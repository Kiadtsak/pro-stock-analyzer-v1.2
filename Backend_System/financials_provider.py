# name , financials_statement.py

from financetoolkit import Toolkit
from dotenv import load_dotenv
import json, os, pandas as pd
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# โหลด .env ระดับโมดูล (ปลอดภัยกว่าการเรียกใน class body)
load_dotenv()


class FinancialsStatement:
    """
    - ถ้ามีไฟล์ data/{symbol}_financials.json → โหลด
    - ถ้าไม่มี → ดึงจาก API (FinanceToolkit + FMP price) แล้วบันทึก
    - รองรับ refresh บังคับดึงใหม่
    """
    def __init__(self, symbol: str, data_dir: str = "data", **kwargs) -> None:
        if not symbol:
            raise ValueError("ต้องระบุสัญลักษณ์หุ้น เช่น 'NVDA'")
        self.symbol = symbol.upper().strip()

        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            raise EnvironmentError("กรุณาตรวจสอบ API_KEY ในไฟล์ .env")

        self.data_dir = data_dir
        self.lookback_years = 10 # จำนวนปีย้อนหลังที่ต้องการดึงข้อมูล
        self.quarterly = kwargs.get("quarterly", False)  # ถ้า True จะดึงข้อมูลรายไตรมาส
        os.makedirs(self.data_dir, exist_ok=True)

        self.file_path = os.path.join(self.data_dir, f"{self.symbol}_financials.json")
        # Toolkit รองรับ list หรือ str ก็ได้
        self.toolkit = Toolkit([self.symbol], api_key=self.api_key)
        self.basic_info: Dict[str, Any] = {}
        self.data: Dict[str, Any] = {}

    # ---------- Public ----------
    def load_data_json_or_api(self, force: bool = False) -> Dict[str, Any]:
        """
        โหลดไฟล์ถ้ามี (และไม่ force) ไม่งั้นดึง API แล้วบันทึก
        Return: dict { Basic Info, Income Statement, Balance Sheet, Cash Flow Statement }
        """
        if os.path.exists(self.file_path) and not force:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            print(f" โหลดข้อมูลจากไฟล์สำเร็จ: {self.symbol}")
            return self.get_combined_data()

        print(f" ไม่พบไฟล์ {self.file_path} หรือสั่ง refresh -> ดึงจาก API ...")
        self._load_financials_from_api()
        self.save_to_json()
        print(" ดึงข้อมูลจาก API และบันทึกผลเรียบร้อย")
        return self.get_combined_data()

    def refresh(self) -> Dict[str, Any]:
        """ บังคับดึงใหม่จาก API """
        return self.load_data_json_or_api(force=True)

    # ---------- Internals ----------
    def _load_financials_from_api(self) -> None:
        print(f"🔄 กำลังโหลดข้อมูลการเงินของ {self.symbol}...")
        # 1) งบการเงิน (FinanceToolkit)
        income_statement = self.toolkit.get_income_statement()
        balance_sheet = self.toolkit.get_balance_sheet_statement()
        cash_flow_statement = self.toolkit.get_cash_flow_statement()

        if any(df is None for df in (income_statement, balance_sheet, cash_flow_statement)):
            raise RuntimeError("❌ ดึงงบการเงินไม่สำเร็จ (ตรวจ API Key / Symbol)")

        # 2) ราคาปัจจุบัน + ประวัติรายปี (FMP)
        quote_url = f"https://financialmodelingprep.com/api/v3/quote/{self.symbol}?apikey={self.api_key}"
        resp = requests.get(quote_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError(f"ไม่พบข้อมูล quote ของ {self.symbol} จาก FMP")

        hist_url = (
            f"https://financialmodelingprep.com/api/v3/historical-price-full/"
            f"{self.symbol}?serietype=line&timeseries=2000&apikey={self.api_key}"
        )
        hist_resp = requests.get(hist_url, timeout=60)
        hist_resp.raise_for_status()
        hist_data = hist_resp.json() or {}
        historical = hist_data.get("historical", []) or []

        # หาราคาใกล้สิ้นปีที่สุดในแต่ละปี
        year_to_prices = {}
        for item in historical:
            try:
                d = datetime.strptime(item["date"], "%Y-%m-%d")
                year_to_prices.setdefault(d.year, []).append((d, float(item["close"])))
            except Exception:
                continue

        prices_by_year: Dict[int, float] = {}
        for year, entries in year_to_prices.items():
            target = datetime(year, 12, 31)
            closest = min(entries, key=lambda x: abs((x[0] - target).days))
            prices_by_year[year] = round(closest[1], 2)

        # ปีที่มีในงบ (จะเก็บเฉพาะปีที่มีงบจริง)
        try:
            available_years = set(income_statement.T.index.astype(str))
        except Exception:
            raise RuntimeError("ไม่สามารถอ่าน index ของ Income Statement ได้")

        prices_filtered: Dict[str, float] = {
            str(y): p for y, p in prices_by_year.items() if str(y) in available_years
        }

        # Basic Info ควรใช้คีย์ "Symbol" ตามที่ pipeline อื่นอ้างถึง
        self.basic_info = {
            "Symbol": self.symbol,
            "Name": data[0].get("name", ""),
            "CurrentPrice": data[0].get("price", 0.0),
            "MarketCap": data[0].get("marketCap", 0.0),
            "Prices": prices_filtered,  # ราคาปลายปีต่อปี
        }

        # รวมข้อมูลเป็น JSON-friendly
        income_statement_data = json.loads(income_statement.T.to_json(orient="index"))
        # เติมราคา (ปลายปี) ต่อปีไว้ในงบรายได้เพื่อสะดวก downstream
        for y_str, price in prices_filtered.items():
            if y_str in income_statement_data:
                income_statement_data[y_str]["price"] = price

        self.data = {
            "Basic Info": self.basic_info,
            "Income Statement": income_statement_data,
            "Balance Sheet": json.loads(balance_sheet.T.to_json(orient="index")),
            "Cash Flow Statement": json.loads(cash_flow_statement.T.to_json(orient="index")),
        }

    def save_to_json(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        print(f" บันทึกข้อมูลสำเร็จที่ {self.file_path}")

    def get_combined_data(self) -> Dict[str, Any]:
        if not self.data:
            print(" self.data ยังว่าง")
            return {}
        return {
            "Basic Info": self.data.get("Basic Info", {}),
            "Income Statement": self.data.get("Income Statement", {}),
            "Balance Sheet": self.data.get("Balance Sheet", {}),
            "Cash Flow Statement": self.data.get("Cash Flow Statement", {}),
        }
