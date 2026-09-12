#!/usr/bin/env python3
"""L12 independent, read-only re-derivation of the decisive G-LIT counts.

Group lead lifecycle L12 (literature). No network, no writes outside the machine
record passed on the command line, no ledger/map mutation.

Re-derives, from the two pinned files only:
  * the rubric-literal HF-02 predicate: a row's class_ids contains >=2 frozen class tokens
  * row count / order preservation between live ledger and staged HF-02 candidate
  * the field-level diff scope (which rows, which fields)
  * empty-class_ids counts, overall and by conclusion_type
  * the pinned R6 self-declared-scope predicate (re-implemented from the
    PREREGISTRATION text; same predicate, independently coded)

Usage:
  python3 artifacts/literature/reviews/l12_hf02_staged_rederive.py --out <path.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / "ledger" / "theorems.jsonl"
STAGED = ROOT / "artifacts" / "worker-025" / "l0_hf02_staged" / "staged" / "theorems.hf02-staged.jsonl"
LIVE_PIN = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
STAGED_PIN = "b3ab6a1a635720a97e51fd332bcf1d9f9e6fdc45ad64d886106f1cd298d61cea"
FROZEN = ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH")

# R6_self_declared_scope, transcribed from
# artifacts/worker-099/hf02_staged_adoption_verify/PREREGISTRATION.json
R6 = {
    "AF-SCC-C0-VAC-GEN": [re.compile(r"(does not|not) (decide|prove|settle|establish|imply).{0,60}(C\^?0|continuous)", re.I),
                          re.compile(r"not the C\^?0 formulation", re.I),
                          re.compile(r"any SCC formulation", re.I)],
    "AF-SCC-C2-VAC-GEN": [re.compile(r"(does not|not) (decide|prove|settle|establish|imply).{0,60}(C\^?2|Lipschitz)", re.I),
                          re.compile(r"not the C\^?2 formulation", re.I)],
    "AF-WCC-VAC-GEN": [re.compile(r"(does not|not) (decide|prove|settle|establish).{0,60}(WCC|weak cosmic censorship)", re.I)],
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load(p: Path):
    rows = []
    for line in p.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def frozen_hits(row):
    cids = row.get("class_ids") or []
    return [t for t in cids if t in FROZEN]


def hf02(rows):
    return [r["theorem_id"] for r in rows if len(frozen_hits(r)) >= 2]


def self_contradicted(row):
    cids = set(frozen_hits(row))
    dni = row.get("does_not_imply") or []
    if isinstance(dni, str):
        dni = [dni]
    hits = {}
    for tok in cids:
        for pat in R6.get(tok, []):
            for s in dni:
                if pat.search(str(s)):
                    hits.setdefault(tok, []).append(str(s)[:160])
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "artifacts/literature/reviews/L12-hf02-staged-rederive.json"))
    a = ap.parse_args()

    live_sha, staged_sha = sha256(LIVE), sha256(STAGED)
    live, staged = load(LIVE), load(STAGED)

    live_ids = [r.get("theorem_id") for r in live]
    staged_ids = [r.get("theorem_id") for r in staged]
    by_id_live = {r.get("theorem_id"): r for r in live}
    by_id_staged = {r.get("theorem_id"): r for r in staged}

    changed_rows, changed_fields = {}, {}
    for tid in live_ids:
        if tid not in by_id_staged:
            changed_rows.setdefault("missing_from_staged", []).append(tid)
            continue
        a_, b_ = by_id_live[tid], by_id_staged[tid]
        keys = set(a_) | set(b_)
        diff = sorted(k for k in keys if a_.get(k) != b_.get(k))
        if diff:
            changed_rows[tid] = diff
            for k in diff:
                changed_fields[k] = changed_fields.get(k, 0) + 1
    for tid in staged_ids:
        if tid not in by_id_live:
            changed_rows.setdefault("added_in_staged", []).append(tid)

    def empty_counts(rows):
        out = {"total": 0, "by_conclusion_type": {}}
        for r in rows:
            if not (r.get("class_ids") or []):
                out["total"] += 1
                ct = r.get("conclusion_type")
                out["by_conclusion_type"][ct] = out["by_conclusion_type"].get(ct, 0) + 1
        return out

    THM_LIKE = {"theorem", "conditional_theorem"}

    def thm_unbound(rows):
        return [r["theorem_id"] for r in rows
                if r.get("conclusion_type") in THM_LIKE and not (r.get("class_ids") or [])]

    sc_live = {r["theorem_id"]: self_contradicted(r) for r in live}
    sc_staged = {r["theorem_id"]: self_contradicted(r) for r in staged}
    sc_live = {k: v for k, v in sc_live.items() if v}
    sc_staged = {k: v for k, v in sc_staged.items() if v}

    rec = {
        "schema_version": "0.1",
        "artifact": "artifacts/literature/reviews/L12-hf02-staged-rederive.json",
        "task_id": "LIT-L12-HF02-REDERIVE-01",
        "actor": "astra-lead-literature",
        "lifecycle": "L12",
        "created_at_note": "wall-clock stamped by the emitting checkpoint; this record is deterministic and offline",
        "read_only": True,
        "authority_note": ("Independent measurement only. No gate verdict, no node status, no "
                           "validation_status, no ledger or map write."),
        "pins": {
            "ledger/theorems.jsonl": {"declared": LIVE_PIN, "measured": live_sha, "match": live_sha == LIVE_PIN},
            "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl":
                {"declared": STAGED_PIN, "measured": staged_sha, "match": staged_sha == STAGED_PIN},
        },
        "frozen_tokens": list(FROZEN),
        "hf02_literal": {
            "predicate": "row.class_ids contains >=2 of the four frozen class tokens",
            "live_count": len(hf02(live)), "live_rows": hf02(live),
            "staged_count": len(hf02(staged)), "staged_rows": hf02(staged),
        },
        "rows": {"live": len(live), "staged": len(staged),
                 "order_preserved": live_ids == staged_ids,
                 "staged_id_sequence_sha256": hashlib.sha256(json.dumps(staged_ids).encode()).hexdigest()},
        "diff": {"changed_row_count": len([k for k in changed_rows if k not in ("missing_from_staged", "added_in_staged")]),
                 "changed_rows": changed_rows, "changed_field_histogram": changed_fields},
        "empty_class_ids": {"live": empty_counts(live), "staged": empty_counts(staged)},
        "theorem_like_unbound": {
            "definition": "conclusion_type in {theorem, conditional_theorem} and class_ids == []",
            "live_count": len(thm_unbound(live)), "live_rows": thm_unbound(live),
            "staged_count": len(thm_unbound(staged)), "staged_rows": thm_unbound(staged),
            "newly_unbound": sorted(set(thm_unbound(staged)) - set(thm_unbound(live))),
        },
        "r6_self_contradicted": {
            "predicate": "R6_self_declared_scope re-implemented from PREREGISTRATION.json (same predicate, independent code)",
            "live_rows": sorted(sc_live), "live_count": len(sc_live),
            "staged_rows": sorted(sc_staged), "staged_count": len(sc_staged),
            "quotes_live": sc_live,
        },
        "agreement_with_w099": {
            "w099_reported": {"hf02_live": 8, "hf02_staged": 0, "empty_live": 28, "empty_staged": 34,
                              "thm_like_live": 21, "thm_like_staged": 24, "newly_unbound": ["T-303", "T-305", "T-526"]},
        },
    }
    rec["agreement_with_w099"]["matches"] = {
        "hf02_live": rec["hf02_literal"]["live_count"] == 8,
        "hf02_staged": rec["hf02_literal"]["staged_count"] == 0,
        "empty_live": rec["empty_class_ids"]["live"]["total"] == 28,
        "empty_staged": rec["empty_class_ids"]["staged"]["total"] == 34,
        "thm_like_live": rec["theorem_like_unbound"]["live_count"] == 21,
        "thm_like_staged": rec["theorem_like_unbound"]["staged_count"] == 24,
        "newly_unbound": rec["theorem_like_unbound"]["newly_unbound"] == ["T-303", "T-305", "T-526"],
    }
    out = Path(a.out)
    out.write_text(json.dumps(rec, indent=2, sort_keys=False) + "\n")
    print(json.dumps({"out": str(out), "sha256": sha256(out),
                      "hf02": rec["hf02_literal"]["live_count"], "hf02_staged": rec["hf02_literal"]["staged_count"],
                      "matches": rec["agreement_with_w099"]["matches"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
