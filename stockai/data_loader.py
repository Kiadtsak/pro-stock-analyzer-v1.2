"""
data_loader.py — โหลดและตรวจสอบงบการเงิน JSON จากโฟลเดอร์ data/
=================================================================

หน้าที่เดียว: อ่านไฟล์ data/{SYMBOL}_financials.json แล้วคืนงบ 4 ชุด
(income, balance, cashflow, basic) แบบที่ส่วนอื่นเอาไปใช้ต่อได้เลย
"""
from __future__ import annotations

import os
import json
import glob
from typing import Any, Dict, List, Tuple

from . import config


def _pick_key(d: Dict[str, Any], candidates: List[str]) -> str | None:
    """หาคีย์แรกที่ตรง (รองรับชื่อสะกดต่างกัน)"""
    for k in candidates:
        if k in d:
            return k
    return None


def list_symbols() -> List[str]:
    """คืนรายชื่อหุ้นทั้งหมดที่มีไฟล์งบใน data/ (เรียงตามตัวอักษร)"""
    pattern = os.path.join(config.DATA_DIR, "*_financials.json")
    symbols = []
    for path in glob.glob(pattern):
        name = os.path.basename(path).replace("_financials.json", "")
        if name and "{" not in name:  # ข้ามไฟล์ template เช่น {symbol}_financials.json
            symbols.append(name.upper())
    return sorted(set(symbols))


def load_symbol(symbol: str) -> Dict[str, Any]:
    """โหลด JSON ดิบของหุ้นหนึ่งตัว"""
    symbol = (symbol or "").upper().strip()
    if not symbol:
        raise ValueError("ต้องระบุสัญลักษณ์หุ้น เช่น NVDA")

    path = os.path.join(config.DATA_DIR, f"{symbol}_financials.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"ไม่พบไฟล์งบการเงิน: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or not data:
        raise ValueError(f"ไฟล์ {path} ว่างเปล่าหรือรูปแบบไม่ถูกต้อง")
    return data


def extract_statements(
    data: Dict[str, Any],
) -> Tuple[dict, dict, dict, dict]:
    """
    แยกงบ 4 ชุดจาก dict ดิบ (ยืดหยุ่นชื่อคีย์)
    คืน: (income, balance, cashflow, basic_info)
    """
    k_is = _pick_key(data, config.KEY_CANDIDATES["income"])
    k_bs = _pick_key(data, config.KEY_CANDIDATES["balance"])
    k_cf = _pick_key(data, config.KEY_CANDIDATES["cashflow"])
    k_basic = _pick_key(data, config.KEY_CANDIDATES["basic"])

    if not (k_is and k_bs and k_cf):
        raise KeyError(
            f"ไม่พบงบครบ 3 ชุด (IS={k_is}, BS={k_bs}, CF={k_cf})"
        )

    income = data.get(k_is, {}) or {}
    balance = data.get(k_bs, {}) or {}
    cashflow = data.get(k_cf, {}) or {}
    basic = data.get(k_basic, {}) or {}
    return income, balance, cashflow, basic


def load_statements(symbol: str) -> Tuple[dict, dict, dict, dict]:
    """ทางลัด: โหลดไฟล์ + แยกงบในขั้นตอนเดียว"""
    return extract_statements(load_symbol(symbol))
