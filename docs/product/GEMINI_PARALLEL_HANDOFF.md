# SERENITY / GEMINI PRODUCT TEAM — COMPLETE PROJECT HANDOFF
**Prepared:** 2026-11-14 (America/Moncton)
**GitHub:** https://github.com/Baraka-Hani/Serenity
**Assigned work:** https://github.com/Baraka-Hani/Serenity/issues/27
**Working branch:** `gemini/travel-journey-2026-11-14` (already created from `main`)
**Company program:** https://github.com/Baraka-Hani/Serenity/issues/13
**Product issue:** https://github.com/Baraka-Hani/Serenity/issues/17

## What Serenity is

Serenity is a travel discovery, saving, mapping and trip-planning product. Its
primary customer experience is: **view authentic travel video → identify and
save a destination → see it in a PRIVATE map → plan a trip**. Valuable
extensions include discovery, creator identity, destination ownership,
saved/visited distinctions, messaging and future reusable travel modules.
The product should feel cohesive, fluid, mobile-friendly and dependable.
Do not chase boilerplate output or token usage at the expense of product quality.

The founder is separately building an AI-operated software company around
Serenity. For now your responsibility is **the real travel app and its frontend
tests**, not agent orchestration. You are one department of a larger company.

## Actual architecture (verified from repo docs)

**Current main product:** Python stdlib HTTP server `backend/server.py`;
SQLite and private runtime uploads in ignored `backend/data/`;
HTML/CSS/plain JavaScript PWA at repo root. Server binds to loopback by
default. Source modules include `backend/social.py`,
`backend/trip_locations.py`, `backend/trip_visibility.py`,
`backend/messaging.py` and `backend/studio_import.py`. Privacy and
account ownership are core constraints.

**Separate prototype:** `nomad-canvas/` is React + TypeScript + Vite,
optionally Firebase, with device-local demo mode. DO NOT assume the main
app uses React, React Native, Next.js or Firebase, and do not silently
migrate or combine the two apps.

**Important code paths:**
- `destination-picker.js` — current first-party destination search UI
- `backend/test_destination_picker.js` — associated Node regression suite
- `backend/server.py` — read-only API reference (no auth/route changes)
- `backend/trip_locations.py` — read-only map/destination data
- `backend/trip_visibility.py` — read-only privacy/publication rules
- `docs/ARCHITECTURE.md` and `AGENTS.md` — mandatory architecture/safety rules

Discover other relevant existing product files before implementing. Never
invent an API endpoint or claim a missing integration exists without checking.

## Current state of the company (DO NOT MISREPRESENT)

Company OS development is occurring via unmerged stacked **draft** PRs:
- https://github.com/Baraka-Hani/Serenity/pull/12 — departments, task ledger, Obsidian HQ
- https://github.com/Baraka-Hani/Serenity/pull/21 — engineering/QA mock pipeline and manager quality policy
- https://github.com/Baraka-Hani/Serenity/pull/23 — default-off hosted Qwen/GPT-OSS adapters, quota guard, real-file mock review
- https://github.com/Baraka-Hani/Serenity/pull/25 — offline durable checkpoint and sandbox/quality contracts, two-shift HQ

**These are not part of your `main` base branch.** They are deliberately
separate from the product PR to permit concurrent work. They are NOT
live autonomous employees and no model-generated code is yet executing in
a privileged worker. PR #25 CI passed, but company stack diverged from
`main`. Your product PR must NOT require those draft branches to merge.

**Other work in parallel:** ChatGPT company team branch
`company/parallel-ops-2026-11-14`, GitHub issue #28:
https://github.com/Baraka-Hani/Serenity/issues/28
That team owns `company/**`, operating system test files, quota/CI/trusted
checks and Obsidian operations. Shared integration issue:
https://github.com/Baraka-Hani/Serenity/issues/29

## Gemini team responsibilities / hard file boundary

You may read all non-sensitive source and docs, but **EDIT ONLY**:
1. Root-level PWA frontend JS, CSS, HTML necessary for an approved low-risk
   travel UX enhancement. Preferred first target: `destination-picker.js`.
2. Product-only Node test scripts including `backend/test_destination_picker.js`
   (and new, clearly named product test fixtures).
3. New product-specific docs under `docs/product/` only.

Do not edit `company/**`, `tools/**` company automation,
`.github/workflows/**`, `AGENTS.md`,
`AI_COMPANY_OPERATING_CHARTER.md`, `docs/MODULE*.md`,
`backend/test_module*.py`, auth/session/identity, payments, Firebase
deployment, production SQLite/media, `backend/data/**`, secrets or
permissions. Do not deploy, merge or enable billing.

If a backend endpoint or privacy rule change is required, **STOP that
subtask**, document the exact contract needed, and create/update a GitHub
issue for the owner/ChatGPT integration track. Continue on unrelated safe UI
work instead.

