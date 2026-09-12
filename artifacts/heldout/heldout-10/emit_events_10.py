#!/usr/bin/env python3
"""Emit FORM-HELDOUT-10 upward events to comms/outbox/worker-084.jsonl (idempotent).

One JSON object per line, protocol fields: event_id, event_type, created_at, actor.
Re-running does not duplicate events: an event_id already present in the outbox is skipped.

Usage: python3 emit_events_10.py
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms" / "outbox" / "worker-084.jsonl"
CST = timezone(timedelta(hours=8))

TASK = "FORM-HELDOUT-10"
CORPUS = "FORM-HELDOUT-10"
NODE = "A1"
GATE = "G-CLASSBIND"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
ASSIGNMENT = ("successor to assign-FORM-HELDOUT-09-worker-084 (self-claimed re-issue; no new inbox "
              "card issued; the 09 card pins are stale on 4/6 paths)")
FALSIFIER = ("A heldout-10 run that binds superseded bytes, a manifest hashed after a stage run, any "
             "control rejected for a reason other than the pre-registered R03 literal-match defect, or a "
             "union escape rate of 0 reported without raw per-fixture verdicts.")
DO_NOT_CLAIM = "No node completion, no gate verdict, no theorem. Independent measurement evidence only."


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    man = json.loads((HERE / "manifest.json").read_text())
    rep = json.loads((HERE / "report.json").read_text())
    raw = json.loads((HERE / "raw" / "raw_verdicts.json").read_text())
    find = json.loads((HERE / "findings.json").read_text())
    hs = {
        "manifest.json": sha(HERE / "manifest.json"),
        "report.json": sha(HERE / "report.json"),
        "raw/raw_verdicts.json": sha(HERE / "raw" / "raw_verdicts.json"),
        "checkpoint.json": sha(HERE / "checkpoint.json"),
        "findings.json": sha(HERE / "findings.json"),
        "REPORT.md": sha(HERE / "REPORT.md"),
    }
    t = lambda: datetime.now(CST).isoformat(timespec="seconds")  # noqa: E731
    base = {"actor": "worker-084", "node_id": NODE, "gate": GATE, "class_ids": CLASSES,
            "task_id": TASK, "corpus_id": CORPUS, "assignment": ASSIGNMENT}
    ev = []

    def add(event_id, event_type, **kw):
        e = {"event_id": event_id, "event_type": event_type, "created_at": t(), **base, **kw}
        ev.append(e)

    add("w084-heldout10-02-artifact-manifest", "artifact",
        artifact_type="heldout_corpus_manifest", path=rel(HERE / "manifest.json"),
        sha256=hs["manifest.json"], validation_status="unverified",
        evidence_refs=[f"{rel(HERE / 'manifest.json')}#sha256:{hs['manifest.json'][:12]}",
                       "artifacts/formulation/FROZEN.json#sha256:815e08079aef",
                       "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2"],
        note=("pre-registered before any fixture stage run; 33 mutants / 19 families / 7 controls on "
              "LIVE FROZEN rev29 rev13 bytes; card_pin_staleness records 4/6 stale heldout-09 pins; "
              "known_calibration_defect records the F1/WCC R03 rejection at freeze time"))
    add("w084-heldout10-03-artifact-raw-verdicts", "artifact",
        artifact_type="heldout_raw_verdicts", path=rel(HERE / "raw" / "raw_verdicts.json"),
        sha256=hs["raw/raw_verdicts.json"], validation_status="unverified",
        evidence_refs=[f"{rel(HERE / 'raw' / 'raw_verdicts.json')}#sha256:{hs['raw/raw_verdicts.json'][:12]}"],
        note=("per-fixture stage A/B verdicts for 33 mutants + 7 controls; no fixture rewritten after a "
              "verdict; pins re-measured after the run with no drift"))
    add("w084-heldout10-04-artifact-report", "artifact",
        artifact_type="heldout_measurement_report", path=rel(HERE / "report.json"),
        sha256=hs["report.json"], validation_status="unverified",
        evidence_refs=[f"{rel(HERE / 'report.json')}#sha256:{hs['report.json'][:12]}"],
        note=("valid=false (strict H5: frozen WCC canonical rejected by stage B R03, pre-registered); "
              "all-mutant union escape 0.7879 (7/33 caught, all R03-only WCC); informative C2+C0 arms "
              "26 mutants union escape 1.0 (0/26 caught)"))
    add("w084-heldout10-05-artifact-findings", "artifact",
        artifact_type="heldout_findings", path=rel(HERE / "findings.json"),
        sha256=hs["findings.json"], validation_status="unverified",
        evidence_refs=[f"{rel(HERE / 'findings.json')}#sha256:{hs['findings.json'][:12]}"],
        note="interpretation only; every number copied from report.json/raw_verdicts.json")
    add("w084-heldout10-06-artifact-report-md", "artifact",
        artifact_type="heldout_report_markdown", path=rel(HERE / "REPORT.md"),
        sha256=hs["REPORT.md"], validation_status="unverified",
        evidence_refs=[f"{rel(HERE / 'REPORT.md')}#sha256:{hs['REPORT.md'][:12]}"])

    add("w084-heldout10-07b-claim-c2", "claim", class_id="AF-SCC-C2-VAC-GEN",
        supersedes_rejected_event_id="w084-heldout10-07-claim-c2",
        statement=("At the LIVE FROZEN rev29 bytes, on the informative C2 arm (13 mutants spanning 13 "
                   "leak families), stage A accepted 13/13 and stage B accepted 13/13; C2 union escape "
                   "1.0, 0 caught. The rev13 schema bytes do not close the C2 structural/semantic "
                   "class-binding leak."),
        conclusion_type="numerical_evidence",
        conclusion_type_note="worker measurement evidence only; not a theorem, not a gate verdict",
        assumptions=["fixtures frozen and unmodified since the pre-registered manifest",
                     "stage tool bytes 000e09e46b2f / c79d8ab8440a unchanged during the run",
                     "arm informative because the frozen C2 canonical passes both stages"],
        falsifier=("Re-run run_heldout_10.py at the recorded hashes; falsified if any C2 mutant is caught, "
                   "any verdict disagrees, or the C2 canonical fails a stage."),
        evidence_refs=[f"{rel(HERE / 'report.json')}#sha256:{hs['report.json'][:12]}",
                       f"{rel(HERE / 'raw' / 'raw_verdicts.json')}#sha256:{hs['raw/raw_verdicts.json'][:12]}",
                       "schemas/af_scc_c2_vacuum.yaml#sha256:e9a27996dfd3"],
        artifact_refs=[rel(HERE / "report.json"), rel(HERE / "raw" / "raw_verdicts.json")])
    add("w084-heldout10-08b-claim-c0", "claim", class_id="AF-SCC-C0-VAC-GEN",
        supersedes_rejected_event_id="w084-heldout10-08-claim-c0",
        statement=("At the LIVE FROZEN rev29 bytes, on the informative C0 arm (13 mutants spanning 13 "
                   "leak families), stage A accepted 13/13 and stage B accepted 13/13; C0 union escape "
                   "1.0, 0 caught, including both new f0-binding-stale-hash mutants m32/m33. The rev13 "
                   "evidence-binding repair is not verified by either stage."),
        conclusion_type="numerical_evidence",
        conclusion_type_note="worker measurement evidence only; not a theorem, not a gate verdict",
        assumptions=["fixtures frozen and unmodified since the pre-registered manifest",
                     "stage tool bytes unchanged during the run",
                     "arm informative because the frozen C0 canonical passes both stages"],
        falsifier=("Re-run run_heldout_10.py at the recorded hashes; falsified if any C0 mutant is caught, "
                   "any verdict disagrees, or the C0 canonical fails a stage."),
        evidence_refs=[f"{rel(HERE / 'report.json')}#sha256:{hs['report.json'][:12]}",
                       f"{rel(HERE / 'raw' / 'raw_verdicts.json')}#sha256:{hs['raw/raw_verdicts.json'][:12]}",
                       "schemas/af_scc_c0_vacuum.yaml#sha256:b2ab6acb2bbe"],
        artifact_refs=[rel(HERE / "report.json"), rel(HERE / "raw" / "raw_verdicts.json")])
    add("w084-heldout10-09b-claim-r03-calibration", "claim", class_id="AF-WCC-VAC-GEN",
        supersedes_rejected_event_id="w084-heldout10-09-claim-r03-calibration",
        statement=("Stage B c79d8ab8440a rejects the untouched frozen F1/WCC canonical "
                   "schemas/af_wcc_vacuum.yaml#d9cebb9404b2 on R03 (literal-substring binder match), "
                   "measured before corpus freeze and again during the run. All 7 WCC-arm stage-B "
                   "catches are R03-only and therefore spurious; the WCC arm is non-informative and "
                   "strict H5 is false for this pre-registered reason alone."),
        conclusion_type="numerical_evidence",
        conclusion_type_note="worker measurement evidence only; not a theorem, not a gate verdict",
        assumptions=["canonical bytes unchanged before/after the run",
                     "R03 is the only failed rule in all 7 WCC catches"],
        falsifier=("An independent run of stage B c79d8ab8440a on schemas/af_wcc_vacuum.yaml "
                   "d9cebb9404b2 reporting accept, or a stage-B revision whose R03 resolves the binder "
                   "structurally, falsifies this calibration finding."),
        evidence_refs=[f"{rel(HERE / 'manifest.json')}#sha256:{hs['manifest.json'][:12]}",
                       f"{rel(HERE / 'raw' / 'raw_verdicts.json')}#sha256:{hs['raw/raw_verdicts.json'][:12]}",
                       "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2"],
        artifact_refs=[rel(HERE / "manifest.json"), rel(HERE / "raw" / "raw_verdicts.json")])

    add("w084-heldout10-10-blocker-strict-h5", "blocker",
        description=("Strict H5 is false for FORM-HELDOUT-10 solely because stage B c79d8ab8440a rejects "
                     "the untouched frozen F1/WCC canonical d9cebb9404b2 on R03 (literal-substring binder "
                     "match: formal writes 'q in I+ and t0 in [0,T)' while the binder is '(q,t0)'). The "
                     "instrument defect is unchanged by the rev13 prose repair. Consequence: the WCC arm "
                     f"carries no signal and the strict run is not valid; the informative C2/C0 arms "
                     f"measure union escape {rep['aggregates_informative_arms_only']['union_escape']} "
                     f"({rep['aggregates_informative_arms_only']['union_caught']}/"
                     f"{rep['aggregates_informative_arms_only']['mutants']} caught) on fresh rev13 fixtures."),
        needed_to_unblock=("Stage-B R03 structural binder equivalence (or an explicit lead annotation that "
                           "R03 is a recorded calibration blind spot), after which this preserved corpus can "
                           "be re-run unchanged; no rule edit was made by this worker."),
        evidence_refs=[f"{rel(HERE / 'report.json')}#sha256:{hs['report.json'][:12]}",
                       "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2",
                       "artifacts/worker-06/spec_conformance_audit.py#sha256:c79d8ab8440a"],
        falsifier=("A stage-B run at c79d8ab8440a that accepts d9cebb9404b2, or a lead annotation that "
                   "closes the R03 question, falsifies the blocker."))

    add("w084-heldout10-11-review-self", "review", target_id=TASK, reviewer="worker-084",
        verdict="inconclusive", score=3,
        hard_failures=["strict H5 false: frozen F1/WCC canonical rejected by stage B R03 (instrument, "
                       "pre-registered, not a corpus defect)"],
        findings=["informative C2/C0 arms: 26/26 mutants escape both stages (union escape 1.0), "
                  "replicating heldout-09 on fresh rev13 bytes",
                  "all 7 WCC-arm catches are R03-only and spurious",
                  "both new f0-binding-stale-hash mutants escape both stages",
                  "4/4 authored controls and both frozen C2/C0 canonicals pass both stages; no format "
                  "domination of the informative arms",
                  "manifest hashed before any fixture stage run; no pin moved during the run"],
        evidence_refs=[f"{rel(HERE / 'report.json')}#sha256:{hs['report.json'][:12]}"],
        note="self-review by the executor; not a gate verdict and not an independent review")

    add("w084-heldout10-12-checkpoint", "status", status="active", hours=0.4,
        summary=(f"CHECKPOINT (worker-084, {TASK}): strict valid=false (pre-registered R03/F1 defect); "
                 f"33 mutants / 19 families / 7 controls at FROZEN rev29; all live pins matched before and "
                 f"after the run (no moving target); informative C2+C0 arms union escape "
                 f"{rep['aggregates_informative_arms_only']['union_escape']} "
                 f"({rep['aggregates_informative_arms_only']['union_caught']}/26 caught); new "
                 f"f0-binding-stale-hash family escapes 2/2. Artifacts: manifest {hs['manifest.json'][:12]}, "
                 f"raw {hs['raw/raw_verdicts.json'][:12]}, report {hs['report.json'][:12]}, findings "
                 f"{hs['findings.json'][:12]}."),
        evidence_refs=[f"{rel(HERE / 'checkpoint.json')}#sha256:{hs['checkpoint.json'][:12]}",
                       f"{rel(HERE / 'report.json')}#sha256:{hs['report.json'][:12]}"],
        next_falsifier=("Independent re-run of run_heldout_10.py reproduces every per-fixture verdict and "
                        "the 0/26 informative-arm catch, or a repaired stage-B R03 changes the WCC control "
                        "verdict; either direction is informative."))
    add("w084-heldout10-13-complete", "status", status="active", hours=0.4,
        summary=(f"Bounded worker lifecycle complete ({TASK}, worker-084). One class-bound task executed "
                 f"under artifacts/heldout/heldout-10/: fresh corpus on LIVE FROZEN rev29 rev13 bytes, "
                 f"manifest hashed before any fixture stage run, both stages run once per fixture, raw "
                 f"verdicts retained, report + findings + checkpoint emitted. No node completion, no "
                 f"validation_status=passed, no gate verdict, no theorem is claimed; worker exits for "
                 f"recycling."),
        evidence_refs=[f"{rel(HERE / 'report.json')}#sha256:{hs['report.json'][:12]}",
                       f"{rel(HERE / 'checkpoint.json')}#sha256:{hs['checkpoint.json'][:12]}"],
        next_falsifier=FALSIFIER,
        do_not_claim=DO_NOT_CLAIM)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    emitted = 0
    with OUTBOX.open("a") as f:
        for e in ev:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e) + "\n")
            emitted += 1
    print(f"emitted {emitted} new events ({len(ev) - emitted} already present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
