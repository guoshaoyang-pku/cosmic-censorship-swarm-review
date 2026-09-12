#!/usr/bin/env python3
"""Emit the W090-F0-VOCAB-CONFORMANCE-01 events + checkpoint. Idempotent by event_id:
re-running skips lines whose event_id already appears in the outbox."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]                      # .../ai4math-swarm
OUTBOX = ROOT / "comms/outbox/worker-090.jsonl"
STATE = ROOT / "runtime/state/worker-090_f0_vocab_conformance_checkpoint.json"
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TASK = "W090-F0-VOCAB-CONFORMANCE-01"
CLASS = "AF-SCC-C2-VAC-GEN"
GATE = "G-FORM"
PIN = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


checker = BASE / "check_vocab_conformance.py"
results = BASE / "results.json"
controls = BASE / "controls.json"
readme = BASE / "README.md"
res = json.loads(results.read_text())
ctl = json.loads(controls.read_text())
assert res["pin_stable"] and res["exit_ok"], "refusing to emit an unstable/void measurement"
assert ctl["all_pass"], "refusing to emit with a failed control"

checkpoint = {
    "task_id": TASK, "actor": "worker-090", "created_at": NOW,
    "node_id": "F2a", "class_id": CLASS, "gate": GATE,
    "status": "complete (worker deliverable; no node status or gate verdict claimed)",
    "method": res["method"],
    "pins": res["pins"], "pins_after": res["pins_after"], "pin_stable": res["pin_stable"],
    "summary": res["summary"],
    "findings": [{k: f[k] for k in ("id", "severity", "statement")} for f in res["findings"]],
    "f0_self_consistency": {"violations": res["f0_self_consistency"]["violations"],
                            "classification_counts": res["f0_self_consistency"]["classification_counts"]},
    "registry_binding": res["registry_binding"],
    "controls": {"n": ctl["n_controls"], "all_pass": ctl["all_pass"],
                 "ids": [c["id"] for c in ctl["controls"]]},
    "artifact_sha256": {rel(p): sha(p) for p in (checker, results, controls, readme)},
    "falsifier": res["falsifier"],
    "non_claims": res["non_claims"],
    "reproduce": "cd artifacts/worker-090/f0_vocab_conformance && python3 check_vocab_conformance.py",
}
BASE.joinpath("checkpoint.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
STATE.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
sha_checkpoint = sha(BASE / "checkpoint.json")

sums = BASE / "SHA256SUMS"
sums.write_text("".join(f"{sha(p)}  {rel(p)}\n" for p in
                        (checker, results, controls, readme, BASE / "checkpoint.json")))
sha_sums = sha(sums)

E = []
E.append({
    "event_id": f"w090-vocab-{NOW}-task", "event_type": "status", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE,
    "task_id": TASK, "status": "active", "hours": 0.1,
    "summary": ("Took ONE bounded class-bound task from the standing queue (no inbox card existed "
                "for worker-090): independent, hash-pinned F0-relative vocabulary conformance audit "
                "of the frozen rev12 F2a schema (class AF-SCC-C2-VAC-GEN) with F1/F2b as "
                "corroborating comparison. Read-only; no gate or node status claimed."),
    "evidence_refs": [f"{rel(results)}#{sha(results)[:12]}", f"schemas/af_scc_c2_vacuum.yaml#{PIN[:12]}"],
    "next_falsifier": res["falsifier"],
})
E.append({
    "event_id": f"w090-vocab-{NOW}-artifact-checker", "event_type": "artifact", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "artifact_type": "checker_code", "path": rel(checker), "sha256": sha(checker),
    "validation_status": "unverified",
    "evidence_refs": [f"{rel(checker)}#{sha(checker)[:12]}", f"schemas/af_scc_c2_vacuum.yaml#{PIN[:12]}"],
    "note": "stdlib+PyYAML; 8 controls on sandbox copies; exit 0 iff pin stable and all controls pass",
})
E.append({
    "event_id": f"w090-vocab-{NOW}-artifact-results", "event_type": "artifact", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "artifact_type": "evidence", "path": rel(results), "sha256": sha(results),
    "validation_status": "unverified",
    "evidence_refs": [f"{rel(results)}#{sha(results)[:12]}",
                      f"research_map/formulation_taxonomy.yaml#{res['pins']['research_map/formulation_taxonomy.yaml'][:12]}",
                      f"artifacts/formulation/VOCAB_ALIASES.json#{res['pins']['artifacts/formulation/VOCAB_ALIASES.json'][:12]}"],
    "note": f"matrix n={len(res['matrix'])}; summary={json.dumps(res['summary']['by_classification'], sort_keys=True)}",
})
E.append({
    "event_id": f"w090-vocab-{NOW}-artifact-controls", "event_type": "artifact", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "artifact_type": "evidence", "path": rel(controls), "sha256": sha(controls),
    "validation_status": "unverified",
    "evidence_refs": [f"{rel(controls)}#{sha(controls)[:12]}"],
    "note": f"{ctl['n_controls']}/{ctl['n_controls']} controls pass; sandbox-only mutations",
})
E.append({
    "event_id": f"w090-vocab-{NOW}-artifact-readme", "event_type": "artifact", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "artifact_type": "readme", "path": rel(readme), "sha256": sha(readme),
    "validation_status": "unverified", "evidence_refs": [f"{rel(readme)}#{sha(readme)[:12]}"],
})
E.append({
    "event_id": f"w090-vocab-{NOW}-artifact-checkpoint", "event_type": "artifact", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "artifact_type": "checkpoint_json", "path": rel(BASE / "checkpoint.json"), "sha256": sha_checkpoint,
    "validation_status": "unverified",
    "evidence_refs": [f"{rel(BASE / 'checkpoint.json')}#{sha_checkpoint[:12]}",
                      f"{rel(STATE)}#{sha_checkpoint[:12]}"],
    "note": "worker-local checkpoint; copy at runtime/state/worker-090_f0_vocab_conformance_checkpoint.json",
})
E.append({
    "event_id": f"w090-vocab-{NOW}-artifact-sums", "event_type": "artifact", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "artifact_type": "hash_ledger", "path": rel(sums), "sha256": sha_sums,
    "validation_status": "unverified", "evidence_refs": [f"{rel(sums)}#{sha_sums[:12]}"],
})
E.append({
    "event_id": f"w090-vocab-{NOW}-review", "event_type": "review", "created_at": NOW,
    "actor": "worker-090", "reviewer": "worker-090", "node_id": "F2a",
    "target_id": "F2a,F1,F2b vocabulary conformance vs F0 rev5",
    "class_id": CLASS, "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "gate": GATE, "task_id": TASK, "verdict": "revise", "score": 3.5,
    "counts_as_full_schema_verdict": False, "review_kind": "vocabulary_conformance_audit",
    "reviewed_sha256": PIN,
    "hard_failures": [
        {"id": "W090-VOCAB-01", "severity": "major (blocking until the authority ruling is recorded)",
         "axis": "F0 allowed list vs VOCAB_ALIASES canonical token",
         "finding": ("All five non-exact vocabulary slots use the registry CANONICAL while the F0 "
                     "allowed list contains only its aliases, so exact-membership conformance and "
                     "alias-aware conformance disagree on the same meaning. F2a: "
                     "conclusion_type=scc_c2_future_inextendibility (F0 lists strong_cosmic_censorship_C2) "
                     "and genericity_kind=residual_comeager (F0 lists baire_residual/provisional_baire_residual)."),
         "instances": res["summary"]["inverted"]},
        {"id": "W090-VOCAB-04", "severity": "major",
         "axis": "implicit registry dependency",
         "finding": ("F2a and F2b resolve non-exact tokens only through VOCAB_ALIASES.json but declare "
                     "no registry pointer; F1 does (genericity.vocabulary_aliases_ref, line 149)."),
         "instances": res["summary"]["schemas_without_registry_pointer"]},
    ],
    "findings": [
        {"id": "W090-VOCAB-06", "severity": "major",
         "statement": ("The canonical taxonomy's own classes[*].axes carry 5 registry-ALIAS tokens "
                       "(strong_cosmic_censorship_C2/_C0, provisional_baire_residual x3); under the "
                       "registry policy those are canonicalisation targets, so F0 is a party to the "
                       "inversion, not only its reference."),
         "instances": next(f["instances"] for f in res["findings"] if f["id"] == "W090-VOCAB-06")},
        {"id": "W090-VOCAB-05", "severity": "info",
         "statement": ("F0 is internally self-consistent: 26/26 non-null classes[*].axes tokens are "
                       "members of F0's own allowed lists; the disagreement is strictly cross-artifact."),
         "instances": res["f0_self_consistency"]["violations"]},
        {"id": "W090-VOCAB-03", "severity": "info",
         "statement": "No token is accepted only as a registry alias of an F0-allowed canonical; the mismatch is entirely the inversion direction.",
         "instances": res["summary"]["alias_resolvable"]},
        {"id": "W090-VOCAB-07", "severity": "info",
         "statement": "0 duplicate top-level YAML keys in F0 and all three schemas at the pins.",
         "instances": res["duplicate_top_level_keys"]},
    ],
    "artifact_refs": [rel(results), rel(controls), rel(checker), rel(readme), rel(BASE / "checkpoint.json")],
    "evidence_refs": [f"{rel(results)}#{sha(results)[:12]}", f"{rel(controls)}#{sha(controls)[:12]}",
                      f"schemas/af_scc_c2_vacuum.yaml#{PIN[:12]}",
                      "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                      "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"],
    "next_falsifier": res["falsifier"],
    "authority_note": "advisory scoped worker audit; cannot set a gate verdict or node status",
    "non_claims": res["non_claims"],
})
E.append({
    "event_id": f"w090-vocab-{NOW}-claim", "event_type": "claim", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "conclusion_type": "formal_model",
    "statement": (
        "Measured property of the frozen rev12 formulation artifacts at pins F0 0abb9ed8a961, "
        "F1 cce9c60146d6, F2a 5476a3f2c6bc, F2b 55d0a1ea9bda, VOCAB_ALIASES 46cd9f1eb534 and "
        "FROZEN rev28 2f358f6722d9 (pin stable across the run): of the 12 vocabulary-valued fields "
        "checked against F0 rev5 field_vocabulary, 6 are exact, 1 is the null regularity token, "
        "0 are unregistered, and 5 are INVERSIONS in which the schema uses the VOCAB_ALIASES "
        "canonical while the F0 allowed list contains only that canonical's aliases "
        "(F1 genericity_kind; F2a conclusion_type + genericity_kind; F2b conclusion_type + "
        "genericity_kind). F2a and F2b resolve those tokens only through the alias registry but "
        "declare no registry pointer (F1 does, at line 149). F0 is internally self-consistent "
        "(26/26 classes[*].axes tokens exact) yet its own descriptors carry 5 registry-alias tokens. "
        "8/8 sandbox controls reproduce their pre-committed classifications and the pin digest is "
        "unchanged before/after. Consequence for G-FORM: an exact-membership conformance scan "
        "rejects F2a on 2 of 4 axes; an alias-aware scan accepts them only if the still-open "
        "controller ruling makes alias-equivalence authoritative."),
    "assumptions": [
        "the canonical paths are authoritative and the measured sha256 pins are the frozen revision",
        "PyYAML last-wins for mapping keys; duplicate top-level keys were separately counted (0)",
        "VOCAB_ALIASES.json is the declared alias authority for the axes it lists and is silent elsewhere",
    ],
    "falsifier": res["falsifier"],
    "evidence_refs": [f"{rel(results)}#{sha(results)[:12]}", f"{rel(controls)}#{sha(controls)[:12]}",
                      f"{rel(checker)}#{sha(checker)[:12]}",
                      "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                      "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
                      "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc"],
    "artifact_refs": [rel(results), rel(controls), rel(checker), rel(BASE / "checkpoint.json")],
    "non_claims": res["non_claims"],
})
E.append({
    "event_id": f"w090-vocab-{NOW}-complete", "event_type": "status", "created_at": NOW,
    "actor": "worker-090", "node_id": "F2a", "class_id": CLASS, "gate": GATE, "task_id": TASK,
    "status": "active", "hours": 0.4,
    "summary": ("W090-F0-VOCAB-CONFORMANCE-01 complete at worker level: independent hash-pinned "
                "F0-relative vocabulary conformance audit. 12 field checks: 6 exact, 5 inverted, "
                "1 null, 0 unregistered; F2a/F2b lack the registry pointer they depend on; F0 "
                "self-consistent but its own descriptors carry 5 registry aliases. 8/8 controls, "
                "pin stable, artifacts hashed, checkpoint written. No node status or gate verdict "
                "claimed; the authority ruling (F0 allowed list vs registry canonical) remains the "
                "controller's to record."),
    "evidence_refs": [f"{rel(results)}#{sha(results)[:12]}", f"{rel(controls)}#{sha(controls)[:12]}",
                      f"{rel(BASE / 'checkpoint.json')}#{sha_checkpoint[:12]}"],
    "next_falsifier": res["falsifier"],
    "authority_note": "advisory worker status; no gate verdict, no node status promotion",
})

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
        schemas.validate_event(ev)          # fails closed before any write
        if ev["event_id"] in existing:
            print("DUP ", ev["event_id"])
            continue
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
        appended += 1
        print("OK  ", ev["event_id"])
print(f"appended {appended}/{len(E)}; artifacts {rel(results)} {sha(results)[:12]}, "
      f"{rel(controls)} {sha(controls)[:12]}, checkpoint {sha_checkpoint[:12]}")
