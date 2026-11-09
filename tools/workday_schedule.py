#!/usr/bin/env python3
"""Gate Serenity's supervised workday events in Atlantic local time."""

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


LOCAL_ZONE = ZoneInfo("America/Moncton")
EVENTS = {9: "intake", 17: "report"}


def evaluate(now, enabled=False, manual_event=None, nominal_utc_hour=None):
    if manual_event:
        return {"should_run": True, "event": manual_event, "reason": "manual dry run"}
    if not enabled:
        return {"should_run": False, "event": "none", "reason": "workforce disabled"}
    event_time = now
    if nominal_utc_hour is not None:
        event_time = now.astimezone(timezone.utc).replace(
            hour=nominal_utc_hour, minute=0, second=0, microsecond=0
        )
    local = event_time.astimezone(LOCAL_ZONE)
    if local.weekday() >= 5:
        return {"should_run": False, "event": "none", "reason": "weekend"}
    event = EVENTS.get(local.hour) if local.minute == 0 else None
    if not event:
        return {"should_run": False, "event": "none", "reason": "outside event time"}
    return {"should_run": True, "event": event, "reason": "scheduled workday event"}


def parse_now(value):
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--now must include a timezone")
    return parsed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--manual-event", choices=("intake", "report"))
    parser.add_argument("--scheduled-cron", help="nominal GitHub cron expression")
    parser.add_argument("--now", help="timezone-aware ISO timestamp for verification")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    try:
        now = parse_now(args.now)
        nominal_hour = None
        if args.scheduled_cron:
            parts = args.scheduled_cron.split()
            if len(parts) != 5 or not parts[1].isdigit():
                raise ValueError("--scheduled-cron must contain one numeric UTC hour")
            nominal_hour = int(parts[1])
            if nominal_hour not in range(24):
                raise ValueError("--scheduled-cron UTC hour is invalid")
        result = evaluate(now, args.enabled, args.manual_event, nominal_hour)
    except ValueError as error:
        parser.error(str(error))

    lines = [
        f"should_run={str(result['should_run']).lower()}",
        f"event={result['event']}",
        f"reason={result['reason']}",
        f"local_date={now.astimezone(LOCAL_ZONE).date().isoformat()}",
    ]
    text = "\n".join(lines) + "\n"
    if args.github_output:
        args.github_output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
