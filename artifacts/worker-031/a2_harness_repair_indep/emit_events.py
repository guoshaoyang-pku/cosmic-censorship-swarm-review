#!/usr/bin/env python3
"""Emit W031-A2-HARNESS-REPAIR-INDEP-01 events into comms/outbox/worker-031.jsonl.

Idempotent: skips any event_id already present in the file. Append-only, one JSON object
per line. Worker measurement only; no node status transition or gate verdict is claimed.
"""
import hashlib
import json
import os
import time

D = "artifacts/worker-031/a2_harness_repair_indep"
OUT = "comms/outbox/worker-031.jsonl"
TASK = "W031-A2-HARNESS-REPAIR-INDEP-01"
NOW = time.strftime("%Y-%m-%dT%H:%M:%S%z")
TS = time.strftime("%Y%m%dT%H%M%S")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


REPORT = sha(f"{D}/report.json")
README = sha(f"{D}/README.md")
CKPT = sha(f"{D}/CHECKPOINT.json")
HARNESS = sha("evaluation/ablation_harness.py")
DESIGN = sha("evaluation/ablation_design.yaml")
E = []


def add(o):
    o.update({"created_at": NOW, "actor": "worker-031"})
    E.append(o)


base = {"class_id": "GLOBAL", "class_ids": ["GLOBAL"], "node_id": "A2", "gate": "G-AUDIT",
        "task_id": TASK,
        "counts_as_node_verdict": False, "counts_as_gate_verdict": False,
        "counts_as_validation_pass": False, "counts_as_full_schema_verdict": False,
        "counts_as_independent": True,
        "does_not_claim": ["no node A2 completion or status transition",
                           "no validation_status=passed", "no G-AUDIT gate verdict",
                           "no real-model result: the dry run is synthetic",
                           "no resolution of design-owner residues R1-R3"]}

add(dict(base, event_id=f"w031-a2indep-{TS}-01-artifact-report", event_type="artifact",
         artifact_type="review_report", path=f"{D}/report.json", sha256=REPORT,
         validation_status="unverified",
         summary="Independent A2 harness-repair verification report: accept 4.0 at "
                 "evaluation/ablation_harness.py#0fae94bf0190; 10/10 checks, 8/8 controls fire, "
                 "CSV byte-identical to producer, report equal modulo generated_at, pins unchanged."))

add(dict(base, event_id=f"w031-a2indep-{TS}-02-artifact-readme", event_type="artifact",
         artifact_type="review_readme", path=f"{D}/README.md", sha256=README,
         validation_status="unverified",
         summary="Human-readable record of the independent verification, reproduce commands, "
                 "prior-finding disposition, non-blocking observation O1 and residues R1-R3."))

add(dict(base, event_id=f"w031-a2indep-{TS}-03-artifact-checkpoint", event_type="artifact",
         artifact_type="checkpoint", path=f"{D}/CHECKPOINT.json", sha256=CKPT,
         validation_status="unverified",
         summary=f"Task pins and artifact hashes: harness {HARNESS[:12]}, design {DESIGN[:12]}, "
                 f"report {REPORT[:12]}, 12 files hashed, canonical pins unchanged start-to-end."))

