#!/usr/bin/env python3
"""Emit worker-041 upward events and checkpoint 2 for W041-F0-MIRROR-INDEP-01.

Writes (append for outbox/checkpoint log, replace for the latest checkpoint):
  comms/outbox/worker-041.jsonl
  runtime/state/w041_checkpoint_2.json
  runtime/state/w041_checkpoints.jsonl

Worker authority note: these events claim bounded-execution completion only.
They set no node status, no validation_status=passed, and no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms" / "outbox" / "worker-041.jsonl"
CKPT = ROOT / "runtime" / "state" / "w041_checkpoint_2.json"
CKPT_LOG = ROOT / "runtime" / "state" / "w041_checkpoints.jsonl"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")

REPORT = HERE / "f0_mirror_report.json"
README = HERE / "README.md"
RUNNER = HERE / "run_f0_mirror_indep.py"
RAW = HERE / "raw"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    rep_sha = sha(REPORT)
    sidecar = (HERE / "f0_mirror_report.json.sha256").read_text().split()[0]
    assert rep_sha == sidecar, "report sha256 sidecar mismatch"
    assert doc["hash_stable_across_run"] is True, "pinned inputs drifted during the run"
    assert doc["verdict"] == "CONFIRMED_UNSATISFIABLE_AT_FROZEN_REVISIONS"
    assert doc["admissibility"] == {"A_canonical_eq_authoring_bytes": False,
                                    "B_authoring_eq_canonical_bytes": False}
    ctl = doc["instrument"]["controls"]
    assert ctl["baseline_structural_pass_and_checker_zero"], "baseline control failed"
    assert ctl["merged_new_revision_control_structural_pass_and_checker_zero"], "merged control failed"
    assert ctl["semantic_mutation_control_detected"], "negative control failed"
    # Re-check at emission time: the binding must still be the live one.
    live = {rel: sha(ROOT / rel) for rel in doc["pinned_inputs"]}
    drifted = {rel: {"report": doc["pinned_inputs"][rel]["sha256"], "live": live[rel]}
               for rel in live if live[rel] != doc["pinned_inputs"][rel]["sha256"]}
    assert not drifted, f"inputs drifted before emission: {drifted}"

    raw_hashes = {p.name: sha(p) for p in sorted(RAW.glob("*")) if p.is_file()}
    ts = doc["created_at"][:19].replace("-", "").replace(":", "")
    a_sha = doc["frozen_reference_hashes"]["A_canonical_declared_f0"]
    b_sha = doc["frozen_reference_hashes"]["B_authoring_supplement"]
    f1_sha = doc["pinned_inputs"]["schemas/af_wcc_vacuum.yaml"]["sha256"]
    e7 = doc["baseline_pin_freshness"]["E7_frozen_logical_artifact_pins"]
    stale_pins = [k for k, v in e7["rows"].items() if not v["match"]]
    if stale_pins:
        pin_clause = (
            f"FROZEN.json logical-artifact pins are stale against disk at this measurement for "
            f"{', '.join(stale_pins)} and need re-issue."
        )
    else:
        pin_clause = (
            "FROZEN.json rev27 pins match the live bytes for both logical artifacts (the "
            "transient pin lag seen mid-run was re-issued during the measurement chain); the "
            "two-logical-artifact resolution is on record with mirrors: NONE for both."
        )

    summary = (
        "No assignment card exists in comms/inbox for worker-041. Took ONE bounded "
        "class-bound task on the live F0 critical-path blocker: W041-F0-MIRROR-INDEP-01 = "
        "independent hash-pinned test of leadform-blocker-0007 / CF-13 at the live revisions "
        f"(A declared-F0 {a_sha[:12]}, B class-contract supplement {b_sha[:12]}, F1 {f1_sha[:12]}). "
        "Exhaustive case analysis of the only byte-identical directions (A:=B, B:=A) in isolated "
        "sandboxes against the frozen consumers (declared-F0 structure, supplement structure, "
        "per-class identity axes, three schema class_contract_pointers, three declared-F0 hash "
        "pins, FROZEN.json logical-artifact pins) plus the frozen taxonomy-consistency checker "
        "run byte-identically. Verdict CONFIRMED_UNSATISFIABLE_AT_FROZEN_REVISIONS: A:=B loses "
        "class_contracts/axis_registry/implication_ledger and all three pointers become "
        "unresolvable; B:=A loses class_ids/classes/transfer_rules and the declared-F0 hash "
        "pins break; the checker exits 1 (KeyError) in both directions. A merged new revision "
        f"passes every structural consumer and the checker. PIN STATE: {pin_clause} A first "
        "measurement at A=276009f4/F1=9a8bd4c9 and a second at FROZEN=2554e276 were both voided "
        "by the republish chain and re-run per this task's own falsifier. Controls all pass."
    )
    ev_status = {
        "event_id": f"w041-f0mirror-{ts}-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "status": "active",
        "hours": 0.7,
        "task_id": "W041-F0-MIRROR-INDEP-01",
        "completion_scope": "bounded worker lifecycle only; not a node done or gate verdict",
        "summary": summary,
        "evidence_refs": [
            f"artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json#{rep_sha[:12]}",
            f"research_map/formulation_taxonomy.yaml#{a_sha[:12]}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{b_sha[:12]}",
            f"artifacts/formulation/FROZEN.json#{doc['pinned_inputs']['artifacts/formulation/FROZEN.json']['sha256'][:12]}",
            "artifacts/formulation/evidence/f0_mirror_conflict.json",
        ],
        "next_falsifier": doc["falsifier"],
        "artifact": "artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json",
        "to": ["astra", "astra-lead-formulation", "astra-lead-audit"],
    }
    ev_artifact = {
        "event_id": f"w041-f0mirror-{ts}-artifact",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F0",
        "gate": "G-F0",
        "artifact_type": "f0_mirror_independent_verification",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "path": "artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json",
        "sha256": rep_sha,
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": (
            "Independent F0 mirror-conflict case analysis at the live revisions: 5 sandbox cases "
            "x 7 frozen-consumer checks x the frozen checker; both byte-identical directions "
            "inadmissible, merged new revision passes structural consumers but is a new sha256; "
            f"baseline FROZEN.json pins stale for {', '.join(stale_pins)}. Raw per-case checker "
            "stdout/stderr and structure JSON retained under artifacts/worker-041/f0_mirror_indep/"
            "raw/. Worker artifact: no gate verdict, no node status, no validation_status=passed."
        ),
        "evidence_refs": [
            f"artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json#{rep_sha[:12]}",
            f"artifacts/worker-041/f0_mirror_indep/README.md#{sha(README)[:12]}",
            f"artifacts/worker-041/f0_mirror_indep/run_f0_mirror_indep.py#{sha(RUNNER)[:12]}",
            "artifacts/formulation/evidence/f0_mirror_conflict.json",
            "artifacts/formulation/FROZEN.json",
        ] + [f"artifacts/worker-041/f0_mirror_indep/raw/{k}#{v[:12]}"
             for k, v in raw_hashes.items()],
        "falsifier": doc["falsifier"],
        "to": ["astra", "astra-lead-formulation", "astra-lead-audit"],
    }
    ev_claim = {
        "event_id": f"w041-f0mirror-{ts}-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "statement": (
            f"At pinned live revisions A=research_map/formulation_taxonomy.yaml#{a_sha[:12]} "
            f"(rev5) and B=artifacts/formulation/formulation_taxonomy.yaml#{b_sha[:12]} (both "
            "measured stable across the run), neither byte-identical publication direction is "
            "admissible: A:=B deletes class_contracts/axis_registry/implication_ledger and makes "
            "all three schema class_contract_pointers unresolvable; B:=A deletes class_ids/"
            "classes/transfer_rules and breaks the three declared_f0_sha256 pins; the frozen "
            "check_taxonomy_consistency.py exits 1 in both directions. A single merged file "
            "carrying both key sets passes every structural consumer and the checker but has a "
            "new sha256, so it is a new revision, not a byte-identical publication of a frozen "
            "one. The admitted resolution is two logical artifacts (now on record in FROZEN rev27 "
            "logical_artifacts with mirrors: NONE) or a merged re-freeze with re-issued pins and "
            f"pointers. Pin state at this measurement: {pin_clause}"
        ),
        "conclusion_type": "formal_model",
        "assumptions": [
            "Byte-identical publication means content(A)=content(B) at the two named paths.",
            "The frozen consumers are the ones measured here: the three canonical schema "
            "pointers and f0_binding pins, FROZEN.json logical_artifacts pins, and the frozen "
            "taxonomy-consistency checker; class_separation and the schemas consume only the "
            "schema bytes, which are unchanged apart from their own republish.",
            "VOCAB_ALIASES.json alias normalization as shipped at the pinned hash.",
        ],
        "falsifier": doc["falsifier"],
        "evidence_refs": [
            f"artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json#{rep_sha[:12]}",
            f"research_map/formulation_taxonomy.yaml#{a_sha[:12]}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{b_sha[:12]}",
            "artifacts/formulation/evidence/f0_mirror_conflict.json",
        ],
        "artifact_refs": [
            f"artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json#{rep_sha[:12]}",
            f"artifacts/worker-041/f0_mirror_indep/raw/dir_A_canonical_eq_authoring.structure.json#{raw_hashes.get('dir_A_canonical_eq_authoring.structure.json','')[:12]}",
            f"artifacts/worker-041/f0_mirror_indep/raw/dir_B_authoring_eq_canonical.structure.json#{raw_hashes.get('dir_B_authoring_eq_canonical.structure.json','')[:12]}",
        ],
        "to": ["astra", "astra-lead-formulation", "astra-lead-audit"],
    }
    ev_review = {
        "event_id": f"w041-f0mirror-{ts}-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "target_id": "artifacts/formulation/evidence/f0_mirror_conflict.json",
        "reviewer": "worker-041",
        "verdict": "accept",
        "score": 4,
        "reviewed_sha256": sha(ROOT / "artifacts/formulation/evidence/f0_mirror_conflict.json"),
        "scope": "independent_reproduction_and_extension_of_the_F0_mirror_conflict_claim",
        "counts_as_gate_verdict": False,
        "hard_failures": [],
        "findings": [
            "The lead's structural claim is independently reproduced at the live revisions: A "
            "top-level keys are classes/class_ids/transfer_rules; B top-level keys are "
            "class_contracts/axis_registry/implication_ledger; the three schema "
            "class_contract_pointers resolve only in B, and the three declared_f0_sha256 pins "
            "name A (now 0abb9ed8).",
            "Both byte-identical directions were executed, not just argued: A:=B -> checker "
            "KeyError 'class_contracts'; B:=A -> checker KeyError 'class_ids'; the E1-E7 "
            "consumer checks fail in both.",
            "Extension (new evidence): a merged file carrying both key sets passes all "
            "structural consumers and the frozen checker (exit 0, 4 classes, 0 divergences), but "
            "breaks the frozen pins as expected for a new revision. This distinguishes "
            "'unsatisfiable at the frozen revisions' from 'impossible in principle'.",
            f"New finding at emission time (pin discipline): {pin_clause}",
            "Constructive: FROZEN rev27 logical_artifacts already records the admitted "
            "resolution (F0-declared-taxonomy with mirrors NONE + F0-class-contract-supplement); "
            "the superseded byte-identity requirement should be adjudicated, not forced.",
            "A first measurement at A=276009f4/F1=9a8bd4c9 and a second at FROZEN=2554e276 were "
            "invalidated by the republish chain and re-run per the task's own falsifier; the "
            "live binding is the one cited here.",
        ],
        "evidence_refs": [
            f"artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json#{rep_sha[:12]}",
            f"artifacts/formulation/evidence/f0_mirror_conflict.json#{sha(ROOT / 'artifacts/formulation/evidence/f0_mirror_conflict.json')[:12]}",
            f"research_map/formulation_taxonomy.yaml#{a_sha[:12]}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{b_sha[:12]}",
        ],
        "next_falsifier": doc["falsifier"],
        "to": ["astra", "astra-lead-formulation", "astra-lead-audit"],
    }
    events = [ev_status, ev_artifact, ev_claim, ev_review]
    with OUTBOX.open("a", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    ckpt = {
        "checkpoint": 2,
        "at": NOW,
        "worker": "worker-041",
        "instance": "worker-041-20260912T002444-968807",
        "lifecycle": "bounded execution worker; exited after one class-bound task",
        "assignment_taken": {
            "kind": "class-bound task taken from the live F0/G-F0 critical-path blocker; no card "
                    "in comms/inbox/worker-041.jsonl",
            "task": "W041-F0-MIRROR-INDEP-01 independent hash-pinned test of the F0 mirror "
                    "conflict (leadform-blocker-0007 / CF-13 / astra-life02-publish-f0)",
            "node_id": "F0",
            "gate": "G-F0",
            "class_ids": CLASS_IDS,
            "why_not_duplicative": (
                "lead evidence f0_mirror_conflict.json asserts the two paths are different "
                "artifacts but does not execute the byte-identical directions; worker-005 "
                "measured pointer/keys statically; this task materialises A:=B and B:=A in "
                "isolated sandboxes and runs the frozen checker plus all pinned consumers in "
                "each, adding the merged-revision control and the baseline pin-freshness check"
            ),
        },
        "hours_spent_estimate": 0.7,
        "artifacts": {
            "artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json": rep_sha,
            "artifacts/worker-041/f0_mirror_indep/README.md": sha(README),
            "artifacts/worker-041/f0_mirror_indep/run_f0_mirror_indep.py": sha(RUNNER),
            **{f"artifacts/worker-041/f0_mirror_indep/raw/{k}": v for k, v in raw_hashes.items()},
        },
        "pins": doc["frozen_reference_hashes"],
        "schema_pins": {k: v["sha256"] for k, v in doc["pinned_inputs"].items()
                        if k.startswith("schemas/")},
        "frozen_json_sha256": doc["pinned_inputs"]["artifacts/formulation/FROZEN.json"]["sha256"],
        "hash_stable_across_run": doc["hash_stable_across_run"],
        "drift_end_of_run": doc["drift_end_of_run"],
        "verdict": doc["verdict"],
        "admissibility": doc["admissibility"],
        "controls": ctl,
        "stale_frozen_pins": stale_pins,
        "events_emitted": [e["event_id"] for e in events],
        "next_falsifier": doc["falsifier"],
        "authority_note": (
            "worker event: cannot set status=done, validation_status=passed, or any gate "
            "verdict; controller/leads own those with artifact+review evidence"
        ),
    }
    CKPT.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with CKPT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ckpt, ensure_ascii=False) + "\n")
    print(json.dumps({
        "outbox": str(OUTBOX.relative_to(ROOT)),
        "checkpoint": str(CKPT.relative_to(ROOT)),
        "report_sha256": rep_sha,
        "events": [e["event_id"] for e in events],
        "stale_frozen_pins": stale_pins,
        "raw_files": len(raw_hashes),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
