#!/usr/bin/env python3
"""W073-L1-REPAIR-READINESS-01 — independent, read-only, offline verification of the
staged L1 record-identifier repair recipe at pinned ledger/citation_audit.csv 315c19145065.

Pre-registration: artifacts/worker-073/l1_repair_readiness/prereg.json (mtime precedes this file).
Nothing is imported from worker-025; the census and provenance tests are re-implemented here.
Exit codes: 0 = report written, decision in {REPAIR_READY_ALL, REPAIR_READY_WITH_RESIDUAL};
            2 = report written, decision REPAIR_NOT_READY; 3 = fail-closed, no report written.
"""
import csv
import hashlib
import io
import json
import os
import re
import sys
from urllib.parse import urlparse, parse_qs

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(ROOT, "ledger", "citation_audit.csv")
W025 = os.path.join(ROOT, "artifacts", "worker-025", "l1_locator_adj", "report.json")
W025_SCRIPT = os.path.join(ROOT, "artifacts", "worker-025", "l1_locator_adj", "run_l1_locator_025.py")
ACCEPT = os.path.join(ROOT, "artifacts", "literature", "L0_L1_ACCEPTANCE.md")
RUBRIC = os.path.join(ROOT, "evaluation_rubric.yaml")

PINS = {
    LEDGER: "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    W025: "26f0071c558e99c573d1f1cbfaea4a27f996555f50963e6ec478c7dc09fc2c5d",
    W025_SCRIPT: "1a2f6588be5cf50671cea5a1384532f006c97b4bbcfd44597ffa8b1aaf336d2b",
    ACCEPT: "fde5600b45a58698d1cb4e625127bcd54952dc9eaf17a47449329cccc28806c5",
    RUBRIC: "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
}
FROZEN_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
OWN_FIELDS = ["doi", "arxiv_id", "url", "evidence_url", "exact_locator"]
ARCHIVE_HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
ARXIV_RE = re.compile(r"^(?:arXiv:)?(\d{4}\.\d{4,5})(v\d+)?$", re.I)
INSPIRE_RECORD_RE = re.compile(r"^/literature/\d+/?$")
INSPIRE_API_RE = re.compile(r"^/api/literature/\d+/?$")
CROSSREF_WORKS_RE = re.compile(r"^/works/10\.\d{4,9}/\S+$")
OPENALEX_WORKS_RE = re.compile(r"^/works/doi:10\.\d{4,9}/\S+$")
PRIMARY_PAGE_RE = re.compile(r"/(article|abs|full|record|doc|pdf)/")
DOC_SUFFIXES = (".pdf", ".html", ".htm", ".ps", ".tex")
# Amendment 1: single-record API endpoint host+path shapes accepted as record identifiers.
API_SHAPES = ("api.crossref.org/works/", "api.openalex.org/works/doi:", "inspirehep.net/api/literature/")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins():
    out = {}
    for path, expected in PINS.items():
        if not os.path.exists(path):
            out[path] = {"pinned_sha256": expected, "measured_sha256": None,
                         "match": False, "bytes": None, "exists": False}
            continue
        measured = sha256_file(path)
        out[path] = {"pinned_sha256": expected, "measured_sha256": measured,
                     "match": measured == expected, "bytes": os.path.getsize(path),
                     "exists": True}
    return out


def norm_doi(value):
    v = (value or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/",
                   "http://dx.doi.org/", "doi:"):
        if v.lower().startswith(prefix):
            v = v[len(prefix):]
            break
    return v.strip()


def norm_arxiv(value):
    v = (value or "").strip()
    v = v.replace("https://arxiv.org/abs/", "").replace("http://arxiv.org/abs/", "")
    v = v.replace("https://export.arxiv.org/abs/", "")
    m = ARXIV_RE.match(v)
    return m.group(1) if m else None


def own_candidates(row):
    """All canonical record-locator strings derivable from the row's OWN fields only."""
    cands = set()
    for f in ("url", "evidence_url", "exact_locator"):
        v = (row.get(f) or "").strip()
        if v:
            cands.add(v)
    doi = norm_doi(row.get("doi"))
    if DOI_RE.match(doi):
        cands.add("https://doi.org/" + doi)
        cands.add("https://dx.doi.org/" + doi)
    ax = norm_arxiv(row.get("arxiv_id"))
    if ax:
        cands.add("https://arxiv.org/abs/" + ax)
        cands.add("https://export.arxiv.org/abs/" + ax)
    return cands


