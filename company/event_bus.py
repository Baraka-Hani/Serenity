"""Thread-safe, hash-linked SQLite event journal and audit replay bus.

Records task state transitions, quota telemetry events, shift handoffs, and
quality verdicts with cryptographic tamper-detection. Fails closed if the chain
diverges or is corrupted.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

GENESIS_HASH = "0" * 64


class EventBusError(ValueError):
    """Raised for event bus validation or integrity failures."""


def iso_utc_now() -> str:
    """Return current timestamp in ISO-8601 UTC format."""
    return datetime.now(timezone.utc).isoformat()


def compute_event_hash(
    prev_hash: str,
    timestamp: str,
    event_type: str,
    department: str,
    agent_id: str,
    payload_json: str,
) -> str:
    """Compute deterministic SHA256 digest binding an event to its predecessor."""
    raw = f"{prev_hash}|{timestamp}|{event_type}|{department}|{agent_id}|{payload_json}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EventBus:
    """Cryptographically linked audit journal storing company operational events."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Create events table and indices if they do not exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS company_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    department TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_event_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type_dept
                ON company_events (event_type, department)
            """)

    def close(self) -> None:
        """Close SQLite connection."""
        self.conn.close()

    def get_latest_event(self) -> Optional[Dict[str, Any]]:
        """Return the most recently recorded event, or None if empty."""
        cursor = self.conn.execute(
            "SELECT * FROM company_events ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

    def publish(
        self,
        event_type: str,
        department: str,
        agent_id: str,
        payload: Dict[str, Any],
        *,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an immutable, hash-linked event in the journal."""
        if not event_type or not isinstance(event_type, str):
            raise EventBusError("event_type must be a non-empty string")
        if not department or not isinstance(department, str):
            raise EventBusError("department must be a non-empty string")
        if not agent_id or not isinstance(agent_id, str):
            raise EventBusError("agent_id must be a non-empty string")
        if not isinstance(payload, dict):
            raise EventBusError("payload must be a dictionary")

        ts = timestamp or iso_utc_now()
        payload_str = json.dumps(payload, sort_keys=True)

        with self._lock:
            latest = self.get_latest_event()
            prev_hash = latest["event_hash"] if latest else GENESIS_HASH
            ev_hash = compute_event_hash(
                prev_hash, ts, event_type, department, agent_id, payload_str
            )
            event_id = f"EVT-{ts.replace(':', '').replace('-', '')[:15]}-{ev_hash[:8]}"

            with self.conn:
                cursor = self.conn.execute(
                    """
                    INSERT INTO company_events (
                        event_id, timestamp, event_type, department,
                        agent_id, payload_json, previous_event_hash, event_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (event_id, ts, event_type, department, agent_id,
                     payload_str, prev_hash, ev_hash),
                )
                row_id = cursor.lastrowid

            return {
                "id": row_id,
                "event_id": event_id,
                "timestamp": ts,
                "event_type": event_type,
                "department": department,
                "agent_id": agent_id,
                "payload": payload,
                "previous_event_hash": prev_hash,
                "event_hash": ev_hash,
            }

    def get_events(
        self,
        *,
        event_type: Optional[str] = None,
        department: Optional[str] = None,
        limit: int = 100,
        since_id: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query events matching optional type and department filters."""
        query = "SELECT * FROM company_events WHERE id > ?"
        params: List[Any] = [since_id]

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if department:
            query += " AND department = ?"
            params.append(department)

        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            item["payload"] = json.loads(item["payload_json"])
            results.append(item)
        return results

    def verify_chain_integrity(self) -> Tuple[bool, str]:
        """Verify the cryptographic hash-chain across all stored events."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT * FROM company_events ORDER BY id ASC"
            )
            rows = cursor.fetchall()

            if not rows:
                return True, "Event journal is empty; chain is trivially intact."

            expected_prev = GENESIS_HASH
            for idx, row in enumerate(rows):
                ev = dict(row)
                if ev["previous_event_hash"] != expected_prev:
                    return False, (
                        f"Hash chain break at event ID {ev['id']} ({ev['event_id']}): "
                        f"expected prev_hash {expected_prev[:12]}..., found {ev['previous_event_hash'][:12]}..."
                    )

                recomputed = compute_event_hash(
                    ev["previous_event_hash"],
                    ev["timestamp"],
                    ev["event_type"],
                    ev["department"],
                    ev["agent_id"],
                    ev["payload_json"],
                )

                if ev["event_hash"] != recomputed:
                    return False, (
                        f"Tampered event content at event ID {ev['id']} ({ev['event_id']}): "
                        f"stored hash {ev['event_hash'][:12]}..., computed {recomputed[:12]}..."
                    )

                expected_prev = ev["event_hash"]

            return True, f"Verified chain integrity: all {len(rows)} events are cryptographically intact."

    def count(self) -> int:
        """Return total count of recorded events."""
        cursor = self.conn.execute("SELECT COUNT(*) as total FROM company_events")
        return int(cursor.fetchone()["total"])
