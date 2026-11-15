# Serenity agent instructions

These rules apply to the entire repository. Serenity uses delegated,
**quality-first** engineering with an independent Builder and Reviewer,
a Chief of Staff and an Architecture reviewer. Managers should not require
the owner to approve every routine code commit. See
[delegated engineering authority](docs/DELEGATED_ENGINEERING_AUTHORITY.md).
The actual autonomous GitHub writer remains disabled until safeguards are verified.

## Product boundaries

- Preserve the existing stack. The main app is a Python/SQLite backend with a
  plain JavaScript PWA. `nomad-canvas/` is a separate React/Vite/Firebase
  prototype.
- Prefer small, reviewable changes over new frameworks or services.
- Keep the main app and `nomad-canvas/` boundaries explicit. Do not silently
  move features or data between them.

## Required workflow

1. Start from a written task with acceptance criteria and a risk level.
2. Work only in an isolated branch or managed worktree.
3. The Builder implements the smallest complete change and records evidence.
4. The Reviewer inspects the diff, reruns relevant checks, and reports findings.
5. For ordinary low-risk work, the Engineering Manager may approve isolated
   branch commits and draft PRs **once every applicable actual test and
   independent QA/architecture gate passes**. A protected-branch low-risk merge
   is only eligible after trusted branch rules, exact-commit CI and integration
   checks are enforced; no such automatic writer is enabled today.
6. The owner approves new financial commitments, credentials/access changes,
   public releases/production deployment, production data and material
   security/privacy/strategic decisions. Do not request individual approval
   for every routine commit.

Agents must not merge their own work or mark a task complete without test or
inspection evidence.

## Verification

Run the checks relevant to the changed area:

```bash
python3 backend/test_server.py
python3 backend/test_messaging.py
python3 backend/test_account_discovery.py
node backend/test_chat_ui.js
node backend/test_destination_picker.js
node backend/test_feed_hub.js
node backend/test_studio_grouping.js
node backend/test_studio_publication.js
cd nomad-canvas && npm install && npm run build
```

If a check cannot run, state the exact reason and do not describe it as passing.
Never use real user data for tests. The backend tests create isolated temporary
data and may bind a localhost port.

## Security and production stops

Agents may independently work on pre-scoped documentation, tests and
application code in isolated workspaces. Managers may authorize **routine
feature-branch commits/PRs** when real CI, independent review, architectural
alignment, code scope and rollback gates are satisfied. Future low-risk merges
may be automated only behind enforced protected-branch rules and validated
trusted evidence; **today's prototype does not push, merge or execute AI code**.

Explicit owner approval remains required for:

- new vendors, billing, paid APIs, compute, storage, purchases, overages or
  spending outside a precisely authorized budget;
- public deployment, Firebase/production deployment or changing a live project;
- adding or rotating credentials, OAuth settings, secrets, service accounts or
  expanding agent permissions;
- production data changes, real database migrations, destructive cleanup,
  sensitive authentication, account/identity or location privacy changes;
- contacting users, publishing public content, and strategic pivots.

**Quality is non-negotiable:** an apparently cheap open-weight patch must pass
the same verification as any premium-model patch. Missing tests or a missing
independent review blocks the commit regardless of model or subscription.

Never commit `.env` files, tokens, service-account keys, private media,
`backend/data/`, or user databases. Do not expose port 8765 directly to the
internet.

## Cost controls

- Default task budget: no paid external services and no new infrastructure.
- Record any proposed recurring or usage-based cost before implementation.
- Stop for approval before an action can create charges.
- Optimize for accepted, tested user value, integration quality and low
  regression rate—not generated lines, number of agent calls or merely
  exhausting subscription credits.
- Use ChatGPT Plus/Codex and Google AI Plus/Gemini for high-leverage
  architecture, integration and critical reviews when supported. Their
  consumer allowances do not imply unattended API access or synchronized
  five-hour resets; respect separate usage and 90%-wind-down policies.

## Evidence format

Every Builder handoff should include: changed files, checks run and results,
known limitations, security/cost impact, and rollback instructions. Every
Reviewer response should lead with actionable findings, then list verification
performed and an approve/request-changes recommendation.
