---
artifact_type: plan
authority: derived
generated_by: conformance-fixture
provenance_note: "conformance fixture — study-gate escape hatch (this check targets another rule)"
parent_artifacts: ["docs/00_all_clean.md"]
---
# 16 — Inline-array parent_artifacts

Uses inline YAML/JSON array syntax `parent_artifacts: ["docs/00_all_clean.md"]`.
Engine must parse this as a list with one item, not as a string of characters (G16).
