"""
trainer.py — เทรนโมเดล AI (LightGBM) จากฟีเจอร์ ~85 ตัว
=========================================================

เทรน 2 โมเดล:
  1) **Regressor**  — ทำนายผลตอบแทน 1 ปีข้างหน้า (LGBMRegressor)
  2) **Classifier** — ตีตรา "ชนะตลาด/แพ้ตลาด" (LGBMClassifier)

LightGBM รองรับค่า NaN ในตัว (ไม่ต้อง impute) เหมาะกับฟีเจอร์การเงินที่บางช่อง
ขาดหายเป็นปกติ ประเมินผลแบบ GroupKFold (group = หุ้น) กันข้อมูลรั่วข้ามบริษัท

บันทึกที่ artifacts/ai/:
  return_model.joblib, valuation_classifier.joblib,
  feature_metadata.json, metrics.json
"""
from __future__ import annotations

import os
import json
from typing import Any, Dict

import numpy as np
import pandas as pd
import joblib

from lightgbm import LGBMRegressor, LGBMClassifier
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.metrics import (
    mean_absolute_error, r2_score,
    accuracy_score, f1_score, roc_auc_score,
)

from .. import config
from ..features import build_dataset, feature_columns

RANDOM_STATE = 42


def _regressor() -> LGBMRegressor:
    return LGBMRegressor(
        n_estimators=500, learning_rate=0.03, num_leaves=31,
        min_child_samples=20, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.8, reg_lambda=1.0,
        random_state=RANDOM_STATE, n_jobs=-1, verbose=-1,
    )


def _classifier() -> LGBMClassifier:
    return LGBMClassifier(
        n_estimators=500, learning_rate=0.03, num_leaves=31,
        min_child_samples=20, subsample=0.8, subsample_freq=1,
        colsample_bytree=0.8, reg_lambda=1.0,
        random_state=RANDOM_STATE, n_jobs=-1, verbose=-1,
    )


def _cv_evaluate(df: pd.DataFrame, X: pd.DataFrame) -> Dict[str, Any]:
    groups = df["Stock Symbol"].values
    n_splits = max(2, min(5, df["Stock Symbol"].nunique()))
    gkf = GroupKFold(n_splits=n_splits)
    metrics: Dict[str, Any] = {"cv_folds": n_splits}

    # Regressor
    y_reg = df["fwd_return"].values
    reg_pred = cross_val_predict(_regressor(), X, y_reg, groups=groups, cv=gkf)
    metrics["regression"] = {
        "mae": round(float(mean_absolute_error(y_reg, reg_pred)), 4),
        "r2": round(float(r2_score(y_reg, reg_pred)), 4),
        "baseline_mae_mean": round(float(mean_absolute_error(y_reg, np.full_like(y_reg, y_reg.mean()))), 4),
    }

    # Classifier
    y_cls = df["label"].values
    if len(np.unique(y_cls)) < 2:
        metrics["classification"] = {"note": "มีคลาสเดียว ข้ามการประเมิน"}
    else:
        cls_pred = cross_val_predict(_classifier(), X, y_cls, groups=groups, cv=gkf)
        cls_proba = cross_val_predict(_classifier(), X, y_cls, groups=groups, cv=gkf, method="predict_proba")[:, 1]
        metrics["classification"] = {
            "accuracy": round(float(accuracy_score(y_cls, cls_pred)), 4),
            "f1": round(float(f1_score(y_cls, cls_pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_cls, cls_proba)), 4),
            "positive_rate": round(float(y_cls.mean()), 4),
        }
    return metrics


def train(verbose: bool = True) -> Dict[str, Any]:
    """เทรนโมเดลทั้งหมด + ประเมินผล + บันทึกลง artifacts/ai/"""
    os.makedirs(config.ARTIFACT_DIR, exist_ok=True)

    df = build_dataset()
    feat_cols = feature_columns(df)
    X = df[feat_cols]

    if verbose:
        print(f"📊 ชุดข้อมูล: {len(df)} แถว / {df['Stock Symbol'].nunique()} หุ้น | "
              f"{len(feat_cols)} ฟีเจอร์ (LightGBM)")

    metrics = _cv_evaluate(df, X)

    # เทรนจริงด้วยข้อมูลทั้งหมด
    reg = _regressor().fit(X, df["fwd_return"].values)
    has_two = df["label"].nunique() >= 2
    cls = _classifier().fit(X, df["label"].values) if has_two else None

    importances = reg.feature_importances_
    importance = dict(sorted(
        {c: int(v) for c, v in zip(feat_cols, importances)}.items(),
        key=lambda kv: kv[1], reverse=True,
    ))

    joblib.dump(reg, config.RETURN_MODEL_PATH)
    if cls is not None:
        joblib.dump(cls, config.CLASS_MODEL_PATH)

    metadata = {
        "feature_columns": feat_cols,
        "n_features": len(feat_cols),
        "n_samples": int(len(df)),
        "n_symbols": int(df["Stock Symbol"].nunique()),
        "model": "LightGBM",
        "label_definition": "outperform_median_that_year",
        "undervalued_threshold": config.UNDERVALUED_THRESHOLD,
        "has_classifier": cls is not None,
    }
    with open(config.METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    summary = {**metadata, "metrics": metrics,
               "feature_importance_top20": dict(list(importance.items())[:20])}
    with open(config.METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if verbose:
        print("✅ เทรนเสร็จ บันทึกที่:", config.ARTIFACT_DIR)
        rm = metrics.get("regression", {})
        print(f"   Regression  MAE={rm.get('mae')} (baseline {rm.get('baseline_mae_mean')}), R²={rm.get('r2')}")
        cm = metrics.get("classification", {})
        if "accuracy" in cm:
            print(f"   Classifier  Acc={cm['accuracy']} F1={cm['f1']} AUC={cm['roc_auc']} (ชนะตลาด {cm['positive_rate']})")
        print("   Top features:", list(importance.items())[:8])

    return summary


if __name__ == "__main__":
    train()