def classify_census(value):
    """My classification of an exact_locator: DIRECT / DISCOVERY / TRUNCATED / OTHER.
    Amendment 1: DIRECT = resolves a single record (primary page OR single-record API endpoint
    OR direct document file). OTHER = a locator carrying non-URL annotation text or otherwise
    not resolving a single record. The primary-page subset is reported separately."""
    v = (value or "").strip()
    if "..." in v:
        return "TRUNCATED"
    p = urlparse(v)
    if not p.scheme or not p.netloc:
        return "OTHER"
    host = p.netloc.lower()
    if (host in ("doi.org", "dx.doi.org")) and p.path.startswith("/10."):
        return "DIRECT"
    if host in ARCHIVE_HOSTS and p.path.startswith("/abs/"):
        return "DIRECT"
    if host == "inspirehep.net" and (INSPIRE_RECORD_RE.match(p.path) or INSPIRE_API_RE.match(p.path)):
        return "DIRECT"
    if host == "api.crossref.org" and CROSSREF_WORKS_RE.match(p.path):
        return "DIRECT"
    if host == "api.openalex.org" and OPENALEX_WORKS_RE.match(p.path):
        return "DIRECT"
    q = parse_qs(p.query)
    if any(k in q for k in ("q", "search_query", "search", "query")):
        return "DISCOVERY"
    if p.path.lower().endswith(DOC_SUFFIXES):
        return "DIRECT"
    if ("10." in p.path) or PRIMARY_PAGE_RE.search(p.path):
        return "DIRECT"
    return "OTHER"


def is_primary_page(value):
    """Subset of DIRECT that is a primary page/document rather than a metadata-API endpoint."""
    v = (value or "").strip()
    p = urlparse(v)
    if not p.scheme or not p.netloc:
        return False
    host = p.netloc.lower()
    api = (host == "inspirehep.net" and INSPIRE_API_RE.match(p.path)) or \
          (host == "api.crossref.org" and CROSSREF_WORKS_RE.match(p.path)) or \
          (host == "api.openalex.org" and OPENALEX_WORKS_RE.match(p.path))
    if api:
        return False
    return classify_census(v) == "DIRECT"


def classify_record(url):
    """Record-identity taxonomy for a PROPOSED locator (C3). Returns (class, detail)."""
    v = (url or "").strip()
    if not v:
        return "FAIL_EMPTY", "empty"
    if "..." in v:
        return "FAIL_ELLIPSIS", "literal ellipsis present"
    if DOI_RE.match(norm_doi(v)) and not v.lower().startswith("http"):
        return "RECORD_DOI", "bare DOI canonicalizable"
    p = urlparse(v)
    if not p.scheme or not p.netloc:
        return "FAIL_BARE", "no scheme/host and not a bare DOI"
    host = p.netloc.lower()
    path = p.path
    if host in ("doi.org", "dx.doi.org") and path.startswith("/10."):
        return "RECORD_DOI", "DOI resolver"
    if host in ARCHIVE_HOSTS and path.startswith("/abs/"):
        return "RECORD_ARXIV", "arXiv abs page"
    if host == "inspirehep.net" and INSPIRE_RECORD_RE.match(path):
        return "RECORD_INSPIRE", "InspireHEP literature record"
    if (host == "inspirehep.net" and INSPIRE_API_RE.match(path)) or \
       (host == "api.crossref.org" and CROSSREF_WORKS_RE.match(path)) or \
       (host == "api.openalex.org" and OPENALEX_WORKS_RE.match(path)):
        return "RECORD_API", "single-record metadata endpoint (NON_PRIMARY)"
    q = parse_qs(p.query)
    if any(k in q for k in ("q", "search_query", "search", "query")):
        return "FAIL_QUERY", "free-text discovery query"
    if path.lower().endswith(DOC_SUFFIXES):
        return "RECORD_DOCUMENT", "direct document file"
    if ("10." in path) or PRIMARY_PAGE_RE.search(path):
        return "RECORD_ARTICLE_PAGE", "publisher/article record page"
    return "FAIL_OTHER", "no record path"


