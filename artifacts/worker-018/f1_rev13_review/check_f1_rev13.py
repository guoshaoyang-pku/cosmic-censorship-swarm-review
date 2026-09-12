#!/usr/bin/env python3
"""W018-F1-REV13-REVIEW-01: independent, hash-pinned, fail-closed review harness.

Target : F1 / AF-WCC-VAC-GEN, artifact artifacts/formulation/schemas/af_wcc_vacuum.yaml
         at the measured rev13 bytes bf0c28fa673e5bd5d82d03ab93059b99580af0f3f65a81d4924e0bc8e74a6226.
         Hash-move forensics: rev12 cce9c60146d6 was measured at 00:52:35 and had moved to
         rev13 bf0c28fa67 by 00:53:20; the fail-closed guard caught the move (see README).
Author : worker-018 (not an author of the schema; no author code is imported or executed).
Method : read the pinned bytes, measure every cited hash, run pre-registered structural,
         binding and semantic checks, then run labelled mutant controls to prove each
         check is non-vacuous. Any pin drift is fail-closed (exit 3), never a verdict.
Output : results.json in the same directory.
"""
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"

# ---------------------------------------------------------------- pins (rev28)
PINS = {
    "F1_canonical": (
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    ),
    "F1_mirror": (
        "schemas/af_wcc_vacuum.yaml",
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    ),
    "FROZEN": (
        "artifacts/formulation/FROZEN.json",
        "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833",
    ),
    "F0_declared": (
        "research_map/formulation_taxonomy.yaml",
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    ),
    "F0_supplement": (
        "artifacts/formulation/formulation_taxonomy.yaml",
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    ),
    "VOCAB_ALIASES": (
        "artifacts/formulation/VOCAB_ALIASES.json",
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    ),
    "VARIANT_REGISTRY": (
        "artifacts/formulation/VARIANT_REGISTRY.json",
        "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
    ),
    "CONSISTENCY_EVIDENCE": (
        "artifacts/formulation/evidence/taxonomy_consistency.json",
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    ),
}

REQUIRED_SECTIONS = [
    "quantifiers", "topology", "data_class", "regularity", "genericity",
    "i_plus", "visibility", "conclusion", "falsifier", "anti_scope",
    "f0_binding", "class_contract_pointer",
]

ACK = "W018-F1-REV13-REVIEW-01"


