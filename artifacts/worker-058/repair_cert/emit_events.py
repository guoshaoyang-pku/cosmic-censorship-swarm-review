#!/usr/bin/env python3
"""Emit W058-REPAIR-CERT-02 events to comms/outbox/worker-058.jsonl.

Validates every event with research_map.schemas.validate_event, re-hashes every
referenced artifact on disk, refuses duplicate event ids, appends (never rewrites).
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
    ("repair_cert_checker", "artifacts/worker-058/repair_cert/sweep_scc_order.py"),
    ("repair_cert_sweep_json", "artifacts/worker-058/repair_cert/scc_order_sweep.json"),
    ("repair_cert_selftest_harness", "artifacts/worker-058/repair_cert/run_sensitivity_selftest.py"),
    ("repair_cert_selftest_json", "artifacts/worker-058/repair_cert/sensitivity_selftest.json"),
    ("repair_cert_report", "artifacts/worker-058/repair_cert/README.md"),
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

    sweep = json.load(open(os.path.join(ROOT, ARTIFACTS[1][1])))
    selftest = json.load(open(os.path.join(ROOT, ARTIFACTS[3][1])))
    assert sweep["verdict"] == "FAIL" and sweep["counts"]["hard"] == 2, "sweep changed; re-read before emitting"
    assert selftest["all_expectations_met"] is True, "self-test not calibrated"

    events = []
    for i, (kind, rel) in enumerate(ARTIFACTS):
        events.append({
            "event_id": "w058-rc2-%s-art-%d" % (stamp, i),
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODE,
            "class_id": CLASSES,
            "artifact_type": kind,
            "path": rel,
            "sha256": hashes[rel],
            "validation_status": "unverified",
            "note": ("W058-REPAIR-CERT-02 full-text SCC order/strength sweep; verdict FAIL "
                     "(HF-1 known C0:251 inversion + MINOR-1 R2-10 refresh), 7/7 sensitivity. "
                     "Unverified: lead-formulation owns interpretation and any gate consequence."),
        })
    events.append({
        "event_id": "w058-rc2-%s-claim-cert" % stamp,
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "class_id": CLASSES,
        "statement": (
            "At the frozen canonical hashes C0 1bb78ce9 and C2 b6123750 (FROZEN rev26 2554e276), an "
            "independent full-text sweep of both SCC schemas' YAML scalar content -- including anti_scope, "
            "class_identity_variants, must_not_conflate and the conclusion strength buckets, regions the "
            "prior ledger-only audits did not cover -- evaluates 40 order/strength claims and reports "
            "exactly 2 hard findings: (HF-1) C0 line 251 'C2 is a strictly larger extension class' "
            "contradicts the chain declared at C0 line 244, and (MINOR-1, R2-10 refresh) C0 line 240 "
            "'replacing future by two-sided direction' is still filed under forbidden_weakenings although "
            "two-sided is strictly stronger and C2 repaired the same mislabel. Both repairs applied by "
            "string surgery (mutant M1) make the calibrated checker return PASS with 0 hard findings. "
            "3 advisories remain (C0:157 denial sentence, H2_loc variant-vs-class identity tension in both "
            "files). This is an artifact-consistency result, not a mathematical claim."),
        "conclusion_type": "formal_model",
        "assumptions": [
            "The implication_ledger.extension_class_containment declaration is the audit axiom; the order "
            "is not re-derived from the regularity definitions (limitation carried from W058-CONTAIN-01).",
            "Strength is monotone in extension-set size: the inexistence statement over a larger extension "
            "set is the stronger statement.",
            "The sweep is lexical/semi-structured: it evaluates claims carrying a comparator token and a "
            "regularity token; semantic claims without those tokens are out of scope.",
            "Verdicts bind to the measured sha256 values, not to FROZEN revision numbers.",
        ],
        "falsifier": (
            "A reader exhibits an order/strength claim this sweep accepts that contradicts the declared "
            "chain, or shows a reported hard finding is not present in the bound bytes, or shows the chain "
            "axiom is mis-derived from the definitions."),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
            "schemas/af_scc_c2_vacuum.yaml#b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
            "artifacts/formulation/FROZEN.json#2554e276a0db70579ce36f7e665c9af81a1707bdc99e33758e861bec1d2df2e3",
            "artifacts/worker-058/repair_cert/scc_order_sweep.json#%s" % hashes[ARTIFACTS[1][1]],
            "artifacts/worker-058/repair_cert/sensitivity_selftest.json#%s" % hashes[ARTIFACTS[3][1]],
        ],
        "artifact_refs": ["artifacts/worker-058/repair_cert/scc_order_sweep.json#%s"
                          % hashes[ARTIFACTS[1][1]]],
    })
    events.append({
        "event_id": "w058-rc2-%s-blocker-repairs" % stamp,
        "event_type": "blocker",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "class_id": "AF-SCC-C0-VAC-GEN",
        "description": (
            "Two C0 wording repairs are pending at the frozen hash 1bb78ce9 and are mechanical: "
            "(1) implication_ledger.forbidden_transfers[0].reason line 251 'strictly larger' -> "
            "'strictly smaller' (gate-relevant; third independent confirmation); (2) "
            "conclusion.forbidden_weakenings[5] line 240 'replacing future by two-sided direction' moved "
            "to forbidden_strengthenings (R2-10 minor, update to the rev5 record: C2 fixed, C0 not). A "
            "pre-registered acceptance test exists: after re-freeze, sweep_scc_order.py must return "
            "hard==0; mutant M1 shows both repairs together achieve it."),
        "needed_to_unblock": (
            "Lead-formulation applies the two repairs in schemas/af_scc_c0_vacuum.yaml, re-freezes with a "
            "new sha256, and re-runs artifacts/worker-058/repair_cert/sweep_scc_order.py --root . ; PASS "
            "(0 hard findings) certifies the repair. Do not hand-merge; publish one revision."),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
            "schemas/af_scc_c0_vacuum.yaml:251",
            "schemas/af_scc_c0_vacuum.yaml:240",
            "artifacts/worker-058/repair_cert/scc_order_sweep.json#%s" % hashes[ARTIFACTS[1][1]],
            "artifacts/worker-058/repair_cert/_scratch/M1_repair_both/result.json",
        ],
        "expected_information_gain": "high: turns the last recorded C0 formulation repair into a one-command mechanical check",
    })
    events.append({
        "event_id": "w058-rc2-%s-status" % stamp,
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
            "W058-REPAIR-CERT-02 complete at worker level: full-text SCC order/strength sweep (40 claims; "
            "2 hard, 3 advisory, 35 consistent) plus a 7/7 calibrated mutant suite and a pre-registered "
            "post-repair acceptance test. HF-1 = known C0:251 inversion persists at 1bb78ce9; MINOR-1 = "
            "R2-10 labelling refreshed (C2 fixed, C0 open). Boundary: audits internal order/strength "
            "consistency only; no physical truth, citation, node completion or gate verdict claimed."),
        "evidence_refs": [
            "artifacts/worker-058/repair_cert/scc_order_sweep.json#%s" % hashes[ARTIFACTS[1][1]],
            "artifacts/worker-058/repair_cert/sensitivity_selftest.json#%s" % hashes[ARTIFACTS[3][1]],
            "schemas/af_scc_c0_vacuum.yaml#1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
        ],
        "next_falsifier": (
            "Re-run at the next canonical C0 hash: falsified if PASS at 1bb78ce9 (defect must remain "
            "visible) or FAIL after both repairs at the new hash (repair insufficiency or new defect)."),
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
