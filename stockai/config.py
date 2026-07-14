"""
config.py — ค่าคงที่และ path กลางของทั้งระบบ (แก้ที่เดียว ใช้ทุกที่)
"""
from __future__ import annotations

import os

# -------------------------------------------------------------------
# Paths — อ้างอิงจาก root ของโปรเจกต์เสมอ (ไม่ขึ้นกับ cwd)
# -------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(ROOT_DIR, "data")            # งบการเงิน JSON ดิบ
EXPORT_DIR = os.path.join(ROOT_DIR, "expotes")       # ผลลัพธ์ ratio/valuation
ARTIFACT_DIR = os.path.join(ROOT_DIR, "artifacts", "ai")  # โมเดล AI ที่เทรนแล้ว

# ไฟล์โมเดลที่เทรนเสร็จ
RETURN_MODEL_PATH = os.path.join(ARTIFACT_DIR, "return_model.joblib")
CLASS_MODEL_PATH = os.path.join(ARTIFACT_DIR, "valuation_classifier.joblib")
METADATA_PATH = os.path.join(ARTIFACT_DIR, "feature_metadata.json")
METRICS_PATH = os.path.join(ARTIFACT_DIR, "metrics.json")

# -------------------------------------------------------------------
# ชื่อคีย์งบการเงินที่อาจสะกดต่างกัน (รองรับหลายรูปแบบ)
# -------------------------------------------------------------------
KEY_CANDIDATES = {
    "income": ["Income Statement", "Income statement", "Statement of Income"],
    "balance": ["Balance Sheet", "Balance sheet", "Balance Sheet Statement"],
    "cashflow": ["Cash Flow Statement", "Cashflow Statement", "Cash Flow"],
    "basic": ["Basic Info", "Profile", "Company Profile"],
}

# -------------------------------------------------------------------
# พารามิเตอร์ของ AI
# -------------------------------------------------------------------
# ถ้าผลตอบแทน 1 ปีข้างหน้า > ค่านี้ => ตีตรา "ถูก/น่าซื้อ" (label = 1)
UNDERVALUED_THRESHOLD = 0.10  # 10%

# ฟีเจอร์ที่ใช้ป้อนโมเดล (เลือกตัวที่มีความหมายและมักไม่ว่าง)
# มาจาก ratio ใน expotes/result.json + ฟีเจอร์การเติบโตที่คำนวณเพิ่ม
RATIO_FEATURES = [
    "ROE", "ROA", "EBITDA Margin", "Net Profit Margin",
    "Gross Profit Margin", "Operating Profit Margin",
    "Current Ratio", "Quick Ratio", "Cash Ratio",
    "Asset Turnover", "Inventory Turnover", "Receivables Turnover",
    "PE Ratio", "PBV Ratio",
    "Debt to Equity", "Debt to Assets", "Altman Z-Score",
]
GROWTH_FEATURES = ["Revenue Growth", "Net Income Growth", "FCF Growth"]
FEATURE_COLUMNS = RATIO_FEATURES + GROWTH_FEATURES
