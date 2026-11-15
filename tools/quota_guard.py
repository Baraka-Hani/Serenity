#!/usr/bin/env python3
"""Offline quota policy evaluator: no network, credentials, model calls or scheduling.

All results are advisory until trusted, provider-specific quota adapters and an
approved executor are implemented. No output from this tool authorizes execution.
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

WIND_DOWN_AT = 0.90
SNAPSHOT_MAX_AGE = timedelta(minutes=10)
VALID_SOURCES = {"simulation", "account_usage_manual", "cli_status_manual", "provider_headers"}
VALID_BUCKETS = {
    "five_hour", "weekly", "daily", "requests_per_day", "requests_per_minute",
    "tokens_per_day", "tokens_per_minute",
}


class QuotaError(ValueError):
    """Malformed or insufficient quota evidence."""


def instant(value):
    if not isinstance(value, str):
        raise QuotaError("timestamp must be an ISO-8601 string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise QuotaError("invalid ISO-8601 timestamp") from error
    if result.tzinfo is None:
        raise QuotaError("timestamps must carry an explicit UTC offset")
    return result.astimezone(timezone.utc)


def _validated(snapshot, now):
    if not isinstance(snapshot, dict):
        raise QuotaError("snapshot must be an object")
    if not isinstance(snapshot.get("model"), str) or not snapshot["model"].strip():
        raise QuotaError("model identifier missing")
    if snapshot.get("source") not in VALID_SOURCES:
        raise QuotaError("source unrecognized")
    if snapshot.get("complete") is not True:
        raise QuotaError("quota snapshot does not cover all applicable limits")
    observed = instant(snapshot.get("observed_at"))
    if observed > now + timedelta(minutes=1):
        raise QuotaError("future-dated observation")
    if now - observed > SNAPSHOT_MAX_AGE:
        raise QuotaError("quota observation is stale")
    buckets = snapshot.get("limits")
    if not isinstance(buckets, list) or not buckets:
        raise QuotaError("at least one quota window required")
    seen = set()
    for bucket in buckets:
        if not isinstance(bucket, dict):
            raise QuotaError("quota windows must be objects")
        name = bucket.get("name")
        if name not in VALID_BUCKETS or name in seen:
            raise QuotaError("unrecognized or duplicate quota window")
        seen.add(name)
        total, remaining = bucket.get("total"), bucket.get("remaining")
        if (isinstance(total, bool) or isinstance(remaining, bool)
                or not isinstance(total, (int, float))
                or not isinstance(remaining, (int, float))
                or not (0 < total < float("inf")) or not (0 <= remaining <= total)):
            raise QuotaError("quota total or remaining is invalid")
        reset_at = instant(bucket.get("reset_at"))
        if reset_at <= observed:
            raise QuotaError("reset time must follow observation")
        if not isinstance(bucket.get("window_id"), str) or not bucket["window_id"].strip():
            raise QuotaError("quota window_id missing")
    return observed


def assess(snapshot, *, now=None):
    """Assess one model's most restrictive quota window; fail closed on uncertainty."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise QuotaError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    model = snapshot.get("model") if isinstance(snapshot, dict) else None
    base = {
        "model": model, "state": "UNKNOWN", "accept_new_work": False,
        "model_calls_authorized": False, "finish_only": False,
        "checkpoint_required": True, "window_used_percent": None,
        "limiting_windows": [], "reset_after": [], "reason": "",
    }
    try:
        _validated(snapshot, now)
    except QuotaError as error:
        base["reason"] = str(error)
        return base

    windows = snapshot["limits"]
    overdue = [w for w in windows if instant(w["reset_at"]) <= now]
    used = {w["name"]: 100.0 * (1 - w["remaining"] / w["total"]) for w in windows}
    max_used = max(used.values())
    base["window_used_percent"] = round(max_used, 3)
    base["limiting_windows"] = [w["name"] for w in windows if used[w["name"]] >= 90 - 1e-9]
    base["reset_after"] = [
        {"name": w["name"], "reset_at": w["reset_at"]}
        for w in windows if w["name"] in base["limiting_windows"]
    ]
    if overdue:
        base["state"] = "RESET_VERIFICATION_REQUIRED"
        base["reason"] = "reset timestamp passed; obtain a fresh observation before resuming"
    elif any(w["remaining"] == 0 for w in windows):
        base["state"] = "EXHAUSTED"
        base["reason"] = "one or more applicable quota windows exhausted"
    elif max_used >= 90 - 1e-9:
        base["state"] = "WIND_DOWN"
        base["finish_only"] = True
        base["reason"] = "at least one applicable quota window consumed 90% or more"
    else:
        base["state"] = "READY"
        base["accept_new_work"] = True
        base["checkpoint_required"] = False
        base["reason"] = "all observed quota windows are below 90% used"
    return base


