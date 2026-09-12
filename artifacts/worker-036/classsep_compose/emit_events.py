#!/usr/bin/env python3
"""Emit the W036-CLASSSEP-COMPOSE-01 upward events (append-only) and validate them.

Writes: comms/outbox/worker-036.jsonl (append) and a local copy under this directory.
Every event is one JSON object per line with event_id / event_type / created_at / actor.

Class-binding discipline: events carry a *singular* class_id (AF-SCC-C0-VAC-GEN); the four
frozen classes are declared in the non-scanned `scope_classes` field, never as a `class_ids`
container — so the packet does not itself exhibit the disjunction shape it measures.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-036.jsonl"
LOCAL = HERE / "events_w036_compose.jsonl"

REQUIRED = {
    "status": ("event_id", "event_type", "created_at", "actor", "node_id", "status"),
    "artifact": ("event_id", "event_type", "created_at", "actor", "node_id", "path", "sha256",
                 "validation_status"),
    "claim": ("event_id", "event_type", "created_at", "actor", "class_id", "statement",
              "conclusion_type", "assumptions", "falsifier", "evidence_refs"),
}


def h(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate(events: list) -> list:
    problems = []
    ids = set()
    for e in events:
        eid = e.get("event_id")
        if eid in ids:
            problems.append(f"duplicate event_id {eid}")
        ids.add(eid)
        for k in REQUIRED[e["event_type"]]:
            if k not in e or e[k] in (None, "", []):
                problems.append(f"{eid}: missing {k}")
        if e["event_type"] == "claim":
            if e.get("conclusion_type") == "theorem" and not e.get("artifact_refs"):
                problems.append(f"{eid}: theorem without artifact_refs")
            if e.get("class_ids"):
                problems.append(f"{eid}: claim carries a class_ids container (class-binding discipline)")
        try:
            json.dumps(e)
        except TypeError as exc:  # pragma: no cover
            problems.append(f"{eid}: not JSON-serializable: {exc}")
    return problems


def main() -> int:
    ck = json.loads((HERE / "CHECKPOINT.json").read_text())
    r = ck["result"]
    rep_sha = ck["artifacts"]["artifacts/worker-036/classsep_compose/report.json"]
    ck_sha = h(HERE / "CHECKPOINT.json")
    build_sha = ck["artifacts"]["artifacts/worker-036/classsep_compose/candidate_build.json"]
    fx_sha = ck["artifacts"]["artifacts/worker-036/classsep_compose/fixtures/compose_fixtures.jsonl"]
    probe_sha = ck["artifacts"]["artifacts/worker-036/classsep_compose/probe_compose.py"]
    pr0 = r["composed_c0_sha256"]
    pr1 = r["composed_c1_sha256"]
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    base = "w036-compose-20260912T010500"
    scope = ck["scope_classes"]
    evidence = [
        f"artifacts/worker-036/classsep_compose/report.json#{rep_sha[:12]}",
        f"artifacts/worker-036/classsep_compose/CHECKPOINT.json#{ck_sha[:12]}",
        f"artifacts/worker-036/classsep_compose/candidate_build.json#{build_sha[:12]}",
        "research_map/class_separation.py#c266dbceca87",
        "research_map/class_separation.py#a8c04fc31e4a",
        "proposed/class_separation.py#e2d24b927ee8",
        "artifacts/worker-036/classsep_disj_rule/candidate_class_separation.py#1bc87c9542ed",
        "artifacts/worker-085/candidate_diff/report.json#439822557fd9",
        "artifacts/worker-07/class_separation_falsification/results.json#d69ad58468be",
        "research_map/research_map.json#ed28b714464e",
        "ledger/theorems.jsonl#a1674f094979",
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
            "scope_classes": scope,
            "status": "active",
            "hours": 0.1,
            "summary": ("Took ONE class-bound task (no inbox card for worker-036; self-selected from the open "
                        "astra-life05-classsep-calibration adjudication): W036-CLASSSEP-COMPOSE-01 — measure whether "
                        "the two staged class-separation candidates (prose-precision e2d24b927ee8 and container-recall "
                        "1bc87c9542ed) compose mechanically and behave additively, on the pinned base c266dbceca87 and "
                        "rebased onto the live canonical a8c04fc31e4a that moved mid-lifecycle. Worker evidence only; "
                        "no gate verdict, no node done, no canonical patch applied."),
            "evidence_refs": evidence[:1],
            "next_falsifier": "Re-run build_composition.py + probe_compose.py; any of the 48 checks failing voids the completion claim.",
        },
        {
            "event_id": f"{base}-artifact",
            "event_type": "artifact",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "scope_classes": scope,
            "artifact_type": "composition_calibration_packet",
            "path": "artifacts/worker-036/classsep_compose/report.json",
            "sha256": rep_sha,
            "validation_status": "unverified",
            "note": ("Full 64-hex hashes for every deliverable and pinned input are in "
                     "artifacts/worker-036/classsep_compose/CHECKPOINT.json#%s; composed candidates "
                     "PR0=%s (C0+P+R) and PR1=%s (rebased C1+P+R); no canonical registry written."
                     % (ck_sha[:12], pr0[:12], pr1[:12])),
            "evidence_refs": [f"artifacts/worker-036/classsep_compose/report.json#{rep_sha[:12]}",
                              f"artifacts/worker-036/classsep_compose/CHECKPOINT.json#{ck_sha[:12]}",
                              f"artifacts/worker-036/classsep_compose/candidate_build.json#{build_sha[:12]}"],
            "next_falsifier": "Re-hash the report, checkpoint, build record, probe and fixtures at the pinned inputs; a mismatch voids the artifact registration.",
        },
        {
            "event_id": f"{base}-claim",
            "event_type": "claim",
            "actor": "worker-036",
            "created_at": now,
            "node_id": "A1",
            "gate": "G-AUDIT/G-CLASSBIND",
            "class_id": "AF-SCC-C0-VAC-GEN",
            "scope_classes": scope,
            "conclusion_type": "formal_model",
            "counts_as_full_schema_verdict": False,
            "statement": (
                "At the pinned hashes the two staged class-separation candidates compose mechanically and behave "
                "exactly additively. base_c0: canonical c266dbceca87 plus prose-precision e2d24b927ee8 (4 hunks) plus "
                "container-recall 1bc87c9542ed (1 hunk) yields PR0 69459628d65b with disjoint hunks, byte-exact "
                "reverse-apply, order-independent composition and composed delta equal to the union of patch deltas. "
                "On 736 measured items (worker-085's 12-case battery, the prior packet's 26-case battery, a "
                "pre-registered 12-case compose battery, 62 L0 ledger rows, and every findings_for_map element of the "
                "frozen and live map snapshots) Counter(PR) equals Counter(P)+Counter(R)-Counter(C) item-for-item: "
                "0 interactions, C0-window aggregate 48/48/383/383, C1-window aggregate 43/43/378/378. External "
                "controls reproduce worker-085's 12 recorded counts and the prior packet's 26 recorded expectations; "
                "the worker-07 27-fixture corpus stays PASS 17/0/10/0 with identical per-fixture classification under "
                "all eight revisions; null and overfire controls behave. The live canonical moved mid-lifecycle to "
                "a8c04fc31e4a (a CF-16 metalinguistic-quotation exemption); the staged patches rebase onto it with a "
                "3-way delta merge at 0 conflicts (PR1 c5d157d23823, reverse-apply exact), while a naive 2-way "
                "re-diff of either patch file onto the new canonical would revert the new canonical's own edit "
                "(prose 5 lines, container 3 lines, including the exemption block) - so adoption must rebase, not "
                "re-apply. On the live map snapshot ed28b714464e the live-base change alone removes 4 findings and "
                "adds 0; P adds 1 prose finding; R adds 208 container findings (20 two-class, 81 three-class, "
                "107 four-class); composition adds exactly 209. Therefore the two candidates are compatible for "
                "joint adoption, and the composition's live cost is dominated by the container rule's cardinality "
                "policy, which remains an owner decision. This is checker-calibration measurement evidence for the "
                "detector owner and the CLASSSEP-calibration adjudicator, not a gate verdict, node transition, "
                "mathematics or physics claim."),
            "assumptions": [
                "Canonical and staged bytes are read from hash-pinned snapshots; no canonical file is modified (CF-4: the detector owner applies checker changes).",
                "Composition is a line-level 3-way delta merge; disjointness, reverse-apply and delta-union are verified mechanically for both windows.",
                "Additivity is evaluated per measured item on exact finding multisets; an interaction would appear as Counter(PR) != Counter(P)+Counter(R)-Counter(C).",
                "The live map snapshot ed28b714464e binds the live-surface numbers; the map moves under swarm traffic and the measurement does not follow it.",
                "Worker events cannot set gate verdicts or node status; this claim supplies measurement evidence only.",
            ],
            "falsifier": (
                "Re-run build_composition.py then probe_compose.py at the pinned snapshots: falsified if any of the 48 "
                "checks fails - any window where the composition is not C+P+R (hunk conflict, rebase conflict, "
                "reverse-apply not the base, delta content not the union); any measured item where "
                "Counter(PR) != Counter(P)+Counter(R)-Counter(C); any external-control mismatch against worker-085's "
                "12 counts or the prior packet's 26 expectations; any worker-07 fixture classification change or "
                "fn>0/fp>0 under any of the 8 revisions; any live added finding not carrying 'container disjoins' (R) "
                "or not statement-mode prose (P); a null control changing any finding or an overfire control failing "
                "to break >=5 negative cases; a naive 2-way reapply of either patch file onto a8c04fc31e4a that does "
                "NOT revert the base's own edit; or any pinned input drifting mid-run. The rebase window is void if "
                "research_map/class_separation.py moves off a8c04fc31e4a."),
            "evidence_refs": evidence,
            "artifact_refs": [
                f"artifacts/worker-036/classsep_compose/report.json#{rep_sha[:12]}",
                f"artifacts/worker-036/classsep_compose/candidate_build.json#{build_sha[:12]}",
                f"artifacts/worker-036/classsep_compose/probe_compose.py#{probe_sha[:12]}",
                f"artifacts/worker-036/classsep_compose/fixtures/compose_fixtures.jsonl#{fx_sha[:12]}",
                f"artifacts/worker-036/classsep_compose/CHECKPOINT.json#{ck_sha[:12]}",
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
            "scope_classes": scope,
            "status": "active",
            "hours": 0.1,
            "summary": ("W036-CLASSSEP-COMPOSE-01 complete at worker level (one bounded class-bound task; completion "
                        "claim only, NOT a node done and NOT a gate verdict). Probe overall PASS 48/48, exit 0; "
                        "deliverables hash-pinned in CHECKPOINT.json; checkpoint mirrored to "
                        "runtime/state/w036_classsep_compose_checkpoint_20260912T010500.json. No canonical artifact, "
                        "map, gate, ledger or numerics_lock modified; no canonical patch applied. Exiting for recycling."),
            "evidence_refs": [f"artifacts/worker-036/classsep_compose/CHECKPOINT.json#{ck_sha[:12]}",
                              "runtime/state/w036_classsep_compose_checkpoint_20260912T010500.json"],
            "next_falsifier": "Re-hash the deliverables in CHECKPOINT.json; a mismatch voids the completion claim.",
        },
    ]
    problems = validate(events)
    if problems:
        print(json.dumps({"validation": "FAILED", "problems": problems}, indent=1))
        return 1
    payload = "".join(json.dumps(e, sort_keys=True) + "\n" for e in events)
    with OUTBOX.open("a") as f:
        f.write(payload)
    LOCAL.write_text(payload)
    print(json.dumps({"appended": len(events), "validation": "OK",
                      "outbox": str(OUTBOX.relative_to(ROOT)),
                      "local": str(LOCAL.relative_to(ROOT))}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
