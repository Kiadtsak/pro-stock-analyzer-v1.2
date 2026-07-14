"""
Leverage Ratios — 15 formulas.

Measures debt structure, financial risk, and ability to service debt.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, sround


class LeverageRatios(RatioBase):
    category = "leverage"
    description = "Debt structure and coverage"

    def compute(self) -> dict[str, float | None]:
        total_debt = self._total_debt()
        long_term_debt = get(self.balance, "Long Term Debt")
        short_term_debt = get(self.balance, "Short Term Debt", "Current Debt")
        total_assets = self._total_assets()
        total_equity = self._total_equity()
        total_liab = self._total_liabilities()
        ebit = self._ebit()
        ebitda = self._ebitda()
        ni = self._net_income()
        interest = self._interest_expense()
        ocf = self._ocf()

        # Debt service = principal + interest (approx)
        debt_service = None
        if interest is not None and short_term_debt is not None:
            debt_service = interest + short_term_debt

        # Net debt = total debt - cash
        cash = self._cash() or 0
        net_debt = None if total_debt is None else total_debt - cash

        return {
            # ── Debt structure ──────────────────────────
            "Debt to Equity (D/E)": sround(sdiv(total_debt, total_equity)),
            "Debt to Assets (D/A)": sround(sdiv(total_debt, total_assets)),
            "Long Term Debt to Equity": sround(sdiv(long_term_debt, total_equity)),
            "Long Term Debt to Assets": sround(sdiv(long_term_debt, total_assets)),
            "Short Term Debt to Total Debt": sround(sdiv(short_term_debt, total_debt)),
            "Total Liabilities to Equity": sround(sdiv(total_liab, total_equity)),
            "Equity Multiplier": sround(sdiv(total_assets, total_equity)),
            "Equity Ratio": sround(sdiv(total_equity, total_assets)),
            "Financial Leverage": sround(sdiv(total_assets, total_equity)),

            # ── Coverage ratios ─────────────────────────
            "Interest Coverage (EBIT)": sround(sdiv(ebit, interest)),
            "Interest Coverage (EBITDA)": sround(sdiv(ebitda, interest)),
            "Cash Interest Coverage": sround(sdiv(ocf, interest)),
            "Debt Service Coverage Ratio (DSCR)": sround(sdiv(
                self._operating_income(), debt_service)),
            "Fixed Charge Coverage": sround(sdiv(
                (ebit or 0) + (get(self.income, "Lease Cost", "Rent Expense") or 0),
                (interest or 0) + (get(self.income, "Lease Cost", "Rent Expense") or 0))),

            # ── Net debt metrics ────────────────────────
            "Net Debt": sround(net_debt, 2),
            "Net Debt to EBITDA": sround(sdiv(net_debt, ebitda)),
            "Net Debt to Equity": sround(sdiv(net_debt, total_equity)),
            "Debt to EBITDA": sround(sdiv(total_debt, ebitda)),

            # ── Solvency ────────────────────────────────
            "Times Interest Earned": sround(sdiv(ebit, interest)),
            "Cash Flow to Debt": sround(sdiv(ocf, total_debt)),
        }
