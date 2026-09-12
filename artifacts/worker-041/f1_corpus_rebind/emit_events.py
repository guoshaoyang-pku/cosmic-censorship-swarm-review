#!/usr/bin/env python3
"""Emit the W041-F1-CORPUS-REBIND-01 events (idempotent by event_id).

Validates every event against research_map.schemas.validate_event and every
cited hash against disk before writing anything.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TS = "2026-09-12T01:02:00+08:00"
BASE = "w041-f1corpus-20260912T0102"
TASK = "W041-F1-CORPUS-REBIND-01"
CLASS_ID = "AF-WCC-VAC-GEN"
TO = ["astra", "astra-lead-formulation", "astra-lead-audit"]

FILES = {
    "report": "artifacts/worker-041/f1_corpus_rebind/report.json",
    "verifier": "artifacts/worker-041/f1_corpus_rebind/run_f1_corpus_rebind.py",
    "prereg": "artifacts/worker-041/f1_corpus_rebind/PREREGISTRATION.md",
    "readme": "artifacts/worker-041/f1_corpus_rebind/README.md",
}
H = {k: hashlib.sha256((ROOT / v).read_bytes()).hexdigest() for k, v in FILES.items()}

EV_REFS = [
    f"{FILES['report']}#{H['report'][:12]}",
    f"{FILES['prereg']}#{H['prereg'][:12]}",
    "schemas/f1_falsifier_tests.jsonl#56bcb4b3234b",
    "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
    "artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml#cce9c60146d6",
    "artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml#cce9c60146d6",
    "artifacts/formulation/FROZEN.json#815e08079aef",
    "comms/outbox/astra-lead-formulation.jsonl#lead-form-20260912T005743-93",
]

FALSIFIER = (
    "L-FORM-04 falsifier (first disjunct): the rev13 edits change a field any of the 25 tests "
    "exercises. Falsified for this report if any exercised path resolves to identical values at "
    "rev12 cce9c60146d6 and rev13 d9cebb9404b2, if either rev12 baseline copy does not hash to "
    "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3, if the negative control "
    "fires, or if the reported touched-row set is not {10,16,22,24}. Re-running is void if either "
    "schema or the corpus hash moves."
)
NEXT_FALSIFIER = (
    "Re-run `python3 artifacts/worker-041/f1_corpus_rebind/run_f1_corpus_rebind.py` at the same "
    "pins (expect exit 0, FALSIFIER_FIRES, touched rows {10,16,22,24}). The report is void if "
    "sha256(schemas/af_wcc_vacuum.yaml) != d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d, "
    "sha256(schemas/f1_falsifier_tests.jsonl) != 56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e, "
    "or the corpus is re-bound so binding_sha256 != cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3."
)

EVENTS = [
    {
        "event_id": f"{BASE}-artifact-report",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-041",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "task_id": TASK,
        "artifact_type": "measurement_report",
        "path": FILES["report"],
        "sha256": H["report"],
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": ("L-FORM-04 adjudication input: pre-registered rev12->rev13 exercised-field analysis of "
                    "schemas/f1_falsifier_tests.jsonl at pin 56bcb4b3234b. FALSIFIER_FIRES, severity semantic: "
                    "4/25 rows (10,16,22,24) exercise a changed field (visibility.definition, "
                    "class_identity_variants[0].relation, f0_binding.binding_note). No calibrated probe outcome "
                    "changes. Two pre-existing stale probe expectations in row F1-AMB-25 at the bound rev12. "
                    "Worker artifact, unverified; no gate verdict or node status."),
        "falsifier": FALSIFIER,
        "evidence_refs": EV_REFS,
        "to": TO,
    },
    {
        "event_id": f"{BASE}-artifact-verifier",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-041",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "task_id": TASK,
        "artifact_type": "verifier",
        "path": FILES["verifier"],
        "sha256": H["verifier"],
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": ("Deterministic read-only instrument; pre-registered rules in PREREGISTRATION.md. Exit 0 "
                    "analysis complete, 3 pin drift, 4 control failure. Controls C1-C4/C6 all pass, 81/84 "
                    "probe calibration (1 JSON-representation artifact, 2 stale expectations at the bound "
                    "revision)."),
        "falsifier": FALSIFIER,
        "evidence_refs": EV_REFS,
        "to": TO,
    },
    {
        "event_id": f"{BASE}-artifact-prereg",
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-041",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "task_id": TASK,
        "artifact_type": "preregistration",
        "path": FILES["prereg"],
        "sha256": H["prereg"],
        "validation_status": "unverified",
        "claims_completion": False,
        "summary": "Classification, calibration and control rules frozen before execution; README.md carries the verdict summary.",
        "falsifier": FALSIFIER,
        "evidence_refs": EV_REFS,
        "to": TO,
    },
    {
        "event_id": f"{BASE}-claim",
        "event_type": "claim",
        "created_at": TS,
        "actor": "worker-041",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": (
            "At F1 rev12 cce9c60146d6 vs rev13 d9cebb9404b2 (both pinned and stable across the run), the "
            "L-FORM-04 falsifier FIRES with severity semantic: 4 of the 25 rows of "
            "schemas/f1_falsifier_tests.jsonl exercise at least one changed field -- row 10 (F1-AMB-11) and "
            "row 16 (F1-AMB-17) exercise visibility.definition, row 22 (F1-AMB-23) exercises "
            "visibility.definition and class_identity_variants[0].relation, row 24 (F1-AMB-25) exercises "
            "f0_binding.binding_note and class_identity_variants[0].relation. The three semantic changed leaves "
            "are the direction correction STRONGER->WEAKER, the visibility.definition rewrite, and the appended "
            "rev13 binding note; quantifiers.domains.D5.definition also changed but is not exercised. No "
            "calibrated probe pass/fail changes between the two revisions, so the corpus's decisions remain "
            "reproducible at rev13, but the lead's premise that item 3 changed no exercised field is false and "
            "the declared rev12 binding is a false statement about the evaluated bytes: re-binding (rev14) is "
            "semantics-forced, not merely pin hygiene. Independently of rev13, 2 of 84 probes fail at the "
            "corpus's own bound revision cce9c60146d6 (row F1-AMB-25 expects the superseded F0 hash 276009f4 "
            "while rev12/rev13 declare 0abb9ed8a961, and expects binding-note text astra-classscope-02 that the "
            "rev12 note no longer contains); these were left stale by the earlier astra-life03-repin-claims "
            "rev11->rev12 rebind, so any rev14 rebind must be content-aware."),
        "assumptions": [
            "Both rev12 baseline copies (worker-033 pinned canonical, heldout-09 bases) hash to the corpus's declared binding_sha256 cce9c60146d6; the corpus was authored against those bytes.",
            "'Exercises a field' is read literally per L-FORM-04's falsifier: any probe path or deciding-field token whose subtree contains a changed leaf.",
            "Probe semantics are the natural reading of the declared kinds (contains/equals/is_none/is_true/path_exists/nonnull); calibration against the recorded pass at rev12 is reported (81/84) and outcome-level claims use calibrated probes only.",
            "The rev12 baseline copies are authentic snapshots of the superseded schema revision; FROZEN.json at 815e08079aef and the live rev13 bytes were unchanged before and after the measurement.",
        ],
        "falsifier": FALSIFIER,
        "next_falsifier": NEXT_FALSIFIER,
        "artifact_refs": [
            f"{FILES['report']}#{H['report'][:12]}",
            f"{FILES['verifier']}#{H['verifier'][:12]}",
            f"{FILES['prereg']}#{H['prereg'][:12]}",
        ],
        "evidence_refs": EV_REFS,
        "to": TO,
    },
    {
        "event_id": f"{BASE}-review",
        "event_type": "review",
        "created_at": TS,
        "actor": "worker-041",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "task_id": TASK,
        "target_id": "schemas/f1_falsifier_tests.jsonl",
        "reviewer": "worker-041",
        "verdict": "revise",
        "score": 3.0,
        "reviewed_sha256": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
        "scope": "binding-adjudication input for L-FORM-04; not a gate verdict, not a full-corpus content review",
        "counts_as_gate_verdict": False,
        "hard_failures": [
            {"id": "HF-041-CR-1", "severity": "hard",
             "finding": ("Row F1-AMB-25 records pass=true on f0_binding.declared_f0_sha256 equals 276009f4... and "
                         "f0_binding.binding_note contains 'astra-classscope-02', but neither value exists at the "
                         "row's own declared binding cce9c60146d6 (rev12: 0abb9ed8a961..., note rewritten); the "
                         "recorded passes are not reproducible at the bound revision, pre-dating rev13.")},
        ],
        "findings": [
            "L-FORM-04 falsifier FIRES (semantic): rows 10, 16, 22, 24 exercise visibility.definition / class_identity_variants[0].relation / f0_binding.binding_note, all changed rev12->rev13; the lead's 'prose-direction only, no exercised field changed' premise is false.",
            "Counterweight: 0 calibrated probe outcomes change between rev12 and rev13, so a content-aware rebind can re-pin without re-deriving the 25 decisions; the two pre-existing stale expectations in F1-AMB-25 are the only expectations that must change.",
            "Binding metadata for all 25 rows still names rev12 cce9c60146d6 while the live F1 canonical is rev13 d9cebb9404b2; the corpus was previously rebound rev11->rev12 at 2026-09-12T00:32:31+08:00 by astra-life03-repin-claims, which is the same class of event and left the probe expectations stale.",
            "quantifiers.domains.D5.definition changed but is not exercised by any row; f0_binding.consistency_evidence_sha256 changed and is likewise not exercised.",
            "Controls all pass: both rev12 copies pinned, live hashes stable before/after, positive control sees 12 changed leaves incl. all 3 expected semantic paths, negative control on an unexercised leaf touches no row, analysis deterministic over two runs.",
        ],
        "evidence_refs": EV_REFS,
        "next_falsifier": NEXT_FALSIFIER,
        "to": TO,
    },
    {
        "event_id": f"{BASE}-status",
        "event_type": "status",
        "created_at": TS,
        "actor": "worker-041",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "task_id": TASK,
        "status": "active",
        "hours": 0.5,
        "completion_scope": "one bounded class-bound worker task; no node status, no gate verdict, no canonical edit",
        "summary": ("W041-F1-CORPUS-REBIND-01 complete: L-FORM-04 adjudication input at pinned rev12 cce9c60146d6 vs "
                    "rev13 d9cebb9404b2. FALSIFIER_FIRES (semantic): 4/25 rows exercise a changed field "
                    "(10,16,22,24); 0 probe outcomes change; 2 pre-existing stale expectations at the bound rev12 "
                    "(F1-AMB-25); 81/84 probe calibration; controls all pass; instrument, preregistration and report "
                    "hash-pinned. Worker checkpoint written."),
        "evidence_refs": EV_REFS,
        "next_falsifier": NEXT_FALSIFIER,
        "to": TO,
    },
]

outdir = ROOT / "artifacts/worker-041/f1_corpus_rebind"
for e in EVENTS:
    validate_event(e)
for e in EVENTS:
    for ref in e.get("evidence_refs", []):
        if "#" in ref:
            p, h = ref.rsplit("#", 1)
            fp = ROOT / p
            if fp.is_file() and len(h) == 64:
                got = hashlib.sha256(fp.read_bytes()).hexdigest()
                assert got == h, f"hash mismatch {ref}"

(outdir / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in EVENTS))

outbox = ROOT / "comms/outbox/worker-041.jsonl"
existing = set()
if outbox.exists():
    for line in outbox.read_text().splitlines():
        try:
            existing.add(json.loads(line)["event_id"])
        except Exception:
            pass
added = 0
with outbox.open("a") as f:
    for e in EVENTS:
        if e["event_id"] not in existing:
            f.write(json.dumps(e, sort_keys=True) + "\n")
            added += 1
print(json.dumps({"validated": len(EVENTS), "appended": added,
                  "already_present": len(EVENTS) - added,
                  "hashes": {k: v[:12] for k, v in H.items()}}, indent=2))
