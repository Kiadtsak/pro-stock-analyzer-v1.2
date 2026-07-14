# valuation_analysis.py
from __future__ import annotations

import os
import json
import math
import pandas as pd
from typing import Dict, List, Any, Optional

# -------------------------
# Config / Defaults
# -------------------------
EXPORT_JSON_DEFAULT = "expotes/result.json"
VALUATION_JSON = "expotes/valuation.json"
VALUATION_CSV  = "expotes/valuation.csv"

# terminal growth ตามหมวดอุตสาหกรรม (ปรับได้)
TERMINAL_G_BY_SECTOR = {
    "Technology": 0.03,
    "Information Technology": 0.03,
    "Financials": 0.025,
    "Finance": 0.025,
    "Real Estate": 0.02,
    "REIT": 0.02,
    "Other": 0.025,
}

# mapping symbol -> sector (ใช้เฉพาะกรณีไม่มี Sector ในไฟล์)
SYMBOL_SECTOR_FALLBACK = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "AMD": "Technology", "GOOGL": "Technology",
    "KBANK": "Financials", "SCB": "Financials", "BBL": "Financials",
    "CPN": "Real Estate", "LH": "Real Estate", "QH": "Real Estate",
}


# -------------------------
# Utilities
# -------------------------
def _safe_last(series: pd.Series) -> Optional[float]:
    if series is None or series.empty:
        return None
    try:
        return float(series.dropna().iloc[-1])
    except Exception:
        return None


def _infer_sector(symbol: str, df_symbol: pd.DataFrame) -> str:
    # 1) ถ้ามีคอลัมน์ Sector ใช้อันนั้น
    if "Sector" in df_symbol.columns and df_symbol["Sector"].notna().any():
        sector = str(df_symbol["Sector"].dropna().iloc[-1])
        return sector

    # 2) ถ้าไม่มี ใช้ fallback mapping
    return SYMBOL_SECTOR_FALLBACK.get(symbol.upper(), "Other")


def _terminal_growth_for_sector(sector: str) -> float:
    for key, g in TERMINAL_G_BY_SECTOR.items():
        if key.lower() in sector.lower():
            return g
    return TERMINAL_G_BY_SECTOR["Other"]


def _avg_growth(series: pd.Series, lookback: int = 5) -> Optional[float]:
    """คำนวณค่าเฉลี่ย YoY growth (เชิงเส้น) ของ series ย้อนหลัง N ปี"""
    s = series.dropna().sort_index()
    if len(s) < 2:
        return None
    s = s.tail(lookback + 1)  # ใช้ข้อมูลล่าสุด N+1 จุด
    yoy = s.pct_change().dropna()
    if yoy.empty:
        return None
    return float(yoy.mean())


def _clip_growth(g: float, lo: float = -0.3, hi: float = 0.25) -> float:
    """กัน growth สุดโต่ง เพื่อความอนุรักษ์นิยม"""
    return max(lo, min(hi, g))


# -------------------------
# Core: YoY Growth + DCF
# -------------------------
def compute_growth_table(df_symbol: pd.DataFrame) -> pd.DataFrame:
    """
    คืนตาราง YoY Growth หลักๆ: Owner Earnings, Free Cash Flow (FCF), EPS (ถ้ามี)
    """
    cols = []
    if "Owner Earnings" in df_symbol.columns:
        cols.append("Owner Earnings")
    if "Free Cash Flow (FCF)" in df_symbol.columns:
        cols.append("Free Cash Flow (FCF)")
    if "EPS" in df_symbol.columns:
        cols.append("EPS")

    if not cols:
        # ไม่มีคอลัมน์หลักให้คำนวณ คืนตารางว่าง (แต่ไม่ error)
        return pd.DataFrame()

    df = df_symbol.sort_values("Year").copy()
    for c in cols:
        df[f"{c} YoY (%)"] = df[c].pct_change() * 100.0

    keep = ["Year"] + [f"{c} YoY (%)" for c in cols]
    return df[keep]


