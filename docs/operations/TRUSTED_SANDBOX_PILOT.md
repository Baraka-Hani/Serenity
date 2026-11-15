# Serenity C-Track — Restricted Sandbox Pilot and Delegated Manager PR Plan

**Tracked in:** [Issue #32](https://github.com/Baraka-Hani/Serenity/issues/32)
and [draft technical PR #31](https://github.com/Baraka-Hani/Serenity/pull/31).
**State:** security contracts implemented and tested in CI; **real OCI run
not activated**. Gemini's G1–G4 **noncoding company onboarding** is tracked in
[issue #27](https://github.com/Baraka-Hani/Serenity/issues/27). Technical
coordination is [issue #29](https://github.com/Baraka-Hani/Serenity/issues/29).

## This module's concrete improvements

1. **Hardened host-to-container mount path.** The Docker `--mount` option
   accepts comma-delimited suboptions, so an unvalidated directory name
   could unintentionally add a host mount. The fixed command now accepts
   only a resolved safe absolute path (no comma, colon, newline or parent
   symlink), then mounts exactly the approved two-file readonly workspace.
2. **Reviewed pinned image requirement.** A syntactically valid digest was
   previously sufficient if an owner boolean was supplied. The actual
   runtime now also requires a matching
   `SERENITY_APPROVED_NODE_IMAGE` value. A random digest is not a vetted
   base image. The `--pull=never` test invocation remains unchanged; a
   separately authorized GitHub job preloads the explicitly approved digest.
3. **Manual-only, read-only hosted runner pilot.** The
   `.github/workflows/serenity-candidate-sandbox.yml` workflow runs ONLY
   with explicit `workflow_dispatch`, from protected `main`, when
   `SERENITY_SANDBOX_OWNER_APPROVED=true` AND an exact reviewed image is
   provided as an admin-managed GitHub Actions variable. It uses checkout
   `persist-credentials:false`, `permissions: contents: read`, no
   provider keys, and checks out existing trusted Serenity regression
   source only. It is **not a scheduled agent** or live Qwen/GPT-OSS task.
4. **Honest sandbox smoke artifact.**
   `company/sandbox_smoke.py` checks exact source/test hashes, invokes
   the existing read-only, network-none, rootless-in-container, resource-
   limited Docker command only after gates, and records
   `sandbox-smoke.json`. It labels itself **known checked-in test source**,
   not a model-generated patch, and states that the artifact has not yet
   been independently authenticated by a trusted GitHub job lookup.
5. **Candidate-bound job attestation schema.**
   `company/sandbox_attestation.py` represents source, app and candidate
   SHA-256 digests, pinned image, exact GitHub head, run ID, attempt, job ID,
   test command, exit code and log checksums. This checksum is NOT a
   signature: an attacker controlling the job can forge it. The
   `check_github_job` helper rejects stale or mismatched job IDs, SHAs,
   attempts, unprotected workflow refs, skipped functional-test step, or
   unsuccessful runs. Only independently fetched GitHub job/run metadata
   may be supplied, not model-produced JSON.
6. **Manager quality gate remains blocked until real provenance.**
   `company/technical_readiness.py` can now record whether a claimed
   sandbox run corresponds to a GitHub job, but makes no claim of
   cryptographically authenticated isolation; it **always** sets
   `manager_commit_execution_authorized=false`. Even a synthetic
   all-green PR/QA fixture is `BLOCKED_PENDING_TRUSTED_ISOLATION_ATTESTATION`
   rather than falsely labeled ready.
7. **Independent regression coverage.** The new
   `backend/test_module7_sandbox_attestation.py` and
   `backend/test_module7_sandbox_smoke.py` exercise valid fixture claims,
   tampering, wrong commit, wrong attempt, skipped CI step, mount injection,
   wrong image digest, default-off gate, and no generated-code execution.

## Exact administrative prerequisites for the first *manual* smoke

These are **not yet completed**. Gemini's provider/onboarding team can
validate administrative facts independently and report any blockers.
Only an authorized owner/admin should take initial privileged actions.

1. Review this stacked PR and the main-branch diff before any merge.
   The manual workflow will not run from this draft branch: it is designed
   to be executed *only* from a reviewed protected default branch.
2. Review an official Node 22 image **by verified registry digest** and
   approve exactly the required platform manifest; DO NOT invent/paste
   an arbitrary `sha256:` string. Check Docker/Actions quotas and
   policies before any run to avoid unapproved charges.
3. In GitHub repository Actions variables (not public issues), set
   `SERENITY_APPROVED_NODE_IMAGE` to that **reviewed full digest**,
   and `SERENITY_SANDBOX_OWNER_APPROVED=true` only after the
   preconditions are met. These are feature-gate variables, **not secrets**.
   Do not place credential values in the variables or this repository.
4. Manually dispatch **Serenity reviewed Node sandbox smoke** from
   protected `main`. It will check out main's known test source, preload
   only the reviewed official image, and run the test in a single
   network-disabled read-only Docker container with CPU/memory/PID/time
   limits. It has read-only repository permissions.
5. Independently inspect the GitHub Actions job ID, run attempt, exact
   head SHA, successful `Execute isolated test in network-off Docker`
   step, uploaded `sandbox-smoke.json` artifact and test result. A
   matching artifact checksum alone cannot prove trusted execution.
   Keep the candidate-quality gate closed until a protected trusted
   workflow and evidence-verification authority are audited.

## Important distinction: trusted-source smoke vs future generated-code pilot

This first owner-initiated test uses the **existing, reviewed** Serenity
destination picker test and first-party app source. It does **not**
exercise a new Qwen-generated test, authenticate a GPT-OSS review or
prove future low-risk code quality. An actual generated-code pilot needs:

- A validated candidate patch tied to a real issue and baseline SHA;
- A verified Free-account provider and genuinely distinct model review;
- A trusted workflow that tests the exact **candidate** SHA, without
  granting a Docker socket or secrets to generated code;
- Actual end-to-end Python/JS/React, privacy and architecture checks;
- An independent, reviewable exact-head PR commit and CI evidence;
- A separate initial owner-authorized scoped GitHub App (no paid fallback)
  before enabling a future manager branch writer.

The existing `company/manager_writer.py` remains planning-only:
`write_branch_commit`, `create_draft_pr` and `merge_protected_branch`
all fail closed. Future managers should not need *per-commit* owner approval
for already authorized low-risk tasks, but cannot self-expand budgets,
permissions or production access.

## Verified and unverified definitions

| Category | Honest state |
| --- | --- |
| Existing Serenity product regression tests | Run by normal CI |
| Mount/image threat-model regression tests | CI contracts, no Docker runtime |
| GitHub run and job attestation correspondence | Synthetic contracts; ready for actual API verification |
| Reviewed container image digest | **OWNER VERIFICATION REQUIRED** |
| Manual trusted-source Docker functional smoke | **NOT YET RUN** |
| Generated-code sandbox test | **NOT YET RUN** |
| Qwen/GPT-OSS live inference | **NOT YET AUTHORIZED** |
| GitHub protected branch / App permissions | **NOT CONFIGURED HERE** |
| Manager code-writing agents | **DISABLED** |
| Two shifts / Obsidian HQ | Simulated and reportable; no unattended live workers |
| New financial exposure, merge or deployment | None |

## Next independent technical module

**C-Track Module T — Authorized Trusted Sandbox Execution + real Candidate
Acceptance**. After verified owner setup, execute the trusted-source
smoke once, verify real run metadata and image digest, then implement an
isolated candidate artifact input flow and actual exact-head PR CI job,
while Gemini continues provider/GitHub administrative onboarding.
Never replace actual test evidence with simulated checks or charge paid
APIs without approval.
