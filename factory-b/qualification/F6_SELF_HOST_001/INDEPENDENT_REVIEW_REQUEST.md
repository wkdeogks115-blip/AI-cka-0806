# F6 Independent Review Request

Review only the frozen candidate `FACTORY_PACKAGE_INTEGRITY_VERIFIER_V1` and its evidence.

## Check
- correctness of byte/path integrity logic;
- unsafe ZIP/directory edge cases;
- whether any Portable v2 semantic verification/approval responsibility was duplicated;
- whether tests cover material failure modes;
- whether a simpler implementation would be materially safer or cheaper.

Return one of: `KEEP`, `PATCH`, `REDESIGN`, `NO_MATERIAL_DELTA`.
Severity: `CRITICAL`, `MAJOR`, `MINOR`, `COSMETIC`.

Do not approve merge/production. This is qualification review only.
