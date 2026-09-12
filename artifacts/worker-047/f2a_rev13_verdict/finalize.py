#!/usr/bin/env python3
"""Assemble the W047-F2A-REV13-VERDICT-01 deliverable set and hash ledger.

Writes (all outside canonical artifacts):
  reviews/F2a-review-rev13-047.json        canonical review record
  <task>/snapshot/SHA256SUMS               frozen input manifest (regenerated clean)
  <task>/MANIFEST.json                     deliverable hash ledger
  <task>/checkpoint.json                   worker-local checkpoint
  runtime/state/w047_f2a_rev13_verdict_checkpoint.json   byte-identical copy
Prints the hash table used for the outbox events.
"""
import hashlib
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TASK = "W047-F2A-REV13-VERDICT-01"
TARGET_SHA = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
PINS = {
    "schemas/af_scc_c2_vacuum.yaml": TARGET_SHA,
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    drift = {rel: {"expected": want, "measured": sha(os.path.join(ROOT, rel))}
             for rel, want in PINS.items()}
    drift = {k: v for k, v in drift.items() if v["expected"] != v["measured"]}
    if drift:
        raise SystemExit(f"PIN DRIFT: {json.dumps(drift, indent=1)}")

    report = json.load(open(os.path.join(HERE, "report.json")))
    review_src = os.path.join(HERE, "REVIEW.md")
    review_md_sha = sha(review_src)

    review = {
        "schema": "class-schema-review/v1",
        "review_id": "W047-F2A-REV13-VERDICT-01",
        "event_type": "review",
        "reviewer": "worker-047",
        "reviewer_role": "bounded execution worker (independent; did not author F2a, F0, F1, F2b or any earlier F2a verdict)",
        "group_id": "formulation",
        "node_id": "F2a",
        "target_id": "F2a",
        "gate": "G-FORM",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "task_id": TASK,
        "artifact_path": "schemas/af_scc_c2_vacuum.yaml",
        "artifact": "schemas/af_scc_c2_vacuum.yaml",
        "reviewed_sha256": TARGET_SHA,
        "artifact_sha256": TARGET_SHA,
        "reviewed_revision": 13,
        "counts_as_full_schema_verdict": True,
        "counts_as_independent": True,
        "verdict": "revise",
        "score": 3.5,
        "score_rationale": "35/39 full-schema criteria pass, class identity clean (canonical separator 0 findings, regression PASS), the rev13 consistency-evidence repair is verified closed; two hard axes remain: the extension predicate does not freeze M' category / iota regularity (HF-047-01) and the F0-relative vocabulary authority is unresolved with no alias-registry pointer (HF-047-02).",
        "hard_failures": [
            {
                "id": "HF-047-01",
                "checks": ["G23", "G24"],
                "severity": "critical (blocking for G-FORM)",
                "axis": "extension predicate under-frozen: differentiable category of M' and regularity of iota",
                "finding": "extension_predicate clause (a) says only 'iota: M -> M' is an isometric embedding' and topology.extension_topology says only 'M' is a connected 4-manifold'; neither fixes a differentiability class for M' or for iota. The sibling F2b (AF-SCC-C0-VAC-GEN) DOES freeze M' as a SMOOTH (C-infinity) 4-manifold after accepted repair F2b-16-03 ('a merely topological M' cannot carry a classical Lorentzian tensor field'), so the authoring convention exists and F2a diverges from it. The containment ledger E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 and the tier-1 falsifier's isometry step are only well-typed once both are frozen.",
                "evidence_refs": [
                    "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                    "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                    "artifacts/worker-047/f2a_rev13_verdict/report.json",
                ],
                "falsifier": "A repaired F2a freezes the differentiable category of M' and the regularity of iota, and the instrument's G23/G24 re-run PASS (positive control C10 demonstrates this flip).",
            },
            {
                "id": "HF-047-02",
                "checks": ["G39", "G40"],
                "severity": "major (blocking until the authority is single-sourced)",
                "axis": "cross-artifact vocabulary authority + undeclared alias registry",
                "finding": "conclusion_type=scc_c2_future_inextendibility and genericity.kind=residual_comeager are the VOCAB_ALIASES.json canonicals, while F0's allowed lists hold only their aliases (strong_cosmic_censorship_C2 / provisional_baire_residual). Exact-membership conformance fails; alias-aware conformance succeeds only if an unrecorded ruling makes alias equivalence authoritative, and F2a declares no VOCAB_ALIASES.json pointer. F0's own classes[*].axes also carry alias tokens, so the repair may be F0-side. Independently re-measures worker-090 W090-VOCAB-01/-04 at rev13.",
                "evidence_refs": [
                    "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
                    "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                    "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
                    "artifacts/worker-047/f2a_rev13_verdict/report.json",
                ],
                "falsifier": "F2a's two axis tokens become exact members of the F0 allowed lists, or the controller records an alias-equivalence ruling and F2a declares the alias registry; the instrument's G39/G40 then re-run PASS.",
            },
        ],
        "soft_findings": [],
        "findings": [
            "CLOSED at rev13: worker-091 HF-091-01 / worker-090 W090-F2A-01 (stale f0_binding.consistency_evidence_sha256). G06 now passes: declared hash resolves to the live artifacts/formulation/evidence/taxonomy_consistency.json 9e335e9ba1bf, consistent=true over 4 classes.",
            "INDEPENDENTLY REPRODUCED: worker-091 HF-091-02, extended with the F2b sibling precedent (F2b freezes M' smooth; F2a fixes neither M' category nor iota regularity).",
            "INDEPENDENTLY RE-MEASURED at rev13 inside a full-schema verdict: worker-090 W090-VOCAB-01 (5-token inversion survives) and W090-VOCAB-04 (F2a declares no registry pointer).",
            "CLASS IDENTITY CLEAN: canonical research_map/class_separation.py findings_for_text -> 0 findings; regression PASS (17 TP / 10 TN / 0 FN / 0 FP, corpus 27).",
            "FROZEN rev29 pins schemas/af_scc_c2_vacuum.yaml at e9a27996 and FROZEN does not pin any superseded F2a; the freeze manifest itself was rewritten at 00:57:26 within revision 29 (delta note only) and its F2a entry was unchanged - recorded, not treated as content drift.",
            "33 further criteria pass: identity/single C2 token, F0 pointer and axes, quantifier order, correct negation, D0 disjoint union, conclusion family/obstruction/forbidden strengthenings-weakenings, clauses (a)-(f), frozen equation and direction, must-not-conflate, containment chain in all three locations, entailment and forbidden-transfer ledger, genericity kind/ambient/transfer/variants, topology, data class, I+/visibility roles, tiered falsifier, anti-scope, open-problem honesty, non-vacuity status.",
        ],
        "evidence_refs": [
            "artifacts/worker-047/f2a_rev13_verdict/report.json",
            "artifacts/worker-047/f2a_rev13_verdict/check_f2a_rev13_verdict.py",
            "artifacts/worker-047/f2a_rev13_verdict/REVIEW.md",
            "artifacts/worker-047/f2a_rev13_verdict/evidence/classsep_f2a.json",
            "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
        ],
        "conditions": [
            "binds only schemas/af_scc_c2_vacuum.yaml sha256 e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe; any different measured hash voids it",
            "one independent full-schema verdict at this hash; G-FORM still needs two distinct accepts at one frozen revision",
            "does not re-adjudicate the physics, the conjecture, or which of F0/registry owns the vocabulary authority",
            "no canonical artifact was written or edited by this task",
        ],
        "review_file_sha256": review_md_sha,
        "authority_note": "worker evidence only; does not set validation_status, node status or a gate verdict",
        "non_claims": [
            "not a gate verdict or node completion",
            "mathematical truth of the AF-SCC-C2-VAC-GEN statement is untouched",
            "the vocabulary failure does not decide which authority wins",
        ],
        "falsifier": "See REVIEW.md: repaired M' category + iota regularity -> G23/G24 PASS; exact F0 membership or recorded alias ruling + declared registry pointer -> G39/G40 PASS; or any content pin moves; or any control stops discriminating.",
    }

    review_path = os.path.join(ROOT, "reviews/F2a-review-rev13-047.json")
    with open(review_path, "w", encoding="utf-8") as fh:
        json.dump(review, fh, indent=1, sort_keys=True)
        fh.write("\n")

    # regenerate snapshot/SHA256SUMS cleanly
    snap = os.path.join(HERE, "snapshot")
    lines = []
    for dirpath, _, files in os.walk(snap):
        for fn in sorted(files):
            if fn == "SHA256SUMS":
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, snap)
            lines.append(f"{sha(p)}  {rel}")
    with open(os.path.join(snap, "SHA256SUMS"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(lines)) + "\n")

    deliverables = {
        "check_f2a_rev13_verdict.py": os.path.join(HERE, "check_f2a_rev13_verdict.py"),
        "report.json": os.path.join(HERE, "report.json"),
        "REVIEW.md": review_src,
        "evidence/classsep_f2a.json": os.path.join(HERE, "evidence/classsep_f2a.json"),
        "snapshot/SHA256SUMS": os.path.join(snap, "SHA256SUMS"),
        "reviews/F2a-review-rev13-047.json": review_path,
    }
    hashes = {rel: {"sha256": sha(p), "bytes": os.path.getsize(p)} for rel, p in deliverables.items()}
    manifest = {
        "schema": "w047-f2a-rev13-verdict-manifest/v1",
        "task_id": TASK,
        "actor": "worker-047",
        "target": {"path": "schemas/af_scc_c2_vacuum.yaml", "class_id": "AF-SCC-C2-VAC-GEN",
                   "node_id": "F2a", "revision": 13, "sha256": TARGET_SHA},
        "pins": PINS,
        "verdict": report["verdict"],
        "summary": report["summary"],
        "controls_pass": report["controls_pass"],
        "deliverables": hashes,
        "verifier_exit_code": report["exit_code"],
        "canonical_edits": "none",
        "note": "self-hash excluded by construction; recorded in the artifact event and checkpoint",
    }
    man_path = os.path.join(HERE, "MANIFEST.json")
    with open(man_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")

    checkpoint = {
        "schema": "w047-worker-checkpoint/v1",
        "checkpoint_id": "w047-cp5-f2a-rev13",
        "task_id": TASK,
        "actor": "worker-047",
        "instance": "worker-047-20260912T005347-968807",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "status": "worker_level_complete",
        "verdict": "revise",
        "score": 3.5,
        "counts_as_full_schema_verdict": True,
        "target_sha256": TARGET_SHA,
        "summary": report["summary"],
        "controls_pass": report["controls_pass"],
        "deliverable_hashes": {k: v["sha256"] for k, v in hashes.items()},
        "manifest_sha256": sha(man_path),
        "runtime_state_copy": "runtime/state/w047_f2a_rev13_verdict_checkpoint.json",
        "authority_note": "worker-local checkpoint; node status and gate verdicts deliberately unchanged",
    }
    cp_path = os.path.join(HERE, "checkpoint.json")
    with open(cp_path, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)
        fh.write("\n")
    shutil.copyfile(cp_path, os.path.join(ROOT, "runtime/state/w047_f2a_rev13_verdict_checkpoint.json"))

    out = {
        "checkpoint.json": sha(cp_path),
        "MANIFEST.json": sha(man_path),
        "report.json": hashes["report.json"]["sha256"],
        "check_f2a_rev13_verdict.py": hashes["check_f2a_rev13_verdict.py"]["sha256"],
        "REVIEW.md": hashes["REVIEW.md"]["sha256"],
        "reviews/F2a-review-rev13-047.json": hashes["reviews/F2a-review-rev13-047.json"]["sha256"],
        "evidence/classsep_f2a.json": hashes["evidence/classsep_f2a.json"]["sha256"],
        "snapshot/SHA256SUMS": hashes["snapshot/SHA256SUMS"]["sha256"],
        "verdict": report["verdict"],
        "hard_fail": report["summary"]["hard_fail"],
    }
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
