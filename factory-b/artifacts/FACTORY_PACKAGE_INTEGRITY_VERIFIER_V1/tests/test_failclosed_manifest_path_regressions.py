from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import zipfile
from pathlib import Path

import pytest

MOD_PATH = Path(__file__).resolve().parents[1] / "src" / "package_integrity.py"
spec = importlib.util.spec_from_file_location("package_integrity", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)
verify_package = mod.verify_package


def _row(path: str, data: bytes = b"x", size=None):
    return {"path": path, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data) if size is None else size}


def _manifest(rows, **overrides):
    value = {"schema_version": "1.0.0", "candidate": "REGRESSION", "file_count": len(rows), "files": rows}
    value.update(overrides)
    return value


def _write_dir(root: Path, files: dict[str, bytes], manifest: dict):
    root.mkdir()
    for rel, data in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_manifest_scalar_types_fail_closed(tmp_path):
    cases = [
        _manifest([_row("a.txt")], file_count=True),
        _manifest([_row("a.txt", size=True)]),
        _manifest([_row("a.txt")], schema_version=None),
        _manifest([_row("a.txt")], candidate=None),
    ]
    for i, manifest in enumerate(cases):
        root = tmp_path / f"p-{i}"
        _write_dir(root, {"a.txt": b"x"}, manifest)
        assert verify_package(root)["verdict"] == "FAIL"


def test_noncanonical_and_nul_manifest_paths_fail_closed(tmp_path):
    for i, path in enumerate(["./a.txt", "d//a.txt", "C:/a.txt", "a\x00b"]):
        root = tmp_path / f"p-{i}"
        root.mkdir()
        (root / "MANIFEST.json").write_text(json.dumps(_manifest([_row(path)])), encoding="utf-8")
        receipt = verify_package(root)
        assert receipt["verdict"] == "FAIL"


def test_zip_unsafe_directory_entries_fail_closed(tmp_path):
    variants = []
    symlink = zipfile.ZipInfo("linkdir/")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    variants.append((symlink, b"../outside"))
    traversal = zipfile.ZipInfo("../evil/")
    traversal.external_attr = (stat.S_IFDIR | 0o755) << 16
    variants.append((traversal, b""))
    absolute = zipfile.ZipInfo("/abs/")
    absolute.external_attr = (stat.S_IFDIR | 0o755) << 16
    variants.append((absolute, b""))

    for i, (entry, data) in enumerate(variants):
        zpath = tmp_path / f"unsafe-{i}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as zf:
            zf.writestr("a.txt", b"x")
            zf.writestr("MANIFEST.json", json.dumps(_manifest([_row("a.txt")])))
            zf.writestr(entry, data)
        assert verify_package(zpath)["verdict"] == "FAIL"


def test_zip_safe_explicit_directory_entry_still_passes(tmp_path):
    zpath = tmp_path / "safe-dir.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("d/", b"")
        zf.writestr("d/a.txt", b"x")
        zf.writestr("MANIFEST.json", json.dumps(_manifest([_row("d/a.txt")])))
    assert verify_package(zpath)["verdict"] == "PASS"


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root can read chmod-000 directories")
def test_unreadable_unexpected_directory_fails_closed(tmp_path):
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "a.txt").write_bytes(b"x")
    (root / "MANIFEST.json").write_text(json.dumps(_manifest([_row("a.txt")])), encoding="utf-8")
    hidden = root / "hidden"
    hidden.mkdir()
    (hidden / "secret.txt").write_text("secret")
    hidden.chmod(0)
    try:
        receipt = verify_package(root)
    finally:
        hidden.chmod(0o700)
    assert receipt["verdict"] == "FAIL"
    assert any(item.startswith("directory-scan-error:hidden:") for item in receipt["errors"])


def test_control_character_manifest_paths_include_del_and_c1_fail_closed(tmp_path):
    payload = b"x"
    controls = ["\n", "\x7f", "\u0085", "\u009f"]
    for i, control in enumerate(controls):
        name = f"bad{control}name-{i}.txt"

        root = tmp_path / f"pkg-control-{i}"
        _write_dir(root, {name: payload}, _manifest([_row(name, payload)]))
        receipt = verify_package(root)
        assert receipt["verdict"] == "FAIL"
        assert any("control-character-not-allowed" in item for item in receipt["errors"])

        zpath = tmp_path / f"control-{i}.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as zf:
            zf.writestr(name, payload)
            zf.writestr("MANIFEST.json", json.dumps(_manifest([_row(name, payload)])))
        receipt = verify_package(zpath)
        assert receipt["verdict"] == "FAIL"
        assert any("control-character-not-allowed" in item for item in receipt["errors"])


def test_zip_colon_ads_path_fails_closed(tmp_path):
    payload = b"x"
    manifest = _manifest([_row("safe.txt:ads", payload)])
    z = tmp_path / "colon-ads.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("safe.txt:ads", payload)
        f.writestr("MANIFEST.json", json.dumps(manifest))
    receipt = verify_package(z)
    assert receipt["verdict"] == "FAIL"
    assert any("colon-not-allowed" in item for item in receipt["errors"])


def test_zip_nonregular_unix_member_types_fail_closed(tmp_path):
    payload = b"payload"
    special_types = [
        ("fifo", stat.S_IFIFO),
        ("character-device", stat.S_IFCHR),
        ("block-device", stat.S_IFBLK),
        ("socket", stat.S_IFSOCK),
        ("directory-without-slash", stat.S_IFDIR),
    ]
    for label, file_type in special_types:
        zpath = tmp_path / f"special-{label}.zip"
        member = zipfile.ZipInfo("member.bin")
        member.create_system = 3
        member.external_attr = (file_type | 0o600) << 16
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as zf:
            zf.writestr(member, payload)
            zf.writestr("MANIFEST.json", json.dumps(_manifest([_row("member.bin", payload)])))
        receipt = verify_package(zpath)
        assert receipt["verdict"] == "FAIL", label
        assert any("not-regular-file" in item for item in receipt["unsafe_paths"]), (label, receipt)


def test_zip_regular_unix_and_absent_type_bits_remain_compatible(tmp_path):
    payload_regular = b"regular"
    payload_unspecified = b"unspecified"
    zpath = tmp_path / "compatible-types.zip"

    regular = zipfile.ZipInfo("regular.bin")
    regular.create_system = 3
    regular.external_attr = (stat.S_IFREG | 0o600) << 16

    unspecified = zipfile.ZipInfo("unspecified.bin")
    unspecified.create_system = 3
    unspecified.external_attr = 0o600 << 16

    manifest = _manifest([
        _row("regular.bin", payload_regular),
        _row("unspecified.bin", payload_unspecified),
    ])
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr(regular, payload_regular)
        zf.writestr(unspecified, payload_unspecified)
        zf.writestr("MANIFEST.json", json.dumps(manifest))

    receipt = verify_package(zpath)
    assert receipt["verdict"] == "PASS"
    assert receipt["verified_files"] == 2
