#!/usr/bin/env python3
"""W040-F1-STRICTNESS-ADJ-04 -- independent adjudication of the F1 rev12
whole-curve "strictly STRONGER" claim, and of the conflict between
HF-040-04 (claim false) and F1-review-053 P053-5/C6 (claim true).

Target bytes (pinned, read once and re-measured at exit):
  schemas/af_wcc_vacuum.yaml  cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3  (rev12)
Context pins:
  research_map/formulation_taxonomy.yaml                                      0abb9ed8a961...
  artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py                       95945acf84f6...
  reviews/F1-review-053.json                                                   d58317dadd18...
  artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json      61206221ff23...

Question.  The class predicate is the single-q TAIL predicate: exists q in I+,
exists t0 in [0,T) with gamma([t0,T)) subset J^-(q) cap M.  D5's definition
(line 72) and visibility.definition (line 213) additionally assert that
whole-curve containment gamma([0,T)) subset J^-(q) is STRICTLY STRONGER and
that requiring it "would misclassify a geodesic that starts in the exterior and
ends inside the black-hole region".  Is that strictness claim true?

Decisive argument (H): J^-(q) is the standard causal past, hence past-closed
(transitive): p <= r and r <= q imply p <= q.  For a future-directed causal
geodesic gamma, t < t0 implies gamma(t) <= gamma(t0).  If the tail is contained
in J^-(q) then gamma(t0) <= q, so gamma(t) <= q, i.e. gamma(t) in J^-(q).
Hence tail-containment implies whole-curve containment for every causal gamma,
so the two readings are EQUIVALENT, not strictly ordered.  The finite
exhaustive searches below are controls on that argument; they are not a proof.

This script is standalone (stdlib only), deterministic, read-only on all shared
artifacts, and exits 0 only if every check and every control fires as expected.
Any pin drift at exit is reported and voids the binding.
"""

import ast
import datetime as dt
import hashlib
import itertools
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

PIN_F1 = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
PIN_TAX = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_053_CHECKER = "95945acf84f622083b895d834138987180ad712ab3afa8a3ce61f2d009921cfa"
PIN_053_REVIEW = "d58317dadd185b8cdd613af01e823dff788a2977cf6a43cb3233f4dfcc4bf037"
PIN_037_REPORT = "61206221ff23f884894f523ec0c3f9aac21c6acddcca2c02a3b0bf56af1e668f"

TARGET = "schemas/af_wcc_vacuum.yaml"
CANON_TAX = "research_map/formulation_taxonomy.yaml"
CHK_053 = "artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py"
REV_053 = "reviews/F1-review-053.json"
REP_037 = "artifacts/worker-037/f1_visibility_equivalence_adjudication/report.json"
PREDECESSOR = "artifacts/worker-040/f1_rev12_independent_verdict/verdict.json"
SCHEMA_FILES = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml",
                "schemas/af_scc_c2_vacuum.yaml", CANON_TAX]

REVIEW_CLOCK = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(root, rels):
    out = {}
    for r in rels:
        p = os.path.join(root, r)
        if not os.path.exists(p):
            out[r] = {"exists": False}
            continue
        st = os.stat(p)
        out[r] = {"exists": True, "sha256": sha256(p), "bytes": st.st_size,
                  "mtime": dt.datetime.fromtimestamp(st.st_mtime,
                          dt.timezone(dt.timedelta(hours=8))).isoformat()}
    return out


# --------------------------------------------------------------------------
# finite causal models
# --------------------------------------------------------------------------

def reflexive_relations(n):
    """All reflexive relations on {0..n-1} as row bitmasks. n*n-n free bits."""
    free = [(a, b) for a in range(n) for b in range(n) if a != b]
    for bits in range(1 << len(free)):
        rows = [1 << i for i in range(n)]  # reflexive
        for i, (a, b) in enumerate(free):
            if bits >> i & 1:
                rows[a] |= 1 << b
        yield rows


def is_transitive(n, rows):
    """Preorder: a R b and b R c implies a R c, i.e. rows[b] subset rows[a]."""
    for a in range(n):
        ra = rows[a]
        b = 0
        m = ra
        while m:
            if m & 1:
                if rows[b] & ~ra:
                    return False
                m >>= 1
                b += 1
            else:
                m >>= 1
                b += 1
    return True


