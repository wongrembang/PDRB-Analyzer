"""
Halaman 2: Analisis Regional – Perbandingan Antar Kabupaten/Kota
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import json, requests

import config
from data.loader import load_all_data, compute_growth
from data.centroids_jateng import CENTROIDS_JATENG
from utils import analytics, charts
from utils.analytics import compute_rrg_trail, compute_rrg_trail_regional, clean_kode
from utils.charts    import chart_rrg_trail


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

# URL alternatif GeoJSON Jawa Tengah (urutan prioritas)
_GEOJSON_URLS = [
    config.GEOJSON_URL,
    config.GEOJSON_URL_ALT,
    "https://raw.githubusercontent.com/Ronzxy/indonesia-geojson/main/provinces/33-jawa-tengah.geojson",
    "https://raw.githubusercontent.com/gadm21/gadm/main/json/IDN_adm2.json",
    "https://raw.githubusercontent.com/ibnux/BPS-Data-Indonesia/main/geojson/33.json",
]

_GEOJSON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (PDRB-Analyzer-Dashboard/1.0)",
    "Accept": "application/json, text/plain, */*",
}


@st.cache_data(show_spinner=False)
def _load_geojson():
    """
    Load GeoJSON Jawa Tengah.
    Urutan: (1) file lokal → (2) coba beberapa URL → (3) return None (fallback bubble map).
    """
    fp = config.GEOJSON_FILE
    if os.path.exists(fp):
        with open(fp) as f:
            return json.load(f)

    for url in _GEOJSON_URLS:
        try:
            resp = requests.get(url, timeout=12, headers=_GEOJSON_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                # Simpan ke disk supaya request berikutnya pakai cache lokal
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                return data
        except Exception:
            continue
    return None


def _show_map(geojson, kode_vals: dict, kode_names: dict,
              title: str, colorscale: str = "YlOrRd"):
    """
    Tampilkan peta choropleth (jika GeoJSON tersedia) atau bubble map (fallback).
    Selalu berhasil — tidak pernah menampilkan pesan error.
    """
    if geojson is not None:
        fig = charts.chart_choropleth(
            geojson, kode_vals, kode_names,
            title=title, colorscale=colorscale,
        )
    else:
        fig = charts.chart_bubble_map(
            kode_vals, kode_names, CENTROIDS_JATENG,
            title=title, colorscale=colorscale,
        )
        st.caption(
            "ℹ️ Peta ditampilkan sebagai **bubble map** (GeoJSON batas wilayah "
            "tidak tersedia). Untuk tampilan choropleth, letakkan file "
            "`jateng.geojson` di folder `assets/`."
        )
    import streamlit as _st
    _st.plotly_chart(fig, use_container_width=True)


def _get_kab_total(pdrb_data, kode, tabel, period):
    """Ambil PDRB total satu kab/kota satu periode."""
    try:
        return pdrb_data[kode][tabel]["total"].get(period)
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <div style="background:linear-gradient(90deg,#2ca02c,#17becf);
         padding:0.8rem 1.2rem;border-radius:8px;color:white;margin-bottom:1rem;">
        <h2 style="margin:0">🗺️ Analisis Regional</h2>
        <p style="margin:0;opacity:0.9">Perbandingan antar kabupaten/kota & analisis ketimpangan</p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Memuat data..."):
        pdrb_data, penduduk_data, kode_wilayah = load_all_data()

    # ── Pilih wilayah ──
    kab_list  = [(k, v["name"], v["kelompok"]) for k, v in kode_wilayah.items()
                 if k != "3300"]
    kelompok_all = sorted(set(x[2] for x in kab_list))

    with st.expander("📍 Pilih Kabupaten/Kota", expanded=True):
        col_kg, col_kab = st.columns([1, 3])
        with col_kg:
            st.markdown("**Filter Kelompok Pembangunan**")
            kg_sel = {}
            for kg in kelompok_all:
                kg_sel[kg] = st.checkbox(kg, value=True, key=f"kg_{kg}")

        with col_kab:
            st.markdown("**Pilih Kabupaten/Kota**")
            visible_kabs = [(k, n, kg) for k, n, kg in kab_list if kg_sel.get(kg)]

            cols_kab = st.columns(3)
            kab_sel = {}
            for i, (k, n, kg) in enumerate(visible_kabs):
                with cols_kab[i % 3]:
                    kab_sel[k] = st.checkbox(n[:35], value=(i < 5), key=f"kab_{k}")

    selected_kodes = [k for k, v in kab_sel.items() if v]

    if len(selected_kodes) < 2:
        st.warning("Pilih minimal 2 kabupaten/kota untuk perbandingan.")
        return

    # ── Filter periode ──
    sample_kode = selected_kodes[0]
    all_perds = pdrb_data.get(sample_kode, {}).get("adhb", {}).get("periods", [])
    avail_years = sorted(set(int(p[:4]) for p in all_perds))

    c1, c2, c3 = st.columns(3)
    with c1:
        yr_start = st.selectbox("Tahun Awal", avail_years, index=0, key="reg_yr_s")
    with c2:
        yr_end = st.selectbox("Tahun Akhir", avail_years,
                               index=len(avail_years) - 1, key="reg_yr_e")
    with c3:
        tabel_choice = st.selectbox("Tabel PDRB",
                                     ["ADHB (Harga Berlaku)", "ADHK (Harga Konstan)"],
                                     key="reg_tabel")
        tabel = "adhb" if "ADHB" in tabel_choice else "adhk"

    filtered_perds = [p for p in all_perds if yr_start <= int(p[:4]) <= yr_end]
    kode_names = {k: v["name"] for k, v in kode_wilayah.items()}

    # ── TABS ──
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 Perbandingan Nilai",
        "🔬 LQ & Shift Share",
        "🔄 RRG Regional",
        "⚖️ Analisis Ketimpangan",
        "📉 Konvergensi/Divergensi",
        "🎯 Diversifikasi (HHI)",
        "🌐 Gravitasi Ekonomi",
        "⭐ Overlay Prioritas",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1: PERBANDINGAN NILAI
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("#### Perbandingan Nilai PDRB Antar Kabupaten/Kota")

        cola, colb, colc = st.columns(3)
        with cola:
            view_mode = st.selectbox("Tampilan", [
                "Nilai Absolut", "Distribusi (%)",
                "Pertumbuhan Q to Q", "Pertumbuhan Y on Y", "Pertumbuhan C to C",
            ], key="rv_mode")
        with colb:
            chart_type = st.selectbox("Jenis Grafik",
                                       ["Bar", "Garis", "Bar Horizontal"],
                                       key="rv_chart")
        with colc:
            vis_mode = st.radio("Visualisasi", ["Grafik", "Tabel", "Peta"],
                                 horizontal=True, key="rv_vis")

        # Pilih sektor untuk perbandingan
        sample_sectors = pdrb_data.get(sample_kode, {}).get(tabel, {}).get("sectors", {})
        main_sector_opts = {
            "__total__": "▶ PDRB Total",
            **{k: f"{k} – {v['name'][:45]}"
               for k, v in sample_sectors.items() if v["parent"] is None},
        }
        sec_choice = st.selectbox("Sektor yang Dibandingkan",
                                   list(main_sector_opts.keys()),
                                   format_func=lambda x: main_sector_opts[x],
                                   key="rv_sector")

        # Ambil data per kab
        def _get_series(kode, sec):
            tbl = pdrb_data.get(kode, {}).get(tabel, {})
            if sec == "__total__":
                return tbl.get("total", {})
            else:
                return tbl.get("sectors", {}).get(sec, {}).get("values", {})

        if view_mode == "Nilai Absolut":
            data_dict = {kode_names.get(k, k): {p: _get_series(k, sec_choice).get(p)
                                                  for p in filtered_perds}
                         for k in selected_kodes}
        elif view_mode == "Distribusi (%)":
            data_dict = {}
            for k in selected_kodes:
                total_series = pdrb_data.get(k, {}).get(tabel, {}).get("total", {})
                sec_series   = _get_series(k, sec_choice)
                row = {}
                for p in filtered_perds:
                    v   = sec_series.get(p)
                    tot = total_series.get(p)
                    row[p] = (v / tot * 100) if (v and tot) else None
                data_dict[kode_names.get(k, k)] = row
        else:
            mode_map = {
                "Pertumbuhan Q to Q": "qtq",
                "Pertumbuhan Y on Y": "yoy",
                "Pertumbuhan C to C": "ctc",
            }
            mode  = mode_map.get(view_mode, "qtq")
            data_dict = {}
            for k in selected_kodes:
                full_series = _get_series(k, sec_choice)
                g = compute_growth(full_series, mode=mode)
                data_dict[kode_names.get(k, k)] = {p: g.get(p) for p in filtered_perds}

        df_cmp = pd.DataFrame(data_dict).T

        yunit = "%" if ("%" in view_mode or "Pertumbuhan" in view_mode) else "Juta Rp"
        title_str = (f"{view_mode} – {main_sector_opts[sec_choice]} "
                     f"[{tabel_choice}]")

        if vis_mode == "Grafik":
            ct_map = {"Bar": "bar", "Garis": "line", "Bar Horizontal": "bar"}
            df_cmp.insert(0, "name", df_cmp.index)
            fig = charts.chart_bar_line(
                df_cmp, filtered_perds,
                chart_type=ct_map[chart_type],
                title=title_str, yaxis_title=yunit,
            )
            st.plotly_chart(fig, use_container_width=True)

        elif vis_mode == "Tabel":
            st.dataframe(
                df_cmp.map(lambda x: f"{x:,.2f}" if pd.notna(x) else ""),
                use_container_width=True,
            )

        else:  # Peta
            geojson = _load_geojson()
            last_p = filtered_perds[-1] if filtered_perds else None
            if last_p:
                kode_vals = {k: _get_series(k, sec_choice).get(last_p)
                             for k in selected_kodes}
                kode_vals = {k: v for k, v in kode_vals.items() if v}
                _show_map(geojson, kode_vals, kode_names,
                          title=f"Peta {title_str} [{last_p}]")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2: LQ & SHIFT SHARE KOMPARATIF
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("#### Perbandingan LQ & Shift Share Antar Kabupaten/Kota")
        sub_lq, sub_ss = st.tabs(["📌 LQ Komparatif", "↕️ Shift Share Komparatif"])

        with sub_lq:
            col_l1, col_l2 = st.columns([1, 3])
            with col_l1:
                lq_period = st.selectbox("Periode", filtered_perds[::-1], key="lq2_p")
                lq_level  = st.radio("Level", ["Utama", "Sub-sektor"], key="lq2_lv")
                lq_vis    = st.radio("Tampilkan", ["Grafik Batang", "Tabel", "Peta"],
                                      key="lq2_vis")

            with col_l2:
                # Daftar sektor
                sample_scts = pdrb_data.get(sample_kode, {}).get(tabel, {}).get("sectors", {})
                if lq_level == "Utama":
                    sct_filter = [k for k, v in sample_scts.items() if v["parent"] is None]
                else:
                    sct_filter = [k for k, v in sample_scts.items() if v["parent"] is not None]

                sec_for_lq = st.multiselect(
                    "Pilih Sektor untuk LQ",
                    sct_filter,
                    default=sct_filter[:min(5, len(sct_filter))],
                    format_func=lambda x: f"{x} – {sample_scts.get(x, {}).get('name', '')[:50]}",
                    key="lq2_sec",
                )

                # Hitung LQ per kab
                lq_rows = []
                for k in selected_kodes:
                    prov_tbl  = pdrb_data.get("3300", {}).get(tabel, {})
                    reg_tbl   = pdrb_data.get(k, {}).get(tabel, {})
                    prov_tot  = prov_tbl.get("total", {}).get(lq_period)
                    reg_tot   = reg_tbl.get("total", {}).get(lq_period)
                    prov_sct  = {ks: v["values"].get(lq_period)
                                 for ks, v in prov_tbl.get("sectors", {}).items()}
                    reg_sct   = {ks: v["values"].get(lq_period)
                                 for ks, v in reg_tbl.get("sectors", {}).items()}
                    lq_v = analytics.compute_lq(reg_sct, prov_sct, reg_tot, prov_tot)
                    for ks in (sec_for_lq or sct_filter[:5]):
                        lq_rows.append({
                            "kode_kab": k,
                            "kab": kode_names.get(k, k),
                            "sektor": clean_kode(ks),
                            "nama_sektor": sample_scts.get(ks, {}).get("name", ks)[:40],
                            "LQ": lq_v.get(ks),
                        })

                df_lq2 = pd.DataFrame(lq_rows)

                if not df_lq2.empty and lq_vis == "Grafik Batang":
                    import plotly.express as px
                    fig_lq2 = px.bar(
                        df_lq2.dropna(subset=["LQ"]),
                        x="nama_sektor", y="LQ", color="kab",
                        barmode="group",
                        title=f"Perbandingan LQ [{lq_period}]",
                        labels={"LQ": "Nilai LQ", "nama_sektor": "Lapangan Usaha"},
                    )
                    fig_lq2.add_hline(y=1, line_dash="dash", line_color="orange")
                    fig_lq2.update_layout(height=500, xaxis_tickangle=-45,
                                          margin=dict(b=200))
                    st.plotly_chart(fig_lq2, use_container_width=True)
                    with st.expander("💡 Cara Membaca LQ", expanded=False):
                        st.markdown("""
                        **Location Quotient (LQ)** mengukur spesialisasi/keunggulan relatif
                        suatu sektor di suatu wilayah dibanding provinsi.

                        | Nilai LQ | Interpretasi |
                        |----------|-------------|
                        | LQ > 1 | Sektor **basis** — unggulan, surplus, dapat diekspor ke luar wilayah |
                        | LQ = 1 | Sama dengan rata-rata provinsi |
                        | LQ < 1 | Sektor **non-basis** — belum mencukupi kebutuhan lokal |

                        *LQ ≥ 1,5 → sektor basis kuat. Semakin tinggi LQ, semakin terspesialisasi.*
                        """)

                elif not df_lq2.empty and lq_vis == "Tabel":
                    pivot = df_lq2.pivot_table(
                        index="nama_sektor", columns="kab", values="LQ"
                    ).round(3)
                    st.dataframe(pivot, use_container_width=True)

                elif not df_lq2.empty and lq_vis == "Peta":
                    # Peta LQ untuk sektor pertama terpilih
                    if sec_for_lq:
                        chosen_sec = sec_for_lq[0]
                        lq_map_vals = {row["kode_kab"]: row["LQ"]
                                       for row in lq_rows
                                       if row["sektor"] == chosen_sec and row["LQ"]}
                        geojson = _load_geojson()
                        sec_label = sample_scts.get(chosen_sec, {}).get("name", chosen_sec)
                        _show_map(geojson, lq_map_vals, kode_names,
                                  title=f"Peta LQ – {sec_label} [{lq_period}]",
                                  colorscale="RdYlGn")

        with sub_ss:
            col_s1, col_s2 = st.columns([1, 3])
            with col_s1:
                ss2_start = st.selectbox("Periode Awal", filtered_perds, key="ss2_s")
                ss2_end   = st.selectbox("Periode Akhir", filtered_perds[::-1], key="ss2_e")
                ss2_comp  = st.multiselect("Komponen", ["NS", "IM", "CE", "Net Shift"],
                                            default=["IM", "CE"], key="ss2_comp")
                ss2_level = st.radio("Level", ["Utama"], key="ss2_lv")

            with col_s2:
                ss_cmp_rows = []
                for k in selected_kodes:
                    ss_df = analytics.compute_shift_share(
                        pdrb_data, k, "3300", tabel, ss2_start, ss2_end
                    )
                    if not ss_df.empty:
                        if ss2_level == "Utama":
                            ss_df = ss_df[ss_df["parent"].isna()]
                        for ks, row in ss_df.iterrows():
                            entry = {"Kabupaten/Kota": kode_names.get(k, k), "Sektor": clean_kode(ks),
                                     "Lapangan Usaha": row.get("nama", "")[:40]}
                            for comp in ss2_comp:
                                entry[comp] = row.get(comp)
                            ss_cmp_rows.append(entry)

                if ss_cmp_rows:
                    df_ss2 = pd.DataFrame(ss_cmp_rows)
                    if ss2_comp:
                        import plotly.express as px
                        comp_sel = ss2_comp[0]
                        fig_ss2 = px.bar(
                            df_ss2, x="Lapangan Usaha", y=comp_sel,
                            color="Kabupaten/Kota", barmode="group",
                            title=f"Shift Share – Komponen {comp_sel} "
                                  f"[{ss2_start} → {ss2_end}]",
                        )
                        fig_ss2.update_layout(height=500, xaxis_tickangle=-45,
                                              margin=dict(b=200))
                        st.plotly_chart(fig_ss2, use_container_width=True)
                        with st.expander("💡 Cara Membaca Shift Share", expanded=False):
                            st.markdown("""
                            **Shift Share Analysis** menguraikan pertumbuhan ekonomi menjadi 3 komponen:

                            | Komponen | Arti |
                            |----------|------|
                            | **NS** (National Share) | Pertumbuhan akibat efek pertumbuhan provinsi secara keseluruhan |
                            | **IM** (Industry Mix / Proportional Shift) | Efek bauran industri — apakah sektor ini tumbuh pesat di tingkat provinsi? |
                            | **CE** (Competitive Effect / Differential Shift) | Keunggulan kompetitif lokal — apakah wilayah ini tumbuh lebih cepat dari rata-rata provinsi? |

                            *CE positif = wilayah kompetitif di sektor tersebut.
                            CE negatif = wilayah tertinggal dari rata-rata provinsi di sektor tersebut.*
                            """)
                        st.dataframe(df_ss2, use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak cukup data Shift Share untuk wilayah terpilih.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3: RRG REGIONAL
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("#### Relative Regional Growth (RRG) Regional")

        rrg_mode = st.radio(
            "Mode RRG",
            ["Total PDRB Kab/Kota", "Per Lapangan Usaha Antar Kab/Kota"],
            horizontal=True, key="rrg2_mode",
        )
        rc1, rc2 = st.columns(2)
        with rc1:
            rrg2_perds = st.slider("Jumlah Triwulan Trail", 6, 24, 12, key="rrg2_n")
        with rc2:
            rrg2_tail  = st.slider("Panjang Trail (titik)", 3, 12, 6, key="rrg2_tail")
        rrg2_tabel = "adhk"

        if rrg_mode == "Total PDRB Kab/Kota":
            trail_reg = compute_rrg_trail_regional(
                pdrb_data, selected_kodes, "3300", rrg2_tabel, rrg2_perds
            )
            # Tambahkan nama kab/kota ke trail_data
            for kode_k, meta in trail_reg.items():
                meta["name"]   = kode_names.get(kode_k, kode_k)
                meta["parent"] = None

            if trail_reg:
                fig_rrg = chart_rrg_trail(
                    trail_reg,
                    title="RRG – Perbandingan PDRB Total Kab/Kota vs Provinsi",
                    height=max(680, 580 + len(trail_reg) * 10),
                    n_tail=rrg2_tail,
                )
                st.plotly_chart(fig_rrg, use_container_width=True)

                # Tabel posisi terkini
                def _ql(rs, rgr):
                    if   rs >= 100 and rgr >= 100: return "LEADING"
                    elif rs >= 100 and rgr <  100: return "WEAKENING"
                    elif rs <  100 and rgr >= 100: return "IMPROVING"
                    return "LAGGING"
                rows_t = []
                for kode_k, meta in trail_reg.items():
                    lt = meta["trail"][-1]
                    rows_t.append({"Kab/Kota": meta["name"],
                                   "RS-Ratio": round(lt["RS"], 3),
                                   "RS-Momentum": round(lt["RGR"], 3),
                                   "Posisi": _ql(lt["RS"], lt["RGR"]),
                                   "Periode": lt["period"]})
                st.dataframe(pd.DataFrame(rows_t).sort_values("RS-Ratio", ascending=False),
                             use_container_width=True, hide_index=True)
            else:
                st.info("Tidak cukup data RRG regional.")

        else:  # Per Lapangan Usaha
            sample_scts = pdrb_data.get(sample_kode, {}).get(rrg2_tabel, {}).get("sectors", {})
            main_scts   = {k: v for k, v in sample_scts.items() if v["parent"] is None}
            sec_rrg2    = st.selectbox(
                "Pilih Lapangan Usaha",
                list(main_scts.keys()),
                format_func=lambda x: f"{x} – {main_scts[x]['name'][:50]}",
                key="rrg2_sec",
            )

            # Hitung trail per kab/kota untuk sektor terpilih
            trail_sec: dict = {}
            tbl_p = pdrb_data.get("3300", {}).get(rrg2_tabel, {})
            for kode_k in selected_kodes:
                tbl_r  = pdrb_data.get(kode_k, {}).get(rrg2_tabel, {})
                pv_sec = tbl_p.get("sectors", {}).get(sec_rrg2, {})
                rv_sec = tbl_r.get("sectors", {}).get(sec_rrg2, {})
                all_p  = sorted(
                    set(tbl_r.get("periods", [])) & set(tbl_p.get("periods", []))
                )
                use_p = all_p[-rrg2_perds:] if len(all_p) >= rrg2_perds else all_p

                rs_series = []
                for p in use_p:
                    r_val = rv_sec.get("values", {}).get(p)
                    r_tot = tbl_r.get("total", {}).get(p)
                    p_val = pv_sec.get("values", {}).get(p)
                    p_tot = tbl_p.get("total", {}).get(p)
                    if not all([r_val, r_tot, p_val, p_tot]) or r_tot == 0 or p_tot == 0:
                        continue
                    rs_series.append((p, (r_val / r_tot) / (p_val / p_tot) * 100))

                if len(rs_series) < 3:
                    continue
                trail = []
                for i in range(1, len(rs_series)):
                    p_c, rs_c = rs_series[i]
                    _, rs_p   = rs_series[i - 1]
                    trail.append({"period": p_c, "RS": round(rs_c, 3),
                                  "RGR": round(rs_c / rs_p * 100 if rs_p else 100, 3)})
                if len(trail) >= 2:
                    trail_sec[kode_k] = {
                        "name":   kode_names.get(kode_k, kode_k),
                        "parent": None,
                        "trail":  trail,
                    }

            if trail_sec:
                sec_name = main_scts.get(sec_rrg2, {}).get("name", sec_rrg2)
                fig_rrg2 = chart_rrg_trail(
                    trail_sec,
                    title=f"RRG – {sec_name} Antar Kab/Kota",
                    height=max(680, 580 + len(trail_sec) * 10),
                    n_tail=rrg2_tail,
                )
                st.plotly_chart(fig_rrg2, use_container_width=True)
            else:
                st.info("Tidak cukup data untuk RRG per lapangan usaha.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4: ANALISIS KETIMPANGAN
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("#### Analisis Ketimpangan Ekonomi Regional")

        ktmp_tabs = st.tabs([
            "💰 PDRB Per Kapita",
            "📐 Indeks Williamson",
            "🔲 Tipologi Klassen",
            "⚖️ Indeks Theil",
            "🔗 Kemiripan Struktur",
        ])

        tabel_ktmp = "adhb"  # Ketimpangan umumnya pakai ADHB

        # ── PDRB Per Kapita ──
        with ktmp_tabs[0]:
            pdrb_pc_df = analytics.compute_pdrb_perkapita(
                pdrb_data, penduduk_data, selected_kodes, tabel_ktmp
            )
            if not pdrb_pc_df.empty:
                pc_perds = [p for p in filtered_perds if p in pdrb_pc_df.columns]
                if pc_perds:
                    import plotly.graph_objects as go
                    fig_pc = go.Figure()
                    for k in selected_kodes:
                        if k not in pdrb_pc_df.index:
                            continue
                        y_vals = [pdrb_pc_df.loc[k, p] for p in pc_perds]
                        fig_pc.add_trace(go.Scatter(
                            x=pc_perds, y=y_vals, name=kode_names.get(k, k),
                            mode="lines+markers",
                        ))
                    # Rata-rata provinsi
                    prov_pc = analytics.compute_pdrb_perkapita(
                        pdrb_data, penduduk_data, ["3300"], tabel_ktmp
                    )
                    if not prov_pc.empty and "3300" in prov_pc.index:
                        prov_vals = [prov_pc.loc["3300", p] for p in pc_perds]
                        fig_pc.add_trace(go.Scatter(
                            x=pc_perds, y=prov_vals, name="Rata-rata Provinsi",
                            mode="lines", line=dict(width=3, dash="dash", color="red"),
                        ))
                    fig_pc.update_layout(
                        title="PDRB Per Kapita (Juta Rp/Jiwa)",
                        xaxis_title="Periode", yaxis_title="Juta Rp/Jiwa",
                        height=500, xaxis_tickangle=-45,
                    )
                    st.plotly_chart(fig_pc, use_container_width=True)

                    # Tabel
                    st.dataframe(
                        pdrb_pc_df[pc_perds]
                        .rename(index=kode_names)
                        .round(4)
                        .map(lambda x: f"{x:,.4f}" if pd.notna(x) else ""),
                        use_container_width=True,
                    )

        # ── Williamson ──
        with ktmp_tabs[1]:
            st.markdown("""
            **Indeks Williamson** (Iw) mengukur ketimpangan pendapatan antar wilayah.
            - Iw mendekati 0 → **Merata**
            - Iw mendekati 1+ → **Timpang**
            """)

            williams_all = analytics.compute_williamson_timeseries(
                pdrb_data, penduduk_data, selected_kodes, tabel=tabel_ktmp
            )
            williams_filt = {p: v for p, v in williams_all.items()
                             if p in filtered_perds and v is not None}

            if williams_filt:
                fig_wm = charts.chart_williamson_trend(
                    williams_filt,
                    title="Indeks Williamson – Wilayah Terpilih",
                )
                st.plotly_chart(fig_wm, use_container_width=True)
                with st.expander("💡 Cara Membaca Indeks Williamson", expanded=False):
                    st.markdown("""
                    **Indeks Williamson (Iw)** mengukur ketimpangan PDRB per kapita antar wilayah
                    dengan mempertimbangkan bobot jumlah penduduk.

                    | Nilai Iw | Interpretasi |
                    |----------|-------------|
                    | < 0,35 | Ketimpangan **rendah** — distribusi relatif merata |
                    | 0,35 – 0,50 | Ketimpangan **sedang** — perlu perhatian |
                    | > 0,50 | Ketimpangan **tinggi** — disparitas antar wilayah signifikan |

                    *Tren menurun = ketimpangan mengecil (kondisi baik).*
                    *Tren meningkat = ketimpangan melebar (perlu kebijakan redistribusi).*
                    """)

                # Tabel
                wm_rows = [{"Periode": p, "Indeks Williamson": round(v, 4)}
                           for p, v in williams_filt.items()]
                st.dataframe(pd.DataFrame(wm_rows), use_container_width=True,
                             hide_index=True)

                # Juga per kelompok pembangunan
                st.divider()
                st.markdown("**Per Kelompok Pembangunan**")
                for kg in kelompok_all:
                    kg_kodes = [k for k, v in kode_wilayah.items()
                                if v["kelompok"] == kg and k in selected_kodes]
                    if len(kg_kodes) < 2:
                        continue
                    w_kg = analytics.compute_williamson_timeseries(
                        pdrb_data, penduduk_data, kg_kodes, tabel=tabel_ktmp
                    )
                    w_kg_filt = {p: v for p, v in w_kg.items()
                                 if p in filtered_perds and v is not None}
                    if w_kg_filt:
                        last_p = max(w_kg_filt)
                        st.metric(f"Williamson – {kg} [{last_p}]",
                                  f"{w_kg_filt[last_p]:.4f}")

        # ── Klassen ──
        with ktmp_tabs[2]:
            st.markdown("""
            **Tipologi Klassen** mengklasifikasikan wilayah berdasarkan
            PDRB per kapita dan laju pertumbuhan dibandingkan rata-rata provinsi.
            """)

            col_k1, col_k2 = st.columns([1, 3])
            with col_k1:
                klass_start = st.selectbox("Periode Awal (Basis)", filtered_perds,
                                            key="kl_s")
                klass_end   = st.selectbox("Periode Akhir", filtered_perds[::-1],
                                            key="kl_e")

            with col_k2:
                klass_df = analytics.compute_klassen(
                    pdrb_data, penduduk_data, selected_kodes,
                    klass_start, klass_end, tabel_ktmp,
                )
                if not klass_df.empty:
                    # Hitung rata-rata provinsi untuk referensi
                    pdrb_pc = analytics.compute_pdrb_perkapita(
                        pdrb_data, penduduk_data, ["3300"], tabel_ktmp
                    )
                    yi_s = pdrb_pc.loc["3300", klass_start] if (
                        "3300" in pdrb_pc.index and klass_start in pdrb_pc.columns) else 0
                    yi_e = pdrb_pc.loc["3300", klass_end] if (
                        "3300" in pdrb_pc.index and klass_end in pdrb_pc.columns) else 0
                    g_prov = (yi_e - yi_s) / abs(yi_s) * 100 if yi_s else 0
                    y_prov = yi_e

                    fig_kl = charts.chart_klassen_scatter(
                        klass_df, kode_names, g_prov, y_prov,
                        title=f"Tipologi Klassen [{klass_start} → {klass_end}]",
                    )
                    st.plotly_chart(fig_kl, use_container_width=True)
                    with st.expander("💡 Cara Membaca Tipologi Klassen", expanded=False):
                        st.markdown("""
                        **Tipologi Klassen** mengklasifikasikan wilayah ke dalam 4 kuadran
                        berdasarkan perbandingan dengan rata-rata provinsi:

                        | Kuadran | PDRB/Kapita | Pertumbuhan | Interpretasi |
                        |---------|-------------|-------------|-------------|
                        | **Maju & Tumbuh Pesat** | > rata-rata | > rata-rata | Wilayah unggulan |
                        | **Maju tapi Tertekan** | > rata-rata | < rata-rata | Potensi besar, pertumbuhan melambat |
                        | **Berkembang Cepat** | < rata-rata | > rata-rata | Tumbuh pesat, kapasitas masih rendah |
                        | **Relatif Tertinggal** | < rata-rata | < rata-rata | Butuh intervensi kebijakan |

                        *Garis putus-putus = nilai rata-rata provinsi.*
                        """)

                    disp_df = klass_df.copy()
                    disp_df.index = [kode_names.get(k, k) for k in disp_df.index]
                    st.dataframe(
                        disp_df.reset_index().rename(columns={"index": "Kab/Kota"}),
                        use_container_width=True, hide_index=True,
                    )
                else:
                    st.info("Tidak cukup data untuk Tipologi Klassen.")

        # ── Theil ──
        with ktmp_tabs[3]:
            st.markdown("""
            **Indeks Theil** mengukur ketimpangan dengan mempertimbangkan
            distribusi pendapatan secara lebih sensitif terhadap perbedaan ekstrem.
            - Nilai 0 → Sempurna merata
            - Nilai > 0 → Makin timpang
            """)
            theil_ts = analytics.compute_theil_timeseries(
                pdrb_data, penduduk_data, selected_kodes, tabel_ktmp
            )
            theil_filt = {p: v for p, v in theil_ts.items()
                          if p in filtered_perds and v is not None}

            if theil_filt:
                import plotly.graph_objects as go
                fig_th = go.Figure(go.Scatter(
                    x=sorted(theil_filt.keys()),
                    y=[theil_filt[p] for p in sorted(theil_filt.keys())],
                    mode="lines+markers",
                    line=dict(color="#9467bd", width=2),
                    fill="tozeroy", fillcolor="rgba(148,103,189,0.1)",
                ))
                fig_th.update_layout(
                    title="Indeks Theil – Wilayah Terpilih",
                    xaxis_title="Periode", yaxis_title="Indeks Theil",
                    height=400, xaxis_tickangle=-45,
                )
                st.plotly_chart(fig_th, use_container_width=True)
                with st.expander("💡 Cara Membaca Indeks Theil", expanded=False):
                    st.markdown("""
                    **Indeks Theil (T)** mengukur ketimpangan distribusi pendapatan.
                    Berbeda dari Williamson, Theil lebih sensitif terhadap perbedaan ekstrem.

                    | Nilai T | Interpretasi |
                    |---------|-------------|
                    | Mendekati 0 | Distribusi sangat **merata** |
                    | 0,1 – 0,3 | Ketimpangan **rendah–sedang** |
                    | > 0,3 | Ketimpangan **tinggi** |

                    *Dibandingkan Williamson: Theil lebih peka terhadap ketimpangan
                    di ujung distribusi (wilayah sangat kaya vs sangat miskin).*
                    """)
            else:
                st.info("Tidak tersedia data Indeks Theil untuk periode ini.")

        # ── Kemiripan Struktur ──
        with ktmp_tabs[4]:
            st.markdown("""
            **Indeks Kemiripan Struktur** mengukur seberapa mirip/berbeda
            struktur ekonomi antar wilayah.
            - Metode **Krugman**: nilai 0 (identik) s.d. 2 (sangat berbeda)
            - Metode **Cosine**: nilai 0 (identik) s.d. 1 (sangat berbeda)
            """)
            col_km1, col_km2 = st.columns([1, 3])
            with col_km1:
                km_period = st.selectbox("Periode", filtered_perds[::-1], key="km_p")
                km_method = st.radio("Metode", ["krugman", "cosine"], key="km_m")

            with col_km2:
                km_df = analytics.compute_struktur_kemiripan(
                    pdrb_data, selected_kodes, km_period, tabel_ktmp, km_method
                )
                if not km_df.empty:
                    km_df.index = [kode_names.get(k, k) for k in km_df.index]
                    km_df.columns = [kode_names.get(k, k) for k in km_df.columns]

                    import plotly.express as px
                    fig_km = px.imshow(
                        km_df, text_auto=".3f",
                        color_continuous_scale="RdYlGn_r",
                        title=f"Indeks Kemiripan Struktur ({km_method.title()}) [{km_period}]",
                        zmin=0,
                    )
                    fig_km.update_layout(height=max(550, len(selected_kodes) * 55),
                            font=dict(size=12))
                    st.plotly_chart(fig_km, use_container_width=True)
                    with st.expander("💡 Cara Membaca Indeks Kemiripan Struktur", expanded=False):
                        st.markdown("""
                        **Indeks Kemiripan Struktur** mengukur seberapa mirip komposisi
                        sektor ekonomi dua wilayah. Semakin rendah nilainya, semakin mirip strukturnya.

                        **Metode Krugman:**
                        - Nilai 0 = struktur identik
                        - Nilai 2 = struktur sangat berbeda (tidak ada kesamaan sama sekali)

                        **Metode Cosine:**
                        - Nilai 0 = struktur identik
                        - Nilai 1 = struktur sangat berbeda

                        *Warna merah = struktur mirip. Warna hijau = struktur berbeda.
                        Wilayah dengan struktur mirip cenderung bereaksi sama terhadap guncangan ekonomi.*
                        """)
                else:
                    st.info("Tidak cukup data untuk analisis kemiripan struktur.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5: KONVERGENSI / DIVERGENSI
    # ══════════════════════════════════════════════════════════════════════════
    with tab5:
        st.subheader("📉 Analisis Konvergensi / Divergensi Ekonomi")
        st.caption("Mengukur apakah kesenjangan PDRB per kapita antar wilayah mengecil (konvergen) "
                   "atau membesar (divergen) dari waktu ke waktu.")

        conv_tabel = st.radio("Tabel", ["ADHB", "ADHK"], horizontal=True, key="conv_tbl")
        conv_t = "adhb" if conv_tabel == "ADHB" else "adhk"

        kab_kodes = [k for k in selected_kodes if k != "3300"]
        if len(kab_kodes) < 3:
            st.warning("Pilih minimal 3 kabupaten/kota untuk analisis konvergensi.")
        else:
            with st.spinner("Menghitung konvergensi..."):
                conv_result = analytics.compute_convergence(
                    pdrb_data, penduduk_data, kab_kodes, tabel=conv_t
                )

            if not conv_result or not conv_result.get("sigma"):
                st.warning("Data tidak cukup untuk analisis konvergensi.")
            else:
                sigma_s = conv_result["sigma"]
                beta_r  = conv_result.get("beta")

                # Indikator konvergensi
                if len(sigma_s) >= 2:
                    trend_dir = sigma_s[-1]["sigma"] - sigma_s[0]["sigma"]
                    is_conv   = trend_dir < 0
                    st.markdown(
                        f'<div style="background:{"rgba(56,211,159,0.12)" if is_conv else "rgba(248,81,73,0.12)"}; '
                        f'border-left:4px solid {"#3fb950" if is_conv else "#f85149"};'
                        f'padding:0.8rem 1.2rem;border-radius:8px;margin-bottom:1rem;">'
                        f'<b>{"✅ KONVERGEN" if is_conv else "⚠️ DIVERGEN"}</b> — '
                        f'σ {"menurun" if is_conv else "meningkat"} dari '
                        f'{sigma_s[0]["sigma"]:.5f} ({sigma_s[0]["period"]}) ke '
                        f'{sigma_s[-1]["sigma"]:.5f} ({sigma_s[-1]["period"]})'
                        f'</div>', unsafe_allow_html=True
                    )

                fig_conv = charts.chart_convergence(
                    sigma_s, beta_r,
                    title=f"Konvergensi Ekonomi — {len(kab_kodes)} Kab/Kota Terpilih"
                )
                st.plotly_chart(fig_conv, use_container_width=True)

                if beta_r:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Beta (β)", f"{beta_r['beta']:.5f}",
                              help="Negatif = konvergen, Positif = divergen")
                    c2.metric("R²", f"{beta_r['r2']:.4f}")
                    c3.metric("Kesimpulan",
                              "Konvergen ✅" if beta_r["converging"] else "Divergen ⚠️")

                with st.expander("📖 Interpretasi Konvergensi", expanded=False):
                    st.markdown("""
