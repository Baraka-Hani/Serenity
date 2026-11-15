"""No-network provider and quota dispatch contracts for Serenity Module 4."""
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from urllib import error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.hosted_inference import (
    MODELS, ManualContext, ProviderBlocked, _model_payload, call_groq,
    partial_quota,
)
from company.model_dispatch import decide_model, dispatch_pair, synthetic_snapshot, verified_reset

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


class FakeResponse:
    def __init__(self, output, *, url="https://api.groq.com/openai/v1/chat/completions",
                 headers=None):
        self.url = url
        self.headers = headers or {}
        self.blob = json.dumps({
            "choices": [{"message": {"content": json.dumps(output)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        }).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def geturl(self): return self.url
    def read(self, cap): return self.blob[:cap]


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.calls = 0
        self.sent = None
    def open(self, req, *, timeout):
        self.calls += 1
        self.sent = req
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


GOOD = ManualContext(True, True, True, True)


class HostedModelContracts(unittest.TestCase):
    def test_exact_approved_models_and_strict_schema(self):
        for role in ("builder", "reviewer"):
            payload = _model_payload(role, "Follow Serenity architecture and safe policy.", "Public synthetic task.")
            self.assertEqual(payload["model"], MODELS[role])
            self.assertTrue(payload["response_format"]["json_schema"]["strict"])
            self.assertEqual(payload["stream"], False)
            self.assertLessEqual(payload["max_completion_tokens"], 1000)
        self.assertEqual(_model_payload("builder", "Follow safety instructions.", "Public data")["reasoning_effort"], "none")
        self.assertEqual(_model_payload("reviewer", "Follow safety instructions.", "Public data")["reasoning_effort"], "low")

    def test_disabled_without_manual_evidence(self):
        opener = FakeOpener(FakeResponse({"schema_version": 1}))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProviderBlocked):
                call_groq("builder", "Follow the policy.", "Public snippet", ctx=GOOD,
                          api_key="not-a-real-secret", transport=opener)
        self.assertEqual(opener.calls, 0)

    def test_ineligible_account_and_unattended_blocked(self):
        for ctx in (ManualContext(), ManualContext(True, True, True, False),
                    ManualContext(True, True, True, True, unattended=True)):
            opener = FakeOpener(FakeResponse({}))
            with patch.dict(os.environ, {"SERENITY_PROVIDER_MANUAL_LIVE": "true"}):
                with self.assertRaises(ProviderBlocked):
                    call_groq("builder", "Follow all checks.", "Public text",
                              ctx=ctx, api_key="fake", transport=opener)
            self.assertEqual(opener.calls, 0)

    def test_single_authorized_injected_transport_and_no_retries(self):
        sample = {"schema_version": 1, "approved": True}
        opener = FakeOpener(FakeResponse(sample, headers={
            "x-ratelimit-limit-requests":"1000",
            "x-ratelimit-remaining-requests":"80",
            "x-ratelimit-limit-tokens":"8000",
            "x-ratelimit-remaining-tokens":"7000",
        }))
        with patch.dict(os.environ, {"SERENITY_PROVIDER_MANUAL_LIVE":"true"}):
            outcome = call_groq("reviewer", "Follow the trusted policy.", "Public sample.",
                                ctx=GOOD, api_key="test-key", transport=opener)
        self.assertEqual(opener.calls, 1)
        self.assertEqual(outcome["model_id"], "openai/gpt-oss-120b")
        self.assertEqual(outcome["output"], sample)
        self.assertEqual(outcome["usage"]["total_tokens"], 120)
        self.assertFalse(outcome["quota_partial"]["complete"])
        self.assertTrue(outcome["quota_partial"]["windows"][0]["wind_down"])

    def test_429_no_retry_and_no_secret_leak(self):
        exc = error.HTTPError("https://api.groq.com/openai/v1/chat/completions",
                              429, "too many", {}, None)
        opener = FakeOpener(exc)
        with patch.dict(os.environ, {"SERENITY_PROVIDER_MANUAL_LIVE":"true"}):
            with self.assertRaises(ProviderBlocked) as cm:
                call_groq("builder", "Policy instructions.", "Public sample",
                          ctx=GOOD, api_key="sensitive-test-value", transport=opener)
        self.assertEqual(cm.exception.code, "QUOTA")
        self.assertNotIn("sensitive-test-value", str(cm.exception))
        self.assertEqual(opener.calls, 1)

    def test_billing_required_blocks_no_paid_fallback(self):
        exc = error.HTTPError("https://api.groq.com/openai/v1/chat/completions",
                              402, "payment required", {}, None)
        opener = FakeOpener(exc)
        with patch.dict(os.environ, {"SERENITY_PROVIDER_MANUAL_LIVE":"true"}):
            with self.assertRaises(ProviderBlocked) as cm:
                call_groq("builder", "Policy instructions.", "Public sample",
                          ctx=GOOD, api_key="fake", transport=opener)
        self.assertEqual(cm.exception.code, "BILLING_OR_ACCESS")
        self.assertEqual(opener.calls, 1)

    def test_redirected_provider_response_is_rejected(self):
        opener = FakeOpener(FakeResponse({}, url="https://other.example.net/"))
        with patch.dict(os.environ, {"SERENITY_PROVIDER_MANUAL_LIVE":"true"}):
            with self.assertRaises(ProviderBlocked) as cm:
                call_groq("builder", "Policy instructions.", "Public sample",
                          ctx=GOOD, api_key="fake", transport=opener)
        self.assertEqual(cm.exception.code, "REDIRECT")

    def test_missing_and_malformed_quota_headers_fail_closed(self):
        for headers in (None, {"x-ratelimit-limit-tokens": "bad",
                                "x-ratelimit-remaining-tokens":"-1"}):
            status = partial_quota(headers)
            self.assertFalse(status["complete"])
            self.assertFalse(status["automatic_resumption_allowed"])


class QuotaDispatchContracts(unittest.TestCase):
    def good(self, fraction=0.75):
        return {model: synthetic_snapshot(model, now=NOW,
                                          remaining_fraction=fraction)
                for model in MODELS.values()}

    def test_both_models_independently_ready_in_simulation(self):
        result = dispatch_pair(self.good(), now=NOW, estimated_builder_tokens=700,
                               estimated_reviewer_tokens=700)
        self.assertTrue(result["both_ready"])
        self.assertFalse(result["automatic_execution_authorized"])

    def test_no_quota_data_means_blocked(self):
        result = dispatch_pair({}, now=NOW)
        self.assertFalse(result["both_ready"])
        self.assertEqual(result["models"]["builder"]["quota_state"], "UNKNOWN")

    def test_one_model_exhausted_stops_workflow(self):
        snap = self.good()
        snap[MODELS["reviewer"]] = synthetic_snapshot(MODELS["reviewer"], now=NOW,
                                                        remaining_fraction=0.0)
        result = dispatch_pair(snap, now=NOW)
        self.assertFalse(result["both_ready"])
        self.assertTrue(result["models"]["builder"]["accept_work"])
        self.assertEqual(result["models"]["reviewer"]["quota_state"], "EXHAUSTED")

    def test_90_percent_wind_down_and_estimated_call_preserves_reserve(self):
        snap = synthetic_snapshot(MODELS["builder"], now=NOW, remaining_fraction=0.10)
        self.assertFalse(decide_model("builder", snap, now=NOW)["accept_work"])
        pre_threshold = synthetic_snapshot(MODELS["builder"], now=NOW,
                                            remaining_fraction=0.25)
        decision = decide_model("builder", pre_threshold, now=NOW,
                                estimated_token_cost=1900)
        self.assertEqual(decision["status"], "WIND_DOWN")
        self.assertFalse(decision["accept_work"])

    def test_headers_or_mock_cannot_start_live_task(self):
        snap = synthetic_snapshot(MODELS["builder"], now=NOW, remaining_fraction=0.75)
        self.assertFalse(decide_model("builder", snap, now=NOW,
                                      manual_live=True)["accept_work"])
        snap["source"] = "provider_headers"
        self.assertFalse(decide_model("builder", snap, now=NOW,
                                      manual_live=True)["accept_work"])

    def test_losing_any_quota_bucket_blocks(self):
        snap = synthetic_snapshot(MODELS["builder"], now=NOW)
        snap["limits"].pop()
        self.assertFalse(decide_model("builder", snap, now=NOW)["accept_work"])

    def test_no_clock_only_reset(self):
        previous = synthetic_snapshot(MODELS["builder"], now=NOW, remaining_fraction=0.05)
        after = synthetic_snapshot(MODELS["builder"], now=NOW+timedelta(minutes=2),
                                    remaining_fraction=0.75)
        self.assertFalse(verified_reset(previous, after,
                                        now=NOW+timedelta(minutes=2))["resume"])

    def test_weekly_and_subscription_are_not_shared_with_groq(self):
        result = dispatch_pair(self.good(), now=NOW)
        self.assertEqual(set(result["models"]), {"builder", "reviewer"})
        self.assertFalse(result["automatic_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
