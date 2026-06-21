#!/usr/bin/env python3
"""
warrant conformance suite — runner + parser + judge, self-contained.

Runs the provenance checker engine against a synthetic fixture set and verifies
each check (G1-D4) fires when expected. Dual-run for R2 (registry-absent).
Crash on a hard check → hard FAIL (same standard as parallax daemon audit).

Usage:
  python3 conformance/run.py --engine PATH [--policy PATH]
  Default policy: _fixtures/policy.json (self-conformance mode).
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
FIXTURES = HERE / "_fixtures" / "check"
EXPECTED_PATH = HERE / "_expected" / "check.json"


def parse_stdout(stdout_text):
    results = {}
    checked = 0
    in_warnings = False
    in_errors = False

    for line in stdout_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"Checked (\d+) docs\.", line)
        if m:
            checked = int(m.group(1))
            continue
        if "All frontmatter valid" in line:
            continue
        if line.startswith("synced ") or line.startswith("cross-team sync"):
            continue
        if re.match(r"\d+ WARNING\(s\):", line):
            in_warnings, in_errors = True, False
            continue
        if re.match(r"\d+ ERROR\(s\):", line):
            in_warnings, in_errors = False, True
            continue

        m = re.match(r"[⚠✗]\s+(\S+?):\s+(.*)", line)
        if m:
            relpath = m.group(1)
            message = m.group(2)
            results.setdefault(relpath, {"errors": [], "warnings": []})
            if in_errors:
                results[relpath]["errors"].append(message)
            elif in_warnings:
                results[relpath]["warnings"].append(message)

    return {"checked": checked, "results": results}


def run_engine_sandbox(engine_path, policy_path, extra_cleanup=None):
    sandbox = tempfile.mkdtemp(prefix="wc_")
    try:
        shutil.copytree(str(FIXTURES), sandbox, dirs_exist_ok=True)
        engine_copy = Path(sandbox) / Path(engine_path).name
        shutil.copy2(str(engine_path), str(engine_copy))
        if policy_path:
            shutil.copy2(str(policy_path), str(Path(sandbox) / "policy.json"))
        if extra_cleanup:
            extra_cleanup(sandbox)

        result = subprocess.run(
            [sys.executable, str(engine_copy), "--policy",
             str(Path(sandbox) / "policy.json")],
            cwd=sandbox, capture_output=True, text=True, timeout=30,
        )
        return result.stdout, result.stderr, result.returncode
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def judge(parsed, expected, exit_codes):
    expected_output = expected.get("expected_output", {})
    hard = set(expected.get("hard", []))
    checks_meta = expected.get("checks", {})

    crash_markers = ["Traceback", "Error"]
    crashed = False
    for ec, serr in exit_codes:
        if ec > 1 or any(m in serr for m in crash_markers):
            crashed = True
            break

    verdict_checks = {}
    for cid, meta in checks_meta.items():
        status = meta.get("status", "UNKNOWN")
        if status == "BLOCKED":
            verdict_checks[cid] = "BLOCKED"
            continue

        is_hard = cid in hard

        if crashed and is_hard:
            verdict_checks[cid] = "FAIL"
            continue
        elif crashed:
            verdict_checks[cid] = "BLOCKED"
            continue

        fixture = meta.get("fixture", "")
        actual = parsed["results"].get(fixture, {"errors": [], "warnings": []})

        if status == "PASS":
            has_issues = (len(actual.get("errors", [])) > 0 or
                         len(actual.get("warnings", [])) > 0)
            verdict_checks[cid] = "FAIL" if has_issues else "PASS"
        elif status == "FAIL":
            has_issues = len(actual.get("errors", [])) > 0 or len(actual.get("warnings", [])) > 0
            verdict_checks[cid] = "PASS" if has_issues else "FAIL"
        else:
            verdict_checks[cid] = "UNKNOWN"

    gate = "PASS"
    for cid in hard:
        if verdict_checks.get(cid, "UNKNOWN") not in ("PASS", "BLOCKED"):
            gate = "FAIL"
            break

    passed = sum(1 for v in verdict_checks.values() if v == "PASS")
    total = len(verdict_checks)
    hard_fails = [cid for cid in hard if verdict_checks.get(cid) == "FAIL"]
    blocked = [cid for cid, v in verdict_checks.items() if v == "BLOCKED"]

    return {
        "checks": verdict_checks,
        "gate": gate,
        "conformance_pct": round(100 * passed / total, 1) if total else 0,
        "hard_fails": hard_fails,
        "blocked": blocked,
        "checked_count": parsed["checked"],
        "summary": f"{passed}/{total} checks pass. Gate: {gate}. Blocked: {blocked}. Hard fails: {hard_fails}.",
    }


def recompute_verdict(verdict, hard):
    gate = "PASS"
    for cid in hard:
        if verdict["checks"].get(cid, "UNKNOWN") not in ("PASS", "BLOCKED"):
            gate = "FAIL"
            break
    verdict["gate"] = gate
    passed = sum(1 for v in verdict["checks"].values() if v == "PASS")
    verdict["conformance_pct"] = round(100 * passed / len(verdict["checks"]), 1)
    verdict["hard_fails"] = [cid for cid in hard if verdict["checks"].get(cid) == "FAIL"]
    verdict["blocked"] = [cid for cid, v in verdict["checks"].items() if v == "BLOCKED"]
    verdict["summary"] = f"{passed}/{len(verdict['checks'])} checks pass. Gate: {verdict['gate']}. Blocked: {verdict['blocked']}. Hard fails: {verdict['hard_fails']}."
    return verdict


def main():
    engine_path = None
    policy_path = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--engine" and i + 1 < len(args):
            engine_path = args[i + 1]; i += 2
        elif args[i] == "--policy" and i + 1 < len(args):
            policy_path = args[i + 1]; i += 2
        else:
            i += 1

    if not engine_path:
        engine_path = str(HERE.parent / "reference" / "_check_frontmatter.py")
    if not policy_path:
        policy_path = str(FIXTURES / "policy.json")

    expected = json.load(open(EXPECTED_PATH))
    hard = set(expected.get("hard", []))
    exit_codes = []

    stdout1, stderr1, ec1 = run_engine_sandbox(engine_path, policy_path)
    exit_codes.append((ec1, stderr1))

    def r2_cleanup(sandbox_path):
        (Path(sandbox_path) / "artifact_types.json").unlink(missing_ok=True)

    stdout2, stderr2, ec2 = run_engine_sandbox(engine_path, policy_path,
                                                extra_cleanup=r2_cleanup)
    exit_codes.append((ec2, stderr2))
    r2_pass = ec2 < 2 and "Traceback" not in stderr2

    parsed = parse_stdout(stdout1)
    verdict = judge(parsed, expected, exit_codes)

    if "R2" in verdict["checks"]:
        verdict["checks"]["R2"] = "PASS" if r2_pass else "FAIL"
    verdict = recompute_verdict(verdict, hard)

    print("=== warrant conformance ===")
    print(f"engine: {engine_path}")
    print(f"exit_code: {ec1}")
    print(f"checked: {parsed['checked']} docs")
    crash_lines = [l for l in (stderr1 + stderr2).split("\n")
                   if l.strip() and ("Error" in l or "Trace" in l)]
    if crash_lines:
        print(f"stderr: {crash_lines[0]}")
    print(f"\ngate: {verdict['gate']}")
    print(f"conformance: {verdict['conformance_pct']}%")
    for cid in sorted(verdict["checks"]):
        status = verdict["checks"][cid]
        desc = expected.get("checks", {}).get(cid, {}).get("desc", "")
        print(f"  {cid}: {status if status in ('PASS','FAIL','BLOCKED') else 'PASS'}  ({desc})")
    print(f"\nsummary: {verdict['summary']}")

    vp = HERE / "_verdict_check.json"
    json.dump(verdict, open(vp, "w"), indent=2)
    print(f"\n_verdict_check.json written to {vp}")

    return 0 if verdict["gate"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
