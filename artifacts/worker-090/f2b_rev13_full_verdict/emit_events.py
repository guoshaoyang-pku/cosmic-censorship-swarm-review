#!/usr/bin/env python3
"""Emit the W090-F2B-REV13-FULL-01 review, worker checkpoint and outbox events.

Idempotent: skips any event_id already present in the outbox.  Writes only
worker-owned paths (artifacts/worker-090/..., reviews/F2b-rev13-full-090.json,
runtime/state/w090_*_checkpoint.json) and appends to the worker's own outbox.
"""
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TASK = "W090-F2B-REV13-FULL-01"
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-090.jsonl")
REVIEW = os.path.join(ROOT, "reviews", "F2b-rev13-full-090.json")
CKPT = os.path.join(ROOT, "runtime", "state", "w090_f2b_rev13_full_checkpoint.json")
ART = "artifacts/worker-090/f2b_rev13_full_verdict"

PINS = {
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F2b_mirror": ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F1": ("schemas/af_wcc_vacuum.yaml", "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "F0": ("research_map/formulation_taxonomy.yaml", "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "supplement": ("artifacts/formulation/formulation_taxonomy.yaml", "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "consistency_evidence": ("artifacts/formulation/evidence/taxonomy_consistency.json", "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"),
    "frozen": ("artifacts/formulation/FROZEN.json", "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
    "vocab_aliases": ("artifacts/formulation/VOCAB_ALIASES.json", "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba"),
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    now = datetime.now(CST).isoformat()
    res = json.load(open(os.path.join(ROOT, ART, "results.json")))
    ctr = json.load(open(os.path.join(ROOT, ART, "controls.json")))
    hashes = {}
    for rel in ("pin_snapshot.py", "check_f2b_rev13_full.py", "results.json", "controls.json",
                "README.md", "snapshot/MANIFEST.json"):
        p = os.path.join(ROOT, ART, rel)
        hashes[rel] = sha(p) if os.path.isfile(p) else None

    findings = [
        {"id": "W090-F2B13-01", "severity": "major (cross-artifact authority, non-blocking for content)",
         "statement": "F0 field_vocabulary still lists alias tokens (conclusion_type strong_cosmic_censorship_C0; genericity_kind provisional_baire_residual) while F2b uses the VOCAB_ALIASES canonical tokens (scc_c0_future_inextendibility, residual_comeager); F2b declares no VOCAB_ALIASES.json pointer. Same family as W090-VOCAB-01/04; needs the controller single-sourcing ruling, not a schema edit.",
         "evidence_refs": [f"{PINS['F0'][0]}#{PINS['F0'][1][:12]}", f"{PINS['vocab_aliases'][0]}#{PINS['vocab_aliases'][1][:12]}"]},
        {"id": "W090-F2B13-02", "severity": "minor",
         "statement": "review_status.independent_reviewers=[] and verdict=pending while >=6 F2b rev13 review events exist in the accepted stream at this pin (W090-R12-02 analog).",
         "evidence_refs": [f"{PINS['F2b'][0]}#{PINS['F2b'][1][:12]}", "research_map/events.jsonl"]},
        {"id": "W090-F2B13-03", "severity": "minor",
         "statement": "The schema still has no supplement hash field; the supplement d7419b4e8963 is bound only transitively via the FROZEN rev29 manifest, and taxonomy_consistency.json embeds 0 byte-identity witnesses (W090-FCONSEV-01/-02 open at this pin).",
         "evidence_refs": [f"{PINS['supplement'][0]}#{PINS['supplement'][1][:12]}", f"{PINS['frozen'][0]}#{PINS['frozen'][1][:12]}"]},
        {"id": "W090-F2B13-04", "severity": "info (fresh, cross-cutting)",
         "statement": "research_map/class_separation.py moved again during the CF-26 write-freeze: a8c04fc31e4a -> e36b0d644ca7 at 2026-09-12 01:06:12, with no artifact/assignment event announcing it in research_map/events.jsonl or comms/outbox. Detector-bound verdicts must cite the detector hash they measured. Pinned c266dbec returns 0 findings on F2b; live e36b0d64 also returns 0 on F2b.",
         "evidence_refs": ["research_map/class_separation.py#e36b0d644ca7", "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py#c266dbceca87"]},
    ]
    review = {
        "schema": "class-schema-review/v1",
        "review_id": TASK,
        "review_scope": "Independent, mechanized full-schema verification of F2b AF-SCC-C0-VAC-GEN rev13 at b2ab6acb2bbe under FROZEN rev29 815e08079aef: pins/mirror, binding chain, vocabulary, class boundary and conclusion inflation, C0/C2 implication direction, genericity, T1 data-class transfer guard, falsifier decidability, detector and fixture behavior. Not a gate verdict and not an endorsement of any numerics or literature node.",
        "target_id": "F2b",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "reviewer": "worker-090",
        "reviewer_role": "bounded execution worker; non-author of F0/F0R/F1/F2a/F2b; no canonical file written or edited",
        "verdict": "accept",
        "score": 4.0,
        "counts_as_full_schema_verdict": True,
        "blind": False,
        "blind_disclosure": "Not a carded blind review. Verdict-level rows of the map review index and worker-061's scoped CH-axis accept event were read while auditing F2b accept coverage; no full-schema F2b review body was read before this verdict. The audit lead decides whether this review counts toward binding coverage.",
        "reviewed_revision": 13,
        "reviewed_sha256": PINS["F2b"][1],
        "reviewed_pins": {k: {"path": v[0], "sha256": v[1]} for k, v in PINS.items()},
        "checks_total": res["counts"]["checks"],
        "checks_pass": res["counts"]["pass"],
        "blocking_failures": res["blocking_failures"],
        "controls": f"{ctr['caught']}/{ctr['total']}",
        "carriers": res["carriers"],
        "findings": findings,
        "hard_failures": [],
        "artifact_refs": [f"{ART}/check_f2b_rev13_full.py", f"{ART}/results.json",
                          f"{ART}/controls.json", f"{ART}/README.md", f"{ART}/pin_snapshot.py",
                          f"{ART}/snapshot/MANIFEST.json"],
        "evidence_refs": [f"{ART}/results.json#{hashes['results.json'][:12]}",
                          f"{ART}/controls.json#{hashes['controls.json'][:12]}",
                          f"{ART}/check_f2b_rev13_full.py#{hashes['check_f2b_rev13_full.py'][:12]}",
                          f"{PINS['F2b'][0]}#{PINS['F2b'][1][:12]}",
                          f"{PINS['F0'][0]}#{PINS['F0'][1][:12]}",
                          f"{PINS['supplement'][0]}#{PINS['supplement'][1][:12]}",
                          f"{PINS['consistency_evidence'][0]}#{PINS['consistency_evidence'][1][:12]}",
                          f"{PINS['frozen'][0]}#{PINS['frozen'][1][:12]}",
                          f"{PINS['vocab_aliases'][0]}#{PINS['vocab_aliases'][1][:12]}"],
        "assumptions": [
            "canonical paths are authoritative and the measured sha256 pins define the revision under audit",
            "all content checks read freeze-first snapshot copies; live canonical files are only hashed, never edited",
            "the pinned class-separation detector is the CF-26-recorded c266dbec copy; the live file is drifted and not adopted",
            "the semantic fixture stage is advisory because the suite's observed-verdict calibration is invalid (ADJ-CONTROL-STALENESS)",
            "core data_class equality uses the checker's declared norm_core normalization (parentheticals and articles stripped, parity truncated at first ';', provenance fields excluded)",
        ],
        "next_falsifier": "Any of: F2b canonical or mirror bytes change from b2ab6acb2bbe; any blocking check flipping to fail at the same pin; any pre-registered mutant escaping; the F0 declared hash or the consistency-evidence declaration going stale; or the pinned detector c266dbec returning a finding on the F2b text. Each voids this verdict at the new bytes.",
        "non_claims": [
            "no gate verdict, no node status, no validation_status promotion",
            "no canonical artifact was written or edited by this verification",
            "accept covers the schema content at the pin; it does not adjudicate the F0-allowed-list vs registry authority conflict (W090-F2B13-01), which is a controller/lead ruling",
            "not blind; the audit lead decides whether it counts toward the >=2-full-accept binding requirement",
            "does not re-derive the mathematics of C0 inextendibility and does not endorse any literature node",
        ],
        "authority_note": "advisory worker verdict; cannot set a gate verdict or node status",
        "created_at": now,
    }
    os.makedirs(os.path.dirname(REVIEW), exist_ok=True)
    with open(REVIEW, "w") as fh:
        json.dump(review, fh, indent=1, sort_keys=True)
    review_sha = sha(REVIEW)

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "actor": "worker-090",
        "task_id": TASK,
        "created_at": now,
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "headline": "F2b rev13 b2ab6acb: 44 checks, 40 pass, 0 blocking failures, 4 carriers, 8/8 mutants caught -> accept (advisory, not blind).",
        "pins": {k: {"path": v[0], "sha256": v[1]} for k, v in PINS.items()},
        "findings": ["W090-F2B13-01", "W090-F2B13-02", "W090-F2B13-03", "W090-F2B13-04"],
        "new_cross_cutting_observation": "research_map/class_separation.py moved a8c04fc31e4a -> e36b0d644ca7 at 01:06:12 with no announcing event (CF-26 extension)",
        "artifacts": {f"{ART}/{k}": v for k, v in hashes.items()},
        "review_path": "reviews/F2b-rev13-full-090.json",
        "review_sha256": review_sha,
        "next_falsifier": review["next_falsifier"],
        "authority_note": "worker checkpoint; no gate verdict, no node status, no canonical write",
    }
    os.makedirs(os.path.dirname(CKPT), exist_ok=True)
    with open(CKPT, "w") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)
    ckpt_sha = sha(CKPT)

    existing = set()
    if os.path.isfile(OUTBOX):
        for line in open(OUTBOX):
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    events = []

    def ev(eid, etype, **kw):
        if eid in existing:
            return
        d = {"event_id": eid, "event_type": etype, "created_at": now, "actor": "worker-090",
             "task_id": TASK, "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM"}
        d.update(kw)
        events.append(d)

    ev(f"w090-f2b13-{TASK}-task", "status", status="active",
       summary="Took ONE bounded class-bound task (no inbox card for worker-090): W090-F2B-REV13-FULL-01 = independent mechanized full-schema verification of F2b AF-SCC-C0-VAC-GEN rev13 b2ab6acb under FROZEN rev29, read-only, freeze-first pinned.",
       evidence_refs=[f"{ART}/snapshot/MANIFEST.json#{hashes['snapshot/MANIFEST.json'][:12]}"],
       hours=0.5,
       next_falsifier="See review; any pin move or blocking check flip voids the verdict.")
    for rel in ("pin_snapshot.py", "snapshot/MANIFEST.json", "check_f2b_rev13_full.py",
                "results.json", "controls.json", "README.md"):
        ev(f"w090-f2b13-{TASK}-artifact-{rel.split('/')[-1]}", "artifact",
           artifact_type="checker" if rel.endswith(".py") else "evidence",
           path=f"{ART}/{rel}", sha256=hashes[rel], validation_status="unverified",
           note="read-only verification output; worker cannot promote validation status",
           evidence_refs=[f"{ART}/{rel}#{hashes[rel][:12]}"])
    ev(f"w090-f2b13-{TASK}-artifact-review", "artifact", artifact_type="review",
       path="reviews/F2b-rev13-full-090.json", sha256=review_sha, validation_status="unverified",
       evidence_refs=[f"reviews/F2b-rev13-full-090.json#{review_sha[:12]}"])
    ev(f"w090-f2b13-{TASK}-artifact-checkpoint", "artifact", artifact_type="checkpoint_json",
       path="runtime/state/w090_f2b_rev13_full_checkpoint.json", sha256=ckpt_sha,
       validation_status="unverified",
       evidence_refs=[f"runtime/state/w090_f2b_rev13_full_checkpoint.json#{ckpt_sha[:12]}"])
    ev(f"w090-f2b13-{TASK}-review", "review", target_id="F2b", reviewer="worker-090",
       verdict="accept", score=4.0, reviewed_sha256=PINS["F2b"][1], reviewed_revision=13,
       counts_as_full_schema_verdict=True, blind=False,
       hard_failures=[], carriers=res["carriers"],
       findings=[f["id"] + ": " + f["statement"][:220] for f in findings],
       artifact_refs=review["artifact_refs"], evidence_refs=review["evidence_refs"],
       next_falsifier=review["next_falsifier"],
       authority_note="advisory worker verdict; cannot set gate verdict or node status")
    ev(f"w090-f2b13-{TASK}-claim", "claim", conclusion_type="formal_model",
       statement=("At F2b = b2ab6acb2bbe (rev13) under FROZEN rev29 815e08079aef, a 44-check mechanized, "
                  "freeze-first, read-only verification finds 0 blocking schema-local failures and 4 declared "
                  "non-blocking carriers; 8/8 pre-registered mutants are caught. Verified positives include: F0 "
                  "declared hash, consistency-evidence declaration and mirror bytes all resolve; class components "
                  "agree with F0 axes modulo registry aliases; sibling disjointness pair present and symmetric; "
                  "C0=>C2 one-way only with the converse forbidden; I+/visibility absent from operative conclusion "
                  "fields and explicitly prohibited; tier-1 falsifier decidable with genericity routes R1/R2; and "
                  "the normalized 16-key data_class core is identical between F2b and F2a (and vs F1) with identical "
                  "F2b/F2a genericity fields, satisfying the T1 guard for the licensed C0=>C2 transfer. Carriers: "
                  "W090-F2B13-01 (F0 all-list vs registry alias authority conflict; registry pointer absent), "
                  "W090-F2B13-02 (stale review_status), W090-F2B13-03 (supplement bound only transitively; evidence "
                  "embeds 0 witnesses), W090-F2B13-04 (class_separation.py second unannounced drift to e36b0d644ca7 "
                  "at 01:06:12 during the CF-26 freeze). This is a declaration/behavior measurement, not a "
                  "mathematical result; no gate or node status claimed."),
       assumptions=review["assumptions"], falsifier=review["next_falsifier"],
       evidence_refs=review["evidence_refs"], artifact_refs=review["artifact_refs"],
       non_claims=review["non_claims"])
    ev(f"w090-f2b13-{TASK}-detector-drift", "blocker",
       node_id="A1", class_id="AF-SCC-C0-VAC-GEN", gate="G-AUDIT",
       description=("research_map/class_separation.py moved again while the CF-26 detector write-freeze is in force: "
                    "a8c04fc31e4a -> e36b0d644ca7 at 2026-09-12 01:06:12, no announcing artifact/assignment event in "
                    "research_map/events.jsonl or comms/outbox. F2b is unaffected in outcome (pinned c266dbec and live "
                    "e36b0d64 both return 0 findings on the F2b text), but any detector-bound verdict must cite the "
                    "detector hash it measured."),
       needed_to_unblock=("astra-life06-classsep-detector-adjudication returns one operative decision at cited hashes; "
                          "either adopt e36b0d64 with a review or roll back, and refresh the frozen pin explicitly."),
       evidence_refs=["research_map/class_separation.py#e36b0d64", 
                      "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py#c266dbec",
                      f"{ART}/results.json#{hashes['results.json'][:12]}"])
    ev(f"w090-f2b13-{TASK}-complete", "status", status="active",
       summary=("W090-F2B-REV13-FULL-01 complete at worker level and exiting for recycling. F2b rev13 b2ab6acb: "
                "44 checks (40 pass, 0 blocking fail, 4 carriers), 8/8 mutants, pin stable, canonical files untouched. "
                "Verdict accept 4.0, advisory and NOT blind (disclosed). REC-23 context: this is one non-author full-schema "
                "accept at the rev13 pin; binding still needs the audit lead's r3 adjudication and the F2b accept count."),
       evidence_refs=[f"reviews/F2b-rev13-full-090.json#{review_sha[:12]}",
                      f"{ART}/results.json#{hashes['results.json'][:12]}",
                      f"{ART}/controls.json#{hashes['controls.json'][:12]}",
                      f"runtime/state/w090_f2b_rev13_full_checkpoint.json#{ckpt_sha[:12]}"],
       hours=0.5, next_falsifier=review["next_falsifier"],
       authority_note="advisory worker status; no gate verdict, no node status promotion")

    with open(OUTBOX, "a") as fh:
        for d in events:
            fh.write(json.dumps(d, sort_keys=True) + "\n")
    print(json.dumps({"emitted": [e["event_id"] for e in events],
                      "review_sha256": review_sha, "checkpoint_sha256": ckpt_sha,
                      "artifacts": hashes}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
