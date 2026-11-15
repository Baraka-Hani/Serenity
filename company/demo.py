#!/usr/bin/env python3
"""Create a complete SAMPLE two-shift agent handoff and export an Obsidian HQ.

Only fixture data and simulated organization roles, no model calls. This is
not evidence that real agents have executed any code.
"""
import argparse
import json
import tempfile
from pathlib import Path
from company.office import CompanyOffice
from company.obsidian import export_vault


def simulate(db_path, vault):
    office = CompanyOffice(db_path)
    try:
        office.shift_checkpoint("shift_1_start", "Simulated 09:00 intake; no actual agents connected")
        task_id = office.new_task(
            "Sample: prepare travel-video card test cases",
            "engineering", "Proposal includes valid rendering and missing-media test cases", "low")
        office.transition(task_id, "EVALUATED", "Synthetic task has clear acceptance criteria")
        office.assign(task_id, "lead-builder")
        office.transition(task_id, "QUEUED", "Mock assignment only")
        office.transition(task_id, "IN_PROGRESS", "Simulated Builder work, no model or code executed")
        office.checkpoint(task_id, "Mock implementation note saved; tests not actually run",
                          "example/not-a-real-branch")
        msg_id = office.send_message(task_id, "lead-builder", "qa-director",
                                    "Sample handoff: inspect placeholder test-plan, no implementation available")
        office.transition(task_id, "IN_REVIEW", "QA review requested on synthetic fixture")
        office.shift_checkpoint("shift_1_end_shift_2_start",
                                "Simulated 14:00 handoff; task remains IN_REVIEW")
        office.acknowledge(msg_id, "qa-director")
        office.send_message(task_id, "qa-director", "chief-of-staff",
                            "Sample QA note: require real passing tests before verification")
        office.shift_checkpoint("shift_2_end",
                                "Simulated 19:00 final report: unverified task pending actual tests")
        office.request_approval(task_id, "merge",
                                "Illustrative only: no merge until real code and independent tests exist")
        exported = export_vault(office, vault)
        return {"simulation": True, "task_id": task_id, "pending_approvals": 1,
                "status": "AWAITING_REAL_TESTS", "hq": exported, "summary": office.snapshot()}
    finally:
        office.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vault", type=Path, required=True)
    p.add_argument("--db", type=Path,
                   help="optional persistent demonstration DB; must never be real production data")
    args = p.parse_args()
    if args.db is not None:
        result = simulate(args.db, args.vault)
    else:
        with tempfile.TemporaryDirectory() as d:
            result = simulate(Path(d) / "simulated-company.sqlite3", args.vault)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
