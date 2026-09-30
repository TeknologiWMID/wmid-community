# Design Brief: Redesign Direktori Anggota WMID

Versi 1 · 30 September 2026 · Tahap perencanaan (belum implementasi)

Dokumen ini merangkum rencana redesign tampilan Direktori Anggota Wikimedia Indonesia. Isinya: audit sistem saat ini, arah desain terpilih, design system, inventori komponen, pola layout mobile, dan panduan copywriting. Tiga mockup HTML statis ada di folder `mockups/` sebagai ilustrasi konsep.

## 0. Batasan yang dipegang

Redesign ini hanya menyentuh lapisan tampilan dan teks. Yang **tidak** berubah:

- Alur kerja (user flow), urutan langkah, dan tujuan setiap tombol atau formulir.
- Fitur, logika bisnis, validasi, dan aturan verifikasi.
- Struktur data (model, field, pilihan nilai yang disimpan) dan URL.
- Peran dan hak akses: `user` (Anggota) dan `admin`.

Yang boleh berubah: HTML/CSS template, susunan visual di dalam halaman, ikon, ilustrasi, serta teks yang terlihat pengguna (label, judul, placeholder, pesan `messages.*` di views, teks di JavaScript).

Beberapa ide yang muncul selama audit memang butuh perubahan logika. Semuanya dikumpulkan terpisah di **Bagian 8 (Di luar cakupan)** supaya tidak tercampur.

---

## 1. Audit sistem saat ini

### 1.1 Peta halaman dan alur

**Publik dan autentikasi**

| Halaman | URL | Template | Fungsi |
|---|---|---|---|
| Beranda | `/` | `index.html` | Pintu masuk. Tamu melihat tombol Masuk, anggota melihat tombol Profil. |
| Masuk | `/masuk/` | `login.html` | Email + kata sandi. Batas percobaan: terlalu banyak gagal, tunggu 1 menit. |
| Daftar | `/daftar/` | `register.html` | Nama, email, kata sandi dua kali. Jika email cocok dengan akun hasil impor, akun itu diklaim beserta riwayatnya. |
| Tidak ditemukan | (404) | `404.html` | Halaman mandiri, tidak memakai `base.html`. |

**Anggota (peran `user`, juga bisa diakses admin)**

| Halaman | URL | Template | Fungsi |
|---|---|---|---|
| Profil saya | `/profil/` | `profile.html` | Identitas, kartu "lengkapi profil", hasil sinkronisasi, bio/keahlian/HP, riwayat kegiatan (termasuk tarik permintaan yang menunggu), komunitas, statistik kontribusi wiki, suntingan per proyek, 10 suntingan terbaru. |
| Ubah profil | `/profil/edit/` | `profile_edit.html` | Form profil (nama, bio, ketersediaan, keahlian, email jika bukan akun email, HP, provinsi, kota, tanggal gabung WMID). Panel akun Wikimedia. Panel komunitas: cari & minta gabung, minta keluar, batalkan permintaan. |
| Catat kegiatan | `/profil/kegiatan/catat/` | `riwayat_catat.html` | Cari kegiatan resmi (autocomplete) atau ketik kegiatan lain. Kegiatan lain membuka field tanggal, lokasi, jenis, komunitas terkait. Peran dan keterangan. Dikirim untuk diverifikasi. |
| Sinkronkan | `/profil/sinkron/` | (aksi) | Tarik ulang kontribusi wiki. Jeda minimal 5 menit. |
| Hubungkan Wikimedia | `/oauth/login/` | (aksi) | OAuth 2.0. Hanya untuk menautkan akun yang sudah masuk, bukan cara masuk. |
| Komunitas | `/komunitas/` | `komunitas.html` | Tampilan kartu atau peta (Leaflet). Admin melihat tombol Sinkronkan. |
| Detail komunitas | `/komunitas/<slug>/` | `komunitas_detail.html` | Info, statistik (anggota, kegiatan), daftar anggota dengan narahubung di atas, kegiatan terkait. |
| Kegiatan | `/kegiatan/` | `kegiatan_list.html` | Kartu kegiatan dengan status (akan datang, berlangsung, selesai), paginasi. Admin melihat tombol Sinkron API. |
| Detail kegiatan | `/kegiatan/<kode>/` | `kegiatan_detail.html` | Tanggal, lokasi, komunitas, deskripsi, tautan. |

**Pengurus (peran `admin`)**

| Halaman | URL | Template | Fungsi |
|---|---|---|---|
| Ringkasan | `/admin/` | `admin_dashboard.html` | Tiga angka (anggota, komunitas, kegiatan), grafik kegiatan dan anggota baru 12 bulan, grafik status ketersediaan, 5 kegiatan terbaru, 5 komunitas terbesar. |
| Anggota | `/admin/anggota/` | `admin_anggota.html` | Cari (nama, email, lokasi, username), saring ketersediaan & komunitas, urutkan (nama, kegiatan terbanyak/tersedikit, baru bergabung), tabel 11 kolom, paginasi 25, ekspor CSV/XLSX dengan pilih kolom dan pratinjau. |
| Detail anggota | `/admin/anggota/<id>/` | `admin_anggota_detail.html` | Semua data profil, komunitas, data Wikimedia, tabel riwayat kegiatan. |
| Ubah anggota | `/admin/anggota/<id>/edit/` | `admin_anggota_edit.html` | Ubah ketersediaan dan peran, centang komunitas, ubah peran/status tiap riwayat, hapus riwayat, tambah kegiatan. Admin tidak bisa mengubah perannya sendiri. |
| Komunitas | `/admin/komunitas/` | `admin_komunitas.html` | Cari, saring jenis, urutkan, tabel 15 kolom (termasuk 9 kolom jumlah per jenis kegiatan), ekspor. |
| Detail komunitas | `/admin/komunitas/<slug>/` | `admin_komunitas_detail.html` | Info, anggota + jumlah kegiatan terverifikasi, kegiatan + ringkasan per jenis. |
| Ubah komunitas | `/admin/komunitas/<slug>/edit/` | `admin_komunitas_edit.html` | Nama, jenis, aktif, narahubung (cari anggota), deskripsi, URL logo, pranala. Tambah/keluarkan anggota, tambah/lepas kegiatan. |
| Kegiatan | `/admin/kegiatan/` | `admin_kegiatan_data.html` | Cari, saring jenis, urutkan, tabel 10 kolom, ekspor. |
| Detail kegiatan | `/admin/kegiatan/<kode>/` | `admin_kegiatan_detail.html` | Info, tabel peserta berpaginasi, wizard **impor peserta** 3 langkah (unggah file, petakan kolom, pilih baris & peran) + hasil. |
| Ubah kegiatan | `/admin/kegiatan/<kode>/edit/` | `admin_kegiatan_edit.html` | Judul, tanggal, lokasi, jenis, deskripsi. Tambah/lepas komunitas. Hapus peserta. |
| Verifikasi | `/admin/verifikasi/` | `admin_kegiatan_list.html` | Antrean permintaan gabung/keluar komunitas dan pendaftaran kegiatan. Terima atau tolak. Tolak pendaftaran kegiatan = entri dihapus. |

**Alur utama yang harus tetap identik**

1. *Daftar → Profil*: daftar dengan email, langsung masuk ke profil. Jika email cocok dengan akun impor, riwayat lama otomatis tersambung.
2. *Masuk → Hubungkan Wikimedia → Sinkron*: OAuth hanya dari profil; setelah terhubung, kontribusi ditarik otomatis.
3. *Catat kegiatan → Menunggu → Diverifikasi pengurus*: anggota bisa menarik permintaan selama masih menunggu.
4. *Minta gabung/keluar komunitas → Menunggu → Diterima/ditolak pengurus*: dilakukan dari halaman Ubah profil.
5. *Pengurus mencari orang*: halaman Anggota, cari + saring + urutkan menurut jumlah kegiatan terverifikasi, buka detail, ekspor.
6. *Pengurus mengelola kegiatan*: sinkron dari API, impor peserta dari Excel/CSV, ubah data, hapus peserta.

### 1.2 Temuan visual

- **Beranda masih berisi lorem ipsum** dan mosaik kotak dekoratif. Halaman pertama yang dilihat tamu tidak menjelaskan apa-apa.
- **Tidak ada sistem komponen bersama.** `base.html` punya token dasar, tapi setiap halaman admin mendefinisikan ulang tabel, pil status, avatar, dan modal. Banyak `style="..."` inline dan `onmouseover`.
- **Tabel admin terlalu lebar**: 11 kolom (Anggota), 15 kolom (Komunitas), 10 kolom (Kegiatan). Di ponsel hanya bisa digeser ke samping, dan kolom yang paling menentukan (jumlah kegiatan terverifikasi) terselip di tengah.
- **Rekam jejak kurang terlihat.** Tujuan sistem adalah mencari pelatih, juri, panitia, narasumber. Di profil, peran tampil sebagai lencana warna-warni kecil; di daftar anggota hanya angka.
- **Warna tanpa sistem**: 4 warna jenis komunitas (biru, hijau, ungu, oranye), 7 warna titik peran, merah untuk "Sibuk" dan kuning untuk "Tidak aktif" (terbalik dari intuisi: sibuk bukan bahaya).
- **Mobile**: menu hamburger tanpa label berisi 6 tautan; tidak ada navigasi yang bisa dijangkau jempol; modal ekspor dan impor tidak dirancang untuk layar kecil; peta komunitas punya panel samping yang menutupi peta.
- **Grafik tanpa pertanyaan yang jelas**: donat "Status anggota" sulit dibandingkan; judul grafik "Kegiatan berlangsung" ambigu.
- **Identitas lemah**: "WMID Directory" (header) vs "WMID Community" (404) vs "Direktori Anggota WMID" (judul tab).

