#!/usr/bin/env python3
"""Independent read-only reproduction for the worker-075 review of the r3 CLASSSEP
adjudication (card astra-life07-classsep-adjudication-review, node A1, gate G-AUDIT).

Target: reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467 (actor
astra-lead-audit; worker-075 is a non-author).

Frozen pins reproduced (all four cited arms + the corpora + the map snapshot):
  APPLIED  research_map/class_separation.py                          a8c04fc31e4a
  PRE      artifacts/worker-049/classsep_fn_audit/pinned/
           class_separation_c266_recovered.py                        c266dbceca87
  STAGED   proposed/class_separation.py                              e2d24b927ee8
  PROSEFIX artifacts/worker-049/classsep_prose_fix/
           class_separation_prosefix.py                              dc8aa0de3869

Reproduces:
  (i)   27-fixture regression (corpus a) at each cited arm, per-fixture classes;
  (ii)  APPLIED live census on the frozen map snapshot f344ed2aaea5:
        hard=19 = 17 labeled metalinguistic FP + 2 unlabeled DETECTOR_SELF claims;
  (iii) 16-fixture assertion-vs-mention (corpus c) sens/spec table + adoption bar;
  (iv)  worker-049 39-fixture cue-FN corpus (corpus d) + worker-035 23-control battery,
        attribution of the 10/10 (11/12) cue suppression to dc8aa0de3869, not e2d24b92;
  (v)   detector freeze: research_map/class_separation.py == a8c04fc31e4a before AND
        after, byte-distinct from the void e36b0d644ca7 which stays out.

READ-ONLY on every canonical, proposed, schema and ledger file. The r3 script
artifacts/audit/classsep_r3_adjudication.py is NOT executed because it rewrites
reviews/CLASSSEP-calibration-adjudication.json and copies a new snapshot. This script
writes only under artifacts/worker-075/classsep_adjudication_review/.

Exit codes: 0 = reproduced; 2 = cited-pin mismatch (fail closed -> inconclusive);
3 = internal inconsistency (e.g. aggregate/count disagreement).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

ADJ = ROOT / "reviews/CLASSSEP-calibration-adjudication.json"
ADJ_SCRIPT = ROOT / "artifacts/audit/classsep_r3_adjudication.py"
SNAP = ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
CAL_PATH = ROOT / "artifacts/audit/classsep_calibration.py"
W049_HARNESS = ROOT / "artifacts/worker-049/classsep_fn_audit/run_fn_audit_049.py"
W049_CORPUS = ROOT / "artifacts/worker-049/classsep_fn_audit/corpus.json"
W035_BATTERY = ROOT / "artifacts/worker-049/classsep_prose_fix/worker035_controls.json"
W07_RESULTS = ROOT / "artifacts/worker-07/class_separation_falsification/results.json"
VOID_EVIDENCE = ROOT / "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py"
CF29 = ROOT / "runtime/state/controller_verification/cf29-detector-write-forensics.json"

ARMS = {
    "APPLIED": ("research_map/class_separation.py", "a8c04fc31e4a"),
    "PRE": ("artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
            "c266dbceca87"),
    "STAGED": ("proposed/class_separation.py", "e2d24b927ee8"),
    "PROSEFIX": ("artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                 "dc8aa0de3869"),
}

PINS = {
    "adjudication": (ADJ, "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1"),
    "adjudication_script": (ADJ_SCRIPT, "fc92f4eac503d4d493e80e03ac63f7688e3e580fe71f3684d46de923e6f67f07"),
    "map_snapshot": (SNAP, "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749"),
    "calibration_module": (CAL_PATH, "8f2efd262f97b53a50c33a698d57074b83b4df0c2793f5ff7799648bea958464"),
    "w049_harness": (W049_HARNESS, "6e5306aafe7bccdf9eaf0cea63b6f6e65a564326b909a5f3a1e865a18a6dae36"),
    "w049_corpus": (W049_CORPUS, "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23"),
    "w035_battery": (W035_BATTERY, "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d"),
    "w07_results": (W07_RESULTS, "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452"),
    "void_detector_evidence": (VOID_EVIDENCE, "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"),
    "cf29_forensics": (CF29, "b573dcfdcc20c7ada64ac2e6ebd78787713d55343d9ae46298fa7b390dee9491"),
}

_AUTO_CUES = [
    ("CASE_LABEL", r"TC-F0-|SPLIT_REQUIRED|directive="),
    ("NON_MERGE_COMPOUND", r"non-?merge"),
    ("DETECTOR_SELF", r"\bdetector\b|\bflag(?:s|ged)?\b|\bregex\b|\bscanner\b|asserted as one class"),
    ("QUOTATION", r"['\"\u2018\u2019\u201c\u201d]"),
    ("NEGATION", r"\bno\b|\bnot\b|\bnever\b|\bnor\b|rather than|\bwithout\b"),
    ("WINDOW_ARTIFACT", r"retired|merged file|components moved"),
    ("DETECTOR_DESCRIPTION", r"merge pattern|pattern matches|R1"),
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def auto_mech(finding: str) -> str:
    for name, pat in _AUTO_CUES:
        if re.search(pat, finding, re.I):
            return name
    return "UNCLASSIFIED"


def pin_check() -> dict:
    out, bad = {}, []
    for name, (p, expected) in PINS.items():
        got = sha256(p)
        ok = got == expected
        out[name] = {"path": p.relative_to(ROOT).as_posix(), "sha256": got,
                     "expected": expected, "match": ok}
        if not ok:
            bad.append(f"{name}: {got[:12]} != {expected[:12]}")
    for arm, (rel, cited) in ARMS.items():
        got = sha256(ROOT / rel)
        ok = got.startswith(cited)
        out[f"arm_{arm}"] = {"path": rel, "sha256": got, "cited_prefix": cited, "match": ok}
        if not ok:
            bad.append(f"arm {arm}: {got[:12]} != cited {cited}")
    return {"pins": out, "bad": bad}


def rows_corpus_a(mod) -> list:
    """Per-fixture classes for corpus (a): registered worker-07 runner semantics."""
    res = json.loads((ROOT / "artifacts/worker-07/class_separation_falsification/results.json").read_text())
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
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        rows.append({"id": fx["id"], "class": cls, "surface": fx.get("surface"),
                     "is_class_merge": truth, "fired": got})
    return rows


def live_census_frozen(mod, snap: Path) -> dict:
    """(b) live hard-finding census on the FROZEN snapshot only.

    Known claim indices carry the adjudication's LIVE_LABELS; every other hard finding is
    reported separately with an automatic mechanism tag so nothing is silently called FP.
    """
    import importlib.util as _iu
    cal = load(CAL_PATH, "cal_for_live")
    m = json.loads(snap.read_text())
    raw = mod.findings_for_map(m)
    hard = [x for x in raw if not x.startswith("CLASSSEP-SOFT:")]
    per_claim: dict[int, list] = {}
    non_claim: list[str] = []
    for x in hard:
        mo = re.search(r"claims\[(\d+)\]", x)
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
                                  "auto_mechanism": auto_mech(f)})
    return {"hard_total": len(hard), "soft_total": len(raw) - len(hard),
            "claims_flagged": len(per_claim), "labeled_claims": sorted(cal.LIVE_LABELS),
            "tp": tp, "fp": fp, "unlabeled_count": len(unlabeled),
            "labeled_detail": labeled_detail, "unlabeled": unlabeled,
            "non_claim_findings": non_claim, "map_sha256": sha256(snap),
            "claims_in_map": len(m.get("claims", []))}


def corpus_d_census(w049, mods: dict) -> dict:
    corpus = json.loads(W049_CORPUS.read_text())
    out = {}
    for arm, mod in mods.items():
        rows = w049.measure_fixtures(mod, corpus)
        agg = w049.corpus_aggregates(rows, None)
        bat = w049.re_score_worker035(mod, W035_BATTERY)
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


def decide(censuses: dict) -> dict:
    verdicts = {}
    for arm in ARMS:
        a = censuses["corpus_a_27fixtures"][arm]
        c = censuses["corpus_c_assertion_mention"][arm]
        d = censuses["corpus_d_worker049"][arm]
        sens_num, sens_den = (int(x) for x in c["sensitivity"].split("/"))
        spec_num, spec_den = (int(x) for x in c["specificity"].split("/"))
        verdicts[arm] = {
            "corpus_a_pass": a["verdict"] == "PASS",
            "sensitivity": c["sensitivity"], "specificity": c["specificity"],
            "sens_ok": sens_num / sens_den >= 5 / 6,
            "spec_ok": spec_num / spec_den >= 9 / 10,
            "cue_fn_high": d["cue_induced_fn_high_confidence"],
            "battery": f"{d['worker035_battery']['passed']}/{d['worker035_battery']['total']}",
            "meets_bar": (a["verdict"] == "PASS" and sens_num / sens_den >= 5 / 6
                          and spec_num / spec_den >= 9 / 10
                          and d["cue_induced_fn_high_confidence"] == 0),
        }
    adoptable = [k for k, v in verdicts.items() if v["meets_bar"]]
    return {"choice": "a" if adoptable else "c", "adoptable_arms": adoptable,
            "per_arm": verdicts}


def compare_with_declared(adj: dict, measured: dict) -> dict:
    """Cell-by-cell comparison against the adjudication's declared numbers."""
    cells, mismatches = [], []

    def cell(name, declared, got):
        ok = declared == got
        cells.append({"cell": name, "declared": declared, "measured": got, "match": ok})
        if not ok:
            mismatches.append(name)

    for arm in ARMS:
        d = adj["corpus_a_27fixtures"][arm]
        m = measured["corpus_a_27fixtures"][arm]
        for k in ("tp", "fp", "tn", "fn", "verdict"):
            cell(f"A.{arm}.{k}", d[k], m[k])
        db = adj["corpus_b_live"][arm]
        mb = measured["corpus_b_live"][arm]
        for k in ("hard_total", "soft_total", "claims_flagged", "tp", "fp",
                  "unlabeled_count", "claims_in_map"):
            cell(f"B.{arm}.{k}", db[k], mb[k])
        cell(f"B.{arm}.map_sha256", db["map_sha256"], mb["map_sha256"])
        dc = adj["corpus_c_assertion_mention"][arm]
        mc = measured["corpus_c_assertion_mention"][arm]
        for k in ("tp", "fp", "tn", "fn", "sensitivity", "specificity"):
            cell(f"C.{arm}.{k}", dc[k], mc[k])
        dd = adj["corpus_d_worker049_cue_fn"][arm]
        md = measured["corpus_d_worker049_cue_fn"][arm]
        for k in ("cue_induced_fn_total", "cue_induced_fn_high_confidence",
                  "adversarial_cleared", "adversarial_total", "mention_fp",
                  "plain_positive_fn", "twin_controls_flagged"):
            cell(f"D.{arm}.{k}", dd[k], md[k])
        cell(f"D.{arm}.battery", dd["worker035_battery"]["passed"], md["worker035_battery"]["passed"])
        # per-fixture classes
        dper = adj["per_fixture_tp_fp_fn_census"]
        mper = measured["per_fixture_tp_fp_fn_census"]
        for corpus_key, arm_key in (("corpus_a", "corpus_a"), ("corpus_c", "corpus_c"),
                                    ("corpus_d", "corpus_d")):
            dmap = dper[corpus_key][arm]
            mmap = mper[arm_key][arm]
            if set(dmap) != set(mmap):
                mismatches.append(f"perfixture.{corpus_key}.{arm}.id_set")
                continue
            diffs = {k: (dmap[k], mmap[k]) for k in dmap if dmap[k] != mmap[k]}
            cells.append({"cell": f"PERFIXTURE.{corpus_key}.{arm}", "declared": len(dmap),
                          "measured": len(mmap), "match": not diffs, "diffs": diffs})
            if diffs:
                mismatches.append(f"perfixture.{corpus_key}.{arm}:{diffs}")
        # decision row
        dp = adj["decision"]["per_arm"][arm]
        mp = measured["decision"]["per_arm"][arm]
        for k in ("corpus_a_pass", "sensitivity", "specificity", "sens_ok", "spec_ok",
                  "cue_fn_high", "battery", "meets_bar"):
            cell(f"DECISION.{arm}.{k}", dp[k], mp[k])
    cell("DECISION.choice", adj["decision"]["choice"], measured["decision"]["choice"])
    cell("DECISION.adoptable_arms", adj["decision"]["adoptable_arms"],
         measured["decision"]["adoptable_arms"])
    return {"cells": cells, "n_cells": len(cells),
            "n_mismatch": len(mismatches), "mismatches": mismatches}


