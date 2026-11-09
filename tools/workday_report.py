#!/usr/bin/env python3
"""Render a deterministic, read-only Markdown report from Serenity task JSON."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path


FIELDS = (
    "task",
    "model",
    "agent_role",
    "contribution",
    "status",
    "verification",
    "cost",
    "blocker",
    "owner_decision",
)
OPTIONAL_FIELDS = {"blocker", "owner_decision"}


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("date"), str):
        raise ValueError("report requires a string date")
    data["date"] = " ".join(data["date"].split())
    try:
        parsed_date = date.fromisoformat(data["date"])
    except ValueError:
        raise ValueError("report date must use YYYY-MM-DD") from None
    if parsed_date.isoformat() != data["date"]:
        raise ValueError("report date must use YYYY-MM-DD")
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("report requires a tasks list")
    for index, task in enumerate(tasks, 1):
        if not isinstance(task, dict):
            raise ValueError(f"task {index} must be an object")
        missing = [field for field in FIELDS if field not in task]
        if missing:
            raise ValueError(f"task {index} missing: {', '.join(missing)}")
        if any(not isinstance(task[field], str) for field in FIELDS):
            raise ValueError(f"task {index} fields must be strings")
        for field in FIELDS:
            task[field] = " ".join(task[field].split())
            if field not in OPTIONAL_FIELDS and not task[field]:
                raise ValueError(f"task {index} {field} cannot be blank")
    return data


def render(data):
    lines = [f"# Serenity workday report — {data['date']}", ""]
    if not data["tasks"]:
        return "\n".join(lines + ["No tasks recorded.", ""])

    for index, task in enumerate(data["tasks"], 1):
        lines.extend([
            f"## {index}. {task['task']}",
            "",
            f"- **Model:** {task['model']}",
            f"- **Agent role:** {task['agent_role']}",
            f"- **Contribution:** {task['contribution']}",
            f"- **Status:** {task['status']}",
            f"- **Verification:** {task['verification']}",
            f"- **Cost:** {task['cost']}",
            f"- **Blocker:** {task['blocker'] or 'None'}",
            f"- **Owner decision:** {task['owner_decision'] or 'None'}",
            "",
        ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON task report input")
    args = parser.parse_args(argv)
    try:
        data = validate(json.loads(args.input.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(render(data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
