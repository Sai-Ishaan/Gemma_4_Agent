# Phase 1 — Local Orchestration and Deterministic Guardrails

**Project:** Gemma 4 Developer Agent   
**Status:** Initial implementation demonstrated; further validation required  
**Primary objective:** Establish a local agent-orchestration workflow with deterministic validation mechanisms that assess generated code changes and return structured feedback.

---

## 1. Objective

Phase 1 establishes the initial local execution and validation infrastructure for the proposed code-generation and refinement system.

The phase focuses on three principal elements:

1. Local model orchestration through Ollama.
2. Tool-mediated code execution and repair operations.
3. Deterministic guardrails for syntax validation, patch-scope validation, and structural pedagogical-trace validation.

The intention is to separate model-generated decisions from deterministic validation. The model proposes a code change, while external validation scripts assess selected properties of the proposed change.

This phase establishes an initial prototype. It does not yet demonstrate the effectiveness of the complete proposed architecture or establish behavioural correctness across a benchmark.

## 2. Architecture and Execution Components

### 2.1 Local Model Orchestration

**File:** `local_agent_runner.py`

This script establishes a basic interaction between a locally hosted language model and a Python execution tool.

The current implementation:
- Connects to Ollama.
- Uses `llama3.2:3b` as the current placeholder model.
- Provides a tool interface for executing Python snippets.
- Allows the model to request tool execution through its tool-calling interface.
- Returns tool execution results to the model.
- Limits the interaction loop to a configured number of turns.

The script demonstrates basic local model-to-tool orchestration.

**Current limitation:** This runner does not integrate the syntax, scope, or pedagogical guardrail scripts. It also does not implement persistent patch generation or repository-level repair validation.

### 2.2 Model-Connected Repair Workflow

**File:** `local_repair_agent.py`

This script implements the initial model-connected repair-and-validation workflow.

The current implementation:
1. Creates a temporary workspace.
2. Creates a Python source file containing a controlled defect in `calculate_discount`.
3. Defines a diagnostic report containing the permitted modification scope.
4. Supplies the original source and repair task to the local model.
5. Exposes an `apply_and_validate_patch` tool to the model.
6. Receives the model-proposed complete source and patch text.
7. Writes the proposed source into the temporary target file.
8. Writes the supplied patch text into a separate candidate patch file.
9. Invokes the syntax validator against the target source.
10. Invokes the scope validator against the supplied patch and diagnostic report.
11. Combines the validation results and penalty values.
12. Returns structured feedback to the model.
13. Allows the model to produce a subsequent response.

The demonstrated workflow therefore connects model-generated repair proposals to deterministic syntax and declared-scope checks.

**Important implementation distinction:** The current workflow writes the model-proposed complete source directly into the target file. It does not apply the supplied unified diff to the original file. The supplied diff is inspected separately. Consistency between the proposed source and diff has not yet been established.

**Current limitations:**
- Behavioural regression tests are not integrated.
- The pedagogical-trace validator is not integrated into this repair workflow.
- Graph-grounded retrieval and graph-edge verification are not implemented in this workflow.
- Patch/source consistency is not verified.
- Execution occurs in a temporary workspace, but the workspace is not a hardened security sandbox.
- The supplied execution output does not independently establish behavioural correctness.

### 2.3 Temporary Execution Environment

**File:** `sandbox_repl.py`

This script provides a temporary Python execution mechanism.

The current implementation:
- Creates a temporary directory.
- Writes a supplied Python snippet to a temporary file.
- Executes the file through a Python subprocess.
- Applies a timeout.
- Returns execution status, exit code, standard output, and standard error.

This provides temporary-file isolation and execution-time limits for the demonstrated workflow.

It must not be described as a secure operating-system-level sandbox. Filesystem access, network access, and other process capabilities are not comprehensively restricted.

### 2.4 Deterministic Validation Scripts

The validation scripts are located under:

`submission_pkg/skills/validation/scripts/`

#### A. Syntax validation

**File:** `syntax_check.py`

Purpose:
- Parse supplied Python files using Python's AST facilities.
- Identify syntax-invalid files.
- Return structured validation results.
- Assign a penalty of `-1.0` when syntax validation fails.

