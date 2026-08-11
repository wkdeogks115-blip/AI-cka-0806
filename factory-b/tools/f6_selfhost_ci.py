#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
Q=ROOT/'qualification/F6_SELF_HOST_001'
ART=ROOT/'artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1'
IGNORE_DIRS={'__pycache__','.pytest_cache','.git'}
IGNORE_SUFFIX={'.pyc','.pyo'}

def tree_hash(root: Path) -> str:
    rows=[]
    for p in sorted(root.rglob('*'), key=lambda x:x.as_posix()):
        rel=p.relative_to(root)
        if any(part in IGNORE_DIRS for part in rel.parts) or not p.is_file() or p.suffix in IGNORE_SUFFIX: continue
        h=hashlib.sha256(p.read_bytes()).hexdigest(); rows.append((rel.as_posix(),h))
    out=hashlib.sha256()
    for rel,h in rows:
        out.update(rel.encode()); out.update(b'\0'); out.update(h.encode()); out.update(b'\n')
    return out.hexdigest()

h=tree_hash(ART)
for name in ['WORK_ORDER.json','ARTIFACT_CONTRACT.json','RELEASE_CONTRACT.json']:
    obj=json.loads((Q/name).read_text(encoding='utf-8'))
    if obj.get('candidate_hash')!=h: raise SystemExit(f'{name} candidate_hash mismatch')
rc=json.loads((Q/'RELEASE_CONTRACT.json').read_text(encoding='utf-8'))
if rc.get('target')!='GITHUB_PR' or rc.get('approval_state')!='SCOPED_APPROVED' or rc.get('independent_approval')!='PENDING' or rc.get('read_back_required') is not True:
    raise SystemExit('release contract does not preserve F6 candidate-only approval boundary')
print('F6_GITHUB_CI_PREFLIGHT_PASS')
print('artifact_hash='+h)
print('independent_review=PENDING')
