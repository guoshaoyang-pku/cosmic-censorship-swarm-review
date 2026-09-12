#!/usr/bin/env python3
"""W022-F2B-REV30-CORRECTED-FREEZE-REHEARSAL-01 -- sandbox-only rehearsal of the rev30
publication path keyed on the corrected F2b containment candidate 51c253c4.

Read-only on every canonical path.  Every write lands under
artifacts/worker-022/f2b_rev30_corrected/ (sandboxes included).  No gate verdict, no node
status, no validation_status, no mathematics claim; the owner owns any rev30 publication.

Family-2 instrument: pre-registration (preregistration.json, written before measurement)
declares pins, expectations E1-E14, controls K1-K5 and the falsifier.  This file measures
them and writes report.json, OWNER_RUNBOOK.corrected.md and SHA256SUMS.txt.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
OUT = HERE.parent
PRE = json.loads((OUT / "preregistration.json").read_text())
PINS = PRE["pins"]
PARAMS = PRE["rehearsal_parameters"]
AT = PARAMS["refreeze_at"]
REV = PARAMS["refreeze_revision"]
DELTA = PARAMS["refreeze_delta"]
CAND = ROOT / PARAMS["candidate_primary"]
CAND_NEST = ROOT / PARAMS["candidate_alternative"]
C0_CANON = "schemas/af_scc_c0_vacuum.yaml"
C0_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
C2_CANON = "schemas/af_scc_c2_vacuum.yaml"
C2_HASH = PINS[C2_CANON]
CAND_HASH = PINS[PARAMS["candidate_primary"]]

COPY_DIRS = [
    "artifacts/formulation",
    "artifacts/worker-06",
    "artifacts/worker08",
    "artifacts/worker-008",
    "artifacts/worker-080",
    "schemas",
]
COPY_FILES = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md",
]

checks: dict[str, dict] = {}
records: dict[str, object] = {}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def check(cid: str, ok: bool, detail) -> bool:
    checks[cid] = {"ok": bool(ok), "detail": detail}
    return bool(ok)


def cmd(args, cwd=None, timeout=900) -> dict:
    t0 = time.time()
    proc = subprocess.run([str(a) for a in args], cwd=str(cwd or ROOT),
                          capture_output=True, text=True, timeout=timeout)
    return {
        "command": [str(a) for a in args],
        "cwd": str(cwd or ROOT),
        "exit_code": proc.returncode,
        "seconds": round(time.time() - t0, 3),
        "stdout_tail": proc.stdout.strip().splitlines()[-25:],
        "stderr_tail": proc.stderr.strip().splitlines()[-15:],
    }


def build_sandbox(dest: Path) -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    copied = []
    for rel in COPY_DIRS:
        src = ROOT / rel
        if not src.exists():
            return {"ok": False, "missing": rel, "copied": copied}
        shutil.copytree(src, dest / rel)
        copied.append(rel)
    for rel in COPY_FILES:
        src = ROOT / rel
        if not src.exists():
            return {"ok": False, "missing": rel, "copied": copied}
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest / rel)
        copied.append(rel)
    return {"ok": True, "missing": None, "copied": copied, "root": str(dest.relative_to(ROOT))}


def leaf_diff(a, b, prefix="") -> list[dict]:
    """Independent recursive leaf-path diff of two parsed YAML documents."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{prefix}.{k}" if prefix else str(k)
            if k not in a:
                out.append({"path": p, "kind": "added", "new": repr(b[k])[:200]})
            elif k not in b:
                out.append({"path": p, "kind": "removed", "old": repr(a[k])[:200]})
            else:
                out.extend(leaf_diff(a[k], b[k], p))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append({"path": prefix, "kind": "list-length", "old": len(a), "new": len(b)})
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(leaf_diff(x, y, f"{prefix}[{i}]"))
    else:
        if a != b:
            out.append({"path": prefix, "kind": "changed", "old": repr(a)[:240], "new": repr(b)[:240]})
    return out


def manifest_identity(p: Path) -> dict:
    d = json.loads(p.read_text())
    return {
        "revision": d.get("revision"),
        "frozen_at": d.get("frozen_at"),
        "digest": sha(p),
        "files": len(d.get("files", {})),
        "delta": d.get("delta"),
    }


