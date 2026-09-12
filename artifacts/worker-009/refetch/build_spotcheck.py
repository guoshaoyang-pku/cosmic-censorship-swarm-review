#!/usr/bin/env python3
"""worker-009 bounded task: independent re-fetch spot check of SCC ledger rows.

Assignment: asg-2026-09-11-L1-deepseek-flash-09-18
  node L1, gate G-LIT, classes AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN
  acceptance: verify SCC-side sources with exact theorem numbers and class mapping
  falsifier: theorem quoted in the wrong regularity class

Outputs (deterministic):
  ledger/citation_audit_scc_worker-009_spotcheck.csv
  reviews/L1-spotcheck-09.json
  artifacts/worker-009/refetch/REFETCH_MANIFEST.json
  comms/outbox/worker-009.jsonl   (8 schema-validated events)
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
REF = ROOT / "artifacts" / "worker-009" / "refetch"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def extract_env(txt: str, env: str, label: str | None = None, contains: str | None = None):
    for m in re.finditer(r"\\begin\{" + env + r"\}(.*?)\\end\{" + env + r"\}", txt, re.S):
        body = m.group(1)
        if label is not None and ("\\label{" + label + "}") not in body:
            continue
        if contains is not None and contains not in body:
            continue
        return body
    raise SystemExit(f"env {env} label={label} contains={contains!r} not found")


def detex(s: str) -> str:
    """Minimal readable rendering of a TeX theorem body; substitutions are recorded."""
    s = re.sub(r"%.*", "", s)
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    s = re.sub(r"\\footnote\{", " (", s)
    s = re.sub(r"\\cite\{([^}]*)\}", r"[\1]", s)
    for a, b in (("\\emph{", ""), ("\\textbf{", ""), ("\\underline{", ""), ("\\CHone", "CH1"),
                 ("\\CHtwo", "CH2"), ("\\CH", "CH"), ("\\EH", "EH"), ("\\Sgm", "Sigma"),
                 ("\\rd", "d"), ("\\varpi", "varpi"), ("\\omg", "omega"), ("\\eps", "epsilon"),
                 ("\\alp", "alpha"), ("\\dlt", "delta")):
        s = s.replace(a, b)
    s = re.sub(r"[{}]", "", s)
    s = s.replace("\\", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# ---------------------------------------------------------------- sources
SOURCES = {
    "duke": {
        "locator": "https://arxiv.org/e-print/1501.04598v1",
        "archive": REF / "src_1501.04598v1.tar.gz",
        "tex": REF / "src_1501.04598v1" / "SCClinear-150119-2.tex",
        "fetched_at": "2026-09-12T00:18:00+08:00",
    },
    "vdm": {
        "locator": "https://arxiv.org/e-print/2001.11156v2",
        "archive": REF / "src_2001.11156v2.tar.gz",
        "tex": REF / "src_2001.11156v2" / "globalinext_revised_for_CMP.tex",
        "fetched_at": "2026-09-12T00:20:00+08:00",
    },
    "partii": {
        "locator": "https://arxiv.org/e-print/1702.05716v2",
        "archive": REF / "src_1702.05716v2.tar.gz",
        "tex": REF / "src_1702.05716v2" / "SCCExterior-arXiv.190222.tex",
        "fetched_at": "2026-09-12T00:20:00+08:00",
    },
    "dafermos": {
        "locator": "https://arxiv.org/e-print/gr-qc/0307013v3",
        "archive": REF / "src_gr-qc_0307013v3.tar.gz",
        "tex": REF / "src_gr-qc_0307013v3" / "interior.tex",
        "fetched_at": "2026-09-12T00:20:00+08:00",
    },
}
for s in SOURCES.values():
    s["sha256"] = sha256_file(s["archive"])
    s["bytes"] = s["archive"].stat().st_size
    s["tex_text"] = s["tex"].read_text(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- quotes
DUKE_MAIN = extract_env(SOURCES["duke"]["tex_text"], "theorem", label="main.thm")
VDM_A = extract_env(SOURCES["vdm"]["tex_text"], "theo", label="rough2")
VDM_B = extract_env(SOURCES["vdm"]["tex_text"], "theo", label="rough1")
VDM_C = extract_env(SOURCES["vdm"]["tex_text"], "theo", label="rough1cond")
PARTII_MAIN = extract_env(SOURCES["partii"]["tex_text"], "theorem", label="main.theorem.intro")
DAF_THM12 = extract_env(SOURCES["dafermos"]["tex_text"], "theorem", label="allo9ewr")
DAF_COR13 = extract_env(SOURCES["dafermos"]["tex_text"], "corollary",
                        contains="Strong cosmic censorship")

# ---------------------------------------------------------------- canonical ledger rows
canon = {r["citation_id"]: r for r in csv.DictReader(open(ROOT / "ledger" / "citation_audit.csv"))}
CANON_HASH = sha256_file(ROOT / "ledger" / "citation_audit.csv")
SHARD = ROOT / "ledger" / "citation_audit_scc_flash-09.csv"
SHARD_HASH = sha256_file(SHARD)
shard = {r["citation_id"]: r for r in csv.DictReader(open(SHARD))}

ROWS = [
    {
        "spotcheck_id": "SC-09-001",
        "target_shard_id": "W09-003",
        "target_canonical_id": "SRC-055",
        "src": "duke",
        "env": "theorem",
        "theorem": "Theorem 1.1 (Main theorem, first version)",
        "ledger_excerpt_checked": shard["W09-003"]["evidence_excerpt"],
        "quote_tex": DUKE_MAIN,
        "theorem_number_check": (
            "CONFIRMED. Source uses \\newtheorem{theorem}{Theorem}[section]; main.thm is the 1st "
            "theorem environment in section 1 => Theorem 1.1. It is followed (line 325) by the 2nd "
            "theorem (Price-law sharpness) => 1.2, and by the 3rd (line 489, quantitative lower "
            "bound) => 1.3, matching the ledger's 'see also Theorem 1.3'."
        ),
        "equation_check": (
            "CONFIRMED. \\label{wave.eqn} is the 1st numbered equation of section 1 (TeX line 295) "
            "=> (1.1), the linear wave equation Box_g phi = 0 on a fixed RN background."
        ),
        "c0_c2_check": (
            "CONFIRMED. Conclusion is 'not in W^{1,2}_{loc} near any point of CH' = H^1 obstruction "
            "on a FIXED background. It is neither a C0 nor a C2 nonlinear inextendibility theorem; "
            "shard c0_or_c2 field states exactly this."
        ),
        "class_binding_check": (
            "PASS. Shard class_ids = AF-SCC-OTHER-MODELS (no binding to AF-SCC-C2-VAC-GEN or "
            "AF-SCC-C0-VAC-GEN). Canonical SRC-055 class_mapping = '(evidence/tag only)': acceptable, "
            "the row cannot support either frozen vacuum class."
        ),
        "match_verdict": "CONFIRMED-MATCH",
        "discrepancies": "None. Shard excerpt is a faithful de-TeXed rendering of the source theorem.",
        "correction_proposed": "none",
    },
    {
        "spotcheck_id": "SC-09-002",
        "target_shard_id": "W09-011",
        "target_canonical_id": "SRC-025",
        "src": "vdm",
        "env": "theo",
        "theorem": "Theorem A (two-ended), Theorem B (one-ended CH), Theorem C (one-ended, CH_Gamma empty)",
        "ledger_excerpt_checked": shard["W09-011"]["evidence_excerpt"],
        "quote_tex": VDM_A + "\n\n" + VDM_B + "\n\n" + VDM_C,
        "theorem_number_check": (
            "CONFIRMED. Source sets \\renewcommand{\\thetheo}{\\Alph{theo}} => theo environments are "
            "lettered A,B,C,...; rough2=A, rough1=B, rough1cond=C. Formal results use "
            "\\newtheorem{thm}{Theorem}[section] and sit in section 3 => 3.x; the blow-up theorem is "
            "3.2, two-ended C^2-future-inextendibility 3.3, one-ended across CH 3.4, matching the "
            "shard's 'formal Theorem 3.2/3.3/3.4'."
        ),
        "equation_check": (
            "CONFIRMED. Theorem A refers to Theorem 0.2 (two-ended a priori Penrose diagram, "
            "\\thetheothree=0.2); Theorem B/C refer to Theorem 0.1 (one-ended, \\thetheotwo=0.1)."
        ),
        "c0_c2_check": (
            "CONFIRMED. A/B/C are C^2-future-inextendibility statements. The same paper's Conjecture "
            "1.1 (C0 version) is stated FALSE for this model; shard c0_or_c2 field separates C2 "
            "(inextendible) from C0 (extendible) correctly."
        ),
        "class_binding_check": (
            "SHARD PASS / CANONICAL FAIL. Shard class_ids = AF-SCC-OTHER-MODELS, correct: the model "
            "is Einstein-Maxwell-Klein-Gordon in spherical symmetry, not 4D vacuum. Canonical "
            "SRC-025 class_mapping = AF-SCC-C2-VAC-GEN binds a non-vacuum model result to the frozen "
            "vacuum class; F2a l1_ledger_refs T-514 marks this model result scope_use 'different data "
            "class; do not transfer'."
        ),
        "match_verdict": "CONFIRMED-MATCH (statement) / CLASS-BINDING-REVISE (canonical row)",
        "discrepancies": (
            "Canonical SRC-025 class_mapping=AF-SCC-C2-VAC-GEN vs schema F2a binding rule "
            "(model-class result, do not transfer)."
        ),
        "correction_proposed": (
            "Canonical SRC-025 class_mapping should be '(model-class evidence only; no class-id "
            "binding)' or the registered variant reference; not the bare frozen class id."
        ),
    },
    {
        "spotcheck_id": "SC-09-003",
        "target_shard_id": "W09-013",
        "target_canonical_id": "SRC-058",
        "src": "partii",
        "env": "theorem",
        "theorem": "Theorem 1.1 (C^2 formulation of SCC, rough version)",
        "ledger_excerpt_checked": shard["W09-013"]["evidence_excerpt"],
        "quote_tex": PARTII_MAIN,
        "theorem_number_check": (
            "CONFIRMED. \\newtheorem{theorem}{Theorem}[section]; main.theorem.intro is the 1st "
            "theorem environment in section 1 => Theorem 1.1; the following intro theorems are 1.2 "
            "and 1.3. The shard's 'Theorem 1.1 (rough version)' is exact."
        ),
        "equation_check": (
            "CONFIRMED. Abstract and theorem both state the C^2 formulation for two-ended AF data; "
            "genericity conditions (1) open in weighted C^1, (2) complement of co-dimension >=1 in "
            "weighted C^infinity, hence dense in weighted C^infinity."
        ),
        "c0_c2_check": (
            "CONFIRMED. C^2-future-inextendibility for a generic set; C0 is not addressed here "
            "(shard c0_or_c2 field says exactly this)."
        ),
        "class_binding_check": (
            "SHARD PASS / CANONICAL FAIL. Shard class_ids = AF-SCC-OTHER-MODELS, correct: "
            "Einstein-Maxwell-real-scalar, spherical symmetry, two-ended. Canonical SRC-058 "
            "class_mapping = AF-SCC-C2-VAC-GEN violates the schema caveat 'support for this class is "
            "preprint-level or model-class ... each entry's does_not_imply clauses must travel with "
            "any citation'."
        ),
        "match_verdict": "CONFIRMED-MATCH (statement) / CLASS-BINDING-REVISE (canonical row)",
        "discrepancies": (
            "Canonical SRC-058 class_mapping=AF-SCC-C2-VAC-GEN vs F2a T-514 scope_use 'different data "
            "class; do not transfer'."
        ),
        "correction_proposed": (
            "Canonical SRC-058 class_mapping should be '(model-class evidence only; no class-id "
            "binding)', keeping the shard's AF-SCC-OTHER-MODELS token."
        ),
    },
    {
        "spotcheck_id": "SC-09-004",
        "target_shard_id": "W09-002",
        "target_canonical_id": "SRC-021;SRC-056",
        "src": "dafermos",
        "env": "theorem",
        "theorem": "Theorem 1.2; Corollary 1.3",
        "ledger_excerpt_checked": shard["W09-002"]["evidence_excerpt"],
        "quote_tex": DAF_THM12 + "\n\n" + DAF_COR13,
        "theorem_number_check": (
            "CONFIRMED. \\newtheorem{corollary}[theorem] shares the theorem counter: Theorem 1.1 "
            "(line 216, existence of the maximal development), Theorem 1.2 (line 295, mass blow-up / "
            "no C^1 metric), Corollary 1.3 (line 368, SCC false). The shard's numbering is exact."
        ),
        "equation_check": (
            "CONFIRMED. Corollary 1.3 cites formulation [13] = bibitem chr:givp = D. Christodoulou, "
            "'On the global initial value problem and the issue of singularities', Class. Quantum "
            "Grav. 16 (1999) no. 12A, A23-A35: the C0 formulation."
        ),
        "c0_c2_check": (
            "CONFIRMED. Theorem 1.2 gives C0-extendibility of the metric and excludes C^1 extensions; "
            "it does NOT prove C2-inextendibility. Shard c0_or_c2 field states 'C2: NOT addressed. Do "
            "not upgrade this citation to C2 SCC false.'"
        ),
        "class_binding_check": (
            "FAIL (shard and canonical). Shard class_ids = AF-SCC-OTHER-MODELS;AF-SCC-C0-VAC-GEN and "
            "canonical SRC-021/SRC-056 class_mapping = AF-SCC-C0-VAC-GEN. The source is "
            "Einstein-Maxwell-scalar (not VAC = 4D Einstein vacuum, Lambda=0) and it FALSEFIES the C0 "
            "formulation rather than supporting the frozen class statement. F2b anti_scope says the "
            "horizon-localized C0 formulation is a registered VARIANT (parent_class "
            "AF-SCC-C0-VAC-GEN, variant_id CH) and 'Binding T-301 to the frozen class would be a "
            "scope error in the other direction'; the frozen AF-SCC-C0-VAC-GEN remains open."
        ),
        "match_verdict": "CONFIRMED-MATCH (statement) / CLASS-BINDING-REVISE (shard + canonical)",
        "discrepancies": (
            "Class-id leak in both the shard row (class_ids) and the canonical row (class_mapping): "
            "non-vacuum C0-falsity bound to AF-SCC-C0-VAC-GEN; SRC-056 additionally carries "
            "AF-WCC-SCALAR-SPH alongside."
        ),
        "correction_proposed": (
            "Drop AF-SCC-C0-VAC-GEN from shard W09-002 class_ids; canonical SRC-021/SRC-056 "
            "class_mapping -> 'AF-SCC-OTHER-MODELS (anti-scope: C0-formulation falsity, horizon-"
            "localized variant CH; no class-id binding)'. Lead-literature adjudicates."
        ),
    },
    {
        "spotcheck_id": "SC-09-005",
        "target_shard_id": "W09-005",
        "target_canonical_id": "(none; unresolved)",
        "src": None,
        "env": None,
        "theorem": "n/a - assigned citation 'Eardley-Gundlach' not located",
        "ledger_excerpt_checked": shard["W09-005"]["evidence_excerpt"],
        "quote_tex": "",
        "theorem_number_check": "n/a",
        "equation_check": "n/a",
        "c0_c2_check": "n/a",
        "class_binding_check": (
            "n/a. Independent re-query (2026-09-12): OpenAlex "
            "filter=raw_author_name.search:Eardley + search='critical phenomena gravitational "
            "collapse' -> 0 results; Crossref query.bibliographic='Eardley Gundlach critical "
            "phenomena gravitational collapse' -> 5 hits, all Gundlach-only. No joint Eardley-"
            "Gundlach publication found. Nearest real works confirmed: Eardley-Hirschmann 1995, "
            "PRD 51:4198, DOI 10.1103/PhysRevD.51.4198 ('Universal scaling and echoing in the "
            "gravitational collapse of a complex scalar field', OpenAlex HTTP 200) and "
            "Gundlach-Martin-Garcia 2007 Living Rev. Rel. 10:5 (shard W09-006)."
        ),
        "match_verdict": "UNRESOLVED-CONFIRMED",
        "discrepancies": (
            "None: shard correctly marks the citation unsupported and proposes the two real works."
        ),
        "correction_proposed": (
            "Assignment item 'Eardley-Gundlach' should be replaced by Eardley-Hirschmann 1995 "
            "(DOI 10.1103/PhysRevD.51.4198) and/or dropped; no resolvable joint work exists."
        ),
    },
]

# ---------------------------------------------------------------- write spotcheck CSV
COLS = [
    "spotcheck_id", "refetch_timestamp", "reviewer", "target_shard", "target_shard_id",
    "target_canonical", "target_canonical_id", "assignment_id", "gate", "class_scope",
    "locator_refetched", "fetch_method", "http_status", "archive_bytes", "archive_sha256",
    "source_tex_file", "ledger_excerpt_checked", "source_tex_quote", "source_quote_plain",
    "quote_tex_sha256", "theorem_number_check", "equation_check", "c0_c2_check",
    "class_binding_check", "match_verdict", "discrepancies", "correction_proposed", "falsifier",
    "evidence_ref",
]
csv_path = ROOT / "ledger" / "citation_audit_scc_worker-009_spotcheck.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in ROWS:
        s = SOURCES.get(r["src"]) if r["src"] else None
        quote_plain = detex(r["quote_tex"]) if r["quote_tex"] else ""
        row = {
            "spotcheck_id": r["spotcheck_id"],
            "refetch_timestamp": NOW,
            "reviewer": "worker-009",
            "target_shard": "ledger/citation_audit_scc_flash-09.csv",
            "target_shard_id": r["target_shard_id"],
            "target_canonical": "ledger/citation_audit.csv",
            "target_canonical_id": r["target_canonical_id"],
            "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
            "gate": "G-LIT",
            "class_scope": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN (scope check only)",
            "locator_refetched": s["locator"] if s else "n/a (null-result queries)",
            "fetch_method": (
                "arxiv e-print TeX source retrieved with curl, unpacked locally, theorem "
                "environments parsed from .tex" if s else
                "OpenAlex works API + Crossref works API, independent re-query"
            ),
            "http_status": 200 if s else "200 (both APIs)",
            "archive_bytes": s["bytes"] if s else "",
            "archive_sha256": s["sha256"] if s else "",
            "source_tex_file": s["tex"].name if s else "",
            "ledger_excerpt_checked": r["ledger_excerpt_checked"],
            "source_tex_quote": r["quote_tex"],
            "source_quote_plain": quote_plain,
            "quote_tex_sha256": sha256_text(r["quote_tex"]) if r["quote_tex"] else "",
            "theorem_number_check": r["theorem_number_check"],
            "equation_check": r["equation_check"],
            "c0_c2_check": r["c0_c2_check"],
            "class_binding_check": r["class_binding_check"],
            "match_verdict": r["match_verdict"],
            "discrepancies": r["discrepancies"],
            "correction_proposed": r["correction_proposed"],
            "falsifier": (
                "A re-fetch of the same locator shows a different theorem number, a different "
                "regularity class in the conclusion, or a frozen vacuum class id that the source's "
                "matter component (VAC) cannot satisfy."
            ),
            "evidence_ref": (
                f"{s['locator']} (HTTP 200, sha256 {s['sha256'][:16]})" if s else
                "https://api.openalex.org/works (HTTP 200); https://api.crossref.org/works (HTTP 200)"
            ),
        }
        w.writerow(row)

# ---------------------------------------------------------------- manifest
manifest = {
    "manifest_id": f"worker-009-refetch-{STAMP}",
    "created_at": NOW,
    "task": "asg-2026-09-11-L1-deepseek-flash-09-18",
    "node_id": "L1",
    "gate": "G-LIT",
    "method": "independent re-fetch; arXiv e-print TeX sources (authoritative full text), parsed locally",
    "sources": [
        {
            "tag": k,
            "locator": v["locator"],
            "http_status": 200,
            "fetched_at": v["fetched_at"],
            "fetched_by": "worker-009",
            "archive_bytes": v["bytes"],
            "archive_sha256": v["sha256"],
            "tex_file_used": v["tex"].name,
            "theorem_labels_verified": labels,
        }
        for (k, v), labels in zip(
            SOURCES.items(),
            [
                ["main.thm", "wave.eqn"],
                ["rough2", "rough1", "rough1cond", "conditionnalSCCtheoremtwoended", "CHinexttheorem"],
                ["main.theorem.intro"],
                ["eis9ew", "allo9ewr", "chr:givp"],
            ],
        )
    ],
    "raw_html_partial_fetches": {
        "note": "ar5iv HTML mirrors were fetched first for cross-checking but were truncated by the "
                "60 s transfer cap; the authoritative evidence used here is the complete arXiv "
                "e-print TeX source. Partial HTML files are retained in this directory.",
        "files": ["0307013.html", "1501.04598.html", "1702.05716.html", "2001.11156.html"],
    },
    "null_result_queries": [
        "https://api.openalex.org/works?filter=raw_author_name.search:Eardley&search=critical phenomena gravitational collapse -> count 0",
        "https://api.crossref.org/works?query.bibliographic=Eardley+Gundlach+critical+phenomena+gravitational+collapse -> 5 hits, none jointly authored",
        "https://api.openalex.org/works/doi:10.1103/PhysRevD.51.4198 -> Eardley-Hirschmann 1995 confirmed",
    ],
    "canonical_ledger_snapshot": {"path": "ledger/citation_audit.csv", "sha256": CANON_HASH},
    "shard_snapshot": {"path": "ledger/citation_audit_scc_flash-09.csv", "sha256": SHARD_HASH},
}
man_path = REF / "REFETCH_MANIFEST.json"
man_path.write_text(json.dumps(manifest, indent=2))

# ---------------------------------------------------------------- review JSON
confirmed = [r["spotcheck_id"] for r in ROWS if r["match_verdict"].startswith("CONFIRMED-MATCH (statement)") is False]
review = {
    "review_id": f"L1-spotcheck-09-{STAMP}",
    "reviewer": "worker-009",
    "node_id": "L1",
    "gate": "G-LIT",
    "class_scope": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-09-18",
    "created_at": NOW,
    "acceptance_checked": (
        "Re-fetch >=3 ledger rows directly from the DOI/arXiv locator; quote the fetched text; "
        "state match/mismatch against the ledger excerpt verbatim; emit a review event with verdict."
    ),
    "method": (
        "Five ledger rows re-fetched from arXiv e-print TeX sources (complete, authoritative) and "
        "parsed locally; theorem numbering recomputed from the source's own counters; class binding "
        "checked against schemas/af_scc_c2_vacuum.yaml and schemas/af_scc_c0_vacuum.yaml."
    ),
    "rows_checked": 5,
    "rows_confirmed_statement": 4,
    "rows_confirmed_with_class_correction": 3,
    "rows_unresolved_confirmed": 1,
    "verdict": "revise",
    "score": 3,
    "hard_failures": [
        "HF-09-CLASS-01: canonical SRC-025 and SRC-058 set class_mapping=AF-SCC-C2-VAC-GEN for "
        "non-vacuum model results (EMKG / EM-scalar spherical), violating F2a l1_ledger_refs T-514 "
        "scope_use 'different data class; do not transfer' and the VAC matter component.",
        "HF-09-CLASS-02: canonical SRC-021/SRC-056 and shard row W09-002 bind the Einstein-Maxwell-"
        "scalar C0-falsity to AF-SCC-C0-VAC-GEN; F2b anti_scope places that horizon-localized "
        "statement in registered variant CH, and binds to the frozen class only as a scope error.",
    ],
    "findings": [
        "Statements and theorem numbers of SRC-055 (Luk-Oh Duke Thm 1.1, eq. (1.1)), SRC-058 "
        "(Luk-Oh Part II Thm 1.1), SRC-025 (Van de Moortel Theorems A/B/C, formal 3.2/3.3/3.4) and "
        "SRC-021/SRC-056 (Dafermos Thm 1.2, Cor 1.3) are reproduced exactly from freshly fetched "
        "primary TeX sources.",
        "The C0/C2 distinction in the shard rows W09-003/W09-011/W09-013 is honest; the class leak "
        "enters in the canonical class_mapping column (and in W09-002's class_ids).",
        "W09-005 ('Eardley-Gundlach') is independently confirmed unresolved: OpenAlex returns 0 "
        "records with Eardley as author on critical-phenomena collapse; Crossref returns "
        "Gundlach-only works. Eardley-Hirschmann 1995 (DOI 10.1103/PhysRevD.51.4198) is the nearest "
        "real work and is verified.",
        "Reproducibility gap addressed: raw TeX archives with sha256 and exact e-print locators are "
        "retained in artifacts/worker-009/refetch/.",
    ],
    "evidence_refs": [
        f"ledger/citation_audit_scc_worker-009_spotcheck.csv#{sha256_file(csv_path)[:16]}",
        f"artifacts/worker-009/refetch/REFETCH_MANIFEST.json#{sha256_file(man_path)[:16]}",
        f"artifacts/worker-009/refetch/src_1501.04598v1.tar.gz#{SOURCES['duke']['sha256'][:16]}",
        f"artifacts/worker-009/refetch/src_1702.05716v2.tar.gz#{SOURCES['partii']['sha256'][:16]}",
        f"artifacts/worker-009/refetch/src_2001.11156v2.tar.gz#{SOURCES['vdm']['sha256'][:16]}",
        f"artifacts/worker-009/refetch/src_gr-qc_0307013v3.tar.gz#{SOURCES['dafermos']['sha256'][:16]}",
        f"ledger/citation_audit.csv#{CANON_HASH[:16]}",
        f"ledger/citation_audit_scc_flash-09.csv#{SHARD_HASH[:16]}",
    ],
    "next_falsifier": (
        "A ledger row whose source, re-fetched at its own locator, yields a different theorem number "
        "or a conclusion in a regularity class other than the one bound in class_mapping; or any "
        "class_mapping that names a frozen vacuum class while the source's matter component is not VAC."
    ),
    "what_this_does_not_prove": (
        "Spot check of 5 of 35 shard rows; no full-ledger verification, no gate verdict, no theorem "
        "promotion. Worker events cannot set status=done or validation_status=passed."
    ),
    "outcome_counts": {
        "accept": 1, "revise": 3, "reject": 0, "inconclusive": 1,
        "note": "accept=SRC-055; revise=SRC-025,SRC-058,SRC-021/056 (statements confirmed, class "
                "binding only); inconclusive=W09-005 Eardley-Gundlach (unresolved confirmed)."
    },
    "rows": [
        {
            "spotcheck_id": r["spotcheck_id"],
            "target": f"{r['target_shard_id']} / {r['target_canonical_id']}",
            "verdict": (
                "accept" if r["spotcheck_id"] == "SC-09-001" else
                "inconclusive" if r["spotcheck_id"] == "SC-09-005" else "revise"
            ),
            "score": {"SC-09-001": 4, "SC-09-002": 3, "SC-09-003": 3, "SC-09-004": 2,
                      "SC-09-005": 2}[r["spotcheck_id"]],
            "match_verdict": r["match_verdict"],
            "discrepancies": r["discrepancies"],
            "correction_proposed": r["correction_proposed"],
        }
        for r in ROWS
    ],
}
rev_path = ROOT / "reviews" / "L1-spotcheck-09.json"
rev_path.write_text(json.dumps(review, indent=2))

# ---------------------------------------------------------------- outbox events
SPOT_SHA = sha256_file(csv_path)
REV_SHA = sha256_file(rev_path)
MAN_SHA = sha256_file(man_path)
EVID = [
    f"ledger/citation_audit_scc_worker-009_spotcheck.csv#{SPOT_SHA[:16]}",
    f"reviews/L1-spotcheck-09.json#{REV_SHA[:16]}",
    f"artifacts/worker-009/refetch/REFETCH_MANIFEST.json#{MAN_SHA[:16]}",
    f"artifacts/worker-009/refetch/src_1702.05716v2.tar.gz#{SOURCES['partii']['sha256'][:16]}",
    f"artifacts/worker-009/refetch/src_2001.11156v2.tar.gz#{SOURCES['vdm']['sha256'][:16]}",
    f"artifacts/worker-009/refetch/src_1501.04598v1.tar.gz#{SOURCES['duke']['sha256'][:16]}",
    f"artifacts/worker-009/refetch/src_gr-qc_0307013v3.tar.gz#{SOURCES['dafermos']['sha256'][:16]}",
]
events = [
    {
        "event_id": f"w009-refetch-{STAMP}-artifact-01",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "group_id": "literature",
        "artifact_type": "citation_audit_spotcheck",
        "path": "ledger/citation_audit_scc_worker-009_spotcheck.csv",
        "sha256": SPOT_SHA,
        "validation_status": "unverified",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-LIT",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "evidence_refs": EVID,
        "note": (
            "5-row independent re-fetch spot check from complete arXiv e-print TeX sources: "
            "W09-003, W09-011, W09-013, W09-002 confirmed at statement level; W09-005 (Eardley-"
            "Gundlach) unresolved independently confirmed. 3 canonical class_mapping leaks flagged "
            "(SRC-025, SRC-058, SRC-021/SRC-056)."
        ),
    },
    {
        "event_id": f"w009-refetch-{STAMP}-artifact-02",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "group_id": "literature",
        "artifact_type": "review_artifact",
        "path": "reviews/L1-spotcheck-09.json",
        "sha256": REV_SHA,
        "validation_status": "unverified",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-LIT",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "evidence_refs": EVID,
        "note": "Structured spot-check review; G-LIT re-fetch criterion evidence; lead-literature adjudicates.",
    },
    {
        "event_id": f"w009-refetch-{STAMP}-review-01",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-009",
        "target_id": "ledger/citation_audit.csv:SRC-055",
        "reviewer": "worker-009",
        "verdict": "accept",
        "score": 4,
        "hard_failures": [],
        "findings": [
            "Luk-Oh 2015/2017 Duke Theorem 1.1 verified verbatim from arXiv:1501.04598v1 TeX; "
            "equation (1.1) and theorem numbering confirmed; neither C0 nor C2 nonlinear claim, so "
            "'evidence/tag only' canonical mapping is correct."
        ],
        "evidence_refs": EVID,
    },
    {
        "event_id": f"w009-refetch-{STAMP}-review-02",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-009",
        "target_id": "ledger/citation_audit.csv:SRC-025",
        "reviewer": "worker-009",
        "verdict": "revise",
        "score": 3,
        "hard_failures": [
            "HF-09-CLASS-01: class_mapping=AF-SCC-C2-VAC-GEN binds a non-vacuum EMKG model result "
            "to the frozen vacuum class; F2a T-514 scope_use is 'different data class; do not "
            "transfer'."
        ],
        "findings": [
            "Van de Moortel Theorems A/B/C and formal 3.2/3.3/3.4 verified from arXiv:2001.11156v2 "
            "TeX (\\thetheo = \\Alph{theo}); C2-inextendibility and C0-falsity correctly separated in "
            "the shard row W09-011. Only the canonical class_mapping needs correction."
        ],
        "evidence_refs": EVID,
    },
    {
        "event_id": f"w009-refetch-{STAMP}-review-03",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-009",
        "target_id": "ledger/citation_audit.csv:SRC-058",
        "reviewer": "worker-009",
        "verdict": "revise",
        "score": 3,
        "hard_failures": [
            "HF-09-CLASS-01: class_mapping=AF-SCC-C2-VAC-GEN binds a spherical EM-scalar model C2 "
            "result to the frozen vacuum class; schema F2a caveat requires the does_not_imply clauses "
            "to travel with any citation."
        ],
        "findings": [
            "Luk-Oh Part II Theorem 1.1 verified verbatim from arXiv:1702.05716v2 TeX, including "
            "genericity conditions (1) and (2); shard row W09-013 maps to AF-SCC-OTHER-MODELS "
            "correctly. Canonical class_mapping needs correction."
        ],
        "evidence_refs": EVID,
    },
    {
        "event_id": f"w009-refetch-{STAMP}-review-04",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-009",
        "target_id": "ledger/citation_audit_scc_flash-09.csv:W09-002",
        "reviewer": "worker-009",
        "verdict": "revise",
        "score": 2,
        "hard_failures": [
            "HF-09-CLASS-02: class_ids/class_mapping bind the Einstein-Maxwell-scalar C0-falsity "
            "(Dafermos Thm 1.2 / Cor 1.3) to AF-SCC-C0-VAC-GEN; F2b anti_scope registers the "
            "horizon-localized C0 statement as variant CH of the parent class and warns that binding "
            "it to the frozen class is a scope error in the other direction."
        ],
        "findings": [
            "Dafermos Theorem 1.2 and Corollary 1.3 verified verbatim from gr-qc/0307013v3 TeX "
            "(shared theorem counter; chr:givp = Christodoulou CQG 16 (1999) A23-A35). C0-extendible "
            "/ C1-inextendible / C2-not-addressed separation in the shard row is correct; the class "
            "token is not.",
            "Affected canonical rows: SRC-021 and SRC-056 (both class_mapping=AF-SCC-C0-VAC-GEN; "
            "SRC-056 additionally AF-WCC-SCALAR-SPH)."
        ],
        "evidence_refs": EVID,
    },
    {
        "event_id": f"w009-refetch-{STAMP}-review-05",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-009",
        "target_id": "ledger/citation_audit_scc_flash-09.csv:W09-005",
        "reviewer": "worker-009",
        "verdict": "inconclusive",
        "score": 2,
        "hard_failures": [],
        "findings": [
            "Assigned citation 'Eardley-Gundlach' independently confirmed unlocatable: OpenAlex "
            "author-filtered query returns 0; Crossref bibliographic query returns Gundlach-only "
            "works. Nearest verified real work: Eardley-Hirschmann 1995, DOI "
            "10.1103/PhysRevD.51.4198 (OpenAlex HTTP 200). Replacement or removal recommended."
        ],
        "evidence_refs": EVID,
    },
    {
        "event_id": f"w009-refetch-{STAMP}-status-01",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "status": "active",
        "hours": 0.3,
        "summary": (
            "Bounded task asg-2026-09-11-L1-deepseek-flash-09-18 (G-LIT): independent re-fetch spot "
            "check of 5 SCC-class ledger rows against complete arXiv e-print TeX sources. 4/5 "
            "statements and theorem numbers reproduced exactly (Luk-Oh Duke Thm 1.1; Luk-Oh Part II "
            "Thm 1.1; Van de Moortel Thms A/B/C + 3.2/3.3/3.4; Dafermos Thm 1.2/Cor 1.3). Two hard "
            "class-binding failures flagged: frozen vacuum class ids attached to non-vacuum model "
            "results (SRC-025, SRC-058 -> AF-SCC-C2-VAC-GEN; SRC-021/SRC-056 and shard W09-002 -> "
            "AF-SCC-C0-VAC-GEN). Eardley-Gundlach confirmed unresolved."
        ),
        "evidence_refs": EVID,
        "next_falsifier": (
            "Lead-literature merge adjudicates the class_mapping corrections; a further spot check "
            "should re-fetch any corrected row and confirm the class token matches the schema's "
            "variant/anti-scope registry rather than a frozen class id."
        ),
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-LIT",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
    },
]
for e in events:
    validate_event(e)

outbox = ROOT / "comms" / "outbox" / "worker-009.jsonl"
with open(outbox, "a") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")

print(json.dumps({
    "spotcheck_csv": str(csv_path), "spotcheck_sha256": SPOT_SHA,
    "review_json": str(rev_path), "review_sha256": REV_SHA,
    "manifest": str(man_path), "manifest_sha256": MAN_SHA,
    "outbox": str(outbox), "events_written": len(events),
    "canonical_ledger_sha256": CANON_HASH, "shard_sha256": SHARD_HASH,
}, indent=2))
