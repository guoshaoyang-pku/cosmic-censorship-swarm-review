#!/usr/bin/env python3
"""L1 independent re-fetch spot-check #5 (G-LIT) -- worker-062.

Class-bound task (AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN,
AF-WCC-SCALAR-SPH).  One bounded worker task per the swarm worker contract:
read handoff/map + comms, work one class-bound task, emit an artifact with a
measured sha256, a pre-registered falsifier and pre-registered controls,
checkpoint, exit.

Design rules honoured here (HANDOFF.md section 6 / PROTOCOL.md rules 3-5):
  * run the null first  -> controls C1/C2/C3 are computed before the verdict;
  * the sample frame is frozen (written to disk) BEFORE any fetch;
  * fail-closed if ledger/citation_audit.csv has drifted off the pinned hash;
  * the ledger's own verdict/status columns are never used as evidence;
  * this worker does not set gate verdicts or validation_status=passed.

Usage:  python3 run_spotcheck_062.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
HERE = Path(__file__).resolve().parent              # artifacts/worker-062/l1_spotcheck
RAW = HERE / "raw"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"

CST = timezone(timedelta(hours=8))
def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")

PINNED_LEDGER_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"

FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}

# Rows already re-fetched at (or reported against) the pinned hash by earlier
# checks on disk; excluded so this sample adds disjoint coverage.
#   worker-07  (hash-pinned check #3, frame rows 41-95)
#   worker-086 (hash-pinned check #4)
#   worker-047 / worker-076 / worker-049 / worker-077 (later checks on disk)
#   flash-10 rows 1-20, flash-11 rows 21-40 (earlier csv revisions, rows kept out anyway)
EXCLUDED = {
    # flash-10 rows 1-20, flash-11 rows 21-40
    *{f"SRC-{i:03d}" for i in range(1, 41)},
    # worker-07 check #3 (+ frame endpoints it re-read)
    "SRC-041", "SRC-049", "SRC-057", "SRC-065", "SRC-073", "SRC-080", "SRC-081", "SRC-089",
    # worker-086 check #4
    "SRC-001", "SRC-004", "SRC-009", "SRC-016", "SRC-017", "SRC-025", "SRC-033", "SRC-096", "SRC-097",
    # worker-047
    "SRC-043", "SRC-054", "SRC-061", "SRC-094",
    # worker-076
    "SRC-035", "SRC-040", "SRC-047", "SRC-056", "SRC-078",
    # worker-049
    "SRC-021", "SRC-029", "SRC-062", "SRC-084", "SRC-091",
    # worker-077 raw fetches
    "SRC-042",
}

# Pre-registered systematic rule: eligible = class-bound rows not in EXCLUDED,
# sorted by citation_id; take every 3rd starting at 1-based index 2 -> 6 rows.
SAMPLE_RULE = "eligible sorted by citation_id ascending; every 3rd starting at index 2 (1-based); first 6"
# Pre-registered targeted item: independent corroboration of a hard failure
# reported by worker-086 (SRC-025, declared MISMATCH on year).  Declared BEFORE
# any fetch; reported separately, never merged into the disjoint-sample verdict.
CORROBORATION = ["SRC-025"]

# Pre-registered comparison policy (frozen before fetch).
POLICY = {
    "title": "ledger-title parenthetical provenance annotations containing 'reconstruction'/'abstract' are stripped first; then normalised token Jaccard >= 0.85 -> pass; else MISMATCH",
    "first_author": "family name (last token) casefold equality -> pass; else MISMATCH",
    "year": "|ledger_year - fetch_published_year| <= 1 -> pass/partial (preprint-vs-journal convention); > 1 -> MISMATCH",
    "excerpt": "content-token coverage of ledger evidence_excerpt against fetched abstract: >= 0.60 pass, 0.30-0.60 partial, < 0.30 MISMATCH",
    "row_verdict": "any MISMATCH -> MISMATCH; else any PARTIAL -> PARTIAL; else MATCH",
    "locator": "exact_locator that is an API search query is recorded as a locator defect (falsifier-relevant); the fetch uses the row's arxiv_id / primary record id; primary endpoint export.arxiv.org API, declared fallback arxiv.org/abs/<id> HTML meta (the row's own evidence_url host) after repeated 429/5xx",
    "ledger_columns": "status/verdict/assessment columns are NOT used as evidence",
}

STOPWORDS = {
    "this", "that", "with", "from", "have", "which", "these", "those", "their", "there",
    "where", "when", "such", "into", "than", "then", "them", "they", "also", "more",
    "most", "some", "only", "over", "under", "between", "after", "before", "other",
    "results", "result", "using", "used", "shown", "show", "shows", "paper", "work",
    "here", "been", "were", "will", "would", "could", "should", "about", "however",
    "namely", "given", "case", "cases", "thus", "therefore", "moreover", "further",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_tokens(text: str) -> list[str]:
    text = re.sub(r"\$[^$]*\$", " ", text)
    text = re.sub(r"[^A-Za-z0-9 ]+", " ", text.lower())
    return [t for t in text.split() if t]


def ledger_title(text: str) -> str:
    """Strip provenance annotations such as '(OpenAlex abstract reconstruction)'."""
    return re.sub(r"\((?:[^()]*?(?:reconstruction|abstract)[^()]*?)\)", " ", text, flags=re.I)


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def content_tokens(text: str) -> set[str]:
    return {t for t in norm_tokens(text) if len(t) >= 4 and t not in STOPWORDS}


def strip_excerpt(excerpt: str) -> str:
    e = excerpt.strip()
    e = re.sub(r"^(arXiv abstract \(exact excerpt\)|arXiv abstract|Springer abstract|Reconstructed abstract \(OpenAlex inverted index\)|Abstract)\s*:\s*", "", e, flags=re.I)
    e = e.replace("...", " ").replace("[...]", " ")
    e = e.strip().strip("'\"").strip()
    return e


def fetch_arxiv(arxiv_id: str, dest: Path, tries: int = 3) -> dict:
    """GET the arXiv API record; retry with backoff on 429/5xx. Saves raw body."""
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
    delay = 5
    last = None
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "ai4math-swarm-worker-062/0.1 (spotcheck)"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read()
                status = r.status
            if status == 200 and body:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(body)
                return {"ok": True, "http_status": status, "attempts": attempt, "source": "arxiv-api",
                        "url": url, "raw_sha256": hashlib.sha256(body).hexdigest(),
                        "fetched_at": now()}
            last = f"http {status}"
        except urllib.error.HTTPError as e:
            last = f"http {e.code}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if attempt < tries:
            time.sleep(delay)
            delay = min(delay * 2, 30)
    return {"ok": False, "error": last, "url": url, "fetched_at": now()}


def fetch_abs_html(arxiv_id: str, dest: Path, tries: int = 3) -> dict:
    """Declared fallback: the row's own evidence_url (arxiv.org/abs) HTML meta."""
    url = f"https://arxiv.org/abs/{arxiv_id}"
    delay = 10
    last = None
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ai4math-swarm-worker-062)"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read()
                status = r.status
            if status == 200 and body:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(body)
                return {"ok": True, "http_status": status, "attempts": attempt, "source": "arxiv-abs-html",
                        "url": url, "raw_sha256": hashlib.sha256(body).hexdigest(),
                        "fetched_at": now()}
            last = f"http {status}"
        except urllib.error.HTTPError as e:
            last = f"http {e.code}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if attempt < tries:
            time.sleep(delay)
            delay = min(delay * 2, 30)
    return {"ok": False, "error": last, "url": url, "fetched_at": now()}


