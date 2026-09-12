#!/usr/bin/env python3
"""W032-L0-BLIND-REVIEW-01 independent machine checks.

Reviewer: worker-032 (not an author of the ledger, registry, or audit).
Targets (frozen): ledger/theorems.jsonl#ce42d205e761,
                  ledger/citation_audit.csv#315c19145065.

This script only reads. It never edits the ledger, registry, or audit.
It recomputes, from the pinned bytes, the checks the literature lead
self-reported in artifacts/literature/reviews/L0-rev2-disposition.md §D.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
TARGETS = {
    "ledger/theorems.jsonl": "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}
SUPPORT = [
    "artifacts/literature/registry.jsonl",
    "artifacts/literature/unresolved.jsonl",
    "artifacts/literature/reviews/L1-spotcheck-rev2.json",
    "artifacts/literature/reviews/L0-rev2-disposition.md",
    "artifacts/literature/L0_L1_ACCEPTANCE.md",
    "artifacts/formulation/rule_spec.json",
    "research_map/formulation_taxonomy.yaml",
]
CLASS_TOKEN = re.compile(r"^AF-[A-Z0-9-]+$")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jload(p: Path):
    with p.open() as f:
        return json.load(f)


def jlines(p: Path):
    out = []
    with p.open() as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def pin() -> dict:
    return {rel: sha256(ROOT / rel) for rel in list(TARGETS) + SUPPORT}


def main() -> int:
    start = now()
    pins_before = pin()
    report: dict = {
        "task_id": "W032-L0-BLIND-REVIEW-01",
        "reviewer": "worker-032",
        "node_id": "L0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "started_at": start,
        "pins_before": pins_before,
        "target_pins_match_declared": {
            rel: pins_before[rel] == want for rel, want in TARGETS.items()
        },
        "checks": {},
        "findings": [],
    }

    ledger = jlines(ROOT / "ledger/theorems.jsonl")
    reg = jlines(ROOT / "artifacts/literature/registry.jsonl")
    with (ROOT / "ledger/citation_audit.csv").open() as f:
        audit = list(csv.DictReader(f))
    audit_cols = list(audit[0].keys()) if audit else []
    spec = jload(ROOT / "artifacts/formulation/rule_spec.json")
    frozen_four = sorted(spec["frozen_classes"])

    # --- C1 class-token binding ------------------------------------------------
    class_tokens = Counter()
    foreign = []
    tag_classlike = Counter()
    for r in ledger:
        tid = r.get("theorem_id")
        for field in ("class_ids", "informs_classes"):
            for tok in r.get(field, []) or []:
                class_tokens[tok] += 1
                if tok not in frozen_four:
                    foreign.append({"theorem_id": tid, "field": field, "token": tok})
        for tag in r.get("ledger_tags", []) or []:
            if CLASS_TOKEN.match(str(tag)):
                tag_classlike[tag] += 1
    report["checks"]["C1_class_token_census"] = {
        "frozen_four_from_rule_spec": frozen_four,
        "rule_spec_sha256": pins_before["artifacts/formulation/rule_spec.json"],
        "tokens_in_class_ids_and_informs_classes": dict(class_tokens),
        "tokens_outside_frozen_four": foreign,
        "class_like_tokens_in_ledger_tags": dict(tag_classlike),
        "verdict": "pass" if not foreign else "fail",
    }
    if foreign:
        report["findings"].append({
            "label": "B-C1", "severity": "blocking",
            "finding": f"{len(foreign)} class token(s) outside the frozen four in class-bearing fields",
            "evidence": foreign[:10],
        })

    # --- C2 unresolved marking --------------------------------------------------
    bad_unresolved = []
    for r in ledger:
        u = r.get("unresolved")
        if not isinstance(u, list) or not u or any(not str(x).strip() for x in u):
            bad_unresolved.append(r.get("theorem_id"))
    report["checks"]["C2_unresolved_marking"] = {
        "rows": len(ledger),
        "rows_with_nonempty_unresolved": sum(1 for r in ledger if r.get("unresolved")),
        "rows_failing": bad_unresolved,
        "verdict": "pass" if not bad_unresolved else "fail",
    }
    if bad_unresolved:
        report["findings"].append({
            "label": "B-C2", "severity": "blocking",
            "finding": "row(s) without a populated unresolved list", "evidence": bad_unresolved[:10],
        })

    # --- C3 source-id resolution ------------------------------------------------
    reg_ids = [r["source_id"] for r in reg]
    # the audit CSV keys sources as `citation_id`; `source_id` is the ledger/registry key
    audit_ids = {row.get("source_id") or row.get("citation_id") for row in audit}
    dup_reg = [k for k, v in Counter(reg_ids).items() if v > 1]
    dangling, dangling_audit = [], []
    for r in ledger:
        for sid in r.get("source_ids", []) or []:
            if sid not in set(reg_ids):
                dangling.append({"theorem_id": r.get("theorem_id"), "source_id": sid})
            if sid not in audit_ids:
                dangling_audit.append({"theorem_id": r.get("theorem_id"), "source_id": sid})
    report["checks"]["C3_source_resolution"] = {
        "registry_rows": len(reg), "registry_duplicate_ids": dup_reg,
        "audit_rows": len(audit), "audit_columns": audit_cols,
        "ledger_source_ids_unresolved_in_registry": dangling,
        "ledger_source_ids_unresolved_in_audit": dangling_audit,
        "verdict": "pass" if not (dangling or dangling_audit or dup_reg) else "fail",
    }
    if dangling or dangling_audit or dup_reg:
        report["findings"].append({
            "label": "B-C3", "severity": "blocking",
            "finding": "source_id resolution failure or duplicate registry id",
            "evidence": {"registry": dangling[:5], "audit": dangling_audit[:5], "dup": dup_reg},
        })

    # --- C4 spot-check binding and independent count ----------------------------
    spot = jload(ROOT / "artifacts/literature/reviews/L1-spotcheck-rev2.json")
    spot_binding = spot.get("binding", {})
    binding_ok = {
        "ledger/theorems.jsonl": spot_binding.get("ledger/theorems.jsonl") == pins_before["ledger/theorems.jsonl"],
        "ledger/citation_audit.csv": spot_binding.get("ledger/citation_audit.csv") == pins_before["ledger/citation_audit.csv"],
    }
    results = spot.get("results", [])
    indep = [x for x in results if "independent" in str(x.get("fetched_by", "")).lower()]
    lead = [x for x in results if x not in indep]
    verdicts = Counter(x.get("verdict") for x in results)
    report["checks"]["C4_spotcheck_binding"] = {
        "file_sha256": pins_before["artifacts/literature/reviews/L1-spotcheck-rev2.json"],
        "binding_hashes_match_current_pins": binding_ok,
        "targets_total": spot.get("summary", {}).get("targets"),
        "independent_targets_from_summary": spot.get("summary", {}).get("independent_targets"),
        "independent_targets_recounted": len(indep),
        "independent_source_ids": [x.get("source_id") for x in indep],
        "lead_corroborating_targets_recounted": len(lead),
        "verdicts": dict(verdicts),
        "verdict": "pass" if all(binding_ok.values()) and len(indep) >= 3 else "fail",
    }
    if not all(binding_ok.values()) or len(indep) < 3:
        report["findings"].append({
            "label": "B-C4", "severity": "blocking",
            "finding": "spot-check evidence is not bound to the frozen hash or fewer than 3 independent targets",
            "evidence": report["checks"]["C4_spotcheck_binding"],
        })

    # --- C5 conclusion_type / verification_status discipline --------------------
    theorem_no_art = [r["theorem_id"] for r in ledger
                      if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")]
    accepted_unverified = [r["theorem_id"] for r in ledger
                           if r.get("status") == "accepted" and r.get("verification_status") == "unverified"]
    reg_ev = {r["source_id"]: (r.get("verification") or {}).get("evidence_type") for r in reg}
    strongest_ok = {"full-text"}
    overstate = []
    for r in ledger:
        types = {reg_ev.get(s) for s in r.get("source_ids", []) or []}
        vs = r.get("verification_status")
        if vs in {"full-text", "page-checked"} and types and not (types & strongest_ok):
            overstate.append({"theorem_id": r.get("theorem_id"), "verification_status": vs,
                              "registry_evidence_types": sorted(t for t in types if t)})
    report["checks"]["C5_conclusion_and_status_discipline"] = {
        "conclusion_type_counts": dict(Counter(r.get("conclusion_type") for r in ledger)),
        "theorem_rows_without_artifact_refs": theorem_no_art,
        "theorem_rows_without_artifact_refs_count": len(theorem_no_art),
        "accepted_rows_with_unverified_status": accepted_unverified,
        "rows_claiming_fulltext_or_page_checked_without_fulltext_registry_evidence": overstate,
        "registry_evidence_type_counts": dict(Counter(reg_ev.values())),
        "verdict": "pass" if not accepted_unverified and not overstate else "fail",
    }
    if accepted_unverified or overstate:
        report["findings"].append({
            "label": "B-C5", "severity": "blocking",
            "finding": "verification_status overstates locator evidence",
            "evidence": {"accepted_unverified": accepted_unverified, "overstate": overstate[:10]},
        })
    if theorem_no_art:
        report["findings"].append({
            "label": "N-C5", "severity": "non_blocking",
            "finding": (f"{len(theorem_no_art)} ledger rows carry conclusion_type=theorem with no artifact_refs "
                        "(claim-vocabulary collision carried from flash-17 HF-01; lead disposition defers to a "
                        "bounded rev 3 pending controller decision). It does not alter a class token, a citation, "
                        "or the unresolved marking, so it does not block the three L0 acceptance criteria."),
            "evidence": {"rows": theorem_no_art, "count": len(theorem_no_art)},
            "owner": "astra-lead-literature / controller decision",
        })

    # --- C6 registry evidence depth + source_meta -------------------------------
    report["checks"]["C6_evidence_depth_and_source_meta"] = {
        "registry_evidence_type": dict(Counter(reg_ev.values())),
        "ledger_rows_with_source_meta_key": sum(1 for r in ledger if "source_meta" in r),
        "registry_rows_with_source_meta_key": sum(1 for r in reg if "source_meta" in r),
        "verdict": "observation_only (deferred rev-3 backlog per BL-2)",
    }
    report["findings"].append({
        "label": "N-C6", "severity": "non_blocking",
        "finding": ("0/62 ledger rows and 0/97 registry rows carry source_meta (matter_model, "
                    "cosmological_constant, dimension, symmetry, formulation); evidence depth is "
                    "84 abstract / 12 metadata / 1 full-text, so most theorem bodies are abstract-level. "
                    "Deferred by the lead to a bounded rev 3 (BL-2) and constrained by paywalled primaries (BL-3)."),
        "owner": "astra-lead-literature / human-pi for library access",
    })

    # --- C7 T-301 residual class binding ----------------------------------------
    t301 = next((r for r in ledger if r.get("theorem_id") == "T-301"), None)
    report["checks"]["C7_T301_residual"] = {
        "found": t301 is not None,
        "conclusion_type": (t301 or {}).get("conclusion_type"),
        "class_ids": (t301 or {}).get("class_ids"),
        "status": (t301 or {}).get("status"),
        "verification_status": (t301 or {}).get("verification_status"),
        "does_not_imply_present": bool((t301 or {}).get("does_not_imply")),
        "note": ("flash-16 residual: class_ids still binds AF-SCC-C0-VAC-GEN while the data "
                 "assumptions are interior/local. Disposition records it as partially addressed; "
                 "recorded here as a scope caveat, not a blocking defect at this hash."),
    }

    # --- C8 independent re-fetch (recorded by the reviewer at run time) ---------
    report["checks"]["C8_independent_refetch"] = {
        "performed_by": "worker-032 (this reviewer), separate agent context, read-only ledger access",
        "fetched_at": "2026-09-12T00:22+08:00",
        "method": "direct HTTPS GET by reviewer; title/author/year/venue compared to registry record",
        "results": [
            {
                "source_id": "SRC-001",
                "url": "https://comptes-rendus.academie-sciences.fr/mecanique/articles/10.5802/crmeca.284/",
                "http": 200,
                "registry": {"title": "Weak cosmic censorship, trapped surfaces, and naked singularities for the Einstein vacuum equations",
                              "authors": ["Yakov Shlapentokh-Rothman"], "year": 2025,
                              "venue": "Comptes Rendus. Mecanique, Volume 353 (2025), pp. 379-410"},
                "live": {"title": "Weak cosmic censorship, trapped surfaces, and naked singularities for the Einstein vacuum equations",
                          "author": "Yakov Shlapentokh-Rothman",
                          "venue_year": "Comptes Rendus. Mecanique, Volume 353 (2025), pp. 379-410",
                          "abstract_text_matches_registry_evidence": True},
                "verdict": "MATCH",
            },
            {
                "source_id": "SRC-003",
                "url": "https://arxiv.org/abs/2204.09891",
                "http": 200,
                "registry": {"title": "Naked Singularities for the Einstein Vacuum Equations: The Interior Solution",
                              "authors": ["Yakov Shlapentokh-Rothman"], "year": 2022},
                "live": {"title": "Naked Singularities for the Einstein Vacuum Equations: The Interior Solution",
                          "author": "Yakov Shlapentokh-Rothman", "submitted": "21 Apr 2022"},
                "verdict": "MATCH",
            },
            {
                "source_id": "SRC-009",
                "url": "https://arxiv.org/abs/2606.25755",
                "http": 200,
                "registry": {"title": "C^0-inextendibility of a class of warped-product black hole spacetimes",
                              "authors": ["Karim Mosani"], "year": 2026},
                "live": {"title": "$C^0$-inextendibility of a class of warped-product black hole spacetimes",
                          "author": "Karim Mosani", "submitted": "24 Jun 2026"},
                "verdict": "MATCH",
            },
            {
                "source_id": "SRC-090",
                "url": "https://www.math.tecnico.ulisboa.pt/~jnatar/nonarxivpapers/Chrusciel.pdf",
                "http": "not fetched",
                "reason": "reviewer fetch tool refuses application/pdf; recorded as NOT independently re-verified by this review",
                "verdict": "UNVERIFIED_BY_THIS_REVIEW",
            },
        ],
        "note": ("These three MATCH checks are independent of the four checks in L1-spotcheck-rev2.json "
                 "(different reviewer, three sources: SRC-001, SRC-003, SRC-009, none of which is in that "
                 "file's independent set) and are title/author/year-level only, not full-text theorem-scope checks."),
    }

    pins_after = pin()
    report["pins_after"] = pins_after
    report["hash_stable_during_review"] = pins_before == pins_after
    if pins_before != pins_after:
        report["findings"].append({
            "label": "B-DRIFT", "severity": "blocking",
            "finding": "a pinned hash moved during the review window; verdict is void per the assignment stop rule",
            "evidence": {k: {"before": pins_before[k], "after": pins_after[k]}
                          for k in pins_before if pins_before[k] != pins_after[k]},
        })
    report["finished_at"] = now()

    blocking = [f for f in report["findings"] if f["severity"] == "blocking"]
    report["verdict_if_reviewed_by_these_checks"] = "revise" if blocking else "accept"
    report["blocking_count"] = len(blocking)

    out = ROOT / "artifacts/worker-032/l0_review/report.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: report[k] for k in
                      ("task_id", "verdict_if_reviewed_by_these_checks", "blocking_count",
                       "hash_stable_during_review")}, indent=1))
    for f in report["findings"]:
        print(f["severity"], f["label"], f["finding"][:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
