"""Fail-closed manager engineering governance; does not perform GitHub writes.

Managers may commit reviewed routine changes to isolated branches or create
draft PRs, and may merge eligible low-risk changes only when GitHub trusted CI,
branch rules and independent reviews actually verify evidence. This offline
decision is NOT a token or permission to perform an external action.
"""
from urllib.parse import urlparse

ROUTINE_ACTIONS = frozenset({"branch_commit", "draft_pr", "protected_merge"})
OWNER_ACTIONS = frozenset({"spending", "credentials", "production_deployment",
                           "public_release", "production_data", "strategic_change",
                           "external_publication"})
SENSITIVE_TERMS = (
    ".env", "secrets", "credentials", "billing", "payment", "payments",
    "backend/data/", "/data/", "firebase",
    "auth", "session", "accounts", "location_history", "privacy", "migration",
    "database", "deploy", "workflows", ".github", "agents.md",
    "operating_charter",
)
MANDATORY_CHECKS = frozenset({
    "python_integration", "browser_js", "react_typecheck_build",
    "dependency_security", "privacy_scan", "architecture_integration",
    "regression_tests",
})


class QualityPolicyError(ValueError):
    pass


def _valid_evidence_link(value):
    """Limit evidence pointers to known Serenity URLs, never attest to authenticity."""
    if not isinstance(value, str) or len(value) > 300:
        return False
    uri = urlparse(value)
    return (uri.scheme == "https" and uri.hostname == "github.com"
            and uri.path.startswith("/Baraka-Hani/Serenity/")
            and not uri.username and not uri.password)


def evaluate_manager_action(record):
    """Advisory policy outcome for a prospective manager-authorized code action.

    No self-reported JSON can prove CI, reviewer independence or policy
    compliance; a future trusted GitHub adapter must confirm those details.
    This always returns execution_authorized=False and never touches code.
    """
    if not isinstance(record, dict):
        raise QualityPolicyError("quality evidence must be an object")
    action = record.get("action")
    if action not in ROUTINE_ACTIONS | OWNER_ACTIONS:
        raise QualityPolicyError("unknown action")
    result = {
        "action": action,
        "policy": "Serenity quality-first delegated engineering v2",
        "manager_may_commit_after_verified_gates": False,
        "owner_approval_required": False,
        "execution_authorized": False,
        "pending_trusted_verification": True,
        "status": "BLOCKED",
        "reasons": [],
    }
    reasons = result["reasons"]
    if action in OWNER_ACTIONS:
        result["owner_approval_required"] = True
        reasons.append("financial/production/credential/strategic authority reserved to owner")
        result["status"] = "OWNER_APPROVAL_REQUIRED"
        return result
    if record.get("risk") != "low":
        reasons.append("only low-risk scoped engineering can be delegated")
    if not isinstance(record.get("changed_files"), list) or not record["changed_files"]:
        reasons.append("changed-file inventory missing")
    else:
        for path in record["changed_files"]:
            if (not isinstance(path, str) or path.startswith("/")
                    or "\\" in path or ".." in path.split("/") or len(path) > 180
                    or any(t in path.lower() for t in SENSITIVE_TERMS)):
                reasons.append("restricted or invalid path; human specialist review required")
                break
    if record.get("product_purpose") != "documented":
        reasons.append("user value/purpose not documented")
    if record.get("architecture_alignment") != "verified":
        reasons.append("integration/architecture alignment not verified")
    if record.get("acceptance_met") is not True:
        reasons.append("task acceptance criteria not verified")
    if record.get("rollback_documented") is not True:
        reasons.append("rollback path not documented")
    if record.get("new_financial_exposure") is not False:
        reasons.append("any new cost requires explicit owner approval")
        result["owner_approval_required"] = True
    if record.get("independent_reviewer") != "approved":
        reasons.append("independent specialist QA review missing")
    check_results = record.get("checks")
    if not isinstance(check_results, dict):
        reasons.append("required check evidence missing")
    else:
        absent = sorted(k for k in MANDATORY_CHECKS if check_results.get(k) != "pass")
        if absent:
            reasons.append("required checks not passing: " + ", ".join(absent))
    if record.get("ci_conclusion") != "success" or not _valid_evidence_link(record.get("ci_url")):
        reasons.append("verified GitHub CI success URL required")
    if record.get("qa_conclusion") != "approve" or not _valid_evidence_link(record.get("qa_url")):
        reasons.append("independent QA evidence link and approval required")
    if record.get("provider_allowance") not in ("unused", "verified_eligible"):
        reasons.append("no confirmed model/quota allowance for further calls")
    if action == "protected_merge":
        if record.get("branch_protection") != "enforced":
            reasons.append("protected merge requires enforced repository branch rules")
        if record.get("integration_smoke") != "pass":
            reasons.append("protected merge requires passing integration smoke tests")
    if not reasons:
        result["status"] = "MANAGER_POLICY_ELIGIBLE_PENDING_TRUSTED_INTEGRATION"
        result["manager_may_commit_after_verified_gates"] = True
    return result
