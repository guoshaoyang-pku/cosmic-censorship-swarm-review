#!/usr/bin/env python3
"""W059-F0-ADJUDICATE-01 tooling blind-spot test.

Question: does artifacts/formulation/tools/check_taxonomy_consistency.py detect a D3
regression in AF-WCC-SCALAR-SPH's conclusion text (the class its line-59 D3 branch
does not name), or does it certify CONSISTENT?

Three trees are built from the pinned canonical F0 snapshot and the authoring mirror:
  tree0 control          : pristine bytes                     -> expect CONSISTENT
  tree1 scalar-mutant    : scalar conclusion loses genericity -> expect detection (D3)
  tree2 covered-mutant   : C2/C0 loss of 'comeager'           -> positive control for
                           the D3 branch (must be detected), proving tree1's result is
                           a coverage gap and not a dead instrument.

Each run uses its own copy of the tool so ROOT resolves inside that tree; the tool's
already-written evidence file is read back and hashed. No canonical artifact is touched.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SNAP = ROOT / "artifacts/worker-059/f0_adjudication/snapshot/f0.276009f4f63d.yaml"
AUTHORING = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
TOOL = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
WORK = ROOT / "artifacts/worker-059/f0_adjudication/blindspot_test"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build_tree(name: str, taxonomy_text: str) -> Path:
    tree = WORK / name
    if tree.exists():
        shutil.rmtree(tree)
    (tree / "research_map").mkdir(parents=True)
    (tree / "artifacts/formulation/tools").mkdir(parents=True)
    (tree / "artifacts/formulation/evidence").mkdir(parents=True)
    (tree / "research_map/formulation_taxonomy.yaml").write_text(taxonomy_text)
    shutil.copy(AUTHORING, tree / "artifacts/formulation/formulation_taxonomy.yaml")
    shutil.copy(ALIASES, tree / "artifacts/formulation/VOCAB_ALIASES.json")
    shutil.copy(TOOL, tree / "artifacts/formulation/tools/check_taxonomy_consistency.py")
    return tree


def run(tree: Path) -> dict:
    p = subprocess.run(
        [sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"],
        cwd=tree, capture_output=True, text=True,
    )
    ev = tree / "artifacts/formulation/evidence/taxonomy_consistency.json"
    return {
        "exit_code": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip()[-500:],
        "evidence_written": ev.exists(),
        "evidence_sha256": sha(ev) if ev.exists() else None,
        "evidence_consistent": (json.loads(ev.read_text()).get("consistent") if ev.exists() else None),
        "evidence_divergences": (json.loads(ev.read_text()).get("contract_divergences") if ev.exists() else None),
    }


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    base = SNAP.read_text()

    # mutation 1: scalar conclusion loses explicit quantifier AND equivalence becomes plain claim
    old_scalar = (
        "        For generic data in the class, the MGHD admits I+ and every future-inextendible causal\n"
        "        geodesic contained in J-(I+) is complete; equivalently, the singularities that form are\n"
        "        hidden behind an event horizon and no singularity is visible from I+.\n"
    )
    assert old_scalar in base, "scalar conclusion block not found verbatim"
    scalar_mutant = base.replace(
        old_scalar,
        "        For every data set in the class, the MGHD admits I+.\n",
    )

    # mutation 2: positive control — remove every 'comeager' occurrence from the C2/C0
    # conclusion texts and put the old ambiguous phrase into the C0 text, so the tool's
    # own line-59 D3 branch must fire.
    covered_mutant = base.replace("comeager", "typical")
    c0_line = "        data set in G_{s,delta}, the MGHD is future-inextendible as a C0 (continuous-metric)"
    assert c0_line in covered_mutant, "C0 conclusion line not found verbatim"
    covered_mutant = covered_mutant.replace(
        c0_line,
        "        data set in the class, the MGHD is future-inextendible as a C0 (continuous-metric)",
    )

    trees = {
        "tree0_control": base,
        "tree1_scalar_mutant": scalar_mutant,
        "tree2_covered_mutant_positive_control": covered_mutant,
    }
    out = {"canonical_snapshot_sha256": sha(SNAP), "tool": str(TOOL), "tool_sha256": sha(TOOL), "runs": {}}
    for name, text in trees.items():
        tree = build_tree(name, text)
        res = run(tree)
        res["mutated_taxonomy_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        out["runs"][name] = res
        print(name, "->", res["exit_code"], res["stdout"])

    t1 = out["runs"]["tree1_scalar_mutant"]
    t2 = out["runs"]["tree2_covered_mutant_positive_control"]

    # static coverage: which class ids does the tool's D3 branch name, and is the scalar
    # conclusion text ever passed to ctext() at all?
    import ast
    src = TOOL.read_text()
    tree_ast = ast.parse(src)
    frozen = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
    ctext_args: set[str] = set()
    d3_cids: list[str] = []
    for node in ast.walk(tree_ast):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "ctext":
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    ctext_args.add(a.value)
        if isinstance(node, ast.If):
            seg = ast.get_source_segment(src, node.test) or ""
            if "for every data set in the class" in seg:
                d3_cids = [c for c in frozen if c in seg]
    out["static_tool_analysis"] = {
        "d3_branch_line": next(
            (i + 1 for i, l in enumerate(src.splitlines())
             if "for every data set in the class" in l and "ctext(" in l), None),
        "class_ids_named_in_d3_condition": d3_cids,
        "all_class_ids_passed_to_ctext_anywhere": sorted(ctext_args & set(frozen)),
        "scalar_class_conclusion_ever_inspected": "AF-WCC-SCALAR-SPH" in ctext_args,
        "frozen_classes": frozen,
    }
    out["conclusion"] = {
        "blind_spot_reproduced": bool(t1["exit_code"] == 0 and t1["evidence_consistent"] is True),
        "instrument_positive_control_fires": bool(t2["exit_code"] != 0 and t2["evidence_consistent"] is False),
        "scalar_class_not_named_in_d3_condition": "AF-WCC-SCALAR-SPH" not in d3_cids,
        "scalar_conclusion_never_inspected_statically": "AF-WCC-SCALAR-SPH" not in ctext_args,
        "interpretation": (
            "the D3 branch detects a C2/C0 regression (positive control) but certifies the identical "
            "regression in AF-WCC-SCALAR-SPH as CONSISTENT, because its class tuple covers only the "
            "C2/C0 pair and the scalar conclusion text is never compared"
        ),
    }
    (WORK / "blindspot_result.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["conclusion"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