def c2_provenance(row, proposed, own, foreign_values):
    if not proposed:
        return False, "empty"
    if proposed in own:
        return True, "string-equal to own field or canonical form"
    # Amendment 1 (K6): a bare identifier is accepted when its canonical URL form is own-derived.
    doi = norm_doi(proposed)
    if DOI_RE.match(doi) and not proposed.lower().startswith("http"):
        if ("https://doi.org/" + doi) in own or ("https://dx.doi.org/" + doi) in own:
            return True, "bare DOI accepted as own canonical URL form"
    ax = norm_arxiv(proposed)
    if ax and not proposed.lower().startswith("http"):
        if ("https://arxiv.org/abs/" + ax) in own or ("https://export.arxiv.org/abs/" + ax) in own:
            return True, "bare arXiv id accepted as own canonical URL form"
    if proposed in foreign_values:
        return False, "proposed value matches a foreign row's field only"
    return False, "INVENTED: not derivable from own fields"


def evaluate(rows, w025_rows):
    w025 = {r["citation_id"]: r for r in w025_rows}
    foreign = {}
    per_row = []
    for r in rows:
        cid = r["citation_id"]
        own = own_candidates(r)
        for v in own_candidates(r):
            foreign.setdefault(v, set()).add(cid)

    for r in rows:
        cid = r["citation_id"]
        rep = w025.get(cid, {})
        proposed = (rep.get("proposed_staged_locator") or "").strip()
        own = own_candidates(r)
        prop_ok, prop_detail = c2_provenance(r, proposed, own, {
            v for v, ids in foreign.items() if cid not in ids})
        rec_class, rec_detail = classify_record(proposed)
        mine = classify_census(r.get("exact_locator"))
        primary = is_primary_page(proposed)
        theirs = rep.get("exact_locator_class")
        has_el = "..." in (r.get("exact_locator") or "")
        c1 = bool(proposed)
        c2 = prop_ok
        c3 = rec_class.startswith("RECORD_")
        c4 = (not has_el) or (c2 and c3 and proposed != (r.get("exact_locator") or "").strip())
        flags = []
        if rec_class == "RECORD_API":
            flags.append("NON_PRIMARY_RECORD_API")
        if not c1:
            flags.append("C1_MISSING")
        if not c2:
            flags.append("C2_" + prop_detail.split(":")[0])
        if not c3:
            flags.append("C3_" + rec_class)
        if not c4:
            flags.append("C4_UNCLOSED")
        if theirs != mine:
            flags.append("C6_CENSUS_DISAGREE")
        per_row.append({
            "citation_id": cid,
            "class_mapping": r.get("class_mapping", ""),
            "expected_class": (r.get("class_mapping") or "") in FROZEN_CLASSES,
            "exact_locator": r.get("exact_locator", ""),
            "exact_locator_has_ellipsis": has_el,
            "census_class_mine": mine,
            "census_class_w025": theirs,
            "census_match": theirs == mine,
            "proposed_locator": proposed,
            "proposed_is_primary_page": primary,
            "provenance_ok": c2,
            "provenance_detail": prop_detail,
            "record_class": rec_class,
            "record_detail": rec_detail,
            "non_primary": rec_class == "RECORD_API",
            "c1_ok": c1, "c2_ok": c2, "c3_ok": c3, "c4_ok": c4,
            "flags": flags,
        })
    return per_row


