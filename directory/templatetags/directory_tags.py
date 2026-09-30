from django import template

register = template.Library()


@register.filter
def split_skills(value):
    if not value:
        return []
    return [s.strip() for s in value.split(',') if s.strip()]


# ── Filter tampilan (Serambi) ────────────────────────────────────────────────
# Semua filter di bawah hanya mengubah cara data ditampilkan.
# Nilai yang tersimpan di database dan pilihan `choices` di models.py tidak berubah.

AVAIL_LABELS = {
    'aktif': 'Bisa diajak',
    'sibuk': 'Sedang sibuk',
    'tidak_aktif': 'Tidak aktif',
}


@register.filter
def avail_label(value):
    """Label ketersediaan untuk UI: 'aktif' -> 'Bisa diajak'."""
    return AVAIL_LABELS.get(value, value or '')


ROLE_ICONS = {
    'peserta': 'r-peserta',
    'pelatih': 'r-pelatih',
    'panitia': 'r-panitia',
    'juri': 'r-juri',
    'penanggung_jawab': 'r-pj',
    'narasumber': 'r-narasumber',
    'lainnya': 'r-lainnya',
}


@register.filter
def role_icon(value):
    """ID simbol ikon untuk peran kegiatan."""
    return ROLE_ICONS.get(value, 'r-lainnya')


JENIS_ICONS = {
    'daerah': 'j-daerah',
    'bahasa': 'j-bahasa',
    'proyek': 'j-proyek',
    'klubWiki': 'j-klub',
    'lainnya': 'r-lainnya',
}


@register.filter
def jenis_icon(value):
    """ID simbol ikon untuk jenis komunitas."""
    return JENIS_ICONS.get(value, 'r-lainnya')


SUMBER_LABELS = {
    'otomatis': 'Dari situs WMID',
    'manual-admin': 'Dibuat pengurus',
    'manual-anggota': 'Dicatat anggota',
}


@register.filter
def sumber_label(value):
    """Label sumber kegiatan untuk UI."""
    return SUMBER_LABELS.get(value, value or '')


@register.filter
def initials(value):
    """Dua huruf inisial dari nama tampilan: 'Anggota Contoh' -> 'AC'."""
    if not value:
        return '?'
    words = [w for w in str(value).replace('_', ' ').replace('.', ' ').split() if w]
    if not words:
        return '?'
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()
