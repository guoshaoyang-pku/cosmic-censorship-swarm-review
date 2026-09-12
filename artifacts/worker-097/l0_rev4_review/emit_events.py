#!/usr/bin/env python3
"""Emit worker-097 rev-4 L0 review events + checkpoint (idempotent, validated, fail-closed).

Appends to comms/outbox/worker-097.jsonl only after every event passes
research_map/schemas.py:validate_event. Writes runtime/state/w097_checkpoint_l0_rev4_review.json
and appends a one-line summary to runtime/state/w097_checkpoints.jsonl. Re-running skips an
event_id that already exists in the outbox.
"""
from __future__ import annotations
import datetime, hashlib, json, os, sys

REPO = "/data3/guoshaoyang/workdir/ai4math-swarm"
OUT = "artifacts/worker-097/l0_rev4_review"
OUTBOX = "comms/outbox/worker-097.jsonl"
CKPT = "runtime/state/w097_checkpoint_l0_rev4_review.json"
CKPT_LOG = "runtime/state/w097_checkpoints.jsonl"
TASK = "W097-L0-REV4-INDEP-REVIEW-01"
LEDGER = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
AUDIT = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
RUBRIC = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"
ARCHIVE = "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72"
REV3 = "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6"
CLASSES = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
NOW = lambda: datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def ref(p):
    return f"{p}#sha256:{sha(p)}"


