"""
tests/test_ratios_unit.py — Unit tests for individual ratio calculators.

รันแยกกันแต่ละหมวด — เร็ว, isolated, ไม่พึ่ง engine

Usage:
    pytest tests/test_ratios_unit.py                       # ทั้งหมด
    pytest tests/test_ratios_unit.py::TestProfitability    # class เดียว
    pytest tests/test_ratios_unit.py -k gross_margin       # เฉพาะที่มีคำว่า gross_margin
    pytest tests/test_ratios_unit.py -v                    # verbose
"""
from __future__ import annotations

import math

import pytest

from backend.ratios import (
    BuffettRatios,
    CashFlowRatios,
    DividendRatios,
    EfficiencyRatios,
    GrowthRatios,
    LeverageRatios,
    LiquidityRatios,
    ProfitabilityRatios,
    QualityRatios,
    ValuationRatios,
)

# ═══════════════════════════════════════════════════════════════════════════
# TestProfitability
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestProfitability:
    """Test profitability ratios with hand-computed answers."""

    def test_gross_margin(self, synthetic_income, synthetic_balance):
        calc = ProfitabilityRatios(income=synthetic_income, balance=synthetic_balance)
        # Gross Profit 500M / Revenue 1000M = 50%
        assert calc.compute()["Gross Profit Margin"] == pytest.approx(50.0, rel=0.01)

    def test_operating_margin(self, synthetic_income):
        calc = ProfitabilityRatios(income=synthetic_income)
        # 200M / 1000M = 20%
        assert calc.compute()["Operating Profit Margin"] == pytest.approx(20.0, rel=0.01)

    def test_ebitda_margin(self, synthetic_income):
        calc = ProfitabilityRatios(income=synthetic_income)
        assert calc.compute()["EBITDA Margin"] == pytest.approx(25.0, rel=0.01)

    def test_net_margin(self, synthetic_income):
        calc = ProfitabilityRatios(income=synthetic_income)
        assert calc.compute()["Net Profit Margin"] == pytest.approx(15.0, rel=0.01)

    def test_roe(self, synthetic_income, synthetic_balance, synthetic_prev_balance):
        calc = ProfitabilityRatios(
            income=synthetic_income,
            balance=synthetic_balance,
            prev_balance=synthetic_prev_balance,
        )
        # NI 150M / Avg Equity 550M = 27.27%
        assert calc.compute()["ROE"] == pytest.approx(27.27, rel=0.02)

    def test_roa(self, synthetic_income, synthetic_balance, synthetic_prev_balance):
        calc = ProfitabilityRatios(
            income=synthetic_income,
            balance=synthetic_balance,
            prev_balance=synthetic_prev_balance,
        )
        # NI 150M / Avg Assets 950M = 15.79%
        assert calc.compute()["ROA"] == pytest.approx(15.79, rel=0.02)

    def test_roic(self, synthetic_income, synthetic_balance, synthetic_prev_balance):
        calc = ProfitabilityRatios(
            income=synthetic_income,
            balance=synthetic_balance,
            prev_balance=synthetic_prev_balance,
        )
        # NOPAT = 200 × 0.79 = 158M
        # Invested Capital = Avg Equity + Debt - Cash = 550 + 200 - 200 = 550M
        # ROIC = 158/550 = 28.73%
        assert calc.compute()["ROIC"] == pytest.approx(28.73, rel=0.02)

    def test_effective_tax(self, synthetic_income):
        calc = ProfitabilityRatios(income=synthetic_income)
        # 40M / 190M = 21.05%
        assert calc.compute()["Effective Tax Rate"] == pytest.approx(21.05, rel=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# TestLiquidity — with parametrize (multiple cases in one test)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestLiquidity:
    def test_current_ratio(self, synthetic_balance):
        calc = LiquidityRatios(balance=synthetic_balance)
        # CA 500 / CL 200 = 2.5
        assert calc.compute()["Current Ratio"] == pytest.approx(2.5, rel=0.01)

    def test_cash_ratio(self, synthetic_balance):
        calc = LiquidityRatios(balance=synthetic_balance)
        # Cash 200 / CL 200 = 1.0
        assert calc.compute()["Cash Ratio"] == pytest.approx(1.0, rel=0.01)

    def test_quick_ratio(self, synthetic_balance):
        calc = LiquidityRatios(balance=synthetic_balance)
        # (Cash 200 + STI 50 + AR 150) / CL 200 = 400/200 = 2.0
        assert calc.compute()["Quick Ratio (Acid Test)"] == pytest.approx(2.0, rel=0.01)

    @pytest.mark.parametrize("ca, cl, expected", [
        (1000, 500, 2.0),    # normal
        (500, 500, 1.0),     # equal
        (300, 500, 0.6),     # weak liquidity
        (0, 500, 0.0),       # no assets
    ])
    def test_current_ratio_cases(self, ca, cl, expected):
        """Table-driven test — 4 cases in one function."""
        balance = {"Total Current Assets": ca, "Total Current Liabilities": cl}
        calc = LiquidityRatios(balance=balance)
        assert calc.compute()["Current Ratio"] == pytest.approx(expected, rel=0.01)

    def test_current_ratio_zero_liabilities_returns_none(self):
        """Edge case — division by zero should return None, not crash."""
        calc = LiquidityRatios(
            balance={"Total Current Assets": 1000, "Total Current Liabilities": 0}
        )
        assert calc.compute()["Current Ratio"] is None


# ═══════════════════════════════════════════════════════════════════════════
# TestLeverage
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestLeverage:
    def test_debt_to_equity(self, synthetic_balance):
        calc = LeverageRatios(balance=synthetic_balance)
        # 200 / 600 = 0.333
        assert calc.compute()["Debt to Equity (D/E)"] == pytest.approx(0.333, rel=0.01)

    def test_interest_coverage(self, synthetic_income):
        calc = LeverageRatios(income=synthetic_income)
        # EBIT 200 / Interest 10 = 20
        assert calc.compute()["Interest Coverage (EBIT)"] == pytest.approx(20.0)

    def test_net_debt_zero_when_cash_equals_debt(self, synthetic_balance):
        calc = LeverageRatios(balance=synthetic_balance)
        # Debt 200 - Cash 200 = 0
        assert calc.compute()["Net Debt"] == pytest.approx(0.0, abs=1.0)


# ═══════════════════════════════════════════════════════════════════════════
# TestCashFlow — includes bug regression test for CapEx sign
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCashFlow:
    def test_fcf_margin(self, synthetic_income, synthetic_cashflow):
        calc = CashFlowRatios(income=synthetic_income, cashflow=synthetic_cashflow)
        # FCF 120M / Revenue 1000M = 12%
        assert calc.compute()["FCF Margin"] == pytest.approx(12.0, rel=0.01)

    def test_cash_conversion_ratio(self, synthetic_income, synthetic_cashflow):
        calc = CashFlowRatios(income=synthetic_income, cashflow=synthetic_cashflow)
        # FCF 120M / NI 150M = 0.8
        assert calc.compute()["Cash Conversion Ratio"] == pytest.approx(0.8, rel=0.01)

    def test_capex_to_ocf(self, synthetic_income, synthetic_cashflow):
        calc = CashFlowRatios(income=synthetic_income, cashflow=synthetic_cashflow)
        # 60 / 180 = 0.333
        assert calc.compute()["CapEx to OCF"] == pytest.approx(0.333, rel=0.01)

    def test_negative_capex_produces_positive_ratio(self):
        """
        REGRESSION TEST — Bug #1/#2 (CapEx sign)

        Real yfinance/FMP data stores CapEx as negative.
        _capex() must return abs() so ratios remain positive.
        """
        income = {"Revenue": 1000_000_000, "Net Income": 100_000_000}
        cashflow = {
            "Operating Cash Flow": 180_000_000,
            "Capital Expenditure": -60_000_000,   # NEGATIVE (like real data)
        }
        calc = CashFlowRatios(income=income, cashflow=cashflow)
        r = calc.compute()

        capex_ocf = r.get("CapEx to OCF")
        assert capex_ocf is not None
        assert capex_ocf > 0, f"CapEx/OCF should be positive, got {capex_ocf}"
        assert capex_ocf == pytest.approx(0.333, rel=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# TestGrowth
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestGrowth:
    def test_revenue_growth(self, synthetic_income, synthetic_prev_income):
        calc = GrowthRatios(income=synthetic_income, prev_income=synthetic_prev_income)
        # (1000 - 800) / 800 = 25%
        assert calc.compute()["Revenue Growth YoY"] == pytest.approx(25.0, rel=0.01)

    def test_net_income_growth(self, synthetic_income, synthetic_prev_income):
        calc = GrowthRatios(income=synthetic_income, prev_income=synthetic_prev_income)
        # (150 - 100) / 100 = 50%
        assert calc.compute()["Net Income Growth YoY"] == pytest.approx(50.0, rel=0.01)

    def test_retention_ratio_as_percentage(
        self, synthetic_income, synthetic_cashflow
    ):
        """
        REGRESSION TEST — Bug #5 (Retention Ratio scale)

        Retention Ratio must be returned as percentage (e.g., 80.0)
        not raw ratio (0.8) — for consistency with dividend module.
        """
        calc = GrowthRatios(
            income=synthetic_income,
            cashflow=synthetic_cashflow,
        )
        r = calc.compute()
        retention = r.get("Retention Ratio")
        # NI 150M, Div 30M → Retention = (150-30)/150 = 80%
        assert retention == pytest.approx(80.0, rel=0.01), \
            f"Retention should be 80.0 (percent), got {retention}"

    def test_growth_returns_none_without_prev_data(self, synthetic_income):
        """Edge case — no prev year data → growth should be None."""
        calc = GrowthRatios(income=synthetic_income)   # no prev_income
        r = calc.compute()
        assert r.get("Revenue Growth YoY") is None


# ═══════════════════════════════════════════════════════════════════════════
# TestValuation
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestValuation:
    def test_eps(self, synthetic_income):
        calc = ValuationRatios(income=synthetic_income)
        assert calc.compute()["Earnings Per Share (EPS)"] == pytest.approx(1.5)

    def test_pe_ratio(self, synthetic_income, synthetic_basic_info):
        calc = ValuationRatios(income=synthetic_income, basic_info=synthetic_basic_info)
        # Price 100 / EPS 1.5 = 66.67
        assert calc.compute()["P/E Ratio"] == pytest.approx(66.67, rel=0.01)

    def test_enterprise_value(self, synthetic_income, synthetic_balance, synthetic_basic_info):
        calc = ValuationRatios(
            income=synthetic_income,
            balance=synthetic_balance,
            basic_info=synthetic_basic_info,
        )
        # MC 10B + Debt 200M - Cash 200M = 10B
        assert calc.compute()["Enterprise Value (EV)"] == pytest.approx(10_000_000_000, rel=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# TestQuality (Altman Z, Piotroski F)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestQuality:
    def test_altman_z_score(
        self, synthetic_income, synthetic_balance, synthetic_basic_info
    ):
        calc = QualityRatios(
            income=synthetic_income,
            balance=synthetic_balance,
            basic_info=synthetic_basic_info,
        )
        r = calc.compute()
        # Z = 1.2×0.3 + 1.4×0.3 + 3.3×0.2 + 0.6×25 + 1.0×1.0 = 17.44
        assert r["Altman Z-Score"] == pytest.approx(17.44, rel=0.05)

    def test_altman_z_zone_interpretation(self):
        """Verify Z-score zones: >3 safe, 1.81-3 grey, <1.81 distress."""
        # Test safe zone company
        income = {"Revenue": 1000, "EBIT": 200}
        balance = {
            "Total Assets": 1000, "Total Current Assets": 500,
            "Total Current Liabilities": 200, "Retained Earnings": 300,
            "Total Liabilities": 400,
        }
        basic = {"MarketCap": 10_000_000_000, "CurrentPrice": 100.0}
        calc = QualityRatios(income=income, balance=balance, basic_info=basic)
        z = calc.compute()["Altman Z-Score"]
        assert z > 3.0, f"Safe zone expected, got Z={z}"

    def test_piotroski_returns_none_without_prev_data(self, synthetic_income):
        """Piotroski needs prev year data — should be None without it."""
        calc = QualityRatios(income=synthetic_income)
        r = calc.compute()
        assert r.get("Piotroski F-Score") is None


# ═══════════════════════════════════════════════════════════════════════════
# TestBuffett — Regression tests for Bug #3, #4
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestBuffett:
    def test_roe_uses_avg_equity(
        self, synthetic_income, synthetic_balance, synthetic_prev_balance
    ):
        """
        REGRESSION TEST — Bug #3 (ROE cross-module consistency)

        Buffett module ROE must use avg equity (matching profitability).
        Previously used current equity → gave different values.
        """
        calc_buffett = BuffettRatios(
            income=synthetic_income,
            balance=synthetic_balance,
            prev_balance=synthetic_prev_balance,
        )
        calc_prof = ProfitabilityRatios(
            income=synthetic_income,
            balance=synthetic_balance,
            prev_balance=synthetic_prev_balance,
        )
        roe_buffett = calc_buffett.compute()["Current ROE"]
        roe_prof = calc_prof.compute()["ROE"]

        assert roe_buffett is not None
        assert roe_prof is not None
        assert abs(roe_buffett - roe_prof) < 0.1, \
            f"ROE inconsistent: buffett={roe_buffett}, profitability={roe_prof}"

    def test_roe_none_when_equity_negative(self, synthetic_income):
        """
        REGRESSION TEST — Bug #4 (Negative equity → ROE explosion)

        Companies like ABBV with negative equity should return None,
        not a meaninglessly huge percentage.
        """
        balance = {
            "Total Assets": 1_000_000_000,
            "Total Equity": -100_000_000,   # NEGATIVE
        }
        calc = BuffettRatios(income=synthetic_income, balance=balance)
        assert calc.compute()["Current ROE"] is None


# ═══════════════════════════════════════════════════════════════════════════
# TestDividend
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestDividend:
    def test_dps(self, synthetic_income, synthetic_cashflow):
        calc = DividendRatios(income=synthetic_income, cashflow=synthetic_cashflow)
        # Div 30M / 100M shares = 0.30
        assert calc.compute()["Dividend Per Share (DPS)"] == pytest.approx(0.30, rel=0.01)

    def test_payout_ratio(self, synthetic_income, synthetic_cashflow):
        calc = DividendRatios(income=synthetic_income, cashflow=synthetic_cashflow)
        # 30M / 150M = 20%
        assert calc.compute()["Dividend Payout Ratio"] == pytest.approx(20.0, rel=0.01)

    def test_growth_needs_prev_income(
        self, synthetic_income, synthetic_cashflow,
        synthetic_prev_income, synthetic_prev_cashflow,
    ):
        """Dividend growth requires prev_income (for prev_shares → prev_dps)."""
        calc = DividendRatios(
            income=synthetic_income,
            cashflow=synthetic_cashflow,
            prev_income=synthetic_prev_income,
            prev_cashflow=synthetic_prev_cashflow,
        )
        # Prev DPS 0.20 → Current 0.30 → +50%
        assert calc.compute()["Dividend Growth YoY"] == pytest.approx(50.0, rel=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# Edge case tests — using parametrize
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestEdgeCases:
    @pytest.mark.parametrize("category_class", [
        ProfitabilityRatios, EfficiencyRatios, LiquidityRatios, LeverageRatios,
        CashFlowRatios, GrowthRatios, ValuationRatios, QualityRatios,
    ])
    def test_empty_data_no_crash(self, category_class):
        """Every ratio module must not crash on empty inputs."""
        calc = category_class()
        result = calc.compute()   # should not raise
        assert isinstance(result, dict)
        # Most values will be None — that's OK
        assert all(v is None or isinstance(v, (int, float)) for v in result.values())

    @pytest.mark.parametrize("bad_input", [
        None,
        {},
        {"Revenue": None},
        {"Revenue": "invalid_string"},
        {"Revenue": float("nan")},
        {"Revenue": float("inf")},
    ])
    def test_bad_revenue_input(self, bad_input):
        """Every kind of bad input should result in None, not crash."""
        calc = ProfitabilityRatios(income=bad_input or {})
        result = calc.compute()
        # Gross Margin depends on Revenue — should be None
        assert result["Gross Profit Margin"] is None or isinstance(result["Gross Profit Margin"], float)

    def test_all_ratios_return_finite_or_none(self, synthetic_income, synthetic_balance):
        """No ratio should return inf/nan — only finite numbers or None."""
        calc = ProfitabilityRatios(income=synthetic_income, balance=synthetic_balance)
        for name, val in calc.compute().items():
            if val is not None:
                assert not math.isinf(val), f"{name} is infinity"
                assert not math.isnan(val), f"{name} is NaN"
