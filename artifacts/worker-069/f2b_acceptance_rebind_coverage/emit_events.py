#!/usr/bin/env python3
"""Fail-closed outbox emitter for W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01.

Validates every event against research_map/schemas.validate_event, re-hashes every referenced
artifact on disk, and appends to comms/outbox/worker-069.jsonl (skipping event_ids already
present there or already ingested). Run: python3 emit_events.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TAG = "w069-arb-20260912T012600"
OUTBOX = ROOT / "comms/outbox/worker-069.jsonl"
SEEN = ROOT / "runtime/state/ingested_ids.json"


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def art(path: str) -> str:
    return f"{path}#{sha(path)[:12]}"


R = "artifacts/worker-069/f2b_acceptance_rebind_coverage"
REPORT = f"{R}/report.json"
ADDENDUM = f"{R}/addendum_cause_decomposition.json"
CHECKER = f"{R}/check_rebind_coverage.py"
ADD_CHECKER = f"{R}/addendum_cause_decomposition.py"
PREREG = f"{R}/PREREGISTRATION.json"
README = f"{R}/README.md"
CPT = f"{R}/CHECKPOINT.json"
RCPT = "runtime/state/w069_f2b_acceptance_rebind_checkpoint_20260912T012500.json"

EV = [
    {
        "event_id": f"{TAG}-status-claim",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "No assignment card exists for worker-069 (pass-08 open assignments are lead-owned or worker-006). "
            "Took ONE bounded class-bound task: W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01 = pre-registered sandbox "
            "sufficiency test of the authorized acceptance-corpus rebind (REC-36 item 7 / CF-32 i) at FROZEN rev29 "
            "815e08079aef / rev13 pins. Headline: the rebind CLEARS the preflight failure (regenerated fixture binds "
            "live C0 b2ab6acb, byte-deterministic, 31/31 union catches, 0 union escapes) but ACCEPTANCE still exits 1 "
            "solely because stage-B R03 rejects the untouched frozen F1 d9cebb9404b2 (REC-41). No canonical write."),
        "evidence_refs": [art(PREREG), art(REPORT), art(ADDENDUM),
                          "artifacts/formulation/FROZEN.json#815e08079aef",
                          "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"],
        "next_falsifier": ("Re-run check_rebind_coverage.py on byte-identical pinned inputs; falsified if the baseline "
                           "no longer exits 3, the regenerated fixture does not bind live C0 or is not deterministic, "
                           "any predicate flips, a recorded catch is an escape, or any pin drifts."),
    },
    {
        "event_id": f"{TAG}-artifact-prereg",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "artifact_type": "preregistration",
        "path": PREREG,
        "sha256": sha(PREREG),
        "validation_status": "unverified",
        "summary": "Pins (16 inputs), predicates P0-P7, controls CTL-1..CTL-8 and the decision rule fixed before the run.",
        "evidence_refs": [art(REPORT)],
    },
    {
        "event_id": f"{TAG}-artifact-checker",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "artifact_type": "independent_checker",
        "path": CHECKER,
        "sha256": sha(CHECKER),
        "validation_status": "unverified",
        "summary": ("Independent stdlib+PyYAML instrument: 16-input pin guard, 5 sandboxes, pinned-tool execution only "
                    "inside sandboxes, byte-deterministic report (double-run digest equal), live tree read-only."),
        "evidence_refs": [art(REPORT), art(PREREG)],
    },
    {
        "event_id": f"{TAG}-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "artifact_type": "verification_report",
        "path": REPORT,
        "sha256": sha(REPORT),
        "validation_status": "unverified",
        "summary": ("Pre-registered verdict REBIND_INSUFFICIENT_AT_MEASURED_BASE (P4 required exit 0; 0 union escapes). "
                    "Baseline reproduces live exit 3 PREFLIGHT FAIL; rebind deterministic at live C0; post-rebind run exit 1 "
                    "with mutants 31/31, union 31/31, controls 2/2, F1 stage-B fail. run_digest e31af21fc62a."),
        "evidence_refs": [art(ADDENDUM), "artifacts/formulation/evidence/semantic_escape_rebased.json#7e44de0e3906",
                          "artifacts/formulation/evidence/acceptance_pipeline_report.json#9b7d6c8208d3"],
    },
    {
        "event_id": f"{TAG}-artifact-addendum-checker",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "artifact_type": "independent_checker_addendum",
        "path": ADD_CHECKER,
        "sha256": sha(ADD_CHECKER),
        "validation_status": "unverified",
        "summary": "Cause-decomposition instrument: per-canonical stage rows, stage-B non-vacuity controls, refined census.",
        "evidence_refs": [art(ADDENDUM)],
    },
    {
        "event_id": f"{TAG}-artifact-addendum",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "artifact_type": "addendum_measurement",
        "path": ADDENDUM,
        "sha256": sha(ADDENDUM),
        "validation_status": "unverified",
        "summary": ("Cause decomposition: structural stages pass on all three canonical schemas; stage-B rejects only "
                    "af_wcc_vacuum.yaml (F1 d9cebb9404b2) with failed_rules ['R03']; F2a/F2b accepted; stage-B non-vacuous "
                    "(rejects a pinned caught mutant and mangled copies). A6 conditional prediction pre-registered. "
                    "run_digest 5288539f6d69."),
        "evidence_refs": [art(REPORT), "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                          "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a"],
    },
    {
        "event_id": f"{TAG}-artifact-readme",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "artifact_type": "report_note",
        "path": README,
        "sha256": sha(README),
        "validation_status": "unverified",
        "summary": "Human-readable verdict table, controls, governance findings, binding census, falsifier, non-claims.",
        "evidence_refs": [art(REPORT), art(ADDENDUM)],
    },
    {
        "event_id": f"{TAG}-artifact-checkpoint",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "artifact_type": "checkpoint",
        "path": CPT,
        "sha256": sha(CPT),
        "validation_status": "unverified",
        "summary": "Bounded-lifecycle checkpoint: pins, artifact hashes, sandbox listing digests, verdict, next falsifier.",
        "evidence_refs": [art(REPORT), art(ADDENDUM), art(RCPT)],
    },
    {
        "event_id": f"{TAG}-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-tooling measurement (not a mathematics claim), at FROZEN rev29 815e08079aef / F1 d9cebb9404b2 "
            "/ F2a e9a27996dfd3 / F2b b2ab6acb2bbe, executed only in sandboxes: (1) the pinned acceptance corpus fixture "
            "7e44de0e binds base 1bb78ce9 and run_acceptance.py fails preflight with exit 3; (2) regenerating the corpus "
            "with the pinned generator c6e4f9cc at live C0 b2ab6acb produces a byte-deterministic fixture (identical across "
            "two independent sandboxes) with 31 mutants, 1 unparsed, 0 control false positives, and clears preflight; "
            "(3) the post-rebind acceptance run exits 1 with mutants 31/31 and union_caught 31/31 (0 union escapes) and "
            "controls 2/2, failing only because stage-B rejects the untouched frozen F1 with failed_rules ['R03'] "
            "(REC-41); (4) the generated rebased_fixtures directory (33 files) is load-bearing but covered by no hash in "
            "FROZEN.files; the stage-B auditor and fixture manifest are bound only transitively inside the pinned fixture. "
            "Therefore authorized item (7) alone cannot reach ACCEPTANCE: PASS at these pins; it must land together with "
            "the REC-41 stage-B fix and a re-pin that covers the generated fixture directory."),
        "assumptions": [
            "all inputs read at the pinned hashes recorded in report.json; no canonical path was executed or written",
            "the sandbox is faithful: pinned tool bytes are copied unchanged and resolve ROOT inside the sandbox",
            "the two-stage acceptance pipeline (check_class_schema.py + spec_conformance_audit.py behind run_acceptance.py) "
            "is the project's G-FORM acceptance criterion, as recorded in the worker-069 F2a/F2b verdicts and CF-32",
            "the regenerated corpus is deterministic for these pinned tool bytes; a future tool or C0 byte move re-opens it",
        ],
        "falsifier": (
            "Re-run check_rebind_coverage.py on byte-identical pinned inputs. Falsified if (a) the baseline no longer exits 3 "
            "or names different hashes; (b) the regenerated fixture does not bind live C0 or is not byte-deterministic across "
            "the two sandboxes; (c) any recorded predicate verdict flips on the same bytes; (d) ACCEPTANCE: PASS is reached "
            "but a mutant recorded as caught is in fact an escape; or (e) any pinned input differs at re-measurement. The A6 "
            "conditional is falsified if a post-stage-B-fix sandbox run still exits non-zero."),
        "evidence_refs": [art(REPORT), art(PREREG), art(ADDENDUM), art(CHECKER), art(RCPT),
                          "artifacts/formulation/FROZEN.json#815e08079aef",
                          "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                          "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                          "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a"],
        "artifact_refs": [art(REPORT), art(ADDENDUM), art(CHECKER), art(ADD_CHECKER)],
    },
    {
        "event_id": f"{TAG}-review",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "target_id": "REC-36-item7-acceptance-corpus-rebind",
        "target_artifact": "artifacts/formulation/evidence/semantic_escape_rebased.json",
        "reviewed_sha256": "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292",
        "reviewer": "worker-069",
        "verdict": "revise",
        "score": 3.5,
        "hard_failures": [
            {"id": "HF-069ARB-1", "label": "pinned acceptance report cannot be regenerated at the live pins",
             "severity": "blocking-for-clean-accept",
             "detail": ("artifacts/formulation/evidence/acceptance_pipeline_report.json 9b7d6c82 records PASS / union 31/31 but "
                        "was generated before the rev13 F1 byte move; run_acceptance.py exits 3 on the pinned corpus "
                        "(base 1bb78ce9 != live C0 b2ab6acb), so the pinned report is not evidence at the current pins (CF-32 i)."),
             "evidence_refs": [art(REPORT), "artifacts/formulation/evidence/semantic_escape_rebased.json#7e44de0e3906",
                               "artifacts/formulation/evidence/acceptance_pipeline_report.json#9b7d6c8208d3"],
             "falsifier": "regenerate the corpus and the acceptance report at the live C0 and re-pin both; the finding is void once the pinned report reproduces from live bytes"},
            {"id": "HF-069ARB-2", "label": "the authorized rebind alone is not sufficient for ACCEPTANCE: PASS",
             "severity": "blocking-for-clean-accept",
             "detail": ("after a byte-deterministic rebind at live C0 the run still exits 1: stage-B rejects the untouched frozen "
                        "F1 d9cebb9404b2 with failed_rules ['R03'] (REC-41 / astra-life08-stageb-r03). Item (7) and the stage-B fix "
                        "must land together and the pipeline must be re-run; the free-standing claim that rebinding closes CF-32 is false."),
             "evidence_refs": [art(ADDENDUM), "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                               "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a"],
             "falsifier": "a post-rebind sandbox run reaching ACCEPTANCE: PASS with the frozen F1 bytes unchanged and R03 still failing, or evidence that the F1 stage-B failure is caused by the corpus"},
            {"id": "HF-069ARB-3", "label": "generated acceptance fixtures are unpinned but load-bearing",
             "severity": "advisory-gate-hygiene",
             "detail": ("artifacts/formulation/evidence/rebased_fixtures/ (33 files, read by run_acceptance.py at run time) is covered "
                        "by no hash in FROZEN.files; deleting one mutant moves mutants.total 31 -> 30 with no pin change (CTL-6). "
                        "The rebind should re-pin the directory listing hash or the fixture must carry the per-mutant hashes."),
             "evidence_refs": [art(REPORT), "artifacts/formulation/FROZEN.json#815e08079aef"],
             "falsifier": "the rebind publishes a pin covering the generated directory contents (or the checker verifies per-mutant hashes from the fixture), making the finding void"},
        ],
        "findings": [
            "REBIND CLEARS PREFLIGHT: regenerated fixture binds live C0 b2ab6acb, 31 mutants, 1 unparsed, 0 control false positives, 33 files, byte-identical across two independent sandboxes.",
            "CORPUS CONTENT CLEAN AT THE PINS: post-rebind mutants 31/31 union-caught (structural 30, semantic 11), 0 union escapes, controls 2/2, consistent with the pinned fixture's generation-time numbers.",
            "REMAINING BLOCKER IS NOT THE CORPUS: the only failing canonical row is F1 af_wcc_vacuum.yaml at stage-B R03; all three canonical schemas pass the structural stage; F2a/F2b pass both stages.",
            "STAGE-B NON-VACUOUS: accepts frozen F2a/F2b, rejects a pinned mutant it is recorded as catching (struct01 R06/R13), rejects mangled F1/F2a copies.",
            "GOVERNANCE: generated fixtures directory unpinned (load-bearing); stage-B auditor + fixture manifest bound only transitively inside the pinned fixture; FROZEN.json is the self-referential pin root; schemas/af_scc_c0_vacuum.yaml.sha256 is a stale unbound sidecar that no pipeline tool reads.",
            "CONTROLS 8/8 registered: 7 clean; CTL-6's fail-closed discrimination is masked at these pins by the independent F1/R03 blocker, while its load-bearing observation (31 -> 30) holds.",
            "A6 (pre-registered prediction): adopted rebind + adopted stage-B fix that makes frozen F1 pass without degrading other rules => ACCEPTANCE: PASS, canonical 3/3, controls 2/2, mutants 31/31.",
        ],
        "non_claims": ["worker verdict only; no gate verdict, node status or validation promotion",
                       "no canonical write, repair or re-pin; sandbox execution only",
                       "REC-41 attribution is the measured failing rule, not an adjudication of worker-006's fix"],
    },
    {
        "event_id": f"{TAG}-blocker",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "description": ("The acceptance criterion cannot reach PASS at the measured pins by the authorized corpus rebind alone. "
                        "Measured: rebind clears preflight at live C0 (byte-deterministic, 31/31 union catches, 0 escapes, controls "
                        "2/2) but run_acceptance.py still exits 1 because stage-B rejects the untouched frozen F1 d9cebb9404b2 with "
                        "R03 (REC-41). Additionally the regenerated fixture directory is load-bearing yet covered by no FROZEN pin, "
                        "so a PASS would not be bound to the corpus contents."),
        "needed_to_unblock": ("land REC-36 item (7) and the REC-41 stage-B R03 fix in the same rev14 window, re-run the pipeline at "
                              "the new pins, and make the freeze cover the generated rebased_fixtures contents (listing hash or "
                              "per-mutant hashes) together with the fixture; then astra-life05-verify-gform-r3 can cite a reproducible "
                              "post-fix acceptance report."),
        "evidence_refs": [art(REPORT), art(ADDENDUM), "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                          "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
                          "artifacts/formulation/FROZEN.json#815e08079aef"],
        "falsifier": "a post-rebind sandbox run that reaches ACCEPTANCE: PASS on the unchanged frozen F1 bytes, or a pin that covers the generated fixture directory at the measured pins",
    },
    {
        "event_id": f"{TAG}-status-complete",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-069",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
        "gate": "G-FORM",
        "status": "active",
        "hours": 1.1,
        "checkpoint": f"{RCPT}#{sha(RCPT)[:12]}",
        "summary": ("W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01 complete at worker level: artifacts on disk and hash-pinned. "
                    "Verdict PREFLIGHT_CLEARED_BY_REBIND__PASS_BLOCKED_ONLY_BY_REC41_STAGEB_R03; pre-registered run verdict "
                    "REBIND_INSUFFICIENT_AT_MEASURED_BASE with 0 union escapes. This is a worker completion claim, not a node "
                    "transition; G-FORM, F2b status and the rev14 freeze remain the controller's and leads' to set. No canonical write."),
        "evidence_refs": [art(REPORT), art(ADDENDUM), art(README), art(CPT), art(RCPT),
                          "artifacts/formulation/FROZEN.json#815e08079aef",
                          "artifacts/formulation/evidence/semantic_escape_rebased.json#7e44de0e3906"],
        "next_falsifier": ("Re-run check_rebind_coverage.py on byte-identical pinned inputs; falsified if the baseline no longer "
                           "exits 3, the regenerated fixture does not bind live C0 or is not byte-deterministic, any predicate flips, "
                           "a recorded catch is an escape, or any pin drifts. A6 is falsified by a post-stage-B-fix run that still exits non-zero."),
    },
]


def main() -> int:
    seen = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            try:
                seen.add(json.loads(line)["event_id"])
            except Exception:  # noqa: BLE001
                pass
    if SEEN.exists():
        try:
            seen |= set(json.loads(SEEN.read_text()))
        except Exception:  # noqa: BLE001
            pass

    ok, skipped = [], []
    for ev in EV:
        if ev["event_id"] in seen:
            skipped.append(ev["event_id"])
            continue
        validate_event(ev)
        # fail closed on every declared artifact hash
        for key in ("path", "target_artifact"):
            if ev.get(key) and (ROOT / ev[key]).exists() and key == "path":
                declared = ev.get("sha256")
                if declared and sha(ev[key]) != declared:
                    raise SystemExit(f"hash mismatch for {ev[key]}")
        for ref in ev.get("evidence_refs", []) + ev.get("artifact_refs", []):
            p = ref.split("#")[0]
            if not (ROOT / p).exists():
                raise SystemExit(f"missing evidence path {p} in {ev['event_id']}")
            if "#" in ref:
                want = ref.split("#")[1]
                got = sha(p)
                if not (got.startswith(want) or want in got):
                    raise SystemExit(f"evidence hash mismatch {ref}")
        ok.append(ev["event_id"])
    if ok:
        with OUTBOX.open("a") as f:
            for ev in EV:
                if ev["event_id"] in ok:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    print(json.dumps({"validated_and_appended": ok, "skipped_duplicates": skipped,
                      "outbox": str(OUTBOX.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
