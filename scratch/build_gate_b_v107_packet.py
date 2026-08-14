from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

REPO = "wkdeogks115-blip/AI-cka-0806"
PR = 22
BASE_BRANCH = "review/f6-2-major-001-v1-0-3"
HEAD_BRANCH = "review/f6-2-failclosed-hardening-v1-0-5"
BASE_SHA = "212ae0e6b6375d68c81261c08f6b27bc0dab07e8"
HEAD_SHA = "1b542817bf2bd23309b8da69231c5656fc23a37a"
ARTIFACT_SHA256 = "e151c0b328c7c26f3fb57db89bb21cbb255215c056003f20bc9283737b2e6d51"
CI_RUN_ID = 31769013367
CI_JOB_ID = 94670811638
CI_TESTS = "23/23 PASS"

CHANGED = [
    "factory-b/artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1/README.md",
    "factory-b/artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1/src/package_integrity.py",
    "factory-b/artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1/tests/test_failclosed_manifest_path_regressions.py",
    "factory-b/artifacts/FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1/tests/test_malformed_manifest_failclosed_probe.py",
    "factory-b/qualification/F6_SELF_HOST_001/ARTIFACT_CONTRACT.json",
    "factory-b/qualification/F6_SELF_HOST_001/RELEASE_CONTRACT.json",
    "factory-b/qualification/F6_SELF_HOST_001/WORK_ORDER.json",
]

ROOT = Path("gate_b_v107_packet")
ZIP_PATH = Path("GATE_B_CLEAN_REVIEW_PACKET_V1_0_7.zip")


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


subprocess.check_call(["git", "fetch", "--no-tags", "origin", BASE_BRANCH, HEAD_BRANCH])
base_actual = run("git", "rev-parse", f"origin/{BASE_BRANCH}")
head_actual = run("git", "rev-parse", f"origin/{HEAD_BRANCH}")
assert base_actual == BASE_SHA, (base_actual, BASE_SHA)
assert head_actual == HEAD_SHA, (head_actual, HEAD_SHA)
actual_changed = run("git", "diff", "--name-only", BASE_SHA, HEAD_SHA).splitlines()
assert actual_changed == CHANGED, {"actual": actual_changed, "expected": CHANGED}

if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir()

identity = {
    "repository": REPO,
    "pr": PR,
    "state_at_freeze": "OPEN_DRAFT_UNMERGED_REVALIDATED_BEFORE_PACKET_BUILD",
    "base_branch": BASE_BRANCH,
    "base_sha": BASE_SHA,
    "head_branch": HEAD_BRANCH,
    "head_sha": HEAD_SHA,
    "changed_files": CHANGED,
    "changed_file_count": len(CHANGED),
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "candidate": "FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1 v1.0.7-patch-candidate",
    "packet_purpose": "TRUE_CLEAN_INDEPENDENT_REREVIEW_INPUT_ONLY",
    "finality": "CANDIDATE_ONLY",
}
write("01_TARGET_IDENTITY.json", json.dumps(identity, indent=2, ensure_ascii=False) + "\n")

ci = {
    "evidence_label": "ACTUAL_EXACT_HEAD_GITHUB_CI_REFERENCE",
    "run_id": CI_RUN_ID,
    "job_id": CI_JOB_ID,
    "head_sha": HEAD_SHA,
    "checkout_sha_assertion": "PASS",
    "artifact_tests": CI_TESTS,
    "selfhost_marker": "F6_GITHUB_CI_PREFLIGHT_PASS",
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "artifact_hash_match": True,
    "independent_review": "PENDING_REREVIEW",
    "note": "Technical CI is factual evidence, not independent approval.",
}
write("02_CI_EVIDENCE_REFERENCE.json", json.dumps(ci, indent=2) + "\n")

