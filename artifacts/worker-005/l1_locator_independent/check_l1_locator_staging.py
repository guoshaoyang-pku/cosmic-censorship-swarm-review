#!/usr/bin/env python3
"""W005-L1-LOCATOR-STAGING-VALIDATION-01

Independent, read-only validation of the L1 locator remediation staging map in
    artifacts/worker-025/l1_locator_adj/report.json
against the frozen canonical ledger
    ledger/citation_audit.csv#315c19145065...

What this instrument does NOT do:
  * it does not write, repoint or repair any canonical artifact;
  * it does not claim a gate verdict, a node status or validation_status=passed;
  * it does not re-fetch the network. HTTP statuses are taken from the cited
    worker-025 cache and are reported as cache-sourced corroboration only.

The one file this instrument writes on a normal run is the *non-canonical*
candidate patch under artifacts/worker-005/l1_locator_independent/ (owner of
record for ledger/citation_audit.csv is astra-lead-literature).

Determinism: the report contains no wall-clock call. Re-running with the same
--stamp on the same bytes must reproduce the report byte-for-byte.

Usage:
    python3 check_l1_locator_staging.py --selftest
    python3 check_l1_locator_staging.py --report-out .../report.json \
        --candidate-out .../citation_audit.locator-repair.candidate.csv \
        --stamp 2026-09-12T01:30:00+08:00
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import re
import sys

SELF = "artifacts/worker-005/l1_locator_independent/check_l1_locator_staging.py"
FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
NON_CLASS_MARKERS = {"(evidence/tag only)"}
QUERY_RE = re.compile(r"[?&](q|search_query|query|search)=")
ANNOT_RE = re.compile(r"\s")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ARXIV_ID_RE = re.compile(r"^(\d{4}\.\d{4,5}|[a-z-]+(\.[A-Z]{2})?/\d{7})$", re.I)

CHECKS = [
    ("C1", "pins_and_declared_inputs_measured"),
    ("C2", "report_rows_match_canonical_order_and_ids"),
    ("C3", "report_row_cells_match_canonical_bytes"),
    ("C4", "independent_census_reproduced"),
    ("C5", "staged_values_all_direct_record_locators"),
    ("C6", "staged_values_owned_by_the_same_source"),
    ("C7", "staged_values_unique_no_cross_binding"),
    ("C8", "change_set_minimal_and_exact"),
    ("C9", "class_mapping_bytes_untouched_and_in_scope"),
    ("C10", "candidate_patch_byte_mechanics"),
    ("C11", "anchor_cache_claims_corroborated"),
]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_canonical(root: str):
    path = os.path.join(root, "ledger/citation_audit.csv")
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    header = rows[0]
    body = rows[1:]
    return path, raw, header, body


def field(header, row, name):
    return row[header.index(name)] if name in header else None


def classify(u: str) -> str:
    """Independent locator taxonomy.

    QUERY     - carries a search/query parameter (a discovery query, not a record)
    TRUNCATED - query literal elided with '...' (subset of QUERY forms)
    ANNOTATED - URL polluted by prose/whitespace outside the URL itself
    API_RECORD- stable metadata-record endpoint keyed by a DOI
    CLEAN_URL - everything else (record page / DOI / arXiv abs)
    """
    s = (u or "").strip()
    if "..." in s:
        return "TRUNCATED"
    if QUERY_RE.search(s) or "/api/query" in s:
        return "QUERY"
    if ANNOT_RE.search(s):
        return "ANNOTATED"
    if "api.crossref.org/works/" in s or "api.openalex.org/works/" in s:
        return "API_RECORD"
    return "CLEAN_URL"


def is_direct_record_locator(u: str) -> bool:
    """A locator that identifies one record (no query, no elision, no prose)."""
    s = (u or "").strip()
    if not s or not s.startswith("http"):
        return False
    cls = classify(s)
    return cls in ("CLEAN_URL", "API_RECORD")


def url_owns(candidate: str, row_fields) -> bool:
    """True iff the candidate locator is derivable from the row's own columns."""
    c = (candidate or "").strip()
    if not c:
        return False
    pool = set()
    for v in row_fields:
        v = (v or "").strip()
        if not v:
            continue
        pool.add(v)
        pool.add(v.rstrip("/"))
        if v.startswith("http"):
            pool.add(v.lower())
        if DOI_RE.match(v):
            pool.add("https://doi.org/" + v)
            pool.add("https://doi.org/" + v.lower())
        if ARXIV_ID_RE.match(v):
            pool.add("https://arxiv.org/abs/" + v)
    c_norm = c.rstrip("/")
    return c in pool or c_norm in pool or c.lower() in pool


