#!/usr/bin/env python3
"""Emit the W036-CLASSSEP-DISJ-RULE-01 upward events (append-only) and validate them.

Writes: comms/outbox/worker-036.jsonl (append) and a local copy under this directory.
Every event is one JSON object per line with event_id / event_type / created_at / actor.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-036.jsonl"
LOCAL = HERE / "events_w036_disj_rule.jsonl"


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ck = json.loads((HERE / "CHECKPOINT.json").read_text())
    rep_sha = ck["artifacts"]["artifacts/worker-036/classsep_disj_rule/report.json"]
    ck_sha = h(HERE / "CHECKPOINT.json")
    cand_sha = ck["artifacts"]["artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py"]
    fx_sha = ck["artifacts"]["artifacts/worker-036/classsep_disj_rule/fixtures/disj_fixtures.jsonl"]
    probe_sha = ck["artifacts"]["artifacts/worker-036/classsep_disj_rule/probe_disj_rule.py"]
    r = ck["result"]
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    base = "w036-disj-rule-20260912T0050"
    classes = ck["class_ids"]
    evidence = [
        f"artifacts/worker-036/classsep_disj_rule/report.json#{rep_sha[:12]}",
        f"artifacts/worker-036/classsep_disj_rule/CHECKPOINT.json#{ck_sha[:12]}",
        "research_map/class_separation.py#c266dbceca87",
        "research_map/research_map.json#3d45be5969ec",
        "ledger/theorems.jsonl#a1674f094979",
        "artifacts/worker-097/l0_rev3_review/snapshots/theorems.jsonl#3e3d35531421",
        "artifacts/worker-029/f2b_full_review/ledger_theorems_snapshot.jsonl#ce42d205e761",
        "artifacts/worker-07/class_separation_falsification/results.json#d69ad58468be",
        "artifacts/worker-027/classsep_token_binding/ood_corpus/results.json",
    ]
    events = [
        {
            "event_id": f"{base}-task",
            "event_type": "status",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "status": "active",
            "hours": 0.05,
            "summary": ("Took ONE class-bound task (no inbox card for worker-036; self-selected from the "
                        "evidence_hard_failures/blocker raised by my prior lifecycle W036-CLASSSEP-DISJ-01/02/03): "
                        "W036-CLASSSEP-DISJ-RULE-01, build and measure a staged container-disjunction rule (R5) for "
                        "research_map/class_separation.py against the pinned canonical bytes c266dbceca87, with a "
                        "pre-registered fixture battery and a live map/ledger blast-radius counterfactual. Canonical "
                        "files read-only; no rule edits to canonical artifacts."),
            "evidence_refs": evidence[:2],
            "next_falsifier": "Re-hash the staged deliverables; any mismatch with CHECKPOINT.json voids the task claim.",
        },
        {
            "event_id": f"{base}-artifact-candidate",
            "event_type": "artifact",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_ids": classes,
            "artifact_type": "staged_checker_candidate",
            "path": "artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py",
            "sha256": cand_sha,
            "validation_status": "unverified",
            "note": ("Canonical c266dbceca87 + exactly one inserted hunk (10 added lines, 0 removed), generated "
                     "mechanically by build_candidate.py; reverse-apply reproduces canonical byte-for-byte. "
                     "STAGED ONLY: research_map/class_separation.py untouched (detector owner applies checker changes)."),
            "evidence_refs": [f"artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py#{cand_sha[:12]}"],
            "next_falsifier": "Any canonical file changed by this task, or reverse-apply not reproducing c266dbceca87, voids the artifact.",
        },
        {
            "event_id": f"{base}-artifact-fixtures",
            "event_type": "artifact",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_ids": classes,
            "artifact_type": "fixture_corpus",
            "path": "artifacts/worker-036/classsep_disj_rule/fixtures/disj_fixtures.jsonl",
            "sha256": fx_sha,
            "validation_status": "unverified",
            "note": ("26 pre-registered cases: 8 positives (2- and 3-class containers, list/comma/semicolon, "
                     "duplicate, case/space, three-group ids), 13 negatives/orthogonality (single, duplicate-same, "
                     "variant tag, non-class token, empty/null, metalinguistic prose, unknown-token, single-token "
                     "merge, CF-16 prose shape), 1 map-level, 3 text-route scope cases."),
            "evidence_refs": [f"artifacts/worker-036/classsep_disj_rule/fixtures/disj_fixtures.jsonl#{fx_sha[:12]}"],
            "next_falsifier": "Any fixture expectation not met by the final run voids the coverage claim.",
        },
        {
            "event_id": f"{base}-artifact-probe",
            "event_type": "artifact",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_ids": classes,
            "artifact_type": "checker",
            "path": "artifacts/worker-036/classsep_disj_rule/probe_disj_rule.py",
            "sha256": probe_sha,
            "validation_status": "unverified",
            "note": ("Deterministic probe: 23 checks (pin/drift, structural reverse-apply, fixture battery, frozen-map "
                     "counterfactual with independent label-for-label re-derivation, 3 pinned ledger revisions, worker-07 "
                     "and worker-027 corpus regression, inert/overfire power controls, measured text-route limitation). "
                     "Exit 0 and overall PASS at the pinned snapshots."),
            "evidence_refs": [f"artifacts/worker-036/classsep_disj_rule/probe_disj_rule.py#{probe_sha[:12]}"],
            "next_falsifier": "Re-run at the pinned snapshots; any of the 23 checks failing falsifies the measurement.",
        },
        {
            "event_id": f"{base}-artifact-report",
            "event_type": "artifact",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_ids": classes,
            "artifact_type": "measurement_report",
            "path": "artifacts/worker-036/classsep_disj_rule/report.json",
            "sha256": rep_sha,
            "validation_status": "unverified",
            "note": (f"overall {r['overall']} {r['checks_passed']}/{r['checks_total']}; map canonical "
                     f"{r['map_canonical_findings']} -> candidate {r['map_candidate_findings']} (+{r['map_added']}, "
                     f"-{r['map_removed']}), added by surface {r['map_added_by_surface']}, by class count "
                     f"{r['map_added_by_class_count']}; ledger disj rows identical on all three pinned revisions; "
                     f"worker-07 regression unchanged {r['worker_07_regression_canonical']}."),
            "evidence_refs": [f"artifacts/worker-036/classsep_disj_rule/report.json#{rep_sha[:12]}"],
            "next_falsifier": "A re-run producing different counts at the same pinned snapshots voids the report.",
        },
        {
            "event_id": f"{base}-artifact-checkpoint",
            "event_type": "artifact",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_ids": classes,
            "artifact_type": "checkpoint",
            "path": "artifacts/worker-036/classsep_disj_rule/CHECKPOINT.json",
            "sha256": ck_sha,
            "validation_status": "unverified",
            "note": ("Bounded-task checkpoint with full 64-hex artifact and input hashes; copy mirrored at "
                     "runtime/state/w036_classsep_disj_rule_checkpoint_20260912T0050.json. No canonical registry written."),
            "evidence_refs": [f"artifacts/worker-036/classsep_disj_rule/CHECKPOINT.json#{ck_sha[:12]}"],
            "next_falsifier": "Any artifact hash in the checkpoint failing to match disk voids the checkpoint.",
        },
        {
            "event_id": f"{base}-claim",
            "event_type": "claim",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "conclusion_type": "formal_model",
            "counts_as_full_schema_verdict": False,
            "statement": (
                "At the pinned hashes (class_separation.py c266dbceca87, frozen map 3d45be5969ec, L0 ledger revisions "
                "a1674f094979 / 3e3d35531421 / ce42d205e761, worker-07 corpus d69ad58468be) the mechanically generated "
                "candidate that adds exactly one container-level rule to _scan_class_ids closes the class_ids "
                "disjunction blind spot measured in W036-CLASSSEP-DISJ-01/02/03 with 23/23 checks passing: all 8 "
                "pre-registered positive fixture shapes are detected, all 13 negative/orthogonality cases stay clean "
                "(including the CF-16 prose shape, whose 10 live prose findings are unchanged), the standing worker-07 "
                "corpus is byte-identical per fixture (17/0/10/0) for canonical and candidate, the worker-027 OOD arity "
                "corpus classification is unchanged, and on all three pinned ledger revisions the candidate flags "
                "exactly rows {3,4,24,26,29,45,57,59} where canonical flags none. The measured live blast radius on the "
                "frozen map is +100 container findings (94 claim containers, 6 node containers; 58 four-class, 32 "
                "three-class, 10 two-class), because the map's class_ids containers are dominated by scope-metadata "
                "declarations rather than singular bindings; the HF-02 target population is the 8 ledger rows plus the "
                "10 two-class map containers. The artifact-body route (findings_for_text) remains blind and is not "
                "covered by this claim. Therefore the staging is a correct coverage fix for structured declaration "
                "surfaces with a measured precision cost, and the surface/cardinality policy for map claims is an owner "
                "decision, not a worker one."
            ),
            "assumptions": [
                "Canonical detector semantics are read from the pinned source and loaded from a byte-identical snapshot; no canonical code was modified (CF-4: detector owner applies checker changes).",
                "A class_ids container is disjunctive iff it holds >=2 distinct members of the four frozen classes; registered variant ids are tags/relations, never classes (worker-023 adjudication).",
                "The frozen map 3d45be5969ec and the three ledger revisions are the measured surfaces; live continuation of swarm traffic does not alter the pinned-snapshot result.",
                "Worker events cannot set gate verdicts or node status; this claim supplies measurement evidence for the detector/gate owner.",
            ],
            "falsifier": (
                "Re-run `python3 artifacts/worker-036/classsep_disj_rule/probe_disj_rule.py` on the pinned snapshots: "
                "falsified if any of the 23 checks fails, i.e. any positive fixture unflagged or any negative flagged; "
                "any added frozen-map finding not carrying 'container disjoins'; any of the 8 named ledger rows missed "
                "on any pinned revision or canonical flags one there; any worker-07 or worker-027 OOD fixture changing "
                "classification; reverse-applying the R5 hunk not reproducing canonical c266dbceca87; the inert-R5 "
                "control adding any finding or the overfire-R5 control not breaking negatives; or any measured input "
                "drifting mid-run. Live application is additionally void if research_map/class_separation.py has moved "
                "off c266dbceca87 without a rebase."
            ),
            "evidence_refs": evidence,
            "artifact_refs": [
                f"artifacts/worker-036/classsep_disj_rule/report.json#{rep_sha[:12]}",
                f"artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py#{cand_sha[:12]}",
                f"artifacts/worker-036/classsep_disj_rule/fixtures/disj_fixtures.jsonl#{fx_sha[:12]}",
                f"artifacts/worker-036/classsep_disj_rule/probe_disj_rule.py#{probe_sha[:12]}",
            ],
        },
        {
            "event_id": f"{base}-status-complete",
            "event_type": "status",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "class_ids": classes,
            "status": "active",
            "hours": 0.1,
            "summary": ("W036-CLASSSEP-DISJ-RULE-01 complete at worker level (one bounded class-bound task; completion "
                        "claim only, NOT a node done and NOT a gate verdict). Deliverables on disk and hash-pinned: "
                        "candidate " + cand_sha[:12] + ", fixtures " + fx_sha[:12] + ", probe " + probe_sha[:12] +
                        ", report " + rep_sha[:12] + ", checkpoint " + ck_sha[:12] + ". Probe overall PASS 23/23, exit 0. "
                        "No canonical artifact, map, gate, ledger or numerics_lock modified. Exiting for recycling."),
            "evidence_refs": [f"artifacts/worker-036/classsep_disj_rule/CHECKPOINT.json#{ck_sha[:12]}",
                              "runtime/state/w036_classsep_disj_rule_checkpoint_20260912T0050.json"],
            "next_falsifier": "Re-hash the five deliverables; a mismatch voids the completion claim.",
        },
    ]
    lines = [json.dumps(e, ensure_ascii=False) for e in events]
    for e, line in zip(events, lines):
        assert json.loads(line)["event_id"] == e["event_id"]
        for req in ("event_id", "event_type", "created_at", "actor"):
            assert e.get(req), (e["event_id"], req)
    with OUTBOX.open("a") as f:
        existing = OUTBOX.read_text() if OUTBOX.exists() else ""
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write("\n".join(lines) + "\n")
    LOCAL.write_text("\n".join(lines) + "\n")
    print(json.dumps({"appended": len(events), "outbox": str(OUTBOX.relative_to(ROOT)), "local": str(LOCAL.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
