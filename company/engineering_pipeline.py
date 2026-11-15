"""Serenity Engineering: offline, end-to-end issue -> patch -> QA -> owner gate.

This deliberately DOES NOT invoke a model, run untrusted generated code,
connect to GitHub, or change the source repository. No live mode exists.
A verified, independently authorized cloud executor is a future component.
"""
import argparse
import ast
import difflib
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from company.office import CompanyOffice
from company.obsidian import export_vault

# Narrow initial allowlist. New real Serenity code paths must be approved in
# an independently reviewed policy change; issue descriptions do NOT grant scope.
SAFE_PATHS = frozenset({"company/fixtures/destination_label.py"})
MAX_BYTES = 6000
MAX_JSON_BYTES = 12000
MODEL_PLAN = {"builder": "qwen/qwen3.8-27b", "reviewer": "openai/gpt-oss-120b"}
VALID_RUN_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{2,80}$")
UNSAFE_CALLS = {"exec", "eval", "compile", "open", "input", "__import__", "globals",
                "locals", "getattr", "setattr", "delattr", "breakpoint"}


class EngineeringBlocked(ValueError):
    """Safe failure requiring review or policy change."""


def sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_string(value, max_chars):
    if not isinstance(value, str) or not value.strip() or len(value) > max_chars:
        raise EngineeringBlocked("missing or oversized required text")
    if "\x00" in value or "\r" in value:
        raise EngineeringBlocked("unexpected control character")
    return value


def _path(path):
    if not isinstance(path, str) or "\\" in path or "\x00" in path:
        raise EngineeringBlocked("unsafe path syntax")
    pure = PurePosixPath(path)
    if (pure.is_absolute() or str(pure) != path
            or any(part in ("", ".", "..") or part.startswith(".") for part in pure.parts)
            or path not in SAFE_PATHS):
        raise EngineeringBlocked("file is not in the fixed engineering pilot allowlist")
    return pure


def safe_read(root, path):
    relative = _path(path)
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise EngineeringBlocked("source root must be a real directory")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise EngineeringBlocked("symlink in source path")
    if not current.is_file():
        raise EngineeringBlocked("allowlisted source file missing")
    raw = current.read_bytes()
    if len(raw) > MAX_BYTES:
        raise EngineeringBlocked("source exceeds context size cap")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        raise EngineeringBlocked("source is not UTF-8") from None


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise EngineeringBlocked("manifest must be an object")
    required = {"schema_version", "run_key", "source_kind", "title",
                "acceptance", "risk", "department", "target_path", "simulation_only"}
    if set(manifest) != required:
        raise EngineeringBlocked("unexpected or missing manifest keys")
    if manifest["schema_version"] != 1 or manifest["simulation_only"] is not True:
        raise EngineeringBlocked("only explicit offline demonstration manifests are supported")
    if not isinstance(manifest["run_key"], str) or not VALID_RUN_KEY.fullmatch(manifest["run_key"]):
        raise EngineeringBlocked("invalid run key")
    if manifest["source_kind"] != "synthetic_issue_fixture":
        raise EngineeringBlocked("real issue inputs require a separate owner-authorized adapter")
    if manifest["risk"] != "low" or manifest["department"] != "engineering":
        raise EngineeringBlocked("engineering pilot allows low-risk tasks only")
    _bounded_string(manifest["title"], 160)
    _bounded_string(manifest["acceptance"], 600)
    _path(manifest["target_path"])
    return manifest


def mock_builder(manifest, original):
    """Deterministic fixture change; not a simulated actual Qwen response."""
    if manifest["target_path"] != "company/fixtures/destination_label.py":
        raise EngineeringBlocked("unknown demonstration target")
    old = "def destination_label(title):"
    new = "def destination_label(title: str) -> str:"
    if original.count(old) != 1:
        raise EngineeringBlocked("expected fixture text is missing or duplicated")
    content = original.replace(old, new)
    return {
        "schema_version": 1,
        "run_key": manifest["run_key"],
        "changes": [{
            "path": manifest["target_path"],
            "expected_sha256": sha256(original),
            "replacement_text": content,
        }],
        "simulated_builder": True,
    }


