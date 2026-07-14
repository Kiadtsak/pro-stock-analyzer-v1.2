"""
debug_keys.py
=============
รัน script นี้บน Mac ของคุณเพื่อหา root cause ของ "Net Income $0.00" + "Shares 0M"
จากภาพล่าสุด

วิธีใช้:
    cd "/Users/npphone6622hotmail.com/Desktop/AI Valuation Stock System version1"
    python Backend/debug_keys.py AAPL

จะ print:
    1. คีย์จริงที่ data adapter ส่งมา
    2. ค่าที่ code คาดเทียบกับค่าที่ได้
    3. แนะนำการแก้ที่ตรงจุด
"""
from __future__ import annotations
import sys
import json
from pathlib import Path

# Add Backend to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def diagnose(symbol: str = "AAPL"):
    print("=" * 70)
    print(f"  LUXE CAPITAL — DCF Bug Diagnostics for {symbol}")
    print("=" * 70)

    # --- STEP 1: หา adapter / loader ที่ใช้ดึง data ---
    print("\n[1] Looking for data adapter modules in Backend/ ...")
    backend = Path(__file__).resolve().parent
    candidates = []
    for p in backend.rglob("*.py"):
        name = p.name.lower()
        if any(kw in name for kw in ["adapter", "loader", "fetcher", "fmp", "api", "data", "client"]):
            if "cashflow" not in name:
                candidates.append(p.relative_to(backend))
    print(f"    candidates: {candidates or 'ไม่พบ — ผู้ใช้ดึงข้อมูลจากที่อื่น'}")

    # --- STEP 2: ลอง fetch data จริง ---
    print(f"\n[2] Trying to fetch raw data for {symbol} ...")
    income, balance, cashflow = try_fetch(symbol)

    if not income:
        print("    ❌ ไม่สามารถ fetch ได้อัตโนมัติ")
        print("    → กรุณา paste คีย์ที่ adapter ของคุณส่งให้ CashFlowModel มาให้ดู")
        print("    หรือใส่ print() ใน adapter เพื่อ dump keys ดังตัวอย่าง:")
        print("       print('Income keys:', list(income_data.keys())[:30])")
        return

    # --- STEP 3: ตรวจคีย์ที่เจอ vs ที่ code คาด ---
    print(f"\n[3] Income statement keys ที่ได้จริง ({len(income)} keys):")
    for k in sorted(income.keys()):
        v = income[k]
        v_str = f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)[:40]
        print(f"    {k!r:50}  →  {v_str}")

    # --- STEP 4: ตรวจคีย์ที่ CashFlowModel เดิมต้องการ ---
    print("\n[4] คีย์ที่ CashFlowModel.py เดิมหา:")
    expected = {
        "Revenue":                     income.get("Revenue"),
        "Net Income":                  income.get("Net Income"),
        "Operating Income":            income.get("Operating Income"),
        "EPS":                         income.get("EPS"),
        "EBITDA":                      income.get("EBITDA"),
        "EBIT":                        income.get("EBIT"),
        "Gross Profit":                income.get("Gross Profit"),
        "Cost of Goods Sold":          income.get("Cost of Goods Sold"),
        "Interest Expense":            income.get("Interest Expense"),
        "Depreciation and Amortization": income.get("Depreciation and Amortization"),
        "Weighted Average Shares":     income.get("Weighted Average Shares"),
        "Weighted Average Shares Diluted": income.get("Weighted Average Shares Diluted"),
        "price":                       income.get("price"),
    }
    missing = []
    for k, v in expected.items():
        status = "✅" if v not in (None, 0) else "❌ MISSING"
        if v in (None, 0):
            missing.append(k)
        print(f"    {status}  {k!r:42} → {v}")

    # --- STEP 5: แนะนำคีย์ที่ "น่าจะใช่" สำหรับคีย์ที่หาย ---
    print(f"\n[5] หาคีย์ที่ใกล้เคียงสำหรับ {len(missing)} คีย์ที่หายไป:")
    for m in missing:
        suggestions = fuzzy_match(m, list(income.keys()))
        if suggestions:
            print(f"    {m!r}")
            for s, score in suggestions[:3]:
                print(f"      ↳ ใน data มี: {s!r}  (similarity {score:.0%})")
        else:
            print(f"    {m!r} — ไม่พบคีย์ใกล้เคียง อาจต้องเปลี่ยน data source")

    # --- STEP 6: สรุป fix ---
    print("\n[6] วิธีแก้แนะนำ:")
    if not missing:
        print("    ✅ ทุกคีย์ครบ — bug อยู่ที่อื่น (ไม่ใช่ key mismatch)")
        return

    print("    1. ใช้ CashFlowModel.py patch v3 ที่ส่งไปก่อนหน้านี้ —")
    print("       มี _get() ที่ fuzzy match คีย์ Title/camel/snake/trailing-space")
    print("    2. หรือเพิ่ม alias ใน adapter ของคุณ:")
    print()
    for m in missing:
        sugg = fuzzy_match(m, list(income.keys()))
        if sugg:
            print(f"       income_data[{m!r}] = raw_data.get({sugg[0][0]!r})")


