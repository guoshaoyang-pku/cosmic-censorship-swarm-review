#!/usr/bin/env python3
"""Acceptance checker for FORM-GEN-05 (N1-N5). Reads genericity_matrix.json + rule_spec.json.

Exit 0 iff N1-N5 all PASS. Prints one line per criterion. This is a structural checker: it
does not and cannot decide physical truth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATRIX = HERE / "genericity_matrix.json"
RULE_SPEC = HERE.parent.parent / "formulation" / "rule_spec.json"

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, bool(ok), detail))


def main() -> int:
    m = json.loads(MATRIX.read_text())
    spec = json.loads(RULE_SPEC.read_text())
    vocab = [k for k in spec["vocabularies"]["genericity_kind"] if k != "none"]
    classes = [c for c in m["class_scope"]]

    # N1 -- four notions, each with definition / ambient / topology-or-measure / quantifier form
    notions = m.get("genericity_notions", {})
    n1_missing = [k for k in ["definition", "ambient_space_requirement", "topology_or_measure_requirement", "quantifier_form"]
                  if not notions.get("residual_comeager", {}).get(k)]
    n1 = set(notions) == set(vocab) and not n1_missing
    check("N1_notion_vocabulary_and_fields", n1,
          f"vocab={sorted(vocab)} present={sorted(notions)} missing_fields={n1_missing}")
    for k, v in notions.items():
        check(f"N1.{k}.fields", all(v.get(f) for f in ["definition", "ambient_space_requirement",
              "topology_or_measure_requirement", "quantifier_form", "generic_set_template", "excluded_set_template"]))

    # N2 -- all 12 ordered pairs with state and required support
    pairs = {(r["from"], r["to"]): r for r in m.get("transfer_matrix", [])}
    expected = {(a, b) for a in vocab for b in vocab if a != b}
    n2_complete = set(pairs) == expected
    check("N2_all_ordered_pairs", n2_complete, f"expected={len(expected)} got={len(pairs)} missing={sorted(expected - set(pairs))}")
    bad = []
    for (a, b), r in pairs.items():
        if r.get("state") not in {"holds", "fails", "open"}:
            bad.append(f"{a}->{b}:bad_state")
        if not r.get("falsifier"):
            bad.append(f"{a}->{b}:no_falsifier")
        if r["state"] == "fails" and not r.get("witness_or_source"):
            bad.append(f"{a}->{b}:fails_without_witness")
        if r["state"] in {"holds", "open"} and not r.get("extra_hypothesis"):
            bad.append(f"{a}->{b}:{r['state']}_without_extra_hypothesis")
    check("N2_row_support", not bad, ",".join(bad) or "12/12 rows supported")

    # N2b -- strength partial order consistent with the transfer matrix
    spo = m.get("strength_partial_order", {})
    spo_bad = []
    for a, b in spo.get("strict_implications", []):
        fwd, rev = pairs.get((a, b), {}).get("state"), pairs.get((b, a), {}).get("state")
        if fwd != "holds" or rev != "fails":
            spo_bad.append(f"{a}=>{b}:fwd={fwd},rev={rev}")
    check("N2b_strength_partial_order", not spo_bad, ";".join(spo_bad) or "3 strict implications consistent")

    # N3 -- one falsifier per row (notions and transfers)
    n3 = all(v.get("falsifier") for v in notions.values()) and all(r.get("falsifier") for r in pairs.values())
    check("N3_falsifier_per_row", n3, f"notions={len(notions)} transfers={len(pairs)}")

    # N4 -- citation honesty
    cits = m.get("citations", {})
    bad_c = []
    for cid, c in cits.items():
        if c.get("citation_status") not in spec["vocabularies"]["citation_status"]:
            bad_c.append(f"{cid}:bad_status")
        if c.get("citation_status") == "verified":
            for f in ["url", "retrieved_at", "fetched_quote"]:
                if not c.get(f):
                    bad_c.append(f"{cid}:verified_missing_{f}")
    unresolved = m.get("unresolved", [])
    n4 = (not bad_c) and m.get("no_theorem_claim") is True and all(u.get("next_step") for u in unresolved)
    check("N4_citation_honesty", n4, f"citations={len(cits)} unresolved_items={len(unresolved)} issues={bad_c}")

    # N5 -- R07-shaped per-class sections
    v = spec["vocabularies"]["genericity_kind"]
    sec_bad = []
    for cid in classes:
        s = m.get("per_class_genericity_section", {}).get(cid)
        if not s:
            sec_bad.append(f"{cid}:missing"); continue
        if s.get("kind") not in v:
            sec_bad.append(f"{cid}:kind_not_in_vocab")
        for f in ["ambient_space", "topology_or_measure", "generic_set", "excluded_set",
                  "transfer_failures", "is_part_of_class", "changing_notion_statement", "falsifier"]:
            if not s.get(f):
                sec_bad.append(f"{cid}:missing_{f}")
        if not s.get("transfer_failures"):
            sec_bad.append(f"{cid}:empty_transfer_failures")
        if s.get("is_part_of_class") is not True:
            sec_bad.append(f"{cid}:is_part_of_class_not_true")
        if "different class" not in s.get("changing_notion_statement", ""):
            sec_bad.append(f"{cid}:changing_notion_statement_weak")
    check("N5_r07_sections", not sec_bad and set(m.get("per_class_genericity_section", {})) == set(classes),
          ";".join(sec_bad) or "3/3 classes R07-shaped")

    ok = all(r[1] for r in results)
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name}  {detail}")
    print(f"\nFORM-GEN-05 acceptance: {'PASS' if ok else 'FAIL'} ({sum(1 for r in results if r[1])}/{len(results)} checks)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
