# SERENITY — GEMINI COMPANY ONBOARDING MANDATE (NO CODING)

**As of:** Saturday 14 November 2026, 22:36 America/Moncton
**Company:** Serenity (AI-operated software company building a travel product)
**GitHub:** https://github.com/Baraka-Hani/Serenity
**Gemini track:** https://github.com/Baraka-Hani/Serenity/issues/27
**Your branch:** `gemini/company-onboarding-2026-11-14` (already created from `main`)
**Your allowed deliverables:** documentation, checklists, department operating
procedures, readiness analyses and appropriately permitted GitHub issue/project
organization. **DO NOT write or edit application or agent-execution code.**

## 1. Why you are on this team

The owner is onboarding an AI-based company, not commissioning a separate
Gemini-coded travel app. ChatGPT is already implementing the technical
infrastructure of this company. You are taking on **the other half of the
same onboarding roadmap**, in parallel, to reduce time-to-market.

Your work is meaningful only if it reduces actual blockers to running a
compliant, zero-new-spend, cloud-hosted and verifiably safe development
company. Do not merely rewrite the company vision. Research account
eligibility, permissions, quotas and services, build administrative SOPs
and reporting structures, and produce an actionable activation packet.

The owner's immediate objective is to wake up Sunday 15 November to
**tangible, truthful progress**: two parallel GitHub workstreams with
documented results, passing checks or accurately reported failures, a
clear 1-page onboarding status and the minimum owner decisions needed to
unlock actual authorized operation. Do not claim overnight Gemini coding
unless there is a real supported session or cloud agent executing.

## 2. Vision and business priorities

- **Product:** Serenity travel application; video → discover/save destination
  → *private* map → trip planning. Real product at repo root: Python standard
  library HTTP backend, SQLite and plain JS/HTML/CSS PWA. `nomad-canvas/`
  is a separate React+TypeScript+Vite/Firebase prototype, not today's app.
- **Company:** Seven role-oriented departments: Executive, Engineering,
  QA/Security, Research/Product, Architecture, Operations and AI Platform.
  Agents have persistent logical roles, not always-running human personas.
- **Proposed production workflow:** purposeful approved issue → cloud
  open-weight Builder Qwen → independent GPT-OSS Reviewer → isolated
  functional tests and CI → Engineering Manager's trusted quality decision
  → low-risk branch commit/draft PR when initial permissions have been
  approved → HQ evidence and handoff.
- **Quality:** robust architecture and cross-module integration, real
  tests, privacy/security, clear user value, maintained docs and rollback.
  Low-cost models do NOT lower the quality bar.
- **Owner authority:** the owner does not want to approve each routine
  commit. Managers can do that *after* real independent CI/QA gates and
  initial scoped access setup. Financial commitments, credentials,
  production/public deployment, private production data and material
  privacy/security decisions require owner authorization.
- **Target operating windows:** 09:00–14:00 and 14:00–19:00
  America/Moncton, seven days, with per-provider 90% quota consumption
  wind-down before assigning new tasks, documented handoff and resumption
  on VERIFIED reset. Company windows ≠ provider 5-hour quota resets.
- **Cost:** zero new spend until explicitly approved. Never enable paid
  inference, hosting, overages, subscriptions, add billing information or
  create provider credentials without owner/authorized-account approval.

## 3. Verified current technical state — distinguish built vs live

**Already exists in unmerged draft branches:**
- PR #12: https://github.com/Baraka-Hani/Serenity/pull/12
  Department roles, SQLite company ledger, simulated Chief of Staff,
  Obsidian Markdown/Canvas exporter and task/approval messages.
- PR #21: https://github.com/Baraka-Hani/Serenity/pull/21
  Low-risk synthetic engineering proposal and advisory manager QA policy.
- PR #23: https://github.com/Baraka-Hani/Serenity/pull/23
  Default-off Groq-hosted Qwen and GPT-OSS JSON adapters, quota
  dispatcher, real Serenity test-file *candidate* with mocked model output.
