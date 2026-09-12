#!/usr/bin/env python3
"""Emit W083-REF01-REV29-DISPOSITION-01 upward events to comms/outbox/worker-083.jsonl.

Idempotent: an event whose event_id already appears in the outbox is not re-appended.
Writes only the outbox (append) and a local events.jsonl copy. No canonical artifact touched.
"""
import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/worker-083/ref01_rev29_disposition"
OUTBOX = ROOT / "comms/outbox/worker-083.jsonl"
TASK = "W083-REF01-REV29-DISPOSITION-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE = "F0,F1,F2a,F2b"
TS = time.strftime("%Y-%m-%dT%H:%M:%S%z")
TAG = "w083-ref01rev29-" + time.strftime("%Y%m%dT%H%M%S")


def h(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


FILES = {
    "instrument": "artifacts/worker-083/ref01_rev29_disposition/check_ref01_rev29_disposition.py",
    "report": "artifacts/worker-083/ref01_rev29_disposition/report.json",
    "evidence": "artifacts/worker-083/ref01_rev29_disposition/evidence.json",
    "REPORT": "artifacts/worker-083/ref01_rev29_disposition/REPORT.md",
    "pins": "artifacts/worker-083/ref01_rev29_disposition/pins.json",
    "MANIFEST": "artifacts/worker-083/ref01_rev29_disposition/MANIFEST.json",
    "checkpoint": "artifacts/worker-083/ref01_rev29_disposition/checkpoint.json",
}
H = {k: h(v) for k, v in FILES.items()}
REF = {k: f"{v}#{H[k][:12]}" for k, v in FILES.items()}

report = json.load(open(OUT / "report.json"))
checks_pass = sum(1 for c in report["checks"] if c["pass"])
controls_pass = sum(1 for c in report["controls"] if c["pass"])
digest = report["canonical_digest_sha256"]
n_citing = len({p for paths in
                report["observations"]["intermediate_citations_excluding_report_and_self"].values()
                for p in paths})

statement = (
    "Artifact-and-checker result (not a mathematics or physics claim) at FROZEN rev29 "
    "815e08079aef (all 12 bound inputs hash-stable across the run, "
    "drift=[]): the W083-REF-01 defect is still live and unrepaired after the rev29 "
    "evidence-binding repair. The pinned rev27 closure record "
    "artifacts/formulation/evidence/close_findings_rev27_report.json#dab1d49b9985 (bytes == its "
    "FROZEN rev29 pin, strict-parse clean, 1407 bytes) declares 8 post-write sha256 values of "
    "which exactly 1 is CURRENT (research_map/formulation_taxonomy.yaml 0abb9ed8a961) and 7 are "
    "STALE_DECLARED: taxonomy_consistency f3c119a8 vs live 9e335e9ba1bf, and both mirror copies "
    "of the three schemas b474fbc4/a7ccae4d/b71ec02c vs live d9cebb9404b2/e9a27996dfd3/"
    "b2ab6acb2bbe. The freeze itself is intact: all 8 declared paths' live bytes equal their "
    "FROZEN rev29 pins, so this is a defect in the report's declared-hash block, not a freeze "
    "breach. A content-hash scan of 31,028 files / 763,212,311 bytes recovers 0 copies of the "
    "four intermediate generations, and runtime/state/artifact_hashes.json registers none of "
    "them; the four values survive only as citations in " + str(n_citing) + " review/checkpoint "
    "files, none of which is named in a live map gate evidence_refs. The pinned procedure "
    "artifacts/formulation/tools/close_findings_rev27.py#0234cd3cbda4 exits 1 with 'ASSERT FAIL "
    "[F0 scalar-sph conclusion]' under --dry-run at the frozen bytes while writing nothing (12/12 "
    "guarded paths unchanged), so the closure record is not reproducible from its own pinned "
    "(report, tool, bytes) triple. The live G-FORM gate record names the stale report by path "
    "(unhashed, plus reviews/closefind-verify-094.json#0abb9ed8a961, which binds the F0 taxonomy) "
    "while the operative byte binding is "
    "artifacts/formulation/evidence/gate_test_report.json#26540a6b43cc, which declares all three "
    "rev13 schema hashes and was not named in the live gate refs at the measured map snapshot "
    "a2585ffc2152. " + str(checks_pass) + "/8 hard checks, " + str(controls_pass) + "/7 controls, "
    "canonical digest " + digest + ". Measure-only "
    "remedies R1 (owner rev30 closure receipt) and R2 (controller finding + pin "
    "gate_test_report#26540a6b into G-FORM refs) are recorded and deliberately not applied. No "
    "gate verdict, node status, validation_status, canonical edit or repair is claimed."
)

claim = {
    "event_id": TAG + "-claim-001",
    "event_type": "claim",
    "created_at": TS,
    "actor": "worker-083",
    "task_id": TASK,
    "node_id": NODE,
    "gate": "G-FORM",
    "class_id": ";".join(CLASS_IDS),
    "class_ids": CLASS_IDS,
    "conclusion_type": "stability_result",
    "claims_theorem_status": False,
    "statement": statement,
    "assumptions": [
        "FROZEN rev29 815e08079aef is the current canonical manifest; measured together with its pinned bytes at run time",
        "sha256 binding is the evidence relation the protocol requires (PROTOCOL.md rules 2 and 4)",
        "the recoverability scan set is the repo root minus .git/tmp/node_modules/__pycache__/.cache/.dsh and files >4MB; a copy outside that set is not excluded",
        "citations of the four intermediate hashes are historical review/checkpoint records, valid as provenance of rev12 work but not as evidence of rev13/rev29 bytes",
        "a worker may measure and report but may not edit frozen artifacts, set a gate verdict, node status or validation_status",
    ],
    "falsifier": report["falsifier"],
    "evidence_refs": [
        REF["report"], REF["evidence"], REF["instrument"], REF["pins"],
        "artifacts/formulation/FROZEN.json#815e08079aefbc",
        "artifacts/formulation/evidence/close_findings_rev27_report.json#dab1d49b9985",
        "artifacts/formulation/tools/close_findings_rev27.py#0234cd3cbda4",
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "artifacts/formulation/evidence/gate_test_report.json#26540a6b43cc",
        "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    ],
    "artifact_refs": [REF["report"], REF["evidence"], REF["instrument"], REF["REPORT"],
                      REF["pins"], REF["MANIFEST"]],
    "does_not_claim": [
        "no gate verdict (G-FORM stays pending; worker events cannot move a gate)",
        "no node status (F0/F1/F2a/F2b stay as recorded)",
        "no validation_status=passed",
        "no canonical artifact edited or repair applied",
        "no mathematics, physics or schema-content claim",
        "the map/consumer reads are timestamped moving-target observations, not part of the canonical digest",
    ],
}

events = [{
    "event_id": TAG + "-start",
    "event_type": "status",
    "created_at": TS,
    "actor": "worker-083",
    "task_id": TASK,
    "node_id": NODE,
    "gate": "G-FORM",
    "class_id": ";".join(CLASS_IDS),
    "class_ids": CLASS_IDS,
    "status": "active",
    "hours": 0.4,
    "summary": ("No inbox card for worker-083; took ONE bounded class-bound task: disposition of the "
                "W083-REF-01 evidence defect (stale declared hashes in the pinned rev27 closure record) "
                "at FROZEN rev29, after the rev29 evidence-binding repair. Read-only instrument with 8 "
                "hard checks + 7 controls; result PASS_REF01_DISPOSITION, canonical digest "
                + digest[:14] + "."),
    "evidence_refs": [REF["report"], REF["evidence"], REF["instrument"]],
    "next_falsifier": report["falsifier"],
}]

artifact_types = {
    "instrument": "verification_tool",
    "report": "verification_report",
    "evidence": "measurement_evidence",
    "REPORT": "report",
    "pins": "pin_manifest",
    "MANIFEST": "artifact_manifest",
    "checkpoint": "checkpoint",
}
for key in ["instrument", "report", "evidence", "REPORT", "pins", "MANIFEST", "checkpoint"]:
    events.append({
        "event_id": TAG + "-artifact-" + key,
        "event_type": "artifact",
        "created_at": TS,
        "actor": "worker-083",
        "task_id": TASK,
        "node_id": NODE,
        "gate": "G-FORM",
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "artifact_type": artifact_types[key],
        "path": FILES[key],
        "sha256": H[key],
        "bytes": (ROOT / FILES[key]).stat().st_size,
        "validation_status": "unverified",
        "note": "W083-REF01-REV29-DISPOSITION-01 deliverable (worker measurement; not gate evidence)",
    })

events.append(claim)

events.append({
    "event_id": TAG + "-complete",
    "event_type": "status",
    "created_at": TS,
    "actor": "worker-083",
    "task_id": TASK,
    "node_id": NODE,
    "gate": "G-FORM",
    "class_id": ";".join(CLASS_IDS),
    "class_ids": CLASS_IDS,
    "status": "active",
    "hours": 0.4,
    "summary": (f"W083-REF01-REV29-DISPOSITION-01 complete at worker level: {checks_pass}/8 checks, "
                f"{controls_pass}/7 controls, 0 pin drift, canonical digest {digest[:14]}. W083-REF-01 "
                "is still live at FROZEN rev29 (7/8 declared hashes stale, 0 archived copies of the four "
                "intermediates in 31,028 files, pinned tool fails closed) while the freeze itself is "
                "intact; the operative byte binding is gate_test_report.json#26540a6b. Next consumer: "
                "astra controller / astra-lead-formulation / G-FORM r3 reviewers - do not treat the rev27 "
                "closure table as byte evidence for rev13; remedy options R1/R2 recorded, not applied. "
                "No gate verdict, node status, validation_status or canonical write."),
    "evidence_refs": [REF["report"], REF["evidence"], REF["instrument"], REF["REPORT"],
                      REF["pins"], REF["MANIFEST"], REF["checkpoint"]],
    "next_falsifier": report["falsifier"],
})

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            continue

added = 0
with OUTBOX.open("a") as fh:
    for e in events:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        added += 1

(OUT / "events.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events))
print(json.dumps({"emitted": added, "total": len(events), "outbox": str(OUTBOX),
                  "digest": digest[:14]}, indent=1))
