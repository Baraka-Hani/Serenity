# Chat and account discovery

Open [Chat](http://127.0.0.1:8765/search.html) and sign in. The shared toolbar stays **Home feed → Chat → Map → Clip Studio → Account**.

## What works

- **Find people** shows accounts with public trips. Search by display name, @username, or a destination in a published post. Search can also find a new account with no public posts by its name or username. Emails are never searchable or returned.
- Open a public profile or choose **Message** on a directory card. **Ask creator** on a Home feed video or trip page opens a private composer linked to that particular video; public comments stay separate.
- One conversation per account pair, persisted messages, unread counts, inbox filtering, earlier-message pagination, blocking/unblocking, and draft preservation while switching conversations in the same tab.
- Messages refresh every six seconds while this page is visible; Refresh checks immediately. This is not push notification delivery or background messaging. There are no automated replies from test accounts.
- Video references re-check publication. A hidden or deleted video is unavailable through the messaging API. A trip's private notes, emails, GPS metadata, and unpublished clips never become message attachments.
- Signing out or changing accounts requires reauthentication. Messages and drafts are not saved in browser local storage or service-worker caches. Drafts are intentionally lost when leaving/reloading the page.

`backend/messaging.py` owns conversation authorization, receipts, read positions, blocking, and send limits. `backend/account_discovery.py` owns the directory. `messages-client.js` is the API boundary; `messages.js` and `account-discovery.js` own their respective UIs. Only small links are shared with Home feed and profiles.

## Local test accounts and supplied videos

The explicitly invoked `seed_demo.py` creates six **Demo** accounts, 10 visual-theme collections, and 74 posts from the videos listed in `demo_videos.json`. It also adds three two-way example conversations **only between demo accounts**. It does not send messages to real users.

Usernames: `demo_maya`, `demo_jules`, `demo_rio`, `demo_avery`, `demo_noor`, `demo_kai`. Each email is `<username>@demo.serenity.test`. These are local fixtures, not real people or the people shown in the footage. Profiles, captions, and directory badges identify them as test content. Locations are unconfirmed and no map pins are invented.

The generated shared test password is in `backend/data/demo-access.json` (private file permissions, not served by HTTP). Sign into one demo account in one browser session and another in a separate private-browser session to test replies. Do not save demo passwords in your browser or use demo accounts for real personal data.

```sh
# Read-only input check.
python3 backend/seed_demo.py --source-root '/path/to/Photos Library.photoslibrary/originals'
# Explicitly create local fixtures.
python3 backend/seed_demo.py --source-root '/path/to/Photos Library.photoslibrary/originals' --apply
```

Seeding is rerunnable without duplicate accounts, videos, or sample messages. It refuses conflicts with real accounts and refuses non-loopback/public-origin configuration. It never resets existing account passwords, deletes existing data, re-publishes made-private demo posts, or touches original videos. A private `before-demo-*.sqlite3` snapshot is saved before changes. Native macOS `avconvert` prepares metadata-filtered, fast-start, 720p MP4 copies up to 20 seconds long; originals stay in Photos unchanged. No paid API, external upload, or photo-library scan is used. Media preparation can resume by rerunning the command after interruption.

The seed command does not automatically run when the server starts. Before any future public deployment, remove the local fixtures through an explicit, backed-up cleanup process and do not ship their credentials, database, or original source manifest paths.

## Tests and limits

```sh
python3 backend/test_server.py
python3 backend/test_messaging.py
python3 backend/test_account_discovery.py
# Optional, when Node is installed: pure UI-state tests, not a browser replacement.
node backend/test_chat_ui.js
```

These use disposable databases and synthetic videos, not real user data. They cover authenticated discovery, private destination exclusion, search ranking/pagination, DM membership, idempotent sends, unread positions, video visibility, blocking, rate limits, and safe rerunnable demo setup.

This is a local prototype: message text is stored in SQLite and is **not end-to-end encrypted**. Server administrators can access that database. Do not expose this development server as a production messaging service without deployment hardening, moderation/reporting, retention/deletion policy, and abuse monitoring.
