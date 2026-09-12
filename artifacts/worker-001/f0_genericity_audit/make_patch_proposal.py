#!/usr/bin/env python3
"""Reproducible patch PROPOSAL for the F0 genericity two-slot findings.

Does NOT modify any canonical artifact. Reads the pinned canonical taxonomy and the pinned
class-contract supplement, applies the minimal coupled fix into proposed_*.yaml, emits unified
diffs, and MEASURES the consistency-gate coupling in an isolated sandbox (three arms).

The patch is withheld from the canonical paths because the artifacts are FROZEN rev28 and the
formulation lead owns revision bumps (FROZEN.json change_protocol). It is a proposal with
evidence, not a worker edit.

Measured facts that shaped the proposal:
  * adding genericity_topology to class axes PASSES validate_taxonomy.py 253/253 unchanged
    (the suite does not inspect class axes keys at all);
  * changing the scalar kind without the supplement makes check_taxonomy_consistency.py FAIL
    with "AF-WCC-SCALAR-SPH: genericity residual_comeager vs unresolved", so the two files
    must land together.

The scalar class's `genericity_value_status: unresolved_pending_L1` and its H4 remain the
carriers of the unresolved topology; only the KIND slot is corrected.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CANON = ROOT / "research_map" / "formulation_taxonomy.yaml"
SUPPL = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
ALIASES = ROOT / "artifacts" / "formulation" / "VOCAB_ALIASES.json"
CHECKER = ROOT / "artifacts" / "formulation" / "tools" / "check_taxonomy_consistency.py"

CANON_PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
SUPPL_PIN = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"

OUTDIR = Path(__file__).resolve().parent
SANDBOX = OUTDIR / "consistency_sandbox"

SCALAR = "AF-WCC-SCALAR-SPH"
CLASS_HEADER = re.compile(r'^  "([A-Z0-9\-]+)":\s*$', re.MULTILINE)


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def patch_canonical(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    old_scalar = '      genericity_kind: "unresolved"\n'
    if text.count(old_scalar) != 1:
        raise SystemExit(f"anchor count {text.count(old_scalar)} != 1 for scalar kind")
    text = text.replace(
        old_scalar,
        '      genericity_kind: "provisional_baire_residual"\n'
        '      genericity_topology: "unresolved"\n')
    notes.append(f"{SCALAR}: genericity_kind unresolved -> provisional_baire_residual; "
                 "genericity_topology: unresolved added")

    for cid in ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"):
        start = re.search(rf'^  "{re.escape(cid)}":\s*$', text, re.MULTILINE)
        if not start:
            raise SystemExit(f"class header not found: {cid}")
        nxt = CLASS_HEADER.search(text, start.end())
        end = nxt.start() if nxt else len(text)
        block = text[start.start():end]
        anchor = '      genericity_kind: "provisional_baire_residual"\n'
        if block.count(anchor) != 1:
            raise SystemExit(f"anchor count {block.count(anchor)} != 1 in {cid}")
        block2 = block.replace(anchor, anchor + '      genericity_topology: "unresolved"\n')
        text = text[:start.start()] + block2 + text[end:]
        notes.append(f"{cid}: genericity_topology: unresolved added")
    return text, notes


def patch_supplement(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    old = "AF-WCC-SCALAR-SPH: unresolved}"
    if text.count(old) != 1:
        raise SystemExit(f"supplement frozen anchor count {text.count(old)} != 1")
    text = text.replace(old, "AF-WCC-SCALAR-SPH: residual_comeager}")
    notes.append("axis_registry.genericity_axis.frozen[AF-WCC-SCALAR-SPH]: unresolved -> residual_comeager")

    old_note = "its genericity notion is left UNRESOLVED and owned by that future node"
    new_note = ("its genericity kind is provisional_baire_residual, fixed by the comeager set its "
                "conclusion asserts, while its topology and value status are left unresolved and "
                "owned by that future node")
    if text.count(old_note) != 1:
        raise SystemExit(f"supplement scalar_note anchor count {text.count(old_note)} != 1")
    text = text.replace(old_note, new_note)
    notes.append("scalar_note: stale 'notion is left UNRESOLVED' corrected to name the kind/topology split")
    return text, notes


def unified(a: str, b: str, rel: str) -> str:
    return "".join(difflib.unified_diff(
        a.splitlines(keepends=True), b.splitlines(keepends=True),
        fromfile=f"a/{rel}", tofile=f"b/{rel}"))


def run_consistency_arm(canon_text: str, suppl_text: str) -> dict:
    """Install a 3-file sandbox and run the committed checker; return its verdict."""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "research_map").mkdir(parents=True)
    (SANDBOX / "artifacts" / "formulation" / "tools").mkdir(parents=True)
    (SANDBOX / "artifacts" / "formulation" / "evidence").mkdir(parents=True)
    (SANDBOX / "research_map" / "formulation_taxonomy.yaml").write_text(canon_text)
    (SANDBOX / "artifacts" / "formulation" / "formulation_taxonomy.yaml").write_text(suppl_text)
    shutil.copy(ALIASES, SANDBOX / "artifacts" / "formulation" / "VOCAB_ALIASES.json")
    shutil.copy(CHECKER, SANDBOX / "artifacts" / "formulation" / "tools" /
                "check_taxonomy_consistency.py")
    proc = subprocess.run(
        [sys.executable, str(SANDBOX / "artifacts" / "formulation" / "tools" /
                             "check_taxonomy_consistency.py")],
        capture_output=True, text=True)
    errs = []
    ev = SANDBOX / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
    if ev.is_file():
        errs = json.loads(ev.read_text()).get("errors", [])
    return dict(exit_code=proc.returncode, stdout=proc.stdout.strip(), errors=errs)


def main() -> int:
    canon_raw = CANON.read_text()
    suppl_raw = SUPPL.read_text()
    if hashlib.sha256(canon_raw.encode()).hexdigest() != CANON_PIN:
        print("FAIL-CLOSED: canonical hash != pinned rev5", file=sys.stderr)
        return 3
    if hashlib.sha256(suppl_raw.encode()).hexdigest() != SUPPL_PIN:
        print("FAIL-CLOSED: supplement hash != pinned", file=sys.stderr)
        return 3

    canon_new, n1 = patch_canonical(canon_raw)
    suppl_new, n2 = patch_supplement(suppl_raw)
    (OUTDIR / "proposed_formulation_taxonomy.yaml").write_text(canon_new)
    (OUTDIR / "proposed_formulation_taxonomy_supplement.yaml").write_text(suppl_new)
    (OUTDIR / "patch_proposal.diff").write_text(unified(
        canon_raw, canon_new, "research_map/formulation_taxonomy.yaml"))
    (OUTDIR / "patch_proposal_supplement.diff").write_text(unified(
        suppl_raw, suppl_new, "artifacts/formulation/formulation_taxonomy.yaml"))

    arms = {
        "A_current_pair": run_consistency_arm(canon_raw, suppl_raw),
        "B_canonical_only": run_consistency_arm(canon_new, suppl_raw),
        "C_coupled_fix": run_consistency_arm(canon_new, suppl_new),
    }
    evidence = dict(
        audit="F0 genericity patch-proposal coupling",
        worker="worker-001", node_id="F0", class_id=SCALAR,
        pinned={"canonical": CANON_PIN, "supplement": SUPPL_PIN},
        proposed={"canonical": sha256_text(canon_new), "supplement": sha256_text(suppl_new)},
        canonical_notes=n1, supplement_notes=n2,
        consistency_arms=arms,
        conclusion=("the coupled fix is required and sufficient for the consistency gate: "
                    "canonical-only fails arm B; A and C pass"),
        not_applied=True,
    )
    (OUTDIR / "coupling_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")

    print(f"base_canonical_sha256      {CANON_PIN}")
    print(f"proposed_canonical_sha256  {sha256_text(canon_new)}")
    print(f"base_supplement_sha256     {SUPPL_PIN}")
    print(f"proposed_supplement_sha256 {sha256_text(suppl_new)}")
    for n in n1 + n2:
        print("  -", n)
    for name, a in arms.items():
        print(f"  arm {name}: exit={a['exit_code']} errors={a['errors']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