### 1.3 Temuan copywriting

- Istilah ganda: *Surel* dan *Email*; *Masuk* dan *login/logout*; *Sinkron API*, *Sinkronkan*, *Sync*; *Import* dan *Impor*; *Hubungkan Wikimedia* dan *Konfirmasi dengan Wikimedia*; *Edit profil* dan *Ubah*.
- Sapaan campur: "kamu" di halaman, "Anda" di pesan keluar ("Anda telah logout").
- Pesan teknis sampai ke pengguna: "Validasi state gagal (kemungkinan serangan CSRF)", "Parameter "code" tidak ditemukan dalam callback", "Gagal menukar token", "CentralAuth kosong, dicek satu per satu", "Gagal fetch API", "Net byte".
- Tombol "Hapus" dipakai untuk tiga hal berbeda: menghapus riwayat (permanen), mengeluarkan anggota dari komunitas, dan melepas kaitan kegiatan-komunitas.
- Kata "Keluar" dipakai untuk keluar akun dan keluar komunitas.
- Empty state hanya menyatakan kosong ("Belum ada data.") tanpa langkah berikutnya.
- "Akses ditolak." tanpa penjelasan siapa yang boleh.

---

## 2. Arah desain terpilih: **Serambi**

Gabungan arah *Kampung Wiki* (hangat, untuk halaman anggota) dan *Meja Pengurus* (padat, untuk halaman pengurus), dalam satu sistem token.

**Nama dan ide.** Serambi adalah ruang depan rumah tempat orang bertamu dan bertemu. Direktori ini memang tempat anggota "memperkenalkan diri" lewat rekam jejaknya, dan tempat pengurus mencari orang. Di halaman anggota, rasanya seperti serambi: longgar, wajah dan peran dulu. Di halaman pengurus, rasanya seperti meja kerja di serambi yang sama: padat, cepat dipindai, kontrol rapat.

**Satu motif identitas: cap verifikasi.** Entri riwayat yang sudah diverifikasi pengurus diberi cap bulat (lingkaran ganda dengan tanda centang), seperti stempel pada surat keterangan kegiatan. Motif ini hanya muncul di tempat yang berarti "sudah diperiksa pengurus": riwayat terverifikasi, antrean yang bersih, dan hasil impor yang berhasil. Tidak dipakai sebagai hiasan.

**Tone visual.** Kredibel tanpa kaku. Netral berbias teal, satu warna utama (teal), satu aksen (kuning matahari) yang muncul sekali per layar untuk hal yang butuh perhatian pengurus.

**Tiga pertanyaan penentu per layar.** Sebelum menata halaman, jawab: siapa yang memakai, keputusan apa yang diambil di sini, dan informasi apa yang menentukan keputusan itu. Informasi penentu tampil paling awal dan paling besar.

| Halaman | Keputusan utama | Informasi penentu |
|---|---|---|
| Profil | "Apa yang perlu saya lengkapi atau catat?" | Kelengkapan profil, riwayat + status verifikasi |
| Anggota (pengurus) | "Siapa yang cocok diajak?" | Jumlah riwayat terverifikasi, ketersediaan, keahlian |
| Verifikasi | "Terima atau tolak?" | Siapa, peran apa, di kegiatan apa, keterangan |
| Ringkasan | "Ada yang perlu ditangani?" | Jumlah antrean verifikasi, aktivitas terbaru |

---

## 3. Design system

Token lengkap ada di `mockups/serambi.css`. Nama token bisa langsung dipakai saat implementasi.

### 3.1 Warna

Rasio kontras dihitung dengan rumus WCAG 2.x (bukan perkiraan).

| Token | Terang | Gelap | Pemakaian | Kontras |
|---|---|---|---|---|
| `--bg` | `#F1F4F2` | `#0F1817` | Latar halaman | |
| `--surface` | `#FFFFFF` | `#162220` | Panel, tabel, kartu | |
| `--subtle` | `#E6ECE9` | `#1D2C2A` | Chip netral, hover baris | |
| `--line` | `#D3DCD8` | `#2A3A38` | Garis pemisah (dekoratif) | |
| `--line-strong` | `#7C8E8A` | `#6B807B` | Tepi input, tombol sekunder | 3.45:1 / 3.89:1 (non-teks) |
| `--ink` | `#15282A` | `#E4EDEA` | Teks utama | 15.3:1 / 13.7:1 |
| `--ink-2` | `#4A5C59` | `#BFCFCB` | Teks sekunder | 7.1:1 |
| `--muted` | `#566A66` | `#A3B6B2` | Meta, keterangan | 5.2:1 di `--bg` / 7.7:1 |
| `--primary` | `#0E5E5A` | `#6FCBBE` | Tombol utama, tautan, fokus | 7.6:1 / 8.5:1 |
| `--primary-soft` | `#DCEDEA` | `#173532` | Latar terpilih, avatar | teal di atasnya 6.3:1 |
| `--accent` | `#F5C84C` | `#F5C84C` | **Satu momen per layar** | `--ink` di atasnya 9.7:1 |
| `--success` | `#1D6B43` | `#7AD3A0` | Terverifikasi, cap, "Bisa diajak" | 6.5:1 / 9.1:1 |
| `--warning` | `#8A5A00` | `#F2C45A` | Menunggu verifikasi, akun impor | 5.9:1 / 10:1 |
| `--danger` | `#B42318` | `#FF9A8C` | Hapus, ditolak, error | 6.6:1 / 8:1 |
| `--busy` | `#B07800` | `#E0A63A` | Titik "Sedang sibuk" | 3.8:1 (non-teks) |
| `--idle` | `#6F827E` | `#8FA39F` | Titik "Tidak aktif" | 4.1:1 (non-teks) |

Aturan warna:

- **Palet aktif = netral + teal + satu aksen.** Warna status (success/warning/danger) hanya untuk status, tidak dihitung sebagai warna merek.
- **Aksen kuning** hanya untuk: angka antrean verifikasi di tab Pengurus, dan satu sorotan di beranda. Selalu sebagai isian dengan teks `--ink`, tidak pernah sebagai warna teks.
- **Jenis komunitas dan peran kegiatan tidak lagi diberi warna berbeda.** Keduanya memakai chip netral + ikon. Warna disimpan untuk status, supaya "hijau" selalu berarti terverifikasi.
- **Ketersediaan** dibedakan warna *dan* bentuk: Bisa diajak (titik hijau penuh), Sedang sibuk (titik kuning tua penuh), Tidak aktif (lingkaran kosong abu-abu). Tetap terbaca bagi pengguna buta warna.
- **Mode gelap** mengikuti pengaturan sistem, dengan toggle manual di menu akun. Semua komponen memakai token, tidak ada warna literal.

### 3.2 Tipografi

- **Plus Jakarta Sans** (400, 500, 600, 700, 800) untuk seluruh UI. Alasannya: huruf ini lahir dari proyek identitas kota Jakarta, humanis, bentuk angkanya jelas, dan mendukung aksara Latin dengan diakritik untuk nama-nama daerah. Satu keluarga cukup; hierarki dibangun dari bobot dan ukuran.
- **IBM Plex Mono** (500) khusus data yang memang kode: `KGT-2026-0012`, `K014`, slug, username di tabel pengurus. Tujuannya agar kode mudah dibaca karakter per karakter dan disalin. Tidak dipakai untuk judul atau hiasan.

| Token | Ukuran | Pemakaian |
|---|---|---|
| `--t-36` | 36 px | Judul beranda (desktop) |
| `--t-28` | 28 px | Judul halaman, nama di profil (desktop) |
| `--t-22` | 22 px | Judul halaman & nama (ponsel), angka statistik |
| `--t-18` | 18 px | Judul bagian |
| `--t-16` | 16 px | Teks isi, input (mencegah zoom otomatis di iOS) |
| `--t-14` | 14 px | Isi tabel pengurus, tombol, meta |
| `--t-13` | 13 px | Chip, keterangan kecil |
| `--t-12` | 12 px | Kepala kolom tabel, label hitungan. Batas terkecil. |

Tinggi baris isi 1,55; judul 1,2. Judul memakai `text-wrap: balance`. Angka di tabel dan statistik memakai `tabular-nums`. Label huruf kapital hanya untuk dua hal kecil (lencana ADMIN dan tipe permintaan GABUNG/KELUAR), dengan spasi huruf ringan.

