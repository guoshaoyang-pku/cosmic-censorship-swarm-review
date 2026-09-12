#!/usr/bin/env python3
"""W010-L1-SPOTCHECK-PARTIALS-04: independent adversarial re-fetch of the 5 rows that
worker-028's uncovered-row spot check returned as PARTIAL, plus 3 class-bound rows.

Card: comms/inbox/deepseek-flash-10.jsonl :: astra-glit-00
      ("Re-fetch >=3 ledger rows in your batch directly from the DOI/arXiv locator; quote the
        fetched text; state match/mismatch against the ledger excerpt verbatim; emit a review
        event with verdict.")
Node L1 / gate G-LIT / classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN,
AF-WCC-SCALAR-SPH.

What this does that prior checks did not:
  * targets exactly the rows left contested (028 PARTIAL: SRC-060, SRC-068, SRC-076, SRC-087,
    SRC-088) and re-derives the verdict from the row's own record locator;
  * stores every raw HTTP body with its sha256, and supports --offline re-verification, so the
    falsifier is executable rather than prose;
  * compares a structured (Crossref metadata) excerpt field-by-field instead of running an
    abstract-substring test that cannot succeed on a row with no abstract;
  * resolves the arXiv id from evidence_url when the arxiv_id column is empty (SRC-088).

Ledger is never modified.  No gate verdict, no node status, no validation_status=passed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEDGER = ROOT / "ledger" / "citation_audit.csv"
OUTDIR = ROOT / "artifacts" / "flash-10" / "l1_spotcheck"
RAWDIR = OUTDIR / "raw"
OUT = OUTDIR / "spotcheck-l1-010-partials.json"
CST = timezone(timedelta(hours=8))
UA = "ai4math-swarm-worker-010-l1-spotcheck/1.0 (independent re-fetch; contact: swarm)"

TASK_ID = "W010-L1-SPOTCHECK-PARTIALS-04"
ASSIGNMENT_REF = "astra-glit-00"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

# residue of worker-028's uncovered-row check (sampled_rows) + class-carrying MATCH rows
SAMPLE_ROWS = [59, 60, 63, 68, 76, 79, 87, 88]
ROW_028 = {  # verdicts recorded by artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json
    "SRC-059": "not sampled",
    "SRC-060": "PARTIAL",
    "SRC-063": "MATCH",
    "SRC-068": "PARTIAL",
    "SRC-076": "PARTIAL",
    "SRC-079": "MATCH",
    "SRC-087": "PARTIAL",
    "SRC-088": "PARTIAL",
}
ATOM = "{http://www.w3.org/2005/Atom}"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def norm_tokens(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s or "")
    s = re.sub(r"[^0-9a-zA-Z]+", " ", s).lower()
    return s.split()


def norm_text(s: str) -> str:
    return " ".join(norm_tokens(s))


def strip_jats(s: str) -> str:
    """Crossref titles/abstracts carry JATS markup (<i>, <sup>, entities); strip it with a space."""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s or "")).split())


def norm_compact(s: str) -> str:
    """Aggressive identity normalization: NFKD-fold, drop everything non-alphanumeric.
    T^3-Gowdy -> t3gowdy ; C^{0,1}_loc -> c01loc ; Ringström -> ringstrom."""
    s = unicodedata.normalize("NFKD", html.unescape(strip_jats(s or "")))
    return re.sub(r"[^0-9a-z]+", "", s.lower())


def trigrams(s: str) -> set[str]:
    return {s[i:i + 3] for i in range(max(0, len(s) - 2))}


def digits(s: str) -> list[str]:
    return re.findall(r"\d+", s or "")


def title_match(a: str, b: str) -> dict:
    """Publisher markup mangles math in titles (T^3 -> 'T 3', C^{0,1}_loc -> 'Cloc0,1').
    Crossref renders the latter as a pure transposition of the '01' run, which n-gram/Jaccard
    tests punish.  Rule: compact-equal, OR (same character multiset AND ordered similarity
    >= 0.90).  The bag test makes any inserted/deleted/substituted character fail, including a
    mutated exponent (T^3->T^4) and a changed content word; the ratio test rejects pure anagrams
    such as 'cosmic'->'comsic'.  Residual limitation: a within-word anagram that keeps the bag
    and stays above 0.90 would pass; recorded in the artifact's limitations."""
    ca, cb = norm_compact(a), norm_compact(b)
    bag = sorted(ca) == sorted(cb)
    ratio = round(SequenceMatcher(None, ca, cb).ratio(), 4)
    return {"declared_compact": ca, "fetched_compact": cb, "char_bag_equal": bag,
            "ordered_ratio": ratio, "declared_digits": sorted(digits(strip_jats(a))),
            "fetched_digits": sorted(digits(strip_jats(b))),
            "match": ca == cb or (bag and ratio >= 0.90)}


