### Phase 0: Mock Repository Evaluation Specification
- What is it: An evaluation-design phase.

- Purpose: 
   *To establish a compact, deterministic evaluation contract before expanding the guardrails, graph retrieval, synthetic data generation or model training. 
   * To make sure the policies work before moving to the actual model training and finetuning.
   * Before moving to applying reliable guardrails into agent execution, we must know the defects, deterministic test results to see where agent can 'make-or-break'. Hence, It is essential to have machine-readable run-records

- Status: Proposed Specifications ; Implementation and Measurements Pending.

#### Objective
To build a Python mock repository and set a repair tasks that establishes whether the agent can do the following tasks properly:
  i) To Repair a clearly identified single-function defect or issue.
 ii) To understand and abide to explicit developer scope and protected-file constraints.
 iii) To retrieve a small dependency neighborhood when the target function alone isn't sufficient.
 iv) To avoid unrelated patches and edits as well as resist misleading context.
  v) To be able to handle ambiguous requets by asking for clarification from the developer rather than hallucinating or inventing requirements.
 vi) To use test failures as evidence and recover from bad attempts.
 vii) Return structured, reproducible outcomes, that can later support reward and preference-data generation.

#### Initial Benchmark Design
![alt text](image.png)

Each benchmark task-case will be recorded in the following format:
{
  "task_id": "P0-01",
  "category": "single_function_repair",
  "base_revision": "recorded_git_commit",
  "issue": "Task description visible to the agent",
  "target_hint": "Optional initial file or function",
  "protected_paths": ["tests/"],
  "test_command": "python -m pytest",
  "acceptance_checks": ["check_id_1"],
  "expected_behavior": "Evaluator-only expected behavior"
}

#### Scope, Goals and Non-Goals
(I) In Scope
   - Python Only
   - A small, locally generated mock repository
   - Single-function repair as the default unit of work
   - A small number of multi-file and two-hop dependency cases.
   - A simple baseline agent/policy and deterministic evaluation harness
   - Explicit tests, protected paths, expected outcomes and repeatable starting states.
   - Standard engineering metrics and later comparison with the official competition evaluation

(II) Out of Scope for the First Iteration alone
   - Full repository Graph Based (AST, DFG) and Git DAG indexing
   - A large scale load testing
   - A claim of production-grade virtually secure sandboxing
   - Multi-language support
   - Training or Reward Optimization before the labels and evaluation contract are reliable
   - Using the same examples for both training and final held-out evaluation

#### Mock Repository Design (Initial)
mock_python_repo/
├── README.md
├── src/
│   ├── discounts.py
│   ├── pricing.py
│   ├── inventory.py
│   └── formatting.py
├── tests/
│   ├── test_discounts.py
│   ├── test_pricing.py
│   ├── test_inventory.py
│   └── test_formatting.py
├── fixtures/
│   └── task_manifest.json
└── .git/

- This structure is subjected to change as we progress. It is kept deliberately small and comprehensible. 

- Each bug shall have a stable task ID, a clean initial commit, a task description, explicit constraints, a test command, and a known expected outcome

#### Task manifest fields
Each task should record the following:
- `task_id`: A stable unique identifier
- `category`: In-Scope, Dependency, Out-Of-Scope, Misleading Concepts
- `base_revision`: Clean starting revision or deterministic fixture identifier.
- `issue`: User-facing request
- `target_hint`: Optional function or file hint, not necessarily the final answer.
- `protected_paths`: Files the agent must not change.
- `test_command`: Controlled test invocation
- `expected_behavior`: Repair, Reject, Clarify or Expand Context
- `acceptance_checks`: Objective conditions used by the evaluator
- `Notes`: Known limitations and logic.

#### Expected Behavior Contract
For each task, both the Outcome and the Process have to be evaluated

**Outcome**
 - The proposed patch applies to the exact base revision
 - Only authorised paths are modified
 - The code parses
 - Targeted tests meet the task's acceptance criteria
 - Existing regression tests remain Green
 - Final response accurately reports what was tested and what wasn't
 - Protected tests and fixtures aren't modified to 'Hack' to success

**Process** 
 - The agent begins with the supplied target context and expands only when required to do so.
 - Retrieved graph edges or historical entries include provenance (eg: source file and symbol)
 - A failed check is returned as structured feedback.
 - The agent may attempt a bounded correction after feedback.
 - The agent stops after a configured attempt or resource budget constraints.
 - The developer retains final authority to accept or reject the proposed patch.

