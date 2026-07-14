"""
api.py — FastAPI เปิดระบบเป็นบริการเว็บ
========================================

รัน:
  uvicorn stockai.api:app --reload --port 8000

Endpoints:
  GET  /health                 — เช็คสถานะ
  GET  /symbols                — รายชื่อหุ้นที่มีข้อมูล
  GET  /predict/{symbol}       — พยากรณ์ผลตอบแทน 1 ปี + ถูก/แพง
  GET  /predict                — พยากรณ์ทุกหุ้น เรียงตามผลตอบแทน
  GET  /analyze/{symbol}       — ratio + valuation + AI ครบชุด
  POST /train                  — เทรนโมเดลใหม่จากข้อมูลล่าสุด
  GET  /metrics                — ผลประเมินโมเดลล่าสุด (จากการเทรน)
"""
from __future__ import annotations

import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, __version__
from .data_loader import list_symbols
from .pipeline import analyze as analyze_symbol

app = FastAPI(title="StockAI Valuation API", version=__version__)

# เปิด CORS ให้ frontend (Next.js) เรียกได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/symbols")
def symbols():
    return {"symbols": list_symbols()}


@app.get("/predict/{symbol}")
def predict_one(symbol: str):
    from .ai.predictor import predict, ModelNotTrainedError
    try:
        return predict(symbol)
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/predict")
def predict_all_route():
    from .ai.predictor import predict_all, ModelNotTrainedError
    try:
        return {"predictions": predict_all()}
    except ModelNotTrainedError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/analyze/{symbol}")
def analyze_route(symbol: str, ai: bool = True):
    try:
        return analyze_symbol(symbol, with_ai=ai)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/train")
def train_route():
    from .ai.trainer import train
    try:
        return train(verbose=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
def metrics_route():
    if not os.path.exists(config.METRICS_PATH):
        raise HTTPException(status_code=404, detail="ยังไม่มี metrics — เทรนโมเดลก่อน")
    with open(config.METRICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
