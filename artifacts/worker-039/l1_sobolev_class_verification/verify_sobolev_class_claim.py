#!/usr/bin/env python3
"""W039-L1-SOBOLEV-CLASS-01 — fails-closed primary-source check of the frozen schemas'
`regularity_class.sobolev_variant` citation claim (class-bound task, worker-039).

Claim under test (verbatim, frozen schemas F1/F2a/F2b):
  s: "s > 5/2"
  delta: "delta in (1/2, 1)"
  spaces: "h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}"
  status: "standard_choice; UNVERIFIED citation"

Sub-claims and pre-fixed decision rule (fixed before any verdict was computed):
  SC1 threshold      s > 5/2 for the local (classical) vacuum Cauchy problem on
                     asymptotically flat data.
                     SUPPORTED iff the KR quote set is found in the KR source.
  SC2 decay class    h - delta = O(r^-1), K = O(r^-2) (with the schema's derivative
                     counts) is the standard AF decay family.
                     PARTIALLY_SUPPORTED iff the LR rate/sigma quote set is found;
                     the LR statement uses strictly faster little-o rates and does not
                     enumerate derivative counts, so it cannot be a full match.
  SC3 weighted form  "h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}".
                     NOT_FOUND_IN_CHECKED_SET iff no exact normalization pattern is
                     present in any checked source AND at least one checked source
                     uses a different weighted-space convention (BI quote).
  SC4 delta range    "delta in (1/2, 1)" as part of the standard statement.
                     NOT_FOUND_IN_CHECKED_SET iff the interval pattern is absent.
  Overall             PARTIAL unless SC3 and SC4 are both SUPPORTED; on PARTIAL the
                     schema flag "UNVERIFIED citation" must be retained.

The script is read-only with respect to canonical artifacts; it writes only this task
directory.  It exits non-zero on any integrity or required-quote failure.  The verdict
itself is an evidence classification, not a theorem and not a gate verdict.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TZ = dt.timezone(dt.timedelta(hours=8))
CREATED_AT = dt.datetime.now(TZ).replace(microsecond=0).isoformat()

TASK_ID = "W039-L1-SOBOLEV-CLASS-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_ID = "L1"
GATE = "G-LIT"

SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]

SOURCES = [
    {
        "id": "KR2001",
        "path": "raw/kr2001_rough.html",
        "url": "https://ar5iv.labs.arxiv.org/html/math/0109173",
        "identifier": "arXiv:math/0109173v1",
        "title": "Rough solution for the Einstein Vacuum equations",
        "authors": "S. Klainerman, I. Rodnianski",
        "year": 2001,
        "venue": "arXiv preprint (no journal-ref or DOI on the arXiv record; the quoted statement attributes the classical result to [H-K-M])",
        "peer_reviewed": False,
        "used_for": ["SC1"],
    },
    {
        "id": "LR2005",
        "path": "raw/lr2005_wavecoord.html",
        "url": "https://ar5iv.labs.arxiv.org/html/math/0312479",
        "identifier": "arXiv:math/0312479v2",
        "title": "Global existence for the Einstein vacuum equations in wave coordinates",
        "authors": "H. Lindblad, I. Rodnianski",
        "year": 2005,
        "venue": "Commun. Math. Phys. 256:43-110 (2005), DOI 10.1007/s00220-004-1281-6",
        "peer_reviewed": True,
        "used_for": ["SC2"],
    },
    {
        "id": "BI2004",
        "path": "raw/bi2004_constraints.html",
        "url": "https://ar5iv.labs.arxiv.org/html/gr-qc/0405092",
        "identifier": "arXiv:gr-qc/0405092v1",
        "title": "The Constraint Equations",
        "authors": "R. Bartnik, J. Isenberg",
        "year": 2004,
        "venue": "review chapter preprint (no journal-ref or DOI on the arXiv record)",
        "peer_reviewed": False,
        "used_for": ["SC3-adjacent convention evidence"],
    },
    {
        "id": "BIERI2009",
        "path": "raw/bieri2009_ext.html",
        "url": "https://ar5iv.labs.arxiv.org/html/0904.0620",
        "identifier": "arXiv:0904.0620v2",
        "title": "An Extension of the Stability Theorem of the Minkowski Space in General Relativity",
        "authors": "L. Bieri",
        "year": 2009,
        "venue": "arXiv preprint sketch (no journal-ref or DOI on the arXiv record)",
        "peer_reviewed": False,
        "used_for": ["SC3-adjacent convention evidence"],
    },
]

# Required quote patterns (applied to the deterministic normalized text of the pinned source).
REQUIRED_QUOTES = {
    "SC1": [
        {
            "source": "KR2001",
            "label": "Theorem 1.1 threshold",
            "pattern": r"for some s\s*>\s*5\s*/\s*2",
            "locator": "KR2001, Theorem 1.1",
        },
        {
            "source": "KR2001",
            "label": "Remark 1.2 attribution to the classical result for asymptotically flat data",
            "pattern": r"Theorem 1\.1 implies the classical local existence result",
            "locator": "KR2001, Remark 1.2",
        },
        {
            "source": "KR2001",
            "label": "Remark 1.2 asymptotically flat data sets",
            "pattern": r"for asymptotically flat initial data sets",
            "locator": "KR2001, Remark 1.2",
        },
        {
            "source": "KR2001",
            "label": "Remark 1.2 s > 5/2 for the AF class",
            "pattern": r"and s\s*>\s*5\s*2",
            "locator": "KR2001, Remark 1.2",
        },
    ],
    "SC2": [
        {
            "source": "LR2005",
            "label": "AF data definition",
            "pattern": r"is asymptotically flat",
            "locator": "LR2005, Section 1 (Introduction)",
        },
        {
            "source": "LR2005",
            "label": "metric rate o(r^{-1-sigma})",
            "pattern": r"o\s*\u2061?\s*\(\s*r\s*−\s*1\s*−\s*σ\s*\)",
            "locator": "LR2005, Section 1, display before footnote 3",
        },
        {
            "source": "LR2005",
            "label": "second fundamental form rate o(r^{-2-sigma})",
            "pattern": r"o\s*\u2061?\s*\(\s*r\s*−\s*2\s*−\s*σ\s*\)",
            "locator": "LR2005, Section 1, display before footnote 3",
        },
        {
            "source": "LR2005",
            "label": "sigma > 0",
            "pattern": r"for some σ\s*>\s*0",
            "locator": "LR2005, Section 1, display before footnote 3",
        },
    ],
    "SC3-adjacent": [
        {
            "source": "BI2004",
            "label": "alternative weighted phase space, negative decay indices",
            "pattern": r"asymptotically flat phase space",
            "locator": "BI2004, Section 3 (The Constraints and Evolution)",
        },
        {
            "source": "BI2004",
            "label": "metric weight index -1/2",
            "pattern": r"H\s*−\s*1\s*/\s*2\s*2",
            "locator": "BI2004, Section 3",
        },
        {
            "source": "BI2004",
            "label": "momentum weight index -3/2",
            "pattern": r"H\s*−\s*3\s*/\s*2\s*1",
            "locator": "BI2004, Section 3",
        },
    ],
}

# Absence patterns: the exact normalization claimed by the schema must not appear in any
# checked source if SC3/SC4 are to be classified NOT_FOUND_IN_CHECKED_SET.
ABSENCE_PATTERNS = {
    "SC3": [
        {"label": "H^s_delta", "pattern": r"H\s*δ\s*s"},
        {"label": "H^{s-1}_{delta+1}", "pattern": r"H\s*δ\s*\+\s*1\s*s\s*−\s*1"},
    ],
    "SC4": [
        {"label": "delta in (1/2, 1)", "pattern": r"δ\s*∈\s*\(\s*1\s*/\s*2\s*,\s*1\s*\)"},
        {"label": "1/2 < delta < 1", "pattern": r"1\s*/\s*2\s*<\s*δ\s*<\s*1"},
    ],
}

FABRICATION_CONTROL = "the weighted class H^s_delta with delta in (1/2, 1) is standard"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(raw: str) -> str:
    """Deterministic HTML -> text normalization (fixed for the whole run)."""
    s = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
    s = re.sub(r"<style.*?</style>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s)
    return s


def find_quote(text: str, pattern: str, ctx: int = 220):
    m = re.search(pattern, text)
    if not m:
        return None
    return {
        "matched": m.group(0),
        "offset": m.start(),
        "context": text[max(0, m.start() - ctx): m.end() + ctx],
    }


def schema_claim_snapshot():
    out = {}
    for rel in SCHEMAS:
        p = ROOT / rel
        lines = p.read_text().splitlines()
        captured = []
        for i, ln in enumerate(lines):
            if "sobolev_variant" in ln:
                captured.append(ln)
                indent = len(ln) - len(ln.lstrip())
                for nxt in lines[i + 1: i + 5]:
                    if not nxt.strip():
                        break
                    if len(nxt) - len(nxt.lstrip()) > indent:
                        captured.append(nxt)
                    else:
                        break
        out[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size, "sobolev_lines": captured}
    return out


def main() -> int:
    checks = {"task_id": TASK_ID, "created_at": CREATED_AT, "integrity": {}, "quotes": {}, "absence": {}, "controls": {}}
    failures = []

    # 1. Source integrity
    manifest = []
    texts = {}
    for src in SOURCES:
        p = HERE / src["path"]
        if not p.exists():
            failures.append(f"missing source {src['path']}")
            continue
        h = sha256_file(p)
        texts[src["id"]] = normalize(p.read_text(encoding="utf-8", errors="ignore"))
        entry = {**{k: v for k, v in src.items()}, "sha256": h, "bytes": p.stat().st_size}
        manifest.append(entry)
        checks["integrity"][src["id"]] = {"path": src["path"], "sha256": h, "bytes": p.stat().st_size, "ok": True}

    # 2. Required quotes
    quote_sets = {"SC1": [], "SC2": [], "SC3-adjacent": []}
    for claim, specs in REQUIRED_QUOTES.items():
        for spec in specs:
            found = find_quote(texts.get(spec["source"], ""), spec["pattern"])
            rec = {"source": spec["source"], "label": spec["label"], "locator": spec["locator"],
                   "pattern": spec["pattern"], "found": found is not None}
            if found:
                rec.update(found)
            else:
                failures.append(f"quote not found: {claim}/{spec['label']}")
            quote_sets[claim].append(rec)
            checks["quotes"].setdefault(claim, []).append(rec)

    # 3. Absence checks for the exact schema normalization, over every checked source
    for claim, specs in ABSENCE_PATTERNS.items():
        for spec in specs:
            hits = []
            for sid, text in texts.items():
                m = re.search(spec["pattern"], text)
                if m:
                    hits.append({"source": sid, "matched": m.group(0), "offset": m.start()})
            rec = {"label": spec["label"], "pattern": spec["pattern"], "present_in_any_source": bool(hits), "hits": hits}
            checks["absence"].setdefault(claim, []).append(rec)
            if hits and claim in ("SC3", "SC4"):
                failures.append(f"absence check failed: {claim}/{spec['label']} occurs in {[h['source'] for h in hits]}")

    # 4. Controls: fabricated quote must be absent; single-character mutation of a real quote must fail
    fab = find_quote(texts.get("KR2001", ""), re.escape(FABRICATION_CONTROL))
    checks["controls"]["fabricated_quote_absent"] = {"quote": FABRICATION_CONTROL, "found": fab is not None}
    if fab:
        failures.append("fabrication control failed: fabricated quote was found")
    real_pat = REQUIRED_QUOTES["SC1"][0]["pattern"]
    mutated = real_pat.replace("5", "6", 1)
    mut = find_quote(texts.get("KR2001", ""), mutated)
    checks["controls"]["mutation_detected"] = {"mutated_pattern": mutated, "found": mut is not None}
    if mut:
        failures.append("mutation control failed: mutated quote still matched")

    # 5. Verdict computation per the pre-fixed decision rule
    sc1_ok = all(q["found"] for q in quote_sets["SC1"])
    sc2_ok = all(q["found"] for q in quote_sets["SC2"])
    sc3_absent = all(not r["present_in_any_source"] for r in checks["absence"]["SC3"])
    sc4_absent = all(not r["present_in_any_source"] for r in checks["absence"]["SC4"])
    sc3_adjacent_ok = all(q["found"] for q in quote_sets["SC3-adjacent"])

    sub_claims = [
        {
            "id": "SC1",
            "statement": "s > 5/2 is the classical local well-posedness threshold for the Einstein vacuum Cauchy problem on asymptotically flat data (nabla g, k in H^{s-1}).",
            "status": "SUPPORTED" if sc1_ok else "NOT_FOUND_IN_CHECKED_SET",
            "evidence": "KR2001 Theorem 1.1 + Remark 1.2",
            "evidence_quality": "preprint; the statement attributes the result to [H-K-M], which was not fetched",
            "schema_field": "s: \"s > 5/2\"",
        },
        {
            "id": "SC2",
            "statement": "h - delta_ij = O(r^-1) and K = O(r^-2) is the standard asymptotically flat decay family.",
            "status": "PARTIALLY_SUPPORTED" if sc2_ok else "NOT_FOUND_IN_CHECKED_SET",
            "evidence": "LR2005 Section 1: metric o(r^{-1-sigma}), K o(r^{-2-sigma}), sigma > 0 (peer-reviewed); CK's strongly AF class o(r^{-3/2}), o(r^{-5/2}) quoted in the same footnote",
            "evidence_quality": "peer-reviewed; rates are strictly faster than the schema's big-O rates and derivative counts are not enumerated",
            "schema_field": "asymptotic_decay (not the weighted encoding)",
        },
        {
            "id": "SC3",
            "statement": "The weighted normalization h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1} is the standard published form.",
            "status": "NOT_FOUND_IN_CHECKED_SET" if (sc3_absent and sc3_adjacent_ok) else "UNRESOLVED",
            "evidence": "ABSENT in all four checked sources; BI2004 Section 3 uses a different convention: (g-ring + H^2_{-1/2}) x H^1_{-3/2} (negative decay indices, momentum more negative); BIERI2009 uses interior/exterior weighted L^p norms",
            "evidence_quality": "absence in a bounded checked set + positive evidence of different conventions; not a proof that no source states the schema's form",
            "schema_field": "spaces: \"h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}\"",
        },
        {
            "id": "SC4",
            "statement": "The upper endpoint 1 of the interval delta in (1/2, 1) is part of the standard statement.",
            "status": "NOT_FOUND_IN_CHECKED_SET" if sc4_absent else "UNRESOLVED",
            "evidence": "no checked source states a delta-range at all",
            "evidence_quality": "absence in a bounded checked set",
            "schema_field": "delta: \"delta in (1/2, 1)\"",
        },
    ]

    overall = "PARTIAL" if not (sub_claims[2]["status"] == "SUPPORTED" and sub_claims[3]["status"] == "SUPPORTED") else "SUPPORTED"
    if failures:
        overall = "CHECK_FAILED"

    verification = {
        "schema_version": "worker-verification/v1",
        "task_id": TASK_ID,
        "actor": "worker-039",
        "role": "bounded execution worker",
        "slot": "039",
        "created_at": CREATED_AT,
        "node_id": NODE_ID,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "gate_dependency_note": "the sobolev_variant field is part of the frozen F1/F2a/F2b data_class; a cleared citation would be a G-FORM input, but this artifact is a G-LIT verification only",
        "authority": "worker evidence only; does not set node status, validation_status=passed, or any gate verdict; does not edit the canonical ledger or schemas",
        "claim_under_test": {
            "verbatim": "sobolev_variant: {s: \"s > 5/2\", delta: \"delta in (1/2, 1)\", spaces: \"h - delta_ij in H^s_delta, K in H^{s-1}_{delta+1}\", status: \"standard_choice; UNVERIFIED citation\"}",
            "present_in": schema_claim_snapshot(),
        },
        "sources": manifest,
        "sub_claims": sub_claims,
        "overall_verdict": overall,
        "schema_status_recommendation": {
            "action": "RETAIN the status \"standard_choice; UNVERIFIED citation\"",
            "reason": "SC3 and SC4 (the weighted encoding and the delta interval) have no locator in the checked open set; clearing the flag would promote fluent text to a verified citation",
            "permitted_upgrade": "add the KR2001 Theorem 1.1 / Remark 1.2 locator for the s > 5/2 threshold and the LR2005 Section 1 locator for the AF decay family as PARTIAL support annotations",
            "required_from_owner": "a section/page locator in a named source for the exact H^s_delta / H^{s-1}_{delta+1} normalization and the delta in (1/2,1) interval (the schemas' provenance names only 'Choquet-Bruhat-Geroch maximal development' with identifier null, which does not cover this field)",
            "convention_hazard": "weight indices appear with opposite signs across the literature (BI2004: H^2_{-1/2} x H^1_{-3/2}); the schema uses positive delta and delta+1, so any borrowed locator must be checked for index-sign convention before it is bound",
        },
        "decision_rule": {
            "SC1": "SUPPORTED iff all KR quote patterns present; else NOT_FOUND_IN_CHECKED_SET",
            "SC2": "PARTIALLY_SUPPORTED iff all LR quote patterns present (rates are little-o and faster than the schema's big-O, derivative counts absent); else NOT_FOUND_IN_CHECKED_SET",
            "SC3": "NOT_FOUND_IN_CHECKED_SET iff the exact normalization is absent from every checked source AND a different convention is positively attested; else UNRESOLVED",
            "SC4": "NOT_FOUND_IN_CHECKED_SET iff the interval is absent from every checked source; else UNRESOLVED",
            "overall": "SUPPORTED only if SC3 and SC4 are both SUPPORTED; otherwise PARTIAL; CHECK_FAILED if any integrity/quote/control check fails",
        },
        "falsifier": "A fetched primary source with an exact locator (section, theorem or page) that states the schema's conjunction: h - delta_ij in H^s_delta and K in H^{s-1}_{delta+1} with s > 5/2 and delta in (1/2, 1), on asymptotically flat vacuum data. Such a source flips SC3/SC4 and the overall verdict to SUPPORTED.",
        "next_falsifier": "A source showing delta > 1/2 alone (no upper endpoint) is the standard statement, which would make the schema's '(1/2, 1)' interval an unlicensed strengthening; or a source showing the standard threshold for the weighted class is not s > 5/2.",
        "non_claims": [
            "Does not assert that the schema's normalization is wrong or non-standard; only that it was not found in the four checked open sources.",
            "Does not clear the UNVERIFIED flag and does not resolve any G-FORM gate item.",
            "Absence of a source in this checked set is not evidence of absence in the literature.",
            "The KR2001 statement is a preprint; the underlying classical result [H-K-M] was not fetched.",
        ],
        "limitations": [
            "Bounded source set: four open-access items (2 peer-reviewed/preprint research papers, 2 review/preprint sketches); book sources were not fetchable in this run.",
            "The ar5iv HTML renderings are the pinned evidence; the publisher PDFs were not fetched.",
            "Text normalization collapses whitespace and keeps LaTeX/MathML duplication, which is why quote patterns are regex-tolerant.",
        ],
        "integrity_failures": failures,
        "checks_ref": "checks.json",
        "claims_completion": False,
    }

    (HERE / "checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False) + "\n")
    (HERE / "verification.json").write_text(json.dumps(verification, indent=2, ensure_ascii=False) + "\n")
    (HERE / "SOURCE_MANIFEST.json").write_text(json.dumps({"task_id": TASK_ID, "created_at": CREATED_AT, "sources": manifest}, indent=2, ensure_ascii=False) + "\n")

    print(json.dumps({
        "task_id": TASK_ID,
        "overall_verdict": overall,
        "sub_claims": {s["id"]: s["status"] for s in sub_claims},
        "integrity_failures": failures,
        "sources": {m["id"]: m["sha256"][:16] for m in manifest},
    }, indent=1))
    return 1 if "CHECK_FAILED" in overall else 0


if __name__ == "__main__":
    sys.exit(main())
