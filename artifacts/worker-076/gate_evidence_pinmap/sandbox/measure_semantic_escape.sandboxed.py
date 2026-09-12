#!/usr/bin/env python3
"""Measure the canonical gate's SEMANTIC escape rate on an independent mutation corpus,
re-based onto the canonical key layout so that verdicts are not format-dominated.

Input : artifacts/worker-06/semantic_fixtures/manifest.json (worker-authored mutations,
        originally based on the worker C0 draft layout)
Method: apply each recorded mutation (path = value / delete) to the FROZEN canonical C0
        schema, then run BOTH the canonical structural gate and worker-06's semantic
        auditor. Report escapes, catches, and false positives on controls.
Output: artifacts/formulation/evidence/semantic_escape_rebased.json
"""
from __future__ import annotations
import ast
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
BASE = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
MAN = ROOT / "artifacts/worker-06/semantic_fixtures/manifest.json"
OUT = Path("/data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-076/gate_evidence_pinmap/sandbox/semantic_escape_rebased.fresh.json")
TMP = Path("/data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-076/gate_evidence_pinmap/sandbox/rebased_fixtures_fresh")
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
W06 = ROOT / "artifacts/worker-06/spec_conformance_audit.py"


def parse_mutation(text: str):
    text = text.strip()
    m = re.match(r"^delete\s+([\w.]+)\s*=\s*None$", text)
    if m:
        return ("delete", m.group(1), None)
    m = re.match(r"^([\w.]+)\s*=\s*(.*)$", text, re.S)
    if not m:
        return None
    path, raw = m.group(1), m.group(2).strip()
    try:
        val = ast.literal_eval(raw)
    except Exception:  # noqa: BLE001
        val = raw.strip("'\"")
    return ("set", path, val)


def apply_op(doc, op):
    kind, path, val = op
    parts = path.split(".")
    cur = doc
    for p in parts[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}
        cur = cur[p]
    if kind == "delete":
        cur.pop(parts[-1], None)
    else:
        cur[parts[-1]] = val


def verdict(tool, path, json_flag=True):
    args = [sys.executable, str(tool)] + (["--json", str(path)] if json_flag else [str(path)])
    r = subprocess.run(args, capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
        return d.get("verdict", "?"), d.get("failed_rules", [])
    except Exception:  # noqa: BLE001
        r2 = subprocess.run([sys.executable, str(tool), str(path)], capture_output=True, text=True)
        out = (r2.stdout or "").strip().splitlines()
        v = "pass" if r2.returncode == 0 else "fail"
        return v, [out[-1][:120]] if out else [f"exit{r2.returncode}"]


def main():
    man = json.loads(MAN.read_text())
    base_doc = yaml.safe_load(BASE.read_text())
    if TMP.exists():
        import shutil
        shutil.rmtree(TMP)  # stale fixtures from earlier corpus revisions must not be counted
    TMP.mkdir(parents=True, exist_ok=True)
    rep = {"base_schema": str(BASE.relative_to(ROOT)), "base_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
           "corpus_manifest": str(MAN.relative_to(ROOT)),
           "corpus_manifest_sha256": hashlib.sha256(MAN.read_bytes()).hexdigest(),
           "gate": str(GATE.relative_to(ROOT)), "gate_sha256": hashlib.sha256(GATE.read_bytes()).hexdigest(),
           "w06_auditor": str(W06.relative_to(ROOT)), "w06_sha256": hashlib.sha256(W06.read_bytes()).hexdigest(),
           "mutants": [], "controls": [], "caveat": (
               "mutations were authored against the worker C0 draft layout; they are re-based here onto the frozen "
               "canonical layout by applying the recorded path=value operation. Mutations whose path does not exist "
               "in the canonical layout are ADDED as smuggled keys, which is the intended semantic mutation.")}
    for i in man["fixtures"]:
        op = parse_mutation(str(i.get("mutation", "")))
        if op is None:
            rep["mutants"].append({"fixture": i["fixture"], "error": "unparsed mutation", "mutation": i.get("mutation")})
            continue
        d = copy.deepcopy(base_doc)
        apply_op(d, op)
        p = TMP / i["fixture"]
        p.write_text(yaml.safe_dump(d, sort_keys=False, width=110))
        gv, gr = verdict(GATE, p)
        wv, wr = verdict(W06, p, json_flag=False)
        wv_norm = "pass" if str(wv).lower() in ("accept", "pass", "ok") else "fail"
        rep["mutants"].append({"fixture": i["fixture"], "leak_family": i.get("leak_family"),
                               "mutation_path": i.get("mutation_path"), "rephrased": bool(i.get("rephrased")),
                               "canonical_verdict": gv, "canonical_failed_rules": gr,
                               "canonical_escape": gv == "pass",
                               "w06_verdict": wv, "w06_escape": wv_norm == "pass"})
    # controls: canonical base unchanged, and base + quoted forbidden phrase (must both PASS)
    for name, mut in [("control_canonical_base", lambda x: None),
                      ("control_quoted_phrase", lambda x: x["anti_scope"]["phrases_that_are_not_this_class"].append(
                          "the forbidden composite wording 'C0 or C2' is quoted here only to ban it"))]:
        d = copy.deepcopy(base_doc); mut(d)
        p = TMP / f"{name}.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False, width=110))
        gv, gr = verdict(GATE, p)
        rep["controls"].append({"name": name, "canonical_verdict": gv, "canonical_failed_rules": gr,
                                "false_positive": gv != "pass"})
    unparsed = [m for m in rep["mutants"] if m.get("error")]
    rep["mutants"] = [m for m in rep["mutants"] if not m.get("error")]
    rep["unparsed_mutations"] = unparsed
    n = len(rep["mutants"])
    esc = sum(1 for m in rep["mutants"] if m.get("canonical_escape"))
    wesc = sum(1 for m in rep["mutants"] if m.get("w06_escape"))
    rep["summary"] = {"mutants_rebased": n, "unparsed": len(unparsed), "canonical_caught": n - esc, "canonical_escaped": esc,
                      "canonical_escape_rate": round(esc / n, 4) if n else None,
                      "w06_caught": n - wesc, "w06_escaped": wesc,
                      "w06_escape_rate": round(wesc / n, 4) if n else None,
                      "controls_false_positive": sum(1 for c in rep["controls"] if c["false_positive"])}
    OUT.write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep["summary"], indent=1))
    print("escaped (canonical):", [m["fixture"] for m in rep["mutants"] if m.get("canonical_escape")])
    print("escaped (w06):", [m["fixture"] for m in rep["mutants"] if m.get("w06_escape")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
