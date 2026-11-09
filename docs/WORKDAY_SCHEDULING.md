# Supervised workday scheduling

Phase 5 adds a default-off schedule for the Serenity AI workforce. It recognizes
9 AM intake and 5 PM reporting events on weekdays in `America/Moncton`, including
daylight-saving changes.

## What it does

- Scheduled triggers cover both possible Atlantic UTC offsets.
- A Python gate evaluates the nominal trigger time, so normal GitHub runner
  delays do not skip an event, and accepts only the correct local 9 AM or 5 PM
  event.
- Accepted events render `.github/workday-queue.json` through the read-only
  Phase 4 report generator and upload the Markdown as a short-lived CI artifact.
- Manual workflow runs provide safe intake/report previews.

It does not call models, edit issues, push code, merge, deploy, send email,
access production data, or use secrets.

## Default-off activation

The scheduled job is skipped before runner allocation unless the repository
variable `SERENITY_WORKFORCE_ENABLED` is exactly `true`. Manual dry runs remain
available because they create only a report artifact.

Before activation:

1. Run the manual intake and report previews.
2. Confirm the artifact contains only intended task metadata.
3. Confirm repository Actions usage and cost expectations.
4. Obtain owner approval to set the variable.

## Emergency stop

Set `SERENITY_WORKFORCE_ENABLED` to `false` or remove it. GitHub sees the cron
trigger but skips the job before allocating a runner. Disabling the workflow in
GitHub Actions is the stronger stop if no scheduled trigger should occur.

## Cost boundary

The workflow uses ordinary GitHub-hosted CI minutes and no model or paid API. It
has a five-minute timeout and retains artifacts for 14 days. Activation should
still follow the owner's repository-usage review.
