#!/usr/bin/env python3
"""Write the flash-13 rev1.3 checkpoint JSON (hashes measured at write time)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = REPO / "artifacts/flash-13/form_gate"
OUT = REPO / "runtime/state/flash-13_checkpoint_formgate_rev29_r03_semantic.json"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
TAG = "f13-r03sem-20260912T011448"


def sha(rel):
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


ART = [
    "artifacts/flash-13/form_gate/check_class_schema.py",
    "artifacts/flash-13/form_gate/r03_readings_rev29.json",
    "artifacts/flash-13/form_gate/canonical_recheck_rev29_v13.json",
    "artifacts/flash-13/form_gate/gate_report_rev29_r3_semantic.json",
    "artifacts/flash-13/form_gate/fixture_suite_report.json",
    "artifacts/flash-13/form_gate/gate_report.json",
    "artifacts/flash-13/form_gate/fixtures_r03/manifest.json",
    "artifacts/flash-13/form_gate/fixtures_v13/manifest.json",
    "artifacts/flash-13/form_gate/make_r03_controls.py",
    "artifacts/flash-13/form_gate/make_fixtures_v13.py",
    "artifacts/flash-13/form_gate/r03_readings_audit.py",
    "artifacts/flash-13/form_gate/emit_outbox_r03_semantic.py",
    "artifacts/flash-13/form_gate/README.md",
    "artifacts/flash-13/form_gate/legacy_v12/fixture_suite_report.v12_r03.json",
    "artifacts/flash-13/form_gate/legacy_v12/canonical_recheck_rev29.v12_r03.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/rule_spec.json",
]

readings = json.loads((HERE / "r03_readings_rev29.json").read_text())
cp = {
    "checkpoint_id": "flash-13-formgate-rev29-r03-semantic",
    "actor": "deepseek-flash-13",
    "instance": "worker-013-20260912T010558-968807 (bounded execution worker, one class-bound task)",
    "created_at": NOW,
    "task_id": "F13-G-CLASSBIND-REV29-R03-SEMANTIC",
    "assignment_source": ("standing assign-FORM-GATE-01-20260911T2331 (lead-formulation, "
                          "G-CLASSBIND, F1/F2a/F2b); no newer inbox card existed for "
                          "deepseek-flash-13 (inbox last message 2026-09-11T23:40:52)"),
    "node_id": "F1", "gate": "G-CLASSBIND",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "status": "active", "hours": 1.2,
    "verdict": {
        "gate_1_3_semantic": "pass at the rev13 / FROZEN rev29 bytes (all three canonical schemas, all 16 rules; R16 skipped for WCC)",
        "gate_1_3_literal_reading": "fail - AF-WCC-VAC-GEN R03 only, on declared binder '(q,t0)'; C2 and C0 pass",
        "self_refutation": ("the rev1.2 F-GATE-6 'canonical WCC fails R03' result is withdrawn: it "
                            "was a false positive of the literal-substring proxy, not a defect of "
                            "the canonical schema"),
        "s_strictly_stronger": ("4 controls accepted by the literal reading are rejected by the "
                                "semantic reading: c01 kind reorder, c02 clause deleted, c09 extra "
                                "body keyword, c10 variable only before its quantifier"),
        "corpus_defect": ("all 34 legacy fixtures declared ordered[2].kind='exists' against their "
                          "own sentence 'not exists p'; repaired kind-token-only into fixtures_v13; "
                          "suite metrics identical to rev1.2"),
        "proposal": ("G-CLASSBIND verdict left pending; proposal favours pass under S with the R03 "
                     "reading adjudication reserved to the rule owner (astra-life05-verify-gform-r3)"),
        "m25_still_caught": True,
        "readings_assertions": readings["assertions"],
    },
    "canonical_pins_measured": {rel: sha(rel) for rel in ART if rel.startswith("artifacts/formulation/")},
    "artifacts": {rel: sha(rel) for rel in ART},
    "outbox_event_ids": [f"{TAG}-{s}" for s in (
        "art-checkclassschema", "art-r03readingsrev29", "art-canonicalrecheckrev29v13",
        "art-gatereportrev29r3semanti", "art-fixturesuitereport", "art-gatereport",
        "art-fixturesr03-manifest", "art-fixturesv13-manifest", "art-maker03controls",
        "art-makefixturesv13", "art-r03readingsaudit", "art-README",
        "art-legacyv12-fixturesuitere", "claim", "gate-proposal", "status")],
    "stream_state": {"accepted": 16, "rejected": 0,
                     "stream": "research_map/events.jsonl", "tag": TAG},
    "falsifier": ("a certified-conforming schema S rejects; or a schema S accepts whose formal "
                  "sentence does not realise its declared quantifier structure; or any canonical / "
                  "FROZEN byte change; or owner rules the literal reading normative (then the "
                  "worker-064 E1a/E1b repair is required and S also accepts it)"),
    "next_falsifier": ("independent reviewer re-runs gate 1.3 at the frozen bytes and attacks the "
                       "S criterion with an adversarial schema; controller/lead adjudicates the "
                       "reading and the gate proposal"),
    "authority_note": ("no node completion, no gate verdict, no validation_status=passed, no "
                       "canonical byte modified; worker events are proposals only"),
    "numerics_lock": ("untouched - no N0/N1 numerics work in this task; N0 stays with its own "
                      "verdict path"),
    "excluded_actions": ["no writes under artifacts/formulation/", "no writes to research_map/",
                         "no gate verdict", "no node status change"],
}
OUT.write_text(json.dumps(cp, indent=2, sort_keys=True) + "\n")
print("wrote", OUT.relative_to(REPO))
print("artifacts hashed:", len(cp["artifacts"]), "| assertions pass:",
      all(readings["assertions"].values()))
