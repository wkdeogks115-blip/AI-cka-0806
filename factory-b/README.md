# Factory B v1 GitHub Candidate

This subtree is a reviewable Factory B candidate. It is not an ACTIVE release.

Evidence levels:
- Process-isolated handoff readiness: may be PASS from local clean-room execution.
- GitHub branch/PR existence: may be VERIFIED from GitHub.
- Candidate GitHub Actions: advisory only; the branch can modify its own workflow/checker.
- External PR-scope audit: mandatory for scope acceptance and owned outside the candidate branch.
- External scope receipt: must be bound to the expected repository, PR number, head SHA, and canonical changed-file digest; stale/replayed receipts fail closed.
- Codex execution: must remain UNVERIFIED until a real Codex run returns repository evidence.
- Final approval: external gate only.

The external scope gate verifies complete changed-file scope, locked control Git blob SHAs, and exact PR identity. GitHub Actions SUCCESS by itself is not scope authorization. The offline gate still relies on a lab-captured GitHub connector receipt and does not cryptographically attest the connector origin.
