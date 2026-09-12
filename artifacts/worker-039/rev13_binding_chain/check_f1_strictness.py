#!/usr/bin/env python3
"""Check J — the F1 visibility strictness correction is internally consistent.

worker-039, W039-REV13-BINDCHAIN-01. REC-12 item (3) authorizes exactly one kind of change at
the F1 visibility lines: "assertion direction only" (the card cites worker-076's finding). The
pre-repair text called the whole-curve reading "strictly STRONGER"; the repaired text calls the
variant SET relation "strictly WEAKER". Those are opposite claims, so the correction has to be
checked against the class's own frozen predicate rather than accepted as wording.

This tool does not re-derive the order theory (that is worker-076's W076-GFORM-STRICTNESS-
RECONCILE and worker-039's own S10 sweep). It checks that the *repaired F1 document* is
internally consistent with the direction it now asserts:

  F1.A  visibility.definition states the single-q TAIL predicate;
        visibility.negation_conclusion states the matching tail negation.
  F1.B  the relation "strictly WEAKER" is asserted for variant SET / the set-based reading, and
        no field still asserts the "strictly STRONGER" direction for that relation.
  F1.C  the witness attached to the corrected direction is recorded (test IDs and/or an
        explicit equivalence statement), so the direction is falsifiable from the document.
  F1.D  the F1 conclusion block is unchanged in kind: statement_formal still quantifies over a
        comeager set of data and still names the same conclusion_type
        (weak_cosmic_censorship) — no conclusion inflation.
  F1.E  the class id and node id are unchanged.

Exit 0 iff all sub-checks pass at the measured bytes; exit 1 otherwise. Read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
F1 = "schemas/af_wcc_vacuum.yaml"
CLASS_ID = "AF-WCC-VAC-GEN"
CONCLUSION_TYPE = "weak_cosmic_censorship"


def rec(cid, ok, detail, **extra):
    d = {"check": cid, "status": "PASS" if ok else "FAIL", "detail": detail}
    d.update(extra)
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    p = ROOT / F1
    raw = p.read_bytes()
    doc = yaml.safe_load(raw.decode("utf-8"))
    checks = []

    vis = doc.get("visibility") or {}
    definition = str(vis.get("definition") or "")
    negation = str(vis.get("negation_conclusion") or "")

    # F1.A — the operative predicate is the single-q tail predicate
    tail_ok = ("TAIL" in definition or "tail" in definition) and "J^-(q)" in definition
    single_q = "single q" in definition or "there exists q" in definition or "exists q" in definition
    neg_ok = "tail" in negation.lower() and "J^-(q)" in negation
    checks.append(rec("F1.A.tail_predicate", tail_ok and single_q and neg_ok,
                      f"definition tail={'TAIL' in definition or 'tail' in definition} "
                      f"single_q={single_q} J^-(q)={('J^-(q)' in definition)} "
                      f"negation_tail={'tail' in negation.lower()}"))

    # F1.B — the corrected direction is asserted and the old direction is gone for that relation
    variants = doc.get("class_identity_variants") or []
    set_variant = None
    for v in variants:
        if isinstance(v, dict) and ("set" in str(v.get("kind", "")).lower() or
                                    "set_based" in str(v.get("kind", "")).lower()):
            set_variant = v
            break
    if set_variant is None:
        checks.append(rec("F1.B.set_variant_present", False, "no set-based variant block in F1"))
        weaker = stronger = False
    else:
        relation = str(set_variant.get("relation") or "")
        # revision notes legitimately quote the superseded wording inside [...] brackets; the
        # operative claim is the text outside those brackets.
        operative = re.sub(r"\[[^\]]*\]", " ", relation)
        weaker = "WEAKER" in operative.upper()
        stronger = "STRONGER" in operative.upper()
        # the pre-repair sentence in visibility.definition also carried the claim
        def_stronger = "STRONGER" in definition.upper()
        quoted_old = bool(re.search(r"\[\s*rev\d+:[^\]]*STRONGER[^\]]*\]", relation))
        checks.append(rec("F1.B.direction_corrected", weaker and not stronger and not def_stronger,
                          f"operative relation says WEAKER={weaker} STRONGER={stronger} "
                          f"definition says STRONGER={def_stronger} old_wording_only_in_revision_note={quoted_old}",
                          relation_operative=operative.strip()[:220]))

    # F1.C — the correction carries its falsifier/witness
    witness_tokens = []
    if set_variant is not None:
        blob = json.dumps(set_variant)
        witness_tokens = re.findall(r"(?:W076|T[2-4]|F1-[A-Z]+-\d+|S10)", blob)
    fals = str((set_variant or {}).get("falsifier") or "")
    checks.append(rec("F1.C.correction_witnessed", bool(witness_tokens) and bool(fals),
                      f"witness tokens={sorted(set(witness_tokens))} falsifier_present={bool(fals)}",
                      falsifier=fals[:220]))

    # F1.D — no conclusion inflation
    concl = doc.get("conclusion") or {}
    sf = str(concl.get("statement_formal") or "")
    ct = concl.get("conclusion_type")
    comeager = ("comeager" in sf) and ("forall" in sf or "for all" in sf)
    checks.append(rec("F1.D.conclusion_shape", ct == CONCLUSION_TYPE and comeager,
                      f"conclusion_type={ct!r} formal_has_comeager={comeager}"))

    # F1.E — class / node identity unchanged
    checks.append(rec("F1.E.identity", doc.get("class_id") == CLASS_ID and doc.get("node_id") == "F1",
                      f"class_id={doc.get('class_id')!r} node_id={doc.get('node_id')!r} "
                      f"revision={doc.get('revision')!r}"))

    verdict = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    report = {
        "check_id": "J",
        "task_id": "W039-REV13-BINDCHAIN-01",
        "target": F1,
        "target_sha256": hashlib.sha256(raw).hexdigest(),
        "revision": doc.get("revision"),
        "verdict": verdict,
        "checks": checks,
        "note": ("Direction-only correction: the repaired text asserts that variant SET is strictly "
                 "WEAKER than the single-q tail predicate, which is the direction consistent with the "
                 "tail => set implication; the pre-repair 'strictly STRONGER' claim is absent from the "
                 "amended fields. This tool checks document-internal consistency, not the order theory "
                 "itself (worker-076 W076-GFORM-STRICTNESS-RECONCILE and worker-039 S10 own that)."),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        outp = Path(args.out)
        if not outp.is_absolute():
            outp = ROOT / outp
        outp.write_text(text + "\n")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
