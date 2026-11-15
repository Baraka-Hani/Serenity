# Serenity: two hosted open-weight models — zero-spend pilot

**Status:** proposal only; no agents are enabled. **Prepared:** 2026-11-14.

## Mission and constraints

Use two cloud-hosted open-weight coding models to prepare **low-risk, verifiable** code while the owner's Mac is offline. Reserve ChatGPT Plus/Codex and Google AI Plus/Gemini for human-initiated architecture, critical reviews, and escalation. Claude Code is not a dependency. All work remains subject to [AGENTS.md](../AGENTS.md) and [AI_COMPANY_OPERATING_CHARTER.md](../AI_COMPANY_OPERATING_CHARTER.md); the stricter rule wins.

Zero new subscriptions, zero paid inference, zero unsupervised production access. An unavailable free model must BLOCK its task, not silently switch to paid inference. An agent role is a persisted responsibility, not a dedicated paid seat or continuous 8-hour process.

## Selected free-hosted models (subject to service eligibility and account verification)

| Role | Provider | Exact API model ID | Scope | Stability |
| --- | --- | --- | --- | --- |
| Builder | GroqCloud Free | `qwen/qwen3.8-27b` | Boilerplate, isolated UI helpers, docs, test fixtures, simple refactoring | **Preview; may disappear** |
| First-pass verifier / backup builder | GroqCloud Free | `openai/gpt-oss-120b` | Review generated diff, suggest regression tests, explain errors, prepare repairs | Production-designated |

Qwen3.8-27B and GPT-OSS-120B weights use Apache-2.0 licensing. The *hosted service* is not open-source and its own terms apply. Both run remotely; neither requires inference on the owner's Mac. Groq Free is rate-limited; published baseline for each model is 30 requests/minute, 1,000 requests/day, 8,000 tokens/minute, and 200,000 tokens/day. These are not guaranteed individual account entitlements; check the actual Limits page. Plan for at most **60,000 tokens per model per workday**, with output and prompt lengths capped, and stop on HTTP 429/413 without retry storms. Preserve a contingency to replace preview Qwen with another approved free model.

- Groq free limits: https://console.groq.com/docs/rate-limits
- Groq model list: https://console.groq.com/docs/models
- Groq free billing: https://console.groq.com/docs/billing-faqs
- Qwen model: https://console.groq.com/docs/model/qwen/qwen3.8-27b
- GPT OSS model: https://console.groq.com/docs/model/openai/gpt-oss-120b
- Groq service eligibility: https://console.groq.com/docs/legal/services-agreement

**Service eligibility:** The provider may impose age, jurisdictional and organizational requirements; only an eligible authorized account holder may activate the service. Do not circumvent eligibility or share credentials. Setup steps below are contingent on eligibility.

## Role routing

1. Executive/manager (initially GitHub Issues + existing scripts): selects a task with an owner-approved acceptance checklist and low risk.
2. Qwen Builder: works from relevant file excerpts, never the entire repository or private data; proposes changes only in an isolated working branch.
3. Automated checks: deterministic repository tests and lint/build checks. Failing checks block handoff.
4. GPT-OSS reviewer: checks the exact task, diff, and test outcomes; requests focused corrections. It is not a substitute for automated tests or independent critical review.
5. ChatGPT Plus/Codex or Gemini: **user-initiated** escalation for auth, Firebase rules, public/private travel content, location privacy, security or architectural boundary changes. Consumer subscriptions do not automatically grant unattended API access.
6. Owner: approves all merges, deployment, finance, credentials, publication and any production changes.

Allowed low-risk types: documentation, test generation, UI scaffold with no auth or data migration, non-sensitive refactoring, isolated utility functions. **Every output must be verifiable** even when simple. Forbidden to unattended models: authentication/session handling, payment integrations, visibility/privacy controls, real-location tracking, destructive database operations, secrets, deployments, and repository governance changes.

## Cloud execution while the Mac is off

Hosted inference alone does not execute tasks. A **remote runner/orchestrator** still needs to prepare repository context, call the model, run tests, checkpoint and create reviewable artifacts. Existing `.github/workflows/workday.yml` is disabled and read-only; it only creates reports. Keep it unchanged.

