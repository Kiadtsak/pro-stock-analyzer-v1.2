"""
tests/test_property_based.py — Property-based tests using Hypothesis.

แทนที่จะเทสด้วยตัวอย่างที่เราคิดขึ้นเอง — ให้ Hypothesis สุ่มมั่วให้ 1000+ ครั้ง
มันจะหา edge cases ที่เราไม่นึกถึง

Usage:
    pip install hypothesis
    pytest tests/test_property_based.py
    pytest tests/test_property_based.py --hypothesis-show-statistics
"""
from __future__ import annotations

import math

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from backend.ratios import (
    CashFlowRatios,
    GrowthRatios,
    LiquidityRatios,
    ProfitabilityRatios,
    ValuationRatios,
)

# ═══════════════════════════════════════════════════════════════════════════
# Strategies — how to generate random financial data
# ═══════════════════════════════════════════════════════════════════════════

# Realistic magnitudes for financial data
positive_money = st.floats(min_value=1_000, max_value=1e12, allow_nan=False, allow_infinity=False)
any_money = st.floats(min_value=-1e11, max_value=1e12, allow_nan=False, allow_infinity=False)
positive_ratio = st.floats(min_value=0.01, max_value=100, allow_nan=False, allow_infinity=False)
price = st.floats(min_value=0.01, max_value=10000, allow_nan=False, allow_infinity=False)
shares = st.floats(min_value=1_000_000, max_value=100_000_000_000, allow_nan=False)


# ═══════════════════════════════════════════════════════════════════════════
# Property tests — invariants that must ALWAYS hold
# ═══════════════════════════════════════════════════════════════════════════

class TestProfitabilityProperties:
    @given(revenue=positive_money, gross_profit=any_money)
    @settings(max_examples=200)
    def test_gross_margin_never_crashes(self, revenue, gross_profit):
        """No matter what values, must not crash."""
        income = {"Revenue": revenue, "Gross Profit": gross_profit}
        calc = ProfitabilityRatios(income=income)
        result = calc.compute()   # must not raise
        assert isinstance(result, dict)

    @given(
        revenue=positive_money,
        gross_profit=positive_money,
    )
    def test_gross_margin_always_returns_finite_or_none(self, revenue, gross_profit):
        """Returns must be finite float or None — never inf/nan."""
        income = {"Revenue": revenue, "Gross Profit": gross_profit}
        calc = ProfitabilityRatios(income=income)
        result = calc.compute()
        gm = result.get("Gross Profit Margin")
        if gm is not None:
            assert math.isfinite(gm)

    @given(
        revenue=st.floats(min_value=1e6, max_value=1e12),
        gp_ratio=st.floats(min_value=0.05, max_value=0.9),  # 5-90% margin
    )
    def test_gross_margin_matches_manual_calc(self, revenue, gp_ratio):
        """Gross margin must equal (GP/Revenue) × 100."""
        gross_profit = revenue * gp_ratio
        income = {"Revenue": revenue, "Gross Profit": gross_profit}
        calc = ProfitabilityRatios(income=income)
        gm = calc.compute()["Gross Profit Margin"]
        expected = gp_ratio * 100
        assert gm == pytest.approx(expected, rel=0.001)


class TestLiquidityProperties:
    @given(ca=positive_money, cl=positive_money)
    def test_current_ratio_is_ca_over_cl(self, ca, cl):
        balance = {"Total Current Assets": ca, "Total Current Liabilities": cl}
        calc = LiquidityRatios(balance=balance)
        cr = calc.compute()["Current Ratio"]
        assert cr == pytest.approx(ca / cl, rel=0.001)

    @given(ca=positive_money)
    def test_current_ratio_with_zero_liabilities_is_none(self, ca):
        """Zero denominator must return None, not inf."""
        balance = {"Total Current Assets": ca, "Total Current Liabilities": 0}
        calc = LiquidityRatios(balance=balance)
        assert calc.compute()["Current Ratio"] is None


