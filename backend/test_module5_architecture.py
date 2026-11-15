"""Regression checks for Serenity's architecture and travel loop boundaries."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from company.architecture_contracts import (
    ArchitectureBlocked, validate_low_risk_destination_scope,
)

REQUIRED = [
    "docs/ARCHITECTURE.md",
    "backend/server.py",
    "destination-picker.js",
    "backend/test_destination_picker.js",
    "config/module4_destination_task.json",
]


class ArchitectureContracts(unittest.TestCase):
    def test_current_product_loop_static_contract(self):
        result = validate_low_risk_destination_scope(ROOT)
        self.assertTrue(result["static_contracts_pass"])
        self.assertFalse(result["full_functional_testing_proven"])
        self.assertFalse(result["privacy_review_complete"])
        self.assertEqual(result["target_path"], "backend/test_destination_picker.js")

    def test_direct_third_party_picker_request_would_be_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in REQUIRED:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, dest)
            file = root / "destination-picker.js"
            original = file.read_text(encoding="utf-8")
            file.write_text(original.replace("fetch(`/api/places/search?q=",
                                             "fetch(`https://thirdparty.example/search?q="))
            with self.assertRaises(ArchitectureBlocked):
                validate_low_risk_destination_scope(root)

    def test_scope_unauthorized_backend_change_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in REQUIRED:
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, dest)
            path = root / "config/module4_destination_task.json"
            source = path.read_text(encoding="utf-8")
            path.write_text(source.replace(
                "backend/test_destination_picker.js", "backend/server.py"))
            with self.assertRaises(ArchitectureBlocked):
                validate_low_risk_destination_scope(root)

if __name__ == "__main__":
    unittest.main()
