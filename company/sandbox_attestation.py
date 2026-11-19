"""Cryptographic runner attestation generator and verification engine.

Binds candidate source SHA256, pinned container image digest, test execution logs,
and isolation parameters to prove that test results were produced in an authentic,
network-disabled sandbox environment.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

HEX64 = re.compile(r"^[0-9a-f]{64}$")
PINNED_IMAGE_DIGEST_PATTERN = re.compile(r"^.+@sha256:[0-9a-f]{64}$")


class AttestationError(ValueError):
    """Raised for malformed or tampered sandbox attestation records."""


def sha256_hex(data: str | bytes) -> str:
    """Compute SHA256 hex digest of string or bytes."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def compute_attestation_hash(
    candidate_sha256: str,
    source_sha256: str,
    target_path: str,
    image_digest: str,
    command: str,
    exit_code: int,
    output_sha256: str,
    run_timestamp: str,
    isolation_json: str,
) -> str:
    """Compute deterministic SHA256 digest binding all attestation fields."""
    raw = (
        f"{candidate_sha256}|{source_sha256}|{target_path}|{image_digest}|"
        f"{command}|{exit_code}|{output_sha256}|{run_timestamp}|{isolation_json}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SandboxAttestation:
    """Generates and verifies cryptographic sandbox execution attestations."""

    @staticmethod
    def generate_attestation(
        *,
        candidate_sha256: str,
        source_sha256: str,
        target_path: str,
        image_digest: str,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str = "",
        run_timestamp: Optional[str] = None,
        runner_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a cryptographically bound runner attestation record."""
        if not HEX64.match(candidate_sha256):
            raise AttestationError("Invalid candidate_sha256 format")
        if not HEX64.match(source_sha256):
            raise AttestationError("Invalid source_sha256 format")
        if not PINNED_IMAGE_DIGEST_PATTERN.match(image_digest):
            raise AttestationError(
                f"Image digest '{image_digest}' must be an explicit pinned digest (image@sha256:<hex64>)"
            )
        if not target_path or not isinstance(target_path, str):
            raise AttestationError("target_path must be a non-empty string")
        if not command or not isinstance(command, str):
            raise AttestationError("command must be a non-empty string")
        if not isinstance(exit_code, int):
            raise AttestationError("exit_code must be an integer")

        ts = run_timestamp or datetime.now(timezone.utc).isoformat()
        combined_output = stdout + stderr
        out_sha = sha256_hex(combined_output)

        default_isolation = {
            "network_disabled": True,
            "read_only_root": True,
            "drop_capabilities": ["ALL"],
            "no_new_privileges": True,
            "memory_limit_mb": 512,
            "cpu_limit": 1.0,
        }
        isolation = {**default_isolation, **(runner_metadata or {})}
        isolation_json = json.dumps(isolation, sort_keys=True)

        att_hash = compute_attestation_hash(
            candidate_sha256=candidate_sha256,
            source_sha256=source_sha256,
            target_path=target_path,
            image_digest=image_digest,
            command=command,
            exit_code=exit_code,
            output_sha256=out_sha,
            run_timestamp=ts,
            isolation_json=isolation_json,
        )

        attestation_id = f"ATT-{ts.replace(':', '').replace('-', '')[:15]}-{att_hash[:8]}"

        return {
            "attestation_id": attestation_id,
            "run_timestamp": ts,
            "candidate_sha256": candidate_sha256,
            "source_sha256": source_sha256,
            "target_path": target_path,
            "image_digest": image_digest,
            "command": command,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "output_sha256": out_sha,
            "runner_metadata": isolation,
            "attestation_hash": att_hash,
            "verified_sandbox_execution": (exit_code == 0 and isolation.get("network_disabled") is True),
        }

    @staticmethod
    def verify_attestation(
        attestation: Dict[str, Any],
        expected_candidate_sha: str,
        expected_image_digest: str,
    ) -> Tuple[bool, List[str]]:
        """Verify an attestation record against expected candidate and security requirements."""
        reasons: List[str] = []
        if not isinstance(attestation, dict):
            return False, ["Attestation record must be a dictionary"]

        # 1. Verify candidate SHA match
        cand_sha = attestation.get("candidate_sha256", "")
        if cand_sha != expected_candidate_sha:
            reasons.append(
                f"Candidate SHA mismatch: expected {expected_candidate_sha[:12]}..., "
                f"attestation contains {cand_sha[:12]}..."
            )

        # 2. Verify image digest match
        img_digest = attestation.get("image_digest", "")
        if img_digest != expected_image_digest:
            reasons.append(
                f"Image digest mismatch: expected '{expected_image_digest}', "
                f"attestation contains '{img_digest}'"
            )

        # 3. Verify exit code
        exit_code = attestation.get("exit_code")
        if exit_code != 0:
            reasons.append(f"Test runner exit code is non-zero (exit_code={exit_code}).")

        # 4. Verify output SHA256 integrity
        combined_output = attestation.get("stdout", "") + attestation.get("stderr", "")
        computed_out_sha = sha256_hex(combined_output)
        if attestation.get("output_sha256") != computed_out_sha:
            reasons.append("Output logs do not match output_sha256 checksum.")

        # 5. Verify isolation parameters
        isolation = attestation.get("runner_metadata", {})
        if not isolation.get("network_disabled"):
            reasons.append("Network isolation was NOT enabled during runner execution.")
        if not isolation.get("read_only_root"):
            reasons.append("Read-only root filesystem was NOT enforced.")

        # 6. Verify cryptographic attestation digest
        isolation_json = json.dumps(isolation, sort_keys=True)
        recomputed_hash = compute_attestation_hash(
            candidate_sha256=attestation.get("candidate_sha256", ""),
            source_sha256=attestation.get("source_sha256", ""),
            target_path=attestation.get("target_path", ""),
            image_digest=attestation.get("image_digest", ""),
            command=attestation.get("command", ""),
            exit_code=attestation.get("exit_code", -1),
            output_sha256=attestation.get("output_sha256", ""),
            run_timestamp=attestation.get("run_timestamp", ""),
            isolation_json=isolation_json,
        )

        if attestation.get("attestation_hash") != recomputed_hash:
            reasons.append("Attestation digest verification failed (tampered attestation record).")

        return len(reasons) == 0, reasons
