import json
import ollama
import sys
from pathlib import Path
import subprocess
import tempfile

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SCRIPTS_DIR = WORKSPACE_ROOT/"submission_pkg"/"skills"/"validation"/"scripts"
SCOPE_SCRIPT = SCRIPTS_DIR /"scope_check.py"
SYNTAX_SCRIPT = SCRIPTS_DIR/"syntax_check.py"

def run_guardrail(script_path: Path, *args)-> dict:
    cmd = [sys.executable, str(script_path), *[str(a) for a in args]]
    res = subprocess.run(cmd, capture_output=True, text=True)

    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {"passed": False, "reward_penalty": -1.0, "feedback":"Guardrail evaluation error."}

###Snippet executor in a temporary subprocess
def execute_python_snippet(code_snippet: str)->str:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        script_file = tmp_path/"sandbox_test.py"
        script_file.write_text(code_snippet, encoding="utf-8", newline="\n")
        res = subprocess.run([sys.executable, str(script_file)], capture_output=True, text=True, timeout=5)
        return json.dumps({
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
        })

##Defining available tools for Ollama
available_tools = {
    "execute_python_snippet": execute_python_snippet
}

def run_local_agent(task_prompt: str, target_file_path: str):
    print(f"--- Firing up the Local Agent Loop with Ollama ---")
    print(f"Task: {task_prompt}")

    messages = [
        {
            "role": "system",
            "content": "You are a secure autonomous coding assistant. A Python REPL tool is at your disposal, which you can access and test your code before proposing edits."
        },
        {
            "role": "user",
            "content": task_prompt
        }
    ]

    ### Defining a tool schema for Ollama client
    tools_def = [
        {
            "type": "function",
            "function": {
                "name": "execute_python_snippet",
                "description": "Execute Python code in a secure virtual sandbox to test behavior or outputs.",
                "parameters":{
                    "type": "object",
                    "properties":{
                        "code_snippet": {"type": "string", "description":"Valid Python code to execute."}
                    },
                    "required":["code_snippet"]
                }
            }
        }
    ]

    for turn in range(3):
        response = ollama.chat(
            model="llama3.2:3b",
            messages=messages,
            tools=tools_def
        )
        messages.append(response.message)

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                fn_name = call.function.name
                fn_args = call.function.arguments
                print(f"[Action] Agent called tool: {fn_name} with args: {fn_args}")

                if fn_name in available_tools:
                    tool_result = available_tools[fn_name](**fn_args)
                    print(f"[observation] Tool Output: {tool_result}\n")

                    messages.append({
                        "role": "tool",
                        "content": tool_result
                    })
        else:
            print(f"[Agent Final Response]:\n{response.message.content}")
            break

if __name__ == "__main__":
    sample_task = "Write and test a python function that calculates compound interest for $1000 at 5 percent over 3 years."
    run_local_agent(sample_task, "src/math_ops.py")
