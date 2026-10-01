### Phase 1 local harness.
## Creates temporary mock files, simulates agent synthetic output (valid and invalid ones), executes the syntax, scope and pedagogue check scripts in subprocesses without LLM
# Goal is to see if the exact JSON penalty structures and exit codes are returned

import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SCRIPTS_DIR = WORKSPACE_ROOT / "submission_pkg"/"skills"/"validation"/"scripts"

SYNTAX_SCRIPT = SCRIPTS_DIR/"syntax_check.py"