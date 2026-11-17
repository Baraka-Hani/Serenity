"""Module U integrated QA/Cloud/Shift/Manager Obsidian report checks."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.module_u_report import generate_module_u
from company.checkpoint_store import load_local

SOURCES = (
    "backend/test_destination_picker.js",
    "config/module4_destination_task.json",
    "destination-picker.js",
    ".github/workflows/serenity-candidate-sandbox.yml",
)


class ModuleUHqTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.src = self.root/"checkout"
        for name in SOURCES:
            p = self.src/name
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, p)
        self.out = self.root/"generated-module-u"

    def test_real_serenity_sources_export_owner_visible_blocked_hq(self):
        before = {name: (self.src/name).read_bytes() for name in SOURCES}
        with patch("urllib.request.urlopen", side_effect=AssertionError("no network")):
            result = generate_module_u(self.src, self.out)
        self.assertEqual(result["status"],
                         "OFFLINE_CONTROL_PLANE_VERIFIED_LIVE_COMPANY_BLOCKED")
        self.assertEqual(result["github_writes_performed"], 0)
        self.assertFalse(result["actual_sandbox_execution"])
        self.assertFalse(result["manager_writes_authorized"])
        self.assertFalse(result["verified_remote_git_read"])
        self.assertEqual(result["actual_cloud_model_calls"], 0)
        self.assertEqual(result["cloud_recovery"]["status"], "REMOTE_NOT_OBSERVED")
        self.assertEqual(result["shift_readiness"]["decision"],
                         "CHECKPOINT_NO_NEW_TASKS")
        self.assertEqual(result["candidate"]["github_prs_created"], 0)
        self.assertEqual(
            {name: (self.src/name).read_bytes() for name in SOURCES}, before)
        self.assertEqual(len(load_local(self.out/"company-checkpoint.json")["events"]), 1)
        vault = self.out/"obsidian-vault"/"Serenity HQ"
        for name in (
            "Operations/Cloud Recovery.md",
            "Operations/Shift Quotas.md",
            "Operations/Manager PR Rehearsal.md",
        ):
            with self.subTest(name=name):
                self.assertTrue((vault/name).exists())
        centre = (vault/"Command Centre.md").read_text()
        self.assertIn("Module U", centre)
        self.assertIn("Cloud Recovery", centre)
        self.assertIn("Shift Quotas", centre)
        self.assertIn("Manager PR Rehearsal", centre)
        self.assertIn("NOT LIVE", centre)
        packet = json.loads((self.out/"module-u-report.json").read_text())
        self.assertEqual(packet["candidate"]["intent"]["draft"], True)
        self.assertFalse(packet["candidate"]["intent"]["manager_branch_commit_enabled"])
        self.assertFalse(packet["candidate"]["ci_and_independent_review_verified"])
        self.assertFalse(packet["candidate"]["real_sandbox_executed"])

    def test_reusing_report_path_never_overwrites_existing_observations(self):
        generate_module_u(self.src, self.out)
        before = (self.out/"module-u-report.json").read_bytes()
        with self.assertRaises(ValueError):
            generate_module_u(self.src, self.out)
        self.assertEqual((self.out/"module-u-report.json").read_bytes(), before)

    def test_manifest_sensitive_change_is_not_exported(self):
        manifest = self.src/"config/module4_destination_task.json"
        config = json.loads(manifest.read_text())
        config["target_path"] = "backend/server.py"
        manifest.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            generate_module_u(self.src, self.out)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