At the end, the correct final patch is our primary outcome. A well-informed explanation or trace that comes with it is our auxiliary evidence and must NOT compensate for a patch that violates hard constraints.

#### Guardrail and Reward Policy
In our initial approach, we are going for a Two-Layer evaluation policy, encompassing Constraints Success/Faolures and Signals:

**Layer I: Hard Constraints**
Hard constraint failures should produce a rejected outcome and a machine-readable reason. 
A violation cannot be offset by success at another dimension:
- Protected-path or explicit scope violation
- Test modification intended by bypass acceptance checks
- Patch cannot be applied to the evaluated base revision
- Execution exceeds the configured resource limit
- The result can't be tied to the exact patch that was validated. Scalar reward system alone doesn't guarantee rules are enforced.

**Layer II: Graded Signals**

For candidates that don't violate hard constraints, the following metrics are recorded:
- Targeted-test success
- Regression-test success
- Syntax Validity
- Minimality/unrelated-diff size
- Evidence quality for diagnosis and retrieved context
- Number of tool calls and execution attempts
- Context tokens, graph nodes, and historical entries that are retrieved
- Latency and Resource usage
- Whether the agent has recovered after actionable failure feedback

Reward coefficients aren't finalised until the harness produces reliable measurements and representative failures have beenr eviewed. 

#### Baselines and Comparison Plan
Starting with baselines that can be easily reproducible:
 - **Target-Only Baseline:** Model receives the issue and target file/function context, first without the graph expansion.
 - **Graph-guided baseline:** Same model and issue, with bounded-graph retrieval enabled
 - **Graph and Execution-Feedback baseline:** The same retrieval policy along with test/syntax/scope feedback and a bounded repair loop.
 - **Post-training comparison (For Later Stages):** Compare the base model and post-trained Gemma 4 under the same tool, context, task and resource budgets.

Model settings, maxiumum turns, tool availability, token budgets, and test commands are kept fixes across comparisons, wherever possible. 

For our initial phase, Llama 3.2:3b via Ollama acts as a placeholder, which can help debug orchestration and data collection. It will NOT be used to claim Gemma 4 capability or post-training gains.

#### Metrics
The following metrixs are taken into considering:
 - **Task Completion Rate:** Tasks meeting their specified expected behavior
 - **Repair Success Rate:** Repair tasks whose required acceptance tests pass.
 - **Regression Rate:** Candidate patches that break previously passing tests.
 - **Scope Compliance:** Fraction of tasks with no unauthorised changes; report hard violations separately
 - **Patch Applicability Rate:** Candidate patches that apply to the evaluated base revision.
 - **Syntax-validity Rate:** Patches that leave modified Python files syntatically valid.
 - **Clarification/Rejection Quality:** Ambiguous and out-of-scope tasks handled correctly.
 - **Tool Efficiency:** Tool calls and execution attempts per task and per successful repair.
 - **Context Cost:** Prompt tokens, graph nodes/edges, and history items retrieved.
 - **Failure Recovery Rate**: Failed first attempts that become valid repairs after feedback.
 - **Latency and Resource Usage:** Wall-Clock time and Available CPU/GPU/Memory Measurements

#### Relationship to Standard Benchmarks
The mock repository is a fast development and regression suite, not a complete replacement for external benchmark evaluation.

Once the agent is able to complete the local worflow reliably and efficiently, we align a separate evaluation with Official gemma 4 Developer Agent competition harness and its supported model/submission requirements. Any additional benchmark (such as compatabile subset of SWE-Bench) should be selected only after checking task format, environmental cost, licensing/data constraints, and whether it tests the project's actual claims.

#### Phase 0 exit criteria
Phase 0 is ready to close when:
- [Yes] The mock repository can be restored deterministically for every
  task.
- [Yes] The initial task manifest has stable IDs and objective
  acceptance checks.
- [Yes] In-scope, out-of-scope, ambiguous, dependency,
  misleading-context, and regression scenarios are represented.
- [Yes] The evaluator checks the exact patch that is applied.
- [Yes] Hard constraints are reported separately from graded metrics.
- [Yes] A target-only baseline can run end to end and produce structured
  results.
