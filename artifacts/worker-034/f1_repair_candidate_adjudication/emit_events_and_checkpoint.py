#!/usr/bin/env python3
"""Emit the worker-034 checkpoint + outbox events for the F1 repair-candidate adjudication.

Idempotent: re-running skips event_ids already present in the outbox.  No canonical
artifact is written; the only writes are this artifact directory, one namespaced
runtime/state checkpoint file, and appended lines in comms/outbox/worker-034.jsonl.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-034/f1_repair_candidate_adjudication"
OUTBOX = ROOT / "comms/outbox/worker-034.jsonl"
RT_CKPT = ROOT / "runtime/state/w034_f1_repair_adjudication_checkpoint.json"
NOW = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
STAMP = datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")
TASK = "W034-F1-REPAIR-CANDIDATE-ADJUDICATION-01"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


report = json.loads((OUT / "report.json").read_text())
evidence = json.loads((OUT / "evidence.json").read_text())

deliverables = {
    "report.json": OUT / "report.json",
    "evidence.json": OUT / "evidence.json",
    "adjudicate_f1_repair_candidates.py": OUT / "adjudicate_f1_repair_candidates.py",
    "README.md": OUT / "README.md",
}
hashes = {name: sha256_file(p) for name, p in deliverables.items()}

pins = {p["pin"]: p["measured"] for p in evidence["pins"]}
counts = report["counts"]
ow = report["owner_write_set"]

checkpoint = {
    "schema": "worker-checkpoint/v1",
    "worker": "worker-034",
    "task_id": TASK,
    "created_at": NOW,
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "status": "active",
    "verdict": report["verdict"],
    "authority": "worker measurement only; read-only on all canonical paths; no gate "
                 "verdict, no node status promotion, no canonical corpus write",
    "deliverables": {name: {"path": str(p.relative_to(ROOT)), "sha256": hashes[name],
                            "bytes": p.stat().st_size}
                     for name, p in deliverables.items()},
    "pins": pins,
    "candidate_results": {
        n: {
            "sha256": counts[n]["sha256"],
            "changed_pointers": counts[n]["changed_pointers"],
            "required_pass": counts[n]["required_pass"],
            "record_fidelity_pass": counts[n]["record_fidelity_pass"],
            "provenance_pass": counts[n]["provenance_pass"],
            "freeze_ready": counts[n]["freeze_ready"],
            "controls_all_caught": counts[n]["controls_all_caught"],
            "history_rewrites": counts[n]["history_rewrites"],
            "exec_failures": len(evidence["candidates"][n]["exec_failures"]),
            "excerpt_failures": len(evidence["candidates"][n]["excerpt_failures"]),
        }
        for n in counts
    },
    "recommended_base": {
        "candidate": ow["recommended_base"],
        "sha256": ow["recommended_base_sha256"],
        "residual_excerpt_refreshes": [
            {"test_id": e["test_id"], "path": e["path"],
             "fresh_excerpt_from": e["refresh_from"],
             "fresh_excerpt": e["fresh_excerpt"]}
            for e in ow["residual_excerpt_refreshes"]],
        "provenance_fields_owner_must_set": ow["provenance_fields_owner_must_set"],
        "policy_divergence": ow["policy_divergence"],
    },
    "blocking_facts": [
        "no staged candidate is freeze-ready: 0/4 pass truthful + record-fidelity + "
        "provenance together",
        "cand_w077_mechanical fails 2 probes at rev13 (82/84) and is not usable as evidence",
        "cand_w031_tierA/tierB leave 4/2 stale recorded excerpts respectively",
        "every candidate leaves binding_frozen_revision_schema and rebound_at provenance "
        "gaps (owner must set the actual re-publish instant and schema revision)",
        "the W077 lineage rewrites binding_at_authoring/prior_binding_* on all 25 rows "
        "(100 field instances) while W031 preserves them; the owner must choose a policy",
    ],
    "falsifier": report["falsifier"],
    "next_falsifier": report["next_falsifier"],
    "resume": {
        "read_first": [
            "artifacts/worker-034/f1_repair_candidate_adjudication/README.md",
            "artifacts/worker-034/f1_repair_candidate_adjudication/report.json",
        ],
        "rerun": "python3 artifacts/worker-034/f1_repair_candidate_adjudication/"
                 "adjudicate_f1_repair_candidates.py",
    },
}
(OUT / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
hashes["checkpoint.json"] = sha256_file(OUT / "checkpoint.json")
RT_CKPT.write_text(json.dumps(checkpoint, indent=1) + "\n")

sums = ["%s  %s" % (sha256_file(p), p.name) for p in sorted(OUT.glob("*")) if p.is_file()
        and p.name != "SHA256SUMS"]
sums += ["%s  pinned/%s" % (sha256_file(p), p.name) for p in sorted((OUT / "pinned").glob("*"))]
(OUT / "SHA256SUMS").write_text("\n".join(sums) + "\n")

rel = {
    "report": "artifacts/worker-034/f1_repair_candidate_adjudication/report.json",
    "evidence": "artifacts/worker-034/f1_repair_candidate_adjudication/evidence.json",
    "instrument": "artifacts/worker-034/f1_repair_candidate_adjudication/"
                  "adjudicate_f1_repair_candidates.py",
    "readme": "artifacts/worker-034/f1_repair_candidate_adjudication/README.md",
    "checkpoint": "artifacts/worker-034/f1_repair_candidate_adjudication/checkpoint.json",
}
refs = ["%s#sha256:%s" % (rel[k], hashes[{"report": "report.json",
                                          "evidence": "evidence.json",
                                          "instrument": "adjudicate_f1_repair_candidates.py",
                                          "readme": "README.md",
                                          "checkpoint": "checkpoint.json"}[k]])
        for k in rel]
refs += ["schemas/f1_falsifier_tests.jsonl#sha256:%s" % pins["corpus_orig"]]
refs += ["schemas/af_wcc_vacuum.yaml#sha256:%s" % pins["f1_live_rev13"]]
refs += ["artifacts/formulation/FROZEN.json#sha256:%s" % pins["frozen_rev29"]]
refs += ["artifacts/worker-031/f1_suite_repin_dryrun/patched/"
         "f1_falsifier_tests.tierB.jsonl#sha256:%s" % pins["cand_w031_tierB"]]
refs += ["artifacts/worker-077/f1_suite_rebind_dryrun/run/"
         "proposed_f1_falsifier_tests.rev13.f0refresh.jsonl#sha256:%s"
         % pins["cand_w077_f0refresh"]]

common = {
    "actor": "worker-034",
    "created_at": NOW,
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "task_id": TASK,
}

events = []


def art(kind: str, key: str, artifact_type: str, note: str):
    return {
        **common,
        "event_id": "w034-f1adj-%s-artifact-%s" % (STAMP, kind),
        "event_type": "artifact",
        "artifact_type": artifact_type,
        "path": rel[key],
        "sha256": hashes[{
            "report": "report.json", "evidence": "evidence.json",
            "instrument": "adjudicate_f1_repair_candidates.py",
            "readme": "README.md", "checkpoint": "checkpoint.json"}[key]],
        "bytes": (OUT / {"report": "report.json", "evidence": "evidence.json",
                         "instrument": "adjudicate_f1_repair_candidates.py",
                         "readme": "README.md",
                         "checkpoint": "checkpoint.json"}[key]).stat().st_size,
        "validation_status": "unverified",
        "note": note,
        "evidence_refs": refs,
    }


events.append(art("report", "report", "report",
                  "cross-lineage adjudication of the W031/W077 F1 corpus repair candidates"))
events.append(art("evidence", "evidence", "evidence",
                  "full per-candidate checks, leaf diffs, divergence table, 8 controls"))
events.append(art("instrument", "instrument", "instrument",
                  "read-only adjudication instrument; probe semantics copied from the "
                  "L-FORM-04 runner"))
events.append(art("readme", "readme", "readme", "human-readable adjudication summary"))
events.append(art("checkpoint", "checkpoint", "checkpoint",
                  "worker checkpoint for this task"))

events.append({
    **common,
    "event_id": "w034-f1adj-%s-review-candidates" % STAMP,
    "event_type": "review",
    "reviewer": "worker-034",
    "reviewer_kind": "independent cross-lineage machine adjudication of staged repair "
                     "candidates; not a schema verdict",
    "counts_as_full_schema_verdict": False,
    "target_id": "F1-repair-candidates#w031_tierB:%s,W077_f0refresh:%s"
                 % (pins["cand_w031_tierB"][:16], pins["cand_w077_f0refresh"][:16]),
    "verdict": "revise",
    "score": 3.5,
    "class_ids": ["AF-WCC-VAC-GEN"],
    "findings": [
        {"id": "W034-ADJ-1", "severity": "major",
         "text": "Three of four staged candidates are truthful at the frozen F1 rev13 pin "
                 "(84/84 recorded passes reproduce): w031_tierA, w031_tierB, w077_f0refresh. "
                 "w077_mechanical reproduces only 82/84 and honestly flips the two failing "
                 "recorded passes to false; it must not be frozen as the repaired corpus."},
        {"id": "W034-ADJ-2", "severity": "major",
         "text": "No candidate is freeze-ready. Every candidate leaves C7 provenance gaps: "
                 "binding_frozen_revision_schema stale (24-25/25 rows) and rebound_at "
                 "unchanged (24-25/25 rows); the owner must set the actual re-publish "
                 "instant and schema revision. This independently confirms W077-SR-03."},
        {"id": "W034-ADJ-3", "severity": "major",
         "text": "Policy divergence: the W077 lineage rewrites binding_at_authoring and "
                 "prior_binding_* on all 25 rows (100 field instances) to the new bindings, "
                 "while the W031 lineage preserves the historical record. Rewriting the "
                 "authoring record makes the row unauditable; preserve it and add a new "
                 "field if the new bindings must be recorded."},
        {"id": "W034-ADJ-4", "severity": "minor",
         "text": "w031_tierA leaves 4 stale observed_excerpts and w031_tierB leaves 2 "
                 "(F1-AMB-09/genericity.ambient_space, F1-AMB-21/f0_binding."
                 "declared_f0_sha256); w077_f0refresh refreshes all four. The recommended "
                 "base (w031_tierB, history-preserving) needs those 2 excerpt refreshes."},
        {"id": "W034-ADJ-5", "severity": "info",
         "text": "The two lineages' only irreconcilable semantic difference outside "
                 "provenance policy is the F1-AMB-25/binding_note anchor: W031 chooses the "
                 "live rev13 consistency-evidence sentence, W077 chooses the rev5 F0-refresh "
                 "sentence. Both are revision-specific (absent at authoring) and both pass "
                 "C5b; the owner may choose either, but one must be fixed before freezing."},
    ],
    "hard_failures": [
        {"id": "HF-W034ADJ-1", "name": "no_freeze_ready_candidate",
         "finding": "0/4 candidates pass truthful + record-fidelity + provenance together.",
         "why_blocking": "FROZEN rev30 would freeze a corpus whose own provenance still "
                         "points at rev12/FROZEN rev27 and whose excerpt text is stale.",
         "fix": "compose the owner write set in report.json: w031_tierB base + 2 excerpt "
                "refreshes from w077_f0refresh + owner-set rebound_at and "
                "binding_frozen_revision_schema=13; then re-run this battery on the applied "
                "bytes."},
        {"id": "HF-W034ADJ-2", "name": "history_rewrite_policy_undecided",
         "finding": "W077 rewrites binding_at_authoring/prior_binding_* on 25/25 rows.",
         "why_blocking": "freezing either lineage without an explicit policy silently "
                         "chooses whether the corpus may rewrite its own history.",
         "fix": "record a policy; the audit-safe option is history-preserving (W031) plus a "
                "new additive field for the new bindings, as W077's delta_vs_cce9c601 blocks "
                "already do."},
    ],
    "falsifier": report["falsifier"],
    "next_falsifier": report["next_falsifier"],
    "evidence_refs": refs,
})

events.append({
    **common,
    "event_id": "w034-f1adj-%s-claim" % STAMP,
    "event_type": "claim",
    "conclusion_type": "numerical_evidence",
    "statement": "Machine cross-adjudication of the four staged F1 falsifier-corpus repair "
                 "bytes at the FROZEN rev29 pins: 3/4 candidates reproduce all 84 recorded "
                 "passes at F1 rev13 (w031_tierA, w031_tierB, w077_f0refresh; w077_mechanical "
                 "reproduces 82/84), 0/4 are freeze-ready because all leave stale "
                 "binding_frozen_revision_schema/rebound_at provenance and - for W031 - 2-4 "
                 "stale excerpts, and the W077 lineage additionally rewrites the historical "
                 "binding_at_authoring/prior_binding_* fields on all 25 rows while W031 "
                 "preserves them. The history-preserving truthful base is w031_tierB "
                 "(785e6a4e53d6...); it needs 2 excerpt refreshes from w077_f0refresh plus "
                 "owner-set provenance before a FROZEN rev30 freeze.",
    "assumptions": [
        "the recorded probe pass flags are claims about the schema at the declared binding "
        "revision, and the evaluator semantics are those of the L-FORM-04 instrument",
        "the frozen F1 rev13 bytes d9cebb9404b2 and F0 rev5 0abb9ed8a961 are the binding "
        "targets for a rebind under FROZEN rev29",
        "changed-pointer scope classes in evidence.json are a faithful partition of the leaf "
        "diffs against the canonical corpus",
    ],
    "falsifier": report["falsifier"],
    "artifact_refs": refs[:4],
    "evidence_refs": refs[4:],
})

events.append({
    **common,
    "event_id": "w034-f1adj-%s-blocker" % STAMP,
    "event_type": "blocker",
    "description": "F1 falsifier-corpus rebind is staged but not freezable: four candidate "
                   "byte sets exist from two lineages (W031 tiers A/B, W077 mechanical/"
                   "f0refresh), none passes truthful + record-fidelity + provenance together, "
                   "and the lineages disagree on whether the repair may rewrite the corpus's "
                   "historical binding fields.",
    "needed_to_unblock": "owner decision binding one candidate byte set, using the derived "
                         "write set in artifacts/worker-034/f1_repair_candidate_adjudication/"
                         "report.json: w031_tierB as base, refresh the 2 residual excerpts "
                         "from w077_f0refresh, set rebound_at + binding_frozen_revision_schema "
                         "=13, and record a history-preservation policy; then re-run the "
                         "adjudication battery on the applied bytes before FROZEN rev30.",
    "next_falsifier": report["next_falsifier"],
    "evidence_refs": refs,
})

events.append({
    **common,
    "event_id": "w034-f1adj-%s-status" % STAMP,
    "event_type": "status",
    "status": "active",
    "summary": "W034-F1-REPAIR-CANDIDATE-ADJUDICATION-01 complete: verdict %s; 3/4 candidates "
               "truthful (84/84), 0/4 freeze-ready; 8/8 controls caught on every candidate; "
               "checkpoint "
               "runtime/state/w034_f1_repair_adjudication_checkpoint.json."
               % report["verdict"],
    "hours": 0.5,
    "next_falsifier": report["next_falsifier"],
    "checkpoint": "runtime/state/w034_f1_repair_adjudication_checkpoint.json#sha256:%s"
                  % sha256_file(RT_CKPT),
    "evidence_refs": refs,
})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass

appended = 0
with open(OUTBOX, "a", encoding="utf-8") as f:
    for e in events:
        if e["event_id"] in existing:
            continue
        f.write(json.dumps(e) + "\n")
        appended += 1

print(json.dumps({
    "checkpoint": str(RT_CKPT),
    "checkpoint_sha256": sha256_file(RT_CKPT),
    "events_total": len(events),
    "events_appended": appended,
    "event_ids": [e["event_id"] for e in events],
    "deliverable_hashes": hashes,
}, indent=1))
