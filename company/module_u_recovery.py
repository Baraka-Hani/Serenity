"""Read-only GitHub company-state recovery with conflict-safe handoff plans.

This module never invokes GithubCheckpointStore.write_once, creates a branch,
or merges event histories. Remote state is only accepted from the fixed
GitHub Contents read client that independently verifies its Git blob SHA.
"""
from __future__ import annotations

from company.checkpoint_store import checkpoint_summary, validate_ledger
from company.github_checkpoint import GithubCheckpointStore, RemoteStateBlocked
from company.technical_readiness import reconcile_snapshots


def inspect_recovery(local, *, store=None, remote_read_authorized=False):
    """Report recovery decisions; no filesystem, model or GitHub write."""
    validate_ledger(local)
    local_summary = checkpoint_summary(local)
    result = {
        "schema_version": 1,
        "local_event_count": local_summary["event_count"],
        "local_head": local_summary["last_hash"],
        "task_count": len(local_summary["tasks"]),
        "remote_state_branch": "serenity-company-state",
        "remote_state_file": "state/company-ledger.json",
        "remote_read_executed": False,
        "remote_git_blob_sha": None,
        "remote_event_count": None,
        "status": "REMOTE_NOT_OBSERVED",
        "reason": "no authorized cloud checkpoint read has been performed",
        "common_events": None,
        "next_action": "verify the approved cloud state branch and read-only permission before any sync",
        "remote_write_authorized": False,
        "automatic_merge_authorized": False,
        "unattended_execution_enabled": False,
        "spending_authorized": False,
        "cloud_state_confirmed_durable": False,
    }
    if remote_read_authorized is not True:
        return result
    if not isinstance(store, GithubCheckpointStore):
        result["status"] = "REMOTE_READER_NOT_CONFIGURED"
        result["reason"] = "fixed-source read-only client was not provided"
        return result
    result["remote_read_executed"] = True
    try:
        remote = store.read()
    except RemoteStateBlocked as exc:
        result["status"] = "REMOTE_READ_BLOCKED"
        result["reason"] = str(exc)
        result["next_action"] = "retain local checkpoint and review the missing/stale remote state"
        return result
    # store.read validates the exact fixed path, SHA-1 Git blob, data schema
    # and event integrity chain before this point.
    comparison = reconcile_snapshots(local, remote["ledger"])
    result.update({
        "remote_git_blob_sha": remote["remote_git_blob_sha"],
        "remote_event_count": len(remote["ledger"]["events"]),
        "common_events": comparison["common_events"],
        "status": comparison["status"],
        "reason": "remote Git blob and ledger integrity validated; advisory comparison only",
        "next_action": comparison["next_action"],
        "cloud_state_confirmed_durable": True,
    })
    if comparison["status"] == "DIVERGED_BLOCKED":
        result["next_action"] = "preserve both histories, request human conflict reconciliation"
    return result


def recovery_markdown(report):
    """Generate a safe, human-readable Obsidian status note."""
    from company.obsidian import md
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("invalid recovery status")
    fields = [
        "# Serenity Cloud Checkpoint Recovery",
        "",
        "> Read-only report. No remote state or task history was modified.",
        "",
        f"- Status: **{md(report['status'])}**",
        f"- Local events: {int(report['local_event_count'])}",
        f"- Local chain head: `{md(report['local_head'])}`",
        f"- Remote read performed: **{'YES' if report['remote_read_executed'] else 'NO'}**",
        f"- Remote events: {md(report['remote_event_count'] if report['remote_event_count'] is not None else 'unknown')}",
        f"- Remote Git blob hash: `{md(report['remote_git_blob_sha'] or 'not verified')}`",
        f"- Reason: {md(report['reason'])}",
        f"- Next safe action: {md(report['next_action'])}",
        "",
        "## Permissions and trust",
        "",
        "- Automatic merge: **DISABLED**",
        "- GitHub state writes: **DISABLED**",
        "- Unattended AI agents: **DISABLED**",
        "- New spending: **NOT AUTHORIZED**",
        "",
        "If the remote branch is absent, an expiring GitHub Actions artifact "
        "does not replace durable task state.",
    ]
    return "\n".join(fields) + "\n"