add(dict(base, event_id=f"w031-a2indep-{TS}-04-review", event_type="review",
         target_id=f"evaluation/ablation_harness.py#{HARNESS[:12]}",
         reviewer="worker-031", verdict="accept", score=4.0, hard_failures=[],
         verdict_scope="harness artifact and its design-bound synthetic dry run only",
         findings=[
             "Pins: live harness 0fae94bf0190 == manifest prev/next chain and == report provenance; "
             "design 1b2a83ef670b; 11/11 producer manifest hashes recomputed and matching.",
             "Self-test 21/21 exit 0; two design-bound dry runs byte-identical; CSV byte-identical "
             "to the producer's (1992f62f0c40); report differs from producer's in 2/538 leaves, "
             "both generated_at.",
             "Matched budget: token spread 0.0101, wall-consumption spread 0.0101, tolerance "
             "0.02/0.02, matched=true, walls non-constant [30.0, 30.0, 29.7, 29.76], primary "
             "endpoint guardrail-applied.",
             "Marking: simulated=true, run_mode=dry_run_synthetic, disclaimer present, CSV leading "
             "simulated,run_mode,harness_sha256, 5/5 rows marked; unmarked canonical name refused "
             "exit 2 with no file; --execute refused exit 3.",
             "Declared matched fields all measured; the two unequalisable ones named in "
             "design_deviations and unmatched_declared_fields (spreads 1.074 / 3.547).",
             "Independent checker 10/10; 8/8 negative controls fire, including an end-to-end "
             "0.15-tolerance mutant harness that trips the pre-registered-tolerance check.",
             "Harness-side blocking findings of A2-review-18/19/022/067 closed at the pinned bytes; "
             "R1 (design line 172 names the audit copy), R2 (declared matched-field equalisation), "
             "R3 (canonical dry-run outputs not regenerated at the new pin) remain owner items.",
             "O1 non-blocking: declared_matched_fields[*].tolerance (fixed 0.02) can diverge from "
             "the effective token_tolerance under an override; no effect at the pinned default run."],
         evidence_refs=[f"{D}/report.json#{REPORT[:12]}", f"{D}/CHECKPOINT.json#{CKPT[:12]}",
                        f"evaluation/ablation_harness.py#{HARNESS[:12]}",
                        f"evaluation/ablation_design.yaml#{DESIGN[:12]}"]))

add(dict(base, event_id=f"w031-a2indep-{TS}-05-claim", event_type="claim",
         conclusion_type="measurement", assumptions=[
             "the harness is deterministic under a fixed PYTHONHASHSEED and makes no model calls "
             "(synthetic placeholders only; verified by AST import scan and --execute refusal)",
             "the pre-registered matched-budget tolerance is the design's +/-2%",
             "sha256 pins are the identity of the compared bytes"],
         statement="Artifact-and-checker measurement (not a mathematics claim, not a gate verdict): "
                   "at evaluation/ablation_harness.py#0fae94bf0190 and "
                   "evaluation/ablation_design.yaml#1b2a83ef670b, an independent stdlib-only checker "
                   "and two fresh dry runs reproduce the producer's CSV byte-identically and its "
                   "report to the generated_at field (536/538 leaves equal); 10/10 checks pass and "
                   "8/8 negative controls fire. The harness-side blocking findings of the four prior "
                   "revise verdicts are closed at the pinned bytes; R1-R3 are owner residues.",
         falsifier="Any byte change of the harness or design voids this measurement; a re-run at "
                   "the pinned bytes with budget_check.matched=false, constant wall consumption, an "
                   "unmarked dry-run row, or an unlisted unmatched declared field falsifies it.",
         evidence_refs=[f"{D}/report.json#{REPORT[:12]}", f"{D}/out/indep_check_genuine.json",
                        f"{D}/controls/control_results.json",
                        f"evaluation/ablation_harness.py#{HARNESS[:12]}"]))

add(dict(base, event_id=f"w031-a2indep-{TS}-06-status", event_type="status",
         status="done", hours=0.5,
         summary="Bounded task complete at worker level (completion claim only; workers cannot set "
                 "node done/passed or a gate verdict). W031-A2-HARNESS-REPAIR-INDEP-01: independent "
                 "non-author verification of the repaired A2 harness at 0fae94bf0190 gives accept "
                 "4.0, 0 hard failures, 10/10 checks, 8/8 controls, canonical pins unchanged.",
         next_falsifier="Re-measure the pins and re-run the two dry runs plus check_a2_indep.py at "
                        "0fae94bf0190; if the design owner edits evaluation/ablation_design.yaml "
                        "line 172 or the map pin is regenerated at the new harness hash, re-run this "
                        "review at the new pins.",
         evidence_refs=[f"{D}/report.json#{REPORT[:12]}", f"{D}/CHECKPOINT.json#{CKPT[:12]}"]))

existing = set()
if os.path.exists(OUT):
    for line in open(OUT, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass

new = [e for e in E if e["event_id"] not in existing]
with open(OUT, "a", encoding="utf-8") as f:
    for e in new:
        f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
print(f"wrote {len(new)} events (skipped {len(E) - len(new)} duplicates) to {OUT}")
for e in new:
    print(" ", e["event_id"])