### User-specified governance

Quality first. The founder does not wish to approve each routine feature
commit; Managers may in the future authorize scoped code once actual tests,
independent review, architecture alignment and protected-branch controls
are enforced. They are NOT yet live. Do not treat a mock QA or JSON claim
as valid CI proof. Founder approval is mandatory for new money, credentials,
account/production access, public deployments, private data and material
security/privacy decisions. Default zero new spend.

### Gemini Plus limitations

Use Gemini's available supported editor or coding interfaces. A consumer
Gemini Plus subscription is NOT guaranteed to supply free autonomous API
access, unlimited coding, a five-hour reset, a running server or GitHub
write rights. Do not bypass quotas, fabricate tool runs, or promise unattended
execution. Start the work in a supported Gemini coding session now and
commit only if authenticated/repository access is actually available.

## Concrete work packages (independent; don't wait for ChatGPT)

### G1 — Discovery and tests

Inspect the main PWA navigation and discover where each of these exists:
video/clip view; destination identification; save to user trip/map;
privacy level; map marker; trip-planning interface. Produce a small
**journey integration map** in `docs/product/GEMINI_PRODUCT_REPORT.md`:
- exact existing source path and handler per step
- API path and response contract, based on actual server routes
- what functions today and what is missing or broken
- privacy and owner-data implications; accessibility gaps
- three prioritized, smallest independent improvements.

Run baseline tests using the commands in `AGENTS.md`. Note exact outcome.
No claim of full flow without an automated integration test.

### G2 — One actual user-visible feature

First preference: improve destination picker saved/search response flow
without changing API semantics. Add explicit loading/empty/error UI feedback,
keyboard affordances/accessibility or first-party search regression as
grounded in the actual code. If the current implementation is already
excellent, choose the next lowest-risk missing *frontend* link in the
save-to-map-to-plan journey.

Requirements:
- purposeful visible improvement; no decorative refactor
- preserve original behavior and existing tests; add regression tests
- first-party relative `/api/...` calls; no direct third-party token/client
- clear empty/error/loading states and basic keyboard behavior
- never expose private visited/saved locations by default
- no artificial hardcoded user data or unapproved external SDKs
- no secrets or billing.

### G3 — Verify and deliver

Run relevant Node product tests, and Python tests if permitted/read-only;
the root GitHub CI runs additional Python and React checks. Open **a
DRAFT PR** from `gemini/travel-journey-2026-11-14` into `main`; DO NOT
merge. Report:
- exact modified files and intent
- before/after user behavior
- test commands, actual outcomes and failed/blocked tests
- architecture/API contract or privacy risks
- source head SHA and CI run URL
- rollback steps
- remaining integration dependencies / risks
- any owner-level financial or access request (do not incur costs).

Post PR link and concise status in issue #27. ChatGPT team will perform
cross-team integration checks independently.

## Parallel schedule (Atlantic time; planning windows NOT actual service runs)

**Sat 14 Nov, kickoff ~22:00–23:00:** G1 repository audit/tests and a
standalone PWA change candidate in Gemini; ChatGPT C1 audits company state
and CI evidence independently.

**23:00–00:30:** G2 implement and test bounded UI improvement; ChatGPT C2
implements ops/QC reporting without touching product source.

**Sun 15 Nov, 00:30–02:30:** G3 independent product tests/PR; ChatGPT
validates its own operations PR. Only ongoing, actually initiated and
authorized coding sessions or cloud jobs can progress during these times.

**02:30–07:30:** CI can run when commits/PRs are pushed. There is NO
automatic Gemini coding shift scheduled merely by this document.

**Sunday morning, ~08:00–09:00:** owner compares product UI improvement,
CI, company HQ and integration issue #29, chooses what to merge/deploy later.

The company's desired regular shifts are 09:00–14:00 and 14:00–19:00
America/Moncton, with a 90% quota wind-down per *actual provider meter*
and verified provider reset, NOT assumed reset every five clock hours.

## Deliverable and handoff contract

Use GitHub Issues and PRs as source of truth, not chat context alone.
Never edit another team's branch. For any output, publish these fields
in your PR/issue:
`TEAM`, `ISSUE`, `BASE`, `BRANCH`, `HEAD_SHA`, `FILES`,
`PURPOSE`, `RUN_TESTS`, `CI_RUN`, `REVIEW_STATUS`,
`RISKS`, `BLOCKERS`, `NEXT_ACTION`, `OWNER_COST_APPROVAL`.

For any missing capability, clearly state **not built** rather than
marking it done.

## First task instruction to Gemini

Inspect the actual branch and issue #27 first. Trace the main Serenity
travel journey, choose one low-risk frontend fix and its tests, implement
it on the assigned branch, run tests and open a draft PR. Do not modify
the company OS, secrets, billing, backend auth/privacy or live hosting.
Prioritize user-value and code quality; publish actual evidence when done.
