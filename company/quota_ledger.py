"""Durable SQLite quota ledger enforcing zero-spend limits and 90% wind-down.

Tracks daily token consumption, requests, and model allocations without relying
on partial vendor HTTP headers. Fails closed on uncertainty.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DAILY_TOKEN_BUDGET = 60_000
WIND_DOWN_PERCENT = 0.90
WIND_DOWN_THRESHOLD_TOKENS = int(DEFAULT_DAILY_TOKEN_BUDGET * WIND_DOWN_PERCENT)  # 54,000
SAFETY_MARGIN_PERCENT = 0.25  # 25% buffer for in-flight tasks

VALID_MODELS = {
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "simulation/builder",
    "simulation/reviewer",
}


class QuotaLedgerError(ValueError):
    """Raised for invalid quota records or operations."""


def iso_utc_now() -> str:
    """Return current timestamp in ISO-8601 UTC format."""
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO-8601 timestamp string into timezone-aware datetime."""
    if not isinstance(ts, str):
        raise QuotaLedgerError(f"Timestamp must be a string, got {type(ts)}")
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise QuotaLedgerError("Timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc)


class QuotaLedger:
    """Persistent SQLite ledger tracking AI model usage against a zero-spend budget."""

    def __init__(self, db_path: str = ":memory:"):
        """Initialize quota ledger with SQLite connection."""
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Create necessary tables if they do not exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS quota_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    call_type TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_cents REAL DEFAULT 0.0,
                    task_id TEXT,
                    metadata_json TEXT
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_quota_events_model_ts
                ON quota_events (model, timestamp)
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS quota_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    daily_tokens_consumed INTEGER NOT NULL,
                    daily_budget INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
            """)

    def close(self) -> None:
        """Close SQLite connection."""
        self.conn.close()

    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        *,
        task_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        call_type: str = "inference",
        cost_cents: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record an API invocation event in the ledger."""
        if model not in VALID_MODELS and not model.startswith("test/"):
            raise QuotaLedgerError(f"Unrecognized model identifier: {model}")
        if not isinstance(prompt_tokens, int) or prompt_tokens < 0:
            raise QuotaLedgerError("prompt_tokens must be a non-negative integer")
        if not isinstance(completion_tokens, int) or completion_tokens < 0:
            raise QuotaLedgerError("completion_tokens must be a non-negative integer")
        if cost_cents != 0.0:
            raise QuotaLedgerError("Violation of zero-spend policy: cost_cents must be 0.0")

        ts = timestamp or iso_utc_now()
        # Validate timestamp format
        parse_timestamp(ts)
        total_tokens = prompt_tokens + completion_tokens
        meta_str = json.dumps(metadata or {})

        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO quota_events (
                    timestamp, model, call_type, prompt_tokens,
                    completion_tokens, total_tokens, cost_cents,
                    task_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, model, call_type, prompt_tokens, completion_tokens,
                 total_tokens, cost_cents, task_id, meta_str),
            )
            return cursor.lastrowid

    def get_window_usage(
        self,
        model: str,
        *,
        now: Optional[datetime] = None,
        window_hours: int = 24,
    ) -> Dict[str, Any]:
        """Calculate total consumption for a model within a rolling time window."""
        ref_time = now or datetime.now(timezone.utc)
        if ref_time.tzinfo is None:
            raise QuotaLedgerError("now must be timezone-aware")
        ref_time = ref_time.astimezone(timezone.utc)
        start_time = (ref_time - timedelta(hours=window_hours)).isoformat()

        cursor = self.conn.execute(
            """
            SELECT 
                COUNT(*) as request_count,
                COALESCE(SUM(prompt_tokens), 0) as total_prompt,
                COALESCE(SUM(completion_tokens), 0) as total_completion,
                COALESCE(SUM(total_tokens), 0) as total_consumed
            FROM quota_events
            WHERE model = ? AND timestamp >= ? AND timestamp <= ?
            """,
            (model, start_time, ref_time.isoformat()),
        )
        row = cursor.fetchone()
        consumed = int(row["total_consumed"])
        req_count = int(row["request_count"])
        used_ratio = consumed / DEFAULT_DAILY_TOKEN_BUDGET
        remaining = max(0, DEFAULT_DAILY_TOKEN_BUDGET - consumed)

        return {
            "model": model,
            "window_hours": window_hours,
            "window_start": start_time,
            "window_end": ref_time.isoformat(),
            "requests_count": req_count,
            "prompt_tokens": int(row["total_prompt"]),
            "completion_tokens": int(row["total_completion"]),
            "tokens_consumed": consumed,
            "daily_budget": DEFAULT_DAILY_TOKEN_BUDGET,
            "used_ratio": round(used_ratio, 4),
            "used_percent": round(used_ratio * 100.0, 2),
            "remaining_tokens": remaining,
        }

    def evaluate_status(
        self,
        model: str,
        *,
        now: Optional[datetime] = None,
        estimated_next_call_tokens: int = 0,
    ) -> Dict[str, Any]:
        """Evaluate operational quota status for a model against the 90% threshold."""
        usage = self.get_window_usage(model, now=now)
        consumed = usage["tokens_consumed"]
        remaining = usage["remaining_tokens"]

        result = {
            "model": model,
            "status": "UNKNOWN",
            "accept_new_work": False,
            "finish_only": False,
            "checkpoint_required": True,
            "tokens_consumed": consumed,
            "remaining_tokens": remaining,
            "used_percent": usage["used_percent"],
            "reason": "",
            "finish_allowed": False,
        }

        if consumed >= DEFAULT_DAILY_TOKEN_BUDGET:
            result["status"] = "EXHAUSTED"
            result["reason"] = f"Daily budget of {DEFAULT_DAILY_TOKEN_BUDGET} tokens fully consumed."
            return result

        if consumed >= WIND_DOWN_THRESHOLD_TOKENS:
            result["status"] = "WIND_DOWN"
            result["finish_only"] = True
            result["reason"] = (
                f"Quota consumption ({consumed} tokens) has reached or exceeded "
                f"90% threshold ({WIND_DOWN_THRESHOLD_TOKENS} tokens). "
                "No new tasks may be admitted."
            )
            # Evaluate bounded finish for in-flight tasks
            if estimated_next_call_tokens > 0:
                required_with_buffer = estimated_next_call_tokens * (1.0 + SAFETY_MARGIN_PERCENT)
                if required_with_buffer <= remaining:
                    result["finish_allowed"] = True
                    result["reason"] += " In-flight call permitted within safety margin."
                else:
                    result["finish_allowed"] = False
                    result["reason"] += (
                        f" In-flight call requiring {required_with_buffer:.0f} tokens "
                        f"(with 25% safety buffer) exceeds remaining {remaining} tokens."
                    )
            return result

        # Below 90%
        result["status"] = "READY"
        result["accept_new_work"] = True
        result["finish_only"] = False
        result["checkpoint_required"] = False
        result["finish_allowed"] = True
        result["reason"] = "All quota limits within normal operating margins (<90%)."
        return result

    def create_checkpoint(
        self,
        checkpoint_id: str,
        model: str,
        *,
        now: Optional[datetime] = None,
        extra_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store an atomic quota checkpoint in SQLite."""
        ref_time = now or datetime.now(timezone.utc)
        if ref_time.tzinfo is None:
            raise QuotaLedgerError("now must be timezone-aware")
        ref_time = ref_time.astimezone(timezone.utc)

        eval_data = self.evaluate_status(model, now=ref_time)
        snapshot = {
            "checkpoint_id": checkpoint_id,
            "timestamp": ref_time.isoformat(),
            "model": model,
            "evaluation": eval_data,
            "extra_state": extra_state or {},
        }
        snapshot_json = json.dumps(snapshot)

        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO quota_checkpoints (
                    checkpoint_id, timestamp, model, daily_tokens_consumed,
                    daily_budget, status, snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (checkpoint_id, ref_time.isoformat(), model,
                 eval_data["tokens_consumed"], DEFAULT_DAILY_TOKEN_BUDGET,
                 eval_data["status"], snapshot_json),
            )
        return snapshot

    def verify_reset(
        self,
        model: str,
        *,
        now: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """Verify whether a refreshed quota window allows resuming from WIND_DOWN or EXHAUSTED."""
        eval_data = self.evaluate_status(model, now=now)
        if eval_data["status"] == "READY":
            return True, f"Verified reset: model {model} has {eval_data['remaining_tokens']} tokens remaining (<90% consumed)."
        return False, f"Reset not verified: model {model} is in {eval_data['status']} state ({eval_data['used_percent']}% used)."
