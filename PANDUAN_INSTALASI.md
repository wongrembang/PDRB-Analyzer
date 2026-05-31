# Panduan Instalasi & Penggunaan PDRB Analyzer

## Tentang Aplikasi

**PDRB Analyzer** adalah dashboard interaktif berbasis web untuk analisis ekonomi regional Jawa Tengah. Aplikasi ini dibangun dengan Python + Streamlit dan dapat diakses oleh beberapa pengguna melalui jaringan lokal (LAN).

---

## Persyaratan Sistem

| Komponen | Minimum | Rekomendasi |
|---|---|---|
| Sistem Operasi | Windows 7/10/11 | Windows 10/11 (64-bit) |
| RAM | 4 GB | 8 GB |
| Python | 3.9 | 3.11 atau 3.12 |
| Ruang Disk | 500 MB | 1 GB |

---

## Langkah 1: Install Python

1. Buka browser, kunjungi: **https://python.org/downloads**
2. Klik tombol kuning **"Download Python 3.x.x"**
3. Jalankan installer yang sudah diunduh
4. **PENTING:** Centang kotak **"Add Python to PATH"** sebelum klik Install
5. Klik **"Install Now"**
6. Tunggu hingga selesai, klik **Close**

**Verifikasi instalasi** — buka Command Prompt (tekan `Win+R`, ketik `cmd`, Enter):
```
python --version
```
Jika muncul `Python 3.x.x`, instalasi berhasil.

---

## Langkah 2: Install Dependencies

**Cara otomatis (direkomendasikan):**
Cukup jalankan `start.bat` (langkah 3), aplikasi akan install otomatis saat pertama kali dijalankan.

**Cara manual:**
1. Buka Command Prompt di folder aplikasi (tahan Shift + klik kanan di folder, pilih "Open command window here")
2. Ketik perintah:
```
pip install -r requirements.txt
```
3. Tunggu hingga semua package terinstall (perlu koneksi internet, ±3-10 menit tergantung kecepatan internet)

---

## Langkah 3: Menjalankan Aplikasi

### Cara Mudah (Windows):
**Klik dua kali file `start.bat`**

Aplikasi akan terbuka otomatis di browser. Jika tidak terbuka otomatis, buka browser dan akses:
```
http://localhost:8501
```

### Cara Manual:
1. Buka Command Prompt di folder aplikasi
2. Ketik:
```
streamlit run app.py
```

---

## Langkah 4: Login

Setelah aplikasi terbuka di browser, masukkan kredensial berikut:

| Akun | Username | Password | Hak Akses |
|---|---|---|---|
| Administrator | `admin` | `admin123` | Penuh (termasuk upload data & kelola user) |
| User Biasa | `user1` | `user1234` | Analisis & laporan saja |

> **Catatan Keamanan:** Segera ganti password default setelah login pertama melalui menu **Manajemen Data & User → Manajemen User → Reset Password**.

---

## Akses dari Komputer Lain (Jaringan LAN)

Agar pengguna lain di jaringan yang sama bisa mengakses dashboard:

1. **Pastikan** `start.bat` sudah dijalankan di komputer server
2. **Cari IP address** komputer server:
   - Buka Command Prompt
   - Ketik `ipconfig`
   - Catat **IPv4 Address** (contoh: `192.168.1.100`)
3. **Di komputer lain**, buka browser dan akses:
   ```
   http://192.168.1.100:8501
   ```
4. Jika tidak bisa diakses, nonaktifkan sementara **Windows Firewall** atau tambahkan aturan untuk port `8501`

---

## Struktur File Data

Letakkan file data di folder yang sama dengan `app.py`:

```
PDRB Analyzer/
├── app.py                          ← File utama aplikasi
├── start.bat                       ← Shortcut untuk menjalankan aplikasi
├── requirements.txt                ← Daftar dependensi Python
├── users.yaml                      ← Konfigurasi pengguna & login
├── config.py                       ← Konfigurasi global
├── pdrb triwulanan 3 sektor.xlsx   ← Data PDRB (WAJIB ADA)
├── jumlah penduduk triwulanan.xlsx ← Data Penduduk (WAJIB ADA)
├── kode wilayah.xlsx               ← Kode & nama wilayah (WAJIB ADA)
├── data/
│   ├── loader.py
│   └── cache_pdrb.pkl              ← Cache otomatis (akan dibuat saat pertama kali)
├── utils/
│   ├── analytics.py
│   └── charts.py
└── pages/
    ├── p1_analisis_wilayah.py
    ├── p2_analisis_regional.py
    ├── p3_proyeksi.py
    ├── p4_laporan.py
    ├── p5_petunjuk.py
    └── p6_manajemen.py
```

---

## Menambah Data Periode Terbaru

Ketika ada data PDRB terbaru dari BPS:

1. Login sebagai **admin**
2. Buka menu **Manajemen Data & User → Upload Data**
3. Klik **Browse files** dan pilih file Excel baru
4. Klik **Upload & Proses**
5. Aplikasi akan otomatis memperbarui analisis dengan data terbaru

> File lama akan otomatis di-backup sebelum diganti.

---

## Format File Excel yang Didukung

### File PDRB (`pdrb triwulanan 3 sektor.xlsx`)
- Setiap sheet = satu kabupaten/kota (kode 4 digit, contoh: `3301`)
- Satu sheet khusus untuk provinsi (kode: `3300`)
- Setiap sheet memiliki 2 tabel:
  - **Tabel 1**: PDRB ADHB (Harga Berlaku)
  - **Tabel 2**: PDRB ADHK (Harga Konstan, tahun dasar 2010)
- Kolom = Periode triwulanan (format: 2010Q1, 2010Q2, dst.)
- Baris = Lapangan usaha (66 sektor/sub-sektor)

### File Penduduk (`jumlah penduduk triwulanan.xlsx`)
- Kolom A: Kode wilayah (4 digit)
- Kolom B: Nama wilayah
- Kolom C+: Data penduduk per triwulan (dalam ribu jiwa)

### File Kode Wilayah (`kode wilayah.xlsx`)
- Berisi kode, nama, dan kelompok pembangunan regional setiap kabupaten/kota

---

## Troubleshooting

### Aplikasi tidak mau jalan
- Pastikan Python sudah terinstall dan ada di PATH
- Coba jalankan manual: `streamlit run app.py`
- Lihat pesan error di Command Prompt

### Browser tidak terbuka otomatis
- Buka browser manual, akses `http://localhost:8501`

### Login gagal
- Gunakan username/password yang tepat (case-sensitive)
- Jika lupa password, edit file `users.yaml` dan buat hash password baru

### Data tidak muncul / error saat load
- Pastikan file Excel ada di folder yang benar
- Hapus file `data/cache_pdrb.pkl` lalu refresh halaman (cache akan dibuat ulang)
- Periksa format sheet Excel sesuai ketentuan di atas

### Tidak bisa diakses dari komputer lain
- Pastikan `start.bat` berjalan (jangan ditutup)
- Cek firewall Windows, tambahkan exception untuk port 8501
- Pastikan komputer server dan client di jaringan yang sama

---

## Kontak & Dukungan

Jika mengalami masalah yang tidak tercantum di sini, silakan hubungi pengelola sistem atau BPS Jawa Tengah.

---

*PDRB Analyzer v1.0 | Dibangun dengan Python + Streamlit*
