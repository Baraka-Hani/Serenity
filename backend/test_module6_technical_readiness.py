"""Contracts for the technical readiness gate and event-history reconciliation."""
import hashlib
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from company.technical_readiness import (
    ReadinessBlocked, assess_candidate, reconcile_snapshots,
)
from company.checkpoint_store import empty_ledger, append_event
from company.github_quality import REQUIRED_JOBS

HEAD = "a"*40
SOURCE = b"function destination_label(title) { return title.trim(); }\n"
CANDIDATE = b"function destination_label(title) { return title.trim() || 'unknown'; }\n"


def proof():
    old_hash = hashlib.sha256(SOURCE).hexdigest()
    new_hash = hashlib.sha256(CANDIDATE).hexdigest()
    task = {
        "issue": 22, "risk": "low",
        "target_path": "backend/test_destination_picker.js",
        "original_sha256": old_hash,
        "candidate_sha256": new_hash,
        "pr_head_sha": HEAD,
        "requested_action": "branch_commit",
    }
    builder = {"model": "qwen/qwen3.8-27b", "mode": "live",
               "candidate_sha256": new_hash}
    reviewer = {"model": "openai/gpt-oss-120b", "mode": "live",
                "candidate_sha256": new_hash, "approved": True,
                "architecture_alignment": True, "findings": []}
    sandbox = {
        "candidate_sha256": new_hash,
        "actual_functional_test_executed": True,
        "passed": True,
        "sandbox": "docker_network_none_readonly_unprivileged",
    }
    pr = {
        "number": 1001, "changed_files": 1,
        "state": "open", "draft": True, "user": {"login": "serenity-manager"},
        "head": {"sha": HEAD, "ref": "ai/serenity-issue-22",
                 "repo": {"full_name": "Baraka-Hani/Serenity"}},
        "base": {"ref": "main", "repo": {"full_name": "Baraka-Hani/Serenity"}},
    }
    files = [{"filename": "backend/test_destination_picker.js",
              "status": "modified", "changes": 2}]
    check_runs = [
        {"name": name, "head_sha": HEAD, "status": "completed",
         "conclusion": "success", "app": {"slug": "github-actions"},
         "html_url": "https://github.com/Baraka-Hani/Serenity/actions/runs/1234"}
        for name in sorted(REQUIRED_JOBS)
    ]
    checks = {"total_count": len(check_runs), "check_runs": check_runs}
    reviews = [{
        "state": "APPROVED", "commit_id": HEAD,
        "user": {"login": "independent-human"},
        "submitted_at": "2026-11-14T23:00:00Z",
    }]
    return dict(task=task, original=SOURCE, candidate=CANDIDATE,
                builder=builder, reviewer=reviewer, sandbox=sandbox,
                github_pr=pr, github_files=files, github_checks=checks,
                github_reviews=reviews)


def event(ledger, eid, when, kind="WORK_CHECKPOINT"):
    return append_event(ledger, event_id=eid, kind=kind,
                        actor="operations", shift="shift_1",
                        task_ref="github:Baraka-Hani/Serenity#22",
                        timestamp=when.isoformat(),
                        payload={"checkpoint_ref": "module5-company-ledger"})


