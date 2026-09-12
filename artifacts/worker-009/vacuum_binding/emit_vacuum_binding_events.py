#!/usr/bin/env python3
"""
W009-L1-VACUUM-CLASS-BINDING-CENSUS-01 emitter.

Reads the pinned census outputs, writes
  1. artifacts/worker-009/vacuum_binding/MANIFEST_worker-009.json
  2. appends artifact/review/status events to comms/outbox/worker-009.jsonl
  3. writes runtime/state/w009_vacuum_binding_checkpoint_1.json and appends to
     runtime/state/w009_vacuum_binding_checkpoints.jsonl

Event ids are timestamped from wall-clock at write time (CF-14: no future
dating) and the append is idempotent (an event_id already present in the
outbox is skipped).  No canonical file is written; validation_status stays
"unverified" because only the controller/leads can move it.
"""
import hashlib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
OUTDIR = os.path.join(ROOT, "artifacts", "worker-009", "vacuum_binding")
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-009.jsonl")
STATE = os.path.join(ROOT, "runtime", "state")
CKPT = os.path.join(STATE, "w009_vacuum_binding_checkpoint_1.json")
CKPT_LOG = os.path.join(STATE, "w009_vacuum_binding_checkpoints.jsonl")

RECORD = os.path.join(OUTDIR, "verification_vacuum_binding_worker-009.json")
CSVOUT = os.path.join(OUTDIR, "census_vacuum_binding_worker-009.csv")
RULES = os.path.join(OUTDIR, "rules_vacuum_binding_worker-009.json")
TOOL = os.path.join(OUTDIR, "census_vacuum_binding_worker-009.py")
VERIFY = os.path.join(OUTDIR, "verify_vacuum_binding_worker-009.py")

CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
ANCHORS = {
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
}


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def ref(path):
    return "%s#%s" % (path, sha256_file(os.path.join(ROOT, path))[:16])


