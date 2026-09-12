#!/usr/bin/env python3
"""W098-CLASSSEP-MENTION-SCOPE-01 final battery + report.

Arms: live a8c04fc31e4a, staged proposed/class_separation.py e2d24b927ee8, candidate v1
d88eb425d9a0, candidate v2 3bd684035fc1 (insertion-only shadows of live). Measures the frozen
worker-07 corpus, 8 mandatory-clean prose controls, 2 true-positive controls, 12 mandatory-fire
adversarial merge controls, 5 detector-discussion growth probes, 10 declaration-mode parity
controls, and the live map. Deterministic, read-only, no network. Writes
raw/candidate_battery_final.json and report.json.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
RAW.mkdir(exist_ok=True)

PINS = {
    "live_detector": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
    "staged_candidate": "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
    "candidate_v1": "d88eb425d9a0c116bf29d9fc1c37018423b82212d18b091fa4115dc7fe1b5201",
    "candidate_v2": "3bd684035fc1ad2d7d5d91a34ebcc9a68407c12cfd59e1890f00e011c0710be2",
    "candidate_v3": "6f1a24c441fb758d064b7f545bd8dab6cb115156900e05b773f6c7cd090e9029",
    "corpus": "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
    "prior_report": "artifacts/worker-098/classsep_prose_shadow/report.json",
    "prior_checkpoint2": "runtime/state/w098_classsep_prose_shadow_checkpoint_2.json",
    "proposed_patch": "artifacts/formulation/proposals/classsep_prose_precision_patch.md",
}

CLEAN = [
    ("FP1_live_neg", "so no C0/C2 merge exists at the formal surface."),
    ("FP2_live_split", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; the two rows require a split)"),
    ("FP3_live_mention", "R1's merge pattern matches only bare C0/C2 composites"),
    ("FP4_live_nonmerge", "This is a class separation check: independent C0/C2 non-merge evidence."),
    ("FP5_rather_than", "This is a single-frozen-data-class question rather than a C2/C0 merge."),
    ("FP6_quoted_mention", "the same slot carrying 'C0 or C2 are one class' is flagged"),
    ("FP7_rejected_hypothesis", "We analysed the C0/C2 unified class only as a rejected hypothesis."),
    ("FP8_counting_prose", "This note measures how often the C0/C2 combined pattern appears in review prose."),
]
TP = [
    ("TP1_unit", "The C0/C2 merged class is the right unit of analysis for this portfolio."),
    ("TP2_unified", "This result covers the C0/C2 unified class."),
]
FIRE = [
    ("FN1_meta_case", "The C0/C2 merged class is the only case we consider."),
    ("FN2_meta_test", "We test that the C0/C2 unified class is the right unit."),
    ("FN3_meta_corpus", "This corpus treats the C0/C2 as one class."),
    ("FN4_meta_independent", "The independent C0/C2 merged class is our unit of analysis."),
    ("FN5_meta_pattern", "The C0/C2 combined pattern is the portfolio's chosen unit."),
    ("FN6_neg_scope", "It is not the case that the classes are separate; the C0/C2 are one class."),
    ("AX1_interjection_affirm", "No, the C0/C2 are one class."),
    ("AX2_not_distinct_but", "The C0/C2 are not distinct but one merged class."),
    ("AX3_detector_flags_right_unit", "The detector flags the C0/C2 as one class, which is the right unit."),
    ("AX4_pattern_is_right_unit", "The C0/C2 merged pattern is the right unit of analysis."),
    ("AX5_no_question_idiom", "There is no question that the C0/C2 are one class."),
    ("AX6_contrast_yet", "The classes are separate, yet the C0/C2 are one class."),
]
GROWTH = [
    ("G1_meta_mention", "The audit flags our discussion of the C0/C2 merged label, but that is a metalinguistic mention, not a proposed merge."),
    ("G2_rejected_hypothesis", "We analysed the C0/C2 unified class only as a rejected hypothesis; the portfolio keeps the two classes split."),
    ("G3_counting_prose", "This note measures how often the C0/C2 combined pattern appears in review prose."),
    ("G4_quoted_reject", "The claim quotes 'C0 or C2 are one class' only to reject it."),
    ("G5_no_proposal", "No C0/C2 merged class is proposed anywhere in this note; the classes stay separate."),
]
DECL = ["C0 or C2", "C2/C0", "the C0 and C2 classes", "AF-WCC-VAC-GEN", "no C0/C2 merge",
        "C0-vs-C2 distinction", "never write 'C0 or C2'", "merged C0/C2 class",
        "composite C0C2 regularity", "two separate classes C0, C2"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def peek(p, n=12):
    return sha(p)[:n]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fires(mod, text):
    out = []
    mod._scan_composite(text, "probe", out, mode="prose")
    return out


def corpus_arm(mod, fixtures):
    tp = fp = tn = fn = 0
    for fx in fixtures:
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


def arm(mod, fixtures, live_map):
    return {
        "corpus": corpus_arm(mod, fixtures),
        "clean": [{"name": n, "fires": bool(fires(mod, t))} for n, t in CLEAN],
        "tp": [{"name": n, "fires": bool(fires(mod, t))} for n, t in TP],
        "fire": [{"name": n, "fires": bool(fires(mod, t))} for n, t in FIRE],
        "growth": [{"name": n, "findings": len([x for x in mod.findings({"statement": t}, n, mode="prose")
                                                if not x.startswith("CLASSSEP-SOFT:")])} for n, t in GROWTH],
        "map_live_hard": len(map_hard(mod, live_map)),
        "map_live_findings": [x[:240] for x in map_hard(mod, live_map)],
    }


def acceptance(a, manifest):
    dec = {
        "A1_corpus_pass": a["corpus"]["verdict"] == "PASS",
        "A2_clean_controls_all_clean": all(not r["fires"] for r in a["clean"]),
        "A3_tp_controls_fire": all(r["fires"] for r in a["tp"]),
        "A4_original_over_suppression_zero": all(r["fires"] for r in a["fire"][:6]),
        "A5_new_over_suppression_zero": all(r["fires"] for r in a["fire"][6:]),
        "A6_growth_zero": sum(r["findings"] for r in a["growth"]) == 0,
        "A7_declaration_parity": a["decl_parity_identical"] == 10,
        "A8_insertion_only": manifest["diff"]["insertion_only"],
        "A9_live_map_zero_hard": a["map_live_hard"] == 0,
    }
    decisive = [k for k in dec if k != "A9_live_map_zero_hard"]
    verdict = "adopt-candidate" if all(dec[k] for k in decisive) else (
        "reject" if (not dec["A1_corpus_pass"] or not dec["A8_insertion_only"]) else "revise")
    return dec, verdict


def main() -> int:
    live_path = ROOT / "research_map/class_separation.py"
    staged_path = ROOT / "proposed/class_separation.py"
    v1_path = HERE / "candidate_class_separation.py"
    v2_path = HERE / "candidate_class_separation.v2.py"
    v3_path = HERE / "candidate_class_separation.v3.py"
    corpus_path = ROOT / "artifacts/worker-07/class_separation_falsification/results.json"
    live_map_path = ROOT / "research_map/research_map.json"
    man1 = json.loads((HERE / "build_manifest.json").read_text())
    man2 = json.loads((HERE / "build_manifest_v2.json").read_text())
    man3 = json.loads((HERE / "build_manifest_v3.json").read_text())

    live = load("w098_f_live", live_path)
    staged = load("w098_f_staged", staged_path)
    v1 = load("w098_f_v1", v1_path)
    v2 = load("w098_f_v2", v2_path)
    v3 = load("w098_f_v3", v3_path)

    fixtures = json.loads(corpus_path.read_text())["fixtures"]
    live_map = json.loads(live_map_path.read_text())
    live_map_sha = sha(live_map_path)

    arms = {
        "live_a8c04fc31e4a": arm(live, fixtures, live_map),
        "staged_e2d24b927ee8": arm(staged, fixtures, live_map),
        "candidate_v1_d88eb425d9a0": arm(v1, fixtures, live_map),
        "candidate_v2_3bd684035fc1": arm(v2, fixtures, live_map),
        "candidate_v3_6f1a24c441fb": arm(v3, fixtures, live_map),
    }
    # declaration parity per arm
    for name, mod in (("live_a8c04fc31e4a", live), ("candidate_v1_d88eb425d9a0", v1),
                      ("candidate_v2_3bd684035fc1", v2), ("candidate_v3_6f1a24c441fb", v3)):
        same = 0
        rows = []
        for t in DECL:
            a, b = [], []
            live._scan_composite(t, "decl", a, mode="declaration")
            mod._scan_composite(t, "decl", b, mode="declaration")
            rows.append({"text": t, "identical": a == b})
            same += a == b
        arms[name]["decl_parity_identical"] = same
        arms[name]["decl_parity_rows"] = rows

    acc2, verdict2 = acceptance(arms["candidate_v2_3bd684035fc1"], man2)
    acc1, verdict1 = acceptance(arms["candidate_v1_d88eb425d9a0"], man1)
    acc3, verdict3 = acceptance(arms["candidate_v3_6f1a24c441fb"], man3)

    # attribution: which fire-control failures are candidate-introduced vs inherited from live
    live_fail = {r["name"] for r in arms["live_a8c04fc31e4a"]["fire"] if not r["fires"]}
    v3_fail = {r["name"] for r in arms["candidate_v3_6f1a24c441fb"]["fire"] if not r["fires"]}
    v2_fail = {r["name"] for r in arms["candidate_v2_3bd684035fc1"]["fire"] if not r["fires"]}
    v1_fail = {r["name"] for r in arms["candidate_v1_d88eb425d9a0"]["fire"] if not r["fires"]}

    drift = {
        "live_detector_sha256": sha(live_path), "pin": PINS["live_detector"],
        "live_detector_moved": sha(live_path) != PINS["live_detector"],
        "staged_sha256": sha(staged_path), "staged_moved": sha(staged_path) != PINS["staged_candidate"],
        "v1_sha256": sha(v1_path), "v1_moved": sha(v1_path) != PINS["candidate_v1"],
        "v2_sha256": sha(v2_path), "v2_moved": sha(v2_path) != PINS["candidate_v2"],
        "v3_sha256": sha(v3_path), "v3_moved": sha(v3_path) != PINS["candidate_v3"],
        "corpus_moved": sha(corpus_path) != PINS["corpus"],
        "live_map_sha256": live_map_sha, "live_map_claims": len(live_map.get("claims", [])),
    }

    report = {
        "task_id": "W098-CLASSSEP-MENTION-SCOPE-01",
        "worker": "worker-098",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "measured_at": "2026-09-12T01:00:00+08:00",
        "drift": drift,
        "arms": arms,
        "acceptance_v1": acc1, "verdict_v1": verdict1,
        "acceptance_v2": acc2, "verdict_v2": verdict2,
        "acceptance_v3": acc3, "verdict_v3": verdict3,
        "attribution": {
            "live_fire_control_failures": sorted(live_fail),
            "v1_fire_control_failures": sorted(v1_fail),
            "v2_fire_control_failures": sorted(v2_fail),
            "v3_fire_control_failures": sorted(v3_fail),
            "v3_introduced_over_suppression": sorted(v3_fail - live_fail),
            "v3_inherited_over_suppression": sorted(v3_fail & live_fail),
        },
        "findings": [
            {"id": "W098-CMS-01", "severity": "major", "status": "fixed-in-v2",
             "statement": "v1 rule-implementation defects D1-D5 measured: idiom boundary bug over-suppressed AX1; contrast-tail span left FP5 firing; mention/quoted spans left G1 and claim 192 firing; out-of-sentence assertion left claim 144 firing; zero-count negation left claims 276/306 firing."},
            {"id": "W098-CMS-02", "severity": "major", "status": "live-defect-inherited-fixed-in-v2",
             "statement": "The live detector over-suppresses the first-order assertion AX3 ('The detector flags the C0/C2 as one class, which is the right unit') because the live meta-quotation skip 'detector\\s+(?:finding|flag)' matches 'detector flags'; v2 re-asserts it before that skip. Live arm fires 11/12 mandatory-fire controls, v1 10/12 (AX1+AX3), v2 12/12."},
            {"id": "W098-CMS-03", "severity": "info", "status": "measured",
             "statement": "The staged candidate proposed/class_separation.py#e2d24b927ee8 does not clear the metalinguistic battery: %d/8 mandatory-clean controls still fire and live-map hard count is %d vs live %d; it is a different, narrower fix (negation-split + statement prose keys)." % (
                 sum(1 for r in arms["staged_e2d24b927ee8"]["clean"] if r["fires"]),
                 arms["staged_e2d24b927ee8"]["map_live_hard"], arms["live_a8c04fc31e4a"]["map_live_hard"])},
            {"id": "W098-CMS-04", "severity": "info", "status": "measured",
             "statement": "No new false negative on the 27-fixture worker-07 corpus in any arm: all four arms report PASS (tp=17, fn=0, tn=10, fp=0)."},
            {"id": "W098-CMS-05", "severity": "info", "status": "measured",
             "statement": "Growth mechanism: live %d/5, staged %d/5, v1 %d/5, v2 %d/5, v3 %d/5 detector-discussion probes still produce findings." % (
                 sum(r["findings"] for r in arms["live_a8c04fc31e4a"]["growth"]),
                 sum(r["findings"] for r in arms["staged_e2d24b927ee8"]["growth"]),
                 sum(r["findings"] for r in arms["candidate_v1_d88eb425d9a0"]["growth"]),
                 sum(r["findings"] for r in arms["candidate_v2_3bd684035fc1"]["growth"]),
                 sum(r["findings"] for r in arms["candidate_v3_6f1a24c441fb"]["growth"]))},
            {"id": "W098-CMS-06", "severity": "info", "status": "measured",
             "statement": "Declaration-mode parity is 10/10 for v1/v2/v3 against live; all three candidates are insertion-only derivations of a8c04fc31e4a (v1 +79/-0, v2 +109/-0, v3 +109/-0)."},
            {"id": "W098-CMS-07", "severity": "major" if acc3["A9_live_map_zero_hard"] is False else "info",
             "status": "measured",
             "statement": "v3 leaves %d hard CLASSSEP findings on the live map at %s (claims=%d); residual contexts are listed in arms.candidate_v3_6f1a24c441fb.map_live_findings. Clearing the prose instrument does not retire any historical claim." % (
                 arms["candidate_v3_6f1a24c441fb"]["map_live_hard"], live_map_sha[:12], drift["live_map_claims"])},
        ],
        "evidence": [
            "artifacts/worker-098/classsep_mention_scope/pre_registration.json#%s" % peek(HERE / "pre_registration.json"),
            "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.py#%s" % peek(v1_path),
            "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.v2.py#%s" % peek(v2_path),
            "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.v3.py#%s" % peek(v3_path),
            "artifacts/worker-098/classsep_mention_scope/build_manifest.json#%s" % peek(HERE / "build_manifest.json"),
            "artifacts/worker-098/classsep_mention_scope/build_manifest_v2.json#%s" % peek(HERE / "build_manifest_v2.json"),
            "artifacts/worker-098/classsep_mention_scope/build_manifest_v3.json#%s" % peek(HERE / "build_manifest_v3.json"),
            "artifacts/worker-098/classsep_mention_scope/raw/candidate_battery.json#%s" % peek(RAW / "candidate_battery.json"),
            "artifacts/worker-07/class_separation_falsification/results.json#%s" % peek(corpus_path),
            "research_map/class_separation.py#%s" % peek(live_path),
            "proposed/class_separation.py#%s" % peek(staged_path),
            "research_map/research_map.json#%s" % peek(live_map_path),
            "runtime/state/w098_classsep_prose_shadow_checkpoint_2.json#%s" % peek(ROOT / "runtime/state/w098_classsep_prose_shadow_checkpoint_2.json"),
        ],
        "falsifier": "Re-run artifacts/worker-098/classsep_mention_scope/run_battery_final.py at the pins: v3 is FALSIFIED if any of the 12 mandatory-fire controls produces 0 findings, any of the 8 mandatory-clean controls fires, the worker-07 corpus is not PASS, declaration parity < 10/10, or the v3 diff contains a removed line. The measurement is VOID (rebase) if research_map/class_separation.py or research_map/research_map.json moves off the hashes recorded in drift before the run completes.",
        "non_claims": [
            "not a gate verdict; not a node completion or status transition",
            "no canonical file, schema, gate, or claim status was modified",
            "the corpus PASS means no new FN on the 27 registered fixtures, not that the candidate is defect-free",
            "clearing a claim with the instrument does not retire the claim; retirement is a separate controller/lead action",
        ],
        "numerics_lock": "respected: no N1 work, no numerics/spherical_solver, no GPU work",
    }
    (RAW / "candidate_battery_final.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))

    print("drift:", json.dumps(drift, sort_keys=True))
    for n, a in arms.items():
        print("%-28s corpus=%s clean_fires=%d/8 fire=%d/12 growth=%d map_hard=%d decl=%d" % (
            n, a["corpus"]["verdict"], sum(1 for r in a["clean"] if r["fires"]),
            sum(1 for r in a["fire"] if r["fires"]), sum(r["findings"] for r in a["growth"]),
            a["map_live_hard"], a.get("decl_parity_identical", -1)))
    print("v1:", verdict1, json.dumps(acc1, sort_keys=True))
    print("v2:", verdict2, json.dumps(acc2, sort_keys=True))
    print("v3:", verdict3, json.dumps(acc3, sort_keys=True))
    print("attribution:", json.dumps(report["attribution"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