### 3.3 Spasi, grid, dan kepadatan

- **Skala spasi basis 4**: 4, 8, 12, 16, 20, 24, 32, 40, 56. Jarak antar bagian (24 sampai 32) sengaja lebih besar dari jarak di dalam bagian (8 sampai 16), supaya kelompok terbaca.
- **Lebar konten**: 1200 px untuk halaman pengurus, 1040 px untuk profil, 760 px untuk form dan antrean verifikasi (mata bergerak lurus ke bawah).
- **Titik patah dipilih dari konten, bukan dari ukuran perangkat**:
  - `720px`: di bawahnya navigasi pindah ke bawah, tabel berubah jadi daftar baris, form jadi satu kolom.
  - `960px`: di bawahnya kolom samping profil turun ke bawah kolom utama.
  - `1100px`: di bawahnya kolom sekunder tabel (Lokasi, Kontak) disembunyikan; datanya tetap ada di detail dan ekspor.
- **Dua kepadatan**:
  - *Serambi* (anggota): baris daftar 56 px, padding panel 24 px.
  - *Meja* (pengurus, kelas `.density-meja`): baris tabel sekitar 44 px, padding sel 10 x 12 px.
- **Target sentuh minimal 44 x 44 px** di semua kepadatan. Di ponsel, tombol keputusan (Terima/Tolak) 48 px.

### 3.4 Bentuk dan elevasi

- **Tiga radius saja**: 6 px (kontrol: tombol, input, chip, wadah tabel), 12 px (panel dan lembar bawah), bulat penuh (avatar dan titik status).
- **Bayangan hanya untuk yang melayang**: menu dropdown, modal, lembar bawah, toast. Panel di halaman memakai garis tipis, tanpa bayangan.
- **Tanpa** gradien, blur, glow, garis warna di tepi kiri kartu, atau pola latar.

### 3.5 Ikon

- **Gaya**: garis 1,75 px pada kisi 24 px, ujung membulat, dengan **satu bidang isi lembut** (`--primary-soft`) pada bagian utama ikon. Bidang isi ini yang membuat set terasa milik Serambi, bukan set standar.
- **Dasar**: gambar sendiri atau adaptasi dari set berlisensi terbuka (misalnya Tabler Icons, MIT), lalu diseragamkan ketebalan dan bidang isinya. Satu sprite SVG di `base.html`.
- **Aturan pakai**: ikon selalu bersama label teks, kecuali untuk aksi yang universal (tutup, cari, halaman sebelumnya/berikutnya) dan itu wajib punya `aria-label`. Tidak ada ikon hiasan di judul bagian.
- **Set yang dibutuhkan** (sekitar 30): navigasi (profil, komunitas, kegiatan, pengurus), aksi (cari, saring, tambah, ubah, sinkron, unduh/ekspor, unggah/impor, tutup, tautan luar), data (lokasi, email, telepon, akun wiki, kalender), status (centang, jam menunggu, silang ditolak), dan **7 ikon peran kegiatan**:

| Peran | Ikon |
|---|---|
| Peserta | Orang |
| Pelatih | Papan presentasi |
| Panitia | Papan klip berisi daftar |
| Juri | Timbangan |
| Narasumber | Mikrofon |
| Penanggung jawab | Bendera |
| Lainnya | Tiga titik |

- **Jenis komunitas** juga diberi ikon: Daerah (penanda lokasi), Bahasa (gelembung percakapan), Proyek (papan klip), Klub Wiki (buku), Lainnya (tiga titik).

### 3.6 Ilustrasi

Ilustrasi dipakai sedikit, hanya di tempat yang sepi teks: beranda, empty state utama, halaman 404, dan hasil impor. Gayanya **ilustrasi garis** dengan ketebalan sama seperti ikon (tapi lebih besar), warna teal dengan satu bidang kuning, menggambarkan kegiatan WMID yang nyata:

1. **Beranda**: meja pelatihan dengan beberapa laptop dan papan tulis bertuliskan "WikiLatih". Menggambarkan kegiatan yang dicatat sistem.
2. **Antrean verifikasi kosong**: cap verifikasi besar di atas selembar catatan.
3. **Riwayat kegiatan kosong**: buku catatan terbuka dengan satu baris bertanda cap.
4. **Tidak ada hasil pencarian**: kaca pembesar di atas deretan kartu nama kosong.
5. **404**: rambu jalan yang menunjuk dua arah (Kembali, Beranda).

Tidak ada karakter 3D, figur generik dari pustaka ilustrasi gratis, atau logo Wikimedia yang diubah. **Logo**: pakai logo resmi Wikimedia Indonesia dari tim komunikasi. Redesign ini tidak membuat logo baru.

### 3.7 Gerak

Hanya tiga gerak, semua di bawah 200 ms, dan mati saat `prefers-reduced-motion`:

- Lembar bawah dan modal muncul dari bawah/memudar (160 ms).
- Toast masuk dari bawah di ponsel, dari kanan atas di desktop (tetap seperti sekarang), dengan jeda tertunda saat disentuh atau diarahkan kursor.
- Cap verifikasi "menekan" sekali (skala 1,08 ke 1) saat pengurus menekan Terima.

---

## 4. Prinsip dasar komponen

### Tombol

| Varian | Pemakaian | Aturan |
|---|---|---|
| Utama (teal penuh) | Aksi utama halaman: Simpan perubahan, Catat kegiatan, Terima | Maksimal satu per area |
| Sekunder (garis) | Aksi pendamping: Batal, Ubah profil, Ekspor data, Tolak | |
| Tenang (teks teal) | Aksi ringan: Hapus saringan, Gabung, Lihat semua | |
| Bahaya (merah penuh) | Hanya tombol konfirmasi di modal hapus | Tidak pernah di halaman langsung |
| Bahaya tenang (teks merah) | Pemicu hapus di baris tabel | Membuka modal konfirmasi |

Label tombol = kata kerja + objek bila perlu ("Simpan perubahan", bukan "OK"). Panah dekoratif di tombol dihapus; panah hanya untuk paginasi dan "kembali".

### Form

- Label selalu di atas field, tebal 14 px. Tidak memakai placeholder sebagai pengganti label.
- Petunjuk (hint) di bawah field, 13 px, `--muted`.
- Penanda wajib: kata "(wajib)" setelah label hanya pada form yang campuran; di form yang semua wajib (Masuk, Daftar), tidak ditandai.
- Error: pesan dari server tetap tampil sebagai toast (alur tidak berubah), dan **juga** diulang di atas form sebagai ringkasan jika halaman dirender ulang. Tepi field bermasalah merah bila server mengirim penanda field (lihat Bagian 8 jika belum ada).
- Input 16 px di ponsel, tinggi minimal 44 px, tepi `--line-strong` (kontras 3,45:1).
- **Kombobox pencarian** (kegiatan di Catat kegiatan, komunitas, narahubung, anggota, kegiatan di halaman ubah): satu pola yang sama dengan `role="combobox"`, daftar hasil maksimal 8, bisa dipilih dengan panah dan Enter, pesan "Tidak ada yang cocok" bila kosong.
- **Pilihan ketersediaan**: tiga kartu radio sejajar dengan titik status dan label baru.
- **Input keahlian (tag)**: chip netral, tombol hapus per chip minimal 32 px dengan area sentuh 44 px.

### Tabel (kepadatan Meja)

- Kolom diurutkan menurut keputusan: identitas, lalu **angka penentu** (riwayat terverifikasi), lalu status, lalu atribut, lalu data kontak.
- Kolom yang sama isinya digabung: "Username Wiki" masuk ke sel Anggota; "Email" + "No. HP" jadi satu kolom "Kontak". Tidak ada data yang hilang.
- Seluruh baris bisa diklik ke detail (menggantikan tombol "Detail" di tiap baris), dengan nama sebagai tautan yang terlihat untuk keyboard dan pembaca layar.
- Sel kosong menulis alasannya dengan singkat ("Belum diisi", "Belum ada") dan bukan tanda "—".
- Angka rata kanan, `tabular-nums`.
- Kepala tabel menempel saat digulir di tabel panjang.

### Chip dan lencana

| Komponen | Bentuk | Contoh |
|---|---|---|
| Chip peran | Chip netral + ikon peran | Pelatih, Juri |
| Chip jenis | Chip netral + ikon jenis | Komunitas Daerah |
| Status verifikasi | Ikon + teks berwarna, tanpa latar | Terverifikasi, Menunggu verifikasi, Ditolak |
| Cap | Lingkaran ganda + centang | Di samping entri riwayat terverifikasi |
| Ketersediaan | Titik + teks | Bisa diajak |
| Status kegiatan | Teks + titik (akan datang: garis; berlangsung: hijau berdenyut sekali saat dimuat, lalu diam; selesai: abu-abu) | Berlangsung |
| Lencana peran sistem | Garis teal, huruf kapital kecil | ADMIN |
| Akun impor | Latar `--warning-soft`, teks `--warning` | Belum mendaftar |
| Hitungan antrean | Isian `--accent` | 5 |

