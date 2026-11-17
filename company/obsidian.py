"""Export Serenity's operational ledger into an Obsidian-compatible Markdown vault.

Generated-only files. Never modifies user-authored notes or external systems.
"""
import html
import json
import re
from pathlib import Path

from company.office import DEPARTMENTS, AGENTS


def md(value):
    text = html.escape(str(value), quote=False)
    for char in ("\\", "[", "]", "|", "*", "_", "`", "#", "!", "<", ">"):
        text = text.replace(char, "\\" + char)
    return text.replace("\r", " ").replace("\n", " ")


def _safe_write(directory, name, content):
    path = directory / name
    if path.is_symlink():
        raise ValueError("refusing to overwrite a symlink")
    if path.exists() and not path.is_file():
        raise ValueError("refusing to overwrite a non-file")
    path.write_text(content, encoding="utf-8")
    return path


def export_vault(office, base_directory):
    """Create an isolated generated HQ directory; no external API calls."""
    base = Path(base_directory).expanduser()
    if base.is_symlink():
        raise ValueError("refusing symbolic-link vault root")
    base.mkdir(parents=True, exist_ok=True)
    out = base / "Serenity HQ"
    if out.is_symlink():
        raise ValueError("refusing symbolic-link HQ output")
    out.mkdir(exist_ok=True)
    for folder in ("Departments", "Agents", "Tasks", "Messages"):
        sub = out / folder
        if sub.is_symlink():
            raise ValueError("refusing symbolic-link department directory")
        sub.mkdir(exist_ok=True)
    tasks = office.rows("tasks")
    messages = office.rows("messages")
    approvals = office.rows("approvals")
    events = office.rows("events")
    quota = office.rows("quota_snapshots")
    snapshot = office.snapshot()
    summary = [
        "# Serenity HQ — Command Centre",
        "",
        "> Generated from the local company ledger. Not a live agent dashboard.",
        "> Agent execution is disabled. No external writes, model calls or deployments.",
        "",
        "## Organization",
        "",
        f"- Departments: {snapshot['departments']}",
        f"- Organizational agent roles: {snapshot['role_profiles']} (none running)",
        f"- Pending owner approvals: {snapshot['pending_approvals']}",
        f"- Unacknowledged handoff messages: {snapshot['unacknowledged_messages']}",
        "",
        "## Department Directory",
        "",
    ]
    for slug, name in DEPARTMENTS.items():
        count = sum(t["department"] == slug for t in tasks)
        summary.append(f"- [[Departments/{slug}|{md(name)}]] — {count} tasks")
        dept_tasks = [t for t in tasks if t["department"] == slug]
        detail = [f"# {md(name)}", "", f"Tasks: **{len(dept_tasks)}**", ""]
        for task in dept_tasks:
            detail.append(f"- [[../Tasks/task-{task['id']}|#{task['id']} {md(task['title'])}]] — {task['state']}")
        if not dept_tasks:
            detail.append("_No tasks assigned._")
        _safe_write(out / "Departments", slug + ".md", "\n".join(detail) + "\n")
    summary.extend(["", "## Current Tasks", ""])
    for task in tasks:
        summary.append(f"- [[Tasks/task-{task['id']}|#{task['id']} {md(task['title'])}]] — {task['state']} / {task['department']}")
        related_messages = [m for m in messages if m["task_id"] == task["id"]]
        lines = [
            f"# Task #{task['id']}: {md(task['title'])}", "",
            f"- Department: [[../Departments/{task['department']}]]",
            f"- State: **{task['state']}**",
            f"- Risk: **{task['risk']}**",
            f"- Assigned role: {md(task['assigned_agent'] or 'unassigned')}",
            f"- Branch: {md(task['branch'] or 'none')}", "",
            "## Acceptance Criteria", "", md(task["acceptance"]), "",
            "## Checkpoint", "", md(task["checkpoint"] or "No checkpoint recorded"), "",
            "## Handoffs", "",
        ]
        for message in related_messages:
            lines.append(f"- {md(message['sender'])} → {md(message['recipient'])}: {md(message['body'])} ({'acknowledged' if message['acknowledged'] else 'unacknowledged'})")
        if not related_messages:
            lines.append("_None._")
        _safe_write(out / "Tasks", f"task-{task['id']}.md", "\n".join(lines) + "\n")
    if not tasks:
        summary.append("_No tasks have been created. This is not an active workforce._")
    summary.extend(["", "## Owner Approval Queue", ""])
    for approval in approvals:
        if approval["state"] == "PENDING":
            summary.append(f"- Approval #{approval['id']} — **{md(approval['action'])}**, task #{approval['task_id']}: {md(approval['explanation'])}")
    if snapshot["pending_approvals"] == 0:
        summary.append("_No pending owner approvals._")
    summary.extend(["", "## Latest Operations Events", ""])
    for event in events[-15:]:
        summary.append(f"- {md(event['created_at'])} — {md(event['event_type'])} / {md(event['actor'])}: {md(event['detail'])}")
    if not events:
        summary.append("_No activity yet._")
    summary.extend(["", "## Observed Quotas", ""])
    for q in quota[-10:]:
        summary.append(f"- {md(q['model'])}: {md(q['state'])} ({md(q['source'])}); status is advisory")
    if not quota:
        summary.append("_No verified provider usage has been connected._")
    _safe_write(out, "Command Centre.md", "\n".join(summary) + "\n")
    _safe_write(out, "Owner Approvals.md",
                "# Owner Approvals\n\n" + "\n".join(
                    f"- #{a['id']}: {md(a['action'])} / task #{a['task_id']} — {md(a['state'])}: {md(a['explanation'])}"
                    for a in approvals) + "\n")
    roles = ["# Agent Directory", "", "Agent profiles are responsibilities, not running paid model instances.", ""]
    for slug, (dept, title, model) in AGENTS.items():
        roles.append(f"- [[Agents/{slug}|{md(title)}]] — {md(dept)}")
        _safe_write(out / "Agents", slug + ".md",
                    f"# {md(title)}\n\n- Department: [[../Departments/{dept}]]\n"
                    f"- Model / tool: {md(model)}\n- Execution: **DISABLED**\n"
                    "- Permissions: observe, plan, propose only until explicitly approved.\n")
    _safe_write(out, "Agent Directory.md", "\n".join(roles) + "\n")
    _safe_write(out, "Shift Handoffs.md",
                "# Shift Handoffs\n\n" + "\n".join(
                    f"- {md(e['created_at'])} — {md(e['detail'])}"
                    for e in events if e["event_type"] == "shift_checkpoint") + "\n")
    _safe_write(out, "Company Events.md",
                "# Company Events\n\n" + "\n".join(
                    f"- {md(e['created_at'])} — {md(e['event_type'])}: {md(e['detail'])}"
                    for e in events) + "\n")

    # Native Obsidian Canvas with linked department notes; all references
    # point inside the generated HQ subtree.
    nodes = [{"id": "executive", "type": "file", "file": "Serenity HQ/Departments/executive.md",
              "x": 250, "y": 0, "width": 300, "height": 190}]
    edges = []
    members = [slug for slug in DEPARTMENTS if slug != "executive"]
    for i, slug in enumerate(members):
        nodes.append({
            "id": slug, "type": "file", "file": f"Serenity HQ/Departments/{slug}.md",
            "x": 25 + (i % 3) * 370, "y": 300 + (i // 3) * 260,
            "width": 300, "height": 185,
        })
        edges.append({"id": "exec-" + slug, "fromNode": "executive", "toNode": slug})
    canvas = {"nodes": nodes, "edges": edges}
    _safe_write(base, "Serenity Company.canvas", json.dumps(canvas, indent=2) + "\n")
    return {"output_directory": str(out), "department_pages": len(DEPARTMENTS),
            "task_pages": len(tasks), "agent_pages": len(AGENTS), "canvas": str(base / "Serenity Company.canvas")}
