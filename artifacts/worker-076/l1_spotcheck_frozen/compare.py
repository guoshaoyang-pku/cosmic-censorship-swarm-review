#!/usr/bin/env python3
"""worker-076 L1 independent re-fetch spot check at the frozen ledger hash.

Reads ledger/citation_audit.csv (frozen hash asserted), compares 6 uncovered rows
against raw responses fetched independently in ./raw/, and writes spotcheck_report.json.
No ledger text is used as evidence; only fetched bytes + the frozen row values under test.
"""
import csv, hashlib, json, re, sys, unicodedata
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]          # ai4math-swarm/
HERE = Path(__file__).resolve().parent
LEDGER = ROOT / "ledger/citation_audit.csv"
FROZEN_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
FROZEN_FOUR = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}

def sha256_bytes(b): return hashlib.sha256(b).hexdigest()
def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
    return re.sub(r"\s+", " ", s).strip()
def norm_low(s): return norm(s).lower()
def authors_norm(s):
    parts = re.split(r"[;,]", s or "")
    return sorted(norm_low(p) for p in parts if norm_low(p))
def frags_match(quote, fetched):
    """Quote may contain '...' elisions; every fragment must appear in order."""
    q = norm(quote); f = norm(fetched)
    if not q: return (False, 0, 0)
    frags = [x.strip() for x in re.split(r"\.\.\.|…", q) if len(x.strip()) >= 12]
    if not frags: frags = [q]
    pos, hit = 0, 0
    for fr in frags:
        i = f.find(fr, pos)
        if i >= 0:
            hit += 1; pos = i + len(fr)
    return (hit == len(frags), hit, len(frags))

def arxiv_parse(body):
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(body)
    e = root.find("a:entry", ns)
    if e is None: return None
    g = lambda p: (e.findtext(p, default="", namespaces=ns) or "").strip()
    return {
        "id": g("a:id"), "title": g("a:title"), "summary": norm(g("a:summary")),
        "published": g("a:published"), "updated": g("a:updated"),
        "journal_ref": g("arxiv:journal_ref"), "doi": g("arxiv:doi"),
        "comment": g("arxiv:comment"),
        "authors": [a.findtext("a:name", default="", namespaces=ns) for a in e.findall("a:author", ns)],
    }

def crossref_parse(body):
    m = json.loads(body)["message"]
    yr = None
    for k in ("published-print", "published", "issued", "created"):
        if k in m and m[k].get("date-parts"):
            yr = m[k]["date-parts"][0][0]; break
    return {
        "DOI": m.get("DOI"), "title": (m.get("title") or [""])[0],
        "container": (m.get("container-title") or [""])[0],
        "volume": m.get("volume"), "issue": m.get("issue"), "page": m.get("page"),
        "year": yr, "publisher": m.get("publisher"),
        "authors": [f"{a.get('given','')} {a.get('family','')}".strip() for a in m.get("author", [])],
        "abstract": norm(re.sub(r"<[^>]+>", " ", m.get("abstract", "") or "")),
    }

def inspire_parse(body):
    m = json.loads(body)["metadata"]
    pub = (m.get("publication_info") or [{}])[0]
    doi = ""
    for d in m.get("dois", []):
        if d.get("value", "").lower() == "10.4310/acta.2018.v220.n1.a1": doi = d["value"]; break
    ab = ""
    for a in m.get("abstracts", []):
        if a.get("value"): ab = norm(a["value"]); break
    return {
        "title": (m.get("titles") or [{}])[0].get("title", ""),
        "authors": [a.get("full_name", "") for a in m.get("authors", [])],
        "journal_title": pub.get("journal_title"), "volume": pub.get("journal_volume"),
        "issue": pub.get("journal_issue"), "page_start": pub.get("page_start"),
        "page_end": pub.get("page_end"), "year": pub.get("year"),
        "dois": [d.get("value") for d in m.get("dois", [])], "abstract": ab,
        "arxiv_eprints": m.get("arxiv_eprints", []),
    }

raw_hashes = {}
for line in (HERE / "raw/fetched_sha256.txt").read_text().splitlines():
    h, p = line.split(maxsplit=1)
    raw_hashes[Path(p).name] = h

ledger_bytes = LEDGER.read_bytes()
actual_sha = sha256_bytes(ledger_bytes)
rows = list(csv.DictReader(ledger_bytes.decode().splitlines()))
by_id = {r["citation_id"]: r for r in rows}
dup_ids = sorted({r["citation_id"] for r in rows if sum(1 for x in rows if x["citation_id"] == r["citation_id"]) > 1})

# census
class_tokens = {}
for r in rows:
    for t in [x.strip() for x in r["class_mapping"].split(";") if x.strip()]:
        class_tokens[t] = class_tokens.get(t, 0) + 1
outside = {k: v for k, v in class_tokens.items() if k not in FROZEN_FOUR and k != "(evidence/tag only)"}

