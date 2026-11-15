"""Pure, deterministic tests of the fail-closed per-model quota governor."""
import importlib.util
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "quota_guard.py"
SPEC = importlib.util.spec_from_file_location("quota_guard", MODULE)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

START = datetime(2026, 11, 14, 13, 0, tzinfo=timezone.utc)
NOW = START + timedelta(minutes=2)
RESET = START + timedelta(hours=5)


def timestamp(value):
    return value.isoformat()


def make_snapshot(remaining=11, *, model="codex/plus", weekly_remaining=30,
                  source="account_usage_manual", observed=START, reset=RESET):
    return {
        "model": model, "source": source, "complete": True, "observed_at": timestamp(observed),
        "limits": [
            {"name": "five_hour", "total": 100, "remaining": remaining,
             "reset_at": timestamp(reset), "window_id": "fivehour-A"},
            {"name": "weekly", "total": 100, "remaining": weekly_remaining,
             "reset_at": timestamp(START + timedelta(days=5)), "window_id": "week-A"},
        ],
    }


class QuotaGuardTests(unittest.TestCase):
    def test_new_work_allowed_below_threshold(self):
        result = guard.assess(make_snapshot(remaining=11), now=NOW)
        self.assertEqual(result["state"], "READY")
        self.assertTrue(result["accept_new_work"])
        self.assertFalse(result["model_calls_authorized"])

    def test_wind_down_at_exactly_90_percent(self):
        result = guard.assess(make_snapshot(remaining=10), now=NOW)
        self.assertEqual(result["state"], "WIND_DOWN")
        self.assertFalse(result["accept_new_work"])
        self.assertTrue(result["finish_only"])
        self.assertTrue(result["checkpoint_required"])
        self.assertEqual(result["limiting_windows"], ["five_hour"])
        self.assertFalse(result["model_calls_authorized"])

    def test_exhausted_stops(self):
        result = guard.assess(make_snapshot(remaining=0), now=NOW)
        self.assertEqual(result["state"], "EXHAUSTED")
        self.assertFalse(result["finish_only"])

    def test_weekly_limit_overrides_five_hour(self):
        result = guard.assess(make_snapshot(remaining=90, weekly_remaining=5), now=NOW)
        self.assertEqual(result["state"], "WIND_DOWN")
        self.assertEqual(result["limiting_windows"], ["weekly"])

    def test_missing_observation_fails_closed(self):
        result = guard.assess({}, now=NOW)
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertFalse(result["accept_new_work"])

    def test_incomplete_observation_fails_closed(self):
        snapshot = make_snapshot()
        snapshot["complete"] = False
        self.assertEqual(guard.assess(snapshot, now=NOW)["state"], "UNKNOWN")

    def test_stale_observation_fails_closed(self):
        self.assertEqual(guard.assess(make_snapshot(), now=START+timedelta(minutes=11))["state"], "UNKNOWN")

    def test_reset_time_passed_requires_new_observation(self):
        near_reset = RESET - timedelta(minutes=2)
        snapshot = make_snapshot(remaining=1, observed=near_reset)
        result = guard.assess(snapshot, now=RESET + timedelta(seconds=30))
        self.assertEqual(result["state"], "RESET_VERIFICATION_REQUIRED")
        self.assertFalse(result["accept_new_work"])

    def test_malformed_limits_fail_closed(self):
        for remaining in [-1, 101, None, True]:
            with self.subTest(remaining=remaining):
                snapshot = make_snapshot(remaining=remaining)
                self.assertEqual(guard.assess(snapshot, now=NOW)["state"], "UNKNOWN")

    def test_unverified_sources_blocked(self):
        snapshot = make_snapshot(source="unknown_provider")
        self.assertEqual(guard.assess(snapshot, now=NOW)["state"], "UNKNOWN")

    def test_no_resume_by_clock_alone(self):
        prior = make_snapshot(remaining=9)
        later = make_snapshot(remaining=9, observed=RESET + timedelta(minutes=1),
                              reset=RESET + timedelta(hours=5))
        # Despite the later reset date, the five-hour window identifier did not change.
        result = guard.can_resume(prior, later, now=RESET + timedelta(minutes=2))
        self.assertFalse(result["resume"])

    def test_resume_only_after_verified_new_window(self):
        prior = make_snapshot(remaining=9)
        later = make_snapshot(remaining=100, observed=RESET + timedelta(minutes=1),
                              reset=RESET + timedelta(hours=5))
        later["limits"][0]["window_id"] = "fivehour-B"
        result = guard.can_resume(prior, later, now=RESET + timedelta(minutes=2))
        self.assertTrue(result["resume"])
        self.assertFalse(result["model_calls_authorized"])

    def test_weekly_exhaustion_prevents_resume(self):
        prior = make_snapshot(remaining=9, weekly_remaining=0)
        later = make_snapshot(remaining=100, observed=RESET + timedelta(minutes=1),
                              reset=RESET + timedelta(hours=5), weekly_remaining=0)
        later["limits"][0]["window_id"] = "fivehour-B"
        result = guard.can_resume(prior, later, now=RESET + timedelta(minutes=2))
        self.assertFalse(result["resume"])

    def test_no_resume_without_new_observation(self):
        snapshot = make_snapshot(remaining=9)
        self.assertFalse(guard.can_resume(snapshot, snapshot, now=NOW)["resume"])

    def test_groq_minute_or_daily_limit_controls(self):
        snapshot = {
            "model": "groq/qwen", "source": "provider_headers", "complete": True,
            "observed_at": timestamp(START),
            "limits": [
                {"name": "tokens_per_minute", "total": 1000, "remaining": 500,
                 "reset_at": timestamp(START + timedelta(minutes=1)), "window_id": "minute-A"},
                {"name": "requests_per_day", "total": 1000, "remaining": 80,
                 "reset_at": timestamp(START + timedelta(days=1)), "window_id": "day-A"},
            ],
        }
        result = guard.assess(snapshot, now=START + timedelta(seconds=20))
        self.assertEqual(result["state"], "WIND_DOWN")
        self.assertEqual(result["limiting_windows"], ["requests_per_day"])
        self.assertFalse(result["model_calls_authorized"])


if __name__ == "__main__":
    unittest.main()
