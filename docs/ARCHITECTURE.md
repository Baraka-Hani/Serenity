# Serenity architecture

## System map

```text
Browser / installable PWA
  ├── plain HTML, CSS and JavaScript at repository root
  ├── account, feed, map, messaging and Clip Studio interfaces
  └── service worker caches static shell only
                     │ localhost HTTP / JSON
                     ▼
Python standard-library server (`backend/server.py`)
  ├── account and session handling
  ├── private clips and public posts
  ├── trips, destinations, discovery and messaging
  └── SQLite + uploaded media in ignored `backend/data/`

Separate prototype (`nomad-canvas/`)
  ├── React + TypeScript + Vite
  ├── device-local demo mode
  └── optional Firebase Auth / Firestore / Hosting / Storage boundary
```

## Main application

The repository root is the current full travel product. The browser interface is
served by `backend/server.py`, which binds to loopback by default. It uses the
Python standard library and SQLite, avoiding a Python package-install step.

Important modules include:

- `backend/server.py`: HTTP routes, authentication, uploads and application API;
- `backend/social.py`: social feed persistence and behaviour;
- `backend/messaging.py`: private messaging;
- `backend/studio_import.py`: reviewed private trip imports;
- `backend/trip_locations.py`: destination and map data;
- `backend/trip_visibility.py`: public/private publication changes;
- root-level JS/CSS/HTML: PWA screens and client behaviour.

### Data boundary

`backend/data/` contains local databases, uploads and runtime data and is ignored
by Git. Tests use temporary isolated data. Agents must never substitute real user
data for test fixtures or commit runtime data.

### Deployment boundary

The main application is local by default. Docker and Compose describe a possible
portable deployment, but public operation requires a deliberate HTTPS host,
durable storage, backup, security review and explicit human approval. Port 8765
must not be directly exposed to the internet.

## React/Firebase prototype

`nomad-canvas/` is a separate experiment rather than the frontend for the main
Python app. It supports a device-local demo and contains optional Firebase
configuration. No `.firebaserc` project selection is committed.

Firebase credentials belong in local environment configuration. Service-account
keys and server secrets must never enter Vite variables or the repository.
Storage and billing are intentionally optional and require owner approval.

## Test architecture

- Python integration suites start an isolated HTTP server and temporary data.
- Root browser-logic tests are dependency-free Node scripts.
- The React prototype is verified through TypeScript and Vite build output.
- `.github/workflows/ci.yml` runs these groups independently.

## Near-term architectural rules

1. Augment the current stack; do not introduce orchestration frameworks yet.
2. Keep the main application and prototype separate unless a migration issue is
   explicitly approved.
3. Treat authentication, visibility and ownership changes as medium risk.
4. Treat production data, deployment, billing and secrets as stop-gated work.
5. Prefer GitHub Issues, pull requests and CI as the first operating dashboard.
