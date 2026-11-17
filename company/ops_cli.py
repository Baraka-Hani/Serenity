"""Offline operations CLI (serenity-ops, run with `python3 -m company.ops_cli`) for Serenity operations and verification.

Allows offline inspection of company state, quota tracking, shift simulation,
Obsidian HQ export, and governance gate verification without network access.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from company.event_bus import EventBus
from company.governance_validator import GovernanceValidator, sha256_digest
from company.obsidian_exporter import ObsidianExporter
from company.quota_ledger import DEFAULT_DAILY_TOKEN_BUDGET, QuotaLedger
from company.shift_runner import ShiftRunner


def cmd_status(ledger: QuotaLedger, event_bus: EventBus, args: argparse.Namespace) -> int:
    """Print high-level company status overview."""
    now = datetime.now(timezone.utc)
    shift_info = ShiftRunner.determine_shift(now)
    usage = ledger.get_window_usage("qwen/qwen3.8-27b", now=now)
    status = ledger.evaluate_status("qwen/qwen3.8-27b", now=now)
    events_count = event_bus.count()
    intact, msg = event_bus.verify_chain_integrity()

    print("=" * 60)
    print("           SERENITY AI COMPANY — OPERATING STATUS           ")
    print("=" * 60)
    print(f"Timestamp:          {now.isoformat()}")
    print(f"Active Shift:       {shift_info['name']}")
    print(f"Builder Model:      qwen/qwen3.8-27b (Groq Free)")
    print(f"Quota Status:       {status['status']}")
    print(f"Daily Tokens:       {usage['tokens_consumed']:,} / {DEFAULT_DAILY_TOKEN_BUDGET:,} ({usage['used_percent']}%)")
    print(f"Remaining Tokens:   {usage['remaining_tokens']:,}")
    print(f"Total Audit Events: {events_count} (Chain: {'INTACT' if intact else 'CORRUPT'})")
    print(f"Total Financial:    $0.00 (Zero-Spend Policy Active)")
    print("=" * 60)
    return 0


def cmd_quota(ledger: QuotaLedger, args: argparse.Namespace) -> int:
    """Display detailed quota consumption and wind-down assessment."""
    model = args.model
    now = datetime.now(timezone.utc)
    usage = ledger.get_window_usage(model, now=now)
    status = ledger.evaluate_status(model, now=now)

    print(f"Quota Telemetry for Model: {model}")
    print("-" * 50)
    print(f"Status:             {status['status']}")
    print(f"Tokens Consumed:    {usage['tokens_consumed']:,} / {DEFAULT_DAILY_TOKEN_BUDGET:,}")
    print(f"Used Percentage:    {usage['used_percent']}%")
    print(f"Remaining:          {usage['remaining_tokens']:,} tokens")
    print(f"Requests Count:     {usage['requests_count']}")
    print(f"Accept New Work:    {status['accept_new_work']}")
    print(f"Finish Only:        {status['finish_only']}")
    print(f"Reason:             {status['reason']}")
    return 0


def cmd_simulate_shift(ledger: QuotaLedger, event_bus: EventBus, args: argparse.Namespace) -> int:
    """Simulate a deterministic 5-hour shift execution."""
    shift_num = args.shift
    tasks_count = args.tasks
    model = args.model

    tasks = [
        {
            "task_id": f"TASK-SIM-{i+1:03d}",
            "title": f"Simulated low-risk task #{i+1}",
            "estimated_tokens": 2_000,
        }
        for i in range(tasks_count)
    ]

    event_bus.publish(
        "SHIFT_SIMULATION_STARTED", "operations", "operations-director",
        {"shift": shift_num, "task_count": tasks_count, "model": model}
    )

    runner = ShiftRunner(ledger)
    result = runner.simulate_shift(shift_num, tasks, model=model)

    event_bus.publish(
        "SHIFT_SIMULATION_COMPLETED", "operations", "operations-director",
        {"shift": shift_num, "completed": len(result["completed_tasks"]), "paused": len(result["paused_tasks"])}
    )

    print(result["handoff_report"])
    return 0


def cmd_export_hq(ledger: QuotaLedger, event_bus: EventBus, args: argparse.Namespace) -> int:
    """Export Obsidian HQ vault and canvas to target directory."""
    out_dir = Path(args.output).resolve()
    exporter = ObsidianExporter(ledger, event_bus)
    result = exporter.export_vault(out_dir)

    print(f"Successfully exported Serenity HQ:")
    print(f"- Output Directory: {result['output_directory']}")
    print(f"- Department Pages: {result['department_pages']}")
    print(f"- Agent Pages:      {result['agent_pages']}")
    print(f"- Operations Pages: {result['operations_pages']}")
    print(f"- Visual Canvas:    {result['canvas_path']}")
    return 0


def cmd_verify_gates(args: argparse.Namespace) -> int:
    """Run GovernanceValidator on a known fixture to test all 5 gates."""
    validator = GovernanceValidator()
    orig = b"function test() { return 1; }\n"
    cand = b"function test() { return 2; }\n"
    orig_sha = sha256_digest(orig)
    cand_sha = sha256_digest(cand)
    head_sha = "abcdef1234567890abcdef1234567890abcdef12"

    task = {
        "issue": 22,
        "risk": "low",
        "target_path": "backend/test_destination_picker.js",
        "original_sha256": orig_sha,
        "candidate_sha256": cand_sha,
    }
    ci = {
        "head_sha": head_sha,
        "checks": {
            "backend-and-browser-logic": {"conclusion": "success"},
            "react-prototype": {"conclusion": "success"},
            "module5-privacy-and-architecture": {"conclusion": "success"},
        },
    }
    builder = {"agent_id": "lead-builder", "model": "qwen/qwen3.8-27b"}
    reviewer = {"agent_id": "qa-director", "model": "openai/gpt-oss-120b", "verdict": "approve"}

    res = validator.assess(
        task=task, original_bytes=orig, candidate_bytes=cand,
        ci_evidence=ci, builder_info=builder, reviewer_info=reviewer,
        head_sha=head_sha
    )

    print("Governance Quality Gate Evaluation:")
    print("-" * 50)
    print(f"All Gates Passed:       {res['all_quality_gates_passed']}")
    print(f"Passed Gates:           {', '.join(res['passed_gates'])}")
    print(f"Failed Gates:           {', '.join(res['failed_gates']) or 'None'}")
    print(f"Recommendation:         {res['recommendation']}")
    print(f"Manager Authorized:     {res['manager_commit_execution_authorized']} (Strictly False)")
    return 0 if res["all_quality_gates_passed"] else 1


def cmd_verify_events(event_bus: EventBus, args: argparse.Namespace) -> int:
    """Verify cryptographic integrity of event journal."""
    intact, msg = event_bus.verify_chain_integrity()
    print(f"Event Chain Integrity: {'VALID' if intact else 'COMPROMISED'}")
    print(f"Details: {msg}")
    return 0 if intact else 1


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="serenity-ops",
        description="Serenity AI Company offline operations and verification CLI.",
    )
    parser.add_argument("--db", default=":memory:", help="SQLite database path for ledger/events")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Show current operational status overview")

    # quota
    p_quota = subparsers.add_parser("quota", help="Display quota telemetry")
    p_quota.add_argument("--model", default="qwen/qwen3.8-27b", help="Model identifier")

    # simulate-shift
    p_shift = subparsers.add_parser("simulate-shift", help="Simulate a 5-hour shift execution")
    p_shift.add_argument("--shift", type=int, choices=[1, 2], default=1, help="Shift number (1 or 2)")
    p_shift.add_argument("--tasks", type=int, default=3, help="Number of simulated tasks")
    p_shift.add_argument("--model", default="qwen/qwen3.8-27b", help="Model identifier")

    # export-hq
    p_hq = subparsers.add_parser("export-hq", help="Export Obsidian HQ notes and Canvas")
    p_hq.add_argument("--output", default=".", help="Target directory for Serenity HQ")

    # verify-gates
    subparsers.add_parser("verify-gates", help="Test 5-gate quality decision engine on fixture")

    # verify-events
    subparsers.add_parser("verify-events", help="Verify event journal hash-chain integrity")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    ledger = QuotaLedger(args.db)
    event_bus = EventBus(args.db)

    try:
        if args.command == "status":
            return cmd_status(ledger, event_bus, args)
        elif args.command == "quota":
            return cmd_quota(ledger, args)
        elif args.command == "simulate-shift":
            return cmd_simulate_shift(ledger, event_bus, args)
        elif args.command == "export-hq":
            return cmd_export_hq(ledger, event_bus, args)
        elif args.command == "verify-gates":
            return cmd_verify_gates(args)
        elif args.command == "verify-events":
            return cmd_verify_events(event_bus, args)
        else:
            parser.print_help()
            return 1
    finally:
        ledger.close()
        event_bus.close()


if __name__ == "__main__":
    sys.exit(main())
