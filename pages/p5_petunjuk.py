"""
Halaman 5: Petunjuk Penggunaan & Penjelasan Metode
"""

import streamlit as st


def render():
    st.markdown("""
    <div style="background:linear-gradient(90deg,#bcbd22,#2ca02c);
         padding:0.8rem 1.2rem;border-radius:8px;color:white;margin-bottom:1rem;">
        <h2 style="margin:0">📖 Petunjuk Penggunaan</h2>
        <p style="margin:0;opacity:0.9">Panduan fitur, metode analisis, dan interpretasi hasil</p>
    </div>
    """, unsafe_allow_html=True)

    sections = st.tabs([
        "🚀 Mulai Cepat",
        "🔍 Analisis Wilayah",
        "🗺️ Analisis Regional",
        "📈 Proyeksi",
        "📐 Metode Analisis",
        "🧪 Metode Lanjutan",
        "❓ FAQ",
    ])

    # ── MULAI CEPAT ──
    with sections[0]:
        st.markdown("""
## Selamat Datang di PDRB Analyzer

Dashboard ini dirancang untuk membantu analisis **Produk Domestik Regional Bruto (PDRB)**
kabupaten/kota di Provinsi Jawa Tengah secara komprehensif.

### Langkah Awal
1. **Login** menggunakan username dan password yang diberikan admin
2. Pilih menu dari **sidebar** di sebelah kiri
3. Mulai dengan **Analisis Satu Wilayah** untuk eksplorasi satu kabupaten/kota
4. Gunakan **Analisis Regional** untuk membandingkan antar wilayah
5. **Proyeksi PDRB** tersedia untuk prakiraan ke depan

### Struktur Data
| File | Isi |
|------|-----|
| `pdrb triwulanan 3 sektor.xlsx` | Data PDRB per kab/kota, ADHB & ADHK, 2010–2025 |
| `jumlah penduduk triwulanan.xlsx` | Estimasi penduduk per triwulan per kab/kota |
| `kode wilayah.xlsx` | Kode, nama, dan kelompok pembangunan kab/kota |

### Format Periode
Periode ditampilkan dalam format `YYYYQN`, misal:
- `2023Q1` = Triwulan I Tahun 2023 (Januari–Maret)
- `2024Q4` = Triwulan IV Tahun 2024 (Oktober–Desember)

### Tampilan Pertumbuhan
| Kode | Keterangan |
|------|-----------|
| **Q to Q** | Pertumbuhan triwulan ini vs triwulan sebelumnya |
| **Y on Y** | Pertumbuhan triwulan ini vs triwulan yang sama tahun lalu |
| **C to C** | Pertumbuhan kumulatif year-to-date vs periode yang sama tahun lalu |
        """)

    # ── ANALISIS WILAYAH ──
    with sections[1]:
        st.markdown("""
## Analisis Satu Wilayah

### 1. Grafik & Tabel
Menampilkan data PDRB dalam berbagai tampilan:
- **Nilai Absolut**: Nilai PDRB dalam juta rupiah
- **Distribusi (%)**: Persentase kontribusi setiap sektor terhadap total
- **Pertumbuhan**: Q to Q, Y on Y, atau C to C

**Pilihan interaktif:**
- Centang/hilangkan sektor atau sub-sektor
- Ganti jenis grafik (batang/garis)
- Filter rentang tahun

### 2. Distribusi ADHB (Treemap/Pie Chart)
Menampilkan distribusi PDRB Atas Dasar Harga Berlaku dalam bentuk visual:
- **Treemap**: Menunjukkan proporsi area sesuai nilai
- **Pie Chart**: Grafik lingkaran dengan persentase

### 3. Location Quotient (LQ)
Lihat bagian **Metode Analisis** untuk rumus lengkap.

### 4. Shift Share Analysis
Lihat bagian **Metode Analisis** untuk rumus lengkap.

### 5. RRG (Relative Regional Growth)
Grafik RRG menampilkan posisi setiap sektor dalam 4 kuadran berdasarkan
Relative Share (RS) dan Relative Growth Rate (RGR).
        """)

    # ── ANALISIS REGIONAL ──
    with sections[2]:
        st.markdown("""
## Analisis Regional

### Perbandingan Nilai
Bandingkan nilai PDRB antar kabupaten/kota:
- Pilih beberapa kab/kota dengan checkbox
- Filter kelompok pembangunan (Eks-Karesidenan)
- Tampilkan dalam grafik batang, garis, atau peta choropleth
- Pilih sektor yang ingin dibandingkan

### LQ & Shift Share Komparatif
Bandingkan nilai LQ dan komponen Shift Share antar kab/kota untuk
sektor-sektor tertentu.

### RRG Regional
Dua mode:
1. **Total PDRB**: Titik = kab/kota, berdasarkan PDRB total
2. **Per Lapangan Usaha**: Titik = kab/kota, untuk sektor tertentu

### Analisis Ketimpangan
| Indikator | Deskripsi |
|-----------|-----------|
| PDRB Per Kapita | PDRB ADHB ÷ Jumlah Penduduk |
| Williamson | Ketimpangan tertimbang populasi |
| Klassen | Klasifikasi 4 kuadran (maju/tertinggal) |
| Theil | Ketimpangan sensitif ekstrem |
| Kemiripan Struktur | Indeks Krugman/Cosine Similarity |

### Peta Choropleth
Membutuhkan GeoJSON batas wilayah Jawa Tengah (diunduh otomatis saat
pertama kali digunakan, butuh koneksi internet).
        """)

    # ── PROYEKSI ──
    with sections[3]:
        st.markdown("""
## Proyeksi PDRB

### Metode yang Tersedia

#### 1. Regresi Linear (Trend)
Memfit garis lurus y = a + b·t terhadap data historis.
- **Cocok untuk**: Tren pertumbuhan stabil jangka panjang
- **Output R²**: Mengukur seberapa baik garis memfit data (0–1)
- **Keterbatasan**: Tidak menangkap siklus atau fluktuasi

#### 2. Moving Average
Rata-rata bergerak 4 triwulan (satu tahun).
- **Cocok untuk**: Menghilangkan fluktuasi musiman
- **Keterbatasan**: Reaksi lambat terhadap perubahan tren

#### 3. Rata-rata Pertumbuhan Historis
Menggunakan rata-rata laju pertumbuhan periode sebelumnya.
- **Cocok untuk**: Proyeksi jangka pendek sederhana
- **Keterbatasan**: Sensitif terhadap outlier

#### 4. Exponential Smoothing (Holt)
Double exponential smoothing yang mempertimbangkan tren.
- **Cocok untuk**: Data dengan tren yang berubah
- **Otomatis**: Optimasi parameter α secara otomatis

### Tips Memilih Metode
- **Tren stabil** → Regresi Linear
- **Fluktuasi musiman tinggi** → Moving Average
- **Data terbatas** → Rata-rata Pertumbuhan
- **Tren dinamis** → Exponential Smoothing

### Interval Kepercayaan
Ditampilkan sebagai band ±10% dari nilai proyeksi. Ini merupakan
ilustrasi sederhana, bukan interval statistik yang ketat.
        """)

    # ── METODE ANALISIS ──
    with sections[4]:
        st.markdown("""
## Metode Analisis Ekonomi

### Location Quotient (LQ)

$$LQ_i = \\frac{e_i / e}{E_i / E}$$

**Keterangan:**
- $e_i$ = PDRB sektor $i$ di wilayah
- $e$ = Total PDRB wilayah
- $E_i$ = PDRB sektor $i$ di provinsi (referensi)
- $E$ = Total PDRB provinsi

**Interpretasi:**
| Nilai LQ | Kategori | Makna |
|----------|----------|-------|
| LQ ≥ 1,5 | Sektor Basis Kuat | Spesialisasi tinggi, potensi ekspor besar |
| 1,0 ≤ LQ < 1,5 | Sektor Basis | Memenuhi kebutuhan lokal + ekspor |
| LQ < 1,0 | Bukan Sektor Basis | Tidak mampu memenuhi kebutuhan lokal |

---

### Shift Share Analysis

Dekomposisi pertumbuhan menjadi 3 komponen:

**1. National/Provincial Share (NS)**
$$NS_i = e_{i0} \\cdot \\left(\\frac{E_t - E_0}{E_0}\\right)$$

Pertumbuhan yang disebabkan oleh pertumbuhan ekonomi provinsi secara keseluruhan.

**2. Industry Mix Effect (IM)**
$$IM_i = e_{i0} \\cdot \\left(\\frac{E_{it} - E_{i0}}{E_{i0}} - \\frac{E_t - E_0}{E_0}\\right)$$

Pertumbuhan karena komposisi sektor ekonomi (bauran industri).

**3. Competitive Effect (CE)**
$$CE_i = e_{i0} \\cdot \\left(\\frac{e_{it} - e_{i0}}{e_{i0}} - \\frac{E_{it} - E_{i0}}{E_{i0}}\\right)$$

Pertumbuhan karena keunggulan kompetitif wilayah (daya saing lokal).

**Interpretasi CE:**
- CE > 0: Sektor kompetitif (tumbuh lebih cepat dari provinsi)
- CE < 0: Sektor kurang kompetitif

---

### Relative Regional Growth (RRG)

Diadaptasi dari konsep BCG Growth-Share Matrix:

$$RS = \\frac{share_i^{wilayah}}{share_i^{provinsi}}, \\quad RGR = \\frac{g_i^{wilayah}}{g_i^{provinsi}}$$

**Kuadran:**
| Nama | RS | RGR | Arti |
|------|----|-----|------|
| ⭐ Stars | ≥1 | ≥1 | Dominan & tumbuh pesat → pertahankan/kembangkan |
| ❓ Question Marks | <1 | ≥1 | Potensi tinggi, share kecil → investasi |
| 🐄 Cash Cows | ≥1 | <1 | Dominan tapi melambat → pertahankan/diversifikasi |
| 🐕 Dogs | <1 | <1 | Kecil & lambat → evaluasi/transformasi |

---

### Indeks Williamson

$$I_W = \\frac{\\sqrt{\\sum_i \\left(y_i - \\bar{y}\\right)^2 \\cdot \\frac{f_i}{n}}}{\\bar{y}}$$

- $y_i$ = PDRB per kapita wilayah $i$
- $\\bar{y}$ = Rata-rata PDRB per kapita (= PDRB per kapita provinsi)
- $f_i$ = Jumlah penduduk wilayah $i$
- $n$ = Total penduduk
- Nilai 0 → merata; nilai menuju 1+ → timpang

---

### Tipologi Klassen

Klasifikasi berdasarkan perbandingan dengan rata-rata provinsi:

| | PDRB/kapita > Prov | PDRB/kapita < Prov |
|--|----|----|
| **Pertumbuhan > Prov** | Maju & Tumbuh Pesat (I) | Berkembang Cepat (III) |
| **Pertumbuhan < Prov** | Maju tapi Tertekan (II) | Relatif Tertinggal (IV) |

---

### Indeks Theil

$$T = \\frac{1}{n} \\sum_i \\frac{y_i}{\\bar{y}} \\ln\\left(\\frac{y_i}{\\bar{y}} \\cdot n\\right)$$

- Nilai 0 → distribusi merata
- Makin besar → makin timpang
- Lebih sensitif terhadap ketimpangan di ujung distribusi dibanding Williamson

---

### Kemiripan Struktur Ekonomi (Krugman Index)

$$KSI_{ij} = \\sum_k |s_{ik} - s_{jk}|$$

- $s_{ik}$ = share sektor $k$ di wilayah $i$
- Nilai 0 → struktur identik
- Nilai 2 → struktur sangat berbeda (tidak ada kesamaan sama sekali)
        """)

    # ── METODE LANJUTAN ──
    with sections[5]:
        st.markdown("""
## Metode Analisis Lanjutan

Fitur-fitur berikut merupakan tambahan analisis ekonomi regional tingkat lanjut
yang tersedia di halaman **Analisis Satu Wilayah** (tab Sektor Prioritas & Base Multiplier)
dan **Analisis Regional** (tab Konvergensi, HHI, Gravitasi, Overlay Prioritas).
        """)

        adv1, adv2, adv3, adv4, adv5, adv6 = st.tabs([
            "📉 Konvergensi",
            "🎯 HHI Diversifikasi",
            "🌐 Gravitasi Ekonomi",
            "⭐ Overlay Prioritas",
            "🏗️ Base Multiplier",
            "📊 Output Gap",
        ])


        with adv1:
            st.markdown("""
### Konvergensi / Divergensi

Mengukur apakah kesenjangan PDRB per kapita antar wilayah **mengecil (konvergen)** atau **membesar (divergen)**.

**Sigma Convergence:** Std dev ln(PDRB/kapita) per periode. Turun = konvergen. Naik = divergen.

**Beta Convergence:** Regresi pertumbuhan vs PDRB awal.
Formula: `g(y) = a + B * ln(y0) + e`

| Koef B | Interpretasi |
|--------|-------------|
| < 0 | Konvergen - wilayah miskin tumbuh lebih cepat |
| > 0 | Divergen - wilayah kaya tumbuh lebih cepat |
| = 0 | Tidak ada pola konvergensi |
            """)

        with adv2:
            st.markdown("""
### HHI - Diversifikasi Ekonomi

Rumus: **HHI = Jumlah(si kuadrat)** dimana si = share sektor i terhadap PDRB total.

| HHI | Kategori | Makna |
|-----|---------|-------|
| < 0.15 | Terdiversifikasi | Ekonomi tersebar merata, lebih resilient |
| 0.15-0.25 | Moderat | Cukup beragam |
| > 0.25 | Terkonsentrasi | Rentan guncangan pada sektor dominan |

HHI menurun dari waktu ke waktu = diversifikasi sedang berlangsung (positif).
            """)

        with adv3:
            st.markdown("""
### Model Gravitasi Ekonomi

Rumus: **I(i,j) = PDRB_i x PDRB_j / jarak_ij kuadrat**

Jarak dihitung dengan Haversine formula (jarak lingkaran besar di bumi).

| Nilai Interaksi | Makna |
|-----------------|-------|
| Tinggi | Integrasi ekonomi kuat - perdagangan, investasi, mobilitas |
| Sedang | Perlu peningkatan konektivitas |
| Rendah | Jarak jauh atau PDRB kecil |

Pasangan dengan interaksi tinggi adalah kandidat kawasan metropolitan / koridor ekonomi.
            """)

        with adv4:
            st.markdown("""
### Overlay Matriks Prioritas Sektor

Menggabungkan tiga metode: **LQ + Shift Share + RRG** menjadi skor prioritas terpadu.

| Komponen | Kriteria | Skor |
|----------|----------|------|
| LQ | >= 1 (sektor basis) | +2 |
| CE (Shift Share) | > 0 (kompetitif) | +2 |
| RRG Kuadran | Leading/Improving/Weakening/Lagging | 3/2/1/0 |

| Skor | Label | Rekomendasi |
|------|-------|-------------|
| 6-7 | Unggulan Utama | Pertahankan & kembangkan |
| 4-5 | Potensial | Dorong dengan kebijakan fiskal |
| 2-3 | Perlu Perhatian | Monitor & intervensi |
| 0-1 | Tertinggal | Evaluasi & pertimbangkan diversifikasi |
            """)

        with adv5:
            st.markdown("""
### Economic Base Multiplier

Sektor Basis = sektor dengan LQ >= 1 (produksi melebihi kebutuhan lokal).

**PDRB Basis sektor i** = PDRB(i) x (1 - 1/LQ(i))

**Multiplier (m)** = PDRB_total / PDRB_basis

Artinya: setiap Rp 1 ekspansi di sektor basis mendorong total PDRB sebesar Rp m.

Multiplier tinggi = daya ungkit besar. Multiplier rendah = sektor basis perlu diperkuat.
            """)

        with adv6:
            st.markdown("""
### Output Gap

Output gap mengukur selisih antara **PDRB aktual** dan **PDRB potensial**, dinyatakan dalam persen terhadap potensi.

**Rumus:**
`Output Gap (%) = (PDRB_aktual - PDRB_potensial) / PDRB_potensial x 100`

**Metode estimasi PDRB Potensial: HP Filter (Hodrick-Prescott)**

HP Filter memisahkan deret waktu PDRB menjadi dua komponen:
- **Komponen Tren** (PDRB Potensial): kapasitas produksi jangka panjang
- **Komponen Siklus** (Output Gap): fluktuasi jangka pendek di atas/bawah tren

Minimasi fungsi objektif:
`min { Sum(y_t - tau_t)^2 + lambda * Sum[(tau_{t+1} - tau_t) - (tau_t - tau_{t-1})]^2 }`

Parameter lambda = 1.600 adalah standar untuk data **triwulanan** (Hodrick & Prescott, 1997).

---

**Interpretasi Output Gap:**

| Output Gap | Kondisi | Implikasi Kebijakan |
|------------|---------|---------------------|
| > +2% | Ekspansif kuat | Waspadai overheating, pertimbangkan kebijakan kontraktif (kenaikan suku bunga, pengurangan stimulus) |
| 0% s/d +2% | Ekspansif moderat | Pertumbuhan sehat, pertahankan kebijakan saat ini |
| -2% s/d 0% | Resesif ringan | Dorong stimulasi fiskal atau investasi infrastruktur |
| < -2% | Resesif kuat | Intervensi kebijakan segera diperlukan |

---

**Sigma Convergence Output Gap:**
Jika output gap beberapa wilayah bergerak bersama (menyempit atau melebar secara serentak),
ini mengindikasikan adanya **sinkronisasi siklus ekonomi** antar wilayah.

**Catatan Penting:**
- Gunakan PDRB ADHK (harga konstan) untuk output gap agar tidak terpengaruh inflasi
- Diperlukan minimal **8 periode** data untuk estimasi HP Filter yang akurat
- Hasil dapat berbeda tergantung rentang data yang digunakan (end-point bias)
            """)

