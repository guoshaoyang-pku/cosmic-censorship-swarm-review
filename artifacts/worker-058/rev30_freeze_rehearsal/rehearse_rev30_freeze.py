#!/usr/bin/env python3
"""W058-REV30-FREEZE-REHEARSAL-01 -- sandbox-only rehearsal of the F2b repair -> re-freeze ->
verify -> acceptance chain, plus a freeze-identity collision audit of the rev29 incident.

Worker-058, node F2b, class AF-SCC-C0-VAC-GEN (siblings AF-SCC-C2-VAC-GEN, AF-WCC-VAC-GEN),
gate context G-FORM.  Worker evidence only: canonical tree is read-only (start/end hash proof),
no node status, no validation_status, no gate verdict.

Inputs (pinned, fail-closed on drift):
  * live FROZEN rev29 815e08079aef (50 pins, frozen_at 00:57:26)
  * live C0 b2ab6acb2bbe (defective) and the pre-validated two-edit repair candidate
    84b5d3fa29a6 (worker-066 reconstruction, worker-008 FORM-SEP-04 validation)
  * the two recorded rev29 generations 3d9e3d77fd87 / 815e08079aef (worker-040 pinned copies)
  * the FORM-SEP-04 battery and the fail-closed dual containment checker

Rehearsal steps: guarded re-freeze to revision 30 with a fixed frozen_at (deterministic),
verify_frozen in the sandbox, candidate-vs-control acceptance runs, exact pin-move table,
idempotent second sandbox, and six planted controls (M1-M6).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts" / "worker-058" / "rev30_freeze_rehearsal"
SANDBOX = OUT / "sandbox"
SANDBOX2 = OUT / "sandbox_idem"
CONTROL = OUT / "control"
MUT = OUT / "mutants"
CST = timezone(timedelta(hours=8))
FIXED_AT = "2026-09-12T01:30:00+08:00"
NEW_REV = 30

sys.path.insert(0, str(OUT))
import freeze_guard as FG  # noqa: E402

PATHS = {
    "frozen_live": "artifacts/formulation/FROZEN.json",
    "c0_live": "schemas/af_scc_c0_vacuum.yaml",
    "c0_mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "c2_live": "schemas/af_scc_c2_vacuum.yaml",
    "f1_live": "schemas/af_wcc_vacuum.yaml",
    "f0_taxonomy": "research_map/formulation_taxonomy.yaml",
    "candidate": "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
    "battery": "artifacts/worker08/c2_c0_separation_audit.py",
    "dual": "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py",
    "regenerate": "artifacts/formulation/tools/regenerate_frozen.py",
    "verify": "artifacts/formulation/tools/verify_frozen.py",
    "gen_a": ("artifacts/worker-040/rev29_frozen_drift_adjudication/pinned/"
              "FROZEN.rev29.3d9e3d77fd87.json"),
    "gen_b": ("artifacts/worker-040/rev29_frozen_drift_adjudication/pinned/"
              "FROZEN.rev29.815e08079aef.json"),
}
PINS = {
    "frozen_live": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "c0_live": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "c0_mirror": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "c2_live": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "f1_live": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "f0_taxonomy": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "candidate": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
}
CANONICAL_TOOLS = ["artifacts/formulation/tools/regenerate_frozen.py",
                   "artifacts/formulation/tools/verify_frozen.py"]
LFORM01_FIXED = ("C2 is a strictly smaller extension class (E_C2 subset of E_C0), so "
                 "C2-inextendibility is strictly weaker")
LFORM01_INVERTED = ("C2 is a strictly larger extension class, so C2-inextendibility is "
                    "strictly weaker")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_json(p: Path):
    return json.loads(Path(p).read_text())


def run(cmd, cwd=ROOT):
    proc = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, text=True)
    return (
        {
            "command": " ".join(str(c) for c in cmd),
            "exit_code": proc.returncode,
            "stdout_tail": (proc.stdout or "").strip().splitlines()[-4:],
            "stderr_tail": (proc.stderr or "").strip().splitlines()[-4:],
        },
        proc,
    )


def copy_tree_from_manifest(man: dict, dest: Path) -> dict:
    """Materialise every pinned path (plus the two tools) into a fresh sandbox tree."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    missing, copied = [], 0
    for rel in sorted(man["files"]):
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied += 1
    for rel in CANONICAL_TOOLS:
        dst = dest / rel
        if not dst.exists():
            src = ROOT / rel
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
    # The manifest never pins itself; the sandbox starts from the live rev29 manifest.
    (dest / "artifacts/formulation").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / PATHS["frozen_live"], dest / "artifacts/formulation/FROZEN.json")
    return {"copied": copied, "missing": missing}


