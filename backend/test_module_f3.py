"""Regression test suite for Module F3: Mock Model Dispatcher, Sandbox Attestation Harness & Manager Intent Generator.

Covers MockDispatcher (deterministic Qwen/GPT-OSS mocks and fail-closed live mode),
SandboxAttestation (cryptographic image digest and output hash binding), and
ManagerIntentGenerator (immutable draft PR intent serialization without remote writes).
100% deterministic, zero network, zero external spend.
"""

import json
import os
import unittest
from datetime import datetime, timezone

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from company.governance_validator import sha256_digest
from company.manager_intent import IntentError, ManagerIntentGenerator
from company.mock_dispatcher import DispatcherError, MockDispatcher
from company.quota_ledger import QuotaLedger
from company.sandbox_attestation import (
    AttestationError,
    SandboxAttestation,
    sha256_hex,
)


class TestMockDispatcher(unittest.TestCase):
    """Unit tests for the model dispatch adapter."""

    def setUp(self):
        self.ledger = QuotaLedger(":memory:")
        self.dispatcher = MockDispatcher(ledger=self.ledger, mode="mock")

    def tearDown(self):
        self.ledger.close()

    def test_mock_builder_dispatch(self):
        res = self.dispatcher.dispatch(
            "qwen/qwen3.8-27b",
            "Write a simple destination picker tag validator",
            task_id="TASK-101",
        )

        self.assertEqual(res["mode"], "mock")
        self.assertEqual(res["model"], "qwen/qwen3.8-27b")
        self.assertEqual(res["role"], "builder")
        self.assertEqual(res["status_code"], 200)
        self.assertIn("validateDestinationTag", res["content"])
        self.assertGreater(res["usage"]["total_tokens"], 0)

        # Verify usage was recorded in ledger
        usage = self.ledger.get_window_usage("qwen/qwen3.8-27b")
        self.assertEqual(usage["requests_count"], 1)
        self.assertEqual(usage["tokens_consumed"], res["usage"]["total_tokens"])

    def test_mock_reviewer_dispatch(self):
        res = self.dispatcher.dispatch(
            "openai/gpt-oss-120b",
            "Review git diff for destination picker tag helper",
            task_id="TASK-102",
        )

        self.assertEqual(res["role"], "reviewer")
        self.assertEqual(res["status_code"], 200)

        review = json.loads(res["content"])
        self.assertEqual(review["verdict"], "approve")
        self.assertGreaterEqual(review["confidence"], 0.90)
        self.assertIn("acceptance_criteria_met", review["checks_passed"])

    def test_reject_unapproved_model(self):
        with self.assertRaises(DispatcherError):
            self.dispatcher.dispatch("unapproved/claude-instant", "prompt")

    def test_live_mode_fails_closed_without_authorization(self):
        live_dispatcher = MockDispatcher(ledger=self.ledger, mode="live")

        # Ensure environment variables are not set
        os.environ.pop("SERENITY_CLOUD_PILOT_ENABLED", None)
        os.environ.pop("SERENITY_GROQ_FREE_VERIFIED", None)
        os.environ.pop("GROQ_API_KEY", None)

        with self.assertRaises(DispatcherError) as ctx:
            live_dispatcher.dispatch("qwen/qwen3.8-27b", "test prompt")
        self.assertIn("Live mode blocked", str(ctx.exception))


