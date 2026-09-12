#!/usr/bin/env python3
"""Worker 09 / L1 closing check: independent locator sweep over SCC-side ledger rows.

For every canonical audit row cited by an SCC-tagged theorem in ledger/theorems.jsonl,
re-resolve the locator (OpenAlex for DOI, arXiv abs page for arXiv-only) and compare the
returned title with the ledger title. Writes:
  artifacts/worker-09/extracted/scc_locator_sweep.json   machine record
  artifacts/worker-09/extracted/scc_locator_sweep.md     readable table

This is a title-level identity check (does the locator point at the right work?), not a
theorem-scope check; scope is covered by the hand-audited shard rows.
"""
from __future__ import annotations

import csv
import difflib
import html as html_mod
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
W09 = ROOT / "artifacts" / "worker-09"
OUT = W09 / "extracted"
LEDGER = ROOT / "ledger"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
CACHE = W09 / "sources" / "sweep_cache"
CACHE.mkdir(parents=True, exist_ok=True)


def curl(url: str, cache_name: str, timeout: int = 40) -> tuple[str, str]:
    """Return (http_code_or_ERR, body). Cached on disk."""
    p = CACHE / cache_name
    if p.exists() and p.stat().st_size > 200:
        return "CACHED", p.read_text(errors="replace")
    try:
        r = subprocess.run(
            ["curl", "-sSL", "-m", str(timeout), "-A", UA, url],
            capture_output=True, text=True, timeout=timeout + 10)
        body = r.stdout or ""
        p.write_text(body, errors="replace")
        return ("200" if r.returncode == 0 and body else "ERR"), body
    except Exception as e:  # pragma: no cover
        return "ERR", f"@@{e}@@"


def norm(s: str) -> str:
    s = html_mod.unescape(s or "")
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def scc_source_ids() -> list[str]:
    ids: set[str] = set()
    for line in (LEDGER / "theorems.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        cls = " ".join(e.get("class_ids") or [])
        if "SCC" in cls:
            for s in e.get("source_ids") or []:
                ids.add(s)
    return sorted(ids)


def main() -> int:
    rows = {r["citation_id"]: r for r in csv.DictReader((LEDGER / "citation_audit.csv").open())}
    ids = scc_source_ids()
    out = []
    for cid in ids:
        r = rows.get(cid)
        if not r:
            out.append({"citation_id": cid, "status": "row_missing"})
            continue
        title = r.get("title", "")
        doi = (r.get("doi") or "").strip()
        arxiv = (r.get("arxiv_id") or "").strip()
        rec = {"citation_id": cid, "bibkey": r.get("bibkey"), "ledger_title": title,
               "ledger_doi": doi, "ledger_arxiv": arxiv, "method": None,
               "http": None, "resolved_title": None, "title_ratio": None,
               "verdict": "unresolved"}
        if doi:
            code, body = curl(f"https://api.openalex.org/works/doi:{doi}",
                              f"oa_{re.sub(r'[^A-Za-z0-9]+', '_', doi)}.json")
            rec["method"] = "openalex-doi"
            rec["http"] = code
            try:
                d = json.loads(body)
                rec["resolved_title"] = d.get("title")
                rec["resolved_year"] = d.get("publication_year")
            except Exception:
                rec["resolved_title"] = None
        if not rec.get("resolved_title") and arxiv:
            aid = arxiv
            code, body = curl(f"https://arxiv.org/abs/{aid}",
                              f"arx_{re.sub(r'[^A-Za-z0-9.]+', '_', aid)}.html")
            rec["method"] = "arxiv-abs"
            rec["http"] = code
            t = html_mod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)))
            m = re.search(r"Title:\s*(.+?)(?:Authors:|Abstract:|Comments:|$)", t)
            rec["resolved_title"] = m.group(1).strip() if m else None
        if rec.get("resolved_title"):
            rec["title_ratio"] = round(ratio(title, rec["resolved_title"]), 3)
            rec["verdict"] = "match" if rec["title_ratio"] >= 0.82 else "MISMATCH"
        out.append(rec)

    summary = {
        "checked": len(out),
        "match": sum(1 for r in out if r["verdict"] == "match"),
        "mismatch": sum(1 for r in out if r["verdict"] == "MISMATCH"),
        "unresolved": sum(1 for r in out if r["verdict"] == "unresolved"),
        "source_ids": ids,
    }
    (OUT / "scc_locator_sweep.json").write_text(json.dumps({"summary": summary, "rows": out}, indent=2))
    lines = ["# SCC-side locator sweep (worker-09, closing check)", "",
             f"- rows checked: {summary['checked']} | match: {summary['match']} | "
             f"MISMATCH: {summary['mismatch']} | unresolved: {summary['unresolved']}", "",
             "| SRC | bibkey | method | title ratio | verdict |", "|---|---|---|---|---|"]
    for r in out:
        lines.append(f"| {r['citation_id']} | {r.get('bibkey','')} | {r.get('method','')} | "
                     f"{r.get('title_ratio','')} | {r['verdict']} |")
    (OUT / "scc_locator_sweep.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=1))
    for r in out:
        if r["verdict"] != "match":
            print("  !", r["citation_id"], r["verdict"], r.get("title_ratio"),
                  "|", (r.get("resolved_title") or "")[:70])
    return 0


if __name__ == "__main__":
    sys.exit(main())
