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


# ═══════════════════════════════════════════════════════════════════════════
# Smart fetch — load from cache, or fetch from API if missing/stale
# ═══════════════════════════════════════════════════════════════════════════

def load_or_fetch(
    symbol: str,
    data_dir: Optional[Path] = None,
    max_age_days: int = 30,
    auto_cleanup: bool = True,
) -> dict:
    """
    โหลดข้อมูลหุ้นแบบฉลาด:
      1. ลบไฟล์เก่าเกิน max_age_days ใน data/ อัตโนมัติ (auto_cleanup)
      2. ถ้ามีไฟล์ใน data/ และยังสด → ใช้ cache เลย (ไม่ยิง API)
      3. ถ้าไม่มี/หมดอายุ → ดึงจาก API (FMP → yfinance) + บันทึกลง data/
      4. ถ้า fetch ล้มเหลวแต่มีไฟล์เก่าอยู่ → ใช้ไฟล์เก่าไปก่อน (พร้อม warning)

    Raises:
        FileNotFoundError: ไม่มี cache และ fetch ไม่สำเร็จ
    """
    import logging
    from backend.cache_manager import cleanup_old_files, is_fresh
    from backend.fetcher import fetch_and_save, FetchError

    log = logging.getLogger("pro_stock_analyzer.loader")
    symbol = symbol.upper().strip()
    d = data_dir or DATA_DIR
    path = d / f"{symbol}_financials.json"

    # 1) Auto cleanup — ลบไฟล์เกินอายุ (เฉพาะใน data/)
    if auto_cleanup:
        cleanup_old_files(data_dir=d, max_age_days=max_age_days)

    # 2) Cache hit — มีไฟล์และยังสด
    if path.exists() and is_fresh(path, max_age_days):
        log.info(f"📂 Cache hit: {symbol} (using local file)")
        return load_financials(symbol, data_dir=d)

    # 3) Cache miss — ดึงจาก API
    log.info(f"🌐 Cache miss: {symbol} — fetching from API...")
    try:
        return fetch_and_save(symbol, data_dir=d)
    except FetchError as e:
        # 4) Fallback — fetch พังแต่ยังมีไฟล์เก่า (กรณี cleanup ปิดอยู่)
        if path.exists():
            log.warning(f"⚠ Fetch failed for {symbol}, using stale cache: {e}")
            return load_financials(symbol, data_dir=d)
        raise FileNotFoundError(
            f"No cached data for {symbol} and API fetch failed: {e}"
        )
