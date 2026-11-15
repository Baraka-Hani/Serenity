# Serenity AI Company — GitHub Governance & Safe Permissions Onboarding

**Document ID:** `DOC-ONB-02`  
**Track:** Gemini Track G (Company Onboarding & Governance)  
**Deliverable:** G2 — GitHub governance and safe permissions onboarding  
**Target Repository:** `Baraka-Hani/Serenity`  
**Associated Issue:** [#27](https://github.com/Baraka-Hani/Serenity/issues/27) | **Joint Integration:** [#29](https://github.com/Baraka-Hani/Serenity/issues/29)  
**Date:** Saturday 14 November 2026, 23:25 America/Moncton  
**Policy Status:** Audited & Verified Repository Settings — **Least Privilege Enforced**

---

## 1. Executive Summary & Audited Repository Baseline

This document defines the GitHub access controls, branch protection mechanisms, runner compute boundaries, and quality gate architectures necessary to operate an AI-assisted development workflow safely.

An audit of the `Baraka-Hani/Serenity` repository was conducted via GitHub API inspection on 14 November 2026 at 23:09 Moncton time. The findings establish the baseline security posture:

| Governance Area | Audited Live State | Required Target State | Verification Status |
| :--- | :--- | :--- | :--- |
| **Repository Visibility** | `public` (`isPrivate: false`) | `public` | **VERIFIED (API)** |
| **Workflow Permissions** | `read` (`default_workflow_permissions: "read"`) | `read` (least privilege) | **VERIFIED (API)** |
| **PR Review Approval** | `false` (`can_approve_pull_request_reviews: false`) | `false` (no bot approvals) | **VERIFIED (API)** |
| **Branch Protection (`main`)** | None (`HTTP 404: Branch not protected`) | Protected: Required status checks + Owner PR review | **DEFICIT: ACTION REQUIRED** |
| **Repository Rulesets** | None (`[]` empty) | Ruleset enforcing status checks & linear history | **DEFICIT: ACTION REQUIRED** |
| **Repository Secrets** | None (`no secrets found`) | `GROQ_API_KEY` (when owner enables smoke test) | **VERIFIED (API)** |
| **Repository Variables** | None (`no variables found`) | `SERENITY_CLOUD_PILOT_ENABLED`, `SERENITY_GROQ_FREE_VERIFIED` | **VERIFIED (API)** |
| **GitHub Projects Scope** | CLI token lacks `read:project` | Dedicated Project Board configured via UI | **NOT VERIFIED (TOKEN SCOPE LIMIT)** |

---

## 2. GitHub Actions Compute & Storage Cost Exposure

### 2.1 Compute Budget & Exposure
- **Public Repository Inclusion:** Because `Baraka-Hani/Serenity` is a public repository, standard GitHub-hosted Linux runners (Ubuntu) receive unlimited free compute minutes for standard public open-source workflows.
- **Compute Exposure Controls:** Even with free public minutes, automated tasks must not enter infinite loops or retry storms. Every workflow in `.github/workflows/` must enforce:
  1. `timeout-minutes: 4` (Maximum run ceiling for test and report jobs; `cloud-model-pilot.yml` and `ci.yml` strictly adhere to this).
  2. `concurrency: group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true` (Cancels redundant runs on rapid commits).
  3. Strict manual dispatch (`workflow_dispatch`) for any workflow invoking external network services.
- **Spending Limit:** In the owner's GitHub Billing settings (**Settings → Billing and plans → Spending limit**), ensure the spending limit for Actions is explicitly set to **$0.00**.

### 2.2 Artifact Storage Management
- Workflow jobs upload evidence packages (e.g., `serenity-technical-readiness-and-hq`, test logs).
- To prevent accumulating storage or incurring fees if visibility changes, all `actions/upload-artifact@v4` steps must specify:
  `retention-days: 7` (or `retention-days: 1` for ephemeral smoke test artifacts).

---

## 3. Branch Protection & Ruleset Configuration for `main`

Currently, `main` has no branch protection. Any authenticated git push with write access could alter history or push broken code directly. The owner must establish branch governance immediately.

### 3.1 Recommended Ruleset: "Enforce Production Quality on Main"
Navigate to **Settings → Rules → Rulesets → New branch ruleset**:

1. **General:**
   - Ruleset Name: `production-quality-main`
   - Enforcement status: **Active**
2. **Target branches:**
   - Target: `Default branch` (`main`)
3. **Branch Protections to Enable:**
   - [x] **Restrict deletions:** Prevent accidental deletion of `main`.
   - [x] **Block force pushes:** Prevent overwriting git commit history.
   - [x] **Require a pull request before merging:**
     - Required approvals: `1` (Human repository owner).
     - Dismiss stale pull request approvals when new commits are pushed.
     - Require review from Code Owners (if `CODEOWNERS` is established).
   - [x] **Require status checks to pass before merging:**
     - Require branches to be up to date before merging.
     - Mandatory status checks:
       - `backend-and-browser-logic` (Python 3.11 unit tests & JS logic tests)
       - `react-prototype` (TypeScript typecheck & Vite build)
       - `module5-privacy-and-architecture` (Architecture contracts & privacy checks)
4. **Bypass list:**
   - Only repository owner `Baraka-Hani` in emergency maintenance mode.

---

## 4. Scoped GitHub App vs. Personal Access Tokens (PAT)

For future autonomous manager PR writing and state synchronization, Serenity must reject long-lived Personal Access Tokens in favor of a scoped **GitHub App**.

### 4.1 Comparison & Security Assessment

| Security Dimension | Personal Access Token (Classic / Fine-Grained) | Scoped GitHub App (Recommended) |
| :--- | :--- | :--- |
| **Identity & Audit** | Tied to personal user identity; indistinguishable from human owner actions. | Distinct bot identity (e.g., `serenity-manager[bot]`), cleanly auditable in git log and PR timeline. |
| **Credential Lifetime** | Long-lived (days to 1 year); static credential risk if leaked. | Short-lived installation access tokens (expire automatically after 1 hour). |
| **Permission Granularity** | Broad user permissions; can inadvertently expose all owner repos. | Strictly pinned to single repository `Baraka-Hani/Serenity` with exact API scopes. |
| **Emergency Revocation** | Deleting PAT revokes developer's personal tooling access. | One-click app suspension or uninstallation in repository settings. |

### 4.2 GitHub App Least-Privilege Permission Specification

When configured, the GitHub App must be granted **ONLY** the following repository permissions:

```yaml
Repository Permissions:
  contents: write         # Restrict branch write ONLY to company/* and serenity-company-state
  pull_requests: write    # Create and update draft pull requests targeting main
  issues: write           # Update issue labels, comments, and task checklists
  metadata: read          # Read repository metadata (mandatory default)

Restricted / Excluded Permissions (Must be set to NONE):
  administration: none    # Cannot change repo settings, rename repo, or delete branches
  workflows: none         # Cannot create or alter .github/workflows/*.yml files
  secrets: none           # Zero access to Actions secrets or variables
  billing: none           # Zero access to billing or subscription controls
  members: none           # Zero access to organization membership or invitations
```

### 4.3 Emergency Stop & Rollback Protocol
If any anomalous activity, prompt injection, or unauthorized commit attempt occurs:
1. **Immediate Revocation:** In repository **Settings → GitHub Apps**, click `Suspend` or `Uninstall` on `serenity-manager`.
2. **Secret Nullification:** Delete `GROQ_API_KEY` from repository secrets.
3. **Variable Takedown:** Set `SERENITY_CLOUD_PILOT_ENABLED=false`.
4. **Git State Rollback:** Fast-forward or reset affected feature branches using the verified hash-linked commit log (`git revert` or `git reset --hard <verified-sha>`).

---

## 5. End-to-End Quality Gates (Pre-Commit → PR → Merge)

Routine commits by an AI builder must pass five deterministic quality gates before an Engineering Manager or human owner can consider them. Unverified model prose is never treated as evidence.

```
┌─────────────────────────────────────────────────────────────┐
│                 GATE 1: PURPOSE & SCOPE                     │
│  - Issue acceptance criteria clearly defined               │
│  - Low-risk classification verified (Docs, Tests, Utility)  │
│  - No modifications to Auth, Session, Payment, PII, Workflows│
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 GATE 2: STATIC & REPO HYGIENE               │
│  - Clean git diff in isolated branch (no stray files)       │
│  - JSON / YAML syntax check                                 │
│  - Candidate SHA256 digest calculated and bound             │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              GATE 3: DETERMINISTIC AUTOMATED CI             │
│  - Python 3.11 unit & integration tests: 100% PASS         │
│  - Root vanilla JS browser tests: 100% PASS                │
│  - Nomad-canvas React typecheck & build: 100% PASS          │
│  - Exact head commit SHA matches CI run ID                  │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               GATE 4: INDEPENDENT REVIEWER QA               │
│  - Distinct model identity (openai/gpt-oss-120b)            │
│  - Validates git diff against exact issue requirements      │
│  - Output: Structured JSON report (No self-approval allowed)│
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               GATE 5: DELEGATED AUTHORITY / OWNER           │
│  - Low-Risk Draft PR: Engineering Manager may create        │
│  - Merge into Main: Requires Owner Sign-off + Green CI      │
│  - Spend, Deploy, Credentials: HARD OWNER APPROVAL GATE    │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. GitHub Projects & Department Board Design

Because the current CLI token lacks `read:project` scope, automated creation cannot proceed without elevated authentication. The owner can create this board in under 2 minutes using GitHub's native UI:

### 6.1 Step-by-Step UI Setup
1. Navigate to repository `Baraka-Hani/Serenity` → **Projects** tab.
2. Click **New project** → Select **Board** template → Name: `Serenity AI Company Operations`.
3. Set project visibility to **Public**.

### 6.2 Required Board Columns (Kanban Flow)
Configure the board columns in this exact sequence:
1. `Backlog` — Newly identified opportunities, unscheduled ideas.
2. `Scoped` — Approved tasks with clear acceptance criteria and verified low-risk classification.
3. `In Progress` — Active task assigned to Builder agent (`qwen/qwen3.8-27b`) in isolated branch.
4. `QA` — Automated tests running, assigned to Reviewer agent (`openai/gpt-oss-120b`).
5. `Blocked` — Quota exhausted (90% limit reached), test failure, or missing technical dependency.
6. `Awaiting Owner Financial Decision` — Requests for API keys, budget expansion, or external service spending.
7. `Ready for Manager` — All 4 automated quality gates passed; ready for draft PR synthesis.
8. `Completed` — Verified PR merged into `main` by owner, issue closed.

### 6.3 Standardized Label Taxonomy
The repository already contains foundational labels (`agent:builder`, `agent:reviewer`, `risk:low`). The complete taxonomy for company operations is:

| Category | Label Name | Color | Purpose |
| :--- | :--- | :--- | :--- |
| **Department** | `dept:executive` | `#000000` | Strategy, owner decisions, financial allocations |
| | `dept:engineering` | `#1D76DB` | Builder implementation, refactoring, feature work |
| | `dept:qa-security` | `#0E8A16` | Independent review, threat models, test validation |
| | `dept:research-product` | `#C5DEF5` | Competitive research, user journey analysis |
| | `dept:architecture` | `#0052CC` | System boundaries, interface contracts, data model |
| | `dept:operations` | `#5319E7` | Quota monitoring, two-shift scheduling, HQ sync |
| | `dept:ai-platform` | `#6F42C1` | Model dispatch, prompt templates, runner isolation |
| **Risk Tier** | `risk:low` | `#28A745` | Docs, isolated tests, visual UI (eligible for delegation) |
| | `risk:medium` | `#FFC107` | Cross-module APIs, data contract adjustments |
| | `risk:high-sensitive` | `#DC3545` | Auth, private location tracking, database schema |
| | `risk:financial` | `#B60205` | Requires explicit owner financial sign-off |
| **Execution State** | `status:ready` | `#0E8A16` | Quota verified, pre-checks green, ready to run |
| | `status:wind-down` | `#E36209` | Model quota >= 90%, finishing in-flight only |
| | `status:checkpointed` | `#6A737D` | Paused cleanly; state serialized to local ledger |
| | `status:blocked` | `#D93F0B` | Defect or dependency blocking execution |

---

## 7. Immediate Owner Setup Packet (Fillable Checklist)

The following actions require direct owner execution in the GitHub web interface:

- [ ] **Billing Ceiling:** Confirm GitHub Actions spending limit is set to `$0.00` in personal billing settings.
- [ ] **Ruleset Activation:** Navigate to **Settings → Rules → Rulesets** and create `production-quality-main` enforcing PR reviews and status checks.
- [ ] **Project Board Setup:** Navigate to **Projects** and create `Serenity AI Company Operations` with the 8 standardized columns.
- [ ] **Secret Configuration (Deferred):** Add `GROQ_API_KEY` to Actions secrets only when ready to authorize the single manual smoke test.
- [ ] **Workflow Variables (Deferred):** Set `SERENITY_CLOUD_PILOT_ENABLED=true` and `SERENITY_GROQ_FREE_VERIFIED=true` when authorizing smoke test.
