"""
Valuation Ratios — 24 formulas.

Price-based multiples and enterprise value metrics.
"""
from __future__ import annotations

from backend.ratios.base import RatioBase, get, sdiv, sround


class ValuationRatios(RatioBase):
    category = "valuation"
    description = "Price-based multiples and EV metrics"

    def compute(self) -> dict[str, float | None]:
        price = self._price()
        mcap = self._market_cap()
        shares = self._shares()

        # Per-share metrics
        eps = self._eps()
        ni = self._net_income()
        rev = self._revenue()
        gp = self._gross_profit()
        oi = self._operating_income()
        ebit = self._ebit()
        ebitda = self._ebitda()
        fcf = self._fcf()
        ocf = self._ocf()
        equity = self._total_equity()
        total_debt = self._total_debt() or 0
        cash = self._cash() or 0
        dividends = self._dividends_paid()

        # Book value per share
        bvps = sdiv(equity, shares)

        # Sales per share
        sps = sdiv(rev, shares)

        # Cash flow per share
        cfps = sdiv(ocf, shares)
        fcfps = sdiv(fcf, shares)

        # Enterprise Value = MarketCap + Debt - Cash
        ev = None
        if mcap is not None:
            ev = mcap + total_debt - cash

        # Dividend per share
        dps = sdiv(dividends, shares)

        return {
            # ── Per-share ───────────────────────────────
            "Earnings Per Share (EPS)": sround(eps, 2),
            "Book Value Per Share (BVPS)": sround(bvps, 2),
            "Sales Per Share (SPS)": sround(sps, 2),
            "Cash Flow Per Share": sround(cfps, 2),
            "Free Cash Flow Per Share": sround(fcfps, 2),
            "Dividend Per Share (DPS)": sround(dps, 4),

            # ── Price multiples ─────────────────────────
            "P/E Ratio": sround(sdiv(price, eps)),
            "P/E to Growth (PEG)": self._peg(price, eps),
            "P/B Ratio": sround(sdiv(price, bvps)),
            "P/S Ratio": sround(sdiv(price, sps)),
            "P/CF Ratio": sround(sdiv(price, cfps)),
            "P/FCF Ratio": sround(sdiv(price, fcfps)),
            "Price to Tangible Book": self._p_tangible_book(price, shares, equity),

            # ── Market cap multiples ────────────────────
            "Market Cap": sround(mcap, 2),
            "Market Cap to Revenue": sround(sdiv(mcap, rev)),
            "Market Cap to FCF": sround(sdiv(mcap, fcf)),
            "Market Cap to Net Income": sround(sdiv(mcap, ni)),

            # ── Enterprise Value multiples ──────────────
            "Enterprise Value (EV)": sround(ev, 2),
            "EV / EBITDA": sround(sdiv(ev, ebitda)),
            "EV / EBIT": sround(sdiv(ev, ebit)),
            "EV / Sales (EV/Revenue)": sround(sdiv(ev, rev)),
            "EV / FCF": sround(sdiv(ev, fcf)),
            "EV / OCF": sround(sdiv(ev, ocf)),
            "EV / Gross Profit": sround(sdiv(ev, gp)),

            # ── Yield metrics (inverse of multiples) ────
            "Earnings Yield": sround(sdiv(eps, price)),         # 1/PE
            "FCF Yield": sround(sdiv(fcfps, price)),
            "Sales Yield": sround(sdiv(sps, price)),
            "Book Yield": sround(sdiv(bvps, price)),
        }

    def _peg(self, price, eps) -> float | None:
        """PEG = P/E / EPS Growth (using prev year)."""
        prev_eps = get(self.prev_income, "Earnings Per Share", "EPS")
        if price is None or eps is None or prev_eps is None or eps <= 0:
            return None
        pe = price / eps
        if prev_eps == 0:
            return None
        growth_pct = ((eps - prev_eps) / abs(prev_eps)) * 100
        return sround(sdiv(pe, growth_pct))

    def _p_tangible_book(self, price, shares, equity) -> float | None:
        """P/Tangible Book = Price / Tangible BVPS."""
        goodwill = get(self.balance, "Goodwill") or 0
        intangibles = get(self.balance, "Intangible Assets", "Other Intangible Assets") or 0
        if equity is None:
            return None
        tangible_equity = equity - goodwill - intangibles
        tbvps = sdiv(tangible_equity, shares)
        return sround(sdiv(price, tbvps))
