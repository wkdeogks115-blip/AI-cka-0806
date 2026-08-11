from pathlib import Path
import json, hashlib
root=Path(__file__).resolve().parents[1]
required=['AGENTS.md','CODEX_TASK.md','qualification/qualification_handoff.json','qualification/relevant_files/qualification_source.json','contracts/activation_gate.yaml','candidate_manifest.json']
missing=[x for x in required if not (root/x).is_file()]
if missing: raise SystemExit('missing:'+','.join(missing))
h=json.loads((root/'qualification/qualification_handoff.json').read_text(encoding='utf-8'))
rf=h['RELEVANT_FILES'][0]; p=root/'qualification'/rf['reference']
got=hashlib.sha256(p.read_bytes()).hexdigest()
if got!=rf['sha256']: raise SystemExit('qualification source hash mismatch')
if 'previous chat' in h['CURRENT_CONTEXT'].lower(): raise SystemExit('hidden context dependency')
manifest=json.loads((root/'candidate_manifest.json').read_text(encoding='utf-8'))
if manifest.get('active_release') is not False or manifest.get('codex_execution')!='UNVERIFIED': raise SystemExit('evidence boundary violated')
if manifest.get('factory_can_activate') is not False or manifest.get('activation_authority')!='EXTERNAL_ONLY': raise SystemExit('activation ownership violated')
activation=(root/'contracts/activation_gate.yaml').read_text(encoding='utf-8')
for token in ['factory_activation_authority: NONE','factory_max_status: READY_FOR_EXTERNAL_APPROVAL','factory_runtime_returning_ACTIVE']:
    if token not in activation: raise SystemExit('activation contract missing:'+token)
print('FACTORY_B_REPO_CANDIDATE_CHECK_PASS')
