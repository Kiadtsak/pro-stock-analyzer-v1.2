"""
Growth Ratios — 14 formulas.

Year-over-year growth in key line items.
Uses prev_income, prev_balance, prev_cashflow (previous year data).
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, spct


def _growth(current: float | None, prev: float | None) -> float | None:
    """YoY growth = (current - prev) / abs(prev). Handles negatives."""
    if current is None or prev is None:
        return None
    if prev == 0:
        return None
    return (current - prev) / abs(prev)


class GrowthRatios(RatioBase):
    category = "growth"
    description = "Year-over-year growth in key metrics"

    def compute(self) -> dict[str, float | None]:
        # Current year
        rev = self._revenue()
        ni = self._net_income()
        eps = self._eps()
        oi = self._operating_income()
        ebitda = self._ebitda()
        gp = self._gross_profit()
        fcf = self._fcf()
        ocf = self._ocf()
        equity = self._total_equity()
        assets = self._total_assets()
        book_value = equity
        dividends = self._dividends_paid()

        # Previous year — reconstruct via prev_* attrs
        prev_rev = get(self.prev_income, "Revenue", "Total Revenue", "Sales")
        prev_ni = get(self.prev_income, "Net Income", "Net Income Loss")
        prev_eps = get(self.prev_income, "Earnings Per Share", "EPS")
        prev_oi = get(self.prev_income, "Operating Income", "EBIT")
        prev_ebitda = get(self.prev_income, "EBITDA")
        prev_gp = get(self.prev_income, "Gross Profit")
        prev_fcf = get(self.prev_cashflow, "Free Cash Flow")
        prev_ocf = get(self.prev_cashflow, "Operating Cash Flow",
                       "Cash From Operations")
        prev_equity = get(self.prev_balance, "Total Equity", "Stockholders Equity",
                          "Total Shareholder Equity")
        prev_assets = get(self.prev_balance, "Total Assets")
        prev_div = get(self.prev_cashflow, "Dividends Paid")
        if prev_div is not None:
            prev_div = abs(prev_div)

        return {
            "Revenue Growth YoY": spct(_growth(rev, prev_rev)),
            "Net Income Growth YoY": spct(_growth(ni, prev_ni)),
            "EPS Growth YoY": spct(_growth(eps, prev_eps)),
            "Operating Income Growth YoY": spct(_growth(oi, prev_oi)),
            "EBITDA Growth YoY": spct(_growth(ebitda, prev_ebitda)),
            "Gross Profit Growth YoY": spct(_growth(gp, prev_gp)),
            "FCF Growth YoY": spct(_growth(fcf, prev_fcf)),
            "OCF Growth YoY": spct(_growth(ocf, prev_ocf)),
            "Equity (Book Value) Growth YoY": spct(_growth(equity, prev_equity)),
            "Asset Growth YoY": spct(_growth(assets, prev_assets)),
            "Dividend Growth YoY": spct(_growth(dividends, prev_div)),

            # Composite growth
            "Sustainable Growth Rate": self._sgr(ni, equity, dividends),
            "Internal Growth Rate": self._igr(ni, assets, dividends),

            # Reinvestment rate (used in Buffett quality analysis) — as percentage
            "Retention Ratio": spct(self._retention(ni, dividends)),
        }

    def _sgr(self, ni, equity, div) -> float | None:
        """Sustainable Growth Rate = ROE × Retention Ratio."""
        if ni is None or equity is None or equity == 0:
            return None
        roe = ni / equity
        ret = self._retention(ni, div)
        if ret is None:
            return None
        return spct(roe * ret)

    def _igr(self, ni, assets, div) -> float | None:
        """Internal Growth Rate = ROA × Retention Ratio."""
        if ni is None or assets is None or assets == 0:
            return None
        roa = ni / assets
        ret = self._retention(ni, div)
        if ret is None:
            return None
        return spct(roa * ret)

    def _retention(self, ni, div) -> float | None:
        """1 - (Dividends / Net Income)."""
        if ni is None or ni == 0:
            return None
        return 1 - ((div or 0) / ni)
