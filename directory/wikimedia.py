"""
Fungsi-fungsi untuk berinteraksi dengan Wikimedia OAuth 2.0 dan Action API.
Menggunakan requests secara langsung agar alurnya transparan.
"""
import requests
from django.conf import settings
from django.utils import timezone
from datetime import datetime

MAX_WIKIS_TO_SYNC = getattr(settings, 'MAX_WIKIS_TO_SYNC', 30)
CONTRIBS_PER_WIKI = getattr(settings, 'CONTRIBS_PER_WIKI', 20)

META_API = 'https://meta.wikimedia.org/w/api.php'


def build_authorize_url(state: str) -> str:
    from urllib.parse import urlencode
    params = {
        'response_type': 'code',
        'client_id': settings.WIKIMEDIA_CLIENT_ID,
        'redirect_uri': settings.WIKIMEDIA_REDIRECT_URI,
        'state': state,
    }
    return f'{settings.WIKIMEDIA_AUTHORIZE_URL}?{urlencode(params)}'


def exchange_code_for_token(code: str) -> dict:
    resp = requests.post(
        settings.WIKIMEDIA_TOKEN_URL,
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.WIKIMEDIA_REDIRECT_URI,
            'client_id': settings.WIKIMEDIA_CLIENT_ID,
            'client_secret': settings.WIKIMEDIA_CLIENT_SECRET,
        },
        headers={
            'User-Agent': settings.WIKIMEDIA_USER_AGENT,
            'Accept': 'application/json',
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if 'access_token' not in data:
        raise ValueError(f'Respons token tidak valid: {data}')
    return data


def fetch_profile(access_token: str) -> dict:
    resp = requests.get(
        settings.WIKIMEDIA_PROFILE_URL,
        headers={
            'Authorization': f'Bearer {access_token}',
            'User-Agent': settings.WIKIMEDIA_USER_AGENT,
            'Accept': 'application/json',
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_user_wikis(username: str) -> tuple:
    """
    Ambil daftar semua wiki tempat user terdaftar via CentralAuth globaluserinfo.
    Mengembalikan (wikis_with_edits, raw_merged) di mana:
      - wikis_with_edits: list dict {'wiki','url','editcount'} diurutkan editcount desc,
        dibatasi MAX_WIKIS_TO_SYNC, hanya yang ada suntingan
      - raw_merged: list mentah semua entri dari API (untuk debug)
    """
    resp = requests.get(
        META_API,
        params={
            'action': 'query',
            'meta': 'globaluserinfo',
            'guiuser': username,
            'guiprop': 'merged|editcount',
            'format': 'json',
        },
        headers={'User-Agent': settings.WIKIMEDIA_USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    gui = data.get('query', {}).get('globaluserinfo', {})
    raw_merged = gui.get('merged', [])
    # editcount di level atas = total global edit count dari CentralAuth
    global_editcount = gui.get('editcount', 0)

    wikis_with_edits = [
        {
            'wiki': entry['wiki'],
            'url': entry['url'].rstrip('/'),
            'editcount': entry.get('editcount', 0),
        }
        for entry in raw_merged
        if entry.get('editcount', 0) > 0
    ]
    wikis_with_edits.sort(key=lambda w: w['editcount'], reverse=True)
    return wikis_with_edits[:MAX_WIKIS_TO_SYNC], raw_merged, global_editcount


def fetch_contributions_from_url(api_url: str, username: str, limit: int = CONTRIBS_PER_WIKI) -> list:
    """Ambil kontribusi dari satu wiki via URL API-nya (publik, tanpa auth)."""
    resp = requests.get(
        api_url,
        params={
            'action': 'query',
            'list': 'usercontribs',
            'ucuser': username,
            'uclimit': limit,
            'ucprop': 'title|timestamp|comment|sizediff',
            'format': 'json',
        },
        headers={'User-Agent': settings.WIKIMEDIA_USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get('query', {}).get('usercontribs', [])


def fetch_editcount_from_wiki(api_url: str, username: str) -> int:
    """Tanya satu wiki berapa edit count user — untuk fallback saat globaluserinfo kosong."""
    try:
        resp = requests.get(
            api_url,
            params={
                'action': 'query',
                'list': 'users',
                'ususers': username,
                'usprop': 'editcount',
                'format': 'json',
            },
            headers={'User-Agent': settings.WIKIMEDIA_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        users = resp.json().get('query', {}).get('users', [])
        return users[0].get('editcount', 0) if users else 0
    except Exception:
        return 0



def sync_contributions(member) -> dict:
    """
    Tarik kontribusi dari semua proyek Wikimedia tempat user punya suntingan.
    Jika CentralAuth tidak menemukan wiki manapun, fallback ke CONTRIB_PROJECT.
    Mengembalikan dict: {'saved', 'wikis_found', 'wikis_synced', 'errors', 'fallback'}.
    """
    from directory.models import Contribution

    username = member.wikimedia_username
    if not username:
        return {'saved': 0, 'wikis_found': 0, 'wikis_synced': 0, 'errors': [], 'fallback': False}

    wikis, raw_merged, global_editcount = fetch_user_wikis(username)

    # Jika CentralAuth mengembalikan global editcount yang lebih akurat, update member
    if global_editcount > 0 and global_editcount != member.edit_count:
        member.edit_count = global_editcount
        member.save(update_fields=['edit_count'])

    fallback_used = False
    fallback_editcount = 0

    # Jika CentralAuth tidak menemukan merged account (akun baru atau belum unified),
    # coba satu per satu wiki dari FALLBACK_WIKIS dan cek editcount via API publik.
    if not wikis:
        fallback_used = True
        for host in getattr(settings, 'FALLBACK_WIKIS', [settings.CONTRIB_PROJECT]):
            api_url = f'https://{host}/w/api.php'
            count = fetch_editcount_from_wiki(api_url, username)
            if count > 0:
                wikis.append({'wiki': host, 'url': f'https://{host}', 'editcount': count})
                fallback_editcount += count
        wikis.sort(key=lambda w: w['editcount'], reverse=True)

        # Update edit_count dari fallback jika CentralAuth tidak kasih data
        if fallback_editcount > 0 and global_editcount == 0:
            member.edit_count = fallback_editcount
            member.save(update_fields=['edit_count'])

    total_saved = 0
    errors = []

    for wiki in wikis:
        project_host = wiki['url'].replace('https://', '').replace('http://', '')
        api_url = f"{wiki['url']}/w/api.php"

        try:
            items = fetch_contributions_from_url(api_url, username)
        except Exception as e:
            errors.append(f"{project_host}: {e}")
            continue

        # Hapus data lama untuk wiki ini hanya jika fetch berhasil
        Contribution.objects.filter(member=member, project=project_host).delete()

        for item in items:
            ts_raw = item.get('timestamp', '')
            try:
                ts = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                ts = timezone.now()

            Contribution.objects.create(
                member=member,
                project=project_host,
                title=item.get('title', ''),
                timestamp=ts,
                comment=item.get('comment', ''),
                sizediff=item.get('sizediff', 0),
            )
            total_saved += 1

    member.total_edits_fetched = total_saved
    member.last_synced_at = timezone.now()
    member.save(update_fields=['total_edits_fetched', 'last_synced_at'])

    return {
        'saved': total_saved,
        'wikis_found': len(wikis),
        'wikis_synced': len(wikis) - len(errors),
        'errors': errors,
        'fallback': fallback_used,
    }
