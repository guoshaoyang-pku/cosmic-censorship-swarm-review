#!/usr/bin/env python3
"""Publish W081-GFORM-F1-SUITE-MATERIALITY-01 deliverables and comms events.

Reads evidence.json (produced by measure_materiality.py), writes report.json,
README.md, checkpoint.json, a reviews/ record, a runtime/state checkpoint, and
appends this worker's JSONL events to comms/outbox/worker-081.jsonl.

All writes are worker-scoped (artifacts/worker-081, reviews/, runtime/state,
comms/outbox). No canonical artifact, map node, or gate verdict is touched.
"""

import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TASK = "W081-GFORM-F1-SUITE-MATERIALITY-01"
STAMP = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
STAMP = STAMP[:22] + ":" + STAMP[22:] if len(STAMP) == 24 and STAMP[-3] != ":" else STAMP


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def w(rel, obj):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        if isinstance(obj, str):
            fh.write(obj)
        else:
            json.dump(obj, fh, indent=1, sort_keys=True)
            fh.write("\n")
    return sha256(path)


ev = json.load(open(os.path.join(HERE, "evidence.json"), encoding="utf-8"))
ev["created_at"] = STAMP
with open(os.path.join(HERE, "evidence.json"), "w", encoding="utf-8") as fh:
    json.dump(ev, fh, indent=1, sort_keys=True)
    fh.write("\n")
H = {}
H["tool"] = sha256(os.path.join(HERE, "measure_materiality.py"))
H["evidence"] = sha256(os.path.join(HERE, "evidence.json"))

pins_full = ev["pins_start"]
pin = {k: v["measured"] for k, v in pins_full.items()}
verdict = ev["verdict"]
flips = ev["materiality"]["n_verdict_flips"]
fail = ev["suite_health_at_rev13"]
controls = ev["controls"]

report = {
    "task_id": TASK,
    "actor": "worker-081",
    "created_at": STAMP,
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": ["AF-WCC-VAC-GEN"],
    "node_id": "F1",
    "gate": "G-FORM",
    "role": "bounded read-only worker measurement and adjudication; no gate verdict, no node status, no validation_status=passed, no canonical byte written",
    "question": ev["question"],
    "verdict": verdict,
    "adjudication": {
        "binding_defect_confirmed": {
            "rows": ev["suite"]["rows"],
            "binding_sha256": ev["suite"]["bindings"],
            "binding_frozen_revision": ev["suite"]["binding_frozen_revisions"],
            "live_f1_pin": pin["f1_rev13"],
            "frozen_rev29_manifest": pin["frozen"],
            "frozen_pins_corpus_at": ev["suite"]["corpus_sha256"],
        },
        "materiality": {
            "changed_leaf_paths": ev["materiality"]["n_changed_leaf_paths"],
            "probe_verdict_flips_rev12_vs_rev13": flips,
            "conclusion": "the rev12->rev13 delta is PROBE-IMMATERIAL: identical 84-probe verdict vector on both revisions",
            "worker073_materially_affected_rows": {
                k: {"n_probes": v["n_probes"], "n_verdict_flips": v["n_verdict_flips"], "all_pass_rev13": v["all_pass_rev13"]}
                for k, v in ev["named_rows_worker073"].items()
            },
            "worker073_refinement": "F1-AMB-11/17/23 probes ARE sensitive to visibility.definition (positive control M1 moves 4 of them), but the actual rev13 edit preserved every probed token, so text-adjacency in worker-073's finding is not verdict-affecting",
        },
        "separate_gate_blocker_unfixed_by_rebind": {
            "row": "F1-AMB-25",
            "n_failing_probes": fail["n_failing_probes"],
            "failures": [
                {"kind": p["kind"], "path": p["path"], "reason": p["reason"], "expected": p["expected"]}
                for p in fail["failing_probes"]
            ],
            "note": "both expectations are stale ROW data, false at rev12 and rev13 alike; a pure F1-binding restamp does not make the suite green",
        },
        "prescriptions": [
            "Rebind the 25 rows to F1 d9cebb9404b2 + FROZEN rev29 (binding_sha256/binding_ref/binding_frozen_revision) - mechanical on the measured probe dimension; no probe-text re-derivation is required by this measurement.",
            "Alternatively record the controller immateriality adjudication worker-073 option (b) explicitly, citing this probe-invariance evidence; silence still lets the gate accept F1 on evidence predating the frozen revision.",
            "Repair F1-AMB-25's two stale expectations (declared_f0_sha256 276009f4 -> live F0 0abb9ed8; binding_note token astra-classscope-02 absent) or explicitly exclude that row from the gate evidence; otherwise the corpus is red at the live pin independent of the F1 binding.",
        ],
    },
    "measured": {
        "pins": pins_full,
        "pins_end": ev["pins_end"],
        "pin_stable": ev["pin_ok_start"] and ev["pin_ok_end"],
        "duplicate_mapping_keys": ev["duplicate_keys"],
        "calibration_reproduces_worker029": ev["engine"]["calibration_reproduces_worker029_counts"],
        "controls": controls,
        "n_rows_all_probe_pass_rev13": fail["n_rows_all_probe_pass"],
    },
    "evidence_chain": {
        "suite_corpus": "schemas/f1_falsifier_tests.jsonl#sha256:" + ev["suite"]["corpus_sha256"],
        "f1_rev12_snapshot": "artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml#sha256:" + pin["f1_rev12"],
        "f1_rev13_live": "schemas/af_wcc_vacuum.yaml#sha256:" + pin["f1_rev13"],
        "frozen_manifest": "artifacts/formulation/FROZEN.json#sha256:" + pin["frozen"],
        "f0_canonical": "research_map/formulation_taxonomy.yaml#sha256:" + pin["f0"],
    },
    "falsifier": ev["falsifier"],
    "next_falsifier": "Recompute after any suite rebind: expect 25/25 rows bound to the live F1 pin, the two F1-AMB-25 failures either repaired or excluded, and still 0 probe-verdict flips attributable to the rev12->rev13 delta. A republished F1 hash without a suite rebind reopens F1-073-01.",
    "artifacts": {
        "tool": "artifacts/worker-081/f1_suite_materiality/measure_materiality.py#sha256:" + H["tool"],
        "evidence": "artifacts/worker-081/f1_suite_materiality/evidence.json#sha256:" + H["evidence"],
    },
    "not_claimed": ev["not_claimed"],
}
H["report"] = w("artifacts/worker-081/f1_suite_materiality/report.json", report)

