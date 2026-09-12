#!/usr/bin/env python3
"""Emit worker-059 F2b rev12 verdict artifacts (review, adjudication, checkpoint).

Reads the measured evidence JSON produced by check_f2b_rev12.py and writes the
human/controller-facing artifacts with sha256 bindings.  No global state is touched.
"""
import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
D = ROOT / "artifacts/worker-059/f2b_rev12_verdict"
SNAP = D / "snapshot/f2b.55d0a1ea9bda.yaml"
EV = D / "independent_evidence.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def J(p: Path):
    return json.loads(p.read_text())


def write(p: Path, obj):
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    return sha(p)


now = dt.datetime.now().astimezone().isoformat()
ev = J(EV)
snap = SNAP.read_bytes()
snap_sha = hashlib.sha256(snap).hexdigest()
canon_sha = sha(ROOT / "schemas/af_scc_c0_vacuum.yaml")
canon_mtime = dt.datetime.fromtimestamp(
    os.path.getmtime(ROOT / "schemas/af_scc_c0_vacuum.yaml")).astimezone().isoformat()

# ---------------------------------------------------------------- adjudication
sandbox = D / "sandbox_consistency/artifacts/formulation/evidence/taxonomy_consistency.json"
sandbox_sha = sha(sandbox)
canon_ev = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
canon_ev_sha = sha(canon_ev)
enriched = ROOT / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
enriched_obj = J(enriched)
frozen = J(ROOT / "artifacts/formulation/FROZEN.json")
frozen_ev = frozen["files"]["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"]
frozen_at = frozen["frozen_at"]

adj = {
    "artifact": "consistency-evidence binding adjudication",
    "task_id": "W059-F2B-REV12-VERDICT-01",
    "worker": "worker-059",
    "measured_at": now,
    "scope": "F2b f0_binding, with the identical declaration pattern measured on F1 and F2a "
             "(all three declare consistency_evidence_sha256=675a99d0...); this artifact "
             "adjudicates the chain, it does not modify any canonical file",
    "declared_consistency_evidence_sha256": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
    "declared_in_schemas": {
        "schemas/af_wcc_vacuum.yaml": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
        "schemas/af_scc_c2_vacuum.yaml": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
        "schemas/af_scc_c0_vacuum.yaml": "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48",
    },
    "declared_path_measured_sha256": canon_ev_sha,
    "frozen_rev28_pin": {"path": "artifacts/formulation/evidence/taxonomy_consistency.json",
                         "sha256": frozen_ev, "frozen_at": frozen_at},
    "out_of_tree_enriched_pin": {
        "path": "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json",
        "measured_sha256": sha(enriched),
        "embedded_map_taxonomy_sha256": enriched_obj.get("map_taxonomy_sha256"),
        "embedded_lead_contract_sha256": enriched_obj.get("lead_contract_sha256"),
        "embedded_measured_at": enriched_obj.get("measured_at"),
        "embedded_consistent": enriched_obj.get("consistent"),
        "embedded_errors": enriched_obj.get("errors"),
    },
    "independent_reproduction": {
        "method": "copied the two taxonomy trees, VOCAB_ALIASES.json and the canonical "
                  "artifacts/formulation/tools/check_taxonomy_consistency.py into a sandbox "
                  "root preserving the tool's ROOT=parents[3] layout, then ran the tool there",
        "sandbox_root": str(D / "sandbox_consistency"),
        "command": "python3 artifacts/formulation/tools/check_taxonomy_consistency.py",
        "exit": 0,
        "stdout": "CONSISTENT (4 classes, 0 contract-text divergences)",
        "sandbox_output_sha256": sandbox_sha,
        "canonical_path_sha256": canon_ev_sha,
        "byte_identical_to_canonical_path": sandbox_sha == canon_ev_sha,
        "reproduced_content_has_tree_digests": False,
        "note": "the canonical tool is deterministic and its output on the current canonical "
                "trees is byte-identical to the file at the canonical evidence path; that file "
                "does NOT embed the compared-tree hashes or measured_at",
    },
    "adjudication": {
        "content_proposition_true_today": True,
        "binding_satisfiable_from_canonical_artifacts": False,
        "why": "the declared hash 675a99d0 is the enriched worker-086 pin, not the bytes at the "
               "declared canonical path (9e335e9b) and not the FROZEN rev28 pin (9e335e9b); the "
               "canonical evidence file carries no tree digests, so a third party cannot bind "
               "the declared consistency claim to the declared F0/authoring pair from canonical "
               "artifacts alone",
        "severity": "major/binding (blocks a hash-bound accept; not a semantic failure)",
        "semantic_risk": "low: the consistency proposition itself was independently reproduced "
                         "true at the current tree bytes",
    },
    "minimal_repair": [
        "1. extend artifacts/formulation/tools/check_taxonomy_consistency.py to emit "
        "map_taxonomy_sha256, lead_contract_sha256 and measured_at (about 6 lines)",
        "2. re-run it so artifacts/formulation/evidence/taxonomy_consistency.json itself "
        "carries the compared-tree digests (content becomes equal to the enriched pin's semantics)",
        "3. refresh f0_binding.consistency_evidence_sha256 and checked_at in F1/F2a/F2b to the "
        "new canonical bytes",
        "4. re-freeze (new FROZEN revision) and hold the three schemas + F0 stable for one full "
        "review window",
        "minimal alternative: keep the unenriched canonical file and repoint the three schemas' "
        "consistency_evidence_sha256 to 9e335e9b; this is cheaper but leaves the consistency "
        "claim unbound to tree digests (does not close worker-090 W090-R12-01)",
    ],
    "falsifier": "a canonical revision in which f0_binding.consistency_evidence_sha256 equals "
                 "the measured bytes at f0_binding.consistency_evidence AND that hash equals "
                 "the FROZEN pin AND the canonical evidence file embeds the compared-tree "
                 "digests; or a controller ruling that out-of-tree hash-addressed pins are "
                 "acceptable declarations (which downgrades this to a documentation defect)",
}
adj_sha = write(D / "consistency_adjudication.json", adj)

