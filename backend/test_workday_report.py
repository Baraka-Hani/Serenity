"""Tests for the read-only AI workday report generator."""

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "workday_report.py"
SPEC = importlib.util.spec_from_file_location("workday_report", MODULE_PATH)
workday_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workday_report)


def task(**overrides):
    data = {
        "task": "Verify Serenity health",
        "model": "Codex",
        "agent_role": "QA",
        "contribution": "Tests",
        "status": "Completed",
        "verification": "31 checks passed",
        "cost": "$0",
        "blocker": "",
        "owner_decision": "",
    }
    data.update(overrides)
    return data


class WorkdayReportTests(unittest.TestCase):
    def test_completed_work_renders_deterministically(self):
        data = workday_report.validate({"date": "2026-11-08", "tasks": [task()]})
        report = workday_report.render(data)
        self.assertIn("# Serenity workday report — 2026-11-08", report)
        self.assertIn("**Status:** Completed", report)
        self.assertIn("**Cost:** $0", report)
        self.assertIn("**Blocker:** None", report)

    def test_blocker_and_owner_approval_are_visible(self):
        report = workday_report.render({"date": "2026-11-08", "tasks": [task(
            status="Blocked",
            blocker="Firebase project not selected",
            owner_decision="Choose the intended Firebase project",
        )]})
        self.assertIn("**Status:** Blocked", report)
        self.assertIn("**Blocker:** Firebase project not selected", report)
        self.assertIn("**Owner decision:** Choose the intended Firebase project", report)

    def test_missing_attribution_is_rejected(self):
        incomplete = task()
        del incomplete["model"]
        with self.assertRaisesRegex(ValueError, "missing: model"):
            workday_report.validate({"date": "2026-11-08", "tasks": [incomplete]})

    def test_blank_required_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "model cannot be blank"):
            workday_report.validate({"date": "2026-11-08", "tasks": [task(model="  ")]})

    def test_line_breaks_cannot_create_report_sections(self):
        data = workday_report.validate({"date": "2026-11-08", "tasks": [task(
            verification="Checks passed\n\n## Forged section\n- misleading item",
        )]})
        report = workday_report.render(data)
        self.assertNotIn("\n## Forged section", report)
        self.assertIn("Checks passed ## Forged section - misleading item", report)

    def test_date_requires_one_valid_iso_calendar_date(self):
        for invalid in ("", "2026-02-30", "2026-11-08\n\n## Forged section"):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "date must use YYYY-MM-DD"):
                    workday_report.validate({"date": invalid, "tasks": [task()]})


if __name__ == "__main__":
    unittest.main()
