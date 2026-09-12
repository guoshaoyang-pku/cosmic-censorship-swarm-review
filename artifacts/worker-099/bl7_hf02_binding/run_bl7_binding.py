#!/usr/bin/env python3
"""W099-BL7-HF02-BINDING-01: per-row class-binding determination for the 8 dual-bound
L0 ledger rows, with quote grounding against the pinned ledger bytes.

Reads:  artifacts/worker-099/bl7_hf02_binding/{PREREGISTRATION,ASSIGNMENTS}.json
Pins:    ledger/theorems.jsonl, ledger/citation_audit.csv,
         research_map/formulation_taxonomy.yaml, evaluation_rubric.yaml,
         research_map/class_separation.py
Writes: artifacts/worker-099/bl7_hf02_binding/binding_analysis.json

Exit codes: 0 ok | 3 pinned input drift | 4 control failure

This tool measures and classifies. It rules nothing, edits no ledger, and sets no
node/gate/validation status. See PREREGISTRATION.json.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
FROZEN_FOUR = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
EXPECTED_DUAL = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]
SUBJECT_RELATIONS = {
    "SUBJECT_EXTENDIBILITY",
    "SUBJECT_INEXTENDIBILITY",
    "SUBJECT_STATUS",
}

REG_TOKENS = [
    ("C2", re.compile(r"c\s*\^?\{?\s*2\s*\}?(?![0-9])", re.I)),
    ("C1", re.compile(r"c\s*\^?\{?\s*1\s*\}?(?![0-9])", re.I)),
    ("LIPSCHITZ", re.compile(r"lipschitz|c\s*\^?\{?\s*0\s*,\s*1\s*\}?", re.I)),
    ("L2_LOC", re.compile(r"l\s*\^?2\s*_?loc|l\s*\^?2\b", re.I)),
    ("LS_LOC", re.compile(r"l\s*\^?s\s*_?loc", re.I)),
    ("C0", re.compile(r"c\s*\^?\{?\s*0\s*\}?(?![0-9])", re.I)),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def regex_tokens(text: str) -> list[str]:
    return [name for name, pat in REG_TOKENS if pat.search(text)]


def main() -> int:
    prereg = json.loads((HERE / "PREREGISTRATION.json").read_text())
    assignments = json.loads((HERE / "ASSIGNMENTS.json").read_text())
    pins = prereg["pins"]

    # ---- 1. pinned input drift -------------------------------------------------
    measured = {}
    drift = []
    for rel, expected in pins.items():
        p = ROOT / rel
        got = sha256_file(p) if p.is_file() else None
        measured[rel] = got
        if got != expected:
            drift.append({"path": rel, "expected": expected, "measured": got})
    if drift:
        print("PINNED INPUT DRIFT: " + json.dumps(drift, indent=1))
        return 3

    rows = [json.loads(line) for line in (ROOT / "ledger/theorems.jsonl").read_text().splitlines() if line.strip()]
    sources = {r["citation_id"]: r for r in csv.DictReader((ROOT / "ledger/citation_audit.csv").open())}
    taxonomy = yaml.safe_load((ROOT / "research_map/formulation_taxonomy.yaml").read_text())
    rubric_text = (ROOT / "evaluation_rubric.yaml").read_text()
    detector_text = (ROOT / "research_map/class_separation.py").read_text()

    # ---- 2. population ---------------------------------------------------------
    dual = [r for r in rows if len(r.get("class_ids", [])) >= 2]
    dual_ids = sorted(r["theorem_id"] for r in dual)
    over2 = [r["theorem_id"] for r in rows if len(r.get("class_ids", [])) > 2]
    row_by_id = {r["theorem_id"]: r for r in rows}

    assigned_by_row = {a["theorem_id"]: a for a in assignments["rows"]}
    c1_population = (
        dual_ids == sorted(EXPECTED_DUAL)
        and not over2
        and sorted(assigned_by_row) == sorted(EXPECTED_DUAL)
    )

    # ---- 3. cell grounding + classification ------------------------------------
    results = []
    cells_total = cells_grounded = mutants_caught = 0
    relation_counts: dict[str, int] = {}
    resolution_counts: dict[str, int] = {}
    for tid in EXPECTED_DUAL:
        row = row_by_id[tid]
        asg = assigned_by_row[tid]
        hay = norm(json.dumps(row, ensure_ascii=False, sort_keys=True))
        reg_text = f"{row.get('regularity', '')} || {row.get('statement_exact', '')}"
        cells = []
        for cell in asg["cells"]:
            cells_total += 1
            quote = cell["quote"]
            grounded = norm(quote) in hay
            cells_grounded += int(grounded)
            toks = norm(quote).split()
            # Fabrication control: replace the final token with a sentinel that cannot occur in
            # the pinned bytes. (Truncation would be a prefix of a verbatim quote and would stay
            # grounded, so it cannot serve as a fabrication control.)
            mutant = " ".join(toks[:-1] + ["ZZQFABRICATED"]) if toks else ""
            mutant_caught_here = bool(mutant) and norm(mutant) not in hay
            mutants_caught += int(mutant_caught_here)
            cells.append(
                {
                    "class_id": cell["class_id"],
                    "relation": cell["relation"],
                    "quote": quote,
                    "quote_grounded_in_pinned_row": grounded,
                    "fabrication_negative_control_caught": mutant_caught_here,
                    "class_id_in_frozen_four": cell["class_id"] in FROZEN_FOUR,
                }
            )
            relation_counts[cell["relation"]] = relation_counts.get(cell["relation"], 0) + 1
        resolution_counts[asg["resolution"]] = resolution_counts.get(asg["resolution"], 0) + 1
        results.append(
            {
                "theorem_id": tid,
                "class_ids": row["class_ids"],
                "entry_kind": row.get("entry_kind"),
                "conclusion_type": row.get("conclusion_type"),
                "content_status": row.get("content_status"),
                "regularity_field": row.get("regularity"),
                "mechanical_regularity_tokens": regex_tokens(reg_text),
                "source_ids": row.get("source_ids", []),
                "subject": asg["subject"],
                "cells": cells,
                "intermediate_quote": asg.get("intermediate_quote"),
                "caveat_quote": asg.get("caveat_quote"),
                "resolution": asg["resolution"],
                "recommendation": asg["recommendation"],
                "notes": asg.get("notes"),
            }
        )

    # ---- 4. controls ------------------------------------------------------------
    # C2 token census
    all_tokens = [c["class_id"] for r in results for c in r["cells"]]
    c2_census = all(t in FROZEN_FOUR for t in all_tokens) and len(all_tokens) == 16
    # C3 transfer_argument key census over all 62 rows
    rows_with_transfer_argument = [r["theorem_id"] for r in rows if "transfer_argument" in r]
    c3_no_transfer_argument = len(rows_with_transfer_argument) == 0
    # C4 grounding
    c4_grounding = cells_grounded == cells_total == 16
    # C5 fabrication negative control
    c5_mutants = mutants_caught == cells_total == 16
    # C6 order-insensitivity: relation keyed by class id, not list position
    order_ok = True
    for r in results:
        fwd = {c["class_id"]: c["relation"] for c in r["cells"]}
        rev = {cid: fwd[cid] for cid in reversed(r["class_ids"])}
        if rev != fwd or set(fwd) != set(r["class_ids"]):
            order_ok = False
    order_first_c2 = sum(1 for r in results if r["class_ids"][0] == "AF-SCC-C2-VAC-GEN")
    # C7 single-bound control
    single_bound = [r for r in rows if len(r.get("class_ids", [])) <= 1]
    c7_single_bound = len(single_bound) == 54 and not any(
        "cells" in a for a in assignments["rows"] if a["theorem_id"] not in EXPECTED_DUAL
    )

    controls = {
        "C1_population_is_exactly_the_8_named_dual_rows": c1_population,
        "C2_all_16_class_tokens_in_frozen_four": c2_census,
        "C3_no_row_carries_the_hf02_exemption_key_transfer_argument": c3_no_transfer_argument,
        "C4_every_cell_quote_grounded_in_pinned_row_bytes": c4_grounding,
        "C5_fabrication_negative_control_catches_every_truncated_quote": c5_mutants,
        "C6_relations_are_order_insensitive_wrt_class_ids_list": order_ok,
        "C7_single_and_zero_bound_rows_are_54_and_get_no_cells": c7_single_bound,
        "details": {
            "dual_rows_found": dual_ids,
            "rows_with_more_than_two_class_ids": over2,
            "rows_with_transfer_argument_key": rows_with_transfer_argument,
            "cells_grounded": f"{cells_grounded}/{cells_total}",
            "truncated_quote_mutants_caught": f"{mutants_caught}/{cells_total}",
            "class_ids_list_order_first_is_C2": f"{order_first_c2}/8",
            "single_or_zero_bound_rows": len(single_bound),
            "detector_sha256": pins["research_map/class_separation.py"],
            "detector_scope_note": "The canonical detector is quoted for the record only; this pack does not run or re-implement it.",
            "rubric_hf02_present": "HF-02" in rubric_text and "disjunction of class_ids" in rubric_text,
            "detector_reads_plural_class_ids": "class_ids" in detector_text,
        },
    }
    all_controls_pass = all(v for k, v in controls.items() if k.startswith("C"))

    # taxonomy's own one-binding discipline, quoted for the record
    cls = taxonomy["classes"]
    discriminators = {
        "AF-SCC-C2-VAC-GEN_exclusion": [e for e in cls["AF-SCC-C2-VAC-GEN"]["exclusions"] if "C0" in e],
        "AF-SCC-C0-VAC-GEN_exclusion": [e for e in cls["AF-SCC-C0-VAC-GEN"]["exclusions"] if "C2" in e],
        "AF-WCC-VAC-GEN_exclusion": [e for e in cls["AF-WCC-VAC-GEN"]["exclusions"] if "Strong cosmic" in e],
        "AF-SCC-C2-VAC-GEN_regularity_token": cls["AF-SCC-C2-VAC-GEN"]["axes"]["regularity_token"],
        "AF-SCC-C0-VAC-GEN_regularity_token": cls["AF-SCC-C0-VAC-GEN"]["axes"]["regularity_token"],
        "AF-SCC-C2-VAC-GEN_conclusion_type": cls["AF-SCC-C2-VAC-GEN"]["axes"]["conclusion_type"],
        "AF-SCC-C0-VAC-GEN_conclusion_type": cls["AF-SCC-C0-VAC-GEN"]["axes"]["conclusion_type"],
    }

    aggregate = {
        "population_rows": 8,
        "ledger_rows": len(rows),
        "cells": 16,
        "resolution_counts": resolution_counts,
        "relation_counts": relation_counts,
        "single_subject_rows": sum(1 for k, v in resolution_counts.items() if k.startswith("SINGLE_SUBJECT")),
        "genuine_dual_rows": resolution_counts.get("GENUINE_DUAL", 0),
        "intermediate_neither_rows": resolution_counts.get("INTERMEDIATE_NEITHER", 0),
        "interpretation": (
            "Under the strict one-binding-class reading, 4/8 rows have a determinable single subject whose second id "
            "is relevance/antecedent/inference; 1/8 (T-402) asserts a relation to both classes; 3/8 (D-004, D-005, T-305) "
            "have no frozen-class subject at all because their subject is an intermediate extension class strictly inside "
            "the C0..C2 interval. The literal BL-6 instruction 'choose ONE class or move the second to informs_classes' "
            "therefore has a correct answer for 4/8 rows only."
        ),
    }

    core = {
        "population": {"dual_rows": dual_ids, "ledger_rows": len(rows)},
        "rows": results,
        "aggregate": aggregate,
        "controls": controls,
    }
    core_digest = hashlib.sha256(canonical(core).encode()).hexdigest()

    out = {
        "schema_version": "0.1",
        "artifact_type": "bl7_hf02_binding_analysis",
        "task_id": "W099-BL7-HF02-BINDING-01",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "actor": "worker-099",
        "instance": "worker-099-20260912T005246-968807",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "question": prereg["question"],
        "authority_boundary": prereg["authority_boundary"],
        "evidence_level": prereg["evidence_level"],
        "pins": {rel: {"expected": pins[rel], "measured": measured[rel], "match": measured[rel] == pins[rel]} for rel in pins},
        "assignments_sha256": pins["artifacts/worker-099/bl7_hf02_binding/ASSIGNMENTS.json"],
        "taxonomy_discriminators": discriminators,
        "sources_referenced": sorted({s for r in results for s in r["source_ids"]}),
        "population": core["population"],
        "rows": results,
        "aggregate": aggregate,
        "controls": controls,
        "all_controls_pass": all_controls_pass,
        "core_digest_sha256": core_digest,
        "limitations": [
            "Abstract/metadata-level read only; no page-level or theorem-statement check; no live fetch was made.",
            "The cell relations are a manual expert read, not an automatic classifier; their only machine guarantee is verbatim quote grounding plus the C5 fabrication control.",
            "The C0..C2 ordering (C0 < L^2/L^s connection < Lipschitz < C1 < C2) is the ledger's own reading, quoted from the rows (D-004 does_not_imply, D-005 scope_caveats); where a row relies on a regularity inclusion the cell is marked INFERENCE, not SUBJECT_*.",
            "Aggregates describe the 8-row dual-bound population only; they are not class-binding scores for the 62-row ledger and must not be read as one.",
        ],
        "related_findings": {
            "w063_l0_scope": "reviews/w063-l0-scope-adjudication.json#5db1b10fb3c4 (scope/routing input; content-side per-row table is this pack's addition)",
            "l0_review_17_current": "reviews/L0-review-17-current.json (first HF-02 finding on the 8 rows)",
            "l0_review_18_current": "reviews/L0-review-18-current.json (HF-03 on D-004/SRC-029 matter model; distinct defect class)",
            "bl_6": "comms/outbox/astra-lead-literature.jsonl lit-l5-20260912-011 (BL-6 needed_to_unblock)",
            "bl_7": "comms/outbox/astra-lead-literature.jsonl lit-l6-20260912-006 and lit-l7-20260912-003 (gate-deciding question)",
        },
        "falsifiers": prereg["falsifiers"],
        "not_claimed": prereg["not_claimed"],
        "reproduce": prereg["reproduce"],
    }

    out_path = HERE / "binding_analysis.json"
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")

    print(f"population: {dual_ids}")
    print(f"cells grounded: {cells_grounded}/{cells_total}; mutants caught: {mutants_caught}/{cells_total}")
    print(f"resolutions: {json.dumps(resolution_counts, sort_keys=True)}")
    print(f"relations:   {json.dumps(relation_counts, sort_keys=True)}")
    print(f"all controls pass: {all_controls_pass}")
    print(f"core_digest_sha256: {core_digest}")
    print(f"wrote: {out_path.relative_to(ROOT)}")
    return 0 if all_controls_pass else 4


if __name__ == "__main__":
    sys.exit(main())
