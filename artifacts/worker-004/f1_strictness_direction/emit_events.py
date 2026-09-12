#!/usr/bin/env python3
"""Emit the W004-F1-STRICTNESS-DIRECTION-INDEP-01 event batch to comms/outbox/worker-004.jsonl.

Reads MANIFEST.json at run time (so the manifest's own hash can be reported without a
circular dependency), re-verifies every referenced file against its recorded sha256, and
appends the events. Refuses to emit anything if a hash does not resolve.

Workers cannot set node status=done, validation_status=passed, or a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "comms" / "outbox" / "worker-004.jsonl"
CST = timezone(timedelta(hours=8))
STAMP = "20260912T0145"
NOW = datetime.now(CST).isoformat(timespec="seconds")
CHECKPOINT = "runtime/state/w004_checkpoint_f1_strictness_direction.json"
REVIEW = "reviews/F1-rev13-strictness-direction-worker-004.json"
# harness correction: instrument v2 and its report supersede the first batch; measurements identical
SUPERSEDES = {
    "batch": ["w004-f1dir-20260912T0125-*", "w004-f1dir-20260912T0128-errata-*"],
    "files": {
        "artifacts/worker-004/f1_strictness_direction/verify_f1_strictness_direction.py":
            {"superseded_sha256_prefix": "dcc1e6f628d8"},
        "artifacts/worker-004/f1_strictness_direction/report.json":
            {"superseded_sha256_prefix": "771778055243"},
        "artifacts/worker-004/f1_strictness_direction/MANIFEST.json":
            {"superseded_sha256_prefix": "6baa92e6bbe4"},
    },
    "reason": ("instrument hygiene: the C1 pin-drift control re-entered the full instrument, which "
               "recursed into nested sandbox directories. v2 invokes the child with --no-controls and "
               "skips the control battery on pin drift. No measurement, verdict or finding changed; "
               "controls.json and run_stdout.txt are byte-identical to the first batch."),
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(path: str, prefix: int = 12) -> str:
    return f"{path}#{sha256(ROOT / path)[:prefix]}"


def main() -> int:
    man = json.loads((HERE / "MANIFEST.json").read_text())
    # fail closed: every manifest entry must resolve
    bad = [rel for rel, want in man["files"].items()
           if not (ROOT / rel).is_file() or sha256(ROOT / rel) != want]
    if bad:
        print(f"REFUSING TO EMIT: unresolved manifest entries: {bad}", file=sys.stderr)
        return 3
    man_sha = sha256(HERE / "MANIFEST.json")
    f = man["files"]
    pins = [f"{p}#{h[:12]}" for p, h in man["pins_sha256"].items()]

    base = "artifacts/worker-004/f1_strictness_direction/"
    ev = []

    def add(e):
        e.update({"actor": "worker-004", "created_at": NOW})
        ev.append(e)

    add({"event_id": f"w004-f1dir-{STAMP}-status-take", "event_type": "status",
         "status": "active", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
         "hours": 1.0,
         "summary": ("W004-F1-STRICTNESS-DIRECTION-INDEP-01 taken (no inbox card for worker-004): "
                     "independent verification of the F1 rev13 visibility strictness-direction "
                     "correction at schemas/af_wcc_vacuum.yaml#d9cebb9404b2 and a direction-consistency "
                     "scan of the pinned class corpus. Read-only on canonical paths. This batch "
                     "supersedes the w004-f1dir-20260912T0125/T0128 batch after an instrument-hygiene "
                     "correction; measurements and verdicts are unchanged."),
         "supersedes": SUPERSEDES,
         "evidence_refs": pins, "next_falsifier": "any pinned input hashing differently"})

    art = [
        ("prereg", "verification_preregistration", f[base + "PREREGISTRATION.json"],
         "predictions E1-E10 + controls C1-C6, written before measurement"),
        ("instrument", "verification_instrument", f[base + "verify_f1_strictness_direction.py"],
         "fail-closed stdlib instrument; exhaustive model enumeration + polarity-aware corpus scan"),
        ("report", "verification_report", f[base + "report.json"],
         "pins, 13 checks, direction analysis, corpus scan, finding W004-DIR-01"),
        ("controls", "verification_controls", f[base + "controls.json"],
         "C1 pin drift / C2 planted inversion / C3 planted repair / C4 non-transitive / C5 determinism / C6 count"),
        ("frozendrift", "moving_input_observation", f[base + "frozen_drift_observed.json"],
         "FROZEN.json rewritten >=3x in five minutes; deliberately not bound"),
        ("readme", "verification_readme", f[base + "README.md"],
         "method, results, finding, reproduction, falsifier, non-claims"),
        ("emitter", "event_emitter", f[base + "emit_events.py"],
         "re-verifies every manifest entry before appending the event batch"),
        ("manifest", "verification_manifest", f"MANIFEST.json", man_sha),
    ]
    for tag, atype, sha, note in art:
        path = f"MANIFEST.json" if tag == "manifest" else next(
            k for k, v in f.items() if v == sha)
        add({"event_id": f"w004-f1dir-{STAMP}-artifact-{tag}", "event_type": "artifact",
             "node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "artifact_type": atype,
             "path": path, "sha256": sha, "validation_status": "unverified",
             "evidence_refs": pins, "note": note})

    add({"event_id": f"w004-f1dir-{STAMP}-review", "event_type": "review",
         "target_id": "F1", "reviewer": "worker-004",
         "verdict": "revise", "score": 3.5,
         "hard_failures": [{"id": "W004-DIR-01-HF", "severity": "major", "status": "open",
                            "detail": ("frozen F0 0abb9ed8a961 asserts SET is strictly stronger while "
                                       "F1 rev13 d9cebb94 (whose f0_binding declares that F0 hash) and "
                                       "the registry/delta assert strictly weaker")}],
         "findings": [{"id": "W004-DIR-01", "severity": "major", "status": "open",
                       "detail": ("research_map/formulation_taxonomy.yaml#0abb9ed8a961 lines 94 and 200 "
                                  "state the superseded direction; F1's own direction text is accepted")},
                      {"id": "W004-DIR-02", "severity": "minor", "status": "open",
                       "detail": ("F0 companion supplement d7419b4e8963 records D1 as 'F0 was stronger'; "
                                  "F0 asserted stronger, it was not stronger")}],
         "axis_verdict": "accept",
         "evidence_refs": [ref(base + "report.json"), ref(base + "controls.json"),
                           ref("research_map/formulation_taxonomy.yaml"),
                           ref("schemas/af_wcc_vacuum.yaml"),
                           ref(REVIEW)],
         "review_path": REVIEW,
         "falsifier": ("a pinned hash mismatch; a whole/tail separation among transitive preorders; a "
                       "single-q=>SET violation; a SET=>single-q violation at a causal maximum; a live "
                       "'SET is stronger' statement in F1/registry/delta; a non-disclosing revision note; "
                       "any control not firing")})

    add({"event_id": f"w004-f1dir-{STAMP}-claim", "event_type": "claim",
         "class_id": "AF-WCC-VAC-GEN", "node_id": "F1", "gate": "G-FORM",
         "conclusion_type": "formal_model",
         "statement": ("Artifact-and-checker result, not a mathematical claim: at pins F1 rev13 "
                       "d9cebb9404b2 / rev12 predecessor cce9c60146d6 / F0 0abb9ed8a961 / registry "
                       "6bac9ade / SET delta 64b8d639, the F1 rev13 strictness-direction correction "
                       "reproduces independently (0 whole/tail separations over all 355 preorders on 4 "
                       "points; 0 single-q=>SET violations; 0 SET=>single-q violations at a causal "
                       "maximum; omega-chain strict separation), while the frozen F0 canonical taxonomy "
                       "still asserts the opposite direction at lines 94 and 200 -> cross-artifact "
                       "contradiction W004-DIR-01 requiring owner/controller disposition."),
         "assumptions": [
             "the pinned bytes are the revision under test; any byte change voids the measurement and the instrument fails closed",
             "J^-(q) is past-closed for causal geodesics and the causal relation is transitive (standard)",
             "the finite preorder model set is a valid test bed for the two predicate implications; strictness needs a curve without causal maximum (infinite omega-chain), checked by its index rule",
             "workers cannot set done/passed or a gate verdict; this is advisory evidence for the audit lead and controller"],
         "measurements": {"preorders_4_points": 355, "whole_tail_separations": 0,
                          "single_implies_set_violations": 0,
                          "set_implies_single_at_causal_max_violations": 0,
                          "omega_chain_strict_separation": True,
                          "f0_live_opposite_direction_statements": 2,
                          "f1_rev13_live_opposite_direction_statements": 0,
                          "instrument_exit": 0, "expectations": "13/13", "controls": "6/6"},
         "artifact_refs": [ref(base + "report.json"), ref(base + "controls.json"),
                           ref(base + "PREREGISTRATION.json"), ref(base + "MANIFEST.json")],
         "evidence_refs": [ref(base + "report.json"), ref(base + "controls.json"),
                           ref("research_map/formulation_taxonomy.yaml"),
                           ref("schemas/af_wcc_vacuum.yaml"), ref(REVIEW)],
         "falsifier": ("any pinned hash drift; a transitive-preorder whole/tail separation; a "
                       "single-q=>SET violation; a SET=>single-q violation at a causal maximum; failure "
                       "of the omega-chain witness; a live stronger-direction statement in F1/registry/"
                       "delta; a non-disclosing revision note; any control not firing")})

    add({"event_id": f"w004-f1dir-{STAMP}-blocker", "event_type": "blocker",
         "node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
         "description": ("W004-DIR-01: F1 rev13 d9cebb9404b2 binds F0 0abb9ed8a961 via "
                         "f0_binding.declared_f0_sha256, but the frozen F0 canonical taxonomy asserts the "
                         "superseded strength direction at lines 94 and 200 while F1 rev13, "
                         "VARIANT_REGISTRY 6bac9ade and the SET delta 64b8d639 assert the corrected "
                         "direction. Independent proof agrees with rev13. F0 is frozen and G-F0 passed on "
                         "it, so no worker may repair it."),
         "needed_to_unblock": ("Owner/controller disposition: either authorize an F0 revision that "
                               "corrects lines 94/200 (voids the G-F0 accepts; re-verification required), "
                               "or record an explicit erratum declaring the F0 direction labels a known "
                               "residual and state which text is binding for direction questions."),
         "evidence_refs": [ref(base + "report.json"), ref("research_map/formulation_taxonomy.yaml"),
                           ref("schemas/af_wcc_vacuum.yaml"), ref(base + "README.md"), ref(REVIEW)],
         "falsifier": ("an authoritative controller/lead adjudication showing the F0 lines are already "
                       "void, or that F1 does not bind 0abb9ed8a961, or that the direction question is "
                       "governed by another document")})

    add({"event_id": f"w004-f1dir-{STAMP}-status-harness-erratum", "event_type": "status",
         "status": "active", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "hours": 1.5,
         "summary": ("HARNESS ERRATUM, no measurement change. Instrument v2 "
                     f"{f[base + 'verify_f1_strictness_direction.py'][:12]} supersedes dcc1e6f628d8 and "
                     f"report {f[base + 'report.json'][:12]} supersedes 771778055243: the C1 pin-drift "
                     "control re-entered the full instrument and recursed into nested sandbox "
                     "directories. v2 passes --no-controls to the C1 child and skips the control battery "
                     "on pin drift. controls.json and run_stdout.txt are byte-identical across both "
                     "batches; 13/13 expectations and 6/6 controls hold in both. The verdict (axis "
                     "accept / overall revise, finding W004-DIR-01) and every pinned measurement are "
                     "unchanged."),
         "supersedes": SUPERSEDES,
         "evidence_refs": [ref(base + "controls.json"), ref(base + "report.json"),
                           ref(base + "verify_f1_strictness_direction.py"), ref(base + "run_stdout.txt")]})

    add({"event_id": f"w004-f1dir-{STAMP}-status-checkpoint", "event_type": "status",
         "status": "active", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN", "hours": 1.3,
         "checkpoint": CHECKPOINT + "#" + sha256(ROOT / CHECKPOINT)[:12],
         "summary": ("CHECKPOINT + EXIT. W004-F1-STRICTNESS-DIRECTION-INDEP-01 complete at worker level: "
                     "one bounded class-bound task, read-only on canonical paths. Axis verdict accept on "
                     "the F1 rev13 direction text (13/13 expectations, 6/6 controls, exit 0); overall "
                     "verdict revise carried by cross-artifact finding W004-DIR-01 (frozen F0 still "
                     "asserts the opposite direction). No gate verdict, no node completion, no canonical write."),
         "artifacts": {k: v for k, v in f.items()},
         "evidence_refs": [ref(base + "report.json"), ref(base + "MANIFEST.json"), ref(REVIEW),
                           CHECKPOINT + "#" + sha256(ROOT / CHECKPOINT)[:12]],
         "next_falsifier": ("Re-run artifacts/worker-004/f1_strictness_direction/"
                            "verify_f1_strictness_direction.py: it fails closed on pin drift; a "
                            "controller/lead disposition of W004-DIR-01 changes the blocker, not the "
                            "direction measurement.")})

    ids = [e["event_id"] for e in ev]
    assert len(ids) == len(set(ids)), "duplicate event ids"
    existing = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    clash = [i for i in ids if i in existing]
    if clash:
        print(f"REFUSING TO EMIT: event ids already present: {clash}", file=sys.stderr)
        return 3
    with OUT.open("a") as fh:
        for e in ev:
            fh.write(json.dumps(e, sort_keys=True) + "\n")
    print(f"emitted {len(ev)} events to {OUT.relative_to(ROOT)}; manifest {man_sha[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
