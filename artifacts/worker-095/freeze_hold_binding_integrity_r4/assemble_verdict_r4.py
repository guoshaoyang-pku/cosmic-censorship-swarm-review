#!/usr/bin/env python3
"""Assemble verdict.json + README.md + outbox events for W095-HOLD-BIND-INTEGRITY-06.

Run after run_probe_r4.py. Read-only with respect to canonical artifacts; writes only
under artifacts/worker-095/freeze_hold_binding_integrity_r4/ and appends to
comms/outbox/worker-095.jsonl (validated with research_map.schemas.validate_event).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "evidence" / "raw"
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-095.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ref(p: Path, name: str, note: str = "") -> str:
    s = sha(p)
    return f"{name}#{s[:12]}" + (f" {note}" if note else "")


report = json.loads((RAW / "probe_report_r4.json").read_text())
raw_names = [
    "probe_report_r4.json", "frozen_drift_r4.json", "manifest_self_r4.json",
    "pin_announcements_r4.json", "order_resolution_r4.json", "declared_evidence_r4.json",
    "f2b_binding_r4.json", "stream_hygiene_r4.json", "map_gate_slice_r4.json",
    "probe_drift_r4.json",
]
raw_refs = [ref(RAW / n, f"artifacts/worker-095/freeze_hold_binding_integrity_r4/evidence/raw/{n}")
            for n in raw_names]
canon_refs = [
    "artifacts/formulation/FROZEN.json#" + sha(ROOT / "artifacts/formulation/FROZEN.json")[:12],
    "schemas/af_scc_c0_vacuum.yaml#" + sha(ROOT / "schemas/af_scc_c0_vacuum.yaml")[:12],
    "schemas/af_scc_c2_vacuum.yaml#" + sha(ROOT / "schemas/af_scc_c2_vacuum.yaml")[:12],
    "schemas/af_wcc_vacuum.yaml#" + sha(ROOT / "schemas/af_wcc_vacuum.yaml")[:12],
    "research_map/formulation_taxonomy.yaml#" + sha(ROOT / "research_map/formulation_taxonomy.yaml")[:12],
    "artifacts/formulation/formulation_taxonomy.yaml#" + sha(ROOT / "artifacts/formulation/formulation_taxonomy.yaml")[:12],
    "artifacts/formulation/evidence/taxonomy_consistency.json#" + sha(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json")[:12],
]

verdict = {
    "check_status": report["checks"],
    "class_id": "AF-SCC-C0-VAC-GEN",
    "counts_as_full_schema_verdict": False,
    "evidence_refs": raw_refs + canon_refs,
    "findings": report["findings"],
    "frozen_manifest_sha256": report["frozen_manifest_sha256"],
    "frozen_revision_reviewed": report["frozen_revision"],
    "gate": "G-FORM",
    "hard_failures": report["hard_failures"],
    "next_falsifier": report["next_falsifier"],
    "node_id": "F2b",
    "probe": report["probe"],
    "probe_at": report["probe_at"],
    "probe_script": "artifacts/worker-095/freeze_hold_binding_integrity_r4/run_probe_r4.py",
    "reviewed_revision": 13,
    "reviewed_sha256": sha(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
    "score_0_5": 3,
    "verdict": "revise",
    "worker": "worker-095",
    "live_input_movement": report.get("live_input_movement", {}),
}
(HERE / "verdict.json").write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")

readme = f"""# W095-HOLD-BIND-INTEGRITY-06 -- freeze-hold / class-binding integrity re-probe (r4)

Class-bound task: node **F2b**, class **AF-SCC-C0-VAC-GEN**, gate **G-FORM**.
Successor to `freeze_hold_binding_integrity_r3/` (W095-HOLD-BIND-INTEGRITY-05), re-testing its
declared next falsifier at the live FROZEN revision after the 00:57:48 ingest of the
lead-formulation rev29 pin announcements.

- Probe time: **{report['probe_at']}**; FROZEN **rev{report['frozen_revision']}**
  (`{report['frozen_manifest_sha256'][:12]}`), F2b rev13 (`{verdict['reviewed_sha256'][:12]}`).
- Reproduce: `python3 artifacts/worker-095/freeze_hold_binding_integrity_r4/run_probe_r4.py`
- Verdict: **{verdict['verdict']}** ({verdict['score_0_5']}/5), hard failures {verdict['hard_failures']}.
  Worker review only: `counts_as_full_schema_verdict=false`, no node status or gate verdict set.

## Check table