- [Yes] Results include failed and incomplete runs, context/tool costs,
  and test outcomes.
- [Yes] Training examples and held-out evaluation tasks are separated.
- [Yes] Known limitations and any unimplemented checks are documented.
Phase 0 does not require high repair accuracy. Its purpose is to make
failures interpretable and comparisons reproducible before the system
becomes more complex.

#### Phase 0 Implementation Checklist
- [Done!] Define the manifest schema and stable task IDs.
- [Done!] Create the mock Python repository and its initial passing tests.
- [Done!] Record a clean starting revision for every benchmark task.
- [Done!] Implement evaluator checks for patch applicability, syntax, tests, regressions, and protected paths.
- [Done!] Verify that the evaluator checks the exact code that was executed.
- [Done!] Produce one machine-readable result for both successful and failed runs.

#### Observations after Running Mock Repository:
```python -m pytest -v
======================== test session starts ========================
platform win32 -- Python 3.11.5, pytest-8.4.2, pluggy-1.7.0 -- E:\Gemma_4_Agent\mock_python_repo\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Gemma_4_Agent\mock_python_repo
configfile: pytest.ini
testpaths: tests
collected 16 items                                                   

tests/test_discounts.py::test_discount_rate_boundaries[0-0.0] PASSED [  6%]
tests/test_discounts.py::test_discount_rate_boundaries[99.99-0.0] PASSED [ 12%]
tests/test_discounts.py::test_discount_rate_boundaries[100-0.05] PASSED [ 18%]
tests/test_discounts.py::test_discount_rate_boundaries[499.99-0.05] PASSED [ 25%]
tests/test_discounts.py::test_discount_rate_boundaries[500-0.1] PASSED [ 31%]
tests/test_discounts.py::test_discount_rate_boundaries[750-0.1] PASSED [ 37%]
tests/test_discounts.py::test_discounted_total PASSED          [ 43%]
tests/test_formatting.py::test_currency_format PASSED          [ 50%]
tests/test_formatting.py::test_invalid_currency_rejected PASSED [ 56%]
tests/test_inventory.py::test_available_quantity PASSED        [ 62%]
tests/test_inventory.py::test_can_fulfill PASSED               [ 68%]
tests/test_inventory.py::test_negative_inventory_rejected PASSED [ 75%]
tests/test_pricing.py::test_order_price_applies_discount PASSED [ 81%]
tests/test_pricing.py::test_order_price_without_discount PASSED [ 87%]
tests/test_pricing.py::test_negative_inputs_rejected[-1-2] PASSED [ 93%]
tests/test_pricing.py::test_negative_inputs_rejected[1--2] PASSED [100%]

======================== 16 passed in 0.08s =========================
(.venv) PS E:\Gemma_4_Agent\mock_python_repo> python -m pytest .\tests\test_discounts.py -v
======================== test session starts =========================
platform win32 -- Python 3.11.5, pytest-8.4.2, pluggy-1.7.0 -- E:\Gemma_4_Agent\mock_python_repo\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Gemma_4_Agent\mock_python_repo
configfile: pytest.ini
collected 7 items                                                     

tests/test_discounts.py::test_discount_rate_boundaries[0-0.0] PASSED [ 14%]
tests/test_discounts.py::test_discount_rate_boundaries[99.99-0.0] PASSED [ 28%]
tests/test_discounts.py::test_discount_rate_boundaries[100-0.05] PASSED [ 42%]
tests/test_discounts.py::test_discount_rate_boundaries[499.99-0.05] PASSED [ 57%]
tests/test_discounts.py::test_discount_rate_boundaries[500-0.1] PASSED [ 71%]
tests/test_discounts.py::test_discount_rate_boundaries[750-0.1] PASSED [ 85%]
tests/test_discounts.py::test_discounted_total PASSED           [100%]

========================= 7 passed in 0.10s ==========================
(.venv) PS E:\Gemma_4_Agent\mock_python_repo> Get-Content .\src\discounts.py
### Discount policy for Phase 0 Mock Repo

def discount_rate(subtotal: float)->float:
    if subtotal<100:
        return 0.0 ## 0% below 100
    if subtotal < 500:
        return 0.05 ## 5% from 100 to <500
    return 0.10 ## 10% from 500 and above

def discounted_total(subtotal: float)-> float:
    return round(subtotal * (1.0 -discount_rate(subtotal)), 2)


python -c "import json, jsonschema; d=json.load(open('fixtures/tasks.json', encoding='utf-8')); s=json.load(open('fixtures/task.schema.json', encoding='utf-8')); jsonschema.validate(d, s); print('Manifest schema validation: PASS')"
Manifest schema validation: PASS    
```

