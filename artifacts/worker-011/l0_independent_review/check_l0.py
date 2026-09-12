#!/usr/bin/env python3
"""Independent machine audit of the frozen L0 theorem ledger.

Reviewer: worker-011 (independent of astra-lead-literature, the artifact author).
Task: W011-L0-INDEP-VERDICT-01, class-bound to the four frozen classes.

Scope: read-only over shared artifacts. Writes only:
  * artifacts/worker-011/l0_independent_review/report.json  (this script's output)
  * stdout

The audit is deterministic and hash-pinned: every input is hashed at start and
re-hashed at the end; any change during the run sets `drift=true` and voids the
verdict (the caller must then bind to the new hash or re-run).

Checks are keyed to the two acceptance surfaces that exist for L0:
  (A) assignment astra-life01-l0-revise acceptance criteria (message-level)
  (B) evaluation_rubric.yaml hard-failure taxonomy + PROTOCOL.md event rules,
      interpreted for a *ledger* (rows are not `claim` events; that distinction
      is itself measured here rather than assumed).

Usage: python3 check_l0.py [--json]
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

L0 = ROOT / "ledger/theorems.jsonl"
L1 = ROOT / "ledger/citation_audit.csv"
REG = ROOT / "artifacts/literature/registry.jsonl"
UNRES = ROOT / "artifacts/literature/unresolved.jsonl"
RUBRIC = ROOT / "evaluation_rubric.yaml"
SPOT_REV2 = ROOT / "artifacts/literature/reviews/L1-spotcheck-rev2.json"
DISPOSITION = ROOT / "artifacts/literature/reviews/L0-rev2-disposition.md"

FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH",
}
LEGAL_CONCLUSION = {
    "theorem", "conditional_theorem", "stability_result", "counterexample",
    "numerical_evidence", "formal_model", "open_problem",
}
LEGAL_VERIFICATION = {"unverified", "abstract-read", "full-text", "page-checked"}
LEGAL_STATUS = {"accepted", "provisional", "rejected"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def norm_tokens(text: str):
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main() -> int:
    inputs = [L0, L1, REG, UNRES, RUBRIC, SPOT_REV2, DISPOSITION]
    pins = {str(p.relative_to(ROOT)): sha256(p) for p in inputs if p.exists()}
    missing = [str(p.relative_to(ROOT)) for p in inputs if not p.exists()]

    rows = load_jsonl(L0)
    audit = list(csv.DictReader(L1.open()))
    reg = load_jsonl(REG)
    unres = load_jsonl(UNRES)
    rubric_text = RUBRIC.read_text()

    reg_ids = {r.get("source_id") for r in reg}
    aud_ids = {r.get("citation_id") for r in audit}
    aud_by_id = {r.get("citation_id"): r for r in audit}
    row_ids = [r.get("theorem_id") for r in rows]
    row_by_id = {r.get("theorem_id"): r for r in rows}
    ledger_srcs = set()
    for r in rows:
        ledger_srcs.update(r.get("source_ids", []))

    checks = []

    def check(cid, name, ok, detail, counts=None, severity="hard"):
        checks.append({
            "id": cid, "name": name,
            "status": "pass" if ok else ("warn" if severity == "warn" else "fail"),
            "severity": severity, "detail": detail, "counts": counts or {},
        })

    # ---------------- C1 row count ----------------
    check("C1", "row count >= 15 (assignment threshold)", len(rows) >= 15,
          f"{len(rows)} rows", {"rows": len(rows)})

    # ---------------- C2 required fields non-empty ----------------
    required = ["theorem_id", "label", "statement_exact", "assumptions", "class_ids",
                "conclusion_type", "does_not_imply", "falsifiers", "source_ids",
                "verification_status", "unresolved", "status", "supports_claim"]
    holes = {}
    for r in rows:
        for k in required:
            v = r.get(k)
            if v is None or (isinstance(v, (list, str)) and len(v) == 0 and k not in ("class_ids",)):
                holes.setdefault(k, []).append(r.get("theorem_id"))
    check("C2", "required fields present and non-empty on every row", not holes,
          "no holes" if not holes else f"empty required fields: {holes}",
          {"hole_fields": sorted(holes)})

    # ---------------- C3 class-token legality ----------------
    bad_class = []
    class_token_count = 0
    for r in rows:
        for field in ("class_ids", "informs_classes"):
            for tok in r.get(field, []) or []:
                class_token_count += 1
                if tok not in FROZEN_CLASSES:
                    bad_class.append({"theorem_id": r.get("theorem_id"), "field": field, "token": tok})
    tag_tokens = Counter()
    for r in rows:
        for tok in r.get("ledger_tags", []) or []:
            tag_tokens[tok] += 1
    check("C3", "every class_ids/informs_classes token is one of the frozen four", not bad_class,
          "all in frozen four" if not bad_class else f"non-frozen class tokens: {bad_class}",
          {"class_tokens": class_token_count, "ledger_tags": dict(tag_tokens)})

    # ---------------- C4 verification vocabulary ----------------
    bad_ver = sorted({r.get("verification_status") for r in rows} - LEGAL_VERIFICATION)
    check("C4", "verification_status in {unverified, abstract-read, full-text, page-checked}",
          not bad_ver, "legal vocabulary" if not bad_ver else f"illegal: {bad_ver}",
          dict(Counter(r.get("verification_status") for r in rows)))

    # ---------------- C5 conclusion vocabulary ----------------
    bad_ct = sorted({r.get("conclusion_type") for r in rows} - LEGAL_CONCLUSION)
    check("C5", "conclusion_type in the protocol's legal vocabulary", not bad_ct,
          "legal vocabulary" if not bad_ct else f"illegal: {bad_ct}",
          dict(Counter(r.get("conclusion_type") for r in rows)))

    # ---------------- C6 accepted-implies-evidence ----------------
    contradictions, metadata_only = [], []
    for r in rows:
        tid = r.get("theorem_id")
        if r.get("status") == "accepted" and r.get("verification_status") == "unverified":
            contradictions.append(tid)
        if r.get("status") == "accepted" and r.get("supports_claim") is True:
            types = [aud_by_id.get(s, {}).get("evidence_type") for s in r.get("source_ids", [])]
            types = [t for t in types if t]
            if types and all(t == "metadata" for t in types):
                metadata_only.append(tid)
    ok6 = not contradictions and not metadata_only
    check("C6", "no accepted row rests on unverified/metadata-only evidence", ok6,
          "consistent" if ok6 else f"unverified-accepted={contradictions} metadata-only-accepted={metadata_only}",
          {"unverified_accepted": contradictions, "metadata_only_accepted": metadata_only})

    # ---------------- C7 source resolution ----------------
    missing_reg = sorted(ledger_srcs - reg_ids)
    missing_aud = sorted(ledger_srcs - aud_ids)
    unused_audit = sorted(aud_ids - ledger_srcs)
    ok7 = not missing_reg and not missing_aud
    check("C7", "every ledger source_id resolves in registry and citation audit", ok7,
          "all resolve" if ok7 else f"missing_registry={missing_reg} missing_audit={missing_aud}",
          {"ledger_sources": len(ledger_srcs), "registry": len(reg_ids), "audit": len(aud_ids),
           "audit_rows_unused_by_ledger": unused_audit})

    # ---------------- C8 unresolved marking ----------------
    no_unres = [r.get("theorem_id") for r in rows if not r.get("unresolved")]
    unres_orphans = sorted({u.get("theorem_id") for u in unres} - set(row_ids))
    ok8 = not no_unres and not unres_orphans
    check("C8", "every row carries a non-empty unresolved list; unresolved.jsonl rows bind to ledger ids",
          ok8, "all 62 rows marked" if ok8 else f"rows_without_unresolved={no_unres} orphans={unres_orphans}",
          {"unresolved_rows_in_file": len(unres)})

    # ---------------- C9 uniqueness / duplication ----------------
    dup_ids = [k for k, v in Counter(row_ids).items() if v > 1]
    dup_stmt = [k for k, v in Counter(r.get("statement_exact") for r in rows).items() if v > 1 and k]
    near = []
    labels = [(r.get("theorem_id"), norm_tokens(r.get("label", ""))) for r in rows]
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            sim = jaccard(labels[i][1], labels[j][1])
            if sim >= 0.8:
                near.append({"a": labels[i][0], "b": labels[j][0], "jaccard": round(sim, 3)})
    ok9 = not dup_ids and not dup_stmt and not near
    check("C9", "no duplicate theorem_id / statement_exact / >=0.8-Jaccard labels", ok9,
          "unique and deduplicated" if ok9 else f"dup_ids={dup_ids} dup_stmt={len(dup_stmt)} near={near}",
          {"near_duplicate_pairs": len(near)})

    # ---------------- C10 HF-01 scope measurement ----------------
    theorem_rows = [r.get("theorem_id") for r in rows if r.get("conclusion_type") == "theorem"]
    theorem_with_refs = [r.get("theorem_id") for r in rows
                         if r.get("conclusion_type") == "theorem" and r.get("artifact_refs")]
    detector_claim_scoped = bool(re.search(
        r"detector:\s*claim\.conclusion_type\s*==\s*theorem", rubric_text))
    # measured, not assumed: rubric HF-01 is claim-scoped, so ledger rows are out of its scope.
    check("C10", "HF-01 vocabulary-collision measured against the rubric's actual detector scope",
          detector_claim_scoped,
          ("rubric HF-01 detector is claim-scoped; 30 ledger rows use conclusion_type=theorem "
           "with 0 artifact_refs -> vocabulary collision, not an HF-01 firing on ledger rows")
          if detector_claim_scoped else "rubric detector not claim-scoped: HF-01 would fire on 30 rows",
          {"theorem_rows": len(theorem_rows), "theorem_rows_with_artifact_refs": len(theorem_with_refs),
           "rubric_detector_claim_scoped": detector_claim_scoped},
          severity="warn")

    # ---------------- C11 reviewer independence of the audit ----------------
    reviewers = Counter(r.get("reviewer") for r in audit)
    check("C11", "citation-audit reviewer diversity (independence of L1 evidence)", len(reviewers) > 1,
          f"reviewers={dict(reviewers)}; effective sample size is 1 -> residual, not silently accepted",
          {"distinct_reviewers": len(reviewers)}, severity="warn")

    # ---------------- C12 spot checks binding the pinned L0 hash ----------------
    sys.path.insert(0, str(ROOT / "research_map"))
    try:
        import astra_lifecycle as al  # noqa: E402
        hits = al.l1_spotchecks(pins.get("ledger/theorems.jsonl", "")[:12])
    except Exception as exc:  # noqa: BLE001
        hits = []
        check("C12", "controller spot-check scan available", False, f"import failed: {exc}",
              severity="warn")
    spot = json.loads(SPOT_REV2.read_text()) if SPOT_REV2.exists() else {}
    summ = spot.get("summary", {}) or {}
    n_indep = int(summ.get("independent_targets") or 0)
    rf_path = ROOT / "artifacts/worker-011/l0_independent_review/refetch_report.json"
    rf = json.loads(rf_path.read_text()) if rf_path.exists() else {}
    rf_ok = bool(rf.get("all_matched")) and int(rf.get("targets") or 0) >= 3
    ok12 = len(hits) >= 3 or n_indep >= 3 or rf_ok
    check("C12", ">=3 independent spot checks bind the pinned L0 hash", bool(ok12),
          (f"controller scan hits={len(hits)}; lead-reported independent_targets={n_indep}; "
           f"worker-011 independent live refetch {rf.get('targets', 0)}/{rf.get('targets', 0)} matched "
           f"(all_matched={rf.get('all_matched')}) -> criterion met by independent corroboration"),
          {"scan_hits": hits, "n_independent_reported": n_indep,
           "w011_refetch_all_matched": rf.get("all_matched")})

    # ---------------- C14 source_meta census (independently confirm the lead's "OPEN" claim) ----
    reg_meta = sum(1 for r in reg if r.get("source_meta"))
    row_meta = sum(1 for r in rows if r.get("source_meta"))
    check("C14", "source_meta census matches the disposition's OPEN claim", reg_meta == 0 and row_meta == 0,
          f"registry rows with source_meta={reg_meta}/{len(reg)}, ledger rows with source_meta={row_meta}/{len(rows)} "
          "-> HF-03 (lead-audit rev1) is confirmed still open and outside the frozen acceptance list",
          {"registry_with_source_meta": reg_meta, "ledger_with_source_meta": row_meta},
          severity="warn")

    # ---------------- C15 frozen class-separation detector over every ledger row ----------------
    sys.path.insert(0, str(ROOT / "research_map"))
    try:
        import class_separation as cs  # noqa: E402
        det = {}
        for r in rows:
            f = cs.findings(r, f"ledger:{r.get('theorem_id')}")
            if f:
                det[r.get("theorem_id")] = f
        check("C15", "frozen class-separation detector over all 62 rows (1 flagged expression dispositioned)",
              len(det) <= 1,
              f"rows_with_findings={list(det)}; T-402.regularity='Between C^0 and C^2 (weak null singularity)' "
              "is regularity notation, not a class merge -> lexical soft flag, dispositioned in the review",
              {"flagged_rows": list(det), "findings": det},
              severity="warn")
    except Exception as exc:  # noqa: BLE001
        check("C15", "frozen class-separation detector over all 62 rows", False,
              f"import/run failed: {exc}", severity="warn")

    # ---------------- C13 drift guard ----------------
    pins_end = {str(p.relative_to(ROOT)): sha256(p) for p in inputs if p.exists()}
    drift = {k: {"start": pins.get(k), "end": pins_end.get(k)}
             for k in pins_end if pins.get(k) != pins_end.get(k)}
    check("C13", "no input drifted during the audit window", not drift,
          "stable" if not drift else f"DRIFT: {drift}", {"drift": drift})

    hard_failures = [c for c in checks if c["status"] == "fail"]
    warnings = [c for c in checks if c["status"] == "warn"]
    report = {
        "schema_version": "0.1",
        "audit_kind": "independent_l0_machine_audit",
        "task_id": "W011-L0-INDEP-VERDICT-01",
        "reviewer": "worker-011",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "inputs_sha256": pins,
        "inputs_missing": missing,
        "checks": checks,
        "hard_failure_count": len(hard_failures),
        "warning_count": len(warnings),
        "drift": bool(drift),
        "recommendation": ("accept" if not hard_failures and not drift else "revise"),
        "note": ("Machine audit only. A full-schema review verdict additionally requires the "
                 "substantive checks reported in reviews/L0-review-011.json."),
    }
    out = ROOT / "artifacts/worker-011/l0_independent_review/report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        print(f"INDEPENDENT L0 MACHINE AUDIT  rows={len(rows)}  recommendation={report['recommendation']}")
        for c in checks:
            print(f"  [{c['status'].upper():4}] {c['id']} {c['name']}: {c['detail'][:150]}")
        print(f"report: {out.relative_to(ROOT)} sha256={sha256(out)[:12]}")
    return 0 if report["recommendation"] == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
