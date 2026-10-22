from datetime import date

from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Value, When
from django.db.models.functions import TruncMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from directory.models import Kegiatan, KegiatanAnggota, Komunitas, KomunitasAnggotaPending, Member
from .utils import get_session_member


def _require_admin(request):
    viewer = get_session_member(request)
    if not viewer or not viewer.is_admin:
        messages.error(request, 'Halaman itu khusus pengurus. Kamu dikembalikan ke beranda.')
        return None, redirect('index')
    return viewer, None


def _paginate(qs, request, per_page=25):
    paginator = Paginator(qs, per_page)
    page_obj  = paginator.get_page(request.GET.get('page'))
    page_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))
    params = request.GET.copy()
    params.pop('page', None)
    return page_obj, page_range, params.urlencode()


def _pending_count():
    kg = KegiatanAnggota.objects.filter(status=KegiatanAnggota.STATUS_MENUNGGU).count()
    kom = KomunitasAnggotaPending.objects.count()
    return kg + kom


# ── Overview ──────────────────────────────────────────────────────────────────

def admin_dashboard(request):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    pending_count   = _pending_count()
    total_anggota   = Member.objects.count()
    total_komunitas = Komunitas.objects.count()
    total_kegiatan  = Kegiatan.objects.exclude(sumber=Kegiatan.SUMBER_ANGGOTA).count()
    avail_aktif     = Member.objects.filter(availability=Member.AVAIL_AKTIF).count()
    avail_sibuk     = Member.objects.filter(availability=Member.AVAIL_SIBUK).count()
    avail_tidak     = Member.objects.filter(availability=Member.AVAIL_TIDAK_AKTIF).count()

    recent_kegiatan = (
        Kegiatan.objects
        .exclude(sumber=Kegiatan.SUMBER_ANGGOTA)
        .annotate(peserta_count=Count('peserta',
            filter=Q(peserta__status=KegiatanAnggota.STATUS_TERVERIFIKASI), distinct=True))
        .order_by('-tanggal_mulai')[:5]
    )
    komunitas_top = (
        Komunitas.objects
        .annotate(anggota_count=Count('anggota', distinct=True))
        .order_by('-anggota_count')[:5]
    )

    # Chart data — last 12 months
    _BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
    today = timezone.now().date()
    months_range = []
    for i in range(11, -1, -1):
        m, y = today.month - i, today.year
        while m <= 0:
            m += 12
            y -= 1
        months_range.append(date(y, m, 1))

    member_qs = (
        Member.objects
        .filter(created_at__gte=months_range[0])
        .annotate(month=TruncMonth('created_at'))
        .values('month').annotate(n=Count('id')).order_by('month')
    )
    kegiatan_qs = (
        Kegiatan.objects
        .exclude(sumber=Kegiatan.SUMBER_ANGGOTA)
        .filter(tanggal_mulai__gte=months_range[0])
        .annotate(month=TruncMonth('tanggal_mulai'))
        .values('month').annotate(n=Count('id')).order_by('month')
    )
    member_map   = {row['month'].strftime('%Y-%m'): row['n'] for row in member_qs}
    kegiatan_map = {row['month'].strftime('%Y-%m'): row['n'] for row in kegiatan_qs}

    chart_labels   = [f"{_BULAN[m.month - 1]} '{str(m.year)[2:]}" for m in months_range]
    chart_members  = [member_map.get(m.strftime('%Y-%m'), 0) for m in months_range]
    chart_kegiatan = [kegiatan_map.get(m.strftime('%Y-%m'), 0) for m in months_range]
    chart_avail    = [avail_aktif, avail_sibuk, avail_tidak]

    return render(request, 'directory/admin_dashboard.html', {
        'member':              viewer,
        'total_anggota':       total_anggota,
        'total_komunitas':     total_komunitas,
        'total_kegiatan':      total_kegiatan,
        'pending_count':       pending_count,
        'avail_aktif':         avail_aktif,
        'avail_sibuk':         avail_sibuk,
        'avail_tidak':         avail_tidak,
        'recent_kegiatan':     recent_kegiatan,
        'komunitas_top':       komunitas_top,
        'chart_labels':        chart_labels,
        'chart_members':       chart_members,
        'chart_kegiatan':      chart_kegiatan,
        'chart_avail':         chart_avail,
        'active_admin':        'dashboard',
    })


# ── Anggota ───────────────────────────────────────────────────────────────────

