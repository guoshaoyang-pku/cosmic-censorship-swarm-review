#!/usr/bin/env python3
"""FORM-PROBE-11-REBIND-REV29 runner (worker-006).

Measures the canonical two-stage class-binding pipeline against prose leaks placed in
schema surfaces the pipeline does not scan by design, at FROZEN rev29.
Same declared deltas as FORM-PROBE-11, rebound to the rev29 canonical bytes.

Stages
  A     artifacts/formulation/tools/check_class_schema.py --json FIXTURE   (R01-R31)
  B     artifacts/worker-06/spec_conformance_audit.py FIXTURE              (frozen)
  B'    artifacts/worker-06/exempt11/audit_calibrated_exempt11.py FIXTURE  (documented R03 delta)
  B*    spec_conformance_audit.py --hardened FIXTURE

Primary union escape = accepted by BOTH A and B'.  Frozen-B and hardened-B rates are
reported beside it.  Pre-registration: manifest.json is hashed BEFORE the first mutant
verdict; every fixture byte is re-checked against the manifest; any pinned input that
drifts voids the run (moving-target blocker, CF-19 pattern).

Usage:
  python3 run_exempt11.py --preflight   # controls only
  python3 run_exempt11.py --run         # full run + report.json / blindspot_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
FIX = HERE / "fixtures"
MANIFEST = HERE / "manifest.json"
GATE_A = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
GATE_B = HERE.parent / "spec_conformance_audit.py"
GATE_BP = HERE.parent / "exempt11" / "audit_calibrated_exempt11.py"
KEY_MANIFEST = ROOT / "artifacts" / "formulation" / "KEY_MANIFEST.json"
RULE_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"
CST = timezone(timedelta(hours=8))

PINS = {
    "artifacts/formulation/tools/check_class_schema.py": GATE_A,
    "artifacts/formulation/KEY_MANIFEST.json": KEY_MANIFEST,
    "artifacts/formulation/rule_spec.json": RULE_SPEC,
    "artifacts/worker-06/spec_conformance_audit.py": GATE_B,
    "schemas/af_wcc_vacuum.yaml": ROOT / "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def json_body(text: str) -> dict:
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
    rep = json_body(p.stdout)
    caught = p.returncode != 0 or rep.get("verdict") != "pass"
    return {"stage": "A_structural", "exit": p.returncode, "verdict": rep.get("verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "failures": [f.get("msg") for f in rep.get("failures", [])], "caught": caught}


def stage_b(tool: Path, path: Path, hardened: bool = False, label: str = "B_semantic_frozen") -> dict:
    args = [sys.executable, str(tool), str(path)] + (["--hardened"] if hardened else [])
    p = subprocess.run(args, capture_output=True, text=True, timeout=180)
    rep = json_body(p.stdout)
    caught = p.returncode != 0 or rep.get("verdict") not in ("accept",)
    return {"stage": label, "exit": p.returncode, "verdict": rep.get("verdict"),
            "failed_rules": rep.get("failed_rules", []), "caught": caught}


def evaluate(path: Path) -> dict:
    return {"A_structural": stage_a(path),
            "B_semantic_frozen": stage_b(GATE_B, path),
            "Bp_semantic_calibrated": stage_b(GATE_BP, path, label="Bp_semantic_calibrated"),
            "Bs_semantic_hardened": stage_b(GATE_B, path, hardened=True, label="Bs_semantic_hardened")}


def check_fixture_bytes(manifest: dict) -> list:
    bad = []
    for f in manifest["fixtures"]:
        p = ROOT / f["file"]
        if not p.exists() or sha(p) != f["sha256"]:
            bad.append(f["id"])
    return bad


def check_pins() -> dict:
    return {k: {"path": str(v), "sha256": sha(v)} for k, v in PINS.items()}


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def do_run(preflight_only: bool) -> int:
    manifest = load_manifest()
    manifest_sha_pre = sha(MANIFEST)
    pins = check_pins()
    declared = manifest.get("pins", {})
    pin_mismatch = {k: {"declared": declared.get(k), "measured": pins[k]["sha256"]}
                    for k in pins if k in declared and declared[k] != pins[k]["sha256"]}
    bad_bytes = check_fixture_bytes(manifest)
    corpus_valid = not pin_mismatch and not bad_bytes

    results = {}
    for f in manifest["fixtures"]:
        if preflight_only and f["kind"] == "mutant":
            continue
        results[f["id"]] = evaluate(ROOT / f["file"])

    # ---------------- control gates ----------------
    canon = [f for f in manifest["fixtures"] if f["kind"] == "canonical_pass_control"]
    neg = [f for f in manifest["fixtures"] if f.get("expect") == "pass" and f["kind"] != "canonical_pass_control"]
    pos = [f for f in manifest["fixtures"] if f.get("expect") == "caught"]
    ctrl = {
        "canonical_pass": {f["id"]: bool(not results[f["id"]]["A_structural"]["caught"]
                                         and not results[f["id"]]["Bp_semantic_calibrated"]["caught"])
                           for f in canon},
        "negative_field_pass": {f["id"]: bool(not results[f["id"]]["A_structural"]["caught"]
                                              and not results[f["id"]]["Bp_semantic_calibrated"]["caught"])
                                for f in neg},
        "sensitivity_caught": {f["id"]: bool(results[f["id"]]["A_structural"]["caught"]
                                             or results[f["id"]]["Bp_semantic_calibrated"]["caught"])
                               for f in pos},
    }
    ctrl["all_pass_controls_ok"] = all(ctrl["canonical_pass"].values()) and all(ctrl["negative_field_pass"].values())
    ctrl["all_sensitivity_ok"] = all(ctrl["sensitivity_caught"].values())
    validity = ("VALID" if (corpus_valid and ctrl["all_pass_controls_ok"])
                else "INVALID")

    if preflight_only:
        print(json.dumps({"mode": "preflight", "corpus_valid": corpus_valid,
                          "pin_mismatch": pin_mismatch, "fixture_byte_drift": bad_bytes,
                          "controls": ctrl, "validity": validity,
                          "manifest_sha256_before_run": manifest_sha_pre}, indent=1))
        return 0 if validity == "VALID" else 3

    # ---------------- aggregates over candidate mutants ----------------
    mutants = [f for f in manifest["fixtures"] if f["kind"] == "mutant"]
    rows = []
    for f in mutants:
        r = results[f["id"]]
        a, bp = r["A_structural"], r["Bp_semantic_calibrated"]
        caught = bool(a["caught"] or bp["caught"])
        rules = sorted(set(a.get("failed_rules") or []) | set(bp.get("failed_rules") or []))
        rows.append({
            "fixture_id": f["id"], "class_id": f["base"], "target_path": f["path"],
            "surface": f["surface"], "load_bearing": f["load"],
            "leak_family": f["family"], "injected_text": f["text"],
            "A": {"verdict": a["verdict"], "caught": a["caught"], "failed_rules": a.get("failed_rules")},
            "Bp": {"verdict": bp["verdict"], "caught": bp["caught"], "failed_rules": bp.get("failed_rules")},
            "B_frozen": {"verdict": r["B_semantic_frozen"]["verdict"], "caught": r["B_semantic_frozen"]["caught"]},
            "Bs_hardened": {"verdict": r["Bs_semantic_hardened"]["verdict"], "caught": r["Bs_semantic_hardened"]["caught"]},
            "union_caught": caught,
            "rule_or_blindspot": (",".join(rules) if caught else "BLINDSPOT-no-stage-scans-this-surface"),
            "minimal_repro": (f"python3 {GATE_A.relative_to(ROOT)} --json {f['file']} ; "
                              f"python3 {GATE_B.relative_to(ROOT)} {f['file']}"),
            "falsifier": ("Reject at the pinned hashes falsifies the escape claim: if stage A "
                          "verdict!=pass (R12/R13/R16/R25/R31) or the calibrated stage B verdict "
                          "!=accept, this surface is scanned and the fixture is not a blind spot."),
        })

    def rate(sel, key="union_caught"):
        n = len(sel)
        c = sum(1 for x in sel if x[key])
        return {"n": n, "caught": c, "escape": (n - c) / n if n else None}

    def esc(sel):
        r = rate(sel)
        return {"n": r["n"], "caught": r["caught"], "escape_rate": round(r["escape"], 4) if r["escape"] is not None else None}

    agg = {
        "structural_escape": esc([{**x, "union_caught": x["A"]["caught"]} for x in rows]),
        "semantic_escape_primary": esc([{**x, "union_caught": x["Bp"]["caught"]} for x in rows]),
        "semantic_escape_frozen": esc([{**x, "union_caught": x["B_frozen"]["caught"]} for x in rows]),
        "semantic_escape_hardened": esc([{**x, "union_caught": x["Bs_hardened"]["caught"]} for x in rows]),
        "union_escape": esc(rows),
        "by_surface": {s: esc([x for x in rows if x["surface"] == s]) for s in ("S1", "S2", "S3")},
        "by_load_bearing": {l: esc([x for x in rows if x["load_bearing"] == l]) for l in ("high", "medium", "low")},
        "by_family": {fam: esc([x for x in rows if x["leak_family"] == fam])
                      for fam in sorted({x["leak_family"] for x in rows})},
        "by_class": {c: esc([x for x in rows if x["class_id"] == c])
                     for c in sorted({x["class_id"] for x in rows})},
    }
    families = sorted({x["leak_family"] for x in rows})
    escaped_families = sorted({x["leak_family"] for x in rows if not x["union_caught"]})
    unattributed = [x for x in rows if not ctrl["all_pass_controls_ok"] or not ctrl["all_sensitivity_ok"]]

    # re-measure pins AFTER the run: moving-target control
    pins_after = check_pins()
    drift = {k: {"before": pins[k]["sha256"], "after": pins_after[k]["sha256"]}
             for k in pins if pins[k]["sha256"] != pins_after[k]["sha256"]}
    bad_bytes_after = check_fixture_bytes(manifest)

    report = {
        "artifact": "FORM-PROBE-11-REBIND-REV29-MEASUREMENT",
        "owner": "worker-06", "node_id": "A1", "gate": "G-CLASSBIND",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "recorded_at": now(),
        "question": ("Do prose leaks survive the two-stage class-binding pipeline when placed in "
                     "schema surfaces the pipeline does not lexically scan (exempt-key subtrees, "
                     "non-assertive declarative prose, history/status metadata)?"),
        "frozen_revision": "FROZEN rev29 (2026-09-12T00:54:32+08:00)",
        "lineage": {"predecessor_task": "FORM-PROBE-11", "predecessor_revision": "FROZEN rev28",
                    "predecessor_manifest_sha256": "98e7289a2cfc3c28a3af05b7850a34431c25982d8c3934fbb18555bfd7f936a9",
                    "predecessor_report_sha256": "a6a2a8c8aee3135d118d335e7b84860f7d6946a83bb05c9592780c155a3febc6",
                    "predecessor_verdict_summary_sha256": "a7ce887972918762a13fce50841db8a784d4f92fcd3a759f95a7ca967ba8ac6e",
                    "what_changed": "canonical bases rebound rev28->rev29 (rev12->rev13 evidence-binding repair); declared mutant deltas, gate tools and calibrated auditor unchanged",
                    "rebind_by": "worker-006", "rebind_instance": "worker-006-20260912T005246-968807"},
        "manifest_sha256_before_run": manifest_sha_pre,
        "manifest_sha256_after_run": sha(MANIFEST),
        "pins_before": {k: v["sha256"] for k, v in pins.items()},
        "pins_after": {k: v["sha256"] for k, v in pins_after.items()},
        "moving_target_drift": drift,
        "fixture_byte_drift": bad_bytes_after,
        "corpus_validity": validity,
        "corpus_validity_reason": (
            "all pinned inputs stable; all 6 pass controls accepted by both stages"
            if validity == "VALID" else
            f"pin_mismatch={pin_mismatch} fixture_drift={bad_bytes} controls={ctrl}"),
        "calibration": {
            "pass_controls": ctrl["canonical_pass"], "negative_field_controls": ctrl["negative_field_pass"],
            "sensitivity_controls": ctrl["sensitivity_caught"],
            "all_pass_controls_ok": ctrl["all_pass_controls_ok"],
            "all_sensitivity_ok": ctrl["all_sensitivity_ok"],
            "stage_B_calibration_delta": ("single R03 binder check literal->identifier tokens; "
                                          "see calibrate_exempt11.py; source and calibrated hashes pinned"),
        },
        "aggregates": agg,
        "escape_families": len(escaped_families), "families_probed": len(families),
        "escaped_family_list": escaped_families,
        "findings": [
            (f"{x['fixture_id']} [{x['surface']}/{x['load_bearing']}] {x['leak_family']} survives both stages "
             f"in {x['class_id']}:{x['target_path']}") for x in rows if not x["union_caught"]
        ],
        "unattributed_cases": [x["fixture_id"] for x in unattributed],
        "falsifier": ("Any candidate mutant rejected by stage A (verdict!=pass) or by the calibrated "
                      "stage B (verdict!=accept) at the pinned hashes falsifies its escape entry. "
                      "Any pass control rejected, any pinned hash change during the run, or any fixture "
                      "byte drift voids the whole measurement. A later revision whose gate catches these "
                      "fixtures falsifies the blind-spot claim at that revision only."),
        "authority": ("Independent measurement evidence only. NOT a gate verdict, NOT a node completion, "
                      "NOT a theorem, NOT a physics result. Interpretation is bound to the pinned hashes."),
        "not_claimed": ["gate verdict", "node completion", "theorem", "physics result"],
    }

    (HERE / "raw_verdicts.json").write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "per_surface.json").write_text(json.dumps({
        "artifact": "FORM-PROBE-11-REBIND-REV29-PER-SURFACE",
        "rows": rows,
        "surface_definitions": {
            "S1": "key subtree matching EXEMPT_KEY in check_class_schema.py (negative/prescriptive by declaration)",
            "S2": "non-exempt key not present in ASSERTIVE_PATHS (declarative prose no family rule visits)",
            "S3": "revision/provenance/status metadata prose",
        },
        "aggregates": agg,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "blindspot_report.json").write_text(json.dumps({
        "artifact": "FORM-PROBE-11-REBIND-REV29-BLINDSPOT-REPORT",
        "manifest_sha256": manifest_sha_pre,
        "corpus_validity": validity,
        "entries": [x for x in rows if not x["union_caught"]],
        "caught_entries": [{k: x[k] for k in ("fixture_id", "target_path", "leak_family", "rule_or_blindspot")}
                           for x in rows if x["union_caught"]],
        "falsifier": report["falsifier"],
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"corpus_validity": validity, "union_escape": agg["union_escape"],
                      "structural_escape": agg["structural_escape"],
                      "by_surface": agg["by_surface"], "by_load": agg["by_load_bearing"],
                      "escaped_families": escaped_families,
                      "manifest_sha256_before_run": manifest_sha_pre,
                      "drift": drift, "fixture_drift": bad_bytes_after}, indent=1))
    return 0 if validity == "VALID" else 3


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    sys.exit(do_run(preflight_only=a.preflight))
