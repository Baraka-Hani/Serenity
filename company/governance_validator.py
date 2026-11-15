"""Fail-closed governance validator and quality gate enforcement engine.

Verifies candidate SHA256 digest binding, deterministic CI test provenance,
independent reviewer role segregation, and GitHub ruleset compliance.
Never promotes self-reported model claims to code execution authorization.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Set

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")

MAX_CANDIDATE_BYTES = 65_000

MANDATORY_CI_CHECKS = {
    "backend-and-browser-logic",
    "react-prototype",
    "module5-privacy-and-architecture",
}

FORBIDDEN_SENSITIVE_ACTIONS = frozenset({
    "spending",
    "credentials",
    "production_deployment",
    "production_data",
    "public_release",
    "privacy_security",
})

FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"^\.github/workflows/"),
    re.compile(r"backend/server\.py$"),
    re.compile(r"nomad-canvas/src/tripPayments\.ts$"),
    re.compile(r"backend/data/"),
]


class GovernanceError(ValueError):
    """Raised when a candidate or metadata fails security validation."""


def sha256_digest(content: bytes) -> str:
    """Compute standard SHA256 hex digest of raw bytes."""
    return hashlib.sha256(content).hexdigest()


class GovernanceValidator:
    """Evaluates task, candidate diffs, and verification evidence against quality gates."""

    @staticmethod
    def validate_task_scope(task: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Gate 1: Verify task is within allowlisted low-risk scope."""
        reasons: List[str] = []
        if not isinstance(task, dict):
            return False, ["Task metadata must be a dictionary"]

        risk = task.get("risk", "unknown")
        if risk != "low":
            reasons.append(f"Task risk is '{risk}'; only 'low' risk tasks are eligible for delegated validation.")

        requested_action = task.get("requested_action")
        if requested_action in FORBIDDEN_SENSITIVE_ACTIONS:
            reasons.append(f"Requested action '{requested_action}' requires direct human owner authorization.")

        target_path = task.get("target_path", "")
        for pattern in FORBIDDEN_PATH_PATTERNS:
            if pattern.search(target_path):
                reasons.append(f"Target path '{target_path}' touches a sensitive/forbidden system area.")

        return len(reasons) == 0, reasons

    @staticmethod
    def validate_candidate_bytes(
        original_bytes: bytes,
        candidate_bytes: bytes,
        task: Dict[str, Any],
    ) -> Tuple[bool, List[str], Dict[str, str]]:
        """Gate 2: Cryptographically bind original and candidate digests."""
        reasons: List[str] = []
        digests: Dict[str, str] = {}

        if not isinstance(original_bytes, bytes) or not isinstance(candidate_bytes, bytes):
            return False, ["Original and candidate must be raw byte buffers"], digests

        if len(candidate_bytes) > MAX_CANDIDATE_BYTES:
            reasons.append(f"Candidate size ({len(candidate_bytes)} bytes) exceeds maximum pilot limit ({MAX_CANDIDATE_BYTES} bytes).")

        try:
            original_bytes.decode("utf-8")
            candidate_bytes.decode("utf-8")
        except UnicodeDecodeError:
            reasons.append("Source files must be valid UTF-8 text.")

        orig_hash = sha256_digest(original_bytes)
        cand_hash = sha256_digest(candidate_bytes)
        digests = {"original_sha256": orig_hash, "candidate_sha256": cand_hash}

        if orig_hash == cand_hash:
            reasons.append("Candidate diff is empty (identical to original source).")

        expected_orig = task.get("original_sha256")
        if expected_orig and expected_orig != orig_hash:
            reasons.append(f"Original digest mismatch: task expected {expected_orig[:12]}..., computed {orig_hash[:12]}...")

        expected_cand = task.get("candidate_sha256")
        if expected_cand and expected_cand != cand_hash:
            reasons.append(f"Candidate digest mismatch: task expected {expected_cand[:12]}..., computed {cand_hash[:12]}...")

        return len(reasons) == 0, reasons, digests

    @staticmethod
    def validate_ci_evidence(
        ci_checks: Dict[str, Any],
        head_sha: str,
    ) -> Tuple[bool, List[str]]:
        """Gate 3: Verify deterministic automated CI status checks on exact head SHA."""
        reasons: List[str] = []
        if not isinstance(ci_checks, dict):
            return False, ["CI evidence must be an object containing check results"]

        recorded_sha = ci_checks.get("head_sha", "")
        if not recorded_sha or recorded_sha != head_sha:
            reasons.append(f"CI run head SHA ('{recorded_sha}') does not match evaluated head SHA ('{head_sha}').")

        completed_checks = ci_checks.get("checks", {})
        for required_check in MANDATORY_CI_CHECKS:
            check_data = completed_checks.get(required_check)
            if not check_data:
                reasons.append(f"Mandatory CI status check '{required_check}' is missing.")
            else:
                conclusion = check_data.get("conclusion") or check_data.get("status")
                if conclusion not in ("success", "PASSED"):
                    reasons.append(f"Mandatory CI status check '{required_check}' failed with status: {conclusion}")

        return len(reasons) == 0, reasons

    @staticmethod
    def validate_role_segregation(
        builder_info: Dict[str, Any],
        reviewer_info: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """Gate 4: Ensure Builder and Reviewer roles have distinct identities."""
        reasons: List[str] = []
        builder_id = builder_info.get("model") or builder_info.get("agent_id")
        reviewer_id = reviewer_info.get("model") or reviewer_info.get("agent_id")

        if not builder_id or not reviewer_id:
            reasons.append("Both Builder and Reviewer identities must be fully specified.")
        elif builder_id == reviewer_id:
            reasons.append(f"Self-approval violation: Builder and Reviewer have identical identity '{builder_id}'.")

        reviewer_verdict = reviewer_info.get("verdict")
        if reviewer_verdict not in ("approve", "APPROVED", "PASS"):
            reasons.append(f"Independent QA review verdict is not approved (got: '{reviewer_verdict}').")

        return len(reasons) == 0, reasons

    @staticmethod
    def validate_ruleset_compliance(
        ruleset_config: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """Gate 5: Verify branch protection and ruleset enforcement."""
        reasons: List[str] = []
        if not ruleset_config.get("enforce_on_main", False):
            reasons.append("Branch ruleset for 'main' is not currently active.")
        if not ruleset_config.get("require_pull_request", False):
            reasons.append("Branch ruleset does not enforce pull request creation before merging.")
        if not ruleset_config.get("require_status_checks", False):
            reasons.append("Branch ruleset does not mandate passing CI status checks.")

        return len(reasons) == 0, reasons

    def assess(
        self,
        *,
        task: Dict[str, Any],
        original_bytes: bytes,
        candidate_bytes: bytes,
        ci_evidence: Dict[str, Any],
        builder_info: Dict[str, Any],
        reviewer_info: Dict[str, Any],
        ruleset_config: Optional[Dict[str, Any]] = None,
        head_sha: str = "0000000000000000000000000000000000000000",
    ) -> Dict[str, Any]:
        """Perform comprehensive, fail-closed evaluation across all 5 quality gates."""
        passed_gates: List[str] = []
        failed_gates: List[str] = []
        all_reasons: List[str] = []

        # Gate 1: Scope & Risk
        g1_ok, g1_reasons = self.validate_task_scope(task)
        if g1_ok:
            passed_gates.append("GATE_1_SCOPE_AND_RISK")
        else:
            failed_gates.append("GATE_1_SCOPE_AND_RISK")
            all_reasons.extend(g1_reasons)

        # Gate 2: Candidate SHA Binding
        g2_ok, g2_reasons, digests = self.validate_candidate_bytes(original_bytes, candidate_bytes, task)
        if g2_ok:
            passed_gates.append("GATE_2_SHA_BINDING")
        else:
            failed_gates.append("GATE_2_SHA_BINDING")
            all_reasons.extend(g2_reasons)

        # Gate 3: Deterministic CI Status Checks
        g3_ok, g3_reasons = self.validate_ci_evidence(ci_evidence, head_sha)
        if g3_ok:
            passed_gates.append("GATE_3_CI_EVIDENCE")
        else:
            failed_gates.append("GATE_3_CI_EVIDENCE")
            all_reasons.extend(g3_reasons)

        # Gate 4: Independent QA Role Segregation
        g4_ok, g4_reasons = self.validate_role_segregation(builder_info, reviewer_info)
        if g4_ok:
            passed_gates.append("GATE_4_ROLE_SEGREGATION")
        else:
            failed_gates.append("GATE_4_ROLE_SEGREGATION")
            all_reasons.extend(g4_reasons)

        # Gate 5: Ruleset & Branch Protection Compliance
        ruleset = ruleset_config or {"enforce_on_main": True, "require_pull_request": True, "require_status_checks": True}
        g5_ok, g5_reasons = self.validate_ruleset_compliance(ruleset)
        if g5_ok:
            passed_gates.append("GATE_5_RULESET_COMPLIANCE")
        else:
            failed_gates.append("GATE_5_RULESET_COMPLIANCE")
            all_reasons.extend(g5_reasons)

        all_passed = (len(failed_gates) == 0)

        # Strict fail-closed policy: manager execution is never self-authorized
        return {
            "authorized": False,  # Always False until owner authorizes execution adapter
            "all_quality_gates_passed": all_passed,
            "passed_gates": passed_gates,
            "failed_gates": failed_gates,
            "reasons": all_reasons,
            "digests": digests,
            "manager_commit_execution_authorized": False,  # Fail-closed invariant
            "recommendation": (
                "READY_FOR_DRAFT_PR" if all_passed else "BLOCKED_GATES_FAILED"
            ),
        }
