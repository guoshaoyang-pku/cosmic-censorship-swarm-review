#!/usr/bin/env python3
"""Emit W095-F2A-BIND-INTEGRITY-01 upward events to comms/outbox/worker-095.jsonl.

Every event is validated with research_map.schemas.validate_event BEFORE the file is
written, so the emission cannot introduce a reject. created_at is wall-clock at write
time (controller finding CF-14: no future-dated records).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    verdict_path = HERE / "verdict.json"
    v = json.loads(verdict_path.read_text())
    vsha = sha256_file(verdict_path)
    stamp = datetime.now(CST).replace(microsecond=0)
    ts = stamp.isoformat()
    tag = stamp.strftime("%Y%m%dT%H%M%S")
    f2a = v["reviewed_sha256"]
    f0 = v["measured_f0_canonical_sha256"]
    ev = []

    ev.append({
        "event_id": f"w095-{tag}-task-claim",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-095",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "status": "active",
        "hours": 0.3,
        "summary": (
            "No assignment card exists in comms/inbox for worker-095 (fleet 2026-09-12T00:16:57). Taking ONE bounded "
            "class-bound task, W095-F2A-BIND-INTEGRITY-01: class-binding/publication integrity of F2a "
            "AF-SCC-C2-VAC-GEN at measured canonical sha256 %s, against canonical F0 %s, the authoring F0, the FROZEN "
            "manifest and the canonical FORM-GATE-01. Deliverable: artifacts/worker-095/f2a_binding_integrity/ "
            "(verdict.json + reproducible measure_binding.py + 4 probe passes). Binding probe only; does NOT claim node "
            "completion, a gate verdict, or substitute for a content accept." % (f2a[:12], f0[:12])
        ),
        "evidence_refs": [f"schemas/af_scc_c2_vacuum.yaml#{f2a[:12]}",
                          f"research_map/formulation_taxonomy.yaml#{f0[:12]}",
                          "artifacts/worker-095/f2a_binding_integrity/measure_binding.py"],
        "next_falsifier": v["next_falsifier"],
    })

    ev.append({
        "event_id": f"w095-{tag}-artifact-verdict",
        "event_type": "artifact",
        "created_at": ts,
        "actor": "worker-095",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "artifact_type": "class_binding_integrity_verdict",
        "path": "artifacts/worker-095/f2a_binding_integrity/verdict.json",
        "sha256": vsha,
        "validation_status": "unverified",
    })

    ev.append({
        "event_id": f"w095-{tag}-review-binding",
        "event_type": "review",
        "created_at": ts,
        "actor": "worker-095",
        "target_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "reviewer": "worker-095",
        "verdict": "revise",
        "score": 3.0,
        "reviewed_sha256": f2a,
        "counts_as_full_schema_verdict": False,
        "hard_failures": [
            {"id": "F-BIND-1", "kind": "binding", "severity": "blocking",
             "detail": "F2a.class_contract_pointer resolves only in the non-authoritative authoring F0; the authoritative canonical F0 has no class_contracts key."},
            {"id": "F-BIND-2", "kind": "publication", "severity": "major",
             "detail": "canonical and authoring F0 are structurally different documents (7 shared top-level keys, 23 canonical-only, 18 authoring-only), so canonical == authoring byte-identity is unsatisfiable without discarding canonical content."},
            {"id": "F-BIND-4", "kind": "vocabulary", "severity": "major",
             "detail": "canonical F0 records the alias token strong_cosmic_censorship_C2 while the F2a schema and FORM-GATE-01 require scc_c2_future_inextendibility; VOCAB_ALIASES forbids aliases in a new canonical artifact, so the recorded pointer remedy binds F2a to a policy-violating token (corroborates W082-F-04 / F0-F1-review-17)."},
            {"id": "F-PROV-1", "kind": "provenance", "severity": "major",
             "detail": "7 duplicate revised_at YAML keys in F2a; last-wins drops the revision history on load."},
        ],
        "findings": v["findings"],
        "scope_note": v["scope_note"],
        "evidence_refs": v["evidence_refs"],
    })

    ev.append({
        "event_id": f"w095-{tag}-blocker-binding",
        "event_type": "blocker",
        "created_at": ts,
        "actor": "worker-095",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "description": (
            "G-FORM class-binding blocker re-measured at F2a %s / canonical F0 %s: (1) class_contract_pointer targets "
            "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.<class_id>, which resolves only in the "
            "authoring tree; canonical F0 stores class content under classes.<class_id> and has no class_contracts key. "
            "(2) The recorded unblock 'repoint the pointer at canonical classes.<class_id>' is not sufficient: canonical "
            "classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type = 'strong_cosmic_censorship_C2' whereas the schema and the "
            "frozen gate require 'scc_c2_future_inextendibility' (F2b has the analogous C0 mismatch), and editing "
            "canonical F0 changes its hash and re-triggers the schemas' f0_binding refresh." % (f2a[:12], f0[:12])
        ),
        "needed_to_unblock": (
            "One controller/lead decision on the class contract of record plus a coordinated revision: either add "
            "class_contracts.<class_id> to canonical F0 with the gate vocabulary, or repoint class_contract_pointer at "
            "canonical classes.<class_id> AND reconcile the SCC conclusion_type tokens (strong_cosmic_censorship_C2/C0 -> "
            "scc_c2_future_inextendibility / scc_c0_future_inextendibility); then re-run check_taxonomy_consistency.py with "
            "measured sha256s of both trees and re-freeze F0 and the three schemas in one revision."
        ),
        "evidence_refs": [
            f"schemas/af_scc_c2_vacuum.yaml#{f2a[:12]}",
            f"research_map/formulation_taxonomy.yaml#{f0[:12]} classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type",
            "artifacts/flash-13/form_gate/check_class_schema.py FROZEN_CLASSES",
            "artifacts/worker-095/f2a_binding_integrity/verdict.json#" + vsha[:12],
        ],
    })

    ev.append({
        "event_id": f"w095-{tag}-task-complete",
        "event_type": "status",
        "created_at": ts,
        "actor": "worker-095",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "status": "done",
        "hours": 0.5,
        "summary": (
            "W095 task complete at worker level (node status deliberately unchanged; worker events cannot set F2a done). "
            "Verdict revise on binding/publication integrity at F2a %s: 4 findings (F-BIND-1 blocking, F-BIND-2/F-BIND-4/"
            "F-PROV-1 major), FROZEN rev25 pins 8/8 paths, gate 16/16 on all three schemas, class-separation clean, F2a "
            "content byte-stable across the three observed revisions. counts_as_full_schema_verdict=false."
            % f2a[:12]
        ),
        "evidence_refs": ["artifacts/worker-095/f2a_binding_integrity/verdict.json#" + vsha[:12],
                          f"schemas/af_scc_c2_vacuum.yaml#{f2a[:12]}"],
        "next_falsifier": v["next_falsifier"],
    })

    for e in ev:
        validate_event(e)  # fail closed before writing anything

    out = ROOT / "comms" / "outbox" / "worker-095.jsonl"
    with open(out, "a") as f:
        for e in ev:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print("wrote", len(ev), "validated events ->", out)
    for e in ev:
        print("  ", e["event_type"], e["event_id"])
    print("verdict.json sha256:", vsha)
    print("outbox sha256:", sha256_file(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