def admin_anggota(request):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    q     = request.GET.get('q', '').strip()
    avail = request.GET.get('avail', '')
    kom   = request.GET.get('komunitas', '')
    sort  = request.GET.get('sort', 'nama')

    qs = (
        Member.objects
        .annotate(
            kg_verified=Count('riwayat_kegiatan',
                filter=Q(riwayat_kegiatan__status=KegiatanAnggota.STATUS_TERVERIFIKASI),
                distinct=True),
            kg_total=Count('riwayat_kegiatan', distinct=True),
        )
        .prefetch_related('keanggotaan__komunitas')
    )

    if q:
        qs = qs.filter(
            Q(display_name__icontains=q) | Q(email__icontains=q) |
            Q(location__icontains=q) | Q(wikimedia_username__icontains=q)
        )
    if avail:
        qs = qs.filter(availability=avail)
    if kom:
        qs = qs.filter(keanggotaan__komunitas__slug=kom).distinct()

    sort_map = {
        'nama':      ('display_name', 'email'),
        'kg-desc':   ('-kg_verified', 'display_name'),
        'kg-asc':    ('kg_verified', 'display_name'),
        'join-desc': ('-created_at',),
    }
    qs = qs.annotate(
        _is_import=Case(
            When(auth_method=Member.AUTH_IMPORT, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('_is_import', *sort_map.get(sort, ('display_name', 'email')))

    page_obj, page_range, filter_params = _paginate(qs, request, per_page=25)

    komunitas_all = Komunitas.objects.order_by('nama_komunitas')

    return render(request, 'directory/admin_anggota.html', {
        'member':        viewer,
        'page_obj':      page_obj,
        'page_range':    page_range,
        'filter_params': filter_params,
        'komunitas_all': komunitas_all,
        'q': q, 'avail': avail, 'kom': kom, 'sort': sort,
        'active_admin':  'anggota',
        'pending_count': _pending_count(),
    })


def admin_anggota_export(request):
    viewer, denied = _require_admin(request)
    if denied:
        return JsonResponse({'error': 'forbidden'}, status=403)

    avail_labels = dict(Member.AVAIL_CHOICES)
    role_labels  = dict(Member.ROLE_CHOICES)

    qs = (
        Member.objects
        .annotate(
            kg_verified=Count('riwayat_kegiatan',
                filter=Q(riwayat_kegiatan__status=KegiatanAnggota.STATUS_TERVERIFIKASI),
                distinct=True),
        )
        .prefetch_related('keanggotaan__komunitas')
        .order_by('display_name', 'email')
    )

    rows = []
    for m in qs:
        komunitas_names = ', '.join(
            ka.komunitas.nama_komunitas for ka in m.keanggotaan.all()
        )
        rows.append({
            'display_name':       m.display_name or '',
            'wikimedia_username': m.wikimedia_username or '',
            'email':              m.email or '',
            'phone':              m.phone or '',
            'role':               role_labels.get(m.role, m.role),
            'availability':       avail_labels.get(m.availability, m.availability),
            'wiki_verified':      'Ya' if m.wiki_verified else 'Tidak',
            'location':           m.location or '',
            'skills':             m.skills or '',
            'joined_wmid_at':     m.joined_wmid_at.strftime('%d/%m/%Y') if m.joined_wmid_at else '',
            'created_at':         m.created_at.strftime('%d/%m/%Y') if m.created_at else '',
            'edit_count':         m.edit_count,
            'kg_verified':        m.kg_verified,
            'komunitas':          komunitas_names,
            'bio':                m.bio or '',
        })

    return JsonResponse({'rows': rows})


def admin_anggota_detail(request, pk):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    from django.shortcuts import get_object_or_404
    target = get_object_or_404(
        Member.objects
        .prefetch_related(
            'keanggotaan__komunitas',
            'riwayat_kegiatan__kegiatan',
            'riwayat_kegiatan__kegiatan__komunitas',
        ),
        pk=pk,
    )
    riwayat = (
        target.riwayat_kegiatan
        .exclude(status=KegiatanAnggota.STATUS_DITOLAK)
        .select_related('kegiatan')
        .order_by('-kegiatan__tanggal_mulai')
    )

    return render(request, 'directory/admin_anggota_detail.html', {
        'member':        viewer,
        'target':        target,
        'riwayat':       riwayat,
        'pending_count': _pending_count(),
        'active_admin':  'anggota',
    })


def admin_anggota_edit(request, pk):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    from django.shortcuts import get_object_or_404
    from directory.models import KomunitasAnggota

    target = get_object_or_404(Member, pk=pk)

    if request.method == 'POST':
        # Delete single riwayat entry
        hapus_id = request.POST.get('hapus_riwayat', '').strip()
        if hapus_id:
            try:
                KegiatanAnggota.objects.filter(pk=int(hapus_id), member=target).delete()
            except (ValueError, TypeError):
                pass
            return redirect('admin_anggota_edit', pk=target.pk)

        # Add new riwayat entry
        if '_add_kegiatan' in request.POST:
            new_kg_id   = request.POST.get('new_kegiatan_id', '').strip()
            new_kg_role = request.POST.get('new_kegiatan_role', 'peserta')
            valid_roles = [r[0] for r in KegiatanAnggota.ROLE_CHOICES]
            if new_kg_id:
                try:
                    kg = Kegiatan.objects.get(pk=int(new_kg_id))
                    KegiatanAnggota.objects.get_or_create(
                        kegiatan=kg, member=target,
                        defaults={
                            'role':        new_kg_role if new_kg_role in valid_roles else 'peserta',
                            'status':      KegiatanAnggota.STATUS_TERVERIFIKASI,
                            'added_by':    viewer,
                            'verified_by': viewer,
                            'verified_at': timezone.now(),
                        },
                    )
                except (ValueError, TypeError, Kegiatan.DoesNotExist):
                    pass
            return redirect('admin_anggota_edit', pk=target.pk)

        # Main save
        new_role = request.POST.get('role', '')
        if new_role in [Member.ROLE_USER, Member.ROLE_ADMIN]:
            if target.pk == viewer.pk and new_role != Member.ROLE_ADMIN:
                messages.error(request, 'Kamu tidak bisa mengubah peranmu sendiri. Minta pengurus lain untuk mengubahnya.')
                return redirect('admin_anggota_edit', pk=target.pk)
            target.role = new_role

        new_avail = request.POST.get('availability', '')
        if new_avail in [a[0] for a in Member.AVAIL_CHOICES]:
            target.availability = new_avail

        target.save(update_fields=['role', 'availability'])

        kom_ids_raw = request.POST.getlist('komunitas')
        kom_ids = set()
        for k in kom_ids_raw:
            try:
                kom_ids.add(int(k))
            except (ValueError, TypeError):
                pass
        current_koms = set(target.keanggotaan.values_list('komunitas_id', flat=True))
        for kid in kom_ids - current_koms:
            KomunitasAnggota.objects.get_or_create(
                member=target, komunitas_id=kid,
                defaults={'added_by': viewer},
            )
        KomunitasAnggota.objects.filter(member=target, komunitas_id__in=current_koms - kom_ids).delete()

        valid_roles = [r[0] for r in KegiatanAnggota.ROLE_CHOICES]
        for r in target.riwayat_kegiatan.exclude(status=KegiatanAnggota.STATUS_DITOLAK):
            new_status = request.POST.get(f'riwayat_{r.pk}_status', '')
            new_r_role = request.POST.get(f'riwayat_{r.pk}_role', '')
            changed = []
            if new_status in [KegiatanAnggota.STATUS_MENUNGGU, KegiatanAnggota.STATUS_TERVERIFIKASI]:
                if new_status != r.status:
                    r.status = new_status
                    if new_status == KegiatanAnggota.STATUS_TERVERIFIKASI:
                        r.verified_by = viewer
                        r.verified_at = timezone.now()
                    changed += ['status', 'verified_by', 'verified_at']
            if new_r_role in valid_roles and new_r_role != r.role:
                r.role = new_r_role
                changed.append('role')
            if changed:
                r.save(update_fields=changed)

        messages.success(request, 'Perubahan data anggota tersimpan.')
        return redirect('admin_anggota_detail', pk=target.pk)

    komunitas_all  = Komunitas.objects.order_by('nama_komunitas')
    member_kom_ids = set(target.keanggotaan.values_list('komunitas_id', flat=True))
    riwayat = (
        target.riwayat_kegiatan
        .exclude(status=KegiatanAnggota.STATUS_DITOLAK)
        .select_related('kegiatan')
        .order_by('-kegiatan__tanggal_mulai')
    )
    kegiatan_tersedia = (
        Kegiatan.objects
        .exclude(peserta__member=target)
        .order_by('-tanggal_mulai')
        .values('id', 'judul', 'kode', 'tanggal_mulai')
    )

    return render(request, 'directory/admin_anggota_edit.html', {
        'member':             viewer,
        'target':             target,
        'riwayat':            riwayat,
        'komunitas_all':      komunitas_all,
        'member_kom_ids':     member_kom_ids,
        'kegiatan_tersedia':  kegiatan_tersedia,
        'pending_count':      _pending_count(),
        'active_admin':       'anggota',
    })


# ── Komunitas ─────────────────────────────────────────────────────────────────

def admin_komunitas_detail(request, slug):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    from django.shortcuts import get_object_or_404
    komunitas = get_object_or_404(Komunitas.objects.select_related('narahubung'), slug=slug)
    anggota_qs = (
        komunitas.anggota
        .select_related('member')
        .annotate(kg_verified=Count('member__riwayat_kegiatan',
            filter=Q(member__riwayat_kegiatan__status=KegiatanAnggota.STATUS_TERVERIFIKASI),
            distinct=True))
        .order_by('member__display_name', 'member__email')
    )
    kegiatan_qs = (
        Kegiatan.objects
        .filter(komunitas=komunitas)
        .annotate(peserta_count=Count('peserta',
            filter=Q(peserta__status=KegiatanAnggota.STATUS_TERVERIFIKASI), distinct=True))
        .order_by('-tanggal_mulai')
    )

    jenis_summary = {}
    for jenis_val, jenis_label in Kegiatan.JENIS_CHOICES:
        n = kegiatan_qs.filter(jenis_kegiatan=jenis_val).count()
        if n:
            jenis_summary[jenis_label] = n

    return render(request, 'directory/admin_komunitas_detail.html', {
        'member':         viewer,
        'komunitas':      komunitas,
        'anggota_qs':     anggota_qs,
        'kegiatan_qs':    kegiatan_qs,
        'jenis_summary':  jenis_summary,
        'pending_count':  _pending_count(),
        'active_admin':   'komunitas',
    })


def admin_komunitas_edit(request, slug):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    from django.shortcuts import get_object_or_404
    from directory.models import KomunitasAnggota

    komunitas = get_object_or_404(Komunitas, slug=slug)

    if request.method == 'POST':
        # Remove anggota
        hapus_anggota = request.POST.get('hapus_anggota', '').strip()
        if hapus_anggota:
            try:
                KomunitasAnggota.objects.filter(pk=int(hapus_anggota), komunitas=komunitas).delete()
            except (ValueError, TypeError):
                pass
            return redirect('admin_komunitas_edit', slug=komunitas.slug)

        # Remove kegiatan
        hapus_kg = request.POST.get('hapus_kegiatan', '').strip()
        if hapus_kg:
            try:
                komunitas.kegiatan.remove(Kegiatan.objects.get(pk=int(hapus_kg)))
            except (ValueError, TypeError, Kegiatan.DoesNotExist):
                pass
            return redirect('admin_komunitas_edit', slug=komunitas.slug)

        # Add anggota
        if '_add_anggota' in request.POST:
            member_id = request.POST.get('new_member_id', '').strip()
            if member_id:
                try:
                    m = Member.objects.get(pk=int(member_id))
                    KomunitasAnggota.objects.get_or_create(
                        member=m, komunitas=komunitas,
                        defaults={'added_by': viewer},
                    )
                except (ValueError, TypeError, Member.DoesNotExist):
                    pass
            return redirect('admin_komunitas_edit', slug=komunitas.slug)

        # Add kegiatan
        if '_add_kegiatan' in request.POST:
            kg_id = request.POST.get('new_kegiatan_id', '').strip()
            if kg_id:
                try:
                    komunitas.kegiatan.add(Kegiatan.objects.get(pk=int(kg_id)))
                except (ValueError, TypeError, Kegiatan.DoesNotExist):
                    pass
            return redirect('admin_komunitas_edit', slug=komunitas.slug)

        # Main save
        nama = request.POST.get('nama_komunitas', '').strip()
        if nama:
            komunitas.nama_komunitas = nama
        new_jenis = request.POST.get('jenis_komunitas', '')
        if new_jenis in [j[0] for j in Komunitas.JENIS_CHOICES] or new_jenis == '':
            komunitas.jenis_komunitas = new_jenis
        komunitas.deskripsi         = request.POST.get('deskripsi', '')
        komunitas.pranala_informasi = request.POST.get('pranala_informasi', '').strip()
        komunitas.logo              = request.POST.get('logo', '').strip()
        komunitas.is_active         = 'is_active' in request.POST

        narahubung_id = request.POST.get('narahubung_id', '').strip()
        if narahubung_id:
            try:
                komunitas.narahubung = Member.objects.get(pk=int(narahubung_id))
            except (Member.DoesNotExist, ValueError):
                pass
        else:
            komunitas.narahubung = None

        komunitas.save(update_fields=['nama_komunitas', 'jenis_komunitas', 'deskripsi', 'pranala_informasi', 'logo', 'is_active', 'narahubung'])

        messages.success(request, 'Perubahan data komunitas tersimpan.')
        return redirect('admin_komunitas_detail', slug=komunitas.slug)

    anggota_qs = (
        komunitas.anggota
        .select_related('member')
        .order_by('member__display_name', 'member__email')
    )
    kegiatan_qs = (
        komunitas.kegiatan
        .order_by('-tanggal_mulai')
    )
    member_ids_in  = set(anggota_qs.values_list('member_id', flat=True))
    kg_ids_in      = set(kegiatan_qs.values_list('id', flat=True))

    anggota_tersedia = (
        Member.objects
        .exclude(pk__in=member_ids_in)
        .order_by('display_name', 'email')
        .values('id', 'display_name', 'wikimedia_username', 'email')
    )
    kegiatan_tersedia = (
        Kegiatan.objects
        .exclude(pk__in=kg_ids_in)
        .order_by('-tanggal_mulai')
        .values('id', 'judul', 'kode', 'tanggal_mulai')
    )

    return render(request, 'directory/admin_komunitas_edit.html', {
        'member':                 viewer,
        'komunitas':              komunitas,
        'anggota_qs':             anggota_qs,
        'kegiatan_qs':            kegiatan_qs,
        'anggota_tersedia':       anggota_tersedia,
        'kegiatan_tersedia':      kegiatan_tersedia,
        'pending_count':          _pending_count(),
        'active_admin':           'komunitas',
    })


def admin_komunitas_export(request):
    viewer, denied = _require_admin(request)
    if denied:
        return JsonResponse({'error': 'forbidden'}, status=403)

    jenis_labels = dict(Komunitas.JENIS_CHOICES)

    qs = (
        Komunitas.objects
        .select_related('narahubung')
        .annotate(
            anggota_count=Count('anggota', distinct=True),
            kg_count=Count('kegiatan', distinct=True),
            kg_wikilatih  = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='WikiLatih'),   distinct=True),
            kg_kopdar     = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Kopdar'),      distinct=True),
            kg_makrab     = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Makrab'),      distinct=True),
            kg_rapat      = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Rapat'),       distinct=True),
            kg_mitra      = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Mitra'),       distinct=True),
            kg_dana_wiki  = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Dana Wiki'),   distinct=True),
            kg_hibah_buku = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Hibah Buku'),  distinct=True),
            kg_rapid_fund = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Rapid Fund'),  distinct=True),
            kg_lainnya    = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Lainnya'),     distinct=True),
        )
        .order_by('nama_komunitas')
    )

    rows = []
    for k in qs:
        rows.append({
            'nama_komunitas':   k.nama_komunitas,
            'kode':             k.kode,
            'slug':             k.slug,
            'jenis_komunitas':  jenis_labels.get(k.jenis_komunitas, k.jenis_komunitas or ''),
            'narahubung':       k.narahubung.display_label if k.narahubung else '',
            'status':           'Aktif' if k.is_active else 'Tidak aktif',
            'deskripsi':        k.deskripsi or '',
            'pranala_informasi':k.pranala_informasi or '',
            'anggota_count':    k.anggota_count,
            'kg_count':         k.kg_count,
            'kg_wikilatih':     k.kg_wikilatih,
            'kg_kopdar':        k.kg_kopdar,
            'kg_makrab':        k.kg_makrab,
            'kg_rapat':         k.kg_rapat,
            'kg_mitra':         k.kg_mitra,
            'kg_dana_wiki':     k.kg_dana_wiki,
            'kg_hibah_buku':    k.kg_hibah_buku,
            'kg_rapid_fund':    k.kg_rapid_fund,
            'kg_lainnya':       k.kg_lainnya,
        })

    return JsonResponse({'rows': rows})


def admin_komunitas(request):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    q     = request.GET.get('q', '').strip()
    jenis = request.GET.get('jenis', '')
    sort  = request.GET.get('sort', 'anggota')

    JENIS_COLS = ['WikiLatih', 'Kopdar', 'Makrab', 'Rapat', 'Mitra', 'Dana Wiki', 'Hibah Buku', 'Rapid Fund', 'Lainnya']
    qs = Komunitas.objects.annotate(
        anggota_count=Count('anggota', distinct=True),
        kg_count=Count('kegiatan', distinct=True),
        kg_wikilatih  = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='WikiLatih'),  distinct=True),
        kg_kopdar     = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Kopdar'),     distinct=True),
        kg_makrab     = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Makrab'),     distinct=True),
        kg_rapat      = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Rapat'),      distinct=True),
        kg_mitra      = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Mitra'),      distinct=True),
        kg_dana_wiki  = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Dana Wiki'),  distinct=True),
        kg_hibah_buku  = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Hibah Buku'),  distinct=True),
        kg_rapid_fund  = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Rapid Fund'), distinct=True),
        kg_lainnya     = Count('kegiatan', filter=Q(kegiatan__jenis_kegiatan='Lainnya'),    distinct=True),
    )

    if q:
        qs = qs.filter(nama_komunitas__icontains=q)
    if jenis:
        qs = qs.filter(jenis_komunitas=jenis)

    sort_map = {
        'anggota':      ('-anggota_count', 'nama_komunitas'),
        'kegiatan':     ('-kg_count', 'nama_komunitas'),
        'kegiatan-asc': ('kg_count', 'nama_komunitas'),
        'nama':         ('nama_komunitas',),
    }
    qs = qs.order_by(*sort_map.get(sort, ('-anggota_count', 'nama_komunitas')))

    page_obj, page_range, filter_params = _paginate(qs, request, per_page=20)

    return render(request, 'directory/admin_komunitas.html', {
        'member':        viewer,
        'page_obj':      page_obj,
        'page_range':    page_range,
        'filter_params': filter_params,
        'jenis_cols':    JENIS_COLS,
        'q': q, 'jenis': jenis, 'sort': sort,
        'active_admin':  'komunitas',
        'pending_count': _pending_count(),
    })



