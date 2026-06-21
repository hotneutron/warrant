#!/usr/bin/env python3
"""
warrant apply conformance — verifies _apply_frontmatter stamps correct frontmatter.

Run:  python3 conformance/test_apply.py [--engine PATH] [--policy PATH]
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "_fixtures" / "apply"
EXPECTED_PATH = HERE / "_expected" / "apply.json"
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return None
    meta, key = {}, None
    for line in m.group(1).split("\n"):
        if not line.strip(): continue
        if line.startswith("  - "):
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(line[4:].strip())
        elif ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val.startswith('"') and val.endswith('"'):
                meta[key] = val[1:-1]
            elif val == "[]":
                meta[key] = []
            elif val == "":
                meta[key] = []
            else:
                meta[key] = val
    return meta


def run_apply(engine_path, policy_path):
    sandbox = tempfile.mkdtemp(prefix="wa_")
    engine_copy = Path(sandbox) / Path(engine_path).name
    shutil.copytree(str(FIXTURES), sandbox, dirs_exist_ok=True)
    shutil.copy2(str(engine_path), str(engine_copy))
    pol = policy_path or str(FIXTURES / "policy.json")
    shutil.copy2(str(pol), str(Path(sandbox) / "policy.json"))
    result = subprocess.run(
        [sys.executable, str(engine_copy), "--policy", str(Path(sandbox) / "policy.json")],
        cwd=sandbox, capture_output=True, text=True, timeout=30,
    )
    return sandbox, result.stdout, result.stderr, result.returncode


def check_doc(relpath, content, exp):
    fm = parse_frontmatter(content)
    issues = []
    if exp.get("has_fm", True) and fm is None:
        issues.append("missing frontmatter")
        return issues
    if fm is None: return issues
    for field in ["artifact_type", "authority", "generated_by"]:
        ev = exp.get(field)
        if ev and fm.get(field) != ev:
            issues.append(f"{field}: want {ev!r} got {fm.get(field)!r}")
    ep = exp.get("parent_artifacts")
    if ep is not None:
        ap = fm.get("parent_artifacts", [])
        if isinstance(ap, str): ap = [ap]
        if sorted(ap) != sorted(ep if isinstance(ep, list) else [ep]):
            issues.append(f"parent_artifacts: want {ep} got {ap}")
    # Raw-text assertion: a multi-line `provenance_note: >` block scalar cannot be
    # represented by the field parser, so a field-by-field check would silently miss its
    # destruction. Assert the substring survives in the raw output instead (A10).
    for s in exp.get("body_contains", []):
        if s not in content:
            issues.append(f"body_contains: {s!r} missing (block scalar collapsed/destroyed?)")
    return issues


def main():
    engine_path = None
    policy_path = None
    for i, a in enumerate(sys.argv[1:]):
        if a == "--engine" and i + 1 < len(sys.argv) - 1:
            engine_path = sys.argv[i + 2]
        elif a == "--policy" and i + 1 < len(sys.argv) - 1:
            policy_path = sys.argv[i + 2]

    if not engine_path:
        engine_path = str(HERE.parent / "reference" / "_apply_frontmatter.py")

    exp = json.load(open(EXPECTED_PATH))
    checks_meta = exp.get("checks", {})
    expected_output = exp.get("expected_output", {})
    hard = set(exp.get("hard", []))

    # Run 1: stamp
    sandbox, stdout, stderr, ec = run_apply(engine_path, policy_path)

    results = {}
    for root, dirs, files in os.walk(str(sandbox)):
        for f in sorted(files):
            if not f.endswith(".md"): continue
            spath = Path(root) / f
            rel = spath.relative_to(sandbox).as_posix()
            ex = expected_output.get(rel, {})
            issues = check_doc(rel, spath.read_text(), ex)
            results[rel] = {"issues": issues, "ok": len(issues) == 0}

    # Run 2: idempotency
    sandbox2, stdout2, stderr2, ec2 = run_apply(engine_path, policy_path)
    updated2 = 0
    for line in stdout2.split("\n"):
        if "updated" in line: continue
        if "/" in line and "files updated" in line:
            m = re.match(r"(\d+)/", line)
            if m: updated2 = int(m.group(1))

    shutil.rmtree(sandbox, ignore_errors=True)
    shutil.rmtree(sandbox2, ignore_errors=True)

    verdict = {}
    for cid, meta in checks_meta.items():
        fixture = meta.get("fixture", "")
        if fixture not in results:
            verdict[cid] = "BLOCKED"
            continue
        ok = results[fixture]["ok"]
        if cid == "A3":
            ok = ok and updated2 == 0  # idempotent: no files changed on re-run
        verdict[cid] = "PASS" if ok else "FAIL"

    gate = "PASS"
    for cid in hard:
        if verdict.get(cid, "PASS") != "PASS":
            gate = "FAIL"; break

    passed = sum(1 for v in verdict.values() if v == "PASS")

    print("=== warrant apply conformance ===")
    print(f"engine: {engine_path}")
    for cid in sorted(verdict):
        desc = checks_meta.get(cid, {}).get("desc", "")
        print(f"  {cid}: {verdict[cid]}  ({desc})")
    print(f"\ngate: {gate}  ({passed}/{len(verdict)} pass)")
    if stderr:
        for l in stderr.split("\n"):
            if "Error" in l or "Trace" in l:
                print(f"stderr: {l}"); break

    j = {"checks": verdict, "gate": gate,
         "conformance_pct": round(100 * passed / len(verdict), 1) if verdict else 0}
    json.dump(j, open(HERE / "_verdict_apply.json", "w"), indent=2)
    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