**Sigma Convergence (σ-convergence):**
Jika standar deviasi ln(PDRB/kapita) antar wilayah *menurun* dari waktu ke waktu →
kesenjangan mengecil → **konvergen**.

**Beta Convergence (β-convergence):**
Regresi pertumbuhan PDRB/kapita terhadap nilai awal. Jika koefisien β **negatif** dan
signifikan → wilayah yang tertinggal tumbuh lebih cepat → **konvergen** (catching-up effect).

| Nilai β | Interpretasi |
|---|---|
| < 0 | Konvergen — wilayah miskin tumbuh lebih cepat |
| > 0 | Divergen — wilayah kaya tumbuh lebih cepat |
| ≈ 0 | Tidak ada pola konvergensi |
                    """)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6: DIVERSIFIKASI EKONOMI (HHI)
    # ══════════════════════════════════════════════════════════════════════════
    with tab6:
        st.subheader("🎯 Indeks Diversifikasi Ekonomi (HHI)")
        st.caption("Herfindahl-Hirschman Index mengukur tingkat konsentrasi/diversifikasi "
                   "struktur ekonomi. HHI rendah = terdiversifikasi; tinggi = terkonsentrasi.")

        hhi_tabel = st.radio("Tabel", ["ADHB", "ADHK"], horizontal=True, key="hhi_tbl")
        hhi_t = "adhb" if hhi_tabel == "ADHB" else "adhk"

        with st.spinner("Menghitung HHI..."):
            hhi_dict = analytics.compute_hhi_regional(
                pdrb_data, selected_kodes, tabel=hhi_t
            )

        fig_hhi = charts.chart_hhi(
            hhi_dict, kode_names,
            title=f"Indeks HHI Diversifikasi Ekonomi ({hhi_tabel})"
        )
        st.plotly_chart(fig_hhi, use_container_width=True)

        # Tabel snapshot periode terakhir
        prov_perds_hhi = sorted(pdrb_data.get("3300", {}).get(hhi_t, {}).get("periods", []))
        if prov_perds_hhi:
            last_p_hhi = prov_perds_hhi[-1]
            hhi_rows = []
            for kode in selected_kodes:
                series = hhi_dict.get(kode, [])
                latest = next((s for s in reversed(series) if s["period"] == last_p_hhi), None)
                if not latest and series:
                    latest = series[-1]
                if latest:
                    hhi_val = latest["hhi"]
                    if hhi_val < 0.15:
                        kat = "🟢 Terdiversifikasi"
                    elif hhi_val < 0.25:
                        kat = "🟡 Moderat"
                    else:
                        kat = "🔴 Terkonsentrasi"
                    hhi_rows.append({
                        "Wilayah": kode_names.get(kode, kode),
                        "Periode": latest["period"],
                        "HHI":     f"{hhi_val:.4f}",
                        "Kategori": kat,
                        "Jml Sektor Aktif": latest["n_sectors"],
                    })
            if hhi_rows:
                import pandas as _pd2
                st.dataframe(_pd2.DataFrame(hhi_rows), use_container_width=True, hide_index=True)

        with st.expander("📖 Interpretasi HHI", expanded=False):
            st.markdown("""
