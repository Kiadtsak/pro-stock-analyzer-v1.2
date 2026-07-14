"""
tests/test_benchmarks.py — Performance benchmarks.

วัดว่าโค้ดเร็วแค่ไหน + ตรวจ regression (โค้ดใหม่ช้าลงหรือเปล่า)

Usage:
    pip install pytest-benchmark
    pytest tests/test_benchmarks.py --benchmark-only
    pytest tests/test_benchmarks.py --benchmark-only --benchmark-save=baseline
    pytest tests/test_benchmarks.py --benchmark-compare
"""
from __future__ import annotations

import pytest

from backend import analyze_financials
from backend.ratios import (
    IntrinsicValueRatios,
    ProfitabilityRatios,
    QualityRatios,
)


@pytest.mark.benchmark
class TestSingleRatioBenchmarks:
    """Micro-benchmarks — individual ratio modules."""

    def test_profitability_speed(self, benchmark, synthetic_income, synthetic_balance,
                                  synthetic_prev_balance):
        """Should compute in < 1 ms."""
        def run():
            calc = ProfitabilityRatios(
                income=synthetic_income,
                balance=synthetic_balance,
                prev_balance=synthetic_prev_balance,
            )
            return calc.compute()
        result = benchmark(run)
        assert result["ROE"] is not None

    def test_quality_speed(self, benchmark, synthetic_full_data):
        """Altman Z + Piotroski F (most complex)."""
        d = synthetic_full_data
        def run():
            calc = QualityRatios(
                income=d["Income Statement"]["2023"],
                balance=d["Balance Sheet"]["2023"],
                cashflow=d["Cash Flow Statement"]["2023"],
                basic_info=d["Basic Info"],
                prev_income=d["Income Statement"]["2022"],
                prev_balance=d["Balance Sheet"]["2022"],
                prev_cashflow=d["Cash Flow Statement"]["2022"],
            )
            return calc.compute()
        benchmark(run)

    def test_intrinsic_value_speed(self, benchmark, synthetic_full_data):
        """DCF + Reverse DCF (iterative — slowest)."""
        d = synthetic_full_data
        def run():
            calc = IntrinsicValueRatios(
                income=d["Income Statement"]["2023"],
                balance=d["Balance Sheet"]["2023"],
                cashflow=d["Cash Flow Statement"]["2023"],
                basic_info=d["Basic Info"],
                prev_income=d["Income Statement"]["2022"],
            )
            return calc.compute()
        benchmark(run)


@pytest.mark.benchmark
class TestEngineBenchmarks:
    """Full pipeline benchmarks."""

    def test_full_analysis_speed(self, benchmark, synthetic_full_data):
        """Full engine — all 18 categories, all years. Should be < 50 ms."""
        def run():
            return analyze_financials(synthetic_full_data)
        result = benchmark(run)
        assert result.total_ratios >= 200

    def test_filtered_analysis_faster(self, benchmark, synthetic_full_data):
        """Filtered analysis (5 categories) should be much faster than full."""
        def run():
            return analyze_financials(
                synthetic_full_data,
                categories=["profitability", "valuation", "quality", "liquidity", "leverage"],
            )
        benchmark(run)


@pytest.mark.benchmark
@pytest.mark.real_data
class TestRealDataBenchmarks:
    """Benchmarks with real data."""

    def test_analyze_aapl(self, benchmark, real_aapl_data):
        def run():
            return analyze_financials(real_aapl_data)
        benchmark(run)


# ═══════════════════════════════════════════════════════════════════════════
# Regression guards — fail if performance degrades
# ═══════════════════════════════════════════════════════════════════════════

class TestPerformanceRegressions:
    """Ensure operations complete within target time."""

    def test_full_analysis_under_100ms(self, synthetic_full_data):
        """Full analysis MUST complete in < 100ms."""
        import time
        start = time.perf_counter()
        analyze_financials(synthetic_full_data)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, \
            f"Full analysis took {elapsed_ms:.1f}ms (limit: 100ms)"

    def test_single_ratio_under_10ms(self, synthetic_income, synthetic_balance):
        """Any single ratio module should complete in < 10ms."""
        import time
        start = time.perf_counter()
        ProfitabilityRatios(income=synthetic_income, balance=synthetic_balance).compute()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 10, \
            f"Profitability took {elapsed_ms:.1f}ms (limit: 10ms)"
