"""
Semiconductor / AI Industry Ratios — 8 formulas.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround


class SemiconductorRatios(RatioBase):
    category = "semiconductor"
    description = "Semi/AI industry-specific"

    def compute(self) -> dict[str, float | None]:
        industry = str(self.basic_info.get("Industry", "")).lower()
        is_semi = "semi" in industry or "chip" in industry

        rev = self._revenue()
        rd = get(self.income, "Research and Development",
                 "Research and Development Expenses",
                 "R&D Expenses", "R&D")
        inv = self._inventory()
        cogs = self._cogs()
        capex = self._capex()

        # Inventory days for semi (critical due to cycle)
        inv_days = None
        if cogs and cogs > 0 and inv is not None:
            inv_days = (inv / cogs) * 365

        # Emp / employees
        emp = get(self.basic_info, "Employees", "FullTimeEmployees")

        return {
            "_is_semi": 1 if is_semi else 0,
            "Gross Margin (Semi)": spct(sdiv(self._gross_profit(), rev)),
            "R&D as % Revenue": spct(sdiv(rd, rev)),
            "R&D Intensity (Absolute)": sround(rd, 2),
            "Revenue per Employee": sround(sdiv(rev, emp), 2),
            "Inventory Days": sround(inv_days, 1),
            "Inventory to Revenue": spct(sdiv(inv, rev)),
            "CapEx Intensity": spct(sdiv(capex, rev)),      # semis are capex-heavy
            "Fab Investment (approx)": sround(capex, 2),
        }
