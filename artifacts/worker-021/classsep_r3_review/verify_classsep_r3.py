#!/usr/bin/env python3
"""W021-CLASSSEP-R3-REVIEW-01: independent re-measurement of
reviews/CLASSSEP-calibration-adjudication.json (r3-life06, 7714ffd5b467).

Independent instrument: no author aggregation code is imported. The lifecycle-05
instrument and the worker-049 runner are read as DATA SOURCES only (ast.literal_eval of
LIVE_LABELS / ASSERTION_MENTION_FIXTURES); the worker-049 aggregation rules are re-coded
from their documented semantics. Detector modules are loaded from verified source bytes by
exec(), so the measured bytes are exactly the loaded bytes (sys.dont_write_bytecode).

Read-only on every canonical/proposed/review path. Writes census.json, controls.json and
comparison.json next to this script. Exit codes: 0 ok, 2 pin mismatch (fail closed),
3 control failure.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True

ADJ = "reviews/CLASSSEP-calibration-adjudication.json"
SNAP = "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
CAL = "artifacts/audit/classsep_calibration.py"
R3INSTR = "artifacts/audit/classsep_r3_adjudication.py"
W07 = "artifacts/worker-07/class_separation_falsification/results.json"
W049_CORPUS = "artifacts/worker-049/classsep_fn_audit/corpus.json"
W035 = "artifacts/worker-049/classsep_prose_fix/worker035_controls.json"

PINS = {
    ADJ: "7714ffd5b467c506bc8a8736ba1626a9f8a9211092e5313e74c77a4ccb51cec1",
    SNAP: "f344ed2aaea58e4d21c46c1d919e2476b860da4b757b9fbc948d3649bac7c749",
    CAL: "8f2efd262f97b53a50c33a698d57074b83b4df0c2793f5ff7799648bea958464",
    R3INSTR: "fc92f4eac503d4d493e80e03ac63f7688e3e580fe71f3684d46de923e6f67f07",
    W07: "d69ad58468be16655921dcf0eab9570fa6e7ccaf828558a45d4b306cce3de452",
    W049_CORPUS: "9eb2ea9e27439703ffe7c91168348e6539e5a1fbd268f36383d09d0d3aeeea23",
    W035: "ef881c3aa6ef392c2068828b02d6645043913a0ff88ab0487264a6b770c5914d",
}

ARMS = {
    "APPLIED": ("research_map/class_separation.py", "a8c04fc31e4a"),
    "PRE": ("artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
            "c266dbceca87"),
    "STAGED": ("proposed/class_separation.py", "e2d24b927ee8"),
    "PROSEFIX": ("artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
                 "dc8aa0de3869"),
}
VOID_PREFIX = "e36b0d644ca7"
PRIMARY_CLASS_ID = "AF-SCC-C2-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def check_pins() -> dict:
    out, bad = {}, []
    for rel, want in PINS.items():
        got = sha(ROOT / rel)
        out[rel] = {"sha256": got, "expected": want, "match": got == want}
        if got != want:
            bad.append(f"{rel}: {got} != {want}")
    for arm, (rel, prefix) in ARMS.items():
        got = sha(ROOT / rel)
        ok = got.startswith(prefix)
        out[f"arm:{arm}"] = {"path": rel, "sha256": got, "cited_prefix": prefix, "match": ok}
        if not ok:
            bad.append(f"arm {arm}: {got} !~ {prefix}")
    if bad:
        print("PIN MISMATCH (fail closed):")
        for b in bad:
            print("  -", b)
        sys.exit(2)
    return out


def load_verified(rel: str, prefix: str, name: str):
    """Exec the verified source bytes; never reads/writes a bytecode cache."""
    src = (ROOT / rel).read_bytes()
    got = hashlib.sha256(src).hexdigest()
    if not got.startswith(prefix):
        raise RuntimeError(f"{rel}: {got} !~ {prefix}")
    mod = types.ModuleType(name)
    mod.__file__ = str(ROOT / rel)
    exec(compile(src, str(ROOT / rel), "exec"), mod.__dict__)
    return mod


def extract_literals(rel: str, names: set) -> dict:
    tree = ast.parse((ROOT / rel).read_text())
    found = {}
    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name) and t.id in names:
                found[t.id] = ast.literal_eval(node.value)
    missing = names - set(found)
    if missing:
        raise RuntimeError(f"{rel}: literals not found: {sorted(missing)}")
    return found


# --- detector-independent heuristic, control use only ---------------------------------------
_QUOTED = re.compile(r"'[^']{0,300}'|\"[^\"]{0,300}\"|\u2018[^\u2019]{0,300}\u2019|"
                     r"\u201c[^\u201d]{0,300}\u201d")
_META = re.compile(r"\b(detector|pattern|regex|scanner|flag(?:s|ged)?|quote[sd]?|quoting|"
                   r"case label|fixture|corpus|probe|split|non-?merge|false[- ]positive|"
                   r"retired|moved|audit|assertion|assertions)\b", re.I)
_NEG = re.compile(r"\b(no|not|never|nor|without|rather than|zero)\b", re.I)
_ASSERT = re.compile(r"\b(is|are|as|form|forms|treat|treats|cover|covers|use|uses|regard|"
                     r"regards|merge[sd]?|unif(?:y|ies|ied)|single class|one class)\b", re.I)
_COMPOSITE = re.compile(r"c\s*0\s*(?:/|or|and|,|\+)\s*c\s*2|c\s*2\s*(?:/|or|and|,|\+)\s*c\s*0",
                        re.I)


def first_order_flag(text: str) -> bool:
    """Conservative independent 'first-order C0/C2 merge assertion' heuristic.
    Quoted spans are removed first; a match requires the composite token and an
    assertion verb inside a 120-char window with no negation and no meta vocabulary."""
    t = _QUOTED.sub(" ", text)
    if not _COMPOSITE.search(t):
        return False
    for m in _COMPOSITE.finditer(t):
        win = t[max(0, m.start() - 120):min(len(t), m.end() + 120)]
        if _META.search(win) or _NEG.search(win):
            continue
        if _ASSERT.search(win):
            return True
    return False


# --- (i) worker-07 27-fixture corpus --------------------------------------------------------
def corpus_a(mod) -> dict:
    res = json.loads((ROOT / W07).read_text())
    rows, tp, fn, fp, tn = [], 0, 0, 0, 0
    for fx in res["fixtures"]:
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
        rows.append({"id": fx["id"], "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "per_fixture": rows}


# --- (ii) live census at the frozen snapshot ------------------------------------------------
_AUTO_CUES = [
    ("CASE_LABEL", r"TC-F0-|SPLIT_REQUIRED|directive="),
    ("NON_MERGE_COMPOUND", r"non-?merge"),
    ("DETECTOR_SELF", r"\bdetector\b|\bflag(?:s|ged)?\b|\bregex\b|\bscanner\b|asserted as one class"),
    ("QUOTATION", r"['\"\u2018\u2019\u201c\u201d]"),
    ("NEGATION", r"\bno\b|\bnot\b|\bnever\b|\bnor\b|rather than|\bwithout\b"),
    ("WINDOW_ARTIFACT", r"retired|merged file|components moved"),
    ("DETECTOR_DESCRIPTION", r"merge pattern|pattern matches|R1"),
]


def auto_mech(finding: str) -> str:
    for name, pat in _AUTO_CUES:
        if re.search(pat, finding, re.I):
            return name
    return "UNCLASSIFIED"


def corpus_b(mod, snap_path: Path, live_labels: dict) -> dict:
    m = json.loads(snap_path.read_text())
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
    labeled, unlabeled = [], []
    for idx, finds in sorted(per_claim.items()):
        labels = live_labels.get(idx)
        for k, f in enumerate(finds):
            if labels:
                verdict, mech, cue = labels[k] if k < len(labels) else labels[-1]
                if verdict == "TP":
                    tp += 1
                else:
                    fp += 1
                labeled.append({"claim_index": idx, "verdict": verdict, "mechanism": mech,
                                "cue": cue, "finding": f[:180]})
            else:
                unlabeled.append({"claim_index": idx, "finding": f[:200],
                                  "auto_mechanism": auto_mech(f)})
    # independent label audit: the 14 labeled claim statements vs the label set
    label_audit = []
    claims = m.get("claims", [])
    for idx in sorted(live_labels):
        st = claims[idx].get("statement") if idx < len(claims) else None
        st = st if isinstance(st, str) else str(st)
        label_audit.append({"claim_index": idx,
                            "n_labels": len(live_labels[idx]),
                            "n_findings": len(per_claim.get(idx, [])),
                            "composite_token_present": bool(_COMPOSITE.search(st)),
                            "first_order_flag": first_order_flag(st)})
    return {"hard_total": len(hard), "soft_total": len(raw) - len(hard),
            "claims_flagged": len(per_claim), "labeled_claims": sorted(live_labels),
            "tp": tp, "fp": fp, "unlabeled_count": len(unlabeled),
            "unlabeled": unlabeled, "non_claim_findings": non_claim,
            "claims_in_map": len(claims), "map_sha256": sha(snap_path),
            "label_audit": label_audit}


# --- (iii) assertion-vs-mention fixtures ----------------------------------------------------
def corpus_c(mod, fixtures: list) -> dict:
    rows, tp, fn, fp, tn = [], 0, 0, 0, 0
    for fid, truth, text in fixtures:
        got = bool(mod.findings_for_text(text, f"fixture {fid}"))
        cls = ("TP" if truth and got else "FN" if truth else "FP" if got else "TN")
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fid, "expect_merge_assertion": truth, "fired": got, "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
            "sensitivity": f"{tp}/{tp + fn}", "specificity": f"{tn}/{tn + fp}", "rows": rows}


# --- (iv) worker-049 adversarial corpus + worker-035 battery ---------------------------------
def corpus_d(mod, corpus: dict, battery: dict) -> dict:
    rows = []
    for fx in corpus["fixtures"]:
        prose = mod.findings({"statement": fx["text"], "class_id": PRIMARY_CLASS_ID},
                             f"fx:{fx['id']}", mode="prose")
        rows.append({"id": fx["id"], "category": fx["category"],
                     "expected_findings": fx["expected_findings"], "confidence": fx["confidence"],
                     "twin_of": fx["twin_of"], "adversarial_cue": fx.get("adversarial_cue"),
                     "flags": len(prose) > 0})
    by_id = {r["id"]: r for r in rows}
    adv = [r for r in rows if r["category"] == "ADVERSARIAL_ASSERTION"]
    twins = [r for r in rows if r["category"] == "TWIN_CONTROL"]
    plain = [r for r in rows if r["category"] == "PLAIN_POSITIVE"]
    mentions = [r for r in rows if r["category"] == "MENTION"]
    twin_by_adv = {t["twin_of"]: t["id"] for t in twins if t.get("twin_of")}
    cue_induced = []
    for r in adv:
        tw = by_id.get(twin_by_adv.get(r["id"])) if twin_by_adv.get(r["id"]) else None
        if tw is not None and (not r["flags"]) and tw["flags"]:
            cue_induced.append({"adversarial": r["id"], "twin": tw["id"],
                                "confidence": r["confidence"], "cue": r["adversarial_cue"]})
    passed = 0
    bat_rows = []
    for c in battery["controls"]:
        expect_assertion = c["expect"].startswith("ASSERTION")
        got = len(mod.findings({"statement": c["text"], "class_id": PRIMARY_CLASS_ID},
                               f"control:{c['control_id']}", mode="prose")) > 0
        ok = got == expect_assertion
        passed += int(ok)
        bat_rows.append({"control_id": c["control_id"], "expect_assertion": expect_assertion,
                         "measured_assertion": got, "pass": ok})
    classes = {"tp": 0, "fn": 0, "fp": 0, "tn": 0}
    for r in rows:
        cls = ("TP" if r["expected_findings"] and r["flags"] else
               "FN" if r["expected_findings"] and not r["flags"] else
               "FP" if not r["expected_findings"] and r["flags"] else "TN")
        classes[cls.lower()] += 1
    return {"cue_induced_fn_total": len(cue_induced),
            "cue_induced_fn_high_confidence": sum(1 for c in cue_induced
                                                  if c["confidence"] == "HIGH"),
            "cue_induced_fn_detail": cue_induced,
            "adversarial_cleared": [r["id"] for r in adv if not r["flags"]],
            "adversarial_total": len(adv),
            "mention_fp": [r["id"] for r in mentions if r["flags"]],
            "plain_positive_fn": [r["id"] for r in plain if not r["flags"]],
            "twin_controls_flagged": f"{sum(1 for r in twins if r['flags'])}/{len(twins)}",
            "worker035_battery": {"passed": passed, "total": len(bat_rows),
                                  "verdict": "PASS" if passed == len(bat_rows) else "DEFECTIVE",
                                  "fail_ids": [r["control_id"] for r in bat_rows if not r["pass"]]},
            "fixture_classes": classes,
            "per_fixture": [{"id": r["id"], "expected": r["expected_findings"],
                             "flags": r["flags"],
                             "class": ("TP" if r["expected_findings"] and r["flags"] else
                                       "FN" if r["expected_findings"] and not r["flags"] else
                                       "FP" if not r["expected_findings"] and r["flags"] else "TN")}
                            for r in rows]}


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
        verdicts[arm] = {"corpus_a_pass": a["verdict"] == "PASS",
                         "sensitivity": f"{c['tp']}/{c['tp'] + c['fn']}",
                         "specificity": f"{c['tn']}/{c['tn'] + c['fp']}",
                         "sens_ok": sens >= 5 / 6, "spec_ok": spec >= 9 / 10,
                         "cue_fn_high": d["cue_induced_fn_high_confidence"],
                         "battery": f"{d['worker035_battery']['passed']}/"
                                    f"{d['worker035_battery']['total']}",
                         "meets_bar": (a["verdict"] == "PASS" and sens >= 5 / 6
                                       and spec >= 9 / 10
                                       and d["cue_induced_fn_high_confidence"] == 0)}
    adoptable = [k for k, v in verdicts.items() if v["meets_bar"]]
    if adoptable:
        choice = "a"
    elif (verdicts["PRE"]["sens_ok"] and verdicts["PRE"]["cue_fn_high"] == 0
          and verdicts["APPLIED"]["cue_fn_high"] > 0 and not verdicts["APPLIED"]["spec_ok"]):
        choice = "b"
    else:
        choice = "c"
    return {"choice": choice, "adoption_bar": ADOPTION_BAR, "per_arm": verdicts,
            "adoptable_arms": adoptable}


def cmp_block(mismatch: list, label: str, mine, theirs):
    N_CMP[0] += 1
    if mine != theirs:
        mismatch.append({"block": label, "mine": mine, "adjudication": theirs})


N_CMP = [0]


def main() -> int:
    pins = check_pins()
    before = {rel: sha(ROOT / rel) for rel in list(PINS) + [v[0] for v in ARMS.values()]}
    mods = {arm: load_verified(rel, prefix, f"w021_{arm.lower()}")
            for arm, (rel, prefix) in ARMS.items()}
    lits = extract_literals(CAL, {"LIVE_LABELS", "ASSERTION_MENTION_FIXTURES"})
    snap = ROOT / SNAP

    census = {
        "corpus_a_27fixtures": {a: corpus_a(m) for a, m in mods.items()},
        "corpus_b_live": {a: corpus_b(m, snap, lits["LIVE_LABELS"]) for a, m in mods.items()},
        "corpus_c_assertion_mention": {a: corpus_c(m, lits["ASSERTION_MENTION_FIXTURES"])
                                       for a, m in mods.items()},
        "corpus_d_worker049": {a: corpus_d(m, json.loads((ROOT / W049_CORPUS).read_text()),
                                           json.loads((ROOT / W035).read_text()))
                               for a, m in mods.items()},
    }
    decision = decide(census)

    # --- comparison against the adjudication's own numbers -----------------------------------
    adj = json.loads((ROOT / ADJ).read_text())
    mismatches: list = []
    for arm in ARMS:
        a_mine, a_th = census["corpus_a_27fixtures"][arm], adj["corpus_a_27fixtures"][arm]
        for k in ("tp", "fn", "fp", "tn", "verdict"):
            cmp_block(mismatches, f"corpus_a.{arm}.{k}", a_mine[k], a_th[k])
        b_mine, b_th = census["corpus_b_live"][arm], adj["corpus_b_live"][arm]
        for k in ("hard_total", "soft_total", "claims_flagged", "tp", "fp", "unlabeled_count",
                  "claims_in_map", "labeled_claims"):
            cmp_block(mismatches, f"corpus_b.{arm}.{k}", b_mine[k], b_th.get(k))
        c_mine, c_th = census["corpus_c_assertion_mention"][arm], adj["corpus_c_assertion_mention"][arm]
        for k in ("tp", "fn", "fp", "tn", "sensitivity", "specificity"):
            cmp_block(mismatches, f"corpus_c.{arm}.{k}", c_mine[k], c_th[k])
        d_mine, d_th = (census["corpus_d_worker049"][arm],
                        adj["corpus_d_worker049_cue_fn"][arm])
        for k in ("cue_induced_fn_total", "cue_induced_fn_high_confidence",
                  "adversarial_cleared", "adversarial_total", "mention_fp", "plain_positive_fn",
                  "twin_controls_flagged"):
            cmp_block(mismatches, f"corpus_d.{arm}.{k}", d_mine[k], d_th.get(k))
        cmp_block(mismatches, f"corpus_d.{arm}.battery_passed",
                  d_mine["worker035_battery"]["passed"],
                  d_th["worker035_battery"]["passed"])
        cmp_block(mismatches, f"corpus_d.{arm}.battery_total",
                  d_mine["worker035_battery"]["total"],
                  d_th["worker035_battery"]["total"])
        cmp_block(mismatches, f"corpus_d.{arm}.fixture_classes",
                  d_mine["fixture_classes"], adj["corpus_d_fixture_classes"][arm])
        cmp_block(mismatches, f"decision.{arm}", decision["per_arm"][arm],
                  adj["decision"]["per_arm"][arm])
        for k, v in adj["detectors"].items():
            pass
    cmp_block(mismatches, "decision.choice", decision["choice"], adj["decision"]["choice"])
    cmp_block(mismatches, "decision.adoptable_arms", decision["adoptable_arms"],
              adj["decision"]["adoptable_arms"])
    det_mine = {arm: {"path": rel, "sha256": sha(ROOT / rel)} for arm, (rel, _) in ARMS.items()}
    det_th = {k: {"path": v["path"], "sha256": v["sha256"]} for k, v in adj["detectors"].items()}
    cmp_block(mismatches, "detectors", det_mine, det_th)
    cmp_block(mismatches, "adjudication_sha256", pins[ADJ]["sha256"], pins[ADJ]["expected"])
    cmp_block(mismatches, "attribution_prosefix_high_cue_fn",
              census["corpus_d_worker049"]["PROSEFIX"]["cue_induced_fn_high_confidence"], 10)
    cmp_block(mismatches, "attribution_staged_high_cue_fn",
              census["corpus_d_worker049"]["STAGED"]["cue_induced_fn_high_confidence"], 0)

    # unlabeled auto-mechanism corroboration (card item ii)
    unlabeled_mechs = [u["auto_mechanism"]
                       for u in census["corpus_b_live"]["APPLIED"]["unlabeled"]]
    cmp_block(mismatches, "applied_unlabeled_mechanisms", unlabeled_mechs,
              ["DETECTOR_SELF", "DETECTOR_SELF"])

    # --- controls ----------------------------------------------------------------------------
    controls: list = []

    def ctl(cid, ok, detail):
        controls.append({"id": cid, "pass": bool(ok), "detail": detail})

    # K1 pin-drift detection on a mutated copy
    tmp = HERE / "_k1_mutated_copy.py"
    tmp.write_bytes((ROOT / ARMS["APPLIED"][0]).read_bytes().replace(b"import", b"impart", 1))
    ctl("K1_pin_drift_detected", not sha(tmp).startswith(ARMS["APPLIED"][1]),
        f"mutated copy {sha(tmp)[:12]} does not match {ARMS['APPLIED'][1]}")
    tmp.unlink()

    # K2 bare first-order assertion fires in all arms
    bare = "C0 and C2 are one class in the frozen registry."
    k2 = {a: bool(m.findings_for_text(bare, "ctl-bare")) for a, m in mods.items()}
    ctl("K2_bare_assertion_fires_all_arms", all(k2.values()), k2)

    # K3 quoted assertion is a mention for the heuristic; bare assertion is first-order
    quoted = "'C0 and C2 are one class in the frozen registry.'"
    ctl("K3_heuristic_quoted_vs_bare",
        (first_order_flag(bare) is True) and (first_order_flag(quoted) is False),
        {"bare": first_order_flag(bare), "quoted": first_order_flag(quoted)})

    # K4 determinism: rebuild all four censuses and compare payloads
    census2 = {
        "corpus_a_27fixtures": {a: corpus_a(m) for a, m in mods.items()},
        "corpus_b_live": {a: corpus_b(m, snap, lits["LIVE_LABELS"]) for a, m in mods.items()},
        "corpus_c_assertion_mention": {a: corpus_c(m, lits["ASSERTION_MENTION_FIXTURES"])
                                       for a, m in mods.items()},
        "corpus_d_worker049": {a: corpus_d(m, json.loads((ROOT / W049_CORPUS).read_text()),
                                           json.loads((ROOT / W035).read_text()))
                               for a, m in mods.items()},
    }
    det_ok = all(json.dumps(census[k], sort_keys=True) == json.dumps(census2[k], sort_keys=True)
                 for k in census2)
    ctl("K4_double_run_deterministic", det_ok, "corpus A/B/C/D payloads byte-identical")

    # K5 label-mutation control: flipping A1's truth must move corpus-C sensitivity
    mutated = [(fid, (not truth) if fid == "A1" else truth, text)
               for fid, truth, text in lits["ASSERTION_MENTION_FIXTURES"]]
    m_applied = corpus_c(mods["APPLIED"], mutated)
    ctl("K5_label_mutation_moves_sensitivity",
        m_applied["sensitivity"] != census["corpus_c_assertion_mention"]["APPLIED"]["sensitivity"],
        {"original": census["corpus_c_assertion_mention"]["APPLIED"]["sensitivity"],
         "mutated": m_applied["sensitivity"]})

    # K6 void revision excluded
    applied_sha = sha(ROOT / ARMS["APPLIED"][0])
    ctl("K6_void_revision_excluded",
        applied_sha.startswith(ARMS["APPLIED"][1]) and not applied_sha.startswith(VOID_PREFIX),
        {"applied": applied_sha[:12], "void_prefix": VOID_PREFIX})

    # K7 snapshot identity
    snap_m = json.loads(snap.read_text())
    ctl("K7_snapshot_identity",
        sha(snap) == pins[SNAP]["sha256"] and len(snap_m.get("claims", [])) == 383,
        {"sha256": sha(snap)[:12], "claims": len(snap_m.get("claims", []))})

    # label audit: no labeled-FP claim is a first-order assertion per the heuristic
    la = census["corpus_b_live"]["APPLIED"]["label_audit"]
    ctl("K8_labeled_claims_not_first_order",
        all((not r["first_order_flag"]) and r["composite_token_present"] for r in la),
        {"n_labeled": len(la),
         "first_order_true": [r["claim_index"] for r in la if r["first_order_flag"]],
         "token_absent": [r["claim_index"] for r in la if not r["composite_token_present"]]})

    # post-measurement read-back: every pinned path unchanged, void revision still out
    after = {rel: sha(ROOT / rel) for rel in before}
    moved = {k: {"before": before[k], "after": after[k]} for k in before if before[k] != after[k]}
    ctl("K9_no_write_no_drift", not moved, {"moved": moved})

    # K10 the named worker-075 card path was NOT written by this task (it landed 01:25:14,
    # after this task's measurement; the control records its state instead of asserting absence)
    named = ROOT / "reviews/CLASSSEP-calibration-adjudication-review.json"
    named_state = {"present": named.is_file()}
    if named.is_file():
        named_doc = json.loads(named.read_text())
        named_state.update({"sha256": sha(named), "reviewer": named_doc.get("reviewer"),
                            "verdict": named_doc.get("verdict"),
                            "written_by_this_task": named_doc.get("reviewer") == "worker-021"
                            or sha(named) == sha(ROOT / "reviews/"
                                                 "CLASSSEP-calibration-adjudication-review-021.json")})
    else:
        named_state["written_by_this_task"] = False
    ctl("K10_named_path_not_written_by_this_task",
        not named_state["written_by_this_task"],
        named_state)

    # K11 the 2 unlabeled APPLIED hard findings are detector-self meta-claims
    ctl("K11_unlabeled_are_detector_self", unlabeled_mechs == ["DETECTOR_SELF", "DETECTOR_SELF"],
        {"unlabeled_mechanisms": unlabeled_mechs})

    controls_ok = all(c["pass"] for c in controls)

    payload = {
        "task_id": "W021-CLASSSEP-R3-REVIEW-01",
        "pins": pins,
        "arm_pins_after": {a: sha(ROOT / rel) for a, (rel, _) in ARMS.items()},
        "corpus_a_27fixtures": census["corpus_a_27fixtures"],
        "corpus_b_live": census["corpus_b_live"],
        "corpus_c_assertion_mention": census["corpus_c_assertion_mention"],
        "corpus_d_worker049": census["corpus_d_worker049"],
        "decision": decision,
    }
    with open(HERE / "census.json", "w") as fh:
        json.dump(payload, fh, indent=1, sort_keys=False)
        fh.write("\n")
    with open(HERE / "controls.json", "w") as fh:
        json.dump({"controls": controls, "all_pass": controls_ok}, fh, indent=1)
        fh.write("\n")
    with open(HERE / "comparison.json", "w") as fh:
        json.dump({"mismatches": mismatches, "n_mismatches": len(mismatches),
                   "n_comparisons": N_CMP[0], "controls_all_pass": controls_ok}, fh, indent=1)
        fh.write("\n")

    print(f"pins ok ({len(pins)} entries); arms loaded from verified bytes")
    print(f"{'arm':<9} {'(a)27fx':<16} {'(b)hard':<8} {'(c)sens/spec':<14} "
          f"{'(d)cueH/batt':<14} bar")
    for a in ARMS:
        ca = census["corpus_a_27fixtures"][a]
        cb = census["corpus_b_live"][a]
        cc = census["corpus_c_assertion_mention"][a]
        cd = census["corpus_d_worker049"][a]
        print(f"{a:<9} {ca['verdict']:<16} {cb['hard_total']:<8} "
              f"{cc['sensitivity']}/{cc['specificity']:<9} "
              f"{cd['cue_induced_fn_high_confidence']}/{cd['adversarial_total']} "
              f"batt={cd['worker035_battery']['passed']}/{cd['worker035_battery']['total']:<4} "
              f"{decision['per_arm'][a]['meets_bar']}")
    print(f"DECISION choice={decision['choice']} adoptable={decision['adoptable_arms']}")
    print(f"mismatches vs adjudication: {len(mismatches)}")
    for m in mismatches[:20]:
        print("  -", m["block"], "| mine:", m["mine"], "| adj:", m["adjudication"])
    print(f"controls all_pass={controls_ok}")
    for c in controls:
        if not c["pass"]:
            print("  FAIL", c["id"], c["detail"])
    return 0 if controls_ok and not mismatches else 3


if __name__ == "__main__":
    sys.exit(main())
