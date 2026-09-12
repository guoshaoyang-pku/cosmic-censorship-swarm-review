#!/usr/bin/env python3
"""Primary-source promotion/drop audit of the five uncovered DET-REV12 candidates
(worker-009, bounded class-bound task).

Assignment : asg-2026-09-11-L1-deepseek-flash-09-18   (node L1, gate G-LIT)
Classes    : AF-SCC-C2-VAC-GEN ; AF-SCC-C0-VAC-GEN
Input      : the five DET-REV12 candidates reported as uncovered by
             artifacts/worker-009/classbinding/verification_classbinding_rev12_worker-009.json
             (SRC-014, SRC-029, SRC-033, SRC-048, SRC-061).
Next       : each candidate is re-fetched from its primary source; a candidate is
falsifier    PROMOTED to a class-binding correction only if a verbatim primary-source
             quote shows the cited model is NOT the frozen class's data class
             (4D Einstein vacuum, matter none, Lambda = 0, one-ended AF data), and
             DROPPED otherwise.  A re-fetch showing vacuum/Lambda=0 voids a
             promotion; a hash move on any pinned input voids the whole patch.

What this tool does (read-only against canonical state):
  1. binds every input by sha256 (canonical ledger, 7-row patch, theorem ledger,
     F2a/F2b, FROZEN.json, VARIANT_REGISTRY.json, the five re-fetched sources);
  2. extracts verbatim quotes from the re-fetched primary sources (arXiv e-print
     TeX, or the arXiv abs page where the e-print is unavailable) and hashes each
     quote; every quote must match a declared witness pattern exactly once;
  3. checks each candidate's canonical row, its used_by_theorems, and the
     theorem-layer class_ids that are the root cause of the leak;
  4. applies the promotion rule mechanically to the extracted flags and compares
     the result with the declared per-candidate decision;
  5. writes a 5-row machine-applicable correction proposal (same 21-column schema
     as the 7-row patch) plus a dry-run of the combined 12-row patch against a
     byte-faithful copy of the frozen canonical ledger, with a negative control;
  6. never writes ledger/citation_audit.csv.

Deterministic given --verified-at; no wall clock is read inside.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CANONICAL_LEDGER = ROOT / "ledger" / "citation_audit.csv"
PATCH_CSV = ROOT / "ledger" / "citation_audit_scc_classbinding_worker-009.csv"
THEOREMS = ROOT / "ledger" / "theorems.jsonl"
F2A = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
F2B = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"

OUT_RECORD = ROOT / "artifacts" / "worker-009" / "detrev12" / "verification_candidates_worker-009.json"
OUT_PATCH_CSV = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.csv"
OUT_PATCH_JSONL = ROOT / "ledger" / "citation_audit_scc_candidates_worker-009.jsonl"
OUT_DRYRUN = ROOT / "artifacts" / "worker-009" / "detrev12" / "dryrun_applied_citation_audit_12row.csv"

BOUND_LEDGER_SHA256 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
BOUND_PATCH_CSV_SHA256 = "47917e0e54bc447bab2143decdb22349cfea0214abea5a5619c125f55c1c70aa"
BOUND_THEOREMS_SHA256 = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
BOUND_F2A_SHA256 = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
BOUND_F2B_SHA256 = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
BOUND_REGISTRY_SHA256 = "5eb42f9a384a2bb327f1849fa571778fd88a2c5bf90f8a2c92d570383eb1363b"
BOUND_FROZEN_SHA256 = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"

PATCHED_ROWS = ["SRC-021", "SRC-056", "SRC-025", "SRC-058", "SRC-057", "SRC-024", "SRC-050"]
FROZEN_VACUUM_CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]

# Atomic evidence flags.  A candidate is promoted (its frozen vacuum class binding
# must be struck) iff one of these flags is established by a verbatim quote:
#   matter_nonvacuum  : the cited model carries matter (scalar / Maxwell / ...)
#   lambda_nonzero    : the cited model has a non-zero cosmological constant, or is
#                       a fixed de Sitter-type background
#   not_af_one_ended  : the cited data class is not one-ended asymptotically flat
#                       Lambda=0 vacuum data (spherical, two-ended, characteristic,
#                       linear-proxy, ...)
# Regularity-only mismatches are recorded (regularity_not_c2 / not_c2) but do not by
# themselves promote, because the frozen data class already fails on matter/Lambda for
# every candidate here; they are reported as separate findings.
CANDIDATES = [
    {
        "citation_id": "SRC-014",
        "old_class_mapping": "AF-SCC-C2-VAC-GEN;AF-WCC-SCALAR-SPH",
        "scc_class_ids_at_issue": ["AF-SCC-C2-VAC-GEN"],
        "retained_class_ids": ["AF-WCC-SCALAR-SPH"],
        "new_class_mapping": (
            "AF-WCC-SCALAR-SPH (WCC-side scalar tag retained with scope caveat); "
            "SCC-side frozen vacuum binding AF-SCC-C2-VAC-GEN removed; "
            "model-class: Einstein-massless-scalar spherical collapse; "
            "scope_use: do-not-transfer; no AF-SCC-*-VAC-GEN binding"
        ),
        "matter_model": "Einstein-massless-scalar (spherical gravitational collapse of a scalar field)",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": ["D-007"],
        "decision": "PROMOTE",
        "source_kind": "arxiv_abs_html",
        "source_path": "artifacts/worker-009/detrev12/src/abs_math_9901147.html",
        "source_pin_sha256": "917a7cbf590eb78aecdafadfe97abe4cdcdd55770217a36077438a5d8a14dac6",
        "source_member": "",
        "source_member_pin_sha256": "",
        "locator": "https://arxiv.org/abs/math/9901147",
        "refetch_note": (
            "e-print https://arxiv.org/e-print/math/9901147 returned HTTP 403 "
            "(source not available at the time of refetch); title and abstract are "
            "read from the authoritative arXiv abstract page instead"
        ),
        "quotes": [
            {
                "qid": "Q14-TITLE",
                "role": "title",
                "pattern": r'<meta name="citation_title" content="([^"]*)"',
                "group": 1,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q14-ABS",
                "role": "abstract",
                "pattern": r'<meta name="citation_abstract" content="([^"]*)"',
                "group": 1,
                "flag": "matter_nonvacuum",
            },
        ],
        "concluded_flags": ["matter_nonvacuum"],
        "class_binding_finding": (
            "Christodoulou 1999 is the spherical gravitational collapse of a scalar field "
            "(Einstein-massless-scalar system), not 4D Einstein vacuum Lambda=0; the frozen "
            "SCC vacuum class id AF-SCC-C2-VAC-GEN carries a matter-model source. The "
            "AF-WCC-SCALAR-SPH tag is supported by T-101/T-523/T-525 and is retained."
        ),
        "falsifier": (
            "Any of the following voids this correction: (a) ledger/citation_audit.csv no "
            "longer hashes to 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9; "
            "(b) a re-fetch or the published Annals version shows the collapse model is the 4D "
            "Einstein vacuum equations with Lambda=0 and no scalar field, or that the arXiv "
            "title/abstract do not correspond to the cited work; (c) the lead's class_mapping "
            "derivation regenerates a frozen class id for this row."
        ),
    },
    {
        "citation_id": "SRC-029",
        "old_class_mapping": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "scc_class_ids_at_issue": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "retained_class_ids": [],
        "new_class_mapping": (
            "(evidence/tag only; model-class: Einstein-Maxwell-real-scalar with Lambda>0, "
            "spherical characteristic data; scope_use: do-not-transfer; no class-id binding)"
        ),
        "matter_model": "Einstein-Maxwell-real massless scalar field, positive cosmological constant, spherical symmetry",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": ["D-004"],
        "decision": "PROMOTE",
        "source_kind": "arxiv_eprint_tex",
        "source_path": "artifacts/worker-009/detrev12/src/1707_08975.tar.gz",
        "source_pin_sha256": "43c124b5fad5beacd23c06e2ec907d8933e7ee8c053ecf00199e13af5286e9c8",
        "source_member": "artifacts/worker-009/detrev12/src/x1707/Price_law_revised.tex",
        "source_member_pin_sha256": "a1220288344974e92d0b23611904b7c068c2873fd4e353e8a9dc1780013f2061",
        "locator": "https://arxiv.org/e-print/1707.08975",
        "refetch_note": "complete arXiv e-print TeX source fetched (HTTP 200)",
        "quotes": [
            {
                "qid": "Q29-INTRO",
                "role": "model",
                "pattern": r"In this paper we study the spherically symmetric characteristic initial data problem for the Einstein-Maxwell-scalar\s+field system with a positive cosmological constant in the interior of a black hole, assuming an exponential Price law",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q29-MODEL",
                "role": "equations",
                "pattern": r"We consider the Einstein-Maxwell-real massless scalar field equations in the presence of a cosmological constant \$\\Lambda\$",
                "group": 0,
                "flag": "lambda_nonzero",
            },
            {
                "qid": "Q29-THM",
                "role": "theorem statement",
                "pattern": r"\\begin\{Thm\}\s*\n\\label\{thmMain\}\s*\nConsider the characteristic initial value problem for the spherically symmetric Einstein-Maxwell-scalar field system",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q29-CONCL",
                "role": "conclusion",
                "pattern": r"In particular, no \$C\^2\$ extensions across the Cauchy horizon exist\.",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
        ],
        "concluded_flags": ["matter_nonvacuum", "lambda_nonzero"],
        "class_binding_finding": (
            "Costa-Girao-Natario-Drumond Silva (thmMain) solve the spherically symmetric "
            "Einstein-Maxwell-real-scalar characteristic initial value problem with Lambda>0; "
            "the paper's own no-C^2-extension conclusion is for that non-vacuum, non-zero-Lambda "
            "model. Binding it to frozen AF-SCC-C0-VAC-GEN / AF-SCC-C2-VAC-GEN is a data-class "
            "leak; T-503/T-519 both record does_not_imply denials of vacuum transfer."
        ),
        "falsifier": (
            "Any of the following voids this correction: (a) ledger/citation_audit.csv no longer "
            "hashes to 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9; (b) a "
            "re-fetch of arXiv:1707.08975 shows the matter content is 4D Einstein vacuum with "
            "Lambda=0 and no scalar/Maxwell field, or that thmMain is not the theorem quoted; "
            "(c) the lead's class_mapping derivation regenerates a frozen class id for this row."
        ),
    },
    {
        "citation_id": "SRC-033",
        "old_class_mapping": "AF-SCC-C2-VAC-GEN",
        "scc_class_ids_at_issue": ["AF-SCC-C2-VAC-GEN"],
        "retained_class_ids": [],
        "new_class_mapping": (
            "(evidence/tag only; model-class: linear wave equation on a fixed subextremal "
            "Reissner-Nordstrom-de Sitter / Kerr-Newman-de Sitter background, Lambda>0; "
            "scope_use: do-not-transfer; no class-id binding)"
        ),
        "matter_model": "linear scalar wave on a fixed electrovacuum Reissner-Nordstrom-de Sitter / Kerr-Newman-de Sitter background",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": ["D-007"],
        "decision": "PROMOTE",
        "source_kind": "arxiv_eprint_tex",
        "source_path": "artifacts/worker-009/detrev12/src/1805_08764.tar.gz",
        "source_pin_sha256": "90b4104c885f4607b1047ce5b5756636a1016ba660b70400508de33c5a868b99",
        "source_member": "artifacts/worker-009/detrev12/src/x1805/revision.tex",
        "source_member_pin_sha256": "938f172376a2a2e10dfc3d8457d3d448a969c423851725d237302f60144d5161",
        "locator": "https://arxiv.org/e-print/1805.08764",
        "refetch_note": "complete arXiv e-print TeX source fetched (HTTP 200)",
        "quotes": [
            {
                "qid": "Q33-THM",
                "role": "main theorem",
                "pattern": r"\\begin\{theorem\}\s*\n\\label\{maintheoremINTRO\}\s*\nConsider a subextremal Reissner--Nordstr\\\"om--de Sitter spacetime, or more generally,\s*\nKerr--Newman--de Sitter spacetime \$\\widetilde\{\\mathcal\{M\}\}\$\.",
                "group": 0,
                "flag": "not_af_one_ended",
            },
            {
                "qid": "Q33-PURPOSE",
                "role": "proxy problem",
                "pattern": r"We will prove\s+that, at the level of the proxy\s+problem \$\(\\ref\{linearwaveequation\}\)\$,\s+there is indeed a way to retain the\s+desirable generic\s+\$H\^1_\{\\rm loc\}\$ blowup at the Cauchy horizon:.*?class of initial data\.\}",
                "group": 0,
                "flag": "not_af_one_ended",
            },
            {
                "qid": "Q33-LAMBDA",
                "role": "cosmological constant",
                "pattern": r"which admit in the case \$\\Lambda>0\$\s*\nthe so-called\s+Kerr--de Sitter solutions",
                "group": 0,
                "flag": "lambda_nonzero",
            },
        ],
        "concluded_flags": ["lambda_nonzero", "not_af_one_ended"],
        "class_binding_finding": (
            "Dafermos-Shlapentokh-Rothman (maintheoremINTRO) prove an H^1_loc blow-up statement "
            "for the linear wave equation on a FIXED subextremal RN-dS/KN-dS background with "
            "Lambda>0; the paper is explicit that the electromagnetic field is background and "
            "irrelevant to the analysis. It is neither nonlinear Einstein vacuum Lambda=0 nor "
            "one-ended asymptotically flat data; T-508 records the same non-transfer."
        ),
        "falsifier": (
            "Any of the following voids this correction: (a) ledger/citation_audit.csv no longer "
            "hashes to 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9; (b) a "
            "re-fetch of arXiv:1805.08764 shows the result is for the nonlinear Einstein vacuum "
            "equations with Lambda=0 on asymptotically flat data, or that maintheoremINTRO is not "
            "the theorem the row relies on; (c) the lead's class_mapping derivation regenerates a "
            "frozen class id for this row."
        ),
    },
    {
        "citation_id": "SRC-048",
        "old_class_mapping": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "scc_class_ids_at_issue": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "retained_class_ids": [],
        "new_class_mapping": (
            "(evidence/tag only; model-class: Reissner-Nordstrom-Vaidya and Einstein-Maxwell-scalar "
            "spherical two-ended perturbations; extension class C^0 cap W^{1,s}_loc, s>1; "
            "scope_use: do-not-transfer; no class-id binding)"
        ),
        "matter_model": "Reissner-Nordstrom-Vaidya (charged null dust) and Einstein-Maxwell-scalar spherical perturbations",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C0-VAC-GEN;AF-SCC-C2-VAC-GEN",
        "root_cause_theorem_ids": ["D-005"],
        "decision": "PROMOTE",
        "source_kind": "arxiv_eprint_tex",
        "source_path": "artifacts/worker-009/detrev12/src/2609_05167.tar.gz",
        "source_pin_sha256": "5561438d671ae4639151c5feba4ea6a37a6d33b3304701a350e7a79967b0dc81",
        "source_member": "artifacts/worker-009/detrev12/src/x2609/main.tex",
        "source_member_pin_sha256": "fbe4776ab2eed09d43186810e346a7a81dd34fb0454b1ba28dbcdb621323dbef",
        "locator": "https://arxiv.org/e-print/2609.05167",
        "refetch_note": "complete arXiv e-print TeX source fetched (HTTP 200)",
        "quotes": [
            {
                "qid": "Q48-ABS1",
                "role": "abstract: regularity",
                "pattern": r"we prove the inextendibility of spherically symmetric weak null singularities as spherically symmetric Lorentzian manifolds with a continuous metric and Christoffel symbols in \$L\^\{s\}_\{\\loc\}\$ for \$s >1\$\.",
                "group": 0,
                "flag": "not_af_one_ended",
            },
            {
                "qid": "Q48-ABS2",
                "role": "abstract: models",
                "pattern": r"In particular we show that these assumptions are satisfied by the Reissner-Nordstr.{0,8}m-Vaidya spacetime as well as by a class of spacetimes arising from small and generic spherically symmetric perturbations of subextremal Reissner-Nordstr.{0,8}m under the Einstein-Maxwell-scalar field system\.",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q48-THM",
                "role": "main theorem conclusion",
                "pattern": r"Then there is no strongly spherically symmetric \$C\^0\\cap W\^\{1,s\}_\{\\loc\}\$-extension.*?at \$\(u_\*,0\)\$\.",
                "group": 0,
                "flag": "not_af_one_ended",
            },
            {
                "qid": "Q48-DLO",
                "role": "corollary model",
                "pattern": r"\\begin\{cor\}\[Dafermos-Luk-Oh spacetimes\]\\label\{cor:DLO\}\s*\\red\{Suppose that \$\(M_\{DLO\},g_\{DLO\}\)\$ arises from a solution to the Einstein-Maxwell-scalar field system",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q48-RNV",
                "role": "corollary model",
                "pattern": r"\\begin\{cor\}\[Reissner-Nordstr\\\"\{o\}m-Vaidya\]\\label\{cor:RNV\}",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
        ],
        "concluded_flags": ["matter_nonvacuum", "not_af_one_ended"],
        "class_binding_finding": (
            "Cameron-Sbierski prove C^0 cap W^{1,s}_loc-inextendibility (s>1) for RN-Vaidya and "
            "for spherical Einstein-Maxwell-scalar perturbations of subextremal RN. The source is "
            "non-vacuum, two-ended/spherical, and its extension class is not the frozen classical "
            "C2 vacuum extension predicate; T-304 records 'Does not prove C^2 SCC in vacuum'. Both "
            "frozen vacuum bindings are leaks."
        ),
        "falsifier": (
            "Any of the following voids this correction: (a) ledger/citation_audit.csv no longer "
            "hashes to 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9; (b) a "
            "re-fetch of arXiv:2609.05167 shows the result is for 4D Einstein vacuum Lambda=0 data, "
            "or that cor:RNV / cor:DLO are absent or state something else; (c) the lead's "
            "class_mapping derivation regenerates a frozen class id for this row."
        ),
    },
    {
        "citation_id": "SRC-061",
        "old_class_mapping": "AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
        "scc_class_ids_at_issue": ["AF-SCC-C0-VAC-GEN"],
        "retained_class_ids": ["AF-WCC-SCALAR-SPH"],
        "new_class_mapping": (
            "AF-WCC-SCALAR-SPH (scalar-side tag retained; T-516 registers this source for the "
            "neutral-scalar case with optional Maxwell field); SCC-side frozen vacuum binding "
            "AF-SCC-C0-VAC-GEN removed; model-class: Einstein-Maxwell-(real)-scalar spherical; "
            "scope_use: do-not-transfer; no AF-SCC-*-VAC-GEN binding"
        ),
        "matter_model": "Einstein-Maxwell-(real)-scalar, spherical symmetry (neutral scalar main case)",
        "registry_variant_pointer": "",
        "relevant_class_nonbinding": "AF-SCC-C0-VAC-GEN",
        "root_cause_theorem_ids": ["D-002"],
        "decision": "PROMOTE",
        "source_kind": "arxiv_eprint_tex",
        "source_path": "artifacts/worker-009/detrev12/src/gr-qc_0309115.tar.gz",
        "source_pin_sha256": "80be01a4222ba8156f2b12159039163551454cee10668b266e731cde303e58d9",
        "source_member": "artifacts/worker-009/detrev12/src/x0309115/pricelaw3.tex",
        "source_member_pin_sha256": "e930b36f8282e5851f913598adf229cd9afaf189c9c43100ea1e12081c6e9c07",
        "locator": "https://arxiv.org/e-print/gr-qc/0309115",
        "refetch_note": "complete arXiv e-print TeX source fetched (HTTP 200)",
        "quotes": [
            {
                "qid": "Q61-TITLE",
                "role": "title",
                "pattern": r"of Price's law for the collapse of a self-gravitating scalar field",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q61-THM",
                "role": "main theorem",
                "pattern": r"Consider spacelike spherically symmetric initial\s*\n?data for the Einstein-Maxwell-scalar field equations, with at least one\s*\nasymptotically flat end, such that\s*\nthe scalar field and its gradient have compact support on the initial\s*\nhypersurface\.",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q61-MODEL",
                "role": "equations",
                "pattern": r"The theory will be described by the Einstein-Maxwell-real scalar field equations",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
            {
                "qid": "Q61-CONJ",
                "role": "conjecture scope",
                "pattern": r"conjecture for the Einstein-Maxwell-real scalar field system",
                "group": 0,
                "flag": "matter_nonvacuum",
            },
        ],
        "concluded_flags": ["matter_nonvacuum"],
        "class_binding_finding": (
            "Dafermos-Rodnianski (int-the) state the main theorem for the Einstein-Maxwell-scalar "
            "field equations with a scalar field of compact support; matter is present in every "
            "case, so the row cannot carry the frozen vacuum class AF-SCC-C0-VAC-GEN. T-501 "
            "records 'Does not imply the same for vacuum'; T-516 registers AF-WCC-SCALAR-SPH for "
            "this source, which is why that tag is retained."
        ),
        "falsifier": (
            "Any of the following voids this correction: (a) ledger/citation_audit.csv no longer "
            "hashes to 315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9; (b) a "
            "re-fetch of arXiv:gr-qc/0309115 shows the collapse model is 4D Einstein vacuum with "
            "Lambda=0, or that int-the is stated for the vacuum equations; (c) the lead's "
            "class_mapping derivation regenerates a frozen class id for this row."
        ),
    },
]

PATCH_COLUMNS = [
    "correction_id",
    "canonical_file",
    "canonical_file_sha256",
    "canonical_row_id",
    "old_class_mapping",
    "new_class_mapping",
    "matter_model",
    "scope_use",
    "registry_variant_pointer",
    "relevant_class_nonbinding",
    "root_cause_theorem_ids",
    "source_tex_file",
    "source_tex_sha256",
    "quote_tex",
    "quote_tex_sha256",
    "spotcheck_id",
    "spotcheck_quote_sha256",
    "evidence_basis",
    "class_binding_finding",
    "verification_status",
    "falsifier",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def read_ledger(path: Path):
    """Return (fieldnames, rows, raw_bytes, roundtrip_bytes)."""
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    rdr = csv.reader(io.StringIO(text, newline=""))
    rows = list(rdr)
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerows(rows)
    return rows[0], rows[1:], raw, out.getvalue().encode("utf-8")


def extract_quote(path: Path, spec: dict):
    """Return list of quote records for one candidate spec (found exactly once each)."""
    raw = path.read_bytes()
    out = []
    for q in spec["quotes"]:
        pat = q["pattern"].encode("utf-8")
        ms = list(re.finditer(pat, raw, re.S))
        rec = {
            "qid": q["qid"],
            "role": q["role"],
            "flag": q["flag"],
            "source_file": str(path.relative_to(ROOT)),
            "matches": len(ms),
            "sha256": None,
            "line": None,
            "byte_length": None,
            "text": None,
        }
        if len(ms) == 1:
            m = ms[0]
            if q.get("group", 0) == 0:
                g = m.group(0)
            else:
                g = m.group(q["group"])
            rec["sha256"] = sha256_bytes(g)
            rec["line"] = raw[: m.start()].count(b"\n") + 1
            rec["byte_length"] = len(g)
            rec["text"] = g.decode("utf-8", "replace")
        out.append(rec)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verified-at", required=True)
    args = ap.parse_args()

    checks = []

    def check(cid, desc, ok, detail=""):
        checks.append(
            {"check_id": cid, "description": desc, "result": "PASS" if ok else "FAIL", "detail": str(detail)[:400]}
        )
        return ok

    # --- input binding -----------------------------------------------------
    ledger_fields, ledger_rows, ledger_raw, ledger_rt = read_ledger(CANONICAL_LEDGER)
    by_id = {r[0]: r for r in ledger_rows}
    fi = {name: i for i, name in enumerate(ledger_fields)}

    lineterm = "CRLF" if b"\r\n" in ledger_raw else "LF"
    check("V01", "canonical ledger hashes to the frozen L1 sha",
          sha256_bytes(ledger_raw) == BOUND_LEDGER_SHA256, sha256_bytes(ledger_raw))
    check("V02", "canonical ledger round-trips byte-identically (CRLF preserved)",
          ledger_rt == ledger_raw, f"lineterm={lineterm}")
    check("V03", "canonical ledger shape is 97 rows x 25 columns",
          len(ledger_rows) == 97 and len(ledger_fields) == 25, f"rows={len(ledger_rows)} cols={len(ledger_fields)}")
    check("V04", "7-row patch CSV hashes to its declared sha",
          sha256_file(PATCH_CSV) == BOUND_PATCH_CSV_SHA256, sha256_file(PATCH_CSV))
    check("V05", "theorem ledger hashes to the sha the patch verification pinned",
          sha256_file(THEOREMS) == BOUND_THEOREMS_SHA256, sha256_file(THEOREMS))
    check("V06", "rev12 F2a/F2b schema bytes are the pinned bytes",
          sha256_file(F2A) == BOUND_F2A_SHA256 and sha256_file(F2B) == BOUND_F2B_SHA256,
          f"F2a={sha256_file(F2A)[:12]} F2b={sha256_file(F2B)[:12]}")
    check("V07", "FROZEN.json and VARIANT_REGISTRY.json are the pinned bytes",
          sha256_file(FROZEN) == BOUND_FROZEN_SHA256 and sha256_file(REGISTRY) == BOUND_REGISTRY_SHA256,
          f"FROZEN={sha256_file(FROZEN)[:12]} REGISTRY={sha256_file(REGISTRY)[:12]}")

    # theorem ledger records
    theo = {}
    for line in THEOREMS.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        tid = r.get("theorem_id") or r.get("id")
        if tid:
            theo[tid] = r

    # --- per-candidate primary-source verification -------------------------
    candidate_records = []
    for spec in CANDIDATES:
        cid = spec["citation_id"]
        rec = {
            "citation_id": cid,
            "class_ids": CLASS_IDS,
            "scc_class_ids_at_issue": spec["scc_class_ids_at_issue"],
            "retained_class_ids": spec["retained_class_ids"],
            "old_class_mapping": spec["old_class_mapping"],
            "new_class_mapping": spec["new_class_mapping"],
            "matter_model": spec["matter_model"],
            "decision": spec["decision"],
            "concluded_flags": spec["concluded_flags"],
            "root_cause_theorem_ids": spec["root_cause_theorem_ids"],
            "locator": spec["locator"],
            "refetch_note": spec["refetch_note"],
            "source_path": spec["source_path"],
            "source_sha256": None,
            "source_pin_match": False,
            "quotes": [],
        }
        n = int(cid.split("-")[1])
        idx = len(candidate_records) + 1

        # canonical row exists and matches the declared old mapping
        row = by_id.get(cid)
        check(f"C{idx:02d}-01", f"{cid}: canonical row exists", row is not None)
        if row is None:
            candidate_records.append(rec)
            continue
        check(f"C{idx:02d}-02", f"{cid}: canonical class_mapping equals the declared old mapping",
              row[fi["class_mapping"]] == spec["old_class_mapping"], row[fi["class_mapping"]])
        check(f"C{idx:02d}-03", f"{cid}: every class id at issue is present in the canonical row",
              all(c in row[fi["class_mapping"]] for c in spec["scc_class_ids_at_issue"]))
        with open(PATCH_CSV, newline="") as f:
            prior_patch_rows = {r["canonical_row_id"] for r in csv.DictReader(f)}
        check(f"C{idx:02d}-04", f"{cid}: row is not already covered by the 7-row patch",
              cid not in PATCHED_ROWS and cid not in prior_patch_rows,
              f"patched={sorted(prior_patch_rows)}")

        src = ROOT / spec["source_path"]
        rec["source_sha256"] = sha256_file(src) if src.exists() else None
        rec["source_pin_match"] = rec["source_sha256"] == spec["source_pin_sha256"]
        check(f"C{idx:02d}-05", f"{cid}: re-fetched source hashes to its pin",
              rec["source_pin_match"], rec["source_sha256"])

        if spec["source_kind"] == "arxiv_eprint_tex":
            member = ROOT / spec["source_member"]
            msha = sha256_file(member) if member.exists() else None
            check(f"C{idx:02d}-06", f"{cid}: extracted TeX member hashes to its pin",
                  msha == spec["source_member_pin_sha256"], msha)
            qpath = member
        else:
            qpath = src
            check(f"C{idx:02d}-06", f"{cid}: non-TeX source (abs page); e-print unavailable recorded",
                  "403" in spec["refetch_note"], spec["refetch_note"][:80])

        quotes = extract_quote(qpath, spec)
        rec["quotes"] = quotes
        for q in quotes:
            check(f"C{idx:02d}-q-{q['qid']}", f"{cid}: quote {q['qid']} found exactly once",
                  q["matches"] == 1, f"matches={q['matches']} line={q['line']}")

        # decision rule: promotion requires >=1 established atomic flag, each witnessed
        witnessed = {q["flag"] for q in quotes if q["matches"] == 1}
        ok_flags = all(f in witnessed for f in spec["concluded_flags"]) and len(spec["concluded_flags"]) > 0
        check(f"C{idx:02d}-07", f"{cid}: every concluded flag is witnessed by an extracted quote",
              ok_flags, f"concluded={spec['concluded_flags']} witnessed={sorted(witnessed)}")
        rule_promote = len(spec["scc_class_ids_at_issue"]) > 0 and len(set(spec["concluded_flags"]) & {
            "matter_nonvacuum", "lambda_nonzero", "not_af_one_ended"}) > 0
        expect = "PROMOTE" if rule_promote else "DROP"
        check(f"C{idx:02d}-08", f"{cid}: declared decision follows the mechanical promotion rule",
              spec["decision"] == expect, f"declared={spec['decision']} rule={expect}")

        # theorem-layer root cause carries the leaked class id
        used = [t for t in row[fi["used_by_theorems"]].split(";") if t]
        root_hits = []
        for t in spec["root_cause_theorem_ids"]:
            trec = theo.get(t)
            if trec and set(trec.get("class_ids", [])) & set(spec["scc_class_ids_at_issue"]):
                root_hits.append(t)
        check(f"C{idx:02d}-09", f"{cid}: a root-cause theorem among used_by carries the leaked class id",
              t in used and bool(root_hits), f"used={used} root_hits={root_hits}")

        # theorem-layer does_not_imply denials recorded, when present
        denials = []
        for t in used:
            trec = theo.get(t) or {}
            for d in trec.get("does_not_imply", []):
                if re.search(r"vacuum|transfer|does not apply|Not the C", d, re.I):
                    denials.append({"theorem_id": t, "does_not_imply": d})
        rec["theorem_layer_denials"] = denials
        check(f"C{idx:02d}-10", f"{cid}: theorem layer records at least one vacuum non-transfer caveat",
              len(denials) >= 1, len(denials))

        candidate_records.append(rec)

    # --- extended patch + dry run ------------------------------------------
    patch_rows = []
    for i, rec in enumerate(candidate_records, start=8):
        spec = next(s for s in CANDIDATES if s["citation_id"] == rec["citation_id"])
        primary = next((q for q in rec["quotes"] if q["sha256"]), None)
        secondary = next((q for q in rec["quotes"] if q["sha256"] and q is not primary), None)
        patch_rows.append(
            {
                "correction_id": f"CBC-09-{i:03d}",
                "canonical_file": "ledger/citation_audit.csv",
                "canonical_file_sha256": BOUND_LEDGER_SHA256,
                "canonical_row_id": rec["citation_id"],
                "old_class_mapping": spec["old_class_mapping"],
                "new_class_mapping": spec["new_class_mapping"],
                "matter_model": spec["matter_model"],
                "scope_use": "do-not-transfer",
                "registry_variant_pointer": spec["registry_variant_pointer"],
                "relevant_class_nonbinding": spec["relevant_class_nonbinding"],
                "root_cause_theorem_ids": ";".join(spec["root_cause_theorem_ids"]),
                "source_tex_file": rec["quotes"][0]["source_file"],
                "source_tex_sha256": spec["source_member_pin_sha256"] or spec["source_pin_sha256"],
                "quote_tex": primary["text"],
                "quote_tex_sha256": primary["sha256"],
                "spotcheck_id": f"SC-09-{i:03d}",
                "spotcheck_quote_sha256": secondary["sha256"] if secondary else "",
                "evidence_basis": "worker-009-detrev12-refetch-" + args.verified_at.replace("-", "").replace(":", "")[:15],
                "class_binding_finding": spec["class_binding_finding"],
                "verification_status": "unverified",
                "falsifier": spec["falsifier"],
            }
        )

    with open(OUT_PATCH_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PATCH_COLUMNS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(patch_rows)
    with open(OUT_PATCH_JSONL, "w") as f:
        for row in patch_rows:
            obj = dict(row)
            obj["artifact_type"] = "class_binding_correction"
            obj["class_ids"] = CLASS_IDS
            obj["gate"] = "G-LIT"
            obj["group_id"] = "literature"
            obj["node_id"] = "L1"
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    all_patch_rows = []
    with open(PATCH_CSV, newline="") as f:
        all_patch_rows.extend(list(csv.DictReader(f)))
    all_patch_rows.extend(patch_rows)

    # apply to a byte-faithful copy
    applied = [list(r) for r in ledger_rows]
    changed_cells = []
    refused = []
    ci = fi["class_mapping"]
    ri = fi["citation_id"]
    for pr in all_patch_rows:
        target = None
        for r in applied:
            if r[ri] == pr["canonical_row_id"]:
                target = r
                break
        if target is None or target[ci] != pr["old_class_mapping"]:
            refused.append(pr["correction_id"])
            continue
        if target[ci] != pr["new_class_mapping"]:
            target[ci] = pr["new_class_mapping"]
            changed_cells.append((pr["correction_id"], pr["canonical_row_id"]))
    check("D01", "all 12 patch rows apply to the frozen canonical ledger",
          len(changed_cells) == 12 and not refused, f"changed={len(changed_cells)} refused={refused}")
    check("D02", "exactly 12 cells of 97x25 change",
          len(changed_cells) == 12, f"changed_cells={len(changed_cells)}")

    # negative control: mutate one old mapping, applier must refuse
    neg = dict(all_patch_rows[0])
    neg["old_class_mapping"] = "AF-SCC-C2-VAC-GEN"
    neg_applied = [list(r) for r in ledger_rows]
    neg_refused = False
    for r in neg_applied:
        if r[ri] == neg["canonical_row_id"]:
            if r[ci] != neg["old_class_mapping"]:
                neg_refused = True
            break
    check("D03", "negative control: stale old_class_mapping is refused", neg_refused)

    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerows([ledger_fields] + applied)
    OUT_DRYRUN.write_bytes(out.getvalue().encode("utf-8"))
    dry_run_sha = sha256_file(OUT_DRYRUN)

    # untouched-cell check: only the class_mapping column differs
    diffs = 0
    for a, b in zip(ledger_rows, applied):
        for j, (x, y) in enumerate(zip(a, b)):
            if x != y:
                if j != ci:
                    diffs += 1
    check("D04", "no cell outside class_mapping is modified by the dry run", diffs == 0, f"unexpected={diffs}")

    dry_fields, dry_rows, _, _ = read_ledger(OUT_DRYRUN)
    check("D05", "dry-run ledger keeps the canonical header and all 97 data rows",
          dry_fields == ledger_fields and len(dry_rows) == 97, f"rows={len(dry_rows)}")

    all_pass = all(c["result"] == "PASS" for c in checks)

    record = {
        "verification_id": "worker-009-detrev12-candidates-" + args.verified_at,
        "created_at": args.verified_at,
        "verified_at": args.verified_at,
        "worker": "worker-009",
        "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
        "node_id": "L1",
        "gate": "G-LIT",
        "group_id": "literature",
        "class_ids": CLASS_IDS,
        "task": "primary-source promotion/drop audit of the five DET-REV12 uncovered candidates",
        "canonical_write": "none - proposal only; lead-literature owns ledger/citation_audit.csv",
        "inputs": {
            "ledger/citation_audit.csv": sha256_bytes(ledger_raw),
            "ledger/citation_audit_scc_classbinding_worker-009.csv": sha256_file(PATCH_CSV),
            "ledger/theorems.jsonl": sha256_file(THEOREMS),
            "schemas/af_scc_c2_vacuum.yaml": sha256_file(F2A),
            "schemas/af_scc_c0_vacuum.yaml": sha256_file(F2B),
            "artifacts/formulation/FROZEN.json": sha256_file(FROZEN),
            "artifacts/formulation/VARIANT_REGISTRY.json": sha256_file(REGISTRY),
            "sources": {c["citation_id"]: c["source_sha256"] for c in candidate_records},
        },
        "candidates": candidate_records,
        "counts": {
            "candidates": len(candidate_records),
            "promoted": sum(1 for c in candidate_records if c["decision"] == "PROMOTE"),
            "dropped": sum(1 for c in candidate_records if c["decision"] == "DROP"),
            "patch_rows_total": len(all_patch_rows),
            "changed_cells_in_dry_run": len(changed_cells),
            "canonical_cells": len(ledger_rows) * len(ledger_fields),
        },
        "dryrun": {
            "path": str(OUT_DRYRUN.relative_to(ROOT)),
            "sha256": dry_run_sha,
            "rows": len(applied),
            "cols": len(ledger_fields),
            "header": ledger_fields,
            "changed": [{"correction_id": a, "canonical_row_id": b} for a, b in changed_cells],
        },
        "proposed_patch": {
            "csv": str(OUT_PATCH_CSV.relative_to(ROOT)),
            "jsonl": str(OUT_PATCH_JSONL.relative_to(ROOT)),
            "correction_ids": [p["correction_id"] for p in patch_rows],
        },
        "checks": checks,
        "all_checks_pass": all_pass,
        "falsifier": (
            "A re-fetch showing that any promoted source is 4D Einstein vacuum with Lambda=0 and "
            "no matter field, or that the quoted theorem label does not exist in the cited version, "
            "drops that candidate; a move of ledger/citation_audit.csv, ledger/theorems.jsonl, either "
            "rev12 SCC schema, FROZEN.json or VARIANT_REGISTRY.json voids the patch; a lead "
            "regeneration that keeps a frozen class id on any promoted row voids the derivation fix."
        ),
        "next_falsifier": (
            "Run DET-REV12 over the dry-run ledger: it must return zero uncovered candidates on the "
            "12 patched rows; a surviving frozen vacuum id on SRC-014/029/033/048/061, or a "
            "theorem-layer regeneration that reintroduces one, falsifies this promotion pass. "
            "Independent lead-literature review of the five verbatim quotes is still required; this "
            "record is author self-verification, not an independent verdict."
        ),
        "worker_authority_note": (
            "worker events cannot set status=done, validation_status=passed, or a gate verdict; "
            "this record is a completion claim and proposal for lead-literature adjudication."
        ),
    }
    OUT_RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n")

    print(json.dumps({
        "verification_id": record["verification_id"],
        "all_checks_pass": all_pass,
        "checks": f"{sum(1 for c in checks if c['result']=='PASS')}/{len(checks)}",
        "record": str(OUT_RECORD.relative_to(ROOT)),
        "record_sha256": sha256_file(OUT_RECORD),
        "patch_csv": str(OUT_PATCH_CSV.relative_to(ROOT)),
        "patch_csv_sha256": sha256_file(OUT_PATCH_CSV),
        "patch_jsonl": str(OUT_PATCH_JSONL.relative_to(ROOT)),
        "patch_jsonl_sha256": sha256_file(OUT_PATCH_JSONL),
        "dryrun": str(OUT_DRYRUN.relative_to(ROOT)),
        "dryrun_sha256": dry_run_sha,
        "promoted": record["counts"]["promoted"],
        "dropped": record["counts"]["dropped"],
        "changed_cells": record["counts"]["changed_cells_in_dry_run"],
    }, indent=1))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
