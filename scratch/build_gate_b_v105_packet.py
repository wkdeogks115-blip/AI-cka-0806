from __future__ import annotations

import hashlib
import json
import os
import subprocess
import zipfile
from pathlib import Path

REPO = "wkdeogks115-blip/AI-cka-0806"
PR = 20
BASE_BRANCH = "review/f6-2-major-001-v1-0-3"
HEAD_BRANCH = "review/f6-2-malformed-row-v1-0-4"
BASE_SHA = "212ae0e6b6375d68c81261c08f6b27bc0dab07e8"
HEAD_SHA = "2ca249b17d23d0dd0b64dc4d55b941123ae72e02"
ARTIFACT_SHA256 = "90d9ce035c9345e34410db74549f40e25479a8afc31d36eddbad486c6f91a556"
CI_RUN_ID = 31682332461
CI_JOB_ID = 94390388713
CI_TESTS = "16/16 PASS"

CHANGED = [
    "factory-b/artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1/README.md",
    "factory-b/artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1/src/package_integrity.py",
    "factory-b/artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1/tests/test_malformed_manifest_failclosed_probe.py",
    "factory-b/qualification/F6_SELF_HOST_001/ARTIFACT_CONTRACT.json",
    "factory-b/qualification/F6_SELF_HOST_001/RELEASE_CONTRACT.json",
    "factory-b/qualification/F6_SELF_HOST_001/WORK_ORDER.json",
]

ROOT = Path("gate_b_v105_packet")
ZIP_PATH = Path("GATE_B_CLEAN_REVIEW_PACKET_V1_0_5.zip")


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def write(rel: str, data: str | bytes) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8", newline="\n")