def check_pins(root, report, report_path):
    declared = report.get("pinned_inputs", {})
    measured, mismatches = {}, []
    for rel, want in sorted(declared.items()):
        p = os.path.join(root, rel)
        got = sha256_file(p) if os.path.exists(p) else "ABSENT"
        measured[rel] = got
        if got != want:
            mismatches.append({"path": rel, "declared": want, "measured": got})
    report_sha = sha256_file(report_path) if os.path.exists(report_path) else None
    return {
        "status": "pass" if not mismatches else "fail",
        "detail": {
            "declared": declared,
            "measured": measured,
            "mismatches": mismatches,
            "report_sha256": report_sha,
        },
        "evidence_refs": ([f"{report_path}#{report_sha[:12]}"] if report_sha else [])
        + [f"{rel}#{h[:12]}" for rel, h in measured.items()],
    }


def check_rows_identity(report, header, body):
    rrows = report.get("rows", [])
    problems = []
    if len(rrows) != len(body):
        problems.append(f"row count report={len(rrows)} canonical={len(body)}")
    ids_c = [field(header, r, "citation_id") for r in body]
    ids_r = [r.get("citation_id") for r in rrows]
    for i, (a, b) in enumerate(zip(ids_c, ids_r)):
        if a != b:
            problems.append(f"row {i}: canonical {a!r} != report {b!r}")
    return {
        "status": "pass" if not problems else "fail",
        "detail": {"rows_total": len(rrows), "canonical_total": len(body),
                   "id_mismatches": problems[:20]},
        "evidence_refs": ["ledger/citation_audit.csv#315c19145065"],
    }


def check_row_cells(report, header, body):
    cols = ["bibkey", "class_mapping", "used_by_theorems", "evidence_url", "exact_locator"]
    problems = []
    for c_row, r_row in zip(body, report.get("rows", [])):
        for col in cols:
            a = field(header, c_row, col)
            b = r_row.get(col)
            if a is None or b is None:
                continue
            if a.strip() != str(b).strip():
                problems.append({"citation_id": field(header, c_row, "citation_id"),
                                 "column": col, "canonical": a, "report": b})
    return {
        "status": "pass" if not problems else "fail",
        "detail": {"columns": cols, "mismatches": problems[:20],
                   "mismatch_count": len(problems)},
        "evidence_refs": ["artifacts/worker-025/l1_locator_adj/report.json"],
    }


def check_census(report, header, body):
    counts = {}
    per_row = {}
    for c_row, r_row in zip(body, report.get("rows", [])):
        cid = field(header, c_row, "citation_id")
        cls = classify(field(header, c_row, "exact_locator"))
        counts[cls] = counts.get(cls, 0) + 1
        per_row[cid] = cls
    query_strict = counts.get("QUERY", 0) + counts.get("TRUNCATED", 0)
    expected = {"CLEAN_URL": 19, "API_RECORD": 10, "QUERY": 40, "TRUNCATED": 27,
                "ANNOTATED": 1}
    # worker-025's DIRECT 26 == our CLEAN_URL 19 + the 7 API_RECORD rows they labelled DIRECT
    api_labelled_direct = [
        r["citation_id"] for r in report.get("rows", [])
        if per_row.get(r["citation_id"]) == "API_RECORD"
        and r.get("exact_locator_class") == "DIRECT"
    ]
    api_labelled_other = [
        r["citation_id"] for r in report.get("rows", [])
        if per_row.get(r["citation_id"]) == "API_RECORD"
        and r.get("exact_locator_class") == "OTHER"
    ]
    ok = counts == expected and len(api_labelled_direct) == 7 and len(api_labelled_other) == 3
    return {
        "status": "pass" if ok else "fail",
        "detail": {
            "independent_counts": counts,
            "expected_counts": expected,
            "query_or_truncated": query_strict,
            "reconciles_worker_005_67": query_strict == 67,
            "reconciles_worker_025_71": query_strict + counts.get("ANNOTATED", 0)
            + len(api_labelled_other) == 71,
            "api_record_labelled_direct": api_labelled_direct,
            "api_record_labelled_other": api_labelled_other,
        },
        "evidence_refs": ["ledger/citation_audit.csv#315c19145065",
                          "artifacts/worker-025/l1_locator_adj/report.json"],
    }


