from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

MOD_PATH = Path(__file__).resolve().parents[1] / "src" / "package_integrity.py"
spec = importlib.util.spec_from_file_location("package_integrity", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)
verify_package = mod.verify_package


def _write_directory_manifest(root: Path, manifest: object) -> None:
    root.mkdir()
    (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")


def _write_zip_manifest(path: Path, manifest: object, payloads: dict[str, bytes] | None = None) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in (payloads or {}).items():
            zf.writestr(name, data)
        zf.writestr("MANIFEST.json", json.dumps(manifest))


def test_zip_non_object_manifest_row_fails_closed(tmp_path):
    z = tmp_path / "bad-row.zip"
    _write_zip_manifest(z, {"schema_version":"1.0.0","candidate":"ZIP-BAD-ROW","file_count":1,"files":[None]})
    receipt = verify_package(z)
    assert receipt["verdict"] == "FAIL"
    assert any("manifest-row-0-not-object" in item for item in receipt["errors"])


def test_directory_empty_object_manifest_row_fails_closed(tmp_path):
    root = tmp_path / "empty-object"
    _write_directory_manifest(root, {"schema_version":"1.0.0","candidate":"DIR-EMPTY-ROW","file_count":1,"files":[{}]})
    receipt = verify_package(root)
    assert receipt["verdict"] == "FAIL"
    assert any("manifest-row-0-unsafe-path" in item for item in receipt["errors"])


def test_zip_string_manifest_row_fails_closed(tmp_path):
    z = tmp_path / "string-row.zip"
    _write_zip_manifest(z, {"schema_version":"1.0.0","candidate":"ZIP-STRING-ROW","file_count":1,"files":["a.txt"]})
    receipt = verify_package(z)
    assert receipt["verdict"] == "FAIL"
    assert any("manifest-row-0-not-object" in item for item in receipt["errors"])


def test_mixed_valid_and_non_object_rows_preserve_fail_verdict(tmp_path):
    payload = b"a"
    digest = hashlib.sha256(payload).hexdigest()
    root = tmp_path / "mixed"
    root.mkdir()
    (root / "a.txt").write_bytes(payload)
    manifest = {
        "schema_version":"1.0.0",
        "candidate":"MIXED",
        "file_count":2,
        "files":[{"path":"a.txt","sha256":digest,"size":1}, None],
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    receipt = verify_package(root)
    assert receipt["verdict"] == "FAIL"
    assert receipt["verified_files"] == 1
    assert any("manifest-row-1-not-object" in item for item in receipt["errors"])
