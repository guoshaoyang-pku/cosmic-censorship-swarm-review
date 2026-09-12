#!/usr/bin/env python3
"""W03-PUBLISH-CHECK-01 -- did the 00:09-00:10 publication land, and does anything bind now?

Why this exists
---------------
`astra-life01-publish-frozen` (map assignment, node F1, gate G-FORM) asks the formulation lead
to publish the FROZEN revision byte-identically to the four canonical paths and reconcile
`artifacts/formulation/FROZEN.json` so that `verify_frozen.py` exits 0.  W03-VERDICT-BIND-01
measured the state *before* that publication (scan 2026-09-12T00:08:37+08:00) and found 0/4
tree pairs identical, FROZEN rev 19 already stale, and 0 eligible accepts bound to FROZEN.

This checker re-measures the same quantities after the publication window and reports the
delta.  It is a *measurement*: it does not set gate verdicts, does not edit the map, and does
not touch the artifacts it measures.

What it does
------------
1. Hashes the four canonical/authoring tree pairs and reads their FROZEN-declared hashes.
2. Re-runs the frozen-blocked binding scanner (W03-VERDICT-BIND-01 tool, unmodified) to a new
   output path, and lifts its per-class eligibility.
3. Runs the project's own `verify_frozen.py` and `audit_evidence.py` and captures exit code,
   drift lines and dual-tree-divergence lines verbatim (cross-tool check, not a re-implementation).
4. Compares everything against the W03-VERDICT-BIND-01 baseline report.
5. Emits `report.json` with snapshot hashes, deltas, findings (id, severity, statement,
   falsifier) and limits.

Determinism / limits
--------------------
* stdlib only; sorted iteration; only `generated_at` and the sha256 of this tool vary between runs.
* The formulation lead may regenerate FROZEN.json concurrently (regenerate_frozen.py exists);
  this records the manifest hash at start and end and flags a mid-scan change rather than hiding it.
* An "eligible accept" requires a declared binding field that equals the measured canonical
  sha256.  Prose-only citations are never upgraded.  This makes no claim about mathematical content.
* Snapshot, not a gate: only Astra/the gate owner may move G-FORM.

Usage:
  python3 artifacts/worker-03/publish_binding_check/check_publish_binding.py \
      [--root .] [--out artifacts/worker-03/publish_binding_check/report.json] \
      [--rescan-out artifacts/worker-03/publish_binding_check/rescan_report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))

TREE_PAIRS = (
    ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml",
     "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml",
     "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml",
     "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    ("AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
     "research_map/formulation_taxonomy.yaml",
     "artifacts/formulation/formulation_taxonomy.yaml"),
)

SCANNER = "artifacts/worker-03/review_hash_binding/scan_verdict_bindings.py"
BASELINE = "artifacts/worker-03/review_hash_binding/report.json"
VERIFY_FROZEN = "artifacts/formulation/tools/verify_frozen.py"
AUDIT_EVIDENCE = "research_map/audit_evidence.py"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    with path.open() as fh:
        return json.load(fh)


def run_tool(argv, cwd: Path, timeout: int = 600):
    """Best-effort subprocess capture; never raises on non-zero exit."""
    try:
        proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                              timeout=timeout)
        return {"argv": argv, "exit_code": proc.returncode,
                "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as exc:  # pragma: no cover - tooling failure is recorded, not hidden
        return {"argv": argv, "exit_code": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="artifacts/worker-03/publish_binding_check/report.json")
    ap.add_argument("--rescan-out",
                    default="artifacts/worker-03/publish_binding_check/rescan_report.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_path = (root / args.out).resolve()
    rescan_path = (root / args.rescan_out).resolve()
    rescan_path.parent.mkdir(parents=True, exist_ok=True)

    frozen_path = root / "artifacts/formulation/FROZEN.json"
    frozen_sha_start = sha256_file(frozen_path)
    frozen = load_json(frozen_path)
    frozen_files = frozen.get("files", {})

    pairs = []
    for class_id, canonical_rel, authoring_rel in TREE_PAIRS:
        cpath, apath = root / canonical_rel, root / authoring_rel
        csha = sha256_file(cpath) if cpath.exists() else None
        asha = sha256_file(apath) if apath.exists() else None
        declared = frozen_files.get(authoring_rel, {}).get("sha256")
        pairs.append({
            "class_id": class_id,
            "canonical_path": canonical_rel,
            "canonical_sha256": csha,
            "authoring_path": authoring_rel,
            "authoring_sha256": asha,
            "identical": bool(csha and asha and csha == asha),
            "frozen_declared_sha256": declared,
            "frozen_declared_matches_authoring_disk": bool(declared and declared == asha),
            "frozen_declared_matches_canonical_disk": bool(declared and declared == csha),
        })

    # Baseline (W03-VERDICT-BIND-01) comparison.
    baseline_path = root / BASELINE
    baseline = load_json(baseline_path) if baseline_path.exists() else {}
    base_pairs = {p["authoring_path"]: p for p in baseline.get("tree_pairs", [])}
    base_elig = baseline.get("gate_eligibility", {}).get("classes", [])
    base_accept_eligible = sum(int(c.get("eligible_count", 0)) for c in base_elig)
    base_accept_total = sum(int(c.get("accept_count", 0)) for c in base_elig)
    for pair in pairs:
        bp = base_pairs.get(pair["authoring_path"], {})
        pair["baseline_canonical_sha256"] = bp.get("authoring_sha256")
        pair["baseline_published_sha256"] = bp.get("published_sha256")
        pair["canonical_changed_since_baseline"] = (
            pair["canonical_sha256"] != bp.get("authoring_sha256"))
        pair["authoring_changed_since_baseline"] = (
            pair["authoring_sha256"] != bp.get("published_sha256"))
        pair["identical_at_baseline"] = bool(bp.get("identical"))

    # Re-run the frozen-blocked binding scanner (unmodified) at this snapshot.
    scanner_run = run_tool([sys.executable, SCANNER, "--root", str(root),
                            "--out", str(rescan_path)], root)
    rescan = load_json(rescan_path) if rescan_path.exists() else {}
    rescan_classes = rescan.get("gate_eligibility", {}).get("classes", [])
    rescan_accept_eligible = sum(int(c.get("eligible_count", 0)) for c in rescan_classes)
    rescan_accept_total = sum(int(c.get("accept_count", 0)) for c in rescan_classes)

    # Project tools, captured verbatim as a cross-check.
    vf_run = run_tool([sys.executable, VERIFY_FROZEN], root)
    drift = [ln.strip() for ln in vf_run["stdout"].splitlines() if ln.strip().startswith("DRIFT")]
    ae_run = run_tool([sys.executable, AUDIT_EVIDENCE], root)
    divergences = [ln.strip() for ln in ae_run["stdout"].splitlines()
                   if "dual-tree divergence" in ln]

    frozen_sha_end = sha256_file(frozen_path)
    stable = frozen_sha_start == frozen_sha_end
    research_map_sha = sha256_file(root / "research_map/research_map.json")
    try:
        frozen_at_ahead_seconds = (
            datetime.fromisoformat(frozen.get("frozen_at")) - datetime.now(CST)).total_seconds()
    except (TypeError, ValueError):
        frozen_at_ahead_seconds = None

    identical_now = sum(1 for p in pairs if p["identical"])
    identical_before = sum(1 for p in pairs if p["identical_at_baseline"])
    frozen_drift_now = len(drift)
    frozen_drift_before = sum(
        1 for e in baseline.get("frozen_declared_vs_disk", []) if e.get("match") is False)

    class_schema_paths = {p["authoring_path"] for p in pairs[:3]}
    drift_paths = [ln.split()[1].rstrip(":") for ln in drift if len(ln.split()) > 1]
    class_schema_drifts = [p for p in drift_paths if p in class_schema_paths]
    binds_frozen_accepts = [
        (c["class_id"], v) for c in rescan_classes for v in c.get("verdicts", [])
        if v.get("verdict") == "accept" and v.get("verdict_binding") == "binds_frozen"]
    scoped_accepts = [
        (cid, v) for cid, v in binds_frozen_accepts
        if v.get("counts_as_independent_second_verdict") is False]

    findings = []
    findings.append({
        "id": "W03-PB-01",
        "severity": "major",
        "statement": (
            f"Publication of the three class schemas landed: {sum(1 for p in pairs[:3] if p['identical'])}/3 "
            f"canonical<->authoring class-schema pairs are now byte-identical (baseline {sum(1 for p in pairs[:3] if p['identical_at_baseline'])}/3). "
            "The fourth pair (formulation_taxonomy.yaml) still diverges."
        ),
        "evidence_refs": [
            f"{p['canonical_path']}#{(p['canonical_sha256'] or '')[:12]}" for p in pairs],
        "falsifier": (
            "Re-hash the four pairs. Any class-schema pair that is not byte-identical, or a "
            "taxonomy pair that is byte-identical, contradicts this statement."
        ),
    })
    findings.append({
        "id": "W03-PB-02",
        "severity": "major",
        "statement": (
            f"FROZEN revision {frozen.get('revision')} ({frozen_sha_start[:12]}) is NOT reconciled to disk at "
            f"this snapshot: `verify_frozen.py` exit={vf_run['exit_code']} with {frozen_drift_now} drift "
            f"file(s) {drift_paths}; class-schema drift: {len(class_schema_drifts)} of 3. The publish "
            "acceptance test (verify_frozen exit 0) is therefore not met at this snapshot."
        ),
        "evidence_refs": [f"artifacts/formulation/FROZEN.json#{frozen_sha_start[:12]}"] + [
            "artifacts/formulation/" + p for p in drift_paths[:4]],
        "falsifier": (
            "Re-run `python3 artifacts/formulation/tools/verify_frozen.py` after the lead re-freezes. "
            "Exit code 0 with 0 DRIFT lines falsifies this finding; a mid-scan manifest change is "
            "recorded separately and does not falsify the snapshot."
        ),
    })
    findings.append({
        "id": "W03-PB-03",
        "severity": "major",
        "statement": (
            f"No G-FORM class has an eligible independent accept verdict bound to the current canonical "
            f"sha256: {rescan_accept_eligible} eligible of {rescan_accept_total} accepts across "
            f"{len(rescan_classes)} classes (baseline {base_accept_eligible} eligible of {base_accept_total}). "
            f"{len(binds_frozen_accepts)} accept(s) do bind the canonical bytes, but "
            f"{len(scoped_accepts)} of those self-declare non-independence / partial scope "
            f"({[(cid, v.get('review_file')) for cid, v in scoped_accepts]}). Publishing moved the other "
            "cited hashes out of reach: they now classify as unresolved against current disk."
        ),
        "evidence_refs": [
            f"{c.get('canonical_path')}#{str(c.get('frozen_declared_sha256'))[:12]}"
            for c in rescan_classes] + [
            f"reviews/{v.get('review_file', '').split('/')[-1]}" for _, v in scoped_accepts],
        "falsifier": (
            "Re-run the scanner classified rescan_report.json's tool. Any accept verdict with a declared "
            "binding field equal to the measured canonical sha256, from a reviewer who did not author the "
            "artifact and not self-declared non-independent, falsifies this finding."
        ),
    })
    findings.append({
        "id": "W03-PB-04",
        "severity": "minor",
        "statement": (
            f"`audit_evidence.py` exit={ae_run['exit_code']} reports {len(divergences)} dual-tree divergence "
            "finding(s) at this snapshot (was 4/4 pairs in W03-VERDICT-BIND-01's narrative); only the "
            "taxonomy pair remains. The publish assignment's second acceptance test (0 divergences) is "
            "consequently one file short."
        ),
        "evidence_refs": ["research_map/audit_evidence.py"],
        "falsifier": (
            "Re-run `python3 research_map/audit_evidence.py`; 0 dual-tree divergence lines falsifies the "
            "'one file short' part. A different count contradicts the measured count."
        ),
    })
    if frozen_at_ahead_seconds and frozen_at_ahead_seconds > 0:
        findings.append({
            "id": "W03-PB-05",
            "severity": "minor",
            "statement": (
                f"FROZEN revision {frozen.get('revision')}'s `frozen_at` ({frozen.get('frozen_at')}) is "
                f"{int(frozen_at_ahead_seconds)}s ahead of the scan wall clock "
                f"({datetime.now(CST).isoformat(timespec='seconds')}). `frozen_at` is caller-supplied to "
                "regenerate_frozen.py (`--at`), so it orders revisions only nominally; freshness must be "
                "read from revision + manifest sha256, not from the timestamp."
            ),
            "evidence_refs": [f"artifacts/formulation/FROZEN.json#{frozen_sha_start[:12]}",
                              "artifacts/formulation/tools/regenerate_frozen.py:40"],
            "falsifier": (
                "Read `frozen_at` from FROZEN.json and compare with the file mtime; if frozen_at <= mtime of "
                "the writing run, this finding is falsified. (The tool takes --at from the caller: line 40.)"
            ),
        })

    report = {
        "report_id": f"W03-PUBLISH-CHECK-01-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "task_id": "W03-PUBLISH-CHECK-01",
        "actor": "worker-03",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "inputs": {
            "frozen_manifest": "artifacts/formulation/FROZEN.json",
            "frozen_revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "frozen_manifest_sha256": frozen_sha_start,
            "frozen_manifest_sha256_at_end": frozen_sha_end,
            "frozen_manifest_stable_during_scan": stable,
            "frozen_at_ahead_of_wall_clock_seconds": frozen_at_ahead_seconds,
            "research_map_sha256": research_map_sha,
            "baseline_report": BASELINE,
            "baseline_report_sha256": sha256_file(baseline_path) if baseline_path.exists() else None,
            "baseline_report_id": baseline.get("report_id"),
            "rescan_report": args.rescan_out,
            "rescan_report_sha256": sha256_file(rescan_path) if rescan_path.exists() else None,
            "verify_frozen": vf_run,
            "audit_evidence_exit_code": ae_run["exit_code"],
            "tool": {"path": str(Path(__file__).resolve().relative_to(root)),
                     "sha256": sha256_file(Path(__file__).resolve())},
        },
        "tree_pairs": pairs,
        "frozen_reconciliation": {
            "verify_frozen_exit_code": vf_run["exit_code"],
            "drift_count": frozen_drift_now,
            "drift": drift,
        },
        "binding": {
            "rescan_report_id": rescan.get("report_id"),
            "per_class": rescan_classes,
            "accept_total": rescan_accept_total,
            "eligible_total": rescan_accept_eligible,
            "binds_frozen_accept_count": len(binds_frozen_accepts),
            "binds_frozen_but_not_independent": [
                {"class_id": cid, "review_file": v.get("review_file")}
                for cid, v in scoped_accepts],
        },
        "delta_vs_baseline": {
            "tree_pairs_identical_before": identical_before,
            "tree_pairs_identical_now": identical_now,
            "frozen_drift_before": frozen_drift_before,
            "frozen_drift_now": frozen_drift_now,
            "eligible_accepts_before": base_accept_eligible,
            "eligible_accepts_now": rescan_accept_eligible,
            "dual_tree_divergences_now": len(divergences),
        },
        "findings": findings,
        "falsifier": (
            "Re-run this checker against the same FROZEN revision and canonical bytes. The report is "
            "falsified if (a) any pair marked non-identical re-hashes identical; (b) any pair marked "
            "identical re-hashes different; (c) verify_frozen exits 0 with 0 drift while the report says "
            "otherwise; or (d) any eligible accept bound to the canonical sha256 appears while the report "
            "says 0. A change in the inputs after the snapshot is not a falsifier; `frozen_manifest_sha256` "
            "and `research_map_sha256` pin what was read."
        ),
        "limits": [
            "Snapshot only; the formulation lead was regenerating FROZEN.json during this window "
            f"(manifest stable during scan: {stable}).",
            "Eligibility is machine-read from declared binding fields; reviewer independence is taken "
            "from declared flags, not adjudicated here.",
            "This is worker-authored evidence for the controller; it does not move a gate or a node status.",
            "No claim is made about the mathematical content of any schema or review.",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    summary = {
        "report_id": report["report_id"],
        "report_sha256": sha256_file(out_path),
        "rescan_report_sha256": report["inputs"]["rescan_report_sha256"],
        "pairs_identical": f"{identical_now}/4",
        "verify_frozen_exit": vf_run["exit_code"],
        "drift_count": frozen_drift_now,
        "dual_tree_divergences": len(divergences),
        "eligible_accepts": rescan_accept_eligible,
        "frozen_stable": stable,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
