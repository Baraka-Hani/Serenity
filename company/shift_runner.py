"""Two-shift supervised operating runner and checkpoint coordinator.

Enforces two 5-hour daily operating windows (09:00–14:00 and 14:00–19:00 Moncton),
monitors 90% quota wind-down, manages bounded task completion, and generates
reproducible handoff checkpoints without incurring external financial spend.
"""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from company.quota_ledger import QuotaLedger

SHIFT_1_START = time(9, 0)   # 09:00
SHIFT_1_END = time(14, 0)    # 14:00 (Shift 1 Handoff)
SHIFT_2_START = time(14, 0)  # 14:00
SHIFT_2_END = time(19, 0)    # 19:00 (Shift 2 Closeout)


class ShiftError(ValueError):
    """Raised for invalid shift operations or timing."""


class ShiftRunner:
    """Coordinates two-shift execution, quota checks, and atomic handoffs."""

    def __init__(self, ledger: QuotaLedger):
        self.ledger = ledger

    @staticmethod
    def determine_shift(dt: datetime) -> Dict[str, Any]:
        """Determine which shift window a given datetime falls into."""
        if dt.tzinfo is None:
            raise ShiftError("Datetime must be timezone-aware")
        
        t = dt.time()
        if SHIFT_1_START <= t < SHIFT_1_END:
            return {
                "shift": 1,
                "name": "Shift 1 (Morning / Midday)",
                "active": True,
                "start_time": SHIFT_1_START.isoformat(),
                "end_time": SHIFT_1_END.isoformat(),
            }
        elif SHIFT_2_START <= t < SHIFT_2_END:
            return {
                "shift": 2,
                "name": "Shift 2 (Afternoon / Evening)",
                "active": True,
                "start_time": SHIFT_2_START.isoformat(),
                "end_time": SHIFT_2_END.isoformat(),
            }
        else:
            return {
                "shift": 0,
                "name": "Off-Shift Window (Overnight / Standby)",
                "active": False,
                "start_time": "19:00:00",
                "end_time": "09:00:00",
            }

    def simulate_shift(
        self,
        shift_number: int,
        tasks: List[Dict[str, Any]],
        *,
        model: str = "qwen/qwen3.8-27b",
        start_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Simulate execution of a 5-hour shift against the quota ledger.
        
        Processes tasks, monitors the 90% threshold, handles in-flight completion,
        and produces a checkpoint at the shift boundary.
        """
        if shift_number not in (1, 2):
            raise ShiftError("Shift number must be 1 or 2")

        # Base time anchor for simulation
        base_date = (start_time or datetime.now(timezone.utc)).date()
        shift_start_hour = 9 if shift_number == 1 else 14
        current_sim_time = datetime(
            base_date.year, base_date.month, base_date.day,
            shift_start_hour, 0, tzinfo=timezone.utc
        )
        shift_end_time = current_sim_time + timedelta(hours=5)

        completed_tasks: List[Dict[str, Any]] = []
        paused_tasks: List[Dict[str, Any]] = []
        events_log: List[Dict[str, Any]] = []
        state = "SHIFT_ACTIVE"

        for task in tasks:
            task_id = task.get("task_id", f"TASK-{len(completed_tasks) + 1:03d}")
            est_tokens = task.get("estimated_tokens", 2_500)
            
            # Evaluate quota status before admitting task
            status_eval = self.ledger.evaluate_status(
                model, now=current_sim_time, estimated_next_call_tokens=est_tokens
            )

            if status_eval["status"] == "EXHAUSTED":
                state = "EXHAUSTED"
                events_log.append({
                    "time": current_sim_time.isoformat(),
                    "event": "QUOTA_EXHAUSTED",
                    "task_id": task_id,
                    "details": status_eval["reason"],
                })
                paused_tasks.append({**task, "status": "BLOCKED_QUOTA_EXHAUSTED"})
                break

            elif status_eval["status"] == "WIND_DOWN":
                state = "SHIFT_WIND_DOWN"
                events_log.append({
                    "time": current_sim_time.isoformat(),
                    "event": "WIND_DOWN_TRIGGERED",
                    "task_id": task_id,
                    "details": status_eval["reason"],
                })

                # Can in-flight task be completed within the 25% safety margin?
                if status_eval.get("finish_allowed"):
                    # Execute bounded finish
                    prompt_toks = int(est_tokens * 0.7)
                    comp_toks = est_tokens - prompt_toks
                    self.ledger.record_usage(
                        model, prompt_toks, comp_toks,
                        task_id=task_id, timestamp=current_sim_time.isoformat()
                    )
                    completed_tasks.append({**task, "status": "COMPLETED_IN_WIND_DOWN"})
                    events_log.append({
                        "time": current_sim_time.isoformat(),
                        "event": "BOUNDED_FINISH_COMPLETED",
                        "task_id": task_id,
                        "tokens_consumed": est_tokens,
                    })
                else:
                    paused_tasks.append({**task, "status": "PAUSED_WIND_DOWN_EXCEEDED"})
                    events_log.append({
                        "time": current_sim_time.isoformat(),
                        "event": "TASK_PAUSED_SAFETY_MARGIN_EXCEEDED",
                        "task_id": task_id,
                    })
                # No new tasks admitted after entering wind-down
                break

            else:
                # READY: execute task normally
                prompt_toks = int(est_tokens * 0.7)
                comp_toks = est_tokens - prompt_toks
                self.ledger.record_usage(
                    model, prompt_toks, comp_toks,
                    task_id=task_id, timestamp=current_sim_time.isoformat()
                )
                completed_tasks.append({**task, "status": "COMPLETED"})
                events_log.append({
                    "time": current_sim_time.isoformat(),
                    "event": "TASK_COMPLETED",
                    "task_id": task_id,
                    "tokens_consumed": est_tokens,
                })
                # Advance simulated time by 20 minutes
                current_sim_time += timedelta(minutes=20)
                if current_sim_time >= shift_end_time:
                    events_log.append({
                        "time": current_sim_time.isoformat(),
                        "event": "SHIFT_BOUNDARY_REACHED",
                    })
                    break

        # Generate atomic checkpoint at shift conclusion
        checkpoint_id = f"CP-SHIFT-{shift_number}-{base_date.isoformat()}"
        checkpoint = self.ledger.create_checkpoint(
            checkpoint_id, model, now=shift_end_time,
            extra_state={
                "shift": shift_number,
                "completed_count": len(completed_tasks),
                "paused_count": len(paused_tasks),
            }
        )

        handoff_report = self.generate_handoff_report(
            shift_number=shift_number,
            model=model,
            completed_tasks=completed_tasks,
            paused_tasks=paused_tasks,
            events_log=events_log,
            checkpoint=checkpoint,
            timestamp=shift_end_time.isoformat(),
        )

        return {
            "shift_number": shift_number,
            "final_state": state,
            "completed_tasks": completed_tasks,
            "paused_tasks": paused_tasks,
            "events_log": events_log,
            "checkpoint": checkpoint,
            "handoff_report": handoff_report,
        }

    def generate_handoff_report(
        self,
        *,
        shift_number: int,
        model: str,
        completed_tasks: List[Dict[str, Any]],
        paused_tasks: List[Dict[str, Any]],
        events_log: List[Dict[str, Any]],
        checkpoint: Dict[str, Any],
        timestamp: str,
    ) -> str:
        """Produce structured Markdown handoff document for the shift boundary."""
        status = checkpoint.get("evaluation", {}).get("status", "UNKNOWN")
        consumed = checkpoint.get("evaluation", {}).get("tokens_consumed", 0)
        remaining = checkpoint.get("evaluation", {}).get("remaining_tokens", 0)
        used_pct = checkpoint.get("evaluation", {}).get("used_percent", 0.0)

        next_shift = 2 if shift_number == 1 else 1
        lines = [
            f"# Serenity AI Company — Shift {shift_number} Handoff Report",
            "",
            f"**Timestamp:** `{timestamp}`",
            f"**Shift Window:** Shift {shift_number} (Concluded)",
            f"**Next Window:** Shift {next_shift} Target Window",
            f"**Checkpoint ID:** `{checkpoint.get('checkpoint_id')}`",
            "",
            "## 1. Quota & Consumption Status",
            "",
            f"- **Active Model:** `{model}`",
            f"- **Operating Status:** `{status}`",
            f"- **Daily Consumption:** {consumed:,} / 60,000 tokens ({used_pct}%)",
            f"- **Remaining Allowance:** {remaining:,} tokens",
            f"- **Zero-Spend Incurred:** $0.00",
            "",
            "## 2. Completed Tasks",
            "",
        ]

        if completed_tasks:
            for t in completed_tasks:
                lines.append(f"- [x] `{t.get('task_id')}`: {t.get('title', 'Task')} ({t.get('status')})")
        else:
            lines.append("- *(No tasks completed in this window)*")

        lines.extend([
            "",
            "## 3. Paused / In-Flight Tasks",
            "",
        ])

        if paused_tasks:
            for t in paused_tasks:
                lines.append(f"- [ ] `{t.get('task_id')}`: {t.get('title', 'Task')} — **{t.get('status')}**")
        else:
            lines.append("- *(Zero paused tasks; clean handoff)*")

        lines.extend([
            "",
            "## 4. Shift Events Log",
            "",
        ])

        for ev in events_log:
            lines.append(f"- `{ev.get('time')}` — **{ev.get('event')}**: {ev.get('details', ev.get('task_id', ''))}")

        lines.extend([
            "",
            "## 5. Next Shift Resumption Gate",
            "",
            "> [!IMPORTANT]",
            f"> Shift {next_shift} must verify that fresh quota capacity is available before resuming paused tasks.",
            "> Reaching the clock boundary alone is not proof of reset.",
            "",
        ])

        return "\n".join(lines)
