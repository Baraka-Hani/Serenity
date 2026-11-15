# Serenity Engineering Department — issue → patch → QA → owner

**Status:** integrated end-to-end **offline demonstration only**. Do not interpret
an offline task, a passing AST check, or an Obsidian page as a production-ready
code change. No actual AI models are called by this pipeline.

## How this fits the whole company

- **Executive Office** manages approved backlog and scopes tasks to authorized files.
- **Engineering** proposes the smallest code change in an isolated checkout.
- **QA** independently inspects the proposed patch and its verification evidence.
- **Operations** stores the task checkpoint, audit events, handoff messages and quota notes.
- **Obsidian HQ** displays run provenance, owner decisions and departmental status.
- **Engineering Manager** authorizes routine commits after true CI, independent QA, integration checks and policy alignment. The **owner** retains finance, production/public release, credentials and high-impact security/privacy decisions. The current demo cannot authorize any GitHub action.

This is one workstream within [the company master program](../docs/SERENITY_COMPANY_PROGRAM.md)
and [Engineering issue #14](https://github.com/Baraka-Hani/Serenity/issues/14).
It does **not** replace the Serenity travel-app MVP.

## Working today (without credentials)

The [synthetic engineering task](../config/engineering_demo_task.json) is
deliberately not a real GitHub issue. Its source is
`company/fixtures/destination_label.py`, a non-production helper.

Run at the repository root, with Python 3.11+:

```bash
python3 backend/test_engineering_pipeline.py
python3 -m company.engineering_pipeline \
  --task config/engineering_demo_task.json \
  --source-root . \
  --artifact-root /tmp/serenity-engineering-evidence-new \
  --db /tmp/serenity-company-engineering.sqlite3
```

Choose a new, nonexistent output directory each time. The task run key is
idempotent: rerunning it against the same ledger is blocked, rather than
creating duplicate messages or approval requests.

The process creates:

| Evidence | Purpose |
| --- | --- |
| `proposed.patch` | Human-readable isolated source diff; no source checkout modified |
| `patch-proposal.json` | Versioned, allowlisted structured replacement proposal |
| `qa-review.json` | Offline deterministic QA rules, **not** a model review |
| `engineering-report.json` | Source hash, patch hash, run status, exact verification limitations |
| `isolated-worktree/` | Scratch copy of the changed fixture, not a Git branch or PR |
| `obsidian-vault/Serenity HQ/` | Updated command centre, engineering evidence, messages and owner queue |
| `obsidian-vault/Serenity Company.canvas` | Native Obsidian organizational visualization |

The CLI prints a machine-readable report. The simulated task remains in
`IN_REVIEW`: deterministic static checks are insufficient to pass the
manager's commit gate. It does not create a fictitious owner merge request.
The future manager is authorized by policy to handle routine code only after
real independent QA, actual CI and architecture gates; none of those live
controls are enabled by this demo.

The PR's existing [Serenity checks](../.github/workflows/ci.yml) execute this
demonstration in GitHub-hosted CI and publish a short-lived evidence artifact.
A separate [manual-only workflow](../.github/workflows/engineering-offline.yml)
can be run after the file reaches `main` by a **separate owner-approved merge**.

## Quality-first manager delegation

The proposed [quality gate](quality_gate.py) and [policy](../docs/DELEGATED_ENGINEERING_AUTHORITY.md) require actual passing Python, JS, React and integration checks, an independent reviewer, architecture/mission alignment, a bounded diff and rollback evidence. The evaluation is advisory and always reports `execution_authorized=false`; a mock static screen can never authorize a commit. Owner approval is focused on financial and material high-impact decisions, not every routine patch.

## Security and safety gates already implemented

- Task manifest has a fixed JSON schema, explicit `simulation_only=true`,
  low risk, engineering department and synthetic source kind.
- A single exact file is currently permitted by the fixed allowlist.
  Issue labels, model output or untrusted instructions cannot expand the scope.
- A bounded full-file replacement includes the original file SHA-256.
  Stale hashes, directory traversal, hidden files, secrets and symlinks fail.
- Only one Python function, a small UTF-8 source file and a conservative static
  syntax/construct scan are accepted.
- Proposed code is **never executed** and no model-supplied shell commands are
  honored. A passing static scan is **not** a functional or security test.
- The input repository remains unchanged; changes go only to an isolated
  scratch output directory and proposed patch artifact.
- Role-specific handoff messages, acknowledgements, checkpoint and audit
  event are persisted; one unique run key prevents duplicate owner queues.
- No GitHub write token, provider key, billing setting or scheduled activation
  is used. CI has `contents:read` only.
- The two five-hour shifts and 90% quota policy are still governed by
  [the existing policy](../docs/QUOTA_AWARE_SHIFTS.md); **no live quota
  adapter is connected**, so no automatic inference can start.

## What is NOT yet implemented

- Real GitHub issue approval as an executable task. The company already has a
  **read-only issue importer**, but imported issue bodies remain untrusted and
  do not grant permission to work on source.
- Qwen writing actual source patches; GPT-OSS performing independent model QA.
  The separate synthetic [cloud pilot](../tools/cloud_model_pilot.py) supports
  only a deliberately limited manual model call after eligibility and
  permission checks.
- A secure runner capable of executing model-generated code tests. This
  first version checks syntax and structure only; it **does not** run untrusted
  model-generated Python in a potentially network-connected CI environment.
- Creating a Git branch, PR, or review comments automatically.
  Every code change is a **proposal artifact** until a separate approved
  GitHub write procedure has been designed, tested and authorized.
- Durable *cloud* task memory. SQLite in this pilot lives on the local disk
  or a temporary CI runner. An approved persistence layer with scoped access
  is required for resumable jobs across independent cloud runs.

## Next engineer-to-QA milestone

1. **Initial governance migration:** PR #12 company HQ and this stacked
   engineering PR remain drafts until reviewed. Thereafter verified routine
   work can be delegated to managers without per-commit approval.
2. **Provider eligibility and accounting:** eligible owner/admin confirms
   Groq free plan, data terms, actual quotas and GitHub Actions cost boundary.
   No credentials are required for offline mode.
3. **Approved synthetic smoke tests:** the older manual one-call pilot can
   verify Qwen and GPT-OSS independently without touching real code.
4. **Explicit allowlist and accepted issue:** after a separate review, extend
   the pipeline from synthetic fixture to one low-risk actual Serenity helper.
   Cap model context and output; classify sensitive paths as human-only.
5. **Safe model adapter + review:** implement schema-constrained proposals and
   independent second-model review; introduce a defensible sandbox for test
   execution. Provider-specific quota readers must check every applicable
   window and stop new work at 90% consumed.
6. **Manager commit / PR gate:** add a separately permissioned, CI-verified
   flow for isolated branch commits and draft PRs after independent QA.
   Low-risk protected merges may be manager-operated only behind proven
   branch protections and an activation decision; public deployment and
   spending remain owner controlled.
7. **Durable handoffs:** remote approved state store, restart/replay handling
   and Obsidian sync. Then trial time windows and quota-reset recovery,
   not automatic resets at 14:00.

These are separate development milestones; checkboxes are updated only after
successful evidence and appropriate owner decisions.
