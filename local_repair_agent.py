###Demo code repair agent with guardrail middleware
### Tests how local ai handles bug fix tasks while being constrained and corrected by Phase 1 Guardrails

import subprocess
import sys
from pathlib import Path
import json
import ollama
import tempfile

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

    def apply_and_validation_patch(self, patched_code_snippet: str, patch_diff_text: str)-> str:
        ### Toool function: Applies the agent patch, then runs Phase 1 Guardrails (Syntax and Scope check)
        # live against workspace
        try:
            self.target_file.write_text(patched_code_snippet, encoding="utf-8", newline="\n")
            self.patch_file.write_text(patch_diff_text, encoding="utf-8", newline="\n")
            syntax_res = run_guardrail(SYNTAX_SCRIPT, self.target_file)
            scope_res = run_guardrail(SCOPE_SCRIPT, self.report_file, self.patch_file)
            passed = syntax_res.get("passed", False) and scope_res.get("passed", False)
            total_penalty = syntax_res.get("reward_penalty", 0.0) + scope_res.get("reward_penalty", 0.0)

            return json.dumps({
                "guardrail_passed":passed,
                "reward_penalty": total_penalty,
                "syntax_feedback": syntax_res.get("feedback"),
                "scope_feedback": scope_res.get("feedback")
            })

        except Exception as e:
            return json.dumps({"guardrail_passed": False, "error":str(e)})
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
            "content":(
                "You are an expert autonomous software engineer fixing bugs in Python codebases. "
                "You have access to a validation tool called 'apply_and_validate_patch' that checks your code against strict guardrails. "
                "Your patch must pass both syntax checks and scope limits."
            )
        },
        {
            "role":"user",
            "content":(
                "Here is the buggy code in 'src/math_ops.py':\n"
                "def calculate_discount(price: float, discount_rate: float) -> float:\n"
                "    if not (price < 0 or not 0.0 <= discount_rate <= 1.0):\n"
                "        raise ValueError('Invalid price or discount rate')\n"
                "    return price * (1.0 - discount_rate)\n\n"
                "Fix the condition so valid inputs pass and invalid inputs raise ValueError. "
                "Call the 'apply_and_validate_patch' tool with your updated code and unified diff patch."
            )
        }
    ]

    tools_def = [
        {
            "type":"function",
            "function":{
                "name": "apply_and_validate_patch",
                "description": "Applies the proposed python code and git patch, and then runs security and syntax guardrails.",
                "parameters":{
                    "type":"object",
                    "properties":{
                        "patched_code_snippet": {"type": "string", "description":"The complete updated source code for src/math_ops.py."},
                        "patch_diff_text": {"type":"string", "description":"The unified diff patch string starting with --- a/src/math_ops.py"}
                    },
                    "required": ["patched_code_snippet", "patch_diff_text"]
                }
            }
        }
    ]

    try:
        for turn in range(3):
            response = ollama.chat(model="llama3.2:3b", messages=messages, tools=tools_def)
            messages.append(response.message)

            if response.message.tool_calls:
                for call in response.message.tool_calls:
                    fn_name = call.function.name
                    fn_args = call.function.arguments

                    print(f"[Action] Agent invoked tool: {fn_name}")
                    if fn_name == "apply_and_validate_patch":
                        result = env.apply_and_validation_patch(**fn_args)

                        print(f"[Observation from Guardrails]: {result}\n")
                        messages.append({
                            "role":"tool",
                            "content": result
                        })
            else:
                print(f"[Agent FInal Response]:\n{response.message.content}") 
                break
    finally:
        env.cleanup()

if __name__ == "__main__":
    run_repair_agent()