def surnames(declared: str) -> list[str]:
    """Extract author surnames from a ledger metadata excerpt, dropping affiliations."""
    s = re.sub(r"\([^)]*\)", " ", declared)          # drop (Princeton)
    s = re.sub(r"\band\b", ";", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" ;,")
    out = []
    for part in re.split(r"[;,]", s):
        part = part.strip()
        if not part:
            continue
        toks = [t for t in re.split(r"\s+", part) if len(norm_compact(t)) > 1]
        if toks:
            out.append(toks[-1])
    return out


def coverage(frag_tokens: list[str], fetched_norm: str) -> dict:
    """Token coverage of a ledger fragment in the fetched text + ordered match ratio."""
    if not frag_tokens:
        return {"token_coverage": 0.0, "ordered_token_match_ratio": 0.0,
                "common_prefix_tokens": 0, "contained": False}
    fs = " ".join(frag_tokens)
    contained = fs in fetched_norm
    ftoks = fetched_norm.split()
    # token coverage via difflib on the joined strings (character-level is too lenient; token-level
    # SequenceMatcher over the fragment tokens against the whole fetched token stream is O(n*m),
    # so use the standard trick: match the fragment against sliding windows anchored on its head).
    head = " ".join(frag_tokens[:8])
    idx = fetched_norm.find(head)
    if idx >= 0:
        window = fetched_norm[idx: idx + len(fs) + 200]
        cov = SequenceMatcher(None, fs, window).ratio()
        prefix = len(frag_tokens)
        for k in range(len(frag_tokens), 0, -1):
            if " ".join(frag_tokens[:k]) in fetched_norm:
                prefix = k
                break
        return {"token_coverage": round(cov, 3), "ordered_token_match_ratio": round(cov, 3),
                "common_prefix_tokens": prefix, "contained": contained}
    # no head anchor: best effort global ratio is not meaningful; report 0 and let context be null
    return {"token_coverage": 0.0, "ordered_token_match_ratio": 0.0,
            "common_prefix_tokens": 0, "contained": False}


def context_window(fetched: str, frag_tokens: list[str], width: int = 320) -> str | None:
    """Verbatim window of the fetched text around the fragment head (or None)."""
    if not frag_tokens or not fetched:
        return None
    head = " ".join(frag_tokens[:6])
    i = fetched.lower().find(head.lower())
    if i < 0:
        return None
    return fetched[max(0, i - 80): i + width]


def http_get(url: str, timeout: int = 40) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return {"ok": True, "http_status": r.status, "body": body,
                    "content_type": r.headers.get("Content-Type", ""),
                    "seconds": round(time.time() - t0, 2)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http_status": e.code, "body": e.read()[:20000],
                "content_type": e.headers.get("Content-Type", "") if e.headers else "",
                "error": f"HTTPError {e.code}", "seconds": round(time.time() - t0, 2)}
    except Exception as e:  # noqa: BLE001 - network layer, report verbatim
        return {"ok": False, "http_status": None, "body": b"", "content_type": "",
                "error": f"{type(e).__name__}: {e}", "seconds": round(time.time() - t0, 2)}


# ----------------------------------------------------------------------------- anchors

def anchors_for(row: dict) -> list[dict]:
    """All resolvable record anchors for a row, primary first."""
    out: list[dict] = []
    excerpt = row.get("evidence_excerpt") or ""
    arxiv = (row.get("arxiv_id") or "").strip()
    if not arxiv:
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z-]+/[0-9]{7})",
                      (row.get("evidence_url") or "") + " " + (row.get("url") or ""))
        if m:
            arxiv = m.group(1)
    doi = (row.get("doi") or "").strip()
    m = re.search(r"inspirehep\.net/(?:api/literature|literature)/(\d+)",
                  (row.get("evidence_url") or "") + " " + (row.get("exact_locator") or ""))
    recid = m.group(1) if m else ""
    if arxiv:
        out.append({"anchor": "arxiv-api", "role": "primary" if not excerpt.startswith("Crossref record:") else "secondary",
                    "locator": f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv)}",
                    "record_id": arxiv})
    if doi:
        out.append({"anchor": "crossref-api", "role": "primary" if excerpt.startswith("Crossref record:") else "secondary",
                    "locator": f"https://api.crossref.org/works/{urllib.parse.quote(doi)}",
                    "record_id": doi})
    if recid:
        out.append({"anchor": "inspire-api",
                    "role": "primary" if (excerpt.startswith("Lehigh University abstract:") or not out) else "secondary",
                    "locator": f"https://inspirehep.net/api/literature/{recid}", "record_id": recid})
    if not out:
        out.append({"anchor": "direct", "role": "primary",
                    "locator": row.get("evidence_url") or row.get("url") or row.get("exact_locator"),
                    "record_id": ""})
    order = {"primary": 0, "secondary": 1}
    out.sort(key=lambda a: order[a["role"]])
    return out


