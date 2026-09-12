#!/usr/bin/env python3
"""Fail-closed runner for W006-R03-CAND-HEADTOHEAD-01.

Runs the frozen auditor and both published R03 repair candidates over the pre-registered
corpus, enforces the pre-registered validity gates, and writes raw verdicts plus the
aggregate report. Measurement only: no gate verdict, no node completion, no theorem.
Exit: 0 measurement VALID, 3 measurement INVALID (details in report.json), 2 usage/pin error.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))
SPEC = "artifacts/formulation/rule_spec.json"

VARIANT_FILES = {
    "frozen": "artifacts/worker-06/spec_conformance_audit.py",
    "cand_r03v2": "artifacts/worker-06/r03v2/audit_r03v2.py",
    "cand_004": "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py",
}


def sha(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def measure_pins(pins: dict) -> dict:
    return {rel: sha(ROOT / rel) for rel in pins}


def run_variant(variant: str, target: Path, out_json: Path):
    cmd = [sys.executable, str(ROOT / VARIANT_FILES[variant]), str(target),
           "--spec", str(ROOT / SPEC), "--json", str(out_json)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    rec = {"cmd": " ".join(cmd), "returncode": proc.returncode}
    if out_json.exists():
        rep = json.loads(out_json.read_text())
        rec["verdict"] = rep.get("verdict")
        rec["failed_rules"] = rep.get("failed_rules")
        rec["failed_detail"] = {c["rule"]: c["detail"] for c in rep.get("checks", [])
                                if c.get("verdict") == "fail"}
        rec["undecided_rules"] = rep.get("undecided_rules")
        rec["doc_sha256"] = rep.get("doc_sha256")
    else:
        rec["verdict"] = "error"
        rec["stderr"] = proc.stderr[-500:]
    return rec


def main() -> int:
    prereg = json.loads((HERE / "preregistration.json").read_text())
    manifest = json.loads((HERE / "fixture_manifest.json").read_text())
    pins = prereg["pins"]
    errors: list[str] = []

    pre = measure_pins(pins)
    for rel, want in pins.items():
        if pre[rel] != want:
            errors.append(f"PIN DRIFT pre-run: {rel} {pre[rel][:12]} != {want[:12]}")
    if sha(HERE / "fixture_manifest.json") != prereg["corpus"]["manifest_sha256"]:
        errors.append("CORPUS MANIFEST DRIFT: fixture_manifest.json no longer matches preregistration")
    for m in manifest["fixtures"]:
        p = HERE / "fixtures" / m["fixture"]
        if not p.exists() or sha(p) != m["sha256"]:
            errors.append(f"FIXTURE DRIFT: {m['fixture']}")

    if errors:
        print(json.dumps({"measurement": "INVALID_PRE", "errors": errors}, indent=1))
        return 2

    RAW.mkdir(parents=True, exist_ok=True)
    fixtures = manifest["fixtures"]
    negatives = sorted((ROOT / "artifacts/formulation/fixtures/negative").glob("*.yaml"))

    results = {}          # variant -> {fixture_name: record}
    neg_results = {}      # variant -> {neg_name: record}
    for variant in VARIANT_FILES:
        results[variant] = {}
        for m in fixtures:
            target = HERE / "fixtures" / m["fixture"]
            out = RAW / f"{variant}__{m['fixture']}.json"
            results[variant][m["fixture"]] = run_variant(variant, target, out)
        neg_results[variant] = {}
        for np_ in negatives:
            out = RAW / f"{variant}__neg__{np_.name}.json"
            neg_results[variant][np_.name] = run_variant(variant, np_, out)

    post = measure_pins(pins)
    for rel, want in pins.items():
        if post[rel] != want:
            errors.append(f"PIN DRIFT post-run: {rel} {post[rel][:12]} != {want[:12]}")
    for m in fixtures:
        p = HERE / "fixtures" / m["fixture"]
        if not p.exists() or sha(p) != m["sha256"]:
            errors.append(f"FIXTURE DRIFT post-run: {m['fixture']}")

    # ---- validity gate V2: every fixture is otherwise-valid (non-R03 clean) --------
    for m in fixtures:
        for variant, rec in results.items():
            extra = [r for r in (rec[m["fixture"]]["failed_rules"] or []) if r != "R03"]
            if extra:
                errors.append(f"V2 FORMAT-DOMINATED: {m['fixture']} fails {extra} under {variant}")

    # ---- validity gate V3: non-R03 rule sets identical across variants ------------
    def non_r03(rec):
        return sorted(r for r in (rec["failed_rules"] or []) if r != "R03")

    all_targets = [(m["fixture"], results) for m in fixtures]
    for name, res in all_targets:
        base = non_r03(res["frozen"][name])
        for variant in ("cand_r03v2", "cand_004"):
            if non_r03(res[variant][name]) != base:
                errors.append(f"V3 INSTRUMENTATION: non-R03 rules differ for {name} under {variant}")
    for np_ in negatives:
        name = np_.name
        base = non_r03(neg_results["frozen"][name])
        for variant in ("cand_r03v2", "cand_004"):
            if non_r03(neg_results[variant][name]) != base:
                errors.append(f"V3 INSTRUMENTATION (negative): non-R03 rules differ for {name} under {variant}")

    # ---- validity gate V1: frozen reproduces known control behaviour ---------------
    ctl = results["frozen"]
    if ctl["pos00_canonical_c0.yaml"]["verdict"] != "accept":
        errors.append("V1 frozen does not accept canonical C0 control")
    if ctl["pos01_canonical_c2.yaml"]["verdict"] != "accept":
        errors.append("V1 frozen does not accept canonical C2 control")
    if ctl["pos02_canonical_wcc.yaml"]["verdict"] != "reject" or "R03" not in (ctl["pos02_canonical_wcc.yaml"]["failed_rules"] or []):
        errors.append("V1 frozen does not reproduce the known WCC R03 false positive")

    # ---- metrics -------------------------------------------------------------------
    def metrics(variant):
        res = results[variant]
        fp = [m["fixture"] for m in fixtures
              if m["scored"] and m["category"] == "pos" and res[m["fixture"]]["verdict"] != "accept"]
        fn = [m["fixture"] for m in fixtures
              if m["scored"] and m["category"] == "neg" and res[m["fixture"]]["verdict"] == "accept"]
        edge_fp = [m["fixture"] for m in fixtures if not m["scored"] and res[m["fixture"]]["verdict"] != "accept"]
        canon = sum(1 for m in fixtures if m["category"] == "pos" and res[m["fixture"]]["verdict"] == "accept")
        n_canon = sum(1 for m in fixtures if m["category"] == "pos")
        # gate negatives
        lost, reproduced, still_rejected = [], [], []
        for np_ in negatives:
            f = neg_results["frozen"][np_.name]
            c = neg_results[variant][np_.name]
            f_r03 = "R03" in (f["failed_rules"] or [])
            c_r03 = "R03" in (c["failed_rules"] or [])
            if f_r03 and not c_r03:
                entry = {"negative": np_.name, "frozen_detail": f["failed_detail"].get("R03", ""),
                         "candidate_verdict": c["verdict"],
                         "candidate_failed_rules": c["failed_rules"]}
                lost.append(entry)
                if c["verdict"] == "reject":
                    still_rejected.append(np_.name)
            elif f_r03 and c_r03:
                reproduced.append(np_.name)
        return {
            "primary_fp": fp, "primary_fp_count": len(fp),
            "primary_fn": fn, "primary_fn_count": len(fn),
            "edge_fp": edge_fp, "edge_fp_count": len(edge_fp),
            "canonical_pos_accept": f"{canon}/{n_canon}",
            "gate_negative_frozen_r03_reproduced": len(reproduced),
            "gate_negative_frozen_r03_now_pass": lost,
            "gate_negative_now_pass_count": len(lost),
            "gate_negative_now_pass_but_rejected_by_other_rules": still_rejected,
            "gate_negative_now_pass_overall_accept": [e["negative"] for e in lost
                                                      if e["candidate_verdict"] == "accept"],
        }

    per_candidate = {v: metrics(v) for v in VARIANT_FILES}

    matrix = []
    for m in fixtures:
        row = {"fixture": m["fixture"], "category": m["category"], "scored": m["scored"],
               "expected": m["expected"], "mutation": m["mutation"]}
        for v in VARIANT_FILES:
            r = results[v][m["fixture"]]
            row[v] = {"verdict": r["verdict"], "failed_rules": r["failed_rules"],
                      "r03_detail": (r["failed_detail"] or {}).get("R03", "")}
        matrix.append(row)

    blindspot = []
    for m in fixtures:
        for v in ("cand_r03v2", "cand_004"):
            r = results[v][m["fixture"]]
            dev = (m["expected"] == "accept" and r["verdict"] != "accept") or \
                  (m["expected"] == "reject" and r["verdict"] == "accept")
            blindspot.append({
                "fixture": m["fixture"], "candidate": v, "category": m["category"],
                "expected": m["expected"], "verdict": r["verdict"], "deviation": bool(dev),
                "rule_or_blindspot": (r["failed_detail"] or {}).get("R03", "none"),
                "minimal_repro": f"{VARIANT_FILES[v]} fixtures/{m['fixture']} --spec {SPEC}",
                "rationale": m["rationale"],
            })

    valid = not errors
    report = {
        "task_id": prereg["task_id"], "measured_at": now(), "measurement": "VALID" if valid else "INVALID",
        "errors": errors,
        "pins_pre": pre, "pins_post": post,
        "variant_hashes": {v: sha(ROOT / p) for v, p in VARIANT_FILES.items()},
        "preregistration_sha256": sha(HERE / "preregistration.json"),
        "corpus": {"n_fixtures": len(fixtures), "n_gate_negatives": len(negatives),
                   "manifest_sha256": sha(HERE / "fixture_manifest.json")},
        "per_candidate": per_candidate,
        "adoption_rule_measured_not_wielded": prereg["scoring"]["adoption_rule_measured_not_wielded"],
        "matrix": matrix,
        "hypothesis": prereg["hypothesis"],
        "falsifier": prereg["falsifier"],
        "not_claimed": prereg["not_claimed"],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (HERE / "raw_verdicts.json").write_text(json.dumps(
        {"fixtures": {v: results[v] for v in results},
         "gate_negatives": {v: neg_results[v] for v in neg_results}}, indent=1) + "\n")
    (HERE / "blindspot_report.json").write_text(json.dumps(
        {"task_id": prereg["task_id"], "entries": blindspot}, indent=1) + "\n")
    print(json.dumps({"measurement": report["measurement"], "errors": errors,
                      "per_candidate": per_candidate}, indent=1))
    return 0 if valid else 3


if __name__ == "__main__":
    sys.exit(main())
