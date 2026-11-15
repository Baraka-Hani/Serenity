# Serenity Module 5 — Durable Operations, Safe QA and Manager Authority

**Status:** Integrated implementation in **draft PR #25**; default-OFF.
**Program:** [Master #13](https://github.com/Baraka-Hani/Serenity/issues/13)
→ [Engineering #14](https://github.com/Baraka-Hani/Serenity/issues/14)
→ [Module 4 PR #23](https://github.com/Baraka-Hani/Serenity/pull/23)
→ [Module 5 issue #24](https://github.com/Baraka-Hani/Serenity/issues/24).

No part of this stage grants agents standing write permission, pays for model
calls, creates a GitHub App token, performs public deployment or overrides
financial owner approvals. This stage builds the verifiable foundation.

## Architecture and responsibilities

```text
GitHub issue #22 + real Serenity destination-picker tests
                 |
                 v
    Engineering Manager quality plan
                 |
           +-----+-----+
           |           |
           v           v
  Qwen Builder    GPT-OSS Reviewer
  (Module 4:     (Module 4: separately
  free host,      metered and reviewed)
  default OFF)         |
           +-----------+
                 |
                 v
 Bound candidate SHA + prior source SHA
                 |
                 v
  OCI sandbox (Module 5)
  - network none, unprivileged user, read-only filesystem
  - exact Node 22 reviewed image pinned to SHA256
  - no GitHub/AI credentials, cap-drop ALL, memory/CPU/PID/time caps
  - only two public files, fixed test command
  [execution OFF until dedicated approval]
                 |
                 v
 GitHub CI and independent QA checks
 - exact HEAD commit SHA, names, success and trusted GitHub Actions app
 - changed file inventory, no sensitive paths
 - approved human reviewer not PR author/bot, review tied to same SHA
 - STOP on incomplete or stale evidence
                 |
                 v
 Manager commit/PR proposal (Module 5)
 - exact issue #22 low-risk JS test file only
 - isolated ai/serenity-issue-22* branch
 - CANNOT currently write, merge or deploy
                 |
           +-----+------+
           |            |
           v            v
 Shift checkpoints   Obsidian Operations HQ
 09–14 / 14–19       Department, QA, quotas,
 (America/Moncton)   approvals, shift board
           |
           v
 Event journal: strict allowlist, idempotent keys, hash chain
           |
           v
 Local atomic checkpoint
 + optional GitHub protected state branch:
   serenity-company-state/state/company-ledger.json
   CAS using expected git blob SHA
   [NO remote branch, writes or credentials have been activated]
```

### What's actually implemented

| Component | Existing implementation | Actual execution status |
| --- | --- | --- |
| Replayable task journal | `company/checkpoint_store.py`, canonical events, SHA256 chain, atomic fsync and replace, replay/idempotency checks | Local-only, tested |
| GitHub cloud persistence | `company/github_checkpoint.py`, fixed repo/ref/path, Git Contents optimistic SHA update, strict GET/PUT, explicit manual owner setup | **Remote write OFF**, state branch not created |
| Secure code test sandbox | `company/sandbox_runner.py`, read-only two-file workspace, fixed Docker `node` test, network none, non-root, resource caps, no secrets, vetted pinned image required | Build/test policy only; **untrusted code NOT executed** |
| GitHub CI/review verification | `company/github_quality.py` exact commit SHA, complete checks, QA reviewer identity, changed path, sensitive file blocking, no arbitrary URLs | Read-only code with synthetic contract tests; real PR quality still pending |
| Manager authority | `company/manager_writer.py`, validates low-risk candidate, bound sandbox/review evidence, zero financial exposure and branch/path restrictions | **Planning only**; commit, draft PR and merge actions hard-blocked |
| Two five-hour shifts | `company/shift_coordinator.py`, 9–14 and 14–19 AST/ADT, checkpoint on 90% quota, avoid duplicate QA work | Deterministic proposals and simulations only |
| HQ | `company/obsidian.py` now writes Operations/Shift Board and Task Checkpoints from validated event ledger | Generated local/CI artifact; not a live remote company |
| Company preview | `company/module5_demo.py` makes recoverable shift journal, SQLite company task and handoff, Obsidian HQ | Runs without models, accounts, Docker or GitHub writes |

All scripts default to **NO autonomous execution**. The simulated model work
from Module 4 cannot pass the manager gate. Consumer ChatGPT Plus and Gemini
Plus subscriptions remain **human-initiated** specialist review tools and not
unlimited unattended APIs.

## Run today with zero external services

From the repository root:

```bash
python3 backend/test_module5_checkpoints.py
python3 backend/test_module5_sandbox_writer.py
python3 backend/test_module5_github_quality.py
python3 backend/test_module5_demo.py

python3 -m company.module5_demo \
  --day 2026-11-14 \
  --output /tmp/serenity-module5-new
```

Use a fresh output directory. Generated files:
- `company-checkpoint.json`: validated replayable event journal.
- `serenity-company.sqlite3`: private synthetic operational state, not a
  cloud database and not intended for public publication.
- `obsidian-vault/Serenity HQ/Operations/Shift Board.md`: two sample shifts.
- `obsidian-vault/Serenity HQ/Operations/Task Checkpoints.md`: latest
  task event and restart point.
- `obsidian-vault/Serenity Company.canvas`: organizational view.
- `summary.json`: exact completed vs simulated status, no claimed live agents.

The default PR CI generates a downloadable **short-lived** sample HQ and
checkpoint artifact. Its expiration means **GitHub Actions artifacts are
not the durable company database**.

## Operations and 90% quota rule

The shift windows are always expressed in `America/Moncton` timezone,
including daylight saving transitions. Do **not** equate the five-hour
organizational windows with model credit resets. Every applicable provider
request/token minute/day and subscription limit remains independently
tracked. At 90% measured consumption stop new tasks and checkpoint the
current task. Resume only when new provider evidence proves the restrictive
quota window reset *and* the other windows permit continued work.

Groq rate-limit headers do not cover every scope. The provider adapter
returns `complete=false` for partial observations, and the dispatcher must
remain blocked when quota coverage is stale, unknown or incomplete. This
module does **not** claim a verified account usage API where none has been
integrated. No paid fallback, overage or account cycling.

## Protected state branch and conflict prevention

`GithubCheckpointStore` knows only one allowed location:
- Repository: `Baraka-Hani/Serenity`
- Branch: `serenity-company-state` (not yet created)
- File: `state/company-ledger.json`

The remote writer requires an expected Git *blob* SHA; requests without
one cannot create/overwrite the ledger blindly. A 409/412 conflict causes
reconciliation, never a blind retry. A serialized approved GitHub workflow
with `concurrency` is additionally required to avoid race conditions
between shifts.

The local event-chain hash detects accidental corruption and tampering
unless an attacker can replace **the entire chain**; this is **not a
cryptographic signature** or independently verified audit log. For stronger
assurance use verified Git commit provenance and separate backups.

Until the eligible owner approves a GitHub App identity, tightly scoped
repository access and GitHub Actions usage limits, remote writes stay OFF.
Do not store API keys in an Obsidian vault or Git issue.

## Test sandbox and trust boundary

A model-generated candidate must **never run as a host process** with CI
credentials. The sandbox implementation uses:
- Only the bounded `backend/test_destination_picker.js` candidate and
  the existing public `destination-picker.js` as read-only mounts;
- Docker command arguments fixed by trusted code, not the model;
- Node 22 official image required **by verified digest**, locally cached,
  with `--pull=never`;
- `--network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges`;
- `--user=65534:65534`, CPU/memory/PID/time caps, empty runtime secrets;
- Deterministic functional test `node backend/test_destination_picker.js`.

Actual execution remains disabled until a clean, secret-free runner and an
approved exact image digest are available. Python contract tests inspect
this policy and a fake runtime, but **do not constitute sandboxed functional
execution** or independent quality proof. If those conditions are not met,
checkpoint and report blocked.

GitHub `GithubQualityReader` gets checks and reviews from GitHub itself,
not a model-generated PR summary. It verifies exact `head.sha`, named
GitHub Actions jobs, complete check-run enumeration, independent non-bot
approved reviewer on same SHA, and only allowlisted low-risk file edits.
The contract requires real `module5-candidate-sandbox` and
`module5-privacy-and-architecture` jobs to pass **in addition** to
standard Python/JavaScript/React checks. Such authorized complete jobs are
**not** active yet, so no existing PR is automatically eligible.

## Engineering Manager delegation: practical policy

Managers ultimately need **no individual owner approval for routine
feature-branch commits**, once owner has approved the *initial* tightly
scoped GitHub App setup and CI/QA rules. A manager should:
- Receive a low-risk, purposeful task from the approved backlog;
- Have an open-weight Builder propose a bounded diff in an isolated branch;
- Require independent Reviewer findings, an isolated *actual* functional
  test pass, exact-source hashes, integration tests, architecture agreement;
- Commit only the approved scope, then wait for a real exact-head GitHub
  CI/review verdict before readying any protected merge;
- Document acceptance, failures and model usage in HQ;
- Never pay, change credentials, deploy, modify private user data or
  grant itself higher permissions.

The current `company/manager_writer.py` **does not push or create PRs**.
Its methods deliberately refuse execution until a separately reviewed
trust/authorization integration is implemented. Stated passing results
in a JSON file are **not a security attestation**.

### Owner approval remains mandatory for

New financial exposure (API, storage, overage, vendors, subscriptions);
initial GitHub App credentials and authority, live model activation, public
release/deployment, production data, privacy-sensitive auth/location/payment
changes, and material strategic decisions.

A choice to automate *routine* commits is **not** a standing authorization
to weaken any of these constraints.

## What still needs to happen before unattended execution

1. Resolve stacked PRs #12 → #21 → #23 → this Module 5 PR, accounting for
   newer `main` changes. Do not silently rebase or merge while unapproved.
2. Verify actual provider account eligibility, free plan, quotas and data
   terms. Authorize initial credentials and hard cost limits if eligible.
3. Approve a reviewed pinned Node image and a dedicated GitHub runner
   without GitHub write tokens or secrets for executing candidate code.
4. Add independent CI jobs for trusted sandbox, privacy, dependency and
   architecture integration; connect GitHub evidence to candidate SHA.
5. Configure a dedicated `serenity-company-state` branch with approved
   narrow GitHub App rights, write the first ledger, validate conflict and
   recovery drills; configure immutable audit and offsite backup.
6. Introduce a reviewed, scoped GitHub code writer for low-risk branch
   commits/draft PRs only, after trusted QA and separate initial approval.
   Protected merge remains a higher verified gate; public deploy stays owner.
7. Enable two daily *short scheduled checkpoints* only after the durable
   cloud state, quotas, emergency stop and permissions are proven. This is
   not ten hours of uninterrupted paid compute.
8. Complete an actual Serenity candidate through real model review, sandbox
   functional tests, CI, manager PR, and end-to-end user journey regression.

## Next module

**Module 6 — Trusted Integration and Serenity MVP Delivery.**
Goal: owner-approved isolated *real* low-risk test candidate and verified
manager PR pilot, plus product-level video → destination save → private map
→ planning integration checks. Protect privacy and deployment boundaries.
