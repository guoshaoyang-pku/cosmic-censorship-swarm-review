# extracted verbatim from artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff
# source diff sha256: 0247a5c93acc0e015d09cf4dcec8c643696d4328b748c871857fb82cc9b4669a
# executed with a signature-compatible audit_lib.Violation shim; do not edit by hand

def check_ledger_class_disjunction(records: list[dict], classes: dict[str, dict]) -> list[Violation]:
    """HF-02 (rubric literal): a single class_ids list carrying >=2 frozen classes is a
    disjunction, independent of whether the singular claim path is used. Ledger coverage
    should use `informs_classes`; `class_ids` is an assertion surface."""
    out: list[Violation] = []
    frozen = set(classes)
    for r in records:
        cids = {c for c in (r.get("class_ids") or []) if c in frozen}
        if len(cids) >= 2:
            where = r.get("theorem_id") or r.get("claim_id") or r.get("event_id") or "<record>"
            out.append(Violation("HF-02", "critical", f"ledger/{where}",
                                 f"disjunction of class_ids {sorted(cids)} in one record: "
                                 "classes must never be disjoined", {"class_ids": sorted(cids)}))
    return out
