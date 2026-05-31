"""
Modul pembangun grafik Plotly untuk dashboard PDRB.
"""

import re as _re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


PALETTE = config.COLORS["palette"]

# Dark theme defaults untuk semua chart
_DARK = dict(
    plot_bgcolor  = getattr(config, "CHART_BG",    "#161b22"),
    paper_bgcolor = getattr(config, "CHART_PAPER", "#0d1117"),
    font          = dict(color=getattr(config, "CHART_TEXT", "#e6edf3"), size=12),
)
_GRID = dict(
    showgrid   = True,
    gridcolor  = getattr(config, "CHART_GRID", "rgba(255,255,255,0.07)"),
    linecolor  = "rgba(255,255,255,0.12)",
    zerolinecolor = "rgba(255,255,255,0.15)",
)


def _apply_dark(fig):
    """Terapkan dark background ke seluruh figure."""
    fig.update_layout(**_DARK)
    fig.update_xaxes(**_GRID)
    fig.update_yaxes(**_GRID)
    return fig


def _ck(kode: str) -> str:
    """Bersihkan kode sektor: Q54→Q, M51→MN, dst."""
    m = _re.match(r'^([A-Za-z]+)\d+', str(kode))
    if m:
        ltr = m.group(1).upper()
        return "MN" if ltr == "M" else ltr
    return str(kode)


# ──────────────────────────────────────────────────────────────────────────────
# GRAFIK DASAR: BATANG / GARIS
# ──────────────────────────────────────────────────────────────────────────────

def chart_bar_line(df_filtered, periods, chart_type="bar",
                   title="PDRB", yaxis_title="Juta Rupiah",
                   height=None):
    """
    Buat grafik batang atau garis untuk data terpilih.
    df_filtered: DataFrame dengan index=sektor, columns=periods, + kolom 'name'
    """
    height = height or config.CHART_HEIGHT
    fig = go.Figure()

    for i, (kode, row) in enumerate(df_filtered.iterrows()):
        y_vals = [row.get(p) for p in periods]
        name   = row.get("name", kode) if "name" in row.index else kode
        color  = PALETTE[i % len(PALETTE)]

        if chart_type == "bar":
            fig.add_trace(go.Bar(
                name=name, x=periods, y=y_vals,
                marker_color=color, text=[f"{v:,.0f}" if v else "" for v in y_vals],
                textposition="outside",
            ))
        else:
            fig.add_trace(go.Scatter(
                name=name, x=periods, y=y_vals,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=5),
            ))

    n_traces = len(df_filtered)

    # Banyak trace → legend di kanan (vertikal) agar x-axis tidak tertutup
    if n_traces > 6:
        legend_cfg = dict(
            orientation="v",
            yanchor="top", y=1,
            xanchor="left", x=1.01,
            font=dict(size=10, color="#e6edf3"),
            itemsizing="constant",
            bgcolor="rgba(22,27,34,0.95)",
            bordercolor="rgba(0,212,170,0.35)",
            borderwidth=1,
        )
        margin_cfg = dict(l=60, r=220, t=50, b=80)
    else:
        leg_rows   = max(1, (n_traces + 2) // 3)
        b_margin   = 80 + leg_rows * 24
        legend_cfg = dict(
            orientation="h",
            yanchor="top", y=-0.18,
            xanchor="left", x=0,
            font=dict(size=10),
            itemsizing="constant",
        )
        margin_cfg = dict(l=60, r=20, t=50, b=b_margin)

    layout_args = dict(
        title=title,
        xaxis_title="Periode",
        yaxis_title=yaxis_title,
        height=height,
        hovermode="x unified",
        legend=legend_cfg,
        margin=margin_cfg,
        xaxis=dict(tickangle=-45),
    )
    fig.update_layout(**layout_args)
    _apply_dark(fig)
    return fig


def chart_growth(growth_dict_per_sektor, periods, chart_type="bar",
                 title="Pertumbuhan PDRB (%)", height=None):
    """
    Buat grafik pertumbuhan (%).
    growth_dict_per_sektor: { sektor_name: { period: pct } }
    """
    height = height or config.CHART_HEIGHT
    fig = go.Figure()

    for i, (name, growth_dict) in enumerate(growth_dict_per_sektor.items()):
        y_vals = [growth_dict.get(p) for p in periods]
        color  = PALETTE[i % len(PALETTE)]

        if chart_type == "bar":
            fig.add_trace(go.Bar(
                name=name, x=periods, y=y_vals,
                marker_color=color,
            ))
        else:
            fig.add_trace(go.Scatter(
                name=name, x=periods, y=y_vals,
                mode="lines+markers",
                line=dict(color=color, width=2),
            ))

    n_g = len(growth_dict_per_sektor)
    if n_g > 6:
        leg_g  = dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01,
                      font=dict(size=10, color="#e6edf3"), itemsizing="constant",
                      bgcolor="rgba(22,27,34,0.95)", bordercolor="rgba(0,212,170,0.35)", borderwidth=1)
        mar_g  = dict(l=60, r=220, t=50, b=80)
    else:
        leg_rows_g = max(1, (n_g + 2) // 3)
        leg_g  = dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0,
                      font=dict(size=10), itemsizing="constant")
        mar_g  = dict(l=60, r=20, t=50, b=80 + leg_rows_g * 24)

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title=title,
        xaxis_title="Periode",
        yaxis_title="Pertumbuhan (%)",
        height=height,
        hovermode="x unified",
        barmode="group",
        legend=leg_g,
        margin=mar_g,
        xaxis=dict(tickangle=-45),
    )
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# DISTRIBUSI: TREEMAP & PIE
# ──────────────────────────────────────────────────────────────────────────────

