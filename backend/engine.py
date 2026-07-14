"""
backend/engine.py — Top-level analysis orchestrator.

Takes financial statements (dict form) and runs ALL registered categories,
returning a comprehensive result including:
  - all ratios by category
  - composite scoring (0-100)
  - signal (STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL)
  - bilingual narrative
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.ratios import REGISTRY

# ═══════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class YearResult:
    """Ratios for a single year, grouped by category."""
    year: str
    categories: dict[str, dict[str, float | None]] = field(default_factory=dict)
    ratio_count: int = 0


@dataclass
class AnalysisResult:
    """Full analysis output."""
    symbol: str
    name: str = ""
    sector: str = ""
    industry: str = ""
    current_price: float | None = None
    latest_year: str = ""

    # Ratios by year (each year has all categories)
    years: dict[str, YearResult] = field(default_factory=dict)

    # Latest year separate for quick access
    latest_by_category: dict[str, dict[str, float | None]] = field(default_factory=dict)

    # Scoring
    sub_scores: dict[str, float] = field(default_factory=dict)
    composite_score: float = 50.0
    signal: str = "HOLD"
    signal_th: str = "ถือ"

    # Narrative
    narrative_en: str = ""
    narrative_th: str = ""

    # Metadata
    total_ratios: int = 0
    categories_computed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Engine
# ═══════════════════════════════════════════════════════════════════════════

class AnalysisEngine:
    """Runs all ratio categories for all years."""

    def __init__(self, financials: dict, categories: list[str] | None = None):
        """
        Args:
            financials: dict with keys "Basic Info", "Income Statement",
                        "Balance Sheet", "Cash Flow Statement" (each with year keys)
            categories: subset of REGISTRY to compute. None = all.
        """
        self.data = financials
        self.categories = categories or list(REGISTRY.keys())

    def analyze(self) -> AnalysisResult:
        bi = self.data.get("Basic Info", {}) or {}
        income = self.data.get("Income Statement", {}) or {}
        balance = self.data.get("Balance Sheet", {}) or {}
        cashflow = self.data.get("Cash Flow Statement", {}) or {}

        symbol = bi.get("Symbol", "").upper()
        result = AnalysisResult(
            symbol=symbol,
            name=bi.get("Name", symbol),
            sector=bi.get("Sector", ""),
            industry=bi.get("Industry", ""),
            current_price=bi.get("CurrentPrice"),
        )

        # Available years (intersection of all 3 statements)
        common_years = sorted(
            set(income) & set(balance) & set(cashflow),
            key=lambda y: str(y),
        )
        if not common_years:
            result.warnings.append("No overlapping years across statements")
            return result

        # Build TTM history for multi-year metrics (Buffett, etc)
        ttm_history = []
        for y in common_years:
            ttm_history.append({
                "year": y,
                "income": income.get(y, {}),
                "balance": balance.get(y, {}),
                "cashflow": cashflow.get(y, {}),
            })

        # Attach year-over-year prices for risk metrics
        bi_with_prices = dict(bi)
        bi_with_prices["Prices"] = bi.get("Prices", {})

        # Process each year
        for i, year in enumerate(common_years):
            year_result = YearResult(year=str(year))

            prev_year = common_years[i-1] if i > 0 else None
            prev_income = income.get(prev_year, {}) if prev_year else {}
            prev_balance = balance.get(prev_year, {}) if prev_year else {}
            prev_cashflow = cashflow.get(prev_year, {}) if prev_year else {}

            # For the latest year, adjust basic_info to include current price
            # For older years, use the year's historical price
            year_bi = dict(bi_with_prices)
            year_price = bi.get("Prices", {}).get(str(year))
            if year_price is not None:
                year_bi["CurrentPrice"] = year_price
            # For latest year, prefer real-time current price
            if year == common_years[-1]:
                year_bi["CurrentPrice"] = bi.get("CurrentPrice", year_price)

            # Run each category
            for cat_name in self.categories:
                CalcClass = REGISTRY.get(cat_name)
                if not CalcClass:
                    continue
                try:
                    calc = CalcClass(
                        income=income.get(year, {}),
                        balance=balance.get(year, {}),
                        cashflow=cashflow.get(year, {}),
                        basic_info=year_bi,
                        prev_income=prev_income,
                        prev_balance=prev_balance,
                        prev_cashflow=prev_cashflow,
                        ttm_history=ttm_history,
                    )
                    ratios = calc.compute()
                    year_result.categories[cat_name] = ratios
                    year_result.ratio_count += len(ratios)
                except Exception as e:
                    year_result.categories[cat_name] = {"_error": str(e)}
                    result.warnings.append(f"{cat_name} @ {year}: {e}")

            result.years[str(year)] = year_result

        # Set latest year references
        latest = str(common_years[-1])
        result.latest_year = latest
        if latest in result.years:
            result.latest_by_category = result.years[latest].categories
            result.total_ratios = result.years[latest].ratio_count

        result.categories_computed = self.categories

        # Compute scoring
        result.sub_scores = self._compute_sub_scores(result)
        result.composite_score = self._compute_composite(result.sub_scores)
        result.signal, result.signal_th = self._map_signal(result.composite_score)

        # Build narrative
        result.narrative_en, result.narrative_th = self._narrative(result)

        return result

    # ═══════════════════════════════════════════════════
    # Scoring
    # ═══════════════════════════════════════════════════
    def _compute_sub_scores(self, r: AnalysisResult) -> dict[str, float]:
        """Compute 6 sub-scores (0-100) from latest ratios."""
        latest = r.latest_by_category

        subs = {}

        # Profitability score
        prof = latest.get("profitability", {})
        roe = prof.get("ROE") or 0
        margin = prof.get("Net Profit Margin") or 0
        subs["profitability"] = min(100, max(0, roe * 1.5 + margin * 1.5))

        # Valuation score (from Margin of Safety)
        iv = latest.get("intrinsic_value", {})
        mos = iv.get("Margin of Safety (DCF)")
        if mos is not None:
            subs["valuation"] = min(100, max(0, (mos + 0.2) * 200))
        else:
            subs["valuation"] = 50

        # Quality score (Altman Z + Piotroski F)
        q = latest.get("quality", {})
        z = q.get("Altman Z-Score") or 0
        f = q.get("Piotroski F-Score") or 5
        z_score = 90 if z >= 3 else (60 if z >= 1.81 else 30)
        f_score = min(100, f * 11)   # 9 * 11 = 99
        subs["quality"] = (z_score + f_score) / 2

        # Liquidity score
        liq = latest.get("liquidity", {})
        cr = liq.get("Current Ratio") or 0
        if cr >= 1.5:
            subs["liquidity"] = 85
        elif cr >= 1.0:
            subs["liquidity"] = 60
        else:
            subs["liquidity"] = 30

        # Leverage score (lower D/E = better)
        lev = latest.get("leverage", {})
        de = lev.get("Debt to Equity (D/E)")
        if de is None:
            subs["leverage"] = 50
        elif de < 0.5:
            subs["leverage"] = 85
        elif de < 1.0:
            subs["leverage"] = 70
        elif de < 2.0:
            subs["leverage"] = 40
        else:
            subs["leverage"] = 20

        # Growth score
        grow = latest.get("growth", {})
        rev_g = grow.get("Revenue Growth YoY") or 0
        ni_g = grow.get("Net Income Growth YoY") or 0
        subs["growth"] = min(100, max(0, 50 + (rev_g + ni_g) / 2))

        return {k: round(v, 1) for k, v in subs.items()}

    def _compute_composite(self, subs: dict[str, float]) -> float:
        """Weighted composite score."""
        weights = {
            "profitability": 0.20,
            "valuation":     0.25,
            "quality":       0.20,
            "liquidity":     0.10,
            "leverage":      0.10,
            "growth":        0.15,
        }
        weighted = sum(subs.get(k, 50) * w for k, w in weights.items())
        return round(weighted, 1)

    def _map_signal(self, score: float) -> tuple[str, str]:
        if score >= 75: return "STRONG_BUY", "ซื้อแรง"
        if score >= 60: return "BUY", "ซื้อ"
        if score >= 40: return "HOLD", "ถือ"
        if score >= 25: return "SELL", "ขาย"
        return "STRONG_SELL", "ขายแรง"

    def _narrative(self, r: AnalysisResult) -> tuple[str, str]:
        latest = r.latest_by_category
        prof = latest.get("profitability", {})
        iv = latest.get("intrinsic_value", {})
        q = latest.get("quality", {})

        parts_en = [
            f"{r.symbol} ({r.name}): {r.signal} | Score {r.composite_score}/100."
        ]
        parts_th = [
            f"{r.symbol} ({r.name}): {r.signal_th} | คะแนน {r.composite_score}/100."
        ]

        # ROE
        roe = prof.get("ROE")
        if roe is not None:
            parts_en.append(f"ROE {roe:.1f}%.")
            parts_th.append(f"ROE {roe:.1f}%.")

        # DCF vs Price
        mos = iv.get("Margin of Safety (DCF)")
        if mos is not None:
            if mos > 0:
                parts_en.append(f"Trades {mos*100:.1f}% below DCF value.")
                parts_th.append(f"ราคาต่ำกว่ามูลค่า DCF {mos*100:.1f}%.")
            else:
                parts_en.append(f"Trades {-mos*100:.1f}% above DCF value (overvalued).")
                parts_th.append(f"ราคาสูงกว่ามูลค่า DCF {-mos*100:.1f}% (แพง).")

        # Altman Z
        z = q.get("Altman Z-Score")
        if z is not None:
            zone_en = "safe" if z >= 3 else ("grey" if z >= 1.81 else "distress")
            zone_th = "ปลอดภัย" if z >= 3 else ("เฝ้าระวัง" if z >= 1.81 else "เสี่ยง")
            parts_en.append(f"Altman Z={z:.2f} ({zone_en}).")
            parts_th.append(f"Altman Z={z:.2f} ({zone_th}).")

        return " ".join(parts_en), " ".join(parts_th)


def analyze_financials(financials: dict, categories: list[str] | None = None) -> AnalysisResult:
    """Convenience entry point."""
    return AnalysisEngine(financials, categories).analyze()
