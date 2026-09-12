#!/usr/bin/env python3
"""Class-bound conformance audit: AF-WCC-VAC-GEN literature bindings (worker flash-10, node L1).

Assignment: astra `asg-2026-09-11-L1-deepseek-flash-10-19` ("map each ledger source to the 4
classes; empty cells are the interesting output").  This is the WCC twin of
`c2_class_conformance_audit.py`: it resolves the AF-WCC-VAC-GEN cell at class-conclusion
strength, i.e. it asks whether any accepted ledger entry bound to the class actually discharges
the class's *declared* conclusion, or whether the 7 `covered` matrix cells are binding strength
only.

Method (mechanical, no NLP adjudication; every judgement is a documented field reading):
  1. Read the frozen class definition from the canonical F1 schema and hash it.
  2. Read every ledger entry whose `class_ids` contains AF-WCC-VAC-GEN.
  3. Score each entry against the class's three conjuncts:
       D1 data class : quantifier runs over generic (residual/comeagre) one-ended asymptotically
                       flat *vacuum* Cauchy data -- read from genericity/scope_caveats/assumptions.
       D2 conclusion : concludes complete future null infinity / no visible singularity, read
                       from the entry's own statement text; SCC-only (inextendibility) and
                       trapped-surface-formation-only statements do NOT count (the canonical
                       schema lists both as forbidden strengthenings / non-substitutes).
       D3 evidence   : accepted, no open hypothesis, evidence level peer-reviewed or
                       accepted-in-press.
  4. An entry discharges the class only if D1 and D2 and D3 all hold.
  5. Each bound entry is also given a *direction* (support / support_conditional / falsifier /
     formulation), because the coverage matrix's `covered` status is direction-agnostic: a
     counterexample bound to the class is `covered` at binding strength but is evidence
     *against* the class conclusion, not coverage of it.

Inputs are hashed; the output JSON is a deterministic function of them, apart from the audit id
and created_at.  Nothing here re-adjudicates L0 `class_ids` (A1's job), the F1 schema
(formulation lead's job), or the matrix's coverage rule (documented in README.md).
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLASS = "AF-WCC-VAC-GEN"
SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"
SCHEMA_AUTHORING = ROOT / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
MATRIX = ROOT / "ledger" / "class_coverage.csv"
SUMMARY = HERE / "coverage_summary.json"
MAP = ROOT / "research_map" / "research_map.json"
OUT = HERE / "wcc_class_conformance_audit.json"

TZ = timezone(timedelta(hours=8))
PEER_LEVELS = {"peer-reviewed", "accepted-in-press"}

# WCC conclusion predicate: complete I+ and/or no singularity visible from I+.  Deliberately does
# NOT match bare "future" or "trapped surface".
WCC_SIGNAL = re.compile(
    r"(complete future null infinity"
    r"|future null infinity[^.]{0,80}complete"
    r"|complete[^.]{0,60}I\+"
    r"|I\+[^.]{0,80}complete"
    r"|no (naked )?singularity[^.]{0,40}visible"
    r"|visible (naked )?singularity"
    r"|future asymptotic predictability)",
    re.I,
)
SCC_ONLY = re.compile(r"\b(inextendib|extension of the maximal development)\b", re.I)
D1_WRONG_CLASS = (
    "not generic", "special", "short-pulse", "perturbative", "codimension",
    "symmetry", "polarized", "self-similar", "restricted", "not an open set of general",
    "existence of a special",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    doc = yaml.safe_load(SCHEMA.read_text(encoding="utf-8", errors="replace"))
    concl = doc.get("conclusion") or {}
    gen_block = doc.get("genericity") or {}
    quant = (doc.get("quantifiers") or {}).get("formal", "")
    if isinstance(gen_block, dict):
        gen_kind = gen_block.get("kind") or gen_block.get("genericity_kind") or ""
        gen_topo = gen_block.get("topology") or gen_block.get("topology_id") or ""
        gen_def = gen_block.get("definition") or ""
    else:  # prose layout fallback
        gen_kind, gen_topo, gen_def = str(gen_block), "", ""

    class_def = {
        "path": str(SCHEMA.relative_to(ROOT)),
        "sha256": sha256(SCHEMA),
        "class_id": doc.get("class_id"),
        "node_id": doc.get("node_id"),
        "revision": doc.get("revision"),
        "epistemic_status": doc.get("epistemic_status"),
        "scope_statement": (doc.get("scope_statement") or "").strip(),
        "conclusion_type": concl.get("conclusion_type"),
        "conclusion_statement": concl.get("statement_natural_language"),
        "conclusion_statement_formal": concl.get("statement_formal"),
        "conclusion_epistemic_status": concl.get("epistemic_status"),
        "forbidden_strengthenings": concl.get("forbidden_strengthenings") or [],
        "claim_promotion": concl.get("claim_promotion"),
        "quantifier_formal": quant,
        "genericity_kind": gen_kind,
        "genericity_topology": gen_topo,
        "genericity_definition": (gen_def or "").strip()[:400],
    }
    if SCHEMA_AUTHORING.exists():
        a_hash = sha256(SCHEMA_AUTHORING)
        class_def["authoring_tree_observation"] = (
            "no divergence at read time: canonical and authoring copies share sha256 " + a_hash
            if a_hash == class_def["sha256"]
            else {"path": str(SCHEMA_AUTHORING.relative_to(ROOT)), "sha256": a_hash,
                  "note": "dual-tree copy differs at read time; recorded for the formulation lead / A1, not adjudicated by L1"}
        )

    entries = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    bound = [e for e in entries if CLASS in (e.get("class_ids") or [])]

    def role_of(e: dict) -> str:
        ct, ek = e.get("conclusion_type"), e.get("entry_kind")
        if ct == "counterexample":
            return "falsifier"
        if ct == "open_problem" or ek in {"definition", "literature_status", "conjecture"}:
            return "formulation"
        if ct in {"conditional_theorem", "stability_result", "numerical_evidence"}:
            return "support_conditional"
        if ct == "theorem":
            return "support"
        return "other"

    bindings = []
    for e in sorted(bound, key=lambda x: x.get("theorem_id", "")):
        gen = (e.get("genericity") or "").lower()
        caveats = " ".join(e.get("scope_caveats") or []).lower()
        assumptions = " ".join(e.get("assumptions") or []).lower()
        stmt = ((e.get("statement_exact") or "") + " " + " ".join(e.get("assumptions") or [])).lower()
        unresolved = e.get("unresolved") or []

        # D1: frozen data class = residual/comeagre generic, vacuum, one-ended, asymptotically flat.
        d1_residual = any(k in gen for k in ("residual", "comeagre", "comeager"))
        d1_vacuum = "vacuum" in (gen + " " + assumptions)
        d1_wrong = any(k in gen + " " + caveats for k in D1_WRONG_CLASS)
        d1 = bool(d1_residual and d1_vacuum and not d1_wrong)

        # D2: WCC conclusion predicate (not SCC inextendibility, not trapped-surface formation only).
        d2_type = e.get("conclusion_type") in {"theorem", "conditional_theorem", "stability_result"}
        d2_signal = bool(WCC_SIGNAL.search(stmt))
        d2_scc_only = bool(SCC_ONLY.search(stmt))
        d2_trapped_only = any(k in caveats for k in ("not by itself", "precursor", "no claim about exterior completeness"))
        d2 = bool(d2_type and d2_signal and not d2_scc_only and not d2_trapped_only)

        # D3: accepted, no open hypothesis, peer-reviewed / accepted-in-press.
        d3 = bool(
            e.get("status") == "accepted"
            and e.get("evidence_level") in PEER_LEVELS
            and not unresolved
            and not any("preprint" in c.lower() for c in (e.get("scope_caveats") or []))
        )

        reasons = []
        if not d1:
            reasons.append(
                "D1: genericity is not residual/comeagre AF vacuum"
                + (" (residual token absent)" if not d1_residual else "")
                + (" (no vacuum token)" if not d1_vacuum else "")
                + (" (special/non-generic scope: " + ", ".join(k for k in D1_WRONG_CLASS if k in gen + " " + caveats)[:80] + ")" if d1_wrong else "")
            )
        if not d2:
            reasons.append(
                "D2: "
                + ("counterexample-direction entry (role=falsifier): evidence against the class conclusion, cannot discharge it"
                   if role_of(e) == "falsifier" else
                   "no WCC conclusion predicate located in statement"
                   if not d2_signal else
                   "conclusion is SCC-side (inextendibility), a schema-listed forbidden strengthening for WCC"
                   if d2_scc_only else
                   "trapped-surface formation only, not I+ completeness"
                   if d2_trapped_only else
                   "conclusion_type is not a theorem-strength class conclusion")
            )
        if not d3:
            reasons.append(
                "D3: "
                + ("status != accepted" if e.get("status") != "accepted" else
                   "open items present (n=" + str(len(unresolved)) + ")" if unresolved else
                   "evidence level " + str(e.get("evidence_level")))
            )

        bindings.append({
            "theorem_id": e.get("theorem_id"),
            "label": e.get("label"),
            "entry_kind": e.get("entry_kind"),
            "conclusion_type": e.get("conclusion_type"),
            "status": e.get("status"),
            "verification_status": e.get("verification_status"),
            "evidence_level": e.get("evidence_level"),
            "role": role_of(e),
            "genericity": e.get("genericity"),
            "scope_caveats": e.get("scope_caveats") or [],
            "n_open_items": len(unresolved),
            "checks": {"D1_data_class": d1, "D2_conclusion": d2, "D3_evidence": d3},
            "discharges_class": bool(d1 and d2 and d3),
            "failing_conjuncts": [n for n, ok in (("D1_data_class", d1), ("D2_conclusion", d2), ("D3_evidence", d3)) if not ok],
            "failing_reasons": reasons,
            "source_ids": e.get("source_ids") or [],
            "evidence_ref": f"ledger/theorems.jsonl#{sha256(LEDGER)[:12]}:{e.get('theorem_id')}",
        })

    discharging = [b["theorem_id"] for b in bindings if b["discharges_class"]]
    role_counts: dict[str, int] = {}
    for b in bindings:
        role_counts[b["role"]] = role_counts.get(b["role"], 0) + 1

    # Matrix crosswalk: the class's `covered` cells, annotated by entry direction.
    by_source: dict[str, list[dict]] = {}
    for b in bindings:
        for sid in b["source_ids"]:
            by_source.setdefault(sid, []).append(b)
    covered_cells = []
    with MATRIX.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["class_id"] != CLASS or row["coverage"] != "covered":
                continue
            sid = row["source_id"]
            bound_here = by_source.get(sid, [])
            roles = sorted({b["role"] for b in bound_here})
            direction = (
                "support-side" if any(r in {"support", "support_conditional"} for r in roles)
                else "falsifier-side" if roles and all(r == "falsifier" for r in roles)
                else "formulation-side"
            )
            covered_cells.append({
                "source_id": sid,
                "theorem_ids": [t for t in row["theorem_ids"].split(" | ") if t],
                "roles": roles,
                "direction": direction,
                "any_entry_discharges_class": any(b["discharges_class"] for b in bound_here),
                "binding_only": not any(b["discharges_class"] for b in bound_here),
            })
    direction_mismatch = [c["source_id"] for c in covered_cells if c["direction"] == "falsifier-side"]

    created_at = datetime.now(TZ)
    out = {
        "audit_id": "flash-10-wcc-class-conformance-" + created_at.strftime("%Y%m%dT%H%M%S"),
        "node_id": "L1",
        "class_id": CLASS,
        "actor": "deepseek-flash-10",
        "created_at": created_at.isoformat(timespec="seconds"),
        "assignment_ref": "asg-2026-09-11-L1-deepseek-flash-10-19",
        "gate": "G-LIT",
        "class_definition": class_def,
        "requirement_conjuncts": {
            "D1_data_class": "generic (residual/comeagre) one-ended asymptotically flat vacuum Cauchy data in the declared regularity class (schema genericity: " + str(gen_kind) + "; topology: " + str(gen_topo) + ")",
            "D2_conclusion": "maximal development has complete future null infinity I+ and no future-incomplete causal geodesic visible from I+ (schema conclusion_type=" + str(concl.get("conclusion_type")) + ")",
            "D3_evidence": "accepted entry, no open hypothesis, evidence level peer-reviewed or accepted-in-press",
        },
        "bindings": bindings,
        "summary": {
            "n_bound_entries": len(bindings),
            "role_counts": role_counts,
            "n_discharging": len(discharging),
            "discharging_entries": discharging,
            "class_conclusion_state": "open_problem" if not discharging else "discharged",
            "matrix_crosswalk": {
                "canonical_matrix": str(MATRIX.relative_to(ROOT)),
                "matrix_sha256": sha256(MATRIX),
                "covered_cells": covered_cells,
                "direction_mismatch_cells": direction_mismatch,
                "reading": (
                    "covered = theorem/counterexample-strength binding only (direction-agnostic rule in README.md). "
                    "None of the bound entries discharges D1+D2+D3, so every covered cell is a binding, not a class "
                    "conclusion. Cells whose only accepted bindings are counterexample-direction (direction_mismatch_cells) "
                    "are scope-inversion candidates for A1: a non-generic naked-singularity construction is evidence against "
                    "WCC, not coverage of it, unless the class quantifier is first changed."
                ),
            },
        },
        "inputs": {
            "ledger/theorems.jsonl": {"sha256": sha256(LEDGER), "entries": len(entries), "bound_entries": len(bindings)},
            "schemas/af_wcc_vacuum.yaml": {"sha256": sha256(SCHEMA)},
            "ledger/class_coverage.csv": {"sha256": sha256(MATRIX)},
            "artifacts/flash-10/l1_class_coverage/coverage_summary.json": {"sha256": sha256(SUMMARY)},
        },
        "map_state_observation": _map_observation(),
        "falsifier": (
            "Produce one accepted ledger entry bound to AF-WCC-VAC-GEN that (i) quantifies over generic "
            "(residual/comeagre) one-ended asymptotically flat vacuum Cauchy data, (ii) concludes complete "
            "future null infinity or no singularity visible from I+ (not SCC inextendibility, not trapped-surface "
            "formation alone), and (iii) is peer-reviewed or accepted-in-press with no open hypothesis. Then "
            "n_discharging >= 1 and the class conclusion state is 'discharged'."
        ),
        "limitations": [
            "The audit inherits L0 class_ids; it does not re-adjudicate them (A1's job).",
            "D1/D2/D3 are mechanical readings of the entries' genericity/scope_caveats/unresolved/entry_kind/evidence_level and statement text; a human reviewer may bind an entry differently, which is exactly the A1 verdict this artifact asks for.",
            "The matrix and this audit are snapshots; ledger/schema drift is reported in the input hashes.",
            "The class schema was under active revision during this run (rev9, revised_at 2026-09-12T00:15:00+08:00 is ahead of wall clock); the measured hash is recorded and any later revision voids this verdict for the new hash.",
        ],
        "validation_status": "unverified",
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} | bound={len(bindings)} discharging={len(discharging)}")
    for b in bindings:
        print(f"  {b['theorem_id']:6s} {b['role']:18s} {b['conclusion_type']:18s} {b['evidence_level']:16s} -> fails {b['failing_conjuncts']}")
    print("covered cells:", [(c["source_id"], c["direction"]) for c in covered_cells])
    print("sha256:", sha256(OUT))
    return 0


def _map_observation() -> dict:
    """Record the map's measured F1 hash at read time (drift observation only, not adjudicated)."""
    if not MAP.exists():
        return {}
    md = json.loads(MAP.read_text(encoding="utf-8"))
    obs = {"map_updated_at": md.get("updated_at"), "measured_schema_sha256": sha256(SCHEMA)}
    for g in md.get("gates", []):
        if g.get("gate_id") == "G-FORM":
            obs["gate_text"] = (g.get("unmet") or g.get("criteria"))[:300]
    return obs


if __name__ == "__main__":
    raise SystemExit(main())
