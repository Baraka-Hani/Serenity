"""Candidate-bound sandbox evidence and independent GitHub job matching.

An integrity checksum catches accidental modification, not impersonation.
Only evidence read independently from GitHub's official REST API can
corroborate job/run identity. Even a matching job is NOT an authorization
to commit, merge, deploy, access secrets or enable an unattended worker.
"""
from __future__ import annotations

import hashlib
import json
import re

from company.sandbox_runner import IMAGE_PATTERN

HEX64 = re.compile(r"^[a-f0-9]{64}$")
HEX40 = re.compile(r"^[a-f0-9]{40}$")
JOB = "module5-candidate-sandbox"
WORKFLOW = ".github/workflows/serenity-candidate-sandbox.yml"
REPO = "Baraka-Hani/Serenity"
COMMAND = "node backend/test_destination_picker.js"


class AttestationBlocked(ValueError):
    pass


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("utf-8")).hexdigest()


def create_claim(result, *, head_sha, run_id, run_attempt, job_id,
                 source_sha256, app_sha256):
    """Prepare a bounded checksum record from an *already executed* runner.

    This is merely a claim until checked against GitHub-owned metadata.
    """
    if not isinstance(result, dict) or not {
            "candidate_sha256", "image_digest", "passed", "returncode",
            "actual_functional_test_executed", "sandbox", "command_template"
            }.issubset(result):
        raise AttestationBlocked("runner result incomplete")
    if (not isinstance(head_sha, str) or not HEX40.fullmatch(head_sha)
            or not all(isinstance(s, str) and HEX64.fullmatch(s)
                       for s in (result["candidate_sha256"], source_sha256, app_sha256))
            or not isinstance(result["image_digest"], str)
            or not IMAGE_PATTERN.fullmatch(result["image_digest"])):
        raise AttestationBlocked("source or image digest invalid")
    if (any(type(v) is not int or v <= 0 for v in (run_id, run_attempt, job_id))
            or result["actual_functional_test_executed"] is not True
            or result["sandbox"] != "docker_network_none_readonly_unprivileged"
            or result["command_template"] != COMMAND
            or type(result["passed"]) is not bool
            or type(result["returncode"]) is not int
            or (result["passed"] is not (result["returncode"] == 0))):
        raise AttestationBlocked("invalid run identity or execution semantics")
    if result.get("github_write_permissions") is not False:
        raise AttestationBlocked("runtime must not have GitHub write permissions")
    record = {
        "schema_version": 1,
        "repository": REPO,
        "workflow": WORKFLOW,
        "job_name": JOB,
        "github": {
            "head_sha": head_sha, "run_id": run_id,
            "run_attempt": run_attempt, "job_id": job_id,
        },
        "candidate_sha256": result["candidate_sha256"],
        "source_sha256": source_sha256,
        "app_sha256": app_sha256,
        "image_digest": result["image_digest"],
        "command": COMMAND,
        "sandbox": result["sandbox"],
        "passed": result["passed"],
        "returncode": result["returncode"],
        "stdout_sha256": canonical_hash(str(result.get("stdout_tail", ""))),
        "stderr_sha256": canonical_hash(str(result.get("stderr_tail", ""))),
        "classification": "UNTRUSTED_RUNNER_CLAIM",
    }
    record["checksum_sha256"] = canonical_hash(record)
    return record


