#!/usr/bin/env python3
"""Deterministic, read-only L0 conformance checks for review L0-review-18-rev3.

Target: ledger/theorems.jsonl at the hash measured at run time (review binds to the
measured sha256, never to the path alone). Checks are written against the frozen
criteria in evaluation_rubric.yaml (G-LIT, hard_failures HF-01..HF-14, literature
verifier) and re-run cleanly: python3 artifacts/worker18/l0_review/check_l0.py

Contract:
  * reads only; writes nothing except the JSON report path passed as argv[2]
  * every check reports PASS / FAIL / WARN / INFO plus the exact row ids it counted
  * the script re-hashes the ledger before and after the checks and fails C19 if it moved
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
LEDGER = os.path.join(ROOT, "ledger", "theorems.jsonl")
REGISTRY = os.path.join(ROOT, "artifacts", "literature", "registry.jsonl")
UNRESOLVED = os.path.join(ROOT, "artifacts", "literature", "unresolved.jsonl")
MANIFEST = os.path.join(ROOT, "artifacts", "literature", "MANIFEST.json")
ACCEPTANCE = os.path.join(ROOT, "artifacts", "literature", "L0_L1_ACCEPTANCE.md")
CITATION_AUDIT = os.path.join(ROOT, "ledger", "citation_audit.csv")

FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
# rubric lines 100-104: C0 class status is never `theorem`, never `open_conjecture`
C0_BANNED_CONCLUSION = {"theorem"}
# HF-04 quantity tokens (rates/exponents/codimensions/counts)
QUANTITY_RE = re.compile(
    r"(codimension|codim\b|exponent|scaling|power law|rate\b|"
    r"[0-9]\s*[+\-–]?\s*(?:dimensional|dim\b)|O\(|"
    r"\b(?:generically|generic)\b[^.]{0,40}\b(?:fraction|proportion|measure|dense|open)\b|"
    r"\b\d+(?:\.\d+)?\s*(?:%|percent)\b)",
    re.I,
)
SOURCE_KEYS = ["source_id", "title", "authors", "year", "venue", "doi", "arxiv_id", "url",
               "status", "verification"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jloads(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def text_of(rec):
    parts = []
    for key in ("label", "statement_exact", "assumptions", "scope_caveats", "regularity",
                "topology", "genericity", "does_not_imply"):
        val = rec.get(key)
        if isinstance(val, list):
            parts.extend(str(x) for x in val)
        elif val is not None:
            parts.append(str(val))
    return " ".join(parts)


def main(report_path=None):
    checks = []

    def add(cid, name, status, count, detail, rows=None, hf=None, criterion=None):
        entry = {"id": cid, "name": name, "status": status, "count": count,
                 "detail": detail, "rows": rows or []}
        if hf:
            entry["hard_failure"] = hf
        if criterion:
            entry["criterion"] = criterion
        checks.append(entry)

    ledger_hash_before = sha256(LEDGER)
    ledger_bytes = os.path.getsize(LEDGER)
    recs = jloads(LEDGER)
    reg = jloads(REGISTRY)
    unres = jloads(UNRESOLVED)
    manifest = json.load(open(MANIFEST, encoding="utf-8"))

    # C1 manifest hash bind for the L0/L1 canonical files
    declared = manifest.get("artifacts", {})
    for rel in ("ledger/theorems.jsonl", "ledger/citation_audit.csv",
                "artifacts/literature/registry.jsonl", "artifacts/literature/unresolved.jsonl"):
        measured = sha256(os.path.join(ROOT, rel))
        ok = declared.get(rel) == measured
        add("C1.%s" % rel.split("/")[-1], "manifest hash bind %s" % rel,
            "PASS" if ok else "FAIL", 0 if ok else 1,
            "declared %s measured %s" % (str(declared.get(rel))[:16], measured[:16]))

    # C2 structure
    ids = [r.get("theorem_id") for r in recs]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    allkeys = set()
    for r in recs:
        allkeys.update(r.keys())
    add("C2.structure", "ledger parses; ids unique; rows=%d" % len(recs),
        "PASS" if not dups else "FAIL", len(dups),
        "duplicate ids: %s; union of fields: %d" % (dups or "none", len(allkeys)),
        rows=dups)

    # C3 class ids frozen
    unknown = sorted({c for r in recs for c in (r.get("class_ids") or []) if c not in FROZEN})
    add("C3.class_ids_frozen", "every class_id is one of the 4 frozen ids",
        "PASS" if not unknown else "FAIL", len(unknown), "unknown: %s" % (unknown or "none"),
        rows=unknown, hf="HF-02", criterion="G-LIT crit 3 / frozen_classes")

    # C4 disjunction
    disj = [r["theorem_id"] for r in recs if len(r.get("class_ids") or []) > 1]
    add("C4.class_disjunction", "one class per record (rubric line 54: never disjoined)",
        "FAIL" if disj else "PASS", len(disj),
        "records carrying 2 frozen class ids: %s" % disj,
        rows=disj, hf="HF-02", criterion="frozen_classes note")

    # C5 no class binding at all
    nobind = [r["theorem_id"] for r in recs
              if not (r.get("class_ids") or r.get("informs_classes"))]
    add("C5.class_unbound", "records carry class_ids or informs_classes",
        "WARN" if nobind else "PASS", len(nobind),
        "records with neither: %s" % nobind[:25],
        rows=nobind, criterion="G-LIT crit 3")

    # C6 C0 status_risk: rubric lines 100-104 forbid conclusion_type=theorem for this class
    c0viol = [r["theorem_id"] for r in recs
              if "AF-SCC-C0-VAC-GEN" in (r.get("class_ids") or [])
              and r.get("conclusion_type") in C0_BANNED_CONCLUSION]
    add("C6.c0_status_risk", "no C0 record typed `theorem` (rubric status_risk)",
        "FAIL" if c0viol else "PASS", len(c0viol),
        "C0-bound records with conclusion_type=theorem: %s" % c0viol,
        rows=c0viol, hf="HF-02", criterion="evaluation_rubric.yaml:100-104")

    # C7 HF-14 self-certified acceptance
    selfcert = [r["theorem_id"] for r in recs
                if r.get("author_asserts_supports") is True
                and r.get("review_status") == "not_independently_reviewed"
                and not (r.get("artifact_refs") or r.get("artifact_sha256") or r.get("sha256"))]
    add("C7.self_certified", "no record asserts support with no reviewer verdict and no hash",
        "FAIL" if selfcert else "PASS", len(selfcert),
        "rows author_asserts_supports=true, review_status=not_independently_reviewed, "
        "no artifact hash field: %s" % selfcert,
        rows=selfcert, hf="HF-14", criterion="HF-14 detector; G-LIT")

    # C8 HF-01 literal detector on ledger records
    thm = [r["theorem_id"] for r in recs if r.get("conclusion_type") == "theorem"]
    thm_noref = [r["theorem_id"] for r in recs if r.get("conclusion_type") == "theorem"
                 and not (r.get("artifact_refs") or r.get("artifact_sha256"))]
    add("C8.theorem_no_artifact", "conclusion_type=theorem records carry artifact_refs/hash",
        "FAIL" if thm_noref else "PASS", len(thm_noref),
        "%d theorem-typed records, %d without any artifact_refs/hash field "
        "(the ledger schema has no such field for any record)"
        % (len(thm), len(thm_noref)),
        rows=thm_noref, hf="HF-01",
        criterion="HF-01 detector (claim-scope applicability contested; see review)")

    # C9 HF-04 quantity_check
    qrows = [r["theorem_id"] for r in recs
             if QUANTITY_RE.search(r.get("statement_exact", "") or "")
             and not r.get("quantity_check")]
    add("C9.quantity_check", "quantity-bearing statements carry quantity_check",
        "FAIL" if qrows else "PASS", len(qrows),
        "quantity-token statements with no quantity_check field: %s" % qrows,
        rows=qrows, hf="HF-04", criterion="G-LIT crit 4 / literature verifier")

    # C10 registry locator completeness
    no_loc = [r["source_id"] for r in reg
              if not (r.get("doi") or r.get("arxiv_id") or r.get("url"))]
    add("C10.locator", "every source has DOI | arXiv id | URL",
        "PASS" if not no_loc else "FAIL", len(no_loc),
        "sources without any locator: %s" % no_loc, rows=no_loc,
        criterion="G-LIT crit 1")

    # C11 structured per-source scope metadata
    scope_fields = [k for k in ("matter", "matter_model", "lambda", "cosmological_constant",
                                "dimension", "symmetry", "formulation", "resolution_status")
                    if reg and k in reg[0]]
    add("C11.source_scope_metadata",
        "per-source matter/Lambda/dimension/symmetry/formulation recorded as fields",
        "FAIL" if not scope_fields else "PASS", 0 if scope_fields else len(reg),
        "structured scope fields present in registry rows: %s (0 of %d rows carry them; "
        "scope exists only inside free-text notes/verification)"
        % (scope_fields or "none", len(reg)),
        rows=[], criterion="G-LIT crit 3 / literature verifier")

    # C12 citation_support computability
    from collections import Counter
    statuses = Counter(str(r.get("status")) for r in reg)
    weight_map = {"verified_primary": 1.0, "verified_secondary": 0.5, "partial": 0.25,
                  "unresolved": 0.0, "contradicted": -1.0}
    unweighted = {s: n for s, n in statuses.items() if s.replace("-", "_") not in weight_map}
    add("C12.citation_support", "every source status has a rubric citation_support weight",
        "FAIL" if unweighted else "PASS", sum(unweighted.values()),
        "registry statuses %s; rubric weights (evaluation_rubric.yaml:260-263) define only %s; "
        "unweighted statuses: %s" % (dict(statuses), sorted(weight_map), unweighted),
        rows=sorted(unweighted), criterion="G-LIT crit 2 / metrics.citation_support")

    # C13 unassessed / metadata-only sources cited by accepted rows
    unassessed = set(manifest.get("counts", {}).get("unassessed_sources", []))
    meta_only = {r["source_id"] for r in reg
                 if str(r.get("verification", {}).get("evidence_type")) == "metadata"
                 or str(r.get("status")) == "metadata-only"}
    anchors = set(manifest.get("counts", {}).get("accepted_with_metadata_anchors", []))
    add("C13.unassessed_sources", "no unassessed source is cited; accepted rows have abstract-level evidence",
        "WARN" if unassessed else "PASS", len(unassessed),
        "manifest unassessed_sources=%s; metadata-only evidence sources=%d; "
        "accepted_with_metadata_anchors rows=%s"
        % (sorted(unassessed), len(meta_only), sorted(anchors)),
        rows=sorted(unassessed), criterion="G-LIT crit 1-2")

    # C14 unresolved coverage
    row_unres = [r["theorem_id"] for r in recs if r.get("unresolved")]
    unres_ids = sorted({str(u.get("theorem_id")) for u in unres})
    add("C14.unresolved_coverage", "row-level unresolved[] items aggregated in unresolved.jsonl",
        "WARN" if len(unres_ids) < len(row_unres) else "PASS",
        max(0, len(row_unres) - len(unres_ids)),
        "ledger rows with non-empty unresolved[]: %d; unresolved.jsonl distinct theorem_ids: %d"
        % (len(row_unres), len(unres_ids)),
        rows=[t for t in row_unres if t not in set(unres_ids)][:20],
        criterion="G-LIT crit 5")

    # C15 acceptance doc overclaim
    acc_text = open(ACCEPTANCE, encoding="utf-8").read()
    claimed_none = "L0 gaps\n\n- none" in acc_text.replace("\r", "")
    add("C15.acceptance_doc", "L0_L1_ACCEPTANCE.md gap statement agrees with measured defects",
        "FAIL" if (claimed_none and (disj or selfcert or c0viol or qrows or unweighted)) else "PASS",
        1 if (claimed_none and (disj or selfcert or c0viol or qrows or unweighted)) else 0,
        "acceptance file claims 'L0 gaps: none' while C4=%d C6=%d C7=%d C9=%d C12=%d rows/statuses fail"
        % (len(disj), len(c0viol), len(selfcert), len(qrows), sum(unweighted.values())),
        rows=[], criterion="consistency of declared acceptance with artifact")

    # C16 class coverage
    cov = Counter(c for r in recs for c in (r.get("class_ids") or []))
    add("C16.class_coverage", "each frozen class has >=1 ledger record",
        "PASS" if all(cov.get(c) for c in FROZEN) else "FAIL",
        sum(1 for c in FROZEN if not cov.get(c)),
        "coverage %s (manifest declares 11/10/11/10 order-insensitive)"
        % {c: cov.get(c, 0) for c in FROZEN})

    # C17 source_id cross-reference
    reg_ids = {r["source_id"] for r in reg}
    dangling = sorted({s for r in recs for s in (r.get("source_ids") or []) if s not in reg_ids})
    add("C17.source_refs", "every ledger source_id resolves in the L1 registry",
        "PASS" if not dangling else "FAIL", len(dangling),
        "dangling source_ids: %s" % (dangling or "none"), rows=dangling,
        criterion="G-LIT crit 1")

    # C18 near-duplicate statements (HF-07, quick shingle check)
    def toks(t):
        return set(re.findall(r"[a-z0-9]+", (t or "").lower()))

    dup_pairs = []
    tks = {r["theorem_id"]: toks(r.get("statement_exact", "")) for r in recs}
    order = [r["theorem_id"] for r in recs]
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            ta, tb = tks[a], tks[b]
            if not ta or not tb:
                continue
            j = len(ta & tb) / max(1, len(ta | tb))
            if j >= 0.60:
                dup_pairs.append("%s~%s:%.2f" % (a, b, j))
    add("C18.duplication", "no statement pair with token Jaccard >= 0.60",
        "PASS" if not dup_pairs else "WARN", len(dup_pairs),
        "pairs: %s" % (dup_pairs[:10] or "none"), rows=dup_pairs[:10], hf="HF-07")

    # C19 hash stability across the run
    ledger_hash_after = sha256(LEDGER)
    add("C19.hash_stable", "ledger did not move during the checks",
        "PASS" if ledger_hash_after == ledger_hash_before else "FAIL",
        0 if ledger_hash_after == ledger_hash_before else 1,
        "before %s after %s" % (ledger_hash_before[:16], ledger_hash_after[:16]))

    summary = {
        "pass": sum(1 for c in checks if c["status"] == "PASS"),
        "fail": sum(1 for c in checks if c["status"] == "FAIL"),
        "warn": sum(1 for c in checks if c["status"] == "WARN"),
        "info": sum(1 for c in checks if c["status"] == "INFO"),
    }
    report = {
        "tool": "artifacts/worker18/l0_review/check_l0.py",
        "actor": "deepseek-flash-18",
        "target": "ledger/theorems.jsonl",
        "target_sha256": ledger_hash_before,
        "target_bytes": ledger_bytes,
        "generated_at": manifest.get("generated_at"),
        "checks": checks,
        "summary": summary,
        "frozen_classes": FROZEN,
    }
    if report_path:
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
    return report


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else None
    rep = main(out)
    print(json.dumps(rep["summary"]))
    for c in rep["checks"]:
        print("%-4s %-26s n=%-3s %s" % (c["status"], c["name"][:26], c["count"], c["detail"][:110]))
