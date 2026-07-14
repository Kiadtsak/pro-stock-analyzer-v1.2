"""
Buffett Ratios — 12 formulas.

Long-term quality metrics favored by Warren Buffett:
  - Owner Earnings (FCF-based)
  - ROE consistency (10-year average)
  - Book Value growth
  - Cash Conversion
  - Moat indicators
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, spct, sround


class BuffettRatios(RatioBase):
    category = "buffett"
    description = "Long-term quality (Buffett-style)"

    def compute(self) -> dict[str, float | None]:
        ni = self._net_income()
        rev = self._revenue()
        fcf = self._fcf()
        equity = self._total_equity()
        assets = self._total_assets()
        capex = self._capex() or 0
        da = self._da() or 0

        # Owner Earnings = Net Income + D&A - Maintenance CapEx
        # Approximation: use CapEx × 0.7 as maintenance
        owner_earnings = None
        if ni is not None:
            owner_earnings = ni + da - (capex * 0.7)

        # Alternative: OCF - CapEx (same as FCF, approximation)
        owner_earnings_alt = fcf

        # ROE — use avg equity for consistency with profitability module
        # (previously used current equity, causing cross-module inconsistency)
        roe = spct(sdiv(ni, self._avg_equity()))

        # Cash Conversion = FCF / Net Income (Buffett wants >1)
        cash_conversion = sround(sdiv(fcf, ni))

        # Book Value Per Share Growth (via ttm_history if available)
        bvps_growth_10y = self._bvps_growth_multi_year()

        # 10-year Avg ROE
        avg_roe_10y = self._avg_roe_multi_year()

        # Retained Earnings growth
        re = get(self.balance, "Retained Earnings")
        prev_re = get(self.prev_balance, "Retained Earnings")
        re_growth = None
        if re is not None and prev_re is not None and prev_re > 0:
            re_growth = (re - prev_re) / prev_re

        # Owner Earnings growth
        prev_ni = get(self.prev_income, "Net Income")
        prev_da = get(self.prev_cashflow, "Depreciation and Amortization",
                      "Depreciation & Amortization") or 0
        prev_capex = get(self.prev_cashflow, "Capital Expenditure") or 0
        prev_owner_earnings = None
        if prev_ni is not None:
            prev_owner_earnings = prev_ni + prev_da - (prev_capex * 0.7)
        oe_growth = None
        if owner_earnings is not None and prev_owner_earnings and prev_owner_earnings > 0:
            oe_growth = (owner_earnings - prev_owner_earnings) / prev_owner_earnings

        # Buffett quality thresholds
        moat_indicators = self._moat_check(roe, cash_conversion)

        return {
            # ── Owner Earnings ──────────────────────────
            "Owner Earnings (Buffett)": sround(owner_earnings, 2),
            "Owner Earnings (Simplified)": sround(owner_earnings_alt, 2),
            "Owner Earnings Growth YoY": spct(oe_growth),
            "Owner Earnings Margin": spct(sdiv(owner_earnings, rev)),
            "Owner Earnings Yield": sround(sdiv(owner_earnings, self._market_cap())),

            # ── Returns ─────────────────────────────────
            "Current ROE": roe,
            "10Y Average ROE": avg_roe_10y,
            "ROE Consistency": self._roe_consistency(),        # stddev / mean

            # ── Quality signals ─────────────────────────
            "Cash Conversion Ratio": cash_conversion,
            "Retained Earnings Growth": spct(re_growth),
            "Book Value Per Share Growth (10Y)": bvps_growth_10y,

            # ── Reinvestment quality ────────────────────
            "Reinvestment Rate": self._reinvestment_rate(),
            "Return on Retained Earnings": self._return_on_retained_earnings(),

            # ── Moat check ──────────────────────────────
            "Moat Score (0-4)": moat_indicators,
        }

    def _bvps_growth_multi_year(self) -> float | None:
        """CAGR of Book Value Per Share over history."""
        if not self.ttm_history or len(self.ttm_history) < 2:
            return None
        try:
            first = self.ttm_history[0]
            last = self.ttm_history[-1]
            years = len(self.ttm_history) - 1

            bvps_first = sdiv(
                get(first.get("balance", {}), "Total Equity", "Stockholders Equity"),
                get(first.get("income", {}), "Weighted Average Shares"),
            )
            bvps_last = sdiv(
                get(last.get("balance", {}), "Total Equity", "Stockholders Equity"),
                get(last.get("income", {}), "Weighted Average Shares"),
            )
            if bvps_first is None or bvps_last is None or bvps_first <= 0:
                return None
            cagr = (bvps_last / bvps_first) ** (1 / years) - 1
            return spct(cagr)
        except Exception:
            return None

    def _avg_roe_multi_year(self) -> float | None:
        """Average ROE over available history."""
        if not self.ttm_history:
            return None
        roes = []
        for year_data in self.ttm_history:
            ni = get(year_data.get("income", {}), "Net Income")
            eq = get(year_data.get("balance", {}), "Total Equity",
                     "Stockholders Equity")
            r = sdiv(ni, eq)
            if r is not None:
                roes.append(r)
        if not roes:
            return None
        return spct(sum(roes) / len(roes))

    def _roe_consistency(self) -> float | None:
        """Stddev / Mean of ROE. Lower = more consistent."""
        if not self.ttm_history or len(self.ttm_history) < 3:
            return None
        roes = []
        for y in self.ttm_history:
            r = sdiv(
                get(y.get("income", {}), "Net Income"),
                get(y.get("balance", {}), "Total Equity", "Stockholders Equity"),
            )
            if r is not None:
                roes.append(r)
        if len(roes) < 2:
            return None
        mean = sum(roes) / len(roes)
        if mean == 0:
            return None
        var = sum((r - mean) ** 2 for r in roes) / len(roes)
        std = var ** 0.5
        return sround(std / abs(mean), 4)

    def _reinvestment_rate(self) -> float | None:
        """
        Reinvestment Rate = (CapEx + ΔWC) / Net Income
        Buffett prefers low reinvestment needs.
        """
        ni = self._net_income()
        capex = self._capex() or 0
        change_wc = get(self.cashflow, "Change in Working Capital") or 0
        return sround(sdiv(capex + change_wc, ni))

    def _return_on_retained_earnings(self) -> float | None:
        """
        Approximates: (this year's earnings - last year's earnings)
                     / retained earnings gained during that period.
        """
        ni = self._net_income()
        prev_ni = get(self.prev_income, "Net Income")
        re = get(self.balance, "Retained Earnings")
        prev_re = get(self.prev_balance, "Retained Earnings")

        if not all([ni, prev_ni, re, prev_re]):
            return None
        re_gain = re - prev_re
        earnings_gain = ni - prev_ni
        return spct(sdiv(earnings_gain, re_gain))

    def _moat_check(self, roe: float | None, cash_conv: float | None) -> int | None:
        """
        Simple moat scoring (0-4 signals):
          - ROE > 15% (consistent excellence)
          - Cash Conversion > 1 (real earnings)
          - Gross margin > 40% (pricing power)
          - Low D/E < 0.5 (financial strength)
        """
        score = 0
        if roe is not None and roe > 15:
            score += 1
        if cash_conv is not None and cash_conv > 1.0:
            score += 1
        gm = sdiv(self._gross_profit(), self._revenue())
        if gm is not None and gm > 0.4:
            score += 1
        de = sdiv(self._total_debt(), self._total_equity())
        if de is not None and de < 0.5:
            score += 1
        return score
