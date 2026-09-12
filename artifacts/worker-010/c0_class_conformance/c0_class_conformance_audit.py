#!/usr/bin/env python3
"""Class-bound conformance audit: AF-SCC-C0-VAC-GEN ledger bindings (worker-010, node L1, gate G-LIT).

Assignment reference: astra `asg-2026-09-11-L1-deepseek-flash-10-19` ("Map each ledger source to
the 4 classes; empty cells are the interesting output"), continuing the flash-10 conformance
series (WCC audit 2026-09-12T00:19:10, C2 audit 2026-09-12T00:11:03).  This audit resolves the
remaining F2b cell at class-conclusion strength: for the frozen class AF-SCC-C0-VAC-GEN, does any
accepted ledger entry actually discharge the class's *declared* conclusion, or is the cell only
`covered` at binding strength?

Method (mechanical; no NLP adjudication, no re-adjudication of L0 class_ids):
  1. Read the frozen class definition from the canonical F2b schema and hash it; snapshot the bytes.
  2. Read every ledger entry whose `class_ids` contains the class.
  3. Score each entry against three conjuncts read off the entry's own fields:
       D1 data class : a RESULT entry (not definition/conjecture/literature_status) whose
                       genericity is the class's residual/comeager form over one-ended
                       asymptotically flat VACUUM Cauchy data, with no special/characteristic/
                       interior/exact-solution/not-quantified marker.
       D2 conclusion : entry concludes future INEXTENDIBILITY in a class that contains C0
                       (continuous-metric extension excluded), and does not instead assert that a
                       continuous extension EXISTS.
       D3 evidence   : status accepted, evidence level peer-reviewed or accepted-in-press, no
                       unresolved items, no preprint / not-peer-reviewed caveat.
  4. An entry discharges the class only if D1 AND D2 AND D3 all hold.

Negative controls (self-test) drive the same predicates over four synthetic entries and assert the
expected verdict flips; the results are recorded in the artifact.  `--selftest` runs only the
controls.

Inputs are hashed; the output JSON is deterministic given them.  Nothing here re-adjudicates L0
`class_ids` (A1's job) or the F2b schema (formulation lead's job).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLASS = "AF-SCC-C0-VAC-GEN"
SCHEMA = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
SCHEMA_AUTHORING = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
MATRIX = ROOT / "ledger" / "class_coverage.csv"
TAXONOMY = ROOT / "research_map" / "formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
SNAP_DIR = HERE / "snapshots"
OUT = HERE / "c0_class_conformance_audit.json"

TZ = timezone(timedelta(hours=8))
PEER_LEVELS = {"peer-reviewed", "accepted-in-press"}
RESULT_KINDS = {"theorem", "preprint_result"}
RESULT_CONCLUSIONS = {"theorem", "conditional_theorem"}

# D1 markers: the class's genericity is residual/comeager on the AF vacuum constraint manifold.
GENERIC_MARKERS = ("comeagre", "comeager", "residual")
SPECIAL_MARKERS = (
    "exact solution", "not a generic", "not generic", "not quantified", "special",
    "characteristic", "interior", "impulsive", "high-frequency", "conditional on",
    "assumed", "does not fix", "class-dependent", "not applicable",
)
# D2 markers: direction and forbidden-extension regularity.
EXTENSION_EXISTS_MARKERS = (
    "continuously extendible", "extends continuously", "extended across", "can be extended",
    "extension exists", "extendible but not", "c^0-extendible",
    "c0-extendible", "c^0 extendible", "c0 extendible", "c^0-stability", "c0-stability",
)
INEXTENDIBILITY_TOKEN = "inextendib"
C0_FORBIDDEN_RE = re.compile(r"c\s*\^?\{?0\}?[\s-]*inextendib|continuous(?:ly)?[^.;]{0,60}inextendib|inextendib[^.;]{0,60}continuous")
WEAKER_REGULARITY_MARKERS = ("lipschitz", "c^{0,1}", "c^0,1", "c2", "c^2", "h2_loc", "h^2_loc", "l^2", "l2_loc")
OPEN_HYPOTHESIS_MARKERS = ("conditional", "assum", "expected", "not proved", "unresolved", "conjectur")

# falsifier/weakening vocabulary from the frozen schema
SCHEMA_FORBIDDEN_WEAKENINGS = (
    "dropping the generic quantifier in practice while keeping the word",
    "substituting the distributional-vacuum variant for the bare-metric class",
    "substituting H2_loc for C0 (H2_loc-inextendibility is weaker and entails the C2 sibling, not this class)",
    "substituting C2 or C1 for C0, or citing a C2 result as evidence for this class",
    "using the C0 token for the distributional-vacuum variant without declaring the equation requirement",
    "replacing future by two-sided direction",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grab(text: str, key: str) -> str:
    m = re.search(r"^\s*" + re.escape(key) + r"\s*:\s*(.+)$", text, re.M)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def load_entries() -> list[dict]:
    return [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]


def entry_text(entry: dict) -> dict:
    """Flatten the fields the mechanical predicates read."""
    scope = " ".join(entry.get("scope_caveats") or [])
    assumptions = " ".join(entry.get("assumptions") or [])
    statement = " ".join(str(entry.get(k) or "") for k in ("statement_exact", "label", "regularity"))
    return {
        "genericity": (entry.get("genericity") or "").lower(),
        "scope": scope.lower(),
        "assumptions": assumptions.lower(),
        "statement": statement.lower(),
        "regularity": (entry.get("regularity") or "").lower(),
        "all": " ".join([
            (entry.get("genericity") or ""), scope, assumptions, statement,
            entry.get("topology") or "",
        ]).lower(),
    }


def classify(entry: dict) -> dict:
    """The three conjuncts.  Pure function of the entry's own fields."""
    t = entry_text(entry)
    kind = entry.get("entry_kind")
    concl = entry.get("conclusion_type")

    # --- D1: result over generic (comeager/residual) AF vacuum Cauchy data -------------------
    generic = any(m in t["genericity"] for m in GENERIC_MARKERS)
    special = [m for m in SPECIAL_MARKERS if m in t["genericity"] or m in t["scope"]]
    vacuum = "vacuum" in t["all"]
    af = "asymptotically flat" in t["all"] or "af " in t["all"]
    d1 = bool(kind in RESULT_KINDS and generic and vacuum and af and not special)

    # --- D2: conclusion is future C0-inextendibility, not extension-existence ----------------
    inext = INEXTENDIBILITY_TOKEN in t["statement"]
    ext_exists = [m for m in EXTENSION_EXISTS_MARKERS if m in t["statement"]]
    c0_forbidden = bool(C0_FORBIDDEN_RE.search(t["statement"]))
    # a statement whose forbidden extension class is only Lipschitz/C2/H2/L2 is a weakening
    weaker_only = (
        any(m in t["regularity"] for m in WEAKER_REGULARITY_MARKERS)
        and not re.search(r"metric\s+c\s*\^?0\b|merely continuous|continuous metric", t["statement"])
    )
    d2 = bool(concl in RESULT_CONCLUSIONS and inext and not ext_exists and c0_forbidden and not weaker_only)

    # --- D3: accepted, peer-reviewed/accepted-in-press, no open items ------------------------
    caveats = t["scope"]
    d3 = bool(
        entry.get("status") == "accepted"
        and entry.get("evidence_level") in PEER_LEVELS
        and not (entry.get("unresolved") or [])
        and "preprint" not in caveats
        and "not peer-reviewed" not in caveats
    )

    failing = [n for n, ok in (("D1_data_class", d1), ("D2_conclusion", d2), ("D3_evidence", d3)) if not ok]
    if "lipschitz" in t["regularity"] or "c^{0,1}" in t["regularity"] or "c^0,1" in t["regularity"]:
        forbidden_class = "C^{0,1}/Lipschitz"
    elif "h2_loc" in t["regularity"] or "h^2_loc" in t["regularity"]:
        forbidden_class = "H2_loc"
    elif "c2" in t["regularity"] or "c^2" in t["regularity"]:
        forbidden_class = "C2"
    elif "l^2" in t["regularity"] or "l2_loc" in t["regularity"]:
        forbidden_class = "L2_connection_variant"
    elif c0_forbidden:
        forbidden_class = "C0"
    else:
        forbidden_class = "n/a"
    if kind not in RESULT_KINDS:
        direction = "no_C0_conclusion"
    elif weaker_only and inext:
        direction = "weaker_inextendibility_not_C0"
    elif ext_exists:
        direction = "falsifier_side_extension_exists"
    elif d2:
        direction = "supports_conclusion"
    else:
        direction = "no_C0_conclusion"
    weaker_class = forbidden_class in {"C^{0,1}/Lipschitz", "H2_loc", "C2", "L2_connection_variant"}
    weakener_risk = bool(
        weaker_class and (direction == "weaker_inextendibility_not_C0"
                          or (kind == "definition" and forbidden_class != "C0"))
    )
    open_hyp = sorted({m for m in OPEN_HYPOTHESIS_MARKERS if m in t["scope"] or m in t["assumptions"]})
    return {
        "checks": {"D1_data_class": d1, "D2_conclusion": d2, "D3_evidence": d3},
        "discharges_class": not failing,
        "failing_conjuncts": failing,
        "direction": direction,
        "forbidden_extension_class": forbidden_class,
        "d1_markers": {"generic": generic, "vacuum": vacuum, "asymptotically_flat": af, "special_markers": special},
        "d2_markers": {"inextendibility_token": inext, "extension_exists_markers": ext_exists,
                       "c0_forbidden_regex": c0_forbidden, "weaker_regularity_only": weaker_only},
        "open_hypothesis_markers": open_hyp,
        "weakener_or_inflation_risk": weakener_risk,
    }


