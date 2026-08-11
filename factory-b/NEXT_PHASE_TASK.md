# NEXT PHASE — Factory B after F4A local qualification

## Current best next step
Run one **real independent implementation-agent test** before adding more Factory architecture.

Prepared task: `qualification/HANDOFF_INDEPENDENCE_REHEARSAL_001`.
Give the implementation agent only the rehearsal repo and handoff. Do not provide this chat. Measure:
- whether clarification is needed;
- whether acceptance criteria are met;
- actual test result;
- unrelated diff count;
- evidence completeness.

## Parallel blocker that can wait
Actual Portable v2 binding remains useful but is no longer required to continue local Factory qualification. When the real Portable contracts are available, run Shadow-vs-Actual differential tests and fail closed on mismatches.

## GitHub
Do not write into an arbitrary existing repository. Once a Factory repository is explicitly designated, use a candidate branch, CI, read-back, then Draft PR. No auto-merge.

## Stop rule
Do not add new Core modules before a real independent-agent or real-project failure demonstrates a material missing responsibility.
