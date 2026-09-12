#!/usr/bin/env python3
"""W068-FORM-POLARITY-10 event emitter.

Writes checkpoint.json, then validates and appends the protocol events for this task to
comms/outbox/worker-068.jsonl (idempotent by event_id). Every event is validated with
research_map/schemas.py before it is written. Workers cannot set done/passed/gate
verdicts, so all status events stay `active` and all artifacts stay `unverified`.

Usage: python3 emit_events.py
Exit 0 on success; 2 if validation fails or a required artifact is missing.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms" / "outbox" / "worker-068.jsonl"
ACTOR = "worker-068"
TASK = "W068-FORM-POLARITY-10"
CORPUS = "FORM-POLARITY-10"
GATE = "G-CLASSBIND (folded into G-AUDIT as calibration evidence)"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")
    paths = {
        "manifest": HERE / "manifest.json",
        "report": HERE / "report.json",
        "raw": HERE / "raw_verdicts.json",
        "builder": HERE / "build_corpus.py",
        "runner": HERE / "run_polarity10.py",
        "readme": HERE / "README.md",
    }
    missing = [name for name, p in paths.items() if not p.is_file()]
    if missing:
        print(f"missing artifacts: {missing}", file=sys.stderr)
        return 2
    sh = {name: sha256_file(p) for name, p in paths.items()}
    rel = {name: str(p.relative_to(ROOT)) for name, p in paths.items()}

    report = json.loads(paths["report"].read_text())
    agg = report["aggregates"]

    checkpoint = {
        "task_id": TASK,
        "corpus_id": CORPUS,
        "actor": ACTOR,
        "created_at": now,
        "status": "active",
        "valid": report["valid"],
        "arm_calibration": report["arm_calibration"],
        "summary": {
            "probes_all": agg["probes_all"],
            "probes_informative": agg["probes_informative"],
            "escaped_informative": agg["probes_informative_escaped_union"],
            "union_escape_rate_informative": agg["probe_union_escape_rate_informative"],
            "identity_controls_accepted": f"{agg['identity_controls_accepted']}/{agg['identity_controls']}",
            "known_rejected_rejected": f"{agg['known_rejected_controls_rejected']}/{agg['known_rejected_controls']}",
            "heldout09_reference_still_escaping": f"{agg['known_escape_references_still_escaping']}/{agg['known_escape_references']}",
        },
        "findings": [f["finding"] for f in report["findings"]],
        "artifact_hashes": {name: sh[name] for name in sh},
        "next_falsifier": report["next_falsifier"],
        "claims_completion": False,
    }
    ckpt = HERE / "checkpoint.json"
    if ckpt.is_file():
        # idempotent: never rewrite an existing checkpoint (its hash is already cited by events)
        checkpoint = json.loads(ckpt.read_text())
    else:
        ckpt.write_text(json.dumps(checkpoint, indent=2, sort_keys=False) + "\n")
    sh["checkpoint"] = sha256_file(ckpt)
    rel["checkpoint"] = str(ckpt.relative_to(ROOT))

    def artifact_event(eid, name, artifact_type, summary):
        return {
            "event_id": eid, "event_type": "artifact", "actor": ACTOR, "created_at": now,
            "node_id": "A1", "artifact_type": artifact_type,
            "path": rel[name], "sha256": sh[name], "validation_status": "unverified",
            "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "task_id": TASK,
            "summary": summary,
            "evidence_refs": [f"{rel[name]}#sha256:{sh[name][:12]}"],
            "next_falsifier": report["next_falsifier"],
        }

    events = [
        {
            "event_id": "w068-pol10-01-task-claim", "event_type": "status", "actor": ACTOR,
            "created_at": now, "node_id": "A1", "status": "active", "hours": 0.3,
            "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "task_id": TASK,
            "summary": ("No assignment card exists in comms/inbox for worker-068 (this fleet instance). Took ONE bounded "
                        "class-bound task: W068-FORM-POLARITY-10 = measure how general the FORM-HELDOUT-09 "
                        "conclusion-negation escape is across AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN, "
                        "with identity controls and known-rejected liveness controls, at pinned stage hashes. "
                        "Measurement only; no gate verdict."),
            "evidence_refs": ["artifacts/worker-068/heldout3/report.json#sha256:9904e516a9da", "comms/PROTOCOL.md"],
            "next_falsifier": report["next_falsifier"],
        },
        artifact_event("w068-pol10-02-manifest", "manifest", "polarity_probe_manifest",
                       "Corpus manifest: 15 polarity probes (p1-p7 over W/C2/C0), 3 identity controls, 3 known-rejected controls, 1 byte-identical HELDOUT-09 escape reference; per-fixture sha256, op definitions, measured canonical rev12 / FROZEN rev28 / stage / KEY_MANIFEST binding."),
        artifact_event("w068-pol10-03-report", "report", "polarity_probe_report",
                       "FORM-POLARITY-10 report: valid=true; informative arms C2+C0 => 7/9 probes escape (0.778): inner-negation flip, outer negation, NL negation and the rebuilt HELDOUT-09 inversion all escape; conclusion_type token flip caught by R11. WCC arm non-informative (stage B rejects the unmutated rev12 WCC base, R03)."),
        artifact_event("w068-pol10-04-raw", "raw", "polarity_probe_raw_verdicts",
                       "Per-fixture stage-A/stage-B verdicts with failed rules/checks, arm calibration, input dependency measurement (KEY_MANIFEST sha 014e2d301978, unpinned) and live canonical drift record (none)."),
        artifact_event("w068-pol10-05-builder", "builder", "polarity_probe_builder",
                       "Deterministic builder: snapshots the three canonical schemas at measured hashes, applies one explicit polarity op per probe, refuses on non-applicable op."),
        artifact_event("w068-pol10-06-runner", "runner", "polarity_probe_runner",
                       "Runner with fixture-tamper and stage-hash checks, arm calibration, liveness controls, KEY_MANIFEST dependency measurement, and drift recording."),
        artifact_event("w068-pol10-07-readme", "readme", "submission_note",
                       "README: question, method, binding table, results, 3 findings, non-claims, falsifier, reproduction."),
        artifact_event("w068-pol10-08-checkpoint-artifact", "checkpoint", "checkpoint",
                       f"Checkpoint: valid={report['valid']}, informative probes 9, escapes 7, identity 2/3, liveness 3/3, reference masked by KEY_MANIFEST drift."),
        {
            "event_id": "w068-pol10-09-claim", "event_type": "claim", "actor": ACTOR,
            "created_at": now, "node_id": "A1", "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "task_id": TASK,
            "conclusion_type": "numerical_evidence",
            "statement": ("At the pinned pipeline (stage A 000e09e46b2f, stage B c79d8ab8440a, rule spec 40f9bb9e657b, "
                          "KEY_MANIFEST 014e2d301978) applied to a 15-probe conclusion-polarity corpus built from the "
                          "canonical class schemas at rev12 (W cce9c60146d6, C2 5476a3f2c6bc, C0 55d0a1ea9bda), the WCC "
                          "arm is non-informative because stage B rejects the unmutated WCC base (R03). In the two "
                          "informative arms (C2, C0), 7 of 9 probes escape both stages (union escape rate 0.778): "
                          "p1 inner-negation flip, p2 outer negation, p3 natural-language negation (each for C2 and C0) "
                          "and p7, a rebuild of the HELDOUT-09 C0 conclusion inversion on the rev12 base. The "
                          "conclusion_type token flip (p4) is caught by R11 for both. The byte-identical HELDOUT-09 "
                          "reference fixture is now rejected by stage A only on R22 key hygiene (stale "
                          "'revised_at_unused'), while stage B still accepts it, so the HELDOUT-09 escape is masked by "
                          "an unpinned KEY_MANIFEST dependency rather than fixed. This is a measurement about the "
                          "pipeline, not a class-truth claim."),
            "assumptions": [
                "Escape = accepted by BOTH stages; the corpus and its labels are author-built and require independent adjudication.",
                "A class arm is informative only if its unmutated identity control is accepted by both stages (W is not).",
                "Stage A reads artifacts/formulation/KEY_MANIFEST.json, which is not covered by any pinned stage hash.",
                "Binding is to measured bytes recorded in manifest.json/report.json; live canonical drift during the run was none.",
            ],
            "falsifier": report["next_falsifier"],
            "evidence_refs": [
                f"{rel['report']}#sha256:{sh['report'][:12]}",
                f"{rel['raw']}#sha256:{sh['raw'][:12]}",
                f"{rel['manifest']}#sha256:{sh['manifest'][:12]}",
                f"{rel['checkpoint']}#sha256:{sh['checkpoint'][:12]}",
            ],
            "artifact_refs": [f"{rel['report']}#sha256:{sh['report'][:12]}", f"{rel['raw']}#sha256:{sh['raw'][:12]}"],
        },
        {
            "event_id": "w068-pol10-10-blocker-polarity", "event_type": "blocker", "actor": ACTOR,
            "created_at": now, "node_id": "A1", "class_ids": CLASS_IDS, "gate": GATE,
            "group_id": "formulation", "task_id": TASK,
            "description": ("Conclusion-polarity/content blind spot is class-general for the SCC arms at rev12: probes "
                            "that invert conclusion.statement_formal (inner or outer negation) or invert only "
                            "statement_natural_language are accepted by both stages in AF-SCC-C2-VAC-GEN and "
                            "AF-SCC-C0-VAC-GEN (6/6 such informative probes escape), and the rebuilt HELDOUT-09 C0 "
                            "inversion also escapes (7/9 informative probes total). Neither stage compares conclusion "
                            "statement content against the class conclusion; R11 checks the conclusion_type token only."),
            "needed_to_unblock": ("Independent reviewer adjudication of the probe corpus as well-formed class-binding "
                                  "leaks, then either an R11 extension that compares conclusion.statement_formal / "
                                  "statement_natural_language against the frozen conclusion, or a documented blind-spot "
                                  "entry recording that conclusion polarity is not machine-checked."),
            "evidence_refs": [
                f"{rel['report']}#sha256:{sh['report'][:12]}",
                f"{rel['raw']}#sha256:{sh['raw'][:12]}",
                "artifacts/worker-068/heldout3/mutants/c0_03_conclusion_negated.yaml#sha256:1e8898ac7bad",
            ],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": "w068-pol10-11-blocker-unpinned-input", "event_type": "blocker", "actor": ACTOR,
            "created_at": now, "node_id": "A1", "class_ids": CLASS_IDS, "gate": GATE,
            "group_id": "formulation", "task_id": TASK,
            "description": ("Stage A (check_class_schema.py 000e09e46b2f) reads artifacts/formulation/KEY_MANIFEST.json, "
                            "which no stage hash pins; the current file (014e2d301978, mtime 00:34:42, 271 allowed keys) "
                            "no longer allows 'revised_at_unused'. Consequence: the byte-identical FORM-HELDOUT-09 "
                            "reference fixture c0_03 (1e8898ac7bad) flips from union escape (stage A pass / stage B "
                            "accept at 00:30) to stage A R22 key-hygiene reject (stage B still accepts) without any "
                            "polarity rule change. HELDOUT-09's binding pinned the rule spec but not KEY_MANIFEST, so "
                            "its verdicts are not stable across KEY_MANIFEST revisions."),
            "needed_to_unblock": ("Pin KEY_MANIFEST.json (or the stage-A input set) in FROZEN/corpus bindings and in the "
                                  "stage A binding contract; re-run the HELDOUT-09 reference with the rebuilt rev12 "
                                  "equivalent (this report's p7) as the authoritative polarity check."),
            "evidence_refs": [
                f"{rel['report']}#sha256:{sh['report'][:12]}",
                f"{rel['raw']}#sha256:{sh['raw'][:12]}",
                "artifacts/formulation/KEY_MANIFEST.json#sha256:014e2d301978",
            ],
            "next_falsifier": ("A pinned-input re-run showing the c0_03 reference still escaping at the current "
                               "KEY_MANIFEST (would remove the masking explanation), or a KEY_MANIFEST revision that "
                               "allows 'revised_at_unused' again."),
        },
        {
            "event_id": "w068-pol10-12-blocker-wcc-base", "event_type": "blocker", "actor": ACTOR,
            "created_at": now, "node_id": "F1", "class_ids": CLASS_IDS, "gate": GATE,
            "group_id": "formulation", "task_id": TASK,
            "description": ("Pipeline calibration finding: stage B (worker-06 spec_conformance_audit.py c79d8ab8440a) "
                            "rejects the LIVE canonical schemas/af_wcc_vacuum.yaml at rev12 (cce9c60146d6) with "
                            "R03: binder '(q,t0)' absent from formal sentence. Stage A passes it. The same verdict is "
                            "returned for the unmutated identity fixture, so the WCC arm of FORM-POLARITY-10 is "
                            "non-informative and all 6 WCC probe 'catches' are base-rejection artifacts."),
            "needed_to_unblock": ("Lead-formulation / lead-audit adjudication: either normalize the WCC quantifiers "
                                  "binder spelling to the formal sentence (or add a domain/binder mapping) so the "
                                  "canonical passes stage B, or record the R03 check as over-literal. Until then no "
                                  "WCC class-binding measurement on this pipeline is informative."),
            "evidence_refs": [
                f"{rel['report']}#sha256:{sh['report'][:12]}",
                f"{rel['raw']}#sha256:{sh['raw'][:12]}",
                "schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6",
                "artifacts/worker-06/spec_conformance_audit.py#sha256:c79d8ab8440a",
            ],
            "next_falsifier": ("A stage B run in which the unmutated canonical WCC schema and ctrl_w_identity are "
                               "accepted (R03 no longer fires); then the WCC polarity probes become informative and "
                               "must be re-measured."),
        },
        {
            "event_id": "w068-pol10-13-checkpoint", "event_type": "status", "actor": ACTOR,
            "created_at": now, "node_id": "A1", "status": "active", "hours": 0.4,
            "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "task_id": TASK,
            "summary": ("CHECKPOINT (worker-068, FORM-POLARITY-10): valid=true; 15 probes, informative arms C2+C0 9 "
                        "probes / 7 escapes (0.778); identity 2/3 (W base rejected by stage B R03), liveness 3/3; "
                        "HELDOUT-09 reference masked by unpinned KEY_MANIFEST drift; canonical/stage inputs unchanged "
                        "after the run."),
            "evidence_refs": [
                f"{rel['checkpoint']}#sha256:{sh['checkpoint'][:12]}",
                f"{rel['report']}#sha256:{sh['report'][:12]}",
            ],
            "next_falsifier": report["next_falsifier"],
        },
        {
            "event_id": "w068-pol10-14-complete", "event_type": "status", "actor": ACTOR,
            "created_at": now, "node_id": "A1", "status": "active", "hours": 0.5,
            "class_ids": CLASS_IDS, "gate": GATE, "group_id": "formulation", "task_id": TASK,
            "summary": ("Bounded worker lifecycle complete (W068-FORM-POLARITY-10). Artifacts and events emitted; "
                        "worker exits for recycling. No node completion, validation_status=passed, or gate verdict is "
                        "claimed; the three blockers above carry the open items."),
            "evidence_refs": [
                f"{rel['readme']}#sha256:{sh['readme'][:12]}",
                f"{rel['report']}#sha256:{sh['report'][:12]}",
            ],
            "next_falsifier": "See w068-pol10-10-blocker-polarity, -11-blocker-unpinned-input and -12-blocker-wcc-base.",
        },
    ]

    for ev in events:
        try:
            validate_event(ev)
        except Exception as exc:
            print(f"event {ev.get('event_id')} failed schema validation: {exc}", file=sys.stderr)
            return 2

    existing = set()
    if OUTBOX.is_file():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    written = 0
    with OUTBOX.open("a") as f:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, sort_keys=True) + "\n")
            written += 1
    print(json.dumps({"checkpoint": rel["checkpoint"], "checkpoint_sha256": sh["checkpoint"],
                      "events_total": len(events), "events_written": written,
                      "artifact_hashes": {k: v[:12] for k, v in sh.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