class TechnicalReadinessTests(unittest.TestCase):
    def test_exact_sha_verification_is_still_never_a_write_authorization(self):
        result = assess_candidate(**proof())
        self.assertEqual(result["status"], "READY_FOR_SEPARATE_OWNER_APPROVED_WRITER_INTEGRATION")
        self.assertEqual(result["github_evidence_state"], "GITHUB_API_CHECKS_AND_HUMAN_QA_PASSED")
        self.assertFalse(result["actual_runner_provenance_verified"])
        self.assertFalse(result["manager_commit_execution_authorized"])
        self.assertFalse(result["automatic_merge_authorized"])

    def test_no_github_evidence_blocks(self):
        item = proof()
        del item["github_pr"], item["github_files"], item["github_checks"], item["github_reviews"]
        result = assess_candidate(**item)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("actual GitHub check-runs", " ".join(result["issues"]))

    def test_mock_model_qa_cannot_verify(self):
        item = proof()
        item["reviewer"]["mode"] = "mock"
        self.assertEqual(assess_candidate(**item)["status"], "BLOCKED")

    def test_stale_reviewer_candidate_blocks(self):
        item = proof()
        item["reviewer"]["candidate_sha256"] = "b"*64
        with self.assertRaises(ReadinessBlocked):
            assess_candidate(**item)

    def test_fake_functional_test_flag_alone_never_authorizes(self):
        item = proof()
        item["sandbox"]["sandbox"] = "host_process_no_isolation"
        result = assess_candidate(**item)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["manager_commit_execution_authorized"])
        self.assertFalse(result["actual_runner_provenance_verified"])

    def test_wrong_ci_sha_and_human_self_approval_block(self):
        for mode in ("stale_ci", "self_review", "pending", "pr_head_changed"):
            item = proof()
            if mode == "stale_ci":
                item["github_checks"]["check_runs"][0]["head_sha"] = "b"*40
            elif mode == "self_review":
                item["github_reviews"][0]["user"]["login"] = "serenity-manager"
            elif mode == "pending":
                item["github_checks"]["check_runs"][0]["status"] = "queued"
            else:
                item["task"]["pr_head_sha"] = "b"*40
            with self.subTest(mode=mode):
                self.assertEqual(assess_candidate(**item)["status"], "BLOCKED")

    def test_bad_scope_source_and_financial_action_rejected(self):
        for mode in ("financial", "path", "stale_source", "no_diff"):
            item = proof()
            if mode == "financial":
                item["task"]["requested_action"] = "spending"
            elif mode == "path":
                item["task"]["target_path"] = "backend/server.py"
            elif mode == "stale_source":
                item["task"]["original_sha256"] = "b"*64
            else:
                item["candidate"] = item["original"]
            with self.subTest(mode=mode), self.assertRaises(ReadinessBlocked):
                assess_candidate(**item)

    def test_incomplete_github_check_list_blocks(self):
        item = proof()
        item["github_checks"]["check_runs"].pop()
        self.assertEqual(assess_candidate(**item)["status"], "BLOCKED")

    def test_in_sync_and_safe_fast_forward(self):
        now = datetime(2026, 11, 14, 17, tzinfo=timezone.utc)
        initial = empty_ledger()
        first = event(initial, "issue22-checkpoint-1", now)
        second = event(first, "issue22-checkpoint-2", now+timedelta(minutes=1))
        self.assertEqual(reconcile_snapshots(first, first)["status"], "IN_SYNC")
        self.assertEqual(reconcile_snapshots(first, second)["status"], "REMOTE_AHEAD")
        self.assertEqual(reconcile_snapshots(second, first)["status"], "LOCAL_AHEAD")
        self.assertFalse(reconcile_snapshots(second, first)["remote_write_authorized"])

    def test_diverged_checkpoints_never_automerge(self):
        now = datetime(2026, 11, 14, 17, tzinfo=timezone.utc)
        root = event(empty_ledger(), "issue22-checkpoint-1", now)
        a = event(root, "issue22-local-002", now+timedelta(minutes=1))
        b = event(root, "issue22-remote-002", now+timedelta(minutes=1))
        result = reconcile_snapshots(a, b)
        self.assertEqual(result["status"], "DIVERGED_BLOCKED")
        self.assertFalse(result["auto_resolve"])
        self.assertEqual(result["common_events"], 1)

    def test_corrupted_remote_chain_rejected(self):
        now = datetime(2026, 11, 14, 17, tzinfo=timezone.utc)
        root = event(empty_ledger(), "issue22-checkpoint-1", now)
        corrupt = {"schema_version": root["schema_version"],
                   "events": [dict(root["events"][0])],
                   "last_hash": root["last_hash"]}
        corrupt["events"][0]["payload"] = {"checkpoint_ref": "tampered"}
        with self.assertRaises(ValueError):
            reconcile_snapshots(root, corrupt)


if __name__ == "__main__":
    unittest.main()