def chart_treemap(labels, values, parents=None, title="Distribusi PDRB", height=None):
    """Treemap distribusi PDRB."""
    n = len(labels)
    height = height or max(620, 560 + n * 5)
    if parents is None:
        parents = [""] * len(labels)

    fig = go.Figure(go.Treemap(
        labels=labels,
        values=values,
        parents=parents,
        textinfo="label+percent entry",
        hovertemplate="<b>%{label}</b><br>Nilai: %{value:,.2f} juta<br>Share: %{percentParent:.1%}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, x=0.01),
        height=height,
        margin=dict(t=50, l=5, r=5, b=5),
    )
    _apply_dark(fig)
    return fig


def chart_pie(labels, values, title="Distribusi PDRB", height=None, hole=0.3):
    """Donut/Pie chart distribusi PDRB."""
    n = len(labels)
    # Tinggi dinamis agar legend vertikal di kanan tidak terpotong
    height = height or max(640, 500 + max(0, n - 10) * 20)

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=hole,
        textinfo="percent",
        textposition="inside",
        automargin=True,
        hovertemplate="<b>%{label}</b><br>Nilai: %{value:,.2f} juta<br>Share: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, x=0.01),
        height=height,
        legend=dict(
            orientation="v",
            x=1.02,
            y=1.0,
            xanchor="left",
            yanchor="top",
            font=dict(size=11),
            tracegroupgap=2,
        ),
        margin=dict(t=50, l=10, r=230, b=20),
    )
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# LQ
# ──────────────────────────────────────────────────────────────────────────────

def chart_lq_bar(lq_series: dict, sector_names: dict,
                  title="Location Quotient", height=None):
    """Bar chart LQ untuk satu periode — horizontal agar nama sektor terbaca."""
    n      = len(lq_series)
    height = height or max(500, 80 + n * 28)   # ~28px per sektor
    codes  = sorted(lq_series.keys())
    names  = [f"{_ck(c)} – {sector_names.get(c, c)[:45]}" for c in codes]
    values = [lq_series.get(c) for c in codes]
    colors = ["#2ca02c" if (v and v >= 1) else "#d62728" for v in values]

    fig = go.Figure(go.Bar(
        y=names, x=values,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}" if v else "" for v in values],
        textposition="outside",
    ))
    fig.add_vline(x=1.0, line_dash="dash", line_color="orange",
                  annotation_text="LQ=1", annotation_position="top right")
    fig.update_layout(
        title=dict(text=title, x=0.01),
        xaxis_title="Nilai LQ",
        yaxis_title="",
        height=height,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=280, r=60, t=50, b=40),
    )
    _apply_dark(fig)
    return fig


