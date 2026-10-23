# Phase 0 task contract

- `P0-01`–`P0-09` preserve the nine categories in the original Phase 0 plan. `P0-10` adds a distinct out-of-scope case; it is not a renumbering.
- IDs are stable. Materially changed task semantics require a new ID.
- `tasks.json` contains agent-visible request/context/constraints and public acceptance-check identifiers, but not `expected_behavior`. `evaluator.json` contains evaluator-only expected behavior and acceptance checks. The runner must never expose evaluator metadata in the prompt. File separation reduces accidental leakage but is not a security boundary by itself.
- `fixture:p0-NN-v1` values are named placeholders, not existing Git commits. Replace them with real commit hashes or immutable fixture IDs when reset states exist.
- The manifest describes intended tasks; task-specific buggy revisions, hidden tests, reset orchestration, patch evaluation, and run logging are not implemented yet.
- Clarification/rejection tasks may correctly produce no patch; evaluate their response and absence of unauthorized edits instead of requiring code tests on a nonexistent patch.

## Clean base behavior
- Discount: 0% below 100; 5% from 100 to below 500; 10% at 500+.
- Pricing rejects negative unit prices and quantities and delegates to discount calculation.
- Inventory subtracts reservations, clamps sellable quantity at zero, and rejects negative values.
- Currency formatting requires a three-letter alphabetic code and formats to two decimals.
