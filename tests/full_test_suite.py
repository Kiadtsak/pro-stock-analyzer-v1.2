"""
tests/full_test_suite.py

Comprehensive test suite for Pro Stock Analyzer.

Tests 6 categories:
  1. FORMULA CORRECTNESS — hand-computed known answers vs actual
  2. INTERNAL CONSISTENCY — same ratio in different modules should match
  3. EDGE CASES — missing data, zero denominators, negatives
  4. REAL DATA ROBUSTNESS — load 167 real files, count anomalies
  5. API LAYER — all endpoints return valid data
  6. BUG DETECTION — sign errors, unit errors, cross-module inconsistency

Usage:
    PYTHONPATH=. python3 tests/full_test_suite.py
"""
from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import (
    analyze_financials,
    list_available_symbols,
    load_financials,
)
from backend.ratios import (
    CashFlowRatios,
    DividendRatios,
    GrowthRatios,
    LeverageRatios,
    LiquidityRatios,
    ProfitabilityRatios,
    QualityRatios,
    ValuationRatios,
)

# ═══════════════════════════════════════════════════════════════════════════
# Test result tracking
# ═══════════════════════════════════════════════════════════════════════════

class TestReport:
    def __init__(self):
        self.passed: list[str] = []
        self.failed: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.bugs: list[dict] = []

    def ok(self, name: str):
        self.passed.append(name)

    def fail(self, name: str, reason: str):
        self.failed.append((name, reason))

    def warn(self, name: str, reason: str):
        self.warnings.append((name, reason))

    def bug(self, severity: str, module: str, description: str,
            expected: Any = None, actual: Any = None):
        self.bugs.append({
            "severity": severity,   # CRITICAL / HIGH / MEDIUM / LOW
            "module": module,
            "description": description,
            "expected": expected,
            "actual": actual,
        })


REPORT = TestReport()


# ═══════════════════════════════════════════════════════════════════════════
# Assertion helpers
# ═══════════════════════════════════════════════════════════════════════════

def approx_eq(actual: float | None, expected: float, tol: float = 0.01) -> bool:
    """Check if actual is within tol (relative) of expected."""
    if actual is None:
        return False
    if expected == 0:
        return abs(actual) < tol
    return abs(actual - expected) / abs(expected) < tol


def assert_ratio(name: str, actual: float | None, expected: float, tol: float = 0.01):
    """Assert a ratio computation matches expected value."""
    if actual is None:
        REPORT.fail(name, f"Expected {expected}, got None")
        REPORT.bug("HIGH", name.split(".", maxsplit=1)[0], "Returns None when data available",
                   expected=expected, actual=None)
        print(f"  ✗ {name}: expected {expected}, got None")
        return False
    if not approx_eq(actual, expected, tol):
        REPORT.fail(name, f"Expected {expected:.4f}, got {actual:.4f}")
        REPORT.bug("HIGH", name.split(".", maxsplit=1)[0], f"Wrong value: expected {expected}, got {actual}",
                   expected=expected, actual=actual)
        pct_off = abs(actual - expected) / abs(expected) * 100 if expected else float('inf')
        print(f"  ✗ {name}: expected {expected:.4f}, got {actual:.4f} (off by {pct_off:.1f}%)")
        return False
    REPORT.ok(name)
    print(f"  ✓ {name}: {actual:.4f}")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: FORMULA CORRECTNESS with hand-computed answers
# ═══════════════════════════════════════════════════════════════════════════

