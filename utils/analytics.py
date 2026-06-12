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


# ══════════════════════════════════════════════════════════════════════════════
# ANALISIS LANJUTAN — TAMBAHAN
# ══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# 1. KONVERGENSI / DIVERGENSI (Beta & Sigma Convergence)
# ─────────────────────────────────────────────────────────────────────────────

def compute_convergence(pdrb_data, penduduk_data, kode_list, periods=None, tabel="adhb"):
    """
    Hitung konvergensi/divergensi PDRB per kapita antar wilayah.

    Returns dict:
      sigma  : [{'period': p, 'sigma': nilai}, ...]   — std dev ln(PDRB/kap)
      beta   : {'beta': koef, 'r2': r2, 'converging': bool, 'data': [...]}
      pdrb_pc: { kode: { period: nilai } }
    """
    import math

    kab_list = [k for k in kode_list if k != "3300"]
    if len(kab_list) < 3:
        return None

    if periods is None:
        periods = sorted(pdrb_data.get("3300", {}).get(tabel, {}).get("periods", []))

    # Hitung PDRB per kapita per wilayah per periode
    pdrb_pc = {}
    for kode in kab_list:
        pdrb_pc[kode] = {}
        for p in periods:
            pdrb_val = pdrb_data.get(kode, {}).get(tabel, {}).get("total", {}).get(p)
            pop_val  = penduduk_data.get(kode, {}).get(p)
            if pdrb_val and pop_val and pop_val > 0:
                pdrb_pc[kode][p] = pdrb_val / pop_val

    # Sigma Convergence: std dev ln(PDRB/kap) tiap periode
    sigma_series = []
    for p in periods:
        vals = [math.log(pdrb_pc[k][p]) for k in kab_list
                if p in pdrb_pc.get(k, {}) and pdrb_pc[k][p] > 0]
        if len(vals) >= 3:
            mean_v = sum(vals) / len(vals)
            std_v  = math.sqrt(sum((v - mean_v)**2 for v in vals) / len(vals))
            sigma_series.append({"period": p, "sigma": round(std_v, 6)})

    # Beta Convergence: reg pertumbuhan PDRB/kap ~ awal PDRB/kap
    # Gunakan periode pertama & terakhir yang valid
    valid_perds = [s["period"] for s in sigma_series]
    beta_result = None
    if len(valid_perds) >= 8:
        p_awal  = valid_perds[0]
        p_akhir = valid_perds[-1]
        n_yr    = max(1, len(valid_perds) / 4)   # konversi ke tahun

        xy = []
        for kode in kab_list:
            y0 = pdrb_pc.get(kode, {}).get(p_awal)
            y1 = pdrb_pc.get(kode, {}).get(p_akhir)
            if y0 and y1 and y0 > 0 and y1 > 0:
                ln_y0   = math.log(y0)
                growth  = (math.log(y1) - math.log(y0)) / n_yr
                xy.append((ln_y0, growth, kode))

        if len(xy) >= 4:
            xs  = [r[0] for r in xy]
            ys  = [r[1] for r in xy]
            n   = len(xs)
            mx  = sum(xs) / n
            my  = sum(ys) / n
            ss  = sum((x - mx)**2 for x in xs)
            sp  = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
            beta_coef = sp / ss if ss != 0 else 0
            intercept = my - beta_coef * mx
            y_pred    = [beta_coef * x + intercept for x in xs]
            ss_res    = sum((ys[i] - y_pred[i])**2 for i in range(n))
            ss_tot    = sum((y - my)**2 for y in ys)
            r2        = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            beta_result = {
                "beta":       round(beta_coef, 6),
                "intercept":  round(intercept, 6),
                "r2":         round(r2, 4),
                "converging": beta_coef < 0,
                "p_awal":     p_awal,
                "p_akhir":    p_akhir,
                "data": [{"kode": r[2],
                          "ln_y0": round(r[0], 4),
                          "growth": round(r[1]*100, 4)} for r in xy],
            }

    return {"sigma": sigma_series, "beta": beta_result, "pdrb_pc": pdrb_pc}


# ─────────────────────────────────────────────────────────────────────────────
# 2. INDEKS HERFINDAHL-HIRSCHMAN (HHI) — Diversifikasi Ekonomi
# ─────────────────────────────────────────────────────────────────────────────

