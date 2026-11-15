#!/usr/bin/env python3
"""Offline-only Serenity model-routing dry run; never calls a model or writes to GitHub."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "ai_company_models.json"

class PolicyError(ValueError):
    pass

def route(config, *, task_type, risk, prompt_characters=0, proposed_output_tokens=0):
    """Return a proposed role allocation, never an executable request."""
    policy = config["policies"]
    if config.get("status") != "disabled" or config["future_execution"].get("enabled"):
        raise PolicyError("Dry-run simulator requires disabled model execution")
    if risk not in policy["allowed_risk_levels"]:
        raise PolicyError(f"Risk level {risk!r} is not allowed")
    if task_type in policy["blocked_task_types"] or task_type not in policy["allowed_task_types"]:
        raise PolicyError(f"Task type {task_type!r} is not allowed")
    if not isinstance(prompt_characters, int) or prompt_characters < 0 or prompt_characters > policy["maximum_prompt_characters"]:
        raise PolicyError("Prompt exceeds declared character cap")
    if (not isinstance(proposed_output_tokens, int) or proposed_output_tokens < 0
            or proposed_output_tokens > policy["maximum_output_tokens_per_request"]):
        raise PolicyError("Output exceeds declared token cap")
    roles = {m["role"]: m["model_id"] for m in config["models"] if task_type in m["task_types"]}
    if set(roles) != {"builder", "first_pass_reviewer"}:
        raise PolicyError("Both model roles must support this task")
    return {
        "execution": "DISABLED_OFFLINE_SIMULATION",
        "task_type": task_type,
        "risk": risk,
        "builder_model_id": roles["builder"],
        "reviewer_model_id": roles["first_pass_reviewer"],
        "human_review_required": policy["require_human_review"],
        "allowed_to_merge": policy["can_merge"],
        "allowed_to_deploy": policy["can_deploy"],
        "allowed_to_spend": policy["can_make_paid_calls"],
        "next_stage": "OWNER_VERIFY_FREE_PROVIDER_AND_MANUAL_SMOKE_TEST",
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--task-type", required=True)
    parser.add_argument("--risk", default="low")
    parser.add_argument("--prompt-characters", type=int, default=0)
    parser.add_argument("--output-tokens", type=int, default=0)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        decision = route(config, task_type=args.task_type, risk=args.risk,
                         prompt_characters=args.prompt_characters,
                         proposed_output_tokens=args.output_tokens)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(decision, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
