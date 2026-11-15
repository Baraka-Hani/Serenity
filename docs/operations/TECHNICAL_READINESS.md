# Serenity Technical C-Track — verified readiness and cloud onboarding

**Owner goal:** a genuine low-supervision AI software company delivering a
purposeful, high-quality Serenity travel application. The owner's approvals
focus on new costs, credentials/access, production/public deployment and
material privacy/security; ordinary manager-controlled code delivery is a
target **after** actual independent quality gates and an initial approved
limited GitHub permission setup.

**This document concerns the ChatGPT TECHNICAL track** in issue
[#28](https://github.com/Baraka-Hani/Serenity/issues/28) and draft
[PR #31](https://github.com/Baraka-Hani/Serenity/pull/31).
**Gemini handles administrative company onboarding** in
[issue #27](https://github.com/Baraka-Hani/Serenity/issues/27).
Gemini does NOT code the app. Do not edit their `docs/onboarding/**` branch.

## Current branch stack

The company remains on four unmerged draft branches:
[PR #12](https://github.com/Baraka-Hani/Serenity/pull/12)
→ [PR #21](https://github.com/Baraka-Hani/Serenity/pull/21)
→ [PR #23](https://github.com/Baraka-Hani/Serenity/pull/23)
→ [PR #25](https://github.com/Baraka-Hani/Serenity/pull/25)
→ this [technical PR #31](https://github.com/Baraka-Hani/Serenity/pull/31).
Do not merge/rebase out of order or silently reconcile `main`.

## New technical implementation in PR #31

### 1. Exact-candidate readiness policy (default blocked)

`company/technical_readiness.py::assess_candidate` accepts a bounded
read-only Serenity code candidate, hashes original and proposed bytes, and
requires issue #22 + allowed test path, actual Qwen Builder identity, an
independent GPT-OSS Reviewer bound to the same candidate SHA, and
non-simulated QA. It also checks the intended network-isolated functional
test record and **independently fetched** exact-head GitHub Actions CI,
changed-file inventory and non-bot human reviewer through the existing
read-only `GithubQualityReader`.

What it does **not** prove: untrusted input JSON is **not signed**. A
purported sandbox result or model success message is NOT trusted merely
because it claims a pass. Even a happy test fixture returns
`manager_commit_execution_authorized=false` and
`actual_runner_provenance_verified=false`. The planned manager writer in
`company/manager_writer.py` continues to refuse real commits, PR creation
and merges.

All of these block progression: stale source/candidate hash, mock Reviewer,
Builder/Reviewer identity mismatch, stale CI head SHA, self-approved QA,
queued/missing checks, missing sandbox isolation or GitHub evidence, sensitive
file or financial operation, and forged/incomplete PR scope.

### 2. Safe checkpoint reconciliation

`reconcile_snapshots(local, remote)` validates each ledger's event hash
chain and schema, identifies exact shared prefix, and returns:
- `IN_SYNC` when both histories are identical
- `REMOTE_AHEAD` when remote extends local
- `LOCAL_AHEAD` when local extends remote (requires approved CAS writer)
- `DIVERGED_BLOCKED` for competing events following a shared ancestor

This function does **not** merge, overwrite or upload anything. The existing
GitHub adapter knows only the fixed `serenity-company-state` branch/file,
and remote writes require a separately owner-approved GitHub App setup.
There is not yet approved cloud-durable state; local CI preview artifacts
expire.

### 3. Honest, reproducible HQ readiness packet

`company/technical_report.py` reads the real
`backend/test_destination_picker.js` and bounded task manifest but
uses a **clearly labeled deterministic mock** for the candidate. No
generated code runs; no provider API call occurs. It creates:
- `technical-readiness.json`: blocked/ready evidence with detailed reasons
- `READINESS.md`: human-readable owner/admin handoff and action list
- `company-checkpoint.json`: integrity-checked QA handoff event
- `obsidian-vault/Serenity HQ/`: company organization and Operations Shift
  Board from a local SQLite + journal snapshot

CI runs the new modules and archives a short-lived
`serenity-technical-readiness-and-hq` artifact. It does not authenticate
any real AI provider, unlock the manager writer or enable an agent schedule.

Command at repository root:

```bash
python3 backend/test_module6_technical_readiness.py
python3 backend/test_module6_technical_report.py

python3 -m company.technical_report \
  --source-root . \
  --output /tmp/serenity-tech-readiness-new
```

Use a **new, nonexistent** output directory; no source files are modified.

## Company-wide quality gates still required

These are real blockers, not work already marked complete:

1. **Initial provider eligibility and authorization:** Gemini G1 verifies
   account terms, eligible Groq Free access, exact model IDs, per-window
   real quotas and 90% wind-down. Owner/admin separately authorizes any
   secret/access grant; no new spending, no paid fallback.
2. **Actual restricted functional testing:** owner approves the exact
   pinned Node OCI image/digest and clean credentials-free runner. The
   existing sandbox contract is default OFF. Execute generated test cases
   only there, not directly on a privileged runner.
3. **Independently verified runner provenance:** attach the sandbox result
   to the exact candidate SHA *via a trustworthy protected GitHub Actions
   job*, not arbitrary JSON. Review the workflow file and branch protection.
4. **Trusted QA/CI/architecture:** GitHub API must show completed green
   exact-head checks, static integration/privacy checks, an independent
   human PR reviewer tied to the commit and complete test results.
5. **Durable cloud state:** owner-approved, scoped remote state branch and
   GitHub App permission, CAS race/restart drills, separation from secrets.
6. **Manager PR writer:** initial owner-approved low-risk GitHub App scope,
   trustworthy CI + QA attestation. Only then implement narrowly scoped
   feature-branch pushes and draft PRs. No automatic protected merges,
   production deploys or spending.
7. **Cloud worker activation:** no standing two-shift agents until the
   above gates, actual provider quotas and emergency stop are verified.
   Five-hour organizational shifts 09:00–14:00 and 14:00–19:00 Moncton
   do NOT imply five-hour Groq reset windows. Wind down new jobs at 90%
   measured consumption of every applicable quota bucket.

## Parallel handoff for Gemini and the owner

Gemini's G1–G4 modules can progress independently: actual free-model
eligibility, plan meter/terms, GitHub repository/branch/App permissions,
department SOPs, HQ setup and administrative activation checklist.
This technical PR can pass CI without their changes. The two outputs
converge in [integration issue #29](https://github.com/Baraka-Hani/Serenity/issues/29).

In any morning readiness report distinguish:
`proposal`, `simulated`, `static_checked`, `functionally_executed`,
`independently_reviewed`, `CI_proven`, `committed`, `merged`,
`deployed`, `live_company`. Do NOT call a mock or a contract test
operational company activity.

**Next technical module:** an approved, read-only **candidate sandbox
attestation run** with exact digest and a restricted worker, then a
trusted manager draft-PR writer scoped to one test file after genuine CI
and independent review. Owner retains separate initial authorization for
privileges, credentials, spend and production.
