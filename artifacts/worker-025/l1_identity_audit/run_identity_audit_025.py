#!/usr/bin/env python3
"""W025-L1-IDENTITY-AUDIT-01

Full-population identifier -> bibliographic-record identity audit for
ledger/citation_audit.csv at the frozen hash.

Frozen inputs (sha256 pinned at run time, printed in the report):
  ledger/citation_audit.csv  315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9
  ledger/theorems.jsonl      a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28

Modes:
  default    fetch missing DOI/arXiv metadata into cache/, then build report.json
  --offline  never touch the network; rebuild report.json from the shipped cache only
             (byte-deterministic: no timestamps of the run are written into the report)

This script writes only under artifacts/worker-025/l1_identity_audit/.
It never edits the ledger, the map, or any frozen artifact.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
REPORT = os.path.join(HERE, "report.json")

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CSV_PATH = os.path.join(REPO, "ledger", "citation_audit.csv")
THEOREMS_PATH = os.path.join(REPO, "ledger", "theorems.jsonl")

PINNED_CSV = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
PINNED_THEOREMS = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"

JACCARD_MATCH = 0.60
RATIO_MATCH = 0.80

UA = "worker-025-identity-audit/1.0 (mailto:worker-025@ai4math-swarm.invalid)"

# ---------------------------------------------------------------- helpers


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def canon_title(s: str) -> str:
    """Deterministic title normalization: strip LaTeX/markup, fold accents, sort tokens."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\$[^$]*\$", " ", s)          # inline math
    s = re.sub(r"\\[a-zA-Z]+", " ", s)        # latex commands
    s = s.replace("{", " ").replace("}", " ").replace("\\", " ")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def toks(s: str) -> set:
    return set(canon_title(s).split())


def jaccard(a: str, b: str) -> float:
    ta, tb = toks(a), toks(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, canon_title(a), canon_title(b)).ratio()


def compatible(a: str, b: str) -> bool:
    """Frozen decision rule from PREREGISTRATION.json."""
    return jaccard(a, b) >= JACCARD_MATCH or ratio(a, b) >= RATIO_MATCH


def canon_arxiv_id(a: str) -> str:
    """Display form of an arXiv id (keeps legacy category prefix)."""
    a = (a or "").strip()
    a = re.sub(r"^arxiv:", "", a, flags=re.I)
    a = re.sub(r"v\d+$", "", a)
    return a


def norm_arxiv_key(a: str) -> str:
    """Lookup key for arXiv API responses.

    The arXiv Atom API normalizes legacy ids: id_list=gr-qc/0307013 comes back
    as <id>.../abs/0307013</id> (category prefix dropped). Both the request side
    and the response side are therefore keyed on the bare number.
    """
    return canon_arxiv_id(a).rsplit("/", 1)[-1]


def http_get(url: str, tries: int = 3, timeout: int = 40) -> tuple:
    """Return (status, body_text_or_None, error_or_None). Retries on 429/5xx/network."""
    last_err = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as exc:
            last_err = "HTTP %d" % exc.code
            if exc.code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            return exc.code, None, last_err
        except Exception as exc:  # noqa: BLE001 - network layer, recorded verbatim
            last_err = "%s: %s" % (type(exc).__name__, exc)
            time.sleep(1.0 * (attempt + 1))
    return 0, None, last_err


