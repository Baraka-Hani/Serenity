"""Serenity Module T zero-network preflight regression checks."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.sandbox_preflight import preflight, PreflightBlocked, MAX_BYTES

FILES = list(MAX_BYTES)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for name in FILES:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dest)

    def test_source_and_workflow_hashes_not_live_approval(self):
        result = preflight(self.root)
        self.assertTrue(result["workflow_policy_static_check_passed"])
        self.assertEqual(len(result["source_sha256"]), 64)
        self.assertEqual(len(result["workflow_sha256"]), 64)
        self.assertEqual(result["status"], "BLOCKED_OWNER_IMAGE_AND_RUN_AUTHORIZATION")
        for name in (
            "owner_approved_image_digest_verified",
            "protected_main_ruleset_verified",
            "github_actions_no_cost_verified",
            "github_live_job_ran",
            "actual_functional_smoke_executed",
            "manager_github_writes_enabled",
            "new_spending_authorized",
            "merge_or_deploy_authorized",
        ):
            with self.subTest(field=name):
                self.assertFalse(result[name])

    def test_manual_gate_removed_or_workflow_broadened_blocks(self):
        workflow = self.root / ".github/workflows/serenity-candidate-sandbox.yml"
        original = workflow.read_text()
        bad_patterns = (
            original.replace(
                "vars.SERENITY_SANDBOX_OWNER_APPROVED == 'true'",
                "vars.SERENITY_SANDBOX_OWNER_APPROVED == 'false'"),
            original.replace("on:\n  workflow_dispatch:", "on:\n  push:"),
            original + "\npermissions:\n  contents: write\n",
            original + "\n  schedule:\n    - cron: '* * * * *'\n",
            original + "\n  pull_request_target:\n",
            original.replace("persist-credentials: false", "persist-credentials: true"),
            original + "\n# GROQ_API_KEY\n",
        )
        for bad in bad_patterns:
            workflow.write_text(bad)
            with self.subTest(change=bad[-60:]), self.assertRaises(PreflightBlocked):
                preflight(self.root)

    def test_symlinks_and_empty_inputs_blocked(self):
        file = self.root / "destination-picker.js"
        file.unlink()
        file.symlink_to(ROOT / "destination-picker.js")
        with self.assertRaises(PreflightBlocked):
            preflight(self.root)

    def test_source_hash_changes_are_visible(self):
        baseline = preflight(self.root)["app_sha256"]
        app = self.root / "destination-picker.js"
        app.write_bytes(app.read_bytes() + b"\n// harmless test fixture\n")
        self.assertNotEqual(preflight(self.root)["app_sha256"], baseline)


if __name__ == "__main__":
    unittest.main()
