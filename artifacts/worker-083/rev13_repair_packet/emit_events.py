#!/usr/bin/env python3
"""Emit worker-083 outbox events + checkpoint for W083-REV13-REPAIR-PACKET-01.

Idempotent: events whose event_id already exists in the outbox file are skipped.
Writes only comms/outbox/worker-083.jsonl and runtime/state/w083_checkpoint_4.json
(+ the w083_checkpoints.jsonl log). No canonical artifact path is touched.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKT = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-083.jsonl"
CKPT = ROOT / "runtime/state/w083_checkpoint_4.json"
CKPT_LOG = ROOT / "runtime/state/w083_checkpoints.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(rel: str) -> str:
    return f"{rel}#{sha(PKT / rel)[:12]}"


NOW = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
TASK = "W083-REV13-REPAIR-PACKET-01"
SLUG = TASK.lower().replace("-", "")
NODES = ["F1", "F2a", "F2b"]
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
HOURS = 0.8
ev = json.loads((PKT / "evidence.json").read_text())
pk = json.loads((PKT / "packet.json").read_text())
man = json.loads((PKT / "MANIFEST.json").read_text())
f2b_new = pk["measured"]["f2b_new_sha256"]
ck_new = pk["measured"]["checker_new_sha256"]
ev_new = pk["measured"]["evidence_restored_sha256"]
rev29 = man["candidate_rev29_manifest_sha256"]

STATEMENT = (
    "Artifact-and-checker result (not a mathematics or physics claim) at FROZEN rev28 2f358f6722d9 "
    "(44/44 pins measured, all 12 held canonical hashes unchanged at exit): the two open G-FORM "
    "blockers admit one integrated, apply-ready repair packet that validates end-to-end in an "
    "isolated mirror. L-FORM-01: the single inverted premise in "
    "schemas/af_scc_c0_vacuum.yaml#implication_ledger.forbidden_transfers[0] is repaired by "
    "'strictly larger' -> 'strictly smaller' in both mirrored copies; the structural gate passes "
    "before and after; the packet's directional audit flags the frozen line and is clean after; "
    "F2b moves 55d0a1ea9bda -> 3cdcaa44e6f1. L-FORM-02: worker-096 option O3 is applied - "
    "check_taxonomy_consistency.py gains a --write guard (default dry-run) and emits "
    "map_taxonomy_sha256/lead_contract_sha256/measured_at (de356d999ea3 -> 5094870c7f74), and the "
    "existing enriched evidence bytes 675a99d0 are restored at the canonical evidence path, so the "
    "three schema declarations become true without moving any F1/F2a schema byte. The candidate "
    "re-freeze (rev29, 714f4683015a) moves exactly the four intended pinned entries and "
    "verify_frozen.py exits 0 there, while F1 cce9c60146d6, F2a 5476a3f2c6bc, canonical F0 "
    "0abb9ed8a961 and supplement d7419b4e8963 stay byte-identical, so verdicts bound to those "
    "hashes survive and only F2b verdicts bound to 55d0a1ea are voided. 36/36 checks pass, 6/6 "
    "mutant controls are caught. No gate verdict, node status or validation_status is claimed; the "
    "packet is not applied to canonical bytes."
)

events = [
    {
        "event_id": f"{SLUG}-task-claim",
        "event_type": "status", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES,
        "task_id": TASK, "status": "active", "hours": HOURS,
        "summary": ("No inbox card for worker-083. Took ONE bounded class-bound task: integrate the two open "
                    "G-FORM blockers (L-FORM-01 inverted premise in F2b; L-FORM-02 stale consistency-evidence "
                    "binding across F1/F2a/F2b) into a single apply-ready, controller-authorizable rev13 repair "
                    "packet, using worker-058's repair wording and worker-096's O3 evidence option, and validate "
                    "the COMBINED result in an isolated mirror. Verdict PACKET_VALIDATED 36/36; exactly 4 pinned "
                    "entries move; candidate rev29 verify_frozen exit 0; canonical paths untouched."),
        "evidence_refs": [ref("evidence.json"), ref("packet.json"), ref("MANIFEST.json")],
        "next_falsifier": pk["falsifiers"][0],
    },
    {
        "event_id": f"{SLUG}-artifact-builder",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "artifact_type": "verification_tool",
        "path": "artifacts/worker-083/rev13_repair_packet/build_and_validate.py",
        "sha256": sha(PKT / "build_and_validate.py"), "validation_status": "unverified",
        "note": ("Deterministic read-only builder/validator: pinned-mirror construction, both repairs on copies, "
                 "directional premise audit, GNU patch round-trip, candidate rev29 re-freeze, 6 mutant controls, "
                 "verdict census, canonical-confinement proof. Exit 0 iff 36/36 checks pass."),
    },
    {
        "event_id": f"{SLUG}-artifact-evidence",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "artifact_type": "measurement_evidence",
        "path": "artifacts/worker-083/rev13_repair_packet/evidence.json",
        "sha256": sha(PKT / "evidence.json"), "validation_status": "unverified",
        "note": ("36 checks with expected/observed/falsifier; per-repair before/after hashes; candidate rev29 moved "
                 "entries; verdict census (file-citation level); all controls; canonical_writes=false."),
    },
    {
        "event_id": f"{SLUG}-artifact-packet",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "artifact_type": "repair_packet",
        "path": "artifacts/worker-083/rev13_repair_packet/packet.json",
        "sha256": sha(PKT / "packet.json"), "validation_status": "unverified",
        "note": ("Apply-ready packet: 7 ordered commands, three unified diffs, measured old/new hashes "
                 "(F2b 3cdcaa44e6f1; evidence 675a99d0d25b; checker 5094870c7f74), candidate rev29 manifest "
                 "714f4683015a, void/retained verdict census, falsifiers. Not applied."),
    },
    {
        "event_id": f"{SLUG}-artifact-candidate-manifest",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "artifact_type": "candidate_frozen_manifest",
        "path": "artifacts/worker-083/rev13_repair_packet/work_repair/artifacts/formulation/FROZEN.json",
        "sha256": rev29, "validation_status": "unverified",
        "note": ("Candidate FROZEN revision 29 built only in the mirror: 44 files, verify_frozen.py exit 0, "
                 "exactly 4 entries moved (F2b canonical+mirror, evidence, checker). A canonical re-freeze at a "
                 "different --at yields a different manifest hash with the same 44 file pins."),
    },
    {
        "event_id": f"{SLUG}-artifact-report",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "artifact_type": "verification_report",
        "path": "artifacts/worker-083/rev13_repair_packet/REPORT.md",
        "sha256": sha(PKT / "REPORT.md"), "validation_status": "unverified",
        "note": ("Report: blockers, result table, hash-move table, apply steps, O3-vs-O2 rationale, controls, "
                 "falsifiers, limits."),
    },
    {
        "event_id": f"{SLUG}-artifact-manifest",
        "event_type": "artifact", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "artifact_type": "artifact_manifest",
        "path": "artifacts/worker-083/rev13_repair_packet/MANIFEST.json",
        "sha256": sha(PKT / "MANIFEST.json"), "validation_status": "unverified",
        "note": "Measured hashes of the 12 deliverable files, the 4 moved entries, the 4 unchanged held paths, and the enriched-evidence source pin.",
    },
    {
        "event_id": f"{SLUG}-claim-001",
        "event_type": "claim", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "conclusion_type": "stability_result", "claims_theorem_status": False,
        "does_not_claim": [
            "no gate verdict (G-FORM/G-F0 stay pending; worker events cannot move a gate)",
            "no node status (F1/F2a/F2b stay active/unverified)",
            "the packet is NOT applied; controller authorization is required (REC-9 freeze-hold)",
            "no claim that O3 is the controller's chosen option, only that it is validated and preserves F1/F2a bindings",
            "no mathematics, no physics claim, no verdict count (the census is file-citation level)",
        ],
        "statement": STATEMENT,
        "assumptions": [
            "FROZEN rev28 2f358f6722d9 is the current canonical manifest; measured 44/44 at run time",
            "sha256 binding is the evidence relation the protocol requires (PROTOCOL.md rules 2 and 4)",
            "the enriched evidence generation 675a99d0 held by worker-086 is the byte generation the three schemas declare",
            "worker-096 O3 and worker-058 HF-1 are adopted as adjudicated inputs; this artifact integrates and validates them rather than re-deriving them",
            "the directional audit is a packet-internal DIR-1/DIR-2/DIR-3 grammar over ledger reason strings, control-tested but not a substitute for the worker-058/worker-060 containment checkers",
        ],
        "evidence_refs": [ref("evidence.json"), ref("packet.json"), ref("MANIFEST.json"), ref("REPORT.md"),
                          ref("diffs/check_taxonomy_consistency--O3-guard.patch.diff"),
                          "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                          "artifacts/formulation/FROZEN.json#2f358f6722d9"],
        "artifact_refs": [ref("packet.json"), ref("evidence.json"), ref("MANIFEST.json")],
        "next_falsifier": ("Re-run python3 artifacts/worker-083/rev13_repair_packet/build_and_validate.py at the cited "
                           "base pins; falsified if any check fails, if F2b still contains 'strictly larger' or fails the "
                           "directional audit, if a default patched-checker run changes the evidence bytes, if candidate "
                           "rev29 verify_frozen is non-zero, if more or fewer than the four intended entries move, if any "
                           "F1/F2a/F0 byte changes, or if an extension-set reading exists in which E_C2 strictly contains E_C0."),
    },
    {
        "event_id": f"{SLUG}-complete",
        "event_type": "status", "created_at": NOW, "actor": "worker-083",
        "node_id": "F1,F2a,F2b", "gate": "G-FORM", "class_ids": CLASSES, "task_id": TASK,
        "status": "active", "hours": HOURS,
        "summary": ("W083-REV13-REPAIR-PACKET-01 complete as a bounded worker deliverable (completion claim for the "
                    "artifact, not a node transition: workers cannot set done/passed; G-FORM stays pending). 36/36 "
                    "checks pass, 6/6 mutants caught, candidate rev29 verify_frozen exit 0, canonical paths unchanged. "
                    "Next consumer: astra controller / astra-lead-formulation — the packet is ready to authorize or "
                    "reject at the next pass; recommended ordering is repair before the 02:15 F2b re-verification "
                    "because the F2b target hash moves."),
        "evidence_refs": [ref("evidence.json"), ref("packet.json"), ref("MANIFEST.json"), ref("REPORT.md"),
                          "runtime/state/w083_checkpoint_4.json"],
        "next_falsifier": "; ".join(pk["falsifiers"]),
    },
]

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
appended = 0
with OUTBOX.open("a") as fh:
    for e in events:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e) + "\n")
        appended += 1

checkpoint = {
    "checkpoint_id": "w083-ckpt-4",
    "task_id": TASK,
    "worker": "worker-083",
    "created_at": NOW,
    "node_ids": NODES,
    "gate": "G-FORM",
    "class_ids": CLASSES + ["AF-WCC-SCALAR-SPH"],
    "status": "active",
    "hours": HOURS,
    "authority": "worker evidence only; packet not applied; no gate verdict or node transition claimed",
    "summary": ("Integrated apply-ready rev13 repair packet for L-FORM-01 (F2b inverted premise) + L-FORM-02 "
                "(worker-096 O3 evidence guard/restore), validated in an isolated mirror: 36/36 checks, 6/6 mutants "
                "caught, candidate rev29 verify_frozen exit 0, exactly 4 pinned entries move, F1/F2a/F0 unchanged."),
    "result": {
        "verdict": ev["verdict"],
        "checks_total": ev["checks_total"],
        "checks_failed": ev["checks_failed"],
        "f2b_old_sha256": pk["measured"]["f2b_old_sha256"],
        "f2b_new_sha256": f2b_new,
        "evidence_restored_sha256": ev_new,
        "checker_old_sha256": pk["measured"]["checker_old_sha256"],
        "checker_new_sha256": ck_new,
        "candidate_rev29_manifest_sha256": rev29,
        "candidate_rev29_moved_entries": pk["measured"]["candidate_rev29_moved_entries"],
        "canonical_writes": False,
        "applied": False,
    },
    "artifact_hashes": {rel: sha(PKT / rel) for rel in (
        "MANIFEST.json", "REPORT.md", "build_and_validate.py", "evidence.json", "packet.json",
        "diffs/af_scc_c0_vacuum--LFORM01.patch.diff",
        "diffs/af_scc_c0_vacuum.mirror--LFORM01.patch.diff",
        "diffs/check_taxonomy_consistency--O3-guard.patch.diff",
        "work_repair/artifacts/formulation/FROZEN.json")},
    "base_pins": {
        "artifacts/formulation/FROZEN.json": man["base_frozen_sha256"],
        "schemas/af_wcc_vacuum.yaml": man["unchanged_held_paths"]["schemas/af_wcc_vacuum.yaml"],
        "schemas/af_scc_c2_vacuum.yaml": man["unchanged_held_paths"]["schemas/af_scc_c2_vacuum.yaml"],
        "schemas/af_scc_c0_vacuum.yaml": pk["measured"]["f2b_old_sha256"],
        "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    },
    "next_falsifier": events[-1]["next_falsifier"],
}
CKPT.write_text(json.dumps(checkpoint, indent=2) + "\n")
ck_line = {"checkpoint_id": "w083-ckpt-4", "created_at": NOW, "task_id": TASK,
           "verdict": ev["verdict"], "checks": f"{ev['checks_total'] - len(ev['checks_failed'])}/{ev['checks_total']}",
           "f2b_new_sha256": f2b_new, "checkpoint_file": "runtime/state/w083_checkpoint_4.json",
           "sha256": sha(CKPT)}
if not CKPT_LOG.exists() or "w083-ckpt-4" not in CKPT_LOG.read_text():
    with CKPT_LOG.open("a") as fh:
        fh.write(json.dumps(ck_line) + "\n")
print(json.dumps({"events_appended": appended, "outbox": str(OUTBOX.relative_to(ROOT)),
                  "checkpoint_sha256": sha(CKPT)[:12]}, indent=1))
