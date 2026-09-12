#!/usr/bin/env python3
"""worker-070 bounded class-bound task: L1 as-recorded locator re-resolvability audit.

Question (G-LIT criterion: "ledger rows have resolvable locators"):
  Does the locator actually stored in ledger/citation_audit.csv `exact_locator`
  re-resolve, without modification, to the work the row claims?

Pre-declared method (frozen in this file before any network call):
  * Deterministic census over all data rows, classification rule below.
  * Live sample: for each locator family in FAMILY_ORDER take the 3 rows with the
    smallest 1-based data-row index. Additionally fetch `evidence_url` for every
    row that is elided AND has neither DOI nor arXiv id (rows with no printed
    identifier fallback). Hard cap LIVE_CAP = 18 fetches, fail closed if exceeded.
  * Match test: a fetched body "identifies" the row iff the stored DOI (case-folded)
    or arXiv id appears in the body, or some candidate title extracted from the body
    (title tags / JSON title|name fields) has >= 0.6 significant-token overlap with
    the ledger title.
  * Hash binding: ledger sha256 must equal LEDGER_SHA at start; re-measured after all
    fetches; any drift voids the artifact (fail closed).
  * No row is repaired, no ledger file is edited, no gate verdict and no node status
    is claimed. Worker evidence only.

Output: artifacts/worker-070/l1_locator_resolvability/census.json (+ raw/ snippets).
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
LEDGER = ROOT / "ledger" / "citation_audit.csv"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
OUTDIR = ROOT / "artifacts" / "worker-070" / "l1_locator_resolvability"
RAW = OUTDIR / "raw"
OUT = OUTDIR / "census.json"

LEDGER_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
THEOREMS_SHA = "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72"
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
FAMILY_ORDER = ["elided", "arxiv-api-query", "arxiv-abs", "other-url", "inspire-query"]
N_PER_STRATUM = 3
LIVE_CAP = 18
TIMEOUT = 15
UA = "worker-070-locator-resolvability/1.0 (research audit; contact: swarm worker-070)"

CST = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(u: str) -> str:
    u = (u or "").strip()
    if not u:
        return "empty"
    if "..." in u:
        return "elided"
    if "export.arxiv.org/api/query" in u:
        return "arxiv-api-query"
    if "inspirehep.net/api/literature" in u:
        return "inspire-query"
    if re.match(r"https?://(www\.)?arxiv\.org/abs/", u):
        return "arxiv-abs"
    if u.startswith("http://") or u.startswith("https://"):
        return "other-url"
    return "not-a-url"


def norm(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def sig_tokens(title: str, n: int = 10) -> list[str]:
    return [t for t in norm(title).split() if len(t) > 2][:n]


def candidate_titles(body: str) -> list[str]:
    cands = re.findall(r"<title[^>]*>(.*?)</title>", body, flags=re.S | re.I)
    cands += re.findall(r"<dc:title[^>]*>(.*?)</dc:title>", body, flags=re.S | re.I)
    cands += re.findall(r'"(?:title|name)"\s*:\s*"([^"]{8,400})"', body)
    return cands


def identifies(body: str, row: dict) -> tuple[bool, str]:
    low = (body or "").lower()
    doi = (row.get("doi") or "").strip().lower()
    ax = (row.get("arxiv_id") or "").strip().lower()
    if doi and doi in low:
        return True, f"doi:{doi}"
    if ax and re.search(r"(?<![0-9.])" + re.escape(ax) + r"(?![0-9])", low):
        return True, f"arxiv_id:{ax}"
    sig = set(sig_tokens(row.get("title", "")))
    if not sig:
        return False, "no-title-tokens"
    best = 0.0
    for c in candidate_titles(body):
        toks = set(norm(c).split())
        if not toks:
            continue
        ov = len(sig & toks) / len(sig)
        best = max(best, ov)
    if best >= 0.6:
        return True, f"title_overlap:{best:.2f}"
    return False, f"title_overlap:{best:.2f}"


def fetch(url: str) -> dict:
    res = {"url": url, "http_status": None, "bytes": 0, "sha256": None,
           "exception": None, "snippet_file": None}
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read()
                res["http_status"] = r.status
            res["bytes"] = len(body)
            res["sha256"] = hashlib.sha256(body).hexdigest()
            text = body.decode("utf-8", "replace")
            name = hashlib.sha256(url.encode()).hexdigest()[:16] + ".txt"
            (RAW / name).write_text(text[:20000], encoding="utf-8")
            res["snippet_file"] = f"raw/{name}"
            res["_body"] = text
            return res
        except urllib.error.HTTPError as e:
            res["http_status"] = e.code
            res["exception"] = f"HTTPError:{e.code}"
            if e.code in (429, 503) and attempt == 1:
                time.sleep(6)
                continue
            try:
                body = e.read()
                text = body.decode("utf-8", "replace")
                res["bytes"] = len(body)
                res["sha256"] = hashlib.sha256(body).hexdigest()
                name = hashlib.sha256(url.encode()).hexdigest()[:16] + ".txt"
                (RAW / name).write_text(text[:20000], encoding="utf-8")
                res["snippet_file"] = f"raw/{name}"
                res["_body"] = text
            except Exception:
                pass
            return res
        except Exception as e:  # noqa: BLE001
            res["exception"] = f"{type(e).__name__}:{e}"
            return res
    return res


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(exist_ok=True)

    ledger_sha_start = sha256_file(LEDGER)
    theorems_sha_start = sha256_file(THEOREMS)
    if ledger_sha_start != LEDGER_SHA:
        print(f"FAIL-CLOSED: ledger sha {ledger_sha_start} != pinned {LEDGER_SHA}", file=sys.stderr)
        return 2
    if theorems_sha_start != THEOREMS_SHA:
        print(f"FAIL-CLOSED: theorems sha {theorems_sha_start} != pinned {THEOREMS_SHA}", file=sys.stderr)
        return 2

    with open(LEDGER, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 97, len(rows)

    theorems = {}
    for line in THEOREMS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            theorems[d["theorem_id"]] = d

    census = []
    for i, r in enumerate(rows, 1):
        fam = classify(r["exact_locator"])
        refs = [t.strip() for t in re.split(r"[;|,]", r.get("used_by_theorems", "")) if t.strip()]
        bound = sorted({c for t in refs for c in theorems.get(t, {}).get("class_ids", [])})
        census.append({
            "row": i,
            "citation_id": r["citation_id"],
            "title": r["title"],
            "doi": r["doi"],
            "arxiv_id": r["arxiv_id"],
            "exact_locator": r["exact_locator"],
            "evidence_url": r["evidence_url"],
            "locator_family": fam,
            "has_doi_or_arxiv": bool(r["doi"].strip() or r["arxiv_id"].strip()),
            "no_identifier_fallback": (not r["doi"].strip() and not r["arxiv_id"].strip()),
            "class_mapping": r["class_mapping"],
            "used_by_theorems": refs,
            "theorem_bound_classes": bound,
            "verdict": None,
            "live": None,
        })

    # Pre-declared live sample: first N_PER_STRATUM rows per family in FAMILY_ORDER.
    sample = []
    for fam in FAMILY_ORDER:
        got = [c for c in census if c["locator_family"] == fam][:N_PER_STRATUM]
        sample += got
    no_fallback = [c for c in census if c["locator_family"] == "elided" and c["no_identifier_fallback"]]
    if len(sample) + len(no_fallback) > LIVE_CAP:
        print("FAIL-CLOSED: live sample exceeds cap", file=sys.stderr)
        return 2

    n_fetches = 0
    for c in sample:
        res = fetch(c["exact_locator"])
        n_fetches += 1
        body = res.pop("_body", "")
        ok, why = identifies(body, c)
        status = res["http_status"]
        if c["locator_family"] == "elided":
            c["verdict"] = "UNRESOLVABLE_STRUCTURAL"
            if ok:
                c["verdict"] = "FALSIFIER_ELIDED_BUT_IDENTIFIED"
        elif res["exception"]:
            c["verdict"] = "RATE_LIMITED" if status in (429, 503) else f"FETCH_FAILED_{status or 'EXC'}"
        elif status == 200 and ok:
            c["verdict"] = "RESOLVABLE"
        elif status == 200 and not ok:
            c["verdict"] = "NON_IDENTIFYING"
        else:
            c["verdict"] = f"HTTP_{status}"
        res["identifies"] = ok
        res["match_rule"] = why
        c["live"] = res
        time.sleep(1.5)

    for c in no_fallback:
        res = fetch(c["evidence_url"])
        n_fetches += 1
        body = res.pop("_body", "")
        ok, why = identifies(body, c)
        res["identifies"] = ok
        res["match_rule"] = why
        res["role"] = "fallback_evidence_url (exact_locator elided, no doi/arxiv in row)"
        c["fallback_live"] = res
        time.sleep(1.5)

    ledger_sha_end = sha256_file(LEDGER)
    theorems_sha_end = sha256_file(THEOREMS)
    drift = (ledger_sha_end != LEDGER_SHA) or (theorems_sha_end != THEOREMS_SHA)

    fam_counts = {f: sum(1 for c in census if c["locator_family"] == f) for f in
                  FAMILY_ORDER + ["empty", "not-a-url"]}
    per_class = {}
    for cls in FROZEN + ["(evidence/tag only)"]:
        sel = [c for c in census if cls in [t.strip() for t in re.split(r"[;,]", c["class_mapping"])]]
        per_class[cls] = {
            "rows": len(sel),
            "elided": sum(1 for c in sel if c["locator_family"] == "elided"),
            "no_identifier_fallback": sum(1 for c in sel if c["no_identifier_fallback"]),
        }

    elided_rows = [c["row"] for c in census if c["locator_family"] == "elided"]
    nofb_rows = [c["citation_id"] for c in census if c["no_identifier_fallback"]]
    falsifier_hits = [c["row"] for c in census if c["verdict"] == "FALSIFIER_ELIDED_BUT_IDENTIFIED"]

    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_locator_resolvability_audit",
        "task_id": "w070-l1-locator-resolvability-01",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": FROZEN,
        "actor": "worker-070",
        "reviewer": "worker-070",
        "created_at": now_iso(),
        "authority": ("worker evidence only; no gate verdict, no node status, no validation_status=passed. "
                      "The literature lead owns ledger/citation_audit.csv; this run does not edit it."),
        "question": ("Does the locator stored in citation_audit.csv `exact_locator` re-resolve, without "
                     "modification, to the work the row claims?"),
        "inputs": {
            "ledger/citation_audit.csv": {"sha256_pinned": LEDGER_SHA, "sha256_start": ledger_sha_start,
                                          "sha256_end": ledger_sha_end, "data_rows": len(rows)},
            "ledger/theorems.jsonl": {"sha256_pinned": THEOREMS_SHA, "sha256_start": theorems_sha_start,
                                      "sha256_end": theorems_sha_end, "entries": len(theorems)},
        },
        "method": {
            "classification_rule": {
                "empty": "blank",
                "elided": "contains the literal three-dot token '...'",
                "arxiv-api-query": "host export.arxiv.org, path /api/query",
                "inspire-query": "host inspirehep.net, path /api/literature (not elided)",
                "arxiv-abs": "host arxiv.org, path /abs/<id>",
                "other-url": "any other absolute http(s) URL without '...'",
            },
            "live_sample_rule": f"first {N_PER_STRATUM} rows by data-row index in each family, in order {FAMILY_ORDER}; plus evidence_url for every elided row lacking DOI and arXiv id",
            "match_rule": "stored DOI (case-folded) or arXiv id appears in the body, or a candidate title from the body has >=0.6 significant-token overlap with the ledger title",
            "live_fetches": n_fetches,
            "live_cap": LIVE_CAP,
            "fail_closed": "ledger/theorems hash drift during the run voids the artifact",
        },
        "census": census,
        "aggregate": {
            "rows": len(rows),
            "family_counts": fam_counts,
            "elided_rows": elided_rows,
            "elided_count": len(elided_rows),
            "rows_without_doi_and_arxiv": nofb_rows,
            "rows_without_doi_and_arxiv_count": len(nofb_rows),
            "verdict_counts": {v: sum(1 for c in census if c["verdict"] == v) for v in
                               sorted({str(c["verdict"]) for c in census})},
            "per_class": per_class,
            "falsifier_hits": falsifier_hits,
        },
        "hard_failures": [
            {"kind": "column_semantics",
             "finding": f"{len(elided_rows)}/97 rows store an elided `exact_locator` (literal '...' inside the query); the stored locator cannot be re-resolved as recorded.",
             "rows": elided_rows},
            {"kind": "no_identifier_fallback",
             "finding": f"{len(nofb_rows)} elided rows also carry no DOI and no arXiv id, so the row has no printed resolvable identifier in the doi/arxiv_id columns; a resolvable pointer exists only in `evidence_url` (checked live).",
             "rows": nofb_rows},
        ] if not drift else [
            {"kind": "hash_drift", "finding": "ledger or theorems sha changed during the run; artifact void.", "rows": []}
        ],
        "falsifier": ("A row classified `elided` whose as-recorded locator, fetched unmodified, returns a body "
                      "identifying the row's work falsifies the column-semantics finding; a row classified as a "
                      "non-elided identifier/query whose as-recorded fetch returns a different work falsifies its "
                      "RESOLVABLE verdict; ledger drift away from 315c19145065 or theorems drift away from "
                      "ce42d205e761 voids the whole artifact."),
        "drift": drift,
        "status": "draft-unverified; spot/census evidence only",
    }

    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"family_counts={fam_counts}")
    print(f"elided={len(elided_rows)} no_identifier_fallback={nofb_rows}")
    print(f"verdicts={artifact['aggregate']['verdict_counts']}")
    print(f"falsifier_hits={falsifier_hits} drift={drift} fetches={n_fetches}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