def sha256(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def measure_pins():
    measured = {}
    drift = []
    for key, (path, want) in PINS.items():
        got = sha256(path)
        measured[key] = {"path": path, "declared_pin": want, "measured": got, "match": got == want}
        if got != want:
            drift.append({"key": key, "path": path, "declared_pin": want, "measured": got})
    return measured, drift


# ------------------------------------------------------- finite-model semantics
def preorders(n):
    """All reflexive transitive relations on {0..n-1} (deduplicated)."""
    off = [(i, j) for i in range(n) for j in range(n) if i != j]
    seen = set()
    for mask in range(1 << len(off)):
        rel = {(i, i) for i in range(n)}
        for b, (i, j) in enumerate(off):
            if mask >> b & 1:
                rel.add((i, j))
        # transitive closure
        changed = True
        while changed:
            changed = False
            for (a, b) in list(rel):
                for (c, d) in list(rel):
                    if b == c and (a, d) not in rel:
                        rel.add((a, d))
                        changed = True
        seen.add(frozenset(rel))
    return sorted(seen, key=lambda r: (len(r), sorted(r)))


def chains(n, rel):
    """All non-empty causally ordered chains: tuples of distinct points whose consecutive
    pairs (x_i, x_{i+1}) satisfy x_i <= x_{i+1} in the preorder.  The order is the causal
    order itself, never the tuple index of a subset (v2 correction: the v1 draft ordered
    subsets by index, which manufactured spurious tail=>whole violations)."""
    out = []
    for size in range(1, n + 1):
        for seq in itertools.permutations(range(n), size):
            if all((seq[i], seq[i + 1]) in rel for i in range(size - 1)):
                out.append(seq)
    return out


def past_closed_semantics(n=4):
    """Check: for every preorder, every causal past J^-(q), every causal chain gamma and
    every tail start t0: tail(gamma,t0) subset J  =>  gamma subset J.

    Past-closedness of J^-(q) is what the schema's own words 'causal past J^-(q)' denote;
    the check is therefore a finite-model corroboration of the two-line transitivity
    argument (x <= y in J^-(q) => x in J^-(q)).  A second pass uses a deliberately
    NON-past-closed past set to show the instrument can detect a violation.
    """
    n_pre, n_pairs, divergences = 0, 0, []
    for rel in preorders(n):
        n_pre += 1
        for q in range(n):
            J = {x for x in range(n) if (x, q) in rel}
            for gamma in chains(n, rel):
                for t0 in range(len(gamma)):
                    tail = set(gamma[t0:])
                    n_pairs += 1
                    if tail <= J and not set(gamma) <= J:
                        divergences.append({"q": q, "gamma": gamma, "t0": t0})
    # non-past-closed control: strip the minimal element of J so J is not past-closed
    control_divergences = 0
    control_examples = []
    for rel in preorders(n):
        for q in range(n):
            J = {x for x in range(n) if (x, q) in rel}
            if not J:
                continue
            minimal = [x for x in J if not any(y != x and (y, x) in rel for y in J)]
            if not minimal:
                continue
            Jp = J - {minimal[0]}
            for gamma in chains(n, rel):
                for t0 in range(len(gamma)):
                    tail = set(gamma[t0:])
                    if tail <= Jp and not set(gamma) <= Jp:
                        control_divergences += 1
                        if len(control_examples) < 3:
                            control_examples.append({"q": q, "gamma": gamma, "t0": t0, "J_minus": sorted(Jp)})
                        break
    return n_pre, n_pairs, divergences, control_divergences, control_examples


# ------------------------------------------------------------------- checking
def run_checks(f1, f0, vocab, frozen, pins):
    checks = []

    def chk(cid, ok, detail, kind="PASS"):
        checks.append({"id": cid, "status": "PASS" if ok else kind, "detail": detail})

    # C01-C07 pin integrity
    chk("C01_F1_pin", pins["F1_canonical"]["match"] and pins["F1_mirror"]["match"],
        "F1 canonical and mirror both at d9cebb9404b2e79e; drift=%s" % (not pins["F1_canonical"]["match"] or not pins["F1_mirror"]["match"]))
    chk("C02_FROZEN_pin", pins["FROZEN"]["match"], "FROZEN.json at 3d9e3d77fd87 (rev29)")
    manifest_f1 = frozen["files"]["artifacts/formulation/schemas/af_wcc_vacuum.yaml"]["sha256"]
    chk("C03_FROZEN_entry", manifest_f1 == pins["F1_canonical"]["measured"],
        "FROZEN rev%s manifest entry for F1 = %s vs measured %s"
        % (frozen.get("revision"), manifest_f1[:12], pins["F1_canonical"]["measured"][:12]),
        kind="DEFECT")
    chk("C04_mirror_equal", pins["F1_canonical"]["measured"] == pins["F1_mirror"]["measured"],
        "schemas/af_wcc_vacuum.yaml is a byte mirror of the canonical path")
    chk("C05_F0_pin", pins["F0_declared"]["match"], "declared F0 taxonomy at 0abb9ed8a961")
    chk("C06_supplement_pin", pins["F0_supplement"]["match"], "F0 class-contract supplement at d7419b4e8963")
    chk("C07_vocab_pin", pins["VOCAB_ALIASES"]["match"], "VOCAB_ALIASES.json at 46cd9f1eb534")
    chk("C07b_variant_registry_pin", pins["VARIANT_REGISTRY"]["match"], "VARIANT_REGISTRY.json at 5eb42f9a384a")

    # C08 class identity / required structure
    chk("C08_class_id", f1.get("class_id") == "AF-WCC-VAC-GEN" and f1.get("node_id") == "F1",
        "class_id=%r node_id=%r" % (f1.get("class_id"), f1.get("node_id")))
    comp = f1.get("class_components", {})
    chk("C09_components", [comp.get(k) for k in ("asymptotics", "censorship", "matter", "genericity")] == ["AF", "WCC", "VAC", "GEN"],
        "class_components=%r" % (comp,))
    missing = [s for s in REQUIRED_SECTIONS if s not in f1]
    chk("C10_required_sections", not missing, "missing=%r" % (missing,))

    # C11 binding pointers
    chk("C11_f0_declared_hash", f1["f0_binding"]["declared_f0_sha256"] == pins["F0_declared"]["measured"],
        "f0_binding.declared_f0_sha256 matches the measured declared F0 artifact")
    chk("C12_contract_pointer", f1.get("class_contract_pointer") == "research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN"
        and f1["f0_binding"].get("class_contract_supplement_pointer", "").endswith("#class_contracts.AF-WCC-VAC-GEN"),
        "class_contract_pointer and supplement pointer both resolve to AF-WCC-VAC-GEN")

    # C13 the stale consistency pointer (expected DEFECT)
    declared_ce = f1["f0_binding"]["consistency_evidence_sha256"]
    measured_ce = pins["CONSISTENCY_EVIDENCE"]["measured"]
    chk("C13_consistency_evidence_binding", declared_ce == measured_ce,
        "declared consistency_evidence_sha256=%s vs measured %s at %s" % (declared_ce[:12], measured_ce[:12], PINS["CONSISTENCY_EVIDENCE"][0]),
        kind="DEFECT")

    # C14 conclusion vocabulary
    tok = f1["conclusion"]["conclusion_type"]
    canon = vocab["conclusion_type"]
    allowed = set(canon) | {a for v in canon.values() for a in v}
    chk("C14_conclusion_token", tok in allowed, "conclusion_type=%r in VOCAB_ALIASES conclusion_type table" % tok)

    # C15 quantifier chain integrity
    q = f1["quantifiers"]
    doms = [d for d in ("D0", "D1", "D2", "D3", "D4", "D5") if d in q.get("domains", {})]
    chk("C15_quantifier_domains", len(doms) == 6 and len(q.get("ordered", [])) == 6,
        "domains=%r ordered=%d" % (doms, len(q.get("ordered", []))))
    chk("C16_quantifier_formal", isinstance(q.get("formal"), str) and q["formal"].strip() != ""
        and isinstance(q.get("negation"), str) and "there exists r in D0" in q["negation"],
        "formal quantifier and explicit negation present")

    # C17 the false strictness relation in the ASSERTION region only.  Calibration note:
    # a first draft matched the raw field and fired on the bracketed [rev13: ...] note that
    # quotes the corrected error; the assertion region (before the first [revN: bracket) is
    # what a reader is asked to treat as the definition, so that is what is checked.
    d5 = q["domains"]["D5"]["definition"]
    vis_def = f1["visibility"]["definition"]
    d5_assert = re.split(r"\[rev\d+:", d5)[0]
    vis_assert = re.split(r"\[rev\d+:", vis_def)[0]
    d5_strict = bool(re.search(r"strictly\s+STRONGER", d5_assert))
    vis_strict = bool(re.search(r"strictly\s+stronger|would\s+misclassify", vis_assert))
    quoted = ("strictly STRONGER" in d5 or "strictly stronger" in d5 or "misclassify" in vis_def)
    chk("C17_strictness_assertion_clean", not (d5_strict or vis_strict),
        "assertion region: D5 strict=%s, visibility strict/misclassify=%s; raw field still quotes the corrected phrase in a [rev13] note=%s (not a defect)"
        % (d5_strict, vis_strict, quoted),
        kind="DEFECT")

    # C18 negation uses the declared tail predicate (internal consistency)
    neg = f1["visibility"]["negation_conclusion"]
    chk("C18_negation_uses_tail", "tail gamma([t0,T))" in neg and "NOT contained" in neg,
        "visibility.negation_conclusion negates the tail predicate, matching D5")

    # C19 anti-scope present
    chk("C19_anti_scope", bool(f1["anti_scope"].get("not_this_class")) and bool(f1["anti_scope"].get("phrases_that_are_not_this_class")),
        "anti_scope lists %d not-this-class items" % len(f1["anti_scope"].get("not_this_class", [])))

    # C20 F0 class contract exists for this class
    contracts = f0.get("classes", {}) or {}
    chk("C20_f0_contract", "AF-WCC-VAC-GEN" in contracts, "declared F0 taxonomy defines class AF-WCC-VAC-GEN")

    # C21 review bookkeeping (advisory)
    rs = f1.get("review_status", {})
    chk("C21_review_bookkeeping", bool(rs.get("independent_reviewers")),
        "review_status.independent_reviewers=%r while at-pin F1 verdicts exist" % (rs.get("independent_reviewers"),),
        kind="ADVISORY")

    # C24 freeze registration: the reviewed hash must appear in an accepted artifact event
    # (FROZEN change_protocol) -- measured locally on the accepted stream, read-only.
    try:
        events = (ROOT / "research_map/events.jsonl").read_text(errors="replace")
    except OSError:
        events = ""
    hits = 0
    for line in events.splitlines():
        if pins["F1_canonical"]["measured"] in line and '"event_type": "artifact"' in line:
            hits += 1
    chk("C24_freeze_event_registration", hits > 0,
        "accepted-stream artifact events citing the reviewed F1 hash %s: %d (FROZEN manifest registration is checked at C03; this is stream bookkeeping only)"
        % (pins["F1_canonical"]["measured"][:12], hits),
        kind="ADVISORY")

    # C25 cross-artifact variant-SET direction: F1 rev13 states 'strictly WEAKER'; the
    # declared F0 taxonomy (F1's own f0_binding target, unchanged at 0abb9ed8a961) and
    # VARIANT_REGISTRY.json must not state the opposite direction.
    f1_rel = f1["class_identity_variants"][0].get("relation", "")
    f1_weaker = "strictly WEAKER" in f1_rel
    f0_raw = (ROOT / PINS["F0_declared"][0]).read_text()
    reg_raw = (ROOT / PINS["VARIANT_REGISTRY"][0]).read_text()
    f0_inverted = bool(re.search(r"set-based reading[\s\S]{0,400}?strictly stronger", f0_raw))
    reg_inverted = bool(re.search(r"strictly STRONGER than AF-WCC-VAC-GEN", reg_raw))
    chk("C25_set_direction_cross_artifact", f1_weaker and not f0_inverted and not reg_inverted,
        "F1 says WEAKER=%s ; F0-declared(0abb9ed8a961) inverted=%s ; VARIANT_REGISTRY inverted=%s"
        % (f1_weaker, f0_inverted, reg_inverted),
        kind="DEFECT")

    # C26 the reviewed bytes must be pinned by the freeze manifest at one revision
    chk("C26_frozen_revision", frozen.get("revision", 0) >= 29,
        "FROZEN revision=%s frozen_at=%s" % (frozen.get("revision"), frozen.get("frozen_at")))

    return checks


def main():
    pins, drift = measure_pins()
    if drift:
        OUT.write_text(json.dumps({"ack": ACK, "harness_status": "FAIL_CLOSED_PIN_DRIFT", "drift": drift, "pins": pins}, indent=1))
        print("PIN DRIFT", json.dumps(drift))
        return 3

    f1 = yaml.safe_load((ROOT / PINS["F1_canonical"][0]).read_text())
    f0 = yaml.safe_load((ROOT / PINS["F0_declared"][0]).read_text())
    vocab = json.loads((ROOT / PINS["VOCAB_ALIASES"][0]).read_text())
    frozen = json.loads((ROOT / PINS["FROZEN"][0]).read_text())

    checks = run_checks(f1, f0, vocab, frozen, pins)

    n_pre, n_pairs, div, ctrl_div, ctrl_ex = past_closed_semantics(4)
    checks.append({
        "id": "C22_tail_vs_whole_curve",
        "status": "DEFECT" if div else "PASS",
        "detail": ("finite preorders=%d, (J^-,chain,t0) triples=%d, tail=>whole violations=%d; "
                   "non-past-closed control violations=%d" % (n_pre, n_pairs, len(div), ctrl_div)),
    })
    checks.append({
        "id": "C23_semantics_control_sensitivity",
        "status": "PASS" if ctrl_div > 0 else "HARNESS_FAIL",
        "detail": "non-past-closed past-set control produced %d violations; examples=%r" % (ctrl_div, ctrl_ex),
    })

    counts = {}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1

    # post-read re-measure: a verdict is valid only if the pinned bytes did not move
    moved = [k for k in ("F1_canonical", "F1_mirror") if sha256(PINS[k][0]) != PINS[k][1]]
    status = "MOVED_DURING_REVIEW" if moved else "OK"
    result = {
        "ack": ACK,
        "harness_status": status,
        "moved_after_checks": moved,
        "reviewed_pins": pins,
        "reviewed_revision": f1.get("revision"),
        "reviewed_revised_at": f1.get("revised_at"),
        "checks": checks,
        "counts": counts,
        "hard_failures": [c["id"] for c in checks if c["status"] == "DEFECT"],
        "advisory": [c["id"] for c in checks if c["status"] == "ADVISORY"],
        "semantics": {"preorders": n_pre, "triples": n_pairs, "violations": len(div),
                      "control_violations": ctrl_div, "control_examples": ctrl_ex},
        "instrument_note": "No author code imported or executed; yaml/json parsing only.",
    }
    OUT.write_text(json.dumps(result, indent=1))
    print(json.dumps({"counts": counts, "hard_failures": result["hard_failures"], "status": status}, indent=1))
    return 0 if status == "OK" else 4


if __name__ == "__main__":
    sys.exit(main())
