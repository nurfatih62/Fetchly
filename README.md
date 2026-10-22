# Fetchly

Pengunduh video YouTube dan TikTok yang berjalan sepenuhnya di komputer sendiri. Tempel tautan, lihat pratinjau, lalu simpan sebagai **MP4** atau **MP3**. Gratis, open source (MIT), tanpa akun, tanpa iklan, dan tanpa pelacakan.

Fetchly terdiri dari dua bagian:

- **Aplikasi lokal** (folder `app/` + `static/`) — server Python kecil yang hanya bisa dibuka dari komputer sendiri.
- **Landing page statis** (folder `landing/`) — halaman informasi untuk di-host gratis di Vercel. Halaman ini tidak terhubung ke aplikasi lokal.

> Gunakan hanya untuk video yang kamu miliki haknya, video berlisensi yang boleh diunduh (misalnya Creative Commons), atau video yang diizinkan pemiliknya. Patuhi Ketentuan Layanan YouTube dan TikTok serta hukum hak cipta yang berlaku.

## Fitur

- Mendukung tautan YouTube (`watch`, `youtu.be`, `shorts`, `m.youtube.com`) dan TikTok (`@user/video`, `vm.tiktok.com`, `vt.tiktok.com`).
- Pratinjau thumbnail, judul, kanal/akun, dan durasi.
- MP4 dengan pilihan **Terbaik, 1080p, 720p, 480p, 360p** — hanya kualitas yang tersedia yang ditampilkan.
- MP3 192 kbps.
- Unduhan otomatis setelah file siap, dengan nama file yang aman.
- Pemeriksaan ffmpeg dan yt-dlp saat aplikasi dijalankan.
- Pesan error Bahasa Indonesia, tanpa stack trace di browser.
- Server hanya mengikat ke `127.0.0.1`; tidak bisa dibuka dari perangkat lain di jaringan.
- File sementara dihapus setelah dikirim, atau otomatis dibersihkan saat aplikasi dijalankan lagi.
- UI responsif, mode gelap mengikuti preferensi sistem, dan mendukung `prefers-reduced-motion`.

## Persyaratan