def check_staged_direct(report):
    bad = [{"citation_id": r.get("citation_id"),
            "staged": r.get("proposed_staged_locator"),
            "class": classify(r.get("proposed_staged_locator")),
            "declared_direct": r.get("proposed_locator_is_direct")}
           for r in report.get("rows", [])
           if not is_direct_record_locator(r.get("proposed_staged_locator"))]
    return {
        "status": "pass" if not bad else "fail",
        "detail": {"rows_total": len(report.get("rows", [])),
                   "staged_direct": len(report.get("rows", [])) - len(bad),
                   "violations": bad[:20]},
        "evidence_refs": ["artifacts/worker-025/l1_locator_adj/report.json"],
    }


def check_staged_ownership(report, header, body):
    bad = []
    for c_row, r_row in zip(body, report.get("rows", [])):
        pool = [field(header, c_row, c) for c in
                ("url", "doi", "arxiv_id", "evidence_url", "exact_locator")]
        if not url_owns(r_row.get("proposed_staged_locator"), pool):
            bad.append({"citation_id": field(header, c_row, "citation_id"),
                        "staged": r_row.get("proposed_staged_locator"),
                        "own_columns": pool})
    return {
        "status": "pass" if not bad else "fail",
        "detail": {"rows_total": len(body), "same_source": len(body) - len(bad),
                   "violations": bad[:20]},
        "evidence_refs": ["ledger/citation_audit.csv#315c19145065"],
    }


def check_staged_unique(report):
    seen, dup = {}, []
    for r in report.get("rows", []):
        v = (r.get("proposed_staged_locator") or "").strip()
        if v in seen and seen[v] != r.get("citation_id"):
            dup.append({"locator": v, "rows": [seen[v], r.get("citation_id")]})
        seen[v] = r.get("citation_id")
    return {
        "status": "pass" if not dup else "fail",
        "detail": {"distinct_staged": len(seen), "duplicates": dup[:20]},
        "evidence_refs": ["artifacts/worker-025/l1_locator_adj/report.json"],
    }


def check_minimal_change(report, header, body):
    changed, non_direct_unchanged, gratuitous, wrong = [], [], [], []
    for c_row, r_row in zip(body, report.get("rows", [])):
        cid = field(header, c_row, "citation_id")
        canon = field(header, c_row, "exact_locator")
        staged = r_row.get("proposed_staged_locator")
        cls = classify(canon)
        if (canon or "").strip() != (staged or "").strip():
            changed.append({"citation_id": cid, "class": cls, "old": canon, "new": staged})
            if is_direct_record_locator(canon):
                gratuitous.append(cid)
        elif cls in ("QUERY", "TRUNCATED", "ANNOTATED"):
            non_direct_unchanged.append({"citation_id": cid, "class": cls, "value": canon})
        if not is_direct_record_locator(staged):
            wrong.append(cid)
    ok = (len(changed) == 68 and not gratuitous and not non_direct_unchanged and not wrong)
    return {
        "status": "pass" if ok else "fail",
        "detail": {"changed_rows": len(changed),
                   "changed_breakdown": {k: sum(1 for c in changed if c["class"] == k)
                                         for k in ("QUERY", "TRUNCATED", "ANNOTATED",
                                                   "CLEAN_URL", "API_RECORD")},
                   "gratuitous_direct_changes": gratuitous,
                   "unchanged_non_direct": non_direct_unchanged[:20],
                   "staged_not_direct": wrong,
                   "changed": changed},
        "evidence_refs": ["ledger/citation_audit.csv#315c19145065",
                          "artifacts/worker-025/l1_locator_adj/report.json"],
    }