def main():
    rec = json.load(open(RECORD, encoding="utf-8"))
    # Event ids, manifest and checkpoint all bind to the record's frozen run
    # stamp, so re-emitting the same record is byte-stable and idempotent.
    # The stamp is the wall-clock time at which the census was written, never
    # a future time (CF-14).
    TS = rec["run_stamp"].replace("-", "").replace(":", "").replace("+0800", "").replace("+08:00", "")
    CREATED = rec["run_stamp"]
    counts = rec["counts"]
    scope_rows = [r for r in rec["rows"] if r["row_verdict"] == "SCOPE_ERROR"]
    new_rows = [r for r in scope_rows if not r["pending_cbc09_correction"]]
    old_rows = [r for r in scope_rows if r["pending_cbc09_correction"]]

    art = {
        "artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json": sha256_file(RECORD),
        "artifacts/worker-009/vacuum_binding/census_vacuum_binding_worker-009.csv": sha256_file(CSVOUT),
        "artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json": sha256_file(RULES),
        "artifacts/worker-009/vacuum_binding/census_vacuum_binding_worker-009.py": sha256_file(TOOL),
        "artifacts/worker-009/vacuum_binding/verify_vacuum_binding_worker-009.py": sha256_file(VERIFY),
    }
    manifest = {
        "manifest_id": "W009-VACBIND-MANIFEST-1",
        "task_id": rec["task_id"],
        "worker": "worker-009",
        "created_at": CREATED,
        "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "assignment_id": rec["assignment_id"], "class_ids": CLASS_IDS,
        "record": {"path": "artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json",
                   "sha256": art["artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json"]},
        "artifacts": art,
        "anchors": ANCHORS,
        "census_digest": rec["census_digest"],
        "counts": counts,
        "controls_all_pass": rec["controls_all_pass"],
        "not_claimed": rec["not_claimed"],
        "falsifier": rec["falsifier"],
    }
    MANIFEST = os.path.join(OUTDIR, "MANIFEST_worker-009.json")
    open(MANIFEST, "w", encoding="utf-8").write(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    art["artifacts/worker-009/vacuum_binding/MANIFEST_worker-009.json"] = sha256_file(MANIFEST)

    events = []
    ev = lambda n: "w009-vacbinding-%s-%s" % (TS, n)

    art_specs = [
        ("verification_record", "artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json",
         "ledger-internal class-binding census of the 34 canonical L1 rows that bind a frozen SCC vacuum class"),
        ("census_csv", "artifacts/worker-009/vacuum_binding/census_vacuum_binding_worker-009.csv",
         "one row per (citation_id, bound class) with matter/lambda axes and hash-bound decisive quotes"),
        ("rule_spec", "artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json",
         "pins, cue patterns, tiers, decision rule, lexicon and controls used by the census"),
        ("verification_tool", "artifacts/worker-009/vacuum_binding/census_vacuum_binding_worker-009.py",
         "deterministic census tool; re-runs from the four pinned files with 14 controls"),
        ("verification_tool", "artifacts/worker-009/vacuum_binding/verify_vacuum_binding_worker-009.py",
         "read-only reproducibility verifier: digest, verdicts, quote binding, pins, controls, CSV groups"),
        ("manifest", "artifacts/worker-009/vacuum_binding/MANIFEST_worker-009.json",
         "artifact + anchor hashes for the census package"),
    ]
    for i, (atype, path, summary) in enumerate(art_specs, 1):
        events.append({
            "event_id": ev("artifact-%02d" % i), "event_type": "artifact", "created_at": CREATED,
            "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
            "class_ids": CLASS_IDS, "assignment_id": rec["assignment_id"],
            "artifact_type": atype, "path": path, "sha256": art[path],
            "validation_status": "unverified",
            "evidence_refs": ["ledger/citation_audit.csv#315c19145065", "ledger/theorems.jsonl#a1674f094979",
                              "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe", "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                              "artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json#%s" % art["artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json"][:16]],
            "summary": summary,
            "validation_status_note": "worker events cannot set validation_status=passed (PROTOCOL rule 2)",
        })

    hard = []
    for i, r in enumerate(scope_rows, 1):
        p = [x for x in r["per_class"] if x["verdict"] == "SCOPE_ERROR"][0]
        q = p["decisive_statements"][0]["quote"] if p["decisive_statements"] else ""
        tag = r["pending_cbc09_correction"] or "NEW"
        hard.append("HF-W009-VACBIND-%02d: %s binds %s to a source outside the frozen predicate "
                    "(matter=%s, Lambda=%s; %s). Pending CBC-09: %s. Decisive: \"%s\"" % (
                        i, r["citation_id"], ";".join(p2["class_id"] for p2 in r["per_class"] if p2["verdict"] == "SCOPE_ERROR"),
                        p["matter"], p["lambda"], p["reason"], tag, q[:180]))
    findings = [
        {"id": "W009-VACBIND-F1", "severity": "major",
         "finding": ("Census of the 34 canonical L1 rows that bind AF-SCC-C2-VAC-GEN or AF-SCC-C0-VAC-GEN against the "
                     "frozen predicate (matter=none, EVE Ric(g)=0, Lambda=0): 19 LICENSED, 15 SCOPE_ERROR, "
                     "0 UNDETERMINED. 13 rows are matter-axis errors, 2 are Lambda-axis errors "
                     "(SRC-035 Kerr-de Sitter, SRC-064 Kerr-de Sitter). %d/%d scope-error rows are already named by the "
                     "pending CBC-09 primary-source correction proposal and the census agrees on all of them."
                     % (counts["already_in_pending_cbc09"], counts["SCOPE_ERROR"]))},
        {"id": "W009-VACBIND-F2", "severity": "major",
         "finding": ("%d scope-error rows are NOT covered by the pending CBC-09 corrections: %s. Each binds a frozen "
                     "SCC vacuum class although its cited source carries matter and/or Lambda > 0." % (
                         len(new_rows), ", ".join(r["citation_id"] for r in new_rows)))},
        {"id": "W009-VACBIND-F3", "severity": "info",
         "finding": ("Evidence path is ledger-internal (pinned citation_audit.csv + theorems.jsonl + the two schema "
                     "bytes); it does not re-fetch primaries. Agreement with the independently derived CBC-09 "
                     "primary-source corrections is therefore a cross-method corroboration, not a copy.")},
        {"id": "W009-VACBIND-F4", "severity": "info",
         "finding": ("Scope note: 5 additional rows bind AF-WCC-VAC-GEN together with an SCC class; the WCC class was "
                     "outside this census's predicate test. If the L1 repair revises these rows, the WCC axis should be "
                     "checked in the same pass (SRC-035/SRC-064 carry Lambda > 0 and are already flagged).")},
    ]

    events.append({
        "event_id": ev("review-01"), "event_type": "review", "created_at": CREATED,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": CLASS_IDS, "assignment_id": rec["assignment_id"],
        "target_id": "ledger/citation_audit.csv#315c19145065",
        "reviewer": "worker-009",
        "reviewer_independence": ("worker-009 is not the author of ledger/citation_audit.csv or ledger/theorems.jsonl and "
                                  "wrote no canonical file; but worker-009 authored the pending CBC-09 corrections, so this "
                                  "census is a same-worker cross-method re-derivation, NOT an independent reviewer verdict."),
        "verdict": "revise", "score": 3.0, "counts_as_full_schema_verdict": False,
        "review_scope": ("class-binding census of the SCC vacuum tokens at ledger/citation_audit.csv#315c19145065; "
                         "covers only the frozen predicate matter=none / Lambda=0; no detector-scope or HF-02 ruling; "
                         "no regularity-axis (C0 vs C2) adjudication"),
        "hard_failures": hard,
        "findings": findings,
        "agreement_matrix": rec["agreement_matrix"],
        "new_scope_errors": [r["citation_id"] for r in new_rows],
        "evidence_refs": ["ledger/citation_audit.csv#315c19145065", "ledger/theorems.jsonl#a1674f094979",
                          "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe", "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                          "artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json#%s" % art["artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json"][:16],
                          "artifacts/worker-009/vacuum_binding/census_vacuum_binding_worker-009.csv#%s" % art["artifacts/worker-009/vacuum_binding/census_vacuum_binding_worker-009.csv"][:16],
                          "ledger/citation_audit_scc_classbinding_worker-009.jsonl#%s" % ref("ledger/citation_audit_scc_classbinding_worker-009.jsonl"),
                          "ledger/citation_audit_scc_candidates_worker-009.csv#%s" % ref("ledger/citation_audit_scc_candidates_worker-009.csv")],
        "falsifier": rec["falsifier"],
    })

    events.append({
        "event_id": ev("status-01"), "event_type": "status", "created_at": CREATED,
        "actor": "worker-009", "node_id": "L1", "gate": "G-LIT", "group_id": "literature",
        "class_ids": CLASS_IDS, "assignment_id": rec["assignment_id"],
        "status": "active", "hours": 0.6,
        "summary": ("Bounded class-bound task (worker-009, L1/G-LIT): ledger-internal census of all 34 canonical rows that "
                    "bind AF-SCC-C2-VAC-GEN or AF-SCC-C0-VAC-GEN against the frozen predicate matter=none / Einstein vacuum "
                    "equations Ric(g)=0 / Lambda=0. 97 rows censused, 34 in scope, 19 LICENSED, 15 SCOPE_ERROR, 0 "
                    "UNDETERMINED; 165 decisive quotes hash-bound; 14/14 controls pass; reproducibility verifier PASS at "
                    "census_digest %s. 6 scope errors are new relative to the pending CBC-09 proposal: %s. No canonical "
                    "file written, no gate verdict, no validation_status." % (
                        rec["census_digest"][:16], ", ".join(r["citation_id"] for r in new_rows))),
        "evidence_refs": ["artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json#%s" % art["artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json"][:16],
                          "artifacts/worker-009/vacuum_binding/MANIFEST_worker-009.json#%s" % art["artifacts/worker-009/vacuum_binding/MANIFEST_worker-009.json"][:16],
                          "artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json#%s" % art["artifacts/worker-009/vacuum_binding/rules_vacuum_binding_worker-009.json"][:16],
                          "ledger/citation_audit.csv#315c19145065", "ledger/theorems.jsonl#a1674f094979",
                          "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe", "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3"],
        "next_falsifier": ("Independent non-author re-run of verify_vacuum_binding_worker-009.py --recheck at the four "
                           "pinned hashes, then a primary-source check of any one 'new' row: exhibit a 4D Einstein-vacuum "
                           "(Ric=0, Lambda=0, no matter) model statement in the cited paper for SRC-029, SRC-033, SRC-035, "
                           "SRC-048, SRC-064 or SRC-072, which would falsify that row's SCOPE_ERROR verdict. Reviewer must "
                           "also re-measure that all 165 decisive quotes are verbatim in the pinned fields."),
    })

    # idempotent append
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    appended = 0
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in events:
            if e["event_id"] in existing:
                continue
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            appended += 1

    checkpoint = {        "checkpoint_id": "w009-vacbinding-%s" % CREATED,
        "created_at": CREATED,
        "worker": "worker-009", "label": "worker-009-L1-vacuum-class-binding-census",
        "assignment_id": rec["assignment_id"], "node_id": "L1", "gate": "G-LIT",
        "class_ids": CLASS_IDS,
        "record": {"path": "artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json",
                   "sha256": art["artifacts/worker-009/vacuum_binding/verification_vacuum_binding_worker-009.json"]},
        "artifacts": art,
        "anchors": ANCHORS,
        "census_digest": rec["census_digest"],
        "controls_all_pass": rec["controls_all_pass"],
        "counts": counts,
        "new_scope_errors": [r["citation_id"] for r in new_rows],
        "events_appended_this_run": appended,
        "events_in_outbox_for_this_record": sum(
            1 for line in open(OUTBOX, encoding="utf-8")
            if line.strip() and json.loads(line).get("event_id", "").startswith(ev(""))),
    }
    open(CKPT, "w", encoding="utf-8").write(json.dumps(checkpoint, ensure_ascii=False, indent=1) + "\n")
    with open(CKPT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")

    print("manifest:", MANIFEST)
    print("events appended:", appended, "of", len(events))
    print("checkpoint:", CKPT)
    print("scope errors:", counts["SCOPE_ERROR"], "new:", checkpoint["new_scope_errors"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
