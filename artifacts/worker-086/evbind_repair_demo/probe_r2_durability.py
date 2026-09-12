#!/usr/bin/env python3
"""W086-GFORM-R2-DURABILITY-01 — R2 restore durability probe + writer-guard candidate.

Bounded class-bound worker task, worker-086.  Gate G-FORM, nodes F1/F2a/F2b,
classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN.

Question: worker-092 adjudicated repair path R2 (restore the declared evidence
bytes 675a99d0 at the canonical path) and recorded that R2 is durable only if
the standalone checker stops writing the canonical path.  This probe measures
that claim under a sandbox that mirrors ROOT, with the live repository treated
read-only, and produces a minimal non-writing guard candidate.

Run:  python3 artifacts/worker-086/evbind_repair_demo/probe_r2_durability.py
Exit: 0 all checks pass; 1 check failure; 2 moving target / fail-closed.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ART = Path(__file__).resolve().parent
REPO = ART.parents[2]
SANDBOX = ART / "sandbox"
DECLARED = REPO / "artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json"
PINNED_CHECKER = REPO / "artifacts/formulation/tools/check_taxonomy_consistency.py"
GUARDED_CHECKER = ART / "check_taxonomy_consistency.guarded.py"
GUARDED_REL = "artifacts/formulation/tools/check_taxonomy_consistency.guarded.py"
CANON_EVIDENCE = REPO / "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = REPO / "artifacts/formulation/FROZEN.json"

DECLARED_SHA = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LEAN_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
CHECKER_SHA = "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd"
FROZEN_SHA = "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1"
PIN_FIELDS = ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at")

EXPECTED_LIVE = {
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/evidence/taxonomy_consistency.json": LEAN_SHA,
    "artifacts/formulation/tools/check_taxonomy_consistency.py": CHECKER_SHA,
    "artifacts/formulation/FROZEN.json": FROZEN_SHA,
    "artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json": DECLARED_SHA,
}

CHECKS = []


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(Path(p).read_bytes())


def now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def live_pins() -> dict:
    return {rel: sha_file(REPO / rel) for rel in EXPECTED_LIVE}


def record(cid: str, ok: bool, detail) -> None:
    CHECKS.append({"id": cid, "ok": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {detail if isinstance(detail, str) else json.dumps(detail)[:300]}")


def run_checker(script: Path, *args: str):
    r = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=SANDBOX,
        capture_output=True,
        text=True,
    )
    return {"rc": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}


def stage_sandbox() -> None:
    """Mirror ROOT into SANDBOX; the guarded candidate must live under the
    sandbox tools path or its Path(__file__).parents[3] resolves to the repo."""
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    for rel in (
        "research_map/formulation_taxonomy.yaml",
        "artifacts/formulation/formulation_taxonomy.yaml",
        "artifacts/formulation/VOCAB_ALIASES.json",
        "artifacts/formulation/tools/check_taxonomy_consistency.py",
    ):
        dst = SANDBOX / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, dst)
    shutil.copyfile(GUARDED_CHECKER, SANDBOX / GUARDED_REL)
    (SANDBOX / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)


def stage_declared() -> None:
    shutil.copyfile(DECLARED, SANDBOX / "artifacts/formulation/evidence/taxonomy_consistency.json")


def sandbox_evidence_sha() -> str:
    return sha_file(SANDBOX / "artifacts/formulation/evidence/taxonomy_consistency.json")


def main() -> int:
    started = now()
    report_path = ART / "report.json"
    pre = live_pins()
    fail_closed = {k: (pre[k], EXPECTED_LIVE[k]) for k in EXPECTED_LIVE if pre[k] != EXPECTED_LIVE[k]}
    if fail_closed:
        report = {
            "schema_version": "0.1",
            "task_id": "W086-GFORM-R2-DURABILITY-01",
            "actor": "worker-086",
            "created_at": started,
            "verdict": "MOVING_TARGET_FAIL_CLOSED",
            "moving_target": fail_closed,
            "checks": [],
        }
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 2

    # ---- C0: independent reconstruction of the declared document -------------
    live = json.loads(CANON_EVIDENCE.read_text())
    declared_raw = DECLARED.read_bytes()
    declared = json.loads(declared_raw)
    rec = {k: (declared[k] if k in PIN_FIELDS else live.get(k)) for k in declared}
    rec_sha = sha_bytes((json.dumps(rec, indent=2) + "\n").encode())
    record(
        "C0-declared-is-lean-plus-three-pin-fields",
        rec_sha == DECLARED_SHA and set(declared) - set(live) == set(PIN_FIELDS),
        {"reconstructed_sha256": rec_sha, "declared_sha256": sha_bytes(declared_raw),
         "extra_fields": sorted(set(declared) - set(live))},
    )

    # ---- build the guard candidate ------------------------------------------
    sys.path.insert(0, str(ART))
    import guard_build  # noqa: E402  (local candidate builder)

    guard = guard_build.build()
    record("C1-guard-builds-from-pinned-checker",
           guard["pinned_sha256"] == CHECKER_SHA and guard["guarded_sha256"] != CHECKER_SHA,
           {"pinned_sha256": guard["pinned_sha256"], "guarded_sha256": guard["guarded_sha256"]})
    guarded_abs = SANDBOX / GUARDED_REL

    # ---- sandbox matrix ------------------------------------------------------
    stage_sandbox()
    stage_declared()
    record("C2-sandbox-staged-at-declared-bytes", sandbox_evidence_sha() == DECLARED_SHA,
           sandbox_evidence_sha())

    # control: the pinned (unguarded) checker mutates the canonical path
    u = run_checker(SANDBOX / "artifacts/formulation/tools/check_taxonomy_consistency.py")
    after_u = sandbox_evidence_sha()
    record(
        "C3-control-unguarded-checker-mutates-path",
        u["rc"] == 0 and after_u == LEAN_SHA,
        {"rc": u["rc"], "stdout": u["stdout"], "path_after": after_u, "expected_after": LEAN_SHA},
    )
    computed_bytes = (SANDBOX / "artifacts/formulation/evidence/taxonomy_consistency.json").read_bytes()
    record(
        "C4-computed-document-equals-live-lean-document",
        sha_bytes(computed_bytes) == LEAN_SHA and computed_bytes == CANON_EVIDENCE.read_bytes(),
        {"computed_sha256": sha_bytes(computed_bytes), "live_sha256": sha_file(CANON_EVIDENCE)},
    )

    # guarded checker, default mode: restore is durable
    stage_declared()
    g1 = run_checker(guarded_abs)
    after_g1 = sandbox_evidence_sha()
    record(
        "C5-guarded-checker-preserves-restored-bytes",
        g1["rc"] == 0
        and after_g1 == DECLARED_SHA
        and "not written" in g1["stdout"]
        and f"on_disk_sha256={DECLARED_SHA}" in g1["stdout"],  # sentinel: ROOT resolved to SANDBOX
        {"rc": g1["rc"], "stdout": g1["stdout"], "path_after": after_g1,
         "sandbox_root_sentinel": f"on_disk_sha256={DECLARED_SHA}" in g1["stdout"]},
    )
    g2 = run_checker(guarded_abs)
    after_g2 = sandbox_evidence_sha()
    record(
        "C6-guarded-checker-repeat-is-byte-stable",
        g2["rc"] == 0 and after_g2 == DECLARED_SHA,
        {"rc": g2["rc"], "path_after": after_g2, "runs": 2},
    )

    # control: guard does not silence inconsistency detection
    mp = SANDBOX / "research_map/formulation_taxonomy.yaml"
    tax = yaml.safe_load(mp.read_text())
    tax["classes"]["AF-WCC-VAC-GEN"]["axes"]["family"] = "WCC-MUTANT-CONTROL"
    mp.write_text(yaml.safe_dump(tax, sort_keys=False))
    g3 = run_checker(guarded_abs)
    after_g3 = sandbox_evidence_sha()
    record(
        "C7-guard-keeps-inconsistency-detection",
        g3["rc"] == 1 and "INCONSISTENT" in g3["stdout"] and after_g3 == DECLARED_SHA,
        {"rc": g3["rc"], "stdout": g3["stdout"][:200], "path_after": after_g3},
    )
    shutil.copyfile(REPO / "research_map/formulation_taxonomy.yaml", mp)

    # control: explicit owner regeneration (--write) still available
    g4 = run_checker(guarded_abs, "--write")
    after_g4 = sandbox_evidence_sha()
    record(
        "C8-explicit-write-opt-in-regenerates",
        g4["rc"] == 0 and after_g4 == LEAN_SHA,
        {"rc": g4["rc"], "path_after": after_g4, "expected_after": LEAN_SHA},
    )

    # leave the sandbox in the repaired state (declared bytes restored, guard on)
    stage_declared()
    g5 = run_checker(guarded_abs)
    final_sha = sandbox_evidence_sha()
    record(
        "C9-final-repaired-fixpoint-declared-equals-disk",
        g5["rc"] == 0 and final_sha == DECLARED_SHA,
        {"rc": g5["rc"], "path_after": final_sha},
    )

    # ---- live repository untouched ------------------------------------------
    post = live_pins()
    record(
        "C10-live-pins-unchanged-by-probe",
        post == pre,
        {k: {"before": pre[k], "after": post[k]} for k in pre if pre[k] != post[k]} or "all 10 pins identical",
    )

    # ---- residual requirement: FROZEN still pins the lean bytes --------------
    frozen = json.loads(FROZEN.read_text())
    frozen_pin = frozen["files"]["artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"]
    record(
        "C11-residual-frozen-repin-required",
        frozen_pin == LEAN_SHA,
        {"frozen_pin": frozen_pin, "declared_sha256": DECLARED_SHA,
         "residual": "R2+guard makes declared==disk but FROZEN rev28 pins the lean bytes; "
                     "the owner must publish a FROZEN revision that re-pins the evidence path (and the "
                     "guarded tool hash) before declared==disk==freeze holds at one instant."},
    )

    all_ok = all(c["ok"] for c in CHECKS)
    verdict = (
        "R2_DURABLE_WITH_NOWRITE_GUARD__RESIDUAL_FROZEN_REPIN_AND_OWNER_APPLY_REQUIRED"
        if all_ok
        else "R2_DURABILITY_CHECK_FAILED"
    )
    report = {
        "schema_version": "0.1",
        "artifact_kind": "repair_durability_probe",
        "task_id": "W086-GFORM-R2-DURABILITY-01",
        "actor": "worker-086",
        "role": "bounded execution worker",
        "created_at": started,
        "finished_at": now(),
        "gate": "G-FORM",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "authority": "worker measurement and candidate artifact only; no canonical write, no schema edit, "
                     "no gate verdict, no node status",
        "incident_log": [
            {
                "at": "2026-09-12T00:47:25+08:00",
                "phase": "probe development run #1 (superseded; this report is the corrected run)",
                "what": "The guarded candidate was first executed from "
                        "artifacts/worker-086/evbind_repair_demo/ instead of a mirrored tools path, so its "
                        "Path(__file__).resolve().parents[3] resolved to the repository root. The C8 "
                        "--write control therefore rewrote the canonical evidence path "
                        "artifacts/formulation/evidence/taxonomy_consistency.json with byte-identical "
                        "content.",
                "impact": "Content unchanged: measured sha256 before and after the incident is "
                          "9e335e9b (live lean document); all 10 live pins identical before/after. The "
                          "canonical file mtime moved to 2026-09-12 00:47:25.106985689 +0800.",
                "detection": "C5 sandbox sentinel failed in run #1 because the guard note reported the "
                             "live on-disk hash while the sandbox path stayed at declared bytes.",
                "fix": "The guarded candidate is now installed inside the sandbox mirror "
                       "(sandbox/artifacts/formulation/tools/) and C5 asserts "
                       "on_disk_sha256=675a99d0 from the guard note, proving ROOT resolves to the "
                       "sandbox. No probe run after that fix touches a canonical path (C10).",
            }
        ],
        "inputs": {
            "artifacts/worker-086/evidence_collision/report.json": "bd548a3f7b1f56bca9296e16962e493c3a52d814aad4b44fb2ad09eb451ecfee",
            "artifacts/worker-092/evbind (adjudication R2+guard)": "see comms/outbox/worker-092.jsonl w092-20260912T004304-evbind-claim",
            "pins": pre,
        },
        "guard_candidate": guard,
        "sandbox": {
            "path": "artifacts/worker-086/evbind_repair_demo/sandbox",
            "mirrors": list(EXPECTED_LIVE)[:4],
            "evidence_path_final_sha256": final_sha,
        },
        "checks": CHECKS,
        "checks_passed": sum(1 for c in CHECKS if c["ok"]),
        "checks_total": len(CHECKS),
        "verdict": verdict,
        "repair_recipe_verified": {
            "step_1_owner_stage": "cp artifacts/worker-086/evidence_collision/restore_candidate/"
                                  "taxonomy_consistency.675a99d0d25b.json "
                                  "artifacts/formulation/evidence/taxonomy_consistency.json",
            "step_2_owner_apply_guard": "apply guard.patch to "
                                        "artifacts/formulation/tools/check_taxonomy_consistency.py "
                                        "(guarded candidate sha256 given above)",
            "step_3_owner_repin": "publish a FROZEN revision re-pinning the evidence path at "
                                  f"{DECLARED_SHA} and the guarded tool at its new hash",
            "durability": "with step 2 applied, re-running the checker leaves the canonical evidence path "
                          "at 675a99d0 (C5/C6/C9); without it the first run rewrites it to 9e335e9b (C3)",
        },
        "falsifier": "The R2+guard repair fails if, after the owner stages steps 1-3: (a) one standalone "
                     "guarded-checker run leaves the canonical evidence path at any hash other than "
                     "675a99d0; or (b) any of the three schema hashes or the F0 taxonomy hash changes; or "
                     "(c) the unguarded pinned checker no longer rewrites a sandbox copy to 9e335e9b "
                     "(control dead); or (d) FROZEN still pins 9e335e9b at the canonical evidence path.",
        "next_falsifier": "Re-run artifacts/worker-086/evidence_collision/probe_collision.py at the "
                          "post-repair pins; the repair clears only when declared hash, live bytes and "
                          "the FROZEN pin agree at one measured instant.",
        "non_claims": [
            "Does not edit the canonical evidence path, the schemas, the pinned checker or FROZEN.",
            "Does not decide the repair choice between R1/R2/R3; it measures the durability leg of R2.",
            "Does not exercise close_findings_rev27.py --apply, the second writer of the canonical path.",
            "Does not claim a gate verdict, node completion or validation_status=passed.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")

    # pins sidecar + manifest (excluding the manifest itself)
    pins_doc = {
        "task_id": report["task_id"],
        "created_at": started,
        "live_pins_before": pre,
        "live_pins_after": post,
        "declared_sha256": DECLARED_SHA,
        "guarded_candidate_sha256": guard["guarded_sha256"],
        "guard_patch_sha256": guard["patch_sha256"],
    }
    (ART / "PINS.json").write_text(json.dumps(pins_doc, indent=2) + "\n")
    manifest = {}
    for p in sorted(ART.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256" and "__pycache__" not in p.parts:
            manifest[str(p.relative_to(ART))] = sha_file(p)
    (ART / "MANIFEST.sha256").write_text(
        "".join(f"{v}  {k}\n" for k, v in sorted(manifest.items()))
    )
    print(f"\nVERDICT: {verdict}  ({report['checks_passed']}/{report['checks_total']} checks pass)")
    print(f"report: {report_path.relative_to(REPO)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
