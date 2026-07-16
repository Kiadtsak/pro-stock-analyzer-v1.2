#!/usr/bin/env python3
"""
apply_smart_fetch.py — ติดตั้งระบบ Smart Fetch + Auto Cleanup เข้าโปรเจกต์

Usage:
    cd ~/Desktop/pro_stock_analyzer_v1.2
    python3 apply_smart_fetch.py

สิ่งที่ทำ:
  1. เช็คว่า backend/fetcher.py และ backend/cache_manager.py ถูก copy มาแล้ว
  2. เพิ่มฟังก์ชัน load_or_fetch() ใน backend/loader.py
  3. แก้ backend/app.py:
       - ทุก endpoint ที่เรียก load_financials() → เปลี่ยนเป็น load_or_fetch()
       - เพิ่ม startup cleanup (ลบไฟล์เกิน 30 วันตอนเปิด server)
       - เพิ่ม endpoints: GET /api/cache/status, POST /api/cache/cleanup
  4. Clear __pycache__

หลังรัน:
  - ป้อนหุ้นที่ไม่มีใน data/ → ระบบดึงจาก API ให้อัตโนมัติ + เก็บไฟล์
  - ไฟล์เกิน 30 วันถูกลบอัตโนมัติทุกครั้งที่ server start / มีการ fetch
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"

if not BACKEND.exists():
    print(f"❌ ไม่พบ {BACKEND} — รันจากโฟลเดอร์ pro_stock_analyzer เท่านั้น")
    sys.exit(1)


def check_file(path: Path, name: str) -> bool:
    if path.exists():
        print(f"  ✓ {name} พร้อมแล้ว")
        return True
    print(f"  ❌ ไม่พบ {name} — copy ไฟล์นี้เข้า backend/ ก่อน แล้วรันใหม่")
    return False


def patch(path: Path, old: str, new: str, desc: str) -> bool:
    if not path.exists():
        print(f"  ⚠ ไม่พบไฟล์ {path.name}")
        return False
    text = path.read_text(encoding="utf-8")
    if new.strip() in text:
        print(f"  ✓ ติดตั้งแล้ว (ข้าม): {desc}")
        return False
    if old.strip() not in text:
        print(f"  ⚠ ไม่เจอ pattern ใน {path.name} — ข้าม: {desc}")
        print(f"     (โค้ดอาจถูกแก้ไว้แล้ว — เช็คด้วยตัวเองตาม INSTALL_SMART_FETCH.md)")
        return False
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"  ✓ Patched {path.name}: {desc}")
    return True


print("╔" + "═" * 64 + "╗")
print("║  Smart Fetch + Auto Cleanup — Installer".ljust(65) + "║")
print("╚" + "═" * 64 + "╝")

# ═══════════════════════════════════════════════════════════════════
# Step 1: เช็คว่าไฟล์ใหม่ 2 ตัวถูกวางแล้ว
# ═══════════════════════════════════════════════════════════════════
print("\n[1/4] เช็คไฟล์ใหม่")
ok = True
ok &= check_file(BACKEND / "fetcher.py", "backend/fetcher.py")
ok &= check_file(BACKEND / "cache_manager.py", "backend/cache_manager.py")
if not ok:
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════
# Step 2: เพิ่ม load_or_fetch() ใน loader.py
# ═══════════════════════════════════════════════════════════════════
print("\n[2/4] เพิ่ม load_or_fetch() ใน backend/loader.py")

LOADER_ADDON = '''

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
'''

loader_path = BACKEND / "loader.py"
loader_text = loader_path.read_text(encoding="utf-8")
if "def load_or_fetch(" in loader_text:
    print("  ✓ load_or_fetch() มีอยู่แล้ว (ข้าม)")
else:
    loader_path.write_text(loader_text.rstrip() + "\n" + LOADER_ADDON,
                           encoding="utf-8")
    print("  ✓ เพิ่ม load_or_fetch() ต่อท้าย loader.py แล้ว")

# ═══════════════════════════════════════════════════════════════════
# Step 3: แก้ app.py — ใช้ load_or_fetch + startup cleanup + endpoints
# ═══════════════════════════════════════════════════════════════════
print("\n[3/4] แก้ backend/app.py")

app_path = BACKEND / "app.py"

# 3a. เพิ่ม import
patch(
    app_path,
    old="""from backend import (
    analyze_financials, load_financials, list_available_symbols,
    validate_data, REGISTRY, CATEGORY_LABELS,
)""",
    new="""from backend import (
    analyze_financials, load_financials, list_available_symbols,
    validate_data, REGISTRY, CATEGORY_LABELS,
)
from backend.loader import load_or_fetch
from backend.cache_manager import cleanup_old_files, cache_status""",
    desc="เพิ่ม imports (load_or_fetch, cache_manager)",
)

# 3b. เปลี่ยนทุก load_financials(symbol) เป็น load_or_fetch(symbol)
app_text = app_path.read_text(encoding="utf-8")
n = app_text.count("data = load_financials(symbol)")
if n > 0:
    app_text = app_text.replace(
        "data = load_financials(symbol)",
        "data = load_or_fetch(symbol)",
    )
    app_path.write_text(app_text, encoding="utf-8")
    print(f"  ✓ เปลี่ยน load_financials → load_or_fetch ({n} จุด)")
else:
    if "data = load_or_fetch(symbol)" in app_text:
        print("  ✓ endpoints ใช้ load_or_fetch อยู่แล้ว (ข้าม)")
    else:
        print("  ⚠ ไม่เจอ 'data = load_financials(symbol)' — เช็คเอง")

# 3c. เพิ่ม startup cleanup + cache endpoints (วางก่อน @app.get("/api/health"))
CACHE_ENDPOINTS = '''
# ═══════════════════════════════════════════════════════════════════════════
# Cache lifecycle — startup cleanup + management endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def _startup_cache_cleanup():
    """ลบไฟล์ cache ที่เกิน 30 วัน ทุกครั้งที่ server start."""
    report = cleanup_old_files()
    if report["deleted"]:
        print(f"🗑  Startup cleanup: deleted {len(report['deleted'])} stale files")


@app.get("/api/cache/status")
async def get_cache_status():
    """ดูสถานะ cache — ไฟล์ไหนสด ไฟล์ไหนใกล้หมดอายุ."""
    return cache_status()


@app.post("/api/cache/cleanup")
async def run_cache_cleanup(dry_run: bool = False):
    """สั่งลบไฟล์เก่าเกิน 30 วันทันที (dry_run=true เพื่อดูก่อนไม่ลบจริง)."""
    return cleanup_old_files(dry_run=dry_run)


@app.get("/api/health")'''

app_text = app_path.read_text(encoding="utf-8")
if "/api/cache/status" in app_text:
    print("  ✓ cache endpoints มีอยู่แล้ว (ข้าม)")
elif '@app.get("/api/health")' in app_text:
    app_text = app_text.replace('@app.get("/api/health")', CACHE_ENDPOINTS, 1)
    app_path.write_text(app_text, encoding="utf-8")
    print("  ✓ เพิ่ม startup cleanup + /api/cache/status + /api/cache/cleanup")
else:
    print("  ⚠ ไม่เจอ @app.get(\"/api/health\") — เพิ่ม endpoints เองตามคู่มือ")

# ═══════════════════════════════════════════════════════════════════
# Step 4: Clear pycache
# ═══════════════════════════════════════════════════════════════════
print("\n[4/4] Clear __pycache__")
count = 0
for cache in ROOT.rglob("__pycache__"):
    shutil.rmtree(cache, ignore_errors=True)
    count += 1
print(f"  ✓ ลบ {count} __pycache__ dirs")

print()
print("═" * 66)
print("  ✅ ติดตั้งเสร็จ!")
print("═" * 66)
print("""
ทดสอบ:
  1. รัน server:        make run
  2. ป้อนหุ้นที่ไม่มีใน data/  → ระบบดึงจาก API + เก็บไฟล์ให้อัตโนมัติ
  3. ดูสถานะ cache:     curl http://localhost:8300/api/cache/status
  4. สั่งลบไฟล์เก่าทันที: curl -X POST http://localhost:8300/api/cache/cleanup

หมายเหตุ:
  - ติดตั้งไลบรารี: pip install financetoolkit yfinance
  - FMP: ตั้ง FMP_API_KEY ใน .env หรือ environment (ใช้ key ใหม่ที่ rotate แล้ว!)
    (financetoolkit ต้องมี key ถึงจะดึงงบได้ — ไม่มี key จะ fallback เป็น yfinance)
  - ปรับอายุ cache: แก้ MAX_AGE_DAYS ใน backend/cache_manager.py
""")
