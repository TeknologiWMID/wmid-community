import logging
import traceback
from datetime import date, datetime, time

from django.contrib import messages
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.urls import reverse

from directory.models import Kegiatan, KegiatanAnggota, Komunitas, KomunitasAnggotaPending, Member
from directory.wikimedia import sync_contributions
from .utils import get_session_member, store_sync_result


logger = logging.getLogger(__name__)

def index(request):
    member = get_session_member(request)
    return render(request, 'directory/index.html', {
        'member':       member,
        'member_count': Member.objects.count(),
    })


def profile(request):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu untuk membuka halaman itu.')
        return redirect('index')

    sync_result = request.session.pop('last_sync_result', None)

    recent = member.contributions.order_by('-timestamp')[:10]

    _stats_key = f'profile_contrib_stats:{member.pk}'
    stats = cache.get(_stats_key)
    if stats is None or sync_result:
        projects = list(
            member.contributions.values('project')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        agg = member.contributions.aggregate(
            bytes_added=Sum('sizediff', filter=Q(sizediff__gt=0)),
            bytes_removed=Sum('sizediff', filter=Q(sizediff__lt=0)),
        )
        unique_pages = member.contributions.values('project', 'title').distinct().count()
        stats = {
            'projects':     projects,
            'bytes_added':  agg['bytes_added'] or 0,
            'bytes_removed': abs(agg['bytes_removed'] or 0),
            'unique_pages': unique_pages,
        }
        cache.set(_stats_key, stats, 300)

    projects      = stats['projects']
    bytes_added   = stats['bytes_added']
    bytes_removed = stats['bytes_removed']
    unique_pages  = stats['unique_pages']

    DEFAULT_GROUPS = {'*', 'user'}
    special_groups = [g for g in (member.groups or []) if g not in DEFAULT_GROUPS]
    skills_list    = [s.strip() for s in member.skills.split(',') if s.strip()] if member.skills else []
    my_komunitas   = list(member.keanggotaan.select_related('komunitas').order_by('komunitas__nama_komunitas'))

    riwayat_kegiatan = (
        KegiatanAnggota.objects
        .filter(member=member, status__in=[
            KegiatanAnggota.STATUS_TERVERIFIKASI,
            KegiatanAnggota.STATUS_MENUNGGU,
        ])
        .select_related('kegiatan')
        .order_by('-kegiatan__tanggal_mulai')
    )

    incomplete = []
    if not member.display_name:
        incomplete.append({'text': 'Isi nama lengkap', 'url': reverse('profile_edit')})
    if not member.bio:
        incomplete.append({'text': 'Tulis bio singkat', 'url': reverse('profile_edit')})
    if not (member.skills and member.skills.strip()):
        incomplete.append({'text': 'Tambah keahlian', 'url': reverse('profile_edit')})

    return render(request, 'directory/profile.html', {
        'member':           member,
        'special_groups':   special_groups,
        'recent':           recent,
        'projects':         projects,
        'bytes_added':      bytes_added,
        'bytes_removed':    bytes_removed,
        'net_bytes':        bytes_added - bytes_removed,
        'unique_pages':     unique_pages,
        'sync_result':      sync_result,
        'skills_list':      skills_list,
        'my_komunitas':     my_komunitas,
        'riwayat_kegiatan': riwayat_kegiatan,
        'incomplete':       incomplete,
    })


_RESYNC_COOLDOWN = 300  # 5 menit


def resync(request):
    member = get_session_member(request)
    if not member:
        return redirect('index')
    cache_key = f'resync_cooldown:{member.pk}'
    if cache.get(cache_key):
        messages.warning(request, 'Suntinganmu baru saja disinkronkan. Kamu bisa sinkronkan lagi setelah 5 menit.')
        return redirect('profile')
    cache.set(cache_key, True, _RESYNC_COOLDOWN)
    try:
        store_sync_result(request, sync_contributions(member))
    except Exception as e:
        logger.warning('Sinkronisasi suntingan gagal untuk anggota %s: %s', member.pk, e)
        messages.error(request, 'Sinkronisasi gagal. Coba lagi beberapa menit lagi.')
        request.session['last_sync_error'] = traceback.format_exc()
    return redirect('profile')


def profile_edit(request):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu untuk membuka halaman itu.')
        return redirect('index')

    if request.method == 'POST':
        member.display_name = request.POST.get('display_name', '').strip()[:200]
        member.bio          = request.POST.get('bio', '').strip()[:500]
        member.phone        = request.POST.get('phone', '').strip()[:20]

        province = request.POST.get('location_province', '').strip()
        city     = request.POST.get('location_city', '').strip()
        member.location = (f'{city}, {province}' if city and province else province)[:100]
        member.skills   = request.POST.get('skills', '').strip()[:300]

        joined_raw = request.POST.get('joined_wmid_at', '').strip()
        if joined_raw:
            try:
                member.joined_wmid_at = date.fromisoformat(joined_raw)
            except ValueError:
                messages.error(request, 'Tanggal belum lengkap atau formatnya salah.')
        else:
            member.joined_wmid_at = None

        avail = request.POST.get('availability', '').strip()
        if avail in (Member.AVAIL_AKTIF, Member.AVAIL_SIBUK, Member.AVAIL_TIDAK_AKTIF):
            member.availability = avail

        update_fields = ['display_name', 'bio', 'location', 'skills', 'joined_wmid_at', 'availability', 'phone']

        if member.auth_method != Member.AUTH_EMAIL:
            new_email = request.POST.get('email', '').strip().lower()
            if new_email != member.email:
                if new_email and Member.objects.filter(email=new_email).exclude(pk=member.pk).exists():
                    messages.error(request, 'Email ini sudah dipakai akun lain. Pakai email yang berbeda.')
                    return redirect('profile_edit')
                member.email = new_email
                update_fields.append('email')

        member.save(update_fields=update_fields)
        messages.success(request, 'Profil tersimpan.')
        return redirect('profile')

    DEFAULT_GROUPS = {'*', 'user'}
    special_groups = [g for g in (member.groups or []) if g not in DEFAULT_GROUPS]

    joined_ids   = set(member.keanggotaan.values_list('komunitas_id', flat=True))
    pending_all  = KomunitasAnggotaPending.objects.filter(member=member).select_related('komunitas')
    pending_gabung     = [p for p in pending_all if p.tipe == KomunitasAnggotaPending.TIPE_GABUNG]
    pending_keluar_ids = {p.komunitas_id for p in pending_all if p.tipe == KomunitasAnggotaPending.TIPE_KELUAR}
    pending_gabung_ids = {p.komunitas_id for p in pending_gabung}

    my_komunitas  = Komunitas.objects.filter(pk__in=joined_ids, is_active=True)
    all_komunitas = Komunitas.objects.filter(is_active=True).exclude(pk__in=joined_ids).exclude(pk__in=pending_gabung_ids)

    return render(request, 'directory/profile_edit.html', {
        'member':             member,
        'special_groups':     special_groups,
        'my_komunitas':       my_komunitas,
        'all_komunitas':      all_komunitas,
        'pending_gabung':     pending_gabung,
        'pending_keluar_ids': pending_keluar_ids,
    })


def profile_kegiatan_tambah(request):
    return redirect('riwayat_catat')


def riwayat_cancel(request, entry_id):
    member = get_session_member(request)
    if not member or request.method != 'POST':
        return redirect('profile')

    KegiatanAnggota.objects.filter(
        pk=entry_id,
        member=member,
        status=KegiatanAnggota.STATUS_MENUNGGU,
    ).delete()
    return redirect('profile')


def riwayat_catat(request):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu untuk membuka halaman itu.')
        return redirect('index')

    if request.method == 'POST':
        valid_roles = [r[0] for r in KegiatanAnggota.ROLE_CHOICES]
        role = request.POST.get('role', 'peserta').strip()
        if role not in valid_roles:
            role = 'peserta'

        kegiatan_id = request.POST.get('kegiatan_id', '').strip()

        catatan = request.POST.get('catatan', '').strip()[:200]

        if kegiatan_id:
            from django.shortcuts import get_object_or_404
            kegiatan = get_object_or_404(Kegiatan, pk=kegiatan_id)
            _, created = KegiatanAnggota.objects.get_or_create(
                kegiatan=kegiatan, member=member,
                defaults={'role': role, 'catatan': catatan, 'status': KegiatanAnggota.STATUS_MENUNGGU, 'added_by': member},
            )
            if created:
                messages.success(request, f'Catatanmu di {kegiatan.judul} terkirim. Pengurus akan memverifikasinya.')
            else:
                messages.info(request, 'Kegiatan ini sudah ada di riwayatmu.')
        else:
            judul       = request.POST.get('judul', '').strip()[:255]
            mulai_str   = request.POST.get('tanggal_mulai', '').strip()
            selesai_str = request.POST.get('tanggal_selesai', '').strip()
            lokasi      = request.POST.get('lokasi', '').strip()[:255]

            if not judul or not mulai_str:
                messages.error(request, 'Nama kegiatan dan tanggal mulai perlu diisi.')
                return redirect('riwayat_catat')

            try:
                tgl_mulai = datetime.combine(date.fromisoformat(mulai_str), time())
            except (ValueError, TypeError):
                messages.error(request, 'Tanggal mulai belum lengkap atau formatnya salah.')
                return redirect('riwayat_catat')

            if KegiatanAnggota.objects.filter(
                member=member,
                kegiatan__judul__iexact=judul,
                kegiatan__tanggal_mulai__date=tgl_mulai.date(),
                kegiatan__sumber=Kegiatan.SUMBER_ANGGOTA,
            ).exists():
                messages.info(request, 'Kamu sudah mencatat kegiatan dengan nama dan tanggal yang sama. Cek riwayatmu.')
                return redirect('profile')

            if selesai_str:
                try:
                    tgl_selesai = datetime.combine(date.fromisoformat(selesai_str), time())
                except (ValueError, TypeError):
                    messages.error(request, 'Tanggal selesai belum lengkap atau formatnya salah.')
                    return redirect('riwayat_catat')
                if tgl_selesai < tgl_mulai:
                    messages.error(request, 'Tanggal selesai lebih awal dari tanggal mulai. Periksa lagi kedua tanggalnya.')
                    return redirect('riwayat_catat')
            else:
                tgl_selesai = tgl_mulai

            jenis = request.POST.get('jenis_kegiatan', '').strip()
            if jenis not in Kegiatan.JENIS_VALUES:
                jenis = ''

            kegiatan = Kegiatan.objects.create(
                judul=judul,
                tanggal_mulai=tgl_mulai,
                tanggal_selesai=tgl_selesai,
                lokasi=lokasi,
                sumber=Kegiatan.SUMBER_ANGGOTA,
                dibuat_oleh=member,
                jenis_kegiatan=jenis,
            )
            komunitas_ids = [i for i in request.POST.getlist('komunitas_id') if i]
            if komunitas_ids:
                kegiatan.komunitas.set(
                    Komunitas.objects.filter(pk__in=komunitas_ids)
                )
            KegiatanAnggota.objects.create(
                kegiatan=kegiatan, member=member,
                role=role, catatan=catatan, status=KegiatanAnggota.STATUS_MENUNGGU, added_by=member,
            )

            messages.success(request, f'{kegiatan.judul} sudah dicatat. Pengurus akan memverifikasinya.')

        return redirect('profile')

    already_in_ids = member.riwayat_kegiatan.values_list('kegiatan_id', flat=True)
    wmid_kegiatan = (
        Kegiatan.objects
        .filter(sumber__in=[Kegiatan.SUMBER_OTOMATIS, Kegiatan.SUMBER_ADMIN])
        .exclude(pk__in=already_in_ids)
        .only('pk', 'judul', 'tanggal_mulai', 'lokasi')
        .order_by('-tanggal_mulai')[:150]
    )
    other_kegiatan = (
        Kegiatan.objects
        .filter(sumber=Kegiatan.SUMBER_ANGGOTA)
        .exclude(pk__in=already_in_ids)
        .exclude(dibuat_oleh=member)
        .only('pk', 'judul', 'tanggal_mulai', 'lokasi')
        .order_by('-tanggal_mulai')[:50]
    )
    komunitas_all = Komunitas.objects.filter(is_active=True).order_by('nama_komunitas')

    return render(request, 'directory/riwayat_catat.html', {
        'member':         member,
        'wmid_kegiatan':  wmid_kegiatan,
        'other_kegiatan': other_kegiatan,
        'komunitas_all':  komunitas_all,
        'role_choices':   KegiatanAnggota.ROLE_CHOICES,
        'jenis_choices':  Kegiatan.JENIS_CHOICES,
    })
