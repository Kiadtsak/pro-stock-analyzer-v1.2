"""
tests/conftest.py — Shared pytest fixtures.

Fixtures ที่ทุก test file ใช้ได้ — ไม่ต้อง import
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure backend is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ═══════════════════════════════════════════════════════════════════════════
# Data fixtures — synthetic financial data with known-answer values
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def synthetic_income():
    """Income statement with clean round numbers."""
    return {
        "Revenue": 1_000_000_000,          # 1B
        "Cost of Goods Sold": 500_000_000,  # 500M
        "Gross Profit": 500_000_000,        # 50% gross margin
        "Operating Income": 200_000_000,    # 20% op margin
        "EBIT": 200_000_000,
        "EBITDA": 250_000_000,              # 25% EBITDA margin
        "Net Income": 150_000_000,          # 15% net margin
        "Earnings Per Share": 1.50,
        "Weighted Average Shares Diluted": 100_000_000,
        "Research and Development": 100_000_000,
        "Interest Expense": 10_000_000,
        "Income Before Tax": 190_000_000,
        "Income Tax Expense": 40_000_000,   # ~21% effective
        "Depreciation and Amortization": 50_000_000,
    }


@pytest.fixture
def synthetic_prev_income():
    """Previous year income for growth calcs."""
    return {
        "Revenue": 800_000_000,
        "Cost of Goods Sold": 400_000_000,
        "Gross Profit": 400_000_000,
        "Operating Income": 160_000_000,
        "Net Income": 100_000_000,
        "Earnings Per Share": 1.0,
        "Weighted Average Shares Diluted": 100_000_000,
    }


@pytest.fixture
def synthetic_balance():
    """Balance sheet."""
    return {
        "Total Assets": 1_000_000_000,
        "Total Current Assets": 500_000_000,
        "Total Current Liabilities": 200_000_000,
        "Cash And Cash Equivalents": 200_000_000,
        "Short Term Investments": 50_000_000,
        "Total Equity": 600_000_000,
        "Total Debt": 200_000_000,
        "Long Term Debt": 180_000_000,
        "Short Term Debt": 20_000_000,
        "Retained Earnings": 300_000_000,
        "Total Liabilities": 400_000_000,
        "Inventory": 100_000_000,
        "Accounts Receivable": 150_000_000,
        "Accounts Payable": 100_000_000,
    }


@pytest.fixture
def synthetic_prev_balance():
    """Previous year balance."""
    return {
        "Total Assets": 900_000_000,
        "Total Current Assets": 400_000_000,
        "Total Current Liabilities": 200_000_000,
        "Cash And Cash Equivalents": 100_000_000,
        "Total Equity": 500_000_000,
        "Total Debt": 200_000_000,
        "Long Term Debt": 180_000_000,
        "Retained Earnings": 200_000_000,
        "Inventory": 80_000_000,
        "Accounts Receivable": 100_000_000,
        "Accounts Payable": 80_000_000,
    }


@pytest.fixture
def synthetic_cashflow():
    """Cash flow statement."""
    return {
        "Operating Cash Flow": 180_000_000,
        "Capital Expenditure": 60_000_000,
        "Free Cash Flow": 120_000_000,
        "Depreciation and Amortization": 50_000_000,
        "Dividends Paid": -30_000_000,
        "Common Stock Repurchased": -20_000_000,
        "Change in Working Capital": -15_000_000,
        "Investing Cash Flow": -80_000_000,
    }


@pytest.fixture
def synthetic_prev_cashflow():
    """Previous year cash flow."""
    return {
        "Operating Cash Flow": 120_000_000,
        "Capital Expenditure": 50_000_000,
        "Free Cash Flow": 70_000_000,
        "Dividends Paid": -20_000_000,
    }


@pytest.fixture
def synthetic_basic_info():
    """Basic company info."""
    return {
        "Symbol": "TEST",
        "Name": "Test Corporation",
        "Sector": "Technology",
        "Industry": "Software - Application",
        "CurrentPrice": 100.0,
        "MarketCap": 10_000_000_000,
        "Employees": 1000,
        "Prices": {"2020": 60.0, "2021": 80.0, "2022": 70.0, "2023": 100.0},
    }


@pytest.fixture
def synthetic_full_data(
    synthetic_income, synthetic_prev_income,
    synthetic_balance, synthetic_prev_balance,
    synthetic_cashflow, synthetic_prev_cashflow,
    synthetic_basic_info,
):
    """Complete financial data (both years) for engine testing."""
    return {
        "Basic Info": synthetic_basic_info,
        "Income Statement": {
            "2022": synthetic_prev_income,
            "2023": synthetic_income,
        },
        "Balance Sheet": {
            "2022": synthetic_prev_balance,
            "2023": synthetic_balance,
        },
        "Cash Flow Statement": {
            "2022": synthetic_prev_cashflow,
            "2023": synthetic_cashflow,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# Real data fixture (skip if not available)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def real_aapl_data():
    """Real AAPL data if available, otherwise skip test."""
    from backend import load_financials
    try:
        return load_financials("AAPL")
    except FileNotFoundError:
        pytest.skip("AAPL_financials.json not in data/")


@pytest.fixture(params=["AAPL", "NVDA", "MSFT", "GOOGL", "META"])
def real_symbol_data(request):
    """Parametrized fixture — runs the same test across multiple symbols."""
    from backend import load_financials
    try:
        return load_financials(request.param)
    except FileNotFoundError:
        pytest.skip(f"{request.param}_financials.json not in data/")


# ═══════════════════════════════════════════════════════════════════════════
# API fixture — FastAPI TestClient
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def api_client():
    """FastAPI TestClient for API tests."""
    try:
        from fastapi.testclient import TestClient

        from backend.app import app
    except ImportError:
        pytest.skip("FastAPI or backend.app not available")
    return TestClient(app)
