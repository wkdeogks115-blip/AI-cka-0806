#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from factory_b.transfer_system import validate_packet

packet_path=ROOT/'qualification/TRANSFER_QUALIFICATION_001/transfer_packet.json'
packet=json.loads(packet_path.read_text(encoding='utf-8'))
errs=validate_packet(ROOT,packet)
if errs:
    print('TRANSFER_PACKET_INVALID')
    for e in errs: print('-',e)
    raise SystemExit(2)
repo=ROOT/'qualification/HANDOFF_INDEPENDENCE_REHEARSAL_001/repo'
cp=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=repo,text=True,capture_output=True)
print(cp.stdout,end='')
print(cp.stderr,end='')
if cp.returncode==0:
    print('UNEXPECTED: qualification baseline already passes; independent-agent task is no longer a valid unfinished baseline')
    raise SystemExit(3)
expected=['test_basic_spaces','test_trim_and_collapse','test_strip_punctuation']
if not all(name in cp.stdout for name in expected):
    print('UNEXPECTED: baseline failures differ from the frozen qualification expectation')
    raise SystemExit(4)
print('TRANSFER_QUALIFICATION_PREFLIGHT_PASS')
print('packet_hash='+packet['packet_hash'])
print('baseline_status=EXPECTED_FAIL_BEFORE_AGENT')
