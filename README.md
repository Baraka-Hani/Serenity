# Serenity
Foundational repository for the scalable AI infrastructure that Serenity is going to pilot. It also contains the Serenity travel app and a separate React/Firebase prototype.

## AI development workflow

Serenity uses a supervised Builder → Reviewer workflow with isolated branches,
automated checks, manager-authorized routine commits after verified quality, and owner-controlled financial/public-release decisions. Start with
[`AGENTS.md`](AGENTS.md), then see the [agent roles](docs/AGENT_ROLES.md),
[architecture](docs/ARCHITECTURE.md), [task-management
workflow](docs/TASK_MANAGEMENT.md), and [workforce foundation
checklist](docs/AI_WORKFORCE_FOUNDATION.md). The [workday reporting
guide](docs/WORKDAY_REPORTING.md) defines the 9 AM intake, 2 PM shift handoff,
and 7 PM evidence report.
The [supervised scheduling guide](docs/WORKDAY_SCHEDULING.md) defines the
default-off two five-hour shifts every day, including weekends, and emergency stop.
The [quota-aware model policy](docs/QUOTA_AWARE_SHIFTS.md) defines the 90%
wind-down threshold and verified-reset rule. Both schedules remain
coordination-only until separately approved agents are connected.

## AI company headquarters (in development)

Serenity is also the pilot for a human-supervised AI software company:
Executive Office, Engineering, QA, Research & Product, Architecture,
Operations and AI Platform. Its implementation is tracked in
[the unified company roadmap](docs/SERENITY_COMPANY_PROGRAM.md) and
[company program issue #13](https://github.com/Baraka-Hani/Serenity/issues/13).

The [company OS quick-start](company/README.md) describes a runnable Python/
SQLite task ledger, department-to-department messages, owner approval inbox,
90% quota-aware Chief-of-Staff dry-run planner, two-shift checkpoints, a
read-only GitHub Issue importer, and an Obsidian Canvas/Markdown exporter.

```bash
python3 -m company.demo --vault /path/to/temporary-vault
python3 -m company.cli status
python3 -m company.cli plan
```

These commands do not start AI models. Cloud AI and GitHub workflows remain
manual-only or disabled until separately authorized; see
[cloud pilot setup](docs/CLOUD_PILOT_SETUP.md).

## Projects

- **Main app and local backend** — a responsive travel-sharing app with public trip posts, accounts, Clip Studio, messaging, and map-based discovery. The Python backend uses SQLite and stores local account data, databases, and uploads under `backend/data/`.
- **`nomad-canvas/`** — a standalone React/Vite/Firebase prototype with local demo mode, travel metadata, and optional backend handoffs for inventory and payments.

## Run the main app

Requires Python 3:

```bash
python3 backend/server.py
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/). The server binds to loopback by default and is intended for local development; see [backend/README.md](backend/README.md) for app behavior, deployment notes, and test commands.

## Run the React prototype

Requires Node.js and npm:

```bash
cd nomad-canvas
npm install
npm run dev
```

Build it with `npm run build`. Firebase settings are optional for local demo mode. To use Firebase, copy `.env.example` to `.env.local` and configure the Firebase web app values; never commit `.env.local`, service-account credentials, or payment/provider secrets. See [nomad-canvas/README.md](nomad-canvas/README.md) for setup and hosting details.

## Data and deployment

Local databases, uploaded media, environment files, dependencies, and generated build output are excluded from Git. Back up `backend/data/` separately if you need to preserve local accounts and uploads. The main app needs its Python backend and persistent storage to run; publishing source to GitHub does not deploy that backend. GitHub Pages alone cannot run it.
