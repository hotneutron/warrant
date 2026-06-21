---
artifact_type: exercise_step
authority: structured
generated_by: conformance-fixture
parent_artifacts:
  - docs/_derived_parent.md
---
# 20 — Narrowed gate: structured child on a DERIVED parent is OK

An `exercise_step` (structured) cites a `derived` plan parent, with NO provenance_note.
The narrowed inversion gate warns only on `structured ← speculative` (laundering
speculation as structured), NOT `structured ← derived` — a structured doc building on a
derived conclusion is the intended pattern. So this must NOT warn.

This is the regression-lock distinguishing the narrowed gate from the prior
`parent_rank < self_rank` form (which would have warned here). Contrast G7
(`structured ← speculative` → WARN) and G19 (`derived ← speculative` → OK).

(An `exercise_step`, not a `findings`, deliberately — so the findings-contract check,
which independently requires a structured-authority parent, does not fire and confound
the inversion behavior under test.)
