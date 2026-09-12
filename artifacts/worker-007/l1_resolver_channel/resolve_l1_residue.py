#!/usr/bin/env python3
"""W007-L1-RESOLVER-CHANNEL-01

Independent, live re-resolution of the L1 citation ledger's DOI/arXiv identity
audit (artifacts/worker-025/l1_identity_audit/report.json), plus the frozen
sub-population of 31 citation_ids that the superseded report revision
(a8703d304a5b) marked FETCH_FAILED.

Design constraints (see PREREGISTRATION.json, incl. amendment_01, written
before the first fetch of this task):
  * inputs are hash-pinned; a moved input aborts the run (exit 2);
  * DOIs are used with the case declared in the ledger, never lowercased;
  * every DOI is offered to BOTH registration agencies (Crossref and DataCite),
    because arXiv's 10.48550/* DOIs are DataCite-registered and return
    Crossref 404; the report records which agency holds each DOI;
  * arXiv ids go through the arXiv Atom API in content-addressed chunks,
    accepting the legacy display form (gr-qc/0307013) and the bare numeric
    form, with or without a vN suffix;
  * the verdict rule and the title thresholds are those of the audit under
    test (declared in its PREREGISTRATION.json), so per-row verdicts and the
    published jaccard/ratio scores are directly comparable;
  * report.json is byte-deterministic: no wall-clock, no host, no ordering by
    anything but citation_id; --offline rebuilds it from the shipped cache.

Writes only under artifacts/worker-007/l1_resolver_channel/.
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
AUDIT_LIVE_PATH = os.path.join(REPO, "artifacts", "worker-025", "l1_identity_audit", "report.json")
AUDIT_PATH = os.path.join(HERE, "snapshot", "worker-025_l1_identity_audit_report.5bd6b3263fea.json")

PIN_CSV = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
PIN_AUDIT = "5bd6b3263feaf9ff497a1c96c2afb269e9c7cad088d1c377e1b016d1d4f3603b"
SUPERSEDED_AUDIT = "a8703d304a5b1bf7a0c02b777abcdaffbf4a3d4f3f625c160412bb8ba30c98f6"

# citation_ids whose verdict was FETCH_FAILED in the superseded revision
# a8703d304a5b, captured 2026-09-12T01:12 from those bytes before the file moved.
SUPERSEDED_FETCH_FAILED_IDS = [
    "SRC-003", "SRC-007", "SRC-008", "SRC-009", "SRC-014", "SRC-037", "SRC-039",
    "SRC-040", "SRC-045", "SRC-046", "SRC-047", "SRC-048", "SRC-049", "SRC-052",
    "SRC-056", "SRC-057", "SRC-061", "SRC-062", "SRC-063", "SRC-064", "SRC-065",
    "SRC-078", "SRC-079", "SRC-080", "SRC-081", "SRC-082", "SRC-084", "SRC-085",
    "SRC-091", "SRC-093", "SRC-097",
]

JACCARD_MATCH = 0.60
RATIO_MATCH = 0.80
ARXIV_CHUNK = 20
UA = "worker-007-l1-resolver-channel/1.0 (mailto:worker-007@ai4math-swarm.invalid)"


# ------------------------------------------------------------------ basics

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def canon_title(s: str) -> str:
    """Same canonical form as the audit under test (NFKD fold, lowercase,
    strip inline math / LaTeX commands / HTML, split on non-alphanumerics)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("{", " ").replace("}", " ").replace("\\", " ")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def toks(s: str):
    return set(canon_title(s).split())


