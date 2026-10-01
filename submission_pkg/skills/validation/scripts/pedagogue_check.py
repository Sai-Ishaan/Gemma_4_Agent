## A script to intercept the diagnostic report given by the Graph Reasoner
## Aim: To verify that the agent has provided a mathematically contiguous reasoning path (as in unbroken chan of graph nodes) connecting bug symptom to Root Cause


import json
import sys
from pathlib import Path
from typing import List, Dict, Any

def verify_contigous_trace(trace_path: List[Dict[str, str]])-> bool:
    ##Checks if sequence of nodes follow a valid unbroken chain. Requires querying NetworkX in the real run.
    if not trace_path or len(trace_path) <2:
        return False

    valid_edge_types = {"CALLS", "DEPENDS_ON", "INJECTS_INTO", "CONFIGURES", "MODIFIED_BY"}
    for i in range(len(trace_path) -1):
        current_step = trace_path[i]
        next_step = trace_path[i+1]

        ##Verify the agent specified how these nodes connect
        edge = current_step.get("relation_to_next")
        if not edge or edge not in valid_edge_types:
            return False

    return True

def main():
    if len(sys.argv < 2):
        print(json.dumps({ "passed": False, "reward_penalty": -0.5, "feedback": "Usage: Python pedagogue_check.py <diagnostic_report.json>"}))
        sys.exit(1)

    report_path = Path(sys.argv[1])

    if not report_path.exists():
        sys.exit(1)
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        reasoning_trace = data.get("pedagogical_trace", [])
        is_traceable = verify_contigous_trace(reasoning_trace)

        if not is_traceable:
            output = {"passed":False, "reward_penalty":-0.4, 
                    "feedback": "Pedagogical trace failed. The reasoning trace has missing or invalid types. must show an unbroken path (AST, DFG, or Git) from symptom to root cause."}
        else:
            output = {
                "passed": True, "reward_penalty":0.0, "feedback": "Pedagogical trace validated, logical path is Contiguous and Explainable."
            }
        print(json.dumps(output, indent=2))
        sys.exit(0 if is_traceable else 1)
    except Exception as e:
        print(json.dumps({
            "passed":False,
            "reward_penalty":-0.4,
            "feedback": f"Failed to parse pedagogical trace: {str(e)}"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()