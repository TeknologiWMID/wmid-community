import logging
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from directory.models import Kegiatan, KegiatanAnggota, KegiatanLink, Komunitas, SkippedExternalSlug
from .utils import get_session_member


logger = logging.getLogger(__name__)

def kegiatan_list(request):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu untuk membuka halaman itu.')
        return redirect('index')

    qs = Kegiatan.objects.filter(
        sumber__in=[Kegiatan.SUMBER_OTOMATIS, Kegiatan.SUMBER_ADMIN]
    ).prefetch_related('komunitas').order_by('-tanggal_mulai')

    paginator = Paginator(qs, 21)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'directory/kegiatan_list.html', {
        'member':     member,
        'kegiatan':   page_obj,
        'page_obj':   page_obj,
        'paginator':  paginator,
        'page_range': paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1),
    })


def kegiatan_detail(request, kode):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu untuk membuka halaman itu.')
        return redirect('index')

    kegiatan = get_object_or_404(Kegiatan, kode=kode)

    return render(request, 'directory/kegiatan_detail.html', {
        'member':   member,
        'kegiatan': kegiatan,
    })


def kegiatan_daftar(request, kode):
    """User mendaftarkan diri ke kegiatan."""
    member = get_session_member(request)
    if not member or request.method != 'POST':
        return redirect('kegiatan_list')

    kegiatan = get_object_or_404(Kegiatan, kode=kode)
    role = request.POST.get('role', 'peserta').strip()
    catatan = request.POST.get('catatan', '').strip()[:200]

    valid_roles = [r[0] for r in KegiatanAnggota.ROLE_CHOICES]
    if role not in valid_roles:
        role = 'peserta'

    status = (KegiatanAnggota.STATUS_TERVERIFIKASI
              if member.is_admin
              else KegiatanAnggota.STATUS_MENUNGGU)

    obj, created = KegiatanAnggota.objects.get_or_create(
        kegiatan=kegiatan, member=member,
        defaults={'role': role, 'catatan': catatan, 'status': status, 'added_by': member},
    )
    if not created:
        messages.info(request, 'Kegiatan ini sudah ada di riwayatmu.')
    elif status == KegiatanAnggota.STATUS_MENUNGGU:
        messages.success(request, 'Terkirim. Pengurus akan memverifikasi pendaftaranmu.')
    else:
        messages.success(request, f'Kamu tercatat sebagai {obj.get_role_display().lower()} di kegiatan ini.')

    return redirect('kegiatan_detail', kode=kode)



def sync_kegiatan(request):
    """Admin: sinkronisasi kegiatan dari dashboard wikimedia.or.id."""
    member = get_session_member(request)
    if not member or not member.is_admin:
        return redirect('kegiatan_list')

    import requests as _req
    from django.conf import settings
    API_URL = settings.DASHBOARD_API_BASE_URL + '/events'
    try:
        resp = _req.get(API_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.warning('Sinkronisasi kegiatan gagal: %s', e)
        messages.error(request, 'Data dari situs WMID tidak bisa diambil saat ini. Coba lagi nanti.')
        return redirect('kegiatan_list')

    if not payload.get('success'):
        logger.warning('API kegiatan mengembalikan success=false')
        messages.error(request, 'Data dari situs WMID tidak bisa diambil saat ini. Coba lagi nanti.')
        return redirect('kegiatan_list')

    raw = payload.get('data', [])
    if isinstance(raw, dict) and 'data' in raw:
        raw = raw['data']

    # Hapus entri SkippedExternalSlug yang sudah tidak ada di API (sudah dihapus dari sumber)
    api_slugs = {(item.get('slug') or '').strip() for item in raw if (item.get('slug') or '').strip()}
    SkippedExternalSlug.objects.exclude(slug__in=api_slugs).delete()

    skipped_slugs = set(SkippedExternalSlug.objects.values_list('slug', flat=True))

    created = updated = skipped = 0
    for item in raw:
        slug = (item.get('slug') or '').strip()
        if not slug:
            skipped += 1
            continue
        if slug in skipped_slugs:
            skipped += 1
            continue

        tanggal_mulai   = item.get('tanggal_mulai')
        tanggal_selesai = item.get('tanggal_selesai')
        if not tanggal_mulai or not tanggal_selesai:
            skipped += 1
            continue

        raw_jenis = (item.get('jenis_kegiatan') or '').strip()
        jenis = raw_jenis if raw_jenis in Kegiatan.JENIS_VALUES else (Kegiatan.JENIS_LAINNYA if raw_jenis else '')

        defaults = {
            'judul':           (item.get('judul') or '').strip()[:255] or slug,
            'deskripsi':       (item.get('deskripsi') or '').strip(),
            'tanggal_mulai':   tanggal_mulai,
            'tanggal_selesai': tanggal_selesai,
            'lokasi':          (item.get('lokasi') or '').strip()[:255],
            'sumber':          Kegiatan.SUMBER_OTOMATIS,
            'jenis_kegiatan':  jenis,
        }

        kg, was_created = Kegiatan.objects.get_or_create(
            external_slug=slug,
            defaults=defaults,
        )

        if not was_created:
            skipped += 1
            continue

        if item.get('links'):
            for i, link in enumerate(item['links']):
                KegiatanLink.objects.create(
                    kegiatan=kg,
                    judul_link=(link.get('judul_link') or '').strip()[:255],
                    url=(link.get('url') or '').strip()[:500],
                    urutan=i,
                )

        komunitas_slugs = item.get('komunitas_terkait') or []
        if komunitas_slugs:
            kg.komunitas.set(Komunitas.objects.filter(slug__in=komunitas_slugs))

        created += 1

    messages.success(request, f'Sinkronisasi selesai: {created} kegiatan baru, {updated} diperbarui, {skipped} dilewati.')
    return redirect('kegiatan_list')
