#!/usr/bin/env python3
"""W025-L1-LOCATOR-ADJ-01 - independent adjudication of the L1 exact_locator defect.

Node L1 / gate G-LIT.  Frozen input: ledger/citation_audit.csv (sha256 315c19145065...).
Question adjudicated (open finding HF-W005-L0-01): the column named `exact_locator` is a
discovery query rather than a record locator for part of the corpus, and the L0/L1
acceptance note claims it "carries the primary page/record URL".

This script does NOT edit the live artifact and does NOT set any gate/node verdict.
It produces a hash-bound, deterministic, offline-replayable census plus a live-anchor
check, and a mechanical (staged) repair recipe.

Modes:
  python3 run_l1_locator_025.py            # use cache, fetch only missing URLs
  python3 run_l1_locator_025.py --offline  # never touch the network
"""
from __future__ import annotations

import argparse
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CACHE = os.path.join(HERE, "cache")
OUT = os.path.join(HERE, "report.json")

CSV_PATH = os.path.join(ROOT, "ledger", "citation_audit.csv")
LEDGER_PATH = os.path.join(ROOT, "ledger", "theorems.jsonl")
NOTE_PATH = os.path.join(ROOT, "artifacts", "literature", "L0_L1_ACCEPTANCE.md")
RUBRIC_PATH = os.path.join(ROOT, "evaluation_rubric.yaml")

PINNED = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/literature/L0_L1_ACCEPTANCE.md": None,
}

UA = "ai4math-swarm-worker-025/1.0 (bounded L1 locator adjudication; local research audit)"
DIRECT_RE = re.compile(
    r"(doi\.org/10\.|arxiv\.org/(abs|pdf)/|inspirehep\.net/literature/\d|"
    r"journals\.aps\.org|link\.aps\.org/doi|projecteuclid|iopscience|sciencedirect|"
    r"springer|cambridge|oup\.com|wiley|zbmath|numdam|ams\.org|comptes-rendus|annals)"
)
DISCOVERY_RE = re.compile(r"(api/query|\?q=|search_query=|sortBy=)")
# A staged replacement counts as a record identifier if it names the record itself.
RECORD_ID_RE = re.compile(
    r"(doi\.org/10\.|arxiv\.org/(abs|pdf)/|inspirehep\.net/(api/)?literature/\d|"
    r"api\.crossref\.org/works/|api\.openalex\.org/works/|\.pdf($|[?#])|"
    r"journals\.aps\.org|link\.aps\.org/doi|projecteuclid|iopscience|sciencedirect|"
    r"springer|cambridge|oup\.com|wiley|zbmath|numdam|ams\.org|comptes-rendus|annals)"
)
MATCH_KINDS = {"ARXIV_ID_MATCH", "DOI_MATCH", "TITLE_MATCH"}

CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- locator census
def classify(v: str) -> str:
    if "..." in v:
        return "TRUNCATED"
    if DISCOVERY_RE.search(v):
        return "DISCOVERY"
    if DIRECT_RE.search(v):
        return "DIRECT"
    return "OTHER"


def is_direct(v: str) -> bool:
    return bool(v) and classify(v) == "DIRECT"


def proposed_locator(row: dict) -> str | None:
    for key, tmpl in (
        ("evidence_url", None),
        ("url", None),
        ("doi", "https://doi.org/{}"),
        ("arxiv_id", "https://arxiv.org/abs/{}"),
    ):
        val = (row.get(key) or "").strip()
        if not val:
            continue
        if "..." in val:
            continue
        if key in ("evidence_url", "url"):
            if val.startswith("http"):
                return val
        elif key == "doi":
            return tmpl.format(val)
        elif key == "arxiv_id":
            return tmpl.format(val)
    return None


def is_record_identifier(v: str) -> bool:
    return bool(v) and bool(RECORD_ID_RE.search(v)) and "..." not in v


# ---------------------------------------------------------------- fetch + cache
def cache_paths(url: str):
    tag = sha256_bytes(url.encode())[:20]
    return os.path.join(CACHE, tag + ".body"), os.path.join(CACHE, tag + ".meta.json")