def compute_hhi(pdrb_data, kode, tabel="adhb", periods=None):
    """
    Hitung HHI (Herfindahl-Hirschman Index) untuk satu wilayah per periode.
    HHI = Σ(si²) di mana si = share sektor i terhadap total PDRB.
    HHI mendekati 0 = sangat terdiversifikasi; mendekati 1 = sangat terkonsentrasi.

    Returns: [{'period': p, 'hhi': nilai, 'n_sectors': n}, ...]
    """
    scts = pdrb_data.get(kode, {}).get(tabel, {}).get("sectors", {})
    main_scts = {k: v for k, v in scts.items() if v.get("parent") is None}

    if periods is None:
        periods = sorted(pdrb_data.get(kode, {}).get(tabel, {}).get("periods", []))

    result = []
    for p in periods:
        vals = [v["values"].get(p, 0) or 0 for v in main_scts.values()]
        total = sum(vals)
        if total <= 0:
            continue
        shares = [v / total for v in vals]
        hhi    = sum(s**2 for s in shares)
        result.append({
            "period":    p,
            "hhi":       round(hhi, 6),
            "hhi_norm":  round((hhi - 1/len(shares)) / (1 - 1/len(shares)), 4)
                         if len(shares) > 1 else 0,
            "n_sectors": len([v for v in vals if v > 0]),
        })
    return result


def compute_hhi_regional(pdrb_data, kode_list, tabel="adhb", periods=None):
    """
    Hitung HHI untuk beberapa wilayah, kembalikan dict { kode: [hhi_series] }.
    """
    return {kode: compute_hhi(pdrb_data, kode, tabel, periods) for kode in kode_list}


# ─────────────────────────────────────────────────────────────────────────────
# 3. OVERLAY SEKTOR PRIORITAS (LQ + Shift Share + RRG)
# ─────────────────────────────────────────────────────────────────────────────

