"""Tamper-evident, replayable Serenity company event checkpoints.

Local snapshots are atomic. GitHub storage is optional, scope-limited, and
DISABLED by default. Event fields deliberately cannot contain free-form user
messages, secrets, or personal travel/location data. This is a plan for
durable cloud persistence; it never creates the remote state branch.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ZERO = "0" * 64
MAX_EVENTS = 500
MAX_SNAPSHOT_BYTES = 220000
EVENT_TYPES = frozenset({
    "TASK_ACCEPTED", "TASK_CLAIMED", "WORK_CHECKPOINT",
    "QA_HANDOFF", "QA_RESULT", "QUOTA_WIND_DOWN", "QUOTA_RESET_VERIFIED",
    "SHIFT_STARTED", "SHIFT_ENDED", "MANAGER_REVIEW", "OWNER_GATE",
})
ACTORS = frozenset({"executive", "engineering", "qa", "research",
                    "architecture", "operations", "platform", "owner"})
SHIFTS = frozenset({"shift_1", "shift_2", "outside"})
SAFE_TEXT = re.compile(r"^[a-zA-Z0-9 ._:/#=@+,-]{0,160}$")
EVENT_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{5,120}$")
HEX = re.compile(r"^[0-9a-f]{64}$")
PAYLOAD_KEYS = frozenset({"checkpoint_ref", "candidate_sha", "commit_sha",
                          "review_ref", "quota_model", "quota_state", "reason_code",
                          "ci_run_id", "issue_number", "approval_type"})
MAX_PAYLOAD_ENTRIES = 8


class CheckpointBlocked(ValueError):
    pass


def _bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("utf-8")


def _hash(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _text(value, max_len=160):
    if (not isinstance(value, str) or len(value) > max_len
            or not SAFE_TEXT.fullmatch(value)
            or any(bad in value.lower() for bad in ("ghp_", "github_pat_", "sk-",
                                                    "api_key", "password", "bearer "))):
        raise CheckpointBlocked("unsafe checkpoint field")
    return value


def _time(value):
    if not isinstance(value, str):
        raise CheckpointBlocked("missing aware timestamp")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CheckpointBlocked("invalid timestamp") from exc
    if date.tzinfo is None:
        raise CheckpointBlocked("timestamps must be offset aware")
    return date


def empty_ledger():
    return {"schema_version": 1, "events": [], "last_hash": ZERO}


def validate_ledger(ledger):
    if not isinstance(ledger, dict) or set(ledger) != {"schema_version", "events", "last_hash"}:
        raise CheckpointBlocked("invalid ledger structure")
    if ledger["schema_version"] != 1 or not isinstance(ledger["events"], list):
        raise CheckpointBlocked("unsupported ledger version")
    if len(ledger["events"]) > MAX_EVENTS or len(_bytes(ledger)) > MAX_SNAPSHOT_BYTES:
        raise CheckpointBlocked("ledger exceeds retention limit; require approved archival policy")
    previous = ZERO
    keys = set()
    previous_time = None
    for number, event in enumerate(ledger["events"], start=1):
        if not isinstance(event, dict) or set(event) != {
                "sequence", "event_id", "kind", "actor", "shift", "task_ref",
                "timestamp", "payload", "previous_hash", "hash"}:
            raise CheckpointBlocked("invalid event schema")
        if type(event["sequence"]) is not int or event["sequence"] != number:
            raise CheckpointBlocked("invalid event sequence")
        eid = event["event_id"]
        if not isinstance(eid, str) or not EVENT_ID.fullmatch(eid) or eid in keys:
            raise CheckpointBlocked("duplicate or invalid event id")
        keys.add(eid)
        if (type(event["kind"]) is not str or type(event["actor"]) is not str
                or event["kind"] not in EVENT_TYPES or event["actor"] not in ACTORS):
            raise CheckpointBlocked("unknown event or actor")
        if type(event["shift"]) is not str or event["shift"] not in SHIFTS:
            raise CheckpointBlocked("unknown shift")
        _text(event["task_ref"], 120)
        timestamp = _time(event["timestamp"])
        if previous_time is not None and timestamp < previous_time:
            raise CheckpointBlocked("non-monotonic event timestamps")
        previous_time = timestamp
        payload = event["payload"]
        if (not isinstance(payload, dict) or len(payload) > MAX_PAYLOAD_ENTRIES
                or not set(payload).issubset(PAYLOAD_KEYS)):
            raise CheckpointBlocked("unbounded or sensitive payload")
        for key, value in payload.items():
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                raise CheckpointBlocked("invalid payload value")
            _text(str(value), 160)
        if event["previous_hash"] != previous:
            raise CheckpointBlocked("broken event hash chain")
        digest = event["hash"]
        if not isinstance(digest, str) or not HEX.fullmatch(digest):
            raise CheckpointBlocked("invalid event digest")
        if _hash({k: v for k, v in event.items() if k != "hash"}) != digest:
            raise CheckpointBlocked("event modified after checkpoint")
        previous = digest
    if ledger["last_hash"] != previous:
        raise CheckpointBlocked("ledger head does not match last event")
    return ledger


def append_event(ledger, *, event_id, kind, actor, shift, task_ref,
                 timestamp, payload=None):
    validate_ledger(ledger)
    if not isinstance(event_id, str) or not EVENT_ID.fullmatch(event_id):
        raise CheckpointBlocked("invalid idempotency id")
    if any(event["event_id"] == event_id for event in ledger["events"]):
        # Idempotent replay: caller must reconcile the originally written event.
        match = next(e for e in ledger["events"] if e["event_id"] == event_id)
        fields = dict(kind=kind, actor=actor, shift=shift, task_ref=task_ref,
                      timestamp=timestamp, payload=payload or {})
        if any(match[k] != v for k, v in fields.items()):
            raise CheckpointBlocked("same event key supplied with different data")
        return ledger
    if len(ledger["events"]) >= MAX_EVENTS:
        raise CheckpointBlocked("ledger full; archival policy required")
    event = {
        "sequence": len(ledger["events"]) + 1, "event_id": event_id,
        "kind": kind, "actor": actor, "shift": shift, "task_ref": task_ref,
        "timestamp": timestamp, "payload": payload or {},
        "previous_hash": ledger["last_hash"],
    }
    event["hash"] = _hash(event)
    updated = {"schema_version": 1, "events": [*ledger["events"], event],
               "last_hash": event["hash"]}
    validate_ledger(updated)
    return updated


def load_local(path):
    path = Path(path)
    if path.is_symlink():
        raise CheckpointBlocked("symlink checkpoint rejected")
    if not path.exists():
        return empty_ledger()
    if not path.is_file() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise CheckpointBlocked("invalid checkpoint file")
    try:
        return validate_ledger(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CheckpointBlocked("checkpoint corrupt") from exc


def store_local(path, ledger, *, expected_last_hash):
    """Atomic compare-before-write for a SINGLE local process.

    Multiple-host concurrency requires the separately enabled remote
    GitHub optimistic commit/version guard and serialized worker queue.
    """
    validate_ledger(ledger)
    path = Path(path)
    if path.is_symlink() or not path.parent.is_dir() or path.parent.is_symlink():
        raise CheckpointBlocked("unsafe checkpoint path")
    current = load_local(path)
    if not isinstance(expected_last_hash, str) or current["last_hash"] != expected_last_hash:
        raise CheckpointBlocked("stale local checkpoint")
    fd, tmp = tempfile.mkstemp(prefix=".serenity-", suffix=".json",
                                dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(json.dumps(ledger, sort_keys=True, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        if hasattr(os, "O_DIRECTORY"):
            folder = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(folder)
            finally:
                os.close(folder)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)
    return {"stored": True, "last_hash": ledger["last_hash"],
            "event_count": len(ledger["events"])}


def checkpoint_summary(ledger):
    ledger = validate_ledger(ledger)
    pending = {}
    for event in ledger["events"]:
        if event["task_ref"]:
            pending[event["task_ref"]] = {"kind": event["kind"],
                                         "shift": event["shift"],
                                         "actor": event["actor"],
                                         "event_id": event["event_id"]}
    return {"event_count": len(ledger["events"]), "last_hash": ledger["last_hash"],
            "tasks": pending, "source": "checkpoint_only",
            "remote_persistence_confirmed": False,
            "autonomous_execution_enabled": False}
