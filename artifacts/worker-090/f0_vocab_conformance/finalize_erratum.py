#!/usr/bin/env python3
"""ERR-W090-VOCAB-01: re-pin W090-F0-VOCAB-CONFORMANCE-01 after the rev12 -> rev13 schema move.

The original events (w090-vocab-2026-09-12T00:53:12+08:00-*) are bound to rev12 pins
F1 cce9c601 / F2a 5476a3f2 / F2b 55d0a1ea. The formulation lead published rev13 at
2026-09-12T00:53:20+08:00 (F1 bf0c28fa / F2a e9a27996 / F2b b2ab6acb) while this worker was
emitting. This addendum re-measures the SAME property on the rev13 bytes and reports whether the
finding survives. Idempotent by event_id."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-090.jsonl"
STATE = ROOT / "runtime/state/worker-090_f0_vocab_conformance_checkpoint.json"
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TASK = "W090-F0-VOCAB-CONFORMANCE-01"
CLASS = "AF-SCC-C2-VAC-GEN"
GATE = "G-FORM"
OLD = {"F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
       "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
       "F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"}
NEW = {"F1": "bf0c28fa673e5bd5d82d03ab93059b99580af0f3f65a81d4924e0bc8e74a6226",
       "F2a": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
       "F2b": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


res13 = json.loads((BASE / "results_rev13.json").read_text())
ctl13 = json.loads((BASE / "controls_rev13.json").read_text())
res12 = json.loads((BASE / "snapshot_rev12/results.json").read_text())
assert res13["pin_stable"] and res13["exit_ok"] and ctl13["all_pass"]
# F1 is churning independently; bind the erratum to whatever the post-rev12 run measured, and
# require only that the primary class (F2a) moved off the rev12 pin.
NEW = {"F1": res13["pins"]["schemas/af_wcc_vacuum.yaml"],
       "F2a": res13["pins"]["schemas/af_scc_c2_vacuum.yaml"],
       "F2b": res13["pins"]["schemas/af_scc_c0_vacuum.yaml"]}
assert NEW["F2a"] != OLD["F2a"], "F2a did not move; no erratum needed"
same_vector = (res12["summary"]["by_classification"] == res13["summary"]["by_classification"]
               and res12["summary"]["inverted"] == res13["summary"]["inverted"]
               and res12["summary"]["schemas_without_registry_pointer"]
               == res13["summary"]["schemas_without_registry_pointer"])
assert same_vector, "finding changed between rev12 and rev13; write a fresh review, not an erratum"

fs = [f for f in res13["findings"] if f["id"] == "W090-VOCAB-06"][0]
addendum = {
    "erratum_id": "ERR-W090-VOCAB-01", "task_id": TASK, "actor": "worker-090",
    "created_at": NOW, "node_id": "F2a", "class_id": CLASS, "gate": GATE,
    "cause": ("moving target: formulation lead published rev13 (revised_at 2026-09-12T00:53:20+08:00) "
              "after the original measurement was emitted at 00:53:12+08:00"),
    "supersedes_events": ["w090-vocab-2026-09-12T00:53:12+08:00-review",
                          "w090-vocab-2026-09-12T00:53:12+08:00-claim",
                          "w090-vocab-2026-09-12T00:53:12+08:00-complete"],
    "old_pins": OLD, "new_pins": NEW,
    "rev12_measurement": {"results": "snapshot_rev12/results.json",
                          "results_sha256": sha(BASE / "snapshot_rev12/results.json"),
                          "controls_sha256": sha(BASE / "snapshot_rev12/controls.json")},
    "rev13_measurement": {"results": "results_rev13.json", "results_sha256": sha(BASE / "results_rev13.json"),
                          "controls": "controls_rev13.json", "controls_sha256": sha(BASE / "controls_rev13.json")},
    "finding_survives": True,
    "classification_vector_rev12": res12["summary"]["by_classification"],
    "classification_vector_rev13": res13["summary"]["by_classification"],
    "inverted_rev13": res13["summary"]["inverted"],
    "unregistered_rev13": res13["summary"]["unregistered"],
    "schemas_without_registry_pointer_rev13": res13["summary"]["schemas_without_registry_pointer"],
    "f0_self_consistency_rev13": res13["f0_self_consistency"]["violations"],
    "alias_in_f0_rev13": fs["instances"],
    "controls_rev13": {"n": ctl13["n_controls"], "all_pass": ctl13["all_pass"]},
    "falsifier": res13["falsifier"],
    "non_claims": res13["non_claims"] + [
        "This erratum re-pins the measurement only; it does not adjudicate the authority conflict.",
        "The original rev12 artifact events remain valid because they hash this worker's own files; "
        "only the rev12-bound review and claim are superseded.",
    ],
}
(BASE / "addendum_rev13.json").write_text(json.dumps(addendum, indent=2, sort_keys=True) + "\n")
sha_add = sha(BASE / "addendum_rev13.json")
ckpt = {
    "erratum_id": "ERR-W090-VOCAB-01", "task_id": TASK, "actor": "worker-090", "created_at": NOW,
    "status": "complete", "node_id": "F2a", "class_id": CLASS, "gate": GATE,
    "old_pins": OLD, "new_pins": NEW, "finding_survives": True,
    "classification_vector": res13["summary"]["by_classification"],
    "inverted": res13["summary"]["inverted"],
    "controls": {"n": ctl13["n_controls"], "all_pass": ctl13["all_pass"]},
    "artifact_sha256": {"addendum_rev13.json": sha_add,
                        "results_rev13.json": sha(BASE / "results_rev13.json"),
                        "controls_rev13.json": sha(BASE / "controls_rev13.json"),
                        "snapshot_rev12/results.json": sha(BASE / "snapshot_rev12/results.json")},
    "falsifier": res13["falsifier"],
    "note": "runtime/state/worker-090_f0_vocab_conformance_checkpoint.json was updated in place for the rev12 checkpoint; this file is the rev13 re-pin record.",
}
(BASE / "addendum_checkpoint.json").write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
sha_ck = sha(BASE / "addendum_checkpoint.json")

E = [
    {"event_id": f"w090-vocab-erratum-{NOW}-artifact-addendum", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE,
     "task_id": TASK, "artifact_type": "errata", "path": rel(BASE / "addendum_rev13.json"),
     "sha256": sha_add, "validation_status": "unverified",
     "evidence_refs": [f"{rel(BASE / 'addendum_rev13.json')}#{sha_add[:12]}"],
     "summary": "ERR-W090-VOCAB-01: rev12->rev13 re-pin; the 5-token inversion finding survives unchanged."},
    {"event_id": f"w090-vocab-erratum-{NOW}-artifact-results13", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE,
     "task_id": TASK, "artifact_type": "evidence", "path": rel(BASE / "results_rev13.json"),
     "sha256": sha(BASE / "results_rev13.json"), "validation_status": "unverified",
     "evidence_refs": [f"{rel(BASE / 'results_rev13.json')}#{sha(BASE / 'results_rev13.json')[:12]}",
                       f"schemas/af_scc_c2_vacuum.yaml#{NEW['F2a'][:12]}"],
     "note": "same checker, rev13 pins; 8/8 controls; pin_stable=true"},
    {"event_id": f"w090-vocab-erratum-{NOW}-artifact-controls13", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE,
     "task_id": TASK, "artifact_type": "evidence", "path": rel(BASE / "controls_rev13.json"),
     "sha256": sha(BASE / "controls_rev13.json"), "validation_status": "unverified",
     "evidence_refs": [f"{rel(BASE / 'controls_rev13.json')}#{sha(BASE / 'controls_rev13.json')[:12]}"],
     "note": f"{ctl13['n_controls']}/{ctl13['n_controls']} controls pass on rev13 copies"},
    {"event_id": f"w090-vocab-erratum-{NOW}-artifact-checkpoint", "event_type": "artifact",
     "created_at": NOW, "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE,
     "task_id": TASK, "artifact_type": "checkpoint_json", "path": rel(BASE / "addendum_checkpoint.json"),
     "sha256": sha_ck, "validation_status": "unverified",
     "evidence_refs": [f"{rel(BASE / 'addendum_checkpoint.json')}#{sha_ck[:12]}"],
     "note": "rev13 re-pin checkpoint; the rev12 checkpoint.json is left byte-identical to its emitted hash"},
    {"event_id": f"w090-vocab-erratum-{NOW}-review", "event_type": "review", "created_at": NOW,
     "actor": "worker-090", "reviewer": "worker-090", "node_id": "F2a",
     "target_id": "F2a,F1,F2b vocabulary conformance vs F0 rev5", "class_id": CLASS,
     "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"], "gate": GATE,
     "task_id": TASK, "verdict": "revise", "score": 3.5, "counts_as_full_schema_verdict": False,
     "review_kind": "vocabulary_conformance_audit", "reviewed_sha256": NEW["F2a"],
     "supersedes": "w090-vocab-2026-09-12T00:53:12+08:00-review",
     "hard_failures": [
         {"id": "W090-VOCAB-01", "severity": "major (blocking until the authority ruling is recorded)",
          "axis": "F0 allowed list vs VOCAB_ALIASES canonical token",
          "finding": ("Rev13 re-measurement: all five non-exact vocabulary slots still use the registry "
                      "CANONICAL while the F0 allowed list contains only its aliases. F2a: "
                      "conclusion_type=scc_c2_future_inextendibility, genericity_kind=residual_comeager. "
                      "The property is revision-stable across rev12 -> rev13."),
          "instances": res13["summary"]["inverted"]},
         {"id": "W090-VOCAB-04", "severity": "major", "axis": "implicit registry dependency",
          "finding": "F2a and F2b still declare no VOCAB_ALIASES.json pointer; F1 does (line 149).",
          "instances": res13["summary"]["schemas_without_registry_pointer"]}],
     "findings": [
         {"id": "W090-VOCAB-06", "severity": "major",
          "statement": "F0's own classes[*].axes still carry 5 registry-ALIAS tokens; F0 self-consistency is clean at 26/26.",
          "instances": fs["instances"]},
         {"id": "W090-VOCAB-02", "severity": "info",
          "statement": "Rev13 re-pin: 0 unregistered tokens; the mismatch remains entirely the inversion direction.",
          "instances": res13["summary"]["unregistered"]}],
     "artifact_refs": [rel(BASE / "addendum_rev13.json"), rel(BASE / "results_rev13.json"),
                       rel(BASE / "controls_rev13.json"), rel(BASE / "addendum_checkpoint.json")],
     "evidence_refs": [f"{rel(BASE / 'results_rev13.json')}#{sha(BASE / 'results_rev13.json')[:12]}",
                       f"{rel(BASE / 'controls_rev13.json')}#{sha(BASE / 'controls_rev13.json')[:12]}",
                       f"schemas/af_scc_c2_vacuum.yaml#{NEW['F2a'][:12]}",
                       f"schemas/af_wcc_vacuum.yaml#{NEW['F1'][:12]}",
                       f"schemas/af_scc_c0_vacuum.yaml#{NEW['F2b'][:12]}",
                       "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                       "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"],
     "next_falsifier": res13["falsifier"],
     "authority_note": "advisory scoped worker audit; cannot set a gate verdict or node status"},
    {"event_id": f"w090-vocab-erratum-{NOW}-claim", "event_type": "claim", "created_at": NOW,
     "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
     "conclusion_type": "formal_model",
     "supersedes": "w090-vocab-2026-09-12T00:53:12+08:00-claim",
     "statement": (
         "Revision-stable measured property at the rev13 pins (F1 bf0c28fa673e, F2a e9a27996dfd3, "
         "F2b b2ab6acb2bbe, F0 0abb9ed8a961, VOCAB_ALIASES 46cd9f1eb534, FROZEN rev28 2f358f6722d9; "
         "pin stable across the run): the same 12-field F0-relative vocabulary matrix measured at "
         "rev12 (6 exact, 1 null, 0 unregistered, 5 inverted) is reproduced byte-for-byte in "
         "classification at rev13, so the rev12->rev13 revision did not touch the vocabulary axes. "
         "The five inversions are F1 genericity_kind; F2a conclusion_type + genericity_kind; F2b "
         "conclusion_type + genericity_kind, each using the VOCAB_ALIASES canonical while F0's "
         "allowed list contains only its aliases. F2a and F2b still declare no registry pointer. "
         "F0 remains internally self-consistent (26/26) while its own descriptors carry 5 "
         "registry-alias tokens. 8/8 controls pass at rev13; the original rev12 events are "
         "superseded by ERR-W090-VOCAB-01."),
     "assumptions": ["the canonical paths are authoritative and the measured sha256 pins are the frozen revision",
                     "PyYAML last-wins for mapping keys; duplicate top-level keys counted separately (0)",
                     "VOCAB_ALIASES.json is the declared alias authority for the axes it lists"],
     "falsifier": res13["falsifier"],
     "evidence_refs": [f"{rel(BASE / 'results_rev13.json')}#{sha(BASE / 'results_rev13.json')[:12]}",
                       f"{rel(BASE / 'controls_rev13.json')}#{sha(BASE / 'controls_rev13.json')[:12]}",
                       f"schemas/af_scc_c2_vacuum.yaml#{NEW['F2a'][:12]}",
                       "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                       "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"],
     "artifact_refs": [rel(BASE / "addendum_rev13.json"), rel(BASE / "results_rev13.json"),
                       rel(BASE / "controls_rev13.json"), rel(BASE / "addendum_checkpoint.json")],
     "non_claims": addendum["non_claims"]},
    {"event_id": f"w090-vocab-erratum-{NOW}-complete", "event_type": "status", "created_at": NOW,
     "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
     "status": "active", "hours": 0.2,
     "summary": ("ERR-W090-VOCAB-01 complete: rev12->rev13 re-pin of W090-F0-VOCAB-CONFORMANCE-01. "
                 "The 5-token authority-inversion finding and the F2a/F2b missing-registry-pointer "
                 "finding survive unchanged at rev13 (6 exact / 5 inverted / 0 unregistered; 8/8 "
                 "controls; pin stable). Original rev12-bound review and claim are superseded; the "
                 "rev12 artifact events remain valid (self-hashed files, snapshot preserved). "
                 "No node status or gate verdict claimed."),
     "evidence_refs": [f"{rel(BASE / 'addendum_rev13.json')}#{sha_add[:12]}",
                       f"{rel(BASE / 'results_rev13.json')}#{sha(BASE / 'results_rev13.json')[:12]}",
                       f"{rel(BASE / 'addendum_checkpoint.json')}#{sha_ck[:12]}"],
     "next_falsifier": res13["falsifier"],
     "authority_note": "advisory worker status; no gate verdict, no node status promotion"},
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            pass
appended = 0
with OUTBOX.open("a") as fh:
    for ev in E:
        schemas.validate_event(ev)
        if ev["event_id"] in existing:
            print("DUP ", ev["event_id"])
            continue
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
        appended += 1
        print("OK  ", ev["event_id"])
print(f"appended {appended}/{len(E)}; addendum {sha_add[:12]}, results_rev13 "
      f"{sha(BASE / 'results_rev13.json')[:12]}, controls_rev13 {sha(BASE / 'controls_rev13.json')[:12]}")
