"""
CashFlowModel.py — PATCHED v3 (2026-05-19)
==========================================

Root cause fixed:
    'Intrinsic Value / Share = $0.00' ในภาพเกิดจาก code หาคีย์
    "Weighted Average Shares" ไม่เจอ → ใช้ fallback 1.0 → DCF sum / 1
    → ค่ามหาศาล → frontend guard → แสดง $0.00

Fixes:
    1. _get_shares_outstanding() — robust resolver ลอง 8 key aliases
       (Title Case, camelCase, snake_case, trailing-space, FMP-style)
    2. Fallback chain: profile → market_cap/price → net_income/EPS
    3. คืน None (ไม่ใช่ 0.0 หรือ ค่ามหาศาล) เมื่อหาไม่เจอ
       → caller รู้ว่าควรแสดง "N/A" ไม่ใช่ $0.00
    4. _get() ใหม่ — string normalize (lower, strip space, snake)
       เพื่อจับคีย์แบบ case-insensitive และทนต่อ whitespace
"""
from __future__ import annotations
import re
import numpy as np
from Backend.Settings import TAX_RATE, RISK_FREE_RATE, BETA
from typing import Dict, Optional, List


# ============================================================
#  Key aliases — ทุกแบบที่ data sources จริงๆ ส่งมา
# ============================================================
SHARES_KEYS = [
    "Weighted Average Shares",
    "Weighted Average Shares Diluted",
    "weighted_average_shares",
    "weighted_average_shares_diluted",
    "weightedAverageSharesOutstanding",
    "weightedAverageSharesOutDil",
    "shares_outstanding",
    "sharesOutstanding",
    "commonStockSharesOutstanding",
    "Shares Outstanding",
]

PRICE_KEYS  = ["price", "Price", "current_price", "currentPrice", "stock_price"]
MCAP_KEYS   = ["market_cap", "marketCap", "Market Cap", "MarketCap"]
NI_KEYS     = ["Net Income", "net_income", "netIncome", "NI"]
EPS_KEYS    = ["EPS", "eps", "earnings_per_share", "earningsPerShare"]


def _normalize_key(s: str) -> str:
    """lowercase + strip + collapse spaces+underscores → for fuzzy matching."""
    return re.sub(r"[\s_]+", "", s.lower().strip())