def parse_arxiv_abs_html(html_text: str) -> dict:
    def meta(name: str) -> list[str]:
        return [re.sub(r"\s+", " ", m).strip()
                for m in re.findall(rf'<meta name="{name}" content="([^"]*)"', html_text)]

    import html as _html

    title = meta("citation_title")
    authors = [a.split(",")[0].strip() for a in meta("citation_author")]
    date = meta("citation_date") or meta("citation_online_date")
    abs_meta = meta("citation_abstract")
    if abs_meta:
        summary = _html.unescape(abs_meta[0])
    else:
        m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', html_text, re.S)
        summary = _html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))) if m else ""
    summary = re.sub(r"^Abstract:\s*", "", re.sub(r"\s+", " ", summary)).strip()
    return {
        "title": _html.unescape(title[0]) if title else "",
        "authors": [_html.unescape(a) for a in authors],
        "published": (date[0][:10].replace("/", "-") if date else ""),
        "summary": summary,
        "doi": "",
    }


def parse_record(path: Path) -> dict:
    text = path.read_text(errors="replace")
    if path.suffix == ".html":
        return parse_arxiv_abs_html(text)
    if path.suffix == ".json":
        doc = json.loads(text)
        return parse_json_record(doc, path.name)
    return parse_arxiv(text)