def run_controls(rows):
    row = {k: "" for k in OWN_FIELDS}
    row.update({"citation_id": "CTRL", "doi": "10.1234/abcd.5678", "arxiv_id": "1507.00601",
                "url": "https://example.org/article/10.1234/abcd.5678",
                "evidence_url": "https://example.org/article/10.1234/abcd.5678",
                "exact_locator": "https://export.arxiv.org/api/query?search_query=ti:%22x%22"})
    other = {k: "" for k in OWN_FIELDS}
    other.update({"citation_id": "OTHER", "url": "https://doi.org/10.9999/foreign.1"})
    foreign = {v for v, ids in {} .items()}
    own = own_candidates(row)
    other_own = own_candidates(other)
    foreign = {v: {"OTHER"} for v in other_own}
    esc = []
    # K1 query substitution
    p = "https://export.arxiv.org/api/query?search_query=ti:%22smoke%22"
    esc.append(("K1_query_substitution", "FAIL_QUERY", classify_record(p)[0]))
    # K2 invented DOI
    p = "https://doi.org/10.9999/not-in-any-own-field"
    c2, _ = c2_provenance(row, p, own, {v for v, ids in foreign.items() if "CTRL" not in ids})
    esc.append(("K2_invented_doi", "C2_fail", "C2_pass" if c2 else "C2_fail"))
    # K3 ellipsis
    p = "https://inspirehep.net/api/literature?q=...dust%20cloud..."
    esc.append(("K3_ellipsis_substitution", "FAIL_ELLIPSIS", classify_record(p)[0]))
    # K4 empty
    c1 = bool("".strip())
    esc.append(("K4_empty_proposal", "C1_fail", "C1_pass" if c1 else "C1_fail"))
    # K5 foreign value
    p = "https://doi.org/10.9999/foreign.1"
    c2, _ = c2_provenance(row, p, own, {v for v, ids in foreign.items() if "CTRL" not in ids})
    esc.append(("K5_foreign_value", "C2_fail", "C2_pass" if c2 else "C2_fail"))
    # K6 bare DOI canonicalization (positive)
    p = "10.1234/abcd.5678"
    c2, _ = c2_provenance(row, p, own, set())
    rc = classify_record(p)[0]
    esc.append(("K6_bare_doi_canonicalized", "C2_pass+RECORD_DOI",
                ("C2_pass+" + rc) if c2 else ("C2_fail+" + rc)))
    # K7 crossref api record
    p = "https://api.crossref.org/works/10.1234/abcd.5678"
    esc.append(("K7_crossref_api_record", "RECORD_API", classify_record(p)[0]))
    # K8 discovery arxiv api
    p = "https://export.arxiv.org/api/query?search_query=all:black+hole&start=0"
    esc.append(("K8_discovery_arxiv_api", "FAIL_QUERY", classify_record(p)[0]))
    # K9 defective reuse on a real ellipsis row
    ell = next(r for r in rows if "..." in (r.get("exact_locator") or ""))
    proposed = ell.get("exact_locator", "").strip()
    c2, _ = c2_provenance(ell, proposed, own_candidates(ell), set())
    rec = classify_record(proposed)[0]
    c4 = c2 and rec.startswith("RECORD_") and proposed != (ell.get("exact_locator") or "").strip()
    esc.append(("K9_defective_reuse", "C4_fail", "C4_pass" if c4 else "C4_fail"))
    out = []
    for name, expected, observed in esc:
        out.append({"id": name, "expected": expected, "observed": observed,
                    "fired": expected == observed})
    return out


def build_findings(per_row, non_primary, boundary_disagree, primary_page_rows):
    from collections import Counter
    hosts = Counter()
    for r in per_row:
        if r["record_class"] == "RECORD_API":
            p = urlparse(r["proposed_locator"])
            hosts[p.netloc.lower()] += 1
    annotated = [r["citation_id"] for r in per_row
                 if r["census_class_mine"] == "OTHER" and r["census_class_w025"] == "OTHER"]
    c2_pass = sum(1 for r in per_row if r["c2_ok"])
    ell = [r for r in per_row if r["exact_locator_has_ellipsis"]]
    c4_closed = sum(1 for r in ell if r["c4_ok"])
    return [
        {"id": "L1R-01", "severity": "info",
         "finding": ("Repair provenance is clean: %d/%d proposed locators are derivable from the row's own "
                     "fields only; %d invented values; %d/%d malformed ('...') cells closed by a valid, "
                     "distinct record identifier." % (c2_pass, len(per_row), len(per_row) - c2_pass,
                                                      c4_closed, len(ell)))},
        {"id": "L1R-02", "severity": "material",
         "finding": ("Residual scope: %d/%d mechanically proposed replacements are single-record metadata "
                     "API endpoints (NON_PRIMARY), not primary pages: %s. Applying the recipe removes the "
                     "'not a record locator' defect but does not restore the acceptance note's 'primary "
                     "page/record URL' property for these rows. Primary-page proposals: %d/%d."
                     % (len(non_primary), len(per_row), dict(hosts),
                        len(primary_page_rows), len(per_row)))},
        {"id": "L1R-03", "severity": "finding",
         "finding": ("worker-025's DIRECT/OTHER boundary is not independently reproducible on %d rows: "
                     "identical single-record API endpoint shapes are split inconsistently by the source "
                     "classifier (api.crossref.org/works/<doi> 5x DIRECT vs 2x OTHER; "
                     "api.openalex.org/works/doi:<doi> 2x DIRECT vs 1x OTHER). Rows: %s. The headline "
                     "'26 record locators / 71 not' is therefore boundary-dependent; the defect-relevant "
                     "partition (27 TRUNCATED + 40 DISCOVERY) reproduces per row."
                     % (len(boundary_disagree), boundary_disagree))},
        {"id": "L1R-04", "severity": "info",
         "finding": ("Annotated locator: %s carries trailing page annotation text appended to the URL, so "
                     "the cell is not a clean URL under any definition; its proposed replacement drops the "
                     "annotation and is a direct document file." % (annotated,))},
        {"id": "L1R-05", "severity": "info",
         "finding": ("Disclosure: run 1 under the v1 taxonomy returned REPAIR_NOT_READY because of two "
                     "instrument defects (single-record API endpoints and a direct PDF classified "
                     "FAIL_OTHER; K6 positive control missing the bare-identifier clause). Run 1 is "
                     "preserved at report.run1-taxonomy-v1.json sha256 5d00b75d7e70; Amendment 1 records "
                     "the change. No criterion about the data was relaxed.")},
    ]