def jaccard(a: str, b: str) -> float:
    ta, tb = toks(a), toks(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return round(len(ta & tb) / len(ta | tb), 4)


def ratio(a: str, b: str) -> float:
    return round(difflib.SequenceMatcher(None, canon_title(a), canon_title(b)).ratio(), 4)


def compatible(a: str, b: str) -> bool:
    return jaccard(a, b) >= JACCARD_MATCH or ratio(a, b) >= RATIO_MATCH


def author_overlap(a, b):
    """Same semantics as the audit's superseded rule: -1.0 when either side is empty,
    full-name token sets compared as sorted strings."""
    if not a or not b:
        return -1.0
    sa = {" ".join(sorted(canon_title(x).split())) for x in a if x}
    sb = {" ".join(sorted(canon_title(x).split())) for x in b if x}
    sa.discard("")
    sb.discard("")
    if not sa or not sb:
        return -1.0
    return round(len(sa & sb) / max(1, min(len(sa), len(sb))), 4)


def _surname_tokens(name: str):
    return {t for t in canon_title(name).split() if len(t) > 1}


def surname_overlap(a, b):
    """Sensitivity replica of the audit's CURRENT rule (script revision 5aaead41,
    mtime 01:15:00): fraction of the shorter author list whose multi-character
    (surname) tokens appear in the other list. Used only to attribute verdict
    differences; the preregistered verdict keeps the superseded rule."""
    if not a or not b:
        return -1.0
    sa = [_surname_tokens(x) for x in a if x and _surname_tokens(x)]
    sb = [_surname_tokens(x) for x in b if x and _surname_tokens(x)]
    if not sa or not sb:
        return -1.0
    hits = sum(1 for na in sa if any(na & nb for nb in sb))
    return round(hits / min(len(sa), len(sb)), 4)


def canon_arxiv_id(a: str) -> str:
    a = (a or "").strip()
    a = re.sub(r"^arxiv:", "", a, flags=re.I)
    return re.sub(r"v\d+$", "", a)


def norm_arxiv_key(a: str) -> str:
    return canon_arxiv_id(a).rsplit("/", 1)[-1]


# ------------------------------------------------------------------ cache/net

def cache_path(name: str) -> str:
    return os.path.join(CACHE, re.sub(r"[^A-Za-z0-9._-]", "_", name) + ".json")


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


def http_get(url: str, tries: int = 3, timeout: int = 45):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", "replace"), None
        except urllib.error.HTTPError as exc:
            last = "HTTP %d" % exc.code
            if exc.code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (attempt + 1))
                continue
            return exc.code, None, last
        except Exception as exc:  # noqa: BLE001
            last = "%s: %s" % (type(exc).__name__, exc)
            time.sleep(1.0 * (attempt + 1))
    return 0, None, last


# ------------------------------------------------------------------ resolvers

def crossref_lookup(doi: str) -> dict:
    key = "crossref_" + doi
    hit = cache_get(key)
    if hit is not None:
        return hit
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    status, body, err = http_get(url)
    rec = {"agency": "crossref", "id": doi, "url": url, "http_status": status, "error": err,
           "body_sha256": None, "title": None, "authors": [], "year": None,
           "container": None, "arxiv_id_declared": None}
    if body is not None:
        rec["body_sha256"] = sha256_bytes(body.encode("utf-8"))
        try:
            msg = json.loads(body).get("message", {})
            rec["title"] = (msg.get("title") or [None])[0]
            rec["authors"] = [" ".join(x for x in (a.get("given"), a.get("family")) if x)
                              for a in (msg.get("author") or [])]
            parts = (msg.get("issued") or {}).get("date-parts") or [[None]]
            rec["year"] = parts[0][0] if parts and parts[0] else None
            rec["container"] = (msg.get("container-title") or [None])[0]
            rec["arxiv_id_declared"] = msg.get("arxiv-id") or None
            if not rec["arxiv_id_declared"]:
                for alt in (msg.get("alternative-id") or []):
                    if str(alt).lower().startswith("arxiv:"):
                        rec["arxiv_id_declared"] = str(alt).split(":", 1)[1]
        except Exception as exc:  # noqa: BLE001
            rec["error"] = "parse: %s" % exc
    cache_put(key, rec)
    return rec


def datacite_lookup(doi: str) -> dict:
    key = "datacite_" + doi
    hit = cache_get(key)
    if hit is not None:
        return hit
    url = "https://api.datacite.org/dois/" + urllib.parse.quote(doi, safe="")
    status, body, err = http_get(url)
    rec = {"agency": "datacite", "id": doi, "url": url, "http_status": status, "error": err,
           "body_sha256": None, "title": None, "authors": [], "year": None,
           "container": None, "arxiv_id_declared": None}
    if body is not None:
        rec["body_sha256"] = sha256_bytes(body.encode("utf-8"))
        try:
            attrs = (json.loads(body).get("data") or {}).get("attributes") or {}
            titles = attrs.get("titles") or []
            rec["title"] = titles[0].get("title") if titles else None
            rec["authors"] = [" ".join(x for x in (c.get("given"), c.get("family")) if x)
                              for c in (attrs.get("creators") or [])]
            rec["year"] = attrs.get("publicationYear")
            rec["container"] = (attrs.get("container") or {}).get("title")
            for ident in (attrs.get("identifiers") or []):
                if str(ident.get("identifierType", "")).lower() == "arxiv":
                    rec["arxiv_id_declared"] = ident.get("identifier")
        except Exception as exc:  # noqa: BLE001
            rec["error"] = "parse: %s" % exc
    cache_put(key, rec)
    return rec


