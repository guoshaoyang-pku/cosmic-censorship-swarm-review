#!/usr/bin/env python3
"""W068-FORM-DEFFREEZE-13 event emitter + final checkpoint (worker-068).

Reads the artifacts written by run_deffreeze13.py, validates every emitted event against
research_map/schemas.py, appends them to comms/outbox/worker-068.jsonl (idempotent by
event_id), and writes checkpoint_final.json with the full artifact hash set and the task
event-id list. Measurement only: no gate verdict, no node completion, no validation_status
above `unverified`.

Usage: python3 emit_events.py
Exit: 0 emitted (or already present); 2 validation/precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-068.jsonl"
TASK = "W068-FORM-DEFFREEZE-13"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
NOW = datetime.now(CST).isoformat(timespec="seconds")

sys.path.insert(0, str(ROOT / "research_map"))
try:
    from schemas import validate_event  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"cannot import research_map/schemas.py: {e}", file=sys.stderr)
    sys.exit(2)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#sha256:{sha256_file(ROOT / rel)[:12]}"


def main() -> int:
    report_path = HERE / "report.json"
    checkpoint_path = HERE / "checkpoint.json"
    for p in (report_path, checkpoint_path):
        if not p.is_file():
            print(f"missing {p}; run run_deffreeze13.py first", file=sys.stderr)
            return 2
    report = json.loads(report_path.read_text())
    checkpoint = json.loads(checkpoint_path.read_text())
    if not report.get("valid"):
        print("report.valid is false; refusing to emit", file=sys.stderr)
        return 2
    ct = report["freeze_evaluation"]["catch_tables"]
    iso = ct["isolated4"]
    union = ct["union_escapes"]
    p12 = ct["polarity12_content_probes"]
    fp = ct["control_false_positives"]
    minimal_iso = report["freeze_evaluation"]["minimal_subsets_isolated"]
    minimal_ref = report["freeze_evaluation"]["minimal_subsets_reference"]
    isolated_manifest = json.loads((HERE / "isolated_manifest.json").read_text())

    artifacts = {
        "rule": "artifacts/worker-068/deffreeze13/definition_freeze_check.py",
        "builder": "artifacts/worker-068/deffreeze13/build_isolated.py",
        "isolated_manifest": "artifacts/worker-068/deffreeze13/isolated_manifest.json",
        "runner": "artifacts/worker-068/deffreeze13/run_deffreeze13.py",
        "raw": "artifacts/worker-068/deffreeze13/raw_verdicts.json",
        "report": "artifacts/worker-068/deffreeze13/report.json",
        "candidate_rule": "artifacts/worker-068/deffreeze13/candidate_rule.json",
        "checkpoint": "artifacts/worker-068/deffreeze13/checkpoint.json",
        "readme": "artifacts/worker-068/deffreeze13/README.md",
    }
    for k, rel in artifacts.items():
        if not (ROOT / rel).is_file():
            print(f"missing artifact {k}: {rel}", file=sys.stderr)
            return 2

    common = {"actor": "worker-068", "node_id": "A1", "gate": GATE,
              "group_id": "formulation", "class_ids": CLASSES}
    events = [
        {**common, "event_id": "w068-def13-01-active", "event_type": "status",
         "created_at": NOW, "status": "active", "hours": 0.5,
         "summary": ("W068-FORM-DEFFREEZE-13 taken from the open W068-P12-G1 queue item (no inbox "
                     "card): definition-site freeze R-CAND-D + mutation-isolation audit of the four "
                     "FORM-HELDOUT-08 reference escapes."),
         "evidence_refs": [ref(artifacts["isolated_manifest"]), ref(artifacts["checkpoint"])],
         "next_falsifier": ("A leaf re-diff showing an isolated fixture differs from the pinned base at "
                            "more than its declared mutation leaf; or a stage rejection of one at the "
                            "pinned hashes.")},
        {**common, "event_id": "w068-def13-02-artifact-rule", "event_type": "artifact",
         "created_at": NOW, "class_id": "AF-WCC-VAC-GEN",
         "artifact_type": "candidate_gate_rule", "path": artifacts["rule"],
         "sha256": sha256_file(ROOT / artifacts["rule"]), "validation_status": "unverified",
         "evidence_refs": [ref(artifacts["report"]), ref(artifacts["candidate_rule"])]},
        {**common, "event_id": "w068-def13-03-artifact-isolated", "event_type": "artifact",
         "created_at": NOW, "class_id": "AF-SCC-C0-VAC-GEN",
         "artifact_type": "mutation_isolated_corpus", "path": artifacts["isolated_manifest"],
         "sha256": sha256_file(ROOT / artifacts["isolated_manifest"]), "validation_status": "unverified",
         "evidence_refs": [ref(artifacts["report"])],
         "note": ("4 fixtures, one verified single-leaf mutation each: m04 data_class.adm_mass.sign, "
                  "m16 implication_ledger.extension_class_containment, m25 i_plus.completeness_definition, "
                  "m29 quantifiers.domains.D2.definition")},
        {**common, "event_id": "w068-def13-04-artifact-report", "event_type": "artifact",
         "created_at": NOW, "class_id": "AF-SCC-C0-VAC-GEN",
         "artifact_type": "measurement_report", "path": artifacts["report"],
         "sha256": sha256_file(ROOT / artifacts["report"]), "validation_status": "unverified",
         "evidence_refs": [ref(artifacts["raw"]), ref(artifacts["readme"])]},
        {**common, "event_id": "w068-def13-05-claim", "event_type": "claim",
         "created_at": NOW, "class_id": "AF-WCC-VAC-GEN", "conclusion_type": "numerical_evidence",
         "statement": ("Definition-site freeze measurement (proposal R-CAND-D, not adopted): the four "
                       "labelled FORM-HELDOUT-08 mutations, isolated to exactly one leaf each on the "
                       "pinned rev11 base, are accepted by BOTH class-binding stages (4/4 escape) - the "
                       "reference-corpus catch is confounded because a metadata-only freeze and an "
                       "identity-only freeze each flag 4/4 reference fixtures while the conclusion "
                       "freeze flags 0/4; the minimal freeze family for 4/4 isolated catch with zero "
                       f"control false positives is {minimal_iso}; freeze_contract_min catches "
                       f"{iso['freeze_contract_min']['flagged']}/4 isolated, "
                       f"{union['freeze_contract_min']['flagged']}/18 union escapes, "
                       f"{p12['freeze_contract_min']['flagged']}/27 statement-axis probes, with "
                       f"{fp['freeze_contract_min']['flagged']}/19 control false positives. The minimal "
                       f"family on the confounded reference corpus is {minimal_ref}."),
         "assumptions": ["pinned rev11 class bases are the intended frozen contract bytes",
                         "the four mutation values copied from the heldout3 reference fixtures are the "
                         "intended labelled mutations (worker-068 labels; independent adjudication open)",
                         "escape is defined as accepted by both pinned stages"],
         "falsifier": report["falsifier"],
         "evidence_refs": [ref(artifacts["report"]), ref(artifacts["raw"]),
                           ref(artifacts["candidate_rule"]), ref(artifacts["isolated_manifest"])],
         "artifact_refs": [artifacts["rule"], artifacts["isolated_manifest"], artifacts["report"]]},
        {**common, "event_id": "w068-def13-06-blocker-independent", "event_type": "blocker",
         "created_at": NOW,
         "description": ("(1) R-CAND-D is a proposal with no independent adjudication: the isolated "
                         "corpus, the four mutation labels and the rule are all worker-068-built. "
                         "(2) The four isolated fixtures escape both stages at the pinned hashes; an "
                         "independent executor (not worker-068) must reproduce this before the escape "
                         "count is cited. (3) The owner must decide whether registry annotations "
                         "(anti_scope / class_identity_variants) stay outside the contract freeze; two "
                         "legitimate accepted controls are flagged by identity-inclusive variants."),
         "needed_to_unblock": ("Lead-formulation / lead-audit adjudication: commission an independent "
                               "executor (not worker-068) to re-run both pinned stages on the isolated "
                               "corpus; commission an independent reviewer to adjudicate the four "
                               "labelled mutations and to rule on the identity-registry scope."),
         "evidence_refs": [ref(artifacts["report"]), ref(artifacts["candidate_rule"]),
                           ref(artifacts["isolated_manifest"])],
         "next_falsifier": ("An independent re-run that rejects any isolated fixture; an independent "
                            "reviewer classifying a labelled mutation as a non-leak; or an owner-adopted "
                            "stage revision that rejects one at a new hash.")},
        {**common, "event_id": "w068-def13-07-complete", "event_type": "status",
         "created_at": NOW, "status": "active", "hours": 0.6, "claims_completion": False,
         "summary": ("Bounded worker lifecycle complete (W068-FORM-DEFFREEZE-13). Artifacts and events "
                     "emitted; worker exits for recycling. No node completion, validation_status=passed "
                     "or gate verdict is claimed; open items are carried by w068-def13-06-blocker-independent."),
         "evidence_refs": [ref(artifacts["readme"]), ref(artifacts["report"]),
                           ref(artifacts["candidate_rule"])],
         "next_falsifier": "See w068-def13-06-blocker-independent and report.json next_falsifier."},
    ]

    # checkpoint_final lists events 01..07 and the full artifact hash set
    final = {
        "checkpoint_id": "w068-ckpt-deffreeze13-final",
        "task_id": TASK, "worker": "worker-068", "created_at": NOW,
        "global_checkpoint_ref": checkpoint.get("checkpoint_id"),
        "valid": report["valid"],
        "summary": checkpoint["summary"],
        "task_event_ids": [e["event_id"] for e in events],
        "artifacts": {str(p.relative_to(ROOT)): sha256_file(p)
                      for p in sorted(HERE.rglob("*")) if p.is_file()},
        "non_claims": report["non_claims"],
    }
    final_path = HERE / "checkpoint_final.json"
    final_path.write_text(json.dumps(final, indent=2, sort_keys=True))

    events.append({**common, "event_id": "w068-def13-08-checkpoint-confirm", "event_type": "status",
                   "created_at": NOW, "status": "active", "hours": 0.6, "claims_completion": False,
                   "summary": ("Post-checkpoint confirmation: worker-local final checkpoint written with "
                               "the full artifact hash set and the task event-id list; the 15-minute "
                               "global cycle ingests these outbox events."),
                   "evidence_refs": [ref("artifacts/worker-068/deffreeze13/checkpoint_final.json"),
                                     ref(artifacts["report"])],
                   "next_falsifier": "See w068-def13-06-blocker-independent."})

    for e in events:
        try:
            validate_event(e)
        except Exception as ex:
            print(f"event validation failed for {e.get('event_id')}: {ex}", file=sys.stderr)
            return 2

    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                continue
    emitted = [e for e in events if e["event_id"] not in existing]
    if emitted:
        with OUTBOX.open("a") as f:
            for e in emitted:
                f.write(json.dumps(e, sort_keys=True) + "\n")
    print(json.dumps({"outbox": str(OUTBOX.relative_to(ROOT)),
                      "emitted": [e["event_id"] for e in emitted],
                      "already_present": [e["event_id"] for e in events if e["event_id"] in existing],
                      "checkpoint_final": str(final_path.relative_to(ROOT)),
                      "checkpoint_final_sha256": sha256_file(final_path)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
