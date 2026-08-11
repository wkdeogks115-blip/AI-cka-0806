from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

CONTROL_FILES = {"MANIFEST.json", "SHA256SUMS.txt"}
HEX64 = set("0123456789abcdef")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_manifest_path(raw: str) -> tuple[bool, str]:
    if not isinstance(raw, str) or not raw:
        return False, "empty-or-nonstring"
    if "\\" in raw:
        return False, "backslash-not-allowed"
    p = PurePosixPath(raw)
    if p.is_absolute() or raw.startswith("/"):
        return False, "absolute-path"
    if any(part in {"", ".", ".."} for part in p.parts):
        return False, "dot-or-traversal-segment"
    return True, p.as_posix()


def _manifest_rows(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return [], ["manifest-root-not-object"]
    for key in ("schema_version", "candidate", "file_count", "files"):
        if key not in manifest:
            errors.append(f"manifest-missing-key:{key}")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        return [], errors + ["manifest-files-not-array"]
    if manifest.get("file_count") != len(rows):
        errors.append("manifest-file-count-mismatch")
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"manifest-row-{i}-not-object")
            continue
        raw = row.get("path")
        ok, normalized = _safe_manifest_path(raw)
        if not ok:
            errors.append(f"manifest-row-{i}-unsafe-path:{raw!r}:{normalized}")
            continue
        if normalized in seen:
            errors.append(f"manifest-duplicate-path:{normalized}")
        seen.add(normalized)
        digest = row.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in HEX64 for c in digest.lower()):
            errors.append(f"manifest-invalid-sha256:{normalized}")
        size = row.get("size")
        if size is not None and (not isinstance(size, int) or size < 0):
            errors.append(f"manifest-invalid-size:{normalized}")
    return rows, errors


def _base_receipt(subject: Path, mode: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "subject": str(subject),
        "mode": mode,
        "manifest_found": False,
        "manifest_candidate": None,
        "declared_files": 0,
        "verified_files": 0,
        "missing": [],
        "unexpected": [],
        "hash_mismatches": [],
        "size_mismatches": [],
        "unsafe_paths": [],
        "duplicate_paths": [],
        "errors": [],
        "verdict": "FAIL",
        "semantic_correctness": "NOT_ASSESSED",
        "evidence_sufficiency": "NOT_ASSESSED",
        "release_approval": "NOT_ASSESSED",
    }


def _finalize(r: dict[str, Any]) -> dict[str, Any]:
    blocking = (
        r["errors"] or r["missing"] or r["unexpected"] or r["hash_mismatches"]
        or r["size_mismatches"] or r["unsafe_paths"] or r["duplicate_paths"]
        or not r["manifest_found"]
    )
    r["verdict"] = "FAIL" if blocking else "PASS"
    return r


def verify_directory(root: Path) -> dict[str, Any]:
    r = _base_receipt(root, "DIRECTORY")
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        r["errors"].append("MANIFEST.json-not-found")
        return _finalize(r)
    if manifest_path.is_symlink():
        r["unsafe_paths"].append("MANIFEST.json:symlink")
        return _finalize(r)
    r["manifest_found"] = True
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        r["errors"].append(f"manifest-json-error:{type(e).__name__}")
        return _finalize(r)
    r["manifest_candidate"] = manifest.get("candidate") if isinstance(manifest, dict) else None
    rows, errors = _manifest_rows(manifest)
    r["errors"].extend(errors)
    r["declared_files"] = len(rows)
    declared: set[str] = set()
    for row in rows:
        raw = row.get("path")
        ok, rel = _safe_manifest_path(raw)
        if not ok:
            r["unsafe_paths"].append(str(raw))
            continue
        if rel in declared:
            r["duplicate_paths"].append(rel)
            continue
        declared.add(rel)
        p = root / Path(*PurePosixPath(rel).parts)
        if not p.exists():
            r["missing"].append(rel)
            continue
        if p.is_symlink() or not p.is_file():
            r["unsafe_paths"].append(f"{rel}:not-regular-file")
            continue
        try:
            data = p.read_bytes()
        except Exception as e:
            r["errors"].append(f"directory-member-read-error:{rel}:{type(e).__name__}")
            continue
        if _sha256_bytes(data) != str(row.get("sha256", "")).lower():
            r["hash_mismatches"].append(rel)
            continue
        if row.get("size") is not None and len(data) != row["size"]:
            r["size_mismatches"].append(rel)
            continue
        r["verified_files"] += 1
    actual: set[str] = set()
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            r["unsafe_paths"].append(f"{rel}:symlink")
        elif p.is_file() and rel not in CONTROL_FILES:
            actual.add(rel)
    r["unexpected"].extend(sorted(actual - declared))
    return _finalize(r)


