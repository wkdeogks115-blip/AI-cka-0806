# NEXT PHASE — Real Transfer Qualification

## Current best next step
Run `FACTORY_B_V1_TRANSFER_QUALIFICATION_001.zip` with a genuinely separate implementation agent using no prior conversation context.

Target GitHub branch: `factory-b/handoff-agent-001`.

The agent receives only the transfer package / explicitly listed repository files. It must implement the task, run required tests, and return an `agent_result_receipt.json`.

## Factory-side evaluation after return
1. Validate packet/receipt schema and packet hash.
2. Compare changed paths against allowed write scope.
3. Verify required test evidence.
4. Evaluate acceptance criteria and evidence completeness.
5. Count clarifications and unrelated diffs.
6. Read back GitHub branch if used.
7. Set handoff independence to PASS only if the actual external execution satisfies the contract.

## Stop rule
Do not add another Core/Router unless the real external-agent run demonstrates a missing responsibility that cannot be handled by an existing Core or support contract.
