#!/usr/bin/env python3
"""Build the F0 open-case disposition matrix (worker-02, assignment asg-...-11).

Inputs (hash-pinned, read-only):
  schemas/taxonomy_cases.jsonl          (assignment artifact; 9 cases have open=true)
  research_map/formulation_taxonomy.yaml (frozen class axes, guards, gaps, directive)

Output:
  artifacts/flash-02/open_case_disposition.json

The output is an ADJUDICATION INPUT, not an adjudication. Authority rule: a worker
may not create class ids or move a gate; `class_scope_adjudication.directive`
(astra-classscope-02) rejects new class ids pending Human PI, so every open case
that needs coverage beyond the frozen four is routed as a deferred request bound
to a frozen parent class, and never as a new class id in `class_ids`.

Usage: python3 artifacts/flash-02/build_open_case_disposition.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
CORPUS = ROOT / "schemas" / "taxonomy_cases.jsonl"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
OUT = ROOT / "artifacts" / "flash-02" / "open_case_disposition.json"

DISPOSITION_TOKENS = {
    "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI": (
        "the record's axis vector is outside every frozen class; a new class would be "
        "required, but astra-classscope-02 rejects new class ids pending Human PI, so the "
        "request is registered with its frozen parent class and stays unresolved"
    ),
    "SPLIT_REQUIRED": (
        "the record merges two frozen conclusions/regularities that must be filed separately "
        "(G3/X5); no new class id is needed"
    ),
    "SPLIT_AND_BRIDGE_REQUIRED": (
        "the record merges two conclusion families (X4/G1); each family files under its own "
        "frozen class and the cross-family link needs a separate bridge artifact"
    ),
}

# Authored adjudication table for the 9 open cases. Case-level facts (axis_vector,
# violated_vocabulary, leak_kind, falsifier) are read from the corpus, not retyped.
TABLE = {
    "TC-F0-N01": {
        "disposition": "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
        "bound_parent_class_ids": ["AF-WCC-VAC-GEN"],
        "gap_ref": "coverage_gaps.CG2",
        "rule_refs": ["guards.G5", "transfer_rules.forbidden.X2", "coverage_gaps.CG2"],
        "filing_verdict": "reject",
        "requested_scope": {
            "family": "WCC", "matter_model": "massless_scalar_field",
            "symmetry": "none_assumed", "asymptotics": "asymptotically_flat_3p1",
        },
        "decisive_hypothesis": (
            "AF-WCC-VAC-GEN:H2 fails (matter_model must be vacuum); the recomputed vector "
            "family=WCC/matter_model=massless_scalar_field/symmetry=none_assumed matches no "
            "frozen class, and CG2 forbids filing it here."
        ),
    },
    "TC-F0-N02": {
        "disposition": "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
        "bound_parent_class_ids": ["AF-WCC-VAC-GEN"],
        "gap_ref": "coverage_gaps.CG2",
        "rule_refs": ["guards.G4", "transfer_rules.forbidden.X3", "coverage_gaps.CG2"],
        "filing_verdict": "reject",
        "requested_scope": {
            "family": "WCC", "matter_model": "vacuum",
            "symmetry": "spherical", "asymptotics": "asymptotically_flat_3p1",
        },
        "decisive_hypothesis": (
            "AF-WCC-VAC-GEN:H5 fails (symmetry must be none_assumed); no vacuum spherical "
            "class exists, so the symmetry release X3 is forbidden and a new class would be "
            "required before any filing."
        ),
    },
    "TC-F0-N04": {
        "disposition": "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
        "bound_parent_class_ids": ["AF-SCC-C2-VAC-GEN"],
        "gap_ref": "coverage_gaps.CG2",
        "rule_refs": [
            "classes.AF-SCC-C2-VAC-GEN.exclusions",
            "field_vocabulary.matter_model",
            "coverage_gaps.CG2",
        ],
        "filing_verdict": "reject",
        "requested_scope": {
            "family": "SCC", "matter_model": "electrovacuum",
            "symmetry": "none_assumed", "regularity_token": "C2",
        },
        "decisive_hypothesis": (
            "AF-SCC-C2-VAC-GEN:H1/H2 fail; matter_model=electrovacuum is outside the closed "
            "field vocabulary (allowed: vacuum, massless_scalar_field), so the record cannot "
            "be mapped to vacuum and needs a new class."
        ),
    },
    "TC-F0-N09": {
        "disposition": "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
        "bound_parent_class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gap_ref": "coverage_gaps.CG2",
        "rule_refs": ["guards.G4", "guards.G5", "coverage_gaps.CG2"],
        "filing_verdict": "reject",
        "requested_scope": {
            "family": "SCC", "matter_model": "massless_scalar_field",
            "symmetry": "spherical", "regularity_token": "C0",
        },
        "decisive_hypothesis": (
            "AF-SCC-C0-VAC-GEN:H1/H2 fail (massless scalar + spherical); no SCC scalar class "
            "exists and both G4 (symmetry release) and G5 (matter swap) are violated."
        ),
    },
    "TC-F0-N10": {
        "disposition": "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
        "bound_parent_class_ids": ["AF-WCC-SCALAR-SPH"],
        "gap_ref": "coverage_gaps.CG2",
        "rule_refs": ["transfer_rules.forbidden.X3", "coverage_gaps.CG2"],
        "filing_verdict": "reject",
        "requested_scope": {
            "family": "WCC", "matter_model": "massless_scalar_field",
            "symmetry": "none_assumed", "asymptotics": "asymptotically_flat_3p1",
        },
        "decisive_hypothesis": (
            "AF-WCC-SCALAR-SPH:H2 fails (symmetry must be spherical); refiling the "
            "non-spherical scalar statement under the spherical class is the forbidden X3 "
            "symmetry release, so the scope needs a new class."
        ),
    },
    "TC-F0-N11": {
        "disposition": "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
        "bound_parent_class_ids": ["AF-WCC-SCALAR-SPH", "AF-WCC-VAC-GEN"],
        "gap_ref": "coverage_gaps.CG2",
        "rule_refs": [
            "guards.G5",
            "classes.AF-WCC-SCALAR-SPH.exclusions",
            "coverage_gaps.CG2",
        ],
        "filing_verdict": "reject",
        "requested_scope": {
            "family": "WCC", "matter_model": "vacuum",
            "symmetry": "spherical", "asymptotics": "asymptotically_flat_3p1",
        },
        "decisive_hypothesis": (
            "AF-WCC-SCALAR-SPH:H1 fails (the data are vacuum, not massless-scalar: G5 swap); "
            "spherical vacuum is also outside every frozen class, so the record is rejected "
            "as filed and its scope joins the same new-class request as TC-F0-N02."
        ),
    },
    "TC-F0-N14": {
        "disposition": "SPLIT_REQUIRED",
        "bound_parent_class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gap_ref": None,
        "rule_refs": ["guards.G3", "transfer_rules.forbidden.X5"],
        "filing_verdict": "reject_or_split",
        "requested_scope": None,
        "decisive_hypothesis": (
            "G3/X5: the paraphrase 'either continuously or twice-continuously differentiable' "
            "merges the C0 and C2 conclusions, which hard decision 1 keeps separate; the "
            "record must be split into the two frozen SCC classes or rejected."
        ),
    },
    "TC-F0-N15": {
        "disposition": "SPLIT_AND_BRIDGE_REQUIRED",
        "bound_parent_class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gap_ref": None,
        "rule_refs": ["transfer_rules.forbidden.X4", "guards.G1"],
        "filing_verdict": "reject_or_split",
        "requested_scope": None,
        "decisive_hypothesis": (
            "X4/G1: one filing asserts both the WCC visibility conclusion and the SCC "
            "C2-inextendibility conclusion; each files under its own frozen class and the "
            "cross-family implication needs a separate bridge artifact, so the record cannot "
            "resolve to exactly one class."
        ),
    },
    "TC-F0-N16": {
        "disposition": "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI",
        "bound_parent_class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gap_ref": "coverage_gaps.CG2",
        "rule_refs": [
            "field_vocabulary.asymptotics",
            "classes.AF-SCC-C0-VAC-GEN.exclusions",
            "coverage_gaps.CG2",
        ],
        "filing_verdict": "reject",
        "requested_scope": {
            "family": "SCC", "matter_model": "vacuum_with_positive_Lambda",
            "symmetry": "none_assumed", "asymptotics": "asymptotically_de_sitter_3p1",
            "regularity_token": "C0",
        },
        "decisive_hypothesis": (
            "AF-SCC-C0-VAC-GEN:H1 fails (Lambda=0 and asymptotically_flat_3p1 are required); "
            "asymptotically_de_sitter_3p1 and vacuum_with_positive_Lambda are outside the "
            "closed vocabulary, and CG2 routes them to a new class rather than to this one."
        ),
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_corpus() -> list[dict]:
    rows = []
    with CORPUS.open() as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    corpus = load_corpus()
    open_cases = [r for r in corpus if r.get("open") is True]
    tax = yaml.safe_load(TAXONOMY.read_text())
    frozen = list(tax["class_ids"])
    tax_sha = sha256(TAXONOMY)
    corpus_sha = sha256(CORPUS)

    missing = set(TABLE) - {r["case_id"] for r in open_cases}
    extra = {r["case_id"] for r in open_cases} - set(TABLE)
    if missing or extra:
        print(f"FATAL: table/corpus mismatch missing={sorted(missing)} extra={sorted(extra)}")
        return 2

    rows = []
    for rec in sorted(open_cases, key=lambda r: r["case_id"]):
        cid = rec["case_id"]
        spec = TABLE[cid]
        rows.append({
            "case_id": cid,
            "polarity": rec["polarity"],
            "filed_class_id": rec.get("as_filed_class_id"),
            "bound_parent_class_ids": spec["bound_parent_class_ids"],
            "disposition": spec["disposition"],
            "filing_verdict": spec["filing_verdict"],
            "gap_ref": spec["gap_ref"],
            "rule_refs": spec["rule_refs"],
            "leak_kind": rec.get("leak_kind"),
            "axis_vector": rec.get("axis_vector"),
            "violated_vocabulary": rec.get("violated_vocabulary"),
            "requested_scope": spec["requested_scope"],
            "decisive_hypothesis": spec["decisive_hypothesis"],
            "falsifier": rec["falsifier"],
            "evidence_refs": [
                f"schemas/taxonomy_cases.jsonl#{corpus_sha[:12]}#{cid}",
                f"research_map/formulation_taxonomy.yaml#{tax_sha[:12]}",
            ],
            "worker_can_adjudicate": False,
            "status": "proposed_not_adjudicated",
        })

    art = {
        "schema_version": "1.0",
        "artifact_type": "open_case_disposition_matrix",
        "artifact_id": "artifacts/flash-02/open_case_disposition.json",
        "node_id": "F0",
        "gate": "G-F0",
        "assignment_event_id": "asg-2026-09-11-F0-deepseek-flash-02-11",
        "actor": "deepseek-flash-02",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "authority": (
            "worker adjudication input only; the formulation lead and Human PI decide. "
            "No class id is created, no gate verdict is proposed, no node status is claimed."
        ),
        "corpus_ref": {
            "path": "schemas/taxonomy_cases.jsonl",
            "sha256": corpus_sha,
            "open_cases": len(open_cases),
        },
        "taxonomy_ref": {
            "path": "research_map/formulation_taxonomy.yaml",
            "sha256": tax_sha,
            "revision": tax.get("revision"),
            "status": tax.get("status"),
            "directive": tax.get("class_scope_adjudication", {}).get("directive"),
        },
        "frozen_class_ids": frozen,
        "disposition_tokens": DISPOSITION_TOKENS,
        "rows": rows,
        "summary": {
            "open_cases": len(open_cases),
            "rows": len(rows),
            "bijection": True,
            "new_class_ids_created": 0,
            "deferred_to_human_pi": sum(
                1 for r in rows if r["disposition"] == "NEW_CLASS_REQUEST_DEFERRED_TO_HUMAN_PI"
            ),
            "split_required": sum(1 for r in rows if r["disposition"] == "SPLIT_REQUIRED"),
            "split_and_bridge_required": sum(
                1 for r in rows if r["disposition"] == "SPLIT_AND_BRIDGE_REQUIRED"
            ),
        },
        "falsifier": (
            "Any corpus case with open=true missing from rows, any case appearing twice, any "
            "disposition token outside disposition_tokens, any AF-* token in this artifact that "
            "is not one of frozen_class_ids, or class_scope_adjudication.directive != "
            "astra-classscope-02 at the pinned taxonomy sha."
        ),
        "claims_theorem_status": False,
        "completion_claim": False,
    }
    OUT.write_text(json.dumps(art, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"written": str(OUT.relative_to(ROOT)), "sha256": sha256(OUT),
                      "summary": art["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
