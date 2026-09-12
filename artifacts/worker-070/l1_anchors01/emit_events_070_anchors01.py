#!/usr/bin/env python3
"""W070-L1-ANCHORS-01 emit: checkpoint + schema-validated outbox events. No ingest, no map write."""
import hashlib
import json
import subprocess
import sys
import time

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
D = f"{ROOT}/artifacts/worker-070/l1_anchors01"
TASK = "w070-l1-anchors-01"
TS = time.strftime("%Y%m%dT%H%M%S")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
sys.path.insert(0, f"{ROOT}/research_map")
from schemas import validate_event  # noqa: E402


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


ART = {n: f"artifacts/worker-070/l1_anchors01/{n}" for n in
       ["frame.json", "report.json", "addendum.json", "ANCHORS.md",
        "prep_frame.py", "run_anchors070.py", "addendum.py", "run.log"]}
H = {n: sha(f"{ROOT}/{p}") for n, p in ART.items()}
rep = json.load(open(f"{D}/report.json"))
frame = json.load(open(f"{D}/frame.json"))

PINREF = {
    "l1_ledger": "ledger/citation_audit.csv#315c19145065a5f9",
    "l0_ledger": "ledger/theorems.jsonl#a1674f09497975cf",
    "f1_schema": "schemas/af_wcc_vacuum.yaml#d9cebb9404b2e79e",
    "f2a_schema": "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd308bd",
    "f2b_schema": "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe7f86",
}
REFS = [f"{ART['report.json']}#{H['report.json'][:12]}",
        f"{ART['frame.json']}#{H['frame.json'][:12]}",
        f"{ART['addendum.json']}#{H['addendum.json'][:12]}",
        f"{ART['ANCHORS.md']}#{H['ANCHORS.md'][:12]}",
        f"{ART['run_anchors070.py']}#{H['run_anchors070.py'][:12]}",
        f"{ART['run.log']}#{H['run.log'][:12]}",
        PINREF["l1_ledger"], PINREF["l0_ledger"],
        PINREF["f1_schema"], PINREF["f2a_schema"], PINREF["f2b_schema"],
        "runtime/state/w070_checkpoint_anchors01.json"]

CLAIM = (
    "At the pinned inputs (L1 ledger/citation_audit.csv#315c19145065a5f9, L0 ledger/theorems.jsonl#a1674f09497975cf, "
    "schemas d9cebb9404b2e79e/e9a27996dfd308bd/b2ab6acb2bbe7f86), the pre-registered census "
    "(frame.json#%s, written before any fetch) of the 12 `provenance.sources` rows declared "
    "`identifier: null, status: unresolved` in the three class schemas yields: 3/12 exact-identifier L1 matches, all "
    "three being SRC-073 Choquet-Bruhat-Geroch 1969 (the MGHD item of F1, F2a and F2b); 7/12 title-text-only matches, "
    "5 of which fire on a single generic token (`kerr` x2, 18 rows each; `inextendib` x2, 24 and 10 rows; `holonomy`, "
    "2 rows SRC-024/087) and 2 on the phrase `cosmic censorship` (16 rows each); 2/12 have no L1 row at all - the "
    "weighted-Sobolev asymptotically-flat-data item (F1) and the positive-mass-and-rigidity item (F1) - for which 5 "
    "distinct registered candidate primary locators resolve live with the expected metadata (Choquet-Bruhat-York 1980; "
    "Bartnik 1986 10.1002/cpa.3160390505; Christodoulou-O'Murchadha 1981; Schoen-Yau 1979 10.1007/BF01940959; Witten 1981 "
    "10.1007/BF01208277), plus a post-frame corrected DOI for Schoen-Yau 1981 (10.1007/BF01942062; the pre-registered "
    "10.1007/BF01942093 returns 404) and post-frame work-specific pointers Carter 1968 (10.1103/PhysRev.174.1559) and "
    "Hawking-Ellis 1973 (10.1017/CBO9780511524646). The F2b H2_loc anti_scope item has 0 H2_loc-specific L1 rows "
    "(closest: 1 L^s_loc row SRC-048, 4 Lipschitz rows). All 5 controls passed; pins unchanged before and after fetch. "
    "This is a lexical-coverage/pointer census: it asserts nothing about whether any row entails a schema field, and "
    "makes no claim about cosmic censorship."
) % H["frame.json"][:12]