def chart_lq_heatmap(lq_df: pd.DataFrame, sector_names: dict,
                      title="Heatmap LQ", height=None):
    """Heatmap LQ: rows=sektor, cols=periode."""
    n      = len(lq_df.index)
    height = height or max(500, 100 + n * 26)
    y_labels = [f"{_ck(c)} – {sector_names.get(c, c)[:40]}" if sector_names else _ck(c)
                for c in lq_df.index]

    fig = go.Figure(go.Heatmap(
        z=lq_df.values,
        x=list(lq_df.columns),
        y=y_labels,
        colorscale=[[0, "#d62728"], [0.5, "#ffffff"], [1, "#2ca02c"]],
        zmid=1.0,
        text=[[f"{v:.2f}" if v and not np.isnan(v) else "" for v in row]
               for row in lq_df.values],
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b><br>Periode: %{x}<br>LQ: %{z:.3f}<extra></extra>",
        colorbar=dict(title="LQ"),
    ))
    fig.update_layout(
        title=dict(text=title, x=0.01),
        height=height,
        xaxis_tickangle=-45,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=320, r=20, t=50, b=60),
    )
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# SHIFT SHARE
# ──────────────────────────────────────────────────────────────────────────────

def chart_shift_share(ss_df: pd.DataFrame, components=("NS", "IM", "CE"),
                       title="Shift Share Analysis", height=None):
    """Grouped bar chart komponen Shift Share — horizontal agar nama sektor terbaca."""
    n      = len(ss_df)
    height = height or max(500, 80 + n * 30)   # ~30px per sektor
    colors_map = {
        "NS": "#1f77b4",
        "IM": "#ff7f0e",
        "CE": "#2ca02c",
        "Net Shift": "#d62728",
        "Total Perubahan": "#9467bd",
    }
    nama_col = ss_df["nama"] if "nama" in ss_df.columns else ss_df.index
    # Buat label singkat: kode – nama (max 45 karakter)
    if ss_df.index.name == "kode" or (hasattr(ss_df.index, 'name') and ss_df.index.name):
        labels = [f"{_ck(idx)} – {row[:45]}" for idx, row in zip(ss_df.index, nama_col)]
    else:
        labels = [str(v)[:55] for v in nama_col]

    fig = go.Figure()
    for comp in components:
        if comp not in ss_df.columns:
            continue
        fig.add_trace(go.Bar(
            name=comp,
            y=labels,
            x=ss_df[comp],
            orientation="h",
            marker_color=colors_map.get(comp, "#9467bd"),
        ))
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title=dict(text=title, x=0.01),
        barmode="group",
        xaxis_title="Nilai (Juta Rupiah)",
        yaxis_title="",
        height=height,
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=320, r=40, t=80, b=40),
    )
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# RRG (Relative Regional Growth / Portfolio Matrix)
# ──────────────────────────────────────────────────────────────────────────────

