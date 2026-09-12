#!/usr/bin/env python3
"""W095-CLASSSEP-DRIFT-R5-VERIFY-01 (worker-095, node A1, gate G-AUDIT).

ONE bounded, class-bound task: independent verification of the SECOND
post-adjudication move of the class-separation detector, to live bytes
`research_map/class_separation.py` sha256 e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed
(mtime 2026-09-12 01:06:12 +0800), measured against the pre-registered adoption bar
recorded in reviews/CLASSSEP-calibration-adjudication.json (r3-life06, decision (c)).

Independence: this runner re-implements the census aggregation itself and calls only
the detectors' public API (`findings`, `findings_for_map`, `findings_for_text`).
Corpus FIXTURE DATA is imported read-only from the pinned adjudication module; no
author scoring code (classsep_calibration.py census functions, run_fn_audit_049.py,
classsep_r3_adjudication.py) is imported or executed.

Arms:
  PRE       c266dbceca87  pre-drift canonical (recovered copy, REC-22 active pin)
  APPLIED   a8c04fc31e4a  first drift, measured by the r3 adjudication
  STAGED    e2d24b927ee8  proposed/class_separation.py
  PROSEFIX  dc8aa0de3869  worker-049 prosefix artifact (FN-rejected by r3)
  NEW_LIVE  e36b0d644ca7  live bytes after the 01:06:12 move  <-- subject

Corpora (all hash-pinned here, read-only):
  (a) worker-07 27-fixture falsification corpus
  (b) live hard findings on FROZEN map snapshot f344ed2aaea5 (frozen 01:03:24)
  (c) 16-fixture labeled assertion-vs-mention set (fixture data from the r3 module)
  (d) worker-049 39-fixture adversarial cue corpus + worker-035 23-control battery

Writes only under artifacts/worker-095/classsep_drift_r5_verify/. Sets no gate
verdict, no node status, no validation_status.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "evidence/raw"
RAW.mkdir(parents=True, exist_ok=True)
STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")

PRIMARY_CLASS_ID = "AF-SCC-C2-VAC-GEN"

ARMS = {
    "PRE": ("artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
            "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"),
    "APPLIED": ("artifacts/worker-032/classsep-prose-01/pinned/class_separation.a8c04fc31e4a.py",
                "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"),
    "STAGED": ("proposed/class_separation.py",
               "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819"),
    "PROSEFIX": ("artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                 "dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470"),
    "NEW_LIVE": ("artifacts/worker-095/classsep_drift_r5_verify/pinned/"
                 "class_separation.live.e36b0d644ca7.py",
                 "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"),
}
LIVE_CANONICAL = "research_map/class_separation.py"

PINS = {
    "worker07_results": ("artifacts/worker-07/class_separation_falsification/results.json",
                         "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"),
    "w049_corpus_v1": ("artifacts/worker-049/classsep_fn_audit/corpus.json",
                       "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "w035_battery": ("artifacts/worker-049/classsep_prose_fix/worker035_controls.json",
                     "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"),
    "map_snapshot_r3": ("artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json",
                        "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"),
    "r3_adjudication_module": ("artifacts/audit/classsep_calibration.py",
                               "8f2efd262f97b53a50c33a698d57074b83b4df0c2793f5ff7799648bea958464"),
    "r3_adjudication": ("reviews/CLASSSEP-calibration-adjudication.json",
                        "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1"),
}

ADOPTION_BAR = {
    "corpus_a": "PASS 17/0/10/0",
    "sensitivity": ">=5/6",
    "specificity": ">=9/10",
    "cue_induced_fn": "0 HIGH-confidence",
    "live_metalinguistic": "0",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_pins() -> dict:
    out, bad = {}, []
    for name, (rel, want) in PINS.items():
        got = sha256(ROOT / rel)
        ok = got == want
        out[name] = {"path": rel, "sha256": got, "expected": want, "match": ok}
        if not ok:
            bad.append(f"{name}: {got} != {want}")
    for arm, (rel, want) in ARMS.items():
        got = sha256(ROOT / rel)
        ok = got == want
        out[f"arm_{arm}"] = {"path": rel, "sha256": got, "expected": want, "match": ok}
        if not ok:
            bad.append(f"arm {arm}: {got} != {want}")
    if bad:
        print("PIN MISMATCH (fail closed):")
        for b in bad:
            print("  -", b)
        sys.exit(2)
    return out


# --- (a) 27-fixture falsification corpus -----------------------------------------------------
def corpus_a_census(mod, results: dict) -> dict:
    tp = fn = fp = tn = 0
    rows = []
    for fx in results["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.is_file():
            continue
        m = json.loads(p.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"),
                                                 f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        cls = ("TP" if truth and got else "FN" if truth else "FP" if got else "TN")
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fx["id"], "class": cls, "is_class_merge": truth, "fired": got})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": tp + fn + fp + tn,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "non_pass_rows": [r for r in rows if r["class"] not in ("TP", "TN")], "rows": rows}


# --- (c) 16-fixture labeled assertion-vs-mention set -----------------------------------------
def corpus_c_census(mod, fixtures: list) -> dict:
    tp = fn = fp = tn = 0
    rows = []
    for fid, truth, text in fixtures:
        got = bool(mod.findings_for_text(text, f"fixture {fid}"))
        cls = ("TP" if truth and got else "FN" if truth else "FP" if got else "TN")
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fid, "expect_merge_assertion": truth, "fired": got, "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(fixtures),
            "sensitivity": f"{tp}/{tp+fn}", "specificity": f"{tn}/{tn+fp}", "rows": rows}


# --- (d) worker-049 39-fixture adversarial corpus + worker-035 battery ------------------------
def corpus_d_census(mod, corpus: dict) -> dict:
    rows = []
    for fx in corpus["fixtures"]:
        prose = mod.findings({"statement": fx["text"], "class_id": PRIMARY_CLASS_ID},
                             f"fx:{fx['id']}", mode="prose")
        rows.append({"id": fx["id"], "category": fx["category"], "twin_of": fx.get("twin_of"),
                     "adversarial_cue": fx["adversarial_cue"], "expected_findings": fx["expected_findings"],
                     "confidence": fx["confidence"], "flags": len(prose) > 0})
    by_id = {r["id"]: r for r in rows}
    twin_by_adv = {r["twin_of"]: r["id"] for r in rows if r.get("twin_of")}
    cue_induced = []
    for r in rows:
        if r["category"] != "ADVERSARIAL_ASSERTION":
            continue
        tw = by_id.get(twin_by_adv.get(r["id"], ""))
        if tw is not None and (not r["flags"]) and tw["flags"]:
            cue_induced.append({"adversarial": r["id"], "twin": tw["id"],
                                "confidence": r["confidence"], "cue": r["adversarial_cue"]})
    adv = [r for r in rows if r["category"] == "ADVERSARIAL_ASSERTION"]
    twins = [r for r in rows if r["category"] == "TWIN_CONTROL"]
    mentions = [r for r in rows if r["category"] == "MENTION"]
    plain = [r for r in rows if r["category"] == "PLAIN_POSITIVE"]
    return {"adversarial_total": len(adv),
            "adversarial_cleared": [r["id"] for r in adv if not r["flags"]],
            "plain_positive_fn": [r["id"] for r in plain if not r["flags"]],
            "mention_fp": [r["id"] for r in mentions if r["flags"]],
            "twin_controls_flagged": f"{sum(1 for r in twins if r['flags'])}/{len(twins)}",
            "cue_induced_fn_total": len(cue_induced),
            "cue_induced_fn_high_confidence": sum(1 for c in cue_induced if c["confidence"] == "HIGH"),
            "cue_induced_fn_detail": cue_induced,
            "per_fixture": [{"id": r["id"], "category": r["category"], "flags": r["flags"]} for r in rows]}


def battery_census(mod, battery: dict) -> dict:
    rows = []
    passed = 0
    for c in battery["controls"]:
        expect_assertion = c["expect"].startswith("ASSERTION")
        got = len(mod.findings({"statement": c["text"], "class_id": PRIMARY_CLASS_ID},
                               f"control:{c['control_id']}", mode="prose")) > 0
        ok = got == expect_assertion
        passed += int(ok)
        rows.append({"control_id": c["control_id"], "expect_assertion": expect_assertion,
                     "measured_assertion": got, "pass": ok})
    return {"passed": passed, "total": len(rows),
            "verdict": "PASS" if passed == len(rows) else "DEFECTIVE",
            "fail_ids": [r["control_id"] for r in rows if not r["pass"]]}


# --- (b) live hard findings on the frozen snapshot --------------------------------------------
def corpus_b_census(mod, snapshot: dict, live_labels: dict) -> dict:
    raw = mod.findings_for_map(snapshot)
    hard = [x for x in raw if not x.startswith("CLASSSEP-SOFT:")]
    per_claim, non_claim = {}, []
    for x in hard:
        mo = re.search(r"claims\[(\d+)\]", x)
        (per_claim.setdefault(int(mo.group(1)), []) if mo else non_claim).append(x)
    tp = fp = 0
    labeled, unlabeled = [], []
    for idx, finds in sorted(per_claim.items()):
        labels = live_labels.get(idx)
        for k, f in enumerate(finds):
            if labels:
                verdict, mech, cue = labels[k] if k < len(labels) else labels[-1]
                tp += verdict == "TP"; fp += verdict != "TP"
                labeled.append({"claim_index": idx, "verdict": verdict, "mechanism": mech,
                                "cue": cue, "finding": f[:180]})
            else:
                unlabeled.append({"claim_index": idx, "finding": f[:200]})
    return {"hard_total": len(hard), "soft_total": len(raw) - len(hard),
            "claims_flagged": len(per_claim), "labeled_claims": sorted(live_labels),
            "tp": tp, "fp": fp, "unlabeled_count": len(unlabeled),
            "unlabeled": unlabeled, "non_claim_findings": non_claim,
            "labeled_detail": labeled,
            "map_sha256": sha256(ROOT / PINS["map_snapshot_r3"][0]),
            "claims_in_map": len(snapshot.get("claims", []))}


# --- authorization / provenance check ----------------------------------------------------------
def authorization_check(live_sha: str) -> dict:
    events = ROOT / "research_map/events.jsonl"
    adjudication = json.loads((ROOT / PINS["r3_adjudication"][0]).read_text())
    hits, classsep_events = 0, []
    with events.open(errors="replace") as fh:
        for line in fh:
            if live_sha in line:
                hits += 1
            if "class_separation.py" in line:
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                classsep_events.append({"created_at": o.get("created_at"), "actor": o.get("actor"),
                                        "event_type": o.get("event_type"), "event_id": o.get("event_id")})
    classsep_events.sort(key=lambda x: str(x.get("created_at")))
    return {
        "live_sha256": live_sha,
        "event_stream": "research_map/events.jsonl",
        "event_stream_sha256_at_read": sha256(events),
        "events_binding_live_sha256": hits,
        "last_5_classsep_events": classsep_events[-5:],
        "adjudicated_applied_sha256": adjudication["detectors"]["APPLIED"]["sha256"],
        "active_pin_sha256": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
        "active_pin_source": "research_map/research_map.json frozen_artifacts[class_separation.py] "
                             "(REC-22: pin stays c266dbec; a8c04fc3 unadopted drift)",
        "live_equals_adjudicated_applied": live_sha == adjudication["detectors"]["APPLIED"]["sha256"],
        "live_equals_active_pin": live_sha ==
            "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    }


def main() -> int:
    pins = verify_pins()
    live_sha_before = sha256(ROOT / LIVE_CANONICAL)
    if live_sha_before != ARMS["NEW_LIVE"][1]:
        print(f"LIVE MOVED BEFORE RUN: {live_sha_before}")
        return 2

    cal = load_module(ROOT / PINS["r3_adjudication_module"][0], "pinned_r3_fixture_data")
    fixtures_c = list(cal.ASSERTION_MENTION_FIXTURES)
    live_labels = dict(cal.LIVE_LABELS)
    results_a = json.loads((ROOT / PINS["worker07_results"][0]).read_text())
    corpus_d = json.loads((ROOT / PINS["w049_corpus_v1"][0]).read_text())
    battery = json.loads((ROOT / PINS["w035_battery"][0]).read_text())
    snapshot = json.loads((ROOT / PINS["map_snapshot_r3"][0]).read_text())

    mods = {arm: load_module(ROOT / rel, f"cs_{arm.lower()}") for arm, (rel, _) in ARMS.items()}

    censuses = {"corpus_a": {}, "corpus_b": {}, "corpus_c": {}, "corpus_d": {}, "battery": {}}
    for arm, mod in mods.items():
        censuses["corpus_a"][arm] = corpus_a_census(mod, results_a)
        censuses["corpus_b"][arm] = corpus_b_census(mod, snapshot, live_labels)
        censuses["corpus_c"][arm] = corpus_c_census(mod, fixtures_c)
        censuses["corpus_d"][arm] = corpus_d_census(mod, corpus_d)
        censuses["battery"][arm] = battery_census(mod, battery)

    per_arm, adopter = {}, []
    for arm in ARMS:
        a, b, c, d, e = (censuses["corpus_a"][arm], censuses["corpus_b"][arm],
                         censuses["corpus_c"][arm], censuses["corpus_d"][arm],
                         censuses["battery"][arm])
        sens_n, sens_d = map(int, c["sensitivity"].split("/"))
        spec_n, spec_d = map(int, c["specificity"].split("/"))
        meets = (a["verdict"] == "PASS" and sens_n / sens_d >= 5 / 6 and spec_n / spec_d >= 9 / 10
                 and d["cue_induced_fn_high_confidence"] == 0)
        per_arm[arm] = {
            "corpus_a": {"tp": a["tp"], "fn": a["fn"], "fp": a["fp"], "tn": a["tn"], "verdict": a["verdict"]},
            "corpus_c": {"sensitivity": c["sensitivity"], "specificity": c["specificity"],
                         "tp": c["tp"], "fn": c["fn"], "fp": c["fp"], "tn": c["tn"]},
            "corpus_d": {"cue_induced_fn_high": d["cue_induced_fn_high_confidence"],
                         "cue_induced_fn_total": d["cue_induced_fn_total"],
                         "adversarial_cleared": d["adversarial_cleared"],
                         "mention_fp": d["mention_fp"]},
            "battery": {"passed": e["passed"], "total": e["total"], "verdict": e["verdict"]},
            "live": {"hard_total": b["hard_total"], "fp": b["fp"], "tp": b["tp"],
                     "unlabeled": b["unlabeled_count"], "claims_flagged": b["claims_flagged"]},
            "meets_adoption_bar": meets,
        }
        if meets:
            adopter.append(arm)

    auth = authorization_check(live_sha_before)
    live_sha_after = sha256(ROOT / LIVE_CANONICAL)
    moved_during = live_sha_after != live_sha_before

    # independent cross-check against the r3 adjudication's published per-arm numbers
    r3 = json.loads((ROOT / PINS["r3_adjudication"][0]).read_text())
    xcheck = {}
    for arm, key in (("PRE", "PRE"), ("APPLIED", "APPLIED"), ("STAGED", "STAGED"),
                     ("PROSEFIX", "PROSEFIX")):
        pub_a = r3["corpus_a_27fixtures"][key]
        pub_c = r3["corpus_c_assertion_mention"][key]
        pub_d = r3["corpus_d_worker049_cue_fn"][key]
        pub_b = r3["corpus_b_live"][key]
        mine = per_arm[arm]
        xcheck[arm] = {
            "corpus_a_match": [mine["corpus_a"]["tp"], mine["corpus_a"]["fn"],
                               mine["corpus_a"]["fp"], mine["corpus_a"]["tn"]]
                              == [pub_a["tp"], pub_a["fn"], pub_a["fp"], pub_a["tn"]],
            "corpus_c_match": [mine["corpus_c"]["tp"], mine["corpus_c"]["fn"],
                               mine["corpus_c"]["fp"], mine["corpus_c"]["tn"]]
                              == [pub_c["tp"], pub_c["fn"], pub_c["fp"], pub_c["tn"]],
            "cue_fn_high_match": mine["corpus_d"]["cue_induced_fn_high"]
                                 == pub_d["cue_induced_fn_high_confidence"],
            "battery_match": [mine["battery"]["passed"], mine["battery"]["total"]]
                             == [pub_d["worker035_battery"]["passed"], pub_d["worker035_battery"]["total"]],
            "live_hard_match": mine["live"]["hard_total"] == pub_b["hard_total"],
        }
    all_xcheck = all(all(v.values()) for v in xcheck.values())

    # per-arm deltas of NEW_LIVE vs APPLIED on the two drift-sensitive corpora
    def arm_detail(arm, corpus):
        return censuses[corpus][arm]
    delta = {
        "corpus_c_rows_APPLIED": {r["id"]: r["class"] for r in arm_detail("APPLIED", "corpus_c")["rows"]},
        "corpus_c_rows_NEW_LIVE": {r["id"]: r["class"] for r in arm_detail("NEW_LIVE", "corpus_c")["rows"]},
        "live_hard_APPLIED": arm_detail("APPLIED", "corpus_b")["hard_total"],
        "live_hard_NEW_LIVE": arm_detail("NEW_LIVE", "corpus_b")["hard_total"],
        "live_unlabeled_APPLIED": arm_detail("APPLIED", "corpus_b")["unlabeled"],
        "live_unlabeled_NEW_LIVE": arm_detail("NEW_LIVE", "corpus_b")["unlabeled"],
        "cue_fn_detail_NEW_LIVE": arm_detail("NEW_LIVE", "corpus_d")["cue_induced_fn_detail"],
    }

    verdict = {
        "schema": "worker-095/classsep-drift-r5-verify/v1",
        "task_id": "W095-CLASSSEP-DRIFT-R5-VERIFY-01",
        "actor": "worker-095",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "created_at": NOW,
        "subject": {"path": LIVE_CANONICAL, "sha256": live_sha_before,
                    "mtime": datetime.fromtimestamp(
                        (ROOT / LIVE_CANONICAL).stat().st_mtime).astimezone().isoformat(timespec="seconds")},
        "predecessor_adjudicated": r3["detectors"]["APPLIED"]["sha256"],
        "active_pin": auth["active_pin_sha256"],
        "authorization": auth,
        "adoption_bar_r3": ADOPTION_BAR,
        "arms": per_arm,
        "adoptable_arms_measured": adopter,
        "r3_published_numbers_independently_reproduced": all_xcheck,
        "r3_crosscheck": xcheck,
        "new_live_vs_applied": delta,
        "drift_during_run": moved_during,
        "live_sha256_after": live_sha_after,
        "pins": pins,
        "headline": (
            f"live_bytes={live_sha_before[:12]} != adjudicated_APPLIED="
            f"{r3['detectors']['APPLIED']['sha256'][:12]} != active_pin=c266dbecaa87; "
            f"NEW_LIVE corpus_a={per_arm['NEW_LIVE']['corpus_a']['verdict']}, "
            f"sens/spec={per_arm['NEW_LIVE']['corpus_c']['sensitivity']}/"
            f"{per_arm['NEW_LIVE']['corpus_c']['specificity']}, "
            f"cueFN_high={per_arm['NEW_LIVE']['corpus_d']['cue_induced_fn_high']}, "
            f"battery={per_arm['NEW_LIVE']['battery']['passed']}/{per_arm['NEW_LIVE']['battery']['total']}, "
            f"live_hard={per_arm['NEW_LIVE']['live']['hard_total']}, "
            f"meets_bar={per_arm['NEW_LIVE']['meets_adoption_bar']}"
        ),
        "falsifier": (
            "This receipt is withdrawn if: (i) the live canonical bytes are re-measured and do not hash "
            "to e36b0d644ca7 (unless a recorded controller artifact event binds the new bytes and the "
            "census is re-run at them); (ii) the pinned corpus files or the r3 adjudication artifact "
            "change hash; (iii) an author/controller event dated <= 2026-09-12T01:07:35+08:00 is produced "
            "that binds e36b0d644ca7 before the 01:06:12 write, or a pre-registration showing the "
            "e36b0d carve-out meets the adoption bar; (iv) the independent re-run of any arm does not "
            "reproduce that arm's r3-published corpus_a/corpus_c/corpus_d/live numbers."
        ),
        "no_gate_self_pass": ("Sets no gate verdict, node status or validation_status. Read-only on every "
                              "canonical, proposed, review and corpus file; the live detector was copied, "
                              "never written."),
    }

    (RAW / "pins_r5.json").write_text(json.dumps(pins, indent=2) + "\n")
    (RAW / "censuses_r5.json").write_text(json.dumps(censuses, indent=2) + "\n")
    (RAW / "authorization_r5.json").write_text(json.dumps(auth, indent=2) + "\n")
    (HERE / "verdict.json").write_text(json.dumps(verdict, indent=2) + "\n")

    print(verdict["headline"])
    print(f"independently reproduced r3 published numbers: {all_xcheck}")
    print(f"drift during run: {moved_during} (after={live_sha_after[:12]})")
    print(f"-> {HERE / 'verdict.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
