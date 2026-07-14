"""
features.py — ประกอบชุดข้อมูลฝึก (panel data) จากฟีเจอร์ ~85 ตัว + ราคาจริง
=============================================================================

  - **Features** = ฟีเจอร์การเงิน ~85 ตัวของปี Y (จาก feature_engineering)
  - **Target (regression)** = ผลตอบแทนราคา Y→Y+1
  - **Label (classification)** = "ชนะตลาด" = ผลตอบแทนเหนือค่ามัธยฐานของหุ้นทั้งหมดในปีนั้น
    (ตัดผล market-wide ออก ทำให้โมเดลเรียนรู้การ "เลือกหุ้นเด่น" จริงๆ)

ทุกหุ้นสร้างได้หลายแถว (1 แถว = 1 หุ้น-ปี) ตามแนว panel data ของ Quant fund

ฟังก์ชันหลัก:
  build_dataset()           -> DataFrame (ใช้ตอนเทรน)
  build_feature_row(symbol) -> ฟีเจอร์ปีล่าสุด (ใช้ตอนพยากรณ์)
  feature_columns(df)       -> รายชื่อคอลัมน์ฟีเจอร์ (ตัด id/label ออก)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

import pandas as pd

from . import config
from .data_loader import list_symbols, load_statements
from .feature_engineering import engineer_symbol

# คอลัมน์ที่ไม่ใช่ฟีเจอร์ (id + เป้าหมาย)
NON_FEATURE_COLS = {"Stock Symbol", "Year", "fwd_return", "label", "fwd_year"}


def _price(prices: dict, year: str):
    try:
        v = float(prices.get(year))
        return v if not (math.isnan(v) or math.isinf(v)) else None
    except (TypeError, ValueError):
        return None


def feature_columns(df: pd.DataFrame) -> List[str]:
    """คอลัมน์ฟีเจอร์ = ทุกคอลัมน์ตัวเลขที่ไม่ใช่ id/label"""
    return [c for c in df.columns if c not in NON_FEATURE_COLS]


def build_dataset() -> pd.DataFrame:
    """
    สร้าง panel dataset ของทุกหุ้น-ปีที่มีฟีเจอร์ + ราคา Y และ Y+1 ครบ
    คอลัมน์: Stock Symbol, Year, <~85 features>, fwd_return, label
    """
    rows: List[Dict[str, Any]] = []

    for symbol in list_symbols():
        try:
            feats, years = engineer_symbol(symbol)
            _, _, _, basic = load_statements(symbol)
            prices = basic.get("Prices", {}) or {}
        except Exception as e:
            print(f"⚠️ ข้าม {symbol}: {e}")
            continue

        for y in years:
            ny = str(int(y) + 1)
            p0, p1 = _price(prices, y), _price(prices, ny)
            if p0 is None or p1 is None or p0 <= 0:
                continue
            row = {"Stock Symbol": symbol, "Year": int(y)}
            row.update(feats[y])
            row["fwd_return"] = p1 / p0 - 1.0
            rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("สร้างชุดข้อมูลไม่ได้ — ตรวจว่ามีงบและราคาใน data/")

    # ---- Label "ชนะตลาด": เทียบกับมัธยฐานผลตอบแทนของหุ้นทั้งหมดในปีเดียวกัน ----
    median_by_year = df.groupby("Year")["fwd_return"].transform("median")
    df["label"] = (df["fwd_return"] > median_by_year).astype(int)

    return df


def build_feature_row(symbol: str) -> Dict[str, Any]:
    """ฟีเจอร์ของปีล่าสุดที่มีข้อมูลครบ (ใช้พยากรณ์)"""
    feats, years = engineer_symbol(symbol)
    if not years:
        raise RuntimeError(f"สร้างฟีเจอร์ของ {symbol} ไม่ได้")
    latest = years[-1]
    row = {"Stock Symbol": symbol.upper(), "Year": int(latest)}
    row.update(feats[latest])
    return row
