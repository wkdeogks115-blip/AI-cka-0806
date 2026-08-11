# Expected evaluation behavior

- Exact packet hash mismatch -> REJECT.
- Any changed file outside `allowed_write_scope` -> REJECT.
- Missing required test result -> PATCH.
- Required test FAIL/NOT_RUN -> PATCH.
- Acceptance result not all PASS -> PATCH.
- Receipt status BLOCKED -> BLOCKED.
- All required evidence present, all required tests PASS, all acceptance PASS, no scope violation, zero clarification -> ACCEPT + handoff independence PASS.
- Same as above but with clarification(s) -> ACCEPT + handoff independence PARTIAL.

Only an actual receiving-agent run can populate an evidence-bearing receipt. The example receipt is never treated as evidence.
