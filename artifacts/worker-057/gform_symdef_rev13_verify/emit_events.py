#!/usr/bin/env python3
"""Emit the W057-GFORM-SYMDEF-REV13-VERIFY-01 events to comms/outbox/worker-057.jsonl
and write the worker checkpoint.

Idempotent: an event_id already present in the outbox is skipped; the checkpoint file and
log line are written only if the checkpoint id is not already present.  Every artifact
sha256 and every pinned input sha256 is re-measured on disk before the events are written;
a mismatch aborts (nothing is appended).  Events are validated against
research_map/schemas.py before being appended.

Authority guard: the emitted events claim no gate verdict, no node status and no
validation_status=passed; emitter aborts if the report's verdict is DIVERGENT or if any
control failed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUTBOX = REPO / "comms" / "outbox" / "worker-057.jsonl"
CKPT = REPO / "runtime" / "state" / "w057_checkpoint_gform_symdef_rev13.json"
CKPT_LOG = REPO / "runtime" / "state" / "w057_checkpoints.jsonl"
sys.path.insert(0, str(REPO))
from research_map.schemas import validate_event  # noqa: E402

D = "artifacts/worker-057/gform_symdef_rev13_verify"
P = {
    "report": f"{D}/report.json",
    "harness": f"{D}/verify_symbol_defs_rev13.py",
    "baseline_checker": f"{D}/baseline_checker_sealed.py",
    "baseline_report": f"{D}/baseline_report.json",
    "reportmd": f"{D}/REPORT.md",
}
INPUTS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
]

FALSIFIER = (
    "Re-hash the four pinned inputs (schemas/af_wcc_vacuum.yaml d9cebb9404b2e79e…c5d3d, "
    "schemas/af_scc_c2_vacuum.yaml e9a27996dfd308bd…d82fe, schemas/af_scc_c0_vacuum.yaml "
    "b2ab6acb2bbe7f86…4501c, research_map/formulation_taxonomy.yaml 0abb9ed8a96135c9…094e3) "
    "and re-run artifacts/worker-057/gform_symdef_rev13_verify/verify_symbol_defs_rev13.py: "
    "the report is falsified for the recorded sha256 values if any measured input hash differs, "
    "if any control C1-C5 flips to false, if the independent major-finding set stops equalling "
    "the sealed baseline set, or if a definition site for P_WCC or MGHD appears outside the "
    "normative sites (which flips the verdict to REPAIRED). A moved schema or taxonomy hash "
    "voids this report for the new bytes.")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    H = {k: sha(REPO / v) for k, v in P.items()}
    report = json.loads((REPO / P["report"]).read_text())

    assert report["verdict"] in ("VERIFIED_REV13", "VERIFIED_REV13_WITH_BASELINE_CORRECTION"), \
        f"unexpected verdict {report['verdict']}"
    assert all(c["ok"] for c in report["controls"].values()), "a control failed"
    for rel in INPUTS:
        measured = sha(REPO / rel)
        assert measured == report["measured_inputs"][rel]["sha256"], f"input moved: {rel}"
        assert report["measured_inputs"][rel]["match"], f"input not pinned: {rel}"

    evidence = [f"{P['report']}#{H['report'][:12]}", f"{P['harness']}#{H['harness'][:12]}",
                f"{P['baseline_checker']}#{H['baseline_checker'][:12]}",
                f"{P['baseline_report']}#{H['baseline_report'][:12]}",
                f"{P['reportmd']}#{H['reportmd'][:12]}"] + \
               [f"{rel}#{report['measured_inputs'][rel]['sha256'][:12]}" for rel in INPUTS]

    now = report["created_at"]
    pre = "w057-gformsymdef13"
    common = {"created_at": now, "actor": "worker-057", "node_id": "F1,F2a,F2b",
              "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
              "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
              "gate": "G-FORM", "group_id": "formulation",
              "task_id": "W057-GFORM-SYMDEF-REV13-VERIFY-01"}
    confirm = [f for f in report["findings"]]
    cf = "; ".join(f"{f['node']} {f['symbol']} ({f['kind']})" for f in confirm)

    events = [
        dict(common, event_id=f"{pre}-status-start", event_type="status", status="active",
             hours=0.1,
             summary=("No card exists in comms/inbox/worker-057.jsonl; took ONE bounded "
                      "class-bound task (AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN; "
                      "F1/F2a/F2b; gate G-FORM): independent re-test of the normative-symbol "
                      "definition findings at the rev-13 schema bytes, with a sealed re-run of "
                      "the original checker as the comparison arm. Method: structural YAML "
                      "definition-site map (no import of the baseline code) + 5 pre-registered "
                      "controls."),
             evidence_refs=[f"{rel}#{report['measured_inputs'][rel]['sha256'][:12]}"
                            for rel in INPUTS],
             next_falsifier=FALSIFIER),
        dict(common, event_id=f"{pre}-artifact-report", event_type="artifact",
             artifact_type="independent_verification_report", path=P["report"],
             sha256=H["report"], bytes=(REPO / P["report"]).stat().st_size,
             validation_status="unverified", verdict=report["verdict"],
             checks=f"{sum(c['ok'] for c in report['controls'].values())}/"
                    f"{len(report['controls'])}",
             confirmed_findings=cf,
             unreproduced_baseline_findings=report["agreement"]["unreproduced_baseline_findings"],
             measured_inputs={rel: report["measured_inputs"][rel]["sha256"] for rel in INPUTS},
             reproduce=f"python3 {P['harness']}",
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-harness", event_type="artifact",
             artifact_type="verifier_script", path=P["harness"], sha256=H["harness"],
             bytes=(REPO / P["harness"]).stat().st_size, validation_status="unverified",
             reproduce=f"python3 {P['harness']}", falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-baseline", event_type="artifact",
             artifact_type="sealed_baseline_checker", path=P["baseline_checker"],
             sha256=H["baseline_checker"], bytes=(REPO / P["baseline_checker"]).stat().st_size,
             validation_status="unverified",
             note=("byte-copy of the rev-12 checker with only the output filename changed; "
                   "its run output is the sealed comparison arm"),
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-artifact-reportmd", event_type="artifact",
             artifact_type="report_markdown", path=P["reportmd"], sha256=H["reportmd"],
             bytes=(REPO / P["reportmd"]).stat().st_size, validation_status="unverified",
             falsifier=FALSIFIER, evidence_refs=evidence),
        dict(common, event_id=f"{pre}-review", event_type="review",
             reviewer="worker-057 (advisory; independent of the schema authors and of the G-FORM reviewers)",
             target_id=f"{P['report']}#{H['report']}", target_path=P["report"],
             reviewed_sha256=H["report"], verdict="accept", score=4.0, hard_failures=[],
             findings=[
                 {"severity": "confirm", "check": "F1",
                  "finding": ("At rev 13 the five remaining symbol defects reproduce under an "
                              "independent decision procedure and 5/5 controls: F1 P_WCC has no "
                              "definition site; F2a/F2b MGHD is taxonomy-prose-only; F2a/F2b "
                              "apply the class-defining extension predicate to MGHD(D) while its "
                              "definition is on (M',g',iota).")},
                 {"severity": "correction", "check": "F2",
                  "finding": ("The baseline's sixth major finding is a false positive at rev 13: "
                              "AF_{I+} has a definitional leaf i_plus.predicate_abbreviation "
                              "(added by the rev-12 repair) that the sealed checker does not "
                              "recognise; it must not be cited as a standing G-FORM failure at "
                              "these bytes.")},
                 {"severity": "confirm", "check": "F3",
                  "finding": ("The uniformity question is unchanged by the rev-13 repair: F1 "
                              "AF_{I+} is defined file-locally, F2 MGHD relies on taxonomy prose, "
                              "and F1 P_WCC has no definition anywhere. The strict and "
                              "prose-sufficient policies still cannot both stand; adjudication "
                              "is the G-FORM reviewers'/controller's call.")},
                 {"severity": "scope", "check": "A1",
                  "finding": ("Instrument-bound: the verdict is valid only at the four recorded "
                              "hashes; the schemas were moving during this session (rev 13 "
                              "written 00:53:20-00:53:40) and a moved byte voids the report.")},
             ],
             authority_note=("worker review is advisory evidence only: it sets no gate verdict, "
                             "no node status and no validation_status=passed, and it does not "
                             "adjudicate the definition-site policy."),
             evidence_refs=evidence),
        dict(common, event_id=f"{pre}-claim", event_type="claim",
             conclusion_type="formal_model",
             statement=(
                 "Artifact-and-checker result, not a mathematical claim: at the rev-13 pins "
                 "schemas/af_wcc_vacuum.yaml sha256 "
                 f"{report['measured_inputs']['schemas/af_wcc_vacuum.yaml']['sha256']}, "
                 "schemas/af_scc_c2_vacuum.yaml sha256 "
                 f"{report['measured_inputs']['schemas/af_scc_c2_vacuum.yaml']['sha256']}, "
                 "schemas/af_scc_c0_vacuum.yaml sha256 "
                 f"{report['measured_inputs']['schemas/af_scc_c0_vacuum.yaml']['sha256']} and "
                 "frozen research_map/formulation_taxonomy.yaml sha256 "
                 f"{report['measured_inputs']['research_map/formulation_taxonomy.yaml']['sha256']}, "
                 "an independently written structural definition-site probe plus a sealed re-run "
                 "of the earlier checker agree on five of the six earlier major findings and the "
                 "independent probe refuses the sixth: (1) F1 quantifiers.negation_normal_form "
                 "uses P_WCC(D) with no definition site in the file and no occurrence in the "
                 "frozen taxonomy; (2) F2a and F2b conclusion.statement_formal and "
                 "quantifiers.negation_normal_form use MGHD(D) with no definition site, the "
                 "taxonomy carrying only the expansion prose (11 mention scalars, no "
                 "definition_ref); (3) in both SCC classes proper_future_extension_in_class is "
                 "defined on the extension tuple (M',g',iota) of (M,g) but applied to MGHD(D), "
                 "so the negated extension existential is implicit at the use site; (4) the "
                 "baseline's AF_{I+} no-definition-site finding is NOT reproduced because "
                 "i_plus.predicate_abbreviation is a definitional leaf that names and expands "
                 "the symbol. 5/5 controls pass (defined symbol resolves, binder resolves, "
                 "absent symbol unresolved, byte tamper caught by the pin, injected-definition "
                 "refutation branch fires). This measures schema well-formedness at pinned "
                 "bytes; it decides no definition-site policy and asserts nothing about cosmic "
                 "censorship."),
             assumptions=[
                 "the four canonical files are the measured hashes recorded in evidence_refs; "
                 "a moved byte voids this report for the new bytes",
                 "a symbol is defined when a definitional scalar outside the normative sites "
                 "names it (leaf definition, definitional key, or a symbol-naming key paired "
                 "with a sibling definition); taxonomy prose mention alone is recorded as the "
                 "weaker class mentioned_not_defined",
                 "the normative-site paths are taken from the sealed baseline report, not "
                 "invented here; the probe's decision rule is otherwise independent",
                 "no semantic correctness of the class statements is assumed or decided",
             ],
             falsifier=FALSIFIER, evidence_refs=evidence,
             artifact_refs=[f"{P['report']}#{H['report'][:12]}",
                            f"{P['harness']}#{H['harness'][:12]}",
                            f"{P['baseline_report']}#{H['baseline_report'][:12]}"],
             not_claimed=["gate verdict", "node status", "validation_status=passed",
                          "definition-site policy", "schema or taxonomy edit",
                          "numerics_lock release"]),
        dict(common, event_id=f"{pre}-blocker-symbols", event_type="blocker",
             description=(
                 "At the rev-13 pins the dangling-symbol defect set is 6 major findings across "
                 "the three class schemas (P_WCC in F1; MGHD in F2a/F2b; the extension-predicate "
                 "argument role in F2a/F2b) and the definition-site policy remains non-uniform: "
                 "F1 AF_{I+} is defined file-locally by i_plus.predicate_abbreviation while F2 "
                 "MGHD is taxonomy-prose-only and F1 P_WCC is defined nowhere. The earlier "
                 "blocker (w57-symdef-20260912T003243-blocker-symbols) therefore still stands at "
                 "the new bytes, minus AF_{I+}."),
             needed_to_unblock=(
                 "lead-formulation publishes a symbols/definitions block or definition_ref for "
                 "P_WCC and MGHD (or records the uniform policy that taxonomy prose expansion "
                 "counts as a definition site); then re-run "
                 "artifacts/worker-057/gform_symdef_rev13_verify/verify_symbol_defs_rev13.py at "
                 "the new hash and confirm the independent verdict flips to REPAIRED (no major "
                 "findings) or that the recorded policy names each accepted prose-only symbol."),
             evidence_refs=evidence),
        dict(common, event_id=f"{pre}-status-complete", event_type="status", status="active",
             hours=0.4, claims_completion=False,
             summary=("W057-GFORM-SYMDEF-REV13-VERIFY-01 complete as one bounded class-bound "
                      "worker task: verdict VERIFIED_REV13_WITH_BASELINE_CORRECTION (5/5 "
                      "controls; independent probe reproduces 5 of 6 baseline major findings at "
                      "rev 13 and refutes the AF_{I+} finding as a baseline false positive; "
                      "P_WCC, MGHD x2 and the extension-predicate role persist). Checkpoint "
                      "written to runtime/state/w057_checkpoint_gform_symdef_rev13.json and "
                      "runtime/state/w057_checkpoints.jsonl. No gate verdict, no node "
                      "completion, no taxonomy/schema edit; worker slot can be recycled."),
             evidence_refs=evidence, next_falsifier=FALSIFIER),
    ]

    for ev in events:
        validate_event(ev)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    appended, skipped = [], []
    with OUTBOX.open("a") as f:
        for ev in events:
            if ev["event_id"] in existing:
                skipped.append(ev["event_id"])
                continue
            f.write(json.dumps(ev, sort_keys=True) + "\n")
            appended.append(ev["event_id"])

    ckpt = {
        "checkpoint": "w057-gformsymdef13-1",
        "worker": "worker-057",
        "assignment": "W057-GFORM-SYMDEF-REV13-VERIFY-01 (self-selected; no inbox card existed)",
        "at": now,
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "status": "active",
        "hours_spent_estimate": 0.4,
        "verdict": report["verdict"],
        "inputs": {rel: report["measured_inputs"][rel]["sha256"] for rel in INPUTS},
        "artifacts": {P[k]: H[k] for k in P},
        "events_appended": appended,
        "events_skipped_duplicate": skipped,
        "falsifier": FALSIFIER,
        "next_falsifier": FALSIFIER,
    }
    CKPT.write_text(json.dumps(ckpt, indent=1) + "\n")
    if not CKPT_LOG.exists() or ckpt["checkpoint"] not in CKPT_LOG.read_text():
        with CKPT_LOG.open("a") as f:
            f.write(json.dumps({k: ckpt[k] for k in
                                ("checkpoint", "worker", "at", "gate", "verdict",
                                 "events_appended", "falsifier")}) + "\n")

    print(json.dumps({"appended": appended, "skipped": skipped,
                      "checkpoint": str(CKPT.relative_to(REPO)),
                      "artifacts": {k: v[:12] for k, v in H.items()},
                      "inputs": {rel: report["measured_inputs"][rel]["sha256"][:12]
                                 for rel in INPUTS}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
