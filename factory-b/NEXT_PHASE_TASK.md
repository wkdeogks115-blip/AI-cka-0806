# NEXT PHASE — Factory B after verified F5 GitHub rehearsal

## Verified new evidence
A real GitHub candidate branch, Draft PR, read-back, and GitHub Actions run have completed successfully in `wkdeogks115-blip/AI-cka-0806`. This closes the **GitHub rehearsal** blocker, not the full Factory release blocker.

## Current best next step
Run one **real independent implementation-agent test** using `qualification/HANDOFF_INDEPENDENCE_REHEARSAL_001`. Give the agent only the repo/task files, not this chat. Measure:
- clarification count;
- acceptance-criteria completion;
- actual test result;
- unrelated diff count;
- evidence completeness.

## Why this is now first
More Router/Core work has lower information gain. GitHub transport itself has been proven in a real external environment; the biggest unresolved question is whether an implementation agent can succeed from the frozen Handoff alone.

## Portable v2
Actual binding remains `UNVERIFIED`. It can wait until the independent-agent test because current Factory defects can still be found without pretending Shadow behavior is actual Portable behavior.

## GitHub
Keep PR #3 as Draft. Do not merge yet. After the independent-agent result, either patch the handoff/Factory contract or expand this candidate branch with the full Factory source.

## Stop rule
Do not add a new Core module unless the real-agent test or a real product produces a material missing responsibility that cannot be fixed in an existing module, blueprint, contract, or support layer.