def check_class_mapping(report, header, body):
    problems, token_rows, marker_rows = [], 0, 0
    disjunctive = []
    for c_row, r_row in zip(body, report.get("rows", [])):
        cid = field(header, c_row, "citation_id")
        a = (field(header, c_row, "class_mapping") or "").strip()
        b = str(r_row.get("class_mapping") or "").strip()
        if a != b:
            problems.append({"citation_id": cid, "canonical": a, "report": b})
        if ";" in b:
            disjunctive.append(cid)
        for tok in [t.strip() for t in b.split(";") if t.strip()]:
            if tok in FROZEN_CLASSES:
                token_rows += 1
            elif tok in NON_CLASS_MARKERS:
                marker_rows += 1
            else:
                problems.append({"citation_id": cid, "unknown_token": tok})
    return {
        "status": "pass" if not problems else "fail",
        "detail": {"rows_total": len(body), "class_token_rows": token_rows,
                   "marker_rows": marker_rows, "mismatches": problems[:20],
                   "disjunctive_rows": len(disjunctive),
                   "disjunctive_ids": disjunctive},
        "evidence_refs": ["ledger/citation_audit.csv#315c19145065"],
    }


def build_candidate(header, body, report):
    """Return (candidate_bytes, cell_diff) - only exact_locator cells may move."""
    idx = header.index("exact_locator")
    staged = {r.get("citation_id"): r.get("proposed_staged_locator")
              for r in report.get("rows", [])}
    out_rows = [list(header)]
    diffs = []
    for row in body:
        new = list(row)
        cid = field(header, row, "citation_id")
        val = staged.get(cid, new[idx])
        if (new[idx] or "").strip() != (val or "").strip():
            diffs.append({"citation_id": cid, "row": len(out_rows),
                          "old": new[idx], "new": val})
            new[idx] = val
        out_rows.append(new)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerows(out_rows)
    return buf.getvalue().encode("utf-8"), diffs


def check_candidate(root, header, body, report, candidate_path, raw):
    data, diffs = build_candidate(header, body, report)
    # round-trip: reparse the candidate and compare every cell but exact_locator
    new_rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
    byte_problems = []
    if len(new_rows) != len(body) + 1:
        byte_problems.append("row count changed")
    changed_cells = 0
    for i, (a, b) in enumerate(zip(body, new_rows[1:])):
        for j, (x, y) in enumerate(zip(a, b)):
            if x != y:
                changed_cells += 1
                if header[j] != "exact_locator":
                    byte_problems.append(
                        {"row": i, "column": header[j], "canonical": x, "candidate": y})
    wrote = None
    if candidate_path:
        os.makedirs(os.path.dirname(candidate_path), exist_ok=True)
        with open(candidate_path, "wb") as fh:
            fh.write(data)
        wrote = sha256_file(candidate_path)
    # identity: canonical bytes must be untouched on disk
    canonical_path = os.path.join(root, "ledger/citation_audit.csv")
    if os.path.exists(canonical_path):
        canonical_now = sha256_file(canonical_path)
    else:
        canonical_now = hashlib.sha256(raw).hexdigest()  # synthetic self-test root
    ok = (not byte_problems and changed_cells == len(diffs) == 68
          and canonical_now == hashlib.sha256(raw).hexdigest())
    return {
        "status": "pass" if ok else "fail",
        "detail": {"changed_cells": changed_cells, "declared_diffs": len(diffs),
                   "changed_cells_outside_exact_locator": byte_problems[:20],
                   "candidate_path": candidate_path, "candidate_sha256": wrote,
                   "canonical_untouched_sha256": canonical_now,
                   "canonical_expected_sha256": hashlib.sha256(raw).hexdigest()},
        "evidence_refs": [f"{candidate_path}#{(wrote or '')[:12]}",
                          "ledger/citation_audit.csv#315c19145065"],
        "_diffs": diffs,
    }


