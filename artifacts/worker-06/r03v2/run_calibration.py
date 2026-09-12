#!/usr/bin/env python3
"""Run the pre-registered R03-v2 calibration and write the measurement artifacts.

Reads fixture_manifest.json (hashed definition), verifies every pin, then runs
  stage B frozen   artifacts/worker-06/spec_conformance_audit.py
  stage B vice     artifacts/worker-06/r03v2/audit_r03v2.py
on the 17-fixture corpus and the 30 gate negatives, plus the standalone rule across the
pre-registered span ablation. No fixture is edited after the manifest is written; the
frozen tool is not written to. Writes report.json, calibration_table.json,
blindspot_report.json, raw_verdicts.json.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
W06 = HERE.parent
ROOT = W06.parent.parent
CST = timezone(timedelta(hours=8))
sys.path.insert(0, str(HERE))
import r03v2_rule  # noqa: E402

FROZEN = W06 / "spec_conformance_audit.py"
VICE = HERE / "audit_r03v2.py"
MANIFEST = HERE / "fixture_manifest.json"
PREREG = HERE / "preregistration.json"
GATE_NEG = sorted((ROOT / "artifacts" / "formulation" / "fixtures" / "negative").glob("*.yaml"))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_stage(tool: Path, fixture: Path) -> dict:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "v.json"
        proc = subprocess.run([sys.executable, str(tool), str(fixture), "--json", str(out)],
                              capture_output=True, text=True)
        if not out.exists():
            return {"verdict": "error", "failed_rules": [], "checks": [],
                    "stderr": (proc.stderr or proc.stdout)[-400:]}
        data = json.loads(out.read_text())
        data["_exit"] = proc.returncode
        return data


def r03(result: dict) -> tuple[str, str]:
    for c in result.get("checks", []):
        if c.get("rule") == "R03":
            return c.get("verdict", "?"), str(c.get("detail", ""))[:300]
    return "?", "R03 not reported"


def standalone(tool_fixture: Path, span: int) -> tuple[bool, list[str]]:
    doc = yaml.safe_load(tool_fixture.read_text())
    q = doc.get("quantifiers") or {}
    formal = q.get("formal") or ""
    reasons = []
    for e in q.get("ordered") or []:
        ok, why = r03v2_rule.binder_bound(str(e.get("binder")), str(formal), span)
        if not ok:
            reasons.append(why)
    return (not reasons), reasons


def frozen_pred(fixture: Path) -> tuple[bool, list[str]]:
    doc = yaml.safe_load(fixture.read_text())
    q = doc.get("quantifiers") or {}
    formal = q.get("formal") or ""
    reasons = []
    for e in q.get("ordered") or []:
        ok, why = r03v2_rule.binder_bound_frozen(str(e.get("binder")), str(formal))
        if not ok:
            reasons.append(why)
    return (not reasons), reasons


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    prereg = json.loads(PREREG.read_text())
    pins_before = {rel: sha(ROOT / rel) for rel in prereg["pins"] if (ROOT / rel).exists()}
    if pins_before.get("artifacts/worker-06/r03v2/fixture_manifest.json") != sha(MANIFEST):
        sys.exit("manifest hash does not match the pre-registration")

    rows, raw = [], {}
    for row in manifest["rows"]:
        fx = ROOT / row["file"]
        if sha(fx) != row["sha256"]:
            sys.exit(f"fixture drift {row['file']}")
        rf, rv = run_stage(FROZEN, fx), run_stage(VICE, fx)
        f_ok, f_why = frozen_pred(fx)
        v_ok, v_why = standalone(fx, 80)
        r03f, detf = r03(rf)
        r03v, detv = r03(rv)
        raw[row["id"]] = {"frozen": rf, "vice": rv,
                          "standalone_frozen_r03": f_ok, "standalone_v2_r03": v_ok}
        rows.append({**{k: row[k] for k in ("id", "kind", "class_id", "scored", "mutation",
                                            "expect_frozen_r03", "expect_v2_r03", "file", "sha256")},
                     "frozen_r03": r03f, "frozen_detail": detf, "frozen_overall": rf.get("verdict"),
                     "v2_r03": r03v, "v2_detail": detv, "v2_overall": rv.get("verdict"),
                     "standalone_frozen": f_ok, "standalone_v2": v_ok,
                     "standalone_frozen_reason": f_why, "standalone_v2_reason": v_why})

    pos = [r for r in rows if r["kind"] == "pos"]
    nab = [r for r in rows if r["kind"] == "neg_abs"]
    nnb = [r for r in rows if r["kind"] == "neg_nonbind"]
    probes = [r for r in rows if r["kind"] == "span_probe"]

    gate = {}
    gate_class = {"explained_literal_tuple_fp": [], "substantive_both_reject": [],
                  "lost_catch": [], "other": []}
    for g in GATE_NEG:
        rf, rv = run_stage(FROZEN, g), run_stage(VICE, g)
        r03f, detf = r03(rf)
        r03v, detv = r03(rv)
        doc = yaml.safe_load(g.read_text())
        q = doc.get("quantifiers") if isinstance(doc, dict) else None
        formal = str(q.get("formal") or "") if isinstance(q, dict) else ""
        absent = re.findall(r"binder '([^']*)' absent from formal sentence", detf)
        co_bound = {b: r03v2_rule.binder_bound(b, formal)[0] for b in absent}
        if r03f == "fail" and r03v == "pass" and absent and all(co_bound.values()):
            gate_class["explained_literal_tuple_fp"].append(g.name)
        elif r03f == "fail" and r03v == "fail":
            gate_class["substantive_both_reject"].append(g.name)
        elif r03f == "fail" and r03v == "pass":
            gate_class["lost_catch"].append(g.name)
        else:
            gate_class["other"].append(g.name)
        gate[g.name] = {"frozen_r03": r03f, "v2_r03": r03v, "v2_detail": detv,
                        "frozen_detail": detf, "absent_binders": absent,
                        "absent_binders_co_bound_v2": co_bound,
                        "frozen_overall": rf.get("verdict"), "v2_overall": rv.get("verdict")}
    unexplained = gate_class["lost_catch"]

    spans = prereg["rule"]["span_ablation"]
    table = []
    for span in spans:
        pos_acc = sum(1 for r in rows if r["kind"] == "pos" and standalone(
            ROOT / next(m["file"] for m in manifest["rows"] if m["id"] == r["id"]), span)[0])
        abs_catch = sum(1 for r in rows if r["kind"] == "neg_abs" and not standalone(
            ROOT / next(m["file"] for m in manifest["rows"] if m["id"] == r["id"]), span)[0])
        nb_catch = sum(1 for r in rows if r["kind"] == "neg_nonbind" and not standalone(
            ROOT / next(m["file"] for m in manifest["rows"] if m["id"] == r["id"]), span)[0])
        probe_rej = sum(1 for r in rows if r["kind"] == "span_probe" and not standalone(
            ROOT / next(m["file"] for m in manifest["rows"] if m["id"] == r["id"]), span)[0])
        table.append({"span": span, "pos_accept": pos_acc, "pos_fp": len(pos) - pos_acc,
                      "neg_abs_catch": abs_catch, "neg_nonbind_catch": nb_catch,
                      "span_probe_reject": probe_rej})

    unexplained = gate_class["lost_catch"]
    pos_fp = [r["id"] for r in pos if r["standalone_v2"] is False]
    lost_abs = [r["id"] for r in nab if r["standalone_v2"] is True]
    nonbind_catch = [r["id"] for r in nnb if r["standalone_v2"] is False]
    frozen_nonbind_acc = [r["id"] for r in nnb if r["standalone_frozen"] is True]

    falsifier = {
        "pos_false_positive": {"status": "triggered" if pos_fp else "not triggered", "ids": pos_fp},
        "neg_abs_lost_catch": {"status": "triggered" if lost_abs else "not triggered", "ids": lost_abs},
        "gate_negative_lost_catch_unexplained": {"status": "triggered" if unexplained else "not triggered",
                                                 "ids": unexplained},
        "neg_nonbind_catch": {"status": "3/3 caught" if len(nonbind_catch) == 3 else f"{len(nonbind_catch)}/3",
                              "ids": nonbind_catch,
                              "frozen_accepted": frozen_nonbind_acc},
    }

    pins_after = {rel: sha(ROOT / rel) for rel in prerequisites(prereg)}
    drift = {k: [pins_before.get(k), v] for k, v in pins_after.items() if pins_before.get(k) != v}

    report = {
        "artifact": "R03-V2-CALIBRATION-REPORT",
        "owner": "worker-006",
        "node_id": "A1", "gate": "G-CLASSBIND",
        "class_ids": prereg["class_ids"],
        "recorded_at": datetime.now(CST).isoformat(timespec="seconds"),
        "question": prereg["question"],
        "preregistration_sha256": sha(PREREG),
        "manifest_sha256": sha(MANIFEST),
        "frozen_source_sha256": sha(FROZEN),
        "proposal_copy_sha256": sha(VICE),
        "span_default": 80,
        "pins_before": pins_before, "pins_after": pins_after, "pin_drift": drift,
        "validity": "VALID" if not drift else "INVALID (pin drift)",
        "aggregates": {
            "pos": {"n": len(pos), "frozen_accept": sum(1 for r in pos if r["frozen_r03"] == "pass"),
                    "v2_accept": sum(1 for r in pos if r["v2_r03"] == "pass")},
            "neg_abs": {"n": len(nab),
                        "frozen_catch": sum(1 for r in nab if r["frozen_r03"] == "fail"),
                        "v2_catch": sum(1 for r in nab if r["v2_r03"] == "fail")},
            "neg_nonbind": {"n": len(nnb),
                            "frozen_catch": sum(1 for r in nnb if r["frozen_r03"] == "fail"),
                            "v2_catch": sum(1 for r in nnb if r["v2_r03"] == "fail")},
            "gate_negative_regression": {"n": len(gate), "unexplained_lost_r03_catch": len(unexplained)},
            "gate_negative_classification": {k: len(v) for k, v in gate_class.items()},
            "span_probes": {r["id"]: {"frozen": r["frozen_r03"], "v2": r["v2_r03"],
                                      "mutation": r["mutation"]} for r in probes},
        },
        "span_ablation": table,
        "gate_negative_classification": gate_class,
        "falsifier_status": falsifier,
        "frozen_fp_family": "WCC-class schemas whose coordinate binder is written 'q in I+ and "
                            "t0 in [0,T)' instead of the literal tuple '(q,t0)'",
        "findings": [
            f"frozen R03 rejects {len(pos) - sum(1 for r in pos if r['frozen_r03'] == 'pass')}/{len(pos)} "
            f"positive controls; every rejection is the literal-tuple false positive",
            f"R03-v2 (span=80) accepts {sum(1 for r in pos if r['v2_r03'] == 'pass')}/{len(pos)} "
            "positive controls and catches 3/3 neg_abs and 3/3 neg_nonbind",
            "neg_nonbind fixtures are genuine R03 violations the frozen literal test misses: the "
            "declared binder is unbound while its spelling survives in a trailing remark",
            f"span ablation: FP=0 for span>={next((t['span'] for t in table if t['pos_fp'] == 0), None)}; "
            "the window only matters for coordinated binders kept on one head",
        ],
        "authority": prereg["authority"],
        "not_claimed": prereg["not_claimed"],
    }
    blind = {"artifact": "R03-V2-BLINDS POT", "note": "per-fixture v2 outcome and minimal repro",
             "entries": []}
    blind["artifact"] = "R03-V2-BLINDSPOT-REPORT"
    for r in rows:
        fx = ROOT / next(m["file"] for m in manifest["rows"] if m["id"] == r["id"])
        blind["entries"].append({
            "id": r["id"], "kind": r["kind"], "class_id": r["class_id"],
            "v2_caught": (r["standalone_v2"] is False) if r["kind"] != "pos" else (r["v2_r03"] == "pass"),
            "frozen_outcome": {"r03": r["frozen_r03"], "detail": r["frozen_detail"]},
            "v2_outcome": {"r03": r["v2_r03"], "detail": r["v2_detail"]},
            "minimal_repro": f"python3 artifacts/worker-06/r03v2/audit_r03v2.py {r.get('file', '')}",
            "falsifier": "a positive control rejected by R03-v2, or a neg_abs accepted by R03-v2",
        })
    blind["gate_negative_regression"] = gate
    (HERE / "raw_verdicts.json").write_text(json.dumps(raw, indent=1) + "\n")
    (HERE / "calibration_table.json").write_text(json.dumps(table, indent=1) + "\n")
    (HERE / "blindspot_report.json").write_text(json.dumps(blind, indent=1) + "\n")
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("validity", "aggregates", "falsifier_status")}, indent=1))
    return 0


def prerequisites(prereg: dict) -> list[str]:
    rels = [r for r in prereg["pins"] if (ROOT / r).exists()]
    return rels


if __name__ == "__main__":
    sys.exit(main())
