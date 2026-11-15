# Serenity AI Company — Operating Model, Two-Shift SOPs & Obsidian HQ

**Document ID:** `DOC-ONB-03`  
**Track:** Gemini Track G (Company Onboarding & Governance)  
**Deliverable:** G3 — Operating model / Obsidian headquarters onboarding  
**Target Repository:** `Baraka-Hani/Serenity`  
**Associated Issue:** [#27](https://github.com/Baraka-Hani/Serenity/issues/27) | **Joint Integration:** [#29](https://github.com/Baraka-Hani/Serenity/issues/29)  
**Date:** Saturday 14 November 2026, 23:35 America/Moncton  
**Policy Status:** Standard Operating Procedure (SOP) — **Zero New Spending Guaranteed**

---

## 1. Seven-Department Organization & Role Architecture

Serenity's workforce operates across seven persistent logical departments. These represent structured responsibilities and communication boundaries, rather than costly, always-running background daemons.

| Department | Department Key | Assigned Logical Agent | Engine / Model Assignment | Core Mission & Authority |
| :--- | :--- | :--- | :--- | :--- |
| **Executive Office** | `executive` | `chief-of-staff` | Deterministic workflow / Human Owner | Strategic backlog ranking, executive reporting, financial decision inbox, owner authorization gatekeeper. |
| **Engineering** | `engineering` | `lead-builder` | `qwen/qwen3.8-27b` (GroqCloud Free) | Implements bounded low-risk issues in isolated worktrees; writes unit tests and minimal diffs. |
| **Quality Assurance** | `qa` | `qa-director` | `openai/gpt-oss-120b` (GroqCloud Free) | Conducts independent code critique, inspects regression tests, verifies acceptance criteria. |
| **Research & Product** | `research` | `research-director` | Not connected (Human / Offline) | User discovery, competitor analysis, feature opportunity scoring (80% travel product / 20% internal tools). |
| **Architecture** | `architecture` | `chief-architect` | Human-guided ChatGPT / Gemini | Preserves system boundaries (Python PWA vs React prototype), data isolation (`backend/data/`), module contracts. |
| **Operations** | `operations` | `operations-director` | Deterministic workflow | Two-shift coordinator, quota telemetry monitoring, hash-linked checkpointing, incident response. |
| **AI Platform** | `platform` | `platform-engineer` | Not connected (Offline scripts) | Model dispatch adapters, prompt templates, runner sandboxing, CI test harness maintenance. |

---

## 2. Inter-Department Handoff Contracts & Conflict Resolution

### 2.1 Standardized Handoff Contract (JSON / Markdown)
Transitions between departments must be recorded in the local SQLite ledger (`company/office.py`) and serialized with cryptographic digest binding:

```json
{
  "task_id": "TASK-2026-11-042",
  "department_from": "engineering",
  "department_to": "qa",
  "agent_id": "lead-builder",
  "model_id": "qwen/qwen3.8-27b",
  "source_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "candidate_sha256": "4a5b6c7d8e9f...",
  "git_branch": "task/travel-destination-label",
  "diff_summary": {
    "files_changed": ["destination-picker.js", "backend/test_destination_picker.js"],
    "lines_added": 28,
    "lines_deleted": 4
  },
  "deterministic_checks": {
    "node_browser_tests": "PASSED",
    "python_backend_tests": "PASSED",
    "react_prototype_build": "PASSED",
    "ci_run_url": "https://github.com/Baraka-Hani/Serenity/actions/runs/43670053964"
  },
  "review_request": {
    "acceptance_criteria_checklist": [
      {"criterion": "Destination label wraps on mobile viewports", "verified": true},
      {"criterion": "No changes to backend data storage format", "verified": true}
    ]
  }
}
```

### 2.2 Task Lifecycle & State Transitions
Tasks advance through strict states defined in `company/office.py`:
$$\text{PROPOSED} \longrightarrow \text{EVALUATED} \longrightarrow \text{QUEUED} \longrightarrow \text{IN\_PROGRESS} \longrightarrow \text{IN\_REVIEW} \longrightarrow \text{VERIFIED} \longrightarrow \text{DONE}$$
- If owner sign-off is needed: `AWAITING_OWNER_ACTION` or `BLOCKED_APPROVAL`.
- If quota is reached or CI fails: `BLOCKED` with rollback checkpoint.

### 2.3 Escalation & Conflict Resolution Hierarchy
1. **Builder vs. Reviewer Disagreement:** If `lead-builder` and `qa-director` disagree on an implementation detail, the Reviewer's objection prevails by default. The Builder must attempt repair. If deadlocked after 2 cycles, the task transitions to `IN_REVIEW` assigned to `chief-architect`.
2. **Architectural Dispute:** If a proposal alters the boundary between the Python HTTP server and the React prototype, or touches `backend/data/`, the `chief-architect` evaluates feasibility. If unresolvable, it is queued for human owner decision in the Obsidian Financial/Strategic Inbox.
3. **Safety / Financial Gate:** Any suggestion to install paid dependencies, add external APIs, or adjust permission rules immediately pauses the task in `BLOCKED_APPROVAL` until the human owner signs off.

---

## 3. Daily Two-Shift Operating Runbook (America/Moncton)

Serenity enforces two 5-hour daily operating windows, 7 days a week:
- **Shift 1 (Morning / Midday):** 09:00 – 14:00 America/Moncton
- **Shift 2 (Afternoon / Evening):** 14:00 – 19:00 America/Moncton

> [!IMPORTANT]
> **Shift Hours $\neq$ Provider Quota Resets:** A shift boundary is an organizational coordination milestone, **not** a provider quota reset. Reaching 14:00 does not magically replenish Groq or consumer tokens. All model allocations must adhere to the 90% wind-down policy.

```
       09:00 Moncton                              14:00 Moncton                              19:00 Moncton
         │                                          │                                          │
         ▼                                          ▼                                          ▼
┌──────────────────┐                       ┌──────────────────┐                       ┌──────────────────┐
│ SHIFT 1 STARTUP  │                       │ SHIFT 1 HANDOFF  │                       │ SHIFT 2 CLOSEOUT │
│ - Reconcile CAS  │                       │ - Save checkpoints│                      │ - Generate Day   │
│ - Check Quotas   │ ──── Shift 1 Work ───►│ - Shift Handoff  │ ──── Shift 2 Work ───►│   Executive Brief│
│ - Pick Top Issue │                       │   Doc            │                       │ - Verify Zero-   │
└──────────────────┘                       └────────┬─────────┘                       │   Spend State    │
                                                    │                                 └──────────────────┘
                                                    ▼
                                           ┌──────────────────┐
                                           │ SHIFT 2 STARTUP  │
                                           │ - Verify Reset   │
                                           │ - Resume Paused  │
                                           └──────────────────┘
```

### 3.1 Shift 1 Runbook (09:00 – 14:00)
- **09:00 — Shift Initialization:**
  1. Restore latest state from local SQLite ledger and CAS checkpoint.
  2. Query Groq quota telemetry and verify remaining daily/minute buckets.
  3. Inspect GitHub Issues for any newly approved owner tasks.
- **09:15 – 13:30 — Core Execution:**
  1. Assign next approved `risk:low` task to `lead-builder`.
  2. Enforce 90% wind-down monitoring on every API call.
  3. If quota reaches $\ge 90\%$, immediately halt new task intake; complete only bounded in-flight work with 25% safety margin.
- **13:30 – 14:00 — Shift 1 Handoff Protocol:**
  1. Pause active work; run all deterministic test suites.
  2. Serialize in-flight task diffs and state to checkpoint journal.
  3. Generate `Shift_1_Handoff.md` containing: active tasks, quota consumed, tests passed, blockers encountered.

### 3.2 Shift 2 Runbook (14:00 – 19:00)
- **14:00 — Shift 2 Resumption:**
  1. Load `Shift_1_Handoff.md`.
  2. Verify provider quota telemetry. If a new quota window has opened, transition from `VERIFY_RESET` to `READY`. If quota remains exhausted, model tasks stay paused while non-model work continues.
  3. Resume unfinished tasks first; do not start new tasks while previous work remains in review.
- **14:15 – 18:30 — Core Execution:**
  1. Run independent QA on Shift 1 Builder outputs.
  2. Produce candidate SHA bindings and review findings.
- **18:30 – 19:00 — Shift 2 Closeout & Executive Briefing:**
  1. Execute full offline regression suite.
  2. Export updated Markdown vault to `Serenity HQ/` for owner review.
  3. Generate the **Daily Executive Briefing** for the owner's morning review.
  4. Verify zero external financial spend ($0.00).

---

## 4. Obsidian Headquarters (HQ) Onboarding Experience

Serenity uses Obsidian as an inspectable, file-based command centre. In accordance with `company/obsidian.py`, the HQ is generated deterministically from the local ledger.

> [!NOTE]
> **Snapshot Exporter vs. Live Sync:** The current Obsidian implementation is an **offline read-only exporter**. It writes standard Markdown notes and a visual Canvas file. It does **not** maintain a live WebSocket connection or bi-directional background sync. The owner inspects notes locally on their Mac.

### 4.1 Vault Directory Structure
When `company.obsidian.export_vault()` executes, it generates the following directory layout:

```text
Serenity HQ/
  ├── Serenity Company.canvas       # Interactive visual map of departments & flows
  ├── Command Centre.md              # Root dashboard & executive summary
  ├── Departments/
  │   ├── Executive Office.md        # Owner approvals inbox & strategy
  │   ├── Engineering.md             # Active builder branches & tasks
  │   ├── Quality Assurance.md       # Independent reviewer audits & findings
  │   ├── Research and Product.md    # Opportunity backlog (80/20 product split)
  │   ├── Architecture.md            # Boundary contracts & interface specs
  │   ├── Operations.md              # Quota telemetry & shift handoff logs
  │   └── AI Platform.md             # Model adapter status & sandbox health
  ├── Agents/
  │   ├── Chief of Staff.md          # Manager activity log
  │   ├── Lead Builder.md            # Builder execution history
  │   └── QA Director.md             # Reviewer verdicts & rejection log
  ├── Tasks/                         # One Markdown file per ledger task
  ├── Messages/                      # Inter-agent handoff communications
  ├── Engineering/                   # Test candidate hashes & diff summaries
  └── Operations/
      ├── Quota Telemetry.md         # Daily token consumption graphs & limits
      ├── Checkpoints.md             # Hash-linked CAS replay log
      └── Incidents.md               # Incident reports & rollback logs
```

### 4.2 Obsidian Company Canvas (`Serenity Company.canvas`)
The visual canvas provides a spatial overview:
- **Left Cluster (Strategy & Product):** Executive Office $\longleftrightarrow$ Research & Product.
- **Center Cluster (Architecture & Engineering):** Architecture $\longleftrightarrow$ Engineering $\longleftrightarrow$ Quality Assurance.
- **Right Cluster (Operations & Infrastructure):** Operations $\longleftrightarrow$ AI Platform $\longleftrightarrow$ External Providers.
- **Status Cards:** Real-time color-coded cards displaying active shift window, current token consumption vs 60,000 ceiling, and pending owner approvals.

---

## 5. Company Key Performance Indicators (KPIs)

The performance of the AI workforce is measured by quality, safety, and integration—never raw token burn:

| Metric | Target | Measurement Method | Failure Consequence |
| :--- | :--- | :--- | :--- |
| **Accepted Tested Features** | $\ge 1$ / day | Merged PRs with 100% test coverage | Review task scoping and complexity |
| **CI Failure Rate** | $< 5\%$ | Failed GitHub Actions runs / Total runs | Pause builder; inspect test fixtures |
| **Review Defect Detection** | $> 80\%$ | Defects caught by Reviewer before human check | Adjust Reviewer prompt / context |
| **Escaped Regressions** | **0** | Regressions identified post-merge | Immediate hotfix & test suite addition |
| **Unresolved Blocked Tasks** | $< 2$ | Tasks paused in `BLOCKED` state | Escalate to human owner in morning brief |
| **Daily Token Efficiency** | $< 60,000$ / day | SQLite token counter from API telemetry | Enforce stricter prompt compression |
| **External Financial Cost** | **$0.00** | GitHub billing API + provider invoice check | **HARD STOP: Immediate emergency audit** |
| **Time from Issue to Draft PR**| $< 4$ hours | Timestamp difference in ledger | Split issues into smaller atomic units |

---

## 6. Incident Response Runbook & Emergency Playbooks

### Scenario A: Lost or Corrupted Cloud State
- *Symptom:* Hash chain break in CAS journal or missing SQLite records.
- *Action:* Halt all agent tasks. Revert ledger state to the last verified cryptographic root commit in `serenity-company-state`. Never guess or synthesize lost state.

### Scenario B: Provider Rate Limiting (HTTP 429) or Outage
- *Symptom:* HTTP 429 (Too Many Requests) or HTTP 503 from GroqCloud.
- *Action:* Immediate fail-closed transition to `EXHAUSTED`. **Zero retry storms.** Record `x-ratelimit-reset` timestamp. Suspend model calls until the reset window has elapsed and verified.

### Scenario C: Prompt Injection or Malicious Task Content
- *Symptom:* Untrusted issue text contains jailbreak attempts, instructions to alter `.github/workflows/`, or requests to exfiltrate files.
- *Action:* Builder regex sanitizer flags prohibited directives (`eval`, `curl`, `workflow`, `token`). Task is quarantined in `BLOCKED_APPROVAL` with tag `security:injection-attempt`. Alert owner in executive report.

### Scenario D: Secrets or PII Exposure
- *Symptom:* Model output or git diff contains API keys, passwords, or personal location data.
- *Action:*
  1. Terminate runner process immediately.
  2. Revoke compromised credentials at provider console.
  3. If committed to git history, use `git-filter-repo` or BFG to scrub the commit before pushing to remote.
  4. Log incident in `Serenity HQ/Operations/Incidents.md`.

### Scenario E: Unauthorized Auto-Merge or Commit Attempt
- *Symptom:* Agent script attempts direct push to `main` without required PR or status checks.
- *Action:* GitHub Ruleset `production-quality-main` blocks the push automatically. Script logs security exception and revokes its own execution lease.

### Scenario F: Emergency Company Kill-Switch
- *Trigger:* Any high-severity security, financial, or integrity breach.
- *Execution:*
  1. Revoke `GROQ_API_KEY` in GitHub Secrets.
  2. Set `SERENITY_CLOUD_PILOT_ENABLED=false` in Repository Variables.
  3. Kill any active local runner processes (`pkill -f serenity`).

---

## 7. Zero-Cost Operations Ledger & Financial Approval Gates

Every resource utilized by Serenity must be documented in the cost ledger with an explicit verification status:

| Resource | Service / Vendor | Current Cost | Plan Expiration / Reset | Hard Financial Gate Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **Inference (Builder)** | GroqCloud (`qwen/qwen3.8-27b`) | $0.00 | Rolling 24-hour UTC window | Exhaustion of 200k daily free tokens |
| **Inference (Reviewer)** | GroqCloud (`openai/gpt-oss-120b`) | $0.00 | Rolling 24-hour UTC window | Exhaustion of 200k daily free tokens |
| **CI / CD Compute** | GitHub Actions (Linux) | $0.00 | Public repository unlimited | Workflow execution $> 4$ minutes |
| **Artifact Storage** | GitHub Actions Artifacts | $0.00 | 7-day automatic retention purge | Total storage $> 500$ MB |
| **Local Headquarters** | Obsidian (Local Markdown) | $0.00 | Local disk storage (Free) | Commercial Obsidian Sync (Not used) |
| **Application Hosting** | Localhost (`backend/server.py`)| $0.00 | Local loopback Python | Cloud VPS / PaaS deployment request |

> [!CAUTION]
> **Paid Service Trigger Rule:** If any agent or workflow encounters a requirement for credit card entry, paid API credits, server hosting, domain purchase, or paid third-party tools, the operation must **HALT IMMEDIATELY**. The task must be moved to `AWAITING_OWNER_ACTION` and placed in the owner's financial inbox. **Silence is never consent.**
