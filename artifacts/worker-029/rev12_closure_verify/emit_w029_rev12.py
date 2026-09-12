#!/usr/bin/env python3
"""
W029-REV12-CLOSURE-03 emitter — builds the upward events for the rev12 closure verdict,
validates every event against research_map/schemas.py BEFORE writing anything, writes the
worker checkpoint, and appends to comms/outbox/worker-029.jsonl idempotently.

Order of operations (fail-closed):
  1. re-measure every artifact sha256 from disk;
  2. build events with those measured hashes;
  3. validate all events with the real validator;
  4. write runtime/state/w029_rev12_checkpoint.json;
  5. append only event_ids not already present in the outbox.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
HERE = Path(__file__).resolve().parent
REL = "artifacts/worker-029/rev12_closure_verify"

TASK = "W029-REV12-CLOSURE-03"
NODE = "F1,F2a,F2b"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


report = json.loads((HERE / "report.json").read_text())
evidence = json.loads((HERE / "evidence.json").read_text())
manifest = json.loads((HERE / "snapshot_manifest.json").read_text())

FILES = {
    "checker": (f"{REL}/check_rev12_closure.py", "checker_code"),
    "report": (f"{REL}/report.json", "audit_report"),
    "evidence": (f"{REL}/evidence.json", "evidence"),
    "readme": (f"{REL}/REVIEW.md", "summary"),
    "manifest": (f"{REL}/snapshot_manifest.json", "snapshot_manifest"),
}
measured = {k: sha256(HERE / Path(rel).name) for k, (rel, _) in FILES.items()}

hashes = report["measured_hashes"]
F1H, F2AH, F2BH = hashes["af_wcc_vacuum.yaml"], hashes["af_scc_c2_vacuum.yaml"], hashes["af_scc_c0_vacuum.yaml"]
TAXH = hashes["formulation_taxonomy.canonical.yaml"]
LEDGERH = evidence["ledger_snapshot_sha256"]
c2 = [c for c in report["checks"] if c["check_id"].startswith("C2")][0]
bad_rows = [e for e in c2["evidence"] if e.get("claim_matches_ledger") is False]

FALSIFIER = (
    "Re-run check_rev12_closure.py on the same snapshot bytes: the closure claim is falsified if any "
    "check reported PASS here reports FAIL, or if a cited ledger row's verification_status equals the "
    "schema's claimed citation_status. If the live paths no longer match the snapshot hashes, the "
    "verdict is superseded (not falsified) and must be re-issued against the new revision."
)

HARD_FAILURE = {
    "id": "HF-29-02",
    "check_id": "C2",
    "severity": "hard",
    "finding": (
        "rev12 did not close HF-29-02: 11 of 14 l1_ledger_refs rows assert citation_status="
        "'verified_by_L1' while the frozen ledger/theorems.jsonl @%s records verification_status="
        "'abstract-read' and review_status='not_independently_reviewed' for every row (61 abstract-read "
        "+ 1 unverified, 0 independently reviewed). The token appears nowhere in the ledger. "
        "ledger/citation_audit.csv @315c19145065 verifies citation METADATA (resolver/primary-page "
        "fetch), not independent reading of the theorem statement, so it cannot license the claim. "
        "Affected rows: F1 T-204/T-208; F2a T-401/T-402/T-514/T-520; F2b D-002/T-301/T-302/T-515/T-528." % LEDGERH[:12]
    ),
    "evidence": [
        f"{REL}/evidence.json#{measured['evidence'][:12]}",
        f"ledger/theorems.jsonl#{LEDGERH[:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{F2BH[:12]}",
    ],
    "falsifier": (
        "Show a ledger/theorems.jsonl row whose verification_status/review_status records independent "
        "L1 verification for one of the 11 cited ids and re-pin the ledger hash, or show the 11 "
        "citation_status values revised to the ledger vocabulary."
    ),
}

POSITIVE_FINDINGS = [
    {
        "id": "W029R-01",
        "severity": "pass",
        "finding": "HF-29-01 closed at rev12: class_contract_pointer resolves for all three classes under research_map/formulation_taxonomy.yaml#classes.<ID>, and the authoring supplement is split into class_contract_supplement_pointer.",
        "check_id": "C1",
    },
    {
        "id": "W029R-02",
        "severity": "pass",
        "finding": "HF-29-03 closed at rev12: no future-dated revision timestamp remains; revision_history indices are monotone.",
        "check_id": "C3,C9",
    },
    {
        "id": "W029R-03",
        "severity": "pass",
        "finding": "The rev11 duplicate-YAML-key defect class is closed in all three schemas and the taxonomy (duplicate-preserving loader used).",
        "check_id": "C4",
    },
    {
        "id": "W029R-04",
        "severity": "pass",
        "finding": "G-FORM criterion 'no single frozen data class (s,delta,norm)': met semantically at rev12. D0 is a tagged disjoint union over a bare index r (the ill-typed (s,delta) binder is gone), the normative regularity (smooth default, s>5/2, delta in (1/2,1), weighted Sobolev spaces) is identical across F1/F2a/F2b, and all three D0 definitions resolve to regularity.data_regularity. Remaining differences are non-normative prose (C6b, info).",
        "check_id": "C5,C6",
    },
    {
        "id": "W029R-05",
        "severity": "info",
        "finding": "Non-normative prose drift: F1's data_class.regularity_class.sobolev_variant.spaces carries '(weighted Sobolev)' and its regularity.data_regularity includes 'delta in (1/2,1)'; F2a/F2b omit both while recording delta under regularity_class.sobolev_variant. No mathematical content differs; flagged for the gate owner.",
        "check_id": "C6b",
    },
]

EVENTS = [
    {
        "event_id": "w029r-20260912T0042-status-start",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-029",
        "node_id": NODE,
        "class_id": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "status": "active",
        "hours": 0.25,
        "summary": (
            "One class-bound task: independent closure verification of F1/F2a/F2b rev12 at the measured "
            "hashes, re-checking the three prior hard failures HF-29-01/02/03 and the standing G-FORM "
            "single-data-class criterion from frozen snapshots. Read-only; no canonical artifact edited."
        ),
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#{F1H[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{F2AH[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{F2BH[:12]}",
            f"research_map/formulation_taxonomy.yaml#{TAXH[:12]}",
        ],
        "next_falsifier": FALSIFIER,
    },
    *[
        {
            "event_id": f"w029r-20260912T0042-artifact-{k}",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": "worker-029",
            "node_id": NODE,
            "class_id": CLASSES,
            "gate": GATE,
            "task_id": TASK,
            "artifact_type": atype,
            "path": rel,
            "sha256": measured[k],
            "validation_status": "unverified",
            "note": "Deterministic read-only closure verification over frozen snapshot bytes; worker-level evidence, not a gate verdict.",
        }
        for k, (rel, atype) in FILES.items()
    ],
    {
        "event_id": "w029r-20260912T0042-review-rev12",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-029",
        "reviewer": "worker-029",
        "target_id": "F1,F2a,F2b",
        "class_id": CLASSES,
        "gate": GATE,
        "artifact_path": "schemas/af_wcc_vacuum.yaml;schemas/af_scc_c2_vacuum.yaml;schemas/af_scc_c0_vacuum.yaml",
        "reviewed_sha256": f"{F1H};{F2AH};{F2BH}",
        "verdict": "revise",
        "score": report["score"],
        "hard_failures": [HARD_FAILURE],
        "findings": POSITIVE_FINDINGS,
        "evidence_refs": [
            f"{REL}/report.json#{measured['report'][:12]}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"ledger/theorems.jsonl#{LEDGERH[:12]}",
        ],
        "falsifier": FALSIFIER,
    },
    {
        "event_id": "w029r-20260912T0042-claim-rev12",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-029",
        "node_id": NODE,
        "class_id": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "conclusion_type": "numerical_evidence",
        "artifact_refs": [
            f"{REL}/report.json#{measured['report'][:12]}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"{REL}/check_rev12_closure.py#{measured['checker'][:12]}",
            f"{REL}/REVIEW.md#{measured['readme'][:12]}",
        ],
        "statement": (
            "Deterministic measurement at frozen rev12 hashes F1 %s / F2a %s / F2b %s / taxonomy %s / "
            "ledger %s: 10 of 11 checks PASS and exactly one hard check FAILS. Closed at rev12: "
            "HF-29-01 (class_contract_pointer now resolves under the canonical classes key), HF-29-03 "
            "(no future-dated revision timestamp), the rev11 duplicate-YAML-key defect class (all three "
            "schemas + taxonomy), and the G-FORM criterion 'no single frozen data class (s,delta,norm)' "
            "is met semantically (D0 is a tagged disjoint union over a bare index r; the normative "
            "smooth/H^s_delta regularity with s>5/2, delta in (1/2,1) is identical across the three "
            "schemas). Still open: HF-29-02 - 11 of 14 l1_ledger_refs rows assert citation_status="
            "'verified_by_L1' while every row of the frozen ledger records verification_status="
            "'abstract-read' and review_status='not_independently_reviewed' (61 abstract-read + 1 "
            "unverified, 0 independently reviewed) and the token appears nowhere in the ledger; "
            "citation_audit.csv verifies citation metadata only. Verdict revise at these hashes. This is "
            "worker evidence; no gate verdict, node status, or validation_status is claimed."
        ) % (F1H[:12], F2AH[:12], F2BH[:12], TAXH[:12], LEDGERH[:12]),
        "assumptions": [
            "The verdict binds only to the frozen snapshot bytes under artifacts/worker-029/rev12_closure_verify/snapshots/ plus the frozen ledger snapshot; all five live paths matched at emission.",
            "The canonical-path policy of research_map/ASTRA_HANDOFF.md (2026-09-12) is in force.",
            "citation_status is compared against the ledger's verification_status vocabulary; a conservative downgrade (unresolved/unverified on an abstract-read row) is counted as honest.",
            "Normative equality of the data class compares the smooth default, the s and delta bounds, and the Sobolev spaces; non-normative prose differences are reported separately as C6b.",
            "A worker review is evidence only and cannot set a gate verdict, a node status, or validation_status.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#{F1H}",
            f"schemas/af_scc_c2_vacuum.yaml#{F2AH}",
            f"schemas/af_scc_c0_vacuum.yaml#{F2BH}",
            f"research_map/formulation_taxonomy.yaml#{TAXH}",
            f"ledger/theorems.jsonl#{LEDGERH}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
        ],
    },
    {
        "event_id": "w029r-20260912T0042-blocker-hf2902",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": "worker-029",
        "node_id": NODE,
        "class_id": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "description": HARD_FAILURE["finding"],
        "severity": "high",
        "needed_to_unblock": (
            "Formulation-side, one of: (i) set citation_status on the 11 rows (F1 T-204/T-208; F2a "
            "T-401/T-402/T-514/T-520; F2b D-002/T-301/T-302/T-515/T-528) to the ledger vocabulary "
            "(abstract-read), removing the contradiction with the same artifacts' citation_status: "
            "unverified; or (ii) record genuine independent L1 verification in ledger/theorems.jsonl "
            "(verification_status/review_status) and re-pin the ledger hash. No schema text change is "
            "needed for the data-class criterion: C6 is met semantically at rev12."
        ),
        "evidence_refs": [
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"ledger/theorems.jsonl#{LEDGERH[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{F2BH[:12]}",
            f"schemas/af_wcc_vacuum.yaml#{F1H[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{F2AH[:12]}",
        ],
        "stop_rule": (
            "No further closure measurement from this worker on these hashes; the fix is owned by "
            "astra-lead-formulation / lead-literature. Any revision that changes the three schema "
            "hashes or the ledger hash voids this measurement and needs a fresh snapshot."
        ),
    },
    {
        "event_id": "w029r-20260912T0042-status-complete",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-029",
        "node_id": NODE,
        "class_id": CLASSES,
        "gate": GATE,
        "task_id": TASK,
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W029-REV12-CLOSURE-03 complete at worker level: checker, snapshot manifest, evidence, "
            "report and review note exist on disk and are hash-pinned; deterministic rerun is "
            "byte-identical. Verdict revise at F1 %s / F2a %s / F2b %s; live paths still match at "
            "emission. This is a completion claim, not a node transition (workers cannot set "
            "done/passed/gate verdicts). Checkpoint: runtime/state/w029_rev12_checkpoint.json."
        ) % (F1H[:12], F2AH[:12], F2BH[:12]),
        "evidence_refs": [
            f"{REL}/report.json#{measured['report'][:12]}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"{REL}/REVIEW.md#{measured['readme'][:12]}",
        ],
        "next_falsifier": FALSIFIER,
    },
]

# ---- step 3: validate everything before writing anything -----------------------
errors = []
for ev in EVENTS:
    try:
        validate_event(dict(ev))
    except SchemaError as ex:
        errors.append(f"{ev['event_id']}: {ex}")
if errors:
    print("VALIDATION FAILED — nothing written:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
print(f"validated {len(EVENTS)} events OK")

# ---- step 4: checkpoint -------------------------------------------------------
checkpoint = {
    "worker": "worker-029",
    "task_id": TASK,
    "created_at": NOW,
    "node_id": NODE,
    "class_ids": CLASSES.split(";"),
    "gate": GATE,
    "verdict": report["verdict"],
    "score": report["score"],
    "summary": report["summary"],
    "measured_hashes": report["measured_hashes"],
    "ledger_snapshot_sha256": LEDGERH,
    "live_matches_snapshot": report["live_matches_snapshot"],
    "artifacts": {k: {"path": rel, "sha256": measured[k]} for k, (rel, _) in FILES.items()},
    "outbox": "comms/outbox/worker-029.jsonl",
    "event_ids": [e["event_id"] for e in EVENTS],
    "blocker": "HF-29-02 survives rev12 (citation_status verified_by_L1 vs ledger abstract-read)",
    "falsifier": FALSIFIER,
    "authority_note": "worker evidence only; cannot set a gate verdict, node status, or validation_status",
}
ckpt = ROOT / "runtime/state/w029_rev12_checkpoint.json"
ckpt.write_text(json.dumps(checkpoint, indent=2) + "\n")
print("checkpoint:", ckpt.relative_to(ROOT), sha256(ckpt)[:12])

# ---- step 5: idempotent append ------------------------------------------------
outbox = ROOT / "comms/outbox/worker-029.jsonl"
existing = set()
if outbox.exists():
    for line in outbox.read_text().splitlines():
        if line.strip():
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass
new = [e for e in EVENTS if e["event_id"] not in existing]
with outbox.open("a") as f:
    for e in new:
        f.write(json.dumps(e) + "\n")
print(f"outbox appended {len(new)} new events ({len(EVENTS) - len(new)} already present)")
print("artifact hashes:")
for k in FILES:
    print(f"  {k:9s} {measured[k]}")
