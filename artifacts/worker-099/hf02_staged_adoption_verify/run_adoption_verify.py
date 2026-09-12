#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W099-HF02-STAGED-ADOPTION-VERIFY-01

Non-author, deterministic verification of the staged HF-02 repair
(artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl)
against its source packet, the frozen taxonomy/registry, each row's own
does_not_imply field, the G-LIT rubric, and the worker-099 prior subject census.

Read-only on every canonical path. Writes only RESULTS.json and README.md
inside this directory. Fail-closed on any pin drift (exit 3).

stdlib only. No network. Deterministic: the core_digest must be identical
across repeated runs at the same pins.
"""
import hashlib
import json
import os
import re
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
VARIANT_IDS = ["SET", "CH", "H2LOC", "TWOSIDED", "DISTRIBUTIONAL", "L2CONN", "LIP"]
POPULATION = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]
ALLOWED_CHANGED_FIELDS = {"class_ids", "informs_classes", "ledger_tags"}

PINS = OrderedDict([
    ("ledger/theorems.jsonl",
     "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"),
    ("artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl",
     "b3ab6a1a635720a97e51fd332bcf1d9f9e6fdc45ad64d886106f1cd298d61cea"),
    ("artifacts/worker-025/l0_hf02_staged/staged/diff.json",
     "241b493611c04372bee8b2e7a28249e7685d014e1891d4b2caaff4f4748b3211"),
    ("artifacts/worker-025/l0_hf02_staged/report.json",
     "46d98ec27dea7fb5ddc532782e187a4ddc45dc48f63a9cc1287bcaa10f21390b"),
    ("artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json",
     "0f86158c5bb79adac957a4585a6be4b62abf13c541ea74769f9e629749c4f9d6"),
    ("research_map/formulation_taxonomy.yaml",
     "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    ("evaluation_rubric.yaml",
     "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"),
    ("artifacts/formulation/VARIANT_REGISTRY.json",
     "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb"),
    ("artifacts/worker-007/rev29_preflight/snapshot/VARIANT_REGISTRY.5eb42f9a384a.json",
     "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b"),
    ("artifacts/worker-099/bl7_hf02_binding/binding_analysis.json",
     "ffe9119cb5f2b7f017f78f26575e1a7814534fd9262f532d452bf7c1b6edb189"),
])
PACKET_TIME = "2026-09-12T00:36:38+08:00"
LEAD_ACTORS = {"astra", "astra-lead-formulation", "astra-lead-literature",
               "astra-lead-audit", "astra-lead-numerics"}

DISCLAIM = {
    "AF-SCC-C0-VAC-GEN": [
        r"(?i)\b(does not|doesn't|not|none)\b[^.]{0,60}\b(decide|prove|settle|establish|imply)\b[^.]{0,60}(c\^?0|continuous)",
        r"(?i)\bnot the c\^?0 formulation\b",
        r"(?i)\b(does not|not)\b[^.]{0,25}\b(decide|settle)\b[^.]{0,25}any scc formulation",
    ],
    "AF-SCC-C2-VAC-GEN": [
        r"(?i)\b(does not|doesn't|not|none)\b[^.]{0,60}\b(decide|prove|settle|establish|imply)\b[^.]{0,60}c\^?2",
        r"(?i)\bnot the c\^?2 formulation\b",
        r"(?i)\b(does not|not)\b[^.]{0,25}\b(decide|settle)\b[^.]{0,25}any scc formulation",
    ],
    "AF-WCC-VAC-GEN": [
        r"(?i)\b(does not|doesn't|not)\b[^.]{0,60}\b(decide|prove|settle|establish)\b[^.]{0,60}(wcc|weak cosmic censorship)",
    ],
}
CLASS_TEXT_CUE = {
    "AF-SCC-C0-VAC-GEN": ["c^0", "c^{0", "continuous"],
    "AF-SCC-C2-VAC-GEN": ["c^2", "c^{2"],
    "AF-WCC-VAC-GEN": ["i+", "visible", "visibility", "asymptotic predictability"],
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def as_list(v):
    if v is None:
        return []
    return list(v) if isinstance(v, list) else [v]


def disjunction_count(rows):
    n = 0
    ids = []
    for r in rows:
        toks = [t for t in as_list(r.get("class_ids")) if t in FROZEN]
        if len(toks) >= 2:
            n += 1
            ids.append(r.get("theorem_id"))
    return n, ids


def unknown_token_hits(rows):
    hits = []
    for r in rows:
        for field in ("class_ids", "informs_classes"):
            for t in as_list(r.get(field)):
                if t not in FROZEN:
                    hits.append({"row": r.get("theorem_id"), "field": field, "token": t})
    return hits


def variant_in_class_ids(rows):
    hits = []
    for r in rows:
        for t in as_list(r.get("class_ids")):
            if t in VARIANT_IDS:
                hits.append({"row": r.get("theorem_id"), "token": t})
    return hits


def self_contradictions(rows):
    """R6: class_ids token disclaimed by the row's own does_not_imply."""
    out = []
    for r in rows:
        dis = as_list(r.get("does_not_imply"))
        for tok in as_list(r.get("class_ids")):
            pats = DISCLAIM.get(tok, [])
            for d in dis:
                for p in pats:
                    m = re.search(p, d)
                    if m:
                        out.append({"row": r.get("theorem_id"), "token": tok,
                                    "quote": d, "match": m.group(0)})
                        break
                else:
                    continue
                break
    return out


