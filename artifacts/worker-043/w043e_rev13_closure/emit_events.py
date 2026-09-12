#!/usr/bin/env python3
"""W043E step 3 - emit worker-043 upward events to comms/outbox/worker-043.jsonl.

Every event is validated with research_map/schemas.validate_event before writing.
Worker authority: no gate verdict, no node status transition, no validation_status
promotion.  The review event is a worker review of the landed repair, not one of the
two binding independent verdicts G-FORM requires.
"""
from __future__ import annotations

import datetime as dt
import hashlib
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
CKPT = ROOT / "runtime/state/w043e_checkpoint.json"
DOC = "artifacts/worker-043/w043e_rev13_closure"
TASK_ID = "W043E-REV13-CLOSURE-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_IDS = ["F1", "F2a", "F2b"]

report = json.loads((HERE / "report.json").read_text())
manifest = json.loads((HERE / "MANIFEST.json").read_text())
D = manifest["deliverables"]
for extra in ("MANIFEST.json",):
    b = (HERE / extra).read_bytes()
    D[extra] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def sha(rel: str) -> str:
    return D[rel]["sha256"]


def ref(rel: str) -> str:
    return f"{DOC}/{rel}#{D[rel]['sha256'][:12]}"


def ev(event_id: str, event_type: str, **kw):
    e = {"event_id": event_id, "event_type": event_type, "created_at": TS,
         "actor": "worker-043", **kw}
    validate_event(e)
    return e


# --------------------------------------------------------------- checkpoint
pins_end = report["pins_end"]
ckpt = {
    "schema": "w043e-checkpoint/v1",
    "task_id": TASK_ID,
    "worker": "worker-043",
    "created_at": TS,
    "node_ids": NODE_IDS,
    "class_ids": CLASS_IDS,
    "gate": report["gate"],
    "verdict": report["verdict"],
    "chain_closed_live": report["chain_closed_live"],
    "amended_chain_closed": report["amended_chain_closed"],
    "checks": [{"id": c["id"], "status": c["status"]} for c in report["checks"]],
    "findings": [{"id": f["id"], "severity": f["severity"]} for f in report["findings"]],
    "pins": {k: pins_end[k] for k in pins_end
             if k.startswith(("schemas/", "artifacts/formulation/evidence",
                              "artifacts/formulation/FROZEN",
                              "artifacts/formulation/tools"))},
    "evidence_refs": [ref("report.json"), ref("README.md")],
    "next_falsifier": report["next_falsifier"],
    "authority_note": report["authority_note"],
}
CKPT.parent.mkdir(parents=True, exist_ok=True)
CKPT.write_text(json.dumps(ckpt, indent=2) + "\n")
ckpt_sha = hashlib.sha256(CKPT.read_bytes()).hexdigest()
ckpt_ref = f"runtime/state/w043e_checkpoint.json#{ckpt_sha[:12]}"

events = []

# ---------------------------------------------------------------- status(claim)
events.append(ev(
    f"w043e-{TAG}-status-claim",
    "status",
    node_id="F1,F2a,F2b",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate=report["gate"],
    task_id=TASK_ID,
    status="active",
    hours=0.5,
    summary=(
        "Took one bounded class-bound task (no inbox card for worker-043): independent "
        "post-repair binding-closure audit of the landed astra-life05-evidence-binding-repair "
        "at rev13 / FROZEN rev29. Result: pointer resolves 3/3 but the evidence-to-F0 chain is "
        "open 3/3 (evidence 9e335e9b carries no map_taxonomy_sha256 / lead_contract_sha256 / "
        "measured_at). Executed controls: tool byte-deterministic; evidence hash invariant under "
        "an unchecked F0 mutation; compared-field mutation caught. Minimal completion tested "
        "(evidence_bound_candidate 1322f3d37786 + single-token re-point -> chain_closed True). "
        "Secondary: F2b line 246 false strength relation persists at rev13. Verdict revise; "
        "worker evidence only, no gate verdict or node status."),
    evidence_refs=[ref("report.json"), ref("raw/chain_live_F2a.json"),
                   ref("raw/evidence_bound_candidate.json"), ckpt_ref],
    next_falsifier=report["next_falsifier"],
))