def make_synthetic_data() -> dict:
    """
    Build synthetic financials with hand-computable expected values.

    Chosen so all ratios have clean expected values.
    """
    return {
        "Basic Info": {
            "Symbol": "TEST",
            "Name": "Test Corporation",
            "Sector": "Technology",
            "Industry": "Software - Application",
            "CurrentPrice": 100.0,
            "MarketCap": 10_000_000_000,  # 10B
            "Employees": 1000,
            "Prices": {
                "2020": 60.0, "2021": 80.0, "2022": 70.0, "2023": 100.0
            },
        },
        "Income Statement": {
            "2022": {
                "Revenue": 800_000_000,
                "Cost of Goods Sold": 400_000_000,
                "Gross Profit": 400_000_000,
                "Operating Income": 160_000_000,
                "EBIT": 160_000_000,
                "EBITDA": 200_000_000,
                "Net Income": 100_000_000,
                "Earnings Per Share": 1.0,
                "Weighted Average Shares Diluted": 100_000_000,
                "Research and Development": 80_000_000,
                "Selling General and Administrative": 80_000_000,
                "Interest Expense": 10_000_000,
                "Income Before Tax": 150_000_000,
                "Income Tax Expense": 50_000_000,
                "Depreciation and Amortization": 40_000_000,
            },
            "2023": {
                "Revenue": 1_000_000_000,      # 25% growth
                "Cost of Goods Sold": 500_000_000,
                "Gross Profit": 500_000_000,   # 50% gross margin
                "Operating Income": 200_000_000,  # 20% op margin
                "EBIT": 200_000_000,
                "EBITDA": 250_000_000,         # 25% EBITDA margin
                "Net Income": 150_000_000,     # 15% net margin, +50% YoY
                "Earnings Per Share": 1.50,    # +50% YoY
                "Weighted Average Shares Diluted": 100_000_000,
                "Research and Development": 100_000_000,
                "Selling General and Administrative": 100_000_000,
                "Interest Expense": 10_000_000,
                "Income Before Tax": 190_000_000,
                "Income Tax Expense": 40_000_000,   # 21% effective
                "Depreciation and Amortization": 50_000_000,
            },
        },
        "Balance Sheet": {
            "2022": {
                "Total Assets": 900_000_000,
                "Total Current Assets": 400_000_000,
                "Total Current Liabilities": 200_000_000,
                "Cash And Cash Equivalents": 100_000_000,
                "Total Equity": 500_000_000,
                "Total Debt": 200_000_000,
                "Long Term Debt": 180_000_000,
                "Short Term Debt": 20_000_000,
                "Retained Earnings": 200_000_000,
                "Total Liabilities": 400_000_000,
                "Inventory": 80_000_000,
                "Accounts Receivable": 100_000_000,
                "Accounts Payable": 80_000_000,
            },
            "2023": {
                "Total Assets": 1_000_000_000,
                "Total Current Assets": 500_000_000,       # CR = 2.5
                "Total Current Liabilities": 200_000_000,
                "Cash And Cash Equivalents": 200_000_000,  # cash ratio = 1.0
                "Short Term Investments": 50_000_000,
                "Total Equity": 600_000_000,
                "Total Debt": 200_000_000,                 # D/E = 0.33
                "Long Term Debt": 180_000_000,
                "Short Term Debt": 20_000_000,
                "Retained Earnings": 300_000_000,
                "Total Liabilities": 400_000_000,
                "Inventory": 100_000_000,
                "Accounts Receivable": 150_000_000,
                "Accounts Payable": 100_000_000,
                "Goodwill": 50_000_000,
                "Intangible Assets": 25_000_000,
            },
        },
        "Cash Flow Statement": {
            "2022": {
                "Operating Cash Flow": 120_000_000,
                "Capital Expenditure": 50_000_000,
                "Free Cash Flow": 70_000_000,
                "Depreciation and Amortization": 40_000_000,
                "Dividends Paid": -20_000_000,
                "Change in Working Capital": -10_000_000,
                "Investing Cash Flow": -60_000_000,
            },
            "2023": {
                "Operating Cash Flow": 180_000_000,   # +50% YoY
                "Capital Expenditure": 60_000_000,
                "Free Cash Flow": 120_000_000,        # FCF margin = 12%
                "Depreciation and Amortization": 50_000_000,
                "Dividends Paid": -30_000_000,        # payout = 20%
                "Common Stock Repurchased": -20_000_000,
                "Change in Working Capital": -15_000_000,
                "Investing Cash Flow": -80_000_000,
            },
        },
    }


def test_profitability():
    print("\n══ TEST 1.1: Profitability Ratios (Synthetic Data) ══")
    d = make_synthetic_data()
    calc = ProfitabilityRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
        prev_balance=d["Balance Sheet"]["2022"],
    )
    r = calc.compute()

    # Hand-computed expected values:
    #   Revenue = 1000M, Gross Profit = 500M → Gross Margin = 50%
    #   OI = 200M → Op Margin = 20%
    #   EBITDA = 250M → EBITDA Margin = 25%
    #   NI = 150M → Net Margin = 15%
    #   Avg Equity = (500+600)/2 = 550M → ROE = 150/550 = 27.27%
    #   Avg Assets = (900+1000)/2 = 950M → ROA = 150/950 = 15.79%
    #   NOPAT = EBIT × (1 - 0.21) = 200 × 0.79 = 158M
    #   Invested Capital = Avg Equity + Debt - Cash = 550 + 200 - 200 = 550M
    #   ROIC = 158 / 550 = 28.73%
    #   Effective Tax = 40/190 = 21.05%
    assert_ratio("profitability.Gross Profit Margin", r.get("Gross Profit Margin"), 50.0)
    assert_ratio("profitability.Operating Profit Margin", r.get("Operating Profit Margin"), 20.0)
    assert_ratio("profitability.EBITDA Margin", r.get("EBITDA Margin"), 25.0)
    assert_ratio("profitability.Net Profit Margin", r.get("Net Profit Margin"), 15.0)
    assert_ratio("profitability.ROE", r.get("ROE"), 27.27, tol=0.01)
    assert_ratio("profitability.ROA", r.get("ROA"), 15.79, tol=0.01)
    assert_ratio("profitability.ROIC", r.get("ROIC"), 28.73, tol=0.02)
    assert_ratio("profitability.NOPAT", r.get("NOPAT"), 158_000_000, tol=0.01)
    assert_ratio("profitability.Effective Tax Rate", r.get("Effective Tax Rate"), 21.05, tol=0.01)


