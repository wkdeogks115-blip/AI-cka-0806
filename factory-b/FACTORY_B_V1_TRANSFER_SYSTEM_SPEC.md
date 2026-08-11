# FACTORY B v1 — Transfer System Specification

## Purpose
Turn a frozen Factory B implementation handoff into a self-contained, agent-neutral task package that another AI or developer can execute without access to the originating conversation.

## Ownership boundary
The Transfer System is a support layer, not a seventh Core module. The six Core modules remain unchanged. Portable v2 retains control-plane ownership for risk, verification policy, evidence promotion, and approval. The receiving agent only implements within the packet's declared scope.

## Pipeline
`Factory Work Order -> Implementation Handoff -> Transfer Packet Freeze -> Package -> External Agent -> Result Receipt -> Deterministic Evaluation -> Independent Review -> Release Contract`

## Deliverables
- Frozen transfer packet with SHA-256 binding.
- Explicit context policy: `EXPLICIT_FILES_ONLY_NO_PRIOR_CHAT`.
- Allowed write scope and prohibited actions.
- Required tests and acceptance criteria.
- Standard result receipt schema.
- Deterministic evaluator scorecard.
- Portable ZIP task pack with manifest and per-file hashes.

## Qualification rule
Local tests, mutation/property simulations, and clean replay can qualify the protocol implementation locally. They cannot prove true handoff independence. That status remains `UNVERIFIED` until a genuinely separate receiving agent executes the packet without hidden context and returns evidence.
