#!/usr/bin/env python3
"""W070-L1-ANCHORS-01 runner.

Reads the pre-registered frame.json, verifies pins, applies the ledger-match rules to the
pinned L1 ledger, resolves the registered candidate primary locators live (Crossref / arXiv),
runs controls, and writes report.json + ANCHORS.md + run.log. No ledger/schema write.
"""
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
D = f"{ROOT}/artifacts/worker-070/l1_anchors01"
RAW = f"{D}/raw"
UA = "w070-anchors-census/1.0 (research verification; contact: swarm-local)"
SPACING = 1.2
NS = {"a": "http://www.w3.org/2005/Atom"}

log_lines = []


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    log_lines.append(line)


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").casefold()).strip()


def norm_arxiv(s):
    return re.sub(r"v\d+$", "", (s or "").strip().lower())


_last_fetch = [0.0]


def fetch(url, raw_name, accept=None):
    """One live GET, save raw bytes, return (status, bytes, sha, error)."""
    wait = SPACING - (time.time() - _last_fetch[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if accept:
        req.add_header("Accept", accept)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read()
            status = r.status
            err = None
    except urllib.error.HTTPError as e:
        body = e.read()
        status = e.code
        err = f"HTTPError {e.code}"
    except Exception as e:  # noqa: BLE001
        body = b""
        status = 0
        err = f"{type(e).__name__}: {e}"
    _last_fetch[0] = time.time()
    path = f"{RAW}/{raw_name}"
    with open(path, "wb") as f:
        f.write(body)
    return status, body, sha256_bytes(body), err


# ------------------------------------------------------------------ resolvers
def resolve_doi(doi, tag):
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    status, body, sha, err = fetch(url, f"crossref_{tag}.json")
    out = {"kind": "doi", "id": doi, "http_status": status, "raw_sha256": sha,
           "raw": f"raw/crossref_{tag}.json", "error": err}
    if status == 200:
        try:
            m = json.loads(body)["message"]
            out.update({
                "title": " ".join(m.get("title") or []),
                "authors": "; ".join(f"{a.get('given','')} {a.get('family','')}".strip()
                                     for a in (m.get("author") or [])),
                "year": ((m.get("issued", {}).get("date-parts") or [[None]])[0][0]),
                "venue": (m.get("container-title") or [""])[0],
                "resolved": True,
            })
        except Exception as e:  # noqa: BLE001
            out.update({"resolved": False, "parse_error": f"{type(e).__name__}: {e}"})
    else:
        out["resolved"] = False
    return out


def resolve_crossref_query(query, tag):
    url = ("https://api.crossref.org/works?rows=3&query.bibliographic="
           + urllib.parse.quote(query))
    status, body, sha, err = fetch(url, f"crossrefq_{tag}.json")
    out = {"kind": "crossref_query", "query": query, "http_status": status,
           "raw_sha256": sha, "raw": f"raw/crossrefq_{tag}.json", "error": err,
           "candidates": []}
    if status == 200:
        try:
            items = json.loads(body)["message"]["items"]
            for m in items:
                out["candidates"].append({
                    "title": " ".join(m.get("title") or []),
                    "authors": "; ".join(f"{a.get('given','')} {a.get('family','')}".strip()
                                         for a in (m.get("author") or [])),
                    "year": ((m.get("issued", {}).get("date-parts") or [[None]])[0][0]),
                    "venue": (m.get("container-title") or [""])[0],
                    "doi": m.get("DOI", ""),
                })
            out["resolved"] = bool(out["candidates"])
        except Exception as e:  # noqa: BLE001
            out.update({"resolved": False, "parse_error": f"{type(e).__name__}: {e}"})
    else:
        out["resolved"] = False
    return out


def parse_arxiv_xml(body):
    root = ET.fromstring(body)
    entries = []
    for e in root.findall("a:entry", NS):
        entries.append({
            "arxiv_id": (e.findtext("a:id", "", NS) or "").rsplit("/", 1)[-1],
            "title": " ".join((e.findtext("a:title", "", NS) or "").split()),
            "authors": "; ".join((a.findtext("a:name", "") or "")
                                 for a in e.findall("a:author", NS)),
            "published": (e.findtext("a:published", "", NS) or "")[:10],
        })
    return entries


def resolve_arxiv(aid, tag):
    url = ("https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(aid)
           + "&max_results=5")
    status, body, sha, err = fetch(url, f"arxiv_{tag}.xml")
    out = {"kind": "arxiv", "id": aid, "http_status": status, "raw_sha256": sha,
           "raw": f"raw/arxiv_{tag}.xml", "error": err, "entries": []}
    if status == 200 and body:
        try:
            out["entries"] = parse_arxiv_xml(body)
            out["resolved"] = bool(out["entries"])
        except Exception as e:  # noqa: BLE001
            out.update({"resolved": False, "parse_error": f"{type(e).__name__}: {e}"})
    else:
        out["resolved"] = False
    return out


def expectation_met(res, spec):
    """Check a resolution against the frame's expected title/author tokens."""
    if not res.get("resolved"):
        return False, "not resolved"
    titles, authors = [], []
    if res["kind"] == "crossref_query":
        for c in res.get("candidates", []):
            titles.append(norm(c.get("title"))); authors.append(norm(c.get("authors")))
    else:
        entries = res.get("entries")
        if entries is not None:  # arxiv
            for e in entries:
                titles.append(norm(e.get("title"))); authors.append(norm(e.get("authors")))
        else:  # crossref doi
            titles.append(norm(res.get("title"))); authors.append(norm(res.get("authors")))
    tok_ok = any(all(t in t for t in spec.get("expect_title_tokens", [])) for t in titles)
    au_ok = True
    if spec.get("expect_author_any"):
        au_ok = any(any(a in au for au in authors) for a in spec["expect_author_any"])
    if res["kind"] == "crossref_query":
        # a top-3 bibliographic hit must satisfy title tokens AND an expected author
        return (tok_ok and au_ok), f"title_tokens={tok_ok} author={au_ok} n_hits={len(titles)}"
    return tok_ok, f"title_tokens={tok_ok}"


# ------------------------------------------------------------------ main
def main():
    t0 = time.time()
    log("W070-L1-ANCHORS-01 start")
    frame_path = f"{D}/frame.json"
    frame_sha = sha256_file(frame_path)
    frame = json.load(open(frame_path))
    log(f"frame sha256 {frame_sha} (pre-registered; written before any fetch)")
    log(f"frame task {frame['task_id']} rows={len(frame['derived_rows'])}")

    pins_before = {rel: sha256_file(f"{ROOT}/{rel}") for rel in frame["pins"]}
    drift_before = {k: (v, frame["pins"][k]) for k, v in pins_before.items()
                    if v != frame["pins"][k]}
    log(f"pin recheck before fetch: drift={drift_before or 'none'}")

    # ---- L1 ledger load
    with open(f"{ROOT}/ledger/citation_audit.csv", newline="") as f:
        ledger = list(csv.DictReader(f))
    log(f"L1 ledger rows {len(ledger)}")
    for r in ledger:
        r["_title_n"] = norm(r.get("title"))
        r["_authors_n"] = norm(r.get("authors"))
        r["_doi_n"] = (r.get("doi") or "").strip().casefold()
        r["_arxiv_n"] = norm_arxiv(r.get("arxiv_id"))

    def row_matches(row, rule):
        for pred in rule.get("any_of", []):
            if "title_all" in pred and all(t in row["_title_n"] for t in pred["title_all"]):
                return True, f"title_all={pred['title_all']}"
            if "title_any" in pred and any(p in row["_title_n"] for p in pred["title_any"]):
                return True, f"title_any={pred['title_any']}"
            if "author_all" in pred and all(t in row["_authors_n"] for t in pred["author_all"]):
                return True, f"author_all={pred['author_all']}"
            if "doi_equal" in pred and row["_doi_n"] == pred["doi_equal"].casefold():
                return True, "doi_equal"
            if "arxiv_equal" in pred and row["_arxiv_n"] == norm_arxiv(pred["arxiv_equal"]):
                return True, "arxiv_equal"
        return False, None

    # map derived rows -> registry item ids positionally, per schema, in registry order
    schema_of_prefix = {"F1": "schemas/af_wcc_vacuum.yaml",
                        "F2a": "schemas/af_scc_c2_vacuum.yaml",
                        "F2b": "schemas/af_scc_c0_vacuum.yaml"}
    ordered_ids = {}
    for rid in frame["item_registry"]:
        prefix = rid.rsplit("-", 1)[0]
        ordered_ids.setdefault(schema_of_prefix[prefix], []).append(rid)
    rows_out = []
    pos = {}
    for r in frame["derived_rows"]:
        pos[r["schema"]] = pos.get(r["schema"], 0)
        rid = ordered_ids[r["schema"]][pos[r["schema"]]]
        pos[r["schema"]] += 1
        item = {"item_id": rid, **r}
        matches = []
        for lr in ledger:
            ok, why = row_matches(lr, frame["item_registry"][rid]["rule"])
            if ok:
                matches.append({"citation_id": lr["citation_id"],
                                "title": lr.get("title", ""), "doi": lr.get("doi", ""),
                                "arxiv_id": lr.get("arxiv_id", ""), "why": why,
                                "class_mapping": lr.get("class_mapping", ""),
                                "evidence_type": lr.get("evidence_type", ""),
                                "assessment": lr.get("assessment", "")})
        item["ledger_matches"] = matches
        item["ledger_row_exists"] = bool(matches)
        rows_out.append(item)

    # ---- controls
    log("controls: parser fixture / positive DOI / negative DOI / positive arXiv / idempotence")
    controls = {}
    fx = frame["controls"]["parser_fixture"]["fixture"]
    controls["parser_fixture"] = {
        "ok": all(t in norm(fx["title"]) for t in ["fixture", "cauchy", "problem"]),
        "detail": norm(fx["title"]),
    }
    cs = frame["controls"]["positive_doi"]
    c1 = resolve_doi(cs["id"], "ctl_pos_doi")
    ok1, why1 = expectation_met(c1, cs)
    controls["positive_doi"] = {"ok": ok1, "detail": f"{c1.get('title','')[:80]} | {why1}",
                                "raw_sha256": c1["raw_sha256"]}
    c2 = resolve_doi(frame["controls"]["negative_doi"]["id"], "ctl_neg_doi")
    controls["negative_doi"] = {"ok": (not c2.get("resolved")) and c2["http_status"] in (0, 404, 400, 403, 406),
                                "detail": f"http={c2['http_status']} resolved={c2.get('resolved')} err={c2.get('error')}",
                                "raw_sha256": c2["raw_sha256"]}
    c3 = resolve_arxiv(frame["controls"]["positive_arxiv"]["id"], "ctl_pos_arxiv")
    ok3, why3 = expectation_met(c3, frame["controls"]["positive_arxiv"])
    controls["positive_arxiv"] = {"ok": ok3, "detail": f"{c3['entries'][0]['title'][:80] if c3.get('entries') else c3.get('error')} | {why3}",
                                  "raw_sha256": c3["raw_sha256"]}
    c4 = resolve_doi(cs["id"], "ctl_idem_doi")
    idem = (norm(c4.get("title")) == norm(c1.get("title"))
            and c4["raw_sha256"] == c1["raw_sha256"])
    controls["idempotence_doi"] = {"ok": idem,
                                   "detail": f"same_sha={c4['raw_sha256']==c1['raw_sha256']}",
                                   "raw_sha256": c4["raw_sha256"]}
    log(f"controls: {json.dumps({k: v['ok'] for k, v in controls.items()})}")

    # ---- candidate resolution (only for items without a ledger row; dedup by candidate key)
    cache = {}
    for item in rows_out:
        rid = item["item_id"]
        spec = frame["item_registry"][rid]
        item["informational"] = bool(spec.get("informational"))
        if item["ledger_row_exists"]:
            item["classification"] = "LEDGER_ROW_EXISTS"
            item["candidates_resolved"] = []
            continue
        if not spec.get("candidates"):
            item["classification"] = "NO_CANDIDATE_REGISTERED"
            item["candidates_resolved"] = []
            continue
        resolved = []
        for cid in spec["candidates"]:
            cspec = frame["candidate_registry"][cid]
            if cid not in cache:
                if cspec["kind"] == "doi":
                    res = resolve_doi(cspec["id"], cid.lower())
                elif cspec["kind"] == "arxiv":
                    res = resolve_arxiv(cspec["id"], cid.lower())
                else:
                    res = resolve_crossref_query(cspec["query"], cid.lower())
                met, why = expectation_met(res, cspec)
                res["expectation_met"] = met
                res["expectation_detail"] = why
                cache[cid] = res
                log(f"candidate {cid}: http={res['http_status']} resolved={bool(res.get('resolved'))} "
                    f"expectation_met={met} ({why})")
            resolved.append({"candidate_id": cid, **{k: cache[cid][k] for k in
                             ("kind", "id", "http_status", "raw", "raw_sha256",
                              "expectation_met", "expectation_detail") if k in cache[cid]}})
        item["candidates_resolved"] = resolved
        if any(r["expectation_met"] for r in resolved):
            item["classification"] = "CANDIDATE_RESOLVED_NOT_IN_LEDGER"
        else:
            item["classification"] = "CANDIDATE_UNRESOLVED"

    # ---- post-fetch drift check
    pins_after = {rel: sha256_file(f"{ROOT}/{rel}") for rel in frame["pins"]}
    drift_after = {k: (v, frame["pins"][k]) for k, v in pins_after.items()
                   if v != frame["pins"][k]}
    ledger_stable = pins_after["ledger/citation_audit.csv"] == frame["pins"]["ledger/citation_audit.csv"]
    corpus_valid = (not drift_after)
    log(f"pin recheck after fetch: drift={drift_after or 'none'} corpus_valid={corpus_valid}")

    # ---- aggregate
    from collections import Counter
    per_class = {}
    for item in rows_out:
        c = per_class.setdefault(item["class_id"], Counter())
        c[item["classification"]] += 1
    agg = {
        "n_rows": len(rows_out),
        "labels": dict(Counter(i["classification"] for i in rows_out)),
        "per_class": {k: dict(v) for k, v in per_class.items()},
        "ledger_rows_matched": sum(len(i["ledger_matches"]) for i in rows_out),
        "distinct_ledger_rows_matched": len({m["citation_id"] for i in rows_out for m in i["ledger_matches"]}),
    }
    controls_ok = all(v["ok"] for v in controls.values())
    hard_failures = []
    if not corpus_valid:
        hard_failures.append(f"pin drift: {drift_after}")
    if not controls_ok:
        hard_failures.append("control failure: " + json.dumps({k: v["ok"] for k, v in controls.items()}))
    if not ledger_stable:
        hard_failures.append("L1 ledger moved during the run")

    report = {
        "schema_version": "w070-anchors-report-1",
        "task_id": frame["task_id"],
        "actor": frame["actor"],
        "node_id": frame["node_id"],
        "group_id": "literature",
        "class_ids": frame["class_ids"],
        "gate": frame["gate"],
        "status": "COMPLETE" if not hard_failures else "VOID_OR_FAILED",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "authority": "worker evidence only; no gate verdict, no node completion, no ledger write",
        "question": frame["question"],
        "frame_sha256": frame_sha,
        "pins": frame["pins"],
        "pins_before": pins_before,
        "pins_after": pins_after,
        "corpus_valid": corpus_valid,
        "ledger_stable": ledger_stable,
        "controls": controls,
        "aggregate": agg,
        "items": rows_out,
        "candidates": cache,
        "hard_failures": hard_failures,
        "limits": frame["limits"] + [
            "one live fetch per candidate; arXiv/Crossref ranking and metadata are time-varying",
        ],
        "falsifier": ("Re-run this instrument at the same pins. Falsified if any item's "
                      "classification changes, if a candidate reported resolved re-resolves with "
                      "different title tokens, or if any control returns false. A pin sha256 "
                      "change voids the run rather than falsifying it."),
    }
    with open(f"{D}/report.json", "w") as f:
        json.dump(report, f, indent=1)
    log(f"report.json sha256 {sha256_file(D + '/report.json')}")
    log(f"aggregate {json.dumps(agg)}")
    log(f"elapsed {time.time()-t0:.1f}s")

    # ---- human-readable note
    L = ["# W070-L1-ANCHORS-01 — unanchored provenance census (worker-070)", ""]
    L.append(f"- frame `frame.json#{frame_sha[:12]}` (pre-registered before fetch); pins "
             f"{', '.join(k.split('/')[-1]+'#'+v[:12] for k, v in frame['pins'].items())}")
    L.append(f"- status **{report['status']}**; corpus_valid={corpus_valid}; controls_ok={controls_ok}")
    L.append(f"- scope: the {agg['n_rows']} `identifier: null` provenance rows in the three class schemas")
    L.append("")
    L.append("## Census")
    L.append("")
    L.append("| item | class | concept | label | ledger refs | candidate |")
    L.append("|---|---|---|---|---|---|")
    for i in rows_out:
        refs = ", ".join(m["citation_id"] for m in i["ledger_matches"]) or "—"
        cand = ", ".join(f"{c['candidate_id']}({'ok' if c['expectation_met'] else 'no'})"
                         for c in i["candidates_resolved"]) or "—"
        concept = i["concept"].replace("|", "/")[:70]
        L.append(f"| {i['item_id']} | {i['class_id']} | {concept} | {i['classification']} | {refs} | {cand} |")
    L.append("")
    L.append("## Controls")
    for k, v in controls.items():
        L.append(f"- {k}: {'PASS' if v['ok'] else 'FAIL'} — {v['detail']}")
    L.append("")
    L.append("## Reading")
    L.append("- `LEDGER_ROW_EXISTS` means the pinned L1 ledger already carries a row matching the")
    L.append("  pre-registered rule: the schema's `identifier: null` is a pointer gap, not a source gap.")
    L.append("- `CANDIDATE_RESOLVED_NOT_IN_LEDGER` means no ledger row matched but the registered")
    L.append("  primary locator resolves live with the expected metadata: a bindable pointer waits on")
    L.append("  the ledger owner. It does NOT mean the work entails the schema field.")
    L.append("- `CANDIDATE_UNRESOLVED` / `NO_CANDIDATE_REGISTERED` are the residual source gaps.")
    L.append("")
    L.append("No ledger, schema, map or review artifact was written by this task.")
    with open(f"{D}/ANCHORS.md", "w") as f:
        f.write("\n".join(L) + "\n")
    with open(f"{D}/run.log", "w") as f:
        f.write("\n".join(log_lines) + "\n")
    print(json.dumps(agg, indent=1))


if __name__ == "__main__":
    main()
