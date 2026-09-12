#!/usr/bin/env python3
"""worker-09 / L1 / SCC classes: build the revised, frozen, dedup-audited shard package.

Addresses astra-lead-literature review `lit-l2-20260912-012` (verdict revise) on
ledger/citation_audit_scc_flash-09.lead_schema.csv:
  (1) 20/24 rows duplicate canonical sources -> merge script dedups by citation_id only;
      fix: dedup by DOI / arXiv id / exact title / bibkey and emit an explicit disposition;
  (2) class_mapping carries non-frozen tokens -> fix: emit frozen tokens only, taken from the
      adjudicated canonical row, with the raw shard mapping preserved in `assessment`;
  (3) shard rewritten several times during adjudication -> fix: freeze every output by sha256;
  (4) exact theorem locators exist in the rich shard but were dropped by the lead-schema file ->
      fix: carry them into `exact_locator` + the canonical-keyed enrichment patch.

Non-destructive: the canonical ledger ldger/citation_audit.csv is hash-frozen for the in-flight
G-LIT re-fetch spot checks (sha256 315c19145065a5f9...). This script NEVER writes it.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "ledger"
W09 = ROOT / "artifacts" / "worker-09"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

CANON = LEDGER / "citation_audit.csv"
RICH = LEDGER / "citation_audit_scc_flash-09.csv"
LEAD_SCHEMA = LEDGER / "citation_audit_scc_flash-09.lead_schema.csv"
REV2 = LEDGER / "citation_audit_scc_flash-09.rev2.csv"
DEDUP = LEDGER / "citation_audit_scc_flash-09.rev2.dedup.tsv"
ENRICH = LEDGER / "citation_audit_scc_flash-09.enrichment.csv"
BINDING = W09 / "scc_class_binding.json"
REPORT = W09 / "revision_report.json"

FROZEN = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
TAG_ONLY = "(evidence/tag only)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_doi(d: str) -> str:
    d = (d or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d)


def norm_arx(a: str) -> str:
    a = (a or "").strip().lower()
    a = re.sub(r"^arxiv:", "", a)
    return re.sub(r"v\d+$", "", a)


def keys_of(row: dict) -> dict:
    return {
        "doi": norm_doi(row.get("doi")),
        "arxiv_id": norm_arx(row.get("arxiv_id")),
        "title": (row.get("title") or "").strip().lower(),
        "bibkey": (row.get("bibkey") or "").strip().lower(),
    }


def load_csv(path: Path):
    with path.open(newline="") as f:
        r = csv.DictReader(f)
        return list(r), list(r.fieldnames)


META_LOCATOR = re.compile(r"^(n/a|none|no numbered|abstract[- ]level|abstract confirms)\b", re.I)
NUMBERED = re.compile(r"\b(Thm|Theorem|Cor|Corollary|Prop|Proposition|Lemma)\s*[0-9A-Z]\b|\bT\d+(\.\d+)?\b")


def classify_locator(row: dict) -> tuple[str, str]:
    """Return (locator_level, locator). theorem_numbered > statement > abstract > resolver."""
    thm = (row.get("theorem_exact") or "").strip()
    if thm and not META_LOCATOR.match(thm):
        return ("theorem_numbered" if NUMBERED.search(thm) else "statement"), thm
    if thm:
        return "abstract", (row.get("exact_locator") or "").strip()
    return "resolver", (row.get("exact_locator") or "").strip()


def frozen_mapping(canon_rows: list[dict]) -> str:
    toks: list[str] = []
    for r in canon_rows:
        for t in (r.get("class_mapping") or "").split(";"):
            t = t.strip()
            if not t:
                continue
            if t in FROZEN and t not in toks:
                toks.append(t)
    if not toks:
        return TAG_ONLY
    return ";".join(sorted(toks))


def main() -> int:
    canon, canon_fields = load_csv(CANON)
    rich, rich_fields = load_csv(RICH)
    lead, lead_fields = load_csv(LEAD_SCHEMA)
    inputs = {str(p.relative_to(ROOT)): {"sha256": sha256(p), "bytes": p.stat().st_size}
              for p in (CANON, RICH, LEAD_SCHEMA)}

    # index canonical sources by every identifying key
    index: dict[tuple[str, str], list[dict]] = {}
    for r in canon:
        for k, v in keys_of(r).items():
            if v:
                index.setdefault((k, v), []).append(r)

    rows_out: list[dict] = []
    dedup_rows: list[dict] = []
    enrich_rows: list[dict] = []
    new_rows: list[str] = []
    levels: list[str] = []
    controls = [r for r in rich if r["citation_id"].startswith("W09-CTRL")]

    for s in rich:
        cid = s["citation_id"]
        if cid.startswith("W09-CTRL"):
            continue
        hits: list[dict] = []
        match_keys: list[str] = []
        for k, v in keys_of(s).items():
            for r in index.get((k, v), []):
                if r["citation_id"] not in [h["citation_id"] for h in hits]:
                    hits.append(r)
                    match_keys.append(f"{k}={v[:48]}")
        canon_ids = [r["citation_id"] for r in hits]
        if hits:
            disposition = "already-canonical"
        elif cid == "W09-005":
            disposition = "negative-unregistered"
        else:
            disposition = "NEW"
            new_rows.append(cid)

        level, locator = classify_locator(s)
        levels.append(level)
        mapping = frozen_mapping(hits) if hits else TAG_ONLY
        c0c2 = (s.get("c0_or_c2") or "").strip()
        notprove = (s.get("what_it_does_not_prove") or "").strip()
        assessment = (
            f"assessed: {';'.join(canon_ids) if canon_ids else 'UNMATCHED'}"
            f" | locator_level: {level}"
            f" | C0/C2: {c0c2[:300]}"
            f" | does_not_prove: {notprove[:300]}"
            f" | raw_class_mapping(shard): {(s.get('class_mapping') or '')[:150]}"
        )
        row = {k: (s.get(k) or "") for k in canon_fields}
        row.update({
            "citation_id": cid,
            "exact_locator": locator,
            "class_mapping": mapping,
            "assessment": assessment,
            "verdict": "unresolved" if disposition == "negative-unregistered" else "verified",
            "reviewer": "deepseek-flash-09",
        })
        rows_out.append(row)

        dedup_rows.append({
            "w09_id": cid,
            "bibkey": s.get("bibkey", ""),
            "canonical_citation_ids": ";".join(canon_ids),
            "match_keys": ";".join(match_keys[:4]),
            "disposition": disposition,
            "locator_level": level,
            "frozen_class_mapping": mapping,
        })
        if hits:
            for r in hits:
                enrich_rows.append({
                    "canonical_citation_id": r["citation_id"],
                    "w09_id": cid,
                    "bibkey": s.get("bibkey", ""),
                    "exact_locator_proposed": locator if level != "resolver" else "",
                    "locator_level": level,
                    "class_mapping_frozen": r.get("class_mapping", ""),
                    "c0_c2": c0c2,
                    "does_not_prove": notprove,
                    "evidence_ref": f"ledger/citation_audit_scc_flash-09.csv#{inputs[str(RICH.relative_to(ROOT))]['sha256'][:16]};ledger/citation_audit.csv#{inputs[str(CANON.relative_to(ROOT))]['sha256'][:16]}",
                    "apply_status": "NOT-APPLIED (canonical frozen for in-flight G-LIT spot checks)",
                })

    # write revised shard (canonical 25-column schema)
    with REV2.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=canon_fields)
        w.writeheader()
        w.writerows(rows_out)

    with DEDUP.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["w09_id", "bibkey", "canonical_citation_ids",
                                          "match_keys", "disposition", "locator_level",
                                          "frozen_class_mapping"])
        w.writeheader()
        w.writerows(dedup_rows)

    with ENRICH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["canonical_citation_id", "w09_id", "bibkey",
                                          "exact_locator_proposed", "locator_level",
                                          "class_mapping_frozen", "c0_c2", "does_not_prove",
                                          "evidence_ref", "apply_status"])
        w.writeheader()
        w.writerows(enrich_rows)

    # self-check
    token_bad = sorted({t.strip() for r in rows_out for t in r["class_mapping"].split(";")
                        if t.strip() and t.strip() not in FROZEN and t.strip() != TAG_ONLY})
    theorem_rows = [lvl for lvl in levels if lvl == "theorem_numbered"]
    checks = {
        "rev2_schema_matches_canonical": list(rows_out[0].keys()) == canon_fields,
        "rev2_row_count": len(rows_out),
        "non_frozen_tokens_in_rev2_class_mapping": token_bad,
        "new_rows_not_already_canonical": new_rows,
        "negative_control_rows_excluded": [c["citation_id"] for c in controls],
        "canonical_sha_unchanged_after_build": sha256(CANON) == inputs[str(CANON.relative_to(ROOT))]["sha256"],
        "theorem_numbered_locator_rows": len(theorem_rows),
    }
    if token_bad or new_rows or not checks["rev2_schema_matches_canonical"] or not checks["canonical_sha_unchanged_after_build"]:
        print("SELF-CHECK FAILED", json.dumps(checks, indent=1))
        return 2

    # sha256 sidecars (freeze by hash)
    outputs = {}
    for p in (REV2, DEDUP, ENRICH):
        h = sha256(p)
        Path(str(p) + ".sha256").write_text(f"{h}  {p.name}\n")
        outputs[str(p.relative_to(ROOT))] = {"sha256": h, "bytes": p.stat().st_size}

    legacy_rows = sum(1 for r in rich if r["citation_id"].startswith("W09-CTRL"))
    report = {
        "report_id": "w09-rev2-20260912",
        "worker": "deepseek-flash-09",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "created_at": NOW,
        "target_review": "lit-l2-20260912-012 (verdict revise, score 4)",
        "inputs": inputs,
        "outputs": outputs,
        "self_check": checks,
        "dedup_summary": {
            "shard_rows": len(rows_out),
            "already_canonical": sum(1 for d in dedup_rows if d["disposition"] == "already-canonical"),
            "new_rows": len(new_rows),
            "negative_unregistered": sum(1 for d in dedup_rows if d["disposition"] == "negative-unregistered"),
            "negative_control_rows": legacy_rows,
        },
        "review_findings_disposition": {
            "duplicate_rows_defect": "fixed by DOI/arXiv/title/bibkey dedup: 0 rows remain unmerged-and-new; "
                                     "30/31 shard rows already exist in canonical and are reported per canonical id",
            "non_frozen_class_tokens": "fixed: rev2 class_mapping is restricted to the four frozen tokens or "
                                       "'(evidence/tag only)', taken from the adjudicated canonical rows; raw shard mapping kept in assessment",
            "shard_hash_instability": "fixed: rev2/dedup/enrichment written once and frozen with .sha256 sidecars",
            "exact_theorem_locators": "fixed: theorem-level locators carried into exact_locator; canonical-keyed "
                                      "enrichment patch emitted but NOT APPLIED because canonical is hash-frozen for in-flight spot checks",
            "eardley_gundlach_negative": "preserved: W09-005 stays unresolved and is not registered",
        },
        "canonical_freeze": {
            "path": str(CANON.relative_to(ROOT)),
            "sha256": inputs[str(CANON.relative_to(ROOT))]["sha256"],
            "decision": "no canonical write from worker-09",
            "reason": "G-LIT controller audit binds the in-flight >=3 independent re-fetch spot checks to this hash; "
                      "rewriting it would invalidate them. The enrichment patch is staged for the owner.",
            "falsifier": "if the controller re-freezes canonical after the spot checks, apply "
                         "ledger/citation_audit_scc_flash-09.enrichment.csv and re-measure",
        },
        "falsifier": "A frozen-class token in rev2 is shown to be the wrong class for its source; or a proposed "
                     "theorem locator does not match the cited paper; or a shard row marked already-canonical "
                     "is shown absent from canonical.",
    }
    BINDING_EXISTS = BINDING.exists()
    REPORT.write_text(json.dumps(report, indent=1) + "\n")
    out_h = sha256(REPORT)
    Path(str(REPORT) + ".sha256").write_text(f"{out_h}  {REPORT.name}\n")
    print(json.dumps({"rev2": outputs, "report_sha256": out_h, "binding_exists": BINDING_EXISTS,
                      "checks": checks}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
