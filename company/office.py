"""Serenity's local, persistent company operating ledger.

No API clients, model execution, payments or deployments. All methods record
intent/evidence in a SQLite database, not authorization to act externally.
Runtime data belongs under ignored backend/data, never in version control.
"""
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEPARTMENTS = {
    "executive": "Executive Office",
    "engineering": "Engineering",
    "qa": "Quality Assurance",
    "research": "Research and Product",
    "architecture": "Architecture",
    "operations": "Operations",
    "platform": "AI Platform",
}
AGENTS = {
    "chief-of-staff": ("executive", "Manager", "workflow"),
    "lead-builder": ("engineering", "Builder", "qwen/qwen3.8-27b"),
    "qa-director": ("qa", "Reviewer", "openai/gpt-oss-120b"),
    "research-director": ("research", "Researcher", "not-connected"),
    "chief-architect": ("architecture", "Architect", "human-guided ChatGPT / Gemini"),
    "operations-director": ("operations", "Operations", "workflow"),
    "platform-engineer": ("platform", "Systems", "not-connected"),
}
STATES = {
    "PROPOSED", "EVALUATED", "QUEUED", "IN_PROGRESS", "IN_REVIEW",
    "VERIFIED", "AWAITING_OWNER_ACTION", "DONE", "BLOCKED_APPROVAL",
    "BLOCKED_QUOTA", "BLOCKED_DEPENDENCY", "PAUSED", "CANCELLED",
}
ALLOWED = {
    "PROPOSED": {"EVALUATED", "CANCELLED"},
    "EVALUATED": {"QUEUED", "BLOCKED_APPROVAL", "CANCELLED"},
    "QUEUED": {"IN_PROGRESS", "BLOCKED_APPROVAL", "BLOCKED_QUOTA", "BLOCKED_DEPENDENCY", "PAUSED", "CANCELLED"},
    "IN_PROGRESS": {"IN_REVIEW", "BLOCKED_APPROVAL", "BLOCKED_QUOTA", "BLOCKED_DEPENDENCY", "PAUSED"},
    "IN_REVIEW": {"IN_PROGRESS", "VERIFIED", "BLOCKED_APPROVAL", "BLOCKED_QUOTA", "PAUSED"},
    "VERIFIED": {"AWAITING_OWNER_ACTION", "IN_PROGRESS"},
    "AWAITING_OWNER_ACTION": {"DONE", "IN_PROGRESS", "BLOCKED_APPROVAL"},
    "BLOCKED_APPROVAL": {"QUEUED", "PAUSED", "CANCELLED"},
    "BLOCKED_QUOTA": {"QUEUED", "PAUSED", "CANCELLED"},
    "BLOCKED_DEPENDENCY": {"QUEUED", "PAUSED", "CANCELLED"},
    "PAUSED": {"QUEUED", "CANCELLED"},
    "DONE": set(),
    "CANCELLED": set(),
}
APPROVAL_ACTIONS = {"merge", "deploy", "spending", "credentials", "publication", "production_data", "strategy"}
SLUG = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS departments (
  slug TEXT PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agents (
  slug TEXT PRIMARY KEY, department TEXT NOT NULL REFERENCES departments(slug),
  title TEXT NOT NULL, model TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled=0)
);
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, department TEXT NOT NULL REFERENCES departments(slug),
  risk TEXT NOT NULL CHECK (risk IN ('low','medium','high')),
  acceptance TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'PROPOSED',
  assigned_agent TEXT REFERENCES agents(slug),
  checkpoint TEXT NOT NULL DEFAULT '', branch TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  external_ref TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL REFERENCES tasks(id),
  sender TEXT NOT NULL, recipient TEXT NOT NULL, body TEXT NOT NULL,
  created_at TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL REFERENCES tasks(id),
  action TEXT NOT NULL, explanation TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'PENDING',
  requested_at TEXT NOT NULL, decided_at TEXT, decision_note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, task_id INTEGER REFERENCES tasks(id),
  actor TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quota_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT, model TEXT NOT NULL, source TEXT NOT NULL,
  state TEXT NOT NULL, observed_at TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_task_state ON tasks(state);