def chart_rrg(rrg_df: pd.DataFrame, title="Relative Regional Growth (RRG)",
              height=None, show_arrows=True):
    """
    Scatter plot RRG dengan 4 kuadran berwarna.
    X-axis: RS (Relative Share)  |  Y-axis: RGR (Relative Growth Rate)
    """
    height = height or 680

    quad_cfg = {
        "⭐ Stars":     dict(color="#2ca02c", bg="rgba(44,160,44,0.07)"),
        "❓ Question":  dict(color="#1f77b4", bg="rgba(31,119,180,0.07)"),
        "🐄 Cash Cow":  dict(color="#ff7f0e", bg="rgba(255,127,14,0.07)"),
        "🐕 Dogs":      dict(color="#d62728", bg="rgba(214,39,40,0.07)"),
    }

    x_mid = 1.0
    y_mid = 1.0

    # Padding sumbu berdasarkan rentang data
    all_rs  = list(rrg_df["RS"])
    all_rgr = list(rrg_df["RGR"])
    pad = 0.25
    x_min = min(all_rs  + [x_mid - 0.5]) - pad
    x_max = max(all_rs  + [x_mid + 0.5]) + pad
    y_min = min(all_rgr + [y_mid - 0.5]) - pad
    y_max = max(all_rgr + [y_mid + 0.5]) + pad

    fig = go.Figure()

    # ── Background kuadran (shapes) ──
    quad_shapes = [
        # Stars  (kanan-atas)
        dict(x0=x_mid, x1=x_max, y0=y_mid, y1=y_max,
             fillcolor="rgba(44,160,44,0.08)", line_width=0),
        # Question  (kiri-atas)
        dict(x0=x_min, x1=x_mid, y0=y_mid, y1=y_max,
             fillcolor="rgba(31,119,180,0.08)", line_width=0),
        # Cash Cow  (kanan-bawah)
        dict(x0=x_mid, x1=x_max, y0=y_min, y1=y_mid,
             fillcolor="rgba(255,127,14,0.08)", line_width=0),
        # Dogs  (kiri-bawah)
        dict(x0=x_min, x1=x_mid, y0=y_min, y1=y_mid,
             fillcolor="rgba(214,39,40,0.08)", line_width=0),
    ]
    for sh in quad_shapes:
        fig.add_shape(type="rect", xref="x", yref="y", **sh)

    # ── Kelompokkan titik per kuadran untuk legend bersih ──
    groups = {"⭐ Stars": [], "❓ Question": [], "🐄 Cash Cow": [], "🐕 Dogs": []}
    for kode_s, row in rrg_df.iterrows():
        rs, rgr = row["RS"], row["RGR"]
        if   rs >= x_mid and rgr >= y_mid: q = "⭐ Stars"
        elif rs <  x_mid and rgr >= y_mid: q = "❓ Question"
        elif rs >= x_mid and rgr <  y_mid: q = "🐄 Cash Cow"
        else:                              q = "🐕 Dogs"
        groups[q].append((kode_s, row))

    for quad_name, items in groups.items():
        if not items:
            continue
        cfg   = quad_cfg[quad_name]
        xs    = [r["RS"]  for _, r in items]
        ys    = [r["RGR"] for _, r in items]
        texts = [r.get("name", k)[:22] for k, r in items]
        hovs  = [
            f"<b>{r.get('name', k)}</b><br>RS: {r['RS']:.3f}<br>RGR: {r['RGR']:.3f}"
            for k, r in items
        ]
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            name=quad_name,
            marker=dict(size=14, color=cfg["color"],
                        line=dict(width=1.5, color="white")),
            text=texts,
            textposition="top center",
            textfont=dict(size=10, color=cfg["color"]),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hovs,
            legendgroup=quad_name,
        ))

        # ── Panah pergerakan: line + dot tail + annotation head ──
        if show_arrows:
            for k, r in items:
                rs, rgr = r["RS"], r["RGR"]
                rs_p  = r.get("RS_prev",  rs)
                rgr_p = r.get("RGR_prev", rgr)
                dist = ((rs - rs_p)**2 + (rgr - rgr_p)**2) ** 0.5
                if dist < 0.008:
                    continue

                # 1. Batang (shaft) panah — scatter line, selalu terlihat
                fig.add_trace(go.Scatter(
                    x=[rs_p, rs], y=[rgr_p, rgr],
                    mode="lines",
                    line=dict(color=cfg["color"], width=2.5),
                    opacity=0.8,
                    showlegend=False,
                    hoverinfo="skip",
                ))

                # 2. Tail (titik awal) — lingkaran kosong di posisi sebelumnya
                fig.add_trace(go.Scatter(
                    x=[rs_p], y=[rgr_p],
                    mode="markers",
                    marker=dict(
                        size=9, color="white",
                        line=dict(color=cfg["color"], width=2.5),
                        symbol="circle",
                    ),
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{r.get('name', k)}</b> (Sebelumnya)<br>"
                        f"RS: {rs_p:.3f}<br>RGR: {rgr_p:.3f}<extra></extra>"
                    ),
                ))

                # 3. Kepala panah — annotation arrowhead di posisi saat ini
                fig.add_annotation(
                    x=rs, y=rgr, ax=rs_p, ay=rgr_p,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1.2,
                    arrowwidth=2.5, arrowcolor=cfg["color"],
                    text="", opacity=0.85,
                )

    # ── Garis tengah ──
    fig.add_vline(x=x_mid, line_dash="dot", line_color="#666", opacity=0.6,
                  annotation_text="RS=1", annotation_position="top right",
                  annotation_font_size=10)
    fig.add_hline(y=y_mid, line_dash="dot", line_color="#666", opacity=0.6,
                  annotation_text="RGR=1", annotation_position="top right",
                  annotation_font_size=10)

    # ── Label sudut kuadran ──
    corner_labels = [
        (x_max - pad*0.3, y_max - pad*0.3, "⭐ Stars",    "#2ca02c"),
        (x_min + pad*0.3, y_max - pad*0.3, "❓ Question", "#1f77b4"),
        (x_max - pad*0.3, y_min + pad*0.3, "🐄 Cash Cow", "#ff7f0e"),
        (x_min + pad*0.3, y_min + pad*0.3, "🐕 Dogs",     "#d62728"),
    ]
    for xc, yc, lbl, clr in corner_labels:
        fig.add_annotation(
            x=xc, y=yc, text=f"<b>{lbl}</b>",
            showarrow=False,
            font=dict(size=13, color=clr),
            bgcolor="rgba(255,255,255,0.75)",
            bordercolor=clr, borderwidth=1, borderpad=4,
        )

    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=14)),
        xaxis=dict(title="Relative Share (RS)",
                   range=[x_min, x_max], zeroline=False, showgrid=True,
                   gridcolor="rgba(200,200,200,0.4)"),
        yaxis=dict(title="Relative Growth Rate (RGR)",
                   range=[y_min, y_max], zeroline=False, showgrid=True,
                   gridcolor="rgba(200,200,200,0.4)"),
        height=height,
        plot_bgcolor="white",
        legend=dict(
            title="Kuadran",
            orientation="v", x=1.01, y=1,
            xanchor="left", yanchor="top",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#ccc", borderwidth=1,
        ),
        margin=dict(l=70, r=160, t=60, b=60),
        hovermode="closest",
    )
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# KETIMPANGAN
# ──────────────────────────────────────────────────────────────────────────────

