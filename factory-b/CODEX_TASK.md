# Codex task — Factory B v1 integration candidate

## Goal
Validate that the `factory-b/` candidate can be understood and modified from repository-local instructions without access to prior ChatGPT conversation history.

## Inputs
- `factory-b/AGENTS.md`
- `factory-b/qualification/qualification_handoff.json`
- files explicitly listed by that handoff
- `factory-b/contracts/activation_gate.yaml`

## Required work
1. Execute the qualification handoff in an isolated working directory.
2. Run the candidate tests.
3. Keep changes inside `factory-b/**` unless a workflow file under `.github/workflows/factory-b-candidate.yml` is explicitly required.
4. Return raw test output, changed file list, and hashes of generated artifacts.

## Non-goals
- Do not modify Portable Core, Runner, sealed comparison inputs, or answer-pack source.
- Do not merge the PR.
- Do not claim final approval.

## Success boundary
A successful Codex run may prove repository-local handoff execution for this candidate. It does not by itself activate Factory B v1; activation still requires the external approval gate defined in `activation_gate.yaml`.
