from __future__ import annotations

import importlib.util
import json
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
