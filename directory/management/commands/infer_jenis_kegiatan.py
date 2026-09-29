from django.core.management.base import BaseCommand

from directory.models import Kegiatan

RULES = [
    ('WikiLatih',  ['wikilatih']),
    ('Kopdar',     ['kopdar']),
    ('Makrab',     ['makrab']),
    ('Rapat',      ['rapat']),
    ('Mitra',      ['mitra']),
    ('Dana Wiki',  ['dana wiki']),
    ('Hibah Buku', ['hibah buku']),
    ('Rapid Fund', ['rapid fund', 'rapidfund']),
]


def infer(judul):
    lower = judul.lower()
    for jenis, keywords in RULES:
        if any(kw in lower for kw in keywords):
            return jenis
    return ''


class Command(BaseCommand):
    help = 'Isi jenis_kegiatan berdasarkan kata kunci di judul (hanya yang masih kosong)'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
                            help='Timpa semua, termasuk yang sudah terisi')

    def handle(self, *args, **options):
        overwrite = options['all']
        qs = Kegiatan.objects.all() if overwrite else Kegiatan.objects.filter(jenis_kegiatan='')

        updated = skipped = 0
        for kg in qs:
            jenis = infer(kg.judul)
            if jenis:
                kg.jenis_kegiatan = jenis
                kg.save(update_fields=['jenis_kegiatan'])
                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Selesai: {updated} diperbarui, {skipped} tidak cocok (dibiarkan kosong).'
        ))
