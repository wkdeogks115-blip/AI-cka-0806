from __future__ import annotations

ALLOWED_PREFIXES = ("factory-b/",)
ALLOWED_EXACT = {".github/workflows/factory-b-candidate.yml"}

def normalize_repo_path(path: str) -> str:
    p = str(path).strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p

def is_allowed_repo_path(path: str) -> bool:
    p = normalize_repo_path(path)
    if not p or p.startswith("/") or p == ".." or p.startswith("../") or "/../" in p:
        return False
    if p in ALLOWED_EXACT:
        return True
    return any(p.startswith(prefix) and len(p) > len(prefix) for prefix in ALLOWED_PREFIXES)

def validate_changed_paths(paths):
    normalized=[normalize_repo_path(p) for p in paths if str(p).strip()]
    bad=[p for p in normalized if not is_allowed_repo_path(p)]
    return {"ok": not bad, "changed": normalized, "violations": bad}
