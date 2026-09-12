#!/usr/bin/env python3
"""Emit worker-068 HELDOUT-09 artifacts + claim + checkpoint.

Writes:
  comms/outbox/worker-068.jsonl          (validated upward events, one JSON/line)
  runtime/state/w068_checkpoint_1.json   (bounded-task checkpoint)
  runtime/state/w068_checkpoints.jsonl   (append-only checkpoint log)

Every sha256 is computed from the file on disk at emit time. Never sets a map gate
verdict or a node status; status events stay `active` with claims_completion=false.

Usage: python3 emit_comms.py [--dry-run]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-068.jsonl"
CKPT = ROOT / "runtime" / "state" / "w068_checkpoint_1.json"
CKPT_LOG = ROOT / "runtime" / "state" / "w068_checkpoints.jsonl"

TASK = "W068-FORM-HELDOUT-09"
NODE = "A1"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
PRIMARY_CLASS = "AF-WCC-VAC-GEN"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#sha256:{sha(ROOT / rel)[:12]}"


def main(dry_run: bool) -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    report = json.loads((HERE / "report.json").read_text())
    raw = json.loads((HERE / "raw_verdicts.json").read_text())
    ag = report["aggregates"]
    if not raw["valid"]:
        print("REFUSING to emit: run invalid:", raw["invalid_reasons"], file=sys.stderr)
        return 2

    files = {
        "manifest": "artifacts/worker-068/heldout3/manifest.json",
        "report": "artifacts/worker-068/heldout3/report.json",
        "raw": "artifacts/worker-068/heldout3/raw_verdicts.json",
        "sensitivity": "artifacts/worker-068/heldout3/gate_sensitivity_check.json",
        "validity": "artifacts/worker-068/heldout3/leak_validity_review.json",
        "builder": "artifacts/worker-068/heldout3/build_corpus.py",
        "runner": "artifacts/worker-068/heldout3/run_heldout3.py",
        "emitter": "artifacts/worker-068/heldout3/emit_artifacts.py",
        "submission": "artifacts/worker-068/heldout3/SUBMISSION.md",
        "escaped_fixture": "artifacts/worker-068/heldout3/mutants/c0_03_conclusion_negated.yaml",
    }
    h = {k: sha(ROOT / v) for k, v in files.items()}
    binding = report["frozen_revision_binding"]

    events = []

    def ev(eid, etype, **kw):
        e = {"event_id": eid, "event_type": etype, "created_at": now, "actor": "worker-068",
             "task_id": TASK, "claims_completion": False}
        e.update(kw)
        events.append(e)

    ev("w068-hel09-01-task-claim", "status", node_id=NODE, class_id=PRIMARY_CLASS,
       class_ids=CLASSES, status="active", hours=0.3,
       summary=("No assignment card exists in comms/inbox for worker-068 (100-worker fleet launched 00:12/00:16). "
                "Taking one bounded class-bound task: W068-FORM-HELDOUT-09 = third held-out class-binding corpus, "
                "built from the current canonical bytes and bound to the FROZEN revision measured at build time. "
                "Deliverable is a measurement + escaped-family report; no gate verdict, no node completion."),
       evidence_refs=["artifacts/formulation/FROZEN.json", "comms/PROTOCOL.md"],
       next_falsifier=("An independent reviewer classifying the escaped fixture as a non-leak, or a later FROZEN "
                       "revision catching the same fixture text, invalidates the escape family."))

    artifact_specs = [
        ("w068-hel09-02-manifest", "heldout_corpus_manifest", files["manifest"],
         "Corpus manifest: 35 leaky mutants + 6 known-rejected controls + 4 conforming controls + 4 HELDOUT-08 escape "
         "references, per-fixture sha256, mutation ops, expected catcher rules, frozen revision binding."),
        ("w068-hel09-03-report", "heldout_corpus_report", files["report"],
         f"HELDOUT-09 report: union escape {ag['leaky_escaped_union']}/{ag['leaky']} "
         f"({ag['union_escape_rate']:.4f}); stage A caught {ag['caught_stage_a']}, stage B caught {ag['caught_stage_b']}; "
         f"false positives {ag['false_positives']}; known-rejected controls "
         f"{ag['known_rejected_controls_rejected']}/{ag['known_rejected_controls']}; HELDOUT-08 escapes still escaping "
         f"{ag['known_escape_references_still_escaping']}/{ag['known_escape_references']}."),
        ("w068-hel09-04-raw", "raw_gate_verdicts", files["raw"],
         "Per-fixture stage-A/stage-B verdicts with failed rules, rejected checks, stderr and drift/validity flags."),
        ("w068-hel09-05-sensitivity", "gate_sensitivity_check", files["sensitivity"],
         "Gate-liveness check: 6/6 FORM-HELDOUT-07 known-rejected leaks still rejected; 4/4 FORM-HELDOUT-08 escape "
         "families still escape at the current revision (replication, not validity)."),
        ("w068-hel09-06-validity", "leak_validity_review", files["validity"],
         "Author-side (explicitly NON-INDEPENDENT) classification of the 35 leaky fixtures; independent adjudication "
         "required before escape families are cited."),
        ("w068-hel09-07-builder", "corpus_builder", files["builder"],
         "Deterministic builder; refuses to run when live canonical bytes differ from the FROZEN manifest entry."),
        ("w068-hel09-08-runner", "corpus_runner", files["runner"],
         "Two-stage runner with post-build drift check and known-rejected positive controls."),
        ("w068-hel09-09-submission", "submission_note", files["submission"],
         "SUBMISSION.md: binding table, method, results, escaped fixture, non-claims, falsifier, reproduction."),
        ("w068-hel09-10-escaped", "escaped_fixture", files["escaped_fixture"],
         "The single union escape: C0 conclusion polarity inverted while the C0 token is kept; R11 checks the token, "
         "not statement polarity against negation_normal_form."),
    ]
    for eid, atype, rel, summary in artifact_specs:
        ev(eid, "artifact", node_id=NODE, class_ids=CLASSES, artifact_type=atype, path=rel,
           sha256=sha(ROOT / rel), validation_status="unverified", gate=GATE, group_id="formulation",
           summary=summary, evidence_refs=[ref(rel), f"artifacts/formulation/FROZEN.json#rev{binding['revision']}"],
           next_falsifier="Independent review of this artifact; any canonical republish voids the binding.")

    ev("w068-hel09-11-claim", "claim", node_id=NODE, class_id=PRIMARY_CLASS, class_ids=CLASSES,
       conclusion_type="numerical_evidence",
       statement=(f"At FROZEN revision {binding['revision']}, the two-stage class-binding pipeline catches "
                  f"{ag['union_caught']}/{ag['leaky']} held-out class-bound mutants (union escape rate "
                  f"{ag['union_escape_rate']:.4f}). The single union escape is c0_03_conclusion_negated: the C0 "
                  f"conclusion statement is logically inverted while class_id and conclusion_type stay C0-valid, and "
                  f"neither stage detects it. 4/4 conforming controls are accepted (0 false positives), 6/6 "
                  f"FORM-HELDOUT-07 known-rejected leaks are still rejected, and 4/4 FORM-HELDOUT-08 escape families "
                  f"still escape. This is a measurement claim about the gates, not a class-truth claim."),
       assumptions=[
           f"Binding: canonical schemas equal FROZEN revision {binding['revision']} at build and run time "
           f"(W {binding['schemas']['schemas/af_wcc_vacuum.yaml'][:12]}, C2 "
           f"{binding['schemas']['schemas/af_scc_c2_vacuum.yaml'][:12]}, C0 "
           f"{binding['schemas']['schemas/af_scc_c0_vacuum.yaml'][:12]}).",
           f"Stage hashes fixed: structural {raw['stage_hashes']['structural'][:12]}, semantic "
           f"{raw['stage_hashes']['semantic'][:12]}, rule spec {raw['stage_hashes']['rule_spec'][:12]}.",
           "Escape = accepted by BOTH stages; leak labels are author-side and need independent adjudication.",
       ],
       falsifier=("An independent reviewer classifying c0_03_conclusion_negated as a legitimate formulation removes "
                  "the escape family; a later FROZEN revision in which the same fixture text is caught invalidates it; "
                  "canonical drift between build and run voids the run (runner checks and records it)."),
       evidence_refs=[ref(files["report"]), ref(files["raw"]), ref(files["sensitivity"]),
                      ref(files["validity"]), ref(files["escaped_fixture"])],
       artifact_refs=[files["report"], files["raw"], files["manifest"]],
       gate=GATE, group_id="formulation", review_status="unverified")

    ev("w068-hel09-12-blocker-polarity", "blocker", node_id=NODE, class_ids=CLASSES,
       description=("Class-binding blind spot: conclusion polarity/statement-content inversion is not checked. "
                    "c0_03_conclusion_negated keeps class_id, conclusion_type and all required slots valid but "
                    "asserts the negation of the frozen C0 conclusion; both stages accept it. The 4 persistent "
                    "FORM-HELDOUT-08 escape families (adm-mass-erasure, containment-reversal, "
                    "completeness-definition-swap, data-domain-contradiction) also remain accepted at rev25."),
       needed_to_unblock=("Independent reviewer adjudication of c0_03_conclusion_negated, and either an R11 extension "
                          "comparing conclusion.statement_formal polarity/content against negation_normal_form or a "
                          "documented blind-spot entry for the polarity check."),
       evidence_refs=[ref(files["escaped_fixture"]), ref(files["sensitivity"]), ref(files["report"])],
       gate=GATE, group_id="formulation", next_falsifier=("A revised gate that rejects c0_03_conclusion_negated, or an "
                                                          "independent verdict that the fixture is not a leak."))

    summary_ck = (f"CHECKPOINT 1: HELDOUT-09 built and run valid at FROZEN rev{binding['revision']}. "
                  f"escape {ag['leaky_escaped_union']}/{ag['leaky']}; stage A {ag['caught_stage_a']}, "
                  f"stage B {ag['caught_stage_b']}; fp {ag['false_positives']}; known-rejected "
                  f"{ag['known_rejected_controls_rejected']}/{ag['known_rejected_controls']}; escape refs persisting "
                  f"{ag['known_escape_references_still_escaping']}/{ag['known_escape_references']}.")
    ev("w068-hel09-13-checkpoint", "status", node_id=NODE, class_ids=CLASSES, status="active", hours=0.6,
       summary=summary_ck,
       evidence_refs=[ref(files["report"]), ref(files["raw"])],
       next_falsifier="Independent adjudication of the escaped fixture; re-run only on a fresh revision or assignment.")

    ev("w068-hel09-14-complete", "status", node_id=NODE, class_ids=CLASSES, status="active", hours=0.7,
       summary=("Bounded worker lifecycle complete (W068-FORM-HELDOUT-09). Artifacts + events emitted; worker is "
                "exiting for recycling. No node completion, validation_status=passed, or gate verdict is claimed."),
       evidence_refs=[ref(files["submission"]), ref(files["manifest"])],
       next_falsifier="See w068-hel09-12-blocker-polarity and the report next_falsifier.")

    checkpoint = {
        "checkpoint": 1,
        "at": now,
        "worker": "worker-068",
        "task_id": TASK,
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASSES,
        "hours_spent_estimate": 0.7,
        "status": {"delivered": True, "validation_status": "unverified",
                   "no_completion_claim": "worker cannot set done/passed/gate verdict"},
        "frozen_revision_binding": binding,
        "measurement": {
            "valid": raw["valid"],
            "leaky": ag["leaky"],
            "union_escape_rate": ag["union_escape_rate"],
            "escaped_fixtures": report["escaped_fixtures"],
            "stage_a_caught": ag["caught_stage_a"],
            "stage_b_caught": ag["caught_stage_b"],
            "false_positives": ag["false_positives"],
            "known_rejected_controls": ag["known_rejected_controls_rejected"],
            "known_escape_references_still_escaping": ag["known_escape_references_still_escaping"],
            "per_class": report["per_class"],
        },
        "artifacts": {v: {"sha256": h[k]} for k, v in files.items()},
        "events": [e["event_id"] for e in events],
        "falsifier": report["next_falsifier"],
        "next_falsifier": ("Independent reviewer adjudicates c0_03_conclusion_negated; a later FROZEN revision that "
                           "catches it closes the polarity blind spot."),
    }

    if dry_run:
        print(json.dumps({"events": len(events), "checkpoint": checkpoint["checkpoint"],
                          "escaped": report["escaped_fixtures"]}, indent=1))
        return 0

    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    CKPT.write_text(json.dumps(checkpoint, indent=2) + "\n")
    with CKPT_LOG.open("a") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")
    print(json.dumps({"wrote": str(OUTBOX.relative_to(ROOT)), "events": len(events),
                      "checkpoint": str(CKPT.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--dry-run" in sys.argv))
