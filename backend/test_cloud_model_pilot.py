"""Network-free safety tests for the one-call cloud pilot."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cloud_model_pilot", ROOT / "tools" / "cloud_model_pilot.py")
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)
CONFIG = json.loads((ROOT / "config" / "ai_company_models.json").read_text(encoding="utf-8"))


class CloudPilotTests(unittest.TestCase):
    def test_default_mock_has_no_network_or_repository_access(self):
        def forbidden(*args, **kwargs):
            self.fail("network should never be used in default mode")
        with patch.object(pilot.request, "urlopen", side_effect=forbidden):
            for role in ("builder", "reviewer"):
                r = pilot.run_pilot(CONFIG, role=role, mode="mock", environ={})
                self.assertEqual(r["status"], "SIMULATED")
                self.assertTrue(r["requires_owner_review"])
                self.assertFalse(r["automatic_new_work_allowed"])
                self.assertFalse(r["executed_generated_code"])
                self.assertFalse(r["repository_writes"])

    def test_expected_approved_model_ids(self):
        self.assertEqual(pilot.model_for(CONFIG, "builder"), "qwen/qwen3.8-27b")
        self.assertEqual(pilot.model_for(CONFIG, "reviewer"), "openai/gpt-oss-120b")

    def test_unauthorized_live_call_blocks_without_transport(self):
        def forbidden(*args, **kwargs):
            self.fail("transport should not be invoked")
        for env in ({}, {"SERENITY_PILOT_APPROVED": "true"},
                    {"SERENITY_GROQ_FREE_VERIFIED": "true"}):
            with self.subTest(env=env), self.assertRaises(pilot.PilotBlocked):
                pilot.run_pilot(CONFIG, role="builder", mode="live",
                                environ=env, transport=forbidden)

    def test_approved_live_invokes_only_one_synthetic_call(self):
        seen = []
        def stub(payload, *, api_key):
            seen.append((payload, api_key))
            return {"response_excerpt": "PROPOSAL: test only",
                    "quota": {"complete": False, "automatic_new_work_allowed": False}}
        env = {"SERENITY_PILOT_APPROVED": "true",
               "SERENITY_GROQ_FREE_VERIFIED": "true", "GROQ_API_KEY": "test-fake-key"}
        r = pilot.run_pilot(CONFIG, role="builder", mode="live", environ=env, transport=stub)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1], "test-fake-key")
        self.assertIn("SYNTHETIC CODE", seen[0][0]["messages"][1]["content"])
        self.assertEqual(r["status"], "PROPOSAL_ONLY")
        self.assertFalse(r["automatic_new_work_allowed"])

    def test_model_spoofing_blocked(self):
        other = json.loads(json.dumps(CONFIG))
        other["models"][0]["model_id"] = "unapproved-model"
        with self.assertRaises(pilot.PilotBlocked):
            pilot.run_pilot(other, role="builder", mode="mock", environ={})

    def test_unknown_role_blocked(self):
        with self.assertRaises(pilot.PilotBlocked):
            pilot.run_pilot(CONFIG, role="chief_executive", mode="mock", environ={})

    def test_policy_change_blocks(self):
        changed = json.loads(json.dumps(CONFIG))
        changed["policies"]["can_make_paid_calls"] = True
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "config.json"
            file.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(pilot.PilotBlocked):
                pilot.load_config(file)

    def test_quota_headers_90_percent_guard_and_incomplete_telemetry(self):
        result = pilot.observed_quota({
            "x-ratelimit-limit-requests": "1000",
            "x-ratelimit-remaining-requests": "100",
            "x-ratelimit-reset-requests": "4h",
            "x-ratelimit-limit-tokens": "8000",
            "x-ratelimit-remaining-tokens": "5000",
        })
        self.assertFalse(result["complete"])
        self.assertFalse(result["automatic_new_work_allowed"])
        self.assertTrue(result["observed_windows"][0]["at_or_over_90_percent"])
        self.assertFalse(result["observed_windows"][1]["at_or_over_90_percent"])

    def test_malformed_quota_headers_never_authorize(self):
        result = pilot.observed_quota({
            "x-ratelimit-limit-tokens": "abc",
            "x-ratelimit-remaining-tokens": "-100",
        })
        self.assertEqual(result["observed_windows"], [])
        self.assertFalse(result["automatic_new_work_allowed"])

    def test_requested_output_is_bounded(self):
        for role in ("builder", "reviewer"):
            payload = pilot.create_payload(pilot.model_for(CONFIG, role), role)
            self.assertLessEqual(payload["max_completion_tokens"], 500)
            self.assertNotIn("backend/data", payload["messages"][1]["content"])

if __name__ == "__main__":
    unittest.main()
