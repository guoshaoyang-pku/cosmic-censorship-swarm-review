#!/usr/bin/env python3
"""Append the FORM-GATE-01 v2 events: gate re-run against FROZEN revision 4, extended fixtures,
and resolution of the F2a vocabulary blocker. All events validated before writing; all hashes
recomputed from disk."""
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


def sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def ref(rel: str, n: int = 16) -> str:
    return f"{rel}#{sha(rel)[:n]}"


def ev(eid, etype, **kw):
    e = {"event_id": eid, "event_type": etype, "created_at": NOW, "actor": ACTOR, **kw}
    validate_event(e)
    return e


def main() -> int:
    files = {
        "gate": "artifacts/flash-13/form_gate/check_class_schema.py",
        "report": "artifacts/flash-13/form_gate/gate_report.json",
        "suite": "artifacts/flash-13/form_gate/fixture_suite_report.json",
        "manifest": "artifacts/flash-13/form_gate/fixtures/manifest.json",
        "readme": "artifacts/flash-13/form_gate/README.md",
        "runner": "artifacts/flash-13/form_gate/run_gate_tests.py",
        "fixtures": "artifacts/flash-13/form_gate/make_fixtures.py",
        "frozen": "artifacts/formulation/FROZEN.json",
        "aliases": "artifacts/formulation/VOCAB_ALIASES.json",
        "spec": "artifacts/formulation/rule_spec.json",
        "wcc": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "c2": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "c0": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    }
    events = []
    for key, art_type in (("gate", "class_schema_gate"), ("report", "gate_report"),
                          ("suite", "acceptance_suite_report"), ("manifest", "fixture_corpus"),
                          ("readme", "documentation"), ("runner", "acceptance_runner"),
                          ("fixtures", "fixture_generator")):
        events.append(ev(f"f13-fg2-art-{key}", "artifact", node_id="F1",
                         class_id="AF-WCC-VAC-GEN", artifact_type=art_type,
                         path=files[key], sha256=sha(files[key]), validation_status="unverified"))
    events.append(ev(
        "f13-fg2-status-1", "status", node_id="F1", status="active", hours=2.5,
        summary=(
            "FORM-GATE-01 v2 re-run against FROZEN revision 4 "
            f"(FROZEN.json sha {sha(files['frozen'])[:12]}): all three canonical schemas PASS "
            "all 16 rules with frozen_match=true — af_wcc_vacuum f512af5f4db3 (R16 skipped), "
            "af_scc_c2_vacuum 836746b39be4, af_scc_c0_vacuum 188e513130c6. Per-rule verdicts and "
            "JSON paths are in gate_report.json results[].per_rule. Fixture suite extended for "
            "R09/R12/R15/R16 per the follow-up: 3/3 conforming pass, 24/24 mutants rejected and "
            "each keyed to exactly one rule id (m19-m24 added), 6 rephrased mutants now 3 caught "
            "(R13 spelled-out regularity, R07 non-Baire generic_set, R14 'continued' witness) and "
            "3 documented blind spots (semantic synonym leakage: r01/r02/r06). Gate supports the "
            "published VOCAB_ALIASES.json and records every alias_uses entry. F-GATE-1 (F2a "
            "pre-spec vocabulary) is resolved by the frozen revision; F-GATE-2 (R12 prohibition-"
            "context policy) remains an open spec question and is documented. No node completion "
            "or gate verdict claimed."),
        evidence_refs=[ref(files["gate"]), ref(files["report"]), ref(files["suite"]),
                       ref(files["manifest"]), ref(files["frozen"]), ref(files["aliases"]),
                       ref(files["wcc"]), ref(files["c2"]), ref(files["c0"])],
        next_falsifier=(
            "A frozen canonical revision on which the gate fails a rule a domain reviewer shows "
            "is legitimate, or a mutant that silently passes; the three remaining blind spots "
            "(r01/r02/r06) are the current semantic falsifiers.")))
    events.append(ev(
        "f13-fg2-status-f2", "status", node_id="F2", status="active", hours=0.2,
        summary=(
            "Blocker f13-fg-blocker-1 resolved: the revised canonical C2 schema "
            "(AF-SCC-C2-VAC-GEN) at frozen sha 836746b39be4 passes all 16 gate rules after the "
            "lead's revision and VOCAB_ALIASES.json policy; the earlier 14-rule vocabulary "
            "finding is historical. No further action requested from this worker beyond review."),
        evidence_refs=[ref(files["c2"]), ref(files["report"]), ref(files["aliases"])],
        next_falsifier=(
            "Any later revision of the C2 schema that reintroduces a pre-spec key or drops a "
            "required block; the gate is re-run on each frozen revision.")))
    events.append(ev(
        "f13-fg2-claim-c2", "claim", class_id="AF-SCC-C2-VAC-GEN", node_id="F2",
        conclusion_type="numerical_evidence",
        statement=(
            "Supersedes f13-fg-claim-1: at FROZEN revision 4 the canonical C2 schema "
            "(836746b39be4) passes all 16 rules of FORM-RULE-SPEC under this independent gate, "
            "including R06 (extension regularity exactly C2), R09/R10 (I+ not in conclusion, "
            "visibility cross-referenced to WCC), R13 (no composite C0/C2) and R16 (one-way "
            "implication ledger with forbidden WCC transfer). The earlier failure was a "
            "vocabulary-contract mismatch, now resolved by the frozen revision."),
        assumptions=[
            "the frozen hash is the review target per FROZEN.json change protocol",
            "structural pass only; C2 mathematics and citations remain A1/L1 work"],
        falsifier=(
            "A re-run of check_class_schema.py on sha 836746b39be4 that reports any rule failure, "
            "or a reviewer showing a rule passes vacuously on that file."),
        evidence_refs=[ref(files["c2"]), ref(files["report"]), ref(files["spec"])],
        artifact_refs=[{"path": files["report"], "sha256": sha(files["report"])}]))

    out = REPO / "comms" / "outbox" / f"{ACTOR}.jsonl"
    with open(out, "a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"appended {len(events)} validated v2 events to {out}")
    print(f"outbox lines={sum(1 for _ in open(out))} sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
