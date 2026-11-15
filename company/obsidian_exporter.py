"""Export Serenity operational control plane and audit journal to an Obsidian vault.

Generates structured Markdown notes and an interactive visual Canvas representation
under 'Serenity HQ/'. Completely offline, zero network, zero external API writes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from company.event_bus import EventBus
from company.quota_ledger import DEFAULT_DAILY_TOKEN_BUDGET, QuotaLedger

DEPARTMENTS = {
    "executive": ("Executive Office", "Strategic backlog, financial inbox, owner authorizations"),
    "engineering": ("Engineering", "Lead Builder, isolated worktrees, bounded diff implementation"),
    "qa": ("Quality Assurance", "QA Director, independent reviewer critique, regression checks"),
    "research": ("Research and Product", "User discovery, competitive analysis, 80/20 opportunity split"),
    "architecture": ("Architecture", "Chief Architect, system boundaries, data contracts"),
    "operations": ("Operations", "Operations Director, quota governor, shift coordinator, incident logs"),
    "platform": ("AI Platform", "Model adapters, offline test harnesses, sandbox runner"),
}

AGENTS = {
    "chief-of-staff": ("executive", "Manager", "Deterministic Workflow / Owner"),
    "lead-builder": ("engineering", "Builder", "qwen/qwen3.8-27b (Groq Free)"),
    "qa-director": ("qa", "Reviewer", "openai/gpt-oss-120b (Groq Free)"),
    "chief-architect": ("architecture", "Architect", "Human-Guided ChatGPT / Gemini"),
    "operations-director": ("operations", "Coordinator", "Deterministic Two-Shift Workflow"),
}


def safe_write_file(directory: Path, filename: str, content: str) -> Path:
    """Safely write text content to a file, strictly rejecting symlinks."""
    target = directory / filename
    if target.is_symlink():
        raise ValueError(f"Refusing to write through symbolic link: {target}")
    if target.exists() and not target.is_file():
        raise ValueError(f"Target path exists but is not a regular file: {target}")
    target.write_text(content, encoding="utf-8")
    return target


class ObsidianExporter:
    """Exports company ledger, quotas, and audit events to an Obsidian vault."""

    def __init__(self, ledger: QuotaLedger, event_bus: Optional[EventBus] = None):
        self.ledger = ledger
        self.event_bus = event_bus

    def export_vault(self, base_directory: str | Path) -> Dict[str, Any]:
        """Generate full 'Serenity HQ/' directory structure and notes."""
        raw_path = Path(base_directory).expanduser()
        if raw_path.is_symlink():
            raise ValueError("Refusing symbolic-link vault root directory")
        base_path = raw_path.resolve()
        if base_path.is_symlink():
            raise ValueError("Refusing symbolic-link vault root directory")

        hq_dir = base_path / "Serenity HQ"
        if hq_dir.is_symlink():
            raise ValueError("Refusing symbolic-link HQ output directory")
        hq_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        subdirs = ["Departments", "Agents", "Operations", "Tasks"]
        for sub in subdirs:
            p = hq_dir / sub
            if p.is_symlink():
                raise ValueError(f"Refusing symbolic-link subdirectory: {p}")
            p.mkdir(exist_ok=True)

        dept_count = self._export_departments(hq_dir / "Departments")
        agent_count = self._export_agents(hq_dir / "Agents")
        ops_count = self._export_operations(hq_dir / "Operations")
        self._export_command_centre(hq_dir)
        canvas_path = self._export_canvas(hq_dir)

        return {
            "output_directory": str(hq_dir),
            "department_pages": dept_count,
            "agent_pages": agent_count,
            "operations_pages": ops_count,
            "canvas_path": str(canvas_path),
        }

    def _export_command_centre(self, hq_dir: Path) -> Path:
        """Generate root 'Command Centre.md' dashboard note."""
        usage_builder = self.ledger.get_window_usage("qwen/qwen3.8-27b")
        status_builder = self.ledger.evaluate_status("qwen/qwen3.8-27b")
        events_count = self.event_bus.count() if self.event_bus else 0

        content = [
            "# Serenity HQ — Command Centre",
            "",
            "> **Operating Mode:** Supervised AI Workforce Control Plane",
            "> **Cost Policy:** Strict Zero New Spend ($0.00)",
            "> **Autonomous Execution:** Disabled (Fail-Closed)",
            "",
            "## 1. Real-Time Status & Token Meters",
            "",
            f"- **Lead Builder (`qwen/qwen3.8-27b`):** `{status_builder['status']}` ({usage_builder['tokens_consumed']:,} / {DEFAULT_DAILY_TOKEN_BUDGET:,} tokens, {usage_builder['used_percent']}%)",
            f"- **Remaining Allowance:** {usage_builder['remaining_tokens']:,} tokens",
            f"- **Recorded Audit Events:** {events_count} events",
            "- **Total Financial Incurred:** $0.00",
            "",
            "## 2. Operating Departments",
            "",
        ]

        for dept_key, (name, mission) in DEPARTMENTS.items():
            content.append(f"- **[[Departments/{name}|{name}]]:** {mission}")

        content.extend([
            "",
            "## 3. Operations & Auditing",
            "",
            "- [[Operations/Quota Telemetry|Quota Telemetry & Rate Limits]]",
            "- [[Operations/Shift Handoffs|Daily Two-Shift Handoffs]]",
            "- [[Operations/Event Journal|Cryptographic Audit Journal]]",
            "- [[Serenity Company.canvas|Visual Spatial Map (Canvas)]]",
            "",
            "---",
            "*Generated deterministically from Serenity operational ledger.*",
        ])

        return safe_write_file(hq_dir, "Command Centre.md", "\n".join(content))

    def _export_departments(self, dept_dir: Path) -> int:
        """Generate one note per department."""
        count = 0
        for dept_key, (name, mission) in DEPARTMENTS.items():
            content = [
                f"# Department: {name}",
                "",
                f"**Department Key:** `{dept_key}`",
                f"**Mission:** {mission}",
                "",
                "## Assigned Agents",
                "",
            ]
            for agent_id, (d_key, role, model) in AGENTS.items():
                if d_key == dept_key:
                    content.append(f"- **[[Agents/{agent_id.replace('-', ' ').title()}|{agent_id}]]:** {role} ({model})")

            content.extend([
                "",
                "## Standard Operating Procedures",
                "",
                "- All code outputs require deterministic automated tests.",
                "- Reviewer role must be independent from Builder role.",
                "- Any proposed spending or credential request halts immediately.",
                "",
                "[[Command Centre|← Back to Command Centre]]",
            ])
            safe_write_file(dept_dir, f"{name}.md", "\n".join(content))
            count += 1
        return count

    def _export_agents(self, agent_dir: Path) -> int:
        """Generate one note per registered agent."""
        count = 0
        for agent_id, (dept_key, role, model) in AGENTS.items():
            name = agent_id.replace("-", " ").title()
            dept_name = DEPARTMENTS.get(dept_key, (dept_key, ""))[0]
            content = [
                f"# Agent: {name}",
                "",
                f"**Agent ID:** `{agent_id}`",
                f"**Role:** {role}",
                f"**Department:** [[Departments/{dept_name}|{dept_name}]]",
                f"**Assigned Engine / Model:** `{model}`",
                "",
                "## Authority Boundaries",
                "",
                "- May operate only within isolated worktrees.",
                "- Cannot authorize branch commits or pull request merges.",
                "- Subject to the 90% quota wind-down policy.",
                "",
                "[[Command Centre|← Back to Command Centre]]",
            ]
            safe_write_file(agent_dir, f"{name}.md", "\n".join(content))
            count += 1
        return count

    def _export_operations(self, ops_dir: Path) -> int:
        """Generate operational dashboard notes."""
        usage = self.ledger.get_window_usage("qwen/qwen3.8-27b")
        status = self.ledger.evaluate_status("qwen/qwen3.8-27b")

        # Quota Telemetry Note
        quota_content = [
            "# Operations: Quota Telemetry & Rate Limits",
            "",
            f"**Observed Model:** `qwen/qwen3.8-27b`",
            f"**Operating Status:** `{status['status']}`",
            f"**Tokens Consumed:** {usage['tokens_consumed']:,} / {DEFAULT_DAILY_TOKEN_BUDGET:,} ({usage['used_percent']}%)",
            f"**Remaining Budget:** {usage['remaining_tokens']:,} tokens",
            f"**Requests In Window:** {usage['requests_count']}",
            f"**Financial Spend:** $0.00",
            "",
            "## Rate Limit State Machine",
            "",
            "- `< 90% (0 – 53,999 tokens):` **READY** (Admitting approved low-risk tasks)",
            "- `≥ 90% (54,000 – 59,999 tokens):` **WIND_DOWN** (Finish-only, 25% safety margin)",
            "- `100% (60,000 tokens):` **EXHAUSTED** (Immediate halt, atomic checkpoint)",
            "",
            "[[Command Centre|← Back to Command Centre]]",
        ]
        safe_write_file(ops_dir, "Quota Telemetry.md", "\n".join(quota_content))

        # Shift Handoffs Note
        shift_content = [
            "# Operations: Daily Two-Shift Handoffs",
            "",
            "- **Shift 1:** 09:00 – 14:00 America/Moncton",
            "- **Shift 2:** 14:00 – 19:00 America/Moncton",
            "- **Off-Shift:** 19:00 – 09:00 (Standby)",
            "",
            "## Handoff Policy",
            "",
            "Shift boundaries are organizational handoffs, **not** provider quota resets.",
            "Resumption in Shift 2 requires verified quota capacity.",
            "",
            "[[Command Centre|← Back to Command Centre]]",
        ]
        safe_write_file(ops_dir, "Shift Handoffs.md", "\n".join(shift_content))

        # Event Journal Note
        journal_content = [
            "# Operations: Cryptographic Event Journal",
            "",
        ]
        if self.event_bus:
            intact, msg = self.event_bus.verify_chain_integrity()
            badge = "✅ CHAIN INTACT" if intact else "❌ CHAIN BROKEN"
            journal_content.extend([
                f"**Integrity Status:** {badge}",
                f"**Verification:** {msg}",
                f"**Total Events:** {self.event_bus.count()}",
                "",
                "## Recent Events",
                "",
            ])
            for ev in self.event_bus.get_events(limit=25):
                journal_content.append(
                    f"- `{ev['timestamp']}` — **{ev['event_type']}** ({ev['department']}/{ev['agent_id']}): "
                    f"`{ev['event_hash'][:8]}...`"
                )
        else:
            journal_content.append("- *(No active event bus attached)*")

        journal_content.extend([
            "",
            "[[Command Centre|← Back to Command Centre]]",
        ])
        safe_write_file(ops_dir, "Event Journal.md", "\n".join(journal_content))

        return 3

    def _export_canvas(self, hq_dir: Path) -> Path:
        """Generate 'Serenity Company.canvas' visual graph."""
        nodes = [
            {
                "id": "node_command",
                "x": 0, "y": 0, "width": 320, "height": 180,
                "type": "text",
                "text": "## 🏛️ Executive Office\n- Strategy & Approvals\n- Owner Authority Gate\n- Zero-Spend Enforcer",
            },
            {
                "id": "node_research",
                "x": -360, "y": 0, "width": 300, "height": 160,
                "type": "text",
                "text": "## 🔍 Research & Product\n- 80% Travel App Discovery\n- 20% Tooling Improvement\n- Customer Pain Points",
            },
            {
                "id": "node_arch",
                "x": 0, "y": 240, "width": 320, "height": 160,
                "type": "text",
                "text": "## 📐 Architecture\n- System Boundaries\n- Python PWA vs React Proto\n- Interface Contracts",
            },
            {
                "id": "node_eng",
                "x": -360, "y": 240, "width": 300, "height": 160,
                "type": "text",
                "text": "## ⚙️ Engineering\n- Lead Builder\n- `qwen/qwen3.8-27b`\n- Bounded Unit Tests",
            },
            {
                "id": "node_qa",
                "x": 380, "y": 240, "width": 300, "height": 160,
                "type": "text",
                "text": "## 🛡️ Quality Assurance\n- QA Director\n- `openai/gpt-oss-120b`\n- Independent Critique",
            },
            {
                "id": "node_ops",
                "x": 0, "y": 460, "width": 320, "height": 160,
                "type": "text",
                "text": "## ⏱️ Operations\n- Two 5-Hour Daily Shifts\n- 60k Token Budget Meter\n- 90% Wind-Down Checkpoint",
            },
            {
                "id": "node_platform",
                "x": 380, "y": 460, "width": 300, "height": 160,
                "type": "text",
                "text": "## 🧪 AI Platform\n- Offline Test Harnesses\n- Container Sandbox Gates\n- Telemetry Parsers",
            },
        ]

        edges = [
            {"id": "e1", "fromNode": "node_command", "toNode": "node_research", "fromSide": "left", "toSide": "right"},
            {"id": "e2", "fromNode": "node_command", "toNode": "node_arch", "fromSide": "bottom", "toSide": "top"},
            {"id": "e3", "fromNode": "node_arch", "toNode": "node_eng", "fromSide": "left", "toSide": "right"},
            {"id": "e4", "fromNode": "node_arch", "toNode": "node_qa", "fromSide": "right", "toSide": "left"},
            {"id": "e5", "fromNode": "node_arch", "toNode": "node_ops", "fromSide": "bottom", "toSide": "top"},
            {"id": "e6", "fromNode": "node_ops", "toNode": "node_platform", "fromSide": "right", "toSide": "left"},
        ]

        canvas_data = {"nodes": nodes, "edges": edges}
        target = hq_dir / "Serenity Company.canvas"
        target.write_text(json.dumps(canvas_data, indent=2), encoding="utf-8")
        return target
