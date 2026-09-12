#!/usr/bin/env python3
"""Worker-024 outbox emitter: validates and writes comms/outbox/worker-024.jsonl.

Every event is checked with research_map.schemas.validate_event before it is
written, so the controller's ingest cannot reject it on schema grounds. Run from
the repo root:
    python3 artifacts/worker-024/f2b_rev29_repair/emit_events_024.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

# As-emitted timestamp. The outbox file was written at 01:08:17 and the wall clock read
# 01:08:43 when the run was audited, so these six carry a created_at ~100 s in the future.
# That clock slip is recorded by ERRATUM below rather than silently rewritten here, so this
# emitter stays byte-faithful to what was actually ingested (see the snapshot it writes).
TS = "2026-09-12T01:10:00+08:00"
ERRATUM_TS = "2026-09-12T01:09:30+08:00"
ACTOR = "worker-024"
CAND = "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml"
CAND_SHA = "679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9"
REPORT = "artifacts/worker-024/f2b_rev29_repair/report.json"
REPORT_SHA = "ac31490bbc835f33cf03ac0ed386b160a7bcc023bc0f8f4d92df439d8e27c375"
BRIEF = "artifacts/worker-024/f2b_rev29_repair/vocab_token_conflict_024.json"
BRIEF_SHA = "8a62fb32151257b6415f7e22349de5278cc7aac2ef06f2b7dd5a20d34b04ed41"
F2B = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"
FROZEN = "artifacts/formulation/FROZEN.json#815e08079aef"
F0 = "research_map/formulation_taxonomy.yaml#0abb9ed8a961"
F2A = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534"

EVENTS = [
    {
        "event_id": "w024-f2b-repair-status-20260912T0110",
        "event_type": "status",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": "F2b",
        "status": "active",
        "hours": 0.75,
        "summary": (
            "F2b rev29 (b2ab6acb2bbe) blocking carriers W018-R13-F2B-B1 (line 152 denies a C2/C0 "
            "containment the artifact's own ledger asserts) and W018-R13-F2B-B2 / HF-075-F2b-LARGER "
            "(line 246 calls C2 'a strictly larger extension class' while E_C2 is the smallest "
            "extension set) were independently re-derived from the artifact bytes and repaired in an "
            "unfrozen 2-line candidate (sha256 679ab7bc8746). Verification: 19 PASS / 0 FAIL / "
            "1 ADJUDICATION; adapted worker-018 checker C17-CHAIN-DENIAL PASS, C18-TRANSFER-REASON "
            "PASS. Residual F2b blocker set after repair is D3-VOCAB-CONFLICT-ADJUDICATION only. "
            "No canonical artifact was modified; no node status, validation_status or gate verdict is "
            "claimed."
        ),
        "evidence_refs": [F2B, FROZEN, F2A, VOCAB, F0,
                          f"{CAND}#{CAND_SHA[:12]}", f"{REPORT}#{REPORT_SHA[:12]}"],
        "next_falsifier": (
            "Re-run artifacts/worker-024/f2b_rev29_repair/verify_f2b_repair_024.py: the repair claim "
            "is false if live F2b no longer measures b2ab6acb2bbe, if the containment string no "
            "longer parses to E_C0 > E_H2loc > E_{C^1,1} > E_C2, if the patch touches a third line, or "
            "if C17/C18 fail on candidate bytes 679ab7bc8746 under an independent instrument."
        ),
    },
    {
        "event_id": "w024-f2b-repair-artifact-candidate-20260912T0110",
        "event_type": "artifact",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": "F2b",
        "artifact_type": "repair_candidate_unfrozen",
        "path": CAND,
        "sha256": CAND_SHA,
        "validation_status": "unverified",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "note": (
            "Unfrozen candidate for F2b rev30; exactly lines 152 and 246 differ from rev29. Applying, "
            "re-pinning and bumping the revision is the formulation lead's action (CF-4)."
        ),
        "evidence_refs": [F2B, FROZEN],
    },
    {
        "event_id": "w024-f2b-repair-artifact-report-20260912T0110",
        "event_type": "artifact",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": "F2b",
        "artifact_type": "repair_verification_report",
        "path": REPORT,
        "sha256": REPORT_SHA,
        "validation_status": "unverified",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "evidence_refs": [CAND, F2B, FROZEN, F0, F2A, VOCAB],
    },
    {
        "event_id": "w024-f2b-repair-artifact-vocab-brief-20260912T0110",
        "event_type": "artifact",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": "F2b",
        "artifact_type": "adjudication_brief",
        "path": BRIEF,
        "sha256": BRIEF_SHA,
        "validation_status": "unverified",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "evidence_refs": [F0, VOCAB, F2B, F2A],
    },
    {
        "event_id": "w024-f2b-repair-claim-20260912T0110",
        "event_type": "claim",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "statement": (
            "The two F2b rev29 blocking carriers are wording defects confined to lines 152 and 246 and "
            "admit a 2-line repair that leaves every other field byte-identical; after that repair the "
            "only remaining F2b blocker is the gate-wide conclusion-token conflict between F0's allowed "
            "list and VOCAB_ALIASES' canonical tokens, which is not worker-fixable."
        ),
        "conclusion_type": "open_problem",
        "assumptions": [
            "The artifact bytes at b2ab6acb2bbe are the object under repair; any move voids this claim.",
            "The containment order is the artifact's own: E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2.",
            "Correcting a normative carrier must preserve its normative content (the nesting statement and the transfer ban), not delete it.",
            "The alias policy in VOCAB_ALIASES forbids alias forms in new canonical artifacts.",
        ],
        "falsifier": (
            "Any of: (a) live F2b no longer measures b2ab6acb2bbe; (b) a third line changes under the "
            "patch; (c) C17/C18 fail on candidate 679ab7bc8746 under an independent instrument; "
            "(d) a frozen adjudication shows line 152 or 246 is normative text that must be retained "
            "as written; (e) D1/D2 are shown to be non-normative prose exempt from rule_spec R06/R16."
        ),
        "evidence_refs": [F2B, FROZEN, F0, F2A, VOCAB,
                          f"{CAND}#{CAND_SHA[:12]}", f"{REPORT}#{REPORT_SHA[:12]}"],
        "artifact_refs": [f"{CAND}#{CAND_SHA[:12]}", f"{REPORT}#{REPORT_SHA[:12]}",
                          f"{BRIEF}#{BRIEF_SHA[:12]}"],
    },
    {
        "event_id": "w024-f2b-repair-blocker-d3-20260912T0110",
        "event_type": "blocker",
        "created_at": TS,
        "actor": ACTOR,
        "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "description": (
            "D3 conclusion-token conflict: F2b line 211 uses VOCAB_ALIASES canonical "
            "'scc_c0_future_inextendibility' (F2a line 209 likewise uses the C2 canonical form) while "
            "F0 field_vocabulary.conclusion_type.allowed lists only the alias forms "
            "['weak_cosmic_censorship','strong_cosmic_censorship_C2','strong_cosmic_censorship_C0']. "
            "The conflict is gate-wide, not F2b-specific: F2a carries two accepts at e9a27996dfd3 with "
            "the identical conflict, so a F2b-only re-stamp would desynchronise the siblings and would "
            "write an alias form into a new canonical artifact contrary to the frozen VOCAB_ALIASES "
            "policy. A worker cannot set a validation_status or gate verdict, and the canonical write "
            "belongs to the gate owner."
        ),
        "needed_to_unblock": (
            "Exactly one gate-owner decision (astra-lead-formulation) with one independent review, "
            "applied gate-wide to F2a and F2b: either (A) record a one-token addendum making the "
            "VOCAB_ALIASES canonical tokens operative for G-FORM without writing "
            "research_map/formulation_taxonomy.yaml (any write voids G-F0), or (B) re-stamp both "
            "schemas to the F0 alias forms and accept that both schema hashes move and all current "
            "F2a/F2b verdicts are void. Both resolutions are specified with hashes in "
            "artifacts/worker-024/f2b_rev29_repair/vocab_token_conflict_024.json."
        ),
        "evidence_refs": [F0, VOCAB, F2B, F2A,
                          "reviews/F2b-review-rev29-075.json",
                          "reviews/F2a-review-worker-017.json",
                          "reviews/F2a-review-worker-072-rev13.json",
                          f"{BRIEF}#{BRIEF_SHA[:12]}"],
    },
]

ERRATUM = {
    "event_id": "w024-f2b-repair-erratum-timestamp-20260912T0108",
    "event_type": "status",
    "created_at": ERRATUM_TS,
    "actor": ACTOR,
    "node_id": "F2b",
    "status": "active",
    "hours": 0.0,
    "summary": (
        "Timestamp erratum, content unchanged: the six w024-f2b-repair-* events were written to "
        "comms/outbox/worker-024.jsonl at 2026-09-12T01:08:17+08:00 and ingested with "
        "created_at 2026-09-12T01:10:00+08:00, i.e. about 100 s ahead of the wall clock at "
        "creation. The measured creation instant is 2026-09-12T01:08:17+08:00 (worker-024.jsonl "
        "mtime). No claim, "
        "artifact, hash, verdict or evidence ref in those events is affected; this erratum sets no "
        "node status beyond the active status of this run. The six payloads are snapshotted verbatim "
        "in artifacts/worker-024/f2b_rev29_repair/outbox_events_snapshot_024.jsonl."
    ),
    "evidence_refs": ["comms/outbox/worker-024.jsonl",
                      "artifacts/worker-024/f2b_rev29_repair/outbox_events_snapshot_024.jsonl",
                      f"{REPORT}#{REPORT_SHA[:12]}"],
    "next_falsifier": (
        "Compare the six events' created_at against the worker-024.jsonl mtime "
        "(2026-09-12T01:08:17+08:00): the erratum is falsified if the ingested created_at is not "
        "01:10:00 or the file mtime is not 01:08:17, or if any of the six payloads differs from its "
        "verbatim copy in outbox_events_snapshot_024.jsonl on any field other than the "
        "controller-added/normalised fields _received_at, _source_file, _normalized and the "
        "class_id derived from class_ids."
    ),
}


def main():
    all_events = EVENTS + [ERRATUM]
    for e in all_events:
        validate_event(e)

    # verbatim snapshot of the six task events (no erratum self-reference)
    snap = ROOT / "artifacts/worker-024/f2b_rev29_repair/outbox_events_snapshot_024.jsonl"
    snap.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in EVENTS))

    out = ROOT / "comms/outbox/worker-024.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if out.exists():
        for line in out.read_text().splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    new = [e for e in all_events if e["event_id"] not in seen]
    with out.open("a") as f:
        for e in new:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"wrote {len(new)} schema-valid events ({len(all_events) - len(new)} already present) -> {out.relative_to(ROOT)}")
    print(f"snapshot -> {snap.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