Current boundary:
- Validates Python syntax.
- Does not establish semantic correctness.
- Does not independently establish that the program's intended behaviour is correct.
- Does not replace behavioural regression testing.

#### B. Patch-scope validation

**File:** `scope_check.py`

Purpose:
- Read permitted paths from a diagnostic report.
- Extract modified paths from patch text.
- Compare the modified paths against the declared permitted scope.
- Identify unauthorized modifications.
- Return structured validation results and a scope-related penalty.

The simulated scope-creep scenario demonstrated detection of an unauthorized file named `unauthorized_core.py`.

Current limitations:
- Empty or missing scope definitions can currently pass validation.
- Patch extraction relies on a simplified interpretation of diff headers.
- Path normalization and repository-root enforcement are incomplete.
- The validator checks patch text rather than independently inspecting the resulting repository state.

These limitations must be addressed before treating the validator as a robust repository-integrity mechanism.

#### C. Pedagogical-trace validation

**File:** `pedagogue_check.py`

Purpose:
- Validate the structure of a supplied `pedagogical_trace`.
- Check that the trace contains the minimum required number of entries.
- Check that intermediate entries contain the expected fields.
- Check relation labels against an accepted set:
  - `CALLS`
  - `DEPENDS_ON`
  - `INJECTS_INTO`
  - `CONFIGURES`
  - `MODIFIED_BY`
- Return a structured result and a penalty of `-0.4` when the tested structural conditions fail.

Current limitation:

The validator checks the structure and allowed relation labels. It does not independently verify that the represented relationships exist in an actual repository dependency graph.

It should therefore be described as a structural pedagogical-trace validator, not a graph-grounded reasoning verifier.

### 2.5 Simulated Guardrail Harness

**File:** `mock_agent.py`

This script provides four constructed scenarios for testing the deterministic validation mechanisms.

| Scenario | Purpose | Expected result |
|---|---|---|
| A | Valid code, permitted patch scope, structurally valid pedagogical trace | All checks pass |
| B | Python syntax error | Syntax failure detected; penalty `-1.0` |
| C | Modification outside declared scope | Unauthorized path detected |
| D | Invalid pedagogical-trace relation | Structural validation failure; penalty `-0.4` |

The harness tests expected pass and failure paths using constructed artifacts. It does not invoke the local language model to generate these scenarios.

## 3. Observed Execution Results

Two separate executions were observed.

### 3.1 Model-Connected Repair Execution

**Command:**

`python .\local_repair_agent.py`

**Target:** `src/math_ops.py`

**Task:** Correct the control-flow inversion defect in `calculate_discount` without violating the declared modification scope.

**Observed execution:**
- The agent invoked `apply_and_validate_patch`.
- The validation tool returned `guardrail_passed: true`.
- The combined reward penalty was `0.0`.
- AST syntax validation passed.
- Declared patch-scope validation passed.
- The model subsequently returned a final response.

**Observed validator output:**

- Syntax feedback: `All modified files passed AST syntax validation.`
- Scope feedback: `Patch complies with defined scope.`

**Interpretation:**

This execution demonstrates that the local model can participate in a tool-mediated repair workflow and receive deterministic syntax and scope-validation feedback.

It does not establish that the repaired function passes behavioural tests. No independent behavioural test result was included in this execution record.

### 3.2 Simulated Guardrail Harness Execution

**Command:**

`python .\mock_agent.py`

**Observed results:**

| Scenario | Observed output | Result |
|---|---|---|
| A — Happy path | Syntax PASS; Scope PASS; Pedagogy PASS | Expected pass |
| B — Syntax failure | Syntax error caught; penalty `-1.0` | Expected failure detected |
| C — Scope violation | Unauthorized `unauthorized_core.py` intercepted | Expected failure detected |
| D — Pedagogical-trace failure | Broken trace flagged; penalty `-0.4` | Expected failure detected |

**Overall observed result:** All four constructed scenarios completed with their expected outcomes.

**Interpretation:**

