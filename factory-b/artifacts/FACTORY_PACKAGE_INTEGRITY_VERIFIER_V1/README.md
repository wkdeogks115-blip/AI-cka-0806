# Factory Package Integrity Verifier v1

A deterministic integrity checker for Factory B artifact/release packages.

It verifies byte/path integrity only. It **does not** decide semantic correctness,
quality, safety, evidence sufficiency, or release approval. Those remain outside
this artifact (Portable/control-plane/reviewer responsibilities).

## Supported inputs
- a directory containing root `MANIFEST.json`
- a ZIP containing root `MANIFEST.json`
- a ZIP containing exactly one safe wrapper directory whose direct child is `MANIFEST.json`

Ambiguous/multiple wrapper roots are rejected. ZIP member read/CRC failures are
returned as a machine-readable `FAIL` receipt rather than escaping as an exception.

The manifest contract supported by v1 is the Factory B manifest shape:
`schema_version`, `candidate`, `file_count`, and `files[]` where each file row
contains `path`, `sha256`, and optional `size`.

## CLI

```bash
python src/package_integrity.py /path/to/package.zip
python src/package_integrity.py /path/to/extracted/package --pretty
```

Exit code is 0 only when the integrity verdict is `PASS`.
