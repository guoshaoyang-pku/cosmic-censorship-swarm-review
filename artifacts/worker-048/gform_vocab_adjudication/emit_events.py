#!/usr/bin/env python3
"""W48-GFORM-VOCAB-ADJUDICATION-01 / emit_events.py

Build, schema-validate and append the upward events for the vocabulary
adjudication to comms/outbox/worker-048.jsonl.  Idempotent: event_ids already
present in the outbox are skipped.  Nothing else is written.

Usage: python3 emit_events.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-048.jsonl"
CST = timezone(timedelta(hours=8))

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

PINS = {
    "F1": "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
    "F2a": "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
    "F2b": "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
    "F0": "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    "SPEC": "artifacts/formulation/rule_spec.json#40f9bb9e657b",
    "ALIASES": "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
    "FROZEN": "artifacts/formulation/FROZEN.json#2f358f6722d9",
    "F0_SUPP": "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
}
ARTS = {
    "audit_vocab.py": ART / "audit_vocab.py",
    "snapshot_inputs.py": ART / "snapshot_inputs.py",
    "emit_events.py": ART / "emit_events.py",
    "report.json": ART / "report.json",
    "README.md": ART / "README.md",
    "snapshot_manifest.json": ART / "snapshot_manifest.json",
}
FALSIFIER = (
    "A canonical registry that names strong_cosmic_censorship_C2 / strong_cosmic_censorship_C0 as the "
    "required token form for a new canonical artifact; or a controller ruling that F0's "
    "field_vocabulary governs the schemas (which would make F2a/F2b non-conformant and reverse "
    "W48-VOCAB-01); or a gate run that detects this divergence without a human reading it.  A later "
    "write to the live files is not a falsifier: it is a new revision to re-run against."
)


def sha(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = datetime.now(CST)
    ts = now.strftime("%Y%m%dT%H%M%S")
    eid = lambda slug: f"w48-{ts}-{slug}"  # noqa: E731
    created = now.isoformat(timespec="seconds")

    hashes = {name: sha(p) for name, p in ARTS.items()}
    for name, p in ARTS.items():
        assert p.is_file(), f"missing artifact {p}"
    report = json.loads((ART / "report.json").read_text())
    s = report["summary"]
    assert s["controls_all_flip"] is True and report["reproduce_guard"]["all_match"] is True

    art_refs = [f"artifacts/worker-048/gform_vocab_adjudication/{n}#{h[:12]}"
                for n, h in hashes.items()]
    ev = []

    ev.append({
        "event_id": eid("status-vocab-task"), "event_type": "status", "created_at": created,
        "actor": "worker-048", "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN",
        "status": "active", "hours": 0.2,
        "summary": "W48-GFORM-VOCAB-ADJUDICATION-01 taken under the open G-FORM/G-F0 review round: "
                   "hash-bound adjudication of the conclusion-type/genericity token authority that "
                   "produces HF-059-F2A-01 / w063-C08 / W082-F-04. Snapshot 11 inputs, FROZEN rev28 "
                   "0 mismatches.",
        "evidence_refs": [PINS["F2a"], PINS["F1"], PINS["F2b"], PINS["F0"], PINS["SPEC"],
                          PINS["ALIASES"], PINS["FROZEN"], art_refs[2]],
        "next_falsifier": FALSIFIER,
    })

    for name, h in hashes.items():
        ev.append({
            "event_id": eid(f"artifact-{name.replace('.', '_')}"), "event_type": "artifact",
            "created_at": created, "actor": "worker-048", "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "artifact_type": {"audit_vocab.py": "tool", "snapshot_inputs.py": "tool",
                              "emit_events.py": "tool",
                              "report.json": "report", "README.md": "readme",
                              "snapshot_manifest.json": "manifest"}[name],
            "path": f"artifacts/worker-048/gform_vocab_adjudication/{name}",
            "sha256": h, "validation_status": "unverified",
            "note": "worker-level artifact; validation_status is not promotable by a worker",
        })

    ev.append({
        "event_id": eid("claim-vocab-authority"), "event_type": "claim", "created_at": created,
        "actor": "worker-048", "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "F2a", "gate": "G-FORM", "conclusion_type": "formal_model",
        "statement": "At the rev12/F0-rev5 pins, the three frozen class schemas use the canonical "
                     "conclusion tokens enforced by rule_spec R11 and named canonical by VOCAB_ALIASES "
                     "(F2a: scc_c2_future_inextendibility; F2b: scc_c0_future_inextendibility), while "
                     "F0 rev5's field_vocabulary allow-lists and class axes use the alias forms "
                     "(strong_cosmic_censorship_C2/C0) plus the token 'unresolved' for "
                     "AF-WCC-SCALAR-SPH.genericity_kind, which neither registry defines. Therefore the "
                     "reported F2a/F2b defect is an alias-form artifact of F0's stale list, not a schema "
                     "defect; the gate blocker is the undecided designation of the governing vocabulary, "
                     "which F0's own rev2 revision note already records as open.",
        "assumptions": [
            "canonical path research_map/formulation_taxonomy.yaml is authoritative for G-F0 (REC-3)",
            "rule_spec.json is the vocabulary the canonical gate tool check_class_schema.py enforces (R11)",
            "VOCAB_ALIASES.json policy text governs the form of tokens in new canonical artifacts",
            "the measured bytes still equal the snapshot pins (checked by the reproduce guard)",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [PINS["F2a"], PINS["F1"], PINS["F2b"], PINS["F0"], PINS["F0_SUPP"],
                          PINS["SPEC"], PINS["ALIASES"], PINS["FROZEN"], art_refs[2], art_refs[4]],
        "artifact_refs": art_refs,
    })

    ev.append({
        "event_id": eid("review-f2a"), "event_type": "review", "created_at": created,
        "actor": "worker-048", "reviewer": "worker-048", "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN", "gate": "G-FORM",
        "target_id": PINS["F2a"], "reviewed_sha256": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "verdict": "revise", "score": 3.5,
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_verdict": True,
        "hard_failures": [
            {"id": "W48-VOCAB-09", "severity": "gate-blocking-but-not-F2a-content",
             "finding": "Strict membership of the F2a conclusion token in F0 rev5's "
                        "field_vocabulary.conclusion_type.allowed is False, while alias-aware equality "
                        "with F0's class axis is True. Until the governing vocabulary is designated, a "
                        "gate reader cannot decide F2a conformance without a ruling. No F2a content "
                        "defect was found: the token is exactly rule_spec R11's value and a canonical "
                        "key of VOCAB_ALIASES.",
             "falsifier": "A controller/lead ruling that F0 field_vocabulary governs, which would make "
                          "the F2a token non-conformant; or an F2a revision whose token differs from the "
                          "rule_spec R11 value."},
        ],
        "findings": [
            "12 checks / 7 controls: schema-side token conformance V1-V3 PASS; F0-side V4-V7 FAIL; "
            "supplement V8 PASS; strict-vs-alias divergence V9; policy timeline V10 PASS; "
            "author-acknowledged open designation V11 PASS; policy-text conformance V12 FAIL.",
            "Root cause is F0 rev5 (written 00:31:41, after VOCAB_ALIASES 23:32:53); repairing F0 forces "
            "F1/F2a/F2b revisions under each schema's own f0_binding rule, so the zero-hash-movement "
            "repair is a recorded ruling at the current pins (report.repair_matrix Path B).",
            "Corroborates worker-059 HF-059-F2A-01, worker-063 C08 and worker-082 W082-F-04; adds the "
            "rule_spec/VOCAB_ALIASES/F0 three-way matrix, the 'unresolved' unregistered-token census, "
            "and the repair-cost measurement.",
        ],
        "reviewer_independence": "worker-048 authored no formulation artifact, edited no schema, and read "
                                 "only snapshot copies; the instrument was written for this task.",
        "next_falsifier": "A registry or controller ruling that designates strong_cosmic_censorship_C2/C0 "
                          "as the required form for new canonical artifacts, or an F2a revision whose "
                          "token is not scc_c2_future_inextendibility.",
    })

    ev.append({
        "event_id": eid("review-f0-vocab"), "event_type": "review", "created_at": created,
        "actor": "worker-048", "reviewer": "worker-048", "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate": "G-F0", "target_id": PINS["F0"], "reviewed_sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "verdict": "revise", "score": 3.0,
        "counts_as_full_schema_verdict": False,
        "hard_failures": [
            {"id": "W48-VOCAB-04", "severity": "hard",
             "finding": "research_map/formulation_taxonomy.yaml#0abb9ed8a961:148-152 lists only alias "
                        "tokens in field_vocabulary.conclusion_type.allowed and omits both canonical SCC "
                        "keys; class axes C2/C0 use the alias forms (lines 254, 325).",
             "falsifier": "A revision or ruling that makes the alias-form list the governing vocabulary "
                          "for canonical artifacts."},
            {"id": "W48-VOCAB-06", "severity": "hard",
             "finding": "field_vocabulary.genericity_kind.allowed (lines 142-144) is entirely alias "
                        "forms plus 'unresolved'; 'unresolved' is defined by neither rule_spec.json "
                        "genericity_kind nor VOCAB_ALIASES.json, and it is used as "
                        "AF-WCC-SCALAR-SPH.axes.genericity_kind (line 393).",
             "falsifier": "A registry that defines 'unresolved' as a genericity_kind token."},
            {"id": "W48-VOCAB-12", "severity": "policy",
             "finding": "VOCAB_ALIASES policy ('aliases ... must never appear in a new canonical "
                        "artifact') predates F0 rev5: registry 23:32:53 vs F0 rev5 00:31:41. F0 rev5 "
                        "therefore carries alias forms in a new canonical artifact; F0's own rev2 note "
                        "(lines 34-35) already records the designation as an open finding.",
             "falsifier": "A record showing the alias registry was created after F0 rev5, or a ruling "
                          "that F0's allow-list is descriptive rather than normative."},
        ],
        "findings": [
            "The companion supplement d7419b4e8963 already uses canonical tokens (V8 PASS), so the two "
            "F0 companion artifacts disagree on vocabulary form at the frozen pins.",
            "Repair matrix measured: Path A (F0 rev6) voids all rev12 verdicts via the schemas' own "
            "f0_binding rule; Path B (recorded ruling at current hashes) moves no bytes; Path C "
            "(rewrite schemas to alias tokens) violates the policy text and fails rule_spec R11.",
        ],
        "reviewer_independence": "worker-048 authored no F0 artifact; read-only against snapshot copies.",
        "next_falsifier": "A canonical registry naming the alias forms as required, a ruling that F0 "
                          "field_vocabulary governs, or a revision of F0 whose vocabulary matches "
                          "rule_spec/VOCAB_ALIASES canonical keys.",
    })

    ev.append({
        "event_id": eid("status-vocab-complete"), "event_type": "status", "created_at": created,
        "actor": "worker-048", "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN",
        "status": "active", "hours": 0.4,
        "summary": "W48-GFORM-VOCAB-ADJUDICATION-01 complete at worker level: F2a is conformant to the "
                   "rule_spec/VOCAB_ALIASES canonical vocabulary; F0 rev5's alias-form field_vocabulary "
                   "and the unregistered 'unresolved' token are the root cause of HF-059-F2A-01 / "
                   "w063-C08. 12 checks, 7/7 controls flip, reproduce guard 12/12; verdicts revise on "
                   "F2a and F0 carried solely by the undecided token authority; 5 artifacts hash-pinned. "
                   "Not a gate verdict; no canonical artifact modified.",
        "evidence_refs": art_refs + [PINS["F2a"], PINS["F0"], PINS["SPEC"], PINS["ALIASES"]],
        "next_falsifier": FALSIFIER,
    })

    for e in ev:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:  # noqa: BLE001
                continue
    fresh = [e for e in ev if e["event_id"] not in existing]
    print(f"{len(ev)} events built, {len(ev) - len(fresh)} already present, {len(fresh)} to append")
    for e in ev:
        print(f"  {e['event_type']:<9} {e['event_id']}  validated")
    if args.dry_run:
        return 0
    with OUTBOX.open("a") as f:
        for e in fresh:
            f.write(json.dumps(e, sort_keys=False) + "\n")
    print(f"appended {len(fresh)} events -> {OUTBOX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
