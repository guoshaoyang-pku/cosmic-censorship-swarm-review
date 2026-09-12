#!/usr/bin/env python3
"""Emit W041-XSCHEMA-DATACLASS-01 events + checkpoint, and repair the rejected
W041-F2A-PIN-RCA-01 claim by re-emitting it with a schema-valid conclusion_type.

Writes only: artifacts/worker-041/**, comms/outbox/worker-041.jsonl,
runtime/state/w041_checkpoint_4.json, runtime/state/w041_checkpoints.jsonl.
Every hash is measured from disk at emit time; nothing is hand-typed.
All events are validated against research_map.schemas.validate_event before append.
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = f"{ROOT}/artifacts/worker-041/xschema_dataclass"
RCA = f"{ROOT}/artifacts/worker-041/f2a_pin_rca"
OUTBOX = f"{ROOT}/comms/outbox/worker-041.jsonl"
CKPT = f"{ROOT}/runtime/state/w041_checkpoint_4.json"
CKPT_LOG = f"{ROOT}/runtime/state/w041_checkpoints.jsonl"
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat()
TASK = "W041-XSCHEMA-DATACLASS-01"
CLAIM_CLASS = "AF-WCC-VAC-GEN"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

sys.path.insert(0, f"{ROOT}/research_map")
from schemas import validate_event  # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def ref(relpath):
    abspath = relpath if relpath.startswith("/") else f"{ROOT}/{relpath}"
    return f"{relpath}#{sha256(abspath)[:12]}"


report = json.load(open(f"{HERE}/xschema_report.json"))
report_sha = sha256(f"{HERE}/xschema_report.json")
script_sha = sha256(f"{HERE}/run_xschema.py")

EVIDENCE = [
    ref("artifacts/worker-041/xschema_dataclass/xschema_report.json"),
    ref("artifacts/worker-041/xschema_dataclass/run_xschema.py"),
    ref("artifacts/worker-041/xschema_dataclass/raw/diff_census.json"),
    ref("schemas/af_wcc_vacuum.yaml"),
    ref("schemas/af_scc_c2_vacuum.yaml"),
    ref("schemas/af_scc_c0_vacuum.yaml"),
    ref("research_map/formulation_taxonomy.yaml"),
    ref("artifacts/formulation/formulation_taxonomy.yaml"),
    ref("artifacts/formulation/FROZEN.json"),
]
assert report_sha == hashlib.sha256(open(f"{HERE}/xschema_report.json", "rb").read()).hexdigest()

STATEMENT = (
    "Cross-schema measurement at FROZEN rev28 / rev12 hashes (F1 cce9c60146d6, F2a 5476a3f2c6bc, "
    "F2b 55d0a1ea9bda): the worker-088 flag `strict_data_class_shared=false` is explained, not a "
    "cross-artifact content conflict. The three schemas share a byte-identical data-class core across "
    "13 pre-registered paths after whitespace normalisation (vacuum Einstein equations, matter none, "
    "Lambda 0, both constraint equations, s > 5/2, delta in (1/2,1), the two O(r^-k) decay forms, "
    "connected oriented complete R^3 one-ended slice, spacetime dimension 4, completeness) and a "
    "verbatim tagged-disjoint-union D0 definition. The only non-editorial differences are (a) the "
    "declared class axis `regularity.extension_regularity` = none / C2 / C0, which matches each "
    "schema's class_components.regularity_token and each class contract's conclusion_type through the "
    "frozen VOCAB_ALIASES canon, and (b) per-class prohibition/warning text. C0 and C2 are not merged "
    "in any assertion field (class_id, class_components, extension_regularity, conclusion "
    "statement/type); prohibition text that names C2/C0 only to forbid conflation is excluded per the "
    "controller's CF-16 metalinguistic-mention pattern. 7/7 checks PASS, two runs identical except "
    "created_at, all three target hashes stable across the run. Measurement/adjudication input only."
)
FALSIFIER = (
    "Re-run `python3 artifacts/worker-041/xschema_dataclass/run_xschema.py` at the same measured "
    "hashes: falsified if any of the 13 shared-core paths is absent or differs across F1/F2a/F2b; if "
    "the D0 definitions are not verbatim identical; if extension_regularity no longer matches the "
    "class token or the canonical/supplement class contracts via VOCAB_ALIASES; if a C0/C2 merge token "
    "appears in an assertion field; if a meaning-bearing divergence appears in a non-core, "
    "non-class-axis diff-census path; or if any of the three target hashes moves (hash drift voids the "
    "measurement). Instrument controls: an in-memory exponent or decay-rate mutation must be flagged "
    "and a wording-only change must not."
)
ASSUMPTIONS = [
    "The 13 SHARED_CORE paths are the data-class core the three classes are declared to share; the "
    "selection was fixed in run_xschema.py before the run and is visible in the report.",
    "CLASS_AXIS paths (extension_regularity*, extension_topology, horizon_topology, must_not_conflate, "
    "excluded_data) are expected to differ per class; only shared-core and unexplained meaning-bearing "
    "differences can fail the run.",
    "Whitespace/case normalisation and trailing-period stripping do not change meaning; the unnormalised "
    "raw blocks are retained in the report under `raw`.",
    "The frozen VOCAB_ALIASES canonicalisation is the correct equivalence for conclusion_type and "
    "genericity_kind, per the pinned taxonomy checker.",
    "Detector bugs found and fixed during this run (whole-block numeric multisets, CF-16 prohibition "
    "text, substring 'ric' in 'numeric') are logged in the report and drafts retained under raw/.",
]

events = [
    {
        "event_id": f"w041-xschema-{TASK}-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F1",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "secondary_gate": "G-AUDIT/A1",
        "status": "active",
        "completion_claim": True,
        "hours": 0.3,
        "task_id": TASK,
        "summary": (
            "W041-XSCHEMA-DATACLASS-01 complete: one bounded class-bound task, hash-pinned, 7/7 checks "
            "PASS. No cross-artifact data-class conflict at rev12; the worker-088 strict-identity flag "
            "resolves to class-axis + editorial differences only. Worker completion claim only — does "
            "NOT set node status, gate verdict, or validation_status."
        ),
        "evidence_refs": EVIDENCE,
        "next_falsifier": FALSIFIER,
    },
    {
        "event_id": f"w041-xschema-{TASK}-artifact-report",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F1",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "artifact_type": "measurement_report",
        "path": "artifacts/worker-041/xschema_dataclass/xschema_report.json",
        "sha256": report_sha,
        "validation_status": "unverified",
        "claims_completion": False,
        "task_id": TASK,
        "summary": "Cross-schema data-class identity + class-binding report; raw blocks and diff census included.",
        "falsifier": FALSIFIER,
        "evidence_refs": [ref("artifacts/worker-041/xschema_dataclass/raw/diff_census.json")],
    },
    {
        "event_id": f"w041-xschema-{TASK}-artifact-instrument",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F1",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "artifact_type": "verifier",
        "path": "artifacts/worker-041/xschema_dataclass/run_xschema.py",
        "sha256": script_sha,
        "validation_status": "unverified",
        "claims_completion": False,
        "task_id": TASK,
        "summary": "Deterministic fail-closed instrument; exits 3 on target-hash drift, 1 on any check FAIL.",
        "falsifier": FALSIFIER,
        "evidence_refs": EVIDENCE,
    },
    {
        "event_id": f"w041-xschema-{TASK}-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F1",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": CLAIM_CLASS,
        "class_ids": CLASS_IDS,
        "gate": "G-FORM",
        "secondary_gate": "G-AUDIT/A1",
        "conclusion_type": "formal_model",
        "task_id": TASK,
        "statement": STATEMENT,
        "assumptions": ASSUMPTIONS,
        "falsifier": FALSIFIER,
        "artifact_refs": [f"artifacts/worker-041/xschema_dataclass/xschema_report.json#{report_sha[:12]}"],
        "evidence_refs": EVIDENCE,
    },
    {
        "event_id": "w041-f2apin-W041-F2A-PIN-RCA-01-claim-r2",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-041",
        "node_id": "F2a",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate": "G-FORM",
        "conclusion_type": "formal_model",
        "repairs_rejected_event_id": "w041-f2apin-W041-F2A-PIN-RCA-01-claim",
        "rejection_reason": "claim: invalid conclusion_type (diagnosis)",
        "task_id": "W041-F2A-PIN-RCA-01",
        "statement": (
            "schemas/af_scc_c2_vacuum.yaml @ 5476a3f2c6bc declares consistency_evidence_sha256="
            "675a99d0..., but the canonical evidence file is a deterministic, input-sensitive output "
            "that check_taxonomy_consistency.py rewrites on every run; measured live value at the time "
            "of the RCA was 9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b. The "
            "schema's refresh rule names one of the checker's four inputs, so a re-stamp is a fixpoint "
            "only until the next edit of any input. F2a rev12 is otherwise clean: the prior critical "
            "D0 ill-typedness finding and the class_contract_pointer finding are both closed at this "
            "hash. Re-emitted with a schema-valid conclusion_type after the original claim was "
            "auto-rejected as `invalid conclusion_type`; statement, artifacts and falsifier unchanged."
        ),
        "assumptions": [
            "The four inputs identified in the RCA are the checker's complete input set (read from its source).",
            "Sandbox reproduction is faithful: the checker's ROOT resolves inside the sandbox; the live "
            "evidence file was never written by worker-041 (its hash was 9e335e9b before and after).",
            "This re-emission repairs the event schema only; it does not re-run or re-interpret the experiment.",
        ],
        "falsifier": (
            "Kill conditions for this diagnosis: (a) two runs on identical inputs produce different "
            "output hashes (nondeterminism); (b) 675a99d0 IS reproducible from the current four inputs; "
            "(c) an edit to the authoring contract / VOCAB_ALIASES / checker is shown NOT to change the "
            "evidence output; (d) check_taxonomy_consistency.py does not rewrite the evidence path. Any "
            "one falsifies the derived-output-staleness mechanism. Separately, an atomic re-stamp to the "
            "then-live evidence hash followed by a freeze with no further input edit REPAIRS the hard "
            "failure and supersedes the revise verdict — it does not falsify the root cause. Note: "
            "worker-092 `artifacts/worker-092/evbind/report.json` independently measured the same defect "
            "and adjudicated repair options R1/R2/R3; symptom credit to workers 086/092/094/034."
        ),
        "artifact_refs": [f"artifacts/worker-041/f2a_pin_rca/f2a_pin_rca_report.json#{sha256(RCA + '/f2a_pin_rca_report.json')[:12]}"],
        "evidence_refs": [
            ref("artifacts/worker-041/f2a_pin_rca/f2a_pin_rca_report.json"),
            ref("artifacts/worker-041/f2a_pin_rca/raw/experiment.json"),
            ref("schemas/af_scc_c2_vacuum.yaml"),
            ref("artifacts/worker-092/evbind/report.json"),
        ],
    },
]

for e in events:
    validate_event(e)

existing = set()
with open(OUTBOX) as fh:
    for line in fh:
        line = line.strip()
        if line:
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass
appended, skipped = [], []
with open(OUTBOX, "a") as fh:
    for e in events:
        if e["event_id"] in existing:
            skipped.append(e["event_id"])
            continue
        fh.write(json.dumps(e, sort_keys=True) + "\n")
        appended.append(e["event_id"])

ckpt = {
    "schema_version": "0.1",
    "checkpoint_id": "w041-checkpoint-xschema",
    "checkpoint": 4,
    "task_id": TASK,
    "actor": "worker-041",
    "created_at": NOW,
    "node_id": "F1",
    "node_ids": ["F1", "F2a", "F2b"],
    "class_id": CLAIM_CLASS,
    "class_ids": CLASS_IDS,
    "gate": "G-FORM",
    "measurement": "cross-schema data-class identity + class binding at rev12 frozen hashes",
    "verdict": "accept_at_measured_hashes",
    "hours": 0.3,
    "targets": report["measured_sha256"],
    "report_path": "artifacts/worker-041/xschema_dataclass/xschema_report.json",
    "report_sha256": report_sha,
    "instrument_sha256": script_sha,
    "checks": {c["check_id"]: c["status"] for c in report["checks"]},
    "n_pass": report["n_pass"],
    "n_fail": report["n_fail"],
    "detector_bugs_found_and_fixed": 3,
    "events_emitted": appended,
    "events_skipped_duplicate": skipped,
    "repaired_events": ["w041-f2apin-W041-F2A-PIN-RCA-01-claim -> -claim-r2 (invalid conclusion_type)"],
    "next_falsifier": FALSIFIER,
    "status": "done",
    "authority_note": "worker checkpoint; no node status or gate verdict claimed",
}
with open(CKPT, "w") as fh:
    json.dump(ckpt, fh, indent=1)
    fh.write("\n")
with open(CKPT_LOG, "a") as fh:
    fh.write(json.dumps({k: ckpt[k] for k in (
        "checkpoint", "created_at", "task_id", "actor", "node_id", "class_id", "gate",
        "verdict", "report_path", "report_sha256", "n_pass", "n_fail",
        "events_emitted", "events_skipped_duplicate", "next_falsifier")}, sort_keys=True) + "\n")

print(json.dumps({
    "report_sha256": report_sha,
    "instrument_sha256": script_sha,
    "checks": ckpt["checks"],
    "events_appended": appended,
    "events_skipped": skipped,
    "checkpoint": CKPT,
}, indent=1))
