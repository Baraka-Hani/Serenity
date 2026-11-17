"""Chief-of-Staff planning tests: no model calls, external writes or paid work."""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.office import CompanyOffice
from company.manager import propose_work, shift_at

AT_ONE = datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc)  # 13:00 AST
AT_TWO = datetime(2026, 11, 14, 19, 0, tzinfo=timezone.utc)  # 15:00 AST
AT_NIGHT = datetime(2026, 11, 15, 1, 0, tzinfo=timezone.utc)
MODEL = "qwen/qwen3.8-27b"
READY = {MODEL: {"state": "READY", "accept_new_work": True}}
WIND_DOWN = {MODEL: {"state": "WIND_DOWN", "accept_new_work": False}}


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.office = CompanyOffice(Path(self.temp.name) / "office.sqlite3")
        self.addCleanup(self.office.close)

    def task(self, risk="low", start=False):
        t = self.office.new_task("Task", "engineering", "Three tests pass", risk)
        self.office.transition(t, "EVALUATED", "criteria")
        self.office.assign(t, "lead-builder")
        self.office.transition(t, "QUEUED", "low-risk work")
        if start and risk == "low":
            self.office.transition(t, "IN_PROGRESS", "fixture checkpoint")
        return t

    def test_daily_shifts_are_local_not_quota_resets(self):
        self.assertEqual(shift_at(AT_ONE), "shift_1")
        self.assertEqual(shift_at(AT_TWO), "shift_2")
        self.assertEqual(shift_at(AT_NIGHT), "outside_workday")

    def test_unknown_quota_blocks_builder(self):
        t = self.task()
        result = propose_work(self.office, {}, now=AT_ONE)
        self.assertEqual(result["selected"], [])
        self.assertEqual(result["blocked"][0]["task_id"], t)
        self.assertFalse(result["execution_enabled"])

    def test_ready_quota_proposes_only(self):
        t = self.task()
        result = propose_work(self.office, READY, now=AT_ONE)
        self.assertEqual(result["selected"][0]["task_id"], t)
        self.assertFalse(result["selected"][0]["may_invoke_model"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(self.office.rows("tasks")[0]["state"], "QUEUED")

    def test_90_percent_or_exhaustion_blocks_new_work(self):
        t = self.task()
        for quotas in (WIND_DOWN, {MODEL: {"state": "EXHAUSTED"}},
                       {MODEL: {"state": "RESET_VERIFICATION_REQUIRED"}}):
            with self.subTest(quotas=quotas):
                result = propose_work(self.office, quotas, now=AT_ONE)
                self.assertEqual(result["selected"], [])
                self.assertEqual(result["blocked"][0]["task_id"], t)

    def test_finish_first_selects_active_task_before_queued(self):
        queued = self.task()
        active = self.task(start=True)
        result = propose_work(self.office, READY, now=AT_ONE)
        self.assertEqual(result["selected"][0]["task_id"], active)
        self.assertEqual(result["selected"][1]["task_id"], queued)

    def test_qa_review_is_not_sent_back_to_builder(self):
        t = self.task(start=True)
        self.office.transition(t, "IN_REVIEW", "QA has diff")
        result = propose_work(self.office, READY, now=AT_ONE)
        self.assertEqual(result["selected"], [])
        self.assertEqual(result["review_queue"][0]["task_id"], t)

    def test_pending_owner_action_blocks_task(self):
        t = self.task()
        self.office.request_approval(t, "merge", "Must ask owner")
        result = propose_work(self.office, READY, now=AT_ONE)
        self.assertEqual(result["selected"], [])
        self.assertIn("owner approval", result["blocked"][0]["why"])

    def test_high_risk_task_never_selected(self):
        t = self.task(risk="high")
        result = propose_work(self.office, READY, now=AT_ONE)
        self.assertEqual(result["selected"], [])
        self.assertIn("risk", result["blocked"][0]["why"])

    def test_after_hours_no_new_assignments(self):
        self.task()
        self.assertEqual(propose_work(self.office, READY, now=AT_NIGHT)["selected"], [])

    def test_pending_handoffs_and_owner_inbox_visible(self):
        t = self.task()
        self.office.send_message(t, "lead-builder", "qa-director", "Review output")
        self.office.request_approval(t, "deploy", "No deployment without owner")
        result = propose_work(self.office, {}, now=AT_ONE)
        self.assertEqual(len(result["pending_messages"]), 1)
        self.assertEqual(len(result["owner_approvals"]), 1)

    def test_invalid_quota_object_fails_closed(self):
        self.task()
        with self.assertRaises(ValueError):
            propose_work(self.office, [], now=AT_ONE)

    def test_capacity_limit_bounded(self):
        for _ in range(5):
            self.task()
        self.assertEqual(len(propose_work(self.office, READY, now=AT_ONE, max_candidates=2)["selected"]), 2)


if __name__ == "__main__":
    unittest.main()
