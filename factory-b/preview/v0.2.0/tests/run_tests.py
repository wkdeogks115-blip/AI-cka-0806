from pathlib import Path
import json, subprocess, sys, re
ROOT=Path(__file__).resolve().parents[1]
results=[]
def check(name, ok, detail=""):
    results.append({"name":name,"pass":bool(ok),"detail":detail})
src=(ROOT/"run_preview.py").read_text(encoding="utf-8")+(ROOT/"preview_engine.py").read_text(encoding="utf-8")
check("no_external_factory_zip_runtime_dependency","zipfile.ZipFile" not in src)
p=subprocess.run([sys.executable,"-B",str(ROOT/"run_preview.py"),str(ROOT/"examples/01_skill_idea.json")],cwd=ROOT,text=True,capture_output=True)
check("sample_exit",p.returncode==0,p.stderr)
o=json.loads(p.stdout)
check("sample_type",o.get("artifact_type",{}).get("artifact_type")=="SKILL")
check("sample_assetization",o.get("assetization",{}).get("action")=="CREATE_SKILL")
check("preview_boundary",o.get("active_release") is False and o.get("activation_evidence") is False and o.get("final_approval")=="UNVERIFIED")
snap=json.loads((ROOT/"CURRENT_SNAPSHOT.json").read_text(encoding="utf-8"))
check("snapshot_proof_gate",snap.get("factory_b",{}).get("proof_gate","").endswith("/issues/15"))
check("snapshot_preactive",snap.get("factory_b",{}).get("active_v1")=="PREACTIVE")
html=(ROOT/"START_HERE.html").read_text(encoding="utf-8")
check("html_offline",not re.search(r'<script[^>]+src=',html,re.I) and "fetch(" not in html and "XMLHttpRequest" not in html)
refs=json.loads((ROOT/"SOURCE_REFERENCES.json").read_text(encoding="utf-8"))
check("answer_pack_not_merged",refs["answer_pack"]["runtime_merged"] is False)
out={"passed":sum(x["pass"] for x in results),"total":len(results),"failed":sum(not x["pass"] for x in results),"results":results}
print(json.dumps(out,ensure_ascii=False,indent=2))
if out["failed"]: raise SystemExit(1)
