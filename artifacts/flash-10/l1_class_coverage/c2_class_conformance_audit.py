#!/usr/bin/env python3
"""Class-bound conformance audit: AF-SCC-C2-VAC-GEN literature bindings (worker flash-10, node L1).

Assignment: astra `asg-2026-09-11-L1-deepseek-flash-10-19` ("map each ledger source to the 4
classes; empty cells are the interesting output").  This audit resolves one of those cells at
class-conclusion strength: it asks, for the frozen class AF-SCC-C2-VAC-GEN, whether any accepted
ledger entry actually discharges the class's *declared* conclusion, or whether the cell is only
`covered` at binding strength.

Method (mechanical, no NLP adjudication):
  1. Read the frozen class definition from the canonical F2a schema and hash it.
  2. Read every accepted entry in the L0 ledger whose `class_ids` contains the class.
  3. Score each entry against the class's three conjuncts, each read from the entry's own fields:
       D1 data class   : entry genericity/assumptions quantify over the frozen one-ended AF vacuum
                         Cauchy-data class (residual/comeagre in the weighted H^4 topology).
       D2 conclusion   : entry concludes future-inextendibility in the C2 extension class (directly,
                         or by the licensed non-Lipschitz => non-C2 regularity inclusion).
       D3 evidence     : entry is not an open_problem/literature_status, has no open hypothesis,
                         and its evidence level is peer-reviewed or accepted-in-press.
  4. An entry discharges the class only if D1 and D2 and D3 all hold.

Inputs are hashed; the output JSON is deterministic given them.  Nothing here re-adjudicates L0
`class_ids` (A1's job) or the F2a schema (formulation lead's job).
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLASS = "AF-SCC-C2-VAC-GEN"
SCHEMA = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
SCHEMA_AUTHORING = ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c2_vacuum.yaml"
LEDGER = ROOT / "ledger" / "theorems.jsonl"
MATRIX = ROOT / "ledger" / "class_coverage.csv"
SUMMARY = HERE / "coverage_summary.json"
MAP = ROOT / "research_map" / "research_map.json"
OUT = HERE / "c2_class_conformance_audit.json"

TZ = timezone(timedelta(hours=8))
PEER_LEVELS = {"peer-reviewed", "accepted-in-press"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grab(text: str, key: str) -> str:
    m = re.search(r"^\s*" + re.escape(key) + r"\s*:\s*(.+)$", text, re.M)
    if not m:
        return ""
    return m.group(1).strip().strip('"')


def main() -> int:
    text = SCHEMA.read_text(encoding="utf-8", errors="replace")
    authoring = SCHEMA_AUTHORING.read_text(encoding="utf-8", errors="replace") if SCHEMA_AUTHORING.exists() else ""
    class_def = {
        "path": str(SCHEMA.relative_to(ROOT)),
        "sha256": sha256(SCHEMA),
        "class_id": grab(text, "class_id"),
        "conclusion_type": grab(text, "conclusion_type"),
        "conclusion_statement": grab(text, "statement_natural_language"),
        "quantifier_class": grab(text, "quantifier_class"),
        # the schema layout changed across revisions (rev3 used genericity_kind; later revisions
        # carry a bare `genericity:` token): accept either spelling.
        "genericity_kind": grab(text, "genericity_kind") or grab(text, "genericity"),
        "extension_regularity": grab(text, "extension_regularity"),
        "claim_promotion": grab(text, "claim_promotion"),
        "symmetry": grab(text, "symmetry"),
    }
    # the frozen data-class definition (line-wrapped YAML scalar; accept both layouts)
    m = (re.search(r"^\s*definition:\s*\"([^\"]*H\^?4[^\"]*)\"", text, re.M)
         or re.search(r"^\s*definition:\s*\"(h - delta_euclidean[^\"]*)\"", text, re.M))
    class_def["data_class_definition"] = m.group(1) if m else ""
    m = re.search(r"^\s*equations:\s*\"([^\"]*)\"", text, re.M)
    class_def["data_class_equations"] = m.group(1) if m else ""
    m = re.search(r"^\s*default:\s*\"([^\"]*)\"", text, re.M)
    class_def["data_class_regularity_default"] = m.group(1) if m else ""
    m = re.search(r"^\s*sobolev_variant:\s*(\{.*\})", text, re.M)
    class_def["data_class_sobolev_variant"] = m.group(1) if m else ""
    m = re.search(r"^\s*generic_set:\s*\"([^\"]*)\"", text, re.M)
    class_def["generic_set"] = m.group(1) if m else ""

    if authoring and sha256(SCHEMA_AUTHORING) != sha256(SCHEMA):
        class_def["authoring_tree_observation"] = {
            "path": str(SCHEMA_AUTHORING.relative_to(ROOT)),
            "sha256": sha256(SCHEMA_AUTHORING),
            "quantifier_class": grab(authoring, "quantifier_class"),
            "conclusion_statement": grab(authoring, "statement_natural_language"),
            "note": (
                "dual-tree copy differs in quantifier_class and natural-language statement; "
                "recorded as an observation for the formulation lead / A1, not adjudicated by L1"
            ),
        }
    else:
        class_def["authoring_tree_observation"] = (
            "no divergence at read time: canonical and authoring copies share sha256 "
            + sha256(SCHEMA)
        )

    entries = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    bound = [e for e in entries if CLASS in (e.get("class_ids") or [])]

    # record the revision the map's G-FORM gate still names, when it differs from the file on disk
    map_note = None
    if MAP.exists():
        md = json.loads(MAP.read_text(encoding="utf-8"))
        for g in md.get("gates", []):
            if g.get("gate_id") == "G-FORM":
                unmet = " ".join(g.get("unmet") or [])
                mm = re.search(r"F2a at ([0-9a-f]{8,})", unmet)
                if mm:
                    map_note = {
                        "map_gate_measured_f2a_prefix": mm.group(1),
                        "canonical_file_sha256": sha256(SCHEMA),
                        "map_updated_at": md.get("updated_at"),
                        "note": "map gate text and the canonical file on disk disagree; publication/review rebinding is the formulation lead's call, recorded here only to date the audit",
                    }
    class_def["map_pinned_f2a_revision_observation"] = map_note

    bindings = []
    for e in sorted(bound, key=lambda x: x["theorem_id"]):
        gen = (e.get("genericity") or "").lower()
        caveats = " ".join(e.get("scope_caveats") or []).lower()
        unresolved = e.get("unresolved") or []
        # D1: frozen data class = generic (residual) one-ended asymptotically flat vacuum Cauchy data
        d1_generic_residual = ("residual" in gen or "comeagre" in gen or "comeager" in gen) and "vacuum" in gen
        d1_wrong_class = any(k in gen + " " + caveats for k in (
            "characteristic", "not full asymptotically flat", "interior", "special", "not generic",
            "not quantified", "expected (not proved", "not proved here"))
        d1 = bool(d1_generic_residual and not d1_wrong_class)
        # D2: C2 future-inextendibility conclusion
        d2 = e.get("conclusion_type") in {"theorem", "conditional_theorem"} and (
            "inextendib" in json.dumps(e).lower() or "inextendib" in (e.get("statement_exact") or "").lower()
        )
        # D3: no open hypothesis, adequate evidence level
        d3 = e.get("status") == "accepted" and e.get("evidence_level") in PEER_LEVELS and not any(
            "not peer-reviewed" in c.lower() or "preprint" in c.lower() for c in (e.get("scope_caveats") or [])
        ) and not unresolved
        failing = [name for name, ok in (("D1_data_class", d1), ("D2_conclusion", d2), ("D3_evidence", d3)) if not ok]
        bindings.append({
            "theorem_id": e["theorem_id"],
            "label": e.get("label"),
            "entry_kind": e.get("entry_kind"),
            "conclusion_type": e.get("conclusion_type"),
            "status": e.get("status"),
            "verification_status": e.get("verification_status"),
            "evidence_level": e.get("evidence_level"),
            "genericity": e.get("genericity"),
            "n_open_items": len(unresolved),
            "checks": {"D1_data_class": d1, "D2_conclusion": d2, "D3_evidence": d3},
            "discharges_class": not failing,
            "failing_conjuncts": failing,
            "evidence_ref": f"ledger/theorems.jsonl#{sha256(LEDGER)[:12]}:{e['theorem_id']}",
        })

    discharging = [b["theorem_id"] for b in bindings if b["discharges_class"]]

    import csv as _csv
    covered_cells = []
    with MATRIX.open(newline="", encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if row["class_id"] == CLASS and row["coverage"] == "covered":
                covered_cells.append({
                    "source_id": row["source_id"],
                    "theorem_ids": [t for t in row["theorem_ids"].split(" | ") if t],
                })

    created_at = datetime.now(TZ)
    out = {
        "audit_id": "flash-10-c2-class-conformance-" + created_at.strftime("%Y%m%dT%H%M%S"),
        "node_id": "L1",
        "class_id": CLASS,
        "actor": "deepseek-flash-10",
        "created_at": created_at.isoformat(timespec="seconds"),
        "class_definition": class_def,
        "requirement_conjuncts": {
            "D1_data_class": "generic (residual/comeagre) one-ended asymptotically flat vacuum Cauchy data in the frozen weighted H^4 topology",
            "D2_conclusion": "maximal development future-inextendible as a twice continuously differentiable vacuum Lorentzian manifold",
            "D3_evidence": "accepted entry, no open hypothesis, evidence level peer-reviewed or accepted-in-press",
        },
        "bindings": bindings,
        "summary": {
            "n_bound_entries": len(bindings),
            "n_discharging": len(discharging),
            "discharging_entries": discharging,
            "class_conclusion_state": "open_problem" if not discharging else "discharged",
            "matrix_crosswalk": {
                "canonical_matrix": str(MATRIX.relative_to(ROOT)),
                "matrix_sha256": sha256(MATRIX),
                "covered_cells": covered_cells,
                "reading": "covered = theorem-strength binding only; none of the bound entries discharges D1+D2+D3, so the cell is a binding, not a class conclusion",
            },
        },
        "inputs": {
            "ledger/theorems.jsonl": {"sha256": sha256(LEDGER), "entries": len(entries), "bound_entries": len(bindings)},
            "schemas/af_scc_c2_vacuum.yaml": {"sha256": sha256(SCHEMA)},
            "ledger/class_coverage.csv": {"sha256": sha256(MATRIX)},
            "artifacts/flash-10/l1_class_coverage/coverage_summary.json": {"sha256": sha256(SUMMARY)},
        },
        "falsifier": (
            "Produce one accepted ledger entry bound to AF-SCC-C2-VAC-GEN that (i) quantifies over generic "
            "(residual/comeagre) one-ended asymptotically flat vacuum Cauchy data, (ii) concludes future "
            "C2-inextendibility of the maximal development, and (iii) is peer-reviewed or accepted-in-press with "
            "no open hypothesis. Then n_discharging >= 1 and the class conclusion state is 'discharged'."
        ),
        "limitations": [
            "The audit inherits L0 class_ids; it does not re-adjudicate them (A1's job).",
            "D1/D2/D3 are mechanical readings of the ledger fields genericity/scope_caveats/unresolved; a human reviewer may bind an entry differently, which is exactly the A1 verdict this artifact asks for.",
            "The matrix and this audit are snapshots; ledger drift is reported in the input hashes.",
        ],
        "validation_status": "unverified",
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} | bound={len(bindings)} discharging={len(discharging)}")
    for b in bindings:
        print(f"  {b['theorem_id']:6s} {b['entry_kind']:18s} {b['conclusion_type']:20s} {b['evidence_level']:18s} -> fails {b['failing_conjuncts']}")
    print("sha256:", sha256(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
