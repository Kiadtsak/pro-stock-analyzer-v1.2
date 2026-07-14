"""
harvester.py — ดึงงบการเงินจำนวนมากมาเก็บใน data/ แบบจำกัดอัตรา
================================================================

ดึงงบจาก FinanceToolkit + FMP (ใช้ตัวดึงเดิม Backend.financials_provider)
มาเก็บเป็น data/{SYMBOL}_financials.json โดย **จำกัด 10 ตัว/นาที**
(แต่ละ batch 10 ตัว จะใช้เวลาอย่างน้อย 60 วินาที เพื่อกันชน rate limit ของ API)

ใช้งาน:
    from stockai.harvester import harvest, harvest_and_train
    harvest()                 # ดึงครบ 100 หุ้นในลิสต์มาตรฐาน
    harvest_and_train()       # ดึงเสร็จแล้วเทรน AI ต่อทันที

หรือผ่าน CLI:
    python -m stockai.cli harvest            # ดึง 100 หุ้น
    python -m stockai.cli harvest --train    # ดึงแล้วเทรนต่อ
"""
from __future__ import annotations

import os
import json
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from . import config
from Backend_System.financials_provider import FinancialsStatement

load_dotenv()

# ไฟล์รายชื่อหุ้น (แก้ไฟล์นี้เพื่อเพิ่ม/ลบหุ้น 1 บรรทัด = 1 ตัว, ขึ้นต้น # = คอมเมนต์)
UNIVERSE_FILE = os.path.join(os.path.dirname(__file__), "universe.txt")

# รายชื่อดัชนีหุ้นจาก FMP (ดึงสดจาก API แทนการพิมพ์เอง)
FMP_INDEX_LISTS = {
    "sp500": "https://financialmodelingprep.com/api/v3/sp500_constituent",
    "nasdaq": "https://financialmodelingprep.com/api/v3/nasdaq_constituent",
    "dowjones": "https://financialmodelingprep.com/api/v3/dowjones_constituent",
}


def fetch_symbol_list(sources: str = "sp500", timeout: int = 30) -> List[str]:
    """
    ดึง "รายชื่อหุ้น" จาก FMP โดยตรง (ไม่ต้องพิมพ์เองใน universe.txt)
    sources: ชื่อดัชนีคั่นด้วย comma เช่น "sp500" หรือ "sp500,nasdaq,dowjones"
    คืนรายชื่อ ticker ไม่ซ้ำ (คงลำดับ)
    """
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise EnvironmentError("ไม่พบ API_KEY ใน .env")

    symbols: List[str] = []
    for src in [s.strip().lower() for s in sources.split(",") if s.strip()]:
        url = FMP_INDEX_LISTS.get(src)
        if not url:
            print(f"⚠️ ไม่รู้จักแหล่ง '{src}' (เลือกได้: {', '.join(FMP_INDEX_LISTS)})")
            continue
        try:
            r = requests.get(f"{url}?apikey={api_key}", timeout=timeout)
            r.raise_for_status()
            data = r.json()
            got = [str(x.get("symbol", "")).upper().strip() for x in data if x.get("symbol")]
            symbols.extend(got)
            print(f"📋 {src}: ได้ {len(got)} ตัวจาก API")
        except Exception as e:
            print(f"⚠️ ดึงรายชื่อ '{src}' ไม่สำเร็จ: {e}")
    return list(dict.fromkeys(symbols))

# -------------------------------------------------------------------
# จักรวาลหุ้นมาตรฐาน 100 ตัว (US large-cap ที่ FMP มีข้อมูลครบ)
# -------------------------------------------------------------------
DEFAULT_UNIVERSE: List[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "JPM", "V",
    "MA", "UNH", "HD", "PG", "JNJ", "COST", "ORCL", "ABBV", "BAC", "KO",
    "PEP", "CVX", "WMT", "MRK", "CRM", "AMD", "NFLX", "ADBE", "TMO", "ACN",
    "LIN", "MCD", "ABT", "CSCO", "INTC", "WFC", "DIS", "QCOM", "TXN", "DHR",
    "VZ", "INTU", "AMGN", "CMCSA", "PFE", "NKE", "PM", "UNP", "IBM", "HON",
    "GE", "CAT", "COP", "LOW", "SPGI", "NOW", "BA", "GS", "ELV", "RTX",
    "AMAT", "BKNG", "DE", "BLK", "SBUX", "MDT", "LMT", "ADP", "GILD", "ISRG",
    "MU", "ADI", "REGN", "VRTX", "C", "MMC", "TJX", "SCHW", "ZTS", "MO",
    "BSX", "PGR", "CB", "SO", "DUK", "PLTR", "TSM", "BMY", "UPS", "PYPL",
    "MS", "AXP", "ETN", "SLB", "KLAC", "PANW", "LRCX", "SNPS", "CDNS", "MAR",
]