class CashFlowModel:
    def __init__(
        self,
        income_data: Optional[Dict] = None,
        balance_data: Optional[Dict] = None,
        cashflow_data: Optional[Dict] = None,
    ):
        self.income = income_data or {}
        self.balance = balance_data or {}
        self.cashflow = cashflow_data or {}

    # ---------------- Safe helpers ---------------- #

    def _num(self, d: Dict, key: str, default: float = 0.0) -> float:
        v = d.get(key, default)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def _safe_div(self, num: float, den: float, default: float = 0.0) -> float:
        try:
            if den == 0 or den is None:
                return default
            return num / den
        except (TypeError, ZeroDivisionError):
            return default

    # ⭐ NEW: case/space-insensitive lookup with multiple aliases
    def _get(self, d: Dict, keys: List[str], default: float = 0.0) -> float:
        """
        Fuzzy key lookup — ลองหลายชื่อคีย์, normalize space/case.
        ช่วยแก้บั๊กที่ raw data ส่งคีย์มาแบบ camelCase, snake_case,
        หรือมี trailing space.
        """
        if not d:
            return default

        # 1) exact match กับ aliases
        for k in keys:
            if k in d and d[k] is not None:
                try:
                    return float(d[k])
                except (TypeError, ValueError):
                    continue

        # 2) normalized match (lowercase, ไม่สน space/underscore)
        normalized_targets = {_normalize_key(k) for k in keys}
        for actual_key, val in d.items():
            if _normalize_key(actual_key) in normalized_targets:
                if val is not None:
                    try:
                        return float(val)
                    except (TypeError, ValueError):
                        continue

        return default

    # ⭐ NEW: robust shares resolver — fallback chain
    def _get_shares_outstanding(self) -> Optional[float]:
        """
        หา shares outstanding ตามลำดับ:
            1. income statement (8 key aliases รวม trailing space)
            2. derive จาก market_cap / price
            3. derive จาก net_income / EPS

        Returns:
            float > 0 ถ้าหาเจอ
            None ถ้าหาไม่เจอ — caller ควรแสดง "N/A" ไม่ใช่ $0.00
        """
        # 1) Direct lookup
        shares = self._get(self.income, SHARES_KEYS, default=0.0)
        if shares > 0:
            return shares

        # ลองที่ balance / cashflow ด้วย เผื่อบาง provider เก็บไว้ที่นั่น
        shares = self._get(self.balance, SHARES_KEYS, default=0.0)
        if shares > 0:
            return shares

        # 2) Derive จาก market_cap / price
        mcap = self._get(self.income, MCAP_KEYS, default=0.0)
        price = self._get(self.income, PRICE_KEYS, default=0.0)
        if mcap > 0 and price > 0:
            return mcap / price

        # 3) Derive จาก net_income / EPS
        ni = self._get(self.income, NI_KEYS, default=0.0)
        eps = self._get(self.income, EPS_KEYS, default=0.0)
        if ni > 0 and eps > 0:
            return ni / eps

        return None  # หาไม่เจอ — ไม่ใช่ 0, ไม่ใช่ 1

    # ================= Cost of Capital ================= #

    def cost_of_equity(self, market_return: Optional[List[float]] = None) -> float:
        rm = 0.10 if market_return is None else float(np.mean(market_return))
        return RISK_FREE_RATE + BETA * (rm - RISK_FREE_RATE)

    def interest_paid(self) -> float:
        ip = self._num(self.cashflow, "Interest Paid", 0.0)
        if ip != 0:
            return abs(ip)
        ie = self._num(self.income, "Interest Expense", 0.0)
        return abs(ie)

    def wacc(self) -> float:
        equity = self._num(self.balance, "Total Shareholder Equity", 0.0)
        if equity <= 0:
            equity = self._num(self.balance, "Total Equity", 0.0)
        debt = self._num(self.balance, "Total Debt", 0.0)

        if equity <= 0 and debt <= 0:
            return 0.10

        interest = self.interest_paid()
        if debt > 0 and interest > 0:
            cost_debt = interest / debt
        else:
            cost_debt = RISK_FREE_RATE + 0.02

        cost_debt = min(max(cost_debt, 0.01), 0.15)
        cost_debt_after_tax = cost_debt * (1 - TAX_RATE)

        total = equity + debt
        ke = self.cost_of_equity()
        wacc = (equity / total) * ke + (debt / total) * cost_debt_after_tax
        return round(wacc, 4)

    # ================= Cash Flow ================= #

    def Operating_Cash_Flow(self) -> float:
        ocf_direct = self._num(self.cashflow, "Operating Cash Flow", 0.0)
        if ocf_direct != 0:
            return ocf_direct
        ni = self._num(self.income, "Net Income", 0.0)
        da = self._num(self.income, "Depreciation and Amortization", 0.0)
        sbc = self._num(self.cashflow, "Stock Based Compensation", 0.0)
        onc = self._num(self.cashflow, "Other Non Cash Items", 0.0)
        wc = self._num(self.cashflow, "Change in Working Capital", 0.0)
        return ni + da + sbc + onc + wc

    def Free_Cash_Flow(self) -> float:
        fcf_direct = self._num(self.cashflow, "Free Cash Flow", 0.0)
        if fcf_direct != 0:
            return fcf_direct
        ocf = self.Operating_Cash_Flow()
        capex = self._num(self.cashflow, "Capital Expenditure", 0.0)
        return ocf + capex

    def unlevered_free_cash_flow(self) -> float:
        op_inc = self._num(self.income, "Operating Income", 0.0)
        da = self._num(self.income, "Depreciation and Amortization", 0.0)
        capex = self._num(self.cashflow, "Capital Expenditure", 0.0)
        wc = self._num(self.cashflow, "Change in Working Capital", 0.0)
        return op_inc * (1 - TAX_RATE) + da + capex - wc

    # ================= Growth ================= #

    def growth_rate_cagr(self, start: float, end: float, years: int) -> float:
        if start is None or end is None or start <= 0 or end <= 0 or years <= 0:
            return 0.0
        try:
            return float(np.power(end / start, 1 / years) - 1)
        except Exception:
            return 0.0

    # ================= DCF (Vectorized) ================= #

    def dcf_model_multiyear(self, ufcf_series: List[float], years: int = 10) -> np.ndarray:
        ufcf = np.array([float(x) for x in ufcf_series if x is not None], dtype=float)
        if len(ufcf) == 0:
            raise ValueError("UFCF series ว่าง")

        wacc = self.wacc()
        if wacc <= 0:
            wacc = 0.10

        if len(ufcf) < years:
            if len(ufcf) >= 2:
                g = self.growth_rate_cagr(ufcf[0], ufcf[-1], len(ufcf) - 1)
            else:
                g = 0.05
            last = ufcf[-1]
            extra = []
            for _ in range(years - len(ufcf)):
                last = last * (1 + g)
                extra.append(last)
            ufcf = np.concatenate([ufcf, np.array(extra)])

        ufcf = ufcf[:years]

        t = np.arange(1, years + 1)
        discount_factor = np.power(1 + wacc, t)
        discounted = ufcf / discount_factor

        g = self.growth_rate_cagr(ufcf[0], ufcf[-1], years)
        g = min(max(g, -0.05), wacc - 0.01)
        terminal = (ufcf[-1] * (1 + g)) / (wacc - g)
        terminal_discounted = terminal / np.power(1 + wacc, years)

        return np.append(discounted, terminal_discounted)

    # ⭐ FIXED METHOD
    def intrinsic_value_per_share(self, ufcf_series: List[float]) -> Optional[float]:
        """
        Equity Value / shares outstanding.

        🔴 OLD BUG: ถ้าหาคีย์ shares ไม่เจอ → ใช้ fallback 1.0 →
                    ค่ามหาศาล → frontend guard → แสดง $0.00 หลอกผู้ใช้

        ✅ NEW: ถ้าหาไม่เจอ คืน None ตรงๆ ให้ caller รู้ว่าควรแสดง "N/A"
        """
        dcf = self.dcf_model_multiyear(ufcf_series)
        equity_value = float(dcf.sum())

        shares = self._get_shares_outstanding()
        if shares is None or shares <= 0:
            # ❌ ไม่ใช้ fallback 1.0 อีกแล้ว → ให้ caller รู้ว่าหาไม่เจอ
            return None

        return round(equity_value / shares, 2)

    # ⭐ NEW: Full DCF result สำหรับ UI (ตรงกับที่ screenshot แสดง)
    def dcf_full_result(
        self,
        ufcf_series: List[float],
        years: int = 10,
        terminal_growth: float = 0.025,
    ) -> Dict:
        """
        Return ข้อมูลครบสำหรับ render หน้า DCF Valuation ใน UI:
            intrinsic_value / share, equity_value, terminal_pv,
            wacc, terminal_growth, sector, shares_out, 10-year forecast
        """
        wacc = self.wacc()
        if wacc <= 0:
            wacc = 0.10

        ufcf = np.array([float(x) for x in ufcf_series if x is not None], dtype=float)
        if len(ufcf) == 0:
            return self._dcf_empty("UFCF series empty")

        # Extrapolate ถ้าไม่ครบ
        if len(ufcf) < years:
            if len(ufcf) >= 2:
                g0 = self.growth_rate_cagr(ufcf[0], ufcf[-1], len(ufcf) - 1)
            else:
                g0 = 0.05
            last = ufcf[-1]
            extra = []
            for _ in range(years - len(ufcf)):
                last = last * (1 + g0)
                extra.append(last)
            ufcf = np.concatenate([ufcf, np.array(extra)])

        ufcf = ufcf[:years]

        # Per-year FCF + PV
        t = np.arange(1, years + 1)
        discount = np.power(1 + wacc, t)
        pvs = ufcf / discount

        # Terminal
        if wacc <= terminal_growth:
            return self._dcf_empty(
                f"WACC ({wacc:.2%}) must exceed terminal growth ({terminal_growth:.2%})"
            )
        terminal_value = (ufcf[-1] * (1 + terminal_growth)) / (wacc - terminal_growth)
        terminal_pv = terminal_value / (1 + wacc) ** years

        equity_value = float(pvs.sum() + terminal_pv)

        shares = self._get_shares_outstanding()
        intrinsic = round(equity_value / shares, 2) if (shares and shares > 0) else None

        forecast = [
            {
                "year": int(yr),
                "fcf":  round(float(fcf), 2),
                "pv":   round(float(pv), 2),
            }
            for yr, fcf, pv in zip(t, ufcf, pvs)
        ]

        return {
            "intrinsic_value_per_share": intrinsic,  # None = แสดง "N/A"
            "equity_value":              round(equity_value, 2),
            "terminal_value_pv":         round(float(terminal_pv), 2),
            "wacc":                      round(wacc, 4),
            "terminal_growth":           terminal_growth,
            "shares_out":                round(shares, 2) if shares else 0.0,
            "shares_out_resolved":       shares is not None,
            "forecast":                  forecast,
        }

    @staticmethod
    def _dcf_empty(note: str) -> Dict:
        return {
            "intrinsic_value_per_share": None,
            "equity_value":  None,
            "terminal_value_pv": None,
            "wacc": None,
            "terminal_growth": None,
            "shares_out": 0.0,
            "shares_out_resolved": False,
            "forecast": [],
            "note": note,
        }
    
    # CashFlowModel.py — Additional Functions Patch
        # เพิ่มฟังก์ชั้นไหม่
   