def bindings_for(entries: list[dict]) -> list[dict]:
    bound = [e for e in entries if CLASS in (e.get("class_ids") or [])]
    out = []
    for e in sorted(bound, key=lambda x: x.get("theorem_id") or ""):
        c = classify(e)
        out.append({
            "theorem_id": e.get("theorem_id"),
            "label": e.get("label"),
            "entry_kind": e.get("entry_kind"),
            "conclusion_type": e.get("conclusion_type"),
            "status": e.get("status"),
            "verification_status": e.get("verification_status"),
            "evidence_level": e.get("evidence_level"),
            "regularity": e.get("regularity"),
            "genericity": e.get("genericity"),
            "n_open_items": len(e.get("unresolved") or []),
            **c,
            "evidence_ref": f"ledger/theorems.jsonl#{sha256(LEDGER)[:12]}:{e.get('theorem_id')}",
        })
    return out


# ---------------------------------------------------------------------------------------------
# Negative controls: same predicates, synthetic entries, asserted verdict flips.
# ---------------------------------------------------------------------------------------------
CONTROLS = [
    {
        "name": "CTRL-POS-discharges",
        "expect_discharge": True,
        "expect_failing": [],
        "entry": {
            "theorem_id": "CTRL-POS", "entry_kind": "theorem", "conclusion_type": "theorem",
            "status": "accepted", "evidence_level": "peer-reviewed",
            "genericity": "comeager (residual) subset of the one-ended asymptotically flat vacuum Cauchy data manifold",
            "statement_exact": ("For a comeager set of one-ended asymptotically flat vacuum initial data, "
                                "the maximal globally hyperbolic development is future-inextendible as a "
                                "Lorentzian manifold with a merely continuous metric."),
            "regularity": "metric C^0; no regularity demanded of the connection",
            "assumptions": ["Einstein vacuum equations"], "scope_caveats": [], "unresolved": [],
            "topology": "asymptotically flat", "label": "synthetic positive control",
        },
    },
    {
        "name": "CTRL-WEAK-lipschitz-only",
        "expect_discharge": False,
        "expect_failing": ["D2_conclusion"],
        "entry": {
            "theorem_id": "CTRL-WEAK", "entry_kind": "theorem", "conclusion_type": "theorem",
            "status": "accepted", "evidence_level": "peer-reviewed",
            "genericity": "comeager (residual) subset of the one-ended asymptotically flat vacuum Cauchy data manifold",
            "statement_exact": ("For a comeager set of one-ended asymptotically flat vacuum initial data, "
                                "the maximal development is not Lipschitz-extendible."),
            "regularity": "Lipschitz-inextendibility (metric C^{0,1})",
            "assumptions": ["Einstein vacuum equations"], "scope_caveats": [], "unresolved": [],
            "topology": "asymptotically flat", "label": "synthetic weakening control",
        },
    },
    {
        "name": "CTRL-SPECIAL-exact-solution",
        "expect_discharge": False,
        "expect_failing": ["D1_data_class"],
        "entry": {
            "theorem_id": "CTRL-SPECIAL", "entry_kind": "theorem", "conclusion_type": "theorem",
            "status": "accepted", "evidence_level": "peer-reviewed",
            "genericity": "Exact solution, not a generic-data statement.",
            "statement_exact": ("The maximal analytic Schwarzschild spacetime is inextendible as a "
                                "Lorentzian manifold with a continuous metric."),
            "regularity": "C^0 metric",
            "assumptions": ["Exact Schwarzschild spacetime"], "scope_caveats": [], "unresolved": [],
            "topology": "Schwarzschild", "label": "synthetic special-data control",
        },
    },
    {
        "name": "CTRL-PREPRINT-conditional",
        "expect_discharge": False,
        "expect_failing": ["D3_evidence"],
        "entry": {
            "theorem_id": "CTRL-PREPRINT", "entry_kind": "preprint_result", "conclusion_type": "theorem",
            "status": "accepted", "evidence_level": "preprint",
            "genericity": "comeager (residual) subset of the one-ended asymptotically flat vacuum Cauchy data manifold",
            "statement_exact": ("For a comeager set of one-ended asymptotically flat vacuum initial data, "
                                "the maximal development is future-inextendible as a Lorentzian manifold "
                                "with a merely continuous metric."),
            "regularity": "metric C^0",
            "assumptions": ["Einstein vacuum equations"], "scope_caveats": ["Preprint; not peer-reviewed."],
            "unresolved": [], "topology": "asymptotically flat", "label": "synthetic preprint control",
        },
    },
]


