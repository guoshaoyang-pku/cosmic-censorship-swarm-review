#!/usr/bin/env python3
"""W098-CLASSSEP-MENTION-SCOPE-01 battery.

Three arms: live (research_map/class_separation.py), staged (proposed/class_separation.py),
candidate (candidate_class_separation.py, insertion-only shadow of live). Measures each arm on
the frozen worker-07 corpus (27 fixtures), 8 mandatory-clean prose controls, 2 true-positive
controls, 12 mandatory-fire adversarial merge controls, 5 detector-discussion growth probes,
10 declaration-mode parity controls, and the map (pinned snapshot + live). Read-only.

Deterministic, no network. Writes raw/candidate_battery.json and report.json.
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
sys.path.insert(0, str(ROOT / "research_map"))

PINS = {
    "live_detector": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
    "staged_candidate": "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
    "corpus": "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
}

CLEAN_CONTROLS = [
    ("FP1_live_neg", "so no C0/C2 merge exists at the formal surface."),
    ("FP2_live_split", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; the two rows require a split)"),
    ("FP3_live_mention", "R1's merge pattern matches only bare C0/C2 composites"),
    ("FP4_live_nonmerge", "This is a class separation check: independent C0/C2 non-merge evidence."),
    ("FP5_rather_than", "This is a single-frozen-data-class question rather than a C2/C0 merge."),
    ("FP6_quoted_mention", "the same slot carrying 'C0 or C2 are one class' is flagged"),
    ("FP7_rejected_hypothesis", "We analysed the C0/C2 unified class only as a rejected hypothesis."),
    ("FP8_counting_prose", "This note measures how often the C0/C2 combined pattern appears in review prose."),
]
TP_CONTROLS = [
    ("TP1_unit", "The C0/C2 merged class is the right unit of analysis for this portfolio."),
    ("TP2_unified", "This result covers the C0/C2 unified class."),
]
FIRE_CONTROLS = [
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
DECL_PARITY = [
    "C0 or C2", "C2/C0", "the C0 and C2 classes", "AF-WCC-VAC-GEN", "no C0/C2 merge",
    "C0-vs-C2 distinction", "never write 'C0 or C2'", "merged C0/C2 class",
    "composite C0C2 regularity", "two separate classes C0, C2",
]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


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


def arm(mod, fixtures, snap_map, live_map):
    return {
        "corpus": corpus_arm(mod, fixtures),
        "clean_controls": [{"name": n, "text": t, "fires": bool(fires(mod, t))} for n, t in CLEAN_CONTROLS],
        "tp_controls": [{"name": n, "text": t, "fires": bool(fires(mod, t))} for n, t in TP_CONTROLS],
        "fire_controls": [{"name": n, "text": t, "fires": bool(fires(mod, t))} for n, t in FIRE_CONTROLS],
        "growth": [{"name": n, "findings": len([x for x in mod.findings({"statement": t}, n, mode="prose")
                                                if not x.startswith("CLASSSEP-SOFT:" )])} for n, t in GROWTH],
        "map_snapshot_6d3f0f2792a2_hard": len(map_hard(mod, snap_map)),
        "map_live_hard": len(map_hard(mod, live_map)),
    }


def main() -> int:
    live_path = ROOT / "research_map/class_separation.py"
    staged_path = ROOT / "proposed/class_separation.py"
    cand_path = HERE / "candidate_class_separation.py"
    corpus_path = ROOT / "artifacts/worker-07/class_separation_falsification/results.json"
    snap_path = ROOT / "artifacts/worker-098/classsep_prose_shadow/snapshot/research_map.pinned.json"
    live_map_path = ROOT / "research_map/research_map.json"

    live_sha, staged_sha = sha(live_path), sha(staged_path)
    corpus_sha = sha(corpus_path)

    live = load("w098_ms_live", live_path)
    staged = load("w098_ms_staged", staged_path)
    cand = load("w098_ms_cand", cand_path)

    fixtures = json.loads(corpus_path.read_text())["fixtures"]
    snap_map = json.loads(snap_path.read_text())
    live_map = json.loads(live_map_path.read_text())
    live_map_sha = sha(live_map_path)

    arms = {"live": arm(live, fixtures, snap_map, live_map),
            "staged_e2d24b927ee8": arm(staged, fixtures, snap_map, live_map),
            "candidate_d88eb425d9a0": arm(cand, fixtures, snap_map, live_map)}

    # declaration-mode parity (candidate must equal live on all controls)
    parity = []
    for t in DECL_PARITY:
        a, b = [], []
        live._scan_composite(t, "decl", a, mode="declaration")
        cand._scan_composite(t, "decl", b, mode="declaration")
        parity.append({"text": t, "live": a, "candidate": b, "identical": a == b})

    # residual live hard findings for the report (truncated)
    residual = [x[:220] for x in map_hard(cand, live_map)]

    acc = arms["candidate_d88eb425d9a0"]
    acceptance = {
        "A1_corpus_pass": acc["corpus"]["verdict"] == "PASS",
        "A2_clean_controls_all_clean": all(not r["fires"] for r in acc["clean_controls"]),
        "A3_tp_controls_fire": all(r["fires"] for r in acc["tp_controls"]),
        "A4_original_over_suppression_zero": all(r["fires"] for r in acc["fire_controls"][:6]),
        "A5_new_over_suppression_zero": all(r["fires"] for r in acc["fire_controls"][6:]),
        "A6_growth_zero": sum(r["findings"] for r in acc["growth"]) == 0,
        "A7_declaration_parity": all(r["identical"] for r in parity),
        "A8_insertion_only": json.loads((HERE / "build_manifest.json").read_text())["diff"]["insertion_only"],
        "A9_live_map_zero_hard": acc["map_live_hard"] == 0,
    }
    decisive = [k for k in acceptance if k != "A9_live_map_zero_hard"]
    verdict = "adopt-candidate" if all(acceptance[k] for k in decisive) else (
        "reject" if (not acceptance["A1_corpus_pass"] or not acceptance["A8_insertion_only"]) else "revise")

    drift = {
        "live_detector_sha256": live_sha, "live_detector_pin": PINS["live_detector"],
        "live_detector_moved": live_sha != PINS["live_detector"],
        "staged_sha256": staged_sha, "staged_pin": PINS["staged_candidate"],
        "staged_moved": staged_sha != PINS["staged_candidate"],
        "corpus_sha256": corpus_sha, "corpus_pin": PINS["corpus"],
        "corpus_moved": corpus_sha != PINS["corpus"],
        "live_map_sha256": live_map_sha, "live_map_claims": len(live_map.get("claims", [])),
    }

    out = {
        "task_id": "W098-CLASSSEP-MENTION-SCOPE-01",
        "measured_at": "2026-09-12T00:58:00+08:00",
        "pins": PINS, "drift": drift, "arms": arms,
        "declaration_parity": parity,
        "acceptance_candidate": acceptance, "verdict_candidate": verdict,
        "residual_live_hard_findings_candidate": residual,
        "candidate_sha256": sha(cand_path),
        "candidate_build_manifest": json.loads((HERE / "build_manifest.json").read_text()),
    }
    (RAW / "candidate_battery.json").write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps({k: out[k] for k in ("drift", "verdict_candidate", "acceptance_candidate",
                                          "residual_live_hard_findings_candidate")}, indent=2, sort_keys=True))
    for arm_name, a in arms.items():
        print(arm_name, "corpus", a["corpus"], "clean_fires",
              sum(1 for r in a["clean_controls"] if r["fires"]), "fire_ok",
              sum(1 for r in a["fire_controls"] if r["fires"]), "/12", "growth",
              sum(r["findings"] for r in a["growth"]), "map_snap", a["map_snapshot_6d3f0f2792a2_hard"],
              "map_live", a["map_live_hard"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
