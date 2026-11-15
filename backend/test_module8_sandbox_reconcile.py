"""Tests: official attempt-job discovery, immutable smoke bounds, no GitHub writes."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.sandbox_reconcile import (
    AttestationBlocked, validate_smoke_record, reconcile_smoke_with_github,
    WORKFLOW_FULL_REF,
)
from company.github_quality import BASE_URL, GithubQualityReader

SHA = "a"*40
CANDIDATE = hashlib.sha256(b"real checked in source fixture").hexdigest()
APP = hashlib.sha256(b"existing destination picker").hexdigest()
IMAGE = "docker.io/library/node:22-bookworm-slim@sha256:" + "b"*64
RUN = 5007
ATTEMPT = 2
JOBID = 7001


def smoke():
    return {
        "schema_version": 1,
        "purpose": "KNOWN_CHECKED_IN_SERENITY_TEST_SMOKE",
        "source_sha256": CANDIDATE,
        "candidate_sha256": CANDIDATE,
        "app_sha256": APP,
        "image_digest": IMAGE,
        "runner_result": {
            "candidate_sha256": CANDIDATE,
            "actual_functional_test_executed": True,
            "sandbox": "docker_network_none_readonly_unprivileged",
            "passed": True,
            "returncode": 0,
            "command_template": "node backend/test_destination_picker.js",
            "image_digest": IMAGE,
            "github_write_permissions": False,
            "stdout_tail": "tests pass",
            "stderr_tail": "",
        },
        "github_run_id": str(RUN),
        "github_run_attempt": str(ATTEMPT),
        "github_head_sha": SHA,
        "github_workflow_ref": WORKFLOW_FULL_REF,
        "github_job_name": "module5-candidate-sandbox",
        "provenance": "UNTRUSTED_OUTPUT_PENDING_INDEPENDENT_GITHUB_JOB_LOOKUP",
        "model_generated_code_executed": False,
        "manager_commit_authorized": False,
        "automatic_merge_authorized": False,
    }


def job():
    return {
        "name": "module5-candidate-sandbox",
        "id": JOBID, "run_id": RUN, "head_sha": SHA,
        "status": "completed", "conclusion": "success",
        "steps": [{
            "name": "Execute isolated test in network-off Docker",
            "status": "completed", "conclusion": "success",
        }],
    }


def run():
    return {
        "id": RUN, "run_attempt": ATTEMPT,
        "head_sha": SHA, "head_branch": "main",
        "status": "completed", "conclusion": "success",
        "event": "workflow_dispatch",
        "path": ".github/workflows/serenity-candidate-sandbox.yml@refs/heads/main",
        "repository": {"full_name": "Baraka-Hani/Serenity"},
    }


class Response:
    def __init__(self, url, data):
        self.url, self.data = url, json.dumps(data).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def geturl(self): return self.url
    def read(self, max_size): return self.data[:max_size]


class Transport:
    def __init__(self, *, jobs=None, runner=None):
        self.jobs = jobs if jobs is not None else {
            "total_count": 1, "jobs": [job()],
        }
        self.runner = runner if runner is not None else run()
        self.requests = []
    def open(self, request, timeout):
        if request.get_method() != "GET":
            raise AssertionError("no GitHub write allowed")
        if "Authorization" in request.headers:
            raise AssertionError("test must not use credentials")
        self.requests.append(request.full_url)
        routes = {
            BASE_URL + "/actions/runs/5007/attempts/2/jobs?per_page=100": self.jobs,
            BASE_URL + "/actions/runs/5007": self.runner,
        }
        if request.full_url not in routes:
            raise AssertionError("out-of-scope network request")
        return Response(request.full_url, routes[request.full_url])


class SandboxReconcileTests(unittest.TestCase):
    def evaluate(self, data=None, transport=None):
        t = transport or Transport()
        result = reconcile_smoke_with_github(
            data if data is not None else smoke(),
            reader=GithubQualityReader(transport=t),
        )
        return result, t

    def test_completed_actual_job_correspondence_has_no_writer_authority(self):
        result, transport = self.evaluate()
        self.assertEqual(result["status"], "GITHUB_CORRESPONDENCE_VERIFIED_ONLY")
        self.assertEqual(result["job_id"], JOBID)
        self.assertEqual(result["candidate_sha256"], CANDIDATE)
        self.assertTrue(result["github_correspondence"])
        for key in ("manager_commit_execution_authorized", "automatic_merge_authorized",
                    "public_deploy_authorized", "source_provenance_signed",
                    "sandbox_isolation_independently_attested",
                    "model_generated_code_executed"):
            self.assertFalse(result[key])
        self.assertEqual(transport.requests, [
            BASE_URL + "/actions/runs/5007/attempts/2/jobs?per_page=100",
            BASE_URL + "/actions/runs/5007",
        ])

    def test_proposed_generated_code_is_not_checked_in_source_smoke(self):
        record = smoke()
        record["candidate_sha256"] = "f"*64
        with self.assertRaises(AttestationBlocked):
            validate_smoke_record(record)

    def test_injected_auth_or_special_workflow_ref_fails_before_network(self):
        for field, value in (
            ("github_workflow_ref", "other/repo/.github/workflows/x.yml@refs/heads/main"),
            ("github_job_name", "malicious"),
            ("manager_commit_authorized", True),
            ("automatic_merge_authorized", True),
            ("model_generated_code_executed", True),
            ("github_head_sha", "c"*39),
            ("github_run_id", "0"),
            ("github_run_attempt", "1;curl"),
            ("provenance", "SIGNED_ATTESTATION"),
        ):
            data = smoke()
            data[field] = value
            t = Transport()
            with self.subTest(field=field), self.assertRaises(AttestationBlocked):
                self.evaluate(data, t)
            self.assertFalse(t.requests)

    def test_incomplete_attempt_job_list_is_blocked(self):
        for jobs in (
            {"total_count": 2, "jobs": [job()]},
            {"total_count": 100, "jobs": [job()]*100},
            {"total_count": 2, "jobs": [job(), job()]},
            {"total_count": 1, "jobs": [{"name": "other", "id": JOBID}]},
        ):
            t = Transport(jobs=jobs)
            with self.subTest(jobs=jobs["total_count"]), self.assertRaises(AttestationBlocked):
                self.evaluate(transport=t)

    def test_pending_or_wrong_job_sha_denies_positive_result(self):
        for change in ({"conclusion": "cancelled"},
                       {"head_sha": "c"*40},
                       {"run_id": RUN + 1},
                       {"steps": [{"name": "Execute isolated test in network-off Docker",
                                   "status": "completed", "conclusion": "skipped"}]}):
            j = job()
            j.update(change)
            with self.subTest(change=change), self.assertRaises(AttestationBlocked):
                self.evaluate(transport=Transport(jobs={"total_count": 1, "jobs": [j]}))

    def test_wrong_repo_run_attempt_or_sha_denied(self):
        for update in (
            {"run_attempt": 1},
            {"head_sha": "c"*40},
            {"head_branch": "feature"},
            {"event": "push"},
            {"repository": {"full_name": "another/repo"}},
            {"path": ".github/workflows/serenity-candidate-sandbox.yml@refs/heads/feature"},
        ):
            rv = run()
            rv.update(update)
            with self.subTest(update=update), self.assertRaises(AttestationBlocked):
                self.evaluate(transport=Transport(runner=rv))

    def test_untrusted_runner_claim_cannot_be_relabelled_as_verified(self):
        record = smoke()
        record["runner_result"]["github_write_permissions"] = True
        with self.assertRaises(AttestationBlocked):
            self.evaluate(record)


if __name__ == "__main__":
    unittest.main()
