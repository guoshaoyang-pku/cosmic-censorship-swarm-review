#!/usr/bin/env python3
"""Publish worker-063 review artifact + outbox event + checkpoint (bounded, advisory)."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


rep_path = os.path.join(ROOT, "artifacts/worker-063/gform_r3_binding_table/report.json")
r = json.load(open(rep_path))
rep_sha = sha256_file(rep_path)
script_sha = sha256_file(os.path.join(ROOT, "artifacts/worker-063/gform_r3_binding_table/measure_binding_table.py"))
r3_path = os.path.join(ROOT, "reviews/G-FORM-final-verify-r3.json")
r3_sha = sha256_file(r3_path)

cc = r["criterion_counts"]
cvd = r["r3"]["r3_vs_disk"]
f1 = r["falsifier_F1_cited_hashes"]
f2 = r["falsifier_F2_author_accepts"]
f4 = r["falsifier_F4_pin_movement"]
res = r["r3"]["row_resolution"]
mut = r["f2b_mutation_check_vs_w066_pins"]

review = {
    "schema": "worker-review/1",
    "event_id": "w063-gform-r3-bindings-20260912T0121-review",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-063",
    "reviewer": "worker-063",
    "instance": "worker-063-gform-r3-bindings",
    "authority_note": (
        "Advisory worker review. Does not set a gate verdict, node status, validation_status or "
        "freeze state, and writes no canonical artifact. Target is the r3 coverage-adjudication "
        "artifact and its evidence basis (REC-39 compliance), not a canonical schema."
    ),
    "target_id": "G-FORM-final-verify-r3",
    "reviewed_sha256": r3_sha,
    "reviewed_path": "reviews/G-FORM-final-verify-r3.json",
    "node_id": "F1,F2a,F2b",
    "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "gate": "G-FORM",
    "review_kind": "REC-39 per-file binding-table reproduction + CF-31 count adjudication input",
    "counts_as_full_schema_verdict": False,
    "counts_as_independent": True,
    "verdict": "revise",
    "score": 3.0,
    "score_note": (
        "Not a quality grade of the frozen schemas. r3's terminal conclusion (G-FORM NOT proposable "
        "at FROZEN rev29) is independently supported by this measurement; the revise verdict is on the "
        "coverage table as REC-39 evidence: required per-file fields are absent, one counted F2b accept "
        "is asserted full-schema without a declaration, and the table is stale at emission+30s."
    ),
    "concurrence_with_terminal_verdict": (
        "CONCUR: at the measured pins every class carries live named carriers; no counted accept "
        "disposes of them (worker-097 evidence_sufficiency=INSUFFICIENT at "
        "artifacts/worker-097/f2b_accept_sufficiency/report.json#9ae5438c1d46), so 'revise / not "
        "proposable' stands. This review does not ask for a different gate verdict; it supplies the "
        "REC-39 binding table and the CF-31 count adjudication that r3 was required to publish."
    ),
    "measured_instant": r["measured_at"],
    "corpus": r["corpus"],
    "pins_measured": {c: {"path": p["path"], "pin": p["pin"], "matches_frozen": p["pin_matches_frozen"]}
                      for c, p in r["pins"].items()},
    "hard_failures": [
        {
            "id": "HF-063-01",
            "severity": "major",
            "field": "G-FORM-final-verify-r3.coverage_table[*].non_author_accepts_full[*]",
            "finding": ("8/8 counted rows lack the three REC-39-required per-file fields: filename, "
                        "reviewed_sha256, independence_basis. Rows resolve only via accepted-stream "
                        "event_id + reviewer; 8/8 fail exact resolution to the file's own declared "
                        "event_id or review_id (classifications: %s)." % (
                            sorted({x["resolves"] for x in res}))),
            "required_fix": ("Emit per row: reviews/<file>.json, its sha256, reviewer, verdict, "
                             "reviewed_sha256, file mtime, full-schema flag state, independence basis."),
        },
        {
            "id": "HF-063-02",
            "severity": "major",
            "field": "coverage_table[F2b] vs reviews/F2b-review-rev13-052.json#%s" %
                     sha256_file(os.path.join(ROOT, "reviews/F2b-review-rev13-052.json"))[:12],
            "finding": ("r3 counts worker-052 as non_author_accepts_full with full_schema=true, but the "
                        "file declares no counts_as_full_schema_verdict field (state ABSENT; "
                        "reviewer_is_author=false, blind=true, hard_failures=[]). Strict declared-flag "
                        "count for F2b is 2 (worker-071, worker-090); loose count is 3. The missing "
                        "declaration must be adjudicated, not silently counted as full."),
        },
        {
            "id": "HF-063-03",
            "severity": "minor",
            "field": "coverage_table[F2a] staleness",
            "finding": ("reviews/F2a-review-rev29-085.json (reviewed_sha256=e9a27996dfd3, "
                        "counts_as_full_schema_verdict=true, hard_failures=[], written_at "
                        "2026-09-12T01:18:30+08:00) is a full accept at the pin and is omitted because "
                        "r3 measured at 01:18:00. Coverage moved within 30s of the table; REC-39's "
                        "'re-measure at use time' is not satisfiable from a table without a per-row "
                        "measured instant."),
        },
        {
            "id": "HF-063-04",
            "severity": "major",
            "field": "G-FORM-final-verify-r3 (REC-39 second requirement)",
            "finding": ("r3 does not state which of the CF-31 counts is correct and why the other is "
                        "wrong. This review supplies the adjudication (cf31_adjudication below) with "
                        "disk evidence."),
        },
    ],
    "findings": [
        {"id": "W063-F1", "check": "r3 falsifier 'a cited sha256 that does not equal the measured canonical sha256'",
         "detail": "0/4 cited 64-hex hashes unresolved: 815e08079aef->FROZEN, d9cebb9404b2->F1, "
                   "e9a27996dfd3->F2a, b2ab6acb2bbe->F2b; all measured equal.",
         "severity": "info"},
        {"id": "W063-F2", "check": "r3 falsifier 'a counted accept whose reviewer authored the artifact'",
         "detail": "0 violations. Pin-author set measured from artifact events whose own declared path "
                   "is the schema: {astra-lead-formulation} for all three pins; no counted reviewer is "
                   "in it. Earlier naive pin-mention counting produced a false positive for worker-072 "
                   "and was discarded.",
         "severity": "info"},
        {"id": "W063-F3", "check": "r3 falsifier 'an accept that ignores one of the named carriers'",
         "detail": "Recorded third-party dispositions resolve and support the carrier claim: "
                   "artifacts/worker-066/f2b_accept_disposition/report.json#a82623db025e (revise) and "
                   "artifacts/worker-097/f2b_accept_sufficiency/report.json#9ae5438c1d46 "
                   "(evidence_sufficiency=INSUFFICIENT: no accept at b2ab6acb2bbe disposes HF-152 or "
                   "HF-246). Keyword probe over counted accepts is reported informational-only in the "
                   "report and is not used as a hard finding.",
         "severity": "info"},
        {"id": "W063-F4", "check": "r3 falsifier 'any schema write during the round that moves a pin'",
         "detail": "0 violations: F1/F2a/F2b pins equal FROZEN rev29 declared values before and after "
                   "the measurement window.",
         "severity": "info"},
        {"id": "W063-F5", "check": "fixed-filename mutability (root cause of CF-31 drift), measured",
         "detail": "reviews/F2b-review-worker-072-rev29.json was rewritten in place at 01:14:54 "
                   "(created_at still claims 01:10:13): accept/hard=0 -> revise/hard=2, sha256 "
                   "7487f310d208 -> 5db91bb0781d. worker-066's verbatim pinned copy preserves the "
                   "accept bytes. Stream-event counting and filename-label counting both drift under "
                   "this; only a per-file sha256 at a stated instant binds.",
         "severity": "major"},
        {"id": "W063-F6", "check": "criterion-dependent counts at %s" % r["measured_at"],
         "detail": json.dumps({"strict": {c: cc[c]["strict_declared_full_accept"] for c in cc},
                               "loose": {c: cc[c]["loose_accept_at_pin"] for c in cc},
                               "revise_at_pin": {c: cc[c]["revise_at_pin"] for c in cc}}),
         "severity": "info"},
        {"id": "W063-F7", "check": "r3 claimed-vs-disk reconciliation",
         "detail": json.dumps({"claimed_but_not_strict": {c: cvd[c]["claimed_but_not_strict"] for c in cvd},
                               "claimed_but_not_loose": {c: cvd[c]["claimed_but_not_loose"] for c in cvd},
                               "disk_loose_not_claimed": {c: cvd[c]["disk_loose_not_claimed"] for c in cvd}}),
         "severity": "info"},
    ],
    "cf31_adjudication": {
        "controller_pass08_scan": {"F2b": 4, "reviewers": ["worker-052", "worker-071", "worker-072", "worker-090"]},
        "lead_census_0110": {"F2b_accept": 0, "F2b_revise": 7},
        "disk_at_%s" % r["measured_at"]: {
            "pin": r["pins"]["F2b"]["pin"],
            "strict_declared_full_accept": cc["F2b"]["strict_declared_full_accept"],
            "loose_accept_at_pin": cc["F2b"]["loose_accept_at_pin"],
            "revise_at_pin": cc["F2b"]["revise_at_pin"],
            "accept_flag_absent": cc["F2b"]["accept_flag_absent"],
        },
        "which_is_correct": ("Neither stated count is correct at its own emission instant. The "
                             "hash-bound strict count at 2026-09-12T01:20:56+08:00 is 2 "
                             "(worker-071, worker-090); the loose count is 3 (+worker-052, whose "
                             "full-schema declaration is ABSENT and must be adjudicated)."),
        "why_controller_4_is_wrong": ("Its list includes worker-072, whose file at the same pin was "
                                      "rewritten to revise with 2 hard failures at 01:14:54 (stream "
                                      "event 01:15:24), i.e. before the pass-08 final emission at "
                                      "01:16:26. A stream-event scan not re-measured from disk at use "
                                      "time carried a flipped verdict."),
        "why_lead_0_is_wrong": ("worker-090's accept at the pin declares "
                                "counts_as_full_schema_verdict=true with hard_failures=[] and was "
                                "written 01:08:56, 74s before the 01:10 census; worker-071's landed "
                                "01:10:40. Whatever predicate produced 0, it was not "
                                "reviewed_sha256==pin + declared full-schema flag + empty "
                                "hard_failures at use time."),
        "root_cause": ("No stated hash-bound inclusion predicate; review files are mutable under "
                       "fixed names (W063-F5) and revision labels in filenames (*rev13*) do not match "
                       "the pins they bind (all three F2b accepts bind reviewed_sha256=b2ab6acb2bbe, "
                       "the rev29 pin)."),
        "required_next": ("Per-row filename + reviewed_sha256 + mtime + flag state + independence "
                          "basis at one stated instant; adjudicate worker-052's absent flag; re-measure "
                          "from disk at use time. This review supplies the table and does not move the "
                          "gate."),
    },
    "evidence_refs": [
        "artifacts/worker-063/gform_r3_binding_table/report.json#%s" % rep_sha[:12],
        "artifacts/worker-063/gform_r3_binding_table/measure_binding_table.py#%s" % script_sha[:12],
        "reviews/G-FORM-final-verify-r3.json#%s" % r3_sha[:12],
        "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "artifacts/formulation/FROZEN.json#815e08079aef",
        "reviews/F2b-review-rev13-052.json#%s" % sha256_file(os.path.join(ROOT, "reviews/F2b-review-rev13-052.json"))[:12],
        "artifacts/worker-066/f2b_accept_disposition/pinned/reviews__F2b-review-worker-072-rev29.json#7487f310d208",
        "reviews/F2b-review-worker-072-rev29.json#5db91bb0781d",
        "artifacts/worker-097/f2b_accept_sufficiency/report.json#9ae5438c1d46",
        "artifacts/worker-066/f2b_accept_disposition/report.json#a82623db025e",
    ],
    "falsifier": (
        "Re-run artifacts/worker-063/gform_r3_binding_table/measure_binding_table.py at the three "
        "FROZEN rev29 pins (d9cebb9404b2 / e9a27996dfd3 / b2ab6acb2bbe): this review is falsified if "
        "the strict F2b count is not 2 at the stated instant, if reviews/F2b-review-rev13-052.json is "
        "shown to declare counts_as_full_schema_verdict (making the count 3), if any counted F2b "
        "accept's reviewed_sha256 differs from b2ab6acb2bbe or its reviewer equals the pin author "
        "{astra-lead-formulation}, if any of r3's four cited 64-hex hashes fails to resolve to the "
        "named live path, or if any of the three pins moves without a new revision. A later write to "
        "a review file or to the pin is not a falsifier - it is a new revision to re-run against."
    ),
    "next_falsifier": (
        "At the rev14/FROZEN rev30 pins after REC-36 lands: re-run this measurement and require the "
        "r3 successor to carry per-row filename+reviewed_sha256+mtime+flag+basis, worker-052's flag "
        "adjudicated, and zero post-emission omissions; the F2b carriers :152/:246 are falsified only "
        "if the new revision changes those lines while the mutant controls still pass."
    ),
    "worker_status": "active",
    "claims_completion": False,
}

rev_path = os.path.join(ROOT, "reviews/G-FORM-r3-bindings-worker-063.json")
with open(rev_path, "w", encoding="utf-8") as fh:
    json.dump(review, fh, indent=1, sort_keys=False)
    fh.write("\n")
rev_sha = sha256_file(rev_path)

# outbox: one compact JSON object per line (protocol ingest channel)
outbox = os.path.join(ROOT, "comms/outbox/worker-063.jsonl")
line = json.dumps(review, separators=(",", ":"), sort_keys=False)
with open(outbox, "a", encoding="utf-8") as fh:
    fh.write(line + "\n")

# checkpoint
ckpt = {
    "schema": "worker-checkpoint/1",
    "actor": "worker-063",
    "created_at": NOW,
    "instance": "worker-063-gform-r3-bindings",
    "status": "active",
    "task": "REC-39 support: independent per-file G-FORM r3 binding table + CF-31 count adjudication",
    "class_ids": review["class_ids"],
    "node_id": "F1,F2a,F2b",
    "gate": "G-FORM",
    "gate_verdict_set_by_this_worker": None,
    "hours": 0.4,
    "summary": (
        "Measured the REC-39 per-file binding table from disk at FROZEN rev29 pins. r3 supplies 0/8 "
        "required filename+reviewed_sha256+independence_basis fields; F2b strict count 2 vs r3's 3 "
        "(worker-052 flag ABSENT); F2a coverage moved 30s after r3's cut (worker-085 accept omitted); "
        "controller 4-count carried worker-072's flipped verdict; lead 0-count excluded worker-090's "
        "declared full accept. Concurrent with r3's terminal 'not proposable' conclusion."
    ),
    "artifacts": {
        "report": {"path": "artifacts/worker-063/gform_r3_binding_table/report.json", "sha256": rep_sha},
        "instrument": {"path": "artifacts/worker-063/gform_r3_binding_table/measure_binding_table.py", "sha256": script_sha},
        "review": {"path": "reviews/G-FORM-r3-bindings-worker-063.json", "sha256": rev_sha},
        "outbox": {"path": "comms/outbox/worker-063.jsonl"},
    },
    "pins_at_checkpoint": {c: r["pins"][c]["pin"] for c in r["pins"]},
    "corpus_digest": r["corpus"]["digest"],
    "falsifier_results": {
        "F1_unresolved_cited_hashes": 0,
        "F2_author_accept_violations": len(f2),
        "F3_recorded_dispositions_present": 3,
        "F4_pin_movements": sum(1 for x in f4 if x["moved"]),
        "f2b_accepts_unchanged_vs_w066_pins": all(x["unchanged_since_pin"] for x in mut),
    },
    "open_items": [
        "worker-052 F2b full-schema declaration ABSENT - audit lead must adjudicate before counting",
        "r3 successor must publish per-row filename+reviewed_sha256+mtime+flag+basis at a stated instant",
        "REC-36 rev14/FROZEN rev30 will void these pins; re-run at new pins",
    ],
    "next_falsifier": review["next_falsifier"],
    "no_completion_claim": True,
}
ck_path = os.path.join(ROOT, "runtime/state/w063_gform_r3_bindings_checkpoint.json")
with open(ck_path, "w", encoding="utf-8") as fh:
    json.dump(ckpt, fh, indent=1, sort_keys=True)
    fh.write("\n")
ck_sha = sha256_file(ck_path)

print("review:", rev_path, rev_sha)
print("outbox:", outbox, "appended 1 line")
print("checkpoint:", ck_path, ck_sha)
print("report_sha256:", rep_sha)
print("script_sha256:", script_sha)
