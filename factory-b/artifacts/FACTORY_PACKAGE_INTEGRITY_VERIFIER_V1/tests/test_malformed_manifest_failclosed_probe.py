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


def test_non_object_manifest_row_returns_fail_receipt_instead_of_raising(tmp_path):
    root = tmp_path / "pkg"
    root.mkdir()
    manifest = {
        "schema_version": "1.0.0",
        "candidate": "MALFORMED-ROW-PROBE",
        "file_count": 1,
        "files": [None],
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")

    receipt = verify_package(root)

    assert receipt["verdict"] == "FAIL"
    assert any("manifest-row-0-not-object" in item for item in receipt["errors"])


def test_nul_manifest_path_returns_fail_receipt_instead_of_raising(tmp_path):
    root = tmp_path / "pkg-nul"
    root.mkdir()
    manifest = {
        "schema_version": "1.0.0",
        "candidate": "NUL-PATH-PROBE",
        "file_count": 1,
        "files": [{"path": "bad\x00name", "sha256": "0" * 64, "size": 0}],
    }
    (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    receipt = verify_package(root)
    assert receipt["verdict"] == "FAIL"
    assert any("control-character-not-allowed" in item for item in receipt["errors"])


def test_windows_drive_prefixed_zip_path_is_rejected(tmp_path):
    payload = b"x"
    manifest = {
        "schema_version": "1.0.0",
        "candidate": "DRIVE-PREFIX-PROBE",
        "file_count": 1,
        "files": [{"path": "C:/x.txt", "sha256": hashlib.sha256(payload).hexdigest(), "size": 1}],
    }
    z = tmp_path / "drive-prefix.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("C:/x.txt", payload)
        f.writestr("MANIFEST.json", json.dumps(manifest))
    receipt = verify_package(z)
    assert receipt["verdict"] == "FAIL"
    assert any("colon-not-allowed" in item for item in receipt["errors"])
