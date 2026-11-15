# Serenity: delegated engineering authority and quality-first model allocation

**Proposed charter amendment v1.2 — 2026-11-14.** Owner direction: AI managers
should run routine software delivery without requiring individual approval for
each commit, provided every defined quality gate passes. **Financial decisions
remain with the owner.** No GitHub-writing executor is activated by this
documentation. [Company charter](../AI_COMPANY_OPERATING_CHARTER.md) and
[repository agent rules](../AGENTS.md) apply throughout.

## Organizational philosophy

Serenity is built to be reliable and integrated, not merely to generate a lot
of code. Assess work by **verified user value, maintainability, architecture
coherence, privacy, security, reproducible tests and regression risk**. Do not
maximize raw lines of code, volume of prompts, or consumed credits.

Managers own execution, review, refinement and audit trails. The owner
specifies product direction and budgets and decides matters with material
security, financial, publication or production consequences.

## Delegated approval tiers (target policy, not enabled execution)

| Class | Typical work | Who may approve repository actions after verified gates |
| --- | --- | --- |
| Routine / low risk | Docs, tests, pure utilities, isolated visual UI, safe refactors | Engineering Manager may commit to isolated branch and create/update draft PR without owner sign-off; may merge low-risk PR only when *future approved* protected-branch enforcement verifies all gates |
| Integration / medium risk | Cross-module APIs, larger UI flows, data contract changes | Engineering + Architecture + independent QA must review. Branch commits may proceed after verified checks; protected merge depends on policy and additional specialist evidence; owner is informed, not asked about every line |
| Sensitive / high impact | Auth, private locations, payment, identity, permissions, production data, credentials, public release, major migrations | Human specialist and owner gate before affected high-impact actions; routine unaffected work may continue |
| Financial | New vendors, paid inference, usage overages, compute, storage, subscriptions, renewals, unapproved budgets | **Owner approval required**; default **zero new spending** |

**Commit ≠ merge ≠ deploy**. Routine commits to a feature branch are within
delegated scope once the following gate is actually enforced; a protected
branch merge adds stronger integration checks, and a production deployment
or new spending remains a separate decision. No model may edit the
permissions/guardrails that grant itself broader authority.

## Mandatory pre-commit / PR / merge quality evidence

1. **Purpose:** the issue explains user benefit, intended behavior, tradeoffs,
   clear acceptance criteria, relevant architecture contracts and scope.
2. **Source control:** isolated branch or worktree, changed-file inventory,
   bounded diff, approved code areas only, no data or secrets leakage.
3. **Reproducible verification:** all relevant Python tests, JS browser tests,
   React/Vite typecheck/build, targeted regression tests, dependency/security
   checks, and privacy controls; each has a link to actual completed CI.
4. **Independent QA:** a Reviewer other than the Builder inspects exact diff,
   risk, tests, interfaces, integration edge cases, failure modes and rollback.
5. **Architecture:** cross-module contracts and component reuse remain consistent
   with Serenity's existing Python/PWA and React/Firebase prototype boundaries;
   if interfaces change, consumers are tested before approval.
6. **Documentation:** changed APIs and behavior documented; design decisions
   linked to existing company charter; reviewer records findings and fixes.
7. **Evidence provenance:** capture exact source SHA, PR/diff, model/provider,
   checks, QA verdict and any confidence limits; no fabricated pass statuses.
8. **Cost boundary:** no new financial exposure unless explicitly preapproved
   and within precise remaining budget; failing provider quota causes
   checkpoint, not a paid fallback.

For **manager-authorized low-risk merge**, also require enforced GitHub branch
rules, full green CI for the exact head SHA, passing integration smoke test,
verified review independence, issue acceptance met, and no sensitive files.
Any missing evidence blocks the action; do not treat a Boolean in an untrusted
issue or model output as proof of completion.

`company/quality_gate.py` expresses a **conservative offline policy** and
returns `execution_authorized=false` for every evaluation. It cannot
verify actual GitHub CI provenance by itself. A future trusted adapter must
validate GitHub run IDs, head SHA, reviewer identity, branch protection,
permissions and file classification before automating any push or merge.

## AI model allocation — quality over artificial quota exhaustion

