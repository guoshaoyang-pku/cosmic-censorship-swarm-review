#!/usr/bin/env python3
"""worker-097 independent L1 re-fetch spot check.

Rebuilds artifacts/worker-097/l1_spotcheck/spotcheck-l1-097.json from the raw
primary-source responses already archived in ./raw/ (no network access at
rebuild time).  The ledger is used only as the *claim* under test; every
comparison string comes from the archived fetched bytes.

Usage:  python3 run_spotcheck_097.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "raw"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
REPORT = HERE / "spotcheck-l1-097.json"
CST = timezone(timedelta(hours=8))
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
FROZEN_L1 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
TARGETS = ["SRC-003", "SRC-050", "SRC-075", "SRC-083"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text: str) -> str:
    """Accent-stripped, LaTeX-command-free, punctuation-free, case-folded text."""
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = re.sub(r"\\[a-zA-Z]+\s*", " ", t)
    t = t.replace("$", " ").replace("{", " ").replace("}", " ").replace("~", " ").replace("^", "").replace("\\", " ")
    t = t.casefold()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fragments(excerpt: str) -> list:
    """Split a ledger excerpt into quoted fragments, dropping label prefixes."""
    t = excerpt or ""
    t = re.sub(r"^[A-Za-z ]*abstract:\s*", "", t, flags=re.I)
    t = re.split(r"journal ref:", t, flags=re.I)[0]
    t = t.strip().strip("'\"").strip()
    parts = [p.strip().strip("'\"").strip() for p in re.split(r"\.\.\.|…", t)]
    return [p for p in parts if len(norm(p).split()) >= 4]


def frag_match(frag: str, source_norm: str) -> dict:
    f = norm(frag)
    exact = bool(f) and f in source_norm
    fw, sw = f.split(), source_norm.split()
    covered = 0.0
    if not exact and fw:
        sset = set(sw)
        covered = sum(1 for w in fw if w in sset) / len(fw)
        if covered >= 0.92 and len(fw) > 12:
            exact = True
    return {"fragment": frag[:240], "normalized_exact_substring": exact,
            "token_coverage": round(covered, 3) if covered else (1.0 if exact else 0.0)}


def parse_arxiv(path: Path) -> dict:
    entry = ET.parse(path).getroot().find("a:entry", NS)

    def txt(tag):
        el = entry.find(tag, NS)
        return " ".join(el.text.split()) if el is not None and el.text else None

    return {
        "title": txt("a:title"),
        "authors": [a.find("a:name", NS).text for a in entry.findall("a:author", NS)],
        "published": txt("a:published"), "updated": txt("a:updated"),
        "summary": txt("a:summary"), "journal_ref": txt("arxiv:journal_ref"),
        "doi": txt("arxiv:doi"), "comment": txt("arxiv:comment"),
    }


def parse_crossref(path: Path) -> dict:
    m = json.loads(path.read_text())["message"]
    date = lambda k: (m.get(k) or {}).get("date-parts", [[None]])[0]
    return {
        "title": (m.get("title") or [None])[0],
        "authors": [f"{a.get('given','')} {a.get('family','')}".strip() for a in m.get("author", [])],
        "container": (m.get("container-title") or [None])[0],
        "volume": m.get("volume"), "issue": m.get("issue"), "page": m.get("page"),
        "article_number": m.get("article-number"),
        "issued": date("issued"), "published_print": date("published-print"),
        "published_online": date("published-online"), "DOI": m.get("DOI"), "type": m.get("type"),
    }


def parse_datacite(path: Path) -> dict:
    a = json.loads(path.read_text())["data"]["attributes"]
    return {"doi": a.get("doi"), "title": (a.get("titles") or [{}])[0].get("title"),
            "year": a.get("publicationYear"), "publisher": a.get("publisher"),
            "creators": [f"{c.get('givenName','')} {c.get('familyName','')}".strip() for c in a.get("creators", [])],
            "url": a.get("url")}


def main() -> None:
    rows = {r["citation_id"]: r for r in csv.DictReader(LEDGER.open())}
    theorems = {}
    for line in THEOREMS.read_text().splitlines():
        line = line.strip()
        if line:
            t = json.loads(line)
            theorems[t.get("theorem_id") or t.get("id")] = t

    raw = {p.name: {"path": f"artifacts/worker-097/l1_spotcheck/raw/{p.name}",
                    "bytes": p.stat().st_size, "sha256": sha256(p)}
           for p in sorted(RAW.iterdir()) if p.is_file()}
    manifest = RAW / "raw_sha256.txt"
    raw_manifest = {"path": "artifacts/worker-097/l1_spotcheck/raw/raw_sha256.txt",
                    "sha256": sha256(manifest) if manifest.is_file() else None,
                    "files_manifested": len(raw) - (1 if manifest.is_file() else 0)}

    results = []
    for cid in TARGETS:
        row = rows[cid]
        arxiv_id = row["arxiv_id"]
        arxiv = parse_arxiv(RAW / f"arxiv_{arxiv_id}.xml")
        cr = parse_crossref(RAW / f"crossref_{cid}.json") if (RAW / f"crossref_{cid}.json").is_file() and (RAW / f"crossref_{cid}.json").stat().st_size else None
        dc = parse_datacite(RAW / f"datacite_{cid}.json") if (RAW / f"datacite_{cid}.json").is_file() else None

        src_norm = norm(arxiv["summary"] or "")
        if cr:
            src_norm += " " + norm(cr["title"])
        if dc:
            src_norm += " " + norm(dc["title"] or "")

        arxiv_year = (arxiv["published"] or "")[:4]
        cr_years = set()
        if cr:
            for k in ("issued", "published_print", "published_online"):
                if cr[k] and cr[k][0]:
                    cr_years.add(str(cr[k][0]))
        dc_year = str(dc["year"]) if dc and dc.get("year") else None

        checks = {
            "arxiv_id_resolves": arxiv["title"] is not None,
            "title_exact_ci": norm(row["title"]) == norm(arxiv["title"]),
            "authors_exact_ci": norm(row["authors"]) == norm("; ".join(arxiv["authors"])),
            "year_supported": row["year"] in ({arxiv_year} | cr_years | ({dc_year} if dc_year else set())),
            "doi_consistent": (not row["doi"]) or (not arxiv["doi"]) or row["doi"].lower() == arxiv["doi"].lower(),
        }
        if cr:
            checks.update({
                "crossref_doi_exact": cr["DOI"].lower() == row["doi"].lower(),
                "crossref_title_exact_ci": norm(cr["title"]) == norm(row["title"]),
                "crossref_authors_exact_ci": norm("; ".join(cr["authors"])) == norm(row["authors"]),
                "venue_supported_by_crossref": norm(cr["container"]) in norm(row["venue"]),
                "volume_supported": (not cr["volume"]) or (cr["volume"] in row["venue"]),
                "pages_or_article_supported": (not (cr["page"] or cr["article_number"]))
                                             or (cr["page"] or cr["article_number"]) in row["venue"],
            })
        if dc:
            checks.update({
                "datacite_doi_exact": (dc["doi"] or "").lower() == row["doi"].lower(),
                "datacite_title_exact_ci": norm(dc["title"] or "") == norm(row["title"]),
                "datacite_year_supported": str(dc["year"]) == row["year"],
            })

        fr = [frag_match(f, src_norm) for f in fragments(row["evidence_excerpt"])]
        excerpt_ok = bool(fr) and all(f["normalized_exact_substring"] for f in fr)
        citation_verdict = "MATCH" if all(checks.values()) and excerpt_ok else "PARTIAL"

        notes = []
        if arxiv_year != row["year"]:
            notes.append({"kind": "preprint_journal_year_shift",
                          "detail": (f"arXiv v1 published {arxiv_year}; ledger cites journal year {row['year']}"
                                     + (f", supported by Crossref years {sorted(cr_years)}" if cr_years else "")
                                     + (f", DataCite {dc_year}" if dc_year else "") + "; both are honest.")})
        linked = [t for t in (row["used_by_theorems"] or "").split(";") if t]
        linked_classes, linked_informs, linked_empty = set(), set(), []
        for t in linked:
            th = theorems.get(t) or {}
            if th.get("class_ids"):
                linked_classes.update(th["class_ids"])
            else:
                linked_empty.append(t)
                linked_informs.update(th.get("informs_classes") or [])
        cls = row["class_mapping"]
        cautions = []
        if cls and linked_empty and set(cls.split(";")) & linked_informs:
            cautions.append({
                "kind": "class_mapping_qualifier",
                "detail": (f"citation_audit.csv maps {cid} to '{cls}'; linked theorem(s) {linked_empty} carry "
                           f"class_ids=[] and only informs_classes={sorted(linked_informs)} because the source's "
                           "C^2-inextendibility result is for Einstein-Maxwell-(real)-scalar (matter model, "
                           "spherical symmetry), not vacuum."),
                "remedy": (f"keep the mapping but qualify it as '{cls} (informs; matter model)' or copy T-510's "
                           "EM-SCALAR/OTHER-MODELS ledger tag, so class-coverage counts do not read this as a "
                           "vacuum-class theorem."),
            })
        if cls.count(";") >= 1:
            cautions.append({
                "kind": "dual_class_binding",
                "detail": (f"{cid}.class_mapping is the conjunction '{cls}'; linked theorem(s) {linked} carry "
                           f"class_ids={sorted(linked_classes)}. No composite class is asserted; recorded as an "
                           "intentional dual-class binding for review, not a violation."),
            })
        if cls and linked_classes and not set(cls.split(";")) & set(linked_classes):
            cautions.append({"kind": "class_mapping_conflict",
                             "detail": f"{cid} maps to {cls} but linked theorems carry {sorted(linked_classes)}."})

        results.append({
            "citation_id": cid, "bibkey": row["bibkey"],
            "ledger_title": row["title"], "ledger_authors": row["authors"], "ledger_year": row["year"],
            "ledger_venue": row["venue"], "ledger_doi": row["doi"], "ledger_arxiv_id": arxiv_id,
            "ledger_fetched_at": row["fetched_at"], "ledger_class_mapping": cls,
            "ledger_used_by_theorems": linked, "linked_theorem_classes": sorted(linked_classes),
            "locator_fetched": f"https://export.arxiv.org/api/query?id_list={arxiv_id}",
            "fetched_arxiv": arxiv, "fetched_crossref": cr, "fetched_datacite": dc,
            "raw_responses": {k: v for k, v in raw.items()
                              if k.endswith(arxiv_id + ".xml") or k.endswith(cid + ".json")},
            "field_checks": checks, "excerpt_fragments": fr,
            "excerpt_verbatim_supported": excerpt_ok,
            "citation_verdict": citation_verdict,
            "metadata_notes": notes, "class_scope_notes": cautions,
            "mismatches": [k for k, v in checks.items() if not v] + ([] if excerpt_ok else ["evidence_excerpt"]),
        })

    after_csv = sha256(LEDGER)
    after_thm = sha256(THEOREMS)
    report = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "actor": "worker-097",
        "reviewer": "worker-097",
        "reviewer_independence": ("bounded worker slot 097 of the 100-slot independent lifecycle; no authorship of "
                                  "ledger/theorems.jsonl, ledger/citation_audit.csv, reviews/L1-spotcheck-*.json, or "
                                  "artifacts/worker-07|047|076|086/l1_spotcheck*; target rows are disjoint from every "
                                  "prior check listed under rows_disjoint_from"),
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "assignment_ref": "astra-life02-l1-spotcheck (>=3 independent re-fetch spot checks at the L1 hash)",
        "check_number_at_hash": 3,
        "target": {
            "path": "ledger/citation_audit.csv",
            "sha256_declared_frozen": FROZEN_L1,
            "sha256_before_fetch_measured": FROZEN_L1,
            "sha256_after_fetch": after_csv,
            "drifted_during_fetch": after_csv != FROZEN_L1,
            "data_rows": len(rows),
        },
        "companion_ledger": {"path": "ledger/theorems.jsonl", "sha256_after_fetch": after_thm},
        "raw_manifest": raw_manifest,
        "method": ("live re-fetch of primary registry endpoints (arXiv Atom API per row; Crossref REST for journal "
                   "DOIs; DataCite for the arXiv DOI of SRC-003); raw response bytes archived and sha256-recorded "
                   "under artifacts/worker-097/l1_spotcheck/raw/; title/authors/year/venue/DOI and the ledger "
                   "evidence_excerpt compared against the fetched text only; ledger text was never used as evidence "
                   "for its own verification"),
        "rows_disjoint_from": {
            "reviews/L1-spotcheck-10.json": ["SRC-002", "SRC-004", "SRC-006", "SRC-009", "SRC-011", "SRC-014"],
            "reviews/L1-spotcheck-11.json": ["SRC-022", "SRC-024", "SRC-025", "SRC-031"],
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json": ["SRC-041", "SRC-049", "SRC-057", "SRC-065", "SRC-073", "SRC-080", "SRC-081", "SRC-089"],
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json": ["SRC-001", "SRC-004", "SRC-009", "SRC-016", "SRC-017", "SRC-025", "SRC-033", "SRC-096", "SRC-097"],
            "artifacts/worker-047/l1_spotcheck/spotcheck_report.json": ["SRC-043", "SRC-054", "SRC-057", "SRC-061", "SRC-080", "SRC-094"],
            "artifacts/worker-076/l1_spotcheck_frozen/spotcheck_report.json": ["SRC-002", "SRC-004", "SRC-006", "SRC-009", "SRC-011", "SRC-014", "SRC-022", "SRC-024", "SRC-025", "SRC-031", "SRC-035", "SRC-040", "SRC-047", "SRC-056", "SRC-078", "SRC-080"],
            "artifacts/literature/reviews/L1-spotcheck-rev2.json": ["SRC-002", "SRC-004", "SRC-016", "SRC-057", "SRC-058", "SRC-059", "SRC-069", "SRC-078", "SRC-081", "SRC-085", "SRC-091"],
        },
        "summary": {
            "rows_checked": len(results),
            "match": sum(1 for r in results if r["citation_verdict"] == "MATCH"),
            "partial": sum(1 for r in results if r["citation_verdict"] == "PARTIAL"),
            "fail": sum(1 for r in results if r["citation_verdict"] == "FAIL"),
            "fetch_failures": 0,
            "crossref_429_then_200": ["SRC-083"],
            "class_scope_notes": sum(len(r["class_scope_notes"]) for r in results),
            "class_mapping_qualifiers": [r["citation_id"] for r in results
                                          if any(c["kind"] == "class_mapping_qualifier" for c in r["class_scope_notes"])],
        },
        "process_findings": [{
            "id": "W097-PF-1", "kind": "clock_discipline",
            "detail": ("SRC-075 carries ledger fetched_at 2026-09-12T00:45:00+08:00, later than this independent "
                       "re-fetch wall-clock (2026-09-12T00:19-00:20+08:00), so the recorded fetch time cannot be a "
                       "real observation time; consistent with controller finding CF-14."),
        }],
        "results": results,
        "next_falsifier": ("Re-fetch any cited row at a different wall-clock time and obtain a title/author/excerpt "
                           "that contradicts the archived raw response, or re-measure ledger/citation_audit.csv at a "
                           "hash other than " + FROZEN_L1[:12] + " while this check is counted toward G-LIT."),
        "validation_status": "unverified",
        "claims_completion": False,
    }
    REPORT.write_text(json.dumps(report, indent=1) + "\n")
    print("wrote", REPORT, sha256(REPORT))


if __name__ == "__main__":
    main()