def validate_claim(record):
    if (not isinstance(record, dict) or set(record) != {
            "schema_version", "repository", "workflow", "job_name", "github",
            "candidate_sha256", "source_sha256", "app_sha256", "image_digest",
            "command", "sandbox", "passed", "returncode", "stdout_sha256",
            "stderr_sha256", "classification", "checksum_sha256"}):
        raise AttestationBlocked("claim schema not recognized")
    if (record["schema_version"] != 1 or record["repository"] != REPO
            or record["workflow"] != WORKFLOW or record["job_name"] != JOB
            or record["classification"] != "UNTRUSTED_RUNNER_CLAIM"):
        raise AttestationBlocked("wrong provenance or classification")
    if (not isinstance(record["github"], dict)
            or set(record["github"]) != {"head_sha", "run_id", "run_attempt", "job_id"}
            or not isinstance(record["github"]["head_sha"], str)
            or not HEX40.fullmatch(record["github"]["head_sha"])):
        raise AttestationBlocked("malformed run identity")
    if any(type(record["github"][k]) is not int or record["github"][k] <= 0
           for k in ("run_id", "run_attempt", "job_id")):
        raise AttestationBlocked("invalid run identifiers")
    if any(not isinstance(record[k], str) or not HEX64.fullmatch(record[k])
           for k in ("candidate_sha256", "source_sha256", "app_sha256",
                     "stdout_sha256", "stderr_sha256", "checksum_sha256")):
        raise AttestationBlocked("invalid record digest")
    if (not isinstance(record["image_digest"], str)
            or not IMAGE_PATTERN.fullmatch(record["image_digest"])
            or record["command"] != COMMAND
            or record["sandbox"] != "docker_network_none_readonly_unprivileged"
            or type(record["passed"]) is not bool or type(record["returncode"]) is not int
            or record["passed"] is not (record["returncode"] == 0)):
        raise AttestationBlocked("invalid sandbox execution details")
    expected = canonical_hash({k: v for k, v in record.items()
                               if k != "checksum_sha256"})
    if record["checksum_sha256"] != expected:
        raise AttestationBlocked("runner claim was modified")
    return record


def check_github_job(record, *, job, run, expected_head_sha, approved_workflow_ref):
    """Compare to independently retrieved, authenticated GitHub API records.

    job/run must be fetched *separately* by a read-only trusted client,
    not copied from the generated model, artifact or PR description.
    This still does not prove sandbox isolation or justify a repo write.
    """
    validate_claim(record)
    if (not isinstance(expected_head_sha, str)
            or not HEX40.fullmatch(expected_head_sha)
            or expected_head_sha != record["github"]["head_sha"]):
        raise AttestationBlocked("attestation does not match expected exact commit")
    if (not isinstance(approved_workflow_ref, str)
            or approved_workflow_ref != WORKFLOW + "@refs/heads/main"):
        raise AttestationBlocked("workflow is not from an approved protected main ref")
    if not isinstance(job, dict) or not isinstance(run, dict):
        raise AttestationBlocked("trusted GitHub job/run metadata missing")
    ref = record["github"]
    if (job.get("id") != ref["job_id"] or job.get("run_id") != ref["run_id"]
            or job.get("name") != JOB or job.get("status") != "completed"
            or job.get("head_sha") != expected_head_sha
            or job.get("conclusion") != "success"):
        raise AttestationBlocked("job identity or successful conclusion mismatch")
    if (run.get("id") != ref["run_id"]
            or run.get("run_attempt") != ref["run_attempt"]
            or run.get("head_sha") != expected_head_sha
            or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or run.get("event") != "workflow_dispatch"):
        raise AttestationBlocked("workflow run identity/head SHA mismatch")
    if run.get("path") != approved_workflow_ref:
        raise AttestationBlocked("GitHub did not execute approved workflow ref")
    steps = job.get("steps")
    if (not isinstance(steps, list) or not any(
            isinstance(step, dict)
            and step.get("name") == "Execute isolated test in network-off Docker"
            and step.get("status") == "completed"
            and step.get("conclusion") == "success"
            for step in steps)):
        raise AttestationBlocked("actual isolated functional test step not verified")
    if record["passed"] is not True:
        raise AttestationBlocked("claimed functional test did not pass")
    return {
        "gitHub_job_correspondence_verified": True,
        "job_id": job["id"], "run_id": run["id"],
        "run_attempt": run["run_attempt"],
        "head_sha": expected_head_sha,
        "candidate_sha256": record["candidate_sha256"],
        "source": "github_job_metadata_match_and_untrusted_artifact",
        "test_runner_isolation_independently_attested": False,
        "model_qa_independently_verified": False,
        "manager_commit_execution_authorized": False,
        "automatic_merge_authorized": False,
    }