readme = """# W081-GFORM-F1-SUITE-MATERIALITY-01

**Worker:** worker-081 · **Class:** `AF-WCC-VAC-GEN` · **Node:** F1 · **Gate:** G-FORM · **Created:** {stamp}

## Task taken

F1's falsifier suite (`schemas/f1_falsifier_tests.jsonl`, 25 rows / 84 probes) binds the
**superseded** F1 rev12 hash `cce9c60146d6…` while the live canonical F1 schema is rev13
`d9cebb9404b2…` (FROZEN rev29 `815e08079aef…`). `worker-073` filed this as blocking hard
failure `F1-073-01` and prescribed either a rebind **or** "an explicit controller adjudication
that the declared semantics-preserving rev13 delta is immaterial for those probes".
`worker-029` measured the binding and probe mismatch counts. Nobody had enumerated the changed
leaves and tested whether the delta can move a probe verdict, with a positive control proving the
test is not vacuous. This card does exactly that, read-only.

## Result — `{verdict}`

| measurement | value |
|---|---|
| pins stable start→end | {pins} |
| rows / probes | 25 / 84 |
| binding | 25/25 rows `cce9c60146d6…`, `binding_frozen_revision=27` |
| changed leaf paths rev12→rev13 | {nchanged} |
| **probe verdict flips rev12→rev13** | **{flips}** |
| stored-vs-recomputed mismatches | {mm} at rev12, {mm} at rev13 (same set) |
| failing probes at rev13 | {nfail} — all in `F1-AMB-25` |
| rows all-probe-pass at rev13 | {npass}/25 |
| duplicate YAML mapping keys | 0 in both revisions |

**Adjudication.** (1) The stale binding is confirmed. (2) The rev12→rev13 delta is
**probe-immaterial**: all 12 changed leaves are either unreferenced by probes (8) or touched by
probes whose probed tokens survive the edit (4: `visibility.definition`,
`class_identity_variants[0].relation`, `f0_binding.binding_note`, and metadata); the 84-probe
verdict vector is identical at both revisions. So a pure binding restamp needs no probe-text
re-derivation, and worker-073's option (b) adjudication is defensible on this dimension.
(3) worker-073's three "materially affected" rows `F1-AMB-11/17/23` are **text-adjacent, not
verdict-affected**: their probes are sensitive to `visibility.definition` (control M1 moves 4 of
them), but the actual rev13 edit preserved every probed token, so 0/11 of their probes flip.
(4) **Separate blocker not fixed by any rebind:** `F1-AMB-25` carries two stale row expectations
that are false at *both* revisions — `declared_f0_sha256` expects `276009f4…` while the schema
declares the live F0 `0abb9ed8…`, and `binding_note` is expected to contain `astra-classscope-02`
which occurs nowhere in either revision. The suite is therefore **not green at the live pin**,
and a rebind alone does not make it green.

## Controls (anti-vacuity)

| control | mutation | probes moved |
|---|---|---|
| M1 positive | blank `visibility.definition` | {m1} (F1-AMB-11/17/23) |
| M2 positive | restore F1-AMB-25 expected F0 hash | {m2} (fail→pass) |
| M3 positive | delete `non_vacuity.condition` | {m3} |
| M4 specificity | mutate unreferenced `authored_by` | {m4} (required) |

M1–M3 prove the engine detects change; M4 proves it does not fire on unreferenced leaves.
Reproduce: `python3 artifacts/worker-081/f1_suite_materiality/measure_materiality.py`
(verdict `STALE_BINDING_PROBE_IMMATERIAL`, exit 0; exit 3 = pin drift).

## Prescriptions (worker-level, advisory)

1. Rebind the 25 rows to F1 `d9cebb9404b2` + FROZEN rev29 — mechanical on the measured dimension.
2. Or record the controller immateriality adjudication explicitly, citing this invariance evidence.
3. Repair `F1-AMB-25`'s two stale expectations or explicitly exclude that row from gate evidence.

## Falsifier

Re-run in an unchanged tree: any probe whose rev12 vs rev13 verdict differs; any pin measured
≠ recorded; a positive control moving 0 probes; the specificity control moving >0 probes; or a
changed-leaf count other than 12 falsifies this report.

**Authority:** no gate verdict, no node status, no `validation_status=passed`, no canonical byte
written. Evidence: `evidence.json#sha256:{eh}`, tool `measure_materiality.py#sha256:{th}`,
report `report.json#sha256:{rh}`.
""".format(
    stamp=STAMP,
    verdict=verdict,
    pins="yes (6/6)" if (ev["pin_ok_start"] and ev["pin_ok_end"]) else "NO — VOID",
    nchanged=ev["materiality"]["n_changed_leaf_paths"],
    flips=flips,
    mm=ev["engine"]["n_stored_mismatch_rev12"],
    nfail=fail["n_failing_probes"],
    npass=fail["n_rows_all_probe_pass"],
    m1=controls[0]["probes_moved"],
    m2=controls[1]["probes_moved"],
    m3=controls[2]["probes_moved"],
    m4=controls[3]["probes_moved"],
    eh=H["evidence"][:12],
    th=H["tool"][:12],
    rh=H["report"][:12],
)
H["readme"] = w("artifacts/worker-081/f1_suite_materiality/README.md", readme)

