"""
backend/app.py — FastAPI application.

Serves the ratio analysis engine + static frontend.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend import (
    CATEGORY_LABELS,
    REGISTRY,
    analyze_financials,
    list_available_symbols,
    load_financials,
    validate_data,
)
from backend.config import FRONTEND_DIR, HOST, PORT
from backend.loader import load_or_fetch
from backend.cache_manager import cleanup_old_files, cache_status
from backend.narrator import deep_analyze

app = FastAPI(
    title="Pro Stock Analyzer",
    description="Professional financial ratio analysis — 200+ formulas across 18 categories",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# API endpoints
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# Cache lifecycle — startup cleanup + management endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def _startup_cache_cleanup():
    """ลบไฟล์ cache ที่เกิน 30 วัน ทุกครั้งที่ server start."""
    report = cleanup_old_files()
    if report["deleted"]:
        print(f"🗑  Startup cleanup: deleted {len(report['deleted'])} stale files")


@app.get("/api/cache/status")
async def get_cache_status():
    """ดูสถานะ cache — ไฟล์ไหนสด ไฟล์ไหนใกล้หมดอายุ."""
    return cache_status()


@app.post("/api/cache/cleanup")
async def run_cache_cleanup(dry_run: bool = False):
    """สั่งลบไฟล์เก่าเกิน 30 วันทันที (dry_run=true เพื่อดูก่อนไม่ลบจริง)."""
    return cleanup_old_files(dry_run=dry_run)


@app.get("/api/health")
async def health():
    return {"status": "ok", "categories": len(REGISTRY)}


@app.get("/api/categories")
async def get_categories():
    """List all 18 ratio categories with EN/TH labels."""
    return {
        "count": len(REGISTRY),
        "categories": [
            {
                "id": name,
                "class": cls.__name__,
                "description": cls.description,
                "label_en": CATEGORY_LABELS[name][0],
                "label_th": CATEGORY_LABELS[name][1],
            }
            for name, cls in REGISTRY.items()
        ],
    }


@app.get("/api/symbols")
async def get_symbols():
    """List all cached symbols."""
    symbols = list_available_symbols()
    return {"count": len(symbols), "symbols": symbols}


@app.get("/api/analyze/{symbol}")
async def analyze(
    symbol: str,
    categories: str | None = Query(None, description="Comma-separated category IDs. None = all"),
):
    """Full analysis for a symbol."""
    try:
        data = load_or_fetch(symbol)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    valid, warnings = validate_data(data)
    cat_list = None
    if categories:
        cat_list = [c.strip() for c in categories.split(",") if c.strip()]
        # Validate
        invalid = [c for c in cat_list if c not in REGISTRY]
        if invalid:
            raise HTTPException(400, f"Unknown categories: {invalid}")

    try:
        result = analyze_financials(data, categories=cat_list)
        # Convert dataclass to dict for JSON
        return _result_to_dict(result, warnings)
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")


@app.get("/api/analyze/{symbol}/category/{category}")
async def analyze_single_category(symbol: str, category: str):
    """Get ratios for one category across all years."""
    if category not in REGISTRY:
        raise HTTPException(400, f"Unknown category: {category}")

    try:
        data = load_or_fetch(symbol)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    result = analyze_financials(data, categories=[category])

    return {
        "symbol": symbol.upper(),
        "category": category,
        "label_en": CATEGORY_LABELS[category][0],
        "label_th": CATEGORY_LABELS[category][1],
        "years": {
            y: yr.categories.get(category, {})
            for y, yr in result.years.items()
        },
    }


@app.get("/api/analyze/{symbol}/deep")
async def analyze_deep(symbol: str):
    """
    Full 12-section deep analysis using 80-100 of the 200+ ratios.
    Returns structured sections + rendered markdown (TH + EN).
    """
    try:
        data = load_or_fetch(symbol)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    try:
        result = analyze_financials(data)
        deep = deep_analyze(result)
        return deep
    except Exception as e:
        raise HTTPException(500, f"Deep analysis failed: {e}")


@app.get("/api/analyze/{symbol}/summary")
async def analyze_summary(symbol: str):
    """Just the scorecard + signal + narrative (fast)."""
    try:
        data = load_or_fetch(symbol)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    result = analyze_financials(data)

    return {
        "symbol": result.symbol,
        "name": result.name,
        "sector": result.sector,
        "industry": result.industry,
        "current_price": result.current_price,
        "latest_year": result.latest_year,
        "signal": result.signal,
        "signal_th": result.signal_th,
        "composite_score": result.composite_score,
        "sub_scores": result.sub_scores,
        "narrative_en": result.narrative_en,
        "narrative_th": result.narrative_th,
        "total_ratios": result.total_ratios,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════════════════

def _result_to_dict(r, warnings=None) -> dict:
    return {
        "symbol": r.symbol,
        "name": r.name,
        "sector": r.sector,
        "industry": r.industry,
        "current_price": r.current_price,
        "latest_year": r.latest_year,
        "signal": r.signal,
        "signal_th": r.signal_th,
        "composite_score": r.composite_score,
        "sub_scores": r.sub_scores,
        "narrative_en": r.narrative_en,
        "narrative_th": r.narrative_th,
        "total_ratios": r.total_ratios,
        "categories_computed": r.categories_computed,
        "years": {
            y: {
                "year": yr.year,
                "ratio_count": yr.ratio_count,
                "categories": yr.categories,
            }
            for y, yr in r.years.items()
        },
        "latest_by_category": r.latest_by_category,
        "warnings": r.warnings + (warnings or []),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Frontend (static)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Serve the dashboard."""
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {
        "service": "Pro Stock Analyzer",
        "api_docs": "/docs",
        "endpoints": ["/api/health", "/api/categories", "/api/symbols",
                     "/api/analyze/{symbol}"],
    }


# Mount static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host=HOST, port=PORT, reload=True)
