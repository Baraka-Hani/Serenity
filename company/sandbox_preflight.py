"""Read-only, zero-network Serenity Module T sandbox activation preflight.

This validates the *source checkout's* known-source smoke scope and
manual-workflow safety policy, but it does not authenticate GitHub branch
rules/variables, approve paid compute or run a container.
"""
import hashlib
from pathlib import Path

from company.sandbox_runner import IMAGE_PATTERN

APP = "destination-picker.js"
TEST = "backend/test_destination_picker.js"
WORKFLOW = ".github/workflows/serenity-candidate-sandbox.yml"
MAX_BYTES = {APP: 16000, TEST: 6500, WORKFLOW: 12000}


class PreflightBlocked(ValueError):
    pass


def _read_fixed(root, name):
    base = Path(root)
    if not base.is_dir() or base.is_symlink():
        raise PreflightBlocked("checkout root must be an ordinary directory")
    current = base
    for part in Path(name).parts:
        current = current / part
        if current.is_symlink():
            raise PreflightBlocked("symlinks are forbidden in preflight inputs")
    if not current.is_file() or not 0 < current.stat().st_size <= MAX_BYTES[name]:
        raise PreflightBlocked("missing or oversized reviewed input")
    contents = current.read_bytes()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        raise PreflightBlocked("review input not valid UTF-8") from None
    return contents, decoded


def preflight(root):
    """Return honest audit packet; NEVER authorizes a live run."""
    app, _ = _read_fixed(root, APP)
    test, _ = _read_fixed(root, TEST)
    workflow, yaml = _read_fixed(root, WORKFLOW)
    required = (
        "workflow_dispatch:", "contents: read",
        "github.ref == 'refs/heads/main'",
        "vars.SERENITY_SANDBOX_OWNER_APPROVED == 'true'",
        "vars.SERENITY_APPROVED_NODE_IMAGE != ''",
        "persist-credentials: false",
        "Execute isolated test in network-off Docker",
        "docker pull \"$IMAGE\"",
        "python3 -m company.sandbox_smoke",
        "retention-days: 7",
    )
    if any(marker not in yaml for marker in required):
        raise PreflightBlocked("manual owner-approval workflow contract changed")
    for prohibited in (
        "pull_request_target:", "\n  schedule:", "contents: write",
        "actions: write", "id-token: write", "SERENITY_REMOTE_STATE_WRITE",
        "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY", "gh pr merge", "docker.sock",
    ):
        if prohibited in yaml:
            raise PreflightBlocked("disallowed workflow permission or command")
    if "on:\n  workflow_dispatch:" not in yaml:
        raise PreflightBlocked("workflow is not exclusively manual")
    return {
        "schema_version": 1,
        "module": "T",
        "repository": "Baraka-Hani/Serenity",
        "source_scope": [APP, TEST],
        "source_sha256": hashlib.sha256(test).hexdigest(),
        "app_sha256": hashlib.sha256(app).hexdigest(),
        "workflow_sha256": hashlib.sha256(workflow).hexdigest(),
        "source_checkout_scanned": True,
        "workflow_policy_static_check_passed": True,
        "owner_approved_image_digest_verified": False,
        "protected_main_ruleset_verified": False,
        "github_actions_no_cost_verified": False,
        "github_live_job_ran": False,
        "sandbox_image_registry_digest_verified": False,
        "actual_functional_smoke_executed": False,
        "model_generated_candidate_executed": False,
        "signed_runner_attestation_available": False,
        "manager_github_writes_enabled": False,
        "new_spending_authorized": False,
        "merge_or_deploy_authorized": False,
        "status": "BLOCKED_OWNER_IMAGE_AND_RUN_AUTHORIZATION",
        "next_action": "Owner/admin verifies GitHub Actions quota, protected main and exact image digest; after separately approving initial setup, dispatch one manual trusted-source test",
    }
