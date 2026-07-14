"""
Risk Ratios — 10 formulas.

Volatility, drawdown, Sharpe, Sortino, Beta.

Note: Most require price history not statements. We compute what we can
from financial data and note when time-series data is required.
"""
from __future__ import annotations

import math

from backend.ratios.base import RatioBase, sdiv, spct, sround


class RiskRatios(RatioBase):
    category = "risk"
    description = "Volatility, drawdown, financial risk"

    def compute(self) -> dict[str, float | None]:
        # Prices from basic_info if available
        prices_by_year = self.basic_info.get("Prices", {}) or {}
        price_values = sorted(
            [(int(y), float(p)) for y, p in prices_by_year.items()
             if str(y).isdigit()],
            key=lambda x: x[0],
        )

        returns = []
        for i in range(1, len(price_values)):
            _, prev_p = price_values[i-1]
            _, curr_p = price_values[i]
            if prev_p > 0:
                returns.append((curr_p - prev_p) / prev_p)

        results = {}

        # Financial risk (from statements)
        results["Debt-to-Equity Risk Score"] = self._debt_risk_score()
        results["Interest Coverage Warning"] = self._interest_warning()
        results["Cash Runway (Years)"] = self._cash_runway()
        results["Financial Leverage"] = sround(sdiv(self._total_assets(),
                                                     self._total_equity()))

        # Volatility (from prices)
        if returns:
            mean_r = sum(returns) / len(returns)
            var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
            std = math.sqrt(var)
            results["Annualized Volatility"] = spct(std)
            results["Mean Annual Return"] = spct(mean_r)

            # Sharpe (rf = 4.5%)
            rf = 0.045
            if std > 0:
                sharpe = (mean_r - rf) / std
                results["Sharpe Ratio"] = sround(sharpe, 3)

            # Sortino (downside deviation)
            downside_rets = [r for r in returns if r < 0]
            if downside_rets:
                dstd = math.sqrt(sum(r ** 2 for r in downside_rets) / len(downside_rets))
                if dstd > 0:
                    results["Sortino Ratio"] = sround((mean_r - rf) / dstd, 3)

            # Max Drawdown
            peak = price_values[0][1]
            max_dd = 0
            for _, p in price_values:
                peak = max(peak, p)
                dd = (p - peak) / peak if peak > 0 else 0
                max_dd = min(max_dd, dd)
            results["Max Drawdown"] = spct(max_dd)

            # Compound Annual Return
            years_span = price_values[-1][0] - price_values[0][0]
            if years_span > 0 and price_values[0][1] > 0:
                cagr = (price_values[-1][1] / price_values[0][1]) ** (1 / years_span) - 1
                results["Price CAGR"] = spct(cagr)

        return results

    def _debt_risk_score(self) -> int | None:
        """Simple 0-3 score: 0 = safe, 3 = high risk."""
        de = sdiv(self._total_debt(), self._total_equity())
        if de is None:
            return None
        if de > 2.0:
            return 3
        if de > 1.0:
            return 2
        if de > 0.5:
            return 1
        return 0

    def _interest_warning(self) -> int | None:
        """1 = warning (Interest Coverage < 3), 0 = OK."""
        ic = sdiv(self._ebit(), self._interest_expense())
        if ic is None:
            return None
        return 1 if ic < 3 else 0

    def _cash_runway(self) -> float | None:
        """Years of cash on hand at current burn rate. Only if burning cash."""
        cash = self._cash()
        ocf = self._ocf()
        if cash is None or ocf is None:
            return None
        if ocf >= 0:
            return None  # not burning cash — infinite runway
        return sround(cash / abs(ocf), 2)
