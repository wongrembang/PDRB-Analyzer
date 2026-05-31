"""
Halaman 0: Dashboard Ringkasan – Indikator Utama PDRB
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

import config
from data.loader import load_all_data
from utils import analytics, charts
from utils.analytics import clean_kode


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_total(pdrb_data, kode, tabel, period):
    try:
        return pdrb_data[kode][tabel]["total"].get(period)
    except Exception:
        return None

def _growth(v_now, v_prev):
    if v_now is None or v_prev is None or v_prev == 0:
        return None
    return round((v_now - v_prev) / abs(v_prev) * 100, 2)

def _qtq(pdrb_data, kode, tabel, period, all_perds):
    idx = all_perds.index(period) if period in all_perds else -1
    if idx < 1:
        return None
    return _growth(_get_total(pdrb_data, kode, tabel, period),
                   _get_total(pdrb_data, kode, tabel, all_perds[idx - 1]))

def _yoy(pdrb_data, kode, tabel, period, all_perds):
    idx = all_perds.index(period) if period in all_perds else -1
    if idx < 4:
        return None
    return _growth(_get_total(pdrb_data, kode, tabel, period),
                   _get_total(pdrb_data, kode, tabel, all_perds[idx - 4]))

def _ctoc(pdrb_data, kode, tabel, period, all_perds):
    if period not in all_perds:
        return None
    q = int(period[5])
    yr = period[:4]
    prev_yr = str(int(yr) - 1)
    cur_perds  = [p for p in all_perds if p[:4] == yr      and int(p[5]) <= q]
    prev_perds = [p for p in all_perds if p[:4] == prev_yr and int(p[5]) <= q]
    if not cur_perds or not prev_perds:
        return None
    sum_cur  = sum(_get_total(pdrb_data, kode, tabel, p) or 0 for p in cur_perds)
    sum_prev = sum(_get_total(pdrb_data, kode, tabel, p) or 0 for p in prev_perds)
    return _growth(sum_cur, sum_prev)

def _fmt_val(v):
    if v is None:
        return "—"
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:,.3f} T"
    if abs(v) >= 1_000:
        return f"{v / 1_000:,.3f} M"
    return f"{v:,.2f}"

def _fmt_pct(v):
    """Kembalikan string persentase dengan warna HTML (untuk kartu)."""
    if v is None:
        return None, "—", "#6c757d"
    arrow = "▲" if v >= 0 else "▼"
    color = "#27ae60" if v >= 0 else "#e74c3c"
    return arrow, f"{abs(v):.2f}%", color

def _get_penduduk(penduduk_data, kode, period, all_kab_kodes=None):
    """Ambil penduduk; untuk provinsi (3300) jumlahkan semua kab/kota."""
    v = penduduk_data.get(kode, {}).get(period)
    if v:
        return v
    # Fallback: sum kab/kota untuk provinsi
    if kode == "3300" and all_kab_kodes:
        total = sum(penduduk_data.get(k, {}).get(period, 0) or 0 for k in all_kab_kodes)
        return total if total > 0 else None
    return None

def _card_metric(label, value, value_color="#212529",
                 bg="#f8f9fa", border="#dee2e6", icon=""):
    """Render satu kartu metrik sebagai HTML."""
    return f"""
    <div style="background:{bg};border:1px solid {border};border-radius:10px;
                padding:0.8rem 0.5rem;text-align:center;height:100%;
                box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <div style="font-size:0.68rem;color:#6c757d;font-weight:600;
                    text-transform:uppercase;letter-spacing:0.05em;margin-bottom:5px;">
            {icon} {label}
        </div>
        <div style="font-size:1.1rem;font-weight:700;color:{value_color};line-height:1.3;">
            {value}
        </div>
    </div>"""


# ─────────────────────────────────────────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <div style="background:linear-gradient(90deg,#2c3e50,#3498db);
         padding:0.9rem 1.4rem;border-radius:10px;color:white;margin-bottom:1.2rem;">
        <h2 style="margin:0;font-size:1.5rem;">📋 Dashboard Ringkasan</h2>
        <p style="margin:0;opacity:0.88;font-size:0.9rem;">
            Indikator utama PDRB kabupaten/kota — Provinsi Jawa Tengah
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Memuat data..."):
        pdrb_data, penduduk_data, kode_wilayah = load_all_data()

    # Daftar wilayah
    all_kodes  = list(kode_wilayah.keys())
    kab_kodes  = [k for k in all_kodes if k != "3300"]
    kode_names = {k: v["name"] for k, v in kode_wilayah.items()}
    kelompok_map = {k: v.get("kelompok", "-") for k, v in kode_wilayah.items()}
    kelompok_all = sorted(set(v for v in kelompok_map.values() if v and v != "-"))

    prov_perds  = sorted(pdrb_data.get("3300", {}).get("adhk", {}).get("periods", []))
    avail_years = sorted(set(int(p[:4]) for p in prov_perds))

    # ── Filter panel ──────────────────────────────────────────────────────────
    with st.expander("🔧 Filter & Pengaturan", expanded=True):
        col_a, col_b, col_c, col_d = st.columns([1.6, 2.4, 1, 1])

        with col_a:
            kg_opts   = ["Semua Kelompok"] + kelompok_all
            kg_filter = st.selectbox("Kelompok Pembangunan", kg_opts, key="rs_kg")

        with col_b:
            if kg_filter == "Semua Kelompok":
                wil_opts = all_kodes
            else:
                wil_opts = [k for k in all_kodes if kelompok_map.get(k) == kg_filter]

            # Default: provinsi + 4 kab/kota pertama (tanpa duplikat)
            kab_default = [k for k in wil_opts if k != "3300"][:4]
            default_sel = (["3300"] + kab_default) if "3300" in wil_opts else wil_opts[:5]

            selected_kodes = st.multiselect(
                "Kabupaten/Kota/Provinsi",
                options=wil_opts,
                default=[k for k in dict.fromkeys(default_sel) if k in wil_opts],
                format_func=lambda x: kode_names.get(x, x),
                key="rs_kodes",
            )

        with col_c:
            yr_s = st.selectbox("Tahun Awal",  avail_years,
                                index=max(0, len(avail_years) - 6), key="rs_yr_s")
            yr_e = st.selectbox("Tahun Akhir", avail_years,
                                index=len(avail_years) - 1,         key="rs_yr_e")

        with col_d:
            avail_snap = [p for p in reversed(prov_perds) if yr_s <= int(p[:4]) <= yr_e]
            period_sel = st.selectbox("Periode Snapshot", avail_snap, key="rs_period")
            dist_type  = st.radio("Grafik Distribusi", ["Treemap", "Pie"],
                                  horizontal=True, key="rs_dist")

    if not selected_kodes:
        st.info("Pilih minimal 1 wilayah untuk menampilkan dashboard.")
        return

    filtered_perds = [p for p in prov_perds if yr_s <= int(p[:4]) <= yr_e]

    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 1: KARTU INDIKATOR SNAPSHOT
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(f"### 📊 Indikator Snapshot — Periode **{period_sel}**")

    # (label, icon, bg_color, border_color)
    CARD_CONFIGS = [
        ("PDRB ADHB",     "💰", "#eaf4fb", "#aed6f1"),
        ("PDRB ADHK",     "📐", "#eafaf1", "#a9dfbf"),
        ("PDRB/Kapita",   "👤", "#fef9e7", "#f9e79f"),
        ("Penduduk",      "🏘️", "#f9ebea", "#f1948a"),
        ("Growth Q-to-Q", "📈", "#f4ecf7", "#c39bd3"),
        ("Growth YoY",    "📅", "#eaf4fb", "#85c1e9"),
        ("Growth C-to-C", "📆", "#fdf2e9", "#f0b27a"),
    ]

    for kode in selected_kodes:
        wil_name   = kode_names.get(kode, kode)
        all_kode_p = sorted(pdrb_data.get(kode, {}).get("adhk", {}).get("periods", prov_perds))
        adhb_val   = _get_total(pdrb_data, kode, "adhb", period_sel)
        adhk_val   = _get_total(pdrb_data, kode, "adhk", period_sel)
        pop_val    = _get_penduduk(penduduk_data, kode, period_sel, kab_kodes)
        pdrb_pc    = (adhb_val / pop_val * 1000) if (adhb_val and pop_val and pop_val > 0) else None
        qtq_val    = _qtq (pdrb_data, kode, "adhk", period_sel, all_kode_p)
        yoy_val    = _yoy (pdrb_data, kode, "adhk", period_sel, all_kode_p)
        ctoc_val   = _ctoc(pdrb_data, kode, "adhk", period_sel, all_kode_p)

        kelp  = kelompok_map.get(kode, "")
        badge = (f'<span style="background:#3498db;color:white;font-size:0.7rem;'
                 f'padding:2px 8px;border-radius:12px;margin-left:8px;">{kelp}</span>'
                 if kelp else "")

        st.markdown(
            f'<div style="font-size:1.05rem;font-weight:700;margin:0.6rem 0 0.4rem;">'
            f'📍 {wil_name}{badge}</div>',
            unsafe_allow_html=True,
        )

        # Bangun data tiap kartu: (display_text, warna_teks)
        def _pct_display(v):
            arr, pct, clr = _fmt_pct(v)
            if arr is None:
                return "—", "#6c757d"
            return f"{arr} {pct}", clr

        qtq_disp,  qtq_clr  = _pct_display(qtq_val)
        yoy_disp,  yoy_clr  = _pct_display(yoy_val)
        ctoc_disp, ctoc_clr = _pct_display(ctoc_val)

        card_data = [
            (_fmt_val(adhb_val),                        "#212529"),
            (_fmt_val(adhk_val),                        "#212529"),
            (_fmt_val(pdrb_pc),                         "#212529"),
            (f"{pop_val:,.0f}" if pop_val else "—",     "#212529"),
            (qtq_disp,                                  qtq_clr),
            (yoy_disp,                                  yoy_clr),
            (ctoc_disp,                                 ctoc_clr),
        ]

        cols = st.columns(7)
        for col, (label, icon, bg, border), (disp, clr) in zip(cols, CARD_CONFIGS, card_data):
            with col:
                st.markdown(
                    _card_metric(label, disp, value_color=clr, bg=bg, border=border, icon=icon),
                    unsafe_allow_html=True,
                )

        st.markdown("<hr style='margin:0.8rem 0;border-color:#e9ecef;'>",
                    unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 2: TABEL RINGKASAN
    # ═════════════════════════════════════════════════════════════════════════
    with st.expander("📋 Tabel Ringkasan Indikator", expanded=True):
        rows = []
        for kode in selected_kodes:
            all_kp   = sorted(pdrb_data.get(kode, {}).get("adhk", {}).get("periods", prov_perds))
            adhb_val = _get_total(pdrb_data, kode, "adhb", period_sel)
            adhk_val = _get_total(pdrb_data, kode, "adhk", period_sel)
            pop_val  = _get_penduduk(penduduk_data, kode, period_sel, kab_kodes)
            pdrb_pc  = (adhb_val / pop_val * 1000) if (adhb_val and pop_val and pop_val > 0) else None
            qtq_v    = _qtq (pdrb_data, kode, "adhk", period_sel, all_kp)
            yoy_v    = _yoy (pdrb_data, kode, "adhk", period_sel, all_kp)
            ctoc_v   = _ctoc(pdrb_data, kode, "adhk", period_sel, all_kp)
            rows.append({
                "Wilayah":            kode_names.get(kode, kode),
                "Kelompok":           kelompok_map.get(kode, "-"),
                "PDRB ADHB (Jt Rp)":  f"{adhb_val:,.2f}"  if adhb_val else "—",
                "PDRB ADHK (Jt Rp)":  f"{adhk_val:,.2f}"  if adhk_val else "—",
                "PDRB/Kapita (Jt Rp)": f"{pdrb_pc:,.4f}"  if pdrb_pc  else "—",
                "Penduduk (Rb jiwa)":  f"{pop_val:,.0f}"   if pop_val  else "—",
                "Q-to-Q (%)":          f"{qtq_v:+.2f}"    if qtq_v  is not None else "—",
                "YoY (%)":             f"{yoy_v:+.2f}"    if yoy_v  is not None else "—",
                "C-to-C (%)":          f"{ctoc_v:+.2f}"   if ctoc_v is not None else "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 3 & 4: GRAFIK TREN + DISTRIBUSI
    # ═════════════════════════════════════════════════════════════════════════
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### 📈 Tren PDRB Antar Wilayah")
        t1, t2, t3 = st.columns(3)
        with t1:
            tren_tabel = st.radio("Tabel", ["ADHB", "ADHK"],
                                  horizontal=True, key="rs_tren_tbl")
            tren_t = "adhb" if tren_tabel == "ADHB" else "adhk"
        with t2:
            tren_chart = st.radio("Jenis Grafik", ["Garis", "Bar"],
                                  horizontal=True, key="rs_tren_chart")
        with t3:
            tren_disp = st.selectbox(
                "Tampilan",
                ["Nilai Absolut", "Pertumbuhan YoY", "Pertumbuhan QtoQ"],
                key="rs_tren_disp"
            )

        tren_rows = {}
        for kode in selected_kodes:
            raw_vals = [_get_total(pdrb_data, kode, tren_t, p) for p in filtered_perds]
            if tren_disp == "Pertumbuhan YoY":
                all_kp = sorted(pdrb_data.get(kode, {}).get(tren_t, {}).get("periods", prov_perds))
                vals = [_yoy(pdrb_data, kode, tren_t, p, all_kp) for p in filtered_perds]
            elif tren_disp == "Pertumbuhan QtoQ":
                all_kp = sorted(pdrb_data.get(kode, {}).get(tren_t, {}).get("periods", prov_perds))
                vals = [_qtq(pdrb_data, kode, tren_t, p, all_kp) for p in filtered_perds]
            else:
                vals = raw_vals
            tren_rows[kode] = vals

        df_tren = pd.DataFrame(tren_rows, index=filtered_perds).T
        df_tren.insert(0, "name", df_tren.index.map(kode_names))

        y_title = "%" if "Pertumbuhan" in tren_disp else "Juta Rupiah"
        fig_tren = charts.chart_bar_line(
            df_tren, filtered_perds,
            chart_type="line" if tren_chart == "Garis" else "bar",
            title=f"Tren PDRB {tren_tabel} — {tren_disp}",
            yaxis_title=y_title,
        )
        st.plotly_chart(fig_tren, use_container_width=True)

    with col_right:
        st.markdown(f"### 🥧 Distribusi PDRB ADHB")
        st.caption(f"Periode: {period_sel}")

        if len(selected_kodes) == 1:
            kode  = selected_kodes[0]
            scts  = pdrb_data.get(kode, {}).get("adhb", {}).get("sectors", {})
            main  = {k: v for k, v in scts.items() if v["parent"] is None}
            lbls  = [f"{clean_kode(k)} – {v['name'][:28]}" for k, v in main.items()]
            vals  = [v["values"].get(period_sel) or 0 for v in main.values()]
            title_d = f"Distribusi ADHB – {kode_names.get(kode, kode)[:25]}"
        else:
            dist_v  = {kode_names.get(k, k)[:25]:
                       _get_total(pdrb_data, k, "adhb", period_sel) or 0
                       for k in selected_kodes}
            lbls    = list(dist_v.keys())
            vals    = list(dist_v.values())
            title_d = f"Distribusi PDRB ADHB Antar Wilayah"

        if dist_type == "Treemap":
            fig_d = charts.chart_treemap(lbls, vals, title=title_d)
        else:
            fig_d = charts.chart_pie(lbls, vals, title=title_d)

        st.plotly_chart(fig_d, use_container_width=True)

        # Tabel distribusi per sektor (multi-wilayah)
        if len(selected_kodes) > 1:
            with st.expander("📊 Detail distribusi per sektor"):
                sample_k = selected_kodes[0]
                sct_keys = [
                    k for k, v in pdrb_data.get(sample_k, {})
                    .get("adhb", {}).get("sectors", {}).items()
                    if v["parent"] is None
                ]
                dist_tab = []
                for ks in sct_keys:
                    nm = pdrb_data[sample_k]["adhb"]["sectors"][ks]["name"][:38]
                    row = {"Sektor": f"{clean_kode(ks)} – {nm}"}
                    for kd in selected_kodes:
                        v = (pdrb_data.get(kd, {}).get("adhb", {})
                             .get("sectors", {}).get(ks, {})
                             .get("values", {}).get(period_sel))
                        row[kode_names.get(kd, kd)[:18]] = f"{v:,.2f}" if v else "—"
                    dist_tab.append(row)
                if dist_tab:
                    st.dataframe(pd.DataFrame(dist_tab),
                                 use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════════════
    # BAGIAN 5: GRAFIK PERTUMBUHAN
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("### 📉 Grafik Pertumbuhan PDRB ADHK")
    g1, g2 = st.columns([1, 4])
    with g1:
        growth_mode = st.radio(
            "Jenis Pertumbuhan",
            ["Q to Q", "Year on Year", "C to C"],
            key="rs_growth_mode",
        )
    with g2:
        g_data = {}
        for kode in selected_kodes:
            kn    = kode_names.get(kode, kode)
            all_kp = sorted(pdrb_data.get(kode, {}).get("adhk", {}).get("periods", prov_perds))
            g_row = {}
            for p in filtered_perds:
                if growth_mode == "Q to Q":
                    g_row[p] = _qtq (pdrb_data, kode, "adhk", p, all_kp)
                elif growth_mode == "Year on Year":
                    g_row[p] = _yoy (pdrb_data, kode, "adhk", p, all_kp)
                else:
                    g_row[p] = _ctoc(pdrb_data, kode, "adhk", p, all_kp)
            g_data[kn] = g_row

        fig_g = charts.chart_growth(
            g_data, filtered_perds,
            chart_type="line",
            title=f"Pertumbuhan PDRB ADHK — {growth_mode}",
        )
        st.plotly_chart(fig_g, use_container_width=True)
