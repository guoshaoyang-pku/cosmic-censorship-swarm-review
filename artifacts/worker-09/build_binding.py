#!/usr/bin/env python3
"""worker-09 / L1: bind the SCC-side verified sources to the two frozen SCC schemas.

Answers the `citation_status: unresolved (L1 owns the anchor)` slots in
schemas/af_scc_c0_vacuum.yaml and schemas/af_scc_c2_vacuum.yaml using only rows present in the
frozen shard ledger/citation_audit_scc_flash-09.csv and the canonical ledger/citation_audit.csv.
Every disposition is resolved | partial | unresolved; nothing is promoted beyond the source.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

SHARD = ROOT / "ledger" / "citation_audit_scc_flash-09.csv"
CANON = ROOT / "ledger" / "citation_audit.csv"
REV2 = ROOT / "ledger" / "citation_audit_scc_flash-09.rev2.csv"
OUT = ROOT / "artifacts" / "worker-09" / "scc_class_binding.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(p: Path) -> str:
    return f"{p.relative_to(ROOT)}#{sha(p)[:16]}"


shard_rows = {r["citation_id"]: r for r in csv.DictReader(SHARD.open())}
canon_rows = {r["citation_id"]: r for r in csv.DictReader(CANON.open())}
rev2_rows = {r["citation_id"]: r for r in csv.DictReader(REV2.open())}

SHARD_REF, CANON_REF, REV2_REF = ref(SHARD), ref(CANON), ref(REV2)

ENTRIES = [
    {
        "slot": "af_scc_c0_vacuum.yaml:83",
        "slot_text": "candidate_tool spacelike-diameter obstruction, identifier arXiv:1507.00601, "
                     "'L1 must confirm author, scope (Schwarzschild-type interiors only) and that it is "
                     "not imported as a proof of this class'",
        "disposition": "resolved-scope-caveated",
        "w09_ids": ["W09-009"],
        "canonical_src": ["SRC-005", "SRC-006"],
        "exact_locator": "Thm 4.9; Thm 4.11 (Sbierski 2018, JDG 108(2) 319-378; DOI 10.4310/jdg/1518490820; arXiv:1507.00601)",
        "c0_or_c2": "C0: inextendible (maximal analytic Schwarzschild; obstruction through the r=0 singularity / interior).",
        "does_not_prove": "Not a class proof: Schwarzschild-specific, no dynamical or AF-generic data. Must not be imported "
                          "as a proof of AF-SCC-C0-VAC-GEN, whose literal form T-301 expects FALSE conditional on Kerr stability.",
        "falsifier": "A page check shows the numbered statements differ, or their scope is wider than the maximal analytic "
                     "Schwarzschild extension.",
    },
    {
        "slot": "af_scc_c0_vacuum.yaml:325 (worker-supplied pointer Dafermos-Luk arXiv:1710.01722)",
        "slot_text": "'the literal AF-SCC-C0-VAC-GEN class is expected FALSE conditional on Kerr exterior "
                     "stability ... L1 must adjudicate'",
        "disposition": "resolved-conditional",
        "w09_ids": ["W09-010"],
        "canonical_src": ["SRC-004"],
        "exact_locator": "Thm 4.24 (Dafermos-Luk, Ann. of Math. 202(2) 309-630 (2025); DOI 10.4007/annals.2025.202.2.1; arXiv:1710.01722v3)",
        "c0_or_c2": "C0: EXTENDIBLE across a non-trivial piece of the Cauchy horizon (smallness condition on interior data). "
                    "Refutes the C0 formulation conditional on Kerr exterior stability. No C2 statement.",
        "does_not_prove": "Does not prove C2-inextendibility (strictly stronger); does not give an unconditional theorem; the "
                          "data are posed inside the black-hole interior, not on an asymptotically flat Cauchy surface.",
        "falsifier": "Thm 4.24's hypotheses exclude the class (e.g. the smallness condition fails generically), or the "
                     "constructed extension is not C0 across CH+.",
    },
    {
        "slot": "af_scc_c2_vacuum.yaml:283 / af_scc_c0_vacuum.yaml:303 (T-305, Lipschitz near i+)",
        "slot_text": "citation_status: unresolved; 'preprint, conditional on a Price-law estimate'",
        "disposition": "partial-unresolved",
        "w09_ids": ["W09-019", "W09-020", "W09-021", "W09-016", "W09-017"],
        "canonical_src": ["SRC-083", "SRC-084", "SRC-085", "SRC-080", "SRC-081"],
        "exact_locator": "Linear inputs: spin +/-2 Teukolsky CH asymptotics (W09-019/W09-020/W09-021). Intermediate rung: "
                         "C^{0,1}_loc-inextendibility (W09-016 Thm 1.2; W09-017, accepted Invent. Math.).",
        "c0_or_c2": "C^{0,1}_loc sits strictly between C0 (extendible) and C2 (inextendible by inclusion). The shard does not "
                    "promote T-305's own conditional nonlinear Price-law rung.",
        "does_not_prove": "Does not prove C2 SCC; does not prove C0 SCC; the nonlinear Price-law estimate remains an assumption, "
                          "not a theorem, in the located sources.",
        "falsifier": "A verified source proves the nonlinear Price-law estimate, or constructs a Lipschitz extension of the Kerr "
                     "Cauchy horizon near i+.",
    },
    {
        "slot": "af_scc_c2_vacuum.yaml:282 (T-401, no peer-reviewed C2 theorem for generic AF vacuum data)",
        "slot_text": "l1_status: provisional; 'absence of evidence, not impossibility'",
        "disposition": "supported-as-open",
        "w09_ids": ["W09-016", "W09-017"],
        "canonical_src": ["SRC-080", "SRC-081"],
        "exact_locator": "Thm 1.2 (arXiv:2604.04877v1: characteristic IVP, C0-extendible, not Lipschitz); C^{0,1}_loc-inextendibility "
                         "from curvature blow-up (arXiv:2409.18838, accepted Invent. Math.).",
        "c0_or_c2": "C0 extendible; C2 inextendible by inclusion, at preprint/accepted-in-press level, for characteristic interior data.",
        "does_not_prove": "No full AF Cauchy-data C2 theorem. Whether characteristic interior data discharges AF-SCC-C2-VAC-GEN is an "
                          "F1 decision, not an L1 promotion.",
        "falsifier": "Peer review rejects arXiv:2604.04877, or a C2 (hence locally Lipschitz) extension of the weak null singularity is constructed.",
    },
    {
        "slot": "af_scc_c2_vacuum.yaml:243 (entailment E_C2 subset E_H2loc)",
        "slot_text": "status: standard_fact, citation_status: unresolved",
        "disposition": "resolved-standard-fact",
        "w09_ids": ["W09-016", "W09-017"],
        "canonical_src": ["SRC-080", "SRC-081"],
        "exact_locator": "Scope statements of W09-016/W09-017: a C1/C2 metric is locally Lipschitz, so C^{0,1}_loc-inextendibility "
                         "entails C2-inextendibility.",
        "c0_or_c2": "Entailment direction confirmed: E_C2 subset E_H2loc; non-Lipschitz-extendibility implies non-C2-extendibility.",
        "does_not_prove": "The entailment is one-way; H2_loc-inextendibility is strictly stronger than C2-inextendibility.",
        "falsifier": "Exhibit a C2 extension of a weak null singularity that is not locally Lipschitz.",
    },
    {
        "slot": "af_scc_c2_vacuum.yaml:141 / af_scc_c0_vacuum.yaml:142 (adm_mass positive mass theorem)",
        "slot_text": "citation_status: unresolved, locator 'to be supplied by L1' (Schoen-Yau / Witten)",
        "disposition": "unresolved",
        "w09_ids": [],
        "canonical_src": [],
        "exact_locator": "",
        "c0_or_c2": "Not a C0/C2 discriminator; used only to exclude negative-mass data from the ambient space.",
        "does_not_prove": "The SCC shard contains no Schoen-Yau/Witten row, so L1 cannot supply the locator from the verified set. "
                          "Kept unresolved deliberately rather than cited from memory.",
        "falsifier": "A verified ledger row for the positive mass theorem with an exact numbered locator appears.",
    },
    {
        "slot": "af_scc_c2_vacuum.yaml:163 / af_scc_c0_vacuum.yaml:165 (excluded_set: stationary/axisymmetric Kerr data admit a C-infinity extension)",
        "slot_text": "excluded_set_status: unresolved",
        "disposition": "unresolved-pointer-only",
        "w09_ids": ["W09-028"],
        "canonical_src": ["SRC-022"],
        "exact_locator": "W09-028 = Luk 2018 (JAMS; symmetry-free vacuum spacetimes with a null singular boundary). No numbered "
                         "locator for 'the Kerr MGHD admits a C-infinity extension' is carried by the shard.",
        "c0_or_c2": "Neither: the pointer bounds the excluded set, it does not decide C0 or C2.",
        "does_not_prove": "The classical C-infinity extendibility of the Kerr maximal development is not verified here; keep the slot "
                          "unresolved rather than citing by memory.",
        "falsifier": "A numbered theorem for the maximal analytic extension of Kerr is supplied and page-checked.",
    },
    {
        "slot": "af_scc_c0_vacuum.yaml:316-319 (concept identifiers)",
        "slot_text": "Choquet-Bruhat-Geroch MGHD; C0-inextendibility exact hypotheses; Kerr maximal analytic extension; H2_loc-inextendibility anti-scope",
        "disposition": "partial",
        "w09_ids": ["W09-009", "W09-016"],
        "canonical_src": ["SRC-005", "SRC-080"],
        "exact_locator": "C0-inextendibility exact hypotheses: W09-009 Thm 4.9/Thm 4.11. H2_loc/C0 anti-scope: W09-016 (non-Lipschitz "
                         "does not imply C0-inextendibility).",
        "c0_or_c2": "Two of four concept slots resolved at theorem level; Choquet-Bruhat-Geroch MGHD and the Kerr maximal analytic "
                    "extension remain unverified in the shard.",
        "does_not_prove": "Do not conflate C0-inextendibility with H2_loc-inextendibility; the latter is stronger and neither is "
                          "supplied for generic AF vacuum data.",
        "falsifier": "A numbered source for either remaining concept slot is supplied and page-checked.",
    },
]

# integrity checks
missing_w09 = sorted({w for e in ENTRIES for w in e["w09_ids"] if w not in shard_rows})
missing_src = sorted({s for e in ENTRIES for s in e["canonical_src"] if s not in canon_rows})
if missing_w09 or missing_src:
    raise SystemExit(f"reference check failed: missing_w09={missing_w09} missing_src={missing_src}")

payload = {
    "binding_id": "w09-scc-class-binding-20260912",
    "worker": "deepseek-flash-09",
    "node_id": "L1",
    "gate": "G-LIT",
    "assignment_id": "asg-2026-09-11-L1-deepseek-flash-09-18",
    "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "created_at": NOW,
    "schema_inputs": {
        "schemas/af_scc_c0_vacuum.yaml": sha(ROOT / "schemas" / "af_scc_c0_vacuum.yaml"),
        "schemas/af_scc_c2_vacuum.yaml": sha(ROOT / "schemas" / "af_scc_c2_vacuum.yaml"),
    },
    "ledger_inputs": {
        str(SHARD.relative_to(ROOT)): sha(SHARD),
        str(CANON.relative_to(ROOT)): sha(CANON),
        str(REV2.relative_to(ROOT)): sha(REV2),
    },
    "evidence_refs": [SHARD_REF, CANON_REF, REV2_REF],
    "summary": {
        "entries": len(ENTRIES),
        "resolved": sum(1 for e in ENTRIES if e["disposition"].startswith("resolved")),
        "partial": sum(1 for e in ENTRIES if e["disposition"].startswith("partial")),
        "unresolved": sum(1 for e in ENTRIES if e["disposition"].startswith("unresolved")),
        "c0_key_result": "T-301: C0 formulation refuted conditional on Kerr stability (Thm 4.24).",
        "c2_key_result": "T-526/T-527: C0-extendible but not Lipschitz => not C2, characteristic interior data, preprint/accepted-in-press.",
        "class_separation": "C0 and C2 remain separate rungs: C^{0,1}_loc sits strictly between them; no located source proves C2-inextendibility for generic AF vacuum Cauchy data (T-401 open).",
    },
    "entries": ENTRIES,
    "falsifier": "Any disposition marked resolved is shown to misquote the source's regularity class, or a resolved slot's locator "
                 "resolves to a different work.",
}
OUT.write_text(json.dumps(payload, indent=1) + "\n")
h = sha(OUT)
Path(str(OUT) + ".sha256").write_text(f"{h}  {OUT.name}\n")
print(json.dumps({"path": str(OUT.relative_to(ROOT)), "sha256": h, "bytes": OUT.stat().st_size,
                  "summary": payload["summary"]}, indent=1))
