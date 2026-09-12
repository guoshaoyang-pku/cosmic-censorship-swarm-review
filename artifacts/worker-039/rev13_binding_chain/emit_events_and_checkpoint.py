#!/usr/bin/env python3
"""Emit worker-039 outbox events + checkpoint for W039-REV13-BINDCHAIN-01.

Appends validated JSONL to comms/outbox/deepseek-flash-39.jsonl and writes a worker checkpoint
under runtime/state/. Canonical artifacts are only read; the bundle directory is the only write
(plus the checker's deterministic evidence rewrite, which check D restores byte-identically).
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

TZ = dt.timezone(dt.timedelta(hours=8))
NOW = dt.datetime.now(TZ).replace(microsecond=0)
TS = NOW.isoformat()
STAMP = NOW.strftime("%Y%m%dT%H%M%S")

TASK_ID = "W039-REV13-BINDCHAIN-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
OUTBOX = ROOT / "comms/outbox/deepseek-flash-39.jsonl"

BUNDLE = [
    "report_rev13.json",
    "report_pre_repair.json",
    "checks.json",
    "f1_strictness.json",
    "f0_f1_direction.json",
    "fingerprints_pre_repair.json",
    "rev12_recovery.json",
    "README.md",
    "verify_binding_chain.py",
    "schema_fingerprint.py",
    "recover_rev12_baseline.py",
    "check_f1_strictness.py",
    "check_f0_f1_direction.py",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


hashes = {rel(HERE / b): sha(HERE / b) for b in BUNDLE}
canonical = {
    "schemas/af_wcc_vacuum.yaml": sha(ROOT / "schemas/af_wcc_vacuum.yaml"),
    "schemas/af_scc_c2_vacuum.yaml": sha(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
    "schemas/af_scc_c0_vacuum.yaml": sha(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
    "schemas/taxonomy_cases.jsonl": sha(ROOT / "schemas/taxonomy_cases.jsonl"),
    "artifacts/formulation/evidence/taxonomy_consistency.json": sha(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"),
    "artifacts/formulation/FROZEN.json": sha(ROOT / "artifacts/formulation/FROZEN.json"),
    "artifacts/formulation/KEY_MANIFEST.json": sha(ROOT / "artifacts/formulation/KEY_MANIFEST.json"),
    "research_map/formulation_taxonomy.yaml": sha(ROOT / "research_map/formulation_taxonomy.yaml"),
    "artifacts/formulation/formulation_taxonomy.yaml": sha(ROOT / "artifacts/formulation/formulation_taxonomy.yaml"),
}

entry_hashes = {
    "task_id": TASK_ID,
    "actor": "worker-039",
    "created_at": TS,
    "artifact_dir": rel(HERE),
    "artifacts": {rel(HERE / b): hashes[rel(HERE / b)] for b in BUNDLE},
    "canonical_inputs_measured_at_this_run": canonical,
}
(HERE / "entry_hashes.json").write_text(json.dumps(entry_hashes, indent=2, ensure_ascii=False) + "\n")
hashes[rel(HERE / "entry_hashes.json")] = sha(HERE / "entry_hashes.json")

rev13 = json.loads((HERE / "report_rev13.json").read_text())
pre = json.loads((HERE / "report_pre_repair.json").read_text())
k = json.loads((HERE / "f0_f1_direction.json").read_text())
j = json.loads((HERE / "f1_strictness.json").read_text())

FALSIFIER = (
    "Re-run verify_binding_chain.py: any schema/evidence/FROZEN/KEY_MANIFEST link whose declared "
    "value differs from the measured live bytes at the named pins flips the verdict; a strict-core "
    "field other than F1 quantifiers moving between the recovered rev12 baseline and the live bytes "
    "is reported as FAIL; check K is falsified by showing research_map/formulation_taxonomy.yaml "
    "lines 94/200 are historical rather than live, or by amending the G-F0-frozen taxonomy (which "
    "re-opens G-F0)."
)
NEXT_FALSIFIER = (
    "R3 reviewers: re-derive the five binding links and the item-(3) field diff by hand; and have "
    "the formulation lead/Astra adjudicate the F0-vs-F1 direction divergence (F0 L94/L200 assert "
    "'strictly stronger' where F1 rev13 asserts EQUIVALENT) before a G-FORM accept, because "
    "check_taxonomy_consistency.py does not compare predicate strength and G-F0 is frozen."
)

events = []

ev1 = {
    "event_id": f"w039-rev13bind-{STAMP}-artifact-report",
    "event_type": "artifact",
    "created_at": TS,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F1",
    "class_ids": CLASS_IDS,
    "task_id": TASK_ID,
    "artifact_type": "binding_chain_verification",
    "path": rel(HERE / "report_rev13.json"),
    "sha256": hashes[rel(HERE / "report_rev13.json")],
    "validation_status": "unverified",
    "gate": "G-FORM",
    "summary": (
        "Independent fail-closed verification of the REC-12 evidence-binding chain at the repaired "
        "bytes: F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, FROZEN rev29 815e08079aef, "
        "evidence 9e335e9ba1bf, corpus ccf7041bd0ff. 32 checks, 26 pass, 0 fail, 2 findings: (I) the "
        "F1 strict-core digest moved only in quantifiers.D5, the authorized item-(3) direction "
        "correction; (K) the G-F0-frozen research_map/formulation_taxonomy.yaml still asserts the "
        "opposite direction at live lines 94 and 200. All six binding links measure declared == live; "
        "evidence reproduces byte-identically from its checker; FROZEN rev29 files and logical "
        "artifacts all match; KEY_MANIFEST covers every schema key; check_class_schema exits 0 on all "
        "three. No gate verdict, no node status, no canonical edit."
    ),
    "evidence_refs": [
        f"schemas/af_wcc_vacuum.yaml#sha256:{canonical['schemas/af_wcc_vacuum.yaml']}",
        f"schemas/af_scc_c2_vacuum.yaml#sha256:{canonical['schemas/af_scc_c2_vacuum.yaml']}",
        f"schemas/af_scc_c0_vacuum.yaml#sha256:{canonical['schemas/af_scc_c0_vacuum.yaml']}",
        f"artifacts/formulation/FROZEN.json#sha256:{canonical['artifacts/formulation/FROZEN.json']}",
        f"artifacts/formulation/evidence/taxonomy_consistency.json#sha256:{canonical['artifacts/formulation/evidence/taxonomy_consistency.json']}",
        f"{rel(HERE / 'report_rev13.json')}#sha256:{hashes[rel(HERE / 'report_rev13.json')]}",
    ],
    "next_falsifier": NEXT_FALSIFIER,
    "claims_completion": False,
}
events.append(ev1)

ev2 = dict(ev1)
ev2.update(
    event_id=f"w039-rev13bind-{STAMP}-artifact-checks",
    artifact_type="verification_check_evidence",
    path=rel(HERE / "checks.json"),
    sha256=hashes[rel(HERE / "checks.json")],
    summary=(
        "Per-check evidence for both runs of the binding-chain verifier (pre-repair PENDING_REPAIR at "
        "rev12/FROZEN rev28 with the two recognised CF-20 defects; repaired CONSISTENT_WITH_FINDINGS "
        "at rev13/FROZEN rev29), including the deterministic checker reproduction, the corpus binding "
        "census, the FROZEN manifest sweep, the R22 key-coverage check, and the strict-core field "
        "diff against the recovered rev12 baseline."
    ),
    evidence_refs=[
        f"{rel(HERE / 'report_rev13.json')}#sha256:{hashes[rel(HERE / 'report_rev13.json')]}",
        f"{rel(HERE / 'report_pre_repair.json')}#sha256:{hashes[rel(HERE / 'report_pre_repair.json')]}",
        f"{rel(HERE / 'rev12_recovery.json')}#sha256:{hashes[rel(HERE / 'rev12_recovery.json')]}",
    ],
)
events.append(ev2)

ev3 = dict(ev1)
ev3.update(
    event_id=f"w039-rev13bind-{STAMP}-artifact-f1-strictness",
    artifact_type="review_check_evidence",
    path=rel(HERE / "f1_strictness.json"),
    sha256=hashes[rel(HERE / "f1_strictness.json")],
    summary=(
        "Check J: the repaired F1 is document-internally consistent with the direction it now asserts "
        "(single-q tail predicate stated with matching negation; variant SET relation says WEAKER; the "
        "old STRONGER wording survives only inside a bracketed revision note; witness tokens "
        "W076/T2/T3/T4 and a falsifier present; conclusion_type and comeager quantifier unchanged; "
        "class/node identity unchanged)."
    ),
)
events.append(ev3)

ev4 = dict(ev1)
ev4.update(
    event_id=f"w039-rev13bind-{STAMP}-artifact-f0-f1-direction",
    artifact_type="review_check_evidence",
    path=rel(HERE / "f0_f1_direction.json"),
    sha256=hashes[rel(HERE / "f0_f1_direction.json")],
    summary=(
        "Check K: F1 rev13 direction is WEAKER for variant SET; the supplement and VARIANT_REGISTRY "
        "agree; the variant-SET delta file's polarity hits are historical ledger sides. Two LIVE "
        "contradictions remain in the G-F0-frozen research_map/formulation_taxonomy.yaml (lines 94 and "
        "200 still call the set-based reading 'strictly stronger'). check_taxonomy_consistency.py "
        "returns CONSISTENT because it does not compare predicate strength."
    ),
)
events.append(ev4)

ev5 = {
    "event_id": f"w039-rev13bind-{STAMP}-claim",
    "event_type": "claim",
    "created_at": TS,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": CLASS_IDS,
    "task_id": TASK_ID,
    "conclusion_type": "open_problem",
    "statement": (
        "Verification finding (not a mathematical result) at the repaired pins F1 d9cebb9404b2, F2a "
        "e9a27996dfd3, F2b b2ab6acb2bbe, FROZEN rev29 815e08079aef, evidence 9e335e9ba1bf, corpus "
        "ccf7041bd0ff: the REC-12 evidence-binding chain is complete and reproducible at those bytes — "
        "every f0_binding declared hash equals the live file, the consistency evidence is a fresh "
        "deterministic product of check_taxonomy_consistency.py, all 36 corpus rows and the meta row "
        "carry the declared F0 sha and the superseded 66bf917bd368 appears nowhere, the FROZEN rev29 "
        "manifest matches every listed file and logical artifact, KEY_MANIFEST covers every schema key, "
        "and check_class_schema.py exits 0 on all three schemas. Two findings qualify the result: (I) "
        "the F1 strict-core digest moved relative to the recovered rev12 bytes and a field-level diff "
        "confines the move to quantifiers.D5 — the REC-12 item-(3) assertion-direction correction from "
        "'strictly STRONGER' to 'EQUIVALENT' — while F2a/F2b cores are byte-identical; (K) the "
        "G-F0-frozen research_map/formulation_taxonomy.yaml still asserts the opposite direction at "
        "live lines 94 and 200, which check_taxonomy_consistency.py cannot detect because it compares "
        "axes rather than predicate strength. This claim asserts no theorem, no gate verdict, no node "
        "status, and prescribes no schema or F0 edit."
    ),
    "assumptions": [
        "The repaired bytes are the ones the REC-12 repair published (rev13 schemas, FROZEN rev29); any later write voids the pins in this claim.",
        "rev12 baseline bytes were recovered from independently written hash-verified snapshots, not archived live; the recovery matches the rev12 pin recorded before the repair and F2a/F2b recovered cores equal the repaired cores.",
        "The verifier's strict-core partition is the one documented in schema_fingerprint.py; a field classified as allowed-prose is audited by check J rather than by the digest.",
        "Check K is lexical and local-window with historical-record exclusion; it reports candidates for adjudication, not a semantic proof.",
        "The F0 declared taxonomy is G-F0-frozen, so divergence there is reported, not repaired.",
    ],
    "falsifier": FALSIFIER,
    "evidence_refs": [
        f"schemas/af_wcc_vacuum.yaml#sha256:{canonical['schemas/af_wcc_vacuum.yaml']}",
        f"schemas/af_scc_c2_vacuum.yaml#sha256:{canonical['schemas/af_scc_c2_vacuum.yaml']}",
        f"schemas/af_scc_c0_vacuum.yaml#sha256:{canonical['schemas/af_scc_c0_vacuum.yaml']}",
        f"schemas/taxonomy_cases.jsonl#sha256:{canonical['schemas/taxonomy_cases.jsonl']}",
        f"artifacts/formulation/evidence/taxonomy_consistency.json#sha256:{canonical['artifacts/formulation/evidence/taxonomy_consistency.json']}",
        f"artifacts/formulation/FROZEN.json#sha256:{canonical['artifacts/formulation/FROZEN.json']}",
        f"research_map/formulation_taxonomy.yaml#sha256:{canonical['research_map/formulation_taxonomy.yaml']}",
        f"{rel(HERE / 'report_rev13.json')}#sha256:{hashes[rel(HERE / 'report_rev13.json')]}",
        f"{rel(HERE / 'f0_f1_direction.json')}#sha256:{hashes[rel(HERE / 'f0_f1_direction.json')]}",
    ],
    "artifact_refs": [
        f"{rel(HERE / 'report_rev13.json')}#sha256:{hashes[rel(HERE / 'report_rev13.json')]}",
        f"{rel(HERE / 'checks.json')}#sha256:{hashes[rel(HERE / 'checks.json')]}",
        f"{rel(HERE / 'f1_strictness.json')}#sha256:{hashes[rel(HERE / 'f1_strictness.json')]}",
        f"{rel(HERE / 'f0_f1_direction.json')}#sha256:{hashes[rel(HERE / 'f0_f1_direction.json')]}",
        f"{rel(HERE / 'rev12_recovery.json')}#sha256:{hashes[rel(HERE / 'rev12_recovery.json')]}",
        f"{rel(HERE / 'README.md')}#sha256:{hashes[rel(HERE / 'README.md')]}",
    ],
    "claims_completion": False,
}
events.append(ev5)

ev6 = {
    "event_id": f"w039-rev13bind-{STAMP}-review-gform-binding",
    "event_type": "review",
    "created_at": TS,
    "actor": "worker-039",
    "reviewer": "worker-039",
    "reviewer_independence": (
        "worker-039 authored none of the three schemas, the F0 taxonomy, the corpus, the consistency "
        "tool or the repair; every check re-measures the pinned bytes from disk and the rev12 baseline "
        "was recovered from other agents' hash-verified snapshots"
    ),
    "target_id": "G-FORM-EVIDENCE-BINDING-CHAIN",
    "node_id": "F1",
    "class_ids": CLASS_IDS,
    "gate": "G-FORM",
    "artifact": "schemas/af_wcc_vacuum.yaml",
    "artifact_sha256": canonical["schemas/af_wcc_vacuum.yaml"],
    "review_kind": "binding_chain_verification",
    "counts_as_full_schema_verdict": False,
    "verdict": "revise",
    "score": 3.5,
    "hard_failures": [
        "K_F0_F1_DIRECTION_DIVERGENCE: the G-F0-frozen research_map/formulation_taxonomy.yaml asserts at live lines 94 and 200 that the set-based visibility reading is 'strictly stronger', while repaired F1 (schemas/af_wcc_vacuum.yaml d9cebb9404b2, quantifiers.D5 and class_identity_variants) asserts the two readings are EQUIVALENT for causal geodesics. FROZEN rev29 records the same residual as blocker L-FORM-03. The binding gate is green and check_taxonomy_consistency.py is CONSISTENT, but neither compares predicate strength, so this is not cleared by them. F0 bytes are G-F0-frozen: adjudication, not a worker edit, is required."
    ],
    "findings": [
        "Positive: all six binding links measure declared == live at the repaired pins (F1/F2a/F2b, F0 declared taxonomy 0abb9ed8a961, class-contract supplement d7419b4e8963, evidence 9e335e9ba1bf); the evidence file is a fresh deterministic product of check_taxonomy_consistency.py; the case corpus is 36/36 + meta bound to the declared F0 sha with zero occurrences of the superseded 66bf917bd368; FROZEN rev29's 44 files and 2 logical artifacts all hash-match; KEY_MANIFEST has zero uncovered keys; check_class_schema.py exits 0 on all three schemas.",
        "I (finding, not a failure): the F1 strict-core digest moved relative to the recovered rev12 bytes; a field-level diff confines the move to quantifiers.D5, which is REC-12 item (3). F2a/F2b strict cores are byte-identical to rev12, and check J passes 5/5 on F1's internal consistency (direction asserted as WEAKER, old wording only inside a revision note, witness + falsifier present, conclusion_type and comeager quantifier unchanged).",
        "The variant-SET delta file and VARIANT_REGISTRY.json now agree with F1 (strength 'strictly weaker'); their STRONGER polarity hits are historical ledger sides ('from', D1 f0_reading) and are classified as records, not live claims.",
        "Pre-repair control: the same tool returned PENDING_REPAIR at rev12/FROZEN rev28, recognising exactly the two CF-20 defects (stale 675a99d0d25b pin; corpus state) rather than reporting a generic break — the tool distinguishes known-in-flight from unrecognised.",
        "Method note for the R3 reviewers: the rev12 baseline had to be recovered from worker-060/worker-007/worker-080/worker-032 snapshots because the first capture ran while the repair was in flight; recovery is pin-checked and the F2a/F2b equality is the control.",
    ],
    "evidence_refs": [
        f"schemas/af_wcc_vacuum.yaml#sha256:{canonical['schemas/af_wcc_vacuum.yaml']}",
        f"research_map/formulation_taxonomy.yaml#sha256:{canonical['research_map/formulation_taxonomy.yaml']}",
        f"artifacts/formulation/FROZEN.json#sha256:{canonical['artifacts/formulation/FROZEN.json']}",
        f"{rel(HERE / 'report_rev13.json')}#sha256:{hashes[rel(HERE / 'report_rev13.json')]}",
        f"{rel(HERE / 'f0_f1_direction.json')}#sha256:{hashes[rel(HERE / 'f0_f1_direction.json')]}",
        f"{rel(HERE / 'f1_strictness.json')}#sha256:{hashes[rel(HERE / 'f1_strictness.json')]}",
    ],
    "next_falsifier": NEXT_FALSIFIER,
    "claims_completion": False,
}
events.append(ev6)

ev7 = {
    "event_id": f"w039-rev13bind-{STAMP}-status",
    "event_type": "status",
    "created_at": TS,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F1",
    "class_ids": CLASS_IDS,
    "task_id": TASK_ID,
    "gate": "G-FORM",
    "status": "active",
    "hours": 0.8,
    "summary": (
        "No inbox assignment for worker-039; took one unclaimed class-bound task on the open critical "
        "path: independent verification of the REC-12 evidence-binding chain before the R3 review. "
        "Result CONSISTENT_WITH_FINDINGS at F1 d9cebb9404b2 / F2a e9a27996dfd3 / F2b b2ab6acb2bbe / "
        "FROZEN rev29 815e08079aef: 32 checks, 26 pass, 0 fail. All six binding links declared == live, "
        "evidence reproduces byte-identically, corpus 36/36+meta bound to the declared F0 sha, FROZEN "
        "rev29 fully matching, R22 coverage complete, gate exit 0 x3. Two findings for adjudication: "
        "the F1 core digest move is confined to the authorized quantifiers.D5 direction correction "
        "(check J passes 5/5), and the G-F0-frozen taxonomy still asserts the opposite direction at "
        "lines 94/200 (check K), which the consistency gate cannot see. No gate verdict, no node "
        "status, no canonical artifact edited, no claim promoted."
    ),
    "evidence_refs": [
        f"{rel(HERE / 'report_rev13.json')}#sha256:{hashes[rel(HERE / 'report_rev13.json')]}",
        f"{rel(HERE / 'checks.json')}#sha256:{hashes[rel(HERE / 'checks.json')]}",
        f"{rel(HERE / 'f0_f1_direction.json')}#sha256:{hashes[rel(HERE / 'f0_f1_direction.json')]}",
        f"{rel(HERE / 'entry_hashes.json')}#sha256:{hashes[rel(HERE / 'entry_hashes.json')]}",
    ],
    "next_falsifier": NEXT_FALSIFIER,
    "claims_completion": False,
}
events.append(ev7)

for e in events:
    validate_event(e)

with open(OUTBOX, "a", encoding="utf-8") as fh:
    for e in events:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")

checkpoint = {
    "task_id": TASK_ID,
    "worker": "worker-039",
    "node_id": "F1",
    "class_ids": CLASS_IDS,
    "gate": "G-FORM",
    "status": "COMPLETE",
    "checkpoint_at": TS,
    "verdict": "CONSISTENT_WITH_FINDINGS",
    "pre_repair_run": {"status": pre["status"], "counts": pre["counts"], "pins": pre["schema_pins"]},
    "rev13_run": {"status": rev13["status"], "counts": rev13["counts"], "pins": rev13["schema_pins"],
                  "frozen_revision": rev13.get("frozen_revision"),
                  "frozen_sha256": rev13["measured"].get("frozen_sha256")},
    "findings": {
        "I_strict_core": rev13["measured"].get("strict_core_drift"),
        "J_f1_strictness": rev13["measured"].get("f1_strictness", {}).get("verdict"),
        "K_f0_f1_direction": rev13["measured"].get("f0_f1_direction"),
    },
    "artifacts": {rel(HERE / b): hashes[rel(HERE / b)] for b in BUNDLE + ["entry_hashes.json"]},
    "canonical_inputs_measured": canonical,
    "events_emitted": [e["event_id"] for e in events],
    "outbox": rel(OUTBOX),
    "holes": [
        "rev12 raw bytes were recovered from other agents' hash-verified snapshots, not archived live (see rev12_recovery.json)",
        "check K is lexical/local-window: it flags the live F0 lines 94 and 200 for adjudication, it does not prove a contradiction in the order theory",
    ],
    "next_falsifier": NEXT_FALSIFIER,
    "non_claims": [
        "not a gate verdict, not a node status, not a schema accept",
        "does not assert the repaired schemas are mathematically correct",
        "does not adjudicate variant SET or amend F0",
    ],
}
ckpt_path = ROOT / f"runtime/state/w039_rev13_bindchain_checkpoint_{STAMP}.json"
ckpt_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n")

print(json.dumps({
    "outbox_appended": rel(OUTBOX),
    "events": [e["event_id"] for e in events],
    "checkpoint": rel(ckpt_path),
    "report_rev13_sha256": hashes[rel(HERE / "report_rev13.json")],
    "verdict": "CONSISTENT_WITH_FINDINGS",
}, indent=1))
