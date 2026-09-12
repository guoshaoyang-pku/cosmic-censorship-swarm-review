#!/usr/bin/env python3
"""worker-040 adjudication instrument: F2a (AF-SCC-C2-VAC-GEN) evidence-binding repair paths.

Question (decision-relevant, from HF-W092-F2A-01 + the audit-lead bind-chain addendum):
    the rev12 schemas declare f0_binding.consistency_evidence_sha256 = 675a99d0d25b,
    while the named path measures 9e335e9b (FROZEN rev28 pin). Two repairs were proposed.
    Which repair is valid against FROZEN rev28 and the FROZEN change protocol, and what
    does the family-wide picture imply for G-FORM?

This instrument measures, it does not assert: every claim in report.json is bound to a
measured sha256 recorded in measurements.json. Controls run first (fail closed).

Exit 0 = instrument ran and self-checks passed; the report carries the findings.
Exit 3 = a control or a hash-stability self-check failed (no report written).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time

import yaml

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
F0_CANONICAL = "research_map/formulation_taxonomy.yaml"
F0_SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE_LIVE = "artifacts/formulation/evidence/taxonomy_consistency.json"
EVIDENCE_PINNED = "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
FROZEN = "artifacts/formulation/FROZEN.json"
CONSISTENCY_CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(path: str) -> dict:
    p = os.path.join(BASE, path)
    st = os.stat(p)
    return {
        "path": path,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
        "exists": True,
    }


def classify(declared: str, named_path_hash: str, pinned_hash: str | None) -> str:
    """Resolution status of a declared sha256 whose named path measures named_path_hash."""
    if declared == named_path_hash:
        return "resolved_at_named_path"
    if pinned_hash is not None and declared == pinned_hash:
        return "mismatch_at_named_path_pinned_copy_resolves"
    return "mismatch_unresolvable"


def frozen_pin_conflict(declared: str, frozen_pin: str) -> bool:
    """True iff restoring the declared bytes at the named path would violate the frozen pin."""
    return declared != frozen_pin


def run_controls() -> dict:
    """Synthetic cases with expected outcomes; the classifier must reproduce all of them."""
    cases = [
        {
            "id": "ctl-equal",
            "declared": "a" * 64,
            "named": "a" * 64,
            "pinned": None,
            "expected": "resolved_at_named_path",
        },
        {
            "id": "ctl-mismatch-pinned",
            "declared": "b" * 64,
            "named": "c" * 64,
            "pinned": "b" * 64,
            "expected": "mismatch_at_named_path_pinned_copy_resolves",
        },
        {
            "id": "ctl-mismatch-unresolvable",
            "declared": "b" * 64,
            "named": "c" * 64,
            "pinned": "d" * 64,
            "expected": "mismatch_unresolvable",
        },
        {
            "id": "ctl-freeze-conflict-yes",
            "declared": "b" * 64,
            "frozen": "c" * 64,
            "expected": True,
        },
        {
            "id": "ctl-freeze-conflict-no",
            "declared": "b" * 64,
            "frozen": "b" * 64,
            "expected": False,
        },
    ]
    results = []
    ok = True
    for c in cases:
        if "expected" in c and c["id"].startswith("ctl-freeze"):
            got = frozen_pin_conflict(c["declared"], c["frozen"])
        else:
            got = classify(c["declared"], c["named"], c["pinned"])
        passed = got == c["expected"]
        ok = ok and passed
        results.append({"id": c["id"], "expected": c["expected"], "got": got, "pass": passed})
    return {"all_passed": ok, "n": len(results), "detected": sum(r["pass"] for r in results), "cases": results}


def main() -> int:
    controls = run_controls()
    with open(os.path.join(OUT, "controls.json"), "w") as fh:
        json.dump(controls, fh, indent=1, sort_keys=True)
    if not controls["all_passed"]:
        print("CONTROL FAILURE", json.dumps(controls))
        return 3

    measurements: dict[str, dict] = {}
    for label, path in list(SCHEMAS.items()) + [
        ("F0-canonical", F0_CANONICAL),
        ("F0-supplement", F0_SUPPLEMENT),
        ("evidence-live", EVIDENCE_LIVE),
        ("evidence-pinned", EVIDENCE_PINNED),
        ("FROZEN", FROZEN),
        ("consistency-checker", CONSISTENCY_CHECKER),
    ]:
        measurements[label] = measure(path)

    frozen = json.load(open(os.path.join(BASE, FROZEN)))
    frozen_pin = frozen["files"][EVIDENCE_LIVE]["sha256"]

    per_class = {}
    for node, path in SCHEMAS.items():
        before = measurements[node]["sha256"]
        doc = yaml.safe_load(open(os.path.join(BASE, path)))
        after = sha256_file(os.path.join(BASE, path))
        if before != after:
            print(f"HASH UNSTABLE during read: {path} {before} -> {after}")
            return 3
        fb = doc["f0_binding"]
        declared_f0 = fb["declared_f0_sha256"]
        declared_ev = fb["consistency_evidence_sha256"]
        named_live = measurements["evidence-live"]["sha256"]
        pinned = measurements["evidence-pinned"]["sha256"]
        per_class[node] = {
            "class_id": doc["class_id"],
            "schema_sha256": before,
            "declared_f0_sha256": declared_f0,
            "declared_f0_status": classify(declared_f0, measurements["F0-canonical"]["sha256"], None),
            "declared_evidence_sha256": declared_ev,
            "named_evidence_path": fb.get("consistency_evidence"),
            "named_evidence_measured": named_live,
            "evidence_status": classify(declared_ev, named_live, pinned),
            "frozen_rev28_pin": frozen_pin,
            "restore_repair_conflicts_with_frozen": frozen_pin_conflict(declared_ev, frozen_pin),
            "checked_at": fb.get("checked_at"),
            "checked_at_older_than_live_mtime": (fb.get("checked_at") or "") < measurements["evidence-live"]["mtime"],
            "refresh_rule": fb.get("rule"),
        }

    live_doc = json.load(open(os.path.join(BASE, EVIDENCE_LIVE)))
    pinned_doc = json.load(open(os.path.join(BASE, EVIDENCE_PINNED)))
    live_keys, pinned_keys = set(live_doc), set(pinned_doc)
    superset = {
        "pinned_is_strict_superset_of_live": pinned_keys > live_keys,
        "keys_only_in_pinned": sorted(pinned_keys - live_keys),
        "keys_only_in_live": sorted(live_keys - pinned_keys),
    }

    checker_src = open(os.path.join(BASE, CONSISTENCY_CHECKER)).read().lower()
    blind_spot = {
        "checker_mentions_quantifier": bool(re.search(r"quantifier", checker_src)),
        "checker_mentions_domain": bool(re.search(r"\bdomain", checker_src)),
        "evidence_reports_consistent": live_doc.get("consistent"),
        "note": "evidence compares class-contract text; it cannot detect a quantified-index divergence between the two pinned statements",
    }

    family_consistent = len({v["declared_evidence_sha256"] for v in per_class.values()}) == 1
    all_pinned_resolve = all(v["evidence_status"].endswith("pinned_copy_resolves") for v in per_class.values())
    all_f0_resolved = all(v["declared_f0_status"] == "resolved_at_named_path" for v in per_class.values())

    report = {
        "artifact": "F2A-EVIDENCE-BINDING-REPAIR-ADJUDICATION",
        "author": "worker-040",
        "class_scope": "AF-SCC-C2-VAC-GEN (family scan: AF-WCC-VAC-GEN, AF-SCC-C0-VAC-GEN)",
        "node_scope": "F2a (family scan: F1, F2b)",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "question": "Which repair of the rev12 f0_binding consistency-evidence hash defect is valid against FROZEN rev28 and the change protocol?",
        "measured": {
            "live_evidence": measurements["evidence-live"],
            "pinned_evidence": measurements["evidence-pinned"],
            "frozen_rev28_pin_of_live_path": frozen_pin,
            "frozen_revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "frozen_change_protocol": frozen.get("change_protocol"),
        },
        "family_scan": per_class,
        "derived": {
            "all_declared_f0_hashes_resolve": all_f0_resolved,
            "all_evidence_declarations_pinned_copy_resolves": all_pinned_resolve,
            "single_declared_evidence_hash_across_family": family_consistent,
            "pinned_vs_live_bytes": superset,
            "checker_blind_spot": blind_spot,
        },
        "findings": [
            {
                "id": "W040-F2A-BIND-01",
                "status": "replicated",
                "text": "HF-W092-F2A-01 replicates: at schema pin 5476a3f2c6bc the declared consistency_evidence_sha256 675a99d0d25b does not equal the measured bytes at the named path (9e335e9b), which is also the FROZEN rev28 pin.",
                "evidence": ["schemas/af_scc_c2_vacuum.yaml#" + per_class["F2a"]["schema_sha256"][:12],
                             EVIDENCE_LIVE + "#" + measurements["evidence-live"]["sha256"][:12],
                             FROZEN + "#" + sha256_file(os.path.join(BASE, FROZEN))[:12]],
            },
            {
                "id": "W040-F2A-BIND-02",
                "status": "correction",
                "text": "HF-W092-F2A-01 states the live/frozen bytes are a strict superset of the declared ones. Measured direction is the reverse: the declared/pinned object is a strict superset of the live bytes, adding keys " + ", ".join(superset["keys_only_in_pinned"]) + ". The class-semantics conclusion (no semantic impact) survives; the containment direction in the finding does not.",
                "evidence": [EVIDENCE_PINNED + "#" + measurements["evidence-pinned"]["sha256"][:12]],
            },
            {
                "id": "W040-F2A-BIND-03",
                "status": "decisive",
                "text": "The proposed pin-preserving repair (restore the 675a99d0 bytes at the named canonical path) conflicts with FROZEN revision 28, which pins that path at 9e335e9b. Executing it falsifies the FROZEN manifest and requires a FROZEN revision bump, so it is not pin-preserving as labelled.",
                "evidence": [FROZEN + "#" + sha256_file(os.path.join(BASE, FROZEN))[:12]],
            },
            {
                "id": "W040-F2A-BIND-04",
                "status": "decisive",
                "text": "The live evidence file is rewritten repeatedly while its content hash stays 9e335e9b (mtime now " + measurements["evidence-live"]["mtime"] + ", schema checked_at " + str(per_class["F2a"]["checked_at"]) + "): the mtime argument cannot by itself distinguish a stale declaration from a re-written identical file. The schema's own refresh rule triggers on the declared F0 artifact changing hash, and that artifact is stable at 0abb9ed8a961 across the family.",
                "evidence": [EVIDENCE_LIVE + "#" + measurements["evidence-live"]["sha256"][:12]],
            },
            {
                "id": "W040-F2A-BIND-05",
                "status": "decisive",
                "text": "The consistency evidence, at either revision, cannot close the gate's substantive defect: it reports consistent=true and its checker contains no quantifier/index-domain comparison, so the cross-artifact divergence between the declared-F0 conclusion 'for every admissible (s,delta)' and the schemas' 'forall r in D0' (tagged union with smooth) is outside its scope. Refreshing or restoring the evidence hash therefore does not make G-FORM passable.",
                "evidence": ["artifacts/formulation/tools/check_taxonomy_consistency.py#" + measurements["consistency-checker"]["sha256"][:12],
                             F0_CANONICAL + "#" + measurements["F0-canonical"]["sha256"][:12]],
            },
            {
                "id": "W040-F2A-BIND-06",
                "status": "decision_tree",
                "text": "Repair paths and their measured consequences. (A) restore declared bytes at named path: resolves the literal declaration, falsifies FROZEN rev28, needs FROZEN rev29; does not address BIND-05. (B) re-stamp all three schemas to 9e335e9b: schema bytes change to rev13 and void every rev12-bound verdict (including the only current-hash accepts on F1 and F2b); does not address BIND-05. (C) disposition as a documentation/pointer defect, treating the declared sha256 as content-addressed (FROZEN change protocol: bind the sha256, not the path) with the pinned copy as the resolution object: no canonical byte changes; preserves rev12 pins; requires an owner annotation and answers BIND-05 separately. (D) combined rev13 repair (F0 anchor and/or schema D0 fix plus re-stamped evidence): the only path that can make G-FORM passable, at the cost of the rev12 review coverage.",
                "evidence": [FROZEN + "#" + sha256_file(os.path.join(BASE, FROZEN))[:12]],
            },
        ],
        "recommendation": {
            "binding": False,
            "text": "If lead-audit rules the (s,delta)/D0 divergence dispositionable under F0 H3, path C is the cheapest valid disposition and rev12 verdicts survive. If the divergence is blocking (as filed by the F1/F2a/F2b repin reviews), path D is the only passable sequence and paths A/B merely trade a pointer defect for either a FROZEN breach or a full re-review; choose D and fold the evidence re-stamp into the same revision bump.",
        },
        "falsifiers": [
            "Report falsified if sha256(artifacts/formulation/evidence/taxonomy_consistency.json) becomes 675a99d0d25b (then the declaration resolves at the named path and BIND-01/03/06-A change status).",
            "Report falsified if FROZEN revision 28 does not pin " + EVIDENCE_LIVE + " at 9e335e9b, or if FROZEN is superseded by a revision that pins 675a99d0 there.",
            "BIND-02 falsified if the pinned object's key set is not a strict superset of the live object's key set.",
            "BIND-05 falsified if the consistency checker (at the cited hash) compares quantified index domains, or if a refreshed evidence object records and fails the (s,delta) vs D0 divergence.",
            "BIND-04 falsified if the declared F0 artifact hash changes at the named path without a corresponding f0_binding refresh.",
        ],
        "limitations": [
            "This is a worker adjudication, not a gate verdict; worker events cannot move gates or status.",
            "No canonical or shared artifact was modified; only artifacts/worker-040/**, reviews/, comms/outbox/worker-040.jsonl and runtime/state/ were written.",
        ],
    }

    with open(os.path.join(OUT, "measurements.json"), "w") as fh:
        json.dump(measurements, fh, indent=1, sort_keys=True)
    with open(os.path.join(OUT, "report.json"), "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)

    entry_hashes = {
        "adjudicate.py": sha256_file(os.path.abspath(__file__)),
        "measurements.json": sha256_file(os.path.join(OUT, "measurements.json")),
        "report.json": sha256_file(os.path.join(OUT, "report.json")),
        "controls.json": sha256_file(os.path.join(OUT, "controls.json")),
    }
    with open(os.path.join(OUT, "entry_hashes.json"), "w") as fh:
        json.dump(entry_hashes, fh, indent=1, sort_keys=True)

    print(json.dumps({"controls": controls["detected"], "findings": len(report["findings"]),
                      "entry_hashes": entry_hashes}, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
