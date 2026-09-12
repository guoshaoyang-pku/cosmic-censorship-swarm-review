#!/usr/bin/env python3
"""Pre-registration for W006-R03-CAND-HEADTOHEAD-01.

Written and hashed BEFORE any corpus fixture is run against any candidate. A preflight
on the three LIVE canonical controls only was performed at 01:09 (frozen rejects WCC on
R03; both candidates and frozen accept C0/C2); no corpus fixture was scored before this
file existed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


VARIANTS = {
    "frozen": "artifacts/worker-06/spec_conformance_audit.py",
    "cand_r03v2": "artifacts/worker-06/r03v2/audit_r03v2.py",
    "cand_004": "artifacts/worker-004/f1_r03_repair/patched/spec_conformance_audit.py",
}
prereg = {
    "task_id": "W006-R03-CAND-HEADTOHEAD-01",
    "worker": "worker-006",
    "created_at": datetime.now(CST).isoformat(timespec="seconds"),
    "node_id": "A1",
    "gate": "G-CLASSBIND",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "question": "At the LIVE FROZEN rev29 bytes, on a fresh binder-layout corpus written "
                "after both repairs were published, which R03 repair carries false "
                "positives / false negatives, and does either preserve frozen catches?",
    "hypothesis": "R03-v2 (binder-head co-binding within span=80) has 0 primary FP and 0 "
                  "primary FN but over-rejects comma-coordinated and long-span legitimate "
                  "binders (edge probes). The worker-004 patch (component-wise whole-word) "
                  "has 0 primary FP on the corpus but accepts head-scope, empty-tuple and "
                  "non-identifier-bound cases (primary FN) while over-rejecting nothing "
                  "measured here.",
    "candidates": {
        label: {"path": rel, "sha256": sha(ROOT / rel),
                "rule": {"cand_r03v2": "binder-head co-binding, span=80, ordered ids",
                         "cand_004": "every binder token present as a whole word in formal",
                         "frozen": "literal substring of binder in formal"}[label]}
        for label, rel in VARIANTS.items()
    },
    "pins": {
        "schemas/af_wcc_vacuum.yaml": sha(ROOT / "schemas/af_wcc_vacuum.yaml"),
        "schemas/af_scc_c2_vacuum.yaml": sha(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
        "schemas/af_scc_c0_vacuum.yaml": sha(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
        "artifacts/formulation/rule_spec.json": sha(ROOT / "artifacts/formulation/rule_spec.json"),
        "artifacts/formulation/FROZEN.json": sha(ROOT / "artifacts/formulation/FROZEN.json"),
    },
    "corpus": {
        "manifest": "artifacts/worker-06/r03headtohead/fixture_manifest.json",
        "manifest_sha256": sha(HERE / "fixture_manifest.json"),
        "fixtures_dir": "artifacts/worker-06/r03headtohead/fixtures",
        "scored": {"pos": 5, "neg": 6},
        "edge_probes": 2,
        "derived_regression_set": {
            "path": "artifacts/formulation/fixtures/negative/*.yaml",
            "n": len(list((ROOT / "artifacts/formulation/fixtures/negative").glob("*.yaml"))),
            "note": "DERIVED, not held-out: the canonical gate negatives were used by the "
                    "R03-v2 author's own calibration; counts here are a regression check, "
                    "not an out-of-sample estimate.",
        },
        "out_of_sample_disclosure": "No fixture in this corpus is reused from "
                                    "artifacts/worker-06/r03v2/fixtures or from worker-004's "
                                    "f1_r03_repair battery. Both repairs were published before "
                                    "this corpus was generated.",
    },
    "protocol": {
        "command": "python3 <variant.py> <fixture> --spec artifacts/formulation/rule_spec.json --json <raw>/<variant>__<fixture>.json",
        "fail_closed": ["any variant/spec/canonical/FROZEN pin drift before or after the run",
                        "any fixture byte drift from the manifest",
                        "any fixture whose frozen failed_rules is not a subset of {R03} "
                        "(format-dominated corpus -> INVALID)",
                        "any non-R03 failed-rule difference across variants on any file "
                        "(instrumentation error -> INVALID)",
                        "frozen control check failing (pos00/pos01 accept, pos02 reject R03)"],
        "preflight_disclosure": "At 01:09 only the three live canonical controls were run "
                               "(frozen: C0/C2 accept, WCC reject R03; both candidates: 3/3 "
                               "accept). No corpus fixture was run before preregistration.",
    },
    "scoring": {
        "primary": "for each candidate: FP = scored pos fixtures rejected; FN = scored neg "
                   "fixtures accepted. scored = true only in categories pos/neg.",
        "edge": "probe01/probe02 are spec-legitimate (expected accept) and scored separately "
                "as edge_FP; they measure each candidate's pre-declared residue.",
        "regression": "on the 31 canonical gate negatives, count frozen-R03 rejects that the "
                      "candidate no longer rejects, and print the frozen rule detail to "
                      "classify the literal-tuple FP family vs substantive catches.",
        "adoption_rule_measured_not_wielded": "A candidate is measured SAFE at these bytes iff "
                                              "primary FP = 0 and primary FN = 0 and it accepts "
                                              "3/3 live canonicals and loses no substantive "
                                              "frozen gate-negative catch. The verdict is the "
                                              "counts; adoption is the owner's decision.",
    },
    "falsifier": "This measurement is falsified if any pinned byte or fixture byte drifts "
                 "during the run; if the frozen control check fails; if any fixture fails a "
                 "non-R03 rule under any variant (format-dominated corpus); or if the "
                 "recorded raw JSON does not reproduce from the recorded command lines.",
    "not_claimed": "no gate verdict, no node completion, no theorem, no physics result, no "
                   "recommendation to adopt either candidate",
}
out = HERE / "preregistration.json"
out.write_text(json.dumps(prereg, indent=1) + "\n")
print(json.dumps({"preregistration": str(out), "sha256": sha(out)}, indent=1))
