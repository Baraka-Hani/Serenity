"""Integration contracts for the real-source, no-billing Module 4 pipeline."""
import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.hosted_inference import ManualContext
from company.model_dispatch import synthetic_snapshot
from company.hosted_inference import MODELS
from company.module4_pipeline import (
    ADDED_ASSERT, SOURCE_PATH, ARCH_PATH,
    Module4Blocked, check_source, mock_builder, mock_reviewer,
    run_module4, validate_builder_output, validate_review, validate_task,
)
from company.office import CompanyOffice

TASK = json.loads((ROOT / "config/module4_destination_task.json").read_text())


class Module4PipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.src = self.tmp / "safe-source"
        for path in (SOURCE_PATH, ARCH_PATH):
            destination = self.src / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, destination)
        self.out = self.tmp / "evidence"
        self.db = self.tmp / "company.sqlite3"

    def test_real_serenity_test_mock_pipeline_and_hq_audit(self):
        before = (self.src / SOURCE_PATH).read_bytes()
        report = run_module4(TASK, root=self.src, artifacts=self.out,
                             db=self.db, mode="mock")
        self.assertEqual(report["state"], "MOCK_REVIEW_PENDING_FULL_TESTS")
        self.assertEqual(report["issue"], 22)
        self.assertFalse(report["functional_tests_executed"])
        self.assertFalse(report["manager_commit_eligible"])
        self.assertFalse(report["reviewed_by_distinct_model"])
        self.assertFalse(report["github_writes"])
        self.assertEqual(report["syntax_only"]["syntax"], "pass")
        self.assertEqual((self.src / SOURCE_PATH).read_bytes(), before)
        self.assertIn(ADDED_ASSERT, (self.out / "proposed.patch").read_text())
        self.assertTrue((self.out / "reviewer-output.json").exists())
        hq = self.out / "obsidian-vault" / "Serenity HQ"
        self.assertIn("Module 4", (hq / "Command Centre.md").read_text())
        self.assertIn("Manager commit gate", (hq / "Engineering/module4-1.md").read_text())
        office = CompanyOffice(self.db)
        try:
            self.assertEqual(len(office.rows("module4_runs")), 1)
            self.assertEqual(len(office.rows("manager_quality_checks")), 1)
            self.assertEqual(len(office.rows("messages")), 2)
            self.assertEqual(len(office.rows("approvals")), 0)
            self.assertEqual(office.rows("tasks")[0]["state"], "IN_REVIEW")
            self.assertFalse(office.snapshot()["execution_enabled"])
        finally:
            office.close()

    def test_duplicate_run_refused_and_no_replays(self):
        run_module4(TASK, root=self.src, artifacts=self.out, db=self.db)
        with self.assertRaises(Module4Blocked):
            run_module4(TASK, root=self.src, artifacts=self.tmp/"another", db=self.db)
        office = CompanyOffice(self.db)
        try:
            self.assertEqual(len(office.rows("module4_runs")), 1)
            self.assertEqual(len(office.rows("messages")), 2)
        finally:
            office.close()

    def test_rejects_unsafe_or_out_of_scope_tasks(self):
        variants = [
            {"issue": 17}, {"risk": "high"}, {"department": "qa"},
            {"target_path": "backend/server.py"},
            {"target_path": "../.env"}, {"source_kind": "private_data"},
            {"architecture_path": "backend/data/roam.sqlite3"},
        ]
        for overrides in variants:
            with self.subTest(overrides=overrides):
                with self.assertRaises(Module4Blocked):
                    validate_task({**TASK, **overrides})

    def test_source_symlink_to_private_files_blocked(self):
        candidate = self.src / SOURCE_PATH
        candidate.unlink()
        candidate.symlink_to(ROOT / SOURCE_PATH)
        with self.assertRaises(Module4Blocked):
            check_source(self.src, SOURCE_PATH)

    def test_only_add_assertions_and_preserve_existing_tests(self):
        original = check_source(self.src, SOURCE_PATH)
        candidate = mock_builder(TASK, original)
        self.assertEqual(validate_builder_output(candidate, TASK, original)["added_assertions"],
                         [ADDED_ASSERT])
        for replacement in (
            original.replace("Search must be explicit", "Search could be implicit"),
            original + "\nprocess.exit(0);\n",
            original + "\n  assert(true);\n",
        ):
            with self.subTest(replacement=replacement[-40:]):
                x = dict(candidate, replacement_text=replacement)
                with self.assertRaises(Module4Blocked):
                    validate_builder_output(x, TASK, original)

    def test_shell_and_network_in_assertions_rejected(self):
        original = check_source(self.src, SOURCE_PATH)
        candidate = mock_builder(TASK, original)
        for assertion in (
            "  assert(require('child_process').execSync('echo hello'));",
            "  assert(eval('1'));",
            "  assert(fetch('https://external.example.com'));",
        ):
            candidate["replacement_text"] = original.replace(
                "  assert(requests.length === 1 && requests[0].includes('q=Lisbon'), 'Search must be explicit and go through the local API');",
                "  assert(requests.length === 1 && requests[0].includes('q=Lisbon'), 'Search must be explicit and go through the local API');" +
                "\n" + assertion)
            with self.subTest(assertion=assertion), self.assertRaises(Module4Blocked):
                validate_builder_output(candidate, TASK, original)

    def test_builder_response_key_and_hash_checks(self):
        original = check_source(self.src, SOURCE_PATH)
        for mutation in ({"source_sha256": "bad"}, {"path": "backend/server.py"},
                         {"run_key": "foreign-task"}, {"commands": ["curl"]}):
            candidate = mock_builder(TASK, original)
            candidate.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(Module4Blocked):
                validate_builder_output(candidate, TASK, original)

    def test_reviewer_identity_schema_and_risk_checks(self):
        review = mock_reviewer(TASK)
        self.assertTrue(validate_review(review, TASK)["approved"])
        for mutation in ({"run_key": "another-run"},
                         {"approved": "true"}, {"risk_flags": [1]},
                         {"executable": "node code.js"}):
            item = dict(review)
            item.update(mutation)
            with self.subTest(mutation=mutation), self.assertRaises(Module4Blocked):
                validate_review(item, TASK)

    def test_live_mode_never_invoked_without_fresh_quota_or_approval(self):
        seen = []
        def forbidden(*args, **kwargs):
            seen.append(args)
            raise AssertionError("provider must not be invoked")
        with self.assertRaises(Module4Blocked):
            run_module4(TASK, root=self.src, artifacts=self.out, db=self.db,
                        mode="live", provider=forbidden)
        self.assertEqual(seen, [])

    def test_fake_live_quota_is_not_sufficient(self):
        now = datetime.now(timezone.utc)
        quotas = {model: synthetic_snapshot(model, now=now) for model in MODELS.values()}
        with self.assertRaises(Module4Blocked):
            run_module4(TASK, root=self.src, artifacts=self.out, db=self.db,
                        mode="live", quotas=quotas, manual_context=ManualContext(True, True, True, True))
        self.assertFalse(self.out.exists())

    def test_data_remains_read_only_and_new_artifact_dir_required(self):
        self.out.mkdir()
        with self.assertRaises(Module4Blocked):
            run_module4(TASK, root=self.src, artifacts=self.out, db=self.db)
        self.assertFalse((self.out / "module4-report.json").exists())


if __name__ == "__main__":
    unittest.main()
