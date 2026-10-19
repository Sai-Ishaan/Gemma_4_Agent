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
    ## Green Phase (Patch Verification)
    candidate_file_path = workspace_dir/"src"/"math_ops.py"
    raw_patch_bytes = patch_file.read_bytes()
    patch_text = raw_patch_bytes.decode("utf-8").replace("\r\n", "\n").replace("\xa0", " ")
    
    patch_proc = subprocess.run(
        ["git", "apply", "--ignore-space-change", "--whitespace=nowarn"], 
        input=patch_text, 
        cwd=workspace_dir, 
        text=True, 
        capture_output=True
    )
    if patch_proc.returncode !=0:
        try:
            candidate_file_path.write_text(patch_text, encoding="utf-8", newline="\n")
        except Exception as e:
            output={
                "passed":False,
                "reward_penalty": -1.0,
                "phase": "patch_application_failed",
                "feedback": f"Patch Application failed via Git apply: {patch_proc.stderr.strip()}"
            }
            print(json.dumps(output, indent=2))
            sys.exit(1)

    green_result = run_pytest(workspace_dir, test_file_rel) ## re-run pytest on patcjed code
    ##revert hot changrs to keep workspace clean after change
    subprocess.run(["git", "checkout", "."], cwd=workspace_dir, capture_output=True)

    if not green_result["passed"]:
        output={
            "passed": False,
            "reward_penalty": -1.0,
            "phase": "green_phase_failed",
            "feedback": f"TDD Violation (Green Phase): The implementation patch failed to fix the test. Pytest output: \n{green_result['stdout']}\n{green_result['stdout']}"
        }
        print(json.dumps(output, indent=2))
        sys.exit(1)

    ##Success: both gates passed successfully
    output={
        "passed": True,
        "reward_penalty":0.0,
        "phase": "tdd_complete",
        "feedback": "TDD Co-synthesis passed: Test successfully failed on buggy code and passed on patched code."
    }
    print(json.dumps(output, indent=2))
    sys.exit(0)

print("TDD Guardrail module loaded")
if __name__ == "__main__":
    main()
