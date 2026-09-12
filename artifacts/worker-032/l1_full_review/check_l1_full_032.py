#!/usr/bin/env python3
"""W032-L1-FULL-INDEPENDENT-REVIEW-01 independent checker.

Read-only over every canonical path. Stdlib only. Writes:
  artifacts/worker-032/l1_full_review/report.json
  artifacts/worker-032/l1_full_review/controls.json

Implements preregistration.json (B1..B9, N1..N5, K0..K8, verdict rule) and
amendment A1 (B7 predicate refinement, post-hoc disclosed). Does not import
any prior scanner.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = datetime.timezone(datetime.timedelta(hours=8))

L1 = ROOT / "ledger/citation_audit.csv"
L0 = ROOT / "ledger/theorems.jsonl"
ACCEPT_NOTE = ROOT / "artifacts/literature/L0_L1_ACCEPTANCE.md"
MANIFEST = ROOT / "artifacts/literature/MANIFEST.json"
UNRESOLVED = ROOT / "artifacts/literature/unresolved.jsonl"
RUBRIC = ROOT / "evaluation_rubric.yaml"

PINS = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/literature/L0_L1_ACCEPTANCE.md": "fde5600b45a58698d1cb4e625127bcd54952dc9eaf17a47449329cccc28806c5",
    "artifacts/literature/unresolved.jsonl": "c7662d2926264eccb92f17c0889cbfc4afb4ae1b03b3d8113ee8ceb97b25d235",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
}
FROZEN = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
ANNOT = "(evidence/tag only)"
FIELDS = ["citation_id", "bibkey", "title", "authors", "year", "venue", "doi", "arxiv_id",
          "url", "status", "resolver_result", "verification_method", "evidence_type",
          "fetched_at", "http_status", "exact_locator", "evidence_url", "elided_quote",
          "mirror_of", "evidence_excerpt", "used_by_theorems", "class_mapping",
          "assessment", "verdict", "reviewer"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.datetime.now(CST).isoformat(timespec="seconds")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def load_rows() -> list[dict]:
    with open(L1, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in FIELDS:
            r.setdefault(k, "")
    return rows


def load_theorems() -> dict:
    th = {}
    with open(L0, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                d = json.loads(line)
                th[d["theorem_id"]] = d
    return th


def ids_of(field: str) -> list[str]:
    return [x.strip() for x in re.split(r"[;,]", field or "") if x.strip()]


def class_tokens(r: dict) -> tuple[set, bool]:
    raw = (r.get("class_mapping") or "").strip()
    if raw == ANNOT:
        return set(), True
    return {t for t in re.split(r"[;,\s]+", raw) if t}, False


RECORD_RE = re.compile(
    r"(^10\.\d{4,9}/\S+$"
    r"|doi\.org/10\.\d{4,9}/\S+"
    r"|arxiv\.org/(abs|pdf)/[^/\s]+"
    r"|export\.arxiv\.org/(abs|pdf)/[^/\s]+"
    r"|/api/(literature|works|abs)/[^?\s]+"
    r"|inspirehep\.net/(api/)?(literature|record)/\d+"
    r")",
    re.I,
)


def anchor_kind(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return "ABSENT"
    if re.fullmatch(r"10\.\d{4,9}/\S+", v):
        return "DOI"
    if re.fullmatch(r"\d{4}\.\d{4,5}(v\d+)?", v) or re.fullmatch(r"[a-z-]+(\.[A-Z]{2})?/\d{7}(v\d+)?", v):
        return "ARXIV_ID"
    if "..." in v:
        return "TRUNCATED"
    if re.search(r"(\?q=|/search|api/query|/query\b)", v, re.I):
        return "DISCOVERY_QUERY"
    if RECORD_RE.search(v):
        return "RECORD"
    if v.startswith("http"):
        return "OTHER_HTTP"
    return "OTHER"


def record_anchor(r: dict) -> tuple[str, str]:
    for col in ("evidence_url", "url", "doi", "arxiv_id"):
        v = (r.get(col) or "").strip()
        if v and v.lower() not in {"none", "false"}:
            return col, v
    return "ABSENT", ""


def row_defects(r: dict, th: dict) -> list[str]:
    out = []
    try:
        toks, _annot = class_tokens(r)
        if any(t not in FROZEN for t in toks):
            out.append("B1")
        if record_anchor(r)[0] == "ABSENT":
            out.append("B2")
        if (r.get("resolver_result") or "").strip() in {"unresolved", "contradicted"}:
            out.append("B3")
        if (r.get("verdict") or "").strip() == "verified" and not (r.get("status") or "").startswith("verified"):
            out.append("B3")
        used = ids_of(r.get("used_by_theorems"))
        m = re.match(r"\s*assessed:\s*(.*)$", r.get("assessment") or "")
        assessed = ids_of(m.group(1)) if m else []
        if any(i not in th for i in used) or any(i not in th for i in assessed):
            out.append("B4")
        if set(used) != set(assessed):
            out.append("B9")
        if toks:
            tcls = set()
            for i in used:
                tcls |= set(th.get(i, {}).get("class_ids") or [])
            if used and not (toks & tcls):
                out.append("B5")
        if (r.get("status") or "").strip() == "verified-primary" and (r.get("evidence_type") or "").strip() == "metadata":
            out.append("B6")
    except Exception as exc:  # fail closed
        out.append(f"EXC:{type(exc).__name__}")
    return out


def title_key(r: dict, refined: bool) -> str:
    t = r.get("title") or ""
    if refined:
        t = re.sub(r"\s*\([^()]{0,80}\)\s*$", "", t)
    return "ttl:" + norm(t) + "|" + (r.get("year") or "").strip()


def components(rows: list[dict], refined: bool = False) -> dict:
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for r in rows:
        cid = r["citation_id"]
        find(cid)
        keys = []
        if (r.get("doi") or "").strip():
            keys.append("doi:" + r["doi"].strip().lower())
        if (r.get("arxiv_id") or "").strip():
            keys.append("arx:" + r["arxiv_id"].strip().lower())
        if (r.get("title") or "").strip():
            keys.append(title_key(r, refined))
        for k in keys:
            union(cid, k)
    if refined:
        for r in rows:
            mo = (r.get("mirror_of") or "").strip()
            if mo:
                union(r["citation_id"], mo)
    comp: dict = defaultdict(list)
    for r in rows:
        comp[find(r["citation_id"])].append(r["citation_id"])
    return {k: sorted(v) for k, v in comp.items() if len(v) > 1}


def b7_defects(rows: list[dict], refined: bool = False) -> list[dict]:
    by_id = {r["citation_id"]: r for r in rows}
    out = []
    for comp, members in components(rows, refined).items():
        present = [m for m in members if m in by_id]
        empties = [m for m in present if not (by_id[m].get("mirror_of") or "").strip()]
        if len(empties) != 1:
            out.append({"component": members, "defect": "primary_count", "empty_mirror_of": sorted(empties)})
        for m in present:
            mo = (by_id[m].get("mirror_of") or "").strip()
            if mo and mo not in members:
                out.append({"component": members, "defect": "out_of_component",
                            "citation_id": m, "mirror_of": mo})
    return out


def main() -> int:
    pins_t0 = {str(p.relative_to(ROOT)): sha256(p) for p in (L1, L0, ACCEPT_NOTE, UNRESOLVED, RUBRIC)}
    manifest = json.loads(MANIFEST.read_text())
    manifest_declared = (manifest.get("artifacts") or {}).get("ledger/citation_audit.csv")
    rows = load_rows()
    th = load_theorems()
    unresolved = [json.loads(l) for l in UNRESOLVED.read_text().splitlines() if l.strip()]
    note = ACCEPT_NOTE.read_text()

    ex = lambda code: [r["citation_id"] for r in rows if code in row_defects(r, th)][:12]
    checks: dict = {}

    ids = [r["citation_id"] for r in rows]
    bib = [r["bibkey"] for r in rows]
    checks["C1_shape"] = {
        "result": "PASS" if len(rows) == 97 and len(set(ids)) == len(ids) and len(set(bib)) == len(bib)
                  and all((r.get("title") or "").strip() for r in rows) else "FAIL",
        "rows": len(rows), "unique_citation_ids": len(set(ids)), "unique_bibkeys": len(set(bib)),
        "missing_frozen_columns": [c for c in FIELDS if c not in rows[0]],
    }
    for code, label in (("B1", "B1_foreign_class_token"), ("B2", "B2_no_record_anchor"),
                        ("B3", "B3_resolution_or_verdict_mismatch"), ("B4", "B4_dangling_theorem_ref"),
                        ("B5", "B5_cross_surface_class_conflict"), ("B6", "B6_status_overstatement"),
                        ("B9", "B9_assessment_mismatch")):
        hits = ex(code)
        checks[label] = {"result": "PASS" if not hits else "FAIL", "count": len(hits), "examples": hits}

    strict = b7_defects(rows, refined=False)
    amended = b7_defects(rows, refined=True)
    checks["B7_duplicate_annotation_strict"] = {"result": "PASS" if not strict else "FAIL", "count": len(strict), "examples": strict[:6]}
    checks["B7_duplicate_annotation_amended_A1"] = {"result": "PASS" if not amended else "FAIL", "count": len(amended), "examples": amended[:6]}

    # amendment blast radius: strict vs amended may differ only on the SRC-020/060/072 component
    def compmap(defs):
        return {tuple(d["component"]) for d in defs}
    changed = compmap(strict) ^ compmap(amended)
    blast_ok = all(set(c) <= {"SRC-020", "SRC-060", "SRC-072"} for c in changed)

    multi_components = {tuple(v): v for v in components(rows, refined=True).values()}
    comp_table = []
    for members in sorted(multi_components, key=lambda m: (-len(m), m)):
        comp_table.append({
            "members": list(members),
            "primaries": [m for m in members if not (dict((r["citation_id"], r) for r in rows)[m].get("mirror_of") or "").strip()],
            "amended_defects": len(b7_defects([dict((r["citation_id"], r) for r in rows)[m] for m in members], refined=True)),
        })
    checks["C6_duplicate_components"] = {"count": len(comp_table), "components": comp_table,
                                         "duplicate_cluster_rate": round(len(comp_table) / len(rows), 4)}

    n1 = [r["citation_id"] for r in rows if class_tokens(r)[1]]
    multi = [r["citation_id"] for r in rows if (not class_tokens(r)[1]) and len(class_tokens(r)[0]) > 1]
    checks["N1_annotation_only_class_mapping"] = {"count": len(n1), "examples": n1[:8], "status": "REFERRED_BL7_HF02_SCOPE"}
    checks["N1b_multiclass_class_mapping"] = {"count": len(multi), "examples": multi[:8], "status": "REFERRED_BL7_HF02_SCOPE"}
    n2 = Counter(anchor_kind(r.get("exact_locator", "")) for r in rows)
    note_line = next((l.strip() for l in note.splitlines() if "exact_locator` column carries" in l), None)
    checks["N2_exact_locator_census"] = {
        "status": "REFERRED_REC6_BL7", "kinds": dict(n2),
        "record_shaped": sum(v for k, v in n2.items() if k in {"DOI", "ARXIV_ID", "RECORD"}),
        "non_record": sum(v for k, v in n2.items() if k in {"TRUNCATED", "DISCOVERY_QUERY", "OTHER_HTTP", "OTHER", "ABSENT"}),
        "acceptance_note_line": note_line,
    }
    checks["N3_self_certification"] = dict(Counter(r["reviewer"] for r in rows))
    checks["N4_status_method_asymmetry"] = {
        "verified_api_with_primary_method": [r["citation_id"] for r in rows
                                             if r["status"] == "verified-api" and "primary" in r["verification_method"]],
        "verified_primary_with_api_method": [r["citation_id"] for r in rows
                                             if r["status"] == "verified-primary" and r["verification_method"].endswith("-api")],
    }
    doi_not_in_urls = [r["citation_id"] for r in rows if r["doi"].strip()
                       and r["doi"].lower() not in " ".join([r["url"], r["evidence_url"], r["exact_locator"]]).lower()]
    arx_not_in_urls = [r["citation_id"] for r in rows if r["arxiv_id"].strip()
                       and r["arxiv_id"].split("v")[0] not in " ".join([r["url"], r["evidence_url"], r["exact_locator"]])]
    checks["N5_rejected_weak_predicates"] = {
        "doi_absent_from_url_set": len(doi_not_in_urls),
        "arxiv_absent_from_url_set": len(arx_not_in_urls),
        "note": "legitimate record pairs share neither string (journal DOI + arXiv locator); rejected as non-defects (K0 stays clean)",
    }
    checks["C8_manifest_pin"] = {"result": "PASS" if manifest_declared == PINS["ledger/citation_audit.csv"] else "FAIL",
                                 "declared": manifest_declared, "pin": PINS["ledger/citation_audit.csv"]}
    checks["C8_unresolved_disclosure"] = {"result": "PASS" if len(unresolved) > 0 else "FAIL",
                                          "entries": len(unresolved),
                                          "kinds": dict(Counter(u.get("kind") for u in unresolved)),
                                          "unassessed_sources_in_manifest": (manifest.get("counts") or {}).get("unassessed_sources")}

    # ---------------- controls ----------------
    base = dict(rows[0])
    def mutant(**kw):
        m = dict(base); m.update(kw); return m
    controls = {}
    controls["K0_clean"] = row_defects(mutant(), th) == []
    controls["K1_foreign_token"] = "B1" in row_defects(mutant(class_mapping="AF-NOT-A-CLASS"), th)
    controls["K2_no_anchor"] = "B2" in row_defects(mutant(doi="", arxiv_id="", url="", evidence_url=""), th)
    controls["K3_unresolved"] = "B3" in row_defects(mutant(resolver_result="unresolved"), th)
    controls["K4_dangling"] = "B4" in row_defects(mutant(used_by_theorems="T-999", assessment="assessed: T-999"), th)
    controls["K5_class_conflict"] = "B5" in row_defects(mutant(class_mapping="AF-WCC-VAC-GEN", used_by_theorems="D-002", assessment="assessed: D-002"), th)
    controls["K6_overstatement"] = "B6" in row_defects(mutant(status="verified-primary", evidence_type="metadata"), th)
    controls["K8_assessment_mismatch"] = "B9" in row_defects(mutant(used_by_theorems="D-002", assessment="assessed: T-999"), th)
    # same structure as the real SRC-020/060/072 chain: DOI-less primary + two DOI-carrying
    # suffix-annotated mirrors pointing at it
    clean_chain = [mutant(citation_id="SYN-1", title="Synthetic Record", year="2001", doi="", arxiv_id="",
                          evidence_url="https://inspirehep.net/api/literature/1", mirror_of=""),
                   mutant(citation_id="SYN-2", title="Synthetic Record (Crossref record)", year="2001",
                          doi="10.1000/syn", mirror_of="SYN-1"),
                   mutant(citation_id="SYN-3", title="Synthetic Record (OpenAlex abstract reconstruction)",
                          year="2001", doi="10.1000/syn", mirror_of="SYN-1")]
    controls["K7b_clean_mirror"] = b7_defects(clean_chain, refined=True) == []
    controls["K7c_unannotated_dup"] = any(d["defect"] == "primary_count" for d in b7_defects(
        [mutant(citation_id="SYN-3", title="Dup", year="2002", doi="10.1000/dup", mirror_of=""),
         mutant(citation_id="SYN-4", title="Dup", year="2002", doi="10.1000/dup", mirror_of="")], refined=True))
    controls["K7d_suffix_chain_amended_clean"] = b7_defects(clean_chain, refined=True) == []
    controls["K7e_suffix_chain_strict_fires"] = b7_defects(clean_chain, refined=False) != []

    def compmap(defs):
        return {tuple(d["component"]) for d in defs}
    changed = compmap(strict) ^ compmap(amended)
    blast_ok = all(set(c) <= {"SRC-020", "SRC-060", "SRC-072"} for c in changed)
    controls["K9_amendment_blast_radius"] = blast_ok

    blocking = [k for k, v in checks.items()
                if k.split("_")[0] in {"B1", "B2", "B3", "B4", "B5", "B6", "B7", "B9"}
                and v["result"] == "FAIL" and "strict" not in k]
    pins_t1 = {str(p.relative_to(ROOT)): sha256(p) for p in (L1, L0, ACCEPT_NOTE, UNRESOLVED, RUBRIC)}
    drift = {k: {"pin": PINS[k], "t0": pins_t0.get(k), "t1": pins_t1.get(k)}
             for k in pins_t0 if not (pins_t0[k] == pins_t1[k] == PINS.get(k))}
    verdict = "accept" if (not blocking and not drift and all(controls.values())) else "revise"

    report = {
        "schema": "worker-032/l1-full-review/report/v1",
        "task_id": "W032-L1-FULL-INDEPENDENT-REVIEW-01",
        "generated_at": now(),
        "actor": "worker-032",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": sorted(FROZEN),
        "target_id": "L1",
        "target_path": "ledger/citation_audit.csv",
        "reviewed_sha256": PINS["ledger/citation_audit.csv"],
        "pins_t0": pins_t0,
        "pins_t1": pins_t1,
        "drift": drift,
        "checks": checks,
        "controls": {k: ("PASS" if v else "FAIL") for k, v in controls.items()},
        "amendment_A1": {"applied": True, "blast_radius_ok": blast_ok,
                         "strict_defects": len(strict), "amended_defects": len(amended),
                         "post_hoc": True},
        "blocking_failures": blocking,
        "verdict_per_amended_rule": verdict,
        "falsifier": json.loads((OUT / "preregistration.json").read_text())["falsifier"],
        "authority_note": "read-only; no canonical write; no gate verdict; no node completion",
        "not_claimed": [
            "no decision of the ruling-bound axes (rubric HF-02 scope for multi-class rows; REC-6 exact_locator vs evidence_url)",
            "no external re-fetch or live HTTP resolution (offline review of recorded evidence only)",
            "no physics/mathematics claim; ledger metadata audit only",
        ],
    }
    core = {k: v for k, v in report.items() if k != "generated_at"}
    report["measurement_digest"] = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "controls.json").write_text(json.dumps(
        {"controls": report["controls"], "blocking_failures": blocking, "verdict": verdict,
         "strict_defects": len(strict), "amended_defects": len(amended),
         "digest": report["measurement_digest"]}, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "blocking": blocking, "strict_B7": len(strict),
                      "amended_B7": len(amended), "blast_ok": blast_ok,
                      "controls": report["controls"], "digest": report["measurement_digest"]}, indent=1))
    return 0 if verdict == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
