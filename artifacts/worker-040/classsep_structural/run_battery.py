#!/usr/bin/env python3
"""W040-A1-CLASSSEP-STRUCTURAL-01 runner.

Read-only on every shared artifact. Scores the pre-registered clause-scope structural
cue (`structural_class_separation.py`, rule STRUCTURAL_R1) on the frozen union corpora
and on the worker-035 holdout battery, reproduces the published lexical-arm numbers as
harness control C1, and writes its own artifacts under
artifacts/worker-040/classsep_structural/.

Exit 0 when all controls pass (the structural endpoint may still fail the adoption bar;
that is a recorded result, not a runner error).
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import structural_class_separation as structural  # noqa: E402

NOW = datetime.now().astimezone().isoformat(timespec="seconds")

PINS = {
    "worker07_results": ("artifacts/worker-07/class_separation_falsification/results.json",
                         "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"),
    "audit_calibration": ("artifacts/audit/classsep_calibration.py",
                          "8f2efd262f97b53a50c33a698d57074b83b4df0c2793f5ff7799648bea958464"),
    "w049_v1": ("artifacts/worker-049/classsep_fn_audit/corpus.json",
                "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "w049_v2": ("artifacts/worker-073/classsep_union_separability/pinned/corpus_049_v2_guardprobe.json",
                "db6dff9f4edaf585a78c2a5e084665c037db61bc354a86c5cba74f5f71c6ed8b"),
    "w049_twinfix": ("artifacts/worker-073/classsep_union_separability/pinned/corpus_049_twinfix.json",
                     "c3bbb5be3979eeb4dec2a85e352b8faa77d50a3aa15d9afa95a2a6b7159c5e43"),
    "w098_probes": ("artifacts/worker-098/classsep_prose_shadow/drift_recheck.json",
                    "ffabb753313fdf76fe5df3760ed0a0f52eb5c8539b6e0e9d6b0800fbfe3a6395"),
    "w035_battery": ("artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
                     "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"),
    "live_snapshot": ("artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
                      "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"),
    "adjudication_r3": ("reviews/CLASSSEP-calibration-adjudication.json",
                        "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1"),
}
REF_ARMS = {
    "APPLIED_a8c04fc31e4a": ("artifacts/worker-073/classsep_union_separability/pinned/"
                             "class_separation.live.a8c04fc31e4a.py",
                             "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"),
    "PRE_c266dbceca87": ("artifacts/worker-073/classsep_union_separability/pinned/"
                         "class_separation.c266dbceca87.py",
                         "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"),
    "PROSEFIX_dc8aa0de3869": ("artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                              "dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470"),
}
CANONICAL_WRITE_GUARD = [
    "research_map/class_separation.py", "proposed/class_separation.py",
    "schemas/af_scc_c0_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml", "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json", "evaluation_rubric.yaml",
    "reviews/CLASSSEP-calibration-adjudication.json",
]


def sha256(p) -> str:
    p = ROOT / p
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load_module(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def score_map_corpus(module, fixtures, root=ROOT):
    tp = fn = tn = fp = 0
    rows = []
    for fx in fixtures:
        path = root / fx["fixture_path"]
        if not path.exists():
            rows.append({"id": fx["id"], "class": "MISSING"}); continue
        m = json.loads(path.read_text())
        det = module.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (root / art).is_file():
                    det += module.findings_for_text((root / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fx["id"], "class": cls})
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "corpus_size": len(fixtures), "rows": rows}


def score_text_set(module, items):
    """items: list of (id, expect_bool, text)."""
    rows, tp = [], 0
    fn = fp = tn = 0
    for fid, expect, text in items:
        got = bool(module.findings_for_text(text, f"fixture {fid}"))
        cls = "TP" if expect and got else "FN" if expect else "FP" if got else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fid, "expect": bool(expect), "fired": got, "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(items),
            "sensitivity": f"{tp}/{tp + fn}", "specificity": f"{tn}/{tn + fp}", "rows": rows}


def score_corpus_d(module, fixtures):
    by_id = {f["id"]: f for f in fixtures}
    adv_total = twin_flagged = 0
    cleared = []
    cue_fn = []
    mention_fp = []
    positive_fn = []
    for f in fixtures:
        got = bool(module.findings_for_text(f["text"], f"fixture {f['id']}"))
        if f["category"] == "ADVERSARIAL_ASSERTION":
            adv_total += 1
            twin = by_id.get(f["id"] + "T")
            twin_fired = bool(twin) and bool(module.findings_for_text(twin["text"], f"fixture {twin['id']}"))
            if twin_fired:
                twin_flagged += 1
            if not got:
                cleared.append(f["id"])
                if twin_fired:
                    cue_fn.append({"adversarial": f["id"], "twin": twin["id"],
                                   "confidence": f.get("confidence"), "cue": f.get("adversarial_cue")})
        elif f["category"] in ("TWIN_CONTROL", "PLAIN_POSITIVE") and not got:
            positive_fn.append(f["id"])
        elif f["category"] == "MENTION" and got:
            mention_fp.append(f["id"])
    return {"adversarial_total": adv_total, "adversarial_cleared": cleared,
            "twin_controls_flagged": f"{twin_flagged}/{adv_total}",
            "cue_induced_fn": cue_fn,
            "cue_induced_fn_high": sum(1 for x in cue_fn if x["confidence"] == "HIGH"),
            "mention_fp": mention_fp, "positive_fn": positive_fn}


def score_w098(module, probes):
    fn_rows = [{"name": x["name"], "fired": bool(module.findings_for_text(x["text"], x["name"]))}
               for x in probes["fn"]]
    fp_rows = [{"name": x.get("name", x["text"][:40]),
                "expected_live": x.get("expected_live", False),
                "fired": bool(module.findings_for_text(x["text"], x.get("name", "fp")))}
               for x in probes["fp"]]
    return {"fn_fired": f"{sum(r['fired'] for r in fn_rows)}/{len(fn_rows)}", "fn_rows": fn_rows,
            "fp_clean": f"{sum(not r['fired'] for r in fp_rows)}/{len(fp_rows)}", "fp_rows": fp_rows}


def score_battery(module, battery):
    rows = []
    for c in battery["controls"]:
        expect_assert = str(c["expect"]).upper().startswith("ASSERT")
        got = bool(module.findings_for_text(c["text"], c["control_id"]))
        rows.append({"id": c["control_id"], "expect": c["expect"], "fired": got,
                     "pass": got == expect_assert})
    pos = [r for r in rows if r["expect"].upper().startswith("ASSERT")]
    neg = [r for r in rows if not r["expect"].upper().startswith("ASSERT")]
    return {"pos_pass": f"{sum(r['pass'] for r in pos)}/{len(pos)}",
            "neg_pass": f"{sum(r['pass'] for r in neg)}/{len(neg)}",
            "all_pass": all(r["pass"] for r in rows), "rows": rows}


def live_census(module, snapshot, live_labels):
    m = json.loads(snapshot.read_text())
    findings = module.findings_for_map(m)
    hard = [f for f in findings if not f.startswith("CLASSSEP-SOFT")]
    soft = [f for f in findings if f.startswith("CLASSSEP-SOFT")]
    flagged = {}
    for f in hard:
        import re as _re
        for mo in _re.finditer(r"claims\[(\d+)\]", f):
            flagged.setdefault(int(mo.group(1)), []).append(f)
    labeled_fp_still = []
    unlabeled = []
    for idx in sorted(flagged):
        labels = live_labels.get(idx)
        if labels is None:
            unlabeled.append(idx)
        elif all(v[0] == "FP" for v in labels):
            labeled_fp_still.append(idx)
    return {"map_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "claims_in_map": len(m.get("claims", [])),
            "structural_hard": len(hard), "structural_soft": len(soft),
            "claims_flagged": len(flagged),
            "labeled_fp_still_firing": labeled_fp_still,
            "unlabeled_flagged": unlabeled,
            "non_claim_findings": [f for f in hard if "claims[" not in f][:5]}


def main() -> int:
    # ---- C6: pins fail closed
    pin_check = {}
    bad = []
    for name, (rel, want) in list(PINS.items()) + list(REF_ARMS.items()):
        got = sha256(rel)
        ok = got == want
        pin_check[name] = {"path": rel, "sha256": got, "expected": want, "ok": ok}
        if not ok:
            bad.append(name)
    if bad:
        print("PIN DRIFT (fail closed):", bad)
        (HERE / "results.json").write_text(json.dumps(
            {"schema": "worker-040/classsep-structural-results/v1", "at": NOW,
             "pin_drift": bad, "pin_check": pin_check, "meets_bar": False,
             "result": "ABORTED_PIN_DRIFT"}, indent=1))
        return 1

    sentinel_before = {p: sha256(p) for p in CANONICAL_WRITE_GUARD}

    structural_mod = structural
    arms = {"STRUCTURAL_R1": structural_mod}
    for name, (rel, _want) in REF_ARMS.items():
        arms[name] = load_module(rel, f"arm_{name}")

    w07 = json.loads((ROOT / PINS["worker07_results"][0]).read_text())
    corpus_c = structural.extract_assertion_mention_fixtures(ROOT / PINS["audit_calibration"][0])
    w049_v1 = json.loads((ROOT / PINS["w049_v1"][0]).read_text())["fixtures"]
    w049_v2 = json.loads((ROOT / PINS["w049_v2"][0]).read_text())["fixtures"]
    w098 = json.loads((ROOT / PINS["w098_probes"][0]).read_text())["probes"]
    battery = json.loads((ROOT / PINS["w035_battery"][0]).read_text())
    live_labels = None
    tree = ast.parse((ROOT / PINS["audit_calibration"][0]).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "LIVE_LABELS" for t in node.targets):
            live_labels = ast.literal_eval(node.value)
    if live_labels is None:
        raise RuntimeError("LIVE_LABELS not found")

    all_arms = {}
    for name, mod in arms.items():
        all_arms[name] = {
            "corpus_a": score_map_corpus(mod, w07["fixtures"]),
            "corpus_c": score_text_set(mod, corpus_c),
            "corpus_d_v1": score_corpus_d(mod, w049_v1),
            "corpus_d_v2": score_corpus_d(mod, w049_v2),
            "worker098": score_w098(mod, w098),
            "worker035_battery": score_battery(mod, battery),
        }

    primary = all_arms["STRUCTURAL_R1"]
    ca = primary["corpus_a"]
    cc = primary["corpus_c"]
    d1 = primary["corpus_d_v1"]
    d2 = primary["corpus_d_v2"]
    sens_ok = cc["tp"] >= 5
    spec_ok = cc["tn"] >= 9
    cue_ok = d1["cue_induced_fn_high"] == 0 and d2["cue_induced_fn_high"] == 0
    corpus_a_pass = ca["verdict"] == "PASS"
    meets_bar = bool(corpus_a_pass and sens_ok and spec_ok and cue_ok)

    # ---- C1 harness reproduction against published adjudication numbers
    published = json.loads((ROOT / PINS["adjudication_r3"][0]).read_text())
    per_arm = published["decision"]["per_arm"]
    c1 = {}
    for name, pub in (("APPLIED_a8c04fc31e4a", per_arm["APPLIED"]),
                      ("PRE_c266dbceca87", per_arm["PRE"]),
                      ("PROSEFIX_dc8aa0de3869", per_arm["PROSEFIX"])):
        got = all_arms[name]
        c1[name] = {
            "corpus_a_verdict": got["corpus_a"]["verdict"],
            "corpus_a_pass_match": (got["corpus_a"]["verdict"] == "PASS") == pub["corpus_a_pass"],
            "sensitivity": got["corpus_c"]["sensitivity"], "sensitivity_match": got["corpus_c"]["sensitivity"] == pub["sensitivity"],
            "specificity": got["corpus_c"]["specificity"], "specificity_match": got["corpus_c"]["specificity"] == pub["specificity"],
            "cue_fn_high": got["corpus_d_v1"]["cue_induced_fn_high"],
            "cue_fn_high_match": got["corpus_d_v1"]["cue_induced_fn_high"] == pub["cue_fn_high"],
        }
    c1_ok = all(v["corpus_a_pass_match"] and v["sensitivity_match"] and v["specificity_match"]
                and v["cue_fn_high_match"] for v in c1.values())

    # ---- C2 determinism
    rerun = {n: {"corpus_a": score_map_corpus(m, w07["fixtures"]),
                 "corpus_c": score_text_set(m, corpus_c)} for n, m in arms.items()}
    payload_a = json.dumps({k: v["corpus_a"] for k, v in all_arms.items()}, sort_keys=True)
    payload_b = json.dumps({k: v["corpus_a"] for k, v in rerun.items()}, sort_keys=True)
    payload_c1 = json.dumps({k: v["corpus_c"] for k, v in all_arms.items()}, sort_keys=True)
    payload_c2 = json.dumps({k: v["corpus_c"] for k, v in rerun.items()}, sort_keys=True)
    c2_ok = payload_a == payload_b and payload_c1 == payload_c2

    # ---- C5 directional controls
    c5_fire = bool(structural_mod.findings_for_text('"C0 and C2 are one class," and we agree.',
                                                    "C5-positive"))
    c5_silent = not bool(structural_mod.findings_for_text("Do not treat C0 or C2 as one class.",
                                                          "C5-negative"))
    c5_ok = c5_fire and c5_silent

    # ---- C3 no canonical writes
    sentinel_after = {p: sha256(p) for p in CANONICAL_WRITE_GUARD}
    c3_ok = sentinel_before == sentinel_after

    controls = {
        "C1_harness_reproduction": {"ok": c1_ok, "detail": c1,
                                    "note": "must reproduce the published APPLIED/PRE/PROSEFIX corpus C numbers and corpus A PASS"},
        "C2_determinism": {"ok": c2_ok, "note": "corpus A and C scoring byte-identical on double run"},
        "C3_no_canonical_write": {"ok": c3_ok, "before": sentinel_before, "after": sentinel_after},
        "C4_holdout_battery": {"ok": primary["worker035_battery"]["all_pass"],
                               "pos_pass": primary["worker035_battery"]["pos_pass"],
                               "neg_pass": primary["worker035_battery"]["neg_pass"],
                               "rows": primary["worker035_battery"]["rows"]},
        "C5_directional_controls": {"ok": c5_ok, "quoted_endorsement_fires": c5_fire,
                                    "merge_prohibition_silent": c5_silent},
        "C6_pin_drift_guard": {"ok": True, "pins": pin_check},
    }
    controls_ok = all(v["ok"] for v in controls.values())

    # ---- live census
    live = live_census(structural_mod, ROOT / PINS["live_snapshot"][0], live_labels)
    live_refs = {name: live_census(mod, ROOT / PINS["live_snapshot"][0], live_labels)
                 for name, mod in arms.items() if name != "STRUCTURAL_R1"}

    result = {
        "schema": "worker-040/classsep-structural-results/v1",
        "task_id": "W040-A1-CLASSSEP-STRUCTURAL-01",
        "at": NOW, "actor": "worker-040", "node_id": "A1", "gate": "G-AUDIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "prereg": "artifacts/worker-040/classsep_structural/PRE_REGISTRATION.json",
        "primary_configuration": structural.VERSION,
        "pins": pin_check,
        "reference_arms": {k: v for k, v in all_arms.items() if k != "STRUCTURAL_R1"},
        "primary": primary,
        "live_census_structural": live,
        "live_census_reference_arms": live_refs,
        "adoption_bar": {"corpus_a_pass": corpus_a_pass, "sensitivity_ge_5of6": sens_ok,
                         "specificity_ge_9of10": spec_ok,
                         "cue_induced_fn_high_zero": cue_ok,
                         "live_metalinguistic_zero": len(live["labeled_fp_still_firing"]) == 0},
        "meets_bar": meets_bar,
        "controls": controls,
        "controls_ok": controls_ok,
        "result": "MEETS_BAR" if meets_bar else "BELOW_BAR_RECORDED",
    }
    (HERE / "results.json").write_text(json.dumps(result, indent=1, sort_keys=True))
    (HERE / "controls.json").write_text(json.dumps(controls, indent=1, sort_keys=True, default=str))

    print(f"{structural.VERSION} corpus A {ca['verdict']} {ca['tp']}/{ca['fn']}/{ca['tn']}/{ca['fp']}")
    print(f"{structural.VERSION} corpus C sens {cc['sensitivity']} spec {cc['specificity']}")
    print(f"{structural.VERSION} corpus D v1 cleared {d1['adversarial_cleared']} cue-FN-high {d1['cue_induced_fn_high']}")
    print(f"{structural.VERSION} corpus D v2 cleared {d2['adversarial_cleared']} cue-FN-high {d2['cue_induced_fn_high']}")
    print(f"{structural.VERSION} w098 {primary['worker098']['fn_fired']} fn, {primary['worker098']['fp_clean']} fp-clean")
    print(f"{structural.VERSION} holdout battery {primary['worker035_battery']['pos_pass']} pos, {primary['worker035_battery']['neg_pass']} neg")
    print(f"live structural hard {live['structural_hard']} labeled-FP still firing {live['labeled_fp_still_firing']}")
    print(f"meets_bar={meets_bar} controls_ok={controls_ok}")
    for k, v in controls.items():
        if not v["ok"]:
            print("CONTROL FAIL:", k)
    return 0 if controls_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
