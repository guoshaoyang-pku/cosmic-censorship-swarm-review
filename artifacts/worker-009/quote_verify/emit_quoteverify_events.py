#!/usr/bin/env python3
"""Emit worker-009 checkpoint + outbox events for W009-L1-QUOTEVERIFY-01."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
QP = os.path.join(ROOT, "artifacts", "worker-009", "quote_verify")
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-009.jsonl")
CKPT = os.path.join(ROOT, "runtime", "state", "w009_quoteverify_checkpoint_1.json")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
STAMP = NOW.replace(":", "").replace("-", "").replace("+0800", "")

CLASSES = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sh(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT)


REC = os.path.join(QP, "verification_quotes_worker-009.json")
CSV = os.path.join(QP, "quote_verify_worker-009.csv")
TOOL = os.path.join(QP, "verify_quotes_worker-009.py")
MAN = os.path.join(QP, "MANIFEST_worker-009.json")

ver = json.load(open(REC))
artifacts = {rel(REC): sh(REC), rel(CSV): sh(CSV), rel(TOOL): sh(TOOL), rel(MAN): sh(MAN)}
anchors = {
    "canonical_ledger": sh(os.path.join(ROOT, "ledger", "citation_audit.csv")),
    "candidate_csv": sh(os.path.join(ROOT, "ledger", "citation_audit_scc_candidates_worker-009.csv")),
    "candidate_jsonl": sh(os.path.join(ROOT, "ledger", "citation_audit_scc_candidates_worker-009.jsonl")),
    "f2a_c2_schema": sh(os.path.join(ROOT, "artifacts", "formulation", "schemas", "af_scc_c2_vacuum.yaml")),
    "f2b_c0_schema": sh(os.path.join(ROOT, "artifacts", "formulation", "schemas", "af_scc_c0_vacuum.yaml")),
}

checkpoint = {
    "checkpoint_id": f"w009-quoteverify-{NOW}",
    "created_at": NOW,
    "worker": "worker-009",
    "label": "worker-009-L1-quote-class-discrimination",
    "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
    "node_id": "L1",
    "gate": "G-LIT",
    "class_ids": CLASSES,
    "record": {"path": rel(REC), "sha256": artifacts[rel(REC)]},
    "artifacts": artifacts,
    "anchors": anchors,
    "counts": {"pass": ver["summary"]["checks_pass"], "fail": ver["summary"]["checks_fail"]},
    "summary": ver["summary"],
    "closure_verdict": "accept-self-verified" if ver["summary"]["checks_fail"] == 0 else "revise",
    "independence_caveat": ver["independence_caveat"],
    "canonical_untouched": True,
    "numerics_lock": "respected (no numerics/ work)",
    "next_falsifier": ver["next_falsifier"],
}
with open(CKPT, "w", encoding="utf-8") as f:
    json.dump(checkpoint, f, indent=1, ensure_ascii=False)
    f.write("\n")

base = f"w009-quoteverify-{STAMP}"
events = [
    {
        "event_id": f"{base}-task-receipt",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASSES,
        "status": "active",
        "hours": 0.2,
        "summary": ("Took ONE bounded class-bound task from standing card asg-2026-09-11-L1-deepseek-flash-09-18: "
                    "W009-L1-QUOTEVERIFY-01, same-worker cross-method re-derivation of the five SCC class-binding "
                    "correction quotes from pinned bytes plus explicit C0/C2 schema-predicate discrimination. "
                    "No canonical file is written."),
        "evidence_refs": [f"{rel(REC)}#{artifacts[rel(REC)][:16]}"],
        "next_falsifier": "see final status event",
    },
    {
        "event_id": f"{base}-artifact-01",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASSES,
        "artifact_type": "verification_record",
        "path": rel(REC),
        "sha256": artifacts[rel(REC)],
        "validation_status": "unverified",
        "summary": (f"67/67 checks PASS, 0 FAIL; 5/5 quotes byte-exact at pinned source hashes; 5/5 correction rows "
                    f"warranted; 0 rows support a C0 or C2 vacuum binding; 0 residual binding defects."),
    },
    {
        "event_id": f"{base}-artifact-02",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASSES,
        "artifact_type": "verification_table",
        "path": rel(CSV),
        "sha256": artifacts[rel(CSV)],
        "validation_status": "unverified",
        "summary": "Per-row C0/C2 discrimination table for CBC-09-008..012.",
    },
    {
        "event_id": f"{base}-artifact-03",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASSES,
        "artifact_type": "verification_tool",
        "path": rel(TOOL),
        "sha256": artifacts[rel(TOOL)],
        "validation_status": "unverified",
        "summary": ("Byte-reproducible verifier: newline-preserving CSV read, quote hash/presence, theorem-env "
                    "enumeration, binding-vs-mention classifier, 6 controls."),
    },
    {
        "event_id": f"{base}-artifact-04",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASSES,
        "artifact_type": "artifact_manifest",
        "path": rel(MAN),
        "sha256": artifacts[rel(MAN)],
        "validation_status": "unverified",
        "summary": "Manifest of the three quote-verification artifacts.",
    },
    {
        "event_id": f"{base}-review-01",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASSES,
        "target_id": "ledger/citation_audit_scc_candidates_worker-009.csv",
        "reviewer": "worker-009",
        "verdict": "accept",
        "score": 4.0,
        "hard_failures": [],
        "findings": [
            "Five of five correction quotes are byte-exact in their pinned source files with recorded sha256 verified (read the CSV newline-preserving; a text-mode read rewrites CRLF->LF inside quote_tex and falsely breaks the SRC-029 hash).",
            "Explicit C0/C2 discrimination against the frozen F2a/F2b schema predicates: 0/5 rows support a C0 vacuum binding and 0/5 support a C2 vacuum binding, because each quoted context states non-vacuum matter and/or non-zero-Lambda (de Sitter) or fixed-background linear content.",
            "Exact theorem locators recorded: SRC-033 maintheoremINTRO; SRC-029 abstract -> thmMain (non-vacuum); SRC-061 abstract -> int-the (non-vacuum); SRC-048 abstract with cor:RNV/cor:DLO non-vacuum; SRC-014 html title (scalar-field collapse).",
            "Binding-vs-mention classifier (CF-16 pattern) confirms the literal frozen ids in the proposed new mappings of CBC-09-008/012 sit inside removal phrases: 0 residual binding defects.",
            "INDEPENDENCE CAVEAT: this is same-worker cross-method self-verification, not an independent reviewer verdict; lead-audit review at the pinned hashes is still required.",
        ],
        "evidence_refs": [f"{rel(REC)}#{artifacts[rel(REC)][:16]}",
                          f"{rel(CSV)}#{artifacts[rel(CSV)][:16]}",
                          f"{rel(TOOL)}#{artifacts[rel(TOOL)][:16]}"],
    },
    {
        "event_id": f"{base}-status-01",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-009",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASSES,
        "status": "active",
        "hours": 0.4,
        "summary": ("Bounded task complete at worker level; node status, validation_status and gates deliberately "
                    "unchanged. 67/67 checks PASS / 0 FAIL; all five class-binding corrections corroborated at the "
                    "quote level with explicit C0/C2 discrimination; canonical ledger and patch files untouched; "
                    "numerics lock respected; no solver created."),
        "evidence_refs": [f"{rel(REC)}#{artifacts[rel(REC)][:16]}",
                          f"{rel(CKPT)}#{sh(CKPT)[:16]}",
                          f"ledger/citation_audit.csv#{anchors['canonical_ledger'][:16]}"],
        "next_falsifier": ver["next_falsifier"],
    },
]

existing = set()
if os.path.exists(OUTBOX):
    for line in open(OUTBOX, encoding="utf-8"):
        if line.strip():
            try:
                existing.add(json.loads(line)["event_id"])
            except Exception:
                pass

appended = 0
with open(OUTBOX, "a", encoding="utf-8") as f:
    for e in events:
        if e["event_id"] in existing:
            continue
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
        appended += 1

# validate whole outbox parses
n = 0
for line in open(OUTBOX, encoding="utf-8"):
    if line.strip():
        json.loads(line)
        n += 1

print(json.dumps({
    "checkpoint": rel(CKPT), "checkpoint_sha256": sh(CKPT),
    "events_appended": appended, "outbox_events_total": n,
    "event_ids": [e["event_id"] for e in events],
}, indent=1))