- PR #25: https://github.com/Baraka-Hani/Serenity/pull/25
  Atomic local hash-linked checkpoint journal, disabled remote GitHub CAS
  adapter, sandbox contract (not actual authorized execution), read-only
  exact-head GitHub QA verifier and simulated two 5-hour shifts.
- Existing CI: PR #25 previously passed at
  https://github.com/Baraka-Hani/Serenity/actions/runs/43667172013
  (this validates code/control-plane simulations, NOT live agents).
- Branch stack is **diverged** from `main` and must not be merged
  without reconciliation/authorization.

**NOT yet done:**
Actual live Qwen/GPT-OSS calls; verified eligible provider account;
provider-owned complete quota readings; GitHub App credentials;
persistent approved cloud state branch; network-isolated real generated
test execution; automatic manager GitHub writer; scheduled AI employees;
live Obsidian sync; merged/deployed app improvements.
**An Obsidian mock vault and CI artifact are not a running company.**

Master program https://github.com/Baraka-Hani/Serenity/issues/13
Operations #15, HQ #16, QA #20, Module 5 #24, Module 6 #26.

## 4. Your four autonomous-to-plan onboarding modules

These modules have **no dependency on new ChatGPT code**; start G1 and G2
immediately, then G3 and G4. Confirm facts using current official vendor
documentation. Where account access/eligibility is unknown, mark
`OWNER_ACTION_REQUIRED` instead of inventing a status.

### G1 — Provider and credit operations onboarding
Output `docs/onboarding/01_PROVIDER_AND_QUOTAS.md`.

- Inspect official Groq documentation for the precise model IDs
  `qwen/qwen3.8-27b` and `openai/gpt-oss-120b`, whether they are
  available to eligible Free accounts, current rate limits and data/terms.
  Distinguish account-specific limits, published baseline limits and
  actual observed readings. Do not assume all endpoints or plan features.
- Research supported tools and usage-display methods for ChatGPT
  Plus/Codex and Google AI Plus/Gemini. The user wants them for advanced
  architecture, critical integration reviews and code QA, but **consumer
  subscriptions are not free unlimited unattended APIs**. Do not
  inaccurately claim Google AI Plus has AI Pro's 5-hour quota.
- Specify evidence needed for RPM/RPD/TPM/TPD and any model/project tier,
  latest reset/observation, 90% wind-down and checkpoint. Partial headers
  must never green-light missing windows.
- Produce exact eligible-account/admin setup steps for a one-call,
  zero-new-spend pilot. Do NOT ask the owner to paste API keys into chat,
  a GitHub issue, Obsidian or a doc.
- Define a matrix with VERIFIED / NEEDS ACCOUNT CHECK / NOT SUPPORTED /
  REQUIRES OWNER APPROVAL. Identify risks of provider plan restrictions.

### G2 — GitHub governance and safe permissions onboarding
Output `docs/onboarding/02_GITHUB_AND_PERMISSIONS.md`.

- Determine repository-level Actions workflow permissions, branch
  protection/rulesets and available GitHub App scopes needed for
  read-only CI, state-checkpoint CAS and manager low-risk PR writing.
  Validate actual current settings only when your connected GitHub
  access can truly view them; otherwise provide UI navigation + clear
  `NOT VERIFIED` marks.
- Determine any Actions storage/compute cost or quota exposure before
  recommending overnight cloud tasks. Do not switch paid Actions on.
- Set out least-privilege roles and initial owner-approval packet:
  purpose, exact permission, allowed branch/path, expiry/rotation,
  emergency stop, audit and fallback. No credentials created by default.
- Document quality gates: exact commit SHA, real Node/Python tests,
  React typecheck/build where affected, integration, architecture,
  privacy/security and independent QA; deny GitHub write if incomplete.
