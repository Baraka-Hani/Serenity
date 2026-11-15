"""Produce a full company Module 5 two-shift HQ artifact without any services.

Simulates the operational handoff for real Serenity Issue #22 using local
durable event checkpoints. Does not invoke model APIs, GitHub writes, Docker,
paid services or production systems.
"""
import argparse
import json
import os
from datetime import date
from pathlib import Path

from company.checkpoint_store import (
    empty_ledger, store_local, load_local, checkpoint_summary,
)
from company.shift_coordinator import simulate_two_shifts, propose_shift
from company.office import CompanyOffice
from company.obsidian import export_vault


def generate(output, *, day):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("output directory must not exist")
    if any(p.is_symlink() for p in output.parents if p.exists()):
        raise ValueError("symlink output parent forbidden")
    output.mkdir(parents=True)
    checkpoint = output / "company-checkpoint.json"
    original = empty_ledger()
    two_shifts = simulate_two_shifts(original, day=day)
    stored = store_local(checkpoint, two_shifts, expected_last_hash=original["last_hash"])
    recovered = load_local(checkpoint)
    if recovered["last_hash"] != two_shifts["last_hash"]:
        raise ValueError("checkpoint did not survive disk round-trip")
    db = output / "serenity-company.sqlite3"
    office = CompanyOffice(db)
    try:
        task_id = office.import_issue(
            "Baraka-Hani/Serenity", 22,
            "Strengthen destination picker first-party API test",
            "Test candidate awaits verified full CI, independent QA and sandbox",
            ["dept:engineering", "risk:low"])
        office.shift_checkpoint("shift_1_start", "Sample 09:00 intake. No actual model calls.")
        office.transition(task_id, "EVALUATED", "Safe synthetic operations demo only")
        office.assign(task_id, "lead-builder")
        office.transition(task_id, "QUEUED", "No automatic executor enabled")
        office.checkpoint(task_id, "First shift records demo candidate, not runnable code")
        office.shift_checkpoint("shift_1_end_shift_2_start",
                                "Sample 14:00: checkpoint persisted and read back")
        office.send_message(task_id, "lead-builder", "qa-director",
                            "Candidate awaits authenticated sandbox and trusted CI checks")
        office.shift_checkpoint("shift_2_end",
                                "Sample 19:00: quality gate blocked; no owner finance request")
        hq = export_vault(office, output / "obsidian-vault",
                          checkpoint_ledger=recovered)
        # The SQLite copy is included for inspection but is NOT cloud-durable
        # without approved remote persistence.
        summary = {
            "simulated": True, "task_id": task_id,
            "ledger": checkpoint_summary(recovered),
            "local_store": stored,
            "hq": hq,
            "actual_cloud_calls": 0,
            "actual_autonomous_shifts": 0,
            "actual_code_commits": 0,
            "actual_spending": 0,
            "github_remote_persistence_enabled": False,
            "manager_writer_enabled": False,
            "next_gate": "trusted sandbox CI and owner-approved GitHub state/manager access",
        }
    finally:
        office.close()
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--day", default="2026-11-14",
                        help="simulation date in America/Moncton")
    args = parser.parse_args()
    try:
        result = generate(args.output, day=date.fromisoformat(args.day))
    except (ValueError, OSError) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