# ── Kegiatan admin ────────────────────────────────────────────────────────────

def admin_kegiatan_detail(request, kode):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    from django.shortcuts import get_object_or_404

    kegiatan = get_object_or_404(
        Kegiatan.objects
        .prefetch_related('komunitas', 'links')
        .annotate(peserta_count=Count('peserta',
            filter=Q(peserta__status=KegiatanAnggota.STATUS_TERVERIFIKASI), distinct=True)),
        kode=kode,
    )
    peserta_all = (
        kegiatan.peserta
        .exclude(status=KegiatanAnggota.STATUS_DITOLAK)
        .select_related('member')
        .order_by('role', 'member__display_name')
    )
    peserta_paginator = Paginator(peserta_all, 50)
    peserta_page = peserta_paginator.get_page(request.GET.get('peserta_page', 1))

    return render(request, 'directory/admin_kegiatan_detail.html', {
        'member':        viewer,
        'kegiatan':      kegiatan,
        'peserta_page':  peserta_page,
        'peserta_paginator': peserta_paginator,
        'pending_count': _pending_count(),
        'active_admin':  'kegiatan',
    })


def admin_kegiatan_tambah(request):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    from django.utils.dateparse import parse_datetime

    def _aware(raw):
        dt = parse_datetime(raw) if raw else None
        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt

    form = {}
    kom_ids = set()
    if request.method == 'POST':
        form = {k: request.POST.get(k, '').strip() for k in
                ('judul', 'tanggal_mulai', 'tanggal_selesai', 'lokasi', 'jenis_kegiatan', 'deskripsi')}
        kom_ids = {int(i) for i in request.POST.getlist('komunitas') if i.isdigit()}
        mulai, selesai = _aware(form['tanggal_mulai']), _aware(form['tanggal_selesai'])

        if not form['judul']:
            messages.error(request, 'Judul kegiatan wajib diisi.')
        elif not mulai or not selesai:
            messages.error(request, 'Isi tanggal dan jam mulai serta selesai.')
        elif selesai < mulai:
            messages.error(request, 'Waktu selesai tidak boleh lebih awal dari waktu mulai.')
        else:
            jenis = form['jenis_kegiatan'] if form['jenis_kegiatan'] in Kegiatan.JENIS_VALUES else ''
            kegiatan = Kegiatan.objects.create(
                judul=form['judul'],
                deskripsi=form['deskripsi'],
                tanggal_mulai=mulai,
                tanggal_selesai=selesai,
                lokasi=form['lokasi'],
                jenis_kegiatan=jenis,
                sumber=Kegiatan.SUMBER_ADMIN,
                dibuat_oleh=viewer,
            )
            if kom_ids:
                kegiatan.komunitas.set(Komunitas.objects.filter(pk__in=kom_ids))
            messages.success(request, f'Kegiatan {kegiatan.kode} ditambahkan. Sekarang kamu bisa menambahkan peserta.')
            return redirect('admin_kegiatan_detail', kode=kegiatan.kode)

    return render(request, 'directory/admin_kegiatan_tambah.html', {
        'member':        viewer,
        'form':          form,
        'kom_ids':       kom_ids,
        'jenis_choices': Kegiatan.JENIS_CHOICES,
        'komunitas_all': Komunitas.objects.order_by('nama_komunitas').only('id', 'nama_komunitas', 'kode'),
        'pending_count': _pending_count(),
        'active_admin':  'kegiatan',
    })


