#!/usr/bin/env python3
"""Emit the F13-G-CLASSBIND-REV29-R03 event set to comms/outbox/deepseek-flash-13.jsonl.

Appends artifact / claim / gate-proposal / status events, each hash-bound to the files on disk
at emit time.  Every event is validated against research_map/schemas.py before it is written,
and the emitter re-measures the canonical pins so a mid-flight republication is caught here
rather than published as a stale verdict.  Idempotence is intentionally NOT provided: the outbox
is an append-only stream and this worker instance emits its checkpoint exactly once.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/deepseek-flash-13.jsonl"

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

PINS = {
    "F1": ("artifacts/formulation/schemas/af_wcc_vacuum.yaml", "d9cebb9404b2e79e"),
    "F2a": ("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd308bd"),
    "F2b": ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe7f86"),
    "FROZEN": ("artifacts/formulation/FROZEN.json", "815e08079aefbc16"),
    "spec": ("artifacts/formulation/rule_spec.json", "40f9bb9e657b2c6b"),
    "e1a": ("artifacts/worker-064/r03_cause/patch_candidates/wcc_candidate_E1a.yaml",
            "2f51ace6ef745976"),
}


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / rel, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(rel)[:16]}"


drift = [k for k, (rel, prefix) in PINS.items() if sha(rel)[:16] != prefix]
if drift:
    raise SystemExit(f"PIN DRIFT before emit: {drift}; re-run the gate and rebuild the record")

TS = datetime.now().astimezone().isoformat(timespec="seconds")
PREFIX = "f13-r29r03-" + datetime.now().strftime("%Y%m%dT%H%M%S")
FILES = {
    "gate": "artifacts/flash-13/form_gate/check_class_schema.py",
    "report_11": "artifacts/flash-13/form_gate/gate_report_rev29.json",
    "report_12": "artifacts/flash-13/form_gate/gate_report_rev29_r3.json",
    "suite": "artifacts/flash-13/form_gate/fixture_suite_report.json",
    "m25": "artifacts/flash-13/form_gate/fixtures/m25_wcc_binder_unused.yaml",
    "manifest": "artifacts/flash-13/form_gate/fixtures/manifest.json",
    "e1a": "artifacts/flash-13/form_gate/e1a_crosscheck.json",
    "recheck": "artifacts/flash-13/form_gate/canonical_recheck_rev29.json",
    "builder": "artifacts/flash-13/form_gate/make_recheck_rev29.py",
    "addm25": "artifacts/flash-13/form_gate/add_m25_fixture.py",
    "makefixtures": "artifacts/flash-13/form_gate/make_fixtures.py",
    "readme": "artifacts/flash-13/form_gate/README.md",
}
H = {k: sha(v) for k, v in FILES.items()}
R = {k: f"{v}#{H[k][:16]}" for k, v in FILES.items()}
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
CANON_REFS = [ref(p) for p, _ in PINS.values()]
CORE = [R["recheck"], R["report_12"], R["report_11"], R["gate"], R["suite"]]

events: list[dict] = [
    {"event_id": f"{PREFIX}-art-gate", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_implementation", "class_id": CLASSES, "path": FILES["gate"],
     "sha256": H["gate"], "validation_status": "unverified",
     "supersedes": {"path": FILES["gate"],
                    "sha256": "ad7d120b84499a92abf46302d71011fc2da7574ceab3b0d870494ef562ca22e1"},
     "evidence_refs": [R["gate"], R["recheck"], R["report_12"]],
     "note": ("FORM-GATE-01 revision 1.2: R03 now enforces the published 'formal is a single "
              "sentence using those binders' require (whitespace-normalised literal-usage test, "
              "disclosed as literal). All other rules unchanged; conforming fixtures unchanged.")},
    {"event_id": f"{PREFIX}-art-report11", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_report_pre_hardening", "class_id": CLASSES,
     "path": FILES["report_11"], "sha256": H["report_11"], "validation_status": "unverified",
     "evidence_refs": [R["report_11"], R["gate"], ref("artifacts/formulation/FROZEN.json")],
     "note": ("Gate 1.1 canonical run at the rev13 bytes: all three pass. Kept as the "
              "pre-hardening column of the R03 bisect (same bytes, different gate revision).")},
    {"event_id": f"{PREFIX}-art-report12", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_report", "class_id": CLASSES, "path": FILES["report_12"],
     "sha256": H["report_12"], "validation_status": "unverified",
     "evidence_refs": [R["report_12"], R["gate"], R["report_11"], ref("artifacts/formulation/FROZEN.json")],
     "note": ("Gate 1.2 canonical run at byte-identical rev13 bytes: AF-WCC-VAC-GEN fails R03 "
              "(ordered[5] binder '(q,t0)' absent from quantifiers.formal); C2 and C0 pass.")},
    {"event_id": f"{PREFIX}-art-m25", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "fixture_mutant", "class_id": "AF-WCC-VAC-GEN", "path": FILES["m25"],
     "sha256": H["m25"], "validation_status": "unverified",
     "evidence_refs": [R["m25"], R["suite"], R["manifest"]],
     "note": ("New single-rule R03 mutant: differs from conforming_wcc.yaml only in "
              "quantifiers.ordered[2].binder 'p' -> '(p,t0)'; mirrors the canonical rev13 defect.")},
    {"event_id": f"{PREFIX}-art-manifest", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "fixture_manifest", "class_id": CLASSES, "path": FILES["manifest"],
     "sha256": H["manifest"], "validation_status": "unverified",
     "evidence_refs": [R["manifest"], R["m25"], R["suite"]],
     "note": "Corpus now 3 positives / 25 single-expectation mutants / 6 rephrased; m25 entry added."},
    {"event_id": f"{PREFIX}-art-suite", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_control_report", "class_id": CLASSES, "path": FILES["suite"],
     "sha256": H["suite"], "validation_status": "unverified",
     "evidence_refs": [R["suite"], R["gate"], R["manifest"], R["m25"]],
     "note": ("Suite exit 0 under gate 1.2: 3/3 conforming pass; 25/25 mutants rejected with the "
              "expected rule (17 single-keyed; R06 cross-talk on six SCC mutants); 5/6 rephrased "
              "caught, 1 documented blind spot; exit 3 on absent canonical.")},
    {"event_id": f"{PREFIX}-art-e1a", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "crosscheck_evidence", "class_id": "AF-WCC-VAC-GEN", "path": FILES["e1a"],
     "sha256": H["e1a"], "validation_status": "unverified",
     "evidence_refs": [R["e1a"], ref(PINS["e1a"][0]), R["gate"]],
     "note": ("External worker-064 E1a one-clause repair candidate 2f51ace6ef74 passes gate 1.2 "
              "R01-R16 (R16 skipped for WCC): the corrected R03 is repairable, not a blanket reject.")},
    {"event_id": f"{PREFIX}-art-recheck", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "binding_record", "class_id": CLASSES, "path": FILES["recheck"],
     "sha256": H["recheck"], "validation_status": "unverified",
     "evidence_refs": CORE + [R["e1a"], R["manifest"]] + CANON_REFS,
     "note": ("Binds FROZEN rev29, spec, both gate revisions, canonical bytes, mirrors, controls "
              "and the E1a cross-check into one record; drift_check all false at build.")},
    {"event_id": f"{PREFIX}-art-builder", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_tooling", "class_id": CLASSES, "path": FILES["builder"],
     "sha256": H["builder"], "validation_status": "unverified",
     "evidence_refs": [R["builder"], R["recheck"]],
     "note": "Reproducible builder for canonical_recheck_rev29.json; re-measures inputs, records drift."},
    {"event_id": f"{PREFIX}-art-addm25", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_tooling", "class_id": "AF-WCC-VAC-GEN", "path": FILES["addm25"],
     "sha256": H["addm25"], "validation_status": "unverified",
     "evidence_refs": [R["addm25"], R["m25"], R["makefixtures"]],
     "note": ("Writes exactly the m25 mutant + manifest entry; deliberately does not re-run "
              "make_fixtures.py wholesale (its SCC positives carry a manual post-generation "
              "alignment) - documented non-idempotency of the generator.")},
    {"event_id": f"{PREFIX}-art-makefixtures", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_tooling", "class_id": "AF-WCC-VAC-GEN", "path": FILES["makefixtures"],
     "sha256": H["makefixtures"], "validation_status": "unverified",
     "evidence_refs": [R["makefixtures"], R["addm25"]],
     "note": "m25 mutation added to the in-code corpus definition (documentation of the mutant's construction)."},
    {"event_id": f"{PREFIX}-art-readme", "event_type": "artifact", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND",
     "artifact_type": "gate_documentation", "class_id": CLASSES, "path": FILES["readme"],
     "sha256": H["readme"], "validation_status": "unverified",
     "evidence_refs": [R["readme"], R["recheck"], R["suite"]],
     "note": "Revision 1.2 section: R03 change, measured bisect, controls, cross-checks, F-GATE-6."},
    {"event_id": f"{PREFIX}-claim", "event_type": "claim", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "gate": "G-CLASSBIND", "class_id": CLASSES,
     "conclusion_type": "stability_result",
     "statement": (
         "At the rev13 / FROZEN rev29 bytes (AF-WCC-VAC-GEN d9cebb9404b2, AF-SCC-C2-VAC-GEN "
         "e9a27996dfd3, AF-SCC-C0-VAC-GEN b2ab6acb2bbe, FROZEN 815e08079aef, spec 40f9bb9e657b) "
         "the independent FORM-GATE-01 gate revision 1.2 (5522541bde4e) fails canonical WCC on "
         "exactly R03: quantifiers.ordered[5] declares the tuple binder '(q,t0)' while "
         "quantifiers.formal renders the same quantifier variable-wise ('not exists q in I+ and "
         "t0 in [0,T) with ...'), and the published R03 require is that the formal sentence uses "
         "those binders. C2 and C0 pass R01-R16. The byte-identical canonical files passed under "
         "gate 1.1 (ad7d120b8449), whose R03 checked only that some quantifier occurs, so gate "
         "1.1 under-detected the published require. This is an independent second-implementation "
         "reproduction of the R03 rejection measured by the adopted semantic auditor "
         "(worker-064 W064-R03-CAUSE-01, auditor c79d8ab8440a; also worker-080 Probe B and "
         "worker-16 W16-R03-ADJ-01). Fixture controls stay green under 1.2 (3/3 conforming pass, "
         "25/25 mutants rejected with the expected rule - new m25 keyed to R03 - exit 3 on absent "
         "canonical, exit 0 conforming), and worker-064's E1a one-clause repair candidate "
         "2f51ace6ef74 passes R01-R16 under the corrected gate, so the failure is repairable by "
         "rendering the declared binder and is a formal-rendering defect, not a mathematical "
         "verdict against the rev12 repair."),
     "assumptions": [
         "the R03 addition is a whitespace-normalised literal-usage test, disclosed as literal; "
         "alpha-equivalent re-renderings of a declared binder would be flagged and are for the "
         "rule owner to adjudicate, not for this worker to excuse",
         "FROZEN rev29 pins the three canonical hashes measured here and the mirrors are "
         "byte-identical; any republication voids the verdict and requires a re-run",
         "scope is structural R01-R16 conformance only: no mathematical truth, non-vacuity, "
         "citation adjudication, node completion or gate verdict is claimed, and no canonical "
         "byte was modified by this worker",
         "the E1a candidate is an external worker-064 artifact used read-only as a control; it is "
         "not endorsed as the only repair and is not in the FROZEN manifest"],
     "falsifier": (
         "The rule owner certifies the variable-wise WCC rendering as satisfying R03 (then the "
         "literal test is too strict and must be relaxed by adjudication), or an alpha-renamed "
         "schema certified conforming is rejected by it, or any canonical file byte changes, or "
         "gate 1.1's R03 is shown to have checked binder usage elsewhere."),
     "evidence_refs": CORE + [R["e1a"], R["manifest"], R["builder"], R["readme"]] + CANON_REFS},
    {"event_id": f"{PREFIX}-gate-proposal", "event_type": "gate", "created_at": TS,
     "actor": "deepseek-flash-13", "gate_id": "G-CLASSBIND",
     "scope": "F1/F2a/F2b rev13 canonical schemas at FROZEN rev29 (R03 literal-usage reading)",
     "verdict": "pending",
     "criteria": (
         "PROPOSAL ONLY, not set by this worker. Measured: gate 1.2 canonical verdict fail - WCC "
         "R03 only; C2/C0 pass; fixture controls green; evidence hash-bound. Requested owner "
         "adjudication between (a) one-clause formal-sentence repair (worker-064 E1a/E1b; changes "
         "the F1 hash and requires F1 re-review) and (b) ratifying the variable-wise rendering as "
         "R03-conforming (relax the literal test; keeps frozen bytes). Until then G-CLASSBIND "
         "cannot be proposed as pass at these bytes under this gate."),
     "evidence_refs": [R["recheck"], R["report_12"], R["report_11"], R["suite"], R["e1a"]]},
    {"event_id": f"{PREFIX}-status", "event_type": "status", "created_at": TS,
     "actor": "deepseek-flash-13", "node_id": "F1", "status": "active", "hours": 1.0,
     "summary": (
         "CHECKPOINT / bounded worker instance closing. Took ONE class-bound task "
         "(F1 / AF-WCC-VAC-GEN + F2a/F2b, G-CLASSBIND): frozen-hash re-run of the independent "
         "FORM-GATE-01 gate at rev13 / FROZEN rev29, which exposed and fixed an R03 "
         "under-detection. Result: gate 1.1 passed all three at the rev13 bytes; gate 1.2 fails "
         "WCC on R03 (declared binder '(q,t0)' unused in quantifiers.formal) while C2/C0 pass at "
         "byte-identical files; fixture suite 3/3 positives + 25/25 mutants (new m25 keyed R03); "
         "worker-064 E1a repair candidate passes R01-R16, so the defect is repairable. This "
         "independently corroborates the live R03 blocker (w064/w080/w16). No node completion, no "
         "gate self-pass, no canonical modification."),
     "evidence_refs": CORE + [R["e1a"], R["readme"], R["manifest"]] + CANON_REFS,
     "next_falsifier": (
         "Rule-owner adjudication of R03 literal vs variable-wise composite binders; after a WCC "
         "repair or rule relaxation, re-run this gate at the new hashes; a repaired WCC that "
         "still leaves the declared binder unused must keep failing R03.")},
]

with open(OUTBOX, "a") as fh:
    for ev in events:
        validate_event(ev)
        fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")

print(f"appended {len(events)} events to {OUTBOX.relative_to(ROOT)}")
for ev in events:
    print(" ", ev["event_id"])
