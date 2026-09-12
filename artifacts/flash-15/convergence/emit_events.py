#!/usr/bin/env python3
"""Append worker-15 convergence-15 events to the outbox (idempotent by event_id).

Writes only to comms/outbox/deepseek-flash-15.jsonl. Does not ingest or touch the map.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms/outbox/deepseek-flash-15.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ACTOR = "deepseek-flash-15"

# path -> (event_id, artifact_type, node_id)
ARTIFACTS = {
    "reviews/convergence-15.json": ("w15-conv-artifact-review-20260912T0013", "review_verdict", "A1"),
    "artifacts/flash-15/convergence/divergence_check.json": ("w15-conv-artifact-divergence-20260912T0013", "gate_evidence", "A1"),
    "artifacts/flash-15/convergence/gate_run_canonical_rev3.txt": ("w15-conv-artifact-gatelog-canonical-20260912T0013", "gate_evidence", "A1"),
    "artifacts/flash-15/convergence/gate_run_frozen_rev8.txt": ("w15-conv-artifact-gatelog-frozen-20260912T0013", "gate_evidence", "A1"),
    "artifacts/flash-15/convergence/leakage_scan_canonical_rev3.json": ("w15-conv-artifact-leakage-20260912T0013", "gate_evidence", "A1"),
    "artifacts/flash-15/checkpoints/checkpoint-07.json": ("w15-conv-artifact-checkpoint-20260912T0013", "checkpoint", "A1"),
}


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main() -> int:
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                continue

    events = []

    for path, (eid, atype, node) in ARTIFACTS.items():
        events.append({
            "event_id": eid,
            "event_type": "artifact",
            "created_at": NOW,
            "actor": ACTOR,
            "node_id": node,
            "group_id": "audit",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "artifact_type": atype,
            "path": path,
            "sha256": sha(path),
            "validation_status": "unverified",
            "assignment_ref": "astra-conv-05",
            "evidence_refs": [f"{path}#{sha(path)[:12]}"],
        })

    review_sha = sha("reviews/convergence-15.json")
    findings = [
        "B1 [B, missing required field]: extension_predicate is referenced at lines 75-76 (D3.definition_ref) and 209 (conclusion.statement_formal) but no such top-level key exists at the reviewed hash (4 token occurrences, 0 definitions).",
        "B2 [B, ambiguous quantifier]: conclusion.statement_formal (209) reads 'forall (s,delta) in D0, forall D in D_gen^{s,delta}' while only D1-D3 are defined and D_gen carries no (s,delta) superscript; contradicts quantifiers.formal (52) and the revision's own binding_note (25) claiming the disjunctive domain was removed.",
        "B3 [B, frozen-gate conformance]: check_class_schema.py (sha 000e09e4) exits 1 on the reviewed hash: R17, R18, R19, R22, R27. R27 is a lexical false-negative (the exists-G quantifier IS stated at line 52); R17-R19/R22 are real absences. The file binds spec v1.1 while the frozen spec/tool are later revisions.",
        "N1 [N]: tier_1.machine_checkable_steps (279-285) overstates machine-checkability (sampled C2 checks, isometry onto an open proper subset, future-point condition).",
        "N2 [N]: citation_status: verified (49, 327) coexists with three unresolved_citations (357-369); scope the token.",
        "N3 [N]: excluded_set (155) names type-II critical-collapse threshold data inside a block declared vacuum-specific (172); name the model or move to neighbouring_class_facts.",
        "N4 [N]: conclusion_type duplicated at 42 and 205; add a gate equality check or a single source.",
        "N5 [N]: declared created_at/revised_at (23:45/23:50) postdate the file mtime (23:38:01); do not order by declared clocks.",
        "N6 [N]: review_history (371-395) still lists revision 3 as pending; owner should record this verdict.",
        "B-G1 [gate-scope B]: the published canonical artifact (schemas/af_scc_c2_vacuum.yaml, 23fec0e9, rev3, FAILS the frozen gate) and the FROZEN.json rev19 entry (artifacts/formulation/schemas/af_scc_c2_vacuum.yaml, e9fcefe6, rev8, PASSES) are different files; P5 mirror violated, no single hash both passes and is reviewed.",
        "B-G2 [gate-scope B, frozen copy]: the frozen copy reintroduces the family-of-statements quantifier (D0 = 'admissible regularity pairs: Sobolev s>2.5 and delta in (0.5,1), or the smooth-with-decay default'; formal ranging 'forall (s,delta) in D0') that lead-audit reopened rev2 for; the lexical gate passes it, so this is a semantic escape.",
        "G-3 [gate-scope N]: F2b data-class mismatch (line 133) is recorded by peers 17/18 as a G-FORM blocker; cited, not re-derived here.",
    ]
    events.append({
        "event_id": "w15-conv-review-20260912T0013",
        "event_type": "review",
        "created_at": NOW,
        "actor": ACTOR,
        "reviewer": ACTOR,
        "target_id": "AF-SCC-C2-VAC-GEN",
        "target_subnode": "F2a",
        "node_id": "A1",
        "group_id": "audit",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-AUDIT",
        "assignment_ref": "astra-conv-05",
        "verdict": "revise",
        "score": 3.0,
        "target_hash_cited_in_artifact": "23fec0e9cd68bc99d42f2fa2228f343391df70d802ae50ba368c1e70d96e0f9d",
        "frozen_manifest_hash_not_reviewed": "e9fcefe6e59555ba210d1440e5a0a5d4659cf7e6a859b63b60fda8b4066cbcb0",
        "hard_failures": [findings[0], findings[1], findings[2], findings[9], findings[10]],
        "findings": findings,
        "summary": "P2 triage, one verdict on the published canonical C2 hash 23fec0e9 (rev3). Prior round 9/9 hard failures resolved at this hash; leakage and inflation clean. Verdict revise driven by 3 artifact-level B findings (dangling extension_predicate, undefined domains in conclusion.statement_formal, frozen gate rejection) and 2 gate-scope B findings: the canonical published file and the FROZEN.json rev19 entry are different artifacts (P5 breach), and the frozen copy reintroduces the previously-adjudicated disjunctive regularity-pair quantifier while passing the lexical gate. Remedy is a publish + re-bind, not another rewrite loop.",
        "artifact_refs": [f"reviews/convergence-15.json#{review_sha[:12]}"],
        "evidence_refs": [
            "schemas/af_scc_c2_vacuum.yaml#23fec0e9cd68",
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#e9fcefe6e595",
            "artifacts/formulation/FROZEN.json#da6a0ee9f2f6",
            "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f",
            f"artifacts/flash-15/convergence/divergence_check.json#{sha('artifacts/flash-15/convergence/divergence_check.json')[:12]}",
            f"artifacts/flash-15/convergence/gate_run_canonical_rev3.txt#{sha('artifacts/flash-15/convergence/gate_run_canonical_rev3.txt')[:12]}",
            f"artifacts/flash-15/convergence/gate_run_frozen_rev8.txt#{sha('artifacts/flash-15/convergence/gate_run_frozen_rev8.txt')[:12]}",
        ],
        "next_falsifier": "On one published canonical hash equal to the FROZEN.json entry: extension_predicate present and resolved; no undefined domain in conclusion.statement_formal; frozen gate exits 0; a YAML parse shows a single regularity setting (no (s,delta) family); and >=1 A1 verdict cites that hash.",
        "hours": 0.5,
    })

    events.append({
        "event_id": "w15-conv-status-20260912T0013",
        "event_type": "status",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": "A1",
        "group_id": "audit",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-AUDIT",
        "assignment_id": "astra-conv-05",
        "status": "active",
        "hours": 0.5,
        "summary": "convergence-15 delivered: B/N triage of F2a at published canonical sha 23fec0e9 (rev3). 3 B + 6 N artifact-level, 2 B + 1 N gate-scope. Prior round 9/9 hard failures resolved at this hash; no repeated finding charged as B. Key gate blocker: canonical published hash FAILS the frozen gate while the FROZEN.json rev19 entry PASSES but is a different file at a non-canonical path and reintroduces the disjunctive regularity-pair quantifier (D0) that reopened rev2. Recommend: one publish of gate-passing content with the single frozen data class restored, then re-bind one A1 verdict; do not start another rewrite loop.",
        "artifact_refs": [f"reviews/convergence-15.json#{review_sha[:12]}"],
        "evidence_refs": [
            "schemas/af_scc_c2_vacuum.yaml#23fec0e9cd68",
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#e9fcefe6e595",
            "artifacts/formulation/FROZEN.json#da6a0ee9f2f6",
            f"artifacts/flash-15/checkpoints/checkpoint-07.json#{sha('artifacts/flash-15/checkpoints/checkpoint-07.json')[:12]}",
        ],
        "next_falsifier": "sha256(schemas/af_scc_c2_vacuum.yaml) == FROZEN.json entry for AF-SCC-C2-VAC-GEN, that hash passes check_class_schema.py, a YAML parse shows one regularity setting, and an A1 verdict cites it.",
        "no_completion_claimed": True,
    })

    appended = 0
    with OUTBOX.open("a") as fh:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
            appended += 1
    print(f"appended {appended} events (of {len(events)}) to {OUTBOX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
