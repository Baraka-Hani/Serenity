"""Read-only technical readiness and Obsidian HQ packet for Serenity.

Uses an actual existing Serenity test source, but mock candidate and mock
review only. Produces a reproducible, truthful CI artifact and a handoff
checkpoint. No untrusted code execution, network calls, GitHub mutation,
provider API requests, new credentials, scheduling, spending or deployment.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from company.checkpoint_store import (
    append_event, empty_ledger, store_local, checkpoint_summary,
)
from company.module4_pipeline import (
    SOURCE_PATH, check_source, digest, mock_builder, validate_builder_output,
    validate_task,
)
from company.office import CompanyOffice
from company.obsidian import export_vault
from company.technical_readiness import assess_candidate

TASK_FILE = "config/module4_destination_task.json"
UNTRUSTED_REASON = "model_qa_simulation_not_real_ci"


def generate_packet(source_root, target_dir):
    source_root, target_dir = Path(source_root), Path(target_dir)
    if target_dir.exists() or target_dir.is_symlink():
        raise ValueError("output directory must be new")
    if any(parent.is_symlink() for parent in target_dir.parents if parent.exists()):
        raise ValueError("symlink in output path")
    manifest_path = source_root / TASK_FILE
    if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > 12000:
        raise ValueError("unexpected task manifest")
    task = validate_task(json.loads(manifest_path.read_text(encoding="utf-8")))
    original = check_source(source_root, SOURCE_PATH)
    proposal = mock_builder(task, original)
    validated = validate_builder_output(proposal, task, original)
    candidate = validated["replacement"]
    info = {
        "issue": task["issue"], "risk": task["risk"],
        "target_path": SOURCE_PATH,
        "original_sha256": digest(original),
        "candidate_sha256": digest(candidate),
        "requested_action": "branch_commit",
    }
    readiness = assess_candidate(
        task=info, original=original.encode("utf-8"),
        candidate=candidate.encode("utf-8"),
        builder={"model": "qwen/qwen3.8-27b", "mode": "mock",
                 "candidate_sha256": info["candidate_sha256"]},
        reviewer={"model": "openai/gpt-oss-120b", "mode": "mock",
                  "approved": True, "architecture_alignment": True,
                  "candidate_sha256": info["candidate_sha256"], "findings": []},
        sandbox=None,
    )
    if readiness["status"] != "BLOCKED" or readiness["manager_commit_execution_authorized"]:
        raise ValueError("unverified engineering candidate must not be ready")
    target_dir.mkdir(parents=True, mode=0o700)
    now = datetime.now(timezone.utc)
    journal = append_event(
        empty_ledger(), event_id="issue22-tech-readiness-" + now.strftime("%Y%m%d%H%M%S%f"),
        kind="QA_HANDOFF", actor="operations", shift="outside",
        task_ref="github:Baraka-Hani/Serenity#22",
        timestamp=now.isoformat(),
        payload={"candidate_sha": info["candidate_sha256"],
                 "reason_code": "MOCK_QA_ONLY"},
    )
    store_local(target_dir/"company-checkpoint.json", journal,
                expected_last_hash=empty_ledger()["last_hash"])
    office = CompanyOffice(target_dir/"private-company-state.sqlite3")
    try:
        task_id = office.import_issue(
            "Baraka-Hani/Serenity", task["issue"], task["title"],
            task["acceptance"], ["dept:engineering", "risk:low"])
        office.checkpoint(task_id,
                          "Technical readiness blocked: mock model QA, no sandbox or trusted PR head evidence")
        office.send_message(
            task_id, "lead-builder", "qa-director",
            "Mock candidate checkpoint only; no actual model call, test execution or authorized commit")
        hq = export_vault(office, target_dir/"obsidian-vault",
                          checkpoint_ledger=journal)
    finally:
        office.close()
    result = {
        "schema_version": 1,
        "issue": task["issue"],
        "actual_ai_calls": 0,
        "candidate_source": "deterministic_fixture_using_real_Serenity_test",
        "sandbox_actual_functional_test_executed": False,
        "github_exact_head_proof_fetched": False,
        "remote_cloud_checkpoint_confirmed": False,
        "manager_branch_commit_enabled": False,
        "automatic_merge_enabled": False,
        "billing_or_deployment_changed": False,
        "readiness": readiness,
        "checkpoint": checkpoint_summary(journal),
        "hq": {"mode": "generated_local_mock", "status": "BLOCKED",
               "note": "Obsidian view is a snapshot, not live synchronization"},
    }
    (target_dir/"technical-readiness.json").write_text(
        json.dumps(result, indent=2)+"\n", encoding="utf-8")
    (target_dir/"READINESS.md").write_text(
        "# Serenity technical onboarding — evidence-based handoff\n\n"
        "**STATUS: BLOCKED FOR LIVE AGENT EXECUTION**\n\n"
        "- Real Serenity source considered: `" + SOURCE_PATH + "`\n"
        "- Qwen Builder / GPT-OSS Reviewer: **mock outputs only**\n"
        "- Network-isolated generated-code functional tests: **NOT RUN**\n"
        "- Independent GitHub PR-head and human QA verification: **NOT FETCHED**\n"
        "- GitHub App writer / durable cloud state: **DISABLED**\n"
        "- Billing, production, merge, deployment: **UNCHANGED**\n"
        "- Evidence: `technical-readiness.json`, `company-checkpoint.json`, "
        "`obsidian-vault/Serenity HQ/`\n\n"
        "## Next permitted engineering actions\n\n"
        "1. Verify eligible free provider/account and actual complete quota telemetry; "
        "obtain separate owner approval for any new secrets.\n"
        "2. Validate a pinned Node OCI image and an approved no-secrets runner.\n"
        "3. Run actual generated tests isolated from CI privileges; bind test result to candidate SHA.\n"
        "4. Collect real exact-head GitHub checks and independent reviewer evidence.\n"
        "5. Activate a scoped low-risk manager PR writer only after initial access approval.\n",
        encoding="utf-8",
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = generate_packet(args.source_root, args.output)
    except (ValueError, OSError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps({
        "status": result["readiness"]["status"],
        "issue": result["issue"],
        "actual_ai_calls": result["actual_ai_calls"],
        "manager_branch_commit_enabled": result["manager_branch_commit_enabled"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