def admin_kegiatan_edit(request, kode):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    from django.shortcuts import get_object_or_404
    from django.utils.dateparse import parse_datetime

    kegiatan = get_object_or_404(Kegiatan, kode=kode)

    if request.method == 'POST':
        # Remove peserta
        hapus_peserta = request.POST.get('hapus_peserta', '').strip()
        if hapus_peserta:
            try:
                KegiatanAnggota.objects.filter(pk=int(hapus_peserta), kegiatan=kegiatan).delete()
                messages.success(request, 'Peserta dihapus dari kegiatan.')
            except (ValueError, TypeError):
                pass
            return redirect('admin_kegiatan_edit', kode=kegiatan.kode)

        # Remove komunitas
        hapus_kom = request.POST.get('hapus_komunitas', '').strip()
        if hapus_kom:
            try:
                kegiatan.komunitas.remove(Komunitas.objects.get(pk=int(hapus_kom)))
            except (ValueError, TypeError, Komunitas.DoesNotExist):
                pass
            return redirect('admin_kegiatan_edit', kode=kegiatan.kode)

        # Add komunitas
        if '_add_komunitas' in request.POST:
            kom_id = request.POST.get('new_komunitas_id', '').strip()
            if kom_id:
                try:
                    kegiatan.komunitas.add(Komunitas.objects.get(pk=int(kom_id)))
                except (ValueError, TypeError, Komunitas.DoesNotExist):
                    pass
            return redirect('admin_kegiatan_edit', kode=kegiatan.kode)

        # Main save
        judul = request.POST.get('judul', '').strip()
        if judul:
            kegiatan.judul = judul
        kegiatan.deskripsi = request.POST.get('deskripsi', '')
        kegiatan.lokasi    = request.POST.get('lokasi', '').strip()

        new_jenis = request.POST.get('jenis_kegiatan', '')
        if new_jenis in Kegiatan.JENIS_VALUES or new_jenis == '':
            kegiatan.jenis_kegiatan = new_jenis

        for field, attr in [('tanggal_mulai', 'tanggal_mulai'), ('tanggal_selesai', 'tanggal_selesai')]:
            raw = request.POST.get(field, '').strip()
            if raw:
                dt = parse_datetime(raw)
                if dt:
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt)
                    setattr(kegiatan, attr, dt)

        kegiatan.save(update_fields=[
            'judul', 'deskripsi', 'lokasi', 'jenis_kegiatan',
            'tanggal_mulai', 'tanggal_selesai',
        ])
        messages.success(request, 'Perubahan kegiatan tersimpan.')
        return redirect('admin_kegiatan_detail', kode=kegiatan.kode)

    komunitas_terpilih = kegiatan.komunitas.all()
    kom_ids_in = set(komunitas_terpilih.values_list('id', flat=True))
    komunitas_tersedia = (
        Komunitas.objects
        .exclude(pk__in=kom_ids_in)
        .order_by('nama_komunitas')
        .values('id', 'nama_komunitas', 'kode')
    )
    peserta_qs = (
        KegiatanAnggota.objects
        .filter(kegiatan=kegiatan)
        .exclude(status=KegiatanAnggota.STATUS_DITOLAK)
        .select_related('member')
        .order_by('role', 'member__display_name')
    )

    return render(request, 'directory/admin_kegiatan_edit.html', {
        'member':             viewer,
        'kegiatan':           kegiatan,
        'komunitas_terpilih': komunitas_terpilih,
        'komunitas_tersedia': komunitas_tersedia,
        'peserta_qs':         peserta_qs,
        'pending_count':      _pending_count(),
        'active_admin':       'kegiatan',
    })