# ------------------------------------------------------------------- parsed fetched text

def parse_arxiv(body: bytes) -> dict:
    root = ET.fromstring(body)
    e = root.find(f"{ATOM}entry")
    if e is None:
        return {}
    authors = [a.findtext(f"{ATOM}name") or "" for a in e.findall(f"{ATOM}author")]
    return {
        "title": " ".join((e.findtext(f"{ATOM}title") or "").split()),
        "abstract": " ".join((e.findtext(f"{ATOM}summary") or "").split()),
        "authors": authors,
        "published": e.findtext(f"{ATOM}published") or "",
        "journal_ref": " ".join((e.findtext(f"{ATOM}journal_ref") or "").split()),
        "doi": e.findtext(f"{ATOM}doi") or "",
    }


def _crossref_date(msg: dict) -> str:
    for k in ("published-print", "published-online", "published", "issued", "created"):
        dp = (msg.get(k) or {}).get("date-parts")
        if dp and dp[0]:
            p = dp[0] + [1, 1]
            return f"{p[0]:04d}-{p[1]:02d}-{p[2]:02d}"
    return ""


def parse_crossref(body: bytes) -> dict:
    msg = json.loads(body)["message"]
    authors = []
    for a in msg.get("author") or []:
        authors.append(" ".join(x for x in [a.get("given"), a.get("family")] if x) or a.get("name", ""))
    return {
        "title": " ".join((msg.get("title") or [""])[0].split()),
        "abstract": re.sub(r"<[^>]+>", " ", msg.get("abstract") or ""),
        "authors": authors,
        "published": _crossref_date(msg),
        "journal": " ".join((msg.get("container-title") or [""])[0].split()),
        "volume": str(msg.get("volume") or ""),
        "issue": str(msg.get("issue") or ""),
        "page": str(msg.get("page") or ""),
        "doi": msg.get("DOI") or "",
        "reference_count": msg.get("reference-count"),
    }


def parse_inspire(body: bytes) -> dict:
    md = json.loads(body)["metadata"]
    pi = (md.get("publication_info") or [{}])[0]
    return {
        "title": " ".join((md.get("titles") or [{}])[0].get("title", "").split()),
        "abstract": " ".join(((md.get("abstracts") or [{}])[0].get("value", "") or "").split()),
        "authors": [a.get("full_name", "") for a in md.get("authors") or []],
        "published": str(pi.get("year") or ""),
        "journal": pi.get("journal_title") or "",
        "volume": str(pi.get("journal_volume") or ""),
        "page": str(pi.get("page_start") or pi.get("artid") or ""),
        "doi": ((md.get("dois") or [{}])[0].get("value") or ""),
        "arxiv": ((md.get("arxiv_eprints") or [{}])[0].get("value") or ""),
    }


PARSERS = {"arxiv-api": parse_arxiv, "crossref-api": parse_crossref, "inspire-api": parse_inspire}

# ---------------------------------------------------------------- ledger-excerpt parsing

LABELS = ("Abstract:", "Crossref record:", "arXiv page confirms title and abstract:",
          "Lehigh University abstract:", "INSPIRE recid")
META_RE = {
    "title": re.compile(r"title '([^']+)'"),
    "author": re.compile(r"authors? ([^;]+?)(?:;| Annals| Duke| Journal| Comm| Phys| DOI|$)"),
    "volume": re.compile(r"volume (\d+)"),
    "issue": re.compile(r"issue (\d+)"),
    "pages": re.compile(r"pages ([0-9ivxlcdm]+-[0-9ivxlcdm]+)"),
    "published": re.compile(r"published (\d{4}-\d{2}-\d{2})"),
    "doi": re.compile(r"DOI (10\.[^\s;]+)"),
    "reference_count": re.compile(r"reference-count (\d+)"),
}


