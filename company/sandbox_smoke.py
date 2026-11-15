"""One explicitly owner-approved trusted-source sandbox smoke run.

The workflow consumes *only* existing checked-in first-party Serenity test
code. No generated/untrusted candidate or live provider content is passed
by this command. This deliberately precedes the later generated-code pilot.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from company.sandbox_runner import (
    SandboxBlocked, IMAGE_PATTERN, TEST_TARGET, FIXED_APP,
    run_manual_sandbox,
)

MAX_FILE = 16000


def checksum(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_FILE:
        raise SandboxBlocked("trusted-source smoke test path is not ordinary bounded file")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trusted_smoke(repo_root, output, *, approved_image, owner_approved=False):
    repo_root, output = Path(repo_root), Path(output)
    if (owner_approved is not True
            or not isinstance(approved_image, str)
            or not IMAGE_PATTERN.fullmatch(approved_image)
            or os.environ.get("SERENITY_APPROVED_NODE_IMAGE") != approved_image
            or os.environ.get("SERENITY_SANDBOX_MANUAL") != "true"):
        raise SandboxBlocked("owner-approved Node image and single manual task required")
    if (not repo_root.is_dir() or repo_root.is_symlink()
            or output.exists() or output.is_symlink()
            or any(p.is_symlink() for p in output.parents if p.exists())):
        raise SandboxBlocked("invalid source or existing output destination")
    source = repo_root / TEST_TARGET
    app = repo_root / FIXED_APP
    if (source.is_symlink() or app.is_symlink()):
        raise SandboxBlocked("source symlink rejected")
    source_sha = checksum(source)
    app_sha = checksum(app)
    output.mkdir(parents=True, mode=0o700)
    result = run_manual_sandbox(
        repo_root, source, output / "workspace",
        candidate_sha256=source_sha, approved_image_digest=approved_image,
        owner_approved_sandbox=True)
    record = {
        "schema_version": 1,
        "purpose": "KNOWN_CHECKED_IN_SERENITY_TEST_SMOKE",
        "source_sha256": source_sha,
        "candidate_sha256": source_sha,
        "app_sha256": app_sha,
        "image_digest": approved_image,
        "runner_result": result,
        "github_run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "github_head_sha": os.environ.get("GITHUB_SHA", ""),
        "github_workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF", ""),
        "github_job_name": os.environ.get("GITHUB_JOB", ""),
        "provenance": "UNTRUSTED_OUTPUT_PENDING_INDEPENDENT_GITHUB_JOB_LOOKUP",
        "model_generated_code_executed": False,
        "manager_commit_authorized": False,
        "automatic_merge_authorized": False,
    }
    (output/"sandbox-smoke.json").write_text(
        json.dumps(record, indent=2)+"\n", encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = trusted_smoke(
            args.source_root, args.output,
            approved_image=os.environ.get("SERENITY_APPROVED_NODE_IMAGE", ""),
            owner_approved=os.environ.get("SERENITY_SANDBOX_MANUAL")=="true",
        )
    except (OSError, ValueError, SandboxBlocked) as exc:
        parser.exit(2, "BLOCKED: " + str(exc)+"\n")
    print(json.dumps({
        "status": "TRUSTED_SOURCE_SANDBOX_SMOKE_EXECUTED",
        "test_passed": result["runner_result"]["passed"],
        "model_generated_code_executed": False,
        "manager_commit_authorized": False,
    }, indent=2))
    if not result["runner_result"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
