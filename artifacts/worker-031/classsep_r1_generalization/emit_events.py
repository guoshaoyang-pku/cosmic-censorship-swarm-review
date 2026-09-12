#!/usr/bin/env python3
"""Emit W031-CLASSSEP-R1-GENERALIZATION-01 events to comms/outbox/worker-031.jsonl.

Self-reject check first (PROTOCOL rule 5): every emitted text is scanned by the live
canonical detector; a nonzero hard finding aborts the emit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = REPO / "comms/outbox/worker-031.jsonl"
NOW = "2026-09-12T01:40:00+08:00"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    det = load("w031_live_det", REPO / "research_map/class_separation.py")
    report = HERE / "out/report.json"
    probes = HERE / "out" / "probes.json"
    battery = HERE / "fixtures_battery.json"
    runner = HERE / "run_generalization_031.py"
    probe_runner = HERE / "run_probes_031.py"
    readme = HERE / "README.md"
    checkpoint = HERE / "CHECKPOINT.json"
    for p in (report, probes, battery, runner, probe_runner, readme, checkpoint):
        assert p.exists(), p

    summary = json.loads(report.read_text())["summary"]
    claim_stmt = (
        "Artifact-and-checker measurement (not a mathematics claim, not a gate verdict): at the pinned "
        "bytes canonical research_map/class_separation.py a8c04fc31e4a, staged candidate "
        "class_separation_prose_r1.py 42cdb6839cc4, map design pin 262da697 (320 claims), worker-07 corpus, "
        "worker-049 corpus d, worker-035 battery e, the candidate's full r3 adoption-bar report reproduces "
        "exactly on this independently written runner (27-fixture PASS, w049 HIGH cue-induced FN 0, w035 23/23, "
        "design-pin hard 17 -> 0), but on a fresh 42-fixture battery authored after the candidate's rules and "
        "labeled before execution, the candidate's sensitivity is 14/24 against canonical 16/24 while specificity "
        "is 11/18 against 7/18: five candidate-specific failures (GA07, GA08, GB02, GC03, GC04) are attributable to "
        "sentence-wide exception scope and to the new assertion vocabulary being unbound to report frames, and "
        "twelve further misses are shared with canonical. The candidate moves the lexical frontier; it does not "
        "establish that assertion-vs-mention is lexically separable."
    )
    review_findings = [
        "Verdict GENERALIZATION_NOT_ESTABLISHED: all four pre-registered recount numbers reproduce (w07 PASS 17/0/10/0; w049 HIGH cue-FN 0; w035 23/23; design-pin hard 17 -> 0), so the candidate's own claims are honest, but they bind only to corpora published before its rules.",
        "Fresh battery: canonical 16/24 sens / 7/18 spec; candidate 14/24 / 11/18; prosefix 12/24 / 12/18. Error sets: candidate-only 5 (GA07, GA08, GB02, GC03, GC04), canonical-only 7 (GB04-GB07, GC05, GD05, GF05), shared 12 (assertion-vocabulary gap and token-form gap).",
        "Mechanism isolated as minimal pairs: GB02 fires on the reported-denial probe whose embedded clause uses the candidate's new assertion vocabulary (unbound to the report frame); the quoted-token-then-assertion pair is cleared by candidate AND canonical, so exception scope is sentence-wide; the report-then-deny pair fires in all three arms, so post-composite negation scope remains unbound; P2b litotes is fixed by the candidate only.",
        "Live-map caution: the candidate is silent on 38 of 38 composite-bearing claims at pin 262da697 (prosefix also 38/38). Zero hard findings and zero genuine assertions are the same number to a silent detector, so 0 hard is a lower bound on the miss count, not a clean-census result.",
        "No gate self-pass: worker measurement; sets no gate verdict, no node status, no validation_status; canonical path untouched at a8c04fc31e4a.",
    ]

    events = [
        {"event_id": "w031-r1gen-20260912T014000-art-report", "event_type": "artifact",
         "created_at": NOW, "actor": "worker-031", "artifact_type": "measurement_report",
         "node_id": "A1", "gate": "G-AUDIT", "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         "path": "artifacts/worker-031/classsep_r1_generalization/out/report.json",
         "sha256": sha(report), "validation_status": "unverified",
         "summary": "Independent generalization audit of the staged prose candidate 42cdb683. Recount reproduces all reported numbers; fresh 42-fixture battery gives candidate 14/24 sens / 11/18 spec vs canonical 16/24 / 7/18. Verdict GENERALIZATION_NOT_ESTABLISHED.",
         "evidence_refs": [f"artifacts/worker-031/classsep_r1_generalization/out/report.json#{sha(report)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/out/probes.json#{sha(probes)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/CHECKPOINT.json#{sha(checkpoint)[:12]}"]},
        {"event_id": "w031-r1gen-20260912T014000-art-battery", "event_type": "artifact",
         "created_at": NOW, "actor": "worker-031", "artifact_type": "labeled_fixture_corpus",
         "node_id": "A1", "gate": "G-AUDIT", "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         "path": "artifacts/worker-031/classsep_r1_generalization/fixtures_battery.json",
         "sha256": sha(battery), "validation_status": "unverified",
         "summary": "Fresh 42-fixture assertion-vs-mention battery (24 positive / 18 negative), authored after the candidate's rules were published, labels fixed before any detector executed on the file; per-fixture rationale included. Companion minimal-pair probe runner isolates the mechanisms.",
         "evidence_refs": [f"artifacts/worker-031/classsep_r1_generalization/fixtures_battery.json#{sha(battery)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/run_generalization_031.py#{sha(runner)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/run_probes_031.py#{sha(probe_runner)[:12]}"]},
        {"event_id": "w031-r1gen-20260912T014000-claim", "event_type": "claim",
         "created_at": NOW, "actor": "worker-031", "conclusion_type": "formal_model",
         "node_id": "A1", "gate": "G-AUDIT", "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         "statement": claim_stmt,
         "assumptions": [
             "the pinned candidate, canonical detector, map snapshot and three pre-registered corpora are the byte-sets hashed in CHECKPOINT.json; pins were re-verified after the run (pins_stable true)",
             "the fresh battery labels were written before either detector was executed on the file and are falsifiable per fixture; MEDIUM-confidence fixtures are marked",
             "a hard finding means a non-SOFT string returned by findings_for_text/findings_for_map at the pinned bytes",
             "recount uses each corpus author's own expected/ground-truth field; the fresh battery uses this task's labels",
         ],
         "falsifier": "Any pin mismatch at re-run; the candidate's recounted numbers not reproducing (they do); or all five candidate-specific fresh-battery failures being attributable to labeling error rather than to the candidate's rule chain (each is recorded with rationale and all-arm verdicts, and the two mechanisms are isolated as minimal pairs).",
         "evidence_refs": [f"artifacts/worker-031/classsep_r1_generalization/out/report.json#{sha(report)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/out/probes.json#{sha(probes)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/README.md#{sha(readme)[:12]}"],
         "artifact_refs": [f"artifacts/worker-031/classsep_r1_generalization/out/report.json#{sha(report)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/fixtures_battery.json#{sha(battery)[:12]}"]},
        {"event_id": "w031-r1gen-20260912T014000-review", "event_type": "review",
         "created_at": NOW, "actor": "worker-031", "target_id": "A1",
         "reviewer": "worker-031", "verdict": "revise", "score": 3.5,
         "counts_as_full_schema_verdict": False, "counts_as_independent": True,
         "hard_failures": [],
         "findings": review_findings,
         "evidence_refs": [f"artifacts/worker-031/classsep_r1_generalization/out/report.json#{sha(report)[:12]}",
                           f"artifacts/worker-031/classsep_r1_generalization/out/probes.json#{sha(probes)[:12]}"]},
        {"event_id": "w031-r1gen-20260912T014000-status", "event_type": "status",
         "created_at": NOW, "actor": "worker-031", "node_id": "A1",
         "status": "done", "task_id": "W031-CLASSSEP-R1-GENERALIZATION-01",
         "hours": 0.5,
         "summary": "Bounded task complete: independent recount of the staged prose candidate (all reported numbers reproduced) plus a fresh 42-fixture generalization battery and mechanism probes. Verdict GENERALIZATION_NOT_ESTABLISHED (candidate 14/24 sens, canonical 16/24; candidate spec 11/18, canonical 7/18). No gate verdict.",
         "evidence_refs": [f"artifacts/worker-031/classsep_r1_generalization/out/report.json#{sha(report)[:12]}"],
         "next_falsifier": "Adjudicate the five candidate-specific fresh-battery failures and the two minimal-pair mechanisms; if the labels hold, the next detector attempt must bind the exception scope to the clause carrying the assertion, not the sentence."},
        {"event_id": "w031-r1gen-20260912T014000-art-checkpoint", "event_type": "artifact",
         "created_at": NOW, "actor": "worker-031", "artifact_type": "checkpoint",
         "node_id": "A1", "gate": "G-AUDIT", "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
         "path": "artifacts/worker-031/classsep_r1_generalization/CHECKPOINT.json",
         "sha256": sha(checkpoint), "validation_status": "unverified",
         "summary": "Task pins and artifact hashes for W031-CLASSSEP-R1-GENERALIZATION-01; canonical detector measured a8c04fc31e4a, candidate 42cdb6839cc4, design-pin map 262da697.",
         "evidence_refs": [f"artifacts/worker-031/classsep_r1_generalization/CHECKPOINT.json#{sha(checkpoint)[:12]}"]},
    ]

    # PROTOCOL rule 5 — reject own output before sending.
    bad = []
    for ev in events:
        for k in ("statement", "summary", "next_falsifier"):
            v = ev.get(k)
            if isinstance(v, str):
                bad += [(ev["event_id"], k, f) for f in det.findings_for_text(v, f"{ev['event_id']}/{k}")
                        if not f.startswith("CLASSSEP-SOFT")]
        for f in ev.get("findings", []) or []:
            bad += [(ev["event_id"], "findings", x) for x in det.findings_for_text(f, ev["event_id"])
                    if not x.startswith("CLASSSEP-SOFT")]
    if bad:
        print("SELF-REJECT: emitted text produces hard findings")
        for b in bad:
            print("  ", b[0], b[1], b[2][:200])
        return 2

    with OUTBOX.open("a") as fh:
        for ev in events:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
    print(f"emitted {len(events)} events -> {OUTBOX}")
    print("self-reject scan: clean (0 hard findings on all emitted prose)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
