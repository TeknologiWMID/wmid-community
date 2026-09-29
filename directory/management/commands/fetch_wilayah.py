import json
import os
import time
import requests
from django.core.management.base import BaseCommand

PROVINCES_URL = 'https://www.emsifa.com/api-wilayah-indonesia/api/provinces.json'
REGENCIES_URL = 'https://www.emsifa.com/api-wilayah-indonesia/api/regencies/{id}.json'

ABBREVS = {'Dki', 'Di', 'Ntb', 'Ntt', 'Nad'}

def _title(s):
    return ' '.join(w.upper() if w.title() in ABBREVS else w.title() for w in s.split())

def _format_regency(name):
    t = _title(name)
    if t.startswith('Kabupaten '):
        return 'Kab. ' + t[10:]
    return t


class Command(BaseCommand):
    help = 'Fetch Indonesian province/regency data from emsifa API and save locally'

    def handle(self, *args, **options):
        self.stdout.write('Mengambil data provinsi...')
        try:
            provinces = requests.get(PROVINCES_URL, timeout=15).json()
        except Exception as e:
            self.stderr.write(f'Gagal ambil provinsi: {e}')
            return

        result = {'provinces': [], 'regencies': {}}

        for prov in provinces:
            name = _title(prov['name'])
            result['provinces'].append({'id': prov['id'], 'name': name})
            self.stdout.write(f'  {name}...')
            try:
                regs = requests.get(REGENCIES_URL.format(id=prov['id']), timeout=15).json()
                result['regencies'][prov['id']] = [
                    {'id': r['id'], 'name': _format_regency(r['name'])}
                    for r in regs
                ]
            except Exception as e:
                self.stderr.write(f'  Gagal {name}: {e}')
                result['regencies'][prov['id']] = []
            time.sleep(0.05)

        out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'wilayah.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        total_reg = sum(len(v) for v in result['regencies'].values())
        self.stdout.write(self.style.SUCCESS(
            f'Selesai: {len(result["provinces"])} provinsi, {total_reg} kab/kota → {out_path}'
        ))
