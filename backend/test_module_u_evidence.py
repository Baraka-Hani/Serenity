"""Module U read-only GitHub Git blob / exact SHA / CI / QA dossier tests."""
import base64
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.module_u_evidence import (
    DossierBlocked, inspect_exact_pr, git_blob_sha,
)
from company.github_quality import GithubQualityReader, REQUIRED_JOBS

BASE = "a"*40
HEAD = "b"*40
ORIGINAL = b"const place = 'Sackville';\n"
CANDIDATE = b"const place = 'Sackville';\n// assert local API\n"
PATH = "backend/test_destination_picker.js"
PR = 1001


def blob(contents):
    return {
        "type": "file", "path": PATH,
        "sha": git_blob_sha(contents),
        "size": len(contents), "encoding": "base64",
        "content": base64.b64encode(contents).decode("ascii"),
    }


def sources():
    pr = {
        "number": PR, "state": "open", "draft": True,
        "changed_files": 1, "user": {"login": "serenity-manager"},
        "head": {"sha": HEAD, "ref": "ai/serenity-issue-22",
                 "repo": {"full_name": "Baraka-Hani/Serenity"}},
        "base": {"sha": BASE, "ref": "main",
                 "repo": {"full_name": "Baraka-Hani/Serenity"}},
    }
    files = [{"filename": PATH, "status": "modified", "changes": 2}]
    checks = {"total_count": len(REQUIRED_JOBS), "check_runs": [
        {"name": name, "head_sha": HEAD, "status": "completed",
         "conclusion": "success", "app": {"slug": "github-actions"},
         "html_url": "https://github.com/Baraka-Hani/Serenity/actions/runs/999"}
        for name in sorted(REQUIRED_JOBS)]}
    reviews = [{"user": {"login": "independent-human"},
                "commit_id": HEAD, "state": "APPROVED",
                "submitted_at": "2026-11-14T23:00:00Z"}]
    return {
        "/pulls/1001": pr,
        "/pulls/1001/files?per_page=100": files,
        "/commits/"+HEAD+"/check-runs?per_page=100": checks,
        "/pulls/1001/reviews?per_page=100": reviews,
        "/contents/"+PATH+"?ref="+BASE: blob(ORIGINAL),
        "/contents/"+PATH+"?ref="+HEAD: blob(CANDIDATE),
    }


class StubReader(GithubQualityReader):
    def __init__(self, routes=None):
        super().__init__()
        self.routes = routes if routes is not None else sources()
        self.paths = []
    def _get(self, path):
        self.paths.append(path)
        if path not in self.routes:
            raise AssertionError("unapproved GitHub API endpoint")
        return self.routes[path]


def run_case(reader=None):
    return inspect_exact_pr(
        reader or StubReader(), pr_number=PR,
        expected_base_sha256=hashlib.sha256(ORIGINAL).hexdigest(),
        expected_candidate_sha256=hashlib.sha256(CANDIDATE).hexdigest())


