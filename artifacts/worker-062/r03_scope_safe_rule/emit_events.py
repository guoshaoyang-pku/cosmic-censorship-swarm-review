#!/usr/bin/env python3
"""Write CHECKPOINT.json, then append the W062 R03 scope-safe-rule events to the outbox.

Idempotent: existing event_ids in comms/outbox/worker-062.jsonl are skipped.
No canonical/instrument path is written; only this task dir and the worker's own outbox.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTBOX = ROOT / "comms/outbox/worker-062.jsonl"
LABEL = "w062-r03scope-" + datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%dT%H%M")
CST = timezone(timedelta(hours=8))

TASK = "W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01"
NODES = ["F1", "F2a", "F2b"]
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


BASE = {
    "actor": "worker-062",
    "node_id": "F1",
    "nodes": NODES,
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": CLASSES,
    "gate": "G-FORM",
    "task_id": TASK,
}

REPORT = json.loads((HERE / "report.json").read_text())
AMEND = json.loads((HERE / "AMENDMENT_01.json").read_text())
E4_HASH = REPORT["tool_hashes"]["E4_scope_aware"]
MATRIX_ROWS = json.loads((HERE / "matrix.json").read_text())["rows"]

ARTIFACTS = [
    ("preregistration", HERE / "PREREGISTRATION.json", "preregistration",
     "Pre-registered pins, variants, expected matrix, expectations E1-E13, controls C1-C8, decision and stop rules."),
    ("deterministic_harness", HERE / "run_scope_safe_rule.py", "harness",
     "Pin-gated sandbox harness: builds baseline/E3/E4/E4-noscope from pinned bytes, generates variants, runs the 4x11x2 matrix and all controls."),
    ("artifact_report", HERE / "report.json", "report",
     "Full machine report: per-cell verdicts/failed rules/doc hashes, pins pre/post, tool hashes, expectations, controls."),
    ("matrix", HERE / "matrix.json", "matrix",
     "Compact 4-tool x 11-target matrix."),
    ("controls", HERE / "controls.json", "controls",
     "Control table C1-C8 incl. malformed-document control."),
    ("amendment", HERE / "AMENDMENT_01.json", "amendment",
     "Disclosed post-hoc E11 instrument correction (1 unified-diff hunk) + direct-canonical-bytes corroboration."),
    ("amendment_harness", HERE / "amend_e11_hunk_count.py", "amendment-harness",
     "Difflib hunk recount and direct run on published canonical F1 bytes; post-hoc, no verdict change."),
    ("candidate_tool", HERE / "sandbox/tools/E4/spec_conformance_audit.py", "candidate-E4",
     "E4 scope-aware R03 candidate bytes (sandbox only; live stage-2 instrument untouched and unpinned in FROZEN rev29)."),
    ("documentation", HERE / "README.md", "readme",
     "Question, method, matrix, controls, E11 disclosure, recommendation and scope limits."),
    ("entry_hashes", HERE / "entry_hashes.json", "entry-hashes",
     "Declared sha256 of the core deliverables."),
]


def main():
    stamp = now()
    entry_hashes = {rel(p): sha(p) for _, p, _, _ in ARTIFACTS}

    checkpoint = {
        "checkpoint_id": f"worker-062-r03scope-{stamp}",
        "task_id": TASK,
        "worker": "worker-062",
        "created_at": stamp,
        "node_id": "F1",
        "nodes": NODES,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASSES,
        "gate": "G-FORM",
        "verdict": REPORT["verdict"],
        "score": 3.5,
        "subjects": [
            {"node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
             "path": "schemas/af_wcc_vacuum.yaml",
             "sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d", "revision": 13},
            {"node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN",
             "path": "schemas/af_scc_c2_vacuum.yaml",
             "sha256": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe", "revision": 13},
            {"node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
             "path": "schemas/af_scc_c0_vacuum.yaml",
             "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c", "revision": 13},
        ],
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": REPORT["frozen_json_informational"]["pre"], "revision": 29},
        "pins": REPORT["inputs_pinned"],
        "input_pins_post": REPORT["input_pins_post"],
        "tool_hashes": REPORT["tool_hashes"],
        "matrix": MATRIX_ROWS,
        "expectations": REPORT["expectations"],
        "controls": REPORT["controls"],
        "e11_amendment": AMEND["A1_E11_instrument_correction"]["corrected_measurement"]["unified_diff_hunks"],
        "direct_canonical_corroboration": {k: f"{v['verdict']}/{','.join(v['failed_rules']) or '-'}"
                                           for k, v in AMEND["A2_direct_canonical_bytes_corroboration"]["results"].items()},
        "artifact_hashes": entry_hashes,
        "hard_failure_ids": ["HF-W062-R03SCOPE-01", "HF-W062-R03SCOPE-02"],
        "next_falsifier": "Run E4 against a scope-error rendering it accepts, or show it rejecting V1/V2/F2a/F2b, or move any input pin; also falsified if an adopted R03 revision is used as gate evidence while artifacts/worker-06/spec_conformance_audit.py stays unpinned in artifacts/formulation/FROZEN.json.",
    }
    (HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    cp_hash = sha(HERE / "CHECKPOINT.json")
    entry_hashes[rel(HERE / "CHECKPOINT.json")] = cp_hash
    ARTIFACTS.append(("checkpoint", HERE / "CHECKPOINT.json",
                      "Worker checkpoint: verdict PARTIAL, pins, matrix, E11 amendment, artifact hashes and falsifiers.",
                      "checkpoint"))

    ev = []
    common_refs = [f"{rel(HERE / 'report.json')}#{REPORT and sha(HERE / 'report.json')[:12]}",
                   f"{rel(HERE / 'PREREGISTRATION.json')}#{sha(HERE / 'PREREGISTRATION.json')[:12]}",
                   f"{rel(HERE / 'CHECKPOINT.json')}#{cp_hash[:12]}",
                   "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
                   "artifacts/worker-06/spec_conformance_audit.py#c79d8ab8440a",
                   "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py#3f69bc1eb27a",
                   "artifacts/formulation/FROZEN.json#815e08079aef"]

    def add(e):
        e["event_id"] = f"{LABEL}-{e['event_id']}"
        if not e.get("created_at"):
            e["created_at"] = stamp
        e.update(BASE)
        ev.append(e)

    add({"event_type": "status", "status": "active", "hours": 0.25, "event_id": "status-open",
         "summary": "No inbox card for worker-062 (relaunched slot). Took ONE bounded class-bound task on the live G-FORM critical path, "
                    "W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01: pre-registered, sandbox-only measurement of a scope-aware R03 amendment (E4) "
                    "that fixes the canonical-F1 literal-match false positive without the negation-scope over-acceptance the formulation lead measured for cand_E3.",
         "evidence_refs": common_refs,
         "next_falsifier": "Any E4 column cell deviating from the pre-registered matrix, or any input pin moving."})

    for kind, path, eid, summary in ARTIFACTS:
        h = sha(path)
        add({"event_type": "artifact", "event_id": f"artifact-{eid}",
             "artifact_type": kind, "path": rel(path), "sha256": h,
             "validation_status": "unverified",
             "artifact_refs": [f"{rel(path)}#{h[:12]}"],
             "evidence_refs": common_refs,
             "falsifier": "The file's measured sha256 differs from the one declared here.",
             "summary": f"{summary} sha256 {h[:12]}."})

    add({"event_type": "claim", "event_id": "claim",
         "conclusion_type": "formal_model",
         "statement": (
             "Artifact-and-checker measurement (not a mathematics or physics claim, not a theorem): at pinned bytes "
             "(canonical F1 d9cebb9404b2, frozen stage-2 auditor c79d8ab8440a, cand_E3 3f69bc1eb27a, rule spec 40f9bb9e657b), "
             "a pre-registered 4-tool x 11-target sandbox matrix with two deterministic runs per cell reproduces the formulation lead's "
             "scope finding (cand_E3 accepts the negation-scope-error rendering V3) and measures a scope-aware candidate E4 that accepts "
             "canonical frozen F1, its grouped/product/reordered equivalents, and canonical F2a/F2b, while rejecting V3, an unbound-restriction "
             "control, a shadow-quantifier control, a fully unbound control and a wrong-variable control. E4 replaces only the R03 binder block "
             "(one contiguous hunk, 28 changed lines): a non-literal composite binder passes iff the number of lexically located quantifier phrases "
             "equals the declared ordered-binder count, the phrase kind matches, and every binder variable occurs as a whole word inside that "
             "quantifier's own restriction phrase. All 13 pre-registered expectations except E11 hold and all 8 controls pass; E11 failed only because "
             "its hunk metric was implemented as a positional line comparison (446 changed lines), and a disclosed post-hoc amendment measures "
             "1 unified-diff hunk. Pre-registered verdict is therefore PARTIAL, not VALID. E4 is a sandbox candidate only; the stage-2 tool is unpinned "
             "in FROZEN rev29, so adoption requires pinning it in the same FROZEN revision."
         ),
         "assumptions": [
             "the FROZEN rev29 manifest, the three rev13 schemas, the rule spec 40f9bb9e657b and the two tool copies are the binding reference at measurement time",
             "all tools were invoked with the pinned --spec explicitly, so tool location does not change the rule set",
             "variants are canonical F1 with only the tail after 'with finite affine length: ' replaced; V0 is a YAML round-trip, and the direct canonical-bytes run in AMENDMENT_01 corroborates the same column",
             "this measures the stage-2 rule engine only; no end-to-end run_acceptance.py PASS is claimed",
             "no canonical, frozen, pinned or live-instrument byte was written; every write is under artifacts/worker-062/r03_scope_safe_rule/ or this worker's own outbox",
         ],
         "falsifier": "Show a run at the declared pins where E4 accepts a scope-error rendering, or rejects V1/V2/F2a/F2b, or any E4 matrix cell deviating from the pre-registered matrix; or show any input pin moving between T0 and T1.",
         "evidence_refs": common_refs + [f"{rel(HERE / 'matrix.json')}#{sha(HERE / 'matrix.json')[:12]}",
                                          f"{rel(HERE / 'AMENDMENT_01.json')}#{sha(HERE / 'AMENDMENT_01.json')[:12]}",
                                          f"{rel(HERE / 'sandbox/tools/E4/spec_conformance_audit.py')}#{E4_HASH[:12]}"],
         "artifact_refs": [f"{rel(HERE / 'report.json')}#{sha(HERE / 'report.json')[:12]}",
                           f"{rel(HERE / 'sandbox/tools/E4/spec_conformance_audit.py')}#{E4_HASH[:12]}"],
         "reviewed_sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"})

    add({"event_type": "review", "event_id": "review",
         "target_id": "F1@FROZEN-rev29-d9cebb9404b2 / R03 stage-2 rule (sandbox candidate E4)",
         "reviewer": "worker-062",
         "reviewer_role": "bounded execution worker (not the schema author, not the stage-2 author, not a gate verdict)",
         "verdict": "revise", "score": 3.5, "counts_as_full_schema_verdict": False,
         "reviewed_sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
         "summary": "Scope-aware R03 repair candidate review: revise 3.5. The pre-registered matrix matched cell-for-cell (4 tools x 11 targets, 2 runs/cell) and E4 is the first measured A-prime candidate: it accepts canonical F1 and rejects the scope-error, unbound-restriction and shadow-quantifier renderings that cand_E3 accepts, with F2a/F2b and literal-composite behaviour unchanged. Two hard findings below; neither is a defect of the E4 column.",
         "hard_failures": [
             {"id": "HF-W062-R03SCOPE-01", "name": "stage2_tool_unpinned_for_any_r03_adoption", "class_id": "AF-WCC-VAC-GEN",
              "severity": "blocking-adoption",
              "finding": "artifacts/worker-06/spec_conformance_audit.py (c79d8ab8440a) is wired by the pinned run_acceptance.py but has zero occurrences in artifacts/formulation/FROZEN.json; any R03 amendment would change gate outcomes with no pinned byte moving. E4 must not be adopted as gate evidence before the stage-2 tool is pinned in the same FROZEN revision (formulation-lead governance blocker, independently reproduced).",
              "falsifier": "Show the stage-2 tool pinned in FROZEN.json at a revision that also pins run_acceptance.py, or show an adopted R03 revision whose gate evidence is bound to an unpinned stage-2 tool (which would falsify the governance requirement, not the finding)."},
             {"id": "HF-W062-R03SCOPE-02", "name": "e11_hunk_metric_defect_disclosed", "class_id": "AF-WCC-VAC-GEN",
              "severity": "non-blocking-disclosed",
              "finding": "Expectation E11's 'one hunk' property was measured by positional line comparison and failed at 446 changed lines across a +22-line insertion; the property is true (difflib: 1 hunk, 28 changed lines) and the correction is recorded post-hoc in AMENDMENT_01.json without changing the pre-registered PARTIAL verdict.",
              "falsifier": "Show the E4 candidate differing from the baseline in more than one unified-diff hunk."},
         ],
         "findings": "Canonical F1 still fails R03 at the published pin; this task supplies a measured candidate, not a repair. Worker evidence only; no gate verdict, node status or validation_status set.",
         "evidence_refs": common_refs + [f"{rel(HERE / 'AMENDMENT_01.json')}#{sha(HERE / 'AMENDMENT_01.json')[:12]}"]})

    add({"event_type": "status", "status": "active", "hours": 0.05, "event_id": "status-complete",
         "summary": "CHECKPOINT + EXIT. W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01 complete at worker level: one bounded class-bound task, "
                    "4 tools x 11 targets x 2 deterministic runs, pre-registered matrix matched cell-for-cell (E13), 13/13 substantive expectations "
                    "with E11's metric defect disclosed and corrected post-hoc, 8/8 controls, 7/7 input pins stable pre/post, canonical/live bytes "
                    "untouched. Verdict PARTIAL under the pre-registered rule; E4 (sha256 3cd55a5373e8) is a sandbox candidate for the owner cascade, "
                    "conditional on pinning the stage-2 tool in the same FROZEN revision. No node status, validation_status or gate verdict set.",
         "evidence_refs": common_refs + [f"{rel(HERE / 'sandbox/tools/E4/spec_conformance_audit.py')}#{E4_HASH[:12]}"],
         "artifact_refs": [f"{rel(HERE / 'CHECKPOINT.json')}#{cp_hash[:12]}"],
         "next_falsifier": "Owner/controller: if A-prime is pursued, adopt E4 (or an equivalent scope requirement) and pin the stage-2 tool in the same FROZEN revision, then re-run the F1 r3 review at the new bytes; falsified by any scope-error rendering E4 accepts or by a gate accept that binds an unpinned stage-2 tool."})

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    new = [e for e in ev if e["event_id"] not in existing]
    if new:
        with OUTBOX.open("a") as f:
            for e in new:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"checkpoint CHECKPOINT.json sha256 {cp_hash[:16]}")
    print(f"events: {len(new)} appended, {len(ev) - len(new)} already present -> {OUTBOX}")
    for e in new:
        print(f"  {e['event_type']:9s} {e['event_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
