#!/usr/bin/env python3
"""Emit W037-L0-HF02-CLASSBIND-EVIDENCE-01 events + checkpoint.

Writes only: comms/outbox/worker-037.jsonl (append), this artifact directory
(SHA256SUMS), and runtime/state/w037_l0_hf02_classbind_checkpoint.json.
Every event is schema-validated with research_map.schemas.validate_event before
it is appended; an invalid event aborts the whole batch.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUTBOX = os.path.join(REPO, "comms/outbox/worker-037.jsonl")
EVENTS = os.path.join(REPO, "research_map/events.jsonl")
CHECKPOINT = os.path.join(REPO, "runtime/state/w037_l0_hf02_classbind_checkpoint.json")

TASK_ID = "W037-L0-HF02-CLASSBIND-EVIDENCE-01"
ACTOR = "worker-037"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"]
NODE = "L0"
GATE = "G-LIT"
NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
TS = NOW.replace(":", "").replace("-", "")[:15]

sys.path.insert(0, REPO)
from research_map.schemas import validate_event  # noqa: E402


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_report():
    with open(os.path.join(HERE, "report.json")) as f:
        return json.load(f)


def build_files():
    names = {
        "REPORT.md": "report",
        "report.json": "verification_report",
        "build_candidate.py": "checker",
        "binding_rules.json": "decision_table",
        "CANDIDATE.json": "candidate_spec",
        "candidate_ledger_variantB.jsonl": "candidate_artifact",
        "candidate_ledger_variantA.jsonl": "candidate_artifact",
        "SHA256SUMS": "checksums",
    }
    out = []
    for n, t in names.items():
        p = os.path.join(HERE, n)
        out.append({"name": n, "path": os.path.relpath(p, REPO), "type": t, "sha256": sha256_file(p)})
    return out


def write_sha256sums():
    names = sorted(n for n in os.listdir(HERE)
                   if os.path.isfile(os.path.join(HERE, n)) and n != "SHA256SUMS")
    with open(os.path.join(HERE, "SHA256SUMS"), "w") as f:
        for n in names:
            f.write(f"{sha256_file(os.path.join(HERE, n))}  {n}\n")


def main():
    rep = read_report()
    write_sha256sums()
    files = build_files()
    vB = next(f for f in files if f["name"] == "candidate_ledger_variantB.jsonl")
    vA = next(f for f in files if f["name"] == "candidate_ledger_variantA.jsonl")
    repj = next(f for f in files if f["name"] == "report.json")
    cand = next(f for f in files if f["name"] == "CANDIDATE.json")
    checker = next(f for f in files if f["name"] == "build_candidate.py")
    rules = next(f for f in files if f["name"] == "binding_rules.json")
    readme = next(f for f in files if f["name"] == "REPORT.md")

    # checkpoint (written before event hash computation is impossible; compute then write then
    # patch its hash into the status event at the end)
    checkpoint = {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "instance": f"worker-037-{TS}",
        "created_at": NOW,
        "node_id": NODE,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "status": "complete_worker_level",
        "verdict": "REPAIR_CANDIDATE_VALIDATED_ADVISORY",
        "hard_pins": rep["hard_pins_measured"],
        "context_pins_at_start": rep["context_pins_measured_at_start"],
        "context_drift_during_run": rep.get("context_drift_during_run", {}),
        "checks_all_pass": rep["checks_all_pass"],
        "controls_all_expected": rep["controls_all_expected"],
        "checks": rep["checks"],
        "controls": rep["controls"],
        "live_literal_disjunctions": rep["live_literal_disjunctions"],
        "candidate_sha256": rep["candidate_sha256"],
        "artifact_sha256": {f["name"]: f["sha256"] for f in files},
        "adjacent_c0_typed_census": rep["adjacent_c0_typed_census"],
        "falsifier": ("Re-run build_candidate.py at the hard pins: falsified if any of the 8 rows "
                      "stops disjoining two frozen ids, any check flips false, any evidence quote "
                      "leaves its field, a variant leaves a disjunction/unknown token, or a "
                      "canonical path changes. Hard-pin drift voids (exit 3) rather than falsifies."),
        "does_not_claim": [
            "gate verdict", "node status", "validation_status promotion",
            "authority to edit canonical artifacts", "A0/rubric scope ruling",
            "class-binding repair as landed", "theorem", "physics or mathematics result",
            "one of the two independent accepts",
        ],
        "next_falsifier": ("Controller/A0 BL-7 ruling; if a repair is authorized, apply the chosen "
                           "variant as a NEW ledger revision and re-audit at the new hash; then "
                           "re-run this instrument against the new bytes."),
    }
    with open(CHECKPOINT, "w") as f:
        json.dump(checkpoint, f, indent=1, ensure_ascii=False, sort_keys=True)
    ck_hash = sha256_file(CHECKPOINT)
    ck_rel = os.path.relpath(CHECKPOINT, REPO)

    ev = []
    base = f"w037-hf02classbind-{TS}"
    for f in files:
        ev.append({
            "event_id": f"{base}-artifact-{f['name'].replace('.', '_')}",
            "event_type": "artifact",
            "created_at": NOW,
            "actor": ACTOR,
            "node_id": NODE,
            "class_id": ";".join(CLASS_IDS),
            "class_ids": CLASS_IDS,
            "gate": GATE,
            "task_id": TASK_ID,
            "artifact_type": f["type"],
            "path": f["path"],
            "sha256": f["sha256"],
            "validation_status": "unverified",
            "evidence_refs": [f"{repj['path']}#{repj['sha256'][:12]}",
                              f"{vB['path']}#{vB['sha256'][:12]}"],
            "summary": f"W037-L0-HF02-CLASSBIND-EVIDENCE-01 artifact: {f['name']}",
        })
    ev.append({
        "event_id": f"{base}-artifact-checkpoint",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": NODE,
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "task_id": TASK_ID,
        "artifact_type": "checkpoint",
        "path": ck_rel,
        "sha256": ck_hash,
        "validation_status": "unverified",
        "evidence_refs": [f"{repj['path']}#{repj['sha256'][:12]}"],
    })

    ev.append({
        "event_id": f"{base}-claim",
        "event_type": "claim",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": NODE,
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "task_id": TASK_ID,
        "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-ledger measurement, not a mathematics claim. At pins ledger/theorems.jsonl "
            "a1674f094979, evaluation_rubric.yaml d748a9e3574e, F0 taxonomy 0abb9ed8a961: the live "
            "HF-02 class-disjunction set is exactly the 8 rows D-004, D-005, T-303, T-305, T-402, "
            "T-515, T-526, T-528; each row's own text binds the C2 class for T-305/T-402/T-526, the "
            "WCC class for T-515/T-528, and no frozen class for D-004/D-005/T-303. Two candidate "
            "ledgers (variantA sha256 969c9bef8a63, variantB sha256 b2a27c9cf49b) each clear the "
            "literal disjunction (8 -> 0) with 0 unknown tokens, 0 other-key changes, and no added "
            "canonical-detector finding; canonical bytes are unchanged."
        ),
        "assumptions": [
            "The literal HF-02 predicate for this ledger surface is: class_ids contains two or more frozen class tokens (the canonical scanner does not scan class_ids cardinality; measured).",
            "A row's binding is what its own statement/does_not_imply/scope_caveats text asserts or entails, per the frozen class contracts and the rubric implication note (SCC-C0 implies SCC-C2, not conversely).",
            "informs_classes is the ledger's existing relevance channel (7 live rows use it with class_ids []).",
            "No canonical artifact was edited; all measurement is read-only.",
        ],
        "falsifier": rep["checks"] and (
            "Re-run build_candidate.py at the hard pins: falsified if any of the 8 rows stops "
            "disjoining two frozen ids, any declared check flips to false, any evidence quote no "
            "longer occurs in its named field, a variant leaves a disjunction or unknown token, or "
            "a canonical path changes during the run. Hard-pin drift voids (exit 3), not falsifies."
        ),
        "evidence_refs": [
            f"{repj['path']}#{repj['sha256'][:12]}",
            f"{checker['path']}#{checker['sha256'][:12]}",
            f"{rules['path']}#{rules['sha256'][:12]}",
            f"{cand['path']}#{cand['sha256'][:12]}",
            f"{vB['path']}#{vB['sha256'][:12]}",
            f"{vA['path']}#{vA['sha256'][:12]}",
            f"{readme['path']}#{readme['sha256'][:12]}",
            "ledger/theorems.jsonl#a1674f094979",
            "evaluation_rubric.yaml#d748a9e3574e",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        ],
        "artifact_refs": [f"{cand['path']}#{cand['sha256'][:12]}",
                          f"{vB['path']}#{vB['sha256'][:12]}"],
        "does_not_claim": checkpoint["does_not_claim"],
    })

    ev.append({
        "event_id": f"{base}-blocker",
        "event_type": "blocker",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": NODE,
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "task_id": TASK_ID,
        "blocker_id": "W037-BL-HF02-OWNER-RULING",
        "description": (
            "The HF-02 ledger class-disjunction repair cannot land from the worker side: the BL-7 "
            "controller/A0 ruling on whether HF-02 is ledger-scoped is still open, and which single "
            "class each row binds is an owner content decision. This task supplies the quote-verified "
            "evidence and two validated candidate ledgers (variantA first-listed / variantB "
            "evidence-driven) but applies neither. Two adjacent items also need owner disposition: "
            "(i) T-402.regularity keeps its separate canonical bare-composite finding; (ii) T-302 is "
            "a single-class C0 row typed conclusion_type=theorem against the C0 rubric status_risk."
        ),
        "needed_to_unblock": (
            "Controller/A0 (a) rule HF-02 ledger scope; (b) if repairing, choose variant A or B, "
            "authorize it as a NEW ledger revision, and dispatch a fresh verdict round at the new "
            "hash (all current verdicts void on the hash move); (c) rule on the T-302 C0+theorem "
            "typing and the T-402.regularity text."
        ),
        "evidence_refs": [
            f"{repj['path']}#{repj['sha256'][:12]}",
            f"{cand['path']}#{cand['sha256'][:12]}",
            f"{vB['path']}#{vB['sha256'][:12]}",
            "ledger/theorems.jsonl#a1674f094979",
            "evaluation_rubric.yaml#d748a9e3574e",
            "artifacts/worker-063/l0_scope_adjudication/report.json",
        ],
    })

    ev.append({
        "event_id": f"{base}-status",
        "event_type": "status",
        "created_at": NOW,
        "actor": ACTOR,
        "node_id": NODE,
        "class_id": ";".join(CLASS_IDS),
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "task_id": TASK_ID,
        "status": "active",
        "hours": 0.6,
        "summary": (
            "W037-L0-HF02-CLASSBIND-EVIDENCE-01 complete at worker level (task status only; worker "
            "events cannot set node/gate state). One bounded class-bound task self-selected from "
            "the live BL-7 critical path; no inbox card existed for worker-037. 8/8 live disjoined "
            "rows evidence-bound; 16/16 checks, 8/8 controls; two candidate ledgers validated; "
            "canonical bytes unchanged. Checkpoint written."
        ),
        "evidence_refs": [
            f"{repj['path']}#{repj['sha256'][:12]}",
            f"{readme['path']}#{readme['sha256'][:12]}",
            f"{vB['path']}#{vB['sha256'][:12]}",
            f"{ck_rel}#{ck_hash[:12]}",
        ],
        "next_falsifier": checkpoint["falsifier"],
        "does_not_claim": checkpoint["does_not_claim"],
    })

    # validate every event before writing anything
    bad = []
    for e in ev:
        try:
            validate_event(e)
        except Exception as exc:  # SchemaError
            bad.append({"event_id": e.get("event_id"), "error": str(exc)})
    if bad:
        print("SCHEMA REJECT:", json.dumps(bad, indent=1))
        return 1

    existing = set()
    for p in (OUTBOX, EVENTS):
        if os.path.exists(p):
            with open(p, errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("event_id"):
                        existing.add(d["event_id"])
    dupes = [e["event_id"] for e in ev if e["event_id"] in existing]
    if dupes:
        print("DUPLICATE event_id:", dupes)
        return 1

    with open(OUTBOX, "a") as f:
        for e in ev:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    print(json.dumps({
        "events_emitted": len(ev),
        "outbox": os.path.relpath(OUTBOX, REPO),
        "checkpoint": ck_rel,
        "checkpoint_sha256": ck_hash,
        "artifact_sha256": {f["name"]: f["sha256"] for f in files},
        "variantB_sha256": vB["sha256"],
        "variantA_sha256": vA["sha256"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