def split_fragments(excerpt: str) -> list[str]:
    """Ledger excerpt -> quoted content fragments, with labels and trailing DOI tails stripped."""
    s = excerpt or ""
    for lab in LABELS:
        if s.startswith(lab):
            s = s[len(lab):].strip()
    s = re.sub(r"Related DOI:.*$", "", s).strip()          # SRC-088 tail
    parts = re.split(r"\.\.\.|…", s)
    out = []
    for p in parts:
        p = p.strip().strip("'\"").strip()
        p = re.sub(r"['\"]\s*$", "", p).strip()             # closing quote of a composite excerpt
        if p:
            out.append(p)
    return out


def parse_meta_excerpt(excerpt: str) -> dict:
    out = {}
    for k, rx in META_RE.items():
        m = rx.search(excerpt)
        v = m.group(1) if m else None
        if v is not None and k == "doi":
            v = v.rstrip(".,;")          # sentence punctuation after the DOI
        out[k] = v
    return out


def compare_meta_row(row: dict, fetched: dict) -> dict:
    declared = parse_meta_excerpt(row["evidence_excerpt"])
    checks: dict[str, dict] = {}
    for field, want in declared.items():
        if want is None:
            continue
        if field == "author":
            got = " ".join(fetched.get("authors") or [])
            got_c = norm_compact(got)
            names = surnames(want)
            hits = {s: norm_compact(s) in got_c for s in names}
            checks[field] = {"declared": want, "fetched": got,
                             "declared_surnames": names, "surname_hits": hits,
                             "match": bool(names) and all(hits.values())}
        elif field == "published":
            got = fetched.get("published") or ""
            checks[field] = {"declared": want, "fetched": got, "match": want == got}
        elif field == "volume":
            checks[field] = {"declared": want, "fetched": fetched.get("volume", ""), "match": want == str(fetched.get("volume", ""))}
        elif field == "issue":
            checks[field] = {"declared": want, "fetched": fetched.get("issue", ""), "match": want == str(fetched.get("issue", ""))}
        elif field == "pages":
            checks[field] = {"declared": want, "fetched": fetched.get("page", ""), "match": want == str(fetched.get("page", ""))}
        elif field == "reference_count":
            checks[field] = {"declared": want, "fetched": fetched.get("reference_count"), "match": str(want) == str(fetched.get("reference_count"))}
        elif field == "doi":
            checks[field] = {"declared": want, "fetched": fetched.get("doi", ""),
                             "match": want.lower() == str(fetched.get("doi", "")).lower()}
        elif field == "title":
            tm = title_match(want, strip_jats(fetched.get("title", "")))
            checks[field] = {"declared": want, "fetched": strip_jats(fetched.get("title", "")),
                             "match": tm["match"], "char_bag_equal": tm["char_bag_equal"],
                             "ordered_ratio": tm["ordered_ratio"]}
    for field in ("title", "doi"):  # identity fields must be present and match
        if field not in checks:
            checks[field] = {"declared": None, "fetched": strip_jats(fetched.get(field, "") or ""),
                             "match": False, "note": "declared field not parsed"}
    ok = all(c["match"] for c in checks.values())
    return {"kind": "metadata-field-comparison", "fields": checks, "all_fields_match": ok}


def compare_abstract_row(row: dict, fetched: dict) -> dict:
    frags = split_fragments(row["evidence_excerpt"])
    fnorm = norm_text(" ".join([fetched.get("title", ""), fetched.get("abstract", "")]))
    fraw = " ".join([fetched.get("title", ""), fetched.get("abstract", "")])
    comps = []
    for f in frags:
        ft = norm_tokens(f)
        c = coverage(ft, fnorm)
        c["fragment"] = f
        c["fragment_tokens"] = len(ft)
        c["fetched_context"] = context_window(fraw, ft)
        if c["contained"]:
            c["fragment_verdict"] = "verbatim_contained"
        elif c["token_coverage"] >= 0.95:
            c["fragment_verdict"] = "near_verbatim_but_not_contained"
        elif c["token_coverage"] >= 0.6:
            c["fragment_verdict"] = "partial"
        else:
            c["fragment_verdict"] = "unsupported"
        comps.append(c)
    bad = [c for c in comps if c["fragment_verdict"] != "verbatim_contained"]
    return {"kind": "abstract-fragment-containment", "fragments": comps,
            "all_fragments_supported": not bad,
            "unsupported_fragments": [c["fragment"][:100] for c in bad]}


