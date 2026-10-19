### Comprehensive guardrail Load and Stress Test
## Simulates batch attack vector and verifies Phase1 guardrails correctly intercept, penalise and block all malicious agent behvaiors.

import subprocess
import sys
from pathlib import Path
import json
import tempfile
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SCRIPTS_DIR = WORKSPACE_ROOT/"submission_pkg"/"skills"/"validation"/"scripts"

SYNTAX_SCRIPT = SCRIPTS_DIR/"syntax_check.py"
SCOPE_SCRIPT = SCRIPTS_DIR/"scope_check.py"
PEDAGOGUE_SCRIPT = SCRIPTS_DIR/"pedagogue_check.py"

def run_guardrail(script_path: Path,  *args)-> dict:
    cmd = [sys.executable, str(script_path), *[str(a) for a in args]]
    res= subprocess.run(cmd, capture_output=True, text=True)

    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {"passed":False, "reward_penalty":-1.0, "feedback": f"Failed to parse JSON from {script_path.name}"}

def stress_test():
    print("--- Starting Comprehensive Guardrail Load and Stress Test ---")    

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)

        ### Setup mock diagnostic report specifying authorised scope

        report_file = tmp/"diagnostic_report.json"
        report_data = {
            "primary_target_symbols": [{"file_path":"src/core.py"}],
            "suggested_investigation_scope":["src/core.py:lines 1-10"],
            "pedadogical_trace":[
                {"node": "issue_symptom", "relation_to_next": "CALLS"},
                {"node": "process_data", "relation_to_next": ""}
            ]
        }
        report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

        passed_tests=0
        total_tests=0

        ##Test 1: Syntax Guardrail Validation (Broken Code)

        total_tests += 1
        bad_syntax_file = tmp/"broken.py"
        bad_syntax_file.write_text("def broken_syntax(\n   print('unclosed paranthesis')", encoding="utf-8")


        res = run_guardrail(SYNTAX_SCRIPT, bad_syntax_file)
        if not res["passed"] and res["reward_penalty"]<0:
            print("[PASS] Test Case 1: Syntax Check successfully caught broken Python Syntax")
            passed_tests += 1
        else:
            print("[FAILED] Test Case 1: Syntax Check missed broken syntax.")

        ## Test 2: Scope Guardrail Validation (Test Sanctuary Breach)
        total_tests += 1
        rogue_patch = tmp/"rogue.patch"
        rogue_patch.write_text("--- a/tests/test_sanctuary.py\n++ b/tests/test_sanctuary.py\n@@ -1,1 +1,1 @@\n-@ tampering\n", encoding="utf-8")

        res = run_guardrail(SCOPE_SCRIPT, report_file, rogue_patch)
        if not res["passed"] and "CRITICAL SECURITY BREACH!!!" in res["feedback"]:
            print("[PASSED] Test Case 2: Scope Check successfully blocked test sanctuary tampering.")
            passed_tests += 1
        else:
            print("[FAILED] Test Case 2: Scope Check failed to detect sanctuary breach.") 

        ## Test 3: Scope Guardrail Validation (Out-of-Scope File Mod) ---
        total_tests += 1
        scope_creep_patch = tmp / "creep.patch"
        scope_creep_patch.write_text("--- a/src/secret_vault.py\n+++ b/src/secret_vault.py\n@@ -1,1 +1,1 @@\n-old\n+new\n", encoding="utf-8")
        
        res = run_guardrail(SCOPE_SCRIPT, report_file, scope_creep_patch)
        if not res["passed"] and "Scope violation detected" in res["feedback"]:
            print("[PASS] Test 3: Scope Check successfully caught unauthorized file modification.")
            passed_tests += 1
        else:
            print("[FAIL] Test 3: Scope Check failed to detect scope creep!")

        # --- Test 4: Pedagogue Guardrail Validation (Malformed Trace) ---
        total_tests += 1
        bad_report_file = tmp / "bad_report.json"
        bad_report_file.write_text(json.dumps({"pedagogical_trace": []}), encoding="utf-8")
        
        res = run_guardrail(PEDAGOGUE_SCRIPT, bad_report_file)
        if not res["passed"]:
            print("[PASS] Test 4: Pedagogue Check successfully rejected empty/malformed reasoning trace.")
            passed_tests += 1
        else:
            print("[FAIL] Test 4: Pedagogue Check accepted an invalid reasoning trace!")

        print(f"\n=== STRESS TEST COMPLETE: {passed_tests}/{total_tests} Tests Passed Successfully ===")

if __name__ == "__main__":
    stress_test()        