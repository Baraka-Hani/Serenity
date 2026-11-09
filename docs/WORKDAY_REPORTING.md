# AI workday reporting

Phase 4 adds a read-only operating record for Serenity's supervised 9 AM–5 PM
AI workforce. It does not schedule agents, mutate GitHub, merge code, deploy, or
access production data.

## 9 AM intake

For each approved task, record the task name, model, agent role, contribution,
starting status, expected verification, cost boundary, known blocker, and any
decision reserved for the owner.

## During the workday

Update the structured task record only when there is evidence: a commit, test
result, review finding, blocker, or owner decision. Model claims alone are not
completion evidence.

## 5 PM report

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
process, or deployment integration. Scheduling and notifications remain a later
owner-approved step after this reporting format proves useful.
