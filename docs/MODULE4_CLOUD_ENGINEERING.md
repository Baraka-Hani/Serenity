# Module 4 — Serenity hosted cloud Engineering department

**Stage:** integrated provider + per-model quota + real product test candidate + QA/HQ pipeline.
**Execution state:** **OFF by default**. Source code, credential settings, default branch,
production, billing, and schedules remain unchanged.

## Business objective

Build the Serenity travel app with **purposeful, fully integrated, high-quality**
engineering. Use affordable hosted open-weight inference for routine work, then
reserve ChatGPT Plus/Codex and Google AI Plus/Gemini for difficult integration,
architecture, UX, debugging and security-review decisions through their
supported **interactive** interfaces. This is not an unlimited agent/API
entitlement. The aim is *quality per accepted feature*, not output volume.

[Master company program #13](https://github.com/Baraka-Hani/Serenity/issues/13),
[Engineering #14](https://github.com/Baraka-Hani/Serenity/issues/14), and
[real product QA issue #22](https://github.com/Baraka-Hani/Serenity/issues/22)
are the context for this module.

## Architecture and statuses

```text
GitHub #22 + approved task manifest
          |
          v
READ-ONLY source (backend/test_destination_picker.js)
    + docs/ARCHITECTURE.md (read-only)
          |
          v
Quota governor (each model: requests/minute, requests/day,
              tokens/minute, tokens/day; 90% wind-down)
          |
          v
Qwen3.8-27B Builder -> structured JSON code replacement candidate
          |                (offline deterministic mock by default)
          v
Exact file scope, source SHA-256, original assertion preservation,
bounded inserted assertions, disallowed constructs
          |
          v
GPT-OSS-120B separate Reviewer -> structured QA JSON
          |                (offline deterministic mock by default)
          v
Node `--check` syntax parse only (does NOT execute candidate JS)
          |
          v
SQLite company task, handoff, quota/quality decisions and run evidence
          |
          v
Obsidian HQ / Engineering/module4-*.md, proposed.patch,
builder-output.json, reviewer-output.json, quota-decision.json
          |
          v
Quality gate BLOCKED (no executed tests, trusted QA+CI, or merge authority)
```

### Two actual hosted model IDs (Groq)

| Department role | Model ID | Current integration |
| --- | --- | --- |
| Builder | `qwen/qwen3.8-27b` | Secure single HTTPS structured-response adapter; preview model |
| First independent Reviewer | `openai/gpt-oss-120b` | Separate model, strict JSON schema, no tool execution |

The adapter hardcodes the endpoint and both models, requires explicit **manual
one-task authorization**, verified eligible Free plan, data terms, quota
preflight and secret; refuses redirects, malformed responses, unbounded prompts,
HTTP 429, charge-required responses, and automatic retries. It does not check
billing from the provider account; that is a separate administrative check.

**Provider free-tier quotas are not guaranteed.** Groq publishes baseline
30 RPM, 1,000 RPD, 8,000 TPM and 200,000 TPD for these models, but the exact
account quota must be verified. Its rate-limit response headers describe
RPD and TPM only. The dispatcher refuses to infer that other limits are
available from those incomplete headers. It also does not pretend a Groq
minute/day allowance resets every five hours.

Official docs:
- https://console.groq.com/docs/models
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/structured-outputs
- https://console.groq.com/docs/api-reference

## Run the complete zero-network test locally or through CI

From the repository root:

```bash
python3 backend/test_module4_providers.py
python3 backend/test_module4_pipeline.py
python3 -m company.module4_pipeline \
  --task config/module4_destination_task.json \
  --root . \
  --artifacts /tmp/serenity-module4-new \
  --db /tmp/serenity-module4.sqlite3
```

Requires Python 3.11 and Node 22. The output directory must not already
exist. This only reads two approved public source files. It writes a **candidate
artifact**, an offline SQLite ledger and an Obsidian vault, not the repository.
The module is also part of the normal
[`Serenity checks`](../.github/workflows/ci.yml) GitHub workflow. After a
separately approved merge, `Module 4 manual engineering evidence` can run
without the owner's computer; it uses no model keys and only mock models.

Generated artifact inventory:
- `proposed.patch`: existing destination-picker regression file diff
- `backend/test_destination_picker.js`: isolated candidate copy only
- `builder-output.json` and `reviewer-output.json`: structured mock or
  explicit manual model data with honest provenance
- `quota-decision.json`: separate quota assessments for Builder and Reviewer
- `module4-report.json`: issue, source SHA, architecture SHA, candidate SHA,
  syntax-only check, QA verdict and blocked manager gate
- `obsidian-vault/Serenity HQ/`: department handoffs, task, manager quality
  decision and Module 4 evidence

### Why a successful mock is NOT a code-quality approval

The source used is *real* Serenity test code and the task corresponds to a
*real* GitHub issue. In mock mode, however, Qwen/GPT-OSS are not invoked and
the model outputs are deterministic fixtures. A passing `node --check` parses
JavaScript syntax but does **not run** the proposed test. Existing repository
CI continues testing **unchanged** product code. Neither a simulated review nor
the current CI evidence authorizes a manager commit. The candidate remains
`IN_REVIEW`.

This deliberately protects against the unsafe pattern of executing arbitrary
LLM-generated JavaScript directly in a privileged GitHub Actions runner.
Before running generated tests, implement a separate isolated, network-
restricted, permission-limited runner, and prove integration and regression
checks. This is a follow-up milestone, not silently bypassed here.

## Manual hosted inference — future owner/eligible admin gate

The Python adapter and CLI support a **separately authorized** manual live
pair on issue #22. It has **NOT** been activated. For a future eligible owner
or administrator to authorize this, all of the following must be true:

1. Verify age/terms eligibility and account region with the provider; do not
   circumvent service requirements.
2. Verify a genuine Free plan, no payment/overage exposure, and that model IDs
   and quotas are actually available.
3. Review privacy/data handling and consent to send only the allowlisted
   non-sensitive test source and architecture text.
4. Authorize the provider key in an appropriate restricted secret store; no
   tokens or provider account details in GitHub issues or Obsidian.
5. Provide fresh, **complete** and account-confirmed quota snapshots for
   both models covering the four relevant Groq rate-limit scopes.
6. Explicitly approve one bounded *manual* task run (not a daily cron,
   continuous worker, or standing background agent).
7. Require logged responses, no retries, 90% stop/reserve checks and verified
   next-window evidence. A provider response's partial headers must not
   automatically greenlight future jobs.

The CLI has flags for these future manual operations, but no secrets have been
created and no live requests executed. Even when enabled, **this is only a
review-candidate flow**, not autonomous code execution, commits or deployment.
For developer safety, prefer testing the separately scoped
[`cloud_model_pilot.py`](../tools/cloud_model_pilot.py) synthetic one-request
workflow before enabling the real-source pair.

## Owner / manager decision boundaries

- Engineering Manager may eventually commit **routine** work after all actual
  independently verified CI, security/privacy, architecture, targeted user
  acceptance and rollback gates, **not** per-commit owner approvals.
- Current `company/quality_gate.py` is advisory and never performs GitHub
  writes. Untrusted model claims, manually typed JSON and passing mock tests
  are insufficient.
- New spending, credentials/access, sensitive private locations, payments,
  production data, production/public deployment and material strategic change
  still require specific owner authorization.
- ChatGPT Plus/Codex and Google AI Plus are reserved for high-value
  architecture/integration reasoning and secondary verification. Their
  consumer usage is not assumed to supply background API capacity.
- Work windows 09:00–14:00 and 14:00–19:00 Atlantic are organizational. The
  90% threshold is on each *model's actual applicable usage bucket*, not 90%
  of a five-hour clock timer. Resume only on a verified reset.

## Next module after Module 4

**Module 5 — Durable autonomous shifts + trusted GitHub-quality integration**:
introduce an approved remotely durable event/approval store, a true provider
quota reader and verified reset, an isolated test executor for candidate code,
authenticated CI/head-SHA/independent-review validation, and the scoped
manager commit/PR writer. Add read-only Obsidian synchronization and keep
production deploy/billing owner-gated. Nothing should be activated before
these controls and required owner authorization are in place.
