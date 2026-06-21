# warrant — reference engine

The shared default checker. Domain-agnostic: the
union of the participating teams' checks, with everything domain-specific driven by the team
`policy.json`'s `config` block. Each optional check runs only if its source is configured
**and** present; otherwise it is silently skipped.

Each team's `policy.json` lives in **its own (consumer) repo**, not here — e.g. a team runs
`reference/_check_frontmatter.py --policy /path/to/its/warrant_policy.json` from
its own repo. The engine is shared; the policy is per-team.

```bash
python3 _check_frontmatter.py --policy /path/to/consumer/warrant_policy.json   # a team's policy
python3 _check_frontmatter.py                                                  # default: ./policy.json (neutral)
```

## Checks

**Generic (always):** frontmatter present + parseable · required fields · artifact_type
known · authority matches `type→authority` (policy) · parent paths exist · authority
inversion (warn, `provenance_note` escape) · findings bar (structured parent /
`provenance_note`) · findings physical-grounding soft-check · `convergence` field on
reaction/cross_check.

**Registry validation:** every `type_authority` key must be in the
`artifact_types` registry (`../artifact_types/artifact_types.json`) — drift is an error.
Skipped if the registry submodule isn't present.

**Domain hooks (config-driven, optional):** unqualified-leaf-ref detection (needs
`leaf_source`, e.g. `methodology_state.json`) · sync-coverage + ambient status line (needs
`ledger_path`) · `extra_roots` / `skip` / `partner_markers` / `partner_name`.

## Config keys (`policy.json` → `config`)

`docs_dir` · `extra_roots` · `skip` · `partner_markers` · `partner_name` · `leaf_source` ·
`ledger_path` · `registry`. Root is discovered by walking up to `methodology_state.json`
(else git toplevel), so the engine works at any nesting depth.

A team adopts the reference by pointing its hook at this engine with `--policy
<team>/policy.json`; it keeps its own `<team>/` only if it diverges.