def attribution_check(measured: dict) -> dict:
    d = measured["corpus_d_worker049_cue_fn"]
    return {
        "prosefix_cue_fn_high": d["PROSEFIX"]["cue_induced_fn_high_confidence"],
        "prosefix_cue_fn_total": d["PROSEFIX"]["cue_induced_fn_total"],
        "prosefix_cleared": len(d["PROSEFIX"]["adversarial_cleared"]),
        "staged_cue_fn_high": d["STAGED"]["cue_induced_fn_high_confidence"],
        "staged_cue_fn_total": d["STAGED"]["cue_induced_fn_total"],
        "staged_sens_spec": (measured["corpus_c_assertion_mention"]["STAGED"]["sensitivity"],
                             measured["corpus_c_assertion_mention"]["STAGED"]["specificity"]),
        "prosefix_sens_spec": (measured["corpus_c_assertion_mention"]["PROSEFIX"]["sensitivity"],
                               measured["corpus_c_assertion_mention"]["PROSEFIX"]["specificity"]),
        "verdict": ("CONFIRMED: 10/10 HIGH cue-FN belongs to PROSEFIX dc8aa0de3869; "
                    "STAGED e2d24b92 has 0 cue-induced FN and its rejection rests on the FP axis"
                    if d["PROSEFIX"]["cue_induced_fn_high_confidence"] == 10
                    and d["STAGED"]["cue_induced_fn_high_confidence"] == 0
                    else "NOT CONFIRMED"),
    }