def compute_sector_priority(pdrb_data, kode, tabel="adhb", periods=None,
                            ref_kode="3300"):
    """
    Overlay tiga analisis: LQ, Shift Share (Competitive Effect), dan RRG quadrant.
    Menghasilkan matriks prioritas sektor.

    Returns: list of dict per sektor utama:
      { kode_skt, nama, lq, ce (competitive effect SS), rrg_quad,
        priority_score, priority_label }
    """
    if periods is None:
        periods = sorted(pdrb_data.get(kode, {}).get(tabel, {}).get("periods", []))
    if not periods:
        return []

    last_p  = periods[-1]
    # Pilih periode awal untuk SS (4 tahun lalu / 16 periode)
    n_back  = min(16, len(periods) - 1)
    first_p = periods[-n_back - 1] if n_back > 0 else periods[0]

    scts_r   = pdrb_data.get(kode,     {}).get(tabel, {}).get("sectors", {})
    scts_ref = pdrb_data.get(ref_kode, {}).get(tabel, {}).get("sectors", {})
    main_scts = {k: v for k, v in scts_r.items() if v.get("parent") is None}

    # ── LQ (periode terakhir) ──────────────────────────────────────────────
    total_r   = sum((v["values"].get(last_p) or 0) for v in main_scts.values())
    total_ref = sum((pdrb_data.get(ref_kode, {}).get(tabel, {})
                     .get("total", {}).get(last_p, 0) or 0) for _ in [1])
    total_ref = pdrb_data.get(ref_kode, {}).get(tabel, {}).get("total", {}).get(last_p) or 0

    lq_vals = {}
    for ks, sv in main_scts.items():
        vi_r   = sv["values"].get(last_p) or 0
        vi_ref = (scts_ref.get(ks, {}).get("values", {}).get(last_p) or 0)
        vref_t = total_ref
        vr_t   = total_r
        if vr_t > 0 and vref_t > 0 and vi_ref > 0:
            lq_vals[ks] = round((vi_r / vr_t) / (vi_ref / vref_t), 4)
        else:
            lq_vals[ks] = None

    # ── Shift Share — Competitive Effect ──────────────────────────────────
    ce_vals = {}
    for ks, sv in main_scts.items():
        v0_r   = sv["values"].get(first_p) or 0
        v1_r   = sv["values"].get(last_p)  or 0
        v0_ref = (scts_ref.get(ks, {}).get("values", {}).get(first_p) or 0)
        v1_ref = (scts_ref.get(ks, {}).get("values", {}).get(last_p)  or 0)
        if v0_r > 0 and v0_ref > 0:
            gr_ref = (v1_ref - v0_ref) / v0_ref if v0_ref > 0 else 0
            ce_vals[ks] = round((v1_r - v0_r) - v0_r * gr_ref, 2)
        else:
            ce_vals[ks] = None

    # ── RRG Quadrant (periode terakhir vs sebelumnya) ─────────────────────
    rrg_data = compute_rrg_trail(pdrb_data, kode, kode_prov=ref_kode,
                                  tabel=tabel, n_periods=8)
    rrg_quad = {}
    for ks, rd in rrg_data.items():
        trail = rd.get("trail", [])
        if trail:
            latest = trail[-1]
            rs  = latest.get("RS",  100)
            rgr = latest.get("RGR", 100)
            if rs >= 100 and rgr >= 100:
                rrg_quad[ks] = "Leading"
            elif rs >= 100 and rgr < 100:
                rrg_quad[ks] = "Weakening"
            elif rs < 100 and rgr >= 100:
                rrg_quad[ks] = "Improving"
            else:
                rrg_quad[ks] = "Lagging"
        else:
            rrg_quad[ks] = "N/A"

    # ── Priority Score ─────────────────────────────────────────────────────
    QUAD_SCORE = {"Leading": 3, "Improving": 2, "Weakening": 1, "Lagging": 0, "N/A": 0}
    result = []
    for ks, sv in main_scts.items():
        lq  = lq_vals.get(ks)
        ce  = ce_vals.get(ks)
        qd  = rrg_quad.get(ks, "N/A")

        score = 0
        if lq is not None and lq >= 1:  score += 2
        if ce is not None and ce > 0:   score += 2
        score += QUAD_SCORE.get(qd, 0)

        if score >= 6:    label = "⭐ Unggulan Utama"
        elif score >= 4:  label = "✅ Potensial"
        elif score >= 2:  label = "⚠️ Perlu Perhatian"
        else:             label = "🔻 Tertinggal"

        result.append({
            "kode_skt":       ks,
            "nama":           sv.get("name", ks),
            "lq":             lq,
            "lq_status":      "Basis" if (lq or 0) >= 1 else "Non-Basis",
            "ce":             ce,
            "ce_status":      "Kompetitif" if (ce or 0) > 0 else "Tidak Kompetitif",
            "rrg_quad":       qd,
            "priority_score": score,
            "priority_label": label,
        })

    result.sort(key=lambda x: -x["priority_score"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. ANALISIS GRAVITASI EKONOMI
# ─────────────────────────────────────────────────────────────────────────────

def compute_gravity(pdrb_data, kode_list, periods=None, tabel="adhb"):
    """
    Model gravitasi ekonomi: Interaction_ij = k * (PDRB_i * PDRB_j) / Dist_ij²
    Menggunakan koordinat dari centroids_jateng.py.

    Returns: list of dict { wilayah_i, wilayah_j, pdrb_i, pdrb_j,
                             jarak_km, interaction, periode }
    """
    import math
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from data.centroids_jateng import CENTROIDS_JATENG as centroids
    except ImportError:
        return []

    if periods is None:
        periods = sorted(pdrb_data.get("3300", {}).get(tabel, {}).get("periods", []))
    if not periods:
        return []

    last_p = periods[-1]
    kab_list = [k for k in kode_list if k != "3300" and k in centroids]

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
            math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    rows = []
    for i in range(len(kab_list)):
        for j in range(i + 1, len(kab_list)):
            ki, kj = kab_list[i], kab_list[j]
            pi_val = pdrb_data.get(ki, {}).get(tabel, {}).get("total", {}).get(last_p)
            pj_val = pdrb_data.get(kj, {}).get(tabel, {}).get("total", {}).get(last_p)
            if not pi_val or not pj_val:
                continue
            lat_i, lon_i, _ = centroids[ki]
            lat_j, lon_j, _ = centroids[kj]
            dist = haversine(lat_i, lon_i, lat_j, lon_j)
            if dist < 1:
                dist = 1
            interaction = (pi_val * pj_val) / (dist ** 2)
            rows.append({
                "kode_i":      ki,
                "kode_j":      kj,
                "pdrb_i":      round(pi_val, 2),
                "pdrb_j":      round(pj_val, 2),
                "jarak_km":    round(dist, 1),
                "interaction": round(interaction, 2),
                "periode":     last_p,
            })

    rows.sort(key=lambda x: -x["interaction"])
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 5. ECONOMIC BASE MULTIPLIER
# ─────────────────────────────────────────────────────────────────────────────

def compute_base_multiplier(pdrb_data, kode, tabel="adhb", periods=None,
                             ref_kode="3300"):
    """
    Hitung Economic Base Multiplier dari LQ.
    Basic PDRB  = sektor dengan LQ >= 1 (ekspor ke luar wilayah)
    Non-basic   = sektor dengan LQ < 1
    Multiplier  = Total PDRB / Basic PDRB

    Returns: list of dict per periode:
      { period, total_pdrb, basic_pdrb, nonbasic_pdrb, multiplier,
        basic_sectors: [{ kode, nama, lq, nilai }] }
    """
    if periods is None:
        periods = sorted(pdrb_data.get(kode, {}).get(tabel, {}).get("periods", []))

    scts_r   = pdrb_data.get(kode,     {}).get(tabel, {}).get("sectors", {})
    scts_ref = pdrb_data.get(ref_kode, {}).get(tabel, {}).get("sectors", {})
    main_scts = {k: v for k, v in scts_r.items() if v.get("parent") is None}

    result = []
    for p in periods:
        total_r   = sum((v["values"].get(p) or 0) for v in main_scts.values())
        total_ref = pdrb_data.get(ref_kode, {}).get(tabel, {}).get("total", {}).get(p) or 0
        if total_r <= 0 or total_ref <= 0:
            continue

        basic_pdrb    = 0
        basic_sectors = []
        for ks, sv in main_scts.items():
            vi_r   = sv["values"].get(p) or 0
            vi_ref = scts_ref.get(ks, {}).get("values", {}).get(p) or 0
            if total_r > 0 and total_ref > 0 and vi_ref > 0:
                lq = (vi_r / total_r) / (vi_ref / total_ref)
                if lq >= 1.0 and vi_r > 0:
                    # Basic PDRB = bagian yang "diekspor" (melebihi kebutuhan lokal)
                    basic_part = vi_r * (1 - 1/lq)
                    basic_pdrb += basic_part
                    basic_sectors.append({
                        "kode": ks,
                        "nama": sv.get("name", ks),
                        "lq":   round(lq, 4),
                        "nilai_basic": round(basic_part, 2),
                    })

        if basic_pdrb > 0:
            multiplier = total_r / basic_pdrb
            result.append({
                "period":       p,
                "total_pdrb":   round(total_r, 2),
                "basic_pdrb":   round(basic_pdrb, 2),
                "nonbasic_pdrb":round(total_r - basic_pdrb, 2),
                "multiplier":   round(multiplier, 4),
                "basic_sectors": sorted(basic_sectors, key=lambda x: -x["lq"]),
            })

    return result


# ─────────────────────────────────────────────────────────────────────
# OUTPUT GAP  (HP Filter, λ = 1600 untuk data triwulanan)
# ─────────────────────────────────────────────────────────────────────

def compute_output_gap(pdrb_data, kode, tabel="adhk", periods=None):
    """
    Hitung output gap satu wilayah menggunakan HP Filter.

    Output gap (%) = (PDRB_aktual - PDRB_potensial) / PDRB_potensial × 100

    Returns
    -------
    list of dict:
        period, actual, potential, gap_abs, gap_pct
    Atau dict {"error": ...} bila data tidak cukup.
    """
    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter
    except ImportError:
        return {"error": "statsmodels tidak terinstal"}

    if kode not in pdrb_data:
        return {"error": f"Kode {kode} tidak ditemukan"}

    tbl = pdrb_data[kode].get(tabel, {})
    if not tbl:
        return {"error": f"Tabel {tabel} tidak tersedia untuk {kode}"}

    all_periods = tbl.get("periods", [])
    total_vals  = tbl.get("total", {})

    if periods:
        use_periods = [p for p in all_periods if p in periods]
    else:
        use_periods = list(all_periods)

    # Ambil nilai total PDRB — harus berurutan & tanpa NaN
    series = []
    valid_periods = []
    for p in use_periods:
        v = total_vals.get(p)
        if v is not None and v > 0:
            series.append(float(v))
            valid_periods.append(p)

    if len(series) < 8:
        return {"error": "Data terlalu sedikit untuk HP Filter (minimal 8 periode)"}

    series_arr = np.array(series)

    # HP Filter  λ=1600 standar triwulanan
    cycle, trend = hpfilter(series_arr, lamb=1600)

    result = []
    for i, p in enumerate(valid_periods):
        actual    = series_arr[i]
        potential = trend[i]
        gap_abs   = actual - potential
        gap_pct   = (gap_abs / potential * 100) if potential != 0 else 0.0
        result.append({
            "period":    p,
            "actual":    round(actual, 2),
            "potential": round(potential, 2),
            "gap_abs":   round(gap_abs, 2),
            "gap_pct":   round(gap_pct, 4),
        })

    return result


def compute_output_gap_regional(pdrb_data, kode_list, tabel="adhk", periods=None):
    """
    Hitung output gap untuk banyak wilayah sekaligus.

    Returns
    -------
    dict  {kode: list_of_dict | {"error": ...}}
    """
    result = {}
    for kode in kode_list:
        result[kode] = compute_output_gap(pdrb_data, kode, tabel=tabel, periods=periods)
    return result
