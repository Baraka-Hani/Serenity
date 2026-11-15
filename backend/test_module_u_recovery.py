"""Module U remote checkpoint recovery / tamper and divergent history tests."""
import base64
import hashlib
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.checkpoint_store import empty_ledger, append_event
from company.github_checkpoint import GithubCheckpointStore, READ_URL
from company.module_u_recovery import inspect_recovery, recovery_markdown

NOW = datetime(2026, 11, 14, 15, tzinfo=timezone.utc)
TASK = "github:Baraka-Hani/Serenity#22"


def append(journal, ident, minute):
    return append_event(
        journal, event_id=ident, kind="WORK_CHECKPOINT", actor="operations",
        shift="shift_1", task_ref=TASK,
        timestamp=(NOW + timedelta(minutes=minute)).isoformat(),
        payload={"checkpoint_ref": "module5-company-ledger"})


def response(ledger, *, corrupt_sha=False, bad_encoding=False):
    raw = json.dumps(ledger, sort_keys=True).encode("utf-8")
    sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()
    return {
        "type": "file", "path": "state/company-ledger.json",
        "sha": "0"*40 if corrupt_sha else sha,
        "size": len(raw), "encoding": "base64",
        "content": "@invalid@" if bad_encoding else base64.b64encode(raw).decode(),
    }


class RemoteResponse:
    def __init__(self, url, data):
        self.url, self.body = url, json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def geturl(self): return self.url
    def read(self, count): return self.body[:count]


class Transport:
    def __init__(self, data):
        self.data, self.calls = data, []
    def open(self, request, timeout):
        self.calls.append((request.get_method(), request.full_url))
        if request.get_method() != "GET" or request.full_url != READ_URL:
            raise AssertionError("unexpected remote state network operation")
        return RemoteResponse(request.full_url, self.data)


class RemoteRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.local = append(empty_ledger(), "issue22-checkpoint-1", 0)

    def read_result(self, remote):
        trans = Transport(response(remote))
        result = inspect_recovery(
            self.local, store=GithubCheckpointStore(transport=trans),
            remote_read_authorized=True)
        self.assertEqual(trans.calls, [("GET", READ_URL)])
        return result

    def test_no_permission_means_no_network(self):
        trans = Transport(response(self.local))
        result = inspect_recovery(
            self.local, store=GithubCheckpointStore(transport=trans))
        self.assertEqual(result["status"], "REMOTE_NOT_OBSERVED")
        self.assertFalse(result["cloud_state_confirmed_durable"])
        self.assertEqual(trans.calls, [])
        self.assertIn("not verified", recovery_markdown(result))

    def test_no_store_blocks_without_network(self):
        result = inspect_recovery(
            self.local, remote_read_authorized=True)
        self.assertEqual(result["status"], "REMOTE_READER_NOT_CONFIGURED")
        self.assertFalse(result["remote_write_authorized"])

    def test_verified_same_remote_head(self):
        result = self.read_result(self.local)
        self.assertEqual(result["status"], "IN_SYNC")
        self.assertTrue(result["cloud_state_confirmed_durable"])
        self.assertEqual(result["local_event_count"], 1)
        self.assertEqual(result["common_events"], 1)
        self.assertEqual(len(result["remote_git_blob_sha"]), 40)
        self.assertFalse(result["remote_write_authorized"])

    def test_remote_ahead_and_local_ahead_are_read_only(self):
        ahead = append(self.local, "issue22-checkpoint-2", 1)
        result = self.read_result(ahead)
        self.assertEqual(result["status"], "REMOTE_AHEAD")
        self.assertEqual(result["remote_event_count"], 2)
        self.assertFalse(result["automatic_merge_authorized"])
        result = self.read_result(empty_ledger())
        self.assertEqual(result["status"], "LOCAL_AHEAD")
        self.assertIn("owner-approved", result["next_action"])
        self.assertFalse(result["remote_write_authorized"])

    def test_diverged_histories_block_without_merging(self):
        remote = append(empty_ledger(), "issue22-other-worker", 0)
        result = self.read_result(remote)
        self.assertEqual(result["status"], "DIVERGED_BLOCKED")
        self.assertEqual(result["common_events"], 0)
        self.assertIn("human", result["next_action"])
        self.assertFalse(result["automatic_merge_authorized"])

    def test_fake_sha_and_corrupt_base64_not_trusted(self):
        for mutation in ({"corrupt_sha": True}, {"bad_encoding": True}):
            trans = Transport(response(self.local, **mutation))
            result = inspect_recovery(
                self.local, store=GithubCheckpointStore(transport=trans),
                remote_read_authorized=True)
            self.assertEqual(result["status"], "REMOTE_READ_BLOCKED")
            self.assertFalse(result["cloud_state_confirmed_durable"])
            self.assertFalse(result["remote_write_authorized"])

    def test_tampered_event_chain_does_not_count_as_valid_cloud_state(self):
        remote = json.loads(json.dumps(self.local))
        remote["events"][0]["payload"]["checkpoint_ref"] = "changed"
        trans = Transport(response(remote))
        result = inspect_recovery(
            self.local, store=GithubCheckpointStore(transport=trans),
            remote_read_authorized=True)
        self.assertEqual(result["status"], "REMOTE_READ_BLOCKED")
        self.assertFalse(result["cloud_state_confirmed_durable"])

    def test_recovery_report_contains_no_secrets_or_remote_writes(self):
        markdown = recovery_markdown(inspect_recovery(self.local))
        self.assertIn("Read-only report", markdown)
        self.assertIn("Unattended AI agents: **DISABLED**", markdown)
        self.assertIn("GitHub state writes: **DISABLED**", markdown)
        self.assertNotIn("GITHUB_TOKEN", markdown)


if __name__ == "__main__":
    unittest.main()
