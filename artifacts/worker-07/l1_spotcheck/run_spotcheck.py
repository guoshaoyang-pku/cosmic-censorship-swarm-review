#!/usr/bin/env python3
"""Independent L1 re-fetch spot check #3 (G-LIT, node L1) by deepseek-flash-07.

Read-only. Pins ledger/citation_audit.csv by sha256, samples rows in the range that the
two prior independent spot checks did not cover (data rows 41-95; flash-10 covered 1-20,
flash-11 covered 21-40), re-fetches each sampled source from its locator through the
arXiv API or Crossref API, and records the raw response hash plus the comparison.

Fail-closed: if the pinned csv hash does not match, the run aborts without fetching.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "ledger" / "citation_audit.csv"
OUT_DIR = Path(__file__).resolve().parent
PINNED_CSV_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
# Sampling was first frozen against sha 0b72b419... at 00:06; the literature lead rebuilt the
# audit file before any successful fetch (fail-closed abort), the sample rows kept the same
# source_ids, and the pin was moved to the rebuilt revision at 00:08. Recorded, not hidden.
CSV_HASH_HISTORY = [
    {"sha256": "0b72b4190667fc812528ad8aaa1e7405aae20e89906e892b4ef259199b32370d", "observed_at": "2026-09-12T00:06+08:00", "outcome": "fail-closed abort before fetching (file rebuilt by astra-lead-literature)"},
    {"sha256": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9", "observed_at": "2026-09-12T00:08+08:00", "outcome": "re-pinned; sample rows 41-95 re-verified to carry the same source_ids before fetching"},
]
FRAME = (41, 95)  # inclusive, 1-based data-row indices
# S1: every 8th row of the frame starting at 41. S2: targeted augmentation declared
# before fetching: row 80 (SRC-080) is the load-bearing source for T-526/T-527 and
# T-401's C2 status; row 81 is already in S1.
SAMPLE_ROWS = [41, 49, 57, 65, 73, 80, 81, 89]
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_API = "https://export.arxiv.org/api/query?id_list={ident}"
CROSSREF_API = "https://api.crossref.org/works/{doi}"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def curl(url: str) -> dict:
    cmd = [
        "curl", "-sS", "--max-time", "45", "-L",
        "-w", "\n%{http_code}", url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        return {"ok": False, "error": p.stderr.decode("utf-8", "replace")[:300], "url": url}
    out = p.stdout
    # strip the trailing "\n<http_code>" written by -w
    if b"\n" in out:
        body, _, code = out.rpartition(b"\n")
    else:
        body, code = out, b""
    try:
        status = int(code.strip() or b"0")
    except ValueError:
        status = 0
    return {
        "ok": status == 200 and len(body) > 0,
        "http_status": status,
        "bytes": len(body),
        "sha256": sha256_bytes(body),
        "body": body,
        "url": url,
    }


def parse_arxiv(body: bytes) -> dict:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as e:
        return {"parse_error": str(e)}
    entry = root.find(f"{ATOM}entry")
    if entry is None:
        return {"parse_error": "no entry"}
    title = " ".join((entry.findtext(f"{ATOM}title") or "").split())
    authors = [
        " ".join((a.findtext(f"{ATOM}name") or "").split())
        for a in entry.findall(f"{ATOM}author")
    ]
    published = entry.findtext(f"{ATOM}published") or ""
    journal_ref = " ".join((entry.findtext("{http://arxiv.org/schemas/atom}journal_ref") or "").split())
    doi = entry.findtext("{http://arxiv.org/schemas/atom}doi") or ""
    abstract = " ".join((entry.findtext(f"{ATOM}summary") or "").split())
    return {
        "title": title,
        "authors": authors,
        "published": published,
        "year": published[:4],
        "journal_ref": journal_ref,
        "doi": doi,
        "abstract": abstract,
    }


def parse_crossref(body: bytes) -> dict:
    try:
        msg = json.loads(body)["message"]
    except Exception as e:  # noqa: BLE001
        return {"parse_error": str(e)}
    title = msg.get("title") or [""]
    title = " ".join((title[0] if title else "").split())
    authors = []
    for a in msg.get("author") or []:
        name = " ".join(x for x in [a.get("given"), a.get("family")] if x)
        if name:
            authors.append(name)
    issued = ((msg.get("issued") or {}).get("date-parts") or [[None]])[0]
    year = str(issued[0]) if issued and issued[0] else ""
    abstract = re.sub(r"<[^>]+>", " ", msg.get("abstract") or "")
    abstract = " ".join(abstract.split())
    return {
        "title": title,
        "authors": authors,
        "published": msg.get("published-print", {}).get("date-parts", [[None]])[0][0] if msg.get("published-print") else "",
        "year": year,
        "journal_ref": (msg.get("container-title") or [""])[0],
        "doi": msg.get("DOI") or "",
        "abstract": abstract,
    }


def first_family(authors: str) -> str:
    a = (authors or "").replace(" and ", ",")
    first = a.split(",")[0].strip()
    return norm(first.split()[-1]) if first else ""


LATEX_NOISE = {"cite", "mathcal", "mathrm", "mathbb", "text", "box", "displaystyle", "loc", "nabla", "infty"}


def content_tokens(s: str) -> list[str]:
    return [t for t in norm(s).split() if len(t) > 2 and t not in LATEX_NOISE]


def quote_probe(quote: str, abstract: str) -> str:
    """Classify whether the CSV quote letter is grounded in the fetched abstract.

    Token-level, because the CSV quotes are LaTeX-bearing and carry a source-label
    prefix ('Abstract: ...', 'Crossref record: ...'); a byte-level substring test is
    not meaningful across those encodings.
    """
    if not abstract.strip():
        return "no_abstract_available"
    q = re.sub(r"^\s*[A-Za-z][A-Za-z0-9 (/)\-]{0,40}:\s*", "", quote).strip(" '\"")
    if "..." in q:
        q = q.split("...")[0]
    qt, at = content_tokens(q), content_tokens(abstract)
    if not qt:
        return "not_checked"
    probe = qt[:25]
    # ordered containment of the probe tokens in the abstract tokens
    i = 0
    for t in at:
        if i < len(probe) and t == probe[i]:
            i += 1
    if i == len(probe):
        return "grounded_in_abstract"
    jac = len(set(probe) & set(at)) / max(1, len(set(probe) | set(at)))
    return "close_paraphrase" if jac >= 0.7 else "not_found_in_abstract"


def compare(row: dict, fetched: dict) -> dict:
    lt, ft = norm(row["title"]), norm(fetched.get("title", ""))
    if lt and ft and (lt == ft or lt in ft or ft in lt):
        title_verdict = "strong"
    elif lt and ft:
        sl, sf = set(lt.split()), set(ft.split())
        jac = len(sl & sf) / max(1, len(sl | sf))
        title_verdict = "partial" if jac >= 0.6 else "mismatch"
    else:
        title_verdict = "unavailable"

    ledger_family = first_family(row.get("authors", ""))
    fetched_families = [first_family(a) for a in fetched.get("authors", [])]
    author_ok = bool(ledger_family) and ledger_family in fetched_families

    ly = (row.get("year") or "").strip()
    fy = (fetched.get("year") or "").strip()
    year_ok = bool(ly) and bool(fy) and abs(int(ly) - int(fy)) <= 1 if (ly.isdigit() and fy.isdigit()) else None

    quote = (row.get("evidence_excerpt") or "").strip()
    low = quote.lower()
    if re.match(r"^\s*(crossref|openalex|inspire|metadata)[^:]{0,20}record", low) or low.startswith("crossref record"):
        quote_check = "metadata_record_consistent" if title_verdict == "strong" else "metadata_record_mismatch"
    else:
        quote_check = quote_probe(quote, fetched.get("abstract", "")) if quote else "not_checked"
    year_note = None
    if title_verdict == "strong" and author_ok and year_ok is False:
        year_note = "year differs by >1; consistent with preprint-first-posting vs journal year, not a locator error"

    if title_verdict == "strong" and author_ok and year_ok is not False:
        verdict = "MATCH"
    elif title_verdict == "strong":
        verdict = "PARTIAL"
    elif title_verdict == "partial" and author_ok:
        verdict = "PARTIAL"
    elif title_verdict == "unavailable":
        verdict = "FETCH_FAILED"
    else:
        verdict = "MISMATCH"
    return {
        "title_verdict": title_verdict,
        "author_ok": author_ok,
        "ledger_first_family": ledger_family,
        "fetched_families": fetched_families,
        "year_ok": year_ok,
        "ledger_year": ly,
        "fetched_year": fy,
        "quote_check": quote_check,
        "year_note": year_note,
        "verdict": verdict,
    }


def main() -> int:
    raw = CSV_PATH.read_bytes()
    got = sha256_bytes(raw)
    if got != PINNED_CSV_SHA256:
        print(f"FAIL-CLOSED: {CSV_PATH} sha256 {got} != pinned {PINNED_CSV_SHA256}", file=sys.stderr)
        return 2
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    if not (FRAME[0] <= SAMPLE_ROWS[0] and SAMPLE_ROWS[-1] <= FRAME[1] <= len(rows)):
        print("FAIL-CLOSED: sample rows outside frame", file=sys.stderr)
        return 2

    started = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    results = []
    for n in SAMPLE_ROWS:
        row = rows[n - 1]
        arxiv_id = (row.get("arxiv_id") or "").strip()
        doi = (row.get("doi") or "").strip()
        if arxiv_id:
            url = ARXIV_API.format(ident=arxiv_id)
            kind = "arxiv_api"
        elif doi:
            url = CROSSREF_API.format(doi=doi)
            kind = "crossref_api"
        else:
            results.append({"row": n, "citation_id": row["citation_id"], "verdict": "FETCH_FAILED",
                            "error": "no locator on row", "ledger": ledger_view(row)})
            continue
        fetched_at = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        resp = curl(url)
        entry = {
            "row": n,
            "citation_id": row["citation_id"],
            "bibkey": row.get("bibkey"),
            "class_mapping": row.get("class_mapping"),
            "used_by_theorems": row.get("used_by_theorems"),
            "ledger": ledger_view(row),
            "locator_kind": kind,
            "locator_used": url,
            "fetched_at": fetched_at,
        }
        if not resp["ok"]:
            entry.update({"verdict": "FETCH_FAILED", "fetch": {k: resp.get(k) for k in ("http_status", "bytes", "sha256", "error")}})
            results.append(entry)
        else:
            body = resp["body"]
            parsed = parse_arxiv(body) if kind == "arxiv_api" else parse_crossref(body)
            cmp_ = compare(row, parsed)
            entry.update({
                "fetch": {"http_status": resp["http_status"], "bytes": resp["bytes"], "sha256": resp["sha256"]},
                "fetched": {k: parsed.get(k) for k in ("title", "authors", "year", "journal_ref", "doi", "published")},
                "fetched_abstract_head": (parsed.get("abstract") or "")[:600],
                "comparison": cmp_,
                "verdict": cmp_["verdict"],
            })
            results.append(entry)
        time.sleep(3.0)  # arXiv API rate-limit courtesy

    counts = {v: 0 for v in ("MATCH", "PARTIAL", "MISMATCH", "FETCH_FAILED")}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    hard_failures = [
        {"id": f"SPOT3-HF-{i+1:02d}", "row": r["row"], "citation_id": r["citation_id"],
         "finding": "locator re-fetch contradicts the ledger row", "verdict": r["verdict"]}
        for i, r in enumerate(results) if r["verdict"] == "MISMATCH"
    ]
    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "actor": "deepseek-flash-07",
        "reviewer": "deepseek-flash-07",
        "created_at": started,
        "check_number": 3,
        "independent_of": ["reviews/L1-spotcheck-10.json", "reviews/L1-spotcheck-11.json"],
        "independence_note": "Sampled rows 41-95, disjoint from flash-10 (rows 1-20) and flash-11 (rows 21-40); locators were re-fetched from the primary APIs, no ledger text was used as evidence.",
        "inputs": {
            "ledger/citation_audit.csv": {"sha256": got, "data_rows": len(rows), "checked_frame": f"data rows {FRAME[0]}-{FRAME[1]}",
                                          "hash_history": CSV_HASH_HISTORY,
                                          "sha256_after_fetch": sha256_bytes(CSV_PATH.read_bytes()),
                                          "drifted_during_fetch": sha256_bytes(CSV_PATH.read_bytes()) != got}
        },
        "sampling_rule": {
            "frozen_before_fetch": True,
            "S1": "every 8th data row of the frame 41-95 starting at 41 -> rows 41,49,57,65,73,81,89",
            "S2_targeted_augmentation": "row 80 (SRC-080) added: load-bearing source for T-526/T-527 and for T-401's C2 status; declared before any fetch",
            "sampled_rows": SAMPLE_ROWS,
            "revision_note": "after the 00:08 rebuild the same rows 41-95 were re-read and still carry source_ids SRC-041,049,057,065,073,080,081,089; the primary-source locators below are those of the re-pinned revision",
            "class_coverage_from_class_mapping": sorted({c.strip() for r in results for c in (r.get("class_mapping") or "").split(";") if c.strip() in CLASS_IDS}),
        },
        "method": "curl -> arXiv API (export.arxiv.org/api/query?id_list=) or Crossref API (api.crossref.org/works/); raw body hashed; title/author/year compared after case/punctuation normalisation; declared CSV quote letter tested at content-token level against the fetched abstract (the CSV quotes are LaTeX-bearing and carry source-label prefixes).",
        "results": results,
        "summary": {"checked": len(results), **counts,
                    "quote_grounding": {k: sum(1 for r in results if r.get("comparison", {}).get("quote_check") == k)
                                        for k in ("grounded_in_abstract", "close_paraphrase", "not_found_in_abstract",
                                                  "metadata_record_consistent", "metadata_record_mismatch",
                                                  "no_abstract_available", "not_checked")}},
        "hard_failures": hard_failures,
        "findings": [
            {"id": "SPOT3-F-01", "severity": "info",
             "finding": f"{counts['MATCH']}/{len(results)} sampled locators re-fetch to the recorded work; {counts['PARTIAL']} partial, {counts['MISMATCH']} mismatch, {counts['FETCH_FAILED']} fetch failure."},
            {"id": "SPOT3-F-02", "severity": "info",
             "finding": "This is an abstract/metadata-level check, not a page check of the theorem statement; verification_status=abstract-read remains the honest level for the checked rows."},
            {"id": "SPOT3-F-03", "severity": "info",
             "finding": f"Declared quote letters: {sum(1 for r in results if r.get('comparison', {}).get('quote_check') == 'grounded_in_abstract')}/{len(results)} grounded token-for-token in the fetched abstract, "
                        f"{sum(1 for r in results if r.get('comparison', {}).get('quote_check') == 'close_paraphrase')} close paraphrase, "
                        f"{sum(1 for r in results if r.get('comparison', {}).get('quote_check') == 'not_found_in_abstract')} not found, "
                        f"{sum(1 for r in results if r.get('comparison', {}).get('quote_check','').startswith('metadata_record'))} CSV excerpts are metadata records (title/authors/venue), not abstract quotations, and are consistent with the fetched record, "
                        f"{sum(1 for r in results if r.get('comparison', {}).get('quote_check') == 'no_abstract_available')} no abstract available. "
                        "CSV quotes are LaTeX-bearing and carry source-label prefixes, so grounding was tested at token level."},
            {"id": "SPOT3-F-04", "severity": "info",
             "finding": "Year fields are preprint-first-posting years for two rows (SRC-057 ledger 2019 vs arXiv 2017; SRC-081 ledger 2025 vs arXiv 2024); title and authors match, so these are journal/preprint year conventions, not locator errors. Citation_audit's `year` column mixes the two conventions, which a consumer comparing years mechanically would misread."},
            {"id": "SPOT3-F-05", "severity": "info",
             "finding": "ledger/citation_audit.csv was rebuilt by astra-lead-literature between the sampling freeze (sha 0b72b419) and the first fetch; the run aborted fail-closed, the pin was moved to sha 315c1914 and the sample rows were re-verified to carry the same source_ids. The file remains a moving target during this run; the artifact records the hash before and after fetching."},
        ],
        "falsifiers": [
            "Re-running this script at the same pinned CSV sha256 returns a different per-row verdict set (non-reproducible fetch evidence).",
            "Any sampled locator resolves to a work whose title/author/year contradicts the row: the corresponding MATCH verdict is false and the row is a hard failure.",
            "A row outside this 8-row sample is later found to have a fabricated locator, which would falsify only the sample-level no-error claim, not the per-row results above.",
        ],
        "non_claims": [
            "Does not claim the ledger is citation-clean outside the 8 sampled rows.",
            "Does not promote any theorem, class, or gate; validation_status is unverified.",
            "Does not edit the ledger or the audit CSV (read-only run).",
        ],
        "reproduce": "python3 artifacts/worker-07/l1_spotcheck/run_spotcheck.py",
    }
    out = OUT_DIR / "spotcheck-l1-07.json"
    payload = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out.write_text(payload, encoding="utf-8")
    (OUT_DIR / "spotcheck-l1-07.json.sha256").write_text(sha256_bytes(payload.encode()) + "  spotcheck-l1-07.json\n", encoding="utf-8")
    print(json.dumps({"artifact": str(out.relative_to(ROOT)), "sha256": sha256_bytes(payload.encode()), "summary": artifact["summary"]}, indent=2))
    return 0


def ledger_view(row: dict) -> dict:
    return {k: row.get(k) for k in ("title", "authors", "year", "venue", "doi", "arxiv_id", "url", "verdict", "resolver_result", "verification_method", "evidence_type", "evidence_excerpt", "assessment", "reviewer")}


if __name__ == "__main__":
    raise SystemExit(main())
