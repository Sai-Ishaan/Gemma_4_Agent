## Gemma-4 Developer Agent: From 'Vibe Coding' to 'Optimized Engineering'

- The following is our submission for the [Gemma-4 Google Developer Agent Competition] (https://www.kaggle.com/competitions/gemma-4-developer-agent/overview) 

#### <u> Introduction </u>
Current market coding agents rely on internet-connected models, which require a powerful commercial infrastructure. This makes advance Software Development and Engineering out of reach for the general audience. This base encompasses the various methologies and approaches used to fine-tune Gemma-4 to not only help developers navigate and optimise their software development workflow and tasks, but also optimize it on existing market hardware.

#### <u> Goal </u>
Post-train an open source model into a reliable agent for navigating complex coding tasks and codebases, and draft fixes for real software issues, helping in accelerating developer workflow.

#### Initial Approach: Model Distillation/Trajectory Replay Loop:

Instead of traditional RLHF, we can build a **Model Distillation/Trajectory Replay loop**:

- **Teacher Rollouts:** Unconstraining the Base Gemma 4 model, letting it generate multiple varied attempts to fix a dataset of software issues. Tracking its exact CLI Commands, Search Queries, and Patch Generations.

- **Reward Loop:** Applying all the patches in the sandbox. If the patch passes the tests, reward is assigned as +1 and trajectory is saved. If it fails, Reward is assigned as 0 and discarded.

- **Student Distillation (Unsloth LoRA):** Training the LoRA adapters using Unsloth toolkit. The training data is a step-by-step reasoning and chain of thought and retrieval trajectory that shows how the final state (code) is achieved. This is achieved by _teaching_ the model _How_ to navigate, not just how the final diff looks like.

#### Agent Hierarchy Design

Since the goal is to make engineering more structured, moving away from blindly re-writing code snippets (Vibe Coding) can be achieved by making the orchestration enforce a strict chain of thought. Having one massive prompt can be tedious, so we need specialized sub-agents. These can be broken down into the following:

**A) Codebase Mapper (Discovery):**
- **Role:** Finds where the bugs are located

- **Skill Execution:** This agent shouldn't read the whole repository. A custom skill is assigned (such as lightweight regex pipeline or Jaccard Based semantic JSON store) to rapidly index the repo and pull relevant file paths and class structures.

**B) Code Analyzer (Hypothesis Formation):**
- **Role:** Acts as the senior engineer, reading issues and files provided by the Codebase Mapper.

- **Constraint Enforced:** This agent merely makes note, perform RCA and write down a diagnostic markdown report, mentioning which snippets/files require change, and steps to fix them. 

**C) Coder / Patch Executor (Action):**
- **Role:** The coder/dev. It takes the analyzer's hypothesis and outputs a strict unified diff (`.patch` file).

- **Self-Healing Loop:** If the `eval_config.yaml` test fails, the coder agent catches the traceback error, using it to trigger the Mapper to fetch new context, forming a closed loop iterative process that runs until the 12-hour timer nears its limit.

#### Proposed Development LifeCycle

A Four-Phase Development Cycle has been proposed, spanning from setting up local guardrails to LoRA Fine-Tuning:

- **Phase 1 (Local Orchestration and Guardrails Setup):** Deterministic validation scripts for syntaxes, sematics, and training checks are setup in host hardware, returning structured JSON error reports and scalar reward penalties (R ∈ [-1.0, 1.0]). Using a simulated mock agent, it validates the pipeline mechanics.

- **Phase 2 (Synthetic Curriculum Engine):** A testbed is created to auto-generate baseline codebases with zero-price boundary unit test suites (`create_clean_testbed.py`). Synthetic Bugs are then injected using a script via AST `NodeTransformer` mutations (`inject_bugs.py`), with the expectated unit tests to fail. This will automatically generate ground-truth bug-fix pairs (`gemma_training_curriculum.jsonl`) with linked NetworkX dependency graphs.

- **Phase 3 (Trajectory Rollouts and Reward Modeling):** This phase is dedicated to formulate agent prompts from synthetic curriculum items, and execute candidate action rollouts by combining reasoning steps, diagnostic reports, and patch diffs.

- **Phase 4 (Remote LoRA Distillation and Deployment):** Using Unsloth LoRa fine-tuning on gemma-4, and export PEFT adapters and packages for evaluation.




#### Architectural Design
Standard LLM coding agents rely mostly on raw text context windows, which fall prey to the 'memory-wall' effect and diluted attention when handling complex directories. To overcome this, our system introduces a **Multi-Dimensional Graph Architecture** which deconstructs the project semantics into three distinct layers before Context Assembly:

 - **Abstract Syntax Layer (AST):** Extracts structural hierarchies (CallGraphVisitor) across functions and classes, allowing the agent to trace symbol dependencies without thousands of raw code tokens.

 - **DFG (Data Flow Graph) Layer:** Maps variable state changes, parameter pass-throughs and returns dependencies across module boundaries.

 - **Git commit DAG (Directed Acyclic Graph) Layer:** Indexes historical code churn and recent commit deltas to prioritise investigation scopes of modified snippets or blocks in specific regions.

The localised NetworkX subgraph data along with target code snippets are then fed into `gemma-4-31b-it-qat-w4a16-ct`. This ensures the agent reduces context overhead and eliminates scope hallucination.

#### Development Approach and Guardrails
 
 To make the seamless transition from a baseless 'Vibe-Coding' to 'Deterministic Software Development', every propoed agent action should pass through a modular verification suite. The following scripts are built in our pipeline in order to enforce individual engineering boundaries:
  
  - **`syntax_check.py`(For Code Validity):** Parses modified files using `ast.parse()` to catch compilation errors, indentation mis-matches, or bad diffs before test suite execution.

  - **`scope_check.py`(For Containment and Security):** It validates generated patch files against approved symbol scopes in `diagnostic_report.json` to prevent unauthorised file edits or out-of-scope actions.

  - **`pedagogue_check.py`(For Reasoning Trace Integrity):** This verifies the agent's diagnostic report contains structured graph relationships such as `CALLS`, `DEPENDS_ON` etc:- rather than ungrounded claims.

  - **`mock_agent.py` (For Validation Harness):** Acts as a simulator that runs end-to-end completely to verify that all Guardrail scripts return predictable JSON Schema output and scalar penalties.

  - **`create_clean_testbed.py` (Reference Environment):** Generates isolated multi-module Python repos (`clean_repo/`) equipped with interdependent functions and struct unittest/pytest script suites.

  - **`inject_bugs.py` (Synthetic Data Generator):** It simulates change or mutation in clean AST nodes (in the initial example, swapping comparion and arithmetic operators) to automatically produce a bug-fix curriculum pairs alongside NetworkX call graphs.

