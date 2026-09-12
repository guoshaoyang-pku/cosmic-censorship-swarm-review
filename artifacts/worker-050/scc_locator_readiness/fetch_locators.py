#!/usr/bin/env python3
"""W050-SCC-LOCATOR-READINESS-02: live-fetch pass for SCC-bound weak locator rows.

Scope: rows of the frozen L1 citation ledger (ledger/citation_audit.csv) whose
class_mapping contains AF-SCC-C2-VAC-GEN or AF-SCC-C0-VAC-GEN and whose
`exact_locator` is not a per-row record locator.  Read-only: this script never
edits the ledger; it writes an observation file that a separate deterministic
assembler consumes.

Why a separate fetch pass: HTTP observations are not reproducible from bytes, so
they are recorded once, with the ledger sha256 they were made against, and the
assembler treats a missing or non-200 observation as UNVERIFIED rather than as a
pass.  A ledger revision invalidates the whole observation set.

Falsifiers:
  F1 a fetched locator that does not return the cited work (title mismatch)
     voids that row's CONFIRMED verdict;
  F3 any change to ledger/citation_audit.csv away from the pinned sha256 voids
     the whole table;
  F4 a live re-fetch returning HTTP != 200 or a different record voids the row.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
PINNED_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
SCC_CLASSES = ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN")
UA = "Mozilla/5.0 (compatible; ai4math-swarm-worker-050/1.0; locator-readiness-audit)"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def weak_locator(locator: str) -> bool:
    """True when the string is not a single-record locator (strict reading)."""
    loc = (locator or "").strip()
    if not loc:
        return True
    if "..." in loc:
        return True
    low = loc.lower()
    if any(tok in low for tok in ("search_query=", "?q=", "&q=", "/search")):
        return True
    return not (loc.startswith("http://") or loc.startswith("https://"))


def norm_title(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = s.lower()
    s = re.sub(r"\\[a-z]+", " ", s)          # drop LaTeX control words
    s = re.sub(r"[^a-z0-9]+", " ", s)        # keep alphanumerics only
    return " ".join(s.split())


def title_match(ledger_title: str, returned_title: str) -> tuple[bool, float, str]:
    a, b = norm_title(ledger_title), norm_title(returned_title)
    if not a or not b:
        return False, 0.0, "no_title"
    if a == b:
        return True, 1.0, "exact_normalised_equality"
    if a in b or b in a:
        return True, round(min(len(a), len(b)) / max(len(a), len(b)), 3), "normalised_containment"
    ta, tb = set(a.split()), set(b.split())
    inter = ta & tb
    if not inter:
        return False, 0.0, "no_token_overlap"
    precision, recall = len(inter) / len(tb), len(inter) / len(ta)
    f1 = 2 * precision * recall / (precision + recall)
    return (f1 >= 0.75), round(f1, 3), "token_f1"


def _html_title(body: str) -> str:
    for pat in (
        r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_title["\']',
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        r"<title[^>]*>(.*?)</title>",
    ):
        m = re.search(pat, body, re.I | re.S)
        if m:
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            t = re.sub(r"^\[[^\]]+\]\s*", "", t)          # arXiv id prefix
            t = re.sub(r"^Title:\s*", "", t, flags=re.I)
            if t:
                return t
    return ""


def parse_body(url: str, content_type: str, body: bytes) -> tuple[str, str]:
    """Return (returned_title, parse_kind)."""
    text = body.decode("utf-8", "replace")
    if "json" in (content_type or "").lower() or text.lstrip()[:1] in "{[":
        try:
            doc = json.loads(text)
        except Exception:
            doc = None
        if isinstance(doc, dict):
            md = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else doc
            titles = md.get("titles") if isinstance(md, dict) else None
            if isinstance(titles, list) and titles and isinstance(titles[0], dict):
                return str(titles[0].get("title", "")), "json_metadata_titles"
            if isinstance(md, dict) and isinstance(md.get("title"), str):
                return md["title"], "json_title"
            msg = doc.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("title"), list) and msg["title"]:
                return str(msg["title"][0]), "crossref_message_title"
    return _html_title(text), "html"


def json_ids(body: bytes, markers: tuple[str, ...]) -> list[str]:
    """Extract identifier tokens (doi/arxiv) present in a JSON body."""
    try:
        doc = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return []
    out: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in markers and isinstance(v, (str, int)):
                    out.append(str(v))
                elif k == "value" and isinstance(v, str):
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(doc)
    return out


def fetch(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.5"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(200000)
            return {
                "http_status": int(resp.status),
                "final_url": resp.geturl(),
                "content_type": resp.headers.get("Content-Type", ""),
                "body": body,
                "elapsed_s": round(time.time() - t0, 3),
            }
    except urllib.error.HTTPError as e:
        return {"http_status": int(e.code), "final_url": url, "content_type": e.headers.get("Content-Type", ""),
                "body": e.read(20000), "elapsed_s": round(time.time() - t0, 3), "error": "HTTPError"}
    except Exception as e:  # noqa: BLE001 - network errors are recorded, never raised
        return {"http_status": None, "final_url": url, "content_type": "", "body": b"",
                "elapsed_s": round(time.time() - t0, 3), "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--only", default="", help="comma-separated citation_ids (debug)")
    ap.add_argument("--sleep", type=float, default=0.3)
    args = ap.parse_args()

    ledger_sha = sha256_file(args.ledger)
    rows = list(csv.DictReader(open(args.ledger, newline="")))
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    targets = []
    for r in rows:
        cm = {t.strip() for t in (r.get("class_mapping") or "").split(";") if t.strip()}
        if not (cm & set(SCC_CLASSES)):
            continue
        if only and r["citation_id"] not in only:
            continue
        targets.append(r)

    fetches = []
    for r in sorted(targets, key=lambda x: x["citation_id"]):
        loc = (r.get("exact_locator") or "").strip()
        candidate = (r.get("evidence_url") or "").strip()
        rec = {
            "citation_id": r["citation_id"],
            "bibkey": r["bibkey"],
            "class_mapping": r["class_mapping"],
            "ledger_title": r["title"],
            "ledger_arxiv_id": (r.get("arxiv_id") or "").strip(),
            "ledger_doi": (r.get("doi") or "").strip(),
            "current_exact_locator": loc,
            "current_classification": "weak" if weak_locator(loc) else "direct_record_locator",
            "fetched_locator": candidate,
            "fetched_at": datetime.now(TZ).replace(microsecond=0).isoformat(),
        }
        if not candidate:
            rec.update({"http_status": None, "verdict": "NO_CANDIDATE", "note": "row has no evidence_url"})
            fetches.append(rec)
            continue
        obs = fetch(candidate, args.timeout)
        body = obs.pop("body")
        title, parse_kind = parse_body(obs["final_url"] or candidate, obs["content_type"], body)
        matched, ratio, basis = title_match(r["title"], title)
        ids = json_ids(body, ("doi", "dois", "arxiv_eprints", "arxiv_id", "eprint"))
        doi_match = bool(r.get("doi")) and any(r["doi"].lower() in i.lower() for i in ids)
        arxiv_match = bool(r.get("arxiv_id")) and any(r["arxiv_id"].lower() in i.lower() for i in ids)
        rec.update({
            "http_status": obs["http_status"],
            "final_url": obs["final_url"],
            "content_type": obs["content_type"],
            "elapsed_s": obs["elapsed_s"],
            "error": obs.get("error"),
            "parse_kind": parse_kind,
            "title_returned": title,
            "title_match": matched,
            "title_match_ratio": ratio,
            "title_match_basis": basis,
            "doi_match_in_body": doi_match,
            "arxiv_id_match_in_body": arxiv_match,
            "response_excerpt": re.sub(r"\s+", " ", body.decode("utf-8", "replace"))[:400],
        })
        rec["verdict"] = (
            "CONFIRMED" if obs["http_status"] == 200 and matched
            else ("FAIL_TITLE_MISMATCH" if obs["http_status"] == 200
                  else "UNVERIFIED_HTTP_%s" % obs["http_status"])
        )
        fetches.append(rec)
        time.sleep(args.sleep)

    out = {
        "artifact_id": "W050-SCC-LOCATOR-READINESS-02-fetch",
        "artifact_type": "live_fetch_observations",
        "actor": "worker-050",
        "created_at": datetime.now(TZ).replace(microsecond=0).isoformat(),
        "ledger": args.ledger,
        "ledger_sha256_measured": ledger_sha,
        "ledger_sha256_pinned": PINNED_LEDGER_SHA256,
        "matches_pin": ledger_sha == PINNED_LEDGER_SHA256,
        "scope": "rows whose class_mapping contains %s" % " or ".join(SCC_CLASSES),
        "fetch_count": len(fetches),
        "confirmed": sum(1 for f in fetches if f.get("verdict") == "CONFIRMED"),
        "fetches": fetches,
    }
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print(
        "fetched=%d confirmed=%d failed_or_unverified=%d ledger_pin_ok=%s"
        % (len(fetches), out["confirmed"],
           len(fetches) - out["confirmed"], ledger_sha == PINNED_LEDGER_SHA256)
    )
    return 0 if ledger_sha == PINNED_LEDGER_SHA256 else 3


if __name__ == "__main__":
    sys.exit(main())
