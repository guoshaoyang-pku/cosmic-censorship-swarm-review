#!/usr/bin/env python3
"""Emit the W083-F2B-REV13-LIVE-DEFECT-LEDGER-01 events to comms/outbox/worker-083.jsonl
and write the worker checkpoint to runtime/state/.

Idempotent: an event_id already present in the outbox is skipped.  Every event is
validated with research_map/schemas.py before it is appended.  Worker authority: no
gate verdict, no node status promotion, no validation_status=passed, no canonical write.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

TZ = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent
TASK_ID = "W083-F2B-REV13-LIVE-DEFECT-LEDGER-01"
CLASSES = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"]
TS = datetime.now(TZ).isoformat()
OUTBOX = ROOT / "comms/outbox/worker-083.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(rel: str, n: int = 12) -> str:
    return f"{rel}#{sha(ROOT / rel)[:n]}"


report = json.loads((OUT / "report.json").read_text())
manifest = json.loads((OUT / "MANIFEST.json").read_text())
base = "artifacts/worker-083/f2b_live_defect_ledger"
cand = report["candidate"]
cand_hash = cand["sha256"]

primary = [
    (f"{base}/check_f2b_live_defect_ledger.py", "instrument"),
    (f"{base}/report.json", "report"),
    (f"{base}/evidence.json", "evidence"),
    (f"{base}/sweep.json", "evidence"),
    (f"{base}/controls.json", "evidence"),
    (f"{base}/candidate/af_scc_c0_vacuum.yaml", "candidate_repair"),
    (f"{base}/candidate.diff", "candidate_repair"),
    (f"{base}/candidate_meta.json", "candidate_repair"),
    (f"{base}/REPORT.md", "report"),
    (f"{base}/MANIFEST.json", "manifest"),
    (f"{base}/checkpoint.json", "checkpoint"),
]

evidence_refs = [
    ref("schemas/af_scc_c0_vacuum.yaml"),
    ref("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    ref("schemas/af_scc_c2_vacuum.yaml"),
    ref("schemas/af_wcc_vacuum.yaml"),
    ref("research_map/formulation_taxonomy.yaml"),
    ref("artifacts/formulation/VOCAB_ALIASES.json"),
    ref("artifacts/formulation/FROZEN.json"),
    ref("artifacts/formulation/evidence/taxonomy_consistency.json"),
    ref("artifacts/formulation/evidence/semantic_escape_rebased.json"),
    ref("artifacts/formulation/tools/check_class_schema.py"),
]
artifact_refs = [f"{p}#{sha(ROOT / p)[:12]}" for p, _ in primary if (ROOT / p).exists()]
artifact_refs.append(f"{base}/MANIFEST.json#{sha(OUT / 'MANIFEST.json')[:12]}")

events = [
    {
        "event_id": "w083f2bledger01-start", "event_type": "status", "created_at": TS,
        "actor": "worker-083", "task_id": TASK_ID, "node_id": "F2b", "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASSES, "status": "active", "hours": 0.2,
        "summary": "Taking one bounded class-bound task with no inbox card: consolidated live-defect "
                   "ledger at F2b rev13 b2ab6acb (FROZEN rev29 815e0807) + sandbox repair preflight.",
        "evidence_refs": evidence_refs, "next_falsifier": "any pinned input moving during the run",
    },
    {
        "event_id": "w083f2bledger01-claim-001", "event_type": "claim", "created_at": TS,
        "actor": "worker-083", "task_id": TASK_ID, "node_id": "F2b", "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASSES,
        "statement": (
            "At live F2b rev13 b2ab6acb (FROZEN rev29 815e0807) three defect classes reproduce from "
            "primary bytes: D1 line 246 'C2 is a strictly larger extension class' inverts the file's own "
            "chain E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; D2 line 152 carries a live "
            "'No containment with C2 or C0 is asserted here' denial against :239/:242-243/:272 and the "
            "corrected C2 sibling; D3 conclusion.conclusion_type scc_c0_future_inextendibility (F2b) and "
            "scc_c2_future_inextendibility (F2a) fall outside F0's declared "
            "field_vocabulary.conclusion_type.allowed while VOCAB_ALIASES.json names the scc_* tokens "
            "canonical and F0 class axes use strong_cosmic_censorship_C0/C2 - the identical F2a conflict "
            "was not in worker-075's F2b-scoped finding and F2a carries 3 live accepts. A two-line "
            "sandbox-only repair closes D1/D2 (candidate sha256 %s); D3 is a gate-owner adjudication and "
            "is deliberately not applied. 43/43 checks, 7/7 pre-registered controls, no pin drift."
            % cand_hash[:12]),
        "conclusion_type": "stability_result",
        "assumptions": [
            "the FROZEN rev29 pin set and the live canonical/mirror bytes are the object of measurement",
            "the file's own implication_ledger.extension_class_containment is the authority for the containment direction",
            "F0 field_vocabulary.conclusion_type.allowed and VOCAB_ALIASES.json are both frozen artifacts whose disagreement is unresolved",
            "the worker may measure and propose but not adjudicate the token conflict or write any canonical path",
        ],
        "falsifier": (
            "Re-run artifacts/worker-083/f2b_live_defect_ledger/check_f2b_live_defect_ledger.py at the cited "
            "pins. Falsified if any check FAILs; either carrier is absent or explicitly scoped/retracted at the "
            "live bytes; an extension-set reading exists in which E_C2 strictly contains E_C0; F2a's "
            "conclusion_type is inside the F0 allowed vocabulary; a third carrier of either defect class exists; "
            "any control departs from its tabled value; or any pinned input moved during the run."),
        "next_falsifier": (
            "The owner's rev14: if line 246 becomes 'strictly smaller' and line 152 is replaced by the nested "
            "correction, D1/D2 should close at the new hash; any surviving carrier, any unscoped denial, or a "
            "token adjudication that leaves the other SCC schema conflicting keeps the ledger open."),
        "evidence_refs": evidence_refs, "artifact_refs": artifact_refs,
        "defects": [b["id"] for b in report["blocking"]],
        "non_blocking": [n["id"] for n in report["non_blocking"]],
        "checks": report["checks"], "candidate_sha256": cand_hash,
        "authority": report["authority"], "non_claims": report["non_claims"],
    },
]

for rel, atype in primary:
    p = ROOT / rel if (ROOT / rel).exists() else OUT / Path(rel).name
    if not p.exists():
        continue
    h = sha(p)
    events.append({
        "event_id": f"w083f2bledger01-artifact-{Path(rel).name}".replace(".", "-"),
        "event_type": "artifact", "created_at": TS, "actor": "worker-083",
        "task_id": TASK_ID, "node_id": "F2b", "gate": "G-FORM",
        "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASSES,
        "artifact_type": atype, "path": rel, "sha256": h, "validation_status": "unverified",
        "note": "W083-F2B-REV13-LIVE-DEFECT-LEDGER-01 deliverable (worker measurement; not gate evidence)",
    })

events.append({
    "event_id": "w083f2bledger01-blocker", "event_type": "blocker", "created_at": TS,
    "actor": "worker-083", "task_id": TASK_ID, "node_id": "F2b", "gate": "G-FORM",
    "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASSES,
    "description": (
        "G-FORM F2b is withheld on 3 reproduced defects at live b2ab6acb, and one of them is not "
        "F2b-local: D1/D2 are owner-repairable text carriers, but D3 (conclusion_type vocabulary) "
        "conflicts identically on F2a, whose live hash carries 3 accepts and would be non-conformant "
        "under F0's allowed list. Repairing only F2b leaves the F2a/F0 disagreement live."),
    "needed_to_unblock": (
        "(1) formulation owner: rev14 with the two text carriers fixed (sandbox candidate "
        "1315427fbc92 is apply-ready as a two-line edit, D3 deliberately excluded) + FROZEN refresh + "
        "evidence/corpus rebind at the new hash (semantic_escape_rebased.base_sha256 is stale: "
        "1bb78ce9 vs live b2ab6acb); (2) gate owner: one token adjudication covering BOTH SCC schemas "
        "(F0 allowed strong_cosmic_censorship_C0/C2 vs VOCAB_ALIASES canonical scc_*_future_inextendibility); "
        "(3) audit lead: fresh independent accepts at the post-repair hash."),
    "evidence_refs": evidence_refs + [f"{base}/report.json#{sha(OUT / 'report.json')[:12]}"],
})

events.append({
    "event_id": "w083f2bledger01-complete", "event_type": "status", "created_at": TS,
    "actor": "worker-083", "task_id": TASK_ID, "node_id": "F2b", "gate": "G-FORM",
    "class_id": "AF-SCC-C0-VAC-GEN", "class_ids": CLASSES, "status": "active", "hours": 0.4,
    "summary": (
        "W083-F2B-REV13-LIVE-DEFECT-LEDGER-01 complete at worker level: 43/43 checks, 7/7 controls, "
        "0 pin drift, 20-file manifest; sandbox candidate %s (not applied). No gate verdict, no node "
        "status, no validation_status, no canonical write." % cand_hash[:12]),
    "evidence_refs": artifact_refs,
    "next_falsifier": "re-run the instrument at the cited pins; any FAIL or any moved pin voids the ledger",
})

# validate every event before touching the outbox
for e in events:
    validate_event(e)

existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                pass

appended = 0
with OUTBOX.open("a", encoding="utf-8") as fh:
    for e in events:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
        appended += 1

# worker checkpoint (controller state is not written by a worker)
cp = json.loads((OUT / "checkpoint.json").read_text())
cp.update({
    "task_id": TASK_ID, "actor": "worker-083", "created_at": TS,
    "artifact_hashes": {k: v["sha256"] for k, v in manifest["files"].items()},
    "events_appended": appended, "outbox": str(OUTBOX.relative_to(ROOT)),
})
state = ROOT / "runtime/state"
(state / "w083_checkpoint_6.json").write_text(json.dumps(cp, indent=1, ensure_ascii=False), encoding="utf-8")
with (state / "w083_checkpoints.jsonl").open("a", encoding="utf-8") as fh:
    fh.write(json.dumps({"checkpoint_id": "w083-ckpt-6", "task_id": TASK_ID, "at": TS,
                         "path": "runtime/state/w083_checkpoint_6.json",
                         "sha256": sha(state / "w083_checkpoint_6.json"),
                         "canonical_writes": False, "no_completion_claim": True},
                        ensure_ascii=False) + "\n")

print(json.dumps({"events_total": len(events), "appended": appended,
                  "outbox_lines": len(OUTBOX.read_text().splitlines()),
                  "checkpoint": "runtime/state/w083_checkpoint_6.json",
                  "checkpoint_sha256": sha(state / "w083_checkpoint_6.json")[:16]}, indent=1))
