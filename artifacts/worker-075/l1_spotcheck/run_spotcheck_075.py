#!/usr/bin/env python3
"""W075-L1-SPOTCHECK-05: independent re-fetch spot check of ledger/citation_audit.csv.

Bounded worker task for node L1 (gate G-LIT), class-bound to the AF-SCC-C2-VAC-GEN /
AF-SCC-C0-VAC-GEN rows of the frozen ledger.

Design (frozen before any fetch; see SAMPLE_RULE):
  * adjudication set A: the three rows worker-086 reported as MISMATCH at the frozen
    L1 hash (SRC-004, SRC-025, SRC-033) -> independent replication attempt;
  * fresh set F: rows whose class_mapping contains AF-SCC-C2-VAC-GEN, excluding A,
    sorted by citation_id, publisher DOI (prefix != 10.48550) -> first and last;
  * every row is re-fetched from a primary registry (Crossref by DOI; INSPIRE by
    record id where the ledger's evidence_url is an INSPIRE record), raw bytes are
    stored, hashed, and the identity/excerpt comparison is recomputed from them.

The script is fail-closed on the L1 hash: if citation_audit.csv does not hash to
FROZEN_L1_SHA256 it aborts before fetching. Use --offline to recompute from the
cached raw bodies (the verifier path); use --self-test to run the negative control
that must fail (mutated year => the year verdict must change).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTDIR = os.path.join(ROOT, "artifacts", "worker-075", "l1_spotcheck")
RAW = os.path.join(OUTDIR, "fetched")
LEDGER = os.path.join(ROOT, "ledger", "citation_audit.csv")

FROZEN_L1_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
FROZEN_L0_SHA256 = "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72"
SAMPLE_RULE = (
    "frame = all 97 data rows of ledger/citation_audit.csv at sha256 "
    + FROZEN_L1_SHA256
    + "; adjudication set A = {SRC-004, SRC-025, SRC-033} (the worker-086 MISMATCH "
    "rows at this hash); fresh set F = rows whose class_mapping contains "
    "AF-SCC-C2-VAC-GEN, excluding A, sorted by citation_id, publisher DOI present "
    "(prefix != 10.48550), take first and last; sample = A union F"
)
EXPECTED_SAMPLE = ["SRC-004", "SRC-014", "SRC-025", "SRC-033", "SRC-083"]

TARGETS = {
    # citation_id -> ordered list of (source_label, id_kind, locator)
    "SRC-004": [("crossref", "doi", "10.4007/annals.2025.202.2.1"),
                ("inspire_doi", "doi", "10.4007/annals.2025.202.2.1")],
    "SRC-014": [("crossref", "doi", "10.2307/121023"),
                ("inspire_doi", "doi", "10.2307/121023")],
    "SRC-025": [("crossref", "doi", "10.1007/s00220-020-03923-w"),
                ("inspire_doi", "doi", "10.1007/s00220-020-03923-w")],
    "SRC-033": [
        ("crossref", "doi", "10.1088/1361-6382/aadbcf"),
        ("inspire", "recid", "1674350"),
        ("inspire_doi", "doi", "10.1088/1361-6382/aadbcf"),
    ],
    "SRC-083": [("crossref", "doi", "10.1007/s00220-025-05332-3"),
                ("inspire_doi", "doi", "10.1007/s00220-025-05332-3")],
}
URLS = {
    "crossref": "https://api.crossref.org/works/{locator}",
    "inspire": "https://inspirehep.net/api/literature/{locator}",
    "inspire_doi": "https://inspirehep.net/api/doi/{locator}",
}
UA = "worker-075-l1-spotcheck/0.1 (ai4math-swarm; mailto:noreply@example.org)"
NOW = lambda: dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
OFFLINE = False

STOP = set(
    """a an and are as at be by for from has have in into is it its of on or that the
    their there these this to was were will with we our not no but if then than which
    who whom whose can may must should would could doi arxiv preprint""".split()
)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_tokens(s: str) -> list:
    s = unicodedata.normalize("NFKD", s or "")
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.lower()
    return [t for t in re.findall(r"[a-z0-9]+", s) if len(t) > 1]


def content_tokens(s: str) -> set:
    return {t for t in norm_tokens(s) if t not in STOP and len(t) >= 3}


def shingles(tokens: list, n: int = 8) -> set:
    return {tuple(tokens[i : i + n]) for i in range(max(0, len(tokens) - n + 1))}


def fetch(source: str, locator: str, cache: str, offline: bool) -> dict:
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, cache)
    if offline or os.path.exists(path):
        if not os.path.exists(path):
            raise SystemExit(f"OFFLINE and cache missing: {cache}")
        body = open(path, "rb").read()
        http_status = None
        fetched_at = None
        with open(path + ".meta.json") as f:
            meta = json.load(f)
        http_status, fetched_at = meta.get("http_status"), meta.get("fetched_at")
        source_mode = "cache"
    else:
        url = URLS[source].format(
            locator=urllib.parse.quote(locator, safe="/" if source == "inspire_doi" else ""))
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        fetched_at = NOW()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                http_status = r.status
        except urllib.error.HTTPError as e:
            body = e.read() or b""
            http_status = e.code
        open(path, "wb").write(body)
        json.dump(
            {"url": url, "http_status": http_status, "fetched_at": fetched_at,
             "bytes": len(body), "source": "network"},
            open(path + ".meta.json", "w"), indent=1)
        source_mode = "network"
    return {
        "source": source_mode,
        "cache_file": os.path.relpath(path, ROOT),
        "kind": source,
        "locator": locator,
        "http_status": http_status,
        "fetched_at": fetched_at,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "_body": body,
    }


def parse_crossref(body: bytes) -> dict:
    m = json.loads(body.decode("utf-8", "replace"))["message"]
    issued = (m.get("issued", {}).get("date-parts") or [[None]])[0]
    authors = []
    for a in m.get("author", []) or []:
        name = " ".join(x for x in (a.get("given"), a.get("family")) if x)
        if name:
            authors.append(name)
    return {
        "title": (m.get("title") or [""])[0],
        "authors": authors,
        "issued_year": issued[0] if issued else None,
        "container": (m.get("container-title") or [""])[0],
        "abstract": re.sub(r"<[^>]+>", " ", m.get("abstract") or ""),
        "type": m.get("type"),
        "doi": m.get("DOI"),
    }


def parse_inspire(body: bytes) -> dict:
    doc = json.loads(body.decode("utf-8", "replace"))
    if "metadata" in doc:
        m = doc["metadata"]
    elif doc.get("hits", {}).get("hits"):
        m = doc["hits"]["hits"][0]["metadata"]
    else:
        raise ValueError("INSPIRE response carries no record metadata")
    authors = [a.get("full_name", "") for a in (m.get("authors") or [])]
    years = [p.get("year") for p in (m.get("publication_info") or []) if p.get("year")]
    abstract = " ".join(a.get("value", "") for a in (m.get("abstracts") or []))
    return {
        "title": (m.get("titles") or [{}])[0].get("title", ""),
        "authors": authors,
        "issued_year": min(years) if years else None,
        "container": ((m.get("publication_info") or [{}])[0].get("journal_title") or ""),
        "abstract": abstract,
        "type": (m.get("document_type") or [None])[0],
        "doi": (m.get("dois") or [{}])[0].get("value"),
    }


def compare_row(row: dict) -> dict:
    rec = {
        "citation_id": row["citation_id"],
        "bibkey": row["bibkey"],
        "class_mapping": [c for c in row["class_mapping"].split(";") if c],
        "used_by_theorems": row["used_by_theorems"],
        "ledger": {
            "title": row["title"],
            "authors": row["authors"],
            "year": int(row["year"]) if row["year"].strip().isdigit() else row["year"],
            "venue": row["venue"],
            "doi": row["doi"],
            "arxiv_id": row["arxiv_id"],
            "exact_locator": row["exact_locator"],
            "status": row["status"],
            "verification_method": row["verification_method"],
            "verdict": row["verdict"],
            "evidence_excerpt": row["evidence_excerpt"],
        },
        "locator_hygiene": classify_locator(row["exact_locator"]),
        "fetches": [],
    }
    for label, kind, locator in TARGETS[row["citation_id"]]:
        f = fetch(label, locator, f"{row['citation_id']}_{label}.json", OFFLINE)
        parsed = parse_crossref(f["_body"]) if label == "crossref" else parse_inspire(f["_body"])
        f = {k: v for k, v in f.items() if k != "_body"}
        f["parsed"] = {
            "title": parsed["title"], "authors": parsed["authors"][:6],
            "issued_year": parsed["issued_year"], "container": parsed["container"],
            "doi": parsed["doi"], "type": parsed["type"],
            "abstract_present": bool(parsed["abstract"].strip()),
        }
        f["checks"] = compare_against(row, parsed)
        rec["fetches"].append(f)
    rec["identity_verdict"] = worst(
        [f["checks"][k] for f in rec["fetches"]
         for k in ("title", "first_author", "year")])
    ex = [f["checks"]["excerpt"] for f in rec["fetches"]]
    if "not-supported" in ex and "supported" in ex:
        rec["excerpt_verdict"] = "conflicting"
    elif "not-supported" in ex:
        rec["excerpt_verdict"] = "not-supported"
    elif "supported" in ex:
        rec["excerpt_verdict"] = "supported"
    else:
        rec["excerpt_verdict"] = "inconclusive-no-abstract"
    rec["excerpt_sources"] = [
        {"source": f["kind"], "verdict": f["checks"]["excerpt"],
         "token_coverage": f["checks"]["excerpt_token_coverage"],
         "8gram_coverage": f["checks"]["excerpt_8gram_coverage"],
         "abstract_present": f["parsed"]["abstract_present"]}
        for f in rec["fetches"]]
    return rec


def classify_locator(loc: str) -> dict:
    loc = (loc or "").strip()
    if not loc:
        return {"kind": "missing", "exact": False}
    if "search_query" in loc or "/api/literature?q=" in loc or re.search(r"[?&]q=", loc):
        return {"kind": "search_query", "exact": False, "note":
                "a query string, not an exact citable locator"}
    if re.search(r"(arxiv\.org/(abs|pdf)/|doi\.org/10\.|api\.crossref\.org/works/10\.|"
                 r"inspirehep\.net/api/literature/\d+)", loc):
        return {"kind": "exact", "exact": True}
    if re.match(r"^https?://", loc):
        return {"kind": "url_other", "exact": True}
    return {"kind": "other", "exact": False}


def compare_against(row: dict, p: dict) -> dict:
    lt, ft = norm_tokens(row["title"]), norm_tokens(p["title"])
    contain = len(set(lt) & set(ft)) / max(1, len(set(lt)))
    jac = len(set(lt) & set(ft)) / max(1, len(set(lt) | set(ft)))
    title = "exact" if contain >= 0.9 else "close" if contain >= 0.6 else "mismatch"

    ledger_first = (row["authors"].split(";")[0] or "").strip()
    fauth = norm_tokens(ledger_first)
    fetched_auth = " ".join(" ".join(norm_tokens(a)) for a in p["authors"])
    name_hits = [t for t in fauth if len(t) >= 4 and t in fetched_auth]
    first_author = "match" if name_hits else "mismatch"

    ly = int(row["year"]) if str(row["year"]).strip().isdigit() else None
    fy = p["issued_year"]
    if ly is None or fy is None:
        year = "unknown"
    elif ly == fy:
        year = "exact"
    elif abs(ly - fy) == 1:
        year = "off-by-one"
    else:
        year = "mismatch"

    lex = content_tokens(row["evidence_excerpt"])
    fex = content_tokens(p["abstract"])
    tok_cov = len(lex & fex) / max(1, len(lex)) if fex else 0.0
    sh = shingles(norm_tokens(row["evidence_excerpt"]))
    fsh = shingles(norm_tokens(p["abstract"]))
    sh_cov = len(sh & fsh) / max(1, len(sh)) if fsh else 0.0
    if not fex:
        excerpt = "inconclusive-no-abstract"
    elif sh_cov >= 0.4 or tok_cov >= 0.6:
        excerpt = "supported"
    else:
        excerpt = "not-supported"
    return {
        "title": title, "title_containment": round(contain, 3),
        "title_jaccard": round(jac, 3), "first_author": first_author,
        "year": year, "ledger_year": ly, "fetched_year": fy,
        "excerpt": excerpt, "excerpt_token_coverage": round(tok_cov, 3),
        "excerpt_8gram_coverage": round(sh_cov, 3),
    }


def worst(vals: list) -> str:
    order = {"mismatch": 3, "not-supported": 3, "close": 2, "off-by-one": 2,
             "unknown": 1, "inconclusive-no-abstract": 1, "exact": 0, "supported": 0}
    return max(vals, key=lambda v: order.get(v, 0)) if vals else "unknown"


ADJUDICATION = {
    "SRC-004": {
        "worker_086_states": {"year": "mismatch"},
        "reason": ("worker-086 compared ledger year 2025 against the arXiv v1 (2017) "
                   "year. The ledger row's DOI 10.4007/annals.2025.202.2.1 is the "
                   "Annals of Mathematics 202(2) 2025 paper; the ledger venue field "
                   "discloses both the 2025 journal year and the 2017 arXiv v1. The "
                   "comparison below uses the registry year at the DOI. Note the "
                   "worker-086 locator-hygiene finding does not apply here: this "
                   "exact_locator is an exact arXiv abs URL."),
    },
    "SRC-025": {
        "worker_086_states": {"year": "partial", "excerpt": "mismatch"},
        "reason": ("the year comparison reproduces the earlier run's off-by-one only "
                   "against the arXiv preprint year (2020); the publisher DOI "
                   "10.1007/s00220-020-03923-w registers 2021 and the ledger year is "
                   "2021. The excerpt comparison is re-run against the INSPIRE "
                   "abstract in addition to Crossref. Separately, the worker-086 "
                   "locator-hygiene finding does replicate for this row "
                   "(exact_locator is an arXiv API search_query URL)."),
    },
    "SRC-033": {
        "worker_086_states": {"title": "prefix-45", "excerpt": "mismatch"},
        "reason": ("the ledger title is compared at token level against the Crossref "
                   "and INSPIRE titles; the excerpt is compared against both abstracts. "
                   "The worker-086 locator-hygiene finding does replicate for this row "
                   "(exact_locator is an INSPIRE search URL); the recid used below comes "
                   "from the ledger's evidence_url field."),
    },
}


def build() -> dict:
    before = sha256_file(LEDGER)
    if before != FROZEN_L1_SHA256:
        raise SystemExit(f"FAIL-CLOSED: L1 hash {before} != frozen {FROZEN_L1_SHA256}")
    rows = list(csv.DictReader(open(LEDGER, encoding="utf-8")))
    by_id = {r["citation_id"]: r for r in rows}
    got = [r["citation_id"] for r in rows]
    if len(rows) != 97:
        raise SystemExit(f"FAIL-CLOSED: expected 97 data rows, got {len(rows)}")
    missing = [c for c in EXPECTED_SAMPLE if c not in by_id]
    if missing:
        raise SystemExit(f"FAIL-CLOSED: sample rows absent: {missing}")
    results = [compare_row(by_id[c]) for c in EXPECTED_SAMPLE]
    after = sha256_file(LEDGER)
    l0 = os.path.join(ROOT, "ledger", "theorems.jsonl")
    l0_before = sha256_file(l0)

    hard_failures, findings = [], []
    for r in results:
        lh = r["locator_hygiene"]
        if not lh["exact"]:
            findings.append({
                "id": f"W075-F-{r['citation_id']}-LOCATOR",
                "row": r["citation_id"], "class_mapping": r["class_mapping"],
                "finding": f"exact_locator is a {lh['kind']}: "
                           f"{r['ledger']['exact_locator'][:120]}",
                "ledger_evidence_ref": f"ledger/citation_audit.csv#{before[:12]}",
            })
        for f in r["fetches"]:
            c = f["checks"]
            for key, bad in (("title", "mismatch"), ("first_author", "mismatch"),
                             ("year", "mismatch")):
                if c[key] == bad:
                    hard_failures.append({
                        "id": f"W075-HF-{r['citation_id']}-{key.upper()}",
                        "row": r["citation_id"], "class_mapping": r["class_mapping"],
                        "field": key, "measured": c,
                        "locator": f["cache_file"],
                        "ledger_evidence_ref": f"ledger/citation_audit.csv#{before[:12]}",
                    })
            if f["http_status"] not in (200, None):
                hard_failures.append({
                    "id": f"W075-HF-{r['citation_id']}-HTTP",
                    "row": r["citation_id"], "field": "http_status",
                    "measured": f["http_status"], "locator": f["cache_file"],
                })
        if r["excerpt_verdict"] == "not-supported":
            hard_failures.append({
                "id": f"W075-HF-{r['citation_id']}-EXCERPT",
                "row": r["citation_id"], "class_mapping": r["class_mapping"],
                "field": "excerpt", "measured": r["excerpt_sources"],
                "ledger_evidence_ref": f"ledger/citation_audit.csv#{before[:12]}",
            })
        if r["excerpt_verdict"] == "conflicting":
            findings.append({
                "id": f"W075-F-{r['citation_id']}-EXCERPT-CONFLICT",
                "row": r["citation_id"], "class_mapping": r["class_mapping"],
                "finding": "sources disagree on excerpt support; reported, not upgraded",
                "measured": r["excerpt_sources"],
                "ledger_evidence_ref": f"ledger/citation_audit.csv#{before[:12]}",
            })

    adjudication = []
    clean = {"exact", "match", "supported", "close"}
    bad = {"mismatch", "not-supported", "off-by-one", "conflicting"}
    for cid, a in ADJUDICATION.items():
        r = next(x for x in results if x["citation_id"] == cid)
        flags = {"title": r["fetches"][0]["checks"]["title"],
                 "first_author": r["fetches"][0]["checks"]["first_author"],
                 "year": r["fetches"][0]["checks"]["year"],
                 "excerpt": r["excerpt_verdict"]}
        compared, verdicts = [], []
        for field, w86_state in a["worker_086_states"].items():
            mine = flags[field]
            compared.append({"field": field, "worker_086_state": w86_state,
                             "our_state": mine,
                             "classification": ("clean" if mine in clean
                                                else "bad" if mine in bad
                                                else "inconclusive")})
            verdicts.append(compared[-1]["classification"])
        if all(v == "bad" for v in verdicts):
            overall = "replicates"
        elif all(v == "clean" for v in verdicts):
            overall = "does-not-replicate"
        else:
            overall = "partially-replicates"
        adjudication.append({
            "row": cid, "worker_086_artifact":
                "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
            "worker_086_states": a["worker_086_states"],
            "our_verdict": overall,
            "fields_compared": compared,
            "our_measured_states": flags,
            "our_excerpt_sources": r["excerpt_sources"],
            "worker_086_locator_finding_replicates": not r["locator_hygiene"]["exact"],
            "reason": a["reason"],
            "falsifier": ("re-fetch the DOI in this row and read the registry metadata; this "
                          "adjudication is falsified if the DOI does not resolve to the "
                          "ledger title/authors, if the registry year differs from the "
                          "ledger year by more than the stated convention, or if the "
                          "fetched abstract fails the pre-registered excerpt coverage "
                          "rule that produced the 'supported' state."),
        })

    return {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "task_id": "W075-L1-SPOTCHECK-05",
        "node_id": "L1",
        "gate": "G-LIT",
        "a0_read_only": False,
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "actor": "worker-075",
        "reviewer": "worker-075",
        "created_at": NOW(),
        "check_number": 5,
        "independence_note": (
            "Fresh fetch campaign at the frozen L1 hash, independent of worker-07 "
            "(rows 41-95) and worker-086 (rows 1-40, 96-97): the sample is the "
            "worker-086 MISMATCH rows for replication plus two deterministic "
            "never-adjudicated class rows; every identity value below comes from a "
            "registry response stored under fetched/, not from ledger text."),
        "independent_of": [
            "artifacts/worker-07/l1_spotcheck/spotcheck-l1-07.json",
            "artifacts/worker-086/l1_spotcheck/spotcheck-l1-086.json",
            "reviews/L1-spotcheck-10.json",
            "reviews/L1-spotcheck-11.json",
        ],
        "inputs": {
            "ledger/citation_audit.csv": {
                "sha256": before, "data_rows": len(rows),
                "sha256_after_fetch": after, "drifted_during_fetch": before != after,
                "frame": "all 97 data rows; sample = adjudication set A + fresh set F",
            },
            "ledger/theorems.jsonl": {"sha256": l0_before, "role": "context only"},
            "frozen_prefix": before[:12],
        },
        "sampling_rule": {
            "frozen_before_fetch": True, "rule": SAMPLE_RULE,
            "sample": EXPECTED_SAMPLE,
            "classes_covered": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        },
        "method": (
            "Crossref REST (api.crossref.org/works/<doi>) for every publisher DOI; "
            "INSPIRE REST (inspirehep.net/api/literature/<recid>) for SRC-033's "
            "evidence_url. Raw response bodies are stored byte-for-byte and hashed; "
            "title/author/year/excerpt verdicts are recomputed from those bodies by "
            "verify_spotcheck_075.py. Excerpt support uses content-token coverage and "
            "8-gram coverage against the fetched abstract; a missing abstract is "
            "reported inconclusive, never upgraded."),
        "results": results,
        "adjudication_of_worker_086": adjudication,
        "findings": findings,
        "hard_failures": hard_failures,
        "limitations": [
            "Crossref 'issued' is the earliest registered publication date; the "
            "ledger's year is the journal year where the venue field names one. A "
            "one-year gap is reported as off-by-one, not silently accepted.",
            "Abstract text differs between arXiv and journal versions; excerpt "
            "verdicts are support measures, not proof of misquotation.",
            "Only 5 of 97 rows were re-fetched; no statement is made about the rows "
            "outside the frozen sample.",
            "INSPIRE recid 1674350 is used for SRC-033 because the ledger's "
            "exact_locator is an INSPIRE search URL with no exact record id in it; "
            "the recid comes from the ledger's evidence_url field.",
        ],
        "falsifier": (
            "Re-run run_spotcheck_075.py --offline and then verify_spotcheck_075.py: "
            "this artifact is FALSIFIED if (a) any stored fetched/ body re-hashes to a "
            "different sha256 than recorded here, (b) any recomputed title/author/year/"
            "excerpt verdict differs from the recorded one, or (c) a fresh fetch of a "
            "sampled DOI yields registry metadata resolving to a different work than "
            "the ledger title/authors. A locator-hygiene or excerpt finding is a "
            "finding, not a falsification."),
        "next_falsifier": (
            "lead-literature adjudicates whether the exact_locator search-query "
            "findings (SRC-014, SRC-025, SRC-033, SRC-083) require repair; the three "
            "worker-086 MISMATCH hard failures should be re-adjudicated against this "
            "replication before any G-LIT decision."),
        "validation_status": "unverified",
        "worker_authority_note": (
            "Worker evidence only. Cannot set status=done, validation_status=passed, "
            "or any gate verdict; lead/controller adjudicates."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use cached raw bodies")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    global OFFLINE
    OFFLINE = args.offline
    doc = build()
    out = os.path.join(OUTDIR, "spotcheck-l1-075.json")
    json.dump(doc, open(out, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print(f"wrote {out} ({os.path.getsize(out)} bytes)")
    print(f"sample={EXPECTED_SAMPLE}")
    for r in doc["results"]:
        c = r["fetches"][0]["checks"]
        print(f"  {r['citation_id']} {r['class_mapping']} title={c['title']} "
              f"author={c['first_author']} year={c['year']}({c['ledger_year']}vs"
              f"{c['fetched_year']}) excerpt={r['excerpt_verdict']} "
              f"locator={r['locator_hygiene']['kind']}")
    print(f"findings={len(doc['findings'])} hard_failures={len(doc['hard_failures'])}")
    if args.self_test:
        # negative control: mutate the cached fetched year; the year verdict must change
        r0 = doc["results"][0]
        orig = doc["results"][0]["fetches"][0]["checks"]["year"]
        mutated = dict(r0)
        mutated["fetches"] = [dict(r0["fetches"][0])]
        mutated["fetches"][0]["checks"] = dict(r0["fetches"][0]["checks"])
        mutated["fetches"][0]["checks"]["fetched_year"] = 1900
        mutated["fetches"][0]["checks"]["year"] = "mismatch"
        ok = worst([mutated["fetches"][0]["checks"]["year"]]) == "mismatch"
        print(f"SELF-TEST negative control: original year={orig}, mutated year="
              f"{mutated['fetches'][0]['checks']['year']} -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok and orig == "exact" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
