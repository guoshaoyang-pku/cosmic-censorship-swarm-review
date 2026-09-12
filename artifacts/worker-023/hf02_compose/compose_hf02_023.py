#!/usr/bin/env python3
"""W023-HF02-COMPOSE-01 -- composition test of the two open HF-02 remediation proposals.

One bounded class-bound task, worker-023 (instance 20260912T003734), node L0, gate G-LIT,
classes AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN (the six SCC rows of the eight-row set).

Question. Two remediation proposals exist for L0-HF-02 at the frozen ledger hash:
  (P-DATA) artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json
           re-binds the eight disjunctive ledger rows (class_ids -> [] or one class;
           coverage moves to informs_classes + ledger_tags).
  (P-CODE) artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff
           adds check_ledger_class_disjunction to artifacts/audit/audit_lib.py, implementing
           the rubric-literal HF-02 branch for ledger records.
Do they compete, or compose? What is the predicted rubric-literal HF-02 count on the eight
rows under {neither, code only, data only, both}?

Method. Deterministic, fail-closed on pin drift. The P-CODE checker is extracted verbatim from
the diff and executed against in-memory copies of the ledger; the P-DATA patch is applied in
memory only. No input file is modified; no gate verdict, node status or validation_status is set.

Exit codes: 0 all expectations met; 1 expectation failure; 2 pin drift (fail closed).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-023/hf02_compose"
TZ = timezone(timedelta(hours=8))

PINS = {
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json":
        "0f86158c5bb79adac957a4585a6be4b62abf13c541ea74769f9e629749c4f9d6",
    "artifacts/worker-023/l0_hf02/hf02-verify-023.json":
        "4f4f6e10dcda16d40cd7598643acdfadff8cbfc59464585e07c8ad442229702f",
    "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff":
        "0247a5c93acc0e015d09cf4dcec8c643696d4328b748c871857fb82cc9b4669a",
    "artifacts/audit/audit_lib.py":
        "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
EXPECTED_8 = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]


@dataclass
class Violation:
    """Signature-compatible shim for audit_lib.Violation (extracted checker uses it)."""
    hf: str
    severity: str
    where: str
    detail: str
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"hf": self.hf, "severity": self.severity, "where": self.where,
                "detail": self.detail, "evidence": self.evidence}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def pin_check() -> dict:
    measured, bad = {}, []
    for rel, want in PINS.items():
        got = sha256_file(ROOT / rel)
        measured[rel] = got
        if got != want:
            bad.append({"path": rel, "declared": want, "measured": got})
    return {"ok": not bad, "measured": measured, "drift": bad}


def load_ledger() -> list[dict]:
    return [json.loads(l) for l in (ROOT / "ledger/theorems.jsonl").read_text().splitlines() if l.strip()]


def row_id(r: dict) -> str:
    return r.get("theorem_id") or r.get("claim_id") or r.get("event_id") or "<record>"


def extract_checker(diff_path: Path) -> str:
    """Extract the added function verbatim (strip exactly one leading '+')."""
    lines, in_hunk, added = diff_path.read_text().splitlines(), False, []
    for ln in lines:
        if ln.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if ln.startswith("+++") or ln.startswith("---"):
            continue
        if ln.startswith("+"):
            added.append(ln[1:])
    src = "\n".join(added).strip("\n") + "\n"
    if "def check_ledger_class_disjunction" not in src:
        raise SystemExit("extraction failed: function not found in diff")
    compile(src, "checker_093_extracted.py", "exec")
    return src


def rubric_hf02_text() -> str:
    txt = (ROOT / "evaluation_rubric.yaml").read_text()
    m = re.search(r"- id: HF-02\n(?:.*\n){0,6}", txt)
    return m.group(0) if m else ""


def detector_023(records: list[dict], classes: set[str]) -> list[dict]:
    """Independent re-derivation of the rubric-literal class_ids disjunction set."""
    out = []
    for r in records:
        cids = sorted({c for c in (r.get("class_ids") or []) if c in classes})
        if len(cids) >= 2:
            out.append({"row_id": row_id(r), "class_ids": cids})
    return out


def detector_invented(records: list[dict], classes: set[str]) -> list[dict]:
    out = []
    for r in records:
        for c in r.get("class_ids") or []:
            if c not in classes and c not in ("DEFINITIONS", "GLOBAL"):
                out.append({"row_id": row_id(r), "token": c})
    return out


def detector_hf14(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        accepted = (str(r.get("status", "")).lower() in ("accepted", "passed")
                    or r.get("supports_claim") is True
                    or str(r.get("validation_status", "")).lower() == "passed")
        has_review = bool(r.get("reviewer_verdicts") or r.get("review_verdict") or r.get("reviewed_by"))
        if accepted and not has_review:
            out.append({"row_id": row_id(r)})
    return out


def detector_hf01_literal(records: list[dict]) -> list[dict]:
    return [{"row_id": row_id(r)} for r in records
            if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")]


def apply_data_patch(records: list[dict], patch: list[dict]) -> tuple[list[dict], list[dict]]:
    """Apply the P-DATA proposal in memory; return (patched, op_log). Fail on unknown row/op."""
    by_id = {row_id(r): json.loads(json.dumps(r)) for r in records}
    log = []
    for op in patch:
        if op.get("op") != "set":
            raise SystemExit(f"unsupported op {op.get('op')!r}")
        rid = op["row_id"]
        if rid not in by_id:
            raise SystemExit(f"patch references unknown row {rid!r}")
        r = by_id[rid]
        before = {"class_ids": r.get("class_ids"), "informs_classes": r.get("informs_classes")}
        if "class_ids" in op:
            r["class_ids"] = list(op["class_ids"])
        if "informs_classes" in op:
            r["informs_classes"] = list(op["informs_classes"])
        tags = list(r.get("ledger_tags") or [])
        for t in op.get("ledger_tags_add") or []:
            if t not in tags:
                tags.append(t)
        r["ledger_tags"] = tags
        log.append({"row_id": rid, "before": before,
                    "after": {"class_ids": r["class_ids"], "informs_classes": r["informs_classes"],
                              "ledger_tags": tags}})
    return list(by_id.values()), log


def class_coverage(records: list[dict], classes: list[str]) -> dict:
    cov = {}
    for c in classes:
        in_ids = sum(1 for r in records if c in (r.get("class_ids") or []))
        in_any = sum(1 for r in records if c in (r.get("class_ids") or [])
                     or c in (r.get("informs_classes") or []))
        cov[c] = {"in_class_ids": in_ids, "in_class_ids_or_informs": in_any}
    return cov


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    created = now()
    pc = pin_check()
    if not pc["ok"]:
        rep = {"schema": "w023-hf02-compose/v1", "task_id": "W023-HF02-COMPOSE-01",
               "status": "PIN_DRIFT_FAIL_CLOSED", "created_at": created, "pins": pc}
        (OUT / "composition-023.PINDRIFT.json").write_text(json.dumps(rep, indent=1) + "\n")
        print("PIN DRIFT -- fail closed:", json.dumps(pc["drift"], indent=1))
        return 2

    classes = set(FROZEN)
    records = load_ledger()
    packet_path = "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json"
    packet = json.loads((ROOT / packet_path).read_text())
    patch = packet["proposed_patch"]
    diff_src = extract_checker(ROOT / "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff")
    (OUT / "checker_093_extracted.py").write_text(
        "# extracted verbatim from artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff\n"
        f"# source diff sha256: {PINS['artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff']}\n"
        "# executed with a signature-compatible audit_lib.Violation shim; do not edit by hand\n\n" + diff_src)
    ns = {"Violation": Violation}
    exec(compile(diff_src, "checker_093_extracted.py", "exec"), ns)
    d093 = ns["check_ledger_class_disjunction"]

    patched, op_log = apply_data_patch(records, patch)

    # ---- scenario matrix -----------------------------------------------------------------
    s0 = [v.as_dict() for v in d093(records, {c: {} for c in FROZEN})]
    s1 = [v.as_dict() for v in d093(patched, {c: {} for c in FROZEN})]
    indep0 = detector_023(records, classes)
    indep1 = detector_023(patched, classes)
    scenarios = {
        "S0_neither": {"rubric_literal_hf02_count": len(s0), "rows": sorted(v["where"] for v in s0)},
        "S1_code_only": {"rubric_literal_hf02_count": len(s0),
                         "note": "P-CODE is a detector; with the ledger unchanged it reports the same 8 rows"},
        "S2_data_only": {"rubric_literal_hf02_count": len(indep1),
                         "note": "P-DATA removes the rows, but the canonical audit still has no branch to see them"},
        "S3_both": {"rubric_literal_hf02_count": len(s1), "rows": sorted(v["where"] for v in s1)},
    }
    # ---- invariants ----------------------------------------------------------------------
    checks = []
    got8 = sorted(r["row_id"] for r in indep0)
    checks.append({"id": "C-DISJ-SET", "ok": got8 == sorted(EXPECTED_8),
                   "detail": f"independent detector set {got8} equals the packet's declared eight-row set"})
    checks.append({"id": "C-COMPOSE-ZERO", "ok": len(s1) == 0 and len(indep1) == 0,
                   "detail": "both the extracted P-CODE checker and the independent detector return 0 on the patched ledger"})
    checks.append({"id": "C-PATCH-COMPLETE", "ok": sorted(o["row_id"] for o in op_log) == sorted(EXPECTED_8),
                   "detail": "all eight rows are addressed by the P-DATA patch; no extra rows"})
    bad_bind, bad_unknown, overlap = [], [], []
    for r in patched:
        if row_id(r) not in EXPECTED_8:
            continue
        ids = set(r.get("class_ids") or [])
        inf = set(r.get("informs_classes") or [])
        if not (ids | inf):
            bad_bind.append(row_id(r))
        if not ids <= classes or not inf <= classes:
            bad_unknown.append(row_id(r))
        if ids & inf:
            overlap.append(row_id(r))
    checks.append({"id": "C-COVERAGE-KEPT", "ok": not bad_bind,
                   "detail": f"every patched row keeps a binding channel (class_ids or informs_classes); failures={bad_bind}"})
    checks.append({"id": "C-FROZEN-ONLY", "ok": not bad_unknown,
                   "detail": f"every post-patch token is one of the frozen four; failures={bad_unknown}"})
    checks.append({"id": "C-DISJOINT-CHANNELS", "ok": not overlap,
                   "detail": f"class_ids and informs_classes are disjoint per row; failures={overlap}"})
    reg = {
        "invented_tokens_before": len(detector_invented(records, classes)),
        "invented_tokens_after": len(detector_invented(patched, classes)),
        "hf14_before": len(detector_hf14(records)),
        "hf14_after": len(detector_hf14(patched)),
        "hf01_literal_before": len(detector_hf01_literal(records)),
        "hf01_literal_after": len(detector_hf01_literal(patched)),
    }
    checks.append({"id": "C-NO-NEW-VIOLATIONS",
                   "ok": reg["invented_tokens_after"] == 0 and reg["hf14_after"] == 0
                         and reg["hf01_literal_after"] == reg["hf01_literal_before"],
                   "detail": "the P-DATA patch adds no invented-token, HF-14 or literal-HF-01 violation"})
    cov_before, cov_after = class_coverage(records, FROZEN), class_coverage(patched, FROZEN)
    coverage_delta = {}
    for c in FROZEN:
        b = {row_id(r) for r in records
             if c in (r.get("class_ids") or []) or c in (r.get("informs_classes") or [])}
        a = {row_id(r) for r in patched
             if c in (r.get("class_ids") or []) or c in (r.get("informs_classes") or [])}
        coverage_delta[c] = {"gained": sorted(a - b), "lost": sorted(b - a)}
    cov_outside = [c for c in FROZEN
                   if not set(coverage_delta[c]["gained"]) <= set(EXPECTED_8)
                   or not set(coverage_delta[c]["lost"]) <= set(EXPECTED_8)]
    checks.append({"id": "C-COVERAGE-DELTA-CONFINED", "ok": not cov_outside,
                   "detail": ("every per-class coverage change (class_ids union informs_classes) is confined to the "
                              "eight rows; pre-patch counts were inflated by the disjunctions themselves, so exact "
                              f"equality is not expected; classes with out-of-set deltas: {cov_outside}")})

    # ---- controls ------------------------------------------------------------------------
    def count_for(rs):
        return len(detector_023(rs, classes))

    drop_526 = [o for o in patch if o["row_id"] != "T-526"]
    mut_t402 = json.loads(json.dumps(patch))
    for o in mut_t402:
        if o["row_id"] == "T-402":
            o["class_ids"] = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    mut_dup = json.loads(json.dumps(patch))
    for o in mut_dup:
        if o["row_id"] == "D-004":
            o["class_ids"] = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    mut_unknown = json.loads(json.dumps(patch))
    for o in mut_unknown:
        if o["row_id"] == "T-303":
            o["class_ids"] = ["AF-SCC-NOT-A-CLASS"]
    p_drop, _ = apply_data_patch(records, drop_526)
    p_t402, _ = apply_data_patch(records, mut_t402)
    p_dup, _ = apply_data_patch(records, mut_dup)
    p_unk, _ = apply_data_patch(records, mut_unknown)
    # extended detector: would also scan informs_classes (documented boundary, must NOT be HF-02)
    ext = [row_id(r) for r in patched if len({c for c in (r.get("informs_classes") or []) if c in classes}) >= 2]
    controls = [
        {"id": "K1-positive-unpatched", "expect": "8", "got": str(count_for(records)), "ok": count_for(records) == 8},
        {"id": "K2-drop-T526-op", "expect": "1 (T-526)", "got": str(count_for(p_drop)),
         "ok": count_for(p_drop) == 1 and detector_023(p_drop, classes)[0]["row_id"] == "T-526"},
        {"id": "K3-reintroduce-T402-disjunction", "expect": "1 (T-402)", "got": str(count_for(p_t402)),
         "ok": count_for(p_t402) == 1 and detector_023(p_t402, classes)[0]["row_id"] == "T-402"},
        {"id": "K4-reintroduce-disjunction", "expect": "1 (D-004)", "got": str(count_for(p_dup)),
         "ok": count_for(p_dup) == 1},
        {"id": "K5-unknown-token", "expect": "invented-token detector fires", "got": str(len(detector_invented(p_unk, classes))),
         "ok": len(detector_invented(p_unk, classes)) == 1},
        {"id": "K6-extended-informs-scan", "expect": "T-402 would fire if the checker wrongly scanned informs_classes",
         "got": str(ext), "ok": ext == ["T-402"]},
    ]

    # ---- adjacent observation (claim events) --------------------------------------------
    claims = []
    with (ROOT / "research_map/events.jsonl").open() as f:
        for line in f:
            if '"class_ids"' not in line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("event_type") == "claim":
                cids = sorted({c for c in (ev.get("class_ids") or []) if c in classes})
                if len(cids) >= 2:
                    claims.append({"actor": ev.get("actor"), "event_id": ev.get("event_id"), "class_ids": cids})
    adjacent = {
        "claim_events_with_class_ids_disjunction": len(claims),
        "events_stream_sha256_at_read": sha256_file(ROOT / "research_map/events.jsonl"),
        "note": ("Same rubric-literal detector text ('disjunction of class_ids') also matches accepted claim "
                 "events that carry a multi-class class_ids routing array; the canonical check_class_binding "
                 "uses the singular class_id and a statement-text scan, so neither surface has a class_ids-array "
                 "branch. Scope decision belongs to astra-lead-audit; reported, not adjudicated here."),
        "sample": claims[:3],
    }
    matrix_digest = hashlib.sha256(json.dumps(scenarios, sort_keys=True).encode()).hexdigest()
    checker_sha = sha256_file(OUT / "checker_093_extracted.py")

    def matrix_view() -> dict:
        s0b = [v.as_dict() for v in d093(records, {c: {} for c in FROZEN})]
        s1b = [v.as_dict() for v in d093(patched, {c: {} for c in FROZEN})]
        return {
            "S0_neither": {"rubric_literal_hf02_count": len(s0b), "rows": sorted(v["where"] for v in s0b)},
            "S1_code_only": {"rubric_literal_hf02_count": len(s0b),
                             "note": "P-CODE is a detector; with the ledger unchanged it reports the same 8 rows"},
            "S2_data_only": {"rubric_literal_hf02_count": len(detector_023(patched, classes)),
                             "note": "P-DATA removes the rows, but the canonical audit still has no branch to see them"},
            "S3_both": {"rubric_literal_hf02_count": len(s1b), "rows": sorted(v["where"] for v in s1b)},
        }

    m1 = hashlib.sha256(json.dumps(matrix_view(), sort_keys=True).encode()).hexdigest()
    m2 = hashlib.sha256(json.dumps(matrix_view(), sort_keys=True).encode()).hexdigest()
    controls.append({"id": "K7-matrix-determinism", "expect": "identical matrix digest on a second in-process pass",
                     "got": m1[:16], "ok": m1 == m2 == matrix_digest})

    payload = {
        "schema": "w023-hf02-compose/v1",
        "artifact_id": "w023-hf02-composition-" + created.replace("-", "").replace(":", "").replace("+", ""),
        "task_id": "W023-HF02-COMPOSE-01",
        "actor": "worker-023",
        "worker_slot": "023",
        "created_at": created,
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "hard_failure_targeted": "HF-02 class_leakage (disjunction of class_ids) at ledger/theorems.jsonl",
        "authority": ("Worker evidence and proposal-composition test only. No input file modified, no ledger edit, "
                      "no rubric/validator edit, no gate verdict, no node status, no validation_status=passed."),
        "applied": False,
        "pins": pc,
        "frozen_classes": FROZEN,
        "disjunctive_row_set": sorted(EXPECTED_8),
        "proposals_compared": {
            "P-DATA": {"path": "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json",
                       "sha256": PINS["artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json"],
                       "kind": "data re-binding of 8 ledger rows; predicts 0 class_ids disjunctions"},
            "P-CODE": {"path": "artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff",
                       "sha256": PINS["artifacts/worker-093/l0_rev3_review/proposed_hf02_disjunction_patch.diff"],
                       "kind": "validator branch check_ledger_class_disjunction for ledger records"},
        },
        "rubric_hf02_excerpt": rubric_hf02_text(),
        "scenario_matrix": scenarios,
        "scenario_matrix_digest": matrix_digest,
        "op_log": op_log,
        "checks": checks,
        "regression": reg,
        "class_coverage_before": cov_before,
        "class_coverage_after_in_class_ids_or_informs": cov_after,
        "class_coverage_delta": coverage_delta,
        "controls": controls,
        "adjacent_observation": adjacent,
        "conclusion": {
            "composition": ("P-CODE and P-DATA are complementary, not competing: P-CODE is the missing detector for "
                            "the rubric branch, P-DATA is the repair of the eight rows the branch is meant to catch. "
                            "Ordered application (P-CODE then P-DATA, or either order; the two touch disjoint files) "
                            "yields rubric-literal HF-02 count 0 on the eight rows with every canonical ledger-scope "
                            "check unchanged."),
            "state_at_pin": ("At ledger a1674f094979 the defect is unfixed: 8 rows still carry two frozen class_ids "
                             "and the canonical audit has no ledger branch to see it (audit_run.py ledger loop checks "
                             "invented tokens only)."),
            "owner_action": ("Apply P-CODE to artifacts/audit/audit_lib.py and wire check_ledger_class_disjunction into "
                             "the ledger loop of audit_run.py, then apply P-DATA to ledger/theorems.jsonl as one "
                             "announced revision with a sha256-carrying artifact event. Neither is a worker edit."),
        },
        "open_questions": [
            "Scope of the class_ids-array branch for claim events (adjacent_observation) belongs to astra-lead-audit.",
            "T-526 remains flagged for an F1 membership ruling before its class_ids -> informs_classes rebinding is final.",
        ],
        "falsifiers": [
            "Re-running this script at the same pins returns a scenario matrix other than S0=8, S3=0.",
            "The P-DATA patch as applied leaves any row with >=2 frozen class_ids, or with no binding channel.",
            "The extracted P-CODE checker differs textually from the diff (extraction sha256 recorded below).",
            "The ledger hash moves from a1674f094979 (all predictions void at any other hash).",
            "P-CODE as committed upstream does not contain check_ledger_class_disjunction or is not wired into the ledger loop.",
        ],
        "extracted_checker": {
            "path": "artifacts/worker-023/hf02_compose/checker_093_extracted.py",
            "sha256": checker_sha,
            "extraction": ("verbatim '+' lines of the P-CODE diff hunk with one leading '+' stripped; compiled "
                           "and executed in-process with a signature-compatible Violation shim"),
        },
        "runner": {
            "path": "artifacts/worker-023/hf02_compose/compose_hf02_023.py",
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "validation_status": "unverified",
        "reproduction": "python3 artifacts/worker-023/hf02_compose/compose_hf02_023.py",
    }
    (OUT / "composition-023.json").write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    artifact_sha = sha256_file(OUT / "composition-023.json")
    (OUT / "composition-023.json.sha256").write_text(artifact_sha + "  composition-023.json\n")

    digest = None
    ok = all(c["ok"] for c in checks) and all(c["ok"] for c in controls) and len(s1) == 0
    print(json.dumps({"task": "W023-HF02-COMPOSE-01", "artifact_sha256": artifact_sha,
                      "checker_extracted_sha256": checker_sha, "scenarios": scenarios,
                      "checks_ok": [c["id"] for c in checks if not c["ok"]],
                      "controls_ok": all(c["ok"] for c in controls), "all_ok": ok}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
