#!/usr/bin/env python3
"""
warrant — reference engine (the shared default).

Domain-agnostic frontmatter authority validator: it checks that each doc's declared
`authority` is *warranted* by its provenance ("no rant without a warrant"). The union of
the participating teams' checks. Everything domain-specific is CONFIG (from the team `policy.json`):
the type→authority map, extra doc roots, the leaf-ref source, the sync ledger, partner
markers. Each optional check runs only if its data source is configured AND present —
otherwise it is silently skipped, so the engine is domain-noun-free.

Run:  python3 _check_frontmatter.py [--policy PATH]   (default: ./policy.json, this dir)

policy.json = { "type_authority": {type: authority}, "config": {
    "docs_dir": "docs", "extra_roots": [...], "skip": [...],
    "partner_markers": [...], "partner_name": "...",
    "leaf_source": "methodology_state.json", "ledger_path": "...",
    "registry": "../artifact_types/artifact_types.json" } }
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
REQUIRED = ["artifact_type", "authority", "generated_by", "parent_artifacts"]
VALID_CONVERGENCE = {"independent", "propagated", "modal", "n/a"}
AUTHORITY_RANK = {"structured": 3, "derived": 2, "speculative": 1}
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
# unit-bearing quantity detector (findings physical-grounding soft-check) — physical
# units only; surrogate units (evals, seeds) deliberately don't count.
PHYS_UNIT_RE = re.compile(
    r"\$\s?\d"
    r"|\d[\d,.]*\s?(?:"
    r"[kmµ]?W\b|mm²|mm\^?2\b|cm²|cm\^?2\b"
    r"|[GMT]B(?:/s|ps)?\b|[GMT]bps\b"
    r"|pJ(?:/bit)?\b|[nµm]s\b|[GM]Hz\b"
    r"|tok(?:ens)?/s|defects?/cm|/wafer\b|/die\b|°C|USD\b"
    r")")

# Neutral reference defaults — a team's policy.json overrides these (namespace-relative).
_DEFAULT_TYPE_AUTHORITY = {
    "findings": "structured", "exercise_step": "structured", "methodology": "structured",
    "plan": "derived", "proposal": "derived", "reflection": "derived", "study": "derived",
    "reaction": "derived", "cross_check": "derived",
    "brainstorm": "speculative", "strategy": "speculative",
    "schema_plan": "speculative", "domain_extension": "speculative",
}


def _repo_root():
    """Discover the CONSUMING repo's root: walk up to methodology_state.json, else the
    git toplevel, else the engine's grandparent. Path-agnostic (any nesting depth)."""
    d = Path(__file__).resolve().parent
    while d != d.parent:
        if (d / "methodology_state.json").exists():
            return d
        d = d.parent
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, cwd=str(ENGINE_DIR), timeout=5)
        if top.returncode == 0 and top.stdout.strip():
            return Path(top.stdout.strip())
    except Exception:
        pass
    return Path(__file__).resolve().parents[1]


REPO = _repo_root()


def load_policy(path):
    if not Path(path).exists():
        return dict(_DEFAULT_TYPE_AUTHORITY), {}
    d = json.load(open(path))
    return d.get("type_authority", _DEFAULT_TYPE_AUTHORITY), d.get("config", {})


def parse_frontmatter(text):
    """Minimal YAML-subset parser for the fields we emit (no external deps)."""
    m = FM_RE.match(text)
    if not m:
        return None
    meta, key = {}, None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        if line.startswith("  - "):
            # a list item overrides a prior SCALAR for this key (e.g. `key: ""` then
            # `  - x` → ["x"], not a crash on str.append) — G14.
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(line[4:].strip())
        elif ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val.startswith("[") and val.endswith("]"):
                # inline array: [], [a, b], ["a", "b"] — parse as a list, not a string
                # the engine would iterate char-by-char (G16).
                inner = val[1:-1].strip()
                meta[key] = [x.strip().strip('"').strip("'") for x in inner.split(",")] if inner else []
            elif val.startswith('"') and val.endswith('"'):
                meta[key] = val[1:-1]
            elif val == "":
                meta[key] = []
            else:
                meta[key] = val
    return meta


