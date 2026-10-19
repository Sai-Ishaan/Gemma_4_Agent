### lightweight Python REPL (Read-Eval-Print Loop)
### It provides a secure subprocess-based executation environmnet for local agent experimentation

import subprocess
import sys
import tempfile
from pathlib import Path


## Function to execute a raw Python code snippet inside a secure temporary environment and captures stdout, stderr and executation status.
def execute_python_snippet(code_snippet:str, timeout_sec: int=3)->dict:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        script_file = tmp_path/"agent_sandbox_script.py"
        script_file.write_text(code_snippet, encoding="utf-8", newline="\n")
        cmd = [sys.executable, str(script_file)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, cwd=tmp_path)
            return{
                "success":result.returncode ==0,
                "exit_code":result.returncode,
                "stdout":result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return{
                "success": False,
                "exit_code": -1,
                "stdout":"",
                "stderr":f"Infinite Loop guard triggered: Execution timed out after {timeout_sec} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "stdout":"",
                "stderr": str(e)
            }
if __name__ == "__main__":
    ### Quick test of REPL wrapper
    mock_code = "print('Virtual Sandbox REPL Active!')\nx= 10+20\nprint(f'Result:{x}')"
    print("Testing REPL Wrapper")
    res= execute_python_snippet(mock_code)
    print(res)        