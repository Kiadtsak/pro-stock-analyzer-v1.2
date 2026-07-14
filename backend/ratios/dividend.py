"""
Dividend Ratios — 10 formulas.

Dividend policy analysis.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround


class DividendRatios(RatioBase):
    category = "dividend"
    description = "Dividend policy analysis"

    def compute(self) -> dict[str, float | None]:
        div = self._dividends_paid()
        shares = self._shares()
        price = self._price()
        ni = self._net_income()
        fcf = self._fcf()
        ocf = self._ocf()
        eps = self._eps()
        equity = self._total_equity()

        dps = sdiv(div, shares)
        prev_div = get(self.prev_cashflow, "Dividends Paid")
        if prev_div is not None:
            prev_div = abs(prev_div)
        prev_shares = get(self.prev_income, "Weighted Average Shares Diluted",
                          "Weighted Average Shares")
        prev_dps = sdiv(prev_div, prev_shares)

        dps_growth = None
        if dps and prev_dps and prev_dps > 0:
            dps_growth = (dps - prev_dps) / prev_dps

        return {
            "Dividends Paid": sround(div, 2),
            "Dividend Per Share (DPS)": sround(dps, 4),
            "Dividend Yield": spct(sdiv(dps, price)),
            "Dividend Payout Ratio": spct(sdiv(div, ni)),
            "Cash Dividend Payout": spct(sdiv(div, fcf)),
            "Dividend Coverage Ratio": sround(sdiv(ni, div)),           # inverse of payout
            "Cash Dividend Coverage": sround(sdiv(fcf, div)),
            "Retention Ratio": self._retention(div, ni),
            "Dividend Growth YoY": spct(dps_growth),
            "Dividend to Equity": spct(sdiv(div, equity)),
        }

    def _retention(self, div, ni) -> float | None:
        if ni is None or ni == 0:
            return None
        return spct(1 - ((div or 0) / ni))
