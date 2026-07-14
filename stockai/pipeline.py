"""
pipeline.py — รวมขั้นตอนวิเคราะห์หุ้นหนึ่งตัวให้จบในที่เดียว
=============================================================

โหลดงบ → คำนวณ ratio → export → ประเมินมูลค่า (DCF)
เรียกใช้โมดูลคำนวณเดิมใน Backend/ ที่ทำงานได้อยู่แล้ว
"""
from __future__ import annotations

import os
import json
from typing import Any, Dict, List

import pandas as pd

from . import config
from .data_loader import load_statements

# โมดูลคำนวณเดิม (ผ่านการทดสอบว่าทำงานได้)
from Backend_System.calculater_all import calculate_ratios_by_year
from Backend_System.valuetion_financials import run_valuation_for_symbol


def compute_ratios(symbol: str) -> Dict[str, Dict[str, Any]]:
    """คำนวณ ratio ทุกปีของหุ้นหนึ่งตัว"""
    income, balance, cashflow, basic = load_statements(symbol)
    ratios = calculate_ratios_by_year(income, balance, cashflow, basic)
    if not ratios:
        raise RuntimeError(f"คำนวณ ratio ของ {symbol} ไม่ได้")
    return ratios


def export_ratios(symbol: str, ratios: Dict[str, Dict[str, Any]]) -> str:
    """บันทึก ratio เป็น CSV + JSON ใน expotes/ คืน path ของ JSON"""
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    df = (
        pd.DataFrame.from_dict(ratios, orient="index")
        .sort_index().round(4).reset_index().rename(columns={"index": "Year"})
    )
    df["Stock Symbol"] = symbol.upper()
    front = ["Stock Symbol", "Year"]
    df = df[front + [c for c in df.columns if c not in front]]

    csv_path = os.path.join(config.EXPORT_DIR, "result.csv")
    json_path = os.path.join(config.EXPORT_DIR, "result.json")
    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_json(json_path, orient="records", force_ascii=False, indent=2)
    return json_path


def analyze(symbol: str, with_ai: bool = True) -> Dict[str, Any]:
    """
    วิเคราะห์หุ้นแบบครบวงจร: ratio + valuation (+ AI ถ้ามีโมเดล)
    คืน dict สรุปผลทั้งหมด
    """
    symbol = symbol.upper()
    ratios = compute_ratios(symbol)
    json_path = export_ratios(symbol, ratios)

    out: Dict[str, Any] = {"symbol": symbol, "years": sorted(ratios.keys())}

    # ---- Valuation (DCF) ----
    try:
        out["valuation"] = run_valuation_for_symbol(symbol, export_json_path=json_path)
    except Exception as e:
        out["valuation_error"] = str(e)

    # ---- AI prediction (ถ้าเทรนแล้ว) ----
    if with_ai:
        try:
            from .ai.predictor import predict
            out["ai"] = predict(symbol)
        except Exception as e:
            out["ai_error"] = str(e)

    return out
