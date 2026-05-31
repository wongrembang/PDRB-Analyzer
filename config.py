"""
Konfigurasi global PDRB Analyzer Dashboard
"""
import os

# Direktori dasar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# File data utama
PDRB_FILE = os.path.join(BASE_DIR, "pdrb triwulanan 3 sektor.xlsx")
PENDUDUK_FILE = os.path.join(BASE_DIR, "jumlah penduduk triwulanan.xlsx")
KODE_WILAYAH_FILE = os.path.join(BASE_DIR, "kode wilayah.xlsx")
USERS_FILE = os.path.join(BASE_DIR, "users.yaml")

# File cache
CACHE_FILE = os.path.join(DATA_DIR, "cache_pdrb.pkl")
GEOJSON_FILE = os.path.join(ASSETS_DIR, "jateng.geojson")

# URL GeoJSON Jawa Tengah (dari sumber publik)
GEOJSON_URL = "https://raw.githubusercontent.com/superpikar/indonesia-geojson/master/jawa-tengah.geojson"
GEOJSON_URL_ALT = "https://raw.githubusercontent.com/ans-4175/peta-indonesia-geojson/master/33.jawa-tengah.geojson"

# Warna tema (dark mode optimized)
COLORS = {
    "primary":   "#00d4aa",
    "secondary": "#4f8ef7",
    "success":   "#3fb950",
    "danger":    "#f85149",
    "warning":   "#d29922",
    "info":      "#58a6ff",
    "palette": [
        "#00d4aa", "#4f8ef7", "#f78166", "#d2a8ff", "#ffa657",
        "#79c0ff", "#56d364", "#ff7b72", "#e3b341", "#bc8cff",
        "#ff9a3c", "#63e6be", "#74b9ff", "#fd79a8", "#a29bfe",
        "#55efc4", "#fdcb6e", "#e17055", "#6c5ce7", "#00cec9",
    ],
}

# Dark chart theme constants
CHART_BG    = "#161b22"
CHART_PAPER = "#0d1117"
CHART_GRID  = "rgba(255,255,255,0.07)"
CHART_TEXT  = "#e6edf3"

# Konfigurasi chart default
CHART_HEIGHT = 500
MAP_HEIGHT = 550

# Konfigurasi analisis
LQ_THRESHOLD = 1.0          # LQ >= 1 = sektor basis
RRG_PERIODS = 8             # Jumlah triwulan untuk RRG

# Label kelompok pembangunan
KELOMPOK_LABEL = {
    "PROVINSI JAWA TENGAH": "Provinsi Jawa Tengah",
    "Banyumas": "Eks Karesidenan Banyumas",
    "Kedu": "Eks Karesidenan Kedu",
    "Surakarta": "Eks Karesidenan Surakarta",
    "Semarang": "Eks Karesidenan Semarang",
    "Pati": "Eks Karesidenan Pati",
    "Pekalongan": "Eks Karesidenan Pekalongan",
}

# Label tampilan
TABEL_LABELS = {
    "adhb": "PDRB Atas Dasar Harga Berlaku (ADHB)",
    "adhk": "PDRB Atas Dasar Harga Konstan (ADHK)",
}

PERTUMBUHAN_LABELS = {
    "qtq": "Pertumbuhan Q to Q (Triwulan ke Triwulan)",
    "yoy": "Pertumbuhan Y on Y (Tahun ke Tahun)",
    "ctc": "Pertumbuhan C to C (Kumulatif ke Kumulatif)",
    "nilai": "Nilai Absolut (Juta Rupiah)",
    "distribusi": "Distribusi / Share (%)",
}