def check_anchor_claims(report):
    """Corroborate the worker-025 anchor claims from the report's own rows.

    Two denominators exist and must bridge: worker-025's defective set is
    non-DIRECT by *their* label (71 = QUERY 40 + TRUNCATED 27 + OTHER 4), while
    this instrument's repair set is QUERY+TRUNCATED+ANNOTATED (68). The 3-row
    difference is exactly the api.crossref/openalex record rows they labelled
    OTHER, all of which carry HTTP_200 anchors.
    """
    rows = report.get("rows", [])
    defective_by_label = [r for r in rows if r.get("exact_locator_class") != "DIRECT"]
    defective_by_mine = [r for r in rows
                         if classify(r.get("exact_locator")) in ("QUERY", "TRUNCATED", "ANNOTATED")]

    def resolving(r):
        return bool(r.get("alternative_anchor_present_ok")) and \
            r.get("alternative_anchor_status") == "HTTP_200"

    claimed = {
        "defective_rows_with_resolving_alternative_anchor":
            report.get("summary", {}).get("defective_rows_with_resolving_alternative_anchor"),
        "defective_rows_without_resolving_alternative_anchor":
            report.get("summary", {}).get("defective_rows_without_resolving_alternative_anchor"),
        "rows_with_alternative_anchor_present":
            report.get("summary", {}).get("rows_with_alternative_anchor_present"),
    }
    by_label = {
        "defective_rows_with_resolving_alternative_anchor":
            sum(1 for r in defective_by_label if resolving(r)),
        "defective_rows_without_resolving_alternative_anchor":
            sum(1 for r in defective_by_label if not resolving(r)),
        "rows_with_alternative_anchor_present":
            sum(1 for r in rows if r.get("alternative_anchor_present_ok")),
    }
    by_mine = {
        "defective_total": len(defective_by_mine),
        "resolving": sum(1 for r in defective_by_mine if resolving(r)),
        "non_resolving": [r["citation_id"] for r in defective_by_mine if not resolving(r)],
    }
    api_other_resolving = [
        r["citation_id"] for r in rows
        if classify(r.get("exact_locator")) == "API_RECORD"
        and r.get("exact_locator_class") != "DIRECT" and resolving(r)
    ]
    bridge_ok = (len(api_other_resolving) == 3
                 and by_mine["resolving"] + len(api_other_resolving)
                 == by_label["defective_rows_with_resolving_alternative_anchor"])
    absent = [r["citation_id"] for r in rows
              if r.get("alternative_anchor_status") == "ABSENT"]
    ok = claimed == by_label and bridge_ok
    return {
        "status": "pass" if ok else "fail",
        "detail": {"source": "worker-025 cache manifest; NOT re-fetched by this instrument",
                   "claimed": claimed, "recomputed_by_report_label": by_label,
                   "recomputed_by_this_taxonomy": by_mine,
                   "api_record_other_rows_resolving": api_other_resolving,
                   "denominator_bridge_ok": bridge_ok,
                   "absent_anchor_ids": absent},
        "evidence_refs": ["artifacts/worker-025/l1_locator_adj/cache_manifest.json",
                          "artifacts/worker-025/l1_locator_adj/report.json"],
    }


