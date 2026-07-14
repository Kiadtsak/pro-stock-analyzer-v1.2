"""
REIT Ratios — 10 formulas.

Real Estate Investment Trust-specific metrics:
FFO, AFFO, NAV, Cap Rate, Occupancy.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround


class REITRatios(RatioBase):
    category = "reit"
    description = "REIT-specific metrics (FFO, AFFO, NAV)"

    def compute(self) -> dict[str, float | None]:
        industry = str(self.basic_info.get("Industry", "")).lower()
        sector = str(self.basic_info.get("Sector", "")).lower()
        is_reit = "reit" in industry or "real estate" in sector

        ni = self._net_income()
        da = self._da() or 0

        # Real estate specific
        gains_on_sales = get(self.income, "Gain on Sale of Real Estate",
                             "Gain on Sale of Properties") or 0
        real_estate_da = get(self.income, "Real Estate Depreciation") or da

        # FFO = Net Income + Real Estate D&A - Gains on Sales
        ffo = None
        if ni is not None:
            ffo = ni + real_estate_da - gains_on_sales

        # AFFO = FFO - Maintenance CapEx - Straight-line rent adjustments
        maint_capex = (self._capex() or 0) * 0.5   # approx maintenance
        sl_rent = get(self.income, "Straight-Line Rent Adjustment") or 0
        affo = None
        if ffo is not None:
            affo = ffo - maint_capex - sl_rent

        shares = self._shares()
        price = self._price()

        # Property values
        total_props = get(self.balance, "Real Estate Properties",
                          "Investment in Real Estate")

        return {
            "_is_reit": 1 if is_reit else 0,
            "Funds From Operations (FFO)": sround(ffo, 2),
            "Adjusted FFO (AFFO)": sround(affo, 2),
            "FFO Per Share": sround(sdiv(ffo, shares), 3),
            "AFFO Per Share": sround(sdiv(affo, shares), 3),
            "P/FFO Multiple": sround(sdiv(price, sdiv(ffo, shares))),
            "P/AFFO Multiple": sround(sdiv(price, sdiv(affo, shares))),
            "FFO Yield": spct(sdiv(sdiv(ffo, shares), price)),
            "AFFO Payout Ratio": spct(sdiv(self._dividends_paid(), affo)),
            "Debt to Real Estate Value": spct(sdiv(self._total_debt(), total_props)),
            "FFO Growth YoY": self._ffo_growth(ffo),
        }

    def _ffo_growth(self, current_ffo) -> float | None:
        if current_ffo is None:
            return None
        prev_ni = get(self.prev_income, "Net Income")
        prev_da = get(self.prev_income, "Real Estate Depreciation") or \
                  get(self.prev_cashflow, "Depreciation and Amortization") or 0
        prev_gains = get(self.prev_income, "Gain on Sale of Real Estate") or 0
        prev_ffo = None
        if prev_ni is not None:
            prev_ffo = prev_ni + prev_da - prev_gains
        if not prev_ffo or prev_ffo == 0:
            return None
        return spct((current_ffo - prev_ffo) / abs(prev_ffo))