# -------------------------------------------------------------------
# จักรวาลชุดที่ 2 — อีก 100 หุ้น (ไม่ซ้ำกับชุดที่ 1)
# semis / cloud / fintech / China ADR / autos / energy / materials / industrials
# -------------------------------------------------------------------
UNIVERSE_2: List[str] = [
    # Semiconductors
    "MRVL", "MCHP", "NXPI", "ON", "TER", "SWKS", "QRVO", "MPWR",
    # Software / Cloud / Security
    "ANET", "FTNT", "ZS", "DDOG", "NET", "CRWD", "SNOW", "TEAM", "WDAY", "OKTA", "TWLO", "HUBS",
    # Internet / Consumer apps
    "DASH", "ABNB", "UBER", "RBLX", "U", "PINS", "SNAP", "SPOT", "ROKU", "TTD", "DOCU", "ZM",
    # Fintech / Payments
    "SQ", "SHOP", "NU", "SOFI", "HOOD", "COIN", "AFRM", "UPST", "MELI", "SE",
    # China ADRs
    "BABA", "BIDU", "NTES", "TCOM", "JD", "PDD", "NIO", "LI", "XPEV",
    # Autos
    "RIVN", "LCID", "F", "GM", "STLA", "HMC", "TM",
    # International pharma / software ADR
    "NVO", "AZN", "SNY", "GSK", "NVS", "SAP",
    # Energy
    "SHEL", "BP", "TTE", "ENB", "EOG", "PSX", "VLO", "MPC", "OXY", "KMI", "WMB", "HAL",
    "BKR", "DVN", "FANG",
    # Materials
    "FCX", "NEM", "NUE", "DOW", "DD", "APD", "SHW", "ECL",
    # Industrials
    "EMR", "ITW", "PH", "GD", "NOC", "TDG", "CSX", "NSC", "FDX", "WM",
    # Extra
    "GRAB", "CPNG", "EW",
]

# จักรวาลรวมทั้งหมด ~200 หุ้น (เผื่ออยากดึงครบในคราวเดียว)
FULL_UNIVERSE: List[str] = DEFAULT_UNIVERSE + UNIVERSE_2


def load_universe() -> List[str]:
    """
    อ่านรายชื่อหุ้นจาก universe.txt (1 บรรทัด = 1 ตัว, # = คอมเมนต์)
    ถ้าไม่มีไฟล์ ใช้ FULL_UNIVERSE (~200 ตัว) แทน
    คืนรายการที่ไม่ซ้ำ (คงลำดับเดิม)
    """
    if not os.path.exists(UNIVERSE_FILE):
        return list(dict.fromkeys(FULL_UNIVERSE))

    symbols: List[str] = []
    with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip().upper()
            if line:
                symbols.append(line)
    return list(dict.fromkeys(symbols)) or list(dict.fromkeys(FULL_UNIVERSE))


def _data_path(symbol: str) -> str:
    return os.path.join(config.DATA_DIR, f"{symbol.upper()}_financials.json")


def _latest_year(symbol: str) -> Optional[int]:
    """อ่านปีงบล่าสุดของหุ้นจากไฟล์ (ใช้ตัดสินว่าข้อมูลเก่าหรือยัง)"""
    path = _data_path(symbol)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        years = [int(y) for y in (d.get("Income Statement", {}) or {}) if str(y).isdigit()]
        return max(years) if years else None
    except Exception:
        return None


