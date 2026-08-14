from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    if any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in raw):
        return False, "control-character-not-allowed"
    if "\\" in raw:
        return False, "backslash-not-allowed"
    if ":" in raw:
        return False, "colon-not-allowed"
    if raw.startswith("/"):
        return False, "absolute-path"
    raw_parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        return False, "dot-or-traversal-segment"
    p = PurePosixPath(raw)
    if p.is_absolute():
        return False, "absolute-path"
    return True, p.as_posix()


def _manifest_rows(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return [], ["manifest-root-not-object"]
    for key in ("schema_version", "candidate", "file_count", "files"):
        if key not in manifest:
            errors.append(f"manifest-missing-key:{key}")
    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        errors.append("manifest-schema-version-invalid")
    candidate = manifest.get("candidate")
    if not isinstance(candidate, str) or not candidate:
        errors.append("manifest-candidate-invalid")
    file_count = manifest.get("file_count")
    if not isinstance(file_count, int) or isinstance(file_count, bool) or file_count < 0:
        errors.append("manifest-file-count-invalid")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        return [], errors + ["manifest-files-not-array"]
    if isinstance(file_count, int) and not isinstance(file_count, bool) and file_count >= 0 and file_count != len(rows):
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
        if size is not None and (not isinstance(size, int) or isinstance(size, bool) or size < 0):
            errors.append(f"manifest-invalid-size:{normalized}")
    return rows, errors


def _valid_sha256_hex(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in HEX64 for c in value.lower())


def _base_receipt(subject: Path, mode: str, expected_manifest_sha256: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "subject": str(subject),
        "mode": mode,
        "manifest_found": False,
        "manifest_candidate": None,
        "manifest_sha256": None,
        "expected_manifest_sha256": expected_manifest_sha256,
        "manifest_hash_match": None,
        "integrity_scope": "ANCHORED_MANIFEST" if expected_manifest_sha256 else "SELF_CONSISTENCY_ONLY",
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


def _directory_member_path_issue(root: Path, root_resolved: Path, rel: str) -> str | None:
    """Return an unsafe-path reason before directory member bytes are read."""
    current = root
    for part in PurePosixPath(rel).parts:
        current = current / part
        try:
            if current.is_symlink():
                component = current.relative_to(root).as_posix()
                return f"{rel}:symlink-component:{component}"
        except OSError as e:
            component = current.relative_to(root).as_posix()
            return f"{rel}:path-component-check-error:{component}:{type(e).__name__}"
    try:
        target_resolved = current.resolve(strict=False)
    except OSError as e:
        return f"{rel}:resolve-error:{type(e).__name__}"
    try:
        target_resolved.relative_to(root_resolved)
    except ValueError:
        return f"{rel}:resolved-outside-package-root"
    return None


def _scan_directory_actual(root: Path) -> tuple[set[str], list[str], list[str]]:
    """Enumerate actual directory members without following symlinks and fail closed on scan errors."""
    actual: set[str] = set()
    unsafe: list[str] = []
    errors: list[str] = []

    def _onerror(err: OSError) -> None:
        filename = getattr(err, "filename", None)
        rel = "<unknown>"
        if filename:
            try:
                rel = Path(filename).relative_to(root).as_posix()
            except Exception:
                rel = str(filename)
        errors.append(f"directory-scan-error:{rel}:{type(err).__name__}")

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False, onerror=_onerror):
        base = Path(dirpath)
        kept_dirs: list[str] = []
        for name in dirnames:
            p = base / name
            rel = p.relative_to(root).as_posix()
            try:
                mode = p.lstat().st_mode
            except OSError as e:
                errors.append(f"directory-entry-lstat-error:{rel}:{type(e).__name__}")
                continue
            if stat.S_ISLNK(mode):
                unsafe.append(f"{rel}:symlink")
            elif not stat.S_ISDIR(mode):
                unsafe.append(f"{rel}:not-directory")
            else:
                kept_dirs.append(name)
        dirnames[:] = kept_dirs

        for name in filenames:
            p = base / name
            rel = p.relative_to(root).as_posix()
            try:
                mode = p.lstat().st_mode
            except OSError as e:
                errors.append(f"directory-entry-lstat-error:{rel}:{type(e).__name__}")
                continue
            if stat.S_ISLNK(mode):
                unsafe.append(f"{rel}:symlink")
            elif not stat.S_ISREG(mode):
                unsafe.append(f"{rel}:not-regular-file")
            elif rel not in CONTROL_FILES:
                actual.add(rel)
    return actual, unsafe, errors


def verify_directory(root: Path, expected_manifest_sha256: str | None = None) -> dict[str, Any]:
    r = _base_receipt(root, "DIRECTORY", expected_manifest_sha256)
    if root.is_symlink():
        r["unsafe_paths"].append("subject-root:symlink")
        return _finalize(r)
    try:
        root_resolved = root.resolve(strict=True)
    except OSError as e:
        r["errors"].append(f"subject-root-resolve-error:{type(e).__name__}")
        return _finalize(r)
    manifest_path = root / "MANIFEST.json"
    if manifest_path.is_symlink():
        r["unsafe_paths"].append("MANIFEST.json:symlink")
        return _finalize(r)
    if not manifest_path.is_file():
        r["errors"].append("MANIFEST.json-not-found")
        return _finalize(r)
    r["manifest_found"] = True
    try:
        manifest_bytes = manifest_path.read_bytes()
        r["manifest_sha256"] = _sha256_bytes(manifest_bytes)
        if expected_manifest_sha256 is not None:
            if not _valid_sha256_hex(expected_manifest_sha256):
                r["errors"].append("expected-manifest-sha256-invalid")
                r["manifest_hash_match"] = False
            else:
                r["manifest_hash_match"] = r["manifest_sha256"] == expected_manifest_sha256.lower()
                if not r["manifest_hash_match"]:
                    r["errors"].append("manifest-sha256-mismatch")
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as e:
        r["errors"].append(f"manifest-json-error:{type(e).__name__}")
        return _finalize(r)
    r["manifest_candidate"] = manifest.get("candidate") if isinstance(manifest, dict) else None
    rows, errors = _manifest_rows(manifest)
    r["errors"].extend(errors)
    r["declared_files"] = len(rows)
    declared: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
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
        path_issue = _directory_member_path_issue(root, root_resolved, rel)
        if path_issue is not None:
            r["unsafe_paths"].append(path_issue)
            continue
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
    actual, scan_unsafe, scan_errors = _scan_directory_actual(root)
    r["unsafe_paths"].extend(scan_unsafe)
    r["errors"].extend(scan_errors)
    r["unexpected"].extend(sorted(actual - declared))
    return _finalize(r)


def _zip_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def verify_zip(path: Path, expected_manifest_sha256: str | None = None) -> dict[str, Any]:
    r = _base_receipt(path, "ZIP", expected_manifest_sha256)
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
            is_dir = info.is_dir()
            check_name = name[:-1] if is_dir and name.endswith("/") else name
            ok, normalized = _safe_manifest_path(check_name)
            if not ok:
                r["unsafe_paths"].append(f"{name}:{normalized}")
                continue
            if _zip_is_symlink(info):
                r["unsafe_paths"].append(f"{normalized}:symlink")
                continue
            if is_dir:
                continue
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
            manifest_bytes = zf.read(info_by_name[manifest_key])
            r["manifest_sha256"] = _sha256_bytes(manifest_bytes)
            if expected_manifest_sha256 is not None:
                if not _valid_sha256_hex(expected_manifest_sha256):
                    r["errors"].append("expected-manifest-sha256-invalid")
                    r["manifest_hash_match"] = False
                else:
                    r["manifest_hash_match"] = r["manifest_sha256"] == expected_manifest_sha256.lower()
                    if not r["manifest_hash_match"]:
                        r["errors"].append("manifest-sha256-mismatch")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except Exception as e:
            r["errors"].append(f"manifest-json-error:{type(e).__name__}")
            return _finalize(r)
        r["manifest_candidate"] = manifest.get("candidate") if isinstance(manifest, dict) else None
        rows, errors = _manifest_rows(manifest)
        r["errors"].extend(errors)
        r["declared_files"] = len(rows)
        declared: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
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


def verify_package(subject: str | Path, *, expected_manifest_sha256: str | None = None) -> dict[str, Any]:
    p = Path(subject)
    if p.is_dir():
        return verify_directory(p, expected_manifest_sha256)
    if p.is_file() and zipfile.is_zipfile(p):
        return verify_zip(p, expected_manifest_sha256)
    r = _base_receipt(p, "UNKNOWN", expected_manifest_sha256)
    r["errors"].append("subject-must-be-directory-or-zip")
    return _finalize(r)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify Factory package MANIFEST/hash/path integrity only.")
    ap.add_argument("subject")
    ap.add_argument("--expected-manifest-sha256", help="Externally frozen MANIFEST.json SHA-256 trust anchor. Without it PASS means package self-consistency only.")
    ap.add_argument("--pretty", action="store_true")
    ns = ap.parse_args(argv)
    receipt = verify_package(ns.subject, expected_manifest_sha256=ns.expected_manifest_sha256)
    print(json.dumps(receipt, ensure_ascii=False, indent=2 if ns.pretty else None, sort_keys=True))
    return 0 if receipt["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
