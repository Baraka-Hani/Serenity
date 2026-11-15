"""Per-model quota-aware planning for hosted Serenity engineering workers.

Works entirely offline from explicit observations. Provider response headers
are PARTIAL (RPD and TPM only), so they cannot independently authorize new
jobs. Manual subscriptions are NOT API usage entitlements.
"""
from datetime import datetime, timezone

from tools.quota_guard import assess, can_resume
from company.hosted_inference import MODELS

BUCKETS = frozenset({
    "requests_per_minute", "requests_per_day", "tokens_per_minute",
    "tokens_per_day",
})


def synthetic_snapshot(model, *, now=None, remaining_fraction=0.75):
    """Test fixture ONLY, never use as a live provider usage attestation."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or not 0 <= remaining_fraction <= 1:
        raise ValueError("invalid test time or remaining allowance")
    from datetime import timedelta
    names = [("requests_per_minute", 30, 1), ("requests_per_day", 1000, 24*60),
             ("tokens_per_minute", 8000, 1), ("tokens_per_day", 200000, 24*60)]
    return {
        "model": model, "source": "simulation", "complete": True,
        "observed_at": now.isoformat(),
        "limits": [{
            "name": name, "total": total, "remaining": int(total*remaining_fraction),
            "reset_at": (now + timedelta(minutes=minutes)).isoformat(),
            "window_id": f"synthetic-{model}-{name}-A",
        } for name, total, minutes in names],
    }


def decide_model(role, snapshot, *, now=None, estimated_token_cost=1000,
                 new_task=True, manual_live=False):
    """Advisory dispatch only: no network or executable provider permissions."""
    now = now or datetime.now(timezone.utc)
    model = MODELS.get(role)
    result = {
        "role": role, "model_id": model, "status": "BLOCKED",
        "accept_work": False, "model_call_authorized": False,
        "reason": "invalid or incomplete quota observation",
        "quota_state": "UNKNOWN", "wind_down_percent": 90,
    }
    if model is None or not isinstance(snapshot, dict) or snapshot.get("model") != model:
        return result
    if not isinstance(estimated_token_cost, int) or isinstance(estimated_token_cost, bool) or not 0 < estimated_token_cost <= 4000:
        result["reason"] = "unbounded request token estimate"
        return result
    if not isinstance(new_task, bool):
        result["reason"] = "invalid new-task indicator"
        return result
    quota = assess(snapshot, now=now)
    result["quota_state"] = quota["state"]
    result["reason"] = quota["reason"]
    observed = {x.get("name"): x for x in snapshot.get("limits", [])
                if isinstance(x, dict)}
    if set(observed) != BUCKETS:
        result["reason"] = "all four Groq request/token minute/day buckets must be observed"
        return result
    if manual_live and snapshot.get("source") != "account_usage_manual":
        result["reason"] = "mock/header-derived telemetry cannot authorize even a manual live call"
        return result
    if quota["state"] == "READY":
        for name, window in observed.items():
            needed = estimated_token_cost if name.startswith("tokens") else 1
            # Reserve the user's last 10% for wind-down, with extra safety:
            # don't start a new task that would meet/exceed the 90% line.
            if window["remaining"] - needed * 1.25 <= 0.10 * window["total"]:
                result["status"] = "WIND_DOWN"
                result["quota_state"] = "WIND_DOWN"
                result["reason"] = f"{name}: next job would exceed 90% utilization threshold"
                return result
        result["status"] = "READY_TO_PROPOSE"
        result["accept_work"] = True
        result["reason"] = "all declared quota windows below 90%, reserved completion capacity"
        return result
    if quota["state"] == "WIND_DOWN":
        result["status"] = "WIND_DOWN"
        result["reason"] = "stop new tasks, checkpoint and reserve remaining budget for bounded completion"
        return result
    result["status"] = quota["state"]
    return result


def dispatch_pair(snapshots, *, now=None, estimated_builder_tokens=1500,
                  estimated_reviewer_tokens=1200, manual_live=False):
    """Independent quotas per model; never transfer/reuse account allowance."""
    if not isinstance(snapshots, dict):
        raise ValueError("snapshots must be a mapping")
    decisions = {
        "builder": decide_model("builder", snapshots.get(MODELS["builder"]),
                                now=now, estimated_token_cost=estimated_builder_tokens,
                                manual_live=manual_live),
        "reviewer": decide_model("reviewer", snapshots.get(MODELS["reviewer"]),
                                 now=now, estimated_token_cost=estimated_reviewer_tokens,
                                 manual_live=manual_live),
    }
    return {"models": decisions, "both_ready": all(v["accept_work"] for v in decisions.values()),
            "new_task_proposed": all(v["accept_work"] for v in decisions.values()),
            "automatic_execution_authorized": False,
            "reset_policy": "new verified window + all other applicable quotas below 90%"}


def verified_reset(old_snapshot, refreshed_snapshot, *, now=None):
    """Only advise reset after distinct provider quota window evidence."""
    if not isinstance(old_snapshot, dict) or not isinstance(refreshed_snapshot, dict):
        return {"resume": False, "reason": "missing quota snapshots", "model_calls_authorized": False}
    if set(x.get("name") for x in old_snapshot.get("limits", []) if isinstance(x,dict)) != BUCKETS:
        return {"resume": False, "reason": "prior four-scope quota state incomplete", "model_calls_authorized": False}
    if set(x.get("name") for x in refreshed_snapshot.get("limits", []) if isinstance(x,dict)) != BUCKETS:
        return {"resume": False, "reason": "refreshed four-scope quota state incomplete", "model_calls_authorized": False}
    return can_resume(old_snapshot, refreshed_snapshot, now=now)
