# Serenity
Foundational repository for the scalable AI infrastructure that Serenity is going to pilot. It also contains the Serenity travel app and a separate React/Firebase prototype.

## AI development workflow

Serenity uses a supervised Builder → Reviewer workflow with isolated branches,
automated checks and a human merge/deployment gate. Start with
[`AGENTS.md`](AGENTS.md), then see the [agent roles](docs/AGENT_ROLES.md),
[architecture](docs/ARCHITECTURE.md), [task-management
workflow](docs/TASK_MANAGEMENT.md), and [workforce foundation
checklist](docs/AI_WORKFORCE_FOUNDATION.md).

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
