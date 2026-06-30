# warrant

> **No rant without a warrant.**

Frontmatter **authority validation** for the parallax ecosystem. Every `docs/*.md`
declares an `authority` tier (`structured` / `derived` / `speculative`) and its
`parent_artifacts`; **warrant** checks that the declared authority is *warranted* by
that provenance. The machine-readable form of "specificity ≠ correctness."

Governed like **parallax**: a shared **reference** engine is the default, a
**conformance** suite verifies any implementation, and the independence that matters
lives in **policy** (the per-team `type → authority` map).

## Structure

| Path | What |
|---|---|
| `reference/` | the shared reference engine — checker + apply, domain-noun-free |
| `conformance/` | verifies any implementation by measurement (synthetic fixtures + golden-diff) |
| `artifact_types/` | **submodule** → the shared type-vocabulary registry |

Each consuming team runs the reference engine with its own `policy.json` kept in
the consumer repo. Per-team implementations are retired in favor of this shared engine.

## The three repos

| repo | governs | per-consumer config |
|---|---|---|
| **[artifact_types](https://github.com/hotneutron/artifact_types)** | the canonical type **vocabulary** | — (shared) |
| **[parallax](https://github.com/hotneutron/parallax)** | the cross-team **exchange** (sync, independence enforcement) | `tiers.json` |
| **warrant** (this) | each repo's internal **doc authority** | `policy.json` (type → authority) |

**Together.** A team's repo submodules **warrant** (to validate its own `docs/`) and
**parallax** (to run the cross-team exchange); both draw their type vocabulary from
**artifact_types**. warrant governs authority *within* a repo; parallax governs what
crosses *between* teams.

**Independently.** warrant validates any repo's frontmatter from a `policy.json` alone.
parallax needs only a sync home. artifact_types is a static JSON + schema.

## Amendment process

The `reference/` engine and the `artifact_types` vocabulary are interface artifacts:
proposal → independent review → bilateral agreement → version bump.
