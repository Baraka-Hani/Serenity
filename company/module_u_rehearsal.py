"""Deterministic manager draft-PR rehearsal using actual Serenity test source.

All QA/sandbox records in this rehearsal are SYNTHETIC fixtures and must
never enter a trusted quality gate. This module never calls GitHub or models.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from company.manager_writer import plan_branch_commit, plan_draft_pr_intent
from company.module4_pipeline import (
    SOURCE_PATH, mock_builder, validate_builder_output, check_source, validate_task,
)
from company.module_u_evidence import git_blob_sha

MANIFEST = "config/module4_destination_task.json"
BRANCH = "ai/serenity-issue-22-demo"


def rehearse_draft_pr(source_root):
    root = Path(source_root)
    manifest = root / MANIFEST
    if (root.is_symlink() or not root.is_dir() or manifest.is_symlink()
            or not manifest.is_file() or manifest.stat().st_size > 12000):
        raise ValueError("untrusted rehearsal source root or task manifest")
    task = validate_task(json.loads(manifest.read_text(encoding="utf-8")))
    original = check_source(root, SOURCE_PATH)
    candidate_info = validate_builder_output(mock_builder(task, original),
                                             task, original)
    proposed = candidate_info["replacement"]
    original_bytes = original.encode("utf-8")
    proposed_bytes = proposed.encode("utf-8")
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    proposed_sha = hashlib.sha256(proposed_bytes).hexdigest()
    # This is an intentionally fabricated test-only attestation. No model or
    # container ran; do not persist it as verified evidence.
    fake_sandbox = {
        "candidate_sha256": proposed_sha,
        "actual_functional_test_executed": True,
        "passed": True, "sandbox": "docker_network_none_readonly_unprivileged",
    }
    fake_qa = {
        "independent_model": "openai/gpt-oss-120b",
        "approved": True, "candidate_sha256": proposed_sha,
        "architecture_alignment": True, "risk_flags": [],
    }
    commit_plan = plan_branch_commit(
        branch=BRANCH, source_sha256=original_sha,
        candidate_sha256=proposed_sha, candidate_text=proposed,
        risk="low", issue=22, changed_files=[SOURCE_PATH],
        sandbox_evidence=fake_sandbox, qa_evidence=fake_qa,
        amount_requested=0)
    pr_intent = plan_draft_pr_intent(commit_plan)
    return {
        "schema_version": 1,
        "task_issue": 22,
        "task_path": SOURCE_PATH,
        "source_git_blob_sha": git_blob_sha(original_bytes),
        "candidate_git_blob_sha": git_blob_sha(proposed_bytes),
        "source_sha256": original_sha,
        "candidate_sha256": proposed_sha,
        "source_verification": "LOCAL_CHECKOUT_ONLY_NOT_AUTHENTICATED_GITHUB_BASE",
        "candidate_verification": "OFFLINE_DETERMINISTIC_MOCK_NOT_TESTED",
        "qa_and_sandbox_inputs": "FABRICATED_TEST_FIXTURES_ONLY",
        "branch": BRANCH,
        "changed_paths": [SOURCE_PATH],
        "intent": pr_intent,
        "rollback": {
            "strategy": "revert feature-branch candidate to verified original Git blob",
            "original_blob_sha": git_blob_sha(original_bytes),
            "do_not_touch_main": True,
            "requires_authenticated_github_base": True,
        },
        "ci_and_independent_review_verified": False,
        "real_sandbox_executed": False,
        "actual_ai_model_calls": 0,
        "source_written": False,
        "github_commits_created": 0,
        "github_prs_created": 0,
        "manager_write_authorized": False,
        "billing_authorized": False,
        "automatic_merge_authorized": False,
        "public_deployment_authorized": False,
        "status": "DRY_RUN_ONLY_BLOCKED_PENDING_TRUSTED_QA_AND_OWNER_SETUP",
    }