def validate_proposal(proposal, manifest, root):
    """Fail-closed full-file replacement, not shell commands or arbitrary diffs."""
    if not isinstance(proposal, dict) or set(proposal) != {
            "schema_version", "run_key", "changes", "simulated_builder"}:
        raise EngineeringBlocked("unexpected patch schema")
    if (proposal["schema_version"] != 1 or proposal["run_key"] != manifest["run_key"]
            or proposal["simulated_builder"] is not True):
        raise EngineeringBlocked("patch identity or offline-source mismatch")
    changes = proposal["changes"]
    if not isinstance(changes, list) or len(changes) != 1:
        raise EngineeringBlocked("exactly one bounded file replacement allowed")
    change = changes[0]
    if not isinstance(change, dict) or set(change) != {
            "path", "expected_sha256", "replacement_text"}:
        raise EngineeringBlocked("invalid replacement object")
    path = change["path"]
    if path != manifest["target_path"]:
        raise EngineeringBlocked("patch exceeds task target")
    original = safe_read(root, path)
    if change["expected_sha256"] != sha256(original):
        raise EngineeringBlocked("source hash mismatch (stale patch)")
    replacement = change["replacement_text"]
    if not isinstance(replacement, str) or not replacement.endswith("\n"):
        raise EngineeringBlocked("invalid source replacement")
    if (not replacement or "\x00" in replacement or "\r" in replacement
            or len(replacement.encode("utf-8")) > MAX_BYTES):
        raise EngineeringBlocked("replacement exceeds code size cap")
    if replacement == original:
        raise EngineeringBlocked("no changes proposed")
    try:
        tree = ast.parse(replacement, filename=path)
    except SyntaxError:
        raise EngineeringBlocked("proposed Python code fails syntax parsing") from None
    # This is a conservative *static screen*, not a general security
    # proof. Generated code is NEVER executed in this first pipeline.
    if any(isinstance(n, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal))
           or isinstance(n, ast.Call) and (
               isinstance(n.func, ast.Name) and n.func.id in UNSAFE_CALLS
               or isinstance(n.func, ast.Attribute) and n.func.attr in UNSAFE_CALLS)
           for n in ast.walk(tree)):
        raise EngineeringBlocked("proposed code contains restricted constructs")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise EngineeringBlocked("only one pure function definition permitted")
    if tree.body[0].name != "destination_label":
        raise EngineeringBlocked("unexpected function entry point")
    return {"path": path, "original": original, "replacement": replacement}


def offline_review(validated):
    """A separate deterministic QA gate, NOT a GPT-OSS model review."""
    before = validated["original"]
    after = validated["replacement"]
    finding = []
    if "def destination_label(title: str) -> str:" not in after:
        finding.append("Expected type contract not present")
    if "return \" \".join(title.split())" not in after:
        finding.append("Fixture behavior was altered")
    if before.count("return ") != after.count("return "):
        finding.append("Return statement count changed")
    if len(after) > len(before) + 120:
        finding.append("Unexpectedly large addition")
    return {
        "reviewer_type": "offline_deterministic_rules",
        "actual_ai_reviewer_called": False,
        "recommendation": "PASS_STATIC_SCREEN" if not finding else "CHANGES_REQUIRED",
        "findings": finding,
        "verification": ["source SHA-256", "allowlist", "Python AST parse",
                         "restricted construct scan", "fixture behavior source check"],
        "functional_tests_executed": False,
        "security_assurance": "No untrusted generated code executed; not a security audit",
    }


def safe_output_directory(path):
    target = Path(path)
    # Must create a NEW isolated artifact root, never clean an existing one.
    if target.exists() or target.is_symlink():
        raise EngineeringBlocked("artifact output directory must not already exist")
    for parent in target.parents:
        if parent.exists() and parent.is_symlink():
            raise EngineeringBlocked("artifact parent is symbolic link")
    target.mkdir(parents=True, exist_ok=False)
    return target


