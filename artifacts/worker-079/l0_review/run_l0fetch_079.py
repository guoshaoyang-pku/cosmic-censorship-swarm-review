#!/usr/bin/env python3
"""W079-L0-BLIND-FULL-REVIEW-01 pre-registered live locator re-fetch.

Implements the sample_rule_frozen block of PREREGISTRATION.json exactly:
the sample is computed from the pinned ledger + citation audit before any fetch,
excluding source ids already referenced by prior L1 spot-check artifacts.

Read-only with respect to the repository. Writes only l0_fetch_evidence.json
in this directory. Exit 2 on pin drift (before or after the fetches).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEED = "W079-L0-BLIND-FULL-REVIEW-01"
UA = {"User-Agent": "w079-l0-review/1.0 (independent verification; read-only)"}
PINS = {
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}
SPOTCHECK_GLOBS = ("reviews/L1-spotcheck-*.json", "artifacts/*/l1_spotcheck/*.json")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def tokens(title: str) -> set:
    return {t for t in re.sub(r"[^a-z0-9 ]", " ", (title or "").lower()).split() if len(t) >= 3}


def overlap(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def get(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read()


def fetch_arxiv(arxiv_id: str):
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    status, body = get(url)
    text = body.decode("utf-8", "replace")
    entries = re.findall(r"<entry>(.*?)</entry>", text, re.S)
    if not entries:
        return status, sha256_text(text), None, None, url
    e = entries[0]
    tm = re.search(r"<title>(.*?)</title>", e, re.S)
    pm = re.search(r"<published>(\d{4})", e)
    im = re.search(r"<id>\s*https?://arxiv\.org/abs/([^<\s]+)", e)
    title = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else None
    year = int(pm.group(1)) if pm else None
    if not im or im.group(1).split("v")[0] != str(arxiv_id).split("v")[0]:
        return status, sha256_text(text), title, year, url
    return status, sha256_text(text), title, year, url


def fetch_doi(doi: str):
    url = f"https://api.crossref.org/works/{doi}"
    status, body = get(url)
    d = json.loads(body.decode("utf-8", "replace"))
    msg = d.get("message", {})
    title = (msg.get("title") or [None])[0]
    parts = (msg.get("issued") or {}).get("date-parts") or [[None]]
    year = parts[0][0] if parts and parts[0] else None
    returned = str(msg.get("DOI", "")).lower()
    title2 = title if returned == doi.lower() else None
    return status, sha256_text(body.decode("utf-8", "replace")), title2, year, url


def classify(audit_title, audit_year, fetched_title, fetched_year):
    if fetched_title is None:
        return "FAIL"
    ov = overlap(audit_title, fetched_title)
    dy = abs((audit_year or 0) - (fetched_year or 0)) if audit_year and fetched_year else None
    if ov < 0.35:
        return "FAIL"
    if ov >= 0.6 and (dy is None or dy <= 1):
        return "MATCH"
    return "PARTIAL"


def main() -> int:
    pre = {p: sha256_file(ROOT / p) for p in PINS}
    if any(pre[p] != PINS[p] for p in PINS):
        print(json.dumps({"status": "PIN_DRIFT", "before": pre}, indent=1))
        return 2

    rows = [json.loads(l) for l in (ROOT / "ledger/theorems.jsonl").read_text().splitlines() if l.strip()]
    citations = {c["citation_id"]: c for c in csv.DictReader((ROOT / "ledger/citation_audit.csv").open())}

    prior_files = sorted({str(p.relative_to(ROOT)) for g in SPOTCHECK_GLOBS for p in ROOT.glob(g)})
    prior_srcs = set()
    for rel in prior_files:
        prior_srcs |= set(re.findall(r"SRC-\d{3}", (ROOT / rel).read_text(errors="replace")))

    candidates = []
    for r in rows:
        for sid in r.get("source_ids") or []:
            c = citations.get(sid)
            if not c or sid in prior_srcs:
                continue
            if c.get("arxiv_id") or c.get("doi"):
                key = sha256_text(f"{r['theorem_id']}|{sid}|{SEED}")
                candidates.append((key, r["theorem_id"], sid))
    candidates.sort()
    sample = candidates[:5]

    evidence = []
    for i, (_key, tid, sid) in enumerate(sample):
        c = citations[sid]
        kind = "arxiv" if c.get("arxiv_id") else "doi"
        try:
            if kind == "arxiv":
                status, bhash, ftitle, fyear, url = fetch_arxiv(c["arxiv_id"])
            else:
                status, bhash, ftitle, fyear, url = fetch_doi(c["doi"])
            verdict = classify(c.get("title"), int(c["year"]) if c.get("year") else None, ftitle, fyear)
            err = None
        except urllib.error.HTTPError as e:
            status, bhash, ftitle, fyear, url, verdict, err = e.code, None, None, None, None, "UNRESOLVED-NETWORK", f"HTTPError {e.code}"
        except Exception as e:  # noqa: BLE001 - network failures recorded, not raised
            status, bhash, ftitle, fyear, url, verdict, err = None, None, None, None, None, "UNRESOLVED-NETWORK", f"{type(e).__name__}: {e}"
        evidence.append({
            "theorem_id": tid, "source_id": sid, "locator_kind": kind,
            "locator": c.get("arxiv_id") or c.get("doi"), "url": url,
            "http_status": status, "body_sha256": bhash,
            "audit_title": c.get("title"), "audit_year": c.get("year"),
            "fetched_title": ftitle, "fetched_year": fyear,
            "title_overlap": round(overlap(c.get("title"), ftitle), 3) if ftitle else 0.0,
            "verdict": verdict, "error": err,
        })
        time.sleep(1.2)

    post = {p: sha256_file(ROOT / p) for p in PINS}
    if post != pre:
        print(json.dumps({"status": "PIN_DRIFT_DURING_RUN", "before": pre, "after": post}, indent=1))
        return 2

    summary = {v: sum(1 for e in evidence if e["verdict"] == v)
               for v in ("MATCH", "PARTIAL", "FAIL", "UNRESOLVED-NETWORK")}
    out = {
        "task_id": SEED,
        "sample_rule": "sha256('<theorem_id>|<source_id>|" + SEED + "') ascending, first 5 eligible, prior spot-check SRCs excluded",
        "prior_spotcheck_files_scanned": len(prior_files),
        "prior_spotcheck_sources_excluded": len(prior_srcs),
        "eligible_candidates": len(candidates),
        "sample": evidence,
        "summary": summary,
        "decision_rule": "FAIL on any sample => review verdict revise; <3 resolved => revise; all pins stable",
        "pins": pre,
    }
    p = HERE / "l0_fetch_evidence.json"
    p.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"status": "OK", "sample": [(e["theorem_id"], e["source_id"], e["verdict"]) for e in evidence],
                      "summary": summary, "evidence_sha256": sha256_file(p)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