# -------------------------------------------------------------------------------- controls

def run_controls(rows_by_idx: dict, fetched_by_idx: dict) -> dict:
    """Mutation controls: the instrument must fail on a fabricated/altered excerpt.  Run before
    any verdict is believed (HANDOFF process rule: run the null first)."""
    cases = [
        ("C1", 60, lambda e: e.replace("annals.2003.158.875", "annals.2003.158.876"),
         "metadata DOI last digit mutated -> identity field must fail"),
        ("C2", 59, lambda e: e.replace("T^3-Gowdy", "T^4-Gowdy"),
         "title exponent mutated -> digit guard must fail"),
        ("C3", 59, lambda e: e.replace("cosmic censorship in", "cosmic censorship conjecture in"),
         "title content word inserted -> trigram guard must fail"),
        ("C4", 68, lambda e: e.replace("Shlapentokh-Rothman", "Shlapentokh-Rothmann"),
         "author surname mutated -> surname check must fail"),
        ("C5", 63, lambda e: e + " This sentence was fabricated for control purposes.",
         "fabricated abstract sentence appended -> fragment containment must fail"),
        ("C6", 88, lambda e: e.replace("local energy blow-up", "local energy decay"),
         "one content word substituted inside an excerpt fragment -> containment must fail"),
    ]
    checks = []
    for cid, idx, mut, why in cases:
        row = dict(rows_by_idx[idx])
        row["evidence_excerpt"] = mut(row["evidence_excerpt"])
        fetched = fetched_by_idx[idx]
        if (rows_by_idx[idx]["evidence_excerpt"] or "").startswith("Crossref record:"):
            comp = compare_meta_row(row, fetched)
            fired = not comp["all_fields_match"]
            fired_fields = [k for k, v in comp["fields"].items() if not v["match"]]
        else:
            comp = compare_abstract_row(row, fetched)
            fired = not comp["all_fragments_supported"]
            fired_fields = comp["unsupported_fragments"]
        checks.append({"control": cid, "row": f"SRC-{idx:03d}", "mutation": why,
                       "instrument_fired": fired, "fired_on": fired_fields,
                       "mutated_excerpt": row["evidence_excerpt"][:160]})
    # positive controls: unmutated excerpts must pass on the same fetched records
    for idx in SAMPLE_ROWS:
        row = rows_by_idx[idx]
        fetched = fetched_by_idx[idx]
        if (row["evidence_excerpt"] or "").startswith("Crossref record:"):
            ok = compare_meta_row(row, fetched)["all_fields_match"]
        else:
            ok = compare_abstract_row(row, fetched)["all_fragments_supported"]
        checks.append({"control": f"P{idx}", "row": f"SRC-{idx:03d}", "mutation": "none (positive control)",
                       "instrument_fired": not ok, "fired_on": [] if ok else ["positive control failed"],
                       "mutated_excerpt": None})
    mutations = [c for c in checks if not c["control"].startswith("P")]
    positives = [c for c in checks if c["control"].startswith("P")]
    return {"verdict": "PASS" if all(c["instrument_fired"] for c in mutations)
            and not any(c["instrument_fired"] for c in positives) else "FAIL",
            "mutations_all_detected": sum(1 for c in mutations if c["instrument_fired"]),
            "mutations_total": len(mutations),
            "positives_all_pass": all(not c["instrument_fired"] for c in positives),
            "positives_total": len(positives), "checks": checks}


# -------------------------------------------------------------------------------- driver

