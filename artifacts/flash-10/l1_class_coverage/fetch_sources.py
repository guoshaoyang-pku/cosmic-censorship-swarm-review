#!/usr/bin/env python3
"""flash-10 / L1 class-coverage: build a *verified-metadata* source registry.

Every locator used by the class-coverage matrix must come from a raw arXiv API
response saved under raw/.  Nothing is written from memory: if a query does not
match, the entry is recorded as unmatched and the matrix must treat it as
unresolved.

Usage:
    python3 fetch_sources.py            # fetch missing raw/*.xml, then rebuild sources.json
    python3 fetch_sources.py --offline  # parse existing raw/*.xml only
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
STOP = {"the", "a", "an", "of", "and", "in", "on", "for", "to", "with", "by", "is", "are"}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP}


def overlap(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta)


def fetch(url: str, tries: int = 5, timeout: int = 40) -> tuple[int, bytes]:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ai4math-swarm-flash10/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:  # 429 needs a longer cool-down
            last = e
            time.sleep(10 + 8 * i if e.code == 429 else 2 + 2 * i)
        except Exception as e:  # noqa: BLE001 - network errors vary
            last = e
            time.sleep(2 + 2 * i)
    raise RuntimeError(f"fetch failed after {tries} tries: {type(last).__name__}: {last}")


def parse_feed(xml: bytes) -> list[dict]:
    root = ET.fromstring(xml)
    out = []
    for e in root.findall(f"{ATOM}entry"):
        def text(tag: str) -> str:
            node = e.find(tag)
            return re.sub(r"\s+", " ", node.text or "").strip() if node is not None else ""

        aid = text(f"{ATOM}id")
        m = re.search(r"abs/([0-9]{4}\.[0-9]{4,5})(v[0-9]+)?", aid)
        out.append({
            "arxiv_id": m.group(1) if m else aid,
            "version": m.group(2) if (m and m.group(2)) else "",
            "title": text(f"{ATOM}title"),
            "abstract": text(f"{ATOM}summary"),
            "published": text(f"{ATOM}published"),
            "updated": text(f"{ATOM}updated"),
            "authors": [re.sub(r"\s+", " ", (a.find(f"{ATOM}name").text or "")).strip()
                        for a in e.findall(f"{ATOM}author") if a.find(f"{ATOM}name") is not None],
            "primary_category": (e.find(f"{ARXIV}primary_category").get("term")
                                 if e.find(f"{ARXIV}primary_category") is not None else ""),
            "journal_ref": text(f"{ARXIV}journal_ref"),
            "doi": text(f"{ARXIV}doi"),
            "comment": text(f"{ARXIV}comment"),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="parse existing raw XML only")
    args = ap.parse_args()

    cfg = json.loads((HERE / "queries.json").read_text())
    ov = json.loads((HERE / "overrides.json").read_text()) if (HERE / "overrides.json").exists() else {}
    reject = ov.get("reject_selected", {})
    rekey = ov.get("rekey_selected", {})
    RAW.mkdir(parents=True, exist_ok=True)
    sources, failures, manual_rejections = [], [], []

    for q in cfg["queries"]:
        key, raw_path = q["key"], RAW / f"{q['key']}.xml"
        status, err = None, None
        if raw_path.exists():
            xml = raw_path.read_bytes()
            status = 200
            fetched_at = datetime.fromtimestamp(raw_path.stat().st_mtime, CST).isoformat(timespec="seconds")
            cached = True
        elif args.offline:
            failures.append({"key": key, "error": "no cached raw xml (offline)"})
            continue
        else:
            params = {
                "search_query": q["query"],
                "start": 0,
                "max_results": q.get("max_results", 5),
                "sortBy": "submittedDate" if q.get("sort") == "submittedDate" else "relevance",
                "sortOrder": "descending",
            }
            url = cfg["endpoint"] + "?" + urllib.parse.urlencode(params)
            try:
                status, xml = fetch(url)
                raw_path.write_bytes(xml)
                fetched_at = now()
                cached = False
                time.sleep(1.0)  # be polite to the API between live queries
            except Exception as e:  # noqa: BLE001
                failures.append({"key": key, "query": q["query"], "error": str(e)})
                sources.append({"key": key, "query": q["query"], "class_hint": q["class_hint"],
                                "retrieval_status": "fetch_failed", "error": str(e),
                                "selection_status": "fetch_failed", "selected": None, "candidates": []})
                print(f"[FAIL] {key}: {e}")
                continue

        try:
            entries = parse_feed(xml)
        except ET.ParseError as e:
            failures.append({"key": key, "error": f"xml parse: {e}"})
            entries = []

        scored = sorted(({"arxiv_id": en["arxiv_id"], "title": en["title"],
                          "overlap": round(overlap(q["expect_title"], en["title"]), 3)} for en in entries),
                        key=lambda x: -x["overlap"])
        threshold = q.get("threshold", cfg["default_threshold"])
        best = next((en for en in entries if overlap(q["expect_title"], en["title"]) >= threshold), None)
        record = {
            "key": key, "query": q["query"], "class_hint": q["class_hint"],
            "retrieval_status": "ok" if entries else "empty", "http_status": status,
            "raw_path": str(raw_path.relative_to(HERE)), "fetched_at": fetched_at, "cached": cached,
            "selection_threshold": threshold,
            "selected": (dict(best, overlap=round(overlap(q["expect_title"], best["title"]), 3))
                         if best else None),
            "candidates": scored[:5],
        }
        if best is None and entries:
            record["selection_status"] = "unmatched"
            failures.append({"key": key, "error": "no candidate above title-overlap threshold",
                             "top": scored[0]["title"] if scored else None})
        else:
            record["selection_status"] = "matched" if best else "empty"
        if key in reject and record.get("selected"):
            record["rejected_selected"] = record.pop("selected")
            record["selection_status"] = "manual_reject"
            record["reject_reason"] = reject[key]
            manual_rejections.append({"key": key, "reason": reject[key],
                                      "rejected_arxiv_id": record["rejected_selected"]["arxiv_id"]})
        if key in rekey:
            record["matrix_key"] = rekey[key]
        else:
            record["matrix_key"] = key
        sources.append(record)
        sel = record.get("selected")
        print(f"[{'OK ' if sel else 'MISS'}] {record['matrix_key']:32s} -> "
              f"{(sel['arxiv_id'] + ' ' + sel['title'][:70]) if sel else record['selection_status']}")

    registry = {
        "generated_at": now(),
        "generator": "artifacts/flash-10/l1_class_coverage/fetch_sources.py",
        "endpoint": cfg["endpoint"],
        "purpose": cfg["purpose"],
        "note": "selected == null means the locator must NOT be written into the matrix; record unresolved.",
        "counts": {"queries": len(cfg["queries"]),
                   "matched": sum(1 for s in sources if s.get("selection_status") == "matched"),
                   "unmatched": sum(1 for s in sources if s.get("selection_status") == "unmatched"),
                   "manual_reject": len(manual_rejections),
                   "fetch_failed": sum(1 for s in sources if s.get("retrieval_status") == "fetch_failed")},
        "sources": sources,
        "failures": failures,
        "manual_rejections": manual_rejections,
    }
    (HERE / "sources.json").write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")

    # human digest for curation
    lines = [f"# Source digest (generated {registry['generated_at']})", ""]
    for s in sources:
        sel = s.get("selected")
        mkey = s.get("matrix_key", s["key"])
        if not sel:
            lines += [f"## {mkey} -- UNRESOLVED ({s.get('selection_status', s.get('retrieval_status'))})",
                      f"query: `{s['query']}`", ""]
            continue
        lines += [f"## {mkey}", f"- arXiv: {sel['arxiv_id']} (overlap {sel['overlap']})",
                  f"- title: {sel['title']}", f"- authors: {', '.join(sel['authors'][:6])}",
                  f"- published: {sel['published'][:10]}  journal_ref: {sel['journal_ref'] or '-'}  doi: {sel['doi'] or '-'}",
                  f"- query: `{s['query']}`", "", f"> {sel['abstract']}", ""]
    (HERE / "SOURCE_DIGEST.md").write_text("\n".join(lines))
    print(json.dumps(registry["counts"]))
    print(f"wrote {HERE/'sources.json'} and SOURCE_DIGEST.md")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
