# Serenity Module U — Exact GitHub Trust, Durable Recovery and Manager Rehearsal

**Branch:** `company/module-u-trust-recovery-2026-11`  
**Draft review PR:** [#38](https://github.com/Baraka-Hani/Serenity/pull/38)  
**Company program:** [#13](https://github.com/Baraka-Hani/Serenity/issues/13)  
**Module issue:** [#36](https://github.com/Baraka-Hani/Serenity/issues/36)  
**Gemini noncoding onboarding:** [#27](https://github.com/Baraka-Hani/Serenity/issues/27); integration [#29](https://github.com/Baraka-Hani/Serenity/issues/29)

## Repository state observed before starting

Earlier [PR #12](https://github.com/Baraka-Hani/Serenity/pull/12)
was merged into `main`, and PRs #21, #23, #25 and #31 were merged
into intermediate company branches. PR #31 is **closed/merged**; this
module therefore opened a **new isolated draft PR #38**, targeting
`company/serenity-hq-operating-system`, not `main`.
At inspection, the company branch was 125 commits ahead and 20
behind `main`. No unilateral merge or rebase was performed.

## Technical changes

### U1 — GitHub-bound independent QA, exact candidate and baseline

`company/module_u_evidence.py` provides `inspect_exact_pr()`:

- Reads actual PR metadata, its complete changed-files inventory,
  the exact HEAD SHA's required GitHub Actions job records and
  independent human review **from the fixed GitHub API**.
- Demands precisely one low-risk change to
  `backend/test_destination_picker.js` on a same-repository, open,
  draft, approved `ai/serenity-*` branch based on `main`.
- Retrieves the **actual test file bytes** from immutable base and
  head commit refs. Validates base64, reported byte count, Git blob
  SHA-1 object digest and SHA-256 against expected original and candidate.
- Rejects stale commit SHAs, changed baseline, changed candidate,
  incomplete checks/reviews, duplicate required checks, bot/self-review,
  forks, unapproved/sensitive paths or a fake file hash.
- Produces an **advisory** record only. Even green GitHub metadata cannot
  attest execution of generated code in a protected sandbox. Model review,
  manager commits, draft PR writes, merges and production remain
  **unauthorized** until authenticated runtime evidence and separately
  approved initial credentials exist.

The current `module5-candidate-sandbox` gate in `github_quality.py`
requires a real successful exact-head candidate job, which does
**not yet exist** as a reviewable PR workflow. The manual-only
checked-in-source smoke is not a substitute; the dossier should
**fail closed** on all current candidate PRs rather than inventing
tests. This remains an explicit follow-on dependency.

### U2 — Read-only remote checkpoint recovery, strict Git identity

`company/github_checkpoint.py` now recomputes the actual Git blob
SHA-1 of remote ledger bytes before accepting GitHub's `sha`
metadata. Strict base64 decoding, size caps, optional metadata
length and the event hash chain are also verified.

`company/module_u_recovery.py` supports **opt-in read-only**
retrieval of the single fixed state file
`serenity-company-state/state/company-ledger.json`, using the
existing `GithubCheckpointStore.read()`. It reports
`IN_SYNC`, `REMOTE_AHEAD`, `LOCAL_AHEAD`, `DIVERGED_BLOCKED`,
`REMOTE_READ_BLOCKED` or `REMOTE_NOT_OBSERVED`.
There is **no automatic reconciliation, GitHub write,
state-branch creation, account access grant or cloud activation**.

Unless an approved state branch has been created and genuinely
read, a local checkpoint and an expiring CI artifact are not
evidence of cloud-durable company memory.

### U3 — Deterministic manager draft-PR rehearsal and rollback

`company/module_u_rehearsal.py` uses the **existing Serenity
destination-picker test** and the allowlisted issue #22 manifest.
It produces the source hash, a bounded deterministic mock candidate,
the proposed candidate hash, Git-style local source blob SHA and
a single-file `ai/serenity-issue-22-demo` draft-PR intent.

Its sandbox/QA inputs are **fabricated test fixtures only**,
explicitly labeled in every output; no Qwen/GPT-OSS call, real
sandbox test, reviewer approval, GitHub commit or draft PR
creation occurred during this rehearsal. The existing
`write_branch_commit`/`create_draft_pr`/`merge_protected_branch`
methods continue to **refuse execution**.

The rollback plan references the baseline Git blob but **requires
independent GitHub base verification** before it may be used.
No automatic revert is attempted.

### U4 — Realistic per-model quotas and resumable shifts

`company/module_u_shift.py` uses `America/Moncton`
09:00–14:00 and 14:00–19:00 as organizational windows only.
It refuses missing or simulated Qwen and GPT-OSS usage data,
treats all four applicable request/token minute/day buckets
independently, stops new tasks at the verified 90% usage threshold,
doesn't infer provider reset from the wall clock, and refuses
duplicate Builder work after a QA handoff.

Even fresh manually entered quota numbers **do not grant authority
to call providers**. Account-verified resets, usage provenance,
actual credit access and cost eligibility remain Gemini G1/owner
requirements.

### Obsidian HQ and CI evidence

`company/module_u_report.py` reuses the no-network technical
readiness packet and creates:

- `module-u-report.json`, `manager-pr-rehearsal.json`
- `cloud-recovery.json` and `shift-readiness.json`
- Existing validated `company-checkpoint.json`
- `Serenity HQ/Operations/Cloud Recovery.md`
- `Serenity HQ/Operations/Shift Quotas.md`
- `Serenity HQ/Operations/Manager PR Rehearsal.md`
- New Command Centre links to these three pages

GitHub CI runs five additional focused Python test modules and
archives the resulting Obsidian HQ preview as
`serenity-module-u-hq-readiness` (short-lived artifact).
**CI pass status must be checked on the exact latest branch SHA**;
passing unit tests of fixtures is not equivalent to actual cloud
agent execution.

Local test command (no network, credentials or Docker calls):

```bash
python3 backend/test_module_u_evidence.py
python3 backend/test_module_u_recovery.py
python3 backend/test_module_u_shift.py
python3 backend/test_module_u_rehearsal.py
python3 backend/test_module_u_report.py
python3 -m company.module_u_report \
  --source-root . \
  --output /tmp/serenity-module-u-new
```

The output directory must not exist. This does not install or
modify the user's existing local Obsidian vault; it generates a
new importable snapshot.

## Owner-only gates and actual company activation

No new payment methods, API accounts, secrets, identity privileges,
public deployments, production/private location data, protected
merges or unattended workers were enabled in this module.

To transition to genuine autonomous *routine* coding, complete
official eligible model quota and data terms verification, an
approved isolated runner and candidate-bound test attestation,
exact-head protected PR CI, independent human/security review,
durable cloud state with authorized scoped repository access, a
narrowly delegated GitHub App PR writer and an emergency stop.
After these initial controls are approved and independently
verified, managers may handle ordinary branch commits without
asking the owner for approval each time; owner financial and
high-impact decisions remain reserved.

**Next module:** authenticated runner/CI provenance, safe,
owner-authorized manager branch-commit/draft-PR execution pilot
and Obsidian synchronization from genuinely observed company state.
This module does not claim those results.