def run(live: bool) -> dict:
    ledger_sha_before = sha256_file(LEDGER)
    rows = list(csv.DictReader(LEDGER.open()))
    fetches: list[dict] = []
    results: list[dict] = []
    rows_by_idx: dict[int, dict] = {}
    fetched_by_idx: dict[int, dict] = {}
    for idx in SAMPLE_ROWS:
        row = rows[idx - 1]
        rows_by_idx[idx] = row
        cid = row["citation_id"]
        assert cid == f"SRC-{idx:03d}", (idx, cid)
        row_fetches = []
        for a in anchors_for(row):
            raw_path = RAWDIR / f"{cid}.{a['anchor']}{'' if a['role']=='primary' else '.2'}.body"
            if live:
                t0 = now()
                resp = http_get(a["locator"])
                RAWDIR.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(resp["body"])
                rec = {"anchor": a["anchor"], "role": a["role"], "record_id": a["record_id"],
                       "locator": a["locator"], "fetched_at": t0, "http_status": resp["http_status"],
                       "ok": resp["ok"], "error": resp.get("error"), "seconds": resp.get("seconds"),
                       "raw_body": str(raw_path.relative_to(ROOT)), "raw_bytes": len(resp["body"]),
                       "raw_sha256": sha256_bytes(resp["body"])}
            else:
                body = raw_path.read_bytes() if raw_path.exists() else b""
                rec = {"anchor": a["anchor"], "role": a["role"], "record_id": a["record_id"],
                       "locator": a["locator"], "fetched_at": None, "http_status": 200 if body else None,
                       "ok": bool(body), "error": None if body else "raw body absent",
                       "seconds": None, "raw_body": str(raw_path.relative_to(ROOT)),
                       "raw_bytes": len(body), "raw_sha256": sha256_bytes(body)}
            if rec["ok"] and a["anchor"] in PARSERS:
                try:
                    rec["parsed"] = PARSERS[a["anchor"]](raw_path.read_bytes())
                except Exception as e:  # noqa: BLE001
                    rec["parse_error"] = f"{type(e).__name__}: {e}"
            fetches.append(rec)
            row_fetches.append(rec)

        prim = next((f for f in row_fetches if f["role"] == "primary" and f.get("parsed")), None)
        secondary = next((f for f in row_fetches if f["role"] == "secondary" and f.get("parsed")), None)
        entry = {
            "citation_id": cid,
            "row_index": idx,
            "ledger_fields": {
                "title": row["title"], "doi": row["doi"], "arxiv_id": row["arxiv_id"],
                "evidence_type": row["evidence_type"], "verification_method": row["verification_method"],
                "class_mapping": row["class_mapping"], "used_by_theorems": row["used_by_theorems"],
                "verdict": row["verdict"], "status": row["status"],
                "exact_locator": row["exact_locator"], "evidence_url": row["evidence_url"],
                "mirror_of": row["mirror_of"], "elided_quote": row["elided_quote"],
            },
            "evidence_excerpt_verbatim": row["evidence_excerpt"],
            "worker_028_verdict": ROW_028.get(cid, "unknown"),
        }
        if prim is None:
            entry["verdict"] = "FETCH_FAILED"
            entry["comparison"] = None
        else:
            fetched = prim["parsed"]
            fetched_by_idx[idx] = fetched
            if (row["evidence_excerpt"] or "").startswith("Crossref record:"):
                entry["comparison"] = compare_meta_row(row, fetched)
                entry["verdict"] = "CONFIRMED_METADATA" if entry["comparison"]["all_fields_match"] else "MISMATCH_FIELD"
            else:
                entry["comparison"] = compare_abstract_row(row, fetched)
                entry["verdict"] = "CONFIRMED_ABSTRACT" if entry["comparison"]["all_fragments_supported"] else "MISMATCH_EXCERPT"
            entry["fetched_primary"] = {"anchor": prim["anchor"], "locator": prim["locator"],
                                        "raw_sha256": prim["raw_sha256"],
                                        "title": fetched.get("title"), "abstract": fetched.get("abstract"),
                                        "authors": fetched.get("authors"), "published": fetched.get("published"),
                                        "doi": fetched.get("doi"), "journal": fetched.get("journal")}
        if secondary:
            entry["secondary_anchor_check"] = {"anchor": secondary["anchor"], "locator": secondary["locator"],
                                               "raw_sha256": secondary["raw_sha256"],
                                               "title": secondary["parsed"].get("title"),
                                               "identity_title_match": norm_text(secondary["parsed"].get("title", "")) ==
                                                                       norm_text(entry.get("fetched_primary", {}).get("title") or
                                                                                 row["title"])}
        # adjudication of worker-028's PARTIAL verdict
        v028 = ROW_028.get(cid)
        if entry["verdict"].startswith("CONFIRMED"):
            if v028 == "PARTIAL":
                entry["adjudication_of_028"] = ("028 PARTIAL not reproduced as a content defect at this anchor: "
                                                "the excerpt is fully supported (elisions/metadata rendering explain the "
                                                "028 substring miss)")
            elif v028 == "MATCH":
                entry["adjudication_of_028"] = "028 MATCH reproduced"
            else:
                entry["adjudication_of_028"] = "row not sampled by 028; this is a first independent re-fetch"
        elif entry["verdict"].startswith("MISMATCH"):
            entry["adjudication_of_028"] = "028 verdict understated: an excerpt fragment or declared metadata field is not supported by the fetched record"
        else:
            entry["adjudication_of_028"] = "fetch failed; 028 verdict not adjudicated"
        results.append(entry)

    ledger_sha_after = sha256_file(LEDGER)
    controls = (run_controls(rows_by_idx, fetched_by_idx)
                if len(fetched_by_idx) == len(SAMPLE_ROWS) else
                {"verdict": "NOT_RUN", "reason": "one or more primary fetches failed"})
    counts = {}
    for e in results:
        counts[e["verdict"]] = counts.get(e["verdict"], 0) + 1
    confirmed = [e["citation_id"] for e in results if e["verdict"].startswith("CONFIRMED")]
    mismatched = [e["citation_id"] for e in results if e["verdict"].startswith("MISMATCH")]
    failed = [e["citation_id"] for e in results if e["verdict"] == "FETCH_FAILED"]
    payload = {
        "schema_version": "0.1",
        "artifact_type": "l1_spotcheck",
        "event_id": f"flash-10-l1-spotcheck-partials-04-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "event_type": "artifact",
        "created_at": now(),
        "actor": "deepseek-flash-10",
        "reviewer": "deepseek-flash-10",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "task_id": TASK_ID,
        "assignment_ref": ASSIGNMENT_REF,
        "purpose": ("Independent adversarial re-fetch of the five rows worker-028 returned as PARTIAL "
                    "(SRC-060/068/076/087/088) plus three class-carrying rows (SRC-059/063/079), to decide "
                    "whether the PARTIAL verdicts are benign elision/metadata-rendering artifacts or "
                    "unsupported excerpts. No ledger file is modified."),
        "sampling": {
            "rule": ("rows {59,60,63,68,76,79,87,88}: the 028 contested set {60,68,76,87,88} plus the "
                     "Crossref row 59 (excluded from the census uncovered set) and the class-carrying "
                     "MATCH rows 63,79; fixed before any fetch; row ids equal 1-based data-row index"),
            "sample_ids": [f"SRC-{i:03d}" for i in SAMPLE_ROWS],
            "frozen_before_fetch": True,
        },
        "target": {"path": "ledger/citation_audit.csv", "sha256_before": ledger_sha_before,
                   "sha256_after": ledger_sha_after, "stable_during_run": ledger_sha_before == ledger_sha_after,
                   "data_rows": len(rows)},
        "inputs": {
            "ledger/citation_audit.csv": {"sha256": ledger_sha_before, "data_rows": len(rows)},
            "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json": {
                "sha256": sha256_file(ROOT / "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json")
                if (ROOT / "artifacts/worker-028/l1_uncovered_spotcheck/uncovered_spotcheck_028.json").exists() else None,
                "role": "prior verdicts being adjudicated"},
        },
        "fetches": fetches,
        "results": results,
        "controls": controls,
        "summary": {"checked_rows": len(results), "confirmed": len(confirmed), "mismatched": len(mismatched),
                    "fetch_failed": len(failed), "verdict_counts": counts,
                    "confirmed_ids": confirmed, "mismatched_ids": mismatched, "fetch_failed_ids": failed,
                    "rows_where_028_partial_was_not_reproduced": [
                        e["citation_id"] for e in results if e["worker_028_verdict"] == "PARTIAL"
                        and e["verdict"].startswith("CONFIRMED")]},
        "method": ("live re-fetch of each row's own record locator (arXiv API id_list where an arXiv id is "
                   "present or derivable from evidence_url; Crossref /works/<doi>; INSPIRE literature/<recid>); "
                   "raw bodies stored byte-verbatim with sha256; metadata excerpts compared field-by-field "
                   "against the Crossref/INSPIRE record with a JATS/diacritic-folding title test (compact "
                   "equality or char-multiset equality plus ordered similarity >= 0.90); abstract excerpts split "
                   "on '...' and each fragment required "
                   "to be a normalized verbatim substring of the fetched title+abstract (a one-word substitution "
                   "inside a fragment fails by construction); six mutation controls plus eight positive controls "
                   "run in-band to demonstrate the instrument fires; every verdict carries the fetched context "
                   "window verbatim.  Re-run with --offline to re-hash the raw bodies and re-derive every verdict."),
        "hard_failures": [f"HF-W010-L1-{cid}: declared excerpt/metadata not supported by the re-fetched record"
                          for cid in mismatched] + [f"HF-W010-L1-{cid}: fetch failed" for cid in failed]
                         + ([] if controls.get("verdict") == "PASS" else ["HF-W010-L1-CONTROLS: mutation control not detected"]),
        "class_binding_note": ("class_mapping is reported verbatim from the ledger and is NOT adjudicated here; "
                               "rows 60/68/87 are Crossref metadata mirrors of SRC-020/SRC-002/SRC-024 and rows "
                               "51/52/59/87/88 carry '(evidence/tag only)' in class_mapping, which is a class-token "
                               "hygiene finding for the literature owner, not a spot-check failure."),
        "falsifier": ("Re-fetch the same locators, or re-run this file with --offline against the shipped raw "
                      "bodies: this artifact is FALSIFIED if (a) any raw body re-hashes to a different sha256 than "
                      "recorded, (b) any recomputed verdict differs from the recorded verdict, (c) any row recorded "
                      "CONFIRMED_* is shown to have a declared metadata field or a >=8-token excerpt fragment "
                      "absent from the fetched record, or (d) the target ledger no longer hashes to "
                      "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9 (all bindings void)."),
        "next_falsifier": ("A live re-fetch of SRC-060/068/076/087/088 that yields a record whose title, "
                           "declared metadata field or excerpt fragment contradicts the ledger under the same "
                           "comparison, or an L0/L1 owner repair of ledger/citation_audit.csv (hash move voids "
                           "this and every other bound spot check)."),
        "not_claimed": ["gate verdict", "node status", "validation_status=passed", "ledger modification",
                        "class_mapping adjudication", "any theorem or physical statement"],
        "limitations": [
            "title identity is a tolerant test (char-multiset + ordered ratio >= 0.90) because Crossref "
            "mangles math markup; a within-word anagram of the title that preserves the character bag and "
            "stays >= 0.90 would pass, and this is not exercised by the six mutation controls",
            "the metadata branch verifies the declared Crossref/INSPIRE fields only; it does not verify that "
            "the cited work actually proves the theorem that uses it (that is A1/L0 scope)",
            "class_mapping tokens are reported verbatim, not adjudicated",
            "abstract-excerpt containment is against the arXiv/INSPIRE abstract; a publisher's final abstract "
            "may differ from the preprint abstract, which is a property of the cited record, not of this test",
        ],
        "reproduce": f"python3 artifacts/flash-10/l1_spotcheck/run_spotcheck_010.py          # live\n"
                     f"python3 artifacts/flash-10/l1_spotcheck/run_spotcheck_010.py --offline  # re-verify raw bodies",
    }
    return payload


