# Radar Kompetitor — Tools Riset YouTube

Tools riset kompetitor YouTube: cari video/channel berdasarkan niche, pantau trending realtime,
analisis performa & strategi channel (frekuensi upload, format konten, engagement), dan bandingkan
beberapa kompetitor sekaligus.

Terdiri dari dua bagian:
- **`scripts/`** — CLI Python yang mengambil data asli dari YouTube Data API v3
  - `research.py` — niche-search, trending, channel, compare (untuk riset manual)
  - `fetch_trending_snapshot.py` + `embed_trending_data.py` (atau `refresh_trending.sh`) — ambil & suntik data untuk tab Trending publik
- **`dashboard/dashboard.html`** — dashboard visual (sudah dipublish sebagai Artifact) untuk melihat hasilnya

## 1. Setup awal

### a. Buat API key
1. Buka https://console.cloud.google.com/ → buat project baru
2. Aktifkan **YouTube Data API v3** (search di search bar → Enable)
3. **APIs & Services → Credentials → Create Credentials → API Key**
4. Copy key, lalu isi ke file `.env`:

```bash
cp .env.example .env
# edit .env, isi YOUTUBE_API_KEY=AIzaSy...
```

Kuota gratis: 10.000 unit/hari. `search` = 100 unit/panggilan, `videos`/`channels` = 1 unit.
Jadi `niche-search` atau `compare` bisa dipakai puluhan kali sehari dengan aman.

### b. Install dependency

```bash
python3 -m pip install -r requirements.txt
```

## 2. Pakai CLI

```bash
# Cari & analisis video di suatu niche, urutkan dari views tertinggi
python3 scripts/research.py niche-search --query "review skincare" --max 30 --order viewCount --days 30

# Lihat trending realtime (region ID = Indonesia)
python3 scripts/research.py trending --region ID --max 25

# Analisis satu channel kompetitor: performa, frekuensi upload, format konten
python3 scripts/research.py channel --handle @namachannel --max-videos 25

# Bandingkan beberapa kompetitor sekaligus
python3 scripts/research.py compare --handles @channel1,@channel2,@channel3
```

Tiap perintah mencetak ringkasan di terminal DAN menyimpan hasil lengkap sebagai file JSON
di folder `data/` (nama file diberi timestamp otomatis).

Opsi berguna lain:
- `--days N` (niche-search) — hanya video yang terbit N hari terakhir
- `--duration short|medium|long` (niche-search) — filter durasi video
- `--region XX` — kode negara 2 huruf (ID, US, dst)
- `--category` (trending) — ID kategori YouTube

## 3. Dashboard

Buka dashboard: **https://claude.ai/code/artifact/38d1c976-0866-4998-b7a7-038922af0fcd**

Dashboard punya 2 tab:

### Tab "Trending" (publik)
Halaman utama — pilih **negara** (Indonesia, US, GB, India, Jepang, Korea Selatan) dan **niche/kategori**
(Gaming, Musik, Komedi, Hiburan, dll) lewat dropdown, langsung tampil video trending untuk kombinasi itu.

Data-nya **tertanam langsung di halaman** (bukan dipanggil live dari browser) — ini disengaja demi
keamanan: API key kamu tidak pernah ada di kode halaman publik, jadi aman dibagikan ke siapa saja
tanpa risiko API key dicuri/disalahgunakan.

**Refresh-nya sekarang full otomatis, tiap 6 jam**, lewat pipeline ini:
1. **GitHub Actions** ([.github/workflows/refresh-trending.yml](.github/workflows/refresh-trending.yml)) jalan tiap 6 jam → ambil data trending pakai `YOUTUBE_API_KEY` yang tersimpan sebagai GitHub Secret → commit `dashboard/dashboard.html` yang sudah diperbarui ke repo [kangkhalief/analisis-youtube](https://github.com/kangkhalief/analisis-youtube) (publik, tanpa API key di kode)
2. **Claude cloud routine** ("Sync trending dashboard artifact" — lihat di https://claude.ai/code/routines) otomatis terpicu lewat webhook setiap ada commit baru → publish ulang ke Artifact ini. Ada juga jadwal cadangan tiap 6 jam 20 menit kalau webhook-nya kebetulan gagal.

Tidak perlu diapa-apakan lagi — kalau mau cek manual: `gh run list --repo kangkhalief/analisis-youtube` (riwayat GitHub Actions) atau buka halaman routine di claude.ai/code/routines.

**Supaya publik beneran bisa akses**: dashboard ini defaultnya **privat**. Buka link dashboard-nya,
klik tombol **Share** di pojok kanan atas halaman, lalu pilih opsi share publik. Claude tidak bisa
melakukan ini untukmu — harus lewat UI langsung.

### Tab "Riset Kompetitor" (pribadi)
Fitur upload manual + query builder yang sudah ada sebelumnya — tetap di sini, tidak hilang:
1. Pilih niche di dropdown "Susun perintah niche" → salin perintah → jalankan di terminal
2. Upload file JSON hasilnya (dari folder `data/`) ke kotak "Unggah data JSON"
3. Dashboard otomatis mendeteksi jenis data dan menampilkan:
   - **Niche search** — top video, kata kunci & tag yang sedang laku, format Shorts vs panjang, papan peringkat engagement
   - **Channel** — profil, frekuensi upload/minggu, pola hari upload, rata-rata views & engagement, views per subscriber, video terbaik
   - **Compare** — ranking kompetitor berdasarkan efisiensi (views per subscriber), tabel perbandingan lengkap

Riwayat data yang pernah diunggah tersimpan otomatis di browser kamu sendiri (localStorage) — tidak
terlihat oleh orang lain yang buka link publik, dan bisa dibuka lagi kapan saja tanpa upload ulang.

## 4. Alur kerja yang disarankan

1. **Cari ide konten**: `niche-search` dengan keyword niche kamu, `--order viewCount --days 30`
   → lihat topik & format apa yang sedang berhasil dalam sebulan terakhir
2. **Pantau tren harian**: `trending --region ID` → cek apa yang sedang viral hari ini
3. **Bedah kompetitor utama**: `channel --handle @kompetitor` → pelajari ritme upload &
   format mereka secara detail
4. **Benchmark posisi kamu**: `compare --handles @kamu,@kompetitor1,@kompetitor2` → lihat siapa
   paling efisien (views per subscriber tinggi = strategi konten yang lebih tajam, bukan cuma
   modal jumlah subscriber)
