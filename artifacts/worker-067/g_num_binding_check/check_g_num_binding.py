#!/usr/bin/env python3
"""W067-GNUM-C8-BINDING-01: independent machine check of the G-NUM C8 binding.

Question
--------
The controller's gate reason for G-NUM (research_map/research_map.json ->
controller_gate_audit.G-NUM, checked 2026-09-12T00:24:40+08:00) states:

    "... protocol measured 1e6cdf04d7a2; the recorded protocol verdict
     reviews/G-NUM-protocol-review.json binds unbound (stale), so criterion C8
     is the exact unmet requirement."

Does the on-disk review file actually fail to bind the measured protocol hash,
or is "unbound (stale)" an artifact of the reader?

Method (read-only; no canonical path is written)
------------------------------------------------
1. Import the live controller module research_map/astra_lifecycle.py and call its
   own pipeline in memory: measured_hashes / publication_status /
   audit_evidence.audit / review_coverage / clock_discipline / lock_guard, then
   gate_audit(). This reproduces the exact gate reason without applying a
   lifecycle pass.
2. Independently measure numerics/CONVERGENCE_PROTOCOL.md and parse
   reviews/G-NUM-protocol-review.json.
3. Compare four things:
     a. the key the G-NUM reason reads  (artifact_sha256, astra_lifecycle.py:259)
     b. the keys the same module binds through elsewhere
        (_explicit_pins: artifact_sha256, reviewed_sha256, sha256, cited_sha256)
     c. what the current review file exposes
     d. which binding is correct against the measured protocol hash
4. Controls:
     C1 the superseded rev1 advisory file (which does use artifact_sha256) must
        still resolve -> isolates the key-convention mismatch as the cause.
     C2 the module's own _explicit_pins must resolve the current review to the
        measured hash -> the file is bindable by the module's declared logic.
     C3 canary no-write control: sha256 of every read canonical file before and
        after must be identical.
     C4 registration control: is the accepting verdict present in map.reviews /
        the lead-audit outbox / events.jsonl?

Exit code 0 iff the false positive reproduces, all controls pass, and no canary
drifted. Any drift or failed control is a hard stop (exit 1).
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = Path(__file__).with_name("binding_check.json")
CANARIES = [
    "numerics/CONVERGENCE_PROTOCOL.md",
    "reviews/G-NUM-protocol-review.json",
    "reviews/G-NUM-protocol-review-rev1-advisory.json",
    "research_map/astra_lifecycle.py",
    "research_map/research_map.json",
    "comms/outbox/astra-lead-audit.jsonl",
    "numerics/tests/n0_gate_proposal.json",
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canary_snapshot() -> dict:
    return {p: (sha256(ROOT / p) if (ROOT / p).is_file() else None) for p in CANARIES}


def main() -> int:
    before = canary_snapshot()

    sys.path.insert(0, str(ROOT / "research_map"))
    import astra_lifecycle as L  # live controller code, imported read-only

    # --- 1. reproduce the live gate reason in memory -------------------------
    m = json.loads(L.MAP.read_text())
    hashes = L.measured_hashes(m)
    pub = L.publication_status()
    soft = L.audit_evidence.audit(L.MAP)["soft"]
    cov = L.review_coverage(hashes)
    clock = L.clock_discipline()
    guard = L.lock_guard(hashes)
    audit = L.gate_audit(m, hashes, pub, soft, cov, clock, guard)
    reason = audit["G-NUM"]["reason"]
    asserts_unbound = "binds unbound" in reason
    asserts_stale = "(stale)" in reason

    # --- 2. measure the protocol and parse the review ------------------------
    proto_path = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
    proto_h = sha256(proto_path)
    review_rel = "reviews/G-NUM-protocol-review.json"
    review_path = ROOT / review_rel
    review = json.loads(review_path.read_text())
    review_h = sha256(review_path)
    reviewed = review.get("reviewed_sha256")
    artifact_key = review.get("artifact_sha256")
    pins = L._explicit_pins(review)
    correct_binding = next((p for p in pins if p.startswith(proto_h[:12]) or proto_h.startswith(p[:12])), None)

    # --- 3. the exact expression astra_lifecycle.py:259 evaluates ------------
    src_lines = (ROOT / "research_map" / "astra_lifecycle.py").read_text().splitlines()
    line259 = src_lines[258].strip()
    buggy_value = str(review.get("artifact_sha256") or "unbound")[:12]

    # --- 4. controls ----------------------------------------------------------
    rev1_path = ROOT / "reviews" / "G-NUM-protocol-review-rev1-advisory.json"
    rev1 = json.loads(rev1_path.read_text())
    c1_observed = str(rev1.get("artifact_sha256") or "unbound")[:12]
    controls = [
        {"id": "C1", "description": "superseded rev1 advisory exposes artifact_sha256, so the "
                                    "line-259 key convention does resolve for the old file",
         "expected": "01b2072434cd", "observed": c1_observed, "pass": c1_observed == "01b2072434cd"},
        {"id": "C2", "description": "module _explicit_pins resolves the current review to the measured "
                                    "protocol hash (the file IS bindable by the module's own logic)",
         "expected": proto_h[:12], "observed": (correct_binding or "none")[:12],
         "pass": bool(correct_binding)},
        {"id": "C3", "description": "no-write canary control: all read canonical files identical "
                                    "before/after this check",
         "expected": "no drift", "observed": "no drift", "pass": None},  # filled below
        {"id": "C4", "description": "registration control: accepting verdict present in map.reviews / "
                                    "lead-audit outbox / events.jsonl",
         "expected": "absent everywhere -> registration gap",
         "observed": None, "pass": None},  # filled below
    ]

    # C4 observations
    ev_id = review.get("event_id")
    map_has_accept = any(
        (r.get("reviewer") or r.get("actor")) == review.get("reviewer")
        and r.get("verdict") == "accept"
        and str(r.get("reviewed_sha256") or r.get("artifact_sha256") or "").startswith(proto_h[:12])
        for r in m.get("reviews", []))
    outbox_has = False
    for ob in (ROOT / "comms" / "outbox").glob("astra-lead-audit*.jsonl"):
        if ev_id and ev_id in ob.read_text():
            outbox_has = True
    events_has = ev_id is not None and ev_id in (ROOT / "research_map" / "events.jsonl").read_text()
    controls[3]["observed"] = {"map_reviews_accept_at_current_hash": map_has_accept,
                               "lead_audit_outbox_event": outbox_has,
                               "events_jsonl": events_has,
                               "event_id": ev_id}
    controls[3]["pass"] = not (map_has_accept or outbox_has or events_has)

    # --- 5. no-write control --------------------------------------------------
    after = canary_snapshot()
    drift = {p: [before[p], after[p]] for p in before if before[p] != after[p]}
    controls[2]["observed"] = "no drift" if not drift else json.dumps(drift)
    controls[2]["pass"] = not drift

    false_positive = (asserts_unbound and asserts_stale
                      and buggy_value == "unbound"
                      and reviewed == proto_h
                      and correct_binding is not None
                      and review.get("verdict") == "accept")
    all_controls_pass = all(c["pass"] for c in controls)

    result = {
        "schema": "worker-067/g-num-binding-check/v1",
        "task_id": "W067-GNUM-C8-BINDING-01",
        "checked_at": now(),
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "protocol": {"path": "numerics/CONVERGENCE_PROTOCOL.md", "sha256": proto_h,
                     "sha256_12": proto_h[:12]},
        "review_file": {
            "path": review_rel, "sha256": review_h, "verdict": review.get("verdict"),
            "reviewer": review.get("reviewer"), "created_at": review.get("created_at"),
            "event_id": ev_id, "reviewed_sha256": reviewed, "artifact_sha256": artifact_key,
            "counts_as_full_schema_verdict": review.get("counts_as_full_schema_verdict"),
            "bindable_by_explicit_pins": (correct_binding or "none")[:12]},
        "controller_source": {
            "path": "research_map/astra_lifecycle.py", "sha256": sha256(ROOT / "research_map" / "astra_lifecycle.py"),
            "line": 259, "expression": line259, "read_key": "artifact_sha256",
            "sibling_binding_keys": ["artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"]},
        "reproduction": {
            "reproduced_in_memory_gate_reason": reason,
            "reason_asserts_binds_unbound": asserts_unbound,
            "reason_asserts_stale": asserts_stale,
            "line259_value_for_current_review": buggy_value,
            "correct_binding_from_review_file": (correct_binding or "none")[:12],
            "binding_agrees_with_measured_protocol": bool(correct_binding and reviewed == proto_h)},
        "controls": controls,
        "verdict": ("FALSE_POSITIVE_CONFIRMED"
                    if (false_positive and all_controls_pass) else "NOT_CONFIRMED"),
        "finding": (
            "The G-NUM gate reason's 'binds unbound (stale)' is a checker artifact, not a property of "
            "the review corpus. reviews/G-NUM-protocol-review.json carries verdict=accept by "
            "astra-lead-audit pinned to reviewed_sha256=" + (reviewed or "none")[:12] + ", which equals "
            "the measured protocol hash " + proto_h[:12] + ". The gate reason at "
            "research_map/astra_lifecycle.py:259 reads only the key artifact_sha256, which that file does "
            "not carry, so it always falls back to 'unbound'. The same module's _explicit_pins() binds "
            "through artifact_sha256 OR reviewed_sha256 and resolves the file correctly. The 'stale' "
            "assertion is therefore also false at this hash; the stale record is the superseded rev1 "
            "advisory (artifact_sha256=01b2072434cd) and the map.reviews entry for the audit lead."),
        "registration_gap": {
            "summary": "The accepting verdict exists only as a file: no review event with event_id "
                       + str(ev_id) + " is present in map.reviews, the lead-audit outbox, or events.jsonl, "
                       "so a map-based adjudication still sees the 00:08 revise at 01b2072434cd.",
            "map_reviews_accept_at_current_hash": map_has_accept,
            "lead_audit_outbox_event": outbox_has,
            "events_jsonl": events_has},
        "proposed_patch": {
            "applied": False,
            "file": "research_map/astra_lifecycle.py", "line": 259,
            "old": "proto_rev_h = str(json.loads(proto_review.read_text()).get(\"artifact_sha256\") or \"unbound\")[:12]",
            "new": "proto_rev_h = str(json.loads(proto_review.read_text()).get(\"artifact_sha256\") or json.loads(proto_review.read_text()).get(\"reviewed_sha256\") or \"unbound\")[:12]",
            "alternative": "or normalize the review writer to always emit artifact_sha256; either branch "
                           "must be decided by the controller, not a breadth worker."},
        "scope_limits": [
            "This is a binding/registration check only. It does not re-review the protocol content; the "
            "worker's prior content verdict on rev3 was revise (F1, section 3.4 constant-CFL scoping) and "
            "that verdict is untouched by this artifact.",
            "No canonical path was edited; the patch above is proposed, not applied.",
            "The gate verdict stays with the controller: this finding only removes a false 'unbound' "
            "reading and flags that the accept is unregistered."],
        "falsifier": (
            "Withdrawn if any of: (a) numerics/CONVERGENCE_PROTOCOL.md no longer hashes to " + proto_h[:12] +
            "; (b) reviews/G-NUM-protocol-review.json no longer carries reviewed_sha256 equal to the "
            "measured protocol hash, or its verdict ceases to be accept; (c) the gate reason no longer "
            "contains 'binds unbound'; (d) the review contract mandates artifact_sha256 for protocol "
            "reviews, in which case the nonconforming party is the review file and the patch branch "
            "flips to the writer."),
        "canary_drift": drift,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("verdict:", result["verdict"])
    print("reason :", reason)
    print("review :", review.get("verdict"), review.get("reviewer"), "reviewed=", (reviewed or "")[:12],
          "artifact_key=", artifact_key)
    print("line259:", line259)
    print("controls:", [(c["id"], c["pass"]) for c in controls])
    return 0 if (false_positive and all_controls_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
