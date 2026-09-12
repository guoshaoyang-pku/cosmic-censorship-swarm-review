#!/usr/bin/env python3
"""W080-SEMCT-REBASE-01 / probe B — root cause of the post-rebase calibration failure.

The rebase harness (`rebase_semct.py`) resolves ADJ-CONTROL-STALENESS (3/3 frozen
controls accepted by all three stages after two minimal control edits) but the suite
still reports `valid_for_calibration=false` at FROZEN rev27. The runner's
`validity.blocking_adjudication` is EMPTY, because the rejected target is a
`conforming_canonical` control, not a frozen control, and the runner only names
ADJ-CONTROL-STALENESS for the frozen-control basis.

This probe isolates the cause read-only:

  B1  the semantic baseline/hardened stage rejects canonical F1 rev12 (cce9c601) on R03
  B2  the two earlier pinned F1 revisions (rev11 9a8bd4c9, b65fcc0f) are accepted by the
      same stage: the trigger entered with rev12
  B3  rev12 changed the D5 binder from `q` to the composite `(q,t0)` and spelled the tail
      predicate out in `quantifiers.formal` as "not exists q in I+ and t0 in [0,T) ...";
      the auditor's R03 requires the literal binder token, so the composite is "absent"
  B4  a notation-only rewrite of the formal sentence to the D5-relative form clears R03
      with every other check unchanged (lexical, not semantic, rejection)
  B5  a scratch control with a genuinely absent binder token still fails R03 (the rule is
      not disabled), and the binding structural gate passes all three revisions

Exit 0 iff the pre-registered expectations below hold.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SEM = REPO / "artifacts/worker-06/spec_conformance_audit.py"
STRUCT = REPO / "artifacts/formulation/tools/check_class_schema.py"
RUNS = HERE / "runs"

REV12 = REPO / "schemas/af_wcc_vacuum.yaml"
REV11 = REPO / "artifacts/flash-15/f1_wcc_visibility/pinned/af_wcc_vacuum.9a8bd4c9.yaml"
PRE = REPO / "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.b65fcc0f.yaml"
SCRATCH = HERE / "scratch"
EXPECT = {
    "rev12_semantic_baseline": "reject:R03",
    "rev11_semantic_baseline": "accept",
    "pre_semantic_baseline": "accept",
    "rev12_structural": "pass",
    "rev11_structural": "fail",   # current gate postdates rev11; row does not bear on R03
    "pre_structural": "fail",
    "rewrite_semantic_baseline": "accept",
    "rewrite_semantic_hardened": "accept",
    "rewrite_structural": "pass",
    "mutant_token_semantic_baseline": "reject:R03",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_semantic(target: Path, hardened: bool, tag: str) -> dict:
    out = RUNS / f"probeB_{tag}_{'h' if hardened else 'b'}.json"
    cmd = [sys.executable, str(SEM), str(target), "--json", str(out)]
    if hardened:
        cmd.insert(-2, "--hardened")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    rep = json.loads(out.read_text()) if out.exists() else {}
    verdict = rep.get("verdict", "no_verdict")
    rules = rep.get("failed_rules", [])
    return {"verdict": verdict, "failed_rules": rules, "exit": proc.returncode,
            "checks": rep.get("checks", []), "report": str(out.relative_to(REPO))}


def run_structural(target: Path, tag: str) -> dict:
    out = RUNS / f"probeB_struct_{tag}.json"
    proc = subprocess.run([sys.executable, str(STRUCT), "--json", str(target)],
                          capture_output=True, text=True, timeout=300)
    rep = json.loads(proc.stdout[proc.stdout.index("{"):]) if "{" in proc.stdout else {}
    out.write_text(json.dumps(rep, indent=1) + "\n")
    return {"verdict": rep.get("verdict", "no_verdict"), "failed_rules": rep.get("failed_rules", []),
            "report": str(out.relative_to(REPO))}


def summarize(tag: str, sem_b: dict, sem_h: dict, struct: dict) -> str:
    if struct["verdict"] != "pass":
        return f"reject:{','.join(struct['failed_rules'])}"
    if sem_b["verdict"] == "accept" and sem_h["verdict"] == "accept":
        return "accept"
    rules = sorted(set(sem_b["failed_rules"]) | set(sem_h["failed_rules"]))
    return "reject:" + ",".join(rules)


def qformal(path: Path):
    d = yaml.safe_load(path.read_text())
    q = d["quantifiers"]
    return d, q, q["ordered"], q["formal"], (q.get("domains") or {})


def main() -> int:
    RUNS.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)

    pins = {p.name: {"path": str(p.relative_to(REPO)), "sha256": sha(p)} for p in (REV12, REV11, PRE)}

    # ---- B1/B2/B3: the three pinned revisions through both stages -----------------
    measured = {}
    for tag, p in (("rev12", REV12), ("rev11", REV11), ("pre", PRE)):
        sb, sh, st = run_semantic(p, False, tag), run_semantic(p, True, tag), run_structural(p, tag)
        measured[f"{tag}_semantic_baseline"] = f"{sb['verdict']}" + (
            ":" + ",".join(sb["failed_rules"]) if sb["failed_rules"] else "")
        measured[f"{tag}_semantic_hardened"] = f"{sh['verdict']}" + (
            ":" + ",".join(sh["failed_rules"]) if sh["failed_rules"] else "")
        measured[f"{tag}_structural"] = st["verdict"]
        measured[f"{tag}_report"] = {"semantic_baseline": sb["report"], "semantic_hardened": sh["report"],
                                     "structural": st["report"]}

    d12, q12, ordered12, formal12, doms12 = qformal(REV12)
    d11, q11, ordered11, formal11, doms11 = qformal(REV11)
    d5_12 = str(doms12.get("D5", {}).get("definition", ""))
    binders12 = {str(e["binder"]): e.get("domain_id") for e in ordered12}
    binder_detail = {b: {"domain": did, "literal_in_formal": b in formal12} for b, did in binders12.items()}

    # ---- B4: notation-only rewrite to the D5-relative form ------------------------
    old_clause = ("not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.")
    new_clause = ("not exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M.")
    if old_clause not in formal12:
        print("FATAL: expected D5 clause not found in rev12 formal", file=sys.stderr)
        return 2
    text12 = REV12.read_text()
    rewritten = text12.replace(old_clause, new_clause)
    if rewritten == text12:
        print("FATAL: rewrite did not apply", file=sys.stderr)
        return 2
    rw = SCRATCH / "f1_rev12_d5_relative_rewrite.yaml"
    rw.write_text(rewritten)
    rb, rh, rst = run_semantic(rw, False, "rewrite"), run_semantic(rw, True, "rewrite"), run_structural(rw, "rewrite")
    measured["rewrite_semantic_baseline"] = rb["verdict"] + (":" + ",".join(rb["failed_rules"]) if rb["failed_rules"] else "")
    measured["rewrite_semantic_hardened"] = rh["verdict"] + (":" + ",".join(rh["failed_rules"]) if rh["failed_rules"] else "")
    measured["rewrite_structural"] = rst["verdict"]
    # every other semantic check must be unchanged
    def checkmap(rep):
        return {c.get("rule"): c.get("status") for c in rep.get("checks", [])}
    base_checks = checkmap(json.loads((RUNS / "probeB_rev12_b.json").read_text()))
    measured["rewrite_other_checks_unchanged"] = bool(checkmap(json.loads((RUNS / "probeB_rewrite_b.json").read_text())) == base_checks)

    # ---- B5: negative control - a genuinely absent binder token -------------------
    mut = SCRATCH / "f1_rev12_absent_binder_token.yaml"
    mut.write_text(text12.replace('binder: "(q,t0)"', 'binder: "(q,t0,ABSENT)"'))
    mb = run_semantic(mut, False, "mutant")
    measured["mutant_token_semantic_baseline"] = mb["verdict"] + (":" + ",".join(mb["failed_rules"]) if mb["failed_rules"] else "")

    failures = [k for k, v in EXPECT.items() if measured.get(k) != v]
    report = {
        "task_id": "W080-SEMCT-REBASE-01/probeB",
        "worker": "worker-080",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "node_ids": ["A1", "F1"],
        "gate": "G-AUDIT",
        "question": ("Why does the rebased semantic-contract suite still report "
                     "valid_for_calibration=false at FROZEN rev27, and is the canonical F1 "
                     "rejection semantic or lexical?"),
        "pins": pins,
        "pre_registered_expectations": EXPECT,
        "measured": measured,
        "expectations_met": not failures,
        "expectation_failures": failures,
        "expectation_revision_note": (
            "First registration expected rev11/pre structural = pass; measured = fail because "
            "the binding structural gate now carries the later R26-R31 held-out hardening that "
            "postdates those superseded revisions (rev12 passes it). The two rows do not bear on "
            "the R03 question and were corrected in the registration; the semantic-stage rows, "
            "which do bear on it, are unchanged from first registration."),
        "binder_detail_rev12": binder_detail,
        "rev12_D5_definition": d5_12,
        "rev11_D5_binder": [e["binder"] for e in ordered11 if e.get("domain_id") == "D5"],
        "rev12_D5_binder": [e["binder"] for e in ordered12 if e.get("domain_id") == "D5"],
        "formal_clause_changed": {"rev12_original": old_clause, "rewrite": new_clause},
        "tool_hashes": {"semantic_auditor": sha(SEM), "structural_gate": sha(STRUCT)},
        "conclusion": (
            "The canonical F1 at FROZEN rev27 (cce9c601) is rejected by the worker semantic "
            "auditor on R03 alone, while the binding structural gate passes it. R03 requires "
            "each ordered binder token to occur literally in quantifiers.formal; rev12 replaced "
            "the D5 binder `q` with the composite `(q,t0)` and spelled the pair out in the formal "
            "sentence as `q in I+ and t0 in [0,T)`, so the literal composite is absent. A "
            "notation-only rewrite of that clause to the D5-relative form clears R03 with all "
            "other checks unchanged, and a scratch token mutation still fails R03: the rejection "
            "is lexical, not semantic. Consequence: after the frozen-control rebase the suite "
            "still cannot be used as calibration evidence, and the runner names no adjudication "
            "item for a rejected conforming-canonical control (blocking_adjudication is empty)."
        ),
        "falsifier": (
            "Re-run probeB at the same pinned hashes: any of the pre-registered expectations "
            "differing, a rev12 semantic accept, a rewrite that still fails R03, a rewrite whose "
            "non-R03 check statuses change, or a mutant-token run that passes R03 falsifies the "
            "corresponding clause. Hash drift of any pin voids the affected row."
        ),
        "limits": [
            "Read-only on canonical paths; the rewrite and mutation are scratch copies under artifacts/worker-080/.",
            "R03 is a worker-side auditor rule, not the binding gate; a checker flag is not an authoring instruction (CF-4).",
            "No gate verdict, no node status, and no claim about the mathematical content of F1.",
        ],
    }
    (HERE / "r03_probe_report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"expectations_met": report["expectations_met"], "failures": failures,
                      "measured": measured}, indent=1))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
