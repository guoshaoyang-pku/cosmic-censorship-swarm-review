#!/usr/bin/env python3
"""W081-N0-C8-ADJ2-03 finalizer: worker checkpoint + schema-validated event emission.

Writes checkpoint.json in this directory, then appends artifact/review/claim/status events to
comms/outbox/worker-081.jsonl.  Every event is validated with research_map.schemas.validate_event
and duplicate event_ids are refused.  After emission the corrected numerics/gates.py guard is
re-evaluated read-only and the post-emission protocol-review tally is recorded in the
runtime/state sidecar (the mechanical contest is expected to remain true: see README finding 2).

Worker authority limits: no gate verdict, no node completion, no canonical path written,
numerics_lock untouched, no review record altered.

Usage: python3 artifacts/worker-081/n0_c8_adjudication_rev2/finalize_rev2.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-081.jsonl"
STATE = ROOT / "runtime" / "state"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "numerics"))
from research_map.schemas import validate_event  # noqa: E402

PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
PROTOCOL_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
TASK = {"task_id": "W081-N0-C8-ADJ2-03", "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"], "gate": "G-NUM", "actor": "worker-081",
        "instance": "worker-081-20260912T002948-968807"}
FALSIFIER = ("Re-measure the pins: if numerics/CONVERGENCE_PROTOCOL.md is not 1e6cdf04d7a24313 "
             "or numerics/protocol/n0_fixed_dt_certification.json is not 1677822ceb9c81e8, this "
             "adjudication does not bind. It is falsified if any certification row has dt != 1e-4, "
             "if the recomputed statistics disagree with the certification beyond 1e-9 relative, "
             "if the certified claim again cites a constant-CFL study as its basis, or if no filed "
             "constant-dt <= 1e-3 ladder with >= 3 rungs exists (then F1' falsifier predicate is "
             "unmet and the dissent stands).")
INPUT_REFS = [
    f"{PROTOCOL}#{PROTOCOL_SHA}",
    "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8",
    "numerics/protocol/n0_fixed_dt_certification.py#3c7c908783844604",
    "numerics/tests/n0_gate_proposal.json#b4192221ff7d96db",
    "numerics/gates.py#fcd1d70991b6eade",
    "numerics/tests/flat_wave_replication.py#8ade1cdc163ea420",
    "numerics/tests/n0_order_4rung.json#c88146a1375c50f0",
    "numerics/protocol/temporal_subdominance_control.json#334f5b71e0d53ab6",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def append_events(events):
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                existing.add(json.loads(line)["event_id"])
    new = []
    for ev in events:
        validate_event(ev)
        if ev["event_id"] in existing:
            raise SystemExit(f"refusing duplicate event_id {ev['event_id']}")
        existing.add(ev["event_id"])
        new.append(ev)
    with open(OUTBOX, "a") as fh:
        for ev in new:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
    return [ev["event_id"] for ev in new]


def main() -> int:
    adj = json.loads((HERE / "adjudication.json").read_text())
    verdict = adj["verdict"]
    B, C, D, E, F = (adj["check_B_protocol_and_structure"], adj["check_C_independent_arithmetic"],
                     adj["check_D_proposal_binding"], adj["check_E_dissent_falsifier"],
                     adj["check_F_guard_tally"])
    assert verdict["disposition"] == "F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION" and not verdict["blocks_gate_pass"]

    t = now()
    stamp = t.replace(":", "").replace("+", "").replace("-", "")
    files = ["adjudicate_review_contest.py", "adjudication.json", "README.md", "finalize_rev2.py"]
    hashes = {f: sha256(HERE / f) for f in files}

    orders = {s: C["per_scheme"][s]["recomputed"]["fit_order"] for s in ("lffd", "cnfd", "cnfem")}
    deltas = {s: C["per_scheme"][s]["recomputed"]["delta_R5"] for s in ("lffd", "cnfd", "cnfem")}
    max_rel = max(max(C["per_scheme"][s]["rel_err"].values()) for s in ("lffd", "cnfd", "cnfem"))
    ladders = E["E1_filed_constant_dt_ladders"]
    accept_ids = F["accepting_reviews"]
    dissent_ids = [d["event_id"] for d in F["dissenting_reviews"]]

    claim_statement = (
        f"Binding/consistency adjudication at protocol sha256 1e6cdf04d7a24313, certification "
        f"numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8 and proposal "
        f"numerics/tests/n0_gate_proposal.json#b4192221ff7d96db: the two rev-3 revise verdicts "
        f"(worker-067 F1, worker-081 F1') are DISCHARGED BY SUPERSESSION of the evidence basis. All "
        f"12 certified rows have dt = 1e-4 exactly across four rungs; the certification's internal "
        f"statistics (fit orders {orders['lffd']:.6f}/{orders['cnfd']:.6f}/{orders['cnfem']:.6f}, "
        f"delta_R5 {deltas['lffd']:.2e}/{deltas['cnfd']:.2e}/{deltas['cnfem']:.2e}, all monotone, "
        f"all in band, max cross-scheme |dp| {C['computed_max_pairwise_abs_diff']:.3e} vs R5 floor "
        f"0.25) reproduce independently from the filed raw rows to <= {max_rel:.1e} relative; the "
        f"certified claim's study/driver references bind to the measured hashes; the superseded "
        f"constant-CFL study appears only under labelled mixed-order/control/supersedes/registry "
        f"paths; and the F1' falsifier predicate is met by {len(ladders)} filed constant-dt <= 1e-3 "
        f"ladders of four rungs each. The standing audit accept at the current hash is therefore the "
        f"operative protocol verdict, and W081's own F1' revise is closed by its own falsifier. "
        f"Mechanical caveat: numerics/gates.py::_protocol_review still reports contest=true because "
        f"a later accept does not rescind an earlier revise (it also still counts W081's withdrawn "
        f"accept); closing condition #1 needs an explicit controller disposition or a guard "
        f"supersession rule. This is worker-level adjudication: no gate verdict, no node completion, "
        f"no review record altered."
    )
    completion_summary = (
        f"W081-N0-C8-ADJ2-03 complete: rev-3 protocol review contest adjudicated against the "
        f"re-based evidence. Disposition F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION. Structural, "
        f"arithmetic and binding checks pass at the pinned hashes (pins unchanged before/after); "
        f"F1' falsifier predicate met by {len(ladders)} filed constant-dt ladders; standing audit "
        f"accept operative. Guard tally recorded mechanically contest=true "
        f"(accepts={accept_ids}, dissents={dissent_ids}) with the supersession-semantics finding "
        f"for controller action. No gate verdict, no node completion, numerics_lock LOCKED."
    )

    ckpt = {
        "schema": "worker-081/checkpoint/v1",
        **TASK,
        "created_at": t,
        "task_status": "complete",
        "node_status_left": "active",
        "gate_verdict": None,
        "numerics_lock": "untouched",
        "artifact_dir": "artifacts/worker-081/n0_c8_adjudication_rev2",
        "artifact_hashes": hashes,
        "input_pins": adj["input_pins_start"],
        "input_pins_end": adj["input_pins_end"],
        "disposition": verdict["disposition"],
        "blocks_gate_pass": verdict["blocks_gate_pass"],
        "measured": {
            "recomputed_orders": orders,
            "recomputed_delta_R5": deltas,
            "max_stat_relative_error": max_rel,
            "cross_scheme_max_abs_dp": C["computed_max_pairwise_abs_diff"],
            "cross_scheme_filed": C["filed_max_pairwise_abs_diff"],
            "filed_constant_dt_ladders": len(ladders),
            "filed_constant_dt_ladders_4rung": len(E["E1_with_four_rungs"]),
            "guard_tally_pre_emission": {"accepts": accept_ids, "dissents": dissent_ids,
                                         "contest": F["contest"]},
        },
        "falsifier": FALSIFIER,
        "evidence_refs": [f"artifacts/worker-081/n0_c8_adjudication_rev2/{f}#{h[:16]}"
                          for f, h in hashes.items()] + INPUT_REFS,
        "authority_note": ("Worker-level adjudication. Not a gate verdict, not a node completion, "
                           "not an edit of any canonical artifact or review record."),
        "outbox_events": [],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(ckpt, indent=1, sort_keys=True))
    hashes["checkpoint.json"] = sha256(HERE / "checkpoint.json")

    events = []
    artifact_meta = {"adjudicate_review_contest.py": "verification_script",
                     "adjudication.json": "evidence", "README.md": "summary",
                     "checkpoint.json": "checkpoint", "finalize_rev2.py": "verification_script"}
    for f, h in hashes.items():
        events.append({
            "event_id": f"w081-{stamp}-adj2-artifact-{f}",
            "event_type": "artifact", "created_at": t, "actor": "worker-081",
            **{k: TASK[k] for k in ("node_id", "gate", "class_id")},
            "class_ids": TASK["class_ids"], "task_id": TASK["task_id"],
            "artifact_type": artifact_meta[f],
            "path": f"artifacts/worker-081/n0_c8_adjudication_rev2/{f}",
            "sha256": h, "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-081/n0_c8_adjudication_rev2/{f}#{h[:16]}"],
            "note": ("Measured by worker-081; validation_status stays unverified until a "
                     "reviewer/controller binds it. Not a gate verdict and not physics evidence."),
        })

    events.append({
        "event_id": f"w081-{stamp}-adj2-review",
        "event_type": "review", "created_at": t, "actor": "worker-081",
        **{k: TASK[k] for k in ("node_id", "gate", "class_id")},
        "class_ids": TASK["class_ids"], "task_id": TASK["task_id"],
        "target_id": f"{PROTOCOL}#{PROTOCOL_SHA}",
        "reviewed_sha256": PROTOCOL_SHA,
        "reviewer": "worker-081",
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "reviewer_independence": ("bounded breadth worker; author of finding F1' (now closed by its "
                                  "own falsifier) and of a withdrawn earlier accept at this hash; no "
                                  "numerics canonical artifact authored; read-only on canonical paths; "
                                  "wrote only under artifacts/worker-081/n0_c8_adjudication_rev2/."),
        "findings": [
            (f"DISPOSITION F1_AND_F1PRIME_DISCHARGED_BY_SUPERSESSION: the certified evidence basis is "
             f"numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c81e8 with dt=1e-4 exactly on "
             f"all 12 rows and four rungs; independent recomputation reproduces the filed statistics to "
             f"<= {max_rel:.1e} relative; max cross-scheme |dp| {C['computed_max_pairwise_abs_diff']:.3e} "
             f"vs R5 floor 0.25."),
            (f"F1' SELF-FALSIFIER MET: {len(ladders)} filed constant-dt <= 1e-3 ladders with four rungs "
             f"each exist (3 at dt=1e-4 in the certification; 6 at dt=1e-3/5e-4 in "
             f"temporal_subdominance_control.json#334f5b71). W081's revise is closed by its own published "
             f"falsifier; the record is not deleted or rewritten."),
            ("F1 PREMISE FALSE for the current certification: no certified row uses dt ~ h, and the "
             "constant-CFL study c88146a1375c50f0 appears only under labelled mixed-order/control/"
             "supersedes/registry paths (4/4 references labelled)."),
            (f"MECHANICAL GUARD FINDING: numerics/gates.py::_protocol_review at fcd1d709 reports "
             f"accepting_reviews={accept_ids} (the first is W081's withdrawn accept, still counted) and "
             f"dissenting_reviews={dissent_ids}, contest=true. A later accept from a dissent author does "
             f"not rescind the earlier revise, so condition #1 needs an explicit controller disposition "
             f"or a guard supersession rule by (reviewer, target) at the same hash."),
            ("SCOPE: no numerical re-run of the certification ladder (worker-046's separate replication), "
             "no gate verdict, no node completion, no canonical file or review record altered, "
             "numerics_lock stays LOCKED."),
        ],
        "evidence_refs": [f"artifacts/worker-081/n0_c8_adjudication_rev2/{f}#{h[:16]}"
                          for f, h in hashes.items()] + INPUT_REFS,
        "next_falsifier": FALSIFIER,
        "authority_note": ("Worker review event: proposes an accept on the adjudicated basis; does not "
                           "set status=done, validation_status=passed, or any gate verdict."),
    })
    events.append({
        "event_id": f"w081-{stamp}-adj2-claim",
        "event_type": "claim", "created_at": t, "actor": "worker-081",
        **{k: TASK[k] for k in ("node_id", "gate", "class_id")},
        "class_ids": TASK["class_ids"], "task_id": TASK["task_id"],
        "conclusion_type": "formal_model",
        "statement": claim_statement,
        "assumptions": [
            "The adjudicated revisions are the sha256 values measured before and after the run; the disposition binds no other revision.",
            "Both dissents are classified as evidence-basis objections from their own texts: F1 says the certified claim used dt~h; F1' says the filed evidence did not use the protocol's fixed-dt methodology.",
            "The R5 uncertainty rule and the four-rung certification requirement are read from numerics/CONVERGENCE_PROTOCOL.md sections 3.2 and 3.8 at the pinned hash.",
            "The guard tally is the mechanical output of numerics/gates.py::_protocol_review at fcd1d709; it is evidence about the event record, not about the physics.",
            "No numerical row-level re-run was performed here; arithmetic reproduction uses the certification's own filed raw rows.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [f"artifacts/worker-081/n0_c8_adjudication_rev2/{f}#{h[:16]}"
                          for f, h in hashes.items()] + INPUT_REFS,
        "artifact_refs": [f"artifacts/worker-081/n0_c8_adjudication_rev2/{f}#{h[:16]}"
                          for f, h in hashes.items()],
    })
    events.append({
        "event_id": f"w081-{stamp}-adj2-complete",
        "event_type": "status", "created_at": t, "actor": "worker-081",
        **{k: TASK[k] for k in ("node_id", "gate", "class_id")},
        "class_ids": TASK["class_ids"], "task_id": TASK["task_id"],
        "status": "active", "hours": 0.4,
        "summary": completion_summary,
        "evidence_refs": [f"artifacts/worker-081/n0_c8_adjudication_rev2/{f}#{h[:16]}"
                          for f, h in hashes.items()] + INPUT_REFS,
        "next_falsifier": FALSIFIER,
    })

    emitted = append_events(events)

    # post-emission guard tally (read-only): records that the mechanical contest remains
    import gates as G
    tally = G._protocol_review(G.load_event_stream(ROOT), sha256(ROOT / PROTOCOL))
    ckpt["outbox_events"] = emitted
    ckpt["checkpoint_written_at"] = now()
    ckpt["guard_tally_post_emission"] = {
        "accepting_reviews": tally["accepting_reviews"],
        "dissenting_reviews": [d["event_id"] for d in tally["dissenting_reviews"]],
        "contest": tally["contest"],
        "note": "expected to remain true until the controller records a disposition (README finding 2)",
    }
    (STATE / "w081_adj2_checkpoint_1.json").write_text(json.dumps(ckpt, indent=1, sort_keys=True))
    with open(STATE / "w081_adj2_checkpoints.jsonl", "a") as fh:
        fh.write(json.dumps({"checkpoint": "w081_adj2_checkpoint_1.json", "task_id": TASK["task_id"],
                             "created_at": ckpt["created_at"], "disposition": verdict["disposition"],
                             "outbox_events": emitted, "artifact_hashes": hashes,
                             "guard_contest_post_emission": tally["contest"]}, sort_keys=True) + "\n")

    print("emitted", len(emitted), "events:", emitted)
    print("checkpoint:", STATE / "w081_adj2_checkpoint_1.json")
    print("guard post-emission: accepts=", tally["accepting_reviews"],
          "dissents=", [d["event_id"] for d in tally["dissenting_reviews"]], "contest=", tally["contest"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
