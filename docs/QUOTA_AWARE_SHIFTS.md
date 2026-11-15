# Serenity: 90% quota-aware shifts and verified reset policy

**Proposed operating policy, 2026-11-14.** Shift windows are 09:00–14:00 and 14:00–19:00 **every day**, in `America/Moncton`. Each window is five clock hours for organizational handoffs. **They do not define or reset provider usage limits.**

## Why time alone is insufficient

- **ChatGPT Plus / Work / Codex:** the applicable five-hour Work/Codex window begins with the first request after the previous one ends; allowance may be exhausted earlier, and a separate *weekly* allowance can also stop work. Inspect **Settings → Usage** or Codex CLI `/status`. No authenticated, supported unattended read API for a personal subscription is assumed; never scrape cookies or simulate a personal login.
- **Gemini Apps:** consumer five-hour and weekly usage limits may apply. The Gemini app's **Settings → Usage Limits → Usage** shows the account's current limits. This app allowance must not be presumed to pay for a background API.
- **Google Antigravity:** **paid Google AI Pro/Ultra** offer five-hour refreshed baseline quotas plus weekly caps; **Free/AI Plus** have primarily weekly quota policies. Check the actual subscription, Antigravity's usage display, and the current product policy; do not infer eligibility from the generic name “Gemini Plus”.
- **GroqCloud Free (hosted open-weight Qwen/GPT-OSS):** provider quota may be specified per minute or day; it is **not** a five-hour reset. HTTP rate-limit headers report requests/day and tokens/minute. Other rate limits and account restrictions must also be considered, using the provider's limits dashboard and a reliable consumption ledger.

Official references:
- https://help.openai.com/en/articles/20001516-managing-usage-with-gpt-6-astra-in-work-and-codex
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://support.google.com/gemini/answer/16275805?hl=en
- https://antigravity.google/docs/plans
- https://console.groq.com/docs/rate-limits

**No provider guarantees two automatic resets corresponding to 09:00 and 14:00.** A five-hour quota bucket may start at a different time and may be exhausted well before its reset. If the verified reset happens after 14:00, Shift 2 resumes only then; if not restored that day, the task remains paused. A provider's weekly, daily, or other bucket may remain restrictive even after its five-hour bucket resets.

## State machine: use the strictest applicable quota bucket per model

```text
READY (each applicable usage bucket is <90% consumed)
  ├── low-risk new work and preapproved work only
  ├── 90% reached in ANY applicable bucket ─> WIND_DOWN
  └── observation missing/stale/untrusted ─> UNKNOWN (pause)

WIND_DOWN (>=90% used but some verified allowance remains)
  ├── stop assigning new work to that model immediately
  ├── finish only bounded in-flight calls after a conservative estimate
  ├── prioritize deterministic tests and documentation (without model calls)
  ├── checkpoint task/branch/diff/evidence/reviewer findings
  └── allowance exhausted ─> EXHAUSTED; reset timestamp reached ─> VERIFY_RESET

EXHAUSTED / VERIFY_RESET / UNKNOWN
  ├── do not assume elapsed clock time restores model access
  ├── no paid overage, account switching, scraping or rate-limit circumvention
  └── fresh permitted usage reading + new quota window ID
       + all other applicable buckets <90% used ─> READY
```

The **90% threshold means 90% of the applicable usage allowance consumed**, *not 90% of elapsed time*. Evaluate all documented quotas, including weekly caps. No workload should be admitted without a reliable recent quota observation. If the provider only exposes reset time at the limit, or the percentage cannot be measured, status is `UNKNOWN`; suspend quota-sensitive automated calls and request an authorized human observation.

At 90%, reserve the final 10% **only for estimated, bounded completion**, not fresh features. If the estimated remaining cost is uncertain, checkpoint before a further model call. Abort on 429/limit response and record the next retry time; never launch retry storms. A *model's* limit pauses that model, not all departments; available non-model work or a separately eligible model may continue according to approved routing.

## What is implemented now

`tools/quota_guard.py` is a **pure, offline policy evaluator** for a structured quota observation. It reports:

- `READY`, `WIND_DOWN`, `EXHAUSTED`, `RESET_VERIFICATION_REQUIRED`, or `UNKNOWN`;
- the most restrictive quota bucket(s) and reset timestamps;
- whether **new work should be queued** or an **in-flight task should checkpoint**;
- whether the preceding saturated bucket has demonstrably moved to a new window before recommending resumption.

**Every output explicitly says `model_calls_authorized: false`**. It cannot itself read ChatGPT/Gemini accounts, invoke AI providers, create a PR, access secrets, purchase credits or start unattended jobs. Sample JSON is invented demonstration data, **not actual subscription quota telemetry**.

### Manual simulation

```bash
python3 tools/quota_guard.py config/quota_example_codex.json --now 2026-11-14T13:02:00Z
python3 tools/quota_guard.py config/quota_example_codex_refreshed.json --previous config/quota_example_codex.json --now 2026-11-14T18:02:00Z
python3 backend/test_quota_guard.py
```

## Real agent handoff requirements (future approval required)

When a trusted usage adapter exists and an actual task executor is approved, the orchestrator must persist:

`task_id, department, model/provider, quota_source, observed_at, window_id, quotas/remaining, reset_at, status, commit/worktree, tests, blockers, context summary, next_safe_action, owner_decisions`.

The task manager must:
1. query **each** model's supported usage source before new work and before each substantial subsequent call;
2. stop admitting fresh tasks at 90% on any applicable bucket;
3. require an estimated completion cost with safety margin before remaining in-flight model calls; otherwise checkpoint;
4. allow deterministic tests, writing documentation and safe bookkeeping **without** model calls while paused;
5. on a reset, observe a **new provider window** with refreshed allowance and check all other active quotas; compare to the prior checkpoint;
6. resume the previous unfinished task before assigning new work; avoid duplicate external side effects;
7. record model-attributed time and token/usage evidence to GitHub/Obsidian later, without private data;
8. keep every merge, deployment, new credentials, spending, publication and production edit human-approved.

**Use provider-specific adapters** in future. A manual observation can inform a human, but it is **not sufficient to authorize an unattended background runner**. Do not run model calls using a personal ChatGPT/Gemini subscription by borrowing browser cookies or undocumented endpoints. For Groq, approved API credentials and response headers are the intended path, subject to account eligibility and free-tier limits.

## What stays unchanged

`.github/workflows/workday.yml` remains **default-off**, read-only and without any LLM call. Its 09:00/14:00/19:00 events are reporting checkpoints only. It does not wake a model just because 14:00 arrived.

Next steps after owner review: verify the unit tests and existing GitHub CI; test a provider-approved read-only quota adapter with synthetic data; prove the 90% transition and new-window recovery; then trial a single narrowly authorized coding job with free hosted inference. No automatic activation is implied.
