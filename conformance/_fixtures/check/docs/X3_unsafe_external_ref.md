---
artifact_type: plan
authority: derived
generated_by: conformance-fixture
parent_artifacts:
  - axiom-meta-op:../../etc/passwd
---
# X3 — unsafe external-looking ref is rejected, not skipped

A path-traversal ref (`..` in the path) is NOT a valid external ref, so it must not
be silently accepted/skipped; it falls through to local resolution, which fails →
parent-not-found error. Guards against `..`/absolute/URL refs slipping through.
