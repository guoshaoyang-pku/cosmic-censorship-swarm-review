#!/usr/bin/env python3
"""Postrun drift annex for W059-SCALARSPH-AXIS-ADJ-01.

The REC-12 evidence-binding repair republished artifacts/formulation/FROZEN.json
to revision 29 while this task was running.  This annex re-measures the live
bytes and records whether the reviewed A/B artifacts moved.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
D = ROOT / "artifacts/worker-059/scalar_sph_axis_adjudication"
LIVE = {
    "canonical_F0": "research_map/formulation_taxonomy.yaml",
    "supplement_F0R": "artifacts/formulation/formulation_taxonomy.yaml",
    "VOCAB_ALIASES": "artifacts/formulation/VOCAB_ALIASES.json",
    "rule_spec": "artifacts/formulation/rule_spec.json",
    "FROZEN": "artifacts/formulation/FROZEN.json",
    "taxonomy_consistency_evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
}
DECLARED = {
    "canonical_F0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "supplement_F0R": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "VOCAB_ALIASES": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "rule_spec": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


live = {k: sha(ROOT / v) for k, v in LIVE.items()}
frozen = json.loads((ROOT / LIVE["FROZEN"]).read_text())
pins = {k: (frozen.get("logical_artifacts", {}).get(k) or {}).get("sha256")
        for k in ("F0-declared-taxonomy", "F0-class-contract-supplement")}
snp = json.loads((D / "snapshot/FROZEN.2f358f6722d9.json").read_text())
snp_pins = {k: (snp.get("logical_artifacts", {}).get(k) or {}).get("sha256")
            for k in ("F0-declared-taxonomy", "F0-class-contract-supplement")}
annex = {
    "task_id": "W059-SCALARSPH-AXIS-ADJ-01",
    "class_id": "AF-WCC-SCALAR-SPH",
    "created_at": "2026-09-12T00:57:00+08:00",
    "trigger": ("artifacts/formulation/FROZEN.json republished to revision 29 (frozen_at 2026-09-12T00:55:02+08:00) "
                "by the REC-12 evidence-binding repair during this task"),
    "reviewed_binding": {
        "note": "the verdict is bound to the A/B artifact bytes, not to the manifest revision; the rev28 snapshot is preserved locally",
        "snapshot_FROZEN_revision": snp.get("revision"),
        "snapshot_FROZEN_sha256": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
        "snapshot_pins": snp_pins,
    },
    "live_measurement": {
        "FROZEN_revision": frozen.get("revision"),
        "FROZEN_frozen_at": frozen.get("frozen_at"),
        "FROZEN_sha256": live["FROZEN"],
        "FROZEN_pins": pins,
        "canonical_F0_sha256": live["canonical_F0"],
        "supplement_F0R_sha256": live["supplement_F0R"],
        "VOCAB_ALIASES_sha256": live["VOCAB_ALIASES"],
        "rule_spec_sha256": live["rule_spec"],
        "taxonomy_consistency_evidence_sha256": live["taxonomy_consistency_evidence"],
    },
    "drift": {
        "FROZEN_manifest_changed": live["FROZEN"] != "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
        "canonical_F0_changed": live["canonical_F0"] != DECLARED["canonical_F0"],
        "supplement_F0R_changed": live["supplement_F0R"] != DECLARED["supplement_F0R"],
        "VOCAB_ALIASES_changed": live["VOCAB_ALIASES"] != DECLARED["VOCAB_ALIASES"],
        "rule_spec_changed": live["rule_spec"] != DECLARED["rule_spec"],
    },
    "verdict_survival": {
        "survives": (live["canonical_F0"] == DECLARED["canonical_F0"]
                     and live["supplement_F0R"] == DECLARED["supplement_F0R"]
                     and live["VOCAB_ALIASES"] == DECLARED["VOCAB_ALIASES"]
                     and live["rule_spec"] == DECLARED["rule_spec"]),
        "reason": ("rev29 still pins F0 at 0abb9ed8 and the supplement at d7419b4e; both the D3 scope contradiction "
                   "and the registry matrix are properties of those unchanged bytes. The verdict would be voided only "
                   "if A, B, VOCAB_ALIASES or rule_spec move; the manifest revision alone does not void it."),
        "live_FROZEN_pins_match_reviewed": (pins.get("F0-declared-taxonomy") == DECLARED["canonical_F0"]
                                            and pins.get("F0-class-contract-supplement") == DECLARED["supplement_F0R"]),
    },
}
(D / "postrun_annex.json").write_text(json.dumps(annex, indent=1) + "\n")
print(json.dumps(annex["drift"], indent=1))
print("verdict_survives:", annex["verdict_survival"]["survives"],
      "| live pins match:", annex["verdict_survival"]["live_FROZEN_pins_match_reviewed"])
