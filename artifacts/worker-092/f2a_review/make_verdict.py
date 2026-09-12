#!/usr/bin/env python3
"""Emit reviews/F2a-review-rev27-c.json from the measured report. Deterministic."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
now = lambda: datetime.now(TZ).isoformat(timespec="seconds")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

rep = json.loads((HERE / "report.json").read_text())
ctrl = json.loads((HERE / "controls.json").read_text())
pin = rep["target"]["pin_sha256"]
matrix = {c["id"]: c["status"] for c in rep["checks"]}
nonpass = [c for c in rep["checks"] if c["status"] != "PASS"]

verdict = {
    "review_id": "F2a-review-rev27-c",
    "task_id": "W092-F2A-CLASSBIND-REVIEW-01",
    "created_at": now(),
    "reviewed_at": rep["finished_at"],
    "reviewer": "worker-092",
    "reviewer_independence": (
        "not an author of schemas/af_scc_c2_vacuum.yaml, artifacts/formulation/**, "
        "research_map/formulation_taxonomy.yaml, or the rule_spec; no F2a review file was read before "
        "this verdict was written (blind per the audit-r2-F2a card); the instrument is an independent "
        "re-implementation of rule_spec R01-R16 and does not import the author's checker"),
    "target_id": "F2a",
    "target": {"node_id": "F2a", "artifact": "schemas/af_scc_c2_vacuum.yaml",
               "artifact_sha256": pin, "path": "schemas/af_scc_c2_vacuum.yaml", "sha256": pin},
    "node_id": "F2a",
    "class_id": "AF-SCC-C2-VAC-GEN",
    "gate": "G-FORM",
    "reviewed_path": "schemas/af_scc_c2_vacuum.yaml",
    "reviewed_sha256": pin,
    "reviewed_mtime": datetime.fromtimestamp(
        (ROOT / "schemas/af_scc_c2_vacuum.yaml").stat().st_mtime, TZ).isoformat(timespec="seconds"),
    "hash_stable_during_review": True,
    "counts_as_full_schema_verdict": True,
    "verdict": "revise",
    "score": 3.5,
    "hard_failures": [{
        "id": "HF-W092-F2A-01",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "detail": (
            "schemas/af_scc_c2_vacuum.yaml#%s declares f0_binding.consistency_evidence_sha256 = "
            "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48, but the canonical path it "
            "names (artifacts/formulation/evidence/taxonomy_consistency.json) measures "
            "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b, which is also the FROZEN "
            "rev28 pin. The declared evidence is unresolvable at the frozen revision; the live/frozen bytes "
            "are a strict superset of the declared ones (they add map_taxonomy_sha256, lead_contract_sha256, "
            "measured_at), so the class semantics are unaffected but the schema's own binding rule is unmet."
        ),
        "falsified_by": ("recompute sha256(artifacts/formulation/evidence/taxonomy_consistency.json) and "
                         "compare to f0_binding.consistency_evidence_sha256 at schema pin %s" % pin[:12]),
        "repair_preserving_pins": (
            "restore the 675a99d0 bytes at the canonical path (hash-verified copy at "
            "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json) and re-freeze "
            "the evidence pin; the rev12 schema bytes and their bound reviews are then untouched"),
        "repair_retiring_pins": (
            "re-stamp consistency_evidence_sha256 in all three schemas to 9e335e9b and re-freeze; this "
            "changes the schema bytes and voids every verdict bound to the rev12 pins"),
    }],
    "findings": [
        {"id": "F-W092-F2A-01", "status": "core",
         "text": "C2/C0 separation is carried by CONTENT, not naming: distinct conclusion_type "
                 "(scc_c2_future_inextendibility vs scc_c0_future_inextendibility), distinct extension "
                 "regularity (C2 vs C0), distinct equation signature (classical_ricci vs none), and an "
                 "asymmetric implication ledger (C0-inext => C2-inext licensed; converse forbidden)."},
        {"id": "F-W092-F2A-02", "status": "core",
         "text": "D0 is a tagged disjoint union {smooth, (sobolev,s,delta)} with s > 5/2, delta in (1/2,1); "
                 "the rev12 retype removes the old ill-typed pair and the forall-r binder is instantiable on "
                 "both disjuncts. definition_ref targets resolve (R03/R03b PASS)."},
        {"id": "F-W092-F2A-03", "status": "core",
         "text": "No conclusion inflation: epistemic_status=open_problem, promotion requires a checked proof "
                 "artifact, forbidden_strengthenings non-empty, and the vacuity argument is explicitly marked "
                 "unverified_proof_obligation rather than asserted."},
        {"id": "F-W092-F2A-04", "status": "soft", "owner": "lead-formulation (F0 canonical taxonomy)",
         "text": "The canonical F0 contract uses the alias conclusion token strong_cosmic_censorship_C2 where "
                 "VOCAB_ALIASES names scc_c2_future_inextendibility canonical and states aliases 'must never "
                 "appear in a new canonical artifact'. Alias-bridged, not a class merge (S02b DEFECT)."},
        {"id": "F-W092-F2A-05", "status": "soft", "owner": "lead-formulation (F2a)",
         "text": "genericity.ambient_space justifies Baire-ness by 'closed subset of a Banach space' while the "
                 "smooth branch is Frechet; Frechet spaces are Baire, so the conclusion holds but the stated "
                 "reason is incomplete for the smooth disjunct (R07b DEFECT)."},
        {"id": "F-W092-F2A-06", "status": "soft", "owner": "lead-formulation (F2a)",
         "text": "revision_history index 9 is marked unused:true yet carries two notes; the rev11 note is never "
                 "applied. Consistent with supersedes:null but the revision trail is ambiguous."},
        {"id": "F-W092-F2A-07", "status": "core",
         "text": "All 16 structural rules of rule_spec.json PASS, 3/3 negative controls were detected by the "
                 "independent instrument, entry==exit hashes for all 9 pinned inputs, and the author's checker "
                 "(separate implementation) also returns pass. The class contract itself is accept-eligible; "
                 "only the provenance defect HF-W092-F2A-01 blocks a clean accept."},
    ],
    "check_matrix": matrix,
    "counts": rep["summary"],
    "controls": {"detected": sum(1 for c in ctrl["controls"] if c["detected"]),
                 "total": len(ctrl["controls"]), "all_detected": ctrl["all_detected"]},
    "non_pass_checks": [{"id": c["id"], "status": c["status"], "detail": c["detail"][:300]} for c in nonpass],
    "evidence_refs": [
        "schemas/af_scc_c2_vacuum.yaml#%s" % pin[:12],
        "artifacts/formulation/FROZEN.json",
        "artifacts/formulation/rule_spec.json#40f9bb9e657b",
        "artifacts/worker-092/f2a_review/report.json#%s" % sha(HERE / "report.json")[:12],
        "artifacts/worker-092/f2a_review/verify_f2a.py#%s" % sha(HERE / "verify_f2a.py")[:12],
        "artifacts/worker-092/f2a_review/controls.json#%s" % sha(HERE / "controls.json")[:12],
        "artifacts/worker-092/f2a_review/acceptance_run.log#%s" % sha(HERE / "acceptance_run.log")[:12],
        "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json#675a99d0d25b",
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
        "artifacts/formulation/formulation_taxonomy.yaml#d7419b4e8963",
    ],
    "falsifier": (
        "Re-run artifacts/worker-092/f2a_review/verify_f2a.py at the same pins: this verdict is falsified if any "
        "check flips, if any of the 3 controls stops being detected, if entry/exit hashes drift, or if "
        "sha256(artifacts/formulation/evidence/taxonomy_consistency.json) becomes 675a99d0d25b (in which case "
        "HF-W092-F2A-01 clears and the revise is superseded by a re-run at the same schema pin)."),
    "scope_limits": rep["scope_limits"],
    "instrument": "artifacts/worker-092/f2a_review/verify_f2a.py",
}

out = ROOT / "reviews/F2a-review-rev27-c.json"
out.write_text(json.dumps(verdict, indent=1, sort_keys=True))
print("wrote", out.relative_to(ROOT), "sha256", sha(out))
print("verdict=%s score=%s HF=%s non_pass=%s" % (
    verdict["verdict"], verdict["score"], [h["id"] for h in verdict["hard_failures"]],
    [c["id"] for c in nonpass]))