def plan_bounded_finish(snapshot, estimated_units, *, now=None):
    """Advise whether an in-progress model operation fits a 25% safety margin.

    Estimated usage must cover *every* active quota bucket in native units.
    For opaque subscription allowances with no defensible unit forecast, do not
    invent estimates: return NO or checkpoint with deterministic tools instead.
    This never authorizes a model call.
    """
    now = now or datetime.now(timezone.utc)
    status = assess(snapshot, now=now)
    result = {"bounded_finish_recommended": False, "model_calls_authorized": False,
              "reason": "not eligible for bounded completion"}
    if status["state"] != "WIND_DOWN":
        result["reason"] = "only an observed WIND_DOWN task can request finish capacity"
        return result
    buckets = {bucket["name"]: bucket for bucket in snapshot["limits"]}
    if not isinstance(estimated_units, dict) or estimated_units.keys() != buckets.keys():
        result["reason"] = "required cost estimates missing for one or more quota windows"
        return result
    for name, cost in estimated_units.items():
        if isinstance(cost, bool) or not isinstance(cost, (float, int)) or not (0 <= cost < float("inf")):
            result["reason"] = f"invalid estimated cost for {name}"
            return result
        if 1.25 * cost > buckets[name]["remaining"]:
            result["reason"] = f"{name}: estimated completion exceeds 80% of remaining allowance"
            return result
    result["bounded_finish_recommended"] = True
    result["reason"] = "conservative estimate fits all observed remaining quotas; owner/provider authorization is separate"
    return result


def can_resume(previous, refreshed, *, now=None):
    """Require an actual refreshed quota window, not simply 5 elapsed hours.

    No service is invoked. Both complete observations must be fresh *at the
    relevant time*, and every previously saturated quota window must advance.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise QuotaError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    try:
        if previous.get("model") != refreshed.get("model"):
            raise QuotaError("models differ")
        old_time = instant(previous.get("observed_at"))
        _validated(previous, old_time)
        _validated(refreshed, now)
        if instant(refreshed["observed_at"]) <= old_time:
            raise QuotaError("refreshed observation must be newer")
        prior = {w["name"]: w for w in previous["limits"]}
        current = {w["name"]: w for w in refreshed["limits"]}
        if prior.keys() != current.keys():
            raise QuotaError("applicable quota windows differ")
        saturated = [name for name, old in prior.items()
                     if 1 - old["remaining"] / old["total"] >= WIND_DOWN_AT - 1e-9]
        if not saturated:
            raise QuotaError("previous observation was not in wind-down")
        for name in saturated:
            old, new = prior[name], current[name]
            if (new["window_id"] == old["window_id"]
                    or instant(new["reset_at"]) <= instant(old["reset_at"])
                    or instant(refreshed["observed_at"]) < instant(old["reset_at"])):
                raise QuotaError(f"{name} has no verified new window")
        result = assess(refreshed, now=now)
        if result["state"] != "READY":
            raise QuotaError("one or more current quota windows still restrict work")
        return {"resume": True, "reason": "quota windows refreshed and all active limits below threshold",
                "model": refreshed["model"], "model_calls_authorized": False}
    except (QuotaError, AttributeError, TypeError, KeyError) as error:
        return {"resume": False, "reason": str(error), "model": refreshed.get("model"),
                "model_calls_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="offline JSON observation, no API calls")
    parser.add_argument("--now", help="timezone-aware ISO-8601 test time")
    parser.add_argument("--previous", type=Path, help="earlier observation, to test a reset")
    args = parser.parse_args()
    now = instant(args.now) if args.now else datetime.now(timezone.utc)
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    outcome = (can_resume(json.loads(args.previous.read_text(encoding="utf-8")), snapshot, now=now)
               if args.previous else assess(snapshot, now=now))
    print(json.dumps(outcome, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
