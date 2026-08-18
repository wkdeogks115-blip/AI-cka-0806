from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import threading
from pathlib import Path

MOD_PATH = Path(__file__).resolve().parents[1] / "src" / "package_integrity.py"
spec = importlib.util.spec_from_file_location("package_integrity_toctou", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

PAYLOAD = b"EXPECTED_PAYLOAD_FOR_TOCTOU_PROOF\n"


def _write_manifest(root: Path, rel: str) -> str:
    m = {"schema_version":"1.0.0","candidate":"TOCTOU-REGRESSION","file_count":1,"files":[{"path":rel,"sha256":hashlib.sha256(PAYLOAD).hexdigest(),"size":len(PAYLOAD)}]}
    b = json.dumps(m, sort_keys=True).encode()
    (root / "MANIFEST.json").write_bytes(b)
    return hashlib.sha256(b).hexdigest()


def test_parent_directory_swap_to_symlink_cannot_escape_root(tmp_path):
    root = tmp_path / "pkg"; root.mkdir(); (root / "payload").mkdir(); (root / "payload" / "a.txt").write_bytes(PAYLOAD)
    outside = tmp_path / "outside"; outside.mkdir(); (outside / "a.txt").write_bytes(PAYLOAD)
    anchor = _write_manifest(root, "payload/a.txt")
    after_check = threading.Event(); swapped = threading.Event(); safe_open_done = threading.Event(); restored = threading.Event()
    original_issue = mod._directory_member_path_issue
    original_safe_read = mod._read_regular_relative_fd

    def issue_wrapper(r, rr, rel):
        result = original_issue(r, rr, rel)
        if rel == "payload/a.txt" and result is None:
            after_check.set(); assert swapped.wait(2)
        return result

    def safe_read_wrapper(root_fd, rel):
        result = original_safe_read(root_fd, rel)
        if rel == "payload/a.txt":
            safe_open_done.set(); assert restored.wait(2)
        return result

    def attacker():
        assert after_check.wait(2)
        os.rename(root / "payload", root / "payload.real")
        os.symlink(outside, root / "payload", target_is_directory=True)
        swapped.set()
        assert safe_open_done.wait(2)
        os.unlink(root / "payload")
        os.rename(root / "payload.real", root / "payload")
        restored.set()

    t = threading.Thread(target=attacker, daemon=True); t.start()
    mod._directory_member_path_issue = issue_wrapper; mod._read_regular_relative_fd = safe_read_wrapper
    try:
        receipt = mod.verify_directory(root, anchor)
    finally:
        mod._directory_member_path_issue = original_issue; mod._read_regular_relative_fd = original_safe_read; t.join(2)
    assert receipt["verdict"] == "FAIL"
    assert receipt["verified_files"] == 0
    assert any("safe-open" in x for x in receipt["unsafe_paths"])


def test_leaf_file_swap_to_symlink_cannot_escape_root(tmp_path):
    root = tmp_path / "pkg"; root.mkdir(); target = root / "a.txt"; target.write_bytes(PAYLOAD)
    outside = tmp_path / "outside.txt"; outside.write_bytes(PAYLOAD)
    anchor = _write_manifest(root, "a.txt")
    after_isfile = threading.Event(); swapped = threading.Event(); safe_open_done = threading.Event(); restored = threading.Event()
    original_isfile = Path.is_file
    original_safe_read = mod._read_regular_relative_fd

    def isfile_wrapper(self: Path):
        result = original_isfile(self)
        if self == target and result:
            after_isfile.set(); assert swapped.wait(2)
        return result

    def safe_read_wrapper(root_fd, rel):
        result = original_safe_read(root_fd, rel)
        if rel == "a.txt":
            safe_open_done.set(); assert restored.wait(2)
        return result

    def attacker():
        assert after_isfile.wait(2)
        os.rename(target, root / "a.real")
        os.symlink(outside, target)
        swapped.set()
        assert safe_open_done.wait(2)
        os.unlink(target)
        os.rename(root / "a.real", target)
        restored.set()

    t = threading.Thread(target=attacker, daemon=True); t.start()
    Path.is_file = isfile_wrapper; mod._read_regular_relative_fd = safe_read_wrapper
    try:
        receipt = mod.verify_directory(root, anchor)
    finally:
        Path.is_file = original_isfile; mod._read_regular_relative_fd = original_safe_read; t.join(2)
    assert receipt["verdict"] == "FAIL"
    assert receipt["verified_files"] == 0
    assert any("safe-open" in x for x in receipt["unsafe_paths"])
