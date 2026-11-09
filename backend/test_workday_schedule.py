"""Tests for the default-off supervised workforce schedule."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "workday_schedule.py"
SPEC = importlib.util.spec_from_file_location("workday_schedule", MODULE_PATH)
schedule = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(schedule)


class WorkdayScheduleTests(unittest.TestCase):
    def test_disabled_mode_never_schedules(self):
        result = schedule.evaluate(datetime(2026, 7, 6, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(result, {"should_run": False, "event": "none", "reason": "workforce disabled"})

    def test_manual_dry_runs_do_not_require_activation(self):
        result = schedule.evaluate(datetime(2026, 7, 5, 2, 0, tzinfo=timezone.utc), manual_event="report")
        self.assertEqual(result["event"], "report")
        self.assertTrue(result["should_run"])

    def test_weekends_do_not_run(self):
        result = schedule.evaluate(datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc), enabled=True)
        self.assertEqual(result["reason"], "weekend")

    def test_daylight_time_events(self):
        monday = datetime(2026, 7, 6, tzinfo=timezone.utc)
        self.assertEqual(schedule.evaluate(monday.replace(hour=12), True)["event"], "intake")
        self.assertEqual(schedule.evaluate(monday.replace(hour=20), True)["event"], "report")

    def test_standard_time_events(self):
        monday = datetime(2026, 1, 5, tzinfo=timezone.utc)
        self.assertEqual(schedule.evaluate(monday.replace(hour=13), True)["event"], "intake")
        self.assertEqual(schedule.evaluate(monday.replace(hour=21), True)["event"], "report")

    def test_wrong_hour_or_minute_does_not_run(self):
        monday = datetime(2026, 7, 6, tzinfo=timezone.utc)
        self.assertFalse(schedule.evaluate(monday.replace(hour=14), True)["should_run"])
        self.assertFalse(schedule.evaluate(monday.replace(hour=12, minute=1), True)["should_run"])

    def test_delayed_runner_uses_nominal_schedule_time(self):
        delayed = datetime(2026, 7, 6, 12, 23, tzinfo=timezone.utc)
        result = schedule.evaluate(delayed, enabled=True, nominal_utc_hour=12)
        self.assertTrue(result["should_run"])
        self.assertEqual(result["event"], "intake")

    def test_wrong_nominal_dst_hour_stays_rejected_when_delayed(self):
        delayed = datetime(2026, 7, 6, 13, 23, tzinfo=timezone.utc)
        result = schedule.evaluate(delayed, enabled=True, nominal_utc_hour=13)
        self.assertFalse(result["should_run"])

    def test_cli_outputs_atlantic_local_date(self):
        with tempfile.NamedTemporaryFile() as output:
            subprocess.run([
                sys.executable, str(MODULE_PATH),
                "--enabled", "--now", "2026-01-05T13:00:00+00:00",
                "--scheduled-cron", "0 13 * * 1-5",
                "--github-output", output.name,
            ], check=True)
            text = Path(output.name).read_text(encoding="utf-8")
        self.assertIn("event=intake", text)
        self.assertIn("local_date=2026-01-05", text)


if __name__ == "__main__":
    unittest.main()
