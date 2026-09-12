#!/usr/bin/env python3
"""W070-L1-LOCATOR-LIVE-02: live re-resolution of the `arxiv-api-query` locator family.

Question: at pinned ledger/citation_audit.csv sha256 315c19145065..., for every row whose
`exact_locator` is an arXiv API query URL, does the URL *as recorded* re-resolve to the work
the row claims (its own `arxiv_id`) in the returned entry list, and at what rank?

Bounded, class-bound literature-scope check (node L1, gate G-LIT). Worker evidence only:
no gate verdict, no node status, no validation_status=passed, no mathematical claim.

Design (freeze-first):
  1. Pin ledger sha256; fail closed if it does not match at start.
  2. Independently classify all 97 locators (own classifier; predecessor census used only as
     an agreement control). Register the frame (all arxiv-api-query rows) to frame.json and hash
     it BEFORE any live fetch.
  3. Fetch each recorded locator once (>=3.1 s spacing per arXiv API policy), store raw bytes.
     Verdict per row is id-based and decidable:
       TOP_HIT_MATCH         target arxiv_id is entry rank 1 of the returned page
       HIT_IN_PAGE_NOT_TOP   target arxiv_id is in the page at rank >= 2
       NOT_IN_RETURNED_PAGE  target arxiv_id is absent from the returned page (incl. 0 entries)
       FETCH_FAILED / PARSE_ERROR
  4. Controls: offline parser fixture; live positive controls (recorded-title queries for two
     frame rows that must find their own id); live negative control (nonsense query must find
     nothing); idempotence re-fetch of SRC-005 (same verdict/hit count); predecessor-census
     classification agreement over all 97 rows; re-execution agreement on the predecessor's
     3 live rows (5,6,7). If the SRC-006 positive control (predecessor TOP_HIT_MATCH) fails,
     the run is INVALID (format-dominated).
  5. Re-hash the ledger at end. Any change -> status VOID_LEDGER_DRIFT, all verdicts voided.

Exit codes: 0 complete, 3 pin mismatch at start, 4 control failure (INVALID), 5 ledger drift at end.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts" / "worker-070" / "l1_locator_live02"
RAW = OUT / "raw"
LEDGER = ROOT / "ledger" / "citation_audit.csv"
PRED_CENSUS = ROOT / "artifacts" / "worker-070" / "l1_locator_resolvability" / "census.json"
PINNED = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
TASK_ID = "w070-l1-locator-live-02"
NODE_ID = "L1"
GATE = "G-LIT"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
UA = "ai4math-swarm-worker-070/1.0 (bounded literature-locator audit; local)"
CST = timezone(timedelta(hours=8))
NS = {"a": "http://www.w3.org/2005/Atom"}
SPACING_S = 3.1
FAMILIES = ["elided", "arxiv-api-query", "inspire-query", "arxiv-abs", "other-url", "empty", "not-a-url"]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_locator(url: str) -> str:
    """Independent classifier (precedence: empty, elided, then host/path families)."""
    u = (url or "").strip()
    if not u:
        return "empty"
    if "..." in u:
        return "elided"
    try:
        sp = urllib.parse.urlsplit(u)
    except ValueError:
        return "not-a-url"
    if sp.scheme not in ("http", "https"):
        return "not-a-url"
    host = (sp.hostname or "").lower()
    path = sp.path or ""
    if (host == "export.arxiv.org" or host.endswith(".export.arxiv.org")) and path.rstrip("/") == "/api/query":
        return "arxiv-api-query"
    if (host == "inspirehep.net" or host.endswith(".inspirehep.net")) and path.startswith("/api/literature"):
        return "inspire-query"
    if (host == "arxiv.org" or host.endswith(".arxiv.org")) and "/abs/" in path:
        return "arxiv-abs"
    return "other-url"


def id_nov(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", (arxiv_id or "").strip())


def parse_atom(xml_bytes: bytes):
    """Return (entries, total_results, error). entries preserve feed order (rank)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return [], None, f"parse_error: {e}"
    total = None
    for el in root.iter():
        if el.tag.endswith("}totalResults"):
            total = (el.text or "").strip()
    entries = []
    for e in root.findall("a:entry", NS):
        raw_id = (e.findtext("a:id", default="", namespaces=NS) or "").strip()
        title = " ".join((e.findtext("a:title", default="", namespaces=NS) or "").split())
        published = (e.findtext("a:published", default="", namespaces=NS) or "").strip()
        authors = [ (a.findtext("a:name", default="", namespaces=NS) or "").strip()
                    for a in e.findall("a:author", NS) ]
        m = re.search(r"abs/([^/?#]+)$", raw_id)
        short = m.group(1) if m else raw_id
        entries.append({
            "rank": len(entries),
            "arxiv_id": id_nov(short),
            "arxiv_id_versioned": short,
            "title": title,
            "published": published,
            "authors": authors[:8],
            "abs_url": raw_id,
        })
    return entries, total, None