checkpoint = {
    "task_id": TASK,
    "actor": "worker-081",
    "label": "worker-081-f1-suite-materiality",
    "created_at": STAMP,
    "gate": "G-FORM",
    "node_ids": ["F1"],
    "class_ids": ["AF-WCC-VAC-GEN"],
    "verdict": verdict,
    "key_counts": {
        "rows": ev["suite"]["rows"],
        "probes": ev["suite"]["probes"],
        "changed_leaf_paths": ev["materiality"]["n_changed_leaf_paths"],
        "probe_verdict_flips": flips,
        "failing_probes_rev13": fail["n_failing_probes"],
    },
    "input_snapshot_sha256": pin,
    "artifacts": {
        "tool": {"path": "artifacts/worker-081/f1_suite_materiality/measure_materiality.py", "sha256": H["tool"]},
        "evidence": {"path": "artifacts/worker-081/f1_suite_materiality/evidence.json", "sha256": H["evidence"]},
        "report": {"path": "artifacts/worker-081/f1_suite_materiality/report.json", "sha256": H["report"]},
        "readme": {"path": "artifacts/worker-081/f1_suite_materiality/README.md", "sha256": H["readme"]},
    },
    "falsifier": ev["falsifier"],
    "not_claimed": ev["not_claimed"],
}
H["checkpoint"] = w("artifacts/worker-081/f1_suite_materiality/checkpoint.json", checkpoint)

