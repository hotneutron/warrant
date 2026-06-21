---
artifact_type: plan
authority: derived
generated_by: conformance-fixture
parent_artifacts:
  - 00_all_clean.md
---
# 18 — Multi-candidate parent path resolution

Parent `00_all_clean.md` is a bare filename (no `docs/` prefix). Engine must resolve
it relative to the doc's own directory first (`docs/00_all_clean.md` → exists), then
relative to REPO root. G18: PASS when parent path found via directory-relative fallback.
