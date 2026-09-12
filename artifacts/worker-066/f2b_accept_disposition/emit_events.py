#!/usr/bin/env python3
"""Emit the W066-F2B-ACCEPT-DISPOSITION-01 lifecycle: checkpoint + outbox events.

Events are validated with research_map/schemas.validate_event BEFORE they are written, because
the ingest layer rejects invalid claims (observed rejection reason: 'claim: invalid
conclusion_type').  Idempotent: an event_id already present in the outbox is not re-appended.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
CHECKPOINT_ID = f"w066-f2b-accept-disposition-{STAMP}"
TASK = "W066-F2B-ACCEPT-DISPOSITION-01"
F2B = "schemas/af_scc_c0_vacuum.yaml"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with (ROOT / rel).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


report = json.loads((OUT / "report.json").read_text())
ARTIFACTS = [
    "artifacts/worker-066/f2b_accept_disposition/audit.py",
    "artifacts/worker-066/f2b_accept_disposition/pin.py",
    "artifacts/worker-066/f2b_accept_disposition/README.md",
    "artifacts/worker-066/f2b_accept_disposition/report.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/accepts.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/carriers.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/checks.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/controls.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/pins.json",
    "artifacts/worker-066/f2b_accept_disposition/evidence/pinned_inputs.json",
]
hashes = {a: sha(a) for a in ARTIFACTS if (ROOT / a).is_file()}

checkpoint = {
    "checkpoint_id": CHECKPOINT_ID,
    "task_id": TASK,
    "actor": "worker-066",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "created_at": NOW,
    "target": report["target"],
    "question": report["question"],
    "verdict": report["verdict"],
    "score": report["score"],
    "clean_accept_count": report["clean_accept_count"],
    "accept_count": len(report["accepts"]),
    "accept_classification": {a["file"]: a["classification"] for a in report["accepts"]},
    "carrier_support_counts": {k: len({s["source"] for s in v})
                               for k, v in report["carrier_support"].items()},
    "checks": report["checks"],
    "controls": {"n": len(report["controls"]),
                 "matched": sum(c["matched"] for c in report["controls"])},
    "artifacts": hashes,
    "pins_entry": report["pins_entry"],
    "pins_exit": report["pins_exit"],
    "next_falsifier": report["falsifier"],
    "notes": [
        "worker authority only; no canonical write, no gate transition, no node status",
        "accept classification is record-scoped; metadata/root co-occurrence is not a disposition",
        "review files are pinned under pinned/ because review bytes are known to move",
    ],
}

(OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, sort_keys=True))
run_state = ROOT / "runtime" / "state" / "w066_f2b_accept_disposition_checkpoint.json"
run_state.parent.mkdir(parents=True, exist_ok=True)
run_state.write_text(json.dumps(checkpoint, indent=1, sort_keys=True))
ck_sha = sha(rel(run_state))

E = "artifacts/worker-066/f2b_accept_disposition/evidence"
R = "artifacts/worker-066/f2b_accept_disposition/report.json"
ev = []

ev.append({
    "event_id": f"w066-f2b-acceptdisp-{STAMP}-01-claim",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "worker-066",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
    "node_id": "F2b",
    "gate": "G-FORM",
    "task_id": TASK,
    "conclusion_type": "formal_model",
    "statement": (
        "Artifact-and-checker measurement (not a gate verdict, not a mathematics claim): at pins "
        "F2b rev13 " + report["target"]["sha256"][:12] + " / FROZEN rev29 "
        + report["target"]["frozen"][:12] + ", 4 review verdicts binding those bytes carry "
        "verdict=accept (worker-090, worker-052, worker-071, worker-072), while 7 independent "
        "non-accept verdicts at the same bytes carry hard failures on two live normative "
        "carriers. Carrier C1-DENIAL is schemas/af_scc_c0_vacuum.yaml:152 "
        "regularity.must_not_conflate[0], whose sentence 'No containment with C2 or C0 is "
        "asserted here' is false of the same document (:239 chain, :241-243 entailments, :274 "
        "anti_scope); carrier C2-PREMISE is :246 "
        "implication_ledger.forbidden_transfers[0].reason, whose clause 'C2 is a strictly larger "
        "extension class' is inverted against the document's own chain (E_C2 innermost) and "
        "against the C2 sibling :237. A record-scoped classifier (22/22 pre-registered controls) "
        "finds that NONE of the 4 accepts disposes either carrier: worker-090, worker-072 and "
        "worker-071 are SILENT on both, and worker-052 AFFIRMATIVELY PASSES the must_not_conflate "
        "and implication-ledger areas without disposing the denial or the inverted premise. The "
        "clean-accept count for AF-SCC-C0-VAC-GEN at these bytes is therefore 0 under the "
        "project's own recorded standard (research_map.json:17922), independent of the verdict "
        "COUNT."
    ),
    "assumptions": [
        "a verdict binds bytes, not paths; all classifications ran against copies pinned at audit time",
        "a 'disposition' must be a verdict-level record that names the carrier (field path, cited line, or the carrier's verbatim live clause) AND states a disposition token; root/metadata co-occurrence is excluded by construction and by control K12",
        "the two carriers are the union of hard failures filed at the pinned hash by non-accept verdicts; support is 7 independent sources each (control K4 drops the most informative source and still recovers both)",
        "an accept that affirmatively passes the carrier's containing slot without disposing the carrier does not discharge it (worker-052 P1)",
        "the repair-design adjudication (candidate 84b5d3fa introduces a false H2_loc->C0 entailment; corrected variant 51c253c4 reverses it) is worker-023/080/044 established work, used here only as attributed control K14/K15",
    ],
    "falsifier": report["falsifier"],
    "evidence_refs": [
        f"{E}/accepts.json#{hashes[f'{E}/accepts.json'][:12]}",
        f"{E}/carriers.json#{hashes[f'{E}/carriers.json'][:12]}",
        f"{E}/checks.json#{hashes[f'{E}/checks.json'][:12]}",
        f"{E}/controls.json#{hashes[f'{E}/controls.json'][:12]}",
        f"{E}/pins.json#{hashes[f'{E}/pins.json'][:12]}",
        f"{E}/pinned_inputs.json#{hashes[f'{E}/pinned_inputs.json'][:12]}",
        f"{R}#{hashes[R][:12]}",
        "schemas/af_scc_c0_vacuum.yaml#" + report["target"]["sha256"][:12],
        "artifacts/formulation/FROZEN.json#" + report["target"]["frozen"][:12],
        "reviews/F2b-review-rev13-052.json#" + sha("reviews/F2b-review-rev13-052.json")[:12],
        "reviews/F2b-review-rev13-worker-071.json#" + sha("reviews/F2b-review-rev13-worker-071.json")[:12],
        "reviews/F2b-review-worker-072-rev29.json#" + sha("reviews/F2b-review-worker-072-rev29.json")[:12],
        "reviews/F2b-rev13-full-090.json#" + sha("reviews/F2b-rev13-full-090.json")[:12],
        "reviews/F2b-review-rev29-053.json#" + sha("reviews/F2b-review-rev29-053.json")[:12],
    ],
    "artifact_refs": [f"{R}#{hashes[R][:12]}", f"{OUT.name}/CHECKPOINT.json#{ck_sha}"],
})

hf = []
for a in report["accepts"]:
    und = [c for c, v in a["classification"].items() if v["classification"] != "DISPOSED"]
    hf.append({"accept": a["file"], "reviewer": a["reviewer"],
               "sha256": a["sha256"], "undisposed_carriers": und,
               "classification": {c: a["classification"][c]["classification"] for c in a["classification"]}})

ev.append({
    "event_id": f"w066-f2b-acceptdisp-{STAMP}-02-review",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-066",
    "reviewer": "worker-066",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-SCC-C0-VAC-GEN"],
    "node_id": "F2b",
    "gate": "G-FORM",
    "task_id": TASK,
    "target_id": "G-FORM:F2b:accept-coverage@" + report["target"]["sha256"][:12],
    "verdict": "revise",
    "score": 2.5,
    "counts_as_full_schema_verdict": False,
    "hard_failures": hf,
    "findings": [
        "4 F2b accepts bind " + report["target"]["sha256"][:12] + "; 0 dispose either live hard carrier. worker-090, worker-072, worker-071 are SILENT; worker-052 affirmatively passes the implication-ledger and must_not_conflate areas (P1) without disposing the inverted premise or the denial.",
        "Both carriers are live at the pinned bytes and each is independently reported by 7 non-accept verdicts; the audit is robust to dropping any single source (control K4).",
        "The project's own recorded standard (research_map.json:17922) is that an F2b accept written without a disposition is written over a known hard failure; applying it yields clean-accept count 0, so the G-FORM F2b criterion ('2 independent accepts per class at one measured hash') is not met by count alone at these bytes.",
        "This does not dispute worker-048's count (its 2 full accepts are verdict-counted, not disposition-checked); it disputes the inference from count to coverage.",
        "Recommended: controller authorises the CORRECTED containment repair staged at worker-080 (candidate_corrected.yaml 51c253c4), not candidate 84b5d3fa; then fresh blind accepts at the new revision. Alternative: a written carrier disposition per accepting reviewer, or a binding ruling that overturns the 7 blocking verdicts with reasons.",
        "22/22 pre-registered controls matched; 10/10 checks pass; no pinned byte moved during the run. Verdict binds F2b " + report["target"]["sha256"][:12] + " and FROZEN " + report["target"]["frozen"][:12] + " only and is void on any hash move.",
    ],
    "evidence_refs": [
        f"{R}#{hashes[R][:12]}",
        f"{E}/accepts.json#{hashes[f'{E}/accepts.json'][:12]}",
        f"{E}/carriers.json#{hashes[f'{E}/carriers.json'][:12]}",
        f"{E}/controls.json#{hashes[f'{E}/controls.json'][:12]}",
        "schemas/af_scc_c0_vacuum.yaml#" + report["target"]["sha256"][:12],
    ],
    "authority_note": "worker verdict on audit coverage only; no gate verdict, no node transition, "
                      "no canonical write, no schema-semantics re-decision.",
})

for kind, node_status in (("03-status-complete", "active"), ("04-status-checkpoint", "active")):
    ev.append({
        "event_id": f"w066-f2b-acceptdisp-{STAMP}-{kind}",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "status": node_status,
        "hours": 0.8 if kind.endswith("complete") else 0.85,
        "summary": (
            "W066-F2B-ACCEPT-DISPOSITION-01 complete as a bounded worker lifecycle: carrier-disposition "
            "audit of the F2b accept wave at " + report["target"]["sha256"][:12] + ". 4 accepts, "
            "0 dispose either of the 2 live normative hard carriers (3 SILENT, 1 AFFIRMATIVE_PASS_UNDISPOSED); "
            "22/22 controls, 10/10 checks, pins stable. This is a completion claim, not a node or gate transition."
            if kind.endswith("complete") else
            "Checkpoint written to runtime/state/w066_f2b_accept_disposition_checkpoint.json ("
            + CHECKPOINT_ID + "); pins re-measured unchanged after the run. worker-066 lifecycle complete; "
            "this event lands in the next ingest cycle."
        ),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#" + report["target"]["sha256"][:12],
            f"{R}#{hashes[R][:12]}",
            f"runtime/state/w066_f2b_accept_disposition_checkpoint.json#{ck_sha}",
            f"artifacts/worker-066/f2b_accept_disposition/CHECKPOINT.json#{ck_sha}",
        ],
        "next_falsifier": report["falsifier"],
    })

# validate BEFORE writing -- the ingest layer rejects invalid claims
for e in ev:
    schemas.validate_event(e)

outbox = ROOT / "comms" / "outbox" / "worker-066.jsonl"
existing = outbox.read_text() if outbox.is_file() else ""
added = [e for e in ev if e["event_id"] not in existing]
with outbox.open("a") as f:
    for e in added:
        f.write(json.dumps(e, sort_keys=True) + "\n")

print(json.dumps({
    "checkpoint": str(run_state.relative_to(ROOT)),
    "checkpoint_sha256": ck_sha[:12],
    "events_validated": len(ev),
    "events_appended": len(added),
    "event_ids": [e["event_id"] for e in ev],
}, indent=1))
