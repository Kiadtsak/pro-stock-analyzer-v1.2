# DEVLOG — จัดโครงสร้างใหม่ + เพิ่มระบบ AI

วันที่: 2026-06-06

## เป้าหมายที่ผู้ใช้สั่ง
1. จัดโครงสร้างโปรเจกต์ใหม่ให้ชัดเจน อ่านง่าย แก้ไขง่าย เพิ่มฟังก์ชันใหม่ได้
2. เพิ่มฟังก์ชัน AI
3. เทรน AI จากงบการเงินใน `data/` และ `expotes/` ให้เก่งสำหรับโปรเจกต์นี้
4. ขอบเขต (ผู้ใช้เลือก): **Python core + FastAPI**
5. งานของ AI (ผู้ใช้เลือก): **ทำนายผลตอบแทน 1 ปี + ตีตราถูก/แพง**

---

## สิ่งที่ทำไปแล้ว ✅

### 1. สำรวจของเดิม (ไม่แตะของที่ใช้ได้)
- ยืนยัน pipeline เดิมรันผ่าน: `Backend/calculater_all.py` คำนวณ 32 ratio/ปี ได้
- พบว่า `data/*.json` มี `Basic Info.Prices` = ราคาหุ้นรายปี → ใช้เป็น "เฉลย" เทรน AI ได้
- เช็ค lib: scikit-learn 1.5.1, pandas 2.2.3, numpy 1.26.4, fastapi 0.115.6 — ครบ

### 2. สร้างแพ็กเกจใหม่ `stockai/`
| ไฟล์ | หน้าที่ |
|------|---------|
| `__init__.py` | เวอร์ชัน + คำอธิบายโครงสร้าง |
| `config.py` | path + ค่าคงที่กลาง (FEATURE_COLUMNS, threshold ฯลฯ) |
| `data_loader.py` | โหลด/แยกงบ JSON, `list_symbols()` |
| `features.py` | `build_dataset()` (features+label) และ `build_feature_row()` |
| `pipeline.py` | `analyze()` = ratio + valuation + AI (เรียกใช้ Backend เดิม) |
| `cli.py` | คำสั่ง: list / train / predict / analyze |
| `api.py` | FastAPI: /predict /analyze /train /metrics /symbols /health |
| `ai/trainer.py` | เทรน 2 โมเดล + ประเมินผลแบบ GroupKFold |
| `ai/predictor.py` | โหลดโมเดล → พยากรณ์รายหุ้น / ทุกหุ้น |
| `README.md` | คู่มือใช้งานฉบับเต็ม |

### 3. ระบบ AI (เทรนจากข้อมูลจริง)
- **Features**: 17 ratio + 3 growth (Revenue/Net Income/FCF) = 20 ฟีเจอร์
- **Label**: ผลตอบแทนราคา Y→Y+1 จาก `Prices`; ตีตรา 1 ถ้า return > 10%
- **โมเดล**: RandomForest (Regressor + Classifier) ใน sklearn Pipeline
  มี SimpleImputer เติมค่าว่างด้วย median
- **ประเมินผล**: GroupKFold จัดกลุ่มตามหุ้น (กันข้อมูลรั่วข้ามบริษัทเดียวกัน)
- บันทึกที่ `artifacts/ai/`: return_model.joblib, valuation_classifier.joblib,
  feature_metadata.json, metrics.json

### 4. ทดสอบแล้วทำงานครบ
- `train` → 55 แถว / 8 หุ้น / 20 ฟีเจอร์ เทรนสำเร็จ
- `predict NVDA` → return คาดการณ์ + verdict + ความมั่นใจ
- `predict --all` → จัดอันดับทุกหุ้น
- `analyze NVDA` → ratio + valuation + AI รวมกัน
- `import stockai.api` → 7 endpoints พร้อมใช้

### 5. อัปเดต `requirements.txt`
- เพิ่ม scikit-learn, joblib, uvicorn

---