def _as_list(v):
    """Normalize a frontmatter field to a list — inverse-provenance edges accept a scalar
    OR a list (a doc can be retired by ≥1 docs). Scalar parses as a single-element list."""
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _is_external_artifact_ref(ref):
    """Return true for repo-qualified external artifact refs: <repo>:<path-in-repo>.

    External parent artifacts are committed artifacts in another repo. The warrant
    checker accepts their syntax but does not dereference them; partner reads stay
    governed by Parallax.
    """
    if not isinstance(ref, str):
        return False
    repo, sep, rel = ref.partition(":")
    if not sep:
        return False
    if "://" in ref or not repo or not rel:
        return False
    if rel.startswith("/") or ".." in Path(rel).parts:
        return False
    return re.fullmatch(r"[A-Za-z0-9_.-]+", repo) is not None


def sync_status_line(ledger_full, partner_name):
    data = json.loads(ledger_full.read_text())
    entries = data.get("entries", [])
    if not entries:
        return f"cross-team sync ledger: NO ENTRIES (create one when reacting to {partner_name})"
    last = entries[-1]
    line = f"synced {last['date']} with {partner_name} (their HEAD {last['their_head']}"
    repo = data.get("repo")
    if repo:
        try:
            n = subprocess.run(["git", "-C", str((REPO / repo).resolve()), "rev-list",
                                "--count", f"{last['their_head']}..HEAD"],
                               capture_output=True, text=True, timeout=5)
            if n.returncode == 0:
                line += f", {n.stdout.strip()} commits behind"
        except Exception:
            pass
    return line + ")"


