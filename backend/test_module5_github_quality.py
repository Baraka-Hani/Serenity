"""Exact GitHub check provenance / independent review contract tests."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.github_quality import (
    EvidenceBlocked, verify_pr_evidence, GithubQualityReader, REQUIRED_JOBS,
)

SHA = "a"*40


def sample_pr():
    return {
        "number": 101, "state": "open", "draft": True, "changed_files": 1,
        "head": {"sha": SHA, "ref": "ai/serenity-issue-22"},
        "base": {"ref": "main"}, "user": {"login": "serenity-manager"},
    }


def sample_checks():
    return {
        "total_count": len(REQUIRED_JOBS),
        "check_runs": [{
            "name": name, "head_sha": SHA, "status": "completed",
            "conclusion": "success", "app": {"slug": "github-actions"},
            "html_url": "https://github.com/Baraka-Hani/Serenity/actions/runs/222",
        } for name in sorted(REQUIRED_JOBS)],
    }


def sample_files():
    return [{
        "filename": "backend/test_destination_picker.js",
        "status": "modified", "changes": 2,
    }]


def sample_reviews():
    return [{
        "state": "APPROVED", "commit_id": SHA, "user": {"login": "qa-human"},
        "submitted_at": "2026-11-14T23:00:00Z",
    }]


class TrustedEvidenceTests(unittest.TestCase):
    def good(self):
        return {
            "pull_request": sample_pr(), "changed_files": sample_files(),
            "checks": sample_checks(), "reviews": sample_reviews(),
        }

    def test_full_exact_commit_trust_check_is_advisory_not_merge(self):
        result = verify_pr_evidence(**self.good())
        self.assertEqual(result["head_sha"], SHA)
        self.assertEqual(result["gate"], "READY_FOR_MANAGER_REVIEW")
        self.assertEqual(result["independent_reviewers"], ["qa-human"])
        self.assertFalse(result["automatic_merge_authorized"])

    def test_fake_ci_or_wrong_sha_rejected(self):
        for mutation in ("pending", "failure", "skipped"):
            record = self.good()
            record["checks"]["check_runs"][0]["conclusion"] = mutation
            with self.subTest(mutation=mutation), self.assertRaises(EvidenceBlocked):
                verify_pr_evidence(**record)
        record = self.good()
        record["checks"]["check_runs"][0]["head_sha"] = "b"*40
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)

    def test_missing_required_check_and_pagination_rejected(self):
        record = self.good()
        record["checks"]["check_runs"].pop()
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)
        record = self.good()
        record["checks"]["total_count"] = len(REQUIRED_JOBS) + 1
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)

    def test_self_approved_review_or_bot_is_not_independent(self):
        for reviewer in ("serenity-manager", "code-review[bot]"):
            record = self.good()
            record["reviews"][0]["user"]["login"] = reviewer
            with self.subTest(reviewer=reviewer), self.assertRaises(EvidenceBlocked):
                verify_pr_evidence(**record)

    def test_stale_review_sha_and_changes_requested_rejected(self):
        record = self.good()
        record["reviews"][0]["commit_id"] = "b"*40
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)
        record = self.good()
        record["reviews"].append({
            "user": {"login": "qa-human"},
            "state": "CHANGES_REQUESTED", "commit_id": SHA,
            "submitted_at": "2026-11-14T23:10:00Z",
        })
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)

    def test_sensitive_paths_and_unexpected_base_block(self):
        for path in (".github/workflows/ci.yml", "backend/server.py",
                     "backend/data/roam.sqlite3", "nomad-canvas/firebase.ts"):
            record = self.good()
            record["changed_files"][0]["filename"] = path
            with self.subTest(path=path), self.assertRaises(EvidenceBlocked):
                verify_pr_evidence(**record)
        record = self.good()
        record["pull_request"]["base"]["ref"] = "production"
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)

    def test_non_draft_and_non_manager_branch_rejected(self):
        record = self.good()
        record["pull_request"]["draft"] = False
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)
        record = self.good()
        record["pull_request"]["head"]["ref"] = "main"
        with self.assertRaises(EvidenceBlocked):
            verify_pr_evidence(**record)

    def test_reader_rejects_invalid_id_without_any_api_call(self):
        class Forbidden:
            def open(self, *a, **kw):
                raise AssertionError("unexpected network read")
        client = GithubQualityReader(transport=Forbidden())
        for number in (0, -1, "101", None):
            with self.assertRaises(EvidenceBlocked):
                client.inspect_draft_pr(number)

if __name__ == "__main__":
    unittest.main()
