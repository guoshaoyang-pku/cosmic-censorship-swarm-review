#!/usr/bin/env python3
"""W043D step 2 - pre-registered durability + acceptance test for repair R2.

Repair R2 (minimal-churn): restore the *declared* consistency-evidence bytes
(sha256 675a99d0..., reproduced byte-exactly by step 1) at the canonical path and
bump FROZEN to rev29 with **only the evidence pin moved**.  No class schema byte
changes, so every hash-pinned schema verdict keeps its binding.

The test measures, on sandbox copies only:

  E1  reconstruction reaches the declared sha256 (step 1).
  E2  the owner checker artifacts/formulation/tools/check_taxonomy_consistency.py:80
      unconditionally rewrites the canonical evidence path: one run after R2 moves
      the evidence hash 675a99d0 -> 9e335e9b (R2 alone is NOT durable).
  E3  R2 + FROZEN rev29 flips the independent W043C full-schema checker to
      accept / 0 FAIL with R15 and R16 PASS (schemas untouched).
  E4  after the clobber, the same checker returns R15 FAIL again (binding destroyed).
  E5  with the checker's write redirected to a report path, two runs leave the
      declared bytes in place (675a99d0), both exit 0, and the checker still
      returns accept / 0 FAIL.
  E6  controls: mutation sensitivity, hashless evidence reopens R16, schemas
      byte-identical, FROZEN schema pins unmoved, canonical tree read-only.

Usage:  python3 durability_test.py [--root REPO]
Writes raw/*.json under the task dir.  Read-only on the shared tree.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parents[2]

F0 = "research_map/formulation_taxonomy.yaml"
F0S = "artifacts/formulation/formulation_taxonomy.yaml"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
CONS_REPORT = "artifacts/formulation/evidence/taxonomy_consistency_report.json"
FROZEN = "artifacts/formulation/FROZEN.json"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
MIRRORS = [
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
]
TOOL_CONS = "artifacts/formulation/tools/check_taxonomy_consistency.py"
CHECKER = "artifacts/worker-043/f2a_rev12_verdict/check_f2a_rev12.py"
EXTRA = [
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
] + MIRRORS

DECLARED = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LEAN = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
DECLARED_AT = "2026-09-12T00:32:02+08:00"
STALE_TOKENS = {
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_checker():
    spec = importlib.util.spec_from_file_location("w043ck", DEFAULT_ROOT / CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_sandbox(rels, prefix):
    d = Path(tempfile.mkdtemp(prefix=prefix, dir=HERE))
    for rel in rels:
        src = DEFAULT_ROOT / rel
        if src.is_file():
            dst = d / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return d


def run_tool(sandbox: Path):
    tool = sandbox / TOOL_CONS
    proc = subprocess.run(
        [sys.executable, str(tool)], capture_output=True, text=True, timeout=180
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout.strip()[:2000],
        "stderr": proc.stderr.strip()[:1000],
    }


def restore_declared(sandbox: Path, restored_bytes: bytes):
    (sandbox / CONS).write_bytes(restored_bytes)


def bump_frozen(sandbox: Path, restored_bytes: bytes, frozen_at: str):
    fz = json.loads((sandbox / FROZEN).read_text())
    before = json.loads(json.dumps(fz["files"]))
    fz["revision"] = fz.get("revision", 28) + 1
    fz["frozen_at"] = frozen_at
    fz["files"][CONS] = {
        "sha256": hashlib.sha256(restored_bytes).hexdigest(),
        "bytes": len(restored_bytes),
    }
    (sandbox / FROZEN).write_text(json.dumps(fz, indent=2) + "\n")
    moved = {k: (before[k]["sha256"], fz["files"][k]["sha256"])
             for k in fz["files"] if before.get(k, {}).get("sha256") != fz["files"][k]["sha256"]}
    return fz, moved, before


def retarget(ck, sandbox: Path, cons_sha: str | None = None):
    for rel in list(ck.TARGETS):
        p = sandbox / rel
        if p.is_file():
            ck.TARGETS[rel] = (sha(p), p.stat().st_size, ck.TARGETS[rel][2])
    if cons_sha:
        p = sandbox / CONS
        ck.TARGETS[CONS] = (cons_sha, p.stat().st_size, ck.TARGETS[CONS][2])


def summarise(res):
    return {
        "verdict": res["verdict"],
        "score": res.get("score"),
        "n_fail": res.get("n_fail"),
        "fail_ids": sorted(c["check_id"] for c in res["checks"] if c["status"] == "FAIL"),
        "R15": next(c["status"] for c in res["checks"] if c["check_id"] == "R15-consistency-binding"),
        "R16": next(c["status"] for c in res["checks"] if c["check_id"] == "R16-evidence-hash-bound"),
        "R14": next(c["status"] for c in res["checks"] if c["check_id"] == "R14-declared-gate"),
    }


def main() -> int:
    global DEFAULT_ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    args = ap.parse_args()
    DEFAULT_ROOT = Path(args.root).resolve()
    raw = HERE / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    # ---- step 1: reconstruction -------------------------------------------------
    rec_script = HERE / "reconstruct_declared_evidence.py"
    proc = subprocess.run(
        [sys.executable, str(rec_script), "--root", str(DEFAULT_ROOT), "--out", str(raw)],
        capture_output=True, text=True, timeout=120,
    )
    (raw / "reconstruct.stdout").write_text(proc.stdout)
    (raw / "reconstruct.stderr").write_text(proc.stderr)
    rec = json.loads((raw / "reconstruction.json").read_text())
    restored_bytes = (raw / "evidence_restored_675a99d0.json").read_bytes()
    E1 = (
        proc.returncode == 0
        and rec["reconstruction_matches_declared"]
        and hashlib.sha256(restored_bytes).hexdigest() == DECLARED
    )

    # ---- canonical pins before --------------------------------------------------
    pins_before = {rel: sha(DEFAULT_ROOT / rel) for rel in
                   [F0, F0S, CONS, FROZEN, TOOL_CONS] + SCHEMAS + MIRRORS}
    canonical_lean = pins_before[CONS] == LEAN

    steps = []

    # ---- E2: baseline clobber ---------------------------------------------------
    sbx_b = build_sandbox(list(load_checker().TARGETS) + EXTRA, "w043d_clobber_")
    restore_declared(sbx_b, restored_bytes)
    e2_before = sha(sbx_b / CONS)
    e2_run = run_tool(sbx_b)
    e2_after = sha(sbx_b / CONS)
    E2 = e2_before == DECLARED and e2_after == LEAN and e2_run["rc"] == 0
    steps.append({
        "id": "E2-owner-checker-clobbers-canonical-evidence",
        "status": "CONFIRMED" if E2 else "UNEXPECTED",
        "detail": (
            "check_taxonomy_consistency.py:80 unconditional write: one run rewrites the "
            "canonical evidence path with the pin-free document; the declared 675a99d0 bytes "
            "do not survive a verification run."
        ),
        "evidence": {
            "sandbox_before_sha256": e2_before,
            "sandbox_after_sha256": e2_after,
            "tool_rc": e2_run["rc"],
            "tool_stdout": e2_run["stdout"][:200],
            "tool_sha256": sha(DEFAULT_ROOT / TOOL_CONS),
        },
    })

    # ---- instrument validation on pristine sandbox ------------------------------
    sbx_c = build_sandbox(list(load_checker().TARGETS) + EXTRA, "w043d_instr_")
    ck0 = load_checker()
    instrument = ck0.selftest(sbx_c)
    (raw / "instrument_selftest.json").write_text(json.dumps(instrument, indent=2) + "\n")

    # ---- E3: R2 repair -> accept ------------------------------------------------
    sbx = build_sandbox(list(load_checker().TARGETS) + EXTRA, "w043d_r2_")
    restore_declared(sbx, restored_bytes)
    fz, moved, fz_before = bump_frozen(sbx, restored_bytes, "2026-09-12T00:50:00+08:00")
    ck = load_checker()
    retarget(ck, sbx)
    res_r2 = ck.run_checks(sbx)
    s_r2 = summarise(res_r2)
    E3 = s_r2["verdict"] == "accept" and s_r2["n_fail"] == 0 and s_r2["R15"] == "PASS" and s_r2["R16"] == "PASS"
    schema_bytes_unchanged = all(sha(sbx / r) == pins_before[r] for r in SCHEMAS)
    steps.append({
        "id": "E3-R2-plus-refreeze-flips-independent-checker-to-accept",
        "status": "PASS" if E3 else "FAIL",
        "detail": (
            "declared bytes restored at the canonical path + FROZEN rev29 (only the evidence "
            "pin moved): independent W043C and F2a content checks accept with 0 FAIL."
        ),
        "evidence": {
            "sandbox_evidence_sha256": sha(sbx / CONS),
            "frozen_revision": fz["revision"],
            "frozen_pins_moved": moved,
            "schemas_byte_identical_to_canonical": schema_bytes_unchanged,
            "checker": s_r2,
        },
    })

    # ---- E4: R2 alone is not durable -------------------------------------------
    e4_before = sha(sbx / CONS)
    e4_run = run_tool(sbx)
    e4_after = sha(sbx / CONS)
    ck2 = load_checker()
    retarget(ck2, sbx, cons_sha=e4_after)
    res_clob = ck2.run_checks(sbx)
    s_clob = summarise(res_clob)
    E4 = e4_before == DECLARED and e4_after == LEAN and s_clob["R15"] == "FAIL"
    steps.append({
        "id": "E4-R2-alone-not-durable",
        "status": "CONFIRMED" if E4 else "UNEXPECTED",
        "detail": (
            "after one owner-checker run the evidence hash is back to 9e335e9b and the "
            "declared binding fails again (R15 FAIL): restoring bytes without fixing the "
            "writer does not hold."
        ),
        "evidence": {
            "evidence_before_sha256": e4_before,
            "evidence_after_sha256": e4_after,
            "tool_rc": e4_run["rc"],
            "checker_after_clobber": s_clob,
        },
    })

    # ---- E5: durability patch ---------------------------------------------------
    restore_declared(sbx, restored_bytes)
    orig_tool = (DEFAULT_ROOT / TOOL_CONS).read_text()
    patch_old = (
        'out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\n'
        'out.write_text(json.dumps(rep, indent=2)+"\\n")'
    )
    patch_new = (
        'report = ROOT/"artifacts/formulation/evidence/taxonomy_consistency_report.json"\n'
        'report.write_text(json.dumps(rep, indent=2)+"\\n")'
    )
    assert patch_old in orig_tool, "canonical checker changed; patch anchor not found"
    patched = orig_tool.replace(patch_old, patch_new)
    (HERE / "patched_check_taxonomy_consistency.py").write_text(patched)
    import difflib
    diff = "".join(difflib.unified_diff(
        orig_tool.splitlines(keepends=True), patched.splitlines(keepends=True),
        fromfile="a/" + TOOL_CONS, tofile="b/" + TOOL_CONS,
    ))
    (HERE / "durability.patch").write_text(diff)
    (sbx / TOOL_CONS).write_text(patched)
    runs = []
    for _ in range(2):
        r = run_tool(sbx)
        runs.append({"rc": r["rc"], "stdout": r["stdout"][:200],
                     "evidence_sha256": sha(sbx / CONS),
                     "report_exists": (sbx / CONS_REPORT).is_file()})
    ck3 = load_checker()
    retarget(ck3, sbx)
    res_final = ck3.run_checks(sbx)
    s_final = summarise(res_final)
    E5 = (
        all(r["rc"] == 0 and r["evidence_sha256"] == DECLARED and r["report_exists"] for r in runs)
        and s_final["verdict"] == "accept" and s_final["n_fail"] == 0
    )
    steps.append({
        "id": "E5-durability-patch-holds-declared-bytes-and-accept",
        "status": "PASS" if E5 else "FAIL",
        "detail": (
            "checker write redirected to taxonomy_consistency_report.json: two consecutive "
            "verification runs leave 675a99d0 in place and the independent checker still "
            "accepts with 0 FAIL."
        ),
        "evidence": {
            "patch": diff.strip().splitlines(),
            "patched_sha256": sha(HERE / "patched_check_taxonomy_consistency.py"),
            "runs": runs,
            "checker_final": s_final,
        },
    })

    # ---- E6: controls -----------------------------------------------------------
    # K2: hashless evidence reopens R16
    lean_from_bound = (json.dumps(
        {k: v for k, v in json.loads(restored_bytes).items()
         if k not in ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at")},
        indent=2) + "\n").encode()
    (sbx / CONS).write_bytes(lean_from_bound)
    ck4 = load_checker()
    retarget(ck4, sbx, cons_sha=hashlib.sha256(lean_from_bound).hexdigest())
    res_hashless = ck4.run_checks(sbx)
    s_hashless = summarise(res_hashless)
    K2 = s_hashless["R16"] == "FAIL"
    restore_declared(sbx, restored_bytes)

    frozen_schema_pins_equal = all(
        fz["files"][r]["sha256"] == fz_before[r]["sha256"] for r in SCHEMAS
    )
    K4 = frozen_schema_pins_equal and set(moved) == {CONS}
    pins_after = {rel: sha(DEFAULT_ROOT / rel) for rel in pins_before}
    K5 = pins_after == pins_before

    controls = {
        "K1_reconstruction_is_hash_sensitive": all(rec["controls"].values()),
        "K2_hashless_evidence_reopens_R16": K2,
        "K3_schemas_byte_identical_under_R2": schema_bytes_unchanged,
        "K4_only_evidence_pin_moved_in_frozen": K4,
        "K5_canonical_tree_read_only": K5,
    }
    steps.append({
        "id": "E6-controls",
        "status": "PASS" if all(controls.values()) and instrument.get("controls_pass") else "FAIL",
        "detail": "instrument self-test 8/8 plus five outcome controls",
        "evidence": {
            "controls": controls,
            "instrument_controls_pass": instrument.get("controls_pass"),
            "hashless_checker": s_hashless,
            "frozen_moved": moved,
            "canonical_drift": [r for r in pins_before if pins_after[r] != pins_before[r]],
        },
    })

    # ---- verdict ----------------------------------------------------------------
    expectations = {
        "E1_reconstruction_matches_declared": E1,
        "E2_owner_checker_clobbers": E2,
        "E3_R2_accept": E3,
        "E4_R2_not_durable": E4,
        "E5_patch_durable_accept": E5,
        "E6_controls": steps[-1]["status"] == "PASS",
    }
    report = {
        "task_id": "W043D-R2-DURABILITY-01",
        "worker": "worker-043",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["F2a", "F1", "F2b", "F0"],
        "gate": "G-FORM",
        "generated_at": __import__("datetime").datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "root": str(DEFAULT_ROOT),
        "authority": "measurement only; no canonical file written; no gate verdict; no review verdict",
        "pins_before": pins_before,
        "canonical_evidence_is_lean": canonical_lean,
        "declared_sha256": DECLARED,
        "lean_sha256": LEAN,
        "declared_generation": DECLARED_AT,
        "expected_outcomes": expectations,
        "steps": steps,
        "verdict": "accept_for_repair_R2" if all(expectations.values()) else "inconclusive",
        "repair_R2": {
            "what": (
                "restore the declared 675a99d0 evidence bytes at "
                "artifacts/formulation/evidence/taxonomy_consistency.json (no class-schema edit), "
                "bump FROZEN rev29 moving only the evidence pin, and redirect the checker's "
                "unconditional write (check_taxonomy_consistency.py:80) to "
                "taxonomy_consistency_report.json"
            ),
            "why_minimal": (
                "schema bytes do not change, so every hash-pinned schema verdict keeps its "
                "binding; the churn of a schema re-stamp (R1) is avoided"
            ),
            "patch": "durability.patch",
            "ordering": "restore bytes -> bump FROZEN -> patch writer; never run the unpatched checker afterwards",
        },
        "next_falsifier": (
            "At the repaired pins, run the patched checker twice and the independent W043C "
            "checker once: the repair fails if the canonical evidence hash moves off 675a99d0, "
            "if FROZEN moves any pin other than the evidence pin, if any schema byte changes, "
            "or if R15/R16 do not both PASS."
        ),
        "non_claims": [
            "no canonical file is written by this task; R2 is an owner-applied proposal",
            "not a gate verdict and not a review verdict on any class schema",
            "does not adjudicate worker-047 C06/C07 (taxonomy conclusion-text pair_(s,delta) vs "
            "schema index_r binder); that item remains open for F0/formulation",
            "R2 repairs the binding axis only; it does not re-open or close any content finding",
            "the sandbox FROZEN rev29 carries a synthetic frozen_at and must be re-issued by the "
            "owner at wall-clock adoption time with only the evidence pin moved",
        ],
        "canonical_drift_after": {r: (pins_before[r], pins_after[r])
                                  for r in pins_before if pins_after[r] != pins_before[r]},
    }
    acceptance = {
        "task_id": report["task_id"],
        "pre_registered_outcomes": expectations,
        "acceptance": "PASS" if all(expectations.values()) else "FAIL",
        "invariant": (
            "canonical schemas byte-identical (F1 cce9c60146d6 / F2a 5476a3f2c6bc / "
            "F2b 55d0a1ea9bda); evidence path = 675a99d0; FROZEN rev29 moves only the "
            "evidence pin; one patched-checker run cannot move the evidence hash"
        ),
        "independent_checker_verdicts": {
            "R2_plus_refreeze": s_r2,
            "after_unpatched_checker_run": s_clob,
            "R2_plus_refreeze_plus_durability_patch": s_final,
        },
        "instrument_controls_pass": bool(instrument.get("controls_pass")),
    }
    (raw / "acceptance.json").write_text(json.dumps(acceptance, indent=2) + "\n")
    (HERE / "acceptance.json").write_text(json.dumps(acceptance, indent=2) + "\n")
    (raw / "durability_report.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"], "expectations": expectations}, indent=1))
    return 0 if all(expectations.values()) else 2


if __name__ == "__main__":
    sys.exit(main())
