#!/usr/bin/env python3
"""W031-CLASSSEP-R1-GENERALIZATION-01 — independent generalization audit of the
staged prose-mode candidate worker-032/classsep-prose-01/candidate/class_separation_prose_r1.py.

What this measures (all at pinned bytes, hash-verified before and after):

  1. recount   — the four pre-registered corpora the candidate reports on
                 (worker-07 27-fixture, worker-049 corpus d + twins, worker-035
                 battery e, lead r3 corpus c), scored by this runner.
  2. fresh     — fixtures_battery.json, authored after the candidate's rules were
                 published, labeled before either detector ran on it.
  3. live      — hard findings + unflagged composite mentions on the two pinned
                 live maps (design pin 262da697, 320 claims).
  4. attribution — where candidate and baseline disagree, both verdicts are
                 recorded so a disagreement can be attributed to the candidate's
                 precedence chain rather than to the corpus.

This is worker measurement. It sets no node status, no validation_status, no gate
verdict, and writes no canonical, proposed or schema file.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PINNED = HERE / "pinned"
RAW = HERE / "raw"

PINS = {
    "canonical": REPO / "research_map/class_separation.py",
    "candidate_r1": PINNED / "class_separation.candidate_r1.42cdb683.py",
    "prosefix_w049": PINNED / "class_separation.prosefix_dc8aa0de.py",
    "canonical_pin_a8c04": PINNED / "class_separation.a8c04fc31e4a.py",
    "map_design": PINNED / "research_map.pin.json",
    "w049_corpus_d": PINNED / "w049_corpus_d.json",
    "w035_battery_e": PINNED / "w035_battery_e.json",
    "battery": HERE / "fixtures_battery.json",
    "w07_results": REPO / "artifacts/worker-07/class_separation_falsification/results.json",
}

ARMS = ["canonical", "candidate_r1", "prosefix_w049"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_pins() -> dict:
    out = {}
    for name, p in PINS.items():
        if p.exists():
            out[name] = {"path": str(p.relative_to(REPO)) if str(p).startswith(str(REPO)) else str(p),
                         "sha256": sha256(p), "bytes": p.stat().st_size}
        else:
            out[name] = {"path": str(p), "sha256": None, "missing": True}
    return out


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"w031_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def count_findings(mod, text: str, where: str) -> int:
    """Hard findings only; CLASSSEP-SOFT is reported separately by the canonical
    findings_for_text and is not a class-merge finding."""
    fs = mod.findings_for_text(text, where)
    return len([f for f in fs if not f.startswith("CLASSSEP-SOFT")])


def score_corpus(rows, key_expected, key_text, mod):
    """rows: list of dicts; returns per-fixture verdicts + confusion."""
    per = []
    for r in rows:
        exp = int(r[key_expected])
        where = r.get("id") or r.get("control_id") or r.get("fixture") or "fixture"
        n = count_findings(mod, r[key_text], str(where))
        got = 1 if n else 0
        per.append({"id": str(where), "expected": exp, "fired": bool(got), "n_findings": n,
                    "class": {(1, 1): "TP", (1, 0): "FN", (0, 1): "FP", (0, 0): "TN"}[(exp, got)]})
    tp = sum(1 for x in per if x["class"] == "TP")
    fn = sum(1 for x in per if x["class"] == "FN")
    fp = sum(1 for x in per if x["class"] == "FP")
    tn = sum(1 for x in per if x["class"] == "TN")
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(per),
            "sensitivity": f"{tp}/{tp + fn}" if (tp + fn) else "n/a",
            "specificity": f"{tn}/{tn + fp}" if (tn + fp) else "n/a", "per_fixture": per}


def score_w07(mod) -> dict:
    res = json.loads(PINS["w07_results"].read_text())
    per = []
    for fx in res["fixtures"]:
        fpth = REPO / fx["fixture_path"]
        if not fpth.exists():
            per.append({"id": fx["fixture_path"], "class": "MISSING", "expected": bool(fx["is_class_merge"])})
            continue
        m = json.loads(fpth.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (REPO / art).is_file():
                    det += mod.findings_for_text((REPO / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        per.append({"id": Path(fx["fixture_path"]).stem, "expected": truth, "fired": got,
                    "class": {(True, True): "TP", (True, False): "FN", (False, True): "FP", (False, False): "TN"}[(truth, got)]})
    tp = sum(1 for x in per if x["class"] == "TP")
    fn = sum(1 for x in per if x["class"] == "FN")
    fp = sum(1 for x in per if x["class"] == "FP")
    tn = sum(1 for x in per if x["class"] == "TN")
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(per),
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE", "per_fixture": per}


def score_w035(mod) -> dict:
    bat = json.loads(PINS["w035_battery_e"].read_text())
    controls = bat["controls"] if isinstance(bat, dict) else bat
    pos = [c for c in controls if c["expect"] == "ASSERTION"]
    neg = [c for c in controls if c["expect"] != "ASSERTION"]
    pos_ok = [c["control_id"] for c in pos if count_findings(mod, c["text"], c["control_id"])]
    neg_bad = [c["control_id"] for c in neg if count_findings(mod, c["text"], c["control_id"])]
    return {"pos_pass": len(pos_ok), "pos_total": len(pos), "neg_pass": len(neg) - len(neg_bad),
            "neg_total": len(neg), "all_pass": len(pos_ok) == len(pos) and not neg_bad,
            "pos_missed": [c["control_id"] for c in pos if c["control_id"] not in pos_ok],
            "neg_fired": neg_bad}


def score_w049(mod) -> dict:
    corp = json.loads(PINS["w049_corpus_d"].read_text())
    fx = {f["id"]: f for f in corp["fixtures"]}
    per = []
    cue_fn, cue_fn_high = [], []
    for f in corp["fixtures"]:
        n = count_findings(mod, f["text"], f["id"])
        got = bool(n)
        exp = bool(f["expected_findings"])
        cls = {(True, True): "TP", (True, False): "FN", (False, True): "FP", (False, False): "TN"}[(exp, got)]
        per.append({"id": f["id"], "category": f["category"], "confidence": f.get("confidence"),
                    "expected": exp, "fired": got, "class": cls})
        if f.get("twin_of") and exp and not got:
            twin = fx.get(f["twin_of"])
            twin_fired = bool(count_findings(mod, twin["text"], twin["id"])) if twin else None
            rec = {"adversarial": f["id"], "twin": f["twin_of"], "twin_fired": twin_fired,
                   "confidence": f.get("confidence"), "cue": f.get("adversarial_cue")}
            cue_fn.append(rec)
            if f.get("confidence") == "HIGH":
                cue_fn_high.append(rec)
    tp = sum(1 for x in per if x["class"] == "TP")
    fn = sum(1 for x in per if x["class"] == "FN")
    fp = sum(1 for x in per if x["class"] == "FP")
    tn = sum(1 for x in per if x["class"] == "TN")
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(per),
            "cue_induced_fn_total": len(cue_fn), "cue_induced_fn_high": len(cue_fn_high),
            "cue_induced_fn_high_detail": cue_fn_high, "per_fixture": per}


def live_map(mod, m: dict) -> dict:
    hard = mod.findings_for_map(m)
    claims = m.get("claims", [])
    composite_like, unflagged = 0, []
    import re as _re
    pat = _re.compile(r"c\s*0\s*(?:or|and|/|,|\+|\s)\s*c\s*2|c\s*2\s*(?:or|and|/|,|\+|\s)\s*c\s*0|c0c2|c2c0", _re.I)
    flagged_idx = set()
    for f in hard:
        mm = _re.search(r"claims\[(\d+)\]", f)
        if mm:
            flagged_idx.add(int(mm.group(1)))
    for i, c in enumerate(claims):
        if not isinstance(c, dict):
            continue
        txt = str(c.get("statement") or "")
        if pat.search(mod.norm(txt)):
            composite_like += 1
            if i not in flagged_idx:
                unflagged.append({"claim_index": i, "actor": c.get("actor"),
                                  "snippet": txt[:300]})
    return {"hard_total": len(hard), "claims_flagged": len(flagged_idx),
            "composite_like_claims": composite_like, "unflagged_composite_like": len(unflagged),
            "unflagged_detail": unflagged}


def main() -> int:
    pins_before = snapshot_pins()
    modules = {}
    for arm in ARMS:
        p = PINS[arm]
        if p.exists():
            modules[arm] = load_module(arm, p)
    battery = json.loads(PINS["battery"].read_text())
    fixtures = battery["fixtures"]

    out = {"schema": "worker-031/classsep-r1-generalization/report/v1",
           "task_id": "W031-CLASSSEP-R1-GENERALIZATION-01", "actor": "worker-031",
           "node_id": "A1", "gate": "G-AUDIT",
           "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
           "question": ("Does the staged prose-mode candidate's rule set generalize beyond the corpora it "
                        "was calibrated on, or does it only move the lexical frontier?"),
           "pins": pins_before, "arms": ARMS, "results": {}}

    for arm, mod in modules.items():
        res = {}
        res["corpus_w07_27fixture"] = score_w07(mod)
        res["corpus_w049_d_plus_twins"] = score_w049(mod)
        res["battery_w035_e"] = score_w035(mod)
        res["battery_fresh_w031"] = score_corpus(fixtures, "expected_findings", "text", mod)
        m = json.loads(PINS["map_design"].read_text())
        res["live_map_design_pin"] = live_map(mod, m)
        out["results"][arm] = res

    # disagreement table on the fresh battery: where arms differ, record all verdicts
    fresh = out["results"]["candidate_r1"]["battery_fresh_w031"]["per_fixture"]
    exp_by_id = {f["id"]: int(f["expected_findings"]) for f in fixtures}
    cat_by_id = {f["id"]: f["category"] for f in fixtures}
    rat_by_id = {f["id"]: f["rationale"] for f in fixtures}
    disagree = []
    for row in fresh:
        verdicts = {arm: out["results"][arm]["battery_fresh_w031"]["per_fixture"] for arm in modules}
        vals = {arm: bool([x for x in verdicts[arm] if x["id"] == row["id"]][0]["fired"]) for arm in modules}
        if len(set(vals.values())) > 1 or vals.get("candidate_r1") != bool(exp_by_id[row["id"]]):
            disagree.append({"id": row["id"], "category": cat_by_id[row["id"]],
                             "expected_findings": exp_by_id[row["id"]],
                             "verdicts": vals, "rationale": rat_by_id[row["id"]]})
    out["fresh_battery_disagreements"] = disagree

    cand = out["results"]["candidate_r1"]
    base = out["results"]["canonical"]
    out["summary"] = {
        "candidate_vs_baseline_fresh_sens": [base["battery_fresh_w031"]["sensitivity"], cand["battery_fresh_w031"]["sensitivity"]],
        "candidate_vs_baseline_fresh_spec": [base["battery_fresh_w031"]["specificity"], cand["battery_fresh_w031"]["specificity"]],
        "candidate_fresh_fp_ids": [x["id"] for x in cand["battery_fresh_w031"]["per_fixture"] if x["class"] == "FP"],
        "candidate_fresh_fn_ids": [x["id"] for x in cand["battery_fresh_w031"]["per_fixture"] if x["class"] == "FN"],
        "baseline_fresh_fp_ids": [x["id"] for x in base["battery_fresh_w031"]["per_fixture"] if x["class"] == "FP"],
        "baseline_fresh_fn_ids": [x["id"] for x in base["battery_fresh_w031"]["per_fixture"] if x["class"] == "FN"],
        "candidate_recount_w07": cand["corpus_w07_27fixture"]["verdict"],
        "candidate_recount_w049_high_cue_fn": cand["corpus_w049_d_plus_twins"]["cue_induced_fn_high"],
        "candidate_recount_w035_all_pass": cand["battery_w035_e"]["all_pass"],
        "candidate_live_design_pin_hard": cand["live_map_design_pin"]["hard_total"],
        "baseline_live_design_pin_hard": base["live_map_design_pin"]["hard_total"],
        "n_disagreements": len(disagree),
    }

    pins_after = snapshot_pins()
    out["pins_after"] = pins_after
    out["pins_stable"] = pins_before == pins_after
    out["runner_checks"] = {
        "canonical_bytes_are_a8c04fc31e4a": pins_before["canonical"]["sha256"] == "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
        "candidate_is_42cdb6839cc4": pins_before["candidate_r1"]["sha256"] == "42cdb6839cc4723f9bb6c937c3ed0e13ff42bcaf2c0ec671344513b8758230d3",
        "battery_n": len(fixtures),
        "battery_hash_reverified": pins_before["battery"]["sha256"] == pins_after["battery"]["sha256"],
        "arms_loaded": sorted(modules),
    }
    out["falsifier"] = ("Falsified if any pin hash changes between pins_before and pins_after; if the battery "
                        "hash is not stable across the run; if the candidate's reported numbers are not "
                        "reproduced by this runner on the pre-registered corpora; or if every fresh-battery "
                        "failure is explainable by a labeling error rather than by the candidate's rule chain.")
    out["no_gate_self_pass"] = ("Worker measurement evidence. Sets no gate verdict, no node status, no "
                                "validation_status. Writes no canonical, proposed or schema file.")

    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "report.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    (RAW / "fresh_battery_disagreements.json").write_text(json.dumps(disagree, indent=1) + "\n")

    print(json.dumps(out["summary"], indent=1))
    print("checks:", json.dumps(out["runner_checks"]))
    print("pins_stable:", out["pins_stable"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
