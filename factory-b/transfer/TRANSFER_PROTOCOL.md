# TRANSFER PROTOCOL v1

## Goal
Preserve task intent and acceptance criteria across agent boundaries while minimizing hidden-context dependence.

## States
`DRAFT -> FROZEN -> DELIVERED -> EXECUTED|BLOCKED -> RECEIPT_RETURNED -> EVALUATED -> ACCEPT|PATCH|REJECT`

## Invariants
- A `FROZEN` packet must carry a content hash.
- The receiving agent may only write under `allowed_write_scope`.
- Returned changed files outside scope force `REJECT`.
- Every declared required test must have a matching returned test record or the receipt must explain why it was not run.
- `VERIFIED` is forbidden as an agent self-assertion; verification status belongs to the evaluator/control plane.
- A non-zero clarification count is not automatically a failure, but it lowers handoff-independence quality and must be recorded.
- Release target does not grant release permission. External release remains subject to Factory Release Contract and approval gates.

## Minimal successful handoff
A task is transfer-ready when another agent can infer what to change, what not to change, how to test, and what evidence to return using only the packet and explicitly listed files.