### Panel dan kartu

- **Panel** (latar putih, garis tipis, radius 12) untuk mengelompokkan satu topik.
- **Kartu yang bisa diklik** (komunitas, kegiatan) memberi umpan balik hover dan `:active`, dan seluruh kartu adalah satu tautan.
- **Nudge** (kartu "Profilmu belum lengkap") memakai latar `--primary-soft`, bukan panel putih, supaya jelas beda fungsi.

### Lapisan melayang

- **Modal konfirmasi hapus** (sudah ada, tetap dipakai): judul menyebut objek, isi menyebut akibatnya, tombol "Batal" dan tombol merah yang mengulang kata kerjanya ("Hapus riwayat", "Keluarkan", "Lepaskan").
- **Modal ekspor** dan **wizard impor**: di desktop tetap modal; di ponsel jadi layar penuh dengan tombol aksi menempel di bawah.
- **Lembar bawah** (ponsel): untuk saringan, menu akun, dan detail peta komunitas.
- **Toast**: tetap dari `messages`, 5 detik, jeda saat disentuh. Di ponsel muncul di atas navigasi bawah.

### Avatar

Inisial dua huruf (sekarang satu huruf). Latar `--primary-soft`, teks teal. Avatar besar di profil memakai latar teal penuh. Tidak ada foto yang diasumsikan.

---

## 5. Inventori komponen dan halaman yang di-redesign

Setiap baris: apa yang ada sekarang, konsep baru, dan penegasan fungsi yang tidak berubah.

### 5.1 Kerangka global

| Komponen | Sekarang | Konsep baru | Fungsi tetap |
|---|---|---|---|
| Header | "WMID Directory", tautan teks, pil akun | Nama "Direktori Anggota" + "Wikimedia Indonesia" di bawahnya (atau logo resmi). Tautan dengan garis bawah tebal untuk halaman aktif. | Tautan yang sama; Pengurus hanya untuk admin |
| Menu akun | Dropdown: Profil saya, Edit profil, Keluar | Dropdown (desktop) / lembar bawah (ponsel): Profil saya, Ubah profil, Tema tampilan, Keluar dari akun | Tujuan sama; toggle tema hanya tampilan |
| Navigasi mobile | Hamburger tanpa label, 6 tautan | Navigasi bawah: Profil, Komunitas, Kegiatan, Pengurus (admin). Ubah profil dan Keluar pindah ke menu akun di kanan atas. | Semua tujuan tetap terjangkau |
| Tab pengurus | Kartu tautan di atas konten | Bar tab di bawah header, bisa digeser di ponsel. Tab Verifikasi membawa hitungan kuning. | 5 tujuan sama |
| Toast | Kanan atas, garis kiri berwarna | Kotak gelap bertepi bulat, ikon status di kiri. Garis kiri berwarna dihapus. | Pesan sama dari `messages` |
| Paginasi | Tombol angka | Sama, target 44 px. Ponsel: hanya panah + "Menampilkan 1-25 dari 132". | Parameter URL sama |
| 404 | Halaman mandiri, "WMID Community" | Memakai kerangka dan token yang sama, ilustrasi rambu. | Tombol Kembali & Beranda |

### 5.2 Halaman anggota

**Beranda** (`index.html`). Isi lorem ipsum diganti konten nyata. Susunan: kiri judul + penjelasan + tombol Masuk dan Daftar (tamu) atau "Buka profil saya" (anggota); kanan contoh entri riwayat bercap (diberi label "contoh"). Di bawahnya alur nyata sistem dalam tiga langkah (karena alurnya memang tiga langkah): Catat kegiatan, Diverifikasi pengurus, Tampil di profil. Blok CTA bawah untuk tamu tetap ada.

**Masuk / Daftar**. Satu kolom 400 px di tengah, di atas latar `--bg`. Tambahan teks penjelas (tanpa mengubah alur): di Masuk, "Punya akun Wikimedia? Hubungkan setelah masuk, dari halaman profil." Di Daftar, "Pernah ikut kegiatan WMID? Daftar dengan email yang sama supaya riwayatmu tersambung."

**Profil saya** (mockup: `mockups/profil.html`).
- Kartu identitas: avatar besar, nama, lencana ADMIN, ketersediaan, akun wiki, lokasi, tombol Ubah profil dan Sinkronkan suntingan (atau Hubungkan akun Wikimedia).
- Nudge kelengkapan profil tepat di bawahnya, dengan alasan yang nyata ("pengurus mencari pelatih, juri, dan narasumber dari profil").
- Hasil sinkronisasi: kotak info yang bisa ditutup, daftar wiki gagal dalam `details`.
- **Riwayat kegiatan jadi kolom utama** (desktop kiri, ponsel paling atas setelah identitas). Tiap entri: bulan-tahun, judul, chip peran berikon, lokasi, dan di kanan cap verifikasi atau status "Menunggu verifikasi" dengan tautan "Batalkan".
- Kolom samping: Tentang (keahlian, email, HP, sejak kapan anggota WMID) dan Komunitas.
- Kontribusi wiki: empat angka ringkas, tabel per proyek, 10 suntingan terbaru di dalam `details` (tidak hilang, hanya dilipat).

**Ubah profil**. Dua kolom tetap (form di kiri, akun Wikimedia dan komunitas di kanan) karena keduanya memang punya tombol kirim sendiri. Form dikelompokkan jadi tiga bagian bertajuk (Tentang kamu, Kontak dan lokasi, Keanggotaan WMID). Tombol Simpan menempel di bawah layar di ponsel. Daftar komunitas memakai baris 56 px dengan status "Menunggu verifikasi" yang jelas dan tombol aksi berlabel ("Keluar dari komunitas", "Batalkan permintaan"), bukan tanda ✕.

**Catat kegiatan**. Satu kolom 640 px. Kombobox kegiatan di atas; saat kegiatan resmi dipilih, tampil kartu ringkas kegiatan dengan tombol "Ganti". Field tambahan untuk kegiatan lain muncul di bawah dalam kelompok bertajuk "Detail kegiatan". Tombol kirim: "Kirim untuk diverifikasi".

**Komunitas**. Pengalih Kartu/Peta jadi kontrol segmen di atas. Kartu komunitas: logo 48 px, nama, chip jenis berikon, dua baris deskripsi, tanpa "Lihat detail" (seluruh kartu tautan). Di ponsel, peta memenuhi layar dengan daftar komunitas di lembar bawah yang bisa ditarik.

**Detail komunitas**. Header dengan logo, nama, jenis, pranala. Dua angka (anggota, kegiatan) sebagai teks di header, bukan kartu statistik terpisah. Anggota: narahubung di atas dengan label "Narahubung". Kegiatan terkait: daftar tanggal di kiri.

**Kegiatan & detail kegiatan**. Kartu kegiatan mengutamakan tanggal (blok tanggal di kiri) dan status. Detail kegiatan memakai daftar label-nilai dan kode kegiatan dalam huruf mono yang bisa disalin.

### 5.3 Halaman pengurus

**Ringkasan** (`admin_dashboard.html`). Disusun dari keputusan "ada yang perlu ditangani?":
1. Baris atas: kotak antrean verifikasi ("5 permintaan menunggu", tombol Buka antrean) hanya bila ada antrean. Bila kosong, satu baris "Antrean verifikasi kosong."
2. Tiga tautan cepat (Anggota, Komunitas, Kegiatan) dengan jumlahnya, sebagai baris tautan, bukan kartu besar dengan `onmouseover`.
3. Grafik dengan judul berupa pertanyaan: "Kegiatan resmi per bulan, 12 bulan terakhir" (batang), "Anggota baru per bulan, 12 bulan terakhir" (batang), "Ketersediaan anggota saat ini" (satu batang bertumpuk berlabel, menggantikan donat).
4. Kegiatan terbaru dan komunitas terbesar sebagai dua daftar.

**Anggota** (mockup: `mockups/anggota.html`). Kolom baru: Anggota (avatar, nama, username), Riwayat terverifikasi, Ketersediaan, Komunitas, Keahlian, Lokasi, Kontak, Terdaftar. Opsi urutan yang sama, dengan label lebih jelas. Di ponsel: pencarian + tombol "Saring (n)" yang membuka lembar bawah; hasil tampil sebagai daftar baris (nama, ketersediaan, komunitas, angka riwayat besar di kanan). Modal ekspor tetap, dengan pratinjau yang bisa digeser di dalam modal.

**Detail anggota**. Header sama dengan profil anggota (agar pengurus melihat apa yang dilihat anggota), ditambah blok "Data sistem" (terdaftar, metode masuk, terakhir sinkron). Tabel riwayat memakai chip peran dan status verifikasi yang sama. Tombol "Ubah data anggota".

**Ubah anggota**. Bagian yang bisa diubah diberi tajuk jelas dan dipisah dari bagian hanya-baca (hanya-baca memakai latar `--subtle` dan label "Hanya bisa diubah oleh anggota"). Daftar centang komunitas diberi kotak pencarian kecil di atasnya (penyaringan tampilan di sisi klien saja). Baris riwayat: pilih peran, pilih status, tombol "Hapus riwayat" merah tenang dengan modal konfirmasi.

