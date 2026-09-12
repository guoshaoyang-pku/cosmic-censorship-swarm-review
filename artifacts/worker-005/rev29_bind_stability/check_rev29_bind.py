#!/usr/bin/env python3
"""W005-REV29-BIND-STABILITY-01 -- independent binding/stability audit at the
FROZEN rev29 (schema rev13) pins.

Classes: AF-WCC-VAC-GEN; AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN   Node: F1,F2a,F2b
Gate: G-FORM     Reviewer: worker-005     Claim type: measurement only.

What it measures (no writes outside the report directory):
  A. sha256 of the three canonical schemas, their artifacts/formulation/schemas
     mirrors, FROZEN.json, the declared F0 taxonomy, the class-contract
     supplement, the consistency evidence, schemas/taxonomy_cases.jsonl and the
     frozen gate tool.
  B. Every hash declared *inside* each schema's f0_binding
     (declared_f0_sha256, consistency_evidence_sha256) resolved against the
     referenced file on disk -> resolved|mismatch|missing.
  C. Canonical <-> mirror byte identity for each class schema.
  D. FROZEN rev29's pins for every audited path against measured bytes.
  E. The frozen gate tool (artifacts/formulation/tools/check_class_schema.py)
     run per schema, plus a live positive control (mutated temp copy must fail)
     so a PASS cannot come from a no-op checker.
  F. A start/end measurement window: any hash that changes between the two
     measurements is reported as a mid-audit move (moving target), never
     silently averaged.
  G. A mechanical review-pin census (advisory): which reviews/*.json name the
     current pins, with their mechanical verdict/score/reviewer fields.

Falsifier: any declared sha256 that does not equal the measured bytes, any
canonical/mirror divergence, any FROZEN rev29 pin that does not match live
bytes, any mid-audit hash move, or a mutated schema that the frozen gate tool
accepts -- falsifies the claim that the rev13/FROZEN-rev29 evidence base is
bound and stable.

Self-test: python3 check_rev29_bind.py --selftest   (null control + 6 mutants)
Audit:     python3 check_rev29_bind.py --root <repo> --out <dir>
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
MIRROR = {k: "artifacts/formulation/schemas/" + Path(v).name for k, v in SCHEMAS.items()}
DECLARED_TARGETS = {
    "declared_f0_sha256": "research_map/formulation_taxonomy.yaml",
    "consistency_evidence_sha256": "artifacts/formulation/evidence/taxonomy_consistency.json",
}
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CASES = "schemas/taxonomy_cases.jsonl"
GATE_TOOL = "artifacts/formulation/tools/check_class_schema.py"
CLASS_IDS = {
    "F1": "AF-WCC-VAC-GEN",
    "F2a": "AF-SCC-C2-VAC-GEN",
    "F2b": "AF-SCC-C0-VAC-GEN",
}
HEX = re.compile(r"\b[0-9a-f]{64}\b")


def sha256_file(p: Path):
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def measure_tree(root: Path):
    """(A) measure every audited path. Returns {relpath: {sha256,bytes,exists}}."""
    paths = list(SCHEMAS.values()) + list(MIRROR.values()) + [
        FROZEN, SUPPLEMENT, CASES, GATE_TOOL] + list(DECLARED_TARGETS.values())
    out = {}
    for rel in sorted(set(paths)):
        f = root / rel
        if f.exists():
            b = f.read_bytes()
            out[rel] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b), "exists": True}
        else:
            out[rel] = {"sha256": None, "bytes": None, "exists": False}
    return out


def load_yaml(p: Path):
    if yaml is None:
        raise RuntimeError("PyYAML unavailable")
    return yaml.safe_load(p.read_text())


def run_gate(root: Path, rel_schema: str):
    tool = root / GATE_TOOL
    if not tool.exists():
        return {"exit_code": None, "verdict": None, "failed_rules": None,
                "error": f"gate tool missing: {GATE_TOOL}"}
    try:
        cp = subprocess.run([sys.executable, str(tool), "--json", str(root / rel_schema)],
                            capture_output=True, text=True, timeout=120)
    except Exception as e:  # pragma: no cover
        return {"exit_code": None, "verdict": None, "failed_rules": None, "error": repr(e)}
    verdict, rules = None, None
    try:
        j = json.loads(cp.stdout)
        verdict, rules = j.get("verdict"), j.get("failed_rules")
    except Exception:
        verdict = cp.stdout.strip()[:200]
    return {"exit_code": cp.returncode, "verdict": verdict, "failed_rules": rules,
            "stderr_tail": cp.stderr.strip()[-200:]}


def gate_live_control(root: Path, workdir: Path):
    """(E-control) a mutated copy must be rejected by the frozen gate tool."""
    src = root / SCHEMAS["F2b"]
    if not src.exists() or yaml is None:
        return {"ran": False, "reason": "schema or yaml missing"}
    d = load_yaml(src)
    d["class_id"] = ""                      # definite class-identity defect
    d["__unregistered_probe_key__"] = "x"   # R22 unknown-key probe
    mut = workdir / "mutant_schema.yaml"
    mut.write_text(yaml.safe_dump(d, sort_keys=False))
    cp = subprocess.run([sys.executable, str(root / GATE_TOOL), "--json", str(mut)],
                        capture_output=True, text=True, timeout=120)
    rejected = cp.returncode != 0
    try:
        j = json.loads(cp.stdout)
        failed = j.get("failed_rules")
        v = j.get("verdict")
    except Exception:
        failed, v = None, None
    return {"ran": True, "mutant": "class_id='' + unknown key", "exit_code": cp.returncode,
            "verdict": v, "failed_rules": failed, "rejected": rejected}


def review_pin_census(root: Path, pins):
    """(G) mechanical census: review files naming a current pin. Advisory only."""
    rd = root / "reviews"
    pin12 = {k: v[:12] for k, v in pins.items() if v}
    hits = {}
    if not rd.is_dir():
        return hits
    for f in sorted(rd.glob("*.json")):
        try:
            txt = f.read_text(errors="replace")
        except OSError:
            continue
        named = [k for k, p in pin12.items() if p in txt]
        if not named:
            continue
        rec = {"targets": named}
        try:
            j = json.loads(txt)
            for key in ("reviewer", "verdict", "score", "target_id"):
                if key in j:
                    rec[key] = j[key]
        except Exception:
            pass
        hits[f.relative_to(root).as_posix()] = rec
    return hits


def audit(root: Path, gate=True, census=True, mid_hook=None, sleep_s=0):
    t0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    start = measure_tree(root)                      # (A) window open
    report = {
        "task": "W005-REV29-BIND-STABILITY-01",
        "class_ids": list(CLASS_IDS.values()),
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "root": str(root),
        "measured_at_start": t0,
        "claim": ("At the FROZEN rev29 (schema rev13) pins the three class schemas, "
                  "their mirrors, their declared f0_binding hashes, the frozen "
                  "manifest pins and the frozen gate tool form one stable, "
                  "internally consistent binding chain."),
        "falsifier": ("Any declared sha256 != measured bytes; any canonical/mirror "
                      "divergence; any FROZEN rev29 pin != live bytes; any mid-audit "
                      "hash move; or a mutated schema the frozen gate tool accepts."),
        "files": start,
        "defects": [],
        "soft_findings": [],
    }

    # (B) declared hash chain + (C) mirror identity
    chain, mirror = {}, {}
    for node, rel in SCHEMAS.items():
        chain[node], mirror[node] = {}, {}
        p = root / rel
        if not p.exists():
            report["defects"].append(f"D-MISSING schema {rel}")
            continue
        try:
            d = load_yaml(p)
        except Exception as e:
            report["defects"].append(f"D-UNPARSEABLE {rel}: {e!r}")
            continue
        fb = d.get("f0_binding") or {}
        for field, target in DECLARED_TARGETS.items():
            declared = fb.get(field)
            measured = start.get(target, {}).get("sha256")
            status = ("missing" if declared is None else
                      "missing" if measured is None else
                      "resolved" if declared == measured else "mismatch")
            chain[node][field] = {"declared": declared, "measured_path": target,
                                  "measured_sha256": measured, "status": status}
            if status != "resolved":
                report["defects"].append(
                    f"D-DECLARED-HASH {node}.{field} declared={str(declared)[:12]} "
                    f"measured={str(measured)[:12]} status={status}")
        sup = fb.get("class_contract_supplement")
        if sup:
            fp = start.get(sup, {})
            chain[node]["class_contract_supplement"] = {
                "declared_path": sup, "exists": fp.get("exists"),
                "measured_sha256": fp.get("sha256"),
                "frozen_pin": None, "status": None}
            if sup != SUPPLEMENT:
                chain[node]["class_contract_supplement"]["status"] = "path-divergent"
                report["soft_findings"].append(
                    f"S-SUPPLEMENT-PATH {node} points at {sup}, audit tracks {SUPPLEMENT}")
            if not fp.get("exists"):
                report["defects"].append(f"D-MISSING supplement {sup}")
        cid = d.get("class_id")
        if cid != CLASS_IDS[node]:
            report["defects"].append(f"D-CLASS-ID {node}: {cid!r} != {CLASS_IDS[node]!r}")
        mrel = MIRROR[node]
        same = start.get(rel, {}).get("sha256") == start.get(mrel, {}).get("sha256")
        mirror[node] = {"canonical": start.get(rel, {}).get("sha256"),
                        "mirror_path": mrel, "mirror": start.get(mrel, {}).get("sha256"),
                        "byte_identical": bool(same)}
        if not same:
            report["defects"].append(f"D-MIRROR-DIVERGENCE {node}: {rel} vs {mrel}")
    report["declared_hash_chain"] = chain
    report["mirror_identity"] = mirror

    # (D) FROZEN rev29 pins
    fz = {"path": FROZEN, "sha256": start.get(FROZEN, {}).get("sha256"),
          "exists": start.get(FROZEN, {}).get("exists"), "pins_checked": {},
          "pin_mismatches": [], "unpinned": []}
    if fz["exists"]:
        try:
            man = json.loads((root / FROZEN).read_text())
            fz["revision"] = man.get("revision")
            fz["frozen_at"] = man.get("frozen_at")
            fz["file_count"] = len(man.get("files", {}))
            for rel in sorted(set(list(SCHEMAS.values()) + list(MIRROR.values()) +
                                  [SUPPLEMENT, CASES])):
                rec = (man.get("files") or {}).get(rel)
                if rec is None:
                    fz["unpinned"].append(rel)
                    report["defects"].append(f"D-UNPINNED {rel} absent from FROZEN rev29")
                    continue
                live = start.get(rel, {}).get("sha256")
                ok = rec.get("sha256") == live
                fz["pins_checked"][rel] = {"pin": rec.get("sha256"), "live": live, "match": ok}
                if not ok:
                    fz["pin_mismatches"].append(rel)
                    report["defects"].append(
                        f"D-FROZEN-PIN {rel} pin={str(rec.get('sha256'))[:12]} "
                        f"live={str(live)[:12]}")
        except Exception as e:
            report["defects"].append(f"D-FROZEN-UNREADABLE {FROZEN}: {e!r}")
    else:
        report["defects"].append(f"D-MISSING {FROZEN}")
    report["frozen"] = fz

    # (E) gate tool + live control
    if gate:
        report["gate_tool_runs"] = {n: run_gate(root, r) for n, r in SCHEMAS.items()}
        for n, r in report["gate_tool_runs"].items():
            if r.get("exit_code") != 0 or str(r.get("verdict")).lower() != "pass":
                report["defects"].append(f"D-GATE-FAIL {n}: {json.dumps(r)[:200]}")
        with tempfile.TemporaryDirectory() as td:
            ctl = gate_live_control(root, Path(td))
        report["gate_tool_live_control"] = ctl
        if ctl.get("ran") and not ctl.get("rejected"):
            report["defects"].append("D-GATE-CONTROL frozen gate tool accepted a mutated schema")

    # (G) advisory review-pin census
    if census:
        pins = {n: start.get(r, {}).get("sha256") for n, r in SCHEMAS.items()}
        report["review_pin_census"] = review_pin_census(root, pins)
        report["review_pin_census_note"] = (
            "mechanical filename/hash/verdict-field census only; it is not a review, "
            "does not read verdict findings, and does not count as a gate verdict")

    # (F) window close; mid_hook exists only so the selftest can prove that a
    # move *inside* the window is caught (live runs never pass a hook).
    if mid_hook is not None:
        mid_hook(root)
    if sleep_s:
        time.sleep(sleep_s)
    end = measure_tree(root)
    moved = [rel for rel in start if start[rel]["sha256"] != end[rel]["sha256"]]
    report["measured_at_end"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["stability_window"] = {"stable": not moved, "moved_paths": moved,
                                  "start_hashes": {k: v["sha256"] for k, v in start.items()},
                                  "end_hashes": {k: v["sha256"] for k, v in end.items()}}
    for rel in moved:
        report["defects"].append(
            f"D-MID-AUDIT-MOVE {rel} {str(start[rel]['sha256'])[:12]} -> {str(end[rel]['sha256'])[:12]}")
    report["verdict"] = "clean" if not report["defects"] else "defects"
    report["defect_count"] = len(report["defects"])
    return report


# --------------------------------------------------------------------- selftest
def _mk_tree(root: Path, stub_gate_rejects_mutant=True):
    """Synthetic tree with the same relative layout as the live audit."""
    def w(rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    f0 = w("research_map/formulation_taxonomy.yaml", "class_ids: [A, B]\n")
    ev = w("artifacts/formulation/evidence/taxonomy_consistency.json", '{"ok": true}\n')
    sup = w("artifacts/formulation/formulation_taxonomy.yaml", "class_contracts: {}\n")
    w(CASES, '{"case": 1}\n')
    h = lambda p: sha256_file(p)
    files = {FROZEN: None}
    for node, rel in SCHEMAS.items():
        body = (
            f"class_id: {CLASS_IDS[node]}\n"
            "f0_binding:\n"
            f"  declared_f0_artifact: research_map/formulation_taxonomy.yaml\n"
            f"  declared_f0_sha256: {h(f0)}\n"
            f"  consistency_evidence_sha256: {h(ev)}\n"
            f"  class_contract_supplement: {SUPPLEMENT}\n"
        )
        w(rel, body)
        w(MIRROR[node], body)
        files[rel] = h(root / rel)
        files[MIRROR[node]] = h(root / MIRROR[node])
    files[SUPPLEMENT] = h(sup)
    files[CASES] = h(root / CASES)
    w(FROZEN, json.dumps({"revision": 29, "frozen_at": "2026-09-12T00:00:00+08:00",
                          "files": {k: {"sha256": v} for k, v in files.items()}}, indent=1))
    tool = root / GATE_TOOL
    tool.parent.mkdir(parents=True, exist_ok=True)
    tool.write_text(
        "import json,sys,yaml\n"
        "d=yaml.safe_load(open(sys.argv[-1]))\n"
        "bad=[]\n"
        "if not d.get('class_id'): bad.append('R01')\n"
        "if '__unregistered_probe_key__' in d: bad.append('R22')\n"
        "print(json.dumps({'verdict':'pass' if not bad else 'fail','failed_rules':bad}))\n"
        "sys.exit(1 if bad else 0)\n")
    return root


def selftest():
    cases = []

    def check(name, mutate=None, expect_clean=False, expect_defect=None, window_move=None):
        with tempfile.TemporaryDirectory() as td:
            root = _mk_tree(Path(td))
            if mutate:
                mutate(root)
            if window_move:
                rep = audit(root, gate=True, census=False, mid_hook=window_move)
                moved = rep["stability_window"]["moved_paths"]
                ok = bool(moved) and any("D-MID-AUDIT-MOVE" in d for d in rep["defects"])
                cases.append({"case": name, "pass": ok, "moved": moved,
                              "verdict": rep["verdict"]})
                return
            rep = audit(root, gate=True, census=False)
            if expect_clean:
                ok = rep["verdict"] == "clean"
                cases.append({"case": name, "pass": ok, "defects": rep["defects"]})
            else:
                ok = any(expect_defect in d for d in rep["defects"])
                cases.append({"case": name, "pass": ok, "defects": rep["defects"]})

    check("null-control synthetic tree clean", expect_clean=True)

    def m_mirror(root):
        p = root / MIRROR["F1"]
        p.write_text(p.read_text() + "# tamper\n")
    check("mutant mirror divergence detected", mutate=m_mirror,
          expect_defect="D-MIRROR-DIVERGENCE")

    def m_declared(root):
        p = root / SCHEMAS["F2a"]
        p.write_text(p.read_text().replace("declared_f0_sha256: ", "declared_f0_sha256: '00' #"))
    check("mutant wrong declared f0 hash detected", mutate=m_declared,
          expect_defect="D-DECLARED-HASH")

    def m_pin(root):
        j = json.loads((root / FROZEN).read_text())
        j["files"][SCHEMAS["F2b"]]["sha256"] = "0" * 64
        (root / FROZEN).write_text(json.dumps(j))
    check("mutant wrong FROZEN pin detected", mutate=m_pin, expect_defect="D-FROZEN-PIN")

    def m_missing(root):
        (root / DECLARED_TARGETS["declared_f0_sha256"]).unlink()
    check("mutant missing declared target detected", mutate=m_missing,
          expect_defect="D-DECLARED-HASH")

    def m_gate(root):
        (root / SCHEMAS["F1"]).write_text(
            (root / SCHEMAS["F1"]).read_text() + "__unregistered_probe_key__: 1\n")
        m = root / MIRROR["F1"]
        m.write_text((root / SCHEMAS["F1"]).read_text())
        j = json.loads((root / FROZEN).read_text())
        j["files"][SCHEMAS["F1"]]["sha256"] = sha256_file(root / SCHEMAS["F1"])
        j["files"][MIRROR["F1"]]["sha256"] = sha256_file(m)
        (root / FROZEN).write_text(json.dumps(j))
    check("mutant gate-tool failure detected", mutate=m_gate, expect_defect="D-GATE-FAIL")

    def m_control(root):
        # break the gate tool so the live control mutant is *accepted*
        (root / GATE_TOOL).write_text(
            "import json,sys\nprint(json.dumps({'verdict':'pass','failed_rules':[]}))\n")
    check("mutant no-op gate tool caught by live control", mutate=m_control,
          expect_defect="D-GATE-CONTROL")

    check("window move detected across two audits", window_move=m_mirror)

    out = {
        "task": "W005-REV29-BIND-STABILITY-01 selftest",
        "cases": cases,
        "passed": sum(1 for c in cases if c["pass"]),
        "total": len(cases),
        "verdict": "PASS" if all(c["pass"] for c in cases) else "FAIL",
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-gate", action="store_true")
    ap.add_argument("--no-census", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="seconds to hold the stability window open before the end measurement")
    a = ap.parse_args()
    if a.selftest:
        res = selftest()
        print(json.dumps(res, indent=1))
        sys.exit(0 if res["verdict"] == "PASS" else 1)
    root = Path(a.root).resolve()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rep = audit(root, gate=not a.no_gate, census=not a.no_census, sleep_s=a.sleep)
    p = out / "report.json"
    p.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in
                      ("verdict", "defect_count", "defects", "measured_at_start",
                       "measured_at_end", "stability_window")}, indent=1))
    print("report:", p, "sha256:", sha256_file(p))
    sys.exit(0 if rep["verdict"] == "clean" else 1)


if __name__ == "__main__":
    main()
