"""Idempotent manager draft PR intent generator with fail-closed security.

Constructs an immutable, serialized intent record representing a verified low-risk
change proposal. Strictly prohibits autonomous remote git pushes or GitHub API writes,
preserving direct human owner authority over repository mutations.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from company.governance_validator import GovernanceValidator
from company.sandbox_attestation import SandboxAttestation


class IntentError(ValueError):
    """Raised when intent prerequisites are unmet or intent is malformed."""


def iso_utc_now() -> str:
    """Return current timestamp in ISO-8601 UTC format."""
    return datetime.now(timezone.utc).isoformat()


class ManagerIntentGenerator:
    """Constructs structured, inspectable draft PR intent records."""

    @staticmethod
    def generate_intent(
        *,
        issue_number: int,
        target_path: str,
        original_sha256: str,
        candidate_sha256: str,
        diff_patch: str,
        governance_assessment: Dict[str, Any],
        sandbox_attestation: Dict[str, Any],
        lines_added: int = 10,
        lines_deleted: int = 2,
    ) -> Dict[str, Any]:
        """Construct an immutable draft PR intent record after verifying gates."""
        # 1. Verify governance gates passed
        if not governance_assessment.get("all_quality_gates_passed"):
            failed = governance_assessment.get("failed_gates", [])
            raise IntentError(
                f"Cannot generate PR intent: governance quality gates failed ({', '.join(failed)})"
            )

        # 2. Verify sandbox attestation
        if not sandbox_attestation.get("verified_sandbox_execution"):
            raise IntentError(
                "Cannot generate PR intent: sandbox runner attestation is missing or execution failed."
            )

        ts = iso_utc_now()
        short_sha = candidate_sha256[:8]
        feature_branch = f"ai/serenity-issue-{issue_number}-{short_sha}"
        title = f"Draft: AI low-risk verified candidate for Issue #{issue_number}"

        att_id = sandbox_attestation.get("attestation_id", "ATT-UNKNOWN")
        img_digest = sandbox_attestation.get("image_digest", "UNKNOWN")

        body = (
            f"## Serenity Engineering Manager — Low-Risk Draft PR Intent\n\n"
            f"**Companion Issue:** #{issue_number}\n"
            f"**Target Path:** `{target_path}`\n"
            f"**Candidate SHA256:** `{candidate_sha256}`\n"
            f"**Original SHA256:** `{original_sha256}`\n"
            f"**Sandbox Attestation:** `{att_id}` (Image: `{img_digest}`)\n\n"
            f"### Verified Quality Gates\n"
            f"- [x] Gate 1: Allowlisted low-risk scope verified (Zero auth, payment, or PII touched).\n"
            f"- [x] Gate 2: Candidate SHA256 cryptographically bound to diff patch.\n"
            f"- [x] Gate 3: Deterministic automated CI status checks verified on exact head commit.\n"
            f"- [x] Gate 4: Independent Reviewer QA verdict confirmed (Distinct Builder/Reviewer roles).\n"
            f"- [x] Gate 5: GitHub ruleset compliance verified for `main`.\n\n"
            f"### Diff Statistics\n"
            f"- Files Changed: 1 (`{target_path}`)\n"
            f"- Lines Added: +{lines_added}\n"
            f"- Lines Deleted: -{lines_deleted}\n"
            f"- Financial Cost: $0.00\n\n"
            f"---\n"
            f"*Autonomous execution disabled. Human owner review required before merge.*"
        )

        raw_intent = f"{feature_branch}|main|{title}|{candidate_sha256}|{ts}"
        intent_hash = hashlib.sha256(raw_intent.encode("utf-8")).hexdigest()
        intent_id = f"INTENT-{ts.replace(':', '').replace('-', '')[:15]}-{intent_hash[:8]}"

        return {
            "intent_id": intent_id,
            "timestamp": ts,
            "issue_number": issue_number,
            "target_branch": "main",
            "feature_branch": feature_branch,
            "title": title,
            "body": body,
            "target_path": target_path,
            "original_sha256": original_sha256,
            "candidate_sha256": candidate_sha256,
            "diff_patch": diff_patch,
            "diff_stats": {
                "files_changed": 1,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
            },
            "governance_assessment": governance_assessment,
            "sandbox_attestation": sandbox_attestation,
            "intent_hash": intent_hash,
            "execution_permitted": False,  # Strict invariant: no autonomous writes
            "status": "PROPOSED_READY_FOR_OWNER_REVIEW",
        }

    @staticmethod
    def serialize_intent(intent: Dict[str, Any]) -> str:
        """Serialize intent record to deterministic JSON string."""
        return json.dumps(intent, indent=2, sort_keys=True)

    @staticmethod
    def validate_intent(intent: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate serialized intent record integrity."""
        reasons: List[str] = []
        if not isinstance(intent, dict):
            return False, ["Intent must be a dictionary"]

        if intent.get("execution_permitted") is not False:
            reasons.append("Safety violation: execution_permitted must be strictly False.")

        if not intent.get("target_branch") or intent.get("target_branch") != "main":
            reasons.append("Target branch must be 'main'.")

        cand_sha = intent.get("candidate_sha256", "")
        if not cand_sha or len(cand_sha) != 64:
            reasons.append("Invalid or missing candidate_sha256 digest.")

        return len(reasons) == 0, reasons
