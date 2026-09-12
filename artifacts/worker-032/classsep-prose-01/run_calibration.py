#!/usr/bin/env python3
"""W032-CLASSSEP-PROSE-01 independent calibration harness.

Five detector arms, six corpora, two map pins.

Arms:
  CANON      pinned canonical research_map/class_separation.py @ a8c04fc31e4a
  CAND       pinned proposed/class_separation.py @ e2d24b927ee8 (worker-16)
  LEAD_PROSE pinned lead r2 calibration arm (sentence-window + _META), in-memory
  PROSEFIX   pinned worker-049 staged prose fix @ dc8aa0de3869
  MY_R1      staged candidate class_separation_prose_r1.py (this task)

Corpora:
  (a) worker-07 registered 27-fixture falsification corpus
  (b) live hard-finding census at both pins, with r2/r3 published labels as data
  (c) lead r2 16-row labeled assertion-vs-mention corpus
  (d) worker-049 cue-induced-FN corpus (12 adversarial + 12 twins + 7 plain
      positives + 8 mentions), pre-registered before any detector ran
  (e) worker-035 23-fixture battery (9 assertions / 14 non-assertive)
  (f) this task's probe sets P1-P4, N1-N13, O1-O4, B1-B5, Q1-Q3

Read-only on canonical paths. Writes only under
artifacts/worker-032/classsep-prose-01/. Emits no gate verdict.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PIN = HERE / "pinned"
MAP_DESIGN = PIN / "research_map.pin.json"                  # 262da697, 320 claims
MAP_LIVE = PIN / "research_map.live-at-w032.json"           # 5ab4bed18107, 414 claims
CANON_PY = PIN / "class_separation.a8c04fc31e4a.py"
CAND_PY = PIN / "class_separation.e2d24b927ee8.cand.py"
LEAD_PY = PIN / "lead_classsep_calibration.py"
PROSEFIX_PY = PIN / "class_separation.dc8aa0de3869.prosefix.py"
MY_PY = HERE / "candidate/class_separation_prose_r1.py"
CORPUS_A = PIN / "worker07_results.json"
CORPUS_D = PIN / "w049_corpus_d.json"
CORPUS_E = PIN / "w035_battery_e.json"
LEAD_R3 = PIN / "CLASSSEP-calibration-adjudication.r3-life06.json"

EXPECTED_SHA = {
    "canonical_pin": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
    "cand_pin": "e2d24b927ee81c45996f8a4853d2f4b6899e8a3ea405c9e68b1ba5bb37448819",
    "prosefix_pin": "dc8aa0de386931cd0de48e9e755bc9b0bf33a12ce1c464f9911f4e9469f12470",
    "map_design_pin": "262da69798578d7741e1d66dec3ed977d05c4bef296974c36063cb255bee628c",
    "map_live_pin": "5ab4bed181071461f107404f",
    "worker07_results_pin": "d69ad58468be16655921dcf0",
    "w049_corpus_d_pin": "9eb2ea9e27439703ffe7",
    "w035_battery_e_pin": "ef881c3aa6ef392c2068",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- (a) 27 fixtures
def score_27(mod) -> dict:
    res = json.loads(CORPUS_A.read_text())
    tp = fn = fp = tn = 0
    rows = []
    for fx in res["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            rows.append({"id": fx["id"], "class": "MISSING"})
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
        cls = ("TP" if got else "FN") if truth else ("FP" if got else "TN")
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fx["id"], "class": cls, "surface": fx.get("surface"),
                     "n_findings": len(det), "first": det[0][:140] if det else None})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": tp + fn + fp + tn,
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "non_pass_rows": [r for r in rows if r["class"] not in ("TP", "TN")]}


# ---------------------------------------------------------------- (b) live census
def score_live(mod, m: dict, labels=None) -> dict:
    labels = labels or {}
    raw = mod.findings_for_map(m)
    per_claim, other = {}, []
    for x in raw:
        mo = re.search(r"claims\[(\d+)\]", x)
        if mo:
            per_claim.setdefault(int(mo.group(1)), []).append(x)
        else:
            other.append(x)
    hard = [x for x in raw if not x.startswith("CLASSSEP-SOFT:")]
    detail = []
    for idx, finds in sorted(per_claim.items()):
        labs = labels.get(idx, [("UNLABELED", "UNLABELED", "")])
        for k, f in enumerate(finds):
            lab = labs[k] if k < len(labs) else (labs[-1] if labs else ("UNLABELED", "", ""))
            detail.append({"claim_index": idx, "verdict": lab[0], "mechanism": lab[1],
                           "cue": lab[2], "finding": f[:200]})
    return {"hard_total": len(hard), "claim_findings": sum(len(v) for v in per_claim.values()),
            "claims_affected": sorted(per_claim), "n_claims_affected": len(per_claim),
            "tp": sum(1 for d in detail if d["verdict"] == "TP"),
            "fp": sum(1 for d in detail if d["verdict"] == "FP"),
            "unlabeled": [d for d in detail if d["verdict"] == "UNLABELED"],
            "per_finding": detail, "other_hard_findings": other}


# ---------------------------------------------------------------- fixture scoring
def score_fixtures(mod, fixtures):
    rows = []
    for fid, truth, text in fixtures:
        got = bool(mod.findings_for_text(text, f"fixture {fid}"))
        rows.append({"id": fid, "expect": truth, "fired": got, "ok": got == truth})
    tp = sum(1 for r in rows if r["expect"] and r["fired"])
    fn = sum(1 for r in rows if r["expect"] and not r["fired"])
    tn = sum(1 for r in rows if not r["expect"] and not r["fired"])
    fp = sum(1 for r in rows if not r["expect"] and r["fired"])
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(rows),
            "sensitivity": f"{tp}/{tp+fn}" if tp + fn else "n/a",
            "specificity": f"{tn}/{tn+fp}" if tn + fp else "n/a",
            "all_ok": all(r["ok"] for r in rows),
            "wrong": [r for r in rows if not r["ok"]], "rows": rows}


# ------------------------------------------------- (d) worker-049 cue-FN corpus
def score_cuefn(mod, corpus: dict) -> dict:
    fx = {f["id"]: f for f in corpus["fixtures"]}
    fired = {fid: bool(mod.findings_for_text(f["text"], f"fixture {fid}")) for fid, f in fx.items()}
    adv = [f for f in corpus["fixtures"] if f["category"] == "ADVERSARIAL_ASSERTION"]
    twin = {f["twin_of"]: f["id"] for f in corpus["fixtures"] if f["category"] == "TWIN_CONTROL" and f["twin_of"]}
    detail, cleared = [], []
    for f in adv:
        if fired[f["id"]]:
            continue
        cleared.append(f["id"])
        t = twin.get(f["id"])
        if t and fired[t]:
            detail.append({"adversarial": f["id"], "twin": t,
                           "confidence": f.get("confidence"),
                           "cue": f.get("adversarial_cue")})
    twins_flagged = sum(1 for t in twin.values() if fired[t])
    return {
        "cue_induced_fn_total": len(detail),
        "cue_induced_fn_high_confidence": sum(1 for d in detail if d["confidence"] == "HIGH"),
        "cue_induced_fn_detail": detail,
        "adversarial_cleared": cleared,
        "adversarial_total": len(adv),
        "mention_fp": [f["id"] for f in corpus["fixtures"]
                       if f["category"] == "MENTION" and fired[f["id"]]],
        "plain_positive_fn": [f["id"] for f in corpus["fixtures"]
                              if f["category"] == "PLAIN_POSITIVE" and not fired[f["id"]]],
        "twin_controls_flagged": f"{twins_flagged}/{len(twin)}",
        "all_expected_met": (not detail and not [f for f in corpus["fixtures"]
                             if f["category"] == "MENTION" and fired[f["id"]]]
                             and not [f for f in corpus["fixtures"]
                             if f["category"] == "PLAIN_POSITIVE" and not fired[f["id"]]]
                             and twins_flagged == len(twin)),
    }


# ------------------------------------------------- (e) worker-035 23-fixture battery
def score_battery(mod, battery: dict) -> dict:
    rows, fails = [], []
    for x in battery["controls"]:
        expect = x["expect"].startswith("ASSERTION")
        got = bool(mod.findings_for_text(x["text"], f"fixture {x['control_id']}"))
        ok = got == expect
        if not ok:
            fails.append(x["control_id"])
        rows.append({"id": x["control_id"], "expect": x["expect"], "fired": got, "ok": ok})
    pos = [r for r in rows if r["expect"].startswith("ASSERTION")]
    neg = [r for r in rows if not r["expect"].startswith("ASSERTION")]
    return {"pos_pass": sum(1 for r in pos if r["ok"]), "pos_total": len(pos),
            "neg_pass": sum(1 for r in neg if r["ok"]), "neg_total": len(neg),
            "all_pass": not fails, "fail_ids": fails, "rows": rows}


PROBES_P = [
    ("P1", "In this model C0 and C2 are one class on the vacuum sector."),
    ("P2", "We treat C2 and C0 as a single schema for the regularities."),
    ("P3", "The merged C0/C2 class is the authoritative definition."),
    ("P4", "C0/C2 constitutes a single class in the declaration surface."),
]
PROBES_N = [
    ("N1", "the 2 split rows (TC-F0-N14 C0/C2 merge, TC-F0-N15 WCC/SCC merge) need no new class"),
    ("N2", "2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; TC-F0-N15 merged WCC/SCC families)"),
    ("N3", "definitions differing in frozen_regularity (C2 vs C0), so no C0/C2 merge exists at the formal surface"),
    ("N4", "R1's merge pattern matches only bare C0/C2 composites, so 'Sobolev variant' is not flagged"),
    ("N5", "the same slot carrying 'C0 or C2 are one class' is flagged"),
    ("N6", "independent C0/C2 non-merge, quantifier/conclusion assertions, semantic baselines"),
    ("N7", "the live C2/C0 components moved at 00:32:02 so the pins no longer resolve"),
    ("N8", "no C0/C2 merge, canonical structural gate exit 0, class_separation negative"),
    ("N9", "the live false-positive shape '... merged C0/C2 ...' inside a statement is NOT cleared by R2-3"),
    ("N10", "all 10 CLASSSEP hard failures of the form 'composite C0/C2 asserted as one class' are detector false positives"),
    ("N11", "0 genuine assertions that C0 and C2 are one class"),
    ("N12", "the canonical guard misses because \\w+ cannot span 'C0/C2' ('no C0/C2 merge exists')"),
    ("N13", "the 'non-merge' compound and the different clause ('the retired merged file; ... the live C2/C0 components moved')"),
]
PROBES_O = [
    ("O1", "The prior audit found no genuine C0/C2 merge, but this model treats C0 and C2 as one class."),
    ("O2", "This is a non-merge bookkeeping step; C0 and C2 are one class in the declaration surface."),
    ("O3", "The quoted detector output is a false positive; nevertheless C0/C2 is a single class here."),
    ("O4", "C0 and C2 are one class here; this is not a merge."),
]
PROBES_B = [
    ("B1", "C0/C2 constitutes one family in the declaration surface."),
    ("B2", "C0 and C2 are one family of regularities."),
    ("B3", "C0/C2 constitutes one regularity class."),
    ("B4", "C0/C2 forms one family in the declaration surface."),
    ("B5", "C0/C2 is a single family of regularities."),
]
PROBES_Q = [
    ("Q1", False, "The directive says 'never split' the C0 or C2 classes."),
    ("Q2", True, "Do not split the C0 or C2 classes."),
    ("Q3", False, "The reviewer wrote \"do not split: C0 or C2\" but the directive is the opposite."),
]


# ------------------------------------------------- independent converse scan
_ASSERT_CUES = re.compile(
    r"(?:treat|cover|use|take|regard|is|are|as)\s+(?:the\s+)?"
    r"(?:c\s*0\s*(?:or|and|/|,|\+)\s*c\s*2|c\s*2\s*(?:or|and|/|,|\+)\s*c\s*0)\s*"
    r"(?:merged|unified|single|one)?\s*class"
    r"|(?:c0\s+and\s+c2|c2\s+and\s+c0)\s+(?:are|is|form|constitute)\s+"
    r"(?:one|a\s+single|the\s+same)\s+(?:class|family|regularity(?:\s+class)?)"
    r"|(?:merge|merging|combine|unify|conflate)\s+(?:the\s+)?(?:c0\s+and\s+c2|c2\s+and\s+c0)",
    re.I)
_QUOTED = re.compile(r"(?<![A-Za-z0-9])'[^'\n]{2,300}'|\"[^\"\n]{2,300}\"")
_META = re.compile(r"detector|CLASSSEP|pattern|regex|fixture|corpus|probe|false[\s-]?positive|"
                   r"quote|describ|assertion|mention|flag", re.I)
_CASE = re.compile(r"TC-[A-Z0-9]+(?:-[A-Z0-9]+)*|SPLIT_REQUIRED|NEW_CLASS_REQUIRED")
_DENY = re.compile(r"\b(?:no|not|never|without|zero|absent|nor|none|0|rather\s+than)\b", re.I)


def converse_scan(mod, m: dict, flagged_claims: list) -> dict:
    flagged = set(flagged_claims)
    cues, unflagged, genuine = [], [], []
    for i, c in enumerate(m["claims"]):
        st = c.get("statement") or ""
        if not isinstance(st, str):
            st = str(st)
        qspans = [(q.start(), q.end()) for q in _QUOTED.finditer(st)]
        for mo in _ASSERT_CUES.finditer(st):
            lo, hi = max(0, mo.start() - 90), min(len(st), mo.end() + 90)
            quoted = any(a < mo.end() and mo.start() < b for a, b in qspans)
            ctx = st[lo:hi]
            row = {"claim_index": i, "already_flagged": i in flagged, "quoted": quoted,
                   "meta": bool(_META.search(ctx)), "case_label": bool(_CASE.search(ctx)),
                   "denied": bool(_DENY.search(ctx)), "span": ctx}
            cues.append(row)
            if i in flagged:
                continue
            unflagged.append(row)
            if not (quoted or row["meta"] or row["case_label"] or row["denied"]):
                genuine.append(row)
    return {"cue_matches": len(cues), "unflagged_candidates": len(unflagged),
            "unflagged_detail": unflagged[:20], "genuine_unflagged": genuine,
            "note": "genuine_unflagged is the false-negative candidate set; it is empty iff "
                    "no first-order merge assertion escaped the arm"}


# ------------------------------------------------- declaration-mode differential
def declaration_differential(canon, mine, m: dict) -> dict:
    diffs = []
    for gi, g in enumerate(m.get("groups", [])):
        if isinstance(g.get("direction"), str):
            where = f"groups[{g.get('id', gi)}].direction"
            a = canon.findings({"direction": g["direction"]}, where)
            b = mine.findings({"direction": g["direction"]}, where)
            if a != b:
                diffs.append({"where": where, "canon": a, "mine": b})
        for n in g.get("nodes", []):
            where = f"node {n.get('id', '?')}"
            a, b = canon.findings(n, where), mine.findings(n, where)
            if a != b:
                diffs.append({"where": where, "canon": a, "mine": b})
    for i, ev in enumerate(m.get("portfolio_events", [])):
        if isinstance(ev, dict):
            where = f"portfolio_events[{i}]"
            a, b = canon.findings(ev, where), mine.findings(ev, where)
            if a != b:
                diffs.append({"where": where, "canon": a, "mine": b})
    return {"n_diffs": len(diffs), "diffs": diffs[:10],
            "note": "non-empty diffs are expected iff the extended assertion vocabulary "
                    "reaches a declaration surface; every diff must be inspected"}


def labels_from_r3(adj: dict):
    out = {}
    det = adj.get("corpus_b_live_detail", {}).get("APPLIED", {})
    for row in det.get("labeled_detail", []):
        out.setdefault(row["claim_index"], []).append(
            (row["verdict"], row["mechanism"], row["cue"]))
    return out


def main() -> int:
    t0 = time.time()
    m_design = json.loads(MAP_DESIGN.read_text())
    m_live = json.loads(MAP_LIVE.read_text())
    adj = json.loads(LEAD_R3.read_text())
    labels_r3 = labels_from_r3(adj)
    lead_mod = load(LEAD_PY, "lead_calib")
    fixtures_c = lead_mod.ASSERTION_MENTION_FIXTURES
    corpus_d = json.loads(CORPUS_D.read_text())
    battery_e = json.loads(CORPUS_E.read_text())

    arms = {
        "CANON": load(CANON_PY, "arm_canon"),
        "CAND": load(CAND_PY, "arm_cand"),
        "LEAD_PROSE": lead_mod.make_prose_arm(CANON_PY),
        "PROSEFIX": load(PROSEFIX_PY, "arm_prosefix"),
        "MY_R1": load(MY_PY, "arm_my"),
    }

    out = {
        "artifact": "W032-CLASSSEP-PROSE-R1",
        "task_id": "W032-CLASSSEP-PROSE-01",
        "worker": "worker-032",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "question": "Can one staged revision along the PROSE direction close R-a..R-d, the A6 "
                    "sensitivity gap and worker-049's cue-induced-FN battery, guarded against "
                    "quoted 'do not split', without the 27-fixture regression and without "
                    "over-suppressing concessive first-order assertions?",
        "pins": {
            "map_design": {"path": str(MAP_DESIGN.relative_to(ROOT)), "sha256": sha(MAP_DESIGN),
                           "updated_at": m_design["updated_at"], "n_claims": len(m_design["claims"])},
            "map_live_at_w032": {"path": str(MAP_LIVE.relative_to(ROOT)), "sha256": sha(MAP_LIVE),
                                 "updated_at": m_live["updated_at"], "n_claims": len(m_live["claims"])},
            "canonical": {"path": str(CANON_PY.relative_to(ROOT)), "sha256": sha(CANON_PY)},
            "cand": {"path": str(CAND_PY.relative_to(ROOT)), "sha256": sha(CAND_PY)},
            "prosefix": {"path": str(PROSEFIX_PY.relative_to(ROOT)), "sha256": sha(PROSEFIX_PY)},
            "candidate": {"path": str(MY_PY.relative_to(ROOT)), "sha256": sha(MY_PY)},
            "lead_r3_adjudication": {"path": str(LEAD_R3.relative_to(ROOT)), "sha256": sha(LEAD_R3)},
            "worker07_results": {"path": str(CORPUS_A.relative_to(ROOT)), "sha256": sha(CORPUS_A)},
            "w049_corpus_d": {"path": str(CORPUS_D.relative_to(ROOT)), "sha256": sha(CORPUS_D)},
            "w035_battery_e": {"path": str(CORPUS_E.relative_to(ROOT)), "sha256": sha(CORPUS_E)},
        },
        "hash_checks": {},
        "corpus_a_27fixtures": {k: score_27(v) for k, v in arms.items()},
        "corpus_b_live_design_pin": {k: score_live(v, m_design, lead_mod.LIVE_LABELS)
                                     for k, v in arms.items()},
        "corpus_b_live_current_pin": {k: score_live(v, m_live, labels_r3) for k, v in arms.items()},
        "corpus_c_assertion_mention": {k: score_fixtures(v, fixtures_c) for k, v in arms.items()},
        "corpus_d_worker049_cuefn": {k: score_cuefn(v, corpus_d) for k, v in arms.items()},
        "corpus_e_worker035_battery": {k: score_battery(v, battery_e) for k, v in arms.items()},
        "probes": {
            "P_positive": {k: score_fixtures(v, [(i, True, t) for i, t in PROBES_P]) for k, v in arms.items()},
            "N_negative": {k: score_fixtures(v, [(i, False, t) for i, t in PROBES_N]) for k, v in arms.items()},
            "O_over_suppression": {k: score_fixtures(v, [(i, True, t) for i, t in PROBES_O]) for k, v in arms.items()},
            "B_blind_spot": {k: score_fixtures(v, [(i, True, t) for i, t in PROBES_B]) for k, v in arms.items()},
            "Q_adversarial": {k: score_fixtures(v, [(i, e, t) for i, e, t in PROBES_Q]) for k, v in arms.items()},
        },
        "converse_scan_design_pin": {
            k: converse_scan(v, m_design, out_claims)
            for k, v in arms.items()
            for out_claims in [score_live(v, m_design, lead_mod.LIVE_LABELS)["claims_affected"]]},
        "converse_scan_current_pin": {
            k: converse_scan(v, m_live, out_claims)
            for k, v in arms.items()
            for out_claims in [score_live(v, m_live, labels_r3)["claims_affected"]]},
        "declaration_mode_differential": declaration_differential(arms["CANON"], arms["MY_R1"], m_design),
    }

    for label, path in [("canonical_pin", CANON_PY), ("cand_pin", CAND_PY),
                        ("prosefix_pin", PROSEFIX_PY), ("map_design_pin", MAP_DESIGN),
                        ("map_live_pin", MAP_LIVE), ("worker07_results_pin", CORPUS_A),
                        ("w049_corpus_d_pin", CORPUS_D), ("w035_battery_e_pin", CORPUS_E)]:
        got = sha(path)
        out["hash_checks"][label] = {"path": str(path.relative_to(ROOT)), "sha256": got,
                                     "expected": EXPECTED_SHA[label],
                                     "match": got.startswith(EXPECTED_SHA[label])}

    a = out["corpus_a_27fixtures"]["MY_R1"]
    c = out["corpus_c_assertion_mention"]["MY_R1"]
    b = out["corpus_b_live_design_pin"]["MY_R1"]
    bl = out["corpus_b_live_current_pin"]["MY_R1"]
    d = out["corpus_d_worker049_cuefn"]["MY_R1"]
    e = out["corpus_e_worker035_battery"]["MY_R1"]
    o = out["probes"]["O_over_suppression"]["MY_R1"]
    q = out["probes"]["Q_adversarial"]["MY_R1"]
    crit = [
        {"id": "AC-1", "criterion": "27-fixture corpus stays PASS 17/0/10/0",
         "measured": f"TP{a['tp']} FN{a['fn']} FP{a['fp']} TN{a['tn']} {a['verdict']}",
         "pass": a["verdict"] == "PASS"},
        {"id": "AC-2", "criterion": "labeled assertion-vs-mention: sensitivity >= 5/6 and specificity >= 9/10",
         "measured": f"sensitivity {c['sensitivity']}, specificity {c['specificity']}",
         "pass": c["tp"] >= 5 and c["tn"] >= 9},
        {"id": "AC-3", "criterion": "live census at design pin: 0 hard findings whose only cue is negation, "
                                    "case-label, quotation, detector-self or cross-clause adjacency",
         "measured": f"hard={b['hard_total']} claims={b['claims_affected']} "
                     f"labeled_fp={b['fp']} unlabeled={len(b['unlabeled'])}",
         "pass": b["hard_total"] == 0},
        {"id": "AC-4", "criterion": "no over-suppression: concessive O1-O4 fire; quoted 'do not split' silent, "
                                    "unquoted fires (Q1-Q3)",
         "measured": f"O probes {o['tp']}/{o['tp']+o['fn']} fired; Q {q['tp']+q['tn']}/{q['n']} correct",
         "pass": o["fn"] == 0 and q["all_ok"]},
        {"id": "AC-5", "criterion": "worker-049 cue-FN corpus: 0 HIGH-confidence cue-induced FN, 0 mention FP, "
                                    "12/12 twins flagged",
         "measured": f"high_cue_fn={d['cue_induced_fn_high_confidence']} "
                     f"mention_fp={d['mention_fp']} twins={d['twin_controls_flagged']} "
                     f"plain_pos_fn={d['plain_positive_fn']}",
         "pass": d["cue_induced_fn_high_confidence"] == 0 and not d["mention_fp"]
                 and d["twin_controls_flagged"] == "12/12" and not d["plain_positive_fn"]},
        {"id": "AC-6", "criterion": "worker-035 battery 23/23 (9 assertions / 14 non-assertive)",
         "measured": f"pos {e['pos_pass']}/{e['pos_total']}, neg {e['neg_pass']}/{e['neg_total']}",
         "pass": e["all_pass"]},
        {"id": "AC-7", "criterion": "current-pin spot check: candidate hard count on the 414-claim live map "
                                    "is <= canonical and contains no genuine assertion",
         "measured": f"canonical={out['corpus_b_live_current_pin']['CANON']['hard_total']} "
                     f"candidate={bl['hard_total']} candidate_claims={bl['claims_affected']}",
         "pass": bl["hard_total"] <= out["corpus_b_live_current_pin"]["CANON"]["hard_total"]
                 and bl["tp"] == 0},
    ]
    out["acceptance"] = {"criteria": crit, "all_pass": all(x["pass"] for x in crit)}

    canon_c = out["corpus_c_assertion_mention"]["CANON"]
    lead_c = out["corpus_c_assertion_mention"]["LEAD_PROSE"]
    pf = out["corpus_d_worker049_cuefn"]["PROSEFIX"]
    out["decision"] = {
        "verdict_on_my_r1": "STAGE-AS-ADOPTABLE-CANDIDATE" if out["acceptance"]["all_pass"]
                            else "NOT-YET-ADOPTABLE",
        "deltas_vs_canonical": {
            "corpus_c_sens": f"{canon_c['sensitivity']} -> {c['sensitivity']}",
            "corpus_c_spec": f"{canon_c['specificity']} -> {c['specificity']}",
            "live_hard_design_pin": f"{out['corpus_b_live_design_pin']['CANON']['hard_total']} -> {b['hard_total']}",
            "live_hard_current_pin": f"{out['corpus_b_live_current_pin']['CANON']['hard_total']} -> {bl['hard_total']}",
        },
        "deltas_vs_lead_prose": {
            "corpus_c_sens": f"{lead_c['sensitivity']} -> {c['sensitivity']}",
            "corpus_c_spec": f"{lead_c['specificity']} -> {c['specificity']}",
            "live_hard_design_pin": f"{out['corpus_b_live_design_pin']['LEAD_PROSE']['hard_total']} -> {b['hard_total']}",
        },
        "deltas_vs_prosefix_worker049": {
            "corpus_c_sens": f"{out['corpus_c_assertion_mention']['PROSEFIX']['sensitivity']} -> {c['sensitivity']}",
            "corpus_c_spec": f"{out['corpus_c_assertion_mention']['PROSEFIX']['specificity']} -> {c['specificity']}",
            "cue_fn_high": f"{pf['cue_induced_fn_high_confidence']} -> {d['cue_induced_fn_high_confidence']}",
            "mention_fp": f"{len(pf['mention_fp'])} -> {len(d['mention_fp'])}",
            "battery_e": f"{out['corpus_e_worker035_battery']['PROSEFIX']['pos_pass'] + out['corpus_e_worker035_battery']['PROSEFIX']['neg_pass']}"
                         f"/23 -> {e['pos_pass'] + e['neg_pass']}/23",
        },
        "known_residual_fn": "corpus_c A5 'The two regularities should be merged into a single class' "
                             "has no C0/C2 token; closing it needs a family-level cue this candidate "
                             "deliberately does not add (see limits).",
        "no_gate_self_pass": "Worker measurement evidence. Sets no gate verdict, no validation_status, "
                             "edits no canonical file; controller ownership of "
                             "research_map/class_separation.py is unchanged.",
        "recommended_next": "Controller stages candidate/class_separation_prose_r1.py (or equivalent) "
                            "behind the P1-P6 retirement policy; the audit lead re-runs this harness "
                            "plus runtime/bin/classsep_regression.py at the new pin and publishes raw "
                            "and calibrated hard counts together.",
    }
    out["falsifier"] = (
        "Falsified if, at the pinned arms/corpora above: (i) the 27-fixture corpus is not PASS 17/0/10/0 "
        "for MY_R1; (ii) any of P1-P4, O1-O4 or B1-B5 fails to fire, or any of N1-N13 or the lead's "
        "M1-M10 fires, under MY_R1; (iii) a genuine unflagged first-order C0/C2 merge appears in either "
        "converse scan; (iv) any live hard finding at the design pin survives whose only cue is negation, "
        "case-label, quotation, detector-self description or cross-clause adjacency; (v) the "
        "declaration-mode differential shows an unattributed change; (vi) a quoted 'do not split: C0 or "
        "C2' fires (Q1/Q3) while an unquoted one does not (Q2/A6); or (vii) any HIGH-confidence "
        "cue-induced FN, mention FP or twin-control clear appears in worker-049's corpus, or the "
        "worker-035 battery drops below 23/23.")
    out["limits"] = [
        "corpus_c A5 remains a false negative by design: no family-level ('the two regularities') merge "
        "rule is added, because it would fire on the same meta-traffic the census is trying to clear.",
        "The live map moves (320 -> 383 -> 414 claims during this task); every number binds only to the "
        "two pinned map hashes and must be re-measured at the next tick.",
        "Q1-Q3, P/N/O/B probes and the converse classifier are this task's own controls; corpus (d) and "
        "(e) are worker-049's pre-registered corpora, re-scored here by an independently written harness.",
        "The candidate is a staged file under artifacts/worker-032/; it has not been applied, reviewed "
        "by a second agent, or run by the controller audit tick.",
    ]
    out["elapsed_sec"] = round(time.time() - t0, 2)
    out["runner_checks"] = {
        "canonical_pin_matches": out["hash_checks"]["canonical_pin"]["match"],
        "cand_pin_matches": out["hash_checks"]["cand_pin"]["match"],
        "prosefix_pin_matches": out["hash_checks"]["prosefix_pin"]["match"],
        "map_design_pin_matches": out["hash_checks"]["map_design_pin"]["match"],
        "map_live_pin_matches": out["hash_checks"]["map_live_pin"]["match"],
        "candidate_is_distinct": sha(MY_PY) != sha(CANON_PY),
        "declaration_differential_clean": out["declaration_mode_differential"]["n_diffs"] == 0,
    }

    (HERE / "report.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"design pin {sha(MAP_DESIGN)[:12]} ({len(m_design['claims'])} claims)  "
          f"live pin {sha(MAP_LIVE)[:12]} ({len(m_live['claims'])} claims)  elapsed {out['elapsed_sec']}s")
    print(f"{'arm':<11}{'27fix':<20}{'live320':<18}{'live414':<18}{'c sens/spec':<14}"
          f"{'d hiFN/mFP':<14}{'e battery'}")
    for k in arms:
        a = out["corpus_a_27fixtures"][k]
        b = out["corpus_b_live_design_pin"][k]
        bl = out["corpus_b_live_current_pin"][k]
        c = out["corpus_c_assertion_mention"][k]
        d = out["corpus_d_worker049_cuefn"][k]
        e = out["corpus_e_worker035_battery"][k]
        print(f"{k:<11}{'TP'+str(a['tp'])+' FN'+str(a['fn'])+' FP'+str(a['fp']):<20}"
              f"{'hard='+str(b['hard_total']):<18}{'hard='+str(bl['hard_total']):<18}"
              f"{c['sensitivity']+'/'+c['specificity']:<14}"
              f"{str(d['cue_induced_fn_high_confidence'])+'/'+str(len(d['mention_fp'])):<14}"
              f"{e['pos_pass']+e['neg_pass']}/23")
    print(f"MY_R1 acceptance all_pass={out['acceptance']['all_pass']} :: " +
          "; ".join(f"{x['id']}={'PASS' if x['pass'] else 'FAIL'}" for x in crit))
    print(f"converse MY_R1 genuine_unflagged={len(out['converse_scan_design_pin']['MY_R1']['genuine_unflagged'])} "
          f"(design) / {len(out['converse_scan_current_pin']['MY_R1']['genuine_unflagged'])} (live)")
    print(f"declaration differential diffs={out['declaration_mode_differential']['n_diffs']}")
    print(f"-> {(HERE / 'report.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