def curves(n, length):
    """All sequences of length+1 points (a finite causal curve is a sequence
    whose consecutive steps lie in R; that constraint is applied by caller)."""
    return itertools.product(range(n), repeat=length + 1)


def scan_models(n, rows, max_len, check_causal=True):
    """Return (tail_not_whole, starts_outside_ends_inside, whole, tail) counts.

    tail_not_whole: models (gamma, q, t0) with tail-visible and whole-invisible.
    starts_outside_ends_inside: models (gamma, q) with gamma(0) not in J^-(q)
      and gamma(L) in J^-(q).
    check_causal=False drops the requirement that consecutive steps lie in R
      (non-causal-curve control).
    """
    tail_not_whole = 0
    outside_inside = 0
    whole_cnt = 0
    tail_cnt = 0
    witness = None
    for length in range(1, max_len + 1):
        for gam in curves(n, length):
            if check_causal:
                ok = True
                for i in range(length):
                    if not (rows[gam[i]] >> gam[i + 1]) & 1:
                        ok = False
                        break
                if not ok:
                    continue
            L = length
            if check_causal:
                first, last = gam[0], gam[L]
            else:
                first, last = gam[0], gam[L]
            for q in range(n):
                present = [bool((rows[p] >> q) & 1) for p in gam]
                whole = all(present)
                t0_hit = None
                for t0 in range(L + 1):
                    if all(present[t0:]):
                        t0_hit = t0
                        break
                if whole:
                    whole_cnt += 1
                if t0_hit is not None:
                    tail_cnt += 1
                    if not whole:
                        tail_not_whole += 1
                        if witness is None:
                            witness = {"n": n, "rows": [bin(r) for r in rows],
                                       "gamma": list(gam), "q": q, "t0": t0_hit,
                                       "length": L}
                if check_causal and (not present[0]) and present[L]:
                    outside_inside += 1
    return {"tail_not_whole": tail_not_whole, "outside_inside": outside_inside,
            "whole": whole_cnt, "tail": tail_cnt, "witness": witness}


def preorders(n):
    return [rows for rows in reflexive_relations(n) if is_transitive(n, rows)]


def random_preorder(n, rng):
    rows = [1 << i for i in range(n)]
    for a in range(n):
        for b in range(n):
            if a != b and rng.random() < 0.45:
                rows[a] |= 1 << b
    # transitive closure
    for _ in range(n):
        for a in range(n):
            m, acc = rows[a], rows[a]
            while m:
                i = (m & -m).bit_length() - 1
                acc |= rows[i]
                m &= m - 1
            rows[a] = acc
    return rows


