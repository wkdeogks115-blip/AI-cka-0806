from pathlib import Path
import json, hashlib, os, subprocess, sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from path_scope import validate_changed_paths

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

def github_changed_files():
    if os.environ.get('GITHUB_EVENT_NAME') != 'pull_request':
        return None
    head_ref=os.environ.get('GITHUB_HEAD_REF','')
    base_ref=os.environ.get('GITHUB_BASE_REF','')
    if not head_ref.startswith('factory-b-'):
        raise SystemExit('unexpected Factory candidate branch:'+head_ref)
    if not base_ref:
        raise SystemExit('missing GITHUB_BASE_REF')
    cp=subprocess.run(['git','diff','--name-only','--diff-filter=ACMRTUXB',f'origin/{base_ref}...HEAD'],text=True,capture_output=True)
    if cp.returncode!=0:
        raise SystemExit('changed-file diff unavailable:'+cp.stderr.strip())
    return [line for line in cp.stdout.splitlines() if line.strip()]

changed=github_changed_files()
if changed is not None:
    scope=validate_changed_paths(changed)
    if not scope['ok']:
        raise SystemExit('path scope violation:'+','.join(scope['violations']))
    if not scope['changed']:
        raise SystemExit('empty changed-file set')
print('FACTORY_B_REPO_CANDIDATE_CHECK_PASS')