def run_offline(manifest, *, source_root, artifact_root, db_path):
    manifest = validate_manifest(manifest)
    source = safe_read(source_root, manifest["target_path"])
    office = CompanyOffice(db_path)
    try:
        # Prevent replay side effects: no duplicate tasks/messages/approvals.
        existing = office.db.execute(
            "SELECT id FROM engineering_runs WHERE run_key=?", (manifest["run_key"],)).fetchone()
        if existing is not None:
            raise EngineeringBlocked("run key already processed; inspect prior evidence")
        proposal = mock_builder(manifest, source)
        validated = validate_proposal(proposal, manifest, source_root)
        review = offline_review(validated)
        out = safe_output_directory(artifact_root)
        scratch = out / "isolated-worktree"
        target = scratch / manifest["target_path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(validated["replacement"], encoding="utf-8")
        # Check source remains unchanged (source repository must be untouched).
        if sha256(safe_read(source_root, manifest["target_path"])) != sha256(source):
            raise EngineeringBlocked("source unexpectedly changed; stop")
        diff = "".join(difflib.unified_diff(
            source.splitlines(keepends=True), validated["replacement"].splitlines(keepends=True),
            fromfile="a/"+manifest["target_path"], tofile="b/"+manifest["target_path"]))
        (out / "proposed.patch").write_text(diff, encoding="utf-8")
        (out / "patch-proposal.json").write_text(
            json.dumps(proposal, indent=2)+"\n", encoding="utf-8")
        (out / "qa-review.json").write_text(json.dumps(review, indent=2)+"\n", encoding="utf-8")
        with office.db:
            task_id = office.new_task(manifest["title"], "engineering", manifest["acceptance"])
            office.transition(task_id, "EVALUATED", "Offline fixture only, not real owner-approved work")
            office.assign(task_id, "lead-builder")
            office.transition(task_id, "QUEUED", "Queued within isolated demonstration only")
            office.transition(task_id, "IN_PROGRESS", "Deterministic patch generated without model calls")
            office.checkpoint(task_id, "Patch and static checks saved as ephemeral artifact; no actual code executed")
            msg_id = office.send_message(
                task_id, "lead-builder", "qa-director",
                "Mock patch ready; inspect static validation and proposed diff")
            office.transition(task_id, "IN_REVIEW", "Offline rule-based QA stage")
            office.acknowledge(msg_id, "qa-director")
            office.send_message(task_id, "qa-director", "chief-of-staff",
                                "Static review: " + review["recommendation"] +
                                "; not an AI review or executed functional test")
            status = "SIMULATED_REVIEW_PENDING_OWNER"
            if review["recommendation"] == "PASS_STATIC_SCREEN":
                office.transition(task_id, "VERIFIED", "Static-only checks verified; functional tests not run")
                office.transition(task_id, "AWAITING_OWNER_ACTION", "Owner may inspect artifact; never auto-merge")
                office.request_approval(
                    task_id, "merge",
                    "Illustrative only. No PR exists. Actual code tests, AI QA and human sign-off still required.")
            else:
                status = "SIMULATED_CHANGES_REQUIRED"
                office.checkpoint(task_id, "Offline review requested changes; not suitable for owner merge")
            report = {
                "schema_version": 1,
                "run_key": manifest["run_key"],
                "source_kind": manifest["source_kind"],
                "mode": "offline_fixture_only",
                "status": status,
                "task_id": task_id,
                "issue_reference": "synthetic, not a real GitHub issue",
                "source_path": manifest["target_path"],
                "original_sha256": sha256(source),
                "proposed_sha256": sha256(validated["replacement"]),
                "builder_actual": "deterministic fixture",
                "reviewer_actual": review["reviewer_type"],
                "future_models": MODEL_PLAN,
                "checks": review["verification"],
                "functional_tests_executed": False,
                "model_requests": 0,
                "provider_cost_usd": 0,
                "github_repository_writes": False,
                "model_execution_authorized": False,
                "automatic_merges_or_deploys": False,
                "owner_decision_required": True,
                "next_gate": "Approved, sandboxed real code/test worker and independent actual model reviewer",
            }
            office.db.execute(
                """INSERT INTO engineering_runs(task_id,run_key,mode,status,source_sha256,
                   patch_sha256,report_json,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (task_id, manifest["run_key"], "offline_fixture_only", status,
                 report["original_sha256"], report["proposed_sha256"],
                 json.dumps(report, sort_keys=True), office.snapshot()["generated_at"]))
            office._event("engineering_pipeline", task_id, "engineering",
                          "Offline proposed patch + QA evidence; no real provider calls")
        (out / "engineering-report.json").write_text(
            json.dumps(report, indent=2)+"\n", encoding="utf-8")
        hq = export_vault(office, out / "obsidian-vault")
        result = {**report, "evidence": {
            "patch": "proposed.patch", "proposal": "patch-proposal.json",
            "review": "qa-review.json", "report": "engineering-report.json",
            "hq": hq["output_directory"]}}
        return result
    finally:
        office.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True, help="explicit synthetic offline task fixture")
    parser.add_argument("--source-root", type=Path, required=True, help="checked out read-only source")
    parser.add_argument("--artifact-root", type=Path, required=True, help="new, empty output directory")
    parser.add_argument("--db", type=Path, required=True, help="private SQLite operational ledger")
    args = parser.parse_args(argv)
    try:
        if args.task.stat().st_size > MAX_JSON_BYTES:
            raise EngineeringBlocked("task manifest exceeds 12 KB")
        manifest = json.loads(args.task.read_text(encoding="utf-8"))
        result = run_offline(manifest, source_root=args.source_root,
                             artifact_root=args.artifact_root, db_path=args.db)
    except (EngineeringBlocked, ValueError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, "BLOCKED: " + str(error)+"\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
