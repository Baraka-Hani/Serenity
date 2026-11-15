"""Bounded GroqCloud chat adapter for the two approved hosted open-weight models.

Network calls occur ONLY when explicitly passed an approved, manual, eligible
live-run context. No default credentials, no scheduled background calls, no
billing or account management, no retries and no redirect to another host.
All model output is untrusted structured data requiring further validation.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error, request

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MODELS = {"builder": "qwen/qwen3.8-27b", "reviewer": "openai/gpt-oss-120b"}
MAX_PROMPT_BYTES = 11500
MAX_RESPONSE_BYTES = 25000
MAX_COMPLETION_TOKENS = 1000

PATCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "run_key", "path", "source_sha256",
                 "replacement_text", "rationale", "test_plan"],
    "properties": {
        "schema_version": {"type": "integer"},
        "run_key": {"type": "string"},
        "path": {"type": "string"},
        "source_sha256": {"type": "string"},
        "replacement_text": {"type": "string"},
        "rationale": {"type": "string"},
        "test_plan": {"type": "string"},
    },
}
REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "run_key", "approved", "findings",
                 "required_tests", "architecture_alignment", "risk_flags"],
    "properties": {
        "schema_version": {"type": "integer"},
        "run_key": {"type": "string"},
        "approved": {"type": "boolean"},
        "findings": {"type": "array", "items": {"type": "string"}},
        "required_tests": {"type": "array", "items": {"type": "string"}},
        "architecture_alignment": {"type": "boolean"},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
    },
}


class ProviderBlocked(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ManualContext:
    """Explicit per-call approval, not a standing agent authorization."""
    eligible_free_account_verified: bool = False
    data_terms_accepted: bool = False
    owner_approved_one_call: bool = False
    quota_preflight_ready: bool = False
    unattended: bool = False


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _model_payload(role, system_instruction, user_context):
    if role not in MODELS:
        raise ProviderBlocked("MODEL", "unapproved model role")
    if not isinstance(system_instruction, str) or not isinstance(user_context, str):
        raise ProviderBlocked("CONTEXT", "both prompts must be strings")
    if not 10 <= len(system_instruction) <= 1800:
        raise ProviderBlocked("CONTEXT", "system policy prompt outside size cap")
    if not user_context.strip() or len(user_context.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ProviderBlocked("CONTEXT", "empty or excessive source context")
    schema = PATCH_SCHEMA if role == "builder" else REVIEW_SCHEMA
    return {
        "model": MODELS[role],
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_context},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "serenity_patch_v1" if role == "builder" else "serenity_review_v1",
                "strict": True, "schema": schema,
            },
        },
        "reasoning_effort": "none" if role == "builder" else "low",
        "reasoning_format": "hidden",
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "stream": False,
    }


def partial_quota(headers):
    """Groq response headers prove RPD and TPM only, NOT all account quotas."""
    result = {"complete": False, "automatic_resumption_allowed": False, "windows": []}
    if not headers:
        return result
    for source, name in (("requests", "requests_per_day"),
                         ("tokens", "tokens_per_minute")):
        try:
            ceiling = int(headers.get("x-ratelimit-limit-" + source, ""))
            remain = int(headers.get("x-ratelimit-remaining-" + source, ""))
            if not 0 < ceiling or not 0 <= remain <= ceiling:
                continue
            result["windows"].append({
                "name": name, "total": ceiling, "remaining": remain,
                "percent_used": round(100 * (ceiling-remain)/ceiling, 3),
                "wind_down": (ceiling-remain)/ceiling >= 0.90,
                "reset_hint": str(headers.get("x-ratelimit-reset-" + source, ""))[:40],
            })
        except (ValueError, TypeError):
            continue
    return result


def _preflight(ctx, api_key):
    if not isinstance(ctx, ManualContext):
        raise ProviderBlocked("AUTHORIZATION", "explicit manual execution context missing")
    if ctx.unattended:
        raise ProviderBlocked("UNATTENDED", "standing agent execution not enabled")
    if not (ctx.eligible_free_account_verified and ctx.data_terms_accepted
            and ctx.owner_approved_one_call and ctx.quota_preflight_ready):
        raise ProviderBlocked("AUTHORIZATION", "free plan, data terms, quota and one-call approval required")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ProviderBlocked("CREDENTIALS", "provider credentials not available")
    if os.environ.get("SERENITY_PROVIDER_MANUAL_LIVE") != "true":
        raise ProviderBlocked("DISABLED", "manual provider switch is default-off")


def call_groq(role, system_instruction, user_context, *, ctx, api_key="",
              transport=None):
    """One bounded request; optional injected transport is for unit tests only."""
    payload = _model_payload(role, system_instruction, user_context)
    _preflight(ctx, api_key)
    wire = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(wire) > MAX_PROMPT_BYTES + 3200:
        raise ProviderBlocked("CONTEXT", "request larger than policy cap")

    req = request.Request(ENDPOINT, data=wire, method="POST",
                          headers={"Authorization": "Bearer " + api_key,
                                   "Content-Type": "application/json",
                                   "Accept": "application/json"})
    opener = transport if transport is not None else request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=20) as response:
            if response.geturl() != ENDPOINT:
                raise ProviderBlocked("REDIRECT", "unapproved response destination")
            raw = response.read(MAX_RESPONSE_BYTES+1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ProviderBlocked("OVERSIZE", "oversized model response")
            doc = json.loads(raw.decode("utf-8"))
            if not isinstance(doc, dict) or not isinstance(doc.get("choices"), list):
                raise ProviderBlocked("FORMAT", "invalid model response")
            content = doc["choices"][0]["message"]["content"]
            if not isinstance(content, str) or len(content) > MAX_RESPONSE_BYTES:
                raise ProviderBlocked("FORMAT", "model output is not bounded text")
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ProviderBlocked("FORMAT", "model JSON must be an object")
            usage = doc.get("usage") or {}
            safe_usage = {key: int(usage[key]) for key in
                          ("prompt_tokens", "completion_tokens", "total_tokens")
                          if type(usage.get(key)) is int and usage[key] >= 0}
            return {"role": role, "model_id": MODELS[role],
                    "output": parsed, "usage": safe_usage,
                    "quota_partial": partial_quota(response.headers)}
    except error.HTTPError as exc:
        if exc.code == 429:
            raise ProviderBlocked("QUOTA", "provider 429; checkpoint, no retry") from None
        if exc.code in (402, 403):
            raise ProviderBlocked("BILLING_OR_ACCESS", "free-tier access not authorized; no paid fallback") from None
        raise ProviderBlocked("PROVIDER", "provider returned HTTP " + str(exc.code)) from None
    except (error.URLError, TimeoutError):
        raise ProviderBlocked("TRANSPORT", "provider unavailable; no automatic retry") from None
    except (json.JSONDecodeError, UnicodeDecodeError, KeyError, IndexError, TypeError):
        raise ProviderBlocked("FORMAT", "malformed or incomplete provider result") from None