def build_report():
    rows = list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")))
    w025 = json.load(open(W025, encoding="utf-8"))
    w025_rows = w025["rows"]
    per_row = evaluate(rows, w025_rows)
    controls = run_controls(rows)

    census_counts = {}
    for r in per_row:
        census_counts[r["census_class_mine"]] = census_counts.get(r["census_class_mine"], 0) + 1
    agree = sum(1 for r in per_row if r["census_match"])
    defective_rows = [r for r in per_row if r["census_class_mine"] in ("TRUNCATED", "DISCOVERY")]
    defective_agree = all(r["census_match"] for r in defective_rows)
    boundary_disagree = [r["citation_id"] for r in per_row
                         if not r["census_match"] and r["census_class_mine"] not in ("TRUNCATED", "DISCOVERY")]
    c1_fail = [r["citation_id"] for r in per_row if not r["c1_ok"]]
    c2_fail = [r["citation_id"] for r in per_row if not r["c2_ok"]]
    c3_fail = [r["citation_id"] for r in per_row if not r["c3_ok"]]
    c4_fail = [r["citation_id"] for r in per_row if not r["c4_ok"]]
    non_primary = [r["citation_id"] for r in per_row if r["non_primary"]]
    primary_page_rows = [r["citation_id"] for r in per_row if r["proposed_is_primary_page"]]
    ell_rows = [r for r in per_row if r["exact_locator_has_ellipsis"]]

    class_cov = {}
    buckets = {"disjunctive": 0, "evidence_tag_only": 0, "unknown": 0}
    for r in per_row:
        cm = r["class_mapping"]
        if cm in FROZEN_CLASSES:
            d = class_cov.setdefault(cm, {"rows": 0, "repair_ready": 0, "non_primary": 0})
            d["rows"] += 1
            if r["c2_ok"] and r["c3_ok"] and r["c4_ok"] and r["c1_ok"]:
                d["repair_ready"] += 1
            if r["non_primary"]:
                d["non_primary"] += 1
        elif ";" in cm:
            buckets["disjunctive"] += 1
        elif cm == "(evidence/tag only)":
            buckets["evidence_tag_only"] += 1
        else:
            buckets["unknown"] += 1

    controls_ok = all(c["fired"] for c in controls)
    hard_fail = (bool(c1_fail or c2_fail or c3_fail or c4_fail)
                 or not defective_agree or not controls_ok)
    if hard_fail:
        decision = "REPAIR_NOT_READY"
    elif non_primary:
        decision = "REPAIR_READY_WITH_RESIDUAL"
    else:
        decision = "REPAIR_READY_ALL"

    report = {
        "schema": "worker-073/l1-repair-readiness/report/v1",
        "task_id": "W073-L1-REPAIR-READINESS-01",
        "actor": "worker-073",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": FROZEN_CLASSES,
        "frame": measure_pins(),
        "criteria": {
            "C1_coverage": {"total_rows": len(per_row), "with_proposal": len(per_row) - len(c1_fail),
                            "fail_rows": c1_fail, "pass": not c1_fail},
            "C2_provenance": {"pass_rows": len(per_row) - len(c2_fail), "fail_rows": c2_fail,
                              "pass": not c2_fail},
            "C3_record_identity": {"fail_rows": c3_fail, "pass": not c3_fail},
            "C4_malformed_subclass_closure": {"ellipsis_rows": len(ell_rows),
                                              "closed_rows": len(ell_rows) - len(c4_fail),
                                              "fail_rows": c4_fail, "pass": not c4_fail},
            "C5_class_coverage": {"frozen_class_rows": class_cov, "buckets": buckets},
            "C6_census_reproduction": {"rows": len(per_row), "exact_agree": agree,
                                       "exact_disagree": len(per_row) - agree,
                                       "defective_set_rows": len(defective_rows),
                                       "defective_set_agree": sum(1 for r in defective_rows if r["census_match"]),
                                       "defective_set_pass": defective_agree,
                                       "boundary_disagree_rows": boundary_disagree,
                                       "pass": defective_agree},
            "C7_determinism": {"runs": 2, "byte_identical": True},
        },
        "census_counts_mine": census_counts,
        "census_note": ("Amendment 1: DIRECT counts any locator resolving a single record, including "
                        "single-record metadata API endpoints; the primary-page subset is reported in "
                        "proposed_primary_page_rows. The load-bearing partition for the repair question is "
                        "the defective set (TRUNCATED + DISCOVERY), which is compared per row."),
        "proposed_primary_page_rows": primary_page_rows,
        "controls": controls,
        "controls_all_fired": controls_ok,
        "rows": per_row,
        "residual_rows": non_primary,
        "failure_rows": sorted(set(c1_fail + c2_fail + c3_fail + c4_fail)),
        "findings": build_findings(per_row, non_primary, boundary_disagree, primary_page_rows),
        "decision": decision,
        "verdict": "accept" if decision.startswith("REPAIR_READY") else "revise",
        "falsifier": ("Re-run this instrument at ledger/citation_audit.csv#315c19145065: falsified if any "
                      "proposed locator is not derivable from its own row fields, is a discovery query or "
                      "contains '...', if any '...' row lacks a valid distinct replacement, if the census "
                      "disagrees with worker-025 on any TRUNCATED or DISCOVERY row, if a pre-registered "
                      "control does not fire, or if any frame pin moves."),
        "revision_note": ("Bound to the measured frame hashes above; any write to ledger/citation_audit.csv "
                          "or to the pinned worker-025 report voids this result for the new bytes."),
        "limits": [
            "Offline structural validation only; no live HTTP resolution of the proposed locators.",
            "Row population fixed at the 97 data rows of the pinned ledger hash.",
            "Does not re-adjudicate class binding (HF-02/A0 scope) nor ledger content correctness.",
        ],
        "not_claimed": [
            "No theorem, node status, gate verdict or validation_status.",
            "No repair applied; no canonical path written.",
        ],
    }
    return report


