"""
feature_engineering.py — สร้างฟีเจอร์ระดับ production (~85 ตัว) ต่อ "หุ้น-ปี"
============================================================================

คำนวณจากงบ 3 ชนิด + ราคา/หุ้นรายปีโดยตรง (ไม่พึ่ง CashFlowModel เดิม เพื่อคุม
ฟีเจอร์ได้เต็มที่) แบ่งเป็น 10 หมวดตามหลัก Quant:

  1. Profitability   2. Growth + CAGR   3. Liquidity      4. Leverage
  5. Efficiency      6. Cash Flow Qual  7. Valuation       8. Quality (Piotroski/Altman)
  9. Buffett         10. Market (momentum รายปี)

หมายเหตุ: ฟีเจอร์ที่ต้องใช้ "ราคารายวัน" (Beta, Volatility, Sharpe, 52W) ไม่ได้ทำ
เพราะ data มีแค่ราคารายปี

ฟังก์ชันหลัก:
  engineer_symbol(symbol) -> ({year: {feature: value}}, [years_sorted])
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from .data_loader import load_statements

DAYS = 365.0


# ---------------------------------------------------------------- helpers
def _f(v: Any) -> Optional[float]:
    """แปลงเป็น float ปลอดภัย (None ถ้าใช้ไม่ได้)"""
    try:
        if v is None:
            return None
        x = float(v)
        return None if (math.isnan(x) or math.isinf(x)) else x
    except (TypeError, ValueError):
        return None


def _div(a: Any, b: Any) -> Optional[float]:
    a, b = _f(a), _f(b)
    if a is None or b is None or b == 0:
        return None
    r = a / b
    return None if (math.isnan(r) or math.isinf(r)) else r


def _cagr(end: Optional[float], start: Optional[float], n: int) -> Optional[float]:
    end, start = _f(end), _f(start)
    if end is None or start is None or start <= 0 or end <= 0 or n <= 0:
        return None
    return (end / start) ** (1.0 / n) - 1.0


def _growth(cur: Optional[float], prev: Optional[float]) -> Optional[float]:
    cur, prev = _f(cur), _f(prev)
    if cur is None or prev is None or prev == 0:
        return None
    return cur / abs(prev) - 1.0


def _std(vals: List[float]) -> Optional[float]:
    xs = [x for x in vals if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / len(xs)) ** 0.5


def _slope(vals: List[Optional[float]]) -> Optional[float]:
    """ความชันของเส้นถดถอย (แนวโน้ม) ของค่าที่มี"""
    pts = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(pts) < 2:
        return None
    n = len(pts)
    sx = sum(i for i, _ in pts)
    sy = sum(v for _, v in pts)
    sxx = sum(i * i for i, _ in pts)
    sxy = sum(i * v for i, v in pts)
    denom = n * sxx - sx * sx
    return (n * sxy - sx * sy) / denom if denom else None


# ---------------------------------------------------------------- per-year ratios
def _point_in_time(inc: dict, bal: dict, cf: dict,
                   price: Optional[float], shares: Optional[float]) -> Dict[str, Any]:
    g = lambda d, k: _f((d or {}).get(k))

    rev = g(inc, "Revenue")
    gross = g(inc, "Gross Profit")
    op_inc = g(inc, "Operating Income")
    ebitda = g(inc, "EBITDA")
    ni = g(inc, "Net Income")
    pretax = g(inc, "Income Before Tax")
    tax = g(inc, "Income Tax Expense")
    int_exp = g(inc, "Interest Expense")
    dna = g(inc, "Depreciation and Amortization")
    eps = g(inc, "EPS Diluted") or g(inc, "EPS")
    cogs = g(inc, "Cost of Goods Sold")

    assets = g(bal, "Total Assets")
    equity = g(bal, "Total Shareholder Equity") or g(bal, "Total Equity")
    cur_assets = g(bal, "Total Current Assets")
    cur_liab = g(bal, "Total Current Liabilities")
    cash = g(bal, "Cash and Cash Equivalents")
    cash_sti = g(bal, "Cash and Short Term Investments")
    inv = g(bal, "Inventory")
    ar = g(bal, "Accounts Receivable")
    ap = g(bal, "Accounts Payable")
    ppe = g(bal, "Property, Plant and Equipment")
    st_debt = g(bal, "Short Term Debt")
    lt_debt = g(bal, "Long Term Debt")
    tot_debt = g(bal, "Total Debt")
    net_debt = g(bal, "Net Debt")
    tot_liab = g(bal, "Total Liabilities")
    retained = g(bal, "Retained Earnings")

    ocf = g(cf, "Operating Cash Flow") or g(cf, "Cash Flow from Operations")
    capex = g(cf, "Capital Expenditure")
    fcf = g(cf, "Free Cash Flow")
    sbc = g(cf, "Stock Based Compensation")
    div_paid = g(cf, "Dividends Paid")
    buyback = g(cf, "Common Stock Purchased")

    if fcf is None and ocf is not None and capex is not None:
        fcf = ocf + capex  # capex มักเป็นค่าลบ

    # market cap / EV รายปี (จาก price × shares ของปีนั้น)
    mktcap = (price * shares) if (price is not None and shares is not None) else None
    ev = None
    if mktcap is not None:
        ev = mktcap + (tot_debt or 0) - (cash or 0)

    # tax rate -> NOPAT -> ROIC
    tax_rate = _div(tax, pretax)
    if tax_rate is None or tax_rate < 0 or tax_rate > 0.6:
        tax_rate = 0.21
    nopat = op_inc * (1 - tax_rate) if op_inc is not None else None
    invested_cap = None
    if equity is not None:
        invested_cap = equity + (tot_debt or 0) - (cash or 0)

    wc = (cur_assets - cur_liab) if (cur_assets is not None and cur_liab is not None) else None
    ebit = op_inc  # ใช้ Operating Income แทน EBIT
    owner_earnings = (ni + (dna or 0) + (capex or 0)) if ni is not None else None  # NI + D&A − CapEx(ลบ)

    inv_turn = _div(cogs, inv)
    rec_turn = _div(rev, ar)
    pay_turn = _div(cogs, ap)
    dio = _div(DAYS, inv_turn)
    dso = _div(DAYS, rec_turn)
    dpo = _div(DAYS, pay_turn)
    ccc = (dio + dso - dpo) if (dio is not None and dso is not None and dpo is not None) else None

    f: Dict[str, Any] = {
        # 1) Profitability
        "Gross Margin": _div(gross, rev),
        "Operating Margin": _div(op_inc, rev),
        "EBITDA Margin": _div(ebitda, rev),
        "Net Margin": _div(ni, rev),
        "Pretax Margin": _div(pretax, rev),
        "FCF Margin": _div(fcf, rev),
        "OCF Margin": _div(ocf, rev),
        "NOPAT Margin": _div(nopat, rev),
        "ROA": _div(ni, assets),
        "ROE": _div(ni, equity),
        "ROIC": _div(nopat, invested_cap),
        "ROCE": _div(ebit, (assets - cur_liab) if (assets is not None and cur_liab is not None) else None),
        "Cash ROA": _div(ocf, assets),
        "Cash ROE": _div(ocf, equity),
        # 3) Liquidity
        "Current Ratio": _div(cur_assets, cur_liab),
        "Quick Ratio": _div((cur_assets - inv) if (cur_assets is not None and inv is not None) else None, cur_liab),
        "Cash Ratio": _div(cash, cur_liab),
        "OCF Ratio": _div(ocf, cur_liab),
        "Cash to Assets": _div(cash_sti, assets),
        "Cash to Liabilities": _div(cash_sti, tot_liab),
        "NWC to Assets": _div(wc, assets),
        # 4) Leverage
        "Debt to Equity": _div(tot_debt, equity),
        "Debt to Assets": _div(tot_debt, assets),
        "LT Debt Ratio": _div(lt_debt, assets),
        "ST Debt Ratio": _div(st_debt, assets),
        "Interest Coverage": _div(op_inc, int_exp),
        "Equity Ratio": _div(equity, assets),
        "Financial Leverage": _div(assets, equity),
        "Liabilities to Assets": _div(tot_liab, assets),
        "Net Debt to EBITDA": _div(net_debt, ebitda),
        "Net Debt to FCF": _div(net_debt, fcf),
        # 5) Efficiency
        "Asset Turnover": _div(rev, assets),
        "Inventory Turnover": inv_turn,
        "Receivable Turnover": rec_turn,
        "Payable Turnover": pay_turn,
        "DIO": dio, "DSO": dso, "DPO": dpo,
        "Cash Conversion Cycle": ccc,
        "Fixed Asset Turnover": _div(rev, ppe),
        "Working Capital Turnover": _div(rev, wc),
        # 6) Cash Flow Quality
        "FCF Yield": _div(fcf, mktcap),
        "FCF to NetIncome": _div(fcf, ni),
        "Owner Earnings Margin": _div(owner_earnings, rev),
        "Owner Earnings Yield": _div(owner_earnings, mktcap),
        "CapEx to Revenue": _div(abs(capex) if capex is not None else None, rev),
        "CapEx to OCF": _div(abs(capex) if capex is not None else None, ocf),
        "SBC to Revenue": _div(sbc, rev),
        "Accrual Ratio": _div((ni - ocf) if (ni is not None and ocf is not None) else None, assets),
        # 7) Valuation (รายปี)
        "PE": _div(price, eps),
        "Earnings Yield": _div(eps, price),
        "PS": _div(mktcap, rev),
        "PBV": _div(mktcap, equity),
        "Price to FCF": _div(mktcap, fcf),
        "Price to OwnerEarnings": _div(mktcap, owner_earnings),
        "EV to EBITDA": _div(ev, ebitda),
        "EV to EBIT": _div(ev, ebit),
        "EV to Sales": _div(ev, rev),
        "Dividend Yield": _div(-div_paid if div_paid is not None else None, mktcap),
        "Buyback Yield": _div(-buyback if buyback is not None else None, mktcap),
        # 9) Buffett
        "Retained Earnings to Assets": _div(retained, assets),
        # ค่าระดับ (level) เก็บไว้ใช้คำนวณ growth/cagr/stability ต่อ (ไม่ใช่ฟีเจอร์โดยตรง)
        "_rev": rev, "_ni": ni, "_eps": eps, "_fcf": fcf, "_equity": equity,
        "_assets": assets, "_ebitda": ebitda, "_op_inc": op_inc, "_ocf": ocf,
        "_oe": owner_earnings, "_shares": shares, "_gross_margin": _div(gross, rev),
        "_roic": _div(nopat, invested_cap), "_roe": _div(ni, equity),
        "_net_margin": _div(ni, rev), "_fcf_margin": _div(fcf, rev),
        "_at": _div(rev, assets), "_cur": _div(cur_assets, cur_liab),
        "_ltdebt_ratio": _div(lt_debt, assets), "_price": price,
    }

    # Shareholder Yield = Dividend + Buyback
    dy, by = f.get("Dividend Yield"), f.get("Buyback Yield")
    f["Shareholder Yield"] = (dy or 0) + (by or 0) if (dy is not None or by is not None) else None

    # 8) Altman Z-Score
    if all(v is not None for v in (wc, assets, retained, ebit, mktcap, tot_liab, rev)) and assets and tot_liab:
        f["Altman Z"] = (1.2 * (wc / assets) + 1.4 * (retained / assets)
                         + 3.3 * (ebit / assets) + 0.6 * (mktcap / tot_liab)
                         + 1.0 * (rev / assets))
    else:
        f["Altman Z"] = None

    return f


# ---------------------------------------------------------------- cross-year
def _piotroski(cur: dict, prev: dict) -> Optional[int]:
    """Piotroski F-Score (0-9) ใช้ค่า level ที่เก็บไว้ในฟีเจอร์ปีปัจจุบัน/ก่อนหน้า"""
    if not prev:
        return None
    score = 0
    roa_c = _div(cur.get("_ni"), cur.get("_assets"))
    roa_p = _div(prev.get("_ni"), prev.get("_assets"))
    # 1 ROA>0  2 OCF>0  3 ROA up  4 OCF>NI
    if roa_c is not None and roa_c > 0: score += 1
    if cur.get("_ocf") is not None and cur["_ocf"] > 0: score += 1
    if roa_c is not None and roa_p is not None and roa_c > roa_p: score += 1
    if cur.get("_ocf") is not None and cur.get("_ni") is not None and cur["_ocf"] > cur["_ni"]: score += 1
    # 5 LT debt ratio ลดลง  6 current ratio เพิ่ม  7 ไม่มีหุ้นเพิ่ม
    if cur.get("_ltdebt_ratio") is not None and prev.get("_ltdebt_ratio") is not None and cur["_ltdebt_ratio"] <= prev["_ltdebt_ratio"]: score += 1
    if cur.get("_cur") is not None and prev.get("_cur") is not None and cur["_cur"] > prev["_cur"]: score += 1
    if cur.get("_shares") is not None and prev.get("_shares") is not None and cur["_shares"] <= prev["_shares"] * 1.02: score += 1
    # 8 gross margin เพิ่ม  9 asset turnover เพิ่ม
    if cur.get("_gross_margin") is not None and prev.get("_gross_margin") is not None and cur["_gross_margin"] > prev["_gross_margin"]: score += 1
    if cur.get("_at") is not None and prev.get("_at") is not None and cur["_at"] > prev["_at"]: score += 1
    return score


def engineer_symbol(symbol: str) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """คืน ({year: {feature: value}}, [years]) — ฟีเจอร์ครบทุกหมวดต่อปี"""
    inc_all, bal_all, cf_all, basic = load_statements(symbol)
    prices = basic.get("Prices", {}) or {}
    years = sorted(set(inc_all) & set(bal_all) & set(cf_all), key=lambda y: int(y) if str(y).isdigit() else 0)
    years = [y for y in years if str(y).isdigit()]

    # รอบ 1: ฟีเจอร์ point-in-time
    feats: Dict[str, Dict[str, Any]] = {}
    for y in years:
        inc, bal, cf = inc_all.get(y, {}), bal_all.get(y, {}), cf_all.get(y, {})
        price = _f((inc or {}).get("price")) or _f(prices.get(y))
        shares = _f((inc or {}).get("Weighted Average Shares Diluted")) or _f((inc or {}).get("Weighted Average Shares"))
        feats[y] = _point_in_time(inc, bal, cf, price, shares)

    # รอบ 2: ฟีเจอร์ข้ามปี (growth / CAGR / stability / trend / momentum / Piotroski)
    for i, y in enumerate(years):
        cur = feats[y]
        prev = feats[years[i - 1]] if i >= 1 else {}
        y3 = feats[years[i - 3]] if i >= 3 else {}
        y5 = feats[years[i - 5]] if i >= 5 else {}

        # Growth YoY
        cur["Revenue Growth"] = _growth(cur.get("_rev"), prev.get("_rev"))
        cur["Net Income Growth"] = _growth(cur.get("_ni"), prev.get("_ni"))
        cur["EPS Growth"] = _growth(cur.get("_eps"), prev.get("_eps"))
        cur["Operating Income Growth"] = _growth(cur.get("_op_inc"), prev.get("_op_inc"))
        cur["EBITDA Growth"] = _growth(cur.get("_ebitda"), prev.get("_ebitda"))
        cur["FCF Growth"] = _growth(cur.get("_fcf"), prev.get("_fcf"))
        cur["Equity Growth"] = _growth(cur.get("_equity"), prev.get("_equity"))
        cur["Asset Growth"] = _growth(cur.get("_assets"), prev.get("_assets"))
        cur["OwnerEarnings Growth"] = _growth(cur.get("_oe"), prev.get("_oe"))

        # CAGR 3Y / 5Y
        cur["Revenue CAGR 3Y"] = _cagr(cur.get("_rev"), y3.get("_rev"), 3)
        cur["Revenue CAGR 5Y"] = _cagr(cur.get("_rev"), y5.get("_rev"), 5)
        cur["EPS CAGR 3Y"] = _cagr(cur.get("_eps"), y3.get("_eps"), 3)
        cur["EPS CAGR 5Y"] = _cagr(cur.get("_eps"), y5.get("_eps"), 5)
        cur["FCF CAGR 3Y"] = _cagr(cur.get("_fcf"), y3.get("_fcf"), 3)
        cur["FCF CAGR 5Y"] = _cagr(cur.get("_fcf"), y5.get("_fcf"), 5)

        # Stability / Trend (trailing สูงสุด 5 ปี ถึงปีนี้)
        win = years[max(0, i - 4):i + 1]
        cur["ROE Stability"] = _std([feats[w].get("_roe") for w in win])
        cur["Margin Stability"] = _std([feats[w].get("_net_margin") for w in win])
        cur["FCF Stability"] = _std([feats[w].get("_fcf_margin") for w in win])
        cur["Revenue Growth Stability"] = _std([feats[w].get("Revenue Growth") for w in win])
        cur["ROIC Trend"] = _slope([feats[w].get("_roic") for w in win])

        # Market momentum (จากราคารายปี) — เป็นผลตอบแทน "อดีต" ใช้เป็นฟีเจอร์ได้
        cur["Momentum 1Y"] = _growth(cur.get("_price"), prev.get("_price"))
        cur["Price Change 3Y"] = _growth(cur.get("_price"), y3.get("_price"))
        cur["Price Change 5Y"] = _growth(cur.get("_price"), y5.get("_price"))

        # PEG = PE / EPS growth(%)
        pe, epsg = cur.get("PE"), cur.get("EPS Growth")
        cur["PEG"] = (pe / (epsg * 100)) if (pe is not None and epsg is not None and epsg > 0) else None

        # Piotroski F-Score
        cur["Piotroski F"] = _piotroski(cur, prev)

    # รอบ 3: ลบค่า level (_xxx) ออกหลังคำนวณข้ามปีครบแล้ว
    # (ลบในลูปที่ 2 ไม่ได้ เพราะปีถัดไปยังต้องใช้ค่า level ของปีก่อนหน้า)
    for y in years:
        for k in [k for k in feats[y] if k.startswith("_")]:
            del feats[y][k]

    return feats, years
