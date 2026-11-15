# AI workday reporting

Phase 4 adds a read-only operating record for Serenity's supervised two
five-hour shifts every day (9 AM–2 PM and 2 PM–7 PM America/Moncton).
It does not execute agents, mutate GitHub, merge code, deploy, or access
production data.

## 9 AM intake

For each approved task, record the task name, model, agent role, contribution,
starting status, expected verification, cost boundary, known blocker, and any
decision reserved for the owner.

## 2 PM handoff between shifts

Checkpoint unfinished tasks, current branches, verification evidence and known
blockers. Shift 2 may resume only authorized work and must not duplicate actions.
The existing generator provides a read-only static report, not a live handoff.

## During either shift

Update the structured task record only when there is evidence: a commit, test
result, review finding, blocker, or owner decision. Model claims alone are not
completion evidence.

## 7 PM final report

Generate the deterministic Markdown report:

```bash
python3 tools/workday_report.py .github/workday-report.example.json
```

The report makes completed, blocked, and approval-required work visible in the
same format. Keep `$0` as the default cost boundary and record proposed spend
before any paid action.

## Safety boundary

The generator reads one local JSON file and writes Markdown to standard output.
It has no network client, credentials, GitHub mutations, timers, background
process, or deployment integration. The read-only scheduler exists but remains default-off. Autonomous execution,
notifications and active task handoffs still require separate owner approval.
