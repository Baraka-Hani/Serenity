"""Deterministic, dry-run Chief of Staff for Serenity.

Produces proposed work routing, never calls models, merges code, purchases
services, or writes to GitHub. A vetted cloud executor must be approved
separately before model proposals become actual calls.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from company.office import AGENTS

ZONE = ZoneInfo("America/Moncton")
STATES_TO_RESUME = {"IN_PROGRESS": 0, "IN_REVIEW": 1, "QUEUED": 2}
INACTIVE = {"CANCELLED", "DONE", "BLOCKED_APPROVAL", "BLOCKED_DEPENDENCY",
            "PAUSED", "BLOCKED_QUOTA", "AWAITING_OWNER_ACTION", "PROPOSED", "EVALUATED", "VERIFIED"}


def shift_at(now):
    """Organization's local shift; *not* a provider quota reset signal."""
    if now.tzinfo is None:
        raise ValueError("time needs timezone")
    local = now.astimezone(ZONE)
    hour = local.hour + local.minute / 60
    if 9 <= hour < 14:
        return "shift_1"
    if 14 <= hour < 19:
        return "shift_2"
    return "outside_workday"


def propose_work(office, quotas, *, now, max_candidates=3):
    """Inspect role states and independently assessed quota results.

    Quota dict values are outputs of the existing quota_guard.assess() method.
    A 'READY' flag is an advisory scheduling condition only. It does NOT
    indicate that actual model calls are authorized, nor replace approval of
    a provider account, task scope or spending.
    """
    if not isinstance(quotas, dict):
        raise ValueError("quota results must be a mapping")
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or not 1 <= max_candidates <= 10:
        raise ValueError("max_candidates must be between 1 and 10")
    shift = shift_at(now)
    summary = {
        "shift": shift,
        "execution_enabled": False,
        "proposals_only": True,
        "selected": [],
        "blocked": [],
        "owner_approvals": [],
        "pending_messages": [],
    }
    tasks = office.rows("tasks")
    approvals = office.rows("approvals")
    messages = office.rows("messages")
    summary["owner_approvals"] = [
        {"approval_id": a["id"], "task_id": a["task_id"], "action": a["action"]}
        for a in approvals if a["state"] == "PENDING"
    ]
    summary["pending_messages"] = [
        {"message_id": m["id"], "task_id": m["task_id"],
         "recipient": m["recipient"]} for m in messages if not m["acknowledged"]
    ]
    if shift == "outside_workday":
        summary["reason"] = "outside coordination shift; no new work proposals"
        return summary
    candidates = sorted(
        [t for t in tasks if t["state"] in STATES_TO_RESUME],
        key=lambda t: (STATES_TO_RESUME[t["state"]], t["created_at"], t["id"]))
    for task in candidates:
        if task["risk"] != "low":
            summary["blocked"].append({"task_id": task["id"], "why": "medium/high risk requires owner-led review"})
            continue
        if any(a["task_id"] == task["id"] and a["state"] == "PENDING" for a in approvals):
            summary["blocked"].append({"task_id": task["id"], "why": "owner approval pending"})
            continue
        agent_id = task["assigned_agent"]
        if agent_id not in AGENTS:
            summary["blocked"].append({"task_id": task["id"], "why": "no matching assigned agent role"})
            continue
        department, role, model = AGENTS[agent_id]
        if department != task["department"]:
            summary["blocked"].append({"task_id": task["id"], "why": "role department mismatch"})
            continue
        if model in ("workflow", "not-connected", "human-guided ChatGPT / Gemini"):
            summary["blocked"].append({"task_id": task["id"], "why": "no approved model executor for role"})
            continue
        observation = quotas.get(model)
        if not isinstance(observation, dict):
            summary["blocked"].append({"task_id": task["id"], "why": "no complete fresh quota observation"})
            continue
        if observation.get("state") != "READY" or observation.get("accept_new_work") is not True:
            summary["blocked"].append({"task_id": task["id"], "why": "quota not READY"})
            continue
        # Provider-specific validation/owner authorization still separate.
        summary["selected"].append({
            "task_id": task["id"], "department": department, "agent_role": agent_id,
            "model": model, "next_action": "checkpointed-task-first" if task["state"] == "IN_PROGRESS" else "queue-for-approved-run",
            "may_invoke_model": False,
        })
        if len(summary["selected"]) == max_candidates:
            break
    summary["reason"] = "dry-run candidate selection, no external execution"
    return summary