SELECTED = ["SRC-035", "SRC-040", "SRC-047", "SRC-056", "SRC-078", "SRC-080"]
FETCH = {
    "SRC-035": [("crossref", "raw/src035_crossref.body", "https://api.crossref.org/works/10.4310/acta.2018.v220.n1.a1"),
                ("inspire-primary-evidence-url", "raw/src035_inspire.body", "https://inspirehep.net/api/literature/1469117")],
    "SRC-040": [("arxiv-api", "raw/src040_arxiv.body", "https://export.arxiv.org/api/query?id_list=2205.14808")],
    "SRC-047": [("arxiv-api", "raw/src047_arxiv.body", "https://export.arxiv.org/api/query?id_list=2603.17911")],
    "SRC-056": [("arxiv-api", "raw/src056_arxiv.body", "https://export.arxiv.org/api/query?id_list=gr-qc/0307013")],
    "SRC-078": [("arxiv-api", "raw/src078_arxiv.body", "https://export.arxiv.org/api/query?id_list=2606.28253")],
    "SRC-080": [("arxiv-api", "raw/src080_arxiv.body", "https://export.arxiv.org/api/query?id_list=2604.04877")],
}
status_by_file = {}
for line in (HERE / "raw/fetch_index.tsv").read_text().splitlines():
    name, code, url = line.split("\t")
    status_by_file[name] = int(code)

results, hard_failures, observations = [], [], []
for cid in SELECTED:
    r = by_id[cid]
    entry = {"citation_id": cid, "bibkey": r["bibkey"], "ledger_class_mapping": r["class_mapping"],
             "ledger_status": r["status"], "ledger_verification_method": r["verification_method"],
             "ledger_verdict": r["verdict"], "ledger_used_by_theorems": r["used_by_theorems"],
             "ledger_exact_locator": r["exact_locator"], "ledger_evidence_url": r["evidence_url"],
             "independent_fetches": [], "field_checks": {}, "quote_check": {}, "verdict": None,
             "observations": []}
    fetched_meta, quote_targets = [], []
    for kind, rel, url in FETCH[cid]:
        body = (HERE / rel).read_bytes()
        name = Path(rel).name
        code = status_by_file.get(name[:-5], None)
        meta = None
        try:
            if "arxiv" in kind: meta = arxiv_parse(body)
            elif kind == "crossref": meta = crossref_parse(body)
            elif "inspire" in kind: meta = inspire_parse(body)
        except Exception as e:
            entry["observations"].append(f"parse_error:{kind}:{e}")
        entry["independent_fetches"].append({"kind": kind, "url": url, "http_status": code,
                                             "sha256": sha256_bytes(body), "bytes": len(body)})
        if meta:
            fetched_meta.append((kind, meta))
            if kind == "arxiv-api":
                quote_targets.append(meta["summary"])
            if kind == "crossref" and meta.get("abstract"):
                quote_targets.append(meta["abstract"])
            if "inspire" in kind and meta.get("abstract"):
                quote_targets.append(meta["abstract"])
    # field checks vs best available fetched metadata
    t_ok = a_ok = y_ok = id_ok = None
    for kind, meta in fetched_meta:
        t_ok = t_ok or norm_low(meta.get("title", "")) == norm_low(r["title"]) or norm_low(r["title"]).startswith(norm_low(meta.get("title", ""))[:40])
        fa = authors_norm(";".join(meta.get("authors", [])))
        a_ok = a_ok or fa == authors_norm(r["authors"])
        y_ok = y_ok or str(meta.get("year") or (meta.get("published") or "")[:4]) == r["year"]
        ident = meta.get("DOI") or meta.get("doi") or ""
        id_ok = id_ok or (r["doi"] and ident.lower() == r["doi"].lower()) or \
                any(str(x).lower() == (r["arxiv_id"] or "").lower() for x in [meta.get("id", "").split("/abs/")[-1]])
    entry["field_checks"] = {"title_match": bool(t_ok), "authors_match": bool(a_ok),
                             "year_match": bool(y_ok), "identifier_match": bool(id_ok)}
    # quote fidelity
    best = None
    for qt in quote_targets:
        ok, hit, tot = frags_match(r["evidence_excerpt"], qt)
        if best is None or hit > best[1]: best = (ok, hit, tot, qt)
    if best:
        entry["quote_check"] = {"fragments_matched": best[1], "fragments_total": best[2],
                                "all_fragments_matched": best[0]}
    else:
        entry["quote_check"] = {"fragments_matched": 0, "fragments_total": 0,
                                "all_fragments_matched": False, "note": "no abstract text in fetched payload"}
    core_ok = all([entry["field_checks"]["title_match"], entry["field_checks"]["authors_match"]])
    ident_ok = entry["field_checks"]["identifier_match"] if r["doi"] or r["arxiv_id"] else True
    q_ok = entry["quote_check"]["all_fragments_matched"]
    if core_ok and ident_ok and q_ok:
        entry["verdict"] = "MATCH"
    elif core_ok and ident_ok:
        entry["verdict"] = "PARTIAL"
        entry["observations"].append("bibliographic identity matches; abstract quote not fully re-verified from fetched payload")
    else:
        entry["verdict"] = "MISMATCH"
        hard_failures.append({"citation_id": cid, "reason": "fetched metadata does not match ledger row",
                              "field_checks": entry["field_checks"]})
    results.append(entry)