## ผลประเมินโมเดล (รอบแรก) — ตามจริง
- Regression: MAE 0.589 (baseline 0.598), R² ≈ 0.02
- Classifier: Acc 0.60, F1 0.74, AUC 0.41
- **สรุป**: โมเดลทำงานครบวงจร แต่ความแม่นยำยัง "เกือบเท่าเดา" เพราะข้อมูลแค่
  55 ตัวอย่าง — เป็นเรื่องปกติของการทำนายราคาหุ้นด้วยข้อมูลน้อย

---

---

## รอบที่ 2 — เชื่อม AI เข้าหน้าเว็บ Next.js ✅ (2026-06-06)

### ไฟล์ที่เพิ่ม/แก้ในฝั่ง frontend
| ไฟล์ | หน้าที่ |
|------|---------|
| `app/api/predict/route.ts` (ใหม่) | Next.js route proxy → FastAPI `GET /predict/{symbol}` มี fallback ตอน backend ออฟไลน์ (503) |
| `components/AIPredictionCard.tsx` (ใหม่) | การ์ดแสดงผล ML: expected return 1 ปี + verdict ถูก/แพง + แถบ confidence (ธีม luxe) |
| `app/ai-analysis/page.tsx` (แก้) | import + ฝัง `<AIPredictionCard>` ใน sidebar ซ้าย แสดงคู่กับรายงาน LLM |