def main():
    os.chdir(REPO)
    sys.path.insert(0, REPO)
    from research_map.schemas import validate_event, SchemaError

    report = json.load(open(f"{OUT}/report.json", encoding="utf-8"))
    files = {fn: f"{OUT}/{fn}" for fn in
             ("report.json", "controls.json", "run_l0_rev4_review.py", "README.md",
              "raw_sha256.txt")}
    H = {fn: sha(p) for fn, p in files.items()}
    ts = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    ev = []

    ev.append({
        "event_id": f"w097-l0rev4-status-{ts}", "event_type": "status", "created_at": NOW(),
        "actor": "worker-097", "node_id": "L0", "class_id": CLASSES, "gate": "G-LIT",
        "task_id": TASK, "status": "active", "hours": 0.6, "claims_completion": False,
        "summary": "No inbox card for worker-097 (recycled slot); took ONE bounded class-bound "
                   "task: W097-L0-REV4-INDEP-REVIEW-01, independent full review of the live L0 "
                   "head at a1674f094979 (rev 4). Verdict revise 1.75 (1 critical / 3 major / "
                   "3 minor); 21 checks + 12 controls, all controls PASS, pins stable "
                   "before/after. No gate verdict, node completion, or validation promotion.",
        "evidence_refs": [ref(files["report.json"]), ref(files["README.md"]),
                          f"ledger/theorems.jsonl#sha256:{LEDGER}",
                          f"ledger/citation_audit.csv#sha256:{AUDIT}",
                          f"evaluation_rubric.yaml#sha256:{RUBRIC}"],
        "next_falsifier": report["falsifier"],
    })
    for fn, atype, summary in (
            ("report.json", "l0_rev4_review_report",
             "21-check machine report: rev-3→rev-4 chain census, content preservation, HF-14 "
             "literal/axis scans, HF-02/class-binding, source scope, metadata anchors, controls."),
            ("run_l0_rev4_review.py", "review_instrument",
             "Fail-closed, stdlib+PyYAML instrument; pins 5 inputs by sha256, exits 3 on stale "
             "pin and 2 on control failure or drift; writes only its own --out."),
            ("controls.json", "review_controls",
             "12/12 mutation controls PASS (accepted status, supports_claim, unknown class, "
             "disjunction, content mutation, missing source, duplicate, forged review_status, "
             "field-removal silence, theorem-without-refs) plus null censuses."),
            ("README.md", "review_summary",
             "Human summary: revision chain, findings F1–F7, what did not fire, falsifier, "
             "reproduction, non-claims.")):
        ev.append({
            "event_id": f"w097-l0rev4-artifact-{fn.split('.')[0]}-{ts}",
            "event_type": "artifact", "created_at": NOW(), "actor": "worker-097",
            "node_id": "L0", "class_id": CLASSES, "gate": "G-LIT", "task_id": TASK,
            "artifact_type": atype, "path": files[fn], "sha256": H[fn],
            "validation_status": "unverified", "claims_completion": False,
            "summary": summary,
            "evidence_refs": [ref(files["report.json"]), ref(files["controls.json"]),
                              f"ledger/theorems.jsonl#sha256:{LEDGER}"],
            "next_falsifier": report["falsifier"],
        })
    ev.append({
        "event_id": f"w097-l0rev4-review-{ts}", "event_type": "review", "created_at": NOW(),
        "actor": "worker-097", "node_id": "L0", "class_id": CLASSES, "gate": "G-LIT",
        "task_id": TASK, "target_id": "L0", "reviewer": "worker-097",
        "reviewer_independence": report["reviewer_independence"],
        "reviewed_sha256": LEDGER, "reviewed_bytes": 151521,
        "review_scope": "full ledger (62/62 rows) at the live canonical hash",
        "verdict": report["verdict"], "score": report["score"],
        "hard_failures": report["hard_failures"],
        "findings": [f"{f['severity'].upper()} {f['id']}: {f['title']}"
                     for f in report["findings"]],
        "counts": report["counts"],
        "evidence_refs": [ref(files["report.json"]), ref(files["controls.json"]),
                          f"ledger/theorems.jsonl#sha256:{LEDGER}",
                          f"ledger/citation_audit.csv#sha256:{AUDIT}",
                          f"evaluation_rubric.yaml#sha256:{RUBRIC}",
                          f"artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl#sha256:{ARCHIVE}",
                          f"{OUT}/snapshots/theorems.jsonl#sha256:{REV3}",
                          "reviews/L0-review-093.json",
                          f"research_map/research_map.json#controller_gate_audit:G-LIT"],
        "next_falsifier": report["falsifier"],
    })
    ev.append({
        "event_id": f"w097-l0rev4-claim-{ts}", "event_type": "claim", "created_at": NOW(),
        "actor": "worker-097", "node_id": "L0", "class_id": CLASSES, "gate": "G-LIT",
        "task_id": TASK, "conclusion_type": "stability_result",
        "statement": "Artifact-and-checker result, not a mathematical claim: at pins "
                     f"ledger/theorems.jsonl {LEDGER[:12]} / ledger/citation_audit.csv "
                     f"{AUDIT[:12]} / evaluation_rubric.yaml {RUBRIC[:12]}, rev 4 is "
                     "content-preserving across all 62 theorem_ids (0 non-axis key changes vs "
                     "the archive ce42d205e761) and closes HF-14 by construction (0 literal "
                     "fires; 60 on the archive positive control), but HF-02 fires on 8 rows "
                     "that disjoin frozen class ids (D-004, D-005, T-303, T-305, T-402, T-515, "
                     "T-526, T-528), class-binding coverage is 26/62 = 0.4194 against target "
                     "1.0, and 0/62 ledger rows and 0/97 audit rows record source scope "
                     "metadata (matter_model/cosmological_constant/dimension/symmetry/"
                     "formulation). The rev-4 axis vocabulary (content_status, "
                     "author_asserts_supports) is not defined in A0 at its pinned hash. "
                     "Worker verdict: revise 1.75; only a gate owner can promote.",
        "assumptions": [
            "The measured sha256 is the artifact identity; the review is valid only at the "
            "five pinned hashes.",
            "HF-02's detector text (disjunction of class_ids) is applied to ledger rows as the "
            "rubric writes it; the row-level membership is reported so the reading is falsifiable.",
            "HF-01 is adjudicated as claim-scoped per its detector text ('claim.conclusion_type'), "
            "which differs from reviews/L0-review-093.json counting it as a ledger hard failure.",
            "The rev-4 axis split is assessed on its own builder guard and MANIFEST; no "
            "fabrication is alleged.",
            "This is a worker measurement: only a controller/lead can bind a gate verdict or "
            "promote validation_status."],
        "falsifier": report["falsifier"],
        "evidence_refs": [ref(files["report.json"]), ref(files["run_l0_rev4_review.py"]),
                          f"ledger/theorems.jsonl#sha256:{LEDGER}",
                          f"evaluation_rubric.yaml#sha256:{RUBRIC}"],
        "artifact_refs": [files["report.json"], files["run_l0_rev4_review.py"]],
        "next_falsifier": "Re-run at the same five pins and find a divergent check status, or "
                          "exhibit a rev-4 disjunctive row absent from the F1 list.",
    })

    # validate all before writing anything
    for e in ev:
        try:
            validate_event(dict(e))
        except SchemaError as ex:
            print(json.dumps({"error": "schema", "event_id": e.get("event_id"),
                              "message": str(ex)}))
            return 2

    seen = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    seen.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    appended = []
    with open(OUTBOX, "a", encoding="utf-8") as f:
        for e in ev:
            if e["event_id"] in seen:
                continue
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended.append(e["event_id"])

    # checkpoint: re-hash every on-disk artifact and the pins
    pins = {"ledger/theorems.jsonl": LEDGER, "ledger/citation_audit.csv": AUDIT,
            "evaluation_rubric.yaml": RUBRIC,
            "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl": ARCHIVE}
    verified, mismatches = {}, []
    for p, want in pins.items():
        got = sha(p)
        verified[p] = got
        if got != want:
            mismatches.append({"path": p, "want": want, "got": got})
    art = {}
    for fn, p in files.items():
        art[p] = {"sha256": H[fn], "bytes": os.path.getsize(p), "exists": True}
    ck = {
        "checkpoint_id": f"w097-ckpt-{ts}", "task_id": TASK, "created_at": NOW(),
        "actor": "worker-097", "target": {"node_id": "L0", "gate": "G-LIT",
                                          "reviewed_sha256": LEDGER},
        "revision_chain": {"archive": ARCHIVE, "rev3": REV3, "rev4": LEDGER},
        "artifacts": art, "pins_reverified": verified, "pin_mismatches": mismatches,
        "verdict": report["verdict"], "score": report["score"],
        "counts": report["counts"],
        "controls": {"total": len(report["controls"]),
                     "failed": report.get("control_failures", [])},
        "events_appended_this_run": appended,
        "authority": "worker checkpoint only; no gate verdict, node status, or validation "
                     "promotion is claimed",
        "falsifier": report["falsifier"],
    }
    os.makedirs(os.path.dirname(CKPT), exist_ok=True)
    with open(CKPT, "w", encoding="utf-8") as f:
        json.dump(ck, f, indent=1, ensure_ascii=False)
    ck_hash = sha(CKPT)
    with open(CKPT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"checkpoint_id": ck["checkpoint_id"], "task_id": TASK,
                            "actor": "worker-097", "created_at": NOW(),
                            "path": CKPT, "sha256": ck_hash,
                            "verdict": report["verdict"], "score": report["score"],
                            "pin_mismatches": len(mismatches)},
                           ensure_ascii=False) + "\n")

    final = {
        "event_id": f"w097-l0rev4-status-final-{ts}", "event_type": "status",
        "created_at": NOW(), "actor": "worker-097", "node_id": "L0", "class_id": CLASSES,
        "gate": "G-LIT", "task_id": TASK, "status": "active", "hours": 0.2,
        "claims_completion": False,
        "summary": "CHECKPOINT complete and exiting cleanly. One bounded class-bound task "
                   "(W097-L0-REV4-INDEP-REVIEW-01) delivered: independent full L0 review at "
                   "a1674f094979, verdict revise 1.75, 12/12 controls PASS, all pins "
                   "re-verified against disk, zero authority-overreach events. Slot exits for "
                   "recycling.",
        "evidence_refs": [f"{CKPT}#sha256:{ck_hash}", ref(files["report.json"]),
                          ref(files["controls.json"]),
                          f"ledger/theorems.jsonl#sha256:{LEDGER}"],
        "next_falsifier": report["falsifier"],
    }
    try:
        validate_event(dict(final))
    except SchemaError as ex:
        print(json.dumps({"error": "schema_final", "message": str(ex)}))
        return 2
    with open(OUTBOX, "a", encoding="utf-8") as f:
        if final["event_id"] not in seen:
            f.write(json.dumps(final, ensure_ascii=False) + "\n")
            appended.append(final["event_id"])

    print(json.dumps({"appended": appended, "checkpoint": CKPT, "checkpoint_sha256": ck_hash,
                      "pin_mismatches": mismatches, "events_total_this_run": len(appended)},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
