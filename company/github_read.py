#!/usr/bin/env python3
"""Allowlisted, read-only GitHub Issue importer for Serenity HQ.

Only approved manual runs perform a network read. Issue bodies are untrusted
task proposals. No API writes, issue comments, pull requests or code execution.
"""
import argparse
import json
import os
from pathlib import Path
from urllib import request, error
from company.office import CompanyOffice

REPO = "Baraka-Hani/Serenity"
URL = "https://api.github.com/repos/Baraka-Hani/Serenity/issues?state=open&per_page=100&page=1"
MAX_JSON_BYTES = 1000000


class ImportBlocked(ValueError):
    pass


def validate_items(raw):
    if not isinstance(raw, list):
        raise ImportBlocked("GitHub response must be a list")
    return [
        {
            "number": item["number"],
            "title": item["title"],
            "body": (item.get("body") or "")[:3000],
            "labels": [label.get("name") for label in item.get("labels", [])
                       if isinstance(label, dict) and isinstance(label.get("name"), str)],
        }
        for item in raw if isinstance(item, dict)
        and "pull_request" not in item
        and isinstance(item.get("number"), int)
        and not isinstance(item["number"], bool)
        and isinstance(item.get("title"), str)
    ]


def read_issues(token=""):
    class NoRedirect(request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "Serenity-HQ-readonly-import",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = "Bearer " + token
    client = request.build_opener(NoRedirect)
    req = request.Request(URL, headers=headers, method="GET")
    try:
        with client.open(req, timeout=12) as resp:
            if resp.geturl() != URL:
                raise ImportBlocked("unexpected redirected URL")
            raw = resp.read(MAX_JSON_BYTES + 1)
            if len(raw) > MAX_JSON_BYTES:
                raise ImportBlocked("response too large")
            return validate_items(json.loads(raw.decode("utf-8")))
    except error.HTTPError as exc:
        raise ImportBlocked("GitHub read failed (HTTP " + str(exc.code) + ")") from None
    except (error.URLError, TimeoutError):
        raise ImportBlocked("GitHub unavailable, no retry") from None


def ingest(office, records):
    tasks = []
    for item in validate_items(records):
        task_id = office.import_issue(REPO, item["number"], item["title"],
                                      item["body"], item["labels"])
        tasks.append({"github_issue": item["number"], "local_task_id": task_id})
    return tasks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--explicit-read-only-github", action="store_true",
                   help="required to allow one network GET to the official GitHub API")
    args = p.parse_args()
    if not args.explicit_read_only_github:
        p.error("GitHub network read requires explicit permission")
    office = CompanyOffice(args.db)
    try:
        outcome = ingest(office, read_issues(os.environ.get("GITHUB_TOKEN", "")))
        print(json.dumps({"source": REPO, "imported_or_existing": outcome,
                          "agents_activated": False, "writes_to_github": False}, indent=2))
    except ImportBlocked as exc:
        p.exit(2, "BLOCKED: " + str(exc) + "\n")
    finally:
        office.close()


if __name__ == "__main__":
    main()
