# F6.1 Adversarial Finding — Manifest Trust Anchor

## Verdict before patch
`PATCH`.

The original `FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1` correctly detected payload tampering when the embedded manifest stayed frozen, but a coordinated substitution of both payload and embedded `MANIFEST.json` returned `PASS`.

That behavior is expected for an unanchored self-consistency checker, but it is insufficient if the result is interpreted as transport/read-back integrity.

## Patch
- add optional external `MANIFEST.json` SHA-256 trust anchor;
- emit `manifest_sha256`, `manifest_hash_match`, and `integrity_scope`;
- distinguish `SELF_CONSISTENCY_ONLY` from `ANCHORED_MANIFEST`;
- fail closed for an invalid or mismatched expected manifest hash.

Patched artifact hash:
`f65cb29d3f69c4328bbb8c9da35a7c98d699b1eb79228a103ca30ac0f502a788`

## Local executable evidence
- artifact tests: 10 passed;
- full Factory regression: 55 passed;
- targeted clean replay: PASS;
- real F5.1 package with external manifest anchor: PASS, 200/200;
- coordinated payload+manifest substitution: unanchored PASS as self-consistency, anchored FAIL with `manifest-sha256-mismatch`.

No extra Monte Carlo simulation was run because deterministic adversarial execution provided stronger information.

Independent review remains pending and must target the patched hash above.
