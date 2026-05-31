"""
PDRB Analyzer Dashboard
Entry point utama — login & navigasi
"""

import os
import sys
import streamlit as st
import yaml
from yaml.loader import SafeLoader

# Pastikan path project dikenali
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

# ──────────────────────────────────────────────────────────────────────────────
# KONFIGURASI HALAMAN
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDRB Analyzer | Jawa Tengah",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global dark base ─────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background-color: #0d1117 !important;
    color: #e6edf3 !important;
}
[data-testid="stHeader"] {
    background-color: #0d1117 !important;
    border-bottom: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stMain"], .main .block-container {
    background-color: #0d1117 !important;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important;
    border-right: 1px solid rgba(0,212,170,0.2) !important;
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
div[data-testid="stSidebarNav"] { display: none; }
[data-testid="stSidebar"] .stRadio > label { color: #8b949e !important; }
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    font-size: 0.92rem !important;
}

/* ── Radio buttons nav style ──────────────────────────────── */
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    padding: 0.45rem 0.7rem !important;
    border-radius: 7px !important;
    margin-bottom: 2px !important;
    transition: background 0.2s !important;
    display: block !important;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
    background: rgba(0,212,170,0.1) !important;
}

/* ── Cards / containers ──────────────────────────────────── */
[data-testid="stMetric"] {
    background: #161b22 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    padding: 0.8rem !important;
}
[data-testid="stMetricLabel"] { color: #8b949e !important; }
[data-testid="stMetricValue"] { color: #e6edf3 !important; }

/* ── Tabs ─────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #161b22 !important;
    border-radius: 10px 10px 0 0 !important;
    border-bottom: 2px solid rgba(0,212,170,0.3) !important;
    gap: 4px !important;
    padding: 0 0.5rem !important;
}
.stTabs [data-baseweb="tab"] {
    font-size: 0.9rem !important;
    color: #8b949e !important;
    padding: 0.6rem 1.1rem !important;
    border-radius: 8px 8px 0 0 !important;
    border: none !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #00d4aa !important;
    background: rgba(0,212,170,0.1) !important;
    border-bottom: 2px solid #00d4aa !important;
}

/* ── Expander ─────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    color: #e6edf3 !important;
    font-weight: 600 !important;
}

/* ── Selectbox / input ────────────────────────────────────── */
[data-testid="stSelectbox"] div,
[data-testid="stMultiSelect"] div {
    background: #161b22 !important;
    border-color: rgba(255,255,255,0.12) !important;
    color: #e6edf3 !important;
}

/* ── Dataframe ────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    background: #161b22 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}

/* ── Divider ──────────────────────────────────────────────── */
hr { border-color: rgba(255,255,255,0.08) !important; }

/* ── Buttons ──────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #00d4aa, #4f8ef7) !important;
    color: #0d1117 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
}
.stButton > button:hover {
    opacity: 0.88 !important;
    transform: translateY(-1px) !important;
}

/* ── Main header component ────────────────────────────────── */
.main-header {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a2332 100%);
    border: 1px solid rgba(0,212,170,0.25);
    border-left: 4px solid #00d4aa;
    padding: 1.1rem 1.6rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
    color: #e6edf3;
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
.main-header h1 { margin: 0; font-size: 1.7rem; color: #e6edf3; }
.main-header p  { margin: 0.2rem 0 0; opacity: 0.75; font-size: 0.9rem; color: #8b949e; }

/* ── Metric card (custom HTML) ────────────────────────────── */
.metric-card {
    background: #161b22;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #484f58; }

/* ── Info / warning / success banners ────────────────────── */
[data-testid="stAlert"] {
    background: #161b22 !important;
    border-radius: 8px !important;
    border-left-width: 4px !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# SISTEM LOGIN
# ──────────────────────────────────────────────────────────────────────────────
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

# streamlit_authenticator tetap diimport untuk fitur manajemen user
try:
    import streamlit_authenticator as stauth
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False


def load_users():
    if os.path.exists(config.USERS_FILE):
        with open(config.USERS_FILE) as f:
            return yaml.load(f, Loader=SafeLoader)
    return None


def save_users(users_cfg):
    with open(config.USERS_FILE, "w") as f:
        yaml.dump(users_cfg, f, default_flow_style=False)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifikasi password dengan bcrypt."""
    try:
        if BCRYPT_AVAILABLE:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        # Fallback: bandingkan langsung (tidak aman, hanya untuk dev)
        return plain == hashed
    except Exception:
        return False


def check_login():
    """
    Tampilkan form login native Streamlit.
    Returns (authenticated: bool, name: str, username: str).
    """
    # Sudah login sebelumnya (session masih aktif)
    if st.session_state.get("authenticated"):
        return (
            True,
            st.session_state.get("name", ""),
            st.session_state.get("username", ""),
        )

    users_cfg = load_users()
    # Bypass jika tidak ada file users (mode dev)
    if not users_cfg:
        st.session_state["authenticated"] = True
        st.session_state["name"]          = "Admin"
        st.session_state["username"]      = "admin"
        st.session_state["role"]          = "admin"
        return True, "Admin", "admin"

    # ── Tampilan form login ──
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        st.markdown("""
        <div style="text-align:center;padding:1.5rem 0 1rem;">
            <h2>📊 PDRB Analyzer</h2>
            <p style="color:#666;">Dashboard Analisis Ekonomi Jawa Tengah</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            st.subheader("🔐 Login")
            username = st.text_input("Username", placeholder="Masukkan username")
            password = st.text_input("Password", type="password",
                                     placeholder="Masukkan password")
            submitted = st.form_submit_button("Login", use_container_width=True,
                                              type="primary")

        if submitted:
            users = users_cfg.get("credentials", {}).get("usernames", {})
            if username in users:
                stored_hash = users[username].get("password", "")
                if verify_password(password, stored_hash):
                    st.session_state["authenticated"] = True
                    st.session_state["name"]          = users[username].get("name", username)
                    st.session_state["username"]      = username
                    st.session_state["role"]          = "admin" if username == "admin" else "user"
                    st.rerun()
                else:
                    st.error("❌ Password salah.")
            else:
                st.error("❌ Username tidak ditemukan.")

    return False, None, None


# ──────────────────────────────────────────────────────────────────────────────
# NAVIGASI SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────
PAGES = {
    "🏠 Beranda":                    "home",
    "📋 Dashboard Ringkasan":        "ringkasan",
    "🔍 Analisis Satu Wilayah":      "analisis_wilayah",
    "🗺️ Analisis Regional":          "analisis_regional",
    "📈 Proyeksi PDRB":              "proyeksi",
    "📄 Generate Laporan":           "laporan",
    "📖 Petunjuk Penggunaan":        "petunjuk",
    "⚙️ Manajemen Data & User":      "manajemen",
}


def sidebar_nav(name):
    with st.sidebar:
        # ── Logo / Brand ──────────────────────────────────────
        st.markdown("""
        <div style="padding:1rem 0.5rem 0.8rem;">
            <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.3rem;">
                <div style="background:linear-gradient(135deg,#00d4aa,#4f8ef7);
                            width:38px;height:38px;border-radius:10px;
                            display:flex;align-items:center;justify-content:center;
                            font-size:1.2rem;flex-shrink:0;">📊</div>
                <div>
                    <div style="font-weight:800;font-size:1.05rem;
                                color:#e6edf3;letter-spacing:0.02em;">
                        PDRB Analyzer
                    </div>
                    <div style="font-size:0.72rem;color:#00d4aa;font-weight:600;
                                letter-spacing:0.05em;">
                        JAWA TENGAH
                    </div>
                </div>
            </div>
            <div style="height:1px;background:linear-gradient(90deg,#00d4aa,transparent);
                        margin:0.5rem 0;opacity:0.4;"></div>
        </div>
        """, unsafe_allow_html=True)

        # ── User badge ─────────────────────────────────────────
        st.markdown(f"""
        <div style="background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.2);
                    border-radius:8px;padding:0.45rem 0.7rem;margin-bottom:0.6rem;
                    display:flex;align-items:center;gap:0.5rem;">
            <span style="font-size:1rem;">👤</span>
            <span style="font-size:0.85rem;font-weight:600;color:#e6edf3;">{name}</span>
        </div>
        """, unsafe_allow_html=True)

        # ── Navigasi ───────────────────────────────────────────
        st.markdown('<div style="font-size:0.7rem;color:#484f58;font-weight:700;'
                    'text-transform:uppercase;letter-spacing:0.1em;'
                    'margin-bottom:0.3rem;padding-left:0.2rem;">Menu</div>',
                    unsafe_allow_html=True)

        page_names = list(PAGES.keys())
        selected   = st.radio("Navigasi", page_names, label_visibility="collapsed")

        st.markdown('<div style="height:1px;background:rgba(255,255,255,0.06);'
                    'margin:0.8rem 0;"></div>', unsafe_allow_html=True)

        # ── Logout ─────────────────────────────────────────────
        if st.button("🚪 Logout", use_container_width=True):
            for k in ["authenticated", "name", "username", "role"]:
                st.session_state.pop(k, None)
            st.rerun()

        # ── Footer branding M@I-2026 ───────────────────────────
        st.markdown("""
        <div style="position:fixed;bottom:0;left:0;width:240px;
                    padding:0.7rem 1rem;
                    background:linear-gradient(0deg,#0d1117,transparent);
                    border-top:1px solid rgba(0,212,170,0.15);">
            <div style="font-size:0.72rem;color:#484f58;margin-bottom:2px;">
                PDRB Analyzer v2.0 · BPS Jawa Tengah
            </div>
            <div style="font-size:0.82rem;font-weight:800;
                        background:linear-gradient(90deg,#00d4aa,#4f8ef7);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        letter-spacing:0.08em;">
                ◈ M@I-2026
            </div>
        </div>
        """, unsafe_allow_html=True)

    return PAGES[selected]


# ──────────────────────────────────────────────────────────────────────────────
# HALAMAN BERANDA
# ──────────────────────────────────────────────────────────────────────────────
def page_home():
    from data.loader import load_all_data

    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1117 0%,#161b22 60%,#1a2332 100%);
                border:1px solid rgba(0,212,170,0.22);border-left:4px solid #00d4aa;
                padding:1.2rem 1.8rem;border-radius:14px;margin-bottom:1.4rem;
                box-shadow:0 4px 32px rgba(0,0,0,0.5);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <h1 style="margin:0;font-size:1.75rem;font-weight:800;color:#e6edf3;">
                    📊 Dashboard PDRB Analyzer
                </h1>
                <p style="margin:0.3rem 0 0;color:#8b949e;font-size:0.9rem;">
                    Analisis Produk Domestik Regional Bruto Kabupaten/Kota – Provinsi Jawa Tengah
                </p>
            </div>
            <div style="text-align:right;flex-shrink:0;margin-left:1rem;">
                <div style="font-size:0.68rem;color:#484f58;font-weight:600;
                            text-transform:uppercase;letter-spacing:0.08em;">Built by</div>
                <div style="font-size:1rem;font-weight:800;
                            background:linear-gradient(90deg,#00d4aa,#4f8ef7);
                            -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                            letter-spacing:0.1em;">◈ M@I-2026</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with st.spinner("Memuat data..."):
        try:
            pdrb_data, penduduk_data, kode_wilayah = load_all_data()
            n_kab     = len([k for k in kode_wilayah if k != "3300"])
            n_periods = len(pdrb_data.get("3300", {}).get("adhb", {}).get("periods", []))
            n_sectors = len(pdrb_data.get("3300", {}).get("adhb", {}).get("sectors", {}))

            with col1:
                st.metric("Kabupaten/Kota", f"{n_kab}", help="Jumlah kab/kota di Jawa Tengah")
            with col2:
                st.metric("Periode Data", f"{n_periods} triwulan",
                          help="Jumlah periode triwulanan tersedia")
            with col3:
                st.metric("Lapangan Usaha", f"{n_sectors}",
                          help="Jumlah sektor & sub-sektor PDRB")
            with col4:
                kelompok_set = set(v["kelompok"] for k, v in kode_wilayah.items() if k != "3300")
                st.metric("Kelompok Pembangunan", f"{len(kelompok_set)}",
                          help="Eks-Karesidenan/kelompok pembangunan regional")

        except Exception as e:
            st.warning(f"Gagal memuat data: {e}")
            return

    st.divider()
    st.subheader("📋 Fitur Dashboard")

    features = [
        ("🔍", "Analisis Satu Wilayah",
         "Grafik PDRB, distribusi, pertumbuhan QtoQ/YoY/CtC, LQ, Shift Share, dan RRG untuk satu kabupaten/kota."),
        ("🗺️", "Analisis Regional",
         "Perbandingan antar kab/kota, peta choropleth, ketimpangan (Williamson, Klassen, Theil), dan RRG regional."),
        ("📈", "Proyeksi PDRB",
         "Proyeksi nilai PDRB ke depan menggunakan berbagai metode statistik (Trend, Moving Average, ARIMA, dll.)."),
        ("📄", "Generate Laporan",
         "Buat laporan PDF/Excel otomatis berisi tabel dan grafik hasil analisis yang dipilih."),
        ("📖", "Petunjuk Penggunaan",
         "Penjelasan lengkap setiap fitur, metode analisis, rumus, dan interpretasi hasil."),
        ("⚙️", "Manajemen Data & User",
         "Upload data terbaru, kelola user, dan lihat log aktivitas sistem."),
    ]

    cols = st.columns(3)
    for i, (icon, name, desc) in enumerate(features):
        with cols[i % 3]:
            st.info(f"**{icon} {name}**\n\n{desc}")

    st.divider()
    st.subheader("📊 Ringkasan PDRB Terkini (ADHB)")

    try:
        import pandas as pd

        # Tentukan periode referensi = periode terakhir yang ada di mayoritas wilayah
        prov_perds = sorted(pdrb_data.get("3300", {}).get("adhb", {}).get("periods", []))
        last_period = prov_perds[-1] if prov_perds else None

        if not last_period:
            st.warning("Data PDRB belum tersedia.")
        else:
            # Bangun tabel lengkap semua wilayah (provinsi + semua kab/kota)
            rows = []

            # Baris provinsi
            prov_val = pdrb_data.get("3300", {}).get("adhb", {}).get("total", {}).get(last_period)
            prov_info = kode_wilayah.get("3300", {"name": "Prov. Jawa Tengah", "kelompok": "Provinsi"})
            rows.append({
                "Kode": "3300",
                "Wilayah": prov_info["name"],
                "Kelompok": "Provinsi",
                "PDRB ADHB (Juta Rp)": prov_val,
                "Periode": last_period,
            })

            # Baris semua kab/kota
            for kode, info in sorted(kode_wilayah.items(), key=lambda x: x[0]):
                if kode == "3300":
                    continue
                tbl_kab = pdrb_data.get(kode, {}).get("adhb", {})
                # Ambil nilai pada last_period; jika kosong coba periode terakhir kab itu sendiri
                val = tbl_kab.get("total", {}).get(last_period)
                prd_kab = sorted(tbl_kab.get("periods", []))
                perd_ref = last_period
                if not val and prd_kab:
                    perd_ref = prd_kab[-1]
                    val = tbl_kab["total"].get(perd_ref)
                rows.append({
                    "Kode": kode,
                    "Wilayah": info["name"],
                    "Kelompok": info.get("kelompok", ""),
                    "PDRB ADHB (Juta Rp)": val,
                    "Periode": perd_ref,
                })

            df_all = pd.DataFrame(rows)

            # Metrik ringkas
            n_wilayah = len(df_all) - 1  # exclude provinsi
            n_valid   = df_all[df_all["Kode"] != "3300"]["PDRB ADHB (Juta Rp)"].notna().sum()
            st.caption(
                f"Periode referensi: **{last_period}** | "
                f"Wilayah tersedia: **{n_valid}/{n_wilayah}** kab/kota"
            )

            # Format angka untuk tampilan
            df_display = df_all.copy()
            df_display["PDRB ADHB (Juta Rp)"] = df_display["PDRB ADHB (Juta Rp)"].apply(
                lambda x: f"{x:,.2f}" if pd.notna(x) and x else "-"
            )

            # Tampilkan tabel
            st.dataframe(
                df_display[["Kode", "Wilayah", "Kelompok", "PDRB ADHB (Juta Rp)", "Periode"]],
                use_container_width=True,
                hide_index=True,
                height=700,
            )

    except Exception as e:
        st.warning(f"Gagal memuat ringkasan: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.get("authenticated"):
        authenticated, name, username = check_login()
        if not authenticated:
            return
    else:
        name = st.session_state.get("name", "User")

    page = sidebar_nav(name)

    if page == "home":
        page_home()
    elif page == "ringkasan":
        from pages import p0_ringkasan
        p0_ringkasan.render()
    elif page == "analisis_wilayah":
        from pages import p1_analisis_wilayah
        p1_analisis_wilayah.render()
    elif page == "analisis_regional":
        from pages import p2_analisis_regional
        p2_analisis_regional.render()
    elif page == "proyeksi":
        from pages import p3_proyeksi
        p3_proyeksi.render()
    elif page == "laporan":
        from pages import p4_laporan
        p4_laporan.render()
    elif page == "petunjuk":
        from pages import p5_petunjuk
        p5_petunjuk.render()
    elif page == "manajemen":
        from pages import p6_manajemen
        p6_manajemen.render()


if __name__ == "__main__":
    main()