def admin_kegiatan_import(request, kode):
    viewer, denied = _require_admin(request)
    if denied:
        return denied
    if request.method != 'POST':
        return JsonResponse({'error': 'method_not_allowed'}, status=405)

    import json
    from django.shortcuts import get_object_or_404

    kegiatan = get_object_or_404(Kegiatan, kode=kode)

    try:
        payload = json.loads(request.body)
        rows = payload.get('rows', [])
        if not isinstance(rows, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'invalid_payload'}, status=400)

    valid_roles = {r[0] for r in KegiatanAnggota.ROLE_CHOICES}
    imported = skipped_dup = skipped_no_data = 0

    for item in rows:
        nama  = (item.get('nama')  or '').strip()[:200]
        email = (item.get('email') or '').strip().lower()
        hp    = (item.get('hp')    or '').strip()[:20]
        role  = item.get('role', 'peserta')
        if role not in valid_roles:
            role = 'peserta'

        if not email:
            skipped_no_data += 1
            continue

        try:
            member = Member.objects.get(email=email)
        except Member.DoesNotExist:
            member = Member.objects.create(
                email=email,
                display_name=nama or email.split('@')[0],
                auth_method=Member.AUTH_IMPORT,
                wiki_verified=False,
                phone=hp,
            )

        _, created = KegiatanAnggota.objects.get_or_create(
            kegiatan=kegiatan,
            member=member,
            defaults={
                'role': role,
                'status': KegiatanAnggota.STATUS_TERVERIFIKASI,
                'added_by': viewer,
            }
        )
        if created:
            imported += 1
        else:
            skipped_dup += 1

    return JsonResponse({
        'ok': True,
        'imported': imported,
        'skipped_duplicate': skipped_dup,
        'skipped_no_data': skipped_no_data,
    })


