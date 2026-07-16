# DEVLOG entry — copy ไปวางบนสุดของ DEVLOG.md (ใต้ header)

---

## 2026-07-15 · v1.3.0 — Smart Fetch + Auto Cache Cleanup

### 🇹🇭 ภาษาไทย

**Bug ที่แก้:** ป้อนชื่อหุ้นที่ไม่มีไฟล์ใน `data/` → ระบบคืน 404 ไม่ทำงานต่อ

**สิ่งที่ทำ:**
1. **Smart Fetch** — เพิ่ม `load_or_fetch()` ใน `backend/loader.py`:
   - เช็ค `data/{SYMBOL}_financials.json` ก่อน → มีและอายุ ≤ 30 วัน → ใช้ cache (ไม่ยิง API)
   - ไม่มี/หมดอายุ → ดึงอัตโนมัติผ่าน **financetoolkit** (FMP, format ตรงกับไฟล์เดิม 100%) → fallback yfinance → เก็บลง `data/`
   - Fetch พังแต่มีไฟล์เก่า → ใช้ไฟล์เก่าพร้อม warning (graceful degradation)
2. **Auto Cleanup** — `backend/cache_manager.py` ใหม่:
   - ลบ `*_financials.json` ใน `data/` ที่อายุเกิน 30 วันอัตโนมัติ
   - ทำงาน 2 จังหวะ: ตอน server start + ก่อนโหลดหุ้นทุกครั้ง
   - ปลอดภัย: ไม่แตะ subfolder / ไฟล์ประเภทอื่น / โฟลเดอร์อื่น
3. **API ใหม่ 2 ตัว:**
   - `GET /api/cache/status` — ดูอายุ+สถานะทุกไฟล์
   - `POST /api/cache/cleanup?dry_run=` — สั่งลบทันที
4. **Tests** — `tests/test_cache_manager.py` 30 ข้อ (อายุไฟล์, ขอบเขตการลบ, dry run, financetoolkit DataFrame conversion, load_or_fetch)

**ไฟล์ใหม่:** `backend/fetcher.py`, `backend/cache_manager.py`, `tests/test_cache_manager.py`
**ไฟล์ที่แก้:** `backend/loader.py` (เพิ่ม load_or_fetch), `backend/app.py` (endpoints ใช้ load_or_fetch + startup cleanup + cache endpoints)
**Installer:** `apply_smart_fetch.py` (idempotent — รันซ้ำได้)

---

### 🇬🇧 English

**Bug fixed:** Entering a symbol with no file in `data/` returned 404 and stopped.

**Changes:**
1. **Smart Fetch** — new `load_or_fetch()` in `backend/loader.py`: cache-first (file exists and ≤ 30 days old → no API call), otherwise fetch via **financetoolkit** (FMP-backed, field names identical to existing data files) with yfinance fallback, save to `data/`, and gracefully fall back to a stale file if fetching fails.
2. **Auto Cleanup** — new `backend/cache_manager.py`: deletes `*_financials.json` in `data/` older than 30 days. Runs at server startup and before each load. Safety-scoped: first level of `data/` only, matching pattern only.
3. **New endpoints:** `GET /api/cache/status`, `POST /api/cache/cleanup?dry_run=`.
4. **Tests:** `tests/test_cache_manager.py` — 30 tests covering file aging, deletion scope/safety, dry-run, financetoolkit DataFrame→JSON conversion, and load_or_fetch cache-hit/stale paths.

**New files:** `backend/fetcher.py`, `backend/cache_manager.py`, `tests/test_cache_manager.py`
**Modified:** `backend/loader.py`, `backend/app.py` (via `apply_smart_fetch.py`, idempotent)

---
