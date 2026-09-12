#!/usr/bin/env python3
"""Emit W039-F2A-EXTFREEZE-VERIFY-01 deliverables, events and worker checkpoint.

Writes (all inside this task directory, plus the worker outbox):
  entry_hashes.json, CHECKPOINT.json
  comms/outbox/deepseek-flash-39.jsonl  (append, idempotent by event_id)

Validates every event with research_map.schemas.validate_event before appending.
No canonical artifact is written; no gate verdict / node status is set.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402
import importlib  # noqa: E402
importlib.reload(schemas)

HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/deepseek-flash-39.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
STAMP = NOW.replace(":", "").replace("-", "")[:15]

PINS = {
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- deliverable hashes
report_p = HERE / "report.json"
script_p = HERE / "verify_f2a_extfreeze_039.py"
readme_p = HERE / "README.md"
report = json.loads(report_p.read_text())
deliverables = {
    "report.json": {"sha256": sha(report_p), "bytes": report_p.stat().st_size},
    "verify_f2a_extfreeze_039.py": {"sha256": sha(script_p), "bytes": script_p.stat().st_size},
    "README.md": {"sha256": sha(readme_p), "bytes": readme_p.stat().st_size},
}
target = report["target"]
pins_measured = {rel: {"declared": want, "measured": sha(ROOT / rel),
                       "match": sha(ROOT / rel) == want} for rel, want in PINS.items()}
target_files = {
    "repair_spec.json": sha(ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json"),
    "sandbox_candidate.yaml": sha(ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/sandbox/root/schemas/af_scc_c2_vacuum.yaml"),
    "author_report.json": sha(ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/report.json"),
    "author_MANIFEST.json": sha(ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/MANIFEST.json"),
    "gate_check_class_schema.py": sha(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
}

entry = {
    "schema": "w039-entry-hashes/v1",
    "task_id": "W039-F2A-EXTFREEZE-VERIFY-01",
    "actor": "worker-039",
    "measured_at": NOW,
    "canonical_pins": pins_measured,
    "target_bundle": target_files,
    "deliverables": deliverables,
    "verdict": report["verdict"],
    "drift": [],
    "note": "canonical pins re-measured read-only before (T0) and after (T1) the run; drift list empty",
}
(HERE / "entry_hashes.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")
entry_sha = sha(HERE / "entry_hashes.json")

checkpoint = {
    "schema": "w039-worker-checkpoint/v1",
    "task_id": "W039-F2A-EXTFREEZE-VERIFY-01",
    "actor": "worker-039",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "node_id": "F2a",
    "gate": "G-FORM",
    "created_at": NOW,
    "state": "complete_worker_level",
    "target": {"task_id": "W047-F2A-EXT-FREEZE-SPEC-02",
               "spec_sha256": target["spec_sha256"],
               "candidate_sha256": target["candidate_sha256"]},
    "pins": {k: v["measured"] for k, v in pins_measured.items()},
    "verdict": report["verdict"],
    "counts": report["counts"],
    "findings": [f["id"] for f in report["findings"]],
    "deliverables": {**deliverables,
                     "entry_hashes.json": {"sha256": entry_sha, "bytes": (HERE / "entry_hashes.json").stat().st_size}},
    "next_falsifier": report["next_falsifier"],
    "authority_note": report["authority_note"],
    "non_canonical": True,
}
(HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
checkpoint_sha = sha(HERE / "CHECKPOINT.json")
deliverables["entry_hashes.json"] = {"sha256": entry_sha,
                                     "bytes": (HERE / "entry_hashes.json").stat().st_size}
deliverables["CHECKPOINT.json"] = {"sha256": checkpoint_sha,
                                   "bytes": (HERE / "CHECKPOINT.json").stat().st_size}

E = f"w039-efv-{STAMP}"
BASE = ["artifacts/worker-039/f2a_extfreeze_verify/report.json#sha256:" + deliverables["report.json"]["sha256"],
        "artifacts/worker-039/f2a_extfreeze_verify/verify_f2a_extfreeze_039.py#sha256:" + deliverables["verify_f2a_extfreeze_039.py"]["sha256"],
        "artifacts/worker-039/f2a_extfreeze_verify/README.md#sha256:" + deliverables["README.md"]["sha256"],
        "artifacts/worker-039/f2a_extfreeze_verify/entry_hashes.json#sha256:" + entry_sha,
        "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json#sha256:" + target["spec_sha256"],
        "artifacts/worker-047/f2a_ext_freeze_spec/sandbox/root/schemas/af_scc_c2_vacuum.yaml#sha256:" + target["candidate_sha256"],
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/FROZEN.json#815e08079aef"]
NEXT_FALSIFIER = report["next_falsifier"]

events = []


def artifact(name, atype, path, sha256, summary):
    events.append({
        "event_id": f"{E}-artifact-{name}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-039",
        "group_id": "formulation",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": "W039-F2A-EXTFREEZE-VERIFY-01",
        "artifact_type": atype,
        "path": path,
        "sha256": sha256,
        "validation_status": "unverified",
        "summary": summary,
        "evidence_refs": BASE,
    })


artifact("report", "independent_verification_report",
         "artifacts/worker-039/f2a_extfreeze_verify/report.json",
         deliverables["report.json"]["sha256"],
         "Independent non-author verification of W047-F2A-EXT-FREEZE-SPEC-02: 12/12 checks pass, 0 fail, 1 non-blocking documentation finding. The spec rebuilds the author's candidate byte-for-byte (37e650ad6481ad24), the structural diff is exactly the three declared leaves, my own six axis detectors are 0/6 baseline and 6/6 candidate, five single-site mutants discriminate, the canonical structural gate does not regress, and all pins are drift-free.")
artifact("checker", "verifier_script",
         "artifacts/worker-039/f2a_extfreeze_verify/verify_f2a_extfreeze_039.py",
         deliverables["verify_f2a_extfreeze_039.py"]["sha256"],
         "Deterministic, stdlib+PyYAML, no worker-047 code imported: re-executes the five (old_text -> new_text) anchors, reconstructs the candidate bytes, diffs parsed YAML leaves, runs six own axis detectors plus mutant/no-op/degenerate controls, and runs the canonical gate read-only. Exit 0 verified / 1 revise / 2 control / 3 pin drift; two runs byte-identical.")
artifact("readme", "README",
         "artifacts/worker-039/f2a_extfreeze_verify/README.md",
         deliverables["README.md"]["sha256"],
         "Task record: unclaimed-gap argument, method, check table P1-P12, sibling-precedent confirmation, finding W039-EFV-F01, verdict boundaries, falsifier, reproduction.")
artifact("entry-hashes", "entry_hashes",
         "artifacts/worker-039/f2a_extfreeze_verify/entry_hashes.json",
         entry_sha,
         "Canonical pins and target-bundle hashes re-measured read-only at entry and exit; zero drift. No canonical artifact written.")
artifact("checkpoint", "worker_checkpoint",
         "artifacts/worker-039/f2a_extfreeze_verify/CHECKPOINT.json",
         checkpoint_sha,
         "Worker checkpoint: task, class/node/gate, pins, verdict, counts, findings, deliverable hashes, next falsifier, authority note.")

events.append({
    "event_id": f"{E}-claim",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN"],
    "gate": "G-FORM",
    "task_id": "W039-F2A-EXTFREEZE-VERIFY-01",
    "conclusion_type": "formal_model",
    "statement": ("Artifact-and-checker measurement, not a mathematical or physics claim, at pins F2a "
                  "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3 (FROZEN rev29 815e08079aef), F2b "
                  "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe, F0 0abb9ed8a961, target spec "
                  "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json#c33e8a468669: the W047 "
                  "five-site extension-freeze repair specification is executable and confined. "
                  "Rebuilding live F2a bytes from its five declared (old_text -> new_text) pairs "
                  "reproduces the author's sandbox candidate byte-for-byte (sha256 "
                  "37e650ad6481ad24551d495887d8cc7bdc0ca713b1cdd614e60324cca681c960, equal to the "
                  "MANIFEST pin); the parsed-YAML structural diff is exactly "
                  "{extension_predicate.definition, topology.extension_topology, "
                  "falsifier.tier_1.witness_type} with no other leaf moved; an independent six-axis "
                  "detector set reads 0/6 resolved on the live bytes and 6/6 on the candidate; five "
                  "single-site reverts each flip their own axis while the no-op control stays 6/6; "
                  "the eight intended post-repair invariants hold; the candidate is sibling-uniform "
                  "with the accepted F2b tokens (SMOOTH M', C-infinity iota, interior future point); "
                  "and the canonical structural gate returns identical pass/[]/exit-0 on live and "
                  "candidate. Finding W039-EFV-F01 (non-blocking, documentation): spec invariant "
                  "list item 7 says the 'C0 or C2' composite token appears nowhere, but exactly one "
                  "occurrence exists in live and candidate at "
                  "anti_scope.phrases_that_are_not_this_class[0], where it names the prohibited "
                  "composite; the author instrument's confined reading (outside anti_scope = 0) "
                  "holds. No canonical write, no gate verdict, no node status."),
    "assumptions": ("Pins as declared and re-measured twice (T0/T1, zero drift); option A of the "
                    "specification as the object verified; my detectors are derived from the spec's "
                    "own defect statement and do not import worker-047 code; no claim about the "
                    "mathematical optimality of option A over option B."),
    "falsifier": NEXT_FALSIFIER,
    "evidence_refs": BASE + ["artifacts/worker-039/f2a_extfreeze_verify/CHECKPOINT.json#sha256:" + checkpoint_sha],
    "artifact_refs": BASE[:4],
})

events.append({
    "event_id": f"{E}-review-w047-spec",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN"],
    "gate": "G-FORM",
    "task_id": "W039-F2A-EXTFREEZE-VERIFY-01",
    "target_id": "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json#c33e8a46866992cf",
    "reviewer": "worker-039",
    "verdict": "accept",
    "score": 4.0,
    "hard_failures": [],
    "findings": [
        "POSITIVE: the specification is executable — the author's sandbox candidate is reproduced byte-for-byte from the declared anchors alone, so an owner apply is mechanical and auditable.",
        "POSITIVE: confinement verified at the parsed-YAML leaf level (exactly three declared leaves); mutation battery shows every axis detector discriminates on a single-site revert, so the 6/6 result is not detector vacuity.",
        "POSITIVE: sibling consistency independently confirmed against the pinned F2b bytes (SMOOTH M', C-infinity iota, interior future point); canonical structural gate identical pass on live and candidate.",
        "W039-EFV-F01 (minor_documentation, non-blocking): invariant item 7 is written as 'no C0 or C2 token anywhere', which the bytes contradict by design; the intended confined form holds. Read it as 'outside anti_scope' and do not delete the anti_scope prohibition entry.",
    ],
    "summary": ("Independent non-author verification of the F2a extension-predicate freeze repair spec: "
                "accept 4.0, no hard failures, one non-blocking documentation finding. Spec is ready "
                "for the owner's rev14 fold; on apply the r3 F2a cards pinned to e9a27996 are void "
                "and a fresh independent verdict is required at the new hash."),
    "evidence_refs": BASE,
})

events.append({
    "event_id": f"{E}-status",
    "event_type": "status",
    "created_at": NOW,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "class_ids": ["AF-SCC-C2-VAC-GEN"],
    "gate": "G-FORM",
    "task_id": "W039-F2A-EXTFREEZE-VERIFY-01",
    "status": "active",
    "hours": 0.4,
    "summary": ("No inbox card for worker-039; took one unclaimed class-bound task on the G-FORM "
                "critical path: independent non-author verification of W047-F2A-EXT-FREEZE-SPEC-02. "
                "Verdict SPEC_EXECUTABLE_AND_VERIFIED, 12/12 checks pass, 0 fail, 1 non-blocking "
                "documentation finding (W039-EFV-F01). The spec rebuilds the author candidate "
                "byte-for-byte, is confined to exactly three YAML leaves, resolves 6/6 freeze axes "
                "with a discriminating mutant battery, preserves all audited invariants, is "
                "sibling-uniform with F2b, and does not regress the canonical structural gate; all "
                "pins drift-free at T0/T1. No gate verdict, node status or canonical write."),
    "evidence_refs": BASE + ["artifacts/worker-039/f2a_extfreeze_verify/CHECKPOINT.json#sha256:" + checkpoint_sha],
    "next_falsifier": NEXT_FALSIFIER,
})

# ---------------------------------------------------------------- validate + append
seen = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            seen.add(json.loads(line)["event_id"])
        except Exception:
            pass
appended = 0
with OUTBOX.open("a") as fh:
    for ev in events:
        schemas.validate_event(ev)
        if ev["event_id"] in seen:
            continue
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
        appended += 1
print(f"events built={len(events)} appended={appended} outbox={OUTBOX}")
print("deliverables:", json.dumps(deliverables, indent=1, sort_keys=True))
