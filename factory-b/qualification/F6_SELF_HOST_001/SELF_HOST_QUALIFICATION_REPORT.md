# F6 Self-host Qualification Report — Patch Candidate / Pre-Review

## Verdict
`PATCH_GITHUB_CI_VERIFIED / INDEPENDENT_REVIEW_PENDING`.

Factory B used its existing pipeline contracts to create the reusable code artifact
`FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1` and then subjected that artifact to an additional
GitHub negative-control review. The current artifact version is `1.0.1-patch-candidate`.

This is **not** an F6 final PASS yet because independent review/approval remains pending.

## Self-host path exercised
1. Artifact Type Gate → `code`
2. Assetization Gate → `BUILD`
3. Blueprint Registry → `CODE_CHANGE`
4. Work Order → `WO-F6-SELFHOST-001 / FROZEN`
5. Artifact Contract 6W+ → completed and hash-bound
6. Build → Python standard-library package integrity verifier
7. Executable verification → artifact tests and GitHub CI
8. Release Contract → `GITHUB_PR`, scoped approval, independent approval pending

No new Core module was added.

## Produced artifact
Purpose: verify package MANIFEST/hash/size/path/readability integrity without claiming semantic correctness,
evidence sufficiency, provenance truth, or release approval.

The tool supports an extracted directory, a ZIP with root `MANIFEST.json`, or a ZIP with exactly one safe wrapper root.

## Real failure 1 and repair
The first real execution against `FACTORY_B_V1_F5_1_TRANSFER_SYSTEM_CANDIDATE.zip` failed because the initial implementation assumed `MANIFEST.json` was at the ZIP root.

Repair: accept either a root manifest or exactly one safe wrapper root containing the manifest; ambiguous/multiple roots remain blocked.

Historical evidence after that repair:
- real F5.1 package: PASS, 200/200 declared files verified;
- deliberately tampered package: FAIL as expected, `README.md` hash mismatch detected;
- artifact unit tests: 7 passed;
- full Factory regression: 52 passed;
- clean replay: PASS.

## Real failure 2 and repair
An additional adversarial GitHub negative control was added in Draft PR #12. It created a valid ZIP, corrupted one stored member after creation, and then invoked the verifier.

Observed on Actions run `31519004054`:
- 7 existing tests passed;
- the new test failed because `zipfile.BadZipFile: Bad CRC-32 for file 'a.txt'` escaped from `ZipFile.read()`;
- no machine-readable FAIL receipt was returned.

This violated the frozen Work Order criterion that failure paths return a machine-readable receipt and non-zero exit status.

Patch in Draft PR #13:
- catch directory and ZIP member read exceptions;
- record `directory-member-read-error:<path>:<Exception>` or `zip-member-read-error:<path>:<Exception>`;
- continue to finalization and return `verdict=FAIL` rather than crashing;
- add a regression test for the CRC-corrupted ZIP member;
- align README and Artifact Contract with the existing one-wrapper-root behavior.

Patched GitHub evidence:
- F6 Actions run `31519624007`: SUCCESS;
- artifact tests: 8/8 PASS;
- frozen candidate hash check: PASS;
- artifact hash: `a07ccd83fbe26686b1cc755b3594c23ddf58a6a6c4619608d4682c0b038117d5`;
- F5 Delivery Rehearsal regression run `31519623836`: SUCCESS.

## Evidence boundaries
- GitHub execution evidence above: VERIFIED for the listed Actions runs;
- earlier full Factory regression 52/52, clean replay, 200/200 real-package check and README tamper check were not re-executed in this narrow patch gate and remain prior technical evidence only;
- actual Portable v2 binding: UNVERIFIED;
- actual external-agent transfer receipt ingestion: NOT CONFIRMED in this gate;
- independent F6 review: PENDING;
- merge/production/public release: NOT_RUN.

## Promotion rule
F6 final `QUALIFIED_PASS` still requires an independent review to return no unresolved CRITICAL/MAJOR defect on the current patch hash. Factory B itself does not grant final approval.
