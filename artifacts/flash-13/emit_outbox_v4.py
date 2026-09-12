#!/usr/bin/env python3
"""Append FORM-GATE-01 v4 events: direct answers to lead followups 2 and 3, final differential
against the current lead tool, F-GATE-4 (unpublished R17-R22) and F-GATE-5 (manifest drift)."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "research_map"))
from schemas import validate_event  # noqa: E402

ACTOR = "deepseek-flash-13"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha(rel):
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def ref(rel):
    return f"{rel}#{sha(rel)[:16]}"


def ev(eid, etype, **kw):
    e = {"event_id": eid, "event_type": etype, "created_at": NOW, "actor": ACTOR, **kw}
    validate_event(e)
    return e


def main():
    readme = "artifacts/flash-13/form_gate/README.md"
    rep = "artifacts/flash-13/form_gate/gate_report.json"
    suite = "artifacts/flash-13/form_gate/fixture_suite_report.json"
    diffrep = "artifacts/flash-13/form_gate/differential_report.json"
    gate = "artifacts/flash-13/form_gate/check_class_schema.py"
    spec = "artifacts/formulation/rule_spec.json"
    frozen = "artifacts/formulation/FROZEN.json"
    lead = "artifacts/formulation/tools/check_class_schema.py"
    wcc = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
    c2 = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
    c0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"

    events = [
        ev("f13-fg4-art-readme", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
           artifact_type="documentation", path=readme, sha256=sha(readme),
           validation_status="unverified"),
        ev("f13-fg4-art-diff", "artifact", node_id="F1", class_id="AF-WCC-VAC-GEN",
           artifact_type="differential_report", path=diffrep, sha256=sha(diffrep),
           validation_status="unverified"),
        ev("f13-fg4-status-answer", "status", node_id="F1", status="active", hours=4.0,
           summary=(
               "Answering leadform followups 2/3. CHOICE: the gate was adapted to the frozen "
               "canonical layout (rule_spec field paths), NOT labelled draft-shape-only; it now "
               "passes the frozen exemplars. Runs: (a) FROZEN revision 5 hashes "
               "f512af5f4db3/836746b39be4/188e513130c6 -> all PASS R01-R16 with frozen_match=true; "
               "(b) current disk hashes ef8441e4bc2c/e67a6707ecd2/7693c7c1c73a -> all PASS "
               "R01-R16 (frozen_match=false because FROZEN.json has not been bumped). Per-rule "
               "verdicts and JSON paths are in gate_report.json results[].per_rule. Fixture suite: "
               "3/3 conforming, 24/24 mutants single-rule keyed, 6 rephrased -> 3 caught / 3 "
               "semantic blind spots; exit 0/1/3 contract holds. DISAGREEMENTS (the deliverable): "
               "final differential vs lead tool sha 1fcc3ad1df5d is 30/36 agreement; both gates "
               "pass all three canonical schemas and reject 24/24 mutants; the 6 remaining "
               "disagreements are my conforming/rephrased fixtures failing the lead tool's "
               "R17/R18/R19/R22, which do not exist in the published rule_spec (see F-GATE-4). "
               "No completion or gate verdict claimed."),
           evidence_refs=[ref(gate), ref(rep), ref(suite), ref(diffrep), ref(spec),
                          ref(frozen), ref(lead), ref(wcc), ref(c2), ref(c0)],
           next_falsifier=(
               "Publish R17-R22 and re-freeze; then extend this gate and re-run the differential. "
               "Until then, any claim that the two gates agree is limited to R01-R16.")),
        ev("f13-fg4-blocker-unpublished", "blocker", node_id="F1",
           description=(
               "Two contract-governance gaps block a clean gate adjudication. (1) The canonical "
               "tool at sha 1fcc3ad1df5d enforces rules R17/R18/R19/R22 that are absent from the "
               "published artifacts/formulation/rule_spec.json (spec_version 1.2, only R01-R16); "
               "the frozen schemas satisfy them but a third-party gate cannot implement or "
               "challenge rules it cannot read. (2) FROZEN.json revision 5 records schema hashes "
               "f512af5f4db3/836746b39be4/188e513130c6 while the files on disk are "
               "ef8441e4bc2c/e67a6707ecd2/7693c7c1c73a, so the frozen hash a reviewer binds to is "
               "not the artifact currently on disk. Both gates nonetheless pass both generations."),
           needed_to_unblock=(
               "lead-formulation: publish the R17-R22 rule text (spec v1.3) and bump FROZEN.json "
               "to the current disk hashes, re-emitting artifact events per the manifest's own "
               "change protocol; or pin the canonical tool to spec v1.2. Then this worker extends "
               "the gate to the published rule set and re-runs the differential."),
           evidence_refs=[ref(spec), ref(lead), ref(frozen),
                          "artifacts/flash-13/form_gate/differential_report.json",
                          "artifacts/flash-13/form_gate/README.md"]),
    ]
    out = REPO / "comms" / "outbox" / f"{ACTOR}.jsonl"
    with open(out, "a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} validated v4 events; total lines="
          f"{sum(1 for _ in open(out))} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
