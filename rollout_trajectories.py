### Phase 3: Trajectory Rollout and Reward Generator
### Reads synthetic curriculum entries, executes agent rollouts, scores generated diffs and reasoning traces using Phase1 guardrails.
###Iterates through all mult-scenario entries in gemma_training_curriculum.jsonl,
###simulates both positive and negative agent rollouts, evaluates them using Phase 1 hardened guardtails
## O/Ps scored JSONL trajectories

import json
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SCRIPTS_DIR = WORKSPACE_ROOT/"submission_pkg"/"skills"/"validation"/"scripts"
SYNTAX_SCRIPT = SCRIPTS_DIR/"syntax_check.py"
SCOPE_SCRIPT = SCRIPTS_DIR/"scope_check.py"
PEDAGOGUE_SCRIPT =SCRIPTS_DIR/"pedagogue_check.py"

def execute_guardrail(script_path: Path, *args)-> dict:
    #### Executes a phase1 guardrail script in subprocess and parses JSON output.
    if not script_path.exists():
        return {"passed": False, "reward_penalty":-0.5, "feedback":f"Missing script: {script_path.name}"}

    cmd = [sys.executable, str(script_path), *[str(a) for a in args]]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return {"passed":False, "reward_penalty":-1.0, "feedback": f"Invalid JSON from {script_path.name}"}

###Scoring a candidate trajectory against syntax, scope and pedagogy guardrails
def evaluate_trajectory(target_file_rel: str, mutated_code: str, diagnostic_report: dict, patch_text: str) -> tuple[float, dict]:
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        target_file = tmp_dir / target_file_rel
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        patched_code = apply_patch_string(mutated_code, patch_text)
        target_file.write_text(patched_code, encoding="utf-8")

        report_file = tmp_dir / "diagnostic_report.json"
        report_file.write_text(json.dumps(diagnostic_report, indent=2), encoding="utf-8")

        patch_file = tmp_dir / "candidate.patch"
        patch_file.write_text(patch_text, encoding="utf-8")

        syntax_res = execute_guardrail(SYNTAX_SCRIPT, target_file)
        scope_res = execute_guardrail(SCOPE_SCRIPT, report_file, patch_file)
        pedagogy_res = execute_guardrail(PEDAGOGUE_SCRIPT, report_file)

        base_reward = 1.0 if (syntax_res.get("passed") and scope_res.get("passed") and pedagogy_res.get("passed")) else 0.0
        penalties = (
            syntax_res.get("reward_penalty", 0.0)
            + scope_res.get("reward_penalty", 0.0)
            + pedagogy_res.get("reward_penalty", 0.0)
        )
        composite_reward = max(-1.0, min(1.0, base_reward + penalties))

        eval_summary = {
            "syntax_passed": syntax_res.get("passed", False),
            "scope_passed": scope_res.get("passed", False),
            "pedagogy_passed": pedagogy_res.get("passed", False),
            "composite_reward": composite_reward,
            "feedback": {
                "syntax": syntax_res.get("feedback"),
                "scope": scope_res.get("feedback"),
                "pedagogy": pedagogy_res.get("feedback"),
            }
        }
        return composite_reward, eval_summary

def apply_patch_string(original_code: str, patch_text: str) -> str:
    #Simple patch simulation for single-file string replacements.
    # If patch contains replacement lines, substitute directly for trajectory evaluation
    lines_to_add = [line[1:] for line in patch_text.splitlines() if line.startswith("+") and not line.startswith("+++")]
    lines_to_remove = [line[1:] for line in patch_text.splitlines() if line.startswith("-") and not line.startswith("---")]
    
    result = original_code
    for old_line, new_line in zip(lines_to_remove, lines_to_add):
        if old_line in result:
            result = result.replace(old_line, new_line, 1)
    return result


def generate_trajectories(curriculum_path: Path, output_path: Path):
    if not curriculum_path.exists():
        print(f"Error: Curriculum file '{curriculum_path}' not found. Run inject_bugs.py first.")
        return

    raw_entries = [json.loads(line) for line in curriculum_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Loaded {len(raw_entries)} multi-scenario curriculum item(s) for comprehensive rollout...")

    trajectories = []

    for idx, item in enumerate(raw_entries):
        rel_file = item.get("file_path", "src/math_ops.py")
        clean_code = item["output_fix"]
        buggy_code = item["input_code"]
        graph_data = item["dependency_graph"]

        # --- Positive Rollout ---
        good_report = {
            "primary_target_symbols": [{"file_path": rel_file}],
            "suggested_investigation_scope": [f"{rel_file}:lines 1-15"],
            "pedagogical_trace": [
                {"node": "issue_symptom", "relation_to_next": "CALLS"},
                {"node": "calculate_discount", "relation_to_next": "DEPENDS_ON"},
                {"node": "root_cause", "relation_to_next": ""}
            ]
        }
        
        good_patch = f"--- a/{rel_file}\n+++ b/{rel_file}\n@@ -1,4 +1,4 @@\n-{buggy_code.splitlines()[1]}\n+{clean_code.splitlines()[1]}\n"

        reward_a, summary_a = evaluate_trajectory(rel_file, buggy_code, good_report, good_patch)

        trajectories.append({
            "trajectory_id": f"traj_{idx}_pos",
            "prompt": {
                "instruction": item["instruction"],
                "input_code": buggy_code,
                "dependency_graph": graph_data
            },
            "response": {
                "diagnostic_report": good_report,
                "patch": good_patch
            },
            "reward": reward_a,
            "evaluation": summary_a
        })

        # --- Negative Rollout (Test Sanctuary Tampering Exploit) ---
        bad_report = {
            "primary_target_symbols": [{"file_path": "tests/test_math.py"}]
        }
        bad_patch = "--- a/tests/test_math.py\n+++ b/tests/test_math.py\n@@ -1,1 +1,1 @@\n+# tampering with test sanctuary\n"

        reward_b, summary_b = evaluate_trajectory(rel_file, buggy_code, bad_report, bad_patch)

        trajectories.append({
            "trajectory_id": f"traj_{idx}_neg_exploit",
            "prompt": {
                "instruction": item["instruction"],
                "input_code": buggy_code,
                "dependency_graph": graph_data
            },
            "response": {
                "diagnostic_report": bad_report,
                "patch": bad_patch
            },
            "reward": reward_b,
            "evaluation": summary_b
        })

    output_path.write_text("\n".join(json.dumps(t) for t in trajectories) + "\n", encoding="utf-8")
    print(f"Phase 3 Comprehensive Complete: Exported {len(trajectories)} scored trajectory pairs to `{output_path.name}`.")


if __name__ == "__main__":
    CURRICULUM_FILE = WORKSPACE_ROOT / "gemma_training_curriculum.jsonl"
    OUTPUT_TRAJECTORIES = WORKSPACE_ROOT / "trajectories_for_lora.jsonl"

    generate_trajectories(CURRICULUM_FILE, OUTPUT_TRAJECTORIES)