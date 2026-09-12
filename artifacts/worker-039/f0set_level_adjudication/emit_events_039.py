#!/usr/bin/env python3
"""Emit worker-039 outbox events + checkpoint for W039-F0SET-LEVEL-ADJ-01.

Appends validated JSONL events to comms/outbox/deepseek-flash-39.jsonl (idempotent by
event_id), writes artifacts/worker-039/f0set_level_adjudication/CHECKPOINT.json and
emission_record.json, then runs the global research_map/checkpoint.py.

Usage: python3 emit_events_039.py
Exit 0 on success; 3 on pin drift since report.json; 2 on schema validation failure.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/deepseek-flash-39.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
STAMP = NOW.strftime("%Y%m%dT%H%M%S%z")
TS = NOW.isoformat()

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def pin(rel_path: str) -> str:
    return sha256_file(ROOT / rel_path)


REPORT = HERE / "report.json"
CHECKER = HERE / "run_f0set_level_039.py"
README = HERE / "README.md"
ENTRY = HERE / "entry_hashes.json"

F0 = "research_map/formulation_taxonomy.yaml#0abb9ed8a961"
F1 = "schemas/af_wcc_vacuum.yaml#d9cebb9404b2"
REG = "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e"
DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04"

# canonical pins must still hold at emission time
PIN_CHECK = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json":
        "64b8d6394a044686de770879675eb4932ff980a942d45d16758b295d4851cecf",
}

report = json.loads(REPORT.read_text())
h_report, h_checker, h_readme = (sha256_file(p) for p in (REPORT, CHECKER, README))

# entry hashes bundle (excludes itself and the emitter, recorded separately)
entry = {
    "task_id": "W039-F0SET-LEVEL-ADJ-01",
    "actor": "worker-039",
    "created_at": TS,
    "sha256": {
        rel(REPORT): h_report,
        rel(CHECKER): h_checker,
        rel(README): h_readme,
    },
    "canonical_pins": {r: pin(r) for r in PIN_CHECK},
    "note": "self-hash of entry_hashes.json and of the emitter is excluded here; the emitter hash "
            "is recorded in emission_record.json",
}
ENTRY.write_text(json.dumps(entry, indent=2) + "\n")
h_entry = sha256_file(ENTRY)

drift = [r for r, want in PIN_CHECK.items() if pin(r) != want]
if drift:
    print(json.dumps({"error": "PIN_DRIFT_AT_EMISSION", "drift": drift}, indent=2))
    sys.exit(3)

TASK = "W039-F0SET-LEVEL-ADJ-01"
EVID = [f"{rel(REPORT)}#sha256:{h_report}", f"{rel(CHECKER)}#sha256:{h_checker}",
        f"{rel(README)}#sha256:{h_readme}", f"{rel(ENTRY)}#sha256:{h_entry}",
        F0, F1, REG, DELTA]

events = []


def ev(**kw):
    kw.setdefault("actor", "worker-039")
    kw.setdefault("created_at", TS)
    kw.setdefault("task_id", TASK)
    events.append(kw)


ev(event_id=f"w039-f0set-{STAMP}-artifact-report", event_type="artifact", node_id="F1",
   class_id="AF-WCC-VAC-GEN", class_ids=["AF-WCC-VAC-GEN"], gate="G-FORM",
   artifact_type="worker_measurement_report", path=rel(REPORT), sha256=h_report,
   validation_status="unverified",
   summary=("F0-vs-F1 SET strength label: level-resolved adjudication. F0 L199-200 is "
            "level-underspecified (true at class level, inverted at predicate level), not simply "
            "inverted; 9-carrier level census; 60,561 finite predicate cases 0 violations; S=>V "
            "proved, no finite witness (T3), omega-chain separates (T5); worker-063 finite witness "
            "not realizable in any preorder. No gate verdict, no node status, no F0 edit."))

ev(event_id=f"w039-f0set-{STAMP}-artifact-checker", event_type="artifact", node_id="F1",
   class_id="AF-WCC-VAC-GEN", class_ids=["AF-WCC-VAC-GEN"], gate="G-FORM",
   artifact_type="verifier_script", path=rel(CHECKER), sha256=h_checker,
   validation_status="unverified",
   summary="Stdlib-only fail-closed runner: preorder enumeration (n=3,4), chain/predicate census, "
           "omega-chain window certificates, worker-063 witness realizability, carrier extraction; "
           "exit 3 on canonical pin drift, 2 on control failure.")

ev(event_id=f"w039-f0set-{STAMP}-artifact-readme", event_type="artifact", node_id="F1",
   class_id="AF-WCC-VAC-GEN", class_ids=["AF-WCC-VAC-GEN"], gate="G-FORM",
   artifact_type="README", path=rel(README), sha256=h_readme, validation_status="unverified",
   summary="Narrative, theorem table T1-T6, answer to worker-063's named falsifier, decision "
           "options A/B/C, falsifier and non-claims.")

ev(event_id=f"w039-f0set-{STAMP}-artifact-entry-hashes", event_type="artifact", node_id="F1",
   class_id="AF-WCC-VAC-GEN", class_ids=["AF-WCC-VAC-GEN"], gate="G-FORM",
   artifact_type="entry_hashes", path=rel(ENTRY), sha256=h_entry, validation_status="unverified",
   summary="Hash-pinned bundle listing for this task; canonical pins re-measured at emission.")

ev(event_id=f"w039-f0set-{STAMP}-claim", event_type="claim", node_id="F1",
   class_id="AF-WCC-VAC-GEN", class_ids=["AF-WCC-VAC-GEN"], gate="G-FORM",
   conclusion_type="formal_model",
   statement=("At the declared preorder causal-structure level: (T1) whole-curve and tail "
              "containment in the same J^-(q) are equivalent; (T2) the single-q tail predicate S "
              "entails the union/SET reading V; (T3) no finite chain separates V from S because a "
              "finite chain has a maximum; (T4) finite I+ collapses V to S by a finite down-set "
              "cover; (T5) the infinite omega-chain separates V from S; (T6) hence S is strictly "
              "stronger than V as predicates while not-V is strictly stronger than not-S as class "
              "conclusions. Consequence: F0 canonical research_map/formulation_taxonomy.yaml "
              "L199-200 'the set-based reading ... is strictly stronger' is true at class level and "
              "inverted at predicate level, i.e. level-underspecified; F1 rev13, the registry and "
              "the SET delta are correct at predicate level; a flip of F0 to 'strictly weaker' "
              "would be false at class level."),
   assumptions=("Declared class structure: reflexive+transitive causal order (preorder); "
                "J^-(q) = downset of q; gamma a chain in causal order; I+ a set of points; "
                "V = gamma contained in the union of J^-(q) over q in I+; B-containment = gamma "
                "outside that union; no GR-realizability claim for the omega-chain."),
   falsifier=("(i) a derivation of V => S in the declared structure; (ii) a FINITE preorder+chain "
              "witness with V and not S; (iii) evidence that F0 L199-200 has no live class-level "
              "referent; (iv) drift of any pinned input."),
   evidence_refs=EVID,
   artifact_refs=EVID[:4],
   next_falsifier=("Show F0 L199-200's referent cannot be the variant class (then it is simply "
                   "inverted), or produce a finite causal witness separating V from S."))

ev(event_id=f"w039-f0set-{STAMP}-review-worker063", event_type="review",
   target_id="artifacts/worker-063/set_direction_adjudication/report.json#5a9ea89dca09",
   reviewer="worker-039", node_id="F1", class_id="AF-WCC-VAC-GEN",
   class_ids=["AF-WCC-VAC-GEN"], gate="G-FORM",
   verdict="revise", score=3, hard_failures=[],
   findings=[
       ("The L2 finite witness (tail [0,1], J(q0)={0}, J(q1)={1}) is not realizable in any "
        "preorder: 0<=1 and 1<=q1 force 0 in J(q1); exhaustive search finds it only in "
        "non-transitive reflexive relations. The separation requires the infinite omega-chain."),
       ("The L1/L2 census runs over arbitrary set systems, not causal structures; it cannot carry "
        "a predicate-level verdict on the declared class without the preorder restriction."),
       ("The direction conclusion (F1/registry/SET delta correct at predicate level; F0 label "
        "wrong at predicate level) is confirmed; the F0 carrier level assignment should be "
        "'predicate-only with a class-level scope caveat', i.e. SCOPE_AMBIGUOUS rather than "
        "unqualified INVERTED."),
   ],
   summary=("Support-invalid for the finite witness; direction confirmed. Recommend re-scoping "
            "HF-W063-SETDIR-1 to a level-annotation erratum."))

ev(event_id=f"w039-f0set-{STAMP}-status", event_type="status", node_id="F1",
   class_id="AF-WCC-VAC-GEN", class_ids=["AF-WCC-VAC-GEN"], gate="G-FORM",
   status="active", hours=0.35,
   summary=("No inbox card for worker-039; took one unclaimed class-bound critical-path task "
            "(worker-063's own named falsifier). Result: F0 L199-200 is SCOPE_AMBIGUOUS "
            "(true at class level, inverted at predicate level), so the correct R3 action is a "
            "level-qualified vocabulary ruling/erratum pointer, not an F0 byte flip. Independent "
            "results: T1-T6 proved, 60,561 finite predicate cases 0 violations, no finite witness, "
            "omega-chain window certificates at N=8/24/64, 9-carrier level census, worker-063 "
            "finite witness unrealizable in a preorder. No gate verdict, no node status, no "
            "canonical artifact edited, no claim promoted."),
   evidence_refs=EVID,
   next_falsifier=("R3 reviewers: decide which level convention is normative for the word "
                   "'stronger' in F0 prose; a finite preorder+chain witness with V and not S "
                   "would overturn T3 and re-open the finite-witness route."))

for e in events:
    validate_event(e)

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass

appended = []
with OUTBOX.open("a") as f:
    for e in events:
        if e["event_id"] in existing:
            continue
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
        appended.append(e["event_id"])

checkpoint = {
    "checkpoint_id": f"w039-f0set-ckpt-{STAMP}",
    "actor": "worker-039",
    "instance_id": "worker-039-20260912T010114-968807",
    "task_id": TASK,
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "created_at": TS,
    "status": "complete_worker_measurement",
    "verdict": ("F0_L199_200_LEVEL_UNDERSPECIFIED__F1_REGISTRY_DELTA_CORRECT_AT_PREDICATE_LEVEL"
                "__F0_VARIANTS_BLOCK_CORRECT_AT_CLASS_LEVEL"),
    "artifacts": {rel(REPORT): h_report, rel(CHECKER): h_checker, rel(README): h_readme,
                  rel(ENTRY): h_entry},
    "pins_verified_at_entry_and_exit": {r: pin(r) for r in PIN_CHECK},
    "emitted_event_ids": appended,
    "claimed_event_ids": [e["event_id"] for e in events],
    "counts": {
        "predicate_cases": report["finite_checks"]["cases"],
        "violations": len(report["finite_checks"]["violations"]),
        "preorders_n4": report["finite_checks"]["preorders"]["4"],
        "carriers": len(report["carrier_level_census"]),
        "controls_all_pass": report["controls"]["all_pass"],
    },
    "outbox": rel(OUTBOX),
}
ckpt_path = HERE / "CHECKPOINT.json"
ckpt_path.write_text(json.dumps(checkpoint, indent=2) + "\n")

# global 15-minute-style checkpoint (ingests outbox -> events.jsonl, validates, audits)
gp = subprocess.run([sys.executable, str(ROOT / "research_map/checkpoint.py"),
                     "--label", "worker-039-f0set-level"],
                    cwd=str(ROOT), capture_output=True, text=True, timeout=900)
global_ckpt = {}
try:
    global_ckpt = json.loads(gp.stdout)
except Exception:
    global_ckpt = {"stdout_tail": gp.stdout[-500:], "stderr_tail": gp.stderr[-500:]}
global_ckpt["returncode"] = gp.returncode

emission = {
    "task_id": TASK,
    "actor": "worker-039",
    "emitted_at": TS,
    "outbox": rel(OUTBOX),
    "emitter": {"path": rel(Path(__file__)), "sha256": sha256_file(Path(__file__))},
    "event_ids": [e["event_id"] for e in events],
    "appended_event_ids": appended,
    "checkpoint": rel(ckpt_path),
    "global_checkpoint": global_ckpt,
    "entry_hashes": rel(ENTRY),
    "note": "written after emission; emitter self-hash is over the file at this moment",
}
(HERE / "emission_record.json").write_text(json.dumps(emission, indent=2) + "\n")

print(json.dumps({
    "appended": appended,
    "skipped_existing": len(events) - len(appended),
    "checkpoint": rel(ckpt_path),
    "global_checkpoint_returncode": gp.returncode,
    "global_checkpoint": {k: global_ckpt.get(k) for k in
                          ("checkpoint_id", "map_validator", "evidence_hard_failures",
                           "comms", "events_pending_application", "gates")},
}, indent=2))
sys.exit(0 if gp.returncode == 0 else 1)
