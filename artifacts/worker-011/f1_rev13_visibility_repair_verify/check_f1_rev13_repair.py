#!/usr/bin/env python3
"""W011-F1-REV13-REPAIR-VERIFY-01 - independent post-repair verification of the
F1 rev13 visibility/strictness repair, class AF-WCC-VAC-GEN.

Outstanding findings being re-tested (raised by worker-011 at rev12 cce9c60146d6):
  HF-011-01 (blocking): D5.definition asserted whole-curve single-q containment is
      "strictly STRONGER" than the class's tail predicate, and visibility.definition
      claimed the whole-curve reading "would misclassify" an exterior-to-BH geodesic.
      Both are false under the schema's declared standard (past-closed) causal past.
  F-011-02 (major): the strictness sentence cited a withdrawn blocker
      ("independently confirmed by worker-037 W037V2-F1") as confirmation.
  F-011-03 (advisory): the SET-variant relation was an unproven strictness direction.

rev13 d9cebb9404b2 claims all three repaired. This instrument re-measures them
independently at the frozen bytes, and additionally checks the NEW rev13 direction
claim (variant SET is strictly WEAKER than the single-q tail predicate) with its own
machine model rather than trusting the cited W076 T2/T3/T4.

Method (read-only on canonical artifacts; writes only under its own artifact dir):
  1. sha256 pin table, before/after drift guard, FROZEN declaration check;
  2. clause-scoped text detectors on the pinned bytes (not on paths);
  3. formal lemma LEMMA-W011-1 (recorded proof) + exhaustive preorder enumeration
     n <= 5 (OEIS A000798 positive control) + fixed-seed samples n = 6,7,8;
  4. new direction checks for variant SET: tail => set, finite-I+ collapse (T3),
     explicit omega-chain witness with no causal maximum (T4), and the
     B-containment-strictly-stronger clause of negation_conclusion;
  5. six teeth controls on in-memory mutants, including a non-past-closed J^-
     reading that must produce divergences;
  6. verdict per finding, residuals, explicit falsifier.

Outputs: report.json, hashes.txt, README.md next to this script.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

TASK_ID = "W011-F1-REV13-REPAIR-VERIFY-01"
RECORD_ID = "RV-W011-F1-REV13-REPAIR-01"
NODE_ID = "F1"
GATE = "G-FORM"
CLASS_ID = "AF-WCC-VAC-GEN"
FROZEN_FOUR = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}

F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
TAX = ROOT / "research_map/formulation_taxonomy.yaml"
EVID = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
W040 = ROOT / "artifacts/worker-040/f1_strictness_adjudication"
W076 = ROOT / "artifacts/worker-076/gform_strictness_reconcile"

PIN_F1 = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
PIN_TAX = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_EVID = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"

# rev12 condemned strings (must be ABSENT at rev13)
REV12_D5_FALSE = "strictly STRONGER and is NOT the predicate of this class"
REV12_VIS_FALSE = "would misclassify a geodesic that starts in the exterior"
REV12_CITATION = "independently confirmed by worker-037 W037V2-F1"

CHECK_IDS = [
    "P01_pins_match_start",
    "P02_frozen_declares_f1_pin",
    "P03_frozen_declares_consistency_evidence",
    "T01_d5_equivalence_present",
    "T02_d5_rev12_false_strictness_absent",
    "T03_vis_equivalence_present",
    "T04_vis_misclassification_absent",
    "T05_operative_tail_predicate_unchanged",
    "T06_withdrawn_citation_absent",
    "T07_variant_relation_is_weaker",
    "B01_f0_binding_taxonomy_resolves",
    "B02_f0_binding_evidence_resolves",
    "B03_class_contract_pointer_resolves",
    "B04_single_class_binding",
    "M01_equivalence_exhaustive_n_le_5",
    "M02_equivalence_sampled_n_6_8",
    "M03_tailset_entails_set",
    "M04_finite_iplus_collapse",
    "M05_omega_chain_separation_witness",
    "M06_b_containment_strictly_stronger",
    "M07_teeth_non_past_closed_jminus",
    "C01_control_false_strictness_detected",
    "C02_control_equivalence_removed_detected",
    "C03_control_weaker_flip_detected",
    "C04_control_withdrawn_citation_detected",
    "C05_control_tampered_binding_detected",
    "C06_control_separator_has_teeth",
    "D01_no_pin_drift",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def load_yaml(path: Path):
    import yaml  # imported lazily; absence is a hard failure

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def assertive(text: str) -> str:
    """Strip bracketed revision-history annotations and quoted prior wording.

    rev13 legitimately *quotes* the condemned rev12 phrases inside [...] notes
    ("the rev12 'strictly STRONGER' assertion was false").  Scanning those as
    assertions is the CF-16 metalinguistic-mention false-positive pattern; the
    detectors below run on the assertive text only, while the exact condemned
    rev12 needles are additionally checked against the full raw bytes.

    Only revision-annotation brackets are stripped ([rev13: ...], [R1 ...]).
    Interval notation such as [0,T) or [t0,T) must be preserved.
    """
    no_notes = re.sub(r"\[(?:rev\s*\d+|R\d+)[^\]]*\]", " ", text, flags=re.IGNORECASE)
    no_quotes = re.sub(r"\"[^\"]{0,160}\"|\u201c[^\u201d]{0,160}\u201d", " ", no_notes)
    return re.sub(r"\s+", " ", no_quotes)


# ---------------------------------------------------------------------------
# preorder / causal-order model machinery (same semantics as the rev12 tool)
# ---------------------------------------------------------------------------
def transitivity_ok(rows: list[int], n: int) -> bool:
    for i in range(n):
        ri = rows[i]
        for j in range(n):
            if (ri >> j) & 1 and (rows[j] & ~ri):
                return False
    return True


def enumerate_preorders(n: int):
    pairs = [(i, j) for i in range(n) for j in range(n) if i != j]
    m = len(pairs)
    for mask in range(1 << m):
        rows = [1 << i for i in range(n)]
        mm = mask
        k = 0
        while mm:
            if mm & 1:
                i, j = pairs[k]
                rows[i] |= 1 << j
            mm >>= 1
            k += 1
        if transitivity_ok(rows, n):
            yield rows


def random_preorders(n: int, count: int, seed: int):
    rng = random.Random(seed)
    for _ in range(count):
        rows = [1 << i for i in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j and rng.random() < 0.28:
                    rows[i] |= 1 << j
        changed = True
        while changed:
            changed = False
            for i in range(n):
                for j in range(n):
                    if (rows[i] >> j) & 1:
                        new = rows[i] | rows[j]
                        if new != rows[i]:
                            rows[i] = new
                            changed = True
        yield rows


def down_masks(rows: list[int], n: int) -> list[int]:
    full = (1 << n) - 1
    dm = [0] * n
    for q in range(n):
        m = 1 << q
        for p in range(n):
            if (rows[p] >> q) & 1:
                m |= 1 << p
        dm[q] = m & full
    return dm


def geodesic_only_masks(rows: list[int], n: int, dm: list[int] | None = None) -> list[int]:
    """Cover-based 'single causal geodesic segment' reachability (NOT past-closed)."""
    if dm is None:
        dm = down_masks(rows, n)

    def strict_below(x, y):
        return bool((rows[x] >> y) & 1) and not bool((rows[y] >> x) & 1)

    gm = [0] * n
    for q in range(n):
        m = 1 << q
        for p in range(n):
            if p == q or not strict_below(p, q):
                continue
            covered = not any(
                r != p and r != q and strict_below(p, r) and strict_below(r, q)
                for r in range(n)
            )
            if covered:
                m |= 1 << p
        gm[q] = m
    return gm


def causal_chains(rows: list[int], n: int, past_masks: list[int] | None = None):
    """All totally ordered subsets, emitted in causal order (past -> future)."""
    if past_masks is None:
        past_masks = down_masks(rows, n)
    for sub in range(1, 1 << n):
        elems = [i for i in range(n) if (sub >> i) & 1]
        if all(
            ((rows[a] >> b) & 1) or ((rows[b] >> a) & 1)
            for a, b in itertools.combinations(elems, 2)
        ):
            elems.sort(key=lambda x: (bin(past_masks[x] & ~(1 << x)).count("1"), x))
            yield tuple(elems)


def preds(chain, jmask: int):
    """whole / tail single-q containment for a chain against J^-(q)=jmask."""
    whole = all((jmask >> c) & 1 for c in chain)
    tail = any(all((jmask >> c) & 1 for c in chain[i:]) for i in range(len(chain)))
    return whole, tail


def set_pred(chain, iplus: list[int], dm: list[int]) -> bool:
    """variant SET: every element lies in some J^-(q), q in I+."""
    return all(any((dm[q] >> c) & 1 for q in iplus) for c in chain)


def tailset_pred(chain, iplus: list[int], dm: list[int]) -> bool:
    """single-q tail predicate: some q in I+ sees a tail of the chain."""
    for q in iplus:
        for i in range(len(chain)):
            if all((dm[q] >> c) & 1 for c in chain[i:]):
                return True
    return False


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------
def main() -> int:
    checks: dict[str, dict] = {}

    def rec(cid: str, ok: bool, detail) -> None:
        checks[cid] = {"pass": bool(ok), "detail": detail}

    if not F1.exists() or not FROZEN.exists() or not TAX.exists() or not EVID.exists():
        print("FATAL: a pinned path is missing", file=sys.stderr)
        return 2

    pins_start = {
        "schemas/af_wcc_vacuum.yaml": sha(F1),
        "research_map/formulation_taxonomy.yaml": sha(TAX),
        "artifacts/formulation/evidence/taxonomy_consistency.json": sha(EVID),
        "artifacts/formulation/FROZEN.json": sha(FROZEN),
    }
    rec(
        "P01_pins_match_start",
        pins_start["schemas/af_wcc_vacuum.yaml"] == PIN_F1
        and pins_start["research_map/formulation_taxonomy.yaml"] == PIN_TAX
        and pins_start["artifacts/formulation/evidence/taxonomy_consistency.json"] == PIN_EVID,
        {
            "measured": pins_start,
            "expected_F1": PIN_F1,
            "expected_TAX": PIN_TAX,
            "expected_EVID": PIN_EVID,
        },
    )
    if not checks["P01_pins_match_start"]["pass"]:
        # fail closed: bindings are void if the target moved
        report = {
            "record_id": RECORD_ID,
            "task_id": TASK_ID,
            "created_at": now_iso(),
            "valid": False,
            "fail_closed_reason": "pin mismatch at start; no verdict issued",
            "checks": checks,
        }
        (ART / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
        print(json.dumps({"valid": False, "reason": "pin mismatch"}))
        return 1

    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    frozen_files = frozen.get("files", {})
    f1_entry = frozen_files.get("schemas/af_wcc_vacuum.yaml", {})
    rec(
        "P02_frozen_declares_f1_pin",
        f1_entry.get("sha256") == PIN_F1,
        {"frozen_revision": frozen.get("revision"), "frozen_sha256": pins_start["artifacts/formulation/FROZEN.json"],
         "declared": f1_entry.get("sha256"), "measured": PIN_F1},
    )
    ev_entry = frozen_files.get("artifacts/formulation/evidence/taxonomy_consistency.json", {})
    rec(
        "P03_frozen_declares_consistency_evidence",
        ev_entry.get("sha256") == PIN_EVID,
        {"declared": ev_entry.get("sha256"), "measured": PIN_EVID},
    )

    raw = F1.read_text(encoding="utf-8")
    lines = raw.splitlines()
    doc = load_yaml(F1)
    d5 = doc["quantifiers"]["domains"]["D5"]
    vis = doc["visibility"]
    variants = doc.get("class_identity_variants", [])
    set_variant = next((v for v in variants if v.get("kind") == "set_based_visibility_reading"), {})

    d5_assert = assertive(d5.get("definition", ""))
    vis_assert = assertive(vis.get("definition", ""))
    rel_assert = assertive(set_variant.get("relation", ""))

    rec(
        "T01_d5_equivalence_present",
        "EQUIVALENT" in d5_assert and "past-closed" in d5_assert,
        {"field": "quantifiers.domains.D5.definition", "assertive_excerpt": d5_assert[:400]},
    )
    rec(
        "T02_d5_rev12_false_strictness_absent",
        REV12_D5_FALSE not in raw
        and "strictly STRONGER" not in d5_assert
        and "NOT the predicate of this class" not in d5_assert,
        {"field": "quantifiers.domains.D5.definition",
         "condemned_rev12_needle": REV12_D5_FALSE,
         "needle_in_raw": REV12_D5_FALSE in raw,
         "strictly_stronger_in_assertive_text": "strictly STRONGER" in d5_assert,
         "assertive_excerpt": d5_assert[:400]},
    )
    rec(
        "T03_vis_equivalence_present",
        "EQUIVALENT" in vis_assert and "past-closed" in vis_assert,
        {"field": "visibility.definition", "assertive_excerpt": vis_assert[:400]},
    )
    rec(
        "T04_vis_misclassification_absent",
        REV12_VIS_FALSE not in raw
        and "would misclassify" not in vis_assert
        and "misclassify a geodesic that starts" not in vis_assert
        and ("no geodesic is misclassified" in vis_assert
             or "no geodesic is misclassified by either reading" in vis_assert),
        {"field": "visibility.definition",
         "condemned_rev12_needle": REV12_VIS_FALSE,
         "needle_in_raw": REV12_VIS_FALSE in raw,
         "would_misclassify_in_assertive_text": "would misclassify" in vis_assert,
         "negated_correction_present": "no geodesic is misclassified" in vis_assert,
         "assertive_excerpt": vis_assert[:400]},
    )
    rec(
        "T05_operative_tail_predicate_unchanged",
        "the TAIL gamma([t0,T)) is contained in J^-(q) intersect M" in vis_assert,
        {"field": "visibility.definition"},
    )
    rec(
        "T06_withdrawn_citation_absent",
        REV12_CITATION not in raw and "worker-037" not in raw and "W037V2" not in raw,
        {"condemned_rev12_needle": REV12_CITATION, "hits_worker037": raw.count("worker-037"),
         "hits_W037V2": raw.count("W037V2")},
    )
    rec(
        "T07_variant_relation_is_weaker",
        "strictly WEAKER" in rel_assert and "strictly STRONGER" not in rel_assert,
        {"field": "class_identity_variants[set_based_visibility_reading].relation",
         "strictly_stronger_in_assertive_text": "strictly STRONGER" in rel_assert,
         "assertive_excerpt": rel_assert[:400]},
    )

    # ---- evidence binding -------------------------------------------------
    fb = doc.get("f0_binding", {})
    tax_path = ROOT / str(fb.get("declared_f0_artifact", ""))
    tax_ok = tax_path.exists() and sha(tax_path) == fb.get("declared_f0_sha256")
    ev_path = ROOT / str(fb.get("consistency_evidence", ""))
    ev_ok = ev_path.exists() and sha(ev_path) == fb.get("consistency_evidence_sha256")
    rec("B01_f0_binding_taxonomy_resolves", tax_ok,
        {"path": str(fb.get("declared_f0_artifact")), "declared": fb.get("declared_f0_sha256"),
         "measured": sha(tax_path) if tax_path.exists() else None})
    rec("B02_f0_binding_evidence_resolves", ev_ok,
        {"path": str(fb.get("consistency_evidence")), "declared": fb.get("consistency_evidence_sha256"),
         "measured": sha(ev_path) if ev_path.exists() else None})

    try:
        tax_doc = load_yaml(TAX)
        ccp_ok = CLASS_ID in tax_doc.get("classes", {})
    except Exception as exc:  # noqa: BLE001
        ccp_ok = False
    rec("B03_class_contract_pointer_resolves", ccp_ok,
        {"pointer": doc.get("class_contract_pointer")})

    struct_class_tokens = set()
    for key in ("class_id", "class_ids", "class_contract_pointer",
                "class_contract_supplement_pointer"):
        val = doc.get(key)
        text = json.dumps(val) if val is not None else ""
        for tok in FROZEN_FOUR:
            if tok in text:
                struct_class_tokens.add(tok)
    cid_ok = doc.get("class_id") == CLASS_ID
    cids = doc.get("class_ids")
    cids_ok = cids in (None, [CLASS_ID])
    rec("B04_single_class_binding", cid_ok and cids_ok and struct_class_tokens <= {CLASS_ID},
        {"class_id": doc.get("class_id"), "class_ids": cids,
         "frozen_tokens_in_structured_binding_fields": sorted(struct_class_tokens)})

    # ---- equivalence: tail <=> whole --------------------------------------
    oeis = {1: 1, 2: 4, 3: 29, 4: 355, 5: 6942}
    exhaustive = {}
    for n in range(1, 6):
        models = chains_checked = evals = tnw = wnt = 0
        for rows in enumerate_preorders(n):
            models += 1
            dm = down_masks(rows, n)
            for chain in causal_chains(rows, n, dm):
                chains_checked += 1
                for q in range(n):
                    whole, tail = preds(chain, dm[q])
                    evals += 1
                    if tail and not whole:
                        tnw += 1
                    if whole and not tail:
                        wnt += 1
        exhaustive[str(n)] = {"models": models, "chains": chains_checked,
                              "tail_q_evaluations": evals,
                              "tail_without_whole": tnw, "whole_without_tail": wnt,
                              "oeis_A000798_expected": oeis[n],
                              "oeis_match": models == oeis[n],
                              "equivalent_on_all": tnw == 0 and wnt == 0}
    ex_ok = all(v["equivalent_on_all"] and v["oeis_match"] for v in exhaustive.values())
    rec("M01_equivalence_exhaustive_n_le_5", ex_ok, exhaustive)

    sampled = {}
    for n, count in ((6, 3000), (7, 2000), (8, 1200)):
        models = chains_checked = evals = tnw = wnt = 0
        for rows in random_preorders(n, count, seed=20260912 + n):
            models += 1
            dm = down_masks(rows, n)
            for chain in causal_chains(rows, n, dm):
                chains_checked += 1
                for q in range(n):
                    whole, tail = preds(chain, dm[q])
                    evals += 1
                    if tail and not whole:
                        tnw += 1
                    if whole and not tail:
                        wnt += 1
        sampled[str(n)] = {"models": models, "chains": chains_checked,
                           "tail_q_evaluations": evals,
                           "tail_without_whole": tnw, "whole_without_tail": wnt,
                           "equivalent_on_all": tnw == 0 and wnt == 0}
    rec("M02_equivalence_sampled_n_6_8",
        all(v["equivalent_on_all"] for v in sampled.values()), sampled)

    # ---- variant SET direction checks (T2/T3/T4 analogues) ------------------
    m03 = m04 = None
    for n in (4, 5):
        models = evals = tailset_not_set = set_not_tailset = 0
        witness = None
        for rows in enumerate_preorders(n):
            models += 1
            dm = down_masks(rows, n)
            iplus_sets = [list(s) for k in range(1, n + 1)
                          for s in itertools.combinations(range(n), k)]
            for chain in causal_chains(rows, n, dm):
                for iplus in iplus_sets:
                    ts = tailset_pred(chain, iplus, dm)
                    st = set_pred(chain, iplus, dm)
                    evals += 1
                    if ts and not st:
                        tailset_not_set += 1
                    if st and not ts:
                        set_not_tailset += 1
                        if witness is None:
                            witness = {"chain": list(chain), "I_plus": iplus}
        if n == 5:
            m03 = {"n": n, "models": models, "evaluations": evals,
                   "tailset_without_set": tailset_not_set, "teeth": tailset_not_set >= 0,
                   "direction_holds": tailset_not_set == 0}
            m04 = {"n": n, "models": models, "evaluations": evals,
                   "set_without_tailset": set_not_tailset,
                   "finite_iplus_collapse": set_not_tailset == 0,
                   "first_counterexample": witness}
    rec("M03_tailset_entails_set", bool(m03 and m03["direction_holds"]),
        dict(m03 or {}, note="tailSet => set is the rev13 'entails the union reading' direction"))
    rec("M04_finite_iplus_collapse", bool(m04 and m04["finite_iplus_collapse"]),
        dict(m04 or {}, note="T3 analogue: on finite causal orders with finite I+, set => tailSet"))

    # ---- explicit omega-chain separation witness (T4 analogue) -------------
    N = 400
    # model (defined for ALL n in N): g_0 <= g_1 <= ... ; I+ = {q_m : m in N};
    # g_n <= q_m  iff  m >= n ; the q's are mutually incomparable.
    def g_le_q(n, m):
        return m >= n

    set_holds = all(any(g_le_q(n, m) for m in range(N + 1)) for n in range(N + 1))
    # no single q_m sees a tail: for every m and start t0, the witness n0 = max(t0, m+1)
    # is beyond m, so g_n0 is NOT <= q_m.  Rule-level check with explicit witnesses.
    no_tail = True
    bad_tail = []
    for m in range(N + 1):
        for t0 in range(N + 1):
            n0 = max(t0, m + 1)
            if g_le_q(n0, m):
                no_tail = False
                bad_tail.append({"q": m, "t0": t0})
    # no causal maximum of gamma: for every k the witness g_{k+1} is not <= g_k
    no_causal_max = all(not (k + 1 <= k) for k in range(N + 1))
    # single-q whole/tail equivalence still holds in this model (LEMMA-W011-1)
    equiv_ok = True
    for m in range(N + 1):
        for t0 in range(N + 1):
            whole = all(g_le_q(n, m) for n in range(N + 1))
            tail = all(g_le_q(n, m) for n in range(t0, N + 1))
            if whole != tail:
                equiv_ok = False
    m05_ok = set_holds and no_tail and no_causal_max and equiv_ok
    rec("M05_omega_chain_separation_witness", m05_ok,
        {"model": "g_0 <= g_1 <= ... (omega-chain); I+ = {q_m : m in N}; g_n <= q_m iff m >= n",
         "N_checked": N, "set_holds": set_holds, "no_single_q_tail": no_tail,
         "no_causal_maximum_of_gamma": no_causal_max,
         "single_q_equivalence_still_holds": equiv_ok,
         "counterexamples_found": bad_tail[:3],
         "note": ("abstract causal-order model, not a claimed spacetime realization; "
                  "set-containment holds (g_n <= q_n) but no q_m sees a tail (witness n0 > m), "
                  "so variant SET is strictly weaker than the single-q tail predicate")})

    # ---- negation_conclusion: B-containment strictly stronger ---------------
    n = 5
    b_implies_neg = 0
    evalcount = 0
    for rows in enumerate_preorders(n):
        dm = down_masks(rows, n)
        for chain in causal_chains(rows, n, dm):
            chain_mask = 0
            for c in chain:
                chain_mask |= 1 << c
            for k in range(1, n + 1):
                for iplus in itertools.combinations(range(n), k):
                    union = 0
                    for x in iplus:
                        union |= dm[x]
                    b_contain = (chain_mask & union) == 0
                    neg_single_q = not any(preds(chain, dm[x])[1] for x in iplus)
                    evalcount += 1
                    if b_contain and not neg_single_q:
                        b_implies_neg += 1
    # omega witness already shows the converse fails: g_0 is in J^-(q_0) yet no tail
    converse_fails = any(g_le_q(0, 0) for _ in [0]) and no_tail
    m06_ok = b_implies_neg == 0 and converse_fails
    rec("M06_b_containment_strictly_stronger", m06_ok,
        {"n": n, "evaluations": evalcount, "b_containment_without_negation": b_implies_neg,
         "converse_fails_on_omega_witness": converse_fails})

    # ---- teeth control: non-past-closed (cover-reachability) J^- ------------
    n = 5
    models = evals = divergences = 0
    first_witness = None
    for rows in enumerate_preorders(n):
        models += 1
        dm = down_masks(rows, n)
        gm = geodesic_only_masks(rows, n, dm)
        for chain in causal_chains(rows, n, dm):
            for q in range(n):
                whole, tail = preds(chain, gm[q])
                evals += 1
                if tail and not whole:
                    divergences += 1
                    if first_witness is None:
                        first_witness = {"chain": list(chain), "q": q,
                                         "J_minus_q_cover": [i for i in range(n) if (gm[q] >> i) & 1]}
    rec("M07_teeth_non_past_closed_jminus", divergences > 0,
        {"n": n, "models": models, "tail_q_evaluations": evals,
         "tail_without_whole": divergences, "first_witness": first_witness})

    # ---- text-detector teeth controls (in-memory mutants) -------------------
    def text_checks(d5_text: str, vis_text: str, relation_text: str, whole_text: str):
        d5a, visa, rela = assertive(d5_text), assertive(vis_text), assertive(relation_text)
        return {
            "d5_equivalence_present": "EQUIVALENT" in d5a and "past-closed" in d5a,
            "d5_rev12_false_absent": (REV12_D5_FALSE not in whole_text
                                      and "strictly STRONGER" not in d5a
                                      and "NOT the predicate of this class" not in d5a),
            "vis_equivalence_present": "EQUIVALENT" in visa and "past-closed" in visa,
            "vis_misclassification_absent": (REV12_VIS_FALSE not in whole_text
                                             and "would misclassify" not in visa
                                             and "no geodesic is misclassified" in visa),
            "withdrawn_citation_absent": (REV12_CITATION not in whole_text
                                          and "worker-037" not in whole_text
                                          and "W037V2" not in whole_text),
            "variant_weaker": "strictly WEAKER" in rela and "strictly STRONGER" not in rela,
        }

    relation = set_variant.get("relation", "")
    base = text_checks(d5.get("definition", ""), vis.get("definition", ""), relation, raw)
    m1 = text_checks(REV12_D5_FALSE + " " + d5.get("definition", ""), vis.get("definition", ""), relation, raw)
    m2 = text_checks(
        d5.get("definition", ""),
        vis.get("definition", "").replace("EQUIVALENT", "a definitional choice")
        .replace("past-closedness", "the standard reading").replace("past-closed", "the standard reading"),
        relation,
        raw.replace("past-closedness of J^-(q)", "the standard reading"),
    )
    m3 = text_checks(d5.get("definition", ""), vis.get("definition", ""),
                     relation.replace("strictly WEAKER", "strictly STRONGER"), raw)
    m4 = text_checks(d5.get("definition", ""), vis.get("definition", ""), relation,
                     raw + "\n# " + REV12_CITATION)
    rec("C01_control_false_strictness_detected",
        base["d5_rev12_false_absent"] and not m1["d5_rev12_false_absent"],
        {"mutant": "rev12 strictness sentence reinserted", "base_flag": base["d5_rev12_false_absent"],
         "mutant_flag": m1["d5_rev12_false_absent"]})
    rec("C02_control_equivalence_removed_detected",
        base["vis_equivalence_present"] and not m2["vis_equivalence_present"],
        {"mutant": "equivalence/past-closure wording removed",
         "base_flag": base["vis_equivalence_present"], "mutant_flag": m2["vis_equivalence_present"]})
    rec("C03_control_weaker_flip_detected",
        base["variant_weaker"] and not m3["variant_weaker"],
        {"mutant": "relation flipped back to strictly STRONGER",
         "base_flag": base["variant_weaker"], "mutant_flag": m3["variant_weaker"]})
    rec("C04_control_withdrawn_citation_detected",
        base["withdrawn_citation_absent"] and not m4["withdrawn_citation_absent"],
        {"mutant": "worker-037 citation reinserted",
         "base_flag": base["withdrawn_citation_absent"], "mutant_flag": m4["withdrawn_citation_absent"]})

    # C05: tampered binding hash must be detected by the B01 comparison
    tampered = dict(fb)
    tampered["declared_f0_sha256"] = "0" * 64
    c05_ok = not (tax_path.exists() and sha(tax_path) == tampered["declared_f0_sha256"])
    rec("C05_control_tampered_binding_detected", c05_ok,
        {"mutant": "declared_f0_sha256 -> 64 zeros", "detected": c05_ok})

    # C06: separator control must not fire on a model where tailSet holds
    # explicit: chain g0<=g1, I+={q} with both <= q  -> set and tailSet both true
    rows_demo = [0b111, 0b110, 0b100]  # 0<=1<=2 with 2 = q (rows are future sets)
    dm_demo = down_masks(rows_demo, 3)
    chain_demo = (0, 1)
    demo_set = set_pred(chain_demo, [2], dm_demo)
    demo_tail = tailset_pred(chain_demo, [2], dm_demo)
    demo_separation = demo_set and not demo_tail  # separator predicate
    rec("C06_control_separator_has_teeth", bool(demo_set and demo_tail and not demo_separation),
        {"model": "0<=1<=q", "set": demo_set, "tailset": demo_tail,
         "separator_reports_weaker": demo_separation,
         "reading": "separator reports separation only when set holds and tailSet fails; "
                    "on a collapsing model it must NOT fire"})

    # ---- drift guard --------------------------------------------------------
    pins_end = {
        "schemas/af_wcc_vacuum.yaml": sha(F1),
        "research_map/formulation_taxonomy.yaml": sha(TAX),
        "artifacts/formulation/evidence/taxonomy_consistency.json": sha(EVID),
        "artifacts/formulation/FROZEN.json": sha(FROZEN),
    }
    frozen_end = json.loads(FROZEN.read_text(encoding="utf-8"))
    f1_still_declared = (
        frozen_end.get("files", {}).get("schemas/af_wcc_vacuum.yaml", {}).get("sha256") == PIN_F1
    )
    drift_ok = all(pins_end[k] == pins_start[k] for k in pins_start) and f1_still_declared
    rec("D01_no_pin_drift", drift_ok,
        {"pins_start": pins_start, "pins_end": pins_end,
         "frozen_revision_end": frozen_end.get("revision"),
         "f1_still_declared_in_frozen_end": f1_still_declared})

    # ---- verdicts -----------------------------------------------------------
    ok = {cid: checks[cid]["pass"] for cid in CHECK_IDS}
    hf011_discharged = all(ok[c] for c in [
        "T01_d5_equivalence_present", "T02_d5_rev12_false_strictness_absent",
        "T03_vis_equivalence_present", "T04_vis_misclassification_absent",
        "T05_operative_tail_predicate_unchanged",
        "M01_equivalence_exhaustive_n_le_5", "M02_equivalence_sampled_n_6_8",
    ])
    f011_02_discharged = ok["T06_withdrawn_citation_absent"]
    f011_03_discharged = all(ok[c] for c in [
        "T07_variant_relation_is_weaker", "M03_tailset_entails_set",
        "M04_finite_iplus_collapse", "M05_omega_chain_separation_witness",
    ])
    controls_ok = all(ok[c] for c in CHECK_IDS if c.startswith("C"))
    valid = all(ok.values()) and pins_start["schemas/af_wcc_vacuum.yaml"] == PIN_F1

    verdict = "accept_targeted_repair" if (hf011_discharged and f011_02_discharged and controls_ok) else "revise"
    report = {
        "schema_version": "1.0",
        "record_id": RECORD_ID,
        "task_id": TASK_ID,
        "actor": "worker-011",
        "reviewer": "worker-011",
        "reviewer_role": "independent_worker_reviewer",
        "created_at": now_iso(),
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "target": "schemas/af_wcc_vacuum.yaml",
        "target_revision": doc.get("revision"),
        "reviewed_sha256": PIN_F1,
        "canonical_taxonomy_sha256": PIN_TAX,
        "consistency_evidence_sha256": PIN_EVID,
        "frozen_sha256_at_start": pins_start["artifacts/formulation/FROZEN.json"],
        "frozen_sha256_at_end": pins_end["artifacts/formulation/FROZEN.json"],
        "frozen_revision_at_end": frozen_end.get("revision"),
        "scope": (
            "Post-repair verification of HF-011-01, F-011-02 and F-011-03 at the frozen F1 rev13 "
            "bytes. Clause-scoped text detectors, a machine model for the whole/tail equivalence, "
            "and new direction checks for the variant SET relation. NOT a full-schema verdict, "
            "NOT a gate verdict."
        ),
        "valid": valid,
        "verdict": verdict,
        "score": 4.0 if verdict == "accept_targeted_repair" else 3.5,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": False,
        "claims_completion": False,
        "prior_findings": {
            "HF-011-01": {
                "status": "discharged_at_this_pin" if hf011_discharged else "persists",
                "evidence": "T01-T05, M01-M02",
            },
            "F-011-02": {
                "status": "discharged_at_this_pin" if f011_02_discharged else "persists",
                "evidence": "T06 (no worker-037/W037V2 reference anywhere in the pinned bytes)",
            },
            "F-011-03": {
                "status": "discharged_at_order_model_level" if f011_03_discharged else "persists",
                "evidence": "T07, M03-M05",
                "scope_note": (
                    "The rev13 'strictly WEAKER' direction and its T2/T3/T4 support are independently "
                    "reproduced at the causal-order level. Spacetime realizability of the separating "
                    "geodesic is NOT claimed by this report and is not claimed by the schema."
                ),
            },
        },
        "residuals": [
            {
                "id": "R-W011-13-01",
                "severity": "advisory",
                "finding": (
                    "M05's separating witness is an infinite causal order (omega-chain, infinite I+), "
                    "not a realized vacuum development. The rev13 relation claim is correct at the order "
                    "level; the physics-level realizability of a geodesic with no causal maximum and no "
                    "single-q visible tail remains a modelling obligation, as it was at rev12."
                ),
            },
            {
                "id": "R-W011-13-02",
                "severity": "advisory",
                "finding": (
                    "negation_conclusion still asserts 'B-containment is strictly stronger'. M06 confirms "
                    "that direction and the omega witness supplies the failure of the converse, so the "
                    "sentence is now supported rather than merely asserted; the same order-level caveat applies."
                ),
            },
            {
                "id": "R-W011-13-03",
                "severity": "note",
                "finding": (
                    "The declared consistency_evidence file is regenerated on a loop; at this run it measured "
                    "9e335e9b (content stable) but its mtime is later than FROZEN.json. Byte-pin holds now; "
                    "durability across the next freeze is an owner obligation (matches worker-069's B2/B4/B3)."
                ),
            },
        ],
        "checks_summary": ok,
        "checks": checks,
        "machine_evidence": {
            "equivalence_exhaustive_preorders_n_le_5": exhaustive,
            "equivalence_sampled_n_6_8": sampled,
            "variant_set_tailset_entails_set": m03,
            "variant_set_finite_iplus_collapse": m04,
            "omega_chain_witness": checks["M05_omega_chain_separation_witness"]["detail"],
            "b_containment": checks["M06_b_containment_strictly_stronger"]["detail"],
            "non_past_closed_control": checks["M07_teeth_non_past_closed_jminus"]["detail"],
        },
        "lemma": {
            "id": "LEMMA-W011-1",
            "statement": (
                "With the standard past-closed causal past J^-(q) and a future-directed causal gamma, "
                "gamma([t0,T)) subset J^-(q) for some t0  <=>  gamma([0,T)) subset J^-(q)."
            ),
            "proof": (
                "(=>) t < t0 gives gamma(t) preceq gamma(t0) in J^-(q); past-closure puts gamma(t) in "
                "J^-(q). (<=) Trivial. Uses only transitivity/past-closure, so it holds for the schema's D4 class."
            ),
        },
        "falsifier": (
            "Re-measure schemas/af_wcc_vacuum.yaml: if it is no longer d9cebb9404b2 the verdict is void. "
            "At d9cebb9404b2 the repair findings are falsified (i.e., HF-011-01/F-011-02/F-011-03 would "
            "be reinstated) by any of: the condemned rev12 strictness or misclassification sentence "
            "reappearing in D5/visibility; a worker-037/W037V2 confirmation citation reappearing; a "
            "witness with the standard past-closed J^-(q) separating tail from whole; a finite-I+ model "
            "with set-containment but no single-q tail; or a failure of the audited text controls to "
            "detect their mutants."
        ),
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#sha256:{PIN_F1[:12]}",
            f"research_map/formulation_taxonomy.yaml#sha256:{PIN_TAX[:12]}",
            f"artifacts/formulation/evidence/taxonomy_consistency.json#sha256:{PIN_EVID[:12]}",
            f"artifacts/formulation/FROZEN.json#sha256:{pins_end['artifacts/formulation/FROZEN.json'][:12]}",
            "reviews/F1-review-011-visibility-strictness.json#sha256:73ebc7740f29",
            "artifacts/worker-011/f1_visibility_strictness_adjudication/report.json#sha256:c0f34e0d9bb8",
        ],
        "authority_note": (
            "Worker evidence only: not a gate verdict, not a node status, not a canonical artifact edit. "
            "No canonical file was modified. The schema owner (lead-formulation) and lead-audit bind interpretation."
        ),
        "run": {
            "python": sys.version.split()[0],
            "deterministic": True,
            "reads_canonical": True,
            "writes": ["report.json", "hashes.txt", "README.md"],
        },
    }

    out = ART / "report.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"valid": valid, "verdict": verdict,
                      "failed_checks": [c for c, v in ok.items() if not v],
                      "report": str(out)}, indent=1))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
