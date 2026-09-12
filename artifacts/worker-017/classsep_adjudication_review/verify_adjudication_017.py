#!/usr/bin/env python3
"""W017-CLASSSEP-R3-ADJUDICATION-REVIEW-01 — independent verification instrument.

Target: reviews/CLASSSEP-calibration-adjudication.json (astra-lead-audit, r3-life06).
Question: do the adjudication's declared pins resolve, and do its decisive censuses
reproduce at those pins, on a runner written independently of the author's
(artifacts/worker-032/classsep-prose-01/pinned/lead_classsep_calibration.py)?

Read-only on every canonical input. Writes only under
artifacts/worker-017/classsep_adjudication_review/.

Usage: python3 verify_adjudication_017.py [--json OUT]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = Path(__file__).resolve().parent
TARGET = ROOT / "reviews/CLASSSEP-calibration-adjudication.json"
LEAD_RUNNER_PIN = ROOT / "artifacts/worker-032/classsep-prose-01/pinned/lead_classsep_calibration.py"
CORPUS_A = ROOT / "artifacts/worker-07/class_separation_falsification/results.json"
CORPUS_D = ROOT / "artifacts/worker-049/classsep_fn_audit/corpus.json"
FROZEN_MAP = ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
SUPERSEDED = ROOT / "reviews/CLASSSEP-calibration-adjudication-l05-superseded.json"
REGISTERED_RUNNER = ROOT / "runtime/bin/classsep_regression.py"
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load_mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def census(rows: list[dict]) -> dict:
    tp = sum(1 for r in rows if r["class"] == "TP")
    fp = sum(1 for r in rows if r["class"] == "FP")
    tn = sum(1 for r in rows if r["class"] == "TN")
    fn = sum(1 for r in rows if r["class"] == "FN")
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "n": len(rows),
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "non_pass_rows": [r for r in rows if r["class"] not in ("TP", "TN")]}


def arm_census_a(mod, fixtures: list[dict]) -> dict:
    rows = []
    for fx in fixtures:
        p = ROOT / fx["fixture_path"]
        if not p.is_file():
            rows.append({"id": fx["id"], "class": "MISSING", "path": fx["fixture_path"]})
            continue
        m = json.loads(p.read_text())
        det = list(mod.findings_for_map(m))
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    try:
                        det += list(mod.findings_for_text((ROOT / art).read_text(errors="replace"),
                                                          f"artifact {art}"))
                    except OSError:
                        pass
        truth, got = bool(fx["is_class_merge"]), bool(det)
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        rows.append({"id": fx["id"], "class": cls, "n_findings": len(det),
                     "expect": truth, "fixture_path": fx["fixture_path"]})
    out = census(rows)
    out["rows"] = rows
    return out


def arm_census_c(mod, fixtures: list[tuple]) -> dict:
    rows = []
    for fid, truth, text in fixtures:
        got = bool(mod.findings_for_text(text, f"fixture {fid}"))
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        rows.append({"id": fid, "expect_merge_assertion": truth, "fired": got, "class": cls})
    out = census(rows)
    out["sensitivity"] = f"{out['tp']}/{out['tp'] + out['fn']}"
    out["specificity"] = f"{out['tn']}/{out['tn'] + out['fp']}"
    out["rows"] = rows
    return out


def arm_census_d(mod, fixtures: list[dict]) -> dict:
    rows, cue_fn, cue_fn_hi, mention_fp = [], [], [], []
    for fx in fixtures:
        if not isinstance(fx, dict) or "text" not in fx:
            continue
        got = bool(mod.findings_for_text(fx["text"], f"fixture {fx.get('id')}"))
        truth = bool(fx.get("expected_findings"))
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        rows.append({"id": fx.get("id"), "class": cls, "category": fx.get("category"),
                     "cue": fx.get("adversarial_cue"), "confidence": fx.get("confidence"),
                     "expect": truth, "fired": got})
        if fx.get("category") == "ADVERSARIAL_ASSERTION" and fx.get("adversarial_cue") and truth and not got:
            cue_fn.append(fx.get("id"))
            if str(fx.get("confidence", "")).upper() == "HIGH":
                cue_fn_hi.append(fx.get("id"))
        if fx.get("category") == "MENTION" and not truth and got:
            mention_fp.append(fx.get("id"))
    out = census(rows)
    out.update({"cue_induced_fn_total": len(cue_fn), "cue_induced_fn_ids": cue_fn,
                "cue_induced_fn_high": len(cue_fn_hi), "cue_induced_fn_high_ids": cue_fn_hi,
                "mention_fp_ids": mention_fp, "rows": rows})
    return out


def live_census(mod, frozen: dict) -> dict:
    raw = list(mod.findings_for_map(frozen))
    per_claim: dict[int, list] = {}
    other = []
    for x in raw:
        mo = re.search(r"claims\[(\d+)\]", x)
        (per_claim.setdefault(int(mo.group(1)), []).append(x) if mo else other.append(x))
    hard = [x for x in raw if not x.startswith("CLASSSEP-SOFT:")]
    return {"hard_total": len(hard), "soft_total": len(raw) - len(hard),
            "claims_flagged": len(per_claim), "per_claim": {str(k): v for k, v in sorted(per_claim.items())},
            "unlabeled_claim_indices": sorted(i for i in per_claim if i > 306),
            "non_claim_findings": other}


def extract_c_fixtures(path: Path) -> list[tuple]:
    """Pull ASSERTION_MENTION_FIXTURES out of the pinned lead runner as DATA via AST."""
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ASSERTION_MENTION_FIXTURES" for t in node.targets):
            return [tuple(x) for x in ast.literal_eval(node.value)]
    raise SystemExit("ASSERTION_MENTION_FIXTURES not found in pinned runner")


def cue_scan(mod, frozen: dict, flagged: set[int]) -> dict:
    """Independent FN direction: strong first-order unity cues anywhere in the snapshot."""
    cues = re.compile(
        r"(?:are|is|form|constitute|treated?\s+as|regarded?\s+as)\s+(?:one|a\s+single|the\s+same)\s+"
        r"(?:merged\s+|unified\s+)?class"
        r"|merge\s+(?:the\s+)?(?:two\s+)?(?:c\s*0\s*(?:and|or|/|,|\+)\s*c\s*2|c\s*2\s*(?:and|or|/|,|\+)\s*c\s*0)"
        r"|(?:c\s*0\s*(?:and|or|/|,|\+)\s*c\s*2|c\s*2\s*(?:and|or|/|,|\+)\s*c\s*0)\s+(?:are|is|form)\s+"
        r"(?:one|a\s+single|the\s+same)\s+class"
        r"|do\s+not\s+split[^.!?]{0,40}(?:c\s*0|c\s*2)", re.I)
    hits = []
    for i, c in enumerate(frozen.get("claims", [])):
        st = c.get("statement") or ""
        if not isinstance(st, str):
            st = str(st)
        for mo in cues.finditer(st):
            hits.append({"claim_index": i, "flagged": i in flagged,
                         "match": mo.group(0)[:90],
                         "context": st[max(0, mo.start() - 70):mo.end() + 70]})
    return {"cue_hits": hits, "unflagged_cue_hits": [h for h in hits if not h["flagged"]]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "report.json"))
    ap.add_argument("--applied-path", default=None,
                    help="override APPLIED with a pinned copy (e.g. the a8c04fc3 bytes) to separate "
                         "the adjudicated pin from the live canonical file")
    args = ap.parse_args()

    adj = json.loads(TARGET.read_text())
    arms_decl = {k: dict(v) for k, v in adj["detectors"].items()}
    applied_override = None
    if args.applied_path:
        applied_override = Path(args.applied_path)
        if not applied_override.is_absolute():
            applied_override = ROOT / applied_override
        arms_decl["APPLIED"]["path"] = str(applied_override.relative_to(ROOT))
        arms_decl["APPLIED"]["sha256"] = sha256(applied_override)
    pre_hashes = {k: sha256(ROOT / v["path"]) for k, v in arms_decl.items()}
    pre_hashes["__snapshot__"] = sha256(FROZEN_MAP)
    pre_hashes["__superseded__"] = sha256(SUPERSEDED)
    pre_hashes["__target__"] = sha256(TARGET)

    pin_checks = []
    for k, v in arms_decl.items():
        p = ROOT / v["path"]
        measured = sha256(p)
        pin_checks.append({"arm": k, "path": v["path"], "declared": v["sha256"],
                           "measured": measured, "match": measured == v["sha256"],
                           "cited_prefix_match": measured.startswith(v["cited_prefix"])})
    pin_checks.append({"arm": "snapshot", "path": adj["frozen_map_snapshot"]["path"],
                       "declared": adj["frozen_map_snapshot"]["sha256"], "measured": sha256(FROZEN_MAP),
                       "match": sha256(FROZEN_MAP) == adj["frozen_map_snapshot"]["sha256"]})
    pin_checks.append({"arm": "superseded", "path": adj["superseded_artifact_preserved"],
                       "declared": adj["superseded_artifact_sha256"], "measured": sha256(SUPERSEDED),
                       "match": sha256(SUPERSEDED) == adj["superseded_artifact_sha256"]})
    for label, p in (("corpus_a", CORPUS_A), ("corpus_d", CORPUS_D),
                     ("lead_runner_pin", LEAD_RUNNER_PIN), ("registered_runner", REGISTERED_RUNNER)):
        pin_checks.append({"arm": label, "path": str(p.relative_to(ROOT)), "declared": None,
                           "measured": sha256(p), "match": None})

    mods = {k: load_mod(ROOT / v["path"], f"cs_{k}") for k, v in arms_decl.items()}

    # ---- (a) 27-fixture corpus ------------------------------------------------------------
    fixtures_a = json.loads(CORPUS_A.read_text())["fixtures"]
    a = {k: arm_census_a(m, fixtures_a) for k, m in mods.items()}

    # ---- (c) labeled assertion/mention fixtures (data extracted from pinned runner) -------
    fixtures_c = extract_c_fixtures(LEAD_RUNNER_PIN)
    c = {k: arm_census_c(m, fixtures_c) for k, m in mods.items()}

    # ---- (d) worker-049 cue-carrying genuine assertions ------------------------------------
    fixtures_d = json.loads(CORPUS_D.read_text())["fixtures"]
    d = {k: arm_census_d(m, fixtures_d) for k, m in mods.items()}

    # ---- (b) live census on the frozen snapshot --------------------------------------------
    frozen = json.loads(FROZEN_MAP.read_text())
    b = {k: live_census(m, frozen) for k, m in mods.items()}
    scan = {k: cue_scan(m, frozen, set(int(i) for i in b[k]["per_claim"])) for k, m in mods.items()}

    # ---- controls ---------------------------------------------------------------------------
    controls = []

    # C1 positive: mutate one corpus-A fixture map in memory; my census must see the change.
    fx = json.loads((ROOT / fixtures_a[0]["fixture_path"]).read_text())
    fx2 = json.loads(json.dumps(fx))
    fx2["groups"][0]["nodes"][0]["label"] = "C0 and C2 are one class"
    c1 = bool(mods["APPLIED"].findings_for_map(fx2))
    controls.append({"id": "C1-mutant-caught", "expected": True, "observed": c1, "pass": c1})

    # C2 negative/absent path must be reported missing, never scored as clean.
    c2 = any(r["class"] == "MISSING" for r in arm_census_a(mods["APPLIED"], [{"id": "X", "is_class_merge": True,
                                                                             "fixture_path": "does/not/exist.json"}])["rows"])
    controls.append({"id": "C2-missing-path-detected", "expected": True, "observed": c2, "pass": c2})

    # C3 anchor pair: a first-order assertion fires; the corpus-C M9 mention outcome is
    # reproduced per arm as the adjudication's own table declares it (defective arms flag it).
    c3a = bool(mods["APPLIED"].findings_for_text("C0 and C2 are one class in the frozen registry.", "anchor"))
    m9 = {k: next((r["class"] for r in c[k]["rows"] if r["id"] == "M9"), None) for k in mods}
    c3b_expect = {"APPLIED": "FP", "PRE": "FP", "STAGED": "FP", "PROSEFIX": "TN"}
    controls.append({"id": "C3-anchor-assertion-fires", "expected": True, "observed": c3a, "pass": c3a})
    controls.append({"id": "C3b-M9-per-arm-class", "expected": c3b_expect, "observed": m9, "pass": m9 == c3b_expect})

    # C4 decision logic: no arm meets the declared adoption bar.
    bar = adj["decision"]["adoption_bar"]
    adoptable = []
    for k in arms_decl:
        ok = (a[k]["verdict"] == "PASS" and a[k]["tp"] == 17 and a[k]["fp"] == 0 and a[k]["fn"] == 0
              and int(c[k]["sensitivity"].split("/")[0]) >= 5
              and int(c[k]["specificity"].split("/")[0]) >= 9
              and d[k]["cue_induced_fn_high"] == 0)
        if ok:
            adoptable.append(k)
    controls.append({"id": "C4-adoption-bar-empty", "expected": [], "observed": adoptable,
                     "pass": adoptable == [] and adj["decision"]["adoptable_arms"] == []})

    # C5 determinism: same run twice, same censuses.
    c5 = all(census(arm_census_d(mods[k], fixtures_d)["rows"]) == census(d[k]["rows"]) for k in mods)
    controls.append({"id": "C5-deterministic-rerun", "expected": True, "observed": c5, "pass": c5})

    # C6 canonical pin stability across the run (no write).
    post = {k: sha256(ROOT / v["path"]) for k, v in arms_decl.items()}
    post["__snapshot__"] = sha256(FROZEN_MAP)
    post["__superseded__"] = sha256(SUPERSEDED)
    post["__target__"] = sha256(TARGET)
    stable = pre_hashes == post
    controls.append({"id": "C6-pins-stable-pre-eq-post", "expected": True, "observed": stable,
                     "pass": stable})

    # ---- compare to the adjudication's declared numbers --------------------------------------
    def cmp(declared, measured):
        return {"declared": declared, "measured": measured, "match": declared == measured}

    declared_a = {k: {"tp": adj["corpus_a_27fixtures"][k]["tp"], "fp": adj["corpus_a_27fixtures"][k]["fp"],
                      "tn": adj["corpus_a_27fixtures"][k]["tn"], "fn": adj["corpus_a_27fixtures"][k]["fn"],
                      "verdict": adj["corpus_a_27fixtures"][k]["verdict"]} for k in arms_decl}
    declared_c_rates = {k: {"sensitivity": adj["corpus_c_assertion_mention"][k]["sensitivity"],
                            "specificity": adj["corpus_c_assertion_mention"][k]["specificity"]}
                        for k in arms_decl}
    declared_d = {k: {"tp": adj["corpus_d_fixture_classes"][k]["tp"], "fn": adj["corpus_d_fixture_classes"][k]["fn"],
                      "fp": adj["corpus_d_fixture_classes"][k]["fp"], "tn": adj["corpus_d_fixture_classes"][k]["tn"],
                      "cue_fn": adj["corpus_d_worker049_cue_fn"][k]["cue_induced_fn_total"],
                      "cue_fn_high": adj["corpus_d_worker049_cue_fn"][k]["cue_induced_fn_high_confidence"]}
                  for k in arms_decl}
    declared_b = {k: {"hard_total": adj["corpus_b_live"][k]["hard_total"],
                      "claims_flagged": adj["corpus_b_live"][k]["claims_flagged"]} for k in arms_decl}

    measurements = {
        k: {
            "a": cmp(declared_a[k], {kk: a[k][kk] for kk in ("tp", "fp", "tn", "fn", "verdict")}),
            "c_counts": cmp({kk: adj["corpus_c_assertion_mention"][k][kk] for kk in ("tp", "fp", "tn", "fn")},
                            {kk: c[k][kk] for kk in ("tp", "fp", "tn", "fn")}),
            "c_rates": cmp(declared_c_rates[k],
                           {"sensitivity": c[k]["sensitivity"], "specificity": c[k]["specificity"]}),
            "d": cmp(declared_d[k], {"tp": d[k]["tp"], "fn": d[k]["fn"], "fp": d[k]["fp"], "tn": d[k]["tn"],
                                     "cue_fn": d[k]["cue_induced_fn_total"], "cue_fn_high": d[k]["cue_induced_fn_high"]}),
            "b": cmp(declared_b[k], {kk: b[k][kk] for kk in ("hard_total", "claims_flagged")}),
        } for k in arms_decl
    }
    mismatches = []
    for arm, section in measurements.items():
        for corp, r in section.items():
            if not r["match"]:
                mismatches.append({"arm": arm, "corpus": corp, **r})

    report = {
        "schema": "worker-017/classsep-r3-adjudication-review/v1",
        "task_id": "W017-CLASSSEP-R3-ADJUDICATION-REVIEW-01",
        "actor": "worker-017",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "created_at": now(),
        "target": {"path": "reviews/CLASSSEP-calibration-adjudication.json",
                   "sha256": sha256(TARGET), "revision": adj.get("revision"),
                   "author": adj.get("actor"), "created_at": adj.get("created_at")},
        "independence": "runner and census written for this review; only fixture data and pinned modules reused. "
                        "No author artifact edited; no detector adopted; canonical pins re-measured pre==post.",
        "pin_checks": pin_checks,
        "all_pins_match": all(p["match"] is not False for p in pin_checks),
        "corpus_a_27fixtures": a,
        "corpus_c_assertion_mention": c,
        "corpus_d_worker049": d,
        "corpus_b_live": b,
        "converse_scan": scan,
        "measurement_vs_adjudication": measurements,
        "mismatches": mismatches,
        "decision_recheck": {"adoption_bar": bar, "adoptable_arms_recomputed": adoptable,
                             "adjudication_choice": adj["decision"]["choice"],
                             "adjudication_adoptable_arms": adj["decision"]["adoptable_arms"]},
        "controls": controls,
        "controls_all_pass": all(c["pass"] for c in controls),
        "canonical_pins_pre": pre_hashes, "canonical_pins_post": post,
        "limits": [
            "The live census binds the frozen map snapshot f344ed2a only; it is not a statement about the live map, which has since grown.",
            "Corpus C fixtures are the author's declared 16 strings extracted from the pinned runner; this review checks the census logic and the arms' behaviour on them, not the strings' provenance.",
            "The 19 live hard findings are re-classified by the reviewer in the companion review JSON, not by this instrument.",
        ],
        "falsifier": "Falsified if any pin in the adjudication fails to resolve at its declared sha256, if any declared census number fails to reproduce, or if a genuine first-order C0/C2 unity assertion is found in the frozen snapshot among claims the APPLIED arm left unflagged.",
    }
    Path(args.json).write_text(json.dumps(report, indent=1) + "\n")
    print(f"report -> {args.json} sha256 {sha256(Path(args.json))}")
    print(f"pins_match={report['all_pins_match']} mismatches={len(mismatches)} controls_pass={report['controls_all_pass']}")
    for k in arms_decl:
        print(f"{k:9s} A={a[k]['tp']}/{a[k]['fn']}/{a[k]['fp']}/{a[k]['tn']} "
              f"C sens={c[k]['sensitivity']} spec={c[k]['specificity']} "
              f"D fn={d[k]['fn']} cueFN={d[k]['cue_induced_fn_total']}({d[k]['cue_induced_fn_high']}H) "
              f"B hard={b[k]['hard_total']}")
    for m in mismatches:
        print("MISMATCH", m)
    return 0 if report["all_pins_match"] and report["controls_all_pass"] and not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
