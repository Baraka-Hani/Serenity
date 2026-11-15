"""Offline model dispatch adapter and fail-closed live execution gateway.

Provides deterministic synthetic responses for qwen/qwen3.8-27b and
openai/gpt-oss-120b in mock mode. Live mode fails closed unless explicit
repository variables and secrets are authorized. Zero new spend guaranteed.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from company.quota_ledger import QuotaLedger

APPROVED_MODELS = {
    "qwen/qwen3.8-27b": "builder",
    "openai/gpt-oss-120b": "reviewer",
}


class DispatcherError(ValueError):
    """Raised when dispatching fails or live prerequisites are unmet."""


def iso_utc_now() -> str:
    """Return current timestamp in ISO-8601 UTC format."""
    return datetime.now(timezone.utc).isoformat()


class MockDispatcher:
    """Model dispatch adapter supporting deterministic offline mocks and gated live mode."""

    def __init__(self, ledger: Optional[QuotaLedger] = None, mode: str = "mock"):
        if mode not in ("mock", "live"):
            raise DispatcherError(f"Invalid mode '{mode}'; must be 'mock' or 'live'")
        self.ledger = ledger
        self.mode = mode

    def dispatch(
        self,
        model: str,
        prompt: str,
        *,
        task_id: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Dispatch a prompt to the specified model adapter."""
        if model not in APPROVED_MODELS:
            raise DispatcherError(f"Model '{model}' is not in the approved Serenity pilot allowlist.")

        if not prompt or not isinstance(prompt, str):
            raise DispatcherError("Prompt must be a non-empty string.")

        if self.mode == "live":
            return self._dispatch_live(model, prompt, task_id=task_id, max_tokens=max_tokens)
        else:
            return self._dispatch_mock(model, prompt, task_id=task_id, max_tokens=max_tokens)

    def _dispatch_mock(
        self,
        model: str,
        prompt: str,
        *,
        task_id: Optional[str] = None,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """Generate deterministic synthetic model response."""
        role = APPROVED_MODELS[model]
        ts = iso_utc_now()

        if role == "builder":
            prompt_tokens = min(len(prompt.split()) * 2, 200)
            completion_tokens = 95
            content = (
                "// Serenity Destination Picker Test Helper\n"
                "function validateDestinationTag(tag) {\n"
                "  if (!tag || typeof tag !== 'string') return false;\n"
                "  return tag.trim().length > 0;\n"
                "}\n"
                "module.exports = { validateDestinationTag };\n"
            )
        else:  # reviewer
            prompt_tokens = min(len(prompt.split()) * 2, 350)
            completion_tokens = 110
            review_payload = {
                "verdict": "approve",
                "confidence": 0.96,
                "checks_passed": [
                    "acceptance_criteria_met",
                    "no_auth_or_payment_modified",
                    "bounded_diff_verified",
                    "deterministic_tests_included",
                ],
                "findings": [
                    "Implementation correctly validates input tags without touching database schema.",
                    "Isolated browser helper preserves travel product boundaries.",
                ],
                "recommendation": "Ready for manager quality gate assessment.",
            }
            content = json.dumps(review_payload, indent=2)

        total_tokens = prompt_tokens + completion_tokens

        # Record in quota ledger if connected
        if self.ledger:
            self.ledger.record_usage(
                model, prompt_tokens, completion_tokens,
                task_id=task_id, timestamp=ts, call_type="mock_inference"
            )

        return {
            "mode": "mock",
            "model": model,
            "role": role,
            "task_id": task_id,
            "timestamp": ts,
            "status_code": 200,
            "content": content,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "headers": {
                "x-ratelimit-remaining-requests": "995",
                "x-ratelimit-remaining-tokens": "7850",
                "x-ratelimit-reset-requests": "23h59m",
                "x-ratelimit-reset-tokens": "45s",
            },
        }

    def _dispatch_live(
        self,
        model: str,
        prompt: str,
        *,
        task_id: Optional[str] = None,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """Fail-closed live execution gateway requiring explicit owner authorization."""
        # 1. Verify owner authorization environment variables
        pilot_enabled = os.environ.get("SERENITY_CLOUD_PILOT_ENABLED", "").lower() == "true"
        free_verified = os.environ.get("SERENITY_GROQ_FREE_VERIFIED", "").lower() == "true"

        if not pilot_enabled or not free_verified:
            raise DispatcherError(
                "Live mode blocked: SERENITY_CLOUD_PILOT_ENABLED and "
                "SERENITY_GROQ_FREE_VERIFIED must both be set to 'true' by the owner."
            )

        # 2. Verify secret presence
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            raise DispatcherError(
                "Live mode blocked: GROQ_API_KEY secret is not configured in the environment."
            )

        # 3. Check quota ledger status
        if self.ledger:
            status = self.ledger.evaluate_status(model, estimated_next_call_tokens=max_tokens)
            if status["status"] in ("EXHAUSTED", "WIND_DOWN") and not status.get("finish_allowed"):
                raise DispatcherError(
                    f"Live mode blocked by quota ledger: {status['reason']}"
                )

        # Live calls require explicit network execution; if running in offline test environment,
        # fail closed cleanly
        raise DispatcherError(
            "Live network call halted: live HTTPS invocation must be executed exclusively "
            "within the authorized GitHub Actions workflow '.github/workflows/cloud-model-pilot.yml'."
        )
