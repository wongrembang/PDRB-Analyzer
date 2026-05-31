"""
Halaman 1: Analisis Satu Wilayah
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np

import config
from data.loader import load_all_data, get_sectors_df, compute_growth, compute_distribution
from utils import analytics, charts
from utils.analytics import compute_rrg_trail
from utils.charts    import chart_rrg_trail


def render():
    st.markdown("""
    <div style="background:linear-gradient(90deg,#1f77b4,#17becf);
         padding:0.8rem 1.2rem;border-radius:8px;color:white;margin-bottom:1rem;">
        <h2 style="margin:0">🔍 Analisis Satu Wilayah</h2>
        <p style="margin:0;opacity:0.9">Analisis mendalam PDRB satu kabupaten/kota</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data ──
    with st.spinner("Memuat data..."):
        pdrb_data, penduduk_data, kode_wilayah = load_all_data()

    # ── Pilih wilayah ──
    wilayah_opts = {v["name"]: k for k, v in kode_wilayah.items()}
    wilayah_opts_sorted = dict(sorted(wilayah_opts.items()))

    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        selected_name = st.selectbox(
            "Pilih Kabupaten/Kota", list(wilayah_opts_sorted.keys()), index=0
        )
        kode = wilayah_opts_sorted[selected_name]

    with col_sel2:
        tabel_choice = st.selectbox(
            "Tabel PDRB", ["ADHB (Harga Berlaku)", "ADHK (Harga Konstan)"]
        )
        tabel = "adhb" if "ADHB" in tabel_choice else "adhk"

    if kode not in pdrb_data or tabel not in pdrb_data[kode]:
        st.error(f"Data tidak tersedia untuk wilayah ini ({kode}).")
        return

    tbl       = pdrb_data[kode][tabel]
    all_perds = tbl["periods"]
    sectors   = tbl["sectors"]

    # ── Filter periode ──
    avail_years = sorted(set(int(p[:4]) for p in all_perds))
    c1, c2 = st.columns(2)
    with c1:
        yr_start = st.selectbox("Tahun Awal", avail_years, index=0)
    with c2:
        yr_end = st.selectbox("Tahun Akhir", avail_years,
                               index=len(avail_years) - 1)

    filtered_perds = [p for p in all_perds
                      if yr_start <= int(p[:4]) <= yr_end]

    if not filtered_perds:
        st.warning("Tidak ada periode yang sesuai.")
        return

    # ── Pilih lapangan usaha ──
    main_sectors = {k: v for k, v in sectors.items() if v["parent"] is None}
    sub_sectors  = {k: v for k, v in sectors.items() if v["parent"] is not None}

    st.divider()
    st.subheader("⚙️ Pilih Lapangan Usaha")

    with st.expander("Centang/Hilangkan Lapangan Usaha & Sub-Sektor", expanded=False):
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.markdown("**Sektor Utama**")
            main_sel = {}
            for kode_s, meta in main_sectors.items():
                main_sel[kode_s] = st.checkbox(
                    f"{kode_s} – {meta['name'][:45]}", value=True, key=f"main_{kode_s}"
                )
        with col_b:
            st.markdown("**Sub-Sektor**")
            sub_sel = {}
            for kode_s, meta in sub_sectors.items():
                parent_checked = main_sel.get(meta["parent"], False)
                sub_sel[kode_s] = st.checkbox(
                    f"{kode_s} – {meta['name'][:55]}", value=False,
                    disabled=not parent_checked, key=f"sub_{kode_s}"
                )

    # Gabungkan sektor yang terpilih
    selected_scts = {k: v for k, v in main_sectors.items() if main_sel.get(k)}
    selected_scts.update({k: v for k, v in sub_sectors.items() if sub_sel.get(k)})

    if not selected_scts:
        st.warning("Pilih minimal satu lapangan usaha.")
        return

    # ── TAB ANALISIS ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Grafik & Tabel",
        "🥧 Distribusi ADHB",
        "🔬 LQ & Shift Share",
        "🔄 RRG",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: GRAFIK & TABEL
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("#### Grafik PDRB")
        cola, colb, colc = st.columns(3)
        with cola:
            chart_type = st.radio("Jenis Grafik", ["Bar", "Garis"], horizontal=True,
                                   key="t1_chart_type")
        with colb:
            view_mode = st.selectbox("Tampilan", [
                "Nilai Absolut",
                "Distribusi (%)",
                "Pertumbuhan Q to Q",
                "Pertumbuhan Y on Y",
                "Pertumbuhan C to C",
            ], key="t1_view_mode")
        with colc:
            show_table = st.checkbox("Tampilkan Tabel", value=True, key="t1_show_table")

        chart_t = "bar" if chart_type == "Bar" else "line"

        if view_mode == "Nilai Absolut":
            df_plot = pd.DataFrame({
                k: {p: v["values"].get(p) for p in filtered_perds}
                for k, v in selected_scts.items()
            }).T
            df_plot.index.name = "kode"
            names = {k: v["name"] for k, v in selected_scts.items()}
            # Add name column
            df_plot.insert(0, "name", df_plot.index.map(names))

            fig = charts.chart_bar_line(
                df_plot, filtered_perds, chart_type=chart_t,
                title=f"PDRB {tabel_choice} – {selected_name}",
                yaxis_title="Juta Rupiah",
            )
            st.plotly_chart(fig, use_container_width=True)

            if show_table:
                df_tbl = df_plot.drop(columns=["name"]).rename(
                    index={k: v["name"][:50] for k, v in selected_scts.items()}
                ).round(2)
                total_row = df_tbl.apply(lambda col: pd.to_numeric(col, errors="coerce").sum())
                total_row.name = "TOTAL"
                df_tbl = pd.concat([df_tbl, total_row.to_frame().T])
                st.dataframe(
                    df_tbl.map(lambda x: f"{x:,.2f}" if pd.notna(x) else ""),
                    use_container_width=True,
                )

        elif view_mode == "Distribusi (%)":
            # Distribusi hanya sektor utama
            main_vals = {k: v for k, v in selected_scts.items() if v["parent"] is None}
            total_per_period = {}
            for p in filtered_perds:
                t = sum(
                    v["values"].get(p) or 0
                    for v in main_vals.values()
                )
                total_per_period[p] = t if t > 0 else None

            dist_data = {}
            for k, v in main_vals.items():
                row = {}
                for p in filtered_perds:
                    val = v["values"].get(p)
                    tot = total_per_period.get(p)
                    row[p] = (val / tot * 100) if (val and tot) else None
                dist_data[k] = row

            df_dist = pd.DataFrame(dist_data).T
            df_dist.insert(0, "name", df_dist.index.map({k: v["name"] for k, v in main_vals.items()}))

            fig = charts.chart_bar_line(
                df_dist, filtered_perds, chart_type=chart_t,
                title=f"Distribusi PDRB (%) – {selected_name}",
                yaxis_title="Share (%)",
            )
            st.plotly_chart(fig, use_container_width=True)

            if show_table:
                df_tbl_dist = df_dist.drop(columns=["name"]).rename(
                    index={k: v["name"][:50] for k, v in main_vals.items()}
                ).round(2)
                total_row_dist = df_tbl_dist.apply(lambda col: pd.to_numeric(col, errors="coerce").sum())
                total_row_dist.name = "TOTAL"
                df_tbl_dist = pd.concat([df_tbl_dist, total_row_dist.to_frame().T])
                st.dataframe(
                    df_tbl_dist.map(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
                    use_container_width=True,
                )

        else:
            # Pertumbuhan
            mode_map = {
                "Pertumbuhan Q to Q": "qtq",
                "Pertumbuhan Y on Y": "yoy",
                "Pertumbuhan C to C": "ctc",
            }
            mode = mode_map[view_mode]

            growth_dict = {}
            for k, v in selected_scts.items():
                series = {p: v["values"].get(p) for p in all_perds}
                g = compute_growth(series, mode=mode)
                # Filter ke periode terpilih
                growth_dict[v["name"][:40]] = {p: g.get(p) for p in filtered_perds}

            fig = charts.chart_growth(
                growth_dict, filtered_perds, chart_type=chart_t,
                title=f"Pertumbuhan PDRB ({view_mode}) – {selected_name}",
            )
            st.plotly_chart(fig, use_container_width=True)

            if show_table:
                df_g = pd.DataFrame(growth_dict).T.round(2)
                total_row_g = df_g.apply(lambda col: pd.to_numeric(col, errors="coerce").sum())
                total_row_g.name = "TOTAL"
                df_g = pd.concat([df_g, total_row_g.to_frame().T])
                st.dataframe(
                    df_g.map(lambda x: f"{x:.2f}%" if pd.notna(x) else ""),
                    use_container_width=True,
                )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: DISTRIBUSI ADHB
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("#### Distribusi PDRB Atas Dasar Harga Berlaku")

        tbl_adhb = pdrb_data[kode].get("adhb", {})
        perds_adhb = tbl_adhb.get("periods", [])
        perds_adhb_filt = [p for p in perds_adhb
                           if yr_start <= int(p[:4]) <= yr_end]

        if not perds_adhb_filt:
            st.warning("Tidak ada data ADHB untuk rentang tahun ini.")
        else:
            col_chart, col_period = st.columns([2, 1])
            with col_period:
                period_dist = st.selectbox("Pilih Periode", perds_adhb_filt[::-1],
                                            key="dist_period")
                chart_dist_type = st.radio("Jenis Chart", ["Treemap", "Pie Chart"],
                                            horizontal=True, key="dist_type")
                show_sub = st.checkbox("Tampilkan Sub-Sektor", value=False,
                                        key="dist_sub")

            adhb_sectors = tbl_adhb.get("sectors", {})
            adhb_total   = tbl_adhb.get("total", {})

            if not show_sub:
                # Hanya sektor utama
                disp_sectors = {k: v for k, v in adhb_sectors.items()
                                if v["parent"] is None}
            else:
                disp_sectors = adhb_sectors

            labels, values, parents_list = [], [], []
            for ks, meta in disp_sectors.items():
                val = meta["values"].get(period_dist)
                if val:
                    labels.append(f"{ks} {meta['name'][:30]}")
                    values.append(val)
                    parent_key = meta["parent"]
                    if parent_key and parent_key in disp_sectors:
                        par_name = f"{parent_key} {disp_sectors[parent_key]['name'][:30]}"
                        parents_list.append(par_name)
                    else:
                        parents_list.append("")

            with col_chart:
                if chart_dist_type == "Treemap":
                    fig = charts.chart_treemap(
                        labels, values, parents_list,
                        title=f"Distribusi PDRB ADHB – {selected_name} [{period_dist}]",
                    )
                else:
                    fig = charts.chart_pie(
                        labels, values,
                        title=f"Distribusi PDRB ADHB – {selected_name} [{period_dist}]",
                    )
                st.plotly_chart(fig, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: LQ & SHIFT SHARE
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("#### Analisis Ekonomi Lanjutan")

        subtab_lq, subtab_ss = st.tabs(["📌 Location Quotient (LQ)", "↕️ Shift Share"])

        # ── LQ ──
        with subtab_lq:
            st.markdown("""
            **Location Quotient (LQ)** mengukur konsentrasi/spesialisasi sektor ekonomi
            suatu wilayah dibandingkan dengan wilayah referensi (Provinsi).
            - LQ ≥ 1,0 → **Sektor Basis** (unggul, potensi ekspor)
            - LQ < 1,0 → **Bukan Sektor Basis**
            """)

            # ── Kontrol LQ (baris kompak) ──
            ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 1])
            with ctrl1:
                lq_period = st.selectbox("Periode LQ", filtered_perds[::-1], key="lq_period")
            with ctrl2:
                lq_view   = st.radio("Tampilkan", ["Satu Periode", "Time Series (Heatmap)"],
                                     key="lq_view")
            with ctrl3:
                lq_level  = st.radio("Level Sektor", ["Utama", "Sub-sektor", "Semua"],
                                     key="lq_level")

            # ── Filter sektor & hitung LQ ──
            if lq_level == "Utama":
                lq_sectors_filter = [k for k in sectors if sectors[k]["parent"] is None]
            elif lq_level == "Sub-sektor":
                lq_sectors_filter = [k for k in sectors if sectors[k]["parent"] is not None]
            else:
                lq_sectors_filter = list(sectors.keys())

            sector_names = {k: v["name"] for k, v in sectors.items()}

            # ── Chart full-width ──
            if lq_view == "Satu Periode":
                prov_tbl   = pdrb_data.get("3300", {}).get(tabel, {})
                prov_total = prov_tbl.get("total", {}).get(lq_period)
                reg_total  = tbl["total"].get(lq_period)
                prov_sct   = {k: v["values"].get(lq_period)
                              for k, v in prov_tbl.get("sectors", {}).items()}
                reg_sct    = {k: v["values"].get(lq_period)
                              for k, v in sectors.items() if k in lq_sectors_filter}

                lq_vals     = analytics.compute_lq(reg_sct, prov_sct, reg_total, prov_total)
                lq_filtered = {k: lq_vals[k] for k in lq_sectors_filter if k in lq_vals}

                if lq_filtered:
                    fig_lq = charts.chart_lq_bar(
                        lq_filtered, sector_names,
                        title=f"LQ – {selected_name} [{lq_period}]",
                    )
                    st.plotly_chart(fig_lq, use_container_width=True)
                    with st.expander("💡 Cara Membaca LQ", expanded=False):
                        st.markdown("""
                        **Location Quotient (LQ)** mengukur spesialisasi suatu sektor
                        di wilayah ini dibandingkan dengan rata-rata Jawa Tengah.

                        | Nilai LQ | Interpretasi |
                        |----------|-------------|
                        | **LQ > 1** | **Sektor Basis** — unggulan daerah, surplus produksi, berpotensi ekspor |
                        | **LQ ≈ 1** | Sektor seimbang — sama dengan rata-rata provinsi |
                        | **LQ < 1** | **Non-Basis** — produksi belum cukup memenuhi kebutuhan lokal |

                        💡 *Sektor basis (LQ ≥ 1) menjadi penggerak utama perekonomian wilayah.
                        Semakin tinggi nilai LQ, semakin kuat spesialisasi sektor tersebut.*
                        """)

                    with st.expander("📋 Tabel LQ", expanded=False):
                        import re as _re
                        def _clean_kode(ks):
                            """Q54→Q, P53→P, M51→MN, dst. (strip angka dari kode sektor utama)."""
                            m = _re.match(r'^([A-Za-z]+)\d+$', str(ks))
                            if m:
                                ltr = m.group(1).upper()
                                return "MN" if ltr == "M" else ltr
                            return str(ks)

                        lq_rows = [
                            {
                                "Kode": _clean_kode(ks),
                                "Lapangan Usaha": sector_names.get(ks, ks),
                                "LQ": round(lq_v, 4),
                                "Klasifikasi": analytics.classify_lq(lq_v),
                            }
                            for ks, lq_v in lq_filtered.items()
                            if lq_v is not None
                        ]
                        if lq_rows:
                            st.dataframe(
                                pd.DataFrame(lq_rows).sort_values("LQ", ascending=False),
                                use_container_width=True, hide_index=True,
                            )
                        else:
                            st.info("Tidak ada data LQ yang tersedia.")
                else:
                    st.info("Tidak ada data LQ untuk sektor terpilih.")

            else:
                lq_ts = analytics.compute_lq_timeseries(
                    pdrb_data, kode, "3300", tabel, filtered_perds
                )
                if not lq_ts.empty:
                    lq_ts_filt = lq_ts.loc[[k for k in lq_sectors_filter if k in lq_ts.index]]
                    lq_ts_filt.index = [f"{k} – {sector_names.get(k,k)[:40]}"
                                        for k in lq_ts_filt.index]
                    fig_hm = charts.chart_lq_heatmap(
                        lq_ts_filt, {},
                        title=f"Heatmap LQ – {selected_name}",
                    )
                    st.plotly_chart(fig_hm, use_container_width=True)

        # ── SHIFT SHARE ──
        with subtab_ss:
            st.markdown("""
            **Shift Share Analysis** menguraikan pertumbuhan ekonomi menjadi 3 komponen:
            - **NS** (National/Provincial Share): Efek pertumbuhan total provinsi
            - **IM** (Industry Mix): Efek bauran industri / komposisi sektor
            - **CE** (Competitive Effect): Efek keunggulan kompetitif wilayah
            """)

            # ── Kontrol SS (baris kompak) ──
            ss_c1, ss_c2, ss_c3, ss_c4 = st.columns([1, 1, 1, 1])
            with ss_c1:
                ss_period_start = st.selectbox("Periode Awal", filtered_perds, key="ss_start")
            with ss_c2:
                ss_period_end   = st.selectbox("Periode Akhir", filtered_perds[::-1], key="ss_end")
            with ss_c3:
                ss_comp = st.multiselect(
                    "Komponen", ["NS", "IM", "CE", "Net Shift"],
                    default=["NS", "IM", "CE"], key="ss_comp",
                )
            with ss_c4:
                ss_level = st.radio("Level Sektor", ["Utama", "Sub-sektor"], key="ss_level")

            # ── Hitung & tampilkan chart full-width ──
            ss_df = analytics.compute_shift_share(
                pdrb_data, kode, "3300", tabel, ss_period_start, ss_period_end,
            )

            if ss_df.empty:
                st.info("Tidak cukup data untuk Shift Share. Coba rentang periode berbeda.")
            else:
                if ss_level == "Utama":
                    ss_df = ss_df[ss_df["parent"].isna()]
                else:
                    ss_df = ss_df[ss_df["parent"].notna()]

                if not ss_df.empty and ss_comp:
                    fig_ss = charts.chart_shift_share(
                        ss_df, components=ss_comp,
                        title=f"Shift Share – {selected_name} [{ss_period_start} → {ss_period_end}]",
                    )
                    st.plotly_chart(fig_ss, use_container_width=True)
                    with st.expander("💡 Cara Membaca Shift Share", expanded=False):
                        st.markdown("""
                        **Shift Share** menguraikan pertumbuhan PDRB suatu sektor menjadi 3 komponen:

                        | Komponen | Simbol | Interpretasi |
                        |----------|--------|-------------|
                        | National Share | **NS** | Bagian pertumbuhan yang disumbang oleh tren pertumbuhan provinsi secara umum |
                        | Proportional Shift | **IM** | Efek komposisi industri — apakah sektor ini secara umum tumbuh cepat di provinsi? |
                        | Differential Shift | **CE** | Keunggulan kompetitif — apakah wilayah ini lebih cepat dari rata-rata provinsi? |

                        ✅ **CE positif** → wilayah kompetitif di sektor ini (tumbuh di atas rata-rata).
                        ⚠️ **CE negatif** → wilayah kalah bersaing di sektor ini (tumbuh di bawah rata-rata).

                        *Net Shift = IM + CE. Net Shift positif = sektor unggulan kompetitif.*
                        """)

                    with st.expander("📋 Tabel Shift Share", expanded=False):
                        show_cols = ["nama"] + [c for c in ss_comp if c in ss_df.columns]
                        show_cols += ["Total Perubahan"]
                        disp_cols = [c for c in show_cols if c in ss_df.columns]
                        st.dataframe(
                            ss_df[disp_cols].reset_index(drop=True),
                            use_container_width=True,
                        )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: RRG
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("#### Relative Regional Growth (RRG)")
        st.markdown("""
        Grafik RRG menampilkan posisi setiap sektor berdasarkan:
        - **RS** (Relative Share): share sektor di wilayah vs share di provinsi
        - **RGR** (Relative Growth Rate): pertumbuhan sektor di wilayah vs provinsi

        | Kuadran | RS | RGR | Interpretasi |
        |---------|-----|-----|-------------|
        | ⭐ Stars     | ≥1 | ≥1 | Dominan & Tumbuh Pesat |
        | ❓ Question  | <1 | ≥1 | Potensi Tumbuh, Share Kecil |
        | 🐄 Cash Cow  | ≥1 | <1 | Dominan, Melambat |
        | 🐕 Dogs      | <1 | <1 | Kecil & Lambat |
        """)

        # ── Kontrol RRG (baris kompak) ──
        rr1, rr2, rr3, rr4 = st.columns([1, 1, 1, 1])
        with rr1:
            rrg_tabel = st.selectbox("Gunakan Tabel", ["ADHK (Konstan)", "ADHB (Berlaku)"],
                                      key="rrg_tabel")
            rrg_t = "adhk" if "ADHK" in rrg_tabel else "adhb"
        with rr2:
            rrg_n_periods = st.slider("Jumlah Triwulan Trail", 6, 24, 12,
                                       key="rrg_n_perds")
        with rr3:
            rrg_level = st.radio("Level Sektor", ["Utama", "Sub-sektor", "Semua"],
                                  key="rrg_level")
        with rr4:
            rrg_n_tail = st.slider("Panjang Trail (titik)", 3, 12, 6,
                                    key="rrg_n_tail")

        # ── Hitung trail ──
        trail_data = compute_rrg_trail(
            pdrb_data, kode, "3300", rrg_t, rrg_n_periods
        )

        # Filter level sektor
        if rrg_level == "Utama":
            trail_data = {k: v for k, v in trail_data.items()
                          if v.get("parent") is None}
        elif rrg_level == "Sub-sektor":
            trail_data = {k: v for k, v in trail_data.items()
                          if v.get("parent") is not None}

        if not trail_data:
            st.info("Tidak cukup data untuk RRG. Coba tambah jumlah triwulan trail.")
        else:
            # ── Inisialisasi session state checkbox sektor ──────────────────
            for _ks in trail_data:
                if f"rrg_sec_{_ks}" not in st.session_state:
                    st.session_state[f"rrg_sec_{_ks}"] = True
            # Simpan daftar key agar callback bisa mengaksesnya
            st.session_state["_rrg_sec_keys"] = list(trail_data.keys())

            def _toggle_rrg_all():
                _val = st.session_state.get("rrg_sel_all", True)
                for _k in st.session_state.get("_rrg_sec_keys", []):
                    st.session_state[f"rrg_sec_{_k}"] = _val

            # ── Expander pilih lapangan usaha ───────────────────────────────
            with st.expander("☑️ Pilih Lapangan Usaha yang Ditampilkan", expanded=True):
                st.checkbox(
                    "Pilih Semua / Hapus Semua",
                    value=True,
                    key="rrg_sel_all",
                    on_change=_toggle_rrg_all,
                )
                sec_cols = st.columns(3)
                sec_checked = {}
                for _idx, (_ks, _meta) in enumerate(trail_data.items()):
                    _label = f"{_clean_kode(_ks)} – {_meta.get('name', str(_ks))[:40]}"
                    with sec_cols[_idx % 3]:
                        sec_checked[_ks] = st.checkbox(_label, key=f"rrg_sec_{_ks}")

            # ── Filter trail berdasarkan pilihan ────────────────────────────
            trail_filtered = {k: v for k, v in trail_data.items()
                              if sec_checked.get(k, True)}

            if not trail_filtered:
                st.warning("Pilih minimal 1 lapangan usaha untuk menampilkan RRG.")
            else:
                rrg_h = max(860, 720 + len(trail_filtered) * 12)
                fig_rrg = chart_rrg_trail(
                    trail_filtered,
                    title=f"RRG – {selected_name} ({rrg_tabel})",
                    height=rrg_h,
                    n_tail=rrg_n_tail,
                )
                st.plotly_chart(fig_rrg, use_container_width=True)
                with st.expander("💡 Cara Membaca RRG (Relative Rotation Graph)", expanded=False):
                    st.markdown("""
                    **RRG** menggambarkan posisi dan pergerakan setiap sektor berdasarkan dua sumbu:
                    - **RS-Ratio (sumbu X)**: Kekuatan relatif share sektor vs provinsi. Nilai >100 = lebih dominan dari provinsi.
                    - **RS-Momentum (sumbu Y)**: Perubahan RS-Ratio. Nilai >100 = share sedang menguat.

                    | Kuadran | Posisi | Interpretasi |
                    |---------|--------|-------------|
                    | 🟢 **LEADING** | Kanan Atas | Share kuat & sedang menguat → sektor unggulan |
                    | 🟠 **WEAKENING** | Kanan Bawah | Share kuat tapi mulai melemah → waspadai tren |
                    | 🔵 **IMPROVING** | Kiri Atas | Share lemah tapi sedang membaik → sektor potensial |
                    | 🔴 **LAGGING** | Kiri Bawah | Share lemah & melemah → butuh perhatian khusus |

                    **Membaca Trail:** Titik terbaru (lingkaran besar) = posisi sekarang.
                    Garis menuju kiri = siklus berlawanan jarum jam (normal).
                    """)



            with st.expander("ð Tabel Posisi RRG (Periode Terkini)", expanded=False):
                def _quad_label(rs, rgr):
                    if   rs >= 100 and rgr >= 100: return "LEADING"
                    elif rs >= 100 and rgr <  100: return "WEAKENING"
                    elif rs <  100 and rgr >= 100: return "IMPROVING"
                    return "LAGGING"

                rows_tbl = []
                for ks, meta in trail_data.items():
                    latest = meta["trail"][-1]
                    rows_tbl.append({
                        "Kode": _clean_kode(ks),
                        "Lapangan Usaha": meta["name"][:55],
                        "RS-Ratio": round(latest["RS"], 3),
                        "RS-Momentum": round(latest["RGR"], 3),
                        "Posisi": _quad_label(latest["RS"], latest["RGR"]),
                        "Periode": latest["period"],
                    })
                st.dataframe(
                    pd.DataFrame(rows_tbl).sort_values("RS-Ratio", ascending=False),
                    use_container_width=True, hide_index=True,
                )
