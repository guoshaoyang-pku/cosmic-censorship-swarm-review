#!/usr/bin/env python3
"""FORM-GEN-05 re-bind closure: is the canonical schemas' transfer relation, as DECLARED,
mathematically equivalent to the 12-pair genericity matrix, or is there a real defect?

Read-only, advisory, no gate verdict.

The schemas do not print a 12-row table; they declare
  (a) the class default kind,
  (b) transfer_failures / transfer_holds (explicit edges),
  (c) variants[].{kind, statement_strength, relation},
  (d) class_change_warning prose.
A row is DERIVED iff it follows from the declared structure by:
  - definitional entailment along declared holds edges (transitivity),
  - the meaning of statement_strength=strictly_stronger/strictly_weaker for non-default kinds
    (X strictly stronger than default D => X -> D holds and D -> X fails),
  - the meaning of statement_strength=incomparable between that kind and the default.
Anything not EXPLICIT or DERIVED is SILENT and reported as a closure gap, not as a contradiction.
Only an explicit/derived OPPOSITE of the matrix state is a hard finding.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "rebind_closure_rev28.json"

SCHEMAS = {
    "AF-WCC-VAC-GEN": ROOT / "schemas" / "af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}
matrix = json.loads((HERE / "genericity_matrix.json").read_text())
MY = {(r["from"], r["to"]): r["state"] for r in matrix["transfer_matrix"]}
DEFAULT = "residual_comeager"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def closure(g: dict) -> dict:
    """Return {(from,to): ('holds'|'fails'|'open', provenance)} implied by the declared schema."""
    rel: dict[tuple, tuple] = {}
    why: dict[tuple, str] = {}

    def put(a, b, state, src):
        if (a, b) not in rel or rel[(a, b)][0] == "open":
            rel[(a, b)] = (state, src)
            why[(a, b)] = src

    for i in (g.get("transfer_holds") or []):
        if isinstance(i, dict) and isinstance(i.get("pair"), list) and len(i["pair"]) == 2:
            put(i["pair"][0], i["pair"][1], "holds", "explicit transfer_holds")
    for i in (g.get("transfer_failures") or []):
        if isinstance(i, dict) and isinstance(i.get("pair"), list) and len(i["pair"]) == 2:
            put(i["pair"][0], i["pair"][1], "fails", "explicit transfer_failures")

    variants = {}
    for v in (g.get("variants") or []):
        if isinstance(v, dict) and v.get("kind"):
            variants[v["kind"]] = v

    # First-order consequences of declared variant strengths. These are declared RELATIVE TO THE
    # DEFAULT quantifier, so they are asserted only on edges incident to DEFAULT: statement_strength
    # says how a kind compares with the class's own quantifier, not how two non-default kinds compare.
    # Explicit edges win over a variant annotation for the same pair.
    for kind, v in variants.items():
        if kind == "none":
            continue
        s = v.get("statement_strength")
        if s == "strictly_stronger":
            put(kind, DEFAULT, "holds", f"declared {kind}=strictly_stronger => {kind}->{DEFAULT}")
            put(DEFAULT, kind, "fails", f"declared {kind}=strictly_stronger => {DEFAULT}->{kind} fails")
        elif s == "strictly_weaker":
            put(DEFAULT, kind, "holds", f"declared {kind}=strictly_weaker => {DEFAULT}->{kind}")
            put(kind, DEFAULT, "fails", f"declared {kind}=strictly_weaker => {kind}->{DEFAULT} fails")
        elif s == "incomparable":
            put(DEFAULT, kind, "fails", f"declared {kind}=incomparable => {DEFAULT}->{kind} fails")
            put(kind, DEFAULT, "fails", f"declared {kind}=incomparable => {kind}->{DEFAULT} fails")

    # transitivity of holds
    changed = True
    while changed:
        changed = False
        for (a, b), (sa, _) in list(rel.items()):
            if sa != "holds":
                continue
            for (c, d), (sc, _) in list(rel.items()):
                if sc == "holds" and c == b and (a, d) not in rel:
                    put(a, d, "holds", f"transitive {a}->{b}->{d}")
                    changed = True

    # definitional: residual_comeager is exactly the default; open-dense-escape is a declared
    # strictly stronger variant of it; finite-codimension-complement is a declared holds edge.
    return {k: {"state": v[0], "provenance": v[1]} for k, v in rel.items()}


report = {"artifact_kind": "form-gen-05-rebind-closure", "worker": "deepseek-flash-15", "slot": "worker-015",
          "task_id": "FORM-GEN-05", "assignment_ref": "assign-FORM-GEN-05-20260911T2331",
          "node_id": "F1", "gate": "G-CLASSBIND", "class_ids": list(SCHEMAS),
          "advisory_only": True, "not_a_gate_verdict": True, "no_completion_claimed": True,
          "matrix_sha256": sha(HERE / "genericity_matrix.json"),
          "gate_test_tool": {"path": "artifacts/formulation/tools/run_gate_tests.py",
                             "sha256": sha(ROOT / "artifacts" / "formulation" / "tools" / "run_gate_tests.py")},
          "schemas": {}}

for cid, path in SCHEMAS.items():
    doc = yaml.safe_load(path.read_text())
    g = doc.get("genericity") or {}
    rel = closure(g)
    rows, gaps, contradictions = {}, [], []
    for pair, mstate in MY.items():
        got = rel.get(pair)
        if got is None:
            rows[f"{pair[0]}->{pair[1]}"] = {"matrix": mstate, "schema": "silent", "agrees": None}
            gaps.append(f"{pair[0]}->{pair[1]}")
            continue
        sstate = got["state"]
        # 'open' in the matrix means no unconditional implication exists. A schema that
        # declares a definite state for that pair is stricter than the matrix, not a contradiction.
        agrees = (mstate == sstate) or (mstate == "open" and sstate == "fails")
        rows[f"{pair[0]}->{pair[1]}"] = {"matrix": mstate, "schema": sstate,
                                         "provenance": got["provenance"], "agrees": agrees}
        if not agrees:
            contradictions.append({"pair": list(pair), "matrix": mstate, "schema": sstate,
                                   "provenance": got["provenance"]})
    report["schemas"][cid] = {
        "sha256": sha(path), "revision": doc.get("revision"),
        "declared_kind": g.get("kind"), "is_part_of_class": g.get("is_part_of_class"),
        "variant_strengths": {v["kind"]: v.get("statement_strength")
                              for v in (g.get("variants") or []) if isinstance(v, dict) and v.get("kind")},
        "rows": rows,
        "hard_contradictions": contradictions,
        "closure_gaps": gaps,
        "counts": {"agree": sum(1 for r in rows.values() if r.get("agrees") is True),
                   "silent": len(gaps), "contradiction": len(contradictions), "total": len(rows)},
    }

tot = {k: sum(s["counts"][k] for s in report["schemas"].values()) for k in ("agree", "silent", "contradiction", "total")}
report["summary"] = {"totals": tot,
                     "verdict": "no mathematical contradiction" if tot["contradiction"] == 0
                                else f"{tot['contradiction']} contradictions",
                     "note": "closure gaps are underspecification, not error; contradiction = schema entails the opposite of the matrix"}
OUT.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report["summary"], indent=2))
for cid, s in report["schemas"].items():
    print(f"\n{cid} rev{s['revision']} {s['sha256'][:12]} counts={s['counts']}")
    for k, r in s["rows"].items():
        if r.get("agrees") is not True:
            print(f"   GAP {k}: matrix={r['matrix']} schema={r['schema']}")
    for c in s["hard_contradictions"]:
        print("   CONTRADICTION", c)
print("\nOUT", OUT, sha(OUT))
