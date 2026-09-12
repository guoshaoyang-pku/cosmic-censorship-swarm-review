#!/usr/bin/env python3
"""
Final corrected event set for W029-REV12-CLOSURE-03.

Supersedes the first emission after a checker bug fix: the checker resolved the manifest's relative
`source_path` against the caller's cwd, so the first evidence.json recorded live_sha256=null and a
false "LIVE DRIFT DETECTED".  Fixed (ROOT = repo root), re-run, live paths verified matching.
Findings, verdict, and score are unchanged (10/11 PASS, HF-29-02 hard FAIL, revise 2.0).
Idempotent on event_id; validates every event before writing.
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


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


report = json.loads((HERE / "report.json").read_text())
evidence = json.loads((HERE / "evidence.json").read_text())
FILES = {
    "checker": (f"{REL}/check_rev12_closure.py", "checker_code"),
    "report": (f"{REL}/report.json", "audit_report"),
    "evidence": (f"{REL}/evidence.json", "evidence"),
    "core": (f"{REL}/report_core.json", "deterministic_core"),
    "readme": (f"{REL}/REVIEW.md", "summary"),
    "manifest": (f"{REL}/snapshot_manifest.json", "snapshot_manifest"),
}
measured = {k: sha(HERE / Path(rel).name) for k, (rel, _) in FILES.items()}
hashes = report["measured_hashes"]
F1H, F2AH, F2BH = hashes["af_wcc_vacuum.yaml"], hashes["af_scc_c2_vacuum.yaml"], hashes["af_scc_c0_vacuum.yaml"]
TAXH = hashes["formulation_taxonomy.canonical.yaml"]
LEDGERH = evidence["ledger_snapshot_sha256"]
live_ok = report["live_matches_snapshot"]

FALSIFIER = report["falsifier"]
SUPERSEDES = [
    "w029r-20260912T0042-status-start",
    "w029r-20260912T0042-artifact-checker",
    "w029r-20260912T0042-artifact-report",
    "w029r-20260912T0042-artifact-evidence",
    "w029r-20260912T0042-artifact-readme",
    "w029r-20260912T0042-artifact-manifest",
    "w029r-20260912T0042-review-rev12",
    "w029r-20260912T0042-claim-rev12",
    "w029r-20260912T0042-blocker-hf2902",
    "w029r-20260912T0042-status-complete",
    "w029r-20260912T0042-artifact-review-corrected",
    "w029r2-20260912T0045-status-corrected",
    "w029r2-20260912T0045-artifact-checker",
    "w029r2-20260912T0045-artifact-report",
    "w029r2-20260912T0045-artifact-evidence",
    "w029r2-20260912T0045-artifact-readme",
    "w029r2-20260912T0045-artifact-manifest",
    "w029r2-20260912T0045-review-rev12",
    "w029r2-20260912T0045-claim-rev12",
    "w029r2-20260912T0045-blocker-hf2902",
    "w029r2-20260912T0045-status-complete",
]
FIX_NOTE = (
    "corrected after two checker fixes: (a) manifest source_path is repo-root-relative, so the first "
    "run measured live paths against the caller's cwd and wrongly reported LIVE DRIFT DETECTED "
    "(re-measured: all four live paths match the frozen snapshots); (b) report.json / evidence.json "
    "carry created_at and are emission records, not byte-stable measurements, so a timestamp-free "
    "report_core.json was added - it is byte-identical across reruns (verified 3x). Verdict, score, "
    "and check results unchanged."
)

c2 = [c for c in report["checks"] if c["check_id"].startswith("C2")][0]
bad = [e for e in c2["evidence"] if e.get("claim_matches_ledger") is False]
HARD_FAILURE = {
    "id": "HF-29-02",
    "check_id": "C2",
    "severity": "hard",
    "finding": (
        "rev12 did not close HF-29-02: %d of %d l1_ledger_refs rows assert citation_status="
        "'verified_by_L1' while the frozen ledger/theorems.jsonl @%s records verification_status="
        "'abstract-read' and review_status='not_independently_reviewed' for every row (61 abstract-read "
        "+ 1 unverified, 0 independently reviewed). The token appears nowhere in the ledger. "
        "ledger/citation_audit.csv @315c19145065 verifies citation METADATA (resolver/primary-page "
        "fetch), not independent reading of the theorem statement, so it cannot license the claim. "
        "Affected: F1 T-204/T-208; F2a T-401/T-402/T-514/T-520; F2b D-002/T-301/T-302/T-515/T-528."
        % (len(bad), len([e for e in c2["evidence"] if "theorem_id" in e]), LEDGERH[:12])
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

FINDINGS = [
    {"id": "W029R-01", "check_id": "C1", "severity": "pass",
     "finding": "HF-29-01 closed at rev12: class_contract_pointer resolves for all three classes under research_map/formulation_taxonomy.yaml#classes.<ID>; the authoring supplement is split into class_contract_supplement_pointer."},
    {"id": "W029R-02", "check_id": "C3,C9", "severity": "pass",
     "finding": "HF-29-03 closed at rev12: no future-dated revision timestamp remains; revision_history indices are monotone."},
    {"id": "W029R-03", "check_id": "C4", "severity": "pass",
     "finding": "The rev11 duplicate-YAML-key defect class is closed in all three schemas and the taxonomy (duplicate-preserving loader used)."},
    {"id": "W029R-04", "check_id": "C5,C6", "severity": "pass",
     "finding": "G-FORM criterion 'no single frozen data class (s,delta,norm)': met semantically at rev12. D0 is a tagged disjoint union over a bare index r; the normative regularity (smooth default, s>5/2, delta in (1/2,1), weighted Sobolev spaces) is identical across F1/F2a/F2b and all three D0 definitions resolve to regularity.data_regularity."},
    {"id": "W029R-05", "check_id": "C6b", "severity": "info",
     "finding": "Non-normative prose drift only: F1's sobolev_variant.spaces carries '(weighted Sobolev)' and its regularity.data_regularity includes the delta range; F2a/F2b omit both there while recording delta under regularity_class.sobolev_variant. No mathematical content differs; for the gate owner."},
]

EVENTS = [
    {
        "event_id": "w029r3-20260912T0050-status-corrected",
        "event_type": "status", "created_at": NOW, "actor": "worker-029",
        "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
        "status": "active", "hours": 0.5,
        "supersedes_event_ids": SUPERSEDES,
        "summary": "Corrected final status for W029-REV12-CLOSURE-03. " + FIX_NOTE + " Live paths verified matching at emission.",
        "evidence_refs": [f"{REL}/report.json#{measured['report'][:12]}", f"{REL}/evidence.json#{measured['evidence'][:12]}"],
        "next_falsifier": FALSIFIER,
    },
    *[
        {
            "event_id": f"w029r3-20260912T0050-artifact-{k}",
            "event_type": "artifact", "created_at": NOW, "actor": "worker-029",
            "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
            "artifact_type": atype, "path": rel, "sha256": measured[k],
            "validation_status": "unverified",
            "supersedes_event_ids": SUPERSEDES,
            "note": "Corrected final hash after the checker path fix; deterministic read-only closure verification. " + FIX_NOTE,
        }
        for k, (rel, atype) in FILES.items()
    ],
    {
        "event_id": "w029r3-20260912T0050-review-rev12",
        "event_type": "review", "created_at": NOW, "actor": "worker-029",
        "reviewer": "worker-029", "target_id": NODE, "class_id": CLASSES, "gate": GATE,
        "artifact_path": "schemas/af_wcc_vacuum.yaml;schemas/af_scc_c2_vacuum.yaml;schemas/af_scc_c0_vacuum.yaml",
        "reviewed_sha256": f"{F1H};{F2AH};{F2BH}",
        "verdict": "revise", "score": report["score"],
        "hard_failures": [HARD_FAILURE], "findings": FINDINGS,
        "supersedes_event_ids": SUPERSEDES,
        "evidence_refs": [f"{REL}/report.json#{measured['report'][:12]}", f"{REL}/evidence.json#{measured['evidence'][:12]}", f"ledger/theorems.jsonl#{LEDGERH[:12]}"],
        "falsifier": FALSIFIER,
    },
    {
        "event_id": "w029r3-20260912T0050-claim-rev12",
        "event_type": "claim", "created_at": NOW, "actor": "worker-029",
        "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
        "conclusion_type": "numerical_evidence",
        "supersedes_event_ids": SUPERSEDES,
        "artifact_refs": [
            f"{REL}/report.json#{measured['report'][:12]}",
            f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"{REL}/check_rev12_closure.py#{measured['checker'][:12]}",
            f"{REL}/REVIEW.md#{measured['readme'][:12]}",
        ],
        "statement": (
            "Deterministic measurement at frozen rev12 hashes F1 %s / F2a %s / F2b %s / taxonomy %s / "
            "ledger %s, with all four live paths re-verified matching at emission: 10 of 11 checks PASS, "
            "exactly one hard check FAILS. Closed at rev12: HF-29-01 (class_contract_pointer resolves "
            "under the canonical classes key), HF-29-03 (no future-dated revision timestamp), the rev11 "
            "duplicate-YAML-key defect class (all three schemas + taxonomy), and the G-FORM criterion "
            "'no single frozen data class (s,delta,norm)' is met semantically (D0 is a tagged disjoint "
            "union over a bare index r; the normative smooth/H^s_delta regularity with s>5/2, delta in "
            "(1/2,1) is identical across the three schemas). Still open: HF-29-02 - 11 of 14 "
            "l1_ledger_refs rows assert citation_status='verified_by_L1' while every row of the frozen "
            "ledger records verification_status='abstract-read' and review_status="
            "'not_independently_reviewed' (61 abstract-read + 1 unverified, 0 independently reviewed) and "
            "the token appears nowhere in the ledger; citation_audit.csv verifies citation metadata only. "
            "Verdict revise at these hashes. Worker evidence only; no gate verdict, node status, or "
            "validation_status is claimed."
        ) % (F1H[:12], F2AH[:12], F2BH[:12], TAXH[:12], LEDGERH[:12]),
        "assumptions": [
            "The verdict binds only to the frozen snapshot bytes under artifacts/worker-029/rev12_closure_verify/snapshots/ plus the frozen ledger snapshot; all live paths were re-measured matching at emission.",
            "The canonical-path policy of research_map/ASTRA_HANDOFF.md (2026-09-12) is in force.",
            "citation_status is compared against the ledger's verification_status vocabulary; a conservative downgrade (unresolved/unverified on an abstract-read row) counts as honest.",
            "Normative equality of the data class compares the smooth default, the s and delta bounds, and the Sobolev spaces; non-normative prose differences are reported separately as C6b.",
            "A worker review is evidence only and cannot set a gate verdict, a node status, or validation_status.",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [
            f"schemas/af_wcc_vacuum.yaml#{F1H}", f"schemas/af_scc_c2_vacuum.yaml#{F2AH}",
            f"schemas/af_scc_c0_vacuum.yaml#{F2BH}", f"research_map/formulation_taxonomy.yaml#{TAXH}",
            f"ledger/theorems.jsonl#{LEDGERH}", f"{REL}/evidence.json#{measured['evidence'][:12]}",
        ],
    },
    {
        "event_id": "w029r3-20260912T0050-blocker-hf2902",
        "event_type": "blocker", "created_at": NOW, "actor": "worker-029",
        "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
        "description": HARD_FAILURE["finding"], "severity": "high",
        "supersedes_event_ids": SUPERSEDES,
        "needed_to_unblock": (
            "Formulation-side, one of: (i) set citation_status on the 11 rows (F1 T-204/T-208; F2a "
            "T-401/T-402/T-514/T-520; F2b D-002/T-301/T-302/T-515/T-528) to the ledger vocabulary "
            "(abstract-read), removing the contradiction with the same artifacts' citation_status: "
            "unverified; or (ii) record genuine independent L1 verification in ledger/theorems.jsonl "
            "and re-pin the ledger hash. No schema text change is needed for the data-class criterion: "
            "C6 is met semantically at rev12."
        ),
        "evidence_refs": [
            f"{REL}/evidence.json#{measured['evidence'][:12]}", f"ledger/theorems.jsonl#{LEDGERH[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{F2BH[:12]}", f"schemas/af_wcc_vacuum.yaml#{F1H[:12]}",
            f"schemas/af_scc_c2_vacuum.yaml#{F2AH[:12]}",
        ],
        "stop_rule": (
            "No further closure measurement from this worker on these hashes; the fix is owned by "
            "astra-lead-formulation / lead-literature. Any revision that changes a schema hash or the "
            "ledger hash voids this measurement and needs a fresh snapshot."
        ),
    },
    {
        "event_id": "w029r3-20260912T0050-status-complete",
        "event_type": "status", "created_at": NOW, "actor": "worker-029",
        "node_id": NODE, "class_id": CLASSES, "gate": GATE, "task_id": TASK,
        "status": "active", "hours": 0.7,
        "supersedes_event_ids": SUPERSEDES,
        "summary": (
            "W029-REV12-CLOSURE-03 complete at worker level. Artifacts hash-pinned; deterministic rerun "
            "byte-identical; live paths verified matching (F1 %s / F2a %s / F2b %s). Verdict revise, "
            "10/11 PASS, HF-29-02 open. This is a completion claim, not a node transition. Checkpoint: "
            "runtime/state/w029_rev12_checkpoint.json."
        ) % (F1H[:12], F2AH[:12], F2BH[:12]),
        "evidence_refs": [
            f"{REL}/report.json#{measured['report'][:12]}", f"{REL}/evidence.json#{measured['evidence'][:12]}",
            f"{REL}/REVIEW.md#{measured['readme'][:12]}",
        ],
        "next_falsifier": FALSIFIER,
    },
]

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
print(f"validated {len(EVENTS)} corrected events OK")

ckpt = ROOT / "runtime/state/w029_rev12_checkpoint.json"
checkpoint = json.loads(ckpt.read_text())
checkpoint.update(
    {
        "corrected_at": NOW,
        "corrected_note": FIX_NOTE,
        "summary": report["summary"],
        "verdict": report["verdict"],
        "score": report["score"],
        "live_matches_snapshot": live_ok,
        "measured_hashes": hashes,
        "artifacts": {k: {"path": rel, "sha256": measured[k]} for k, (rel, _) in FILES.items()},
        "event_ids": checkpoint.get("event_ids", []) + [e["event_id"] for e in EVENTS],
        "latest_event_ids": [e["event_id"] for e in EVENTS],
        "outbox": "comms/outbox/worker-029.jsonl",
    }
)
ckpt.write_text(json.dumps(checkpoint, indent=2) + "\n")
print("checkpoint updated:", ckpt.relative_to(ROOT), sha(ckpt)[:12])

outbox = ROOT / "comms/outbox/worker-029.jsonl"
existing = set()
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
print(f"outbox appended {len(new)} corrected events ({len(EVENTS) - len(new)} already present)")
print("final hashes:", json.dumps(measured, indent=1))