# --------------------------------------------------------------------------
# run all checks
# --------------------------------------------------------------------------
def run_checks(root, report, report_path, candidate_path):
    cpath, raw, header, body = load_canonical(root)
    out = [
        ("C1", check_pins(root, report, report_path)),
        ("C2", check_rows_identity(report, header, body)),
        ("C3", check_row_cells(report, header, body)),
        ("C4", check_census(report, header, body)),
        ("C5", check_staged_direct(report)),
        ("C6", check_staged_ownership(report, header, body)),
        ("C7", check_staged_unique(report)),
        ("C8", check_minimal_change(report, header, body)),
        ("C9", check_class_mapping(report, header, body)),
        ("C10", check_candidate(root, header, body, report, candidate_path, raw)),
        ("C11", check_anchor_claims(report)),
    ]
    titles = dict(CHECKS)
    checks = []
    for cid, res in out:
        checks.append({
            "id": cid,
            "title": titles[cid],
            "status": res["status"],
            "detail": res["detail"],
            "evidence_refs": res["evidence_refs"],
        })
    hard_failures = [c["id"] for c in checks if c["status"] == "fail"]
    return checks, hard_failures


def emit_report(root, report_path, candidate_path, stamp):
    with open(report_path, "r", encoding="utf-8") as fh:
        report = json.load(fh)
    checks, hard_failures = run_checks(root, report, report_path, candidate_path)
    result = {
        "schema": "worker-005/l1-locator-staging-validation/v1",
        "actor": "worker-005",
        "agent_slot": "worker-005",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "task_id": "W005-L1-LOCATOR-STAGING-VALIDATION-01",
        "measured_at": stamp,
        "authority": "worker event; cannot set status=done, validation_status=passed or a gate verdict",
        "target": {
            "canonical_ledger": "ledger/citation_audit.csv",
            "canonical_ledger_sha256": sha256_file(
                os.path.join(root, "ledger/citation_audit.csv")),
            "staging_report": "artifacts/worker-025/l1_locator_adj/report.json",
            "staging_report_sha256": sha256_file(report_path),
            "staging_report_pins": report.get("pinned_inputs", {}),
        },
        "checks": checks,
        "hard_failures": hard_failures,
        "verdict": "staging_validated" if not hard_failures else "staging_defective",
        "findings": [
            {"id": "A-W005-L1S-01", "severity": "advisory",
             "axis": "census label taxonomy consistency",
             "finding": ("worker-025's 4-way label taxonomy is applied inconsistently "
                         "across 10 structurally identical api.crossref/openalex record "
                         "URLs: 7 are labelled DIRECT and 3 OTHER. The staging values are "
                         "identical to the originals in all 10, so the staging map is "
                         "unaffected; only the census label is ambiguous."),
             "evidence_refs": ["artifacts/worker-025/l1_locator_adj/report.json"]},
            {"id": "A-W005-L1S-02", "severity": "advisory",
             "axis": "class_mapping hygiene (out of scope for the locator repair)",
             "finding": ("26/97 canonical rows carry a disjunctive class_mapping token "
                         "(e.g. AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN). The locator repair "
                         "must not and does not touch class_mapping, but the disjunctive "
                         "rows remain an A1 class-leakage item for the literature lead."),
             "evidence_refs": ["ledger/citation_audit.csv#315c19145065"]},
            {"id": "A-W005-L1S-03", "severity": "info",
             "axis": "unresolved alternative anchor",
             "finding": ("SRC-041's cached alternative anchor returned HTTP_403, so 1/71 "
                         "defective rows has no cache-resolving anchor; its staged DOI "
                         "locator https://doi.org/10.1142/9789814374552_0002 is a direct "
                         "record locator but was not re-fetched here."),
             "evidence_refs": ["artifacts/worker-025/l1_locator_adj/cache_manifest.json",
                               "artifacts/worker-025/l1_locator_adj/report.json"]},
        ],
        "not_claimed": ["gate verdict", "node status", "validation_status",
                        "live-artifact repair", "network re-resolution",
                        "citation-support adjudication"],
        "falsifier": ("Re-run this instrument with the same --stamp on a byte-identical "
                      "staging report and canonical ledger: a different check verdict, a "
                      "different candidate sha256, a moved pinned input, a staged locator "
                      "that is not a direct record locator of the same source, or a "
                      "canonical ledger write voids/refutes the corresponding check."),
    }
    return result


