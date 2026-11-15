"""Security and restartability tests for Serenity's event journal and remote state."""
import base64
import json
import os
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.checkpoint_store import (
    CheckpointBlocked, append_event, checkpoint_summary, empty_ledger,
    load_local, store_local, validate_ledger,
)
from company.github_checkpoint import (
    GithubCheckpointStore, RemoteStateBlocked, READ_URL, API_URL,
)
from company.shift_coordinator import simulate_two_shifts, propose_shift
from company.model_dispatch import synthetic_snapshot
from company.hosted_inference import MODELS

NOW = datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc)
TASK = "github:Baraka-Hani/Serenity#22"


def one_event(ledger=None, *, eid="issue22-step1", now=NOW, kind="WORK_CHECKPOINT",
              payload=None):
    return append_event(ledger if ledger is not None else empty_ledger(),
                        event_id=eid, kind=kind, actor="operations",
                        shift="shift_1", task_ref=TASK,
                        timestamp=now.isoformat(), payload=payload or
                        {"checkpoint_ref": "module5-company-ledger"})


class Response:
    def __init__(self, value, url):
        self.raw = json.dumps(value).encode("utf-8")
        self.url = url
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, count): return self.raw[:count]
    def geturl(self): return self.url


class Transport:
    def __init__(self, response):
        self.response = response
        self.calls = []
    def open(self, req, timeout):
        self.calls.append(req)
        return Response(self.response, req.full_url)


class DurableCheckpointTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)

    def test_hash_chain_and_atomic_recovery(self):
        path = self.root / "ledger.json"
        old = empty_ledger()
        new = one_event(old)
        saved = store_local(path, new, expected_last_hash=old["last_hash"])
        self.assertEqual(saved["event_count"], 1)
        self.assertEqual(load_local(path), new)
        self.assertEqual(checkpoint_summary(new)["event_count"], 1)
        self.assertFalse(checkpoint_summary(new)["remote_persistence_confirmed"])

    def test_idempotent_replay_same_event(self):
        first = one_event()
        self.assertEqual(one_event(first), first)
        self.assertEqual(len(first["events"]), 1)

    def test_idempotent_replay_different_payload_blocks(self):
        first = one_event()
        with self.assertRaises(CheckpointBlocked):
            one_event(first, payload={"reason_code": "WRONG_EVENT"})

    def test_edit_detected_even_if_json_well_formed(self):
        ledger = one_event()
        ledger["events"][0]["payload"]["checkpoint_ref"] = "tampered"
        with self.assertRaises(CheckpointBlocked):
            validate_ledger(ledger)

    def test_malformed_and_sensitive_payloads_blocked(self):
        with self.assertRaises(CheckpointBlocked):
            one_event(payload={"password": "a"})
        with self.assertRaises(CheckpointBlocked):
            one_event(payload={"checkpoint_ref": "sk-secretvalue"})
        with self.assertRaises(CheckpointBlocked):
            one_event(payload={"reason_code": "Contains\nSecret"})
        with self.assertRaises(CheckpointBlocked):
            one_event(eid="bad id")

    def test_stale_local_write_does_not_erase_newer_snapshot(self):
        path = self.root / "ledger.json"
        first = one_event()
        store_local(path, first, expected_last_hash=empty_ledger()["last_hash"])
        second = one_event(first, eid="issue22-step2",
                           now=NOW+timedelta(minutes=1))
        with self.assertRaises(CheckpointBlocked):
            store_local(path, second, expected_last_hash=empty_ledger()["last_hash"])
        self.assertEqual(load_local(path), first)

    def test_symlink_checkpoint_blocked(self):
        path = self.root / "real.json"
        path.write_text(json.dumps(empty_ledger()))
        link = self.root / "shortcut.json"
        link.symlink_to(path)
        with self.assertRaises(CheckpointBlocked):
            load_local(link)
        with self.assertRaises(CheckpointBlocked):
            store_local(link, one_event(), expected_last_hash=empty_ledger()["last_hash"])

    def test_two_five_hour_shift_persists_handoff(self):
        ledger = simulate_two_shifts(empty_ledger(), day=date(2026, 11, 14))
        self.assertEqual(len(ledger["events"]), 4)
        self.assertEqual([e["kind"] for e in ledger["events"]],
                         ["SHIFT_STARTED", "SHIFT_ENDED", "SHIFT_STARTED", "SHIFT_ENDED"])
        self.assertEqual(ledger["events"][1]["shift"], "shift_1")
        self.assertEqual(ledger["events"][3]["shift"], "shift_2")
        self.assertEqual(len(simulate_two_shifts(ledger, day=date(2026, 11, 14))["events"]), 4)

    def test_unknown_model_quota_blocks_new_work(self):
        from datetime import timezone
        result = propose_shift(empty_ledger(), {}, now=NOW)
        self.assertEqual(result["decision"], "CHECKPOINT")
        self.assertFalse(result["provider_calls_authorized"])
        self.assertFalse(result["github_writes_authorized"])

    def test_wind_down_blocks_new_task(self):
        quota = {v: synthetic_snapshot(v, now=NOW, remaining_fraction=0.08)
                 for v in MODELS.values()}
        result = propose_shift(empty_ledger(), quota, now=NOW)
        self.assertEqual(result["decision"], "WIND_DOWN")
        self.assertFalse(result["provider_calls_authorized"])

    def test_remote_read_verifies_contents_and_hash_chain(self):
        ledger = one_event()
        response = {"type": "file", "path": "state/company-ledger.json",
                    "encoding": "base64", "sha": "a"*40,
                    "content": base64.b64encode(json.dumps(ledger).encode("utf-8")).decode("ascii")}
        client = GithubCheckpointStore(transport=Transport(response))
        data = client.read()
        self.assertEqual(data["ledger"], ledger)
        self.assertEqual(data["remote_git_blob_sha"], "a"*40)

    def test_default_remote_write_blocked_before_transport(self):
        transport = Transport({"commit": {"sha": "b"*40}})
        client = GithubCheckpointStore(token="fake-test-token", transport=transport)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RemoteStateBlocked):
                client.write_once(one_event(), expected_git_blob_sha="a"*40,
                                  owner_setup_approved=True,
                                  spending_approved_no_overages=True)
        self.assertEqual(transport.calls, [])

    def test_remote_no_blind_create_and_requires_scoped_credentials(self):
        client = GithubCheckpointStore(transport=Transport({}))
        with patch.dict(os.environ, {"SERENITY_REMOTE_STATE_WRITE": "true"}):
            with self.assertRaises(RemoteStateBlocked):
                client.write_once(one_event(), expected_git_blob_sha="a"*40,
                                  owner_setup_approved=True,
                                  spending_approved_no_overages=True)
            client.token = "test-only"
            with self.assertRaises(RemoteStateBlocked):
                client.write_once(one_event(), expected_git_blob_sha="",
                                  owner_setup_approved=True,
                                  spending_approved_no_overages=True)

    def test_remote_write_is_hardcoded_to_state_branch_and_path(self):
        transport = Transport({"commit": {"sha": "b"*40}})
        client = GithubCheckpointStore(token="fake-test-token", transport=transport)
        with patch.dict(os.environ, {"SERENITY_REMOTE_STATE_WRITE": "true"}):
            result = client.write_once(one_event(), expected_git_blob_sha="a"*40,
                                       owner_setup_approved=True,
                                       spending_approved_no_overages=True)
        self.assertTrue(result["remote_write_completed"])
        self.assertEqual(len(transport.calls), 1)
        req = transport.calls[0]
        self.assertEqual(req.full_url, API_URL)
        self.assertEqual(req.get_method(), "PUT")
        payload = json.loads(req.data)
        self.assertEqual(payload["branch"], "serenity-company-state")
        self.assertEqual(payload["sha"], "a"*40)
        self.assertEqual(req.full_url, API_URL)

if __name__ == "__main__":
    unittest.main()
