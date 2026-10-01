### Scope Enforcement Guardrail
### Goal: To compare modified files in a patch against authorised files found by Graph Reasoner Sub Agent and penalise scope creep and unitended edits

import re
import sys
import json
from pathlib import Path
from typing import Set, List, Dict, Any

def extract_authorized_files(report_path: Path) -> Set[str]:
    ## Extract approved paths from Reasoner diagnostic report JSON
    if not report_path.exists():
        return set()
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        authorized = set()

        for item in data.get("primary_target_symbols", []):
            if "file_path" in item: ## extracting from primary target symbols
                authorized.add(str(Path(item["file_path"]).as_posix()))

        for scope_entry in data.get("suggested_investigation_scope", []):
            clean_path = scope_entry.split(":")[0].strip()
            if clean_path:
                authorized.add(str(Path(clean_path).as_posix()))

        return authorized
    
    except Exception:
        return set()        

def extract_patch_modified_files(patch_path: Path)-> Set[str]:
    if not patch_path.exists():
        return set()

    patch_text = patch_path.read_text(encoding="utf-8")

    ### Matches `diff --git a/path_to_file` 
    pattern = re.compile(r"^--- a/(.+)$", re.MULTILINE)

    matches = pattern.findall(patch_text)

    modified_files = set()
    for file_str in matches:
        if file_str!= "/dev/null":
            modified_files.add(str(Path(file_str).as_posix()))
    return modified_files

def main():
    if len(sys.argv) <3:
        print(json.dumps({"passed":False, "reward_penalty": -0.5, "feedback":"Usage: python scope_check.py <diagnostic_report.json> <changes.patch>"}))
        sys.exit(1)

    report_path = Path(sys.argv[1])
    patch_path = Path(sys.argv[2])

    authorized_files = extract_authorized_files(report_path)
    modified_files = extract_patch_modified_files(patch_path) 

    if not authorized_files:
        output = {
            "passed": True,
            "reward_penalty": 0.0,
            "unauthorized_files" : [],
            "feedback": "NO Scope Constraints defined in Diagnostic Report"
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)

    unauthorized = modified_files - authorized_files

    has_violation = len(unauthorized)>0
    penalty = -0.5*len(unauthorized) if has_violation else 0.0

    op = {
        "passed": not has_violation,
        "reward_penalty": penalty,
        "authorized_scope": sorted(list(authorized_files)),
        "modified_files": sorted(list(modified_files)),
        "unauthorized_files": sorted(list(unauthorized)),
        "feedback": f"Scope violation detected! Modified files outside scope: {sorted(list(unauthorized))} " if has_violation else "Patch complies with defined scope."
    }

    print(json.dumps(output, indent=2))
    sys.exit(1 if has_violation else 0)

if __name__ == "__main__":
    main()