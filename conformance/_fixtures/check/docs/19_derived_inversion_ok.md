---
artifact_type: plan
authority: derived
generated_by: conformance-fixture
parent_artifacts:
  - docs/_speculative_parent.md
  - docs/_study_parent.md
---
# 19 — Type-aware inversion: derived child on a speculative parent is OK

A `plan` (derived) cites a speculative brainstorm parent, with NO provenance_note. Under
the type-aware inversion gate, a derived type legitimately inherits a speculative floor
(a plan/reaction ABOUT speculation is itself speculative-grounded) → it must NOT warn.

Contrast G7 (`07_inversion_unack.md`): a *structured* child on the same speculative
parent DOES warn — only a top-tier `structured` type on a lower-authority parent is a
real mislabel. This fixture is the regression-lock for that distinction.