patch_provenance = {
    "evidence_label": "FACTUAL_PATCH_PROVENANCE_NOT_PRIOR_VERDICT_AUTHORITY",
    "prior_exact_head": "a8b73b0b2cb13cc0bbbb9bbbb4bf4b4414ed8d66",
    "prior_artifact_sha256": "c0996266aca5fe0f9b685b395a896346cf18c09be343ca1ae90bcd854fd61581",
    "reproduced_defect": {
        "class": "explicit Unix ZIP non-regular member metadata accepted as regular payload",
        "facts": [
            "manifest-declared FIFO metadata member could return PASS when bytes/hash/size matched",
            "manifest-declared character-device metadata member could return PASS when bytes/hash/size matched",
            "manifest-declared block-device metadata member could return PASS when bytes/hash/size matched",
            "manifest-declared socket metadata member could return PASS when bytes/hash/size matched",
            "directory type metadata on a non-directory-form member could return PASS",
            "symlink metadata was already rejected"
        ]
    },
    "current_patch": {
        "rule": "when Unix type bits are explicit, accept payload only for S_IFREG; accept structural directory only when info.is_dir() and S_IFDIR; reject symlink and all other explicit non-regular types",
        "compatibility": "type bits == 0 remains allowed for common ZIP producers subject to all other checks",
        "regression_vectors": [
            "FIFO declared member -> FAIL",
            "character-device declared member -> FAIL",
            "block-device declared member -> FAIL",
            "socket declared member -> FAIL",
            "directory metadata without directory-form filename -> FAIL",
            "regular Unix member -> PASS",
            "absent Unix type bits member -> PASS"
        ]
    },
    "review_instruction": "Reproduce and evaluate independently. Do not treat prior severity or verdict as authority."
}
write("02A_PATCH_PROVENANCE_FACTS.json", json.dumps(patch_provenance, indent=2, ensure_ascii=False) + "\n")

for path in CHANGED:
    try:
        write("source/base/" + path, git_bytes(BASE_SHA, path))
    except subprocess.CalledProcessError:
        write("source/base/" + path + ".ABSENT", b"")
    write("source/head/" + path, git_bytes(HEAD_SHA, path))

diff = subprocess.check_output(["git", "diff", "--full-index", "--binary", BASE_SHA, HEAD_SHA, "--", *CHANGED])
write("03_PR22_EXACT_DIFF.patch", diff)

contract = f"""# TRUE CLEAN INDEPENDENT RE-REVIEW CONTRACT — PR #{PR} v1.0.7

Use ONLY this packet. Do not use prior project chat, memory, Supervisor recommendations, Gate A results, future ORCA/model plans, or unrelated repository history.

Target:
- Repository: {REPO}
- PR: #{PR}
- Base SHA: {BASE_SHA}
- Exact Head SHA: {HEAD_SHA}
- Artifact tree SHA-256: {ARTIFACT_SHA256}

02A_PATCH_PROVENANCE_FACTS.json contains only the minimum defect/patch facts needed to understand the current delta. Reproduce them independently; do not inherit any prior severity or verdict.

Review independently at minimum:
- source identity and exact seven-file scope
- explicit Unix ZIP member-type fail-closed behavior for FIFO, character-device, block-device, socket, symlink, and directory type on non-directory-form names
- regular Unix ZIP member compatibility and compatibility when Unix type bits are absent
- preservation of C0/DEL/C1, malformed/non-object MANIFEST row, scalar, non-canonical, traversal, repeated-slash, colon/Windows-drive/ADS, ZIP directory-entry, symlink and directory-enumeration fail-closed behavior
- regression risk and adequacy of the new special-type tests
- package byte/path/readability/regular-file integrity within artifact contract scope
- artifact hash / Work-Artifact-Release contract binding
- approval and ownership boundaries
- whether a materially simpler/safer implementation exists

Evidence labels must remain ACTUAL / REPORTED / INFERRED / NOT_VERIFIED. CI reference is evidence, not approval.

Return verdict exactly one of:
- PASS_FOR_ACTUAL_EXTERNAL_E2E
- PATCH_REQUIRED
- HOLD
- REJECT

PASS requires unresolved CRITICAL=0 and MAJOR=0. PASS means only eligibility for the next E2E gate; it is not merge/release/ACTIVE/FINAL approval. Do not modify GitHub, source, tests, or contracts.
"""
write("04_INDEPENDENT_REVIEW_CONTRACT.md", contract)

