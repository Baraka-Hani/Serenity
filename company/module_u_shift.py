"""Quota-aware, restart-safe two-shift *coordination*, not model execution."""
from datetime import datetime, timezone

from company.checkpoint_store import checkpoint_summary, validate_ledger
from company.hosted_inference import MODELS
from company.manager import shift_at
from company.model_dispatch import decide_model, verified_reset


def assess_next_shift(ledger, snapshots, *, now, previous_snapshots=None,
                      task_ref="github:Baraka-Hani/Serenity#22"):
    """Advisory handoff; refuse missing or simulated account quota evidence."""
    validate_ledger(ledger)
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("timezone-aware review instant required")
    if not isinstance(snapshots, dict):
        raise ValueError("quota snapshots must be mapping")
    shift = shift_at(now)
    prior = checkpoint_summary(ledger)["tasks"].get(task_ref)
    result = {
        "schema_version": 1,
        "task_ref": task_ref,
        "shift": shift,
        "time": now.isoformat(),
        "current_checkpoint": prior,
        "roles": {},
        "reason": "missing verified account quota observations",
        "decision": "CHECKPOINT_NO_NEW_TASKS",
        "quota_reset_proven": False,
        "execution_enabled": False,
        "provider_calls_authorized": False,
        "manager_commits_authorized": False,
        "owner_spending_approved": False,
        "observations_are_sufficient_for_live_inference": False,
    }
    if shift == "outside_workday":
        result["reason"] = "outside coordinated 09:00–19:00 Atlantic work windows"
        return result
    # A synthetic fixture is useful for tests but must never activate work.
    evaluations = {}
    for role, model in MODELS.items():
        observation = snapshots.get(model)
        evaluation = decide_model(role, observation, now=now,
                                  manual_live=True)
        evaluations[role] = {
            "model": model,
            "quota_state": evaluation["quota_state"],
            "status": evaluation["status"],
            "reason": evaluation["reason"],
            "source": observation.get("source") if isinstance(observation, dict) else "missing",
        }
    result["roles"] = evaluations
    if any(x["source"] != "account_usage_manual" for x in evaluations.values()):
        result["reason"] = "missing or simulated quota telemetry; checkpoint required"
        return result
    if any(not x["status"] == "READY_TO_PROPOSE" for x in evaluations.values()):
        result["decision"] = "WIND_DOWN_NO_NEW_TASKS" if any(
            x["quota_state"] == "WIND_DOWN" or x["status"] == "WIND_DOWN"
            for x in evaluations.values()) else "CHECKPOINT_NO_NEW_TASKS"
        result["reason"] = "at least one request/token quota window is at 90% or unverified"
        return result
    if previous_snapshots is not None:
        if not isinstance(previous_snapshots, dict):
            raise ValueError("prior quota snapshots must be mapping")
        resets = {}
        for model in MODELS.values():
            old = previous_snapshots.get(model)
            new = snapshots.get(model)
            if not isinstance(old, dict) or not isinstance(new, dict):
                result["reason"] = "missing old/new account quota evidence"
                return result
            state = verified_reset(old, new, now=now)
            resets[model] = state
        result["reset_checks"] = resets
        if not all(s.get("resume") is True for s in resets.values()):
            result["reason"] = "provider window reset not independently demonstrated for every model"
            return result
        result["quota_reset_proven"] = True
    if prior and prior["kind"] in {"QA_HANDOFF", "QA_RESULT", "OWNER_GATE", "MANAGER_REVIEW"}:
        result["decision"] = "AWAIT_QA_DO_NOT_REBUILD"
        result["reason"] = "task is in QA/owner gate; preserve handoff, do not duplicate"
    else:
        result["decision"] = "PROPOSE_RESUME" if prior else "PROPOSE_INTAKE"
        result["reason"] = "account-provided quota windows appear ready; owner activation still required"
    return result


def shift_markdown(report):
    from company.obsidian import md
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("invalid shift status")
    lines = [
        "# Serenity Shift and Quota Readiness", "",
        "> This is a planning snapshot, not an active worker or confirmed provider account.",
        "",
        f"- Shift: **{md(report['shift'])}**",
        f"- Decision: **{md(report['decision'])}**",
        f"- Time: {md(report['time'])}",
        f"- Reason: {md(report['reason'])}",
        "- New provider calls: **DISABLED**",
        "- Manager GitHub writes: **DISABLED**",
        "- Spending authority: **NONE**",
        "", "## Independent model windows", "",
    ]
    for role, row in report.get("roles", {}).items():
        lines.append(
            f"- {md(role)} ({md(row['model'])}): "
            f"{md(row['quota_state'])}, source {md(row['source'])} — "
            f"{md(row['reason'])}")
    if not report.get("roles"):
        lines.append("_No account quota observations provided._")
    lines.extend([
        "", "The 09:00–14:00 and 14:00–19:00 Atlantic shifts are organizational, "
        "not provider quota-reset periods. No new task at or above 90% "
        "of any verified applicable quota window.",
    ])
    return "\n".join(lines) + "\n"
