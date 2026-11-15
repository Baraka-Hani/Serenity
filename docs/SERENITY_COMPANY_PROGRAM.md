# Serenity Company — Operating System and Product Roadmap

**Program status:** implementation foundation in review; autonomous execution **disabled**.
**Owner:** human company founder.
**Primary product:** Serenity travel app.
**Longer-term business:** reusable AI-assisted app-building platform, validated through Serenity and a second vertical.
**Development policy:** open-weight Builder and Reviewer for low-risk verifiable work, ChatGPT Plus and Gemini for human-guided critical decisions; no assumption that consumer subscriptions provide unattended API access.

## The full product/company architecture

```
OWNER / SERENITY HQ
  ├── Executive Office — strategy, backlog, approvals, executive reports
  ├── Research & Product — discovery, interviews, sourced opportunities
  ├── Architecture — boundaries, module specs, threat models
  ├── Engineering — small approved PRs, tests, code
  ├── QA & Security — independent review, CI, evidence
  ├── Operations — scheduling, quotas, costs, checkpoints, incidents
  └── AI Platform — reusable modules, routing, evaluations, deployment controls
          │
          ▼
 Persistent SQLite company ledger (company/office.py)
  ├── Departments and logical agent roles (disabled)
  ├── Task state machine, ownership and checkpoints
  ├── Messages, acknowledgements, approvals and events
  └── Advisory model quota observations
          │
          ├── GitHub (authoritative code, issues, PRs and CI)
          ├── Obsidian exporter (visible notes, owner queue and Canvas map)
          ├── Manual cloud demo runner (no actual model calls)
          └── Future permitted model runners (separate activation)
          │
          ▼
 SERENITY TRAVEL PRODUCT
  ├── Existing Python/SQLite + JavaScript PWA
  ├── Existing independent React/Vite/Firebase prototype
  ├── Video -> save destination -> private map -> travel plan
  ├── Social video, creator content, maps, saved/visited history
  ├── Structured template games/quizzes and authorized 360 hotel media
  └── Optional later booking/monetization integrations
          │
          ▼
 REUSABLE APP BUILDER (after product validation)
  ├── Versioned AppSpec JSON, module registry and dependency validation
  ├── UI modules: feed, maps, identity, games, virtual tours
  ├── Safe deployment templates + migrations + tenancy controls
  └── Second-industry test before general-purpose SaaS
```

## Where the system actually stands

**Existing on main:** Serenity product code, AI operating charter, GitHub CI,
default-off read-only two-shift scheduler, independent review rules, and
the offline 90%-quota policy engine.

**This integrated proposal:** the two-model synthetic cloud pilot from PR #10,
a durable operational ledger, command-line task manager, structured role
communication, owner approval requests, advisory quota history, read-only
Obsidian HQ notes/Canvas, a simulated full company workday, and a manual
cloud demo workflow. This proposal intentionally **consolidates** PR #10 with
the main branch's earlier PR #11 changes. Do not merge both competing branches
without reviewing overlap.

**NOT IMPLEMENTED / NOT ACTIVE:** real LLM coding in isolated branches,
provider telemetry adapters with reliable all-window quotas, independent
cloud-hosted model calls in the same pipeline, permissions-safe PR creation,
automatic GitHub issue-to-task sync, recurring autonomous shifts, live push
notifications, cloud database deployment, production application hosting,
custom Web HQ, and multi-tenant app generator.

## Staged work program: 8–12 weeks, each gate verifiable

These are order-of-magnitude planning windows, not guaranteed delivery dates.
An hour of owner attention most days plus limited free cloud inference may
mean longer elapsed timelines.

### Phase A — Company headquarters foundation (Week 1; underway)

- [x] Department and agent-role structure, versioned policy, default-off controls.
- [x] SQLite task, message, approval, event and checkpoint ledger.
- [x] Offline two-shift simulation and Obsidian command centre/Canvas exporter.
- [ ] GitHub CI passes on the consolidated branch and owner reviews.
- [ ] Owner authorizes a merge; run manual HQ artifact workflow on main.
- [ ] Verify Obsidian opens exported pages without overwriting personal notes.

**Acceptance:** from a fresh database, create a task, assign Engineering,
handoff to QA, checkpoint for shift 2, request human approval, and export a
consistent HQ. Agent activity is explicitly *simulated* until connected.

### Phase B — Real cloud model integration (Weeks 1–2)

- [ ] Eligible owner verifies provider's terms, free quota, data policy and
      GitHub Actions usage; credentials are configured only with approval.
- [ ] Manual synthetic-code calls to Qwen3.8-27B then GPT-OSS-120B.
- [ ] Approve only a narrow set of non-sensitive code files for model context.
- [ ] Build read-only job adapter and machine-readable response schema.
- [ ] Preserve error, rate-limit and usage evidence, no retries/paid fallback.

**Acceptance:** two separate approved model calls on synthetic source, with
quota observations and an owner-viewable artifact; no repo or production writes.

### Phase C — Real Builder → Reviewer → Test workflow (Weeks 2–4)

- [ ] A GitHub Issue with clear acceptance criteria produces an approved task
      in the company ledger; duplicate processing is prevented.
- [ ] Qwen proposes a bounded patch; apply only to an isolated checkout after
      path validation and owner-approved task scope.
- [ ] Run deterministic Python/JS/React tests and reject unsupported changes.
- [ ] GPT-OSS independently reviews diff + evidence and requests repair.
- [ ] Create a draft PR with a clear provenance record and explicit owner gate.
- [ ] ChatGPT and Gemini receive high-risk escalations **interactively**,
      unless supported, permitted APIs are later purchased/authorized.