def cache_path(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return os.path.join(CACHE, safe + ".json")


def cache_get(name: str):
    p = cache_path(name)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def cache_put(name: str, obj) -> None:
    os.makedirs(CACHE, exist_ok=True)
    p = cache_path(name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, p)


# ---------------------------------------------------------------- fetch

ARXIV_CHUNK = 50


def fetch_doi(doi: str) -> dict:
    """Fetch one Crossref record; cached under doi_<doi>."""
    key = "doi_" + doi
    hit = cache_get(key)
    if hit is not None:
        return hit
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    status, body, err = http_get(url)
    rec = {"id": doi, "url": url, "http_status": status, "error": err, "body_sha256": None,
           "title": None, "authors": [], "year": None, "container": None,
           "arxiv_id_declared": None, "raw_ok": False}
    if body is not None:
        rec["body_sha256"] = sha256_bytes(body.encode("utf-8"))
        try:
            msg = json.loads(body).get("message", {})
            rec["title"] = (msg.get("title") or [None])[0]
            rec["authors"] = [
                " ".join(x for x in (a.get("given"), a.get("family")) if x)
                for a in (msg.get("author") or [])
            ]
            parts = (msg.get("issued") or {}).get("date-parts") or [[None]]
            rec["year"] = parts[0][0] if parts and parts[0] else None
            rec["container"] = (msg.get("container-title") or [None])[0]
            rec["arxiv_id_declared"] = msg.get("arxiv-id") or None
            if not rec["arxiv_id_declared"]:
                for alt in (msg.get("alternative-id") or []):
                    if str(alt).lower().startswith("arxiv:"):
                        rec["arxiv_id_declared"] = str(alt).split(":", 1)[1]
            rec["raw_ok"] = True
        except Exception as exc:  # noqa: BLE001
            rec["error"] = "parse: %s" % exc
    cache_put(key, rec)
    return rec


def fetch_datacite(doi: str) -> dict:
    """Fallback resolver for DOIs not registered with Crossref (arXiv 10.48550/* live at DataCite).

    Kept as a separate cached record so the report can say which registration
    agency actually holds the DOI instead of collapsing both into 'resolved'.
    """
    key = "datacite_" + doi
    hit = cache_get(key)
    if hit is not None:
        return hit
    url = "https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="")
    status, body, err = http_get(url)
    rec = {"id": doi, "url": url, "http_status": status, "error": err, "body_sha256": None,
           "title": None, "authors": [], "year": None, "container": None,
           "arxiv_id_declared": None, "raw_ok": False}
    if body is not None:
        rec["body_sha256"] = sha256_bytes(body.encode("utf-8"))
        try:
            attrs = (json.loads(body).get("data") or {}).get("attributes") or {}
            titles = attrs.get("titles") or []
            rec["title"] = titles[0].get("title") if titles else None
            rec["authors"] = [
                " ".join(x for x in (c.get("given"), c.get("family")) if x)
                for c in (attrs.get("creators") or [])
            ]
            rec["year"] = attrs.get("publicationYear")
            rec["container"] = (attrs.get("container") or {}).get("title")
            for ident in (attrs.get("identifiers") or []):
                if str(ident.get("identifierType", "")).lower() == "arxiv":
                    rec["arxiv_id_declared"] = ident.get("identifier")
            rec["raw_ok"] = bool(rec["title"])
        except Exception as exc:  # noqa: BLE001
            rec["error"] = "parse: %s" % exc
    cache_put(key, rec)
    return rec


def resolve_doi(doi: str) -> dict:
    """Crossref first; DataCite on a Crossref miss. Records which agency answered."""
    rec = fetch_doi(doi)
    if rec.get("raw_ok"):
        rec = dict(rec, resolved_via="crossref")
        return rec
    alt = fetch_datacite(doi)
    if alt.get("raw_ok"):
        alt = dict(alt, resolved_via="datacite",
                   crossref_http_status=rec.get("http_status"),
                   crossref_error=rec.get("error"))
        return alt
    return dict(rec, resolved_via=None, datacite_http_status=alt.get("http_status"),
                datacite_error=alt.get("error"))


def parse_arxiv_feed(xml: str) -> dict:
    """Minimal Atom parse: id -> {title, authors, year, doi}. No external deps."""
    out = {}
    for entry in re.findall(r"<entry>(.*?)</entry>", xml, flags=re.S):
        def grab(tag):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), entry, flags=re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else None
        raw_id = grab("id") or ""
        aid = norm_arxiv_key(raw_id.rsplit("/", 1)[-1])
        authors = re.findall(r"<author>\s*<name>(.*?)</name>", entry, flags=re.S)
        pub = grab("published") or ""
        mdoi = re.search(r'<arxiv:doi[^>]*>(.*?)</arxiv:doi>', entry, flags=re.S)
        out[aid] = {
            "title": grab("title"),
            "authors": [re.sub(r"\s+", " ", a).strip() for a in authors],
            "year": int(pub[:4]) if pub[:4].isdigit() else None,
            "doi_declared": mdoi.group(1).strip() if mdoi else None,
        }
    return out