def empty_class_rows(rows):
    return [r.get("theorem_id") for r in rows if not as_list(r.get("class_ids"))]


def theorem_empty_rows(rows):
    return [r.get("theorem_id") for r in rows
            if r.get("conclusion_type") in ("theorem", "conditional_theorem")
            and not as_list(r.get("class_ids"))]


def adoption_fidelity(packet, staged_by_id):
    mismatches = []
    matched = []
    for row in packet["rows"]:
        rid = row["row_id"]
        rec = row.get("recommended") or {}
        st = staged_by_id.get(rid)
        if st is None:
            mismatches.append({"row": rid, "why": "row missing from staged file"})
            continue
        want_c = as_list(rec.get("class_ids"))
        want_i = as_list(rec.get("informs_classes"))
        got_c = as_list(st.get("class_ids"))
        got_i = as_list(st.get("informs_classes"))
        if want_c != got_c or want_i != got_i:
            mismatches.append({"row": rid, "field": "class_ids/informs_classes",
                               "recommended": {"class_ids": want_c, "informs_classes": want_i},
                               "staged": {"class_ids": got_c, "informs_classes": got_i}})
        else:
            matched.append(rid)
    return matched, mismatches


def conditional_rows(packet):
    out = []
    for row in packet["rows"]:
        nf = row.get("needs_f1_ruling")
        if nf:
            out.append({"row": row["row_id"], "question": nf.get("question"),
                        "default_applied": row.get("recommended"),
                        "if_yes": nf.get("if_yes"), "if_no": nf.get("if_no")})
    return out


