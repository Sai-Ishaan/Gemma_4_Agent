#!/usr/bin/env python3
"""
TDD Sandbox Integration Test Harness (run_tdd_sandbox_test.py)
"""

import os
import stat
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SANDBOX = WORKSPACE_ROOT / "sandbox_tdd_workspace"
SCRIPTS_DIR = WORKSPACE_ROOT / "submission_pkg" / "skills" / "validation" / "scripts"
TDD_SCRIPT = SCRIPTS_DIR / "tdd_guardrail.py"

def remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def run_cmd(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)

def test_tdd_pipeline():
    if SANDBOX.exists():
        try:
            shutil.rmtree(SANDBOX, onerror=remove_readonly)
        except Exception as e:
            print(f"Warning: Could not fully clean previous sandbox directory: {e}")

    SANDBOX.mkdir(parents=True, exist_ok=True)
    print(f"Initialized temporary Git sandbox at: {SANDBOX}")

    # 1. Initialize Git Repository
    run_cmd(["git", "init"], cwd=SANDBOX)
    run_cmd(["git", "config", "user.name", "GemmaAgent"], cwd=SANDBOX)
    run_cmd(["git", "config", "user.email", "agent@local.dev"], cwd=SANDBOX)
    run_cmd(["git", "config", "core.autocrlf", "false"], cwd=SANDBOX)

    # 2. Populate Buggy Source File
    src_dir = SANDBOX / "src"
    src_dir.mkdir(exist_ok=True)
    math_ops = src_dir / "math_ops.py"
    math_ops.write_text(
        "def calculate_discount(price: float, discount_rate: float) -> float:\n"
        "    # Bug: inverted condition logic\n"
        "    if not (price < 0 or not 0.0 <= discount_rate <= 1.0):\n"
        "        raise ValueError(\"Invalid price or discount rate\")\n"
        "    return price * (1.0 - discount_rate)\n",
        encoding="utf-8",
        newline="\n"
    )

    # 3. Create Regression Test
    tests_dir = SANDBOX / "tests"
    tests_dir.mkdir(exist_ok=True)
    test_file = tests_dir / "test_math.py"
    test_file.write_text(
        "import pytest\n"
        "from src.math_ops import calculate_discount\n\n"
        "def test_calculate_discount_valid():\n"
        "    assert calculate_discount(100.0, 0.2) == 80.0\n",
        encoding="utf-8",
        newline="\n"
    )

    run_cmd(["git", "add", "."], cwd=SANDBOX)
    run_cmd(["git", "commit", "-m", "Initial commit with buggy math_ops and test"], cwd=SANDBOX)

    # 4. Create the Correct Patch File (using standard ASCII spaces only)
    patch_file = SANDBOX / "candidate_fix.patch"
    patch_content = (
        "--- a/src/math_ops.py\n"
        "+++ b/src/math_ops.py\n"
        "@@ -3,1 +3,1 @@\n"
        "-    if not (price < 0 or not 0.0 <= discount_rate <= 1.0):\n"
        "+    if price < 0 or not (0.0 <= discount_rate <= 1.0):\n"
    )
    patch_file.write_text(patch_content, encoding="utf-8", newline="\n")

    print("\n--- Executing TDD Guardrail Test ---")
    cmd = [
        sys.executable,
        str(TDD_SCRIPT),
        str(SANDBOX),
        "tests/test_math.py",
        str(patch_file)
    ]
    res = run_cmd(cmd)

    print(f"TDD Guardrail Exit Code: {res.returncode}")
    print(f"TDD Guardrail JSON Output:\n{res.stdout}")
    if res.stderr:
        print(f"Stderr: {res.stderr}")

if __name__ == "__main__":
    test_tdd_pipeline()