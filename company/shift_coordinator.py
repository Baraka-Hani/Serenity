"""Serenity Module 5 — two five-hour shifts, 90% quota stop and safe handoffs.

This is a deterministic coordination planner. It consumes verified snapshots
and replayable event history. It does not trigger clocks, model calls, GitHub
writes, deployments or paid work. Separate authorization and trusted
provider-specific telemetry are needed before autonomous shifts can start.
"""
from datetime import datetime, timezone

from company.checkpoint_store import (
    append_event, checkpoint_summary, validate_ledger,
)
from company.hosted_inference import MODELS
from company.manager import shift_at
from company.model_dispatch import dispatch_pair


def propose_shift(ledger, quotas, *, now=None, task_ref="github:Baraka-Hani/Serenity#22"):
    validate_ledger(ledger)
    now = now or datetime.now(timezone.utc)
    shift = shift_at(now)
    result = {
        "shift": shift,
        "task_ref": task_ref,
        "proposals_only": True,
        "unattended_execution_enabled": False,
        "provider_calls_authorized": False,
        "github_writes_authorized": False,
        "financial_spending_authorized": False,
        "decision": "CHECKPOINT",
        "reason": "",
        "quota": None,
        "prior": checkpoint_summary(ledger)["tasks"].get(task_ref),
    }
    if shift == "outside_workday":
        result["reason"] = "outside coordinated shift, preserve checkpoint"
        return result
    if not isinstance(quotas, dict):
        result["reason"] = "missing quota snapshots"
        return result
    pair = dispatch_pair(quotas, now=now)
    result["quota"] = pair
    if not pair["both_ready"]:
        states = {r: q["quota_state"] for r, q in pair["models"].items()}
        result["decision"] = "WIND_DOWN" if "WIND_DOWN" in states.values() else "CHECKPOINT"
        result["reason"] = "one or more model quota windows unavailable/at 90%; do not start a task"
        return result
    last = result["prior"]
    if last and last["kind"] in {"QA_HANDOFF", "QA_RESULT", "OWNER_GATE", "MANAGER_REVIEW"}:
        result["decision"] = "AWAIT_REVIEW"
        result["reason"] = "existing task in QA/owner gate; do not duplicate Builder work"
    else:
        result["decision"] = "PROPOSE_TASK_RESUME" if last else "PROPOSE_TASK_INTAKE"
        result["reason"] = "both model buckets look ready; activation must be separately authorized"
    return result


def record_shift_handoff(ledger, *, event_id, task_ref, now=None,
                         quota_states=None, shift_override=None):
    """Append a safe, auditable handoff, not an instruction to resume models."""
    now = now or datetime.now(timezone.utc)
    shift = shift_override if shift_override is not None else shift_at(now)
    if shift not in {"shift_1", "shift_2"}:
        raise ValueError("handoff must be recorded in a valid five-hour shift")
    status = "UNKNOWN"
    if quota_states:
        if not isinstance(quota_states, dict):
            raise ValueError("quota state summary must be a mapping")
        if any(state in ("WIND_DOWN", "EXHAUSTED", "UNKNOWN") for state in quota_states.values()):
            status = "WIND_DOWN"
        elif all(state == "READY" for state in quota_states.values()):
            status = "READY"
    return append_event(
        ledger,
        event_id=event_id, kind="SHIFT_ENDED", actor="operations",
        shift=shift, task_ref=task_ref,
        timestamp=now.isoformat(),
        payload={"reason_code": status, "checkpoint_ref": "module5-company-ledger"},
    )


def simulate_two_shifts(ledger, *, day, task_ref="github:Baraka-Hani/Serenity#22"):
    """A deterministic Moncton DST-aware fixture, never a live schedule."""
    from datetime import time
    from zoneinfo import ZoneInfo
    zone = ZoneInfo("America/Moncton")
    first = datetime.combine(day, time(9, 0), tzinfo=zone)
    change = datetime.combine(day, time(14, 0), tzinfo=zone)
    end = datetime.combine(day, time(19, 0), tzinfo=zone)
    ledger = append_event(
        ledger, event_id=day.isoformat()+"-start-1",
        kind="SHIFT_STARTED", actor="operations", shift="shift_1",
        task_ref=task_ref, timestamp=first.isoformat(), payload={"reason_code": "SIMULATION"})
    ledger = append_event(
        ledger, event_id=day.isoformat()+"-handoff-14",
        kind="SHIFT_ENDED", actor="operations", shift="shift_1",
        task_ref=task_ref, timestamp=change.isoformat(),
        payload={"reason_code": "SIMULATION", "checkpoint_ref": "module5-company-ledger"})
    ledger = append_event(
        ledger, event_id=day.isoformat()+"-start-2",
        kind="SHIFT_STARTED", actor="operations", shift="shift_2",
        task_ref=task_ref, timestamp=change.isoformat(), payload={"reason_code": "SIMULATION"})
    ledger = append_event(
        ledger, event_id=day.isoformat()+"-handoff-19",
        kind="SHIFT_ENDED", actor="operations", shift="shift_2",
        task_ref=task_ref, timestamp=end.isoformat(),
        payload={"reason_code": "SIMULATION", "checkpoint_ref": "module5-company-ledger"})
    return ledger