class ExactCommitDossierTests(unittest.TestCase):
    def test_consistent_blob_ci_and_independent_review_is_advisory(self):
        reader = StubReader()
        dossier = run_case(reader)
        self.assertEqual(dossier["candidate_sha256"],
                         hashlib.sha256(CANDIDATE).hexdigest())
        self.assertEqual(dossier["candidate_git_blob_sha"], git_blob_sha(CANDIDATE))
        self.assertEqual(dossier["baseline_git_blob_sha"], git_blob_sha(ORIGINAL))
        self.assertEqual(dossier["head_commit_sha"], HEAD)
        self.assertEqual(dossier["independent_human_reviewers"], ["independent-human"])
        self.assertEqual(len(reader.paths), 6)
        self.assertEqual(reader.paths[-2:], [
            "/contents/"+PATH+"?ref="+BASE, "/contents/"+PATH+"?ref="+HEAD])
        self.assertTrue(dossier["github_metadata_correspondence_verified"])
        for key in ("isolated_candidate_runtime_attested",
                    "independent_ai_model_review_proven",
                    "manager_commit_execution_authorized",
                    "draft_pr_write_authorized",
                    "automatic_merge_authorized", "production_deploy_authorized",
                    "owner_financial_approval_granted"):
            self.assertFalse(dossier[key])

    def test_incomplete_checks_or_fake_ci_failed(self):
        for action in ("missing", "paginated", "wrong_sha", "bot_app", "failed"):
            routes = sources()
            checks = routes["/commits/"+HEAD+"/check-runs?per_page=100"]
            if action == "missing":
                checks["check_runs"].pop()
            elif action == "paginated":
                checks["total_count"] = 100
                checks["check_runs"] *= 25
            elif action == "wrong_sha":
                checks["check_runs"][0]["head_sha"] = BASE
            elif action == "bot_app":
                checks["check_runs"][0]["app"]["slug"] = "untrusted-app"
            elif action == "failed":
                checks["check_runs"][0]["conclusion"] = "failure"
            with self.subTest(action=action), self.assertRaises(DossierBlocked):
                run_case(StubReader(routes))

    def test_self_review_and_stale_review_rejected(self):
        for reviewer, sha in (("serenity-manager", HEAD),
                              ("independent-human", BASE),
                              ("untrusted-bot[bot]", HEAD)):
            routes = sources()
            reviews = routes["/pulls/1001/reviews?per_page=100"]
            reviews[0]["user"]["login"] = reviewer
            reviews[0]["commit_id"] = sha
            with self.subTest(reviewer=reviewer), self.assertRaises(DossierBlocked):
                run_case(StubReader(routes))

    def test_fork_or_sensitive_change_rejected(self):
        for change in ("fork", "prod", "multiple", "non_draft", "pr_number"):
            routes = sources()
            pr = routes["/pulls/1001"]
            if change == "fork":
                pr["head"]["repo"]["full_name"] = "attacker/Serenity"
            elif change == "prod":
                routes["/pulls/1001/files?per_page=100"][0]["filename"] = "backend/server.py"
            elif change == "multiple":
                pr["changed_files"] = 2
            elif change == "non_draft":
                pr["draft"] = False
            else:
                pr["number"] = 1002
            with self.subTest(change=change), self.assertRaises(DossierBlocked):
                run_case(StubReader(routes))

    def test_forged_contents_malformed_encoding_or_wrong_ref_rejected(self):
        for change in ("wrong_blob_sha", "mutate_file", "oversize",
                       "bad_b64", "wrong_path", "size", "binary"):
            routes = sources()
            content = routes["/contents/"+PATH+"?ref="+HEAD]
            if change == "wrong_blob_sha":
                content["sha"] = "0"*40
            elif change == "mutate_file":
                content["content"] = base64.b64encode(b"unreviewed source").decode()
            elif change == "oversize":
                buf = b"x"*6501
                content.update(content=base64.b64encode(buf).decode(),
                               sha=git_blob_sha(buf), size=len(buf))
            elif change == "bad_b64":
                content["content"] = "$$$$$"
            elif change == "wrong_path":
                content["path"] = "backend/server.py"
            elif change == "size":
                content["size"] += 1
            elif change == "binary":
                content["content"] = base64.b64encode(b"\xff").decode()
            with self.subTest(change=change), self.assertRaises(DossierBlocked):
                run_case(StubReader(routes))

    def test_stale_expected_hash_or_base_commit_rejected(self):
        with self.assertRaises(DossierBlocked):
            inspect_exact_pr(StubReader(), pr_number=PR,
                             expected_base_sha256="0"*64,
                             expected_candidate_sha256=hashlib.sha256(CANDIDATE).hexdigest())
        routes = sources()
        routes["/pulls/1001"]["base"]["sha"] = HEAD
        with self.assertRaises(DossierBlocked):
            run_case(StubReader(routes))

    def test_client_and_pr_number_must_be_valid(self):
        for number in (0, -1, "1001", 10000001):
            with self.subTest(number=number), self.assertRaises(DossierBlocked):
                inspect_exact_pr(StubReader(), pr_number=number,
                    expected_base_sha256=hashlib.sha256(ORIGINAL).hexdigest(),
                    expected_candidate_sha256=hashlib.sha256(CANDIDATE).hexdigest())
        with self.assertRaises(DossierBlocked):
            inspect_exact_pr(object(), pr_number=1001,
                expected_base_sha256=hashlib.sha256(ORIGINAL).hexdigest(),
                expected_candidate_sha256=hashlib.sha256(CANDIDATE).hexdigest())


if __name__ == "__main__":
    unittest.main()