| check | result | what it measures |
|---|---|---|
| R1 PIN-MATCH | {report['checks']['R1-PIN-MATCH']} | all FROZEN rev{report['frozen_revision']} pins vs disk bytes |
| R2 MANIFEST-SELF | {report['checks']['R2-MANIFEST-SELF']} | FROZEN.json measured vs its announcement |
| R3 ANNOUNCE | {report['checks']['R3-ANNOUNCE']} | pin announcement per held path (HF-05-01 re-test) |
| R4 ORDER-RESOLUTION | {report['checks']['R4-ORDER-RESOLUTION']} | created_at-max / file-order-last / _received_at-max vs pin |
| R5 DECLARED-EVIDENCE | {report['checks']['R5-DECLARED-EVIDENCE']} | f0_binding declared == measured, two consecutive reads |
| R6 NO-PROBE-DRIFT | {report['checks']['R6-NO-PROBE-DRIFT']} | pinned artifacts stable across the probe window |
| R7 CLASS-BINDING | {report['checks']['R7-CLASS-BINDING']} | F2b class_id + class_contract_pointer resolves in canonical F0 |
| R9 STREAM-HYGIENE | INFO | non-ingested / future-dated event cohort |

## Result in one paragraph

The byte-level freeze hold is intact (R1/R2/R6 PASS, 50/50 pins match) and the rev29
change_protocol gap reported by r3 as **HF-05-01 is repaired**: every held path and
FROZEN.json now has an artifact event in the accepted stream carrying the pin
(`lead-form-20260912T005743-00..06`, ingested 00:57:48). What remains is the ordering defect
(**HF-06-01**): resolution by agent-declared `created_at` still binds stale bytes for 2/5 held
paths -- F2b `schemas/af_scc_c0_vacuum.yaml` -> `e6b1af2bd692` (`w06-20260912T0115-f2b-rev6`)
and `research_map/formulation_taxonomy.yaml` -> `276009f4f63d`
(`leadform-artifact-0095-r4f0`) -- while file order and `_received_at` order both resolve to
the pin. The F2b shadow is also the new **HF-06-02**: it is future-dated (created_at
01:15:00, +13 min) and was never ingested (`_received_at` absent), so the r3-recommended
`_received_at` fallback has no defined value for it; the accepted stream
carries {json.loads((RAW / 'stream_hygiene_r4.json').read_text())['without_received_at']}
such non-ingested events. F2b class binding (R7) and declared-evidence resolution (R5) pass.