def admin_kegiatan_export(request):
    viewer, denied = _require_admin(request)
    if denied:
        return JsonResponse({'error': 'forbidden'}, status=403)

    sumber_labels = dict(Kegiatan.SUMBER_CHOICES)

    qs = (
        Kegiatan.objects
        .annotate(
            peserta_count=Count('peserta',
                filter=Q(peserta__status=KegiatanAnggota.STATUS_TERVERIFIKASI), distinct=True),
            peserta_menunggu=Count('peserta',
                filter=Q(peserta__status=KegiatanAnggota.STATUS_MENUNGGU), distinct=True),
        )
        .prefetch_related('komunitas')
        .order_by('-tanggal_mulai')
    )

    rows = []
    for k in qs:
        komunitas_names = ', '.join(km.nama_komunitas for km in k.komunitas.all())
        rows.append({
            'kode':             k.kode,
            'judul':            k.judul,
            'jenis_kegiatan':   k.jenis_kegiatan or '',
            'tanggal_mulai':    k.tanggal_mulai.strftime('%d/%m/%Y') if k.tanggal_mulai else '',
            'tanggal_selesai':  k.tanggal_selesai.strftime('%d/%m/%Y') if k.tanggal_selesai else '',
            'lokasi':           k.lokasi or '',
            'komunitas':        komunitas_names,
            'sumber':           sumber_labels.get(k.sumber, k.sumber),
            'peserta_count':    k.peserta_count,
            'peserta_menunggu': k.peserta_menunggu,
            'deskripsi':        k.deskripsi or '',
        })

    return JsonResponse({'rows': rows})