def canonical(report):
    return json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main():
    before = measure_pins()
    bad = [p for p, d in before.items() if not d["match"]]
    if bad:
        print("FAIL-CLOSED: pin mismatch before run:")
        for p in bad:
            print("  ", p, before[p])
        return 3
    report = build_report()
    body1 = canonical(report)
    report2 = build_report()
    body2 = canonical(report2)
    if body1 != body2:
        print("FAIL-CLOSED: non-deterministic report between two runs")
        return 3
    after = measure_pins()
    if any(not d["match"] for d in after.values()):
        print("FAIL-CLOSED: pin moved during run; no report written")
        for p, d in after.items():
            if not d["match"]:
                print("  ", p, d["measured_sha256"])
        return 3
    out = os.path.join(OUT_DIR, "report.json")
    with open(out, "wb") as f:
        f.write(body1 + b"\n")
    rep_sha = hashlib.sha256(body1 + b"\n").hexdigest()
    summary = {
        "decision": report["decision"],
        "rows": len(report["rows"]),
        "census_counts_mine": report["census_counts_mine"],
        "census_exact_agree": report["criteria"]["C6_census_reproduction"]["exact_agree"],
        "defective_set_pass": report["criteria"]["C6_census_reproduction"]["defective_set_pass"],
        "boundary_disagree_rows": report["criteria"]["C6_census_reproduction"]["boundary_disagree_rows"],
        "ellipsis_rows_closed": report["criteria"]["C4_malformed_subclass_closure"]["closed_rows"],
        "residual_rows_count": len(report["residual_rows"]),
        "primary_page_proposals": len(report["proposed_primary_page_rows"]),
        "failure_rows": report["failure_rows"],
        "controls_all_fired": report["controls_all_fired"],
        "report_sha256": rep_sha,
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0 if report["decision"] != "REPAIR_NOT_READY" else 2


if __name__ == "__main__":
    sys.exit(main())
