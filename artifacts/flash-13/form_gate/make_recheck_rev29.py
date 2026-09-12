#!/usr/bin/env python3
"""Build the FROZEN-rev29 R03 binding record for FORM-GATE-01 (G-CLASSBIND).

One bounded class-bound task (F1 / AF-WCC-VAC-GEN, G-CLASSBIND): re-run the independent
gate at the rev13 canonical bytes under FROZEN rev29, and repair the R03 under-detection
found there.  The record binds, at measured hashes:

  * the pre-hardening gate 1.1 canonical pass (gate_report_rev29.json),
  * the corrected gate 1.2 canonical run (gate_report_rev29_r3.json) in which WCC fails R03
    while C2/C0 pass, at byte-identical canonical hashes,
  * the fixture-suite controls including the new single-rule mutant m25,
  * an independent cross-check of worker-064's E1a one-clause repair candidate.

No self-hash: the record's sha256 is carried by the artifact event that publishes it
(same convention as FROZEN.json).  The builder re-measures every input and records drift
instead of assuming it.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "canonical_recheck_rev29.json"

CANON = {
    "AF-WCC-VAC-GEN": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
MIRRORS = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
E1A = "artifacts/worker-064/r03_cause/patch_candidates/wcc_candidate_E1a.yaml"


def sha(rel: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / rel, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(rel: str):
    return json.loads((ROOT / rel).read_text())


def class_view(report: dict) -> dict:
    out = {}
    for res in report["results"]:
        fails = {rule: v["detail"] for rule, v in res["per_rule"].items() if v["status"] == "fail"}
        out[res["class_id"]] = {
            "sha256": res["sha256"],
            "frozen_match": res.get("frozen_match"),
            "verdict": res["verdict"],
            "failed_rules": sorted(fails),
            "failure_detail": fails,
            "rules_skipped": res.get("rules_skipped", []),
        }
    return out


frozen_json = load("artifacts/formulation/FROZEN.json")
report_11 = load("artifacts/flash-13/form_gate/gate_report_rev29.json")
report_12 = load("artifacts/flash-13/form_gate/gate_report_rev29_r3.json")
suite = load("artifacts/flash-13/form_gate/fixture_suite_report.json")
e1a = load("artifacts/flash-13/form_gate/e1a_crosscheck.json")
manifest = load("artifacts/flash-13/form_gate/fixtures/manifest.json")

measured = {rel: sha(rel) for rel in CANON.values()}
mirror_equal = {cid: (measured[CANON[cid]] == sha(MIRRORS[cid])) for cid in CANON}
frozen_pins = {rel: frozen_json["files"].get(rel, {}).get("sha256") for rel in CANON.values()}
must_not_be_frozen = frozen_json["files"].get(E1A, {}).get("sha256")

# Drift is recorded, never assumed away: canonical bytes are the live bytes at build time,
# and the two gate reports must have measured those same bytes.
report_11_sha = {r["class_id"]: r["sha256"] for r in report_11["results"]}
report_12_sha = {r["class_id"]: r["sha256"] for r in report_12["results"]}
drift = {
    "canonical_vs_frozen_pin": {cid: measured[CANON[cid]] != frozen_pins[CANON[cid]] for cid in CANON},
    "canonical_vs_report_11": {cid: measured[CANON[cid]] != report_11_sha.get(cid) for cid in CANON},
    "canonical_vs_report_12": {cid: measured[CANON[cid]] != report_12_sha.get(cid) for cid in CANON},
    "mirror_byte_identical": mirror_equal,
    "e1a_inside_frozen_manifest": must_not_be_frozen is not None,
}

record = {
    "actor": "deepseek-flash-13",
    "task_id": "F13-G-CLASSBIND-REV29-R03",
    "gate_id": "G-CLASSBIND",
    "node_id": "F1",
    "class_ids": list(CANON),
    "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "assignment_source": (
        "Standing FORM-GATE-01 card assign-FORM-GATE-01-20260911T2331 (G-CLASSBIND) plus "
        "lead-formulation follow-ups requiring a frozen-hash run and deltas only. No new inbox "
        "card existed for deepseek-flash-13; this is one bounded class-bound task, reported, "
        "not a node completion and not a gate self-pass."
    ),
    "frozen": {
        "path": "artifacts/formulation/FROZEN.json",
        "sha256": sha("artifacts/formulation/FROZEN.json"),
        "revision": frozen_json["revision"],
        "frozen_at": frozen_json["frozen_at"],
    },
    "spec": {
        "path": "artifacts/formulation/rule_spec.json",
        "sha256": sha("artifacts/formulation/rule_spec.json"),
        "spec_id": "FORM-RULE-SPEC",
        "gate_reported_version": report_12.get("spec"),
    },
    "gate": {
        "path": "artifacts/flash-13/form_gate/check_class_schema.py",
        "sha256": sha("artifacts/flash-13/form_gate/check_class_schema.py"),
        "version": "1.2",
        "supersedes_sha256": "ad7d120b84499a92abf46302d71011fc2da7574ceab3b0d870494ef562ca22e1",
        "change": ("R03 now enforces the published 'formal is a single sentence using those "
                   "binders' require with a whitespace-normalised literal-usage test; disclosed "
                   "as literal, so alpha-renaming adjudication stays with the rule owner."),
    },
    "canonical_bytes": {
        cid: {"authoring": CANON[cid], "mirror": MIRRORS[cid], "sha256": measured[CANON[cid]],
              "mirror_byte_identical": mirror_equal[cid], "frozen_pin": frozen_pins[CANON[cid]]}
        for cid in CANON
    },
    "bisect_same_bytes_two_gates": {
        "note": ("Both reports measured the byte-identical rev13 canonical files listed above; "
                 "only the gate revision differs."),
        "gate_1_1_report": {"path": "artifacts/flash-13/form_gate/gate_report_rev29.json",
                            "sha256": sha("artifacts/flash-13/form_gate/gate_report_rev29.json"),
                            "verdict": report_11["verdict"], "classes": class_view(report_11)},
        "gate_1_2_report": {"path": "artifacts/flash-13/form_gate/gate_report_rev29_r3.json",
                            "sha256": sha("artifacts/flash-13/form_gate/gate_report_rev29_r3.json"),
                            "verdict": report_12["verdict"], "classes": class_view(report_12)},
        "delta": ("AF-WCC-VAC-GEN flips pass -> fail on exactly R03 (quantifiers.ordered[5] "
                  "declares '(q,t0)'; the formal sentence renders the quantifier variable-wise); "
                  "AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN are unchanged pass, their tuple "
                  "binders occur literally in their formal sentences."),
    },
    "controls": {
        "fixture_suite_report": {
            "path": "artifacts/flash-13/form_gate/fixture_suite_report.json",
            "sha256": sha("artifacts/flash-13/form_gate/fixture_suite_report.json"),
            "summary": suite["summary"],
        },
        "m25_mutant": {
            "path": "artifacts/flash-13/form_gate/fixtures/m25_wcc_binder_unused.yaml",
            "sha256": sha("artifacts/flash-13/form_gate/fixtures/m25_wcc_binder_unused.yaml"),
            "diff_from_conforming_wcc": "quantifiers.ordered[2].binder 'p' -> '(p,t0)'",
            "expected_rule": "R03",
        },
        "fixtures_manifest": {
            "path": "artifacts/flash-13/form_gate/fixtures/manifest.json",
            "sha256": sha("artifacts/flash-13/form_gate/fixtures/manifest.json"),
            "mutants": len(manifest["mutants"]),
        },
        "e1a_crosscheck": {
            "path": "artifacts/flash-13/form_gate/e1a_crosscheck.json",
            "sha256": sha("artifacts/flash-13/form_gate/e1a_crosscheck.json"),
            "candidate": E1A,
            "candidate_sha256": sha(E1A),
            "verdict": e1a["verdict"],
            "note": ("worker-064's one-clause E1a repair candidate (external to this worker) "
                     "passes the corrected gate R01-R16; the corrected R03 is therefore not a "
                     "blanket reject and the canonical failure is repairable by rendering the "
                     "declared tuple binder in quantifiers.formal."),
        },
    },
    "cross_references_external": [
        {"actor": "worker-064", "event_id": "w064-r03-01-claim-c1",
         "artifact": "artifacts/worker-064/r03_cause/report.json",
         "claim": "adopted semantic auditor rejects canonical WCC at rev29 on exactly R03, binder '(q,t0)' absent from formal"},
        {"actor": "worker-080", "event_id": "w080-sr-20260912T004243-blocker-f1r03",
         "claim": "independent F1 R03 blocker reproduced"},
        {"actor": "worker-16", "event_id": "w16-R03-ADJ-01",
         "claim": "R03 adjudication requested"},
    ],
    "scope": ("Structural R01-R16 conformance only, on the three canonical schemas and the "
              "fixture controls. Not a mathematical verdict, not a citation verdict, not a "
              "node completion, not a gate verdict. The R03 failure is a formal-sentence "
              "rendering defect (declared binder unused), not evidence against the rev12 "
              "mathematical repair."),
    "falsifier": (
        "A reviewer shows (a) the canonical WCC formal sentence does use the declared binder "
        "'(q,t0)' under the rule owner's intended reading, or (b) the R03 literal-usage test "
        "rejects a schema the rule owner certifies as conforming after alpha-renaming, or "
        "(c) any canonical file byte changes (frozen_match=False). Any of these voids the "
        "R03 finding and requires a re-run at the new bytes."
    ),
    "next_falsifier": (
        "After the owner repairs the WCC formal rendering (worker-064 E1a/E1b) the canonical "
        "WCC hash changes: re-run this gate at the new hash and re-review F1; a repair that "
        "keeps the declared binder unused must keep failing R03."
    ),
    "drift_check": drift,
}

OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
print(f"wrote {OUT.relative_to(ROOT)}")
print(json.dumps({"verdict_1_1": report_11["verdict"], "verdict_1_2": report_12["verdict"],
                  "wcc_fail_rules": class_view(report_12)["AF-WCC-VAC-GEN"]["failed_rules"],
                  "suite": suite["summary"], "drift": drift}, indent=1))
