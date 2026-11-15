# Serenity Parallel Night Shift — ChatGPT and Gemini Integration Plan

**Prepared Nov 14, 2026, America/Moncton.** Product work and company
infrastructure are separate tracks. This is a **task plan**, not proof that
either model or a cloud agent is running while the owner is asleep.

## Actual program and architecture

- GitHub: https://github.com/Baraka-Hani/Serenity
- Master program: https://github.com/Baraka-Hani/Serenity/issues/13
- Main product: Python stdlib + SQLite + plain-JavaScript PWA at repo root
- Separate optional prototype: React + TypeScript + Vite / Firebase in
  `nomad-canvas/` (not the main frontend)
- Customer loop: video → save destination → private map → trip plan
- Company stack remains **unmerged** and has diverged from newer main:
  #12 Company HQ → #21 Engineering OS → #23 Model adapter →
  #25 Durable operations.
- Module 5 CI last verified green: https://github.com/Baraka-Hani/Serenity/actions/runs/43667172013
- Live workers, paid services, GitHub automated writer and 9–5/2-shift
  schedules are **not activated**. The 90% quota policy and cloud state
  adapter are tested but do not constitute live unattended execution.

## Two independent workstreams

| Dimension | Gemini: Product Team | ChatGPT: Company/Operations Team |
| --- | --- | --- |
| GitHub issue | [#27](https://github.com/Baraka-Hani/Serenity/issues/27) | [#28](https://github.com/Baraka-Hani/Serenity/issues/28) |
| Base branch | `main` | `company/module5-durable-quality-operations` |
| Working branch | `gemini/travel-journey-2026-11-14` | `company/parallel-ops-2026-11-14` |
| Source files | Root PWA JS/CSS/HTML, product Node test files, `docs/product/*` | `company/**`, relevant tools, `backend/test_module*.py`, `docs/operations/*` |
| Main goal | Tangible travel journey improvement + actual UI regression tests | Inspectable company QA/CI and task coordination reports |
| Out of scope | Agent/GitHub permissions, worker frameworks, secrets, backend auth/private data | Gemini's product JS/tests, UI CSS, changing application API |
| Output | Draft product PR to `main`, tests and before/after | Draft operations PR to #25 branch, tests, HQ report |
| Owner decision | Only if high impact or financial | New spending/access/production/high-impact; routine work quality-gated |

No concurrent writes to the same branch or file. Each team has its own
base, scope and acceptance criteria. Reviews are cross-team; code edits are
not. When a shared interface change is needed, describe its required
contract in issue [#29](https://github.com/Baraka-Hani/Serenity/issues/29)
instead of editing someone else's files.

## Time-boxed parallel *plan*, not an automation guarantee

All times America/Moncton; at prep time Saturday Nov 14 evening.

| Time | Gemini product tasks (independent) | ChatGPT company tasks (independent) |
| --- | --- | --- |
| Nov 14, ~22:00–23:00 | **G1** inspect main PWA and find one missing journey/UI test; baseline Node checks | **C1** inspect PR stack and build read-only status/morning brief |
| ~23:00–00:30 | **G2** implement one bounded destination/search/save/map UX improvement and test | **C2** add company HQ/operations handoff record and truthful PR metrics |
| Nov 15, 00:30–02:30 | **G3** verify Node/CI and open draft product PR to `main` | **C3** verify company CI and open draft ops PR to #25 |
| 02:30–07:30 | Only already-triggered CI or **approved** active cloud coding jobs may run | Same; no scheduled autonomous AI worker is implied |
| ~08:00–09:00 | Owner reviews genuine UI difference, tests and PR | Owner reviews CI/QA/HQ, spending blockers and merge-readiness issue #29 |

If the user closes both conversations and no approved cloud coding agent has
started, **development does not continue**. ChatGPT Automations can perform
scheduled status checks, not magically consume Plus/Gemini Plus coding
subscriptions as background APIs. Gemini's session must be started by the
owner in its supported coding environment.

The desired regular company shifts are **09:00–14:00 and 14:00–19:00
America/Moncton**. They coordinate work but are not quota resets. Actual
model limits vary; wind down *new* tasks at verified 90% consumption, save
checkpoints and resume only after independent provider reset evidence.

## Gemini exact handoff

The complete handoff lives in Gemini branch at
`docs/product/GEMINI_PARALLEL_HANDOFF.md`:
https://github.com/Baraka-Hani/Serenity/blob/gemini/travel-journey-2026-11-14/docs/product/GEMINI_PARALLEL_HANDOFF.md

The user should paste that text into Gemini, connect to the repo in a
supported interface and ask it to work on issue #27. The presence of a
GitHub branch alone does not connect or activate Gemini.

## ChatGPT C-track independent modules

- **C1 — Evidence and accountability:** read-only GitHub PR/CI status; true
  vs simulated matrix; real head SHAs, not model claims; issue #28
- **C2 — Obsidian headquarters:** strict sanitized read-only report with
  agent department, task, reviewer, CI, quota and pending financial approval
- **C3 — Integration contract:** verify Gemini PR exact changed filenames
  and current main, compare company PR stack, avoid merging divergent bases.
  Raise PR conflict instead of auto-rebasing, stop on sensitive file edits.

Next quality milestone (Module 6 issue #26) remains actual model-approved
code and isolated generated-code functional tests, with a scope-limited
manager PR writer. Nothing here overrides those owner gates.

## Morning evidence / definition of actual progress

The owner should see:
1. **Product:** a URL to a *draft PR*, exact file changes, real tests passed,
   and an explicit before/after user-visible behavior change. CI on main-based
   product branch matters; a mock prototype is not a shipped app.
2. **Company:** separate operations draft PR, QA/CI status, validated
   company event journal/HQ preview, blocked owner financial decisions.
3. **Integration:** issue #29 summarizes nonoverlapping file scopes,
   divergent base review, failures, exact unblock actions and rollback.
4. **Cost:** all unapproved spending stays $0. No keys in repo/issues/vault.
5. **Truthfulness:** don't mark proposed, mocked, CI-checked, merged and
   deployed as interchangeable. No merges/deployments without authorization.

## Escalation and stop gates

Do not add/rotate credentials, enable subscriptions/paid APIs, spend,
expose local port 8765 to the public internet, change Firebase/production
hosting, import real user data, weaken privacy/visibility/ownership, publish
public communications or activate unattended agents without the specific
owner authorization needed. Routine branch commits by managers can be
delegated only after genuinely trusted exact-commit CI, independent review,
privacy and integration gates, and initial scoped permission setup.

Avoid wasted credits: open-weight hosted coding models do boilerplate and
tests; Plus/Codex and Gemini Plus are high-value architecture/QA review
interfaces, not guaranteed unattended APIs. Never bypass account quota or
free-tier requirements.
