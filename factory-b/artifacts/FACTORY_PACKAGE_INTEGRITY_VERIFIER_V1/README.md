# Factory Package Integrity Verifier v1.0.5-patch-candidate

A deterministic integrity checker for Factory B artifact/release packages.

It verifies package self-consistency (manifest/path/hash/size/readability) and can optionally bind the
manifest to an **external SHA-256 trust anchor**. It **does not** decide semantic correctness,
quality, safety, evidence sufficiency, provenance truth, or release approval.

## Important integrity boundary
Without `--expected-manifest-sha256`, a `PASS` means only that the package bytes are
self-consistent with the manifest inside the same package. If an attacker or broken transport
changes both payload and manifest together, self-consistency alone cannot detect that.

For transport/read-back or release evidence, freeze the manifest hash outside the package and run:

```bash
python src/package_integrity.py package.zip --expected-manifest-sha256 <FROZEN_SHA256> --pretty
```

The receipt reports `integrity_scope` as `SELF_CONSISTENCY_ONLY` or `ANCHORED_MANIFEST`.
Unreadable directory members and corrupt/unreadable ZIP members are fail-closed: the verifier
records a machine-readable read error and returns `verdict=FAIL` instead of allowing the read
exception to escape.

Malformed non-object entries inside `MANIFEST.json` `files[]` are also fail-closed. They are
recorded as manifest-row errors and are skipped during byte verification instead of raising an
uncaught attribute error.

Manifest scalar types are validated fail-closed (`schema_version`, `candidate`, integer `file_count`,
and integer `size`), NUL/non-canonical/dot/repeated-slash/Windows-drive paths are rejected, and ZIP
directory entries are path/symlink-checked before they are ignored as structural directories.

Directory enumeration is also fail-closed: unreadable subdirectories, symlink entries, and non-regular
entries cannot be silently skipped while the package reports `PASS`.

Directory mode rejects a symlink subject root and checks every path component from the package
root through each manifest-declared member before reading bytes. Any symlink component or resolved
target outside the resolved package root is recorded in `unsafe_paths` and fails closed.

## Supported inputs
- a directory containing `MANIFEST.json`
- a ZIP containing root `MANIFEST.json`
- a ZIP containing exactly one safe wrapper root with `MANIFEST.json`

The manifest contract supported by v1 is the Factory B manifest shape:
`schema_version`, `candidate`, `file_count`, and `files[]` where each valid file row is an object
containing `path`, `sha256`, and optional `size`.

## CLI

```bash
python src/package_integrity.py /path/to/package.zip
python src/package_integrity.py /path/to/package.zip --expected-manifest-sha256 <sha256>
python src/package_integrity.py /path/to/extracted/package --pretty
```

Exit code is 0 only when the selected integrity verdict is `PASS`.
