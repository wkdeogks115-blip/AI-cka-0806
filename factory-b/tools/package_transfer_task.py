#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, shutil, tempfile, zipfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from factory_b.transfer_system import validate_packet

TRANSFER_FILES=[
    'transfer/AGENT_ENTRYPOINT.md',
    'transfer/TRANSFER_PROTOCOL.md',
    'transfer/transfer_packet.schema.json',
    'transfer/agent_result_receipt.schema.json',
    'transfer/evaluator_scorecard.schema.json',
]

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--packet',required=True)
    ap.add_argument('--output',required=True)
    args=ap.parse_args()
    packet_path=Path(args.packet)
    if not packet_path.is_absolute(): packet_path=ROOT/packet_path
    packet=json.loads(packet_path.read_text(encoding='utf-8'))
    errs=validate_packet(ROOT,packet)
    if errs:
        print('\n'.join(errs),file=sys.stderr); return 2
    out=Path(args.output)
    if not out.is_absolute(): out=ROOT/out
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='factory_b_transfer_') as td:
        stage=Path(td)/'FACTORY_B_TRANSFER_TASK'
        stage.mkdir()
        files=[]
        def add(src_rel:str,dst_rel:str|None=None):
            src=ROOT/src_rel; dst=stage/(dst_rel or src_rel)
            if not src.exists(): raise FileNotFoundError(src)
            dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
            files.append(dst.relative_to(stage).as_posix())
        for rel in TRANSFER_FILES: add(rel)
        add(packet_path.relative_to(ROOT).as_posix(),'transfer_packet.json')
        qdir=packet_path.parent
        for opt, dst in [('AGENT_START_HERE.md','AGENT_START_HERE.md'),('agent_result_receipt.example.json','RETURN_RECEIPT_EXAMPLE.json')]:
            if (qdir/opt).exists(): add((qdir/opt).relative_to(ROOT).as_posix(),dst)
        for rel in packet['relevant_files']:
            add(rel)
        manifest={
          'schema_version':'1.0.0','task_id':packet['task_id'],'packet_hash':packet['packet_hash'],
          'context_policy':packet['context_policy'],'files':[]
        }
        for rel in sorted(files):
            p=stage/rel; manifest['files'].append({'path':rel,'sha256':sha256_file(p)})
        (stage/'TRANSFER_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file(): z.write(p,p.relative_to(stage.parent).as_posix())
    print(f'CREATED {out} sha256={sha256_file(out)}')
    return 0
if __name__=='__main__': raise SystemExit(main())
