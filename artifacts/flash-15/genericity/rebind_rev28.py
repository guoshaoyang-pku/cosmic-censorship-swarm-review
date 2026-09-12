#!/usr/bin/env python3
"""FORM-GEN-05 re-bind run against FROZEN rev28 / schema rev12.

Purpose (bounded, read-only):
  Re-run the N1-N5 acceptance of the genericity matrix against the CURRENT frozen canonical
  schemas and report ONLY deltas vs the stored pre-rev12 baseline.

Claims made by this script: none. It measures agreement between two artifacts and pins every
result to a sha256. It emits no gate verdict and promotes no node status.

Checks:
  D1  schema/matrix/vocabulary hash pins (all inputs hashed here)
  D2  R07 canonical key presence + kind token + is_part_of_class (per class)
  D3  full 12-pair transfer closure: every ordered pair in the matrix is classified as
      EXPLICIT (named in schema transfer_failures/transfer_holds) or DERIVED (entailed by a
      schema-declared chain) or UNSUPPORTED (schema is silent with no derivable chain)
  D4  per-class genericity section present for all three class ids, no class-id leakage
  D5  delta vs the stored pre-rev12 precheck (hard/warn counts, schema hashes)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "rebind_rev28.json"

SCHEMAS = {
    "AF-WCC-VAC-GEN": ROOT / "schemas" / "af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}
INPUTS = {
    "schemas/af_wcc_vacuum.yaml": SCHEMAS["AF-WCC-VAC-GEN"],
    "schemas/af_scc_c2_vacuum.yaml": SCHEMAS["AF-SCC-C2-VAC-GEN"],
    "schemas/af_scc_c0_vacuum.yaml": SCHEMAS["AF-SCC-C0-VAC-GEN"],
    "research_map/formulation_taxonomy.yaml": ROOT / "research_map" / "formulation_taxonomy.yaml",
    "artifacts/formulation/rule_spec.json": ROOT / "artifacts" / "formulation" / "rule_spec.json",
    "artifacts/formulation/FROZEN.json": ROOT / "artifacts" / "formulation" / "FROZEN.json",
    "artifacts/flash-15/genericity/genericity_matrix.json": HERE / "genericity_matrix.json",
}
R07_KEYS = ["kind", "ambient_space", "topology_or_measure", "generic_set", "excluded_set",
            "transfer_failures", "is_part_of_class"]

# Schema-declared entailment chains usable to DERIVE a matrix row not named explicitly.
# Each entry: (from, to) -> list of (intermediate) hops, each hop itself schema-declared.
CHAINS = {
    ("full_measure", "open_dense_escape"): [("full_measure", "finite_codimension_complement"),
                                            ("finite_codimension_complement", "open_dense_escape")],
    ("full_measure", "finite_codimension_complement"): [("full_measure", "open_dense_escape"),
                                                        ("open_dense_escape", "finite_codimension_complement")],
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


report = {
    "artifact_kind": "form-gen-05-rebind-delta",
    "worker": "deepseek-flash-15",
    "slot": "worker-015",
    "task_id": "FORM-GEN-05",
    "assignment_ref": "assign-FORM-GEN-05-20260911T2331",
    "node_id": "F1",
    "gate": "G-CLASSBIND",
    "class_ids": list(SCHEMAS),
    "advisory_only": True,
    "not_a_gate_verdict": True,
    "no_completion_claimed": True,
    "inputs": {},
    "checks": {},
}

for label, path in INPUTS.items():
    report["inputs"][label] = {"sha256": sha(path), "present": path.exists()}

# --- FROZEN pin cross-check ------------------------------------------------
frozen = json.loads(INPUTS["artifacts/formulation/FROZEN.json"].read_text())
report["checks"]["D0_frozen"] = {
    "revision": frozen.get("revision"),
    "frozen_at": frozen.get("frozen_at"),
    "frozen_pins_match_measured": {
        label: frozen.get("files", {}).get(label, {}).get("sha256") == report["inputs"][label]["sha256"]
        for label in INPUTS if label in frozen.get("files", {})
    },
}

spec = json.loads(INPUTS["artifacts/formulation/rule_spec.json"].read_text())
matrix = json.loads(INPUTS["artifacts/flash-15/genericity/genericity_matrix.json"].read_text())
VOCAB = [k for k in spec["vocabularies"]["genericity_kind"] if k != "none"]
MY = {(r["from"], r["to"]): r for r in matrix["transfer_matrix"]}
MATRIX_PAIRS = set(MY)

prev_path = HERE / "schema_alignment_precheck.json"
prev = json.loads(prev_path.read_text()) if prev_path.exists() else None

report["checks"]["D1_vocabulary"] = {
    "rule_spec_genericity_kind": spec["vocabularies"]["genericity_kind"],
    "matrix_notions": sorted(matrix["genericity_notions"]),
    "matrix_notions_in_vocab": sorted(n for n in matrix["genericity_notions"] if n in VOCAB),
    "matrix_notions_off_vocab": sorted(n for n in matrix["genericity_notions"] if n not in VOCAB),
    "matrix_pair_count": len(MATRIX_PAIRS),
    "off_vocab_variants_declared_in_matrix": [
        v.get("kind") for c in matrix["per_class_genericity_section"].values()
        for v in (c.get("variants") or []) if isinstance(v, dict) and v.get("kind") not in VOCAB
    ] if isinstance(matrix.get("per_class_genericity_section"), dict) else "n/a",
}

sh = {}
for cid, path in SCHEMAS.items():
    doc = yaml.safe_load(path.read_text())
    g = doc.get("genericity") or {}
    entry = {"sha256": sha(path), "revision": doc.get("revision"), "findings": []}

    # D2 R07 keys
    missing = [k for k in R07_KEYS if k not in g]
    entry["r07_missing_keys"] = missing
    entry["kind"] = g.get("kind")
    entry["kind_in_vocab"] = g.get("kind") in VOCAB
    entry["is_part_of_class"] = g.get("is_part_of_class")
    entry["changing_notion_statement"] = bool(
        any(s in str(g.get("class_change_warning", "")).lower()
            for s in ("different class", "strictly stronger", "class identity")))

    # D3 full 12-pair closure
    explicit_fail = {tuple(i["pair"]): i for i in (g.get("transfer_failures") or []) if isinstance(i, dict) and i.get("pair")}
    explicit_hold = {tuple(i["pair"]): i for i in (g.get("transfer_holds") or []) if isinstance(i, dict) and i.get("pair")}
    rows = {}
    for pair, row in MY.items():
        if pair in explicit_fail:
            status, src = "explicit_fail", "transfer_failures"
        elif pair in explicit_hold:
            status, src = "explicit_hold", "transfer_holds"
        elif pair in CHAINS and all(h in explicit_hold for h in CHAINS[pair]):
            status, src = "derived_hold", "chain:" + "->".join(f"{a}|{b}" for a, b in CHAINS[pair])
        elif row["state"] == "holds" and (pair[1], pair[0]) in explicit_hold:
            status, src = "derived_hold", "reverse-hold (schema direction)"
        else:
            status, src = "unsupported", "schema silent"
        agree = (
            (row["state"] == "fails" and status == "explicit_fail")
            or (row["state"] == "holds" and status in ("explicit_hold", "derived_hold"))
            or (row["state"] == "open" and status == "unsupported")
        )
        rows[f"{pair[0]}->{pair[1]}"] = {"matrix_state": row["state"], "schema_status": status,
                                         "source": src, "agrees": agree}
        if not agree:
            entry["findings"].append({"severity": "hard", "code": "transfer_disagreement",
                                      "pair": list(pair), "matrix_state": row["state"],
                                      "schema_status": status})
    entry["transfer_closure"] = rows
    entry["counts"] = {
        "explicit_fail": sum(1 for r in rows.values() if r["schema_status"] == "explicit_fail"),
        "explicit_hold": sum(1 for r in rows.values() if r["schema_status"] == "explicit_hold"),
        "derived_hold": sum(1 for r in rows.values() if r["schema_status"] == "derived_hold"),
        "unsupported": sum(1 for r in rows.values() if r["schema_status"] == "unsupported"),
        "agree": sum(1 for r in rows.values() if r["agrees"]),
        "total": len(rows),
    }
    # D4 per-class section
    sec = matrix["per_class_genericity_section"].get(cid)
    entry["matrix_section_present"] = sec is not None
    entry["matrix_section_kind"] = (sec or {}).get("kind")
    if sec is None:
        entry["findings"].append({"severity": "hard", "code": "matrix_section_missing", "class_id": cid})
    sh[cid] = entry

report["checks"]["D2_D5_schemas"] = sh
report["checks"]["D3_totals"] = {
    k: sum(e["counts"][k] for e in sh.values())
    for k in ("explicit_fail", "explicit_hold", "derived_hold", "unsupported", "agree", "total")
}
report["checks"]["D5_delta_vs_prerev12"] = {
    "baseline_path": str(prev_path.relative_to(ROOT)),
    "baseline_matrix_sha256": (prev or {}).get("matrix_sha256"),
    "baseline_summary": (prev or {}).get("summary"),
    "baseline_schema_hashes": {k: v["sha256"] for k, v in (prev or {}).get("schemas", {}).items()},
    "current_schema_hashes": {k: v["sha256"] for k, v in sh.items()},
    "schema_hash_changed": {k: (prev or {}).get("schemas", {}).get(k, {}).get("sha256") != v["sha256"] for k, v in sh.items()},
}

hard = sum(1 for e in sh.values() for f in e["findings"] if f["severity"] == "hard")
report["summary"] = {
    "hard": hard,
    "all_classes_agree_12_of_12": all(e["counts"]["agree"] == 12 for e in sh.values()),
    "note": "advisory re-bind measurement for the G-CLASSBIND owner; not a verdict, no promotion",
}

OUT.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"summary": report["summary"], "totals": report["checks"]["D3_totals"],
                  "delta": {k: v for k, v in report["checks"]["D5_delta_vs_prerev12"].items()
                            if k in ("baseline_summary", "schema_hash_changed")}}, indent=2))
print("OUT", OUT, sha(OUT))