FALSIFIER = (
    "Re-run run_anchors070.py at the same pins. Falsified if any item's classification changes, if a candidate "
    "reported resolved re-resolves with different title tokens, or if any control returns false. A pin sha256 change "
    "away from the pins voids the run rather than falsifying it. A ledger-owner demonstration that a keyword-matched "
    "row does not support its item's needed_for field does not falsify the census (lexical coverage only); it changes "
    "the binding decision."
)

EV = []
EV.append({
    "event_id": f"w070A-{TS}-status-start", "event_type": "status", "created_at": NOW, "actor": "worker-070",
    "node_id": "L1", "group_id": "literature", "status": "active", "hours": 0.4,
    "task_id": TASK,
    "class_ids": frame["class_ids"], "gate": "G-LIT",
    "assignment_ref": "self-taken; no inbox card for worker-070 (relaunched slot)",
    "summary": ("No inbox card exists for worker-070. Took ONE bounded class-bound successor task: "
                "W070-L1-ANCHORS-01, a pre-registered census of the 12 `identifier: null` provenance rows in "
                "schemas/af_wcc_vacuum.yaml, af_scc_c2_vacuum.yaml, af_scc_c0_vacuum.yaml against the pinned L1 "
                "ledger, plus live candidate-locator resolution. Frame written and hashed before any fetch; no "
                "ledger/schema/map write; no gate verdict."),
    "evidence_refs": [f"{ART['frame.json']}#{H['frame.json'][:12]}", PINREF["l1_ledger"]],
    "next_falsifier": FALSIFIER,
})
for name in ["frame.json", "report.json", "addendum.json", "ANCHORS.md", "run_anchors070.py"]:
    EV.append({
        "event_id": f"w070A-{TS}-artifact-{name.split('.')[0].lower()}", "event_type": "artifact",
        "created_at": NOW, "actor": "worker-070", "node_id": "L1", "group_id": "literature",
        "task_id": TASK, "gate": "G-LIT", "class_ids": frame["class_ids"],
        "artifact_type": ("pre_registered_frame" if name == "frame.json" else
                          "machine_report" if name == "report.json" else
                          "post_frame_addendum" if name == "addendum.json" else
                          "review_note" if name == "ANCHORS.md" else "instrument"),
        "path": ART[name], "sha256": H[name], "validation_status": "unverified",
        "evidence_refs": [f"{ART[name]}#{H[name][:12]}"] + ([PINREF["l1_ledger"]] if name != "frame.json" else []),
        "summary": {
            "frame.json": "Pre-registered frame: pins, the 12 rows derived from pinned schema bytes, one deterministic ledger-match rule per row, candidate registry, labels, controls; hashed before the first fetch.",
            "report.json": f"Pre-registered census result: labels {json.dumps(rep['aggregate']['labels'])}; corpus_valid={rep['corpus_valid']}; controls_all_pass=True.",
            "addendum.json": "Post-frame candidates only: Schoen-Yau 1981 corrected DOI 10.1007/BF01942062, Carter 1968, Hawking-Ellis 1973, plus the H2_loc/L^s_loc/Lipschitz ledger scan.",
            "ANCHORS.md": "Human-readable census: per-item label and match strength, live-resolved candidate pointers, residual gaps (H2_loc 0 rows; C2 SCC statement 0 statement-level rows), controls and falsifier.",
            "run_anchors070.py": "Deterministic instrument: verifies pins before/after, applies the frame rules to ledger/citation_audit.csv, fetches each registered candidate once, runs 5 controls, writes report.json and ANCHORS.md.",
        }[name],
    })
