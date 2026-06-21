#!/usr/bin/env python3
"""
warrant — reference _apply_frontmatter (idempotent frontmatter generator).

Stamps or regenerates frontmatter for every doc based on filename pattern
classification and step-chain conventions. Reads type→authority from policy.json
(same --policy flag as the checker). Re-runnable and idempotent: existing correct
frontmatter is preserved; missing or malformed frontmatter is regenerated.

Run:  python3 _apply_frontmatter.py [--policy PATH]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

_DEFAULT_TYPE_AUTHORITY = {
    "findings": "structured", "exercise_step": "structured", "methodology": "structured",
    "plan": "derived", "proposal": "derived", "reflection": "derived",
    "reaction": "derived", "cross_check": "derived",
    "brainstorm": "speculative", "strategy": "speculative",
    "schema_plan": "speculative", "domain_extension": "speculative",
}

STEP_CHAIN = {
    "step-01-dimensionalization.md": [],
    "step-1-dimensionalization.md": [],
    "step-02-anchor-A-h100-baseline.md": ["step-01-dimensionalization.md"],
    "step-03a-anchor-B-groq-baseline.md": ["step-01-dimensionalization.md"],
    "step-03b-anchor-C-asic-baseline.md": ["step-01-dimensionalization.md"],
    "step-02-03-scenarios-ground-truth.md": ["step-01-dimensionalization.md"],
    "step-2-scenarios.md": ["step-1-dimensionalization.md"],
    "step-2-3-scenarios-ground-truth.md": ["step-1-dimensionalization.md"],
    "step-3-ground-truth.md": ["step-2-scenarios.md", "step-2-3-scenarios-ground-truth.md"],
    "step-04-meta-observe.md": ["step-03b-anchor-C-asic-baseline.md", "step-02-03-scenarios-ground-truth.md"],
    "step-4-cell-A-S1.md": ["step-3-ground-truth.md"],
    "step-4-cell-A-S2.md": ["step-3-ground-truth.md"],
    "step-4-cells-anchorA.md": ["step-3-ground-truth.md"],
    "step-5-cell-B-S1.md": ["step-3-ground-truth.md"],
    "step-5-cell-B-S2.md": ["step-3-ground-truth.md"],
    "step-5-cell-C-S1.md": ["step-3-ground-truth.md"],
    "step-5-cell-C-S2.md": ["step-3-ground-truth.md"],
    "step-5-cells-anchorBC.md": ["step-4-cells-anchorA.md"],
    "step-05-meta-diagnose.md": ["step-04-meta-observe.md"],
    "step-6-meta-observe.md": ["step-4-cells-anchorA.md", "step-5-cells-anchorBC.md"],
    "step-06-08-analytics.md": ["step-05-meta-diagnose.md"],
    "step-7-meta-diagnose.md": ["step-6-meta-observe.md", "step-3-ground-truth.md"],
    "step-8-meta-prioritize.md": ["step-7-meta-diagnose.md"],
    "step-09-reflection.md": ["step-06-08-analytics.md", "step-8-meta-prioritize.md"],
    "step-9-reflection.md": ["step-8-meta-prioritize.md", "step-2-3-scenarios-ground-truth.md"],
    "step-v2-1-dimensionalization.md": [],
    "step-v2-2-ground-truth.md": ["step-v2-1-dimensionalization.md"],
    "step-v2-2-9-meta-analysis.md": ["step-v2-1-dimensionalization.md"],
    "step-v2-3-meta-analysis.md": ["step-v2-2-ground-truth.md"],
    "step-v2-4-cells-anchorA.md": ["step-v2-2-ground-truth.md"],
    "step-v2-5-cells-anchorBC.md": ["step-v2-4-cells-anchorA.md"],
    "step-v2-6-meta-observe.md": ["step-v2-4-cells-anchorA.md", "step-v2-5-cells-anchorBC.md"],
    "step-v2-7-meta-diagnose.md": ["step-v2-6-meta-observe.md", "step-v2-2-ground-truth.md"],
    "step-v2-8-meta-prioritize.md": ["step-v2-7-meta-diagnose.md"],
    "step-v2-9-reflection.md": ["step-v2-3-meta-analysis.md", "step-v2-8-meta-prioritize.md"],
}

STEP_GENERATED_BY = {
    "step-01-dimensionalization.md": "manual",
    "step-1-dimensionalization.md": "manual",
    "step-02-anchor-A-h100-baseline.md": "/competitive-baseline",
    "step-03a-anchor-B-groq-baseline.md": "/competitive-baseline",
    "step-03b-anchor-C-asic-baseline.md": "/competitive-baseline",
    "step-2-scenarios.md": "manual",
    "step-2-3-scenarios-ground-truth.md": "manual",
    "step-3-ground-truth.md": "manual",
    "step-4-cell-A-S1.md": "/competitive-baseline",
    "step-4-cell-A-S2.md": "/competitive-baseline",
    "step-4-cells-anchorA.md": "/competitive-baseline",
    "step-5-cell-B-S1.md": "/competitive-baseline",
    "step-5-cell-B-S2.md": "/competitive-baseline",
    "step-5-cell-C-S1.md": "/competitive-baseline",
    "step-5-cell-C-S2.md": "/competitive-baseline",
    "step-5-cells-anchorBC.md": "/competitive-baseline",
    "step-04-meta-observe.md": "/meta-observe",
    "step-6-meta-observe.md": "/meta-observe",
    "step-05-meta-diagnose.md": "/meta-diagnose",
    "step-7-meta-diagnose.md": "/meta-diagnose",
    "step-06-08-analytics.md": "manual",
    "step-8-meta-prioritize.md": "/meta-prioritize",
    "step-09-reflection.md": "/meta-reflect",
    "step-9-reflection.md": "/meta-reflect",
    "step-v2-1-dimensionalization.md": "manual",
    "step-v2-2-ground-truth.md": "manual",
    "step-v2-2-9-meta-analysis.md": "manual",
    "step-v2-3-meta-analysis.md": "manual",
    "step-v2-4-cells-anchorA.md": "/competitive-baseline",
    "step-v2-5-cells-anchorBC.md": "/competitive-baseline",
    "step-v2-6-meta-observe.md": "/meta-observe",
    "step-v2-7-meta-diagnose.md": "/meta-diagnose",
    "step-v2-8-meta-prioritize.md": "/meta-prioritize",
    "step-v2-9-reflection.md": "/meta-reflect",
}


def _repo_root():
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


def classify(fname):
    if "reaction-" in fname:
        return "reaction"
    if "cross-check" in fname or "cross_check" in fname:
        return "cross_check"
    if "reflection-" in fname:
        return "reflection"
    if "brainstorm-" in fname:
        return "brainstorm"
    if "findings-" in fname:
        return "findings"
    if "strategy-" in fname:
        return "strategy"
    if "schema-plan" in fname:
        return "schema_plan"
    if "proposal-" in fname:
        return "proposal"
    if "exercise-plan" in fname:
        return "plan"
    if "plan-" in fname:
        return "plan"
    if fname.startswith("step-"):
        return "exercise_step"
    if fname == "domain-extensions.md":
        return "domain_extension"
    if fname == "methodology.md":
        return "methodology"
    if fname == "implementation-backlog.md":
        return "backlog"
    if fname == "meta-optimization.md":
        return "report"
    return None


def classify_parents(fname, atype, relpath):
    parts = relpath.split("/")
    if len(parts) > 1 and parts[0].startswith("exercise_"):
        exercise_dir = parts[0]
        step = parts[1] if len(parts) > 1 else fname
        chain = STEP_CHAIN.get(step, [])
        return [f"docs/{exercise_dir}/{p}" for p in chain]
    return []


def generated_by(fname, atype):
    if atype == "exercise_step":
        return STEP_GENERATED_BY.get(fname, "manual")
    return "manual"


def render_frontmatter(meta):
    atype = meta["artifact_type"]
    authority = meta["authority"]
    lines = ["---",
             f"artifact_type: {atype}",
             f"authority: {authority}",
             f"generated_by: {meta['generated_by']}"]
    parents = meta.get("parent_artifacts", [])
    if parents:
        lines.append("parent_artifacts:")
        for p in parents:
            lines.append(f"  - {p}")
    else:
        lines.append("parent_artifacts: []")
    for extra in ["convergence", "trigger", "tags", "provenance_note"]:
        if extra in meta:
            val = meta[extra]
            if extra == "provenance_note" and val:
                val = val.replace('"', "'")
                lines.append(f'provenance_note: "{val}"')
            elif extra == "tags" and isinstance(val, list):
                lines.append(f"tags: [{', '.join(val)}]")
            elif isinstance(val, str):
                lines.append(f"{extra}: {val}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def parse_existing_fm(text):
    """Minimal frontmatter parser — returns dict of existing values for preservation.
    Stores _raw_provenance for block-scalar detection."""
    m = FM_RE.match(text)
    if not m:
        return {}
    meta, key = {}, None
    in_block = False
    block_lines = []
    for line in m.group(1).split("\n"):
        if not line.strip(): continue
        if line.startswith("  - "):
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(line[4:].strip())
        elif ":" in line and not in_block:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip().strip('"')
            if val == "[]": meta[key] = []
            elif key == "parent_artifacts" and val == "":
                meta[key] = []
            elif val in (">", "|"):
                # Block scalar — read subsequent indented lines
                meta[key] = ">"  # marker
                in_block = True
                block_lines = [line]
            else:
                meta[key] = val
        elif in_block and line.startswith("  "):
            block_lines.append(line)
        else:
            in_block = False
    if in_block and block_lines:
        meta["_raw_provenance"] = "\n".join(block_lines)
    return meta


def apply_to_file(path, meta):
    text = path.read_text()
    existing = parse_existing_fm(text)
    # A9: preserve hand-filled parent_artifacts when generated list is empty
    if existing and not meta.get("parent_artifacts"):
        existing_parents = existing.get("parent_artifacts", [])
        if isinstance(existing_parents, list) and existing_parents:
            meta["parent_artifacts"] = existing_parents
    # Carry forward provenance_note, convergence, tags from existing if present
    for field in ["provenance_note", "convergence", "tags", "trigger"]:
        if field in existing and field not in meta:
            meta[field] = existing[field]
    fm = render_frontmatter(meta)
    # A10: if existing had block-scalar provenance_note, inject raw text
    if "_raw_provenance" in existing:
        raw = existing["_raw_provenance"]
        fm = re.sub(r'provenance_note: "[^"]*"', raw, fm)
    if FM_RE.match(text):
        new = FM_RE.sub(fm, text, count=1)
    else:
        new = fm + "\n" + text if not text.startswith("\n") else fm + text
    if new != text:
        path.write_text(new)
        return True
    return False


def main():
    policy_path = ENGINE_DIR / "policy.json"
    if "--policy" in sys.argv:
        idx = sys.argv.index("--policy")
        if idx + 1 < len(sys.argv):
            policy_path = Path(sys.argv[idx + 1])

    TYPE_AUTHORITY, cfg = load_policy(policy_path)
    docs_dir = cfg.get("docs_dir", "docs")
    extra_roots = [REPO / r for r in cfg.get("extra_roots", [])]
    skip = set(cfg.get("skip", []))

    changed = 0
    total = 0
    all_paths = list((REPO / docs_dir).rglob("*.md"))
    for root in extra_roots:
        all_paths += list(root.rglob("*.md"))

    for path in sorted(all_paths):
        rel = path.relative_to(REPO).as_posix()
        if rel in skip:
            continue
        total += 1

        atype = classify(path.name)
        if atype is None:
            print(f"SKIP {rel} — unclassifiable")
            continue

        authority = TYPE_AUTHORITY.get(atype, "derived")
        parents = classify_parents(path.name, atype, rel)
        gen = generated_by(path.name, atype)

        meta = {
            "artifact_type": atype,
            "authority": authority,
            "generated_by": gen,
            "parent_artifacts": parents,
        }
        if apply_to_file(path, meta):
            changed += 1
            print(f"  updated {rel}")

    print(f"\n{changed}/{total} files updated.")


if __name__ == "__main__":
    main()
