# F6 Self-host Qualification Report — F6.2 Combined Patch / Pre-Review

## Verdict
`GITHUB_CI_REVALIDATED / INDEPENDENT_REVIEW_PENDING`.

Factory B used its existing pipeline contracts to create the reusable support artifact
`FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1`. The current candidate version is
`1.0.2-patch-candidate`, artifact tree hash
`9cc6c200eb23fc95042d0aa1cc75720388ebe0d09be9a54d901ab7ae0a595a2f`.

This is **not** an F6 final PASS. Independent review/approval remains pending.

## Self-host path exercised
1. Artifact Type Gate → `code`
2. Assetization Gate → `BUILD`
3. Blueprint Registry → `CODE_CHANGE`
4. Work Order → `WO-F6-SELFHOST-001 / FROZEN`
5. Artifact Contract 6W+ → completed and hash-bound
6. Build → Python standard-library package integrity verifier
7. Executable verification → real package/tamper evidence plus GitHub Actions
8. Release Contract → `GITHUB_PR`, scoped approval, independent approval pending

No new Factory Core module or Portable v2 responsibility was added.

## Integrity boundaries preserved
The verifier checks package byte/path/readability self-consistency and can additionally bind
`MANIFEST.json` to an externally frozen SHA-256 trust anchor. Without that external hash, PASS
means `SELF_CONSISTENCY_ONLY`; with it, the receipt reports `ANCHORED_MANIFEST` and coordinated
payload+manifest substitution can be detected.

It does not claim semantic correctness, evidence sufficiency, provenance truth, or release approval.

## Failure 1 — wrapper-root assumption
The first real F6 execution failed because the distribution ZIP used exactly one wrapper root while
the initial verifier assumed root `MANIFEST.json`.

Repair: accept root manifest or exactly one safe wrapper root; ambiguous/multiple roots remain blocked.

## Failure 2 — coordinated payload+manifest substitution
F6.1 adversarial validation showed that package-internal self-consistency cannot detect a coordinated
replacement of both payload and manifest.

Repair: add optional `expected_manifest_sha256` / CLI `--expected-manifest-sha256`. F6.1 evidence records
a real Factory package as `PASS_200_OF_200_ANCHORED_MANIFEST`, while coordinated tampering passes only
in unanchored self-consistency mode and fails in anchored mode with `manifest-sha256-mismatch`.

## Failure 3 — corrupt ZIP member exception escape
Draft PR #12 added a negative control that creates a valid ZIP and corrupts one stored member after
creation. GitHub Actions run `31519004054` reproduced the defect: the seven prior tests passed, while
the new case raised `zipfile.BadZipFile: Bad CRC-32 for file 'a.txt'` from `ZipFile.read()`.

That violated the frozen Work Order boundary requiring a machine-readable failure receipt and non-zero
failure exit rather than an uncaught exception.

## F6.2 repair
The combined patch is based on latest F6.1 head
`6564a7f291c976949435c0ec0edb0657de1d612c`, so the trust-anchor functionality is preserved.

Minimal code change:
- catch directory-member read errors and record `directory-member-read-error:<path>:<Exception>`;
- catch ZIP-member read errors and record `zip-member-read-error:<path>:<Exception>`;
- continue through normal finalization and return `verdict=FAIL`;
- add one anchored CRC-corruption regression test;
- document fail-closed unreadable-member behavior.

## Current actual GitHub evidence
Draft PR #14 (`factory-b/f6-selfhost-003`) is the combined candidate.

- F6 Actions run `31520744374`: **SUCCESS**
- Artifact tests: **11/11 PASS**
- Candidate artifact hash check: **PASS**
- F5 Delivery Rehearsal run `31520744370`: **SUCCESS**
- PR remains Draft / unmerged.

Prior F6.1 evidence retained, not re-labeled as newly rerun:
- full Factory regression: `PASS_55`
- targeted clean replay: PASS
- real Factory package: `200/200`, anchored manifest PASS
- coordinated payload+manifest tamper: anchored FAIL as expected

## Evidence boundaries
- PR #12 negative-control execution: actual GitHub evidence.
- PR #14 F6/F5 Actions results: actual GitHub evidence.
- F6.1 real-package/trust-anchor records: prior verified local execution evidence.
- full Factory regression 55/55 was not repeated in this narrow patch gate.
- actual Portable v2 binding: UNVERIFIED.
- actual external-agent transfer receipt ingestion: NOT CONFIRMED in this gate.
- independent F6 review: PENDING.
- external final approval: UNVERIFIED.
- Factory ACTIVE v1: PREACTIVE.

## Promotion rule
F6 final `QUALIFIED_PASS` requires an independent review of the **current hash** to return no unresolved
CRITICAL/MAJOR defect. Factory B itself cannot grant that approval or write ACTIVE.
