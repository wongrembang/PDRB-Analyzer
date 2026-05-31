"""
Halaman 6: Manajemen Data & User
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import hashlib
import streamlit as st
import pandas as pd
import yaml
from yaml.loader import SafeLoader
from datetime import datetime

import config


def _hash_password(plain: str) -> str:
    """Hash password sederhana (bcrypt via streamlit-authenticator lebih aman)."""
    try:
        import bcrypt
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        # Fallback: sha256 (kurang aman, hanya untuk demo)
        return "$plain$" + hashlib.sha256(plain.encode()).hexdigest()


def _load_users():
    if os.path.exists(config.USERS_FILE):
        with open(config.USERS_FILE) as f:
            return yaml.load(f, Loader=SafeLoader)
    return {"credentials": {"usernames": {}},
            "cookie": {"expiry_days": 30,
                       "key": "pdrb_key",
                       "name": "pdrb_cookie"}}


def _save_users(cfg):
    with open(config.USERS_FILE, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)


def _log_action(action: str):
    log_fp = os.path.join(config.BASE_DIR, "activity.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user = st.session_state.get("username", "unknown")
    with open(log_fp, "a") as f:
        f.write(f"[{timestamp}] [{user}] {action}\n")


def render():
    st.markdown("""
    <div style="background:linear-gradient(90deg,#7f7f7f,#17becf);
         padding:0.8rem 1.2rem;border-radius:8px;color:white;margin-bottom:1rem;">
        <h2 style="margin:0">⚙️ Manajemen Data & User</h2>
        <p style="margin:0;opacity:0.9">Upload data baru, kelola user, pantau aktivitas sistem</p>
    </div>
    """, unsafe_allow_html=True)

    current_user = st.session_state.get("username", "guest")
    is_admin = current_user in ("admin", "guest")

    tab1, tab2, tab3 = st.tabs([
        "📁 Upload Data",
        "👥 Manajemen User",
        "📋 Log Aktivitas",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: UPLOAD DATA
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader("📁 Upload File Data Terbaru")
        st.markdown("""
        Upload file Excel untuk memperbarui data. Format file harus sama dengan
        file original. Setelah upload berhasil, cache akan direset otomatis.
        """)

        file_configs = [
            {
                "label":    "File PDRB Triwulanan 3 Sektor",
                "hint":     "Format: sheet = kode wilayah (misal 3300, 3301, dst). "
                            "Setiap sheet berisi Tabel 1 (ADHB) dan Tabel 2 (ADHK).",
                "target":   config.PDRB_FILE,
                "key":      "upload_pdrb",
            },
            {
                "label":    "Jumlah Penduduk Triwulanan",
                "hint":     "Format: kolom = periode triwulanan, baris = kab/kota.",
                "target":   config.PENDUDUK_FILE,
                "key":      "upload_pop",
            },
            {
                "label":    "Kode Wilayah",
                "hint":     "Format: Kode | Nama Kab/Kota | Kelompok Pembangunan.",
                "target":   config.KODE_WILAYAH_FILE,
                "key":      "upload_kode",
            },
        ]

        for fc in file_configs:
            with st.expander(f"📄 {fc['label']}"):
                st.caption(fc["hint"])
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    uploaded = st.file_uploader(
                        f"Upload {fc['label']}",
                        type=["xlsx", "xls"],
                        key=fc["key"],
                        label_visibility="collapsed",
                    )
                with col_b:
                    if os.path.exists(fc["target"]):
                        mod_time = os.path.getmtime(fc["target"])
                        st.caption(f"File saat ini:\n"
                                   f"{datetime.fromtimestamp(mod_time).strftime('%d/%m/%Y %H:%M')}")

                if uploaded and is_admin:
                    # Backup file lama
                    if os.path.exists(fc["target"]):
                        bak = fc["target"] + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        shutil.copy2(fc["target"], bak)

                    with open(fc["target"], "wb") as f:
                        f.write(uploaded.getbuffer())

                    # Hapus cache
                    if os.path.exists(config.CACHE_FILE):
                        os.remove(config.CACHE_FILE)

                    # Clear st.cache_data
                    st.cache_data.clear()

                    _log_action(f"Upload file: {fc['label']} ({uploaded.name})")
                    st.success(f"✅ File berhasil diupload dan cache direset!")
                elif uploaded and not is_admin:
                    st.error("⛔ Hanya admin yang dapat mengupload data.")

        st.divider()
        st.subheader("🗑️ Reset Cache Data")
        st.caption("Cache dibuat otomatis untuk mempercepat loading. Reset jika data terasa stale.")
        if st.button("🔄 Reset Cache Sekarang", key="reset_cache"):
            if is_admin:
                if os.path.exists(config.CACHE_FILE):
                    os.remove(config.CACHE_FILE)
                st.cache_data.clear()
                _log_action("Reset cache data")
                st.success("✅ Cache berhasil direset. Data akan dimuat ulang saat halaman diakses.")
            else:
                st.error("⛔ Hanya admin yang dapat mereset cache.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: MANAJEMEN USER
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        if not is_admin:
            st.warning("⛔ Hanya admin yang dapat mengakses manajemen user.")
            return

        st.subheader("👥 Daftar User")
        users_cfg = _load_users()
        usernames = users_cfg.get("credentials", {}).get("usernames", {})

        # Tampilkan tabel user
        user_rows = []
        for uname, udata in usernames.items():
            user_rows.append({
                "Username": uname,
                "Nama": udata.get("name", ""),
                "Email": udata.get("email", ""),
            })
        if user_rows:
            st.dataframe(pd.DataFrame(user_rows), use_container_width=True,
                         hide_index=True)
        else:
            st.info("Belum ada user terdaftar.")

        st.divider()

        # Tambah User
        with st.expander("➕ Tambah User Baru"):
            col1, col2 = st.columns(2)
            with col1:
                new_uname = st.text_input("Username", key="new_uname")
                new_name  = st.text_input("Nama Lengkap", key="new_name")
            with col2:
                new_email = st.text_input("Email", key="new_email")
                new_pass  = st.text_input("Password", type="password", key="new_pass")
                new_pass2 = st.text_input("Konfirmasi Password", type="password",
                                           key="new_pass2")

            if st.button("➕ Tambah User", key="btn_add_user"):
                if not all([new_uname, new_name, new_email, new_pass]):
                    st.error("Lengkapi semua field.")
                elif new_pass != new_pass2:
                    st.error("Password tidak cocok.")
                elif new_uname in usernames:
                    st.error("Username sudah digunakan.")
                else:
                    hashed = _hash_password(new_pass)
                    usernames[new_uname] = {
                        "name":     new_name,
                        "email":    new_email,
                        "password": hashed,
                    }
                    users_cfg["credentials"]["usernames"] = usernames
                    _save_users(users_cfg)
                    _log_action(f"Tambah user: {new_uname}")
                    st.success(f"✅ User '{new_uname}' berhasil ditambahkan.")
                    st.rerun()

        # Hapus/Reset User
        with st.expander("🗑️ Hapus / Reset Password User"):
            if usernames:
                del_user = st.selectbox("Pilih User", list(usernames.keys()),
                                         key="del_user")
                col3, col4 = st.columns(2)
                with col3:
                    if st.button("🗑️ Hapus User", key="btn_del"):
                        if del_user == "admin":
                            st.error("Tidak bisa hapus user admin.")
                        else:
                            del usernames[del_user]
                            users_cfg["credentials"]["usernames"] = usernames
                            _save_users(users_cfg)
                            _log_action(f"Hapus user: {del_user}")
                            st.success(f"User '{del_user}' dihapus.")
                            st.rerun()
                with col4:
                    new_pw = st.text_input("Password Baru", type="password",
                                            key="reset_pw")
                    if st.button("🔑 Reset Password", key="btn_reset_pw"):
                        if new_pw:
                            usernames[del_user]["password"] = _hash_password(new_pw)
                            users_cfg["credentials"]["usernames"] = usernames
                            _save_users(users_cfg)
                            _log_action(f"Reset password user: {del_user}")
                            st.success(f"Password '{del_user}' berhasil direset.")
                        else:
                            st.error("Masukkan password baru.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: LOG AKTIVITAS
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("📋 Log Aktivitas Sistem")
        log_fp = os.path.join(config.BASE_DIR, "activity.log")

        if os.path.exists(log_fp):
            with open(log_fp) as f:
                lines = f.readlines()

            lines = lines[::-1][:200]  # Tampilkan 200 entri terbaru
            log_df = []
            for line in lines:
                line = line.strip()
                if line:
                    log_df.append({"Log": line})

            if log_df:
                st.dataframe(pd.DataFrame(log_df), use_container_width=True,
                             hide_index=True, height=400)
            else:
                st.info("Log kosong.")

            if is_admin:
                if st.button("🗑️ Bersihkan Log", key="clear_log"):
                    open(log_fp, "w").close()
                    st.success("Log berhasil dibersihkan.")
                    st.rerun()
        else:
            st.info("Belum ada aktivitas yang dicatat.")

        st.divider()
        st.subheader("ℹ️ Informasi Sistem")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Cache PDRB", "Ada" if os.path.exists(config.CACHE_FILE) else "Belum ada")
            st.metric("GeoJSON Jawa Tengah",
                      "Ada" if os.path.exists(config.GEOJSON_FILE) else "Belum diunduh")
        with col2:
            if os.path.exists(config.PDRB_FILE):
                sz = os.path.getsize(config.PDRB_FILE) / 1024 / 1024
                mt = datetime.fromtimestamp(os.path.getmtime(config.PDRB_FILE))
                st.metric("File PDRB", f"{sz:.1f} MB",
                          delta=f"Diperbarui: {mt.strftime('%d/%m/%Y')}")
