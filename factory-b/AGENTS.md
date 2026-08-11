# Factory B Candidate Instructions

Scope: `factory-b/**` only.

- Treat Portable AI Orchestrator v2 as the control owner. Do not recreate its router, evidence ledger, approval system, or adapter registry.
- Work only from the task handoff and explicitly referenced files.
- Preserve source hashes and report any mismatch as `STALE` or `BLOCKED`.
- Do not claim tests you did not execute.
- Do not merge or release to production/public without an external final-approval gate.
- Prefer minimal diffs and keep unrelated repository paths untouched.
- For this candidate, actual Codex execution evidence must be labeled separately from process-isolated readiness.
