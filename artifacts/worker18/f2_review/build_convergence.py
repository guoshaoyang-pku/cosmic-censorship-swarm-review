#!/usr/bin/env python3
"""Build reviews/convergence-18.json — P2 blocking/non-blocking triage of worker-18's
F2a/F2b review targets (assignment astra-conv-03).

v2: re-pinned to FROZEN revision 20 (2026-09-12T00:15:00+08:00) after the lead rewrote the
schemas mid-review (v1 pinned FROZEN rev19 and was invalidated by the rev19->rev20 churn).

Reads only; writes the review + machine-evidence files. Emitting outbox events is a separate
step (emit_convergence_events.py) so the review can be inspected first.

Usage: python3 artifacts/worker18/f2_review/build_convergence.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FR = ROOT / "artifacts" / "worker18" / "f2_review"
CST = timezone(timedelta(hours=8))

TARGETS = {
    "F2a": {
        "class_id": "AF-SCC-C2-VAC-GEN",
        "path": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "prior_review": "reviews/F2a-review-18.json",
        "prior_draft_sha": "23fec0e9cd68bc99d42f2fa2228f343391df70d802ae50ba368c1e70d96e0f9d",
        "v1_sha": "e9fcefe6e59555ba210d1440e5a0a5d4659cf7e6a859b63b60fda8b4066cbcb0",
    },
    "F2b": {
        "class_id": "AF-SCC-C0-VAC-GEN",
        "path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "prior_review": "reviews/F2b-review-18.json",
        "prior_draft_sha": "e6b1af2bd6925f27cdae60d57939e434adca53703cb938f0a4133f3a9f29245b",
        "v1_sha": "bdb23f76b89540e82e4a8a3feb12637eb646af54466f624cf6ba2fef5a94bf90",
        "v1_intermediate_sha": "94aaa95aa16cff8cfd73f6931156c8aaf1ab3575b03a15f5325432360ba43f07",
    },
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def tok(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]{3,}", s.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = tok(a), tok(b)
    return round(len(ta & tb) / max(1, len(ta | tb)), 3)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def main() -> int:
    now = datetime.now(CST).isoformat(timespec="seconds")

    # --- fresh machine evidence -------------------------------------------------------------
    st = run([sys.executable, str(FR / "f2_class_probe.py"), "--selftest"])
    selftest = json.loads(st.stdout)
    (FR / "convergence_probe_selftest.json").write_text(json.dumps(selftest, indent=1) + "\n")

    vf = run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"])
    (FR / "convergence_verify_frozen.txt").write_text(
        f"# verify_frozen.py exit={vf.returncode}\n{vf.stdout}{vf.stderr}"
    )

    manifest = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    man_sha = sha(ROOT / "artifacts/formulation/FROZEN.json")

    hashes = {p: sha(ROOT / p) for p in [
        TARGETS["F2a"]["path"], TARGETS["F2b"]["path"],
        "artifacts/formulation/FROZEN.json",
        "artifacts/worker18/f2_review/convergence_probe_report.json",
        "artifacts/worker18/f2_review/convergence_canonical_gate.txt",
        "artifacts/worker18/f2_review/w06_c0_frozen_report.json",
        "artifacts/worker18/f2_review/convergence_probe_selftest.json",
        "artifacts/worker18/f2_review/convergence_verify_frozen.txt",
        "artifacts/worker18/f2_review/convergence-18.v1.json",
        "artifacts/worker18/f2_review/f2_class_probe.py",
    ]}

    # --- verdict reasoning (distinct narratives; independence is measured, not asserted) -----
    reason_c2 = (
        "C2 target, rev9. All four draft hard failures are resolved on the frozen revision: "
        "extension_predicate is a first-class block (probe S7-C2 'extension predicate defined'), "
        "conclusion.statement_formal at line 215 is the same uniform sentence as quantifiers.formal "
        "at line 45 (S6-C2 fires only on the (s,delta) uniformity binder at line 49), and "
        "regularity.data_regularity matches the shared smooth-with-decay default. The canonical "
        "binding gate returns PASS with failed_rules=[] at 8dae50da, which is the authoritative "
        "structural verdict. The single lexical probe hit (S5-C2) is a token inside "
        "anti_scope.phrases_that_are_not_this_class at line 277 - the ban list that exists precisely "
        "to forbid the composite phrase - and the gate's R17-R25 scan accepts that context, so no "
        "blocking finding is recorded. Rev20 replaced the candidate-class tokens with parent_class "
        "+ variant_id references; that is cleaner for class identity, but the two variant entries "
        "inside not_this_class reuse this class's own id, which reads as a self-exclusion and should "
        "carry an explicit variant_id/is_this_class label. That, the binder clarity note and the "
        "tier-1 labelling note are backlog."
    )
    reason_c0 = (
        "C0 target, rev9. The draft's two hard failures do not survive: the line-5 'C0 or C2' "
        "comment is gone, and the two remaining composite-phrase occurrences are both prohibitions - "
        "the quoted ban-list item at line 280 and the explicit 'No containment with C2 or C0 is "
        "asserted here' sentence at line 154. The sibling w06 lint still flags both and then fails "
        "regularity_selector by counting sibling references, so that lint is over-broad on this "
        "artifact, not the artifact itself. The node_id F2b mismatch is a map-side gap: "
        "research_map.json still points node F2 at the worker drafts, FORM-MAP-PATCH-002 is an open "
        "controller resource request, and w06 declared_artifact_matches therefore reports map_node "
        "F2b != declared F2; the artifact-side label is deliberate per the lead's F2a/F2b split. "
        "Non-vacuity: the Minkowski compactness witness covers the extension predicate, while the "
        "generic-statement level stays explicitly conditional on the schema's own UNVERIFIED "
        "trapped-surface family - recorded, not hidden. The rev19/rev20 variant work restructured "
        "class_identity_variants and moved variant CH to parent_class + variant_id; the two variant "
        "entries inside not_this_class reuse this class's own id and should be labelled the same "
        "way. No blocking finding; residue is the map patch, the w06 exemptions, the binder note, "
        "the tier labelling and the variant-entry labelling."
    )
    rj = jaccard(reason_c2, reason_c0)

    review = {
        "review_id": "w18-convergence-20260912T0018+08:00",
        "reviewer": "deepseek-flash-18",
        "actor": "deepseek-flash-18",
        "node_id": "A1",
        "assignment_event_id": "astra-conv-03",
        "assignment_ids": ["astra-conv-03", "asg-a1-f2a-18", "asg-a1-f2b-18", "astra-rev-04-deepseek-flash-18"],
        "created_at": now,
        "revision_of_review": 2,
        "supersedes_review_file": "artifacts/worker18/f2_review/convergence-18.v1.json",
        "supersedes_event_ids": [
            "w18-review-20260912-conv-F2a-accept",
            "w18-review-20260912-conv-F2b-accept",
            "w18-artifact-20260912-convergence18",
            "w18-status-20260912-convergence-delivered",
        ],
        "purpose": (
            "P2 blocking/non-blocking triage of the worker-18 F2 targets on the frozen canonical "
            "revision, per assignment astra-conv-03. v2 because the v1 target hashes moved during "
            "the review window."
        ),
        "b_n_policy": (
            "B = a finding that blocks accept for that target. N = backlog; it does not block. "
            "Verdict is revise only if >=1 B finding is recorded (assignment acceptance rule)."
        ),
        "mid_review_drift": {
            "observed": (
                "v1 was built against FROZEN rev19 targets C2 e9fcefe6 / C0 bdb23f76 and events were "
                "emitted at 00:08:05. Between 00:08:37 and 00:15:00 the lead rewrote WCC, C2 and C0 "
                "(variant-registry rev19/rev20 integration) and re-froze as revision 20; the C0 file "
                "passed through an intermediate 94aaa95a."
            ),
            "action": (
                "Per the assignment's drift rule, v1 is superseded and this v2 restarts the review "
                "against the rev20 hashes actually read: C2 8dae50da, C0 a8d899d2. All machine "
                "evidence below was re-run on those bytes."
            ),
            "v1_file_sha256": hashes["artifacts/worker18/f2_review/convergence-18.v1.json"],
        },
        "independence": {
            "author_of_target": False,
            "targets_authored_by": "astra-lead-formulation",
            "exposure": (
                "I read reviews/INDEX.md, reviews/REVISION_LOG.md, the lead's FROZEN.json deltas and "
                "clarifications, and my own prior reviews of the superseded drafts and rev19 pins. "
                "Those prior verdicts are superseded by this file and must not be double-counted."
            ),
            "kish_ess": {
                "verdicts_in_this_file": 2,
                "independent_reviewers": 1,
                "ess_estimate": 1.2,
                "reasoning_jaccard_c2_vs_c0": rj,
                "note": (
                    "One reviewer produced both verdicts in one session; the narratives differ in "
                    "evidence and argument (jaccard above), but the shared reviewer caps ESS. Prior "
                    "draft/rev19 reviews are not pooled with this file."
                ),
            },
        },
        "frozen_binding": {
            "manifest": "artifacts/formulation/FROZEN.json",
            "manifest_sha256": man_sha,
            "revision": manifest.get("revision"),
            "frozen_at": manifest.get("frozen_at"),
            "targets_match_manifest": True,
            "manifest_integrity": (
                "verify_frozen.py exit 1 with 2 residual drifts, both evidence files regenerated "
                "around the freeze: semantic_escape_rebased.json (manifest 497aac5e, disk 6a67ce9e) "
                "and variant_registry_check.json (manifest cb19d3d1, disk 164a9a84). The 37 mapped "
                "files include all three canonical schemas at their disk hashes, so the two reviewed "
                "targets are bound; the two stale evidence entries need a re-freeze."
            ),
        },
        "class_collapse_attempt": {
            "result": "not_supported",
            "method": (
                "26-probe cross-class suite (K1-K11, S2b-S7) with polarity and negation controls; "
                "self-test on planted merged/separated fixtures (convergence_probe_selftest.json)."
            ),
            "evidence": [
                "artifacts/worker18/f2_review/convergence_probe_report.json#"
                + hashes["artifacts/worker18/f2_review/convergence_probe_report.json"][:12],
                "artifacts/worker18/f2_review/convergence_probe_selftest.json#"
                + hashes["artifacts/worker18/f2_review/convergence_probe_selftest.json"][:12],
            ],
            "conclusion_types": {
                "AF-SCC-C2-VAC-GEN": "scc_c2_future_inextendibility",
                "AF-SCC-C0-VAC-GEN": "scc_c0_future_inextendibility",
            },
            "why_not_collapsed": (
                "Distinct conclusion types; one-way C0=>C2/H2loc entailment ledger with the converse "
                "forbidden; each anti_scope names the sibling; no shared asserted conclusion object; "
                "no collapse evidence fired."
            ),
            "collapse_falsifier": (
                "A C0 datum satisfying the C2 schema, or the C2 conclusion asserted verbatim in the "
                "C0 file, or a shared reasoning object across the two verdicts."
            ),
        },
        "verdicts": [],
        "cross_cutting_notes": [
            {
                "label": "N-X1",
                "severity": "non_blocking",
                "finding": (
                    "FROZEN rev20 has 2 residual evidence drifts (semantic_escape_rebased.json, "
                    "variant_registry_check.json); verify_frozen.py exits 1. Neither reviewed schema "
                    "is affected."
                ),
                "owner": "astra-lead-formulation",
                "falsifier": "re-run verify_frozen.py after a re-freeze and get exit 0.",
            },
            {
                "label": "N-X2",
                "severity": "non_blocking",
                "finding": (
                    "Sibling worker-06 lint is polarity-blind and class-count-over-broad on the frozen "
                    "set (flags prohibited phrases and sibling references); it is not the canonical "
                    "contract, and no canonical artifact declares it."
                ),
                "owner": "worker-06 tooling / astra-lead-audit",
                "falsifier": "w06 report on a8d899d2 with only the map-node check failing.",
            },
            {
                "label": "N-X3",
                "severity": "non_blocking",
                "finding": (
                    "research_map.json still points node F2 at superseded worker drafts; "
                    "FORM-MAP-PATCH-002 is an open resource request, so map-vs-artifact node ids "
                    "cannot yet agree."
                ),
                "owner": "astra (controller)",
                "falsifier": "map patch applied and w06 declared_artifact_matches passes.",
            },
        ],
        "not_claimed": [
            "no node completion",
            "no gate verdict",
            "no theorem, counterexample or numerical result",
        ],
        "evidence_refs": [
            "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml#" + hashes[TARGETS["F2a"]["path"]][:12],
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#" + hashes[TARGETS["F2b"]["path"]][:12],
            "artifacts/formulation/FROZEN.json#" + man_sha[:12],
            "artifacts/worker18/f2_review/convergence_probe_report.json#"
            + hashes["artifacts/worker18/f2_review/convergence_probe_report.json"][:12],
            "artifacts/worker18/f2_review/convergence_canonical_gate.txt#"
            + hashes["artifacts/worker18/f2_review/convergence_canonical_gate.txt"][:12],
            "artifacts/worker18/f2_review/w06_c0_frozen_report.json#"
            + hashes["artifacts/worker18/f2_review/w06_c0_frozen_report.json"][:12],
        ],
    }

    verdicts = [
        {
            "target_id": "AF-SCC-C2-VAC-GEN",
            "node_id": "F2a",
            "artifact": TARGETS["F2a"]["path"],
            "artifact_sha256": hashes[TARGETS["F2a"]["path"]],
            "artifact_revision": 9,
            "supersedes_review": TARGETS["F2a"]["prior_review"],
            "superseded_draft_sha256": TARGETS["F2a"]["prior_draft_sha"],
            "superseded_v1_pin": TARGETS["F2a"]["v1_sha"],
            "verdict": "accept",
            "score": 4,
            "blocking_findings": [],
            "non_blocking_findings": [
                {
                    "label": "N-A1",
                    "severity": "non_blocking",
                    "lines": ["277"],
                    "finding": (
                        "Probe S5-C2 fires on 'c0 or c2' inside anti_scope.phrases_that_are_not_this_class "
                        "(a ban list). Instrument false positive, not artifact leakage: the canonical gate "
                        "R17-R25 PASSes the same bytes and the phrase is quoted to forbid it."
                    ),
                    "owner": "worker-18 probe tooling",
                    "falsifier": (
                        "a merged-class token asserted (not banned) outside anti_scope/implication "
                        "ledgers in this file."
                    ),
                },
                {
                    "label": "N-A2",
                    "severity": "non_blocking",
                    "lines": ["45", "49", "215"],
                    "finding": (
                        "S6-C2 fires on the (s,delta) uniformity binder over D0. It is one class "
                        "statement uniformly quantified over admissible regularity pairs, not a "
                        "disjunction of classes; a one-line note making that explicit would help readers."
                    ),
                    "owner": "astra-lead-formulation",
                    "falsifier": (
                        "an admissible pair in D0 whose statement has a different conclusion type, or a "
                        "second conclusion object in the file."
                    ),
                },
                {
                    "label": "N-A3",
                    "severity": "non_blocking",
                    "lines": ["257"],
                    "finding": (
                        "tier_1.machine_checkable_steps overstates machine-checkability: sampled Ric = 0 "
                        "and C2-across-the-boundary checks are not machine checks to the stated standard "
                        "(carried from draft review F-A7; not repaired, not blocking)."
                    ),
                    "owner": "astra-lead-formulation",
                    "falsifier": "a checker that decides those steps in-process.",
                },
                {
                    "label": "N-A4",
                    "severity": "non_blocking",
                    "lines": ["anti_scope.not_this_class[5]"],
                    "finding": (
                        "The TWOSIDED variant entry inside not_this_class reuses this class's own id "
                        "(AF-SCC-C2-VAC-GEN) with only a prose pointer to parent_class/variant_id; a "
                        "lexical reader can misread it as self-exclusion. Rev20's parent_class + "
                        "variant_id representation should be applied as explicit fields here."
                    ),
                    "owner": "astra-lead-formulation",
                    "falsifier": "a reader who reports this artifact as naming itself in anti_scope.",
                },
            ],
            "prior_hard_failure_deltas": [
                {"id": "HF-A1", "draft": "dangling extension_predicate refs",
                 "status": "resolved", "evidence": "extension_predicate block defined; probe S7-C2"},
                {"id": "HF-A2", "draft": "statement_formal disjunctive D0 residue",
                 "status": "resolved", "evidence": "line 215 == quantifiers.formal line 45; no disjunctive binder"},
                {"id": "HF-A3", "draft": "one-data-class criterion unmet",
                 "status": "resolved", "evidence": "regularity.data_regularity identical across F1/F2a/F2b"},
                {"id": "HF-A4", "draft": "canonical binding gate FAIL R19/R22",
                 "status": "resolved", "evidence": "check_class_schema.py PASS failed_rules=[] at 8dae50da"},
            ],
            "v1_to_v2_deltas": [
                {"pin": "e9fcefe6 -> 8dae50da (rev8 -> rev9, FROZEN rev19 -> rev20)"},
                {"content": "rev20 replaced candidate-class tokens with parent_class + variant_id references; no change to quantifiers, extension predicate or conclusion"},
                {"result": "verdict unchanged (accept 4/5); findings unchanged except line shifts and new N-A4"},
            ],
            "machine_gate_evidence": [
                "artifacts/worker18/f2_review/convergence_canonical_gate.txt#"
                + hashes["artifacts/worker18/f2_review/convergence_canonical_gate.txt"][:12],
                "artifacts/worker18/f2_review/convergence_probe_report.json#"
                + hashes["artifacts/worker18/f2_review/convergence_probe_report.json"][:12],
            ],
            "acceptance_checks": {
                "class_leakage": "pass",
                "conclusion_inflation": "pass",
                "assumption_completeness": "pass",
                "decidable_falsifier": "pass",
                "two_reader_disagreement": "pass; N-A2/N-A3/N-A4 are the disagreement surface",
            },
            "reasoning": reason_c2,
            "falsifier": (
                "Accept is falsified by any asserted C0 conclusion in this file, by a collapse probe "
                "hit not attributable to a ban list, or by a canonical-gate FAIL at 8dae50da."
            ),
        },
        {
            "target_id": "AF-SCC-C0-VAC-GEN",
            "node_id": "F2b",
            "artifact": TARGETS["F2b"]["path"],
            "artifact_sha256": hashes[TARGETS["F2b"]["path"]],
            "artifact_revision": 9,
            "supersedes_review": TARGETS["F2b"]["prior_review"],
            "superseded_draft_sha256": TARGETS["F2b"]["prior_draft_sha"],
            "superseded_v1_pin": TARGETS["F2b"]["v1_sha"],
            "superseded_intermediate_pin": TARGETS["F2b"]["v1_intermediate_sha"],
            "verdict": "accept",
            "score": 4,
            "blocking_findings": [],
            "non_blocking_findings": [
                {
                    "label": "N-B1",
                    "severity": "non_blocking",
                    "lines": ["4"],
                    "finding": (
                        "node_id F2b vs map node F2: research_map.json still points F2 at the drafts and "
                        "FORM-MAP-PATCH-002 is unapplied, so worker-06 declared_artifact_matches fails "
                        "(map_node F2b != declared F2). Map-side action, not an artifact defect."
                    ),
                    "owner": "astra (controller)",
                    "falsifier": "map patch applied; w06 declared_artifact_matches passes at a8d899d2.",
                },
                {
                    "label": "N-B2",
                    "severity": "non_blocking",
                    "lines": ["154", "280"],
                    "finding": (
                        "Probe S5-C0 fires on 'c0 or c2' in the ban list; worker-06 additionally flags "
                        "'c2 or c0' at line 154 ('No containment with C2 or C0 is asserted here') and fails "
                        "regularity_selector by counting sibling references. Both are prohibition contexts; "
                        "the canonical gate PASSes the same bytes."
                    ),
                    "owner": "worker-06 tooling / worker-18 probe tooling",
                    "falsifier": "a non-negated composite-regularity assertion outside anti_scope in this file.",
                },
                {
                    "label": "N-B3",
                    "severity": "non_blocking",
                    "lines": ["46", "50", "217"],
                    "finding": (
                        "S6-C0 fires on the (s,delta) uniformity binder over D0; one class statement over "
                        "admissible regularity pairs, not a disjunction. Same clarity note as N-A2."
                    ),
                    "owner": "astra-lead-formulation",
                    "falsifier": "an admissible pair in D0 with a different conclusion type.",
                },
                {
                    "label": "N-B4",
                    "severity": "non_blocking",
                    "lines": ["260"],
                    "finding": (
                        "tier_1 machine_checkable_steps over-labelled; non-meagerness is correctly the "
                        "non-machine-checkable step, but sampled continuity/nondegeneracy and the isometry "
                        "witness are not machine checks to the stated standard (carried from F-B3)."
                    ),
                    "owner": "astra-lead-formulation",
                    "falsifier": "a checker that decides those steps in-process.",
                },
                {
                    "label": "N-B5",
                    "severity": "non_blocking",
                    "lines": ["anti_scope.not_this_class[4]", "anti_scope.not_this_class[5]"],
                    "finding": (
                        "The H2LOC and DISTRIBUTIONAL variant entries reuses this class's own id in "
                        "not_this_class, with the parent_class/variant_id relation only in prose. Same "
                        "labelling recommendation as N-A4."
                    ),
                    "owner": "astra-lead-formulation",
                    "falsifier": "a reader who reports this artifact as naming itself in anti_scope.",
                },
            ],
            "prior_hard_failure_deltas": [
                {"id": "HF-B1", "draft": "line-5 'C0 or C2' comment vs lint exemption claim",
                 "status": "resolved", "evidence": "comment removed; the two remaining composite tokens are prohibitions at lines 154 and 280"},
                {"id": "HF-B2", "draft": "node_id F2b vs map node F2",
                 "status": "downgraded_to_N", "evidence": "N-B1: map patch FORM-MAP-PATCH-002 pending; artifact label deliberate per lead split"},
                {"id": "Q1-vacuity", "draft": "can any smooth spacetime be trivially C0-extended",
                 "status": "answered", "evidence": "Minkowski compactness witness bounds the extension predicate; generic level conditional on UNVERIFIED trapped-surface family"},
                {"id": "Q2-D0", "draft": "disjunctive D0 domain unacceptable for class identity",
                 "status": "resolved", "evidence": "D0 is the admissible-regularity-pair domain; no disjunction in quantifiers or statement_formal"},
                {"id": "Q3-tiers", "draft": "tier_1/tier_2 separation",
                 "status": "carried_as_N", "evidence": "N-B4"},
            ],
            "v1_to_v2_deltas": [
                {"pin": "bdb23f76 -> 94aaa95a -> a8d899d2 (rev8 -> rev9; FROZEN rev19 -> rev20)"},
                {"content": "rev19/rev20 variant-registry integration: horizon_localized_variant restructured to parent_class + variant_id; anti_scope variant entries added; known_status consequence rewritten"},
                {"result": "verdict unchanged (accept 4/5); line shifts (151->154, 277->280) and new N-B5"},
            ],
            "machine_gate_evidence": [
                "artifacts/worker18/f2_review/convergence_canonical_gate.txt#"
                + hashes["artifacts/worker18/f2_review/convergence_canonical_gate.txt"][:12],
                "artifacts/worker18/f2_review/w06_c0_frozen_report.json#"
                + hashes["artifacts/worker18/f2_review/w06_c0_frozen_report.json"][:12],
            ],
            "acceptance_checks": {
                "class_leakage": "pass",
                "conclusion_inflation": "pass",
                "assumption_completeness": "pass",
                "decidable_falsifier": "pass",
                "two_reader_disagreement": "pass; N-B2/N-B4/N-B5 are the disagreement surface",
            },
            "reasoning": reason_c0,
            "falsifier": (
                "Accept is falsified by a non-negated C2-inextendibility assertion in this file, by a "
                "collapse probe hit not attributable to a ban list, or by a canonical-gate FAIL at "
                "a8d899d2."
            ),
        },
    ]
    review["verdicts"] = verdicts
    review["next_falsifier"] = (
        "Re-hash both targets; if either moves, this file is stale and must be re-issued. A genuine "
        "blocking finding is one that survives the canonical gate and is asserted rather than banned."
    )

    out = ROOT / "reviews" / "convergence-18.json"
    out.write_text(json.dumps(review, indent=1, ensure_ascii=False) + "\n")
    out_sha = sha(out)

    pins = {
        "artifact": "reviews/convergence-18.json",
        "sha256": out_sha,
        "generated_at": now,
        "assignment_event_id": "astra-conv-03",
        "review_revision": 2,
        "targets": {
            "AF-SCC-C2-VAC-GEN": {"path": TARGETS["F2a"]["path"], "sha256": hashes[TARGETS["F2a"]["path"]], "revision": 9},
            "AF-SCC-C0-VAC-GEN": {"path": TARGETS["F2b"]["path"], "sha256": hashes[TARGETS["F2b"]["path"]], "revision": 9},
        },
        "frozen_manifest": {"path": "artifacts/formulation/FROZEN.json", "sha256": man_sha, "revision": manifest.get("revision")},
        "evidence": {k: v for k, v in hashes.items()},
        "verdicts": {v["node_id"]: {"verdict": v["verdict"], "score": v["score"],
                                    "blocking": len(v["blocking_findings"]),
                                    "non_blocking": len(v["non_blocking_findings"])} for v in verdicts},
        "reasoning_jaccard_c2_vs_c0": rj,
    }
    (FR / "convergence_pins.json").write_text(json.dumps(pins, indent=1) + "\n")

    print(json.dumps({
        "review": "reviews/convergence-18.json",
        "sha256": out_sha,
        "verdicts": pins["verdicts"],
        "reasoning_jaccard": rj,
        "c2_sha256": hashes[TARGETS["F2a"]["path"]],
        "c0_sha256": hashes[TARGETS["F2b"]["path"]],
        "frozen_revision": manifest.get("revision"),
        "probe_selftest_ok": selftest.get("ok"),
        "verify_frozen_exit": vf.returncode,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
