"""
backend/cache_manager.py — Data cache lifecycle management.

หน้าที่:
  1. ลบไฟล์ *_financials.json ใน data/ ที่อายุเกิน max_age_days (default 30 วัน) อัตโนมัติ
  2. เช็คว่าไฟล์ยัง "สด" (fresh) อยู่ไหม
  3. รายงานสถานะ cache ทั้งหมด

ความปลอดภัย:
  - ลบเฉพาะไฟล์ *_financials.json ใน data/ เท่านั้น (ไม่แตะ subfolder, ไม่แตะไฟล์อื่น)
  - ไม่ลบไฟล์นอก data/ เด็ดขาด
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("pro_stock_analyzer.cache")

# Default: same data dir as loader
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# อายุสูงสุดของไฟล์ cache (วัน) — เกินนี้จะถูกลบอัตโนมัติ
MAX_AGE_DAYS = 30

# Pattern ของไฟล์ที่จัดการ — เฉพาะไฟล์งบการเงินเท่านั้น
CACHE_PATTERN = "*_financials.json"


def file_age_days(path: Path) -> float:
    """อายุของไฟล์เป็นวัน (นับจาก modified time)."""
    mtime = path.stat().st_mtime
    return (time.time() - mtime) / 86400.0


def is_fresh(path: Path, max_age_days: int = MAX_AGE_DAYS) -> bool:
    """ไฟล์ยังสดอยู่ไหม (อายุไม่เกิน max_age_days)."""
    if not path.exists():
        return False
    return file_age_days(path) <= max_age_days


def cleanup_old_files(
    data_dir: Optional[Path] = None,
    max_age_days: int = MAX_AGE_DAYS,
    dry_run: bool = False,
) -> dict:
    """
    ลบไฟล์ *_financials.json ที่อายุเกิน max_age_days ใน data/ (ไม่รวม subfolder)

    Args:
        data_dir:     โฟลเดอร์ที่จัดการ (default: data/)
        max_age_days: อายุสูงสุด (วัน) — เกินนี้ลบ
        dry_run:      True = แค่รายงาน ไม่ลบจริง

    Returns:
        {
            "deleted": ["AAPL_financials.json", ...],
            "kept":    ["NVDA_financials.json", ...],
            "errors":  [],
            "max_age_days": 30,
        }
    """
    d = data_dir or DATA_DIR
    deleted: list[str] = []
    kept: list[str] = []
    errors: list[str] = []

    if not d.exists():
        return {"deleted": [], "kept": [], "errors": [f"{d} not found"],
                "max_age_days": max_age_days}

    # glob เฉพาะไฟล์ชั้นแรกของ data/ — ไม่ลง subfolder (ปลอดภัย)
    for path in sorted(d.glob(CACHE_PATTERN)):
        if not path.is_file():
            continue
        try:
            age = file_age_days(path)
            if age > max_age_days:
                if not dry_run:
                    path.unlink()
                deleted.append(path.name)
                log.info(f"🗑  Deleted stale cache: {path.name} (age {age:.1f} days)")
            else:
                kept.append(path.name)
        except OSError as e:
            errors.append(f"{path.name}: {e}")
            log.warning(f"Failed to process {path.name}: {e}")

    if deleted:
        log.info(f"Cache cleanup: deleted {len(deleted)}, kept {len(kept)}")

    return {
        "deleted": deleted,
        "kept": kept,
        "errors": errors,
        "max_age_days": max_age_days,
        "dry_run": dry_run,
    }


def cache_status(data_dir: Optional[Path] = None,
                 max_age_days: int = MAX_AGE_DAYS) -> dict:
    """
    รายงานสถานะ cache — ไฟล์ไหนสด ไฟล์ไหนใกล้หมดอายุ

    Returns:
        {
            "total_files": 167,
            "fresh": [...],       # อายุ <= 30 วัน
            "stale": [...],       # อายุ > 30 วัน (จะถูกลบรอบหน้า)
            "files": [{"name": ..., "age_days": ..., "fresh": ...}, ...],
        }
    """
    d = data_dir or DATA_DIR
    files_info = []
    fresh, stale = [], []

    if d.exists():
        for path in sorted(d.glob(CACHE_PATTERN)):
            if not path.is_file():
                continue
            age = file_age_days(path)
            f = age <= max_age_days
            files_info.append({
                "name": path.name,
                "symbol": path.name.replace("_financials.json", ""),
                "age_days": round(age, 1),
                "fresh": f,
                "size_kb": round(path.stat().st_size / 1024, 1),
            })
            (fresh if f else stale).append(path.name)

    return {
        "data_dir": str(d),
        "total_files": len(files_info),
        "fresh_count": len(fresh),
        "stale_count": len(stale),
        "max_age_days": max_age_days,
        "files": files_info,
    }


if __name__ == "__main__":
    # รันตรงๆ ได้: python3 backend/cache_manager.py
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("═" * 60)
    print("  Cache Status")
    print("═" * 60)
    status = cache_status()
    print(f"  Data dir:  {status['data_dir']}")
    print(f"  Total:     {status['total_files']} files")
    print(f"  Fresh:     {status['fresh_count']} (≤ {status['max_age_days']} days)")
    print(f"  Stale:     {status['stale_count']} (will be deleted)")
    print()
    if status["stale_count"] > 0:
        print("  Running cleanup...")
        report = cleanup_old_files()
        print(f"  Deleted: {len(report['deleted'])} files")
        for name in report["deleted"]:
            print(f"    🗑 {name}")
    else:
        print("  ✓ No stale files — nothing to clean")