CREATE INDEX IF NOT EXISTS idx_events_id ON events(id);
"""


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value, limit=1400):
    if not isinstance(value, str):
        raise ValueError("text field must be a string")
    value = " ".join(value.strip().split())
    if not value or len(value) > limit:
        raise ValueError("required text is empty or too long")
    return value


def safe_slug(value):
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise ValueError("invalid department or agent ID")
    return value


class CompanyOffice:
    def __init__(self, filename):
        self.filename = Path(filename)
        if self.filename.name == ":memory:":
            self.db = sqlite3.connect(":memory:")
        else:
            self.filename.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(str(self.filename))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        if "external_ref" not in {
                row["name"] for row in self.db.execute("PRAGMA table_info(tasks)") }:
            # Additive schema migration for existing pilot ledgers.
            self.db.execute("ALTER TABLE tasks ADD COLUMN external_ref TEXT")
        self.db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_external_ref ON tasks(external_ref)")
        self.db.commit()
        self.seed()

    def close(self):
        self.db.close()

    def seed(self):
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO departments(slug,name) VALUES (?,?)",
                list(DEPARTMENTS.items()))
            self.db.executemany(
                "INSERT OR IGNORE INTO agents(slug,department,title,model,enabled) VALUES (?,?,?,?,0)",
                [(slug, *details) for slug, details in AGENTS.items()])

    def _event(self, typ, task_id, actor, detail):
        self.db.execute(
            "INSERT INTO events(event_type,task_id,actor,detail,created_at) VALUES (?,?,?,?,?)",
            (clean(typ, 64), task_id, clean(actor, 100), clean(detail, 4000), utc_now()))

    def _get(self, task_id):
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("task does not exist")
        return row

    def new_task(self, title, department, acceptance, risk="low"):
        safe_slug(department)
        if department not in DEPARTMENTS:
            raise ValueError("unknown department")
        if risk not in {"low", "medium", "high"}:
            raise ValueError("unknown risk level")
        title, acceptance = clean(title, 180), clean(acceptance, 3000)
        with self.db:
            cursor = self.db.execute(
                "INSERT INTO tasks(title,department,risk,acceptance,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                (title, department, risk, acceptance, utc_now(), utc_now()))
            task_id = cursor.lastrowid
            self._event("task_created", task_id, "office", title)
        return task_id

    def import_issue(self, repo, number, title, body, labels):
        """Read-only import of an external GitHub issue as an unapproved proposal.

        This does NOT trust instructions in issue text or start any agent.
        Reimports are idempotent and cannot overwrite local task state.
        """
        if repo != "Baraka-Hani/Serenity":
            raise ValueError("external repository not allowlisted")
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise ValueError("invalid issue number")
        if not isinstance(labels, list):
            raise ValueError("issue labels must be a list")
        label_names = {x for x in labels if isinstance(x, str)}
        depts = [name.split(":", 1)[1] for name in label_names
                 if name.startswith("dept:") and name.split(":", 1)[1] in DEPARTMENTS]
        department = sorted(depts)[0] if depts else "executive"
        risk = "low" if "risk:low" in label_names else "medium"
        external_ref = f"github:{repo}#{number}"
        found = self.db.execute("SELECT id FROM tasks WHERE external_ref=?",
                                (external_ref,)).fetchone()
        if found:
            return found["id"]
        title = clean(title, 180)
        acceptance = clean(body[:3000] if isinstance(body, str) and body.strip()
                           else "Owner must supply acceptance criteria before evaluation", 3000)
        with self.db:
            cursor = self.db.execute(
                "INSERT OR IGNORE INTO tasks(title,department,risk,acceptance,created_at,updated_at,external_ref) VALUES (?,?,?,?,?,?,?)",
                (title, department, risk, acceptance, utc_now(), utc_now(), external_ref))
            if cursor.lastrowid:
                task_id = cursor.lastrowid
                self._event("issue_imported", task_id, "github-readonly", external_ref)
                return task_id
        existing = self.db.execute("SELECT id FROM tasks WHERE external_ref=?",
                                   (external_ref,)).fetchone()
        if existing is None:
            raise ValueError("issue import failed")
        return existing["id"]

    def transition(self, task_id, target, note, actor="office"):
        if target not in STATES:
            raise ValueError("invalid state")
        note = clean(note)
        with self.db:
            task = self._get(task_id)
            if target not in ALLOWED[task["state"]]:
                raise ValueError("invalid task transition: " + task["state"] + " to " + target)
            if target == "IN_PROGRESS" and task["risk"] != "low":
                raise ValueError("medium/high risk work cannot be automatically started")
            if target == "DONE":
                pending = self.db.execute(
                    "SELECT count(*) FROM approvals WHERE task_id=? AND state='PENDING'",
                    (task_id,)).fetchone()[0]
                if pending:
                    raise ValueError("pending owner approvals cannot be bypassed")
            self.db.execute("UPDATE tasks SET state=?,updated_at=? WHERE id=?",
                            (target, utc_now(), task_id))
            self._event("task_state", task_id, actor, target + ": " + note)

    def assign(self, task_id, agent_id):
        safe_slug(agent_id)
        with self.db:
            task = self._get(task_id)
            agent = self.db.execute("SELECT * FROM agents WHERE slug=?", (agent_id,)).fetchone()
            if agent is None:
                raise ValueError("agent role does not exist")
            if agent["department"] != task["department"]:
                raise ValueError("agent department does not match task owner")
            if task["state"] not in ("EVALUATED", "QUEUED"):
                raise ValueError("task must be evaluated or queued before assignment")
            self.db.execute("UPDATE tasks SET assigned_agent=?,updated_at=? WHERE id=?",
                            (agent_id, utc_now(), task_id))
            self._event("task_assigned", task_id, "office", agent_id)

    def checkpoint(self, task_id, note, branch=""):
        note = clean(note, 3000)
        if not isinstance(branch, str) or len(branch) > 200 or any(ord(ch) < 32 for ch in branch):
            raise ValueError("invalid branch")
        with self.db:
            self._get(task_id)
            self.db.execute("UPDATE tasks SET checkpoint=?,branch=?,updated_at=? WHERE id=?",
                            (note, branch, utc_now(), task_id))
            self._event("checkpoint", task_id, "operations", note)

    def send_message(self, task_id, sender, recipient, body):
        body = clean(body, 3000)
        safe_slug(sender)
        safe_slug(recipient)
        with self.db:
            self._get(task_id)
            known = {"owner"} | set(AGENTS)
            if sender not in known or recipient not in known:
                raise ValueError("unknown sender or recipient role")
            cursor = self.db.execute(
                "INSERT INTO messages(task_id,sender,recipient,body,created_at) VALUES (?,?,?,?,?)",
                (task_id, sender, recipient, body, utc_now()))
            self._event("message", task_id, sender, "to " + recipient + ": " + body)
        return cursor.lastrowid

    def acknowledge(self, message_id, recipient):
        safe_slug(recipient)
        with self.db:
            row = self.db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
            if row is None or row["recipient"] != recipient:
                raise ValueError("message or recipient mismatch")
            self.db.execute("UPDATE messages SET acknowledged=1 WHERE id=?", (message_id,))
            self._event("message_ack", row["task_id"], recipient, "message #" + str(message_id))

    def request_approval(self, task_id, action, reason):
        if action not in APPROVAL_ACTIONS:
            raise ValueError("unsupported sensitive action")
        reason = clean(reason, 3000)
        with self.db:
            self._get(task_id)
            cursor = self.db.execute(
                "INSERT INTO approvals(task_id,action,explanation,requested_at) VALUES (?,?,?,?)",
                (task_id, action, reason, utc_now()))
            self._event("approval_requested", task_id, "office", action + ": " + reason)
        return cursor.lastrowid

    def decide_approval(self, approval_id, decision, note, owner_confirm=False):
        if not owner_confirm:
            raise ValueError("local owner confirmation required")
        if decision not in ("APPROVED", "REJECTED"):
            raise ValueError("invalid owner decision")
        with self.db:
            row = self.db.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
            if row is None or row["state"] != "PENDING":
                raise ValueError("approval does not exist or has been decided")
            self.db.execute(
                "UPDATE approvals SET state=?,decided_at=?,decision_note=? WHERE id=?",
                (decision, utc_now(), clean(note), approval_id))
            self._event("owner_decision", row["task_id"], "owner", row["action"] + ": " + decision)
        # This writes a local decision record only, never performs the action.

    def shift_checkpoint(self, name, note):
        if name not in ("shift_1_start", "shift_1_end_shift_2_start", "shift_2_end"):
            raise ValueError("invalid shift checkpoint")
        with self.db:
            self._event("shift_checkpoint", None, "operations", name + ": " + clean(note))

    def record_quota_state(self, result, source, observed_at):
        if not isinstance(result, dict) or result.get("state") not in {
            "READY", "WIND_DOWN", "EXHAUSTED", "UNKNOWN", "RESET_VERIFICATION_REQUIRED"}:
            raise ValueError("invalid quota assessment")
        model = clean(result.get("model") or "unknown", 200)
        source = clean(source, 100)
        observed_at = clean(observed_at, 80)
        with self.db:
            self.db.execute(
                "INSERT INTO quota_snapshots(model,source,state,observed_at,reason,created_at) VALUES (?,?,?,?,?,?)",
                (model, source, result["state"], observed_at, clean(result.get("reason") or "unverified"), utc_now()))
            self._event("quota_observation", None, "operations", model + ": " + result["state"])
        # Observations do not grant provider access or activate an agent.

    def rows(self, table):
        if table not in {"tasks", "agents", "departments", "events", "messages", "approvals", "quota_snapshots"}:
            raise ValueError("unknown table")
        order = "id" if table not in {"agents", "departments"} else "slug"
        return [dict(row) for row in self.db.execute("SELECT * FROM " + table + " ORDER BY " + order)]

    def snapshot(self):
        tasks = self.rows("tasks")
        return {
            "generated_at": utc_now(),
            "execution_enabled": False,
            "agents_connected": 0,
            "tasks_by_state": {s: sum(t["state"] == s for t in tasks) for s in sorted(STATES)},
            "pending_approvals": sum(a["state"] == "PENDING" for a in self.rows("approvals")),
            "unacknowledged_messages": sum(not m["acknowledged"] for m in self.rows("messages")),
            "departments": len(DEPARTMENTS),
            "role_profiles": len(AGENTS),
        }
