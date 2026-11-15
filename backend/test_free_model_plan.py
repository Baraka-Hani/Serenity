"""Offline contract tests for Serenity's zero-spend model-routing proposal."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("free_model_plan", ROOT / "tools" / "free_model_plan.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
CONFIG = json.loads((ROOT / "config" / "ai_company_models.json").read_text(encoding="utf-8"))

class FreeModelRoutingTests(unittest.TestCase):
    def test_allowed_docs_task_is_only_a_proposal(self):
        result = module.route(CONFIG, task_type="docs", risk="low", prompt_characters=500)
        self.assertEqual(result["execution"], "DISABLED_OFFLINE_SIMULATION")
        self.assertEqual(result["builder_model_id"], "qwen/qwen3.8-27b")
        self.assertEqual(result["reviewer_model_id"], "openai/gpt-oss-120b")
        self.assertTrue(result["human_review_required"])
        self.assertFalse(result["allowed_to_spend"])
        self.assertFalse(result["allowed_to_merge"])
        self.assertFalse(result["allowed_to_deploy"])

    def test_tests_and_scaffold_allowed(self):
        for kind in ("tests", "scaffold", "low_risk_refactor"):
            with self.subTest(kind=kind):
                self.assertEqual(module.route(CONFIG, task_type=kind, risk="low")["task_type"], kind)

    def test_high_risk_blocked(self):
        with self.assertRaises(module.PolicyError):
            module.route(CONFIG, task_type="docs", risk="high")

    def test_sensitive_tasks_blocked(self):
        for kind in ("auth", "payments", "privacy", "location_history", "secrets", "deployment", "data_migration", "production"):
            with self.subTest(kind=kind), self.assertRaises(module.PolicyError):
                module.route(CONFIG, task_type=kind, risk="low")

    def test_unknown_task_blocked(self):
        with self.assertRaises(module.PolicyError):
            module.route(CONFIG, task_type="new_feature", risk="low")

    def test_prompt_cap(self):
        with self.assertRaises(module.PolicyError):
            module.route(CONFIG, task_type="docs", risk="low", prompt_characters=12001)

    def test_output_cap(self):
        with self.assertRaises(module.PolicyError):
            module.route(CONFIG, task_type="docs", risk="low", proposed_output_tokens=1001)

    def test_negative_values_blocked(self):
        for key in ("prompt_characters", "proposed_output_tokens"):
            with self.subTest(key=key), self.assertRaises(module.PolicyError):
                module.route(CONFIG, task_type="docs", risk="low", **{key: -1})

    def test_enabling_execution_breaks_simulator(self):
        enabled = json.loads(json.dumps(CONFIG))
        enabled["future_execution"]["enabled"] = True
        with self.assertRaises(module.PolicyError):
            module.route(enabled, task_type="docs", risk="low")

    def test_model_roles_must_both_be_present(self):
        missing = json.loads(json.dumps(CONFIG))
        missing["models"].pop()
        with self.assertRaises(module.PolicyError):
            module.route(missing, task_type="docs", risk="low")

if __name__ == "__main__":
    unittest.main()
