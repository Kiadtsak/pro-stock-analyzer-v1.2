"""
tests/test_cache_manager.py — Tests for smart fetch + auto cache cleanup.

Usage:
    pytest tests/test_cache_manager.py -v
    pytest -m unit
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from backend.cache_manager import (
    cleanup_old_files, cache_status, is_fresh, file_age_days, MAX_AGE_DAYS,
)
from backend.fetcher import _df_to_years, _to_num, _s


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def make_file(directory: Path, name: str, age_days: float) -> Path:
    """สร้างไฟล์ทดสอบพร้อมตั้ง modified time ย้อนหลัง."""
    p = directory / name
    p.write_text(json.dumps({"test": True}))
    mtime = time.time() - age_days * 86400
    os.utime(p, (mtime, mtime))
    return p


# ═══════════════════════════════════════════════════════════════════════════
# TestFileAge
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestFileAge:
    def test_new_file_age_near_zero(self, tmp_path):
        p = make_file(tmp_path, "AAPL_financials.json", age_days=0)
        assert file_age_days(p) < 0.01

    def test_old_file_age_correct(self, tmp_path):
        p = make_file(tmp_path, "OLD_financials.json", age_days=45)
        assert file_age_days(p) == pytest.approx(45, abs=0.1)

    def test_is_fresh_new_file(self, tmp_path):
        p = make_file(tmp_path, "AAPL_financials.json", age_days=5)
        assert is_fresh(p) is True

    def test_is_fresh_boundary_29_days(self, tmp_path):
        """29 วัน — ยังไม่เกิน 30 → สด."""
        p = make_file(tmp_path, "NVDA_financials.json", age_days=29)
        assert is_fresh(p) is True

    def test_is_stale_31_days(self, tmp_path):
        """31 วัน — เกิน 30 → หมดอายุ."""
        p = make_file(tmp_path, "OLD_financials.json", age_days=31)
        assert is_fresh(p) is False

    def test_is_fresh_missing_file(self, tmp_path):
        assert is_fresh(tmp_path / "MISSING_financials.json") is False

    def test_custom_max_age(self, tmp_path):
        p = make_file(tmp_path, "X_financials.json", age_days=10)
        assert is_fresh(p, max_age_days=7) is False    # เกิน 7 วัน
        assert is_fresh(p, max_age_days=14) is True    # ไม่เกิน 14 วัน


# ═══════════════════════════════════════════════════════════════════════════
# TestCleanup — พฤติกรรมการลบ
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCleanup:
    def test_deletes_only_files_over_30_days(self, tmp_path):
        make_file(tmp_path, "FRESH_financials.json", age_days=5)
        make_file(tmp_path, "EDGE_financials.json", age_days=29)
        make_file(tmp_path, "OLD1_financials.json", age_days=31)
        make_file(tmp_path, "OLD2_financials.json", age_days=90)

        report = cleanup_old_files(data_dir=tmp_path)

        assert set(report["deleted"]) == {"OLD1_financials.json", "OLD2_financials.json"}
        assert set(report["kept"]) == {"FRESH_financials.json", "EDGE_financials.json"}
        assert not (tmp_path / "OLD1_financials.json").exists()
        assert (tmp_path / "FRESH_financials.json").exists()

    def test_does_not_touch_other_file_types(self, tmp_path):
        """ไฟล์ที่ไม่ใช่ *_financials.json ต้องไม่ถูกลบแม้เก่าแค่ไหน."""
        make_file(tmp_path, "notes.txt", age_days=365)
        make_file(tmp_path, "config.json", age_days=365)
        make_file(tmp_path, "OLD_financials.json", age_days=365)

        report = cleanup_old_files(data_dir=tmp_path)

        assert (tmp_path / "notes.txt").exists(), "notes.txt ต้องไม่ถูกลบ!"
        assert (tmp_path / "config.json").exists(), "config.json ต้องไม่ถูกลบ!"
        assert not (tmp_path / "OLD_financials.json").exists()
        assert report["deleted"] == ["OLD_financials.json"]

    def test_does_not_touch_subfolders(self, tmp_path):
        """ไฟล์ใน subfolder ต้องไม่ถูกลบ (ความปลอดภัย)."""
        sub = tmp_path / "backup"
        sub.mkdir()
        make_file(sub, "XXX_financials.json", age_days=365)

        cleanup_old_files(data_dir=tmp_path)

        assert (sub / "XXX_financials.json").exists(), "ไฟล์ใน subfolder ต้องไม่ถูกแตะ!"

    def test_dry_run_does_not_delete(self, tmp_path):
        make_file(tmp_path, "OLD_financials.json", age_days=90)

        report = cleanup_old_files(data_dir=tmp_path, dry_run=True)

        assert report["deleted"] == ["OLD_financials.json"]   # รายงานว่าจะลบ
        assert (tmp_path / "OLD_financials.json").exists()    # แต่ไม่ลบจริง

    def test_empty_dir_no_crash(self, tmp_path):
        report = cleanup_old_files(data_dir=tmp_path)
        assert report["deleted"] == []
        assert report["kept"] == []

    def test_missing_dir_returns_error(self, tmp_path):
        report = cleanup_old_files(data_dir=tmp_path / "does_not_exist")
        assert len(report["errors"]) == 1

    def test_custom_max_age_days(self, tmp_path):
        make_file(tmp_path, "A_financials.json", age_days=10)
        report = cleanup_old_files(data_dir=tmp_path, max_age_days=7)
        assert report["deleted"] == ["A_financials.json"]


# ═══════════════════════════════════════════════════════════════════════════
# TestCacheStatus
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCacheStatus:
    def test_status_counts(self, tmp_path):
        make_file(tmp_path, "A_financials.json", age_days=5)
        make_file(tmp_path, "B_financials.json", age_days=50)

        status = cache_status(data_dir=tmp_path)

        assert status["total_files"] == 2
        assert status["fresh_count"] == 1
        assert status["stale_count"] == 1

    def test_status_includes_symbol_and_age(self, tmp_path):
        make_file(tmp_path, "AAPL_financials.json", age_days=5)
        status = cache_status(data_dir=tmp_path)

        f = status["files"][0]
        assert f["symbol"] == "AAPL"
        assert f["age_days"] == pytest.approx(5, abs=0.1)
        assert f["fresh"] is True

    def test_status_empty_dir(self, tmp_path):
        status = cache_status(data_dir=tmp_path)
        assert status["total_files"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# TestFetcherMapping — ทดสอบการแปลง DataFrame ของ financetoolkit (offline)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestFetcherMapping:
    def test_financetoolkit_df_to_years(self):
        """DataFrame แบบ Toolkit (index=รายการ, columns=ปี) → dict รายปี."""
        pd = pytest.importorskip("pandas")
        import numpy as np

        cols = pd.PeriodIndex(["2022", "2023"], freq="Y")
        df = pd.DataFrame(
            {
                cols[0]: [394_328_000_000, 99_803_000_000, np.nan],
                cols[1]: [383_285_000_000, 96_995_000_000, 6.16],
            },
            index=["Revenue", "Net Income", "EPS"],
        )
        out = _df_to_years(df)

        assert set(out.keys()) == {"2022", "2023"}
        assert out["2023"]["Revenue"] == 383_285_000_000
        assert out["2023"]["EPS"] == 6.16
        assert "EPS" not in out["2022"], "NaN ต้องถูกตัดทิ้ง ไม่ใช่เก็บเป็น null"

    def test_df_to_years_multiindex_multi_ticker(self):
        """หลาย ticker (MultiIndex) → เลือกเฉพาะ ticker ที่ขอ."""
        pd = pytest.importorskip("pandas")

        mi = pd.MultiIndex.from_product([["AAPL"], ["Revenue", "Net Income"]])
        df = pd.DataFrame({"2023": [383e9, 97e9]}, index=mi)
        out = _df_to_years(df, ticker="AAPL")
        assert out["2023"]["Revenue"] == 383e9

    def test_df_to_years_skips_non_year_columns(self):
        """คอลัมน์อย่าง TTM ต้องถูกข้าม เก็บเฉพาะปีจริง."""
        pd = pytest.importorskip("pandas")

        df = pd.DataFrame({"TTM": [100.0], "2023": [200.0]}, index=["Revenue"])
        out = _df_to_years(df)
        assert list(out.keys()) == ["2023"]

    def test_df_to_years_empty_or_none(self):
        pd = pytest.importorskip("pandas")
        assert _df_to_years(None) == {}
        assert _df_to_years(pd.DataFrame()) == {}

    @pytest.mark.parametrize("value, expected", [
        (123.45, 123.45),
        ("123.45", 123.45),
        (0, 0.0),
        (None, None),
        ("abc", None),
        (float("nan"), None),
    ])
    def test_to_num_edge_cases(self, value, expected):
        assert _to_num(value) == expected

    def test_s_string_helper(self):
        assert _s("  Apple Inc. ") == "Apple Inc."
        assert _s(None) is None
        assert _s(float("nan")) is None
        assert _s("") is None


# ═══════════════════════════════════════════════════════════════════════════
# TestLoadOrFetch — smart loader (cache hit path เท่านั้น — ไม่ยิง API จริง)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestLoadOrFetch:
    def test_cache_hit_uses_local_file(self, tmp_path):
        """มีไฟล์สดใน data/ → โหลดจาก cache ไม่ยิง API."""
        try:
            from backend.loader import load_or_fetch
        except ImportError:
            pytest.skip("load_or_fetch ยังไม่ติดตั้ง — รัน apply_smart_fetch.py ก่อน")

        payload = {
            "Basic Info": {"Symbol": "TEST", "Name": "Test Corp"},
            "Income Statement": {"2023": {"Revenue": 1000}},
            "Balance Sheet": {"2023": {}},
            "Cash Flow Statement": {"2023": {}},
        }
        p = tmp_path / "TEST_financials.json"
        p.write_text(json.dumps(payload))

        data = load_or_fetch("TEST", data_dir=tmp_path, auto_cleanup=False)
        assert data["Basic Info"]["Symbol"] == "TEST"
        assert data["Income Statement"]["2023"]["Revenue"] == 1000

    def test_stale_file_cleaned_before_load(self, tmp_path):
        """ไฟล์เกิน 30 วัน → auto_cleanup ลบทิ้งก่อน → พยายาม fetch."""
        try:
            from backend.loader import load_or_fetch
        except ImportError:
            pytest.skip("load_or_fetch ยังไม่ติดตั้ง — รัน apply_smart_fetch.py ก่อน")

        p = make_file(tmp_path, "STALEXYZ_financials.json", age_days=45)
        assert p.exists()

        # fetch จะพัง (สัญลักษณ์มั่ว + ไม่มี network ใน CI) → FileNotFoundError
        with pytest.raises(FileNotFoundError):
            load_or_fetch("STALEXYZ", data_dir=tmp_path, auto_cleanup=True)

        # ไฟล์เก่าต้องถูก cleanup ลบไปแล้ว
        assert not p.exists()