def fetch_arxiv_batch(ids: list) -> dict:
    """Fetch arXiv metadata for a chunk; each chunk cached under arxiv_<first>_<n>.

    Caller passes display-form ids (legacy prefix allowed); responses are keyed
    on the bare numeric key that the API returns.
    """
    if not ids:
        return {}
    key = "arxiv_%s_%d" % (norm_arxiv_key(ids[0]).replace("/", "_"), len(ids))
    hit = cache_get(key)
    if hit is not None:
        return hit
    url = ("https://export.arxiv.org/api/query?id_list=%s&max_results=%d"
           % (",".join(ids), len(ids)))
    status, body, err = http_get(url, tries=3, timeout=60)
    rec = {"ids": ids, "url": url, "http_status": status, "error": err,
           "body_sha256": sha256_bytes(body.encode("utf-8")) if body else None,
           "entries": {}}
    if body:
        try:
            rec["entries"] = parse_arxiv_feed(body)
        except Exception as exc:  # noqa: BLE001
            rec["error"] = "parse: %s" % exc
    cache_put(key, rec)
    return rec


# ---------------------------------------------------------------- comparison


def _surname_tokens(name: str) -> set:
    """Token set for one author name, with single-letter initials dropped.

    'P T Chrusciel' and 'Piotr T. Chrusciel' must not be treated as different
    people; registries abbreviate given names inconsistently, so the comparison
    is carried by the multi-character (surname) tokens.
    """
    return {t for t in canon_title(name).split() if len(t) > 1}


