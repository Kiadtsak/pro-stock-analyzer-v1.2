"""
predictor.py — โหลดโมเดลที่เทรนแล้ว มาพยากรณ์รายหุ้น
======================================================

ใช้ฟีเจอร์ของ "ปีล่าสุด" ของหุ้นที่ระบุ แล้วคืน:
  - expected_return_1y : ผลตอบแทนคาดการณ์ 1 ปี (regressor)
  - verdict            : ถูก/แพง  (classifier)
  - confidence         : ความมั่นใจของ classifier (ความน่าจะเป็น)
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict

import pandas as pd
import joblib

from .. import config
from ..features import build_feature_row


class ModelNotTrainedError(RuntimeError):
    """ยังไม่ได้เทรนโมเดล — ให้รัน `python -m stockai.cli train` ก่อน"""


@lru_cache(maxsize=1)
def _load_artifacts():
    """โหลดโมเดล + metadata (cache ไว้ เรียกซ้ำไม่ช้า)"""
    if not os.path.exists(config.RETURN_MODEL_PATH) or not os.path.exists(config.METADATA_PATH):
        raise ModelNotTrainedError(
            "ยังไม่มีโมเดล — รัน `python -m stockai.cli train` ก่อน"
        )
    with open(config.METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    reg = joblib.load(config.RETURN_MODEL_PATH)
    cls = joblib.load(config.CLASS_MODEL_PATH) if metadata.get("has_classifier") else None
    return reg, cls, metadata


def predict(symbol: str) -> Dict[str, Any]:
    """พยากรณ์หุ้นหนึ่งตัวจากฟีเจอร์ปีล่าสุด"""
    reg, cls, metadata = _load_artifacts()
    feature_cols = metadata["feature_columns"]

    row = build_feature_row(symbol)
    X = pd.DataFrame([{c: row.get(c) for c in feature_cols}])[feature_cols]

    expected_return = float(reg.predict(X)[0])

    result: Dict[str, Any] = {
        "symbol": symbol.upper(),
        "based_on_year": row.get("Year"),
        "expected_return_1y": round(expected_return, 4),
        "expected_return_1y_pct": f"{expected_return * 100:.1f}%",
    }

    if cls is not None:
        proba = float(cls.predict_proba(X)[0][1])
        verdict = "น่าจะชนะตลาด (Outperform)" if proba >= 0.5 else "น่าจะแพ้ตลาด (Underperform)"
        result.update({
            "verdict": verdict,
            "outperform_probability": round(proba, 4),
            "undervalued_probability": round(proba, 4),  # คงไว้ให้ frontend เดิมใช้ได้
            "confidence": round(max(proba, 1 - proba), 4),
        })
    else:
        verdict = ("น่าจะชนะตลาด (Outperform)"
                   if expected_return > metadata.get("undervalued_threshold", 0.1)
                   else "น่าจะแพ้ตลาด (Underperform)")
        result["verdict"] = verdict

    return result


def predict_all() -> list[Dict[str, Any]]:
    """พยากรณ์ทุกหุ้นที่มีข้อมูล เรียงตามผลตอบแทนคาดการณ์ (มาก→น้อย)"""
    from ..data_loader import list_symbols
    out = []
    for sym in list_symbols():
        try:
            out.append(predict(sym))
        except Exception as e:
            out.append({"symbol": sym, "error": str(e)})
    out.sort(key=lambda r: r.get("expected_return_1y", -999), reverse=True)
    return out
