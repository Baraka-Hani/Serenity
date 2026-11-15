#!/usr/bin/env python3
"""Manual-only, synthetic-code cloud model pilot for Serenity.

Default mode is offline. Live mode needs explicit operator authorization and a
free-tier Groq API key; it makes exactly ONE bounded model request.
Model output is untrusted REVIEW MATERIAL, never executable code.
"""
import argparse
import json
import os
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "ai_company_models.json"
ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
MAX_RESPONSE_BYTES = 65536
MAX_OUTPUT_TOKENS = 500

# Intentional synthetic-only fixture. Never load actual repository files,
# customer content, or private data into the first pilot.
FIXTURE = """def normalize_label(value):
    return ' '.join(value.split())
"""
INSTRUCTIONS = {
    "builder": (
        "On this public synthetic Python snippet, propose a docstring and three "
        "Python unittest test cases. Do not make network calls or edit files. "
        "Return concise plain text containing PROPOSAL and TESTS headings."
    ),
    "reviewer": (
        "Independently review this synthetic Python function for edge cases, "
        "possible exceptions, test gaps and documentation quality. Respond with "
        "FINDINGS and RECOMMENDATION headings. Do not claim to have run tests."
    ),
}
ROLE_IDS = {"builder": "builder", "reviewer": "first_pass_reviewer"}


class PilotBlocked(ValueError):
    pass


def load_config(path=CONFIG_PATH):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    # The workforce remains DISABLED; this CLI is a separate manual-only test.
    if config.get("status") != "disabled" or config.get("future_execution", {}).get("enabled") is not False:
        raise PilotBlocked("automated execution must remain disabled")
    if config.get("provider", {}).get("name") != "groq" or config["provider"].get("free_only") is not True:
        raise PilotBlocked("approved provider / free-only policy not present")
    policy = config.get("policies", {})
    if (policy.get("can_make_paid_calls") is not False
            or policy.get("can_push") is not False
            or policy.get("can_merge") is not False
            or policy.get("can_deploy") is not False):
        raise PilotBlocked("non-executing, zero-spend safety boundaries are required")
    return config


def model_for(config, role):
    if role not in ROLE_IDS:
        raise PilotBlocked("unsupported agent role")
    matches = [m["model_id"] for m in config["models"] if m.get("role") == ROLE_IDS[role]
               and m.get("provider") == "groq"]
    if len(matches) != 1:
        raise PilotBlocked("missing or duplicate approved model")
    model = matches[0]
    if model not in ("qwen/qwen3.8-27b", "openai/gpt-oss-120b"):
        raise PilotBlocked("model not approved for this pilot")
    return model


def create_payload(model, role):
    if role not in INSTRUCTIONS:
        raise PilotBlocked("unsupported role")
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a code reviewer working on synthetic public test data. Output is a suggestion, not verified code."},
            {"role": "user", "content": INSTRUCTIONS[role] + "\n\nSYNTHETIC CODE:\n" + FIXTURE},
        ],
        "max_completion_tokens": MAX_OUTPUT_TOKENS,
        "stream": False,
    }


def observed_quota(headers):
    """A PARTIAL observation; Groq headers omit some applicable limits.

    These headers currently refer to requests/day and tokens/minute. Never
    treat them alone as evidence that all usage buckets are under 90%.
    """
    observations = []
    for kind, label in (("requests", "requests_per_day"), ("tokens", "tokens_per_minute")):
        try:
            limit = int(headers.get("x-ratelimit-limit-" + kind, ""))
            remain = int(headers.get("x-ratelimit-remaining-" + kind, ""))
            if limit <= 0 or not 0 <= remain <= limit:
                continue
            observations.append({
                "window": label,
                "used_percent": round(100 * (1 - remain / limit), 2),
                "at_or_over_90_percent": remain / limit <= 0.10,
                "reset_hint": str(headers.get("x-ratelimit-reset-" + kind, ""))[:40],
            })
        except (TypeError, ValueError):
            continue
    return {
        "complete": False, "automatic_new_work_allowed": False,
        "observed_windows": observations,
        "reason": "response headers are partial; use account-specific limits and a trusted ledger before scheduling",
    }


def live_response(payload, *, api_key):
    """One HTTPS request. No retries, no external URLs or side effects."""
    if not api_key or not api_key.strip():
        raise PilotBlocked("API key missing")
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(data) > 4096:
        raise PilotBlocked("synthetic prompt exceeded byte limit")
    req = request.Request(
        ENDPOINT, data=data, method="POST",
        headers={"Authorization": "Bearer " + api_key,
                 "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            if resp.geturl() != ENDPOINT:
                raise PilotBlocked("redirected response rejected")
            raw = resp.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise PilotBlocked("model response exceeded maximum length")
            obj = json.loads(raw.decode("utf-8"))
            text = obj["choices"][0]["message"]["content"]
            if not isinstance(text, str):
                raise PilotBlocked("unexpected model output")
            usage = obj.get("usage") or {}
            return {
                "response_excerpt": text[:3500],
                "usage": {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                          if isinstance(usage.get(k), int)},
                "quota": observed_quota(resp.headers),
            }
    except error.HTTPError as exc:
        # Do not echo provider response body, secret-bearing headers or URLs.
        if exc.code == 429:
            raise PilotBlocked("provider rate limit hit (429); checkpoint and stop, no retry") from None
        raise PilotBlocked("provider rejected request (HTTP " + str(exc.code) + ")") from None
    except (error.URLError, TimeoutError):
        raise PilotBlocked("network unavailable or timed out; no retry") from None
    except (KeyError, IndexError, ValueError, UnicodeError):
        raise PilotBlocked("unexpected provider response; no retry") from None


def run_pilot(config, *, role="builder", mode="mock", environ=None, transport=live_response):
    environ = os.environ if environ is None else environ
    model = model_for(config, role)
    payload = create_payload(model, role)
    result = {
        "status": "PROPOSAL_ONLY",
        "mode": mode,
        "model": model,
        "role": role,
        "source": "SYNTHETIC_PUBLIC_FIXTURE",
        "trusted_code": False,
        "executed_generated_code": False,
        "automatic_new_work_allowed": False,
        "repository_writes": False,
        "production_access": False,
        "cost_confirmation": "No provider billing verification available from this CLI",
        "requires_owner_review": True,
    }
    if mode == "mock":
        result["status"] = "SIMULATED"
        result["response_excerpt"] = ("PROPOSAL: add a descriptive docstring. TESTS: whitespace, empty input, "
                                      "non-string input." if role == "builder" else
                                      "FINDINGS: missing type validation. RECOMMENDATION: add tests.")
        result["quota"] = {"complete": False, "automatic_new_work_allowed": False}
        return result
    if mode != "live":
        raise PilotBlocked("mode must be mock or live")
    # Owner must verify provider eligibility, free account, data terms and
    # usage limits BEFORE setting these flags. CLI cannot check billing tier.
    if (environ.get("SERENITY_PILOT_APPROVED") != "true"
            or environ.get("SERENITY_GROQ_FREE_VERIFIED") != "true"):
        raise PilotBlocked("live synthetic smoke test not explicitly approved and free-tier verified")
    response = transport(payload, api_key=environ.get("GROQ_API_KEY", ""))
    result.update(response)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=tuple(ROLE_IDS), default="builder")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args(argv)
    try:
        result = run_pilot(load_config(), role=args.role, mode=args.mode)
    except (PilotBlocked, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    report = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
