import logging
import json

import requests as _req
from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render

from directory.models import Kegiatan, Komunitas, KomunitasAnggota, KomunitasAnggotaPending
from .utils import get_session_member


logger = logging.getLogger(__name__)

def sync_komunitas(request):
    member = get_session_member(request)
    if not member or not member.is_admin:
        return redirect('komunitas_list')

    API_URL = settings.DASHBOARD_API_BASE_URL + '/communities'
    try:
        resp = _req.get(API_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.warning('Sinkronisasi komunitas gagal: %s', e)
        messages.error(request, 'Data dari situs WMID tidak bisa diambil saat ini. Coba lagi nanti.')
        return redirect('komunitas_list')

    if not payload.get('success'):
        logger.warning('API komunitas mengembalikan success=false')
        messages.error(request, 'Data dari situs WMID tidak bisa diambil saat ini. Coba lagi nanti.')
        return redirect('komunitas_list')

    raw = payload.get('data', [])
    if isinstance(raw, dict) and 'data' in raw:
        raw = raw['data']

    created = skipped = 0
    for item in raw:
        slug = (item.get('slug') or '').strip()
        if not slug:
            skipped += 1
            continue
        _, was_created = Komunitas.objects.get_or_create(
            slug=slug,
            defaults={
                'nama_komunitas':    (item.get('nama_komunitas') or '').strip()[:200],
                'jenis_komunitas':   (item.get('jenis_komunitas') or '').strip()[:50],
                'logo':              (item.get('logo_url') or '')[:500],
                'deskripsi':         (item.get('deskripsi') or '').strip(),
                'pranala_informasi': (item.get('pranala') or '')[:500],
                'latitude':          float(item['latitude']) if item.get('latitude') else None,
                'longitude':         float(item['longitude']) if item.get('longitude') else None,
                'is_active':         bool(item.get('is_active', True)),
            }
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    messages.success(request, f'Sinkronisasi selesai: {created} komunitas baru, {skipped} sudah ada sebelumnya.')
    return redirect('komunitas_list')


def komunitas_list(request):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu untuk membuka halaman itu.')
        return redirect('index')

    komunitas = Komunitas.objects.filter(is_active=True)

    def _item(k, with_coords):
        d = {
            'name':      k.nama_komunitas,
            'slug':      k.slug,
            'jenis':     k.jenis_label,
            'jenis_raw': k.jenis_komunitas,
            'logo':      k.logo,
            'deskripsi': k.deskripsi,
            'pranala':   k.pranala_informasi,
        }
        if with_coords:
            d['lat'] = k.latitude
            d['lng'] = k.longitude
        return d

    geo_points = [_item(k, True)  for k in komunitas if k.latitude and k.longitude]
    no_coord   = [_item(k, False) for k in komunitas if not k.latitude or not k.longitude]

    return render(request, 'directory/komunitas.html', {
        'member':          member,
        'komunitas':       komunitas,
        'geo_points_json': json.dumps(geo_points),
        'no_coord_json':   json.dumps(no_coord),
    })


def komunitas_detail(request, slug):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu untuk membuka halaman itu.')
        return redirect('index')

    try:
        komunitas = Komunitas.objects.select_related('narahubung').get(slug=slug)
    except Komunitas.DoesNotExist:
        raise Http404

    anggota_qs = KomunitasAnggota.objects.filter(komunitas=komunitas).select_related('member')
    is_member  = anggota_qs.filter(member=member).exists()
    kegiatan_qs = (
        Kegiatan.objects
        .filter(komunitas=komunitas)
        .order_by('-tanggal_mulai')
    )

    return render(request, 'directory/komunitas_detail.html', {
        'member':      member,
        'komunitas':   komunitas,
        'anggota_qs':  anggota_qs,
        'is_member':   is_member,
        'kegiatan_qs': kegiatan_qs,
    })


def komunitas_join(request, slug):
    member = get_session_member(request)
    if not member or request.method != 'POST':
        return redirect('komunitas_list')

    try:
        komunitas = Komunitas.objects.get(slug=slug)
    except Komunitas.DoesNotExist:
        return redirect('komunitas_list')

    if KomunitasAnggota.objects.filter(member=member, komunitas=komunitas).exists():
        messages.info(request, f'Kamu sudah tergabung di {komunitas.nama_komunitas}.')
        return redirect(request.POST.get('next', 'profile'))

    existing = KomunitasAnggotaPending.objects.filter(member=member, komunitas=komunitas).first()
    if existing:
        if existing.tipe == KomunitasAnggotaPending.TIPE_GABUNG:
            messages.info(request, 'Permintaanmu sudah terkirim sebelumnya dan masih menunggu.')
        else:
            # Stale pending keluar (member sudah dihapus admin tapi pending belum dibersihkan)
            existing.tipe = KomunitasAnggotaPending.TIPE_GABUNG
            existing.save(update_fields=['tipe'])
            messages.success(request, f'Permintaan bergabung dengan {komunitas.nama_komunitas} terkirim. Pengurus akan memeriksanya.')
    else:
        KomunitasAnggotaPending.objects.create(member=member, komunitas=komunitas, tipe=KomunitasAnggotaPending.TIPE_GABUNG)
        messages.success(request, f'Permintaan bergabung dengan {komunitas.nama_komunitas} terkirim. Pengurus akan memeriksanya.')
    return redirect(request.POST.get('next', 'profile'))


def komunitas_pending_cancel(request, slug):
    member = get_session_member(request)
    if not member or request.method != 'POST':
        return redirect('komunitas_list')

    KomunitasAnggotaPending.objects.filter(member=member, komunitas__slug=slug).delete()
    return redirect(request.POST.get('next', 'profile_edit') + '#komunitas')


def komunitas_leave(request, slug):
    member = get_session_member(request)
    if not member or request.method != 'POST':
        return redirect('komunitas_list')

    try:
        komunitas = Komunitas.objects.get(slug=slug)
    except Komunitas.DoesNotExist:
        return redirect('komunitas_list')

    if not KomunitasAnggota.objects.filter(member=member, komunitas=komunitas).exists():
        messages.info(request, 'Kamu tidak tergabung di komunitas ini.')
        return redirect(request.POST.get('next', 'profile'))

    _, created = KomunitasAnggotaPending.objects.get_or_create(
        member=member, komunitas=komunitas,
        defaults={'tipe': KomunitasAnggotaPending.TIPE_KELUAR},
    )
    if created:
        messages.success(request, f'Permintaan keluar dari {komunitas.nama_komunitas} terkirim. Pengurus akan memeriksanya.')
    else:
        messages.info(request, 'Permintaanmu sudah terkirim sebelumnya dan masih menunggu.')
    return redirect(request.POST.get('next', 'profile'))