- Design an immediately usable GitHub Project/Issues department board,
  with columns `Backlog, Scoped, In Progress, QA, Blocked, Awaiting
  Owner Financial Decision, Ready for Manager, Completed`.
  If authorized access supports no-cost Project board creation,
  implement only that low-risk administrative organization. Otherwise
  describe exact setup steps, don't claim done.

### G3 — Operating model / Obsidian headquarters onboarding
Output `docs/onboarding/03_COMPANY_OPERATIONS_AND_HQ.md`.

- Seven departments, exact responsibilities, input/output handoff
  contracts, when a task moves to QA, who approves what and how
  architectural/review conflicts resolve.
- Daily two shift runbook 09:00–14:00 and 14:00–19:00 Atlantic with
  checkpoint at quota >= 90%, current task finish vs no-new-task
  distinction, report at both handoff boundaries, verified reset rule.
- Design Obsidian opening experience (Company Canvas, agents,
  department boards, status, model/quota usage, PRs/CI, blocked approvals,
  financial inbox, daily executive brief) referencing the existing
  exporter. Don't invent live sync.
- Specify company KPIs: accepted *tested* features, CI failures,
  independent review defects, escaped regressions, unresolved tasks,
  quota utilization per model, actual external $ cost and time-to-PR.
- Create a short incident runbook: lost cloud state, failing quota,
  model outage, injected instructions, secrets/privacy leak, incorrect
  auto-merge claim, state-store conflict, shutdown/emergency stop.
- Prepare zero-cost operation cost ledger and clear paid service triggers.

### G4 — Integration and owner activation briefing
Output `docs/onboarding/04_ACTIVATION_DECISIONS_AND_HANDOFF.md`.

- Produce a dependency table:
  `Component | CURRENT VERIFIED STATE | Next action | Responsible
  | Owner permission? | Cost exposure | Evidence link | Done criterion`.
- Separate **GEMINI DONE**, **CHATGPT IMPLEMENTING**, **OWNER TO DO**,
  **BLOCKED**, **SIMULATED ONLY** and **LIVE VERIFIED**; never mix these.
- Cross-check against GitHub program issue #13 and parallel ChatGPT
  issue #28; document anything missing from code but don't implement it.
- Provide one-page morning executive report with exact CI and PR links,
  unpaid/paid distinction, app changes (only if merged/actually present),
  clear readiness and minimum owner actions for compliant first live pilot.
- Open a **docs-only draft PR** from your assigned branch to `main`
  if authenticated GitHub access actually exists. Do NOT merge it.
- Post a brief status linking it on issue #27 and notify integration
  issue #29. If unable to write GitHub, present the complete ready-to-paste
  files and report the limitation.

## 5. Hard boundary: what Gemini must not do

Do NOT:
- change any travel app source, JavaScript/React/Python application code,
  `company/**` executable agent code, `.github/workflows/**`,
  `backend/test_module*.py`, `AGENTS.md` or charter policies;
- create secrets, API keys, paid provider accounts, billing or compute;
- change production data, auth, account permissions or privacy settings;
- merge PRs or deploy to public servers/Firebase;
- authorize autonomous agents, trigger model calls or configure schedules
  without the required initial owner permission;
- infer that ChatGPT/Gemini consumer subscriptions allow background API
  access, artificially exhaust quotas, or circumvent eligibility;
- state that the company ran overnight if there is no evidence.

Gemini may write **ONLY** `docs/onboarding/**` on branch
`gemini/company-onboarding-2026-11-14` and non-sensitive
administrative issue/project metadata where authenticated and safe.
No source modifications to another team's branch.

## 6. Parallel timeline — planning, not guaranteed ongoing execution

User timezone is America/Moncton. Saturday November 14, 2026.
Start immediately in Gemini through an eligible interactive tool session.

