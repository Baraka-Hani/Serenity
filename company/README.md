# Serenity HQ — Start Here

This directory contains the **persistent organizational foundation**, not a
running swarm of AI models. It is designed to grow into a company that operates
short cloud jobs during two five-hour shifts with a human owner.

## Engineering department pilot (integrated)

An [offline end-to-end engineering pipeline](ENGINEERING_DEPARTMENT.md)
now demonstrates a synthetic issue → bounded isolated code patch → QA static
review → department handoff → owner decision queue → Obsidian evidence.
It does **not** execute generated source, call actual models, create a GitHub
PR or alter product code.

```bash
python3 backend/test_engineering_pipeline.py
python3 -m company.engineering_pipeline \
  --task config/engineering_demo_task.json \
  --source-root . \
  --artifact-root /tmp/serenity-eng-evidence-new \
  --db /tmp/serenity-eng-company.sqlite3
```

## Commands

Run from the Serenity repository root. Python 3.11+ and standard library are
sufficient; no external services are needed for the following commands.

### 1. Create the company's durable local ledger

```bash
python3 -m company.cli init
python3 -m company.cli status
python3 -m company.cli agents
python3 -m company.cli departments
```

Default database is the ignored file
`backend/data/serenity_company.sqlite3`. Keep it private and backed up.
The local database is not yet a remotely accessible cloud source of truth.

### 2. Create and prioritize a task

```bash
python3 -m company.cli new "Add destination-card unit tests" --department engineering --risk low --acceptance "Three passing tests and a reviewer decision"
python3 -m company.cli advance 1 EVALUATED --note "Acceptance criteria checked"
python3 -m company.cli assign 1 lead-builder
python3 -m company.cli advance 1 QUEUED --note "Eligible for a future supervised run"
python3 -m company.cli plan
```

`plan` returns a **dry-run** selection and blocks real model work when a quota
observation is missing. Assigning a role does not start a model.

### 3. Send an interdepartment handoff and save the shift

```bash
python3 -m company.cli send 1 --from-role lead-builder --to-role qa-director --message "Request independent review of candidate tests"
python3 -m company.cli shift shift_1_end_shift_2_start --note "14:00 handoff. No live code execution occurred"
python3 -m company.cli messages
```

The message is persisted in SQLite. The destination role is a **profile**,
not a currently listening AI process. Messages require a future approved
dispatcher before a model can autonomously act on them.

### 4. Create the Obsidian company headquarters

```bash
python3 -m company.cli export --vault /path/to/your/Obsidian-vault
```

Generated pages are under `Serenity HQ/` and the organization map is
`Serenity Company.canvas`. The exporter overwrites only its own generated
pages, never arbitrary personal vault files; use a dedicated vault initially.

### 5. Run the whole-company offline simulation

```bash
python3 -m company.demo --vault /path/to/a/test-vault
python3 backend/test_company_office.py
python3 backend/test_company_manager.py
```

The simulation covers task intake, an Engineering→QA message, acknowledgement,
14:00 checkpoint, a second-shift operations event, and an illustrative owner financial approval.
Sample activity is marked as **simulated**, not actual work.

### 6. Read real GitHub issues (optional manual action)

```bash
python3 -m company.github_read --explicit-read-only-github --db backend/data/serenity_company.sqlite3
```

This makes one allowlisted **GET** of
`https://api.github.com/repos/Baraka-Hani/Serenity/issues`. It imports open
issues as unapproved tasks, with deduplication and conservative risk defaults.
No GitHub issue edit, code execution or payment occurs. Set `GITHUB_TOKEN` in
the environment only when necessary and authorized; never place tokens into
notes or the command line. Issue bodies are untrusted input.

After review and merge, a **manual-only** GitHub Actions workflow called
`Serenity HQ manual company simulation` can generate an HQ artifact on a
cloud runner with `simulated` or `github-issues` input. Its state remains
ephemeral until a separate durable remote store is authorized.

## Who is responsible for what

| Office | Assigned responsibility | Model access today |
| --- | --- | --- |
| Executive | Chief of Staff and owner approvals | Offline planner only |
| Engineering | Qwen Builder role | Manual synthetic pilot in draft; no autonomous access |
| QA | GPT-OSS Reviewer | Manual synthetic pilot in draft; no autonomous access |
| Research & Product | Research opportunities, evidence | Not connected |
| Architecture | ChatGPT / Gemini escalations | Human-in-the-loop only |
| Operations | Quotas, scheduling, checkpoints | Offline policy/ledger |
| AI Platform | reusable app modules and infrastructure | Not connected |

## Five-hour shift and 90% quota reality

- Shift 1: **09:00–14:00** America/Moncton; Shift 2 **14:00–19:00**,
  seven days a week. These are coordination windows, not synchronized resets.
- The model's first applicable quota window to reach 90% used causes **wind-down**:
  new model work stops and remaining bounded work is checkpointed.
- Resume requires verified refreshed allowance, not five clock hours elapsed.
- Free Groq model limits are per-minute/day and account-specific; consumer
  ChatGPT/Gemini subscriptions do not automatically authorize background APIs.
- No current model runner is permitted to infer "quota READY" from the
  local, simulated ledger. A future trusted provider adapter is required.

## Longer-term execution

The full phased business and product program is in
[docs/SERENITY_COMPANY_PROGRAM.md](../docs/SERENITY_COMPANY_PROGRAM.md).
GitHub [company epic #13](https://github.com/Baraka-Hani/Serenity/issues/13)
tracks dependencies and departmental assignments.

**Delegated manager policy:** routine branch commits and draft PRs can be manager-approved after verifiable tests, independent QA and architectural alignment. Low-risk protected-branch merges additionally need enforced GitHub rules and actual CI evidence. The currently running demo does not write GitHub. The owner retains approval of financial exposure, credentials/access, production or public releases, production data and material security/privacy changes. See [delegated authority](../docs/DELEGATED_ENGINEERING_AUTHORITY.md).
