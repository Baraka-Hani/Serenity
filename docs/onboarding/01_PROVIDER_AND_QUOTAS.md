# Serenity AI Company — Provider Onboarding and Quota Policy

**Document ID:** `DOC-ONB-01`  
**Track:** Gemini Track G (Company Onboarding & Governance)  
**Deliverable:** G1 — Provider and credit operations onboarding  
**Target Repository:** `Baraka-Hani/Serenity`  
**Associated Issue:** [#27](https://github.com/Baraka-Hani/Serenity/issues/27) | **Joint Integration:** [#29](https://github.com/Baraka-Hani/Serenity/issues/29)  
**Date:** Saturday 14 November 2026, 23:15 America/Moncton  
**Policy Status:** Proposal / Administrative Specification — **Zero New Spending Guaranteed**

---

## 1. Executive Summary & Purpose

This document establishes the verified provider specifications, rate limits, credit constraints, and usage policies required to operate Serenity's supervised AI workforce without incurring financial expense or violating service agreements.

In alignment with [AI_COMPANY_OPERATING_CHARTER.md](../../AI_COMPANY_OPERATING_CHARTER.md) and [docs/QUOTA_AWARE_SHIFTS.md](../QUOTA_AWARE_SHIFTS.md), Serenity adheres to a strict **zero-spend policy**. Autonomous agents must never create paid subscriptions, enable billing, incur overage fees, or switch to paid fallbacks. If free capacity is exhausted or rate limits are reached, the task must **fail closed and checkpoint**, pausing until verified capacity is restored.

---

## 2. Hosted AI Models: Verified GroqCloud Specifications

Serenity designates two remote open-weight models hosted on GroqCloud's LPU (Language Processing Unit) infrastructure for low-risk, verifiable development tasks:

| Role | Provider | Exact API Model ID | License / Weights | Plan Tier | Service Stability | Cost |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Builder** | GroqCloud | `qwen/qwen3.8-27b` | Apache 2.0 | Free Developer Tier | **Preview** (subject to change/deprecation) | $0.00 |
| **First-Pass Reviewer** | GroqCloud | `openai/gpt-oss-120b` | Apache 2.0 | Free Developer Tier | **Production-Designated** | $0.00 |

### 2.1 Model Scope & Boundaries

- **`qwen/qwen3.8-27b` (Builder):**
  - *Allowed Tasks:* Generating isolated unit tests, documentation fixtures, UI layout helpers (HTML/CSS/vanilla JS), standard library utility functions, and non-sensitive refactorings.
  - *Context Policy:* Model receives only bounded file excerpts and exact issue acceptance criteria. Never feed full repository archives, user location history, or private data.
  - *Stability Risk:* Marked as **Preview** by Groq. Preview models may have changing endpoints, temporary throttling, or sudden deprecation. The company architecture must maintain adapter modularity to swap preview models with another approved open-weight model without pipeline redesign.

- **`openai/gpt-oss-120b` (Reviewer):**
  - *Allowed Tasks:* Inspecting proposed git diffs against issue criteria, identifying regression risks, checking test coverage gaps, and providing structured JSON review findings.
  - *Boundary Rule:* The Reviewer cannot edit code or merge pull requests. Review findings are advisory inputs to deterministic test runners and the Engineering Manager.

### 2.2 GroqCloud Free Developer Tier Rate Limits

Rate limits on GroqCloud Free accounts are enforced per model family and account tier. The baseline published parameters must be distinguished from individual account allocations and live HTTP headers:

| Metric | Published Baseline Free Limit | Internal Planned Workday Budget | Strictest Window |
| :--- | :--- | :--- | :--- |
| **Requests Per Minute (RPM)** | 30 req/min | Maximum 10 req/min | 1-minute sliding window |
| **Requests Per Day (RPD)** | 1,000 req/day | Maximum 100 req/day | Rolling 24-hour UTC window |
| **Tokens Per Minute (TPM)** | 8,000 tokens/min | Maximum 4,000 tokens/min | 1-minute sliding window |
| **Tokens Per Day (TPD)** | 200,000 tokens/day | **Maximum 60,000 tokens/day** | Rolling 24-hour UTC window |
| **Concurrent Requests** | 1 active call | 1 active call (strictly sequential) | Instantaneous |

> [!IMPORTANT]
> **Published Baselines vs Account Limits:** The numbers above represent Groq's published developer baseline. Individual accounts may have lower limits based on IP reputation, account age, or region. The actual limits must be validated directly within the owner's [Groq Console Limits](https://console.groq.com/docs/rate-limits) dashboard before any live pilot.

### 2.3 Official Vendor References
- Groq Rate Limits Documentation: <https://console.groq.com/docs/rate-limits>
- Groq Supported Models: <https://console.groq.com/docs/models>
- Groq Free Billing & Quotas FAQ: <https://console.groq.com/docs/billing-faqs>
- Groq Model Spec (`qwen/qwen3.8-27b`): <https://console.groq.com/docs/model/qwen/qwen3.8-27b>
- Groq Model Spec (`openai/gpt-oss-120b`): <https://console.groq.com/docs/model/openai/gpt-oss-120b>
- Groq Terms of Service & Acceptable Use: <https://console.groq.com/docs/legal/services-agreement>

---

## 3. Commercial Consumer Subscriptions: Boundaries & Realities

The company strategy reserves Tier-1 frontier models (ChatGPT Plus/Codex and Google AI Plus/Gemini) for high-impact human-in-the-loop escalation. However, administrative planning must enforce strict technical boundaries regarding consumer subscriptions:

### 3.1 ChatGPT Plus, Team & Codex
- **Consumer Plan Reality:** ChatGPT Plus / Team / Pro subscriptions grant access to interactive browser and IDE interfaces (e.g., OpenAI Canvas, Codex extension). **They do NOT provide a free, unlimited, unattended REST API key.**
- **Usage Windows:** Codex and Work usage is governed by rolling 5-hour interactive windows (initiated at the first prompt after the previous window closes) and global weekly message caps.
- **Strict Prohibition:** Never attempt to scrape web sessions, hijack browser cookies, or reverse-engineer private endpoints to simulate an unattended API. Any programmatic access via OpenAI must use standard API credits (which requires explicit owner financial approval, currently $0.00 budget).
- **Official Guidance:**
  - Managing usage in Work & Codex: <https://help.openai.com/en/articles/20001516-managing-usage-with-gpt-6-astra-in-work-and-codex>
  - Using Codex with your ChatGPT Plan: <https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan>

### 3.2 Google AI Plus, Pro & Gemini Apps
- **Consumer Plan Reality:** Google AI Plus provides consumer access to Gemini Advanced and interactive developer features. It operates under weekly quota policies rather than the 5-hour rolling refresh found in Google AI Pro / Ultra enterprise plans.
- **Clarification:** Do not conflate "Google AI Plus" with "Google AI Pro". Programmatic background access via Google AI Studio / Gemini API CLI is metered separately from the consumer Gemini app.
- **Usage Tracking:** Account limits must be observed via the official console: **Settings → Usage Limits → Usage**.
- **Official Guidance:**
  - Gemini App Usage & Limits: <https://support.google.com/gemini/answer/16275805?hl=en>
  - Google Antigravity Plans & Quotas: <https://antigravity.google/docs/plans>

---

## 4. Quota Telemetry, 90% Wind-Down & Verified Reset Policy

### 4.1 Telemetry Header Collection
Every HTTP response from the Groq API emits rate-limit telemetry headers. The adapter (`company/hosted_inference.py`) must inspect and record:
- `x-ratelimit-limit-requests` (Maximum allowed requests)
- `x-ratelimit-remaining-requests` (Remaining requests in current window)
- `x-ratelimit-reset-requests` (Time until request count resets, e.g., `2m15s` or `18h`)
- `x-ratelimit-limit-tokens` (Maximum allowed tokens per minute)
- `x-ratelimit-remaining-tokens` (Remaining tokens in current minute)
- `x-ratelimit-reset-tokens` (Time until token counter resets)

> [!WARNING]
> **Partial Header Hazard:** Groq headers report per-minute tokens and per-day requests. They do **not** report total rolling daily token consumption (TPD) in response headers. Therefore, the internal runtime ledger must independently tally request and token consumption. **Partial headers must never be treated as proof that unmeasured daily or weekly buckets are open.**

### 4.2 Strictest Applicable Bucket Rule
The quota status is evaluated against all known buckets simultaneously:
$$\text{Consumption Ratio} = \max \left( \frac{\text{Used}_{\text{RPM}}}{\text{Limit}_{\text{RPM}}}, \frac{\text{Used}_{\text{RPD}}}{\text{Limit}_{\text{RPD}}}, \frac{\text{Used}_{\text{TPM}}}{\text{Limit}_{\text{TPM}}}, \frac{\text{Used}_{\text{TPD}}}{\text{Limit}_{\text{TPD}}} \right)$$

### 4.3 Quota State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                           READY                             │
│       All applicable usage buckets are < 90% consumed       │
└──────────────────────────────┬──────────────────────────────┘
                               │
            Any bucket reaches │ Observation missing
            >= 90% consumed    │ or stale
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                         WIND_DOWN                           │
│  - Immediately freeze new task assignment                   │
│  - Allow in-flight task bounded completion (25% safety)     │
│  - Prioritize deterministic local tests & documentation      │
│  - Create atomic hash-linked checkpoint                     │
└──────────────────────────────┬──────────────────────────────┘
                               │ Allowance exhausted or
                               │ in-flight task completed
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXHAUSTED / CHECKPOINT                   │
│  - Model invocation completely suspended                    │
│  - Fail closed: NO paid fallback, NO account switching     │
│  - Record reset timestamp and wait for new window           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Window reset timestamp reached
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        VERIFY_RESET                         │
│  - Clock time ALONE is insufficient                         │
│  - Obtain fresh, authentic telemetry reading                │
│  - Confirm ALL buckets < 90% before transitioning to READY  │
└─────────────────────────────────────────────────────────────┘
```

- **90% Wind-Down Rule:** When any active bucket reaches 90% capacity (e.g., 54,000 of 60,000 daily tokens or 27 of 30 requests/min), no new tasks may be admitted.
- **Bounded Finish Estimator:** An in-flight call may proceed only if `Estimated_Cost * 1.25 <= Remaining_Allowance`. If the remaining allowance cannot guarantee safe completion with a 25% safety buffer, the call is canceled and the task is saved to disk immediately.
- **Verified Reset Rule:** The passage of clock time (e.g., reaching 14:00 Moncton time) does **not** reset provider quotas. A task can resume only after an active telemetry check proves that a new provider quota window has opened and capacity is available.

---

## 5. Account Setup & Zero-Spend Smoke Test Procedure

To enable a safe, manual single-call synthetic smoke test (as authored in `.github/workflows/cloud-model-pilot.yml` and `tools/cloud_model_pilot.py`), the repository owner must execute the following zero-spend administrative onboarding steps:

### 5.1 Owner Step-by-Step Procedure
1. **Account Registration:** Sign in to [GroqCloud Console](https://console.groq.com) using an authorized developer identity.
2. **Verify Free Developer Tier:** Navigate to **Billing & Plans**. Confirm the account is on the **Free Developer Tier**.
   > [!CAUTION]
   > **Do NOT enter a credit card, debit card, bank account, or payment method.** Ensure automatic overage billing and tier upgrades are disabled.
3. **Inspect Active Rate Limits:** Navigate to **Limits**. Confirm that `qwen/qwen3.8-27b` and `openai/gpt-oss-120b` are visible and active with non-zero request/token limits.
4. **Create API Key:**
   - Navigate to **API Keys**.
   - Create a single restricted API key labeled `serenity-ci-smoke-test-2026-11`.
   - Copy the key to your secure local password manager.
5. **Configure GitHub Repository Secrets:**
   - In GitHub: navigate to repository **Settings → Secrets and variables → Actions**.
   - Under **Repository secrets**, click **New repository secret**.
   - Name: `GROQ_API_KEY`.
   - Secret: Paste the API key.
   - Click **Add secret**.
6. **Configure Required Authorization Variables:**
   - Under **Repository variables**, click **New repository variable**.
   - Variable 1: Name `SERENITY_CLOUD_PILOT_ENABLED`, Value `true`.
   - Variable 2: Name `SERENITY_GROQ_FREE_VERIFIED`, Value `true`.
7. **Security Guarantee:**
   - **NEVER** commit the API key to git.
   - **NEVER** paste the API key into GitHub Issues, PR descriptions, comments, or Obsidian notes.
   - If either variable is missing or set to `false`, the CI workflow terminates immediately without network activity.

---

## 6. Provider Readiness & Eligibility Matrix

| Provider / Service | Model ID | Plan Status | Cost Exposure | Quota Verification | Operational Status | Required Owner Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GroqCloud** | `qwen/qwen3.8-27b` | Free Tier (No Card) | $0.00 | Baseline Published (30 RPM / 200k TPD) | `OWNER_ACTION_REQUIRED` | Owner must create account, verify console limits, and set GitHub secret. |
| **GroqCloud** | `openai/gpt-oss-120b` | Free Tier (No Card) | $0.00 | Baseline Published (30 RPM / 200k TPD) | `OWNER_ACTION_REQUIRED` | Same account credentials as Builder. |
| **OpenAI / Codex** | `gpt-4o` / `o1` / `codex` | Plus / Team Subscription | Interactive Subscription (Pre-paid) | Consumer 5-Hour / Weekly Caps | `NOT_SUPPORTED_UNATTENDED` | Use only for manual human-initiated architectural escalations. No unattended API key. |
| **Google Gemini** | `gemini-1.5-pro` / `gemini-2.0` | Google AI Plus | Consumer Subscription | Weekly Consumer Caps | `NOT_SUPPORTED_UNATTENDED` | Use only for manual human-in-the-loop design reviews. No unattended background API. |
| **GitHub Actions** | Standard Linux Runners | Public Repo Inclusion | $0.00 | Unlimited minutes for public open repos; 2,000 min for private | `VERIFIED` | 4-minute workflow execution timeouts enforced in CI configurations. |

---

## 7. Key Findings & Next Actions for Joint Integration

1. **Groq Model IDs Verified:** `qwen/qwen3.8-27b` (Preview) and `openai/gpt-oss-120b` (Production) are official, valid GroqCloud endpoints.
2. **Rate Limit Policy Confirmed:** Safe workday allocation capped at 60,000 tokens per model per 24-hour cycle to guarantee zero overages under free baselines.
3. **Consumer Plan Boundaries Established:** ChatGPT Plus and Google AI Plus are human-in-the-loop tools only; no unattended background API tokens are permitted or assumed.
4. **Handoff to Track C (Engineering):**
   - The technical dispatch engine (`company/hosted_inference.py`) must enforce fail-closed behavior on HTTP 429 and lack of `GROQ_API_KEY`.
   - Quota tracking must maintain an internal SQLite daily token ledger since Groq HTTP response headers do not report rolling daily token consumption.