The current tests imply that the existing behavior of the scripts is according to the tests at present. But it doesn't cover every possible bug.

Taking the example of `discounts.py`:

```
def discount_rate(subtotal: float)->float:
    if subtotal<100:
        return 0.0
    if subtotal < 500:
        return 0.05
    return 0.10
```

The policy currently implemented:
![alt text](image-1.png)

This serves as a clean, good reference

#### Implementation Log and Milestone Status
**(I) Milestone 1: Environment and Clean Baseline**
 - **Status**: Verified for all the items in checklist below
 - **Environment**
   * Working directory: E:\Gemma_4_Agent\mock_python_repo
   * Python 3.11.5
   * OS: Windows (win32)
   * Test Runner: pytest 8.4.2 in the mock repo's .venv
**Verified Checklist**
   - [Yes] Python Executes from the mock environment
   - [Yes] Discount specific suite: 7 passed in 0.10 seconds
   - [Yes] Full baseline suite: 16 passed in 0.08 seconds
   - [Yes] Public task manifest validates against JSON schema
   - [Yes] Discount policy and tested boundary behavior inspected
   - [Yes] Independent Git history for the mock repository
   - [Yes] Reproducible reset to a clean benchmark revision
   - [Yes] Task-specific faulty revision
   - [Yes] Acceptance tests that Detect defects
   - [Yes] Exact-patch evaluation and structured run results
   - [Yes] Write a JSON run record after failure

**Evidence**
   - Terminal output above
   - Git repository
   - git status --short --ignored reports mock_python_repo as ignored by the parent repository.

**Interpretation**
    - The clean mock repository passes its current baseline tests. This establishes a reference state, not agent repair performance or benchmakr readiness

**(II) Milestone2: Reproducible Benchmark Baseline**

**Status**: Verified
 - [Done] Confirm the mock repository has no existing nested Git metadata.

 - [Done] Initialize an independent Git repository without modifying the parent repository's tracking configuration.

 - [Done] Commit the clean mock repository as a named baseline revision.

 - [Done] Verify the baseline commit passes all tests.

 - [Done] Record the baseline commit hash and test output.
**Limitations:** The commit establishes a clean reference state but not that repair evaluation works. Yet to implement task-specific fault revisions, reset orchestration with test scripts, hidden-test execution, patch evaluation etc:-

Introducting a controlled defect by changing the comparison operator.

First, a baseline backup was created before mutating the source file using:
```
Copy-Item .\src\discounts.py .\discounts.py.baseline-backup 
```
You can change the condition manually or use:
```
(Get-Content .\src\discounts.py -Raw).Replace( 'if subtotal<100:', 'if subtotal<=100:') | Set-Content .\src\discounts.py -NoNewline
```

**(III) Milestone 3: P0-01 Boundary-Defect Fixture** 

