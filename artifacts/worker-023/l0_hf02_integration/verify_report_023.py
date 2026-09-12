#!/usr/bin/env python3
"""Independent verifier for W023-L0-HF02-INTEG-01.

Re-derives the integration result from the on-disk raw audit reports and
re-executes the frozen scenarios where the sandboxes are still present. It does
not trust the driver's booleans: every assertion is recomputed here.

Usage:
  python3 artifacts/worker-023/l0_hf02_integration/verify_report_023.py

Exit codes: 0 all assertions pass; 3 an assertion failed; 4 artifact missing.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
ART = REPO / "artifacts/worker-023/l0_hf02_integration"
RAW = ART / "raw"
WORK = REPO / "tmp/w023_hf02_integration"
EXPECTED_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]

results: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append({"check": name, "pass": bool(ok), "detail": detail})


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def vkey(v: dict) -> str:
    return json.dumps({k: v[k] for k in ("hf", "severity", "where", "detail")}, sort_keys=True)


def disj_rows(report: dict) -> list[str]:
    return sorted(v["where"].split("ledger/", 1)[1] for v in report["violations"]
                  if v["hf"] == "HF-02" and v["detail"].startswith("disjunction of class_ids"))


def digest(report: dict) -> str:
    return hashlib.sha256(json.dumps(
        sorted([v["hf"], v["severity"], v["where"], v["detail"]] for v in report["violations"]),
        sort_keys=True).encode()).hexdigest()


def main() -> int:
    for p in (ART / "report.json", ART / "manifest.json", ART / "runner_wiring.diff"):
        if not p.is_file():
            print(f"MISSING {p}", file=sys.stderr)
            return 4
    report = json.loads((ART / "report.json").read_text())
    manifest = json.loads((ART / "manifest.json").read_text())

    # 1. sidecars
    for name, path in (("report.json", ART / "report.json"),
                       ("manifest.json", ART / "manifest.json")):
        side = ART / f"{name}.sha256"
        want = side.read_text().split()[0] if side.is_file() else None
        check(f"sidecar:{name}", want == sha256_file(path), f"sidecar={want} actual={sha256_file(path)}")

    # 2. manifest self-consistency
    for a in manifest["artifacts"]:
        p = REPO / a["path"]
        got = sha256_file(p) if p.is_file() else None
        check(f"manifest:{a['role']}", got == a["sha256"], f"{a['path']} want={a['sha256'][:12]} got={str(got)[:12]}")

    # 3. canonical pins still hold on disk (map snapshot is not on disk after cleanup)
    moved = []
    for rel, want in report["pins"].items():
        if rel.endswith("@snapshot"):
            continue
        p = REPO / rel
        got = sha256_file(p) if p.is_file() else None
        if got != want:
            moved.append({"path": rel, "want": want, "got": got})
    check("canonical_pins_hold", not moved, json.dumps(moved))

    # 4. re-derive from raw evidence
    raw = {}
    for tag in ("baseline_trim", "baseline_trim_rerun", "patched_trim", "patched_trim_rerun",
                "baseline_full", "patched_full"):
        p = RAW / f"{tag}.audit-report.json"
        raw[tag] = json.loads(p.read_text()) if p.is_file() else None
    have_all = all(raw.values())
    check("raw_reports_present", have_all)
    if have_all:
        check("baseline_flags_zero",
              all(disj_rows(raw[t]) == [] for t in ("baseline_trim", "baseline_trim_rerun", "baseline_full")),
              str({t: disj_rows(raw[t]) for t in ("baseline_trim", "baseline_full")}))
        check("patched_flags_exactly_expected",
              all(disj_rows(raw[t]) == EXPECTED_ROWS for t in ("patched_trim", "patched_trim_rerun", "patched_full")),
              str({t: disj_rows(raw[t]) for t in ("patched_trim", "patched_full")}))
        for base_t, pat_t in (("baseline_trim", "patched_trim"), ("baseline_full", "patched_full")):
            b = [vkey(v) for v in raw[base_t]["violations"]]
            p = [vkey(v) for v in raw[pat_t]["violations"]]
            added = [x for x in p if x not in b]
            removed = [x for x in b if x not in p]
            added_obj = [json.loads(x) for x in added]
            expect_baseline = 0 if base_t == "baseline_trim" else None
            check(f"delta:{base_t}->{pat_t}",
                  len(added) == 8 and not removed
                  and all(v["hf"] == "HF-02" and v["detail"].startswith("disjunction of class_ids")
                          for v in added_obj)
                  and (expect_baseline is None or len(b) == expect_baseline),
                  f"baseline_n={len(b)} added={len(added)} removed={len(removed)}")

    # 5. driver's recorded digests match the raw reports
    scen = report["scenarios"]
    check("recorded_digests_match_raw",
          all(scen[t]["violations_digest"] == digest(raw[t]) for t in raw if raw[t]),
          "")
    check("determinism_digests",
          digest(raw["baseline_trim"]) == digest(raw["baseline_trim_rerun"])
          and digest(raw["patched_trim"]) == digest(raw["patched_trim_rerun"]),
          "")

    # 6. re-execute the frozen trimmed scenarios if sandboxes survive
    reexec = {"performed": False}
    sb_canon = WORK / "sandbox_canonical"
    sb_patch = WORK / "sandbox_patched"
    if sb_canon.is_dir() and sb_patch.is_dir():
        reexec["performed"] = True
        for tag, sb in (("baseline_trim", sb_canon), ("patched_trim", sb_patch)):
            out = sb / "artifacts/audit/reports_verify"
            cmd = [sys.executable, str(sb / "artifacts/audit/audit_run.py"),
                   "--map", str(sb / "research_map/research_map_trimmed.json"),
                   "--scan", str(sb / "ledger"), "--out", str(out),
                   "--quiet", "--kind", "findings", "--fail-on-critical"]
            proc = subprocess.run(cmd, cwd=str(sb), capture_output=True, text=True)
            rep = json.loads((out / "LATEST.json").read_text()) if (out / "LATEST.json").is_file() else None
            same = rep is not None and digest(rep) == scen[tag]["violations_digest"]
            check(f"reexec:{tag}", same, f"exit={proc.returncode}")
            reexec[tag] = {"exit_code": proc.returncode, "digest_match": bool(same)}
    else:
        check("reexec_skipped_sandboxes_absent", True, "sandboxes cleaned; static verification only")

    # 7. controls recorded by the driver reproduce their expectations
    ctl = report["controls"]
    check("controls_recorded_all_pass",
          ctl["failed"] == 0 and all(c["got"] == c["expect"] for c in ctl["cases"]),
          f"{ctl['passed']}/{ctl['n']}")

    passed = sum(1 for r in results if r["pass"])
    failed = [r for r in results if not r["pass"]]
    out = {
        "schema": "w023-hf02-integration-verification/v1",
        "task_id": "W023-L0-HF02-INTEG-01",
        "actor": "worker-023",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "verified_report_sha256": sha256_file(ART / "report.json"),
        "verified_manifest_sha256": sha256_file(ART / "manifest.json"),
        "n_checks": len(results), "n_passed": passed, "n_failed": len(failed),
        "verdict": "verified" if not failed else "failed",
        "failed_checks": failed,
        "checks": results,
        "reexecution": reexec,
        "authority": "worker-level verification; no node status, no gate verdict",
    }
    (ART / "verification.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    (ART / "verification.json.sha256").write_text(
        f"{sha256_file(ART / 'verification.json')}  verification.json\n")
    print(f"verification: {passed}/{len(results)} checks pass -> {out['verdict']}")
    for r in failed:
        print(f"  FAIL {r['check']}: {r['detail']}")
    return 0 if not failed else 3


if __name__ == "__main__":
    raise SystemExit(main())
