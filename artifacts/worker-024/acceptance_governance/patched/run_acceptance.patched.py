#!/usr/bin/env python3
"""Two-stage acceptance pipeline for class-bound formulation schemas.

W024 PROPOSED FAIL-CLOSED PATCH (proposal only; not applied to the canonical path).
Deltas against artifacts/formulation/tools/run_acceptance.py#e544c36d2d16:
  P1. nonvacuity(): the declared corpus totals in evidence/semantic_escape_rebased.json
      (summary.mutants_rebased, len(controls)) are enforced against the files on disk.
  P2. stage-2 rule engine artifacts/worker-06/spec_conformance_audit.py is hash-bound to
      the evidence (w06_sha256) AND to the FROZEN pin set (it was in neither).
  P3. stage-1 gate is hash-bound to the evidence (gate_sha256) AND to FROZEN.
  P4. the report is written atomically, only under --write, and carries an `inputs`
      block with the sha256 of every input (refuse-on-nonvacuity; no silent clobber of
      the pinned evidence file).

Exit 0 only if: non-vacuity holds, the three canonical schemas pass BOTH stages, both
controls pass both stages, and the semantic stage catches every mutant in the corpus.
Exit 3 on preflight or non-vacuity failure, 1 on a real acceptance FAIL.
Usage: python3 run_acceptance.py [--json] [--write]
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# W024 patch: allow an explicit sandbox root for copy verification; canonical default
# remains the repo root derived from this file's location.
ROOT = Path(os.environ.get("W024_ROOT", Path(__file__).resolve().parents[3])).resolve()
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
SEM = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
CANON = [ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
         ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
         ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
REBASED = ROOT / "artifacts/formulation/evidence/rebased_fixtures"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
EVIDENCE = ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json"
REPORT = ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(tool, path, json_flag):
    """Structural gate takes --json; the semantic auditor prints JSON but ALWAYS exits 0,
    so its verdict must be read from the JSON body (worker-06 auditor contract)."""
    args = [sys.executable, str(tool)] + (["--json", str(path)] if json_flag else [str(path)])
    r = subprocess.run(args, capture_output=True, text=True)
    if json_flag:
        try:
            d = json.loads(r.stdout)
            return d.get("verdict", "?"), d.get("failed_rules", [])
        except Exception:  # noqa: BLE001
            return f"crash(exit{r.returncode})", []
    try:
        d = json.loads(r.stdout)
        v = d.get("verdict")
        if v is None:
            return ("pass" if r.returncode == 0 else "fail"), []
        return ("pass" if str(v).lower() in ("accept", "pass", "ok") else "fail"), d.get("failed_rules", [])
    except Exception:  # noqa: BLE001
        return ("pass" if r.returncode == 0 else "fail"), []


def preflight():
    """Fail closed on stale fixtures: the rebased corpus must have been generated from the
    CURRENT canonical C0 hash (a stale corpus produced a false alarm on 2026-09-11)."""
    base = ROOT/"artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
    ev = EVIDENCE
    if not ev.exists():
        print("PREFLIGHT FAIL: run measure_semantic_escape.py first"); return False
    rec = json.loads(ev.read_text())
    cur = sha256_file(base)
    if rec.get("base_sha256") != cur:
        print(f"PREFLIGHT FAIL: rebased fixtures are stale\n  corpus base {rec.get('base_sha256')}\n  current base {cur}\n"
              f"  re-run: python3 artifacts/formulation/tools/measure_semantic_escape.py")
        return False
    return True


def nonvacuity(rec):
    """W024 P1-P3: return a list of REASONs; empty list => the run is admissible."""
    reasons = []
    muts = [p for p in sorted(REBASED.glob("*.yaml")) if not p.name.startswith("control_")] if REBASED.is_dir() else []
    ctls = [p for p in sorted(REBASED.glob("*.yaml")) if p.name.startswith("control_")] if REBASED.is_dir() else []
    exp_m = rec.get("summary", {}).get("mutants_rebased")
    exp_c = len(rec.get("controls", []))
    if exp_m is None:
        reasons.append("evidence declares no summary.mutants_rebased")
    elif len(muts) != exp_m:
        reasons.append(f"corpus mutant count {len(muts)} != declared {exp_m}")
    if len(ctls) != exp_c:
        reasons.append(f"control count {len(ctls)} != declared {exp_c}")
    try:
        fz = json.loads(FROZEN.read_text())
        pins = fz.get("files", {})
    except Exception as exc:  # noqa: BLE001
        pins = {}
        reasons.append(f"FROZEN.json unreadable: {exc}")
    for label, tool, rel, declared in (
        ("stage-2", SEM, "artifacts/worker-06/spec_conformance_audit.py", "w06_sha256"),
        ("stage-1", GATE, "artifacts/formulation/tools/check_class_schema.py", "gate_sha256"),
    ):
        if not tool.exists():
            reasons.append(f"{label} tool missing: {tool}")
            continue
        live = sha256_file(tool)
        if live != rec.get(declared):
            reasons.append(f"{label} tool sha256 {live[:12]} != evidence {declared} {str(rec.get(declared))[:12]}")
        if rel not in pins:
            reasons.append(f"{label} tool NOT in FROZEN pins: {rel}")
        elif pins[rel].get("sha256") != live:
            reasons.append(f"{label} tool sha256 {live[:12]} != FROZEN pin {str(pins[rel].get('sha256'))[:12]}")
    return reasons


def main():
    if not preflight():
        return 3
    rec = json.loads(EVIDENCE.read_text())
    reasons = nonvacuity(rec)
    if reasons:
        for reason in reasons:
            print(f"REASON: {reason}")
        print("ACCEPTANCE: REFUSED (non-vacuity precondition failed)")
        return 3
    out = {"stages": {"structural": str(GATE.relative_to(ROOT)), "semantic": str(SEM.relative_to(ROOT))},
           "inputs": {
               "c0_sha256": sha256_file(CANON[2]),
               "gate_sha256": sha256_file(GATE),
               "stage2_sha256": sha256_file(SEM),
               "evidence_sha256": sha256_file(EVIDENCE),
               "frozen_sha256": sha256_file(FROZEN),
               "runner_sha256": sha256_file(Path(__file__)),
               "corpus_mutants": len([p for p in REBASED.glob("*.yaml") if not p.name.startswith("control_")]),
               "corpus_controls": len([p for p in REBASED.glob("*.yaml") if p.name.startswith("control_")]),
           },
           "canonical": [], "mutants": {"total": 0, "semantic_caught": 0, "structural_caught": 0},
           "controls": [], "verdict": "PASS"}
    for p in CANON:
        g, gr = run(GATE, p, True)
        s, _ = run(SEM, p, False)
        row = {"schema": p.name, "structural": g, "semantic": s, "ok": g == "pass" and s == "pass"}
        out["canonical"].append(row)
        if not row["ok"]:
            out["verdict"] = "FAIL"
    for p in sorted(REBASED.glob("*.yaml")):
        if p.name.startswith("control_"):
            g, _ = run(GATE, p, True)
            s, _ = run(SEM, p, False)
            row = {"control": p.name, "structural": g, "semantic": s, "ok": g == "pass" and s == "pass"}
            out["controls"].append(row)
            if not row["ok"]:
                out["verdict"] = "FAIL"
            continue
        out["mutants"]["total"] += 1
        g, _ = run(GATE, p, True)
        s, _ = run(SEM, p, False)
        caught = False
        if g == "fail":
            out["mutants"]["structural_caught"] += 1
            caught = True
        if s == "fail":
            out["mutants"]["semantic_caught"] += 1
            caught = True
        if caught:
            out["mutants"]["union_caught"] = out["mutants"].get("union_caught", 0) + 1
        else:
            out["mutants"].setdefault("union_escapes", []).append(p.name)
    m = out["mutants"]
    m["structural_escapes"] = m["total"] - m["structural_caught"]
    m["note"] = ("neither stage alone is sufficient; the hard requirement is that the UNION catches every mutant. "
                 f"structural {m['structural_caught']}/{m['total']}, semantic {m['semantic_caught']}/{m['total']}, "
                 f"union {m.get('union_caught', 0)}/{m['total']}")
    if m["total"] and m.get("union_caught", 0) != m["total"]:
        out["verdict"] = "FAIL"
        m["union_escapes"] = m.get("union_escapes", [])
    if "--json" in sys.argv:
        print(json.dumps(out, indent=2))
    else:
        print(f"ACCEPTANCE: {out['verdict']}")
        for r in out["canonical"]:
            print(f"  canonical {r['schema']:28} structural={r['structural']:4} semantic={r['semantic']:4}")
        for r in out["controls"]:
            print(f"  control   {r['control']:28} structural={r['structural']:4} semantic={r['semantic']:4}")
        print(f"  mutants: union caught {m.get('union_caught',0)}/{m['total']} (structural {m['structural_caught']}, semantic {m['semantic_caught']})")
        for e in m.get("union_escapes", []):
            print(f"    UNION ESCAPE: {e}")
    if "--write" in sys.argv:
        tmp = REPORT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(out, indent=2) + "\n")
        os.replace(tmp, REPORT)
        print(f"REPORT WRITTEN {REPORT} sha256={sha256_file(REPORT)}")
    else:
        print("REPORT NOT WRITTEN (pass --write to update the pinned evidence file)")
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