**Status**: Verified
**Observation**:
```python -m pytest .\tests\test_discounts.py -v
======================== test session starts ========================
platform win32 -- Python 3.11.5, pytest-8.4.2, pluggy-1.7.0 -- E:\Gemma_4_Agent\mock_python_repo\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: E:\Gemma_4_Agent\mock_python_repo
configfile: pytest.ini
collected 7 items                                                    

tests/test_discounts.py::test_discount_rate_boundaries[0-0.0] PASSED [ 14%]
tests/test_discounts.py::test_discount_rate_boundaries[99.99-0.0] PASSED [ 28%]
tests/test_discounts.py::test_discount_rate_boundaries[100-0.05] FAILED [ 42%]
tests/test_discounts.py::test_discount_rate_boundaries[499.99-0.05] PASSED [ 57%]
tests/test_discounts.py::test_discount_rate_boundaries[500-0.1] PASSED [ 71%]
tests/test_discounts.py::test_discount_rate_boundaries[750-0.1] PASSED [ 85%]
tests/test_discounts.py::test_discounted_total FAILED          [100%]

============================= FAILURES ==============================
______________ test_discount_rate_boundaries[100-0.05] ______________

subtotal = 100, expected = 0.05

    @pytest.mark.parametrize(("subtotal", "expected"), [(0,0.0),(99.99,0.0),(100,0.05),(499.99,0.05),(500,0.10),(750,0.10)])
    def test_discount_rate_boundaries(subtotal, expected):
>       assert discount_rate(subtotal) == expected
E       assert 0.0 == 0.05
E        +  where 0.0 = discount_rate(100)

tests\test_discounts.py:6: AssertionError
_______________________ test_discounted_total _______________________

    def test_discounted_total():
>       assert discounted_total(100.0) == 95.0
E       assert 100.0 == 95.0
E        +  where 100.0 = discounted_total(100.0)

tests\test_discounts.py:9: AssertionError
====================== short test summary info ======================
FAILED tests/test_discounts.py::test_discount_rate_boundaries[100-0.05] - assert 0.0 == 0.05
FAILED tests/test_discounts.py::test_discounted_total - assert 100.0 == 95.0
==================== 2 failed, 5 passed in 0.18s =================
```

Status: Verified
  - [Done] Create a task-specific faulty revision from the clean baseline.

  - [Done] Verify the intended acceptance test fails on the faulty revision.

  - [Done] Verify the clean baseline passes that test.

  - [Done] Verify unrelated baseline tests remain understood and accounted for.

  - [Done] Record the exact faulty revision, test command, and observed outcomes. 

**(IV) Milestone 4: Reproducibility Check**
- **Target Design**:
  [Clean_Baseline] ----(Apply one deliberate mutation)--->[Faulty_P0-01_revision(Expected_failure)]-----(Switch back to clean version)--->[Reset_Verification(Source_Restored_And_Tests_Passed)]

- **Status** : Verified Initial test-oracle check
- **Mutation**: Changed the first condition in src/discounts.py from subtotal < 100 to subtotal <=100
- **Restoration**: Restored src/discounts.py from the pre-mutation backup

- **Experiment**:
 * Run the following commands:

```git status --short
   git diff -- .\src\discounts.py
   git diff --check 
```

- **Observation**:
 * The first command gave `?? discounts.py.baseline-backup`, which means only the temporary backup is untracked.
 * The second and third ones gave no output. Which can be concluded that the tracked source matches the committed baseline, and that there were no whitespace errors detected while checking diff.
 * The original source has been restored, while the backup remains untracked.
 * After restoration, all test suites passed. No errors nor changes were detected.

**(V) Milestone 5: Invalid Patch Rejection and Negative Path Validation**
- **Approach**: Using a set of PowerShell scripts to see if a faulty patch is being accepted and committed.
- **Experiment**:
    * Run the PowerShell script against the src file:
     ``` Eg:- git -C "\Gemma_4_Agent\p0-01-evaluation" restore -- src/discounts.py
     ```
    ```
    git -C "E:\Gemma_4_Agent\p0-01-evaluation" status --short
    ``` 

    * If nothing showed up it means that the work tree is clean and the previous candidate repair won't be contaminating the next experiment. Once comfirmed move to the next set of evaluations:

``` 
"$invalidPatch = "\Gemma_4_Agent\candidate_p0_01_invalid.patch"

@'
diff --git a/src/discounts.py b/src/discounts.py
--- a/src/discounts.py
+++ b/src/discounts.py
@@ -999,3 +999,3 @@
-THIS_LINE_DOES_NOT_EXIST
+THIS_LINE_STILL_DOES_NOT_EXIST
'@ | Set-Content -LiteralPath $invalidPatch -Encoding ascii
Get-Content $invalidPatch"
```
    
  * The above patch references a non-existent line, designated to be rejected rather than repair the defect. Once done, run the evaluator against the invalid patch:
  
  ```.\scripts\evaluate_p0_01.ps1 -PatchPath "\Gemma_4_Agent\candidate_p0_01_invalid.patch"```

  * An invalid patch was defined, which, unlike other patches, has a consistent one-line hunk. Though it might be parseable, the original line won't match the first line of the src file. (in this case, src/discounts.py)
  
