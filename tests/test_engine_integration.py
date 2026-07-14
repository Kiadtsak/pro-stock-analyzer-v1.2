"""
tests/test_engine_integration.py — Integration tests for the AnalysisEngine.

ทดสอบว่า components ทำงานร่วมกันถูกต้อง

Usage:
    pytest tests/test_engine_integration.py
    pytest -m integration
"""
from __future__ import annotations

import pytest

from backend import REGISTRY, analyze_financials


@pytest.mark.integration
class TestAnalysisEngine:
    """Full engine flow tests."""

    def test_engine_runs_all_18_categories(self, synthetic_full_data):
        """Engine should invoke all registered categories."""
        result = analyze_financials(synthetic_full_data)
        assert len(result.categories_computed) == 18
        # Every registered category should have output
        for cat_name in REGISTRY:
            assert cat_name in result.latest_by_category

    def test_engine_computes_200_plus_ratios(self, synthetic_full_data):
        """The system's headline promise: 200+ ratios."""
        result = analyze_financials(synthetic_full_data)
        assert result.total_ratios >= 200, \
            f"Expected 200+ ratios, got {result.total_ratios}"

    def test_signal_is_valid(self, synthetic_full_data):
        """Signal must be one of the 5 valid tiers."""
        result = analyze_financials(synthetic_full_data)
        assert result.signal in [
            "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"
        ]
        assert result.signal_th in [
            "ซื้อแรง", "ซื้อ", "ถือ", "ขาย", "ขายแรง"
        ]

    def test_composite_score_is_0_to_100(self, synthetic_full_data):
        result = analyze_financials(synthetic_full_data)
        assert 0 <= result.composite_score <= 100

    def test_sub_scores_all_0_to_100(self, synthetic_full_data):
        result = analyze_financials(synthetic_full_data)
        expected_keys = [
            "profitability", "valuation", "quality",
            "liquidity", "leverage", "growth",
        ]
        for key in expected_keys:
            assert key in result.sub_scores
            score = result.sub_scores[key]
            assert 0 <= score <= 100, f"{key} score {score} out of range"

    def test_narrative_bilingual(self, synthetic_full_data):
        result = analyze_financials(synthetic_full_data)
        assert result.narrative_en, "English narrative empty"
        assert result.narrative_th, "Thai narrative empty"
        # Thai narrative must contain Thai characters
        assert any("\u0e00" <= c <= "\u0e7f" for c in result.narrative_th)


# ═══════════════════════════════════════════════════════════════════════════
# Cross-module consistency tests — CRITICAL for correctness
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestCrossModuleConsistency:
    """
    Verify that the same metric computed in different modules matches.
    These are regression tests for consistency bugs.
    """

    def test_roe_consistent_across_modules(self, synthetic_full_data):
        """ROE in profitability == Current ROE in buffett."""
        result = analyze_financials(synthetic_full_data)
        roe_prof = result.latest_by_category["profitability"]["ROE"]
        roe_buffett = result.latest_by_category["buffett"]["Current ROE"]
        assert roe_prof is not None
        assert roe_buffett is not None
        assert abs(roe_prof - roe_buffett) < 0.1, \
            f"ROE inconsistent: prof={roe_prof}, buffett={roe_buffett}"

    def test_retention_ratio_consistent_units(self, synthetic_full_data):
        """Retention Ratio in growth and dividend must use same scale (%)."""
        result = analyze_financials(synthetic_full_data)
        ret_growth = result.latest_by_category["growth"].get("Retention Ratio")
        ret_div = result.latest_by_category["dividend"].get("Retention Ratio")
        if ret_growth is not None and ret_div is not None:
            assert abs(ret_growth - ret_div) < 1.0, \
                f"Retention scale mismatch: growth={ret_growth}, div={ret_div}"

    def test_eps_matches_ni_over_shares(self, synthetic_full_data):
        """EPS from valuation == NI / Shares (basic sanity)."""
        result = analyze_financials(synthetic_full_data)
        eps = result.latest_by_category["valuation"]["Earnings Per Share (EPS)"]
        ni = synthetic_full_data["Income Statement"]["2023"]["Net Income"]
        shares = synthetic_full_data["Income Statement"]["2023"]["Weighted Average Shares Diluted"]
        expected = ni / shares
        assert abs(eps - expected) / expected < 0.05

    def test_fcf_matches_ocf_minus_capex(self, synthetic_full_data):
        """FCF from cash_flow == OCF - CapEx (basic sanity)."""
        result = analyze_financials(synthetic_full_data)
        fcf = result.latest_by_category["cash_flow"]["Free Cash Flow (FCF)"]
        ocf = synthetic_full_data["Cash Flow Statement"]["2023"]["Operating Cash Flow"]
        capex = abs(synthetic_full_data["Cash Flow Statement"]["2023"]["Capital Expenditure"])
        expected = ocf - capex
        assert abs(fcf - expected) < 1000  # allow small rounding


