"""Contract tests for the manual, default-off trusted-source container smoke."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from company.sandbox_smoke import trusted_smoke, checksum
from company.sandbox_runner import SandboxBlocked

IMAGE = "docker.io/library/node:22-bookworm-slim@sha256:" + "a"*64


def mocked_result(repo_root, candidate, workspace, *, candidate_sha256,
                  approved_image_digest, owner_approved_sandbox):
    assert owner_approved_sandbox is True
    assert approved_image_digest == IMAGE
    assert hashlib.sha256(Path(candidate).read_bytes()).hexdigest() == candidate_sha256
    return {
        "candidate_sha256": candidate_sha256,
        "image_digest": approved_image_digest,
        "passed": True, "returncode": 0,
        "actual_functional_test_executed": True,
        "sandbox": "docker_network_none_readonly_unprivileged",
        "command_template": "node backend/test_destination_picker.js",
        "github_write_permissions": False,
        "stdout_tail": "mock runtime only",
        "stderr_tail": "",
    }


class ReviewedSmokeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.out = self.tmp/"smoke"

    def test_default_off_even_if_owner_flag_passed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SandboxBlocked):
                trusted_smoke(ROOT, self.out, approved_image=IMAGE,
                              owner_approved=True)
        self.assertFalse(self.out.exists())

    def test_unapproved_image_does_not_start(self):
        with patch.dict(os.environ, {"SERENITY_SANDBOX_MANUAL": "true"}):
            with self.assertRaises(SandboxBlocked):
                trusted_smoke(ROOT, self.out, approved_image=IMAGE,
                              owner_approved=True)
        self.assertFalse(self.out.exists())

    def test_validated_mock_record_never_claims_real_generated_test(self):
        env = {
            "SERENITY_SANDBOX_MANUAL": "true",
            "SERENITY_APPROVED_NODE_IMAGE": IMAGE,
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_SHA": "f"*40,
            "GITHUB_WORKFLOW_REF":
                "Baraka-Hani/Serenity/.github/workflows/serenity-candidate-sandbox.yml@refs/heads/main",
            "GITHUB_JOB": "module5-candidate-sandbox",
        }
        with patch.dict(os.environ, env), patch(
                "company.sandbox_smoke.run_manual_sandbox",
                side_effect=mocked_result) as runner:
            record = trusted_smoke(ROOT, self.out, approved_image=IMAGE,
                                   owner_approved=True)
        self.assertEqual(runner.call_count, 1)
        self.assertTrue(record["runner_result"]["passed"])
        self.assertFalse(record["model_generated_code_executed"])
        self.assertFalse(record["manager_commit_authorized"])
        self.assertEqual(record["provenance"],
                         "UNTRUSTED_OUTPUT_PENDING_INDEPENDENT_GITHUB_JOB_LOOKUP")
        saved = json.loads((self.out/"sandbox-smoke.json").read_text())
        self.assertEqual(saved["source_sha256"],
                         checksum(ROOT/"backend/test_destination_picker.js"))
        self.assertFalse((self.out/"workspace").exists())

    def test_no_output_overwrite(self):
        self.out.mkdir()
        with patch.dict(os.environ, {"SERENITY_SANDBOX_MANUAL": "true",
                                     "SERENITY_APPROVED_NODE_IMAGE": IMAGE}):
            with self.assertRaises(SandboxBlocked):
                trusted_smoke(ROOT, self.out, approved_image=IMAGE,
                              owner_approved=True)

    def test_workflow_is_manual_and_requires_owner_approval(self):
        text = (ROOT / ".github/workflows/serenity-candidate-sandbox.yml").read_text()
        for required in (
            "workflow_dispatch:",
            "contents: read",
            "github.ref == 'refs/heads/main'",
            "vars.SERENITY_SANDBOX_OWNER_APPROVED == 'true'",
            "persist-credentials: false",
            "--source-root .",
            "Execute isolated test in network-off Docker",
            "docker pull",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertNotIn("\n  schedule:", text)
        self.assertNotIn("pull_request_target:", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("GROQ_API_KEY", text)
        self.assertNotIn("GITHUB_TOKEN", text)


if __name__ == "__main__":
    unittest.main()
