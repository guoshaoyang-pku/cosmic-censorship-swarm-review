#!/usr/bin/env python3
"""Independent L1 re-fetch spot check #2 (G-LIT, node L1) by worker-023.

Read-only with respect to the ledger. Pins ledger/citation_audit.csv by sha256
(315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9), samples rows that no
recorded spot check has covered, re-fetches each sampled source from its own locator,
hashes the raw response, and compares the fetched record against the ledger row.

Sampling rule (frozen before any fetch): data rows 45 + 13k, k = 0..4 -> 45, 58, 71, 84, 97.
Disjointness: flash-10 covered a subset of rows 1-20; flash-11 covered a subset of rows
21-40; deepseek-flash-07 sampled {41,49,57,65,73,80,81,89}. None of {45,58,71,84,97} is in
those sets, and this implementation shares no code with the earlier checks.

Fail-closed: if the pinned csv sha256 does not match the file on disk, the run aborts
before fetching and records the abort as the outcome.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "ledger" / "citation_audit.csv"
THEOREMS_PATH = ROOT / "ledger" / "theorems.jsonl"
TAXONOMY_PATH = ROOT / "research_map" / "formulation_taxonomy.yaml"
OUT_DIR = Path(__file__).resolve().parent
RAW_DIR = OUT_DIR / "raw"
OUT_PATH = OUT_DIR / "spotcheck-l1-023.json"

CSV_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
SAMPLE_ROWS = [45, 58, 71, 84, 97]  # frozen before fetch; rule = 45 + 13k
FRAME = (41, 97)

CST = dt.timezone(dt.timedelta(hours=8))
CANONICAL_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
LATEX_NOISE = {
    "cite", "mathcal", "mathrm", "mathbb", "text", "box", "displaystyle", "loc",
    "nabla", "infty", "partial", "sqrt", "frac", "left", "right", "begin", "end",
}
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"


def now() -> str:
    return dt.datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm(s: str) -> str:
    # rev2: strip markup and fold diacritics before tokenising. rev1 did neither, which
    # produced a false title/author mismatch on SRC-071 (Crossref emits <i>T</i><sup>3</sup>
    # and "Ringström"); the sample and the ledger pin were unchanged.
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def content_tokens(s: str) -> list[str]:
    return [t for t in norm(s).split() if len(t) > 2 and t not in LATEX_NOISE]


def curl(url: str, attempts: int = 4) -> dict:
    """Fetch with backoff. rev2: arXiv returned HTTP 429 on the 4th/5th rapid request of
    rev1; retries are transport-level only and do not change the frozen sample."""
    last = None
    for k in range(attempts):
        cmd = ["curl", "-sS", "--max-time", "60", "-L", "-w", "\n%{http_code}", url]
        p = subprocess.run(cmd, capture_output=True)
        if p.returncode != 0:
            last = {"ok": False, "url": url, "http_status": 0,
                    "error": p.stderr.decode("utf-8", "replace")[:300]}
        else:
            body, _, code = p.stdout.rpartition(b"\n")
            try:
                status = int(code.strip() or b"0")
            except ValueError:
                status = 0
            last = {"ok": status == 200 and len(body) > 0, "url": url, "http_status": status,
                    "bytes": len(body), "sha256": sha256_bytes(body), "body": body,
                    "attempt": k + 1}
            if last["ok"]:
                return last
        if k < attempts - 1:
            time.sleep((4, 10, 25)[min(k, 2)])
    return last


def parse_arxiv(body: bytes) -> dict:
    try:
        entry = ET.fromstring(body).find(f"{ATOM}entry")
    except ET.ParseError as e:
        return {"parse_error": str(e)}
    if entry is None:
        return {"parse_error": "no atom entry"}
    authors = [" ".join((a.findtext(f"{ATOM}name") or "").split())
               for a in entry.findall(f"{ATOM}author")]
    return {
        "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
        "authors": authors,
        "published": (entry.findtext(f"{ATOM}published") or "")[:10],
        "year": (entry.findtext(f"{ATOM}published") or "")[:4],
        "journal_ref": " ".join((entry.findtext(f"{ARXIV}journal_ref") or "").split()),
        "doi": entry.findtext(f"{ARXIV}doi") or "",
        "abstract": " ".join((entry.findtext(f"{ATOM}summary") or "").split()),
    }


def parse_openalex(body: bytes) -> dict:
    try:
        msg = json.loads(body)
        inv = msg.get("abstract_inverted_index") or {}
    except Exception as e:  # noqa: BLE001
        return {"parse_error": str(e)}
    pos: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    abstract = " ".join(pos[i] for i in sorted(pos))
    names = []
    for a in msg.get("authorships") or []:
        n = (a.get("author") or {}).get("display_name")
        if n:
            names.append(n)
    return {
        "title": msg.get("title") or "",
        "authors": names,
        "year": str(msg.get("publication_year") or ""),
        "journal_ref": ((msg.get("primary_location") or {}).get("source") or {}).get("display_name") or "",
        "doi": (msg.get("doi") or "").replace("https://doi.org/", ""),
        "abstract": abstract,
    }


def first_family(authors: str) -> str:
    a = (authors or "").replace(" and ", ",")
    first = a.split(",")[0].strip()
    return norm(first.split()[-1]) if first else ""


def title_verdict(lt: str, ft: str) -> str:
    lt, ft = norm(lt), norm(ft)
    if not lt or not ft:
        return "unavailable"
    if lt == ft or lt in ft or ft in lt:
        return "strong"
    sl, sf = set(lt.split()), set(ft.split())
    jac = len(sl & sf) / max(1, len(sl | sf))
    return "partial" if jac >= 0.6 else "mismatch"


def quote_probe(quote: str, abstract: str) -> str:
    if not abstract.strip():
        return "no_abstract_available"
    q = re.sub(r"^\s*[A-Za-z][A-Za-z0-9 (/)\-]{0,60}:\s*", "", quote).strip(" '\"")
    if "..." in q:
        q = q.split("...")[0]
    qt, at = content_tokens(q), content_tokens(abstract)
    if not qt:
        return "not_checked"
    probe = qt[:25]
    i = 0
    for t in at:
        if i < len(probe) and t == probe[i]:
            i += 1
    if i == len(probe):
        return "grounded_in_abstract"
    jac = len(set(probe) & set(at)) / max(1, len(set(probe) | set(at)))
    return "close_paraphrase" if jac >= 0.6 else "not_found_in_abstract"


def parse_arxiv_abs_html(body: bytes) -> dict:
    """Fallback parser for the arXiv abstract page (different endpoint from the API)."""
    html = body.decode("utf-8", "replace")
    t = re.search(r'<h1 class="title[^"]*">(.*?)</h1>', html, re.S)
    title = re.sub(r"<[^>]+>", " ", t.group(1)) if t else ""
    title = re.sub(r"^\s*Title:\s*", "", " ".join(title.split()))
    a = re.search(r'<div class="authors">(.*?)</div>', html, re.S)
    authors = re.findall(r">([^<>]+)</a>", a.group(1)) if a else []
    ab = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', html, re.S)
    abstract = re.sub(r"<[^>]+>", " ", ab.group(1)) if ab else ""
    abstract = re.sub(r"^\s*Abstract:\s*", "", " ".join(abstract.split()))
    d = re.search(r'<meta name="citation_date" content="([^"]+)"', html)
    return {"title": " ".join(title.split()), "authors": [x.strip() for x in authors if x.strip()],
            "year": (d.group(1)[:4] if d else ""), "journal_ref": "", "doi": "",
            "abstract": abstract}


def candidates_for(row: dict) -> list[tuple[str, str]]:
    """Fixed fallback order, declared before fetching: arXiv API -> Crossref -> OpenAlex
    -> arXiv abs page -> recorded evidence URL. Transport rate limits are the only reason
    to move down the chain; the content is never used to choose the next candidate."""
    out: list[tuple[str, str]] = []
    aid = (row.get("arxiv_id") or "").strip()
    doi = (row.get("doi") or "").strip()
    if aid:
        out.append(("arxiv-api", f"https://export.arxiv.org/api/query?id_list={aid}"))
    if doi and not doi.startswith("10.48550"):
        out.append(("crossref-api", f"https://api.crossref.org/works/{doi}"))
    if doi:
        out.append(("openalex-api", f"https://api.openalex.org/works/doi:{doi}"))
    if aid:
        out.append(("arxiv-abs-html", f"https://arxiv.org/abs/{aid}"))
    ev = (row.get("evidence_url") or row.get("url") or "").strip()
    if ev:
        out.append(("page-fetch", ev))
    return out


def parse_by_kind(kind: str, body: bytes) -> dict:
    if kind == "arxiv-api":
        return parse_arxiv(body)
    if kind == "crossref-api":
        return parse_crossref(body)
    if kind == "openalex-api":
        return parse_openalex(body)
    if kind == "arxiv-abs-html":
        return parse_arxiv_abs_html(body)
    text = re.sub(r"<[^>]+>", " ", body.decode("utf-8", "replace"))
    return {"title": "", "authors": [], "year": "", "abstract": " ".join(text.split())}


def locator_for(row: dict) -> tuple[str, str]:
    if row.get("arxiv_id"):
        return "arxiv-api", f"https://export.arxiv.org/api/query?id_list={row['arxiv_id'].strip()}"
    if row.get("doi"):
        return "crossref-api", f"https://api.crossref.org/works/{row['doi'].strip()}"
    return "page-fetch", (row.get("evidence_url") or row.get("url") or row.get("exact_locator") or "").strip()


def parse_crossref(body: bytes) -> dict:
    try:
        msg = json.loads(body)["message"]
    except Exception as e:  # noqa: BLE001
        return {"parse_error": str(e)}
    t = msg.get("title") or [""]
    authors = []
    for a in msg.get("author") or []:
        n = " ".join(x for x in [a.get("given"), a.get("family")] if x)
        if n:
            authors.append(n)
    issued = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0]
    abstract = re.sub(r"<[^>]+>", " ", msg.get("abstract") or "")
    return {"title": (t[0] if t else ""), "authors": authors,
            "year": str(issued[0]) if issued and issued[0] else "",
            "journal_ref": (msg.get("container-title") or [""])[0],
            "doi": msg.get("DOI") or "", "abstract": " ".join(abstract.split())}


def load_theorems() -> dict:
    out = {}
    for line in THEOREMS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            t = json.loads(line)
        except json.JSONDecodeError:
            continue
        out[t.get("theorem_id")] = t
    return out


def class_binding(row: dict, theorems: dict) -> dict:
    raw = (row.get("class_mapping") or "").strip()
    tokens = [t.strip() for t in raw.split(";") if t.strip()]
    canonical = [t for t in tokens if t in CANONICAL_CLASSES]
    noncanonical = [t for t in tokens if t not in CANONICAL_CLASSES]
    used = [u.strip() for u in (row.get("used_by_theorems") or "").split(";") if u.strip()]
    theorem_rows = {u: theorems.get(u) for u in used}
    missing = [u for u, t in theorem_rows.items() if t is None]
    mismatches, gaps = [], []
    for u, t in theorem_rows.items():
        if t is None:
            continue
        # rev2: class binding may be carried by class_ids, class_id, or informs_classes
        # (T-510/T-514 use informs_classes with class_ids empty). rev1 read class_ids only
        # and produced a false "theorem has no class ids" class mismatch.
        tclasses = set(t.get("class_ids") or [])
        if t.get("class_id"):
            tclasses.add(t["class_id"])
        tclasses |= set(t.get("informs_classes") or [])
        if canonical and tclasses and not (set(canonical) & tclasses):
            mismatches.append({"theorem_id": u, "theorem_class_ids": sorted(tclasses),
                               "row_class_mapping": canonical, "kind": "disjoint_class_sets"})
        if canonical and not tclasses:
            gaps.append({"theorem_id": u, "row_class_mapping": canonical,
                         "kind": "theorem_carries_no_class_binding_key"})
    return {"row_class_mapping_raw": raw, "canonical_tokens": canonical,
            "noncanonical_tokens": noncanonical, "used_by_theorems": used,
            "theorems_missing_from_ledger": missing, "class_mismatches": mismatches,
            "class_binding_gaps_soft": gaps}


def main() -> int:
    raw = CSV_PATH.read_bytes()
    digest = sha256_bytes(raw)
    if digest != CSV_SHA256:
        OUT_PATH.write_text(json.dumps({
            "status": "FAIL_CLOSED_ABORT", "reason": "pinned ledger hash mismatch",
            "pinned_sha256": CSV_SHA256, "observed_sha256": digest,
            "created_at": now(), "reviewer": "worker-023", "node_id": "L1",
        }, indent=2))
        print(f"ABORT: ledger sha256 {digest} != pinned {CSV_SHA256}")
        return 2

    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    theorems = load_theorems()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for n in SAMPLE_ROWS:
        row = rows[n - 1]
        if row["citation_id"] == "":
            continue
        kind, url = locator_for(row)
        fetched_at = now()
        attempts_log = []
        resp, used_kind, used_url, parsed = None, kind, url, None
        for cand_kind, cand_url in candidates_for(row):
            attempt = curl(cand_url)
            attempts_log.append({"locator_kind": cand_kind, "url": cand_url,
                                 "http_status": attempt.get("http_status"),
                                 "raw_sha256": attempt.get("sha256"),
                                 "bytes": attempt.get("bytes"), "attempt": attempt.get("attempt"),
                                 "error": attempt.get("error")})
            if not attempt.get("ok"):
                time.sleep(3)
                continue
            cand_parsed = parse_by_kind(cand_kind, attempt["body"])
            if (cand_parsed.get("title") or "").strip() or cand_kind == "page-fetch":
                resp, used_kind, used_url, parsed = attempt, cand_kind, cand_url, cand_parsed
                break
        record = {
            "row": n, "citation_id": row["citation_id"], "bibkey": row["bibkey"],
            "ledger_title": row["title"], "ledger_authors": row["authors"],
            "ledger_year": row["year"], "ledger_locator": url, "locator_kind": kind,
            "locator_used": used_url, "locator_kind_used": used_kind,
            "locator_attempts": attempts_log,
            "fetched_at": fetched_at,
            "http_status": (resp or {}).get("http_status"),
            "fetch_attempt": (resp or {}).get("attempt"), "raw_bytes": (resp or {}).get("bytes"),
            "raw_sha256": (resp or {}).get("sha256"),
            "class_mapping": row["class_mapping"],
            "verification_status_in_ledger": row["status"],
            "error": (resp or {}).get("error"),
        }
        if resp and resp.get("ok") and parsed is not None:
            ext = {"arxiv-api": "xml", "crossref-api": "json", "openalex-api": "json",
                   "arxiv-abs-html": "html", "page-fetch": "txt"}.get(used_kind, "txt")
            raw_name = f"{row['citation_id']}.{used_kind}.{ext}"
            (RAW_DIR / raw_name).write_bytes(resp["body"])
            record["raw_file"] = f"raw/{raw_name}"
            record["fetched"] = {k: v for k, v in parsed.items() if k != "abstract"}
            record["fetched_abstract_chars"] = len(parsed.get("abstract") or "")
            tv = title_verdict(row["title"], parsed.get("title", ""))
            fam = first_family(row["authors"])
            fetched_fams = [first_family(a) for a in parsed.get("authors") or []]
            author_ok = bool(fam) and fam in fetched_fams
            ly, fy = (row.get("year") or "").strip(), str(parsed.get("year") or "").strip()
            year_ok = (abs(int(ly) - int(fy)) <= 1) if (ly.isdigit() and fy.isdigit()) else None
            qc = quote_probe(row.get("evidence_excerpt") or "", parsed.get("abstract") or "")
            if tv == "strong" and author_ok and year_ok is not False and qc in (
                    "grounded_in_abstract", "metadata_record_consistent", "not_checked",
                    "no_abstract_available"):
                verdict = "MATCH"
            elif tv in ("strong", "partial") and author_ok:
                verdict = "PARTIAL"
            elif tv == "unavailable":
                verdict = "FETCH_FAILED"
            else:
                verdict = "MISMATCH"
            record.update({"title_verdict": tv, "author_ok": author_ok,
                           "ledger_first_family": fam, "fetched_families": fetched_fams,
                           "year_ok": year_ok, "ledger_year": ly, "fetched_year": fy,
                           "quote_check": qc, "verdict": verdict})
            if verdict == "PARTIAL" and tv == "strong" and author_ok and year_ok is False:
                record["year_note"] = ("locator resolves to the recorded work; year differs "
                                       "by >1 (preprint-posting vs journal year), not a "
                                       "locator error")
        else:
            record["verdict"] = "FETCH_FAILED"
        record["class_binding"] = class_binding(row, theorems)
        results.append(record)
        time.sleep(3)  # arXiv API courtesy delay between requests

    hard = []
    soft = []
    for r in results:
        if r["verdict"] == "MISMATCH":
            hard.append({"citation_id": r["citation_id"],
                         "finding": "locator resolves to a different work (title mismatch)",
                         "ledger_title": r.get("ledger_title"),
                         "fetched_title": (r.get("fetched") or {}).get("title")})
        for m in r["class_binding"]["class_mismatches"]:
            hard.append({"citation_id": r["citation_id"], "finding": "class-binding mismatch",
                         "detail": m})
        for g in r["class_binding"]["class_binding_gaps_soft"]:
            soft.append({"citation_id": r["citation_id"], "finding": "class-binding gap",
                         "detail": g})
    summary = {
        "checked": len(results),
        "MATCH": sum(1 for r in results if r["verdict"] == "MATCH"),
        "PARTIAL": sum(1 for r in results if r["verdict"] == "PARTIAL"),
        "MISMATCH": sum(1 for r in results if r["verdict"] == "MISMATCH"),
        "FETCH_FAILED": sum(1 for r in results if r["verdict"] == "FETCH_FAILED"),
    }
    out = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CANONICAL_CLASSES,
        "actor": "worker-023",
        "reviewer": "worker-023",
        "created_at": now(),
        "check_number": 2,
        "status": "draft-unverified; spot check only",
        "independence_of": ["reviews/L1-spotcheck-10.json", "reviews/L1-spotcheck-11.json",
                            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json"],
        "independence_note": ("Own sampling rule and own implementation. Sampled rows "
                              "{45,58,71,84,97} are disjoint from flash-10 (1-20 subset), "
                              "flash-11 (21-40 subset) and deepseek-flash-07 "
                              "{41,49,57,65,73,80,81,89}. Raw responses are stored and hashed."),
        "target": {"path": "ledger/citation_audit.csv", "sha256": CSV_SHA256,
                   "data_rows": len(rows), "measured_sha256_at_start": digest},
        "instrument_revision": {
            "revision": 3,
            "superseded_revision_1_file": "superseded/rev1-instrument-bug.json",
            "superseded_revision_2_file": "superseded/rev2-partial-fetch.json",
            "superseded_raw_dirs": ["superseded/raw-rev1/", "superseded/raw-rev2/"],
            "naming_note": ("Superseded outputs are deliberately NOT named spotcheck-l1-*.json: "
                            "the lifecycle l1_spotchecks() glob would otherwise count this one "
                            "check three times."),
            "changes": [
                "HTML-tag stripping + diacritic folding added to title/author normalisation "
                "(rev1 false MISMATCH on SRC-071: Crossref title carries <i>T</i><sup>3</sup> "
                "and author 'Ringström'; same work, same DOI).",
                "Class-binding cross-check now unions class_ids, class_id and informs_classes "
                "(rev1 called T-510/T-514 a class mismatch because class_ids is empty and the "
                "binding lives in informs_classes for T-510; T-514 has no binding key at all "
                "and is reported as a soft gap).",
                "Fixed fallback locator chain arXiv API -> Crossref -> OpenAlex -> arXiv abs "
                "page -> recorded evidence URL, with per-candidate attempts logged (rev2 still "
                "had 2/5 FETCH_FAILED because the shared arXiv API endpoint returned HTTP 429 "
                "on all retries).",
                "Retry with backoff plus inter-request delay retained from rev2.",
            ],
            "unchanged": ["ledger pin", "sample rows {45,58,71,84,97}", "comparison thresholds"],
            "rev1_summary": {"MATCH": 1, "PARTIAL": 1, "MISMATCH": 1, "FETCH_FAILED": 2},
            "rev2_summary": {"MATCH": 2, "PARTIAL": 1, "MISMATCH": 0, "FETCH_FAILED": 2},
        },
        "sampling_rule": {"frozen_before_fetch": True,
                          "rule": f"frame rows {FRAME[0]}-{FRAME[1]}; rows 45 + 13k, k=0..4",
                          "sampled_rows": SAMPLE_ROWS},
        "method": ("Re-fetch each sampled row from its own paper locator (arXiv API id_list= "
                   "for arXiv ids, Crossref API for DOI-only rows; declared fallback chain "
                   "Crossref/OpenAlex/arXiv-abs-page when a transport returns no usable body); "
                   "store and sha256 the raw body; compare title/first-author-family/year after "
                   "markup-stripping and diacritic normalisation; test the ledger "
                   "evidence_excerpt at content-token level against the fetched abstract; "
                   "cross-check the row's class_mapping against the class binding of every "
                   "theorem listed in used_by_theorems (class_ids | class_id | "
                   "informs_classes)."),
        "results": results,
        "summary": summary,
        "hard_failures": hard,
        "soft_findings": soft,
        "findings": [
            {"id": "SPOT23-F-01", "severity": "info",
             "finding": f"{summary['MATCH']} MATCH, {summary['PARTIAL']} PARTIAL, "
                        f"{summary['MISMATCH']} MISMATCH, {summary['FETCH_FAILED']} "
                        f"FETCH_FAILED over {summary['checked']} sampled rows."},
            {"id": "SPOT23-F-02", "severity": "info",
             "finding": "This is an abstract/metadata-level re-fetch, not a full-text theorem "
                        "check; verification_status=abstract-read remains the honest level."},
            {"id": "SPOT23-F-03", "severity": "info",
             "finding": f"{len(soft)} class-binding gap(s) and {len(hard)} hard failure(s) "
                        "recorded for lead adjudication; no ledger edit was made."},
            {"id": "SPOT23-F-04", "severity": "info",
             "finding": "Instrument revision 3 (documented in instrument_revision) corrected "
                        "rev1/rev2 checker defects before this result set; sample and pin were "
                        "unchanged and both earlier outputs are preserved."},
        ],
        "falsifiers": [
            "Re-running this script against the same pinned csv sha256 returns a different "
            "per-row verdict set (non-reproducible fetch evidence).",
            "Any sampled locator resolves to a work whose title/author/year contradicts the row: "
            "the MATCH verdict for that row is false.",
            "A row outside this 5-row sample is later found to have a fabricated locator: this "
            "falsifies only the sampling inference, not the per-row results.",
        ],
        "falsifier_outcome": ("NOT fired" if not hard else "FIRED - see hard_failures"),
        "limitations": [
            f"{len(SAMPLE_ROWS)} of {len(rows)} data rows sampled; the ledger is not clean "
            "outside the sample.",
            "Excerpt grounding is tested against fetched abstracts only; theorem scope vs "
            "regularity class is not decided here.",
            "The ledger was not modified (read-only run).",
        ],
        "non_claims": [
            "Does not claim the ledger is citation-clean outside the sampled rows.",
            "Does not promote any theorem, class, or gate; validation_status is unverified.",
            "Does not edit ledger/citation_audit.csv or any schema.",
        ],
        "reproduce": "python3 artifacts/worker-023/l1_spotcheck/run_spotcheck_023.py",
        "ledger_pin_observed_at_end": sha256_bytes(CSV_PATH.read_bytes()),
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    (OUT_DIR / "spotcheck-l1-023.json.sha256").write_text(
        sha256_bytes(OUT_PATH.read_bytes()) + "  spotcheck-l1-023.json\n")
    print(json.dumps({"summary": summary, "hard_failures": len(hard),
                      "artifact_sha256": sha256_bytes(OUT_PATH.read_bytes()),
                      "ledger_pin_observed_at_end": out["ledger_pin_observed_at_end"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
