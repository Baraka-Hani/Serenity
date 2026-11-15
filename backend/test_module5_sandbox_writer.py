"""Contracts for untrusted-code sandbox isolation and manager GitHub writes."""
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.sandbox_runner import (
    SandboxBlocked, prepare_workspace, fixed_command, run_manual_sandbox,
)
from company.manager_writer import (
    ManagerWriterBlocked, plan_branch_commit, write_branch_commit,
    create_draft_pr, merge_protected_branch,
)

IMAGE = "docker.io/library/node:22-bookworm-slim@sha256:" + "a"*64
TARGET = "backend/test_destination_picker.js"


def evidence(source):
    sha = hashlib.sha256(source).hexdigest()
    return {
        "source_sha256": "b"*64,
        "candidate_sha256": sha,
        "candidate_text": source.decode("utf-8"),
        "branch": "ai/serenity-issue-22",
        "risk": "low", "issue": 22, "changed_files": [TARGET],
        "sandbox_evidence": {
            "candidate_sha256": sha,
            "actual_functional_test_executed": True,
            "passed": True, "sandbox": "docker_network_none_readonly_unprivileged",
        },
        "qa_evidence": {
            "independent_model": "openai/gpt-oss-120b",
            "approved": True, "candidate_sha256": sha,
            "architecture_alignment": True, "risk_flags": [],
        },
        "amount_requested": 0,
    }


class SandboxAndWriterContracts(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.source = self.dir / "candidate.js"
        self.source.write_bytes((ROOT / TARGET).read_bytes())
        self.sha = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def test_manual_sandbox_default_off_before_any_work(self):
        runner = []
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SandboxBlocked):
                run_manual_sandbox(ROOT, self.source, self.dir / "scratch",
                                   candidate_sha256=self.sha,
                                   approved_image_digest=IMAGE,
                                   runner=lambda *a, **kw: runner.append(a))
        self.assertFalse((self.dir/"scratch").exists())
        self.assertEqual(runner, [])

    def test_scratch_has_exactly_two_non_sensitive_files(self):
        scratch = self.dir / "scratch"
        prepared = prepare_workspace(ROOT, self.source, scratch,
                                     expected_candidate_sha256=self.sha)
        files = sorted(str(p.relative_to(scratch)) for p in scratch.rglob("*") if p.is_file())
        self.assertEqual(files, [TARGET, "destination-picker.js"])
        self.assertTrue(prepared["no_secrets_or_runtime_data"])
        self.assertNotIn("backend/data", " ".join(files))

    def test_hardened_container_flags_and_no_shell(self):
        scratch = self.dir / "scratch"
        prepare_workspace(ROOT, self.source, scratch, expected_candidate_sha256=self.sha)
        command = fixed_command(scratch, image_digest=IMAGE)
        joined = " ".join(command)
        for feature in ("--network=none", "--read-only", "--cap-drop=ALL",
                        "--security-opt=no-new-privileges", "--pids-limit=48",
                        "--memory=256m", "--pull=never", "--user=65534:65534"):
            self.assertIn(feature, joined)
        self.assertEqual(command[-2:], ["node", TARGET])
        self.assertNotIn("sh", command)
        self.assertNotIn("bash", command)
        self.assertNotIn("GITHUB_TOKEN", joined)

    def test_docker_mount_delimiter_injection_is_rejected(self):
        attack = self.dir / "bad,src=/var/run/docker.sock"
        attack.mkdir(parents=True)
        with self.assertRaises(SandboxBlocked):
            fixed_command(attack, image_digest=IMAGE)

    def test_arbitrary_pinned_digest_is_not_owner_approved(self):
        with patch.dict(os.environ, {"SERENITY_SANDBOX_MANUAL": "true"}, clear=True):
            with self.assertRaises(SandboxBlocked) as err:
                run_manual_sandbox(ROOT, self.source, self.dir / "unapproved",
                                   candidate_sha256=self.sha,
                                   approved_image_digest=IMAGE,
                                   owner_approved_sandbox=True)
        self.assertIn("not authorized", str(err.exception))
        self.assertFalse((self.dir / "unapproved").exists())

    def test_digest_and_symlink_rejected(self):
        with self.assertRaises(SandboxBlocked):
            prepare_workspace(ROOT, self.source, self.dir/"scratch",
                              expected_candidate_sha256="0"*64)
        link = self.dir / "link.js"
        link.symlink_to(self.source)
        with self.assertRaises(SandboxBlocked):
            prepare_workspace(ROOT, link, self.dir/"other",
                              expected_candidate_sha256=self.sha)

    def test_unpinned_image_and_arbitrary_runtime_blocked(self):
        scratch = self.dir / "scratch"
        scratch.mkdir()
        for image in ("node:22", "alpine:latest", "docker.io/library/node:22-bookworm-slim",
                      "ghcr.io/unknown@sha256:"+"a"*64):
            with self.subTest(image=image), self.assertRaises(SandboxBlocked):
                fixed_command(scratch, image_digest=image)

    def test_manual_authorized_runner_mock_produces_test_attestation(self):
        calls = []
        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=0, stdout="Destination picker tests passed",
                                   stderr="")
        with patch.dict(os.environ, {"SERENITY_SANDBOX_MANUAL": "true",
                                     "SERENITY_APPROVED_NODE_IMAGE": IMAGE}):
            result = run_manual_sandbox(ROOT, self.source, self.dir/"scratch",
                                       candidate_sha256=self.sha,
                                       approved_image_digest=IMAGE,
                                       owner_approved_sandbox=True, runner=fake_run)
        self.assertTrue(result["passed"])
        self.assertTrue(result["actual_functional_test_executed"])
        self.assertEqual(len(calls), 1)
        self.assertNotIn("GROQ_API_KEY", calls[0][1]["env"])
        self.assertNotIn("GITHUB_TOKEN", calls[0][1]["env"])

    def test_manager_write_plan_needs_actual_sandbox_pass_and_independent_qa(self):
        sample = evidence(self.source.read_bytes())
        result = plan_branch_commit(**sample)
        self.assertEqual(result["status"], "WAITING_TRUSTED_ATTESTATION_AND_OWNER_SETUP")
        self.assertFalse(result["manager_write_execution_authorized"])
        self.assertFalse(result["owner_per_commit_approval_required_after_activation"])
        bad = evidence(self.source.read_bytes())
        bad["sandbox_evidence"]["actual_functional_test_executed"] = False
        with self.assertRaises(ManagerWriterBlocked):
            plan_branch_commit(**bad)
        bad = evidence(self.source.read_bytes())
        bad["qa_evidence"]["independent_model"] = "qwen/qwen3.8-27b"
        with self.assertRaises(ManagerWriterBlocked):
            plan_branch_commit(**bad)

    def test_new_financial_exposure_and_high_risk_scope_blocked(self):
        original = evidence(self.source.read_bytes())
        for edit in ({"amount_requested": 0.01}, {"branch": "main"},
                     {"branch": "ai/not-serenity"}, {"risk": "high"},
                     {"changed_files": ["backend/server.py"]}, {"issue": 24}):
            with self.subTest(edit=edit), self.assertRaises(ManagerWriterBlocked):
                plan_branch_commit(**{**original, **edit})

    def test_no_git_push_pr_create_or_merge_without_separate_activation(self):
        for action in (write_branch_commit, create_draft_pr, merge_protected_branch):
            with self.subTest(action=action.__name__), self.assertRaises(ManagerWriterBlocked):
                action(token="fake", authorized=True, branch="ai/serenity-issue-22")


if __name__ == "__main__":
    unittest.main()