The harness provides initial evidence that the implemented validators respond as expected to the four tested scenarios. It does not establish exhaustive validator correctness or generalization to arbitrary repository changes.

## 4. Phase 1 Evidence and File Mapping

| Evidence or responsibility | File |
|---|---|
| Local model and tool orchestration | `local_agent_runner.py` |
| Model-connected repair workflow | `local_repair_agent.py` |
| Temporary Python execution | `sandbox_repl.py` |
| Simulated guardrail scenarios | `mock_agent.py` |
| Python AST validation | `submission_pkg/skills/validation/scripts/syntax_check.py` |
| Declared patch-scope validation | `submission_pkg/skills/validation/scripts/scope_check.py` |
| Pedagogical-trace structure validation | `submission_pkg/skills/validation/scripts/pedagogue_check.py` |

The two observed console executions are the initial execution evidence for this phase. Persistent copies of their complete raw outputs should be maintained separately from this summary.

## 5. Current Implementation Status

| Capability | Status |
|---|---|
| Local Ollama model integration | Demonstrated in execution |
| Model tool-calling interface | Demonstrated in execution |
| Model-connected repair tool | Demonstrated in execution |
| Temporary workspace | Implemented |
| Python AST syntax validation | Demonstrated in both harness and repair execution |
| Declared patch-scope validation | Demonstrated in both harness and repair execution |
| Structural pedagogical-trace validation | Demonstrated in simulated harness |
| Validation feedback returned to model | Demonstrated in repair execution |
| Behavioural regression testing | Not yet integrated |
| Patch/source consistency verification | Not implemented |
| Fail-closed scope validation | Not implemented |
| Graph-edge verification | Not implemented |
| Graph-based repository retrieval | Not demonstrated in this phase |
| Persistent structured experiment records | Not yet established |
| Gemma 4 integration and fine-tuning | Future work |

## 6. Outstanding Work

The following work is required to strengthen Phase 1.

### 6.1 Behavioural Validation

Introduce deterministic tests for `calculate_discount` so that a patch is not accepted solely because it is syntactically valid and within the declared scope.

### 6.2 Patch Integrity

Ensure that the patch being validated corresponds to the source being written into the target file. A derived diff or an actual diff-application workflow should replace the current independent handling of source and patch text.

### 6.3 Fail-Closed Scope Validation

Reject missing, malformed, or empty authorized-scope definitions rather than treating the absence of scope constraints as a successful validation.

### 6.4 Validator Robustness

Improve path normalization, diff parsing, and exception handling. Expand tests beyond the four currently constructed scenarios.

### 6.5 Reproducible Execution Records

Persist structured records containing:
- Task identifier.
- Model identifier.
- Initial source.
- Proposed source or patch.
- Syntax-validation result.
- Scope-validation result.
- Behavioural-validation result.
- Penalty values.
- Final outcome.

### 6.6 Integration Boundaries

Decide whether pedagogical-trace validation belongs in the model-connected repair tool and define how repository graph evidence will be supplied and independently checked.

## 7. Phase Completion Criteria

Phase 1 should not be considered complete merely because the simulated harness passes.

The phase should be considered ready for the next development stage only after:
1. Model-connected repair execution is reproducible.
2. Syntax and scope checks operate on the actual resulting change.
3. Patch integrity is verified.
4. Behavioural regression checks are integrated.
5. Missing or invalid scope definitions fail safely.
6. Execution outcomes are recorded in a reproducible format.
7. The limitations of the current diagnostic validation are documented.

## 8. Relationship to Subsequent Phases

Phase 1 establishes the initial local orchestration and deterministic validation foundation.

It does not yet implement the complete bounded graph-retrieval mechanism, synthetic curriculum generation, trajectory collection, preference-based training, or Gemma 4 fine-tuning described in the broader project roadmap.

These remain separate development objectives and should be evaluated in their respective phases.

---

**Current conclusion:** Phase 1 has progressed beyond a simulated-only guardrail prototype. A local model-connected repair workflow has been demonstrated, alongside a separate four-scenario guardrail harness. The current evidence supports an initial orchestration and validation prototype, while behavioural correctness, patch integrity, and robust scope enforcement remain outstanding.