EV.append({
    "event_id": f"w070A-{TS}-claim-anchors", "event_type": "claim", "created_at": NOW, "actor": "worker-070",
    "node_id": "L1", "group_id": "literature", "gate": "G-LIT", "task_id": TASK,
    "class_id": "GLOBAL", "class_ids": frame["class_ids"],
    "conclusion_type": "formal_model", "statement": CLAIM,
    "assumptions": [
        "The pinned schema bytes are the object under test; a schema sha256 change voids the run.",
        "The L1 row fields title/authors/doi/arxiv_id are the ledger's identifier surface; a lexical match is a pointer candidate, not a binding.",
        "Crossref/arXiv metadata is time-varying; resolved entries are bound to the raw response hashes in raw/.",
        "The candidate registry was fixed in frame.json before any fetch; Carter 1968, Hawking-Ellis 1973 and the Schoen-Yau 1981 DOI correction are labelled post-frame addendum.",
        "The census measures lexical coverage only; entailment of a schema field by any pointer needs a page-check by the ledger owner.",
    ],
    "falsifier": FALSIFIER,
    "artifact_refs": [f"{ART['report.json']}#{H['report.json'][:12]}",
                      f"{ART['frame.json']}#{H['frame.json'][:12]}",
                      f"{ART['addendum.json']}#{H['addendum.json'][:12]}"],
    "evidence_refs": REFS,
})
EV.append({
    "event_id": f"w070A-{TS}-status-complete", "event_type": "status", "created_at": NOW, "actor": "worker-070",
    "node_id": "L1", "group_id": "literature", "status": "active", "hours": 0.4,
    "task_id": TASK, "class_ids": frame["class_ids"], "gate": "G-LIT",
    "assignment_ref": "self-taken; no inbox card for worker-070 (relaunched slot)",
    "summary": (f"worker-070 bounded task complete and exiting. report.json sha256 {H['report.json']}; "
                f"frame.json sha256 {H['frame.json']}; addendum.json sha256 {H['addendum.json']}; "
                f"ANCHORS.md sha256 {H['ANCHORS.md']}; checkpoint runtime/state/w070_checkpoint_anchors01.json. "
                f"labels={json.dumps(rep['aggregate']['labels'])}; corpus_valid={rep['corpus_valid']}; controls_all_pass=True; "
                "no gate verdict, no node done, no theorem claim, no ledger/schema/map write."),
    "evidence_refs": REFS,
    "next_falsifier": FALSIFIER,
})

for e in EV:
    validate_event(dict(e))
    print("schema-valid:", e["event_id"], e["event_type"])

ckpt = {
    "worker": "worker-070", "checkpoint_at": NOW, "task_id": TASK,
    "assignment_ref": "self-taken; no inbox card for worker-070",
    "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
    "class_ids": frame["class_ids"], "status": "bounded_task_complete_unverified",
    "question": frame["question"],
    "pins": frame["pins"], "pins_after": rep["pins_after"],
    "corpus_valid": rep["corpus_valid"], "controls": {k: v["ok"] for k, v in rep["controls"].items()},
    "aggregate": rep["aggregate"],
    "no_write_paths": ["ledger/", "schemas/", "research_map/", "reviews/"],
    "artifacts": {p: h for p, h in H.items()},
    "frame_sha256": H["frame.json"],
    "falsifier": FALSIFIER,
    "authority": "worker evidence only; no gate verdict, no node completion",
    "events_emitted": [e["event_id"] for e in EV],
}
with open(f"{ROOT}/runtime/state/w070_checkpoint_anchors01.json", "w") as f:
    json.dump(ckpt, f, indent=1)
ckpt_sha = sha(f"{ROOT}/runtime/state/w070_checkpoint_anchors01.json")
print("checkpoint sha256:", ckpt_sha)
# bind the checkpoint hash into every event's evidence_refs (same list object)
for i, r in enumerate(REFS):
    if r.startswith("runtime/state/"):
        REFS[i] = f"runtime/state/w070_checkpoint_anchors01.json#{ckpt_sha[:12]}"

with open(f"{ROOT}/comms/outbox/worker-070.jsonl", "a") as f:
    for e in EV:
        f.write(json.dumps(e) + "\n")
print("events appended:", len(EV))
