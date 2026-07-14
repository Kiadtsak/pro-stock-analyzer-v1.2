# Pro Stock Analyzer 📊

> Professional-grade financial ratio analysis system  
> **200+ formulas · 18 categories · Bilingual output (Thai + English)**

Designed to be a drop-in professional financial analysis engine, compatible with
JSON data from `financetoolkit`, FMP, or the existing `System_Stock` format.

## Features

- **255+ ratios computed** on real financial statements
- **18 categories**: Profitability, Efficiency, Liquidity, Leverage, Cash Flow, Growth, Valuation, Quality, Buffett, Cost of Capital, Intrinsic Value, Dividend, Risk + industry-specific (Banking, REIT, SaaS, Semiconductor, Insurance)
- **Advanced quality scores**: Altman Z-Score, Piotroski F-Score (with individual flags), Beneish M-Score, Sloan Accruals
- **Multiple valuation methods**: Two-stage DCF, Owner Earnings DCF, Graham Number, Graham Revised, Ten Cap, Dividend Discount Model, Reverse DCF (implied growth)
- **Composite scoring** with 6 sub-scores → weighted 0-100 signal
- **5-tier signals**: STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL
- **Bilingual narrative** (Thai + English) generated automatically
- **Interactive dashboard**: Luxe theme with score circles, category tabs, ratio trend charts
- **FastAPI backend** with auto-generated OpenAPI docs

## Quick Start

```bash
# 1. Setup (once)
make setup

# 2. Copy financial data JSON files into data/
cp ~/Desktop/System_Stock/data/*.json data/

# 3. Run
make run
# Dashboard: http://localhost:8300
# API docs:  http://localhost:8300/docs
```

## Project Structure

```
pro_stock_analyzer/
├── backend/
│   ├── ratios/                  # 18 category modules + base class
│   │   ├── base.py              # RatioBase + safe math helpers
│   │   ├── profitability.py     # 22 ratios
│   │   ├── efficiency.py        # 18 ratios
│   │   ├── liquidity.py         # 10 ratios
│   │   ├── leverage.py          # 20 ratios
│   │   ├── cash_flow.py         # 22 ratios
│   │   ├── growth.py            # 14 ratios
│   │   ├── valuation.py         # 28 ratios (per-share, price multiples, EV)
│   │   ├── quality.py           # 16 ratios (Altman Z, Piotroski F, Beneish M)
│   │   ├── buffett.py           # 14 ratios (Owner Earnings, Moat, ROE consistency)
│   │   ├── cost_of_capital.py   # 8 ratios (CAPM, WACC, sector-tiered beta)
│   │   ├── intrinsic_value.py   # 12 ratios (DCF, Graham, DDM, Reverse DCF)
│   │   ├── dividend.py          # 10 ratios
│   │   ├── risk.py              # 10 ratios (Sharpe, Sortino, Max DD, CAGR)
│   │   ├── banking.py           # 12 ratios (CAR, NIM, NPL, CET1, LDR)
│   │   ├── reit.py              # 11 ratios (FFO, AFFO, NAV, P/FFO)
│   │   ├── software_saas.py     # 12 ratios (ARR, Rule of 40, Magic Number)
│   │   ├── semiconductor.py     # 9 ratios (R&D%, Fab CapEx, Inventory Days)
│   │   └── insurance.py         # 9 ratios (Combined Ratio, Solvency)
│   ├── engine.py                # AnalysisEngine — orchestrates all categories
│   ├── loader.py                # Loads JSON financials from data/
│   ├── config.py                # Port, paths, env
│   └── app.py                   # FastAPI application
├── frontend/
│   ├── index.html               # Luxe dashboard scaffold
│   ├── style.css                # Navy + gold theme
│   └── app.js                   # Chart.js, tabs, interactive
├── data/                        # Drop JSON financials here
├── docs/FORMULAS.md             # Formula reference
├── tests/smoke_test.py          # Basic smoke tests
├── run.sh                       # Launch script
├── Makefile                     # setup / run / test
├── requirements.txt             # fastapi, uvicorn, pydantic
├── DEVLOG.md                    # Bilingual change log
└── README.md                    # This file
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serves the dashboard |
| GET | `/api/health` | Health check + category count |
| GET | `/api/categories` | List all 18 categories (EN + TH labels) |
| GET | `/api/symbols` | List all cached symbols |
| GET | `/api/analyze/{symbol}` | Full analysis (all categories, all years) |
| GET | `/api/analyze/{symbol}?categories=profitability,valuation` | Filtered analysis |
| GET | `/api/analyze/{symbol}/category/{category}` | Single category, all years |
| GET | `/api/analyze/{symbol}/summary` | Just the scorecard (fast) |

## Data Format

Drop JSON files into `data/` named `{SYMBOL}_financials.json`:

```json
{
  "Basic Info": {
    "Symbol": "NVDA",
    "Name": "NVIDIA Corporation",
    "Sector": "Technology",
    "Industry": "Semiconductors",
    "CurrentPrice": 880.0,
    "MarketCap": 2200000000000,
    "Prices": { "2020": 130, "2021": 294, "2022": 146, "2023": 495, "2024": 880 }
  },
  "Income Statement": {
    "2023": {
      "Revenue": 60922000000,
      "Cost of Goods Sold": 16621000000,
      "Operating Income": 32972000000,
      "Net Income": 29760000000,
      "Weighted Average Shares Diluted": 2500000000
    }
  },
  "Balance Sheet": { "2023": { "Total Assets": 65728000000, "..." : "..." } },
  "Cash Flow Statement": { "2023": { "Operating Cash Flow": 28090000000, "..." : "..." } }
}
```

Compatible with the existing `System_Stock` format. Use `make import-data` to
auto-copy from `../System_Stock/data/`.

## Extending: Adding a new ratio category

```python
# backend/ratios/my_category.py
from backend.ratios.base import RatioBase, sdiv, spct, sround

class MyRatios(RatioBase):
    category = "my_category"
    description = "My custom analysis"

    def compute(self) -> dict:
        return {
            "My Ratio": sround(sdiv(self._revenue(), self._total_assets())),
        }

# Then in backend/ratios/__init__.py, add to REGISTRY:
from backend.ratios.my_category import MyRatios
REGISTRY["my_category"] = MyRatios
CATEGORY_LABELS["my_category"] = ("My Category", "หมวดของฉัน")
```

## Programmatic Usage

```python
from backend import analyze_financials, load_financials

data = load_financials("NVDA")
result = analyze_financials(data)

print(f"Signal: {result.signal}")
print(f"Score:  {result.composite_score}")
print(f"Ratios: {result.total_ratios}")

# Access specific ratios
profitability = result.latest_by_category["profitability"]
print(f"ROE: {profitability['ROE']}")
print(f"ROIC: {profitability['ROIC']}")

# Multi-year analysis
for year, year_data in result.years.items():
    print(f"{year}: {year_data.ratio_count} ratios")
```

## Not Included / Not Investment Advice

⚠️ **Disclaimer**: This tool is for research and educational purposes only.
It is not investment advice. Financial ratios are only one input to
investment decisions — always do your own due diligence.

⚠️ **Note on live data**: This system analyzes JSON financial statement data
you provide. It does not fetch live data — pair with `financetoolkit`, FMP API,
or Yahoo Finance to source data automatically.

## License

MIT — Use freely for research, personal, or commercial work.