# ═══════════════════════════════════════════════════════════════════════════
# Multi-year analysis tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestMultiYearAnalysis:
    def test_result_contains_all_years(self, synthetic_full_data):
        result = analyze_financials(synthetic_full_data)
        assert "2022" in result.years
        assert "2023" in result.years

    def test_latest_year_is_most_recent(self, synthetic_full_data):
        result = analyze_financials(synthetic_full_data)
        assert result.latest_year == "2023"

    def test_2022_has_no_growth_but_2023_does(self, synthetic_full_data):
        """First year has no growth (no prev year); second year does."""
        result = analyze_financials(synthetic_full_data)
        growth_2022 = result.years["2022"].categories.get("growth", {})
        growth_2023 = result.years["2023"].categories.get("growth", {})
        # 2022 has no prev → growth None
        assert growth_2022.get("Revenue Growth YoY") is None
        # 2023 has prev 2022 → growth computed
        assert growth_2023.get("Revenue Growth YoY") is not None


# ═══════════════════════════════════════════════════════════════════════════
# Filtered category tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestCategoryFiltering:
    def test_can_run_single_category(self, synthetic_full_data):
        result = analyze_financials(synthetic_full_data, categories=["profitability"])
        assert result.categories_computed == ["profitability"]
        assert "profitability" in result.latest_by_category
        assert "quality" not in result.latest_by_category

    def test_can_run_subset_of_categories(self, synthetic_full_data):
        result = analyze_financials(
            synthetic_full_data,
            categories=["profitability", "liquidity", "valuation"],
        )
        assert len(result.categories_computed) == 3


# ═══════════════════════════════════════════════════════════════════════════
# Real data tests (skipped if data not available)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
@pytest.mark.real_data
class TestRealData:
    def test_aapl_analysis_produces_reasonable_values(self, real_aapl_data):
        """AAPL should have gross margin 35-55% (real-world range)."""
        result = analyze_financials(real_aapl_data)
        gm = result.latest_by_category["profitability"]["Gross Profit Margin"]
        assert 35 <= gm <= 55, f"AAPL gross margin {gm} out of range"

    def test_multiple_real_symbols_no_crash(self, real_symbol_data):
        """Parametrized — tests AAPL/NVDA/MSFT/GOOGL/META in one shot."""
        result = analyze_financials(real_symbol_data)
        assert result.total_ratios > 200
        assert result.signal in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]

    def test_no_infinity_in_real_data(self, real_symbol_data):
        """Real data must never produce infinity values."""
        import math
        result = analyze_financials(real_symbol_data)
        for cat, ratios in result.latest_by_category.items():
            for name, val in ratios.items():
                if val is not None and isinstance(val, float):
                    assert not math.isinf(val), f"{cat}.{name} is infinity"
                    assert not math.isnan(val), f"{cat}.{name} is NaN"
