# 🚀 Panduan Deploy PDRB Analyzer ke Streamlit Cloud

## Gambaran Umum

```
Laptop/PC  →  GitHub (kode)  →  Streamlit Community Cloud  →  URL publik
                                  (otomatis baca repo)           multi-user
```

---

## LANGKAH 1 — Siapkan Repository GitHub

### 1.1 Install Git (jika belum)
Download di: https://git-scm.com/download/win

### 1.2 Buat akun GitHub
Daftar di: https://github.com (gratis)

### 1.3 Buat repository baru di GitHub
1. Klik tombol **"New repository"**
2. Nama repo: `pdrb-analyzer` (atau sesuai selera)
3. Pilih **Private** (agar data tidak terlihat publik)
4. Klik **"Create repository"**

### 1.4 Upload kode dari folder lokal
Buka **Command Prompt** atau **Git Bash**, arahkan ke folder project:

```bash
cd "D:\project AI\PDRB Analyser"

# Inisialisasi git
git init
git add .
git commit -m "Initial commit - PDRB Analyzer v2.0"

# Hubungkan ke GitHub (ganti USERNAME dan REPO_NAME)
git remote add origin https://github.com/USERNAME/pdrb-analyzer.git
git branch -M main
git push -u origin main
```

> ⚠️ File `.xlsx`, `users.yaml`, dan cache **tidak akan ter-upload** karena sudah ada di `.gitignore` — ini disengaja untuk keamanan data.

---

## LANGKAH 2 — Siapkan Data di Streamlit Cloud

Karena file Excel tidak di-push ke GitHub, ada **2 opsi**:

### Opsi A: Upload via fitur Manajemen Data (Recommended)
Setelah app berhasil deploy, login sebagai admin → halaman **Manajemen Data & User** → upload file Excel.

### Opsi B: Gunakan Streamlit Secrets + Google Drive / Dropbox
Simpan link download file di `secrets.toml` dan buat loader otomatis download saat startup.

---

## LANGKAH 3 — Deploy ke Streamlit Community Cloud

### 3.1 Buat akun Streamlit Cloud
Daftar di: https://share.streamlit.io  
(Login dengan akun GitHub)

### 3.2 Deploy app
1. Klik **"New app"**
2. Pilih repository: `pdrb-analyzer`
3. Branch: `main`
4. Main file path: `app.py`
5. Klik **"Deploy!"**

Tunggu 2–5 menit, app akan tersedia di:
```
https://USERNAME-pdrb-analyzer-app-XXXXX.streamlit.app
```

### 3.3 Konfigurasi users (multi-user)
Setelah deploy, buka halaman **Manajemen Data & User** dengan login admin, lalu tambahkan akun untuk setiap user yang akan mengakses dashboard.

---

## LANGKAH 4 — Update Kode (bila ada perubahan)

Setiap kali ada update kode, cukup jalankan:

```bash
cd "D:\project AI\PDRB Analyser"
git add .
git commit -m "Update: deskripsi perubahan"
git push
```

Streamlit Cloud akan **otomatis redeploy** dalam beberapa detik.

---

## Perbandingan Platform

| Platform | Harga | RAM | Cocok untuk |
|---|---|---|---|
| **Streamlit Community Cloud** | Gratis | 1 GB | Demo, sharing tim kecil |
| **Railway** | $5/bln | 512 MB–8 GB | Produksi ringan |
| **Render** | Gratis* | 512 MB | Dev/staging |
| **Hugging Face Spaces** | Gratis | 16 GB | Data science apps |

*Render gratis: app "tidur" setelah 15 menit tidak diakses.

---

## Tips Keamanan

- Gunakan repo **Private** di GitHub
- Jangan pernah commit file `users.yaml` atau `.xlsx` ke repo
- Ganti password default admin setelah deploy pertama
- Aktifkan 2FA di akun GitHub

---

## Troubleshooting

| Error | Solusi |
|---|---|
| `ModuleNotFoundError` | Pastikan package ada di `requirements.txt` |
| `FileNotFoundError` untuk Excel | Upload file via halaman Manajemen Data |
| App lambat saat pertama dibuka | Normal — Streamlit Cloud "cold start" ~30 detik |
| Memory error | Upgrade ke plan berbayar atau gunakan Railway |

---

*PDRB Analyzer v2.0 — M@I-2026*
