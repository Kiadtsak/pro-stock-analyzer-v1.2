"""
Intrinsic Value — 10 formulas.

Multiple valuation methods:
  - DCF (two-stage: high growth + fade + terminal)
  - Graham Number
  - Ten Cap (Buffett's rule of thumb)
  - Reverse DCF (implied growth from current price)
  - Dividend Discount Model
"""
from __future__ import annotations

import math

from backend.ratios.base import RatioBase, get, sdiv, sround
from backend.ratios.cost_of_capital import (
    EQUITY_RISK_PREMIUM,
    RISK_FREE_RATE,
    SECTOR_BETAS,
)

# Sector-tiered terminal growth
TERMINAL_GROWTH = {
    "Technology": 0.030,
    "Healthcare": 0.028,
    "Consumer Defensive": 0.023,
    "Consumer Cyclical": 0.025,
    "Financial Services": 0.025,
    "Industrials": 0.025,
    "Utilities": 0.020,
    "Energy": 0.020,
    "Basic Materials": 0.022,
    "Real Estate": 0.022,
    "Communication Services": 0.025,
}


class IntrinsicValueRatios(RatioBase):
    category = "intrinsic_value"
    description = "DCF, Graham, Ten Cap valuations"

    def compute(self) -> dict[str, float | None]:
        price = self._price()
        shares = self._shares() or 0
        eps = self._eps()
        bvps = sdiv(self._total_equity(), shares)
        fcf = self._fcf()
        ocf = self._ocf()
        ni = self._net_income()
        div = self._dividends_paid()
        sector = self.basic_info.get("Sector", "")

        beta = SECTOR_BETAS.get(sector, 1.0)
        cost_equity = RISK_FREE_RATE + beta * EQUITY_RISK_PREMIUM
        tg = TERMINAL_GROWTH.get(sector, 0.025)

        # ── DCF (two-stage, 5+5+terminal) ───────────────
        dcf_iv = self._dcf(fcf, shares, cost_equity, tg,
                           high_growth=0.10, high_years=5, fade_years=5)

        # Owner Earnings-based DCF
        owner_earnings = None
        if ni is not None:
            owner_earnings = ni + (self._da() or 0) - ((self._capex() or 0) * 0.7)
        oe_dcf = self._dcf(owner_earnings, shares, cost_equity, tg,
                           high_growth=0.10, high_years=5, fade_years=5)

        # ── Graham Number ───────────────────────────────
        # IV = sqrt(22.5 × EPS × BVPS)
        graham = None
        if eps and bvps and eps > 0 and bvps > 0:
            graham = math.sqrt(22.5 * eps * bvps)

        # ── Graham (Revised): EPS × (8.5 + 2g) ─────────
        # Uses EPS growth rate
        prev_eps = get(self.prev_income, "EPS", "Earnings Per Share")
        g_pct = None
        if eps and prev_eps and prev_eps > 0:
            g_pct = ((eps - prev_eps) / prev_eps) * 100
        graham_revised = None
        if eps and g_pct is not None and eps > 0:
            graham_revised = eps * (8.5 + 2 * min(g_pct, 20))   # cap growth at 20%

        # ── Ten Cap (Rule of 20/25) ─────────────────────
        # Buffett approx: IV = Owner Earnings × 10
        ten_cap = None
        if owner_earnings and shares:
            ten_cap = (owner_earnings * 10) / shares

        # ── Dividend Discount Model (Gordon Growth) ─────
        ddm = self._ddm(div, shares, cost_equity, tg)

        # ── Margin of Safety ────────────────────────────
        # MoS vs DCF
        mos_dcf = None
        if dcf_iv and price and dcf_iv > 0:
            mos_dcf = (dcf_iv - price) / dcf_iv

        mos_graham = None
        if graham and price:
            mos_graham = (graham - price) / graham

        # ── Reverse DCF (implied growth) ────────────────
        implied_g = self._reverse_dcf(price, fcf, shares, cost_equity, tg)

        return {
            "Intrinsic Value (DCF)": sround(dcf_iv, 2),
            "Intrinsic Value (Owner Earnings DCF)": sround(oe_dcf, 2),
            "Intrinsic Value (Graham Number)": sround(graham, 2),
            "Intrinsic Value (Graham Revised)": sround(graham_revised, 2),
            "Intrinsic Value (Ten Cap)": sround(ten_cap, 2),
            "Intrinsic Value (DDM)": sround(ddm, 2),
            "Margin of Safety (DCF)": sround(mos_dcf, 4),
            "Margin of Safety (Graham)": sround(mos_graham, 4),
            "Implied Growth (Reverse DCF)": sround(implied_g, 4),

            # Cross-checks
            "DCF vs Current Price": sround(sdiv(dcf_iv, price)),
            "Assumptions_Cost_of_Equity": round(cost_equity * 100, 3),
            "Assumptions_Terminal_Growth": round(tg * 100, 3),
        }

    def _dcf(
        self,
        starting_cf: float | None, shares: float, wacc: float, terminal_g: float,
        high_growth: float = 0.10, high_years: int = 5, fade_years: int = 5,
    ) -> float | None:
        """Two-stage DCF returning intrinsic value per share."""
        if not starting_cf or starting_cf <= 0 or shares <= 0:
            return None
        if wacc <= terminal_g:
            return None

        # Stage 1: high growth
        cf = starting_cf
        cash_flows = []
        for _ in range(high_years):
            cf *= (1 + high_growth)
            cash_flows.append(cf)

        # Stage 2: fade to terminal growth
        step = (high_growth - terminal_g) / max(fade_years, 1)
        g = high_growth
        for _ in range(fade_years):
            g -= step
            cf *= (1 + g)
            cash_flows.append(cf)

        # PV of cash flows
        pv = 0.0
        for i, c in enumerate(cash_flows, start=1):
            pv += c / ((1 + wacc) ** i)

        # Terminal value
        terminal_cf = cash_flows[-1] * (1 + terminal_g)
        tv = terminal_cf / (wacc - terminal_g)
        pv_tv = tv / ((1 + wacc) ** len(cash_flows))

        enterprise_value = pv + pv_tv

        # Equity value = EV + Cash - Debt
        cash = self._cash() or 0
        debt = self._total_debt() or 0
        equity_value = enterprise_value + cash - debt

        return equity_value / shares

    def _ddm(
        self, dividend: float | None, shares: float,
        cost_equity: float, growth: float,
    ) -> float | None:
        """Gordon Growth DDM: IV = D1 / (r - g)."""
        if not dividend or not shares:
            return None
        if cost_equity <= growth:
            return None
        dps = dividend / shares
        d1 = dps * (1 + growth)
        return d1 / (cost_equity - growth)

    def _reverse_dcf(
        self, price: float | None, fcf: float | None, shares: float,
        wacc: float, terminal_g: float,
    ) -> float | None:
        """
        Solve for growth rate that makes DCF = current price.
        Binary search.
        """
        if not (price and fcf and shares and fcf > 0):
            return None

        low, high = -0.2, 0.4  # -20% to 40% growth
        for _ in range(60):   # 60 iterations = high precision
            mid = (low + high) / 2
            iv = self._dcf(fcf, shares, wacc, terminal_g,
                           high_growth=mid, high_years=5, fade_years=5)
            if iv is None:
                return None
            if abs(iv - price) < 0.01:
                return mid
            if iv > price:
                high = mid
            else:
                low = mid
        return (low + high) / 2
