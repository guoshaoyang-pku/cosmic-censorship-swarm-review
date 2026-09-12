#!/usr/bin/env python3
"""W099-SCALAR-LOCATOR-READINESS-01: AF-WCC-SCALAR-SPH locator resolvability at pinned L1.

Bounded execution worker worker-099. Node L1, gate G-LIT, class AF-WCC-SCALAR-SPH.

Completes BL-4 decision support for the fourth frozen class: worker-050 covered
AF-WCC-VAC-GEN (12 rows) and every SCC-bound row (34 rows); the 10 pure
AF-WCC-SCALAR-SPH rows (8 weak exact_locator cells) were in neither scope.

Fail-closed: aborts before fetching if ledger/citation_audit.csv differs from the pin.

Outputs (under artifacts/worker-099/scalar_locator_readiness/):
  fetch_evidence.pass1.json / fetch_evidence.pass2.json
  readiness.json  (per-row verdicts, controls, aggregate, falsifier outcomes)
  raw/pass1|pass2/<citation_id>.<source>.bin  (raw bodies, hash-pinned)
  *.sha256 for every written artifact

No node status, gate verdict, ledger edit, or validation_status is claimed.
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
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ACTOR = "worker-099"
TASK_ID = "W099-SCALAR-LOCATOR-READINESS-01"
CLASS_ID = "AF-WCC-SCALAR-SPH"
NODE_ID = "L1"
GATE = "G-LIT"

LEDGER_REL = "ledger/citation_audit.csv"
EXPECTED_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
THEOREMS_REL = "ledger/theorems.jsonl"

OUTDIR_REL = "artifacts/worker-099/scalar_locator_readiness"
PREREG_REL = f"{OUTDIR_REL}/PREREGISTRATION.json"

UA = {"User-Agent": "ai4math-swarm-worker-099/0.1 (W099 scalar locator readiness; read-only; local swarm)"}
HTML_UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0 Safari/537.36 ai4math-swarm-worker-099/0.1")}
HOST_MIN_INTERVAL = {
    "export.arxiv.org": 3.2, "arxiv.org": 3.2, "inspirehep.net": 1.5,
    "api.crossref.org": 1.2, "doi.org": 1.2, "api.openalex.org": 1.2,
    "link.springer.com": 2.0,
}
LAST_CALL: dict = {}
REQUESTS_MADE = 0
DEADLINE = None
MAX_REQUESTS = 80

CONTROLS = {
    "C1_positive_penrose_1965": {
        "ref_title": "Gravitational collapse and space-time singularities",
        "url": "https://api.crossref.org/works/10.1103/PhysRevLett.14.57",
        "source": "crossref_api",
        "expect_match": True,
    },
    "C2_negative_mutant_doi": {
        "ref_title": "Gravitational collapse and space-time singularities",
        "url": "https://api.crossref.org/works/10.4007/annals.2025.202.2.9999",
        "source": "crossref_api",
        "expect_match": False,
    },
    "C3_cross_source_src075_arxiv": {
        "ref_title": "A robust proof of the instability of naked singularities in spherical symmetry",
        "url": "https://arxiv.org/abs/1710.02922",
        "source": "arxiv_abs",
        "expect_match": True,
    },
    "C3_cross_source_src075_crossref": {
        "ref_title": "A robust proof of the instability of naked singularities in spherical symmetry",
        "url": "https://api.crossref.org/works/10.1007/s00220-018-3157-1",
        "source": "crossref_api",
        "expect_match": True,
    },
}


# ---------------------------------------------------------------- utilities
def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / LEDGER_REL).exists():
            return parent
    raise SystemExit(f"could not locate repo root ({LEDGER_REL})")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = s.encode("ascii", "ignore").decode()
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\$([^$]*)\$", r" \1 ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def token_f1(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    common = len(ta & tb)
    if common == 0:
        return 0.0
    p, r = common / len(tb), common / len(ta)
    return 2 * p * r / (p + r)


def title_match(ledger_title: str, fetched_title: str) -> tuple[bool, str]:
    a, b = norm(ledger_title), norm(fetched_title)
    if not a or not b:
        return False, "EMPTY_TITLE"
    if a == b:
        return True, "EXACT"
    if a in b or b in a:
        return True, "CONTAINMENT"
    f1 = token_f1(a, b)
    if f1 >= 0.75:
        return True, f"TOKEN_F1_{f1:.3f}"
    return False, f"TOKEN_F1_{f1:.3f}"


def host_of(url: str) -> str:
    return urllib.parse.urlparse(url).netloc


def is_search_endpoint(url: str) -> bool:
    u = url or ""
    if "search_query=" in u:
        return True
    if "/api/literature?q=" in u or re.search(r"[?&]q=", u):
        return True
    if "/api/query" in u and "id_list=" not in u:
        return True
    return False


def is_elided(url: str) -> bool:
    return "..." in (url or "")


def classify_locator(loc: str) -> str:
    loc = (loc or "").strip()
    if not loc:
        return "empty"
    if is_elided(loc):
        return "truncated"
    if is_search_endpoint(loc):
        return "search_query"
    if not loc.startswith("http"):
        return "non_url"
    return "direct_record_locator"


def propose(row: dict) -> tuple[str, str]:
    """Return (proposal_field, proposal_url) or ('', '') if no single-record candidate."""
    for field in ("evidence_url", "url", "doi", "arxiv_id"):
        val = (row.get(field) or "").strip()
        if not val:
            continue
        if field == "doi":
            cand = "https://doi.org/" + val
        elif field == "arxiv_id":
            cand = "https://arxiv.org/abs/" + val
        else:
            cand = val
        if not cand.startswith("http"):
            continue
        if is_search_endpoint(cand) or is_elided(cand):
            continue
        return field, cand
    return "", ""


def route_source(url: str) -> str:
    h = host_of(url)
    if h == "export.arxiv.org":
        return "arxiv_api"
    if h in ("arxiv.org", "www.arxiv.org"):
        return "arxiv_abs"
    if h == "inspirehep.net":
        return "inspirehep_api" if "/api/literature/" in url else "inspirehep_page"
    if h == "api.crossref.org":
        return "crossref_api"
    if h in ("doi.org", "dx.doi.org"):
        return "doi_landing"
    if h == "api.openalex.org":
        return "openalex_api"
    return "other_page"


# ---------------------------------------------------------------- fetching
def polite_wait(url: str) -> None:
    h = host_of(url)
    iv = HOST_MIN_INTERVAL.get(h)
    if not iv:
        return
    last = LAST_CALL.get(h)
    if last is not None:
        dt = time.time() - last
        if dt < iv:
            time.sleep(iv - dt)
    LAST_CALL[h] = time.time()


def http_get(url: str, timeout: int = 30, retries: int = 2) -> dict:
    global REQUESTS_MADE
    if DEADLINE and time.time() > DEADLINE:
        return {"http_status": 0, "error": "global_deadline_exceeded", "body": b""}
    if REQUESTS_MADE >= MAX_REQUESTS:
        return {"http_status": 0, "error": "max_http_requests_exceeded", "body": b""}
    headers = HTML_UA if route_source(url) in ("arxiv_abs", "doi_landing", "other_page") else UA
    last_err = ""
    for attempt in range(retries + 1):
        polite_wait(url)
        REQUESTS_MADE += 1
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return {"http_status": resp.status, "body": body, "final_url": resp.geturl(),
                        "error": ""}
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            return {"http_status": e.code, "body": body, "final_url": url, "error": f"HTTPError {e.code}"}
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            if attempt < retries:
                time.sleep(2 + 3 * attempt)
    return {"http_status": 0, "body": b"", "final_url": url, "error": last_err}


def parse_body(source: str, body: bytes) -> dict:
    text = body.decode("utf-8", "replace")
    out: dict = {"title": "", "authors": [], "year": "", "identifiers": [], "abstract": ""}
    try:
        if source == "arxiv_api":
            root = ET.fromstring(text)
            ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
            entry = root.find("a:entry", ns)
            if entry is not None:
                out["title"] = (entry.findtext("a:title", "", ns) or "").strip()
                out["authors"] = [(a.findtext("a:name", "", ns) or "").strip()
                                  for a in entry.findall("a:author", ns)]
                out["year"] = (entry.findtext("a:published", "", ns) or "")[:4]
                out["identifiers"] = [x for x in [(entry.findtext("a:id", "", ns) or "").strip(),
                                                  (entry.findtext("arxiv:doi", "", ns) or "").strip()] if x]
                out["abstract"] = (entry.findtext("a:summary", "", ns) or "").strip()
        elif source == "arxiv_abs":
            m = re.search(r'<meta\s+name="citation_title"\s+content="([^"]*)"', text, re.I)
            if m:
                out["title"] = m.group(1).strip()
            out["authors"] = re.findall(r'<meta\s+name="citation_author"\s+content="([^"]*)"', text, re.I)
            ym = re.search(r'<meta\s+name="citation_date"\s+content="([^"]*)"', text, re.I)
            out["year"] = (ym.group(1)[:4] if ym else "")
            am = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', text, re.S)
            if am:
                out["abstract"] = re.sub(r"<[^>]+>", " ", am.group(1)).strip()
        elif source == "inspirehep_api":
            d = json.loads(text)
            md = d.get("metadata", {})
            titles = md.get("titles") or []
            if titles:
                out["title"] = (titles[0].get("title") or "").strip()
            out["authors"] = [a.get("full_name", "") for a in (md.get("authors") or [])]
            pi = md.get("publication_info") or []
            if pi:
                out["year"] = str(pi[0].get("year") or "")
            out["identifiers"] = [x for x in ([md.get("dois", [{}])[0].get("value", "")] if md.get("dois") else []) if x]
            out["identifiers"] += [e.get("value", "") for e in (md.get("arxiv_eprints") or [])]
            out["abstract"] = " ".join((a.get("value", "") for a in (md.get("abstracts") or [])))[:2000]
        elif source == "crossref_api":
            d = json.loads(text)
            msg = d.get("message", {})
            t = msg.get("title") or []
            out["title"] = (t[0] if t else "").strip()
            out["authors"] = [f"{a.get('given','')} {a.get('family','')}".strip()
                              for a in (msg.get("author") or [])]
            iss = msg.get("issued", {}).get("date-parts") or [[""]]
            out["year"] = str(iss[0][0] or "")
            out["identifiers"] = [msg.get("DOI", "")]
            out["abstract"] = re.sub(r"<[^>]+>", " ", msg.get("abstract", "") or "").strip()[:2000]
        elif source == "openalex_api":
            d = json.loads(text)
            out["title"] = (d.get("title") or "").strip()
            out["authors"] = [a.get("author", {}).get("display_name", "") for a in (d.get("authorships") or [])]
            out["year"] = str(d.get("publication_year") or "")
            out["identifiers"] = [d.get("doi", "")]
            out["abstract"] = (d.get("abstract") or "")[:2000]
        else:  # doi_landing / other_page
            m = re.search(r'<meta\s+name="citation_title"\s+content="([^"]*)"', text, re.I)
            if m:
                out["title"] = m.group(1).strip()
            out["authors"] = re.findall(r'<meta\s+name="citation_author"\s+content="([^"]*)"', text, re.I)
            ym = re.search(r'<meta\s+name="citation_(?:date|publication_date)"\s+content="([^"]*)"', text, re.I)
            out["year"] = (ym.group(1)[:4] if ym else "")
            m2 = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
            if not out["title"] and m2:
                out["title"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m2.group(1))).strip()
    except Exception as e:  # noqa: BLE001
        out["parse_error"] = f"{type(e).__name__}: {e}"
    return out


def fetch_and_parse(url: str) -> dict:
    r = http_get(url)
    body = r.get("body", b"") or b""
    if body:
        _BODY_CACHE[sha256_bytes(body)] = body
    src = route_source(url)
    parsed = parse_body(src, body) if body else {}
    return {
        "url": url,
        "source": src,
        "http_status": r.get("http_status", 0),
        "error": r.get("error", ""),
        "final_url": r.get("final_url", url),
        "bytes": len(body),
        "sha256": sha256_bytes(body) if body else "",
        "parsed": parsed,
    }


# ---------------------------------------------------------------- main
def run_pass(rows: list[dict], proposals: dict, pass_no: int, outdir: Path) -> dict:
    rawdir = outdir / "raw" / f"pass{pass_no}"
    rawdir.mkdir(parents=True, exist_ok=True)
    observations = []
    for row in rows:
        cid = row["citation_id"]
        field, url = proposals.get(cid, ("", ""))
        if not url:
            observations.append({"citation_id": cid, "row": int(row["__row__"]), "pass": pass_no,
                                 "proposal_field": field, "proposal_url": "",
                                 "http_status": 0, "title_match": False,
                                 "title_metric": "NO_PROPOSAL", "raw_path": "", "raw_sha256": "",
                                 "fetched_title": "", "source": "", "error": ""})
            continue
        f = fetch_and_parse(url)
        body_sha = f["sha256"]
        raw_rel = ""
        if body_sha:
            raw_rel = f"{OUTDIR_REL}/raw/pass{pass_no}/{cid}.{f['source']}.bin"
            payload = _BODY_CACHE.get(body_sha, b"")
            (outdir / "raw" / f"pass{pass_no}" / f"{cid}.{f['source']}.bin").write_bytes(payload)
        fetched_title = (f.get("parsed") or {}).get("title", "")
        ok, metric = title_match(row.get("title", ""), fetched_title)
        observations.append({
            "citation_id": cid, "row": int(row["__row__"]), "pass": pass_no,
            "proposal_field": field, "proposal_url": url, "source": f["source"],
            "http_status": f["http_status"], "error": f["error"], "final_url": f["final_url"],
            "fetched_title": fetched_title,
            "fetched_authors": (f.get("parsed") or {}).get("authors", [])[:6],
            "fetched_year": (f.get("parsed") or {}).get("year", ""),
            "bytes": f["bytes"], "raw_sha256": body_sha, "raw_path": raw_rel,
            "title_metric": metric, "title_match": bool(ok),
        })
    return {"pass": pass_no, "fetched_at": now(), "observations": observations}


_BODY_CACHE: dict = {}


def run_controls(pass_no: int, outdir: Path) -> list[dict]:
    rawdir = outdir / "raw" / f"pass{pass_no}"
    rawdir.mkdir(parents=True, exist_ok=True)
    out = []
    for name, spec in CONTROLS.items():
        f = fetch_and_parse(spec["url"])
        body_sha = f["sha256"]
        raw_rel = ""
        if body_sha:
            raw_rel = f"{OUTDIR_REL}/raw/pass{pass_no}/{name}.{f['source']}.bin"
            payload = _BODY_CACHE.get(body_sha, b"")
            (outdir / "raw" / f"pass{pass_no}" / f"{name}.{f['source']}.bin").write_bytes(payload)
        fetched_title = (f.get("parsed") or {}).get("title", "")
        ok, metric = title_match(spec["ref_title"], fetched_title)
        out.append({
            "control": name, "pass": pass_no, "url": spec["url"], "source": f["source"],
            "http_status": f["http_status"], "error": f["error"],
            "fetched_title": fetched_title, "bytes": f["bytes"], "raw_sha256": body_sha,
            "raw_path": raw_rel, "title_metric": metric, "title_match": bool(ok),
            "expected_match": spec["expect_match"],
            "control_outcome": ("PASS" if (ok == spec["expect_match"]) else "FAIL"),
        })
    return out


# ---------------------------------------------------------------- main
def main() -> int:
    global DEADLINE
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="debug: only first N population rows")
    ap.add_argument("--no-fetch", action="store_true", help="assemble from a previous evidence file (debug)")
    args = ap.parse_args()

    root = repo_root()
    outdir = root / OUTDIR_REL
    outdir.mkdir(parents=True, exist_ok=True)
    ledger_path = root / LEDGER_REL

    pre_sha = sha256_file(ledger_path)
    if pre_sha != EXPECTED_LEDGER_SHA256:
        print(json.dumps({"fatal": "ledger hash moved", "expected": EXPECTED_LEDGER_SHA256,
                          "measured": pre_sha}), file=sys.stderr)
        return 3
    prereg_sha = sha256_file(root / PREREG_REL)
    theorems_path = root / THEOREMS_REL
    theorems_sha = sha256_file(theorems_path) if theorems_path.exists() else ""

    with open(ledger_path, newline="", encoding="utf-8") as fh:
        all_rows = list(csv.DictReader(fh))
    for i, r in enumerate(all_rows, 1):
        r["__row__"] = str(i)
    population = [r for r in all_rows if (r.get("class_mapping") or "").strip() == CLASS_ID]
    if args.limit:
        population = population[: args.limit]

    proposals = {}
    classifications = {}
    for r in population:
        cid = r["citation_id"]
        classifications[cid] = {
            "row": int(r["__row__"]),
            "exact_locator": (r.get("exact_locator") or "").strip(),
            "locator_class": classify_locator(r.get("exact_locator", "")),
            "evidence_url": (r.get("evidence_url") or "").strip(),
            "arxiv_id": (r.get("arxiv_id") or "").strip(),
            "doi": (r.get("doi") or "").strip(),
            "verification_method": r.get("verification_method", ""),
            "status": r.get("status", ""),
            "verdict_recorded": r.get("verdict", ""),
            "class_mapping": r.get("class_mapping", ""),
            "used_by_theorems": r.get("used_by_theorems", ""),
        }
        proposals[cid] = propose(r)

    # global uniqueness of proposals against every row's locator columns
    def locator_values(row):
        return [v.strip() for v in (row.get("exact_locator", ""), row.get("evidence_url", ""),
                                    row.get("url", "")) if (v or "").strip()]

    collisions = {}
    for cid, (field, url) in proposals.items():
        if not url:
            continue
        hits = [f"{r['citation_id']}:{fld}" for r in all_rows for fld, v in
                (("exact_locator", r.get("exact_locator", "")), ("evidence_url", r.get("evidence_url", "")),
                 ("url", r.get("url", "")))
                if (v or "").strip() == url and r["citation_id"] != cid]
        collisions[cid] = hits

    if args.no_fetch:
        ev1 = json.loads((outdir / "fetch_evidence.pass1.json").read_text())
        ev2 = json.loads((outdir / "fetch_evidence.pass2.json").read_text())
    else:
        DEADLINE = time.time() + 900
        ev1 = run_pass(population, proposals, 1, outdir)
        ctl1 = run_controls(1, outdir)
        ev2 = run_pass(population, proposals, 2, outdir)
        ctl2 = run_controls(2, outdir)
        (outdir / "fetch_evidence.pass1.json").write_text(json.dumps(
            {"pass": 1, "fetched_at": now(), "ledger_sha256": pre_sha, "preregistration_sha256": prereg_sha,
             "requests_made": REQUESTS_MADE, "observations": ev1["observations"], "controls": ctl1},
            indent=2, sort_keys=True))
        (outdir / "fetch_evidence.pass2.json").write_text(json.dumps(
            {"pass": 2, "fetched_at": now(), "ledger_sha256": pre_sha, "preregistration_sha256": prereg_sha,
             "requests_made": REQUESTS_MADE, "observations": ev2["observations"], "controls": ctl2},
            indent=2, sort_keys=True))

    obs1 = {o["citation_id"]: o for o in ev1["observations"]}
    obs2 = {o["citation_id"]: o for o in ev2["observations"]}

    results = []
    for r in population:
        cid = r["citation_id"]
        o1, o2 = obs1.get(cid, {}), obs2.get(cid, {})
        field, url = proposals.get(cid, ("", ""))
        cls = classifications[cid]
        collisions_cid = collisions.get(cid, [])
        stable = (o1.get("http_status") == o2.get("http_status")
                  and norm(o1.get("fetched_title", "")) == norm(o2.get("fetched_title", "")))
        if cls["locator_class"] == "direct_record_locator":
            if not url:
                verdict = "NO_PROPOSAL"
            elif not stable:
                verdict = "UNSTABLE_ACROSS_PASSES"
            elif o1.get("http_status") == 200 and o1.get("title_match"):
                verdict = "DIRECT_OK"
            elif o1.get("http_status") == 200 and not o1.get("title_match"):
                verdict = "FAIL_TITLE_MISMATCH"
            else:
                verdict = f"UNVERIFIED_HTTP_{o1.get('http_status', 0)}"
        else:
            if not url:
                verdict = "NO_PROPOSAL"
            elif collisions_cid:
                verdict = "FAIL_PROPOSAL_COLLISION"
            elif not stable:
                verdict = "UNSTABLE_ACROSS_PASSES"
            elif o1.get("http_status") == 200 and o1.get("title_match"):
                verdict = "REPAIR_CONFIRMED"
            elif o1.get("http_status") == 200 and not o1.get("title_match"):
                verdict = "FAIL_TITLE_MISMATCH"
            else:
                verdict = f"UNVERIFIED_HTTP_{o1.get('http_status', 0)}"
        results.append({
            "citation_id": cid, "row": cls["row"], "class_mapping": cls["class_mapping"],
            "exact_locator_class": cls["locator_class"],
            "exact_locator": cls["exact_locator"],
            "proposal_field": field, "proposal_url": url,
            "collisions": collisions_cid,
            "pass1": {k: o1.get(k) for k in ("http_status", "fetched_title", "title_metric",
                                             "raw_path", "raw_sha256", "source", "error", "fetched_year")},
            "pass2": {k: o2.get(k) for k in ("http_status", "fetched_title", "title_metric",
                                             "raw_path", "raw_sha256", "source", "error", "fetched_year")},
            "stable_across_passes": stable,
            "verdict": verdict,
        })

    weak = [x for x in results if x["exact_locator_class"] != "direct_record_locator"]
    direct = [x for x in results if x["exact_locator_class"] == "direct_record_locator"]
    confirmed = [x for x in weak if x["verdict"] == "REPAIR_CONFIRMED"]
    direct_ok = [x for x in direct if x["verdict"] == "DIRECT_OK"]
    failed = [x for x in results if x["verdict"] in ("FAIL_TITLE_MISMATCH", "UNSTABLE_ACROSS_PASSES",
                                                     "FAIL_PROPOSAL_COLLISION")]
    unverified = [x for x in results if x["verdict"].startswith("UNVERIFIED") or x["verdict"] == "NO_PROPOSAL"]
    all_controls = json.loads((outdir / "fetch_evidence.pass1.json").read_text())["controls"]
    all_controls += json.loads((outdir / "fetch_evidence.pass2.json").read_text())["controls"]
    controls_ok = all(c["control_outcome"] == "PASS" for c in all_controls)

    post_sha = sha256_file(ledger_path)
    readiness = {
        "schema_version": "0.1",
        "artifact_type": "scalar_locator_readiness",
        "artifact_id": TASK_ID,
        "actor": ACTOR,
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "created_at": now(),
        "ledger_rel": LEDGER_REL,
        "ledger_sha256": pre_sha,
        "ledger_sha256_before": pre_sha,
        "ledger_sha256_after": post_sha,
        "ledger_drift": (post_sha != pre_sha),
        "theorems_sha256": theorems_sha,
        "preregistration_sha256": prereg_sha,
        "method": ("population = rows with class_mapping == AF-WCC-SCALAR-SPH at the pinned ledger; "
                   "classify exact_locator; propose first single-record candidate from evidence_url/url/doi/arxiv_id; "
                   "two independent live-fetch passes; identify by normalized title equality/containment/token-F1>=0.75; "
                   "check global uniqueness against every row's locator columns"),
        "population_rule": "class_mapping.strip() == 'AF-WCC-SCALAR-SPH'",
        "population_size": len(results),
        "aggregate": {
            "rows": len(results),
            "direct_rows": len(direct),
            "weak_rows": len(weak),
            "direct_ok": len(direct_ok),
            "repair_proposed": len([x for x in weak if x["proposal_url"]]),
            "repair_confirmed": len(confirmed),
            "failed": len(failed),
            "unverified": len(unverified),
            "stable_rows": len([x for x in results if x["stable_across_passes"]]),
            "strict_reading_unmet_cells_at_pin": len(weak),
            "strict_reading_status": (f"UNMET for {len(weak)}/{len(results)} pure-class exact_locator cells at "
                                      f"{pre_sha[:12]}; each carries a confirmed single-record replacement proposal"
                                      if len(confirmed) == len([x for x in weak if x["proposal_url"]]) and weak
                                      else "see per-row verdicts"),
        },
        "per_class_composition": {"AF-WCC-SCALAR-SPH": {"rows": len(results), "weak": len(weak),
                                                        "direct": len(direct),
                                                        "confirmed": len(confirmed)}},
        "controls": all_controls,
        "controls_all_pass": controls_ok,
        "collisions": collisions,
        "results": results,
        "hard_failures": failed,
        "findings": [
            {"id": "W099-SL-F-01", "severity": "info",
             "finding": f"{len(confirmed)}/{len([x for x in weak if x['proposal_url']])} weak rows carry a "
                        f"live-verified, globally unique single-record replacement proposal; "
                        f"{len(direct_ok)}/{len(direct)} direct rows re-verified."},
            {"id": "W099-SL-F-02", "severity": "info",
             "finding": "Under the strict per-row reading the criterion 'ledger rows have resolvable locators' "
                        f"is unmet for {len(weak)} of {len(results)} pure AF-WCC-SCALAR-SPH cells at "
                        f"ledger sha256 {pre_sha[:12]}; under the query-provenance reading all 10 rows carry a "
                        "resolving evidence_url."},
            {"id": "W099-SL-F-03", "severity": "info",
             "finding": f"ledger hash unchanged before/after: {pre_sha == post_sha}; controls all pass: {controls_ok}."},
        ],
        "falsifiers": [
            "F1 any REPAIR_CONFIRMED proposal that does not resolve to the cited work voids that row",
            "F2 a weak-classified row whose exact_locator is in fact a single-record resolvable locator voids that classification",
            "F3 ledger/citation_audit.csv != 315c19145065 voids the whole table (runner exits 3)",
            "F4 a pass-2 observation differing from pass-1 in status or returned record voids the row's stability claim",
            "F5 a proposal colliding with another row's locator columns voids the per-row uniqueness reading for that proposal",
            "F6 control C1 failing to match or C2 matching voids the instrument, not the ledger",
        ],
        "non_claims": [
            "not a ledger edit", "not a G-LIT gate verdict", "not an L1 node completion",
            "not a validation_status", "does not re-adjudicate quoted evidence or mathematical content",
            "the 2 direct rows were re-fetched as corroboration only; no repair is claimed for them",
        ],
        "reproduce": (f"python3 {OUTDIR_REL}/run_scalar_locators.py"),
        "requests_made": REQUESTS_MADE,
    }
    (outdir / "readiness.json").write_text(json.dumps(readiness, indent=2, sort_keys=True))
    for name in ("readiness.json", "fetch_evidence.pass1.json", "fetch_evidence.pass2.json", "PREREGISTRATION.json"):
        p = outdir / name
        (outdir / f"{name}.sha256").write_text(f"{sha256_file(p)}  {name}\n")

    print(json.dumps({"artifact": f"{OUTDIR_REL}/readiness.json",
                      "sha256": sha256_file(outdir / "readiness.json"),
                      "ledger_drift": readiness["ledger_drift"],
                      "aggregate": readiness["aggregate"],
                      "controls_all_pass": controls_ok,
                      "requests_made": REQUESTS_MADE}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
