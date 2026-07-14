"""
Profitability Ratios — 22 formulas.

Measures the company's ability to generate profit from operations,
assets, and equity.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround

TAX_RATE = 0.21     # US corporate tax rate (default)


class ProfitabilityRatios(RatioBase):
    category = "profitability"
    description = "Measures ability to generate profit"

    def compute(self) -> dict[str, float | None]:
        rev = self._revenue()
        cogs = self._cogs()
        gp = self._gross_profit()
        oi = self._operating_income()
        ebit = self._ebit()
        ebitda = self._ebitda()
        ni = self._net_income()

        assets_avg = self._avg_assets()
        equity_avg = self._avg_equity()
        debt = self._total_debt() or 0
        cash = self._cash() or 0

        # NOPAT = EBIT × (1 - Tax)
        nopat = None if ebit is None else ebit * (1 - TAX_RATE)
        invested_capital = None
        if equity_avg is not None:
            invested_capital = equity_avg + debt - cash

        # Extended metrics
        interest = self._interest_expense() or 0
        capex = self._capex() or 0
        rd = get(self.income, "Research and Development",
                 "Research and Development Expenses",
                 "R&D Expenses", "Research Development", "R&D")

        return {
            # ── Margin ratios (as percentages) ──────────
            "Gross Profit Margin": spct(sdiv(gp, rev)),
            "Operating Profit Margin": spct(sdiv(oi, rev)),
            "EBIT Margin": spct(sdiv(ebit, rev)),
            "EBITDA Margin": spct(sdiv(ebitda, rev)),
            "Net Profit Margin": spct(sdiv(ni, rev)),
            "Pre-Tax Margin": spct(sdiv(
                get(self.income, "Income Before Tax", "Pretax Income"), rev)),
            "SG&A Margin": spct(sdiv(
                get(self.income, "Selling General and Administrative",
                    "SG&A Expenses"), rev)),
            "R&D Margin": spct(sdiv(rd, rev)),

            # ── Returns ─────────────────────────────────
            "ROE": spct(sdiv(ni, equity_avg)),
            "ROA": spct(sdiv(ni, assets_avg)),
            "ROIC": spct(sdiv(nopat, invested_capital)),
            "ROCE": spct(sdiv(ebit, invested_capital)),   # Return on Capital Employed
            "Return on Sales (ROS)": spct(sdiv(oi, rev)),
            "Return on Revenue (RoR)": spct(sdiv(ni, rev)),

            # ── Cash-based profitability ────────────────
            "Cash ROA": spct(sdiv(self._ocf(), assets_avg)),
            "Cash Return on Equity": spct(sdiv(self._ocf(), equity_avg)),
            "FCF Return on Assets": spct(sdiv(self._fcf(), assets_avg)),
            "FCF Return on Equity": spct(sdiv(self._fcf(), equity_avg)),

            # ── Component metrics (absolute) ────────────
            "NOPAT": sround(nopat, 2),
            "EBIT": sround(ebit, 2),
            "EBITDA": sround(ebitda, 2),
            "Invested Capital": sround(invested_capital, 2),

            # ── Efficiency of profit conversion ─────────
            "Effective Tax Rate": spct(sdiv(
                get(self.income, "Income Tax Expense", "Tax Expense"),
                get(self.income, "Income Before Tax", "Pretax Income"))),
        }