class TestSandboxAttestation(unittest.TestCase):
    """Unit tests for the sandbox attestation generator and verifier."""

    def setUp(self):
        self.orig_sha = sha256_digest(b"// original source code\n")
        self.cand_sha = sha256_digest(b"// modified candidate source code\n")
        self.target_path = "backend/test_destination_picker.js"
        self.pinned_image = "node:22-alpine@sha256:" + ("a" * 64)
        self.command = "node backend/test_destination_picker.js"
        self.stdout = "PASS: Destination picker test suite (4 tests passed)\n"

    def test_generate_and_verify_valid_attestation(self):
        att = SandboxAttestation.generate_attestation(
            candidate_sha256=self.cand_sha,
            source_sha256=self.orig_sha,
            target_path=self.target_path,
            image_digest=self.pinned_image,
            command=self.command,
            exit_code=0,
            stdout=self.stdout,
        )

        self.assertTrue(att["attestation_id"].startswith("ATT-"))
        self.assertTrue(att["verified_sandbox_execution"])
        self.assertEqual(len(att["attestation_hash"]), 64)

        ok, reasons = SandboxAttestation.verify_attestation(
            att,
            expected_candidate_sha=self.cand_sha,
            expected_image_digest=self.pinned_image,
        )
        self.assertTrue(ok)
        self.assertEqual(len(reasons), 0)

    def test_reject_unpinned_image_digest(self):
        with self.assertRaises(AttestationError):
            SandboxAttestation.generate_attestation(
                candidate_sha256=self.cand_sha,
                source_sha256=self.orig_sha,
                target_path=self.target_path,
                image_digest="node:22-alpine",  # Missing @sha256:...
                command=self.command,
                exit_code=0,
                stdout=self.stdout,
            )

    def test_verify_fails_on_candidate_mismatch(self):
        att = SandboxAttestation.generate_attestation(
            candidate_sha256=self.cand_sha,
            source_sha256=self.orig_sha,
            target_path=self.target_path,
            image_digest=self.pinned_image,
            command=self.command,
            exit_code=0,
            stdout=self.stdout,
        )

        different_sha = "0" * 64
        ok, reasons = SandboxAttestation.verify_attestation(
            att,
            expected_candidate_sha=different_sha,
            expected_image_digest=self.pinned_image,
        )
        self.assertFalse(ok)
        self.assertIn("Candidate SHA mismatch", reasons[0])

    def test_verify_fails_on_non_zero_exit_code(self):
        att = SandboxAttestation.generate_attestation(
            candidate_sha256=self.cand_sha,
            source_sha256=self.orig_sha,
            target_path=self.target_path,
            image_digest=self.pinned_image,
            command=self.command,
            exit_code=1,
            stdout="FAIL: Test assertion failed\n",
        )

        ok, reasons = SandboxAttestation.verify_attestation(
            att,
            expected_candidate_sha=self.cand_sha,
            expected_image_digest=self.pinned_image,
        )
        self.assertFalse(ok)
        self.assertIn("exit code is non-zero", reasons[0])

    def test_verify_fails_on_tampered_digest(self):
        att = SandboxAttestation.generate_attestation(
            candidate_sha256=self.cand_sha,
            source_sha256=self.orig_sha,
            target_path=self.target_path,
            image_digest=self.pinned_image,
            command=self.command,
            exit_code=0,
            stdout=self.stdout,
        )

        # Tamper with attestation hash
        att["attestation_hash"] = "e" * 64
        ok, reasons = SandboxAttestation.verify_attestation(
            att,
            expected_candidate_sha=self.cand_sha,
            expected_image_digest=self.pinned_image,
        )
        self.assertFalse(ok)
        self.assertIn("tampered attestation record", reasons[0])


class TestManagerIntent(unittest.TestCase):
    """Unit tests for the manager draft PR intent generator."""

    def setUp(self):
        self.orig_sha = sha256_digest(b"// original code\n")
        self.cand_sha = sha256_digest(b"// candidate code\n")
        self.pinned_image = "node:22-alpine@sha256:" + ("a" * 64)

        self.valid_gov = {
            "all_quality_gates_passed": True,
            "passed_gates": ["GATE_1", "GATE_2", "GATE_3", "GATE_4", "GATE_5"],
            "failed_gates": [],
        }

        self.valid_att = SandboxAttestation.generate_attestation(
            candidate_sha256=self.cand_sha,
            source_sha256=self.orig_sha,
            target_path="destination-picker.js",
            image_digest=self.pinned_image,
            command="node backend/test_destination_picker.js",
            exit_code=0,
            stdout="OK\n",
        )

    def test_generate_valid_intent(self):
        intent = ManagerIntentGenerator.generate_intent(
            issue_number=22,
            target_path="destination-picker.js",
            original_sha256=self.orig_sha,
            candidate_sha256=self.cand_sha,
            diff_patch="+ // added helper\n",
            governance_assessment=self.valid_gov,
            sandbox_attestation=self.valid_att,
            lines_added=5,
            lines_deleted=0,
        )

        self.assertTrue(intent["intent_id"].startswith("INTENT-"))
        self.assertEqual(intent["target_branch"], "main")
        self.assertTrue(intent["feature_branch"].startswith("ai/serenity-issue-22-"))
        self.assertFalse(intent["execution_permitted"])  # Invariant
        self.assertIn("Draft: AI low-risk verified candidate", intent["title"])

        serialized = ManagerIntentGenerator.serialize_intent(intent)
        parsed = json.loads(serialized)
        ok, reasons = ManagerIntentGenerator.validate_intent(parsed)
        self.assertTrue(ok)
        self.assertEqual(len(reasons), 0)

    def test_reject_intent_when_governance_fails(self):
        bad_gov = {
            "all_quality_gates_passed": False,
            "failed_gates": ["GATE_1_SCOPE_AND_RISK"],
        }
        with self.assertRaises(IntentError):
            ManagerIntentGenerator.generate_intent(
                issue_number=22,
                target_path="destination-picker.js",
                original_sha256=self.orig_sha,
                candidate_sha256=self.cand_sha,
                diff_patch="+ diff\n",
                governance_assessment=bad_gov,
                sandbox_attestation=self.valid_att,
            )

    def test_reject_intent_when_attestation_fails(self):
        bad_att = {**self.valid_att, "verified_sandbox_execution": False}
        with self.assertRaises(IntentError):
            ManagerIntentGenerator.generate_intent(
                issue_number=22,
                target_path="destination-picker.js",
                original_sha256=self.orig_sha,
                candidate_sha256=self.cand_sha,
                diff_patch="+ diff\n",
                governance_assessment=self.valid_gov,
                sandbox_attestation=bad_att,
            )


if __name__ == "__main__":
    unittest.main()
