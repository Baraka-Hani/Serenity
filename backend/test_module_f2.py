"""Regression test suite for Module F2: HQ Event Bus, Obsidian Visual Exporter & Unified CLI.

Covers EventBus (cryptographic hash-chain integrity & tampering detection),
ObsidianExporter (safe note generation & valid Canvas schema), and
Company CLI (status, quota, simulate-shift, export-hq, verify-gates).
100% deterministic, zero network, zero external spend.
"""

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from company.ops_cli import main as cli_main
from company.event_bus import EventBus, EventBusError
from company.obsidian_exporter import DEPARTMENTS, ObsidianExporter
from company.quota_ledger import QuotaLedger


class TestEventBus(unittest.TestCase):
    """Unit tests for the hash-linked audit event journal."""

    def setUp(self):
        self.bus = EventBus(":memory:")

    def tearDown(self):
        self.bus.close()

    def test_publish_and_verify_genesis_event(self):
        ev = self.bus.publish(
            "TASK_PROPOSED", "research", "research-director",
            {"task_id": "TASK-001", "title": "Test proposal"}
        )

        self.assertEqual(ev["id"], 1)
        self.assertTrue(ev["event_id"].startswith("EVT-"))
        self.assertEqual(ev["previous_event_hash"], "0" * 64)
        self.assertEqual(len(ev["event_hash"]), 64)
        self.assertEqual(self.bus.count(), 1)

    def test_hash_chain_linking(self):
        ev1 = self.bus.publish("EVENT_A", "engineering", "lead-builder", {"v": 1})
        ev2 = self.bus.publish("EVENT_B", "qa", "qa-director", {"v": 2})
        ev3 = self.bus.publish("EVENT_C", "operations", "operations-director", {"v": 3})

        self.assertEqual(ev2["previous_event_hash"], ev1["event_hash"])
        self.assertEqual(ev3["previous_event_hash"], ev2["event_hash"])

        intact, msg = self.bus.verify_chain_integrity()
        self.assertTrue(intact)
        self.assertIn("all 3 events are cryptographically intact", msg)

    def test_detect_tampered_payload(self):
        self.bus.publish("EVENT_1", "engineering", "lead-builder", {"secret": "original"})
        self.bus.publish("EVENT_2", "qa", "qa-director", {"secret": "verified"})

        # Tamper directly with the SQLite database row
        with self.bus.conn:
            self.bus.conn.execute(
                "UPDATE company_events SET payload_json = ? WHERE id = 1",
                ('{"secret": "forged_modification"}',)
            )

        intact, msg = self.bus.verify_chain_integrity()
        self.assertFalse(intact)
        self.assertIn("Tampered event content", msg)

    def test_detect_broken_chain_pointer(self):
        self.bus.publish("EVENT_1", "engineering", "lead-builder", {"step": 1})
        self.bus.publish("EVENT_2", "qa", "qa-director", {"step": 2})

        with self.bus.conn:
            self.bus.conn.execute(
                "UPDATE company_events SET previous_event_hash = ? WHERE id = 2",
                ("f" * 64,)
            )

        intact, msg = self.bus.verify_chain_integrity()
        self.assertFalse(intact)
        self.assertIn("Hash chain break", msg)

    def test_query_events_with_filters(self):
        self.bus.publish("TYPE_X", "engineering", "lead-builder", {"val": 1})
        self.bus.publish("TYPE_Y", "qa", "qa-director", {"val": 2})
        self.bus.publish("TYPE_X", "qa", "qa-director", {"val": 3})

        eng_events = self.bus.get_events(department="engineering")
        self.assertEqual(len(eng_events), 1)
        self.assertEqual(eng_events[0]["department"], "engineering")

        type_x_events = self.bus.get_events(event_type="TYPE_X")
        self.assertEqual(len(type_x_events), 2)

    def test_reject_invalid_event_args(self):
        with self.assertRaises(EventBusError):
            self.bus.publish("", "engineering", "lead-builder", {})
        with self.assertRaises(EventBusError):
            self.bus.publish("TYPE", "", "lead-builder", {})
        with self.assertRaises(EventBusError):
            self.bus.publish("TYPE", "dept", "", {})
        with self.assertRaises(EventBusError):
            self.bus.publish("TYPE", "dept", "agent", "not a dict")  # type: ignore


