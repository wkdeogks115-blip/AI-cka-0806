# Factory B v1 GitHub Candidate

This subtree is a reviewable Factory B candidate. It is not an ACTIVE release.

Evidence levels:
- Process-isolated handoff readiness: may be PASS from local clean-room execution.
- GitHub branch/PR existence: may be VERIFIED from GitHub.
- Candidate GitHub Actions: advisory only; the branch can modify its own workflow/checker.
- External PR-scope audit: mandatory for scope acceptance and owned outside the candidate branch.
- Codex execution: must remain UNVERIFIED until a real Codex run returns repository evidence.
- Final approval: external gate only.

The external scope gate verifies the complete changed-file list and locked Git blob SHAs for the candidate workflow/checker/path-scope controls. GitHub Actions SUCCESS by itself is not scope authorization.
