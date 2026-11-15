"""Permission-scoped manager GitHub commit / draft-PR plans, default OFF.

This module produces exact, reviewable API operation plans. A live writer
requires separately authorized GitHub App credentials, branch protections,
trusted sandbox/test attestation, and reviewer provenance. No code here
authorizes main merges, force-push, branch creation, production or spending.

The execution methods intentionally fail closed until a later trusted
attestation authority exists; model-supplied JSON must never switch them on.
"""
import hashlib
import re

from company.github_quality import verify_pr_evidence, EvidenceBlocked

REPO = "Baraka-Hani/Serenity"
TARGET_PATH = "backend/test_destination_picker.js"
FEATURE_BRANCH = re.compile(r"^ai/serenity-issue-22(?:-[a-z0-9]{3,20})?$")
HEX64 = re.compile(r"^[a-f0-9]{64}$")


class ManagerWriterBlocked(ValueError):
    pass


def plan_branch_commit(*, branch, source_sha256, candidate_sha256,
                       candidate_text, risk, issue, changed_files,
                       sandbox_evidence, qa_evidence, amount_requested=0):
    """Prepare a *non-executable* candidate commit packet.

    Deliberately do not trust self-reported tests. Full green evidence must be
    produced by a future trusted worker that binds exactly to candidate_sha.
    """
    if (not isinstance(branch, str) or not FEATURE_BRANCH.fullmatch(branch)
            or branch in ("main", "master")
            or issue != 22 or risk != "low"
            or changed_files != [TARGET_PATH]):
        raise ManagerWriterBlocked("feature branch, issue and scope not allowlisted")
    if (not isinstance(source_sha256, str) or not HEX64.fullmatch(source_sha256)
            or not isinstance(candidate_sha256, str) or not HEX64.fullmatch(candidate_sha256)
            or not isinstance(candidate_text, str)
            or len(candidate_text.encode("utf-8")) > 6500
            or hashlib.sha256(candidate_text.encode("utf-8")).hexdigest() != candidate_sha256):
        raise ManagerWriterBlocked("source/candidate digest invalid")
    if type(amount_requested) not in (int, float) or amount_requested != 0:
        raise ManagerWriterBlocked("financial exposure must route to owner")
    if not isinstance(sandbox_evidence, dict) or not isinstance(qa_evidence, dict):
        raise ManagerWriterBlocked("required test/review provenance missing")
    sandbox_candidate = sandbox_evidence.get("candidate_sha256")
    if sandbox_candidate != candidate_sha256:
        raise ManagerWriterBlocked("functional test evidence from a different candidate")
    if sandbox_evidence.get("actual_functional_test_executed") is not True:
        raise ManagerWriterBlocked("syntactic or mocked checks are insufficient")
    if sandbox_evidence.get("passed") is not True:
        raise ManagerWriterBlocked("functional regression failed")
    if sandbox_evidence.get("sandbox") != "docker_network_none_readonly_unprivileged":
        raise ManagerWriterBlocked("untrusted or missing isolation")
    if qa_evidence.get("independent_model") != "openai/gpt-oss-120b" or qa_evidence.get("approved") is not True:
        raise ManagerWriterBlocked("independent model review absent")
    if qa_evidence.get("candidate_sha256") != candidate_sha256:
        raise ManagerWriterBlocked("review not bound to exact candidate")
    if qa_evidence.get("architecture_alignment") is not True or qa_evidence.get("risk_flags"):
        raise ManagerWriterBlocked("architecture or risk review failed")
    # All evidence is *still self-reported* at this point. Never grant write
    # based solely on a model/review/sandbox dict.
    return {
        "issue": issue, "branch": branch, "path": TARGET_PATH,
        "source_sha256": source_sha256, "candidate_sha256": candidate_sha256,
        "risk": risk, "financial_exposure": 0,
        "api_operations": [
            "GitHub GET existing feature-branch file SHA",
            "GitHub PUT single allowlisted path with exact old blob SHA",
            "GitHub CI on resulting exact head SHA",
            "GitHub CREATE or UPDATE draft PR after trusted checks"
        ],
        "status": "WAITING_TRUSTED_ATTESTATION_AND_OWNER_SETUP",
        "model_claims_not_trusted_as_ci": True,
        "manager_write_execution_authorized": False,
        "owner_per_commit_approval_required_after_activation": False,
        "protected_merge_authorized": False,
        "production_deployment_authorized": False,
        "public_release_authorized": False,
    }


def review_existing_pr_trusted(pull_request, changed_files, checks, reviews):
    """Assess an existing draft PR against actual GitHub API evidence.

    Passing is a *review recommendation*, never an automatic merge.
    """
    try:
        return verify_pr_evidence(pull_request=pull_request,
                                  changed_files=changed_files,
                                  checks=checks, reviews=reviews)
    except EvidenceBlocked as exc:
        return {
            "gate": "BLOCKED", "reason": str(exc),
            "automatic_merge_authorized": False,
            "manager_write_execution_authorized": False,
        }


def write_branch_commit(*args, **kwargs):
    raise ManagerWriterBlocked(
        "LIVE MANAGER WRITES NOT ENABLED: require a separately approved, "
        "scoped GitHub App, trusted sandbox attestation and exact candidate "
        "commit verification; this module cannot push or merge."
    )


def create_draft_pr(*args, **kwargs):
    raise ManagerWriterBlocked(
        "DRAFT PR WRITER NOT ENABLED: trusted commit/CI provenance and an "
        "initial owner-approved GitHub App setup are required."
    )


def merge_protected_branch(*args, **kwargs):
    raise ManagerWriterBlocked(
        "AUTOMATIC MERGES DISABLED: verified protected-branch rules and "
        "independent owner authorization for this capability are required."
    )