def doi_rec(agency: str, doi: str, offline: bool):
    if offline:
        return cache_get(agency + "_" + doi)
    rec = (crossref_lookup if agency == "crossref" else datacite_lookup)(doi)
    time.sleep(0.15)  # polite pacing for the two agency APIs
    return rec


def parse_arxiv_feed(body: str) -> dict:
    entries = {}
    for entry in re.findall(r"<entry>(.*?)</entry>", body, flags=re.S):
        def grab(tag):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (tag, tag), entry, flags=re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else None
        raw_id = grab("id") or ""
        k = norm_arxiv_key(raw_id.rsplit("/", 1)[-1])
        if not k:
            continue
        authors = re.findall(r"<author>\s*<name>(.*?)</name>", entry, flags=re.S)
        pub = grab("published") or ""
        mdoi = re.search(r"<arxiv:doi[^>]*>(.*?)</arxiv:doi>", entry, flags=re.S)
        entries[k] = {
            "title": grab("title"),
            "authors": [re.sub(r"\s+", " ", a).strip() for a in authors],
            "year": int(pub[:4]) if pub[:4].isdigit() else None,
            "doi_declared": mdoi.group(1).strip() if mdoi else None,
        }
    return entries


def arxiv_entries(ids, offline: bool = False) -> dict:
    """Content-addressed chunk cache so distinct id sets never share a file."""
    ordered = sorted(set(ids))
    out = {}
    for i in range(0, len(ordered), ARXIV_CHUNK):
        chunk = ordered[i:i + ARXIV_CHUNK]
        tag = sha256_bytes("\n".join(chunk).encode("utf-8"))[:12]
        key = "arxiv_chunk_%02d_%s" % (i // ARXIV_CHUNK, tag)
        rec = cache_get(key)
        if rec is None and offline:
            rec = {"ids": chunk, "http_status": None, "error": "no cached arXiv response",
                   "body_sha256": None, "entries": {}}
        if rec is None:
            url = ("https://export.arxiv.org/api/query?id_list=%s&max_results=%d"
                   % (",".join(urllib.parse.quote(c, safe="/.") for c in chunk), len(chunk)))
            status, body, err = http_get(url, tries=3, timeout=60)
            entries = parse_arxiv_feed(body) if body else {}
            rec = {"ids": chunk, "url": url, "http_status": status, "error": err,
                   "body_sha256": sha256_bytes(body.encode("utf-8")) if body else None,
                   "entries": entries}
            cache_put(key, rec)
            time.sleep(3.0)
        for cid in chunk:
            out[cid] = rec["entries"].get(norm_arxiv_key(cid))
    return out


# ------------------------------------------------------------------ build

def resolve_rows(selected, ledger, offline, arxiv_lookup):
    rows_out = []
    for r in selected:
        cid = r["citation_id"]
        src = ledger[cid]
        declared_title = src.get("title") or ""
        doi = (src.get("doi") or "").strip()
        aid = canon_arxiv_id(src.get("arxiv_id"))
        channels = {}
        if doi:
            for agency in ("crossref", "datacite"):
                rec = doi_rec(agency, doi, offline)
                if rec is None:
                    continue
                channels[agency] = {
                    "http_status": rec.get("http_status"), "error": rec.get("error"),
                    "title": rec.get("title"), "authors": rec.get("authors") or [],
                    "year": rec.get("year"), "body_sha256": rec.get("body_sha256"),
                    "arxiv_id_declared": rec.get("arxiv_id_declared"),
                }
        entry = arxiv_lookup.get(aid) if aid else None
        if aid:
            channels["arxiv"] = ({"http_status": 200, "title": entry.get("title"),
                                  "authors": entry.get("authors") or [], "year": entry.get("year"),
                                  "doi_declared": entry.get("doi_declared")}
                                 if entry else
                                 {"http_status": None, "title": None, "authors": [],
                                  "year": None, "error": "no entry in arXiv response"})

        # channel precedence mirrors the audit under test: crossref, then datacite
        d_chan = channels.get("crossref") if (channels.get("crossref") or {}).get("title") else \
                 channels.get("datacite") if (channels.get("datacite") or {}).get("title") else None
        a_chan = channels.get("arxiv") if (channels.get("arxiv") or {}).get("title") else None
        d_ok, a_ok = bool(d_chan), bool(a_chan)

        doi_title = (d_chan or {}).get("title")
        arxiv_title = (a_chan or {}).get("title")
        doi_scores = {"jaccard": jaccard(doi_title or "", declared_title) if d_ok else None,
                      "ratio": ratio(doi_title or "", declared_title) if d_ok else None}
        arxiv_scores = {"jaccard": jaccard(arxiv_title or "", declared_title) if a_ok else None,
                        "ratio": ratio(arxiv_title or "", declared_title) if a_ok else None}

        cross_linked = False
        if d_ok and a_ok:
            if (d_chan or {}).get("arxiv_id_declared"):
                cross_linked = canon_arxiv_id((d_chan or {})["arxiv_id_declared"]) == aid
            if not cross_linked and (a_chan or {}).get("doi_declared"):
                cross_linked = (a_chan or {})["doi_declared"].lower().strip() == doi.lower()

        if not doi and not aid:
            base_verdict = "NO_IDENTIFIER"
        elif doi and aid and not (d_ok and a_ok):
            base_verdict = "FETCH_FAILED"
        elif doi and aid:
            base_verdict = ("IDENTITY_MATCH"
                            if (cross_linked or compatible(doi_title, arxiv_title))
                            else "IDENTITY_MISMATCH")
        elif doi:
            base_verdict = ("IDENTITY_MATCH" if compatible(doi_title, declared_title)
                            else "DOI_TITLE_MISMATCH")
        else:
            base_verdict = ("IDENTITY_MATCH" if compatible(arxiv_title, declared_title)
                            else "ARXIV_TITLE_MISMATCH")

        decl_authors = [a.strip() for a in re.split(r"[;|]", src.get("authors") or "") if a.strip()]
        decl_year = (src.get("year") or "").strip()
        contra, contra_surname = [], []
        for chan, rec_authors, rec_year in (("doi", (d_chan or {}).get("authors") or [],
                                             (d_chan or {}).get("year")),
                                            ("arxiv", (a_chan or {}).get("authors") or [],
                                             (a_chan or {}).get("year"))):
            if chan == "doi" and not d_ok:
                continue
            if chan == "arxiv" and not a_ok:
                continue
            ov = author_overlap(decl_authors, rec_authors)
            ovs = surname_overlap(decl_authors, rec_authors)
            if 0 <= ov < 0.5:
                contra.append("%s authors overlap %.2f (declared %d vs record %d)"
                              % (chan, ov, len(decl_authors), len(rec_authors)))
            if 0 <= ovs < 0.5:
                contra_surname.append("%s authors overlap %.2f (declared %d vs record %d)"
                                      % (chan, ovs, len(decl_authors), len(rec_authors)))
            if decl_year.isdigit() and rec_year and abs(int(decl_year) - int(rec_year)) > 1:
                msg = ("%s year %s vs declared %s (likely preprint/journal offset)"
                       % (chan, rec_year, decl_year))
                contra.append(msg)
                contra_surname.append(msg)

        def apply_flag(base, flagged):
            if flagged and base in ("IDENTITY_MATCH", "DOI_TITLE_MISMATCH", "ARXIV_TITLE_MISMATCH"):
                return "IDENTITY_MATCH_WITH_AUTHOR_YEAR_FLAG" if base == "IDENTITY_MATCH" else base
            return base

        verdict = apply_flag(base_verdict, contra)
        verdict_audit_author_rule = apply_flag(base_verdict, contra_surname)
        rows_out.append({
            "citation_id": cid,
            "row": r.get("row"),
            "class_mapping": src.get("class_mapping"),
            "declared_title": declared_title,
            "doi": doi or None,
            "arxiv_id": aid or None,
            "channels": channels,
            "doi_channel_used": ("crossref" if (channels.get("crossref") or {}).get("title")
                                 else "datacite" if (channels.get("datacite") or {}).get("title")
                                 else None),
            "doi_scores": doi_scores,
            "arxiv_scores": arxiv_scores,
            "cross_linked": cross_linked,
            "author_or_year_contradiction": contra,
            "author_or_year_contradiction_audit_current_rule": contra_surname,
            "verdict": verdict,
            "verdict_audit_current_author_rule": verdict_audit_author_rule,
        })
    return rows_out


def compare(rows_out, audit_rows):
    by_id = {r["citation_id"]: r for r in audit_rows}
    out = []
    for row in rows_out:
        a = by_id[row["citation_id"]]
        mismatches = []
        if row["verdict"] != a.get("verdict"):
            mismatches.append("verdict: mine=%s audit=%s" % (row["verdict"], a.get("verdict")))
        checks = [
            ("doi_title", (row["channels"].get("crossref") or {}).get("title")
             if row["doi_channel_used"] == "crossref"
             else (row["channels"].get("datacite") or {}).get("title"),
             a.get("doi_title")),
            ("doi_jaccard", row["doi_scores"]["jaccard"], a.get("doi_vs_declared_jaccard")),
            ("doi_ratio", row["doi_scores"]["ratio"], a.get("doi_vs_declared_ratio")),
            ("arxiv_title", (row["channels"].get("arxiv") or {}).get("title"), a.get("arxiv_title")),
            ("arxiv_jaccard", row["arxiv_scores"]["jaccard"], a.get("arxiv_vs_declared_jaccard")),
            ("arxiv_ratio", row["arxiv_scores"]["ratio"], a.get("arxiv_vs_declared_ratio")),
        ]
        for name, mine, theirs in checks:
            if mine != theirs:
                mismatches.append("%s: mine=%r audit=%r" % (name, mine, theirs))
        out.append({
            "citation_id": row["citation_id"],
            "agree": not mismatches,
            "mismatches": mismatches,
            "audit_current_author_rule_verdict": row["verdict_audit_current_author_rule"],
            "audit_current_author_rule_agrees":
                row["verdict_audit_current_author_rule"] == a.get("verdict"),
        })
    return out


def build(offline: bool) -> dict:
    csv_sha = sha256_file(CSV_PATH)
    audit_sha = sha256_file(AUDIT_PATH)
    if csv_sha != PIN_CSV:
        print("FATAL: ledger/citation_audit.csv hash moved: %s" % csv_sha, file=sys.stderr)
        raise SystemExit(2)
    if audit_sha != PIN_AUDIT:
        print("FATAL: audit report hash moved: %s != %s" % (audit_sha, PIN_AUDIT), file=sys.stderr)
        raise SystemExit(2)

    with open(CSV_PATH, newline="", encoding="utf-8") as fh:
        ledger = {r["citation_id"]: r for r in csv.DictReader(fh)}
    with open(AUDIT_PATH, "r", encoding="utf-8") as fh:
        audit = json.load(fh)
    audit_rows = {r["citation_id"]: r for r in audit["rows"]}

    p1 = [audit_rows[c] for c in SUPERSEDED_FETCH_FAILED_IDS if c in audit_rows]
    p2 = sorted(audit["rows"], key=lambda r: r["citation_id"])

    controls = {}
    c1 = doi_rec("crossref", "10.4007/annals.2023.198.1.3", offline) or {}
    controls["C1_positive_crossref_doi"] = {
        "doi": "10.4007/annals.2023.198.1.3", "http_status": c1.get("http_status"),
        "live_title": c1.get("title") or "",
        "matches_src002_declared": compatible(ledger["SRC-002"]["title"], c1.get("title") or ""),
    }
    bad = doi_rec("crossref", "10.9999/this-doi-does-not-exist-007", offline) or {}
    bad_dc = doi_rec("datacite", "10.9999/this-doi-does-not-exist-007", offline) or {}
    controls["C2_negative_missing_doi"] = {
        "crossref_http_status": bad.get("http_status"),
        "datacite_http_status": bad_dc.get("http_status"),
        "no_record": not (bad.get("title") or bad_dc.get("title")),
    }
    controls["C3_threshold_negative"] = {
        "a": "Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution",
        "b": "Naked singularities for the Navier-Stokes equations",
        "compatible": compatible(
            "Naked Singularities for the Einstein Vacuum Equations: The Exterior Solution",
            "Naked singularities for the Navier-Stokes equations"),
    }
    legacy = arxiv_entries(["gr-qc/0307013"], offline=offline).get("0307013") or {}
    controls["C5_legacy_arxiv_id"] = {
        "arxiv_id": "gr-qc/0307013", "live_title": legacy.get("title") or "",
        "matches_src007_declared": compatible(ledger["SRC-007"]["title"], legacy.get("title") or ""),
    }

    union_ids = [ledger[r["citation_id"]].get("arxiv_id") for r in p2
                 if (ledger[r["citation_id"]].get("arxiv_id") or "").strip()]
    arxiv_lookup = arxiv_entries(union_ids, offline=offline)
    rows_p1 = resolve_rows(p1, ledger, offline, arxiv_lookup)
    rows_p2 = resolve_rows(p2, ledger, offline, arxiv_lookup)
    cmp_p2 = compare(rows_p2, p2)
    my_counts = {}
    for r in rows_p2:
        my_counts[r["verdict"]] = my_counts.get(r["verdict"], 0) + 1
    p1_counts = {}
    for r in rows_p1:
        p1_counts[r["verdict"]] = p1_counts.get(r["verdict"], 0) + 1

    both = sum(1 for r in rows_p2 if r["doi_channel_used"] and
               (r["channels"].get("arxiv") or {}).get("title"))
    agency = {"crossref": sum(1 for r in rows_p2 if r["doi_channel_used"] == "crossref"),
              "datacite": sum(1 for r in rows_p2 if r["doi_channel_used"] == "datacite")}
    disagree = [c for c in cmp_p2 if not c["agree"]]
    claim_replication = {
        "audit_claim_fetch_failed_0": my_counts.get("FETCH_FAILED", 0) == 0,
        "my_fetch_failed": my_counts.get("FETCH_FAILED", 0),
        "audit_claim_identity_mismatches_0": my_counts.get("IDENTITY_MISMATCH", 0) == 0,
        "audit_claim_title_mismatches_0": (my_counts.get("IDENTITY_MISMATCH", 0)
                                           + my_counts.get("DOI_TITLE_MISMATCH", 0)
                                           + my_counts.get("ARXIV_TITLE_MISMATCH", 0)) == 0,
        "my_title_mismatches": (my_counts.get("IDENTITY_MISMATCH", 0)
                                + my_counts.get("DOI_TITLE_MISMATCH", 0)
                                + my_counts.get("ARXIV_TITLE_MISMATCH", 0)),
        "audit_claim_rows_resolved_both_channels_59": both == 59,
        "my_rows_resolved_both_channels": both,
        "audit_claim_doi_registration_agency": agency == audit.get("doi_registration_agency"),
        "my_doi_registration_agency": agency,
        "per_row_agreement": len(cmp_p2) - len(disagree),
        "per_row_total": len(cmp_p2),
        "per_row_disagreements": disagree,
        "per_row_agreement_under_audit_current_author_rule":
            sum(1 for c in cmp_p2 if c["audit_current_author_rule_agrees"]),
        "disagreements_explained_by_author_rule_revision":
            sum(1 for c in cmp_p2 if not c["agree"] and c["audit_current_author_rule_agrees"]),
    }

    return {
        "schema": "worker-007/l1-resolver-channel/v2",
        "task_id": "W007-L1-RESOLVER-CHANNEL-01",
        "actor": "worker-007",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "inputs": {
            "ledger/citation_audit.csv": csv_sha,
            "snapshot/worker-025_l1_identity_audit_report.5bd6b3263fea.json": audit_sha,
            "superseded_audit_report": SUPERSEDED_AUDIT,
            "thresholds": {"jaccard": JACCARD_MATCH, "ratio": RATIO_MATCH},
        },
        "populations": {
            "P1_superseded_fetch_failed": {
                "n": len(rows_p1),
                "citation_ids": [r["citation_id"] for r in rows_p1],
                "provenance": ("citation_ids whose verdict was FETCH_FAILED in the superseded "
                               "report revision a8703d304a5b, captured before it moved"),
            },
            "P2_all_rows": {"n": len(rows_p2), "rule": "every row of the pinned report"},
        },
        "controls": controls,
        "P1_rows": rows_p1,
        "P1_summary": p1_counts,
        "rows": rows_p2,
        "summary": {"my_verdict_counts": my_counts, "audit_verdict_counts": audit.get("counts"),
                    "claim_replication": claim_replication},
        "falsifier": json.load(open(os.path.join(HERE, "PREREGISTRATION.json"),
                                    encoding="utf-8"))["pre_registered_falsifier"],
        "non_claims": json.load(open(os.path.join(HERE, "PREREGISTRATION.json"),
                                     encoding="utf-8"))["non_claims"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    report = build(args.offline)
    blob = json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(blob)
    print(json.dumps(report["summary"]["my_verdict_counts"], sort_keys=True))
    print(json.dumps(report["P1_summary"], sort_keys=True))
    print("agreement: %d/%d" % (report["summary"]["claim_replication"]["per_row_agreement"],
                                report["summary"]["claim_replication"]["per_row_total"]))
    print("report sha256:", sha256_bytes(blob.encode("utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
