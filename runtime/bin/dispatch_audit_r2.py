#!/usr/bin/env python3
"""Audit lead, lifecycle 05: dispatch the pass-04 blind review round (r2).

Cards (from research_map.json assignments astra-life04-verify-gform-r2,
astra-life04-verify-gf0-r2, astra-life04-verify-a0, astra-life04-n0-verify):

  F1  x2, F2a x2, F2b x2  -> reviews/G-FORM-final-verify-r2.json (lead adjudication)
  F0  x2                  -> reviews/G-F0-final-verify-r2.json
  A0  x1                  -> reviews/A0-review-final-verify.json
  N0  x1                  -> reviews/N0-review-final-verify.json

Each card is written to the reviewer's inbox (downward channel) and emitted as an
assignment event so it also lands in the map. Reviews must be blind: the reviewer
hashes the artifact and writes a verdict without reading any other verdict for the
same target. Verdicts cite the full sha256; a moved hash voids the verdict.

Idempotent: re-running skips event_ids already in the accepted stream.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import comms  # noqa: E402

F1_SHA = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
F2A_SHA = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
F2B_SHA = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_COMPANION_SHA = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
A0_SHA = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"

COMMON = (
    "BLIND independent review. You may NOT be an author of the artifact and you may NOT read "
    "any other reviewer's verdict for this target before writing yours (reviews/*<TARGET>* are "
    "off-limits until your file is written). Do not edit the artifact. (1) sha256 the file "
    "yourself immediately before and after reading; if either differs from the pin below, STOP "
    "and emit a `blocker` (moving target) instead of a verdict. (2) Read the artifact from disk "
    "and check: class leakage (a C2 statement smuggled into C0, or a C0/C2 merge), conclusion "
    "inflation (a theorem/counterexample promoted from a model or calibration), assumption "
    "completeness, decidable falsifier, and any field two careful readers would disagree on. "
    "(3) Write ONLY the JSON verdict file named below, then emit ONE `review` event to your own "
    "outbox (comms/outbox/<you>.jsonl) with target_id, reviewer=<you>, verdict, score 0-5, "
    "hard_failures[], findings, reviewed_sha256. (4) Write one checkpoint under "
    "runtime/state/<you>_<target>_checkpoint.json. (5) Exit. Do not set gate verdicts: worker "
    "events cannot move gates or status."
)

CARDS = [
    dict(
        event_id="audit-r2-F1-a", reviewer="worker-071", target="F1",
        path="schemas/af_wcc_vacuum.yaml", pin=F1_SHA, gate="G-FORM",
        class_id="AF-WCC-VAC-GEN", out="reviews/F1-review-rev27-a.json",
        extra=("G-FORM acceptance needs exactly two independent full-schema verdicts per class at "
               "the rev27 pin. Check the 26 acceptance fields, exact quantifiers, D0 binder "
               "typing, topology/data-class/genericity/I+/visibility clauses, conclusion_type, "
               "the falsifier rows in schemas/f1_falsifier_tests.jsonl (each must carry "
               "binding_sha256 == the pin), and that no WCC statement entails SCC."),
        falsifier=("A verdict whose cited sha256 is not the pin, a verdict authored by an artifact "
                   "author, two 'independent' verdicts sharing text, or an accept that ignores a "
                   "duplicate YAML key / ill-typed binder / dangling pointer."),
    ),
    dict(
        event_id="audit-r2-F1-b", reviewer="worker-085", target="F1",
        path="schemas/af_wcc_vacuum.yaml", pin=F1_SHA, gate="G-FORM",
        class_id="AF-WCC-VAC-GEN", out="reviews/F1-review-rev27-b.json",
        extra=("Independent second verdict, same pin. Additionally probe cross-artifact "
               "consistency with F2a/F2b on the shared fields (data_class, regularity, "
               "extension_predicate) and report any mismatch as a finding, not as a hard failure "
               "unless it changes the class statement."),
        falsifier=("A verdict whose cited sha256 is not the pin, copied findings from another "
                   "reviewer, or an accept with an unresolved dangling symbol."),
    ),
    dict(
        event_id="audit-r2-F2a-a", reviewer="worker-046", target="F2a",
        path="schemas/af_scc_c2_vacuum.yaml", pin=F2A_SHA, gate="G-FORM",
        class_id="AF-SCC-C2-VAC-GEN", out="reviews/F2a-review-rev27-a.json",
        extra=("Check that the C2 schema does NOT collapse into C0: the strong-censorship "
               "conclusion must be a distinct conclusion_type with its own control/regularity "
               "signature; verify the D0 binder is instantiable on every disjunct (the rev27 "
               "repair targets the old ill-typed D0)."),
        falsifier=("An accept where C2 and C0 carry the same conclusion_type without a decisive "
                   "axis, or a verdict at a superseded hash."),
    ),
    dict(
        event_id="audit-r2-F2a-b", reviewer="worker-091", target="F2a",
        path="schemas/af_scc_c2_vacuum.yaml", pin=F2A_SHA, gate="G-FORM",
        class_id="AF-SCC-C2-VAC-GEN", out="reviews/F2a-review-rev27-b.json",
        extra=("Independent second verdict, same pin. Re-derive the field matrix from the file "
               "and compare it to the C0 file structure; state explicitly whether C2/C0 "
               "separation is carried by content or only by naming."),
        falsifier=("An accept justified only by prose, or a verdict at a superseded hash."),
    ),
    dict(
        event_id="audit-r2-F2b-a", reviewer="worker-015", target="F2b",
        path="schemas/af_scc_c0_vacuum.yaml", pin=F2B_SHA, gate="G-FORM",
        class_id="AF-SCC-C0-VAC-GEN", out="reviews/F2b-review-rev27-a.json",
        extra=("Check that the C0 schema does not silently import a C2 assumption and that its "
               "conclusion_type is distinguishable from the C2 conclusion. The known soft flag "
               "is candidate-variant class tokens near schemas/af_scc_c0_vacuum.yaml:316; "
               "dispose of it explicitly (annotation vs leak) or record a documented blind spot."),
        falsifier=("An accept that leaves the candidate-variant token undisposed, or a verdict "
                   "at a superseded hash."),
    ),
    dict(
        event_id="audit-r2-F2b-b", reviewer="worker-035", target="F2b",
        path="schemas/af_scc_c0_vacuum.yaml", pin=F2B_SHA, gate="G-FORM",
        class_id="AF-SCC-C0-VAC-GEN", out="reviews/F2b-review-rev27-b.json",
        extra=("Independent second verdict, same pin. Independently re-run the class-separation "
               "regression if available (runtime/bin/classsep_regression.py) and report the "
               "fixture counts you measured."),
        falsifier=("An accept that leaves the C0/C2 regularity distinction unstated, or a verdict "
                   "at a superseded hash."),
    ),
    dict(
        event_id="audit-r2-F0-a", reviewer="worker-041", target="F0",
        path="research_map/formulation_taxonomy.yaml", pin=F0_SHA, gate="G-F0",
        class_id="GLOBAL", out="reviews/F0-review-rev27-a.json",
        extra=(f"F0 rev5 canonical pin {F0_SHA[:12]}; the authoring/tree copy "
               f"artifacts/formulation/formulation_taxonomy.yaml is a COMPANION (pin "
               f"{F0_COMPANION_SHA[:12]}), not a mirror: REC-3 makes byte-identity impossible and "
               "unnecessary. Accept the pair only via a supplement CONSISTENCY check (same class "
               "ids, same statements, no contradictory clause); do NOT fail it for byte "
               "difference. Verify exactly four separate class ids and that the disjointness "
               "tests hold."),
        falsifier=("A verdict pinned to any superseded F0 hash, a verdict that fails the "
                   "companion pair for byte-inequality, or an accept with fewer/more than four "
                   "class ids."),
    ),
    dict(
        event_id="audit-r2-F0-b", reviewer="worker-052", target="F0",
        path="research_map/formulation_taxonomy.yaml", pin=F0_SHA, gate="G-F0",
        class_id="GLOBAL", out="reviews/F0-review-rev27-b.json",
        extra=("Independent second verdict, same pin. Re-check the four gate criteria: four "
               "separate class ids; disjointness tests; single-q visibility predicate; explicit "
               "comeager quantifier; and the companion-supplement consistency evidence in "
               "artifacts/formulation/evidence/f0_mirror_disposition.json."),
        falsifier=("A verdict pinned to a superseded hash, or an accept that never states the "
                   "companion consistency evidence it relied on."),
    ),
    dict(
        event_id="audit-r2-A0", reviewer="worker-089", target="A0",
        path="evaluation_rubric.yaml", pin=A0_SHA, gate="G-AUDIT",
        class_id="GLOBAL", out="reviews/A0-review-worker-089.json",
        extra=("One independent verdict at the measured A0 rubric pin. The three on-disk "
               "verdicts are revises with hash-bound findings: (a) HF-01 conformance reads "
               "claim.artifact_refs which is absent from ledger rows; (b) G-FORM genericity "
               "vocabulary excludes residual_comeager; (c) conclusion_primary="
               "future_asymptotic_predictability promotes an equivalence F1 marks UNVERIFIED; "
               "(d) validation.last_run=null. State for EACH finding whether it is resolved, "
               "unresolved, or out of scope, with line numbers. Do not edit the rubric."),
        falsifier=("A verdict without a cited hash, an accept that leaves any prior finding "
                   "unadjudicated, or a rubric edit during the round."),
    ),
    dict(
        event_id="audit-r2-N0", reviewer="worker-012", target="N0",
        path="numerics/CONVERGENCE_PROTOCOL.md", pin=None, gate="G-NUM",
        class_id="AF-WCC-SCALAR-SPH", out="reviews/N0-review-worker-012.json",
        extra=("Hash the protocol, numerics/results/flat_wave_convergence.json, "
               "numerics/results/flat_wave_replication.json and the N0 stop-rule evidence "
               "yourself and pin all measured hashes in the verdict. Check each stop-rule item at "
               "those hashes: (1) a fourth resolution rung OR an explicit 3-level scoping with "
               "tolerance justification; (2) class binding re-bound to declared F0 rev5 "
               "0abb9ed8a961; (3) one independent replication verdict of the order. Then check "
               "the lock guard: numerics/spherical_solver must be absent and no N1 artifact may "
               "appear in the reviewed evidence. N0-only. Accept only if every stop-rule item is "
               "closed at one hash; otherwise revise and name the open item."),
        falsifier=("A verdict at a stale hash, an accept that leaves a stop-rule item open, any "
                   "spherical_solver file, or any N1 artifact in the reviewed evidence."),
    ),
]


def main():
    ok = 0
    for c in CARDS:
        pin_txt = c["pin"] if c["pin"] else "measure it yourself and pin it"
        ev = {
            "event_id": c["event_id"],
            "event_type": "assignment",
            "created_at": comms.now(),
            "actor": "astra-lead-audit",
            "node_id": c["target"],
            "assignee": c["reviewer"],
            "artifact": c["out"],
            "gate": c["gate"],
            "class_id": c["class_id"],
            "evidence_refs": [f"{c['path']}#{pin_txt}",
                              "artifacts/formulation/FROZEN.json",
                              "comms/PROTOCOL.md",
                              "research_map/ASTRA_HANDOFF.md:36-48"],
            "falsifier": c["falsifier"],
            "acceptance": COMMON.replace("<TARGET>", c["target"]) + " " + c["extra"],
            "task": (f"Independent blind {c['gate']} review of {c['target']} "
                     f"({c['path']}) at pin {pin_txt}. Write {c['out']}. "
                     f"Then emit one review event and one checkpoint, and exit."),
            "budget_agent_hours": 1.0,
            "expected_information_gain": ("Gate G-FORM/G-F0/G-AUDIT/G-NUM requires independent "
                                          "verdicts at the pinned hash; this is one of them."),
            "stop_rule": "1 agent-hour; one verdict file + one review event + one checkpoint, then exit.",
            "deadline": "2026-09-12T02:15:00+08:00",
        }
        comms.send(c["reviewer"], ev)
        r = comms.append_event(ev)
        ok += 1 if r.get("accepted") else 0
        print(f"{'OK ' if r.get('accepted') else 'DUP'} {c['event_id']:<16} -> {c['reviewer']:<11} {c['out']}")
    print(f"dispatched {ok}/{len(CARDS)} accepted (duplicates are skipped)")


if __name__ == "__main__":
    main()