review = {
    "review_id": "W081-F1-SUITE-MATERIALITY-REVIEW",
    "task_id": TASK,
    "reviewer": "worker-081",
    "actor": "worker-081",
    "created_at": STAMP,
    "target_id": "reviews/F1-review-worker-073-rev29.json#F1-073-01",
    "node_id": "F1",
    "class_id": "AF-WCC-VAC-GEN",
    "gate": "G-FORM",
    "verdict": "revise",
    "score": 4.0,
    "counts_as_full_schema_verdict": False,
    "findings": [
        "Binding defect F1-073-01 independently reproduced: 25/25 rows bind F1 rev12 cce9c60146d6, binding_frozen_revision=27, live pin d9cebb9404b2 (FROZEN rev29 815e08079aef).",
        "Materiality measured: 12 changed leaves rev12->rev13, 0/84 probe verdict flips; the delta is probe-immaterial. A pure binding restamp requires no probe-text re-derivation.",
        "worker-073 materially_affected_rows F1-AMB-11/17/23 refined: text-adjacent, not verdict-affected (0 flips; all their probes pass at rev13; control M1 shows they are sensitive to visibility.definition).",
        "Additional blocker: F1-AMB-25 has 2 stale expectations failing at BOTH revisions (declared_f0_sha256 expects 276009f4 vs live F0 0abb9ed8; binding_note lacks token astra-classscope-02). Rebind alone does not make the suite green.",
    ],
    "hard_failures": [
        {"id": "W081-HF-01", "label": "F1 suite binds superseded rev12; not repaired by this measurement (owner action)",
         "falsifier": "25/25 rows rebound to d9cebb9404b2 with FROZEN rev29, or controller immateriality adjudication recorded."},
        {"id": "W081-HF-02", "label": "F1-AMB-25 two stale expectations fail at the live pin independent of the binding",
         "falsifier": "F1-AMB-25 expectations repaired to pass at live F0/schema, or the row excluded from gate evidence."},
    ],
    "evidence_refs": [
        "artifacts/worker-081/f1_suite_materiality/report.json#sha256:" + H["report"][:12],
        "artifacts/worker-081/f1_suite_materiality/evidence.json#sha256:" + H["evidence"][:12],
        "schemas/f1_falsifier_tests.jsonl#sha256:" + ev["suite"]["corpus_sha256"][:12],
        "schemas/af_wcc_vacuum.yaml#sha256:" + pin["f1_rev13"][:12],
    ],
    "falsifier": ev["falsifier"],
    "next_falsifier": report["next_falsifier"],
    "authority_note": "advisory measurement only; no gate verdict or node status",
}
H["review"] = w("reviews/F1-suite-materiality-worker-081.json", review)
H["state_checkpoint"] = w("runtime/state/worker-081_checkpoint_f1suite.json", checkpoint)

events = []


def ev_id(suffix):
    return "w081-f1suite-" + STAMP.replace(":", "").replace("-", "").replace("+", "") + "-" + suffix


base = {"actor": "worker-081", "created_at": STAMP, "node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN"], "gate": "G-FORM", "task_id": TASK}

e = dict(base, event_id=ev_id("status-active"), event_type="status", status="active", hours=0.4,
         summary="W081 F1 suite stale-binding materiality adjudication started; read-only, 6 pins recorded.",
         evidence_refs=["artifacts/worker-081/f1_suite_materiality/evidence.json#sha256:" + H["evidence"][:12]],
         next_falsifier=ev["falsifier"])
events.append(e)

for name, atype, path, h, note in [
    ("tool", "analysis_tool", "artifacts/worker-081/f1_suite_materiality/measure_materiality.py", H["tool"], "independent probe engine + leaf diff + 4 mutation controls"),
    ("evidence", "evidence", "artifacts/worker-081/f1_suite_materiality/evidence.json", H["evidence"], "full 84-probe measurement at rev12 and rev13, pins, controls"),
    ("report", "report", "artifacts/worker-081/f1_suite_materiality/report.json", H["report"], "verdict STALE_BINDING_PROBE_IMMATERIAL + prescriptions"),
    ("readme", "report", "artifacts/worker-081/f1_suite_materiality/README.md", H["readme"], "human-readable summary"),
    ("checkpoint", "checkpoint", "artifacts/worker-081/f1_suite_materiality/checkpoint.json", H["checkpoint"], "artifact-level checkpoint"),
    ("review", "review_record", "reviews/F1-suite-materiality-worker-081.json", H["review"], "advisory review of F1-073-01 with materiality refinement"),
    ("state_checkpoint", "checkpoint", "runtime/state/worker-081_checkpoint_f1suite.json", H["state_checkpoint"], "conventional runtime/state checkpoint"),
]:
    e = dict(base, event_id=ev_id("artifact-" + name), event_type="artifact", artifact_type=atype,
             path=path, sha256=h, validation_status="unverified",
             evidence_refs=["artifacts/worker-081/f1_suite_materiality/report.json#sha256:" + H["report"][:12]],
             note=note)
    events.append(e)

