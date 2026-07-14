"""
Liquidity Ratios — 10 formulas.

Measures ability to meet short-term obligations.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, sround


class LiquidityRatios(RatioBase):
    category = "liquidity"
    description = "Short-term obligation coverage"

    def compute(self) -> dict[str, float | None]:
        ca = self._current_assets()
        cl = self._current_liabilities()
        cash = self._cash()
        inv = self._inventory()
        recv = self._receivables()
        short_term_inv = get(self.balance, "Short Term Investments",
                             "Marketable Securities")

        # Quick assets = cash + short-term investments + receivables
        quick_assets = None
        if cash is not None and recv is not None:
            quick_assets = cash + (short_term_inv or 0) + recv

        # Alt formulation: current assets minus inventory
        quick_alt = None
        if ca is not None and inv is not None:
            quick_alt = ca - inv

        # Defensive interval = liquid assets / daily operating expense
        op_exp = self._revenue()
        if op_exp is not None:
            daily_op = op_exp / 365
        else:
            daily_op = None

        # NWC (Net Working Capital)
        nwc = None if (ca is None or cl is None) else ca - cl

        return {
            "Current Ratio": sround(sdiv(ca, cl)),
            "Quick Ratio (Acid Test)": sround(sdiv(quick_assets, cl)),
            "Quick Ratio (Alt)": sround(sdiv(quick_alt, cl)),
            "Cash Ratio": sround(sdiv(cash, cl)),
            "Absolute Liquidity Ratio": sround(sdiv(
                (cash or 0) + (short_term_inv or 0), cl)),
            "Operating Cash Flow Ratio": sround(sdiv(self._ocf(), cl)),
            "Defensive Interval": sround(sdiv(quick_assets, daily_op), 1),
            "Net Working Capital": sround(nwc, 2),
            "NWC to Assets": sround(sdiv(nwc, self._total_assets())),
            "NWC to Sales": sround(sdiv(nwc, self._revenue())),
        }
