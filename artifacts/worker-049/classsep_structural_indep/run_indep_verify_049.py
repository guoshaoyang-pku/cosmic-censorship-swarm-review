#!/usr/bin/env python3
"""W049-A1-CLASSSEP-STRUCTURAL-INDEP-VERIFY-01 independent verification instrument.

Object under test: worker-040's clause-scope structural classifier STRUCTURAL_R3
(artifacts/worker-040/classsep_structural/pinned/structural_class_separation.R3.frozen.py,
sha256 feeb475de6f9...), whose claim is MEETS_BAR_ON_THE_FROZEN_CORPORA against the
r3 adoption bar recorded at reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467.

This instrument is written from scratch by worker-049 (stdlib only). It does NOT import or
execute worker-040's run_battery.py; it loads the frozen corpora itself and calls only the
public scoring entry points of the arm under test. Reference arms are re-scored with the same
harness as a reproduction control against the adjudication's published numbers.

Modes:
  --preregister  freeze pins + held-out corpus hash into PRE_REGISTRATION.json, no scoring
  --run          fail-closed battery; writes results.json, controls.json, report.json

Exit codes: 0 valid; 2 pin mismatch/absent; 3 nondeterminism; 4 sentinel/canonical write;
            5 reference-control (harness) mismatch.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TASK_ID = "W049-A1-CLASSSEP-STRUCTURAL-INDEP-VERIFY-01"
ACTOR = "worker-049"
NODE = "A1"
GATE = "G-AUDIT"
CLASS_ID = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"

CANDIDATE = "artifacts/worker-040/classsep_structural/pinned/structural_class_separation.R3.frozen.py"
CANDIDATE_MAIN = "artifacts/worker-040/classsep_structural/structural_class_separation.py"

PINS = {
    CANDIDATE: "feeb475de6f9a4e9536cf7ea239a089a787d7066f7a118d4791db308733d2507",
    CANDIDATE_MAIN: "feeb475de6f9a4e9536cf7ea239a089a787d7066f7a118d4791db308733d2507",
    # corpora (None = frozen at preregistration time from the measured bytes)
    "artifacts/worker-07/class_separation_falsification/results.json":
        "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
    "artifacts/audit/classsep_calibration.py":
        "8f2efd262f97b53a50c33a698d57074b83b4df0c2793f5ff7799648bea958464",
    "artifacts/worker-049/classsep_fn_audit/corpus.json":
        "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23",
    "artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json":
        "db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b",
    "artifacts/worker-049/classsep_fn_audit/corpus_guard_twin_fix.json":
        "c3bbb5be3979eeb4dec2a85e352b8faa77d50a3aa15d9afa95a2a6b7159c5e43",
    "artifacts/worker-035/classsep_hardfail_adjudication/controls.json":
        "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d",
    "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json":
        "ffabb753313fdf76fe5df3760ed0a0f52eb5c8539b6e0e9d6b0800fbfe3a6395",
    # adjudication + snapshot
    "reviews/CLASSSEP-calibration-adjudication.json":
        "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1",
    "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json":
        "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749",
    # reference arms
    "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.a8c04fc31e4a.py":
        "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
    "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py":
        "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    "proposed/class_separation.py":
        "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
    "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py":
        "dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470",
    # frozen release the review is scoped to
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    # held-out corpus authored before scoring
    "artifacts/worker-049/classsep_structural_indep/heldout_corpus.json": None,
}

# Canonical paths that must not move during the run (fail-closed).
SENTINELS = [
    "research_map/class_separation.py",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "evaluation_rubric.yaml",
    "proposed/class_separation.py",
    "runtime/bin/classsep_regression.py",
]
# Observation-only paths (the controller rewrites these continuously).
OBSERVED = ["research_map/research_map.json"]

ARMS = {
    "APPLIED": "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.a8c04fc31e4a.py",
    "PRE": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    "STAGED": "proposed/class_separation.py",
    "PROSEFIX": "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
}
PUBLISHED_ARMS = {  # from adjudication decision.per_arm
    "APPLIED": {"corpus_a_pass": True, "sensitivity": "4/6", "specificity": "3/10", "cue_fn_high": 1},
    "PRE": {"corpus_a_pass": True, "sensitivity": "4/6", "specificity": "1/10", "cue_fn_high": 0},
    "STAGED": {"corpus_a_pass": True, "sensitivity": "5/6", "specificity": "1/10", "cue_fn_high": 0},
    "PROSEFIX": {"corpus_a_pass": True, "sensitivity": "4/6", "specificity": "10/10", "cue_fn_high": 10},
}
BAR = {"corpus_a": "PASS 17/0/10/0", "sensitivity": ">=5/6", "specificity": ">=9/10",
       "cue_induced_fn_high": 0, "live_labeled_metalinguistic_fp": 0}
HELDOUT_RULE = {"sensitivity_ge": "6/8", "specificity_ge": "7/8",
                "note": "two disclosed-limitation probes (no composite token; cross-sentence antecedent) are tolerated"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan_text(mod, text, where):
    try:
        return mod.findings_for_text(text, where, mode="prose")
    except TypeError:
        return mod.findings_for_text(text, where)


def scan_obj(mod, obj, where):
    try:
        return mod.findings(obj, where, mode="declaration")
    except TypeError:
        return mod.findings(obj, where)


def hard(fs):
    return [f for f in fs if "SOFT" not in f]


# ------------------------------------------------------------------ corpora

def corpus_a_items():
    res = json.loads((ROOT / "artifacts/worker-07/class_separation_falsification/results.json").read_text())
    items = []
    for fx in res["fixtures"]:
        p = ROOT / fx["fixture_path"]
        assert p.exists(), fx["fixture_path"]
        assert sha256_file(p) == fx["fixture_sha256"], f"fixture drift {fx['fixture_path']}"
        items.append((fx["id"], json.loads(p.read_text()), bool(fx["is_class_merge"])))
    return items


def corpus_c_items():
    """Extract the frozen ASSERTION_MENTION_FIXTURES data block from the pinned calibration
    script by AST literal evaluation (no code execution, no import of the script)."""
    tree = ast.parse((ROOT / "artifacts/audit/classsep_calibration.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ASSERTION_MENTION_FIXTURES" for t in node.targets):
            return [(fid, bool(truth), text) for fid, truth, text in ast.literal_eval(node.value)]
    raise RuntimeError("ASSERTION_MENTION_FIXTURES not found")


def _corpus_with_twins(path):
    o = json.loads((ROOT / path).read_text())
    fx = o["fixtures"]
    twins = {}
    for f in fx:
        if f.get("twin_of"):
            twins.setdefault(f["twin_of"], []).append(f)
    return fx, twins


def score_corpus_a(mod):
    tp = fn = fp = tn = 0
    rows = []
    for fid, fixture, truth in corpus_a_items():
        # faithful to the published worker-07 protocol: score the fixture map, then also score any
        # artifact file a node points at; detected = any non-SOFT finding across both surfaces.
        det = mod.findings_for_map(fixture)
        for g in fixture.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += scan_text(mod, (ROOT / art).read_text(errors="replace"), f"artifact {art}")
        fired = bool(hard(det))
        cls = "TP" if (truth and fired) else "FN" if truth else "FP" if fired else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fid, "truth_merge": truth, "fired": fired, "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
            "verdict": "PASS" if fn == 0 and fp == 0 else "FAIL", "rows": rows}


def score_corpus_c(mod):
    tp = fn = fp = tn = 0
    rows = []
    for fid, truth, text in corpus_c_items():
        fs = scan_text(mod, text, f"fixture {fid}")
        fired = bool(fs)
        cls = "TP" if (truth and fired) else "FN" if truth else "FP" if fired else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fid, "expect_merge_assertion": truth, "fired": fired, "class": cls,
                     "n_findings": len(fs)})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
            "sensitivity": f"{tp}/{tp+fn}", "specificity": f"{tn}/{tn+fp}", "rows": rows}


def score_cue_fn(mod):
    """worker-049 corpus v1 (39) + v2 (25): cleared HIGH adversarial assertions whose twin flags,
    mention FPs, plain-positive FNs, twin flag rate. Twin-fix addendum reported separately."""
    out = {}
    for tag, path in (("v1", "artifacts/worker-049/classsep_fn_audit/corpus.json"),
                      ("v2", "artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json")):
        fx, twins = _corpus_with_twins(path)
        fired = {f["id"]: bool(hard(scan_text(mod, f["text"], f"fixture {f['id']}"))) for f in fx}
        cleared_high, twin_flagged, twin_total = [], 0, 0
        for f in fx:
            if f.get("category") == "ADVERSARIAL_ASSERTION" and f.get("confidence") == "HIGH":
                tw = twins.get(f["id"], [])
                if tw:
                    twin_total += 1
                    if any(fired[t["id"]] for t in tw):
                        twin_flagged += 1
                        if not fired[f["id"]]:
                            cleared_high.append(f["id"])
        mention_fp = [f["id"] for f in fx if f.get("category") == "MENTION"
                      and f.get("expected_findings") == 0 and fired[f["id"]]]
        plain_fn = [f["id"] for f in fx if f.get("category") == "PLAIN_POSITIVE"
                    and f.get("expected_findings") == 1 and not fired[f["id"]]]
        out[tag] = {"n": len(fx), "cleared_high": cleared_high, "cue_induced_fn_high": len(cleared_high),
                    "mention_fp": mention_fp, "plain_positive_fn": plain_fn,
                    "twin_controls_flagged": f"{twin_flagged}/{twin_total}"}
    tf = json.loads((ROOT / "artifacts/worker-049/classsep_fn_audit/corpus_guard_twin_fix.json").read_text())
    add = [f for f in tf.get("fixtures", []) if f.get("id") == "G05T2"]
    if add:
        f = add[0]
        out["twin_fix"] = {"id": f["id"], "expected_findings": f.get("expected_findings"),
                           "fired": bool(hard(scan_text(mod, f["text"], f"fixture {f['id']}"))),
                           "note": tf.get("reporting_note", "authored after v2 results were seen")}
    return out


def score_w035(mod):
    o = json.loads((ROOT / "artifacts/worker-035/classsep_hardfail_adjudication/controls.json").read_text())
    pos = neg = pos_ok = neg_ok = 0
    fails = []
    for c in o["controls"]:
        fired = bool(hard(scan_text(mod, c["text"], f"control {c['control_id']}")))
        if c["expect"] == "ASSERTION":
            pos += 1
            pos_ok += fired
            if not fired:
                fails.append({"id": c["control_id"], "expect": "ASSERTION", "fired": False})
        else:
            neg += 1
            neg_ok += (not fired)
            if fired:
                fails.append({"id": c["control_id"], "expect": c["expect"], "fired": True})
    return {"pos": f"{pos_ok}/{pos}", "neg": f"{neg_ok}/{neg}", "fails": fails}


def score_w098(mod):
    o = json.loads((ROOT / "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json").read_text())
    fn_fire = fn_total = fp_clean = fp_total = 0
    rows = []
    for f in o["probes"]["fn"]:
        fired = bool(hard(scan_text(mod, f["text"], f"probe {f['name']}")))
        fn_total += 1; fn_fire += fired
        rows.append({"name": f["name"], "expect_fire": True, "fired": fired})
    for f in o["probes"]["fp"]:
        fired = bool(hard(scan_text(mod, f["text"], f"probe {f.get('name', 'fp')}")))
        fp_total += 1; fp_clean += (not fired)
        rows.append({"name": f.get("name", f["text"][:20]), "expect_fire": False, "fired": fired})
    return {"fn_fired": f"{fn_fire}/{fn_total}", "fp_clean": f"{fp_clean}/{fp_total}", "rows": rows}


def live_census(mod, snapshot, labeled_idx):
    fs = mod.findings_for_map(snapshot)
    hs = hard(fs)
    seen = []
    for f in hs:
        m = re.search(r"claims\[(\d+)\]", f)
        if m:
            seen.append(int(m.group(1)))
    labeled_firing = sorted({i for i in seen if i in labeled_idx})
    unlabeled = sorted({i for i in seen if i not in labeled_idx})
    return {"hard_total": len(hs), "soft_total": len(fs) - len(hs),
            "claims_flagged": len(set(seen)), "labeled_fp_still_firing": labeled_firing,
            "unlabeled_flagged": unlabeled, "claims_in_snapshot": len(snapshot.get("claims", []))}


def labeled_fp_indices():
    adj = json.loads((ROOT / "reviews/CLASSSEP-calibration-adjudication.json").read_text())
    det = adj["corpus_b_live_detail"]["APPLIED"]["labeled_detail"]
    return sorted({x["claim_index"] for x in det if x["verdict"] == "FP"})


CONTROL_FIXTURES = [
    ("merge_assertion_fires", "C0 or C2 are one class.", True),
    ("quoted_mention_silent", "the detector flagged 'C0 or C2 are one class' in that region.", False),
    ("prohibition_silent", "Do not merge C0 or C2 into one class.", False),
    ("negation_silent", "no C0/C2 merge exists at the formal surface.", False),
    ("separation_silent", "C0 and C2 are distinct classes.", False),
    ("empty_silent", "", False),
]


def run_controls(mod):
    rows = []
    ok = True
    for cid, text, expect_fire in CONTROL_FIXTURES:
        fired = bool(hard(scan_text(mod, text, f"control {cid}")))
        passed = fired == expect_fire
        ok &= passed
        rows.append({"id": cid, "expect_fire": expect_fire, "fired": fired, "pass": passed})
    return {"ok": ok, "rows": rows}


def battery(mod, snapshot, labeled_idx):
    return {
        "corpus_a": score_corpus_a(mod),
        "corpus_c": score_corpus_c(mod),
        "cue_fn": score_cue_fn(mod),
        "w035": score_w035(mod),
        "w098": score_w098(mod),
        "live_census": live_census(mod, snapshot, labeled_idx),
        "controls": run_controls(mod),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preregister", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()

    measured = {}
    problems = []
    for p in PINS:
        fp = ROOT / p
        if not fp.exists():
            problems.append(f"missing pin {p}")
            measured[p] = None
            continue
        measured[p] = sha256_file(fp)
    # pins whose expected value is None are frozen by this instrument at prereg time
    prereg_path = HERE / "PRE_REGISTRATION.json"

    if a.preregister:
        hold = sha256_file(ROOT / "artifacts/worker-049/classsep_structural_indep/heldout_corpus.json")
        prereg = {
            "schema": "worker-049/classsep-structural-indep-prereg/v1",
            "task_id": TASK_ID, "actor": ACTOR, "node_id": NODE, "gate": GATE,
            "class_id": CLASS_ID,
            "created_at": "2026-09-12T01:40:00+08:00",
            "question": ("Does worker-040's STRUCTURAL_R3 clause-scope classifier reproduce the r3 "
                         "adjudication's declared adoption bar on the frozen corpora, and does it hold on a "
                         "non-author authored held-out corpus frozen before scoring?"),
            "object_under_test": {"path": CANDIDATE, "sha256": measured.get(CANDIDATE)},
            "object_main_copy": {"path": CANDIDATE_MAIN, "sha256": measured.get(CANDIDATE_MAIN)},
            "bar_source": {"path": "reviews/CLASSSEP-calibration-adjudication.json",
                           "sha256": measured.get("reviews/CLASSSEP-calibration-adjudication.json"),
                           "decision": "c", "adoption_bar": BAR},
            "frozen_corpora": {
                "corpus_a_worker07_27": "artifacts/worker-07/class_separation_falsification/results.json",
                "corpus_c_assertion_mention_16": "artifacts/audit/classsep_calibration.py",
                "corpus_d_v1_39": "artifacts/worker-049/classsep_fn_audit/corpus.json",
                "corpus_d_v2_25": "artifacts/worker-049/classsep_fn_audit/corpus_guard_probe.json",
                "w035_battery_23": "artifacts/worker-035/classsep_hardfail_adjudication/controls.json",
                "w098_probes": "artifacts/worker-098/classsep_prose_shadow/drift_recheck.json",
            },
            "live_snapshot": {"path": "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
                              "sha256": measured.get("artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json")},
            "reference_arms": {k: {"path": v, "sha256": measured.get(v)} for k, v in ARMS.items()},
            "published_reference_numbers": PUBLISHED_ARMS,
            "methods": {
                "corpus_a": "own loader; per-fixture findings_for_map; detected = any non-SOFT finding; ground truth is_class_merge",
                "corpus_c": "fixtures extracted from the pinned calibration script by ast.literal_eval; fired = any finding (published rule)",
                "cue_fn": "own loader; fired = any non-SOFT finding; cleared_high = HIGH ADVERSARIAL_ASSERTION whose twin control fires and which does not fire; cue_induced_fn_high over v1+v2",
                "live_census": "findings_for_map over the pinned snapshot; labeled FP indices taken from the adjudication's corpus_b_live_detail.APPLIED",
                "reference_control": "same harness on the four pinned lexical arms; must reproduce PUBLISHED_ARMS else harness mismatch (exit 5)",
                "determinism": "full battery executed twice in fresh module imports; digests must match",
                "sentinels": "six canonical paths hashed before/after; movement is exit 4",
                "heldout": "heldout_corpus.json hash frozen here; scored only after this prereg is written",
            },
            "heldout_decision_rule": HELDOUT_RULE,
            "verdict_rule": {
                "REJECT_FROZEN_BAR_NOT_REPRODUCED": "candidate corpus A not PASS, or corpus C sens <5/6, or spec <9/10, or cue_high >0, or labeled FP >0",
                "REVISE_HELDOUT_GAP": "frozen bar reproduced but held-out rule not met",
                "ACCEPT_REPRODUCED_AND_HELDOUT_HOLDS": "frozen bar reproduced and held-out rule met",
                "INCONCLUSIVE_HARNESS_MISMATCH": "reference control deviates from PUBLISHED_ARMS or pins moved",
            },
            "non_claims": [
                "not a gate verdict; G-AUDIT stays pending; workers cannot set status/validation/gate",
                "not an adoption, a proposal write, or a detector-of-record choice",
                "no canonical, schema, taxonomy, ledger or proposed file is edited",
                "held-out corpus is non-author authored but not blind: the corpus author had read the object's disclosed limitations",
            ],
            "falsifier": ("falsified by a re-run of this instrument at the same pins that changes results.json; by any pinned "
                          "input hash move; or by a genuine first-order C0/C2 merge assertion among the claims the candidate "
                          "leaves silent on the frozen snapshot"),
        }
        prereg["pins"] = {p: {"measured": measured[p], "expected": PINS[p] or measured[p]} for p in PINS}
        prereg["heldout_corpus_sha256"] = hold
        prereg_path.write_text(json.dumps(prereg, indent=1, ensure_ascii=False) + "\n")
        print(f"preregistered: {prereg_path} heldout={hold[:12]}")
        return 0

    if not a.run:
        print("use --preregister or --run", file=sys.stderr)
        return 1

    prereg = json.loads(prereg_path.read_text())
    # fail-closed pin check against the recorded expected values
    for p, rec in prereg["pins"].items():
        if measured[p] != rec["expected"]:
            problems.append(f"pin moved: {p} expected {rec['expected'][:12]} measured "
                            f"{(measured[p] or 'MISSING')[:12]}")
    if measured["artifacts/worker-049/classsep_structural_indep/heldout_corpus.json"] != prereg["heldout_corpus_sha256"]:
        problems.append("held-out corpus moved since preregistration")

    t0_sent = {p: sha256_file(ROOT / p) for p in SENTINELS}
    t0_obs = {p: sha256_file(ROOT / p) for p in OBSERVED}

    snapshot = json.loads((ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json").read_text())
    labeled_idx = labeled_fp_indices()

    cand = load_module(CANDIDATE, "cand_structural_r3")
    cand_b1 = battery(cand, snapshot, labeled_idx)
    cand_b2 = battery(load_module(CANDIDATE, "cand_structural_r3_second"), snapshot, labeled_idx)
    deterministic = digest(cand_b1) == digest(cand_b2)

    arm_results, arm_problems = {}, []
    for name, path in ARMS.items():
        mod = load_module(path, f"arm_{name.lower()}")
        b = battery(mod, snapshot, labeled_idx)
        arm_results[name] = {
            "corpus_a": {"verdict": b["corpus_a"]["verdict"], "tp": b["corpus_a"]["tp"],
                         "fn": b["corpus_a"]["fn"], "fp": b["corpus_a"]["fp"], "tn": b["corpus_a"]["tn"]},
            "corpus_c": {"sensitivity": b["corpus_c"]["sensitivity"],
                         "specificity": b["corpus_c"]["specificity"]},
            "cue_fn_high": b["cue_fn"]["v1"]["cue_induced_fn_high"] + b["cue_fn"]["v2"]["cue_induced_fn_high"],
            "live_census": b["live_census"],
        }
        pub = PUBLISHED_ARMS[name]
        ok = (arm_results[name]["corpus_a"]["verdict"] == ("PASS" if pub["corpus_a_pass"] else "FAIL")
              and arm_results[name]["corpus_c"]["sensitivity"] == pub["sensitivity"]
              and arm_results[name]["corpus_c"]["specificity"] == pub["specificity"]
              and arm_results[name]["cue_fn_high"] == pub["cue_fn_high"])
        arm_results[name]["published_match"] = ok
        if not ok:
            arm_problems.append(name)

    t1_sent = {p: sha256_file(ROOT / p) for p in SENTINELS}
    t1_obs = {p: sha256_file(ROOT / p) for p in OBSERVED}
    sentinel_moved = sorted(p for p in SENTINELS if t0_sent[p] != t1_sent[p])

    # held-out scoring
    hold = json.loads((ROOT / "artifacts/worker-049/classsep_structural_indep/heldout_corpus.json").read_text())
    hrows = []
    for f in hold["fixtures"]:
        fired = bool(hard(scan_text(cand, f["text"], f"heldout {f['id']}")))
        hrows.append({"id": f["id"], "shape": f["shape"], "expected_findings": f["expected_findings"],
                      "fired": fired, "pass": bool(fired) == bool(f["expected_findings"])})
    h_sens_n = sum(1 for r in hrows if r["expected_findings"] == 1 and r["fired"])
    h_sens_d = sum(1 for r in hrows if r["expected_findings"] == 1)
    h_spec_n = sum(1 for r in hrows if r["expected_findings"] == 0 and not r["fired"])
    h_spec_d = sum(1 for r in hrows if r["expected_findings"] == 0)
    heldout_holds = h_sens_n >= 6 and h_spec_n >= 7

    c = cand_b1
    frozen_bar_met = (c["corpus_a"]["verdict"] == "PASS"
                      and c["corpus_c"]["tp"] >= 5
                      and c["corpus_c"]["tn"] >= 9
                      and c["cue_fn"]["v1"]["cue_induced_fn_high"] == 0
                      and c["cue_fn"]["v2"]["cue_induced_fn_high"] == 0
                      and not c["live_census"]["labeled_fp_still_firing"])

    if problems or sentinel_moved:
        verdict = "INCONCLUSIVE_PINS_OR_WRITES"
    elif arm_problems or not deterministic:
        verdict = "INCONCLUSIVE_HARNESS_MISMATCH"
    elif not frozen_bar_met:
        verdict = "REJECT_FROZEN_BAR_NOT_REPRODUCED"
    elif not heldout_holds:
        verdict = "REVISE_HELDOUT_GAP"
    else:
        verdict = "ACCEPT_REPRODUCED_AND_HELDOUT_HOLDS"

    results = {
        "schema": "worker-049/classsep-structural-indep-results/v1", "task_id": TASK_ID,
        "actor": ACTOR, "node_id": NODE, "gate": GATE, "class_id": CLASS_ID,
        "at": "2026-09-12T01:42:00+08:00",
        "object_under_test": {"path": CANDIDATE, "sha256": measured[CANDIDATE]},
        "adoption_bar": BAR, "bar_source": prereg["bar_source"],
        "candidate": c, "candidate_run2_digest": digest(cand_b2),
        "deterministic": deterministic,
        "reference_arms": arm_results,
        "heldout": {"corpus_sha256": prereg["heldout_corpus_sha256"], "rows": hrows,
                    "sensitivity": f"{h_sens_n}/{h_sens_d}", "specificity": f"{h_spec_n}/{h_spec_d}",
                    "holds": heldout_holds, "rule": HELDOUT_RULE},
        "frozen_bar_met": frozen_bar_met,
        "verdict": verdict,
        "falsifier": prereg["falsifier"],
        "non_claims": prereg["non_claims"],
    }
    controls = {
        "schema": "worker-049/classsep-structural-indep-controls/v1", "task_id": TASK_ID,
        "pins_resolved": not problems, "pin_problems": problems,
        "reference_control_match": not arm_problems,
        "reference_control_failures": arm_problems,
        "determinism_byte_identical": deterministic,
        "sentinels_before": t0_sent, "sentinels_after": t1_sent, "sentinels_moved": sentinel_moved,
        "observed_map_sha_before": t0_obs, "observed_map_sha_after": t1_obs,
        "map_moved_during_run": t0_obs != t1_obs,
        "directional_controls": c["controls"],
        "exit_codes": {"0": "valid", "2": "pin mismatch", "3": "nondeterminism",
                       "4": "sentinel movement", "5": "reference-control mismatch"},
    }
    (HERE / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n")
    (HERE / "controls.json").write_text(json.dumps(controls, indent=1, ensure_ascii=False) + "\n")

    print(json.dumps({"verdict": verdict, "frozen_bar_met": frozen_bar_met,
                      "heldout": results["heldout"]["sensitivity"] + " " + results["heldout"]["specificity"],
                      "corpus_a": c["corpus_a"]["verdict"],
                      "corpus_c": c["corpus_c"]["sensitivity"] + " " + c["corpus_c"]["specificity"],
                      "cue_fn_high": [c["cue_fn"]["v1"]["cue_induced_fn_high"],
                                      c["cue_fn"]["v2"]["cue_induced_fn_high"]],
                      "live_hard": c["live_census"]["hard_total"],
                      "labeled_firing": c["live_census"]["labeled_fp_still_firing"],
                      "ref_match": not arm_problems, "det": deterministic,
                      "problems": problems, "sentinel_moved": sentinel_moved}, ensure_ascii=False))
    if problems:
        return 2
    if sentinel_moved:
        return 4
    if not deterministic:
        return 3
    if arm_problems:
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
