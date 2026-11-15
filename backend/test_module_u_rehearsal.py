"""Deterministic no-network manager PR and rollback rehearsal contracts."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.module_u_rehearsal import rehearse_draft_pr
from company.manager_writer import (
    ManagerWriterBlocked, write_branch_commit, create_draft_pr, merge_protected_branch,
)

SOURCE = "backend/test_destination_picker.js"
MANIFEST = "config/module4_destination_task.json"


class ManagerRehearsalTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for name in (SOURCE, MANIFEST):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target)

    def test_same_input_yields_same_safe_pr_and_rollback_plan(self):
        before = (self.root/SOURCE).read_bytes()
        first = rehearse_draft_pr(self.root)
        second = rehearse_draft_pr(self.root)
        self.assertEqual(first, second)
        self.assertEqual((self.root/SOURCE).read_bytes(), before)
        self.assertEqual(first["intent"]["base"], "main")
        self.assertTrue(first["intent"]["draft"])
        self.assertEqual(first["intent"]["changed_files_allowlist"], [SOURCE])
        self.assertEqual(len(first["intent"]["idempotency_key"]), 64)
        self.assertEqual(first["status"],
                         "DRY_RUN_ONLY_BLOCKED_PENDING_TRUSTED_QA_AND_OWNER_SETUP")
        self.assertTrue(first["rollback"]["requires_authenticated_github_base"])
        self.assertFalse(first["manager_write_authorized"])
        self.assertFalse(first["intent"]["manager_branch_commit_enabled"])
        self.assertEqual(first["github_commits_created"], 0)
        self.assertEqual(first["github_prs_created"], 0)
        self.assertEqual(first["actual_ai_model_calls"], 0)
        self.assertFalse(first["real_sandbox_executed"])

    def test_fake_qa_input_has_no_authority_or_apparently_valid_review(self):
        summary = rehearse_draft_pr(self.root)
        self.assertEqual(summary["qa_and_sandbox_inputs"],
                         "FABRICATED_TEST_FIXTURES_ONLY")
        self.assertFalse(summary["ci_and_independent_review_verified"])
        for action in (write_branch_commit, create_draft_pr, merge_protected_branch):
            with self.subTest(action=action.__name__), self.assertRaises(ManagerWriterBlocked):
                action(rehearsal=summary, approved=True)

    def test_bad_scope_cannot_be_promoted(self):
        task = self.root / MANIFEST
        baseline = json.loads(task.read_text())
        for change in (
            {"target_path": "backend/server.py"}, {"risk": "high"},
            {"issue": 26}, {"source_kind": "private_data"},
        ):
            task.write_text(json.dumps({**baseline, **change}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                rehearse_draft_pr(self.root)

    def test_source_symlink_and_long_manifest_blocked(self):
        original = self.root/SOURCE
        original.unlink()
        original.symlink_to(ROOT/SOURCE)
        with self.assertRaises(ValueError):
            rehearse_draft_pr(self.root)
        original.unlink()
        shutil.copy2(ROOT/SOURCE, original)
        (self.root/MANIFEST).write_text("x"*15000)
        with self.assertRaises(ValueError):
            rehearse_draft_pr(self.root)

    def test_no_external_network_calls(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("no network")):
            summary = rehearse_draft_pr(self.root)
        self.assertEqual(summary["actual_ai_model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