Initial deployment path:
- Step A: run a **manual, no-network dry run** using `config/ai_company_models.json` and `tools/free_model_plan.py`. This can be tested in CI.
- Step B: after provider eligibility/terms, privacy and GitHub minutes approval, store a restricted API key as a GitHub Actions secret, not in Obsidian, code, issues or logs. Explicitly enable a narrowly scoped manual API smoke test (new workflow, not today's report workflow).
- Step C: test a single **read-only model response** on synthetic public code, using a hard token/output budget and safe error handling. No changes are pushed to default branch.
- Step D: allow a separately reviewed short-lived GitHub Actions build job that creates an isolated branch/PR only for approved low-risk tasks. Keep manual-only until QA passes; schedule later with explicit owner authorization.

GitHub Actions is software-project CI, not a general-purpose 24/7 server. Use short tasks, observe platform use policy and compute limits, and do not run eight hours of idle jobs. Scheduled jobs may be delayed or dropped. Never assume free quotas are contractually guaranteed.

- Actions billing: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- Actions terms: https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features
- Scheduled workflow limitations: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

## Proposed two five-hour shifts per day (America/Moncton)

| Local time | Department | Action | Default |
| --- | --- | --- | --- |
| 09:00 | Executive | Shift 1 intake; restore queue and select approved low-risk items | proposal only |
| 09:15–12:00 | Engineering / Qwen | Create small patch candidates and tests | disabled |
| 12:00–14:00 | QA / GPT-OSS | Review results, checkpoint, and prepare 14:00 handoff | disabled |
| 14:00 | Executive / Operations | Shift 1 closes; Shift 2 resumes eligible checkpointed work | disabled |
| 14:15–17:00 | Engineering / Qwen | Perform corrections and remaining authorized tasks | disabled |
| 17:00–19:00 | QA / GPT-OSS | Run final checks and prepare owner approvals | disabled |
| 19:00 | Operations | Final evidence-backed report | existing read-only tool |

The windows apply **every day, including weekends**: Shift 1 is 09:00–14:00, Shift 2 is 14:00–19:00. These are operating windows, **not** guarantees of 10 hours of inference, free compute, or subscription allowance resets. The existing shift scheduler is default-off and only creates read-only artifacts.

## Department handoff envelope

Example structured record, suitable for future Obsidian rendering:

```json
{
  "task_id": "SERENITY-EXAMPLE",
  "from_department": "Engineering",
  "to_department": "QA",
  "role": "builder",
  "model_id": "qwen/qwen3.8-27b",
  "status": "READY_FOR_REVIEW",
  "branch": "agent/example-only",
  "artifact_links": [],
  "tests": {"result": "not-run"},
  "cost_usd": 0,
  "quota_status": "unverified",
  "owner_action": "review-required"
}
```

Use GitHub as source of truth for code/issues/PRs, a structured event ledger for messages and checkpoints, and Obsidian as a **read-only/synchronized view** of department activity. Avoid simultaneous direct edits to the same vault note by multiple agents.

## Google and ChatGPT integration

- ChatGPT Plus/Codex: manual review/architecture after a passing open-model candidate; protect included usage. No assumption of free programmable OpenAI API.
- Google AI Plus (consumer) is **not** Google AI Pro. Verify the actual plan before assuming Antigravity/Jules quotas. Consumer Gemini Code Assist + Gemini CLI Google-login workflow was retired in June 2026; Antigravity is the current consumer coding route. Paid consumer plans do not necessarily confer free unrestricted automation API access.
- Gemini Developer API free tiers, where eligible, are separate from Google AI Plus subscription entitlement, with their own rates and data terms.
- No Claude Code is required in initial deployment.

Official Google sources:
https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
https://antigravity.google/pricing
https://gemini.google/ca/subscriptions/
https://ai.google.dev/gemini-api/docs/pricing

## Gates before enabling external access

- [ ] Owner verifies provider eligibility, data terms, and acceptable code sharing.
- [ ] Owner verifies no paid plan or payment method is needed.
- [ ] Owner reviews GitHub Actions usage and available quota.
- [ ] Owner authorizes secret creation, limited permissions and per-task caps.
- [ ] No personally identifiable data, real user content, secrets or `backend/data/` sent.
- [ ] Dry-run tests pass in CI.
- [ ] First real generation uses synthetic code only.
- [ ] QA verifies output; owner separately authorizes repository writes.
- [ ] Owner explicitly enables any schedule; emergency-stop validated.

## Onboarding stages: revised sequence

1. **Now:** approve this proposal and run the no-network dispatch simulation.
2. **Next 30–60 minutes:** establish eligible provider account/key, inspect exact free quotas and data controls (owner only); add secret only after authorization.
3. **Next session:** manual synthetic-code API smoke test; verify request/response token caps and 429 behavior.
4. **Following session:** implement one isolated low-risk Serenity task with Qwen; GPT-OSS reviews; deterministic tests; owner reviews draft PR.
5. **Following session:** create a small append-only event ledger and generate Obsidian HQ notes from it.
6. **Later:** test short scheduled cloud CI jobs, checkpoint recovery, no-spend failsafe and emergency stop; only then authorize limited 9–5 activity.
7. **After two weeks:** compare accepted tested work per token, defects and supervision time, then consider extra hosted providers or a paid plan if evidence justifies it.

**This document is a plan, not a declaration that cloud agents are running.**