from django.db import IntegrityError, models


class Member(models.Model):
    ROLE_USER = 'user'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_USER, 'Anggota'),
        (ROLE_ADMIN, 'Admin'),
    ]

    AUTH_EMAIL  = 'email'
    AUTH_IMPORT = 'import'
    AUTH_CHOICES = [
        (AUTH_EMAIL,  'Email & Kata Sandi'),
        (AUTH_IMPORT, 'Import (akun belum terdaftar)'),
    ]

    AVAIL_AKTIF       = 'aktif'
    AVAIL_SIBUK       = 'sibuk'
    AVAIL_TIDAK_AKTIF = 'tidak_aktif'
    AVAIL_CHOICES = [
        (AVAIL_AKTIF,       'Aktif'),
        (AVAIL_SIBUK,       'Sibuk'),
        (AVAIL_TIDAK_AKTIF, 'Tidak aktif'),
    ]

    # — Autentikasi —
    auth_method = models.CharField(max_length=20, choices=AUTH_CHOICES, default=AUTH_EMAIL)
    password_hash = models.CharField(max_length=128, blank=True, default='')
    wiki_verified = models.BooleanField(default=False)

    # — Data dari Wikimedia OAuth (otomatis) —
    wikimedia_username = models.CharField(max_length=255, unique=True, null=True, blank=True)
    wikimedia_userid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True, default='')
    registered_at = models.DateTimeField(null=True, blank=True)
    edit_count = models.PositiveIntegerField(default=0)
    groups = models.JSONField(default=list)
    total_edits_fetched = models.PositiveIntegerField(default=0)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    raw_profile = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    # — Peran dalam sistem —
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)

    # — Data profil yang diisi anggota sendiri —
    display_name = models.CharField(max_length=200, blank=True, default='')
    bio = models.TextField(max_length=500, blank=True, default='')
    location = models.CharField(max_length=100, blank=True, default='')
    joined_wmid_at = models.DateField(null=True, blank=True)
    skills        = models.TextField(max_length=300, blank=True, default='')
    availability  = models.CharField(max_length=20, choices=AVAIL_CHOICES, default=AVAIL_AKTIF)
    phone         = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['email'],
                condition=models.Q(email__gt=''),
                name='unique_nonempty_email',
            )
        ]

    def __str__(self):
        return self.wikimedia_username or self.display_name or self.email or f'Member #{self.pk}'

    @property
    def display_label(self):
        """Nama yang ditampilkan di UI."""
        return (self.display_name
                or self.wikimedia_username
                or (self.email.split('@')[0] if self.email else None)
                or f'Anggota #{self.pk}')

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN


class Komunitas(models.Model):
    JENIS_CHOICES = [
        ('daerah',   'Komunitas Daerah'),
        ('bahasa',   'Komunitas Bahasa'),
        ('proyek',   'Komunitas Proyek'),
        ('klubWiki', 'Klub Wiki'),
        ('lainnya',  'Lainnya'),
    ]

    slug              = models.SlugField(max_length=200, unique=True)
    kode              = models.CharField(max_length=10, unique=True, blank=True, default='')
    nama_komunitas    = models.CharField(max_length=200)
    jenis_komunitas   = models.CharField(max_length=50, choices=JENIS_CHOICES, blank=True)
    narahubung        = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='komunitas_narahubung')
    logo              = models.URLField(max_length=500, blank=True, default='')
    deskripsi         = models.TextField(blank=True, default='')
    pranala_informasi = models.URLField(max_length=500, blank=True, default='')
    latitude          = models.FloatField(null=True, blank=True)
    longitude         = models.FloatField(null=True, blank=True)
    is_active         = models.BooleanField(default=True)
    synced_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nama_komunitas']
        verbose_name_plural = 'komunitas'

    def __str__(self):
        return self.nama_komunitas

    def save(self, *args, **kwargs):
        if not self.kode:
            self.kode = self._generate_kode()
        for _ in range(5):
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.kode = self._generate_kode()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_kode():
        n = Komunitas.objects.count() + 1
        kode = f'K{n:03d}'
        while Komunitas.objects.filter(kode=kode).exists():
            n += 1
            kode = f'K{n:03d}'
        return kode

    @property
    def jenis_label(self):
        return dict(self.JENIS_CHOICES).get(self.jenis_komunitas, self.jenis_komunitas)


class KomunitasAnggota(models.Model):
    member    = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='keanggotaan')
    komunitas = models.ForeignKey('Komunitas', on_delete=models.CASCADE, related_name='anggota')
    joined_at = models.DateTimeField(auto_now_add=True)
    added_by  = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='anggota_ditambahkan')

    class Meta:
        unique_together = ('member', 'komunitas')
        ordering = ['komunitas__nama_komunitas']

    def __str__(self):
        return f'{self.member} — {self.komunitas}'


class KomunitasAnggotaPending(models.Model):
    TIPE_GABUNG = 'gabung'
    TIPE_KELUAR = 'keluar'
    TIPE_CHOICES = [
        (TIPE_GABUNG, 'Permintaan gabung'),
        (TIPE_KELUAR, 'Permintaan keluar'),
    ]

    member    = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='komunitas_pending')
    komunitas = models.ForeignKey('Komunitas', on_delete=models.CASCADE, related_name='anggota_pending')
    tipe      = models.CharField(max_length=10, choices=TIPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('member', 'komunitas')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.member} — {self.tipe} {self.komunitas}'


