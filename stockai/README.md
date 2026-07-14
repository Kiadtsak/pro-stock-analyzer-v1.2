# stockai — โครงสร้างใหม่ + ระบบ AI ประเมินมูลค่าหุ้น

แพ็กเกจ Python ที่จัดระเบียบโปรเจกต์ให้ **อ่านง่าย แก้ไขง่าย ต่อยอดได้** และเพิ่ม
ระบบ AI ที่ **เทรนจากงบการเงิน + ราคาหุ้นจริง** ที่มีอยู่ในโฟลเดอร์ `data/`

## โครงสร้าง

```
stockai/
├── config.py          # path + ค่าคงที่ทั้งหมด (แก้ที่เดียว ใช้ทุกที่)
├── data_loader.py     # โหลด/ตรวจงบการเงิน JSON จาก data/
├── features.py        # สร้างชุดข้อมูลฝึก: features (ratio) + label (return จริง)
├── pipeline.py        # โหลด → ratio → valuation → AI ครบในที่เดียว
├── cli.py             # คำสั่งเทอร์มินัล
├── api.py             # FastAPI เปิดเป็นบริการเว็บ
└── ai/
    ├── trainer.py     # เทรน 2 โมเดล + ประเมินผลแบบ cross-validation
    └── predictor.py   # โหลดโมเดล → พยากรณ์รายหุ้น
```

> ส่วนคำนวณคณิตศาสตร์ (CashFlowModel, ratios, DCF) ยังเรียกใช้โมดูลเดิมใน `Backend/`
> ที่ทำงานได้อยู่แล้ว — โครงสร้างใหม่นี้ห่อหุ้มให้สะอาดโดยไม่ทำของเดิมพัง

## AI ทำอะไร

| โมเดล | ทำนายอะไร | ชนิด |
|-------|-----------|------|
| `return_model` | ผลตอบแทนราคา 1 ปีข้างหน้า (%) | Regression |
| `valuation_classifier` | ตีตรา "ถูก/น่าซื้อ" vs "แพง/เลี่ยง" | Classification |

**วิธีเรียนรู้:** ใช้อัตราส่วนการเงินของปี Y เป็น features และใช้ราคาจริงปี Y→Y+1
(`Basic Info.Prices`) เป็นเฉลย — จึงเทรนได้จากข้อมูลที่มีอยู่โดยไม่ต้องดึงข้อมูลนอก

## วิธีใช้ (CLI)

```bash
python -m stockai.cli list            # ดูหุ้นที่มีข้อมูล
python -m stockai.cli train           # เทรนโมเดลจากข้อมูลทั้งหมด
python -m stockai.cli predict NVDA    # พยากรณ์หุ้นเดียว
python -m stockai.cli predict --all   # พยากรณ์ทุกหุ้น เรียงตามผลตอบแทน
python -m stockai.cli analyze NVDA    # ratio + valuation + AI ครบชุด
```

## วิธีใช้ (เว็บ / FastAPI)

> ⚠️ ใช้ **port 8100** (ไม่ใช่ 8000) เพราะ backend เดิมของโปรเจกต์ใช้ 8000 อยู่แล้ว
> หน้าเว็บอ่าน URL นี้จาก env `STOCKAI_URL` (ตั้งไว้ใน `frontend-nextjs/frontend/.env.local`)

```bash
uvicorn stockai.api:app --reload --port 8100
# เปิด http://localhost:8100/docs เพื่อทดลอง API
```

| Endpoint | หน้าที่ |
|----------|---------|
| `GET /predict/{symbol}` | พยากรณ์รายหุ้น |
| `GET /predict` | พยากรณ์ทุกหุ้น |
| `GET /analyze/{symbol}` | ratio + valuation + AI |
| `POST /train` | เทรนโมเดลใหม่ |
| `GET /metrics` | ผลประเมินโมเดลล่าสุด |

## ⚠️ ข้อจำกัดเรื่องข้อมูล (อ่านก่อนเชื่อผล)

ตอนนี้มีข้อมูลเพียง **8 หุ้น × ~10 ปี = 55 ตัวอย่าง** ซึ่ง**น้อยมาก**สำหรับการ
ทำนายราคาหุ้น ผลที่ได้จึงยังเชื่อถือไม่ได้สูง (cross-validation R² ใกล้ 0)

**โครงสร้างพร้อมแล้ว — ความแม่นยำจะดีขึ้นเองเมื่อเพิ่มข้อมูล** โดย:
1. เพิ่มไฟล์งบหุ้นตัวอื่นลง `data/{SYMBOL}_financials.json` (ยิ่งหลากหลายยิ่งดี)
2. รัน `python -m stockai.cli train` ใหม่

## เพิ่ม / อัปเดตข้อมูลหุ้น (harvest)

**เพิ่มหุ้น** = แก้ไฟล์ `stockai/universe.txt` (1 บรรทัด = 1 ticker) แล้วรัน harvest
ระบบจะ **ข้ามตัวที่มีข้อมูลแล้ว** และ **ดึงเฉพาะตัวใหม่** (หน่วงเฉพาะการดึงจริง 10 ตัว/นาที)

```bash
# ดึงทุกตัวใน universe.txt ที่ยังไม่มี แล้วเทรนต่อ
python -m stockai.cli harvest --train

# ดึงหุ้นเฉพาะกิจโดยไม่ต้องแก้ไฟล์
python -m stockai.cli harvest --symbols "DELL,WDC,HPQ" --train

# อัปเดตงบให้เป็นปีล่าสุด (ดึงทับเฉพาะตัวที่งบเก่ากว่าเกณฑ์)
python -m stockai.cli harvest --update --train                 # เกณฑ์ = ปีปัจจุบัน−1
python -m stockai.cli harvest --update --min-year 2026 --train # ไล่หางบปี 2026

# รีเฟรชทุกตัวใหม่หมด (ใช้เมื่อรู้ว่ามีงบใหม่ออกแล้ว)
python -m stockai.cli harvest --force --train
```

> ⚠️ หลัง `--train` ต้องรีสตาร์ท backend (`uvicorn stockai.api:app --port 8100`)
> ให้เว็บใช้โมเดลใหม่

## ต่อยอดอย่างไร

- **เพิ่มฟีเจอร์ใหม่**: แก้ `config.RATIO_FEATURES` / `GROWTH_FEATURES`
- **เปลี่ยนโมเดล**: แก้ `_build_regressor()` / `_build_classifier()` ใน `ai/trainer.py`
- **เพิ่มเป้าหมายใหม่**: เพิ่ม label ใน `features.build_dataset()` แล้วเทรนเพิ่ม
```
