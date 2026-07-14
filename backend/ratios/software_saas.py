"""
Software / SaaS Ratios — 10 formulas.

SaaS-specific metrics: ARR, NRR, LTV/CAC, Rule of 40, Magic Number.

Note: Many of these require operational data not in standard financials.
We approximate from available data where possible.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround


class SaaSRatios(RatioBase):
    category = "software_saas"
    description = "SaaS metrics (ARR, LTV/CAC, Rule of 40)"

    def compute(self) -> dict[str, float | None]:
        industry = str(self.basic_info.get("Industry", "")).lower()
        is_saas = ("software" in industry or "saas" in industry
                   or "internet" in industry)

        rev = self._revenue()
        prev_rev = get(self.prev_income, "Revenue", "Total Revenue")

        # Growth
        rev_growth = None
        if rev and prev_rev and prev_rev > 0:
            rev_growth = (rev - prev_rev) / prev_rev

        # Approx ARR = latest quarter revenue × 4 (if we had quarterly)
        # From annual: ARR ~ Revenue
        arr = rev

        # Operating expenses breakdown
        sm = get(self.income, "Selling and Marketing", "Sales and Marketing",
                 "S&M Expenses")
        rd = get(self.income, "Research and Development",
                 "Research and Development Expenses",
                 "R&D Expenses", "R&D")
        ga = get(self.income, "General and Administrative")

        # Rule of 40 = Revenue Growth % + Operating Margin %
        op_margin = sdiv(self._operating_income(), rev)
        rule_of_40 = None
        if rev_growth is not None and op_margin is not None:
            rule_of_40 = (rev_growth + op_margin) * 100

        # Magic Number = Net New ARR / S&M spend
        net_new_arr = None
        if rev is not None and prev_rev is not None:
            net_new_arr = rev - prev_rev
        magic_number = sdiv(net_new_arr, sm)

        # Gross Margin (critical for SaaS)
        gm = sdiv(self._gross_profit(), rev)

        return {
            "_is_saas": 1 if is_saas else 0,
            "Estimated ARR": sround(arr, 2),
            "Revenue Growth Rate": spct(rev_growth),
            "SaaS Gross Margin": spct(gm),
            "Operating Margin (SaaS)": spct(op_margin),
            "Rule of 40 Score": sround(rule_of_40, 2),
            "Magic Number": sround(magic_number, 3),
            "S&M as % of Revenue": spct(sdiv(sm, rev)),
            "R&D as % of Revenue": spct(sdiv(rd, rev)),
            "G&A as % of Revenue": spct(sdiv(ga, rev)),
            "Sales Efficiency": sdiv(net_new_arr, sm),
            "R&D Intensity (5Y CAGR)": self._rd_intensity(),
        }

    def _rd_intensity(self) -> float | None:
        if not self.ttm_history or len(self.ttm_history) < 2:
            return None
        rds = []
        for y in self.ttm_history:
            rd = get(y.get("income", {}), "Research and Development",
                     "Research and Development Expenses", "R&D Expenses")
            rev = get(y.get("income", {}), "Revenue", "Total Revenue")
            r = sdiv(rd, rev)
            if r is not None:
                rds.append(r)
        if not rds:
            return None
        return spct(sum(rds) / len(rds))