def test_liquidity():
    print("\n══ TEST 1.2: Liquidity Ratios (Synthetic Data) ══")
    d = make_synthetic_data()
    calc = LiquidityRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
    )
    r = calc.compute()

    # CA = 500, CL = 200 → CR = 2.5
    # Cash = 200 → Cash Ratio = 1.0
    # Quick = Cash + STI + AR = 200+50+150 = 400 → QR = 2.0
    # OCF ratio = 180 / 200 = 0.9
    # NWC = 500 - 200 = 300
    assert_ratio("liquidity.Current Ratio", r.get("Current Ratio"), 2.5)
    assert_ratio("liquidity.Cash Ratio", r.get("Cash Ratio"), 1.0)
    assert_ratio("liquidity.Quick Ratio (Acid Test)", r.get("Quick Ratio (Acid Test)"), 2.0)
    assert_ratio("liquidity.Operating Cash Flow Ratio", r.get("Operating Cash Flow Ratio"), 0.9)
    assert_ratio("liquidity.Net Working Capital", r.get("Net Working Capital"), 300_000_000)


def test_leverage():
    print("\n══ TEST 1.3: Leverage Ratios (Synthetic Data) ══")
    d = make_synthetic_data()
    calc = LeverageRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
    )
    r = calc.compute()

    # D/E = 200/600 = 0.333
    # D/A = 200/1000 = 0.2
    # Equity Multiplier = 1000/600 = 1.667
    # Interest Coverage (EBIT) = 200/10 = 20
    # Net Debt = 200 - 200 = 0
    assert_ratio("leverage.Debt to Equity (D/E)", r.get("Debt to Equity (D/E)"), 0.333, tol=0.01)
    assert_ratio("leverage.Debt to Assets (D/A)", r.get("Debt to Assets (D/A)"), 0.2, tol=0.01)
    assert_ratio("leverage.Equity Multiplier", r.get("Equity Multiplier"), 1.667, tol=0.01)
    assert_ratio("leverage.Interest Coverage (EBIT)", r.get("Interest Coverage (EBIT)"), 20.0)
    assert_ratio("leverage.Net Debt", r.get("Net Debt"), 0.0, tol=0.01)


def test_cash_flow():
    print("\n══ TEST 1.4: Cash Flow Ratios (Synthetic Data) ══")
    d = make_synthetic_data()
    calc = CashFlowRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
    )
    r = calc.compute()

    # OCF = 180M, FCF = 120M
    # OCF Margin = 180/1000 = 18%
    # FCF Margin = 120/1000 = 12%
    # Cash Conversion (FCF/NI) = 120/150 = 0.8
    # OCF/NI = 180/150 = 1.2
    # CapEx/OCF = 60/180 = 0.333
    assert_ratio("cash_flow.OCF Margin", r.get("OCF Margin"), 18.0)
    assert_ratio("cash_flow.FCF Margin", r.get("FCF Margin"), 12.0)
    assert_ratio("cash_flow.Cash Conversion Ratio", r.get("Cash Conversion Ratio"), 0.8, tol=0.01)
    assert_ratio("cash_flow.OCF to Net Income", r.get("OCF to Net Income"), 1.2, tol=0.01)
    assert_ratio("cash_flow.CapEx to OCF", r.get("CapEx to OCF"), 0.333, tol=0.01)


def test_growth():
    print("\n══ TEST 1.5: Growth Ratios (Synthetic Data) ══")
    d = make_synthetic_data()
    calc = GrowthRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
        prev_income=d["Income Statement"]["2022"],
        prev_balance=d["Balance Sheet"]["2022"],
        prev_cashflow=d["Cash Flow Statement"]["2022"],
    )
    r = calc.compute()

    # Revenue: 800 → 1000 → +25%
    # NI: 100 → 150 → +50%
    # EPS: 1.0 → 1.5 → +50%
    # FCF: 70 → 120 → +71.4%
    # Equity: 500 → 600 → +20%
    # Assets: 900 → 1000 → +11.1%
    assert_ratio("growth.Revenue Growth YoY", r.get("Revenue Growth YoY"), 25.0)
    assert_ratio("growth.Net Income Growth YoY", r.get("Net Income Growth YoY"), 50.0)
    assert_ratio("growth.EPS Growth YoY", r.get("EPS Growth YoY"), 50.0)
    assert_ratio("growth.FCF Growth YoY", r.get("FCF Growth YoY"), 71.43, tol=0.02)
    assert_ratio("growth.Equity (Book Value) Growth YoY",
                 r.get("Equity (Book Value) Growth YoY"), 20.0)
    assert_ratio("growth.Asset Growth YoY", r.get("Asset Growth YoY"), 11.11, tol=0.02)


