#!/usr/bin/env python3
"""Build ledger/class_coverage.csv from the L0 theorem ledger (worker flash-10, node L1).

Assignment (astra/asg-2026-09-11-L1-deepseek-flash-10-19):
  "Map each ledger source to the 4 classes; empty cells are the interesting output."
  acceptance: source x class matrix with covered/partial/none and the exact theorem that covers it.

Inputs (read-only):
  ledger/theorems.jsonl                     -- L0 ledger (theorem_id, source_ids, class_ids, ...)
  ledger/citation_audit.csv                 -- L1 source registry (source_id, title, status, ...)
  artifacts/literature/registry.jsonl       -- fallback source metadata
  artifacts/flash-10/l1_class_coverage/sources.json -- flash-10 verified arXiv locators (cross-check)

Output:
  ledger/class_coverage.csv                 -- one row per (source_id, frozen class)
  artifacts/flash-10/l1_class_coverage/coverage_summary.json

Coverage rule (documented in README.md):
  covered     : >=1 accepted ledger entry binds the source to the class with
                entry_kind in {theorem, counterexample_candidate} and
                conclusion_type in {theorem, counterexample}.
  partial     : the source is bound to the class, but only through conjecture/definition/
                review/numerical evidence/stability/conditional/preprint/provisional entries.
  none        : the source is in the ledger registry but no entry binds it to this class
                (includes sources bound only to non-frozen classes -- leakage control).
  unassessed  : the source has no ledger entry at all, so no class assessment is possible.
                'none' would assert a negative that was never checked.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
AUDIT = ROOT / "ledger" / "citation_audit.csv"
REGISTRY = ROOT / "artifacts" / "literature" / "registry.jsonl"
OUT_CSV = ROOT / "ledger" / "class_coverage.csv"
SUMMARY = HERE / "coverage_summary.json"

CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
OTHER_CLASSES = ["DEFINITIONS", "AF-SCC-OTHER-MODELS", "AF-WCC-VAC-BH-FORM", "AF-WCC-VAC-NS-CONSTR"]
CT_RANK = {"theorem": 0, "counterexample": 1, "conditional_theorem": 2, "stability_result": 3,
           "numerical_evidence": 4, "formal_model": 5, "open_problem": 6}
EK_RANK = {"theorem": 0, "counterexample_candidate": 1, "preprint_result": 2, "conditional_theorem": 3,
           "stability_result": 4, "numerical_evidence": 5, "definition": 6, "review": 7,
           "conjecture": 8, "literature_status": 9, "methodological_finding": 10, "unresolved_candidate": 11}
COVERED_KINDS = {"theorem", "counterexample_candidate"}
COVERED_CONCLUSIONS = {"theorem", "counterexample"}

COLUMNS = ["row_id", "source_id", "citation", "authors", "year", "venue", "doi", "arxiv_id", "url",
           "audit_status", "audit_verdict", "class_id", "coverage", "role", "theorem_ids",
           "conclusion_types", "entry_kinds", "strongest_conclusion_type", "exact_theorem",
           "theorem_locator", "genericity", "regularity", "assumptions", "scope_flags", "falsifier",
           "evidence_basis", "verification_status", "ledger_bound_classes", "registry_crosscheck",
           "notes"]

FLAG_PATTERNS = {
    "spherical_symmetry": r"spherical|spherically symmetric",
    "charged_maxwell": r"\bmaxwell\b|charged|\bcharge\b|reissner",
    "cosmological_constant": r"cosmological constant|de sitter|flrw|kasner|big bang|\blambda\b",
    "extra_matter": r"scalar field|klein-gordon|dirac|yang-mills|skyrme|electromagnetic field",
    "linear_only": r"\blinear\b",
}


def scope_flags(text: str) -> str:
    return " | ".join(k for k, pat in FLAG_PATTERNS.items() if re.search(pat, text, re.I)) or "none"


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def toks(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower())
            if t not in {"the", "a", "an", "of", "and", "in", "on", "for", "to", "with", "by"}}


def strength(t: dict) -> tuple:
    covered = (t.get("status") == "accepted" and t.get("entry_kind") in COVERED_KINDS
               and t.get("conclusion_type") in COVERED_CONCLUSIONS)
    return (0 if covered else 1,
            CT_RANK.get(t.get("conclusion_type"), 9),
            EK_RANK.get(t.get("entry_kind"), 12),
            0 if t.get("status") == "accepted" else 1,
            t.get("theorem_id", ""))


def main() -> int:
    thms = load_jsonl(THEOREMS)
    audit_rows = list(csv.DictReader(AUDIT.open(newline="")))
    registry = {r["source_id"]: r for r in load_jsonl(REGISTRY)}
    flash_reg = json.loads((HERE / "sources.json").read_text())

    # flash-10 title -> arxiv locator, for cross-check only
    flash_titles = []
    for s in flash_reg["sources"]:
        sel = s.get("selected")
        if sel:
            flash_titles.append((toks(sel["title"]), sel["arxiv_id"], sel["title"]))

    by_source: dict[str, list[dict]] = {}
    for t in thms:
        for sid in t.get("source_ids", []):
            by_source.setdefault(sid, []).append(t)

    rows = []
    for a in sorted(audit_rows, key=lambda r: r["citation_id"]):
        sid = a["citation_id"]
        entries = by_source.get(sid, [])
        bound = sorted({c for t in entries for c in t.get("class_ids", [])})
        bound_frozen = [c for c in bound if c in CLASSES]
        bound_other = [c for c in bound if c not in CLASSES]
        meta = registry.get(sid, {})
        authors = a.get("authors") or " | ".join(meta.get("authors", []))
        citation = f"{authors}. {a.get('title', '')}."
        year, venue = a.get("year", ""), a.get("venue", "")
        doi = a.get("doi", "") if a.get("doi") not in ("", "-") else ""
        arxiv = a.get("arxiv_id", "") if a.get("arxiv_id") not in ("", "-") else ""
        url = a.get("url", "")
        # cross-check with flash-10 registry by title
        cross = ""
        if not arxiv:
            tt = toks(a.get("title", ""))
            for ftoks, fid, ftitle in flash_titles:
                if tt and ftoks and len(tt & ftoks) / len(tt) >= 0.8:
                    cross = f"flash-10 registry match {fid}: {ftitle}"
                    if not arxiv:
                        arxiv = fid
                    break
        elif cross == "":
            cross = "audit provides locator"

        for cls in CLASSES:
            hits = [t for t in entries if cls in t.get("class_ids", [])]
            if not entries:
                rows.append(dict(row_id="", source_id=sid, citation=citation, authors=authors, year=year,
                                 venue=venue, doi=doi, arxiv_id=arxiv, url=url,
                                 audit_status=a.get("status", ""), audit_verdict=a.get("verdict", ""),
                                 class_id=cls, coverage="unassessed", role="unresolved_mapping",
                                 theorem_ids="", conclusion_types="", entry_kinds="",
                                 strongest_conclusion_type="not_applicable", exact_theorem="",
                                 theorem_locator="n/a", genericity="", regularity="", assumptions="", scope_flags="none",
                                 falsifier=("Map this source to at least one ledger theorem entry and re-run; "
                                            "if it cannot be mapped, class coverage cannot be assessed."),
                                 evidence_basis="registry_only_unmapped",
                                 verification_status=f"audit:{a.get('status','')}",
                                 ledger_bound_classes="(no ledger entry)",
                                 registry_crosscheck=cross,
                                 notes="unassessed: source has zero ledger theorem entries (mapping gap, not a coverage judgement)."))
                continue
            if not hits:
                note = ("empty cell: source is referenced by the ledger but never bound to this class"
                        + (f"; bound classes: {', '.join(bound)}" if bound else "; no class binding at all")
                        + (f" [non-frozen classes: {', '.join(bound_other)}]" if bound_other else ""))
                rows.append(dict(row_id="", source_id=sid, citation=citation, authors=authors, year=year,
                                 venue=venue, doi=doi, arxiv_id=arxiv, url=url,
                                 audit_status=a.get("status", ""), audit_verdict=a.get("verdict", ""),
                                 class_id=cls, coverage="none", role="out_of_class", theorem_ids="",
                                 conclusion_types="", entry_kinds="", strongest_conclusion_type="not_applicable",
                                 exact_theorem="", theorem_locator="n/a", genericity="", regularity="",
                                 assumptions="", scope_flags="none", falsifier="", evidence_basis="ledger_absence",
                                 verification_status=f"audit:{a.get('status','')}",
                                 ledger_bound_classes=" | ".join(bound) or "(none)",
                                 registry_crosscheck=cross, notes=note))
                continue

            best = sorted(hits, key=strength)[0]
            covered = any(strength(t)[0] == 0 for t in hits)
            coverage = "covered" if covered else "partial"
            cts = sorted({t.get("conclusion_type", "") for t in hits})
            eks = sorted({t.get("entry_kind", "") for t in hits})
            if any(t.get("conclusion_type") == "counterexample" for t in hits):
                role = "falsifier"
            elif best.get("entry_kind") == "definition":
                role = "definition"
            elif best.get("conclusion_type") == "open_problem":
                role = "open_problem"
            elif best.get("conclusion_type") == "numerical_evidence":
                role = "numerical_evidence"
            elif best.get("conclusion_type") in {"conditional_theorem", "stability_result"}:
                role = "supporting_conditional"
            else:
                role = "supporting"
            flags = scope_flags(" ".join([best.get("statement_exact") or "",
                                          " ".join(best.get("assumptions") or []),
                                          best.get("genericity") or ""]))
            fals = [f for t in hits for f in (t.get("falsifiers") or [])][:2]
            rows.append(dict(row_id="", source_id=sid, citation=citation, authors=authors, year=year,
                             venue=venue, doi=doi, arxiv_id=arxiv, url=url,
                             audit_status=a.get("status", ""), audit_verdict=a.get("verdict", ""),
                             class_id=cls, coverage=coverage, role=role,
                             theorem_ids=" | ".join(t.get("theorem_id", "") for t in hits),
                             conclusion_types=" | ".join(cts), entry_kinds=" | ".join(eks),
                             strongest_conclusion_type=best.get("conclusion_type", ""),
                             exact_theorem=(best.get("statement_exact") or "").strip(),
                             theorem_locator=f"ledger {best.get('theorem_id','')}"
                                             + (f" (strongest of {len(hits)})" if len(hits) > 1 else ""),
                             genericity=(best.get("genericity") or "").strip(),
                             regularity=(best.get("regularity") or "").strip(),
                             assumptions=" | ".join((best.get("assumptions") or [])[:3]),
                             scope_flags=flags,
                             falsifier=" | ".join(fals),
                             evidence_basis="ledger_theorem" + ("_covered" if covered else "_partial"),
                             verification_status=f"audit:{a.get('status','')}",
                             ledger_bound_classes=" | ".join(bound),
                             registry_crosscheck=cross,
                             notes=("covered by accepted ledger entry " + ", ".join(t.get("theorem_id", "") for t in hits)
                                    if covered else
                                    "partial: binding exists only at strength {"
                                    + ", ".join(cts) + "} / kinds {" + ", ".join(eks) + "}")))

    for i, r in enumerate(rows, 1):
        r["row_id"] = f"CC-{i:04d}"

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    tmp_csv = OUT_CSV.with_suffix(".csv.tmp-w10")
    with tmp_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    tmp_csv.replace(OUT_CSV)  # atomic: readers never see a partial matrix

    summary = {"csv": str(OUT_CSV.relative_to(ROOT)), "rows": len(rows),
               "ledger_theorems": len(thms), "audit_sources": len(audit_rows),
               "inputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in [THEOREMS, AUDIT, REGISTRY, HERE / "sources.json"]},
               "frozen_classes": CLASSES, "classes": {}, "coverage_totals": {},
               "zero_covered_classes": [], "unassessed_sources": [],
               "nonfrozen_binding_sources": {}, "scope_flag_review_queue": []}
    for cls in CLASSES:
        sub = [r for r in rows if r["class_id"] == cls]
        counts = {c: sum(1 for r in sub if r["coverage"] == c)
                  for c in ["covered", "partial", "none", "unassessed"]}
        summary["classes"][cls] = counts
        summary["classes"][cls]["covered_sources"] = [r["source_id"] for r in sub if r["coverage"] == "covered"]
        if counts["covered"] == 0:
            summary["zero_covered_classes"].append(cls)
    for c in ["covered", "partial", "none", "unassessed"]:
        summary["coverage_totals"][c] = sum(1 for r in rows if r["coverage"] == c)
    summary["unassessed_sources"] = sorted({r["source_id"] for r in rows if r["coverage"] == "unassessed"})
    for r in rows:
        if r["coverage"] == "none" and r["ledger_bound_classes"] not in ("", "(none)"):
            extra = [c for c in r["ledger_bound_classes"].split(" | ") if c not in CLASSES]
            if extra:
                summary["nonfrozen_binding_sources"].setdefault(r["source_id"], extra)
    for r in rows:
        if r["coverage"] in {"covered", "partial"} and r["scope_flags"] != "none":
            fl = set(r["scope_flags"].split(" | "))
            conflict = bool(fl & {"charged_maxwell", "cosmological_constant"}) or \
                (r["class_id"].startswith("AF-") and r["class_id"].endswith("VAC-GEN") and "extra_matter" in fl)
            if conflict:
                summary["scope_flag_review_queue"].append(
                    {"source_id": r["source_id"], "class_id": r["class_id"], "coverage": r["coverage"],
                     "scope_flags": r["scope_flags"], "theorem_ids": r["theorem_ids"]})
    tmp_sum = SUMMARY.with_suffix(".json.tmp-w10")
    tmp_sum.write_text(json.dumps(summary, indent=2) + "\n")
    tmp_sum.replace(SUMMARY)

    print(f"wrote {OUT_CSV} ({len(rows)} rows = {len(audit_rows)} sources x {len(CLASSES)} classes)")
    print(f"coverage totals: {summary['coverage_totals']}")
    for cls in CLASSES:
        c = summary["classes"][cls]
        print(f"  {cls:20s} covered={c['covered']:3d} partial={c['partial']:3d} "
              f"none={c['none']:3d} unassessed={c['unassessed']:3d}  "
              f"covered_sources={len(c['covered_sources'])}")
    print(f"classes with ZERO covered cells: {summary['zero_covered_classes']}")
    print(f"sources with no ledger mapping: {summary['unassessed_sources']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
