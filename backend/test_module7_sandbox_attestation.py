"""Regression tests for bound but never automatically authoritative sandbox evidence."""
import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from company.sandbox_attestation import (
    AttestationBlocked, WORKFLOW, JOB, create_claim,
    validate_claim, check_github_job,
)

HEAD = "a"*40
IMAGE = "docker.io/library/node:22-bookworm-slim@sha256:" + "f"*64
CANDIDATE_SHA = hashlib.sha256(b"synthetic test case").hexdigest()
APP_SHA = hashlib.sha256(b"synthetic first party app").hexdigest()
SOURCE_SHA = hashlib.sha256(b"synthetic baseline").hexdigest()
SAFE_WORKFLOW_REF = WORKFLOW + "@refs/heads/main"


def fixture():
    return {
        "candidate_sha256": CANDIDATE_SHA,
        "image_digest": IMAGE,
        "passed": True, "returncode": 0,
        "actual_functional_test_executed": True,
        "sandbox": "docker_network_none_readonly_unprivileged",
        "command_template": "node backend/test_destination_picker.js",
        "github_write_permissions": False,
        "stdout_tail": "tests passed", "stderr_tail": "",
    }


def evidence():
    return create_claim(fixture(), head_sha=HEAD, run_id=123,
                        run_attempt=2, job_id=456,
                        source_sha256=SOURCE_SHA, app_sha256=APP_SHA)


def api_records():
    job = {
        "id": 456, "run_id": 123, "head_sha": HEAD, "name": JOB,
        "status": "completed", "conclusion": "success",
        "steps": [{"name": "Execute isolated test in network-off Docker",
                   "status": "completed", "conclusion": "success"}],
    }
    run = {
        "id": 123, "run_attempt": 2, "head_sha": HEAD,
        "status": "completed", "conclusion": "success",
        "event": "workflow_dispatch",
        "path": SAFE_WORKFLOW_REF,
    }
    return job, run


class RunnerAttestationTests(unittest.TestCase):
    def test_manifest_bound_to_exact_candidate_and_finite_run(self):
        record = evidence()
        self.assertEqual(validate_claim(record), record)
        self.assertEqual(record["candidate_sha256"], CANDIDATE_SHA)
        self.assertEqual(record["github"]["run_attempt"], 2)
        self.assertEqual(record["classification"], "UNTRUSTED_RUNNER_CLAIM")
        self.assertEqual(record["workflow"], WORKFLOW)

    def test_trusted_github_job_correspondence_never_authorizes_commit(self):
        job, run = api_records()
        result = check_github_job(
            evidence(), job=job, run=run, expected_head_sha=HEAD,
            approved_workflow_ref=SAFE_WORKFLOW_REF)
        self.assertTrue(result["gitHub_job_correspondence_verified"])
        self.assertFalse(result["test_runner_isolation_independently_attested"])
        self.assertFalse(result["manager_commit_execution_authorized"])
        self.assertFalse(result["automatic_merge_authorized"])

    def test_tampering_claim_is_rejected(self):
        for field, value in (
            ("candidate_sha256", "f"*64), ("passed", False),
            ("image_digest", "docker.io/library/node:22-bookworm-slim@sha256:"+"e"*64),
            ("job_name", "fake-sandbox")):
            with self.subTest(field=field):
                record = evidence()
                record[field] = value
                with self.assertRaises(AttestationBlocked):
                    validate_claim(record)

    def test_non_executed_or_unapproved_runtime_rejected_at_source(self):
        variations = (
            {"actual_functional_test_executed": False},
            {"github_write_permissions": True},
            {"sandbox": "unrestricted_host_process"},
            {"returncode": 1, "passed": True},
            {"command_template": "node malicious.js"},
            {"image_digest": "node:22"},
        )
        for change in variations:
            data = fixture()
            data.update(change)
            with self.subTest(change=change), self.assertRaises(AttestationBlocked):
                create_claim(data, head_sha=HEAD, run_id=123, run_attempt=1,
                             job_id=456, source_sha256=SOURCE_SHA,
                             app_sha256=APP_SHA)

    def test_missing_malformed_required_result_detected(self):
        for field in ("passed", "command_template", "sandbox", "image_digest"):
            data = fixture()
            data.pop(field)
            with self.subTest(field=field), self.assertRaises(AttestationBlocked):
                create_claim(data, head_sha=HEAD, run_id=123, run_attempt=1,
                             job_id=456, source_sha256=SOURCE_SHA,
                             app_sha256=APP_SHA)

    def test_wrong_run_job_or_commit_fails(self):
        for variant in ("bad_job_id", "wrong_job_sha", "wrong_attempt", "bad_run_head",
                        "bad_job_conclusion", "skipped_test_step", "bad_ref", "pull_request_event"):
            job, run = api_records()
            if variant == "bad_job_id":
                job["id"] = 789
            elif variant == "wrong_job_sha":
                job["head_sha"] = "b"*40
            elif variant == "wrong_attempt":
                run["run_attempt"] = 1
            elif variant == "bad_run_head":
                run["head_sha"] = "b"*40
            elif variant == "bad_job_conclusion":
                job["conclusion"] = "failure"
            elif variant == "skipped_test_step":
                job["steps"][0]["conclusion"] = "skipped"
            elif variant == "bad_ref":
                run["path"] = WORKFLOW + "@refs/heads/feature"
            else:
                run["event"] = "pull_request"
            with self.subTest(variant=variant), self.assertRaises(AttestationBlocked):
                check_github_job(
                    evidence(), job=job, run=run, expected_head_sha=HEAD,
                    approved_workflow_ref=SAFE_WORKFLOW_REF)

    def test_never_accept_unprotected_workflow_selection(self):
        job, run = api_records()
        with self.assertRaises(AttestationBlocked):
            check_github_job(evidence(), job=job, run=run,
                             expected_head_sha=HEAD,
                             approved_workflow_ref=WORKFLOW+"@refs/heads/feature")

    def test_fake_json_claim_without_github_records_rejected(self):
        with self.assertRaises(AttestationBlocked):
            check_github_job(evidence(), job=None, run=None,
                             expected_head_sha=HEAD,
                             approved_workflow_ref=SAFE_WORKFLOW_REF)


if __name__ == "__main__":
    unittest.main()
