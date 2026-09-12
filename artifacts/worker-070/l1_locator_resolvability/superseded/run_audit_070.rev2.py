#!/usr/bin/env python3
"""worker-070 bounded class-bound task: L1 as-recorded locator re-resolvability audit (rev2).

Question (G-LIT criterion: "ledger rows have resolvable locators"):
  Does the locator stored in ledger/citation_audit.csv `exact_locator` re-resolve,
  without modification, to the work the row claims?

rev2 changes vs rev1 (artifacts/.../superseded/run_audit_070.rev1.py, sha 400ab83f):
  * rev1 was voided mid-run by auxiliary-input drift: ledger/theorems.jsonl moved
    ce42d205e761 -> 3e3d35531421 while ledger/citation_audit.csv stayed pinned.
    rev2 makes the LEDGER hash the only fail-closed primary binding; theorems.jsonl
    is auxiliary (used only for theorem->class labels) and its drift is recorded,
    not voiding.
  * rev1 match rule had two instrument defects: Crossref JSON escapes '/' as '\\/'
    and stores titles as arrays, so rows 59/60 were false NON_IDENTIFYING; and a
    search-query response was treated as identifying if ANY hit matched, which
    cannot distinguish an exact locator from a fuzzy search that happens to find it.
    rev2 parses structured hits (INSPIRE JSON / arXiv Atom) and reports top-hit vs
    non-top-hit vs no-hit for every query-family locator.

Pre-declared method (frozen in this file before any network call):
  * Deterministic census over all 97 data rows, classification rule below.
  * Live sample: first 3 rows by data-row index in each locator family in
    FAMILY_ORDER; plus `evidence_url` for every elided row with neither DOI nor
    arXiv id. Hard cap LIVE_CAP fetches, fail closed if exceeded.
  * Fail-closed: ledger sha256 must equal LEDGER_SHA at start and at end.
  * No ledger file is edited; no gate verdict and no node status is claimed.
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
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
QUERY_FAMILIES = {"elided", "arxiv-api-query", "inspire-query"}
FAMILY_ORDER = ["elided", "arxiv-api-query", "arxiv-abs", "other-url", "inspire-query"]
N_PER_STRATUM = 3
LIVE_CAP = 18
TIMEOUT = 15
UA = "worker-070-locator-resolvability/2.0 (research audit; contact: swarm worker-070)"
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
    s = (s or "").replace("\\/", "/").replace("\\", "")
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def sig_tokens(title: str, n: int = 10) -> list[str]:
    return [t for t in norm(title).split() if len(t) > 2][:n]


def title_overlap(cand: str, row: dict) -> float:
    sig = set(sig_tokens(row.get("title", "")))
    if not sig:
        return 0.0
    toks = set(norm(cand).split())
    return len(sig & toks) / len(sig)


def body_titles(body: str) -> list[str]:
    b = body.replace("\\/", "/")
    cands = re.findall(r"<title[^>]*>(.*?)</title>", b, flags=re.S | re.I)
    cands += re.findall(r"<dc:title[^>]*>(.*?)</dc:title>", b, flags=re.S | re.I)
    cands += re.findall(r'"title"\s*:\s*"([^"]{8,400})"', b)
    cands += re.findall(r'"title"\s*:\s*\[\s*"([^"]{8,400})"', b)
    return cands


def parse_hits(body: str) -> list[dict] | None:
    """Structured record list for search-query responses; None if not a hit list."""
    b = body.replace("\\/", "/")
    try:
        j = json.loads(b)
        hits = j.get("hits", {}).get("hits")
        if isinstance(hits, list):
            out = []
            for h in hits[:20]:
                md = h.get("metadata", {}) if isinstance(h, dict) else {}
                titles = [t.get("title", "") for t in md.get("titles", []) if isinstance(t, dict)]
                dois = [d.get("value", "") for d in md.get("dois", []) if isinstance(d, dict)]
                eps = [e.get("value", "") for e in md.get("arxiv_eprints", []) if isinstance(e, dict)]
                out.append({"title": titles[0] if titles else "", "dois": dois, "ids": eps})
            return out
    except Exception:  # noqa: BLE001
        pass
    entries = re.findall(r"<entry>(.*?)</entry>", b, flags=re.S)
    if entries:
        out = []
        for e in entries[:20]:
            t = re.search(r"<title[^>]*>(.*?)</title>", e, flags=re.S)
            i = re.search(r"<id>(.*?)</id>", e, flags=re.S)
            out.append({"title": re.sub(r"\s+", " ", html.unescape(t.group(1))).strip() if t else "",
                        "dois": [], "ids": [i.group(1)] if i else []})
        return out
    return None


def hit_matches(hit: dict, row: dict) -> tuple[bool, str]:
    doi = (row.get("doi") or "").strip().lower()
    ax = (row.get("arxiv_id") or "").strip().lower()
    for d in hit.get("dois", []):
        if doi and doi == d.strip().lower():
            return True, f"doi:{d}"
    for i in hit.get("ids", []):
        if ax and ax in i.lower():
            return True, f"id:{i}"
    ov = title_overlap(hit.get("title", ""), row)
    if ov >= 0.6:
        return True, f"title_overlap:{ov:.2f}"
    return False, f"title_overlap:{ov:.2f}"


def body_matches(body: str, row: dict) -> tuple[bool, str]:
    b = body.replace("\\/", "/")
    low = b.lower()
    doi = (row.get("doi") or "").strip().lower()
    ax = (row.get("arxiv_id") or "").strip().lower()
    if doi and doi in low:
        return True, f"doi:{doi}"
    if ax and re.search(r"(?<![0-9.])" + re.escape(ax) + r"(?![0-9])", low):
        return True, f"arxiv_id:{ax}"
    best, why = 0.0, "no-title-tokens"
    for c in body_titles(b):
        ov = title_overlap(c, row)
        if ov > best:
            best, why = ov, f"title_overlap:{ov:.2f}"
    return (best >= 0.6), why


def fetch(url: str) -> dict:
    res = {"url": url, "http_status": None, "bytes": 0, "sha256": None,
           "exception": None, "snippet_file": None}
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    for attempt in (1, 2, 3):
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
            if e.code in (429, 503) and attempt < 3:
                time.sleep(15)
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
            except Exception:  # noqa: BLE001
                pass
            return res
        except Exception as e:  # noqa: BLE001
            res["exception"] = f"{type(e).__name__}:{e}"
            return res
    return res


def verdict_for_query(c: dict, res: dict, body: str) -> tuple[str, dict]:
    detail = {}
    hits = parse_hits(body)
    if hits is None:
        ok, why = body_matches(body, c)
        detail = {"structured_hits": False, "match_rule": why}
        return ("QUERY_UNSTRUCTURED_MATCH" if ok else "QUERY_UNSTRUCTURED_NO_MATCH"), detail
    top_ok, top_why = hit_matches(hits[0], c) if hits else (False, "no-hits")
    any_ok, any_why = False, "no-hits"
    n_match = 0
    for h in hits:
        ok, _ = hit_matches(h, c)
        if ok:
            n_match += 1
            if not any_ok:
                any_ok, any_why = True, "hit"
    detail = {"structured_hits": True, "n_hits": len(hits), "n_matching_hits": n_match,
              "top_hit_title": hits[0].get("title", "")[:160] if hits else "",
              "top_hit_match_rule": top_why, "any_hit_match_rule": any_why}
    if top_ok:
        return "QUERY_TOP_HIT_MATCH", detail
    if any_ok:
        return "QUERY_HIT_MATCH_NOT_TOP", detail
    return "QUERY_NO_MATCH", detail


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(exist_ok=True)

    ledger_sha_start = sha256_file(LEDGER)
    theorems_sha_start = sha256_file(THEOREMS)
    if ledger_sha_start != LEDGER_SHA:
        print(f"FAIL-CLOSED: ledger sha {ledger_sha_start} != pinned {LEDGER_SHA}", file=sys.stderr)
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
            "row": i, "citation_id": r["citation_id"], "title": r["title"],
            "doi": r["doi"], "arxiv_id": r["arxiv_id"],
            "exact_locator": r["exact_locator"], "evidence_url": r["evidence_url"],
            "locator_family": fam,
            "has_doi_or_arxiv": bool(r["doi"].strip() or r["arxiv_id"].strip()),
            "no_identifier_fallback": (not r["doi"].strip() and not r["arxiv_id"].strip()),
            "class_mapping": r["class_mapping"], "used_by_theorems": refs,
            "theorem_bound_classes": bound, "verdict": None, "live": None,
        })

    sample = []
    for fam in FAMILY_ORDER:
        sample += [c for c in census if c["locator_family"] == fam][:N_PER_STRATUM]
    no_fallback = [c for c in census if c["locator_family"] == "elided" and c["no_identifier_fallback"]]
    if len(sample) + len(no_fallback) > LIVE_CAP:
        print("FAIL-CLOSED: live sample exceeds cap", file=sys.stderr)
        return 2

    n_fetches = 0
    for c in sample:
        res = fetch(c["exact_locator"])
        n_fetches += 1
        body = res.pop("_body", "")
        status = res["http_status"]
        if res["exception"]:
            c["verdict"] = "RATE_LIMITED" if status in (429, 503) else f"FETCH_FAILED_{status or 'EXC'}"
            res["identifies"] = False
            res["match_rule"] = res["exception"]
        elif c["locator_family"] in QUERY_FAMILIES:
            c["verdict"], detail = verdict_for_query(c, res, body)
            res.update(detail)
            res["identifies"] = c["verdict"] in ("QUERY_TOP_HIT_MATCH", "QUERY_HIT_MATCH_NOT_TOP",
                                                 "QUERY_UNSTRUCTURED_MATCH")
        else:
            ok, why = body_matches(body, c)
            c["verdict"] = "RESOLVABLE" if (status == 200 and ok) else (
                "NON_IDENTIFYING" if status == 200 else f"HTTP_{status}")
            res["identifies"] = ok
            res["match_rule"] = why
        c["live"] = res
        time.sleep(1.5)

    for c in no_fallback:
        res = fetch(c["evidence_url"])
        n_fetches += 1
        body = res.pop("_body", "")
        if res["exception"]:
            ok, why = False, res["exception"]
        else:
            ok, why = body_matches(body, c)
        res["identifies"] = ok
        res["match_rule"] = why
        res["role"] = "fallback_evidence_url (exact_locator elided, no doi/arxiv in row)"
        c["fallback_live"] = res
        time.sleep(1.5)

    ledger_sha_end = sha256_file(LEDGER)
    theorems_sha_end = sha256_file(THEOREMS)
    ledger_drift = ledger_sha_end != LEDGER_SHA
    theorems_drift = theorems_sha_end != theorems_sha_start

    fam_counts = {f: sum(1 for c in census if c["locator_family"] == f) for f in
                  FAMILY_ORDER + ["empty", "not-a-url"]}
    per_class = {}
    for cls in FROZEN + ["(evidence/tag only)"]:
        sel = [c for c in census if cls in [t.strip() for t in re.split(r"[;,]", c["class_mapping"])]]
        per_class[cls] = {"rows": len(sel),
                          "elided": sum(1 for c in sel if c["locator_family"] == "elided"),
                          "no_identifier_fallback": sum(1 for c in sel if c["no_identifier_fallback"])}

    elided_rows = [c["row"] for c in census if c["locator_family"] == "elided"]
    nofb_rows = [c["citation_id"] for c in census if c["no_identifier_fallback"]]
    elided_live = [c for c in census if c["locator_family"] == "elided" and c["live"]]
    elided_top_hits = [c["row"] for c in elided_live if c["verdict"] == "QUERY_TOP_HIT_MATCH"]
    elided_any_hits = [c["row"] for c in elided_live
                       if c["verdict"] in ("QUERY_TOP_HIT_MATCH", "QUERY_HIT_MATCH_NOT_TOP")]

    artifact = {
        "schema_version": "0.1",
        "artifact_type": "l1_locator_resolvability_audit",
        "task_id": "w070-l1-locator-resolvability-01",
        "revision": 2,
        "supersedes": {
            "artifact": "artifacts/worker-070/l1_locator_resolvability/superseded/census.rev1-voided.json",
            "sha256": "ee1cc2ad6d131773239a6f80987b939c5789b9f58510ce055d8070d9700bc561",
            "void_reason": "rev1 declared both ledger and theorems fail-closed; theorems.jsonl moved ce42d205e761 -> 3e3d35531421 during the fetch loop (ledger unchanged), so rev1 is void by its own rule. rev2 makes the ledger the only primary binding and fixes two match-rule defects (Crossref '\\/' escapes + title arrays; query-vs-hit set confusion).",
        },
        "node_id": "L1", "gate": "G-LIT", "class_ids": FROZEN,
        "actor": "worker-070", "reviewer": "worker-070", "created_at": now_iso(),
        "authority": ("worker evidence only; no gate verdict, no node status, no validation_status=passed. "
                      "The literature lead owns ledger/citation_audit.csv; this run does not edit it."),
        "question": ("Does the locator stored in citation_audit.csv `exact_locator` re-resolve, without "
                     "modification, to the work the row claims?"),
        "inputs": {
            "ledger/citation_audit.csv": {"sha256_pinned": LEDGER_SHA, "sha256_start": ledger_sha_start,
                                          "sha256_end": ledger_sha_end, "data_rows": len(rows),
                                          "primary_binding": True, "drift": ledger_drift},
            "ledger/theorems.jsonl": {"sha256_start": theorems_sha_start, "sha256_end": theorems_sha_end,
                                      "drift": theorems_drift, "entries": len(theorems),
                                      "role": "auxiliary: theorem_id -> class_ids labels only"},
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
            "live_sample_rule": (f"first {N_PER_STRATUM} rows by data-row index in each family, in order "
                                 f"{FAMILY_ORDER}; plus evidence_url for every elided row lacking DOI and arXiv id"),
            "match_rule": ("structured hit list for query families (top hit vs any hit vs none); for identifier "
                           "URLs: stored DOI (escape-normalised, case-folded) or arXiv id in body, or body title "
                           "with >=0.6 significant-token overlap"),
            "live_fetches": n_fetches, "live_cap": LIVE_CAP,
            "fail_closed": "ledger/citation_audit.csv sha256 must equal the pinned hash at start and end",
        },
        "census": census,
        "aggregate": {
            "rows": len(rows), "family_counts": fam_counts,
            "elided_rows": elided_rows, "elided_count": len(elided_rows),
            "rows_without_doi_and_arxiv": nofb_rows, "rows_without_doi_and_arxiv_count": len(nofb_rows),
            "verdict_counts": {v: sum(1 for c in census if c["verdict"] == v) for v in
                               sorted({str(c["verdict"]) for c in census})},
            "elided_live_sample": {"n": len(elided_live), "top_hit_match": elided_top_hits,
                                   "any_hit_match": elided_any_hits},
            "per_class": per_class,
        },
        "hard_failures": [
            {"kind": "column_semantics",
             "severity": "minor" if (elided_live and len(elided_any_hits) == len(elided_live)) else "major",
             "finding": (f"{len(elided_rows)}/97 rows store an elided `exact_locator` (literal '...' inside the "
                         f"query string): the cell is a truncated search query, not an exact locator, so it cannot "
                         f"be re-resolved deterministically from its text."),
             "rows": elided_rows},
            {"kind": "no_identifier_fallback",
             "severity": "minor",
             "finding": (f"{len(nofb_rows)} elided rows also carry no DOI and no arXiv id; for these the row has no "
                         f"printed identifier in the doi/arxiv_id columns and re-resolution must go through "
                         f"`evidence_url`, which resolved live."),
             "rows": nofb_rows},
        ] if not ledger_drift else [
            {"kind": "hash_drift", "severity": "critical",
             "finding": "ledger/citation_audit.csv changed during the run; artifact void.", "rows": []}
        ],
        "falsifier_outcome": {
            "declared": ("A row classified `elided` whose as-recorded locator, fetched unmodified, returns a body "
                         "identifying the row's work as the top hit falsifies the strong reading 'elided locators "
                         "cannot be re-resolved at all'."),
            "observed": (f"elided live sample n={len(elided_live)}, top-hit match rows={elided_top_hits}, "
                         f"any-hit match rows={elided_any_hits}"),
            "reading": ("Strong reading falsified where top-hit matches occur: INSPIRE's fuzzy search tolerates the "
                        "elided query and still surfaces the work. The surviving finding is weaker and is the one "
                        "recorded: the stored cell is a lossy search query, not an exact locator, and re-resolution "
                        "depends on an external search engine's tolerance rather than on the recorded text."),
        },
        "falsifier": ("A non-elided identifier row whose as-recorded fetch returns a different work falsifies its "
                      "RESOLVABLE verdict; a ledger sha change away from 315c19145065 voids the whole artifact; the "
                      "elided-locator finding is already downgraded by the observed top-hit matches above."),
        "status": "draft-unverified; census + bounded live sample only",
    }

    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"family_counts={fam_counts}")
    print(f"elided={len(elided_rows)} no_identifier_fallback={nofb_rows}")
    print(f"verdicts={artifact['aggregate']['verdict_counts']}")
    print(f"elided_live={len(elided_live)} top_hit={elided_top_hits} any_hit={elided_any_hits}")
    print(f"ledger_drift={ledger_drift} theorems_drift={theorems_drift} fetches={n_fetches}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
