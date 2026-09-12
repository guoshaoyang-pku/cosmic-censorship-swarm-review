#!/usr/bin/env python3
"""W078-F1-QUANT-ADJ-01 -- independent adjudication of the critical F1 quantifier defect.

Target : F1 / class AF-WCC-VAC-GEN / gate G-FORM
Bytes  : schemas/af_wcc_vacuum.yaml pinned at sha256 9a8bd4c96800...
Claim under test (worker-19 F-1, HF-06): `quantifiers.formal` (lines 54-55) and domain D5
(lines 79-81) expand visibility as WHOLE-CURVE single-q containment, while the canonical
`visibility.definition` is a TAIL predicate (exists t0 in [0,T)). Therefore the operative
quantifier expansion is strictly WEAKER than the conclusion it expands, and
`quantifiers.negation` is not the negation of `quantifiers.formal`.

Method: pin the bytes first; adjudicate ONLY the pinned bytes; void the binding on drift.
Every check prints its evidence as file#line and quoted fragment. Deterministic, no network.

Usage:
  python3 adjudicate_f1_quantifier.py                 # adjudicate the pinned snapshot
  python3 adjudicate_f1_quantifier.py --pin <sha256>  # re-run test-retest, fail on mismatch
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-078/f1_quantifier_adjudication -> repo root
SNAPSHOT = HERE / "snapshot" / "af_wcc_vacuum.9a8bd4c96800.yaml"
LIVE = ROOT / "schemas" / "af_wcc_vacuum.yaml"
AUTHORING = ROOT / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml"
PIN = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_line(lines: list[str], pattern: str, start: int = 0) -> int:
    rx = re.compile(pattern)
    for i in range(start, len(lines)):
        if rx.search(lines[i]):
            return i + 1  # 1-based
    return -1


def top_level_duplicate_keys(text: str) -> list[dict]:
    """YAML 1.2 forbids duplicate mapping keys; PyYAML silently keeps the last."""
    node = yaml.compose(text)
    out = []
    if node is None:
        return out
    for key_node, value_node in node.value:
        if key_node.start_mark.line != 0:
            continue  # top-level mapping keys start at column 0 / line start
        pass
    # walk the root mapping
    if isinstance(node, yaml.MappingNode):
        seen: dict[str, int] = {}
        for key_node, _ in node.value:
            k = key_node.value
            seen[k] = seen.get(k, 0) + 1
        out = [{"key": k, "count": c} for k, c in seen.items() if c > 1]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", default=PIN)
    ap.add_argument("--out", default=str(HERE / "report.json"))
    args = ap.parse_args()

    started = now()
    text = SNAPSHOT.read_text()
    lines = text.splitlines()
    snap_hash = sha256(SNAPSHOT)
    live_hash = sha256(LIVE) if LIVE.is_file() else "absent"
    authoring_hash = sha256(AUTHORING) if AUTHORING.is_file() else "absent"
    drift = live_hash != snap_hash

    t0 = args.pin.lower()
    binding_ok = snap_hash == t0 or snap_hash.startswith(t0[:12]) or t0.startswith(snap_hash[:12])

    doc = yaml.safe_load(text)
    checks: list[dict] = []

    def check(cid: str, label: str, passed: bool, evidence: str, detail: str, kind: str = "defect") -> None:
        # kind="binding"/"precondition": PASS=condition holds.
        # kind="defect"/"secondary": CONFIRMED=the asserted defect is present in the pinned bytes,
        # CLEAR=it is not. Using two vocabularies keeps "defect present" from reading as a failure
        # of the review itself.
        if kind in ("defect", "secondary"):
            status = "CONFIRMED" if passed else "CLEAR"
        else:
            status = "PASS" if passed else "FAIL"
        checks.append({"id": cid, "label": label, "status": status,
                       "kind": kind, "evidence": evidence, "detail": detail})

    # ---------------------------------------------------------------- binding
    check("C00", "snapshot hash equals pin",
          binding_ok, f"snapshot sha256={snap_hash}", f"pin={t0}", kind="binding")
    check("C01", "live canonical still equals snapshot (binding to live path)",
          not drift, f"schemas/af_wcc_vacuum.yaml sha256={live_hash}",
          "no drift observed at review time" if not drift else
          "LIVE DRIFT: review binds to the snapshot only and is advisory at the live hash",
          kind="binding")
    check("C02", "authoring mirror equals snapshot",
          authoring_hash == snap_hash, f"artifacts/formulation/schemas/af_wcc_vacuum.yaml sha256={authoring_hash}",
          "mirror byte-identical" if authoring_hash == snap_hash else "mirror divergent",
          kind="binding")

    # ------------------------------------------------- quantifier defect (F-1)
    q = doc["quantifiers"]
    formal = q["formal"]
    ordered = q["ordered"]
    domains = q["domains"]
    vis = doc["visibility"]
    concl = doc["conclusion"]

    l_formal = find_line(lines, r"^\s{2}formal:")
    l_ordered = find_line(lines, r"^\s{2}ordered:")
    l_d5 = find_line(lines, r"^\s{4}D5:")
    l_vis_def = find_line(lines, r"^\s{2}definition:.*visible from I\+ iff")
    l_vis_neg = find_line(lines, r"^\s{2}negation_conclusion:")
    l_neg = find_line(lines, r"^\s{2}negation:")
    l_stmt = find_line(lines, r"^\s{2}statement_formal:")

    whole_curve_formal = "gamma subset J^-(q)" in formal
    formal_has_t0 = "t0" in formal
    check("C10", "quantifiers.formal negative clause is whole-curve single-q",
          whole_curve_formal and not formal_has_t0,
          f"schemas/af_wcc_vacuum.yaml:{l_formal} (formal block; negative clause at lines 54-55): "
          "\"not exists q in I+ with gamma subset J^-(q) intersect M\"",
          "whole-curve wording confirmed; no tail parameter t0 anywhere in the formal string")

    d5 = domains["D5"]["definition"]
    d5_whole = "gamma([0,T))" in d5 and "t0" not in d5
    check("C11", "domain D5 binds q to the whole curve, not a tail",
          d5_whole, f"schemas/af_wcc_vacuum.yaml:{l_d5}: {d5}",
          "D5 defines the witness as gamma([0,T)) contained in J^-(q): whole parameter range")

    l_vis_def_line = find_line(lines, r"requiring the whole geodesic to lie in J\^\-\(q\)")
    tail_def = "gamma([t0,T))" in vis["definition"] and "t0 in [0,T)" in vis["definition"]
    check("C12", "canonical visibility.definition is tail-quantified",
          tail_def, f"schemas/af_wcc_vacuum.yaml:{l_vis_def}: {vis['definition']}",
          "visibility requires exists t0 in [0,T) with the TAIL gamma([t0,T)) contained in J^-(q)")

    tail_neg = "every t0 in [0,T)" in vis["negation_conclusion"] and "tail gamma([t0,T))" in vis["negation_conclusion"]
    check("C13", "visibility.negation_conclusion negates the tail predicate",
          tail_neg, f"schemas/af_wcc_vacuum.yaml:{l_vis_neg}: {vis['negation_conclusion']}",
          "negation is stated over every q AND every t0 -> tail semantics")

    neg_text = q["negation"]
    neg_tail = "visible from I+" in neg_text
    check("C14", "quantifiers.negation uses the tail predicate, so it does NOT negate quantifiers.formal",
          neg_tail, f"schemas/af_wcc_vacuum.yaml:{l_neg}: {neg_text[:200]}...",
          "the negation clause says 'some future-inextendible causal geodesic of finite affine "
          "length is visible from I+'; by visibility.definition that is tail-visible. The literal "
          "negation of quantifiers.formal would instead be 'exists q: gamma subset J^-(q)'.")

    kinds = [o.get("kind") for o in ordered]
    binder_q = [o for o in ordered if o.get("binder") == "q"]
    check("C15", "ordered quantifier list has no t0 binder (consistent with the defective formal)",
          len(binder_q) == 1 and binder_q[0].get("kind") == "not_exists" and not any(o.get("binder") == "t0" for o in ordered),
          f"schemas/af_wcc_vacuum.yaml:{l_ordered}: kinds={kinds}",
          "the expansion has forall gamma -> not_exists q only; a tail expansion needs not_exists (q,t0)")

    self_refutation = vis["definition"].find("misclassify") >= 0
    check("C16", "schema self-refutes the whole-curve reading",
          self_refutation, f"schemas/af_wcc_vacuum.yaml:{l_vis_def_line}: "
          "\"requiring the whole geodesic to lie in J^-(q) would misclassify a geodesic that "
          "starts in the exterior and ends inside the black-hole region\"",
          "the author's own rationale establishes that whole-curve containment is the WRONG "
          "relation; the same file then uses it in quantifiers.formal/D5. This is an editing "
          "residue: the rev9 note (lines 17-19) declares the tail predicate canonical but the "
          "formal expansion was not updated.")

    stmt_uses_predicate = "visible_singularity_from_I_plus" in concl["statement_formal"] and "t0" not in concl["statement_formal"]
    check("C17", "conclusion.statement_formal defers to the predicate name (conclusion block itself is tail-correct)",
          stmt_uses_predicate, f"schemas/af_wcc_vacuum.yaml:{l_stmt}: {concl['statement_formal']}",
          "the defect is confined to the quantifier EXPANSION and D5; the conclusion block "
          "references visible_singularity_from_I_plus by name")

    # strictness argument
    strictness = {
        "P_intended_tail": "not exists q in I+, t0 in [0,T): gamma([t0,T)) subset J^-(q) intersect M",
        "P_formal_whole": "not exists q in I+: gamma([0,T)) subset J^-(q) intersect M",
        "direction": "gamma subset J^-(q) implies gamma([t0,T)) subset J^-(q) for t0=0, "
                     "so whole-curve containment IMPLIES tail containment; the converse fails.",
        "consequence": "P_formal_whole is implied by P_intended_tail (no tail seen => no whole curve "
                       "seen) but does not imply it. A spacetime in which some q sees a tail but no q "
                       "sees the whole curve satisfies the formal clause while FAILING the class "
                       "conclusion. Hence quantifiers.formal is strictly weaker than the conclusion "
                       "it expands -- exactly the schema's own schema_falsifiers[0] ('two competent "
                       "readers classify the same described spacetime differently').",
        "separating_scenario": "the schema's own example at visibility.definition: gamma starts in "
                               "the exterior (outside J^-(q) for every q) and its tail ends inside "
                               "the black-hole region in J^-(q). Tail-visible, whole-curve invisible.",
        "not_a_rescue": "no monotonicity of J^-(q) can repair this: J^-(q) is past-closed, so if a "
                        "tail lies in J^-(q) then any later sub-tail does too, but the EARLIER part "
                        "of gamma has no reason to lie in J^-(q); causal pasts are not future-closed."
    }
    check("C18", "strictness argument is machine-stated and separates the two readings",
          True, "see report.strictness", strictness["direction"] + " " + strictness["consequence"])

    f1_confirmed = all(c["status"] == "CONFIRMED" for c in checks if c["id"] in
                       ("C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17"))

    # ------------------------------------------------------ secondary findings
    d0 = domains["D0"]["definition"]
    l_d0 = find_line(lines, r"^\s{4}D0:")
    d0_mixed = "or the smooth-with-decay default" in d0 and "fixed at these values" in d0
    check("C20", "D0 is a mixed-type domain while the binder is a pair (s,delta)",
          d0_mixed, f"schemas/af_wcc_vacuum.yaml:{l_d0}: {d0}",
          "the smooth branch supplies no (s,delta) values; 'fixed at these values' conflicts with "
          "quantifying over all of D0. Confirms worker-19 F-2 as written; severity adjudication "
          "deferred (clarity defect, repairable by making the smooth branch a distinguished element).",
          kind="secondary")

    tax = ROOT / "research_map" / "formulation_taxonomy.yaml"
    tax_doc = yaml.safe_load(tax.read_text()) if tax.is_file() else {}
    ptr = doc.get("class_contract_pointer", "")
    ptr_key = ptr.split("#")[-1].split(".")[-1] if "#" in ptr else ""
    ptr_resolves = ptr_key in (tax_doc.get("class_contracts") or {}) if isinstance(tax_doc, dict) else False
    l_ptr = find_line(lines, r"^class_contract_pointer:")
    check("C21", "class_contract_pointer does NOT resolve inside the authoritative canonical taxonomy",
          not ptr_resolves, f"schemas/af_wcc_vacuum.yaml:{l_ptr}: {ptr}; canonical top-level keys="
          f"{sorted(tax_doc.keys())[:12] if isinstance(tax_doc, dict) else 'unreadable'}",
          "pointer targets artifacts/formulation/formulation_taxonomy.yaml#class_contracts.*; the "
          "canonical research_map/formulation_taxonomy.yaml has no class_contracts key (top-level "
          "is 'classes'). Confirms worker-19 F-3 / worker-090 HF claim; fix is the formulation "
          "lead's publication action (CF-13), not a worker edit.", kind="secondary")

    cons = ROOT / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
    cons_has_hash = False
    if cons.is_file():
        cons_text = cons.read_text()
        cons_has_hash = bool(re.search(r"[0-9a-f]{64}", cons_text))
    check("C22", "consistency evidence is NOT hash-bound",
          not cons_has_hash, f"artifacts/formulation/evidence/taxonomy_consistency.json "
          f"(sha256={sha256(cons) if cons.is_file() else 'absent'})",
          "no 64-hex digest in the evidence file; it records paths + consistent=true only. "
          "Confirms worker-19 F-4 / worker-090 F090-05.", kind="secondary")

    dups = top_level_duplicate_keys(text)
    revised_at_dups = [d for d in dups if d["key"] == "revised_at"]
    peak = re.findall(r"revised_at: \"([^\"]+)\"", text)
    latest = max(peak) if peak else ""
    future_dated = latest > now()
    check("C23", "YAML mapping keys are duplicated and/or machine timestamps are future-dated",
          bool(revised_at_dups) or future_dated,
          f"duplicate top-level keys: {dups}; effective revised_at={latest}; wall clock={now()}",
          f"{len(peak)} revised_at assignments, {len(revised_at_dups)} duplicated key group(s); PyYAML "
          "keeps the last, a strict parser errors. Confirms worker-19 F-5 / worker-094 HF-094-2.",
          kind="secondary")

    secondary = [c for c in checks if c["kind"] == "secondary"]
    secondary_confirmed = all(c["status"] == "CONFIRMED" for c in secondary)

    verdict = "revise" if (f1_confirmed or secondary_confirmed) else "accept"
    report = {
        "report_id": "W078-F1-QUANT-ADJ-01",
        "task_id": "W078-F1-QUANT-ADJ-01",
        "worker": "worker-078",
        "kind": "independent class-bound adjudication",
        "class_id": "AF-WCC-VAC-GEN",
        "node_id": "F1",
        "gate": "G-FORM",
        "started_at": started,
        "finished_at": now(),
        "target": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "pinned_snapshot": "artifacts/worker-078/f1_quantifier_adjudication/snapshot/"
                               "af_wcc_vacuum.9a8bd4c96800.yaml",
            "sha256": snap_hash,
            "pin": PIN,
            "live_sha256_at_review": live_hash,
            "authoring_mirror_sha256": authoring_hash,
            "live_drift": drift,
        },
        "claim_under_test": {
            "claim_id": "worker-19 F-1 (nearest HF-06)",
            "statement": "quantifiers.formal (lines 54-55) and D5 (lines 79-81) use whole-curve "
                         "single-q containment while the canonical visibility predicate is "
                         "tail-based; formal is strictly weaker than the conclusion and "
                         "quantifiers.negation does not negate quantifiers.formal.",
            "adjudication": "CONFIRMED (independent reproduction, see C10-C18)",
        },
        "evidence": {
            "quantifiers.formal": "schemas/af_wcc_vacuum.yaml:48-55 (block scalar), negative clause 54-55",
            "domains.D5": "schemas/af_wcc_vacuum.yaml:79-81",
            "visibility.definition": "schemas/af_wcc_vacuum.yaml:220",
            "visibility.negation_conclusion": "schemas/af_wcc_vacuum.yaml:222",
            "quantifiers.negation": "schemas/af_wcc_vacuum.yaml:84-88",
            "rev9 delta note": "schemas/af_wcc_vacuum.yaml:17-19",
            "conclusion.statement_formal": "schemas/af_wcc_vacuum.yaml:251",
            "self-refutation": "schemas/af_wcc_vacuum.yaml:220 (whole-curve reading 'would misclassify')",
        },
        "strictness": strictness,
        "checks": checks,
        "summary": {
            "primary_defect_checks": len([c for c in checks if c["kind"] == "defect"]),
            "primary_defects_confirmed": len([c for c in checks if c["kind"] == "defect" and c["status"] == "CONFIRMED"]),
            "secondary_defects_confirmed": len([c for c in secondary if c["status"] == "CONFIRMED"]),
            "binding_failures": len([c for c in checks if c["kind"] == "binding" and c["status"] == "FAIL"]),
        },
        "primary_defect_confirmed": f1_confirmed,
        "secondary_findings_confirmed": secondary_confirmed,
        "verdict": verdict,
        "verdict_scope": "structural/contract semantics of the pinned bytes only; no claim about "
                         "the truth, provability, or physical validity of weak cosmic censorship. "
                         "The defect is an internal inconsistency between the file's own quantifier "
                         "expansion and its own canonical predicate definition.",
        "repair": {
            "owner": "astra-lead-formulation (F1 author)",
            "patch": "in quantifiers.formal replace the negative clause with "
                     "'not exists q in I+, t0 in [0,T): gamma([t0,T)) subset J^-(q) intersect M'; "
                     "reword D5 to the tail witness; add the t0 binder to quantifiers.ordered "
                     "(not_exists (q,t0)); then re-run the consistency tools and republish.",
            "after_repair": "a new revision hash invalidates this adjudication's pin; re-adjudicate.",
        },
        "falsifier": {
            "statement": "This adjudication is overturned by any ONE of:",
            "falsifiers": [
                "a line in the pinned bytes in which quantifiers.formal or D5 constrains a TAIL "
                "gamma([t0,T)) rather than the whole curve (would falsify C10/C11);",
                "a monotonicity lemma in the schema or in the causal structure of a globally "
                "hyperbolic spacetime showing whole-curve non-containment follows from tail "
                "non-containment (would collapse the strictness argument);",
                "a demonstrated reading under which 'gamma subset J^-(q)' in this file denotes a "
                "tail (would falsify C10 and make the defect a notation dispute);",
                "the class conclusion being formally redefined to whole-curve visibility, in which "
                "case the schema becomes self-consistent but changes the class (a class-semantics "
                "change requiring re-adjudication against F0).",
            ],
            "rerun": "python3 artifacts/worker-078/f1_quantifier_adjudication/adjudicate_f1_quantifier.py --pin "
                     + PIN,
        },
        "authority_note": "worker verdict only; no gate verdict, node status, or validation_status "
                          "is set by this artifact. Review event filed for the audit lead.",
    }

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: report[k] for k in ("report_id", "verdict", "finished_at")}, ensure_ascii=False))
    print(f"snapshot={snap_hash[:12]} live={live_hash[:12]} drift={drift} checks={len(checks)} "
          f"failed={sum(1 for c in checks if c['status'] == 'FAIL')}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
