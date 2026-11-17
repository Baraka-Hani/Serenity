"""Source-aware quota and both Moncton shifts; all runtime authority disabled."""
import copy
import sys
import unittest
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.checkpoint_store import empty_ledger, append_event
from company.hosted_inference import MODELS
from company.model_dispatch import synthetic_snapshot
from company.module_u_shift import assess_next_shift, shift_markdown

ATL = ZoneInfo("America/Moncton")
DAY = date(2026, 11, 14)
TASK = "github:Baraka-Hani/Serenity#22"


def at(hour, minute=0):
    return datetime(DAY.year, DAY.month, DAY.day, hour, minute, tzinfo=ATL)


def fake_account(now, fraction=0.75):
    # Synthetic observations ONLY for logic tests. The 'account_usage_manual'
    # label tests the declared data-source contract, not live account proof.
    state = {}
    for model in MODELS.values():
        item = synthetic_snapshot(model, now=now.astimezone(timezone.utc),
                                  remaining_fraction=fraction)
        item["source"] = "account_usage_manual"
        state[model] = item
    return state


class QuotaShiftTests(unittest.TestCase):
    def test_missing_account_evidence_never_starts_work(self):
        for hour in (9, 13, 14, 18):
            with self.subTest(hour=hour):
                result = assess_next_shift(empty_ledger(), {}, now=at(hour))
                self.assertEqual(result["decision"], "CHECKPOINT_NO_NEW_TASKS")
                self.assertFalse(result["provider_calls_authorized"])
                self.assertFalse(result["manager_commits_authorized"])
        self.assertIn("No account quota observations", shift_markdown(result))

    def test_outside_windows_never_uses_models(self):
        for hour in (0, 8, 19, 23):
            with self.subTest(hour=hour):
                result = assess_next_shift(empty_ledger(), fake_account(at(hour)),
                                           now=at(hour))
                self.assertEqual(result["decision"], "CHECKPOINT_NO_NEW_TASKS")
                self.assertEqual(result["shift"], "outside_workday")
                self.assertFalse(result["execution_enabled"])

    def test_simulated_quota_is_never_accepted_even_when_buckets_ready(self):
        now = at(10)
        snapshots = {m: synthetic_snapshot(m, now=now.astimezone(timezone.utc))
                     for m in MODELS.values()}
        result = assess_next_shift(empty_ledger(), snapshots, now=now)
        self.assertEqual(result["decision"], "CHECKPOINT_NO_NEW_TASKS")
        self.assertIn("simulated", result["reason"])
        self.assertFalse(result["provider_calls_authorized"])

    def test_90_percent_wind_down_by_single_model(self):
        now = at(10)
        snapshots = fake_account(now)
        snapshots[MODELS["builder"]]["limits"][0]["remaining"] = 2
        result = assess_next_shift(empty_ledger(), snapshots, now=now)
        self.assertEqual(result["decision"], "WIND_DOWN_NO_NEW_TASKS")
        self.assertFalse(result["provider_calls_authorized"])
        self.assertFalse(result["manager_commits_authorized"])

    def test_evidence_ready_is_only_a_proposal(self):
        now = at(10)
        result = assess_next_shift(empty_ledger(), fake_account(now), now=now)
        self.assertEqual(result["shift"], "shift_1")
        self.assertEqual(result["decision"], "PROPOSE_INTAKE")
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["provider_calls_authorized"])

    def test_next_shift_preserves_qa_handoff(self):
        now = at(14)
        ledger = append_event(
            empty_ledger(), event_id="issue22-qa-handoff",
            kind="QA_HANDOFF", actor="qa", shift="shift_1", task_ref=TASK,
            timestamp=at(13,59).isoformat(),
            payload={"reason_code": "WAITING_QA"})
        result = assess_next_shift(ledger, fake_account(now), now=now)
        self.assertEqual(result["shift"], "shift_2")
        self.assertEqual(result["decision"], "AWAIT_QA_DO_NOT_REBUILD")
        self.assertIn("do not duplicate", result["reason"])

    def test_wall_clock_only_never_proves_quota_reset(self):
        old_time = at(9)
        new_time = at(14)
        original = fake_account(old_time)
        new = fake_account(new_time)
        result = assess_next_shift(empty_ledger(), new, now=new_time,
                                   previous_snapshots=original)
        self.assertEqual(result["decision"], "CHECKPOINT_NO_NEW_TASKS")
        self.assertFalse(result["quota_reset_proven"])
        self.assertFalse(result["provider_calls_authorized"])

    def test_missing_reset_baseline_blocks(self):
        now = at(14)
        result = assess_next_shift(empty_ledger(), fake_account(now), now=now,
                                   previous_snapshots={})
        self.assertEqual(result["decision"], "CHECKPOINT_NO_NEW_TASKS")
        self.assertFalse(result["quota_reset_proven"])

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            assess_next_shift(empty_ledger(), {}, now=datetime(2026,11,14,10))

    def test_escaped_view_contains_no_live_claims(self):
        report = assess_next_shift(empty_ledger(), {}, now=at(10))
        rendered = shift_markdown(report)
        self.assertIn("DISABLED", rendered)
        self.assertIn("90%", rendered)
        self.assertNotIn("Model calls authorized: YES", rendered)


if __name__ == "__main__":
    unittest.main()