**Komunitas (tabel)**. Sembilan kolom jenis kegiatan digabung menjadi satu kolom "Sebaran kegiatan" berisi chip kecil hanya untuk jenis yang nilainya lebih dari nol (misalnya "WikiLatih 4 · Kopdar 2"). Tombol "Tampilkan per jenis" mengembalikan 9 kolom terpisah untuk yang perlu membandingkan. Semua angka tetap sama dan tetap ada di ekspor.

**Detail & ubah komunitas**. Pola sama dengan anggota. Aksi relasi memakai kata kerja yang tepat: "Keluarkan dari komunitas" (anggota), "Lepaskan dari komunitas" (kegiatan), "Hapus narahubung".

**Kegiatan (tabel)**. Kolom: Kegiatan (judul + kode mono di bawahnya), Tanggal, Status, Jenis, Komunitas, Peserta, Sumber, Lokasi. Sumber: "Dari API" / "Dicatat anggota" / "Dibuat admin".

**Detail kegiatan + impor peserta**. Wizard impor tetap tiga langkah + hasil. Indikator langkah memakai nama, bukan hanya angka ("1 Unggah file, 2 Cocokkan kolom, 3 Pilih peserta"). Hasil impor memakai ilustrasi cap bila berhasil, dan daftar baris gagal bila ada.

**Verifikasi** (mockup: `mockups/verifikasi.html`). Satu kolom 760 px. Dua kelompok (Keanggotaan komunitas, Riwayat kegiatan), urutan sama seperti sekarang. Tiap permintaan satu kartu: siapa, apa yang diminta dalam kalimat utuh, chip peran, kode kegiatan, tanggal kirim, keterangan dari anggota dalam kotak kutipan. Tombol Tolak (kiri) dan Terima (kanan, utama). Di ponsel dua tombol selebar kartu, 48 px, di posisi jempol.

---

## 6. Pola layout mobile

Prinsip: layout ponsel adalah susunan tersendiri, bukan versi desktop yang dikecilkan.

### 6.1 Aturan umum

- **Navigasi bawah** 58 px + safe area, 4 tujuan dengan ikon dan label. Konten diberi ruang bawah seukuran navigasi supaya tombol terakhir tidak tertutup.
- **Header ponsel** 60 px, berisi nama sistem dan tombol akun (avatar). Tidak menempel lebih tinggi dari itu.
- **Satu kolom**. Grid dua kolom hanya untuk angka statistik (2 x 2).
- **Aksi utama halaman** berada di akhir form, menempel di bawah layar pada form panjang (Ubah profil, Catat kegiatan, Ubah anggota/komunitas/kegiatan).
- **Tidak ada interaksi yang hanya muncul saat hover.** Semua yang terbuka dengan hover juga terbuka dengan ketuk; semua target punya umpan balik `:active`.
- **Tidak ada gulir horizontal** di halaman. Tabel lebar berubah jadi daftar baris; bila tetap perlu tabel (pratinjau ekspor/impor), tabel digulir di dalam wadahnya sendiri.
- **Ukuran**: judul 22 px, teks isi 16 px, padding panel 16 px, jarak antar bagian 16 px.

### 6.2 Per halaman

| Halaman | Urutan informasi di ponsel | Catatan satu tangan |
|---|---|---|
| Profil | Identitas (avatar 56 px) → Ubah profil & Sinkronkan (dua tombol selebar layar) → nudge → Riwayat kegiatan + Catat kegiatan → Kontribusi → Tentang → Komunitas | Catat kegiatan ada di awal bagian riwayat, dalam jangkauan jempol setelah gulir pertama |
| Ubah profil | Form tiga bagian → Akun Wikimedia → Komunitas | Simpan perubahan menempel di bawah |
| Catat kegiatan | Kombobox → kartu terpilih → detail → peran → keterangan → komunitas | Daftar hasil kombobox tampil di bawah field dan tidak tertutup keyboard |
| Komunitas | Kontrol Kartu/Peta → daftar kartu | Peta: lembar bawah dengan daftar, geser naik untuk melihat detail |
| Kegiatan | Daftar kartu dengan blok tanggal di kiri | |
| Ringkasan | Antrean → tiga tautan cepat → grafik (tinggi 180 px, label bulan tiap dua bulan) → dua daftar | |
| Anggota / Komunitas / Kegiatan (pengurus) | Judul + ekspor (ikon) → cari + Saring (n) → chip saringan aktif → daftar baris → paginasi panah | Saringan di lembar bawah, tombol "Tampilkan hasil" di bawah |
| Detail (pengurus) | Header → aksi (Ubah) → blok info bertumpuk → daftar riwayat/anggota sebagai baris | |
| Verifikasi | Kartu permintaan bertumpuk | Tolak/Terima 48 px, selebar kartu, Terima di kanan |
| Ekspor / Impor | Layar penuh | Tombol aksi menempel di bawah |

### 6.3 Catatan interaksi yang perlu keputusan

Saat ini, pilihan saringan di halaman pengurus langsung mengirim form begitu diganti (`onchange="this.form.submit()"`). Di lembar bawah ponsel, halaman akan dimuat ulang setiap kali satu pilihan diganti, dan lembarnya tertutup. Usulan: di **ponsel saja**, lembar saringan memakai tombol "Tampilkan hasil" untuk mengirim ketiga pilihan sekaligus. Parameter yang dikirim dan hasilnya identik; yang berubah hanya kapan form dikirim. Di desktop, perilaku sekarang dipertahankan. **Perlu persetujuan** karena ini perubahan kecil pada interaksi.

---

## 7. Copywriting

### 7.1 Tone WMID

Seperti sesama relawan yang sudah lama di komunitas dan tahu cara kerjanya: jelas, ramah, tidak menggurui, tidak birokratis.

- **Sapaan "kamu"** di seluruh sistem, termasuk pesan untuk pengurus. "Anda" tidak dipakai.
- **Kalimat aktif dengan pelaku yang jelas**: "Pengurus sudah memverifikasi" lebih jelas dari "Telah diverifikasi".
- **Tulis apa yang terjadi dan apa langkah berikutnya.** Pesan error menyebut masalah dan cara memperbaikinya, tanpa minta maaf berlebihan.
- **Pakai istilah komunitas Wikimedia** yang sudah dikenal anggota: suntingan, halaman, WikiLatih, Kopdar, narahubung.
- **Hindari**: istilah teknis sistem (token, callback, state, API, fetch, CentralAuth), huruf kapital untuk penekanan, tanda seru beruntun, emoji, dan tanda pisah panjang.

### 7.2 Glosarium istilah baku

| Pakai | Jangan pakai | Catatan |
|---|---|---|
| Masuk | Login | Tombol & judul |
| Keluar dari akun | Logout, Keluar (saja) | Supaya tidak rancu dengan keluar komunitas |
| Daftar | Registrasi | |
| Email | Surel | Satu istilah di seluruh sistem |
| Kata sandi | Password | |
| Ubah | Edit | Ubah profil, Ubah data anggota |
| Sinkronkan / sinkronisasi | Sinkron, Sync, Sinkron API | |
| Impor / Ekspor | Import, Export | Ejaan baku |
| Hubungkan akun Wikimedia | Konfirmasi dengan Wikimedia | |
| Suntingan | Kontribusi (untuk angka), edit | "Kontribusi wiki" tetap boleh sebagai judul bagian |
| Riwayat kegiatan | Rekam jejak (di UI) | "Rekam jejak" hanya di beranda |
| Catat kegiatan | Tambah kegiatan (untuk anggota) | |
| Pengurus | Admin (di teks untuk anggota) | Nilai peran di data tetap "Admin" |
| Menunggu verifikasi / Terverifikasi / Ditolak | Pending, Menunggu (saja) | |
| Bisa diajak / Sedang sibuk / Tidak aktif | Aktif / Sibuk / Tidak aktif | Hanya label tampilan; nilai `aktif`, `sibuk`, `tidak_aktif` tetap |
| Hapus | | Hanya untuk yang benar-benar hilang (riwayat, peserta) |
| Keluarkan | Hapus | Anggota dari komunitas |
| Lepaskan | Hapus | Kaitan kegiatan dan komunitas |
| Terima / Tolak | | Tombol verifikasi |

Label tampilan yang berbeda dari label `choices` di `models.py` (ketersediaan, sumber kegiatan) diterapkan lewat template tag atau pemetaan di template, **bukan** dengan mengubah `choices`. Dengan begitu tidak ada migrasi database dan nilai tersimpan tetap sama.

### 7.3 Teks halaman (sebelum → sesudah)