| System | Intended role | How it is used today |
| --- | --- | --- |
| Groq-hosted open-weight Qwen builder | High-volume implementation, tests, components, refactors under verified safe scope | Separate synthetic/manual pilot; no live autopilot configured |
| Groq-hosted GPT-OSS reviewer | First-pass independent analysis and test-gap detection | Separate synthetic/manual pilot; not a completed QA gate |
| ChatGPT Plus / Codex / Work | Architectural integration, difficult bugs, release-blocking failures, complicated code review, acceptance reasoning | Human-initiated in supported ChatGPT/Codex interfaces; no assumed free unattended API |
| Google AI Plus / Gemini / Antigravity | Second perspective for feature design, UI flows, integration and regressions; model-assisted test critique | Human-initiated only via current plan-supported tools; **AI Plus is not AI Pro** |
| Deterministic CI and security tools | Tests, lint, typecheck, dependency/privacy checks, source verification | Mandatory for every change regardless of AI model |

**Do not consume expensive credits solely to consume credits.** Allocate
ChatGPT and Gemini capacity to the highest-value remaining unresolved review
questions. A local Chief of Staff records unresolved issues, PR diffs and
architecture context so the next supported session can start where the
previous ended. Share bounded diffs and relevant interfaces rather than
repeated entire-repository dumps. Use a second model on integration-critical
or uncertain work, not blindly on every tiny doc change.

Work windows are **09:00–14:00** and **14:00–19:00 America/Moncton**
seven days/week, but model usage buckets differ and are not guaranteed to
reset at the shift boundary. Maintain a **90% consumption wind-down** for
each verifiable model allowance bucket; reserve remaining capacity only for
bounded completion and handoff. Record model and review effort, accepted PRs,
regressions found, repair cycles, and model costs.

### Subscription access caveats

- ChatGPT Plus/Codex uses account-specific five-hour and weekly limits. Check
  ChatGPT Settings → Usage or supported Codex `/status` for the actual
  allowance. Plus is **not** an unlimited programmable OpenAI API.
- As of November 2026, Google AI Pro/Ultra have Antigravity five-hour
  refreshes subject to other limits, whereas **Free/AI Plus** have primarily
  weekly quotas. The consumer Gemini CLI Google-login route was sunset;
  verify Antigravity eligibility and current account quotas. The Google AI
  subscription is not automatically a Gemini Developer API budget.
- GroqCloud's Free API has separate per-minute/day caps; it is not a
  five-hour credit bucket. Use provider-approved access and an account
  eligibility check. No paid overage or rate-limit circumvention.

Official sources:
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://help.openai.com/en/articles/20001516-managing-usage-with-gpt-6-astra-in-work-and-codex
- https://www.antigravity.google/docs/plans/
- https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
- https://console.groq.com/docs/rate-limits

## Manager decision and reporting protocol

```text
approved backlog and architecture spec
      |
      v
 Builder in isolated branch -> targeted checks
      |
      v
 independent QA -> CI tests -> architecture consistency check
      |
      +-- FAIL: assign precise repair, checkpoint, rerun
      |
      +-- PASS: Manager may authorize ordinary feature-branch commit/PR
                         |
                         +-- low-risk protected merge:
                         |    if actual CI, rules, independent review and
                         |    integration smoke all verified
                         |
                         +-- sensitive/financial/public release:
                              request owner approval; move to safe work
```

The 7 PM report must distinguish **proposed**, **generated**, **tested**,
**reviewed**, **committed**, **merged**, **deployed** and **actually used**.
Notify the owner of major regressions or spending requests; do not send a
new approval request for each routine commit.

## Deployment and autonomy gates still outstanding

This policy is **not** permission to switch on untrusted shell execution
or hosted agent access today. Before activation:

- Trusted permission-scoped GitHub manager writer, immutable decision audit,
  CI and head-SHA verification, branch protection and emergency stop;
- Bounded model runner in a secure, network-restricted sandbox and separate
  test runner; genuine QA independence;
- Supported provider-account eligibility and quota tracking (90% guard);
- Cloud-durable company ledger and idempotent recovery between shifts;
- Owner authorization for any net-new secrets, billing, production access,
  public deployment or material high-impact modification.

The current engineering demonstration deliberately remains **static-only**,
with no Github write, no actual model calls and no external billing.
