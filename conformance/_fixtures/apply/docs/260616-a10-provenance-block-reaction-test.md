---
artifact_type: reaction
authority: derived
generated_by: manual
parent_artifacts:
  - docs/260616-a1-no-fm-reaction-test.md
convergence: n/a
provenance_note: >
  SENTINEL-A10-BLOCKSCALAR this multi-line provenance_note body must survive an _apply
  round-trip verbatim. A frontmatter parser with no YAML block-scalar support reads the
  '>' as the value and re-renders provenance_note as the literal ">", silently destroying
  this justification text. Preserve the block on regeneration.
---
# A10 — multi-line provenance_note '>' block must round-trip

A correct doc whose `provenance_note` is a **multi-line block scalar** — the form op's
real docs use (the single-line quoted form in A9 is not affected). `_apply` must preserve
the body, not collapse it to `">"`. The judge checks the **raw output text** for the
SENTINEL string, because the field-parser cannot represent a block scalar (so a
field-by-field check would silently miss the destruction).