def chart_williamson_trend(williams_dict: dict, title="Indeks Williamson",
                            height=None):
    """Grafik tren Indeks Williamson."""
    height = height or 400
    periods = sorted(williams_dict.keys())
    vals = [williams_dict[p] for p in periods]
    fig = go.Figure(go.Scatter(
        x=periods, y=vals, mode="lines+markers",
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy", fillcolor="rgba(31,119,180,0.1)",
    ))
    fig.update_layout(
        title=title, xaxis_title="Periode", yaxis_title="Indeks Williamson",
        height=height, xaxis_tickangle=-45,
    )
    _apply_dark(fig)
    return fig


def chart_klassen_scatter(klassen_df: pd.DataFrame, kode_names: dict,
                           g_prov: float, y_prov: float,
                           title="Tipologi Klassen", height=None):
    """Scatter plot tipologi Klassen."""
    height = height or 500
    colors_klass = {
        "I":  "#2ca02c", "II": "#ff7f0e",
        "III": "#1f77b4", "IV": "#d62728",
    }
    label_klass = {
        "I":  "Maju & Tumbuh Pesat",
        "II": "Maju tapi Tertekan",
        "III": "Berkembang Cepat",
        "IV": "Relatif Tertinggal",
    }
    fig = go.Figure()
    for q in ["I", "II", "III", "IV"]:
        sub = klassen_df[klassen_df["kuadran"] == q] if "kuadran" in klassen_df.columns else klassen_df.iloc[0:0]
        if sub.empty:
            continue
        names = [kode_names.get(k, k) for k in sub.index]
        fig.add_trace(go.Scatter(
            x=sub["pdrb_pc"], y=sub["pertumbuhan_%"],
            mode="markers+text",
            name=f"Kuadran {q}: {label_klass[q]}",
            marker=dict(size=12, color=colors_klass[q]),
            text=names, textposition="top center",
            textfont=dict(size=9),
        ))
    fig.add_vline(x=y_prov, line_dash="dash", line_color="gray")
    fig.add_hline(y=g_prov, line_dash="dash", line_color="gray")
    fig.update_layout(
        title=title,
        xaxis_title="PDRB per Kapita (Juta Rp/Jiwa)",
        yaxis_title="Pertumbuhan PDRB per Kapita (%)",
        height=height,
    )
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# PROYEKSI
# ──────────────────────────────────────────────────────────────────────────────

