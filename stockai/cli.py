"""
cli.py — คำสั่งใช้งานระบบจากเทอร์มินัล
========================================

ตัวอย่าง:
  python -m stockai.cli list                 # ดูหุ้นที่มีข้อมูล
  python -m stockai.cli train                # เทรนโมเดล AI จากข้อมูลทั้งหมด
  python -m stockai.cli predict NVDA         # พยากรณ์หุ้นเดียว
  python -m stockai.cli predict --all        # พยากรณ์ทุกหุ้น เรียงตามผลตอบแทน
  python -m stockai.cli analyze NVDA         # ratio + valuation + AI ครบชุด
"""
from __future__ import annotations

import sys
import json
import argparse
import pandas as pd 



def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stockai", description="ระบบประเมินมูลค่าหุ้นด้วย AI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="แสดงหุ้นทั้งหมดที่มีข้อมูลใน data/")
    sub.add_parser("train", help="เทรนโมเดล AI จากงบการเงิน + ราคาจริง")

    p_harvest = sub.add_parser("harvest", help="ดึงงบหุ้นมาเก็บใน data/ (10 ตัว/นาที)")
    p_harvest.add_argument(
        "--symbols", "-s",
        help='ระบุหุ้นเองคั่นด้วย comma เช่น "AMZN,GOOGL,KO" (ว่าง = อ่านจาก universe.txt)',
    )
    p_harvest.add_argument(
        "--source",
        help='ดึงรายชื่อหุ้นสดจาก API: sp500 / nasdaq / dowjones (คั่น comma ได้) '
             'เช่น "sp500" — ดึงเฉพาะตัวที่ยังไม่มีใน data',
    )
    p_harvest.add_argument("--train", action="store_true", help="ดึงเสร็จแล้วเทรน AI ต่อ")
    p_harvest.add_argument("--force", action="store_true", help="ดึงใหม่ทับทุกตัว (รีเฟรชทั้งหมด)")
    p_harvest.add_argument("--update", action="store_true",
                           help="ดึงทับเฉพาะตัวที่งบเก่า (ปีล่าสุด < min-year)")
    p_harvest.add_argument("--min-year", type=int, default=None,
                           help="เกณฑ์ปีงบล่าสุดสำหรับ --update (ดีฟอลต์ = ปีปัจจุบัน−1)")
    p_harvest.add_argument("--dry-run", action="store_true",
                           help="ดูว่าจะดึง/ข้ามตัวไหน แต่ไม่โหลดจริง (ไม่เปลือง API ไม่เทรน)")
    p_harvest.add_argument("--batch-size", type=int, default=10, help="จำนวนหุ้นต่อ batch")
    p_harvest.add_argument("--batch-seconds", type=int, default=60, help="วินาทีขั้นต่ำต่อ batch")

    p_pred = sub.add_parser("predict", help="พยากรณ์ผลตอบแทน/ถูกแพง")
    p_pred.add_argument("symbol", nargs="?", help="เช่น NVDA")
    p_pred.add_argument("--all", action="store_true", help="พยากรณ์ทุกหุ้น")

    p_an = sub.add_parser("analyze", help="วิเคราะห์ครบ: ratio + valuation + AI")
    p_an.add_argument("symbol", help="เช่น NVDA")
    p_an.add_argument("--no-ai", action="store_true", help="ข้ามส่วน AI")

    args = parser.parse_args(argv)

    if args.command == "list":
        from .data_loader import list_symbols
        symbols = list_symbols()
        print(f"พบ {len(symbols)} หุ้น:", ", ".join(symbols))
        return 0

    if args.command == "train":
        from .ai.trainer import train
        train(verbose=True)
        return 0

    if args.command == "harvest":
        from .harvester import harvest, harvest_and_train
        symbols = None
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        kwargs = dict(
            symbols=symbols,
            source=args.source,
            force=args.force,
            update=args.update,
            min_year=args.min_year,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            per_batch_seconds=args.batch_seconds,
        )
        if args.train:
            harvest_and_train(**kwargs)
        else:
            harvest(**kwargs)
        return 0

    if args.command == "predict":
        from .ai.predictor import predict, predict_all
        if args.all:
            _print(predict_all())
        elif args.symbol:
            _print(predict(args.symbol))
        else:
            print("ต้องระบุ symbol หรือใช้ --all", file=sys.stderr)
            return 1
        return 0

    if args.command == "analyze":
        from .pipeline import analyze
        _print(analyze(args.symbol, with_ai=not args.no_ai))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
