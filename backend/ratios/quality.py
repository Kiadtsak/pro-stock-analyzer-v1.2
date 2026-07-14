"""
Quality Ratios — 18 formulas.

Financial health scores:
  - Altman Z-Score:    bankruptcy risk (>3=safe, 1.81-3=grey, <1.81=distress)
  - Piotroski F-Score: financial strength (0-9, higher=better)
  - Beneish M-Score:   earnings manipulation detection (<-2.22=likely clean)
  - Sloan Accruals:    earnings quality
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, sround


class QualityRatios(RatioBase):
    category = "quality"
    description = "Financial health & earnings quality scores"

    def compute(self) -> dict[str, float | None]:
        results: dict[str, float | None] = {}

        # ── Altman Z-Score (Manufacturing) ──────────────
        results["Altman Z-Score"] = self._altman_z()

        # Altman Z' (Private, Non-Manufacturer variant)
        results["Altman Z' Score (Private)"] = self._altman_z_prime()

        # ── Piotroski F-Score ───────────────────────────
        f_score, f_details = self._piotroski_f()
        results["Piotroski F-Score"] = f_score
        for k, v in f_details.items():
            results[f"F-Score: {k}"] = v

        # ── Beneish M-Score (light) ─────────────────────
        results["Beneish M-Score"] = self._beneish_m()

        # ── Sloan Accruals Ratio ────────────────────────
        results["Sloan Accruals"] = self._sloan_accruals()

        # ── Earnings Quality ────────────────────────────
        ocf = self._ocf()
        ni = self._net_income()
        results["Cash Flow to Earnings"] = sround(sdiv(ocf, ni))
        results["Accruals to Assets"] = self._accruals_ratio()

        return results

    # ═══════════════════════════════════════════════════════
    # Altman Z-Score
    # ═══════════════════════════════════════════════════════
    def _altman_z(self) -> float | None:
        """
        Altman Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E

          A = Working Capital / Total Assets
          B = Retained Earnings / Total Assets
          C = EBIT / Total Assets
          D = Market Cap / Total Liabilities
          E = Revenue / Total Assets

        Zones:
          > 3.0     : SAFE
          1.81-3.0  : GREY (risky)
          < 1.81    : DISTRESS
        """
        ta = self._total_assets()
        if ta is None or ta <= 0:
            return None

        ca = self._current_assets() or 0
        cl = self._current_liabilities() or 0
        wc = ca - cl

        re = get(self.balance, "Retained Earnings") or 0
        ebit = self._ebit() or 0
        mcap = self._market_cap() or 0
        tl = self._total_liabilities() or 1  # avoid division-by-zero
        rev = self._revenue() or 0

        try:
            z = (1.2 * (wc / ta)
                 + 1.4 * (re / ta)
                 + 3.3 * (ebit / ta)
                 + 0.6 * (mcap / max(tl, 1))
                 + 1.0 * (rev / ta))
            return round(z, 3)
        except Exception:
            return None

    def _altman_z_prime(self) -> float | None:
        """Altman Z' for private companies (uses Book Value instead of MarketCap)."""
        ta = self._total_assets()
        if ta is None or ta <= 0:
            return None
        ca = self._current_assets() or 0
        cl = self._current_liabilities() or 0
        wc = ca - cl
        re = get(self.balance, "Retained Earnings") or 0
        ebit = self._ebit() or 0
        equity = self._total_equity() or 0
        tl = self._total_liabilities() or 1
        rev = self._revenue() or 0

        try:
            z = (0.717 * (wc / ta)
                 + 0.847 * (re / ta)
                 + 3.107 * (ebit / ta)
                 + 0.420 * (equity / tl)
                 + 0.998 * (rev / ta))
            return round(z, 3)
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════
    # Piotroski F-Score (0-9 scale)
    # ═══════════════════════════════════════════════════════
    def _piotroski_f(self) -> tuple[int | None, dict[str, int | None]]:
        """
        9 binary tests (1 point each):

        Profitability:
          1. Net Income > 0
          2. OCF > 0
          3. ROA increasing
          4. OCF > Net Income (accrual quality)

        Leverage/Liquidity:
          5. Long-term debt decreasing
          6. Current ratio increasing
          7. No new shares issued

        Efficiency:
          8. Gross margin increasing
          9. Asset turnover increasing
        """
        # Need prev-year data to compute deltas
        if not self.prev_income and not self.prev_balance:
            return None, {}

        ni = self._net_income()
        ocf = self._ocf()
        assets = self._total_assets()
        prev_assets = get(self.prev_balance, "Total Assets")

        tests = {}

        # 1. Net Income > 0
        tests["Net Income > 0"] = 1 if (ni is not None and ni > 0) else 0

        # 2. OCF > 0
        tests["OCF > 0"] = 1 if (ocf is not None and ocf > 0) else 0

        # 3. ROA increasing (this year vs last)
        prev_ni = get(self.prev_income, "Net Income")
        curr_roa = sdiv(ni, assets)
        prev_roa = sdiv(prev_ni, prev_assets)
        tests["ROA Increasing"] = (
            1 if (curr_roa is not None and prev_roa is not None and curr_roa > prev_roa) else 0
        )

        # 4. OCF > Net Income (accrual quality)
        tests["OCF > Net Income"] = 1 if (ocf and ni and ocf > ni) else 0

        # 5. Long-term debt decreasing
        lt = get(self.balance, "Long Term Debt") or 0
        prev_lt = get(self.prev_balance, "Long Term Debt") or 0
        tests["LT Debt Decreasing"] = 1 if lt < prev_lt else 0

        # 6. Current Ratio increasing
        curr_cr = sdiv(self._current_assets(), self._current_liabilities())
        prev_cr = sdiv(
            get(self.prev_balance, "Total Current Assets"),
            get(self.prev_balance, "Total Current Liabilities"),
        )
        tests["Current Ratio Improving"] = (
            1 if (curr_cr is not None and prev_cr is not None and curr_cr > prev_cr) else 0
        )

        # 7. No new shares issued
        curr_shares = self._shares() or 0
        prev_shares = get(self.prev_income, "Weighted Average Shares Diluted",
                          "Weighted Average Shares") or 0
        tests["No New Shares"] = 1 if curr_shares <= prev_shares * 1.02 else 0  # allow 2% tolerance

        # 8. Gross Margin increasing
        curr_gm = sdiv(self._gross_profit(), self._revenue())
        prev_gm = sdiv(
            get(self.prev_income, "Gross Profit"),
            get(self.prev_income, "Revenue", "Total Revenue"),
        )
        tests["Gross Margin Improving"] = (
            1 if (curr_gm is not None and prev_gm is not None and curr_gm > prev_gm) else 0
        )

        # 9. Asset Turnover increasing
        curr_at = sdiv(self._revenue(), assets)
        prev_at = sdiv(
            get(self.prev_income, "Revenue", "Total Revenue"),
            prev_assets,
        )
        tests["Asset Turnover Improving"] = (
            1 if (curr_at is not None and prev_at is not None and curr_at > prev_at) else 0
        )

        return sum(tests.values()), tests

    # ═══════════════════════════════════════════════════════
    # Beneish M-Score (simplified)
    # ═══════════════════════════════════════════════════════
    def _beneish_m(self) -> float | None:
        """
        M-Score components (requires 2 years):
          DSRI: Days Sales in Receivables Index
          GMI:  Gross Margin Index
          AQI:  Asset Quality Index
          SGI:  Sales Growth Index
          DEPI: Depreciation Index
          SGAI: SG&A Index
          LVGI: Leverage Index
          TATA: Total Accruals to Total Assets

        Score < -2.22 = likely NOT manipulating
        Score > -1.78 = likely manipulating
        """
        if not self.prev_income or not self.prev_balance:
            return None

        rev = self._revenue()
        prev_rev = get(self.prev_income, "Revenue", "Total Revenue")
        recv = self._receivables()
        prev_recv = get(self.prev_balance, "Accounts Receivable", "Net Receivables")
        gp = self._gross_profit()
        prev_gp = get(self.prev_income, "Gross Profit")
        ta = self._total_assets()
        prev_ta = get(self.prev_balance, "Total Assets")

        if not all([rev, prev_rev, ta, prev_ta]):
            return None

        try:
            # DSRI
            dsri = (sdiv(recv, rev) or 0) / (sdiv(prev_recv, prev_rev) or 1)

            # GMI (higher = declining margins = more likely manipulation)
            gm = sdiv(gp, rev)
            prev_gm = sdiv(prev_gp, prev_rev)
            gmi = (prev_gm or 1) / (gm or 1)

            # SGI (sales growth)
            sgi = rev / prev_rev if prev_rev else 1

            # Basic 4-factor approximation
            m = -4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * sgi
            return round(m, 3)
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════
    # Sloan Accruals & Earnings Quality
    # ═══════════════════════════════════════════════════════
    def _sloan_accruals(self) -> float | None:
        """Sloan Ratio = (NI - OCF - ICF) / Avg Assets."""
        ni = self._net_income()
        ocf = self._ocf()
        icf = get(self.cashflow, "Investing Cash Flow", "Cash Flow from Investing")
        avg_a = self._avg_assets()
        if ni is None or ocf is None or avg_a is None or avg_a == 0:
            return None
        return sround((ni - ocf - (icf or 0)) / avg_a, 4)

    def _accruals_ratio(self) -> float | None:
        """Simple accruals = (NI - OCF) / Total Assets."""
        ni = self._net_income()
        ocf = self._ocf()
        ta = self._total_assets()
        if ni is None or ocf is None or ta is None or ta == 0:
            return None
        return sround((ni - ocf) / ta, 4)