**Kerangka dan navigasi**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Header | WMID Directory | Direktori Anggota · Wikimedia Indonesia |
| Nav | Dashboard | Pengurus |
| Tab pengurus | Verifikasi Data | Verifikasi |
| Menu akun | Edit profil / Keluar | Ubah profil / Keluar dari akun |
| Judul tab browser | Direktori Anggota — Wikimedia Indonesia | Direktori Anggota WMID |
| 404 judul | Halaman tidak ditemukan | Halaman ini tidak ada |
| 404 isi | Alamat … tidak ada atau sudah dipindahkan. | Alamat {path} tidak ditemukan. Mungkin tautannya salah ketik atau halamannya sudah dipindah. |
| 404 tombol | Kembali / Ke beranda | Kembali / Ke beranda |

**Beranda**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Judul | Lorem ipsum dolor sit amet | Temukan orang yang tepat dari rekam jejaknya |
| Subjudul | Lorem ipsum … | Direktori ini mencatat kegiatan dan kontribusi wiki anggota Wikimedia Indonesia. Pengurus bisa mencari pelatih, juri, panitia, atau narasumber dari riwayat yang sudah diverifikasi. |
| Tombol tamu | Masuk | Masuk · Daftar |
| Tombol anggota | Profil saya | Buka profil saya |
| Bagian alur | Lorem ipsum (3 fitur) | **Catat kegiatan**: Tulis kegiatan WMID yang pernah kamu ikuti dan peranmu di sana. · **Diverifikasi pengurus**: Pengurus memeriksa catatanmu, lalu memberi cap terverifikasi. · **Tampil di profil**: Riwayat terverifikasi bisa dilihat pengurus saat mencari orang untuk kegiatan berikutnya. |
| Tambahan | | **Hubungkan akun Wikimedia** supaya suntinganmu di Wikipedia, Wikidata, dan Commons ikut tercatat. |
| CTA bawah | Lorem ipsum … / Masuk sekarang | Sudah pernah ikut kegiatan WMID? Daftar dengan email yang sama, riwayatmu akan langsung tersambung. / Daftar sekarang |

**Masuk & Daftar**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Judul masuk | Masuk ke direktori | Masuk ke Direktori WMID |
| Label | Surel | Email |
| Placeholder email | kamu@example.com | email@example.com |
| Placeholder sandi | •••••••• | (kosong) |
| Catatan masuk | | Punya akun Wikimedia? Hubungkan setelah masuk, dari halaman profil. |
| Tautan | Belum punya akun? Daftar sekarang | Belum punya akun? Daftar |
| Judul daftar | Buat akun | Daftar sebagai anggota |
| Placeholder nama | Nama kamu | (kosong; label "Nama lengkap" cukup) |
| Petunjuk sandi | placeholder "Minimal 8 karakter" | hint di bawah field: Minimal 8 karakter. |
| Label ulang | Ulangi kata sandi | Ketik ulang kata sandi |
| Tombol | Buat akun | Daftar |
| Catatan daftar | | Pernah ikut kegiatan WMID? Pakai email yang sama dengan saat itu supaya riwayatmu tersambung. |
| Toggle sandi (aria) | Tampilkan kata sandi | Tampilkan kata sandi / Sembunyikan kata sandi (berganti sesuai kondisi) |

**Profil**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Tombol | Edit profil | Ubah profil |
| Tombol | Sinkronkan | Sinkronkan suntingan |
| Tombol | Hubungkan Wikimedia / Konfirmasi dengan Wikimedia | Hubungkan akun Wikimedia |
| Kartu kelengkapan | Lengkapi profil / Beberapa informasi belum diisi. Profilmu akan lebih mudah ditemukan pengurus. | **Profilmu belum lengkap.** Pengurus mencari pelatih, juri, dan narasumber dari profil. Lengkapi yang di bawah ini supaya kamu lebih mudah ditemukan. |
| Item | Tambah nama lengkap / Tulis bio singkat / Tambah keahlian | Isi nama lengkap / Tulis bio singkat / Tambah keahlian |
| Hasil sinkron | Sinkronisasi selesai: X kontribusi dari A/B wiki. (CentralAuth kosong, dicek satu per satu) | Sinkronisasi selesai. X suntingan tersimpan dari A dari B wiki. (Daftar wiki gabungan tidak tersedia, jadi setiap wiki dicek satu per satu.) |
| Hasil sinkron | N wiki gagal | N wiki tidak bisa dibaca. Lihat daftarnya |
| Label | Bio singkat / Keahlian / Nomor HP/WA | Tentang / Keahlian / Nomor HP/WA |
| Riwayat | + Catat kegiatan | Catat kegiatan |
| Riwayat, keterangan | | Kegiatan yang sudah diverifikasi pengurus tampil dengan cap hijau. |
| Status | Menunggu verifikasi × | Menunggu verifikasi · Batalkan |
| Riwayat kosong | Belum ada riwayat kegiatan. / Catat kegiatan pertama | Belum ada kegiatan yang tercatat. Pernah jadi peserta, panitia, atau pelatih di kegiatan WMID? Catat di sini supaya pengurus bisa melihatnya. / Catat kegiatan pertamamu |
| Komunitas | + Bergabung | Gabung |
| Komunitas kosong | Belum bergabung dengan komunitas mana pun. Bergabung sekarang | Kamu belum tergabung di komunitas mana pun. Cari komunitas di daerahmu atau komunitas bahasa yang kamu minati. / Cari komunitas |
| Kontribusi belum terhubung | Hubungkan akun Wikimedia untuk menarik riwayat kontribusimu dari semua proyek Wikimedia. | Hubungkan akun Wikimedia supaya suntinganmu di semua proyek Wikimedia ikut tercatat di profil. |
| Statistik | Kontribusi tersimpan / Halaman unik / Proyek aktif / Net byte | Suntingan tersimpan / Halaman berbeda / Proyek wiki / Selisih byte (hint: byte ditambah dikurangi byte dihapus) |
| Tabel | Per proyek / 10 kontribusi terbaru | Suntingan per proyek / 10 suntingan terbaru |
| Kontribusi kosong | Belum ada kontribusi tersimpan. Sinkronkan sekarang | Belum ada suntingan yang tersimpan. Sinkronkan sekarang untuk menarik suntingan terbarumu. |

**Ubah profil**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Judul | Edit profil | Ubah profil |
| Subjudul | Data yang kamu isi akan terlihat oleh pengurus sistem. | Semua yang kamu isi di sini bisa dilihat pengurus WMID. |
| Kembali | ← Profil | Kembali ke profil |
| Placeholder bio | Ceritakan sedikit tentang dirimu dan peranmu di komunitas Wikimedia... | Misalnya: proyek wiki yang sering kamu sunting, topik favorit, atau pengalaman melatih. |
| Hint bio | Maks. 500 karakter. | Maksimal 500 karakter. (tambah penghitung sisa karakter) |
| Label | Status ketersediaan | Bisa diajak ikut kegiatan? |
| Hint | Membantu pengurus menentukan apakah kamu bisa diundang ke kegiatan. | Pengurus melihat ini saat mencari orang untuk kegiatan. |
| Placeholder keahlian | Tulis keahlian, tekan Enter atau + | Ketik satu keahlian, lalu tekan Enter |
| Hint keahlian | Ditampilkan di profilmu. | Contoh: Wikidata, fotografi, menulis artikel, pelatihan daring. |
| Email terkunci | Email tidak bisa diubah pada akun email. | Email ini dipakai untuk masuk, jadi tidak bisa diubah dari sini. |
| Label | Nomor HP / WA (opsional) | Nomor HP/WA (opsional) |
| Placeholder HP | +62 812 xxxx xxxx | +62 8xx xxxx xxxx |
| Label | Bergabung WMID sejak | Anggota WMID sejak |
| Hint | Tanggal kamu resmi menjadi anggota Wikimedia Indonesia. | Kira-kira kapan kamu mulai aktif bersama Wikimedia Indonesia. |
| Panel wiki | Data diambil otomatis dari Wikimedia. Tidak bisa diubah dari sini. | Data ini diambil dari akun Wikimedia-mu dan diperbarui setiap sinkronisasi. |
| Panel wiki (belum) | Belum terhubung / Kamu akan diarahkan ke Wikimedia untuk otorisasi… | Belum terhubung. Kamu akan dibawa ke halaman Wikimedia untuk memberi izin, lalu kembali ke sini. Suntinganmu langsung disinkronkan. |
| Label tabel | Hak | Hak akses wiki |
| Komunitas | Komunitas saya | Komunitasmu |
| Tombol ✕ | (title) Keluar dari komunitas ini | Keluar dari komunitas |
| Tombol ✕ | (title) Batalkan permintaan | Batalkan permintaan |
| Pencarian | Cari komunitas untuk bergabung… | Cari komunitas |
| Semua sudah | Kamu sudah bergabung di semua komunitas yang tersedia. | Kamu sudah tergabung di semua komunitas yang ada. |

