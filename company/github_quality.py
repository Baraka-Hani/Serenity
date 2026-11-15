"""Read-only, exact-commit GitHub evidence verifier.

Only GitHub's official HTTPS API may supply CI runs, changed files and
independent approvals. Model-generated JSON and self-reported CI URLs have
zero authority. Verification is advisory until a scoped writer is approved.
"""
import json
import re
from urllib import error, request

REPO = "Baraka-Hani/Serenity"
BASE_URL = "https://api.github.com/repos/" + REPO
SHA = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_PREFIX = "ai/serenity-"
MAX_RESPONSE = 500000
ALLOWED_FILES = frozenset({"backend/test_destination_picker.js"})
REQUIRED_JOBS = frozenset({
    "backend-and-browser-logic",
    "react-prototype",
    "module5-candidate-sandbox",
    "module5-privacy-and-architecture",
})
BOT_SUFFIX = "[bot]"


class EvidenceBlocked(ValueError):
    pass


def verify_pr_evidence(*, pull_request, changed_files, checks, reviews):
    """No network; consumes records later fetched from trusted GitHub GETs."""
    if not isinstance(pull_request, dict):
        raise EvidenceBlocked("GitHub PR metadata missing")
    head = pull_request.get("head")
    base = pull_request.get("base")
    author = pull_request.get("user") or {}
    number = pull_request.get("number")
    if (not isinstance(head, dict) or not isinstance(base, dict)
            or not isinstance(number, int) or isinstance(number, bool)
            or number <= 0):
        raise EvidenceBlocked("invalid pull request identity")
    sha, branch = head.get("sha"), head.get("ref")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise EvidenceBlocked("invalid exact head SHA")
    if not isinstance(branch, str) or not branch.startswith(ALLOWED_PREFIX):
        raise EvidenceBlocked("unapproved manager feature branch")
    if (not isinstance(head.get("repo"), dict)
            or head["repo"].get("full_name") != REPO
            or not isinstance(base.get("repo"), dict)
            or base["repo"].get("full_name") != REPO):
        raise EvidenceBlocked("fork-based or cross-repository pull requests are not delegated")
    if base.get("ref") not in {"main", "company/engineering-issue-to-review-pipeline",
                               "company/module4-hosted-model-dispatch"}:
        raise EvidenceBlocked("unexpected base branch")
    if pull_request.get("state") != "open" or pull_request.get("draft") is not True:
        raise EvidenceBlocked("only open draft PRs may enter the pilot")
    if not isinstance(changed_files, list) or not changed_files:
        raise EvidenceBlocked("no verified changed files")
    if len(changed_files) != pull_request.get("changed_files") or len(changed_files) > 20:
        raise EvidenceBlocked("file count incomplete or excessive")
    paths = []
    for file in changed_files:
        if not isinstance(file, dict):
            raise EvidenceBlocked("invalid GitHub file entry")
        path = file.get("filename")
        if (path not in ALLOWED_FILES or file.get("status") != "modified"
                or type(file.get("changes")) is not int or file["changes"] > 12
                or file["changes"] <= 0):
            raise EvidenceBlocked("sensitive file, unsupported change, or diff too large")
        paths.append(path)
    if len(set(paths)) != len(paths):
        raise EvidenceBlocked("duplicate changed path")
    if not isinstance(checks, dict) or not isinstance(checks.get("check_runs"), list):
        raise EvidenceBlocked("trusted CI snapshot missing")
    if checks.get("total_count") != len(checks["check_runs"]):
        raise EvidenceBlocked("incomplete check-run pagination")
    passed = set()
    found = {}
    for entry in checks["check_runs"]:
        if not isinstance(entry, dict):
            raise EvidenceBlocked("malformed check record")
        name = entry.get("name")
        if name not in REQUIRED_JOBS:
            continue
        app = entry.get("app") or {}
        if (entry.get("head_sha") != sha or entry.get("status") != "completed"
                or entry.get("conclusion") != "success" or app.get("slug") != "github-actions"):
            raise EvidenceBlocked("required check not a matching successful GitHub Actions job")
        if name in found:
            raise EvidenceBlocked("duplicate check name; ambiguous provenance")
        found[name] = entry.get("html_url", "")
        passed.add(name)
    missing = sorted(REQUIRED_JOBS - passed)
    if missing:
        raise EvidenceBlocked("missing trusted checks: " + ", ".join(missing))
    if not isinstance(reviews, list) or len(reviews) >= 100:
        raise EvidenceBlocked("review metadata missing or pagination incomplete")
    author_login = author.get("login")
    if not isinstance(author_login, str) or not author_login:
        raise EvidenceBlocked("invalid PR author")
    newest = {}
    for review in reviews:
        if not isinstance(review, dict):
            raise EvidenceBlocked("invalid review entry")
        user = review.get("user") or {}
        login = user.get("login")
        if isinstance(login, str) and login:
            # Order from GitHub REST is chronological; a later dismissal or
            # request-changes overrides an earlier approval from that person.
            newest[login] = review
    approved_by = []
    for login, review in newest.items():
        if (login != author_login and not login.endswith(BOT_SUFFIX)
                and review.get("state") == "APPROVED"
                and review.get("commit_id") == sha
                and isinstance(review.get("submitted_at"), str)):
            approved_by.append(login)
    if not approved_by:
        raise EvidenceBlocked("independent human approval of exact head SHA missing")
    if any(review.get("state") == "CHANGES_REQUESTED" for review in newest.values()):
        raise EvidenceBlocked("unresolved requested changes")
    return {
        "trusted_gitHub_evidence": True,
        "head_sha": sha,
        "pull_request": number,
        "branch": branch,
        "changed_files": paths,
        "required_jobs_passed": sorted(passed),
        "independent_reviewers": sorted(approved_by),
        "gate": "READY_FOR_MANAGER_REVIEW",
        "automatic_merge_authorized": False,
        "production_deploy_authorized": False,
    }


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GithubQualityReader:
    def __init__(self, *, token="", transport=None):
        self.token = token
        self.transport = transport or request.build_opener(NoRedirect())

    def _get(self, path):
        if not isinstance(path, str) or not path.startswith("/"):
            raise EvidenceBlocked("bad GitHub path")
        url = BASE_URL + path
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Serenity-M5-readonly-evidence",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        try:
            req = request.Request(url, headers=headers, method="GET")
            with self.transport.open(req, timeout=12) as response:
                if response.geturl() != url:
                    raise EvidenceBlocked("redirect not allowed")
                raw = response.read(MAX_RESPONSE+1)
                if len(raw) > MAX_RESPONSE:
                    raise EvidenceBlocked("GitHub response too large")
                return json.loads(raw.decode("utf-8"))
        except error.HTTPError as exc:
            raise EvidenceBlocked("GitHub evidence HTTP " + str(exc.code)) from None
        except (error.URLError, TimeoutError):
            raise EvidenceBlocked("GitHub read failed") from None
        except (json.JSONDecodeError, UnicodeError):
            raise EvidenceBlocked("malformed GitHub evidence") from None

    def inspect_draft_pr(self, number):
        if type(number) is not int or not 1 <= number <= 10000000:
            raise EvidenceBlocked("invalid PR number")
        pr = self._get("/pulls/" + str(number))
        if not isinstance(pr, dict):
            raise EvidenceBlocked("invalid PR")
        head = pr.get("head") or {}
        sha = head.get("sha")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise EvidenceBlocked("invalid head SHA")
        files = self._get("/pulls/" + str(number) + "/files?per_page=100")
        checks = self._get("/commits/" + sha + "/check-runs?per_page=100")
        reviews = self._get("/pulls/" + str(number) + "/reviews?per_page=100")
        return verify_pr_evidence(pull_request=pr, changed_files=files,
                                  checks=checks, reviews=reviews)
