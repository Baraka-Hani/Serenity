# Serenity AI Company — Integration Briefing, Activation Decisions & Morning Report

**Document ID:** `DOC-ONB-04`  
**Track:** Gemini Track G (Company Onboarding & Governance)  
**Deliverable:** G4 — Integration and owner activation briefing  
**Target Repository:** `Baraka-Hani/Serenity`  
**Associated Issue:** [#27](https://github.com/Baraka-Hani/Serenity/issues/27) | **Joint Integration:** [#29](https://github.com/Baraka-Hani/Serenity/issues/29)  
**Date:** Saturday 14 November 2026, 23:45 America/Moncton  
**Policy Status:** Master Coordination Briefing — **Zero New Spending Guaranteed**

---

## 1. Executive Summary & Dual-Track Alignment

On Saturday 14 November 2026, Serenity established two independent, non-overlapping workstreams to accelerate company onboarding without compromising quality, safety, or financial discipline:

- **Gemini Track G ([#27](https://github.com/Baraka-Hani/Serenity/issues/27), PR [#30](https://github.com/Baraka-Hani/Serenity/pull/30)):** Administrative company onboarding, provider rate limits and credit boundaries, GitHub least-privilege governance, two-shift operating SOPs, Obsidian HQ architecture, and owner activation checklists. **Docs-only; zero application or workflow code modified.**
- **ChatGPT Track C ([#28](https://github.com/Baraka-Hani/Serenity/issues/28), PR [#31](https://github.com/Baraka-Hani/Serenity/pull/31)):** Technical execution pipeline, deterministic candidate SHA binding, independent QA verification, hash-linked checkpoint reconciliation, and Obsidian export scripts. **Code & tests; verified by passing CI run [#43670053964](https://github.com/Baraka-Hani/Serenity/actions/runs/43670053964).**

Both tracks converge at **Joint Integration Issue [#29](https://github.com/Baraka-Hani/Serenity/issues/29)**. This document provides the authoritative integration assessment, dependency truth table, Sunday morning executive report, and minimum owner sign-offs needed for activation.

---

## 2. Master System Dependency & Status Table

To eliminate ambiguity between code simulations and live operations, every system component is classified using an exact, mutually exclusive status taxonomy:

- `GEMINI DONE` — Administrative specification and governance policy fully researched and documented.
- `CHATGPT IMPLEMENTING` — Technical software or test suite currently under active construction on Track C.
- `OWNER TO DO` — Manual action required exclusively by the human repository owner via external UI.
- `BLOCKED` — Execution suspended pending an external dependency, credential, or security gate.
- `SIMULATED ONLY` — Offline deterministic mock or test fixture; no live network or cloud activity.
- `LIVE VERIFIED` — Cryptographically proven or GitHub API-verified live state.

| Component | Current State Category | Current Verified State | Next Action | Responsible Track | Owner Permission Required? | Cost Exposure | Evidence Link | Done Criterion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Provider Quota Research** | `GEMINI DONE` | Groq Free tier, model IDs `qwen/qwen3.8-27b` & `openai/gpt-oss-120b`, and 60k token budget established. | Review account limits on owner console. | Track G | No | $0.00 | [01_PROVIDER_AND_QUOTAS.md](01_PROVIDER_AND_QUOTAS.md) | Official vendor URLs & rate limits verified. |
| **GitHub Access Audit** | `GEMINI DONE` | Repo confirmed public, workflow permissions `read`, PR approvals bot-disabled, branch rules absent. | Configure `production-quality-main` ruleset. | Track G | Yes (Admin) | $0.00 | [02_GITHUB_AND_PERMISSIONS.md](02_GITHUB_AND_PERMISSIONS.md) | Live GitHub API query results documented. |
| **Operating SOPs & HQ** | `GEMINI DONE` | 7-department charter, two-shift runbook (09:00–14:00, 14:00–19:00), 90% wind-down, Obsidian vault structure. | Connect exporter to real test events. | Track G | No | $0.00 | [03_COMPANY_OPERATIONS_AND_HQ.md](03_COMPANY_OPERATIONS_AND_HQ.md) | Standard Operating Procedure published. |
| **Activation Packet** | `GEMINI DONE` | Dependency matrix, 1-page morning report, and owner sign-off checklist completed. | Review by owner upon waking. | Track G | No | $0.00 | [04_ACTIVATION_DECISIONS_AND_HANDOFF.md](04_ACTIVATION_DECISIONS_AND_HANDOFF.md) | Comprehensive onboarding suite merged to PR #30. |
| **Engineering Pipeline** | `CHATGPT IMPLEMENTING` | Static candidate binding, distinct Builder/Reviewer roles, fail-closed offline manager policy. | Implement sandboxed runner attestation ([#32](https://github.com/Baraka-Hani/Serenity/issues/32)). | Track C | No | $0.00 | PR [#31](https://github.com/Baraka-Hani/Serenity/pull/31) | CI run #43670053964 green across all 3 jobs. |
| **Replay & Checkpoints** | `CHATGPT IMPLEMENTING` | Local hash-linked journal detects `IN_SYNC`, `LOCAL_AHEAD`, `DIVERGED_BLOCKED`. | Wire remote CAS adapter when state branch is approved. | Track C | No | $0.00 | `company/checkpoint_store.py` | Unit tests verify divergence detection. |
| **Obsidian Snapshot Exporter** | `SIMULATED ONLY` | `company/obsidian.py` exports mock ledger to Markdown & Canvas. | Feed live candidate SHA events into snapshot exporter. | Track C | No | $0.00 | `serenity-technical-readiness-and-hq` artifact | Verified generation of `Serenity Company.canvas`. |
| **Groq Cloud API Key** | `OWNER TO DO` | No secret exists in GitHub repository (`no secrets found`). | Generate key in Groq console; add `GROQ_API_KEY` to Actions secrets. | Owner | **YES** | $0.00 (Free Tier) | [01_PROVIDER_AND_QUOTAS.md](01_PROVIDER_AND_QUOTAS.md) | Secret securely stored; no chat/doc exposure. |
| **Manual Pilot Variables** | `OWNER TO DO` | No variables exist in GitHub repository (`no variables found`). | Set `SERENITY_CLOUD_PILOT_ENABLED` & `SERENITY_GROQ_FREE_VERIFIED` to `true`. | Owner | **YES** | $0.00 | [01_PROVIDER_AND_QUOTAS.md](01_PROVIDER_AND_QUOTAS.md) | Variables visible in repository settings. |
| **Branch Ruleset for Main** | `OWNER TO DO` | `main` branch has zero protections (`Branch not protected`). | Create ruleset enforcing PR review + 3 status checks. | Owner | **YES** | $0.00 | [02_GITHUB_AND_PERMISSIONS.md](02_GITHUB_AND_PERMISSIONS.md) | API returns active ruleset for `main`. |
| **GitHub Project Board** | `OWNER TO DO` | CLI token lacks `read:project` scope; board not yet created. | Create `Serenity AI Company Operations` board via UI. | Owner | **YES** | $0.00 | [02_GITHUB_AND_PERMISSIONS.md](02_GITHUB_AND_PERMISSIONS.md) | 8 standard columns populated with labels. |
| **Remote State Branch** | `BLOCKED` | Branch `serenity-company-state` does not exist on remote. | Provision isolated empty orphan branch once PR stack merges. | Track C / Owner | **YES** | $0.00 | Issue [#15](https://github.com/Baraka-Hani/Serenity/issues/15) | Branch exists and receives CAS checkpoints. |
| **Live Model Invocation** | `BLOCKED` | Zero live model calls have been executed. All tests use mocks. | Trigger single manual synthetic smoke test via Actions dispatch. | Owner | **YES** | $0.00 | `.github/workflows/cloud-model-pilot.yml` | JSON report artifact confirms 1 successful call. |
| **Main Travel App Code** | `LIVE VERIFIED` | Untouched Python HTTP backend, SQLite, vanilla JS/CSS PWA. | Keep frozen during infrastructure onboarding. | Both Tracks | N/A | $0.00 | Repository Root | Git diff confirms 0 application lines altered. |

---

## 3. Sunday Morning Executive Report (15 November 2026)

```text
========================================================================================
                       SERENITY AI COMPANY — EXECUTIVE BRIEFING
                      Prepared for Owner Review: Sunday 15 Nov 2026
========================================================================================
```

### I. Operating Status & Highlights
- **Dual-Track Progress Complete:** Both parallel tracks have delivered their assigned Saturday evening work packages without conflict. Track G completed administrative onboarding; Track C completed technical engineering readiness.
- **Strict Scope Integrity:** **Zero lines of application code** (`backend/server.py`, JS/HTML/CSS PWA, `nomad-canvas/`) or `.github/workflows/` were modified by Gemini.
- **Financial Status:** **$0.00 total spend.** Zero billing accounts created, zero paid API keys provisioned, zero credit cards entered.
- **Autonomous Execution State:** **FAIL CLOSED (BLOCKED).** Autonomous coding agents are disabled. No background loops or daemons are running.

### II. Pull Requests & CI Verification
1. **Gemini Track G (Onboarding & Governance):**
   - **Branch:** `gemini/company-onboarding-2026-11-14` (based on `main`)
   - **Draft PR:** [#30](https://github.com/Baraka-Hani/Serenity/pull/30)
   - **Content:** Docs-only onboarding suite under `docs/onboarding/` (Modules G1–G4).
   - **Checks:** All checks passing.
2. **ChatGPT Track C (Engineering & Readiness):**
   - **Branch:** `company/parallel-ops-2026-11-14` (stacked on PR #25)
   - **Draft PR:** [#31](https://github.com/Baraka-Hani/Serenity/pull/31)
   - **Content:** Technical readiness evaluator, candidate digest binding, checkpoint reconciliation, test suites.
   - **CI Run:** Verified passing at [Run #43670053964](https://github.com/Baraka-Hani/Serenity/actions/runs/43670053964). Artifact `serenity-technical-readiness-and-hq` successfully produced.

### III. Verified Fact Base vs. Key Deficits
- **Verified Facts:** Groq Free model IDs verified; Actions workflow permissions verified as `read`; CI suites pass 100% deterministically.
- **Live Governance Deficit:** `main` has no branch protection rulesets. Direct pushes are technically possible until the owner creates the recommended ruleset.
- **Missing Telemetry Reality:** Groq headers do not report rolling daily token consumption (TPD). The internal runtime ledger must independently tally token usage to ensure adherence to the 60,000 token daily budget.

---

## 4. Minimum Owner Sign-Offs for Live Pilot Activation

To advance from offline simulation to a supervised, single-call live smoke test, the owner must complete exactly **five manual actions**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   MINIMUM OWNER ACTIVATION CHECKLIST                   │
└────────────────────────────────────────────────────────────────────────┘

[ ] ACTION 1: Verify Groq Free Account (Zero-Spend)
    - Sign in to https://console.groq.com.
    - Confirm Free Developer Tier in Billing (do NOT add payment card).
    - Check Limits page: confirm qwen/qwen3.8-27b and openai/gpt-oss-120b are listed.

[ ] ACTION 2: Configure GitHub Repository Secrets & Variables
    - Generate restricted API key in Groq Console.
    - Add to GitHub Settings -> Secrets -> Actions as GROQ_API_KEY.
    - Add to GitHub Settings -> Variables -> Actions:
        SERENITY_CLOUD_PILOT_ENABLED = true
        SERENITY_GROQ_FREE_VERIFIED = true

[ ] ACTION 3: Establish Branch Ruleset on `main`
    - In Settings -> Rules -> Rulesets, create `production-quality-main`.
    - Enforce PR review (1 approval) + 3 required status checks:
        * backend-and-browser-logic
        * react-prototype
        * module5-privacy-and-architecture

[ ] ACTION 4: Execute Single-Call Manual Smoke Test
    - In GitHub Actions -> "Serenity manual cloud-model pilot".
    - Run workflow manually on `main`:
        mode: mock (Verify green first)
        mode: live, role: builder (Executes exactly 1 bounded call to Qwen)
    - Inspect output JSON artifact to verify header telemetry capture.

[ ] ACTION 5: Reconcile & Authorize PR Stack
    - Review PR #30 (Gemini docs onboarding) and merge to `main`.
    - Review PR #31 (ChatGPT engineering readiness) stacked on #25/#23/#21/#12.
    - Authorize unmerged branch reconciliation.
```

---

## 5. Next Planned Work Packages

1. **Immediate Technical Milestone ([#32](https://github.com/Baraka-Hani/Serenity/issues/32)):** Trusted container runner attestation, candidate SHA provenance bound to PR head, and initial scoped manager draft PR writer.
2. **First Real Feature Pilot ([#26](https://github.com/Baraka-Hani/Serenity/issues/26) / Module 6):** Implementation of an approved low-risk travel product feature (e.g., Destination Label styling or Clip Studio tag helper) under end-to-end verified controls.
3. **Obsidian Live Data Ingestion:** Connect local Obsidian exporter to read live events from the SQLite checkpoint ledger once the first manual pilot executes.