# ------------------------------------------------------------------- artifacts
for rel, kind in [
    ("report.json", "report"),
    ("closure_probe.py", "independent_checker"),
    ("MANIFEST.json", "manifest"),
    ("raw/evidence_bound_candidate.json", "evidence_candidate"),
    ("raw/chain_live_F2a.json", "raw_chain_check"),
    ("raw/chain_amended_F2a.json", "raw_chain_check"),
    ("raw/residual_f2b.json", "raw_measurement"),
    ("raw/frozen_restamp.json", "raw_measurement"),
    ("raw/reviewer_binding_findings.json", "raw_measurement"),
]:
    events.append(ev(
        f"w043e-{TAG}-artifact-{Path(rel).stem}",
        "artifact",
        node_id="F1,F2a,F2b",
        node_ids=NODE_IDS,
        class_id="AF-SCC-C2-VAC-GEN",
        class_ids=CLASS_IDS,
        gate=report["gate"],
        task_id=TASK_ID,
        artifact_type=kind,
        path=f"{DOC}/{rel}",
        sha256=sha(rel),
        bytes=D[rel]["bytes"],
        validation_status="unverified",
        evidence_refs=[ref(rel)],
        falsifier=report["next_falsifier"],
    ))

# ------------------------------------------------------------------------ claim
events.append(ev(
    f"w043e-{TAG}-claim-closure",
    "claim",
    node_id="F1,F2a,F2b",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate=report["gate"],
    task_id=TASK_ID,
    conclusion_type="formal_model",
    statement=(
        "Artifact-and-binding measurement, not a mathematics or physics claim. At the landed "
        "rev13 / FROZEN rev29 bytes (F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, "
        "evidence 9e335e9ba1bf 495 B, FROZEN 815e08079aef, checker de356d999ea3 unchanged, F0 "
        "0abb9ed8a961 / supplement d7419b4e8963 unchanged), astra-life05-evidence-binding-repair "
        "item (2) resolved the pointer in all three schemas but did not close the f0_binding "
        "chain: the evidence document has eight fields and no map_taxonomy_sha256, "
        "lead_contract_sha256 or measured_at, so it cannot be tied to the F0 bytes it reports on. "
        "The canonical checker is byte-deterministic on unchanged inputs (9e335e9b twice) but its "
        "output is unchanged when an unchecked F0 field is mutated (F0 0abb9ed8a961 -> "
        "f1a37ffa91d9, evidence still 9e335e9b), while a compared-field mutation does move it "
        "(exit 1); the gap is the missing input-hash binding. Appending the two tree hashes and "
        "measured_at yields a byte-stable candidate 1322f3d37786, and re-pointing each schema to "
        "it is a single-token substitution after which the closure predicate is True for all "
        "three classes; tamper controls fail it. Secondary measurement at the same bytes: F2b "
        "line 246 still states 'C2 is a strictly larger extension class' while F2b line 239 "
        "states E_C0 contains ... contains E_C2 (worker-083 L-FORM-01 unapplied)."),
    assumptions=[
        "the measured bytes did not change during the audit window (13/13 pins identical at "
        "start and end; FROZEN was re-stamped at 00:57:26 before the second window with "
        "identical content pins, which the report records as S4b)",
        "the closure predicate is evaluated against measured bytes, not FROZEN revision labels",
        "the canonical checker was executed only against a scratch ROOT because it rewrites its "
        "own evidence file",
        "worker verdicts cannot set node status, validation_status or a gate verdict, and this "
        "audit is not one of the two binding independent verdicts per class",
    ],
    falsifier=report["next_falsifier"],
    evidence_refs=[ref("report.json"), ref("README.md"),
                   ref("raw/chain_live_F1.json"), ref("raw/chain_live_F2a.json"),
                   ref("raw/chain_live_F2b.json"), ref("raw/tool_run1.json"),
                   ref("raw/tool_run2.json"), ref("raw/f0_unchecked_mutation.json"),
                   ref("raw/evidence_bound_candidate.json"),
                   "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                   "artifacts/formulation/FROZEN.json#815e08079aef"],
    artifact_refs=[ref("report.json")],
    non_claims=["not a gate verdict", "not a review verdict binding G-FORM",
                "no canonical byte written", "does not adjudicate the F1 strictness direction"],
))

# ----------------------------------------------------------------------- review
events.append(ev(
    f"w043e-{TAG}-review-repair",
    "review",
    target_id="astra-life05-evidence-binding-repair (landed rev13 / FROZEN rev29 815e08079aef)",
    reviewer="worker-043",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate=report["gate"],
    task_id=TASK_ID,
    verdict="revise",
    score=3.0,
    counts_as_full_schema_verdict=False,
    gate_eligible=False,
    hard_failures=[
        {"id": "HF-W043E-1", "severity": "blocking-for-clean-accept",
         "axis": "f0_binding closure (all three classes)",
         "finding": report["findings"][0]["finding"],
         "falsifier": report["findings"][0]["falsifier"]},
        {"id": "HF-W043E-2", "severity": "hard (residual at rev13)",
         "axis": "AF-SCC-C0-VAC-GEN internal strength relation",
         "finding": report["findings"][1]["finding"],
         "falsifier": report["findings"][1]["falsifier"]},
    ],
    findings=[
        "Pointer item resolved 3/3: F1/F2a/F2b declare 9e335e9ba1bf and the live evidence "
        "measures 9e335e9ba1bf; FROZEN rev29 pins all three schemas, mirrors, evidence and tool.",
        "Closure item not resolved: the refreshed evidence binds no inputs, so the rev27 closure "
        "item (e) family (F1-review-090 F090-05, F2b-rev12-069 HF-069F2B-I09, F2a-review-19 "
        "HF-19-F2A-3, F2a-review-043 HF-043-2, F1-review-rev27-a HF-071-01, F2a-review-rev27-c "
        "HF-W092-F2A-01, F2b-review-022, G-FORM-evidence-collision-086) survives the repair.",
        "Minimal completion is tested and ready: raw/evidence_bound_candidate.json "
        "1322f3d37786 (byte-stable) + one-token re-point per schema -> chain_closed True; or "
        "land worker-083 W083-REV13-REPAIR-PACKET-01 L-FORM-02 (enriched writer + restored "
        "675a99d0) instead, which keeps schema bytes.",
        "rev12 -> rev13 byte delta contains 0 unexpected semantic changes (F1 6R/1I, F2a/F2b "
        "3R/1I); the three F1 strictness legs moved but their correctness is worker-061/076/040 "
        "territory and is not endorsed here.",
        "FROZEN rev29 was re-stamped once (3d9e3d77 -> 815e0807) with identical content pins; "
        "pin FROZEN by file hash, not by revision label.",
        "Residual: F2b line 246 vs line 239 self-contradiction (worker-083 L-FORM-01).",
    ],
    reviewed_sha256=pins_end["artifacts/formulation/FROZEN.json"],
    landed_sha256={"F1": pins_end["schemas/af_wcc_vacuum.yaml"],
                   "F2a": pins_end["schemas/af_scc_c2_vacuum.yaml"],
                   "F2b": pins_end["schemas/af_scc_c0_vacuum.yaml"],
                   "evidence": pins_end["artifacts/formulation/evidence/taxonomy_consistency.json"],
                   "FROZEN": pins_end["artifacts/formulation/FROZEN.json"]},
    authority_note=report["authority_note"],
    evidence_refs=[ref("report.json"), ref("README.md"), ckpt_ref],
))

# ---------------------------------------------------------------------- blocker
events.append(ev(
    f"w043e-{TAG}-blocker-closure",
    "blocker",
    node_id="F1,F2a,F2b",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate=report["gate"],
    task_id=TASK_ID,
    description=report["findings"][0]["finding"],
    needed_to_unblock=report["findings"][0]["repair"],
    evidence_refs=[ref("report.json"), ref("raw/chain_live_F1.json"),
                   ref("raw/chain_live_F2a.json"), ref("raw/chain_live_F2b.json"),
                   ref("raw/evidence_bound_candidate.json"),
                   "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf"],
    falsifier=report["findings"][0]["falsifier"],
))

# --------------------------------------------------------------- status(complete)
events.append(ev(
    f"w043e-{TAG}-status-complete",
    "status",
    node_id="F1,F2a,F2b",
    node_ids=NODE_IDS,
    class_id="AF-SCC-C2-VAC-GEN",
    class_ids=CLASS_IDS,
    gate=report["gate"],
    task_id=TASK_ID,
    status="active",
    hours=0.5,
    summary=(
        "W043E-REV13-CLOSURE-01 complete at worker level: one bounded class-bound task, 21/21 "
        "checks executed, 8/8 instrument/mutation controls behave as predicted, canonical tree "
        "unchanged (0/13 pin drift; every tool run inside scratch). Verdict revise: the landed "
        "refresh resolves the pointer but leaves the evidence unbound to the F0 trees, so the "
        "r3 blind round would re-raise the rev27 closure item (e) family; the tested minimal "
        "completion is one token per schema plus the binding fields in the evidence. Artifact "
        "and checkpoint written and hash-pinned. Completion claim only; no node transition, no "
        "gate verdict, no canonical byte changed."),
    evidence_refs=[ref("report.json"), ref("MANIFEST.json"), ckpt_ref],
    next_falsifier=report["next_falsifier"],
))

with OUTBOX.open("a") as fh:
    for e in events:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
print(f"emitted {len(events)} events to {OUTBOX.relative_to(ROOT)}; checkpoint {ckpt_ref}")
