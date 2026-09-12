#!/usr/bin/env python3
"""Emit the W047-F2A-REV13-VERDICT-01 outbox events (idempotent, schema-checked)."""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "comms/outbox/worker-047.jsonl")
TASK = "W047-F2A-REV13-VERDICT-01"
TARGET = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
CLASS = "AF-SCC-C2-VAC-GEN"

H = {
    "checker": "349e7729e3d84032019c2d10882bcb9243216df65380c2b9dc44167dd0b61427",
    "report": "2bb172b8f6550d1ccfe7d62a8835c6ec814489bc6e984e2013552626597be97c",
    "review_md": "8d2c6cc148ed57ccbb44865291c5e018ed624884727055a4322dfceba6cc7265",
    "review_json": "ef02052cfbf159213dcca5124887fa088a0d672e928b7b2422ba7b3c1a229169",
    "classsep": "d672867e5e985c0ca42750c176332e40c394506e0f941eda804be53a9e1b7683",
    "sums": "6e67132398a853208ef5c1608b222858eed243d02b03657cee50a4ba9dc074c5",
    "manifest": "1dda6433b4da9dcd0721615062e4e1a54c53ab7b49b77d15f5ab5077016f4fa1",
    "checkpoint": "4137769736db893470e68621ce250e68476486ac6a76c24bbeb42f725764f066",
}
SHORT = {k: v[:12] for k, v in H.items()}
NOW = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
TS = NOW.replace("-", "").replace(":", "").replace("+", "").replace("T", "T")[:15]
NEXT_FALSIFIER = (
    "At the pins in artifacts/worker-047/f2a_rev13_verdict/snapshot/SHA256SUMS: falsified if (a) any content pin "
    "differs on re-measure; (b) a repaired F2a freezes the differentiable category of M' and the regularity of iota "
    "and G23/G24 re-run PASS; (c) F2a's conclusion_type and genericity_kind become exact members of the F0 allowed "
    "lists (or the controller records an alias-equivalence ruling AND F2a declares the registry pointer) and G39/G40 "
    "re-run PASS; or (d) any of the 16 controls stops discriminating. A later file write at a different hash voids "
    "this verdict; it does not falsify it."
)
EV = f"artifacts/worker-047/f2a_rev13_verdict"
REFS_MAIN = [
    f"{EV}/report.json#{SHORT['report']}",
    f"{EV}/check_f2a_rev13_verdict.py#{SHORT['checker']}",
    f"{EV}/REVIEW.md#{SHORT['review_md']}",
    f"reviews/F2a-review-rev13-047.json#{SHORT['review_json']}",
    f"schemas/af_scc_c2_vacuum.yaml#{TARGET[:12]}",
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
    "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
]


def art(eid, atype, path, sha, node="F2a", note="", refs=None):
    return {
        "event_id": eid, "event_type": "artifact", "created_at": NOW, "actor": "worker-047",
        "node_id": node, "class_id": CLASS, "class_ids": [CLASS], "gate": "G-FORM",
        "task_id": TASK, "artifact_type": atype, "path": path, "sha256": sha,
        "validation_status": "unverified", "note": note, "evidence_refs": refs or REFS_MAIN,
    }


