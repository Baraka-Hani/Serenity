"""Integration smoke tests for two-shift operations and Obsidian evidence."""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.module5_demo import generate
from company.checkpoint_store import load_local


class Module5DemoTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_full_shift_recovery_and_company_hq_artifact(self):
        out = self.root / "module5"
        result = generate(out, day=date(2026, 11, 14))
        self.assertTrue(result["simulated"])
        self.assertFalse(result["github_remote_persistence_enabled"])
        self.assertFalse(result["manager_writer_enabled"])
        self.assertEqual(result["actual_autonomous_shifts"], 0)
        self.assertEqual(result["actual_code_commits"], 0)
        ledger = load_local(out/"company-checkpoint.json")
        self.assertEqual(len(ledger["events"]), 4)
        vault = out / "obsidian-vault" / "Serenity HQ"
        board = (vault / "Operations/Shift Board.md").read_text()
        readable = board.replace(chr(92), "")
        self.assertIn("SHIFT_STARTED", readable)
        self.assertIn("SHIFT_ENDED", readable)
        self.assertIn("19:00", (vault / "Shift Handoffs.md").read_text())
        self.assertIn("Module 5", (vault / "Command Centre.md").read_text())
        self.assertIn("module5-company-ledger", (out/"company-checkpoint.json").read_text())
        self.assertTrue((out/"obsidian-vault"/"Serenity Company.canvas").exists())

    def test_repeat_output_refused_without_overwriting_checkpoint(self):
        out = self.root/"module5"
        generate(out, day=date(2026, 11, 14))
        before = (out/"company-checkpoint.json").read_bytes()
        with self.assertRaises(ValueError):
            generate(out, day=date(2026, 11, 14))
        self.assertEqual(before, (out/"company-checkpoint.json").read_bytes())

    def test_invalid_day_is_not_a_live_schedule(self):
        import subprocess
        cp = subprocess.run(
            [sys.executable, "-m", "company.module5_demo", "--output",
             str(self.root/"x"), "--day", "not-a-date"],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertNotEqual(cp.returncode, 0)
        self.assertFalse((self.root/"x").exists())

if __name__ == "__main__":
    unittest.main()
