# Supervised daily two-shift scheduling

Serenity's proposed operating hours are **every day, including weekends**, in `America/Moncton`:

| Shift | Local hours | Length | Checkpoint |
| --- | --- | --- | --- |
| Shift 1 | 09:00–14:00 | 5 hours | 09:00 intake; 14:00 shift handoff |
| Shift 2 | 14:00–19:00 | 5 hours | 14:00 handoff/intake; 19:00 daily report |

Total planned coverage: **10 hours/day, 70 hours/week**, conditional on provider eligibility, free quotas and explicit future owner activation. These are *operating windows*, not ten hours of guaranteed model inference or automatic subscription-credit resets.

## What the existing read-only workflow does

- UTC schedule triggers cover 09:00, 14:00 and 19:00 Atlantic in both standard time and daylight time, seven days a week.
- A Python gate validates the nominal event hour to reject DST duplicate triggers and handle normal GitHub runner delay.
- 09:00 creates an `intake` artifact, 14:00 creates a `handoff` artifact, and 19:00 creates a `report` artifact. The 14:00 handoff represents the boundary between two shifts; the underlying task record must eventually be updated by a separately approved orchestrator.
- Manual `intake`, `handoff` and `report` previews are available without scheduled activation.
- Output is a validated Markdown report of the static example queue from `.github/workday-queue.json`, retained for 14 days.

**Important:** The current workflow is a read-only report generator. It does **not** call language models, code autonomously, transfer active work, edit issues, push code, merge, deploy, send messages, access secrets or production data.

## Default-off activation

Scheduled jobs skip before runner allocation unless the repository variable `SERENITY_WORKFORCE_ENABLED` is exactly `true`. Merely changing schedule definitions does not activate the workflow.

Before changing that setting:

1. Run all applicable tests, including `python3 backend/test_workday_schedule.py` and the manual intake/handoff/report previews.
2. Verify that reports contain no secrets or sensitive information.
3. Review the actual GitHub Actions quota and cost impact of three events per calendar day.
4. Obtain explicit owner approval.

## Future autonomous worker design (separate approval required)

Each five-hour shift should restore unfinished work, run short bounded cloud tasks, checkpoint outputs, pass findings to QA, and log usage. At 14:00 the second shift inherits open tasks and blockers; it does not automatically restart or duplicate partially finished operations.

Free API quotas and GitHub Actions compute are not guaranteed to cover ten hours of continuous work. On rate limit or depleted subscription allowance, agents should pause, checkpoint, and move only to authorized free work; they must not evade limits or incur charges.

## Emergency stop

Set `SERENITY_WORKFORCE_ENABLED` to `false` or remove it; disable the workflow in GitHub Actions for a stronger stop. Independently revoke any future cloud-inference credentials if required.

## Cost boundary

The existing reporting workflow uses ordinary GitHub-hosted CI minutes and no AI API. Each event has a five-minute runner timeout, read-only permissions, and 14-day artifact retention. Changing to seven-day, three-event scheduling increases possible CI usage if the schedule is authorized.