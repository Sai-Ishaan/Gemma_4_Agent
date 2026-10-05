#!/usr/bin/env python3
"""
Phase 1 Local Guardrail Test Harness (mock_agent.py)
Auto-detects script locations, runs test scenarios, and outputs detailed diagnostic logs on failure.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def find_scripts_dir() -> Path:
    """Locate the scripts directory regardless of execution context."""
    base_dir = Path(__file__).parent.resolve()
    candidates = [
        base_dir / "submission_pkg" / "skills" / "validation" / "scripts",
        base_dir / "skills" / "validation" / "scripts",
        Path.cwd() / "submission_pkg" / "skills" / "validation" / "scripts",
        Path.cwd() / "skills" / "validation" / "scripts",
    ]
    for c in candidates:
        if c.exists() and (c / "syntax_check.py").exists():
            return c.resolve()
    return candidates[0].resolve()


SCRIPTS_DIR = find_scripts_dir()
SYNTAX_SCRIPT = SCRIPTS_DIR / "syntax_check.py"
SCOPE_SCRIPT = SCRIPTS_DIR / "scope_check.py"
PEDAGOGUE_SCRIPT = SCRIPTS_DIR / "pedagogue_check.py"


def run_guardrail(script_path: Path, *args) -> tuple[int, dict]:
    """Executes a guardrail script in a subprocess and parses stdout as JSON."""
    cmd = [sys.executable, str(script_path), *[str(a) for a in args]]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        output_json = json.loads(result.stdout)
    except json.JSONDecodeError:
        output_json = {
            "passed": False,
            "reward_penalty": None,
            "raw_stdout": result.stdout,
            "raw_stderr": result.stderr,
        }
    return result.returncode, output_json


def test_scenario_a_happy_path(temp_dir: Path) -> bool:
    print("\n[Scenario A] Testing Happy Path (All Guardrails Should Pass)...")

    clean_py = temp_dir / "utils.py"
    clean_py.write_text("def add(a: int, b: int) -> int:\n    return a + b\n")

    report_file = temp_dir / "diagnostic_report.json"
    report_payload = {
        "primary_target_symbols": [
            {"file_path": "utils.py", "symbol_name": "utils.add"}
        ],
        "suggested_investigation_scope": ["utils.py:lines 1-5"],
        "pedagogical_trace": [
            {"node": "issue_symptom", "relation_to_next": "CALLS"},
            {"node": "utils.add", "relation_to_next": "DEPENDS_ON"},
            {"node": "root_cause", "relation_to_next": ""}
        ]
    }
    report_file.write_text(json.dumps(report_payload, indent=2))

    patch_file = temp_dir / "valid_change.patch"
    patch_content = (
        "--- a/utils.py\n"
        "+++ b/utils.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-def add(a: int, b: int) -> int:\n"
        "+def add(a: int, b: int) -> int:\n"
    )
    patch_file.write_text(patch_content)

    code_syn, out_syn = run_guardrail(SYNTAX_SCRIPT, clean_py)
    code_scope, out_scope = run_guardrail(SCOPE_SCRIPT, report_file, patch_file)
    code_ped, out_ped = run_guardrail(PEDAGOGUE_SCRIPT, report_file)

    pass_syn = code_syn == 0 and out_syn.get("passed") is True
    pass_scope = code_scope == 0 and out_scope.get("passed") is True
    pass_ped = code_ped == 0 and out_ped.get("passed") is True

    ok = pass_syn and pass_scope and pass_ped
    print(f"  └─ Syntax Check   : {'PASS' if pass_syn else 'FAIL'}")
    print(f"  └─ Scope Check    : {'PASS' if pass_scope else 'FAIL'}")
    print(f"  └─ Pedagogy Check : {'PASS' if pass_ped else 'FAIL'}")

    if not ok:
        print("     [Debug Info]")
        if not pass_syn: print(f"       Syntax Stdout: {out_syn}")
        if not pass_scope: print(f"       Scope Stdout: {out_scope}")
        if not pass_ped: print(f"       Pedagogy Stdout: {out_ped}")

    return ok


def test_scenario_b_syntax_failure(temp_dir: Path) -> bool:
    print("\n[Scenario B] Testing Syntax Error Handling...")

    broken_py = temp_dir / "broken.py"
    broken_py.write_text("def broken_fn(\n    return 42\n")

    code, out = run_guardrail(SYNTAX_SCRIPT, broken_py)

    expected_fail = code != 0 and out.get("passed") is False and out.get("reward_penalty") == -1.0
    print(f"  └─ Caught Syntax Error : {'PASS' if expected_fail else 'FAIL'} (Penalty: {out.get('reward_penalty')})")
    return expected_fail


def test_scenario_c_scope_violation(temp_dir: Path) -> bool:
    print("\n[Scenario C] Testing Scope Creep Guardrail...")

    report_file = temp_dir / "scoped_report.json"
    report_payload = {
        "primary_target_symbols": [{"file_path": "allowed_file.py"}]
    }
    report_file.write_text(json.dumps(report_payload))

    rogue_patch = temp_dir / "rogue.patch"
    rogue_patch.write_text(
        "--- a/unauthorized_core.py\n"
        "+++ b/unauthorized_core.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-# old\n"
        "+# rogue edit\n"
    )

    code, out = run_guardrail(SCOPE_SCRIPT, report_file, rogue_patch)

    unauthorized_list = out.get("unauthorized_files", [])
    expected_fail = code != 0 and out.get("passed") is False and "unauthorized_core.py" in unauthorized_list
    print(f"  └─ Intercepted Out-Of-Scope Patch : {'PASS' if expected_fail else 'FAIL'} (Unauthorized: {unauthorized_list})")
    return expected_fail


def test_scenario_d_pedagogy_gap(temp_dir: Path) -> bool:
    print("\n[Scenario D] Testing Pedagogical Trace Failure...")

    report_file = temp_dir / "broken_trace.json"
    report_payload = {
        "pedagogical_trace": [
            {"node": "step_1", "relation_to_next": "INVALID_EDGE_TYPE"},
            {"node": "step_2", "relation_to_next": ""}
        ]
    }
    report_file.write_text(json.dumps(report_payload))

    code, out = run_guardrail(PEDAGOGUE_SCRIPT, report_file)

    expected_fail = code != 0 and out.get("passed") is False and out.get("reward_penalty") == -0.4
    print(f"  └─ Flagged Broken Reasoning Trace : {'PASS' if expected_fail else 'FAIL'} (Penalty: {out.get('reward_penalty')})")
    return expected_fail


def main():
    print("=" * 65)
    print("      Gemma 4 Developer Agent - Phase 1 Guardrail Harness     ")
    print("=" * 65)
    print(f"Executing scripts from: {SCRIPTS_DIR}")

    if not SCRIPTS_DIR.exists():
        print(f"ERROR: Cannot locate scripts directory at {SCRIPTS_DIR}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        temp_dir = Path(tmp_dir_str)

        results = [
            test_scenario_a_happy_path(temp_dir),
            test_scenario_b_syntax_failure(temp_dir),
            test_scenario_c_scope_violation(temp_dir),
            test_scenario_d_pedagogy_gap(temp_dir),
        ]

    print("\n" + "=" * 65)
    if all(results):
        print(" SUCCESS: All Phase 1 guardrail scenarios passed locally!")
        print(" Your orchestration, guardrails, and penalties are ready for Phase 2.")
        print("=" * 65)
        sys.exit(0)
    else:
        print(" FAILURE: One or more guardrail checks failed to behave as expected.")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    main()