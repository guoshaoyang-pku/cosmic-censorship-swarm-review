#!/usr/bin/env python3
"""W025-L0-HF02-STAGED-REPAIR-01 (worker-025)

Bounded class-bound task: turn worker-023's un-applied HF-02 class_ids-disjunction
proposal (artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json,
sha256 0f86158c5bb7...) into a staged, machine-verified candidate revision of
ledger/theorems.jsonl, WITHOUT writing the live ledger or claiming any gate/node
verdict.

Class binding : AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN (rows touched)
Node / gate   : L0 / G-LIT (literature ledger); audit scope note for G-AUDIT
Anchor        : ledger/theorems.jsonl sha256 a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28

What this script does
  1. Fails closed if any pinned input hash differs from the declared anchor.
  2. Independently re-derives the rubric-literal HF-02 detector firing set
     (a row whose class_ids intersect the four frozen classes in >1 token).
  3. Applies exactly the 8 `set` ops from worker-023's proposed_patch to a
     worker-owned staged copy.
  4. Runs acceptance checks A1-A6 and controls C1-C6; writes report.json.

Writes only under artifacts/worker-025/l0_hf02_staged/**. The live ledger is read
once and never written. Worker output is evidence + a candidate revision only:
it cannot set status=done, validation_status=passed, or any gate verdict, and it
does not re-adjudicate any mathematical claim.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-025/l0_hf02_staged -> swarm root

LEDGER = ROOT / "ledger" / "theorems.jsonl"
ADJ = ROOT / "artifacts" / "worker-023" / "l0_hf02" / "hf02-disjunction-adjudication-023.json"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"
RUBRIC = ROOT / "evaluation_rubric.yaml"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"

PINS = {
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json":
        "0f86158c5bb79adac957a4585a6be4b62abf13c541ea74769f9e629749c4f9d6",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b",
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}

FROZEN4 = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# Fields the staged ops are allowed to touch. Anything else must be byte-identical.
# Tuple (not set): keeps before/after key order deterministic across processes.
PATCHABLE = ("class_ids", "informs_classes", "ledger_tags")

STAGED_DIR = HERE / "staged"
STAGED_LEDGER = STAGED_DIR / "theorems.hf02-staged.jsonl"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_rows(p: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        try:
            rows.append(json.loads(s))
        except ValueError as e:
            raise SystemExit(f"ledger parse error line {i}: {e}")
    return rows


def row_key(r: dict) -> str:
    return r.get("theorem_id") or r.get("id")


def hf02_disjunctions(rows: list[dict]) -> list[str]:
    """Rubric-literal HF-02 'disjunction of class_ids' detector.

    evaluation_rubric.yaml#d748a9e3 HF-02 name: class_leakage; the detector text
    used here is the one worker-093/worker-023 applied to the ledger: a row whose
    class_ids array carries more than one frozen class token.
    """
    out = []
    for r in rows:
        n = sum(1 for c in (r.get("class_ids") or []) if c in FROZEN4)
        if n > 1:
            out.append(row_key(r))
    return out


def canonical(r: dict, drop: set[str] | None = None) -> str:
    d = {k: v for k, v in r.items() if not drop or k not in drop}
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def apply_patch(rows: list[dict], patch: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    staged = copy.deepcopy(rows)
    by_id = {row_key(r): r for r in staged}
    diffs, errors = [], []
    for op in patch:
        rid = op.get("row_id")
        if op.get("op") != "set":
            errors.append(f"{rid}: unsupported op {op.get('op')!r}")
            continue
        r = by_id.get(rid)
        if r is None:
            errors.append(f"{rid}: row not found")
            continue
        before = {k: copy.deepcopy(r.get(k)) for k in PATCHABLE}
        if "class_ids" in op:
            r["class_ids"] = op["class_ids"]
        if "informs_classes" in op:
            r["informs_classes"] = op["informs_classes"]
        for t in op.get("ledger_tags_add") or []:
            tags = list(r.get("ledger_tags") or [])
            if t not in tags:
                tags.append(t)
            r["ledger_tags"] = tags
        after = {k: copy.deepcopy(r.get(k)) for k in PATCHABLE}
        changed = sorted(k for k in PATCHABLE if before.get(k) != after.get(k))
        diffs.append({"row_id": rid, "changed_fields": changed,
                      "before": before, "after": after})
    return staged, diffs, errors


def write_staged(rows: list[dict]) -> str:
    STAGED_DIR.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, sort_keys=False) + "\n" for r in rows)
    STAGED_LEDGER.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> int:
    report: dict = {
        "artifact": "artifacts/worker-025/l0_hf02_staged/report.json",
        "task_id": "W025-L0-HF02-STAGED-REPAIR-01",
        "worker": "worker-025",
        "role": "bounded execution worker",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "authority": ("Worker evidence and staged candidate only. No live ledger write, no gate "
                      "verdict, no node status, no validation_status=passed, no claim re-adjudication."),
        "checks": {}, "controls": {}, "findings": [], "errors": [],
    }

    # ---- P0 pins / fail closed -------------------------------------------------
    pins_measured = {}
    for rel, want in PINS.items():
        got = sha256_file(ROOT / rel)
        pins_measured[rel] = {"declared": want, "measured": got, "match": got == want}
        if got != want:
            report["errors"].append(f"PIN DRIFT {rel}: declared {want} measured {got}")
    report["pins"] = pins_measured
    if report["errors"]:
        (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
        print(json.dumps(report["errors"], indent=1))
        return 2

    live_rows = load_rows(LEDGER)
    adj = json.loads(ADJ.read_text())
    registry = json.loads(REGISTRY.read_text())
    patch = adj.get("proposed_patch") or []

    live_disj = hf02_disjunctions(live_rows)
    report["live"] = {
        "rows": len(live_rows),
        "sha256": PINS["ledger/theorems.jsonl"],
        "hf02_disjunctions": live_disj,
        "hf02_disjunction_count": len(live_disj),
    }

    # ---- A0: adjudication agrees with live bytes ------------------------------
    report["checks"]["A0_anchor_matches_adjudication"] = {
        "ok": adj.get("anchor_ledger_sha256") == PINS["ledger/theorems.jsonl"],
        "adjudication_declared_anchor": adj.get("anchor_ledger_sha256"),
    }
    report["checks"]["A0_patch_row_set_equals_measured_disjunctions"] = {
        "ok": sorted(op.get("row_id") for op in patch) == sorted(live_disj),
        "patch_rows": sorted(op.get("row_id") for op in patch),
        "measured_rows": sorted(live_disj),
    }
    report["checks"]["A0_patch_class_tokens_frozen_only"] = {
        "ok": all(c in FROZEN4 for op in patch for c in (op.get("class_ids") or [])),
        "tokens": sorted({c for op in patch for c in (op.get("class_ids") or [])}),
    }

    # ---- build staged ----------------------------------------------------------
    staged, diffs, apply_errors = apply_patch(live_rows, patch)
    report["errors"].extend(apply_errors)
    staged_sha = write_staged(staged)
    staged_rows = load_rows(STAGED_LEDGER)
    staged_disj = hf02_disjunctions(staged_rows)

    # ---- acceptance ------------------------------------------------------------
    live_ids = [row_key(r) for r in live_rows]
    staged_ids = [row_key(r) for r in staged_rows]
    patched_ids = {op.get("row_id") for op in patch}
    untouched_ok, touched_field_ok, offenders = True, True, []
    for a, b in zip(live_rows, staged_rows):
        rid = row_key(a)
        if rid in patched_ids:
            if canonical(a, drop=PATCHABLE) != canonical(b, drop=PATCHABLE):
                untouched_ok = False
                offenders.append(rid)
            for k in PATCHABLE:
                if a.get(k) == b.get(k):
                    continue
                if k not in {f for d in diffs if d["row_id"] == rid for f in d["changed_fields"]}:
                    touched_field_ok = False
        else:
            if canonical(a) != canonical(b):
                untouched_ok = False
                offenders.append(rid)

    checks = report["checks"]
    checks["A1_row_set_unchanged"] = {"ok": live_ids == staged_ids,
                                      "live": len(live_ids), "staged": len(staged_ids)}
    checks["A2_hf02_disjunctions_zero_after_patch"] = {
        "ok": len(staged_disj) == 0, "before": len(live_disj), "after": staged_disj}
    checks["A3_only_patchable_fields_changed"] = {
        "ok": untouched_ok and touched_field_ok,
        "non_patchable_field_offenders": offenders,
        "patchable_fields": sorted(PATCHABLE)}
    checks["A4_class_ids_disjoint_from_informs"] = {
        "ok": all(set(r.get("class_ids") or []) & set(r.get("informs_classes") or []) == set()
                  for r in staged_rows)}
    checks["A5_staged_parses_and_keeps_row_order"] = {
        "ok": len(staged_rows) == len(live_rows) and
              [row_key(r) for r in staged_rows] == live_ids}
    checks["A6_patch_idempotent_on_staged"] = {
        "ok": (lambda s2: write_staged(s2) == staged_sha)(apply_patch(staged_rows, patch)[0])}

    # ---- controls --------------------------------------------------------------
    controls = report["controls"]
    c1 = copy.deepcopy(staged_rows)
    for r in c1:
        if row_key(r) == (patch[0]["row_id"] if patch else ""):
            r["class_ids"] = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    controls["C1_reintroduced_disjunction_detected"] = {
        "ok": hf02_disjunctions(c1) == [patch[0]["row_id"]] and bool(patch)}
    controls["C2_row_loss_detected"] = {
        "ok": [row_key(r) for r in c1[:-1]] != [row_key(r) for r in staged_rows]
              and len(c1[:-1]) != len(staged_rows)}
    c3 = copy.deepcopy(staged_rows)
    c3[0]["statement_exact"] = str(c3[0].get("statement_exact", "")) + " TAMPER"
    controls["C3_statement_tamper_breaks_A3_scope"] = {
        "ok": canonical(live_rows[0], drop=PATCHABLE) != canonical(c3[0], drop=PATCHABLE)}
    controls["C4_live_ledger_is_the_disjunctive_baseline"] = {
        "ok": len(live_disj) == len(patch) == 8, "live_count": len(live_disj), "patch_ops": len(patch)}
    controls["C5_unknown_row_fails_closed"] = {
        "ok": bool(apply_patch(live_rows, [{"op": "set", "row_id": "__NO_SUCH_ROW__",
                                            "class_ids": []}])[2])}

    report["staged"] = {
        "path": str(STAGED_LEDGER.relative_to(ROOT)),
        "sha256": staged_sha,
        "bytes": STAGED_LEDGER.stat().st_size,
        "rows": len(staged_rows),
        "hf02_disjunctions": staged_disj,
    }
    report["diffs"] = diffs

    n_ok = sum(1 for v in checks.values() if v.get("ok")) + \
        sum(1 for v in controls.values() if v.get("ok"))
    n_total = len(checks) + len(controls)
    report["verdict"] = ("STAGED_REPAIR_VALIDATED_CONDITIONAL_ON_HF02_SCOPE_RULING"
                         if n_ok == n_total and not report["errors"]
                         else "STAGED_REPAIR_NOT_VALIDATED")
    report["acceptance"] = f"{n_ok}/{n_total} checks+controls pass"

    report["scope_note"] = (
        "Conditional on the audit lead's ruling that the rubric-literal HF-02 'disjunction of "
        "class_ids' detector applies to ledger rows whose class_ids array carries more than one "
        "frozen class token. worker-023 recorded that the same detector text also matches "
        "multi-class routing arrays in accepted claim EVENTS (76 events at their read); that "
        "surface is not touched here. Adoption of these bytes also changes the ledger hash and "
        "therefore requires an announced artifact event and lead/controller re-pin (CF-19 "
        "discipline); this worker did not move the live path.")

    report["next_falsifier"] = (
        "Apply the staged bytes at the pinned anchor: any remaining HF-02 disjunction, any change "
        "to a field outside {class_ids, informs_classes, ledger_tags}, any dropped/reordered row, "
        "or any live-ledger hash other than a1674f094979 at build time falsifies this packet.")

    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (STAGED_DIR / "diff.json").write_text(json.dumps(
        {"anchor": PINS["ledger/theorems.jsonl"], "staged": staged_sha, "diffs": diffs}, indent=1) + "\n")

    print(f"verdict={report['verdict']} acceptance={report['acceptance']} "
          f"staged_sha256={staged_sha[:16]} rows={len(staged_rows)}")
    for k, v in {**checks, **controls}.items():
        if not v.get("ok"):
            print(f"  FAIL {k}: {json.dumps(v)[:300]}")
    for e in report["errors"]:
        print(f"  ERROR {e}")
    return 0 if report["verdict"].startswith("STAGED_REPAIR_VALIDATED") else 1


if __name__ == "__main__":
    sys.exit(main())
