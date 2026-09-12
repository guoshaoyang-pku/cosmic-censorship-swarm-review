#!/usr/bin/env python3
"""W064-CHURN-01: emit schema-validated upward events for worker-064.

Every event is validated with research_map.schemas.validate_event before it is appended.
Writes only comms/outbox/worker-064.jsonl.
"""
import hashlib, json, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
from schemas import validate_event  # noqa: E402

OUT = os.path.join(ROOT, "comms", "outbox", "worker-064.jsonl")
NOW = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def ref(name):
    return f"artifacts/worker-064/churn_audit/{name}#{sha(os.path.join(HERE, name))}"

REPORT = ref("report.json")
SAMPLES = ref("samples.jsonl")
MEAS = ref("measurements.json")
MANIFEST = ref("manifest.sha256")

events = [
    {
        "event_id": "w064-churn-01-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-064",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact_type": "publication_stability_binding_audit",
        "path": "artifacts/worker-064/churn_audit/report.json",
        "sha256": sha(os.path.join(HERE, "report.json")),
        "validation_status": "unverified",
        "evidence_refs": [SAMPLES, MEAS],
        "summary": "90 s / 18-sample read-only audit: canonical hashes constant and FROZEN rev25 manifest-bound; the four hashes advertised as final matched 0/18 samples; frozen_at future-dated by 1316 s; F0 canonical/authoring dual-tree divergence 18/18.",
        "falsifier": "Re-run sample_churn.py >=90 s: any canonical hash change at constant FROZEN revision falsifies stability; any sample matching all four advertised hashes falsifies the stale-pin finding; frozen_at <= first-sample wall clock falsifies future-dating; canonical/authoring F0 byte-identity falsifies divergence.",
        "claims_completion": False,
    },
    {
        "event_id": "w064-churn-01-artifact-samples",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-064",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact_type": "churn_sample_log",
        "path": "artifacts/worker-064/churn_audit/samples.jsonl",
        "sha256": sha(os.path.join(HERE, "samples.jsonl")),
        "validation_status": "unverified",
        "evidence_refs": [MANIFEST],
        "summary": "Raw machine evidence: 18 samples x 11 paths x {sha256,bytes,mtime_ns} plus per-sample FROZEN revision/manifest comparison; append-only JSONL.",
        "falsifier": "A line that fails SHA-256 re-hash, or a timestamp out of monotone order, invalidates this evidence file.",
        "claims_completion": False,
    },
    {
        "event_id": "w064-churn-01-artifact-measurements",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-064",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "artifact_type": "churn_measurements",
        "path": "artifacts/worker-064/churn_audit/measurements.json",
        "sha256": sha(os.path.join(HERE, "measurements.json")),
        "validation_status": "unverified",
        "evidence_refs": [SAMPLES, REPORT],
        "summary": "Derived per-path table: distinct hashes, change intervals, last-write instants, FROZEN manifest mismatch counts, advertised-pin match counts, verdict rule.",
        "falsifier": "Recompute from samples.jsonl; any per-path number that disagrees with the raw samples falsifies the derivation.",
        "claims_completion": False,
    },
    {
        "event_id": "w064-churn-01-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-064",
        "node_id": "F0",
        "gate": "G-F0",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "statement": "Measured over 2026-09-12T00:20:04-00:21:29+08:00 (18 samples, 5 s cadence): (1) the four frozen-class canonical artifacts were hash-stable and FROZEN.json rev25 manifest-matched at 18/18 samples (F0 276009f4f63d, F1 9a8bd4c96800, F2a b6123750b37d, F2b 1bb78ce9b357); (2) the four hashes advertised as final in leadform-resource-request-2026-09-12T00:34:00+08:00 matched 0/18 samples; (3) FROZEN rev25 frozen_at=00:42:00 is 1316 s after the window start and after its own mtime 00:19:46; (4) canonical vs authoring F0 taxonomy diverged in 18/18 samples while the three schema mirrors were byte-identical.",
        "conclusion_type": "numerical_evidence",
        "assumptions": [
            "the four canonical paths are the binding artifacts named in FROZEN.json and the formulation comms",
            "wall-clock sample timestamps are the reference for the frozen_at skew check",
            "leadform-resource-request-2026-09-12T00:34:00+08:00 is the advertised-final-pin message; its hashes were quoted verbatim",
        ],
        "falsifier": "Re-run sample_churn.py over >=90 s: any canonical hash change at constant FROZEN revision falsifies (1); any sample matching all four advertised hashes falsifies (2); frozen_at <= first-sample wall clock falsifies (3); canonical/authoring F0 byte-identity across samples falsifies (4).",
        "evidence_refs": [REPORT, SAMPLES, MEAS],
        "artifact_refs": ["artifacts/worker-064/churn_audit/report.json"],
        "not_claimed": "no gate verdict, no node completion, no mathematical verdict on any schema, no attribution of intent",
    },
    {
        "event_id": "w064-churn-01-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-064",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "status": "active",
        "hours": 0.3,
        "summary": "W064-CHURN-01 complete at worker level (no assignment card existed for worker-064). Verdict STABLE_FROZEN_BOUND_WITH_BINDING_DEFECTS. Actionable: correct the advertised final hashes, replace the future-dated FROZEN stamp, reconcile the F0 authoring copy, then re-run this sampler to certify a quiet binding window. Not a node transition: status stays active and no gate is touched.",
        "evidence_refs": [REPORT, SAMPLES],
        "next_falsifier": "Re-run artifacts/worker-064/churn_audit/sample_churn.py after the publisher is quiesced and the advertised pins/FROZEN stamp are corrected; zero canonical changes, 4/4 advertised hashes matching, non-future frozen_at, and byte-identical F0 trees closes the finding.",
    },
    {
        "event_id": "w064-churn-01-blocker",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "worker-064",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "description": "Binding-instruction inconsistency measured, not inferred: (F-CHURN-2) the hashes advertised as final in leadform-resource-request-2026-09-12T00:34:00+08:00 and leadform-blocker-0005 (68392dd8, 4f97273e, a2aef5ac, 0fcc6a19) matched the live canonical files in 0/18 samples; live+manifest-bound set is 9a8bd4c96800, b6123750b37d, 1bb78ce9b357, 276009f4f63d under FROZEN rev25. (F-CHURN-3) FROZEN rev25 frozen_at=2026-09-12T00:42:00+08:00 is future-dated vs its own mtime 00:19:46 (+1316 s vs window start). (F-CHURN-4) F0 canonical 276009f4f63d vs authoring c8e979a1eb48 diverged in 18/18 samples. Any reviewer who follows the comms pins reviews non-canonical bytes; this is the mechanical cause of the standing 'no independent verdict binds the FINAL hashes' blocker.",
        "needed_to_unblock": "(1) re-issue the advertised final-hash set at the live/FROZEN rev25 hashes or republish at the advertised ones; (2) replace the future-dated frozen_at with the actual freeze instant; (3) publish the F0 authoring copy byte-identically to canonical; (4) keep the publisher quiesced while reviewers run, then have a worker re-run W064-CHURN-01 to certify a quiet window.",
        "evidence_refs": [REPORT, SAMPLES, MEAS],
        "falsifier": "A re-run window in which all four advertised hashes match live files, frozen_at precedes the window, and F0 canonical/authoring are byte-identical falsifies this blocker.",
    },
]

written = []
with open(OUT, "a") as f:
    for e in events:
        validate_event(e)          # raises SchemaError on any invalid event
        f.write(json.dumps(e, sort_keys=True) + "\n")
        written.append((e["event_id"], e["event_type"]))
print(json.dumps({"outbox": "comms/outbox/worker-064.jsonl", "written": written,
                  "report_sha256": sha(os.path.join(HERE, "report.json")),
                  "samples_sha256": sha(os.path.join(HERE, "samples.jsonl"))}, indent=1))
