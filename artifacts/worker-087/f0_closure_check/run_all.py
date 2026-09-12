#!/usr/bin/env python3
"""run_all.py -- closure-verification bundle for W087-F0-CLOSURE-CHECK-02.

Reproducible, pin-bound acceptance bundle for the three blocking F0 findings
(B-16F0-1 / W082-F-01, B-16F0-2, B-16F0-3).  Everything runs as subprocesses with
exit-code checks:

  1. measure the canonical F0 taxonomy hash H; optional --expect-pin exits 2 on mismatch;
  2. accept_f0_closure.py at H -> results_canonical.json; record every CL/INV check;
  3. make_regression.py -> regression_check.yaml (the historical pre-rev5 defect restored);
     accept_f0_closure.py on it must exit 3 with CL1..CL3 OPEN (sensitivity control);
  4. drift control: wrong --pin must exit 2 and write no JSON;
  5. aggregate results.json: verdict, per-finding disposition, freeze/publication state,
     lead-side remainder, falsifier.

Exit codes
  0  bundle valid and canonical F0 class-content checks CLOSED at H
  3  bundle valid and canonical F0 class-content checks OPEN at H (detail in results.json)
  1  bundle invalid (an expectation or control failed)
  2  canonical drift from --expect-pin / fail-closed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import make_candidate as MC

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VERIFIER = HERE / "accept_f0_closure.py"
CANONICAL = ROOT / "research_map" / "formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
MAP = ROOT / "research_map" / "research_map.json"
RESULTS = HERE / "results.json"


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable] + args, cwd=str(ROOT), capture_output=True, text=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expect-pin", default=None, help="required canonical sha256; mismatch exits 2")
    args = ap.parse_args(argv)

    canon_sha = MC.sha256_bytes(CANONICAL.read_bytes())
    if args.expect_pin and canon_sha != args.expect_pin:
        print(f"FAIL-CLOSED: canonical drifted: {canon_sha} != {args.expect_pin}", file=sys.stderr)
        return 2

    expectations: list[tuple[str, bool, str]] = []

    # 1. canonical verification
    canon_json = HERE / "results_canonical.json"
    r = run([str(VERIFIER), "--target", str(CANONICAL), "--pin", canon_sha, "--label", "canonical",
             "--json-out", str(canon_json)])
    canon = read_json(canon_json)
    canon_closed = canon.get("closure", {}).get("class_content") == "CLOSED"
    ok = r.returncode == (0 if canon_closed else 3) and canon.get("pin_match") and not canon.get("closure", {}).get("invariant_regressions")
    expectations.append(("canonical_verification_valid", ok,
                         f"exit={r.returncode} class_content={canon.get('closure', {}).get('class_content')} "
                         f"open={canon.get('closure', {}).get('open_checks')} "
                         f"regressions={canon.get('closure', {}).get('invariant_regressions')}"))

    # 2. regression control
    rc = run([str(HERE / "make_regression.py"), "--pin", canon_sha])
    reg_fixture = HERE / "regression_check.yaml"
    reg_ok = rc.returncode == 0 and reg_fixture.exists()
    reg_detail = f"make_regression exit={rc.returncode}"
    if reg_ok:
        reg_json = HERE / "results_regression.json"
        r2 = run([str(VERIFIER), "--target", str(reg_fixture),
                  "--pin", MC.sha256_bytes(reg_fixture.read_bytes()), "--label", "regression-control",
                  "--json-out", str(reg_json)])
        reg = read_json(reg_json)
        reg_open = set(reg.get("closure", {}).get("open_checks", []))
        reg_ok = r2.returncode == 3 and {"CL1", "CL2", "CL3"}.issubset(reg_open)
        reg_detail = f"exit={r2.returncode} open={sorted(reg_open)}"
    expectations.append(("regression_control_detects_reintroduced_defect", reg_ok, reg_detail))

    # 3. drift control
    drift_json = HERE / "results_drift_should_not_exist.json"
    if drift_json.exists():
        drift_json.unlink()
    r3 = run([str(VERIFIER), "--target", str(CANONICAL), "--pin", "0" * 64, "--label", "drift-control",
              "--json-out", str(drift_json)])
    drift_ok = r3.returncode == 2 and not drift_json.exists()
    expectations.append(("drift_control_fail_closed", drift_ok,
                         f"exit={r3.returncode} json_written={drift_json.exists()}"))

    # 4. freeze / publication context (report only)
    fz = read_json(FROZEN)
    frozen_pin = ((fz.get("files") or {}).get("research_map/formulation_taxonomy.yaml") or {}).get("sha256")
    fz_rev = fz.get("revision")
    mapd = read_json(MAP)
    pub = next((p for p in (mapd.get("publication_status", {}) or {}).get("pairs", [])
                if p.get("canonical") == "research_map/formulation_taxonomy.yaml"), {})
    authoring_sha = None
    authoring = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
    if authoring.exists():
        authoring_sha = MC.sha256_bytes(authoring.read_bytes())

    def status_of(check_id: str) -> str:
        return next((c["status"] for c in canon.get("checks", []) if c["id"] == check_id), "MISSING")

    finding_disposition = {
        "B-16F0-1 / W082-F-01": {"decided_by": ["CL1", "CL2", "CL3"],
                                 "status": "CLOSED" if all(status_of(c) == "PASS" for c in ("CL1", "CL2", "CL3")) else "OPEN"},
        "B-16F0-2": {"decided_by": ["CL4"], "status": "CLOSED" if status_of("CL4") == "PASS" else "OPEN"},
        "B-16F0-3": {"decided_by": ["CL5"], "status": "CLOSED" if status_of("CL5") == "PASS" else "OPEN"},
    }
    all_closed = canon_closed and all(v["status"] == "CLOSED" for v in finding_disposition.values())
    all_ok = all(ok for _, ok, _ in expectations)
    verdict = (f"BLOCKING_FINDINGS_CLOSED_AT_{canon_sha[:12]}" if all_closed
               else f"BLOCKING_FINDINGS_OPEN_AT_{canon_sha[:12]}")

    results = {
        "task_id": "W087-F0-CLOSURE-CHECK-02",
        "worker": "worker-087",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "generated_at": now(),
        "verdict": verdict,
        "scope": ("independent closure verification of three specific blocking findings plus regression "
                  "invariants; NOT a full-schema review and NOT a gate verdict. Worker authority only."),
        "pins": {
            "canonical": "research_map/formulation_taxonomy.yaml",
            "canonical_sha256": canon_sha,
            "frozen_pin_sha256": frozen_pin,
            "frozen_revision": fz_rev,
            "canonical_matches_frozen_pin": frozen_pin == canon_sha,
            "authoring_sha256": authoring_sha,
            "map_publication_pair": pub,
        },
        "expectations": [{"name": n, "status": "PASS" if ok else "FAIL", "detail": d} for n, ok, d in expectations],
        "finding_disposition": finding_disposition,
        "checks_at_canonical": {c["id"]: {"status": c["status"], "scope": c["scope"], "title": c["title"],
                                          "detail": c["detail"]} for c in canon.get("checks", [])},
        "lead_side": canon.get("lead_side", []),
        "controls": canon.get("controls", []),
        "history": {
            "rev4_276009f4": "CL1-CL5 all OPEN (worker-16 B-16F0-1/2/3, worker-082 W082-F-01/02, astra-lead-audit blocking list).",
            "worker_candidate_6207dfc0": "repair candidate built from rev4 by artifacts/worker-087/f0_closure_check/"
                                         "make_candidate.py; independently verified to close CL1-CL5 with all invariants "
                                         "and controls passing. Superseded by the lead's rev5 wording; retained as "
                                         "provenance of the intended minimal repair, not as a competing proposal.",
            "rev5_on_disk": "the formulation lead rewrote AF-WCC-SCALAR-SPH (single-q tail predicate + explicit "
                            "comeager binder + superseded-wording note), fixed D3's resolution text and both SCC "
                            "schema_owner pointers; this bundle verifies the result at the measured hash.",
        },
        "lead_side_remaining": [
            "Re-freeze: FROZEN.json still pins rev4 276009f4 (measured at bundle time); canonical rev5 "
            f"{canon_sha[:12]} must be re-frozen with a single sha256 per logical artifact before review verdicts bind.",
            "CL6 publication/mirror: controller adjudication of logical_artifacts / f0_mirror_adjudication_request "
            "(REC-1 pairs-check exception or REC-2 bounded re-freeze) is still open.",
            "CL7 downstream re-pin: schemas/taxonomy_cases.jsonl meta pin and per-case binding_status still name "
            "superseded F0 hashes; owner astra-life03-repin-claims.",
            "Two independent full-schema accepts at the frozen hash are still required for G-F0; this bundle is "
            "targeted closure evidence, not a review verdict.",
        ],
        "acceptance_command": (
            f"python3 artifacts/worker-087/f0_closure_check/run_all.py --expect-pin {canon_sha}"
        ),
        "falsifier": (
            "Re-run this bundle at the same --expect-pin: any expectation not PASS, any control failure, or "
            "canonical drift voids the verdict. Independently, a reviewer showing that the rev5 "
            "AF-WCC-SCALAR-SPH conclusion asserts a visibility predicate not fixed by its hypotheses, or that "
            "the comeager binder is not bound before the data, falsifies the B-16F0-1/B-16F0-2 closure even "
            "though the mechanical checks pass."
        ),
    }
    RESULTS.write_text(json.dumps(results, indent=2) + "\n")

    print(f"verdict: {verdict}")
    for n, ok, d in expectations:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}: {d}")
    print(f"  canonical={canon_sha[:12]} frozen_pin={str(frozen_pin)[:12]} authoring={str(authoring_sha)[:12]}")
    print(f"  results: {RESULTS.relative_to(ROOT)}")
    if not all_ok:
        return 1
    return 0 if all_closed else 3


if __name__ == "__main__":
    sys.exit(main())