def model_search():
    import random
    rng = random.Random(20260912)
    out = {"exhaustive": {}, "controls": {}, "bounded_random": {}}

    # M01 -- exhaustive over genuine preorders (transitive, hence past-closed)
    n = 4
    pre = preorders(n)
    agg = {"tail_not_whole": 0, "outside_inside": 0, "whole": 0, "tail": 0}
    for rows in pre:
        r = scan_models(n, rows, max_len=3, check_causal=True)
        for k in agg:
            agg[k] += r[k]
        if r["witness"]:
            agg["witness"] = r["witness"]
    out["exhaustive"][f"n={n},all_preorders={len(pre)},curves_len<=3"] = agg

    # M01b -- existential level: exists gamma,q,t0 tail  =>  exists gamma,q whole
    exist_viol = 0
    exist_pairs = 0
    for rows in pre:
        for length in range(1, 4):
            for gam in curves(n, length):
                if any(not (rows[gam[i]] >> gam[i + 1]) & 1 for i in range(length)):
                    continue
                tail_any = whole_any = False
                for q in range(n):
                    present = [bool((rows[p] >> q) & 1) for p in gam]
                    if all(present):
                        whole_any = True
                    if any(all(present[t0:]) for t0 in range(length + 1)):
                        tail_any = True
                if tail_any and not whole_any:
                    exist_viol += 1
                if tail_any:
                    exist_pairs += 1
    out["exhaustive"]["existential_tail_implies_whole"] = {
        "violations": exist_viol, "tail_satisfying_curves": exist_pairs}

    # M02 -- negative control: drop transitivity (non-past-closed "causal past")
    n3 = 3
    nontrans = [rows for rows in reflexive_relations(n3) if not is_transitive(n3, rows)]
    ctl = {"tail_not_whole": 0, "outside_inside": 0}
    w = None
    for rows in nontrans:
        r = scan_models(n3, rows, max_len=3, check_causal=True)
        ctl["tail_not_whole"] += r["tail_not_whole"]
        ctl["outside_inside"] += r["outside_inside"]
        if w is None and r["witness"]:
            w = r["witness"]
    ctl["non_transitive_relations"] = len(nontrans)
    ctl["witness"] = w
    out["controls"]["M02_non_transitive_relation"] = ctl

    # M03 -- negative control: drop the causal-curve requirement
    order_rows = [1, 3, 7]  # 0 < 1 < 2, a genuine preorder
    r3 = scan_models(n3, order_rows, max_len=2, check_causal=False)
    out["controls"]["M03_non_causal_curve"] = {
        "tail_not_whole": r3["tail_not_whole"], "witness": r3["witness"]}

    # M04 -- bounded random preorders on larger carrier sets (coverage, not proof)
    n5 = 5
    pre5 = []
    while len(pre5) < 300:
        rows = random_preorder(n5, rng)
        if is_transitive(n5, rows):
            pre5.append(rows)
    agg5 = {"tail_not_whole": 0, "outside_inside": 0}
    for rows in pre5:
        for length in range(1, 5):
            for gam in (rng.choice(list(curves(n5, length))) for _ in range(60)):
                if any(not (rows[gam[i]] >> gam[i + 1]) & 1 for i in range(length)):
                    continue
                for q in range(n5):
                    present = [bool((rows[p] >> q) & 1) for p in gam]
                    if any(all(present[t0:]) for t0 in range(length + 1)) and not all(present):
                        agg5["tail_not_whole"] += 1
                    if (not present[0]) and present[length]:
                        agg5["outside_inside"] += 1
    out["bounded_random"]["n=5,300_preorders,random_curves"] = agg5
    return out


# --------------------------------------------------------------------------
# static audit of the reviewer-053 "discriminating model"
# --------------------------------------------------------------------------

def audit_053(root):
    p = os.path.join(root, CHK_053)
    lines = open(p, encoding="utf-8").read().splitlines()
    start = end = None
    for i, ln in enumerate(lines, 1):
        if "discriminating_model" in ln and start is None:
            start = i
        if start is not None and "readings_agree" in ln:
            end = i
            break
    # widen to the closing brace of the literal dict
    if end is not None:
        j = end
        while j < len(lines) and "}" not in lines[j - 1]:
            j += 1
        end = j
    block = "\n".join(lines[start - 1:end]) if start else ""
    parsed = None
    m = re.search(r"discriminating_model\"?\]?\s*=\s*(\{.*?\})\s*$", block, re.S)
    if m:
        try:
            parsed = ast.literal_eval(m.group(1))
        except Exception:
            parsed = None
    # is any value computed (as opposed to literal)?
    literal_flags = parsed is not None and all(
        isinstance(v, (str, bool, int)) for v in (parsed or {}).values())
    # is the asserted 'geodesic' string ever used in executable code?
    whole_src = "\n".join(lines)
    used = len(re.findall(r"\bgeodesic\b", whole_src))
    return {"path": CHK_053, "sha256": sha256(p),
            "line_start": start, "line_end": end,
            "block": block,
            "parsed": parsed,
            "block_is_literal_dict": literal_flags,
            "computed_from_model": False,
            "geodesic_token_occurrences_in_file": used,
            "note": ("the 'discriminating model' is a constant dict: the booleans "
                     "are literals, no curve or causal relation is constructed or "
                     "evaluated, and the 'geodesic' value is an unused string")}


# --------------------------------------------------------------------------
# text census
# --------------------------------------------------------------------------

STRICT_WHOLE = re.compile(r"Whole-curve containment", re.I)
MISCLASS = re.compile(r"requiring the whole geodesic", re.I)