# ---------------------------------------------------------------- review
review = {
    "event_id": "w059-f2b-rev12-20260912T0044-review",
    "event_type": "review",
    "created_at": now,
    "actor": "worker-059",
    "reviewer": "worker-059",
    "target_id": "F2b",
    "target_path": "schemas/af_scc_c0_vacuum.yaml",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "reviewed_revision": 12,
    "reviewed_sha256": snap_sha,
    "review_window": {"snapshot_sha256": snap_sha, "canonical_sha256_at_finalize": canon_sha,
                      "canonical_mtime": canon_mtime, "drift": canon_sha != snap_sha},
    "artifact": "artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json",
    "verdict": "revise",
    "score": 4.0,
    "counts_as_independent_verdict": True,
    "counts_as_full_schema_verdict": True,
    "counts_as_independent_second_verdict": False,
    "hard_failures": [
        "HF-059-F2B-01 (binding, blocking): f0_binding declares consistency_evidence_sha256="
        "675a99d0d25b2b37... but the declared canonical path "
        "artifacts/formulation/evidence/taxonomy_consistency.json measures 9e335e9ba1bfcf77... "
        "and FROZEN rev28 pins 9e335e9b; 675a99d0 is worker-086's out-of-tree enriched pin. "
        "The canonical file embeds no compared-tree digests, so the declared consistency claim "
        "is not bindable from canonical artifacts (checks B9/B10). Content was independently "
        "reproduced true: the canonical tool re-run in sandbox reproduces 9e335e9b byte-"
        "identically and prints CONSISTENT (4 classes, 0 divergences).",
        "HF-059-F2B-02 (registry conflict, blocking pending a controller ruling): canonical F0 "
        "rev5 (0abb9ed8) stores conclusion_type alias 'strong_cosmic_censorship_C0' and its "
        "field_vocabulary.conclusion_type.allowed lists the aliases, while the FROZEN-pinned "
        "VOCAB_ALIASES.json declares 'scc_c0_future_inextendibility' the canonical key and "
        "states accepted aliases 'must never appear in a new canonical artifact'. F2b itself "
        "uses the canonical token and is policy-compliant; the repair belongs to F0 and needs "
        "one written ruling on which registry governs. Same defect as worker-059 HF-059-F2A-01 "
        "at F2a 5476a3f2.",
    ],
    "findings": [
        "F-059-F2B-01: content surface green at 55d0a1ea. 34 independent checks, 32 pass; the "
        "only blocking failures are the two binding items above; 24/24 deterministic single-"
        "defect mutants were detected (duplicate key, future timestamp, wrong class id, C2 "
        "conclusion token, removed C2/C1 forbidden weakenings, WCC sibling, 'C0 or C2' composite, "
        "dropped comeager quantifier, dangling domain ref, C2 extension regularity, stripped "
        "clause (f), stripped differentiability prohibition, scalar matter, C2 data regularity, "
        "open-dense genericity, I+ in conclusion, visibility in conclusion, WCC falsifier, stale "
        "F0 hash, cleared evidence hash, empty promotion rule, revision=11).",
        "F-059-F2B-02: consistency-evidence adjudication (artifact "
        "artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json): the declaration "
        "is content-true and path-unbound. Sandbox re-run of the canonical tool at current bytes "
        "= 9e335e9b byte-identical, exit 0, CONSISTENT. The enriched pin 675a99d0 embeds "
        "map_taxonomy_sha256=0abb9ed8 (matches measured) and lead_contract_sha256=d7419b4e "
        "(matches measured). Minimal repair: teach the canonical tool to embed the two tree "
        "digests and measured_at, regenerate, refresh the three schemas' declarations, re-freeze.",
        "F-059-F2B-03: canonical gates corroborate at these bytes: check_class_schema.py "
        "verdict=pass, 0 failed rules on the snapshot; runtime/bin/classsep_regression.py PASS "
        "(17/17 leaks, 10/10 controls, FP 0/FN 0); research_map/validate_map.py VALID.",
        "F-059-F2B-04: previously reported defect classes independently confirmed resolved at "
        "this hash: 0 duplicate mapping keys; revised_at 00:31:41 <= canonical mtime 00:32:02 <= "
        "measurement now; class_contract_pointer resolves in canonical classes; declared F0 hash "
        "fresh 0abb9ed8; D0 tagged disjoint union closed under the forall with definition_refs "
        "resolving; clause (f) interior+chronological requirement present; canonical == authoring "
        "mirror; FROZEN rev28 pins match every measured byte.",
        "F-059-F2B-05 (advisory): l1_ledger_refs declare l1_status=accepted for D-002, T-301, "
        "T-515, T-528, T-302 while ledger/theorems.jsonl verification_status is 'abstract-read' "
        "for all five; the ledger rows self-describe acceptance_authority as 'author self-"
        "assessment, not a reviewer verdict', and no mapping between the schema's l1_status "
        "vocabulary and the ledger's verification_status exists. Not blocking on its own.",
        "F-059-F2B-06 (advisory): revision_history row 9 (rev11) is flagged unused:true and is "
        "the only out-of-order row (23:30:35 between 00:30:00 and 00:31:41); effective history "
        "is monotone. Same benign shape as F2a.",
        "F-059-F2B-07 (independence caveat): this is worker-059's first F2b review; the "
        "instrument is own-built (stdlib+PyYAML, no canonical-gate imports) with 24/24 mutant "
        "sensitivity. Prior reviewers (worker-090/worker-095/lead-audit) converged on the "
        "consistency-evidence and token-registry defects, so viewpoint independence is the "
        "controller's call: counts_as_independent_second_verdict=false.",
    ],
    "resolved_at_this_hash": [
        "duplicate mapping keys", "future-dated revised_at", "cross-tree class_contract_pointer",
        "stale declared F0 hash", "D0 pair-vs-smooth ill-typedness (tagged disjoint union)",
        "clause (f) escapability (interior+chronological requirement)",
        "canonical/authoring mirror divergence for F2b", "FROZEN rev28 staleness",
    ],
    "evidence_refs": [
        "artifacts/worker-059/f2b_rev12_verdict/snapshot/f2b.55d0a1ea9bda.yaml#55d0a1ea9bda",
        "artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json",
        "artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py",
        "artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json",
        "artifacts/worker-059/f2b_rev12_verdict/corroboration/check_class_schema_stdout.json",
        "artifacts/worker-059/f2b_rev12_verdict/corroboration/classsep_regression_stdout.txt",
        "artifacts/worker-059/f2b_rev12_verdict/corroboration/validate_map_stdout.txt",
    ],
    "next_falsifier": "A F2b revision (or controller ruling) in which (i) "
                      "f0_binding.consistency_evidence_sha256 equals the measured bytes at the "
                      "declared canonical evidence path, that path equals the FROZEN pin, and the "
                      "canonical evidence embeds map_taxonomy_sha256=0abb9ed8 and "
                      "lead_contract_sha256=d7419b4e; (ii) one governing conclusion-token "
                      "registry is designated so that alias-equivalence is recorded rather than "
                      "contradicted. Hash drift of schemas/af_scc_c0_vacuum.yaml voids this "
                      "verdict immediately (pinned 55d0a1ea9bda).",
    "validation_status": "unverified",
    "note": "Advisory worker verdict; cannot set a gate verdict or node status. Content "
            "semantics pass; binding/publication state fails on the two items above.",
}
review_sha = write(D / "review_F2b_55d0a1ea.json", review)