class Kegiatan(models.Model):
    SUMBER_OTOMATIS = 'otomatis'
    SUMBER_ADMIN    = 'manual-admin'
    SUMBER_ANGGOTA  = 'manual-anggota'
    SUMBER_CHOICES  = [
        (SUMBER_OTOMATIS, 'Otomatis (API)'),
        (SUMBER_ADMIN,    'Manual — Admin'),
        (SUMBER_ANGGOTA,  'Manual — Anggota'),
    ]

    JENIS_WIKILATIH   = 'WikiLatih'
    JENIS_KOPDAR      = 'Kopdar'
    JENIS_MAKRAB      = 'Makrab'
    JENIS_MITRA       = 'Mitra'
    JENIS_RAPAT       = 'Rapat'
    JENIS_DANA_WIKI   = 'Dana Wiki'
    JENIS_HIBAH_BUKU  = 'Hibah Buku'
    JENIS_RAPID_FUND  = 'Rapid Fund'
    JENIS_LAINNYA     = 'Lainnya'
    JENIS_CHOICES = [
        (JENIS_WIKILATIH,  'WikiLatih'),
        (JENIS_KOPDAR,     'Kopdar'),
        (JENIS_MAKRAB,     'Makrab'),
        (JENIS_MITRA,      'Mitra'),
        (JENIS_RAPAT,      'Rapat'),
        (JENIS_DANA_WIKI,  'Dana Wiki'),
        (JENIS_HIBAH_BUKU, 'Hibah Buku'),
        (JENIS_RAPID_FUND, 'Rapid Fund'),
        (JENIS_LAINNYA,    'Lainnya'),
    ]
    JENIS_VALUES = [c[0] for c in JENIS_CHOICES]

    kode              = models.CharField(max_length=20, unique=True, editable=False)
    judul             = models.CharField(max_length=255)
    deskripsi         = models.TextField(blank=True, default='')
    tanggal_mulai     = models.DateTimeField()
    tanggal_selesai   = models.DateTimeField()
    lokasi            = models.CharField(max_length=255, blank=True, default='')
    komunitas         = models.ManyToManyField('Komunitas', blank=True, related_name='kegiatan')
    sumber            = models.CharField(max_length=20, choices=SUMBER_CHOICES, default=SUMBER_ADMIN)
    jenis_kegiatan    = models.CharField(max_length=20, choices=JENIS_CHOICES, blank=True, default='')
    external_slug     = models.CharField(max_length=255, null=True, blank=True, unique=True)
    dibuat_oleh       = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='kegiatan_dibuat')
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-tanggal_mulai']
        verbose_name_plural = 'kegiatan'

    def __str__(self):
        return f'[{self.kode}] {self.judul}'

    def save(self, *args, **kwargs):
        if not self.kode:
            self.kode = self._generate_kode()
        for _ in range(5):
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                self.kode = self._generate_kode()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_kode():
        from datetime import date
        year = date.today().year
        prefix = f'KGT-{year}-'
        last = Kegiatan.objects.filter(kode__startswith=prefix).order_by('-kode').first()
        if last:
            last_num = int(last.kode.split('-')[-1])
            return f'{prefix}{str(last_num + 1).zfill(4)}'
        return f'{prefix}0001'

    @property
    def sudah_selesai(self):
        from django.utils import timezone
        return self.tanggal_selesai < timezone.now()

    @property
    def sedang_berlangsung(self):
        from django.utils import timezone
        now = timezone.now()
        return self.tanggal_mulai <= now <= self.tanggal_selesai


class SkippedExternalSlug(models.Model):
    """Slug kegiatan API yang sudah dihapus manual — tidak akan ditarik ulang saat sync."""
    slug       = models.CharField(max_length=255, unique=True)
    skipped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.slug


class KegiatanLink(models.Model):
    kegiatan   = models.ForeignKey('Kegiatan', on_delete=models.CASCADE, related_name='links')
    judul_link = models.CharField(max_length=255)
    url        = models.URLField(max_length=500, blank=True, default='')
    urutan     = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['urutan']

    def __str__(self):
        return f'{self.kegiatan.kode} — {self.judul_link}'


class KegiatanAnggota(models.Model):
    ROLE_CHOICES = [
        ('peserta',           'Peserta'),
        ('pelatih',           'Pelatih'),
        ('panitia',           'Panitia'),
        ('juri',              'Juri'),
        ('penanggung_jawab',  'Penanggung Jawab'),
        ('narasumber',        'Narasumber'),
        ('lainnya',           'Lainnya'),
    ]
    STATUS_MENUNGGU      = 'menunggu'
    STATUS_TERVERIFIKASI = 'terverifikasi'
    STATUS_DITOLAK       = 'ditolak'
    STATUS_CHOICES = [
        (STATUS_MENUNGGU,      'Menunggu verifikasi'),
        (STATUS_TERVERIFIKASI, 'Terverifikasi'),
        (STATUS_DITOLAK,       'Ditolak'),
    ]

    kegiatan    = models.ForeignKey('Kegiatan', on_delete=models.CASCADE, related_name='peserta')
    member      = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='riwayat_kegiatan')
    role        = models.CharField(max_length=20, choices=ROLE_CHOICES, default='peserta')
    catatan     = models.CharField(max_length=200, blank=True, default='')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_MENUNGGU)
    added_by    = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='kegiatan_anggota_ditambahkan')
    verified_by = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='kegiatan_anggota_diverifikasi')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('kegiatan', 'member')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.member} — {self.kegiatan.kode} ({self.get_role_display()})'

    @property
    def role_css(self):
        return self.role.replace('_', '-')


class Contribution(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='contributions')
    project = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    timestamp = models.DateTimeField()
    comment = models.TextField(blank=True, default='')
    sizediff = models.IntegerField(default=0)  # perubahan byte: positif = tambah, negatif = hapus

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.member.wikimedia_username} — {self.title}'
