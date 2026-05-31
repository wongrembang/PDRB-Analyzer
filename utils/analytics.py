"""
Modul analisis ekonomi PDRB:
  - Location Quotient (LQ)
  - Shift Share Analysis
  - Relative Regional Growth (RRG)
  - Williamson Index
  - Klassen Typology
  - Theil Index
  - Kemiripan Struktur Ekonomi
  - Proyeksi PDRB
"""

import re as _re
import numpy as np
import pandas as pd
from scipy import stats
import warnings

warnings.filterwarnings("ignore")


def clean_kode(ks: str) -> str:
    """Bersihkan kode sektor: hapus digit di belakang huruf.
    Contoh: Q54→Q, P53→P, M51→MN, L50→L, F34→F, dst.
    """
    m = _re.match(r'^([A-Za-z]+)\d+', str(ks))
    if m:
        ltr = m.group(1).upper()
        return "MN" if ltr == "M" else ltr
    return str(ks)


# ─────────────────────────────────────────────────────────────────────
# LOCATION QUOTIENT (LQ)
# ─────────────────────────────────────────────────────────────────────

def compute_lq(region_sector_vals, province_sector_vals, region_total, province_total):
    if not province_total or province_total == 0:
        return {}
    result = {}
    for sektor, e_i in region_sector_vals.items():
        E_i = province_sector_vals.get(sektor)
        if e_i and E_i and E_i != 0 and region_total and region_total != 0:
            result[sektor] = round((e_i / region_total) / (E_i / province_total), 4)
        else:
            result[sektor] = None
    return result


def compute_lq_timeseries(pdrb_data, kode_region, kode_prov="3300", tabel="adhk", periods=None):
    if kode_region not in pdrb_data or kode_prov not in pdrb_data:
        return pd.DataFrame()
    tbl_r = pdrb_data[kode_region][tabel]
    tbl_p = pdrb_data[kode_prov][tabel]
    if periods is None:
        periods = tbl_r["periods"]
    results = {}
    for period in periods:
        region_total = tbl_r["total"].get(period)
        prov_total   = tbl_p["total"].get(period)
        region_sct   = {k: v["values"].get(period) for k, v in tbl_r["sectors"].items()}
        prov_sct     = {k: v["values"].get(period) for k, v in tbl_p["sectors"].items()}
        results[period] = compute_lq(region_sct, prov_sct, region_total, prov_total)
    return pd.DataFrame(results)


def classify_lq(lq_value):
    if lq_value is None: return "N/A"
    if lq_value >= 1.5:  return "Sektor Basis Kuat"
    if lq_value >= 1.0:  return "Sektor Basis"
    if lq_value >= 0.5:  return "Mendekati Basis"
    return "Bukan Sektor Basis"


# ─────────────────────────────────────────────────────────────────────
# SHIFT SHARE
# ─────────────────────────────────────────────────────────────────────

def compute_shift_share(pdrb_data, kode_region, kode_prov="3300",
                        tabel="adhk", period_base=None, period_end=None):
    if kode_region not in pdrb_data or kode_prov not in pdrb_data:
        return pd.DataFrame()
    tbl_r = pdrb_data[kode_region][tabel]
    tbl_p = pdrb_data[kode_prov][tabel]
    periods = sorted(tbl_r["periods"])
    if period_base is None: period_base = periods[0]
    if period_end  is None: period_end  = periods[-1]

    E0 = tbl_p["total"].get(period_base)
    Et = tbl_p["total"].get(period_end)
    if not E0 or E0 == 0 or Et is None:
        return pd.DataFrame()
    g_prov = (Et - E0) / E0

    records = []
    for kode_s, meta in tbl_r["sectors"].items():
        e0 = meta["values"].get(period_base)
        et = meta["values"].get(period_end)
        prov_sec = tbl_p["sectors"].get(kode_s, {})
        E0_i = prov_sec.get("values", {}).get(period_base)
        Et_i = prov_sec.get("values", {}).get(period_end)
        if not all([e0, et, E0_i, Et_i]) or E0_i == 0 or e0 == 0:
            continue
        g_prov_i = (Et_i - E0_i) / E0_i
        g_reg_i  = (et - e0) / e0
        NS  = e0 * g_prov
        IM  = e0 * (g_prov_i - g_prov)
        CE  = e0 * (g_reg_i - g_prov_i)
        records.append({
            "kode": kode_s, "nama": meta["name"], "parent": meta["parent"],
            "E0 (Basis)": round(e0, 2), "Et (Akhir)": round(et, 2),
            "NS": round(NS, 2), "IM": round(IM, 2), "CE": round(CE, 2),
            "Net Shift": round(IM + CE, 2), "Total Perubahan": round(et - e0, 2),
        })
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).set_index("kode")


