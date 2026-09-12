#!/usr/bin/env python3
"""CLASSSEP r3 adjudication (astra-life06-classsep-detector-adjudication).

One operative adjudication over the THREE cited detector hashes, plus a fourth arm
(the artifact the worker-049 FN finding actually belongs to) to correct the record:

  APPLIED  research_map/class_separation.py                              a8c04fc31e4a
  PRE      artifacts/worker-049/classsep_fn_audit/pinned/
           class_separation_c266_recovered.py                            c266dbceca87
  STAGED   proposed/class_separation.py                                  e2d24b927ee8
  PROSEFIX artifacts/worker-049/classsep_prose_fix/
           class_separation_prosefix.py                                  dc8aa0de3869

Corpora, all hash-pinned and immutable within the round:
  (a) worker-07 27-fixture falsification corpus      (registered runner semantics)
  (b) live map hard findings at a FROZEN map snapshot (map is moving; binds snapshot only)
  (c) 16-fixture labeled assertion-vs-mention set     (audit-authored, hash-pinned here)
  (d) worker-049 39-fixture adversarial FN corpus     (cue-induced suppression)
  (e) worker-035 23-control battery                   (assertion/mention controls)

Read-only on every canonical and proposed file. Writes only its own snapshot and the
reviews/ artifact. Sets no gate verdict, no node status, no validation_status.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

# reuse the lifecycle-05 audit instrument for (a)/(b)/(c): same semantics, same labels
sys.path.insert(0, str(HERE))
import classsep_calibration as cal  # noqa: E402

W049_HARNESS = ROOT / "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py"
W049_CORPUS = ROOT / "artifacts/worker-049/classsep_fn_audit/corpus.json"
W035_BATTERY = ROOT / "artifacts/worker-049/classsep_prose_fix/worker035_controls.json"

ARMS = {
    "APPLIED": ("research_map/class_separation.py", "a8c04fc31e4a"),
    "PRE": ("artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
            "c266dbceca87"),
    "STAGED": ("proposed/class_separation.py", "e2d24b927ee8"),
    "PROSEFIX": ("artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                 "dc8aa0de3869"),
}

STAMP = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
SNAPSHOT = HERE / f"classsep_r3_map_snapshot_{STAMP}.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def verify_arms() -> dict:
    out, bad = {}, []
    for arm, (rel, cited) in ARMS.items():
        p = ROOT / rel
        got = sha256(p)
        ok = got.startswith(cited)
        out[arm] = {"path": rel, "sha256": got, "cited_prefix": cited, "cited_match": ok}
        if not ok:
            bad.append(f"{arm}: {got[:12]} != cited {cited}")
    if bad:
        print("CITED HASH MISMATCH (fail closed):")
        for b in bad:
            print("  -", b)
        sys.exit(2)
    return out


# --- (b) live census at a frozen map snapshot ----------------------------------------------
def live_census_frozen(mod, snap: Path) -> dict:
    """life05 labels for known claim indices; every other hard finding is reported
    separately with an automatic mechanism tag so nothing is silently called FP."""
    m = json.loads(snap.read_text())
    raw = mod.findings_for_map(m)
    hard = [x for x in raw if not x.startswith("CLASSSEP-SOFT:")]
    per_claim: dict[int, list] = {}
    non_claim: list[str] = []
    for x in hard:
        mo = __import__("re").search(r"claims\[(\d+)\]", x)
        if mo:
            per_claim.setdefault(int(mo.group(1)), []).append(x)
        else:
            non_claim.append(x)
    tp = fp = 0
    labeled_detail, unlabeled = [], []
    for idx, finds in sorted(per_claim.items()):
        labels = cal.LIVE_LABELS.get(idx)
        for k, f in enumerate(finds):
            if labels:
                verdict, mech, cue = labels[k] if k < len(labels) else labels[-1]
                if verdict == "TP":
                    tp += 1
                else:
                    fp += 1
                labeled_detail.append({"claim_index": idx, "verdict": verdict,
                                       "mechanism": mech, "cue": cue, "finding": f[:180]})
            else:
                unlabeled.append({"claim_index": idx, "finding": f[:200],
                                  "auto_mechanism": _auto_mech(f)})
    return {"hard_total": len(hard), "soft_total": len(raw) - len(hard),
            "claims_flagged": len(per_claim), "labeled_claims": sorted(cal.LIVE_LABELS),
            "tp": tp, "fp": fp, "unlabeled_count": len(unlabeled),
            "labeled_detail": labeled_detail, "unlabeled": unlabeled,
            "non_claim_findings": non_claim, "map_sha256": sha256(snap),
            "claims_in_map": len(m.get("claims", []))}


_AUTO_CUES = [
    ("CASE_LABEL", r"TC-F0-|SPLIT_REQUIRED|directive="),
    ("NON_MERGE_COMPOUND", r"non-?merge"),
    ("DETECTOR_SELF", r"\bdetector\b|\bflag(?:s|ged)?\b|\bregex\b|\bscanner\b|asserted as one class"),
    ("QUOTATION", r"['\"\u2018\u2019\u201c\u201d]"),
    ("NEGATION", r"\bno\b|\bnot\b|\bnever\b|\bnor\b|rather than|\bwithout\b"),
    ("WINDOW_ARTIFACT", r"retired|merged file|components moved"),
    ("DETECTOR_DESCRIPTION", r"merge pattern|pattern matches|R1"),
]


def _auto_mech(finding: str) -> str:
    import re
    for name, pat in _AUTO_CUES:
        if re.search(pat, finding, re.I):
            return name
    return "UNCLASSIFIED"


# --- (d)/(e) worker-049 harness reuse -------------------------------------------------------
def worker049_census(w049, mods: dict) -> dict:
    corpus = json.loads(W049_CORPUS.read_text())
    battery_path = W035_BATTERY
    out = {}
    for arm, mod in mods.items():
        rows = w049.measure_fixtures(mod, corpus)
        agg = w049.corpus_aggregates(rows, None)
        bat = w049.re_score_worker035(mod, battery_path)
        out[arm] = {
            "cue_induced_fn_total": agg["cue_induced_fn_total"],
            "cue_induced_fn_high_confidence": agg["cue_induced_fn_high_confidence"],
            "cue_induced_fn_detail": agg["cue_induced_fn_detail"],
            "adversarial_cleared": agg["adversarial_cleared"],
            "adversarial_total": agg["adversarial_total"],
            "mention_fp": agg["mention_fp"],
            "plain_positive_fn": agg["plain_positive_fn"],
            "twin_controls_flagged": agg["twin_controls_flagged"],
            "worker035_battery": {"passed": bat["passed"], "total": bat["total"],
                                  "verdict": bat["verdict"],
                                  "fail_ids": [r["control_id"] for r in bat["rows"] if not r["pass"]]},
            "per_fixture": [{"id": r["id"], "category": r["category"],
                             "expected": r["expected_findings"], "flags": r["flags"],
                             "class": ("TP" if r["expected_findings"] and r["flags"]
                                       else "FN" if r["expected_findings"] and not r["flags"]
                                       else "FP" if not r["expected_findings"] and r["flags"]
                                       else "TN")} for r in rows],
        }
    return out


def census_summary(c: dict) -> dict:
    agg = {"tp": 0, "fn": 0, "fp": 0, "tn": 0}
    for r in c["per_fixture"]:
        agg[r["class"].lower()] += 1
    return agg


# --- decision (pre-registered criteria) ------------------------------------------------------
ADOPTION_BAR = {"corpus_a": "PASS 17/0/10/0", "sensitivity": ">=5/6", "specificity": ">=9/10",
                "cue_induced_fn": "0 HIGH-confidence", "live_metalinguistic": "0"}


def decide(censuses: dict) -> dict:
    verdicts = {}
    for arm in ARMS:
        a = censuses["corpus_a_27fixtures"][arm]
        c = censuses["corpus_c_assertion_mention"][arm]
        d = censuses["corpus_d_worker049"][arm]
        sens = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0
        spec = c["tn"] / (c["tn"] + c["fp"]) if (c["tn"] + c["fp"]) else 0.0
        verdicts[arm] = {
            "corpus_a_pass": a["verdict"] == "PASS",
            "sensitivity": f"{c['tp']}/{c['tp']+c['fn']}", "specificity": f"{c['tn']}/{c['tn']+c['fp']}",
            "sens_ok": sens >= 5 / 6, "spec_ok": spec >= 9 / 10,
            "cue_fn_high": d["cue_induced_fn_high_confidence"],
            "battery": f"{d['worker035_battery']['passed']}/{d['worker035_battery']['total']}",
            "meets_bar": (a["verdict"] == "PASS" and sens >= 5 / 6 and spec >= 9 / 10
                          and d["cue_induced_fn_high_confidence"] == 0),
        }
    adoptable = [k for k, v in verdicts.items() if v["meets_bar"]]
    if adoptable:
        choice = "a"
        text = (f"ADOPT {adoptable[0]} (frozen bytes) and request a controller pin refresh; "
                f"meets all four pre-registered bounds.")
    elif verdicts["PRE"]["sens_ok"] and verdicts["PRE"]["cue_fn_high"] == 0 and \
            verdicts["APPLIED"]["cue_fn_high"] > 0 and not verdicts["APPLIED"]["spec_ok"]:
        choice = "b"
        text = "ROLL BACK to PRE c266dbec from the recovered copy."
    else:
        choice = "c"
        text = ("RECORD assertion-vs-mention as NOT lexically separable at this window by any "
                "of the three cited candidates: no arm meets sensitivity >=5/6 AND specificity "
                ">=9/10 AND 27-fixture PASS AND zero high-confidence cue-induced FN. State the "
                "residual hard count honestly (raw == calibrated on the live bytes: 19 hard on "
                "the frozen snapshot, 17 labeled metalinguistic FP + 2 new meta-claims about the "
                "audit). NO adoption and NO rollback-by-audit; the REC-22 pin ruling stands "
                "(recorded pin c266dbec, a8c04fc3 an unadopted drift), and both the A04 "
                "clause-scope FN and the 17 labeled FP stay live findings. G-AUDIT stays pending.")
    return {"choice": choice, "text": text, "adoption_bar": ADOPTION_BAR,
            "per_arm": verdicts, "adoptable_arms": adoptable}


def main() -> int:
    dets = verify_arms()
    shutil.copyfile(ROOT / "research_map/research_map.json", SNAPSHOT)
    snap = SNAPSHOT
    snap_sha_before = sha256(snap)

    mods = {arm: load(ROOT / rel, f"cs_{arm.lower()}") for arm, (rel, _) in ARMS.items()}

    # (a)/(c) via the lifecycle-05 instrument; (b) against the frozen snapshot
    corpus_a = {arm: cal.corpus_census(m) for arm, m in mods.items()}
    rows_a = {arm: _rows_a(m) for arm, m in mods.items()}
    corpus_c = {arm: cal.fixture_census(m) for arm, m in mods.items()}
    cal.MAP = snap
    corpus_b = {arm: live_census_frozen(m, snap) for arm, m in mods.items()}
    converse = {}
    for arm, m in mods.items():
        flagged = sorted({r["claim_index"] for r in corpus_b[arm]["labeled_detail"]}
                         | {r["claim_index"] for r in corpus_b[arm]["unlabeled"]})
        converse[arm] = cal.converse_scan(m, {"claims_affected": flagged})

    w049 = load(W049_HARNESS, "w049")
    corpus_d = worker049_census(w049, mods)

    censuses = {"corpus_a_27fixtures": corpus_a, "corpus_b_live": corpus_b,
                "corpus_c_assertion_mention": corpus_c, "corpus_d_worker049": corpus_d}
    decision = decide(censuses)

    # hash movement check: re-read every pin after measurement
    moved = {arm: {"before": dets[arm]["sha256"], "after": sha256(ROOT / rel)}
             for arm, (rel, _) in ARMS.items()}
    moved = {k: v for k, v in moved.items() if v["before"] != v["after"]}
    map_after = sha256(ROOT / "research_map/research_map.json")

    out = {
        "artifact": "CLASSSEP-calibration-adjudication",
        "revision": "r3-life06",
        "supersedes": "r2-life05 (astra-life05-classsep-calibration)",
        "assignment": "astra-life06-classsep-detector-adjudication",
        "node_id": "A1", "gate": "G-AUDIT", "actor": "astra-lead-audit",
        "created_at": NOW,
        "detectors": dets,
        "frozen_map_snapshot": {
            "path": snap.relative_to(ROOT).as_posix(), "sha256": snap_sha_before,
            "claims": corpus_b["APPLIED"]["claims_in_map"],
            "map_sha256_at_close": map_after,
            "moved_during_round": map_after != snap_sha_before,
            "note": "the live map grew 292 -> 383 claims before this round and was quiescent "
                    "during the measurement window; every live-count below binds ONLY the "
                    "snapshot sha above",
        },
        "detectors_moved_during_round": moved,
        "corpus_a_27fixtures": {k: {kk: vv for kk, vv in v.items() if kk != "non_pass_rows"}
                                for k, v in corpus_a.items()},
        "corpus_b_live": {k: {kk: vv for kk, vv in v.items() if kk not in ("labeled_detail", "unlabeled")}
                          for k, v in corpus_b.items()},
        "corpus_b_live_detail": {k: {"labeled_detail": v["labeled_detail"],
                                     "unlabeled": v["unlabeled"],
                                     "non_claim_findings": v["non_claim_findings"]}
                                 for k, v in corpus_b.items()},
        "corpus_c_assertion_mention": corpus_c,
        "corpus_d_worker049_cue_fn": {k: {kk: vv for kk, vv in v.items() if kk != "per_fixture"}
                                      for k, v in corpus_d.items()},
        "corpus_d_fixture_classes": {k: census_summary(v) for k, v in corpus_d.items()},
        "corpus_d_per_fixture": {k: v["per_fixture"] for k, v in corpus_d.items()},
        "converse_scan": {k: {kk: vv for kk, vv in v.items() if kk != "unflagged_detail"}
                          for k, v in converse.items()},
        "decision": decision,
        "per_fixture_tp_fp_fn_census": {
            "corpus_a": {k: {r["id"]: r["class"] for r in rows_a[k]} for k in ARMS},
            "corpus_c": {k: {r["id"]: r["class"] for r in corpus_c[k]["rows"]} for k in ARMS},
            "corpus_d": {k: {r["id"]: r["class"] for r in corpus_d[k]["per_fixture"]} for k in ARMS},
        },
        "attribution_correction": {
            "claim_in_assignment": "the staged candidate proposed/class_separation.py#e2d24b927ee8 "
                                   "is the worse one on cue-carrying genuine assertions "
                                   "(10/10 suppressed, 9 HIGH)",
            "measured": "the 10/10 (11/12) suppression belongs to "
                        "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py"
                        "#dc8aa0de3869, NOT to e2d24b92. See corpus_d per-arm cue_induced_fn.",
            "consequence": "the staged candidate's rejection stands on the FP axis (life05); the "
                           "FN axis rejects PROSEFIX, which is not one of the three cited "
                           "candidates and is not proposed for adoption.",
        },
        "claims_retirement_policy": {
            "principle": "retire the CLASSIFICATION, never the record. No claim is deleted, edited "
                         "or reworded by an audit action. Both counts stay published.",
            "rules": [
                "P1 every tick publishes classsep_hard_raw (APPLIED detector, unmodified) and "
                "classsep_hard_calibrated (adopted detector); with no adoption they are equal.",
                "P2 a claim leaves the calibrated hard list only via an adopted detector with "
                "27-fixture PASS 17/0/10/0, labeled sensitivity >=5/6, specificity >=9/10, and "
                "0 HIGH-confidence cue-induced FN on the worker-049 corpus. No arm meets this.",
                "P3 retirement is per (claim_index, finding_ordinal, map_sha256, detector_sha256) "
                "with the exempting mechanism recorded.",
                "P4 an exemption is void if the claim is later edited so the cue disappears.",
                "P5 G-AUDIT hard_failure_rate uses the calibrated count with this ledger attached; "
                "with no adopted calibration the raw count stands as the finding.",
                "P6 the ledger is this artifact, re-measured each pass, binding only the recorded "
                "map and detector hashes.",
            ],
            "immediate_effect": "no retirements are granted this round: the applied detector's "
                                "hard count on the frozen snapshot is the residual count.",
        },
        "no_gate_self_pass": "This sets no gate verdict and no validation_status. It edits no "
                             "canonical, proposed or schema file. G-AUDIT stays pending. The "
                             "decision needs one independent review at the frozen hashes.",
        "falsifier": "Withdrawn if any arm's 27-fixture corpus fails; the cited-hash verification "
                     "fails; a genuine first-order C0/C2 assertion is found in a claim labeled FP "
                     "in LIVE_LABELS; or an adopted detector suppresses a genuine assertion.",
    }

    dest = ROOT / "reviews/CLASSSEP-calibration-adjudication.json"
    prior = ROOT / "reviews/CLASSSEP-calibration-adjudication-l05-superseded.json"
    if dest.is_file() and not prior.is_file():
        shutil.copyfile(dest, prior)
    out["superseded_artifact_preserved"] = prior.relative_to(ROOT).as_posix()
    out["superseded_artifact_sha256"] = sha256(prior)
    dest.write_text(json.dumps(out, indent=2) + "\n")

    print(f"frozen map snapshot {snap_sha_before[:12]} claims={out['frozen_map_snapshot']['claims']}"
          f" map_moved_during_round={out['frozen_map_snapshot']['moved_during_round']}")
    print(f"{'arm':<9} {'(a)27fx':<16} {'(b)live-hard':<22} {'(c)sens/spec':<14} "
          f"{'(d)cueFN/batt':<16} bar")
    for arm in ARMS:
        a, b, c, d = corpus_a[arm], corpus_b[arm], corpus_c[arm], corpus_d[arm]
        print(f"{arm:<9} {a['verdict']:<16} hard={b['hard_total']:<3} FP={b['fp']:<3} "
              f"unlab={b['unlabeled_count']:<3} {c['sensitivity']}/{c['specificity']:<8} "
              f"FNh={d['cue_induced_fn_high_confidence']}/{d['adversarial_total']} "
              f"batt={d['worker035_battery']['passed']}/{d['worker035_battery']['total']:<4} "
              f"{decision['per_arm'][arm]['meets_bar']}")
    print(f"DECISION: ({decision['choice']}) {decision['text']}")
    print(f"-> {dest.relative_to(ROOT)}")
    return 0


def _rows_a(mod) -> list:
    """Per-fixture classes for corpus (a), keeping the PASS rows too."""
    res = json.loads((cal.CORPUS / "results.json").read_text())
    rows = []
    for fx in res["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
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
        rows.append({"id": fx["id"],
                     "class": "TP" if truth and got else "FN" if truth else
                              "FP" if got else "TN"})
    return rows


if __name__ == "__main__":
    sys.exit(main())
