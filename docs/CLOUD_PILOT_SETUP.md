# Serenity Cloud Pilot — Owner Onboarding

**Current stage:** one-call manual synthetic smoke test. No autonomous builder, no cloud code writes, no schedule activation.

## What has been built

- `tools/cloud_model_pilot.py`: network-free simulation by default. A single Groq request in explicitly approved live mode, using only public synthetic Python. It cannot edit the repository or execute generated code.
- `backend/test_cloud_model_pilot.py`: offline safety tests for flags, model allowlist, boundaries and incomplete quota telemetry.
- `.github/workflows/cloud-model-pilot.yml`: manual-only GitHub Actions runner. Read-only repo permission, four-minute timeout, seven-day report artifact, never uses a development/production branch for a live model call.
- `tools/free_model_plan.py`: existing policy-only routing simulator.
- `docs/QUOTA_AWARE_SHIFTS.md` in [proposed PR #11](https://github.com/Baraka-Hani/Serenity/pull/11): 90% wind-down/verified reset policy. It has **not** been connected to live workers, because it cannot read all provider limit buckets automatically.

## Workflow and its restrictions

```text
Owner authorizes provider eligibility, free-only account, limited test
      ↓
GitHub Actions > Serenity manual cloud-model pilot
      ↓
Mode: mock (default) → Python local report → downloadable JSON artifact
      ↓
Mode: live (separate explicit permission):
  owner-set enabled and free verified variables + GitHub secret
      ↓
One selected model + one synthetic snippet, <= 500 output tokens
      ↓
One JSON artifact → owner reviews, no shell execution or PR created
```

**IMPORTANT:** GitHub `workflow_dispatch` becomes available only after this workflow file has been reviewed and merged into the repository's default branch. Running this PR's CI does *not* activate the cloud pilot.

## Stage 1 — No account or credentials required

1. Review [draft PR #10](https://github.com/Baraka-Hani/Serenity/pull/10).
2. Verify the GitHub CI checks passed, including `python3 backend/test_free_model_plan.py` and `python3 backend/test_cloud_model_pilot.py`.
3. Read the policy and results; approve a code merge separately if satisfactory.
4. Once merged and a trusted manual workflow appears under **Actions**, select `mode=mock` and `role=builder` to generate a zero-network report artifact. Repeat with `role=reviewer` if useful.
5. Examine the report: `status=SIMULATED`, `repository_writes=false`, `automatic_new_work_allowed=false` and no secrets.

## Stage 2 — Account and compliance gate (owner only)

The provider is GroqCloud Free. **Only an account holder who meets the provider's eligibility requirements may activate it.** Do not circumvent age requirements, use another person's credentials without authorization, or expose tokens in chat.

Before enabling a live smoke test, the eligible owner/admin must:
- Verify the service terms, data handling, and provider account eligibility.
- Confirm Groq **Free**, with **no billing method, paid upgrade or automatic overages**.
- Confirm in the Groq **Limits** console that `qwen/qwen3.8-27b` and `openai/gpt-oss-120b` are listed, available, and within usage allowance.
- Review GitHub Actions usage and possible charges if the free included compute is exhausted.
- Use synthetic code only. Never upload personal data, credentials, travel history or `backend/data` to the model provider.
- Independently authorize a secret in repository **Settings → Secrets and variables → Actions**: `GROQ_API_KEY`. Never commit it to source or copy it into an Obsidian note.
- Independently authorize repository variables `SERENITY_CLOUD_PILOT_ENABLED=true` and `SERENITY_GROQ_FREE_VERIFIED=true` **only after confirming the conditions**. Removing either flag disables the live run; revoking the secret is a stronger stop.

The script **cannot independently verify billing tier, account eligibility, or every quota window**. Treat the variables as an accountable owner attestation, not as a substitute for provider-side cost controls.

## Stage 3 — Optional manual live smoke test

Only after Stage 2 approval, run the manual workflow on `main` with `mode=live`, `role=builder`. It will issue **one** bounded synthetic prompt to Qwen via HTTPS and return a JSON artifact. Run the reviewer model as a **separate** deliberate manual invocation, not an unattended chained call.

Rate limits:
- No automatic retries on 429.
- One invocation performs at most one model request, with a 20-second timeout and 500-token response cap.
- Provider response headers are captured as a **partial** token/minute and request/day observation. They do not establish the complete five-hour/weekly/daily state. `automatic_new_work_allowed=false` remains in all reports.
- On unavailable models or uncertain quota state, stop; no paid fallback.
- The current free-tier limits and published model listings are at:
  - https://console.groq.com/docs/rate-limits
  - https://console.groq.com/docs/model/qwen/qwen3.8-27b
  - https://console.groq.com/docs/model/openai/gpt-oss-120b
- A provider's published paid API token price does not imply that the free account will be billed. Verify the actual account and conditions.

## Stage 4 — Next construction milestone (not implemented)

Develop a *separate* low-risk patch worker that reads an approved GitHub Issue, loads bounded non-sensitive code context, asks Qwen for a machine-readable proposed diff, validates it in a temporary checkout, runs tests, and passes the diff to GPT-OSS for review. It must:
- accept tasks only from an owner-reviewed allowlist;
- never execute arbitrary model-generated shell commands;
- reject path traversal, symlinks, credential paths, cross-repo writes, or changes to governance/CI files;
- use strict time, context, and output caps;
- checkpoint when any verified provider quota bucket reaches **90% consumption**;
- resume only after a confirmed new quota window, not simply five clock hours later;
- save findings as artifacts first, with GitHub PR creation gated by additional approval;
- keep ChatGPT Plus / Gemini usage as manual critical-review escalation until explicitly supported API access is available.

## Expected department roles

| Department | Model or system | First actual task |
| --- | --- | --- |
| Engineering | Qwen3.8-27B | Synthetic code proposal; later an approved small helper |
| Quality Assurance | GPT-OSS-120B | Independent first-pass critique |
| Executive | GitHub issue backlog, managers and owner | Managers handle verified routine commits; owner handles finance and high-impact decisions |
| Operations | Existing read-only workday scheduler | Reporting (default-off) |
| Architecture and security escalation | ChatGPT Plus / Gemini (interactive) | Human-reviewed decisions only |

An Obsidian HQ view can be generated later from GitHub issues, PRs, and structured model-run JSON artifacts. The pilot's JSON is intentionally suited to this later integration.

## Resume checklist

- [x] Model and role routing manifest written (PR #10)
- [x] Free-only policy simulation written (PR #10)
- [x] Manual synthetic cloud-model script and tests proposed (PR #10)
- [x] Manual GitHub Actions workflow proposed (PR #10)
- [ ] GitHub CI confirms all checks
- [ ] Current draft foundation requires review before merge; future routine code merges can be manager-delegated only after trusted safeguards are verified and enabled
- [ ] Mock workflow runs on default branch
- [ ] Eligible owner/admin verifies free account, quota, terms and GitHub usage
- [ ] Owner authorizes secret and manual live-test variables, if applicable
- [ ] Live synthetic request made and reviewed
- [ ] Real low-risk patch worker designed and tested with no credentials
- [ ] Quota governor integrated with verified provider telemetry
- [ ] Explicit permission for a limited cloud coding pilot
