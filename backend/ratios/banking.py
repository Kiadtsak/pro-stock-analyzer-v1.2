"""
Banking Ratios — 12 formulas.

Specific to banks — measures capital adequacy, asset quality,
and net interest margin.

Note: Bank financial statements have different line items than
general companies. Some fields may not be present for non-banks.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround


class BankingRatios(RatioBase):
    category = "banking"
    description = "Bank-specific ratios (CAR, NIM, NPL, LDR)"

    def compute(self) -> dict[str, float | None]:
        # Only compute if this looks like a bank
        sector = str(self.basic_info.get("Sector", "")).lower()
        industry = str(self.basic_info.get("Industry", "")).lower()
        is_bank = "bank" in industry or "financial" in sector

        # Common bank line items (may not exist in generic data)
        interest_income = get(self.income, "Interest Income", "Interest Revenue")
        interest_expense = get(self.income, "Interest Expense")
        deposits = get(self.balance, "Deposits", "Total Deposits", "Customer Deposits")
        loans = get(self.balance, "Loans", "Loans and Advances", "Net Loans")
        avg_earning_assets = self._avg_assets()   # simplification
        tier1 = get(self.balance, "Tier 1 Capital", "Common Equity Tier 1")
        rwa = get(self.balance, "Risk Weighted Assets", "RWA")

        # Net Interest Income
        nii = None
        if interest_income is not None:
            nii = interest_income - (interest_expense or 0)

        results = {
            "_is_bank": 1 if is_bank else 0,   # metadata
            "Net Interest Income": sround(nii, 2),
            "Net Interest Margin (NIM)": spct(sdiv(nii, avg_earning_assets)),
            "Loan to Deposit Ratio (LDR)": spct(sdiv(loans, deposits)),
            "Deposit to Assets": spct(sdiv(deposits, self._total_assets())),
            "Loan to Assets": spct(sdiv(loans, self._total_assets())),
            "Interest Income to Total Income": spct(sdiv(interest_income, self._revenue())),
        }

        # Capital adequacy
        if tier1 is not None and rwa is not None:
            results["CET1 Ratio"] = spct(sdiv(tier1, rwa))
            results["Capital Adequacy Ratio (CAR)"] = spct(sdiv(
                tier1 + (get(self.balance, "Tier 2 Capital") or 0), rwa))

        # Efficiency
        op_exp = get(self.income, "Operating Expenses")
        if op_exp is not None:
            results["Cost to Income Ratio"] = spct(sdiv(op_exp, self._revenue()))
            results["Efficiency Ratio"] = spct(sdiv(op_exp,
                (nii or 0) + (get(self.income, "Non-Interest Income") or 0)))

        # Non-performing loans
        npl = get(self.balance, "Non Performing Loans", "NPL")
        if npl is not None and loans:
            results["NPL Ratio"] = spct(sdiv(npl, loans))
            allowance = get(self.balance, "Allowance for Loan Losses",
                            "Provision for Credit Losses")
            if allowance is not None:
                results["NPL Coverage Ratio"] = spct(sdiv(allowance, npl))

        # Return metrics adjusted for banks
        results["ROA (Bank)"] = spct(sdiv(self._net_income(), avg_earning_assets))
        results["ROE (Bank)"] = spct(sdiv(self._net_income(), self._avg_equity()))

        return results