| Kebutuhan | Keterangan |
|---|---|
| Windows 10 atau 11 | Aplikasi juga bisa berjalan di macOS/Linux, tetapi panduan ini untuk Windows. |
| Python 3.11+ | Unduh dari [python.org](https://www.python.org/downloads/windows/). |
| ffmpeg | Dibutuhkan untuk MP3 dan penggabungan video MP4. |
| Koneksi internet | Untuk menghubungi YouTube atau TikTok secara langsung. |

Python dan ffmpeg cukup dipasang sekali.

## Instalasi di Windows

### 1. Pasang Python

1. Buka [python.org/downloads/windows](https://www.python.org/downloads/windows/) dan unduh Python 3.11 atau lebih baru.
2. Jalankan installer. **Centang “Add Python to PATH”** sebelum menekan Install.
3. Buka PowerShell baru, lalu cek:

   ```powershell
   python --version
   ```

   Jika perintah `python` tidak dikenali, coba `py --version`. Kamu juga bisa memakai `py` untuk semua perintah di bawah.

### 2. Pasang ffmpeg

Buka PowerShell dan jalankan:

```powershell
winget install Gyan.FFmpeg
```

Setelah selesai, **tutup dan buka kembali PowerShell**, lalu cek:

```powershell
ffmpeg -version
```

Jika `winget` tidak tersedia, pasang **App Installer** dari Microsoft Store, atau unduh ffmpeg manual dari [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) dan tambahkan folder `bin`-nya ke PATH.

### 3. Unduh kode proyek

1. Buka halaman repositori di GitHub.
2. Klik **Code → Download ZIP**.
3. Ekstrak ZIP ke folder yang mudah diingat, misalnya `Dokumen\Fetchly`.

Atau lewat terminal:

```powershell
git clone https://github.com/nurfatih62/Fetchly.git
cd Fetchly
```

### 4. Pasang dependensi dan jalankan

Buka PowerShell **di folder proyek** (folder yang berisi `run.py`), lalu:

```powershell
pip install -r requirements.txt
python run.py
```

Browser akan terbuka otomatis di `http://127.0.0.1:8000`. Jika browser tidak terbuka, buka alamat itu secara manual.

Untuk menghentikan aplikasi, kembali ke terminal dan tekan `Ctrl+C`.

## Cara pakai

1. Salin tautan video YouTube atau TikTok.
2. Buka aplikasi, tempel tautan, lalu klik **Cek video** (tombol Enter juga bisa).
3. Setelah pratinjau muncul, pilih **MP4** atau **MP3**.
4. Untuk MP4, pilih kualitas yang tersedia.
5. Klik **Unduh**. Tombol berubah menjadi “Menyiapkan...”.
6. File otomatis masuk ke folder unduhan browser. Pesan “Berhasil diunduh” muncul setelah selesai.

Jika ffmpeg belum terpasang, banner peringatan muncul di bagian atas aplikasi. MP3 dan penggabungan MP4 membutuhkan ffmpeg.

## Pengaturan

Semua pengaturan bersifat opsional. Salin `.env.example` menjadi `.env` jika ingin mengubahnya:

```powershell
Copy-Item .env.example .env
notepad .env
```

| Variabel | Bawaan | Keterangan |
|---|---|---|
| `MAX_DURATION_SECONDS` | `900` | Durasi video maksimum (detik). 900 = 15 menit. |
| `MAX_FILESIZE_MB` | `500` | Ukuran file maksimum (MB). |
| `MAX_PARALLEL_JOBS` | `2` | Jumlah proses unduh bersamaan (1–8). |
| `DOWNLOAD_TIMEOUT_SECONDS` | `180` | Batas waktu satu proses unduh. |
| `PORT` | `8000` | Port lokal aplikasi. |
| `TEMP_DIR` | folder temp sistem + `vdl` | Lokasi file sementara. |

Aplikasi selalu mengikat ke `127.0.0.1`, bukan `0.0.0.0`. Jangan ubah bagian itu — tujuannya agar aplikasi tidak bisa diakses dari jaringan.

Jika port `8000` sudah dipakai aplikasi lain, ubah `PORT` di `.env`, atau jalankan sementara:

```powershell
$env:PORT=8001; python run.py
```

## Memperbarui yt-dlp

YouTube dan TikTok sering mengubah sistemnya. Jika unduhan tiba-tiba gagal padahal tautan benar, langkah pertama adalah memperbarui yt-dlp:

```powershell
pip install -U yt-dlp
```

Lalu tutup dan jalankan ulang aplikasi. Pesan error “Terjadi kesalahan...” juga menyarankan langkah ini.

## Landing page dan Vercel

Landing page ada di folder `landing/` dan berupa HTML/CSS statis tanpa build step. Tautan GitHub di landing page dan aplikasi sudah mengarah ke [repositori Fetchly](https://github.com/nurfatih62/Fetchly).

Cara deploy:

1. Push proyek ke repositori GitHub.
2. Buka [vercel.com](https://vercel.com), klik **Add New → Project**, lalu impor repositori.
3. Pada bagian **Root Directory**, pilih `landing`.
4. **Framework Preset**: `Other`.
5. Biarkan Build Command dan Output Directory kosong.
6. Klik **Deploy**. Tidak perlu environment variable.

Landing page tidak mengirim data ke aplikasi lokal dan tidak memiliki backend.

## Struktur proyek

```text
Fetchly/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI, middleware keamanan, static files
│   ├── config.py            # Konfigurasi dari .env
│   ├── errors.py            # Kode dan pesan error
│   ├── routes.py            # Endpoint /api/*
│   ├── schemas.py           # Model Pydantic
│   ├── services/
│   │   └── downloader.py    # Logika yt-dlp
│   └── utils/
│       ├── validators.py    # Validasi URL
│       ├── deps.py          # Cek ffmpeg dan yt-dlp
│       └── files.py         # Temp, nama file, pembersihan
├── static/                  # UI aplikasi lokal
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── favicon.svg
├── landing/                 # Landing page untuk Vercel
│   ├── index.html
│   ├── style.css
│   └── favicon.svg
├── tests/
│   ├── test_validators.py
│   └── test_downloader_formats.py
├── run.py
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

### Alur singkat

```text
Browser (127.0.0.1) → FastAPI lokal → yt-dlp + ffmpeg → YouTube / TikTok
```

File hasil unduhan dikirim langsung dari folder sementara lokal ke browser. Tidak ada server pihak ketiga milik proyek ini.

## Menjalankan test

Test validasi URL dan daftar kualitas format memakai `unittest` bawaan Python, tanpa dependensi tambahan:

```powershell
python -m unittest discover -s tests -v
```

Test mencakup tautan valid, domain palsu seperti `youtube.com.evil.net`, platform lain, skema salah, port, userinfo, batas panjang URL, serta penyaringan kualitas video yang benar-benar tersedia.

## Pemecahan masalah

| Gejala | Solusi |
|---|---|
| `python` tidak dikenali | Pasang ulang Python dan centang “Add Python to PATH”, lalu buka terminal baru. Coba juga `py run.py`. |
| `ffmpeg` tidak ditemukan | Jalankan `winget install Gyan.FFmpeg`, tutup-buka terminal, lalu cek `ffmpeg -version`. |
| Aplikasi tetap jalan tetapi MP3 gagal | ffmpeg belum terpasang atau belum ada di PATH. Lihat panduan di atas. |
| Port 8000 sudah dipakai | Ubah `PORT` di `.env`, atau jalankan `$env:PORT=8001; python run.py`. |
| “Video tidak bisa diakses” | Video privat, dihapus, dibatasi wilayah, atau tautan sudah kedaluwarsa. Coba tautan baru. |
| “Video ini hanya untuk member...” | Konten berbayar/member tidak didukung. |
| “Terjadi kesalahan...” | Perbarui yt-dlp: `pip install -U yt-dlp`, lalu jalankan ulang aplikasi. |
| Gagal mengambil info TikTok | Salin ulang tautan dari aplikasi TikTok; tautan pendek `vm`/`vt` bisa kedaluwarsa. |
| Tombol Tempel tidak bekerja | Browser memblokir akses clipboard. Klik kolom input dan tekan `Ctrl+V`. |
| File MP4 tidak bisa diputar | Gunakan pemutar seperti VLC. Untuk kompatibilitas terbaik, pilih 720p/1080p setelah ffmpeg terpasang. |
| Unduhan terputus | Cek koneksi, coba kualitas lebih rendah, atau perbarui yt-dlp. |

## Batasan penggunaan

Fetchly **tidak** menyediakan fitur untuk:

- melewati DRM, login, atau pembatasan member/berbayar;
- mengunduh seluruh channel atau playlist secara massal (playlist hanya mengambil satu video);
- mengunduh video live, video privat, atau konten yang dibatasi wilayah;
- mengunggah ulang atau memonetisasi konten milik orang lain.

Pengembang tidak bertanggung jawab atas penyalahgunaan perangkat lunak ini. Pengguna bertanggung jawab mematuhi hukum hak cipta dan ketentuan layanan masing-masing platform.

Disclaimer lengkap:

> “Gunakan hanya untuk video yang kamu miliki haknya, video berlisensi yang boleh diunduh (misalnya Creative Commons), atau video yang diizinkan pemiliknya. Patuhi Ketentuan Layanan YouTube dan TikTok serta hukum hak cipta yang berlaku.”

## Keterbatasan yang diketahui

- Sangat bergantung pada `yt-dlp`. Perubahan dari YouTube/TikTok bisa membuat unduhan gagal sampai yt-dlp diperbarui.
- Pemeriksaan bot/usia dari platform dapat memblokir unduhan tertentu. Aplikasi tidak menyediakan login atau cookie.
- Kualitas yang ditampilkan hanya standar (360p–1080p). Video 4K tetap bisa dipilih lewat “Terbaik”, tetapi hasilnya bergantung pada format yang tersedia.
- Tidak ada progress bar real-time; tombol menampilkan status “Menyiapkan...” sampai file siap.
- File diunduh ke memori browser sebelum disimpan. Untuk file sangat besar, gunakan batas ukuran yang wajar.
- ffmpeg wajib untuk MP3 dan umumnya untuk MP4 resolusi tinggi, karena YouTube mengirim video dan audio terpisah.
- Landing page tidak terhubung dengan aplikasi lokal; keduanya memang dipisahkan.

## Lisensi dan kontribusi

Dirilis dengan lisensi [MIT](LICENSE). Kamu bebas memakai, mengubah, dan membagikan kode ini dengan tetap menyertakan lisensi.

Kontribusi terbuka: silakan buka issue untuk laporan bug atau pull request untuk perbaikan. Sertakan langkah reproduksi dan versi yt-dlp (`pip show yt-dlp`) tanpa membagikan tautan pribadi.
