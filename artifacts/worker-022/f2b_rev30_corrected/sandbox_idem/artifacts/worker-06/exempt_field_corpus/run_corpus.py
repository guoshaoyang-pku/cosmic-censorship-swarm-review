#!/usr/bin/env python3
"""FORM-EXEMPT-09 measurement runner (worker-06).

Runs BOTH frozen stages on every pre-registered fixture:
  stage 1 structural: artifacts/formulation/tools/check_class_schema.py  (canonical gate)
  stage 2 semantic:   artifacts/worker-06/spec_conformance_audit.py      (W06 baseline auditor)

A stage "catches" a mutant when it rejects it. An escape is a mutant accepted by a
stage. The union stage catches when at least one stage rejects. Controls must ALL
pass both stages, otherwise the corpus is format-dominated and the run is INVALID.

Writes only aggregates + per-fixture verdicts; no repair is attempted after the run.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUNS = OUT / "runs"
GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
AUDITOR = ROOT / "artifacts" / "worker-06" / "spec_conformance_audit.py"
CANON = ROOT / "artifacts" / "formulation" / "schemas"
CANON_FILES = ["af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_gate(path: Path, tag: str):
    proc = subprocess.run([sys.executable, str(GATE), "--json", str(path)],
                          capture_output=True, text=True)
    try:
        rep = json.loads(proc.stdout)
    except Exception:
        rep = {"verdict": "error", "failed_rules": ["PARSE"], "failures": [proc.stderr[-200:]]}
    (RUNS / f"{tag}.structural.json").write_text(json.dumps(rep, indent=2) + "\n")
    return {"verdict": rep.get("verdict"), "failed_rules": rep.get("failed_rules", []),
            "failures": rep.get("failures", []), "exit": proc.returncode}


def run_auditor(path: Path, tag: str):
    jf = RUNS / f"{tag}.semantic.json"
    proc = subprocess.run([sys.executable, str(AUDITOR), str(path), "--json", str(jf)],
                          capture_output=True, text=True)
    try:
        rep = json.loads(jf.read_text())
    except Exception:
        rep = {"verdict": "error", "failed_rules": ["PARSE"],
               "problems": [proc.stdout[-200:] + proc.stderr[-200:]]}
    return {"verdict": rep.get("verdict"), "failed_rules": rep.get("failed_rules", []),
            "problems": rep.get("problems", [])[:6], "exit": proc.returncode}


def measure(path: Path, tag: str):
    s = run_gate(path, tag)
    m = run_auditor(path, tag)
    struct_caught = s["verdict"] == "fail"
    sem_caught = m["verdict"] == "reject"
    return {
        "fixture": tag,
        "structural": {"verdict": s["verdict"], "caught": struct_caught,
                       "failed_rules": s["failed_rules"], "details": s["failures"][:3]},
        "semantic": {"verdict": m["verdict"], "caught": sem_caught,
                     "failed_rules": m["failed_rules"], "details": m["problems"][:3]},
        "caught_by_any": struct_caught or sem_caught,
        "escaped_both": (not struct_caught) and (not sem_caught),
    }


def main():
    RUNS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((OUT / "manifest.json").read_text())
    manifest_sha = sha256_file(OUT / "manifest.json")

    # integrity: fixtures on disk must match the pre-registered hashes
    drifts = []
    for e in manifest["fixtures"]:
        p = OUT / e["file"]
        if not p.exists() or sha256_file(p) != e["sha256"]:
            drifts.append(e["name"])
    if drifts:
        print(json.dumps({"error": "fixture hash drift", "fixtures": drifts}))
        return 2

    results = {"controls": [], "mutants": []}
    for e in manifest["fixtures"]:
        row = measure(OUT / e["file"], e["name"])
        row.update({k: e.get(k) for k in ("kind", "base", "class_id")})
        if e["kind"] == "mutant":
            row.update({k: e[k] for k in ("family", "field", "injected_text",
                                          "invariant_refs", "would_be_caught_by",
                                          "rephrased_no_canonical_token")})
            results["mutants"].append(row)
        else:
            row["why_legitimate"] = e.get("why_legitimate")
            results["controls"].append(row)

    # external controls: the three frozen canonical schemas as-is
    canon_rows = []
    for f in CANON_FILES:
        row = measure(CANON / f, "canonical_" + f.replace(".yaml", ""))
        row["kind"] = "control_canonical"
        canon_rows.append(row)

    controls = results["controls"] + canon_rows
    controls_ok = all(not c["caught_by_any"] for c in controls)
    bad_controls = [c["fixture"] for c in controls if c["caught_by_any"]]

    mutants = results["mutants"]
    n = len(mutants)
    struct_esc = sum(1 for r in mutants if not r["structural"]["caught"])
    sem_esc = sum(1 for r in mutants if not r["semantic"]["caught"])
    union_esc = sum(1 for r in mutants if r["escaped_both"])

    fam = {}
    for r in mutants:
        if r["escaped_both"]:
            f = fam.setdefault(r["family"], {"family": r["family"], "count": 0,
                                             "example": r["fixture"], "field": r["field"],
                                             "one_sentence_reason": r["injected_text"]})
            f["count"] += 1

    report = {
        "artifact": "FORM-EXEMPT-09-REPORT",
        "owner": "worker-06",
        "node_id": "A1",
        "class_ids": sorted({r["class_id"] for r in mutants}),
        "gate": "G-CLASSBIND",
        "stage_1_structural": {"tool": "artifacts/formulation/tools/check_class_schema.py",
                               "sha256": sha256_file(GATE)},
        "stage_2_semantic": {"tool": "artifacts/worker-06/spec_conformance_audit.py",
                             "sha256": sha256_file(AUDITOR),
                             "layout_note": ("W06 baseline auditor; rule set derived against the "
                                             "worker draft layout, kept as a second opinion. Its "
                                             "per-fixture verdicts are reported as-is.")},
        "manifest_sha256": manifest_sha,
        "corpus": manifest["counts"],
        "corpus_validity": {
            "controls_all_accepted": controls_ok,
            "failed_controls": bad_controls,
            "verdict": "VALID" if controls_ok else "INVALID_FORMAT_DOMINATED",
        },
        "aggregates": {
            "n_mutants": n,
            "structural_caught": n - struct_esc,
            "semantic_caught": n - sem_esc,
            "union_caught": n - union_esc,
            "structural_escape_rate": round(struct_esc / n, 4) if n else None,
            "semantic_escape_rate": round(sem_esc / n, 4) if n else None,
            "union_escape_rate": round(union_esc / n, 4) if n else None,
            "escape_families": sorted(fam.values(), key=lambda x: (-x["count"], x["family"])),
        },
        "controls": controls,
        "mutants": mutants,
    }
    body = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    (OUT / "report.json").write_text(body)
    (OUT / "report.sha256").write_text(hashlib.sha256(body.encode()).hexdigest() + "  report.json\n")
    print(json.dumps({"report_sha256": hashlib.sha256(body.encode()).hexdigest(),
                      "validity": report["corpus_validity"],
                      "aggregates": report["aggregates"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
