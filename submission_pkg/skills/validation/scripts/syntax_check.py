###This script parses all modified .py files in the working directory 
# using native Abstract Syntax Tree (AST) compiler in Python and optional linter tools.

##Goal: To Intercept syntax errors, indent mismatches and invalid expressions
    # Syntax and Static Code Quality Guardrails 

import ast
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

def check_syntax(file_path: Path)-> Dict[str, Any]:
    ##Parsing a single python file with AST and checking for any syntax errors
    if not file_path.exists():
        return{
            "status": "ERROR",
            "file": str(file_path),
            "message": "File does not exist on disk"
        }
    try:
        source=file_path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(file_path))
        return {
            "status": "PASS",
            "file": str(file_path)
        }

    except Exception as e:
        return {
            "status": "FAIL",
            "file": str(file_path),
            "line": e.lineno,
            "column":e.offset,
            "error_type": "SyntaxError",
            "message": str(e.msg),
            "text": e.text.strip() if e.text else ""
        }
    except Exception as e:
        return{
            "status": "FAIL",
            "file": str(file_path),
            "error_type": type(e).__name__,
            "message": str(e)
        }

def main():
    if len(sys.argv) < 2:
        print(json.dump({
            "passed": False,
            "reward_penalty": -1.0,
            "feedback": "Usage: python syntax_check.py <file1.py> [file2.py .....]"
        }))
        sys.exit(1)
    file_paths = [Path(p) for p in sys.argv[1:]]
    results: List[Dict[str,Any]] = []

    has_failures = False
    for path in file_paths:
        if path.suffix == ".py":
            res = check_syntax(path)
            results.append(res)
            if res["status"] != "PASS":
                has_failures = True

    reward_penalty = -1.0 if has_failures else 0.0

    output = {
        "passed": not has_failures,
        "reward_penalty": reward_penalty,
        "results": results,
        "feedback": "Syntax Check Failed. Need to fix syntax and structural issues in the modified files." if has_failures else "All modified files passed AST syntax validation."
    }

    print(json.dumps(output, indent=2))
    sys.exit(1 if has_failures else 0)

if __name__ == "__main__":
    main()