EVENTS = [
    {
        "event_id": f"w047-f2a13-{TS}-status-claim", "event_type": "status", "created_at": NOW,
        "actor": "worker-047", "node_id": "F2a", "class_id": CLASS, "class_ids": [CLASS],
        "gate": "G-FORM", "task_id": TASK, "status": "active", "hours": 0.2,
        "checkpoint": "w047-cp5-f2a-rev13",
        "summary": ("No assignment card exists in comms/inbox for worker-047 (relaunched slot). Took ONE bounded "
                    "class-bound task: W047-F2A-REV13-VERDICT-01 = fresh independent full-schema verdict on "
                    "AF-SCC-C2-VAC-GEN (F2a) at the LIVE rev13 pin e9a27996 (FROZEN rev29). Reason: worker-091's "
                    "F2a review is bound to the superseded rev12 pin 5476a3f2 and itself declares "
                    "counts_as_coverage_for_live_revision=false with 'fresh verdict required at e9a27996'; no "
                    "verdict bound to the live pin existed. Instrument: 39 criteria over identity, F0 contract, "
                    "quantifiers, conclusion, extension predicate, implication ledger, genericity, topology, data "
                    "class, I+/visibility, falsifier, anti-scope, status honesty and vocabulary; 16/16 mutation "
                    "controls; read-only outside this task's directory."),
        "evidence_refs": REFS_MAIN, "next_falsifier": NEXT_FALSIFIER,
    },
    art(f"w047-f2a13-{TS}-art-checker", "verifier",
        f"{EV}/check_f2a_rev13_verdict.py", H["checker"],
        note=("Stdlib+PyYAML, deterministic (double-run byte-identical), fail-closed pins (exit 2 on content drift; "
              "FROZEN manifest pinned semantically by revision 29 + F2a entry), 14 targeted mutation controls + "
              "duplicate-key + future-date + one positive control (exit 3 on control failure).")),
    art(f"w047-f2a13-{TS}-art-report", "verification_report", f"{EV}/report.json", H["report"],
        note=("status=REVISE, 35/39 criteria pass, hard_fail G23/G24/G39/G40, controls 16/16, pin_stable=true; "
              "machine-readable checks, controls, pins, sibling comparison and classsep corroboration.")),
    art(f"w047-f2a13-{TS}-art-reviewmd", "review_note", f"{EV}/REVIEW.md", H["review_md"],
        note="Human-readable full-schema verdict: method, verdict, two hard axes, closed rev13 repairs, non-claims, falsifier, reproduction."),
    art(f"w047-f2a13-{TS}-art-reviewjson", "review_record", "reviews/F2a-review-rev13-047.json", H["review_json"],
        note="Canonical review record at the live pin: revise 3.5, counts_as_full_schema_verdict=true, HF-047-01/HF-047-02 with falsifiers."),
    art(f"w047-f2a13-{TS}-art-classsep", "evidence", f"{EV}/evidence/classsep_f2a.json", H["classsep"],
        note=("Canonical research_map/class_separation.py on the F2a bytes: 0 findings; regression PASS "
              "(17 TP / 10 TN / 0 FN / 0 FP, corpus 27) - class identity corroboration.")),
    art(f"w047-f2a13-{TS}-art-sums", "pinned_input_snapshot", f"{EV}/snapshot/SHA256SUMS", H["sums"],
        note="Frozen copies and sha256 of the 8 pinned inputs at scan time (F2a e9a27996, F2b b2ab6acb, F1 d9cebb94, F0 0abb9ed8a961 + supplement d7419b4e8963, evidence 9e335e9b, VOCAB_ALIASES 46cd9f1e, FROZEN rev29)."),
    art(f"w047-f2a13-{TS}-art-manifest", "artifact_manifest", f"{EV}/MANIFEST.json", H["manifest"],
        note="Measured sha256 + byte size of each deliverable; pins, verdict census and canonical_edits=none."),
    art(f"w047-f2a13-{TS}-art-checkpoint", "worker_checkpoint", f"{EV}/checkpoint.json", H["checkpoint"],
        note=("checkpoint_id w047-cp5-f2a-rev13; byte-identical copy at "
              "runtime/state/w047_f2a_rev13_verdict_checkpoint.json; worker-level complete; node status and gate "
              "verdicts deliberately unchanged.")),
    {
        "event_id": f"w047-f2a13-{TS}-review-fullschema", "event_type": "review", "created_at": NOW,
        "actor": "worker-047", "reviewer": "worker-047",
        "reviewer_role": "bounded execution worker (independent; did not author F2a, F0, F1, F2b or any earlier F2a verdict)",
        "group_id": "formulation", "target_id": "F2a", "node_id": "F2a", "class_id": CLASS,
        "class_ids": [CLASS], "gate": "G-FORM", "task_id": TASK,
        "artifact": "schemas/af_scc_c2_vacuum.yaml", "artifact_path": "schemas/af_scc_c2_vacuum.yaml",
        "artifact_sha256": TARGET, "reviewed_sha256": TARGET, "reviewed_revision": 13,
        "counts_as_full_schema_verdict": True, "counts_as_independent": True,
        "review_file": "reviews/F2a-review-rev13-047.json",
        "review_file_sha256": H["review_json"],
        "verdict": "revise", "score": 3.5,
        "hard_failures": [
            "HF-047-01 (G23,G24, critical): extension_predicate does not freeze the differentiable category of M' nor the regularity of iota; sibling F2b DOES freeze M' as SMOOTH (C-infinity) after accepted repair F2b-16-03, so the authoring convention exists and F2a diverges; containment ledger and tier-1 isometry step are only well-typed once frozen.",
            "HF-047-02 (G39,G40, major/blocking): conclusion_type=scc_c2_future_inextendibility and genericity.kind=residual_comeager are VOCAB_ALIASES canonicals while F0 allowed lists hold only their aliases, and F2a declares no alias-registry pointer; authority must be single-sourced (repair may be F0-side).",
        ],
        "findings": [
            "CLOSED at rev13: worker-091 HF-091-01 / worker-090 W090-F2A-01 stale consistency-evidence hash - G06 passes (declared 9e335e9b resolves; consistent=true, 4 classes).",
            "worker-091 HF-091-02 independently reproduced and sharpened with the F2b sibling precedent.",
            "worker-090 W090-VOCAB-01/-04 independently re-measured at rev13 inside a full-schema verdict.",
            "Class identity CLEAN: canonical class separation 0 findings; regression PASS (17 TP / 10 TN / 0 FN / 0 FP).",
            "33 further criteria pass (identity, F0 pointer/axes, quantifier order, negation, D0 disjoint union, conclusion, clauses (a)-(f), containment in all three locations, genericity, topology, data class, I+/visibility, falsifier, anti-scope, status honesty, non-vacuity).",
            "FROZEN.json was rewritten at 00:57:26 within revision 29 (delta note only) with the F2a entry unchanged; recorded, not treated as content drift.",
        ],
        "conditions": [
            "binds only schemas/af_scc_c2_vacuum.yaml sha256 " + TARGET + "; any other measured hash voids it",
            "one independent full-schema verdict at this hash; G-FORM still needs two distinct accepts at one frozen revision",
            "does not re-adjudicate the physics or which of F0/registry owns the vocabulary authority",
            "no canonical artifact was written or edited",
        ],
        "evidence_refs": REFS_MAIN, "next_falsifier": NEXT_FALSIFIER,
    },
    {
        "event_id": f"w047-f2a13-{TS}-claim-measured", "event_type": "claim", "created_at": NOW,
        "actor": "worker-047", "node_id": "F2a", "class_id": CLASS, "class_ids": [CLASS],
        "gate": "G-FORM", "task_id": TASK, "conclusion_type": "formal_model",
        "statement": ("Measured property of schemas/af_scc_c2_vacuum.yaml at sha256 e9a27996dfd3 (rev13, FROZEN "
                      "rev29; F0 0abb9ed8a961, supplement d7419b4e8963, evidence 9e335e9b, VOCAB_ALIASES 46cd9f1e): "
                      "35/39 full-schema criteria pass, class identity is clean (canonical separator 0 findings; "
                      "regression PASS), and the rev13 consistency-evidence repair is verified closed. Four hard "
                      "criteria fail on two axes: (1) the extension predicate freezes neither the differentiable "
                      "category of M' nor the regularity of iota (G23/G24), while the C0 sibling F2b freezes M' as "
                      "SMOOTH after accepted repair F2b-16-03; (2) conclusion_type and genericity_kind are "
                      "VOCAB_ALIASES canonicals while F0's allowed lists hold only their aliases, and F2a declares no "
                      "alias-registry pointer (G39/G40). 16/16 mutation controls discriminate; pins stable; no "
                      "canonical writes."),
        "assumptions": [
            "the measured sha256 is the artifact identity; a path without a hash binds nothing",
            "a schema criterion is a property of the pinned bytes, not of the author's intent",
            "exact membership in the pointer-resolved F0 allowed list is the default conformance rule; alias-aware equivalence requires a recorded authority ruling (none is present at the pins)",
            "class identity and mathematical truth are disjoint: this claim asserts nothing about cosmic censorship",
            "the FROZEN manifest is a concurrently-rewritten log and is pinned semantically (revision 29 + F2a entry)",
        ],
        "artifact_refs": [
            f"{EV}/report.json#{SHORT['report']}", f"{EV}/REVIEW.md#{SHORT['review_md']}",
            f"{EV}/check_f2a_rev13_verdict.py#{SHORT['checker']}",
            f"reviews/F2a-review-rev13-047.json#{SHORT['review_json']}",
        ],
        "evidence_refs": REFS_MAIN, "falsifier": NEXT_FALSIFIER,
    },
    {
        "event_id": f"w047-f2a13-{TS}-blocker", "event_type": "blocker", "created_at": NOW,
        "actor": "worker-047", "node_id": "F2a", "class_id": CLASS, "class_ids": [CLASS],
        "gate": "G-FORM", "task_id": TASK,
        "description": ("F2a cannot be cleanly accepted at e9a27996: (HF-047-01) extension_predicate clause (a) "
                        "'iota: M -> M' is an isometric embedding' and topology.extension_topology 'M' is a "
                        "connected 4-manifold' fix neither iota's differentiability class nor M''s manifold "
                        "category, while the F2b sibling froze M' as SMOOTH (C-infinity) in the accepted F2b-16-03 "
                        "repair; (HF-047-02) conclusion_type=scc_c2_future_inextendibility and "
                        "genericity.kind=residual_comeager are registry canonicals absent from the F0 allowed lists "
                        "(which hold only their aliases), and F2a declares no VOCAB_ALIASES.json pointer."),
        "needed_to_unblock": ("Owner lead-formulation (F2a schema, F0/registry vocabulary single-sourcing with "
                              "lead-audit/controller): (R1) freeze the differentiable category of M' and the "
                              "regularity of iota in extension_predicate/topology, following the F2b clause (c) "
                              "precedent, then re-freeze and re-emit; (R2) make the conclusion_type and "
                              "genericity_kind authority single-sourced (F0 allowed lists vs VOCAB_ALIASES "
                              "canonicals) and record it; if alias equivalence is the ruling, add the registry "
                              "pointer to F2a. Then re-run this instrument: G23/G24 and G39/G40 must PASS and an "
                              "independent fresh verdict is required at the new hash."),
        "evidence_refs": REFS_MAIN,
    },
    {
        "event_id": f"w047-f2a13-{TS}-status-final", "event_type": "status", "created_at": NOW,
        "actor": "worker-047", "node_id": "F2a", "class_id": CLASS, "class_ids": [CLASS],
        "gate": "G-FORM", "task_id": TASK, "status": "active", "hours": 0.6, "checkpoint": "final",
        "summary": ("FINAL: bounded task delivered and exiting cleanly. W047-F2A-REV13-VERDICT-01 is the first "
                    "full-schema verdict bound to the LIVE F2a rev13 pin e9a27996: revise 3.5, "
                    "counts_as_full_schema_verdict=true, 35/39 checks pass, 16/16 controls, pins stable, no "
                    "canonical writes. Deliverables exist on disk and are hash-pinned (checker, report, REVIEW.md, "
                    "canonical review record, classsep evidence, snapshot, MANIFEST, checkpoint + runtime/state "
                    "copy). Worker events cannot set done/passed or gate verdicts; next owner actions are R1/R2 in "
                    "the blocker and a fresh independent verdict at the repaired hash."),
        "evidence_refs": [
            f"{EV}/checkpoint.json#{SHORT['checkpoint']}", f"{EV}/MANIFEST.json#{SHORT['manifest']}",
            f"{EV}/report.json#{SHORT['report']}", f"reviews/F2a-review-rev13-047.json#{SHORT['review_json']}",
        ],
        "next_falsifier": NEXT_FALSIFIER,
    },
]


def main():
    existing = set()
    if os.path.exists(OUT):
        for line in open(OUT, encoding="utf-8"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except ValueError:
                    pass
    new = [e for e in EVENTS if e["event_id"] not in existing]
    with open(OUT, "a", encoding="utf-8") as fh:
        for e in new:
            fh.write(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n")
    print(json.dumps({"appended": len(new), "skipped_existing": len(EVENTS) - len(new)}))


if __name__ == "__main__":
    main()