attestation_schema = {
    "type": "object",
    "required": ["prior_project_context_used", "only_provided_packet_used", "prior_recommendation_exposure", "independence_status"],
    "properties": {
        "prior_project_context_used": {"type": "boolean"},
        "only_provided_packet_used": {"type": "boolean"},
        "prior_recommendation_exposure": {"type": "boolean"},
        "independence_status": {"enum": ["ATTESTED", "CONTAMINATED", "NOT_VERIFIED"]}
    }
}
write("05_INDEPENDENCE_ATTESTATION_SCHEMA.json", json.dumps(attestation_schema, indent=2) + "\n")

result_schema = {
    "type": "object",
    "required": ["independence_attestation", "target_identity", "findings", "review_dimensions", "verdict", "unverified_items", "rationale"],
    "properties": {
        "verdict": {"enum": ["PASS_FOR_ACTUAL_EXTERNAL_E2E", "PATCH_REQUIRED", "HOLD", "REJECT"]},
        "findings": {"type": "object", "required": ["CRITICAL", "MAJOR", "MINOR", "COSMETIC"]}
    }
}
write("06_INDEPENDENT_REVIEW_RESULT_SCHEMA.json", json.dumps(result_schema, indent=2) + "\n")

readme = f"""# GATE B CLEAN RE-REVIEW PACKET — PR #22 v1.0.7

Mechanically frozen review input, not a review verdict.

Read order:
1. 01_TARGET_IDENTITY.json
2. 04_INDEPENDENT_REVIEW_CONTRACT.md
3. 02A_PATCH_PROVENANCE_FACTS.json
4. 03_PR22_EXACT_DIFF.patch
5. source/base and source/head exact bytes
6. 02_CI_EVIDENCE_REFERENCE.json
7. schemas 05 and 06
8. MANIFEST.json

Excluded: Gate A output, Supervisor recommendation, accumulated chat, data-layer work, future ORCA/model plans, unrelated history.

Expected exact head: {HEAD_SHA}
Expected artifact hash: {ARTIFACT_SHA256}
Finality: CANDIDATE_ONLY.
"""
write("00_README_FIRST.md", readme)

rows = []
for p in sorted(ROOT.rglob("*")):
    if p.is_file() and p.name != "MANIFEST.json":
        b = p.read_bytes()
        rows.append({"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)})
manifest = {
    "schema_version": "1.0.0",
    "packet": "GATE_B_CLEAN_REVIEW_PACKET_PR22_V1_0_7",
    "repo": REPO,
    "pr": PR,
    "base_sha": BASE_SHA,
    "head_sha": HEAD_SHA,
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "file_count": len(rows),
    "files": rows
}
write("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

if ZIP_PATH.exists():
    ZIP_PATH.unlink()
with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(ROOT.rglob("*")):
        if p.is_file():
            rel = p.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(2026, 8, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

packet_sha = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()
Path("GATE_B_CLEAN_REVIEW_PACKET_V1_0_7.sha256.txt").write_text(packet_sha + "  " + ZIP_PATH.name + "\n", encoding="utf-8")
summary = {
    "status": "READY_FOR_TRUE_CLEAN_INDEPENDENT_REREVIEW",
    "packet": ZIP_PATH.name,
    "packet_sha256": packet_sha,
    "base_sha": BASE_SHA,
    "head_sha": HEAD_SHA,
    "artifact_tree_sha256": ARTIFACT_SHA256,
    "changed_files": len(CHANGED),
    "self_certified_review": False
}
Path("GATE_B_PACKET_BUILD_RESULT_V1_0_7.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