**Rumus:** HHI = Σ(sᵢ²) di mana sᵢ = share sektor i terhadap total PDRB

| Nilai HHI | Kategori | Interpretasi |
|---|---|---|
| < 0.15 | 🟢 Terdiversifikasi | Ekonomi tersebar merata di banyak sektor |
| 0.15 – 0.25 | 🟡 Moderat | Sebagian terkonsentrasi, masih cukup beragam |
| > 0.25 | 🔴 Terkonsentrasi | Ekonomi sangat bergantung pada sedikit sektor |

Wilayah dengan HHI tinggi lebih **rentan terhadap guncangan** pada sektor dominannya.
            """)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 7: GRAVITASI EKONOMI
    # ══════════════════════════════════════════════════════════════════════════
    with tab7:
        st.subheader("🌐 Analisis Gravitasi Ekonomi")
        st.caption("Model gravitasi mengukur potensi interaksi ekonomi antar wilayah "
                   "berdasarkan besaran PDRB dan jarak geografis.")

        grav_tabel = st.radio("Tabel", ["ADHB", "ADHK"], horizontal=True, key="grav_tbl")
        grav_t = "adhb" if grav_tabel == "ADHB" else "adhk"
        top_n_grav = st.slider("Tampilkan Top-N Pasangan", 10, 50, 20, key="grav_topn")

        with st.spinner("Menghitung gravitasi ekonomi..."):
            grav_rows = analytics.compute_gravity(
                pdrb_data, selected_kodes, tabel=grav_t
            )

        if not grav_rows:
            st.warning("Data koordinat atau PDRB tidak cukup. Pastikan minimal 2 kab/kota dipilih.")
        else:
            fig_grav = charts.chart_gravity(
                grav_rows, kode_names, top_n=top_n_grav,
                title=f"Top-{top_n_grav} Interaksi Gravitasi Ekonomi"
            )
            st.plotly_chart(fig_grav, use_container_width=True)

            import pandas as _pd3
            df_grav = _pd3.DataFrame([{
                "Wilayah I":    kode_names.get(r["kode_i"], r["kode_i"]),
                "Wilayah J":    kode_names.get(r["kode_j"], r["kode_j"]),
                "PDRB I (Jt)":  f"{r['pdrb_i']:,.2f}",
                "PDRB J (Jt)":  f"{r['pdrb_j']:,.2f}",
                "Jarak (km)":   f"{r['jarak_km']:.1f}",
                "Interaksi":    f"{r['interaction']:,.2f}",
            } for r in grav_rows[:top_n_grav]])
            with st.expander("📋 Tabel Interaksi Gravitasi", expanded=False):
                st.dataframe(df_grav, use_container_width=True, hide_index=True)

            with st.expander("📖 Interpretasi Model Gravitasi", expanded=False):
                st.markdown("""
