#!/usr/bin/env python3
"""W005-L0-REV3-REVIEW-01 independent checker (read-only).

Independent review instrument for the literature node L0 at the rev-3 frozen pins:
  ledger/theorems.jsonl      sha256 a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28
  ledger/citation_audit.csv  sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9

It implements the G-LIT acceptance criteria as machine checks (locators resolvable, verification_status
honest, unresolved disclosed) plus independent cross-artifact invariants between the ledger, the
source registry (artifacts/literature/sources/batch-*.jsonl) and the citation audit.

Read-only on every canonical path.  Work only under artifacts/worker-005/l0_rev3_review/ and tmp/.

Usage:
  python3 check_l0_rev3.py                 # print summary table
  python3 check_l0_rev3.py --report        # also write report.json
  python3 check_l0_rev3.py --selftest      # run mutant selftest, write selftest.json

Authority: worker event only.  This instrument does not set gate verdicts, node status, or
validation_status.  The review verdict it supports is advisory evidence for G-LIT/G-AUDIT.
"""
from __future__ import annotations

import argparse
import copy
import csv
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-005/l0_rev3_review -> repo root

LEDGER = ROOT / "ledger" / "theorems.jsonl"
AUDIT = ROOT / "ledger" / "citation_audit.csv"
SOURCES_GLOB = str(ROOT / "artifacts" / "literature" / "sources" / "batch-*.jsonl")
SPOTCHECK = HERE / "spotcheck_results.json"

LEDGER_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
AUDIT_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"

FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
VERIF_VOCAB = {"unverified", "abstract-read", "full-text", "page-checked"}
CONTENT_VOCAB = {"verified", "provisional", "rejected"}
CONCLUSION_VOCAB = {
    "theorem", "open_problem", "stability_result", "counterexample",
    "conditional_theorem", "formal_model", "numerical_evidence",
}
ENTRY_VOCAB = {
    "theorem", "preprint_result", "definition", "stability_result", "conjecture",
    "numerical_evidence", "literature_status", "methodological_inference",
    "counterexample_candidate", "conditional_theorem", "review", "unresolved_candidate",
    "background",  # observed singleton (D-009); the artifact documents no entry_kind vocabulary
}
EVIDENCE_VOCAB = {"peer-reviewed", "accepted-in-press", "preprint", "numerical", "metadata-only", "unresolved"}
REQUIRED_LEDGER_KEYS = {
    "acceptance_authority", "assumptions", "author_asserts_supports", "class_ids",
    "conclusion_type", "content_status", "does_not_imply", "entry_kind", "evidence_level",
    "falsifiers", "genericity", "label", "ledger_tags", "next_action", "regularity",
    "review_status", "scope_caveats", "source_ids", "statement_exact", "theorem_id",
    "topology", "unresolved", "verification_status",
}
ABSTRACT_LEVEL = {"abstract", "full-text"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


QUERY_LOCATOR_RE = re.compile(r"(search_query=|/api/query|\?q=|/search\?)")


def load_jsonl_strict(path: Path):
    """Parse JSONL; reject duplicate object keys and non-object lines."""
    def no_dups(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                raise ValueError(f"duplicate key {k!r}")
            seen[k] = v
        return seen

    rows, errors = [], []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line, object_pairs_hook=no_dups)
        except Exception as exc:  # noqa: BLE001 - report, do not crash
            errors.append(f"{path.name}:{lineno}: {exc}")
            continue
        rows.append(obj)
    return rows, errors


def measure():
    ledger_rows, ledger_err = load_jsonl_strict(LEDGER)
    audit_map, audit_err = {}, []
    with open(AUDIT, newline="") as fh:
        for row in csv.DictReader(fh):
            cid = row.get("citation_id")
            if cid in audit_map:
                audit_err.append(f"citation_audit.csv: duplicate citation_id {cid}")
            audit_map[cid] = row
    src_map, src_err = {}, []
    for p in sorted(glob.glob(SOURCES_GLOB)):
        rows, errs = load_jsonl_strict(Path(p))
        src_err.extend(errs)
        for s in rows:
            sid = s.get("source_id")
            if sid in src_map:
                src_err.append(f"{Path(p).name}: duplicate source_id {sid}")
            src_map[sid] = s
    return {
        "ledger_rows": ledger_rows,
        "ledger_errors": ledger_err,
        "sources": src_map,
        "sources_errors": src_err,
        "audit": audit_map,
        "audit_errors": audit_err,
    }


def evaluate(data, pins):
    """Return list of check dicts.  Pure function over the supplied data."""
    rows = data["ledger_rows"]
    srcs = data["sources"]
    audit = data["audit"]
    checks = []
    findings = []

    def add(cid, title, ok, detail, hard=True):
        checks.append({"id": cid, "title": title, "status": "pass" if ok else "fail",
                       "hard": hard, "detail": detail})

    # ---------------- P1 pins and parse integrity ----------------
    detail = {
        "ledger_pin_expected": pins["ledger"],
        "ledger_pin_measured": pins["ledger_measured"],
        "audit_pin_expected": pins["audit"],
        "audit_pin_measured": pins["audit_measured"],
        "ledger_rows": len(rows),
        "audit_rows": len(audit),
        "source_records": len(srcs),
        "ledger_parse_errors": data["ledger_errors"],
        "source_parse_errors": data["sources_errors"],
        "audit_parse_errors": data["audit_errors"],
        "pins_stable": pins["stable"],
    }
    ok = (
        pins["ledger_measured"] == pins["ledger"]
        and pins["audit_measured"] == pins["audit"]
        and pins["stable"]
        and not data["ledger_errors"] and not data["sources_errors"] and not data["audit_errors"]
        and len(rows) == 62 and len(audit) == 97
    )
    add("L0-P1", "pins, parse integrity, row counts", ok, detail)

    # ---------------- P2 schema completeness ----------------
    dup_ids, missing = [], []
    seen_ids = set()
    for r in rows:
        tid = r.get("theorem_id")
        if tid in seen_ids:
            dup_ids.append(tid)
        seen_ids.add(tid)
        miss = sorted(REQUIRED_LEDGER_KEYS - set(r))
        if miss:
            missing.append({"theorem_id": tid, "missing": miss})
    bad_types = [
        {"theorem_id": r.get("theorem_id"), "field": k}
        for r in rows
        for k in ("statement_exact", "assumptions", "does_not_imply", "falsifiers", "scope_caveats")
        if not r.get(k)
    ]
    ok = not dup_ids and not missing and not bad_types
    add("L0-P2", "every row complete, ids unique, required fields non-empty", ok,
        {"duplicate_theorem_ids": dup_ids, "missing_keys": missing, "empty_required_fields": bad_types})

    # ---------------- P3 source resolution and locators ----------------
    dangling, locatorless, unused = [], [], []
    for r in rows:
        for sid in r.get("source_ids", []):
            if sid not in srcs:
                dangling.append({"theorem_id": r.get("theorem_id"), "source_id": sid})
    for sid, s in srcs.items():
        if not (s.get("doi") or s.get("arxiv_id") or s.get("url")):
            locatorless.append(sid)
    referenced = {sid for r in rows for sid in r.get("source_ids", [])}
    unused = sorted(set(srcs) - referenced)
    ok = not dangling and not locatorless
    add("L0-P3", "every cited source resolves and carries a locator", ok,
        {"dangling_source_ids": dangling, "locatorless_sources": locatorless,
         "registry_sources_not_cited_by_ledger": unused})

    # ---------------- P4 verification-status honesty ----------------
    unsupported, verified_on_metadata, derivation_mismatch = [], [], []
    for r in rows:
        tid = r.get("theorem_id")
        sids = r.get("source_ids", [])
        ev = [audit[s].get("evidence_type") for s in sids if s in audit]
        has_abstract = any(e in ABSTRACT_LEVEL for e in ev)
        vs = r.get("verification_status")
        if vs not in VERIF_VOCAB:
            unsupported.append({"theorem_id": tid, "value": vs, "why": "not in vocabulary"})
        elif vs == "abstract-read" and not has_abstract:
            unsupported.append({"theorem_id": tid, "value": vs, "why": "no cited source has abstract/full-text evidence",
                                "cited_evidence_types": ev})
        if r.get("content_status") == "verified" and not has_abstract:
            verified_on_metadata.append({"theorem_id": tid, "cited_evidence_types": ev})
        # documented conservative derivation: unverified <=> no abstract-level source
        if vs == "unverified" and has_abstract:
            derivation_mismatch.append({"theorem_id": tid, "cited_evidence_types": ev})
    ok = not unsupported and not verified_on_metadata
    add("L0-P4", "verification_status supported by cited evidence; verified rows not metadata-only", ok,
        {"unsupported_status": unsupported, "verified_on_metadata_only": verified_on_metadata,
         "conservative_derivation_exceptions": derivation_mismatch})
    for item in unsupported:
        findings.append({"id": "F-W005-L0-P4", "severity": "major",
                         "statement": "verification_status unsupported by the cited evidence", "detail": item})

    # ---------------- P5 unresolved disclosure ----------------
    missing_unresolved, empty_unresolved, unverified_rows = [], [], []
    for r in rows:
        tid = r.get("theorem_id")
        if "unresolved" not in r or not isinstance(r.get("unresolved"), list):
            missing_unresolved.append(tid)
        elif not r["unresolved"]:
            empty_unresolved.append(tid)
        if r.get("verification_status") == "unverified":
            unverified_rows.append(tid)
    ok = not missing_unresolved
    add("L0-P5", "unresolved field present and typed on every row", ok,
        {"missing_or_untyped": missing_unresolved, "rows_with_empty_unresolved": empty_unresolved,
         "unverified_rows": unverified_rows,
         "note": "all 62 rows carry at least one explicit unresolved item; this is an honesty signal, not a defect"})

    # ---------------- P6 class-token discipline ----------------
    foreign, unbound, cross_family = [], [], []
    for r in rows:
        tid = r.get("theorem_id")
        toks = list(r.get("class_ids") or []) + list(r.get("informs_classes") or [])
        bad = [t for t in toks if t not in FROZEN_CLASSES]
        if bad:
            foreign.append({"theorem_id": tid, "tokens": bad})
        if not r.get("class_ids") and not r.get("informs_classes"):
            unbound.append(tid)
        fams = {t.split("-")[1] for t in (r.get("class_ids") or []) if t in FROZEN_CLASSES}
        if {"WCC", "SCC"} <= fams:
            cross_family.append({"theorem_id": tid, "class_ids": r.get("class_ids")})
    ok = not foreign
    add("L0-P6", "class tokens restricted to the four frozen classes", ok,
        {"foreign_tokens": foreign, "rows_without_class_binding": unbound,
         "rows_spanning_wcc_and_scc": cross_family})
    if unbound:
        findings.append({"id": "F-W005-L0-U1", "severity": "advisory",
                         "statement": "rows carry no class binding and no informs_classes pointer; they are context, not class evidence",
                         "detail": {"count": len(unbound), "rows": unbound}})
    if cross_family:
        findings.append({"id": "F-W005-L0-U2", "severity": "advisory",
                         "statement": "rows span WCC and SCC class ids in one record; reader cannot tell which class each quoted statement binds",
                         "detail": cross_family})

    # ---------------- P7 conclusion-type discipline ----------------
    bad_vocab, unbounded_claim = [], []
    for r in rows:
        tid = r.get("theorem_id")
        if r.get("conclusion_type") not in CONCLUSION_VOCAB:
            bad_vocab.append({"theorem_id": tid, "field": "conclusion_type", "value": r.get("conclusion_type")})
        if r.get("entry_kind") not in ENTRY_VOCAB:
            bad_vocab.append({"theorem_id": tid, "field": "entry_kind", "value": r.get("entry_kind")})
        if r.get("evidence_level") not in EVIDENCE_VOCAB:
            bad_vocab.append({"theorem_id": tid, "field": "evidence_level", "value": r.get("evidence_level")})
        if r.get("conclusion_type") in {"theorem", "counterexample", "conditional_theorem"} \
                and not (r.get("does_not_imply") and r.get("falsifiers")):
            unbounded_claim.append(tid)
    ok = not bad_vocab and not unbounded_claim
    add("L0-P7", "controlled vocabularies respected; no unqualified theorem promotion", ok,
        {"vocabulary_violations": bad_vocab, "claims_without_does_not_imply_or_falsifier": unbounded_claim})

    # ---------------- P8 ledger <-> citation audit cross-binding ----------------
    id_mismatch = sorted(set(srcs) ^ set(audit))
    unresolved_resolver = [cid for cid, a in audit.items() if (a.get("resolver_result") or "").strip() != "resolved"]
    bad_verdict = [cid for cid, a in audit.items() if (a.get("verdict") or "").strip() not in {"verified", "revise", "reject"}]
    no_reviewer = [cid for cid, a in audit.items() if not (a.get("reviewer") or "").strip()]
    used_by_mismatch = []
    for cid, a in audit.items():
        ubt = (a.get("used_by_theorems") or "").strip()
        declared = {x.strip() for x in ubt.replace(";", ",").split(",") if x.strip()} if ubt else set()
        actual = {r.get("theorem_id") for r in rows if cid in r.get("source_ids", [])}
        if declared != actual:
            used_by_mismatch.append({"citation_id": cid, "declared": sorted(declared), "actual": sorted(actual)})
    bad_mapping = [cid for cid, a in audit.items()
                   if (a.get("class_mapping") or "").strip()
                   and (a["class_mapping"].strip() != "(evidence/tag only)"
                        and not set(x for x in a["class_mapping"].split(";") if x) <= FROZEN_CLASSES)]
    ok = not id_mismatch and not unresolved_resolver and not bad_verdict and not no_reviewer and not used_by_mismatch and not bad_mapping
    add("L0-P8", "citation audit binds one row per registry source and mirrors ledger usage", ok,
        {"id_set_mismatch": id_mismatch, "non_resolved": unresolved_resolver,
         "bad_verdict": bad_verdict, "missing_reviewer": no_reviewer,
         "used_by_mismatch": used_by_mismatch, "class_mapping_outside_frozen": bad_mapping})

    # ---------------- P9 no-binding sources not used as evidence ----------------
    no_binding = {cid for cid, a in audit.items() if (a.get("assessment") or "").startswith("assessed_no_binding")}
    misused = []
    for cid in sorted(no_binding):
        refs = [r.get("theorem_id") for r in rows if cid in r.get("source_ids", [])]
        ubt = (audit[cid].get("used_by_theorems") or "").strip()
        if refs or ubt:
            misused.append({"citation_id": cid, "ledger_refs": refs, "used_by": ubt})
    ok = not misused
    add("L0-P9", "assessed_no_binding sources are not cited as theorem evidence", ok,
        {"no_binding_sources": sorted(no_binding), "misused": misused})

    # ---------------- P10 exact_locator exactness (population census) ----------------
    # Added after the pre-registered spot check: SRC-024's sampled locator turned out to be an
    # arXiv discovery query.  Census of the whole audit, not a pre-registered test.
    query_rows, unstable, fixable = [], [], []
    for cid, a in audit.items():
        loc = (a.get("exact_locator") or "").strip()
        if QUERY_LOCATOR_RE.search(loc):
            query_rows.append(cid)
            if "sortBy=submittedDate" in loc:
                unstable.append(cid)
            s = srcs.get(cid, {})
            if s.get("url") or s.get("doi") or s.get("arxiv_id"):
                fixable.append(cid)
    ok = not query_rows
    add("L0-P10", "citation-audit exact_locator is an exact record locator, not a discovery query", ok,
        {"query_style_exact_locators": len(query_rows), "ids": query_rows,
         "sorted_by_submitted_date_unstable": unstable,
         "repairable_from_registry_locator": len(fixable),
         "acceptance_doc_claim": "artifacts/literature/L0_L1_ACCEPTANCE.md: 'The L1 exact_locator column carries the primary page/record URL.'"})
    if query_rows:
        findings.append({"id": "F-W005-L0-H1", "severity": "major",
                         "statement": "citation_audit.exact_locator holds a discovery query (arXiv/INSPIRE search URL) instead of the record locator on a majority of rows; the registry already carries the exact url/DOI/arXiv id",
                         "detail": {"count": len(query_rows), "of": len(audit),
                                    "unstable_sort_queries": len(unstable),
                                    "repairable": len(fixable),
                                    "examples": [{"citation_id": c, "exact_locator": audit[c]["exact_locator"][:120],
                                                  "registry_locator": srcs.get(c, {}).get("url") or srcs.get(c, {}).get("doi") or srcs.get(c, {}).get("arxiv_id")}
                                                 for c in query_rows[:3]]}})

    # ---------------- advisory: per-source grounding not distinguishable ----------------
    mixed = []
    for r in rows:
        ev = [audit[s].get("evidence_type") for s in r.get("source_ids", []) if s in audit]
        if "metadata" in ev and any(e in ABSTRACT_LEVEL for e in ev):
            mixed.append({"theorem_id": r.get("theorem_id"), "cited_evidence_types": ev})
    if mixed:
        findings.append({"id": "F-W005-L0-U3", "severity": "advisory",
                         "statement": "row-level verification_status cannot identify which cited source grounds the statement; rows mix metadata-only and abstract-level anchors",
                         "detail": {"count": len(mixed), "rows": mixed}})

    # ---------------- advisory: assessment column format is mixed ----------------
    prose = [cid for cid, a in audit.items() if not (a.get("assessment") or "").startswith("assessed: ")]
    if prose:
        findings.append({"id": "F-W005-L0-U4", "severity": "advisory",
                         "statement": "citation_audit.assessment mixes 'assessed: <ids>' with prose 'assessed_no_binding: ...' in one column",
                         "detail": {"count": len(prose), "ids": sorted(prose)}})

    # ---------------- advisory: undocumented entry_kind vocabulary ----------------
    ek_census = {}
    for r in rows:
        ek_census[r.get("entry_kind")] = ek_census.get(r.get("entry_kind"), 0) + 1
    singletons = sorted(k for k, n in ek_census.items() if n == 1)
    if singletons:
        findings.append({"id": "F-W005-L0-U5", "severity": "advisory",
                         "statement": "entry_kind has no documented controlled vocabulary; singleton values are unverifiable labels",
                         "detail": {"census": ek_census, "singletons": singletons}})

    hard_fail = [c["id"] for c in checks if c["hard"] and c["status"] == "fail"]
    return checks, findings, hard_fail


def spotcheck_section():
    if not SPOTCHECK.exists():
        return {"status": "pending", "note": "primary-source spot check not yet executed"}
    return json.loads(SPOTCHECK.read_text())


def build_report():
    t0 = {p: sha256_file(p) for p in (LEDGER, AUDIT)}
    data = measure()
    t1 = {p: sha256_file(p) for p in (LEDGER, AUDIT)}
    pins = {
        "ledger": LEDGER_PIN, "audit": AUDIT_PIN,
        "ledger_measured": t0[LEDGER], "audit_measured": t0[AUDIT],
        "stable": t0 == t1,
        "t0": {str(k): v for k, v in t0.items()},
        "t1": {str(k): v for k, v in t1.items()},
    }
    checks, findings, hard_fail = evaluate(data, pins)
    sc = spotcheck_section()
    if sc.get("status") not in (None, "pending") and sc.get("hard_failure"):
        hard_fail = hard_fail + ["L0-SPOTCHECK"]
    verdict = "accept" if not hard_fail else "revise"
    return {
        "schema": "w005-l0-rev3-review-report/v1",
        "task_id": "W005-L0-REV3-REVIEW-01",
        "actor": "worker-005",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": sorted(FROZEN_CLASSES),
        "measured_at": None,  # filled by caller
        "pins": pins,
        "counts": {
            "ledger_rows": len(data["ledger_rows"]),
            "audit_rows": len(data["audit"]),
            "registry_sources": len(data["sources"]),
            "verified": sum(1 for r in data["ledger_rows"] if r.get("content_status") == "verified"),
            "provisional": sum(1 for r in data["ledger_rows"] if r.get("content_status") == "provisional"),
            "rejected": sum(1 for r in data["ledger_rows"] if r.get("content_status") == "rejected"),
            "not_independently_reviewed": sum(1 for r in data["ledger_rows"] if r.get("review_status") == "not_independently_reviewed"),
        },
        "checks": checks,
        "hard_failures": hard_fail,
        "findings": findings,
        "spotcheck": sc,
        "verdict": verdict,
        "score": (4.0 if verdict == "accept" and not [f for f in findings if f["severity"] == "major"]
                  else 3.0 if hard_fail == ["L0-P10"]
                  else 2.5),
        "verdict_note": "Blind independent verdict file is reviews/L0-review-worker-005-rev3.json; this report is the machine evidence behind it.",
        "falsifier": "Re-measure the two pins; a ledger or citation-audit sha256 differing from the pins, a sampled locator resolving to a different work, or a repaired ledger whose verification_status derivation changes voids this review. A different reading of a cited abstract that contradicts the row's statement_exact refutes the corresponding scope judgement.",
        "authority": "worker event; cannot set status=done, validation_status=passed, or a gate verdict",
        "scope_limits": "structural and locator/evidence-binding review only; no physics or mathematics is decided; read-only on all canonical artifacts",
    }


# ----------------------------- selftest -----------------------------
def _mutants(data):
    """Return list of (name, mutated_data, expected_failing_check)."""
    out = []

    m = copy.deepcopy(data)
    m["ledger_rows"][0].setdefault("source_ids", []).append("SRC-999")
    out.append(("dangling_source_id", m, "L0-P3"))

    m = copy.deepcopy(data)
    m["ledger_rows"][1]["theorem_id"] = m["ledger_rows"][0]["theorem_id"]
    out.append(("duplicate_theorem_id", m, "L0-P2"))

    m = copy.deepcopy(data)
    r = m["ledger_rows"][0]
    r["source_ids"] = [s for s in r["source_ids"] if m["audit"].get(s, {}).get("evidence_type") == "metadata"]
    if not r["source_ids"]:
        sid = next(s for s, a in m["audit"].items() if a["evidence_type"] == "metadata")
        r["source_ids"] = [sid]
    r["verification_status"] = "abstract-read"
    out.append(("abstract_read_on_metadata_only", m, "L0-P4"))

    m = copy.deepcopy(data)
    m["ledger_rows"][2].pop("unresolved", None)
    out.append(("missing_unresolved_key", m, "L0-P5"))

    m = copy.deepcopy(data)
    m["ledger_rows"][3].setdefault("class_ids", []).append("AF-SCC-C3-VAC-GEN")
    out.append(("foreign_class_token", m, "L0-P6"))

    m = copy.deepcopy(data)
    cid = sorted(m["audit"])[0]
    m["audit"][cid]["used_by_theorems"] = "T-000"
    out.append(("used_by_mismatch", m, "L0-P8"))

    m = copy.deepcopy(data)
    sid = sorted(m["sources"])[0]
    m["sources"][sid]["doi"] = ""
    m["sources"][sid]["arxiv_id"] = ""
    m["sources"][sid]["url"] = ""
    out.append(("locatorless_source", m, "L0-P3"))

    m = copy.deepcopy(data)
    nb = [cid for cid, a in m["audit"].items() if a["assessment"].startswith("assessed_no_binding")]
    if nb:
        m["ledger_rows"][4]["source_ids"] = [nb[0]]
        out.append(("no_binding_source_cited", m, "L0-P9"))

    m = copy.deepcopy(data)
    # cure every query locator from the registry, then plant one back as a query
    for cid, a in m["audit"].items():
        if QUERY_LOCATOR_RE.search(a.get("exact_locator") or ""):
            s = m["sources"].get(cid, {})
            a["exact_locator"] = s.get("url") or s.get("doi") or s.get("arxiv_id")
    cid0 = sorted(m["audit"])[0]
    m["audit"][cid0]["exact_locator"] = (m["audit"][cid0]["exact_locator"] or "") + "?q=planted"
    out.append(("query_style_exact_locator", m, "L0-P10"))
    return out


def _cured_locator_copy(data):
    m = copy.deepcopy(data)
    for cid, a in m["audit"].items():
        if QUERY_LOCATOR_RE.search(a.get("exact_locator") or ""):
            s = m["sources"].get(cid, {})
            a["exact_locator"] = s.get("url") or s.get("doi") or s.get("arxiv_id")
    return m


def run_selftest(data, pins):
    baseline_checks, baseline_findings, baseline_hard = evaluate(data, pins)
    # null control: the instrument is deterministic on unchanged inputs
    repeat_checks, _, repeat_hard = evaluate(copy.deepcopy(data), pins)
    reproducible = ([c["status"] for c in baseline_checks] == [c["status"] for c in repeat_checks]
                    and baseline_hard == repeat_hard)
    results = []
    for name, mdata, expected in _mutants(data):
        checks, findings, hard = evaluate(mdata, pins)
        failed = [c["id"] for c in checks if c["hard"] and c["status"] == "fail"]
        results.append({
            "mutant": name,
            "expected_check": expected,
            "caught": expected in failed,
            "failed_checks": failed,
            "hard_failures": hard,
        })
    # repair control: curing the locator defect must flip L0-P10 to pass
    cured_checks, _, cured_hard = evaluate(_cured_locator_copy(data), pins)
    p10_status = next(c["status"] for c in cured_checks if c["id"] == "L0-P10")
    # controls: deliberately blind evaluators must disagree with the instrument
    always_accept = {"hard_failures": [], "verdict": "accept"}
    always_reject_statuses = ["fail"] * len(baseline_checks)
    caught = sum(1 for r in results if r["caught"])
    return {
        "schema": "w005-l0-rev3-selftest/v1",
        "instrument": "artifacts/worker-005/l0_rev3_review/check_l0_rev3.py",
        "baseline": {"verdict": "accept" if not baseline_hard else "revise",
                     "hard_failures": baseline_hard,
                     "failed_checks": [c["id"] for c in baseline_checks if c["status"] == "fail"]},
        "mutants": results,
        "mutants_caught": f"{caught}/{len(results)}",
        "controls": {
            "null_control_reproducible": reproducible,
            "always_accept_control_differs_on_baseline": always_accept["hard_failures"] != baseline_hard,
            "always_reject_control_differs_on_live": always_reject_statuses != [c["status"] for c in baseline_checks],
            "repair_control_locator_cure_flips_P10_to_pass": p10_status == "pass" and "L0-P10" not in cured_hard,
            "all_mutants_discriminated": caught == len(results) and len(results) > 0,
        },
        "mutant_names": [r["mutant"] for r in results],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    t0 = {p: sha256_file(p) for p in (LEDGER, AUDIT)}
    data = measure()
    t1 = {p: sha256_file(p) for p in (LEDGER, AUDIT)}
    pins = {"ledger": LEDGER_PIN, "audit": AUDIT_PIN,
            "ledger_measured": t0[LEDGER], "audit_measured": t0[AUDIT],
            "stable": t0 == t1, "t0": t0, "t1": t1}
    checks, findings, hard = evaluate(data, pins)

    for c in checks:
        print(f"{c['status'].upper():4s} {c['id']}  {c['title']}")
    print(f"hard_failures={hard}")
    print(f"findings={[f['id'] for f in findings]}")

    if args.selftest:
        st = run_selftest(data, pins)
        (HERE / "selftest.json").write_text(json.dumps(st, indent=2) + "\n")
        print("selftest:", st["mutants_caught"], "controls:",
              json.dumps(st["controls"]))
        if not all(st["controls"].values()):
            return 3
    if args.report:
        rep = build_report()
        from datetime import datetime, timezone, timedelta
        rep["measured_at"] = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
        (HERE / "report.json").write_text(json.dumps(rep, indent=2) + "\n")
        print("report verdict:", rep["verdict"])
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
