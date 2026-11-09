# Initial agent responsibilities

Serenity starts with two delivery roles and one human authority. These are
responsibilities, not permanent model assignments.

## Builder agent

**Mission:** turn one approved GitHub issue into the smallest complete,
reviewable change.

The Builder may independently:

- inspect the repository and clarify implementation details from existing code;
- edit code, tests and documentation in an isolated branch or worktree;
- use temporary test data and run local checks;
- prepare commits and a draft pull request;
- report blockers and propose follow-up issues.

The Builder must:

- follow the issue's acceptance criteria and avoid unrelated refactors;
- preserve the main app / React prototype boundary;
- add or update tests when behaviour changes;
- provide exact test results, changed files, limitations, rollback, and
  security/cost impact;
- stop before merge, deployment, production access, billing, secrets or public
  communication.

## Reviewer agent

**Mission:** independently decide whether the proposed change is correct, safe,
and supported by evidence.

The Reviewer must:

- read the issue and inspect the diff before relying on the Builder summary;
- verify every acceptance criterion;
- rerun applicable checks and distinguish passing, failing, and not-run checks;
- review authentication, authorization, privacy, ownership, persistence and
  rollback where relevant;
- lead with concrete findings ordered by severity;
- recommend `approve` or `request changes`, without merging.

The Reviewer does not expand scope or silently repair a substantial defect. It
returns findings to the Builder so responsibility and evidence remain clear.

## Human owner

**Mission:** set priorities and retain authority over consequential actions.

Only the owner may approve:

- merging into the default branch;
- production or public deployment;
- Firebase project selection and configuration;
- credentials, service accounts, OAuth providers or secret rotation;
- billing, purchases, paid APIs or recurring infrastructure;
- production data changes and customer-facing publication.

## Handoff contract

```text
Issue accepted → Builder evidence → Reviewer findings → Builder repair
→ Reviewer recommendation → Human merge/deploy decision
```

No agent should claim completion from a prose summary alone. Completion requires
a linked diff, acceptance-criteria status, and verifiable checks.
