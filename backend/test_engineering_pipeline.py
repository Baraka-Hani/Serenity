"""The complete engineering demo must fail closed and make zero external calls."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from company.engineering_pipeline import (
    EngineeringBlocked, mock_builder, offline_review, run_offline,
    safe_output_directory, safe_read, sha256, validate_manifest, validate_proposal,
)
from company.office import CompanyOffice

SOURCE = ROOT / "company" / "fixtures" / "destination_label.py"
MANIFEST = json.loads((ROOT / "config" / "engineering_demo_task.json").read_text())


class EngineeringPipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.root = self.dir / "repository-copy"
        fixture = self.root / "company" / "fixtures" / "destination_label.py"
        fixture.parent.mkdir(parents=True)
        fixture.write_bytes(SOURCE.read_bytes())
        self.fixture = fixture
        self.manifest = dict(MANIFEST)
        self.db = self.dir / "private-company.sqlite3"
        self.artifact = self.dir / "engineering-artifact"

    def test_end_to_end_issue_patch_review_approval_and_hq(self):
        initial_bytes = self.fixture.read_bytes()
        with patch("urllib.request.urlopen", side_effect=AssertionError("no network allowed")):
            report = run_offline(
                self.manifest, source_root=self.root, artifact_root=self.artifact,
                db_path=self.db)
        self.assertEqual(report["status"], "SIMULATED_PENDING_FULL_QA")
        self.assertFalse(report["manager_commit_authorized"])
        self.assertFalse(report["owner_decision_required"])
        self.assertEqual(report["manager_quality_gate"]["status"], "BLOCKED")
        self.assertEqual(report["model_requests"], 0)
        self.assertFalse(report["model_execution_authorized"])
        self.assertFalse(report["github_repository_writes"])
        self.assertFalse(report["functional_tests_executed"])
        self.assertEqual(initial_bytes, self.fixture.read_bytes())
        self.assertTrue((self.artifact / "proposed.patch").exists())
        self.assertTrue((self.artifact / "isolated-worktree" /
                         self.manifest["target_path"]).exists())
        self.assertTrue((self.artifact / "engineering-report.json").exists())
        self.assertTrue((self.artifact / "obsidian-vault" /
                         "Serenity HQ" / "Command Centre.md").exists())
        self.assertEqual(report["builder_actual"], "deterministic fixture")
        office = CompanyOffice(self.db)
        try:
            self.assertEqual(len(office.rows("engineering_runs")), 1)
            self.assertEqual(len(office.rows("messages")), 2)
            self.assertEqual(len(office.rows("approvals")), 0)
            self.assertEqual(office.rows("tasks")[0]["state"], "IN_REVIEW")
            self.assertTrue(office.rows("messages")[0]["acknowledged"])
            self.assertFalse(office.snapshot()["execution_enabled"])
        finally:
            office.close()

    def test_idempotence_prevents_duplicate_messages_approvals(self):
        run_offline(self.manifest, source_root=self.root, artifact_root=self.artifact,
                    db_path=self.db)
        with self.assertRaises(EngineeringBlocked):
            run_offline(self.manifest, source_root=self.root,
                        artifact_root=self.dir / "artifact-two", db_path=self.db)
        office = CompanyOffice(self.db)
        try:
            self.assertEqual(len(office.rows("engineering_runs")), 1)
            self.assertEqual(len(office.rows("tasks")), 1)
            self.assertEqual(len(office.rows("approvals")), 0)
            self.assertEqual(len(office.rows("messages")), 2)
        finally:
            office.close()

    def test_mock_builder_uses_expected_source_sha(self):
        original = safe_read(self.root, self.manifest["target_path"])
        patch_data = mock_builder(self.manifest, original)
        self.assertEqual(patch_data["changes"][0]["expected_sha256"], sha256(original))
        validated = validate_proposal(patch_data, self.manifest, self.root)
        self.assertIn("title: str", validated["replacement"])

    def test_rejects_stale_patch_hash(self):
        original = safe_read(self.root, self.manifest["target_path"])
        patch_data = mock_builder(self.manifest, original)
        patch_data["changes"][0]["expected_sha256"] = "0" * 64
        with self.assertRaises(EngineeringBlocked):
            validate_proposal(patch_data, self.manifest, self.root)

    def test_rejects_absolute_traversal_and_secret_paths(self):
        for path in ("/etc/passwd", "../AGENTS.md", ".github/workflows/ci.yml",
                     "backend/data/accounts.db", "company/fixtures/../office.py",
                     "company/fixtures/.env", "company\\fixtures\\destination_label.py"):
            with self.subTest(path=path):
                payload = dict(self.manifest, target_path=path)
                with self.assertRaises(EngineeringBlocked):
                    validate_manifest(payload)

    def test_rejects_symlinked_source(self):
        self.fixture.unlink()
        self.fixture.symlink_to(SOURCE)
        with self.assertRaises(EngineeringBlocked):
            safe_read(self.root, self.manifest["target_path"])

    def test_rejects_symlinked_artifact_root(self):
        outside = self.dir / "outside"
        outside.mkdir()
        link = self.dir / "artifact-link"
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(EngineeringBlocked):
            safe_output_directory(link)

    def test_rejects_existing_output_so_no_overwrites(self):
        self.artifact.mkdir()
        with self.assertRaises(EngineeringBlocked):
            run_offline(self.manifest, source_root=self.root,
                        artifact_root=self.artifact, db_path=self.db)
        self.assertFalse((self.artifact / "proposed.patch").exists())

    def test_rejects_high_risk_and_missing_simulation_flag(self):
        for changes in ({"risk": "high"}, {"department": "operations"},
                        {"simulation_only": False}, {"source_kind": "github_issue"}):
            with self.subTest(change=changes), self.assertRaises(EngineeringBlocked):
                validate_manifest(dict(self.manifest, **changes))

    def test_rejects_extra_patch_fields_and_commands(self):
        source = safe_read(self.root, self.manifest["target_path"])
        proposal = mock_builder(self.manifest, source)
        proposal["commands"] = ["curl arbitrary.external.url"]
        with self.assertRaises(EngineeringBlocked):
            validate_proposal(proposal, self.manifest, self.root)

    def test_rejects_disallowed_import_and_code_execution(self):
        source = safe_read(self.root, self.manifest["target_path"])
        proposal = mock_builder(self.manifest, source)
        proposal["changes"][0]["replacement_text"] += "\nimport os\n"
        with self.assertRaises(EngineeringBlocked):
            validate_proposal(proposal, self.manifest, self.root)
        proposal["changes"][0]["replacement_text"] = (
            "def destination_label(title):\n    return eval(title)\n")
        with self.assertRaises(EngineeringBlocked):
            validate_proposal(proposal, self.manifest, self.root)

    def test_rejects_syntax_errors(self):
        source = safe_read(self.root, self.manifest["target_path"])
        proposal = mock_builder(self.manifest, source)
        proposal["changes"][0]["replacement_text"] = "def destination_label(\n"
        with self.assertRaises(EngineeringBlocked):
            validate_proposal(proposal, self.manifest, self.root)

    def test_rejects_large_patch(self):
        source = safe_read(self.root, self.manifest["target_path"])
        proposal = mock_builder(self.manifest, source)
        proposal["changes"][0]["replacement_text"] = "def destination_label(title):\n" + "    # x\n"*1000
        with self.assertRaises(EngineeringBlocked):
            validate_proposal(proposal, self.manifest, self.root)

    def test_reviewer_rejects_modified_fixture_behavior(self):
        source = safe_read(self.root, self.manifest["target_path"])
        proposal = mock_builder(self.manifest, source)
        proposal["changes"][0]["replacement_text"] = (
            "def destination_label(title: str) -> str:\n"
            "    return title.upper()\n")
        validated = validate_proposal(proposal, self.manifest, self.root)
        self.assertEqual(offline_review(validated)["recommendation"], "CHANGES_REQUIRED")

    def test_cli_runs_without_provider_keys_or_network(self):
        env = os.environ.copy()
        env.pop("GROQ_API_KEY", None)
        done = subprocess.run(
            [sys.executable, "-m", "company.engineering_pipeline",
             "--task", str(ROOT / "config" / "engineering_demo_task.json"),
             "--source-root", str(self.root),
             "--artifact-root", str(self.artifact),
             "--db", str(self.db)],
            cwd=ROOT, capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        data = json.loads(done.stdout)
        self.assertEqual(data["model_requests"], 0)
        self.assertEqual(data["status"], "SIMULATED_PENDING_FULL_QA")
        self.assertEqual(data["provider_cost_usd"], 0)


if __name__ == "__main__":
    unittest.main()