**Observation:**
  - The evaluator stopped and recorded the invalid patch withour accepting. 
  - The evaluation is recorded in JSON format.
  - No source modification was left behing since worktree status was empty afterwards.
  -Failed attempt doesn't leave candidate source changes in the eval worktree

**(VI) Milestone 6: Testing Protected-Path Enforcement**
  - Purpose: To verify that passing tests alone cannot override the scope policy and ensure the evaluator rejects attempted modifications in protected test files and paths.

  - **Procedure**:
       * First, we establish a Baseline worktree state: Reset the evaluation worktree to the known faulty base commit using safe reset harness
       * A candidate patch is generated, which can include the correct line source repair in the component at hand, while making an unpermitted change at the same time to a protect path. (tests)
       * The evaluation script is executed against the protected path candidate patch
       * The generated run record is stored in JSON format under `runs/` directory. Helps us check the worktree git status to confirm clean slate and containment.
       * Using command lines, unauthorised commits (harmless) are performed on the test scripts ony at the patch-authoring worktree, not the evaluation worktree. 


**Observations so far:**
  - A valid one-line boundary fix successfully passes all target and full-suite test assertions. The scope and files remain intact, and untouched

  - The evaluator correctly detects corrupt syntaces and incompatible source line contexts, and that too without changing the worktree.

  - Scope and Protected-path integrity remains and confirms that the deterministic evaluation approaches enforces policy boundaries irrespective of whether functional tests pass or not. This prevents reward hacking or rule tampering by the Generative Agents. 

  - The diff confirms the real P0-01 repair and harmless comment in protected testfile

  - Passing functional tests does not override the scope policy

  - The negative path experiment tested with an in-scope patch and the evaluator rejected any patch with a defect in it.

#### What is being demonstrated so far via Recorded Runs:
  - A valid, in-scope patch can be accepted.
  - A patch that leaves a failing candidate test is rejected.
  - A patch that changes a protected test file can be rejected even when the test passes.
  - Baseline-signature mismatch and a dirty main repository can pause/stop evaluation
  - Corrupt and non-applying patches can be rejected.

#### What isn't Demonstrated yet:
  - That The agent can reliably produce repairs; It can only establish an accepted patch, not necessarily autonomous agent success.

  - The diagnostic quality is measured reprodcibly
  - The evaluator outcomes are robust across multiple independent tests.

**Conclusions:** 
 - These existing tests are capable of detecting the injected boundary defect, including its effect on the overall result (eg:- discounted total). This would provide some insight into AI repair capability or task-fixtures, and which are the useful metrics to calculate how strong the guardrails are.

 - Functional correctness and scope compliance are independent checks. Just because one passes the functional test, doesn't mean the evaluator won't reject an unauthorized change

 - Baseline diagnostics require careful interpretation. 

 - Fixing one defect isn't enough to establish correctness. Points out the necessity for regression tests to check near and above boundary conditions.

 - Repair and Development require a separate set of benchmarks


#### So what changes when Virtual Sandbox and Agent come into the picture?

These current behaviors help us know the defects, intended boundary behavior, and expected tests in advance. This helps us understand the difference between a valid repair, bad repair and unauthorised repair.

A Sandbx adds a controlled place to test the candidate changes and inspect them before moving to acceptance state. An Agent changes the problem because it must act on evidence as well as discover, rather than simply present a fix/patch.

The flow can be broken down as follows:

[Agent Receives Task, Scope allowed and Context. It might discover and delve into relevant functions, tests, interfaces and dependencies.]
                                   |
                                   v
[Agent uses retrieved evidence to propose a change. To stop wasting time traversing an entire repository, Graph Retrieval can help explore relevant dependencies]
                                   |
                                   v
[The candidate patch is applied to an isolated work-copy/controlled test environment and deterministic checks are run.]                    
                                   |
                                   v
[Diagnostic feedback of the failures, successes, and relevant evidences to analyse if it needs further context or the current run is sufficient.]
                                   |
                                   v
[The evaluator accepts/rejects the patch according to criteria, and records patches, tests, changed paths, diagnostics and output.]

**Limitations:**
 - A scheme limitation worth pointing out to is that the current schema checks only the shape of the tasks, but it doesn't necessarily require task_id's to be unique across tasks array. 
 - It accepts any non-empty base revision string without checking it can identify an actual Git commit. 
 - These gaps are within semantic and structural validation. 