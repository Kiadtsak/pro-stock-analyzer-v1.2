"""
Cash Flow Ratios — 18 formulas.

Analyzes cash generation quality, coverage, and reinvestment.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround


class CashFlowRatios(RatioBase):
    category = "cash_flow"
    description = "Cash generation, coverage, quality"

    def compute(self) -> dict[str, float | None]:
        rev = self._revenue()
        ni = self._net_income()
        ebitda = self._ebitda()
        ocf = self._ocf()
        capex = self._capex() or 0
        fcf = self._fcf()

        # Unlevered FCF (approx) = EBIT × (1-tax) + D&A - CapEx - ΔWC
        ebit = self._ebit() or 0
        da = self._da() or 0
        change_wc = get(self.cashflow, "Change in Working Capital",
                        "Changes in Working Capital") or 0
        ufcf = None
        if ebit:
            ufcf = ebit * (1 - 0.21) + da - capex - change_wc

        # Owner Earnings (Buffett) = NI + D&A - Maintenance CapEx
        # Approximation: use full CapEx or 70% of it as maintenance
        maint_capex = capex * 0.7 if capex else 0
        owner_earnings = None
        if ni is not None:
            owner_earnings = ni + da - maint_capex

        total_debt = self._total_debt() or 0
        equity = self._total_equity() or 0
        assets = self._total_assets() or 0

        # Dividends & buybacks
        div = self._dividends_paid() or 0
        buyback = get(self.cashflow, "Common Stock Repurchased",
                      "Stock Repurchases") or 0
        buyback = abs(buyback)
        total_return_cash = div + buyback

        return {
            # ── Cash flow generation ────────────────────
            "Operating Cash Flow (OCF)": sround(ocf, 2),
            "Free Cash Flow (FCF)": sround(fcf, 2),
            "Unlevered Free Cash Flow (UFCF)": sround(ufcf, 2),
            "Owner Earnings (Buffett)": sround(owner_earnings, 2),

            # ── Margins ─────────────────────────────────
            "OCF Margin": spct(sdiv(ocf, rev)),
            "FCF Margin": spct(sdiv(fcf, rev)),
            "UFCF Margin": spct(sdiv(ufcf, rev)),

            # ── Quality metrics ─────────────────────────
            "Cash Conversion Ratio": sround(sdiv(fcf, ni)),      # >1 = high quality
            "OCF to Net Income": sround(sdiv(ocf, ni)),          # >1 = clean earnings
            "OCF to EBITDA": sround(sdiv(ocf, ebitda)),
            "Accrual Ratio": sround(sdiv(
                (ni or 0) - (ocf or 0), assets)),            # low = high quality

            # ── Coverage ratios ─────────────────────────
            "OCF to Current Liabilities": sround(sdiv(ocf, self._current_liabilities())),
            "OCF to Total Debt": sround(sdiv(ocf, total_debt)),
            "FCF to Total Debt": sround(sdiv(fcf, total_debt)),
            "FCF Yield (to Equity)": sround(sdiv(fcf, equity)),

            # ── Reinvestment intensity ──────────────────
            "CapEx to OCF": sround(sdiv(capex, ocf)),
            "CapEx to Revenue": sround(sdiv(capex, rev)),
            "CapEx to Depreciation": sround(sdiv(capex, da)),   # >1 = growth investing

            # ── Shareholder return ──────────────────────
            "Dividends to OCF": sround(sdiv(div, ocf)),
            "Dividends to FCF": sround(sdiv(div, fcf)),
            "Buybacks to FCF": sround(sdiv(buyback, fcf)),
            "Total Shareholder Return to FCF": sround(sdiv(total_return_cash, fcf)),
        }