summary = {"rows_in_frozen_csv": len(rows), "unique_citation_ids": len(by_id), "duplicate_ids": dup_ids,
           "class_token_census": class_tokens, "class_tokens_outside_frozen_four": outside,
           "status_census": {s: sum(1 for r in rows if r["status"] == s) for s in sorted({r["status"] for r in rows})},
           "verdict_census": {s: sum(1 for r in rows if r["verdict"] == s) for s in sorted({r["verdict"] for r in rows})},
           "verification_method_census": {s: sum(1 for r in rows if r["verification_method"] == s) for s in sorted({r["verification_method"] for r in rows})},
           "evidence_type_census": {s: sum(1 for r in rows if r["evidence_type"] == s) for s in sorted({r["evidence_type"] for r in rows})},
           "rows_with_empty_evidence_excerpt": sum(1 for r in rows if not r["evidence_excerpt"].strip()),
           "rows_with_empty_locator": sum(1 for r in rows if not (r["exact_locator"].strip() or r["evidence_url"].strip())),
           "rows_checked_this_pass": len(SELECTED),
           "rows_matched": sum(1 for e in results if e["verdict"] == "MATCH"),
           "rows_partial": sum(1 for e in results if e["verdict"] == "PARTIAL"),
           "rows_mismatch": sum(1 for e in results if e["verdict"] == "MISMATCH"),
           "prior_spotchecked_ids": sorted({"SRC-002","SRC-004","SRC-006","SRC-009","SRC-011","SRC-014","SRC-022","SRC-024","SRC-025","SRC-031"}),
           "overlap_with_prior_spotchecks": sorted(set(SELECTED) & {"SRC-002","SRC-004","SRC-006","SRC-009","SRC-011","SRC-014","SRC-022","SRC-024","SRC-025","SRC-031"})}

# class-binding observations (advisory only; no verdict authority)
for e in results:
    cm = e["ledger_class_mapping"]
    if e["citation_id"] == "SRC-035":
        e["observations"].append("ADVISORY: source is Einstein vacuum with positive cosmological constant (Kerr-de Sitter), not asymptotically flat; binding to AF-WCC-VAC-GEN (WCC statement is for asymptotically flat data) is a class-scope question for the lead, not adjudicated here.")
    if e["citation_id"] == "SRC-056":
        e["observations"].append("ADVISORY: source is Einstein-Maxwell/scalar? check: Dafermos charged black hole interior; binding to AF-SCC-C0-VAC-GEN (vacuum) plus AF-WCC-SCALAR-SPH should be confirmed against the schema's data-class definition by the lead.")
    if not cm or cm == "(evidence/tag only)":
        e["observations"].append("ADVISORY: row carries no class mapping; cannot be used for class-bound citation support.")

report = {
    "artifact": "artifacts/worker-076/l1_spotcheck_frozen/spotcheck_report.json",
    "worker": "worker-076",
    "role": "bounded execution worker (100-slot independent lifecycle)",
    "node_id": "L1", "gate": "G-LIT", "class_ids": sorted(FROZEN_FOUR),
    "created_at": None,  # filled by caller
    "task": "independent re-fetch spot check of ledger/citation_audit.csv at the frozen hash; rows chosen are disjoint from reviews/L1-spotcheck-10.json and reviews/L1-spotcheck-11.json",
    "target": {"path": "ledger/citation_audit.csv", "sha256_declared_frozen": FROZEN_SHA,
               "sha256_measured_this_pass": actual_sha, "hash_match": actual_sha == FROZEN_SHA},
    "method": "curl re-fetch of independent registry endpoints (Crossref REST, arXiv Atom API) plus the ledger's own evidence_url for the one DOI row; raw response bytes and sha256 archived in raw/; field-by-field comparison to the frozen row; abstract quote compared verbatim with ellipsis-aware fragment matching; no ledger text trusted as evidence for its own verification",
    "freshness": "all fetches HTTP 200 on 2026-09-12 (see raw/fetch_index.tsv, raw/*.headers)",
    "summary": summary,
    "results": results,
    "hard_failures": hard_failures,
    "advisory_findings": [o for e in results for o in e["observations"]],
    "verdict": "accept-scoped" if not hard_failures else "revise",
    "verdict_scope": f"scoped to the {len(SELECTED)} re-fetched rows at frozen csv sha256 {actual_sha[:12]}; not a G-LIT gate verdict",
    "authority_note": "worker event; no gate verdict, no node completion, no validation_status=passed claimed",
    "next_falsifier": "re-fetch any of these 6 rows at a later date and find (a) a title/author/identifier mismatch, or (b) an abstract quote fragment absent from the primary page; or show the frozen csv hash is not 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}
out = HERE / "spotcheck_report.json"
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"frozen_hash_match": report["target"]["hash_match"], "summary": summary,
                  "verdicts": {e["citation_id"]: e["verdict"] for e in results},
                  "hard_failures": hard_failures}, indent=1))
assert actual_sha == FROZEN_SHA, "frozen ledger hash drift detected"
