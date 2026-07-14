"""
Insurance Ratios — 8 formulas.

Insurance-specific: Combined Ratio, Loss Ratio, Solvency.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct


class InsuranceRatios(RatioBase):
    category = "insurance"
    description = "Insurance-specific (Combined Ratio, Loss Ratio)"

    def compute(self) -> dict[str, float | None]:
        industry = str(self.basic_info.get("Industry", "")).lower()
        is_insurance = "insurance" in industry

        # Insurance-specific line items (may not exist for non-insurers)
        premiums = get(self.income, "Premiums Earned", "Net Premiums Earned",
                       "Insurance Premium Revenue")
        claims = get(self.income, "Insurance Losses", "Claims Paid",
                     "Losses and Loss Adjustment")
        underwriting_exp = get(self.income, "Underwriting Expenses",
                               "Insurance Underwriting Expenses")
        investment_income = get(self.income, "Investment Income",
                                "Net Investment Income")

        # Reserves
        reserves = get(self.balance, "Insurance Reserves", "Policy Reserves",
                       "Loss Reserves")
        surplus = self._total_equity()

        loss_ratio = sdiv(claims, premiums)
        expense_ratio = sdiv(underwriting_exp, premiums)
        combined = None
        if loss_ratio is not None and expense_ratio is not None:
            combined = loss_ratio + expense_ratio

        return {
            "_is_insurance": 1 if is_insurance else 0,
            "Loss Ratio": spct(loss_ratio),
            "Expense Ratio": spct(expense_ratio),
            "Combined Ratio": spct(combined),
            "Underwriting Margin": spct(
                None if combined is None else 1 - combined),
            "Investment Yield": spct(sdiv(investment_income, self._total_assets())),
            "Solvency Ratio": spct(sdiv(surplus, premiums)),
            "Reserve to Premium": spct(sdiv(reserves, premiums)),
            "Reserve to Equity": spct(sdiv(reserves, surplus)),
        }