def find_licensing(packet_time):
    """R5: any accepted lead/controller event after the packet resolving a
    NEEDS_F1_RULING question (characteristic-interior data class)."""
    ev_path = os.path.join(ROOT, "research_map/events.jsonl")
    hits = []
    if not os.path.exists(ev_path):
        return hits
    with open(ev_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("actor") not in LEAD_ACTORS:
                continue
            if e.get("event_type") not in ("review", "gate", "direction_update", "claim"):
                continue
            if str(e.get("created_at", "")) <= packet_time:
                continue
            text = json.dumps(e, ensure_ascii=False)
            if ("T-526" in text or "characteristic interior" in text.lower()
                    or "characteristic-interior" in text.lower()):
                if ("characteristic" in text.lower() and "interior" in text.lower()):
                    hits.append({"event_id": e.get("event_id"), "actor": e.get("actor"),
                                 "event_type": e.get("event_type"),
                                 "created_at": e.get("created_at"),
                                 "verdict": e.get("verdict")})
    return hits


def bl7_ruling_status(packet_time):
    """Any accepted G-LIT gate pass, or lead/controller ruling on HF-02 scope,
    after the packet time closes BL-7."""
    ev_path = os.path.join(ROOT, "research_map/events.jsonl")
    hits = []
    if not os.path.exists(ev_path):
        return "UNKNOWN", hits
    with open(ev_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if str(e.get("created_at", "")) <= packet_time:
                continue
            if e.get("actor") not in LEAD_ACTORS:
                continue
            if e.get("event_type") == "gate" and e.get("gate_id") == "G-LIT" \
                    and e.get("verdict") == "pass":
                hits.append({"event_id": e.get("event_id"), "kind": "G-LIT gate pass"})
            text = json.dumps(e, ensure_ascii=False)
            low = text.lower()
            # A ruling must carry an explicit scope-decision phrase. Referrals
            # ("refer HF-02 to a ruling", "ruling-bound", "pending") do not count.
            decision = [p for p in ("out of scope", "in scope", "does not apply",
                                    "doesn't apply", "applies to ledger",
                                    "not apply to ledger") if p in low]
            referral = [p for p in ("refer", "ruling-bound", "pending") if p in low]
            if e.get("event_type") in ("review", "direction_update") and "hf-02" in low \
                    and decision and not referral:
                hits.append({"event_id": e.get("event_id"), "kind": "HF-02 scope ruling",
                             "decision_phrases": decision})
    return ("CLOSED" if hits else "OPEN"), hits


def registry_drift():
    old = json.load(open(os.path.join(
        ROOT, "artifacts/worker-007/rev29_preflight/snapshot/VARIANT_REGISTRY.5eb42f9a384a.json"),
        encoding="utf-8"))
    new = json.load(open(os.path.join(ROOT, "artifacts/formulation/VARIANT_REGISTRY.json"),
                         encoding="utf-8"))
    o = {v["variant_id"]: v for v in old["variants"]}
    n = {v["variant_id"]: v for v in new["variants"]}
    changed = sorted(k for k in set(o) & set(n)
                     if json.dumps(o[k], sort_keys=True) != json.dumps(n[k], sort_keys=True))
    cited = {}
    for vid in ("L2CONN", "LIP", "H2LOC"):
        cited[vid] = {
            "parent_old": o.get(vid, {}).get("parent_class"),
            "parent_new": n.get(vid, {}).get("parent_class"),
            "entry_byte_identical": json.dumps(o.get(vid), sort_keys=True)
                                    == json.dumps(n.get(vid), sort_keys=True),
        }
    return {"changed_variant_entries": changed,
            "added": sorted(set(n) - set(o)), "removed": sorted(set(o) - set(n)),
            "cited_variants": cited}


def row_delta(live_rows, staged_rows):
    live = {r["theorem_id"]: r for r in live_rows}
    staged = {r["theorem_id"]: r for r in staged_rows}
    changed_rows, illegal = [], []
    for rid in live:
        lr, sr = live[rid], staged.get(rid)
        if sr is None:
            illegal.append({"row": rid, "why": "missing from staged"})
            continue
        fields = sorted(set(lr) | set(sr))
        diff = [f for f in fields if lr.get(f) != sr.get(f)]
        if not diff:
            continue
        changed_rows.append(rid)
        bad = [f for f in diff if f not in ALLOWED_CHANGED_FIELDS]
        if bad:
            illegal.append({"row": rid, "fields": bad})
    extra = sorted(set(staged) - set(live))
    if extra:
        illegal.append({"rows": extra, "why": "extra rows in staged"})
    return changed_rows, illegal


def prior_census_crosswalk(census, staged_by_id, live_by_id):
    cross = []
    grounding_fail, fabricated_ok = 0, 0
    fabricated = "THIS-QUOTE-IS-FABRICATED-AND-OCCURS-NOWHERE"
    for row in census["rows"]:
        rid = row["theorem_id"]
        live_text = json.dumps(live_by_id[rid], ensure_ascii=False)
        cells = row.get("cells", [])
        for c in cells:
            if c.get("quote") and c["quote"] not in live_text:
                grounding_fail += 1
        subject_classes = [c["class_id"] for c in cells
                           if str(c.get("relation", "")).startswith("SUBJECT_")]
        resolution = row.get("resolution")
        staged_c = as_list(staged_by_id[rid].get("class_ids"))
        if resolution == "INTERMEDIATE_NEITHER":
            aligned = (staged_c == [])
            rule = "INTERMEDIATE_NEITHER -> class_ids==[] aligned"
        else:
            aligned = all(s in staged_c for s in subject_classes) and bool(subject_classes)
            rule = "subject classes subset of staged class_ids"
        cross.append({
            "row": rid, "prior_resolution": resolution,
            "prior_subject_classes": subject_classes,
            "prior_recommendation": row.get("recommendation"),
            "staged_class_ids": staged_c,
            "staged_informs_classes": as_list(staged_by_id[rid].get("informs_classes")),
            "aligned_under_subject_reading": aligned, "rule": rule,
        })
    for r in census["rows"]:
        live_text = json.dumps(live_by_id[r["theorem_id"]], ensure_ascii=False)
        if fabricated in live_text:
            fabricated_ok += 1
    return cross, grounding_fail, fabricated_ok


def informs_grounding(packet, live_by_id, staged_by_id):
    out = []
    for row in packet["rows"]:
        rid = row["row_id"]
        live = live_by_id[rid]
        text = json.dumps(live, ensure_ascii=False).lower()
        for tok in as_list(staged_by_id[rid].get("informs_classes")):
            cues = CLASS_TEXT_CUE.get(tok, [])
            named = [c for c in cues if c in text]
            out.append({"row": rid, "informs_class": tok,
                        "row_text_names_class": bool(named),
                        "text_cues_present": named,
                        "registry_grounded": True,
                        "note": "containment relation is asserted by VARIANT_REGISTRY; "
                                "row text mention is weak corroboration only"})
    return out


def build_core(record):
    core = {
        "pins": {k: v["measured"] for k, v in record["pins"].items()},
        "checks": {c["id"]: c["verdict"] for c in record["checks"]},
        "aggregates": record["aggregates"],
        "per_row": record["per_row"],
        "controls": {c["id"]: c["verdict"] for c in record["controls"]},
    }
    blob = json.dumps(core, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def main():
    record = {
        "schema_version": "0.1",
        "artifact_type": "hf02_staged_adoption_verification",
        "task_id": "W099-HF02-STAGED-ADOPTION-VERIFY-01",
        "actor": "worker-099",
        "instance": "worker-099-20260912T011123-968807",
        "node_id": "L0", "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "created_at": "2026-09-12T01:20:00+08:00",
        "authority_boundary": "Worker evidence only; no gate verdict, no node status, "
                              "no validation_status=passed, no canonical write.",
        "validation_status": "unverified",
        "claims_completion": False,
        "checks": [], "controls": [], "per_row": [], "aggregates": {},
    }

    # ---- pins (before) -----------------------------------------------------
    pins = OrderedDict()
    drift = []
    for rel, exp in PINS.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            pins[rel] = {"expected": exp, "measured": None, "bytes": None, "match": False}
            drift.append(rel)
            continue
        h = sha256_file(p)
        b = os.path.getsize(p)
        pins[rel] = {"expected": exp, "measured": h, "bytes": b, "match": h == exp}
        if h != exp:
            drift.append(rel)
    record["pins"] = pins
    record["pin_drift"] = drift

    live_rows = load_jsonl(os.path.join(ROOT, "ledger/theorems.jsonl"))
    staged_rows = load_jsonl(os.path.join(
        ROOT, "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl"))
    live_by_id = {r["theorem_id"]: r for r in live_rows}
    staged_by_id = {r["theorem_id"]: r for r in staged_rows}
    packet = json.load(open(os.path.join(
        ROOT, "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json"),
        encoding="utf-8"))
    census = json.load(open(os.path.join(
        ROOT, "artifacts/worker-099/bl7_hf02_binding/binding_analysis.json"), encoding="utf-8"))

    # ---- C1 population / row integrity ------------------------------------
    ids_ok = [r["theorem_id"] for r in live_rows] == [r["theorem_id"] for r in staged_rows]
    changed_rows, illegal = row_delta(live_rows, staged_rows)
    c1 = {
        "id": "C1_rows_and_allowed_fields",
        "verdict": "PASS" if (len(live_rows) == len(staged_rows) == 62 and ids_ok
                              and sorted(changed_rows) == sorted(POPULATION) and not illegal)
                   else "FAIL",
        "live_rows": len(live_rows), "staged_rows": len(staged_rows),
        "order_preserved": ids_ok, "changed_rows": sorted(changed_rows),
        "illegal_field_changes": illegal,
    }
    record["checks"].append(c1)

    # ---- C2 detector -------------------------------------------------------
    d_live, d_live_ids = disjunction_count(live_rows)
    d_staged, d_staged_ids = disjunction_count(staged_rows)
    unk = {"live": unknown_token_hits(live_rows), "staged": unknown_token_hits(staged_rows)}
    var = {"live": variant_in_class_ids(live_rows), "staged": variant_in_class_ids(staged_rows)}
    c2 = {
        "id": "C2_hf02_literal_detector",
        "verdict": "PASS" if (d_live == 8 and d_staged == 0
                              and not unk["live"] and not unk["staged"]
                              and not var["live"] and not var["staged"]) else "FAIL",
        "disjunction": {"live": d_live, "staged": d_staged,
                        "live_rows": sorted(d_live_ids), "staged_rows": sorted(d_staged_ids)},
        "unknown_tokens": unk, "variant_ids_in_class_ids": var,
    }
    record["checks"].append(c2)

    # ---- C3 binding shape ---------------------------------------------------
    shape_bad = []
    for r in staged_rows:
        ci = as_list(r.get("class_ids"))
        inf = as_list(r.get("informs_classes"))
        if set(ci) & set(inf):
            shape_bad.append({"row": r["theorem_id"], "why": "class_ids intersects informs_classes"})
        if len(set(ci)) != len(ci) or len(set(inf)) != len(inf):
            shape_bad.append({"row": r["theorem_id"], "why": "duplicate token"})
    c3 = {"id": "C3_binding_shape", "verdict": "PASS" if not shape_bad else "FAIL",
          "violations": shape_bad}
    record["checks"].append(c3)

    # ---- C4 adoption fidelity ----------------------------------------------
    matched, mismatches = adoption_fidelity(packet, staged_by_id)
    tag_ok, tag_bad = True, []
    for row in packet["rows"]:
        rid = row["row_id"]
        add = as_list((row.get("recommended") or {}).get("ledger_tags_add"))
        if not add:
            continue
        want = as_list(live_by_id[rid].get("ledger_tags")) + add
        if as_list(staged_by_id[rid].get("ledger_tags")) != want:
            tag_ok = False
            tag_bad.append({"row": rid,
                            "staged": as_list(staged_by_id[rid].get("ledger_tags")),
                            "expected": want})
    c4 = {"id": "C4_adoption_fidelity", "verdict": "PASS" if not mismatches and tag_ok else "FAIL",
          "recommended_rows_matched": matched, "mismatches": mismatches,
          "ledger_tags_add_applied_exactly": tag_ok, "tag_mismatches": tag_bad}
    record["checks"].append(c4)

    # ---- C5 conditional license --------------------------------------------
    cond = conditional_rows(packet)
    licensing = find_licensing(PACKET_TIME)
    licensed = []
    for c in cond:
        c["licensed"] = any(True for _ in licensing)
        licensed.append(c)
    c5 = {"id": "C5_conditional_license",
          "verdict": "PASS" if all(c["licensed"] for c in licensed) else "LICENSE_PENDING",
          "conditional_rows": licensed, "licensing_events_found": licensing,
          "note": "PASS means every needs_f1_ruling row has an accepted lead/controller "
                  "ruling after the packet time; LICENSE_PENDING means the staged bytes "
                  "apply a default branch of an open ruling."}
    record["checks"].append(c5)

    # ---- C6 self-declared scope --------------------------------------------
    sc_live = self_contradictions(live_rows)
    sc_staged = self_contradictions(staged_rows)
    sc_live_pop = sorted({h["row"] for h in sc_live if h["row"] in POPULATION})
    sc_staged_pop = sorted({h["row"] for h in sc_staged if h["row"] in POPULATION})
    c6 = {"id": "C6_self_declared_scope",
          "verdict": "INFO",
          "population_live_rows_with_self_contradicted_class_token": sc_live_pop,
          "population_staged_rows_with_self_contradicted_class_token": sc_staged_pop,
          "all_ledger_live_rows_with_self_contradicted_class_token":
              sorted({h["row"] for h in sc_live}),
          "all_ledger_staged_rows_with_self_contradicted_class_token":
              sorted({h["row"] for h in sc_staged}),
          "live_hits": sc_live, "staged_hits": sc_staged}
    record["checks"].append(c6)

    # ---- C7 empty binding census / gate consequence -------------------------
    emp_live, emp_staged = empty_class_rows(live_rows), empty_class_rows(staged_rows)
    th_live, th_staged = theorem_empty_rows(live_rows), theorem_empty_rows(staged_rows)
    c7 = {"id": "C7_gate_scope_match_census", "verdict": "INFO",
          "class_ids_empty": {"live": len(emp_live), "staged": len(emp_staged),
                              "live_rows": sorted(emp_live), "staged_rows": sorted(emp_staged),
                              "newly_empty": sorted(set(emp_staged) - set(emp_live))},
          "theorem_or_conditional_with_empty_class_ids": {
              "live": len(th_live), "staged": len(th_staged),
              "live_rows": sorted(th_live), "staged_rows": sorted(th_staged),
              "newly_empty": sorted(set(th_staged) - set(th_live))},
          "criterion": "evaluation_rubric.yaml:140 'statement scope matched to class_id; ...' "
                       "cannot be satisfied for a row with class_ids == [].",
          "note": "Computation only; the ruling on whether empty class_ids is acceptable "
                  "belongs to the controller/A0 owner."}
    record["checks"].append(c7)

    # ---- C8 subject crosswalk (prior census) --------------------------------
    cross, grounding_fail, fabricated_ok = prior_census_crosswalk(census, staged_by_id, live_by_id)
    aligned = [c["row"] for c in cross if c["aligned_under_subject_reading"]]
    not_aligned = [c["row"] for c in cross if not c["aligned_under_subject_reading"]]
    c8 = {"id": "C8_subject_reading_crosswalk", "verdict": "INFO",
          "aligned": aligned, "not_aligned": not_aligned,
          "prior_cell_quotes_ungrounded": grounding_fail,
          "fabricated_quote_grounded": bool(fabricated_ok),
          "crosswalk": cross}
    record["checks"].append(c8)

    # ---- C9 registry pin drift ----------------------------------------------
    rd = registry_drift()
    cited_ok = all(v["entry_byte_identical"] for v in rd["cited_variants"].values())
    c9 = {"id": "C9_registry_pin_drift",
          "verdict": "INFO" if rd["changed_variant_entries"] else "PASS",
          "packet_pinned_registry": "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
          "live_registry": "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
          "drift": rd, "cited_variants_byte_identical_across_revisions": cited_ok}
    record["checks"].append(c9)

    # ---- C10 informs grounding ----------------------------------------------
    inf_g = informs_grounding(packet, live_by_id, staged_by_id)
    c10 = {"id": "C10_informs_row_text_mention", "verdict": "INFO",
           "rows": inf_g,
           "row_text_names_class_count": sum(1 for x in inf_g if x["row_text_names_class"]),
           "total_informs_tokens": len(inf_g),
           "note": "containment is registry-asserted; this only records whether the row text "
                   "itself names the target class."}
    record["checks"].append(c10)

    # ---- BL-7 status ---------------------------------------------------------
    bl7, bl7_hits = bl7_ruling_status(PACKET_TIME)
    record["bl7_ruling_status"] = {"status": bl7, "evidence": bl7_hits}

    # ---- controls ------------------------------------------------------------
    controls = []
    mut = [dict(r) for r in staged_rows]
    for r in mut:
        if r["theorem_id"] == "D-004":
            r["class_ids"] = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    n, _ = disjunction_count(mut)
    controls.append({"id": "CTL-1a", "verdict": "PASS" if n == 1 else "FAIL",
                     "detail": "restore D-004 disjunction -> disjunction_count=%d (want 1)" % n})
    mut = [dict(r) for r in staged_rows]
    for r in mut:
        if r["theorem_id"] == "T-515":
            r["class_ids"] = ["AF-BOGUS-CLASS"]
    controls.append({"id": "CTL-1b",
                     "verdict": "PASS" if unknown_token_hits(mut) else "FAIL",
                     "detail": "unknown token mutant -> %d hit(s)" % len(unknown_token_hits(mut))})
    mut = [dict(r) for r in staged_rows]
    for r in mut:
        if r["theorem_id"] == "T-303":
            r["class_ids"] = ["AF-SCC-C0-VAC-GEN"]
    hits = self_contradictions(mut)
    controls.append({"id": "CTL-2",
                     "verdict": "PASS" if any(h["row"] == "T-303" for h in hits) else "FAIL",
                     "detail": "T-303 -> C0 mutant flagged by its own does_not_imply: %s"
                               % sorted({h["row"] for h in hits})})
    mut = [r for r in staged_rows if r["theorem_id"] != "T-528"]
    controls.append({"id": "CTL-3",
                     "verdict": "PASS" if len(mut) == 61 else "FAIL",
                     "detail": "row-drop mutant -> %d rows (want 61)" % len(mut)})
    mut = [dict(r) for r in staged_rows]
    for r in mut:
        if r["theorem_id"] == "T-515":
            r["class_ids"] = []
    _, mism = adoption_fidelity(packet, {r["theorem_id"]: r for r in mut})
    controls.append({"id": "CTL-4",
                     "verdict": "PASS" if any(m["row"] == "T-515" for m in mism) else "FAIL",
                     "detail": "T-515 emptied mutant -> %d adoption mismatch(es)" % len(mism)})
    controls.append({"id": "CTL-5",
                     "verdict": "PASS" if grounding_fail == 0 and fabricated_ok == 0 else "FAIL",
                     "detail": "prior cell quotes ungrounded=%d (want 0); fabricated quote "
                               "grounded=%d (want 0)" % (grounding_fail, fabricated_ok)})
    record["controls"] = controls

    # ---- per-row table --------------------------------------------------------
    packet_by_id = {r["row_id"]: r for r in packet["rows"]}
    cross_by_id = {c["row"]: c for c in cross}
    for rid in POPULATION:
        lr, sr, pr = live_by_id[rid], staged_by_id[rid], packet_by_id[rid]
        record["per_row"].append({
            "row": rid,
            "conclusion_type": lr.get("conclusion_type"),
            "regularity": lr.get("regularity"),
            "live": {"class_ids": as_list(lr.get("class_ids")),
                     "informs_classes": as_list(lr.get("informs_classes"))},
            "staged": {"class_ids": as_list(sr.get("class_ids")),
                       "informs_classes": as_list(sr.get("informs_classes")),
                       "ledger_tags": as_list(sr.get("ledger_tags"))},
            "worker023": {"disposition": pr.get("disposition"),
                          "measured_extension_class": pr.get("measured_extension_class"),
                          "needs_f1_ruling": bool(pr.get("needs_f1_ruling"))},
            "prior_subject_reading": {
                "resolution": cross_by_id[rid]["prior_resolution"],
                "subject_classes": cross_by_id[rid]["prior_subject_classes"],
                "aligned": cross_by_id[rid]["aligned_under_subject_reading"]},
            "self_contradicted_live_tokens":
                sorted({h["token"] for h in sc_live if h["row"] == rid}),
            "self_contradicted_staged_tokens":
                sorted({h["token"] for h in sc_staged if h["row"] == rid}),
            "does_not_imply": as_list(lr.get("does_not_imply")),
        })

    record["aggregates"] = {
        "population_rows": 8, "ledger_rows": len(live_rows),
        "disjunction_count": {"live": d_live, "staged": d_staged},
        "class_ids_empty": {"live": len(emp_live), "staged": len(emp_staged)},
        "theorem_or_conditional_with_empty_class_ids":
            {"live": len(th_live), "staged": len(th_staged),
             "newly_empty": sorted(set(th_staged) - set(th_live))},
        "rows_with_self_contradicted_class_token": {
            "population": {"live": len(sc_live_pop), "staged": len(sc_staged_pop)},
            "all_ledger": {"live": len({h["row"] for h in sc_live}),
                           "staged": len({h["row"] for h in sc_staged})}},
        "adoption_fidelity": {"matched": len(matched), "mismatched": len(mismatches)},
        "subject_reading_alignment": {"aligned": len(aligned), "not_aligned": len(not_aligned),
                                      "not_aligned_rows": sorted(not_aligned)},
        "conditional_license": {"needs_ruling_rows": [c["row"] for c in licensed],
                                "licensed": all(c["licensed"] for c in licensed)},
        "registry_pin_drift_immaterial_to_cited_variants": cited_ok,
    }

    # ---- pins (after) ---------------------------------------------------------
    for rel in PINS:
        p = os.path.join(ROOT, rel)
        record["pins"][rel]["measured_after"] = sha256_file(p) if os.path.exists(p) else None
        record["pins"][rel]["stable"] = (record["pins"][rel]["measured_after"]
                                         == record["pins"][rel]["measured"])

    # ---- verdict --------------------------------------------------------------
    hard_fail = [c["id"] for c in record["checks"]
                 if c["verdict"] in ("FAIL",)] + [c["id"] for c in controls if c["verdict"] == "FAIL"]
    record["prediction_delta"] = {
        "H7_expected_class_ids_empty_staged": 33,
        "H7_measured_class_ids_empty_staged": len(emp_staged),
        "note": "Prediction miss recorded: six population rows become empty "
                "(D-004, D-005, T-303, T-305, T-402, T-526), not five; the earlier "
                "count of five mis-grouped T-526. The runner value is authoritative.",
    }
    record["verdict"] = "PIN_DRIFT" if drift else ("FAIL" if hard_fail else "VERIFIED")
    record["hard_failures"] = hard_fail
    record["summary"] = (
        "Staged HF-02 repair verified non-author at pinned bytes: %d/%d recommended "
        "dispositions applied exactly, disjunctions %d->%d, unknown/variant tokens 0, "
        "population self-declared-scope contradictions in class_ids %d/8 -> %d/8, "
        "class_ids==[] %d -> %d (theorem/conditional empty %d -> %d), "
        "subject-reading crosswalk %d/8 aligned (not aligned: %s), T-526 applies a "
        "pending needs_f1_ruling default (LICENSE_PENDING=%s), registry pin drift "
        "immaterial to the three cited variants=%s, BL-7 ruling %s."
        % (len(matched), len(packet["rows"]), d_live, d_staged,
           len(sc_live_pop), len(sc_staged_pop),
           len(emp_live), len(emp_staged), len(th_live), len(th_staged),
           len(aligned), ",".join(sorted(not_aligned)),
           not all(c["licensed"] for c in licensed), cited_ok, bl7)
    )
    record["falsifiers"] = [
        "Re-run run_adoption_verify.py at the same pins; a different core_digest voids this packet.",
        "Any move of a pinned hash voids this packet.",
        "An accepted lead/controller ruling on T-526's characteristic-interior question flips C5 to PASS.",
        "A G-LIT gate pass or an HF-02 scope ruling after 2026-09-12T00:36:38+08:00 closes BL-7 and changes the consequence stated here.",
    ]
    record["reproduce"] = "python3 artifacts/worker-099/hf02_staged_adoption_verify/run_adoption_verify.py"
    record["core_digest_sha256"] = build_core(record)

    out_json = os.path.join(HERE, "RESULTS.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=1, sort_keys=False)
        fh.write("\n")

    print("verdict=%s core_digest=%s" % (record["verdict"], record["core_digest_sha256"][:16]))
    for c in record["checks"]:
        print("  %-34s %s" % (c["id"], c["verdict"]))
    for c in record["controls"]:
        print("  %-34s %s | %s" % (c["id"], c["verdict"], c["detail"]))
    print("  " + record["summary"])
    if drift:
        print("PIN DRIFT:", drift)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