# ─────────────────────────────────────────────────────────────────────
# RRG – SATU WILAYAH (per sektor)
# ─────────────────────────────────────────────────────────────────────

def compute_rrg(pdrb_data, kode_region, kode_prov="3300", tabel="adhk", n_periods=8):
    if kode_region not in pdrb_data or kode_prov not in pdrb_data:
        return pd.DataFrame()
    tbl_r = pdrb_data[kode_region][tabel]
    tbl_p = pdrb_data[kode_prov][tabel]
    valid = sorted([p for p in tbl_r["periods"] if tbl_r["total"].get(p) and tbl_p["total"].get(p)])
    if len(valid) < 5:
        return pd.DataFrame()

    p_recent  = valid[-n_periods:]
    half      = max(2, len(p_recent) // 2)
    p_current = p_recent[-half:]
    p_prev    = p_recent[:half] if len(p_recent) >= 2 * half else p_recent[:-half]
    if not p_prev: p_prev = p_current

    def _calc(pset):
        ps, pe = pset[0], pset[-1]
        r_tot_s = tbl_r["total"].get(ps) or 0
        r_tot_e = tbl_r["total"].get(pe) or 0
        p_tot_s = tbl_p["total"].get(ps) or 0
        p_tot_e = tbl_p["total"].get(pe) or 0
        out = {}
        for ks, meta in tbl_r["sectors"].items():
            e_s = meta["values"].get(ps)
            e_e = meta["values"].get(pe)
            pm  = tbl_p["sectors"].get(ks, {})
            E_s = pm.get("values", {}).get(ps)
            E_e = pm.get("values", {}).get(pe)
            if not all([e_s, e_e, E_s, E_e, r_tot_e, p_tot_e, r_tot_s, p_tot_s]):
                continue
            if E_e == 0 or p_tot_e == 0 or e_s == 0 or E_s == 0:
                continue
            RS  = (e_e / r_tot_e) / (E_e / p_tot_e)
            g_r = (e_e - e_s) / abs(e_s)
            g_p = (E_e - E_s) / abs(E_s)
            RGR = g_r / g_p if g_p != 0 else None
            if RS is not None and RGR is not None:
                out[ks] = {"RS": RS, "RGR": RGR}
        return out

    cur = _calc(p_current)
    prv = _calc(p_prev)
    rows = []
    for ks, meta in tbl_r["sectors"].items():
        cv = cur.get(ks, {})
        pv = prv.get(ks, {})
        if cv.get("RS") is not None and cv.get("RGR") is not None:
            rows.append({"kode": ks, "name": meta["name"], "parent": meta["parent"],
                         "RS": cv["RS"], "RGR": cv["RGR"],
                         "RS_prev": pv.get("RS", cv["RS"]),
                         "RGR_prev": pv.get("RGR", cv["RGR"])})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("kode")


# ─────────────────────────────────────────────────────────────────────
# RRG – REGIONAL (per kab/kota)
# ─────────────────────────────────────────────────────────────────────

def compute_rrg_regional(pdrb_data, kode_list, kode_prov="3300", tabel="adhk", n_periods=8):
    if kode_prov not in pdrb_data:
        return pd.DataFrame()
    tbl_p = pdrb_data[kode_prov][tabel]
    valid = sorted([p for p in tbl_p["periods"] if tbl_p["total"].get(p)])
    if len(valid) < 4:
        return pd.DataFrame()

    p_recent  = valid[-n_periods:]
    half      = max(2, len(p_recent) // 2)
    p_current = p_recent[-half:]
    p_prev    = p_recent[:half] if len(p_recent) >= 2 * half else p_recent[:-half]
    if not p_prev: p_prev = p_current

    def _rs_rgr(kode, pset):
        tbl_r = pdrb_data.get(kode, {}).get(tabel, {})
        ps, pe = pset[0], pset[-1]
        e_s = tbl_r.get("total", {}).get(ps)
        e_e = tbl_r.get("total", {}).get(pe)
        E_s = tbl_p["total"].get(ps)
        E_e = tbl_p["total"].get(pe)
        if not all([e_s, e_e, E_s, E_e]) or E_e == 0 or E_s == 0:
            return None, None
        RS  = e_e / E_e
        g_r = (e_e - e_s) / abs(e_s)
        g_p = (E_e - E_s) / abs(E_s)
        RGR = g_r / g_p if g_p != 0 else None
        return RS, RGR

    rows = []
    for kode in kode_list:
        if kode not in pdrb_data or tabel not in pdrb_data[kode]:
            continue
        RS, RGR     = _rs_rgr(kode, p_current)
        RS_p, RGR_p = _rs_rgr(kode, p_prev)
        if RS is not None and RGR is not None:
            rows.append({"kode": kode, "RS": RS, "RGR": RGR,
                         "RS_prev": RS_p or RS, "RGR_prev": RGR_p or RGR})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("kode")


# ─────────────────────────────────────────────────────────────────────
# RRG TRAIL – multi-titik per sektor (RS-Ratio × 100, RS-Momentum × 100)
# ─────────────────────────────────────────────────────────────────────

def compute_rrg_trail(pdrb_data, kode_region, kode_prov="3300",
                      tabel="adhk", n_periods=12):
    """
    Hitung trail RRG: untuk setiap sektor, hasilkan deret titik (RS, RGR)
    yang mencerminkan pergerakan posisi dari periode ke periode.

    RS  = (share sektor di wilayah / share sektor di provinsi) × 100
          → 100 = sama dengan provinsi
    RGR = RS(t) / RS(t-1) × 100  (momentum RS)
          → 100 = tidak bergerak

    Kuadran (pusat = 100):
      RS≥100 & RGR≥100 → LEADING    (kuat & menguat)
      RS≥100 & RGR<100 → WEAKENING  (kuat, melemah)
      RS<100 & RGR≥100 → IMPROVING  (lemah, membaik)
      RS<100 & RGR<100 → LAGGING    (lemah & melemah)

    Returns
    -------
    dict  { kode_sektor: { 'name', 'parent', 'trail': [{'period','RS','RGR'}, ...] } }
    Trail diurutkan dari periode tertua ke terbaru.
    """
    if kode_region not in pdrb_data or kode_prov not in pdrb_data:
        return {}
    if tabel not in pdrb_data[kode_region] or tabel not in pdrb_data[kode_prov]:
        return {}

    tbl_r = pdrb_data[kode_region][tabel]
    tbl_p = pdrb_data[kode_prov][tabel]

    # Periode valid (ada di kedua wilayah & total > 0)
    perds_r = set(tbl_r.get("periods", []))
    perds_p = set(tbl_p.get("periods", []))
    common  = sorted(perds_r & perds_p)
    if len(common) < 4:
        return {}

    use_perds = common[-n_periods:] if len(common) >= n_periods else common

    result = {}
    for kode_s, meta in tbl_r["sectors"].items():
        prov_meta = tbl_p["sectors"].get(kode_s, {})
        if not prov_meta:
            continue

        # Hitung RS-Ratio (×100) untuk setiap periode
        rs_series: list[tuple] = []   # list of (period, RS_index)
        for p in use_perds:
            r_val  = meta["values"].get(p)
            r_tot  = tbl_r["total"].get(p)
            pv_val = prov_meta.get("values", {}).get(p)
            p_tot  = tbl_p["total"].get(p)
            if not all([r_val, r_tot, pv_val, p_tot]):
                continue
            if r_tot == 0 or p_tot == 0 or pv_val == 0:
                continue
            rs_idx = (r_val / r_tot) / (pv_val / p_tot) * 100
            rs_series.append((p, rs_idx))

        if len(rs_series) < 3:
            continue

        # Hitung RS-Momentum (×100) = RS(t)/RS(t-1)*100
        trail = []
        for i in range(1, len(rs_series)):
            p_cur, rs_cur = rs_series[i]
            _, rs_prv     = rs_series[i - 1]
            rgr = (rs_cur / rs_prv * 100) if rs_prv != 0 else 100.0
            trail.append({"period": p_cur, "RS": round(rs_cur, 3),
                          "RGR": round(rgr, 3)})

        if len(trail) >= 2:
            result[kode_s] = {
                "name":   meta["name"],
                "parent": meta["parent"],
                "trail":  trail,
            }

    return result


def compute_rrg_trail_regional(pdrb_data, kode_list, kode_prov="3300",
                                tabel="adhk", n_periods=12):
    """
    Versi regional: trail untuk setiap kab/kota berdasarkan total PDRB.
    RS  = share PDRB kab/total provinsi × 100 (diindeks ke rata-rata)
    RGR = RS(t)/RS(t-1) × 100
    """
    if kode_prov not in pdrb_data:
        return {}
    tbl_p = pdrb_data[kode_prov][tabel]
    perds_p = sorted(tbl_p.get("periods", []))
    if len(perds_p) < 4:
        return {}

    use_perds = perds_p[-n_periods:] if len(perds_p) >= n_periods else perds_p

    result = {}
    for kode in kode_list:
        if kode not in pdrb_data or tabel not in pdrb_data[kode]:
            continue
        tbl_r = pdrb_data[kode][tabel]

        rs_series = []
        for p in use_perds:
            r_tot = tbl_r.get("total", {}).get(p)
            p_tot = tbl_p["total"].get(p)
            if not (r_tot and p_tot and p_tot != 0):
                continue
            rs_idx = (r_tot / p_tot) * 100
            rs_series.append((p, rs_idx))

        if len(rs_series) < 3:
            continue

        trail = []
        for i in range(1, len(rs_series)):
            p_cur, rs_cur = rs_series[i]
            _, rs_prv     = rs_series[i - 1]
            rgr = (rs_cur / rs_prv * 100) if rs_prv != 0 else 100.0
            trail.append({"period": p_cur, "RS": round(rs_cur, 3),
                          "RGR": round(rgr, 3)})

        if len(trail) >= 2:
            result[kode] = {"trail": trail}

    return result


# ─────────────────────────────────────────────────────────────────────
# PDRB PER KAPITA
# ─────────────────────────────────────────────────────────────────────

def compute_pdrb_perkapita(pdrb_data, penduduk_data, kode_list, tabel="adhb"):
    records = {}
    for kode in kode_list:
        if kode not in pdrb_data or tabel not in pdrb_data[kode]:
            continue
        total_pdrb = pdrb_data[kode][tabel]["total"]
        penduduk   = penduduk_data.get(kode, {})
        row = {}
        for period, pdrb_val in total_pdrb.items():
            pop = penduduk.get(period)
            if pdrb_val and pop and pop > 0:
                row[period] = (pdrb_val * 1_000_000) / (pop * 1_000) / 1_000_000
            else:
                row[period] = None
        records[kode] = row
    return pd.DataFrame(records).T


# ─────────────────────────────────────────────────────────────────────
# WILLIAMSON INDEX
# ─────────────────────────────────────────────────────────────────────

def compute_williamson(pdrb_data, penduduk_data, kode_list, period,
                       tabel="adhb", kode_prov="3300"):
    pdrb_pc = compute_pdrb_perkapita(pdrb_data, penduduk_data, kode_list, tabel)
    if pdrb_pc.empty:
        return None
    yi_list, fi_list = [], []
    for kode in kode_list:
        if kode not in pdrb_pc.index or period not in pdrb_pc.columns:
            continue
        yi = pdrb_pc.loc[kode, period]
        fi = penduduk_data.get(kode, {}).get(period)
        if yi is not None and fi is not None and not np.isnan(float(yi)):
            yi_list.append(float(yi))
            fi_list.append(float(fi))
    if len(yi_list) < 2:
        return None
    n = sum(fi_list)
    if n == 0:
        return None
    y_bar = sum(y * f for y, f in zip(yi_list, fi_list)) / n
    if y_bar == 0:
        return None
    wv = sum(((yi - y_bar) ** 2) * (fi / n) for yi, fi in zip(yi_list, fi_list))
    return round(float(np.sqrt(wv) / y_bar), 4)


def compute_williamson_timeseries(pdrb_data, penduduk_data, kode_list,
                                  periods=None, tabel="adhb", kode_prov="3300"):
    pdrb_pc = compute_pdrb_perkapita(pdrb_data, penduduk_data, kode_list, tabel)
    if pdrb_pc.empty:
        return {}
    iter_periods = periods if periods is not None else list(pdrb_pc.columns)
    result = {}
    for period in iter_periods:
        result[period] = compute_williamson(pdrb_data, penduduk_data, kode_list,
                                            period, tabel, kode_prov)
    return result


# ─────────────────────────────────────────────────────────────────────
# KLASSEN TYPOLOGY
# ─────────────────────────────────────────────────────────────────────

def _prov_pdrb_pc(pdrb_data, penduduk_data, kode_list, period, tabel, kode_prov):
    """Hitung PDRB per kapita provinsi dari agregat kab/kota."""
    prov_pdrb = pdrb_data.get(kode_prov, {}).get(tabel, {}).get("total", {}).get(period)
    all_kab   = [k for k in penduduk_data if k != kode_prov]
    total_pop = sum(penduduk_data[k].get(period, 0) or 0 for k in all_kab)
    if prov_pdrb and total_pop > 0:
        return (prov_pdrb * 1_000_000) / (total_pop * 1_000) / 1_000_000
    return None


def compute_klassen(pdrb_data, penduduk_data, kode_list,
                    period_start, period_end, tabel="adhb", kode_prov="3300"):
    pdrb_pc = compute_pdrb_perkapita(pdrb_data, penduduk_data, kode_list, tabel)

    # Jika period_start tidak punya data penduduk, gunakan periode valid pertama
    prov_pc_start = _prov_pdrb_pc(pdrb_data, penduduk_data, kode_list,
                                   period_start, tabel, kode_prov)
    prov_pc_end   = _prov_pdrb_pc(pdrb_data, penduduk_data, kode_list,
                                   period_end, tabel, kode_prov)

    # Fallback: cari periode awal yang punya data penduduk
    if not prov_pc_start and not pdrb_pc.empty:
        for col in sorted(pdrb_pc.columns):
            v = _prov_pdrb_pc(pdrb_data, penduduk_data, kode_list, col, tabel, kode_prov)
            if v:
                prov_pc_start = v
                period_start  = col
                break
    if not prov_pc_start or not prov_pc_end:
        return pd.DataFrame()

    g_prov = (prov_pc_end - prov_pc_start) / abs(prov_pc_start) * 100
    y_prov = prov_pc_end

    records = []
    for kode in kode_list:
        if kode not in pdrb_pc.index:
            continue
        yi_s = pdrb_pc.loc[kode, period_start] if period_start in pdrb_pc.columns else None
        yi_e = pdrb_pc.loc[kode, period_end]   if period_end   in pdrb_pc.columns else None
        try:
            ys = float(yi_s)
            ye = float(yi_e)
        except (TypeError, ValueError):
            continue
        if np.isnan(ys) or np.isnan(ye) or ys == 0:
            continue
        gi = (ye - ys) / abs(ys) * 100
        yi = ye
        if   gi >= g_prov and yi >= y_prov: kuadran, label = "I",   "Maju & Tumbuh Pesat"
        elif gi <  g_prov and yi >= y_prov: kuadran, label = "II",  "Maju tapi Tertekan"
        elif gi >= g_prov and yi <  y_prov: kuadran, label = "III", "Berkembang Cepat"
        else:                               kuadran, label = "IV",  "Relatif Tertinggal"
        records.append({"kode": kode, "pdrb_pc": round(yi, 4),
                        "pertumbuhan_%": round(gi, 2),
                        "kuadran": kuadran, "tipologi": label,
                        "period_ref": period_end})
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).set_index("kode")


# ─────────────────────────────────────────────────────────────────────
# THEIL INDEX
# ─────────────────────────────────────────────────────────────────────

def compute_theil(pdrb_data, penduduk_data, kode_list, period, tabel="adhb"):
    pdrb_pc = compute_pdrb_perkapita(pdrb_data, penduduk_data, kode_list, tabel)
    if pdrb_pc.empty or period not in pdrb_pc.columns:
        return None
    vals = [float(pdrb_pc.loc[k, period]) for k in kode_list
            if k in pdrb_pc.index and pdrb_pc.loc[k, period] is not None
            and not np.isnan(float(pdrb_pc.loc[k, period]))]
    if len(vals) < 2:
        return None
    vals = np.array(vals)
    Y_bar = np.mean(vals)
    n = len(vals)
    if Y_bar == 0:
        return None
    T = sum((yi / Y_bar) * np.log((yi / Y_bar) / (1 / n)) for yi in vals if yi > 0)
    return round(float(T / n), 6)


def compute_theil_timeseries(pdrb_data, penduduk_data, kode_list, tabel="adhb"):
    pdrb_pc = compute_pdrb_perkapita(pdrb_data, penduduk_data, kode_list, tabel)
    if pdrb_pc.empty:
        return {}
    return {p: compute_theil(pdrb_data, penduduk_data, kode_list, p, tabel)
            for p in pdrb_pc.columns}


# ─────────────────────────────────────────────────────────────────────
# KEMIRIPAN STRUKTUR EKONOMI
# ─────────────────────────────────────────────────────────────────────

def compute_struktur_kemiripan(pdrb_data, kode_list, period, tabel="adhb", method="krugman"):
    """
    Hitung indeks kemiripan struktur ekonomi antar wilayah.
    method='krugman' : Krugman Specialisation Index  (0=identik, 2=sangat berbeda)
    method='cosine'  : Cosine distance                (0=identik, 1=sangat berbeda)
    Returns: DataFrame (n x n) simetris dengan nilai jarak.
    """
    def _shares(kode):
        tbl = pdrb_data.get(kode, {}).get(tabel, {})
        scts = tbl.get("sectors", {})
        total = tbl.get("total", {}).get(period)
        if not total or total == 0:
            return None
        vec = {}
        for ks, meta in scts.items():
            v = meta.get("values", {}).get(period)
            if v is not None:
                vec[ks] = float(v) / float(total)
        return vec

    shares = {k: _shares(k) for k in kode_list}
    # Hapus yang None
    shares = {k: v for k, v in shares.items() if v}

    codes = list(shares.keys())
    n = len(codes)
    if n < 2:
        return pd.DataFrame()

    # Semua sektor gabungan
    all_sectors = sorted(set(s for v in shares.values() for s in v))

    import numpy as _np
    mat = _np.zeros((n, n))
    for i, ci in enumerate(codes):
        vi = _np.array([shares[ci].get(s, 0.0) for s in all_sectors])
        for j, cj in enumerate(codes):
            if i == j:
                mat[i, j] = 0.0
                continue
            vj = _np.array([shares[cj].get(s, 0.0) for s in all_sectors])
            if method == "krugman":
                mat[i, j] = float(_np.sum(_np.abs(vi - vj)))
            else:  # cosine distance
                denom = (_np.linalg.norm(vi) * _np.linalg.norm(vj))
                if denom == 0:
                    mat[i, j] = 1.0
                else:
                    sim = float(_np.dot(vi, vj) / denom)
                    mat[i, j] = round(1.0 - min(max(sim, -1.0), 1.0), 6)

    return pd.DataFrame(mat, index=codes, columns=codes)


# ─────────────────────────────────────────────────────────────────────
# PROYEKSI PDRB
# ─────────────────────────────────────────────────────────────────────

def _next_quarter(period: str) -> str:
    """Hasilkan label triwulan berikutnya dari format 'YYYYQq'."""
    year, q = int(period[:4]), int(period[5])
    if q < 4:
        return f"{year}Q{q+1}"
    return f"{year+1}Q1"


def project_pdrb(pdrb_data, kode, tabel, sector_key,
                 method="trend", n_forecast=8, n_hist=None):
    """
    Proyeksikan nilai PDRB satu sektor/total untuk satu wilayah.

    Parameters
    ----------
    pdrb_data   : dict hasil load_all_data()
    kode        : kode wilayah (str)
    tabel       : 'adhb' | 'adhk'
    sector_key  : kode sektor, atau '__total__' untuk PDRB total
    method      : 'trend' | 'moving_average' | 'avg_growth' | 'exponential'
    n_forecast  : jumlah triwulan ke depan yang diproyeksikan
    n_hist      : jumlah data historis yang dipakai (None = semua)

    Returns
    -------
    dict dengan kunci:
      periods_hist, values_hist, periods_fcst, values_fcst, r2 (optional)
    None jika data tidak cukup.
    """
    try:
        tbl = pdrb_data[kode][tabel]
    except KeyError:
        return None

    all_periods = tbl.get("periods", [])

    # Ambil nilai historis
    if sector_key == "__total__":
        raw = [(p, tbl["total"].get(p)) for p in all_periods]
    else:
        sec_meta = tbl.get("sectors", {}).get(sector_key)
        if sec_meta is None:
            return None
        raw = [(p, sec_meta["values"].get(p)) for p in all_periods]

    # Filter hanya yang ada nilainya
    raw = [(p, float(v)) for p, v in raw if v is not None]
    if len(raw) < 4:
        return None

    # Batasi historis
    if n_hist and n_hist < len(raw):
        raw = raw[-n_hist:]

    periods_hist = [r[0] for r in raw]
    values_hist  = [r[1] for r in raw]
    n = len(values_hist)

    # ── Generate label periode proyeksi ──
    last_p = periods_hist[-1]
    periods_fcst = []
    cur = last_p
    for _ in range(n_forecast):
        cur = _next_quarter(cur)
        periods_fcst.append(cur)

    result = {
        "periods_hist": periods_hist,
        "values_hist":  values_hist,
        "periods_fcst": periods_fcst,
        "values_fcst":  [],
        "r2":           None,
    }

    import numpy as _np

    # ── Metode proyeksi ──
    if method == "trend":
        x = _np.arange(n, dtype=float)
        y = _np.array(values_hist, dtype=float)
        coeffs = _np.polyfit(x, y, 1)
        slope, intercept = coeffs
        # R²
        y_pred = _np.polyval(coeffs, x)
        ss_res = _np.sum((y - y_pred) ** 2)
        ss_tot = _np.sum((y - _np.mean(y)) ** 2)
        result["r2"] = float(1 - ss_res / ss_tot) if ss_tot > 0 else None
        for i in range(n_forecast):
            result["values_fcst"].append(
                max(0.0, float(intercept + slope * (n + i)))
            )

    elif method == "moving_average":
        window = min(4, n)
        last_ma = float(_np.mean(values_hist[-window:]))
        # Hitung rata-rata perubahan dalam window terakhir
        diffs = _np.diff(values_hist[-window:])
        avg_diff = float(_np.mean(diffs)) if len(diffs) > 0 else 0.0
        prev = last_ma
        for i in range(n_forecast):
            nxt = max(0.0, prev + avg_diff)
            result["values_fcst"].append(nxt)
            prev = nxt

    elif method == "avg_growth":
        # Rata-rata laju pertumbuhan q-to-q (%)
        growths = []
        for i in range(1, n):
            if values_hist[i-1] and values_hist[i-1] != 0:
                growths.append(values_hist[i] / values_hist[i-1])
        if not growths:
            return None
        avg_g = float(_np.mean(growths))
        prev = values_hist[-1]
        for _ in range(n_forecast):
            nxt = max(0.0, prev * avg_g)
            result["values_fcst"].append(nxt)
            prev = nxt

    elif method == "exponential":
        # Holt's Double Exponential Smoothing
        alpha, beta = 0.3, 0.1
        level = float(values_hist[0])
        trend_v = float(values_hist[1] - values_hist[0]) if n > 1 else 0.0
        for v in values_hist[1:]:
            prev_l = level
            level   = alpha * v + (1 - alpha) * (level + trend_v)
            trend_v = beta * (level - prev_l) + (1 - beta) * trend_v
        for i in range(1, n_forecast + 1):
            result["values_fcst"].append(max(0.0, level + i * trend_v))

    else:
        return None

    return result