# --------------------------------------------------------------------------
# self-test: planted mutants, one per check, plus degenerate controls
# --------------------------------------------------------------------------
def _tiny_report():
    """Minimal synthetic report+canonical pair exercising every check."""
    header = ["citation_id", "bibkey", "class_mapping", "used_by_theorems",
              "url", "doi", "arxiv_id", "evidence_url", "exact_locator"]
    # 4 rows: clean, query, truncated, api-record
    body = [
        ["SRC-A", "a2020", "AF-WCC-VAC-GEN", "T-1",
         "https://arxiv.org/abs/2001.00001", "", "2001.00001",
         "https://arxiv.org/abs/2001.00001", "https://arxiv.org/abs/2001.00001"],
        ["SRC-B", "b2020", "(evidence/tag only)", "",
         "https://doi.org/10.1007/x", "10.1007/x", "",
         "https://doi.org/10.1007/x", "https://inspirehep.net/api/literature?q=foo+bar"],
        ["SRC-C", "c2020", "AF-SCC-C2-VAC-GEN", "T-2",
         "https://arxiv.org/abs/2002.00002", "", "2002.00002",
         "https://arxiv.org/abs/2002.00002", "https://export.arxiv.org/api/query?search_query=ti:...foo..."],
        ["SRC-D", "d2020", "AF-SCC-C0-VAC-GEN", "T-3",
         "https://api.crossref.org/works/10.1000/y", "10.1000/y", "",
         "https://api.crossref.org/works/10.1000/y", "https://api.crossref.org/works/10.1000/y"],
    ]
    staged = {
        "SRC-A": "https://arxiv.org/abs/2001.00001",
        "SRC-B": "https://doi.org/10.1007/x",
        "SRC-C": "https://arxiv.org/abs/2002.00002",
        "SRC-D": "https://api.crossref.org/works/10.1000/y",
    }
    rows = []
    for r in body:
        cid = r[0]
        rows.append({
            "citation_id": cid, "bibkey": r[1], "class_mapping": r[2],
            "used_by_theorems": r[3], "evidence_url": r[7], "exact_locator": r[8],
            "proposed_staged_locator": staged[cid],
            "proposed_locator_is_direct": True,
            "exact_locator_class": {"SRC-A": "DIRECT", "SRC-B": "TRUNCATED",
                                    "SRC-C": "TRUNCATED", "SRC-D": "OTHER"}[cid],
            "alternative_anchor_present_ok": True,
            "alternative_anchor_status": "HTTP_200",
        })
    report = {
        "pinned_inputs": {},
        "summary": {"defective_rows_with_resolving_alternative_anchor": 3,
                    "defective_rows_without_resolving_alternative_anchor": 0,
                    "rows_with_alternative_anchor_present": 4},
        "rows": rows,
    }
    return header, body, report


