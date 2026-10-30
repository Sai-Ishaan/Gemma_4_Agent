
### Phase 1 — Model-Connected Repair and Guardrail Validation

**Experiment:** Local repair of a control-flow inversion defect in `calculate_discount` using Llama 3.2:3b and the Phase 1 validation middleware.

**Observed execution:**

- The model invoked the repair tool on Turns 1 and 3.
- Turn 1 produced syntactically valid, in-scope code but failed three of six behavioral tests. The candidate was rejected.
- Turn 2 returned a proposed repair as ordinary text rather than an actual tool invocation. No patch was executed.
- Turn 3 produced a candidate that passed syntax, scope, and all six configured behavioral tests.
- The final candidate was promoted by the repair environment with a combined reward penalty of 0.0.

**Observed validation results:**

| Metric | Result |
|---|---:|
| Syntax validation | Pass |
| Scope validation | Pass |
| Behavioral tests | 6/6 passed |
| Final reward penalty | 0.0 |
| Final candidate promotion | Accepted |

**Interpretation:**

The run demonstrates that the middleware can reject a syntactically valid but behaviorally incorrect candidate and accept a later candidate that satisfies the configured validation checks. It also demonstrates an actual model-connected tool invocation and the use of validation feedback across repair attempts.

**Limitations:**

This is one successful repair trajectory using a small, predefined test suite. It does not establish general repair reliability, comprehensive scope enforcement, or secure sandbox isolation. The zero-price input remains untested, and candidate promotion persistence requires separate verification.

**Status:** Successful controlled repair observed; broader validation pending.
