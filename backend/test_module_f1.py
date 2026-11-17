"""Regression test suite for Module F1: Company Control Plane & Offline Verification Harness.

Covers QuotaLedger (60k token limits & 90% wind-down in SQLite),
ShiftRunner (two 5-hour shifts & atomic checkpoints), and
GovernanceValidator (5-gate fail-closed quality decision engine).
100% deterministic, zero network, zero external spend.
"""

import os
import unittest
from datetime import datetime, time, timedelta, timezone

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from company.governance_validator import GovernanceValidator, sha256_digest
from company.quota_ledger import (
    DEFAULT_DAILY_TOKEN_BUDGET,
    WIND_DOWN_THRESHOLD_TOKENS,
    QuotaLedger,
    QuotaLedgerError,
)
from company.shift_runner import ShiftError, ShiftRunner


class TestQuotaLedger(unittest.TestCase):
    """Unit tests for the SQLite-backed quota ledger."""

    def setUp(self):
        self.ledger = QuotaLedger(":memory:")
        self.model = "qwen/qwen3.8-27b"

    def tearDown(self):
        self.ledger.close()

    def test_initial_state_is_ready(self):
        status = self.ledger.evaluate_status(self.model)
        self.assertEqual(status["status"], "READY")
        self.assertTrue(status["accept_new_work"])
        self.assertFalse(status["finish_only"])
        self.assertFalse(status["checkpoint_required"])
        self.assertEqual(status["tokens_consumed"], 0)
        self.assertEqual(status["remaining_tokens"], DEFAULT_DAILY_TOKEN_BUDGET)

    def test_record_usage_and_aggregate_window(self):
        self.ledger.record_usage(self.model, 1000, 500, task_id="TASK-001")
        self.ledger.record_usage(self.model, 2000, 1000, task_id="TASK-002")

        usage = self.ledger.get_window_usage(self.model)
        self.assertEqual(usage["requests_count"], 2)
        self.assertEqual(usage["prompt_tokens"], 3000)
        self.assertEqual(usage["completion_tokens"], 1500)
        self.assertEqual(usage["tokens_consumed"], 4500)
        self.assertEqual(usage["remaining_tokens"], DEFAULT_DAILY_TOKEN_BUDGET - 4500)

    def test_reject_zero_spend_violation(self):
        with self.assertRaises(QuotaLedgerError):
            self.ledger.record_usage(self.model, 100, 100, cost_cents=0.50)

    def test_reject_negative_tokens(self):
        with self.assertRaises(QuotaLedgerError):
            self.ledger.record_usage(self.model, -10, 50)
        with self.assertRaises(QuotaLedgerError):
            self.ledger.record_usage(self.model, 50, -10)

    def test_reject_unrecognized_model(self):
        with self.assertRaises(QuotaLedgerError):
            self.ledger.record_usage("unapproved/unknown-model", 100, 100)

    def test_wind_down_threshold_trigger(self):
        # 54,000 tokens is 90% of 60,000
        self.ledger.record_usage(self.model, 30_000, 24_000)  # total 54,000
        status = self.ledger.evaluate_status(self.model)

        self.assertEqual(status["status"], "WIND_DOWN")
        self.assertFalse(status["accept_new_work"])
        self.assertTrue(status["finish_only"])
        self.assertTrue(status["checkpoint_required"])
        self.assertEqual(status["tokens_consumed"], 54_000)
        self.assertEqual(status["remaining_tokens"], 6_000)

    def test_bounded_finish_with_safety_margin(self):
        # Consume 55,000 tokens -> 5,000 tokens remaining
        self.ledger.record_usage(self.model, 30_000, 25_000)

        # In-flight task estimating 3,000 tokens:
        # 3,000 * 1.25 = 3,750 <= 5,000 -> Allowed
        status_allowed = self.ledger.evaluate_status(
            self.model, estimated_next_call_tokens=3_000
        )
        self.assertEqual(status_allowed["status"], "WIND_DOWN")
        self.assertTrue(status_allowed["finish_allowed"])

        # In-flight task estimating 4,500 tokens:
        # 4,500 * 1.25 = 5,625 > 5,000 -> Rejected
        status_denied = self.ledger.evaluate_status(
            self.model, estimated_next_call_tokens=4_500
        )
        self.assertEqual(status_denied["status"], "WIND_DOWN")
        self.assertFalse(status_denied["finish_allowed"])

    def test_exhausted_threshold(self):
        # Consume full 60,000 tokens
        self.ledger.record_usage(self.model, 35_000, 25_000)
        status = self.ledger.evaluate_status(self.model)

        self.assertEqual(status["status"], "EXHAUSTED")
        self.assertFalse(status["accept_new_work"])
        self.assertFalse(status["finish_allowed"])
        self.assertEqual(status["remaining_tokens"], 0)

    def test_create_and_query_checkpoint(self):
        self.ledger.record_usage(self.model, 5_000, 2_000)
        cp = self.ledger.create_checkpoint("CP-TEST-001", self.model)

        self.assertEqual(cp["checkpoint_id"], "CP-TEST-001")
        self.assertEqual(cp["evaluation"]["tokens_consumed"], 7_000)
        self.assertEqual(cp["evaluation"]["status"], "READY")

    def test_verify_reset(self):
        # Under 90%
        ok, msg = self.ledger.verify_reset(self.model)
        self.assertTrue(ok)

        # Exhausted
        self.ledger.record_usage(self.model, 60_000, 0)
        ok, msg = self.ledger.verify_reset(self.model)
        self.assertFalse(ok)
        self.assertIn("EXHAUSTED", msg)


