#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from factory_b.transfer_system import freeze_packet, validate_packet


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--input', required=True, help='JSON packet draft without packet_hash')
    ap.add_argument('--output', required=True)
    args=ap.parse_args()
    draft=json.loads(Path(args.input).read_text(encoding='utf-8'))
    frozen=freeze_packet(draft)
    errors=validate_packet(ROOT, frozen)
    if errors:
        print('\n'.join(errors), file=sys.stderr); return 2
    Path(args.output).write_text(json.dumps(frozen, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f"FROZEN {frozen['task_id']} {frozen['packet_hash']}")
    return 0
if __name__=='__main__': raise SystemExit(main())
