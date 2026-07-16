---
artifact_type: findings
authority: structured
generated_by: conformance-fixture
parent_artifacts:
  - axiom-meta-team-b:docs/260713-1156-proposal-dismissal-artifact-and-revisit-contract.md
---
# X2 — external parent confers NO structured authority (the firewall)

A findings doc whose ONLY parent is external, with NO provenance_note. The external
ref is accepted (not dereferenced) but must NOT set has_structured_parent, so the
findings bar (structured parent OR provenance_note) MUST still fire. This is the
cross-repo authority firewall: you cannot launder structured authority through a
foreign parent.
