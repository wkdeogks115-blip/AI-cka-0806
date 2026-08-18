# Authority reconciliation

This branch is **supplemental reproduction evidence only**. It does not supersede the Track B Source Truth or the already independently reviewed patch candidate.

Authoritative current chain after fresh Track B CURRENT read:
- source PR #18 exact head: `212ae0e6b6375d68c81261c08f6b27bc0dab07e8` — unchanged
- authoritative patch source SHA-256: `e28c6ff418f4eac41b17784959b41711cf9d44ec1270c0108b9f82f736254f27`
- authoritative race test SHA-256: `67dcf9636d75f3f026077ee67efa824383d26b9c16402aa649b5bfe6295c4f4a`
- fresh GitHub proof run: `32111008275` — PASS
- fresh independent evaluator: `32111849611` — PASS_CANDIDATE / 10/10 / blocking 0
- immutable receiver: `32112420712` — VALIDATED
- product version created: NO
- ACTIVE / FINAL: false
- next gate: `CONTROLLED_PRODUCT_SIDE_PATCH_INTEGRATION_REVIEW`

The local `v1.0.4` wording in earlier files on this branch is an experiment/package label only and is **not** an approved product version. The local 17/17 and 1000-iteration stress results remain useful as additional evidence that the defect is reproducible and that descriptor-anchored no-follow approaches close the observed escape path.

For product-side integration, use the authoritative independently-reviewed patch source/test above, not the local alternate implementation on this evidence branch.