def admin_kegiatan_data(request):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    q     = request.GET.get('q', '').strip()
    jenis = request.GET.get('jenis', '')
    sort  = request.GET.get('sort', 'terbaru')

    _has_verified = KegiatanAnggota.objects.filter(
        kegiatan=OuterRef('pk'), status=KegiatanAnggota.STATUS_TERVERIFIKASI
    )
    qs = (
        Kegiatan.objects
        .filter(
            Q(sumber__in=[Kegiatan.SUMBER_OTOMATIS, Kegiatan.SUMBER_ADMIN]) |
            Q(Exists(_has_verified))
        )
        .annotate(peserta_count=Count('peserta',
            filter=Q(peserta__status=KegiatanAnggota.STATUS_TERVERIFIKASI), distinct=True))
        .prefetch_related('komunitas')
    )
    if q:
        qs = qs.filter(Q(judul__icontains=q) | Q(kode__icontains=q) | Q(lokasi__icontains=q))
    if jenis:
        qs = qs.filter(jenis_kegiatan=jenis)

    order_map = {
        'terlama':  'tanggal_mulai',
        'nama':     'judul',
        'peserta':  '-peserta_count',
    }
    qs = qs.order_by(order_map.get(sort, '-tanggal_mulai'))

    page_obj, page_range, filter_params = _paginate(qs, request, per_page=20)

    return render(request, 'directory/admin_kegiatan_data.html', {
        'member':        viewer,
        'page_obj':      page_obj,
        'page_range':    page_range,
        'filter_params': filter_params,
        'q':     q,
        'jenis': jenis,
        'sort':  sort,
        'pending_count': _pending_count(),
        'active_admin':  'kegiatan',
    })


