"""
Halaman 3: Proyeksi PDRB
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import config
from data.loader import load_all_data
from utils import analytics, charts
from utils.analytics import clean_kode


def render():
    st.markdown("""
    <div style="background:linear-gradient(90deg,#9467bd,#17becf);
         padding:0.8rem 1.2rem;border-radius:8px;color:white;margin-bottom:1rem;">
        <h2 style="margin:0">📈 Proyeksi PDRB</h2>
        <p style="margin:0;opacity:0.9">Prakiraan nilai PDRB menggunakan berbagai metode statistik</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Memuat data..."):
        pdrb_data, penduduk_data, kode_wilayah = load_all_data()

    # ── Pilih wilayah ──
    wilayah_opts = {v["name"]: k for k, v in kode_wilayah.items()}
    wilayah_opts_sorted = dict(sorted(wilayah_opts.items()))

    st.subheader("⚙️ Konfigurasi Proyeksi")
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_name = st.selectbox("Wilayah", list(wilayah_opts_sorted.keys()),
                                      key="proj_wil")
        kode = wilayah_opts_sorted[selected_name]
        tabel_choice = st.selectbox("Tabel", ["ADHB (Harga Berlaku)", "ADHK (Harga Konstan)"],
                                     key="proj_tbl")
        tabel = "adhb" if "ADHB" in tabel_choice else "adhk"

    with col2:
        method = st.selectbox("Metode Proyeksi", [
            ("trend",        "📈 Regresi Linear (Trend)"),
            ("moving_average", "📊 Moving Average"),
            ("avg_growth",   "📉 Rata-rata Pertumbuhan Historis"),
            ("exponential",  "🔮 Exponential Smoothing (Holt)"),
        ], format_func=lambda x: x[1], key="proj_method")
        method_key = method[0]

        n_forecast = st.slider("Periode Proyeksi ke Depan (Triwulan)", 1, 20, 8,
                                key="proj_n")

    with col3:
        n_history = st.slider("Data Historis yang Digunakan (Triwulan, 0=semua)",
                               0, 60, 0, key="proj_hist")
        n_hist = None if n_history == 0 else n_history

    # ── Pilih sektor ──
    if kode not in pdrb_data or tabel not in pdrb_data[kode]:
        st.error("Data tidak tersedia untuk wilayah ini.")
        return

    sectors = pdrb_data[kode][tabel]["sectors"]

    # ── Bangun daftar opsi sektor (utama + sub-sektor) ──
    main_scts = {k: v for k, v in sectors.items() if v["parent"] is None}
    sub_scts  = {k: v for k, v in sectors.items() if v["parent"] is not None}

    # sector_opts: key → label tampilan (dengan kode bersih)
    sector_opts = {"__total__": "▶ PDRB Total"}
    for k, v in main_scts.items():
        sector_opts[k] = f"{clean_kode(k)} – {v['name'][:55]}"
    for k, v in sub_scts.items():
        sector_opts[k] = f"  ↳ {clean_kode(k)} – {v['name'][:50]}"

    st.divider()
    st.subheader("📋 Pilih Sektor yang Diproyeksikan")

    col_lv, col_multi = st.columns([1, 2])
    with col_lv:
        sec_level = st.radio(
            "Tampilkan Sektor",
            ["Utama saja", "Sub-sektor saja", "Semua"],
            horizontal=False, key="proj_sec_level",
        )
    with col_multi:
        multi_sec = st.checkbox("Proyeksikan beberapa sektor sekaligus",
                                value=False, key="proj_multi")

    # Filter opsi sesuai level
    if sec_level == "Utama saja":
        filtered_opts = {k: v for k, v in sector_opts.items()
                         if k == "__total__" or k in main_scts}
    elif sec_level == "Sub-sektor saja":
        filtered_opts = {k: v for k, v in sector_opts.items()
                         if k in sub_scts}
    else:
        filtered_opts = sector_opts

    if not filtered_opts:
        filtered_opts = {"__total__": "▶ PDRB Total"}

    default_key = "__total__" if "__total__" in filtered_opts else list(filtered_opts.keys())[0]

    if multi_sec:
        sec_choices = st.multiselect(
            "Pilih Sektor",
            list(filtered_opts.keys()),
            default=[default_key],
            format_func=lambda x: filtered_opts.get(x, x),
            key="proj_multi_sec",
        )
    else:
        sec_single = st.selectbox(
            "Pilih Sektor",
            list(filtered_opts.keys()),
            format_func=lambda x: filtered_opts.get(x, x),
            key="proj_single_sec",
        )
        sec_choices = [sec_single]


    if not sec_choices:
        st.warning("Pilih minimal satu sektor.")
        return

    st.divider()
    st.subheader("📊 Hasil Proyeksi")

    method_desc = {
        "trend":          "Regresi linear terhadap waktu. Cocok untuk tren stabil jangka panjang.",
        "moving_average": "Rata-rata bergerak 4 triwulan. Cocok untuk meminimalkan fluktuasi musiman.",
        "avg_growth":     "Rata-rata laju pertumbuhan periode sebelumnya. Sederhana dan intuitif.",
        "exponential":    "Holt's Double Exponential Smoothing. Mempertimbangkan tren dan level.",
    }
    st.info(f"**Metode:** {method[1].split(' ', 1)[1]} — {method_desc.get(method_key, '')}")
    with st.expander("💡 Panduan Memilih & Membaca Metode Proyeksi", expanded=False):
        st.markdown("""
        ### Metode Proyeksi PDRB

        | Metode | Cocok Digunakan Ketika | Kelemahan |
        |--------|----------------------|-----------|
        | **Regresi Linear (Trend)** | Data menunjukkan tren naik/turun stabil jangka panjang | Tidak bisa menangkap fluktuasi musiman |
        | **Moving Average** | Data fluktuatif, ingin hasil yang halus | Lambat merespons perubahan tren |
        | **Rata-rata Pertumbuhan** | Pertumbuhan historis relatif konsisten | Sensitif terhadap outlier satu periode |
        | **Exponential Smoothing (Holt)** | Ada tren + level yang berubah-ubah | Butuh kalibrasi parameter α dan β |

        ### Cara Membaca Grafik Proyeksi
        - **Garis biru** = data historis aktual
        - **Garis oranye putus-putus** = hasil proyeksi
        - **Area bayangan (±10%)** = rentang ketidakpastian ilustratif
        - **R²** (hanya Trend): mendekati 1 = model fit sangat baik; < 0,7 = perlu kehati-hatian

        ⚠️ *Proyeksi bersifat estimasi. Gunakan sebagai acuan awal, bukan kepastian.*
        """)

    for sec in sec_choices:
        sec_label = filtered_opts.get(sec, sec)
        proj = analytics.project_pdrb(
            pdrb_data, kode, tabel, sec, method_key, n_forecast, n_hist
        )

        if not proj:
            st.warning(f"Tidak cukup data untuk proyeksi: {sec_label}")
            continue

        fig = charts.chart_projection(
            proj,
            title=f"Proyeksi PDRB – {sec_label} | {selected_name}",
        )
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("💡 Interpretasi Hasil Proyeksi", expanded=False):
            if proj.get("values_fcst"):
                last_hist = proj["values_hist"][-1] if proj["values_hist"] else 0
                last_fcst = proj["values_fcst"][-1] if proj["values_fcst"] else 0
                growth_pct = ((last_fcst - last_hist) / last_hist * 100) if last_hist else 0
                arah = "📈 meningkat" if growth_pct >= 0 else "📉 menurun"
                st.markdown(f"""
                **Ringkasan:**
                - Nilai akhir historis: **{last_hist:,.2f}** Juta Rp
                - Proyeksi akhir periode: **{last_fcst:,.2f}** Juta Rp
                - Perubahan kumulatif: **{growth_pct:+.2f}%** ({arah})
                {"- R² = " + str(round(proj["r2"],4)) + (" → fit model baik ✅" if proj["r2"] >= 0.7 else " → kehati-hatian diperlukan ⚠️") if proj.get("r2") is not None else ""}

                *Interval ±10% menunjukkan rentang ketidakpastian proyeksi.*
                """)

        # Tabel proyeksi
        col_hist, col_fcst = st.columns(2)
        with col_hist:
            with st.expander(f"📋 Data Historis – {sec_label[:40]}"):
                df_hist = pd.DataFrame({
                    "Periode": proj["periods_hist"],
                    "Nilai (Juta Rp)": [f"{v:,.2f}" for v in proj["values_hist"]],
                })
                st.dataframe(df_hist, use_container_width=True, hide_index=True)

        with col_fcst:
            with st.expander(f"🔮 Hasil Proyeksi – {sec_label[:40]}"):
                df_fcst = pd.DataFrame({
                    "Periode": proj["periods_fcst"],
                    "Proyeksi (Juta Rp)": [f"{v:,.2f}" for v in proj["values_fcst"]],
                    "+10%": [f"{v*1.1:,.2f}" for v in proj["values_fcst"]],
                    "-10%": [f"{max(0,v*0.9):,.2f}" for v in proj["values_fcst"]],
                })
                if proj.get("r2"):
                    st.success(f"R² = {proj['r2']:.4f}")
                st.dataframe(df_fcst, use_container_width=True, hide_index=True)

        st.divider()

    # ── Multi-sektor comparison ──
    if len(sec_choices) > 1:
        st.subheader("📊 Perbandingan Proyeksi Antar Sektor")
        fig_multi = go.Figure()
        for sec in sec_choices:
            proj = analytics.project_pdrb(
                pdrb_data, kode, tabel, sec, method_key, n_forecast, n_hist
            )
            if not proj:
                continue
            label = filtered_opts.get(sec, sec)[:40]
            # Historis + Proyeksi
            all_periods = proj["periods_hist"] + proj["periods_fcst"]
            all_vals    = proj["values_hist"] + proj["values_fcst"]
            fig_multi.add_trace(go.Scatter(
                x=all_periods, y=all_vals,
                name=label, mode="lines+markers",
            ))
            if proj["periods_hist"]:
                _sep_x = len(proj["periods_hist"]) - 0.5
                fig_multi.add_shape(
                    type="line",
                    x0=_sep_x, x1=_sep_x, y0=0, y1=1,
                    xref="x", yref="paper",
                    line=dict(dash="dot", color="gray", width=1.2),
                )

        fig_multi.update_layout(
            title="Perbandingan Proyeksi Semua Sektor Terpilih",
            xaxis_title="Periode", yaxis_title="Juta Rupiah",
            height=500, hovermode="x unified", xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_multi, use_container_width=True)
