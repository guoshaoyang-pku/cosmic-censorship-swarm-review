#!/usr/bin/env python3
"""W062-SCC-LOCATOR-RESOLVABILITY-01 -- SCC-side `exact_locator` resolvability map.

Bounded class-bound task taken by worker-062 (no inbox card exists for this slot).
Node L1 / gate G-LIT / primary class AF-SCC-C0-VAC-GEN.

PRE-REGISTRATION (written before the classification was run)
------------------------------------------------------------
Input pin: `ledger/citation_audit.csv` sha256
315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9 (the frozen L1 hash).
The instrument exits 3 if the file on disk does not match this pin.

Scope (fixed before running): every row whose `class_mapping` contains at least one
SCC token (`AF-SCC-C0-VAC-GEN` or `AF-SCC-C2-VAC-GEN`).  This is disjoint from
worker-050's published scope (`class_mapping` exactly `AF-WCC-VAC-GEN`, 12 rows,
`artifacts/worker-050/wcc_locator_resolution/resolution.json`).

Only the `exact_locator` COLUMN is under test -- whether it addresses one
bibliographic record.  No claim is made about the quality of any citation, and no
ledger cell is edited.

Classification rules (mutually exclusive, evaluated in this order):
  1. `absent`                  -- empty/whitespace field.
  2. `elided_or_truncated`     -- contains a literal ellipsis ("..." or U+2026).
  3. `non_url`                 -- does not start with http:// or https://.
  4. `record_locator`          -- URL that addresses a single record:
        arxiv.org/abs/<id>                      (including old-style math/gr-qc ids)
        doi.org|dx.doi.org/10.<reg>/<suffix>
        api.openalex.org/works/doi:<doi>|W<id>
        export.arxiv.org/api/query?...id_list=<ids>
        inspirehep.net/literature/<digits>  and /api/literature/<digits>
        api.crossref.org/works/10.<reg>/<suffix>
        a direct document file ending in .pdf/.ps/.djvu/.tex
        any publisher path embedding /10.<reg>/<suffix>
  5. `search_or_query_endpoint` -- parsed query carries one of
        q, query, search, filter, terms, keyword(s), text, search_query
     or the raw string carries `sortBy=`, or the path is a search/query endpoint.
  6. `other_http`              -- any other http(s) URL (kept as weak, conservatively).
`direct = (category == "record_locator")`; every non-direct row is `weak`.

Repair proposal: first DIRECT candidate, in the fixed priority order
`evidence_url`, `doi` (as https://doi.org/<doi>), `arxiv_id` (as
https://arxiv.org/abs/<id>), `url`.  All candidates considered are recorded, so a
reviewer can re-rank them.  No candidate is invented: each is a value already in
the row.

Controls with teeth (the run exits 4 if any harness control fails):
  C1 positive  -- 7 synthetic record locators must all classify direct.
  C2 negative  -- 7 synthetic search/query/truncated/empty locators must all
                  classify non-direct (mutant control).
  C3 scope     -- SCC-side count is 34, every selected row carries an SCC token,
                  and the citation_id intersection with the exact-match WCC scope
                  is empty.
  C4 hash guard-- a byte-mutated temp copy of the ledger must make the CLI exit 3.
  C5 cross-instrument -- per-row agreement with worker-050's independently
                  authored WCC map on the 12 exact-match WCC rows (needs_repair
                  must equal weak) -- a different author, same pinned ledger.

Reported (not exit-level): a global reproduction over all 97 rows against
astra-lead-literature's published adjudication counts (67 weak / 30 direct) and
its 43 distinct weak locator strings / worst-case sharing 7.  Those aggregate
numbers were public when this instrument was authored (disclosed); the per-row
classification was computed from the CSV only and the lead's row-level list was
not consulted.

No live fetch is attempted: environment egress from this shell timed out during a
pre-run probe, so every row is marked `unfetched` and no resolvability claim is
made beyond the locator's syntactic shape.  Re-fetch is the declared next
falsifier.

Exit codes: 0 ok, 3 ledger hash != pin, 4 a control failed.
Authority: worker evidence only; not a ledger edit, not a gate verdict, not a
validation_status, not a node completion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlsplit

TZ = timezone(timedelta(hours=8))
PINNED_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
SCC_TOKENS = ("AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN")
PRIMARY_CLASS = "AF-SCC-C0-VAC-GEN"
WCC_EXACT = "AF-WCC-VAC-GEN"
WORKER050_MAP = "artifacts/worker-050/wcc_locator_resolution/resolution.json"

DIRECT_RULES = (
    ("arxiv_abs", re.compile(r"^https?://(?:www\.)?arxiv\.org/abs/[A-Za-z0-9][A-Za-z0-9.\-_/]*$", re.I)),
    ("doi_org", re.compile(r"^https?://(?:dx\.)?doi\.org/10\.\d{4,9}/\S+$", re.I)),
    ("openalex_work_record", re.compile(r"^https?://api\.openalex\.org/works/(?:doi:10\.\d{4,9}/\S+|W\d+)$", re.I)),
    ("arxiv_id_list_record", re.compile(r"^https?://export\.arxiv\.org/api/query\?[^#]*\bid_list=[^&\s]+$", re.I)),
    ("inspirehep_literature_record", re.compile(r"^https?://inspirehep\.net/(?:api/)?literature/\d+$", re.I)),
    ("crossref_work_record", re.compile(r"^https?://api\.crossref\.org/works/10\.\d{4,9}/\S+$", re.I)),
    ("document_file", re.compile(r"^https?://[^\s?#]+\.(?:pdf|ps|djvu|tex)$", re.I)),
    ("publisher_doi_path", re.compile(r"^https?://[^\s?]+/10\.\d{4,9}/[^\s?#]+", re.I)),
)
QUERY_KEYS = {"q", "query", "search", "filter", "terms", "keyword", "keywords", "text", "search_query"}

C1_POSITIVE = [
    ("arxiv-new", "https://arxiv.org/abs/2201.12294"),
    ("arxiv-old", "https://arxiv.org/abs/gr-qc/0307013"),
    ("doi", "https://doi.org/10.1007/s00023-022-01216-7"),
    ("openalex", "https://api.openalex.org/works/doi:10.4007/annals.2003.158.875"),
    ("arxiv-id-list", "https://export.arxiv.org/api/query?id_list=2201.12294"),
    ("inspirehep", "https://inspirehep.net/literature/622602"),
    ("publisher-doi-path", "https://comptes-rendus.academie-sciences.fr/mecanique/articles/10.5802/crmeca.284/"),
]
C2_NEGATIVE = [
    ("arxiv-search", "https://export.arxiv.org/api/query?search_query=ti:%22inextendibility%22+AND+all:Schwarzschild"),
    ("openalex-search", "https://api.openalex.org/works?filter=title.search:inextendibility"),
    ("inspirehep-api-search", "https://inspirehep.net/api/literature?q=weak+null+singularities&sort=mostrecent"),
    ("crossref-search", "https://api.crossref.org/works?query.bibliographic=black+hole+stability"),
    ("sortby-only", "https://export.arxiv.org/api/query?sortBy=submittedDate&max_results=20"),
    ("truncated", "https://inspirehep.net/api/literature?q=...interior%20of%20charged%20black%20holes..."),
    ("empty", ""),
]

CATEGORY_ORDER = (
    "absent",
    "elided_or_truncated",
    "non_url",
    "record_locator",
    "search_or_query_endpoint",
    "other_http",
)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def classify_locator(locator: str) -> dict:
    s = (locator or "").strip()
    if not s:
        return {"category": "absent", "direct": False, "reason": "empty field"}
    if "..." in s or "\u2026" in s:
        return {"category": "elided_or_truncated", "direct": False, "reason": "literal ellipsis in URL"}
    if not re.match(r"^https?://", s, re.I):
        return {"category": "non_url", "direct": False, "reason": "not an http(s) URL"}
    for name, rx in DIRECT_RULES:
        if rx.match(s):
            return {"category": "record_locator", "direct": True, "rule": name, "reason": f"single-record pattern {name}"}
    parts = urlsplit(s)
    keys = {k.lower() for k, _ in parse_qsl(parts.query, keep_blank_values=True)}
    hit = sorted(keys & QUERY_KEYS)
    if hit or re.search(r"[?&]sortBy=", s) or re.search(r"/(?:api/)?(?:search|query)(?:[/?]|$)", parts.path, re.I):
        reason = "query key(s): " + ",".join(hit) if hit else "query/sort endpoint"
        return {"category": "search_or_query_endpoint", "direct": False, "reason": reason}
    return {"category": "other_http", "direct": False, "reason": "http URL with no single-record pattern"}


def load_rows(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def class_tokens(mapping: str) -> list:
    return [t.strip() for t in re.split(r"[;,]", mapping or "") if t.strip()]


ANNOTATION_RX = re.compile(r"\s*\([^()]*\)\s*$")


def strip_trailing_annotation(locator: str) -> str:
    """Drop one trailing parenthetical page/section annotation from a cell value.

    Used only for the declared sensitivity analysis of the lead-adjudication
    convention; the primary classification is applied to the raw cell.
    """
    s = (locator or "").strip()
    m = ANNOTATION_RX.search(s)
    return s[: m.start()].strip() if m else s


def select_scc(rows: list) -> list:
    out = []
    for r in rows:
        toks = class_tokens(r.get("class_mapping", ""))
        if any(t in SCC_TOKENS for t in toks):
            out.append(r)
    return out


def select_wcc_exact(rows: list) -> list:
    return [r for r in rows if (r.get("class_mapping") or "").strip() == WCC_EXACT]


def candidates_for(row: dict) -> list:
    out = []
    for source in ("evidence_url", "doi", "arxiv_id", "url"):
        value = (row.get(source) or "").strip()
        if not value:
            continue
        if source == "doi":
            value = "https://doi.org/" + value
        elif source == "arxiv_id":
            value = "https://arxiv.org/abs/" + value
        c = classify_locator(value)
        out.append({"source": source, "value": value, "category": c["category"],
                    "direct": c["direct"], "rule": c.get("rule")})
    return out


def propose_for(row: dict):
    cands = candidates_for(row)
    for c in cands:
        if c["direct"]:
            return c, cands
    return None, cands


def classify_rows(rows: list) -> list:
    out = []
    for r in rows:
        loc = r.get("exact_locator", "")
        c = classify_locator(loc)
        proposal, cands = (None, [])
        if not c["direct"]:
            proposal, cands = propose_for(r)
        if c["direct"]:
            verdict = "NO_ACTION_NEEDED"
        elif proposal:
            verdict = "PROPOSED_REPLACEMENT"
        else:
            verdict = "REPAIR_UNAVAILABLE"
        out.append({
            "citation_id": r.get("citation_id"),
            "bibkey": r.get("bibkey"),
            "class_mapping": r.get("class_mapping"),
            "class_tokens": class_tokens(r.get("class_mapping", "")),
            "verification_method": r.get("verification_method"),
            "current_exact_locator": loc,
            "category": c["category"],
            "is_direct_record_locator": c["direct"],
            "is_weak": not c["direct"],
            "reason": c["reason"],
            "rule": c.get("rule"),
            "evidence_url": r.get("evidence_url"),
            "doi": r.get("doi"),
            "arxiv_id": r.get("arxiv_id"),
            "url": r.get("url"),
            "candidates_considered": cands,
            "proposed_exact_locator": (proposal or {}).get("value"),
            "proposed_locator_source": (proposal or {}).get("source"),
            "repair_verdict": verdict,
            "fetch": None,
            "fetch_status": "unfetched_no_egress",
        })
    return out


def controls_suite(rows: list, scc_rows: list, scc_classified: list, global_classified: list,
                   root: str, ledger: str) -> dict:
    controls = {}

    c1_fail = [label for label, url in C1_POSITIVE if not classify_locator(url)["direct"]]
    controls["C1_positive_record_locators"] = {
        "pass": not c1_fail, "cases": len(C1_POSITIVE), "failures": c1_fail,
        "detail": "synthetic single-record URLs must all classify record_locator",
    }

    c2_fail = [label for label, url in C2_NEGATIVE if classify_locator(url)["direct"]]
    controls["C2_negative_mutants_not_direct"] = {
        "pass": not c2_fail, "cases": len(C2_NEGATIVE), "failures": c2_fail,
        "detail": "synthetic search/query/truncated/empty locators must not classify record_locator",
    }

    wcc_exact = select_wcc_exact(rows)
    scc_ids = {r["citation_id"] for r in scc_classified}
    wcc_ids = {r["citation_id"] for r in wcc_exact}
    all_scc_tagged = all(any(t in SCC_TOKENS for t in r["class_tokens"]) for r in scc_classified)
    c3_pass = (len(scc_classified) == 34 and not (scc_ids & wcc_ids) and all_scc_tagged)
    controls["C3_scope_and_disjointness"] = {
        "pass": c3_pass,
        "scc_rows": len(scc_classified),
        "wcc_exact_rows": len(wcc_exact),
        "intersection": sorted(scc_ids & wcc_ids),
        "every_row_carries_scc_token": all_scc_tagged,
        "detail": "SCC-side scope must be 34 rows and disjoint from worker-050's exact-match WCC scope",
    }

    guard_rc = None
    guard_err = None
    try:
        with open(ledger, "rb") as f:
            blob = bytearray(f.read())
        idx = blob.find(b"SRC-")
        if idx < 0:
            idx = 0
        blob[idx] = blob[idx] ^ 0x01
        tmpdir = tempfile.mkdtemp(prefix="w062_guard_")
        tmp_ledger = os.path.join(tmpdir, "citation_audit.csv")
        with open(tmp_ledger, "wb") as f:
            f.write(bytes(blob))
        tmp_out = os.path.join(tmpdir, "out.json")
        proc = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--ledger", tmp_ledger,
             "--expect-pin", "--out", tmp_out],
            capture_output=True, text=True, timeout=120,
        )
        guard_rc = proc.returncode
    except Exception as exc:  # pragma: no cover - environment guard
        guard_err = f"{type(exc).__name__}: {exc}"
    controls["C4_hash_guard_teeth"] = {
        "pass": guard_rc == 3, "mutated_exit_code": guard_rc, "expected_exit_code": 3,
        "error": guard_err,
        "detail": "a byte-mutated ledger copy must make the CLI exit 3 before classification",
    }

    c5 = {"pass": False, "compared": 0, "agree": 0, "disagreements": [],
          "source": WORKER050_MAP, "error": None}
    try:
        w050 = json.load(open(os.path.join(root, WORKER050_MAP)))
        w050_rows = {r["citation_id"]: r for r in w050.get("rows", [])}
        mine_all = {r["citation_id"]: r for r in global_classified}
        for cid in sorted(wcc_ids & set(w050_rows)):
            c5["compared"] += 1
            theirs_weak = bool(w050_rows[cid].get("needs_repair"))
            mine_weak = bool(mine_all[cid]["is_weak"]) if cid in mine_all else None
            if mine_weak is None:
                c5["disagreements"].append({"citation_id": cid, "reason": "not classified by w062"})
            elif mine_weak == theirs_weak:
                c5["agree"] += 1
            else:
                c5["disagreements"].append({
                    "citation_id": cid, "worker050_needs_repair": theirs_weak,
                    "w062_is_weak": mine_weak,
                    "current_locator": mine_all[cid]["current_exact_locator"],
                })
        c5["pass"] = c5["compared"] == 12 and not c5["disagreements"]
    except Exception as exc:
        c5["error"] = f"{type(exc).__name__}: {exc}"
    controls["C5_cross_instrument_worker050_wcc12"] = c5

    controls["all_harness_controls_pass"] = all(
        controls[k]["pass"] for k in ("C1_positive_record_locators", "C2_negative_mutants_not_direct",
                                      "C3_scope_and_disjointness", "C4_hash_guard_teeth",
                                      "C5_cross_instrument_worker050_wcc12")
    )
    return controls


def build_report(ledger: str, root: str) -> dict:
    measured = sha256_file(ledger)
    rows = load_rows(ledger)
    scc_rows = select_scc(rows)
    scc_classified = classify_rows(scc_rows)

    cats = {c: sum(1 for r in scc_classified if r["category"] == c) for c in CATEGORY_ORDER}
    weak = [r for r in scc_classified if r["is_weak"]]
    direct = [r for r in scc_classified if r["is_direct_record_locator"]]
    c0_rows = [r for r in scc_classified if PRIMARY_CLASS in r["class_tokens"]]

    weak_locators = [r["current_exact_locator"] for r in weak]
    shared = {}
    for loc in weak_locators:
        shared[loc] = shared.get(loc, 0) + 1
    shared_nonzero = {k: v for k, v in shared.items() if k}
    worst = max(shared_nonzero.values()) if shared_nonzero else 0
    worst_locators = sorted([k for k, v in shared_nonzero.items() if v == worst]) if worst else []

    global_classified = classify_rows(rows)
    g_weak = sum(1 for r in global_classified if r["is_weak"])
    g_direct = sum(1 for r in global_classified if r["is_direct_record_locator"])
    g_weak_locs = [r["current_exact_locator"] for r in global_classified if r["is_weak"]]
    g_distinct = len({x for x in g_weak_locs if x})
    g_worst = max([g_weak_locs.count(x) for x in {y for y in g_weak_locs if y}] or [0])

    lead_claim = {"weak_expected": 67, "direct_expected": 30,
                  "distinct_weak_locators_expected": 43, "worst_sharing_expected": 7}
    relaxed_rows = []
    for r in rows:
        raw = r.get("exact_locator", "")
        stripped = strip_trailing_annotation(raw)
        if stripped != raw:
            c = classify_locator(stripped)
            relaxed_rows.append({"citation_id": r.get("citation_id"), "raw": raw,
                                 "stripped": stripped, "category": c["category"],
                                 "direct_under_stripping": c["direct"]})
    r_weak_locs = []
    for r in rows:
        if not classify_locator(strip_trailing_annotation(r.get("exact_locator", "")))["direct"]:
            r_weak_locs.append(r.get("exact_locator", ""))
    r_distinct = len({x for x in r_weak_locs if x})
    r_worst = max([r_weak_locs.count(x) for x in {y for y in r_weak_locs if y}] or [0])
    global_repro = {
        "measured": {"weak": g_weak, "direct": g_direct,
                     "weak_plus_direct": g_weak + g_direct,
                     "distinct_weak_locators": g_distinct, "worst_sharing": g_worst},
        "lead_adjudication_claim": lead_claim,
        "matches": (g_weak == 67 and g_direct == 30),
        "annotation_stripped_sensitivity": {
            "rule": "strip one trailing parenthetical annotation from the cell, then classify",
            "rows_affected": relaxed_rows,
            "measured": {"weak": len(r_weak_locs), "direct": len(rows) - len(r_weak_locs),
                         "distinct_weak_locators": r_distinct, "worst_sharing": r_worst},
            "matches_lead_aggregate": (len(r_weak_locs) == 67 and len(rows) - len(r_weak_locs) == 30
                                       and r_distinct == 43 and r_worst == 7),
            "adjudication": "the single strict/relaxed difference is SRC-090, whose exact_locator is a direct PDF "
                            "URL followed by a page annotation '(§1.3, p. 19)'; strict reading treats the cell as "
                            "not a URL, the lead's direct-record reading treats the URL part as the locator. Both "
                            "readings are defensible; the row is NOT in the SCC scope, so the SCC table is unaffected.",
        },
        "disclosure": "the lead's aggregate counts were public before this instrument was authored; "
                      "the per-row classification was computed from the CSV only.",
    }

    controls = controls_suite(rows, scc_rows, scc_classified, global_classified, root, ledger)

    report = {
        "schema_version": "w062/1",
        "artifact_id": "W062-SCC-LOCATOR-RESOLVABILITY-01",
        "artifact_type": "class_bound_locator_resolvability_map",
        "actor": "worker-062",
        "created_at": now_iso(),
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": PRIMARY_CLASS,
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "authority": ("decision support for the G-LIT 'ledger rows have resolvable locators' criterion. "
                      "NOT a ledger edit, NOT a gate verdict, NOT a validation_status, NOT a node completion. "
                      "The canonical ledger remains owned by astra-lead-literature."),
        "pins": {
            "ledger/citation_audit.csv": {
                "sha256_pinned": PINNED_SHA256, "sha256_measured": measured,
                "matches_pin": measured == PINNED_SHA256,
                "bytes": os.path.getsize(ledger), "rows": len(rows),
            }
        },
        "scope": {
            "selection_rule": "class_mapping contains AF-SCC-C0-VAC-GEN or AF-SCC-C2-VAC-GEN",
            "scc_rows": len(scc_classified),
            "primary_class_rows_AF_SCC_C0": len(c0_rows),
            "wcc_exact_match_rows": len(select_wcc_exact(rows)),
            "disjoint_from_worker050_wcc_exact_scope": not (
                {r["citation_id"] for r in scc_classified} & {r["citation_id"] for r in select_wcc_exact(rows)}),
            "column_under_test": "exact_locator",
        },
        "counts": {
            "direct_record_locator": len(direct),
            "weak": len(weak),
            "by_category": cats,
            "repair_proposed": sum(1 for r in weak if r["repair_verdict"] == "PROPOSED_REPLACEMENT"),
            "repair_unavailable": sum(1 for r in weak if r["repair_verdict"] == "REPAIR_UNAVAILABLE"),
            "weak_distinct_locator_strings": len(shared_nonzero),
            "weak_worst_sharing": worst,
            "weak_worst_locators": worst_locators,
            "weak_by_verification_method": {
                m: sum(1 for r in weak if r["verification_method"] == m)
                for m in sorted({r["verification_method"] for r in weak})
            },
        },
        "cross_checks": {
            "worker050_wcc12_per_row": controls["C5_cross_instrument_worker050_wcc12"],
            "global_all97_vs_lead_adjudication": global_repro,
        },
        "controls": controls,
        "rows": scc_classified,
        "fetched": False,
        "fetch_policy": ("no live fetch attempted: an egress probe from this shell timed out before the run, "
                         "so all rows are marked unfetched_no_egress and the report makes no claim that any "
                         "proposed locator resolves; re-fetch is the declared next falsifier."),
        "falsifiers": [
            "F1: any SCC-side row classified direct whose exact_locator does not address exactly one record voids that row's classification.",
            "F2: any SCC-side row classified weak whose exact_locator does address exactly one record voids that row's classification.",
            "F3: a re-fetch of a proposed locator that fails to return the cited work (title/author/year mismatch, HTTP >= 400) voids that proposal.",
            "F4: any drift of ledger/citation_audit.csv away from sha256 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9 voids the whole table and the global reproduction.",
            "F5: a rerun of classify_scc_locators.py at the pinned hash that produces different category or proposal fields falsifies reproducibility.",
        ],
        "next_falsifier": ("Re-fetch every proposed SCC-side locator with the originating ledger hash pinned; any "
                           "non-200/mismatch turns the corresponding row from PROPOSED_REPLACEMENT to unverified, "
                           "and any ledger revision voids the table. Independently re-classify a random sample of "
                           "the rows and compare category fields."),
        "scope_limit": ("Only the SCC-side 34 rows were fully classified and only the exact_locator field was "
                        "tested; the remaining 51 non-SCC rows enter only the aggregate global reproduction, not a "
                        "per-row verdict. No fetch was performed. This is one worker artifact; it cannot move a "
                        "node status or a gate."),
    }
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SCC-side exact_locator resolvability map (worker-062)")
    ap.add_argument("--ledger", default="ledger/citation_audit.csv")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="artifacts/worker-062/scc_locator_resolution/resolution.json")
    ap.add_argument("--expect-pin", action="store_true",
                    help="exit 3 unless --ledger matches the frozen sha256")
    args = ap.parse_args(argv)

    pinned = args.expect_pin or os.path.abspath(args.ledger) == os.path.abspath("ledger/citation_audit.csv")
    measured = sha256_file(args.ledger)
    if pinned and measured != PINNED_SHA256:
        print(f"HASH GUARD: {args.ledger} sha256 {measured} != pinned {PINNED_SHA256}", file=sys.stderr)
        return 3

    report = build_report(args.ledger, args.root)
    out = args.out
    if not os.path.isabs(out):
        out = os.path.join(args.root, out) if args.root != "." else out
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    c = report["controls"]
    print(json.dumps({
        "artifact_id": report["artifact_id"],
        "ledger_sha256": report["pins"]["ledger/citation_audit.csv"]["sha256_measured"],
        "scc_rows": report["scope"]["scc_rows"],
        "direct": report["counts"]["direct_record_locator"],
        "weak": report["counts"]["weak"],
        "repair_proposed": report["counts"]["repair_proposed"],
        "controls_pass": c["all_harness_controls_pass"],
        "global_reproduction_matches_lead": report["cross_checks"]["global_all97_vs_lead_adjudication"]["matches"],
        "global_relaxed_matches_lead": report["cross_checks"]["global_all97_vs_lead_adjudication"]["annotation_stripped_sensitivity"]["matches_lead_aggregate"],
        "out": out,
    }, indent=2))
    return 0 if c["all_harness_controls_pass"] else 4


if __name__ == "__main__":
    sys.exit(main())
