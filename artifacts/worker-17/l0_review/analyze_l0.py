#!/usr/bin/env python3
"""Independent mechanical analysis of the L0 literature ledger.

Worker-17 (deepseek-flash-17), assignment audit-a1-20260912T0008-l0-w17.
Read-only over canonical artifacts; writes only under artifacts/worker-17/.
Re-implements the class-token, resolution, duplicate, scope-metadata and
self-certification checks from scratch; imports no lead-authored checker.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent

LEDGER = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "ledger" / "theorems.jsonl"
REGISTRY = ROOT / "artifacts" / "literature" / "registry.jsonl"
AUDIT = ROOT / "ledger" / "citation_audit.csv"
UNRESOLVED = ROOT / "artifacts" / "literature" / "unresolved.jsonl"
RUBRIC = ROOT / "evaluation_rubric.yaml"
MANIFEST = ROOT / "artifacts" / "literature" / "MANIFEST.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_classes() -> list[str]:
    txt = RUBRIC.read_text()
    block = txt.split("frozen_classes:", 1)[1].split("\n# ---", 1)[0]
    return re.findall(r"^\s*- id: (AF-[\w-]+)", block, re.M)


def find_field(obj: dict, names: set[str]) -> list[str]:
    return sorted(k for k in obj if k.lower() in names)


def main() -> int:
    report: dict = {
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "worker": "deepseek-flash-17",
        "assignment": "audit-a1-20260912T0008-l0-w17",
        "artifacts_measured": {
            "ledger/theorems.jsonl": sha256(LEDGER),
            "artifacts/literature/registry.jsonl": sha256(REGISTRY),
            "ledger/citation_audit.csv": sha256(AUDIT),
            "artifacts/literature/unresolved.jsonl": sha256(UNRESOLVED),
        },
        "frozen_classes": frozen_classes(),
    }
    led = [json.loads(l) for l in LEDGER.read_text().splitlines() if l.strip()]
    reg = [json.loads(l) for l in REGISTRY.read_text().splitlines() if l.strip()]
    reg_by_id = {r["source_id"]: r for r in reg}
    audit = list(csv.DictReader(AUDIT.open()))
    unresolved_items = [json.loads(l) for l in UNRESOLVED.read_text().splitlines() if l.strip()]
    manifest = json.loads(MANIFEST.read_text())

    frozen = set(report["frozen_classes"])
    findings: list[dict] = []

    # ---- C1 class tokens -------------------------------------------------
    class_rows: dict[str, list[int]] = {}
    extension_tokens: list[dict] = []
    multi_class_rows: list[dict] = []
    missing_class_rows: list[int] = []
    for i, r in enumerate(led, 1):
        cids = r.get("class_ids") or []
        if not cids:
            missing_class_rows.append(i)
        if len(cids) != 1:
            multi_class_rows.append({"line": i, "theorem_id": r.get("theorem_id"), "class_ids": cids})
        for c in cids:
            class_rows.setdefault(c, []).append(i)
            if c not in frozen:
                extension_tokens.append({"line": i, "theorem_id": r.get("theorem_id"), "token": c})
        for c in (r.get("informs_classes") or []):
            class_rows.setdefault("informs:" + c, []).append(i)
            if c not in frozen:
                extension_tokens.append({"line": i, "theorem_id": r.get("theorem_id"), "token": "informs:" + c})
    report["c1_class_tokens"] = {
        "counts": {k: len(v) for k, v in class_rows.items()},
        "extension_tokens": extension_tokens,
        "rows_with_not_exactly_one_class_id": multi_class_rows,
        "rows_missing_class_ids": missing_class_rows,
        "ok": not extension_tokens and not multi_class_rows and not missing_class_rows,
    }

    # ---- C2 source resolution -------------------------------------------
    unresolved_rows: list[dict] = []
    unresolved_ledger_rows: list[int] = []
    null_locator_sources: list[str] = []
    bad_status_sources: list[dict] = []
    reviewer_labels: dict[str, int] = {}
    scope_fields = {"matter_model", "matter", "cosmological_constant", "lambda", "dimension",
                    "symmetry", "formulation", "source_meta", "quantity_check"}
    reg_scope_carriers: list[str] = []
    ledger_scope_carriers: list[int] = []
    for r in reg:
        rev = str(r.get("reviewer"))
        reviewer_labels[rev] = reviewer_labels.get(rev, 0) + 1
        if not (str(r.get("doi") or "").strip() or str(r.get("arxiv_id") or "").strip()
                or str(r.get("url") or "").strip()):
            null_locator_sources.append(r["source_id"])
        if str(r.get("status")) in {"unresolved", "contradicted"}:
            bad_status_sources.append({"source_id": r["source_id"], "status": r["status"]})
        if find_field(r, scope_fields):
            reg_scope_carriers.append(r["source_id"])
    for i, r in enumerate(led, 1):
        sids = r.get("source_ids") or []
        if not sids:
            unresolved_rows.append({"line": i, "theorem_id": r.get("theorem_id"), "reason": "no source_ids"})
        if find_field(r, scope_fields):
            ledger_scope_carriers.append(i)
        miss = [s for s in sids if s not in reg_by_id]
        if miss:
            unresolved_rows.append({"line": i, "theorem_id": r.get("theorem_id"), "missing_source_ids": miss})
        if not (r.get("unresolved") or []):
            unresolved_ledger_rows.append(i)
    report["c2_resolution"] = {
        "ledger_rows": len(led),
        "registry_sources": len(reg),
        "audit_rows": len(audit),
        "rows_with_missing_source_ids": unresolved_rows,
        "rows_with_empty_unresolved_list": unresolved_ledger_rows,
        "sources_without_locator": null_locator_sources,
        "sources_with_unresolved_or_contradicted_status": bad_status_sources,
        "registry_reviewer_labels": reviewer_labels,
        "registry_scope_metadata_carriers": reg_scope_carriers,
        "ledger_scope_metadata_carriers": ledger_scope_carriers,
        "unresolved_registry_file_items": len(unresolved_items),
        "ok_resolution": not unresolved_rows and not null_locator_sources and not bad_status_sources,
        "ok_unresolved_honesty": not unresolved_ledger_rows and len(unresolved_items) > 0,
    }

    # ---- C3 duplicates ---------------------------------------------------
    ids = [r.get("theorem_id") for r in led]
    dupe_ids = sorted({x for x in ids if ids.count(x) > 1})
    stmts = [r.get("statement_exact", "") for r in led]
    dupes_exact = sorted({s for s in stmts if stmts.count(s) > 1})
    near: list[dict] = []
    for a in range(len(led)):
        for b in range(a + 1, len(led)):
            ratio = difflib.SequenceMatcher(None, stmts[a].lower(), stmts[b].lower()).ratio()
            if ratio >= 0.60:
                near.append({"a": led[a]["theorem_id"], "b": led[b]["theorem_id"], "ratio": round(ratio, 3)})
    near.sort(key=lambda x: -x["ratio"])
    report["c3_duplicates"] = {
        "duplicate_theorem_ids": dupe_ids,
        "duplicate_statement_exact": len(dupes_exact),
        "near_duplicate_pairs_ge_0.60": near,
        "ok": not dupe_ids and not dupes_exact and not near,
    }

    # ---- C4 HF-01 / HF-14 / acceptance honesty ---------------------------
    verdict_fields = {"reviewer", "reviewer_verdict", "review_verdict", "reviewed_by",
                      "independent_review", "verdict", "review_id", "review_ref"}
    hash_fields = {"artifact_refs", "artifact_sha256", "sha256", "evidence_hashes"}
    hf01 = [{"line": i, "theorem_id": r.get("theorem_id")} for i, r in enumerate(led, 1)
            if r.get("conclusion_type") == "theorem" and not (r.get("artifact_refs") or [])]
    hf14: list[dict] = []
    accepted_unverified: list[dict] = []
    for i, r in enumerate(led, 1):
        if r.get("status") == "accepted":
            if str(r.get("verification_status")) == "unverified":
                accepted_unverified.append({"line": i, "theorem_id": r.get("theorem_id")})
            if r.get("supports_claim") is True and not find_field(r, verdict_fields) and not find_field(r, hash_fields):
                hf14.append({"line": i, "theorem_id": r.get("theorem_id"),
                             "verification_status": r.get("verification_status")})
    report["c4_acceptance"] = {
        "hf01_theorem_without_artifact_refs": {"count": len(hf01), "rows": hf01},
        "hf14_self_certified_acceptance": {"count": len(hf14), "rows": hf14},
        "accepted_with_verification_status_unverified": {"count": len(accepted_unverified), "rows": accepted_unverified},
    }

    # ---- C5 evidence depth vs verification_status ------------------------
    depth_rows: list[dict] = []
    for i, r in enumerate(led, 1):
        srcs = [reg_by_id[s] for s in (r.get("source_ids") or []) if s in reg_by_id]
        types = {(s.get("verification") or {}).get("evidence_type") for s in srcs}
        if r.get("status") == "accepted" and types and types <= {"metadata"}:
            depth_rows.append({"line": i, "theorem_id": r.get("theorem_id"),
                               "verification_status": r.get("verification_status"),
                               "source_evidence_types": sorted(t for t in types if t)})
    accepted = [r for r in led if r.get("status") == "accepted"]
    api_only = 0
    for r in accepted:
        srcs = [reg_by_id[s] for s in (r.get("source_ids") or []) if s in reg_by_id]
        if srcs and all(s.get("status") == "verified-api" for s in srcs):
            api_only += 1
    report["c5_evidence_depth"] = {
        "accepted_rows": len(accepted),
        "accepted_abstract_read": sum(1 for r in accepted if r.get("verification_status") == "abstract-read"),
        "accepted_all_sources_verified_api": api_only,
        "accepted_with_only_metadata_evidence": depth_rows,
        "audit_evidence_type_counts": {k: sum(1 for a in audit if a.get("evidence_type") == k)
                                       for k in sorted({a.get("evidence_type") for a in audit})},
    }

    # ---- C6 quantity_check presence for quantitative statements ----------
    quant_pat = re.compile(r"(exponent|rate|codimension|decay|power|Mass|charge|"
                           r"\b\d+(\.\d+)?\s*(%|percent)|\^\{?-?\d|\bO\(|"
                           r"subextremal|extremal)", re.I)
    narrow_pat = re.compile(r"(codimension|exponent|power[- ]law|O\(t|blow[- ]?up rate|"
                            r"decay rate|Price[- ]law|rate O\()", re.I)
    quant_rows = [i for i, r in enumerate(led, 1) if quant_pat.search(r.get("statement_exact", ""))]
    narrow_rows = [i for i, r in enumerate(led, 1) if narrow_pat.search(r.get("statement_exact", ""))]
    has_qc = [i for i, r in enumerate(led, 1) if find_field(r, {"quantity_check"})]
    reg_qc = [r["source_id"] for r in reg if find_field(r, {"quantity_check"})]
    audit_cols = set(audit[0].keys()) if audit else set()
    report["c6_quantity_check"] = {
        "rows_with_quantitative_tokens": len(quant_rows),
        "rows_with_explicit_rate_exponent_codimension_tokens": {
            "count": len(narrow_rows),
            "rows": [{"line": i, "theorem_id": led[i - 1].get("theorem_id")} for i in narrow_rows],
        },
        "ledger_rows_with_quantity_check_field": has_qc,
        "registry_rows_with_quantity_check_field": reg_qc,
        "audit_has_quantity_check_column": "quantity_check" in audit_cols,
        "audit_columns": sorted(audit_cols),
    }

    # ---- C7 manifest cross-check ----------------------------------------
    report["c7_manifest_crosscheck"] = {
        "manifest_ledger_hash": manifest["artifacts"]["ledger/theorems.jsonl"],
        "measured_ledger_hash": report["artifacts_measured"]["ledger/theorems.jsonl"],
        "manifest_registry_hash": manifest["artifacts"]["artifacts/literature/registry.jsonl"],
        "measured_registry_hash": report["artifacts_measured"]["artifacts/literature/registry.jsonl"],
        "manifest_counts": manifest["counts"],
        "ledger_row_count": len(led),
        "status_counts": {s: sum(1 for r in led if r.get("status") == s) for s in {r.get("status") for r in led}},
        "class_coverage": {k: len(v) for k, v in class_rows.items() if not k.startswith("informs:")},
    }

    (OUT / "l0_analysis.json").write_text(json.dumps(report, indent=1) + "\n")
    (OUT / f"l0_analysis_{report['artifacts_measured']['ledger/theorems.jsonl'][:12]}.json").write_text(
        json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("artifacts_measured", "frozen_classes")}, indent=1))
    for key in ("c1_class_tokens", "c2_resolution", "c3_duplicates", "c4_acceptance",
                "c5_evidence_depth", "c6_quantity_check", "c7_manifest_crosscheck"):
        print("==", key, "==")
        s = json.dumps(report[key])
        print(s[:1400])
    print("wrote", OUT / "l0_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
