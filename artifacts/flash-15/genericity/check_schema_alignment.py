#!/usr/bin/env python3
"""FORM-GEN-05 advisory precheck: do the canonical schemas' genericity blocks agree with the
genericity matrix?

ADVISORY ONLY. This is not a gate run and emits no gate verdict; gate G-CLASSBIND belongs to
astra-lead-formulation. Output is pinned to schema sha256 so findings cannot drift onto a later
revision. Read-only.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
SPEC = json.loads((ROOT / "artifacts" / "formulation" / "rule_spec.json").read_text())
MATRIX = json.loads((HERE / "genericity_matrix.json").read_text())
SCHEMAS_DIR = (Path(sys.argv[sys.argv.index("--schemas-dir") + 1]).resolve() if "--schemas-dir" in sys.argv else ROOT / "schemas")
OUT_PATH = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "schema_alignment_precheck.json"
SCHEMAS = {
    "AF-WCC-VAC-GEN": SCHEMAS_DIR / "af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": SCHEMAS_DIR / "af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": SCHEMAS_DIR / "af_scc_c0_vacuum.yaml",
}
R07_KEYS = ["ambient_space", "topology_or_measure", "generic_set", "excluded_set",
            "transfer_failures", "is_part_of_class"]
# Near-miss key names seen in the current drafts. R07 fixes the canonical names, so an alias is
# still a naming finding, but the report must not pretend the content is absent.
ALIASES = {
    "ambient_space": ["parameter_space", "data_space", "ambient"],
    "topology_or_measure": ["topology_name", "topology", "measure"],
    "generic_set": ["candidate_definitions", "generic_set_definition"],
    "excluded_set": ["exception_set", "known_non_generic_exceptions", "non_generic_examples"],
    "transfer_failures": ["transfer", "non_equivalences", "transfer_claims"],
    "is_part_of_class": ["is_part_of_class"],
}
VOCAB = [k for k in SPEC["vocabularies"]["genericity_kind"] if k != "none"]
MY_TRANSFER = {(r["from"], r["to"]): r["state"] for r in MATRIX["transfer_matrix"]}

report = {"artifact_kind": "genericity_schema_alignment_precheck", "advisory_only": True,
          "not_a_gate_verdict": True, "matrix_sha256": hashlib.sha256((HERE / "genericity_matrix.json").read_bytes()).hexdigest(),
          "schemas": {}}

for cid, path in SCHEMAS.items():
    entry = {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
             "findings": []}
    doc = yaml.safe_load(path.read_text())
    g = doc.get("genericity") if isinstance(doc, dict) else None
    if not isinstance(g, dict):
        entry["findings"].append({"severity": "hard", "rule": "R07", "code": "no_genericity_mapping",
                                  "detail": "genericity block absent or not a mapping"})
        report["schemas"][cid] = entry
        continue

    # G1 kind token
    kind = g.get("kind")
    if kind not in VOCAB:
        entry["findings"].append({
            "severity": "hard", "rule": "R07", "code": "kind_not_a_vocabulary_token",
            "detail": f"kind={kind!r} is prose, not one of {VOCAB}",
            "consequence": "G-CLASSBIND R07 fails unless rewritten as a token plus separate prose fields"})
        kl = str(kind).lower()
        if "open" in kl and ("residual" in kl or "comeag" in kl or "meagre" in kl or "meager" in kl):
            entry["findings"].append({
                "severity": "hard", "rule": "R07/class-identity", "code": "kind_conflates_two_notions",
                "detail": ("prose kind names both an open-dense reading and a residual/comeager reading. They are not "
                           "equivalent: residual_comeager -> open_dense_escape fails (W3: the irrationals are comeager "
                           "with empty interior), so a class quantified over the residual set differs from one quantified "
                           "over an open dense set. af_scc_c0_vacuum.yaml itself distinguishes them ('open dense only' is "
                           "strictly weaker), so the drafts are mutually inconsistent about the notion.")})

    # G2 required keys (canonical R07 names; alias presence is reported, not hidden)
    for k in R07_KEYS:
        if k not in g:
            alias = [a for a in ALIASES.get(k, []) if a in g]
            entry["findings"].append({
                "severity": "hard", "rule": "R07",
                "code": f"missing_{k}" if not alias else f"missing_{k}__alias_present",
                "detail": (f"genericity.{k} absent" if not alias else
                           f"genericity.{k} absent under its canonical name; alias(es) present: {alias} "
                           f"(R07 fixes key names, so the alias is still a naming finding, not a content gap)")})
    if "transfer_failures" in g and not g["transfer_failures"]:
        entry["findings"].append({"severity": "hard", "rule": "R07", "code": "empty_transfer_failures"})
    if g.get("is_part_of_class") is not True:
        entry["findings"].append({"severity": "hard", "rule": "R07", "code": "is_part_of_class_not_true"})
    changing = " ".join(str(g.get(k, "")) for k in (
        "changing_notion_statement", "class_change_warning", "is_part_of_class_statement",
        "failed_transfer_semantics", "class_change_note"))
    markers = ["different class", "strictly stronger", "strictly weaker", "class identity",
               "part of the class", "class_change"]
    if not any(s in changing.lower() for s in markers):
        entry["findings"].append({"severity": "warn", "rule": "R07", "code": "no_changing_notion_statement",
                                  "detail": "no explicit statement that changing the notion changes the class/strength"})

    # G3 transfer-claim consistency vs the matrix
    tf = g.get("transfer_failures") or []
    for item in tf:
        if not isinstance(item, dict):
            continue
        pair = item.get("pair")
        direction = item.get("direction")
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            key = (pair[0], pair[1])
            mine = MY_TRANSFER.get(key)
            if direction in ("no_transfer", "fails") and mine == "holds":
                entry["findings"].append({
                    "severity": "hard", "rule": "matrix-consistency", "code": "contradicts_matrix_holds",
                    "pair": list(key), "schema_claim": direction, "matrix_state": mine,
                    "detail": ("schema denies a transfer that is definitional: an open dense set is a "
                               "countable intersection of open dense sets (itself), so it is comeager. "
                               "Witness text " + repr(item.get("witness")) + " is false as stated.")})
            elif direction in ("no_transfer", "fails") and mine == "fails":
                entry["findings"].append({"severity": "info", "rule": "matrix-consistency",
                                          "code": "agrees_with_matrix_fails", "pair": list(key)})
            elif mine == "open":
                entry["findings"].append({"severity": "warn", "rule": "matrix-consistency",
                                          "code": "matrix_says_open", "pair": list(key),
                                          "detail": "schema asserts a direction for a pair the matrix leaves open; needs the missing measure hypothesis stated"})

    # G4 hybrid topology vocabulary gap (single kind token cannot express different topologies for openness vs density)
    blob = json.dumps(g)
    if "open in" in blob and "dense in" in blob and "open in" in blob.split("dense in")[0]:
        entry["findings"].append({
            "severity": "warn", "rule": "vocabulary-gap", "code": "hybrid_open_and_dense_topologies",
            "detail": "block distinguishes the topology in which the set is open from the topology in which it is dense; no single genericity_kind token expresses this, so the schema must declare both topologies explicitly or the vocabulary must be extended by the owner"})

    report["schemas"][cid] = entry

hard = sum(1 for s in report["schemas"].values() for f in s["findings"] if f["severity"] == "hard")
warn = sum(1 for s in report["schemas"].values() for f in s["findings"] if f["severity"] == "warn")
report["summary"] = {"hard": hard, "warn": warn,
                     "note": "advisory input for the lead's G-CLASSBIND run; not a verdict"}

print(json.dumps(report, indent=2))
OUT_PATH.write_text(json.dumps(report, indent=2) + "\n")
print(f"\nADVISORY PRECHECK: hard={hard} warn={warn} -> {OUT_PATH}")