def fetch(url: str, offline: bool, budget: dict, sleep_s: float):
    body_p, meta_p = cache_paths(url)
    if os.path.exists(meta_p) and os.path.exists(body_p):
        meta = json.load(open(meta_p))
        meta["served"] = "cache"
        return meta, open(body_p, "rb").read()
    if offline:
        return {"url": url, "status": None, "error": "NOT_FETCHED_OFFLINE", "served": "offline"}, b""
    if budget["left"] <= 0:
        return {"url": url, "status": None, "error": "NOT_FETCHED_TIME_BUDGET", "served": "budget"}, b""
    time.sleep(sleep_s)
    t0 = time.time()
    meta = {"url": url, "status": None, "error": None}
    body = b""
    cap = 2_000_000
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            meta["status"] = resp.status
            meta["final_url"] = resp.geturl()
            body = resp.read(cap)
    except urllib.error.HTTPError as e:
        meta["status"] = e.code
        meta["error"] = "HTTPError"
        try:
            body = e.read(20_000)
        except Exception:
            body = b""
    except Exception as e:  # noqa: BLE001 - transport errors are data, not crashes
        meta["status"] = None
        meta["error"] = type(e).__name__ + ": " + str(e)[:200]
    budget["left"] -= time.time() - t0
    meta["fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    meta["served"] = "network"
    meta["body_sha256"] = sha256_bytes(body)
    meta["body_len"] = len(body)
    meta["body_truncated"] = len(body) >= cap
    os.makedirs(CACHE, exist_ok=True)
    with open(body_p, "wb") as f:
        f.write(body)
    with open(meta_p, "w") as f:
        json.dump(meta, f, sort_keys=True)
    return meta, body


# ---------------------------------------------------------------- result parsing
def norm_arxiv(x: str) -> str:
    x = (x or "").strip()
    x = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", x)
    x = re.sub(r"v\d+$", "", x)
    return x.strip("/").lower()


def norm_doi(x: str) -> str:
    x = (x or "").strip().lower()
    x = re.sub(r"^https?://(dx\.)?doi\.org/", "", x)
    return x


def norm_title(x: str) -> str:
    x = re.sub(r"[^a-z0-9 ]+", " ", (x or "").lower())
    return " ".join(x.split())


def parse_results(url: str, body: bytes):
    """Return {'kind', 'total', 'ids', 'dois', 'titles'} from a cached API body.

    Handles arXiv Atom, INSPIRE JSON, Crossref/OpenAlex JSON.  A body cut at the
    read cap is parsed from its complete prefix and flagged kind '<kind>-prefix'.
    """
    text = body.decode("utf-8", "replace")
    if "export.arxiv.org/api/query" in url or "<feed" in text[:2000]:
        entries = re.findall(r"<entry>(.*?)</entry>", text, re.S)
        ids, dois, titles = set(), set(), []
        for e in entries:
            m = re.search(r"<id>(.*?)</id>", e, re.S)
            if m:
                ids.add(norm_arxiv(m.group(1)))
            m = re.search(r"<title>(.*?)</title>", e, re.S)
            if m:
                titles.append(norm_title(m.group(1)))
            for d in re.findall(r'<arxiv:doi[^>]*>(.*?)</arxiv:doi>', e, re.S):
                dois.add(norm_doi(d))
        total = int(re.search(r"<opensearch:totalResults[^>]*>(\d+)<", text).group(1)) if "totalResults" in text else len(entries)
        return {"kind": "arxiv", "total": total, "ids": sorted(ids), "dois": sorted(dois), "titles": titles}

    j = None
    try:
        j = json.loads(text)
    except Exception:
        j = None
    if j is None:
        # tolerant prefix parse for a body cut at the read cap
        ids = set(re.findall(r'"arxiv_eprints":\s*\[\s*\{[^}]*"value":\s*"([0-9.]+)"', text))
        dois = set(re.findall(r'"dois":\s*\[\s*\{[^}]*"value":\s*"([^"]+)"', text))
        titles = re.findall(r'"titles":\s*\[\s*\{\s*"title":\s*"((?:[^"\\]|\\.)*)"', text)
        kind = "inspire-prefix" if ('"hits"' in text[:2000] or "inspirehep" in url) else "unparsed"
        if kind == "inspire-prefix":
            return {
                "kind": kind,
                "total": None,
                "ids": sorted(norm_arxiv(x) for x in ids),
                "dois": sorted(norm_doi(x) for x in dois),
                "titles": [norm_title(t) for t in titles],
            }
        return {"kind": "unparsed", "total": None, "ids": [], "dois": [], "titles": []}
    if isinstance(j, dict) and "hits" in j:
        hits = (((j.get("hits") or {}).get("hits")) or [])
        ids, dois, titles = set(), set(), []
        for h in hits:
            md = (h or {}).get("metadata") or {}
            for t in (md.get("titles") or []):
                if isinstance(t, dict) and t.get("title"):
                    titles.append(norm_title(t["title"]))
            for a in (md.get("arxiv_eprints") or []):
                if isinstance(a, dict) and a.get("value"):
                    ids.add(norm_arxiv(a["value"]))
            for d in (md.get("dois") or []):
                if isinstance(d, dict) and d.get("value"):
                    dois.add(norm_doi(d["value"]))
        total = ((j.get("hits") or {}).get("total"))
        return {"kind": "inspire", "total": total, "ids": sorted(ids), "dois": sorted(dois), "titles": titles}
    if isinstance(j, dict) and "message" in j:
        md = j.get("message") or {}
        doi = norm_doi(md.get("DOI") or "")
        title = norm_title((md.get("title") or [""])[0] if isinstance(md.get("title"), list) else (md.get("title") or ""))
        return {"kind": "crossref", "total": 1 if md else 0, "ids": [], "dois": [doi] if doi else [], "titles": [title] if title else []}
    if isinstance(j, dict) and "doi" in j and "id" in j:
        return {
            "kind": "openalex",
            "total": 1,
            "ids": [],
            "dois": [norm_doi(j.get("doi") or "")],
            "titles": [norm_title(j.get("title") or "")],
        }
    return {"kind": "unparsed", "total": None, "ids": [], "dois": [], "titles": []}


def title_jaccard(a: str, b: str) -> float:
    A, B = set(a.split()), set(b.split())
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def cite_match(row: dict, res: dict) -> str:
    kind = res["kind"]
    if kind not in ("arxiv", "inspire", "inspire-prefix", "crossref", "openalex"):
        return "UNTESTABLE"
    aid, doi, title = norm_arxiv(row.get("arxiv_id")), norm_doi(row.get("doi")), norm_title(row.get("title"))
    if aid and aid in res["ids"]:
        return "ARXIV_ID_MATCH"
    if doi and doi in res["dois"]:
        return "DOI_MATCH"
    if kind in ("crossref", "openalex"):
        return "RECORD_ENDPOINT"
    if title:
        best = max((title_jaccard(title, t) for t in res["titles"]), default=0.0)
        if best >= 0.80:
            return "TITLE_MATCH"
    return "NO_MATCH"


def anchor_ok(meta: dict) -> str:
    if meta.get("status") == 200:
        return "HTTP_200"
    if meta.get("status") is not None:
        return "HTTP_" + str(meta["status"])
    if meta.get("error"):
        return str(meta["error"])
    return "NO_STATUS"


def sleep_for(url: str) -> float:
    if "export.arxiv.org/api" in url:
        return 3.05  # arXiv API politeness
    if "inspirehep.net" in url:
        return 1.0
    return 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--time-budget", type=float, default=420.0)
    ap.add_argument("--label", default="W025-L1-LOCATOR-ADJ-01")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)

    pinned_measured = {
        "ledger/citation_audit.csv": sha256_file(CSV_PATH),
        "ledger/theorems.jsonl": sha256_file(LEDGER_PATH),
        "evaluation_rubric.yaml": sha256_file(RUBRIC_PATH),
        "artifacts/literature/L0_L1_ACCEPTANCE.md": sha256_file(NOTE_PATH),
    }
    for rel, want in PINNED.items():
        if want is not None and pinned_measured[rel] != want:
            print("PIN MISMATCH", rel, pinned_measured[rel], "wanted", want, file=sys.stderr)
            return 2

    rows = list(csv.DictReader(open(CSV_PATH, newline="", encoding="utf-8")))
    note_lines = open(NOTE_PATH, encoding="utf-8").read().splitlines()
    note_claim = next((l for l in note_lines if "exact_locator" in l), "")
    budget = {"left": args.time_budget}

    # ---- per-row census (offline) ----
    out_rows = []
    for r in rows:
        loc = (r.get("exact_locator") or "").strip()
        cls = classify(loc)
        prop = proposed_locator(r)
        out_rows.append(
            {
                "citation_id": r.get("citation_id"),
                "bibkey": r.get("bibkey"),
                "class_mapping": r.get("class_mapping"),
                "used_by_theorems": r.get("used_by_theorems"),
                "verdict": r.get("verdict"),
                "exact_locator_class": cls,
                "exact_locator_has_literal_ellipsis": "..." in loc,
                "evidence_url_present": bool((r.get("evidence_url") or "").strip()),
                "proposed_staged_locator": prop,
                "proposed_locator_is_direct": is_record_identifier(prop or ""),
                "exact_locator": loc,
                "evidence_url": r.get("evidence_url"),
            }
        )

    # ---- live checks: defective locators + alternative anchors ----
    defective = [x for x in out_rows if x["exact_locator_class"] in ("DISCOVERY", "TRUNCATED", "OTHER")]
    discovered = {}
    for x in defective:
        u = x["exact_locator"]
        if u in discovered:
            continue
        meta, body = fetch(u, args.offline, budget, sleep_for(u))
        res = parse_results(u, body) if body else {"kind": "unfetched", "total": None, "ids": [], "dois": [], "titles": []}
        discovered[u] = {"meta": meta, "res": res}
    for x in out_rows:
        hit = discovered.get(x["exact_locator"])
        if hit:
            x["exact_locator_fetch_status"] = anchor_ok(hit["meta"])
            x["exact_locator_result_total"] = hit["res"]["total"]
            x["exact_locator_result_kind"] = hit["res"]["kind"]
            x["exact_locator_body_truncated"] = bool(hit["meta"].get("body_truncated"))
            if x["exact_locator_class"] != "DIRECT":
                x["exact_locator_cites_row"] = cite_match(_row_by_id(rows, x["citation_id"]), hit["res"])

    anchors = {}
    for x in out_rows:
        u = (x["evidence_url"] or "").strip()
        if not u or "..." in u or not u.startswith("http"):
            x["alternative_anchor_status"] = "ABSENT" if not u else "MALFORMED"
            continue
        if u not in anchors:
            meta, body = fetch(u, args.offline, budget, sleep_for(u))
            anchors[u] = anchor_ok(meta)
        x["alternative_anchor_status"] = anchors[u]

    # ---- summary ----
    for x in out_rows:
        x["alternative_anchor_present_ok"] = bool((x["evidence_url"] or "").strip()) and (
            "..." not in (x["evidence_url"] or "")
        )

    def count(pred):
        return sum(1 for x in out_rows if pred(x))

    cm_disj = count(lambda x: ";" in (x["class_mapping"] or ""))
    summary = {
        "rows_total": len(out_rows),
        "exact_locator_class_counts": {
            k: count(lambda x, k=k: x["exact_locator_class"] == k)
            for k in ("DIRECT", "DISCOVERY", "TRUNCATED", "OTHER")
        },
        "rows_with_literal_ellipsis": count(lambda x: x["exact_locator_has_literal_ellipsis"]),
        "rows_where_exact_locator_is_not_a_record_locator": count(
            lambda x: x["exact_locator_class"] != "DIRECT"
        ),
        "rows_with_alternative_anchor_present": count(lambda x: x["alternative_anchor_present_ok"]),
        "defective_rows_with_resolving_alternative_anchor": count(
            lambda x: x["exact_locator_class"] != "DIRECT" and x["alternative_anchor_status"] == "HTTP_200"
        ),
        "defective_rows_without_resolving_alternative_anchor": count(
            lambda x: x["exact_locator_class"] != "DIRECT" and x["alternative_anchor_status"] != "HTTP_200"
        ),
        "truncated_queries_returning_zero_relevant_records": count(
            lambda x: x["exact_locator_class"] == "TRUNCATED"
            and x.get("exact_locator_cites_row") == "NO_MATCH"
        ),
        "truncated_queries_with_result_total_zero": count(
            lambda x: x["exact_locator_class"] == "TRUNCATED" and x.get("exact_locator_result_total") == 0
        ),
        "truncated_queries_that_still_contain_the_cited_record": count(
            lambda x: x["exact_locator_class"] == "TRUNCATED"
            and x.get("exact_locator_cites_row") in MATCH_KINDS
        ),
        "truncated_queries_unparsed_or_untestable": count(
            lambda x: x["exact_locator_class"] == "TRUNCATED"
            and x.get("exact_locator_cites_row") in ("UNTESTABLE", "RECORD_ENDPOINT")
        ),
        "discovery_rows_whose_query_contains_the_cited_record": count(
            lambda x: x["exact_locator_class"] == "DISCOVERY"
            and x.get("exact_locator_cites_row") in MATCH_KINDS
        ),
        "discovery_rows_whose_query_does_not_contain_the_cited_record": count(
            lambda x: x["exact_locator_class"] == "DISCOVERY"
            and x.get("exact_locator_cites_row") == "NO_MATCH"
        ),
        "rows_with_staged_locator_repair_available": count(
            lambda x: bool(x["proposed_staged_locator"]) and x["proposed_locator_is_direct"]
        ),
        "rows_missing_evidence_url": count(lambda x: not x["evidence_url_present"]),
        "class_mapping_rows_with_disjunctive_token": cm_disj,
    }

    # ---- cache manifest (reproducibility pins for every fetched URL) ----
    manifest = []
    for m in sorted(os.listdir(CACHE)):
        if not m.endswith(".meta.json"):
            continue
        meta = json.load(open(os.path.join(CACHE, m)))
        manifest.append(
            {
                "url": meta.get("url"),
                "status": meta.get("status"),
                "error": meta.get("error"),
                "body_sha256": meta.get("body_sha256"),
                "body_len": meta.get("body_len"),
                "body_truncated": meta.get("body_truncated", False),
            }
        )
    manifest_path = os.path.join(HERE, "cache_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    manifest_sha = sha256_file(manifest_path)

    report = {
        "schema": "worker-025/l1-locator-adjudication/v1",
        "task_id": args.label,
        "actor": "worker-025",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "pinned_inputs": pinned_measured,
        "cache_manifest": "artifacts/worker-025/l1_locator_adj/cache_manifest.json#" + manifest_sha[:12],
        "cache_manifest_sha256": manifest_sha,
        "acceptance_note_claim": note_claim,
        "acceptance_note_claim_holds_for_rows": count(
            lambda x: x["exact_locator_class"] == "DIRECT"
        ),
        "acceptance_note_claim_falsified_for_rows": count(
            lambda x: x["exact_locator_class"] != "DIRECT"
        ),
        "summary": summary,
        "rows": out_rows,
        "not_claimed": [
            "gate verdict",
            "node status",
            "validation_status",
            "live-artifact repair",
            "citation-support adjudication beyond the locator column",
        ],
        "falsifier": (
            "Re-run at ledger/citation_audit.csv#315c19145065 with --offline on the shipped cache: "
            "this adjudication is falsified if the census differs, if any TRUNCATED row's literal "
            "query returns the cited record, if any defective row lacks a resolving evidence_url, "
            "if any proposed staged locator is not a direct record locator, or if a pinned input hash drifts."
        ),
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote", OUT, sha256_file(OUT))
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


def _row_by_id(rows, cid):
    for r in rows:
        if r.get("citation_id") == cid:
            return r
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
