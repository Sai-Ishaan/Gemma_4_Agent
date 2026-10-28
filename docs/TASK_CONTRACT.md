# Phase 0 task contract

- `P0-01`–`P0-09` preserve the nine categories in the original Phase 0 plan. `P0-10` adds a distinct out-of-scope case; it is not a renumbering.
- Task IDs are stable. A material change to a task's semantics requires a new task ID.
- `tasks.json` contains agent-visible request/context/constraints and public acceptance-check identifiers, but not `expected_behavior`. `evaluator.json` contains evaluator-only expected behavior and acceptance checks. The runner must never expose evaluator metadata in the prompt. File separation reduces accidental leakage but is not a security boundary by itself.
- `fixture:p0-NN-v1` values are named placeholders, not existing Git commits. Replace them with real commit hashes or immutable fixture IDs when reset states exist.
- The manifest describes the intended task set. P0-01 has a local first-pass reset and evaluation workflow; the remaining tasks must be assessed individually before being described as implemented or operational.
- A clarification or rejection task may correctly produce no patch.
- Such tasks must be evaluated on the appropriateness of the response and the absence of unauthorized edits, rather than requiring code tests for a nonexistent patch.
- Evaluation criteria for these tasks must be defined before results are included in benchmark claims.

## Implementation status

- The manifest defines the intended Phase 0 task set. A task definition does not, by itself, establish that its fixture, evaluator, or execution path is implemented or validated.
- **P0-01 has a local first-pass evaluation workflow.** Its implementation includes a recorded faulty revision, a reset script, a patch-evaluation script, baseline-signature checks, candidate test execution, changed-path and protected-path checks, and JSON run records.
- P0-01 has been exercised with selected successful and rejected patch cases. The recorded runs demonstrate particular evaluator paths, not general agent effectiveness or complete benchmark validation.
- The remaining task definitions must be tracked separately from implemented and exercised tasks. Do not describe P0-02–P0-10 as operational unless their fixtures, checks, and execution paths have been verified.
- Hidden-test evaluation and secure isolation of candidate code execution are not provided by the current P0-01 workflow.
- The P0-01 evaluator is a local first-pass evaluator. Its acceptance decision is based on the configured baseline checks, available test suite, and scope rules; acceptance does not prove correctness for all possible inputs.

## Fixture and revision requirements

- A task's `base_revision` must identify the intended starting state for that task. Where a real Git revision is required, use a full commit hash and verify that the commit exists.
- Any named fixture placeholder, such as `fixture:p0-NN-v1`, is an identifier rather than a Git commit. Do not treat it as an executable reset target.
- Record which tasks use verified Git revisions and which still require fixture materialization.
- For P0-01, the reset script reads the task's `base_revision`, checks the commit format and existence, verifies the evaluation worktree, refuses to reset a dirty worktree, and checks the final revision and cleanliness after reset.
- These safeguards reduce accidental worktree damage; they do not provide a secure sandbox for arbitrary code execution.

## P0-01 evaluation contract

The P0-01 evaluator performs the following checks:

1. Resolve the candidate patch and require it to be stored outside the main repository.
2. Verify that the targeted faulty baseline has the expected test-failure signature.
3. Verify that the full-suite faulty baseline has the expected test-failure signature.
4. Check that the candidate patch applies before applying it.
5. Record the changed paths and check task-specific scope and protected-path constraints.
6. Run the candidate test suite, including when the patch violates scope, so that test results remain available for diagnosis.
7. Accept the candidate only when the configured baseline conditions, candidate test condition, and scope conditions are satisfied.
8. Write a structured JSON run record containing the outcome and available diagnostics.

For the current P0-01 configuration, the expected targeted baseline signature is two failures and five passes; the expected full-suite faulty-baseline signature is three failures and thirteen passes. These are configuration-specific signatures, not universal benchmark criteria.

The current acceptance decision is a first-pass gate. It should not be interpreted as proof of semantic correctness beyond the available tests and configured scope checks.

## Clean base behavior
- Discount: 0% below 100; 5% from 100 to below 500; 10% at 500+.
- Pricing: rejects negative unit prices and quantities and delegates to discount calculation.
- Inventory: subtracts reservations, clamps sellable quantity at zero, and rejects negative values.
- Currency: formatting requires a three-letter alphabetic code and formats to two decimals.

## Clarification and out-of-scope tasks
- A clarification or reject task may correctly produce no patch.

- Such tasks must be evaluated on the appropriateness of the response and the absence of unauthorised edits, rather than requiring code rests for a non-existent patch

- Evaluation criteria for these tasks must be defines before results are included in benchmark claims

## Reporting and limitations

- Preserve run records, task revisions, candidate patches, test outcomes, changed paths, acceptance decisions, and relevant error messages so evaluation decisions can be audited.
- Distinguish **specified**, **implemented**, **exercised**, and **validated** states in project documentation.
- A recorded successful run demonstrates that a particular case passed the configured checks; it does not establish repeatability, broad task coverage, or comparative effectiveness.
- Diagnostic fields in a run record are evidence of recorded information, not automatically a diagnostic-quality score.
- Claims about improvements in repair quality, resource use, diagnostic quality, robustness, or generalization require separate, reproducible experiments.