def chart_projection(proj_result: dict, title="Proyeksi PDRB", height=None):
    """Grafik proyeksi PDRB dengan historis dan forecast."""
    height = height or config.CHART_HEIGHT
    fig = go.Figure()

    # Historis
    fig.add_trace(go.Scatter(
        x=proj_result["periods_hist"],
        y=proj_result["values_hist"],
        name="Data Historis",
        mode="lines+markers",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=5),
    ))

    # Forecast
    fig.add_trace(go.Scatter(
        x=proj_result["periods_fcst"],
        y=proj_result["values_fcst"],
        name="Proyeksi",
        mode="lines+markers",
        line=dict(color="#ff7f0e", width=2, dash="dash"),
        marker=dict(size=7, symbol="diamond"),
    ))

    # Confidence band (±10% sebagai ilustrasi)
    vals_f = proj_result["values_fcst"]
    upper  = [v * 1.1 for v in vals_f]
    lower  = [max(0, v * 0.9) for v in vals_f]
    periods_f = proj_result["periods_fcst"]

    fig.add_trace(go.Scatter(
        x=periods_f + periods_f[::-1],
        y=upper + lower[::-1],
        fill="toself",
        fillcolor="rgba(255,127,14,0.1)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Interval ±10%",
    ))

    # Garis pemisah historis-proyeksi
    # Garis pemisah historis-proyeksi (pakai add_shape, bukan add_vline,
    # karena x-axis kategorik tidak kompatibel dengan add_vline di Plotly)
    if proj_result["periods_hist"] and proj_result["periods_fcst"]:
        sep_x = len(proj_result["periods_hist"]) - 0.5
        fig.add_shape(
            type="line",
            x0=sep_x, x1=sep_x, y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(dash="dot", color="gray", width=1.5),
        )
        fig.add_annotation(
            x=sep_x, y=1, xref="x", yref="paper",
            text="Akhir data", showarrow=False,
            font=dict(size=10, color="gray"),
            xanchor="left", yanchor="top",
        )

    r2_text = ""
    if proj_result.get("r2") is not None:
        r2_text = f" | R² = {proj_result['r2']:.4f}"

    fig.update_layout(
        title=title + r2_text,
        xaxis_title="Periode",
        yaxis_title="Juta Rupiah",
        height=height,
        hovermode="x unified",
        xaxis_tickangle=-45,
    )
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# PETA CHOROPLETH
# ──────────────────────────────────────────────────────────────────────────────

def chart_choropleth(geojson, kode_vals: dict, kode_names: dict,
                      title="Peta PDRB", colorscale="YlOrRd",
                      height=None, featureidkey="properties.kode"):
    """
    Peta choropleth Jawa Tengah.
    kode_vals: { kode_str: nilai }
    """
    height = height or config.MAP_HEIGHT
    codes  = list(kode_vals.keys())
    vals   = [kode_vals[k] for k in codes]
    names  = [kode_names.get(k, k) for k in codes]

    fig = px.choropleth(
        locations=codes,
        geojson=geojson,
        color=vals,
        featureidkey=featureidkey,
        color_continuous_scale=colorscale,
        hover_name=names,
        labels={"color": "Nilai"},
        title=title,
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=40, b=0))
    _apply_dark(fig)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# PETA BUBBLE (FALLBACK TANPA GEOJSON)
# ──────────────────────────────────────────────────────────────────────────────

def chart_bubble_map(kode_vals: dict, kode_names: dict,
                     centroids: dict,
                     title="Peta PDRB", colorscale="YlOrRd",
                     height=None, value_label="Nilai"):
    """
    Peta gelembung (bubble map) berbasis OpenStreetMap tiles.
    Digunakan sebagai fallback ketika GeoJSON tidak tersedia.

    Parameters
    ----------
    kode_vals   : { kode_str: nilai_numerik }
    kode_names  : { kode_str: nama_wilayah }
    centroids   : { kode_str: (lat, lon, nama_pendek) }  — dari centroids_jateng.py
    """
    height = height or config.MAP_HEIGHT

    rows = []
    for kode, val in kode_vals.items():
        if kode not in centroids:
            continue
        lat, lon, _ = centroids[kode]
        rows.append({
            "kode": kode,
            "nama": kode_names.get(kode, kode),
            "lat": lat,
            "lon": lon,
            "nilai": val,
        })

    if not rows:
        fig = go.Figure()
        fig.update_layout(title=title, height=height)
        _apply_dark(fig)
    return fig

    df_map = pd.DataFrame(rows)

    fig = px.scatter_map(
        df_map,
        lat="lat", lon="lon",
        size="nilai",
        color="nilai",
        color_continuous_scale=colorscale,
        hover_name="nama",
        hover_data={"nilai": ":,.2f", "lat": False, "lon": False},
        size_max=55,
        zoom=6.8,
        center={"lat": -7.15, "lon": 110.15},
        map_style="open-street-map",
        title=title,
        labels={"nilai": value_label},
    )
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(title=value_label, thickness=14, len=0.7),
    )
    _apply_dark(fig)
    return fig


