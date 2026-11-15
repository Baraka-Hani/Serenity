"""Integrated CI proof that the C-track report does not overclaim readiness."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.technical_report import generate_packet
from company.checkpoint_store import load_local

SOURCE = "backend/test_destination_picker.js"
MANIFEST = "config/module4_destination_task.json"
PREFLIGHT_INPUTS = ("destination-picker.js", ".github/workflows/serenity-candidate-sandbox.yml")


class TechnicalBriefTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "checkout"
        for name in (SOURCE, MANIFEST, *PREFLIGHT_INPUTS):
            dest = self.src / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dest)
        self.out = self.root / "readiness-artifact"

    def test_actual_serenity_source_yields_mock_not_activated_hq(self):
        source_before = (self.src / SOURCE).read_bytes()
        with patch("urllib.request.urlopen", side_effect=AssertionError("no network")):
            result = generate_packet(self.src, self.out)
        self.assertEqual(result["readiness"]["status"], "BLOCKED")
        self.assertEqual(result["actual_ai_calls"], 0)
        self.assertFalse(result["sandbox_actual_functional_test_executed"])
        self.assertFalse(result["manager_branch_commit_enabled"])
        self.assertFalse(result["remote_cloud_checkpoint_confirmed"])
        self.assertFalse(result["github_exact_head_proof_fetched"])
        self.assertEqual(source_before, (self.src / SOURCE).read_bytes())
        self.assertEqual(load_local(self.out/"company-checkpoint.json")["events"][0]["kind"],
                         "QA_HANDOFF")
        vault = self.out/"obsidian-vault"/"Serenity HQ"
        self.assertIn("Module 5", (vault/"Command Centre.md").read_text())
        self.assertTrue((vault/"Operations/Shift Board.md").exists())
        self.assertTrue((vault/"Tasks/task-1.md").exists())
        self.assertTrue((self.out/"READINESS.md").exists())
        self.assertEqual(result["sandbox_preflight"]["status"],
                         "BLOCKED_OWNER_IMAGE_AND_RUN_AUTHORIZATION")
        self.assertTrue((self.out/"sandbox-preflight.json").exists())
        self.assertIn("Module T", (vault/"Command Centre.md").read_text())
        self.assertTrue((vault/"Operations/Sandbox Preflight.md").exists())
        self.assertIn("MOCK", (self.out/"READINESS.md").read_text().upper())
        expected = json.loads((self.out/"technical-readiness.json").read_text())
        self.assertEqual(expected["readiness"], result["readiness"])

    def test_no_overwrites_or_confused_run_replay(self):
        generate_packet(self.src, self.out)
        prior = (self.out/"company-checkpoint.json").read_bytes()
        with self.assertRaises(ValueError):
            generate_packet(self.src, self.out)
        self.assertEqual((self.out/"company-checkpoint.json").read_bytes(), prior)

    def test_suspicious_manifest_scope_refused(self):
        manifest = self.src / MANIFEST
        payload = json.loads(manifest.read_text())
        payload["target_path"] = "backend/data/users.sqlite3"
        manifest.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            generate_packet(self.src, self.out)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