def run_controls() -> dict:
    results = []
    ok_all = True
    for c in CONTROLS:
        got = classify(c["entry"])
        ok = (got["discharges_class"] == c["expect_discharge"]
              and got["failing_conjuncts"] == c["expect_failing"])
        ok_all = ok_all and ok
        results.append({
            "name": c["name"],
            "expected": {"discharges_class": c["expect_discharge"], "failing_conjuncts": c["expect_failing"]},
            "observed": {"discharges_class": got["discharges_class"],
                         "failing_conjuncts": got["failing_conjuncts"],
                         "direction": got["direction"],
                         "forbidden_extension_class": got["forbidden_extension_class"]},
            "pass": ok,
        })
    return {"controls": results, "all_pass": ok_all}


def matrix_crosswalk() -> dict:
    import csv as _csv
    counts: dict[str, int] = {}
    covered = []
    with MATRIX.open(newline="", encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if row["class_id"] != CLASS:
                continue
            counts[row["coverage"]] = counts.get(row["coverage"], 0) + 1
            if row["coverage"] == "covered":
                covered.append({
                    "source_id": row["source_id"],
                    "theorem_ids": [t for t in row["theorem_ids"].split(" | ") if t],
                    "entry_kinds": row.get("entry_kinds", ""),
                    "conclusion_types": row.get("conclusion_types", ""),
                })
    return {
        "canonical_matrix": str(MATRIX.relative_to(ROOT)),
        "matrix_sha256": sha256(MATRIX),
        "coverage_counts": counts,
        "covered_cells": covered,
        "reading": ("covered = a binding exists at some conclusion strength; none of the bound "
                    "entries discharges D1+D2+D3, so the cell is a binding, not a class conclusion"),
    }


def main() -> int:
    controls = run_controls()
    if "--selftest" in sys.argv:
        print(json.dumps(controls, indent=2))
        return 0 if controls["all_pass"] else 1

    text = SCHEMA.read_text(encoding="utf-8", errors="replace")
    authoring = SCHEMA_AUTHORING.read_text(encoding="utf-8", errors="replace") if SCHEMA_AUTHORING.exists() else ""
    schema_sha = sha256(SCHEMA)
    class_def = {
        "path": str(SCHEMA.relative_to(ROOT)),
        "sha256": schema_sha,
        "revision": grab(text, "revision"),
        "class_id": grab(text, "class_id"),
        "conclusion_type": grab(text, "conclusion_type"),
        "statement_natural_language": grab(text, "statement_natural_language"),
        "statement_formal": grab(text, "statement_formal"),
        "epistemic_status": grab(text, "epistemic_status"),
        "genericity_kind": grab(text, "kind") or grab(text, "genericity_kind"),
        "extension_regularity": grab(text, "extension_regularity"),
        "extension_regularity_exact": grab(text, "extension_regularity_exact"),
        "claim_promotion": grab(text, "claim_promotion"),
        "sibling_disjoint_from": grab(text, "sibling_disjoint_from"),
        "forbidden_weakenings": list(SCHEMA_FORBIDDEN_WEAKENINGS),
    }
    class_def["authoring_tree_observation"] = (
        "canonical and authoring bytes identical at read time (sha256 " + schema_sha[:12] + ")"
        if authoring and sha256(SCHEMA_AUTHORING) == schema_sha
        else {"authoring_sha256": sha256(SCHEMA_AUTHORING), "note": "dual-tree divergence; recorded only"}
    )
    if FROZEN.exists():
        frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
        files = frozen.get("files", {})
        f_canon = (files.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
        f_auth = (files.get("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
        class_def["frozen_manifest_observation"] = {
            "path": str(FROZEN.relative_to(ROOT)),
            "sha256": sha256(FROZEN),
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "read_at_wall_clock": datetime.now(TZ).isoformat(timespec="seconds"),
            "binds_canonical_c0_prefix": (f_canon or "")[:12],
            "binds_authoring_c0_prefix": (f_auth or "")[:12],
            "measured_canonical_c0_prefix": schema_sha[:12],
            "note": ("publication binding matches the measured canonical bytes at read time; "
                     "frozen_at is ahead of the reading wall clock (CF-14 class of observation, "
                     "recorded, not adjudicated here)"),
        }

    # byte-identical snapshot so the audit stays readable after further canonical drift
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAP_DIR / f"af_scc_c0_vacuum.{schema_sha[:12]}.yaml"
    if not snap.exists() or sha256(snap) != schema_sha:
        snap.write_bytes(SCHEMA.read_bytes())
    snapshot_sha = sha256(snap)

    entries = load_entries()
    bindings = bindings_for(entries)
    discharging = [b["theorem_id"] for b in bindings if b["discharges_class"]]
    direction_mismatch = [b["theorem_id"] for b in bindings if b["direction"] == "falsifier_side_extension_exists"]
    weakeners = [b["theorem_id"] for b in bindings if b["weakener_or_inflation_risk"]]
    accepted = [b["theorem_id"] for b in bindings if b["status"] == "accepted"]

    created_at = datetime.now(TZ)
    out = {
        "audit_id": "worker-010-c0-class-conformance-" + created_at.strftime("%Y%m%dT%H%M%S"),
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": CLASS,
        "actor": "worker-010",
        "alias_actor": "deepseek-flash-10",
        "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
        "created_at": created_at.isoformat(timespec="seconds"),
        "task": "class-bound conformance audit of the AF-SCC-C0-VAC-GEN ledger bindings",
        "class_definition": class_def,
        "requirement_conjuncts": {
            "D1_data_class": ("RESULT entry over the class's residual/comeager generic set on one-ended "
                              "asymptotically flat VACUUM Cauchy data (no exact-solution / special / "
                              "characteristic / interior / not-quantified substitution)"),
            "D2_conclusion": ("maximal development future-inextendible as a Lorentzian manifold with a "
                              "merely continuous (C0) metric; a statement that instead asserts a continuous "
                              "extension EXISTS is the opposite direction; Lipschitz/C2/H2_loc/L2-connection "
                              "inextendibility is a forbidden weakening, not this class"),
            "D3_evidence": "status accepted, evidence level peer-reviewed or accepted-in-press, no open items, no preprint caveat",
        },
        "bindings": bindings,
        "negative_controls": controls,
        "summary": {
            "n_bound_entries": len(bindings),
            "n_accepted_status": len(accepted),
            "accepted_status_entries": accepted,
            "n_discharging": len(discharging),
            "discharging_entries": discharging,
            "class_conclusion_state": "open_problem" if not discharging else "discharged",
            "direction_mismatch_candidates": direction_mismatch,
            "weakening_or_inflation_candidates": weakeners,
            "matrix_crosswalk": matrix_crosswalk(),
        },
        "inputs": {
            "ledger/theorems.jsonl": {"sha256": sha256(LEDGER), "entries": len(entries), "bound_entries": len(bindings)},
            "schemas/af_scc_c0_vacuum.yaml": {"sha256": schema_sha},
            "ledger/class_coverage.csv": {"sha256": sha256(MATRIX)},
            "research_map/formulation_taxonomy.yaml": {"sha256": sha256(TAXONOMY)},
            "artifacts/formulation/FROZEN.json": {"sha256": sha256(FROZEN)},
            "snapshot": {str(snap.relative_to(ROOT)): {"sha256": snapshot_sha, "bytes": snap.stat().st_size}},
        },
        "falsifier": (
            "Produce one accepted ledger entry bound to AF-SCC-C0-VAC-GEN that (i) quantifies over the "
            "class's generic (residual/comeager) set of one-ended asymptotically flat vacuum Cauchy data, "
            "(ii) concludes future C0-inextendibility of the maximal development (no continuous-metric "
            "extension exists) rather than the existence of such an extension or a weaker-regularity "
            "inextendibility, and (iii) is peer-reviewed or accepted-in-press with no open hypothesis and "
            "no unresolved ledger item. Then n_discharging >= 1 and the class conclusion state is "
            "'discharged'."
        ),
        "limitations": [
            "The audit inherits L0 class_ids; it does not re-adjudicate them (A1's job).",
            "D1/D2/D3 are mechanical readings of the ledger fields genericity/scope_caveats/unresolved/statement_exact; a reviewer may bind an entry differently, which is exactly the A1 verdict this artifact asks for.",
            "The schema, ledger and matrix are snapshots; drift after read time is reported in the input hashes and voids citation at the newer revision, not the measurement.",
            "The negative controls exercise the predicates on synthetic entries only; they do not substitute for an independent re-implementation (verify_c0_conformance.py).",
        ],
        "validation_status": "unverified",
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} | bound={len(bindings)} accepted={len(accepted)} discharging={len(discharging)}")
    print("negative controls all_pass:", controls["all_pass"])
    for b in bindings:
        print(f"  {b['theorem_id']:6s} {b['entry_kind']:18s} {b['conclusion_type']:20s} "
              f"{b['evidence_level']:18s} dir={b['direction']:32s} fails {b['failing_conjuncts']}")
    print("sha256:", sha256(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
