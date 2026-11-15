"""Network-disabled, resource-capped OCI functional-test runner for Serenity.

Untrusted candidate JavaScript is NEVER executed by Python or directly on
GitHub Actions host. This builds a private, minimal read-only test workspace
and a fixed Docker CLI invocation; no model-supplied shell commands, images,
network URLs, mount paths or environment variables are accepted. Default OFF.

A trusted administrator must approve a locally cached, reviewed Node image
pinned to an actual digest before a manual container run.
"""
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from company.module4_pipeline import SOURCE_PATH, Module4Blocked, check_source

IMAGE_PATTERN = re.compile(r"^docker\.io/library/node:22-bookworm-slim@sha256:[0-9a-f]{64}$")
SHA = re.compile(r"^[a-f0-9]{64}$")
MAX_JS_BYTES = 6500
MAX_OUTPUT = 12000
TEST_TARGET = "backend/test_destination_picker.js"
FIXED_APP = "destination-picker.js"


class SandboxBlocked(RuntimeError):
    pass


def _check_file(path, *, max_bytes=MAX_JS_BYTES):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise SandboxBlocked("invalid or oversized sandbox input")
    raw = path.read_bytes()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        raise SandboxBlocked("sandbox input must be UTF-8") from None
    return raw


def prepare_workspace(repo_root, candidate_path, output_directory, *,
                      expected_candidate_sha256):
    """Copy only 2 non-sensitive JS files into a new isolated directory."""
    if not isinstance(expected_candidate_sha256, str) or not SHA.fullmatch(expected_candidate_sha256):
        raise SandboxBlocked("candidate source SHA-256 is required")
    source = _check_file(candidate_path)
    if hashlib.sha256(source).hexdigest() != expected_candidate_sha256:
        raise SandboxBlocked("candidate source hash mismatch")
    # Trusted app JS may be larger than the candidate; still bounded.
    app = Path(repo_root) / FIXED_APP
    for parent in (app, *app.parents):
        if parent == Path(repo_root).parent:
            break
        if parent.is_symlink():
            raise SandboxBlocked("application source symlink rejected")
    app_source = _check_file(app, max_bytes=16000)
    out = Path(output_directory)
    if out.exists() or out.is_symlink():
        raise SandboxBlocked("sandbox scratch workspace must be newly created")
    if any(p.is_symlink() for p in out.parents if p.exists()):
        raise SandboxBlocked("sandbox scratch parent symlink rejected")
    out.mkdir(parents=True, mode=0o700)
    (out / "backend").mkdir(mode=0o700)
    (out / TEST_TARGET).write_bytes(source)
    (out / FIXED_APP).write_bytes(app_source)
    # World-readability is necessary for the UID 65534 sandbox user; no secrets
    # exist in this fixed two-source-file workspace.
    os.chmod(out, 0o755)
    os.chmod(out / "backend", 0o755)
    os.chmod(out / TEST_TARGET, 0o444)
    os.chmod(out / FIXED_APP, 0o444)
    return {"workspace": str(out), "candidate_sha256": expected_candidate_sha256,
            "files": [TEST_TARGET, FIXED_APP], "no_secrets_or_runtime_data": True}


def fixed_command(workspace, *, image_digest):
    if not isinstance(image_digest, str) or not IMAGE_PATTERN.fullmatch(image_digest):
        raise SandboxBlocked("approved official Node 22 image digest required")
    space = Path(workspace)
    if space.is_symlink() or not space.is_dir():
        raise SandboxBlocked("invalid sandbox work directory")
    # No user-selected program or arguments. Read-only root and workspace.
    return [
        "docker", "run", "--rm", "--pull=never",
        "--network=none", "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user=65534:65534", "--pids-limit=48",
        "--memory=256m", "--memory-swap=256m", "--cpus=1",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=12m,mode=1777",
        "--workdir=/workspace",
        "--mount", "type=bind,src=" + str(space.resolve()) +
                   ",dst=/workspace,readonly",
        image_digest, "node", TEST_TARGET,
    ]


def run_manual_sandbox(repo_root, candidate_path, workspace, *,
                       candidate_sha256, approved_image_digest,
                       owner_approved_sandbox=False, runner=None):
    """Run on a dedicated, clean, non-production worker only after approval.

    No API token or provider credentials are read from the environment. The
    invoking GitHub workflow MUST have no secrets, no outbound credentials,
    read-only contents, and no repository write permissions.
    """
    if (owner_approved_sandbox is not True or
            os.environ.get("SERENITY_SANDBOX_MANUAL") != "true"):
        raise SandboxBlocked("sandbox execution is disabled pending authorization")
    prepared = prepare_workspace(repo_root, candidate_path, workspace,
                                 expected_candidate_sha256=candidate_sha256)
    command = fixed_command(prepared["workspace"], image_digest=approved_image_digest)
    execute = runner if runner is not None else subprocess.run
    try:
        result = execute(
            command, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, check=False, timeout=25,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                 "LANG": "C.UTF-8"},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SandboxBlocked("sandbox unavailable or timed out") from None
    if result.returncode not in (0, 1):
        raise SandboxBlocked("container runtime failed or test was terminated")
    return {
        "candidate_sha256": candidate_sha256,
        "actual_functional_test_executed": True,
        "sandbox": "docker_network_none_readonly_unprivileged",
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "stdout_tail": str(result.stdout)[-MAX_OUTPUT:],
        "stderr_tail": str(result.stderr)[-MAX_OUTPUT:],
        "command_template": "node backend/test_destination_picker.js",
        "image_digest": approved_image_digest,
        "github_write_permissions": False,
    }
