#!/usr/bin/env python3
"""Emit W058-REV27-CERT-03 events to comms/outbox/worker-058.jsonl.

Validates every event with research_map.schemas.validate_event, re-hashes every referenced
artifact on disk, refuses duplicate event ids, appends (never rewrites). Refuses to emit if
the certificate no longer shows the measured FAIL or the self-test is uncalibrated.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
import schemas  # noqa: E402

OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-058.jsonl")
CLASSES = "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN"
NODE = "F2b"

ARTIFACTS = [
    ("rev27_delta_checker", "artifacts/worker-058/rev27_cert/check_rev12_delta.py"),
    ("rev27_delta_cert_json", "artifacts/worker-058/rev27_cert/rev12_delta_cert.json"),
    ("rev27_acceptance_sweep_json", "artifacts/worker-058/rev27_cert/sweep_rev27.json"),
    ("rev27_acceptance_checker_frozen_copy",
     "artifacts/worker-058/rev27_cert/sweep_scc_order_frozen_copy.py"),
    ("rev27_selftest_harness", "artifacts/worker-058/rev27_cert/run_sensitivity_selftest.py"),
    ("rev27_selftest_json", "artifacts/worker-058/rev27_cert/sensitivity_selftest.json"),
    ("rev27_cert_report", "artifacts/worker-058/rev27_cert/README.md"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    hashes, missing = {}, []
    for kind, rel in ARTIFACTS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            missing.append(rel)
        else:
            hashes[rel] = sha256(p)
    if missing:
        print("emit refused: missing artifacts %s" % missing, file=sys.stderr)
        return 2

    REL = {kind: path for kind, path in ARTIFACTS}
    cert = json.load(open(os.path.join(ROOT, REL["rev27_delta_cert_json"]), encoding="utf-8"))
    sweep = json.load(open(os.path.join(ROOT, REL["rev27_acceptance_sweep_json"]), encoding="utf-8"))
    selftest = json.load(open(os.path.join(ROOT, REL["rev27_selftest_json"]), encoding="utf-8"))
    assert cert["verdict"] == "FAIL" and cert["counts"]["hard"] == 2, "cert changed; re-read before emitting"
    assert cert["repair_status"]["HF1_open"] and cert["repair_status"]["MINOR1_open"], "repair status changed"
    assert all(v["status"] == "verified" for v in cert["rev12_claim_checks"].values()), "rev12 claim regressed"
    assert sweep["verdict"] == "FAIL" and sweep["counts"]["hard"] == 2, "acceptance sweep changed"
    assert selftest["all_expectations_met"] is True, "self-test not calibrated"

    c0_sha = cert["inputs"]["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    c2_sha = cert["inputs"]["files"]["schemas/af_scc_c2_vacuum.yaml"]["sha256"]
    frozen_sha = cert["inputs"]["frozen_manifest_sha256"]
    frozen_rev = cert["inputs"]["frozen_revision"]
    base_c0 = cert["delta"]["rev26_baseline"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    base_c2 = cert["delta"]["rev26_baseline"]["schemas/af_scc_c2_vacuum.yaml"]["sha256"]

    events = []
    for i, (kind, rel) in enumerate(ARTIFACTS):
        events.append({
            "event_id": "w058-rc3-%s-art-%d" % (stamp, i),
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODE,
            "class_id": CLASSES,
            "artifact_type": kind,
            "path": rel,
            "sha256": hashes[rel],
            "validation_status": "unverified",
            "note": ("W058-REV27-CERT-03 pre-registered re-run at the post-rev12 SCC pins "
                     "(C0 55d0a1ea, C2 5476a3f2): verdict FAIL, the two recorded C0 repairs still "
                     "pending; all four rev12 close-findings claims verified; 10/10 sensitivity. "
                     "Unverified: lead-formulation owns interpretation and any gate consequence."),
        })
    events.append({
        "event_id": "w058-rc3-%s-claim-delta" % stamp,
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "class_id": CLASSES,
        "statement": (
            "At the FROZEN rev%s SCC pin bytes (C0 %s, C2 %s; manifest %s), the pre-registered "
            "acceptance test -- the unmodified sweep_scc_order checker recorded in "
            "W058-REPAIR-CERT-02, sha ff4fba42 -- still returns FAIL with exactly the two findings "
            "recorded since rev26: HF-1 class_size_predicate_inverted at C0:245 (was :251) and "
            "MINOR-1 strength_bucket_mismatch at C0:234 (was :240); delta.new_hard_codes is empty, so "
            "the rev12 edit neither repaired nor worsened the SCC order/strength axis. Independently, "
            "all four rev12 close-findings claims for the SCC pair are verified at the bound bytes: "
            "(C1) duplicate revised_at keys collapsed (rev26: 7 node-level duplicate keys in C0 and 7 "
            "in C2 -> rev27: 0 in both); (C2) revised_at and every revision_history stamp are "
            "wall-clock, not future-dated, revised_at = newest entry; (C3) both class_contract "
            "pointers resolve against the taxonomy files and every definition_ref resolves in-file; "
            "(C4) the D0 retyping left zero stale pair-typed binders, while the rev26 baseline C0 "
            "still contains 'forall (s,delta) in D0' and is caught by the same rule. A 10/10 "
            "calibrated mutant suite includes a both-repairs mutant that makes the unmodified checker "
            "return PASS hard=0. This is an artifact-consistency result, not a mathematical claim."),
        "conclusion_type": "formal_model",
        "assumptions": [
            "The implication_ledger.extension_class_containment declaration remains the audit axiom; "
            "the order is not re-derived from the regularity definitions (limitation carried from "
            "W058-CONTAIN-01).",
            "FROZEN.json moved rev27 (00:32:59) -> rev28 (00:35:08) during the task; the SCC pin bytes "
            "were unchanged at every measurement, so verdicts bind to measured sha256 values, not to "
            "the revision number.",
            "The C0 and C2 schemas and the rev26 baseline snapshot are the bytes at the stated hashes; the "
            "baseline snapshot root is partial, so a C3_pointer hard check there is an artifact of the "
            "missing taxonomy files, not a rev26 defect.",
            "The frozen acceptance checker's yaml_duplicate_keys field double-counts entries (its "
            "loader hook fires per deferred construction); the node-level count in the certificate is "
            "authoritative (rev26: 7 per file; rev27: 0).",
        ],
        "falsifier": (
            "A reader exhibits (a) a rev12 claim C1-C4 that is false at the bound bytes, (b) a stale "
            "pair-typed regularity binder or dangling pointer this checker misses, (c) an order/strength "
            "hard finding present at rev26 but absent from the certificate, or (d) a new rev27 defect "
            "that the calibrated mutants show the checker would have caught but did not."),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#%s" % c0_sha,
            "schemas/af_scc_c2_vacuum.yaml#%s" % c2_sha,
            "artifacts/formulation/FROZEN.json#%s" % frozen_sha,
            "artifacts/worker-058/rev27_cert/rev12_delta_cert.json#%s" % hashes[REL["rev27_delta_cert_json"]],
            "artifacts/worker-058/rev27_cert/sweep_rev27.json#%s" % hashes[REL["rev27_acceptance_sweep_json"]],
            "artifacts/worker-058/rev27_cert/sensitivity_selftest.json#%s" % hashes[REL["rev27_selftest_json"]],
        ],
        "artifact_refs": ["artifacts/worker-058/rev27_cert/rev12_delta_cert.json#%s"
                          % hashes[REL["rev27_delta_cert_json"]]],
    })
    events.append({
        "event_id": "w058-rc3-%s-blocker-repairs" % stamp,
        "event_type": "blocker",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "class_id": "AF-SCC-C0-VAC-GEN",
        "description": (
            "The same two mechanical C0 repairs are still pending after the rev12 close-findings edit "
            "and at the new pin 55d0a1ea, now as the pre-registered acceptance test records them: "
            "(1) implication_ledger.forbidden_transfers[0].reason C0:245 'strictly larger' -> "
            "'strictly smaller' (gate-relevant; unchanged through rev25/rev26/rev27, line shifted -6); "
            "(2) conclusion.forbidden_weakenings C0:234 'replacing future by two-sided direction' is "
            "still a duplicate of the forbidden_strengthenings item at C0:225 and must be removed from "
            "the weakenings bucket. rev12 closed its four declared claims (duplicate revised_at keys, "
            "wall-clock stamp, pointer repointing, D0 retyping) and introduced no new order/strength "
            "hard finding, so these two items are the only blockers on this axis."),
        "needed_to_unblock": (
            "Lead-formulation applies the two repairs in schemas/af_scc_c0_vacuum.yaml, re-freezes with "
            "a new sha256, and re-runs: python3 artifacts/worker-058/rev27_cert/"
            "sweep_scc_order_frozen_copy.py --root . and python3 artifacts/worker-058/rev27_cert/"
            "check_rev12_delta.py --root . ; PASS (0 hard findings) certifies the repair. Mutant "
            "MUT_ok_repair shows both repairs together achieve PASS. Do not hand-merge; publish one "
            "revision."),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#%s" % c0_sha,
            "schemas/af_scc_c0_vacuum.yaml:245",
            "schemas/af_scc_c0_vacuum.yaml:234",
            "artifacts/worker-058/rev27_cert/rev12_delta_cert.json#%s" % hashes[REL["rev27_delta_cert_json"]],
            "artifacts/worker-058/rev27_cert/sweep_rev27.json#%s" % hashes[REL["rev27_acceptance_sweep_json"]],
            "artifacts/worker-058/rev27_cert/_scratch/MUT_ok_repair/schemas/af_scc_c0_vacuum.yaml",
        ],
        "expected_information_gain": (
            "high: the successor to W058-REPAIR-CERT-02's pre-registered acceptance test now also "
            "covers the rev12 claims, so one command pair closes both the repair and the close-findings "
            "verification"),
    })
    events.append({
        "event_id": "w058-rc3-%s-status" % stamp,
        "event_type": "status",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.5,
        "summary": (
            "W058-REV27-CERT-03 complete at worker level: pre-registered acceptance re-run at the "
            "post-rev12 SCC pins (C0 55d0a1ea, C2 5476a3f2, manifest rev%s) returns FAIL hard=2 "
            "advisory=3 consistent=35 over 40 claims; HF-1 and MINOR-1 persist with a -6 line shift "
            "and no new code. All four rev12 close-findings claims (duplicate keys, wall-clock stamp, "
            "pointer repointing, D0 retyping) independently verified; rev26 baseline %s/%s keeps both "
            "repairs open. Sensitivity 10/10 including a both-repairs mutant that yields PASS. "
            "Boundary: artifact-consistency only; no math truth, node completion or gate verdict "
            "claimed."
            % (frozen_rev, base_c0[:12], base_c2[:12])),
        "evidence_refs": [
            "artifacts/worker-058/rev27_cert/rev12_delta_cert.json#%s" % hashes[REL["rev27_delta_cert_json"]],
            "artifacts/worker-058/rev27_cert/sweep_rev27.json#%s" % hashes[REL["rev27_acceptance_sweep_json"]],
            "artifacts/worker-058/rev27_cert/sensitivity_selftest.json#%s" % hashes[REL["rev27_selftest_json"]],
            "schemas/af_scc_c0_vacuum.yaml#%s" % c0_sha,
        ],
        "next_falsifier": (
            "Re-run both commands after the two C0 repairs land. Falsified if the unmodified sweep "
            "still returns hard>0 at the new hash, or if the new hash re-introduces a C1-C4 class of "
            "defect."),
    })

    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    existing.add(json.loads(line)["event_id"])
                except Exception:
                    pass
    fresh = []
    for e in events:
        schemas.validate_event(e)
        if e["event_id"] in existing:
            print("skip duplicate %s" % e["event_id"])
            continue
        fresh.append(e)
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for e in fresh:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    print("validated and appended %d events to %s" % (len(fresh), os.path.relpath(OUTBOX, ROOT)))
    for e in fresh:
        print("  %s %s" % (e["event_type"], e["event_id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
