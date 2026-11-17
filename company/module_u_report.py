"""Standalone Module U CI/HQ artifact: real Serenity source, simulated work.

No GitHub write, no live provider call, no actual sandbox execution, no
authorization upgrade and no remote checkpoint read by default. The output
folder must be new; existing personal Obsidian files are not modified.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from company.checkpoint_store import load_local
from company.module_u_recovery import inspect_recovery, recovery_markdown
from company.module_u_rehearsal import rehearse_draft_pr
from company.module_u_shift import assess_next_shift, shift_markdown
from company.technical_report import generate_packet


def generate_module_u(source_root, output_dir):
    out = Path(output_dir)
    # Reuse the already tested honest Module T read-only packet + Obsidian vault.
    previous = generate_packet(source_root, out)
    if previous["readiness"]["status"] != "BLOCKED":
        raise ValueError("technical readiness must be blocked before rehearsal")
    ledger = load_local(out / "company-checkpoint.json")
    recovery = inspect_recovery(ledger)  # No remote network access.
    dry_run = rehearse_draft_pr(source_root)  # No source or GitHub write.
    # Deterministic local-shift sample only; NOT today's actual provider meter.
    synthetic_review_time = datetime(2026, 11, 14, 10, 0,
                                     tzinfo=ZoneInfo("America/Moncton"))
    shift = assess_next_shift(ledger, {}, now=synthetic_review_time)
    if (recovery["status"] != "REMOTE_NOT_OBSERVED"
            or shift["decision"] != "CHECKPOINT_NO_NEW_TASKS"
            or dry_run["manager_write_authorized"] is not False):
        raise ValueError("offline report cannot assert cloud or manager activation")
    results = {
        "schema_version": 1,
        "module": "U",
        "status": "OFFLINE_CONTROL_PLANE_VERIFIED_LIVE_COMPANY_BLOCKED",
        "issue": 36,
        "candidate": dry_run,
        "cloud_recovery": recovery,
        "shift_readiness": shift,
        "source_not_modified": True,
        "verified_remote_git_read": False,
        "trusted_ci_checked_on_candidate": False,
        "actual_sandbox_execution": False,
        "actual_cloud_model_calls": 0,
        "new_spending_authorized": False,
        "github_writes_performed": 0,
        "manager_writes_authorized": False,
        "autonomous_agents_active": False,
        "merge_deploy_authorized": False,
    }
    (out / "module-u-report.json").write_text(
        json.dumps(results, indent=2)+"\n", encoding="utf-8")
    (out / "manager-pr-rehearsal.json").write_text(
        json.dumps(dry_run, indent=2)+"\n", encoding="utf-8")
    (out / "cloud-recovery.json").write_text(
        json.dumps(recovery, indent=2)+"\n", encoding="utf-8")
    (out / "shift-readiness.json").write_text(
        json.dumps(shift, indent=2)+"\n", encoding="utf-8")
    operations = out / "obsidian-vault" / "Serenity HQ" / "Operations"
    (operations / "Cloud Recovery.md").write_text(
        recovery_markdown(recovery), encoding="utf-8")
    (operations / "Shift Quotas.md").write_text(
        shift_markdown(shift), encoding="utf-8")
    (operations / "Manager PR Rehearsal.md").write_text(
        "# Serenity Engineering Manager — Dry-Run Draft PR\n\n"
        "> This report contains deliberately fabricated QA and sandbox fixtures. "
        "No AI models, Docker tests or GitHub writers ran.\n\n"
        "- Scope: **Issue #22 / backend/test_destination_picker.js only**\n"
        "- Source SHA-256: `" + dry_run["source_sha256"] + "`\n"
        "- Candidate SHA-256: `" + dry_run["candidate_sha256"] + "`\n"
        "- Source Git blob SHA (unauthenticated local checkout): `"
        + dry_run["source_git_blob_sha"] + "`\n"
        "- Draft PR intent: **PREVIEW ONLY**\n"
        "- Proposed PR idempotency key: `"
        + dry_run["intent"]["idempotency_key"] + "`\n"
        "- Independent model QA: **NOT RUN**\n"
        "- Isolated functional tests: **NOT RUN**\n"
        "- Authenticated source blob from GitHub: **NOT FETCHED**\n"
        "- Manager commits / draft PR writes: **DISABLED**\n"
        "- Financial spending: **NONE AUTHORIZED**\n\n"
        "Rollback would require independently verifying the exact original "
        "Git blob before changing any approved feature branch.\n",
        encoding="utf-8")
    command_centre = out / "obsidian-vault" / "Serenity HQ" / "Command Centre.md"
    with command_centre.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n## Module U — Quality and Recovery Readiness\n\n"
            "- [[Operations/Cloud Recovery|Read-only cloud recovery and conflict report]]\n"
            "- [[Operations/Shift Quotas|Quota-aware two-shift readiness]]\n"
            "- [[Operations/Manager PR Rehearsal|Manager draft PR rehearsal — NOT LIVE]]\n"
            "- GitHub source/QA dossier: **available as a tested read-only interface; no real candidate PR inspected**\n"
            "- Remote company state: **NOT OBSERVED**\n"
            "- Autonomous company agents: **DISABLED**\n"
        )
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = generate_module_u(args.source_root, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps({
        "status": result["status"], "issue": result["issue"],
        "github_writes_performed": result["github_writes_performed"],
        "actual_cloud_model_calls": result["actual_cloud_model_calls"],
        "manager_writes_authorized": result["manager_writes_authorized"],
    }, indent=2))


if __name__ == "__main__":
    main()