def guarded_refreeze(sandbox: Path, records: list[dict], revision: int, at: str) -> dict:
    """Refuse a non-monotone or repeated-revision re-freeze BEFORE invoking the writer."""
    current_man = read_json(sandbox / "artifacts/formulation/FROZEN.json")
    current_id = FG.identity(current_man)
    pre = {"current_identity": current_id, "requested_revision": revision}
    try:
        if int(revision) <= int(current_id["revision"]):
            pre.update(accepted=False,
                       violation="G1_revision_not_increasing (pre-write refusal, no bytes written)")
            return pre
    except (TypeError, ValueError):
        pre.update(accepted=False, violation="unparseable current revision")
        return pre
    backup = (sandbox / "artifacts/formulation/FROZEN.json").read_bytes()
    rec, proc = run([sys.executable, sandbox / "artifacts/formulation/tools/regenerate_frozen.py",
                     "--revision", str(revision), "--delta",
                     "W058-REV30-FREEZE-REHEARSAL-01 sandbox rehearsal (F2b two-leaf repair)",
                     "--at", at])
    pre["writer_run"] = rec
    if proc.returncode != 0:
        (sandbox / "artifacts/formulation/FROZEN.json").write_bytes(backup)
        pre.update(accepted=False, violation=f"writer rc={proc.returncode}")
        return pre
    new_id = FG.identity(read_json(sandbox / "artifacts/formulation/FROZEN.json"))
    decision = FG.guard_new_revision(records + [current_id], new_id)
    pre.update(accepted=decision["accept"], decision=decision, new_identity=new_id)
    if not decision["accept"]:
        (sandbox / "artifacts/formulation/FROZEN.json").write_bytes(backup)
        pre["rolled_back"] = True
    return pre


def battery(c0: Path, c2: Path, label: str, outdir: Path) -> dict:
    oj = outdir / f"battery_{label}.json"
    om = outdir / f"battery_{label}.md"
    rec, _ = run([sys.executable, ROOT / PATHS["battery"], "--c2", c2, "--c0", c0,
                  "--out-json", oj, "--out-md", om, "--label", label])
    d = read_json(oj) if oj.is_file() else {}
    return {
        "run": rec,
        "json": str(oj),
        "json_sha256": sha_file(oj) if oj.is_file() else None,
        "verdict": d.get("verdict"),
        "hard_failures": d.get("hard_failures"),
        "X3c_containment_inversions": (d.get("X3c_containment_inversion") or {}).get("violations"),
    }