### การเชื่อมต่อ
```
หน้า ai-analysis → /api/predict?symbol=X (Next route)
                 → BACKEND_URL/predict/X  (FastAPI stockai.api)
                 → RandomForest models    (artifacts/ai/)
```
- ใช้ env เดิม `BACKEND_URL` (มีใน .env.local อยู่แล้ว = http://127.0.0.1:8000)
- LLM report (เชิงคุณภาพ) + ML prediction (เชิงปริมาณ) อยู่หน้าเดียวกัน

### ทดสอบแล้ว (ทั้งสายจริง)
- รัน `uvicorn stockai.api:app --port 8000` + `next dev`
- curl ผ่าน proxy: NVDA → +18.4% Undervalued, AAPL → +33.7% Undervalued ✅
- `tsc --noEmit` ไฟล์ใหม่ผ่านหมด (error ที่เหลือเป็นของเดิม: ขาด `@/lib/auth/*`, `@/components/auth/*`)

### วิธีใช้งานจริง (2 เทอร์มินัล)
```bash
# 1) backend
uvicorn stockai.api:app --port 8000
# 2) frontend
cd frontend-nextjs/frontend && npm run dev
# เปิด /ai-analysis?symbol=NVDA → เห็นการ์ด ML Prediction
```

---

---

## รอบที่ 3 — ดึงงบ 100 หุ้น + เทรน AI ใหม่ (2026-06-06)

### ไฟล์ที่เพิ่ม/แก้
| ไฟล์ | หน้าที่ |
|------|---------|
| `harvester.py` (ใหม่) | ดึงงบจาก FinanceToolkit+FMP (ใช้ `Backend.financials_provider`) มาเก็บ `data/` แบบ **10 ตัว/นาที** |
| `cli.py` (แก้) | เพิ่มคำสั่ง `harvest` (`--train`, `--force`, `--batch-size`, `--batch-seconds`) |

### รายละเอียด harvester
- `DEFAULT_UNIVERSE` = 100 หุ้น US large-cap
- `harvest()` ดึงทีละ batch 10 ตัว, แต่ละ batch ใช้เวลา ≥60 วิ (กัน rate limit FMP)
- ข้ามไฟล์ที่มีแล้ว (skip-existing) เว้นแต่ `--force`; ดึงพังตัวไหนข้ามตัวนั้น ไม่ล้มทั้ง batch
- `harvest_and_train()` ดึงครบแล้วเรียก `ai.trainer.train()` ต่อทันที

### ผลจริง ✅
- ดึง MSFT เดี่ยวสำเร็จก่อน (API key ใช้ได้)
- รัน `harvest --train` เบื้องหลังจนจบ: **สำเร็จ 91, ข้าม 9, ผิดพลาด 0** → ตอนนี้มี **102 ไฟล์ใน data/**
- ชุดข้อมูลเทรนโตจาก **55 → 708 แถว / 101 หุ้น**

### Metrics ก่อน→หลังเพิ่มข้อมูล
| ตัวชี้วัด | เดิม (8 หุ้น) | ใหม่ (101 หุ้น) |
|----------|------|------|
| Classifier AUC | 0.41 (แย่กว่าเดา) | **0.57 (มีสัญญาณจริง)** |
| Classifier Acc / F1 | 0.60 / 0.74 | 0.55 / 0.63 |
| Regression R² | 0.02 | -0.03 (ทำนายตัวเลข return แม่นยาก) |
| Top features | Cash/Current/PE | **Net Income Growth, FCF Growth** (สมเหตุสมผลขึ้น) |

> สรุป: **classifier (ถูก/แพง) ดีขึ้นชัด** จากแย่กว่าเดาเป็นมีสัญญาณจริง.
> ส่วน regression ทำนายขนาด return ยังยาก (ปกติของการพยากรณ์ราคาหุ้น).

---

## รอบที่ 4 — ดึงเพิ่มอีก 100 หุ้น (universe 2) + เทรนใหม่ (2026-06-07)

- เพิ่ม `UNIVERSE_2` (100 หุ้นใหม่: semis/cloud/fintech/China ADR/autos/energy/materials/industrials)
  + `FULL_UNIVERSE` (รวม ~200) ใน `harvester.py`
- เพิ่มออปชัน CLI `harvest --symbols "A,B,C"` ดึงหุ้นเองได้โดยไม่แก้โค้ด
- ตรวจ dedup: universe 2 ไม่ซ้ำกับ universe 1 และข้อมูลเดิมเลย (100 ตัวใหม่ทั้งหมด)
- รัน `harvest_and_train(symbols=UNIVERSE_2)`: **สำเร็จ 100, ผิดพลาด 0** → ตอนนี้ **202 ไฟล์ใน data/**
- ชุดเทรนโต **708 → 1,373 แถว / 201 หุ้น**
- รีสตาร์ท stockai backend (:8100) ให้เว็บใช้โมเดลใหม่; ทดสอบผ่านเว็บ UBER/BABA/MRVL/COIN/NU ได้ ✅

### Metrics พัฒนาการตามจำนวนข้อมูล
| | 8 หุ้น (55) | 101 หุ้น (708) | **201 หุ้น (1,373)** |
|--|--|--|--|
| Regression R² | 0.02 | -0.03 | **0.05 (เป็นบวกแล้ว)** |
| Classifier AUC | 0.41 | 0.57 | **0.59** |
| Top features | Cash/PE | Income/FCF Growth | Income Growth, Debt/Assets, ROA |

> ยิ่งข้อมูลมาก ทั้ง regression และ classifier ดีขึ้นต่อเนื่อง

---

## รอบที่ 5 — เพิ่มหุ้นง่ายขึ้น + โหมดอัปเดต (2026-06-08)

ปัญหาที่ผู้ใช้เจอ: `harvest --train` ขึ้น "สำเร็จ 0 ข้าม 100" เพราะมีครบแล้ว + ถ้าเพิ่มหุ้น
แค่ตัวเดียวก็ยังเสียเวลา wait 60 วิ/batch ฟรี

แก้ไข `harvester.py` + `cli.py`:
- **`universe.txt`** (ใหม่) — รายชื่อหุ้น 202 ตัว, เพิ่มหุ้นแค่แก้ไฟล์นี้; `load_universe()` อ่านให้
- **หน่วงเฉพาะการดึงจริง** — ตัวที่ถูกข้ามไม่นับ ไม่เสียเวลารอ (เพิ่ม 1 ตัวใหม่ → เสร็จใน ~11 วิ)
- **โหมด `--update`** + `--min-year` — ดึงทับเฉพาะตัวที่ปีงบล่าสุด < min_year (ดีฟอลต์ ปีปัจจุบัน−1)
  คืน `updated` ในสรุปผล
- ปรับ default `harvest` (ไม่ใส่ symbols) ให้อ่านจาก universe.txt แทน DEFAULT_UNIVERSE

ทดสอบ: `harvest --symbols "AAPL,NVDA,DELL"` → ข้าม 2 ดึง DELL ใน ~11 วิ; `--update` ข้อมูลทันสมัย → ข้ามหมด ✅
(ตอนนี้ data มี 203 ไฟล์ — เพิ่ม DELL จากการทดสอบ)

### คำสั่งสรุป
```bash
python -m stockai.cli harvest --train                          # ดึงตัวใหม่ใน universe.txt + เทรน
python -m stockai.cli harvest --symbols "DELL,WDC" --train     # ดึงเฉพาะกิจ
python -m stockai.cli harvest --update --min-year 2026 --train # อัปเดตงบปีใหม่
python -m stockai.cli harvest --force --train                  # รีเฟรชทุกตัว
```

---

## รอบที่ 6 — ดึงรายชื่อหุ้นสดจาก API (ไม่ต้องพิมพ์ universe.txt) (2026-06-08)

ผู้ใช้ไม่อยากดูแล universe.txt เอง — อยากให้ดึง "รายชื่อหุ้น" จาก API มาเลย แล้วเช็ค data/
ตัวไหนยังไม่มีค่อยโหลด

เพิ่มใน `harvester.py`:
- **`fetch_symbol_list(sources)`** — ดึงรายชื่อจาก FMP: `sp500` (503) / `nasdaq` (101) / `dowjones` (30)
  คั่น comma ได้ เช่น "sp500,nasdaq,dowjones"
- `harvest(source=...)` — ถ้าระบุ source จะดึงรายชื่อสดจาก API แทน universe.txt
  แล้ว **ข้ามตัวที่มีใน data/ ดึงเฉพาะที่ขาด** (ลำดับ: symbols > source > universe.txt)
- CLI: เพิ่ม `--source`

ทดสอบ: S&P 500 = 503 ตัว, มีใน data แล้ว 148 (ข้าม), ขาด 355 (ดึงใหม่)
รัน `harvest --source sp500 --train` เบื้องหลัง — ดึง 355 ตัวที่ขาด + เทรน

### คำสั่ง (วิธีที่ผู้ใช้ต้องการ — ไม่ต้องแก้ไฟล์)
```bash
python -m stockai.cli harvest --source sp500 --train               # S&P 500
python -m stockai.cli harvest --source sp500,nasdaq,dowjones --train  # รวมหลายดัชนี
python -m stockai.cli harvest --source sp500,nasdaq,dowjones --dry-run  # ดูเฉยๆ ไม่โหลด
```

### เพิ่ม `--dry-run` (ตอบคำถาม "จะไม่ให้ดึงทำยังไง")
- โชว์ว่าจะดึง/ข้ามตัวไหน แต่ไม่โหลดจริง ไม่เทรน ไม่เปลือง API
- หยุด harvest ที่รันอยู่: foreground กด Ctrl+C / background ใช้ TaskStop

---

## ข้อจำกัด / สิ่งที่ควรทำต่อ
- [ ] เพิ่มจำนวนหุ้นใน `data/` (ยิ่งมากยิ่งแม่น) แล้ว train ใหม่
- [ ] valuation `intrinsic_value_per_share` คืน None เพราะ export ไม่มี Shares Outstanding
      (เป็นข้อจำกัดของโค้ดเดิม ยังไม่แก้)
- [ ] ยังไม่ได้ลบ/ย้ายไฟล์ซ้ำของเดิม (`CashFlowModelas.py`, `*.bak`, `data/reult.csv`)
      — เก็บไว้ก่อนเพื่อความปลอดภัย ค่อยเคลียร์เมื่อมั่นใจ
- [ ] ยังไม่ได้ commit (ผู้ใช้ยังไม่สั่ง)
- [x] ~~ต่อ AI เข้าหน้าเว็บ Next.js~~ — เสร็จแล้วในรอบที่ 2
