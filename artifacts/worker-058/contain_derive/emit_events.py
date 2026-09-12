#!/usr/bin/env python3
"""Emit W058-CONTAIN-DERIVE-04 events to comms/outbox/worker-058.jsonl.

Validates every event with research_map.schemas.validate_event, re-hashes every referenced
artifact on disk, refuses duplicate event ids, appends (never rewrites). Refuses to emit if the
certificate no longer shows the expected verdict, the links are not all derived, or the
sensitivity self-test is uncalibrated.
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
# Fixed emission stamp: wall-clock-derived ids made a re-run append a second, identical batch
# (worker-078 precedent). The id set is frozen so re-running this emitter is a no-op.
STAMP = "20260912T004948"

ARTIFACTS = [
    ("containment_derivation_checker", "artifacts/worker-058/contain_derive/derive_containment.py"),
    ("containment_derivation_json", "artifacts/worker-058/contain_derive/containment_derivation.json"),
    ("containment_derivation_selftest_harness",
     "artifacts/worker-058/contain_derive/run_sensitivity_selftest.py"),
    ("containment_derivation_selftest_json",
     "artifacts/worker-058/contain_derive/sensitivity_selftest.json"),
    ("containment_derivation_report", "artifacts/worker-058/contain_derive/README.md"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    stamp = STAMP
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
    cert = json.load(open(os.path.join(ROOT, REL["containment_derivation_json"]),
                          encoding="utf-8"))
    selftest = json.load(open(os.path.join(ROOT, REL["containment_derivation_selftest_json"]),
                              encoding="utf-8"))

    # fail closed if the measured state is not the one recorded in the report
    assert cert["verdict"] == "FAIL", "derivation verdict changed; re-read before emitting"
    hard_codes = {f["code"] for f in cert["hard_findings"]}
    assert "class_size_predicate_inverted" in hard_codes, "hard finding missing"
    assert cert["counts"]["links_derived"] == 3 and cert["counts"]["links_under_justified"] == 0
    assert cert["inputs"]["frozen_match"] is True and not cert["inputs"]["frozen_pin_drift"]
    assert selftest["all_expectations_met"] is True, "self-test not calibrated"
    assert selftest["cases_met"] == selftest["cases_total"] == 12, "self-test case count changed"
    assert selftest["checker_sha256"] == hashes[REL["containment_derivation_checker"]], \
        "self-test was run against a different checker build"

    c0_sha = cert["inputs"]["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    c2_sha = cert["inputs"]["files"]["schemas/af_scc_c2_vacuum.yaml"]["sha256"]
    reg_sha = cert["inputs"]["files"]["artifacts/formulation/VARIANT_REGISTRY.json"]["sha256"]
    tax_sha = cert["inputs"]["files"]["research_map/formulation_taxonomy.yaml"]["sha256"]
    frozen_sha = cert["inputs"]["frozen_manifest_sha256"]
    frozen_rev = cert["inputs"]["frozen_revision"]

    note = ("W058-CONTAIN-DERIVE-04 containment-derivation certificate at C0 %s, C2 %s, registry "
            "%s, manifest rev%s: verdict FAIL (1 hard C0:245, 1 advisory C0:151); all three "
            "containment links derived (L3 depends on the registry's H2LOC continuity conjunct); "
            "12/12 sensitivity mutants met. Unverified: lead-formulation owns interpretation, the "
            "repairs and any gate consequence." % (c0_sha[:12], c2_sha[:12], reg_sha[:12], frozen_rev))

    events = []
    for i, (kind, rel) in enumerate(ARTIFACTS):
        events.append({
            "event_id": "w058-cd-%s-art-%d" % (stamp, i),
            "event_type": "artifact",
            "created_at": now,
            "actor": "worker-058",
            "node_id": NODE,
            "class_id": CLASSES,
            "artifact_type": kind,
            "path": rel,
            "sha256": hashes[rel],
            "validation_status": "unverified",
            "note": note,
        })

    events.append({
        "event_id": "w058-cd-%s-claim-derive" % stamp,
        "event_type": "claim",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "class_id": CLASSES,
        "statement": (
            "At the bound bytes (C0 %s, C2 %s, VARIANT_REGISTRY %s, declared F0 taxonomy %s, "
            "FROZEN rev%s %s), the SCC extension-class chain 'E_C2 subset E_{C^1,1} subset E_H2loc "
            "subset E_C0' declared at C0:238 and C2:236 is DERIVED from the frozen definitional "
            "base rather than assumed: L1 via C2=>C^{1,1} (elementary), L2 via C^{1,1}=>Riem in "
            "L2_loc and C^{1,1}=>C0 satisfying the H2LOC definition, L3 because the registered "
            "H2LOC variant is 'continuous metric with Riemann tensor in L^2_loc' and continuity is "
            "a defining conjunct. The derivation exposes one definitional dependency: a "
            "curvature-only reading of H2_loc would not give E_H2loc subset E_C0 in 4D (H^2_loc "
            "does not embed into C0 at the s=n/2 Sobolev borderline); mutant M4 strips the "
            "conjunct and the checker flips L3 to under_justified. Against the derived order the "
            "bound bytes contain exactly one hard finding: C0:245 calls C2 'a strictly larger "
            "extension class' when the derived order makes it strictly smaller (the transfer "
            "direction and consequent are correct; only the class-size antecedent is false), plus "
            "one advisory: C0:151 'No containment with C2 or C0 is asserted here' is stale against "
            "both ledgers and the registry. The repaired F0 vocabulary entry meaning_C2 ('does NOT "
            "forbid C^{1,1} or H^2_loc') agrees with the derived order. Mutant M1 (both C0 repairs "
            "applied) makes the unmodified checker return PASS hard=0 with all three links still "
            "derived. This is a definitional-consistency result, not a mathematical claim."
            % (c0_sha[:16], c2_sha[:16], reg_sha[:16], tax_sha[:16], frozen_rev, frozen_sha[:16])),
        "conclusion_type": "formal_model",
        "assumptions": [
            "The rule base R1-R4 is declared and sourced: R1 C2=>C^{1,1} and R4 C^{1,1}=>C0 are "
            "elementary, R2 C^{1,1}=>Riem in L2_loc is standard and stated verbatim at C2:151/"
            "C2:240, R3 is the definitional reading of VARIANT_REGISTRY v2.0 H2LOC. The checker "
            "verifies closure under the rule base and the presence of each warrant in the bound "
            "bytes; it does not prove the calculus rules.",
            "Verdicts bind to the measured sha256 values, not to revision numbers; frozen_match "
            "was true for all four pinned inputs at run time.",
            "The sweep is lexical/semi-structured over sentences carrying a class token and a "
            "comparator token; semantic claims without those tokens are out of scope.",
            "No mathematical truth, citation-scope, node-completion or gate claim is made.",
        ],
        "falsifier": (
            "A reader exhibits (a) a frozen definitional base in which a chain link fails or the "
            "order reverses, (b) the checker returning PASS while a bound sentence still calls C2 "
            "strictly larger or denies containment, (c) a sensitivity mutant the checker reports "
            "with the canonical verdict, or (d) VARIANT_REGISTRY H2LOC losing the continuity "
            "conjunct while L3 is still reported derived."),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#%s" % c0_sha,
            "schemas/af_scc_c2_vacuum.yaml#%s" % c2_sha,
            "artifacts/formulation/VARIANT_REGISTRY.json#%s" % reg_sha,
            "research_map/formulation_taxonomy.yaml#%s" % tax_sha,
            "artifacts/formulation/FROZEN.json#%s" % frozen_sha,
            "artifacts/worker-058/contain_derive/containment_derivation.json#%s"
            % hashes[REL["containment_derivation_json"]],
            "artifacts/worker-058/contain_derive/sensitivity_selftest.json#%s"
            % hashes[REL["containment_derivation_selftest_json"]],
        ],
        "artifact_refs": [
            "artifacts/worker-058/contain_derive/containment_derivation.json#%s"
            % hashes[REL["containment_derivation_json"]],
        ],
    })

    events.append({
        "event_id": "w058-cd-%s-blocker-repairs" % stamp,
        "event_type": "blocker",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "class_id": "AF-SCC-C0-VAC-GEN",
        "description": (
            "The derivation certificate confirms, now with a warrant rather than an axiom, that "
            "two C0 sentences block a clean containment-consistency accept at 55d0a1ea: (1) hard "
            "-- implication_ledger.forbidden_transfers[0].reason C0:245 'C2 is a strictly larger "
            "extension class' contradicts the derived order E_C2 subset E_{C^1,1} subset E_H2loc "
            "subset E_C0 (third independent confirmation after worker-08 and W058-CONTAIN-01; "
            "the transfer direction and consequent are correct); (2) advisory -- "
            "regularity.must_not_conflate[0] C0:151 'No containment with C2 or C0 is asserted "
            "here' is stale against the ledger and against VARIANT_REGISTRY v2.0 H2LOC, which "
            "defines H2LOC with the continuity conjunct that makes the chain exact. The SCC axis "
            "is otherwise clean: 23 consistency checks pass, both chain declarations agree, and "
            "the repaired F0 meaning_C2 agrees with the derived order."),
        "needed_to_unblock": (
            "Lead-formulation applies the two mechanical C0 edits in schemas/af_scc_c0_vacuum.yaml "
            "('strictly larger' -> 'strictly smaller' at C0:245; scope or replace the C0:151 "
            "denial), re-freezes with a new sha256, and re-runs: python3 artifacts/worker-058/"
            "contain_derive/derive_containment.py --root . ; PASS (hard=0, advisory=0) certifies "
            "the repair. Mutant M1_both_repairs in sensitivity_selftest.json demonstrates the "
            "acceptance. Do not hand-merge; publish one revision."),
        "evidence_refs": [
            "schemas/af_scc_c0_vacuum.yaml#%s" % c0_sha,
            "schemas/af_scc_c0_vacuum.yaml:245",
            "schemas/af_scc_c0_vacuum.yaml:151",
            "artifacts/formulation/VARIANT_REGISTRY.json#%s" % reg_sha,
            "artifacts/worker-058/contain_derive/containment_derivation.json#%s"
            % hashes[REL["containment_derivation_json"]],
            "artifacts/worker-058/contain_derive/_scratch/M1_both_repairs/result.json",
        ],
        "expected_information_gain": (
            "high: turns the last open C0 containment repair into a one-command derivation "
            "acceptance test whose warrant is machine-checked, so the repair no longer rests on "
            "the chain being taken as an axiom"),
    })

    events.append({
        "event_id": "w058-cd-%s-status" % stamp,
        "event_type": "status",
        "created_at": now,
        "actor": "worker-058",
        "node_id": NODE,
        "group_id": "formulation",
        "class_id": CLASSES,
        "gate": "G-FORM",
        "status": "active",
        "hours": 0.6,
        "summary": (
            "W058-CONTAIN-DERIVE-04 complete at worker level: the SCC containment chain is "
            "re-derived from the frozen definitional base (3/3 links derived; L3 exact only under "
            "the VARIANT_REGISTRY H2LOC continuity conjunct, shown by mutant M4). At C0 %s / C2 %s "
            "/ registry %s / FROZEN rev%s: FAIL hard=1 advisory=1 consistent=23; the single hard "
            "finding is the known C0:245 class-size inversion, now with a derivation warrant; "
            "C0:151 is a stale containment denial. Sensitivity 12/12 including the pre-registered "
            "both-repairs acceptance (M1 -> PASS hard=0, 3/3 links derived). Boundary: "
            "definitional consistency only; no math truth, node completion or gate verdict "
            "claimed." % (c0_sha[:12], c2_sha[:12], reg_sha[:12], frozen_rev)),
        "evidence_refs": [
            "artifacts/worker-058/contain_derive/containment_derivation.json#%s"
            % hashes[REL["containment_derivation_json"]],
            "artifacts/worker-058/contain_derive/sensitivity_selftest.json#%s"
            % hashes[REL["containment_derivation_selftest_json"]],
            "schemas/af_scc_c0_vacuum.yaml#%s" % c0_sha,
        ],
        "next_falsifier": (
            "Re-run after the two C0 repairs land. Falsified if the unmodified checker still "
            "returns hard>0 at the new hash, or if a chain link becomes under_justified with the "
            "registry continuity conjunct still present."),
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
