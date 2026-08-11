from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASK = ROOT / "qualification" / "handoff-independence-task-001" / "repo"
required = [
    TASK / "AGENTS.md",
    TASK / "HANDOFF.md",
    TASK / "src" / "text_utils.py",
    TASK / "tests" / "test_text_utils.py",
]
missing = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
if missing:
    print("MISSING_REQUIRED_FILES", missing)
    raise SystemExit(2)

handoff = (TASK / "HANDOFF.md").read_text(encoding="utf-8").lower()
for forbidden in ["use the previous chat", "follow the previous chat", "as discussed earlier"]:
    if forbidden in handoff:
        print("HIDDEN_CONTEXT_DEPENDENCY", forbidden)
        raise SystemExit(3)

# The fixture is intentionally incomplete before an independent implementation agent runs.
proc = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=TASK,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
print(proc.stdout)
if proc.returncode == 0:
    print("UNEXPECTED_BASELINE_PASS: qualification fixture must require an implementation change")
    raise SystemExit(4)

print("F5_REHEARSAL_PREFLIGHT_PASS: package complete; baseline failure confirmed")