def dcf_buffett_style(
    df_symbol: pd.DataFrame,
    fcf_col: str = "Free Cash Flow (FCF)",
    wacc_col: str = "WACC",
    years: int = 10,
    fade_growth: bool = True,
    sector: Optional[str] = None,
) -> Dict[str, Any]:
    """
    DCF แบบอนุรักษ์นิยม:
    - ปี 1 ใช้ avg YoY FCF 3-5 ปีหลังสุด (clip ที่ 25%)
    - ค่อยๆ fade ไปสู่ terminal growth (ตาม sector) ณ ปีสุดท้าย
    - Discount ด้วย WACC ของงวดล่าสุด (ถ้าไม่มี ใช้ 10%)
    - คืน Intrinsic Equity Value (รวม terminal) และ per-share ถ้ารู้ shares
    """
    if fcf_col not in df_symbol.columns:
        raise ValueError(f"ไม่พบคอลัมน์ '{fcf_col}' ใน expotes/result.json")

    df_symbol = df_symbol.sort_values("Year").copy()
    fcf_last = _safe_last(df_symbol[fcf_col])
    if fcf_last is None:
        raise ValueError("ไม่พบ FCF ล่าสุด (เป็น NaN/ไม่มีข้อมูล)")

    wacc = _safe_last(df_symbol[wacc_col]) if (wacc_col in df_symbol.columns) else None
    if not wacc or not math.isfinite(wacc) or wacc <= 0:
        wacc = 0.10  # สมมติฐานสำรอง 10% หากไม่มี WACC

    # growth แรกเริ่มจากค่าเฉลี่ยย้อนหลัง (อนุรักษ์นิยมด้วยการ clip)
    g_avg = _avg_growth(df_symbol[fcf_col], lookback=5) or 0.08
    g_start = _clip_growth(g_avg, lo=-0.20, hi=0.25)

    # terminal growth ตาม sector
    g_term = _terminal_growth_for_sector(sector or "Other")

    # เตรียมเส้น growth 1..N
    growth_path: List[float] = []
    if fade_growth:
        for i in range(1, years + 1):
            # linear fade: จาก g_start → g_term
            w = i / years
            gi = (1 - w) * g_start + w * g_term
            growth_path.append(gi)
    else:
        growth_path = [g_start] * years

    # forecast & discount
    cf_forecast: List[float] = []
    pv_forecast: List[float] = []
    fcf = fcf_last
    for i, gi in enumerate(growth_path, start=1):
        fcf = fcf * (1 + gi)
        cf_forecast.append(fcf)
        pv = fcf / ((1 + wacc) ** i)
        pv_forecast.append(pv)

    # terminal value ณ ปี N
    fcf_N = cf_forecast[-1]
    tv = (fcf_N * (1 + g_term)) / (wacc - g_term)
    pv_tv = tv / ((1 + wacc) ** years)

    intrinsic_equity_value = float(sum(pv_forecast) + pv_tv)

    # ต่อหุ้น (ถ้ามี Shares Outstanding)
    shares = None
    per_share = None
    for cand in ["Shares Outstanding", "Shares Outstanding (Diluted)"]:
        if cand in df_symbol.columns:
            shares = _safe_last(df_symbol[cand])
            break

    if shares and shares > 0:
        per_share = intrinsic_equity_value / shares

    # สรุปผล
    return {
        "wacc_used": wacc,
        "g_start": g_start,
        "g_terminal": g_term,
        "years": years,
        "cashflows_forecast": cf_forecast,
        "pv_cashflows": pv_forecast,
        "pv_terminal_value": pv_tv,
        "intrinsic_equity_value": intrinsic_equity_value,
        "shares_outstanding": shares,
        "intrinsic_value_per_share": per_share,
    }


def run_valuation_for_symbol(
    symbol: str,
    export_json_path: str = EXPORT_JSON_DEFAULT
) -> Dict[str, Any]:
    """
    โหลด expotes/result.json → เลือกข้อมูลของ symbol →
    คำนวณอุตสาหกรรม, ตาราง YoY Growth, และ DCF (Buffett-style)
    → บันทึกผลลง expotes/valuation.json & .csv
    """
    if not os.path.exists(export_json_path):
        raise FileNotFoundError(f"ไม่พบไฟล์ผลลัพธ์ {export_json_path} (ต้อง export ratios ก่อน)")

    df = pd.read_json(export_json_path)
    if df.empty:
        raise ValueError("ไฟล์ result.json ว่างเปล่า")

    sym = symbol.upper()
    df_symbol = df[df["Stock Symbol"].str.upper() == sym].copy()
    if df_symbol.empty:
        raise ValueError(f"ไม่พบข้อมูลของ {sym} ใน {export_json_path}")

    # หา sector & terminal g
    sector = _infer_sector(sym, df_symbol)

    # ตารางการเติบโต (YoY)
    growth_df = compute_growth_table(df_symbol)

    # DCF
    dcf = dcf_buffett_style(df_symbol, sector=sector)

    # ทำ summary ต่อปี (% growth ของ Owner Earnings เป็นหลัก)
    summary_growth = growth_df.to_dict(orient="records") if not growth_df.empty else []

    result = {
        "symbol": sym,
        "sector": sector,
        "terminal_growth_used": dcf["g_terminal"],
        "wacc_used": dcf["wacc_used"],
        "intrinsic_equity_value": dcf["intrinsic_equity_value"],
        "intrinsic_value_per_share": dcf["intrinsic_value_per_share"],
        "shares_outstanding": dcf["shares_outstanding"],
        "growth_table": summary_growth,
        "cashflows_forecast": dcf["cashflows_forecast"],
        "pv_cashflows": dcf["pv_cashflows"],
        "pv_terminal_value": dcf["pv_terminal_value"],
    }

    # export ไฟล์รายงาน
    os.makedirs(os.path.dirname(VALUATION_JSON), exist_ok=True)
    with open(VALUATION_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # export CSV (เฉพาะส่วนสำคัญให้ดูเร็ว)
    slim = {
        "Stock Symbol": [sym],
        "Sector": [sector],
        "WACC Used": [dcf["wacc_used"]],
        "Terminal Growth Used": [dcf["g_terminal"]],
        "Intrinsic Equity Value": [dcf["intrinsic_equity_value"]],
        "Intrinsic Value / Share": [dcf["intrinsic_value_per_share"]],
        "Shares Outstanding": [dcf["shares_outstanding"]],
    }
    pd.DataFrame(slim).to_csv(VALUATION_CSV, index=False, encoding="utf-8")

    return result