def author_overlap(a: list, b: list) -> float:
    """Fraction of the shorter author list whose surname tokens appear in the other list."""
    if not a or not b:
        return -1.0
    sa = [_surname_tokens(x) for x in a if x and _surname_tokens(x)]
    sb = [_surname_tokens(x) for x in b if x and _surname_tokens(x)]
    if not sa or not sb:
        return -1.0
    hits = sum(1 for na in sa if any(na & nb for nb in sb))
    return hits / min(len(sa), len(sb))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="rebuild report.json from cache only; no network")
    args = ap.parse_args()

    csv_sha = sha256_file(CSV_PATH)
    if csv_sha != PINNED_CSV:
        print("FATAL: ledger/citation_audit.csv hash moved: %s != %s" % (csv_sha, PINNED_CSV),
              file=sys.stderr)
        return 2
    with open(THEOREMS_PATH, "rb") as fh:
        theorems_sha = sha256_bytes(fh.read())
    if theorems_sha != PINNED_THEOREMS:
        print("FATAL: ledger/theorems.jsonl hash moved: %s != %s"
              % (theorems_sha, PINNED_THEOREMS), file=sys.stderr)
        return 2

    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    # --- collect identifier universe, sorted for determinism
    dois = sorted({(r.get("doi") or "").strip().lower() for r in rows if (r.get("doi") or "").strip()})
    arxiv_ids = sorted({canon_arxiv_id(r.get("arxiv_id")) for r in rows if (r.get("arxiv_id") or "").strip()})

    doi_recs, arxiv_recs = {}, {}
    if not args.offline:
        for i, d in enumerate(dois):
            doi_recs[d] = resolve_doi(d)
            time.sleep(0.12)  # polite Crossref pacing
        for i in range(0, len(arxiv_ids), ARXIV_CHUNK):
            chunk = arxiv_ids[i:i + ARXIV_CHUNK]
            rec = fetch_arxiv_batch(chunk)
            for aid in chunk:
                arxiv_recs[aid] = (rec.get("entries") or {}).get(norm_arxiv_key(aid)) or {
                    "title": None, "authors": [], "year": None, "doi_declared": None,
                    "_chunk_error": rec.get("error"), "_http": rec.get("http_status"),
                }
            time.sleep(3.0)  # arXiv asks for >=3s between calls
    else:
        for d in dois:
            hit = cache_get("doi_" + d)
            if hit is not None and hit.get("raw_ok"):
                doi_recs[d] = dict(hit, resolved_via="crossref")
                continue
            alt = cache_get("datacite_" + d)
            if alt is not None and alt.get("raw_ok"):
                doi_recs[d] = dict(alt, resolved_via="datacite",
                                   crossref_http_status=(hit or {}).get("http_status"),
                                   crossref_error=(hit or {}).get("error"))
            elif hit is not None:
                doi_recs[d] = dict(hit, resolved_via=None)
        for i in range(0, len(arxiv_ids), ARXIV_CHUNK):
            chunk = arxiv_ids[i:i + ARXIV_CHUNK]
            hit = cache_get("arxiv_%s_%d" % (norm_arxiv_key(chunk[0]).replace("/", "_"), len(chunk)))
            if hit is not None:
                for aid in chunk:
                    arxiv_recs[aid] = (hit.get("entries") or {}).get(norm_arxiv_key(aid)) or {
                        "title": None, "authors": [], "year": None, "doi_declared": None,
                        "_chunk_error": hit.get("error"), "_http": hit.get("http_status"),
                    }

    # --- per-row adjudication
    out_rows = []
    counts = {}
    for idx, r in enumerate(rows, start=1):
        cid = r["citation_id"]
        doi = (r.get("doi") or "").strip().lower()
        aid = canon_arxiv_id(r.get("arxiv_id"))
        declared_title = r.get("title") or ""
        drec = doi_recs.get(doi) if doi else None
        arec = arxiv_recs.get(aid) if aid else None

        d_ok = bool(drec and drec.get("raw_ok") and drec.get("title"))
        a_ok = bool(arec and arec.get("title"))

        row = {
            "row": idx,
            "citation_id": cid,
            "doi": doi or None,
            "arxiv_id": aid or None,
            "declared_title": declared_title,
            "doi_http_status": (drec or {}).get("http_status"),
            "doi_resolved_via": (drec or {}).get("resolved_via"),
            "doi_error": (drec or {}).get("error"),
            "arxiv_http_status": (arec or {}).get("_http"),
            "arxiv_error": (arec or {}).get("_chunk_error"),
            "doi_title": (drec or {}).get("title"),
            "arxiv_title": (arec or {}).get("title"),
            "doi_year": (drec or {}).get("year"),
            "arxiv_year": (arec or {}).get("year"),
            "doi_authors": (drec or {}).get("authors") or [],
            "arxiv_authors": (arec or {}).get("authors") or [],
        }
        row["doi_vs_declared_jaccard"] = round(jaccard(row["doi_title"] or "", declared_title), 4) if d_ok else None
        row["doi_vs_declared_ratio"] = round(ratio(row["doi_title"] or "", declared_title), 4) if d_ok else None
        row["arxiv_vs_declared_jaccard"] = round(jaccard(row["arxiv_title"] or "", declared_title), 4) if a_ok else None
        row["arxiv_vs_declared_ratio"] = round(ratio(row["arxiv_title"] or "", declared_title), 4) if a_ok else None
        row["doi_vs_arxiv_jaccard"] = round(jaccard(row["doi_title"] or "", row["arxiv_title"] or ""), 4) if (d_ok and a_ok) else None
        row["doi_vs_arxiv_ratio"] = round(ratio(row["doi_title"] or "", row["arxiv_title"] or ""), 4) if (d_ok and a_ok) else None
        row["author_overlap_doi_arxiv"] = round(author_overlap(row["doi_authors"], row["arxiv_authors"]), 4) if (d_ok and a_ok) else None
        row["cross_link_doi_to_arxiv"] = (drec or {}).get("arxiv_id_declared")
        row["cross_link_arxiv_to_doi"] = (arec or {}).get("doi_declared")

        if not doi and not aid:
            verdict = "NO_IDENTIFIER"
        elif doi and aid and not (d_ok and a_ok):
            verdict = "FETCH_FAILED"
        elif doi and aid:
            linked = False
            if row["cross_link_doi_to_arxiv"]:
                linked = canon_arxiv_id(row["cross_link_doi_to_arxiv"]) == aid
            if not linked and row["cross_link_arxiv_to_doi"]:
                linked = row["cross_link_arxiv_to_doi"].lower().strip() == doi
            row["cross_linked"] = bool(linked)
            if linked or compatible(row["doi_title"], row["arxiv_title"]):
                verdict = "IDENTITY_MATCH"
            else:
                verdict = "IDENTITY_MISMATCH"
        elif doi:  # doi only
            verdict = "IDENTITY_MATCH" if compatible(row["doi_title"], declared_title) else "DOI_TITLE_MISMATCH"
        else:  # arxiv only
            verdict = "IDENTITY_MATCH" if compatible(row["arxiv_title"], declared_title) else "ARXIV_TITLE_MISMATCH"

        # author/year contradiction measured on the channel(s) that resolved
        contra = []
        decl_authors = [a.strip() for a in re.split(r"[;|]", r.get("authors") or "") if a.strip()]
        decl_year = (r.get("year") or "").strip()
        row["declared_authors"] = decl_authors
        row["declared_year"] = decl_year
        for chan, rec_authors, rec_year in (
            ("doi", row["doi_authors"], row["doi_year"]),
            ("arxiv", row["arxiv_authors"], row["arxiv_year"]),
        ):
            if chan == "doi" and not d_ok:
                continue
            if chan == "arxiv" and not a_ok:
                continue
            ov = author_overlap(decl_authors, rec_authors)
            if ov >= 0 and ov < 0.5:
                contra.append("%s authors overlap %.2f (declared %d vs record %d)"
                              % (chan, ov, len(decl_authors), len(rec_authors)))
            if decl_year.isdigit() and rec_year and abs(int(decl_year) - int(rec_year)) > 1:
                contra.append("%s year %s vs declared %s (likely preprint/journal offset)"
                              % (chan, rec_year, decl_year))
        row["author_or_year_contradiction"] = contra
        if contra and verdict in ("IDENTITY_MATCH", "DOI_TITLE_MISMATCH", "ARXIV_TITLE_MISMATCH"):
            verdict = "IDENTITY_MATCH_WITH_AUTHOR_YEAR_FLAG" if verdict == "IDENTITY_MATCH" else verdict
        row["verdict"] = verdict
        counts[verdict] = counts.get(verdict, 0) + 1
        out_rows.append(row)

    # --- duplicate identifier analysis (same record cited by >1 row)
    dups = []
    for label, keyf in (("doi", lambda r: (r.get("doi") or "").strip().lower()),
                        ("arxiv", lambda r: canon_arxiv_id(r.get("arxiv_id")))):
        seen = {}
        for r in rows:
            k = keyf(r)
            if k:
                seen.setdefault(k, []).append(r["citation_id"])
        for k, ids in sorted(seen.items()):
            if len(ids) > 1:
                dups.append({"kind": label, "identifier": k, "citation_ids": ids})

    # --- class coverage of the audit (all rows carry all four classes in practice)
    import collections
    per_class = collections.Counter()
    for r in rows:
        for c in (r.get("class_mapping") or "").split(";"):
            c = c.strip()
            if c:
                per_class[c] += 1

    # --- resolver accounting (which registration agency actually holds each DOI)
    resolver_counts = {}
    doi_prefix_counts = {}
    for r in out_rows:
        if r["doi"]:
            src = r["doi_resolved_via"] or "unresolved"
            resolver_counts[src] = resolver_counts.get(src, 0) + 1
            pfx = r["doi"].split("/")[0]
            doi_prefix_counts[pfx] = doi_prefix_counts.get(pfx, 0) + 1

    report = {
        "schema_version": "0.1",
        "artifact_type": "l1_identity_audit",
        "task_id": "W025-L1-IDENTITY-AUDIT-01",
        "actor": "worker-025",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "mode": "offline_replay",
        "mode_note": (
            "report.json is deliberately byte-identical between a cache-complete fetch run "
            "and an --offline replay: no run timestamp, host, or fetch/offline discriminator "
            "is written into it. Fetch provenance lives in cache_manifest.json."
        ),
        "inputs": {
            "ledger/citation_audit.csv": {"sha256": csv_sha, "data_rows": len(rows)},
            "ledger/theorems.jsonl": {"sha256": theorems_sha},
        },
        "frozen_thresholds": {"jaccard_match": JACCARD_MATCH, "ratio_match": RATIO_MATCH},
        "identifier_universe": {
            "unique_dois": len(dois),
            "unique_arxiv_ids": len(arxiv_ids),
            "rows_with_both": sum(1 for r in out_rows if r["doi"] and r["arxiv_id"]),
            "rows_with_doi_only": sum(1 for r in out_rows if r["doi"] and not r["arxiv_id"]),
            "rows_with_arxiv_only": sum(1 for r in out_rows if r["arxiv_id"] and not r["doi"]),
            "rows_with_neither": sum(1 for r in out_rows if not r["doi"] and not r["arxiv_id"]),
        },
        "counts": dict(sorted(counts.items())),
        "doi_registration_agency": dict(sorted(resolver_counts.items())),
        "doi_prefix_row_counts": dict(sorted(doi_prefix_counts.items())),
        "duplicate_identifier_citations": dups,
        "class_mapping_row_counts": dict(sorted(per_class.items())),
        "rows": out_rows,
        "summary": {
            "rows_audited": len(out_rows),
            "rows_resolved_both_channels": sum(1 for r in out_rows if r["doi_title"] and r["arxiv_title"]),
            "rows_resolved_at_least_one": sum(1 for r in out_rows if r["doi_title"] or r["arxiv_title"]),
            "identity_mismatches": counts.get("IDENTITY_MISMATCH", 0),
            "doi_title_mismatches": counts.get("DOI_TITLE_MISMATCH", 0),
            "arxiv_title_mismatches": counts.get("ARXIV_TITLE_MISMATCH", 0),
            "fetch_failed": counts.get("FETCH_FAILED", 0),
            "no_identifier": counts.get("NO_IDENTIFIER", 0),
            "author_or_year_flags": sum(1 for r in out_rows if r["author_or_year_contradiction"]),
            "duplicate_identifier_groups": len(dups),
        },
        "non_claims": [
            "This audit measures identifier->record identity only; it does not re-adjudicate evidence excerpts or content verdicts.",
            "It does not edit the ledger, the map, or any frozen artifact, and it sets no gate or node verdict.",
        ],
        "reproduce": "python3 artifacts/worker-025/l1_identity_audit/run_identity_audit_025.py --offline",
    }

    blob = json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(blob)

    # --- fetch provenance: one entry per cache file, so every resolved field is re-hashable
    manifest = {
        "schema_version": "0.1",
        "artifact_type": "l1_identity_audit_cache_manifest",
        "task_id": "W025-L1-IDENTITY-AUDIT-01",
        "report_sha256": sha256_bytes(blob.encode("utf-8")),
        "note": ("Every bibliographic field in report.json is derived from one of these cached "
                 "HTTP bodies; re-hash a file to confirm it is the body the report used. "
                 "Registry 404s are recorded rather than hidden: a DOI absent from Crossref is "
                 "then looked up at DataCite, which is how the arXiv-issued 10.48550/* DOIs "
                 "resolve."),
        "entries": [],
    }
    for name in sorted(os.listdir(CACHE)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(CACHE, name)
        with open(p, "rb") as fh:
            raw = fh.read()
        rec = json.loads(raw.decode("utf-8"))
        manifest["entries"].append({
            "cache_file": "cache/" + name,
            "cache_sha256": sha256_bytes(raw),
            "request_url": rec.get("url"),
            "http_status": rec.get("http_status"),
            "error": rec.get("error"),
            "body_sha256": rec.get("body_sha256"),
            "records": len(rec.get("entries") or {}) if "entries" in rec else 1,
        })
    mblob = json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(os.path.join(HERE, "cache_manifest.json"), "w", encoding="utf-8") as fh:
        fh.write(mblob)

    print("wrote", REPORT, "sha256", sha256_bytes(blob.encode("utf-8")))
    print("wrote cache_manifest.json sha256", sha256_bytes(mblob.encode("utf-8")),
          "entries", len(manifest["entries"]))
    print("counts:", json.dumps(dict(sorted(counts.items()))))
    print("summary:", json.dumps(report["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