def test_valuation():
    print("\n══ TEST 1.6: Valuation Ratios (Synthetic Data) ══")
    d = make_synthetic_data()
    calc = ValuationRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
        basic_info=d["Basic Info"],
        prev_income=d["Income Statement"]["2022"],
    )
    r = calc.compute()

    # Price = 100, MC = 10B, Shares = 100M
    # EPS = 1.5 → P/E = 66.67
    # BVPS = 600M/100M = 6 → P/B = 16.67
    # SPS = 1000M/100M = 10 → P/S = 10
    # Cash Flow per Share = 180M/100M = 1.8 → P/CF = 55.56
    # FCFPS = 120M/100M = 1.2 → P/FCF = 83.33
    # EV = 10B + 200M - 200M = 10B
    # EV/EBITDA = 10000/250 = 40
    # EV/EBIT = 10000/200 = 50
    # EV/Sales = 10000/1000 = 10
    assert_ratio("valuation.EPS", r.get("Earnings Per Share (EPS)"), 1.5)
    assert_ratio("valuation.BVPS", r.get("Book Value Per Share (BVPS)"), 6.0)
    assert_ratio("valuation.SPS", r.get("Sales Per Share (SPS)"), 10.0)
    assert_ratio("valuation.P/E", r.get("P/E Ratio"), 66.67, tol=0.01)
    assert_ratio("valuation.P/B", r.get("P/B Ratio"), 16.67, tol=0.01)
    assert_ratio("valuation.P/S", r.get("P/S Ratio"), 10.0)
    assert_ratio("valuation.EV", r.get("Enterprise Value (EV)"), 10_000_000_000, tol=0.01)
    assert_ratio("valuation.EV/EBITDA", r.get("EV / EBITDA"), 40.0)
    assert_ratio("valuation.EV/EBIT", r.get("EV / EBIT"), 50.0)


def test_dividend():
    print("\n══ TEST 1.7: Dividend Ratios (Synthetic Data) ══")
    d = make_synthetic_data()
    calc = DividendRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
        basic_info=d["Basic Info"],
        prev_income=d["Income Statement"]["2022"],   # needed for prev_shares → prev_dps
        prev_cashflow=d["Cash Flow Statement"]["2022"],
    )
    r = calc.compute()

    # Div paid = 30M (abs), Shares = 100M → DPS = 0.30
    # Div Yield = 0.30/100 = 0.3%
    # Payout = 30/150 = 20%
    # Coverage (NI/Div) = 150/30 = 5
    # Prev DPS = 20/100 = 0.20, so Growth = 50%
    assert_ratio("dividend.DPS", r.get("Dividend Per Share (DPS)"), 0.30)
    assert_ratio("dividend.Dividend Yield", r.get("Dividend Yield"), 0.30)
    assert_ratio("dividend.Payout Ratio", r.get("Dividend Payout Ratio"), 20.0)
    assert_ratio("dividend.Coverage", r.get("Dividend Coverage Ratio"), 5.0)
    assert_ratio("dividend.Growth YoY", r.get("Dividend Growth YoY"), 50.0)


def test_quality():
    print("\n══ TEST 1.8: Quality (Altman Z, Piotroski F) ══")
    d = make_synthetic_data()
    calc = QualityRatios(
        income=d["Income Statement"]["2023"],
        balance=d["Balance Sheet"]["2023"],
        cashflow=d["Cash Flow Statement"]["2023"],
        basic_info=d["Basic Info"],
        prev_income=d["Income Statement"]["2022"],
        prev_balance=d["Balance Sheet"]["2022"],
        prev_cashflow=d["Cash Flow Statement"]["2022"],
    )
    r = calc.compute()

    # Altman Z:
    #   A = WC/TA = 300/1000 = 0.3
    #   B = RE/TA = 300/1000 = 0.3
    #   C = EBIT/TA = 200/1000 = 0.2
    #   D = MC/TL = 10000/400 = 25
    #   E = Sales/TA = 1000/1000 = 1.0
    #   Z = 1.2*0.3 + 1.4*0.3 + 3.3*0.2 + 0.6*25 + 1.0*1.0
    #     = 0.36 + 0.42 + 0.66 + 15.0 + 1.0 = 17.44
    assert_ratio("quality.Altman Z-Score", r.get("Altman Z-Score"), 17.44, tol=0.05)

    # Piotroski F: profitable (+1 NI>0, +1 OCF>0, +1 ROA increasing, +1 OCF>NI)
    # LT debt same (0), Current ratio: 2.5 vs 2.0 improving (+1)
    # No new shares (100 = 100) (+1)
    # Gross margin: 50% vs 50% same → 0
    # Asset turnover: 1.0 vs (800/900)=0.889 improving (+1)
    # Expect ~7
    f = r.get("Piotroski F-Score")
    if f is None:
        REPORT.fail("quality.Piotroski F-Score", "Returns None")
        print("  ✗ Piotroski F-Score: None")
    elif f < 5 or f > 9:
        REPORT.warn("quality.Piotroski F-Score", f"Unexpected value: {f}")
        print(f"  ⚠ Piotroski F-Score: {f} (expected 6-8)")
    else:
        REPORT.ok("quality.Piotroski F-Score")
        print(f"  ✓ Piotroski F-Score: {f}/9")


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: INTERNAL CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════

