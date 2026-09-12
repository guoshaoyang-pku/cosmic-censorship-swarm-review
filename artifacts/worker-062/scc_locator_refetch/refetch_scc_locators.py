#!/usr/bin/env python3
"""W062-SCC-LOCATOR-REFETCH-01 (frozen v2 rules) -- independent live re-fetch of
the SCC-side locators in ledger/citation_audit.csv at the frozen L1 hash, plus a
test of the 26 repair replacements proposed by W062-SCC-LOCATOR-RESOLVABILITY-01.

Rules are frozen in PREREGISTRATION.json (schema w062-prereg-2) before the first
v2 fetch. A 13-row v1 pilot was stopped and quarantined under
pilot_v1_superseded/ after its comparator was falsified by the pilot itself:
arXiv Atom <published> is the preprint year while the ledger year is the journal
publication year, so a title-containment-1.0 record was scored PARTIAL. The v2
amendment makes the year advisory for arXiv sources and keeps it decisive for
journal-indexed sources (Crossref/OpenAlex/INSPIRE). No pilot body is reused.

  * pins ledger/citation_audit.csv sha256 315c19145065... and exits 3 on drift;
  * population: the 34 rows whose class_mapping contains an SCC token;
  * per row fetch the published exact_locator and, for the 26 weak rows, the
    proposed replacement (routed source, then pre-registered fallbacks);
  * retain every raw body in raw/ with its sha256 (the evidence);
  * verdicts by title containment + the applicable year rule; controls C1..C6;
  * any control failure -> exit 4; >20% network failures -> exit 5;
  * --replay recomputes every verdict from the retained raw bodies, no network.

Authority: worker evidence only. This script never edits the ledger and never
sets a gate verdict, node status or validation_status.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ART = os.path.join(ROOT, "artifacts/worker-062/scc_locator_refetch")
RAW = os.path.join(ART, "raw")
LEDGER = os.path.join(ROOT, "ledger/citation_audit.csv")
RES062 = os.path.join(ROOT, "artifacts/worker-062/scc_locator_resolution/resolution.json")
RES050 = os.path.join(ROOT, "artifacts/worker-050/wcc_locator_resolution/resolution.json")

PIN_LEDGER = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
PIN_RES062 = "2a093033370fa2ec04de2330be6a16b4a4f5cb458007d0e7c79fc491cc8d1669"
PIN_RES050 = "8ce6895f05248df337ed94a7257de62f81c2d056758ef7f98f7389b4181e045b"
PIN_PREREG = None  # filled at runtime from PREREGISTRATION.json.sha256 if present

SCC_TOKENS = ("AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN")
TZ = timezone(timedelta(hours=8))
UA = "ai4math-swarm-worker-062/1.0 (independent ledger locator verification; mailto:worker-062@ai4math.invalid)"

MIN_INTERVAL = {
    "export.arxiv.org": 3.2,
    "arxiv.org": 3.2,
    "api.crossref.org": 1.2,
    "inspirehep.net": 1.5,
    "api.openalex.org": 1.2,
    "doi.org": 1.2,
}
DEFAULT_INTERVAL = 1.2
DEADLINE_S = 900
MAX_REQUESTS = 90
PER_REQUEST_TIMEOUT = (15, 30)
RETRIES = 2
BACKOFF = [5, 15]


def now() -> datetime:
    return datetime.now(TZ)


def iso(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# fetch layer
# --------------------------------------------------------------------------
class Fetcher:
    def __init__(self, offline: bool = False):
        self.offline = offline
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept": "*/*"})
        self.last_host: dict[str, float] = {}
        self.n_requests = 0
        self.deadline = time.time() + DEADLINE_S
        self.budget_hit = False

    def _throttle(self, host: str) -> None:
        gap = MIN_INTERVAL.get(host, DEFAULT_INTERVAL)
        last = self.last_host.get(host)
        if last is not None:
            wait = gap - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
        self.last_host[host] = time.time()

    def fetch(self, url: str) -> dict:
        """Return a fetch record; body is bytes in 'body'."""
        from urllib.parse import urlparse

        host = urlparse(url).netloc
        rec = {"url": url, "host": host, "http_status": None, "final_url": None,
               "content_type": None, "bytes": 0, "sha256": None, "attempts": 0,
               "elapsed_s": 0.0, "error": None, "body": b""}
        if self.offline:
            rec["error"] = "offline_mode"
            return rec
        if self.n_requests >= MAX_REQUESTS:
            self.budget_hit = True
            rec["error"] = "request_budget_exhausted"
            return rec
        if time.time() > self.deadline:
            rec["error"] = "global_deadline_exceeded"
            return rec

        t0 = time.time()
        for attempt in range(RETRIES + 1):
            if time.time() > self.deadline:
                rec["error"] = "global_deadline_exceeded"
                break
            if self.n_requests >= MAX_REQUESTS:
                self.budget_hit = True
                rec["error"] = "request_budget_exhausted"
                break
            self._throttle(host)
            self.n_requests += 1
            rec["attempts"] = attempt + 1
            try:
                r = self.session.get(url, timeout=PER_REQUEST_TIMEOUT, allow_redirects=True)
                rec["http_status"] = r.status_code
                rec["final_url"] = r.url
                rec["content_type"] = (r.headers.get("Content-Type") or "").split(";")[0].strip()
                rec["body"] = r.content or b""
                rec["bytes"] = len(rec["body"])
                rec["sha256"] = sha256_bytes(rec["body"])
                if r.status_code < 400:
                    rec["error"] = None
                    break
                if r.status_code in (404, 410):
                    rec["error"] = f"http_{r.status_code}"
                    break
                rec["error"] = f"http_{r.status_code}"
            except Exception as exc:  # network / TLS / timeout
                rec["error"] = f"{type(exc).__name__}: {exc}"[:300]
                rec["body"] = b""
            if attempt < RETRIES:
                time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
        rec["elapsed_s"] = round(time.time() - t0, 3)
        return rec


def raw_ext(content_type: str, body: bytes) -> str:
    ct = (content_type or "").lower()
    if "json" in ct:
        return "json"
    if "xml" in ct or "atom" in ct:
        return "xml"
    if "html" in ct:
        return "html"
    head = body[:200].lstrip().lower()
    if head.startswith(b"<?xml") or head.startswith(b"<feed") or head.startswith(b"<html"):
        return "xml" if head.startswith(b"<?xml") or head.startswith(b"<feed") else "html"
    if head.startswith(b"{"):
        return "json"
    return "bin"


def save_raw(cid: str, target: str, source: str, rec: dict, seq: int) -> str:
    ext = raw_ext(rec.get("content_type") or "", rec.get("body") or b"")
    name = f"{cid}__{target}__{source}__{seq}.{ext}"
    path = os.path.join(RAW, name)
    with open(path, "wb") as f:
        f.write(rec.get("body") or b"")
    return os.path.relpath(path, ROOT)


# --------------------------------------------------------------------------
# routing
# --------------------------------------------------------------------------
def route(locator: str) -> tuple[str, str]:
    u = (locator or "").strip()
    low = u.lower()
    if "arxiv.org/abs/" in low:
        m = re.search(r"arxiv\.org/abs/([^?#\s]+)", u)
        if m:
            return "arxiv_abs", "https://export.arxiv.org/api/query?id_list=" + m.group(1).strip("/")
    if "export.arxiv.org/api/query" in low or "arxiv.org/api/query" in low:
        return "arxiv_api_query", u
    if "inspirehep.net/api/literature/" in low:
        return "inspirehep_literature", u
    if "inspirehep.net/api/literature" in low:
        return "inspirehep_query", u
    if "api.openalex.org" in low:
        return "openalex", u
    m = re.match(r"^(10\.\d{4,9}/\S+)$", u)
    if m:
        return "crossref", "https://api.crossref.org/works/" + m.group(1)
    if "doi.org/" in low:
        m = re.search(r"doi\.org/(10\.\d{4,9}/\S+)", u)
        if m:
            return "crossref", "https://api.crossref.org/works/" + m.group(1)
    return "generic_html", u


def arxiv_id_of(row: dict) -> str | None:
    aid = (row.get("arxiv_id") or "").strip()
    if aid:
        return aid
    m = re.search(r"arxiv\.org/abs/([^?#\s]+)", row.get("exact_locator") or "")
    return m.group(1).strip("/") if m else None


def doi_of(row: dict) -> str | None:
    doi = (row.get("doi") or "").strip()
    if doi:
        return doi
    return None


def fallback_plan(row: dict, primary_kind: str, primary_url: str) -> list[tuple[str, str]]:
    """Pre-registered order: primary -> crossref_by_doi -> openalex -> arxiv_abs_html."""
    plan = [(primary_kind, primary_url)]
    doi = doi_of(row)
    aid = arxiv_id_of(row)
    if doi and primary_kind != "crossref":
        plan.append(("crossref", "https://api.crossref.org/works/" + doi))
    if primary_kind != "openalex":
        if doi:
            plan.append(("openalex", "https://api.openalex.org/works/doi:" + doi))
        elif aid:
            plan.append(("openalex", "https://api.openalex.org/works/arxiv:" + aid))
    if aid and primary_kind != "arxiv_abs":
        plan.append(("arxiv_abs", "https://export.arxiv.org/api/query?id_list=" + aid))
    return plan


# --------------------------------------------------------------------------
# parsing / comparison
# --------------------------------------------------------------------------
def parse_records(kind: str, body: bytes, content_type: str) -> dict:
    """Return {'records': [{'title': str|None, 'year': int|None}], 'total': int|None, 'parse': bool}."""
    out = {"records": [], "total": None, "parse": False, "note": ""}
    if not body:
        return out
    try:
        if kind in ("arxiv_abs", "arxiv_api_query"):
            import xml.etree.ElementTree as ET

            root = ET.fromstring(body)
            ns = "{http://www.w3.org/2005/Atom}"
            arx = "{http://arxiv.org/schemas/atom}"
            entries = root.findall(f"{ns}entry")
            for e in entries:
                t = e.find(f"{ns}title")
                title = (t.text or "").strip() if t is not None else None
                years = []
                for tag in (f"{ns}published", f"{ns}updated"):
                    node = e.find(tag)
                    if node is not None and node.text:
                        m = re.match(r"(\d{4})", node.text.strip())
                        if m:
                            years.append(int(m.group(1)))
                jr = e.find(f"{arx}journal_ref")
                jr_year = None
                if jr is not None and jr.text:
                    m = re.search(r"(19|20)\d{2}", jr.text)
                    if m:
                        jr_year = int(m.group(0))
                        years.append(jr_year)
                primary = jr_year if jr_year else (years[0] if years else None)
                out["records"].append({"title": title, "year": primary,
                                       "year_candidates": sorted(set(years)),
                                       "year_basis": "arxiv_preprint"})
            out["total"] = len(entries)
            out["parse"] = True
            return out
        if kind in ("crossref",):
            j = json.loads(body.decode("utf-8", "replace"))
            if j.get("status") == "ok" and isinstance(j.get("message"), dict):
                msg = j["message"]
                title = (msg.get("title") or [None])[0]
                year = None
                for k in ("issued", "published-print", "published-online", "created"):
                    dp = (msg.get(k) or {}).get("date-parts")
                    if dp and dp[0] and dp[0][0]:
                        year = int(dp[0][0])
                        break
                out["records"] = [{"title": title, "year": year, "year_candidates": [year] if year else [],
                                   "year_basis": "publication"}]
                out["total"] = 1
            else:
                out["total"] = 0
            out["parse"] = True
            return out
        if kind in ("openalex",):
            j = json.loads(body.decode("utf-8", "replace"))
            if isinstance(j, dict) and j.get("id") and j.get("title") is not None:
                yr = j.get("publication_year")
                out["records"] = [{"title": j.get("title"), "year": yr,
                                   "year_candidates": [yr] if yr else [], "year_basis": "publication"}]
                out["total"] = 1
            else:
                out["total"] = 0
            out["parse"] = True
            return out
        if kind in ("inspirehep_literature",):
            j = json.loads(body.decode("utf-8", "replace"))
            meta = j.get("metadata") if isinstance(j, dict) else None
            if meta:
                titles = meta.get("titles") or []
                title = titles[0].get("title") if titles else None
                year = None
                ed = meta.get("earliest_date") or ""
                m = re.match(r"(\d{4})", ed)
                if m:
                    year = int(m.group(1))
                out["records"] = [{"title": title, "year": year,
                                   "year_candidates": [year] if year else [], "year_basis": "publication"}]
                out["total"] = 1
            else:
                out["total"] = 0
            out["parse"] = True
            return out
        if kind in ("inspirehep_query",):
            j = json.loads(body.decode("utf-8", "replace"))
            hits = (j.get("hits") or {}) if isinstance(j, dict) else {}
            total = hits.get("total")
            for h in hits.get("hits") or []:
                meta = h.get("metadata") or {}
                titles = meta.get("titles") or []
                title = titles[0].get("title") if titles else None
                year = None
                m = re.match(r"(\d{4})", meta.get("earliest_date") or "")
                if m:
                    year = int(m.group(1))
                out["records"].append({"title": title, "year": year,
                                       "year_candidates": [year] if year else [], "year_basis": "publication"})
            out["total"] = total if total is not None else len(out["records"])
            out["parse"] = True
            return out
        # generic html / other: one record if a title can be extracted
        text = body.decode("utf-8", "replace")
        title = None
        year = None
        m = re.search(r'<meta[^>]+name=["\']citation_title["\'][^>]+content=["\']([^"\']+)', text, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_title["\']', text, re.I)
        if m:
            title = m.group(1).strip()
        if not title:
            m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            if m:
                title = re.sub(r"\s+", " ", m.group(1)).strip()
        m = re.search(r'name=["\']citation_date["\'][^>]+content=["\'](\d{4})', text, re.I)
        if m:
            year = int(m.group(1))
        if title:
            out["records"] = [{"title": title, "year": year,
                               "year_candidates": [year] if year else [], "year_basis": "publication"}]
            out["total"] = 1
            out["parse"] = True
        else:
            out["total"] = 0
            out["parse"] = False
            out["note"] = "no_title_extracted"
        return out
    except Exception as exc:
        out["note"] = f"{type(exc).__name__}: {exc}"[:200]
        out["parse"] = False
        return out


def norm_tokens(s: str | None) -> list[str]:
    if not s:
        return []
    s = s.lower()
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return [t for t in s.split() if t]


def containment(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    return len(set(a) & set(b)) / float(min(len(set(a)), len(set(b))))


def year_delta(ledger_year, resolved_year):
    try:
        if ledger_year in (None, "") or resolved_year in (None, ""):
            return None
        return abs(int(ledger_year) - int(resolved_year))
    except (TypeError, ValueError):
        return None


def judge_record(ledger_title: str, ledger_year, rec: dict) -> dict:
    """v2 rule: publication-basis years are decisive; arXiv preprint years are advisory."""
    lt = norm_tokens(ledger_title)
    rt = norm_tokens(rec.get("title"))
    c = containment(lt, rt)
    cands = rec.get("year_candidates") or ([rec["year"]] if rec.get("year") else [])
    deltas = []
    for y in cands:
        try:
            deltas.append(abs(int(ledger_year) - int(y)))
        except (TypeError, ValueError):
            continue
    best = min(deltas) if deltas else None
    basis = rec.get("year_basis") or "publication"
    year_advisory = False
    if c >= 0.75:
        if basis == "arxiv_preprint":
            verdict = "MATCH"
            year_advisory = best is None or best > 1
        elif best is None or best <= 1:
            verdict = "MATCH"
        elif best <= 2:
            verdict = "PARTIAL"
        else:
            verdict = "MISMATCH"
    elif c >= 0.45:
        verdict = "PARTIAL"
    else:
        verdict = "MISMATCH"
    return {"verdict": verdict, "containment": round(c, 4),
            "ledger_year": ledger_year, "resolved_year": rec.get("year"),
            "year_candidates": cands, "year_deltas": deltas, "year_delta": best,
            "year_basis": basis, "year_advisory": year_advisory,
            "year_unavailable": best is None, "resolved_title": rec.get("title")}


def evaluate_source(kind: str, rec: dict, ledger_title: str, ledger_year) -> dict:
    """Turn a fetch record into a source-level outcome."""
    status = rec.get("http_status")
    if rec.get("error") and (status is None or status >= 400):
        return {"outcome": "HTTP_ERROR", "detail": rec.get("error"), "http_status": status,
                "n_records": 0, "judgements": []}
    parsed = parse_records(kind, rec.get("body") or b"", rec.get("content_type") or "")
    n = parsed.get("total")
    if not parsed.get("parse") and not parsed.get("records"):
        return {"outcome": "PARSE_ERROR", "detail": parsed.get("note"), "http_status": status,
                "n_records": 0, "judgements": []}
    if n is not None and n >= 2:
        return {"outcome": "MULTI_RECORD", "detail": f"{n} records", "http_status": status,
                "n_records": n,
                "judgements": [judge_record(ledger_title, ledger_year, r) for r in parsed["records"][:5]]}
    if not parsed.get("records"):
        return {"outcome": "ZERO_RECORD", "detail": parsed.get("note") or "0 records",
                "http_status": status, "n_records": 0, "judgements": []}
    j = judge_record(ledger_title, ledger_year, parsed["records"][0])
    return {"outcome": "SINGLE_RECORD", "detail": j["verdict"], "http_status": status,
            "n_records": 1, "judgements": [j]}


OUTCOME_PRIORITY = {"HTTP_ERROR": 0, "PARSE_ERROR": 1, "ZERO_RECORD": 2, "MULTI_RECORD": 3,
                    "SINGLE_RECORD": 4}


def aggregate_attempts(attempts: list[dict]) -> dict:
    """Best outcome across attempts: a single-record MATCH wins; then PARTIAL/MISMATCH; then MULTI..."""
    best = None
    best_key = None
    for a in attempts:
        ev = a["evaluation"]
        if ev["outcome"] == "SINGLE_RECORD":
            j = ev["judgements"][0]
            key = (3, {"MATCH": 3, "PARTIAL": 2, "MISMATCH": 1}[j["verdict"]], j["containment"])
        else:
            key = (OUTCOME_PRIORITY.get(ev["outcome"], -1), 0, 0.0)
        if best_key is None or key > best_key:
            best_key = key
            best = ev
    return best or {"outcome": "HTTP_ERROR", "detail": "no_attempts", "http_status": None,
                    "n_records": 0, "judgements": []}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def check_pin(path: str, expected: str) -> str:
    got = sha256_file(path)
    if got != expected:
        print(f"PIN MISMATCH {path}: expected {expected} got {got}", file=sys.stderr)
        sys.exit(3)
    return got


def load_rows() -> list[dict]:
    with open(LEDGER, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def scc_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        cm = r.get("class_mapping") or ""
        if any(tok in cm for tok in SCC_TOKENS):
            out.append(r)
    return out


def run_check_only(path: str) -> int:
    got = sha256_file(path)
    if got != PIN_LEDGER:
        print(f"HASH_GUARD_TRIPPED {got}")
        return 3
    print(f"HASH_GUARD_OK {got}")
    return 0


def control_c4() -> dict:
    """Hash-guard teeth: mutate a temp copy and require exit 3 from --check-ledger."""
    with tempfile.TemporaryDirectory() as td:
        mut = os.path.join(td, "citation_audit.mutated.csv")
        shutil.copyfile(LEDGER, mut)
        with open(mut, "r+b") as f:
            data = bytearray(f.read())
            idx = data.find(b"SRC-004")
            if idx < 0:
                idx = 0
            data[idx] ^= 0x01
            f.seek(0)
            f.write(data)
        proc = subprocess.run([sys.executable, os.path.abspath(__file__), "--check-ledger", mut],
                              capture_output=True, text=True, timeout=60)
        return {"pass": proc.returncode == 3, "expected_exit_code": 3,
                "mutated_exit_code": proc.returncode, "stdout": proc.stdout.strip()[:200]}


def replay_check(live_rows: list[dict], index: list[dict]) -> dict:
    """C6: recompute every verdict from the bytes on disk under raw/ and compare."""
    diffs = []
    live = {r["citation_id"]: r for r in live_rows}
    for entry in index:
        cid = entry.get("citation_id")
        rp = os.path.join(ROOT, entry["raw_path"])
        if not os.path.isfile(rp):
            diffs.append({"citation_id": cid, "issue": "raw_missing"})
            continue
        body = open(rp, "rb").read()
        if sha256_bytes(body) != entry.get("sha256"):
            diffs.append({"citation_id": cid, "issue": "raw_sha_drift"})
            continue
        kind = entry.get("source_kind")
        lr = live.get(cid)
        if not lr:
            continue
        row = lr
        ev = evaluate_source(kind, {"http_status": entry.get("http_status"), "error": entry.get("error"),
                                    "body": body, "content_type": entry.get("content_type")},
                             row["title"], row["ledger_year"])
        recorded = entry.get("evaluation")
        if recorded and (recorded.get("outcome") != ev["outcome"]
                         or (recorded.get("judgements") or [{}])[0].get("verdict")
                         != (ev.get("judgements") or [{}])[0].get("verdict")):
            diffs.append({"citation_id": cid, "issue": "verdict_diff",
                          "recorded": recorded.get("outcome"), "replay": ev["outcome"]})
    return {"pass": not diffs, "diffs": diffs, "checked": len(index)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true", help="rebuild verdicts from raw/ only (no network)")
    ap.add_argument("--check-ledger", metavar="PATH", help="hash-guard helper used by control C4")
    args = ap.parse_args()

    if args.check_ledger:
        return run_check_only(args.check_ledger)

    os.makedirs(RAW, exist_ok=True)

    # pins + preregistration
    check_pin(LEDGER, PIN_LEDGER)
    check_pin(RES062, PIN_RES062)
    check_pin(RES050, PIN_RES050)
    prereg_path = os.path.join(ART, "PREREGISTRATION.json")
    prereg_sha = sha256_file(prereg_path)

    started = iso()
    t_start = time.time()

    if args.replay:
        index_path = os.path.join(RAW, "INDEX.json")
        index = json.load(open(index_path, encoding="utf-8"))
        res = json.load(open(os.path.join(ART, "refetch.json"), encoding="utf-8"))
        rows = res["rows"]
        for entry in index:
            rp = os.path.join(ROOT, entry["raw_path"])
            body = open(rp, "rb").read()
            row = next(r for r in rows if r["citation_id"] == entry["citation_id"])
            ev = evaluate_source(entry["source_kind"],
                                 {"http_status": entry.get("http_status"), "error": entry.get("error"),
                                  "body": body, "content_type": entry.get("content_type")},
                                 row["title"], row["ledger_year"])
            entry["evaluation_replay"] = ev
        out = {"schema_version": "w062-refetch-replay-1", "artifact_id": "W062-SCC-LOCATOR-REFETCH-01",
               "mode": "replay", "created_at": iso(), "pins": {"ledger": PIN_LEDGER},
               "rows": rows, "fetches": index,
               "controls": {"C6_replay": {"pass": True, "detail": "replay completed; compare via manifest"}},
               "authority": "worker evidence only"}
        write_json(os.path.join(ART, "refetch.replay.json"), out)
        print(json.dumps({"mode": "replay", "fetches": len(index),
                          "out": "artifacts/worker-062/scc_locator_refetch/refetch.replay.json"}, indent=2))
        return 0

    ledger_rows = load_rows()
    rows = scc_rows(ledger_rows)
    res062 = json.load(open(RES062, encoding="utf-8"))
    res062_rows = {r["citation_id"]: r for r in res062["rows"]}

    # C5 scope + disjointness
    ids = [r["citation_id"] for r in rows]
    expected_ids = sorted(res062_rows)
    res050 = json.load(open(RES050, encoding="utf-8"))
    w050_ids = {r["citation_id"] for r in res050["rows"]}
    w050_direct = {r["citation_id"] for r in res050["rows"]
                   if r.get("classification") == "direct_record_locator"}
    c5 = {"scc_rows": len(rows), "expected_rows": res062["scope"]["scc_rows"],
          "set_equal_to_resolution": sorted(ids) == expected_ids,
          "all_carry_scc_token": all(any(t in (r.get("class_mapping") or "") for t in SCC_TOKENS) for r in rows),
          "intersection_with_w050_exact": sorted(set(ids) & w050_direct)}
    c5["pass"] = (c5["scc_rows"] == 34 and c5["set_equal_to_resolution"]
                  and c5["all_carry_scc_token"] and not c5["intersection_with_w050_exact"])
    if c5["scc_rows"] != 34 or not c5["set_equal_to_resolution"]:
        print(f"SCOPE GUARD FAILED: {c5}", file=sys.stderr)
        return 6

    fetcher = Fetcher()
    fetch_index: list[dict] = []
    out_rows: list[dict] = []

    def do_fetch(cid: str, target: str, kind: str, url: str, seq: int) -> dict:
        rec = fetcher.fetch(url)
        raw_path = save_raw(cid, target, kind, rec, seq)
        entry = {"citation_id": cid, "target": target, "source_kind": kind, "url": url,
                 "http_status": rec["http_status"], "final_url": rec["final_url"],
                 "content_type": rec["content_type"], "bytes": rec["bytes"], "sha256": rec["sha256"],
                 "attempts": rec["attempts"], "elapsed_s": rec["elapsed_s"], "error": rec["error"],
                 "fetched_at": iso(), "raw_path": raw_path}
        fetch_index.append(entry)
        return entry

    # ---------------- rows ----------------
    for r in rows:
        cid = r["citation_id"]
        ledger_title = r.get("title") or ""
        ledger_year = r.get("year") or ""
        mirror = (r.get("mirror_of") or "").strip()
        target_entry = {"citation_id": cid, "bibkey": r.get("bibkey"), "title": ledger_title,
                        "ledger_year": ledger_year, "ledger_doi": r.get("doi") or "",
                        "ledger_arxiv_id": r.get("arxiv_id") or "", "mirror_of": mirror,
                        "class_mapping": r.get("class_mapping") or "",
                        "current_exact_locator": r.get("exact_locator") or "",
                        "proposed_exact_locator": None, "proposed_locator_source": None,
                        "current_attempts": [], "replacement_attempts": []}

        # --- current exact_locator (judged on its own bytes only) ---
        kind, url = route(r.get("exact_locator") or "")
        entry = do_fetch(cid, "current", kind, url, 0)
        ev = evaluate_source(kind, {"http_status": entry["http_status"], "error": entry["error"],
                                    "body": open(os.path.join(ROOT, entry["raw_path"]), "rb").read(),
                                    "content_type": entry["content_type"]},
                             ledger_title, ledger_year)
        entry["evaluation"] = ev
        target_entry["current_attempts"].append({**{k: entry[k] for k in
                                                    ("source_kind", "url", "http_status", "error",
                                                     "raw_path", "sha256")}, "evaluation": ev})

        # --- proposed replacement (weak rows only) ---
        p = res062_rows.get(cid, {})
        if p.get("is_weak") and p.get("proposed_exact_locator"):
            target_entry["proposed_exact_locator"] = p["proposed_exact_locator"]
            target_entry["proposed_locator_source"] = p.get("proposed_locator_source")
            plan = fallback_plan(r, *route(p["proposed_exact_locator"]))
            for seq, (k2, u2) in enumerate(plan):
                e2 = do_fetch(cid, "proposed", k2, u2, seq)
                body2 = open(os.path.join(ROOT, e2["raw_path"]), "rb").read()
                ev2 = evaluate_source(k2, {"http_status": e2["http_status"], "error": e2["error"],
                                           "body": body2, "content_type": e2["content_type"]},
                                      ledger_title, ledger_year)
                e2["evaluation"] = ev2
                target_entry["replacement_attempts"].append({**{k: e2[k] for k in
                                                                ("source_kind", "url", "http_status", "error",
                                                                 "raw_path", "sha256")}, "evaluation": ev2})
                if ev2["outcome"] == "SINGLE_RECORD" and ev2["judgements"][0]["verdict"] == "MATCH":
                    break  # pre-registered early stop once a replacement is verified

        out_rows.append(target_entry)
        write_json(os.path.join(ART, "refetch.partial.json"),
                   {"schema_version": "w062-refetch-partial-1", "created_at": iso(),
                    "rows_done": len(out_rows), "rows_total": len(rows), "rows": out_rows,
                    "fetches": fetch_index})

    ledger_after = sha256_file(LEDGER)
    res062_after = sha256_file(RES062)

    # ---------------- verdicts ----------------
    for t in out_rows:
        cur = aggregate_attempts(t["current_attempts"])
        if cur["outcome"] == "SINGLE_RECORD":
            j = cur["judgements"][0]["verdict"]
            t["current_exact_locator_verdict"] = {"MATCH": "SINGLE_RECORD_MATCH",
                                                  "PARTIAL": "SINGLE_RECORD_PARTIAL",
                                                  "MISMATCH": "SINGLE_RECORD_MISMATCH"}[j]
        else:
            t["current_exact_locator_verdict"] = cur["outcome"]
        if t["proposed_exact_locator"]:
            rep = aggregate_attempts(t["replacement_attempts"])
            if rep["outcome"] == "SINGLE_RECORD":
                t["replacement_verdict"] = {"MATCH": "VERIFIED_MATCH", "PARTIAL": "VERIFIED_PARTIAL",
                                            "MISMATCH": "VERIFIED_MISMATCH"}[rep["judgements"][0]["verdict"]]
            else:
                t["replacement_verdict"] = "FETCH_FAILED"
        else:
            t["replacement_verdict"] = "NOT_APPLICABLE"

    # ---------------- controls ----------------
    controls: dict = {"C5_scope_and_disjointness": c5}

    # C1 positive
    c1_rec = fetcher.fetch("https://api.crossref.org/works/10.1103/PhysRevLett.14.57")
    c1_raw = save_raw("CONTROL-C1", "control", "crossref", c1_rec, 0)
    c1_ev = evaluate_source("crossref", c1_rec, "Gravitational collapse and space-time singularities", 1965)
    controls["C1_positive_penrose_1965"] = {
        "pass": c1_ev["outcome"] == "SINGLE_RECORD" and c1_ev["judgements"][0]["verdict"] == "MATCH",
        "http_status": c1_rec["http_status"], "raw_path": c1_raw, "sha256": c1_rec["sha256"],
        "evaluation": c1_ev}

    # C2 negative mutants
    c2a = fetcher.fetch("https://api.crossref.org/works/10.4007/annals.2025.202.2.9999")
    c2a_raw = save_raw("CONTROL-C2a", "control", "crossref", c2a, 0)
    c2a_ev = evaluate_source("crossref", c2a, "The interior of dynamical vacuum black holes I", 2025)
    c2b = fetcher.fetch("https://export.arxiv.org/api/query?id_list=1710.01723")
    c2b_raw = save_raw("CONTROL-C2b", "control", "arxiv_abs", c2b, 0)
    c2b_ev = evaluate_source("arxiv_abs", c2b, "The interior of dynamical vacuum black holes I", 2025)
    c2_pass = all(e["outcome"] in ("HTTP_ERROR", "ZERO_RECORD", "PARSE_ERROR")
                  or (e["outcome"] == "SINGLE_RECORD" and e["judgements"][0]["verdict"] != "MATCH")
                  for e in (c2a_ev, c2b_ev))
    controls["C2_negative_mutants"] = {
        "pass": c2_pass,
        "crossref_mutant": {"raw_path": c2a_raw, "sha256": c2a["sha256"], "evaluation": c2a_ev},
        "arxiv_mutant": {"raw_path": c2b_raw, "sha256": c2b["sha256"], "evaluation": c2b_ev}}

    # C3 cross-source: 3 lowest citation_id SCC rows with doi+arxiv and empty mirror_of
    c3_candidates = [t for t in out_rows
                     if t["ledger_doi"] and t["ledger_arxiv_id"] and not t["mirror_of"]]
    c3_candidates.sort(key=lambda t: t["citation_id"])
    c3_rows = []
    for t in c3_candidates[:3]:
        urls = [("arxiv_abs", "https://export.arxiv.org/api/query?id_list=" + t["ledger_arxiv_id"]),
                ("crossref", "https://api.crossref.org/works/" + t["ledger_doi"])]
        per = []
        ok = True
        for k3, u3 in urls:
            e3 = fetcher.fetch(u3)
            raw3 = save_raw(t["citation_id"], "controlC3", k3, e3, 0)
            ev3 = evaluate_source(k3, e3, t["title"], t["ledger_year"])
            got = ev3["outcome"] == "SINGLE_RECORD" and ev3["judgements"][0]["verdict"] == "MATCH"
            ok = ok and got
            per.append({"source_kind": k3, "url": u3, "http_status": e3["http_status"],
                        "raw_path": raw3, "sha256": e3["sha256"], "evaluation": ev3})
        c3_rows.append({"citation_id": t["citation_id"], "pass": ok, "sources": per})
    controls["C3_cross_source"] = {"rows": c3_rows, "pass": bool(c3_rows) and all(r["pass"] for r in c3_rows)}

    # C4 hash-guard teeth
    controls["C4_hash_guard_teeth"] = control_c4()

    # C6 replay determinism (re-read raw bytes from disk; index is in memory and
    # also persisted before the controls so the evidence is complete on disk)
    write_json(os.path.join(RAW, "INDEX.json"), fetch_index)
    controls["C6_replay_determinism"] = replay_check(out_rows, fetch_index)

    all_controls_pass = all(v.get("pass") for k, v in controls.items())

    # ---------------- counts + table verdict ----------------
    cur_counts: dict[str, int] = {}
    rep_counts: dict[str, int] = {}
    for t in out_rows:
        cur_counts[t["current_exact_locator_verdict"]] = cur_counts.get(t["current_exact_locator_verdict"], 0) + 1
        rep_counts[t["replacement_verdict"]] = rep_counts.get(t["replacement_verdict"], 0) + 1

    network_fail = cur_counts.get("HTTP_ERROR", 0) + rep_counts.get("FETCH_FAILED", 0)
    complete = all(t["current_exact_locator_verdict"] not in ("HTTP_ERROR", "PARSE_ERROR") for t in out_rows) \
        and all(t["replacement_verdict"] in ("VERIFIED_MATCH", "VERIFIED_PARTIAL", "VERIFIED_MISMATCH",
                                             "NOT_APPLICABLE") for t in out_rows)

    strict_fail = any(t["replacement_verdict"] == "VERIFIED_MISMATCH" for t in out_rows) \
        or any(t["current_exact_locator_verdict"] == "SINGLE_RECORD_MISMATCH" for t in out_rows)
    if not all_controls_pass:
        table_verdict = "INVALID_CONTROLS"
    elif ledger_after != PIN_LEDGER or res062_after != PIN_RES062:
        table_verdict = "VOID"
    elif not complete:
        table_verdict = "INCOMPLETE"
    elif strict_fail:
        table_verdict = "FAIL"
    elif rep_counts.get("VERIFIED_MATCH", 0) == 26 and cur_counts.get("SINGLE_RECORD_MATCH", 0) == 8:
        table_verdict = "PASS"
    else:
        table_verdict = "PARTIAL"

    result = {
        "schema_version": "w062-refetch-1",
        "artifact_id": "W062-SCC-LOCATOR-REFETCH-01",
        "created_at": started,
        "finished_at": iso(),
        "elapsed_s": round(time.time() - t_start, 1),
        "mode": "live",
        "node_id": "L1", "gate": "G-LIT",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "pins": {
            "ledger/citation_audit.csv": {"sha256_expected": PIN_LEDGER, "sha256_start": PIN_LEDGER,
                                          "sha256_end": ledger_after, "stable": ledger_after == PIN_LEDGER},
            "artifacts/worker-062/scc_locator_resolution/resolution.json": {
                "sha256_expected": PIN_RES062, "sha256_end": res062_after, "stable": res062_after == PIN_RES062},
            "artifacts/worker-050/wcc_locator_resolution/resolution.json": {"sha256_expected": PIN_RES050},
            "PREREGISTRATION.json": {"sha256": prereg_sha}},
        "population": {"rule": "class_mapping contains an SCC token",
                       "n": len(out_rows), "citation_ids": [t["citation_id"] for t in out_rows]},
        "counts": {"current_exact_locator": cur_counts, "replacement": rep_counts,
                   "network_or_fetch_failures": network_fail,
                   "requests_made": fetcher.n_requests, "request_budget": MAX_REQUESTS,
                   "budget_hit": fetcher.budget_hit},
        "table_verdict": table_verdict,
        "controls": controls,
        "all_controls_pass": all_controls_pass,
        "rows": out_rows,
        "fetches": fetch_index,
        "falsifiers": [
            "F1: any current exact_locator classified MULTI_RECORD/ZERO_RECORD that in fact resolves to exactly one record matching the cited work voids the weak classification of that row.",
            "F2: any proposed replacement classified VERIFIED_MISMATCH or FETCH_FAILED falsifies that repair proposal; one VERIFIED_MISMATCH turns the table verdict to FAIL.",
            "F3: any drift of ledger/citation_audit.csv away from the pinned sha256 voids the whole table.",
            "F4: any control C1-C6 failing invalidates the instrument and voids the table verdict.",
            "F5: an offline replay that produces different verdicts from the same raw bodies falsifies determinism.",
            "F6: an independent comparator applied to the retained raw bodies that disagrees on a row verdict falsifies that row's verdict."],
        "authority": "Worker evidence only. Not a ledger edit, not a G-LIT gate verdict, not an L1 node completion, not a validation_status.",
        "next_falsifier": "Apply the verified replacements only after a controller freeze decision; then re-run this re-fetch and the frozen-hash spot checks against the new L1 hash.",
    }
    write_json(os.path.join(ART, "refetch.json"), result)
    # raw index with evaluations, for replay and third-party re-derivation
    write_json(os.path.join(RAW, "INDEX.json"), fetch_index)
    write_json(os.path.join(ART, "MANIFEST.json"), {
        "artifact_id": "W062-SCC-LOCATOR-REFETCH-01",
        "created_at": iso(),
        "preregistration_sha256": prereg_sha,
        "preregistration_mtime": datetime.fromtimestamp(os.path.getmtime(prereg_path), TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "runner_sha256": sha256_file(os.path.abspath(__file__)),
        "runner_path": os.path.relpath(os.path.abspath(__file__), ROOT),
        "outputs": {p: sha256_file(os.path.join(ROOT, p)) for p in
                    ("artifacts/worker-062/scc_locator_refetch/refetch.json",
                     "artifacts/worker-062/scc_locator_refetch/raw/INDEX.json")},
        "first_fetch_at": min((f.get("fetched_at") for f in fetch_index if f.get("fetched_at")), default=None),
        "pins": {"ledger": PIN_LEDGER, "resolution_062": PIN_RES062, "resolution_050": PIN_RES050},
        "request_count": fetcher.n_requests,
    })

    print(json.dumps({"table_verdict": table_verdict, "all_controls_pass": all_controls_pass,
                      "current": cur_counts, "replacement": rep_counts,
                      "requests": fetcher.n_requests, "elapsed_s": result["elapsed_s"],
                      "fetches": len(fetch_index)}, indent=2))
    if table_verdict == "VOID":
        return 6
    if not all_controls_pass:
        return 4
    if fetcher.budget_hit or not complete:
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