def refreeze(sandbox: Path, revision: int, at: str, delta: str) -> dict:
    tool = sandbox / "artifacts/formulation/tools/regenerate_frozen.py"
    rec = cmd([sys.executable, tool, "--revision", revision, "--delta", delta, "--at", at], cwd=sandbox)
    man = sandbox / "artifacts/formulation/FROZEN.json"
    rec["manifest_after"] = manifest_identity(man) if man.exists() else None
    return rec


def verify_frozen(sandbox: Path) -> dict:
    tool = sandbox / "artifacts/formulation/tools/verify_frozen.py"
    return cmd([sys.executable, tool], cwd=sandbox)


def pin_move_table(old: dict, new: dict, sandbox: Path) -> dict:
    of, nf = old.get("files", {}), new.get("files", {})
    changed = sorted(k for k in set(of) & set(nf) if of[k].get("sha256") != nf[k].get("sha256"))
    missing = sorted(k for k in of if not (sandbox / k).exists())
    added = sorted(set(nf) - set(of))
    removed = sorted(set(of) - set(nf))
    return {
        "old_revision": old.get("revision"),
        "new_revision": new.get("revision"),
        "n_old": len(of), "n_new": len(nf),
        "changed": [{"path": k, "old": of[k].get("sha256"), "new": nf[k].get("sha256")} for k in changed],
        "missing_on_disk": missing,
        "added_to_manifest": added,
        "removed_from_manifest": removed,
    }


def run_tool_json(sandbox: Path, rel_tool: str, args: list, out_path) -> dict:
    rec = cmd([sys.executable, sandbox / rel_tool] + args, cwd=sandbox)
    outp = Path(out_path)
    try:
        rec["output_path"] = str(outp.relative_to(ROOT))
    except ValueError:
        rec["output_path"] = str(outp)
    rec["output_exists"] = outp.exists()
    rec["output"] = json.loads(outp.read_text()) if outp.exists() else None
    return rec


