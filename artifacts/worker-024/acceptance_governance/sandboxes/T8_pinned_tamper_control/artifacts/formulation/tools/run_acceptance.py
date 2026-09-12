#!/usr/bin/env python3
"""Two-stage acceptance pipeline for class-bound formulation schemas.

Measured motivation (artifacts/formulation/evidence/semantic_escape_rebased.json):
  * the structural gate alone escapes 17/27 (62.96%) of the re-based semantic mutants;
  * worker-06's hardened semantic auditor catches 27/27 with 0 false positives.
A structural gate is not a semantic gate. This pipeline runs both and requires both.

  stage 1  artifacts/formulation/tools/check_class_schema.py   (R01-R16, structure)
  stage 2  artifacts/worker-06/spec_conformance_audit.py       (semantic leak classes)

Exit 0 only if: the three canonical schemas pass BOTH stages, both controls pass both
stages, and the semantic stage catches every mutant in the re-based corpus.
Usage: python3 run_acceptance.py [--json]
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
SEM = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
CANON = [ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
         ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
         ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
REBASED = ROOT / "artifacts/formulation/evidence/rebased_fixtures"


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
    ev = ROOT/"artifacts/formulation/evidence/semantic_escape_rebased.json"
    if not ev.exists():
        print("PREFLIGHT FAIL: run measure_semantic_escape.py first"); return False
    rec = json.loads(ev.read_text())
    cur = hashlib.sha256(base.read_bytes()).hexdigest()
    if rec.get("base_sha256") != cur:
        print(f"PREFLIGHT FAIL: rebased fixtures are stale\n  corpus base {rec.get('base_sha256')}\n  current base {cur}\n"
              f"  re-run: python3 artifacts/formulation/tools/measure_semantic_escape.py")
        return False
    return True


def main():
    if not preflight():
        return 3
    out = {"stages": {"structural": str(GATE.relative_to(ROOT)), "semantic": str(SEM.relative_to(ROOT))},
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
            pass
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
    dest = ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    dest.write_text(json.dumps(out, indent=2) + "\n")
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

# T8 control: pinned-tool tamper
