# Gemma 4 Fine Tune Phase 0 mock repository

This is the initial clean target repository for Phase 0. It defines base behavior and task contracts; it does not yet implement task resets, patch application, evaluator execution, or benchmark runs.

Run baseline tests: `python -m pytest`

`fixtures/tasks.json` is the agent-visible task manifest. `fixtures/evaluator.json` contains evaluator-only expected behavior and must never be included in model prompts. The runner must enforce this separation.

Stable IDs: P0-01 through P0-09 preserve the original plan. P0-10 explicitly covers out-of-scope requests because that behavior was a metric but not a distinct case. IDs must not be renumbered.