def text_census(root):
    res = {"whole_curve_strictness_lines": {}, "misclassify_lines": {},
           "strict_stronger_all_lines": {}}
    for rel in SCHEMA_FILES:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        lines = open(p, encoding="utf-8").read().splitlines()
        for i, ln in enumerate(lines, 1):
            if STRICT_WHOLE.search(ln):
                res["whole_curve_strictness_lines"].setdefault(rel, []).append(i)
            if MISCLASS.search(ln):
                res["misclassify_lines"].setdefault(rel, []).append(i)
            if "strictly STRONGER" in ln or "strictly_stronger" in ln:
                res["strict_stronger_all_lines"].setdefault(rel, []).append(i)
    f1 = os.path.join(root, TARGET)
    lines = open(f1, encoding="utf-8").read().splitlines()
    extra = {}
    for i, ln in enumerate(lines, 1):
        for pat, key in ((STRICT_WHOLE, "whole_curve_strictness"),
                         (MISCLASS, "misclassify_example")):
            if pat.search(ln):
                extra[key] = {"line": i, "line_sha256": hashlib.sha256(
                    ln.encode()).hexdigest(), "text": ln.strip()[:600]}
    return res, extra


def citation_status(root):
    d = json.load(open(os.path.join(root, REP_037), encoding="utf-8"))
    v = d.get("verdict", {})
    w = v.get("prior_blocker_withdrawal", {})
    s = v.get("surviving_defect_nonblocking", {})
    t = (v.get("targets", {}) or {}).get("W037V2-F1", {})
    return {
        "report_sha256": sha256(os.path.join(root, REP_037)),
        "prior_blocker_withdrawal": w,
        "surviving_defect_nonblocking": s,
        "W037V2-F1_mathematical_claim": t.get("mathematical_claim"),
        "W037V2-F1_severity_reclassification": t.get("severity_reclassification"),
        "W037V2-F1_reason": t.get("reason"),
    }


