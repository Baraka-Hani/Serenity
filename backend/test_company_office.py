"""Full company operating-system contract tests; only temporary local data."""
import importlib.util
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.office import CompanyOffice, AGENTS, DEPARTMENTS
from company.obsidian import export_vault
from company.demo import simulate


class OfficeContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db_path = self.root / "serenity.sqlite3"
        self.office = CompanyOffice(self.db_path)
        self.addCleanup(self.office.close)

    def task(self, dept="engineering", risk="low"):
        return self.office.new_task("Test card module", dept, "Renderable HTML card with 3 tests", risk)

    def prep(self, task_id):
        self.office.transition(task_id, "EVALUATED", "Acceptance criteria evaluated")
        self.office.assign(task_id, "lead-builder")
        self.office.transition(task_id, "QUEUED", "Approved low risk work")

    def test_initial_company_has_complete_departments_and_disabled_roles(self):
        self.assertEqual(len(self.office.rows("departments")), len(DEPARTMENTS))
        self.assertEqual(len(self.office.rows("agents")), len(AGENTS))
        self.assertTrue(all(row["enabled"] == 0 for row in self.office.rows("agents")))
        self.assertFalse(self.office.snapshot()["execution_enabled"])

    def test_reopen_preserves_all_tasks_and_roles(self):
        id_ = self.task()
        self.office.close()
        self.office = CompanyOffice(self.db_path)
        self.assertEqual(self.office.rows("tasks")[0]["id"], id_)
        self.assertEqual(len(self.office.rows("departments")), len(DEPARTMENTS))

    def test_task_rejects_missing_acceptance(self):
        with self.assertRaises(ValueError):
            self.office.new_task("title", "engineering", " ")

    def test_task_rejects_unknown_department(self):
        with self.assertRaises(ValueError):
            self.office.new_task("title", "imaginary", "criteria")

    def test_transition_requires_correct_order(self):
        id_ = self.task()
        with self.assertRaises(ValueError):
            self.office.transition(id_, "DONE", "skip steps")
        self.prep(id_)
        self.office.transition(id_, "IN_PROGRESS", "Work started only in ledger")
        self.office.transition(id_, "IN_REVIEW", "Ready to inspect")
        self.office.transition(id_, "VERIFIED", "Dummy fixture has verified evidence")
        self.office.transition(id_, "AWAITING_OWNER_ACTION", "Await owner")
        self.office.transition(id_, "DONE", "Owner accepted local record")
        self.assertEqual(self.office.rows("tasks")[0]["state"], "DONE")

    def test_high_risk_cannot_be_started(self):
        id_ = self.task(risk="high")
        self.office.transition(id_, "EVALUATED", "Owner evaluation")
        self.office.transition(id_, "QUEUED", "For owner only")
        with self.assertRaises(ValueError):
            self.office.transition(id_, "IN_PROGRESS", "Would be unsafe")

    def test_rejects_cross_department_assignment(self):
        id_ = self.task()
        self.office.transition(id_, "EVALUATED", "evaluated")
        with self.assertRaises(ValueError):
            self.office.assign(id_, "qa-director")

    def test_persistent_agent_messages_and_acknowledgement(self):
        id_ = self.task()
        msg = self.office.send_message(id_, "lead-builder", "qa-director", "Diff available")
        self.office.acknowledge(msg, "qa-director")
        self.assertTrue(self.office.rows("messages")[0]["acknowledged"])
        self.assertTrue(any(e["event_type"] == "message_ack" for e in self.office.rows("events")))

    def test_wrong_recipient_cannot_acknowledge(self):
        id_ = self.task()
        msg = self.office.send_message(id_, "lead-builder", "qa-director", "Review this")
        with self.assertRaises(ValueError):
            self.office.acknowledge(msg, "chief-of-staff")

    def test_message_requires_known_agent(self):
        with self.assertRaises(ValueError):
            self.office.send_message(self.task(), "unknown", "qa-director", "Review")

    def test_approval_requests_do_not_execute_actions(self):
        id_ = self.task()
        approval = self.office.request_approval(id_, "deploy", "Requires explicit owner decision")
        with self.assertRaises(ValueError):
            self.office.decide_approval(approval, "APPROVED", "okay")
        self.office.decide_approval(approval, "APPROVED", "Owner authorized local decision record", True)
        self.assertEqual(self.office.rows("approvals")[0]["state"], "APPROVED")
        self.assertFalse(self.office.snapshot()["execution_enabled"])

    def test_cannot_duplicate_owner_decision(self):
        approval = self.office.request_approval(self.task(), "spending", "No spend without owner")
        self.office.decide_approval(approval, "REJECTED", "Not authorized", True)
        with self.assertRaises(ValueError):
            self.office.decide_approval(approval, "APPROVED", "Override", True)

    def test_done_requires_no_pending_approval(self):
        id_ = self.task()
        self.prep(id_)
        self.office.transition(id_, "IN_PROGRESS", "fixture")
        self.office.transition(id_, "IN_REVIEW", "review")
        self.office.transition(id_, "VERIFIED", "fixture tests")
        self.office.transition(id_, "AWAITING_OWNER_ACTION", "handoff")
        self.office.request_approval(id_, "merge", "Do not merge")
        with self.assertRaises(ValueError):
            self.office.transition(id_, "DONE", "bypass approval")

    def test_checkpoint_records_branch_and_state_without_code_execution(self):
        id_ = self.task()
        self.office.checkpoint(id_, "tests pending", "agent/not-real")
        item = self.office.rows("tasks")[0]
        self.assertEqual(item["branch"], "agent/not-real")
        self.assertEqual(item["checkpoint"], "tests pending")
        self.assertFalse(self.office.snapshot()["execution_enabled"])

    def test_shift_checkpoints_record_durable_handoffs(self):
        for name in ("shift_1_start", "shift_1_end_shift_2_start", "shift_2_end"):
            self.office.shift_checkpoint(name, "demo checkpoint")
        self.assertEqual(sum(e["event_type"] == "shift_checkpoint"
                             for e in self.office.rows("events")), 3)

    def test_unrecognized_shift_blocked(self):
        with self.assertRaises(ValueError):
            self.office.shift_checkpoint("shift_3_start", "not approved")

    def test_quota_observation_is_advisory_only(self):
        self.office.record_quota_state({"state": "WIND_DOWN", "model": "qwen",
                                         "reason": "90 percent"},
                                        "simulation", "2026-11-14T12:00:00Z")
        self.assertEqual(self.office.rows("quota_snapshots")[0]["state"], "WIND_DOWN")
        self.assertFalse(self.office.snapshot()["execution_enabled"])

    def test_observability_only_table_allowlist(self):
        with self.assertRaises(ValueError):
            self.office.rows("sqlite_master")

    def test_observability_export_creates_valid_obsidian_canvas(self):
        id_ = self.task()
        self.office.send_message(id_, "lead-builder", "qa-director", "Needs review")
        self.office.request_approval(id_, "merge", "Owner review")
        out = export_vault(self.office, self.root / "vault")
        self.assertEqual(out["department_pages"], len(DEPARTMENTS))
        self.assertEqual(out["task_pages"], 1)
        canvas = json.loads((self.root / "vault" / "Serenity Company.canvas").read_text())
        self.assertEqual(len(canvas["nodes"]), len(DEPARTMENTS))
        content = (self.root / "vault" / "Serenity HQ" / "Command Centre.md").read_text()
        self.assertIn("Pending owner approvals: 1", content)
        self.assertIn("execution is disabled", content.lower())

    def test_observability_export_rejects_symlink(self):
        real = self.root / "real"
        real.mkdir()
        link = self.root / "link"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaises(ValueError):
            export_vault(self.office, link)

    def test_markdown_escape_avoids_raw_html(self):
        self.office.new_task("<script>alert(1)</script>", "research", "No html")
        export_vault(self.office, self.root / "vault")
        rendered = (self.root / "vault" / "Serenity HQ" / "Command Centre.md").read_text()
        self.assertNotIn("<script>", rendered)

    def test_full_day_demo_creates_pending_owner_decision(self):
        demo = simulate(self.root / "demo.sqlite3", self.root / "demo-vault")
        self.assertTrue(demo["simulation"])
        self.assertEqual(demo["pending_approvals"], 1)
        self.assertEqual(demo["summary"]["unacknowledged_messages"], 1)
        self.assertTrue((self.root / "demo-vault" / "Serenity Company.canvas").exists())

    def test_cli_init_and_status_in_separate_process(self):
        args = [sys.executable, "-m", "company.cli", "--db", str(self.root / "cli.sqlite3")]
        first = subprocess.run(args + ["init"], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(first.returncode, 0, first.stderr)
        snapshot = json.loads(first.stdout)
        self.assertEqual(snapshot["role_profiles"], len(AGENTS))

    def test_cli_cannot_fake_owner_confirmation(self):
        id_ = self.task()
        approval = self.office.request_approval(id_, "spending", "No new spending")
        with self.assertRaises(ValueError):
            self.office.decide_approval(approval, "APPROVED", "approve", False)


if __name__ == "__main__":
    unittest.main()
