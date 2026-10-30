###Demo code repair agent with guardrail middleware
### Tests how local ai handles bug fix tasks while being constrained and corrected by Phase 1 Guardrails

import subprocess
import sys
from pathlib import Path
import json
import ollama
import tempfile
import difflib

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SCRIPTS_DIR = WORKSPACE_ROOT/"submission_pkg"/"skills"/"validation"/"scripts"
SYNTAX_SCRIPT = SCRIPTS_DIR/"syntax_check.py"
SCOPE_SCRIPT = SCRIPTS_DIR/"scope_check.py"

def run_guardrail(script_path: Path, *args)-> dict:
    cmd = [sys.executable, str(script_path), *[str(a) for a in args]]
    res = subprocess.run(cmd, capture_output=True, text=True)

    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {"passed": False, "reward_penalty":-1.0, "feedback":f"Guardrail output parsing error. Raw:{res.stdout}"}

def run_behavioral_checks(target_file: Path) -> dict:
    ### Executes behavioural checks against the actual proposed source file. 
    #runs target module in a separate Python process.
    test_code = r'''
import importlib.util
import json
import sys

target_path = sys.argv[1]

try:
    spec = importlib.util.spec_from_file_location(
        "math_ops_under_test", target_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    test_cases = [
        ("zero_discount", 100, 0.0, 100.0),
        ("normal_discount", 100, 0.1, 90.0),
        ("full_discount", 100, 1.0, 0.0),
    ]

    results = []

    for name, price, rate, expected in test_cases:
        actual = module.calculate_discount(price, rate)
        passed = abs(actual - expected) < 1e-9

        results.append({
            "test": name,
            "passed": passed,
            "expected": expected,
            "actual": actual
        })

    valid_cases = [
        ("zero_price", 0, 0.1, 0.0)
    ]
    for name, price, rate, expected in valid_cases:
    try:
        actual = module.calculate_discount(price, rate)
        passed = abs(actual - expected) < 1e-9
    except Exception as exc:
        passed = False
        actual = type(exc).__name__

    results.append({
        "test": name,
        "passed": passed,
        "expected": expected,
        "actual": actual
    })

    invalid_cases = [
        ("negative_price", -100, 0.1),
        ("negative_rate", 100, -0.1),
        ("excessive_rate", 100, 1.1),
    ]

    for name, price, rate in invalid_cases:
        try:
            module.calculate_discount(price, rate)
            passed = False
            actual = "No exception raised"
        except ValueError:
            passed = True
            actual = "ValueError"
        except Exception as exc:
            passed = False
            actual = type(exc).__name__

        results.append({
            "test": name,
            "passed": passed,
            "expected": "ValueError",
            "actual": actual
        })

    passed_count = sum(item["passed"] for item in results)
    failed_count = len(results) - passed_count

    all_passed = failed_count == 0

    print(json.dumps({
        "passed": all_passed,
        "total_tests": len(results),
        "passed_tests": passed_count,
        "failed_tests": failed_count,
        "reward_penalty": 0.0 if all_passed else -1.0,
        "results": results
    }))

except Exception as exc:
    print(json.dumps({
        "passed": False,
        "reward_penalty": -1.0,
        "feedback": f"Behavioural test execution failed: {exc}"
    }))
'''
    if not target_file.is_file():
        return{
            "passed": False,
            "reward_penalty": -1.0,
            "feedback": f"Target file does not exist: {target_file}"
        }
    try:
        result = subprocess.run(
            [sys.executable, "-c", test_code, str(target_file)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode !=0:
            return {
                "passed": False,
                "reward_penalty": -1.0,
                "feedback": result.stderr
            }
        return json.loads(result.stdout)
    
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return{
            "passed": False,
            "reward_penalty": -1.0,
            "feedback": f"Behavioural validation failed: {exc}"
        }

class RepairEnvironment:
    ### Simulates a secure sandbox workspace with target buggy file and scope limits
    def __init__(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp_dir.name)
        ###setup source file with a deliberate bug (Control Flow Inversion)
        self.src_dir = self.workspace/"src"
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.target_file = self.src_dir/"math_ops.py"
        self.target_file.write_text(
            'def calculate_discount(price: float, discount_rate: float) -> float:\n'
            '    # Bug: inverted condition logic\n'
            '    if not (price < 0 or not 0.0 <= discount_rate <= 1.0):\n'
            '        raise ValueError("Invalid price or discount rate")\n'
            '    return price * (1.0 - discount_rate)\n',
            encoding="utf-8",
            newline="\n"
        )

        ##Setting up Diagnostic Report defining authorised scope
        self.report_file = self.workspace/"diagnostic_report.json"
        self.report_data = {
            "primary_target_symbols": [{"file_path": "src/math_ops.py"}],
            "suggested_investigation_scope": ["src/math_ops.py: lines 1-5"]
        }
        self.report_file.write_text(json.dumps(self.report_data, indent=2), encoding="utf-8")
        self.patch_file = self.workspace/"candidate.patch"

    def apply_and_validation_patch(self, patched_code_snippet: str)-> str:
        ### Tool function: Applies the agent patch, then runs Phase 1 Guardrails (Syntax and Scope check)
        # live against workspace
        ### Stage the proposed source, generate its unified diff,
        ###  run Phase 1 guardrails, and promote it only if all
        ### validations pass.

        candidate_file = self.src_dir / "math_ops_candidate.py"

        try:
            # 1. Preserve the original source.
            original_code = self.target_file.read_text(encoding="utf-8")

            # 2. Write the proposed source to a separate candidate file.
            candidate_file.write_text(
                patched_code_snippet,
                encoding="utf-8",
                newline="\n"
            )

        # 3. Generate the unified diff automatically.
            diff = difflib.unified_diff(
                original_code.splitlines(keepends=True),
                patched_code_snippet.splitlines(keepends=True),
                fromfile="a/src/math_ops.py",
                tofile="b/src/math_ops.py"
            )

            patch_diff_text = "".join(diff)

            self.patch_file.write_text(
                patch_diff_text,
                encoding="utf-8",
                newline="\n"
            )

            # 4. Run syntax validation against the candidate.
            syntax_res = run_guardrail(
                SYNTAX_SCRIPT,
                candidate_file
            )

            # 5. Run scope validation against the generated diff.
            scope_res = run_guardrail(
                SCOPE_SCRIPT,
                self.report_file,
                self.patch_file
            )

            # 6. Run behavioral checks only if syntax and scope pass.
            if (
                syntax_res.get("passed", False)
                and scope_res.get("passed", False)
            ):
                behavior_res = run_behavioral_checks(candidate_file)

            else:
                behavior_res = {
                    "passed": False,
                    "reward_penalty": 0.0,
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "results": None,
                    "feedback": (
                        "Behavioural checks skipped because "
                        "syntax or scope validation failed."
                    )
                }

            # 7. Determine the overall validation result.
            passed = (
                syntax_res.get("passed", False)
                and scope_res.get("passed", False)
                and behavior_res.get("passed", False)
            )

            # 8. Calculate the combined penalty.
            total_penalty = (
                syntax_res.get("reward_penalty", 0.0)
                + scope_res.get("reward_penalty", 0.0)
                + behavior_res.get("reward_penalty", 0.0)
            )
 
            # 9. Promote the candidate only after every check passes.
            if passed:
                candidate_file.replace(self.target_file)
                promotion_feedback = (
                    "All validations passed. Candidate promoted "
                    "to the target source file."
                )
            else:
                promotion_feedback = (
                    "Candidate rejected. Original target source "
                    "remains unchanged."
                )

            # 10. Return structured results to the agent.
            return json.dumps({
                "guardrail_passed": passed,
                "reward_penalty": total_penalty,

                "syntax": {
                    "passed": syntax_res.get("passed", False),
                    "feedback": syntax_res.get("feedback")
                },

                "scope": {
                    "passed": scope_res.get("passed", False),
                    "feedback": scope_res.get("feedback")
                },

                "behavior": {
                    "passed": behavior_res.get("passed", False),
                    "total_tests": behavior_res.get("total_tests", 0),
                    "passed_tests": behavior_res.get("passed_tests", 0),
                    "failed_tests": behavior_res.get("failed_tests", 0),
                    "results": behavior_res.get("results"),
                    "feedback": behavior_res.get("feedback")
                },

                "promotion": {
                    "accepted": passed,
                    "feedback": promotion_feedback
                }

            }, indent=2) 

        except Exception as e:
            return json.dumps({
                "guardrail_passed": False,
                "reward_penalty": -1.0,
                "error": str(e),
                "promotion": {
                    "accepted": False,
                    "feedback": (
                        "An error occurred. The candidate was not "
                        "promoted."
                    )
                }
            }, indent=2)
        
    def cleanup(self):
        self.tmp_dir.cleanup()

def run_repair_agent():
    env = RepairEnvironment()
    print("--- Starting Local Code Repair Agent loop ---")
    print(f"Targetting Buggy File: src/math_ops.py")
    print(f"Task: Fix the control flow inversion bug in calculate_discount without violating the scope.")

    messages= [ 
        {
            "role": "system",
    "content": (
        "You are an autonomous Python code repair agent. "
        "You must repair the supplied function using the "
        "apply_and_validate_patch tool. "
        "You MUST invoke this tool with the complete updated source code."
        "The validation environment generates the unified diff automatically."
        "Do not print or describe a tool call as JSON in ordinary text."
        "Do not claim that a patch was applied or validated unless "
        "you receive the actual tool result."
        "The proposed code must pass syntax, declared-scope, and "
        "behavioural regression checks."
    )
        },
        {
            "role":"user",
            "content":(
                "Here is the buggy code in 'src/math_ops.py':\n"
                "def calculate_discount(price: float, discount_rate: float) -> float:\n"
                "    if not (price < 0 or not 0.0 <= discount_rate <= 1.0):\n"
                "        raise ValueError('Invalid price or discount rate')\n"                "    return price * (1.0 - discount_rate)\n\n"
                "Fix the condition so valid inputs pass and invalid inputs raise ValueError. "
                "Call the 'apply_and_validate_patch' tool with your complete updated source code. "
                "Do not return your proposed patch as ordinary text."
                "Invoke the validation tool before providing your final response."
            )
        }
    ]

    tools_def = [
        {
        "type": "function",
        "function": {
            "name": "apply_and_validate_patch",
            "description": "Submit a complete replacement for the target function. The environment generates the patch and validates it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patched_code_snippet": {
                        "type": "string",
                        "description": "Complete replacement Python function."
                    }
                },
                "required": ["patched_code_snippet"]
            }
        }
    }
    ]

    try:
        for turn in range(3):
            print(f"\n--- Agent Turn {turn + 1}/3 ---")

            response = ollama.chat(
            model="llama3.2:3b",
            messages=messages,
            tools=tools_def
            )
            print("\n[DEBUG] Full Ollama response:")
            print(response)

            print("\n[DEBUG] Response message:")
            print(response.message)

            print("\n[DEBUG] Tool calls:")
            print(response.message.tool_calls)
            messages.append(response.message)

            if response.message.tool_calls:
                for call in response.message.tool_calls:
                    fn_name = call.function.name
                    fn_args = call.function.arguments

                    if fn_name != "apply_and_validate_patch":
                        print(f"[Rejected] Unexpected tool: {fn_name}")
                        continue

                    print(f"[Action] Agent invoked tool: {fn_name}")

                    result = env.apply_and_validation_patch(**fn_args)

                    print(f"[Observation from Guardrails]:\n{result}\n")

                    messages.append({
                        "role": "tool",
                        "content": result
                    })

            else:
                print("[Warning] No actual tool call was returned.")

                if turn < 2:
                    messages.append({
                        "role": "user",
                        "content": (
                            "You have not invoked the validation tool yet. "
                            "Your previous response was not an actual tool call. "
                            "Please invoke apply_and_validate_patch using the "
                            "required arguments. Do not return JSON as ordinary text."
                        )
                    })
                else:
                    print("[Failure] Tool invocation was not completed.")
    finally:
        env.cleanup()

if __name__ == "__main__":
    run_repair_agent()