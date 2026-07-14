"""
backend/loader.py — Load financial statements from JSON files.

Compatible with the existing System_Stock format:
  data/{SYMBOL}_financials.json  →  {
      "Basic Info": {...},
      "Income Statement": {year: {...}, ...},
      "Balance Sheet": {year: {...}, ...},
      "Cash Flow Statement": {year: {...}, ...},
  }
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_financials(symbol: str, data_dir: Path | None = None) -> dict:
    """Load a symbol's financial statements from JSON."""
    d = data_dir or DATA_DIR
    path = d / f"{symbol.upper()}_financials.json"
    if not path.exists():
        raise FileNotFoundError(f"No data for {symbol.upper()} at {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def list_available_symbols(data_dir: Path | None = None) -> list[str]:
    """List all symbols with cached JSON data."""
    d = data_dir or DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    return sorted({
        p.stem.replace("_financials", "").upper()
        for p in d.glob("*_financials.json")
    })


def validate_data(data: dict) -> tuple[bool, list[str]]:
    """
    Quick validation. Returns (is_valid, warnings).
    """
    warnings = []
    required_top = ["Income Statement", "Balance Sheet", "Cash Flow Statement"]
    for key in required_top:
        if key not in data:
            warnings.append(f"Missing top-level key: {key}")
        elif not isinstance(data[key], dict):
            warnings.append(f"{key} is not a dict")

    if "Basic Info" not in data:
        warnings.append("Missing Basic Info (analysis will proceed with defaults)")

    # Check for year overlap
    if all(k in data for k in required_top):
        years_i = set(data["Income Statement"].keys())
        years_b = set(data["Balance Sheet"].keys())
        years_c = set(data["Cash Flow Statement"].keys())
        common = years_i & years_b & years_c
        if not common:
            warnings.append("No overlapping years across statements")

    return len([w for w in warnings if not w.startswith("Missing Basic Info")]) == 0, warnings
