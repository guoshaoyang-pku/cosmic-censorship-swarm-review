#!/usr/bin/env python3
"""W043D step 4 - emit the worker's upward events to comms/outbox/worker-043.jsonl.

Validates every event against research_map/schemas.validate_event before writing.
No review verdict is emitted: no canonical artifact changed, so the standing F2a
revise verdict is unaffected.  Ingest is left to the controller.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(CST).replace(microsecond=0)
TS = NOW.isoformat()
TAG = NOW.strftime("%Y%m%dT%H%M")
OUTBOX = ROOT / "comms/outbox/worker-043.jsonl"

TASK_ID = "W043D-R2-DURABILITY-01"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_IDS = ["F0", "F1", "F2a", "F2b"]
DOC = "artifacts/worker-043/w043d_r2_durability"

manifest = json.loads((HERE / "MANIFEST.json").read_text())
report = json.loads((HERE / "report.json").read_text())
acceptance = json.loads((HERE / "acceptance.json").read_text())
D = dict(manifest["deliverables"])
# the manifest cannot carry its own hash; measure it here for the artifact event
_mb = (HERE / "MANIFEST.json").read_bytes()
D["MANIFEST.json"] = {"sha256": __import__("hashlib").sha256(_mb).hexdigest(),
                      "bytes": len(_mb)}


def ev(event_id: str, event_type: str, **kw):
    e = {"event_id": event_id, "event_type": event_type, "created_at": TS,
         "actor": "worker-043", **kw}
    validate_event(e)
    return e


events = []

# ---- artifacts ---------------------------------------------------------------
for rel, kind in [
    ("report.json", "report"),
    ("acceptance.json", "acceptance_report"),
    ("MANIFEST.json", "manifest"),
    ("raw/evidence_restored_675a99d0.json", "evidence_restored"),
    ("durability.patch", "patch"),
    ("patched_check_taxonomy_consistency.py", "patched_tool"),
    ("raw/reconstruction.json", "reconstruction"),
]:
    events.append(ev(
        f"w043d-{TAG}-artifact-{Path(rel).stem}",
        "artifact",
        node_id="F2a",
        node_ids=NODE_IDS,
        class_id="AF-SCC-C2-VAC-GEN",
        class_ids=CLASS_IDS,
        artifact_type=kind,
        path=f"{DOC}/{rel}",
        sha256=D[rel]["sha256"],
        validation_status="unverified",
        gate="G-FORM",
        task_id=TASK_ID,
        evidence_refs=[f"{DOC}/{rel}#{D[rel]['sha256'][:12]}"],
        falsifier=report["next_falsifier"],
    ))

# ---- claim -------------------------------------------------------------------
events.append(ev(
    f"w043d-{TAG}-claim-r2-acceptance",
    "claim",
    node_id="F2a",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate="G-FORM",
    task_id=TASK_ID,
    conclusion_type="formal_model",
    statement=(
        "At pins F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda / FROZEN rev28 "
        "2f358f6722d9 / evidence 9e335e9ba1bf, the declared consistency-evidence generation "
        "675a99d0d25b2b37 (728 B) is byte-reproducible from the lean canonical document plus "
        "insertion-ordered {map_taxonomy_sha256=0abb9ed8a961, lead_contract_sha256=d7419b4e8963, "
        "measured_at=2026-09-12T00:32:02+08:00} (independently reproduces worker-086 F-086-C1). "
        "On sandbox copies, repair R2 (restore those bytes, no schema edit; FROZEN rev29 moving "
        "only the evidence pin) flips the independent W043C full-schema checker to accept / 0 FAIL "
        "with R15+R16 PASS and the three schema hashes unchanged; R2 alone is not durable because "
        "check_taxonomy_consistency.py:80 unconditionally rewrites the canonical evidence path "
        "(one run moves 675a99d0 -> 9e335e9b and reopens R15/R16); redirecting that write to "
        "taxonomy_consistency_report.json makes two consecutive verification runs leave 675a99d0 "
        "in place with the checker still accept / 0 FAIL."
    ),
    assumptions=[
        "the declared bytes are the correct binding target and the declared measured_at is the "
        "authentic generation instant (worker-086 F-086-C1)",
        "the independent checker artifacts/worker-043/f2a_rev12_verdict/check_f2a_rev12.py is a "
        "valid instrument at the pinned bytes (self-test 8/8 on the pristine sandbox)",
        "no canonical file changed during the test (measured before/after; drift list empty)",
    ],
    falsifier=report["next_falsifier"],
    evidence_refs=[
        f"{DOC}/report.json#{D['report.json']['sha256'][:12]}",
        f"{DOC}/acceptance.json#{D['acceptance.json']['sha256'][:12]}",
        f"{DOC}/raw/reconstruction.json#{D['raw/reconstruction.json']['sha256'][:12]}",
        f"{DOC}/raw/evidence_restored_675a99d0.json#{D['raw/evidence_restored_675a99d0.json']['sha256'][:12]}",
        f"{DOC}/durability.patch#{D['durability.patch']['sha256'][:12]}",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3",
        "reviews/G-FORM-evidence-collision-086.json#888477f5e193",
    ],
    artifact_refs=[f"{DOC}/report.json#{D['report.json']['sha256'][:12]}"],
    non_claims=[
        "not a gate verdict and not a review verdict",
        "no canonical file written; R2 is an owner-applied proposal",
        "does not adjudicate worker-047 C06/C07 taxonomy-vs-schema binder divergence",
    ],
))

# ---- blocker -----------------------------------------------------------------
events.append(ev(
    f"w043d-{TAG}-blocker-durability",
    "blocker",
    node_id="F2a",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate="G-FORM",
    task_id=TASK_ID,
    description=(
        "The binding repair is now fully specified and pre-verified but is not yet durable on "
        "the canonical tree: check_taxonomy_consistency.py:80 unconditionally rewrites "
        "artifacts/formulation/evidence/taxonomy_consistency.json with the pin-free document, so "
        "any verification run re-destroys the declared 675a99d0 binding even after a byte-exact "
        "restore (measured: one run 675a99d0 -> 9e335e9b; R15/R16 FAIL again). The minimal-churn "
        "repair R2 is tested: restore declared bytes + FROZEN rev29 evidence-pin-only + redirect "
        "the writer -> independent checker accept / 0 FAIL with schema hashes unchanged."
    ),
    needed_to_unblock=(
        "lead-formulation (canonical-path owner) applies, in order: (1) restore the 728 declared "
        "bytes from raw/evidence_restored_675a99d0.json to the canonical evidence path; (2) bump "
        "FROZEN to rev29 with a wall-clock frozen_at and only the evidence pin moved to 675a99d0; "
        "(3) apply durability.patch to check_taxonomy_consistency.py (re-emit its artifact event "
        "and re-pin it in the same bump if pinned); (4) do not run the unpatched checker after "
        "step 1. Then re-issue the two binding-axis verdicts; schema hashes do not change, so all "
        "content verdicts keep their bindings."
    ),
    evidence_refs=[
        f"{DOC}/report.json#{D['report.json']['sha256'][:12]}",
        f"{DOC}/durability.patch#{D['durability.patch']['sha256'][:12]}",
        f"{DOC}/patched_check_taxonomy_consistency.py#{D['patched_check_taxonomy_consistency.py']['sha256'][:12]}",
        "artifacts/formulation/tools/check_taxonomy_consistency.py:80",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "reviews/G-FORM-evidence-collision-086.json#888477f5e193",
    ],
))

# ---- status ------------------------------------------------------------------
events.append(ev(
    f"w043d-{TAG}-status-complete",
    "status",
    node_id="F2a",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate="G-FORM",
    task_id=TASK_ID,
    status="active",
    hours=0.4,
    summary=(
        "W043D-R2-DURABILITY-01 complete at worker level: one bounded class-bound task "
        "(AF-SCC-C2-VAC-GEN + F1/F2b siblings). 7 artifacts on disk and hash-pinned, 6/6 "
        "pre-registered expectations hold, instrument self-test 8/8, canonical tree unchanged "
        "(drift list empty), checkpoint runtime/state/w043d_checkpoint.json. Verdict for the "
        "repair: accept_for_repair_R2. No node transition, no gate verdict, no canonical byte "
        "changed."
    ),
    evidence_refs=[
        f"{DOC}/report.json#{D['report.json']['sha256'][:12]}",
        f"{DOC}/acceptance.json#{D['acceptance.json']['sha256'][:12]}",
        "runtime/state/w043d_checkpoint.json",
    ],
    next_falsifier=report["next_falsifier"],
))

with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

print(json.dumps({"outbox": str(OUTBOX), "n_events": len(events),
                  "event_ids": [e["event_id"] for e in events]}, indent=1))
