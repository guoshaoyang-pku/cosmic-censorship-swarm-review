#!/usr/bin/env python3
"""Emit W080-F2B-REPAIR-H2E-01 events to comms/outbox/worker-080.jsonl (append-only).

Every line is a single JSON object with the protocol-required keys
event_id / event_type / created_at / actor.  Run once; re-running appends duplicates
(ids include the wall-clock stamp), so the emitted file is validated at the end.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
OUTBOX = ROOT / "comms/outbox/worker-080.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def h(p: str) -> str:
    return sha(ROOT / p)


def ev(eid, etype, at, **kw):
    return {"event_id": eid, "event_type": etype, "created_at": at,
            "actor": "worker-080", **kw}


def main() -> int:
    at = datetime.now(CST).isoformat(timespec="seconds")
    stamp = at.replace("-", "").replace(":", "").replace("+08:00", "")
    report = json.loads((OUT / "report.json").read_text())
    artifacts = {
        "harness": "artifacts/worker-080/f2b_repair_entailment_audit/audit_h2_entailment.py",
        "report": "artifacts/worker-080/f2b_repair_entailment_audit/report.json",
        "readme": "artifacts/worker-080/f2b_repair_entailment_audit/README.md",
        "patch": "artifacts/worker-080/f2b_repair_entailment_audit/repair_patch_corrected.diff",
        "sums": "artifacts/worker-080/f2b_repair_entailment_audit/SHA256SUMS",
        "emit": "artifacts/worker-080/f2b_repair_entailment_audit/emit_events.py",
        "corrected": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml",
        "nesting": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml",
        "rebased": "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_84b5d3fa.yaml",
    }
    H = {k: h(v) for k, v in artifacts.items()}
    live = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
    frozen = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
    refc = "98f9ec83c487d6920968f0bdf98e03974813376b6d222b617300525eb13feb1c"
    w08 = "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml"
    falsifier = report["next_falsifier"]
    not_claimed = [
        "no canonical artifact written or modified",
        "no gate verdict, no node status, no validation_status=passed",
        "no mathematical claim about C0/C2 inextendibility; text-consistency audit only",
        "no attribution of error to worker-017/worker-066/worker-08 for the live defects they found",
        "no ruling on which corrected wording the owner must adopt",
    ]

    # ---- checkpoint (written before the events that cite it) --------------------
    ckpt_path = ROOT / "runtime/state/w080_f2b_repair_entailment_checkpoint.json"
    ckpt = {
        "checkpoint_id": f"w080-f2b-h2e-{stamp}",
        "task_id": report["task_id"], "actor": "worker-080", "created_at": at,
        "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"], "gate": "G-FORM",
        "status": "active",
        "verdict": report["verdict"],
        "checks_pass": report["all_checks_pass"],
        "controls_matched": f"{sum(1 for c in report['controls'] if c['pass'])}/{len(report['controls'])}",
        "findings": report["findings"],
        "artifacts": {k: {"path": v, "sha256": H[k]} for k, v in artifacts.items()},
        "staged_candidates": report["staged_candidates"],
        "pins": {k: v["measured"] for k, v in report["pins"].items()},
        "next_falsifier": falsifier,
        "not_claimed": not_claimed,
    }
    ckpt_path.write_text(json.dumps(ckpt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    artifacts["checkpoint"] = str(ckpt_path.relative_to(ROOT))
    H["checkpoint"] = h(artifacts["checkpoint"])

    base_evidence = [
        f"artifacts/worker-080/f2b_repair_entailment_audit/report.json#{H['report'][:12]}",
        f"artifacts/worker-080/f2b_repair_entailment_audit/audit_h2_entailment.py#{H['harness'][:12]}",
        f"schemas/af_scc_c0_vacuum.yaml#{live[:12]}",
        "schemas/af_scc_c0_vacuum.yaml:152",
        "schemas/af_scc_c0_vacuum.yaml:232",
        "schemas/af_scc_c0_vacuum.yaml:239",
        "schemas/af_scc_c2_vacuum.yaml:152",
        f"artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml#{h(w08)[:12]}",
        f"artifacts/formulation/FROZEN.json#{frozen[:12]}",
        f"artifacts/worker-066/f2b_rev29_containment_binding/pinned/candidate_98f9ec83__af_scc_c0_vacuum.yaml#{refc[:12]}",
        f"runtime/state/w080_f2b_repair_entailment_checkpoint.json#{H['checkpoint'][:12]}",
    ]
    events = []

    events.append(ev(f"w080-h2e-{stamp}-status", "status", at,
                     node_id="F2b", gate="G-FORM",
                     class_id="AF-SCC-C0-VAC-GEN",
                     class_ids=["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
                     status="active", hours=0.5,
                     summary=("W080-F2B-REPAIR-H2E-01: independent audit of the circulating F2b 2-edit repair. "
                              "The H1 edit is correct; the H2 replacement asserts 'H2_loc-inextendibility ENTAILS this "
                              "class's conclusion' inside the C0 file, contradicting the file's own chain at :239 and its "
                              "own forbidden_weakenings row at :232. Candidate 84b5d3fa (= worker-08's repair candidate) "
                              "must not be landed as-is; two finding-free corrected candidates are staged. Read-only."),
                     evidence_refs=base_evidence, next_falsifier=falsifier,
                     not_claimed=not_claimed))

    art = [
        ("harness", "deterministic_audit_harness", "audit_h2_entailment.py",
         "Read-only, stdlib-only, fail-closed harness: pins, candidate reproduction, chain-derived entailment closure, 9 pre-registered controls, gate runs."),
        ("report", "repair_candidate_audit_report", "report.json",
         "18/18 checks, 9/9 controls; verdict REVISE at candidate 84b5d3fa; findings entailment_direction_inverted + normative_contradiction."),
        ("readme", "documentation", "README.md", "Method, evidence, corrected candidates, falsifier."),
        ("patch", "corrected_repair_patch", "repair_patch_corrected.diff",
         "Minimal unified diff live -> corrected candidate (two leaf lines; H1 edit unchanged from the circulating repair)."),
        ("corrected", "corrected_repair_candidate", "staged/candidate_corrected.yaml",
         "H2 direction corrected explicitly; finding-free; canonical structural gate PASS; owner-adoptable."),
        ("nesting", "alternate_repair_candidate", "staged/candidate_nesting_only.yaml",
         "H2 nesting + ledger pointer only, no entailment claim; finding-free; gate PASS."),
        ("rebased", "reproduced_repair_candidate", "staged/candidate_84b5d3fa.yaml",
         "Independent re-application of the two published edits to live bytes; reproduces 84b5d3fa exactly."),
        ("sums", "hash_manifest", "SHA256SUMS", "SHA256SUMS over the bundle."),
    ]
    for key, atype, fname, summ in art:
        e = ev(f"w080-h2e-{stamp}-artifact-{key}", "artifact", at,
               node_id="F2b", gate="G-FORM",
               class_id="AF-SCC-C0-VAC-GEN",
               class_ids=["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
               artifact_type=atype, path=artifacts[key], sha256=H[key],
               validation_status="unverified",
               summary=summ,
               evidence_refs=base_evidence)
        if key == "report":
            e["verdict"] = "REVISE"
        events.append(e)

    events.append(ev(f"w080-h2e-{stamp}-review", "review", at,
                     node_id="F2b", gate="G-FORM",
                     class_id="AF-SCC-C0-VAC-GEN",
                     class_ids=["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
                     target_id="F2b repair candidate 84b5d3fa29a677ad",
                     artifact=artifacts["rebased"], target_sha256=H["rebased"],
                     reviewer="worker-080", verdict="revise", score=2.0,
                     hard_failures=["entailment_direction_inverted", "normative_contradiction"],
                     findings=report["findings"],
                     evidence_refs=base_evidence, falsifier=falsifier,
                     summary=("Revise the 2-edit repair candidate: H1 is correctly repaired, H2 is replaced with a "
                              "class-relative sentence that is true in the C2 file and false in the C0 file.")))

    events.append(ev(f"w080-h2e-{stamp}-claim", "claim", at,
                     node_id="F2b", gate="G-FORM",
                     class_id="AF-SCC-C0-VAC-GEN",
                     class_ids=["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
                     conclusion_type="formal_model",
                     statement=("At live F2b rev13 schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe (FROZEN rev29 815e08079aef), "
                                "the circulating 2-edit repair candidate 84b5d3fa (reproduced independently from live plus the two "
                                "published edits; byte-identical to artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml) "
                                "fixes H1 but introduces a hard entailment inversion: its regularity.must_not_conflate[0] replacement at "
                                ":152 asserts 'H2_loc-inextendibility ENTAILS this class's conclusion', while the file's own chain at :239 "
                                "(E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2) and its one_way_entailments :241-243 make the class "
                                "conclusion entail H2_loc-inextendibility, and its retained forbidden_weakenings row :232 states "
                                "'H2_loc-inextendibility is weaker and entails the C2 sibling, not this class'. The same sentence is correct in "
                                "the C2 sibling at schemas/af_scc_c2_vacuum.yaml:152, so the defect is a cross-class copy of a class-relative "
                                "claim. Two corrected H2 wordings (explicit direction; nesting+pointer) are finding-free under the same "
                                "checker and pass the canonical structural gate, which also passes the defective candidate (blind)."),
                     assumptions=[
                         "the file's own extension_class_containment chain is the internal ground truth for containment order",
                         "the phrase 'this class' resolves to the file's class_id (AF-SCC-C0-VAC-GEN), per the frozen class contract",
                         "the canonical structural gate is used unmodified at its pinned hash",
                         "artifacts are validation_status=unverified; a reviewer/owner verdict is required before any adoption",
                     ],
                     falsifier=falsifier,
                     evidence_refs=base_evidence,
                     artifact_refs=[{"path": artifacts["report"], "sha256": H["report"]},
                                    {"path": artifacts["harness"], "sha256": H["harness"]},
                                    {"path": artifacts["corrected"], "sha256": H["corrected"]}],
                     not_claimed=not_claimed))

    events.append(ev(f"w080-h2e-{stamp}-blocker", "blocker", at,
                     node_id="F2b", gate="G-FORM",
                     class_id="AF-SCC-C0-VAC-GEN",
                     class_ids=["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
                     description=("Do not land the circulating F2b 2-edit repair as-is: candidate 84b5d3fa "
                                  "(= artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml) replaces the H2 "
                                  "containment denial with 'H2_loc-inextendibility ENTAILS this class's conclusion', a false "
                                  "entailment in the C0 context that contradicts F2b :232/:239/:241-243 and would re-issue an "
                                  "order-relative hard finding at rev14."),
                     needed_to_unblock=("astra-lead-formulation (owner): land the H1 edit unchanged plus one of the two corrected H2 "
                                        "wordings staged in artifacts/worker-080/f2b_repair_entailment_audit/staged/ (explicit right "
                                        "direction, or nesting+pointer only), bump revision, mirror byte-identically, re-freeze, and "
                                        "re-emit the artifact event; then lead-audit's G-FORM r3 reviewer re-runs "
                                        "artifacts/worker-080/f2b_repair_entailment_audit/audit_h2_entailment.py and "
                                        "artifacts/worker-066/f2b_rev29_containment_binding/rebind.py at the new hash and requires "
                                        "zero findings under both taxonomies. Alternatively the owner records why the H2 entailment "
                                        "direction is meant otherwise, which voids this blocker only if the recorded reading is "
                                        "consistent with :232."),
                     evidence_refs=base_evidence, falsifier=falsifier))

    events.append(ev(f"w080-h2e-{stamp}-status-final", "status", at,
                     node_id="F2b", gate="G-FORM",
                     class_id="AF-SCC-C0-VAC-GEN",
                     class_ids=["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
                     status="active", hours=0.8,
                     summary=("W080-F2B-REPAIR-H2E-01 complete from the worker side: one bounded class-bound task, read-only on canonical "
                              "paths. The circulating F2b repair fixes H1 but introduces an entailment inversion in H2; corrected "
                              "candidates are staged (candidate_corrected 51c253c46306, candidate_nesting_only 4951cc969803), both "
                              "finding-free with gate PASS. Report f0dae0292f1d, harness ad9bb13cb541, patch 174f40ea586e. Checkpoint "
                              "written to runtime/state/w080_f2b_repair_entailment_checkpoint.json. No gate verdict; no canonical write."),
                     evidence_refs=base_evidence,
                     next_falsifier=falsifier, not_claimed=not_claimed))

    with OUTBOX.open("a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    # validate: every line of the outbox parses and carries the required keys
    bad = 0
    for i, ln in enumerate(OUTBOX.read_text(encoding="utf-8").splitlines(), 1):
        if not ln.strip():
            continue
        try:
            o = json.loads(ln)
        except Exception as exc:  # noqa: BLE001
            bad += 1
            print(f"line {i}: INVALID JSON: {exc}")
            continue
        missing = [k for k in ("event_id", "event_type", "created_at", "actor") if k not in o]
        if missing:
            bad += 1
            print(f"line {i}: missing {missing}")
    print(json.dumps({"appended": len(events), "outbox": str(OUTBOX.relative_to(ROOT)),
                      "lines": sum(1 for _ in OUTBOX.open(encoding='utf-8')),
                      "invalid_lines": bad}, indent=1))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
