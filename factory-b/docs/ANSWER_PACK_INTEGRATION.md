# Answer Pack Integration — Factory B

## Decision
The high-quality answer pack remains a **page/runtime operating contract**, not a Factory B core module.

## Applied here
This Factory iteration follows these answer-pack principles:
- treat previous artifacts as `BASELINE_NOT_TRUTH` until inspected;
- maximize verifiable reuse before adding new architecture;
- prefer actual file/Linux tests over narrative claims;
- run simulation only when it can change a decision or expose a failure mode;
- label `SIMULATED` separately from actual verification;
- patch only material defects and stop on `NO_MATERIAL_DELTA`;
- do not claim external writes, approval, or agent execution that did not occur.

## Why not vendor the Answer Pack into Factory B
The Answer Pack governs how this ChatGPT project answers and verifies work. Factory B is an artifact production/delivery system. Copying the Answer Pack into Factory Core would mix page behavior with artifact-factory architecture and create a second policy owner.

## Current integration verdict
`NO_MATERIAL_DELTA` for the Answer Pack itself. The Factory candidate changed; the Answer Pack did not need a new version for this iteration.
