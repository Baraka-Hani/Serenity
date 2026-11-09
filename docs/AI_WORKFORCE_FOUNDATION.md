# Serenity supervised AI workforce

## Session 1 checkpoint

This document is the durable control panel for Serenity's first 9 AM–5 PM AI
development pilot. The first version deliberately uses GitHub issues, isolated
workspaces, pull requests, and automated checks instead of a custom dashboard or
agent-orchestration framework.

### Current architecture

| Area | Current implementation | Data / deployment boundary |
| --- | --- | --- |
| Main travel app | Python standard-library HTTP server, SQLite, plain JS/CSS PWA | Local-only by default; private state under `backend/data/` |
| Social and travel features | Accounts, trips, clips, feed, messaging, discovery, maps | Served by `backend/server.py` on loopback |
| React prototype | React, TypeScript and Vite in `nomad-canvas/` | Separate prototype; local demo works without Firebase |
| Firebase option | Hosting, Auth, Firestore rules; optional Storage | No local project selection or committed credentials |
| Portable deployment | Dockerfile and Compose | Requires explicit host, HTTPS, durable storage and approval |
| Source control | Git repository connected to `Baraka-Hani/Serenity` | Human-reviewed branches; no unattended default-branch writes |

### Two-agent pilot

```text
ME: choose one small issue and approve its acceptance criteria
  ↓
AI — BUILDER: implement in an isolated worktree; run checks; attach evidence
  ↓
AI — REVIEWER: inspect the diff independently; rerun checks; report findings
  ↓
VERIFY: CI is green and evidence matches the acceptance criteria
  ↓
STOP: human approves merge or sends the task back
```

The Builder and Reviewer are roles, not model commitments. Keep the same issue,
acceptance criteria, and evidence format when comparing models later.

### Autonomy levels

| Marker | Authority | Examples |
| --- | --- | --- |
| AI | Proceed independently in isolation | inspect code, edit docs/tests/code, run local checks, prepare a PR |
| VERIFY | Continue only after evidence is available | acceptance-criteria review, test results, privacy/security inspection |
| ME | Owner decision or access | choose feature, authorize accounts/secrets, accept cost, approve merge |
| STOP | Never proceed without explicit approval | production deploy/data, billing, secrets, purchase, public publishing |

## A real 9 AM–5 PM pilot day

### 9:00 — Intake (ME, 10 minutes)

- Pick one issue labelled for the pilot.
- Confirm outcome, acceptance criteria, risk, and the no-spend default.
- Confirm that no production credentials or real user data are required.

### 9:10–12:00 — Build (AI)

- Create an isolated branch/worktree.
- Implement the smallest complete change.
- Run the relevant Python, JavaScript, or React checks.
- Record changed files, results, limitations, security/cost impact and rollback.

### 12:00–2:00 — Review (AI)

- Review the task and diff without relying on the Builder's summary.
- Check correctness, privacy, authentication, data ownership and regressions.
- Rerun relevant checks and request changes for unsupported claims.

### 2:00–4:30 — Repair and verify (AI)

- Builder addresses findings.
- Reviewer verifies the repairs.
- CI must pass or the failure must be explicitly explained.

### 4:30–5:00 — Decision and report (ME + AI)

- AI produces an evidence-backed daily report.
- ME approves, rejects, or defers the pull request.
- No automatic merge or deployment.

## Daily report template

```markdown
# Serenity daily report — YYYY-MM-DD

## Outcome
- Issue:
- Status: built / in review / blocked / accepted

## Evidence
- Branch or worktree:
- Changed files:
- Checks run:
- Review findings:

## Safety and cost
- Production touched: no
- Secrets accessed: no
- Spend incurred: $0
- New recurring cost proposed: none

## Owner decisions
- [ ] Approve merge
- [ ] Request changes
- [ ] Approve a separately described deployment

## Next workday
- First task:
- Known blocker:
```

## Progress checklist

- [x] Locate the actual Serenity repository and identify its remote.
- [x] Inventory the main Python app, React prototype, Firebase boundary and tests.
- [x] Create an isolated managed worktree without changing the existing checkout.
- [x] Define Builder, Reviewer, human approval and emergency-stop boundaries.
- [x] Add issue and pull-request evidence templates.
- [x] Add a baseline CI workflow for Python, dependency-free JavaScript and React.
- [x] Run the Python integration suites locally (30 tests passed).
- [ ] Run the CI workflow on GitHub after the branch is published.
- [ ] Select and execute one small real feature/bug as the first pilot issue.
- [ ] Compare actual completion quality and cost before adding another model.
- [ ] Consider observability and scheduling only after the pilot is repeatable.

## Known blockers and next exact actions

1. The existing local `main` checkout has unrelated staged GitHub CLI files. Keep
   this pilot in its managed worktree; do not merge or clean those files blindly.
2. This session does not have Node/npm installed, so React and JS checks must run
   in CI or on a Node-equipped machine.
3. The Python suites were allowed to bind an isolated localhost test port and all
   30 tests passed. CI should rerun them on every proposed change.
4. Firebase is intentionally not selected. When Firebase work is genuinely
   needed, the owner must select the intended project and approve any billing or
   public deployment separately.

## When to add more infrastructure

Do not add LangGraph, Temporal, Langfuse, self-hosted models, or a custom HQ until
the Builder→Reviewer pilot completes real issues reliably. The trigger for a
dashboard is repeated work that cannot be understood from GitHub issues, pull
requests, CI evidence, and the daily report. The trigger for model routing is a
measured difference in quality, speed, or cost on Serenity's own tasks.