e = dict(base, event_id=ev_id("claim"), event_type="claim", conclusion_type="numerical_evidence",
         statement="W081-GFORM-F1-SUITE-MATERIALITY-01: The F1 falsifier suite binds superseded F1 rev12 cce9c60146d6 (25/25 rows, binding_frozen_revision=27) while live F1 is rev13 d9cebb9404b2. The rev12->rev13 delta is probe-immaterial: 12 changed leaf paths produce 0/84 probe verdict flips (controls M1-M3 move 1-4 probes, M4 moves 0). Independently, F1-AMB-25 has 2 stale expectations failing at both revisions, so a pure binding rebind does not make the suite green.",
         assumptions=["schemas/f1_falsifier_tests.jsonl is the frozen gate-evidence corpus (FROZEN rev29 56bcb4b3234b)",
                      "the rev12 snapshot artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml is byte-faithful to the bound revision",
                      "6/6 pins stable start->end; no duplicate YAML mapping keys in either revision"],
         falsifier=ev["falsifier"],
         evidence_refs=["artifacts/worker-081/f1_suite_materiality/evidence.json#sha256:" + H["evidence"][:12],
                        "schemas/f1_falsifier_tests.jsonl#sha256:" + ev["suite"]["corpus_sha256"][:12],
                        "schemas/af_wcc_vacuum.yaml#sha256:" + pin["f1_rev13"][:12],
                        "artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml#sha256:" + pin["f1_rev12"][:12]],
         artifact_refs=["artifacts/worker-081/f1_suite_materiality/report.json#sha256:" + H["report"][:12],
                        "artifacts/worker-081/f1_suite_materiality/evidence.json#sha256:" + H["evidence"][:12]],
         next_falsifier=report["next_falsifier"])
events.append(e)

e = dict(base, event_id=ev_id("review"), event_type="review",
         target_id="reviews/F1-review-worker-073-rev29.json#F1-073-01",
         reviewer="worker-081", verdict="revise", score=4.0,
         hard_failures=["W081-HF-01 F1 suite binds superseded rev12 (rebind or adjudication outstanding)",
                        "W081-HF-02 F1-AMB-25 two stale expectations fail at the live pin independent of the binding"],
         findings="Materiality adjudication: 0/84 probe flips rev12->rev13; worker-073 rows F1-AMB-11/17/23 are text-adjacent not verdict-affected; F1-AMB-25 remains red at both revisions. See report.json.",
         evidence_refs=["reviews/F1-suite-materiality-worker-081.json#sha256:" + H["review"][:12],
                        "artifacts/worker-081/f1_suite_materiality/report.json#sha256:" + H["report"][:12]])
events.append(e)

e = dict(base, event_id=ev_id("status-done"), event_type="status", status="done", hours=0.4,
         summary="W081 complete: F1 suite stale binding confirmed, delta probe-immaterial (0/84 flips) with 4 controls, and a separate F1-AMB-25 two-probe failure left red at the live pin. Artifacts hash-pinned; no canonical write.",
         evidence_refs=["artifacts/worker-081/f1_suite_materiality/report.json#sha256:" + H["report"][:12],
                        "artifacts/worker-081/f1_suite_materiality/checkpoint.json#sha256:" + H["checkpoint"][:12],
                        "runtime/state/worker-081_checkpoint_f1suite.json#sha256:" + H["state_checkpoint"][:12]],
         next_falsifier=report["next_falsifier"], artifact="artifacts/worker-081/f1_suite_materiality/report.json")
events.append(e)

outbox = os.path.join(ROOT, "comms/outbox/worker-081.jsonl")
with open(outbox, "a", encoding="utf-8") as fh:
    for e in events:
        fh.write(json.dumps(e, sort_keys=True) + "\n")

print(json.dumps({"verdict": verdict, "hashes": {k: v[:12] for k, v in H.items()}, "events": len(events)}, indent=1))
print("outbox:", outbox)
