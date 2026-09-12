#!/usr/bin/env python3
"""Deterministic, idempotent event emitter for W078-F1-REPAIR-VERIFY-01.

Writes the worker checkpoint and appends the task's events to
comms/outbox/worker-078.jsonl.  Event ids are fixed strings (no wall clock), so
re-running this script is a no-op once the events exist.  It validates every line
it appends and never touches research_map/events.jsonl (controller-owned).
"""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DIR = "artifacts/worker-078/f1_repair_verify"
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-078.jsonl")
CHECKPOINT = "runtime/state/w078_checkpoint_3_f1_repair_verify.json"
PIN = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
OLD_PIN = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
F0 = "research_map/formulation_taxonomy.yaml"


def sha(p):
    with open(os.path.join(ROOT, p), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def now():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def main():
    rep = json.load(open(os.path.join(ROOT, DIR, "report.json")))
    assert rep["verdict"] == "revise" and rep["counts"]["hard_fail"] == 1, rep["counts"]
    assert rep["target"]["pin"] == PIN

    paths = {
        "harness": "%s/verify_f1_repair.py" % DIR,
        "report": "%s/report.json" % DIR,
        "rerun": "%s/report_rerun.json" % DIR,
        "retest": "%s/retest_compare.json" % DIR,
        "readme": "%s/README.md" % DIR,
        "snapshot": "%s/snapshot/af_wcc_vacuum.cce9c60146d6.yaml" % DIR,
    }
    H = {k: sha(v) for k, v in paths.items()}
    f0h = sha(F0)

    ckpt = {
        "checkpoint_id": "w078-ckpt-3-f1-repair-verify",
        "worker": "worker-078",
        "task_id": "W078-F1-REPAIR-VERIFY-01",
        "created_at": now(),
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "pin": PIN,
        "old_pin": OLD_PIN,
        "snapshot": paths["snapshot"],
        "live_canonical_at_end": rep["target"]["live_sha256_at_end"],
        "f0_canonical_at_verify": f0h,
        "verdict": rep["verdict"],
        "score": rep["score"],
        "counts": rep["counts"],
        "hard_failures": rep["hard_failures"],
        "repairs_verified": rep["repairs_verified"],
        "artifact_hashes": {k: {"path": paths[k], "sha256": H[k]} for k in paths},
        "checkpoint_path": CHECKPOINT,
        "detector_provenance": {
            "note": "The first detector draft mis-parsed the containment phrases (regex for the "
                    "J^-(q) token was malformed, 'is [NOT] contained in' and case were not "
                    "accepted, and the control on 9a8bd4c96800 failed). The reported run is the "
                    "post-fix run; the archived control (R18) is the evidence that the detectors "
                    "discriminate defective from repaired bytes.",
            "control_status": "PASS",
            "control_detail": [c["detail"] for c in rep["checks"] if c["id"] == "R18"][0],
        },
        "next_falsifier": rep["next_falsifier"],
        "emitter": "artifacts/worker-078/f1_repair_verify/emit_w078_repair_events.py",
    }
    os.makedirs(os.path.join(ROOT, "runtime/state"), exist_ok=True)
    with open(os.path.join(ROOT, CHECKPOINT), "w") as fh:
        json.dump(ckpt, fh, indent=1)
        fh.write("\n")
    H["checkpoint"] = sha(CHECKPOINT)
    paths["checkpoint"] = CHECKPOINT

    ts = now()
    base = {"created_at": ts, "actor": "worker-078", "node_id": "F1",
            "class_id": "AF-WCC-VAC-GEN", "task_id": "W078-F1-REPAIR-VERIFY-01"}
    fb = rep["evidence_refs"]

    events = []
    events.append(dict(base, event_id="w078-f1repair-task-claim", event_type="status",
                       status="active", hours=0.5,
                       summary=("No assignment card in comms/inbox for worker-078. Taking one bounded "
                                "class-bound task: independent hash-bound verification of the F1 rev12 "
                                "repair at pin cce9c60146d6 (unreviewed when taken; it claims to close "
                                "HF-06/HF-15-1, which this worker independently confirmed at 9a8bd4c96800). "
                                "Pin-then-verify with a drift-voiding binding and a positive control on the "
                                "archived defective bytes."),
                       evidence_refs=["schemas/af_wcc_vacuum.yaml#cce9c60146d6",
                                      "artifacts/worker-078/f1_quantifier_adjudication/report.json#f512a5cb6c14"],
                       next_falsifier=rep["next_falsifier"], artifact="%s/" % DIR))
    for key, atype, note in [
        ("harness", "verifier_code", "21-check repair verifier + discriminating control on the old defective snapshot."),
        ("report", "audit_report", "Primary run: verdict revise, 20/21 checks pass, sole hard failure R17 (stale consistency-evidence hash)."),
        ("rerun", "audit_report", "Second run: identical check statuses / verdict."),
        ("retest", "retest_comparison", "Run1 vs run2 check-status comparison: identical."),
        ("readme", "summary", "Method, verified repairs, control, limits, three falsifiers."),
        ("snapshot", "artifact_snapshot", "Byte-exact snapshot of the verified F1 rev12 bytes."),
        ("checkpoint", "checkpoint", "Worker checkpoint with artifact hashes and detector provenance."),
    ]:
        events.append(dict(base, event_id="w078-f1repair-artifact-%s" % key, event_type="artifact",
                           artifact_type=atype, path=paths[key], sha256=H[key],
                           validation_status="unverified", gate="G-FORM", note=note,
                           evidence_refs=["schemas/af_wcc_vacuum.yaml#cce9c60146d6"] + fb[:1]))
    events.append(dict(base, event_id="w078-f1repair-review-f1", event_type="review",
                       reviewer="worker-078", target_id="schemas/af_wcc_vacuum.yaml#cce9c60146d6",
                       target_node_id="F1", gate="G-FORM", verdict="revise", score=rep["score"],
                       cited_sha256=PIN, verified_sha256=PIN, binding=rep["binding"],
                       hard_failures=["R17: declared consistency_evidence_sha256 675a99d0d25b no longer "
                                      "resolves - artifacts/formulation/evidence/taxonomy_consistency.json "
                                      "measures 9e335e9ba1bf and was regenerated at 00:34:55, after F1 rev12 "
                                      "(00:31:41); the schema's own rule requires the consistency check to be "
                                      "re-run and the binding refreshed before any gate verdict."],
                       findings=[
                           "HF-06 / HF-15-1 REPAIRED and independently verified at the pinned bytes: quantifiers.formal:47 is now the single-q tail clause 'not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M'; D5:71-73 is the (q,t0) tail predicate and explicitly marks whole-curve containment as STRICTLY STRONGER and NOT the class predicate; quantifiers.negation:80 negates the tail predicate; visibility.definition:213 and negation_conclusion:214-215 remain tail-based.",
                           "Positive control R18 discriminates: the same detectors classify the archived defective 9a8bd4c96800 as tail=False whole=True d5_tail=False neg_tail=False (DEFECT) and the pinned bytes as repaired. Three detector-regex bugs were found by the control and fixed before the reported run (see checkpoint detector_provenance).",
                           "Co-emitted repairs verified at the pin: duplicate revised_at keys collapsed into revision_history (strict compose walk: 0 duplicates); no future-dated stamp; class_contract_pointer -> canonical classes.AF-WCC-VAC-GEN plus a separate class_contract_supplement_pointer (both resolve); AF_{I+} defined at i_plus.predicate_abbreviation:193; D0 retyped as a tagged regularity index with 0 surviving (s,delta) binders; declared F0 hash equals measured 0abb9ed8a961 and F0 was stable across the window; canonical class-separation helper returns 0 findings.",
                           "Remaining defect is binding hygiene, not quantifier semantics: refresh f0_binding.consistency_evidence_sha256 (or point it at a hash-stable evidence path) and re-run the consistency checker; the taxonomy_consistency.json file was observed rewritten twice during the window (00:33:16, 00:34:55) by the F0 writer, which is the freeze-discipline pattern the audit flagged.",
                           "Scope: structural/contract/semantic-form at one pinned hash only; no truth, non-vacuity, physics or citation verdict; no gate verdict and no node status set. f1_falsifier_tests.jsonl rebinding (worker-15 F-15-5) and the UNVERIFIED class_identity_variants SET-equivalence remain open and unassessed.",
                       ],
                       evidence_refs=["%s/report.json#%s" % (DIR, H["report"][:12]),
                                      "%s/report_rerun.json#%s" % (DIR, H["rerun"][:12]),
                                      "%s/retest_compare.json#%s" % (DIR, H["retest"][:12]),
                                      "%s/snapshot/af_wcc_vacuum.cce9c60146d6.yaml#cce9c60146d6" % DIR,
                                      "%s#%s" % (F0, f0h[:12])],
                       falsifier=("Re-measure schemas/af_wcc_vacuum.yaml: a sha256 other than %s voids the "
                                  "binding. At the pin, a whole-curve clause in quantifiers.formal/D5, a formal "
                                  "that no longer expands 'not exists visible_singularity_from_I_plus', or a "
                                  "non-discriminating control on %s falsifies the repair verdict. Refreshing the "
                                  "declared consistency-evidence hash falsifies the sole hard failure R17."
                                  % (PIN, OLD_PIN))))
    events.append(dict(base, event_id="w078-f1repair-status-final", event_type="status",
                       status="active", hours=0.5,
                       summary=("W078-F1-REPAIR-VERIFY-01 complete: F1 rev12 at cce9c60146d6 had already "
                                "repaired HF-06/HF-15-1 (tail quantifier in formal:47, D5:71-73, negation:80) "
                                "together with the duplicate-key, future-date, pointer, AF_{I+} and D0 "
                                "defects. Verdict revise, 20/21 checks, sole hard failure R17: the declared "
                                "consistency-evidence hash no longer resolves (file regenerated after the "
                                "schema was written). Control on the superseded defective bytes passes, so the "
                                "detectors discriminate. This is a completion claim, not a node transition."),
                       evidence_refs=["%s/report.json#%s" % (DIR, H["report"][:12]),
                                      "%s/README.md#%s" % (DIR, H["readme"][:12]),
                                      "%s#%s" % (CHECKPOINT, H["checkpoint"][:12])],
                       next_falsifier=rep["next_falsifier"], artifact="%s/" % DIR))

    existing = set()
    if os.path.exists(OUTBOX):
        with open(OUTBOX) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    added = 0
    with open(OUTBOX, "a") as fh:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            blob = json.dumps(ev, ensure_ascii=False)
            json.loads(blob)  # validate before writing
            assert ev["event_id"] and ev["event_type"] and ev["created_at"] and ev["actor"]
            fh.write(blob + "\n")
            added += 1
    print(json.dumps({"appended": added, "already_present": len(events) - added,
                      "checkpoint": CHECKPOINT, "hashes": H}, indent=1))


if __name__ == "__main__":
    main()
