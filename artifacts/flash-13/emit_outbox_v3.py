#!/usr/bin/env python3
"""Append FORM-GATE-01 v3 events: differential cross-check against the lead's frozen tool,
fixture conformance to the frozen contract, and the resulting F-GATE-3 finding."""
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
    g = "artifacts/flash-13/form_gate/check_class_schema.py"
    rep = "artifacts/flash-13/form_gate/gate_report.json"
    suite = "artifacts/flash-13/form_gate/fixture_suite_report.json"
    man = "artifacts/flash-13/form_gate/fixtures/manifest.json"
    readme = "artifacts/flash-13/form_gate/README.md"
    runner = "artifacts/flash-13/form_gate/run_gate_tests.py"
    mkfix = "artifacts/flash-13/form_gate/make_fixtures.py"
    diff = "artifacts/flash-13/form_gate/differential_vs_lead_tool.py"
    diffrep = "artifacts/flash-13/form_gate/differential_report.json"
    lead = "artifacts/formulation/tools/check_class_schema.py"

    events = []
    for key, path, atype in (("gate", g, "class_schema_gate"), ("report", rep, "gate_report"),
                             ("suite", suite, "acceptance_suite_report"),
                             ("manifest", man, "fixture_corpus"), ("readme", readme, "documentation"),
                             ("runner", runner, "acceptance_runner"),
                             ("gen", mkfix, "fixture_generator"),
                             ("diff", diff, "differential_runner"),
                             ("diffrep", diffrep, "differential_report")):
        events.append(ev(f"f13-fg3-art-{key}", "artifact", node_id="F1",
                         class_id="AF-WCC-VAC-GEN", artifact_type=atype, path=path,
                         sha256=sha(path), validation_status="unverified"))
    events.append(ev(
        "f13-fg3-status-1", "status", node_id="F1", status="active", hours=3.5,
        summary=(
            "FORM-GATE-01 v3: black-box differential run against the lead's frozen tool "
            f"({lead} sha {sha(lead)[:12]}). 36 targets, 27 verdict agreements (75%); both gates "
            "pass 3/3 conforming fixtures and 3/3 frozen canonical schemas (WCC f512af5f4db3, "
            "C2 836746b39be4, C0 188e513130c6, frozen_match=true). This gate rejects 24/24 "
            "single-rule mutants; the lead tool rejects 18/24. The 9 remaining disagreements are "
            "all cases where this gate is stricter on spec text: numeric decay rates (R05), "
            "source-conclusion overclaim (R15), cross-family tokens in conclusion blocks "
            "(R12 x4), spelled-out composite regularity (R13), non-Baire generic_set (R07), "
            "family-dependent tier-1 witness (R14). Fixtures were first conformed to the frozen "
            "canonical shape (axes, predicate_name, extension_solution_concept vocabulary, "
            "one_way_entailments/forbidden_transfers, statement_natural_language/formal, "
            "completeness_of_slice, I_plus_topology) and R09's negation check was tightened to "
            "clause level after its own m19 mutant slipped through. F-GATE-3 requests "
            "adjudication: merge these checks into the canonical gate or drop them from this one. "
            "No node completion or gate verdict claimed."),
        evidence_refs=[ref(g), ref(rep), ref(suite), ref(man), ref(diffrep), ref(lead)],
        next_falsifier=(
            "Run both gates on the frozen fixture corpus and rule on each of the 9 disagreements; "
            "or exhibit a conforming schema this gate rejects, which would falsify a stricter "
            "check.")))
    events.append(ev(
        "f13-fg3-claim-diff", "claim", class_id="AF-WCC-VAC-GEN", node_id="F1",
        conclusion_type="numerical_evidence",
        statement=(
            "Independent-implementation differential on 36 structurally controlled targets: this "
            "gate and the lead's frozen gate agree on all accepted objects (3 conforming "
            "fixtures, 3 frozen canonical schemas) and on 18/24 mutants, and disagree on 9 "
            "mutants/rephrased variants where this gate rejects on spec text (R05 numeric decay, "
            "R12 cross-family leakage x4, R13 spelled-out composite, R07 Baire formula, R14 "
            "family witness, R15 overclaim). The disagreement set is a gate-coverage gap "
            "candidate, not a schema defect."),
        assumptions=[
            "the lead tool is invoked as a black box; no source import or copy",
            "verdicts compared at the sha256 recorded in differential_report.json"],
        falsifier=(
            "A domain reviewer shows any of the 9 stricter rule applications rejects a "
            "formulation the spec permits; then that check is over-strict and must be dropped."),
        evidence_refs=[ref(diffrep), ref(g), ref(lead)],
        artifact_refs=[{"path": diffrep, "sha256": sha(diffrep)}]))

    out = REPO / "comms" / "outbox" / f"{ACTOR}.jsonl"
    with open(out, "a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} validated v3 events; total lines="
          f"{sum(1 for _ in open(out))} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
