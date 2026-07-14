import os
import os

from pydantic import SecretStr, field_validator


API_KEY: str | None = None
OPENAI_API_KEY: str | None = None
YEAR = ["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027"]
TAX_RATE = 0.21                                         # อัตราภาษีนิติบุคคล 21% สำหรับสหรัฐอเมริกา
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # โฟลเดอร์ของไฟล์ปัจจุบัน
DATA_DIR = os.path.join(BASE_DIR, "data")
RISK_FREE_RATE = 0.03                                   # อัตราผลตอบแทนที่ปราศจากความเสี่ยง (3% สำหรับสหรัฐอเมริกา)
BETA = 1.0                                                 # ค่า Beta ของหุ้น (1.0 หมายถึงความเสี่ยงเท่าตลาด)
PRICE_STOCK = float()#input("Enter the current stock price: ")  # รับราคาหุ้นจากผู้ใช้
     
    # === ตั้งค่าโมเดลและข้อมูล ===
DATA_PATH = "exports/result.json"  # ชี้ไปไฟล์ JSON ของคุณ
MODEL_PATH = "exports/fair_value_model.pkl"
SCALER_PATH = "artifacts/scaler.pkl"
FEATURES_PATH = "artifacts/features.txt"

    # ตั้งชื่อคอลัมน์เป้าหมาย (ต้องมีในไฟล์ JSON)
    # ถ้าคุณทำ label ชื่ออื่น เช่น "Fair Value", "Intrinsic Value", "Target Price" ให้ใส่ตรงนี้
TARGET_COLUMN = "Fair Value"

    # คอลัมน์ที่ไม่ใช่ฟีเจอร์ในการเทรน
EXCLUDE_COLUMNS = ["Stock Symbol", "Year"]

#    ค่าทั่วไป
TEST_SIZE = 0.2
RANDOM_STATE = 42
N_JOBS = -1



