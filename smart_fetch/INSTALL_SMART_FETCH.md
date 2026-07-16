# 🚀 Smart Fetch + Auto Cache Cleanup — คู่มือติดตั้ง

แก้ bug: ป้อนหุ้นที่ไม่มีใน `data/` แล้วระบบไม่ทำงาน
เพิ่ม: ดึงจาก API อัตโนมัติ + ลบไฟล์เกิน 1 เดือนอัตโนมัติ

---

## 📁 ไฟล์ในชุดนี้ (4 ไฟล์)

| # | ไฟล์ | วางที่ | หน้าที่ |
|---|------|--------|--------|
| 1 | `backend/fetcher.py` | `backend/` | ดึงข้อมูลผ่าน **financetoolkit** (FMP) → yfinance fallback |
| 2 | `backend/cache_manager.py` | `backend/` | ลบไฟล์เกิน 30 วัน + รายงานสถานะ |
| 3 | `apply_smart_fetch.py` | root โปรเจกต์ | Patch script ติดตั้งอัตโนมัติ |
| 4 | `tests/test_cache_manager.py` | `tests/` | Tests 26 ข้อ |

---

## ⚡ ติดตั้ง — 4 ขั้นตอน

```bash
cd ~/Desktop/pro_stock_analyzer_v1.2

# 1) Copy ไฟล์เข้าตำแหน่ง (สมมติ unzip ไว้ที่ ~/Downloads/smart_fetch/)
cp ~/Downloads/smart_fetch/backend/fetcher.py backend/
cp ~/Downloads/smart_fetch/backend/cache_manager.py backend/
cp ~/Downloads/smart_fetch/apply_smart_fetch.py .
cp ~/Downloads/smart_fetch/tests/test_cache_manager.py tests/

# 2) รัน patch script — แก้ loader.py + app.py ให้อัตโนมัติ
python3 apply_smart_fetch.py

# 3) ติดตั้งไลบรารี — financetoolkit (หลัก) + yfinance (fallback ฟรี)
pip install financetoolkit yfinance

# 4) ทดสอบ
PYTHONPATH=$(pwd) pytest tests/test_cache_manager.py -v
# → ควรเห็น 26 passed
```

---

## 🔑 ตั้ง API Key (ถ้าใช้ FMP)

⚠️ **สำคัญ: ใช้ key ใหม่ที่ rotate แล้วเท่านั้น!** (key เดิมรั่วในไฟล์ที่แชร์ไปแล้ว
ต้องไปที่ FMP dashboard → regenerate ก่อน)

```bash
# สร้าง .env ที่ root โปรเจกต์
echo 'FMP_API_KEY=ใส่_KEY_ใหม่ที่_ROTATE_แล้ว' > .env

# หรือ export ชั่วคราว
export FMP_API_KEY=ใส่_KEY_ใหม่
```

**ทำไมต้องมี key:** financetoolkit ดึงงบการเงินจาก FMP — ไม่มี key จะดึงงบไม่ได้
ไม่ตั้ง key ก็ได้ — ระบบจะข้ามไปใช้ yfinance (ฟรี) แทนอัตโนมัติ

**ข้อดีของ financetoolkit:** ชื่อ field ที่ได้ตรงกับไฟล์ใน data/ เดิม 100%
(เช่น "Cost of Goods Sold", "Total Equity", "Operating Cash Flow") เพราะไฟล์เดิม
ก็สร้างจาก format เดียวกัน — ข้อมูลใหม่กับเก่าจึงใช้ร่วมกันได้สนิท

---

## ✅ ทดสอบว่าทำงานจริง

```bash
make run
```

### เทส 1: หุ้นที่ไม่มีใน data/ (นี่คือ bug เดิม)

เปิด browser → พิมพ์หุ้นที่ไม่มี เช่น `KO` → Analyze

**พฤติกรรมใหม่:** ระบบดึงจาก API → เก็บ `data/KO_financials.json` → วิเคราะห์ต่อทันที
(ครั้งแรกช้าหน่อย ~2-5 วินาที ครั้งต่อไปเร็วเพราะใช้ cache)

### เทส 2: ดูสถานะ cache

```bash
curl http://localhost:8300/api/cache/status | python3 -m json.tool
```

เห็นทุกไฟล์พร้อมอายุ (วัน) และสถานะ fresh/stale

### เทส 3: สั่งลบไฟล์เก่าทันที

```bash
# ดูก่อนว่าจะลบอะไร (ไม่ลบจริง)
curl -X POST "http://localhost:8300/api/cache/cleanup?dry_run=true"

# ลบจริง
curl -X POST http://localhost:8300/api/cache/cleanup
```

---

## 🔄 Flow การทำงานใหม่

```
ผู้ใช้ป้อนชื่อหุ้น
      │
      ▼
[auto cleanup] ลบไฟล์ *_financials.json ที่เกิน 30 วันใน data/
      │
      ▼
มีไฟล์ใน data/ และอายุ ≤ 30 วัน?
      │
  ┌───┴───┐
 ใช่      ไม่
  │        │
  ▼        ▼
ใช้ cache  ดึงจาก API (FMP → yfinance)
(ไม่ยิง API)  │
           ▼
        เก็บลง data/{SYMBOL}_financials.json
           │
           ▼
        วิเคราะห์ตามปกติ
```

**Cleanup ทำงานอัตโนมัติ 2 จังหวะ:**
1. ทุกครั้งที่ server start
2. ทุกครั้งที่มีการโหลดหุ้น (ก่อนเช็ค cache)

**ความปลอดภัย:** ลบเฉพาะ `*_financials.json` ชั้นแรกของ `data/` เท่านั้น
— ไม่แตะ subfolder, ไม่แตะไฟล์ .txt/.csv อื่นๆ, ไม่แตะโฟลเดอร์อื่น

---

## ⚙️ ปรับแต่ง

| ต้องการ | แก้ที่ |
|---------|--------|
| เปลี่ยนอายุ cache (เช่น 7 วัน) | `backend/cache_manager.py` → `MAX_AGE_DAYS = 7` |
| ดึงย้อนหลังมากกว่า 5 ปี | `backend/fetcher.py` → `START_DATE = "2014-01-01"` |
| ปิด auto cleanup ต่อ request | `load_or_fetch(symbol, auto_cleanup=False)` |

---

## 🐛 Troubleshooting

**"Cannot fetch XXX from any source"**
- เช็ค internet + สะกดชื่อหุ้นถูกไหม
- เช็คว่าติดตั้งแล้ว: `pip install financetoolkit yfinance`
- ถ้าใช้ FMP: เช็ค key ใน .env (free tier มี limit 250 calls/วัน)

**ModuleNotFoundError: financetoolkit / yfinance**
- `pip install financetoolkit yfinance`

**ไฟล์เก่าไม่ถูกลบ**
- Cleanup ดูจาก modified time — `touch data/XXX_financials.json` จะรีเซ็ตอายุ
- เช็คด้วย `python3 backend/cache_manager.py` (รันตรงๆ ได้)
