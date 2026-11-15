"""Module C: fail-closed technical readiness with honest evidence provenance.

Reads already-fetched *trusted GitHub API* metadata and bounded candidate
bytes. Does not invoke AI providers, execute code, write GitHub, authorize
a manager commit, or treat user/model JSON as signed runtime attestation.
"""
import hashlib
import re

from company.github_quality import EvidenceBlocked, verify_pr_evidence

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TARGET = "backend/test_destination_picker.js"
MAX_CANDIDATE = 6500
SENSITIVE_ACTIONS = frozenset({
    "spending", "credentials", "production_deployment",
    "production_data", "public_release", "privacy_security",
})


class ReadinessBlocked(ValueError):
    pass


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def assess_candidate(*, task, original, candidate, builder, reviewer,
                     sandbox, github_pr=None, github_files=None,
                     github_checks=None, github_reviews=None):
    """Return an inspectable blocked/verified-readiness *advisory* report.

    Inputs from GitHub should be fetched independently by the read-only
    GithubQualityReader. A caller-provided dictionary is never sufficient
    authorization to commit; this module always sets execution_allowed=False.
    """
    if not isinstance(task, dict):
        raise ReadinessBlocked("task metadata missing")
    if task.get("issue") != 22 or task.get("risk") != "low" or task.get("target_path") != TARGET:
        raise ReadinessBlocked("not an allowlisted low-risk Serenity pilot task")
    if any(task.get("requested_action") == item for item in SENSITIVE_ACTIONS):
        raise ReadinessBlocked("owner-controlled activity outside pilot")
    if not isinstance(original, bytes) or not isinstance(candidate, bytes):
        raise ReadinessBlocked("source and candidate must be bounded raw bytes")
    if not (0 < len(original) < MAX_CANDIDATE and 0 < len(candidate) < MAX_CANDIDATE):
        raise ReadinessBlocked("source or candidate outside pilot size limit")
    try:
        original.decode("utf-8")
        candidate.decode("utf-8")
    except UnicodeDecodeError:
        raise ReadinessBlocked("source and candidate must be UTF-8") from None
    before_hash, after_hash = _sha256(original), _sha256(candidate)
    if before_hash == after_hash:
        raise ReadinessBlocked("candidate has no code change")
    if task.get("original_sha256") != before_hash:
        raise ReadinessBlocked("stale original source digest")
    if task.get("candidate_sha256") != after_hash:
        raise ReadinessBlocked("unbound candidate digest")
    if not isinstance(builder, dict) or not isinstance(reviewer, dict):
        raise ReadinessBlocked("Builder and independent Reviewer records required")
    if (builder.get("model") != "qwen/qwen3.8-27b"
            or reviewer.get("model") != "openai/gpt-oss-120b"
            or builder.get("candidate_sha256") != after_hash
            or reviewer.get("candidate_sha256") != after_hash):
        raise ReadinessBlocked("incorrect builder/reviewer identity or candidate binding")
    if builder.get("mode") != "live" or reviewer.get("mode") != "live":
        # Mock responses cannot qualify a candidate for real code execution.
        model_state = "MOCK_OR_UNVERIFIED"
    elif reviewer.get("approved") is True and reviewer.get("architecture_alignment") is True:
        if not isinstance(reviewer.get("findings"), list) or reviewer["findings"]:
            model_state = "CHANGES_REQUESTED"
        else:
            model_state = "SELF_REPORTED_MODEL_REVIEW"
    else:
        model_state = "CHANGES_REQUESTED"
    issues = []
    if model_state != "SELF_REPORTED_MODEL_REVIEW":
        issues.append("real independent model review not established")
    sandbox_status = "NOT_PROVEN"
    if isinstance(sandbox, dict):
        if sandbox.get("candidate_sha256") != after_hash:
            issues.append("sandbox evidence references a different candidate")
        elif sandbox.get("actual_functional_test_executed") is True and sandbox.get("passed") is True:
            if sandbox.get("sandbox") == "docker_network_none_readonly_unprivileged":
                sandbox_status = "SELF_REPORTED_PASS_PENDING_TRUSTED_GITHUB_JOB"
            else:
                issues.append("sandbox hardening requirements not established")
        else:
            issues.append("actual sandboxed functional tests not proven")
    else:
        issues.append("sandbox evidence missing")
    pr_status = "NO_TRUSTED_PR_EVIDENCE"
    confirmed_head = None
    try:
        if all(x is not None for x in (
                github_pr, github_files, github_checks, github_reviews)):
            proof = verify_pr_evidence(
                pull_request=github_pr, changed_files=github_files,
                checks=github_checks, reviews=github_reviews)
            confirmed_head = proof["head_sha"]
            pr_status = "GITHUB_API_CHECKS_AND_HUMAN_QA_PASSED"
            # This verifier enforces exact-HEAD CI and a separate human QA
            # review. It cannot by itself verify that the attached sandbox
            # record genuinely originated from the protected test runner.
            if task.get("pr_head_sha") != confirmed_head:
                issues.append("verified PR head SHA differs from task")
        else:
            issues.append("actual GitHub check-runs and PR reviewer evidence absent")
    except (EvidenceBlocked, KeyError, TypeError) as exc:
        issues.append("trusted GitHub review gate failed: " + str(exc))
    if sandbox_status == "NOT_PROVEN":
        issues.append("functional test isolation not verified")
    # Even with checks green, never authorize a write based on JSON input.
    if pr_status == "GITHUB_API_CHECKS_AND_HUMAN_QA_PASSED" and not issues:
        status = "READY_FOR_SEPARATE_OWNER_APPROVED_WRITER_INTEGRATION"
    else:
        status = "BLOCKED"
    return {
        "schema_version": 1, "issue": 22,
        "source_file": TARGET,
        "source_sha256": before_hash,
        "candidate_sha256": after_hash,
        "github_head_sha": confirmed_head,
        "model_qa_state": model_state,
        "sandbox_evidence_state": sandbox_status,
        "github_evidence_state": pr_status,
        "status": status,
        "issues": issues,
        "untrusted_json_is_not_a_security_attestation": True,
        "actual_runner_provenance_verified": False,
        "manager_commit_execution_authorized": False,
        "automatic_merge_authorized": False,
        "production_deploy_authorized": False,
        "new_spending_authorized": False,
    }


def reconcile_snapshots(local, remote):
    """Compare valid event histories without writes or automatic branch merges.

    Fail closed on divergence, preserve both histories for manual review.
    """
    from company.checkpoint_store import validate_ledger
    validate_ledger(local)
    validate_ledger(remote)
    first = local["events"]
    second = remote["events"]
    same = 0
    for a, b in zip(first, second):
        if a != b:
            break
        same += 1
    if same == len(first) == len(second):
        status = "IN_SYNC"
        next_action = "no changes required"
    elif same == len(first):
        status = "REMOTE_AHEAD"
        next_action = "download and verify remote history before further work"
    elif same == len(second):
        status = "LOCAL_AHEAD"
        next_action = "owner-approved remote CAS write with exact current Git blob SHA"
    else:
        status = "DIVERGED_BLOCKED"
        next_action = "retain both histories; manual event conflict reconciliation"
    return {
        "status": status, "common_events": same,
        "local_events": len(first), "remote_events": len(second),
        "local_head": local["last_hash"], "remote_head": remote["last_hash"],
        "auto_resolve": False, "remote_write_authorized": False,
        "next_action": next_action,
    }