def main():
    policy_path = ENGINE_DIR / "policy.json"
    if "--policy" in sys.argv:
        policy_path = Path(sys.argv[sys.argv.index("--policy") + 1])
    TYPE_AUTHORITY, cfg = load_policy(policy_path)

    docs_dir = cfg.get("docs_dir", "docs")
    extra_roots = [REPO / r for r in cfg.get("extra_roots", [])]
    skip = set(cfg.get("skip", []))
    partner_markers = tuple(cfg.get("partner_markers", []))
    partner_name = cfg.get("partner_name", "the partner")
    leaf_source = cfg.get("leaf_source")
    ledger_path = cfg.get("ledger_path")
    registry = cfg.get("registry") or "../artifact_types/artifact_types.json"

    errors, warnings, checked = [], [], 0
    retire_edges = {}   # rel -> [retirer rels] for the refuted_by/superseded_by graph (cycle check)

    # ---- registry validation: policy type keys must be in the artifact_types
    # registry — drift is an error, not silent. Skipped if the registry isn't present.
    reg_path = (ENGINE_DIR / registry) if not os.path.isabs(registry) else Path(registry)
    if reg_path.exists():
        reg_types = set(json.load(open(reg_path)).get("types", {}))
        for t in sorted(TYPE_AUTHORITY):
            if t not in reg_types:
                errors.append(f"policy: artifact_type '{t}' not in the artifact_types "
                              f"registry — drift (add it there or remove it from policy)")

    # ---- optional domain source: schema leaves for unqualified-leaf-ref detection
    groups, schema_leaves = set(), set()
    if leaf_source and (REPO / leaf_source).exists():
        state = json.loads((REPO / leaf_source).read_text())
        for g, gd in state.get("dimensions", {}).items():
            groups.add(g)
            for l in gd.get("leaves", {}):
                schema_leaves.add(f"{g}/{l}")
    leaf_ref_re = re.compile(r"(?<![\w:.])(" + "|".join(sorted(groups)) + r")/([a-z][a-z0-9_]+)\b") \
        if groups else None

    # ---- optional domain source: the sync ledger (coverage + ambient status line)
    ledger_full = (REPO / ledger_path) if ledger_path else None
    syncs = []
    if ledger_full and ledger_full.exists():
        syncs = json.loads(ledger_full.read_text()).get("entries", [])
    last_sync_date = max((e["date"].replace("-", "")[2:] for e in syncs), default=None)

    all_paths = list((REPO / docs_dir).rglob("*.md"))
    for root in extra_roots:
        all_paths += list(root.rglob("*.md"))
    for path in sorted(all_paths):
        rel = path.relative_to(REPO).as_posix()
        if rel in skip:
            continue
        checked += 1
        text = path.read_text()
        meta = parse_frontmatter(text)
        if meta is None:
            errors.append(f"{rel}: no frontmatter block")
            continue

        if meta.get("artifact_type") in ("reaction", "cross_check"):
            # convergence may be poisoned into a list by a stray `- item` line (G17);
            # guard the set membership against an unhashable value.
            conv = meta.get("convergence")
            if not isinstance(conv, str) or conv not in VALID_CONVERGENCE:
                warnings.append(f"{rel}: reaction/cross_check doc missing or invalid "
                                f"'convergence:' field (independent | propagated | modal | n/a)")
            if leaf_ref_re:
                for m in leaf_ref_re.finditer(text):
                    ref = f"{m.group(1)}/{m.group(2)}"
                    if ref not in schema_leaves:
                        warnings.append(f"{rel}: unqualified leaf ref '{ref}' — not in our "
                                        f"schema; if it is the partner's, qualify as {partner_name}:{ref}")
            if partner_markers and any(mk in text for mk in partner_markers):
                doc_date = re.match(r"(\d{6})-", path.name)
                if doc_date and (last_sync_date is None or last_sync_date < doc_date.group(1)):
                    warnings.append(f"{rel}: references the partner repo but the sync ledger "
                                    f"has no entry on/after {doc_date.group(1)} — record what you saw")

        for field in REQUIRED:
            if field not in meta:
                errors.append(f"{rel}: missing required field '{field}'")

        atype = meta.get("artifact_type")
        if atype not in TYPE_AUTHORITY:
            errors.append(f"{rel}: unknown artifact_type '{atype}'")
            continue

        expected_auth = TYPE_AUTHORITY[atype]
        if meta.get("authority") != expected_auth:
            errors.append(f"{rel}: authority '{meta.get('authority')}' does not match "
                          f"artifact_type '{atype}' (expected '{expected_auth}')")

        has_structured_parent = False
        has_study_parent = False
        for parent in meta.get("parent_artifacts", []):
            if _is_external_artifact_ref(parent):
                continue
            # multi-candidate resolution (G18): the doc's own directory first (a bare
            # filename resolves as a sibling), then REPO root (a repo-relative path).
            ppath = next((c for c in (path.parent / parent, REPO / parent) if c.exists()), None)
            if ppath is None:
                errors.append(f"{rel}: parent_artifacts path does not exist: {parent}")
                continue
            if ppath.is_dir():
                continue
            pmeta = parse_frontmatter(ppath.read_text())
            if not pmeta:
                continue
            # Rule 2 — no authority propagation from retired docs: a parent that is itself
            # refuted/superseded is retired knowledge; building on it warns (provenance_note escape,
            # which the refuter's own doc carries — so a diagnosis citing what it refutes is exempt).
            if (pmeta.get("refuted_by") or pmeta.get("superseded_by")) and not meta.get("provenance_note"):
                warnings.append(f"{rel}: builds on retired knowledge — parent '{parent}' is "
                                f"refuted/superseded; cite a current doc or add a provenance_note")
            if pmeta.get("authority") == "structured":
                has_structured_parent = True
            if pmeta.get("artifact_type") in {"study", "competitive_baseline", "reflection"}:
                has_study_parent = True
            # Inversion = laundering speculation as structured. The constitutional rule is
            # literally "don't quote speculation as if it were structured", so the check is
            # exactly that pair: only a TOP-TIER `structured` type (findings/exercise_step)
            # citing a `speculative` parent, with no provenance_note. `structured←derived`
            # is NOT an inversion — a finding building on a `derived` conclusion is the
            # intended pattern, and a finding lacking *evidence* is the findings-contract
            # check's job below, not this one (see the narrowing note below).
            if expected_auth == "structured" and pmeta.get("authority") == "speculative" \
                    and not meta.get("provenance_note"):
                warnings.append(f"{rel}: authority inversion — structured doc cites "
                                f"speculative parent '{parent}'; add a provenance_note "
                                f"to acknowledge")

        if atype == "findings" and not has_structured_parent and not meta.get("provenance_note"):
            warnings.append(f"{rel}: findings doc has no structured-authority parent and no "
                            f"provenance_note — a findings doc must derive from evidence (a "
                            f"measurement / exercise / prior findings) or justify its structured "
                            f"authority in a provenance_note (findings contract, CLAUDE.md)")

        if atype == "findings":
            doc_date = re.match(r"(\d{6})-", path.name)
            if doc_date and doc_date.group(1) >= "260612":
                n_units = len(PHYS_UNIT_RE.findall(text))
                if n_units < 3:
                    warnings.append(f"{rel}: findings doc carries only {n_units} unit-bearing "
                                    f"quantities — illustrate the results with concrete physical "
                                    f"examples in domain units (W, mm², $, GB/s, ...) "
                                    f"(findings contract item 4, CLAUDE.md)")

        if atype == "plan" and not has_study_parent \
                and not meta.get("provenance_note"):
            warnings.append(f"{rel}: plan lacks pre-implementation study of existing "
                            f"art — no study/competitive_baseline/reflection in parent_artifacts; "
                            f"add one or a provenance_note to acknowledge (study-gate, RULES.md)")

        # ---- inverse-provenance edges: refuted_by / superseded_by (the negative-knowledge marker).
        # A retired doc is excluded from authority propagation (Rule 2, above) and must link the doc
        # that retires it. Edges accept a scalar or a list (H1).
        retirers = _as_list(meta.get("refuted_by")) + _as_list(meta.get("superseded_by"))
        if retirers:
            my_rank = AUTHORITY_RANK.get(meta.get("authority"), 0)
            for target in retirers:
                tpath = next((c for c in (path.parent / target, REPO / target) if c.exists()), None)
                if tpath is None:
                    errors.append(f"{rel}: refuted_by/superseded_by points to a missing doc: {target}")
                    continue
                retire_edges.setdefault(rel, []).append(tpath.relative_to(REPO).as_posix())
                if not tpath.is_file():
                    continue
                ttext = tpath.read_text()
                tmeta = parse_frontmatter(ttext) or {}
                # H2 — the retirer must be at least as authoritative as the doc it retires
                # (a weaker doc refuting a stronger one is a reverse inversion).
                if AUTHORITY_RANK.get(tmeta.get("authority"), 0) < my_rank and not meta.get("provenance_note"):
                    warnings.append(f"{rel}: retired by lower-authority doc '{target}' "
                                    f"({tmeta.get('authority')} < {meta.get('authority')}) — a weaker "
                                    f"doc retiring a stronger one; add a provenance_note to acknowledge")
                # H3 — the retirer should reference the retired doc (provenance or body); soft.
                if path.name not in ttext:
                    warnings.append(f"{rel}: retired by '{target}', but '{target}' does not reference "
                                    f"this doc (unlinked retirement edge)")

    # ---- retirement-graph cycles (A retires B retires A) → error; refutation must be acyclic.
    _seen, _stack, _cycle_node = set(), set(), None

    def _has_cycle(u):
        _seen.add(u)
        _stack.add(u)
        for v in retire_edges.get(u, []):
            if v in _stack or (v not in _seen and _has_cycle(v)):
                return True
        _stack.discard(u)
        return False

    for n in list(retire_edges):
        if n not in _seen and _has_cycle(n):
            _cycle_node = n
            break
    if _cycle_node:
        errors.append(f"{_cycle_node}: retirement-edge cycle — a doc refutes/supersedes one that "
                      f"(transitively) retires it back; refutation must be acyclic")

    print(f"Checked {checked} docs.")
    if ledger_full and ledger_full.exists():
        print(sync_status_line(ledger_full, partner_name))
    if warnings:
        print(f"\n{len(warnings)} WARNING(s):")
        for w in warnings:
            print(f"  ⚠ {w}")
    if errors:
        print(f"\n{len(errors)} ERROR(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("\nAll frontmatter valid. ✓")


if __name__ == "__main__":
    main()
