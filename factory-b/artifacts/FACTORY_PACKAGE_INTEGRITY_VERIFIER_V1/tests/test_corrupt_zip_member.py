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


def test_corrupt_zip_member_returns_machine_readable_fail_receipt(tmp_path):
    payload = b"CRC_SENTINEL_ABC123"
    manifest = {
        "schema_version": "1.0.0",
        "candidate": "CORRUPT-ZIP-NEGATIVE",
        "file_count": 1,
        "files": [
            {
                "path": "a.txt",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size": len(payload),
            }
        ],
    }
    z = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(z, "w", compression=zipfile.ZIP_STORED) as f:
        f.writestr("a.txt", payload)
        f.writestr("MANIFEST.json", json.dumps(manifest))

    raw = z.read_bytes()
    assert raw.count(payload) == 1
    damaged = payload[:-1] + (b"X" if payload[-1:] != b"X" else b"Y")
    z.write_bytes(raw.replace(payload, damaged, 1))

    receipt = verify_package(z)
    assert receipt["verdict"] == "FAIL"
    assert any(item.startswith("zip-member-read-error:a.txt:") for item in receipt["errors"])
