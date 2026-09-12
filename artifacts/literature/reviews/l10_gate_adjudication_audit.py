#!/usr/bin/env python3
"""L10 literature-lifecycle read-only gate audit.

Deterministic. Reads canonical pins and verdict records; writes NOTHING.
Emits one JSON object on stdout so the machine record is reproducible by re-running
this file at the same tree state.

Scope: measure, at the live pins, the facts that decide G-LIT:
  (A) L0 ledger/audit hashes, row counts, frozen class tokens;
  (B) the HF-02 (class_leakage, critical) firing set and the rubric text that scopes it;
  (C) the verdict scope of the two L0 ledger accepts;
  (D) L1 spot-check binding at the audit hash.

No claim, node status, validation_status or gate verdict is produced here.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
# G-LIT criterion (evaluation_rubric.yaml) and HF-02 detector text are cited by line.
RUBRIC = ROOT / "evaluation_rubric.yaml"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def rubric_lines(*nums):
    src = RUBRIC.read_text().splitlines()
    return {n: src[n - 1].strip() for n in nums}


def main() -> dict:
    ledger = ROOT / "ledger" / "theorems.jsonl"
    audit = ROOT / "ledger" / "citation_audit.csv"
    ledger_rows = rows(ledger)
    audit_rows = [l for l in audit.read_text().splitlines() if l.strip()]

    # (B) HF-02 literal detector components on L0 rows.
    dual, unknown, c0_theorem, transfer = [], [], [], []
    informs_dual = []
    for r in ledger_rows:
        cids = r.get("class_ids") or []
        ics = r.get("informs_classes") or []
        if len(cids) >= 2:
            dual.append({"theorem_id": r.get("theorem_id"), "class_ids": cids,
                         "conclusion_type": r.get("conclusion_type")})
        if len(ics) >= 2:
            informs_dual.append({"theorem_id": r.get("theorem_id"), "informs_classes": ics})
        for tok in list(cids) + list(ics):
            if tok not in FROZEN and tok not in [u["theorem_id"] for u in unknown]:
                unknown.append({"theorem_id": r.get("theorem_id"), "token": tok})
        if "AF-SCC-C0-VAC-GEN" in cids and r.get("conclusion_type") == "theorem":
            c0_theorem.append(r.get("theorem_id"))
        if r.get("transfer_argument"):
            transfer.append(r.get("theorem_id"))

    # (C) verdict scope of the two ledger accepts, as recorded by the reviewers themselves.
    accepts = {}
    for name, path in {
        "worker-075": ROOT / "reviews" / "L0-review-075-rev3.json",
        "worker-079": ROOT / "reviews" / "L0-review-worker-079.json",
    }.items():
        d = json.loads(path.read_text())
        accepts[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "verdict": d.get("verdict"),
            "score": d.get("score"),
            "artifact_sha256": d.get("artifact_sha256"),
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            "verdict_scope": d.get("verdict_scope"),
            "hard_failures": d.get("hard_failures"),
            "open_objections": d.get("open_objections"),
        }

    # Revise verdicts binding the same ledger hash (their own recorded targets).
    revises = []
    for path in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("verdict") != "revise":
            continue
        hs = json.dumps(d)
        if sha256(ledger)[:12] not in hs:
            continue
        if d.get("target_id") not in ("L0", None) and "theorems.jsonl" not in hs:
            continue
        revises.append({
            "path": str(path.relative_to(ROOT)),
            "reviewer": d.get("reviewer"),
            "score": d.get("score"),
            "hard_failures": d.get("hard_failures"),
        })

    # (D) L1 spot checks that bind the live audit hash.
    audit_pin = sha256(audit)[:12]
    spot_files, spot_actors = [], set()
    for path in sorted((ROOT / "reviews").glob("L1-spotcheck-*.json")):
        txt = path.read_text()
        if audit_pin in txt:
            d = json.loads(txt)
            spot_files.append({"path": str(path.relative_to(ROOT)),
                               "reviewer": d.get("reviewer") or d.get("actor")})
            spot_actors.add(d.get("reviewer") or d.get("actor"))

    return {
        "schema": "astra/literature/l10-gate-audit/v1",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "astra-lead-literature",
        "read_only": True,
        "pins": {
            "ledger/theorems.jsonl": {
                "sha256": sha256(ledger), "bytes": ledger.stat().st_size,
                "rows": len(ledger_rows),
                "mtime": datetime.fromtimestamp(ledger.stat().st_mtime, CST).isoformat(timespec="seconds"),
            },
            "ledger/citation_audit.csv": {
                "sha256": sha256(audit), "bytes": audit.stat().st_size,
                "rows_data": len(audit_rows) - 1,
                "mtime": datetime.fromtimestamp(audit.stat().st_mtime, CST).isoformat(timespec="seconds"),
            },
        },
        "frozen_class_tokens": FROZEN,
        "hf02": {
            "rubric_preamble": rubric_lines(168, 169),
            "rubric_hf02": rubric_lines(175, 176, 177, 178, 179, 180),
            "glit_criterion_scope_match": rubric_lines(140),
            "rows_total": len(ledger_rows),
            "rows_with_ge2_class_ids": len(dual),
            "dual_class_rows": dual,
            "rows_with_ge2_informs_classes": informs_dual,
            "unknown_class_tokens": unknown,
            "c0_bound_conclusion_type_theorem_rows": c0_theorem,
            "rows_with_transfer_argument": transfer,
            "hf02_components_firing": {
                "unknown_class_id": len(unknown) > 0,
                "disjunction_of_class_ids": len(dual) > 0,
                "forbidden_evidence_without_transfer": len(transfer) == 0,
                "conclusion_type_not_allowed_for_class": len(c0_theorem) > 0,
            },
        },
        "l0_ledger_accepts": accepts,
        "l0_ledger_revises_binding_hash": revises,
        "l1": {
            "audit_sha256_prefix": audit_pin,
            "named_spotcheck_reviews_binding_hash": spot_files,
            "distinct_named_spotcheck_reviewers": sorted(a for a in spot_actors if a),
            "controller_measured_spotchecks": 23,
            "controller_measurement_ref": "runtime/state/controller_verification/astra-lifecycle-06-decisions.json#CF-15",
        },
        "not_claimed": ["gate verdict", "node completion", "validation_status",
                        "independent review", "any theorem"],
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
