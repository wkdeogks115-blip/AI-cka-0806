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


def _manifest(files):
    rows=[]
    for path, data in files.items():
        rows.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"size":len(data)})
    return {"schema_version":"1.0.0","candidate":"TEST","file_count":len(rows),"files":rows}


def _write_zip(path: Path, files: dict[str, bytes], manifest=None, extra=None):
    manifest = manifest or _manifest(files)
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items(): z.writestr(name,data)
        z.writestr("MANIFEST.json",json.dumps(manifest))
        for name,data in (extra or {}).items(): z.writestr(name,data)


def test_valid_zip_passes(tmp_path):
    z=tmp_path/"x.zip"; _write_zip(z,{"a.txt":b"a","d/b.txt":b"b"})
    r=verify_package(z)
    assert r["verdict"]=="PASS"
    assert r["verified_files"]==2
    assert r["semantic_correctness"]=="NOT_ASSESSED"


def test_hash_tamper_detected(tmp_path):
    files={"a.txt":b"a"}; m=_manifest(files)
    z=tmp_path/"x.zip"
    _write_zip(z,{"a.txt":b"tampered"},manifest=m)
    r=verify_package(z)
    assert r["verdict"]=="FAIL" and r["hash_mismatches"]==["a.txt"]


def test_missing_and_unexpected_detected(tmp_path):
    files={"a.txt":b"a","b.txt":b"b"}; m=_manifest(files)
    z=tmp_path/"x.zip"; _write_zip(z,{"a.txt":b"a"},manifest=m,extra={"c.txt":b"c"})
    r=verify_package(z)
    assert r["verdict"]=="FAIL"
    assert "b.txt" in r["missing"] and "c.txt" in r["unexpected"]


def test_manifest_traversal_rejected(tmp_path):
    data=b"x"; m={"schema_version":"1.0.0","candidate":"TEST","file_count":1,"files":[{"path":"../x","sha256":hashlib.sha256(data).hexdigest(),"size":1}]}
    z=tmp_path/"x.zip"; _write_zip(z,{},manifest=m)
    r=verify_package(z)
    assert r["verdict"]=="FAIL"
    assert any("unsafe" in e for e in r["errors"])


def test_directory_symlink_rejected(tmp_path):
    root=tmp_path/"p"; root.mkdir(); (root/"a.txt").write_text("a")
    m=_manifest({"a.txt":b"a"}); (root/"MANIFEST.json").write_text(json.dumps(m))
    try: (root/"link").symlink_to(root/"a.txt")
    except OSError: return
    r=verify_package(root)
    assert r["verdict"]=="FAIL" and any("symlink" in x for x in r["unsafe_paths"])


def test_duplicate_manifest_path_detected(tmp_path):
    digest=hashlib.sha256(b"a").hexdigest()
    m={"schema_version":"1.0.0","candidate":"TEST","file_count":2,"files":[
      {"path":"a.txt","sha256":digest,"size":1},{"path":"a.txt","sha256":digest,"size":1}]}
    z=tmp_path/"x.zip"; _write_zip(z,{"a.txt":b"a"},manifest=m)
    r=verify_package(z)
    assert r["verdict"]=="FAIL"
    assert any("duplicate" in e for e in r["errors"])


def test_single_wrapper_root_zip_passes(tmp_path):
    files={"a.txt":b"a"}; m=_manifest(files)
    z=tmp_path/"x.zip"
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED) as f:
        f.writestr("wrapper/a.txt",b"a")
        f.writestr("wrapper/MANIFEST.json",json.dumps(m))
    r=verify_package(z)
    assert r["verdict"]=="PASS"
    assert r["verified_files"]==1


def test_manifest_anchor_passes(tmp_path):
    files={"a.txt":b"a"}; m=_manifest(files)
    manifest_bytes=json.dumps(m).encode()
    z=tmp_path/"x.zip"
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED) as f:
        f.writestr("a.txt",b"a")
        f.writestr("MANIFEST.json",manifest_bytes)
    expected=hashlib.sha256(manifest_bytes).hexdigest()
    r=verify_package(z,expected_manifest_sha256=expected)
    assert r["verdict"]=="PASS"
    assert r["integrity_scope"]=="ANCHORED_MANIFEST"
    assert r["manifest_hash_match"] is True


def test_coordinated_payload_and_manifest_tamper_detected_with_anchor(tmp_path):
    original_files={"a.txt":b"original"}; original_manifest=_manifest(original_files)
    original_manifest_bytes=json.dumps(original_manifest).encode()
    expected=hashlib.sha256(original_manifest_bytes).hexdigest()
    tampered=b"tampered"
    tampered_manifest=_manifest({"a.txt":tampered})
    z=tmp_path/"coordinated.zip"
    with zipfile.ZipFile(z,"w",zipfile.ZIP_DEFLATED) as f:
        f.writestr("a.txt",tampered)
        f.writestr("MANIFEST.json",json.dumps(tampered_manifest).encode())
    unanchored=verify_package(z)
    assert unanchored["verdict"]=="PASS"
    assert unanchored["integrity_scope"]=="SELF_CONSISTENCY_ONLY"
    anchored=verify_package(z,expected_manifest_sha256=expected)
    assert anchored["verdict"]=="FAIL"
    assert anchored["manifest_hash_match"] is False
    assert "manifest-sha256-mismatch" in anchored["errors"]


def test_invalid_manifest_anchor_rejected(tmp_path):
    z=tmp_path/"x.zip"; _write_zip(z,{"a.txt":b"a"})
    r=verify_package(z,expected_manifest_sha256="not-a-sha")
    assert r["verdict"]=="FAIL"
    assert "expected-manifest-sha256-invalid" in r["errors"]
