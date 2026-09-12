#!/usr/bin/env python3
"""Write CHECKPOINT.json for W036-CLASSSEP-DISJ-RULE-01 (artifact dir + runtime/state copy).

Hash-pins every deliverable and input with full 64-hex digests.  Does not write any
canonical registry (runtime/state/artifact_hashes.json is controller-owned).
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INSTANCE = "worker-036-20260912T003915-968807"


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    artifacts = {}
    for name in [
        "build_candidate.py",
        "make_checkpoint.py",
        "emit_events.py",
        "candidate_class_separation.py",
        "candidate_build.json",
        "probe_disj_rule.py",
        "report.json",
        "README.md",
        "fixtures/disj_fixtures.jsonl",
        "snapshots/class_separation.canonical.c266dbceca87.py",
        "snapshots/research_map.3d45be5969ec.json",
        "snapshots/theorems.a1674f094979.jsonl",
        "snapshots/theorems.3e3d35531421.jsonl",
        "snapshots/theorems.ce42d205e761.jsonl",
    ]:
        p = HERE / name
        artifacts[rel(p)] = h(p)
    for p in sorted((HERE / "controls").glob("*.py")):
        artifacts[rel(p)] = h(p)

    inputs = {
        "research_map/class_separation.py": h(ROOT / "research_map/class_separation.py"),
        "research_map/research_map.json": h(ROOT / "research_map/research_map.json"),
        "ledger/theorems.jsonl": h(ROOT / "ledger/theorems.jsonl"),
        "artifacts/worker-07/class_separation_falsification/results.json": h(ROOT / "artifacts/worker-07/class_separation_falsification/results.json"),
        "artifacts/worker-027/classsep_token_binding/ood_corpus/results.json": h(ROOT / "artifacts/worker-027/classsep_token_binding/ood_corpus/results.json"),
    }
    checks = report["checks"]
    ck = {
        "checkpoint_id": "w036-classsep-disj-rule-ckpt-20260912T0050",
        "task_id": report["task_id"],
        "actor": "worker-036",
        "instance": INSTANCE,
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_id": "A1",
        "gate": "G-AUDIT/G-CLASSBIND",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": report["class_ids"],
        "authority_note": "Worker checkpoint only. No gate verdict, no node status, no canonical artifact or registry modified. A message is not a result until the controller applies it and records the artifact hash.",
        "deliverable": "Staged, measured container-disjunction rule (R5) for research_map/class_separation.py + pre-registered fixture battery + live blast-radius counterfactual.",
        "artifacts": artifacts,
        "inputs_pinned_full_sha256": inputs,
        "result": {
            "overall": report["overall"],
            "checks_passed": sum(1 for c in checks if c["ok"]),
            "checks_total": len(checks),
            "probe_exit_expected": 0,
            "candidate_sha256": report["candidate_sha256"],
            "canonical_sha256": report["canonical_sha256"],
            "map_snapshot_sha256": report["snapshot_map_sha256"],
            "map_canonical_findings": report["map_counterfactual"]["canonical_total"],
            "map_candidate_findings": report["map_counterfactual"]["candidate_total"],
            "map_added": len(report["map_counterfactual"]["added"]),
            "map_removed": len(report["map_counterfactual"]["removed"]),
            "map_added_by_surface": report["map_counterfactual"]["added_by_surface"],
            "map_added_by_class_count": report["map_counterfactual"]["added_by_distinct_class_count"],
            "ledger_disj_rows": {k: v["candidate_disj_rows"] for k, v in report["ledger_counterfactual"].items()},
            "ledger_canonical_disj_rows": {k: v["canonical_disj_rows"] for k, v in report["ledger_counterfactual"].items()},
            "worker_07_regression_canonical": report["corpus_regression"]["worker_07"],
            "worker_07_regression_candidate": report["corpus_regression"]["worker_07_candidate"],
            "worker_027_ood_unchanged": (report["corpus_regression"]["worker_027_ood"] or {}).get("unchanged"),
        },
        "limitations": report["limitations"],
        "next_falsifier": "Re-run probe_disj_rule.py at the pinned snapshots: falsified if any check fails (positive fixture unflagged, negative flagged, any added map finding not 'container disjoins', any of the 8 ledger rows missed on any pinned revision, corpus fixture changing classification, reverse-apply not reproducing canonical, inert/overfire controls off, or any measured input drifting). Live application additionally requires a rebase if research_map/class_separation.py has moved off c266dbceca87, and an owner decision on the surface/cardinality policy for the 100 map containers.",
    }
    out = json.dumps(ck, indent=1) + "\n"
    (HERE / "CHECKPOINT.json").write_text(out)
    state = ROOT / "runtime/state" / "w036_classsep_disj_rule_checkpoint_20260912T0050.json"
    state.write_text(out)
    print(json.dumps({"checkpoint": rel(HERE / "CHECKPOINT.json"), "state_copy": rel(state),
                      "artifacts": len(artifacts), "overall": ck["result"]["overall"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
