#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from factory_b.transfer_system import evaluate_receipt


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--packet', required=True)
    ap.add_argument('--receipt', required=True)
    ap.add_argument('--output')
    args=ap.parse_args()
    packet=json.loads(Path(args.packet).read_text(encoding='utf-8'))
    receipt=json.loads(Path(args.receipt).read_text(encoding='utf-8'))
    score=evaluate_receipt(ROOT, packet, receipt)
    text=json.dumps(score, ensure_ascii=False, indent=2)+'\n'
    if args.output: Path(args.output).write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if score['verdict']=='ACCEPT' else 3
if __name__=='__main__': raise SystemExit(main())