def git_bytes(sha: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{sha}:{path}"])


# Source identity assertions.
subprocess.check_call(["git", "fetch", "--no-tags", "origin", BASE_BRANCH, HEAD_BRANCH])
base_actual = run("git", "rev-parse", f"origin/{BASE_BRANCH}")
head_actual = run("git", "rev-parse", f"origin/{HEAD_BRANCH}")
assert base_actual == BASE_SHA, (base_actual, BASE_SHA)
assert head_actual == HEAD_SHA, (head_actual, HEAD_SHA)
actual_changed = run("git", "diff", "--name-only", BASE_SHA, HEAD_SHA).splitlines()
assert actual_changed == CHANGED, {"actual": actual_changed, "expected": CHANGED}

if ROOT.exists():
    import shutil
    shutil.rmtree(ROOT)
ROOT.mkdir()

identity = {
    "repository": REPO,
    "pr": PR,
    "state_at_freeze": "OPEN_DRAFT_UNMERGED_REVALIDATED_BY_SUPERVISOR_BEFORE_PACKET_BUILD",
    "base_branch": BASE_BRANCH,
    "base_sha": BASE_SHA,
    "head_branch": HEAD_BRANCH,
    "head_sha": HEAD_SHA,
    "changed_files": CHANGED,
    "changed_file_count": len(CHANGED),
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "candidate": "FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1 v1.0.5-patch-candidate",
    "packet_purpose": "TRUE_CLEAN_INDEPENDENT_REVIEW_INPUT_ONLY",
    "finality": "CANDIDATE_ONLY",
}
write("01_TARGET_IDENTITY.json", json.dumps(identity, indent=2, ensure_ascii=False) + "\n")

ci = {
    "evidence_label": "ACTUAL_GITHUB_CI_REFERENCE",
    "run_id": CI_RUN_ID,
    "job_id": CI_JOB_ID,
    "head_sha": HEAD_SHA,
    "artifact_tests": CI_TESTS,
    "selfhost_marker": "F6_GITHUB_CI_PREFLIGHT_PASS",
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "independent_review": "PENDING",
    "note": "Reviewer must not treat CI PASS as automatic independent approval.",
}
write("02_CI_EVIDENCE_REFERENCE.json", json.dumps(ci, indent=2) + "\n")

# Exact source bytes for all six changed files at base and head.
for path in CHANGED:
    try:
        write("source/base/" + path, git_bytes(BASE_SHA, path))
    except subprocess.CalledProcessError:
        write("source/base/" + path + ".ABSENT", b"")
    write("source/head/" + path, git_bytes(HEAD_SHA, path))

# Exact bounded diff.
diff = subprocess.check_output(
    ["git", "diff", "--full-index", "--binary", BASE_SHA, HEAD_SHA, "--", *CHANGED]
)
write("03_PR20_EXACT_DIFF.patch", diff)

contract = f"""# TRUE CLEAN INDEPENDENT REVIEW CONTRACT — PR #{PR} v1.0.5\n\nUse ONLY this packet. Do not use prior project chat, memory, Supervisor recommendations, Gate A results, future ORCA/model plans, or unrelated repository history.\n\nTarget:\n- Repository: {REPO}\n- PR: #{PR}\n- Base SHA: {BASE_SHA}\n- Exact Head SHA: {HEAD_SHA}\n- Artifact tree SHA-256: {ARTIFACT_SHA256}\n\nReview independently at minimum:\n- source identity and six-file scope\n- malformed/non-object MANIFEST files[] fail-closed behavior\n- embedded NUL/control-character path fail-closed behavior\n- colon/Windows drive-prefix path rejection in directory/ZIP-relevant paths\n- package/path integrity and unsafe path edge cases within artifact contract scope\n- regression risk of the minimal path guards\n- tests covering the patched failure modes\n- artifact hash / Work-Artifact-Release contract binding\n- approval boundary and ownership boundary\n- whether a materially simpler/safer implementation exists\n\nEvidence labels must remain ACTUAL / REPORTED / INFERRED / NOT_VERIFIED.\nCI reference is evidence, not approval.\n\nReturn verdict exactly one of:\n- PASS_FOR_ACTUAL_EXTERNAL_E2E\n- PATCH_REQUIRED\n- HOLD\n- REJECT\n\nPASS requires unresolved CRITICAL=0 and MAJOR=0.\nPASS means only eligibility for the next E2E gate; it is not merge/release/ACTIVE/FINAL approval.\nDo not modify GitHub, source, tests, or contracts.\n"""
write("04_INDEPENDENT_REVIEW_CONTRACT.md", contract)

attestation_schema = {
    "type": "object",
    "required": ["prior_project_context_used", "only_provided_packet_used", "prior_recommendation_exposure", "independence_status"],
    "properties": {
        "prior_project_context_used": {"type": "boolean"},
        "only_provided_packet_used": {"type": "boolean"},
        "prior_recommendation_exposure": {"type": "boolean"},
        "independence_status": {"enum": ["ATTESTED", "CONTAMINATED", "NOT_VERIFIED"]},
    },
}
write("05_INDEPENDENCE_ATTESTATION_SCHEMA.json", json.dumps(attestation_schema, indent=2) + "\n")

result_schema = {
    "type": "object",
    "required": ["independence_attestation", "target_identity", "findings", "review_dimensions", "verdict", "unverified_items", "rationale"],
    "properties": {
        "verdict": {"enum": ["PASS_FOR_ACTUAL_EXTERNAL_E2E", "PATCH_REQUIRED", "HOLD", "REJECT"]},
        "findings": {
            "type": "object",
            "required": ["CRITICAL", "MAJOR", "MINOR", "COSMETIC"],
        },
    },
}
write("06_INDEPENDENT_REVIEW_RESULT_SCHEMA.json", json.dumps(result_schema, indent=2) + "\n")

readme = f"""# GATE B CLEAN REVIEW PACKET — v1.0.5\n\nThis is a mechanically frozen review packet, not a review verdict.\n\nRead order:\n1. 01_TARGET_IDENTITY.json\n2. 04_INDEPENDENT_REVIEW_CONTRACT.md\n3. 03_PR20_EXACT_DIFF.patch\n4. source/base and source/head exact bytes\n5. 02_CI_EVIDENCE_REFERENCE.json\n6. schemas 05 and 06\n7. MANIFEST.json\n\nThe packet intentionally excludes Gate A output, Supervisor recommendation, accumulated chat, data-layer simulation, future ORCA/model plans, and unrelated repository history.\n\nExpected exact head: {HEAD_SHA}\nExpected artifact hash: {ARTIFACT_SHA256}\nFinality: CANDIDATE_ONLY.\n"""
write("00_README_FIRST.md", readme)

# Manifest excluding itself first.
rows = []
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.name != "MANIFEST.json":
        b = p.read_bytes()
        rows.append({
            "path": p.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(b).hexdigest(),
            "size": len(b),
        })
manifest = {
    "schema_version": "1.0.0",
    "packet": "GATE_B_CLEAN_REVIEW_PACKET_V1_0_5",
    "repo": REPO,
    "pr": PR,
    "base_sha": BASE_SHA,
    "head_sha": HEAD_SHA,
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "file_count": len(rows),
    "files": rows,
}
write("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

# Deterministic inner ZIP.
if ZIP_PATH.exists():
    ZIP_PATH.unlink()
with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        info = zipfile.ZipInfo(rel, date_time=(2026, 8, 13, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

packet_sha = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()
Path("GATE_B_CLEAN_REVIEW_PACKET_V1_0_5.sha256.txt").write_text(packet_sha + "  " + ZIP_PATH.name + "\n", encoding="utf-8")
summary = {
    "status": "READY_FOR_TRUE_CLEAN_INDEPENDENT_REVIEW",
    "packet": ZIP_PATH.name,
    "packet_sha256": packet_sha,
    "base_sha": BASE_SHA,
    "head_sha": HEAD_SHA,
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "changed_files": len(CHANGED),
    "self_certified_review": False,
}
Path("GATE_B_PACKET_BUILD_RESULT.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
