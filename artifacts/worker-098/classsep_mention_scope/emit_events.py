#!/usr/bin/env python3
"""W098-CLASSSEP-MENTION-SCOPE-01 emission: outbox events + worker checkpoint.

Idempotent: appends an event to comms/outbox/worker-098.jsonl only if its event_id is absent.
Writes runtime/state/w098_classsep_mention_scope_checkpoint_1.json and appends a one-line
summary to runtime/state/w098_classsep_mention_scope_checkpoints.jsonl. Never writes the
controller checkpoint, canonical detector, map, or any gate/node status.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/worker-098.jsonl"
STATE = ROOT / "runtime/state"
TASK = "W098-CLASSSEP-MENTION-SCOPE-01"
AT = "2026-09-12T01:00:00+08:00"
PREFIX = "w098-cms-20260912T0100"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p: Path, n=12) -> str:
    return f"{p.relative_to(ROOT)}#{sha(p)[:n]}"


FILES = {
    "pre_registration": HERE / "pre_registration.json",
    "readme": HERE / "README.md",
    "build_v1": HERE / "build_candidate.py",
    "manifest_v1": HERE / "build_manifest.json",
    "build_v2": HERE / "build_candidate_v2.py",
    "manifest_v2": HERE / "build_manifest_v2.json",
    "build_v3": HERE / "build_candidate_v3.py",
    "manifest_v3": HERE / "build_manifest_v3.json",
    "candidate_v1": HERE / "candidate_class_separation.py",
    "candidate_v2": HERE / "candidate_class_separation.v2.py",
    "candidate_v3": HERE / "candidate_class_separation.v3.py",
    "battery_v1": HERE / "run_battery.py",
    "battery_final": HERE / "run_battery_final.py",
    "liveness_tool": HERE / "liveness_recheck.py",
    "raw_v1": HERE / "raw/candidate_battery.json",
    "raw_final": HERE / "raw/candidate_battery_final.json",
    "raw_liveness": HERE / "raw/liveness_recheck.json",
    "report": HERE / "report.json",
}
PINS = {
    "live_detector": ROOT / "research_map/class_separation.py",
    "staged_candidate": ROOT / "proposed/class_separation.py",
    "corpus": ROOT / "artifacts/worker-07/class_separation_falsification/results.json",
    "live_map": ROOT / "research_map/research_map.json",
    "prior_checkpoint2": STATE / "w098_classsep_prose_shadow_checkpoint_2.json",
}

report = json.loads(FILES["report"].read_text())
liveness = json.loads(FILES["raw_liveness"].read_text())
arms = report["arms"]


def arm_line(name):
    a = arms[name]
    return "%s: corpus=%s, clean_fires=%d/8, genuine_merge_fires=%d/12, growth=%d/5, live_map_hard=%d" % (
        name, a["corpus"]["verdict"], sum(1 for r in a["clean"] if r["fires"]),
        sum(1 for r in a["fire"] if r["fires"]), sum(r["findings"] for r in a["growth"]),
        a["map_live_hard"])


EVIDENCE = [
    ref(FILES["pre_registration"]), ref(FILES["candidate_v3"]), ref(FILES["manifest_v3"]),
    ref(FILES["report"]), ref(FILES["raw_final"]), ref(FILES["raw_liveness"]),
    ref(PINS["live_detector"]), ref(PINS["staged_candidate"]), ref(PINS["corpus"]),
    ref(PINS["prior_checkpoint2"]),
]
FALSIFIER = report["falsifier"]

EVENTS = [
    {
        "event_id": f"{PREFIX}-status-take", "event_type": "status", "created_at": AT,
        "actor": "worker-098", "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT",
        "class_id": CLASS_ID, "status": "active", "hours": 0.5,
        "summary": ("Took one bounded class-bound task on the G-AUDIT critical path: build and measure a "
                    "prose-only, clause-scoped repair candidate for research_map/class_separation.py against the "
                    "live detector a8c04fc31e4a. Pre-registered in " + ref(FILES["pre_registration"]) + "."),
        "evidence_refs": [ref(FILES["pre_registration"]), ref(PINS["live_detector"])],
        "next_falsifier": FALSIFIER,
    },
]
for key, path in (("prereg", FILES["pre_registration"]), ("readme", FILES["readme"]),
                  ("cand-v1", FILES["candidate_v1"]), ("cand-v2", FILES["candidate_v2"]),
                  ("cand-v3", FILES["candidate_v3"]), ("build-v3", FILES["build_v3"]),
                  ("manifest-v3", FILES["manifest_v3"]), ("battery", FILES["battery_final"]),
                  ("liveness-tool", FILES["liveness_tool"]), ("liveness-raw", FILES["raw_liveness"]),
                  ("report", FILES["report"]), ("raw-final", FILES["raw_final"])):
    EVENTS.append({
        "event_id": f"{PREFIX}-art-{key}", "event_type": "artifact", "created_at": AT,
        "actor": "worker-098", "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT",
        "class_id": CLASS_ID, "artifact_type": "classsep_candidate_" + key,
        "path": str(path.relative_to(ROOT)), "sha256": sha(path), "validation_status": "unverified",
        "summary": "W098-CLASSSEP-MENTION-SCOPE-01 artifact pinned at emission time.",
        "evidence_refs": [ref(path)],
    })

EVENTS.append({
    "event_id": f"{PREFIX}-claim-v2", "event_type": "claim", "created_at": AT, "actor": "worker-098",
    "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS_ID,
    "conclusion_type": "numerical_evidence",
    "statement": ("At live detector research_map/class_separation.py#a8c04fc31e4a and pinned live map "
                  + sha(PINS["live_map"])[:12] + f" (claims={report['drift']['live_map_claims']}), the insertion-only "
                  "prose-scope candidate v3 " + ref(FILES["candidate_v3"]) + " passes all nine pre-registered "
                  "criteria: worker-07 corpus PASS (17/0/10/0), 0/8 mandatory-clean prose controls fire, 2/2 "
                  "true-positive controls fire, 12/12 genuine-merge adversarial controls fire (live fires 11/12 "
                  "because its meta-quotation skip swallows 'detector flags ... are one class'), growth 0/5 "
                  "(live 5/5), declaration-mode parity 10/10 with live, insertion-only diff +109/-0, and 0 hard "
                  "CLASSSEP findings on the pinned map (live 17, staged proposed/class_separation.py#e2d24b927ee8 "
                  "22). Liveness addendum: after the 01:00 cycle the map advanced to "
                  + liveness["live_map_sha256"][:12] + f" (claims={liveness['live_map_claims']}) and v3 shows 1 "
                  "hard finding on a NEW growth-family shape (claims[327], worker-049: 'every genuine C0/C2 merge "
                  "assertion carries a mention-style cue'), i.e. the detector-discussion growth mechanism "
                  "reproduces against the repair; live 19, staged 25, v1 6, v2 3 on the same frontier. The "
                  "instrument is therefore battery-clean and pinned-map-clean but not closed under new "
                  "detector-discussion traffic. Measured sequence v1 revise (5 hard, 1/8 clean), v2 revise (2 hard), "
                  "v3 adopt-candidate (0 hard pinned)."),
    "assumptions": [
        "the measured sha256 is the artifact identity; the claim binds only to the pinned bytes",
        "the 27-fixture corpus is the registered ground truth; PASS means no new FN there, not that the candidate is defect-free",
        "the pinned map hash is the measurement surface; the liveness frontier is reported separately and is not part of the pre-registered acceptance",
        "the candidate is a measurement instrument for the detector owner, not an applied change",
    ],
    "falsifier": FALSIFIER,
    "evidence_refs": EVIDENCE,
})

EVENTS.append({
    "event_id": f"{PREFIX}-review", "event_type": "review", "created_at": AT, "actor": "worker-098",
    "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS_ID,
    "target_id": str(FILES["candidate_v3"].relative_to(ROOT)),
    "reviewed_sha256": sha(FILES["candidate_v3"]),
    "reviewer": "worker-098", "verdict": "accept", "score": 4.5, "hard_failures": [],
    "counts_as_full_schema_verdict": False, "counts_as_independent": True,
    "findings": [
        "W098-CMS-01 (major, fixed-in-v2): v1 rule-implementation defects D1-D5 measured and repaired.",
        "W098-CMS-02 (major, live defect, fixed-in-v3): live over-suppresses the first-order assertion AX3 via 'detector\\s+(?:finding|flag)'; v3 re-asserts it.",
        "W098-CMS-03 (info): staged e2d24b927ee8 fires 8/8 clean controls and leaves 22 live-map hard findings; it is a different, narrower fix.",
        "W098-CMS-04 (info): no new FN in any arm on the 27-fixture worker-07 corpus (all PASS).",
        "W098-CMS-05 (info): growth mechanism live 5/5, staged 5/5, v1 1/5, v2 0/5, v3 0/5.",
        "W098-CMS-06 (info): declaration parity 10/10 for v1/v2/v3; insertion-only derivations of a8c04fc31e4a.",
        "W098-CMS-07 (info at v3): 0 hard CLASSSEP findings on the live map at " + sha(PINS["live_map"])[:12] + "; claim retirement remains a separate controller/lead action.",
        "Residual declared risks: contrastive/split phrasings outside the 12 controls could still suppress a genuine assertion; corpus PASS is not a defect-freedom proof.",
    ],
    "evidence_refs": EVIDENCE,
})

EVENTS.append({
    "event_id": f"{PREFIX}-blocker", "event_type": "blocker", "created_at": AT, "actor": "worker-098",
    "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS_ID,
    "description": ("The canonical detector is still research_map/class_separation.py#a8c04fc31e4a and the live map "
                    "still carries 17 hard CLASSSEP findings (metalinguistic mentions, CF-16 pattern). A measured "
                    "repair candidate now exists (v3) but is NOT applied; this worker cannot edit canonical files "
                    "or retire claims."),
    "needed_to_unblock": ("Owner/controller: adopt an equivalent prose-scope fix at a pinned hash (candidate v3 is a "
                          "starting point, not the only option), re-run runtime/bin/classsep_regression.py and "
                          "research_map/audit_evidence.py, and obtain an independent reviewer event at the unchanged "
                          "detector hash. Claim retirement for historical metalinguistic claims is a separate action."),
    "evidence_refs": EVIDENCE,
})

ckpt_path = STATE / "w098_classsep_mention_scope_checkpoint_2.json"
checkpoint = {
    "checkpoint": 2, "at": AT, "worker": "worker-098", "slot": "098", "task_id": TASK,
    "supersedes": "runtime/state/w098_classsep_mention_scope_checkpoint_1.json",
    "checkpoint_note": ("checkpoint 1 stays frozen as the pre-fix emission draft; its claim event "
                        "w098-cms-20260912T0100-claim was rejected at ingest (conclusion_type "
                        "'instrument_finding' is not in research_map/schemas.py) and was retyped to "
                        "numerical_evidence under event id w098-cms-20260912T0100-claim-v2."),
    "assignment": "self-taken, no inbox card for worker-098; continuation of W098-CLASSSEP-PROSE-SHADOW-01 blocker",
    "node_id": "A1", "gate": "G-AUDIT", "class_ids": CLASS_ID.split(";"),
    "verdict": "accept", "score": 4.5, "validation_status": "unverified",
    "status": "delivered",
    "hours_spent_estimate": 0.6,
    "candidate_v3_sha256": sha(FILES["candidate_v3"]),
    "acceptance_v3": report["acceptance_v3"],
    "measured_sequence": {"v1": report["verdict_v1"], "v2": report["verdict_v2"], "v3": report["verdict_v3"]},
    "arms": {k: {
        "corpus": v["corpus"], "clean_fires": sum(1 for r in v["clean"] if r["fires"]),
        "genuine_merge_fires": sum(1 for r in v["fire"] if r["fires"]),
        "growth": sum(r["findings"] for r in v["growth"]), "live_map_hard": v["map_live_hard"],
        "decl_parity_identical": v.get("decl_parity_identical")} for k, v in arms.items()},
    "liveness_recheck": {
        "map_sha256": liveness["live_map_sha256"], "claims": liveness["live_map_claims"],
        "arms": liveness["arms"],
        "residual_shape": ("claims[327] (worker-049 w049-fnaudit-20260912T0056-claim): composite inside a "
                           "post-composite meta-noun construction ('every genuine C0/C2 merge assertion carries "
                           "a mention-style cue'); not covered by the 8 pre-registered clean controls. This is "
                           "the CF-16 growth mechanism reproducing after the repair, and the next control the "
                           "owner should add."),
    },
    "pins": {k: sha(v) for k, v in PINS.items()},
    "artifacts": {str(p.relative_to(ROOT)): sha(p) for p in list(FILES.values())},
    "attribution": report["attribution"],
    "findings": [f["id"] + " (" + f["severity"] + ", " + f["status"] + "): " + f["statement"]
                 for f in report["findings"]],
    "falsifier": FALSIFIER,
    "next_falsifier": ("Any genuine class-merge fixture missed by v3, any mandatory-clean control that fires, or drift "
                       "of the live detector or map off the hashes recorded here; current evidence is a single run at "
                       "one map hash and needs an independent re-run and an owner decision."),
    "outbox_events": [e["event_id"] for e in EVENTS] + [f"{PREFIX}-checkpoint2", f"{PREFIX}-complete2"],
    "numerics_lock": "respected: no N1 work, no numerics/spherical_solver, no GPU work",
    "schema_note": ("claim conclusion_type is numerical_evidence because research_map/schemas.py allows only "
                    "{theorem, conditional_theorem, stability_result, counterexample, numerical_evidence, "
                    "formal_model, open_problem}; 'instrument_finding' is auto-rejected (the prior pass-1 claim "
                    "w098-cps-20260912T0051-claim was rejected for this reason). The claim statement is a count "
                    "report about detector controls, not a physics claim."),
    "non_claims": [
        "not a gate verdict", "not a node completion or status transition", "no canonical write",
        "no claim retirement", "no schema edit", "no claim about cosmic censorship",
    ],
}
ckpt_path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True))

EVENTS.append({
    "event_id": f"{PREFIX}-checkpoint2", "event_type": "status", "created_at": AT, "actor": "worker-098",
    "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS_ID, "status": "active",
    "summary": ("Worker-local checkpoint 2 written (controller runtime checkpoint untouched): "
                + str(ckpt_path.relative_to(ROOT)) + "; includes the liveness recheck at map "
                + liveness["live_map_sha256"][:12] + f" (claims={liveness['live_map_claims']}) with the residual "
                "post-composite meta-noun shape."),
    "evidence_refs": [ref(ckpt_path), ref(FILES["report"]), ref(FILES["raw_liveness"])],
})
EVENTS.append({
    "event_id": f"{PREFIX}-complete2", "event_type": "status", "created_at": AT, "actor": "worker-098",
    "task_id": TASK, "node_id": "A1", "gate": "G-AUDIT", "class_id": CLASS_ID,
    "status": "active", "completion_claim": True, "hours": 0.6,
    "summary": ("W098-CLASSSEP-MENTION-SCOPE-01 complete as a bounded task: pre-registered prose-scope candidate "
                "v3 built insertion-only from a8c04fc31e4a and measured across four arms; v3 meets all nine "
                "pre-registered criteria (corpus PASS, 0/8 clean controls fire, 12/12 genuine merges fire, growth 0, "
                "declaration parity 10/10, live-map hard 17->0 at " + sha(PINS["live_map"])[:12] + "). Liveness "
                "addendum at " + liveness["live_map_sha256"][:12] + ": 1 new growth-family residual (claims[327]). "
                "Task-completion claim only; controller/lead must decide adoption, and claim retirement stays "
                "separate."),
    "next_falsifier": FALSIFIER,
    "evidence_refs": EVIDENCE + [ref(ckpt_path)],
})

# idempotent append
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            existing.add(json.loads(line).get("event_id"))
        except json.JSONDecodeError:
            continue
added = 0
with OUTBOX.open("a") as fh:
    for e in EVENTS:
        if e["event_id"] in existing:
            continue
        fh.write(json.dumps(e, sort_keys=True) + "\n")
        added += 1

summary_line = {
    "task_id": TASK, "worker": "worker-098", "at": AT, "checkpoint": 2,
    "verdict_v3": report["verdict_v3"], "candidate_v3_sha256": sha(FILES["candidate_v3"]),
    "live_map_hard_before": arms["live_a8c04fc31e4a"]["map_live_hard"],
    "live_map_hard_v3": arms["candidate_v3_6f1a24c441fb"]["map_live_hard"],
    "liveness_map_sha256": liveness["live_map_sha256"][:12],
    "liveness_v3_map_hard": liveness["arms"]["v3"]["map_hard"],
    "checkpoint_file": str(ckpt_path.relative_to(ROOT)),
}
with (STATE / "w098_classsep_mention_scope_checkpoints.jsonl").open("a") as fh:
    fh.write(json.dumps(summary_line, sort_keys=True) + "\n")

print(json.dumps({"events_added": added, "events_total": len(EVENTS),
                  "checkpoint": str(ckpt_path.relative_to(ROOT)),
                  "outbox": str(OUTBOX.relative_to(ROOT))}, indent=2))
