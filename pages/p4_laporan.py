"""
Halaman 4: Generate Laporan
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import streamlit as st
import pandas as pd
from datetime import datetime

import config
from data.loader import load_all_data, compute_growth
from utils import analytics


def _to_excel(dfs_dict: dict) -> bytes:
    """Ekspor beberapa DataFrame ke file Excel multi-sheet."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        workbook = writer.book
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#1f77b4", "font_color": "white",
            "border": 1, "align": "center",
        })
        num_fmt = workbook.add_format({"num_format": "#,##0.00", "border": 1})

        for sheet_name, df in dfs_dict.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=True)
            worksheet = writer.sheets[sheet_name[:31]]
            for col_num, col_val in enumerate(df.columns.tolist()):
                worksheet.write(0, col_num + 1, col_val, header_fmt)
            for row_num in range(len(df)):
                for col_num, val in enumerate(df.iloc[row_num]):
                    try:
                        worksheet.write(row_num + 1, col_num + 1, val, num_fmt)
                    except Exception:
                        worksheet.write(row_num + 1, col_num + 1, str(val) if val else "")
    buf.seek(0)
    return buf.read()


def render():
    st.markdown("""
    <div style="background:linear-gradient(90deg,#d62728,#ff7f0e);
         padding:0.8rem 1.2rem;border-radius:8px;color:white;margin-bottom:1rem;">
        <h2 style="margin:0">📄 Generate Laporan</h2>
        <p style="margin:0;opacity:0.9">Ekspor hasil analisis ke file Excel</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Memuat data..."):
        pdrb_data, penduduk_data, kode_wilayah = load_all_data()

    kode_names = {k: v["name"] for k, v in kode_wilayah.items()}

    # ── Konfigurasi Laporan ──
    st.subheader("⚙️ Konfigurasi Laporan")

    col1, col2 = st.columns(2)
    with col1:
        wilayah_opts = {v["name"]: k for k, v in kode_wilayah.items()}
        selected_name = st.selectbox("Wilayah Utama", sorted(wilayah_opts.keys()),
                                      key="rpt_wil")
        kode = wilayah_opts[selected_name]
        tabel_choice = st.selectbox("Tabel PDRB",
                                     ["ADHB (Harga Berlaku)", "ADHK (Harga Konstan)",
                                      "Keduanya"],
                                     key="rpt_tbl")

    with col2:
        all_perds = pdrb_data.get(kode, {}).get("adhb", {}).get("periods", [])
        avail_years = sorted(set(int(p[:4]) for p in all_perds))
        yr_s = st.selectbox("Tahun Awal", avail_years, key="rpt_ys")
        yr_e = st.selectbox("Tahun Akhir", avail_years, index=len(avail_years) - 1,
                             key="rpt_ye")

    filtered_perds = [p for p in all_perds if yr_s <= int(p[:4]) <= yr_e]

    st.divider()
    st.subheader("📋 Konten Laporan")

    col_a, col_b = st.columns(2)
    with col_a:
        inc_nilai    = st.checkbox("Nilai PDRB (Absolut)", value=True, key="rpt_nilai")
        inc_dist     = st.checkbox("Distribusi Sektoral (%)", value=True, key="rpt_dist")
        inc_qtq      = st.checkbox("Pertumbuhan Q to Q", value=True, key="rpt_qtq")
        inc_yoy      = st.checkbox("Pertumbuhan Y on Y", value=True, key="rpt_yoy")
        inc_ctc      = st.checkbox("Pertumbuhan C to C", value=False, key="rpt_ctc")
    with col_b:
        inc_lq       = st.checkbox("Location Quotient (LQ)", value=True, key="rpt_lq")
        inc_ss       = st.checkbox("Shift Share", value=True, key="rpt_ss")
        inc_rrg      = st.checkbox("RRG (data tabel)", value=False, key="rpt_rrg")
        inc_perkapita = st.checkbox("PDRB Per Kapita", value=True, key="rpt_pc")
        inc_proj     = st.checkbox("Proyeksi PDRB", value=False, key="rpt_proj")

    st.divider()

    if st.button("🔄 Generate Laporan Excel", type="primary"):
        dfs = {}
        tabels = []
        if "ADHB" in tabel_choice or tabel_choice == "Keduanya":
            tabels.append("adhb")
        if "ADHK" in tabel_choice or tabel_choice == "Keduanya":
            tabels.append("adhk")

        with st.spinner("Menyusun laporan..."):
            for tbl in tabels:
                tbl_label = "ADHB" if tbl == "adhb" else "ADHK"
                if kode not in pdrb_data or tbl not in pdrb_data[kode]:
                    continue

                tbl_data = pdrb_data[kode][tbl]
                sectors  = tbl_data["sectors"]
                sct_names = {k: v["name"][:50] for k, v in sectors.items()}

                # ── Nilai PDRB ──
                if inc_nilai:
                    rows = []
                    for ks, meta in sectors.items():
                        row = {"Kode": ks, "Lapangan Usaha": meta["name"][:60],
                               "Level": "Utama" if not meta["parent"] else "Sub"}
                        for p in filtered_perds:
                            row[p] = meta["values"].get(p)
                        rows.append(row)
                    # Tambah total
                    total_row = {"Kode": "TOTAL", "Lapangan Usaha": "PDRB TOTAL",
                                 "Level": "Total"}
                    for p in filtered_perds:
                        total_row[p] = tbl_data["total"].get(p)
                    rows.append(total_row)
                    df_nilai = pd.DataFrame(rows)
                    dfs[f"Nilai_{tbl_label}"] = df_nilai

                # ── Distribusi ──
                if inc_dist:
                    main_scts = {k: v for k, v in sectors.items() if not v["parent"]}
                    dist_rows = []
                    for ks, meta in main_scts.items():
                        row = {"Kode": ks, "Lapangan Usaha": meta["name"][:60]}
                        for p in filtered_perds:
                            val = meta["values"].get(p)
                            tot = tbl_data["total"].get(p)
                            row[p] = (val / tot * 100) if (val and tot) else None
                        dist_rows.append(row)
                    dfs[f"Distribusi_{tbl_label}"] = pd.DataFrame(dist_rows)

                # ── Pertumbuhan ──
                for mode_key, mode_label, inc_flag in [
                    ("qtq", "QtoQ", inc_qtq),
                    ("yoy", "YoY", inc_yoy),
                    ("ctc", "CtC", inc_ctc),
                ]:
                    if not inc_flag:
                        continue
                    g_rows = []
                    for ks, meta in sectors.items():
                        full_series = {p: meta["values"].get(p)
                                       for p in tbl_data["periods"]}
                        g = compute_growth(full_series, mode=mode_key)
                        row = {"Kode": ks, "Lapangan Usaha": meta["name"][:60]}
                        for p in filtered_perds:
                            row[p] = g.get(p)
                        g_rows.append(row)
                    dfs[f"Growth_{mode_label}_{tbl_label}"] = pd.DataFrame(g_rows)

                # ── LQ ──
                if inc_lq:
                    lq_ts = analytics.compute_lq_timeseries(
                        pdrb_data, kode, "3300", tbl, filtered_perds
                    )
                    if not lq_ts.empty:
                        lq_ts.index = [f"{k} – {sct_names.get(k, '')[:40]}"
                                       for k in lq_ts.index]
                        dfs[f"LQ_{tbl_label}"] = lq_ts

                # ── Shift Share ──
                if inc_ss and filtered_perds:
                    ss_df = analytics.compute_shift_share(
                        pdrb_data, kode, "3300", tbl,
                        filtered_perds[0], filtered_perds[-1],
                    )
                    if not ss_df.empty:
                        dfs[f"ShiftShare_{tbl_label}"] = ss_df

            # ── PDRB Per Kapita ──
            if inc_perkapita:
                pc_df = analytics.compute_pdrb_perkapita(
                    pdrb_data, penduduk_data, [kode], "adhb"
                )
                if not pc_df.empty:
                    pc_filtered = pc_df[[p for p in filtered_perds
                                         if p in pc_df.columns]]
                    pc_filtered.index = [kode_names.get(k, k) for k in pc_filtered.index]
                    dfs["PDRB_PerKapita"] = pc_filtered

            # ── Proyeksi ──
            if inc_proj:
                proj = analytics.project_pdrb(
                    pdrb_data, kode, "adhb", "__total__", "trend", 8
                )
                if proj:
                    df_proj = pd.DataFrame({
                        "Periode": proj["periods_fcst"],
                        "Proyeksi_Trend (Juta Rp)": proj["values_fcst"],
                    })
                    dfs["Proyeksi"] = df_proj

            if dfs:
                excel_bytes = _to_excel(dfs)
                ts = datetime.now().strftime("%Y%m%d_%H%M")
                fname = f"PDRB_{selected_name.replace(' ', '_')}_{ts}.xlsx"
                st.success(f"✅ Laporan berhasil dibuat: {len(dfs)} sheet")
                st.download_button(
                    label="⬇️ Download Laporan Excel",
                    data=excel_bytes,
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                st.info(f"Sheet yang dibuat: {', '.join(dfs.keys())}")
            else:
                st.warning("Tidak ada data yang bisa diekspor. Cek konfigurasi.")
