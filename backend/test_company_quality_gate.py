"""Contract tests for delegated, quality-first manager authority."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.quality_gate import MANDATORY_CHECKS, QualityPolicyError, evaluate_manager_action


def evidence(action="branch_commit"):
    return {
        "action": action,
        "risk": "low",
        "changed_files": ["company/fixtures/destination_label.py"],
        "product_purpose": "documented",
        "architecture_alignment": "verified",
        "acceptance_met": True,
        "rollback_documented": True,
        "new_financial_exposure": False,
        "independent_reviewer": "approved",
        "checks": {name: "pass" for name in MANDATORY_CHECKS},
        "ci_conclusion": "success",
        "ci_url": "https://github.com/Baraka-Hani/Serenity/actions/runs/123",
        "qa_conclusion": "approve",
        "qa_url": "https://github.com/Baraka-Hani/Serenity/pull/21",
        "provider_allowance": "unused",
        "branch_protection": "enforced",
        "integration_smoke": "pass",
    }


class QualityGateTests(unittest.TestCase):
    def test_manager_can_commit_only_after_all_quality_checks(self):
        x = evaluate_manager_action(evidence())
        self.assertTrue(x["manager_may_commit_after_verified_gates"])
        self.assertEqual(x["status"], "MANAGER_POLICY_ELIGIBLE_PENDING_TRUSTED_INTEGRATION")
        self.assertFalse(x["owner_approval_required"])
        self.assertFalse(x["execution_authorized"])

    def test_manager_can_draft_pr_after_all_checks(self):
        x = evaluate_manager_action(evidence("draft_pr"))
        self.assertTrue(x["manager_may_commit_after_verified_gates"])

    def test_merge_needs_branch_rules_and_integration_smoke(self):
        x = evaluate_manager_action(evidence("protected_merge"))
        self.assertTrue(x["manager_may_commit_after_verified_gates"])
        bad = evidence("protected_merge")
        bad["integration_smoke"] = "missing"
        self.assertFalse(evaluate_manager_action(bad)["manager_may_commit_after_verified_gates"])
        bad["integration_smoke"] = "pass"
        bad["branch_protection"] = "unknown"
        self.assertFalse(evaluate_manager_action(bad)["manager_may_commit_after_verified_gates"])

    def test_approvals_are_reserved_to_owner_for_real_risks(self):
        for action in ("spending", "credentials", "production_deployment",
                       "public_release", "production_data", "strategic_change",
                       "external_publication"):
            with self.subTest(action=action):
                decision = evaluate_manager_action({"action": action})
                self.assertTrue(decision["owner_approval_required"])
                self.assertEqual(decision["status"], "OWNER_APPROVAL_REQUIRED")
                self.assertFalse(decision["execution_authorized"])

    def test_financial_exposure_always_routes_to_owner(self):
        record = evidence()
        record["new_financial_exposure"] = True
        decision = evaluate_manager_action(record)
        self.assertTrue(decision["owner_approval_required"])
        self.assertFalse(decision["manager_may_commit_after_verified_gates"])

    def test_failed_or_missing_check_blocks_commit(self):
        for key in MANDATORY_CHECKS:
            record = evidence()
            record["checks"][key] = "fail"
            with self.subTest(key=key):
                self.assertFalse(evaluate_manager_action(record)["manager_may_commit_after_verified_gates"])

    def test_critical_files_are_not_auto_committed(self):
        for file in (".github/workflows/ci.yml", "backend/auth.py",
                     "backend/data/something.py", "AGENTS.md",
                     "nomad-canvas/firebase.ts", "app/payment.ts",
                     "../README.md", "/etc/passwd", "company/secrets/token.txt"):
            record = evidence()
            record["changed_files"] = [file]
            with self.subTest(file=file):
                self.assertFalse(evaluate_manager_action(record)["manager_may_commit_after_verified_gates"])

    def test_reviewer_and_ci_must_be_independent_and_green(self):
        for field, value in (("independent_reviewer", "builder"),
                             ("qa_conclusion", "request_changes"),
                             ("ci_conclusion", "pending"),
                             ("architecture_alignment", "unverified"),
                             ("rollback_documented", False),
                             ("acceptance_met", False)):
            record = evidence()
            record[field] = value
            with self.subTest(field=field):
                self.assertFalse(evaluate_manager_action(record)["manager_may_commit_after_verified_gates"])

    def test_outside_urls_do_not_count_as_proof(self):
        for link in ("https://evil.example.com/green", "http://github.com/Baraka-Hani/Serenity",
                     "https://github.com.attacker.com/Baraka-Hani/Serenity",
                     "https://github.com@evil.com/Baraka-Hani/Serenity"):
            record = evidence()
            record["ci_url"] = link
            with self.subTest(link=link):
                self.assertFalse(evaluate_manager_action(record)["manager_may_commit_after_verified_gates"])

    def test_medium_and_high_risk_require_human_specialist(self):
        for level in ("medium", "high"):
            record = evidence()
            record["risk"] = level
            self.assertFalse(evaluate_manager_action(record)["manager_may_commit_after_verified_gates"])

    def test_unknown_action_or_invalid_record_rejected(self):
        with self.assertRaises(QualityPolicyError):
            evaluate_manager_action({"action": "self_issue_permissions"})
        with self.assertRaises(QualityPolicyError):
            evaluate_manager_action([])

    def test_company_ledger_records_quality_gate_without_executing(self):
        import tempfile
        from company.office import CompanyOffice
        with tempfile.TemporaryDirectory() as temp:
            office = CompanyOffice(Path(temp) / "quality.sqlite3")
            try:
                task = office.new_task("Review a safe helper", "engineering",
                                       "Relevant code tests pass", risk="low")
                decision = office.evaluate_manager_gate(task, evidence())
                self.assertEqual(decision["status"],
                                 "MANAGER_POLICY_ELIGIBLE_PENDING_TRUSTED_INTEGRATION")
                self.assertFalse(decision["execution_authorized"])
                self.assertEqual(len(office.rows("manager_quality_checks")), 1)
                self.assertFalse(office.snapshot()["execution_enabled"])
                from company.obsidian import export_vault
                out = Path(temp) / "vault"
                export_vault(office, out)
                note = (out / "Serenity HQ" / "Manager Quality Gates.md").read_text()
                self.assertIn("MANAGER_POLICY_ELIGIBLE", note.replace("\\\\_", "_"))
                self.assertIn("advisory", note)
            finally:
                office.close()

    def test_ledger_rejects_mismatched_risk_evidence(self):
        import tempfile
        from company.office import CompanyOffice
        with tempfile.TemporaryDirectory() as temp:
            office = CompanyOffice(Path(temp) / "quality.sqlite3")
            try:
                task = office.new_task("Sensitive work", "engineering",
                                       "Must not auto-approve", risk="high")
                with self.assertRaises(ValueError):
                    office.evaluate_manager_gate(task, evidence())
            finally:
                office.close()

    def test_no_user_approval_each_good_routine_change(self):
        x = evaluate_manager_action(evidence())
        self.assertFalse(x["owner_approval_required"])
        self.assertTrue(x["manager_may_commit_after_verified_gates"])
        # This evaluator never executes code/GitHub writes itself.
        self.assertFalse(x["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