def fetch_json(url: str, dest: Path, tries: int = 3) -> dict:
    delay = 5
    last = None
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "ai4math-swarm-worker-062/0.1 (spotcheck)",
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read()
                status = r.status
            if status == 200 and body:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(body)
                return {"ok": True, "http_status": status, "attempts": attempt, "source": "json-api",
                        "url": url, "raw_sha256": hashlib.sha256(body).hexdigest(), "fetched_at": now()}
            last = f"http {status}"
        except urllib.error.HTTPError as e:
            last = f"http {e.code}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if attempt < tries:
            time.sleep(delay)
            delay = min(delay * 2, 30)
    return {"ok": False, "error": last, "url": url, "fetched_at": now()}


def oa_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def parse_json_record(doc: dict, name: str) -> dict:
    if "openalex" in name:
        auth = doc.get("authorships") or []
        return {
            "title": doc.get("title") or doc.get("display_name") or "",
            "authors": [a.get("author", {}).get("display_name", "") for a in auth[:1]],
            "published": str(doc.get("publication_year") or ""),
            "summary": oa_abstract(doc.get("abstract_inverted_index")),
            "doi": doc.get("doi") or "",
        }
    if "crossref" in name:
        msg = doc.get("message", doc)
        auth = msg.get("author") or []
        parts = (msg.get("issued", {}).get("date-parts") or [[""]])[0]
        return {
            "title": (msg.get("title") or [""])[0],
            "authors": [f"{auth[0].get('given','')} {auth[0].get('family','')}".strip()] if auth else [],
            "published": str(parts[0]) if parts else "",
            "summary": re.sub(r"<[^>]+>", " ", msg.get("abstract", "") or ""),
            "doi": msg.get("DOI", ""),
        }
    meta = doc.get("metadata", doc)
    titles = meta.get("titles") or []
    authors = meta.get("authors") or []
    pinfo = meta.get("publication_info") or []
    abs_ = meta.get("abstracts") or []
    name0 = authors[0].get("full_name", "") if authors else ""
    if "," in name0:  # INSPIRE gives "Family, Given"
        fam, given = [p.strip() for p in name0.split(",", 1)]
        name0 = f"{given} {fam}".strip()
    year = ""
    if pinfo:
        year = str(pinfo[0].get("year") or (pinfo[0].get("earliest_date") or "")[:4])
    if not year:
        year = (meta.get("earliest_date") or "")[:4]
    if not year and meta.get("preprint_date"):
        year = meta["preprint_date"][:4]
    return {
        "title": titles[0].get("title", "") if titles else "",
        "authors": [name0],
        "published": year,
        "summary": (abs_[0].get("value", "") if abs_ else ""),
        "doi": (meta.get("dois") or [{}])[0].get("value", ""),
    }