class TestValuationProperties:
    @given(price=price, eps=st.floats(min_value=0.01, max_value=1000))
    def test_pe_ratio_matches_price_over_eps(self, price, eps):
        """P/E = Price / EPS."""
        income = {
            "Earnings Per Share": eps,
            "Net Income": eps * 100_000_000,
            "Weighted Average Shares Diluted": 100_000_000,
        }
        basic_info = {"CurrentPrice": price}
        calc = ValuationRatios(income=income, basic_info=basic_info)
        pe = calc.compute()["P/E Ratio"]
        assert pe == pytest.approx(price / eps, rel=0.01)

    @given(price=price, eps=st.floats(min_value=-1000, max_value=0))
    def test_pe_ratio_negative_eps_still_returns_finite(self, price, eps):
        """Negative EPS should still return finite (or None), not inf."""
        assume(eps != 0)
        income = {
            "Earnings Per Share": eps,
            "Net Income": eps * 100_000_000,
            "Weighted Average Shares Diluted": 100_000_000,
        }
        calc = ValuationRatios(income=income, basic_info={"CurrentPrice": price})
        pe = calc.compute()["P/E Ratio"]
        if pe is not None:
            assert math.isfinite(pe)


class TestCashFlowProperties:
    @given(
        ocf=positive_money,
        capex=st.floats(min_value=-1e11, max_value=1e11),
    )
    def test_fcf_via_capex_always_positive_ratios(self, ocf, capex):
        """
        REGRESSION property — CapEx/OCF must always be positive
        regardless of CapEx sign.
        """
        cashflow = {
            "Operating Cash Flow": ocf,
            "Capital Expenditure": capex,
        }
        calc = CashFlowRatios(cashflow=cashflow)
        r = calc.compute()
        capex_ocf = r.get("CapEx to OCF")
        if capex_ocf is not None:
            assert capex_ocf >= 0, \
                f"CapEx/OCF must be non-negative, got {capex_ocf} for capex={capex}"


class TestGrowthProperties:
    @given(
        cur=st.floats(min_value=1, max_value=1e12),
        prev=st.floats(min_value=1, max_value=1e12),
    )
    def test_revenue_growth_formula(self, cur, prev):
        """Growth = (cur - prev) / abs(prev) × 100."""
        income = {"Revenue": cur, "Net Income": 100_000, "Weighted Average Shares Diluted": 1_000_000}
        prev_income = {"Revenue": prev, "Net Income": 100_000, "Weighted Average Shares Diluted": 1_000_000}
        calc = GrowthRatios(income=income, prev_income=prev_income)
        g = calc.compute()["Revenue Growth YoY"]
        expected = (cur - prev) / abs(prev) * 100
        assert g == pytest.approx(expected, rel=0.001)


# ═══════════════════════════════════════════════════════════════════════════
# Stateful property test — sequences of operations
# ═══════════════════════════════════════════════════════════════════════════

class TestScaleInvariance:
    """
    Ratios should be scale-invariant — if you multiply all monetary values
    by the same factor, ratios shouldn't change.
    """

    @given(scale=st.floats(min_value=0.1, max_value=1000))
    def test_gross_margin_scale_invariant(self, scale):
        """Gross Margin should be the same in millions or billions."""
        base = {"Revenue": 1000, "Gross Profit": 500}
        scaled = {"Revenue": 1000 * scale, "Gross Profit": 500 * scale}
        calc1 = ProfitabilityRatios(income=base)
        calc2 = ProfitabilityRatios(income=scaled)
        assert calc1.compute()["Gross Profit Margin"] == \
               pytest.approx(calc2.compute()["Gross Profit Margin"], rel=0.001)

    @given(scale=st.floats(min_value=0.1, max_value=1000))
    def test_current_ratio_scale_invariant(self, scale):
        base = {"Total Current Assets": 100, "Total Current Liabilities": 50}
        scaled = {"Total Current Assets": 100 * scale, "Total Current Liabilities": 50 * scale}
        assert LiquidityRatios(balance=base).compute()["Current Ratio"] == \
               pytest.approx(LiquidityRatios(balance=scaled).compute()["Current Ratio"], rel=0.001)