def main() -> int:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    pc = pin_check()
    if pc["bad"]:
        out = {"status": "INCONCLUSIVE", "reason": "cited-pin mismatch", "bad": pc["bad"],
               "pins": pc["pins"], "generated_at": started}
        (HERE / "raw_measurements.json").write_text(json.dumps(out, indent=1) + "\n")
        print("PIN MISMATCH (fail closed):")
        for b in pc["bad"]:
            print("  -", b)
        return 2

    live_before = sha256(ROOT / ARMS["APPLIED"][0])
    adj = json.loads(ADJ.read_text())
    cal = load(CAL_PATH, "cal")
    mods = {arm: load(ROOT / rel, f"cs_{arm.lower()}") for arm, (rel, _) in ARMS.items()}
    w049 = load(W049_HARNESS, "w049")

    # (a) 27-fixture corpus: aggregate (registered instrument) + per-fixture classes
    corpus_a = {arm: cal.corpus_census(m) for arm, m in mods.items()}
    rows_a = {arm: rows_corpus_a(m) for arm, m in mods.items()}
    for arm in ARMS:
        assert corpus_a[arm]["tp"] == sum(1 for r in rows_a[arm] if r["class"] == "TP"), arm
        assert corpus_a[arm]["fp"] == sum(1 for r in rows_a[arm] if r["class"] == "FP"), arm
        assert corpus_a[arm]["fn"] == sum(1 for r in rows_a[arm] if r["class"] == "FN"), arm
        assert corpus_a[arm]["tn"] == sum(1 for r in rows_a[arm] if r["class"] == "TN"), arm

    # (c) 16-fixture assertion-vs-mention
    corpus_c = {arm: cal.fixture_census(m) for arm, m in mods.items()}

    # (b) live census on the frozen snapshot + converse scan on the snapshot
    corpus_b = {arm: live_census_frozen(m, SNAP) for arm, m in mods.items()}
    cal.MAP = SNAP
    converse = {}
    for arm, m in mods.items():
        flagged = sorted({r["claim_index"] for r in corpus_b[arm]["labeled_detail"]}
                         | {r["claim_index"] for r in corpus_b[arm]["unlabeled"]})
        converse[arm] = cal.converse_scan(m, {"claims_affected": flagged})

    # (d)/(e) worker-049 corpus + worker-035 battery
    corpus_d = corpus_d_census(w049, mods)

    censuses = {"corpus_a_27fixtures": corpus_a, "corpus_b_live": corpus_b,
                "corpus_c_assertion_mention": corpus_c, "corpus_d_worker049": corpus_d}
    decision = decide(censuses)

    per_fixture = {
        "corpus_a": {arm: {r["id"]: r["class"] for r in rows_a[arm]} for arm in ARMS},
        "corpus_c": {arm: {r["id"]: r["class"] for r in corpus_c[arm]["rows"]} for arm in ARMS},
        "corpus_d": {arm: {r["id"]: r["class"] for r in corpus_d[arm]["per_fixture"]} for arm in ARMS},
    }

    measured = {
        "corpus_a_27fixtures": {k: {kk: vv for kk, vv in v.items() if kk != "non_pass_rows"}
                                for k, v in corpus_a.items()},
        "corpus_b_live": {k: {kk: vv for kk, vv in v.items() if kk not in ("labeled_detail", "unlabeled")}
                          for k, v in corpus_b.items()},
        "corpus_c_assertion_mention": {k: {kk: vv for kk, vv in v.items() if kk != "rows"}
                                       for k, v in corpus_c.items()},
        "corpus_d_worker049_cue_fn": {k: {kk: vv for kk, vv in v.items() if kk != "per_fixture"}
                                      for k, v in corpus_d.items()},
        "corpus_d_fixture_classes": {k: census_summary(v) for k, v in corpus_d.items()},
        "per_fixture_tp_fp_fn_census": per_fixture,
        "converse_scan": {k: {kk: vv for kk, vv in v.items() if kk != "unflagged_detail"}
                          for k, v in converse.items()},
        "decision": decision,
    }
    comparison = compare_with_declared(adj, measured)
    attribution = attribution_check(measured)

    live_after = sha256(ROOT / ARMS["APPLIED"][0])
    freeze = {
        "live_before": live_before, "live_after": live_after,
        "live_is_cited_applied": live_after.startswith("a8c04fc31e4a"),
        "moved_during_review": live_before != live_after,
        "live_mtime": datetime.fromtimestamp(
            (ROOT / ARMS["APPLIED"][0]).stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        "void_sha256": sha256(VOID_EVIDENCE),
        "void_is_cited": sha256(VOID_EVIDENCE).startswith("e36b0d644ca7"),
        "live_equals_void": live_after == sha256(VOID_EVIDENCE),
    }

    out = {
        "task": "W075-CLASSSEP-R3-ADJUDICATION-REVIEW",
        "assignment": "astra-life07-classsep-adjudication-review",
        "target": "reviews/CLASSSEP-calibration-adjudication.json",
        "target_sha256": sha256(ADJ),
        "generated_at": started,
        "reviewer": "worker-075",
        "pins": pc["pins"],
        "freeze": freeze,
        "measurements": measured,
        "corpus_b_live_detail": {k: {"labeled_detail": v["labeled_detail"],
                                     "unlabeled": v["unlabeled"],
                                     "non_claim_findings": v["non_claim_findings"]}
                                 for k, v in corpus_b.items()},
        "corpus_d_per_fixture": {k: v["per_fixture"] for k, v in corpus_d.items()},
        "comparison": comparison,
        "attribution": attribution,
        "internal_consistency": True,
    }
    (HERE / "raw_measurements.json").write_text(json.dumps(out, indent=1) + "\n")
    (HERE / "per_fixture_census.json").write_text(json.dumps(per_fixture, indent=1) + "\n")

    print(f"pins: {len(pc['pins'])}/{len(pc['pins'])} match; live detector "
          f"{live_before[:12]} -> {live_after[:12]} (moved={freeze['moved_during_review']})")
    print(f"comparison cells: {comparison['n_cells']}, mismatches: {comparison['n_mismatch']}")
    for m in comparison["mismatches"]:
        print("  MISMATCH:", m)
    print(f"attribution: {attribution['verdict']}")
    for arm in ARMS:
        a, b, c, d = (corpus_a[arm], corpus_b[arm], corpus_c[arm], corpus_d[arm])
        print(f"{arm:<9} (a)27fx={a['tp']}/{a['fp']}/{a['tn']}/{a['fn']} {a['verdict']:<9} "
              f"(b)hard={b['hard_total']:<3} FP={b['fp']:<3} unlab={b['unlabeled_count']:<3} "
              f"(c){c['sensitivity']}-{c['specificity']:<6} "
              f"(d)FNh={d['cue_induced_fn_high_confidence']:<3} batt={d['worker035_battery']['passed']}/"
              f"{d['worker035_battery']['total']:<3} bar={decision['per_arm'][arm]['meets_bar']}")
    print(f"DECISION choice ({decision['choice']}); adoptable={decision['adoptable_arms']}")
    print(f"unlabeled APPLIED: {[(u['claim_index'], u['auto_mechanism']) for u in corpus_b['APPLIED']['unlabeled']]}")
    print(f"-> {HERE.relative_to(ROOT)}/raw_measurements.json")
    return 0 if comparison["n_mismatch"] == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