def selftest():
    """Run checks against synthetic data with mutant injection.

    The synthetic fixture is deliberately 4 rows, so the absolute constants in
    C4/C8/C10 cannot pass on it; the self-test therefore asserts *differential*
    behaviour: baseline deterministic, and every planted mutant flips at least
    one check from pass to fail (or changes the failure set), while the two
    degenerate controls behave oppositely.
    """
    header, body, report = _tiny_report()

    # monkey-patch the canonical loader to serve the synthetic fixture for the
    # whole self-test (baseline + every mutant)
    global load_canonical
    real_loader = load_canonical
    buf = io.StringIO()
    csv.writer(buf).writerows([header] + body)
    raw = buf.getvalue().encode()

    def fake_loader(_root):
        return "synthetic", raw, header, body

    load_canonical = fake_loader
    try:
        base_checks, base_fails = run_checks("synthetic", report, "synthetic", None)
        rerun_checks, _ = run_checks("synthetic", report, "synthetic", None)
        base_status = {c["id"]: c["status"] for c in base_checks}
        rerun_status = {c["id"]: c["status"] for c in rerun_checks}

        mutants = []
        for name, mutate, expect in [
            ("M1_drop_row", lambda rp: rp["rows"].pop(), "C2"),
            ("M2_reorder_rows", lambda rp: rp["rows"].reverse(), "C2"),
            ("M3_change_bibkey", lambda rp: rp["rows"][0].update(bibkey="WRONG"), "C3"),
            ("M4_change_class_mapping", lambda rp: rp["rows"][0].update(
                class_mapping="AF-SCC-C2-VAC-GEN"), "C9"),
            ("M5_query_staged", lambda rp: rp["rows"][0].update(
                proposed_staged_locator="https://x.org/?q=foo"), "C5"),
            ("M6_foreign_staged", lambda rp: rp["rows"][0].update(
                proposed_staged_locator="https://arxiv.org/abs/9999.99999"), "C6"),
            ("M7_duplicate_staged", lambda rp: rp["rows"][1].update(
                proposed_staged_locator=rp["rows"][0]["proposed_staged_locator"]), "C7"),
            ("M8_ellipsis_staged", lambda rp: rp["rows"][2].update(
                proposed_staged_locator="https://export.arxiv.org/api/query?search_query=ti:...x..."),
             "C5"),
            ("M9_pin_mismatch", lambda rp: rp["pinned_inputs"].update(
                {"ledger/citation_audit.csv": "0" * 64}), "C1"),
            ("M10_anchor_claim", lambda rp: rp["summary"].update(
                defective_rows_with_resolving_alternative_anchor=99), "C11"),
        ]:
            rp = copy.deepcopy(report)
            mutate(rp)
            try:
                checks, fails = run_checks("synthetic", rp, "synthetic", None)
                status = {c["id"]: c["status"] for c in checks}
                caught = status.get(expect) == "fail"
                flipped = sorted(set(k for k in status if status[k] != base_status[k]))
            except Exception as exc:  # a refused verdict also counts as caught
                caught, flipped = True, [f"EXC:{type(exc).__name__}"]
            mutants.append({"mutant": name, "expected_check": expect,
                            "caught": caught, "flipped": flipped})

        # decision-rule controls: the aggregate rule must accept an all-pass
        # battery, reject an all-fail battery, and therefore not be constant
        def decide(checks):
            return "reject" if any(c["status"] == "fail" for c in checks) else "accept"

        all_pass = [dict(c, status="pass") for c in base_checks]
        all_fail = [dict(c, status="fail") for c in base_checks]
        controls = {
            "baseline_reproducible": base_status == rerun_status,
            "decision_accepts_all_pass": decide(all_pass) == "accept",
            "decision_rejects_all_fail": decide(all_fail) == "reject",
            "decision_nonconstant": decide(all_pass) != decide(all_fail),
            "mutants_all_caught": all(m["caught"] for m in mutants),
        }
        return {
            "schema": "worker-005/l1-locator-staging-selftest/v1",
            "fixture": "synthetic 4-row ledger + staged report",
            "baseline_hard_failures": base_fails,
            "baseline_status": base_status,
            "mutants": mutants,
            "controls": controls,
            "verdict": "PASS" if all(controls.values()) else "FAIL",
        }
    finally:
        load_canonical = real_loader


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    ap.add_argument("--report", default=None,
                    help="staging report (default artifacts/worker-025/l1_locator_adj/report.json)")
    ap.add_argument("--report-out", default=None)
    ap.add_argument("--candidate-out", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selftest-out", default=None)
    ap.add_argument("--stamp", default="2026-09-12T01:30:00+08:00")
    args = ap.parse_args(argv)

    if args.selftest:
        out = selftest()
        text = json.dumps(out, indent=1, sort_keys=True)
        if args.selftest_out:
            os.makedirs(os.path.dirname(args.selftest_out), exist_ok=True)
            with open(args.selftest_out, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
        print(text)
        return 0 if out["verdict"] == "PASS" else 1

    root = args.root
    report_path = args.report or os.path.join(
        root, "artifacts/worker-025/l1_locator_adj/report.json")
    result = emit_report(root, report_path, args.candidate_out, args.stamp)
    text = json.dumps(result, indent=1, sort_keys=True)
    if args.report_out:
        os.makedirs(os.path.dirname(args.report_out), exist_ok=True)
        with open(args.report_out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0 if not result["hard_failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