# ============================================================
#  Helpers
# ============================================================

def try_fetch(symbol: str):
    """พยายาม fetch ข้อมูลจาก adapter ของผู้ใช้แบบหลากหลายวิธี"""
    income, balance, cashflow = {}, {}, {}

    # ลอง import จาก adapter ทั่วไป
    for attempt in [
        lambda: _try_fmp(symbol),
        lambda: _try_yfinance(symbol),
        lambda: _try_user_loader(symbol),
    ]:
        try:
            result = attempt()
            if result and result[0]:
                return result
        except Exception as e:
            continue

    return {}, {}, {}


def _try_fmp(symbol: str):
    """ลอง financetoolkit ที่ติดตั้งอยู่ (จาก Luxe Capital project)"""
    import os
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key or api_key.lower().startswith("your_"):
        return None
    try:
        from financetoolkit import Toolkit
        tk = Toolkit(tickers=[symbol], api_key=api_key, quarterly=False)
        inc = tk.get_income_statement()
        bal = tk.get_balance_sheet_statement()
        cf  = tk.get_cash_flow_statement()
        # Convert latest year to dict
        latest = inc.columns[-1]
        return (
            {idx: inc.loc[idx, latest] for idx in inc.index},
            {idx: bal.loc[idx, latest] for idx in bal.index},
            {idx: cf.loc[idx, latest]  for idx in cf.index},
        )
    except Exception:
        return None


def _try_yfinance(symbol: str):
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        inc = t.financials
        if inc.empty:
            return None
        latest = inc.columns[0]
        return (
            {idx: inc.loc[idx, latest] for idx in inc.index},
            {},
            {},
        )
    except Exception:
        return None


def _try_user_loader(symbol: str):
    """ลอง import จาก Backend ของผู้ใช้"""
    try:
        # Try common module names
        for modname in ["Backend.DataLoader", "Backend.FMPAdapter",
                        "Backend.DataAdapter", "Backend.FinancialData"]:
            try:
                mod = __import__(modname, fromlist=['*'])
                # Look for a fetch function
                for fn_name in ["fetch", "get_financials", "load", "get_data"]:
                    if hasattr(mod, fn_name):
                        data = getattr(mod, fn_name)(symbol)
                        if isinstance(data, tuple) and len(data) == 3:
                            return data
            except ImportError:
                continue
    except Exception:
        pass
    return None


def fuzzy_match(target: str, candidates: list, top: int = 5):
    """หาคีย์ที่คล้ายกัน — case-insensitive + space/underscore tolerant"""
    import re
    norm_target = re.sub(r"[\s_]+", "", target.lower())
    target_words = set(re.findall(r"\w+", target.lower()))

    scored = []
    for c in candidates:
        if not isinstance(c, str):
            continue
        norm_c = re.sub(r"[\s_]+", "", c.lower())
        # Exact match after normalization
        if norm_c == norm_target:
            scored.append((c, 1.0))
            continue
        # Substring match
        if norm_target in norm_c or norm_c in norm_target:
            scored.append((c, 0.85))
            continue
        # Word overlap
        c_words = set(re.findall(r"\w+", c.lower()))
        if target_words and c_words:
            overlap = len(target_words & c_words) / max(len(target_words), len(c_words))
            if overlap >= 0.5:
                scored.append((c, overlap))

    return sorted(scored, key=lambda x: -x[1])[:top]


# ============================================================

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    diagnose(symbol)