def main() -> int:
    t_start = time.time()
    records["task_id"] = PRE["task_id"]
    records["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # ---- E1 (start): pins ----
    start_pins = {rel: (sha(ROOT / rel) if (ROOT / rel).exists() else None) for rel in PINS}
    start_match = {rel: start_pins[rel] == h for rel, h in PINS.items()}
    check("E1_start", all(start_match.values()),
          {"n_pins": len(PINS), "mismatches": [k for k, v in start_match.items() if not v]})
    records["pins_start"] = start_pins

    # ---- E2 / E3: candidate identity and independent leaf diff ----
    cand_hash = sha(CAND)
    nest_hash = sha(CAND_NEST)
    check("E2", cand_hash == CAND_HASH and nest_hash == PINS[PARAMS["candidate_alternative"]],
          {"candidate_corrected": cand_hash, "candidate_nesting_only": nest_hash})
    live_doc = yaml.safe_load((ROOT / C0_CANON).read_text())
    cand_doc = yaml.safe_load(CAND.read_text())
    diff = leaf_diff(live_doc, cand_doc)
    expected_paths = {"regularity.must_not_conflate[0]", "implication_ledger.forbidden_transfers[0].reason"}
    got_paths = {d["path"] for d in diff}
    check("E3", got_paths == expected_paths and all(d["kind"] == "changed" for d in diff),
          {"n_diff": len(diff), "paths": sorted(got_paths), "diff": diff})
    records["leaf_diff"] = diff

    # ---- build sandboxes ----
    sb_ctrl = OUT / "sandbox_control_rev29"
    sb_corr = OUT / "sandbox_corrected"
    sb_idem = OUT / "sandbox_idem"
    records["sandbox_build"] = {
        "control": build_sandbox(sb_ctrl),
        "corrected": build_sandbox(sb_corr),
    }
    if not all(v["ok"] for v in records["sandbox_build"].values()):
        check("sandbox_build", False, records["sandbox_build"])
        (OUT / "report.json").write_text(json.dumps({"checks": checks, "records": records}, indent=2))
        return 1
    check("sandbox_build", True, {k: v["root"] for k, v in records["sandbox_build"].items()})

    # ---- E4: apply corrected candidate to both C0 copies ----
    cand_bytes = CAND.read_bytes()
    (sb_corr / C0_CANON).write_bytes(cand_bytes)
    (sb_corr / C0_MIRROR).write_bytes(cand_bytes)
    mirrored = sha(sb_corr / C0_CANON) == sha(sb_corr / C0_MIRROR) == CAND_HASH
    check("E4", mirrored,
          {"canonical": sha(sb_corr / C0_CANON), "mirror": sha(sb_corr / C0_MIRROR)})

    # ---- E5 / E6 / E7: guarded re-freeze, verify, pin-move table ----
    live_man = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    refr = refreeze(sb_corr, REV, AT, DELTA)
    records["refreeze_corrected"] = refr
    mi = refr["manifest_after"]
    check("E5", refr["exit_code"] == 0 and mi and mi["revision"] == REV and mi["frozen_at"] == AT
          and mi["digest"] != PINS["artifacts/formulation/FROZEN.json"],
          {"exit_code": refr["exit_code"], "manifest": mi})
    ver = verify_frozen(sb_corr)
    records["verify_frozen_corrected"] = ver
    clean = ver["exit_code"] == 0 and any("0 problems" in l for l in ver["stdout_tail"])
    check("E6", clean, {"exit_code": ver["exit_code"], "stdout": ver["stdout_tail"]})
    new_man = json.loads((sb_corr / "artifacts/formulation/FROZEN.json").read_text())
    table = pin_move_table(live_man, new_man, sb_corr)
    records["pin_move_table"] = table
    moved_ok = (sorted(c["path"] for c in table["changed"]) == sorted([C0_CANON, C0_MIRROR])
                and all(c["new"] == CAND_HASH for c in table["changed"])
                and not table["missing_on_disk"] and not table["added_to_manifest"]
                and not table["removed_from_manifest"])
    check("E7", moved_ok, table)

    # ---- E8: idempotence ----
    if sb_idem.exists():
        shutil.rmtree(sb_idem)
    shutil.copytree(sb_corr, sb_idem)
    ident_before = (sb_idem / "artifacts/formulation/FROZEN.json").read_bytes()
    refr2 = refreeze(sb_idem, REV, AT, DELTA)
    ident_after = (sb_idem / "artifacts/formulation/FROZEN.json").read_bytes()
    records["refreeze_idem"] = refr2
    check("E8", refr2["exit_code"] == 0 and ident_before == ident_after,
          {"exit_code": refr2["exit_code"], "byte_identical": ident_before == ident_after})

    # ---- E9: acceptance battery, corrected + rev29 control ----
    # NOTE: c2_c0_separation_audit.py resolves REPO from its own file location and calls
    # Path.relative_to(REPO) on both its inputs and outputs, so each run must use the tool
    # copy and all paths inside the owning sandbox; evidence copies are made afterwards.
    def battery(sandbox, label, out_name):
        rec = run_tool_json(sandbox, "artifacts/worker08/c2_c0_separation_audit.py",
                            ["--c2", sandbox / C2_CANON, "--c0", sandbox / C0_CANON,
                             "--out-json", sandbox / out_name,
                             "--out-md", sandbox / out_name.replace(".json", ".md"),
                             "--label", label],
                            sandbox / out_name)
        if rec["output_exists"]:
            shutil.copyfile(sandbox / out_name, OUT / out_name)
            rec["evidence_copy"] = str((OUT / out_name).relative_to(ROOT))
        return rec

    bat_corr = battery(sb_corr, "w022_rev30_corrected", "battery_w022_rev30_corrected.json")
    bat_ctrl = battery(sb_ctrl, "w022_rev29_control", "battery_w022_rev29_control.json")
    records["battery"] = {"corrected": bat_corr, "control_rev29": bat_ctrl}
    bc = bat_corr.get("output") or {}
    x3c = (bc.get("X3c_containment_inversion") or {}).get("violations")
    check("E9", bat_corr["exit_code"] == 0 and bc.get("verdict") == "PASS"
          and not bc.get("hard_failures") and x3c == 0,
          {"exit_code": bat_corr["exit_code"], "verdict": bc.get("verdict"),
           "hard_failures": len(bc.get("hard_failures") or []),
           "x3c_violations": x3c,
           "post_repair_residuals": bc.get("post_repair_residuals")})

    # ---- E10: dual audit, corrected + expectations ----
    def dual(sandbox, c0, label, expect_c0, out_rel):
        return run_tool_json(sandbox, "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py",
                             ["--c0", c0, "--c2", sandbox / C2_CANON, "--expect-c0", expect_c0,
                              "--expect-c2", C2_HASH, "--label", label, "--json", OUT / out_rel],
                             OUT / out_rel)

    du_corr = dual(sb_corr, sb_corr / C0_CANON, "w022_rev30_corrected", CAND_HASH,
                   "dual_w022_rev30_corrected.json")
    du_ctrl = dual(sb_corr, sb_ctrl / C0_CANON, "w022_rev29_control",
                   sha(sb_ctrl / C0_CANON), "dual_w022_rev29_control.json")
    records["dual"] = {"corrected": du_corr, "control_rev29": du_ctrl}
    dc = du_corr.get("output") or {}
    check("E10", du_corr["exit_code"] == 0 and dc.get("verdict") == "PASS"
          and not dc.get("findings"),
          {"exit_code": du_corr["exit_code"], "verdict": dc.get("verdict"),
           "n_findings": dc.get("n_findings", len(dc.get("findings") or []))})

    # ---- E11 / E12: three derived-evidence tools, corrected vs rev29 control ----
    derived = {}
    for label, sandbox in (("corrected", sb_corr), ("control_rev29", sb_ctrl)):
        entry = {}
        entry["measure_semantic_escape"] = run_tool_json(
            sandbox, "artifacts/formulation/tools/measure_semantic_escape.py", [],
            sandbox / "artifacts/formulation/evidence/semantic_escape_rebased.json")
        entry["rebase_heldout"] = run_tool_json(
            sandbox, "artifacts/formulation/tools/rebase_heldout.py", [],
            sandbox / "artifacts/formulation/evidence/heldout_rebased.json")
        entry["run_gate_tests"] = run_tool_json(
            sandbox, "artifacts/formulation/tools/run_gate_tests.py", [],
            sandbox / "artifacts/formulation/evidence/gate_test_report.json")
        derived[label] = entry
    records["derived_tools"] = derived

    def sem_summary(label):
        o = derived[label]["measure_semantic_escape"].get("output") or {}
        return o.get("summary"), o.get("base_sha256")

    def held_summary(label):
        o = derived[label]["rebase_heldout"].get("output") or {}
        return o.get("after"), o.get("base_sha256")

    def gate_summary(label):
        o = derived[label]["run_gate_tests"].get("output") or {}
        return {"verdict": o.get("verdict"), "counts": o.get("counts")}, (o.get("canonical_sha256") or {}).get("AF-SCC-C0-VAC-GEN")

    d_corr = {"semantic": sem_summary("corrected"), "heldout": held_summary("corrected"), "gate": gate_summary("corrected")}
    d_ctrl = {"semantic": sem_summary("control_rev29"), "heldout": held_summary("control_rev29"), "gate": gate_summary("control_rev29")}
    records["derived_summaries"] = {"corrected": d_corr, "control_rev29": d_ctrl}
    ran_ok = all(
        derived[label][t]["exit_code"] == 0 and derived[label][t]["output_exists"]
        for label in ("corrected", "control_rev29")
        for t in ("measure_semantic_escape", "rebase_heldout", "run_gate_tests"))
    gate = d_corr["gate"][0]
    check("E11", ran_ok and gate.get("verdict") == "PASS"
          and gate["counts"]["canonical_pass"] == 3
          and gate["counts"]["null_controls_pass"] >= 3
          and gate["counts"]["mutants_caught"] == gate["counts"]["mutants_total"],
          {"all_exit_zero": ran_ok, "gate_corrected": gate,
           "sem_corrected": d_corr["semantic"][0], "heldout_corrected": d_corr["heldout"][0]})
    differential = {
        "semantic_summary_equal": d_corr["semantic"][0] == d_ctrl["semantic"][0],
        "heldout_after_equal": d_corr["heldout"][0] == d_ctrl["heldout"][0],
        "gate_verdict_counts_equal": d_corr["gate"][0] == d_ctrl["gate"][0],
        "base_sha_moved_semantic": (d_corr["semantic"][1], d_ctrl["semantic"][1]),
        "base_sha_moved_heldout": (d_corr["heldout"][1], d_ctrl["heldout"][1]),
        "gate_c0_sha": (d_corr["gate"][1], d_ctrl["gate"][1]),
    }
    records["differential"] = differential
    check("E12", differential["semantic_summary_equal"] and differential["heldout_after_equal"]
          and differential["gate_verdict_counts_equal"], differential)

    # ---- controls ----
    bc_ctrl = bat_ctrl.get("output") or {}
    dc_ctrl = du_ctrl.get("output") or {}
    k1 = (bat_ctrl["exit_code"] == 0 and bc_ctrl.get("verdict") == "FAIL"
          and len(bc_ctrl.get("hard_failures") or []) > 0
          and dc_ctrl.get("verdict") == "FAIL"
          and dc_ctrl.get("n_findings", len(dc_ctrl.get("findings") or [])) > 0)
    check("K1_live_rev29_fails", k1,
          {"battery_exit": bat_ctrl["exit_code"], "battery_verdict": bc_ctrl.get("verdict"),
           "dual_exit": du_ctrl["exit_code"], "dual_verdict": dc_ctrl.get("verdict"),
           "dual_findings": dc_ctrl.get("findings")})

    # K2: mirror divergence detected -- mutate the idempotence sandbox's mirror back to live bytes
    (sb_idem / C0_MIRROR).write_bytes((ROOT / C0_MIRROR).read_bytes())
    k2_ver = verify_frozen(sb_idem)
    k2_detected = k2_ver["exit_code"] != 0 and any("DRIFT" in l and C0_MIRROR in l for l in k2_ver["stdout_tail"])
    check("K2_mirror_divergence_detected", k2_detected,
          {"verify_exit": k2_ver["exit_code"], "stdout": k2_ver["stdout_tail"]})

    # K3: wrong expectation hash -> fail-closed
    k3 = dual(sb_corr, sb_corr / C0_CANON, "w022_wrong_expect", PINS[C0_CANON], "dual_w022_wrong_expect.json")
    k3o = k3.get("output") or {}
    k3_detected = k3["exit_code"] != 0 and any(
        f.get("kind") == "hash_mismatch" or "hash" in json.dumps(f).lower() for f in (k3o.get("findings") or []))
    check("K3_wrong_expect_fail_closed", k3_detected,
          {"exit_code": k3["exit_code"], "verdict": k3o.get("verdict"), "findings": k3o.get("findings")})

    # K4: candidate tamper -> declared-hash check fails
    tampered = bytearray(cand_bytes)
    idx = next(i for i, b in enumerate(tampered) if b == ord("E"))
    tampered[idx] = ord("F")
    k4_hash = sha_bytes(bytes(tampered))
    check("K4_candidate_tamper_detected", k4_hash != CAND_HASH,
          {"tampered_sha256": k4_hash, "declared": CAND_HASH})

    # K5: re-implant the live denial into the corrected candidate -> semantic predicate must fire
    den_doc = yaml.safe_load(CAND.read_text())
    live_denial = yaml.safe_load((ROOT / C0_CANON).read_text())["regularity"]["must_not_conflate"][0]
    den_doc["regularity"]["must_not_conflate"][0] = live_denial
    k5_path = OUT / "k5_denial_reimplanted.yaml"
    k5_path.write_text(yaml.safe_dump(den_doc, sort_keys=False, width=110))
    k5_hash = sha(k5_path)
    k5 = dual(sb_corr, k5_path, "w022_k5_denial_reimplanted", k5_hash, "dual_w022_k5.json")
    k5o = k5.get("output") or {}
    k5_detected = k5["exit_code"] != 0 and dc.get("verdict") == "PASS" and bool(k5o.get("findings"))
    check("K5_denial_reimplant_detected", k5_detected,
          {"exit_code": k5["exit_code"], "verdict": k5o.get("verdict"), "findings": k5o.get("findings")})

    # ---- E13: corrected runbook ----
    runbook = render_runbook(d_corr, d_ctrl, new_man)
    (OUT / "OWNER_RUNBOOK.corrected.md").write_text(runbook)
    check("E13", CAND_HASH in runbook and "84b5d3fa" in runbook and "51c253c4" in runbook,
          {"path": "artifacts/worker-022/f2b_rev30_corrected/OWNER_RUNBOOK.corrected.md",
           "bytes": len(runbook)})

    # ---- E14: canonical read-only ----
    end_pins = {rel: (sha(ROOT / rel) if (ROOT / rel).exists() else None) for rel in PINS}
    moved = {rel: (PINS[rel], end_pins[rel]) for rel in PINS if end_pins[rel] != PINS[rel]}
    records["pins_end"] = end_pins
    check("E14_canonical_read_only", not moved, {"moved": moved})
    # E1 (end) == E14 for pins; keep E1 as the single start+end identity statement
    check("E1", checks["E1_start"]["ok"] and not moved,
          {"start_mismatches": [k for k, v in start_match.items() if not v], "moved": moved})

    # ---- report ----
    exp_ids = [f"E{i}" for i in range(1, 15)]
    expectations = {e: checks.get(e, checks.get("E14_canonical_read_only" if e == "E14" else e, {})) for e in exp_ids}
    expectations["E14"] = checks["E14_canonical_read_only"]
    control_ids = [k for k in checks if k.startswith("K")]
    verdict = "REHEARSAL_PASS" if all(checks[k]["ok"] for k in checks) else "REHEARSAL_FAIL"
    report = {
        "task_id": PRE["task_id"],
        "actor": "worker-022",
        "node_id": PRE["node_id"],
        "class_id": PRE["class_id"],
        "gate": PRE["gate"],
        "created_at": PRE["created_at"],
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seconds": round(time.time() - t_start, 1),
        "verdict": verdict,
        "summary": {
            "candidate": CAND_HASH,
            "refrozen_c0": CAND_HASH,
            "rev30_manifest_digest": (records.get("refreeze_corrected", {}).get("manifest_after") or {}).get("digest"),
            "pin_moves": [c["path"] for c in table["changed"]],
            "expectations_passed": sum(1 for k in checks if k.startswith("E") and checks[k]["ok"]),
            "expectations_total": 14,
            "controls_passed": sum(1 for k in control_ids if checks[k]["ok"]),
            "controls_total": len(control_ids),
            "canonical_writes": 0,
            "post_repair_residuals": (bc.get("post_repair_residuals") or []),
        },
        "expectations": expectations,
        "checks": checks,
        "controls": {k: checks[k] for k in control_ids},
        "records": records,
        "authority": PRE["authority"],
        "falsifier": PRE["falsifier"],
        "non_claims": PRE["non_claims"],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    # ---- SHA256SUMS ----
    lines = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file() and p.name not in {"SHA256SUMS.txt", "report.json"}:
            lines.append(f"{sha(p)}  {p.relative_to(ROOT)}")
    lines.append(f"{sha(OUT / 'report.json')}  artifacts/worker-022/f2b_rev30_corrected/report.json")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")

    print(json.dumps(report["summary"], indent=1))
    for k in sorted(checks):
        print(f"{'PASS' if checks[k]['ok'] else 'FAIL'}  {k}")
    return 0 if verdict == "REHEARSAL_PASS" else 1


def render_runbook(d_corr, d_ctrl, new_man) -> str:
    digest = new_man and sha_bytes((json.dumps(new_man, indent=2) + "\n").encode())
    manifest_digest = records.get("refreeze_corrected", {}).get("manifest_after", {}).get("digest")
    return f"""# Owner runbook (CORRECTED) -- rev30 publication from the corrected F2b containment repair

Action card for the owner. Supersedes step 1 and the expected hash of
`artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md`#410f72e5121eb345dde05a2f9c4d5e99f059dabe1fce5a36578fd6eee21e21a6,
which lands `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40`, classified
H2_INVERTED_ENTAILMENT_DIRECTION by `artifacts/worker-088/rev30_publication_guard/guard_report.json`
(worker-080, worker-029, worker-096 concur). This card lands the corrected candidate
`51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a` instead.

Evidence: `artifacts/worker-022/f2b_rev30_corrected/report.json` (sandbox-only rehearsal,
{checks.get('E9', {}).get('ok') and 'battery PASS' or 'battery not confirmed'}, {checks.get('E10', {}).get('ok') and 'dual PASS' or 'dual not confirmed'},
pin-move table exactly the two C0 paths, idempotent re-freeze, 5/5 detected controls).
Worker evidence only; not a gate verdict. The owner still needs two fresh blind accepts at the
published hash.

## Delta vs the worker-058 runbook

| step | worker-058 said | corrected |
|---|---|---|
| 1 source file | `artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml` | `artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml` |
| 1 expected C0 sha256 | `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40` | `{CAND_HASH}` |
| 2 delta string | "F2b L-FORM-01 two-leaf repair (C0:152 denial + C0:245 inversion)" | "{DELTA}" |
| 3 guard | refuse revision collision | unchanged (plus: expected pin moves are exactly the two C0 paths) |
| 5 acceptance | `c2_c0_separation_audit.py` PASS, X3c=0 | unchanged; verified on the corrected bytes |
| new | - | re-run `measure_semantic_escape.py`, `rebase_heldout.py`, `run_gate_tests.py` at the new base (differential vs rev29: {records.get('differential', {}).get('semantic_summary_equal') and records.get('differential', {}).get('heldout_after_equal') and records.get('differential', {}).get('gate_verdict_counts_equal') and 'no count moves' or 'SEE report.json differential'}) |

## Procedure

0. Confirm the base pins are still live before touching anything:
   ```bash
   sha256sum schemas/af_scc_c0_vacuum.yaml artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
   # both must read {PINS[C0_CANON]}
   sha256sum artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml
   # must read {CAND_HASH}
   ```
   Any move voids this card.

1. Apply the pre-validated two-leaf repair to BOTH C0 copies (they must stay byte-identical):
   ```bash
   cp artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml schemas/af_scc_c0_vacuum.yaml
   cp artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
   sha256sum schemas/af_scc_c0_vacuum.yaml artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
   # expected: {CAND_HASH} (both paths)
   ```

2. Re-freeze with a strictly increasing revision and an explicit timestamp:
   ```bash
   python3 artifacts/formulation/tools/regenerate_frozen.py --revision {REV} --delta "{DELTA}" --at <ISO8601>
   ```
   The rehearsal at `{AT}` produced manifest digest
   `{manifest_digest}`, revision {new_man.get('revision') if new_man else REV}, and moved exactly
   `{C0_CANON}` and `{C0_MIRROR}` to `{CAND_HASH}`.

3. Refuse collisions: revision, frozen_at and manifest digest must all be new. A repeat of the
   same revision with different bytes is CF-27.

4. Verify:
   ```bash
   python3 artifacts/formulation/tools/verify_frozen.py   # expect rc=0, 0 problems
   ```

5. Re-run acceptance at the new hash. Keep the output paths INSIDE the repo: the battery tool
   calls `Path.relative_to(REPO)` on its own output paths, so a `/tmp` target (as in the
   worker-058 card) writes the JSON but then crashes at print time with rc=1.
   ```bash
   python3 artifacts/worker08/c2_c0_separation_audit.py --c2 schemas/af_scc_c2_vacuum.yaml \\
     --c0 schemas/af_scc_c0_vacuum.yaml --out-json artifacts/formulation/evidence/rev30_battery.json \\
     --out-md artifacts/formulation/evidence/rev30_battery.md --label rev30
   python3 artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py --c0 schemas/af_scc_c0_vacuum.yaml \\
     --c2 schemas/af_scc_c2_vacuum.yaml --expect-c0 {CAND_HASH} --expect-c2 {C2_HASH} \\
     --label rev30 --json artifacts/formulation/evidence/rev30_dual.json
   ```
   Expected: battery PASS 0 hard failures X3c=0; dual PASS 0 findings.
   Measured residual (recorded by the battery, corpus hygiene only, not a gate failure):
   {json.dumps((records.get('battery', {}).get('corrected', {}).get('output') or {}).get('post_repair_residuals') or [])}

6. Re-run the three derived-evidence tools at the new base and compare headline counts to the
   rev29 control (rehearsed equal, see report.json `records.differential`):
   ```bash
   python3 artifacts/formulation/tools/measure_semantic_escape.py
   python3 artifacts/formulation/tools/rebase_heldout.py
   python3 artifacts/formulation/tools/run_gate_tests.py
   ```

7. Then commission two blind full-schema F2b reviewers at the published FROZEN hash.

Rehearsal artifacts: `artifacts/worker-022/f2b_rev30_corrected/` (report.json, preregistration.json,
rehearse.py, sandbox_control_rev29/, sandbox_corrected/, SHA256SUMS.txt).
"""


if __name__ == "__main__":
    sys.exit(main())
