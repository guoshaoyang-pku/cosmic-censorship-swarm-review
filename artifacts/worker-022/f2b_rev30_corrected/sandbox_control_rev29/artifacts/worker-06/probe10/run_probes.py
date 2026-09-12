#!/usr/bin/env python3
"""FORM-PROBE-10 two-stage measurement runner (worker-06).

Stages
  A   artifacts/formulation/tools/check_class_schema.py --json FIXTURE   (R01-R31)
  B   artifacts/worker-06/spec_conformance_audit.py FIXTURE               (frozen, as specified)
  B'  artifacts/worker-06/probe10/audit_calibrated.py FIXTURE             (documented R03 delta)
  B*  spec_conformance_audit.py --hardened FIXTURE                        (proposed repaired set)

Primary union-escape measure = accepted by BOTH A and B' (calibrated; controls pass).
The frozen-B and hardened-B rates are reported alongside as secondary measures.

  python3 run_probes.py --preflight   # controls only, no mutant verdicts inspected
  python3 run_probes.py --run         # freeze-check, full run, report.json + blindspot_report.json

Pre-registration: --run hashes manifest.json BEFORE the first mutant verdict and records
that hash in report.json.  Fixtures whose bytes drifted from the manifest abort the run.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
FIX = HERE / "fixtures"
GATE_A = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
GATE_B = HERE.parent / "spec_conformance_audit.py"
GATE_BP = HERE / "audit_calibrated.py"
CANON = [ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
         ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
         ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _json_body(text: str) -> dict:
    i = text.find("{")
    if i < 0:
        return {}
    try:
        return json.loads(text[i:])
    except json.JSONDecodeError:
        return {}


def stage_a(path: Path) -> dict:
    p = subprocess.run([sys.executable, str(GATE_A), "--json", str(path)],
                       capture_output=True, text=True, timeout=180)
    rep = _json_body(p.stdout)
    caught = p.returncode != 0 or rep.get("verdict") != "pass"
    return {"stage": "A_structural", "exit": p.returncode, "verdict": rep.get("verdict"),
            "failed_rules": rep.get("failed_rules", []), "caught": caught}


def _auditor(tool: Path, path: Path, hardened: bool = False) -> dict:
    args = [sys.executable, str(tool), str(path)] + (["--hardened"] if hardened else [])
    p = subprocess.run(args, capture_output=True, text=True, timeout=180)
    rep = _json_body(p.stdout)
    return {"exit": p.returncode, "verdict": rep.get("verdict"),
            "failed_rules": rep.get("failed_rules", []), "caught": rep.get("verdict") != "accept"}


def stage_b(path: Path, tool: Path = GATE_B, hardened: bool = False, label: str = "B_semantic_frozen") -> dict:
    r = _auditor(tool, path, hardened)
    r["stage"] = label
    return r


def run_all(entries, frozen_canonical=True):
    rows = []
    if frozen_canonical:
        for p in CANON:
            rows.append({"fixture": p.name, "role": "frozen_canonical",
                         "path": str(p.relative_to(ROOT)),
                         "A": stage_a(p), "B": stage_b(p),
                         "Bp": stage_b(p, GATE_BP, label="Bp_semantic_calibrated"),
                         "Bh": stage_b(p, GATE_B, hardened=True, label="Bh_semantic_hardened")})
    for e in entries:
        p = ROOT / e["path"]
        rows.append({"fixture": e["fixture"], "role": e["role"], "family": e["family"],
                     "rephrased": e["rephrased"], "path": e["path"],
                     "invariant_violated": e["invariant_violated"],
                     "falsifier": e["falsifier"],
                     "expected_rule_if_caught": e["expected_rule_if_caught"],
                     "A": stage_a(p), "B": stage_b(p),
                     "Bp": stage_b(p, GATE_BP, label="Bp_semantic_calibrated"),
                     "Bh": stage_b(p, GATE_B, hardened=True, label="Bh_semantic_hardened")})
    return rows


FAMILY_REASONS = {
    "wcc-content-in-scc": "WCC-family meaning (observability/information at I+) is carried by prose in an SCC schema; R12 scans only literal foreign tokens and R31 only regularity tokens, so a paraphrase escapes both.",
    "scc-content-in-wcc": "SCC-family meaning (non-continuability of the development) is carried by prose in the WCC schema; the foreign-token list has no semantic paraphrase rule.",
    "iplus-completeness-in-scc": "I+ completeness is asserted in an SCC schema through a paraphrase (or an extensions leaf); the negation-aware rule protects the canonical literal wording only.",
    "curvature-hypothesis-in-c0": "A curvature/regularity hypothesis is admitted in a C0 class with wording outside the R29 token list ('Riemann tensor', 'locally bounded').",
    "genericity-transfer-truth-table": "The truth-table-forbidden full_measure -> residual_comeager transfer is asserted in a note inside transfer_failures; R28 checks only structured row direction fields.",
    "converse-entailment": "The forbidden converse entailment is asserted in paraphrase with no literal C0/C2/continuity token; the R16 prose regex is literal.",
    "multi-end-slice": "Multiple asymptotically flat ends are admitted in an unscanned topology leaf; R04 inspects only topology.slice_topology.",
    "foreign-regularity-in-c2": "The extension class is weakened below C2 in prose without the R31 token list ('one weak derivative').",
}


def summarize(rows):
    mutants = [r for r in rows if r["role"] == "mutant"]
    n = len(mutants)
    a_esc = sum(1 for r in mutants if not r["A"]["caught"])
    b_esc = sum(1 for r in mutants if not r["B"]["caught"])
    bp_esc = sum(1 for r in mutants if not r["Bp"]["caught"])
    bh_esc = sum(1 for r in mutants if not r["Bh"]["caught"])
    union_esc = sum(1 for r in mutants if not r["A"]["caught"] and not r["Bp"]["caught"])
    union_frozen = sum(1 for r in mutants if not r["A"]["caught"] and not r["B"]["caught"])
    fams = {}
    for r in mutants:
        if not r["A"]["caught"] and not r["Bp"]["caught"]:
            fams.setdefault(r["family"], []).append(r["fixture"])
    return {
        "mutants": n,
        "families": len({r["family"] for r in mutants}),
        "rephrased": sum(1 for r in mutants if r["rephrased"]),
        "structural_escape_rate": round(a_esc / max(1, n), 4),
        "semantic_escape_rate": round(bp_esc / max(1, n), 4),
        "union_escape_rate": round(union_esc / max(1, n), 4),
        "union_escape_rate_frozen_auditor": round(union_frozen / max(1, n), 4),
        "hardened_auditor_escape_rate": round(bh_esc / max(1, n), 4),
        "structural_caught": n - a_esc, "semantic_caught": n - bp_esc,
        "union_caught": n - union_esc, "frozen_auditor_caught": n - b_esc,
        "escape_families": [
            {"family": f, "count": len(v), "example_name": v[0],
             "one_sentence_reason": FAMILY_REASONS.get(f, "no rule in either stage inspects this axis")}
            for f, v in sorted(fams.items())],
    }


def write_blindspot(rows):
    out = []
    for r in rows:
        if r["role"] != "mutant":
            continue
        caught = r["A"]["caught"] or r["Bp"]["caught"]
        rule = None
        if r["A"]["caught"]:
            rule = "stage A: " + ",".join(r["A"]["failed_rules"] or ["non-pass"])
        elif r["Bp"]["caught"]:
            rule = "stage B': " + ",".join(r["Bp"]["failed_rules"] or ["reject"])
        out.append({
            "fixture": r["fixture"],
            "family": r["family"],
            "rephrased": r["rephrased"],
            "caught": caught,
            "caught_by": rule,
            "rule_or_blindspot": rule or (
                f"BLIND SPOT - expected catching rule {r['expected_rule_if_caught']} is not implemented; "
                "both stages accept the fixture"),
            "minimal_repro": (f"python3 artifacts/formulation/tools/check_class_schema.py --json {r['path']} "
                              f"&& python3 artifacts/worker-06/probe10/audit_calibrated.py {r['path']} "
                              f"&& python3 artifacts/worker-06/spec_conformance_audit.py {r['path']}"),
            "invariant_violated": r["invariant_violated"],
            "falsifier": r["falsifier"],
        })
    return out


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--preflight"
    manifest = json.loads((HERE / "manifest.json").read_text())
    entries = manifest["mutants"] + manifest["pass_controls"] + manifest["sensitivity_controls"]

    if mode == "--preflight":
        rows = run_all(manifest["pass_controls"] + manifest["sensitivity_controls"],
                       frozen_canonical=False)
        bad = []
        for r in rows:
            if r["role"] == "pass_control":
                ok = not r["A"]["caught"] and not r["Bp"]["caught"]
                print(f"pass_control      {r['fixture']:38} A={r['A']['verdict']:6} "
                      f"B'={r['Bp']['verdict']:7} {'OK' if ok else 'FAIL'}")
                if not ok:
                    bad.append(r["fixture"])
            else:
                ok = r["A"]["caught"]
                print(f"sensitivity_ctl   {r['fixture']:38} A={r['A']['verdict']:6} "
                      f"rules={r['A']['failed_rules']} {'OK(must be caught)' if ok else 'FAIL'}")
                if not ok:
                    bad.append(r["fixture"])
        print("PREFLIGHT", "PASS" if not bad else f"FAIL {bad}")
        return 0 if not bad else 1

    if mode != "--run":
        print(__doc__)
        return 2

    # ---- freeze: manifest hash first, then drift/tamper checks, then verdicts
    manifest_sha = sha(HERE / "manifest.json")
    tampered = [e["fixture"] for e in entries
                if sha(ROOT / e["path"]) != e["sha256"]]
    base_drift = [k for k, v in manifest["bases"].items() if sha(ROOT / v["path"]) != v["sha256"]]
    gate_drift = [k for k, v in manifest["gate_inputs"].items() if sha(ROOT / k) != v["sha256"]]
    if tampered or base_drift or gate_drift:
        print(f"ABORT: tampered={tampered} base_drift={base_drift} gate_drift={gate_drift}")
        return 1

    rows = run_all(entries)

    controls_ok = all(not r["A"]["caught"] and not r["Bp"]["caught"]
                      for r in rows if r["role"] == "pass_control")
    sensitivity_ok = all(r["A"]["caught"] for r in rows if r["role"] == "sensitivity_control")
    frozen_canon_rows = [r for r in rows if r["role"] == "frozen_canonical"]

    summary = summarize(rows)
    report = {
        "corpus_id": manifest["corpus_id"],
        "generated_at": now(),
        "manifest_sha256_before_run": manifest_sha,
        "frozen_revision": manifest["frozen_revision"],
        "bases": manifest["bases"],
        "gate_inputs": manifest["gate_inputs"],
        "stages": {
            "A_structural": {"tool": str(GATE_A.relative_to(ROOT)), "sha256": sha(GATE_A)},
            "B_semantic_frozen": {"tool": str(GATE_B.relative_to(ROOT)), "sha256": sha(GATE_B)},
            "Bp_semantic_calibrated": {"tool": str(GATE_BP.relative_to(ROOT)), "sha256": sha(GATE_BP)},
            "Bh_semantic_hardened": {"tool": str(GATE_B.relative_to(ROOT)), "sha256": sha(GATE_B),
                                     "note": "same frozen tool with --hardened"},
        },
        "valid": bool(controls_ok and sensitivity_ok),
        "invalid_reasons": (
            ([] if controls_ok else ["a pass_control was rejected by a stage"]) +
            ([] if sensitivity_ok else ["a sensitivity_control was accepted by stage A"])),
        "controls": {
            "pass_controls_ok": controls_ok,
            "sensitivity_controls_ok": sensitivity_ok,
            "frozen_canonical": [
                {"schema": r["fixture"], "A": r["A"]["verdict"], "B": r["B"]["verdict"],
                 "Bp": r["Bp"]["verdict"], "Bh": r["Bh"]["verdict"],
                 "B_failed_rules": r["B"]["failed_rules"]} for r in frozen_canon_rows],
        },
        "corpus": {"mutants": summary["mutants"], "families": summary["families"],
                   "rephrased": summary["rephrased"],
                   "pass_controls": len(manifest["pass_controls"]),
                   "sensitivity_controls": len(manifest["sensitivity_controls"])},
        "aggregates": {k: v for k, v in summary.items()
                       if k not in ("mutants", "families", "rephrased", "escape_families")},
        "escape_families": summary["escape_families"],
        "measurement_rule": ("union escape = accepted by BOTH stage A (canonical structural gate) and "
                             "stage B' (calibrated semantic auditor). Stage B' passes all three frozen "
                             "canonical controls; the frozen stage B rejects canonical WCC on a "
                             "documented R03 format false positive and is reported as a secondary rate."),
        "deviation_from_H5": ("FORM-HELDOUT-07 required the three frozen canonical schemas to pass both "
                              "stages with the frozen auditor. At rev28 the frozen auditor rejects "
                              "canonical WCC (R03 literal binder), so stage B' adds one pre-registered, "
                              "generic R03 calibration (see calibrate_audit.py). The frozen-B rate is "
                              "reported next to it; pass_controls for B' are the frozen canonical schemas."),
        "note_out_of_sample": ("R31 was hardened from the earlier worker-06 corpora and the lead's "
                               "rephrased probes. This corpus was authored after those derivations from "
                               "the public blind-spot list, so the rates above are an independent "
                               "out-of-sample estimate for the families probed."),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "raw_verdicts.json").write_text(json.dumps(
        {"manifest_sha256_before_run": manifest_sha, "rows": rows}, indent=2) + "\n")
    blind = write_blindspot(rows)
    (HERE / "blindspot_report.json").write_text(json.dumps(
        {"corpus_id": manifest["corpus_id"], "manifest_sha256_before_run": manifest_sha,
         "fixtures": blind}, indent=2) + "\n")

    a = report["aggregates"]
    print(f"valid={report['valid']} (controls={controls_ok}, sensitivity={sensitivity_ok})")
    print(f"structural escape {a['structural_escape_rate']} | semantic(B') escape {a['semantic_escape_rate']} | "
          f"union escape {a['union_escape_rate']} | union escape (frozen B) {a['union_escape_rate_frozen_auditor']} | "
          f"hardened escape {a['hardened_auditor_escape_rate']}")
    print("escape families:", [(f["family"], f["count"]) for f in report["escape_families"]])
    print("blind spots:", sum(1 for b in blind if not b["caught"]), "/", len(blind))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
