# C-Track Module T — evidence reconciliation and zero-spend activation preflight

**Status:** implemented on the existing draft [PR #31](https://github.com/Baraka-Hani/Serenity/pull/31). No GitHub main merge, paid service, credentials, registered Docker digest, scheduled agent, or sandbox runtime has been activated.

**Scope:** company engineering/QA infrastructure only. Gemini handles independent noncoding provider, budget, governance and department onboarding in [issue #27](https://github.com/Baraka-Hani/Serenity/issues/27). Joint decisions flow through [issue #29](https://github.com/Baraka-Hani/Serenity/issues/29).

## Real progress in Module T

- `company/sandbox_reconcile.py` binds a completed, checked-in-source Node smoke record to a **single GitHub-owned job** found from `GET /actions/runs/{id}/attempts/{attempt}/jobs`, then to the completed workflow run. It requires exact repository, main branch, workflow ref, head SHA, job and run ID, run attempt, successful named functional-test step, test and app digests, approved image identity and zero code-write permissions. It rejects duplicates, missing pages, wrong attempt, other repositories, mismatched source, model-generated code masquerading as trusted source and unsafe outcomes.
- `company/sandbox_preflight.py` checks the real current Serenity destination-picker JS and test files, their SHA-256 hashes, and the **manual-only owner gate** in the proposed GitHub workflow. It always classifies cloud run, protected main, official image registry verification, Actions spending, provider eligibility and manager writer as **not verified / not enabled**.
- The read-only `company.technical_report` CI artifact now includes `sandbox-preflight.json` and an Obsidian `Serenity HQ/Operations/Sandbox Preflight.md` page showing exact static source/workflow hashes and owner-only blockers.
- `backend/test_module8_sandbox_reconcile.py` and `backend/test_module8_sandbox_preflight.py` exercise false or incomplete job lists, wrong SHA/attempt/job, replay, foreign repo, suspicious workflow changes, missing owner gate, widened permissions and source symlinks. CI runs the tests, verifies the new HQ page and archives it.
- The existing `company/manager_writer.py` draft-PR plan remains bounded to issue #22 and `backend/test_destination_picker.js`, with no GitHub write or merge capability. Synthetic QA and job correlation are deliberately **not** treated as signed runtime attestation or permission to commit.

## Independent status table

| Capability | State | Evidence |
|---|---|---|
| Current checkout's first-party test and app source hashes | **Static scan** | `sandbox-preflight.json` |
| Manual workflow static owner-gate contract | **Static scan** | `company/sandbox_preflight.py` |
| GitHub run-attempt job discovery and matching | **Unit-tested contract** | `backend/test_module8_sandbox_reconcile.py` |
| Sandbox output SHA checks | **Unit-tested contract** | `company/sandbox_attestation.py` |
| Protected `main` rules verified | **Not verified** | Gemini GitHub G2 / owner |
| Exact reviewed official Node image digest | **Not verified** | Owner/admin |
| Account-level Actions free capacity | **Not verified** | Gemini G2 / owner |
| First actual approved network-off Docker run | **Not executed** | Needs approval + main integration |
| One generated-code candidate functional test | **Not executed** | Needs separate authorized test policy |
| Model calls and independent review | **Not activated** | Gemini G1 checks / owner |
| Manager low-risk PR writer | **Disabled** | Initial scoped App + trust required |
| Two unattended five-hour shifts | **Disabled** | Requires durable cloud execution + authorization |
| Cloud checkpoint and Obsidian live sync | **Disabled** | Existing local/CI simulation only |

## Why a successful GitHub job match does not permit commits

The system compares evidence *claimed by a run* against authoritative GitHub job and workflow metadata. The record checksum detects unexpected changes to those bytes, but it cannot prove that a malicious job did not generate fabricated JSON. Likewise, a successful test of known checked-in source is only a **trusted-source smoke**, not a test of a future proposed Qwen-generated patch. Consequently, reconciliation outputs explicitly deny live code writing, draft PR creation, merges, deployment and spending.

Before activating delegation, separately establish protected GitHub workflow and branch rules, a reviewed isolated runner whose inputs and output are authenticated, and a genuinely tested candidate with independently verified exact-commit CI and QA. Authorize narrow GitHub App rights once; managers can then handle ordinary low-risk commits without repeated owner confirmations, but must not grant themselves more privileges.

## Minimum subsequent owner actions

1. Review/reconcile the stacked draft PRs #12 → #21 → #23 → #25 → #31 against newer `main`. The new manual workflow is **not present on main** before its authorized integration; it cannot run as proposed until then.
2. Confirm Actions usage and no additional spending/overages; verify repository ruleset and workflow permission restrictions through Gemini G2 and owner review.
3. Obtain a **real reviewed** Node 22 OCI image digest for the intended platform and verify its registry provenance. Do not invent a digest.
4. Once approved, configure the repository's two **non-secret** gate variables `SERENITY_SANDBOX_OWNER_APPROVED=true` and `SERENITY_APPROVED_NODE_IMAGE=<reviewed digest>`; do not configure them automatically.
5. Manually dispatch one known-source smoke from protected main. The container must have no network or credentials, no privileged Docker socket, and must have readonly filesystem and resource restrictions.
6. After completion, inspect the actual GitHub Actions run, run attempt, job status/step and artifact, then use `sandbox_reconcile.reconcile_smoke_with_github` with read-only GitHub API access. Report the exact SHA, run and job IDs and what they do *and do not* establish.
7. Only **after further separate approval**, move to an actual generated low-risk Serenity candidate; independent QA, full CI, architecture/security regression and delegated manager draft PR remain mandatory.

Run the offline checks without keys, billing or cloud activation:

```bash
python3 backend/test_module8_sandbox_reconcile.py
python3 backend/test_module8_sandbox_preflight.py
python3 -m company.technical_report --source-root . --output /tmp/serenity-readiness-fresh
```

Do not confuse the expiring CI artifact with durable company memory.

## Next technical module

**C-Track Module U — actual approved main-branch smoke and authenticated low-risk candidate pipeline**. Start with verified administrative readiness and a real restricted trusted-source run, then bind a genuinely reviewed/isolated candidate to its exact SHA and independent PR checks before granting any narrow manager rights. Preserve finance, credentials, production/private data, merge and deployment owner controls.
