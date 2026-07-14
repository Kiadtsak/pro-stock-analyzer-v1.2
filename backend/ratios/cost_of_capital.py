"""
Cost of Capital — 8 formulas.

WACC, Cost of Equity (CAPM), Cost of Debt.

Uses sector-tiered defaults for beta and equity risk premium.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv

# Default assumptions (can be overridden per company)
RISK_FREE_RATE = 0.045       # US 10Y Treasury (Jun 2026 approx)
EQUITY_RISK_PREMIUM = 0.055  # Long-term US market premium
TAX_RATE = 0.21

# Sector beta defaults (Damodaran-style approximations)
SECTOR_BETAS = {
    "Technology": 1.20,
    "Healthcare": 0.90,
    "Consumer Defensive": 0.65,
    "Consumer Cyclical": 1.15,
    "Financial Services": 1.10,
    "Industrials": 1.05,
    "Utilities": 0.55,
    "Energy": 1.25,
    "Basic Materials": 1.15,
    "Real Estate": 0.80,
    "Communication Services": 1.00,
}


class CostOfCapitalRatios(RatioBase):
    category = "cost_of_capital"
    description = "WACC, Cost of Equity, Cost of Debt"

    def compute(self) -> dict[str, float | None]:
        sector = self.basic_info.get("Sector", "")
        beta = SECTOR_BETAS.get(sector, 1.0)

        # ── Cost of Equity (CAPM) ───────────────────────
        cost_equity = RISK_FREE_RATE + beta * EQUITY_RISK_PREMIUM

        # ── Cost of Debt ────────────────────────────────
        interest = self._interest_expense()
        debt = self._total_debt()
        prev_debt = get(self.prev_balance, "Total Debt") or debt or 0
        avg_debt = None if (debt is None or prev_debt is None) else (debt + prev_debt) / 2

        cost_debt_pretax = sdiv(interest, avg_debt)
        cost_debt_after_tax = None
        if cost_debt_pretax is not None:
            cost_debt_after_tax = cost_debt_pretax * (1 - TAX_RATE)

        # ── WACC = (E/V)*Re + (D/V)*Rd*(1-T) ────────────
        equity = self._total_equity() or 0
        debt = debt or 0
        total_cap = equity + debt

        wacc = None
        if total_cap > 0 and cost_debt_after_tax is not None:
            wacc = (equity / total_cap) * cost_equity + (debt / total_cap) * cost_debt_after_tax
        elif total_cap > 0:
            wacc = cost_equity  # no debt case
        # If no equity data, fall back to pure cost of equity
        elif cost_equity is not None:
            wacc = cost_equity

        return {
            "Risk-Free Rate": round(RISK_FREE_RATE * 100, 4),           # %
            "Beta (Sector)": beta,
            "Equity Risk Premium": round(EQUITY_RISK_PREMIUM * 100, 4),
            "Cost of Equity (CAPM)": round(cost_equity * 100, 4),
            "Cost of Debt (Pre-Tax)": None if cost_debt_pretax is None else round(cost_debt_pretax * 100, 4),
            "Cost of Debt (After-Tax)": None if cost_debt_after_tax is None else round(cost_debt_after_tax * 100, 4),
            "WACC": None if wacc is None else round(wacc * 100, 4),
            "Effective Tax Rate": self._effective_tax(),
        }

    def _effective_tax(self) -> float | None:
        pretax = get(self.income, "Income Before Tax", "Pretax Income")
        tax = get(self.income, "Income Tax Expense", "Tax Expense", "Provision for Income Taxes")
        r = sdiv(tax, pretax)
        return None if r is None else round(r * 100, 4)
