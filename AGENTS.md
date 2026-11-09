# Serenity agent instructions

These rules apply to the entire repository. They are designed for a supervised
two-agent pilot: one Builder proposes changes and one Reviewer verifies them.

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
5. A human approves before merge, deployment, publication, or production data
   changes.

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

Agents may independently edit documentation, tests, and application code in an
isolated workspace. Human approval is required before any of the following:

- pushing or merging to the default branch;
- public deployment, Firebase deployment, or changing a live project;
- enabling billing, paid APIs, storage, or purchases;
- adding or rotating credentials, OAuth settings, secrets, or service accounts;
- changing production data, database migrations on real data, or destructive
  cleanup;
- contacting users or publishing content.

Never commit `.env` files, tokens, service-account keys, private media,
`backend/data/`, or user databases. Do not expose port 8765 directly to the
internet.

## Cost controls

- Default task budget: no paid external services and no new infrastructure.
- Record any proposed recurring or usage-based cost before implementation.
- Stop for approval before an action can create charges.
- Optimize for cost per accepted, tested change—not number of agent calls.

## Evidence format

Every Builder handoff should include: changed files, checks run and results,
known limitations, security/cost impact, and rollback instructions. Every
Reviewer response should lead with actionable findings, then list verification
performed and an approve/request-changes recommendation.