class TestShiftRunner(unittest.TestCase):
    """Unit tests for the two-shift scheduler and handoff simulator."""

    def setUp(self):
        self.ledger = QuotaLedger(":memory:")
        self.runner = ShiftRunner(self.ledger)
        self.model = "qwen/qwen3.8-27b"

    def tearDown(self):
        self.ledger.close()

    def test_determine_shift_windows(self):
        # 10:30 UTC -> Shift 1
        dt_shift1 = datetime(2026, 11, 15, 10, 30, tzinfo=timezone.utc)
        s1 = self.runner.determine_shift(dt_shift1)
        self.assertEqual(s1["shift"], 1)
        self.assertTrue(s1["active"])

        # 16:00 UTC -> Shift 2
        dt_shift2 = datetime(2026, 11, 15, 16, 0, tzinfo=timezone.utc)
        s2 = self.runner.determine_shift(dt_shift2)
        self.assertEqual(s2["shift"], 2)
        self.assertTrue(s2["active"])

        # 21:00 UTC -> Off-shift
        dt_off = datetime(2026, 11, 15, 21, 0, tzinfo=timezone.utc)
        soff = self.runner.determine_shift(dt_off)
        self.assertEqual(soff["shift"], 0)
        self.assertFalse(soff["active"])

    def test_reject_naive_datetime(self):
        naive = datetime(2026, 11, 15, 10, 0)
        with self.assertRaises(ShiftError):
            self.runner.determine_shift(naive)

    def test_simulate_shift_1_success(self):
        tasks = [
            {"task_id": "TASK-101", "title": "Doc fixture", "estimated_tokens": 1000},
            {"task_id": "TASK-102", "title": "Unit test helper", "estimated_tokens": 1500},
        ]
        res = self.runner.simulate_shift(1, tasks, model=self.model)

        self.assertEqual(res["shift_number"], 1)
        self.assertEqual(len(res["completed_tasks"]), 2)
        self.assertEqual(len(res["paused_tasks"]), 0)
        self.assertIn("Shift 1 Handoff Report", res["handoff_report"])
        self.assertIn("CP-SHIFT-1", res["checkpoint"]["checkpoint_id"])

    def test_simulate_shift_wind_down_behavior(self):
        # Pre-seed ledger with 53,000 tokens (approaching 54k)
        self.ledger.record_usage(self.model, 30_000, 23_000)

        tasks = [
            # This task consumes 2,000 -> total 55,000 (crosses 54k into WIND_DOWN)
            {"task_id": "TASK-201", "title": "First task", "estimated_tokens": 2000},
            # This task requires 6,000 tokens: 6000 * 1.25 = 7500 > 5000 remaining -> Paused
            {"task_id": "TASK-202", "title": "Large task", "estimated_tokens": 6000},
        ]

        res = self.runner.simulate_shift(2, tasks, model=self.model)
        self.assertEqual(len(res["completed_tasks"]), 1)
        self.assertEqual(len(res["paused_tasks"]), 1)
        self.assertEqual(res["paused_tasks"][0]["status"], "PAUSED_WIND_DOWN_EXCEEDED")
        self.assertEqual(res["final_state"], "SHIFT_WIND_DOWN")