def dual(c0: Path, c2: Path, expect_c0: str, expect_c2: str, label: str, outdir: Path) -> dict:
    oj = outdir / f"dual_{label}.json"
    rec, _ = run([sys.executable, ROOT / PATHS["dual"], "--c0", c0, "--c2", c2,
                  "--expect-c0", expect_c0, "--expect-c2", expect_c2,
                  "--label", label, "--json", oj])
    d = read_json(oj) if oj.is_file() else {}
    finds = d.get("findings") or []
    return {
        "run": rec,
        "json": str(oj),
        "json_sha256": sha_file(oj) if oj.is_file() else None,
        "verdict": d.get("verdict"),
        "n_findings": len(finds),
        "finding_kinds": sorted({f.get("kind") for f in finds}),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for d in (CONTROL, MUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    report = {
        "schema": "worker-058/rev30-freeze-rehearsal/v1",
        "rehearsal_id": "W058-REV30-FREEZE-REHEARSAL-01",
        "actor": "worker-058",
        "created_at": now(),
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"],
        "node_ids": ["F2b"],
        "gate_context": "G-FORM",
        "authority": ("worker evidence only; canonical paths read-only; no node status, no "
                      "validation_status, no gate verdict; owner owns any rev30 publication"),
        "fixed_at": FIXED_AT,
    }

    # ---- Step 0: pin inputs, fail closed -------------------------------------
    pins = {}
    for key, rel in PATHS.items():
        p = ROOT / rel
        if not p.is_file():
            print(f"FATAL missing input {rel}", file=sys.stderr)
            return 2
        pins[key] = {"path": rel, "sha256": sha_file(p)}
    for key, expected in PINS.items():
        ok = pins[key]["sha256"] == expected
        pins[key]["expected"] = expected
        pins[key]["match"] = ok
        if not ok:
            print(f"FATAL pin drift {key}: {pins[key]['sha256']} != {expected}", file=sys.stderr)
            return 2
    live_start = {k: pins[k]["sha256"] for k in ("c0_live", "c2_live", "f1_live",
                                                 "f0_taxonomy", "frozen_live")}
    report["inputs"] = pins
    report["candidate"] = {
        "path": PATHS["candidate"],
        "sha256": pins["candidate"]["sha256"],
        "provenance": ("worker-066 reconstruction, validated by worker-008 FORM-SEP-04 "
                       "W008-FORMSEP04-CANDIDATE-VALIDATION-01 (verdict CANDIDATE_CLEARS_FORMSEP04)"),
        "changed_leaf_paths": ["implication_ledger.forbidden_transfers[0].reason",
                               "regularity.must_not_conflate[0]"],
    }

    # ---- Step 1: sandbox from live rev29 pins, then apply the repair ----------
    live_man = read_json(ROOT / PATHS["frozen_live"])
    build = copy_tree_from_manifest(live_man, SANDBOX)
    if build["missing"]:
        print(f"FATAL sandbox incomplete: {build['missing']}", file=sys.stderr)
        return 2
    shutil.copyfile(ROOT / PATHS["c0_live"], CONTROL / "rev29_c0_control.yaml")
    cand_bytes = (ROOT / PATHS["candidate"]).read_bytes()
    for rel in ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"):
        (SANDBOX / rel).write_bytes(cand_bytes)
    report["sandbox"] = {
        "root": str(SANDBOX.relative_to(ROOT)),
        "built_from_manifest": PATHS["frozen_live"],
        "n_pinned_copied": build["copied"],
        "c0_candidate_written_to": ["schemas/af_scc_c0_vacuum.yaml",
                                    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"],
        "c0_candidate_sha256": sha_file(SANDBOX / "schemas/af_scc_c0_vacuum.yaml"),
        "mirror_equal_after_repair": (sha_file(SANDBOX / "schemas/af_scc_c0_vacuum.yaml")
                                      == sha_file(SANDBOX / "artifacts/formulation/schemas/"
                                                  "af_scc_c0_vacuum.yaml")),
    }

    # ---- Step 2: freeze-identity audit of the recorded rev29 generations -----
    gen_ids = [FG.load_identity(ROOT / PATHS["gen_a"]), FG.load_identity(ROOT / PATHS["gen_b"])]
    history = FG.audit_history(gen_ids)
    report["freeze_identity_audit"] = {
        "recorded_generations": gen_ids,
        "collisions": history["repeated_revision_distinct_identity"],
        "history_unique": history["history_unique"],
        "meaning": ("both recorded generations declare revision 29 with different manifest "
                    "digests, so the bare label 'rev29' is ambiguous (CF-27)"),
    }
    if history["history_unique"]:
        print("FATAL expected a rev29 identity collision, observed none", file=sys.stderr)
        return 2

    # ---- Step 3: guarded re-freeze in the sandbox -----------------------------
    refreeze = guarded_refreeze(SANDBOX, gen_ids, NEW_REV, FIXED_AT)
    report["guarded_refreeze"] = refreeze
    if not refreeze.get("accepted"):
        print("FATAL guarded re-freeze refused", file=sys.stderr)
        return 2
    new_man = read_json(SANDBOX / "artifacts/formulation/FROZEN.json")
    new_id = FG.identity(new_man)
    report["new_freeze"] = {
        "revision": new_man.get("revision"),
        "frozen_at": new_man.get("frozen_at"),
        "n_files": len(new_man["files"]),
        "manifest_sha256": sha_file(SANDBOX / "artifacts/formulation/FROZEN.json"),
        "identity": new_id,
        "rev30_delta": new_man.get("rev30_delta"),
    }

    # ---- Step 4: verify_frozen in sandbox + guard tree check ------------------
    rec_v, proc_v = run([sys.executable, SANDBOX / "artifacts/formulation/tools/verify_frozen.py"])
    tree = FG.verify_tree(new_man, SANDBOX)
    report["verify_frozen_sandbox"] = {
        "run": rec_v, "exit_code": proc_v.returncode, "clean": tree["clean"],
        "problems": tree["problems"], "n_files": tree["n_files"],
    }
    if proc_v.returncode != 0 or not tree["clean"]:
        print("FATAL sandbox verify_frozen not clean", file=sys.stderr)
        return 2

    # ---- Step 5: acceptance battery + dual checker, candidate vs control ------
    sb_c0 = SANDBOX / "schemas/af_scc_c0_vacuum.yaml"
    sb_c2 = SANDBOX / "schemas/af_scc_c2_vacuum.yaml"
    sb_c1 = CONTROL / "rev29_c0_control.yaml"
    report["acceptance"] = {
        "candidate": {
            "battery": battery(sb_c0, sb_c2, "rev30_candidate", OUT),
            "dual": dual(sb_c0, sb_c2, sha_file(sb_c0), sha_file(sb_c2), "rev30_candidate", OUT),
        },
        "canonical_control_rev29": {
            "battery": battery(sb_c1, sb_c2, "rev29_control", OUT),
            "dual": dual(sb_c1, sb_c2, sha_file(sb_c1), sha_file(sb_c2), "rev29_control", OUT),
        },
        "wrong_expect_control": dual(sb_c0, sb_c2, "deadbeef" * 8, sha_file(sb_c2),
                                     "wrong_expect", OUT),
    }

    # ---- Step 6: pin-move table (live rev29 -> sandbox rev30) -----------------
    live_files, new_files = live_man["files"], new_man["files"]
    moved = sorted(p for p in set(live_files) | set(new_files)
                   if live_files.get(p, {}).get("sha256") != new_files.get(p, {}).get("sha256"))
    added = sorted(set(new_files) - set(live_files))
    removed = sorted(set(live_files) - set(new_files))
    report["pin_move_table"] = {
        "moved": [{"path": p,
                   "rev29": live_files.get(p, {}).get("sha256"),
                   "rev30": new_files.get(p, {}).get("sha256")} for p in moved],
        "added": added,
        "removed": removed,
        "unexpected_moves": [p for p in moved
                             if p not in ("schemas/af_scc_c0_vacuum.yaml",
                                          "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")],
    }

    # ---- Step 7: idempotency --------------------------------------------------
    build2 = copy_tree_from_manifest(live_man, SANDBOX2)
    for rel in ("schemas/af_scc_c0_vacuum.yaml",
                "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"):
        (SANDBOX2 / rel).write_bytes(cand_bytes)
    refreeze2 = guarded_refreeze(SANDBOX2, gen_ids, NEW_REV, FIXED_AT)
    man2_bytes = (SANDBOX2 / "artifacts/formulation/FROZEN.json").read_bytes()
    man1_bytes = (SANDBOX / "artifacts/formulation/FROZEN.json").read_bytes()
    report["idempotency"] = {
        "second_sandbox_built": not build2["missing"],
        "second_refreeze_accepted": refreeze2.get("accepted"),
        "manifest_bytes_identical": man1_bytes == man2_bytes,
        "manifest_sha256_second": hashlib.sha256(man2_bytes).hexdigest(),
        "candidate_bytes_identical": (sha_file(SANDBOX2 / "schemas/af_scc_c0_vacuum.yaml")
                                      == sha_file(sb_c0)),
    }

    # ---- Step 8: planted controls M1-M6 ---------------------------------------
    mutants = []

    # M1: same-revision re-freeze must be refused pre-write.
    m1_dir = MUT / "M1_same_revision"
    shutil.copytree(SANDBOX, m1_dir)
    before = sha_file(m1_dir / "artifacts/formulation/FROZEN.json")
    m1 = guarded_refreeze(m1_dir, gen_ids, 29, FIXED_AT)
    after = sha_file(m1_dir / "artifacts/formulation/FROZEN.json")
    mutants.append({"id": "M1_same_revision_refused", "accepted": m1.get("accepted"),
                    "manifest_unchanged": before == after,
                    "expectation_met": (not m1.get("accepted")) and before == after,
                    "detail": m1.get("violation")})

    # M2: mirror divergence (canonical repaired, mirror left at rev29) must be DRIFT.
    m2_dir = MUT / "M2_mirror_divergence"
    shutil.copytree(SANDBOX, m2_dir)
    (m2_dir / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml").write_bytes(
        (ROOT / PATHS["c0_mirror"]).read_bytes())
    t2 = FG.verify_tree(read_json(m2_dir / "artifacts/formulation/FROZEN.json"), m2_dir)
    mutants.append({"id": "M2_mirror_divergence_detected", "clean": t2["clean"],
                    "problems": t2["problems"],
                    "expectation_met": (not t2["clean"]) and any(
                        "formulation/schemas/af_scc_c0_vacuum.yaml" in p["path"]
                        for p in t2["problems"])})

    # M3: one-byte tamper inside a pinned file must be DRIFT.
    m3_dir = MUT / "M3_pin_tamper"
    shutil.copytree(SANDBOX, m3_dir)
    victim = m3_dir / "schemas/af_scc_c2_vacuum.yaml"
    b = bytearray(victim.read_bytes())
    b[-1] = (b[-1] + 1) % 256
    victim.write_bytes(bytes(b))
    t3 = FG.verify_tree(read_json(m3_dir / "artifacts/formulation/FROZEN.json"), m3_dir)
    mutants.append({"id": "M3_pin_tamper_detected", "clean": t3["clean"],
                    "problems": t3["problems"], "expectation_met": not t3["clean"]})

    # M4: a missing pinned file must be MISSING.
    m4_dir = MUT / "M4_missing_pin"
    shutil.copytree(SANDBOX, m4_dir)
    (m4_dir / "schemas/af_wcc_vacuum.yaml").unlink()
    t4 = FG.verify_tree(read_json(m4_dir / "artifacts/formulation/FROZEN.json"), m4_dir)
    mutants.append({"id": "M4_missing_pin_detected", "clean": t4["clean"],
                    "problems": t4["problems"], "expectation_met": not t4["clean"]})

    # M5: a third generation at revision 30 with different bytes must collide in the audit.
    m5_man = json.loads(json.dumps(new_man))
    first = sorted(m5_man["files"])[0]
    m5_man["files"][first]["sha256"] = "0" * 64
    m5_id = FG.identity(m5_man)
    audit5 = FG.audit_history(gen_ids + [new_id, m5_id])
    mutants.append({"id": "M5_third_generation_collision", "records": audit5["n_records"],
                    "collisions": audit5["repeated_revision_distinct_identity"],
                    "expectation_met": any(c["revision"] == "30"
                                           for c in audit5["repeated_revision_distinct_identity"])})

    # M6: reverting the L-FORM-01 leaf must make the battery fire again.
    wrong = cand_bytes.decode("utf-8").replace(LFORM01_FIXED, LFORM01_INVERTED)
    wrong_path = MUT / "M6_wrong_repair_c0.yaml"
    if wrong == cand_bytes.decode("utf-8"):
        print("FATAL M6 could not plant the inversion", file=sys.stderr)
        return 2
    wrong_path.write_text(wrong)
    b6 = battery(wrong_path, sb_c2, "M6_wrong_repair", MUT)
    mutants.append({"id": "M6_wrong_repair_fires", "verdict": b6["verdict"],
                    "X3c": b6["X3c_containment_inversions"],
                    "expectation_met": b6["verdict"] == "FAIL"
                    and (b6["X3c_containment_inversions"] or 0) >= 1})
    report["mutants"] = mutants

    # ---- Step 9: canonical read-only proof ------------------------------------
    live_end = {k: sha_file(ROOT / PATHS[k]) for k in live_start}
    report["canonical_read_only"] = {
        "start": live_start, "end": live_end, "unchanged": live_start == live_end,
    }

    # ---- Step 10: verdict ------------------------------------------------------
    acc = report["acceptance"]
    checks = {
        "inputs_pinned": True,
        "rev29_identity_collision_confirmed": not history["history_unique"],
        "guarded_refreeze_accepted_rev30": report["guarded_refreeze"]["accepted"],
        "sandbox_verify_frozen_clean": report["verify_frozen_sandbox"]["clean"],
        "sandbox_mirror_consistent": report["sandbox"]["mirror_equal_after_repair"],
        "candidate_battery_pass": acc["candidate"]["battery"]["verdict"] == "PASS",
        "candidate_dual_pass": acc["candidate"]["dual"]["verdict"] == "PASS",
        "control_still_fails_battery": acc["canonical_control_rev29"]["battery"]["verdict"] == "FAIL",
        "control_still_fails_dual": acc["canonical_control_rev29"]["dual"]["verdict"] == "FAIL",
        "wrong_expect_fail_closed": acc["wrong_expect_control"]["run"]["exit_code"] == 3,
        "pin_moves_exactly_the_two_c0_paths": (
            sorted(p["path"] for p in report["pin_move_table"]["moved"])
            == ["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                "schemas/af_scc_c0_vacuum.yaml"]
        ) and not report["pin_move_table"]["added"] and not report["pin_move_table"]["removed"]
        and not report["pin_move_table"]["unexpected_moves"],
        "refreeze_idempotent": (report["idempotency"]["manifest_bytes_identical"]
                                and report["idempotency"]["candidate_bytes_identical"]),
        "all_mutants_expected": all(m["expectation_met"] for m in mutants),
        "canonical_unchanged": report["canonical_read_only"]["unchanged"],
    }
    report["checks"] = checks
    report["verdict"] = ("REV30_FREEZE_REHEARSAL_READY"
                         if all(checks.values()) else "REHEARSAL_INCONCLUSIVE")
    report["falsifier"] = (
        "Any of: (a) a pinned input hash differs from its declared value; (b) the sandbox "
        "rev30 manifest does not verify clean against the sandbox tree; (c) the pre-validated "
        "candidate (84b5d3fa) does not pass both the FORM-SEP-04 battery and the fail-closed "
        "dual checker while the rev29 control fails both; (d) more or fewer than the two C0 "
        "paths move between rev29 and rev30; (e) the second identical sandbox run does not "
        "reproduce the manifest bytes; (f) any planted control M1-M6 is not caught; (g) any "
        "canonical byte changed during the run."
    )
    report["next_falsifier"] = (
        "Owner publishes rev30 with the two-leaf repair; then the rehearsal's expected rev30 "
        "manifest identity must match the published one, and two blind full-schema F2b "
        "reviewers must accept at the published hash."
    )
    report["residual_defects_out_of_scope"] = [
        "L-FORM-03 predicate-strength inversion in research_map/formulation_taxonomy.yaml "
        "(G-F0 frozen; controller decision required, voids G-F0 if edited)",
        "C0 strength-bucket mislabel (advisory, not in the validated two-leaf repair surface)",
        "L-FORM-04 F1 falsifier-suite repin (worker-031 proposal; independent pin move)",
    ]

    rep_path = OUT / "report.json"
    rep_path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    # ---- Step 11: runbook + checkpoint + hashes -------------------------------
    moved_paths = [p["path"] for p in report["pin_move_table"]["moved"]]
    runbook = [
        "# Owner runbook -- rev30 publication from the rehearsed repair",
        "",
        f"Rehearsal verdict: **{report['verdict']}** (sandbox only; worker evidence, not a gate).",
        "",
        "1. Apply the pre-validated two-leaf repair to BOTH C0 copies (they must stay byte-identical):",
        "   ```bash",
        "   cp artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml \\",
        "      schemas/af_scc_c0_vacuum.yaml",
        "   cp artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml \\",
        "      artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "   ```",
        f"   expected new C0 sha256: `{PINS['candidate']}` (both paths).",
        "2. Re-freeze with a strictly increasing revision and an explicit timestamp:",
        "   ```bash",
        "   python3 artifacts/formulation/tools/regenerate_frozen.py --revision 30 \\",
        f"     --delta \"F2b L-FORM-01 two-leaf repair (C0:152 denial + C0:245 inversion)\" --at <ISO8601>",
        "   ```",
        "3. Record the new freeze identity and refuse collisions (the guard demonstrated in this",
        "   rehearsal): revision, frozen_at and manifest digest must be new; if revision 30 already",
        "   exists with different bytes, STOP -- that is a repeat of CF-27.",
        "4. Verify:",
        "   ```bash",
        "   python3 artifacts/formulation/tools/verify_frozen.py   # expect rc=0",
        "   ```",
        "5. Re-run acceptance at the new hash before requesting reviews:",
        "   ```bash",
        "   python3 artifacts/worker08/c2_c0_separation_audit.py --c2 schemas/af_scc_c2_vacuum.yaml \\",
        "     --c0 schemas/af_scc_c0_vacuum.yaml --out-json /tmp/rev30_battery.json \\",
        "     --out-md /tmp/rev30_battery.md --label rev30",
        "   ```",
        f"   expected: PASS, 0 hard failures, X3c=0. Pins that must move: {moved_paths}.",
        "6. Then commission two blind full-schema F2b reviewers at the published FROZEN hash.",
        "",
        "Sandbox artifacts from the rehearsal are under "
        f"`{OUT.relative_to(ROOT)}/` (report.json, sandbox/, sandbox_idem/, mutants/).",
    ]
    (OUT / "OWNER_RUNBOOK.md").write_text("\n".join(runbook) + "\n")

    readme = [
        "# W058-REV30-FREEZE-REHEARSAL-01",
        "",
        "Worker-058, class `AF-SCC-C0-VAC-GEN` (F2b), gate context `G-FORM`. Sandbox-only: no",
        "canonical path written, no node status, no validation_status, no gate verdict.",
        "",
        "## Why this task",
        "",
        "The F2b repair candidate is pre-validated (worker-008, 84b5d3fa) but no rev30 freeze",
        "exists, and rev29 was published twice with different bytes under the same label (CF-27).",
        "This rehearsal proves the whole chain -- repair, guarded re-freeze, verify, acceptance --",
        "in an isolated tree, so the owner's publication is one rehearsed step.",
        "",
        "## Result",
        "",
        f"- verdict: **{report['verdict']}**",
        f"- rev30 sandbox manifest: {report['new_freeze']['n_files']} pins, "
        f"sha256 `{report['new_freeze']['manifest_sha256'][:12]}`, identity "
        f"`{report['new_freeze']['identity']['manifest_digest'][:12]}` (frozen_at {FIXED_AT})",
        f"- verify_frozen in sandbox: rc={report['verify_frozen_sandbox']['exit_code']}, "
        f"{report['verify_frozen_sandbox']['n_files']} files, 0 problems",
        f"- candidate battery/dual: {acc['candidate']['battery']['verdict']} / "
        f"{acc['candidate']['dual']['verdict']}; rev29 control: "
        f"{acc['canonical_control_rev29']['battery']['verdict']} / "
        f"{acc['canonical_control_rev29']['dual']['verdict']}",
        f"- pin moves: {moved_paths}",
        "- idempotent second sandbox: "
        f"{report['idempotency']['manifest_bytes_identical']}",
        f"- controls M1-M6: {sum(1 for m in mutants if m['expectation_met'])}/{len(mutants)} met",
        "- canonical bytes unchanged during the run: "
        f"{report['canonical_read_only']['unchanged']}",
        "",
        "## Files",
        "",
        "| file | role |",
        "|---|---|",
        "| `freeze_guard.py` | freeze identity / revision monotonicity / tree verification |",
        "| `rehearse_rev30_freeze.py` | deterministic rehearsal driver |",
        "| `report.json` | full machine-readable certificate |",
        "| `OWNER_RUNBOOK.md` | one-step publication procedure with expected hashes |",
        "| `checkpoint.json` | bounded-task checkpoint |",
        "| `sandbox/`, `sandbox_idem/`, `mutants/` | disposable rehearsal trees |",
        "",
        "## Reproduce",
        "",
        "```bash",
        "cd /data3/guoshaoyang/workdir/ai4math-swarm",
        "python3 artifacts/worker-058/rev30_freeze_rehearsal/rehearse_rev30_freeze.py",
        "```",
        "",
        "## Falsifier",
        "",
        report["falsifier"],
        "",
        "## Next falsifier",
        "",
        report["next_falsifier"],
    ]
    (OUT / "README.md").write_text("\n".join(readme) + "\n")

    checkpoint = {
        "schema": "worker-058/checkpoint/v1",
        "actor": "worker-058",
        "task_id": "W058-REV30-FREEZE-REHEARSAL-01",
        "created_at": now(),
        "class_ids": report["class_ids"],
        "node_ids": report["node_ids"],
        "gate_context": report["gate_context"],
        "status": "worker-level complete; owner rev30 publication pending",
        "verdict": report["verdict"],
        "freeze_identity": report["new_freeze"]["identity"],
        "artifacts": {
            "report": {"path": "artifacts/worker-058/rev30_freeze_rehearsal/report.json",
                       "sha256": sha_file(rep_path)},
            "instrument": {"path": "artifacts/worker-058/rev30_freeze_rehearsal/"
                                   "rehearse_rev30_freeze.py",
                           "sha256": sha_file(Path(__file__))},
            "guard": {"path": "artifacts/worker-058/rev30_freeze_rehearsal/freeze_guard.py",
                      "sha256": sha_file(OUT / "freeze_guard.py")},
            "runbook": {"path": "artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md",
                        "sha256": sha_file(OUT / "OWNER_RUNBOOK.md")},
        },
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
    }
    ckpt_path = OUT / "checkpoint.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

    sums = {}
    for f in sorted(OUT.glob("*")):
        if f.is_file() and f.name != "SHA256SUMS.txt":
            sums[str(f.relative_to(ROOT))] = sha_file(f)
    (OUT / "SHA256SUMS.txt").write_text(
        "".join(f"{h}  {p}\n" for p, h in sorted(sums.items()))
    )

    print(json.dumps({
        "verdict": report["verdict"],
        "rev30_manifest_sha256": report["new_freeze"]["manifest_sha256"],
        "freeze_identity": report["new_freeze"]["identity"],
        "checks": checks,
        "mutants_met": f"{sum(1 for m in mutants if m['expectation_met'])}/{len(mutants)}",
        "pin_moves": moved_paths,
        "canonical_unchanged": report["canonical_read_only"]["unchanged"],
        "report": str(rep_path.relative_to(ROOT)),
    }, indent=1))
    return 0 if report["verdict"] == "REV30_FREEZE_REHEARSAL_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