def admin_kegiatan_list(request):
    viewer, denied = _require_admin(request)
    if denied:
        return denied

    pending_kg = (
        KegiatanAnggota.objects
        .filter(status=KegiatanAnggota.STATUS_MENUNGGU)
        .select_related('member', 'kegiatan')
        .order_by('created_at')
    )
    pending_kom = (
        KomunitasAnggotaPending.objects
        .select_related('member', 'komunitas')
        .order_by('created_at')
    )

    return render(request, 'directory/admin_kegiatan_list.html', {
        'member':       viewer,
        'pending':      pending_kg,
        'pending_kom':  pending_kom,
        'active_admin': 'verifikasi',
        'pending_count': pending_kg.count() + pending_kom.count(),
    })


def admin_komunitas_verify(request, entry_id):
    viewer, denied = _require_admin(request)
    if denied:
        return denied
    if request.method != 'POST':
        return redirect('admin_verifikasi')

    from directory.models import KomunitasAnggota
    entry = KomunitasAnggotaPending.objects.filter(pk=entry_id).select_related('member', 'komunitas').first()
    if not entry:
        messages.error(request, 'Permintaan ini sudah tidak ada. Mungkin sudah diproses pengurus lain.')
        return redirect('admin_verifikasi')

    action = request.POST.get('action', '').strip()
    name   = entry.member.display_label
    kom    = entry.komunitas.nama_komunitas

    if action == 'terima':
        if entry.tipe == KomunitasAnggotaPending.TIPE_GABUNG:
            KomunitasAnggota.objects.get_or_create(
                member=entry.member, komunitas=entry.komunitas,
                defaults={'added_by': viewer},
            )
            messages.success(request, f'{name} sekarang anggota {kom}.')
        elif entry.tipe == KomunitasAnggotaPending.TIPE_KELUAR:
            KomunitasAnggota.objects.filter(member=entry.member, komunitas=entry.komunitas).delete()
            messages.success(request, f'{name} sudah keluar dari {kom}.')
        entry.delete()
    elif action == 'tolak':
        entry.delete()
        messages.info(request, f'Permintaan {name} ditolak.')

    return redirect('admin_verifikasi')


def admin_kegiatan_verify(request, entry_id):
    viewer, denied = _require_admin(request)
    if denied:
        return denied
    if request.method != 'POST':
        return redirect('admin_verifikasi')

    entry = KegiatanAnggota.objects.filter(pk=entry_id).select_related('kegiatan', 'member').first()
    if not entry:
        messages.error(request, 'Permintaan ini sudah tidak ada. Mungkin sudah diproses pengurus lain.')
        return redirect('admin_verifikasi')

    action = request.POST.get('action', '').strip()
    if action == 'terima':
        entry.status      = KegiatanAnggota.STATUS_TERVERIFIKASI
        entry.verified_by = viewer
        entry.verified_at = timezone.now()
        entry.save(update_fields=['status', 'verified_by', 'verified_at'])
        messages.success(request, f'Riwayat {entry.member.display_label} terverifikasi.')
    elif action == 'tolak':
        name = entry.member.display_label
        entry.delete()
        messages.info(request, f'Catatan {name} ditolak dan dihapus.')

    return redirect('admin_verifikasi')


def admin_kegiatan_assign(request, kode):
    viewer, denied = _require_admin(request)
    if denied:
        return denied
    if request.method != 'POST':
        return redirect('admin_verifikasi')

    kegiatan = Kegiatan.objects.filter(kode=kode).first()
    if not kegiatan:
        messages.error(request, 'Kegiatan tidak ditemukan.')
        return redirect('admin_verifikasi')

    member_id = request.POST.get('member_id', '').strip()
    role      = request.POST.get('role', 'peserta').strip()
    catatan   = request.POST.get('catatan', '').strip()[:200]

    valid_roles = [r[0] for r in KegiatanAnggota.ROLE_CHOICES]
    if role not in valid_roles:
        role = 'peserta'

    try:
        target = Member.objects.get(pk=member_id)
    except Member.DoesNotExist:
        messages.error(request, 'Anggota tidak ditemukan.')
        return redirect('kegiatan_detail', kode=kode)

    obj, created = KegiatanAnggota.objects.get_or_create(
        kegiatan=kegiatan, member=target,
        defaults={
            'role': role, 'catatan': catatan,
            'status': KegiatanAnggota.STATUS_TERVERIFIKASI,
            'added_by': viewer, 'verified_by': viewer,
            'verified_at': timezone.now(),
        },
    )
    if not created:
        messages.info(request, f'{target.display_label} sudah ada di daftar peserta.')
    else:
        messages.success(request, f'{target.display_label} ditambahkan sebagai {obj.get_role_display().lower()}.')

    return redirect('kegiatan_detail', kode=kode)