class TestGovernanceValidator(unittest.TestCase):
    """Unit tests for the 5-gate fail-closed quality decision engine."""

    def setUp(self):
        self.validator = GovernanceValidator()
        self.original = b"// Destination Picker\nfunction render() {}\n"
        self.candidate = b"// Destination Picker\nfunction render() { return true; }\n"
        self.orig_sha = sha256_digest(self.original)
        self.cand_sha = sha256_digest(self.candidate)
        self.head_sha = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"

        self.valid_task = {
            "issue": 22,
            "risk": "low",
            "target_path": "destination-picker.js",
            "original_sha256": self.orig_sha,
            "candidate_sha256": self.cand_sha,
        }

        self.valid_ci = {
            "head_sha": self.head_sha,
            "checks": {
                "backend-and-browser-logic": {"conclusion": "success"},
                "react-prototype": {"conclusion": "success"},
                "module5-privacy-and-architecture": {"conclusion": "success"},
            },
        }

        self.valid_builder = {"agent_id": "lead-builder", "model": "qwen/qwen3.8-27b"}
        self.valid_reviewer = {
            "agent_id": "qa-director",
            "model": "openai/gpt-oss-120b",
            "verdict": "approve",
        }
        self.valid_ruleset = {
            "enforce_on_main": True,
            "require_pull_request": True,
            "require_status_checks": True,
        }

    def test_all_gates_pass(self):
        res = self.validator.assess(
            task=self.valid_task,
            original_bytes=self.original,
            candidate_bytes=self.candidate,
            ci_evidence=self.valid_ci,
            builder_info=self.valid_builder,
            reviewer_info=self.valid_reviewer,
            ruleset_config=self.valid_ruleset,
            head_sha=self.head_sha,
        )

        self.assertTrue(res["all_quality_gates_passed"])
        self.assertEqual(len(res["failed_gates"]), 0)
        self.assertEqual(res["recommendation"], "READY_FOR_DRAFT_PR")
        # Invariant: commit execution is NEVER self-authorized
        self.assertFalse(res["manager_commit_execution_authorized"])
        self.assertFalse(res["authorized"])

    def test_gate_1_fails_on_sensitive_action(self):
        bad_task = {**self.valid_task, "requested_action": "spending"}
        res = self.validator.assess(
            task=bad_task,
            original_bytes=self.original,
            candidate_bytes=self.candidate,
            ci_evidence=self.valid_ci,
            builder_info=self.valid_builder,
            reviewer_info=self.valid_reviewer,
            head_sha=self.head_sha,
        )
        self.assertFalse(res["all_quality_gates_passed"])
        self.assertIn("GATE_1_SCOPE_AND_RISK", res["failed_gates"])
        self.assertEqual(res["recommendation"], "BLOCKED_GATES_FAILED")

    def test_gate_1_fails_on_forbidden_path(self):
        bad_task = {**self.valid_task, "target_path": ".github/workflows/ci.yml"}
        res = self.validator.assess(
            task=bad_task,
            original_bytes=self.original,
            candidate_bytes=self.candidate,
            ci_evidence=self.valid_ci,
            builder_info=self.valid_builder,
            reviewer_info=self.valid_reviewer,
            head_sha=self.head_sha,
        )
        self.assertIn("GATE_1_SCOPE_AND_RISK", res["failed_gates"])

    def test_gate_2_fails_on_sha_mismatch(self):
        bad_task = {**self.valid_task, "candidate_sha256": "0" * 64}
        res = self.validator.assess(
            task=bad_task,
            original_bytes=self.original,
            candidate_bytes=self.candidate,
            ci_evidence=self.valid_ci,
            builder_info=self.valid_builder,
            reviewer_info=self.valid_reviewer,
            head_sha=self.head_sha,
        )
        self.assertIn("GATE_2_SHA_BINDING", res["failed_gates"])

    def test_gate_3_fails_on_missing_or_failed_ci(self):
        bad_ci = {
            "head_sha": self.head_sha,
            "checks": {
                "backend-and-browser-logic": {"conclusion": "failure"},
                "react-prototype": {"conclusion": "success"},
                # module5 check missing
            },
        }
        res = self.validator.assess(
            task=self.valid_task,
            original_bytes=self.original,
            candidate_bytes=self.candidate,
            ci_evidence=bad_ci,
            builder_info=self.valid_builder,
            reviewer_info=self.valid_reviewer,
            head_sha=self.head_sha,
        )
        self.assertIn("GATE_3_CI_EVIDENCE", res["failed_gates"])

    def test_gate_4_fails_on_self_approval(self):
        # Same model / identity for both Builder and Reviewer
        bad_reviewer = {**self.valid_reviewer, "model": "qwen/qwen3.8-27b", "agent_id": "lead-builder"}
        res = self.validator.assess(
            task=self.valid_task,
            original_bytes=self.original,
            candidate_bytes=self.candidate,
            ci_evidence=self.valid_ci,
            builder_info=self.valid_builder,
            reviewer_info=bad_reviewer,
            head_sha=self.head_sha,
        )
        self.assertIn("GATE_4_ROLE_SEGREGATION", res["failed_gates"])

    def test_gate_5_fails_on_missing_ruleset(self):
        bad_ruleset = {"enforce_on_main": False, "require_pull_request": False, "require_status_checks": False}
        res = self.validator.assess(
            task=self.valid_task,
            original_bytes=self.original,
            candidate_bytes=self.candidate,
            ci_evidence=self.valid_ci,
            builder_info=self.valid_builder,
            reviewer_info=self.valid_reviewer,
            ruleset_config=bad_ruleset,
            head_sha=self.head_sha,
        )
        self.assertIn("GATE_5_RULESET_COMPLIANCE", res["failed_gates"])


if __name__ == "__main__":
    unittest.main()
