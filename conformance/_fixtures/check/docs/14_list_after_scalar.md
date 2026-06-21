---
artifact_type: plan
authority: derived
generated_by: conformance-fixture
parent_artifacts: ""
convergence: n/a
  - docs/00_all_clean.md
---
# 14 — Scalar-then-list parse

This frontmatter has `parent_artifacts: ""` (scalar empty string) followed by
`  - docs/00_all_clean.md` (list item) with `convergence: n/a` between them.
The engine must parse this without crashing, and parent_artifacts should be
`["docs/00_all_clean.md"]` — a list with the item, not the empty string (G14).
