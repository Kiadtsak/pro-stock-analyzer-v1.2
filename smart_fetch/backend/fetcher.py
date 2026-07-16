"""
backend/fetcher.py — Fetch financial data when not in cache.

ใช้ไลบรารี **financetoolkit** เป็นตัวหลัก (pip install financetoolkit)
  - ข้อมูลจาก FMP ผ่าน financetoolkit → format ตรงกับไฟล์ data/ เดิม 100%
    (financetoolkit คือตัวที่ normalize ชื่อ field เป็น "Cost of Goods Sold",
     "Total Equity", "Operating Cash Flow" ฯลฯ แบบเดียวกับไฟล์เดิม)
  - ต้องมี FMP_API_KEY (ใน .env หรือ environment)

Fallback: yfinance (ฟรี ไม่ต้องมี key — pip install yfinance)

ผลลัพธ์: data/{SYMBOL}_financials.json พร้อมใช้กับ analyze_financials ทันที
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("pro_stock_analyzer.fetcher")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
START_DATE = "2019-01-01"     # ดึงย้อนหลังประมาณ 5 ปีงบ


class FetchError(Exception):
    """Raised when all fetch sources fail."""


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════

def fetch_and_save(symbol: str, data_dir: Optional[Path] = None) -> dict:
    """
    ดึงข้อมูลหุ้นแล้วบันทึกลง data/{SYMBOL}_financials.json

    ลำดับ: financetoolkit (FMP) → yfinance → raise FetchError

    Returns: dict ข้อมูลงบการเงิน (format เดียวกับไฟล์เดิมใน data/)
    """
    symbol = symbol.upper().strip()
    d = data_dir or DATA_DIR
    d.mkdir(parents=True, exist_ok=True)

    data = None
    errors: list[str] = []

    # ── Source 1: financetoolkit (ต้องมี FMP_API_KEY) ──────────
    if FMP_API_KEY:
        try:
            log.info(f"📡 Fetching {symbol} via financetoolkit (FMP)...")
            data = _fetch_financetoolkit(symbol)
        except ImportError:
            errors.append("financetoolkit: not installed (pip install financetoolkit)")
        except Exception as e:
            errors.append(f"financetoolkit: {e}")
            log.warning(f"financetoolkit fetch failed for {symbol}: {e}")
    else:
        errors.append("financetoolkit: skipped (no FMP_API_KEY set)")

    # ── Source 2: yfinance (fallback ฟรี) ──────────────────────
    if data is None:
        try:
            log.info(f"📡 Fetching {symbol} via yfinance (fallback)...")
            data = _fetch_yfinance(symbol)
        except ImportError:
            errors.append("yfinance: not installed (pip install yfinance)")
        except Exception as e:
            errors.append(f"yfinance: {e}")
            log.warning(f"yfinance fetch failed for {symbol}: {e}")

    if data is None:
        raise FetchError(
            f"Cannot fetch {symbol} from any source. Errors: {'; '.join(errors)}"
        )

    # Validate — ต้องมีอย่างน้อย 1 ปีของ income statement
    if not data.get("Income Statement"):
        raise FetchError(f"{symbol}: fetched data has no Income Statement years")

    # ── Save ────────────────────────────────────────────────────
    path = d / f"{symbol}_financials.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    n_years = len(data["Income Statement"])
    log.info(f"💾 Saved {symbol} → {path.name} ({n_years} years)")

    return data


# ═══════════════════════════════════════════════════════════════════════════
# Source 1: financetoolkit  (pip install financetoolkit)
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_financetoolkit(symbol: str) -> dict:
    """
    ดึงผ่าน financetoolkit — คืนข้อมูลใน format เดียวกับไฟล์ data/ เดิมเป๊ะ
    เพราะ financetoolkit คือตัว normalize ชื่อ field แบบเดียวกัน
    """
    from financetoolkit import Toolkit    # lazy import

    tk = Toolkit(
        tickers=[symbol],
        api_key=FMP_API_KEY,
        start_date=START_DATE,
        quarterly=False,
        progress_bar=False,
    )

    income = _df_to_years(tk.get_income_statement(), symbol)
    balance = _df_to_years(tk.get_balance_sheet_statement(), symbol)
    cashflow = _df_to_years(tk.get_cash_flow_statement(), symbol)

    if not income:
        raise FetchError(
            f"financetoolkit returned no income statement for {symbol} "
            f"(invalid symbol, or FMP key limit/invalid)"
        )

    # ── Basic Info จาก profile ─────────────────────────────
    basic: dict[str, Any] = {"Symbol": symbol}
    try:
        profile = tk.get_profile()
        p = profile[symbol] if symbol in getattr(profile, "columns", []) \
            else profile.iloc[:, 0]
        basic.update({
            "Name": _s(p.get("Company Name")) or symbol,
            "Sector": _s(p.get("Sector")) or "",
            "Industry": _s(p.get("Industry")) or "",
            "CurrentPrice": _to_num(p.get("Price")),
            "MarketCap": _to_num(p.get("Market Capitalization")),
            "Currency": _s(p.get("Currency")) or "USD",
            "Employees": _to_num(p.get("Full Time Employees")),
            "Beta": _to_num(p.get("Beta")),
        })
    except Exception as e:
        log.warning(f"Profile fetch failed for {symbol} (continuing): {e}")
        basic.setdefault("Name", symbol)

    # ── Prices รายปี (สำหรับ risk metrics) ─────────────────
    try:
        hist = tk.get_historical_data(period="yearly")
        prices = {}
        for idx, row in hist.iterrows():
            year = str(idx)[:4]
            close = _to_num(row.get("Adj Close")) or _to_num(row.get("Close"))
            if close is not None and year.isdigit():
                prices[year] = round(close, 2)
        if prices:
            basic["Prices"] = prices
    except Exception as e:
        log.warning(f"Historical prices failed for {symbol} (continuing): {e}")

    return {
        "Basic Info": basic,
        "Income Statement": income,
        "Balance Sheet": balance,
        "Cash Flow Statement": cashflow,
    }


def _df_to_years(df, ticker: Optional[str] = None) -> dict:
    """
    แปลง DataFrame ของ financetoolkit → {year: {field: value}}

    Toolkit คืน DataFrame ที่ index = ชื่อรายการ (เช่น "Revenue"),
    columns = ปี (Period/str) — ถ้าหลาย ticker index เป็น MultiIndex
    """
    if df is None or getattr(df, "empty", True):
        return {}

    # หลาย ticker → เลือกเฉพาะ ticker ที่ต้องการ
    try:
        import pandas as pd
        if isinstance(df.index, pd.MultiIndex) and ticker is not None:
            df = df.loc[ticker]
    except Exception:
        pass

    out: dict[str, dict] = {}
    for col in df.columns:
        year = str(col)[:4]
        if not year.isdigit():
            continue
        year_data = {}
        for item in df.index:
            num = _to_num(df.loc[item, col])
            if num is not None:
                year_data[str(item).strip()] = num
        if year_data:
            out[year] = year_data
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Source 2: yfinance fallback  (pip install yfinance)
# — map ชื่อ field เป็นชุดเดียวกับ financetoolkit เพื่อ format สม่ำเสมอ
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_yfinance(symbol: str) -> dict:
    import yfinance as yf    # lazy import

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    if not info.get("longName") and not info.get("shortName"):
        raise FetchError(f"yfinance: no data for {symbol} (invalid symbol?)")

    basic = {
        "Symbol": symbol,
        "Name": info.get("longName") or info.get("shortName") or symbol,
        "Sector": info.get("sector", ""),
        "Industry": info.get("industry", ""),
        "CurrentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
        "MarketCap": info.get("marketCap"),
        "Currency": info.get("currency", "USD"),
        "Employees": info.get("fullTimeEmployees"),
    }

    try:
        hist = ticker.history(period="5y", interval="1mo")
        if hist is not None and not hist.empty:
            prices = {}
            for date, row in hist.iterrows():
                prices[str(date.year)] = round(float(row["Close"]), 2)
            basic["Prices"] = prices
    except Exception:
        pass

    income = _convert_yf_statement(ticker.financials, {
        "Total Revenue": "Revenue",
        "Cost Of Revenue": "Cost of Goods Sold",
        "Gross Profit": "Gross Profit",
        "Research And Development": "Research and Development Expenses",
        "Selling General And Administration": "Selling, General and Administrative Expenses",
        "Operating Expense": "Operating Expenses",
        "Interest Expense": "Interest Expense",
        "EBITDA": "EBITDA",
        "EBIT": "EBIT",
        "Operating Income": "Operating Income",
        "Pretax Income": "Income Before Tax",
        "Tax Provision": "Income Tax Expense",
        "Net Income": "Net Income",
        "Basic EPS": "EPS",
        "Diluted EPS": "EPS Diluted",
        "Basic Average Shares": "Weighted Average Shares",
        "Diluted Average Shares": "Weighted Average Shares Diluted",
        "Reconciled Depreciation": "Depreciation and Amortization",
    })

    balance = _convert_yf_statement(ticker.balance_sheet, {
        "Cash And Cash Equivalents": "Cash and Cash Equivalents",
        "Other Short Term Investments": "Short Term Investments",
        "Accounts Receivable": "Accounts Receivable",
        "Inventory": "Inventory",
        "Current Assets": "Total Current Assets",
        "Net PPE": "Property, Plant and Equipment",
        "Goodwill": "Goodwill",
        "Other Intangible Assets": "Intangible Assets",
        "Total Assets": "Total Assets",
        "Accounts Payable": "Accounts Payable",
        "Current Debt": "Short Term Debt",
        "Current Liabilities": "Total Current Liabilities",
        "Long Term Debt": "Long Term Debt",
        "Total Debt": "Total Debt",
        "Total Liabilities Net Minority Interest": "Total Liabilities",
        "Retained Earnings": "Retained Earnings",
        "Common Stock": "Common Stock",
        "Stockholders Equity": "Total Equity",
    })

    cashflow = _convert_yf_statement(ticker.cashflow, {
        "Operating Cash Flow": "Operating Cash Flow",
        "Capital Expenditure": "Capital Expenditure",
        "Free Cash Flow": "Free Cash Flow",
        "Depreciation And Amortization": "Depreciation and Amortization",
        "Change In Working Capital": "Change in Working Capital",
        "Stock Based Compensation": "Stock Based Compensation",
        "Cash Dividends Paid": "Dividends Paid",
        "Repurchase Of Capital Stock": "Common Stock Purchased",
        "Investing Cash Flow": "Cash Flow from Investing",
        "Financing Cash Flow": "Cash Flow from Financing",
    })

    return {
        "Basic Info": basic,
        "Income Statement": income,
        "Balance Sheet": balance,
        "Cash Flow Statement": cashflow,
    }


def _convert_yf_statement(df, mapping: dict) -> dict:
    """แปลง DataFrame ของ yfinance เป็น {year: {field: value}} ตาม mapping."""
    if df is None or getattr(df, "empty", True):
        return {}
    result = {}
    for col in df.columns:
        year = str(col.year) if hasattr(col, "year") else str(col)[:4]
        year_data = {}
        for yf_key, our_key in mapping.items():
            if yf_key in df.index:
                num = _to_num(df.loc[yf_key, col])
                if num is not None:
                    year_data[our_key] = num
        if year_data:
            result[year] = year_data
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _to_num(v: Any) -> Optional[float]:
    """แปลงเป็น float ปลอดภัย (NaN/None/str-ที่ไม่ใช่เลข → None)."""
    if v is None:
        return None
    try:
        x = float(v)
        if x != x:      # NaN
            return None
        return x
    except (TypeError, ValueError):
        return None


def _s(v: Any) -> Optional[str]:
    """แปลงเป็น str ปลอดภัย (NaN/None → None)."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and v != v:
            return None
    except Exception:
        pass
    s = str(v).strip()
    return s or None


if __name__ == "__main__":
    # ทดสอบ: python3 backend/fetcher.py AAPL
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sym = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    try:
        data = fetch_and_save(sym)
        years = sorted(data["Income Statement"].keys())
        src = "financetoolkit" if FMP_API_KEY else "yfinance"
        print(f"✅ {sym}: {len(years)} years {years} (source: {src})")
    except FetchError as e:
        print(f"❌ {e}")