def _zip_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def verify_zip(path: Path) -> dict[str, Any]:
    r = _base_receipt(path, "ZIP")
    try:
        zf = zipfile.ZipFile(path)
    except Exception as e:
        r["errors"].append(f"zip-open-error:{type(e).__name__}")
        return _finalize(r)
    with zf:
        infos = zf.infolist()
        names: list[str] = []
        info_by_name: dict[str, zipfile.ZipInfo] = {}
        for info in infos:
            name = info.filename
            if info.is_dir():
                continue
            ok, normalized = _safe_manifest_path(name)
            if not ok:
                r["unsafe_paths"].append(f"{name}:{normalized}")
                continue
            if _zip_is_symlink(info):
                r["unsafe_paths"].append(f"{normalized}:symlink")
            if normalized in info_by_name:
                r["duplicate_paths"].append(normalized)
            else:
                info_by_name[normalized] = info
                names.append(normalized)
        manifest_key = "MANIFEST.json"
        prefix = ""
        if manifest_key not in info_by_name:
            candidates = [n for n in info_by_name if n.endswith("/MANIFEST.json") and n.count("/") == 1]
            if len(candidates) == 1:
                manifest_key = candidates[0]
                prefix = manifest_key[: -len("MANIFEST.json")]
            else:
                r["errors"].append("MANIFEST.json-not-found-or-ambiguous-wrapper-root")
                return _finalize(r)
        r["manifest_found"] = True
        try:
            manifest = json.loads(zf.read(info_by_name[manifest_key]).decode("utf-8"))
        except Exception as e:
            r["errors"].append(f"manifest-json-error:{type(e).__name__}")
            return _finalize(r)
        r["manifest_candidate"] = manifest.get("candidate") if isinstance(manifest, dict) else None
        rows, errors = _manifest_rows(manifest)
        r["errors"].extend(errors)
        r["declared_files"] = len(rows)
        declared: set[str] = set()
        for row in rows:
            raw = row.get("path")
            ok, rel = _safe_manifest_path(raw)
            if not ok:
                r["unsafe_paths"].append(str(raw))
                continue
            if rel in declared:
                r["duplicate_paths"].append(rel)
                continue
            declared.add(rel)
            info = info_by_name.get(prefix + rel)
            if info is None:
                r["missing"].append(rel)
                continue
            if _zip_is_symlink(info):
                r["unsafe_paths"].append(f"{rel}:symlink")
                continue
            try:
                data = zf.read(info)
            except Exception as e:
                r["errors"].append(f"zip-member-read-error:{rel}:{type(e).__name__}")
                continue
            if _sha256_bytes(data) != str(row.get("sha256", "")).lower():
                r["hash_mismatches"].append(rel)
                continue
            if row.get("size") is not None and len(data) != row["size"]:
                r["size_mismatches"].append(rel)
                continue
            r["verified_files"] += 1
        actual: set[str] = set()
        for n in names:
            if prefix:
                if not n.startswith(prefix):
                    r["unexpected"].append(n)
                    continue
                logical = n[len(prefix):]
            else:
                logical = n
            if logical not in CONTROL_FILES:
                actual.add(logical)
        r["unexpected"].extend(sorted(actual - declared))
    return _finalize(r)


def verify_package(subject: str | Path) -> dict[str, Any]:
    p = Path(subject)
    if p.is_dir():
        return verify_directory(p)
    if p.is_file() and zipfile.is_zipfile(p):
        return verify_zip(p)
    r = _base_receipt(p, "UNKNOWN")
    r["errors"].append("subject-must-be-directory-or-zip")
    return _finalize(r)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify Factory package MANIFEST/hash/path integrity only.")
    ap.add_argument("subject")
    ap.add_argument("--pretty", action="store_true")
    ns = ap.parse_args(argv)
    receipt = verify_package(ns.subject)
    print(json.dumps(receipt, ensure_ascii=False, indent=2 if ns.pretty else None, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