**Rumus:** Interaksi(i,j) = (PDRB_i × PDRB_j) / Jarak_ij²

Pasangan wilayah dengan nilai interaksi **tinggi** memiliki potensi:
- Integrasi ekonomi yang kuat (perdagangan, investasi, tenaga kerja)
- Kandidat untuk **kawasan metropolitan / koridor ekonomi**
- Saling ketergantungan tinggi dalam rantai pasokan

Pasangan dengan interaksi **rendah** karena jarak jauh atau PDRB kecil → perlu
infrastruktur konektivitas untuk meningkatkan integrasi regional.
                """)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 8: OVERLAY PRIORITAS REGIONAL
    # ══════════════════════════════════════════════════════════════════════════
    with tab8:
        st.subheader("⭐ Overlay Prioritas Sektor — Perbandingan Regional")
        st.caption("Bandingkan matriks prioritas sektor (LQ + SS + RRG) antar beberapa wilayah.")

        ov_tabel = st.radio("Tabel", ["ADHB", "ADHK"], horizontal=True, key="ov_tbl")
        ov_t = "adhb" if ov_tabel == "ADHB" else "adhk"

        kab_sel_ov = [k for k in selected_kodes if k != "3300"]
        if not kab_sel_ov:
            st.warning("Pilih minimal 1 kabupaten/kota.")
        else:
            sel_ov = st.selectbox(
                "Pilih wilayah untuk ditampilkan matriks prioritasnya:",
                kab_sel_ov,
                format_func=lambda x: kode_names.get(x, x),
                key="ov_sel_wil"
            )

            with st.spinner("Menghitung prioritas sektor..."):
                prio_data = analytics.compute_sector_priority(
                    pdrb_data, sel_ov, tabel=ov_t
                )

            if prio_data:
                fig_ov = charts.chart_sector_priority(
                    prio_data,
                    title=f"Matriks Prioritas Sektor — {kode_names.get(sel_ov, sel_ov)}"
                )
                st.plotly_chart(fig_ov, use_container_width=True)

            # Tabel ringkasan semua wilayah terpilih
            st.markdown("#### 📋 Ringkasan Sektor Unggulan Semua Wilayah Terpilih")
            import pandas as _pd4
            all_rows = []
            for kode in kab_sel_ov:
                pd_data = analytics.compute_sector_priority(pdrb_data, kode, tabel=ov_t)
                top3 = [d for d in pd_data if d["priority_score"] >= 4][:3]
                for d in top3:
                    all_rows.append({
                        "Wilayah":    kode_names.get(kode, kode)[:25],
                        "Sektor":     f"{d['kode_skt']} – {d['nama'][:35]}",
                        "LQ":         f"{d['lq']:.3f}" if d["lq"] else "—",
                        "RRG":        d["rrg_quad"],
                        "CE Status":  d["ce_status"],
                        "Prioritas":  d["priority_label"],
                        "Skor":       d["priority_score"],
                    })
            if all_rows:
                df_all_ov = _pd4.DataFrame(all_rows).sort_values(
                    ["Wilayah", "Skor"], ascending=[True, False]
                )
                st.dataframe(df_all_ov, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada sektor dengan skor prioritas tinggi di wilayah terpilih.")
                    df_all_ov, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada sektor dengan skor prioritas tinggi di wilayah terpilih.")