def parse_arxiv(xml_text: str) -> dict:
    entry = re.search(r"<entry>(.*?)</entry>", xml_text, re.S)
    body = entry.group(1) if entry else xml_text

    def one(tag: str, scope: str = body):
        m = re.search(rf"<{tag}>(.*?)</{tag}>", scope, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

    return {
        "title": one("title"),
        "authors": [re.sub(r"\s+", " ", a).strip() for a in re.findall(r"<name>(.*?)</name>", body, re.S)],
        "published": one("published")[:10],
        "summary": one("summary"),
        "doi": one("doi"),
    }


def compare(ledger_row: dict, fetched: dict) -> dict:
    states: dict[str, str] = {}
    detail: dict[str, object] = {}

    lt, ft = norm_tokens(ledger_title(ledger_row["title"])), norm_tokens(fetched["title"])
    j = jaccard(lt, ft)
    states["title"] = "pass" if j >= 0.85 else "MISMATCH"
    detail["title_jaccard"] = round(j, 3)

    la = norm_tokens(str(ledger_row["authors"]).split(";")[0])   # first author only
    fa = norm_tokens(fetched["authors"][0]) if fetched["authors"] else []
    la_last = la[-1] if la else ""
    fa_last = fa[-1] if fa else ""
    states["first_author"] = "pass" if la_last and la_last == fa_last else "MISMATCH"
    detail["first_author_ledger"] = la_last
    detail["first_author_fetch"] = fa_last

    ly = re.sub(r"\D", "", ledger_row.get("year", ""))[:4]
    fy = (fetched.get("published") or "")[:4]
    if ly and fy:
        d = abs(int(ly) - int(fy))
        states["year"] = "pass" if d <= 1 else "MISMATCH"
        detail["year_delta"] = d
    else:
        states["year"] = "partial"
        detail["year_delta"] = None
    detail["ledger_year"], detail["fetch_year"] = ly, fy

    ex = content_tokens(strip_excerpt(ledger_row.get("evidence_excerpt", "")))
    ab = content_tokens(fetched.get("summary", ""))
    cov = len(ex & ab) / len(ex) if ex else 0.0
    states["excerpt"] = "pass" if cov >= 0.60 else ("partial" if cov >= 0.30 else "MISMATCH")
    detail["excerpt_coverage"] = round(cov, 3)
    detail["excerpt_tokens"] = len(ex)

    vals = list(states.values())
    row_verdict = "MISMATCH" if "MISMATCH" in vals else ("PARTIAL" if "partial" in vals else "MATCH")
    return {"states": states, "detail": detail, "verdict": row_verdict}


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    ledger_sha_before = sha256_file(LEDGER)
    if ledger_sha_before != PINNED_LEDGER_SHA:
        print(json.dumps({"abort": "ledger hash drifted; fail-closed", "measured": ledger_sha_before,
                          "pinned": PINNED_LEDGER_SHA}, indent=2))
        return 2

    rows = list(csv.DictReader(LEDGER.open()))
    by_id = {r["citation_id"]: r for r in rows}
    for i, r in enumerate(rows, start=1):
        r["_row"] = i

    eligible = [r for r in rows
                if any(c.strip() in FROZEN_CLASSES for c in r.get("class_mapping", "").split(";"))
                and r["citation_id"] not in EXCLUDED]
    eligible_sorted = sorted(eligible, key=lambda r: r["citation_id"])
    sample = eligible_sorted[1::3][:6]

    manifest = {
        "manifest_version": "1.0",
        "created_at": now(),
        "actor": "worker-062",
        "task": "independent L1 re-fetch spot-check #5 (G-LIT), class-bound to the four frozen classes",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": sorted(FROZEN_CLASSES),
        "target": {"path": "ledger/citation_audit.csv", "sha256": ledger_sha_before, "data_rows": len(rows)},
        "eligible_frame": {
            "definition": "class-bound rows (class_mapping contains one of the four frozen ids) minus rows already re-fetched at/reported against the pinned hash by earlier checks on disk (flash-10, flash-11, worker-07/086/047/076/049/077)",
            "count": len(eligible_sorted),
            "ids": [r["citation_id"] for r in eligible_sorted],
        },
        "sampling_rule": SAMPLE_RULE,
        "sample_ids": [r["citation_id"] for r in sample],
        "targeted_corroboration": {
            "ids": CORROBORATION,
            "reason": "worker-086 check #4 reported SRC-025 as a hard MISMATCH (year 2021 vs fetched 2020); this re-fetch independently confirms or refutes that finding. Reported separately from the disjoint sample.",
            "declared_before_fetch": True,
        },
        "comparison_policy": POLICY,
        "controls_preregistered": [
            "C1 positive: SRC-045 fetched record vs its own ledger row must yield MATCH",
            "C2 negative: SRC-045 fetched record with title mutated and year +7 must yield MISMATCH on title and year",
            "C3 negative: SRC-045 fetched record compared against the SRC-050 ledger row must yield a title MISMATCH",
        ],
        "falsifier": "Any sampled locator resolving to a different work, any ledger excerpt contradicted by the fetched abstract, any year delta > 1, or a control that fails to fire, turns this artifact's finding to revise; if the ledger is revised after this run the artifact binds only to the pinned sha256 above.",
        "independence_note": "Sample frame is disjoint from every row re-fetched at the pinned hash by checks already on disk; locators are re-fetched from the primary arXiv API; ledger verdict/status columns are not used as evidence.",
        "authority_note": "Worker evidence only. This artifact cannot set a gate verdict, status=done, or validation_status=passed.",
        "ledger_sha256_at_freeze": ledger_sha_before,
        "theorems_sha256_at_freeze": sha256_file(THEOREMS),
    }
    (HERE / "manifest_062.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[manifest] frozen frame={len(eligible_sorted)} sample={manifest['sample_ids']}")

    results, hard_failures, advisory = [], [], []
    order = [r["citation_id"] for r in sample] + [c for c in CORROBORATION if c not in
                                                 {r['citation_id'] for r in sample}]

    for k, cid in enumerate(order):
        r = by_id[cid]
        out = {
            "citation_id": cid,
            "row": r["_row"],
            "class_mapping": r["class_mapping"],
            "used_by_theorems": r.get("used_by_theorems", ""),
            "arxiv_id": r.get("arxiv_id", ""),
            "ledger_title": r["title"],
            "ledger_year": r["year"],
            "exact_locator_is_search_query": bool(re.search(r"[?&](search_query|q)=", r.get("exact_locator", ""))),
            "fetch": {},
            "comparison": {},
            "panel": "corroboration" if cid in CORROBORATION else "disjoint_sample",
        }
        if not r.get("arxiv_id"):
            loc = (r.get("evidence_url") or r.get("exact_locator") or "").strip()
            if "openalex.org" in loc:
                base, dest = f"{cid}_openalex", RAW / f"{cid}_openalex.json"
                url0 = loc if loc.startswith("http") else f"https://api.openalex.org/works/doi:{r.get('doi','')}"
                url = url0 + ("&" if "?" in url0 else "?") + "mailto=worker-062@invalid.example"
            elif "inspirehep.net" in loc:
                base, dest, url = f"{cid}_inspire", RAW / f"{cid}_inspire.json", loc
            elif "crossref.org" in loc:
                base, dest, url = f"{cid}_crossref", RAW / f"{cid}_crossref.json", loc
            else:
                out["comparison"] = {"verdict": "UNFETCHED", "reason": f"unsupported locator host: {loc[:70]}"}
                advisory.append(f"{cid}: unsupported locator host")
                results.append(out)
                continue
            if dest.exists() and dest.stat().st_size > 0:
                fres = {"ok": True, "source": "json-api", "resumed": True, "url": url,
                        "raw_sha256": sha256_file(dest), "fetched_at": now()}
            else:
                if k:
                    time.sleep(4)
                fres = fetch_json(url, dest)
            out["fetch"] = fres
            if not fres.get("ok") or not dest.exists():
                out["comparison"] = {"verdict": "UNFETCHED", "reason": fres.get("error", "no body")}
                advisory.append(f"{cid}: fetch failed ({fres.get('error')})")
                results.append(out)
                continue
            raw_path = dest
            parsed = parse_record(dest)
        else:
            base = f"{cid}_{r['arxiv_id'].replace('/', '_')}"
            api_dest, html_dest = RAW / f"{base}.xml", RAW / f"{base}.html"
            api_url = f"https://export.arxiv.org/api/query?id_list={r['arxiv_id']}&max_results=1"
            if api_dest.exists() and api_dest.stat().st_size > 0:
                fres = {"ok": True, "source": "arxiv-api", "resumed": True, "url": api_url,
                        "raw_sha256": sha256_file(api_dest), "fetched_at": now()}
            elif html_dest.exists() and html_dest.stat().st_size > 0:
                fres = {"ok": True, "source": "arxiv-abs-html", "resumed": True,
                        "url": f"https://arxiv.org/abs/{r['arxiv_id']}",
                        "raw_sha256": sha256_file(html_dest), "fetched_at": now()}
            else:
                if k:
                    time.sleep(4)  # arXiv API politeness between sequential requests
                fres = fetch_arxiv(r["arxiv_id"], api_dest)
                if not fres.get("ok"):
                    api_err = fres.get("error")
                    fres = fetch_abs_html(r["arxiv_id"], html_dest)
                    fres["declared_fallback_from"] = f"arxiv-api ({api_err})"
            out["fetch"] = fres
            raw_path = api_dest if api_dest.exists() and api_dest.stat().st_size > 0 else html_dest
            if not fres.get("ok") or not raw_path.exists():
                out["comparison"] = {"verdict": "UNFETCHED", "reason": fres.get("error", "no body")}
                advisory.append(f"{cid}: fetch failed ({fres.get('error')})")
                results.append(out)
                continue
        parsed = parse_record(raw_path)
        out["fetched"] = {k2: parsed[k2] for k2 in ("title", "authors", "published", "doi")}
        out["comparison"] = compare(r, parsed)
        if out["comparison"]["verdict"] == "MISMATCH":
            hard_failures.append({"citation_id": cid, "row": r["_row"],
                                  "detail": out["comparison"]["detail"],
                                  "states": out["comparison"]["states"]})
        results.append(out)

    # ---- pre-registered controls (run the null first) ----
    controls: dict[str, dict] = {}
    ctl_row = by_id["SRC-045"]
    ctl_fetch = next((x for x in results if x["citation_id"] == "SRC-045" and x["fetch"].get("ok")), None)
    if ctl_fetch:
        candidates = sorted(RAW.glob(f"SRC-045_{ctl_row['arxiv_id'].replace('/', '_')}.*"))
        parsed = parse_record(candidates[0])
        c1 = compare(ctl_row, parsed)
        controls["C1_positive_self"] = {"expected": "MATCH", "observed": c1["verdict"], "detail": c1["detail"]}
        mut = dict(parsed)
        mut["title"] = "Unrelated mutant control title about black hole interiors"
        y = (parsed.get("published") or "2025")[:4]
        mut["published"] = f"{int(y)+7}-01-01"
        c2 = compare(ctl_row, mut)
        controls["C2_negative_mutant"] = {"expected": "MISMATCH", "observed": c2["verdict"],
                                          "detail": c2["detail"], "states": c2["states"]}
        c3 = compare(by_id["SRC-050"], parsed)
        controls["C3_negative_crossrow"] = {"expected": "MISMATCH", "observed": c3["verdict"],
                                            "detail": c3["detail"], "states": c3["states"]}
    controls_ok = (
        controls.get("C1_positive_self", {}).get("observed") == "MATCH"
        and controls.get("C2_negative_mutant", {}).get("observed") == "MISMATCH"
        and controls.get("C3_negative_crossrow", {}).get("observed") == "MISMATCH"
    )

    sample_results = [r for r in results if r["panel"] == "disjoint_sample"]
    corrob_results = [r for r in results if r["panel"] == "corroboration"]
    unmatched = [r["citation_id"] for r in sample_results if r["comparison"].get("verdict") == "UNFETCHED"]
    mismatched = [r["citation_id"] for r in sample_results if r["comparison"].get("verdict") == "MISMATCH"]
    partial = [r["citation_id"] for r in sample_results if r["comparison"].get("verdict") == "PARTIAL"]

    locator_defects = [r["citation_id"] for r in sample_results if r["exact_locator_is_search_query"]]
    if locator_defects:
        advisory.append(
            "exact_locator is an API search query, not an exact locator, for sampled rows: "
            + ", ".join(locator_defects)
            + ". A search query is not independently citable and does not re-resolve to a unique record; "
              "recommendation to the L1 owner: replace exact_locator with the resolved record URL before the next freeze.")
    fallback_rows = [r["citation_id"] for r in sample_results if r["fetch"].get("source") == "arxiv-abs-html"]
    if fallback_rows:
        advisory.append(
            "export.arxiv.org API returned HTTP 429 (swarm-wide rate limiting) during this check; rows "
            + ", ".join(fallback_rows)
            + " were re-fetched from the row's own declared evidence_url host (arxiv.org/abs HTML meta), "
              "which is why they carry source=arxiv-abs-html.")

    if not controls_ok:
        verdict, verdict_reason = "inconclusive", "pre-registered control(s) failed; comparator not trusted"
    elif unmatched:
        verdict, verdict_reason = "inconclusive", f"fetch incomplete for {unmatched}"
    elif mismatched:
        verdict, verdict_reason = "revise", f"hard mismatch on {mismatched} at pinned hash"
    elif partial:
        verdict, verdict_reason = "match-with-partials", f"no mismatch; partials on {partial} (year convention)"
    else:
        verdict, verdict_reason = "match", "all sampled rows re-fetched and matched at the pinned hash"

    ledger_sha_after = sha256_file(LEDGER)
    report = {
        "schema_version": "0.1",
        "artifact_type": "l1_refetch_spotcheck",
        "actor": "worker-062",
        "reviewer": "worker-062",
        "role": "bounded execution worker",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": sorted(FROZEN_CLASSES),
        "created_at": now(),
        "check_number": 5,
        "revision_note": "Pass 1 of this check fetched only SRC-045: export.arxiv.org returned 429 (swarm-wide rate limiting) for the other five rows. Pass 2 (this artifact) reuses the pass-1 raw for SRC-045 and applies the pre-declared arxiv.org/abs HTML fallback for rows whose API fetch still fails. The sample frame and comparison policy are unchanged between passes; pass 1 produced no verdict.",
        "sample_frame_size": len(eligible_sorted),
        "target": manifest["target"],
        "sample_ids": manifest["sample_ids"],
        "corroboration_ids": CORROBORATION,
        "comparison_policy": POLICY,
        "controls_preregistered": manifest["controls_preregistered"],
        "results": results,
        "controls": controls,
        "controls_ok": controls_ok,
        "hard_failures": hard_failures,
        "advisory_findings": advisory,
        "summary": {
            "sample_checked": len(sample_results),
            "sample_match": len([r for r in sample_results if r["comparison"].get("verdict") == "MATCH"]),
            "sample_partial": len(partial),
            "sample_mismatch": len(mismatched),
            "unfetched": len(unmatched),
            "controls_ok": controls_ok,
            "locator_defect_rows": locator_defects,
            "html_fallback_rows": fallback_rows,
            "ledger_sha256_before": ledger_sha_before,
            "ledger_sha256_after": ledger_sha_after,
            "ledger_drifted_during_fetch": ledger_sha_after != ledger_sha_before,
            "theorems_sha256": manifest["theorems_sha256_at_freeze"],
        },
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "verdict_scope": "advisory worker evidence for node L1 / gate G-LIT; binds only to ledger/citation_audit.csv sha256 " + ledger_sha_before[:12],
        "authority_note": manifest["authority_note"],
        "falsifier": manifest["falsifier"],
        "next_falsifier": "Re-run at the same pinned csv sha256 and compare verdict sets; a single row whose re-fetched locator resolves to a different work falsifies the MATCH set and turns the spot-check verdict to revise.",
        "independence_note": manifest["independence_note"],
    }
    out_path = HERE / "spotcheck-l1-062.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    digest = sha256_file(out_path)
    (HERE / "spotcheck-l1-062.json.sha256").write_text(f"{digest}  spotcheck-l1-062.json\n")
    print(json.dumps({"verdict": verdict, "reason": verdict_reason,
                      "sha256": digest, "sample": manifest["sample_ids"],
                      "mismatches": mismatched, "partials": partial,
                      "controls_ok": controls_ok}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