def title_overlap(a: str, b: str) -> float:
    stop = {"the", "a", "an", "of", "and", "on", "in", "for", "to", "with", "at", "by", "from", "is", "are"}
    wa = {w for w in re.findall(r"[a-z0-9']+", a.lower()) if w not in stop}
    wb = {w for w in re.findall(r"[a-z0-9']+", b.lower()) if w not in stop}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def fetch(url: str):
    """One logical fetch with up to 2 attempts. Returns dict."""
    last = None
    for attempt in (1, 2):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/atom+xml,application/xml,*/*"})
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read()
                return {"http_status": resp.status, "bytes": len(body), "body": body,
                        "elapsed_s": round(time.time() - t0, 2), "attempt": attempt, "exception": None}
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
            if attempt == 1:
                time.sleep(5.0)
    return {"http_status": None, "bytes": 0, "body": b"", "elapsed_s": None, "attempt": 2, "exception": last}


def live_query(url: str) -> dict:
    f = fetch(url)
    out = {"url": url, "http_status": f["http_status"], "bytes": f["bytes"],
           "sha256": sha256_bytes(f["body"]) if f["body"] else None, "elapsed_s": f["elapsed_s"],
           "exception": f["exception"], "n_hits": None, "total_results": None, "entries": [],
           "parse_error": None, "body": f["body"]}
    if f["body"]:
        entries, total, err = parse_atom(f["body"])
        out["entries"] = entries
        out["n_hits"] = len(entries)
        out["total_results"] = total
        out["parse_error"] = err
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    runner_sha = sha256_file(Path(__file__))
    created = now()
    print(f"[{created}] runner sha256={runner_sha}")

    # 1. pin ledger
    ledger_start = sha256_file(LEDGER)
    print(f"ledger sha256 start={ledger_start}")
    if ledger_start != PINNED:
        report = {
            "schema_version": "0.1", "artifact_type": "l1_locator_live_resolution_report",
            "task_id": TASK_ID, "node_id": NODE_ID, "gate": GATE, "class_ids": CLASS_IDS,
            "actor": "worker-070", "created_at": created, "runner_sha256": runner_sha,
            "authority": "worker evidence only; no gate verdict, no node status, no validation_status=passed",
            "status": "VOID_LEDGER_DRIFT_BEFORE_START",
            "inputs": {"ledger/citation_audit.csv": {"sha256_pinned": PINNED, "sha256_start": ledger_start}},
            "falsifier": "n/a (run did not start)",
        }
        (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print("VOID: ledger hash != pin at start; no fetch performed.")
        return 3

    # 2. classify + frame (before any live fetch)
    rows = list(csv.DictReader(open(LEDGER, encoding="utf-8")))
    my_family = {}
    frame = []
    for i, r in enumerate(rows, start=1):
        fam = classify_locator(r["exact_locator"])
        my_family[r["citation_id"]] = fam
        if fam == "arxiv-api-query":
            frame.append({
                "row": i,
                "citation_id": r["citation_id"],
                "arxiv_id": id_nov(r["arxiv_id"]),
                "claimed_title": r["title"],
                "claimed_authors": r["authors"],
                "claimed_year": r["year"],
                "class_mapping": r["class_mapping"],
                "used_by_theorems": r["used_by_theorems"],
                "locator": r["exact_locator"],
                "locator_sha256": sha256_bytes(r["exact_locator"].encode("utf-8")),
            })
    frame_view = {"task_id": TASK_ID, "pinned_ledger_sha256": PINNED, "data_rows": len(rows),
                  "frame_rule": "rows whose exact_locator classifies as arxiv-api-query (host export.arxiv.org, path /api/query; '...' takes precedence -> elided)",
                  "frame_size": len(frame), "rows": frame}
    frame_bytes = (json.dumps(frame_view, indent=1, sort_keys=True) + "\n").encode("utf-8")
    (OUT / "frame.json").write_bytes(frame_bytes)
    frame_sha = sha256_bytes(frame_bytes)
    (OUT / "frame.sha256.txt").write_text(f"{frame_sha}  frame.json\nregistered_at={created}\nrunner_sha256={runner_sha}\n", encoding="utf-8")
    print(f"frame registered BEFORE fetch: {len(frame)} rows, sha256={frame_sha}")

    # predecessor census as read-only agreement control
    pred = json.loads(PRED_CENSUS.read_text(encoding="utf-8"))
    pred_family = {c["citation_id"]: c["locator_family"] for c in pred["census"]}
    pred_verdict = {c["citation_id"]: c.get("verdict") for c in pred["census"]}
    fam_agree = sum(1 for k in my_family if my_family[k] == pred_family.get(k))
    fam_disagree = sorted(k for k in my_family if my_family[k] != pred_family.get(k))
    print(f"classification agreement vs predecessor census: {fam_agree}/{len(my_family)} disagree={fam_disagree}")

    # offline parser control
    synth = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1111.11111v3</id><title>Alpha Control Title</title><published>2020-01-01T00:00:00Z</published><author><name>A One</name></author></entry><entry><id>http://arxiv.org/abs/2222.22222v1</id><title>Beta Control Title</title><published>2021-01-01T00:00:00Z</published><author><name>B Two</name></author></entry><entry><id>http://arxiv.org/abs/3333.33333</id><title>Gamma Control Title</title><published>2022-01-01T00:00:00Z</published><author><name>C Three</name></author></entry></feed>"""
    se, st, serr = parse_atom(synth)
    parser_control = {
        "name": "offline_atom_parser_rank_fixture",
        "pass": (serr is None and len(se) == 3 and se[0]["arxiv_id"] == "1111.11111" and se[1]["arxiv_id"] == "2222.22222"
                 and se[2]["arxiv_id"] == "3333.33333" and id_nov("1111.11111v3") == "1111.11111"),
        "detail": {"n_entries": len(se), "ids": [e["arxiv_id"] for e in se], "error": serr},
    }
    print("parser control:", parser_control["pass"])

    # 3. live loop
    results = []
    for idx, item in enumerate(frame):
        if idx > 0:
            time.sleep(SPACING_S)
        lv = live_query(item["locator"])
        if lv["body"]:
            (RAW / f"{item['citation_id']}.xml").write_bytes(lv["body"])
        verdict = None
        rank = None
        title_only_rank = None
        if lv["exception"] is not None:
            verdict = "FETCH_FAILED"
        elif lv["parse_error"] is not None:
            verdict = "PARSE_ERROR"
        else:
            ranks = [e["rank"] for e in lv["entries"] if e["arxiv_id"] == item["arxiv_id"]]
            rank = ranks[0] if ranks else None
            if rank == 0:
                verdict = "TOP_HIT_MATCH"
            elif rank is not None:
                verdict = "HIT_IN_PAGE_NOT_TOP"
            else:
                verdict = "NOT_IN_RETURNED_PAGE"
            t_ranks = [e["rank"] for e in lv["entries"] if title_overlap(item["claimed_title"], e["title"]) >= 0.75]
            title_only_rank = t_ranks[0] if t_ranks else None
        rec = {
            "row": item["row"], "citation_id": item["citation_id"], "arxiv_id": item["arxiv_id"],
            "class_mapping": item["class_mapping"], "locator": item["locator"],
            "locator_sha256": item["locator_sha256"],
            "http_status": lv["http_status"], "bytes": lv["bytes"], "response_sha256": lv["sha256"],
            "n_hits": lv["n_hits"], "total_results": lv["total_results"],
            "target_rank": rank, "title_only_match_rank": title_only_rank,
            "verdict": verdict, "exception": lv["exception"], "parse_error": lv["parse_error"],
            "top_hit_arxiv_id": lv["entries"][0]["arxiv_id"] if lv["entries"] else None,
            "top_hit_title": lv["entries"][0]["title"] if lv["entries"] else None,
            "entry_ids": [e["arxiv_id"] for e in lv["entries"]],
            "predecessor_verdict": pred_verdict.get(item["citation_id"]),
        }
        results.append(rec)
        print(f"  [{idx+1}/{len(frame)}] {item['citation_id']} rank={rank} hits={lv['n_hits']} -> {verdict}")

    # positive controls: recorded-title queries for two frame rows must find their own id
    pos_targets = [r for r in frame if r["citation_id"] in ("SRC-062", "SRC-078")]
    pos_controls = []
    for t in pos_targets:
        q = "https://export.arxiv.org/api/query?search_query=ti:%22" + urllib.parse.quote(t["claimed_title"]) + "%22&start=0&max_results=5"
        time.sleep(SPACING_S)
        lv = live_query(q)
        ok = any(e["arxiv_id"] == t["arxiv_id"] for e in lv["entries"]) if lv["parse_error"] is None and lv["exception"] is None else False
        pos_controls.append({"name": f"recorded_title_query_finds_{t['citation_id']}", "query": q,
                             "target_arxiv_id": t["arxiv_id"], "n_hits": lv["n_hits"],
                             "entry_ids": [e["arxiv_id"] for e in lv["entries"]],
                             "exception": lv["exception"], "parse_error": lv["parse_error"], "pass": ok})
        print(f"  positive control {t['citation_id']}: pass={ok} n_hits={lv['n_hits']}")

    # negative control
    time.sleep(SPACING_S)
    neg_q = 'https://export.arxiv.org/api/query?search_query=ti:%22zzqqxx+nonexistent+unicorn+title%22+AND+all:%22no+such+phrase+7f3a%22&start=0&max_results=5'
    neg_lv = live_query(neg_q)
    neg_pass = (neg_lv["exception"] is None and neg_lv["parse_error"] is None and neg_lv["n_hits"] == 0)
    neg_control = {"name": "live_negative_nonsense_query", "query": neg_q, "n_hits": neg_lv["n_hits"],
                   "total_results": neg_lv["total_results"], "pass": neg_pass,
                   "exception": neg_lv["exception"], "parse_error": neg_lv["parse_error"]}
    print(f"  negative control: pass={neg_pass} n_hits={neg_lv['n_hits']}")

    # idempotence control on SRC-005 (also predecessor re-execution rows 5,6,7)
    time.sleep(SPACING_S)
    idem_item = frame[0]
    idem_lv = live_query(idem_item["locator"])
    idem_ranks = [e["rank"] for e in idem_lv["entries"] if e["arxiv_id"] == idem_item["arxiv_id"]]
    idem_rank = idem_ranks[0] if idem_ranks else None
    if idem_lv["exception"] is not None:
        idem_verdict = "FETCH_FAILED"
    elif idem_lv["parse_error"] is not None:
        idem_verdict = "PARSE_ERROR"
    elif idem_rank == 0:
        idem_verdict = "TOP_HIT_MATCH"
    elif idem_rank is not None:
        idem_verdict = "HIT_IN_PAGE_NOT_TOP"
    else:
        idem_verdict = "NOT_IN_RETURNED_PAGE"
    first = results[0]
    idem_pass = (idem_verdict == first["verdict"] and idem_lv["n_hits"] == first["n_hits"]
                 and (idem_lv["entries"][0]["arxiv_id"] if idem_lv["entries"] else None) == first["top_hit_arxiv_id"])
    idem_control = {"name": "idempotence_refetch_SRC-005", "pass": idem_pass, "first_verdict": first["verdict"],
                    "refetch_verdict": idem_verdict, "first_n_hits": first["n_hits"], "refetch_n_hits": idem_lv["n_hits"],
                    "first_top_id": first["top_hit_arxiv_id"],
                    "refetch_top_id": idem_lv["entries"][0]["arxiv_id"] if idem_lv["entries"] else None}
    print(f"  idempotence control: pass={idem_pass}")

    # predecessor positive control must hold (SRC-006)
    src006 = next((r for r in results if r["citation_id"] == "SRC-006"), None)
    pred_pos_control = {"name": "predecessor_TOP_HIT_MATCH_row_SRC-006_still_top",
                        "pass": bool(src006 and src006["verdict"] == "TOP_HIT_MATCH"),
                        "observed": src006["verdict"] if src006 else None,
                        "predecessor_verdict": pred_verdict.get("SRC-006")}

    controls = {
        "parser_fixture": parser_control,
        "positive_live_recorded_title": pos_controls,
        "negative_live_nonsense": neg_control,
        "idempotence_refetch": idem_control,
        "predecessor_top_hit_row": pred_pos_control,
        "classification_agreement_vs_predecessor": {"agree": fam_agree, "rows": len(my_family),
                                                     "disagree_rows": fam_disagree,
                                                     "pass": fam_agree == len(my_family)},
    }
    all_controls_pass = all(c["pass"] for c in controls.values() if isinstance(c, dict) and "pass" in c) and all(
        c["pass"] for c in pos_controls)
    # predecessor top-hit control is a hard gate on corpus validity
    corpus_valid = all_controls_pass and pred_pos_control["pass"] and parser_control["pass"]

    # ledger end hash (fail closed)
    ledger_end = sha256_file(LEDGER)
    drift = ledger_end != ledger_start
    print(f"ledger sha256 end={ledger_end} drift={drift}")

    # 4. aggregates
    from collections import Counter, defaultdict
    verdict_counts = Counter(r["verdict"] for r in results)
    n = len(results)
    loc_groups = defaultdict(list)
    for it in frame:
        loc_groups[it["locator"]].append(it["citation_id"])
    dup_groups = {k: v for k, v in loc_groups.items() if len(v) > 1}
    per_class = defaultdict(lambda: {"rows": 0, "verdicts": Counter()})
    for r in results:
        for cls in [c.strip() for c in (r["class_mapping"] or "").split(";") if c.strip()]:
            per_class[cls]["rows"] += 1
            per_class[cls]["verdicts"][r["verdict"]] += 1
    top_hit_rows = [r["citation_id"] for r in results if r["verdict"] == "TOP_HIT_MATCH"]
    not_top_rows = [r["citation_id"] for r in results if r["verdict"] != "TOP_HIT_MATCH"]
    # predecessor verdict names differ from this run's; normalize before comparing (rev1 defect fix)
    pred_norm = {"QUERY_TOP_HIT_MATCH": "TOP_HIT_MATCH", "QUERY_HIT_MATCH_NOT_TOP": "HIT_IN_PAGE_NOT_TOP",
                 "QUERY_NO_MATCH": "NOT_IN_RETURNED_PAGE"}
    reexec = {}
    for cid in ("SRC-005", "SRC-006", "SRC-007"):
        mine = next((r for r in results if r["citation_id"] == cid), None)
        pv = pred_verdict.get(cid)
        reexec[cid] = {"predecessor": pv, "predecessor_normalized": pred_norm.get(pv, pv),
                       "this_run": mine["verdict"] if mine else None,
                       "agree": bool(mine and pred_norm.get(pv, pv) == mine["verdict"])}

    hard_failures = []
    if not corpus_valid:
        hard_failures.append({"kind": "control_failure", "severity": "critical",
                              "finding": "at least one control failed; corpus is format-dominated and INVALID"})
    if drift:
        hard_failures.append({"kind": "ledger_drift", "severity": "critical",
                              "finding": "ledger/citation_audit.csv sha256 changed during the run; all verdicts VOID"})
    hard_failures.append({
        "kind": "locator_not_work_specific",
        "severity": "major",
        "finding": f"{len(dup_groups)} distinct locator strings in the arxiv-api-query family are shared by "
                   f"{sum(len(v) for v in dup_groups.values())} rows (max sharing {max((len(v) for v in dup_groups.values()), default=0)}); "
                   "a shared query cannot top-resolve every row that cites it.",
        "groups": [{"locator": k, "n_rows": len(v), "rows": v} for k, v in
                   sorted(dup_groups.items(), key=lambda kv: -len(kv[1]))],
    })
    hard_failures.append({
        "kind": "locator_does_not_reresolve_as_recorded",
        "severity": "major",
        "finding": f"{len(not_top_rows)}/{n} arxiv-api-query rows do not re-resolve, as recorded, to the claimed work at "
                   f"rank 1 (of which {verdict_counts.get('NOT_IN_RETURNED_PAGE', 0)} return the target not at all in the page; "
                   f"{verdict_counts.get('FETCH_FAILED', 0)} fetch failures; {verdict_counts.get('HIT_IN_PAGE_NOT_TOP', 0)} present but not top).",
        "rows": not_top_rows,
    })

    report = {
        "schema_version": "0.1",
        "artifact_type": "l1_locator_live_resolution_report",
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "group_id": "literature",
        "class_ids": CLASS_IDS,
        "actor": "worker-070",
        "reviewer": "worker-070",
        "created_at": created,
        "finished_at": now(),
        "authority": "worker evidence only; no gate verdict, no node status, no validation_status=passed; "
                     "the literature lead owns ledger/citation_audit.csv and no ledger edit was made",
        "question": "At pinned ledger sha256, does each arxiv-api-query `exact_locator` re-resolve as recorded to the work its row claims?",
        "pins": {"ledger/citation_audit.csv": PINNED, "predecessor_census": sha256_file(PRED_CENSUS),
                 "frame.json": frame_sha, "runner": runner_sha},
        "inputs": {"ledger/citation_audit.csv": {"sha256_pinned": PINNED, "sha256_start": ledger_start,
                                                 "sha256_end": ledger_end, "drift": drift, "data_rows": len(rows)},
                   "predecessor_census": {"path": "artifacts/worker-070/l1_locator_resolvability/census.json",
                                          "sha256": sha256_file(PRED_CENSUS), "role": "read-only agreement control"}},
        "frame": {"path": "artifacts/worker-070/l1_locator_live02/frame.json", "sha256": frame_sha,
                  "registered_before_fetch": True, "size": n,
                  "rule": frame_view["frame_rule"]},
        "method": {
            "verdict_rule": {
                "TOP_HIT_MATCH": "claimed arxiv_id (version-stripped) equals entry rank 1 of the returned page",
                "HIT_IN_PAGE_NOT_TOP": "claimed arxiv_id present at rank >= 2",
                "NOT_IN_RETURNED_PAGE": "claimed arxiv_id absent from the returned page (including 0 entries)",
                "FETCH_FAILED": "no 2xx/parseable body after 2 attempts",
                "PARSE_ERROR": "body fetched but Atom parse failed",
            },
            "fetch_policy": f"as-recorded URL, one logical fetch per row, >= {SPACING_S}s spacing, UA={UA}, timeout 45s, 2 attempts",
            "title_secondary_rule": "content-word overlap >= 0.75 vs claimed title, recorded only as supporting rank",
            "fail_closed": "ledger sha256 must equal the pin at start and end; end drift voids the artifact",
        },
        "census": results,
        "aggregate": {
            "rows_in_family": n,
            "verdict_counts": dict(verdict_counts),
            "top_hit_count": len(top_hit_rows),
            "top_hit_rows": top_hit_rows,
            "as_recorded_reresolution_rate": round(len(top_hit_rows) / n, 4) if n else None,
            "distinct_locators": len(loc_groups),
            "duplicate_locator_groups": len(dup_groups),
            "rows_sharing_a_locator": sum(len(v) for v in dup_groups.values()),
            "max_rows_per_locator": max((len(v) for v in dup_groups.values()), default=1),
            "per_class": {k: {"rows": v["rows"], "verdicts": dict(v["verdicts"])} for k, v in per_class.items()},
            "reexecution_agreement_predecessor_live_rows": reexec,
        },
        "controls": controls,
        "corpus_valid": corpus_valid,
        "hard_failures": hard_failures,
        "status": ("VOID_LEDGER_DRIFT" if drift else ("COMPLETE_INVALID_CONTROL_FAILURE" if not corpus_valid else "COMPLETE")),
        "falsifier": "Re-run this instrument at the same pinned ledger hash. Falsified if any TOP_HIT_MATCH row re-runs as "
                     "non-top, or if a row reported NOT_IN_RETURNED_PAGE appears at rank 1 on re-fetch, or if any control "
                     "re-runs false. A ledger sha256 change away from the pin voids the run rather than falsifying it. "
                     "Findings about locator specificity are falsified by editing the locator column so each row carries a "
                     "work-specific locator (e.g. its own abs URL or id_list query) and re-running to TOP_HIT_MATCH on all rows.",
        "falsifier_outcome": {"controls_pass": all_controls_pass, "corpus_valid": corpus_valid,
                              "predecessor_top_hit_row_still_top": pred_pos_control["pass"],
                              "ledger_drift": drift},
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    report_sha = sha256_file(OUT / "report.json")
    print(f"wrote {OUT/'report.json'} sha256={report_sha}")
    print(f"status={report['status']} verdicts={dict(verdict_counts)} top_hit={top_hit_rows}")
    if drift:
        return 5
    if not corpus_valid:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
