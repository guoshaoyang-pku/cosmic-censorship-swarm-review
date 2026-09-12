#!/usr/bin/env python3
"""W098-CLASSSEP-RESTORE-REPRO-01 -- restore reproduction instrument.

Independent, read-only, deterministic, no-network re-measurement of the worker-098
drift-recheck evidence that research_map.json binds for
astra-life06-classsep-detector-adjudication, run AFTER the CF-29 unauthorized detector
write and the controller's mechanical restore to a8c04fc31e4a.

Three arms:
  RESTORED  live research_map/class_separation.py (must equal the four a8c04fc31e4a pins)
  VOID      the preserved e36b0d644ca evidence copy (never adopted)
  PRE       the recovered c266dbecaa87 pre-change copy

Batteries (verbatim from the pass-2 drift recheck):
  corpus    worker-07 27-row class-separation falsification corpus
  probes    4 declared false-positive, 2 true-positive, 6 adversarial genuine-merge
  growth    3 detector-discussion growth probes
  hard      map hard-finding counts on two frozen snapshots + the live map

The instrument never writes to a canonical path. It writes exactly one file:
raw/restore_repro.json (plus its own directory). Aborts as VOID if the live detector
moves off the pre-registered hash at any point.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PREREG = json.loads((HERE / "pre_registration.json").read_text())
PINS = PREREG["pins"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- pin guards
live_det_path = ROOT / PINS["live_detector"]["path"]
adjudication_path = ROOT / PINS["adjudication"]["path"]
live_map_path = ROOT / PINS["live_map_at_prereg"]["path"]

pin_checks = {}
for key in ("live_detector", "restore_source_pin_worker073", "adjudication_applied_pin_worker032",
            "voided_bytes_evidence", "pre_change_recovered", "adjudication",
            "adjudication_frozen_map_snapshot", "worker098_frozen_map_snapshot",
            "cf29_forensics", "pass2_recorded_raw", "corpus_worker07"):
    pin = PINS[key]
    measured = sha(ROOT / pin["path"])
    pin_checks[key] = {"path": pin["path"], "declared": pin["sha256"], "measured": measured,
                       "match": measured == pin["sha256"]}

forensics = json.loads((ROOT / PINS["cf29_forensics"]["path"]).read_text())
restored_sha = forensics["detector"]["restored_sha256"]
four_way = {
    "live": pin_checks["live_detector"]["measured"],
    "worker073_restore_source": pin_checks["restore_source_pin_worker073"]["measured"],
    "worker032_applied_pin": pin_checks["adjudication_applied_pin_worker032"]["measured"],
    "cf29_forensics_restored_sha256": restored_sha,
}
E1 = len(set(four_way.values())) == 1 and all(v == PINS["live_detector"]["sha256"] for v in four_way.values())
restore_guard_ok = E1 and pin_checks["voided_bytes_evidence"]["match"] and pin_checks["pre_change_recovered"]["match"]

start_live_det = sha(live_det_path)
start_live_map = sha(live_map_path)
start_adjudication = sha(adjudication_path)

if not restore_guard_ok or start_live_det != PINS["live_detector"]["sha256"]:
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "restore_repro.json").write_text(json.dumps({
        "task_id": PREREG["task_id"], "status": "VOID",
        "reason": "restore guard failed: live detector or pins moved before measurement",
        "pin_checks": pin_checks, "four_way_restore": four_way, "E1": E1,
        "start_live_detector": start_live_det,
    }, indent=2, sort_keys=True))
    print("VOID: restore guard failed")
    raise SystemExit(2)

adj = json.loads(adjudication_path.read_text())
live_map = json.loads(live_map_path.read_text())
adj_snap = json.loads((ROOT / PINS["adjudication_frozen_map_snapshot"]["path"]).read_text())
w098_snap = json.loads((ROOT / PINS["worker098_frozen_map_snapshot"]["path"]).read_text())
pass2_raw = json.loads((ROOT / PINS["pass2_recorded_raw"]["path"]).read_text())
corpus = json.loads((ROOT / PINS["corpus_worker07"]["path"]).read_text())

arms = {
    "RESTORED": load_module("w098_rr_restored", live_det_path),
    "VOID": load_module("w098_rr_void", ROOT / PINS["voided_bytes_evidence"]["path"]),
    "PRE": load_module("w098_rr_pre", ROOT / PINS["pre_change_recovered"]["path"]),
}

# ---------------------------------------------------------------- batteries
def run_corpus(mod):
    tp = fp = tn = fn = 0
    for fx in corpus["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            continue
        m = json.loads(p.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        tp += truth and got
        fn += truth and not got
        fp += (not truth) and got
        tn += (not truth) and not got
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE"}


FP_PROBES = [
    "so no C0/C2 merge exists at the formal surface.",
    "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; the two rows require a split)",
    "R1's merge pattern matches only bare C0/C2 composites",
    "This is a class separation check: independent C0/C2 non-merge evidence.",
]
TP_PROBES = [
    "The C0/C2 merged class is the right unit of analysis for this portfolio.",
    "This result covers the C0/C2 unified class.",
]
FN_PROBES = [
    ("FN1_meta_case", "The C0/C2 merged class is the only case we consider."),
    ("FN2_meta_test", "We test that the C0/C2 unified class is the right unit."),
    ("FN3_meta_corpus", "This corpus treats the C0/C2 as one class."),
    ("FN4_meta_independent", "The independent C0/C2 merged class is our unit of analysis."),
    ("FN5_meta_pattern", "The C0/C2 combined pattern is the portfolio's chosen unit."),
    ("FN6_neg_scope", "It is not the case that the classes are separate; the C0/C2 are one class."),
]
GROWTH = [
    ("G1_meta_mention", "The audit flags our discussion of the C0/C2 merged label, but that is a metalinguistic mention, not a proposed merge."),
    ("G2_rejected_hypothesis", "We analysed the C0/C2 unified class only as a rejected hypothesis; the portfolio keeps the two classes split."),
    ("G3_counting_prose", "This note measures how often the C0/C2 combined pattern appears in review prose."),
]


def fires(mod, text):
    out = []
    mod._scan_composite(text, "probe", out, mode="prose")
    return out


def map_hard(mod, m):
    hard = [x for x in mod.findings_for_map(m) if not str(x).startswith("CLASSSEP-SOFT:")]
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            art = n.get("artifact")
            p = ROOT / art if art else None
            if p and p.is_file() and p.stat().st_size < 2_000_000:
                hard += [x for x in mod.findings_for_text(p.read_text(errors="replace"),
                                                          f"{n['id']} artifact {art}")
                         if not str(x).startswith("CLASSSEP-SOFT:")]
    return hard


batteries = {}
for arm, mod in arms.items():
    fp_rows = [{"text": t, "fires": bool(fires(mod, t))} for t in FP_PROBES]
    tp_rows = [{"text": t, "fires": bool(fires(mod, t))} for t in TP_PROBES]
    fn_rows = [{"name": n, "text": t, "fires": bool(fires(mod, t))} for n, t in FN_PROBES]
    growth = [{"name": n, "hard": len([x for x in mod.findings({"statement": t}, n, mode="prose")
                                       if not x.startswith("CLASSSEP-SOFT:")])} for n, t in GROWTH]
    batteries[arm] = {
        "corpus": run_corpus(mod),
        "fp_probes": fp_rows,
        "fp_firing": sum(r["fires"] for r in fp_rows),
        "fp_clean": sum(not r["fires"] for r in fp_rows),
        "tp_probes": tp_rows,
        "tp_firing": sum(r["fires"] for r in tp_rows),
        "fn_probes": fn_rows,
        "over_suppressed": sum(not r["fires"] for r in fn_rows),
        "growth": growth,
        "growth_total": sum(r["hard"] for r in growth),
        "hard_adj_snapshot_f344ed2aaea5": len(map_hard(mod, adj_snap)),
        "hard_w098_snapshot_6d3f0f2792a2": len(map_hard(mod, w098_snap)),
        "hard_live_map_at_start": len(map_hard(mod, live_map)),
    }

R = batteries["RESTORED"]
V = batteries["VOID"]
P = batteries["PRE"]
p2 = pass2_raw["corpus_live"]

expectations = [
    {"id": "E1", "ok": E1, "detail": four_way},
    {"id": "E2", "ok": (start_adjudication == PINS["adjudication"]["sha256"]
                        and adj["decision"]["choice"] == "c"
                        and "NOT lexically separable" in adj["decision"]["text"]
                        and adj["detectors"]["APPLIED"]["cited_match"] is True),
     "detail": {"sha_match": start_adjudication == PINS["adjudication"]["sha256"],
                "choice": adj["decision"]["choice"],
                "not_lexically_separable": "NOT lexically separable" in adj["decision"]["text"],
                "applied_cited_match": adj["detectors"]["APPLIED"]["cited_match"]}},
    {"id": "E3", "ok": (pin_checks["voided_bytes_evidence"]["match"]
                        and V is not None and PINS["voided_bytes_evidence"]["sha256"] != PINS["live_detector"]["sha256"]),
     "detail": {"void_hash": pin_checks["voided_bytes_evidence"]["measured"],
                "distinct_from_restored": PINS["voided_bytes_evidence"]["sha256"] != PINS["live_detector"]["sha256"]}},
    {"id": "E4", "ok": (R["corpus"]["verdict"] == "PASS"
                        and {k: R["corpus"][k] for k in ("tp", "fn", "fp", "tn")}
                        == {k: p2[k] for k in ("tp", "fn", "fp", "tn")}),
     "detail": {"restored": R["corpus"], "pass2_recorded": p2}},
    {"id": "E5", "ok": R["fp_firing"] == 3 and R["fp_clean"] == 1,
     "detail": {"firing": R["fp_firing"], "clean": R["fp_clean"]}},
    {"id": "E6", "ok": R["tp_firing"] == 2, "detail": {"firing": R["tp_firing"]}},
    {"id": "E7", "ok": R["over_suppressed"] == 0, "detail": {"over_suppressed": R["over_suppressed"]}},
    {"id": "E8", "ok": R["growth_total"] == 3, "detail": {"growth_total": R["growth_total"]}},
    {"id": "E9", "ok": (R["hard_adj_snapshot_f344ed2aaea5"] == 19
                        and P["hard_adj_snapshot_f344ed2aaea5"] == 24
                        and V["hard_adj_snapshot_f344ed2aaea5"] == 16),
     "detail": {"RESTORED": R["hard_adj_snapshot_f344ed2aaea5"],
                "PRE": P["hard_adj_snapshot_f344ed2aaea5"],
                "VOID": V["hard_adj_snapshot_f344ed2aaea5"]}},
    {"id": "E10", "ok": (R["hard_w098_snapshot_6d3f0f2792a2"] == 13
                         and P["hard_w098_snapshot_6d3f0f2792a2"] == 17
                         and V["hard_w098_snapshot_6d3f0f2792a2"] <= R["hard_w098_snapshot_6d3f0f2792a2"]),
     "detail": {"RESTORED": R["hard_w098_snapshot_6d3f0f2792a2"],
                "PRE": P["hard_w098_snapshot_6d3f0f2792a2"],
                "VOID": V["hard_w098_snapshot_6d3f0f2792a2"]}},
    {"id": "E11", "ok": any([R["fp_firing"] != V["fp_firing"],
                             R["over_suppressed"] != V["over_suppressed"],
                             R["growth_total"] != V["growth_total"],
                             R["hard_adj_snapshot_f344ed2aaea5"] != V["hard_adj_snapshot_f344ed2aaea5"]]),
     "detail": {"fp": [R["fp_firing"], V["fp_firing"]],
                "over_suppression": [R["over_suppressed"], V["over_suppressed"]],
                "growth": [R["growth_total"], V["growth_total"]],
                "hard_adj": [R["hard_adj_snapshot_f344ed2aaea5"], V["hard_adj_snapshot_f344ed2aaea5"]]}},
]

end_live_det = sha(live_det_path)
end_live_map = sha(live_map_path)
end_adjudication = sha(adjudication_path)
expectations.append({
    "id": "E12",
    "ok": (end_live_det == start_live_det and end_adjudication == start_adjudication
           and start_live_map == end_live_map),
    "detail": {"map_start": start_live_map, "map_end": end_live_map,
               "claims_start": len(live_map.get("claims", [])),
               "detector_start": start_live_det, "detector_end": end_live_det,
               "adjudication_start": start_adjudication, "adjudication_end": end_adjudication,
               "stable": start_live_map == end_live_map}})

out = {
    "task_id": PREREG["task_id"],
    "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "status": "OK",
    "read_only_proof": {
        "detector_start": start_live_det, "detector_end": end_live_det,
        "adjudication_start": start_adjudication, "adjudication_end": end_adjudication,
        "live_map_start": start_live_map, "live_map_end": end_live_map,
        "canonical_unchanged": start_live_det == end_live_det and start_adjudication == end_adjudication,
    },
    "pin_checks": pin_checks,
    "four_way_restore": four_way,
    "adjudication": {"sha256": start_adjudication, "decision_choice": adj["decision"]["choice"],
                     "detectors": {k: v.get("sha256") for k, v in adj["detectors"].items()}},
    "live_map_start": {"sha256": start_live_map, "claims": len(live_map.get("claims", []))},
    "live_map_end": {"sha256": end_live_map, "claims": len(json.loads(live_map_path.read_text()).get("claims", []))},
    "arms": batteries,
    "expectations": expectations,
    "expectations_pass": sum(e["ok"] for e in expectations),
    "expectations_total": len(expectations),
    "verdict": "REPRODUCED" if all(e["ok"] for e in expectations) else "DISCREPANT",
}
RAW.mkdir(parents=True, exist_ok=True)
(RAW / "restore_repro.json").write_text(json.dumps(out, indent=2, sort_keys=True))
print(json.dumps({"verdict": out["verdict"], "expectations_pass": out["expectations_pass"],
                  "expectations_total": out["expectations_total"],
                  "failed": [e["id"] for e in expectations if not e["ok"]]}, indent=2))
