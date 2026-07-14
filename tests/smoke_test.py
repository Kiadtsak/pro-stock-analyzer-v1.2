"""
tests/smoke_test.py — Basic verification.

Runs analysis on mock data and asserts:
  - all 18 categories register
  - 200+ ratios computed
  - engine returns valid result structure
  - no crashes on missing data
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend import CATEGORY_LABELS, REGISTRY, analyze_financials


def test_registry():
    assert len(REGISTRY) == 18, f"Expected 18 categories, got {len(REGISTRY)}"
    for name in REGISTRY:
        assert name in CATEGORY_LABELS, f"{name} missing from CATEGORY_LABELS"
    print("✓ Registry test: 18 categories, all labeled")


def test_full_analysis():
    """End-to-end analysis on mock NVDA data."""
    mock = _mock_nvda_data()
    result = analyze_financials(mock)

    assert result.symbol == "NVDA"
    assert result.total_ratios >= 200, f"Expected 200+ ratios, got {result.total_ratios}"
    assert result.signal in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    assert 0 <= result.composite_score <= 100
    assert len(result.categories_computed) == 18
    assert result.narrative_en, "English narrative empty"
    assert result.narrative_th, "Thai narrative empty"

    print(f"✓ Full analysis: {result.total_ratios} ratios, "
          f"signal={result.signal}, score={result.composite_score}")


def test_missing_data_no_crash():
    """Analyzer should handle empty/partial data gracefully."""
    empty = {
        "Basic Info": {"Symbol": "TEST"},
        "Income Statement": {"2023": {}},
        "Balance Sheet": {"2023": {}},
        "Cash Flow Statement": {"2023": {}},
    }
    result = analyze_financials(empty)
    assert result.symbol == "TEST"
    # Most ratios will be None but shouldn't crash
    print(f"✓ Empty data test: {result.total_ratios} ratios (mostly None expected)")


def test_partial_data():
    """Only income statement, no balance sheet."""
    partial = {
        "Basic Info": {"Symbol": "TST", "Sector": "Technology"},
        "Income Statement": {"2023": {"Revenue": 100_000, "Net Income": 20_000}},
        "Balance Sheet": {"2023": {"Total Assets": 500_000}},
        "Cash Flow Statement": {"2023": {"Operating Cash Flow": 25_000}},
    }
    result = analyze_financials(partial)
    prof = result.latest_by_category.get("profitability", {})
    assert prof.get("Net Profit Margin") == 20.0, f"Got {prof.get('Net Profit Margin')}"
    print("✓ Partial data test: Net Profit Margin = 20% correct")


# ─── Mock data ─────────────────────────────────────────────────
def _mock_nvda_data():
    return {
        "Basic Info": {
            "Symbol": "NVDA", "Name": "NVIDIA Corporation",
            "Sector": "Technology", "Industry": "Semiconductors",
            "CurrentPrice": 880.0, "MarketCap": 2_200_000_000_000,
            "Employees": 26196,
            "Prices": {"2020": 130, "2021": 294, "2022": 146, "2023": 495, "2024": 880},
        },
        "Income Statement": {
            "2023": {
                "Revenue": 60922_000_000, "Cost of Goods Sold": 16621_000_000,
                "Gross Profit": 44301_000_000, "Operating Income": 32972_000_000,
                "EBITDA": 34500_000_000, "Net Income": 29760_000_000,
                "Earnings Per Share": 11.93, "Weighted Average Shares Diluted": 2500_000_000,
                "Research and Development": 8675_000_000, "Interest Expense": 257_000_000,
                "Income Before Tax": 33818_000_000, "Income Tax Expense": 4058_000_000,
                "Depreciation and Amortization": 1508_000_000,
            },
            "2022": {
                "Revenue": 26974_000_000, "Cost of Goods Sold": 11618_000_000,
                "Gross Profit": 15356_000_000, "Operating Income": 4224_000_000,
                "Net Income": 4368_000_000, "Earnings Per Share": 1.74,
                "Weighted Average Shares Diluted": 2510_000_000,
            },
        },
        "Balance Sheet": {
            "2023": {
                "Total Assets": 65728_000_000, "Total Current Assets": 44345_000_000,
                "Total Current Liabilities": 10631_000_000,
                "Cash And Cash Equivalents": 25984_000_000,
                "Total Equity": 42978_000_000, "Total Debt": 9709_000_000,
                "Long Term Debt": 8459_000_000, "Retained Earnings": 29817_000_000,
                "Total Liabilities": 22750_000_000, "Inventory": 5282_000_000,
                "Accounts Receivable": 9999_000_000,
            },
            "2022": {
                "Total Assets": 41182_000_000, "Total Current Assets": 23073_000_000,
                "Total Current Liabilities": 6563_000_000,
                "Cash And Cash Equivalents": 3389_000_000, "Total Equity": 22101_000_000,
                "Total Debt": 12026_000_000, "Long Term Debt": 10953_000_000,
                "Retained Earnings": 4818_000_000, "Total Liabilities": 19081_000_000,
                "Inventory": 5159_000_000, "Accounts Receivable": 3827_000_000,
            },
        },
        "Cash Flow Statement": {
            "2023": {
                "Operating Cash Flow": 28090_000_000, "Capital Expenditure": 1069_000_000,
                "Free Cash Flow": 27021_000_000, "Depreciation and Amortization": 1508_000_000,
                "Change in Working Capital": -3891_000_000, "Dividends Paid": -395_000_000,
                "Investing Cash Flow": -10566_000_000,
            },
            "2022": {
                "Operating Cash Flow": 5641_000_000, "Capital Expenditure": 1833_000_000,
                "Free Cash Flow": 3808_000_000, "Depreciation and Amortization": 1544_000_000,
                "Dividends Paid": -398_000_000,
            },
        },
    }


if __name__ == "__main__":
    print("═══════════════════════════════════════════════════════════════")
    print("  Pro Stock Analyzer — Smoke Tests")
    print("═══════════════════════════════════════════════════════════════")
    test_registry()
    test_full_analysis()
    test_missing_data_no_crash()
    test_partial_data()
    print("═══════════════════════════════════════════════════════════════")
    print("  ✅ All tests passed")
    print("═══════════════════════════════════════════════════════════════")
