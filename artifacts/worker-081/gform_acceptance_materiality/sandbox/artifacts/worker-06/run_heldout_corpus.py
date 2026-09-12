#!/usr/bin/env python3
"""Run the FORM-HELDOUT-07 two-stage measurement on the frozen held-out corpus.

Stage A (structural):  python3 artifacts/formulation/tools/check_class_schema.py --json FIXTURE
Stage B (semantic):    python3 artifacts/worker-06/spec_conformance_audit.py FIXTURE   (baseline)

The manifest is hashed BEFORE any stage runs. Controls must pass both stages or the
measurement is invalid (H5). The report follows H4: aggregates plus union escapes only.

Usage: python3 run_heldout_corpus.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CORPUS = HERE / "heldout_corpus"
STRUCT_GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
SEM_GATE = HERE / "spec_conformance_audit.py"
CST = timezone(timedelta(hours=8))


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_stage_a(target: Path):
    proc = subprocess.run([sys.executable, str(STRUCT_GATE), "--json", str(target)],
                          capture_output=True, text=True, timeout=180)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"exit": proc.returncode,
            "verdict": rep.get("verdict"),
            "escaped": proc.returncode == 0 and rep.get("verdict") == "pass",
            "failed_rules": rep.get("failed_rules", []),
            "stderr": proc.stderr.strip()[:200]}


def run_stage_b(target: Path):
    proc = subprocess.run([sys.executable, str(SEM_GATE), str(target)],
                          capture_output=True, text=True, timeout=180)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"exit": proc.returncode,
            "verdict": rep.get("verdict"),
            "escaped": rep.get("verdict") == "accept",
            "failed_rules": rep.get("failed_rules", []),
            "stderr": proc.stderr.strip()[:200]}


def main():
    manifest_path = CORPUS / "manifest.json"
    manifest_sha = sha(manifest_path)  # hashed before any stage run
    manifest = json.loads(manifest_path.read_text())

    # integrity: fixture hashes must match the manifest recorded before the run
    tampered = [e["fixture"] for e in manifest["mutants"] + manifest["controls"]
                if not (ROOT / e["path"]).exists() or sha(ROOT / e["path"]) != e["sha256"]]

    controls = []
    for e in manifest["controls"]:
        a, b = run_stage_a(ROOT / e["path"]), run_stage_b(ROOT / e["path"])
        controls.append({"fixture": e["fixture"], "kind": e["kind"],
                         "stage_a": a, "stage_b": b,
                         "accepted_both": a["exit"] == 0 and b["escaped"]})
    for p in manifest["frozen_canonical_controls"]:
        a, b = run_stage_a(ROOT / p), run_stage_b(ROOT / p)
        controls.append({"fixture": p.split("/")[-1], "kind": "frozen-canonical",
                         "stage_a": a, "stage_b": b,
                         "accepted_both": a["exit"] == 0 and b["escaped"]})
    controls_ok = all(c["accepted_both"] for c in controls) and not tampered

    results, a_esc, b_esc, both_esc = [], 0, 0, 0
    for e in manifest["mutants"]:
        a, b = run_stage_a(ROOT / e["path"]), run_stage_b(ROOT / e["path"])
        a_esc += 1 if a["escaped"] else 0
        b_esc += 1 if b["escaped"] else 0
        both = a["escaped"] and b["escaped"]
        both_esc += 1 if both else 0
        results.append({"fixture": e["fixture"], "family": e["family"], "rephrased": e["rephrased"],
                        "stage_a": a, "stage_b": b, "union_escape": both})

    n = len(results)
    FAMILY_REASONS = {
        "c2-conclusion-in-c0": "the C2-level conclusion is stated in conclusion.statement_natural_language prose while conclusion_type stays scc_c0_future_inextendibility, and neither stage scans the statement text for a regularity-level claim.",
        "composite-regularity": "the merged requirement is phrased as 'continuous, or alternatively twice differentiable' inside an unscanned extensions key, so no composite token and no scanned path matches.",
        "curvature-hypothesis": "a Kretschmann-boundedness hypothesis sits under non_vacuity.extensions, and extension subtrees are skipped by the gate's key scan and not inspected semantically.",
        "quantifier-order": "the ordered quantifier list is reordered (extension quantifier before the data quantifier) while all binders remain present, which neither stage checks for order consistency.",
        "regularity-substitution": "the H2_loc substitution is carried by extension_predicate.extensions.category prose rather than the frozen regularity field, so the frozen-axis comparison sees no change.",
        "scope-prose": "the C2-level strengthening is appended to scope_statement, which is not in the assertive-path scan set.",
        "symmetry-assumption": "a spherical-symmetry restriction is stated in data_class.extensions.symmetry_note while data_class.symmetry still reads none_assumed; the contradiction is inside an extensions block.",
        "transfer-failure": "a false transfer row (full_measure implies residual_comeager) is added to genericity.transfer_failures; neither stage checks the truth of transfer rows.",
        "wcc-content-in-scc": "the WCC content is in visibility.reason, a deliberately exempt explanatory field, rather than in the visibility predicate or conclusion block.",
    }
    escaped_families = {}
    for r in results:
        if r["union_escape"]:
            escaped_families.setdefault(r["family"], []).append(r)
    fam_rows = []
    for fam, rows in sorted(escaped_families.items()):
        fam_rows.append({"family": fam, "count": len(rows), "example_name": rows[0]["fixture"],
                         "one_sentence_reason": FAMILY_REASONS.get(fam, "no rule in either stage inspects this axis")})
    report = {
        "corpus_id": "FORM-HELDOUT-07",
        "assignment": "assign-FORM-HELDOUT-07-2026-09-11T23:44:25+08:00",
        "generated_at": now(),
        "manifest_sha256_before_run": manifest_sha,
        "valid": bool(controls_ok),
        "invalid_reasons": ([] if controls_ok else
                            (["tampered or missing fixtures: " + ", ".join(tampered)] if tampered else [])
                            + [f"control {c['fixture']} rejected by a stage" for c in controls if not c["accepted_both"]]),
        "stages": {
            "structural": {"gate": str(STRUCT_GATE.relative_to(ROOT)), "sha256": sha(STRUCT_GATE)},
            "semantic": {"gate": str(SEM_GATE.relative_to(ROOT)), "sha256": sha(SEM_GATE)},
        },
        "corpus": {
            "mutants": n,
            "families": len({r["family"] for r in results}),
            "rephrased": sum(1 for r in results if r["rephrased"]),
            "controls": len(controls),
        },
        "aggregates": {
            "structural_escape_rate": round(a_esc / max(1, n), 4),
            "semantic_escape_rate": round(b_esc / max(1, n), 4),
            "union_escape_rate": round(both_esc / max(1, n), 4),
            "structural_caught": n - a_esc,
            "semantic_caught": n - b_esc,
            "union_caught": n - both_esc,
        },
        "escape_families": fam_rows,
        "note_R17_R25": ("R17-R25 in the canonical gate were derived from the earlier worker-06 corpus; "
                         "this held-out corpus was authored after that derivation, so the union escape rate "
                         "above is the out-of-sample estimate (H6)."),
        "measurement_rule": "union escape = accepted by BOTH stages; controls must be accepted by both stages or valid=false",
    }
    (CORPUS / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (CORPUS / "raw_verdicts.json").write_text(json.dumps(
        {"manifest_sha256_before_run": manifest_sha, "controls": controls, "results": results}, indent=2) + "\n")
    a = report["aggregates"]
    print(f"valid={report['valid']} | structural escape {a['structural_escape_rate']} | "
          f"semantic escape {a['semantic_escape_rate']} | union escape {a['union_escape_rate']}")
    print("controls ok:", controls_ok, "| tampered:", tampered)
    print("escape families:", [(f["family"], f["count"]) for f in fam_rows])
    return 0


if __name__ == "__main__":
    sys.exit(main())