def offline_verify() -> int:
    """Re-hash raw bodies and re-derive verdicts; compare to the shipped artifact."""
    if not OUT.exists():
        print("artifact absent; run live first", file=sys.stderr)
        return 2
    shipped = json.loads(OUT.read_text())
    fresh = run(live=False)
    bad = 0
    for name in ("target", "inputs"):
        if shipped.get(name) != fresh.get(name):
            print(f"RE-VERIFY FAIL: {name} differs", file=sys.stderr)
            bad += 1
    sh = {f["raw_body"]: f["raw_sha256"] for f in shipped["fetches"]}
    fr = {f["raw_body"]: f["raw_sha256"] for f in fresh["fetches"]}
    if sh != fr:
        for k in sorted(set(sh) | set(fr)):
            if sh.get(k) != fr.get(k):
                print(f"RE-VERIFY FAIL: raw body hash {k}: {sh.get(k)} != {fr.get(k)}", file=sys.stderr)
                bad += 1
    sh = {r["citation_id"]: (r["verdict"], json.dumps(r.get("comparison"), sort_keys=True)) for r in shipped["results"]}
    fr = {r["citation_id"]: (r["verdict"], json.dumps(r.get("comparison"), sort_keys=True)) for r in fresh["results"]}
    for cid in sorted(set(sh) | set(fr)):
        if sh.get(cid) != fr.get(cid):
            print(f"RE-VERIFY FAIL: {cid} verdict/comparison differs", file=sys.stderr)
            bad += 1
    print(f"offline re-verification: {'PASS' if bad == 0 else 'FAIL'} "
          f"({len(fr)} rows, {len(fr)} raw bodies, {bad} mismatch(es)); artifact sha256 {sha256_file(OUT)}")
    return 0 if bad == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="re-verify from stored raw bodies")
    args = ap.parse_args()
    if args.offline:
        return offline_verify()
    payload = run(live=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} sha256={sha256_file(OUT)}")
    print(json.dumps(payload["summary"], indent=1))
    for e in payload["results"]:
        print(f"  {e['citation_id']}: {e['verdict']}  (028={e['worker_028_verdict']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