| Window | Gemini onboarding independently | ChatGPT technical independently |
| --- | --- | --- |
| 22:40–23:20 Nov 14 | G1 provider availability, free limits, human review plan | C1 review CI/stack and trusted quality/runner controls |
| 23:20–00:10 Nov 15 | G2 GitHub account/permissions/branch rules, cost controls | C2 persistent state, quota/handoff and safe QA integration |
| 00:10–01:00 | G3 department SOPs, shift charter, Obsidian HQ setup | C3 company technical tests, CI artifact and draft PR |
| 01:00–01:40 | G4 review readiness, docs-only PR/issue handoff | Review/plan owner-authorized live pilot, no unintended activation |
| Overnight | Only authenticated, actually-running eligible sessions/jobs progress | Existing CI can finish after pushes; no implicit background coding |
| 08:00–09:00 Nov 15 | Reconcile Gemini admin checklist and evidence | Joint #29 review of CI, PRs and owner gates |

The schedule is a coordination plan: **this document alone does not
schedule Gemini or ChatGPT to execute**. Neither team should promise
continuous work while the owner is asleep without a real approved cloud
agent or scheduled workflow. Account/provider prerequisites may block
activation and must be honestly listed.

## 7. Evidence format and joint handoff

On finishing each Gemini module, post its link to #27 and use:
`MODULE, FACT CHECKED, OFFICIAL SOURCE URL, ACCOUNT ELIGIBILITY UNKNOWN?,
OWNER ACTION, NEW COST, OUTPUT DOC, STATUS, NEXT HANDOFF`.

Tell ChatGPT team via issue #29 **which verified API/account settings,
GitHub permission facts and operational policies it can rely on**.
Do not assume they can read your Gemini private conversation.

## Immediate instruction

Begin **G1 and G2**, not coding. Verify official provider docs, free-tier
eligibility, model/account limits, GitHub least-privilege permissions
and existing branch/CI facts. Create concrete, source-backed onboarding
documents and a docs-only draft PR. Then complete G3 and G4.

---

## 8. Track G Completion Status & Module Evidence Index

All four assigned onboarding modules have been completed and verified under the strict zero-spend, docs-only mandate:

| Module | Fact Checked? | Official Source URLs | Account Eligibility | Owner Action | New Cost | Output Deliverable | Status | Joint Handoff Target |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **G1** | Yes | [Groq Limits](https://console.groq.com/docs/rate-limits), [Groq Models](https://console.groq.com/docs/models), [OpenAI Usage](https://help.openai.com/en/articles/20001516), [Gemini Usage](https://support.google.com/gemini/answer/16275805) | Free Tier (No Card) | Setup `GROQ_API_KEY` secret & variables | $0.00 | [`01_PROVIDER_AND_QUOTAS.md`](01_PROVIDER_AND_QUOTAS.md) | **COMPLETE** | Informs C-track `company/hosted_inference.py` |
| **G2** | Yes (Live API) | GitHub REST API (`repos/Baraka-Hani/Serenity`) | Public Repo (`isPrivate: false`) | Create Ruleset for `main` & Projects Board | $0.00 | [`02_GITHUB_AND_PERMISSIONS.md`](02_GITHUB_AND_PERMISSIONS.md) | **COMPLETE** | Informs C-track manager PR writer |
| **G3** | Yes | Repo Architecture & [`company/obsidian.py`](../../company/obsidian.py) | Local SQLite / Markdown | Inspect Obsidian HQ on Mac | $0.00 | [`03_COMPANY_OPERATIONS_AND_HQ.md`](03_COMPANY_OPERATIONS_AND_HQ.md) | **COMPLETE** | Informs C-track `company/shift_coordinator.py` |
| **G4** | Yes | Issue [#13](../../issues/13), [#27](../../issues/27), [#28](../../issues/28), [#29](../../issues/29), PR [#30](../../pull/30), [#31](../../pull/31) | System Integrated | Complete 5 minimum activation steps | $0.00 | [`04_ACTIVATION_DECISIONS_AND_HANDOFF.md`](04_ACTIVATION_DECISIONS_AND_HANDOFF.md) | **COMPLETE** | Informs Owner & Joint Review #29 |

Comprehensive Index: [`docs/onboarding/README.md`](README.md)

