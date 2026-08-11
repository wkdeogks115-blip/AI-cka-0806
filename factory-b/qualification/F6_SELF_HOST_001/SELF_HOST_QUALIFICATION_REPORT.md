# F6 Self-host Qualification Report — Local / Pre-Review

## Verdict
`LOCAL_VERIFIED / EXTERNAL_REVIEW_PENDING`.

Factory B used its own existing pipeline contracts to create a new reusable code artifact from scratch:
`FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1`.

This is **not** an F6 final PASS yet because independent review/approval remains pending.

## Self-host path actually exercised
1. Artifact Type Gate → `code`
2. Assetization Gate → `BUILD`
3. Blueprint Registry → `CODE_CHANGE`
4. Work Order → `WO-F6-SELFHOST-001 / FROZEN`
5. Artifact Contract 6W+ → completed and schema-valid
6. Build → Python standard-library package integrity verifier
7. Local executable verification → artifact tests + real Factory package
8. Release Contract → `GITHUB_PR`, scoped approval, independent approval pending

No new Core module was added.

## Produced artifact
Purpose: verify package MANIFEST/hash/size/path integrity without claiming semantic correctness,
evidence sufficiency, or release approval.

The tool supports an extracted directory or ZIP and emits a JSON integrity receipt.

## First real failure and repair
The first real execution against `FACTORY_B_V1_F5_1_TRANSFER_SYSTEM_CANDIDATE.zip` failed because the initial implementation assumed `MANIFEST.json` was at the ZIP root.
The actual Factory distribution uses exactly one wrapper directory.

Patch: accept either a root manifest or exactly one safe wrapper root containing the manifest; ambiguous/multiple roots remain blocked.

After the patch:
- real F5.1 package: PASS, 200/200 declared files verified;
- deliberately tampered package: FAIL as expected, `README.md` hash mismatch detected;
- artifact unit tests: 7 passed;
- full Factory regression: 52 passed;
- Factory validator: PASS, 49 required files / 13 schemas / 6 Core / 11 blueprints;
- clean replay: PASS.

## Evidence boundaries
- local execution results above: VERIFIED in the local Linux environment;
- prior external-agent qualification: GitHub commit/diff verified and tests independently reproduced, but the external result receipt bundle has not been ingested here;
- actual Portable v2 binding: UNVERIFIED;
- independent F6 review: PENDING;
- merge/production/public release: NOT_RUN.

## Promotion rule
F6 final `QUALIFIED_PASS` requires independent review to return no unresolved CRITICAL/MAJOR defect and the GitHub candidate CI/read-back to pass on the current candidate hash.
