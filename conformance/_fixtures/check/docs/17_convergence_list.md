---
artifact_type: reaction
authority: derived
generated_by: conformance-fixture
parent_artifacts:
convergence: n/a
  - docs/00_all_clean.md
---
# 17 — Convergence-list poisoning

Frontmatter has `parent_artifacts:` (empty) then `convergence: n/a` then
`  - docs/00_all_clean.md`. The list item attaches to `convergence` (the last
key), setting convergence to `["docs/00_all_clean.md"]` — a list, not a string.
Engine must NOT crash on `conv not in VALID_CONVERGENCE` (TypeError: unhashable
type 'list'). Handle gracefully: convert list to its first element or skip (G17).
