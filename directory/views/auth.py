import logging
import secrets
from datetime import datetime

from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import check_password, make_password

from directory.models import Member
from directory.wikimedia import (
    build_authorize_url,
    exchange_code_for_token,
    fetch_profile,
    sync_contributions,
)
from .utils import get_session_member, store_sync_result


logger = logging.getLogger(__name__)

_OAUTH_PUTUS = 'Proses menghubungkan akun terputus. Mulai lagi dari tombol Hubungkan akun Wikimedia di profil.'

def register(request):
    if get_session_member(request):
        return redirect('profile')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        display_name = request.POST.get('display_name', '').strip()[:200]
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        ctx = {'email': email, 'display_name': display_name}
        has_error = False

        if not display_name:
            messages.error(request, 'Nama lengkap belum diisi.')
            has_error = True
        if not email:
            messages.error(request, 'Email belum diisi.')
            has_error = True
        if not password:
            messages.error(request, 'Kata sandi belum diisi.')
            has_error = True
        elif len(password) < 8:
            messages.error(request, 'Kata sandi terlalu pendek. Pakai minimal 8 karakter.')
            has_error = True
        if password and password != password2:
            messages.error(request, 'Kedua kata sandi tidak sama. Ketik ulang dengan teliti.')
            has_error = True
        shadow = None
        if email:
            try:
                existing = Member.objects.get(email=email)
                if existing.auth_method == Member.AUTH_IMPORT:
                    shadow = existing
                else:
                    messages.error(request, 'Email ini sudah punya akun. Masuk dengan email tersebut.')
                    has_error = True
            except Member.DoesNotExist:
                pass

        if has_error:
            return render(request, 'directory/register.html', ctx)

        if shadow:
            shadow.display_name = display_name
            shadow.password_hash = make_password(password)
            shadow.auth_method = Member.AUTH_EMAIL
            shadow.save(update_fields=['display_name', 'password_hash', 'auth_method'])
            request.session['member_id'] = shadow.pk
            riwayat_count = shadow.riwayat_kegiatan.filter(
                status='terverifikasi'
            ).count()
            msg = 'Akunmu sudah jadi. Selamat datang di Direktori WMID.'
            if riwayat_count:
                msg += f' {riwayat_count} riwayat kegiatanmu yang lama sudah tersambung ke akun ini.'
            messages.success(request, msg)
            return redirect('profile')

        member = Member.objects.create(
            email=email,
            display_name=display_name,
            password_hash=make_password(password),
            auth_method=Member.AUTH_EMAIL,
            wiki_verified=False,
        )
        request.session['member_id'] = member.pk
        messages.success(request, 'Akunmu sudah jadi. Selamat datang di Direktori WMID.')
        return redirect('profile')

    return render(request, 'directory/register.html', {})


_MAX_ATTEMPTS    = 10
_LOCKOUT_SECONDS = 60  # 1 menit


def _login_cache_key(ip):
    return f'login_attempts:{ip}'


def _get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def email_login(request):
    if get_session_member(request):
        return redirect('profile')

    if request.method == 'POST':
        ip = _get_client_ip(request)
        cache_key = _login_cache_key(ip)
        attempts = cache.get(cache_key, 0)

        if attempts >= _MAX_ATTEMPTS:
            messages.error(request, 'Terlalu banyak percobaan masuk. Tunggu 1 menit, lalu coba lagi.')
            return render(request, 'directory/login.html', {})

        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        try:
            member = Member.objects.get(email=email, auth_method=Member.AUTH_EMAIL)
        except Member.DoesNotExist:
            cache.set(cache_key, attempts + 1, _LOCKOUT_SECONDS)
            messages.error(request, 'Email atau kata sandi tidak cocok. Periksa lagi, lalu coba masuk.')
            return render(request, 'directory/login.html', {'email': email})

        if not check_password(password, member.password_hash):
            cache.set(cache_key, attempts + 1, _LOCKOUT_SECONDS)
            messages.error(request, 'Email atau kata sandi tidak cocok. Periksa lagi, lalu coba masuk.')
            return render(request, 'directory/login.html', {'email': email})

        cache.delete(cache_key)
        request.session['member_id'] = member.pk
        messages.success(request, f'Selamat datang kembali, {member.display_name or email}.')
        return redirect('profile')

    return render(request, 'directory/login.html', {})


