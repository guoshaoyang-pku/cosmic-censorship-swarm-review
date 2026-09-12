#!/usr/bin/env python3
"""Emit W054-A0-VOCAB-RECONCILE-01 events to comms/outbox/worker-054.jsonl.

Self-validates every event with research_map/schemas.validate_event before writing.
No canonical state is touched here; ingest is the controller's locked step.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TS = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
NOW = datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


ART = "artifacts/worker-054/a0_vocab_reconcile"
report = HERE / "report.json"
edits = HERE / "proposed_a0_vocab_edits.json"
patched = HERE / "evaluation_rubric.patched.proposal.yaml"
harness = HERE / "reconcile.py"
readme = HERE / "README.md"
rp = json.loads(report.read_text())

CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
TASK = "W054-A0-VOCAB-RECONCILE-01"
GATE = "G-AUDIT"
NODE = "A0"
PRIMARY_CLASS = "AF-SCC-C2-VAC-GEN"
A0_SHA = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"

REFS = [
    f"{ART}/report.json#{sha(report)[:12]}",
    f"{ART}/proposed_a0_vocab_edits.json#{sha(edits)[:12]}",
    f"{ART}/evaluation_rubric.patched.proposal.yaml#{sha(patched)[:12]}",
    f"{ART}/reconcile.py#{sha(harness)[:12]}",
    f"{ART}/README.md#{sha(readme)[:12]}",
    "evaluation_rubric.yaml#d748a9e3574e",
    "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
    "artifacts/formulation/FROZEN.json#2f358f6722d9",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
    "ledger/theorems.jsonl#a1674f094979",
    "ledger/citation_audit.csv#315c19145065",
]

common = {"task_id": TASK, "node_id": NODE, "gate": GATE, "class_id": PRIMARY_CLASS,
          "class_ids": CLASS_IDS, "created_at": NOW, "actor": "worker-054"}


def ev(**kw):
    e = dict(common)
    e.update(kw)
    return e


events = []
for name, path, atype, note in [
    ("report", report, "verification_report",
     "Full census/patch/controls record with all nine pins and the falsifier."),
    ("edits", edits, "proposal",
     "12 line-anchored edits {line, old, new, kind, owner_decision}; proposal only, not applied."),
    ("patched", patched, "proposal_copy",
     "A0 byte copy with the proposal applied; zero-unmet under the same census; NOT canonical."),
    ("harness", harness, "tool",
     "Deterministic read-only harness; exits 0 iff 9/9 controls pass; fail-closed on pin/line drift."),
    ("readme", readme, "summary",
     "One-page summary: pins, census table, controls, advisory, falsifier, reproduction."),
]:
    events.append(ev(event_id=f"w054-a0vocab-{TS}-artifact-{name}", event_type="artifact",
                     artifact_type=atype, path=f"{ART}/{path.name}",
                     sha256=sha(path), validation_status="unverified",
                     evidence_refs=REFS, note=note))

events.append(ev(
    event_id=f"w054-a0vocab-{TS}-review",
    event_type="review", reviewer="worker-054", target_id="A0",
    target={"path": "evaluation_rubric.yaml", "sha256": A0_SHA, "node_id": NODE, "gate": GATE},
    verdict="revise", score=3.0,
    hard_failures=[
        "conclusion_primary is not a registered canonical token for any of the 4 frozen classes "
        "(future_asymptotic_predictability, C2_inextendibility_of_maximal_development, "
        "C0_inextendibility_of_maximal_development); canonical: weak_cosmic_censorship, "
        "scc_c2_future_inextendibility, scc_c0_future_inextendibility",
        "G-FORM genericity enum (line 128) omits the frozen kind residual_comeager (only its alias "
        "comeager) and contains unregistered tokens codim_ge_1, non_generic_excluded",
        "G-LIT criteria/detectors (lines 28,30,138,142,184,190) name resolution_status and "
        "quantity_check, neither of which exists in the frozen L0/L1",
        "metrics.citation_support weights (verified_primary/verified_secondary/partial/unresolved/"
        "contradicted) match no frozen L1 status/verdict value set, so citation_support == 1.0 is "
        "not computable as written",
    ],
    findings=[
        "13 unmet vocabulary slots on the pinned A0 under a census driven by "
        "VOCAB_ALIASES.json + frozen L0/L1 field and value sets (9/9 controls pass).",
        "A 12-edit line-anchored proposal applied only to a byte copy is 0-unmet under the same "
        "census; the wrong-class decoy is still flagged; the diff is confined to the declared "
        "lines; all nine canonical hashes are unchanged across the run.",
        "2 edits are flagged owner_decision: the AF-WCC-SCALAR-SPH pending-genericity rule "
        "(taxonomy kind `unresolved` is unregistered) and the quantity-record substitute for "
        "quantity_check (no frozen drop-in field).",
    ],
    evidence_refs=REFS,
    next_falsifier=rp["falsifier"],
))

events.append(ev(
    event_id=f"w054-a0vocab-{TS}-claim",
    event_type="claim", conclusion_type="formal_model",
    statement=(
        "At the nine pinned hashes (A0 d748a9e3574e; taxonomy rev5 0abb9ed8a961; F1 cce9c60146d6; "
        "F2a 5476a3f2c6bc; F2b 55d0a1ea9bda; VOCAB_ALIASES 46cd9f1eb534; L0 a1674f094979; L1 "
        "315c19145065; FROZEN rev28 2f358f6722d9, all verified pre- and post-run with zero drift), "
        "the pinned A0 evaluation rubric has exactly 13 unmet vocabulary slots: four class "
        "conclusion_primary tokens and one conclusion_implied token are unregistered non-canonical "
        "names, the G-FORM genericity enum omits the frozen kind residual_comeager and carries two "
        "unregistered kinds, the G-LIT criteria and HF-03/HF-04 detectors name resolution_status "
        "and quantity_check which occur zero times in the frozen L0/L1, and the citation_support "
        "weights match no frozen value set. A 12-edit line-anchored proposal applied only to a byte "
        "copy is 0-unmet under the same census; a wrong-class decoy mapping is still flagged; the "
        "diff is confined to the declared lines; no canonical hash changes. This is a read-only "
        "machine measurement plus an owner-reviewable proposal, not a gate verdict and not an "
        "applied edit; the advisory finding that AF-WCC-SCALAR-SPH's taxonomy genericity_kind "
        "`unresolved` has no registered token is formulation-owned and was reported, not patched."
    ),
    assumptions=[
        "vocabulary authority is the frozen artifacts themselves: VOCAB_ALIASES.json for tokens, "
        "and the L0/L1 field/value sets measured at the pinned hashes",
        "the alias policy 'canonical token first; aliases are equivalent for consistency checks "
        "only' makes alias-only use an advisory downgrade and unregistered use a defect",
        "the proposal is evaluated only on a byte copy; canonical promotion is the A0 owner's call",
        "no semantic claim about the rubric's mathematical adequacy is made; this is vocabulary "
        "reconciliation",
    ],
    falsifier=rp["falsifier"],
    evidence_refs=REFS, artifact_refs=REFS[:5],
))

events.append(ev(
    event_id=f"w054-a0vocab-{TS}-status",
    event_type="status", status="active", hours=0.4,
    summary=(
        "W054-A0-VOCAB-RECONCILE-01 complete at worker level: one bounded class-bound task taken "
        "(A0 rubric / G-AUDIT). Census: 13 unmet vocabulary slots on the pinned A0; proposal: 12 "
        "line-anchored edits applied only to a copy -> 0 unmet; controls 9/9 (pins, negative "
        "control, decoy specificity, diff confinement, no canonical write, schema/taxonomy alias "
        "agreement). Advisory to lead-formulation: taxonomy rev5 AF-WCC-SCALAR-SPH "
        "genericity_kind `unresolved` is not a registered token in VOCAB_ALIASES.json, so no "
        "machine check can admit that class yet. No canonical write; no gate verdict."
    ),
    evidence_refs=REFS, next_falsifier=rp["falsifier"],
))

out = ROOT / "comms/outbox/worker-054.jsonl"
with open(out, "a") as fh:
    for e in events:
        validate_event(e)
        fh.write(json.dumps(e) + "\n")

print(json.dumps({
    "written": str(out),
    "count": len(events),
    "event_ids": [e["event_id"] for e in events],
    "artifact_sha256": {p.name: sha(p) for p in (report, edits, patched, harness, readme)},
}, indent=1))
