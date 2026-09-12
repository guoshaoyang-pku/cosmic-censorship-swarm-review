#!/usr/bin/env python3
"""One-shot: run the instrument, write report.json, compute hashes, emit outbox events.

Idempotent-ish: regenerates the report from the live files each run and writes the
outbox messages with fresh event ids. Does NOT ingest (controller does that).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))


def find_root(start: str) -> str:
    cur = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.isdir(os.path.join(cur, "research_map")) and os.path.isdir(os.path.join(cur, "schemas")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise RuntimeError("swarm root not found")
        cur = parent


ROOT = find_root(__file__)
OUTDIR = os.path.join(ROOT, "artifacts", "worker-031", "f1_rebind_adjudication")
INSTR = os.path.join(OUTDIR, "recheck_f1_rebind_031.py")
REPORT = os.path.join(OUTDIR, "report.json")
ANALYSIS = os.path.join(OUTDIR, "ANALYSIS.md")
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-031.jsonl")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def now():
    return datetime.now(CST).replace(microsecond=0).isoformat()


def main():
    # 1. regenerate report from live inputs
    with open(REPORT, "w", encoding="utf-8") as fh:
        r = subprocess.run([sys.executable, INSTR], stdout=fh, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return 1
    rep = json.load(open(REPORT, encoding="utf-8"))
    rep["created_at"] = now()
    rep["artifact_id"] = "artifacts/worker-031/f1_rebind_adjudication/report.json"
    rep["worker"] = "worker-031"
    # pin hashes of this worker's own outputs as measured
    rep["worker_outputs"] = {
        "instrument": {"path": "artifacts/worker-031/f1_rebind_adjudication/recheck_f1_rebind_031.py",
                        "sha256": sha256_file(INSTR)},
        "report": {"path": "artifacts/worker-031/f1_rebind_adjudication/report.json"},
        "analysis": {"path": "artifacts/worker-031/f1_rebind_adjudication/ANALYSIS.md",
                      "sha256": sha256_file(ANALYSIS) if os.path.exists(ANALYSIS) else None},
    }
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    rep_sha = sha256_file(REPORT)
    instr_sha = sha256_file(INSTR)
    ana_sha = sha256_file(ANALYSIS) if os.path.exists(ANALYSIS) else None
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    pins = rep["pins"]
    f1_sha = pins["F1_canonical"]["sha256"]
    f0_sha = pins["F0_canonical"]["sha256"]
    suite_sha = pins["suite"]["sha256"]

    evidence = [
        f"schemas/f1_falsifier_tests.jsonl#{suite_sha[:12]}",
        f"schemas/af_wcc_vacuum.yaml#{f1_sha[:12]}",
        f"research_map/formulation_taxonomy.yaml#{f0_sha[:12]}",
        "artifacts/worker-031/f1_rebind_adjudication/report.json",
        "artifacts/worker-031/f1_rebind_adjudication/recheck_f1_rebind_031.py",
        "artifacts/worker-031/f1_rebind_adjudication/ANALYSIS.md",
    ]
    falsifier = (
        "Any of the three pins moving (F1 canonical, F0 canonical, suite), or a re-run of "
        "recheck_f1_rebind_031.py showing C-A/C-B failing, or the F1-AMB-25 expected/cross_artifact "
        "F0 value being updated to the live F0 hash so the deciding probe recomputes true — each "
        "voids or repairs this finding."
    )

    events = [
        {
            "event_id": f"w031-f1-rebind-artifact-report-{ts}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-031",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "f1_rebind_probe_recompute",
            "path": "artifacts/worker-031/f1_rebind_adjudication/report.json",
            "sha256": rep_sha,
            "validation_status": "unverified",
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w031-f1-rebind-artifact-instrument-{ts}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-031",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "measurement_instrument",
            "path": "artifacts/worker-031/f1_rebind_adjudication/recheck_f1_rebind_031.py",
            "sha256": instr_sha,
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/worker-031/f1_rebind_adjudication/report.json"],
            "falsifier": "A reviewer re-running the instrument and not reproducing report.json's census/controls voidsthe measurement.",
        },
        {
            "event_id": f"w031-f1-rebind-artifact-analysis-{ts}",
            "event_type": "artifact",
            "created_at": now(),
            "actor": "worker-031",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "finding_analysis",
            "path": "artifacts/worker-031/f1_rebind_adjudication/ANALYSIS.md",
            "sha256": ana_sha,
            "validation_status": "unverified",
            "evidence_refs": ["artifacts/worker-031/f1_rebind_adjudication/report.json"],
            "falsifier": falsifier,
        },
        {
            "event_id": f"w031-f1-rebind-blocker-{ts}",
            "event_type": "blocker",
            "created_at": now(),
            "actor": "worker-031",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "description": (
                "schemas/f1_falsifier_tests.jsonl (sha256 56bcb4b3234b) was re-pinned to F1 rev12/rev13 "
                "at 00:32:31, but row F1-AMB-25 still carries the superseded F0 expectation "
                "276009f4f63d in its deciding probe and in cross_artifact, and still records pass=true. "
                "Recomputed against the live F0 canonical (0abb9ed8a961) the deciding equality probe is "
                "FALSE (and the binding_note 'astra-classscope-02' probe is FALSE). All 25 rows claim "
                "84/84 probes pass; against the live canonical pair 82/84 pass. This is the exact "
                "staleness the row was written to detect, now asserting a false outcome itself."
            ),
            "needed_to_unblock": (
                "Formulation lead (owner of astra-life03-repin-claims): update F1-AMB-25's "
                "f0_binding.declared_f0_sha256 expected value and cross_artifact[0].sha256 to the live "
                "F0 canonical 0abb9ed8a961 (or re-derive the row if the F0 revision is contested), "
                "re-run the row's probes, and re-emit the suite artifact event + sha256. Controller: "
                "do not bind a G-FORM verdict to this suite's 84/84 pass claim until repaired or the "
                "two probes are explicitly dispositioned."
            ),
            "evidence_refs": evidence,
            "falsifier": falsifier,
        },
        {
            "event_id": f"w031-f1-rebind-status-{ts}",
            "event_type": "status",
            "created_at": now(),
            "actor": "worker-031",
            "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN",
            "gate": "G-FORM",
            "status": "blocked",
            "hours": 0.6,
            "summary": (
                "Bounded F1 task: re-measure the 25-row falsifier suite against the post-repin state. "
                "Controls all pass: replay on the pre-revision snapshot reproduces 84/84 recorded "
                "outcomes, mutation control detects, all 25 rows are uniformly re-pinned to F1 "
                "cce9c60146d6, and the schema's own f0_binding is live. One defect found: F1-AMB-25 "
                "asserts the superseded F0 hash 276009f4f63d as pass=true for its deciding probe and "
                "in cross_artifact; against live F0 0abb9ed8a961 it is false. Census 82/84. Reported as "
                "a blocker for the formulation owner; no gate verdict, no node status, no file edited."
            ),
            "evidence_refs": evidence,
            "next_falsifier": (
                "Re-run the instrument after the formulation owner repairs F1-AMB-25; if the deciding "
                "probe recomputes true at the then-live F0 hash and C-A/C-B still pass, the defect is "
                "repaired and this blocker closes. If instead the F0 revision that invalidated the row "
                "is itself reverted, re-measure before closing."
            ),
        },
    ]

    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    print(json.dumps({
        "report": REPORT, "report_sha256": rep_sha,
        "instrument_sha256": instr_sha, "analysis_sha256": ana_sha,
        "adjudication": rep["adjudication"],
        "recorded_pass": rep["census"]["recorded_pass"],
        "recomputed_pass_current": rep["census"]["recomputed_pass_current"],
        "events_appended": len(events),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
