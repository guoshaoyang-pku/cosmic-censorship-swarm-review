#!/usr/bin/env python3
"""W038-F0-CONFORMANCE-02 emitter: outbox events + checkpoint for the rev28 recheck.

Writes:
  comms/outbox/worker-038.jsonl                      (append 4 events)
  runtime/state/w038_checkpoint_4.json               (checkpoint)
Re-validates event shape against research_map/events.schema.json before appending,
and re-measures the frozen pins so the checkpoint records any move during emission.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D = "artifacts/worker-038/f0_conformance"
NOW = datetime.now().astimezone().isoformat(timespec="seconds")
TAG = NOW.replace("-", "").replace(":", "").split("+")[0]


def sha256(p: str) -> str:
    h = hashlib.sha256()
    with (ROOT / p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(p: str) -> str:
    return f"{p}#{sha256(p)}"


ARTIFACTS = [
    f"{D}/rev28_verdict.json",
    f"{D}/REPORT_rev28_recheck.md",
    f"{D}/independent_checks_rev28.json",
    f"{D}/freeze_integrity_rev28.json",
    f"{D}/worker01_validation_rev28.json",
    f"{D}/run_manifest_rev28.txt",
    f"{D}/snapshots/rev28/FROZEN.snapshot.json",
    f"{D}/freeze_integrity_check.py",
    "reviews/F0-conformance-038-rev28.json",
]
H = {p: sha256(p) for p in ARTIFACTS}

F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
RUBRIC = "evaluation_rubric.yaml"
CHECKER = "artifacts/worker-01/validate_taxonomy.py"

STRONG = (
    f"{F0}#{H[F0] if F0 in H else sha256(F0)}"
)
EV = [
    {
        "event_id": f"w038-02-artifact-verdict-{TAG}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-038",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact_type": "f0_conformance_verdict_rev28",
        "path": f"{D}/rev28_verdict.json",
        "sha256": H[f"{D}/rev28_verdict.json"],
        "validation_status": "unverified",
        "summary": "W038-F0-CONFORMANCE-02 machine verdict: accept at canonical F0 0abb9ed8 under FROZEN rev28 2f358f6722d9; declared 253/0 pass, independent 11 PASS/0 FAIL/2 NOTE, freeze integrity 44/44 pins match.",
        "falsifier": "a substantiated FAIL in any of the three check suites, or a FROZEN rev28 pin whose bytes differ from the pin, flips this to revise; the verdict is void if either frozen hash moves.",
        "evidence_refs": [ref(p) for p in [
            f"{D}/independent_checks_rev28.json", f"{D}/freeze_integrity_rev28.json",
            f"{D}/worker01_validation_rev28.json", f"{D}/run_manifest_rev28.txt",
            FROZEN, F0, SUPP]],
    },
    {
        "event_id": f"w038-02-artifact-review-{TAG}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-038",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact_type": "review",
        "path": "reviews/F0-conformance-038-rev28.json",
        "sha256": H["reviews/F0-conformance-038-rev28.json"],
        "validation_status": "unverified",
        "summary": "Independent non-author F0 conformance review at FROZEN rev28: verdict accept, score 3.5, 0 hard failures, two non-blocking findings (genericity_kind vs comeager conclusion confirmed; pre-rev28 freeze drift recorded).",
        "falsifier": "any substantiated FAIL against the machine-checkable G-F0 criteria at the pinned hash flips the verdict to revise.",
        "evidence_refs": [ref(p) for p in [
            f"{D}/rev28_verdict.json", f"{D}/independent_checks_rev28.json",
            f"{D}/freeze_integrity_rev28.json", F0, SUPP, FROZEN, RUBRIC, CHECKER]],
    },
    {
        "event_id": f"w038-02-review-f0-accept-{TAG}",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-038",
        "target_id": "F0",
        "reviewer": "worker-038",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                      "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "verdict": "accept",
        "score": 3.5,
        "hard_failures": [],
        "findings": ("accept at canonical research_map/formulation_taxonomy.yaml#0abb9ed8a961 "
                     "under FROZEN.json rev28 2f358f6722d9. Non-blocking W038-02-F1: "
                     "AF-WCC-SCALAR-SPH axes.genericity_kind='unresolved' and H4 says the genericity "
                     "notion is unresolved, while the rev5 conclusion quantifies over a comeager set; "
                     "no checker compares that field (independently confirms astra-lead-audit O-GF0-1). "
                     "Non-blocking W038-02-F2: FROZEN rev27 5fa3b3bf mismatched five listed files at "
                     "00:35:06; rev28 matches all 44 with 0 post-freeze modifications. B-GF0-1 partially "
                     "addressed (one non-author verdict at the frozen hash, but not blind, so worker-038 "
                     "counts once); B-GF0-2 remains controller adjudication."),
        "reviewed_sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "frozen_manifest_sha256": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
        "counts_as_full_schema_verdict": True,
        "blind_to_artifact_lineage": False,
        "review_path": "reviews/F0-conformance-038-rev28.json",
        "evidence_refs": [ref(p) for p in [
            f"{D}/rev28_verdict.json", "reviews/F0-conformance-038-rev28.json",
            f"{D}/independent_checks_rev28.json", f"{D}/freeze_integrity_rev28.json",
            F0, SUPP, FROZEN]],
    },
    {
        "event_id": f"w038-02-status-f0-{TAG}",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-038",
        "node_id": "F0",
        "status": "active",
        "hours": 0.5,
        "summary": ("F0 recheck complete at FROZEN rev28. Prior blocker F0-FREEZE-DRIFT is resolved at the "
                    "manifest level: rev28 pins canonical 0abb9ed8 and supplement d7419b4e and all 44 file "
                    "pins match disk. W038-F0-CONFORMANCE-02 issues accept (3.5) at 0abb9ed8; this is one "
                    "non-author verdict for B-GF0-1 but not blind, so a second distinct reviewer is still "
                    "required. B-GF0-2 (canonical vs authoring adjudication) is unchanged and controller-side. "
                    "New non-blocking finding W038-02-F1 confirms O-GF0-1: genericity_kind is unresolved while "
                    "the scalar-class conclusion says comeager; no checker covers that field. No gate verdict, "
                    "no completion claim."),
        "next_falsifier": ("a reader who shows a G-F0 criterion misread by the independent or freeze-integrity "
                           "checker, a FROZEN rev28 pin whose bytes differ, or a non-frozen class in the "
                           "taxonomy, refutes the accept; the verdict is void if either frozen hash moves."),
        "evidence_refs": [ref(p) for p in [
            f"{D}/rev28_verdict.json", "reviews/F0-conformance-038-rev28.json",
            f"{D}/freeze_integrity_rev28.json", f"{D}/independent_checks_rev28.json",
            FROZEN, F0]],
    },
]

# Validate against research_map/schemas.py (authoritative for ingest). The
# JSON-schema file is incomplete (it omits status/blocker), so it is applied only
# to the event types it actually defines.
import sys
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402
try:
    import jsonschema
    json_schema = json.loads((ROOT / "research_map/events.schema.json").read_text())
    JSON_SCHEMA_TYPES = {"direction_update", "claim", "artifact", "review", "resource_request"}
    HAVE_JS = True
except Exception:
    json_schema, HAVE_JS = None, False

base_ok = ["event_id", "event_type", "created_at", "actor"]
for e in EV:
    missing = [k for k in base_ok if k not in e]
    assert not missing, (e["event_id"], missing)
    validate_event(e)
    if HAVE_JS and e["event_type"] in JSON_SCHEMA_TYPES:
        jsonschema.validate(e, json_schema)

out = ROOT / "comms/outbox/worker-038.jsonl"
before = out.read_text() if out.exists() else ""
with out.open("a") as f:
    for e in EV:
        f.write(json.dumps(e, sort_keys=True) + "\n")

# Checkpoint (includes measured pins at emit time).
pins_after = {p: sha256(p) for p in [F0, SUPP, FROZEN, RUBRIC, CHECKER]}
ckpt = {
    "worker": "worker-038",
    "checkpoint": 4,
    "run": "W038-F0-CONFORMANCE-02",
    "at": NOW,
    "node_id": "F0",
    "gate": "G-F0",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN",
                  "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
    "verdicts": {
        "rev4_accept": {"sha256": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
                        "verdict": "accept", "binding": "advisory only (superseded hash)"},
        "rev28_accept": {"sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
                         "frozen_manifest": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
                         "frozen_revision": 28,
                         "declared_checker": "253/0 pass",
                         "independent": "11 PASS / 0 FAIL / 2 NOTE",
                         "freeze_integrity": "44/44 files, 2/2 logical, 5/5 critical pins match; 0 post-freeze modifications",
                         "verdict": "accept", "score": 3.5,
                         "binding": "bound at the measured hashes; one non-author verdict, not blind"},
    },
    "prior_blocker": {
        "id": "F0-FREEZE-DRIFT",
        "state": "resolved at manifest level by FROZEN rev28",
        "detail": "rev27 5fa3b3bf mismatched 5 of its listed files when measured at 00:35:06; rev28 2f358f6722d9 matches all 44",
    },
    "final_hashes": {p: H[p] for p in ARTIFACTS},
    "pins_at_emit": pins_after,
    "pins_stable_at_emit": (
        pins_after[F0] == "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
        and pins_after[FROZEN] == "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
    ),
    "outbox_events": [e["event_id"] for e in EV],
    "open_blockers": {
        "B-GF0-1": "one non-author accept at the frozen hash from this run; a second verdict from a distinct (and blind) reviewer identity is still required",
        "B-GF0-2": "canonical vs authoring F0 logical-artifact adjudication (REC-1/REC-2) remains controller-side",
        "W038-02-F1": "non-blocking: axes.genericity_kind='unresolved' vs comeager conclusion for AF-WCC-SCALAR-SPH; H4 blocks claim filing on that class until named",
    },
    "rejected_events": [],
    "numerics_lock": "respected: no N1 work, no self-gravitating solver written or run",
    "status": {"delivered": True, "result": "ACCEPT at frozen rev28 (score 3.5)",
               "validation_status": "unverified",
               "no_completion_claim": "no gate verdict; F0 remains draft_unverified; G-F0 remains pending"},
    "hours_spent_estimate": 0.5,
}
ck = ROOT / "runtime/state/w038_checkpoint_4.json"
ck.write_text(json.dumps(ckpt, indent=1) + "\n")

print("jsonschema validation:", "on" if HAVE_JS else "unavailable (field check only)")
print("events appended:", len(EV), "->", out)
print("outbox bytes", len(before), "->", out.stat().st_size)
print("checkpoint ->", ck)
print("pins stable at emit:", ckpt["pins_stable_at_emit"])
for p in ARTIFACTS:
    print(" ", H[p][:12], p)
