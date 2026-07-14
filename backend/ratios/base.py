"""
backend/ratios/base.py — Foundation for all financial ratio calculators.

Every category (Profitability, Liquidity, ...) inherits from RatioBase.
Provides safe math operations that never raise on bad data (returns None).
"""
from __future__ import annotations

import math
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# Safe math helpers — return None instead of raising on bad input
# ═══════════════════════════════════════════════════════════════════════════

def sfloat(v: Any) -> float | None:
    """Safely convert to float. Returns None for NaN/Inf/None/non-numeric."""
    if v is None:
        return None
    try:
        x = float(v)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except (TypeError, ValueError):
        return None


def sdiv(num: Any, den: Any) -> float | None:
    """Safe division: returns None if denominator is 0/None."""
    n, d = sfloat(num), sfloat(den)
    if n is None or d is None or d == 0:
        return None
    return n / d


def spct(v: float | None, decimals: int = 4) -> float | None:
    """Convert ratio to percentage (× 100)."""
    if v is None:
        return None
    return round(v * 100, decimals)


def savg(*values: Any) -> float | None:
    """Average of numeric values, ignoring None."""
    nums = [sfloat(v) for v in values]
    nums = [n for n in nums if n is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def sround(v: float | None, decimals: int = 4) -> float | None:
    """Round if not None."""
    return None if v is None else round(v, decimals)


# ═══════════════════════════════════════════════════════════════════════════
# Fuzzy key lookup — handles inconsistent key names across data sources
# ═══════════════════════════════════════════════════════════════════════════

def get(d: dict | None, *keys: str, default: Any = None) -> Any:
    """
    Get first non-None value from dict by trying multiple keys.

    Case-insensitive and whitespace-tolerant.

    Example:
        get(income, "Revenue", "Total Revenue", "Sales")
        → tries each key, returns first valid float found
    """
    if not d:
        return default

    # Direct match first (fast path)
    for k in keys:
        if k in d:
            v = sfloat(d[k])
            if v is not None:
                return v

    # Normalized fallback
    norm = {str(k).lower().strip(): v for k, v in d.items()}
    for k in keys:
        v = sfloat(norm.get(k.lower().strip()))
        if v is not None:
            return v

    return default


# ═══════════════════════════════════════════════════════════════════════════
# RatioBase — parent class for all category calculators
# ═══════════════════════════════════════════════════════════════════════════

class RatioBase:
    """
    Base class for ratio calculators.

    Sub-classes implement compute() which returns a dict of {ratio_name: value}.

    Available inputs (all optional):
        income        — Income Statement for the year
        balance       — Balance Sheet for the year
        cashflow      — Cash Flow Statement for the year
        basic_info    — {'CurrentPrice', 'MarketCap', 'Sector', ...}
        prev_income   — Income Statement for prior year (for growth ratios)
        prev_balance  — Balance Sheet for prior year (for turnover averages)
        prev_cashflow — Cash Flow Statement for prior year
        ttm_history   — list of dicts for 5-10 years (for long-term metrics)
    """

    # Sub-classes override this
    category: str = "base"
    description: str = ""

    def __init__(
        self,
        income: dict | None = None,
        balance: dict | None = None,
        cashflow: dict | None = None,
        basic_info: dict | None = None,
        prev_income: dict | None = None,
        prev_balance: dict | None = None,
        prev_cashflow: dict | None = None,
        ttm_history: list[dict] | None = None,
    ):
        self.income = income or {}
        self.balance = balance or {}
        self.cashflow = cashflow or {}
        self.basic_info = basic_info or {}
        self.prev_income = prev_income or {}
        self.prev_balance = prev_balance or {}
        self.prev_cashflow = prev_cashflow or {}
        self.ttm_history = ttm_history or []

    # ── Convenient shortcuts ─────────────────────────────
    def _revenue(self) -> float | None:
        return get(self.income, "Revenue", "Total Revenue", "Sales", "Net Sales")

    def _cogs(self) -> float | None:
        return get(self.income, "Cost of Goods Sold", "Cost Of Revenue", "COGS")

    def _gross_profit(self) -> float | None:
        gp = get(self.income, "Gross Profit")
        if gp is not None:
            return gp
        rev, cogs = self._revenue(), self._cogs()
        if rev is not None and cogs is not None:
            return rev - cogs
        return None

    def _operating_income(self) -> float | None:
        return get(self.income, "Operating Income", "Operating Income Loss", "EBIT")

    def _ebit(self) -> float | None:
        ebit = get(self.income, "EBIT", "Operating Income")
        if ebit is not None:
            return ebit
        # EBIT = Net Income + Interest + Taxes
        ni = self._net_income()
        interest = get(self.income, "Interest Expense") or 0
        tax = get(self.income, "Income Tax Expense", "Tax Expense") or 0
        if ni is not None:
            return ni + interest + tax
        return None

    def _ebitda(self) -> float | None:
        ebitda = get(self.income, "EBITDA")
        if ebitda is not None:
            return ebitda
        # EBITDA = EBIT + D&A
        ebit = self._ebit()
        da = get(self.income, "Depreciation and Amortization",
                 "Depreciation & Amortization", "D&A")
        if da is None:
            da = get(self.cashflow, "Depreciation and Amortization") or 0
        if ebit is not None:
            return ebit + (da or 0)
        return None

    def _net_income(self) -> float | None:
        return get(self.income, "Net Income", "Net Income Loss",
                   "Net Income Common")

    def _total_assets(self) -> float | None:
        return get(self.balance, "Total Assets")

    def _total_equity(self) -> float | None:
        return get(self.balance, "Total Equity", "Stockholders Equity",
                   "Total Stockholder Equity", "Total Shareholder Equity")

    def _total_liabilities(self) -> float | None:
        return get(self.balance, "Total Liabilities")

    def _current_assets(self) -> float | None:
        return get(self.balance, "Total Current Assets", "Current Assets")

    def _current_liabilities(self) -> float | None:
        return get(self.balance, "Total Current Liabilities", "Current Liabilities")

    def _cash(self) -> float | None:
        return get(self.balance, "Cash And Cash Equivalents", "Cash",
                   "Cash and Cash Equivalents", "Cash & Short Term Investments")

    def _total_debt(self) -> float | None:
        td = get(self.balance, "Total Debt")
        if td is not None:
            return td
        # Sum from components
        lt = get(self.balance, "Long Term Debt") or 0
        st = get(self.balance, "Short Term Debt", "Current Debt") or 0
        if lt or st:
            return lt + st
        return None

    def _inventory(self) -> float | None:
        return get(self.balance, "Inventory", "Inventories")

    def _receivables(self) -> float | None:
        return get(self.balance, "Accounts Receivable", "Net Receivables",
                   "Trade Receivables")

    def _payables(self) -> float | None:
        return get(self.balance, "Accounts Payable", "Trade Payables")

    def _ocf(self) -> float | None:
        return get(self.cashflow, "Operating Cash Flow",
                   "Cash From Operations", "Cash Flow From Operations")

    def _capex(self) -> float | None:
        # Always return positive magnitude — real data (yfinance/FMP) stores CapEx as negative
        v = get(self.cashflow, "Capital Expenditure", "Capex", "CapEx")
        return None if v is None else abs(v)

    def _fcf(self) -> float | None:
        fcf = get(self.cashflow, "Free Cash Flow", "FCF")
        if fcf is not None:
            return fcf
        ocf, capex = self._ocf(), self._capex()
        if ocf is not None:
            return ocf - (capex or 0)
        return None

    def _shares(self) -> float | None:
        return get(self.income, "Weighted Average Shares Diluted",
                   "Weighted Average Shares", "Weighted Average Shares Outstanding",
                   "Shares Outstanding")

    def _eps(self) -> float | None:
        eps = get(self.income, "Earnings Per Share", "EPS", "Basic EPS",
                  "EPS Diluted", "Diluted EPS")
        if eps is not None:
            return eps
        ni, sh = self._net_income(), self._shares()
        return sdiv(ni, sh)

    def _price(self) -> float | None:
        return sfloat(self.basic_info.get("CurrentPrice") or
                      self.basic_info.get("Price"))

    def _market_cap(self) -> float | None:
        mc = sfloat(self.basic_info.get("MarketCap"))
        if mc is not None:
            return mc
        p, sh = self._price(), self._shares()
        return None if (p is None or sh is None) else p * sh

    def _dividends_paid(self) -> float | None:
        dp = get(self.cashflow, "Dividends Paid", "Common Dividends")
        return None if dp is None else abs(dp)  # often stored as negative

    def _interest_expense(self) -> float | None:
        ie = get(self.income, "Interest Expense")
        return None if ie is None else abs(ie)

    def _da(self) -> float | None:
        """Depreciation & Amortization."""
        da = get(self.income, "Depreciation and Amortization", "D&A")
        if da is not None:
            return da
        return get(self.cashflow, "Depreciation and Amortization",
                   "Depreciation & Amortization")

    def _avg_assets(self) -> float | None:
        cur = self._total_assets()
        prev = get(self.prev_balance, "Total Assets")
        if cur is not None and prev is not None:
            return (cur + prev) / 2
        return cur

    def _avg_equity(self) -> float | None:
        cur = self._total_equity()
        prev = get(self.prev_balance, "Total Equity", "Stockholders Equity",
                   "Total Stockholder Equity")
        # Guard: negative equity makes ROE/ROIC meaningless
        # Return None to signal "not applicable" rather than misleading value
        if cur is not None and cur <= 0:
            return None
        if cur is not None and prev is not None:
            # If prev equity was positive but current is negative (or vice versa),
            # the average would be near-zero and cause ratio explosion.
            if prev <= 0:
                return cur   # Only use current when prev is bad
            return (cur + prev) / 2
        return cur

    def _avg_inventory(self) -> float | None:
        cur = self._inventory()
        prev = get(self.prev_balance, "Inventory", "Inventories")
        if cur is not None and prev is not None:
            return (cur + prev) / 2
        return cur

    def _avg_receivables(self) -> float | None:
        cur = self._receivables()
        prev = get(self.prev_balance, "Accounts Receivable", "Net Receivables")
        if cur is not None and prev is not None:
            return (cur + prev) / 2
        return cur

    def _avg_payables(self) -> float | None:
        cur = self._payables()
        prev = get(self.prev_balance, "Accounts Payable")
        if cur is not None and prev is not None:
            return (cur + prev) / 2
        return cur

    # ── Sub-classes implement this ───────────────────────
    def compute(self) -> dict[str, float | None]:
        """Return {ratio_name: value} — override in subclass."""
        raise NotImplementedError
