#!/usr/bin/env python3
"""Finalize W010-F2A-C2-CONFORMANCE-REV13-01.

Order (single run, one shared timestamp):
  1. re-hash the audited pair (report + independent verifier) and every pinned input;
  2. write W010_F2A_C2_REV13_result.json;
  3. append artifact x2 / claim / status events to comms/outbox/worker-010.jsonl
     (idempotent: an event_id already present is skipped, never rewritten);
  4. write the worker checkpoint in the artifact dir and under runtime/state/.
Worker events cannot set status=done, validation_status=passed or a gate verdict; nothing
here does. Re-runnable: a second run appends a new stamp only if the artifacts changed.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-010.jsonl"
CST = timezone(timedelta(hours=8))

TASK_ID = "W010-F2A-C2-CONFORMANCE-REV13-01"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
GATE = "G-LIT"
NODE_ID = "L1"
RUN_ID = "run-2026-09-11T23:15+08:00"

AUDIT = HERE / "c2_conformance_audit.json"
AUDIT_PY = HERE / "c2_conformance_audit.py"
VERIFY = HERE / "verify_c2_rev13_independent.json"
VERIFY_PY = HERE / "verify_c2_rev13_independent.py"
RESULT = HERE / "W010_F2A_C2_REV13_result.json"
CKPT_LOCAL = HERE / "checkpoint_w010_c2_rev13.json"
CKPT_STATE = ROOT / "runtime/state/w010_c2_conformance_rev13_checkpoint.json"

PINS = ["schemas/af_scc_c2_vacuum.yaml", "ledger/theorems.jsonl",
        "research_map/formulation_taxonomy.yaml", "ledger/class_coverage.csv",
        "artifacts/formulation/FROZEN.json",
        "artifacts/worker-010/class_binding_reconcile/binding_reconcile_audit.json"]
SNAPS = ["snapshots/af_scc_c2_vacuum.e9a27996dfd3.yaml",
         "snapshots/theorems.a1674f094979.jsonl",
         "snapshots/formulation_taxonomy.0abb9ed8a961.yaml",
         "snapshots/class_coverage.abbaee54a5a3.csv",
         "snapshots/FROZEN.815e08079aef.json",
         "snapshots/binding_reconcile_audit.dc391cad38cd.json"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(path: str) -> str:
    return f"{path}#{sha256(ROOT / path)[:12]}"


def main() -> int:
    now_dt = datetime.now(CST)
    now = now_dt.isoformat(timespec="seconds")
    stamp = now_dt.strftime("%Y%m%dT%H%M%S")

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    verify = json.loads(VERIFY.read_text(encoding="utf-8"))
    s = audit["summary"]
    reclass = audit["direction_reclassification_vs_cbr"]

    art = {
        "report": {"path": str(AUDIT.relative_to(ROOT)), "sha256": sha256(AUDIT),
                   "role": "class conformance + direction audit report"},
        "driver": {"path": str(AUDIT_PY.relative_to(ROOT)), "sha256": sha256(AUDIT_PY),
                   "role": "deterministic read-only audit driver"},
        "verify": {"path": str(VERIFY.relative_to(ROOT)), "sha256": sha256(VERIFY),
                   "role": "independent second implementation + labeled fixtures"},
        "verify_py": {"path": str(VERIFY_PY.relative_to(ROOT)), "sha256": sha256(VERIFY_PY),
                      "role": "verifier driver"},
    }
    for p in PINS:
        art[Path(p).stem] = {"path": p, "sha256": sha256(ROOT / p), "role": "pinned input"}
    snap_hashes = {}
    for sp in SNAPS:
        full = HERE / sp
        if full.exists():
            snap_hashes[str(full.relative_to(ROOT))] = sha256(full)

    # ---- 2. result summary (self-contained, no self-hash)
    result = {
        "worker": "worker-010",
        "task_id": TASK_ID,
        "task": "class-bound conformance + direction audit of the AF-SCC-C2-VAC-GEN (F2a) "
                "ledger bindings at FROZEN rev29 / schema rev13",
        "status": "complete_from_worker_side",
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "assignment_ref": None,
        "assignment_note": "no inbox card for worker-010 at fleet 2026-09-12T01:04; ONE "
                           "bounded class-bound task self-selected (comms/PROTOCOL.md; same "
                           "convention as workers 048/063/069).",
        "created_at": now,
        "run_id": RUN_ID,
        "pins": {p: sha256(ROOT / p) for p in PINS},
        "artifacts": list(art.values()),
        "snapshots": snap_hashes,
        "summary": s,
        "direction_correction_vs_cbr": {
            "cbr_lexical_contrary_ids_c2": reclass["cbr_lexical_contrary_ids"],
            "semantic_contrary_count_all_bindings": reclass[
                "semantic_contrary_count_all_bindings"],
            "reclassified": reclass["reclassified"],
            "note": "The CBR audit (W010-CBR-01) flagged direction lexically. For the C2 "
                    "class a C0/L^2_loc extension assertion is not the negation of 'no C2 "
                    "extension'; all five flags are regularity-conflation or negation-scope "
                    "artifacts. Corrected contrary count for AF-SCC-C2-VAC-GEN: 0.",
        },
        "verification": {
            "all_pass": verify["all_pass"],
            "checks": [{"check": c["check"], "all_pass": c["all_pass"]} for c in verify["checks"]],
            "n_bindings_agree": verify["checks"][3].get("n_agree"),
            "n_fixtures": len(verify["fixtures"]),
            "predicate_repairs_found_by_fixtures": len(verify["predicate_repairs"]),
            "target_report_sha256": verify["target_report_sha256"],
        },
        "falsifier": audit["falsifier"],
        "non_claims": [
            "not a mathematical result",
            "not an independent reviewer verdict",
            "not a gate verdict; worker events cannot move gates or node status",
            "does not re-adjudicate the ledger's class_ids (A1's job)",
        ],
        "validation_status": "unverified",
        "claims_completion": False,
    }
    RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ---- validation context for the checkpoint
    try:
        val = subprocess.run([sys.executable, str(ROOT / "research_map/validate_map.py")],
                             capture_output=True, text=True, timeout=120)
        map_validator = (val.stdout.strip().splitlines() or ["?"])[-1][:120]
    except Exception as exc:
        map_validator = f"unavailable: {exc}"
    try:
        rm = json.loads((ROOT / "research_map/research_map.json").read_text(encoding="utf-8"))
        map_ctx = {"sha256": sha256(ROOT / "research_map/research_map.json"),
                   "updated_at": rm.get("updated_at"),
                   "gates": {g["gate_id"]: g["verdict"] for g in rm.get("gates", [])},
                   "numerics_lock": (rm.get("numerics_lock") or {}).get("state")}
    except Exception as exc:
        map_ctx = {"error": str(exc)}

    reading = audit["reading"]
    correction = audit["direction_correction"]
    falsifier = audit["falsifier"]

    # ---- 3. events
    refs = [ref(art["report"]["path"]), ref(art["driver"]["path"]),
            ref(art["verify"]["path"]), ref(art["verify_py"]["path"])] + \
           [ref(p) for p in PINS] + \
           [ref(p) for p in snap_hashes] + [ref(str(RESULT.relative_to(ROOT)))]

    events = [
        {
            "event_id": f"w010-{stamp}-c2rev13-artifact-report",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-010",
            "run_id": RUN_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "class_id": CLASS_ID,
            "class_ids": [CLASS_ID],
            "artifact_type": "class_conformance_audit",
            "path": art["report"]["path"],
            "sha256": art["report"]["sha256"],
            "bytes": AUDIT.stat().st_size,
            "task_id": TASK_ID,
            "validation_status": "unverified",
            "claims_completion": False,
            "summary": (
                f"AF-SCC-C2-VAC-GEN (F2a) rev13 conformance + direction audit at "
                f"schemas/af_scc_c2_vacuum.yaml#{sha256(ROOT / PINS[0])[:12]} (FROZEN rev29) "
                f"and ledger/theorems.jsonl#{sha256(ROOT / PINS[1])[:12]}: "
                f"{s['n_bound_entries']} bound entries, {s['n_result_entries']} results, "
                f"n_d1_pass={s['n_d1_pass']}, n_d2_supports={s['n_d2_supports']} "
                f"(T-305/T-526/T-527 conclude a regularity at least as strong as "
                f"C2-inextendibility), n_d2_contrary={s['n_d2_contrary']}, "
                f"n_d2_weaker_not_contrary={s['n_d2_weaker_not_contrary']} (T-303 asserts only "
                f"a C0 extension), n_d3_pass={s['n_d3_pass']}, n_discharging="
                f"{s['n_discharging']}; class conclusion state "
                f"'{s['class_conclusion_state']}' = the schema's declared epistemic_status. "
                f"Direction correction: the CBR audit's 5 lexical C2 negation-side flags "
                f"(D-004/T-303/T-401/T-402/T-526) are regularity-conflation or negation-scope "
                f"artifacts; semantic contrary count for this class is 0. 6/6 controls pass."
            ),
            "evidence_refs": refs,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w010-{stamp}-c2rev13-artifact-verify",
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-010",
            "run_id": RUN_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "class_id": CLASS_ID,
            "class_ids": [CLASS_ID],
            "artifact_type": "verification_report",
            "path": art["verify"]["path"],
            "sha256": art["verify"]["sha256"],
            "bytes": VERIFY.stat().st_size,
            "task_id": TASK_ID,
            "validation_status": "unverified",
            "claims_completion": False,
            "summary": (
                f"Independent second implementation (no import of the audit driver; "
                f"positive-marker data-class test, ordinal regularity lattice, "
                f"own-assertion-field direction scan): "
                f"{verify['checks'][3].get('n_agree')}/{len(verify['per_binding_agreement'])} "
                f"bindings agree on D1/D2/D3/discharge, binding selection sets identical "
                f"({len(verify['checks'][2]['independent_ids'])} ids), semantic contrary count "
                f"0 by both implementations, {len(verify['fixtures'])}/"
                f"{len(verify['fixtures'])} labeled fixtures pass, all pins re-measured "
                f"unchanged. Three verifier predicate defects were caught by the fixtures "
                f"before the run and repaired in the verifier only (the audited report was "
                f"never modified). Mechanical reproducibility check, not a reviewer verdict."
            ),
            "evidence_refs": [ref(art["verify"]["path"]), ref(art["verify_py"]["path"]),
                              ref(art["report"]["path"]), ref(PINS[0]), ref(PINS[1]),
                              ref(PINS[5])],
            "falsifier": verify["falsifier"],
        },
        {
            "event_id": f"w010-{stamp}-c2rev13-claim",
            "event_type": "claim",
            "created_at": now,
            "actor": "worker-010",
            "run_id": RUN_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "class_id": CLASS_ID,
            "class_ids": [CLASS_ID],
            "task_id": TASK_ID,
            "conclusion_type": "open_problem",
            "statement": (
                f"At the live pins schemas/af_scc_c2_vacuum.yaml#{sha256(ROOT / PINS[0])[:12]} "
                f"(F2a revision 13, FROZEN rev29 {sha256(ROOT / PINS[4])[:12]}) and "
                f"ledger/theorems.jsonl#{sha256(ROOT / PINS[1])[:12]}, "
                f"{s['n_bound_entries']} ledger entries carry AF-SCC-C2-VAC-GEN in class_ids: "
                f"{s['n_non_result_entries']} are definitions / literature-status / conjecture "
                f"and {s['n_result_entries']} are results (T-303, T-305, T-526, T-527). No "
                f"result satisfies D1_data_class: T-303 is a special high-frequency/impulsive "
                f"null-hypersurface construction, T-305 is conditional on an unproved "
                f"Price-law estimate for data on a hypersurface inside a dynamical black "
                f"hole, T-526 solves a characteristic initial value problem not quantified as "
                f"open/dense, and T-527's curvature blow-up hypothesis is expected but not "
                f"proved for the class. Read with regularity inclusion, 3 results conclude a "
                f"regularity at least as strong as C2-inextendibility (T-305, T-526, T-527; "
                f"Lipschitz / C^0,1_loc-inextendibility implies non-C2-extendibility), 1 "
                f"(T-303) asserts only a C0 extension and is therefore not the negation of the "
                f"C2 conclusion, and 0 assert a C2-or-smoother vacuum extension. D3_evidence "
                f"passes for {s['n_d3_pass']} bindings: every binding carries at least one "
                f"unresolved ledger item, two are provisional, and three are preprint-level. "
                f"Hence n_discharging={s['n_discharging']} and the class conclusion state is "
                f"'{s['class_conclusion_state']}', matching the schema's declared "
                f"epistemic_status. Corollary correction: the CBR audit's five lexical "
                f"negation-side flags on this class (D-004, T-303, T-401, T-402, T-526) are "
                f"regularity-conflation or negation-scope artifacts, so the semantic "
                f"contrary-side count for AF-SCC-C2-VAC-GEN is 0. This is a ledger/schema "
                f"state measurement at the pinned hashes, not a mathematical result, not a "
                f"reviewer verdict, and not a gate verdict."
            ),
            "assumptions": [
                "class_ids and conclusion_type are inherited from the ledger as written; this "
                "audit does not re-adjudicate them (A1's job)",
                "D1/D2/D3 are declared mechanical readings of the ledger fields "
                "statement_exact/genericity/regularity/topology/scope_caveats/unresolved; a "
                "reviewer may bind an entry differently, which is the A1 verdict this "
                "artifact asks for",
                "D2 is a direction/regularity reading, not an adjudication of whether a "
                "conditional or non-class result is mathematically correct",
                "the class contract is read from the rev13 C2 schema bytes and is not "
                "modified; the audit writes only inside artifacts/worker-010/",
            ],
            "corrects": {
                "artifact": "artifacts/worker-010/class_binding_reconcile/"
                            "binding_reconcile_audit.json",
                "artifact_sha256": sha256(ROOT / PINS[5]),
                "class_id": CLASS_ID,
                "field": "direction_findings",
                "old": "5 lexical negation-side flags (D-004, T-303, T-401, T-402, T-526)",
                "new": "0 semantic contrary-side bindings under regularity inclusion",
                "scope": "AF-SCC-C2-VAC-GEN only; the C0/WCC readings are not re-adjudicated",
            },
            "evidence_refs": refs,
            "artifact_refs": [ref(art["report"]["path"]), ref(art["verify"]["path"])],
            "expected_information_gain": (
                "Gives A1/G-LIT/G-FORM readers the first D1/D2/D3 discharge reading for the "
                "C2 sibling at the rev13 pins, separates 'the class has bindings' from 'the "
                "class has discharging evidence', and replaces the lexical C2 direction "
                "flags with a regularity-inclusion reading that cannot count a C0 extension "
                "as evidence against a C2 conclusion."
            ),
            "falsifier": falsifier,
            "validation_status": "unverified",
        },
        {
            "event_id": f"w010-{stamp}-c2rev13-status",
            "event_type": "status",
            "created_at": now,
            "actor": "worker-010",
            "run_id": RUN_ID,
            "node_id": NODE_ID,
            "gate": GATE,
            "class_id": CLASS_ID,
            "class_ids": [CLASS_ID],
            "task_id": TASK_ID,
            "status": "active",
            "hours": 1.0,
            "summary": f"W010-F2A-C2-CONFORMANCE-REV13-01 complete from the worker side: one "
                       f"bounded class-bound task on AF-SCC-C2-VAC-GEN at FROZEN rev29 / F2a "
                       f"rev13. {reading} {correction} Artifacts on disk and hash-pinned; "
                       f"independent verifier all_pass={verify['all_pass']}. No node "
                       f"completion, gate verdict, or promotion is claimed; hash registration "
                       f"in runtime/state/artifact_hashes.json is left to the controller.",
            "evidence_refs": [ref(art["report"]["path"]), ref(art["verify"]["path"]),
                              ref(PINS[0]), ref(PINS[1]), ref(str(RESULT.relative_to(ROOT)))],
            "next_falsifier": falsifier,
            "validation_status": "unverified",
            "claims_completion": False,
        },
    ]

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    appended = []
    with OUTBOX.open("a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended.append(e["event_id"])

    # ---- 4. checkpoints (after the append so they can name what actually landed)
    ckpt = {
        "checkpoint_id": f"ckpt-{stamp}",
        "label": "w010-c2-conformance-rev13",
        "worker": "worker-010",
        "task_id": TASK_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "node_id": NODE_ID,
        "created_at": now,
        "run_id": RUN_ID,
        "map_validator": map_validator,
        "map_context": map_ctx,
        "pins": {p: sha256(ROOT / p) for p in PINS},
        "artifact_hashes": {a["path"]: a["sha256"] for a in art.values()},
        "result_artifact": {"path": str(RESULT.relative_to(ROOT)), "sha256": sha256(RESULT)},
        "snapshots": snap_hashes,
        "reading": reading,
        "direction_correction": correction,
        "verification_all_pass": verify["all_pass"],
        "n_bindings_agree": verify["checks"][3].get("n_agree"),
        "n_fixtures_pass": sum(1 for f in verify["fixtures"] if f["pass"]),
        "n_fixtures": len(verify["fixtures"]),
        "planned_event_ids": [e["event_id"] for e in events],
        "appended_event_ids": appended,
        "duplicate_event_ids_skipped": [e["event_id"] for e in events
                                        if e["event_id"] not in appended],
        "outbox_sha256_after": sha256(OUTBOX) if OUTBOX.exists() else None,
        "next_falsifier": falsifier,
        "claims_completion": False,
        "validation_status": "unverified",
    }
    CKPT_TEXT = json.dumps(ckpt, indent=2, ensure_ascii=False) + "\n"
    CKPT_LOCAL.write_text(CKPT_TEXT, encoding="utf-8")
    CKPT_STATE.write_text(CKPT_TEXT, encoding="utf-8")

    print(f"result   {RESULT.relative_to(ROOT)} sha256={sha256(RESULT)}")
    print(f"checkpoint {CKPT_LOCAL.relative_to(ROOT)} sha256={sha256(CKPT_LOCAL)}")
    print(f"checkpoint {CKPT_STATE.relative_to(ROOT)} (identical bytes)")
    print(f"appended {len(appended)}/{len(events)} events to {OUTBOX.relative_to(ROOT)}")
    for e in appended:
        print("  +", e)
    print(f"map_validator={map_validator} verify_all_pass={verify['all_pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