def oauth_login(request):
    member = get_session_member(request)
    if not member:
        messages.info(request, 'Masuk dulu, lalu hubungkan akun Wikimedia dari halaman profil.')
        return redirect('email_login')

    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    request.session['linking_member_id'] = member.pk

    response = redirect(build_authorize_url(state))
    response.set_cookie('oauth_state', state, max_age=600, httponly=True, samesite='Lax')
    return response


def oauth_callback(request):
    error = request.GET.get('error')
    if error:
        logger.warning('OAuth ditolak: %s', request.GET.get('error_description', error))
        messages.error(request, 'Wikimedia tidak memberi izin, jadi akun belum terhubung. Coba hubungkan lagi dari profil.')
        return redirect('profile')

    code = request.GET.get('code')
    state = request.GET.get('state')
    saved_state = request.session.pop('oauth_state', None) or request.COOKIES.get('oauth_state')

    if not code:
        logger.warning('OAuth callback tanpa parameter code')
        messages.error(request, _OAUTH_PUTUS)
        return redirect('profile')

    if state != saved_state:
        logger.warning('OAuth state tidak cocok')
        messages.error(request, _OAUTH_PUTUS)
        return redirect('profile')

    linking_member_id = request.session.pop('linking_member_id', None)
    if not linking_member_id:
        logger.warning('OAuth callback tanpa linking_member_id di sesi')
        messages.error(request, _OAUTH_PUTUS)
        return redirect('profile')

    try:
        token_data = exchange_code_for_token(code)
    except Exception as e:
        logger.warning('OAuth gagal menukar token: %s', e)
        messages.error(request, 'Wikimedia sedang tidak bisa dihubungi. Coba lagi beberapa menit lagi.')
        return redirect('profile')

    try:
        profile = fetch_profile(token_data['access_token'])
    except Exception as e:
        logger.warning('OAuth gagal mengambil profil: %s', e)
        messages.error(request, 'Wikimedia sedang tidak bisa dihubungi. Coba lagi beberapa menit lagi.')
        return redirect('profile')

    return _handle_account_link(request, profile, linking_member_id)


def _handle_account_link(request, profile, linking_member_id):
    try:
        member = Member.objects.get(pk=linking_member_id)
    except Member.DoesNotExist:
        logger.warning('Sesi penautan akun tidak valid')
        messages.error(request, _OAUTH_PUTUS)
        return redirect('index')

    wiki_userid = str(profile.get('sub', ''))
    wiki_username = profile.get('username', '')

    if Member.objects.filter(wikimedia_userid=wiki_userid).exclude(pk=linking_member_id).exists():
        messages.error(request, f'Akun Wikimedia {wiki_username} sudah dipakai oleh anggota lain di direktori ini. Kalau itu akunmu, hubungi pengurus.')
        return redirect('profile')

    registered_at = None
    registered_raw = profile.get('registered')
    if registered_raw:
        for fmt in ('%Y%m%d%H%M%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S%z'):
            try:
                registered_at = datetime.strptime(str(registered_raw), fmt)
                break
            except (ValueError, TypeError):
                continue

    member.wikimedia_username = wiki_username
    member.wikimedia_userid = wiki_userid
    member.wiki_verified = True
    member.edit_count = profile.get('editcount', 0)
    member.groups = profile.get('groups', [])
    member.registered_at = registered_at
    member.raw_profile = {}
    if not member.email:
        member.email = profile.get('email', '')
    member.save()

    try:
        store_sync_result(request, sync_contributions(member))
    except Exception as e:
        logger.warning('Sinkronisasi setelah OAuth gagal: %s', e)
        messages.warning(request, 'Akun Wikimedia sudah terhubung, tapi suntinganmu belum bisa ditarik. Coba Sinkronkan suntingan dari profil.')

    messages.success(request, f'Akun Wikimedia {wiki_username} sudah terhubung.')
    request.session['member_id'] = member.pk
    return redirect('profile')


def logout(request):
    request.session.flush()
    messages.success(request, 'Kamu sudah keluar dari akun.')
    return redirect('index')