class TestObsidianExporter(unittest.TestCase):
    """Unit tests for exporting ledger state to Obsidian vault and Canvas."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.ledger = QuotaLedger(":memory:")
        self.bus = EventBus(":memory:")
        self.exporter = ObsidianExporter(self.ledger, self.bus)

    def tearDown(self):
        self.ledger.close()
        self.bus.close()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_export_complete_vault_structure(self):
        self.ledger.record_usage("qwen/qwen3.8-27b", 2000, 1000)
        self.bus.publish("INIT", "executive", "chief-of-staff", {"status": "started"})

        result = self.exporter.export_vault(self.tmp_dir)

        hq_dir = Path(result["output_directory"])
        self.assertTrue(hq_dir.is_dir())
        self.assertTrue((hq_dir / "Command Centre.md").is_file())
        self.assertTrue((hq_dir / "Serenity Company.canvas").is_file())
        self.assertTrue((hq_dir / "Departments").is_dir())
        self.assertTrue((hq_dir / "Agents").is_dir())
        self.assertTrue((hq_dir / "Operations").is_dir())

        self.assertEqual(result["department_pages"], 7)
        self.assertEqual(result["agent_pages"], 5)
        self.assertEqual(result["operations_pages"], 3)

        # Check all department notes exist
        for dept_key, (name, _) in DEPARTMENTS.items():
            self.assertTrue((hq_dir / "Departments" / f"{name}.md").is_file())

    def test_canvas_json_schema(self):
        result = self.exporter.export_vault(self.tmp_dir)
        canvas_file = Path(result["canvas_path"])
        self.assertTrue(canvas_file.is_file())

        data = json.loads(canvas_file.read_text(encoding="utf-8"))
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertGreater(len(data["nodes"]), 0)
        self.assertGreater(len(data["edges"]), 0)

        for node in data["nodes"]:
            self.assertIn("id", node)
            self.assertIn("x", node)
            self.assertIn("y", node)
            self.assertIn("width", node)
            self.assertIn("height", node)
            self.assertIn("text", node)

    def test_symlink_rejection(self):
        sym_root = Path(self.tmp_dir) / "symlink_dir"
        os.symlink(self.tmp_dir, sym_root)
        with self.assertRaises(ValueError):
            self.exporter.export_vault(sym_root)


class TestCompanyCLI(unittest.TestCase):
    """Unit tests for the unified operations CLI."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.tmp_dir) / "test_company.sqlite")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _run_cli(self, args):
        f = io.StringIO()
        with redirect_stdout(f):
            exit_code = cli_main(["--db", self.db_path] + args)
        return exit_code, f.getvalue()

    def test_cli_status(self):
        code, out = self._run_cli(["status"])
        self.assertEqual(code, 0)
        self.assertIn("SERENITY AI COMPANY — OPERATING STATUS", out)
        self.assertIn("Zero-Spend Policy Active", out)

    def test_cli_quota(self):
        code, out = self._run_cli(["quota", "--model", "qwen/qwen3.8-27b"])
        self.assertEqual(code, 0)
        self.assertIn("Quota Telemetry for Model", out)
        self.assertIn("Tokens Consumed:", out)

    def test_cli_simulate_shift(self):
        code, out = self._run_cli(["simulate-shift", "--shift", "1", "--tasks", "2"])
        self.assertEqual(code, 0)
        self.assertIn("Shift 1 Handoff Report", out)

    def test_cli_export_hq(self):
        out_hq = str(Path(self.tmp_dir) / "export_test")
        code, out = self._run_cli(["export-hq", "--output", out_hq])
        self.assertEqual(code, 0)
        self.assertIn("Successfully exported Serenity HQ", out)

    def test_cli_verify_gates(self):
        code, out = self._run_cli(["verify-gates"])
        self.assertEqual(code, 0)
        self.assertIn("All Gates Passed:       True", out)
        self.assertIn("Manager Authorized:     False", out)

    def test_cli_verify_events(self):
        # Initial empty
        code, out = self._run_cli(["verify-events"])
        self.assertEqual(code, 0)
        self.assertIn("Event Chain Integrity: VALID", out)


if __name__ == "__main__":
    unittest.main()
