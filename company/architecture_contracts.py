"""Serenity travel-product architectural smoke contracts (read-only).

These checks guard the minimum product loop while Engineering's agent
workforce is being developed. They complement, not replace, end-to-end
functional, security or privacy tests.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TASK = "backend/test_destination_picker.js"


class ArchitectureBlocked(ValueError):
    pass


def validate_low_risk_destination_scope(root=ROOT):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ArchitectureBlocked("source root must be ordinary directory")
    required = ("docs/ARCHITECTURE.md", "backend/server.py",
                "destination-picker.js", "backend/test_destination_picker.js",
                "config/module4_destination_task.json")
    code = {}
    for name in required:
        target = root / name
        if target.is_symlink() or not target.is_file():
            raise ArchitectureBlocked("missing or linked architecture source")
        size = target.stat().st_size
        if not 0 < size < 80000:
            raise ArchitectureBlocked("unexpected source size")
        code[name] = target.read_text(encoding="utf-8")
    policy = code["docs/ARCHITECTURE.md"]
    backend = code["backend/server.py"]
    picker = code["destination-picker.js"]
    test = code["backend/test_destination_picker.js"]
    try:
        task = json.loads(code["config/module4_destination_task.json"])
    except (json.JSONDecodeError, TypeError):
        raise ArchitectureBlocked("invalid task manifest") from None
    if task.get("target_path") != EXPECTED_TASK or task.get("risk") != "low":
        raise ArchitectureBlocked("pilot scope no longer limited to low-risk tests")
    if ("Python standard-library server" not in policy
            or "React + TypeScript + Vite" not in policy
            or "localhost" not in policy):
        raise ArchitectureBlocked("main app/prototype boundaries changed")
    if 'os.environ.get("ROAM_HOST", "127.0.0.1")' not in backend:
        raise ArchitectureBlocked("backend no longer binds locally by default")
    if "fetch(`/api/places/search?q=" not in picker:
        raise ArchitectureBlocked("destination picker no longer uses local places API")
    if "Search must be explicit and go through the local API" not in test:
        raise ArchitectureBlocked("first-party request regression baseline missing")
    if "Zero latitude/longitude are valid" not in test:
        raise ArchitectureBlocked("zero-coordinate map regression baseline missing")
    return {
        "source_trust": "checked_out_repository_static_contract",
        "target_path": EXPECTED_TASK, "read_only": True,
        "cross_module_boundaries": ["PWA destination picker -> local Python API",
                                   "map includes zero coordinates",
                                   "React/Firebase prototype remains separate"],
        "authentication_or_private_data_exposed": False,
        "static_contracts_pass": True,
        "full_functional_testing_proven": False,
        "privacy_review_complete": False,
        "production_deployment_authorized": False,
    }
