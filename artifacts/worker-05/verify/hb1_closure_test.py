#!/usr/bin/env python3
"""HF-B1 closure trial for the F0 binding evidence (worker-05, node F2a).

Task (class-bound): AF-SCC-C2-VAC-GEN, F2a, gate G-FORM.
Open blocker HF-B1 (w05-f0bind-rev13-20260912T0103-blocker): the schema rule
"if the declared F0 artifact changes hash, this binding must be refreshed and the
consistency check re-run" cannot be discharged because
artifacts/formulation/evidence/taxonomy_consistency.json records no sha256 of the
compared files, so its bytes are revision-independent and B7 hard-fails.

This harness tests whether the hash-bound successor produced by
gen_hashbound_consistency_evidence.py closes HF-B1, without writing any canonical
path.  Scenarios (all inside artifacts/worker-05/verify/hb1_sandbox/):

  live_pre        live bytes as found: old evidence has no input hashes (defect reproduced)
  before          checker over live bytes + live old evidence -> expect FAIL, B7 only
  base            checker over live bytes + generated hash-bound record -> expect PASS
  stale           generated base record checked against a moved canonical revision
                  -> expect FAIL (V1/V3), i.e. the record is revision-sensitive
  repair          canonical moved + schemas rebound + record regenerated
                  -> expect PASS and a record hash different from base
  determinism     two independent generations over unchanged inputs are byte-identical
  live_post       live canonical/supplement/evidence hashes unchanged (no canonical write)

Falsifier for this harness: the `before` leg passes (defect absent), or the `base`
leg still hard-fails B7, or `stale` passes (record not revision-sensitive), or the
`repair` leg fails with the evidence regenerated and schemas rebound.

Usage: python3 hb1_closure_test.py [--report PATH]
Exit 0 iff every expectation holds; 1 otherwise; 2 on setup error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VERIFY = Path(__file__).resolve().parent
SANDBOX = VERIFY / "hb1_sandbox"
CHECKER = VERIFY / "check_class_binding_drift.py"
GENERATOR = VERIFY / "gen_hashbound_consistency_evidence.py"

CANONICAL_REL = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT_REL = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
SCHEMA_RELS = (
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
)
PROBE_COMMENT = "\n# hb1-closure probe: simulated F0 revision bump (sandbox only)\n"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def checker_report(sandbox: Path, out: Path) -> dict:
    proc = run([sys.executable, str(CHECKER), "--root", str(sandbox), "--json", str(out)])
    try:
        report = json.loads(out.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        report = {"parse_error": proc.stdout[-2000:] + proc.stderr[-2000:]}
    report["exit_code"] = proc.returncode
    return report


def b7_status(report: dict) -> dict:
    out = {}
    for schema in report.get("schemas", []):
        checks = {c["check"]: c["status"] for c in schema.get("checks", [])}
        out[schema["class_id"]] = {
            "verdict": schema.get("verdict"),
            "hard_failures": schema.get("hard_failures", []),
            "B7": checks.get("B7"),
            "B1": checks.get("B1"),
        }
    return out


def verify_record(record_path: Path, canonical: Path, supplement: Path) -> dict:
    """Binding checks on a candidate evidence record (V1-V4)."""
    rec = json.loads(record_path.read_text(encoding="utf-8"))
    canon_sha = sha256_file(canonical)
    supp_sha = sha256_file(supplement)
    blob = json.dumps(rec)
    declared = (rec.get("binding") or {}).get("declared_f0_sha256")
    inputs = rec.get("input_sha256") or {}
    checks = {
        "V1_canonical_input_matches_measured": inputs.get(CANONICAL_REL) == canon_sha,
        "V2_supplement_input_matches_measured": inputs.get(SUPPLEMENT_REL) == supp_sha,
        "V3_declared_f0_matches_measured_canonical": bool(declared) and declared == canon_sha,
        "V4_declared_hash_present_in_record_bytes": bool(declared)
        and (declared in blob or declared[:16] in blob),
    }
    failures = [k for k, ok in checks.items() if not ok]
    return {
        "record": str(record_path),
        "record_sha256": sha256_file(record_path),
        "measured": {"canonical": canon_sha, "supplement": supp_sha},
        "checks": checks,
        "hard_failures": failures,
        "verdict": "fail" if failures else "pass",
    }


def fill_sandbox(name: str, canonical_bytes: bytes, evidence: bytes) -> Path:
    sb = SANDBOX / name
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "research_map").mkdir(parents=True)
    (sb / "artifacts/formulation/evidence").mkdir(parents=True)
    (sb / "schemas").mkdir(parents=True)
    (sb / CANONICAL_REL).write_bytes(canonical_bytes)
    shutil.copyfile(ROOT / SUPPLEMENT_REL, sb / SUPPLEMENT_REL)
    for rel in SCHEMA_RELS:
        shutil.copyfile(ROOT / rel, sb / rel)
    (sb / EVIDENCE_REL).write_bytes(evidence)
    return sb


def generate(sandbox: Path, out_rel: str) -> dict:
    out = sandbox / out_rel
    proc = run([sys.executable, str(GENERATOR), "--root", str(sandbox), "--out", str(out)])
    if proc.returncode != 0:
        raise RuntimeError(f"generator failed: {proc.stderr}")
    return json.loads(proc.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=str(VERIFY / "hb1_closure_report.json"))
    args = ap.parse_args()

    for tool in (CHECKER, GENERATOR):
        if not tool.exists():
            print(f"missing tool: {tool}", file=sys.stderr)
            return 2

    live = {
        "canonical": ROOT / CANONICAL_REL,
        "supplement": ROOT / SUPPLEMENT_REL,
        "evidence": ROOT / EVIDENCE_REL,
    }
    live_pre = {k: sha256_file(v) for k, v in live.items()}
    live_old_evidence = live["evidence"].read_bytes()
    live_old_doc = json.loads(live_old_evidence)
    defect_present = "input_sha256" not in live_old_doc and "map_taxonomy_sha256" not in live_old_doc

    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)

    result: dict = {
        "harness": "hb1_closure_test.py",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "task": "HF-B1 hash-bound evidence closure trial (no canonical writes)",
        "live_pre_sha256": live_pre,
        "defect_present_in_live_evidence": defect_present,
        "scenarios": {},
        "canonical_writes": [],
    }
    expectations: list[tuple[str, bool, str]] = []
    def expect(name, ok, detail):
        expectations.append((name, bool(ok), detail))

    # ---- before: live bytes + live old evidence -> expect B7-only hard fail
    sb_before = fill_sandbox("before", live["canonical"].read_bytes(), live_old_evidence)
    rep_before = checker_report(sb_before, SANDBOX / "before_checker_report.json")
    b7_before = b7_status(rep_before)
    result["scenarios"]["before"] = {"checker": b7_before, "exit_code": rep_before.get("exit_code")}
    expect("before: checker fails", rep_before.get("verdict") == "fail",
           f"verdict={rep_before.get('verdict')}")
    expect("before: every hard failure is B7",
           all(all(f.startswith("B7") for f in v["hard_failures"]) for v in b7_before.values())
           and len(b7_before) == 3 and all(v["hard_failures"] for v in b7_before.values()),
           json.dumps(b7_before))

    # ---- base: live bytes + generated hash-bound record -> expect PASS
    sb_base = fill_sandbox("base", live["canonical"].read_bytes(), live_old_evidence)
    gen_base = generate(sb_base, EVIDENCE_REL)
    rec_base = sb_base / EVIDENCE_REL
    rep_base = checker_report(sb_base, SANDBOX / "base_checker_report.json")
    b7_base = b7_status(rep_base)
    vb_base = verify_record(rec_base, sb_base / CANONICAL_REL, sb_base / SUPPLEMENT_REL)
    result["scenarios"]["base"] = {
        "generated_sha256": gen_base["sha256"],
        "checker": b7_base,
        "exit_code": rep_base.get("exit_code"),
        "record_verify": vb_base,
    }
    expect("base: generator reports consistent", gen_base["consistent"] is True, str(gen_base))
    expect("base: record verifies (V1-V4)", vb_base["verdict"] == "pass", json.dumps(vb_base))
    expect("base: checker all hard checks pass", rep_base.get("verdict") == "pass",
           json.dumps(b7_base))
    expect("base: B7 passes for all three schemas",
           all(v["B7"] == "pass" for v in b7_base.values()), json.dumps(b7_base))

    # ---- determinism: independent generation of the same record is byte-identical
    gen_base2 = generate(sb_base, "determinism_copy.json")
    expect("determinism: second generation byte-identical", gen_base2["sha256"] == gen_base["sha256"],
           f"{gen_base2['sha256']} vs {gen_base['sha256']}")

    # ---- stale: base record vs moved canonical -> expect FAIL on V1/V3
    sb_repair = fill_sandbox("repair", live["canonical"].read_bytes() + PROBE_COMMENT.encode(),
                             live_old_evidence)
    stale = verify_record(rec_base, sb_repair / CANONICAL_REL, sb_repair / SUPPLEMENT_REL)
    result["scenarios"]["stale_detected"] = stale
    expect("stale: moved canonical revision is detected", stale["verdict"] == "fail"
           and "V1_canonical_input_matches_measured" in stale["hard_failures"]
           and "V3_declared_f0_matches_measured_canonical" in stale["hard_failures"],
           json.dumps(stale["hard_failures"]))

    # ---- repair: rebound schemas + regenerated record -> expect PASS, new record hash
    new_canon_sha = sha256_file(sb_repair / CANONICAL_REL)
    for rel in SCHEMA_RELS:
        p = sb_repair / rel
        text = p.read_text(encoding="utf-8")
        text = text.replace(live_pre["canonical"], new_canon_sha)
        p.write_text(text, encoding="utf-8")
    gen_repair = generate(sb_repair, EVIDENCE_REL)
    rec_repair = sb_repair / EVIDENCE_REL
    rep_repair = checker_report(sb_repair, SANDBOX / "repair_checker_report.json")
    b7_repair = b7_status(rep_repair)
    vb_repair = verify_record(rec_repair, sb_repair / CANONICAL_REL, sb_repair / SUPPLEMENT_REL)
    result["scenarios"]["repair"] = {
        "moved_canonical_sha256": new_canon_sha,
        "generated_sha256": gen_repair["sha256"],
        "checker": b7_repair,
        "exit_code": rep_repair.get("exit_code"),
        "record_verify": vb_repair,
    }
    expect("repair: record bytes move with the revision",
           gen_repair["sha256"] != gen_base["sha256"],
           f"{gen_repair['sha256']} vs {gen_base['sha256']}")
    expect("repair: regenerated record verifies", vb_repair["verdict"] == "pass",
           json.dumps(vb_repair))
    expect("repair: checker all hard checks pass", rep_repair.get("verdict") == "pass",
           json.dumps(b7_repair))

    # ---- drop-in proposal in the worker lane (explicitly NOT the canonical path)
    dropin = VERIFY / "taxonomy_consistency_hashbound.json"
    gen_dropin = generate(ROOT, str(dropin))
    result["dropin_proposal"] = {
        "path": str(dropin.relative_to(ROOT)),
        "sha256": gen_dropin["sha256"],
        "destined_canonical_path": EVIDENCE_REL,
        "note": "proposed successor for the formulation lead to drop in and re-pin; not written canonically by this worker",
    }
    expect("dropin: equals sandbox base record (cross-root determinism)",
           gen_dropin["sha256"] == gen_base["sha256"],
           f"{gen_dropin['sha256']} vs {gen_base['sha256']}")

    # ---- checker selftest (null control + planted defects)
    proc_st = run([sys.executable, str(CHECKER), "--selftest"])
    result["scenarios"]["checker_selftest"] = {"exit_code": proc_st.returncode,
                                               "stdout": proc_st.stdout.strip()}
    expect("checker selftest passes", proc_st.returncode == 0, proc_st.stdout.strip())

    # ---- live byte-stability control (no canonical write)
    live_post = {k: sha256_file(v) for k, v in live.items()}
    result["live_post_sha256"] = live_post
    expect("no canonical write: live hashes unchanged", live_pre == live_post,
           json.dumps({"pre": live_pre, "post": live_post}))

    result["expectations"] = [{"name": n, "ok": ok, "detail": d} for n, ok, d in expectations]
    result["failed_expectations"] = [n for n, ok, _ in expectations if not ok]
    result["verdict"] = "pass" if all(ok for _, ok, _ in expectations) else "fail"
    report_path = Path(args.report)
    report_path.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(report_path),
        "report_sha256": sha256_file(report_path),
        "verdict": result["verdict"],
        "failed_expectations": result["failed_expectations"],
        "base_record_sha256": gen_base["sha256"],
        "dropin_sha256": gen_dropin["sha256"],
    }, indent=1))
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
