#!/usr/bin/env python3
"""Emit worker-067 upward events for W067-N0-PROVENANCE-DRIFT-LEDGER-01.

Idempotent: re-running skips event_ids already present in comms/outbox/worker-067.jsonl.
Worker events are advisory: no gate verdict, no node status, no validation_status=passed.
"""
import datetime
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUTBOX = os.path.join(REPO, "comms", "outbox", "worker-067.jsonl")
LEDGER = os.path.join(HERE, "ledger.json")
SCRIPT = os.path.join(HERE, "check_provenance.py")
README = os.path.join(HERE, "README.md")
CHECKPOINT = os.path.join(REPO, "runtime", "state", "worker-067_checkpoint_7.json")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def existing_ids():
    ids = set()
    if os.path.isfile(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["event_id"])
            except Exception:
                pass
    return ids


def main():
    led = json.load(open(LEDGER, encoding="utf-8"))
    h = {p: sha(p) for p in (LEDGER, SCRIPT, README, CHECKPOINT)}
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    ev = [
        {
            "event_id": "w067-provledger-%s-00-take" % stamp,
            "event_type": "status", "created_at": now, "actor": "worker-067",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
            "status": "active", "hours": 0.1,
            "summary": ("No worker-067 inbox assignment (fleet 2026-09-12T00:47). Took ONE bounded "
                        "class-bound task W067-N0-PROVENANCE-DRIFT-LEDGER-01: independent read-only "
                        "measured census of every path->sha256 binding and every explicit "
                        "*_matches_on_disk assertion reachable from the live N0/G-NUM acceptance chain "
                        "(proposal evidence_hashes, replication verdict, certification, protocol inline "
                        "refs), to support astra-life04-n0-verify. No canonical writes."),
            "evidence_refs": ["research_map/research_map.json#controller_gate_audit.G-NUM",
                              "runtime/state/controller_verification/lifecycle_20260912-004844.json"],
            "next_falsifier": led["next_falsifier"],
        },
        {
            "event_id": "w067-provledger-%s-10-art-script" % stamp,
            "event_type": "artifact", "created_at": now, "actor": "worker-067",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
            "artifact_type": "deterministic_provenance_ledger_instrument",
            "path": "artifacts/worker-067/n0_provenance_ledger/check_provenance.py",
            "sha256": h[SCRIPT], "validation_status": "unverified",
            "summary": "Read-only checker: parses declared (path, expected-hash) pairs + 4 explicit provenance booleans, measures live bytes, 7 fail-closed controls, exit 2 on drift/control failure.",
            "evidence_refs": ["artifacts/worker-067/n0_provenance_ledger/check_provenance.py#" + h[SCRIPT][:12]],
            "next_falsifier": led["next_falsifier"],
        },
        {
            "event_id": "w067-provledger-%s-11-art-ledger" % stamp,
            "event_type": "artifact", "created_at": now, "actor": "worker-067",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
            "artifact_type": "provenance_drift_ledger",
            "path": "artifacts/worker-067/n0_provenance_ledger/ledger.json",
            "sha256": h[LEDGER], "validation_status": "unverified",
            "summary": ("verdict=%s; 39 bindings (33 MATCH / 6 STALE / 0 MISSING; 5 stale already "
                        "recorded as drift, 1 excluded-by-source); 4 provenance assertions (3 AGREE, "
                        "1 CONTRADICTS: fixed_replication_verdict.json L31 declares "
                        "fixed_taxonomy_sha256_matches_on_disk=true while L7/L39 pin superseded rev2 "
                        "66bf917b vs live rev5 0abb9ed8); anchors b4192221ff7d / dcad962324e3 / "
                        "1677822ceb9c / 1e6cdf04d7a2 stable before+after; controls 7/7." % led["verdict"]),
            "evidence_refs": ["artifacts/worker-067/n0_provenance_ledger/ledger.json#" + h[LEDGER][:12],
                              "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                              "numerics/protocol/fixed_replication_verdict.json#dcad962324e3"],
            "next_falsifier": led["next_falsifier"],
        },
        {
            "event_id": "w067-provledger-%s-12-art-readme" % stamp,
            "event_type": "artifact", "created_at": now, "actor": "worker-067",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
            "artifact_type": "method_and_findings_note",
            "path": "artifacts/worker-067/n0_provenance_ledger/README.md",
            "sha256": h[README], "validation_status": "unverified",
            "summary": "Per-binding table, result, significance/scope, minimal repair recommendation (owner astra-lead-numerics), reproduction, falsifier, non-claims.",
            "evidence_refs": ["artifacts/worker-067/n0_provenance_ledger/ledger.json#" + h[LEDGER][:12]],
            "next_falsifier": led["next_falsifier"],
        },
        {
            "event_id": "w067-provledger-%s-20-review" % stamp,
            "event_type": "review", "created_at": now, "actor": "worker-067",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH", "class_ids": ["AF-WCC-SCALAR-SPH"],
            "gate": "G-NUM", "verdict": "revise", "score": 3.5, "counts_as_full_schema_verdict": False,
            "counts_as_independent_second_verdict": False,
            "authority_note": "Worker review event: advisory; does not set status=done, validation_status=passed, or any gate verdict. Lead-audit owns astra-life04-n0-verify.",
            "findings": [
                "F1 (measured, self-consistency): numerics/protocol/fixed_replication_verdict.json#dcad962324e3 L31 declares fixed_taxonomy_sha256_matches_on_disk=true while its own chained pin L7 and provenance L39 hold superseded F0 rev2 66bf917bd368; live research_map/formulation_taxonomy.yaml measures rev5 0abb9ed8a961. The declared boolean is CONTRADICTED by the bytes. The three sibling booleans (fixed_json L29, harness L26, script L30) and 33/39 bindings MATCH.",
                "F2 (scope, not a hard failure): the contradicted boolean is provenance-only. The verdict's q1/q2 scheme-independence numbers and the certified orders do not reference the taxonomy pin (binding_status=PROVISIONAL; proposal class_binding_note declares the F0 binding not load-bearing for the order claim), and the same rev2-pin drift is already recorded in numerics/results/flat_wave_convergence_rev3.json L137/L140, numerics/protocol/scheme_independence_review.md L272 and numerics/blockers.md item 5. No measured number changes.",
                "F3 (residual, owner astra-lead-numerics; CF-12 one canonical path/one owner): minimal repair is to set L7 and L39 to the measured rev5 hash and re-evaluate L31. Until then the artifact asserts a false matches_on_disk value and is cited in the N0 acceptance chain (n0_gate_proposal.evidence_hashes L321) and in the independent-replication stop-rule item.",
                "P1-P3: anchor stability C6, read-only proof C7 across every swept byte, and detector controls C3/C5 all pass; the two prior worker-067 findings (protocol section 3.4 scoping F1, reader-side key-convention binding) are not re-litigated here.",
            ],
            "hard_failures": [],
            "independence_limits": "Bounded breadth worker; author of no numerics/N0 canonical artifact and of no reviewed file; read-only on every canonical path; wrote only under artifacts/worker-067/ and runtime/state/worker-067_checkpoint_7.json. This review does not accept or reject N0 or G-NUM.",
            "evidence_refs": [
                "artifacts/worker-067/n0_provenance_ledger/ledger.json#" + h[LEDGER][:12],
                "artifacts/worker-067/n0_provenance_ledger/check_provenance.py#" + h[SCRIPT][:12],
                "artifacts/worker-067/n0_provenance_ledger/README.md#" + h[README][:12],
                "numerics/protocol/fixed_replication_verdict.json#dcad962324e3",
                "numerics/tests/n0_gate_proposal.json#b4192221ff7d",
                "numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c",
                "numerics/CONVERGENCE_PROTOCOL.md#1e6cdf04d7a2",
                "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                "numerics/results/flat_wave_convergence_rev3.json",
                "numerics/blockers.md",
            ],
            "next_falsifier": led["next_falsifier"],
        },
        {
            "event_id": "w067-provledger-%s-99-complete" % stamp,
            "event_type": "status", "created_at": now, "actor": "worker-067",
            "node_id": "N0", "class_id": "AF-WCC-SCALAR-SPH", "gate": "G-NUM",
            "status": "active", "hours": 0.5,
            "summary": ("W067-N0-PROVENANCE-DRIFT-LEDGER-01 complete at worker level: "
                        "LEDGER_COMPLETE_WITH_CONTRADICTED_ASSERTION, 7/7 controls, 0 canonical writes, "
                        "checkpoint runtime/state/worker-067_checkpoint_7.json. The N0 chain has exactly "
                        "one unrecorded-as-written defect: a false matches_on_disk assertion in "
                        "fixed_replication_verdict.json; all other stale pins are already recorded drift "
                        "or excluded-by-source, and no certified number is affected. This is a completion "
                        "claim for the task, not a node transition and not a gate verdict; N0 stays active "
                        "and numerics_lock stays LOCKED."),
            "evidence_refs": [
                "artifacts/worker-067/n0_provenance_ledger/ledger.json#" + h[LEDGER][:12],
                "artifacts/worker-067/n0_provenance_ledger/check_provenance.py#" + h[SCRIPT][:12],
                "artifacts/worker-067/n0_provenance_ledger/README.md#" + h[README][:12],
                "runtime/state/worker-067_checkpoint_7.json#" + h[CHECKPOINT][:12],
            ],
            "next_falsifier": led["next_falsifier"],
        },
    ]
    have = existing_ids()
    appended = 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in ev:
            if e["event_id"] in have:
                continue
            fh.write(json.dumps(e, sort_keys=True) + "\n")
            appended += 1
    print(json.dumps({"appended": appended, "skipped_existing": len(ev) - appended,
                      "outbox": OUTBOX, "ledger_sha256": h[LEDGER],
                      "checkpoint_sha256": h[CHECKPOINT]}, indent=1))


if __name__ == "__main__":
    main()