**Acceptance:** one small Serenity feature passes tests and independent review
and appears as a draft PR with rollback instructions. No production merge.

### Phase D — Reliable quota-aware operational shifts (Weeks 3–5)

- [ ] Trusted provider-specific quota readers for free hosted inference, using
      supported provider usage endpoints and a local consumption ledger.
- [ ] Stop new jobs at 90% of **any applicable** verified quota bucket; reserve
      remaining capacity only for bounded in-flight work; otherwise checkpoint.
- [ ] Verify reset by provider evidence, not by waiting five clock hours.
- [ ] 09:00–14:00 and 14:00–19:00 America/Moncton schedule (seven days);
      event triggers are short jobs, **not** ten hours of cloud compute.
- [ ] Demonstrate message acknowledgement, blocked-approval task switching,
      idempotent resumption, dead-letter handling and emergency stop.
- [ ] Request owner permission before enabling recurring cloud Actions.

**Acceptance:** simulated outage, exhausted credit, missed window and restart
recover cleanly without duplicate external side effects or spending.

### Phase E — Obsidian operational headquarters (Weeks 4–6)

- [x] Generate departmental pages, agent profiles, task notes, messages,
      quota status, approval queue and organizational Canvas.
- [ ] Incremental read-only GitHub/agent event sync into the ledger.
- [ ] Notifications/owner inbox and activity status reconciliation.
- [ ] Optionally a dedicated web-based HQ if Obsidian's refresh and interactive
      controls are insufficient.

**Acceptance:** each task appears under its department with provenance,
evidence, blocker, review outcome, next shift and required owner decision.

### Phase F — Serenity travel MVP and reusable modules (Weeks 4–9)

- [ ] Validate the core video → destination save → private map → plan journey.
- [ ] Preserve account/location privacy, upload permissions, moderation,
      performance and CDN cost constraints; no production sensitive changes by
      unattended open-weight agents.
- [ ] Add structured game templates and permissioned hotel virtual tours only
      after core loop and user feedback.
- [ ] Separate the React prototype from Python product intentionally; do not
      casually migrate both into a new stack.
- [ ] Build extraction-ready UI and data modules with integration tests.

**Acceptance:** a tested prototype with end-to-end user flow, privacy review
and documented costs; publish only on owner approval.

### Phase G — AI app-builder platform (Weeks 8–12+)

- [ ] Specify versioned `AppSpec` schema and reusable module contracts.
- [ ] Create controlled app generation, isolated builds, migrations, deploy gate.
- [ ] Validate a second non-travel vertical before general-purpose claims.
- [ ] Add multi-tenant identity, subscription/billing and marketplace features
      only when justified and approved.

**Acceptance:** two distinct apps share multiple tested modules, with
reproducible deployment steps and user-controlled revisions.

## Operational responsibilities

| Department | Role | Current capability | Next connector |
| --- | --- | --- | --- |
| Executive | Chief of Staff | SQLite task queue, owner approval ledger | GitHub issues and policy checks |
| Engineering | Lead Builder | Profile, mock flow, synthetic cloud pilot | Scoped code patch runner |
| QA | QA Director | Message receipt, simulation, CI | Independent model + test audit |
| Research | Research Director | Profile and tasks | Sourced research agent |
| Architecture | Chief Architect | Human-in-the-loop escalation | ChatGPT / Gemini manual workflow |
| Operations | Operations Director | Shifts, 90% policy, checkpoints | Trusted quota and queue adapters |
| AI Platform | Platform Engineer | Profile and product architecture | Module registry/AppSpec |

Roles are not separate model subscriptions. **All operational role profiles
remain disabled until individually approved.**

## Source-of-truth and permissions

- GitHub is authoritative for code/PRs/issues; no direct non-reviewed main writes.
- SQLite operational ledger is authoritative for task states, messages and
  decisions in the pilot. It is local until a durable approved cloud store
  is selected; GitHub CI's temporary disks are not durable company memory.
- Obsidian is a generated, readable view, not a multi-writer queue.
- Model APIs are a separate paid/free and contractual decision; consumer
  ChatGPT Plus and Google AI Plus do not automatically confer API execution.
- Never expose secrets or account/location data in Obsidian, GitHub Issues or
  model context. Do not deploy Firebase or the local Python backend directly
  to a public port without threat modeling and owner approval.

## Minimal company owner dashboard

Run the demonstration from the repository root:

```bash
python3 -m company.demo --vault /path/to/a/temporary/Obsidian-vault
python3 -m company.cli --db backend/data/serenity_company.sqlite3 init
python3 -m company.cli --db backend/data/serenity_company.sqlite3 status
python3 -m company.cli --db backend/data/serenity_company.sqlite3 export --vault /path/to/Obsidian-vault
```

Use the manual `Serenity HQ offline company simulation` GitHub Action after
merge to generate a downloadable HQ/Canvas artifact while the computer is off.
It does not connect live AI models or send agent messages independently.

## Owner-level next decisions (each has a corresponding approval gate)

1. Review consolidated PR, tests and its difference from older PR #10.
2. Decide whether to merge the integrated company ledger after QA.
3. Choose where durable company state should live when agents operate in the
   cloud (e.g. GitHub issue+artifact checkpoint first, hosted database later).
4. Approve provider eligibility/free-plan access and GitHub Actions usage
   before any live external model request.
5. Decide whether to open a public Serenity staging deployment; production
   hosting remains a separate reviewed project.

**Non-goal:** claim the entire company or a 70-hour autonomous workforce is
running simply because a dashboard and scheduler exist.
