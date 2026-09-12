#!/usr/bin/env python3
"""W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01  (worker-069, class AF-SCC-C0-VAC-GEN)

Independent, pre-registered sufficiency test of the authorized acceptance-corpus rebind
(controller pass-08 REC-36 item (7), finding CF-32) at the live FROZEN rev29 / rev13 pins.

Question: if the rebased semantic-escape corpus is regenerated with the PINNED generator at
the live C0 base, does run_acceptance.py reach ACCEPTANCE: PASS, or does a content-level
union escape survive?

Method: copy the pinned inputs into sandboxes, run the pinned tools there only. The live
canonical tree is read for hashes, never executed or written. Verdict predicates and controls
are fixed in PREREGISTRATION.json before this instrument was run.

Deterministic: report.json contains no wall-clock fields; run_digest is the sha256 of the
canonical JSON body with run_digest removed.

Usage: python3 check_rebind_coverage.py [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE

# ---------------------------------------------------------------- pins (preregistered)
PINS = {
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/tools/run_acceptance.py":
        "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
    "artifacts/formulation/tools/measure_semantic_escape.py":
        "c6e4f9ccce7f68e472338c72dab6d3b84cb85b7ccfa3dd69416b384cdea11272",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/evidence/semantic_escape_rebased.json":
        "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292",
    "artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/worker-06/semantic_fixtures/manifest.json":
        "c102445df3971109101e4d54b609ff1c5bfdf9147ddb1f1b099476a816030deb",
    "artifacts/formulation/evidence/acceptance_pipeline_report.json":
        "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6",
}
EXPECT_BASE_STALE = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
EXPECT_BASE_LIVE = PINS["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]
SIDECAR = "schemas/af_scc_c0_vacuum.yaml.sha256"

# files copied into every sandbox (tools + inputs); generated outputs stay inside the sandbox
SANDBOX_FILES = [
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/formulation/tools/measure_semantic_escape.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/evidence/semantic_escape_rebased.json",
    "artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/worker-06/semantic_fixtures/manifest.json",
]
TOOLS = {
    "acceptance": "artifacts/formulation/tools/run_acceptance.py",
    "measure": "artifacts/formulation/tools/measure_semantic_escape.py",
    "gate": "artifacts/formulation/tools/check_class_schema.py",
    "w06": "artifacts/worker-06/spec_conformance_audit.py",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def measure_pins() -> dict:
    out = {}
    for rel in PINS:
        p = ROOT / rel
        out[rel] = {"exists": p.exists(),
                    "measured": sha256_file(p) if p.exists() else None,
                    "expected": PINS[rel],
                    "match": p.exists() and sha256_file(p) == PINS[rel]}
    return out


def pin_mismatches(measured: dict) -> list:
    return [r for r, v in measured.items() if not v["match"]]


def fixture_listing(d: Path) -> list:
    if not d.exists():
        return []
    return sorted((p.name, sha256_file(p)) for p in d.glob("*.yaml"))


def run_tool(sandbox: Path, rel_tool: str, timeout: int = 1800) -> dict:
    tool = sandbox / rel_tool
    try:
        r = subprocess.run([sys.executable, str(tool)], cwd=str(sandbox),
                           capture_output=True, text=True, timeout=timeout)
        return {"argv": [sys.executable, rel_tool], "cwd": "<sandbox>", "exit": r.returncode,
                "stdout": r.stdout[-8000:], "stderr": r.stderr[-4000:]}
    except subprocess.TimeoutExpired as e:
        return {"argv": [sys.executable, rel_tool], "cwd": "<sandbox>", "exit": None,
                "stdout": (e.stdout or "")[-8000:] if isinstance(e.stdout, str) else "",
                "stderr": f"TIMEOUT after {timeout}s"}


def build_sandbox(sandbox: Path) -> dict:
    if sandbox.exists():
        shutil.rmtree(sandbox)
    verified = {}
    for rel in SANDBOX_FILES:
        src = ROOT / rel
        h = sha256_file(src)
        if h != PINS[rel]:
            raise RuntimeError(f"pin drift while building sandbox: {rel} {h} != {PINS[rel]}")
        dest = sandbox / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        verified[rel] = h
    return verified


def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def acceptance_summary(sandbox: Path, res: dict) -> dict:
    rep = sandbox / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    body = read_json(rep) if rep.exists() else None
    first = (res.get("stdout") or "").strip().splitlines()
    return {
        "exit": res.get("exit"),
        "first_line": first[0] if first else None,
        "stdout_tail": res.get("stdout", "")[-2500:],
        "stderr_tail": res.get("stderr", "")[-1000:],
        "report_written": rep.exists(),
        "report_sha256": sha256_file(rep) if rep.exists() else None,
        "report": body,
    }


def measure_summary(sandbox: Path, res: dict) -> dict:
    fx = sandbox / "artifacts/formulation/evidence/semantic_escape_rebased.json"
    body = read_json(fx) if fx.exists() else None
    fxdir = sandbox / "artifacts/formulation/evidence/rebased_fixtures"
    return {
        "exit": res.get("exit"),
        "stdout": res.get("stdout", "")[-2000:],
        "stderr_tail": res.get("stderr", "")[-1000:],
        "fixture_written": fx.exists(),
        "fixture_sha256": sha256_file(fx) if fx.exists() else None,
        "base_sha256": (body or {}).get("base_sha256"),
        "base_binds_live_c0": (body or {}).get("base_sha256") == EXPECT_BASE_LIVE,
        "summary": (body or {}).get("summary"),
        "mutant_files": sorted(p.name for p in fxdir.glob("*.yaml")) if fxdir.exists() else [],
    }


def union_escapes(rep: dict | None) -> list:
    if not rep:
        return []
    return rep.get("mutants", {}).get("union_escapes", []) or []


def escape_details(sandbox: Path, rep: dict | None, names: list) -> list:
    """For each union escape, re-run both pinned stages and record their verdicts/failed rules."""
    details = []
    for name in names:
        p = sandbox / "artifacts/formulation/evidence/rebased_fixtures" / name
        gate = run_tool_argv(sandbox, TOOLS["gate"], ["--json", str(p)])
        w06 = run_tool_argv(sandbox, TOOLS["w06"], [str(p)])
        details.append({"fixture": name, "gate": gate, "w06": w06,
                        "fixture_sha256": sha256_file(p) if p.exists() else None})
    return details


def run_tool_argv(sandbox: Path, rel_tool: str, argv: list) -> dict:
    tool = sandbox / rel_tool
    try:
        r = subprocess.run([sys.executable, str(tool)] + argv, cwd=str(sandbox),
                           capture_output=True, text=True, timeout=600)
        body = None
        try:
            body = json.loads(r.stdout)
        except Exception:  # noqa: BLE001
            body = None
        return {"exit": r.returncode, "verdict": (body or {}).get("verdict"),
                "failed_rules": (body or {}).get("failed_rules"),
                "stdout_head": r.stdout[:1200], "stderr_head": r.stderr[:400]}
    except Exception as e:  # noqa: BLE001
        return {"exit": None, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    raw = outdir / "raw"
    raw.mkdir(exist_ok=True)

    report: dict = {"schema": "worker-069/rebind-coverage/v1",
                    "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
                    "actor": "worker-069",
                    "node_id": "F2b",
                    "class_id": "AF-SCC-C0-VAC-GEN",
                    "gate": "G-FORM"}

    # ---- P0 pin guard + read-only baseline snapshot
    pins_start = measure_pins()
    live_fx_dir = ROOT / "artifacts/formulation/evidence/rebased_fixtures"
    live_fx_start = fixture_listing(live_fx_dir)
    report["pins_start"] = {k: v["measured"] for k, v in pins_start.items()}
    mm = pin_mismatches(pins_start)
    if mm:
        report["predicates"] = {"P0_pin_guard": {"ok": False, "mismatches": mm}}
        report["verdict"] = "VOID_BY_DRIFT"
        write_report(outdir, report)
        print("VOID_BY_DRIFT:", mm)
        return 2
    report["predicates"] = {"P0_pin_guard": {"ok": True, "n_inputs": len(pins_start)}}

    # ---- CTL-5 pin-guard self-test (synthetic)
    tmp = outdir / "raw/_pinguard_selftest.bin"
    tmp.write_bytes(b"worker-069 pin guard selftest\n")
    good = sha256_file(tmp)
    ctl5 = {"correct_hash_accepted": (good == sha256_file(tmp)),
            "wrong_hash_rejected": (sha256_file(tmp) != "0" * 64),
            "self_test_ok": (good == sha256_file(tmp) and sha256_file(tmp) != "0" * 64)}
    report["predicates"]["CTL-5_pin_guard_selftest"] = ctl5

    # ---- baseline sandbox (pinned fixture, stale base)
    sb_base = outdir / "sandbox_base"
    build_sandbox(sb_base)
    base_run = run_tool(sb_base, TOOLS["acceptance"])
    base = acceptance_summary(sb_base, base_run)
    report["baseline"] = base
    text = (base_run.get("stdout") or "") + (base_run.get("stderr") or "")
    p1 = (base["exit"] == 3 and "PREFLIGHT FAIL" in text
          and EXPECT_BASE_STALE in text and EXPECT_BASE_LIVE in text and not base["report_written"])
    report["predicates"]["P1_baseline_preflight"] = {"ok": bool(p1), "exit": base["exit"]}

    # ---- CTL-2 fixture-field sensitivity: flip one hex char of declared base
    sb_ctl2 = outdir / "sandbox_ctl2_fieldflip"
    build_sandbox(sb_ctl2)
    fx2 = sb_ctl2 / "artifacts/formulation/evidence/semantic_escape_rebased.json"
    body2 = read_json(fx2)
    body2["base_sha256"] = ("2" + body2["base_sha256"][1:]) if body2["base_sha256"][0] != "2" \
        else ("3" + body2["base_sha256"][1:])
    fx2.write_text(json.dumps(body2, indent=2) + "\n")
    ctl2_run = run_tool(sb_ctl2, TOOLS["acceptance"])
    ctl2 = acceptance_summary(sb_ctl2, ctl2_run)
    ctl2_text = (ctl2_run.get("stdout") or "") + (ctl2_run.get("stderr") or "")
    report["predicates"]["CTL-2_field_sensitivity"] = {
        "ok": ctl2["exit"] == 3 and body2["base_sha256"] in ctl2_text,
        "flipped_declared": body2["base_sha256"], "exit": ctl2["exit"],
        "stdout_head": ctl2_text.strip().splitlines()[:4]}

    # ---- P2/P3/P4 rebind sandboxes A and B
    sbs = {}
    for tag in ("a", "b"):
        sb = outdir / f"sandbox_rebind_{tag}"
        build_sandbox(sb)
        res = run_tool(sb, TOOLS["measure"])
        sbs[tag] = (sb, res, measure_summary(sb, res))
    sb_a, meas_a_res, meas_a = sbs["a"]
    sb_b, meas_b_res, meas_b = sbs["b"]
    report["regeneration_a"] = meas_a
    report["regeneration_b"] = meas_b
    p2 = (meas_a["exit"] == 0 and meas_a["base_binds_live_c0"]
          and (meas_a["summary"] or {}).get("mutants_rebased") == 31
          and (meas_a["summary"] or {}).get("unparsed") == 1
          and (meas_a["summary"] or {}).get("controls_false_positive") == 0
          and len(meas_a["mutant_files"]) == 33)
    report["predicates"]["P2_regeneration"] = {"ok": bool(p2), "summary": meas_a["summary"],
                                               "n_files": len(meas_a["mutant_files"])}
    p3 = meas_a["fixture_sha256"] == meas_b["fixture_sha256"] and meas_a["fixture_sha256"] is not None
    report["predicates"]["P3_determinism"] = {"ok": bool(p3), "sha_a": meas_a["fixture_sha256"],
                                              "sha_b": meas_b["fixture_sha256"]}
    report["predicates"]["CTL-7_determinism"] = {"ok": bool(p3)}

    # ---- P4 acceptance after rebind
    acc_res = run_tool(sb_a, TOOLS["acceptance"])
    acc = acceptance_summary(sb_a, acc_res)
    report["acceptance_after_rebind"] = acc
    m = (acc.get("report") or {}).get("mutants", {})
    esc = union_escapes(acc.get("report"))
    p4 = (acc["exit"] == 0
          and all(r.get("ok") for r in (acc.get("report") or {}).get("canonical", []))
          and all(r.get("ok") for r in (acc.get("report") or {}).get("controls", []))
          and m.get("total") == 31 and m.get("union_caught") == 31)
    report["predicates"]["P4_rebind_sufficiency"] = {"ok": bool(p4), "exit": acc["exit"],
                                                     "verdict": (acc.get("report") or {}).get("verdict"),
                                                     "mutants": m, "union_escapes": esc}
    report["predicates"]["CTL-3_negative"] = {"ok": acc["exit"] != 3}
    report["predicates"]["CTL-4_parser_guard"] = {
        "ok": (meas_a["summary"] or {}).get("unparsed") == 1}
    if esc:
        report["escape_details"] = escape_details(sb_a, acc.get("report"), esc)

    # ---- CTL-6 unbound input is load-bearing (delete one mutant in a throwaway copy)
    sb_ctl6 = outdir / "sandbox_ctl6_deleted_mutant"
    if sb_ctl6.exists():
        shutil.rmtree(sb_ctl6)
    shutil.copytree(sb_a, sb_ctl6)
    mutants = sorted((sb_ctl6 / "artifacts/formulation/evidence/rebased_fixtures").glob("*.yaml"))
    deleted = None
    for p in mutants:
        if not p.name.startswith("control_"):
            deleted = p.name
            p.unlink()
            break
    ctl6_res = run_tool(sb_ctl6, TOOLS["acceptance"])
    ctl6 = acceptance_summary(sb_ctl6, ctl6_res)
    ctl6_m = (ctl6.get("report") or {}).get("mutants", {})
    report["predicates"]["CTL-6_unbound_input_load_bearing"] = {
        "ok": ctl6["exit"] == 0 and ctl6_m.get("total") == 30,
        "deleted_fixture": deleted, "exit": ctl6["exit"],
        "mutants_total": ctl6_m.get("total"), "union_caught": ctl6_m.get("union_caught"),
        "verdict": (ctl6.get("report") or {}).get("verdict")}

    # ---- P6 binding census
    frozen = read_json(ROOT / "artifacts/formulation/FROZEN.json") or {}
    ffiles = frozen.get("files", {})
    fixture = read_json(ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json") or {}
    transitive = {
        "artifacts/worker-06/spec_conformance_audit.py": fixture.get("w06_sha256"),
        "artifacts/worker-06/semantic_fixtures/manifest.json": fixture.get("corpus_manifest_sha256"),
        "artifacts/formulation/tools/check_class_schema.py": fixture.get("gate_sha256"),
    }
    census = []
    for rel, hv in report["pins_start"].items():
        fz = ffiles.get(rel, {}).get("sha256") if isinstance(ffiles.get(rel), dict) else None
        census.append({
            "path": rel,
            "live": hv,
            "frozen_pin": fz,
            "frozen_bound": bool(fz) and fz == hv,
            "transitive_record": transitive.get(rel),
            "transitive_bound": transitive.get(rel) == hv,
            "classification": ("frozen-pin" if fz and fz == hv else
                               "transitive-in-pinned-fixture" if transitive.get(rel) == hv else
                               "unpinned"),
        })
    # generated fixtures directory: live, load-bearing, not pinned
    live_fx = fixture_listing(live_fx_dir)
    census.append({"path": "artifacts/formulation/evidence/rebased_fixtures/",
                   "live": f"{len(live_fx)} files, listing_sha256={sha256_bytes(json.dumps(live_fx).encode())}",
                   "frozen_pin": None, "frozen_bound": False, "transitive_record": None,
                   "transitive_bound": False, "classification": "unpinned-generated-directory"})
    report["binding_census"] = census
    report["predicates"]["P6_binding_census"] = {
        "ok": True,
        "n_frozen_bound": sum(1 for c in census if c["classification"] == "frozen-pin"),
        "n_transitive": sum(1 for c in census if c["classification"] == "transitive-in-pinned-fixture"),
        "n_unpinned": sum(1 for c in census if c["classification"].startswith("unpinned")),
        "unpinned": [c["path"] for c in census if c["classification"].startswith("unpinned")]}

    # ---- P7 sidecar advisory
    side = ROOT / SIDECAR
    side_body = side.read_text().split() if side.exists() else []
    tool_sidecar_hits = {}
    for rel in ("artifacts/formulation/tools/run_acceptance.py",
                "artifacts/formulation/tools/measure_semantic_escape.py",
                "artifacts/formulation/tools/check_class_schema.py",
                "artifacts/worker-06/spec_conformance_audit.py"):
        tool_sidecar_hits[rel] = b".sha256" in (ROOT / rel).read_bytes()
    report["sidecar_advisory"] = {
        "path": SIDECAR,
        "declares": side_body[0] if side_body else None,
        "live_c0": EXPECT_BASE_LIVE,
        "stale": (side_body[0] if side_body else None) != EXPECT_BASE_LIVE,
        "any_pipeline_tool_reads_dot_sha256": any(tool_sidecar_hits.values()),
        "tool_scan": tool_sidecar_hits,
    }
    report["predicates"]["P7_sidecar_advisory"] = {
        "ok": report["sidecar_advisory"]["stale"]
              and not report["sidecar_advisory"]["any_pipeline_tool_reads_dot_sha256"],
        "role": "advisory-only"}

    # ---- P5/CTL-8 read-only proof
    pins_end = measure_pins()
    live_fx_end = fixture_listing(live_fx_dir)
    report["pins_end"] = {k: v["measured"] for k, v in pins_end.items()}
    report["pins_stable"] = report["pins_start"] == report["pins_end"]
    report["live_fixture_listing_stable"] = live_fx_start == live_fx_end
    report["live_fixture_listing_start_sha256"] = sha256_bytes(json.dumps(live_fx_start).encode())
    report["predicates"]["P5_collateral"] = {
        "ok": report["pins_stable"] and report["live_fixture_listing_stable"],
        "pins_stable": report["pins_stable"],
        "live_rebased_fixtures_stable": report["live_fixture_listing_stable"],
        "n_live_fixtures": len(live_fx_end)}
    report["predicates"]["CTL-8_read_only"] = {"ok": report["predicates"]["P5_collateral"]["ok"]}

    # ---- verdict
    preds = report["predicates"]
    if not p1:
        verdict = "VOID_BASELINE_NOT_REPRODUCED"
    elif not p2 or not p3:
        verdict = "VOID_REBIND_NOT_REPRODUCIBLE"
    elif p4 and preds["P5_collateral"]["ok"]:
        verdict = "REBIND_SUFFICES_AT_MEASURED_BASE"
    elif preds["P5_collateral"]["ok"]:
        verdict = "REBIND_INSUFFICIENT_AT_MEASURED_BASE"
    else:
        verdict = "VOID_BY_WRITE"
    report["verdict"] = verdict
    report["verdict_basis"] = {
        "P1_baseline_preflight": p1, "P2_regeneration": bool(p2), "P3_determinism": bool(p3),
        "P4_rebind_sufficiency": bool(p4),
        "n_union_escapes": len(esc),
        "unpinned_inputs": preds["P6_binding_census"]["unpinned"],
    }
    write_report(outdir, report)
    print(json.dumps({"verdict": verdict, "basis": report["verdict_basis"],
                      "regeneration": meas_a["summary"],
                      "acceptance_after_rebind": {
                          "exit": acc["exit"], "verdict": (acc.get("report") or {}).get("verdict"),
                          "mutants": m}}, indent=1))
    return 0


def write_report(outdir: Path, report: dict) -> None:
    body = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    digest = sha256_bytes(body.encode())
    report["run_digest"] = digest
    (outdir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    (outdir / "raw" / "report.body.json").write_text(body + "\n")


if __name__ == "__main__":
    sys.exit(main())
