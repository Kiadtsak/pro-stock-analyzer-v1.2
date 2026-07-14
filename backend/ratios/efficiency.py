"""
Efficiency Ratios — 18 formulas.

Measures how efficiently the company uses its assets and manages
working capital.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, sdiv, sround


class EfficiencyRatios(RatioBase):
    category = "efficiency"
    description = "Asset utilization and working capital efficiency"

    def compute(self) -> dict[str, float | None]:
        rev = self._revenue()
        cogs = self._cogs()

        assets_avg = self._avg_assets()
        equity_avg = self._avg_equity()
        inv_avg = self._avg_inventory()
        recv_avg = self._avg_receivables()
        pay_avg = self._avg_payables()

        fixed_assets = self._total_assets() and (
            (self._total_assets() or 0) - (self._current_assets() or 0)
        )

        wc = None
        if self._current_assets() is not None and self._current_liabilities() is not None:
            wc = self._current_assets() - self._current_liabilities()

        # Turnover ratios
        asset_turnover = sdiv(rev, assets_avg)
        inv_turnover = sdiv(cogs, inv_avg)
        recv_turnover = sdiv(rev, recv_avg)
        pay_turnover = sdiv(cogs, pay_avg)

        # Days (365 / turnover)
        dio = sdiv(365, inv_turnover) if inv_turnover else None
        dso = sdiv(365, recv_turnover) if recv_turnover else None
        dpo = sdiv(365, pay_turnover) if pay_turnover else None

        # CCC = DIO + DSO - DPO
        ccc = None
        if dio is not None and dso is not None and dpo is not None:
            ccc = dio + dso - dpo

        return {
            # ── Turnover ratios ─────────────────────────
            "Asset Turnover": sround(asset_turnover),
            "Fixed Asset Turnover": sround(sdiv(rev, fixed_assets)),
            "Equity Turnover": sround(sdiv(rev, equity_avg)),
            "Inventory Turnover": sround(inv_turnover),
            "Receivables Turnover": sround(recv_turnover),
            "Payables Turnover": sround(pay_turnover),
            "Working Capital Turnover": sround(sdiv(rev, wc)),

            # ── Days ratios ─────────────────────────────
            "Days Inventory Outstanding (DIO)": sround(dio, 2),
            "Days Sales Outstanding (DSO)": sround(dso, 2),
            "Days Payable Outstanding (DPO)": sround(dpo, 2),
            "Cash Conversion Cycle (CCC)": sround(ccc, 2),

            # ── Efficiency metrics ──────────────────────
            "Revenue per Employee": self._revenue_per_employee(),
            "Sales per Share": sdiv(rev, self._shares()),
            "Capital Intensity": sround(sdiv(assets_avg, rev)),   # inverse of asset turnover
            "Working Capital": sround(wc, 2),
            "Working Capital Ratio": sround(sdiv(wc, self._total_assets())),

            # ── Operating efficiency ────────────────────
            "OCF to Sales": sdiv(self._ocf(), rev),
            "CapEx to Sales": sdiv(self._capex(), rev),
        }

    def _revenue_per_employee(self) -> float | None:
        from backend.ratios.base import get
        emp = get(self.basic_info, "Employees", "FullTimeEmployees")
        return sdiv(self._revenue(), emp)