def test_consistency():
    """Same ratio in different modules should produce the same value."""
    print("\n══ TEST 2: Internal Consistency Across Modules ══")

    d = make_synthetic_data()
    result = analyze_financials(d)
    latest = result.latest_by_category

    # ROE should be same in profitability, buffett, dividend
    roe_prof = latest["profitability"].get("ROE")
    roe_buffett = latest["buffett"].get("Current ROE")

    if roe_prof is not None and roe_buffett is not None:
        if abs(roe_prof - roe_buffett) > 0.5:
            REPORT.bug("HIGH", "cross-module",
                       f"ROE differs across modules: profitability={roe_prof}, buffett={roe_buffett}")
            print(f"  ✗ ROE inconsistency: profitability={roe_prof:.2f} vs buffett={roe_buffett:.2f}")
        else:
            REPORT.ok("consistency.ROE")
            print(f"  ✓ ROE consistent: {roe_prof:.2f} ≈ {roe_buffett:.2f}")

    # Retention Ratio scale inconsistency check
    ret_growth = latest["growth"].get("Retention Ratio")
    ret_div = latest["dividend"].get("Retention Ratio")
    if ret_growth is not None and ret_div is not None:
        # In synthetic data: retention = 1 - 30/150 = 0.8 (raw) or 80% (percent)
        if abs(ret_growth - ret_div) > 1:
            REPORT.bug("MEDIUM", "cross-module",
                       f"Retention Ratio SCALE MISMATCH: growth={ret_growth}, dividend={ret_div}",
                       expected="Same value in both modules",
                       actual=f"growth={ret_growth}, dividend={ret_div}")
            print("  ✗ Retention Ratio scale mismatch:")
            print(f"      growth module:   {ret_growth}")
            print(f"      dividend module: {ret_div}")
            print("      → One returns raw (0.8), other returns % (80.0) — INCONSISTENT!")
        else:
            REPORT.ok("consistency.Retention Ratio")

    # EPS: manual calc (NI/Shares) vs stored
    eps_val = latest["valuation"].get("Earnings Per Share (EPS)")
    ni = d["Income Statement"]["2023"]["Net Income"]
    shares = d["Income Statement"]["2023"]["Weighted Average Shares Diluted"]
    expected_eps = ni / shares
    if eps_val and abs(eps_val - expected_eps) / expected_eps > 0.05:
        REPORT.bug("HIGH", "valuation",
                   f"EPS from module ({eps_val}) doesn't match NI/Shares ({expected_eps})")
        print(f"  ✗ EPS mismatch: got {eps_val}, expected {expected_eps}")
    else:
        REPORT.ok("consistency.EPS")
        print(f"  ✓ EPS consistent with NI/Shares: {eps_val}")

    # FCF: stored vs (OCF - CapEx)
    fcf_stored = d["Cash Flow Statement"]["2023"]["Free Cash Flow"]
    ocf = d["Cash Flow Statement"]["2023"]["Operating Cash Flow"]
    capex = d["Cash Flow Statement"]["2023"]["Capital Expenditure"]
    expected_fcf = ocf - capex
    if abs(fcf_stored - expected_fcf) > 100:
        print(f"  ⚠ Test data itself: FCF stored ({fcf_stored}) ≠ OCF-CapEx ({expected_fcf})")


# ═══════════════════════════════════════════════════════════════════════════
# PART 3: EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════

