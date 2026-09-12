#!/usr/bin/env python3
"""W050-L0-INDEPENDENT-SPOTCHECK-04 -- live re-fetch pass over the static sample.

Reads the deterministic class-stratified sample from static_report.json (2 L0 rows per
frozen class, each with one per-record locator), re-fetches each locator live, extracts a
title from the returned record (HTML or API JSON) and compares it to the title recorded in
the pinned L1 ledger.

Usage:
  python3 fetch_l0_sample.py --pass 1   -> fetch_evidence.json
  python3 fetch_l0_sample.py --pass 2   -> fetch_evidence_recheck.json

Exit codes: 0 all fetches completed and titles matched; 1 at least one fetch failed or
mismatched (recorded, not hidden); 3 ledger pin drift (fail closed).
This is an independent worker measurement; it edits no ledger and sets no gate verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
L0_PATH = ROOT / "ledger" / "theorems.jsonl"
L1_PATH = ROOT / "ledger" / "citation_audit.csv"
L0_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
L1_PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
UA = "ai4math-swarm-l0-spotcheck/1.0 (worker-050 independent re-fetch)"
TIMEOUT = 30
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 1}


def title_match(recorded: str, fetched: str) -> dict:
    a, b = norm_tokens(recorded), norm_tokens(fetched)
    if not a or not b:
        return {"matched": False, "jaccard": 0.0, "recorded_tokens_missing": sorted(a)}
    inter = a & b
    return {
        "matched": len(inter) / len(a | b) >= 0.6 or a <= b,
        "jaccard": round(len(inter) / len(a | b), 4),
        "recorded_tokens_missing": sorted(a - b)[:12],
    }


def extract_title(body: str, content_type: str, url: str) -> str:
    if "json" in (content_type or "") or body.lstrip()[:1] in "[{":
        try:
            doc = json.loads(body)
        except ValueError:
            doc = None
        if isinstance(doc, dict):
            md = doc.get("metadata") or {}
            for candidate in (
                (md.get("titles") or [{}])[0].get("title") if isinstance(md, dict) else None,
                doc.get("title"),
                doc.get("result", {}).get("title") if isinstance(doc.get("result"), dict) else None,
            ):
                if candidate:
                    return str(candidate)
    for pattern in (
        r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\'](.*?)["\']',
        r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']citation_title["\']',
        r"<title[^>]*>(.*?)</title>",
    ):
        m = re.search(pattern, body, re.S | re.I)
        if m:
            title = re.sub(r"\s+", " ", m.group(1)).strip()
            title = re.sub(r"\s*[\.\-–]\s*arXiv:\s*\S+.*$", "", title, flags=re.I).strip()
            return title
    return ""


def fetch(url: str) -> dict:
    attempts = []
    for attempt in (1, 2):
        started = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read(400000).decode("utf-8", "ignore")
                attempts.append(
                    {
                        "attempt": attempt,
                        "http_status": resp.status,
                        "final_url": resp.geturl(),
                        "content_type": resp.headers.get("Content-Type", ""),
                        "bytes_sampled": len(body),
                        "elapsed_ms": int((time.time() - started) * 1000),
                        "error": None,
                    }
                )
                return {"ok": True, "attempts": attempts, "title": extract_title(body, resp.headers.get("Content-Type", ""), url)}
        except urllib.error.HTTPError as exc:
            attempts.append(
                {
                    "attempt": attempt,
                    "http_status": exc.code,
                    "final_url": url,
                    "error": f"HTTPError: {exc.reason}",
                    "elapsed_ms": int((time.time() - started) * 1000),
                }
            )
        except Exception as exc:  # noqa: BLE001 - network failures are data here
            attempts.append(
                {
                    "attempt": attempt,
                    "http_status": None,
                    "final_url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                    "elapsed_ms": int((time.time() - started) * 1000),
                }
            )
        if attempt == 1:
            time.sleep(3)
    return {"ok": False, "attempts": attempts, "title": ""}


def load_l1():
    import csv

    with open(L1_PATH, newline="") as fh:
        return {r["citation_id"]: r for r in csv.DictReader(fh)}


def per_record_locators(item: dict, l1: dict) -> list[str]:
    """Ordered unique per-record locators for one sampled row: primary first, then fallbacks."""
    rec = l1.get(item["source_id"], {})
    ordered = [item["locator"]]
    for field in ("evidence_url", "url", "exact_locator"):
        url = (rec.get(field) or "").strip()
        if url and url not in ordered and not any(m in url for m in ("api/query", "api/literature?q=", "search_query=", "?q=", "/search")):
            ordered.append(url)
    return ordered


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pass", dest="pass_no", type=int, choices=(1, 2), default=1)
    args = ap.parse_args()

    if sha256(L0_PATH) != L0_PIN or sha256(L1_PATH) != L1_PIN:
        print("PIN DRIFT at fetch start; refusing to run", file=sys.stderr)
        return 3

    sample = json.loads((OUT / "static_report.json").read_text())["spotcheck_sample"]
    l1 = load_l1()
    records = []
    for item in sample:
        tried, best = [], None
        for locator in per_record_locators(item, l1):
            result = fetch(locator)
            comparison = title_match(item["l1_title"], result["title"])
            ok = result["ok"] and comparison["matched"]
            tried.append(
                {
                    "locator": locator,
                    "http_status": result["attempts"][-1].get("http_status"),
                    "ok": result["ok"],
                    "fetched_title": result["title"],
                    "title_comparison": comparison,
                    "attempts": result["attempts"],
                }
            )
            if ok and best is None:
                best = tried[-1]
            if ok:
                break
        records.append(
            {
                **item,
                "fetched_at": now(),
                "locators_tried": tried,
                "matched_locator": best["locator"] if best else None,
                "matched_locator_field": next(
                    (f for f in ("evidence_url", "url", "exact_locator")
                     if (l1.get(item["source_id"], {}).get(f) or "").strip() == (best or {}).get("locator")),
                    None,
                ) if best else None,
                "verdict": "match" if best else "mismatch_or_unverified",
            }
        )
        last = tried[-1]
        print(f"  {item['theorem_id']} {item['source_id']} -> {records[-1]['verdict']} "
              f"({len(tried)} locator(s) tried; last http={last['http_status']})")

    drift = sha256(L0_PATH) != L0_PIN or sha256(L1_PATH) != L1_PIN
    out = {
        "task_id": "W050-L0-INDEPENDENT-SPOTCHECK-04",
        "artifact_type": f"live_refetch_pass_{args.pass_no}",
        "class_id": ";".join(sorted({s["class_id"] for s in sample})),
        "node_id": "L0",
        "gate": "G-LIT",
        "actor": "worker-050",
        "pass": args.pass_no,
        "fetched_at": now(),
        "pins": {"L0": L0_PIN, "L1": L1_PIN, "pin_drift_after_fetch": drift},
        "counts": {
            "requested": len(records),
            "resolved_with_title_match": sum(1 for r in records if r["verdict"] == "match"),
            "failed_or_unverified": sum(1 for r in records if r["verdict"] != "match"),
            "locator_attempts": sum(len(r["locators_tried"]) for r in records),
            "http_200_attempts": sum(
                1 for r in records for t in r["locators_tried"] if t["http_status"] == 200
            ),
            "primary_locator_403_or_error": sum(
                1 for r in records if r["locators_tried"][0]["http_status"] != 200
            ),
        },
        "records": records,
        "falsifier": (
            "F1: a re-fetch at any recorded locator returning a different status or a record whose "
            "title does not match the pinned L1 title voids that row; F2: any L0/L1 hash change voids "
            "the whole pass; F3: an ordered 1:1 reproduction of this file from fetch_l0_sample.py "
            "--pass N fails."
        ),
    }
    name = "fetch_evidence.json" if args.pass_no == 1 else "fetch_evidence_recheck.json"
    (OUT / name).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"pass {args.pass_no}: {out['counts']['resolved_with_title_match']}/{len(records)} rows "
          f"resolved with title match ({out['counts']['locator_attempts']} locator attempts), drift={drift}")
    return 3 if drift else (0 if out["counts"]["failed_or_unverified"] == 0 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
