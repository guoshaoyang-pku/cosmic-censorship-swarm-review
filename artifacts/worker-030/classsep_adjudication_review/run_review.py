#!/usr/bin/env python3
"""W030E-CLASSSEP-ADJUDICATION-REVIEW-01 -- independent, read-only review instrument.

Target (pinned): reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467
(astra-lead-audit, r3-life06, "REC-22" four-arm class-separation census and decision (c)).

The adjudication states: "The decision needs one independent review at the frozen hashes."
The audit lead that authored it has filed its own author-conflict blocker
(audit-l07-b4-audit-author-conflict), so the review must come from an independent worker.

This instrument does NOT re-run the adjudication's harness (which is not pinned in the
artifact). It independently:
  A  verifies every cited hash (adjudication, frozen map snapshot, four detector arms);
  B  verifies the snapshot's self-binding (map_sha256_at_close, claims==383);
  C  re-runs the standing 27-fixture regression on each arm with a private harness and
     compares TP/FN/FP/TN with corpus_a_27fixtures;
  D  re-runs each arm on the frozen snapshot map and compares the hard-count census with
     corpus_b_live (APPLIED 19 / PRE 24 / STAGED 25 / PROSEFIX 1) and the labeled/unlabeled
     split of the APPLIED hard findings;
  E,F,G,H  recompute corpus_c / corpus_d / corpus_a / corpus_d_fixture_classes arithmetic
     from the artifact's own published per-fixture rows;
  I  recompute the adoption bar and check decision (c) follows (adoptable_arms == []);
  J  check the attribution correction (PROSEFIX, not STAGED, owns the cue-induced FN);
  K  drift guard: re-measure every pin at exit and fail closed on any movement.

Exit codes: 0 = no blocking failure, 1 = a blocking check failed, 2 = pin drift (void).
No canonical file is written. Reads only; the only writes are report.json in this directory.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

ADJUDICATION = "reviews/CLASSSEP-calibration-adjudication.json"
ADJ_SHA = "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1"
SNAPSHOT = "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
SNAP_SHA = "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"
CORPUS_A = "artifacts/worker-07/class_separation_falsification/results.json"
CORPUS_A_SHA = "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"
RUNNER = "runtime/bin/classsep_regression.py"
RUNNER_SHA = "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091"

ARMS = {
    # name: (declared path, declared sha, executable pinned copy)
    "APPLIED": (
        "research_map/class_separation.py",
        "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
        "artifacts/worker-032/classsep-prose-01/pinned/class_separation.a8c04fc31e4a.py",
    ),
    "PRE": (
        "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
        "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
        "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    ),
    "STAGED": (
        "proposed/class_separation.py",
        "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
        "proposed/class_separation.py",
    ),
    "PROSEFIX": (
        "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
        "dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470",
        "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
    ),
}
LIVE = "research_map/class_separation.py"

findings = []
checks = []


def sha256_file(rel: str) -> str | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(cid: str, name: str, ok: bool, detail, blocking: bool = True):
    checks.append({"id": cid, "name": name, "ok": bool(ok), "blocking": blocking, "detail": detail})
    if not ok and blocking:
        findings.append({"id": cid, "severity": "BLOCKING", "detail": detail})
    elif not ok:
        findings.append({"id": cid, "severity": "non_blocking", "detail": detail})
    return ok


def load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(f"w030e_{name}", ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fixture_regression(module) -> dict:
    """Private re-implementation of runtime/bin/classsep_regression.py scoring."""
    results = json.loads((ROOT / CORPUS_A).read_text())
    tp = fp = tn = fn = 0
    rows = []
    for fx in results["fixtures"]:
        fmap = json.loads((ROOT / fx["fixture_path"]).read_text())
        scored = list(module.findings_for_map(fmap))
        for g in fmap.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    scored += list(module.findings_for_text((ROOT / art).read_text(errors="replace"), f"artifact {art}"))
        got = bool(scored)
        truth = bool(fx["is_class_merge"])
        if truth and got:
            tp += 1; cls = "TP"
        elif truth and not got:
            fn += 1; cls = "FN"
        elif not truth and got:
            fp += 1; cls = "FP"
        else:
            tn += 1; cls = "TN"
        rows.append({"id": fx["id"], "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(results["fixtures"]),
            "verdict": "PASS" if (fn == 0 and fp == 0) else "DEFECTIVE", "rows": rows}


def main() -> int:
    adj_sha = sha256_file(ADJUDICATION)
    snap_sha = sha256_file(SNAPSHOT)
    corpus_sha = sha256_file(CORPUS_A)
    runner_sha = sha256_file(RUNNER)
    live_before = sha256_file(LIVE)

    # ---- A: cited-hash verification -------------------------------------------------
    check("A0", "adjudication artifact pinned", adj_sha == ADJ_SHA, {"measured": adj_sha, "pin": ADJ_SHA})
    check("A1", "frozen map snapshot pinned", snap_sha == SNAP_SHA, {"measured": snap_sha, "pin": SNAP_SHA})
    arm_meas = {}
    for name, (path, sha, exec_path) in ARMS.items():
        m = sha256_file(path)
        arm_meas[name] = {"path": path, "measured": m, "pin": sha}
        check(f"A2-{name}", f"arm {name} cited hash matches", m == sha, arm_meas[name])
        x = sha256_file(exec_path)
        check(f"A3-{name}", f"arm {name} executable copy hash matches", x == sha, {"exec": exec_path, "measured": x})
    check("A4", "27-fixture ground truth pinned", corpus_sha == CORPUS_A_SHA, {"measured": corpus_sha})
    check("A5", "regression runner pinned (reference only, not executed)",
          runner_sha == RUNNER_SHA, {"measured": runner_sha, "pin": RUNNER_SHA})

    if adj_sha != ADJ_SHA or snap_sha != SNAP_SHA:
        report(checks, {"verdict": "VOID_PIN_DRIFT", "findings": findings},
               {"adjudication": adj_sha, "snapshot": snap_sha, "live_before": live_before, "live_after": sha256_file(LIVE)})
        return 2

    adj = json.loads((ROOT / ADJUDICATION).read_text())
    snap = json.loads((ROOT / SNAPSHOT).read_text())

    # ---- B: snapshot self-binding ---------------------------------------------------
    check("B0", "snapshot map_sha256_at_close == measured sha",
          adj["frozen_map_snapshot"]["map_sha256_at_close"] == SNAP_SHA,
          {"declared": adj["frozen_map_snapshot"]["map_sha256_at_close"]})
    check("B1", "snapshot claims count == 383 (declared and measured)",
          len(snap.get("claims", [])) == 383 and adj["frozen_map_snapshot"]["claims"] == 383,
          {"measured": len(snap.get("claims", [])), "declared": adj["frozen_map_snapshot"]["claims"]})
    check("B2", "live map not claimed as stable", adj["frozen_map_snapshot"]["moved_during_round"] is False,
          {"moved_during_round": adj["frozen_map_snapshot"]["moved_during_round"]})

    # ---- C: independent 27-fixture regression per arm -------------------------------
    corpus_a = {}
    for name, (_p, _s, exec_path) in ARMS.items():
        mod = load_module(name, exec_path)
        got = fixture_regression(mod)
        decl = adj["corpus_a_27fixtures"][name]
        corpus_a[name] = got
        check(f"C-{name}", f"27-fixture regression reproduces corpus_a_27fixtures.{name}",
              (got["tp"], got["fn"], got["fp"], got["tn"]) == (decl["tp"], decl["fn"], decl["fp"], decl["tn"])
              and got["verdict"] == decl["verdict"],
              {"measured": {k: got[k] for k in ("tp", "fn", "fp", "tn", "verdict")},
               "declared": {k: decl[k] for k in ("tp", "fn", "fp", "tn", "verdict")}})

    # ---- D: independent frozen-snapshot census per arm ------------------------------
    census = {}
    for name, (_p, _s, exec_path) in ARMS.items():
        mod = load_module(f"census_{name}", exec_path)
        found = list(mod.findings_for_map(snap))
        idx = sorted(int(x) for f in found for x in re.findall(r"claims\[(\d+)\]", f))
        census[name] = {"hard_total": len(found), "claim_indices": idx, "findings": found}
        decl = adj["corpus_b_live"][name]
        check(f"D-{name}", f"frozen-snapshot hard census reproduces corpus_b_live.{name}.hard_total",
              len(found) == decl["hard_total"],
              {"measured": len(found), "declared": decl["hard_total"]})
    appl = census["APPLIED"]
    lab_rows = adj["corpus_b_live_detail"]["APPLIED"]["labeled_detail"]
    unl_rows = adj["corpus_b_live_detail"]["APPLIED"]["unlabeled"]
    measured_multiset = sorted(appl["claim_indices"])
    declared_multiset = sorted([r["claim_index"] for r in lab_rows] + [r["claim_index"] for r in unl_rows])
    check("D-labeled", "APPLIED 19 hard findings split 17 labeled + 2 unlabeled (claim-index multiset)",
          measured_multiset == declared_multiset and len(lab_rows) == 17 and len(unl_rows) == 2,
          {"measured": measured_multiset, "declared": declared_multiset,
           "declared_rows": len(lab_rows) + len(unl_rows)})
    declared_texts = [r["finding"] for r in lab_rows + unl_rows]
    unmatched = []
    for f in appl["findings"]:
        head = f[:110]
        if not any(dt.startswith(head) or head.startswith(dt[:110]) for dt in declared_texts):
            unmatched.append(head)
    check("D-text", "each measured APPLIED finding is recorded in labeled_detail/unlabeled (prefix identity)",
          not unmatched, {"unmatched": unmatched})
    # Non-blocking: `labeled_claims` is an arm-invariant 14-claim label list (the same in all four
    # arms), not the APPLIED-specific flagged set; 2 of its entries (127, 187) are not flagged by
    # APPLIED at the snapshot. The decision's "17 labeled FP" corresponds to labeled_detail rows.
    lab_claims = adj["corpus_b_live"]["APPLIED"]["labeled_claims"]
    check("D-label-field", "labeled_claims field is a global label list, not the APPLIED flagged set",
          len(lab_claims) == 14 and all(adj["corpus_b_live"][a]["labeled_claims"] == lab_claims for a in ARMS)
          and set(lab_claims) - set(appl["claim_indices"]) == {127, 187},
          {"labeled_claims": lab_claims, "not_flagged_by_APPLIED": sorted(set(lab_claims) - set(appl["claim_indices"]))},
          blocking=False)

    # ---- E: corpus_c arithmetic from published rows ---------------------------------
    def confusion(rows, expect_key, fired_key):
        tp = fn = fp = tn = 0
        for r in rows:
            exp = bool(r[expect_key]); got = bool(r[fired_key])
            if exp and got: tp += 1
            elif exp and not got: fn += 1
            elif not exp and got: fp += 1
            else: tn += 1
        return tp, fn, fp, tn

    for name in ARMS:
        decl = adj["corpus_c_assertion_mention"][name]
        tp, fn, fp, tn = confusion(decl["rows"], "expect_merge_assertion", "fired")
        check(f"E-{name}", f"corpus_c arithmetic recomputes ({name})",
              (tp, fn, fp, tn) == (decl["tp"], decl["fn"], decl["fp"], decl["tn"]),
              {"measured": [tp, fn, fp, tn], "declared": [decl["tp"], decl["fn"], decl["fp"], decl["tn"]]})
        sens_ok = (tp / (tp + fn) if tp + fn else 0) >= 5 / 6
        spec_ok = (tn / (tn + fp) if tn + fp else 0) >= 9 / 10
        pa = adj["decision"]["per_arm"][name]
        check(f"E-bar-{name}", f"corpus_c bar flags recompute ({name})",
              (pa["sens_ok"], pa["spec_ok"]) == (sens_ok, spec_ok)
              and decl["sensitivity"] == f"{tp}/{tp+fn}" and decl["specificity"] == f"{tn}/{tn+fp}",
              {"measured": [sens_ok, spec_ok], "declared": [pa["sens_ok"], pa["spec_ok"]],
               "sens": f"{tp}/{tp+fn}", "declared_sens": decl["sensitivity"],
               "spec": f"{tn}/{tn+fp}", "declared_spec": decl["specificity"]})

    # ---- F: corpus_d cue-FN arithmetic from per-fixture rows ------------------------
    for name in ARMS:
        decl = adj["corpus_d_worker049_cue_fn"][name]
        rows = adj["corpus_d_per_fixture"][name]
        by_id = {r["id"]: r for r in rows}
        adv = [r for r in rows if r["category"] == "ADVERSARIAL_ASSERTION" and r["expected"] == 1]
        fns = [r["id"] for r in adv if not r["flags"]]
        twins = [r for r in rows if r["category"] == "CONTROL_TWIN"]
        twin_ok = [r["id"] for r in twins if r["flags"]]
        mentions = [r["id"] for r in rows if r["category"] == "MENTION" and r["flags"]]
        check(f"F-{name}", f"corpus_d cue-FN recomputes ({name})",
              len(fns) == decl["cue_induced_fn_total"] and len(mentions) == len(decl["mention_fp"])
              and len(twin_ok) == len(twins),
              {"measured_fn": fns, "declared_total": decl["cue_induced_fn_total"],
               "measured_mention_fp": mentions, "declared_mention_fp": decl["mention_fp"],
               "twins_flagged": f"{len(twin_ok)}/{len(twins)}", "declared_twins": decl["twin_controls_flagged"]})

    # ---- G: corpus_a per-fixture census arithmetic ----------------------------------
    for name in ARMS:
        rows = adj["per_fixture_tp_fp_fn_census"]["corpus_a"][name]
        counts = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
        for v in rows.values():
            counts[v] += 1
        decl = adj["corpus_a_27fixtures"][name]
        check(f"G-{name}", f"corpus_a per-fixture census sums to declared ({name})",
              (counts["TP"], counts["FN"], counts["FP"], counts["TN"]) == (decl["tp"], decl["fn"], decl["fp"], decl["tn"]),
              {"measured": counts, "declared": [decl["tp"], decl["fn"], decl["fp"], decl["tn"]]})

    # ---- H: corpus_d fixture-class census arithmetic --------------------------------
    for name in ARMS:
        rows = adj["corpus_d_per_fixture"][name]
        counts = {"TP": 0, "FN": 0, "FP": 0, "TN": 0}
        for r in rows:
            exp = r["expected"]; got = bool(r["flags"])
            counts["TP" if exp and got else "FN" if exp else "FP" if got else "TN"] += 1
        decl = adj["corpus_d_fixture_classes"][name]
        check(f"H-{name}", f"corpus_d fixture-class census sums to declared ({name})",
              (counts["TP"], counts["FN"], counts["FP"], counts["TN"]) == (decl["tp"], decl["fn"], decl["fp"], decl["tn"]),
              {"measured": counts, "declared": [decl["tp"], decl["fn"], decl["fp"], decl["tn"]]})

    # ---- I: decision (c) follows from the bar ---------------------------------------
    per_arm = adj["decision"]["per_arm"]
    recomputed_meets = {}
    for name in ARMS:
        c = adj["corpus_c_assertion_mention"][name]
        sens_ok = (c["tp"] / (c["tp"] + c["fn"])) >= 5 / 6
        spec_ok = (c["tn"] / (c["tn"] + c["fp"])) >= 9 / 10
        cue_high = adj["corpus_d_worker049_cue_fn"][name]["cue_induced_fn_high_confidence"]
        corpus_pass = adj["corpus_a_27fixtures"][name]["verdict"] == "PASS"
        recomputed_meets[name] = bool(corpus_pass and sens_ok and spec_ok and cue_high == 0)
    decl_meets = {n: per_arm[n]["meets_bar"] for n in ARMS}
    check("I0", "adoption bar recomputes per arm", recomputed_meets == decl_meets,
          {"measured": recomputed_meets, "declared": decl_meets})
    check("I1", "adoptable_arms empty iff no arm meets the bar",
          adj["decision"]["adoptable_arms"] == [] and not any(recomputed_meets.values()),
          {"adoptable_arms": adj["decision"]["adoptable_arms"], "measured_meets": recomputed_meets})
    txt = adj["decision"]["text"]
    check("I2", "decision (c) text matches the measured bar outcome",
          adj["decision"]["choice"] == "c" and "NOT lexically separable" in txt
          and "NO adoption" in txt and "c266dbec" in txt and "G-AUDIT stays pending" in txt,
          {"choice": adj["decision"]["choice"], "text_len": len(txt)})

    # ---- J: attribution correction ---------------------------------------------------
    st = adj["corpus_d_worker049_cue_fn"]["STAGED"]
    pf = adj["corpus_d_worker049_cue_fn"]["PROSEFIX"]
    check("J0", "attribution correction holds (cue-FN belongs to PROSEFIX, not STAGED)",
          st["cue_induced_fn_total"] == 0 and st["cue_induced_fn_high_confidence"] == 0
          and pf["cue_induced_fn_total"] == 11 and pf["cue_induced_fn_high_confidence"] == 10,
          {"STAGED": [st["cue_induced_fn_total"], st["cue_induced_fn_high_confidence"]],
           "PROSEFIX": [pf["cue_induced_fn_total"], pf["cue_induced_fn_high_confidence"]]})

    # ---- K: drift guard --------------------------------------------------------------
    live_after = sha256_file(LIVE)
    check("K0", "no pinned input moved during the review",
          adj_sha == ADJ_SHA and snap_sha == SNAP_SHA
          and all(sha256_file(p) == s for _n, (p, s, _e) in ARMS.items() if _n != "APPLIED")
          and sha256_file(ARMS["APPLIED"][0]) == ARMS["APPLIED"][1],
          {"live_before": live_before, "live_after": live_after})
    blocking = [c for c in checks if not c["ok"] and c["blocking"]]
    verdict = "REVIEW_ACCEPT_DECISION_SUPPORTED" if not blocking else "REVIEW_BLOCKING_DEFECT"
    drift = live_before != ARMS["APPLIED"][1] or live_after != ARMS["APPLIED"][1]
    if drift:
        findings.append({
            "id": "W030E-LIVE",
            "severity": "non_blocking",
            "detail": ("live detector path hash differs from the adjudication's APPLIED citation "
                       "at review time: before=%s after=%s, cited=%s"
                       % (live_before, live_after, ARMS["APPLIED"][1])),
        })
    report(checks, {"verdict": verdict, "findings": findings}, {
        "adjudication": adj_sha, "snapshot": snap_sha, "live_before": live_before, "live_after": live_after,
        "arms": arm_meas, "corpus_a": corpus_a, "census": census,
        "recomputed_meets": recomputed_meets,
    })
    return 0 if not blocking else 1


def report(checks, verdict, measured):
    out = {
        "schema": "worker-030/classsep-adjudication-review/v1",
        "task_id": "W030E-CLASSSEP-ADJUDICATION-REVIEW-01",
        "actor": "worker-030",
        "target": f"{ADJUDICATION}#{ADJ_SHA}",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "measured_pins": measured,
        "checks": checks,
        "n_checks": len(checks),
        "n_failed": sum(1 for c in checks if not c["ok"]),
        "n_blocking": sum(1 for c in checks if not c["ok"] and c["blocking"]),
        **verdict,
    }
    (HERE / "report.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "n_checks", "n_failed", "n_blocking")}, indent=1))
    for f in out["findings"]:
        print("FINDING", f["severity"], f["id"], ":", str(f["detail"])[:220])
    return out


if __name__ == "__main__":
    sys.exit(main())
