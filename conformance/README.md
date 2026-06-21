# warrant conformance suite

Pre-registered black-box test suites for the warrant reference engine.
Two suites: checker (`test_check.py`) and frontmatter generator (`test_apply.py`).

```
python3 conformance/test_check.py --engine reference/_check_frontmatter.py
python3 conformance/test_apply.py --engine reference/_apply_frontmatter.py
```

## Results

| Suite | Checks | Result |
|-------|--------|--------|
| test_check.py | 26 (G1-G20, R1-R2, D1-D4) | 26/26 PASS, GATE PASS |
| test_apply.py | 10 (A1-A10) | 10/10 PASS, GATE PASS |

## Architecture

```
conformance/
  test_check.py           # checker suite: sandbox → engine → parse → judge
  test_apply.py           # apply suite: sandbox → apply → inspect frontmatter
  _fixtures/
    check/                # synthetic corpus for checker (26 fixture docs)
      policy.json         artifact_types.json   methodology_state.json
      sync_ledger.json    docs/                  extra_root/
    apply/                # synthetic corpus for apply (10 fixture docs)
      policy.json         methodology_state.json
      docs/               extra_root/
  _expected/
    check.json            # per-check-id expected results for checker
    apply.json            # per-doc expected frontmatter properties for apply
  _verdict_check.json           # checker output (gitignored)
  _verdict_apply.json     # apply output (gitignored)
  README.md
```

## Checker (26 checks, 4 layers)

| Layer | IDs | Description |
|-------|-----|-------------|
| G — Generic | G1-G20 | Frontmatter, fields, type→authority, parents, type-aware inversion gate (narrowed: only `structured←speculative` warns), findings bar, physical grounding, convergence, parser resilience, inline arrays, multi-candidate paths |
| R — Registry | R1-R2 | Policy keys ⊆ artifact_types, registry-absent skip |
| D — Domain hooks | D1-D4 | Unqualified leaf ref, sync coverage, extra_roots, skip honored |

## Apply (10 checks)

| ID | Check |
|----|-------|
| A1 | No frontmatter → stamped |
| A2 | Missing field → regenerated |
| A3 | Correct → untouched (idempotent) |
| A4 | Wrong type/authority → corrected |
| A5 | Exercise step → chain parents |
| A6 | Extra root → scanned |
| A7 | Pattern classification → correct type |
| A8 | Authority from policy.json |
| A9 | Hand-filled parents + provenance_note → preserved, not overwritten |
| A10 | Multi-line `provenance_note: >` block → survives round-trip, not collapsed to `">"` |

## Fairness

- Synthetic fixtures — zero real repo data
- Black box — measures stdout/exit-code/file-effects
- Pre-registered — `_expected/*.json` committed before cross-team scoring
- Per check-id matching — verifies behavior, not message wording
