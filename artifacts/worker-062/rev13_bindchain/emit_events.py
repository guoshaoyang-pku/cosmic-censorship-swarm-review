#!/usr/bin/env python3
"""Emit worker-062 rev13 bind-chain events and the worker checkpoint.

Idempotent: an event whose event_id already exists in comms/outbox/worker-062.jsonl is skipped.
Exit 0 on success, 2 on validation failure.  No canonical artifact is written.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-062.jsonl"
STATE = ROOT / "runtime/state/worker-062_rev13_bindchain_checkpoint.json"
CST = timezone(timedelta(hours=8))
TASK = "W062-GFORM-REV13-BINDCHAIN-RETEST-01"
ACTOR = "worker-062"
NODES = ["F1", "F2a", "F2b"]
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-FORM"
CLS = "AF-SCC-C0-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main() -> int:
    ts = datetime.now(CST).isoformat(timespec="seconds")
    tag = f"w062-rev13-{ts}"
    report = json.loads((HERE / "report.json").read_text())
    files = {
        "report.json": "artifact_report",
        "verify_rev13_bindchain.py": "deterministic_read_only_harness",
        "PREREGISTRATION.json": "preregistration",
        "controls.json": "controls",
        "entry_hashes.json": "entry_hashes",
        "README.md": "documentation",
    }
    hashes = {name: sha(HERE / name) for name in files}
    href = {name: f"artifacts/worker-062/rev13_bindchain/{name}#{h[:12]}" for name, h in hashes.items()}
    subjects = [f"{s['path']}#{s['sha256'][:12]}" for s in report["subjects"]]
    evidence = [href["report.json"], href["PREREGISTRATION.json"], href["entry_hashes.json"],
                f"artifacts/formulation/FROZEN.json#{report['frozen_manifest']['sha256'][:12]}"] + subjects + \
               ["artifacts/formulation/evidence/semantic_escape_rebased.json#7e44de0e3906",
                "artifacts/formulation/evidence/acceptance_pipeline_report.json#9b7d6c8208d3",
                "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf"]
    v = report["verdict"]
    hard = v["hard_failures"]

    checkpoint = {
        "checkpoint_id": f"worker-062-rev13-bindchain-{ts}",
        "task_id": TASK,
        "worker": ACTOR,
        "created_at": ts,
        "node_id": "F2b",
        "nodes": NODES,
        "class_id": CLS,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "verdict": v["value"],
        "score": v["score"],
        "hard_failure_ids": v["hard_failure_ids"],
        "counts_as_full_schema_verdict": False,
        "subjects": report["subjects"],
        "frozen_manifest": report["frozen_manifest"],
        "entry_hashes_t0": report["entry_hashes"]["t0"],
        "entry_hashes_t1": report["entry_hashes"]["t1"],
        "drift": report["entry_hashes"]["drift"],
        "artifacts": {f"artifacts/worker-062/rev13_bindchain/{k}": h for k, h in hashes.items()},
        "checkpoint_self_sha256": "excluded (self-reference); measured by the emitting script and carried in the "
                                  "artifact/status events",
        "report_sha256": hashes["report.json"],
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
        "authority_note": report["authority_note"],
        "exit": "worker exits; no node status, validation_status=passed or gate verdict set",
    }
    ck = HERE / "CHECKPOINT.json"
    ck.write_text(json.dumps(checkpoint, indent=2) + "\n")
    chash = sha(ck)
    href["CHECKPOINT.json"] = f"artifacts/worker-062/rev13_bindchain/CHECKPOINT.json#{chash[:12]}"
    STATE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ck, STATE)

    events = []

    def ev(event_id, event_type, **kw):
        d = {"event_id": event_id, "event_type": event_type, "created_at": ts, "actor": ACTOR,
             "node_id": "F2b", "nodes": NODES, "class_id": CLS, "class_ids": CLASS_IDS,
             "gate": GATE, "task_id": TASK}
        d.update(kw)
        events.append(d)

    ev(f"{tag}-status-open", "status", status="active", hours=0.5,
       summary=("No assignment card exists in comms/inbox for worker-062 (relaunched slot). Took ONE bounded "
                "class-bound task, W062-GFORM-REV13-BINDCHAIN-RETEST-01: independent read-only re-test of the "
                "evidence-binding chain of F1/F2a/F2b at the rev13 / FROZEN rev29 bytes, re-testing the rev12 "
                "blocking defect classes (C06 stale consistency hash, C10 stale two-stage acceptance corpus) plus "
                "class separation and structural-gate reproduction."),
       evidence_refs=evidence, reviewed_sha256=report["subjects"][2]["sha256"],
       next_falsifier=report["next_falsifier"])

    for name, atype in files.items():
        ev(f"{tag}-artifact-{name.split('.')[0].lower()}", "artifact", artifact_type=atype,
           path=f"artifacts/worker-062/rev13_bindchain/{name}", sha256=hashes[name],
           validation_status="unverified", artifact_refs=[href[name]], evidence_refs=evidence,
           falsifier="The file's measured sha256 differs from the one declared here.",
           summary=f"W062 rev13 bind-chain {atype.replace('_', ' ')}: {name} (sha256 {hashes[name][:12]}).")
    ev(f"{tag}-artifact-checkpoint", "artifact", artifact_type="checkpoint",
       path="artifacts/worker-062/rev13_bindchain/CHECKPOINT.json", sha256=chash,
       validation_status="unverified", artifact_refs=[href["CHECKPOINT.json"]], evidence_refs=evidence,
       falsifier="The checkpoint's declared artifact hashes or pins do not match the files on disk.",
       summary="Worker checkpoint: pins, T0/T1 entry hashes, verdict, artifact hashes, falsifiers.")

    ev(f"{tag}-claim", "claim",
       statement=("Artifact-and-checker measurement (not a mathematics or physics claim): at FROZEN rev29 "
                  f"({report['frozen_manifest']['sha256'][:12]}) the three schemas measure F1 d9cebb9404b2, F2a "
                  "e9a27996dfd3, F2b b2ab6acb2bbe; the C06-class consistency-evidence binding is CLEARED (declared == "
                  "measured == pinned 9e335e9ba1bf in all three); the C10-class two-stage acceptance criterion is NOT "
                  "reproducible: semantic_escape_rebased.json still binds rev11 C0 1bb78ce9b357 while C0 measures "
                  "b2ab6acb2bbe, the canonical pipeline's fail-closed preflight exits 3 in a mirror sandbox, and after a "
                  "mechanical rebase the pipeline still FAILs because the semantic stage rejects canonical F1 on R03 "
                  "(binder '(q,t0)' absent from quantifiers.formal). Pin identity, class separation and the structural "
                  "gate are clean (3/3 pass); 8/8 controls behave as declared; the rebased mutation corpus is still "
                  "caught 31/31 by the union of the two stages."),
       conclusion_type="artifact_measurement",
       assumptions=["the FROZEN rev29 manifest pins are the binding reference at measurement time",
                    "the canonical tools (check_class_schema.py, run_acceptance.py, measure_semantic_escape.py, "
                    "spec_conformance_audit.py) are the declared acceptance machinery",
                    "the pipeline is reproduced only on a byte copy under ./sandbox; canonical bytes are read-only",
                    "no ledger, schema, manifest or evidence file was edited or re-pointed"],
       falsifier=report["falsifier"], evidence_refs=evidence,
       artifact_refs=[href["report.json"], href["verify_rev13_bindchain.py"], href["controls.json"],
                      href["entry_hashes.json"]])

    findings = [
        {"id": "HF-W062-REV13-01", "severity": "blocking-for-clean-accept",
         "finding": hard[0]["finding"], "falsifier": hard[0]["falsifier"], "evidence": hard[0]["evidence_refs"]},
        {"id": "HF-W062-REV13-02", "severity": "evidence-binding",
         "finding": hard[1]["finding"], "falsifier": hard[1]["falsifier"], "evidence": hard[1]["evidence_refs"]},
        {"id": "O-W062-01", "severity": "observation-post-hoc",
         "finding": report["post_hoc_observations"][0]["finding"],
         "falsifier": "Show quantifiers.formal containing the literal '(q,t0)' at F1 d9cebb9404b2, or an auditor run "
                      "accepting canonical F1 without a notation change.",
         "evidence": report["post_hoc_observations"][0]["evidence_refs"]},
        {"id": "P-W062-01", "severity": "positive",
         "finding": ("C06-class cleared at rev13: declared consistency_evidence_sha256 == measured 9e335e9ba1bf == "
                     "FROZEN rev29 pin in all three schemas."),
         "evidence": ["artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf"]},
        {"id": "P-W062-02", "severity": "positive",
         "finding": ("Pin identity, class separation and structural gate clean at rev13; 8/8 controls behave as declared; "
                     "the rebased mutation corpus is still caught 31/31 by the union."),
         "evidence": [f"artifacts/formulation/FROZEN.json#{report['frozen_manifest']['sha256'][:12]}",
                      "artifacts/formulation/tools/check_class_schema.py",
                      href["report.json"]]},
    ]
    ev(f"{tag}-review", "review", target_id="F1,F2a,F2b@FROZEN-rev29",
       reviewer=ACTOR, verdict=v["value"], score=v["score"],
       hard_failures=[{"id": h["id"], "severity": h["severity"], "finding": h["finding"],
                       "falsifier": h["falsifier"], "evidence_refs": h["evidence_refs"]} for h in hard],
       findings=findings, evidence_refs=evidence,
       reviewed_sha256=report["subjects"][2]["sha256"],
       counts_as_full_schema_verdict=False,
       falsifier=report["falsifier"],
       summary=("Independent binding-chain review of F1/F2a/F2b at FROZEN rev29: revise 3.0, 2 hard failures "
                "(not reproducible two-stage acceptance; pinned acceptance report records no base hash). Not a "
                "full-schema verdict; does not consume a G-FORM reviewer slot."))

    ev(f"{tag}-status-complete", "status", status="active", hours=0.5,
       summary=("CHECKPOINT + EXIT. W062-GFORM-REV13-BINDCHAIN-RETEST-01 complete at worker level: one bounded "
                "class-bound task, 22 checks and 8/8 controls, verdict revise 3.0 with HF-W062-REV13-01 (two-stage "
                "acceptance not reproducible: stale corpus base 1bb78ce9 vs C0 b2ab6acb; even rebased, F1 is rejected "
                "by the semantic stage on R03) and HF-W062-REV13-02 (pinned acceptance report records no base hash). "
                "C06-class cleared; pin identity, class separation and structural gate clean; canonical bytes untouched; "
                "no node status, validation_status or gate verdict set."),
       evidence_refs=evidence,
       artifact_refs=[href["report.json"], href["verify_rev13_bindchain.py"], href["PREREGISTRATION.json"],
                      href["controls.json"], href["entry_hashes.json"], href["README.md"], href["CHECKPOINT.json"],
                      "runtime/state/worker-062_rev13_bindchain_checkpoint.json"],
       reviewed_sha256=report["subjects"][2]["sha256"],
       next_falsifier=report["next_falsifier"])

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:  # noqa: BLE001
                    pass
    new = [e for e in events if e["event_id"] not in existing]
    with OUTBOX.open("a") as fh:
        for e in new:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    # schema validation: every event must carry the base fields and its type's required fields
    req = {"status": [], "claim": ["class_id", "statement", "conclusion_type", "assumptions", "falsifier", "evidence_refs"],
           "artifact": ["node_id", "artifact_type", "path", "sha256", "validation_status"],
           "review": ["target_id", "reviewer", "verdict", "score", "hard_failures", "findings"]}
    bad = []
    for e in events:
        for k in ["event_id", "event_type", "created_at", "actor"] + req[e["event_type"]]:
            if k not in e or e[k] is None:
                bad.append((e["event_id"], k))
    print(json.dumps({"emitted": len(new), "skipped": len(events) - len(new), "schema_missing": bad,
                      "outbox": str(OUTBOX.relative_to(ROOT)), "checkpoint": str(STATE.relative_to(ROOT)),
                      "checkpoint_sha256": chash, "report_sha256": hashes["report.json"]}, indent=2))
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