# 


# ──────────────────────────────────────────────────────────────────────────────
# RRG TRAIL – gaya Relative Rotation Graph standar
# ──────────────────────────────────────────────────────────────────────────────

def chart_rrg_trail(trail_data: dict, title="Relative Rotation Graph (RRG)",
                    height=None, n_tail=6):
    """
    Gambar RRG trail multi-titik per sektor.

    trail_data : output dari compute_rrg_trail() atau compute_rrg_trail_regional()
                 { kode: { 'name', 'parent', 'trail': [{'period','RS','RGR'},...] } }
    n_tail     : jumlah titik trail yang ditampilkan (terbaru)
    """
    height = height or 860

    # ── Konfigurasi kuadran ──────────────────────────────────────────────────
    QUAD = {
        "LEADING":   dict(color="#2ca02c", bg="rgba(44,160,44,0.08)",
                          x_side="right", y_side="top"),
        "WEAKENING": dict(color="#ff7f0e", bg="rgba(255,127,14,0.08)",
                          x_side="right", y_side="bottom"),
        "IMPROVING": dict(color="#1f77b4", bg="rgba(31,119,180,0.08)",
                          x_side="left",  y_side="top"),
        "LAGGING":   dict(color="#d62728", bg="rgba(214,39,40,0.08)",
                          x_side="left",  y_side="bottom"),
    }
    MID = 100.0   # garis tengah kedua sumbu

    def _quadrant(rs, rgr):
        if   rs >= MID and rgr >= MID: return "LEADING"
        elif rs >= MID and rgr <  MID: return "WEAKENING"
        elif rs <  MID and rgr >= MID: return "IMPROVING"
        else:                          return "LAGGING"

    # ── Kumpulkan semua nilai untuk hitung range sumbu ───────────────────────
    all_rs, all_rgr = [MID], [MID]
    for meta in trail_data.values():
        for pt in meta.get("trail", [])[-n_tail:]:
            all_rs.append(pt["RS"])
            all_rgr.append(pt["RGR"])

    pad   = max(5.0, (max(all_rs) - min(all_rs)) * 0.18,
                     (max(all_rgr) - min(all_rgr)) * 0.18)
    x_min = min(all_rs)  - pad;  x_max = max(all_rs)  + pad
    y_min = min(all_rgr) - pad;  y_max = max(all_rgr) + pad

    fig = go.Figure()

    # ── Background kuadran ───────────────────────────────────────────────────
    for name, cfg in QUAD.items():
        x0 = MID if cfg["x_side"] == "right" else x_min
        x1 = x_max if cfg["x_side"] == "right" else MID
        y0 = MID if cfg["y_side"] == "top"    else y_min
        y1 = y_max if cfg["y_side"] == "top"  else MID
        fig.add_shape(type="rect", xref="x", yref="y",
                      x0=x0, x1=x1, y0=y0, y1=y1,
                      fillcolor=cfg["bg"], line_width=0, layer="below")

    # ── Label kuadran ────────────────────────────────────────────────────────
    corner_pos = {
        "LEADING":   (x_max - pad*0.3, y_max - pad*0.3),
        "WEAKENING": (x_max - pad*0.3, y_min + pad*0.3),
        "IMPROVING": (x_min + pad*0.3, y_max - pad*0.3),
        "LAGGING":   (x_min + pad*0.3, y_min + pad*0.3),
    }
    for qname, (xc, yc) in corner_pos.items():
        fig.add_annotation(
            x=xc, y=yc, text=f"<b>{qname}</b>",
            showarrow=False,
            font=dict(size=14, color=QUAD[qname]["color"]),
            opacity=0.55,
        )

    # ── Garis tengah ─────────────────────────────────────────────────────────
    fig.add_vline(x=MID, line_dash="dot", line_color="#888", line_width=1.2, opacity=0.7)
    fig.add_hline(y=MID, line_dash="dot", line_color="#888", line_width=1.2, opacity=0.7)

    # ── Kelompokkan entri per kuadran untuk legend ────────────────────────────
    quad_groups: dict[str, list] = {q: [] for q in QUAD}
    for kode_s, meta in trail_data.items():
        trail = meta.get("trail", [])
        if not trail:
            continue
        tail   = trail[-n_tail:]
        latest = tail[-1]
        qname  = _quadrant(latest["RS"], latest["RGR"])
        quad_groups[qname].append((kode_s, meta, tail, latest, qname))

    # ── Gambar trail & titik per entri ───────────────────────────────────────
    legend_added: set[str] = set()

    for qname, entries in quad_groups.items():
        color = QUAD[qname]["color"]
        for kode_s, meta, tail, latest, _ in entries:
            label  = meta.get("name", kode_s)[:28]
            show_l = qname not in legend_added

            # Gradasi opacity: titik lama lebih transparan
            n = len(tail)
            for i in range(len(tail) - 1):
                opacity_line = 0.25 + 0.65 * (i / max(n - 1, 1))
                fig.add_trace(go.Scatter(
                    x=[tail[i]["RS"],     tail[i+1]["RS"]],
                    y=[tail[i]["RGR"],    tail[i+1]["RGR"]],
                    mode="lines",
                    line=dict(color=color, width=2.2),
                    opacity=opacity_line,
                    showlegend=False,
                    hoverinfo="skip",
                ))

            # Titik historis (kecil, transparan)
            if n > 1:
                fig.add_trace(go.Scatter(
                    x=[pt["RS"]  for pt in tail[:-1]],
                    y=[pt["RGR"] for pt in tail[:-1]],
                    mode="markers",
                    marker=dict(size=6, color=color, opacity=0.35,
                                line=dict(color="white", width=0.8)),
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{label}</b><br>"
                        "Periode: %{customdata}<br>"
                        "RS: %{x:.2f} | RGR: %{y:.2f}<extra></extra>"
                    ),
                    customdata=[pt["period"] for pt in tail[:-1]],
                ))

            # Titik terkini (besar, penuh) — satu per kuadran untuk legend
            fig.add_trace(go.Scatter(
                x=[latest["RS"]],
                y=[latest["RGR"]],
                mode="markers+text",
                name=qname if show_l else "",
                marker=dict(size=13, color=color,
                            line=dict(color="white", width=1.8)),
                text=[label],
                textposition="top center",
                textfont=dict(size=9, color=color),
                showlegend=show_l,
                legendgroup=qname,
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    f"Periode: {latest['period']}<br>"
                    "RS: %{x:.2f} | RGR: %{y:.2f}<extra></extra>"
                ),
            ))
            if show_l:
                legend_added.add(qname)


    # ── Layout ──────────────────────────────────────────────────────────────

    # ── Layout ──────────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=14)),
        xaxis=dict(
            title="RS-Ratio →",
            range=[x_min, x_max], zeroline=False,
            showgrid=True, gridcolor="rgba(255,255,255,0.07)",
            linecolor="rgba(255,255,255,0.12)",
        ),
        yaxis=dict(
            title="RS-Momentum →",
            range=[y_min, y_max], zeroline=False,
            showgrid=True, gridcolor="rgba(255,255,255,0.07)",
            linecolor="rgba(255,255,255,0.12)",
        ),
        height=height,
        plot_bgcolor=getattr(config, "CHART_BG", "#161b22"),
        paper_bgcolor=getattr(config, "CHART_PAPER", "#0d1117"),
        font=dict(color=getattr(config, "CHART_TEXT", "#e6edf3"), size=12),
        legend=dict(
            orientation="h",
            x=0.0, y=-0.10,
            xanchor="left", yanchor="top",
            bgcolor="rgba(22,27,34,0.92)",
            bordercolor="rgba(255,255,255,0.15)",
            borderwidth=1,
            font=dict(size=11),
            itemsizing="constant",
        ),
        margin=dict(l=65, r=30, t=60, b=110),
        hovermode="closest",
    )
    _apply_dark(fig)
    return fig
