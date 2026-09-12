#!/usr/bin/env python3
"""W061-F1-REV12-GATE-03 emitter: writes REVIEW.json / REVIEW.md / CHECKPOINT.json and the
worker-061 outbox events.  Every hash is measured from disk at emission time."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
TASK = REPO / "artifacts/worker-061/f1_rev12_gate"
OUTBOX = REPO / "comms/outbox/worker-061.jsonl"
STATE = REPO / "runtime/state/w061_rev12_gate_checkpoint.json"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
F1 = "schemas/af_wcc_vacuum.yaml"
F1_SHA = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def line_of(text: str, needle: str, nth: int = 1) -> int:
    n = 0
    for i, l in enumerate(text.splitlines(), 1):
        if needle in l:
            n += 1
            if n == nth:
                return i
    return -1


def main():
    f1_text = (REPO / F1).read_text()
    probe = json.loads((TASK / "probe_rev12_output.json").read_text())
    rp = probe["repair_checks_rev12"]
    rule_matrix = probe["rule_matrix"]
    gate_matrix = probe["canonical_gate_matrix"]
    replay = probe["canonical_gate_replay_matrix"]

    reviewed_sha = sha(REPO / F1)
    assert reviewed_sha == F1_SHA, f"canonical F1 moved: {reviewed_sha}"

    fixtures = sorted((TASK / "fixtures").glob("*.yaml"))
    rule_reports = sorted((TASK / "rule_reports").glob("*.json"))
    gate_reports = sorted((TASK / "canonical_gate").glob("*.json"))

    lines = {
        "revision": line_of(f1_text, "revision: 12"),
        "revision_history": line_of(f1_text, "revision_history:"),
        "class_contract_pointer": line_of(f1_text, "class_contract_pointer:"),
        "class_contract_supplement_pointer": line_of(f1_text, "class_contract_supplement_pointer:"),
        "binder_r": line_of(f1_text, 'binder: "r"'),
        "formal_tail": line_of(f1_text, "not exists q in I+ and t0 in [0,T)"),
        "D5": line_of(f1_text, "    D5:"),
        "D5_tail": line_of(f1_text, "definition: \"pairs (q,t0) with q a point of I+"),
        "negation_tail": line_of(f1_text, "has a tail visible from I+."),
        "predicate_abbreviation": line_of(f1_text, "predicate_abbreviation:"),
        "statement_formal": line_of(f1_text, "statement_formal:"),
        "visibility_definition": line_of(f1_text, "  definition: \"a future-inextendible causal geodesic"),
        "f0_binding": line_of(f1_text, "f0_binding:"),
        "class_id": line_of(f1_text, "class_id: AF-WCC-VAC-GEN"),
    }

    artifact_paths = [
        TASK / "rule/check_predicate_consistency.py",
        TASK / "run_all.py",
        TASK / "probe_rev12_output.json",
        TASK / "pinned/af_wcc_vacuum.rev12.yaml",
        TASK / "pinned/formulation_taxonomy.canonical.yaml",
        TASK / "pinned/FROZEN.rev28.json",
        TASK / "pinned/KEY_MANIFEST.rev28.json",
        TASK / "pinned/hist/FROZEN.rev27.json",
        TASK / "pinned/hist/KEY_MANIFEST.rev27.json",
        TASK / "gate_replay/rev27/tool/check_class_schema.py",
        TASK / "gate_replay/rev28/tool/check_class_schema.py",
    ]
    artifact_hashes = {str(p.relative_to(REPO)): sha(p) for p in artifact_paths}
    fixture_hashes = {str(p.relative_to(REPO)): sha(p) for p in fixtures}
    report_hashes = {str(p.relative_to(REPO)): sha(p) for p in rule_reports}
    gate_hashes = {str(p.relative_to(REPO)): sha(p) for p in gate_reports}

    findings = [
        {
            "id": "F-01",
            "class": "positive",
            "axis": "HF-06 visibility predicate (rev11 hard failure)",
            "statement": ("REPAIRED at cce9c601. visibility.definition is the single-q TAIL predicate; "
                          "quantifiers.formal binds 'not exists q in I+ and t0 in [0,T) with "
                          "gamma([t0,T)) subset J^-(q) intersect M'; domains.D5 defines the (q,t0) tail "
                          "pairs and explicitly repudiates whole-curve containment as strictly stronger; "
                          "quantifiers.negation negates the tail predicate and visibility.negation_conclusion "
                          "carries 'for every q in I+ and every t0'."),
            "evidence_refs": [f"{F1}#L{lines['formal_tail']}", f"{F1}#L{lines['D5_tail']}",
                              f"{F1}#L{lines['negation_tail']}",
                              f"{F1}#sha256:{reviewed_sha[:12]}"],
            "probe": "rule_reports/POS_rev12_canonical.yaml.json -> R3,R4,R5,R6 pass",
        },
        {
            "id": "F-02",
            "class": "positive",
            "axis": "dangling AF_{I+} (rev11 hard failure)",
            "statement": ("REPAIRED: conclusion.predicate_abbreviation defines AF_{I+} and binds it to "
                          "i_plus.definition with no additional assumption; statement_formal calls it by name."),
            "evidence_refs": [f"{F1}#L{lines['predicate_abbreviation']}", f"{F1}#L{lines['statement_formal']}"],
        },
        {
            "id": "F-03",
            "class": "positive",
            "axis": "YAML strictness / duplicate keys (rev11 hard failure)",
            "statement": ("REPAIRED: yaml.compose finds 0 duplicate mapping keys at cce9c601 (rev11 had 7 "
                          "duplicate revised_at keys plus 2 revised_at_unused); revision history moved into "
                          "a revision_history list."),
            "evidence_refs": [f"{F1}#L{lines['revision_history']}"],
            "probe": "probe_rev12_output.json:repair_checks_rev12.duplicate_top_level_keys == []",
        },
        {
            "id": "F-04",
            "class": "positive",
            "axis": "class-contract pointer resolution (rev11 hard failure)",
            "statement": ("REPAIRED: class_contract_pointer now targets "
                          "research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN, which resolves "
                          "(classes.AF-WCC-VAC-GEN present at taxonomy 0abb9ed8); the authoring-tree "
                          "supplement is a separately named field (class_contract_supplement_pointer) so "
                          "the declared taxonomy and the supplement cannot be conflated."),
            "evidence_refs": [f"{F1}#L{lines['class_contract_pointer']}",
                              f"{F1}#L{lines['class_contract_supplement_pointer']}",
                              "research_map/formulation_taxonomy.yaml#sha256:0abb9ed8a961"],
        },
        {
            "id": "F-05",
            "class": "positive",
            "axis": "freeze hash binding",
            "statement": ("FROZEN rev28 (self 2f358f67) declares F1 = cce9c601 and the measured canonical "
                          "F1 equals it; f0_binding.declared_f0_sha256 equals the measured canonical "
                          "taxonomy 0abb9ed8. All five pinned canonical files match FROZEN rev28."),
            "evidence_refs": ["artifacts/formulation/FROZEN.json#sha256:2f358f6722d9",
                              f"{F1}#L{lines['f0_binding']}"],
            "probe": "probe_rev12_output.json:pins + repair_checks_rev12.frozen_declared_matches_measured",
        },
        {
            "id": "F-06",
            "class": "advisory",
            "axis": "D0 residual (tagged-union reading)",
            "statement": ("The rev11 ill-typedness hard failure is repaired: the first binder is the single "
                          "tagged index r and all quantified objects are r-indexed. Residual for lead "
                          "adjudication: D0 remains a tagged disjoint union whose definition contains "
                          "'smooth ... or ... (sobolev,s,delta)', so the G-FORM item 'no single frozen data "
                          "class (s,delta,norm) is shared by F1/F2a/F2b' (W037-F5) is restructured rather "
                          "than removed. The exact-prefix criterion is met at prefix level ('forall r in D0'); "
                          "whether the tagged-index formulation satisfies the single-data-class criterion is "
                          "a scope call, not a schema-level hard failure."),
            "evidence_refs": [f"{F1}#L{lines['binder_r']}", f"{F1}#L{lines['D5']}"],
        },
        {
            "id": "F-07",
            "class": "finding-control",
            "axis": "binding-gate blindness on the predicate-identity axis (continuity of W061 F-06)",
            "statement": ("CONFIRMED at rev12. With the current manifest (014e2d30, FROZEN rev28) the "
                          "binding gate check_class_schema.py (000e09e4, rule_spec 40f9bb9e) returns "
                          "pass/failed_rules [] on all four semantic substitutions: M0 formal B-containment, "
                          "M1 variant-SET predicate in visibility.definition, M2 stale whole-curve D5, M4 "
                          "whole-curve negation - as well as on the key-hygiene control and the cosmetic "
                          "control. Under the pre-fix manifest (fce91948, FROZEN rev27) the same four "
                          "mutants also pass; only the unfixed canonical POS trips R22 (unknown keys). The "
                          "proposed rule W061-PREDICATE-CONSISTENCY-V1 detects 4/4 mutants (R3/R4/R5/R6/R7), "
                          "passes POS/keyfix/cosmetic and returns not_applicable for the F2a/F2b siblings."),
            "evidence_refs": [str((TASK / 'probe_rev12_output.json').relative_to(REPO)) +
                              "#sha256:" + sha(TASK / "probe_rev12_output.json")[:12],
                              "rule/check_predicate_consistency.py#sha256:" +
                              sha(TASK / "rule/check_predicate_consistency.py")[:12]],
            "recommendation": ("adopt R3-R7 (or equivalent) into the binding gate; the four mutants are "
                               "ready-made NEG fixtures and the rule script is standalone"),
        },
        {
            "id": "F-08",
            "class": "process-resolved",
            "axis": "freeze -> tool-manifest binding in the rev27 window",
            "statement": ("FROZEN rev27 (self 2554e276, 00:32:59) declared KEY_MANIFEST fce91948, which did "
                          "not whitelist the rev12 keys, so F1/F2a/F2b returned fail R22 between ~00:33 and "
                          "~00:34; the manifest was edited in place to 014e2d30 and FROZEN bumped to rev28 "
                          "(self 2f358f67, 00:35:08), after which the same schema bytes pass. Reproduced "
                          "with the frozen tool bytes in gate_replay/. No standing failure at emission time; "
                          "recorded because G-FORM verification reads the freeze/manifest pair."),
            "evidence_refs": ["pinned/hist/FROZEN.rev27.json", "pinned/hist/KEY_MANIFEST.rev27.json",
                              "pinned/FROZEN.rev28.json", "pinned/KEY_MANIFEST.rev28.json"],
        },
        {
            "id": "F-09",
            "class": "advisory",
            "axis": "canonical vs authoring taxonomy divergence (CF-13 residual)",
            "statement": ("Canonical taxonomy 0abb9ed8 and authoring mirror d7419b4e still differ. F1's "
                          "class_contract_pointer now resolves in the canonical tree, so F1 is unaffected; "
                          "the supplement pointer intentionally targets the authoring mirror. CF-13 remains "
                          "partially open at the taxonomy level."),
            "evidence_refs": ["research_map/formulation_taxonomy.yaml#sha256:0abb9ed8a961",
                              "artifacts/formulation/formulation_taxonomy.yaml#sha256:d7419b4e8963"],
        },
    ]

    review = {
        "task_id": "W061-F1-REV12-GATE-03",
        "worker": "worker-061",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "target": F1,
        "reviewed_sha256": reviewed_sha,
        "reviewed_revision": rp["revision"],
        "verdict": "accept",
        "score": 4.5,
        "hard_failures": [],
        "findings": findings,
        "repair_checks": rp,
        "proposed_rule": {
            "rule_set": "W061-PREDICATE-CONSISTENCY-V1",
            "script": "artifacts/worker-061/f1_rev12_gate/rule/check_predicate_consistency.py",
            "script_sha256": sha(TASK / "rule/check_predicate_consistency.py"),
            "verdict_on_reviewed_hash": rule_matrix["POS_rev12_canonical.yaml"]["verdict"],
            "sensitivity": "4/4 NEG mutants fail (M0 R4+R7, M1 R3+R7, M2 R5, M4 R6)",
            "specificity": "POS/keyfix/cosmetic pass; F2a/F2b not_applicable; 0 false failures",
            "fixtures": fixture_hashes,
            "rule_reports": report_hashes,
        },
        "canonical_gate_at_review": {
            "tool": "artifacts/formulation/tools/check_class_schema.py",
            "tool_sha256": sha(REPO / "artifacts/formulation/tools/check_class_schema.py"),
            "rule_spec_sha256": sha(REPO / "artifacts/formulation/rule_spec.json"),
            "manifest_measured_sha256": sha(REPO / "artifacts/formulation/KEY_MANIFEST.json"),
            "verdict_on_reviewed_hash": gate_matrix["POS_rev12_canonical.yaml"]["verdict"],
            "verdict_on_mutants": {k: v["verdict"] for k, v in gate_matrix.items()},
            "replay_rev27_fce91948": {k: v["manifest_rev27_fce91948"] for k, v in replay.items()},
            "replay_rev28_014e2d30": {k: v["manifest_rev28_014e2d30"] for k, v in replay.items()},
        },
        "positive_controls": {
            "classsep_regression": "runtime/bin/classsep_regression.py -> leaks 17/17, controls 10/10, FP 0, FN 0, PASS",
            "scc_siblings": {k: v["rule"]["verdict"] for k, v in probe["scc_sibling_controls"].items()},
            "cosmetic_control": rule_matrix["CTL_cosmetic.yaml"]["verdict"],
        },
        "independence": {
            "author_of_target": "astra-lead-formulation (rev12 via artifacts/formulation/tools/close_findings_rev27.py)",
            "reviewer_is_author": False,
            "correlated_exposure": ("Follow-up verification by the same reviewer as W061-F1-INDEP-REV-02: this "
                                    "is a repair audit at a new hash, not an independent discovery. The "
                                    "reviewer read the headings of close_findings_rev27.py when selecting the "
                                    "probe set, so exposure to the author's intended fixes is correlated."),
            "conflicts": "none declared; no artifact in the formulation tree was modified",
        },
        "scope_limits": [
            "structure/class binding/formal-expansion consistency only: no physical truth claim, no citation verification, no proof check",
            "the accept binds only to cce9c601 and does not extend to later revisions",
            "worker evidence, not a gate verdict or node completion; the controller/lead adjudicates",
            "F2a/F2b were used only as not_applicable rule controls and are not reviewed here",
        ],
        "next_falsifier": ("Re-measure schemas/af_wcc_vacuum.yaml; any change voids this accept. On cce9c601 "
                           "the accept is falsified by any of: (a) the proposed rule returning fail on "
                           "cce9c601; (b) any of M0/M1/M2/M4 returning pass under the rule (sensitivity "
                           "broken); (c) the canonical gate gaining a predicate-axis rule that flags "
                           "cce9c601; (d) FROZEN declaring any hash other than cce9c601 for F1; (e) "
                           "visibility.definition, quantifiers.formal, D5 or quantifiers.negation losing "
                           "the t0 tail binder; (f) the class_contract_pointer failing to resolve in the "
                           "canonical taxonomy."),
        "authority_note": ("Worker evidence only. This review does not set node status, validation_status or any "
                           "gate verdict; it does not modify canonical artifacts."),
        "created_at": NOW,
    }
    review_json = TASK / "REVIEW.json"
    review_json.write_text(json.dumps(review, indent=2, sort_keys=False) + "\n")
    review_sha = sha(review_json)

    md = [f"# W061-F1-REV12-GATE-03 -- F1 independent repair audit at cce9c601",
          "",
          f"- target: `{F1}`  ",
          f"- reviewed_sha256: `{reviewed_sha}` (revision {rp['revision']})  ",
          f"- verdict: **accept** (score 4.5), hard failures: none  ",
          f"- proposed rule verdict at this hash: **{rule_matrix['POS_rev12_canonical.yaml']['verdict']}**  ",
          f"- binding gate verdict at this hash (manifest 014e2d30): "
          f"**{gate_matrix['POS_rev12_canonical.yaml']['verdict']}**",
          "",
          "## Findings", ""]
    for f in findings:
        md.append(f"**{f['id']} [{f['class']}] {f['axis']}** -- {f['statement']}")
        md.append("")
    md += ["## Proposed control", "",
           "`W061-PREDICATE-CONSISTENCY-V1` closes the predicate-identity axis the binding gate does not "
           "police: R3 canonical predicate tail form, R4 formal expansion, R5 not-exists domain, R6 negation, "
           "R7 variant-not-assertive. 4/4 NEG mutants detected; all POS/CTL controls pass; F2a/F2b N/A.",
           "",
           "## Next falsifier", "", review["next_falsifier"], ""]
    (TASK / "REVIEW.md").write_text("\n".join(md))

    checkpoint = {
        "task_id": "W061-F1-REV12-GATE-03",
        "worker": "worker-061",
        "checkpoint": 1,
        "created_at": NOW,
        "status": "task_complete_worker_evidence_only",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "reviewed_sha256": reviewed_sha,
        "verdict": "accept",
        "score": 4.5,
        "hard_failures": [],
        "open_advisories": ["F-06 D0 tagged-union single-data-class adjudication",
                            "F-07 adopt predicate-consistency rule R3-R7 into the binding gate",
                            "F-09 CF-13 canonical/authoring taxonomy divergence"],
        "artifacts": {**artifact_hashes, **fixture_hashes, **report_hashes, **gate_hashes,
                      str(review_json.relative_to(REPO)): review_sha,
                      "artifacts/worker-061/f1_rev12_gate/REVIEW.md": sha(TASK / "REVIEW.md")},
        "next_falsifier": review["next_falsifier"],
        "hours": 0.6,
    }
    checkpoint_json = TASK / "CHECKPOINT.json"
    checkpoint_json.write_text(json.dumps(checkpoint, indent=2, sort_keys=False) + "\n")
    checkpoint_sha = sha(checkpoint_json)
    STATE.write_text(json.dumps(checkpoint, indent=2, sort_keys=False) + "\n")

    # ---------------- outbox events ----------------
    def ev(eid, etype, **kw):
        d = {"event_id": eid, "event_type": etype, "created_at": NOW, "actor": "worker-061",
             "task_id": "W061-F1-REV12-GATE-03", "node_id": "F1",
             "class_id": "AF-WCC-VAC-GEN", "gate": "G-FORM"}
        d.update(kw)
        return d

    refs = [
        f"{F1}#sha256:{reviewed_sha[:12]}",
        "artifacts/worker-061/f1_rev12_gate/rule/check_predicate_consistency.py#sha256:"
        + sha(TASK / "rule/check_predicate_consistency.py")[:12],
        "artifacts/worker-061/f1_rev12_gate/probe_rev12_output.json#sha256:"
        + sha(TASK / "probe_rev12_output.json")[:12],
        f"artifacts/worker-061/f1_rev12_gate/REVIEW.json#sha256:{review_sha[:12]}",
        f"artifacts/worker-061/f1_rev12_gate/CHECKPOINT.json#sha256:{checkpoint_sha[:12]}",
    ]
    next_f = review["next_falsifier"]

    events = [
        ev("w061-rev12-20260912T0040-claim", "status", status="active", hours=0.6,
           summary=("Took one bounded class-bound task with no inbox assignment: independent repair audit "
                    "of F1 rev12 (AF-WCC-VAC-GEN) at cce9c601 plus a proposed gate rule for the "
                    "predicate-identity axis. Result: all five rev11 hard failures verified repaired; "
                    "verdict accept 4.5; canonical gate passes every semantic mutant (blindness confirmed "
                    "at rev12); proposed rule detects 4/4 mutants and passes all controls."),
           evidence_refs=refs, next_falsifier=next_f),
        ev("w061-rev12-20260912T0040-artifact-rule", "artifact",
           artifact_type="gate_rule_proposal", path="artifacts/worker-061/f1_rev12_gate/rule/check_predicate_consistency.py",
           sha256=sha(TASK / "rule/check_predicate_consistency.py"), validation_status="unverified",
           note="W061-PREDICATE-CONSISTENCY-V1: standalone R0-R8 rule closing the visibility-predicate axis; worker proposal, not a canonical gate change."),
        ev("w061-rev12-20260912T0040-artifact-probe", "artifact",
           artifact_type="probe_output", path="artifacts/worker-061/f1_rev12_gate/probe_rev12_output.json",
           sha256=sha(TASK / "probe_rev12_output.json"), validation_status="unverified",
           note="Pins, repair checks, rule matrix, canonical-gate matrix, manifest-rev27/rev28 replay, SCC controls; rerunnable via run_all.py."),
        ev("w061-rev12-20260912T0040-artifact-review", "artifact",
           artifact_type="independent_review_json", path="artifacts/worker-061/f1_rev12_gate/REVIEW.json",
           sha256=review_sha, validation_status="unverified",
           note="Worker evidence, not a gate verdict and not a node completion claim; controller/lead adjudication required."),
        ev("w061-rev12-20260912T0040-artifact-checkpoint", "artifact",
           artifact_type="checkpoint_json", path="artifacts/worker-061/f1_rev12_gate/CHECKPOINT.json",
           sha256=checkpoint_sha, validation_status="unverified",
           note="Hash ledger for every emitted artifact; copy at runtime/state/w061_rev12_gate_checkpoint.json."),
        ev("w061-rev12-20260912T0040-review", "review", reviewer="worker-061", target_id="F1",
           artifact=F1, artifact_sha256=reviewed_sha, reviewed_sha256=reviewed_sha,
           verdict="accept", score=4.5, hard_failures=[],
           findings=[f"[{f['id']} {f['class']}] {f['axis']}: {f['statement'][:300]}" for f in findings],
           evidence_refs=refs, next_falsifier=next_f,
           independence=review["independence"],
           authority_note=review["authority_note"]),
        ev("w061-rev12-20260912T0040-final", "status", status="active", hours=0.6,
           summary=("Bounded task complete: rule + fixtures + probe matrix + REVIEW.json + CHECKPOINT.json "
                    "written and hashed; review event emitted. No node status, validation_status or gate "
                    "verdict claimed (worker authority rule). Accept binds only to cce9c601; the rev27->rev28 "
                    "manifest transition is recorded as a resolved process finding."),
           evidence_refs=refs, next_falsifier=next_f),
    ]

    with OUTBOX.open("a") as fh:
        for e in events:
            fh.write(json.dumps(e) + "\n")

    # re-parse the whole outbox to prove every line is valid JSON
    bad = 0
    for ln in OUTBOX.read_text().splitlines():
        if ln.strip():
            try:
                json.loads(ln)
            except json.JSONDecodeError:
                bad += 1
    print("REVIEW.json", review_sha[:16], "CHECKPOINT.json", checkpoint_sha[:16])
    print("events appended:", len(events), "outbox line total:", len(OUTBOX.read_text().splitlines()),
          "invalid JSON lines:", bad)
    print("state checkpoint:", STATE, sha(STATE)[:16])


if __name__ == "__main__":
    main()