# ---------------------------------------------------------------- checkpoint
ckpt = {
    "checkpoint_id": "w059-ckpt-f2b-rev12-" + now.replace(":", "").replace("-", "")[:15],
    "worker": "worker-059",
    "task_id": "W059-F2B-REV12-VERDICT-01",
    "node_id": "F2b",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "status": "complete_bounded_task",
    "created_at": now,
    "reviewed_sha256": snap_sha,
    "review_verdict": "revise",
    "review_score": 4.0,
    "hard_failures": ["HF-059-F2B-01", "HF-059-F2B-02"],
    "checks": {"n_checks": ev["n_checks"], "n_failed": ev["n_failed"],
               "blocking_failed": ev["blocking_failed_checks"],
               "advisory_failed": ev["advisory_failed_checks"]},
    "mutants": {"detected": ev["mutant_controls"]["detected"],
                "total": ev["mutant_controls"]["total"]},
    "artifacts": {
        "snapshot": {"path": "artifacts/worker-059/f2b_rev12_verdict/snapshot/f2b.55d0a1ea9bda.yaml",
                     "sha256": snap_sha},
        "instrument": {"path": "artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py",
                       "sha256": sha(D / "check_f2b_rev12.py")},
        "evidence": {"path": "artifacts/worker-059/f2b_rev12_verdict/independent_evidence.json",
                     "sha256": sha(EV)},
        "adjudication": {"path": "artifacts/worker-059/f2b_rev12_verdict/consistency_adjudication.json",
                         "sha256": adj_sha},
        "review": {"path": "artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json",
                   "sha256": review_sha},
    },
    "global_state_mutated": False,
    "notes": "Worker-level checkpoint only. Canonical files were read and hashed, never written. "
             "The sandbox consistency re-run wrote only under this artifact directory. "
             "classsep_regression.py wrote only its own runtime/state/classsep_regression outputs.",
    "next_falsifier": review["next_falsifier"],
}
ckpt_sha = write(D / "checkpoint_w059_f2b_rev12.json", ckpt)

print(json.dumps({
    "snapshot_sha256": snap_sha,
    "evidence_sha256": sha(EV),
    "instrument_sha256": sha(D / "check_f2b_rev12.py"),
    "adjudication_sha256": adj_sha,
    "review_sha256": review_sha,
    "checkpoint_sha256": ckpt_sha,
    "canonical_f2b_sha256_at_finalize": canon_sha,
}, indent=1))
