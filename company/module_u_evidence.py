"""Read-only exact-commit quality dossier for a Serenity low-risk draft PR.

Every source hash is recomputed from GitHub's official Contents API at the
specific base/head commit. Green CI/review metadata is correlated with the
same head SHA, but never treated as authorization for a write or deployment.
All network reads go through GithubQualityReader's fixed GitHub origin.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import re

from company.github_quality import (
    EvidenceBlocked, GithubQualityReader, REPO, SHA, verify_pr_evidence,
)

PATH = "backend/test_destination_picker.js"
MAX_SOURCE_BYTES = 6500
MAX_CHECKS = 99


class DossierBlocked(ValueError):
    pass


def git_blob_sha(data):
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data
    ).hexdigest()


def _verified_file(obj, *, path=PATH):
    if (not isinstance(obj, dict) or obj.get("type") != "file"
            or obj.get("path") != path
            or obj.get("encoding") != "base64"
            or not isinstance(obj.get("content"), str)
            or not isinstance(obj.get("sha"), str)
            or not SHA.fullmatch(obj["sha"])):
        raise DossierBlocked("untrusted GitHub contents-file metadata")
    try:
        data = base64.b64decode("".join(obj["content"].split()), validate=True)
        data.decode("utf-8")
    except (binascii.Error, UnicodeError, ValueError):
        raise DossierBlocked("malformed or non-text source") from None
    if (not 0 < len(data) <= MAX_SOURCE_BYTES
            or type(obj.get("size")) is not int or obj["size"] != len(data)
            or git_blob_sha(data) != obj["sha"]):
        raise DossierBlocked("GitHub Git blob digest, size or source bounds mismatch")
    return {
        "git_blob_sha": obj["sha"],
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }


def inspect_exact_pr(reader, *, pr_number, expected_base_sha256,
                     expected_candidate_sha256):
    """Inspect existing PR read-only; caller cannot supply GitHub evidence.

    This is strict about a single allowed test file and every required CI job.
    It is a reviewer dossier, NOT a manager authorization or a signed runner
    attestation. No candidate code is executed.
    """
    if not isinstance(reader, GithubQualityReader):
        raise DossierBlocked("an independently configured read-only GitHub client is required")
    if type(pr_number) is not int or not 1 <= pr_number <= 10000000:
        raise DossierBlocked("invalid PR number")
    for digest in (expected_base_sha256, expected_candidate_sha256):
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise DossierBlocked("expected source SHA-256 is invalid")
    try:
        pr = reader._get("/pulls/" + str(pr_number))
        if not isinstance(pr, dict):
            raise DossierBlocked("GitHub PR record missing")
        head, base = pr.get("head") or {}, pr.get("base") or {}
        head_sha, base_sha = head.get("sha"), base.get("sha")
        if (not isinstance(head_sha, str) or not SHA.fullmatch(head_sha)
                or not isinstance(base_sha, str) or not SHA.fullmatch(base_sha)
                or head_sha == base_sha or base.get("ref") != "main"):
            raise DossierBlocked("expected exact main base and distinct head commits")
        if not isinstance(pr.get("changed_files"), int) or pr["changed_files"] != 1:
            raise DossierBlocked("PR does not have exactly one changed file")
        files = reader._get("/pulls/" + str(pr_number) + "/files?per_page=100")
        checks = reader._get("/commits/" + head_sha + "/check-runs?per_page=100")
        reviews = reader._get("/pulls/" + str(pr_number) + "/reviews?per_page=100")
        if (not isinstance(checks, dict) or
                type(checks.get("total_count")) is not int or
                checks["total_count"] >= 100):
            raise DossierBlocked("CI jobs may be incompletely paginated")
        qa = verify_pr_evidence(pull_request=pr, changed_files=files,
                                checks=checks, reviews=reviews)
        # Hash the actual files from each immutable commit, not untrusted
        # model text or an arbitrary branch's latest state.
        base_data = reader._get("/contents/" + PATH + "?ref=" + base_sha)
        head_data = reader._get("/contents/" + PATH + "?ref=" + head_sha)
        original = _verified_file(base_data)
        candidate = _verified_file(head_data)
    except EvidenceBlocked as exc:
        raise DossierBlocked("trusted GitHub PR/QA/CI gate failed: " + str(exc)) from None
    if original["sha256"] != expected_base_sha256:
        raise DossierBlocked("baseline source hash differs from expected GitHub blob")
    if candidate["sha256"] != expected_candidate_sha256:
        raise DossierBlocked("candidate source hash differs from expected GitHub blob")
    if original["git_blob_sha"] == candidate["git_blob_sha"]:
        raise DossierBlocked("candidate does not change original file")
    return {
        "schema_version": 1,
        "issue_scope": 22,
        "pr_number": pr_number,
        "base_commit_sha": base_sha,
        "head_commit_sha": head_sha,
        "source_path": PATH,
        "baseline_git_blob_sha": original["git_blob_sha"],
        "baseline_sha256": original["sha256"],
        "candidate_git_blob_sha": candidate["git_blob_sha"],
        "candidate_sha256": candidate["sha256"],
        "trusted_github_checks": qa["required_jobs_passed"],
        "independent_human_reviewers": qa["independent_reviewers"],
        "evidence_class": "GITHUB_API_FILE_CI_AND_REVIEW_CORRESPONDENCE",
        "github_metadata_correspondence_verified": True,
        "isolated_candidate_runtime_attested": False,
        "independent_ai_model_review_proven": False,
        "manager_commit_execution_authorized": False,
        "draft_pr_write_authorized": False,
        "automatic_merge_authorized": False,
        "production_deploy_authorized": False,
        "owner_financial_approval_granted": False,
        "status": "INSPECTED_READ_ONLY_WITH_FINAL_RUNTIME_TRUST_BLOCKED",
    }
