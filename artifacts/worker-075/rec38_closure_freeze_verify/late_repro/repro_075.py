#!/usr/bin/env python3
"""worker-075 independent read-only reproduction of the r3 CLASSSEP adjudication.

Assignment: astra-life07-classsep-adjudication-review (node A1, gate G-AUDIT).
Reviewer is a non-author: worker-075 did not write the detector, the adjudication
script, the calibration module, or any of the corpora.

Read-only on every cited file. Writes ONLY tmp/w075_classsep_review/.
No detector write, no schema/ledger/claim edit, no gate self-pass.

Reproduces:
  (i)   27-fixture regression per arm (corpus A)
  (ii)  APPLIED live census at the frozen map snapshot f344ed2aaea5 (corpus B)
  (iii) sens/spec table + adoption bar (corpus C + corpus D)
  (iv)  attribution correction prosefix dc8aa0de3869 vs staged e2d24b92
  (v)   detector bytes a8c04fc31e4a stable; void e36b0d644ca7 absent
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.dont_write_bytecode = True  # never write .pyc anywhere

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "tmp/w075_classsep_review"
CST = timezone(timedelta(hours=8))

CITED = {
    "adjudication_json": (
        "reviews/CLASSSEP-calibration-adjudication.json",
        "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1"),
    "adjudication_script": (
        "artifacts/audit/classsep_r3_adjudication.py",
        "fc92f4eac503d4d493e80e03ac63f7688e3e580fe71f3684d46de923e6f67f07"),
    "map_snapshot": (
        "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
        "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"),
    "pre_detector": (
        "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
        "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"),
    "applied_detector": (
        "research_map/class_separation.py",
        "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"),
}
AUX = {
    "staged_detector": (
        "proposed/class_separation.py",
        "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819"),
    "prosefix_detector": (
        "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
        "dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470"),
    "calibration_module": (
        "artifacts/audit/classsep_calibration.py",
        "8f2efd262f97b53a50c33a698d57074b83b4df0c2793f5ff7799648bea958464"),
    "w049_harness": (
        "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py",
        None),
    "w049_corpus": (
        "artifacts/worker-049/classsep_fn_audit/corpus.json",
        "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "w035_battery": (
        "artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
        "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"),
    "w07_results": (
        "artifacts/worker-07/class_separation_falsification/results.json",
        "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"),
    "void_detector_evidence": (
        "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
        "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"),
    "cf29_forensics": (
        "runtime/state/controller_verification/cf29-detector-write-forensics.json", None),
    "life07_decisions": (
        "runtime/state/controller_verification/astra-lifecycle-07-decisions.json", None),
}

ARMS = {
    "APPLIED": "research_map/class_separation.py",
    "PRE": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    "STAGED": "proposed/class_separation.py",
    "PROSEFIX": "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_pins() -> dict:
    out, bad = {}, []
    for key, (rel, want) in {**CITED, **AUX}.items():
        got = sha256(ROOT / rel)
        rec = {"path": rel, "sha256": got, "expected": want,
               "match": (got == want) if want else None}
        if want and got != want:
            bad.append(f"{key}: {got} != {want}")
        out[key] = rec
    if bad:
        print("CITED HASH MISMATCH (fail closed):")
        for b in bad:
            print("  -", b)
        raise SystemExit(2)
    return out


# ---------------------------------------------------------------- corpus A
def corpus_a(mods: dict) -> dict:
    res = json.loads((ROOT / "artifacts/worker-07/class_separation_falsification/results.json").read_text())
    assert len(res["fixtures"]) == 27, len(res["fixtures"])
    out = {}
    for arm, mod in mods.items():
        tp = fn = fp = tn = 0
        rows = []
        for fx in res["fixtures"]:
            p = ROOT / fx["fixture_path"]
            m = json.loads(p.read_text())
            det = mod.findings_for_map(m)
            for g in m.get("groups", []):
                for n in g.get("nodes", []):
                    art = n.get("artifact")
                    if art and (ROOT / art).is_file():
                        det += mod.findings_for_text((ROOT / art).read_text(errors="replace"),
                                                     f"artifact {art}")
            got, truth = bool(det), bool(fx["is_class_merge"])
            cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
            tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
            rows.append({"id": fx["id"], "surface": fx.get("surface"), "class": cls,
                         "truth": truth, "fired": got})
        out[arm] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
                    "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
                    "rows": rows}
    return {"n_fixtures": len(res["fixtures"]),
            "results_sha256": sha256(ROOT / "artifacts/worker-07/class_separation_falsification/results.json"),
            "arms": out}


# ---------------------------------------------------------------- corpus C
def corpus_c(mods: dict, cal) -> dict:
    fixtures = cal.ASSERTION_MENTION_FIXTURES
    out = {}
    for arm, mod in mods.items():
        tp = fn = fp = tn = 0
        rows = []
        for fid, truth, text in fixtures:
            got = bool(mod.findings_for_text(text, f"fixture {fid}"))
            cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
            tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
            rows.append({"id": fid, "expect_merge_assertion": truth, "fired": got,
                         "class": cls, "text": text})
        out[arm] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
                    "sensitivity": f"{tp}/{tp+fn}", "specificity": f"{tn}/{tn+fp}",
                    "rows": rows}
    return {"n_fixtures": len(fixtures), "fixtures_from": "artifacts/audit/classsep_calibration.py::ASSERTION_MENTION_FIXTURES",
            "arms": out}


# ---------------------------------------------------------------- corpus B
def corpus_b(mods: dict, cal, snap_path: Path) -> dict:
    snap = json.loads(snap_path.read_text())
    out = {}
    for arm, mod in mods.items():
        raw = mod.findings_for_map(snap)
        hard = [x for x in raw if not x.startswith("CLASSSEP-SOFT:")]
        per_claim, non_claim = {}, []
        for x in hard:
            mo = re.search(r"claims\[(\d+)\]", x)
            if mo:
                per_claim.setdefault(int(mo.group(1)), []).append(x)
            else:
                non_claim.append(x)
        tp = fp = 0
        labeled, unlabeled = [], []
        for idx, finds in sorted(per_claim.items()):
            labels = cal.LIVE_LABELS.get(idx)
            for k, f in enumerate(finds):
                if labels:
                    verdict, mech, cue = labels[k] if k < len(labels) else labels[-1]
                    tp += verdict == "TP"; fp += verdict != "TP"
                    labeled.append({"claim_index": idx, "verdict": verdict,
                                    "mechanism": mech, "cue": cue, "finding": f})
                else:
                    unlabeled.append({"claim_index": idx, "finding": f})
        out[arm] = {"hard_total": len(hard), "soft_total": len(raw) - len(hard),
                    "claims_flagged": len(per_claim), "tp": tp, "fp": fp,
                    "labeled_count": len(labeled), "unlabeled_count": len(unlabeled),
                    "labeled": labeled, "unlabeled": unlabeled,
                    "non_claim_findings": non_claim}
    # author-instrument cross-check on APPLIED
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("cs_r3", ROOT / "artifacts/audit/classsep_r3_adjudication.py")
    r3 = _ilu.module_from_spec(spec)
    spec.loader.exec_module(r3)
    author = r3.live_census_frozen(mods["APPLIED"], snap_path)
    return {"snapshot": {"path": snap_path.relative_to(ROOT).as_posix(),
                         "sha256": sha256(snap_path), "claims_in_map": len(snap.get("claims", []))},
            "arms": out, "author_instrument_crosscheck_APPLIED": {
                "hard_total": author["hard_total"], "fp": author["fp"],
                "unlabeled_count": author["unlabeled_count"],
                "claims_flagged": author["claims_flagged"],
                "unlabeled": author["unlabeled"]}}


# ---------------------------------------------------------------- corpus D
def corpus_d(mods: dict, w049) -> dict:
    corpus = json.loads((ROOT / "artifacts/worker-049/classsep_fn_audit/corpus.json").read_text())
    out = {}
    for arm, mod in mods.items():
        rows = w049.measure_fixtures(mod, corpus)
        agg = w049.corpus_aggregates(rows, None)
        bat = w049.re_score_worker035(mod, ROOT / "artifacts/worker-049/classsep_prose_fix/worker035_controls.json")
        per_fixture = []
        tp = fn = fp = tn = 0
        for r in rows:
            cls = ("TP" if r["expected_findings"] and r["flags"]
                   else "FN" if r["expected_findings"] and not r["flags"]
                   else "FP" if not r["expected_findings"] and r["flags"] else "TN")
            tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
            per_fixture.append({"id": r["id"], "category": r["category"],
                                "expected": r["expected_findings"], "flags": r["flags"],
                                "class": cls})
        out[arm] = {
            "cue_induced_fn_total": agg["cue_induced_fn_total"],
            "cue_induced_fn_high_confidence": agg["cue_induced_fn_high_confidence"],
            "cue_induced_fn_detail": agg["cue_induced_fn_detail"],
            "adversarial_total": agg["adversarial_total"],
            "adversarial_cleared": agg["adversarial_cleared"],
            "mention_fp": agg["mention_fp"],
            "plain_positive_fn": agg["plain_positive_fn"],
            "twin_controls_flagged": agg["twin_controls_flagged"],
            "battery": {"passed": bat["passed"], "total": bat["total"], "verdict": bat["verdict"],
                        "fail_ids": [r["control_id"] for r in bat["rows"] if not r["pass"]]},
            "fixture_classes": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
            "per_fixture": per_fixture,
        }
    return out


# ---------------------------------------------------------------- adoption bar
def adoption_bar(a: dict, c: dict, d: dict) -> dict:
    out = {}
    for arm in ARMS:
        ca, cc, cd = a["arms"][arm], c["arms"][arm], d[arm]
        sens_num, sens_den = map(int, cc["sensitivity"].split("/"))
        spec_num, spec_den = map(int, cc["specificity"].split("/"))
        sens_ok = sens_num / sens_den >= 5 / 6
        spec_ok = spec_num / spec_den >= 9 / 10
        corpus_a_pass = ca["verdict"] == "PASS"
        high = cd["cue_induced_fn_high_confidence"]
        out[arm] = {"corpus_a_verdict": ca["verdict"], "corpus_a_tp_fp_tn_fn":
                    [ca["tp"], ca["fp"], ca["tn"], ca["fn"]],
                    "sensitivity": cc["sensitivity"], "specificity": cc["specificity"],
                    "sens_ok": sens_ok, "spec_ok": spec_ok,
                    "cue_fn_high": high, "cue_fn_total": cd["cue_induced_fn_total"],
                    "cue_fn_ok": high == 0,
                    "meets_all_four": corpus_a_pass and sens_ok and spec_ok and high == 0}
    return out


# ---------------------------------------------------------------- converse scan
ASSERT_CUES = re.compile(
    r"(?:treat|cover|use|take|regard|is|are|as)\s+(?:the\s+)?(?:c\s*0\s*(?:or|and|/|,|\+)\s*c\s*2"
    r"|c\s*2\s*(?:or|and|/|,|\+)\s*c\s*0)\s*(?:merged|unified|single|one)?\s*class"
    r"|(?:c0c2|c2c0)\s+(?:is|are|as)\s+one\s+class"
    r"|(?:merge|merging|combine|unify)\s+(?:the\s+)?(?:c0\s+and\s+c2|c2\s+and\s+c0)"
    r"|(?:c0\s+and\s+c2|c2\s+and\s+c0)\s+(?:are|is|form)\s+(?:one|a single|the same)\s+class", re.I)


def converse_scan(snap_path: Path, flagged_by_arm: dict) -> dict:
    snap = json.loads(snap_path.read_text())
    out = {}
    for arm, flagged in flagged_by_arm.items():
        cands, unflagged = [], []
        for i, c in enumerate(snap["claims"]):
            st = c.get("statement") or ""
            if not isinstance(st, str):
                st = str(st)
            for mo in ASSERT_CUES.finditer(st):
                lo, hi = max(0, mo.start() - 80), min(len(st), mo.end() + 80)
                rec = {"claim_index": i, "already_flagged": i in flagged, "span": st[lo:hi]}
                cands.append(rec)
                if i not in flagged:
                    unflagged.append(rec)
        out[arm] = {"cue_matches": len(cands), "unflagged_candidates": len(unflagged),
                    "unflagged_detail": unflagged[:10]}
    return out


def main() -> int:
    pins = check_pins()
    cal = load(ROOT / "artifacts/audit/classsep_calibration.py", "cs_cal")
    w049 = load(ROOT / "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py", "w049")
    mods = {arm: load(ROOT / rel, f"cs_{arm.lower()}") for arm, rel in ARMS.items()}

    applied_sha_before = sha256(ROOT / "research_map/class_separation.py")
    snap_path = ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"

    a = corpus_a(mods)
    c = corpus_c(mods, cal)
    b = corpus_b(mods, cal, snap_path)
    d = corpus_d(mods, w049)
    bar = adoption_bar(a, c, d)

    flagged_by_arm = {arm: sorted({r["claim_index"] for r in b["arms"][arm]["labeled"]}
                                  | {r["claim_index"] for r in b["arms"][arm]["unlabeled"]})
                      for arm in ARMS}
    conv = converse_scan(snap_path, flagged_by_arm)

    applied_sha_after = sha256(ROOT / "research_map/class_separation.py")
    void_live = sha256(ROOT / "research_map/class_separation.py") == \
        "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"

    # author decision reproduction (pure functions, no writes)
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("cs_r3b", ROOT / "artifacts/audit/classsep_r3_adjudication.py")
    r3 = _ilu.module_from_spec(spec)
    spec.loader.exec_module(r3)
    censuses = {"corpus_a_27fixtures": {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                                        for k, v in a["arms"].items()},
                "corpus_c_assertion_mention": c["arms"],
                "corpus_d_worker049": {k: {**v, "worker035_battery": v["battery"]}
                                       for k, v in d.items()}}
    author_decision = r3.decide(censuses)

    out = {
        "task": "W075-CLASSSEP-R3-ADJUDICATION-REVIEW",
        "assignment": "astra-life07-classsep-adjudication-review",
        "reviewer": "worker-075",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "pins": pins,
        "corpus_a_27fixtures": a,
        "corpus_b_live": b,
        "corpus_c_assertion_mention": c,
        "corpus_d_worker049": d,
        "adoption_bar": bar,
        "converse_scan": conv,
        "detector_bytes": {
            "applied_sha_before": applied_sha_before,
            "applied_sha_after": applied_sha_after,
            "applied_stable": applied_sha_before == applied_sha_after == CITED["applied_detector"][1],
            "live_equals_void_e36b0d644ca": void_live,
            "void_evidence_sha256": pins["void_detector_evidence"]["sha256"],
        },
        "author_decision_crosscheck": author_decision,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "repro_results.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({
        "pins_ok": all(v["match"] is not False for v in pins.values()),
        "corpus_a": {k: f"{v['verdict']} {v['tp']}/{v['fp']}/{v['tn']}/{v['fn']}" for k, v in a["arms"].items()},
        "corpus_b_hard": {k: v["hard_total"] for k, v in b["arms"].items()},
        "corpus_b_applied_labeled_unlabeled": [b["arms"]["APPLIED"]["labeled_count"],
                                               b["arms"]["APPLIED"]["unlabeled_count"]],
        "corpus_c": {k: f"{v['sensitivity']} / {v['specificity']}" for k, v in c["arms"].items()},
        "corpus_d_high_fn": {k: v["cue_induced_fn_high_confidence"] for k, v in d.items()},
        "meets_all_four": {k: v["meets_all_four"] for k, v in bar.items()},
        "author_decision": author_decision["choice"],
        "applied_stable": applied_sha_before == applied_sha_after == CITED["applied_detector"][1],
        "live_equals_void": void_live,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
