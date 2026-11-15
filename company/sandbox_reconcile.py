"""Serenity Module T: independently reconcile a completed trusted-source sandbox run.

Read-only GitHub verification binds a downloaded smoke record to the
*actual GitHub run attempt and job* fetched from GitHub, not user-provided
job IDs or untrusted AI output. Even a matched record is not signed
runtime attestation and NEVER enables a manager writer, merge or deploy.
"""
import re

from company.github_quality import GithubQualityReader, EvidenceBlocked
from company.sandbox_attestation import (
    AttestationBlocked, REPO, WORKFLOW, JOB, HEX40, HEX64,
    create_claim, check_github_job,
)

WORKFLOW_FULL_REF = REPO + "/" + WORKFLOW + "@refs/heads/main"
MAX_RUN_ID = 10 ** 16


def _positive_id(value):
    if type(value) is not int or not 0 < value <= MAX_RUN_ID:
        raise AttestationBlocked("run identifier must be a positive bounded integer")
    return value


def validate_smoke_record(smoke):
    """Validate the narrow checked-in source smoke schema, no model artifacts."""
    expected = {
        "schema_version", "purpose", "source_sha256", "candidate_sha256",
        "app_sha256", "image_digest", "runner_result", "github_run_id",
        "github_run_attempt", "github_head_sha", "github_workflow_ref",
        "github_job_name", "provenance", "model_generated_code_executed",
        "manager_commit_authorized", "automatic_merge_authorized",
    }
    if not isinstance(smoke, dict) or set(smoke) != expected:
        raise AttestationBlocked("unknown smoke record schema")
    if (smoke["schema_version"] != 1 or
            smoke["purpose"] != "KNOWN_CHECKED_IN_SERENITY_TEST_SMOKE" or
            smoke["provenance"] != "UNTRUSTED_OUTPUT_PENDING_INDEPENDENT_GITHUB_JOB_LOOKUP" or
            smoke["model_generated_code_executed"] is not False or
            smoke["manager_commit_authorized"] is not False or
            smoke["automatic_merge_authorized"] is not False):
        raise AttestationBlocked("record claims unauthorized operations")
    if smoke["source_sha256"] != smoke["candidate_sha256"]:
        raise AttestationBlocked("trusted-source smoke must not include a generated candidate")
    if any(not isinstance(smoke.get(key), str) or
           not HEX64.fullmatch(smoke[key])
           for key in ("source_sha256", "app_sha256", "candidate_sha256")):
        raise AttestationBlocked("invalid source hash")
    if (not isinstance(smoke.get("github_head_sha"), str)
            or not HEX40.fullmatch(smoke["github_head_sha"])
            or smoke.get("github_workflow_ref") != WORKFLOW_FULL_REF
            or smoke.get("github_job_name") != JOB):
        raise AttestationBlocked("workflow/head/job identity is not protected main smoke")
    for key in ("github_run_id", "github_run_attempt"):
        raw = smoke.get(key)
        if (not isinstance(raw, str) or not re.fullmatch(r"[1-9][0-9]{0,15}", raw)):
            raise AttestationBlocked("malformed GitHub run or attempt")
    if not isinstance(smoke.get("runner_result"), dict):
        raise AttestationBlocked("missing sandbox result")
    result = smoke["runner_result"]
    if result.get("candidate_sha256") != smoke["candidate_sha256"]:
        raise AttestationBlocked("runner executed different candidate")
    if result.get("image_digest") != smoke["image_digest"]:
        raise AttestationBlocked("runner used different image")
    if (result.get("passed") is not True or
            result.get("actual_functional_test_executed") is not True or
            result.get("github_write_permissions") is not False):
        raise AttestationBlocked("sandbox did not report a successful read-only execution")
    return smoke


def reconcile_smoke_with_github(smoke, *, reader):
    """Fetch exact attempt jobs + run from the official GitHub API, read only.

    The job ID is learned from GitHub, NOT from smoke JSON. Require an exact
    single completed job for that run attempt; any missing/paginated/duplicate
    records fail closed. This does not use credentials inside Docker.
    """
    validate_smoke_record(smoke)
    if not isinstance(reader, GithubQualityReader):
        raise AttestationBlocked("independent trusted read-only GitHub client required")
    run_id = _positive_id(int(smoke["github_run_id"]))
    attempt = _positive_id(int(smoke["github_run_attempt"]))
    response = reader._get(
        "/actions/runs/" + str(run_id) +
        "/attempts/" + str(attempt) + "/jobs?per_page=100")
    if (not isinstance(response, dict)
            or type(response.get("total_count")) is not int
            or not 1 <= response["total_count"] < 100
            or not isinstance(response.get("jobs"), list)
            or len(response["jobs"]) != response["total_count"]):
        raise AttestationBlocked("GitHub attempt job list is incomplete")
    matching = [job for job in response["jobs"] if (
        isinstance(job, dict) and job.get("name") == JOB)]
    if len(matching) != 1:
        raise AttestationBlocked("missing or ambiguous official sandbox job")
    job = matching[0]
    job_id = _positive_id(job.get("id"))
    if job.get("run_id") != run_id:
        raise AttestationBlocked("job belongs to a different run")
    run = reader._get("/actions/runs/" + str(run_id))
    if (not isinstance(run, dict) or run.get("head_branch") != "main"
            or not isinstance(run.get("repository"), dict)
            or run["repository"].get("full_name") != REPO):
        raise AttestationBlocked("not an official main-branch Serenity run")
    claim = create_claim(
        smoke["runner_result"], head_sha=smoke["github_head_sha"],
        run_id=run_id, run_attempt=attempt, job_id=job_id,
        source_sha256=smoke["source_sha256"],
        app_sha256=smoke["app_sha256"],
    )
    checked = check_github_job(
        claim, job=job, run=run, expected_head_sha=smoke["github_head_sha"],
        approved_workflow_ref=WORKFLOW + "@refs/heads/main",
    )
    return {
        "status": "GITHUB_CORRESPONDENCE_VERIFIED_ONLY",
        "trusted_source_smoke": True,
        "model_generated_code_executed": False,
        "head_sha": checked["head_sha"],
        "run_id": checked["run_id"],
        "attempt": checked["run_attempt"],
        "job_id": checked["job_id"],
        "candidate_sha256": checked["candidate_sha256"],
        "claim_sha256": claim["checksum_sha256"],
        "github_correspondence": True,
        "sandbox_isolation_independently_attested": False,
        "source_provenance_signed": False,
        "manager_commit_execution_authorized": False,
        "draft_pr_creation_authorized": False,
        "automatic_merge_authorized": False,
        "new_spending_authorized": False,
        "public_deploy_authorized": False,
    }