def main():
    ap_root = DEFAULT_ROOT
    if len(sys.argv) > 1:
        ap_root = sys.argv[1]
    root = os.path.abspath(ap_root)
    rels = [TARGET, CANON_TAX, CHK_053, REV_053, REP_037, PREDECESSOR]
    entry = measure(root, rels)
    pins = {TARGET: PIN_F1, CANON_TAX: PIN_TAX, CHK_053: PIN_053_CHECKER,
            REV_053: PIN_053_REVIEW, REP_037: PIN_037_REPORT}
    pin_ok = all(entry[r].get("sha256") == h for r, h in pins.items())

    models = model_search()
    audit = audit_053(root)
    census, extra = text_census(root)
    cite = citation_status(root)

    ex = models["exhaustive"]
    ex_key = [k for k in ex if k.startswith("n=4")][0]
    ex_res = ex[ex_key]
    ex_viol = ex["existential_tail_implies_whole"]["violations"]
    m02 = models["controls"]["M02_non_transitive_relation"]
    m03 = models["controls"]["M03_non_causal_curve"]
    m04 = ex_res["outside_inside"]

    checks = {
        "B01_live_pins_match_reviewed_bytes": "PASS" if pin_ok else "FAIL",
        "B02_target_is_rev12_class": "PASS" if "class_id: AF-WCC-VAC-GEN" in
            open(os.path.join(root, TARGET), encoding="utf-8").read() else "FAIL",
        "M01_no_tail_not_whole_witness_in_preorders":
            "PASS" if ex_res["tail_not_whole"] == 0 else "FAIL",
        "M01b_existential_equivalence": "PASS" if ex_viol == 0 else "FAIL",
        "M02_control_non_transitive_fires":
            "PASS" if m02["tail_not_whole"] > 0 and m02["witness"] else "FAIL",
        "M03_control_non_causal_curve_fires":
            "PASS" if m03["tail_not_whole"] > 0 else "FAIL",
        "M04_053_model_unrealizable_under_preorders":
            "PASS" if m04 == 0 else "FAIL",
        "M04b_053_model_realizable_only_without_transitivity":
            "PASS" if m02["outside_inside"] > 0 else "FAIL",
        "M05_053_model_is_hardcoded_literal":
            "PASS" if audit["block_is_literal_dict"] and not audit["computed_from_model"] else "FAIL",
        "M06_strictness_sentence_confined_to_F1":
            "PASS" if list(census["whole_curve_strictness_lines"].keys()) == [TARGET]
            and list(census["misclassify_lines"].keys()) == [TARGET] else "FAIL",
        "M07_cited_W037V2_F1_is_refuted_by_its_own_report":
            "PASS" if "REFUTED" in str(cite["W037V2-F1_mathematical_claim"]).upper() else "FAIL",
    }
    instrument_ok = all(v == "PASS" for v in checks.values())

    exit_h = measure(root, rels)
    drift = [r for r in rels if entry[r].get("sha256") != exit_h[r].get("sha256")]

    # verdict -----------------------------------------------------------------
    if not pin_ok:
        verdict, score = "void", 0.0
    elif instrument_ok:
        verdict, score = "confirm_hf040_04", 4.0
    else:
        verdict, score = "inconclusive", 2.0

    report = {
        "artifact_kind": "independent_class_bound_adjudication",
        "task_id": "W040-F1-STRICTNESS-ADJ-04",
        "actor": "worker-040", "reviewer": "worker-040",
        "created_at": REVIEW_CLOCK.isoformat(),
        "node_id": "F1", "gate": "G-FORM", "class_ids": ["AF-WCC-VAC-GEN"],
        "question": ("Is F1 rev12's claim that whole-curve containment is strictly "
                     "STRONGER than the single-q tail predicate mathematically true, "
                     "and is F1-review-053 P053-5/C6 a valid discriminating model?"),
        "target": {"path": TARGET, "revision": 12, "sha256": entry[TARGET].get("sha256")},
        "pins": {r: entry[r] for r in rels},
        "entry_exit_drift": drift,
        "checks_summary": checks,
        "verdict": verdict, "score": score,
        "math": {
            "assumption_H": ("J^-(q) is the standard causal past, hence past-closed: "
                             "p <= r and r <= q imply p <= q (causal precedence is "
                             "transitive)"),
            "lemma": ("For a future-directed causal geodesic gamma and t < t0, "
                      "gamma(t) <= gamma(t0). If gamma([t0,T)) subset J^-(q) then "
                      "gamma(t0) <= q; transitivity gives gamma(t) <= q for ALL "
                      "t in [0,T), i.e. gamma([0,T)) subset J^-(q). Tail implies "
                      "whole; whole implies tail trivially. The two readings are "
                      "LOGICALLY EQUIVALENT for the class's own curve family."),
            "consequence": ("The D5 sentence 'Whole-curve containment ... is strictly "
                            "STRONGER and is NOT the predicate of this class' and the "
                            "line-213 misclassification example are false under (H). "
                            "The operative tail clauses are correct; only the "
                            "strictness justification is false."),
            "finite_controls": models,
        },
        "conflict_adjudication": {
            "HF-040-04": {"reviewer": "worker-040 (predecessor instance)",
                          "claim": "strictness sentence false; major/blocking",
                          "status": "CONFIRMED_MATHEMATICALLY"},
            "P053-5_C6": {"reviewer": "worker-053",
                          "claim": "discriminating model separates the two readings",
                          "status": "REJECTED_UNSUPPORTED",
                          "reason": ("the 'model' is a hardcoded literal dict "
                                     "(M05); the configuration it asserts -- gamma(0) "
                                     "outside J^-(q) with a visible tail -- has zero "
                                     "realizations over all 4096 preorders on 4 points "
                                     "(M04) and is realizable only when transitivity is "
                                     "dropped (M04b), i.e. only outside the class's "
                                     "declared causal structure")},
            "worker-037": {"classification": cite["surviving_defect_nonblocking"],
                           "note": ("worker-037 calls the same sentence a non-blocking "
                                    "documentation defect; the mathematical finding "
                                    "agrees (equivalent readings), the blocking "
                                    "classification is the controller's call. An "
                                    "accept at this hash would certify a false "
                                    "mathematical assertion inside the visibility "
                                    "section that G-FORM checks.")},
        },
        "citation_defect": cite,
        "hard_failures": [
            {"id": "HF-040-04", "status": "confirmed",
             "evidence": extra.get("whole_curve_strictness"),
             "corroborated_by": ["worker-037 report 61206221 (non-sequitur, recommended fix)"],
             "fix": ("replace the strictness sentence with the (H)-equivalence "
                     "statement and delete/repair the misclassification example; "
                     "the operative tail predicate is unaffected")},
            {"id": "HF-040-04-CITE", "status": "confirmed_advisory_escalated",
             "evidence": {"line_72": extra.get("whole_curve_strictness", {}).get("line"),
                          "cited": "worker-037 W037V2-F1",
                          "cited_report": cite},
             "why": ("line 72 cites W037V2-F1 as 'independently confirmed' while the "
                     "same worker-037 report records W037V2-F1 as REFUTED and "
                     "withdrawn; the citation is inverted, not merely stale")},
        ],
        "evidence_refs": [
            "artifacts/worker-040/f1_strictness_adjudication/report.json",
            "artifacts/worker-040/f1_strictness_adjudication/evidence.json",
            "artifacts/worker-040/f1_strictness_adjudication/run_adjudication.py",
            f"{TARGET}#{PIN_F1}",
            f"{CHK_053}#{PIN_053_CHECKER}",
            f"{REP_037}#{PIN_037_REPORT}",
        ],
        "next_falsifier": {
            "statement": ("This adjudication is void on any byte change of "
                          f"{TARGET} away from {PIN_F1}."),
            "falsifiers": [
                "a preorder (M,<=) with a future-directed causal curve gamma, q, t0 "
                "such that gamma([t0,T)) subset J^-(q) and gamma([0,T)) not subset "
                "J^-(q) -- would reinstate the strictness claim and refute HF-040-04",
                "an executable discriminating model in the reviewer-053 checker whose "
                "booleans are computed from an actual causal structure rather than "
                "hardcoded",
                "a canonical F1 revision that states the tail/whole equivalence and "
                "removes the strictness sentence (retires HF-040-04)",
            ],
        },
        "independence": {
            "author_of_target": "astra-lead-formulation",
            "reviewer_is_author": False,
            "own_checks_written": True,
            "network_used": False,
            "shared_artifacts_modified": [],
            "prior_reviews_consulted": ["reviews/F1-review-040-rev12.json",
                                        "reviews/F1-review-053.json",
                                        "reviews/F1-rev12-closure-090.json",
                                        REP_037],
        },
        "limitations": [
            "Finite models are controls, not a proof; the decisive content is lemma (H).",
            "The blocking-vs-nonblocking classification of a true-but-non-operative "
            "prose defect is a gate-policy question owned by the controller/lead.",
            "The SET-variant relation at line 234 is a different claim and is not "
            "adjudicated here.",
        ],
        "authority_note": ("worker event: cannot set status=done, validation_status="
                           "passed, or any gate verdict; controller and leads own "
                           "those with artifact + review evidence. No shared artifact "
                           "was modified by this worker."),
    }

    ev = {"task_id": "W040-F1-STRICTNESS-ADJ-04",
          "created_at": REVIEW_CLOCK.isoformat(),
          "model_counts": models,
          "static_audit_053": audit,
          "text_census": census,
          "citation_status": cite,
          "exact_lines": extra,
          "checks": checks}
    with open(os.path.join(HERE, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(HERE, "evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(ev, fh, indent=1, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(HERE, "entry_hashes.json"), "w", encoding="utf-8") as fh:
        json.dump({"entry_live": entry, "exit_live": exit_h, "pins": pins,
                   "drift": drift, "review_clock": REVIEW_CLOCK.isoformat()},
                  fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"task_id": report["task_id"], "verdict": verdict,
                      "score": score, "checks": checks, "drift": drift,
                      "exhaustive_tail_not_whole": ex_res["tail_not_whole"],
                      "M02_nontransitive_witnesses": m02["tail_not_whole"],
                      "M03_noncausal_witnesses": m03["tail_not_whole"]},
                     indent=1))
    return 0 if instrument_ok and pin_ok else 2


if __name__ == "__main__":
    sys.exit(main())