**Catat kegiatan**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Subjudul | Tambahkan riwayat kegiatan yang sudah kamu ikuti. | Catat kegiatan yang pernah kamu ikuti. Pengurus akan memeriksanya sebelum tampil sebagai terverifikasi. |
| Label | Nama kegiatan * | Nama kegiatan |
| Placeholder | Ketik nama kegiatan WMID atau kegiatan lainnya… | Ketik nama kegiatan |
| Hint | Kegiatan WMID resmi akan muncul saat mengetik. Pilih dari daftar, atau lanjutkan mengetik untuk mencatat kegiatan lainnya. | Kegiatan resmi WMID muncul saat kamu mengetik. Tidak ada di daftar? Tulis saja namanya, lalu isi detailnya di bawah. |
| Hint | Kosongkan jika sehari. | Kosongkan kalau kegiatannya hanya sehari. |
| Placeholder lokasi | Contoh: Jakarta / Daring | Nama kota, atau "Daring" |
| Label | Peranmu di kegiatan ini | Peranmu |
| Opsi jenis | — Pilih jenis — | Pilih jenis kegiatan |
| Label | Keterangan (opsional) | Keterangan untuk pengurus (opsional) |
| Placeholder | Tautan laporan, halaman Meta, atau catatan lainnya | Misalnya tautan laporan atau halaman Meta kegiatan |

**Komunitas & kegiatan**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Subjudul | N komunitas Wikimedia aktif di Indonesia. | N komunitas Wikimedia di Indonesia |
| Tombol | Sinkronkan / Sinkron API | Sinkronkan dari situs WMID |
| Tampilan | Kartu / Peta | Daftar / Peta |
| Deskripsi kosong | - | Belum ada deskripsi. |
| Kartu | Lihat detail | (dihapus, seluruh kartu jadi tautan) |
| Kosong (admin) | Belum ada data komunitas. / Sinkronkan sekarang | Belum ada komunitas. Tarik datanya dari situs WMID untuk mulai. / Sinkronkan sekarang |
| Kosong (anggota) | Hubungi admin untuk melakukan sinkronisasi. | Daftar komunitas belum diisi. Hubungi pengurus WMID. |
| Detail | Halaman komunitas | Kunjungi halaman komunitas |
| Detail | Anggota terdaftar / Kegiatan tercatat | anggota / kegiatan (di header) |
| Kegiatan subjudul | Riwayat dan jadwal kegiatan Wikimedia Indonesia. | Kegiatan Wikimedia Indonesia yang sudah lewat dan yang akan datang |
| Kegiatan kosong | Belum ada kegiatan. | Belum ada kegiatan. Kegiatan resmi akan muncul setelah pengurus menyinkronkan data dari situs WMID. |

**Pengurus**

| Lokasi | Sekarang | Usulan |
|---|---|---|
| Ringkasan subjudul | Direktori Anggota WMID | Yang perlu kamu tahu hari ini |
| Tautan cepat | Lihat, cari, dan filter semua anggota / Buka daftar → | Cari anggota menurut riwayat dan ketersediaan |
| Grafik | Kegiatan berlangsung, 12 bulan terakhir | Kegiatan resmi per bulan, 12 bulan terakhir |
| Grafik | Status anggota, Distribusi ketersediaan | Ketersediaan anggota saat ini |
| Anggota subjudul | N anggota ditemukan | N anggota cocok dengan saringan (tanpa saringan: N anggota) |
| Placeholder | Cari nama, email, lokasi… | Cari nama, username, email, atau lokasi |
| Opsi | Semua ketersediaan | Semua |
| Opsi urut | Kegiatan terbanyak / Kegiatan tersedikit / Bergabung terbaru | Riwayat terbanyak / Riwayat paling sedikit / Baru mendaftar |
| Tombol | Reset | Hapus saringan |
| Kolom | Kegiatan | Riwayat terverifikasi |
| Sel akun impor | Belum terdaftar | Belum mendaftar (hint: akun dibuat dari impor peserta) |
| Tidak ada hasil | Tidak ada anggota yang cocok. | Tidak ada anggota yang cocok. Coba kata kunci lain atau hapus saringan. |
| Ekspor | Ekspor Data Anggota / Pilih kolom yang akan diekspor / Pratinjau (8 baris pertama) / Unduh sebagai: | Ekspor data anggota / Pilih kolom / Pratinjau 8 baris pertama / Unduh sebagai CSV · Unduh sebagai Excel |
| Detail | Detail Anggota / Edit | (nama anggota sebagai judul) / Ubah data anggota |
| Detail | ✓ Wiki terverifikasi | Akun Wikimedia terhubung |
| Detail | Grup | Grup pengguna wiki |
| Detail | Terakhir disinkron: Belum pernah | Terakhir disinkronkan: belum pernah |
| Ubah | Profil (hanya-baca) | Profil · hanya bisa diubah oleh anggota |
| Ubah | Hapus (riwayat) | Hapus riwayat |
| Modal | Konfirmasi Hapus / Hapus riwayat kegiatan ini dari profil anggota? | Hapus riwayat ini? / Riwayat "{judul}" akan hilang dari profil {nama}. Tindakan ini tidak bisa dibatalkan. |
| Modal | Hapus anggota ini dari komunitas? | Keluarkan {nama} dari {komunitas}? / Riwayat kegiatannya tidak ikut terhapus. |
| Modal | Lepas kegiatan ini dari komunitas? | Lepaskan kegiatan ini dari {komunitas}? / Kegiatan dan pesertanya tetap ada. |
| Modal | Hapus {nama} dari kegiatan ini? | Hapus {nama} dari daftar peserta? / Riwayat kegiatan ini akan hilang dari profilnya. |
| Tombol modal | Batal / Hapus | Batal / (kata kerja yang sama dengan judul: Hapus riwayat, Keluarkan, Lepaskan, Hapus peserta) |
| Ubah komunitas | Hapus narahubung | Kosongkan narahubung |
| Ubah komunitas | — Jenis — | Pilih jenis |
| Ubah kegiatan | — Tidak ditentukan — | Belum ditentukan |
| Sumber | API / Pengguna / Manual — Admin / Manual — Anggota | Dari situs WMID / Dicatat anggota / Dibuat pengurus |
| Impor | Import peserta / Import Peserta / Unggah file Excel atau CSV | Impor peserta / Unggah file Excel (.xlsx, .xls) atau CSV |
| Impor | Seret file ke sini atau klik untuk memilih | Seret file ke sini, atau pilih file |
| Impor | Baris pertama adalah nama kolom (header) | Baris pertama berisi nama kolom |
| Impor | Pilih kolom mana yang berisi Nama dan Email peserta: | Kolom mana yang berisi nama dan email peserta? |
| Impor | Import N peserta / Mengimpor… | Impor N peserta / Sedang mengimpor… |
| Impor error | Gagal membaca file. / Gagal memproses file: {err} | File tidak bisa dibaca. Pastikan formatnya .xlsx, .xls, atau .csv, lalu coba lagi. |
| Verifikasi judul | Verifikasi Data / Pendaftaran yang menunggu konfirmasi | Menunggu verifikasi / Periksa tiap permintaan, lalu terima atau tolak. Riwayat yang diterima langsung tampil di profil anggota. |
| Verifikasi | Permintaan keanggotaan komunitas / Pendaftaran kegiatan | Keanggotaan komunitas / Riwayat kegiatan |
| Verifikasi | Ingin bergabung — X | Ingin bergabung dengan X |
| Verifikasi | {peran} — {kegiatan} · {kode} | Mencatat diri sebagai {peran} di {kegiatan} |
| Verifikasi | "{catatan}" | Keterangan dari anggota: {catatan} |
| Verifikasi kosong | Tidak ada data yang menunggu verifikasi. | **Antrean sudah bersih.** Tidak ada catatan kegiatan atau permintaan komunitas yang menunggu. Permintaan baru dari anggota akan muncul di sini. |

### 7.4 Pesan sistem (views)

