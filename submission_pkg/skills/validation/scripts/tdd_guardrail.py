### Uses a Red-Green signal-like Gated approach
## Red Phase: Agent's submitted test must FAIL against original code
## Green Phase: Agent's code patch must make the test PASS
import json
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def run_pytest(workspace_path: Path, test_file_rel: str)->dict:
    ## execs pytests on a specific test file within the workspace
    cmd = [sys.executable, "-m", "pytest", "-q", test_file_rel]
    res = subprocess.run(cmd, cwd=workspace_path, capture_output=True, text=True)
    return{
        "exit_code": res.returncode,
        "passed":res.returncode == 0,
        "stdout": res.stdout.strip(),
        "stderr": res.stderr.strip()
    }

def main():
    if len(sys.argv) <4:
        print(json.dumps({
            "passed": False,
            "reward_penalty": -1.0,
            "feedback": "Usage: python tdd_guardrail.py <workspace_dir> <test_file_rel> <patch_file>"
        }))
        sys.exit(1)
    workspace_dir = Path(sys.argv[1]).resolve()
    test_file_rel = sys.argv[2]
    patch_file = Path(sys.argv[3]).resolve()

    if not workspace_dir.exists():
        print(json({
            "passed":False,
            "reward_penalty": -1.0,
            "feedback": f"Workspace directory doesn't exist: {workspace_dir}"
        }))
        sys.exit(1)
    ### Red Phase (Test Validation)
    red_result = run_pytest(workspace_dir, test_file_rel)
    if red_result["passed"]:
        output={
            "passed":False,
            "reward_penalty":-1.0,
            "phase":"red_phase_failed",
            "feedback": f"TDD Violation (Red Phase): The submitted test passed immediately against defective code. Valid bug test Initially Must fail."
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)