Do not read this as a gate verdict or a node completion.
"""
(HERE / "README.md").write_text(readme)

# ---------------- outbox events ----------------
stamp = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
created = datetime.now(CST).isoformat(timespec="seconds")
base = f"w095-hold-r4-{stamp}"
verdict_ref = ref(HERE / "verdict.json", "artifacts/worker-095/freeze_hold_binding_integrity_r4/verdict.json")
script_ref = ref(HERE / "run_probe_r4.py", "artifacts/worker-095/freeze_hold_binding_integrity_r4/run_probe_r4.py")
ev_refs = [verdict_ref, script_ref] + raw_refs

summary = (
    "W095-HOLD-BIND-INTEGRITY-06 (r4) re-probe at FROZEN rev29 815e08079aef / live F2b rev13 "
    f"{verdict['reviewed_sha256'][:12]}: verdict revise (3/5). R1/R2/R6 PASS (50/50 pins, no "
    "pinned-artifact drift), R3 ANNOUNCE PASS -- HF-05-01 (unannounced rev29 pins) is REPAIRED by "
    "lead-form-20260912T005743-00..06 ingested 00:57:48. R4 FAIL: created_at ordering still "
    "binds stale bytes for 2/5 held paths (F2b -> e6b1af2bd692; canonical F0 taxonomy -> "
    "276009f4f63d) while file order and _received_at order resolve to the pin for 5/5. "
    "HF-06-02: the F2b shadow is future-dated (01:15:00) and not ingested (_received_at absent), "
    "the exact class for which the r3 fallback rule is undefined. R5/R7 PASS. "
    "counts_as_full_schema_verdict=false; worker events cannot set node status or a gate verdict."
)
next_f = report["next_falsifier"]

events = [
    {"event_id": f"{base}-task-claim", "event_type": "status", "created_at": created,
     "actor": "worker-095", "node_id": "F2b", "status": "active", "hours": 0.3,
     "summary": "Taking ONE class-bound successor task W095-HOLD-BIND-INTEGRITY-06 (class "
                "AF-SCC-C0-VAC-GEN, gate G-FORM, node F2b): re-test the r3 next_falsifier after "
                "the 00:57:48 rev29 pin-announcement ingest. Binding/a-ordering probe only; no "
                "node completion, no gate verdict, no canonical byte edit.",
     "evidence_refs": [verdict_ref, script_ref] + raw_refs[:2],
     "next_falsifier": next_f},
    {"event_id": f"{base}-artifact-verdict", "event_type": "artifact", "created_at": created,
     "actor": "worker-095", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "artifact_type": "class_binding_integrity_verdict",
     "path": "artifacts/worker-095/freeze_hold_binding_integrity_r4/verdict.json",
     "sha256": sha(HERE / "verdict.json"), "validation_status": "unverified"},
    {"event_id": f"{base}-claim-binding", "event_type": "claim", "created_at": created,
     "actor": "worker-095", "class_id": "AF-SCC-C0-VAC-GEN",
     "statement": "At FROZEN rev29 (815e08079aef) the byte-level freeze hold is intact for all "
                  "five held paths (50/50 pins match; no pinned-artifact drift during the probe) "
                  "and the rev29 pin-announcement gap HF-05-01 is repaired by "
                  "lead-form-20260912T005743-00..06 (ingested 00:57:48); the residual defect is "
                  "ordering: agent-declared created_at resolves 'latest artifact per path' to "
                  "stale bytes for F2b (e6b1af2bd692) and canonical F0 taxonomy (276009f4f63d), "
                  "and one shadow event is future-dated and carries no _received_at.",
     "conclusion_type": "formal_model",
     "assumptions": ["FROZEN.json rev29 is the freeze authority for the five held paths",
                     "resolution over research_map/events.jsonl is the binding read path",
                     "worker review cannot set node status or gate verdicts"],
     "falsifier": next_f, "evidence_refs": ev_refs + canon_refs},
    {"event_id": f"{base}-review-binding", "event_type": "review", "created_at": created,
     "actor": "worker-095", "reviewer": "worker-095", "target_id": "F2b",
     "class_id": "AF-SCC-C0-VAC-GEN", "target_path": "schemas/af_scc_c0_vacuum.yaml",
     "artifact_sha256": verdict["reviewed_sha256"], "verdict": "revise", "score": 3,
     "frozen_revision_reviewed": report["frozen_revision"],
     "counts_as_full_schema_verdict": False,
     "summary": summary[:900],
     "hard_failures": report["hard_failures"],
     "findings": [{"id": f["id"], "severity": f["severity"], "finding": f["finding"][:400]}
                  for f in report["findings"]],
     "evidence_refs": ev_refs + canon_refs},
    {"event_id": f"{base}-blocker-order-resolution", "event_type": "blocker", "created_at": created,
     "actor": "worker-095", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
     "description": "HF-06-01/HF-06-02 at FROZEN rev29 after the pin announcements landed: the "
                    "byte hold passes but no ordering rule is declared for 'latest artifact per "
                    "path'. created_at-max binds stale bytes for 2/5 held paths (F2b "
                    "schemas/af_scc_c0_vacuum.yaml -> e6b1af2bd692 from w06-20260912T0115-f2b-rev6, "
                    "created_at 01:15:00; research_map/formulation_taxonomy.yaml -> 276009f4f63d "
                    "from leadform-artifact-0095-r4f0, created_at 00:44:00) while file-order-last "
                    "and _received_at-max both resolve to the pin for 5/5. The F2b shadow is "
                    "future-dated and not ingested (no _received_at), and the stream carries "
                    "hundreds of such non-ingested events, so the r3-recommended _received_at "
                    "fallback needs an explicit value for them. Read-path/ingest fix, not a "
                    "canonical byte edit.",
     "needed_to_unblock": "(a) declare the binding read path in the repo and make it rank by "
                          "controller order (_received_at), with an explicit rule for events "
                          "lacking _received_at and for future-dated created_at; (b) re-ingest or "
                          "mark superseded the non-ingested cohort that bypassed comms.py so every "
                          "accepted event has an arrival order; (c) re-probe from a second instance "
                          "to confirm 5/5 resolve to the FROZEN pin under the declared rule.",
     "evidence_refs": ev_refs + canon_refs},
    {"event_id": f"{base}-task-receipt-complete", "event_type": "status", "created_at": created,
     "actor": "worker-095", "node_id": "F2b", "status": "active", "hours": 0.3,
     "summary": "W095-HOLD-BIND-INTEGRITY-06 worker-level receipt complete; node status "
                "deliberately unchanged. verdict=revise (3/5) at FROZEN rev29 815e08079aef / F2b "
                "rev13 " + verdict["reviewed_sha256"][:12] + "; artifact + 10 raw evidence files "
                "+ checkpoint written; HF-05-01 repair confirmed, HF-06-01/HF-06-02 recorded. "
                "counts_as_full_schema_verdict=false.",
     "evidence_refs": ev_refs + canon_refs,
     "next_falsifier": next_f},
]

lines = []
for ev in events:
    ev["class_id"] = ev.get("class_id", "AF-SCC-C0-VAC-GEN")
    validate_event(ev)
    lines.append(json.dumps(ev, sort_keys=True))
with OUTBOX.open("a") as f:
    f.write("\n".join(lines) + "\n")
print(json.dumps({"verdict_sha256": sha(HERE / "verdict.json"), "events": len(lines),
                  "event_ids": [e["event_id"] for e in events]}, indent=2))
