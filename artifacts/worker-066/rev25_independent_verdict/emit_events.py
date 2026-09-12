#!/usr/bin/env python3
"""W066-REV25-VERDICT-01 step 5: emit the upward events to comms/outbox/worker-066.jsonl.

Every event is validated with research_map/schemas.validate_event before it is written, so the
outbox cannot contain a schema-invalid line. Nothing is written to research_map/events.jsonl;
ingest is the controller's step.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-066.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
WCC = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
C2 = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
C0 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
F0 = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
RULE_SPEC = "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ev(event_id, event_type, **kw):
    e = {"event_id": event_id, "event_type": event_type, "created_at": NOW, "actor": "worker-066"}
    e.update(kw)
    return validate_event(e)


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    hashes = {
        "report.json": sha(HERE / "report.json"),
        "README.md": sha(HERE / "README.md"),
        "pinned_manifest.json": sha(HERE / "pinned_manifest.json"),
        "evidence/crosschecks.json": sha(HERE / "evidence/crosschecks.json"),
        "evidence/replica_verdicts.json": sha(HERE / "evidence/replica_verdicts.json"),
        "evidence/acceptance_comparison.json": sha(HERE / "evidence/acceptance_comparison.json"),
        "checkpoint_result.json": None,
    }

    v = {x["target_id"]: x for x in report["verdicts"]}
    find = {f["id"]: f for f in report["findings"]}
    base = "artifacts/worker-066/rev25_independent_verdict"

    def finding_lines(ids):
        return [f"{i} [{find[i]['severity']}] {find[i]['statement'][:240]}" for i in ids]

    events = [
        ev("w066-rev25-claim-task", "status", node_id="F1", class_id="AF-WCC-VAC-GEN",
           class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
           status="active", hours=0.2, task_id="W066-REV25-VERDICT-01",
           summary=("No assignment card exists in comms/inbox for worker-066. Taking one bounded "
                    "class-bound task: W066-REV25-VERDICT-01 = independent hash-bound verification of "
                    "the rev25 canonical class schemas, the F0 binding and the binding rule spec, plus "
                    "an independent replication of the two-stage acceptance measurement. Answers "
                    "leadform-resource-request-2026-09-12T00:34:00+08:00 items (1) and (2). Workers "
                    "cannot set gates; verdicts below are reviewer verdicts only."),
           evidence_refs=[f"{base}/pinned_manifest.json#{hashes['pinned_manifest.json'][:12]}",
                          "artifacts/formulation/FROZEN.json#rev25"],
           next_falsifier=("any pinned target byte changes during the window, or the replica run fails "
                           "to reproduce union 31/31, or a claimed defect does not reproduce on the "
                           "pinned bytes")),
        ev("w066-rev25-review-f1", "review", target_id=f"schemas/af_wcc_vacuum.yaml#{WCC}", reviewer="worker-066",
           verdict=v[f"schemas/af_wcc_vacuum.yaml#{WCC}"]["verdict"], score=v[f"schemas/af_wcc_vacuum.yaml#{WCC}"]["score"],
           hard_failures=v[f"schemas/af_wcc_vacuum.yaml#{WCC}"]["hard_failures"],
           findings=finding_lines(["W066-B1", "W066-N1", "W066-N2"]),
           reviewed_sha256=WCC, node_id="F1", class_id="AF-WCC-VAC-GEN",
           note=("machine-green at the pinned bytes (structural pass, semantic accept; acceptance "
                 "pipeline replicated) but revise: the file is not a conforming YAML document "
                 "(7 duplicate root keys), so the declared revision history is not readable by any "
                 "conforming parser.")),
        ev("w066-rev25-review-f2a", "review", target_id=f"schemas/af_scc_c2_vacuum.yaml#{C2}", reviewer="worker-066",
           verdict=v[f"schemas/af_scc_c2_vacuum.yaml#{C2}"]["verdict"], score=v[f"schemas/af_scc_c2_vacuum.yaml#{C2}"]["score"],
           hard_failures=v[f"schemas/af_scc_c2_vacuum.yaml#{C2}"]["hard_failures"],
           findings=finding_lines(["W066-B1", "W066-N1", "W066-N2"]),
           reviewed_sha256=C2, node_id="F2a", class_id="AF-SCC-C2-VAC-GEN",
           note="same duplicate-key defect; conclusion token and C2/C0 separation pass both stages."),
        ev("w066-rev25-review-f2b", "review", target_id=f"schemas/af_scc_c0_vacuum.yaml#{C0}", reviewer="worker-066",
           verdict=v[f"schemas/af_scc_c0_vacuum.yaml#{C0}"]["verdict"], score=v[f"schemas/af_scc_c0_vacuum.yaml#{C0}"]["score"],
           hard_failures=v[f"schemas/af_scc_c0_vacuum.yaml#{C0}"]["hard_failures"],
           findings=finding_lines(["W066-B1", "W066-B2", "W066-N1", "W066-N2"]),
           reviewed_sha256=C0, node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
           note=("duplicate keys plus a machine-locatable internal contradiction: :157 denies H2_loc "
                 "containment while :244 asserts the full chain; F2a :157 carries the corrected wording.")),
        ev("w066-rev25-review-f0", "review", target_id=f"research_map/formulation_taxonomy.yaml#{F0}", reviewer="worker-066",
           verdict=v[f"research_map/formulation_taxonomy.yaml#{F0}"]["verdict"], score=v[f"research_map/formulation_taxonomy.yaml#{F0}"]["score"],
           hard_failures=v[f"research_map/formulation_taxonomy.yaml#{F0}"]["hard_failures"],
           findings=finding_lines(["W066-B4", "W066-B5", "W066-N2"]),
           reviewed_sha256=F0, node_id="F0", class_id="GLOBAL",
           note=("declared F0 is draft_unverified, uses alias conclusion tokens in classes.AF-SCC-C2/C0 "
                 "conclusion.type, and inlines 2 variants against the registry's 7.")),
        ev("w066-rev25-review-rulespec", "review", target_id=f"artifacts/formulation/rule_spec.json#{RULE_SPEC}",
           reviewer="worker-066", verdict=v[f"artifacts/formulation/rule_spec.json#{RULE_SPEC}"]["verdict"],
           score=v[f"artifacts/formulation/rule_spec.json#{RULE_SPEC}"]["score"],
           hard_failures=["W066-B3"], findings=finding_lines(["W066-B3", "W066-N4"]),
           reviewed_sha256=RULE_SPEC, node_id="F1", class_id="GLOBAL",
           note=("spec v1.2 declares R01-R16; the gate at 000e09e4 enforces R17-R25 and R27-R31. "
                 "Manifest rev7_delta and DELIVERABLE_SUMMARY:22 claim a v1.3 that is absent on disk.")),
    ]

    for name, h in [("report.json", hashes["report.json"]), ("README.md", hashes["README.md"]),
                    ("pinned_manifest.json", hashes["pinned_manifest.json"]),
                    ("evidence/crosschecks.json", hashes["evidence/crosschecks.json"]),
                    ("evidence/replica_verdicts.json", hashes["evidence/replica_verdicts.json"]),
                    ("evidence/acceptance_comparison.json", hashes["evidence/acceptance_comparison.json"])]:
        events.append(ev(f"w066-rev25-artifact-{name.replace('/', '-').replace('.', '-')}", "artifact",
                         node_id="F1", artifact_type=("report" if name == "report.json" else
                                                      "readme" if name == "README.md" else
                                                      "manifest" if name == "pinned_manifest.json" else "evidence"),
                         path=f"{base}/{name}", sha256=h, validation_status="unverified",
                         task_id="W066-REV25-VERDICT-01",
                         class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
                         note="worker-066 rev25 independent verdict artifact"))

    rep = report["measurements"]["acceptance_replication"]
    events.append(ev("w066-rev25-claim-replication", "claim", class_id="AF-WCC-VAC-GEN",
                     class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
                     conclusion_type="formal_model", node_id="F1", task_id="W066-REV25-VERDICT-01",
                     statement=(f"At the pinned FROZEN-rev25 byte set (schemas 9a8bd4c9/b6123750/1bb78ce9, "
                                f"gates 000e09e4+c79d8ab8, corpus bound to C0 1bb78ce9) an independent "
                                f"re-implementation of the two-stage acceptance measurement reproduces the "
                                f"frozen result exactly: canonical {sum(1 for r in rep['canonical'] if r['structural'] and r['semantic'])}/3 pass both "
                                f"stages, controls {rep['controls_pass']}/{rep['controls_total']}, union "
                                f"{rep['aggregates']['union_caught']}/{rep['aggregates']['total']} mutants "
                                f"caught (structural {rep['aggregates']['structural_caught']}, semantic "
                                f"{rep['aggregates']['semantic_caught']}); agreement with "
                                f"artifacts/formulation/evidence/acceptance_pipeline_report.json#9b7d6c82 is exact. "
                                f"Independently, four cross-checks fail on the same bytes: duplicate YAML keys "
                                f"x3 schemas, F2b :157/:244 contradiction, R17-R31 enforced but undeclared, "
                                f"F0 alias tokens + 2-vs-7 variant divergence. The replicated numbers are "
                                f"machine-green; the artifacts are not yet acceptable as written."),
                     assumptions=[
                         "a verdict binds bytes, not paths; every measurement used pinned/ copies",
                         "the two gates are run as published (no --hardened flag, frozen rule_spec passed explicitly)",
                         "union escape is defined as accepted by BOTH stages; controls must pass both",
                         "the pinned FROZEN.json rev25 is the declaration of record for the target hashes"],
                     falsifier=("re-run run_replica.py + crosschecks.py on the same pins: the claim is falsified "
                                "if union_caught != 31, or a canonical schema or control fails a stage, or the "
                                "frozen report disagrees, or yaml.compose returns no duplicate keys, or F2b "
                                ":157 matches :244, or rule_spec#40f9bb9e declares R17-R31, or F0 classes "
                                "AF-SCC-C2/C0 conclusion.type equals the canonical token, or the F0 inline "
                                "variant set equals the registry's"),
                     evidence_refs=[f"{base}/evidence/replica_verdicts.json#{hashes['evidence/replica_verdicts.json'][:12]}",
                                    f"{base}/evidence/acceptance_comparison.json#{hashes['evidence/acceptance_comparison.json'][:12]}",
                                    f"{base}/evidence/crosschecks.json#{hashes['evidence/crosschecks.json'][:12]}",
                                    f"{base}/pinned_manifest.json#{hashes['pinned_manifest.json'][:12]}"],
                     artifact_refs=[f"{base}/report.json#{hashes['report.json'][:12]}"]))

    events.append(ev("w066-rev25-complete", "status", node_id="F1", class_id="AF-WCC-VAC-GEN",
                     class_ids=["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
                     status="active", hours=0.6, task_id="W066-REV25-VERDICT-01",
                     summary=("W066-REV25-VERDICT-01 complete: 5 reviewer verdicts emitted (3 schemas, F0, "
                              "rule_spec; all revise with named B findings), 6 artifact events, 1 replication "
                              "claim; all files exist on disk and are hash-pinned. This is a completion claim, "
                              "not a node/gate transition (workers cannot set done/passed). Checkpoint follows."),
                     evidence_refs=[f"{base}/report.json#{hashes['report.json'][:12]}",
                                    f"{base}/README.md#{hashes['README.md'][:12]}",
                                    f"{base}/evidence/crosschecks.json#{hashes['evidence/crosschecks.json'][:12]}"],
                     next_falsifier=("re-issue these verdicts after the B findings are fixed and re-frozen; any "
                                     "pinned-byte accept then supersedes this revise")))

    lines = [json.dumps(e, ensure_ascii=False) for e in events]
    with OUTBOX.open("a") as f:
        f.write("\n".join(lines) + "\n")

    # self-check: the file must parse and every line must validate
    for i, line in enumerate(OUTBOX.read_text().splitlines(), 1):
        validate_event(json.loads(line))
    print(f"wrote {len(events)} events to {OUTBOX}")
    for e in events:
        print(" ", e["event_type"], e["event_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
