#!/usr/bin/env python3
"""Local Serenity company operating-system command interface. No cloud calls."""
import argparse
import importlib.util
import json
from pathlib import Path
from company.office import CompanyOffice
from company.obsidian import export_vault
from company.manager import propose_work
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "backend" / "data" / "serenity_company.sqlite3"


def quota_assessment(snapshot_path):
    module_file = ROOT / "tools" / "quota_guard.py"
    spec = importlib.util.spec_from_file_location("quota_guard", module_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    payload = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    return mod.assess(payload), payload


def build_parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DEFAULT_DB,
                   help="SQLite ledger; default is ignored backend/data directory")
    s = p.add_subparsers(dest="command", required=True)

    s.add_parser("init", help="initialize roles, departments and empty database")
    s.add_parser("status", help="current operational status, not live model telemetry")
    for name in ("tasks", "agents", "departments", "events", "messages", "approvals", "quota_snapshots", "manager_quality_checks"):
        s.add_parser(name, help="read ledger rows for " + name)

    a = s.add_parser("new", help="create an unapproved task proposal")
    a.add_argument("title")
    a.add_argument("--department", choices=(
        "executive", "engineering", "qa", "research", "architecture", "operations", "platform"), required=True)
    a.add_argument("--acceptance", required=True)
    a.add_argument("--risk", choices=("low", "medium", "high"), default="low")

    a = s.add_parser("advance", help="advance a task state; never starts external agents")
    a.add_argument("id", type=int)
    a.add_argument("state")
    a.add_argument("--note", required=True)

    a = s.add_parser("assign", help="assign an organizational role, not an API invocation")
    a.add_argument("id", type=int)
    a.add_argument("agent")

    a = s.add_parser("checkpoint", help="record task checkpoint for a future shift")
    a.add_argument("id", type=int)
    a.add_argument("--note", required=True)
    a.add_argument("--branch", default="")

    a = s.add_parser("send", help="queue a persistent message between agent roles")
    a.add_argument("id", type=int)
    a.add_argument("--from-role", required=True)
    a.add_argument("--to-role", required=True)
    a.add_argument("--message", required=True)

    a = s.add_parser("ack", help="acknowledge a queued role message")
    a.add_argument("id", type=int)
    a.add_argument("--recipient", required=True)

    a = s.add_parser("request-approval", help="request explicit owner decision")
    a.add_argument("id", type=int)
    a.add_argument("--action", required=True)
    a.add_argument("--reason", required=True)

    a = s.add_parser("decide", help="record owner's decision only; never performs external action")
    a.add_argument("id", type=int)
    a.add_argument("--decision", choices=("APPROVED", "REJECTED"), required=True)
    a.add_argument("--note", required=True)
    a.add_argument("--confirm-owner", action="store_true")

    a = s.add_parser("shift", help="record an organizational shift checkpoint")
    a.add_argument("name", choices=("shift_1_start", "shift_1_end_shift_2_start", "shift_2_end"))
    a.add_argument("--note", required=True)

    a = s.add_parser("quota-import", help="store an offline advisory quota assessment")
    a.add_argument("file", type=Path)

    a = s.add_parser("manager-gate", help="record advisory QA/CI policy decision, never commit code")
    a.add_argument("id", type=int)
    a.add_argument("--evidence", type=Path, required=True,
                   help="local JSON summary; cannot prove its own CI claims")

    a = s.add_parser("plan", help="dry-run Chief of Staff task selection; no model calls")
    a.add_argument("--quota-snapshot", type=Path, help="offline JSON quota snapshot to assess")
    a.add_argument("--now", help="time-aware ISO-8601 timestamp for dry-run testing")

    a = s.add_parser("export", help="render safe generated Markdown/Canvas inside an Obsidian vault")
    a.add_argument("--vault", type=Path, required=True)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    office = CompanyOffice(args.db)
    try:
        c = args.command
        if c == "init":
            answer = office.snapshot()
        elif c == "status":
            answer = office.snapshot()
        elif c in ("tasks", "agents", "departments", "events", "messages", "approvals", "quota_snapshots", "manager_quality_checks"):
            answer = office.rows(c)
        elif c == "new":
            answer = {"task_id": office.new_task(args.title, args.department, args.acceptance, args.risk)}
        elif c == "advance":
            office.transition(args.id, args.state, args.note)
            answer = {"task_id": args.id, "state": args.state}
        elif c == "assign":
            office.assign(args.id, args.agent)
            answer = {"task_id": args.id, "agent": args.agent}
        elif c == "checkpoint":
            office.checkpoint(args.id, args.note, args.branch)
            answer = {"task_id": args.id, "checkpoint_saved": True}
        elif c == "send":
            answer = {"message_id": office.send_message(args.id, args.from_role, args.to_role, args.message)}
        elif c == "ack":
            office.acknowledge(args.id, args.recipient)
            answer = {"message_id": args.id, "acknowledged": True}
        elif c == "request-approval":
            answer = {"approval_id": office.request_approval(args.id, args.action, args.reason)}
        elif c == "decide":
            office.decide_approval(args.id, args.decision, args.note, args.confirm_owner)
            answer = {"approval_id": args.id, "recorded": args.decision, "executed_action": False}
        elif c == "shift":
            office.shift_checkpoint(args.name, args.note)
            answer = {"shift_checkpoint": args.name, "agent_execution": False}
        elif c == "quota-import":
            result, snapshot = quota_assessment(args.file)
            office.record_quota_state(result, snapshot.get("source", "unverified"),
                                      snapshot.get("observed_at", "unknown"))
            answer = result
        elif c == "manager-gate":
            if args.evidence.stat().st_size > 16000:
                raise ValueError("quality evidence too large")
            record = json.loads(args.evidence.read_text(encoding="utf-8"))
            answer = office.evaluate_manager_gate(args.id, record)
        elif c == "plan":
            now = (datetime.fromisoformat(args.now.replace("Z", "+00:00"))
                   if args.now else datetime.now(timezone.utc))
            quotas = {}
            if args.quota_snapshot:
                result, _ = quota_assessment(args.quota_snapshot)
                if result["model"]:
                    quotas[result["model"]] = result
            answer = propose_work(office, quotas, now=now)
        elif c == "export":
            answer = export_vault(office, args.vault)
        else:
            raise ValueError("unknown command")
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit("BLOCKED: " + str(exc)) from None
    finally:
        office.close()
    print(json.dumps(answer, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
