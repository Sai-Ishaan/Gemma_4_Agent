#!/usr/bin/env python3
"""
Local Sandbox Integration Runner (run_sandbox_test.py)
Tests the end-to-end pipeline on a real local sample codebase directory,
invoking live guardrail scripts (`syntax_check.py`, `scope_check.py`, `pedagogue_check.py`).
"""

import json
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SCRIPTS_DIR = WORKSPACE_ROOT / "submission_pkg" / "skills" / "validation" / "scripts"
TEST_REPO = WORKSPACE_ROOT / "sandbox_workspace"

def setup_sandbox():
    """Sets up a real multi-file sandbox repository on disk."""
    if TEST_REPO.exists():
        import shutil
        shutil.rmtree(TEST_REPO)
    
    src_dir = TEST_REPO / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    
    # Create module A (Math operations with a deliberate bug)
    (src_dir / "math_ops.py").write_text(
        'def calculate_total(price: float, tax: float) -> float:\n'
        '    # Bug: using addition instead of multiplication for tax computation, or inverted condition\n'
        '    if price < 0:\n'
        '        raise ValueError("Price cannot be negative")\n'
        '    return price + (price * tax)\n',
        encoding="utf-8"
    )

    # Create module B (Utility helper)
    (src_dir / "utils.py").write_text(
        'def format_currency(val: float) -> str:\n'
        '    return f"${val:.2f}"\n',
        encoding="utf-8"
    )
    
    print(f"Sandbox repository initialized at: {TEST_REPO}")

def run_guardrail(script_name: str, *args) -> dict:
    script_path = SCRIPTS_DIR / script_name
    cmd = [sys.executable, str(script_path), *[str(a) for a in args]]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {"passed": False, "reward_penalty": -1.0, "feedback": f"Output parsing failed for {script_name}. Raw stdout: {res.stdout}"}

def simulate_live_test():
    setup_sandbox()

    target_file = TEST_REPO / "src" / "math_ops.py"
    report_file = TEST_REPO / "diagnostic_report.json"
    patch_file = TEST_REPO / "candidate.patch"

    # 1. Create a Diagnostic Report defining the authorized scope
    report_data = {
        "primary_target_symbols": [{"file_path": "src/math_ops.py"}],
        "suggested_investigation_scope": ["src/math_ops.py:lines 1-10"],
        "pedagogical_trace": [
            {"node": "issue_symptom", "relation_to_next": "CALLS"},
            {"node": "calculate_total", "relation_to_next": "DEPENDS_ON"}
        ]
    }
    report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    # 2. Scenario A: Valid Patch (Fixes math_ops.py correctly)
    print("\n--- Running Scenario A: Valid In-Scope Fix ---")
    valid_patch = (
        "--- a/src/math_ops.py\n"
        "+++ b/src/math_ops.py\n"
        "@@ -5,1 +5,1 @@\n"
        "-    return price + (price * tax)\n"
        "+    return price * (1.0 + tax)\n"
    )
    patch_file.write_text(valid_patch, encoding="utf-8")

    # Apply patch to sandbox file for syntax checking
    target_file.write_text(
        'def calculate_total(price: float, tax: float) -> float:\n'
        '    if price < 0:\n'
        '        raise ValueError("Price cannot be negative")\n'
        '    return price * (1.0 + tax)\n',
        encoding="utf-8"
    )

    syntax_res = run_guardrail("syntax_check.py", target_file)
    scope_res = run_guardrail("scope_check.py", report_file, patch_file)
    pedagogy_res = run_guardrail("pedagogue_check.py", report_file)

    print(f"Syntax Check:    {syntax_res.get('passed')} | {syntax_res.get('feedback')}")
    print(f"Scope Check:     {scope_res.get('passed')} | {scope_res.get('feedback')}")
    print(f"Pedagogy Check:  {pedagogy_res.get('passed')} | {pedagogy_res.get('feedback')}")

    # 3. Scenario B: Rogue Exploit Patch (Tries to touch utils.py outside scope)
    print("\n--- Running Scenario B: Out-of-Scope Scope Creep Exploit ---")
    rogue_patch = (
        "--- a/src/utils.py\n"
        "+++ b/src/utils.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-    return f\"${val:.2f}\"\n"
        "+    return f\"EUR {val:.2f}\"\n"
    )
    patch_file.write_text(rogue_patch, encoding="utf-8")

    scope_rogue_res = run_guardrail("scope_check.py", report_file, patch_file)
    print(f"Scope Check (Rogue): {scope_rogue_res.get('passed')} | {scope_rogue_res.get('feedback')}")
    print(f"Reward Penalty:      {scope_rogue_res.get('reward_penalty')}")

if __name__ == "__main__":
    simulate_live_test()