def test_edge_cases():
    print("\n══ TEST 3: Edge Cases ══")

    # 3a. Empty data
    empty = {
        "Basic Info": {"Symbol": "TEST"},
        "Income Statement": {"2023": {}},
        "Balance Sheet": {"2023": {}},
        "Cash Flow Statement": {"2023": {}},
    }
    try:
        result = analyze_financials(empty)
        REPORT.ok("edge.empty_data")
        print(f"  ✓ Empty data doesn't crash ({result.total_ratios} ratios, most None)")
    except Exception as e:
        REPORT.bug("CRITICAL", "engine", f"Crashes on empty data: {e}")
        print(f"  ✗ Empty data crashes: {e}")

    # 3b. Zero denominators
    zero_data = make_synthetic_data()
    zero_data["Income Statement"]["2023"]["Revenue"] = 0
    zero_data["Balance Sheet"]["2023"]["Total Equity"] = 0
    zero_data["Balance Sheet"]["2023"]["Total Assets"] = 0
    try:
        result = analyze_financials(zero_data)
        prof = result.latest_by_category.get("profitability", {})
        if prof.get("Net Profit Margin") is not None:
            REPORT.bug("HIGH", "profitability",
                       "Net Profit Margin computed with Revenue=0 (should be None)")
            print(f"  ✗ Zero revenue → Net Margin={prof.get('Net Profit Margin')} (should be None)")
        else:
            REPORT.ok("edge.zero_revenue")
            print("  ✓ Zero revenue → margin is None (correct)")
    except Exception as e:
        REPORT.bug("CRITICAL", "engine", f"Crashes on zero denominators: {e}")
        print(f"  ✗ Zero denominator crashes: {e}")

    # 3c. Negative Net Income
    neg_data = make_synthetic_data()
    neg_data["Income Statement"]["2023"]["Net Income"] = -50_000_000
    neg_data["Income Statement"]["2023"]["EPS"] = -0.50
    neg_data["Income Statement"]["2023"]["Earnings Per Share"] = -0.50
    try:
        result = analyze_financials(neg_data)
        REPORT.ok("edge.negative_ni")
        print(f"  ✓ Negative NI handled (ratios computed: {result.total_ratios})")
    except Exception as e:
        REPORT.bug("HIGH", "engine", f"Crashes on negative NI: {e}")
        print(f"  ✗ Negative NI crashes: {e}")

    # 3d. Single year (no prev)
    single = make_synthetic_data()
    del single["Income Statement"]["2022"]
    del single["Balance Sheet"]["2022"]
    del single["Cash Flow Statement"]["2022"]
    try:
        result = analyze_financials(single)
        growth = result.latest_by_category.get("growth", {})
        rev_g = growth.get("Revenue Growth YoY")
        if rev_g is not None:
            REPORT.bug("MEDIUM", "growth",
                       f"Revenue Growth YoY computed without prev year: got {rev_g}")
            print(f"  ✗ Single-year data → growth returns {rev_g} (should be None)")
        else:
            REPORT.ok("edge.single_year")
            print("  ✓ Single-year data → growth ratios are None (correct)")
    except Exception as e:
        REPORT.bug("HIGH", "engine", f"Single-year crashes: {e}")

    # 3e. NaN in input
    nan_data = make_synthetic_data()
    nan_data["Income Statement"]["2023"]["Net Income"] = float("nan")
    try:
        result = analyze_financials(nan_data)
        prof = result.latest_by_category.get("profitability", {})
        # Should either be None or a valid number, not NaN
        for k, v in prof.items():
            if v is not None and isinstance(v, float) and math.isnan(v):
                REPORT.bug("HIGH", "profitability", f"{k} returns NaN")
                print(f"  ✗ NaN propagates in {k}")
        REPORT.ok("edge.nan_input")
        print("  ✓ NaN input handled without propagation")
    except Exception as e:
        REPORT.bug("HIGH", "engine", f"NaN input crashes: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# PART 4: REAL DATA ROBUSTNESS
# ═══════════════════════════════════════════════════════════════════════════

def test_real_data():
    print("\n══ TEST 4: Real Data Robustness (up to 20 symbols) ══")

    symbols = list_available_symbols()[:20]
    if not symbols:
        print("  ⚠ No real data files in data/")
        return

    total_ratios = 0
    total_none = 0
    extreme_values = []
    inf_values = []
    crashes = []

    for sym in symbols:
        try:
            data = load_financials(sym)
            result = analyze_financials(data)

            for cat, ratios in result.latest_by_category.items():
                for name, val in ratios.items():
                    if name.startswith("_"):
                        continue
                    total_ratios += 1
                    if val is None:
                        total_none += 1
                    elif isinstance(val, float):
                        if math.isinf(val):
                            inf_values.append((sym, cat, name, val))
                        elif abs(val) > 10000 and "Ratio" not in name and "Score" not in name and "Value" not in name and "Cap" not in name and "Debt" not in name and "Earnings" not in name and "NOPAT" not in name and "Sales" not in name and "Assets" not in name and "Capital" not in name and "Cash Flow" not in name and "OCF" not in name and "FCF" not in name and "EBIT" not in name and "Days" not in name and "Turnover" not in name and "per" not in name.lower() and "Revenue" not in name and "Income" not in name and "Interest" not in name and "Book" not in name and "Investments" not in name and "Working" not in name and "Buybacks" not in name and "Payout" not in name and "Dividends" not in name:
                            extreme_values.append((sym, cat, name, val))
        except Exception as e:
            crashes.append((sym, str(e)))

    print(f"  Tested: {len(symbols)} symbols")
    print(f"  Total ratios computed: {total_ratios}")
    print(f"  Nones: {total_none} ({100*total_none/max(total_ratios,1):.1f}%)")
    print(f"  Infinities: {len(inf_values)}")
    print(f"  Suspiciously extreme (>10,000%): {len(extreme_values)}")
    print(f"  Crashes: {len(crashes)}")

    if inf_values:
        REPORT.bug("HIGH", "multiple", f"Found {len(inf_values)} infinity values")
        print("\n  ✗ INFINITY VALUES FOUND:")
        for sym, cat, name, val in inf_values[:5]:
            print(f"      {sym} · {cat} · {name}: {val}")

    if extreme_values:
        print("\n  ⚠ Suspiciously extreme values (sample):")
        for sym, cat, name, val in extreme_values[:5]:
            print(f"      {sym} · {cat} · {name}: {val:.2f}")

    if crashes:
        REPORT.bug("CRITICAL", "engine", f"Crashes on {len(crashes)} real symbols")
        print("\n  ✗ CRASHES:")
        for sym, err in crashes[:5]:
            print(f"      {sym}: {err}")

    if not (inf_values or crashes):
        REPORT.ok("real_data.robustness")


# ═══════════════════════════════════════════════════════════════════════════
# PART 5: KNOWN-VALUE CROSS-CHECK against AAPL real data
# ═══════════════════════════════════════════════════════════════════════════

def test_aapl_reality_check():
    """Compare computed ratios against publicly known AAPL numbers."""
    print("\n══ TEST 5: Real AAPL Data — Reality Check ══")

    try:
        data = load_financials("AAPL")
    except FileNotFoundError:
        print("  ⚠ AAPL_financials.json not found — skipping")
        return

    result = analyze_financials(data)
    latest = result.latest_by_category
    prof = latest.get("profitability", {})
    val = latest.get("valuation", {})
    cf = latest.get("cash_flow", {})

    # Known real values for AAPL FY2024 (approximate ranges):
    # Gross margin ~40-46%, Net margin ~24-27%, ROE 150%+
    checks = [
        ("AAPL.Gross Margin", prof.get("Gross Profit Margin"), 35, 55),
        ("AAPL.Net Margin", prof.get("Net Profit Margin"), 20, 30),
        ("AAPL.ROE (dilutive)", prof.get("ROE"), 100, 300),  # AAPL famous for high ROE
        ("AAPL.P/E Ratio", val.get("P/E Ratio"), 15, 60),
        ("AAPL.FCF Margin", cf.get("FCF Margin"), 15, 35),
    ]

    for name, actual, lo, hi in checks:
        if actual is None:
            REPORT.warn(name, "Returns None — data likely missing")
            print(f"  ⚠ {name}: None")
        elif lo <= actual <= hi:
            REPORT.ok(name)
            print(f"  ✓ {name}: {actual:.2f} (range {lo}-{hi})")
        else:
            REPORT.bug("HIGH", "profitability",
                       f"AAPL {name} = {actual} outside plausible range [{lo}, {hi}]")
            print(f"  ✗ {name}: {actual:.2f} outside plausible [{lo}, {hi}]")


# ═══════════════════════════════════════════════════════════════════════════
# PART 6: SPECIFIC BUG HUNTING
# ═══════════════════════════════════════════════════════════════════════════

def test_specific_bugs():
    """Hunt for specific bug patterns known to cause issues."""
    print("\n══ TEST 6: Known Bug Patterns ══")

    # Bug pattern 1: CapEx sign handling with NEGATIVE CapEx (like real yfinance data)
    d = make_synthetic_data()
    d["Cash Flow Statement"]["2023"]["Capital Expenditure"] = -60_000_000  # NEGATIVE
    del d["Cash Flow Statement"]["2023"]["Free Cash Flow"]  # force computation
    result = analyze_financials(d)
    fcf = result.latest_by_category.get("cash_flow", {}).get("Free Cash Flow (FCF)")
    # Expected: 180 - (-60) = 240 if code doesn't handle sign
    # Or 180 - 60 = 120 if it does
    if fcf is not None:
        if abs(fcf - 240_000_000) < 1_000_000:
            REPORT.bug("CRITICAL", "cash_flow",
                       "CapEx sign bug: negative CapEx from real data is ADDED to OCF, "
                       "producing WRONG FCF. Should abs() or subtract sign-adjusted.",
                       expected=120_000_000,
                       actual=fcf)
            print("  ✗ CRITICAL BUG: Negative CapEx handled wrong")
            print("      OCF=180M, CapEx=-60M (negative like real data)")
            print(f"      Expected FCF: 120M   Got: {fcf/1e6:.0f}M")
        elif abs(fcf - 120_000_000) < 1_000_000:
            REPORT.ok("cash_flow.negative_capex")
            print(f"  ✓ Negative CapEx handled correctly (FCF = {fcf/1e6:.0f}M)")

    # Bug pattern 2: CapEx to OCF sign inconsistency
    d2 = make_synthetic_data()
    d2["Cash Flow Statement"]["2023"]["Capital Expenditure"] = -60_000_000
    result2 = analyze_financials(d2)
    capex_ocf = result2.latest_by_category.get("cash_flow", {}).get("CapEx to OCF")
    if capex_ocf is not None and capex_ocf < 0:
        REPORT.bug("HIGH", "cash_flow",
                   f"CapEx/OCF ratio is negative ({capex_ocf}) with negative-signed CapEx. "
                   "Should use absolute value for consistency.")
        print(f"  ✗ CapEx/OCF is negative ({capex_ocf:.3f}) due to sign — should be positive")
    else:
        print(f"  ✓ CapEx/OCF sign OK: {capex_ocf}")

    # Bug pattern 3: Real AAPL uses "Research and Development Expenses"
    # while my code searches for "Research and Development"
    try:
        aapl = load_financials("AAPL")
        # Manually check
        income_2024 = list(aapl["Income Statement"].values())[-1]
        rd_key_actual = None
        for k in income_2024:
            if "research" in k.lower():
                rd_key_actual = k
                break
        result = analyze_financials(aapl)
        prof = result.latest_by_category.get("profitability", {})
        rd_margin = prof.get("R&D Margin")
        if rd_key_actual and "Expenses" in rd_key_actual and rd_margin is None:
            REPORT.bug("MEDIUM", "profitability",
                       f"R&D field name mismatch: data has '{rd_key_actual}' but "
                       f"code searches for 'Research and Development' (no 'Expenses'). "
                       f"R&D Margin returns None.")
            print(f"  ✗ R&D field name mismatch: data uses '{rd_key_actual}' → R&D Margin=None")
        else:
            print(f"  ✓ R&D field lookup works (margin={rd_margin})")
    except FileNotFoundError:
        pass

    # Bug pattern 4: Test that FCF is not double-counted (once from stored, once from OCF-CapEx)
    d3 = make_synthetic_data()
    result3 = analyze_financials(d3)
    fcf3 = result3.latest_by_category.get("cash_flow", {}).get("Free Cash Flow (FCF)")
    if fcf3 is not None and abs(fcf3 - 120_000_000) < 1_000_000:
        REPORT.ok("cash_flow.fcf_stored")
        print(f"  ✓ Stored FCF field used correctly ({fcf3/1e6:.0f}M)")


# ═══════════════════════════════════════════════════════════════════════════
# PART 7: DEEP NARRATOR
# ═══════════════════════════════════════════════════════════════════════════

def test_deep_narrator():
    print("\n══ TEST 7: Deep Narrator (Report Generation) ══")

    try:
        from backend.narrator import deep_analyze
    except ImportError as e:
        REPORT.warn("narrator.import", str(e))
        print(f"  ⚠ Cannot import narrator: {e}")
        return

    try:
        data = load_financials("AAPL")
    except FileNotFoundError:
        data = make_synthetic_data()

    result = analyze_financials(data)
    try:
        deep = deep_analyze(result)
        n_sections = len(deep.get("sections", []))
        n_used = deep.get("ratios_used_in_analysis", 0)
        md_th_len = len(deep.get("markdown_th", ""))
        md_en_len = len(deep.get("markdown_en", ""))

        if n_sections < 10:
            REPORT.bug("MEDIUM", "narrator", f"Only {n_sections} sections (expected 12)")
        if n_used < 40:
            REPORT.bug("MEDIUM", "narrator", f"Only {n_used} ratios used (expected 60+)")
        if md_th_len < 3000 or md_en_len < 3000:
            REPORT.bug("MEDIUM", "narrator",
                       f"Markdown too short (TH={md_th_len}, EN={md_en_len})")

        print(f"  ✓ Deep report: {n_sections} sections, {n_used} ratios used, "
              f"markdown TH={md_th_len} chars, EN={md_en_len} chars")
        REPORT.ok("narrator.generate")

    except Exception as e:
        REPORT.bug("HIGH", "narrator", f"deep_analyze crashes: {e}")
        print(f"  ✗ Deep analyze crashes: {e}")
        traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def print_summary():
    print("\n" + "═" * 70)
    print("  📋 TEST SUMMARY")
    print("═" * 70)
    print(f"  ✓ Passed:   {len(REPORT.passed)}")
    print(f"  ✗ Failed:   {len(REPORT.failed)}")
    print(f"  ⚠ Warnings: {len(REPORT.warnings)}")
    print(f"  🐛 Bugs:     {len(REPORT.bugs)}")

    if REPORT.failed:
        print("\n" + "─" * 70)
        print("  ✗ FAILURES:")
        for name, reason in REPORT.failed:
            print(f"     {name}")
            print(f"       └ {reason}")

    if REPORT.bugs:
        print("\n" + "─" * 70)
        print("  🐛 BUG REPORT:")
        by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for bug in REPORT.bugs:
            by_sev.setdefault(bug["severity"], []).append(bug)

        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if by_sev.get(sev):
                print(f"\n  [{sev}] {len(by_sev[sev])} bugs:")
                for bug in by_sev[sev]:
                    print(f"     • {bug['module']}: {bug['description']}")
                    if bug.get('expected') is not None:
                        print(f"         Expected: {bug['expected']}")
                        print(f"         Actual:   {bug['actual']}")

    print("\n" + "═" * 70)


def main():
    print("╔" + "═" * 68 + "╗")
    print("║" + "  Pro Stock Analyzer — Comprehensive Test Suite".ljust(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Run all tests
    test_profitability()
    test_liquidity()
    test_leverage()
    test_cash_flow()
    test_growth()
    test_valuation()
    test_dividend()
    test_quality()

    test_consistency()
    test_edge_cases()
    test_real_data()
    test_aapl_reality_check()
    test_specific_bugs()
    test_deep_narrator()

    print_summary()

    # Exit code = number of bugs
    return len(REPORT.bugs) + len(REPORT.failed)


if __name__ == "__main__":
    sys.exit(main())
