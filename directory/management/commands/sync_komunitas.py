import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from directory.models import Komunitas

TIMEOUT = 15


class Command(BaseCommand):
    help = 'Sinkronisasi data komunitas dari dashboard.wikimedia.or.id'

    def handle(self, *args, **options):
        self.stdout.write('Mengambil data komunitas...')
        api_url = settings.DASHBOARD_API_BASE_URL + '/communities'

        try:
            resp = requests.get(api_url, timeout=TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as e:
            self.stderr.write(f'Gagal fetch API: {e}')
            return
        except ValueError:
            self.stderr.write('Response bukan JSON valid.')
            return

        if not payload.get('success'):
            self.stderr.write(f'API mengembalikan success=false: {payload}')
            return

        raw = payload.get('data', [])
        # handle paginated (Laravel paginator wraps data in .data.data)
        if isinstance(raw, dict) and 'data' in raw:
            raw = raw['data']

        created = updated = skipped = 0
        FIELDS = ['nama_komunitas', 'jenis_komunitas', 'logo', 'deskripsi',
                  'pranala_informasi', 'is_active']

        for item in raw:
            slug = item.get('slug', '').strip()
            if not slug:
                skipped += 1
                continue

            defaults = {
                'nama_komunitas':    (item.get('nama_komunitas') or '').strip()[:200],
                'jenis_komunitas':   (item.get('jenis_komunitas') or '').strip()[:50],
                'logo':              (item.get('logo_url') or '')[:500],
                'deskripsi':         (item.get('deskripsi') or '').strip(),
                'pranala_informasi': (item.get('pranala') or '')[:500],
                'latitude':          float(item['latitude']) if item.get('latitude') else None,
                'longitude':         float(item['longitude']) if item.get('longitude') else None,
                'is_active':         bool(item.get('is_active', True)),
            }

            obj, was_created = Komunitas.objects.update_or_create(
                slug=slug, defaults=defaults
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Selesai: {created} baru, {updated} diperbarui, {skipped} dilewati.'
            )
        )