def is_stale(symbol: str, min_year: int) -> bool:
    """ข้อมูลเก่า = ปีงบล่าสุดน้อยกว่า min_year (ควรดึงใหม่เพื่ออัปเดต)"""
    latest = _latest_year(symbol)
    return latest is None or latest < min_year


def fetch_one(symbol: str, force: bool = False) -> Dict[str, Any]:
    """
    ดึงหุ้นหนึ่งตัวมาเก็บใน data/ คืน dict สรุปผล
    {symbol, status: ok|skipped|error, message}
    """
    symbol = symbol.upper().strip()
    path = _data_path(symbol)

    if os.path.exists(path) and not force:
        return {"symbol": symbol, "status": "skipped", "message": "มีไฟล์อยู่แล้ว"}

    try:
        fs = FinancialsStatement(symbol=symbol, data_dir=config.DATA_DIR)
        data = fs.load_data_json_or_api(force=True)  # ดึง + บันทึกลงไฟล์
        if not data:
            return {"symbol": symbol, "status": "error", "message": "API คืนข้อมูลว่าง"}
        return {"symbol": symbol, "status": "ok", "message": "ดึงสำเร็จ"}
    except Exception as e:
        return {"symbol": symbol, "status": "error", "message": str(e)}


def harvest(
    symbols: Optional[List[str]] = None,
    source: Optional[str] = None,
    batch_size: int = 10,
    per_batch_seconds: int = 60,
    force: bool = False,
    update: bool = False,
    min_year: Optional[int] = None,
    dry_run: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    ดึงงบเป็น batch ละ `batch_size` ตัว โดยแต่ละ batch ใช้เวลาอย่างน้อย
    `per_batch_seconds` วินาที (ดีฟอลต์ = 10 ตัว/นาที)

    การตัดสินใจต่อหุ้น:
      - ไม่มีไฟล์            -> ดึงใหม่
      - มีไฟล์ + force       -> ดึงทับ (รีเฟรชทุกตัว)
      - มีไฟล์ + update      -> ดึงทับเฉพาะตัวที่ "งบเก่า" (ปีล่าสุด < min_year)
      - มีไฟล์ (อื่นๆ)        -> ข้าม

    ลำดับการเลือกรายชื่อหุ้น:
      1) `symbols` ที่ส่งเข้ามาตรงๆ
      2) `source` -> ดึงรายชื่อสดจาก FMP (เช่น "sp500") โดยไม่ต้องพิมพ์เอง
      3) universe.txt
    จากนั้น **ข้ามตัวที่มีใน data/ แล้ว ดึงเฉพาะตัวที่ยังไม่มี**

    คืน dict สรุป: {ok, skipped, updated, errors}
    """
    if symbols is None:
        symbols = fetch_symbol_list(source) if source else load_universe()
    symbols = list(dict.fromkeys(s.upper().strip() for s in symbols))
    total = len(symbols)

    if min_year is None:
        # ดีฟอลต์ = ปีก่อนหน้า: ถือว่าข้อมูลทันสมัยถ้ามีงบของปีที่แล้ว
        # (งบประจำปีมักออกหลังสิ้นปีไม่กี่เดือน) — เลี่ยงดึงซ้ำโดยไม่จำเป็น
        min_year = time.localtime().tm_year - 1

    ok: List[str] = []
    skipped: List[str] = []
    updated: List[str] = []
    errors: List[Dict[str, str]] = []

    # โหมด dry-run: บอกว่าจะดึง/ข้ามตัวไหน แต่ไม่โหลดจริง (ไม่เปลือง API)
    if dry_run:
        to_fetch, to_skip = [], []
        for sym in symbols:
            exists = os.path.exists(_data_path(sym))
            is_update = bool(exists and not force and update and is_stale(sym, min_year))
            will_fetch = force or is_update or not exists
            (to_fetch if will_fetch else to_skip).append(sym)
        if verbose:
            print(f"🔎 DRY-RUN (ยังไม่โหลดจริง): จาก {total} ตัว "
                  f"-> จะดึง {len(to_fetch)}, ข้าม {len(to_skip)}")
            if to_fetch:
                preview = ", ".join(to_fetch[:50]) + (" ..." if len(to_fetch) > 50 else "")
                print(f"   จะดึง: {preview}")
        return {
            "dry_run": True, "total": total,
            "to_fetch": to_fetch, "to_skip": to_skip,
            "n_to_fetch": len(to_fetch), "n_to_skip": len(to_skip),
        }

    if verbose:
        mode = "force (ทับทุกตัว)" if force else ("update (ทับเฉพาะงบเก่า)" if update else "ปกติ (ข้ามตัวที่มี)")
        print(f"🌾 เริ่มดึง {total} หุ้น | โหมด: {mode}"
              + (f" | อัปเดตถ้าปีล่าสุด < {min_year}" if update else "")
              + f"\n   (batch ละ {batch_size} ตัว, อย่างน้อย {per_batch_seconds} วิ/batch)")

    # หน่วงเวลา "เฉพาะการดึงจริง" — ตัวที่ถูกข้ามไม่นับ ไม่เสียเวลารอฟรี
    fetch_idx = 0            # ลำดับของการดึงจริง (0-based)
    window_start = 0.0       # เวลาเริ่มของ batch การดึงปัจจุบัน
    for i, sym in enumerate(symbols):
        exists = os.path.exists(_data_path(sym))
        is_update = bool(exists and not force and update and is_stale(sym, min_year))
        do_force = force or is_update
        will_fetch = do_force or not exists  # ตรงกับเงื่อนไขใน fetch_one

        # ก่อนเริ่มดึงของ batch ใหม่ (ตัวที่ 10, 20, ...) ให้หน่วงให้ครบเวลา
        if will_fetch:
            if fetch_idx > 0 and fetch_idx % batch_size == 0:
                elapsed = time.monotonic() - window_start
                wait = per_batch_seconds - elapsed
                if wait > 0:
                    if verbose:
                        print(f"   ⏳ ดึงครบ {batch_size} ตัว — รอ {wait:.0f} วิ กัน rate limit...")
                    time.sleep(wait)
            if fetch_idx % batch_size == 0:
                window_start = time.monotonic()
            fetch_idx += 1

        res = fetch_one(sym, force=do_force)
        if res["status"] == "ok" and is_update:
            res["message"] = "อัปเดตงบใหม่"
        status = res["status"]
        if status == "ok":
            ok.append(sym)
            if is_update:
                updated.append(sym)
        elif status == "skipped":
            skipped.append(sym)
        else:
            errors.append({"symbol": sym, "message": res["message"]})

        if verbose and status != "skipped":
            icon = {"ok": "✅", "error": "❌"}[status]
            print(f"   {icon} [{fetch_idx}] {sym}: {res['message'][:80]}")

    summary = {
        "total": total,
        "ok": ok,
        "skipped": skipped,
        "updated": updated,
        "errors": errors,
        "n_ok": len(ok),
        "n_skipped": len(skipped),
        "n_updated": len(updated),
        "n_errors": len(errors),
    }
    if verbose:
        print(f"\n🌾 ดึงเสร็จ: สำเร็จ {len(ok)} (ในนั้นอัปเดต {len(updated)}), "
              f"ข้าม {len(skipped)}, ผิดพลาด {len(errors)}")
        if updated:
            print("   อัปเดตงบใหม่:", ", ".join(updated))
        if errors:
            print("   หุ้นที่ผิดพลาด:", ", ".join(e["symbol"] for e in errors))
    return summary


def harvest_and_train(
    symbols: Optional[List[str]] = None,
    force: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """ดึงงบครบแล้วเทรนโมเดล AI ต่อทันที"""
    harvest_summary = harvest(symbols=symbols, force=force, **kwargs)

    # dry-run = แค่ดูว่าจะดึงอะไร ไม่ต้องเทรน
    if harvest_summary.get("dry_run"):
        print("\n(โหมด dry-run: ข้ามการเทรน)")
        return {"harvest": harvest_summary, "train": None}

    print("\n🧠 เริ่มเทรนโมเดล AI จากข้อมูลที่ดึงมาทั้งหมด...")
    from .ai.trainer import train
    train_summary = train(verbose=True)

    return {"harvest": harvest_summary, "train": train_summary}


if __name__ == "__main__":
    harvest_and_train()