| Sumber | Sekarang | Usulan |
|---|---|---|
| Akses admin | Akses ditolak. | Halaman itu khusus pengurus. Kamu dikembalikan ke beranda. |
| Belum masuk | Silakan login terlebih dahulu. | Masuk dulu untuk membuka halaman itu. |
| Daftar | Nama lengkap wajib diisi. | Nama lengkap belum diisi. |
| Daftar | Email wajib diisi. | Email belum diisi. |
| Daftar | Kata sandi wajib diisi. | Kata sandi belum diisi. |
| Daftar | Kata sandi minimal 8 karakter. | Kata sandi terlalu pendek. Pakai minimal 8 karakter. |
| Daftar | Konfirmasi kata sandi tidak cocok. | Kedua kata sandi tidak sama. Ketik ulang dengan teliti. |
| Daftar | Email sudah terdaftar. Silakan masuk. | Email ini sudah punya akun. Masuk dengan email tersebut. |
| Daftar | Akun berhasil dibuat. Selamat datang! | Akunmu sudah jadi. Selamat datang di Direktori WMID. |
| Daftar (klaim) | … N riwayat kegiatan sebelumnya ditemukan dan diklaim otomatis. | … N riwayat kegiatanmu yang lama sudah tersambung ke akun ini. |
| Masuk | Terlalu banyak percobaan login. Coba lagi dalam 1 menit. | Terlalu banyak percobaan masuk. Tunggu 1 menit, lalu coba lagi. |
| Masuk | Email atau kata sandi salah. | Email atau kata sandi tidak cocok. Periksa lagi, lalu coba masuk. |
| Masuk | Selamat datang kembali, {nama}! | Selamat datang kembali, {nama}. |
| Keluar | Anda telah logout. | Kamu sudah keluar dari akun. |
| OAuth | Silakan masuk terlebih dahulu untuk menghubungkan akun Wikimedia. | Masuk dulu, lalu hubungkan akun Wikimedia dari halaman profil. |
| OAuth | Wikimedia menolak otorisasi: {desc} | Wikimedia tidak memberi izin, jadi akun belum terhubung. Coba hubungkan lagi dari profil. |
| OAuth | Parameter "code" tidak ditemukan dalam callback. / Validasi state gagal (kemungkinan serangan CSRF). Coba lagi. / Sesi tidak valid… / Sesi link tidak valid. | (satu pesan untuk semua) Proses menghubungkan akun terputus. Mulai lagi dari tombol Hubungkan akun Wikimedia di profil. |
| OAuth | Gagal menukar token: {e} / Gagal mengambil profil: {e} | Wikimedia sedang tidak bisa dihubungi. Coba lagi beberapa menit lagi. (detail teknis tetap dicatat di log server) |
| OAuth | Akun Wikimedia "{u}" sudah terhubung ke akun lain. | Akun Wikimedia {u} sudah dipakai oleh anggota lain di direktori ini. Kalau itu akunmu, hubungi pengurus. |
| OAuth | Akun Wikimedia terhubung, tapi sync kontribusi gagal: {e} | Akun Wikimedia sudah terhubung, tapi suntinganmu belum bisa ditarik. Coba Sinkronkan suntingan dari profil. |
| OAuth | Akun Wikimedia "{u}" berhasil dihubungkan. | Akun Wikimedia {u} sudah terhubung. |
| Sinkron | Sinkronisasi baru saja dilakukan. Tunggu 5 menit sebelum sync ulang. | Suntinganmu baru saja disinkronkan. Kamu bisa sinkronkan lagi setelah 5 menit. |
| Sinkron | Sync gagal: {e} | Sinkronisasi gagal. Coba lagi beberapa menit lagi. |
| Profil | Format tanggal tidak valid. | Tanggal belum lengkap atau formatnya salah. |
| Profil | Email sudah digunakan oleh akun lain. | Email ini sudah dipakai akun lain. Pakai email yang berbeda. |
| Profil | Profil berhasil diperbarui. | Profil tersimpan. |
| Catat | Pendaftaran ke "{judul}" dikirim, menunggu verifikasi admin. | Catatanmu di {judul} terkirim. Pengurus akan memverifikasinya. |
| Catat | Kamu sudah terdaftar di kegiatan ini. | Kegiatan ini sudah ada di riwayatmu. |
| Catat | Judul dan tanggal mulai wajib diisi. | Nama kegiatan dan tanggal mulai perlu diisi. |
| Catat | Format tanggal mulai/selesai tidak valid. | Tanggal mulai (atau selesai) belum lengkap atau formatnya salah. |
| Catat | Tanggal selesai tidak boleh sebelum tanggal mulai. | Tanggal selesai lebih awal dari tanggal mulai. Periksa lagi kedua tanggalnya. |
| Catat | Kamu sudah pernah mencatat kegiatan serupa pada tanggal yang sama. | Kamu sudah mencatat kegiatan dengan nama dan tanggal yang sama. Cek riwayatmu. |
| Catat | Kegiatan "{judul}" dicatat, menunggu verifikasi admin. | {judul} sudah dicatat. Pengurus akan memverifikasinya. |
| Daftar kegiatan | Pendaftaran terkirim, menunggu verifikasi admin. | Terkirim. Pengurus akan memverifikasi pendaftaranmu. |
| Daftar kegiatan | Berhasil terdaftar sebagai {peran}. | Kamu tercatat sebagai {peran} di kegiatan ini. |
| Komunitas | Permintaan bergabung dengan X dikirim, menunggu verifikasi admin. | Permintaan bergabung dengan X terkirim. Pengurus akan memeriksanya. |
| Komunitas | Permintaan keluar dari X dikirim, menunggu verifikasi admin. | Permintaan keluar dari X terkirim. Pengurus akan memeriksanya. |
| Komunitas | Permintaan sudah terkirim, sedang menunggu verifikasi. | Permintaanmu sudah terkirim sebelumnya dan masih menunggu. |
| Komunitas | Kamu sudah anggota X. / Kamu bukan anggota komunitas ini. | Kamu sudah tergabung di X. / Kamu tidak tergabung di komunitas ini. |
| Sinkron data | Gagal fetch API: {e} / API mengembalikan error. | Data dari situs WMID tidak bisa diambil saat ini. Coba lagi nanti. |
| Sinkron data | Sinkronisasi selesai: a baru, b diperbarui, c dilewati. | Sinkronisasi selesai: a kegiatan baru, b diperbarui, c dilewati. |
| Sinkron data | … a komunitas baru ditambahkan, b sudah ada. | Sinkronisasi selesai: a komunitas baru, b sudah ada sebelumnya. |
| Admin | Admin tidak dapat mengubah role dirinya sendiri. | Kamu tidak bisa mengubah peranmu sendiri. Minta pengurus lain untuk mengubahnya. |
| Admin | Data anggota/komunitas berhasil diperbarui. / Kegiatan berhasil diperbarui. / Peserta berhasil dihapus. | Perubahan tersimpan. / Perubahan kegiatan tersimpan. / Peserta dihapus dari kegiatan. |
| Admin | Data tidak ditemukan. / Kegiatan tidak ditemukan. / Anggota tidak ditemukan. | Permintaan ini sudah tidak ada. Mungkin sudah diproses pengurus lain. / Kegiatan tidak ditemukan. / Anggota tidak ditemukan. |
| Verifikasi | {nama} berhasil bergabung dengan X. / {nama} dikeluarkan dari X. / Permintaan {nama} ditolak. | {nama} sekarang anggota X. / {nama} sudah keluar dari X. / Permintaan {nama} ditolak. |
| Verifikasi | Pendaftaran {nama} diterima. / Pendaftaran {nama} ditolak dan dihapus. | Riwayat {nama} terverifikasi. / Catatan {nama} ditolak dan dihapus. |
| Tambah peserta | {nama} sudah terdaftar di kegiatan ini. / {nama} berhasil ditambahkan sebagai {peran}. | {nama} sudah ada di daftar peserta. / {nama} ditambahkan sebagai {peran}. |

Catatan: pesan teknis yang dihapus dari tampilan tetap dicatat di log server (`logger.warning`), supaya jejak untuk pengembang tidak hilang. Ini satu-satunya perubahan pada views selain teks, dan tidak mengubah alur.

### 7.5 Aturan format

- Tanggal: `27 Sep 2026` (format Django `d M Y` dengan locale `id`). Rentang: `27-29 Sep 2026` atau `27 Sep - 2 Okt 2026`. Jam: `09.00-12.00` (titik, sesuai kebiasaan Indonesia).
- Angka ribuan pakai titik: `18.402`.
- Nomor telepon ditampilkan seperti yang diisi anggota.
- Judul kalimat biasa (sentence case): "Riwayat kegiatan", bukan "Riwayat Kegiatan".

---

## 8. Di luar cakupan (butuh perubahan logika)

Ide yang muncul selama audit tapi **tidak** dimasukkan ke redesign karena menyentuh logika atau data. Dicatat untuk dibahas terpisah.

1. **Saring anggota menurut peran** (misalnya "pernah jadi pelatih"). Ini inti dari "mencari orang yang tepat", tapi saat ini pencarian hanya menurut nama/email/lokasi/username, ketersediaan, dan komunitas. Butuh parameter baru di `admin_anggota`.
2. **Ringkasan per peran di profil dan detail anggota** ("Pelatih 3 kali, Juri 1 kali"). Butuh agregasi baru di view. Mockup profil tidak menampilkannya agar tetap jujur terhadap data yang ada.
3. **Cari menurut keahlian** di halaman Anggota (keahlian belum ikut pencarian).
4. **Penanda field error dari server** agar field yang salah bisa diberi tepi merah. Saat ini error hanya berupa pesan.
5. **Logo resmi** WMID perlu disediakan tim komunikasi.
6. Tautan username wiki tidak konsisten: profil anggota ke Meta-Wiki, detail pengurus ke id.wikipedia. Menyeragamkannya mengubah tujuan tautan.

---

## 9. Langkah berikutnya

1. Review brief ini, terutama glosarium (7.2), perubahan label ketersediaan, dan catatan interaksi saringan di ponsel (6.3).
2. Setujui atau revisi tiga mockup.
3. Implementasi bertahap yang aman: token + `base.html` dulu (semua halaman ikut berubah warna dan huruf), lalu komponen bersama, lalu halaman per halaman, lalu teks. Setiap tahap diuji dengan alur di Bagian 1.1.
