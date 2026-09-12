#!/usr/bin/env python3
"""W004 SEMCT rebase, part 2: self-contained end-to-end proof in shadow repos.

Builds artifact-local shadow copies of the binding gate toolchain so the measurement
cannot race the live tree:

  shadow_repo/       stage tools + KEY_MANIFEST rev27 (fce91948ba3a, pre-regeneration)
  shadow_repo_rev28/ same stage tools + KEY_MANIFEST rev28 (014e2d301978, live since 00:34)

and runs the suite twice per shadow repo:

  suite_patched/  rebased controls              -> rev27: exit 0, valid=true
  suite_stale/    original frozen controls      -> rev27: exit 3, valid=false
  suite_patched/  rebased controls              -> rev28: exit 3 (R22 on revised_at_unused)

The rev27/rev28 manifest pair isolates the second blocker: the key allowlist was
regenerated from the new canonical revision at 00:34 and no longer contains
`revised_at_unused`, so R22 now rejects not only the controls but also the pinned
canonical revision that was gate-accepted minutes earlier.  Only the rev27 run can
demonstrate the control rebase; the rev28 run demonstrates the regression.

Stage tools are byte copies (hashes pinned); the only runner patch is one line:
`REPO = HERE.parent.parent` -> `REPO = HERE.parents[2]` for shadow path resolution.
Canonical schemas are byte snapshots of the last revision measured accepted by all
three stages.  All provenance is recorded in suite_run_report.json.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CST = timezone(timedelta(hours=8))

SUITE = REPO / "schemas" / "semantic_contract_tests"
RUNNER = SUITE / "run_contract_tests.py"
MANIFEST = SUITE / "manifest.json"
REBASED = HERE / "rebased_controls"

STAGE_PINS = {
    "structural": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "semantic": "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
}
STAGE_TOOL = {
    "structural": REPO / "artifacts" / "formulation" / "tools" / "check_class_schema.py",
    "semantic": REPO / "artifacts" / "worker-06" / "spec_conformance_audit.py",
}
RULE_SPEC = REPO / "artifacts" / "formulation" / "rule_spec.json"
KM_SNAP = {
    "rev27": {"sha256": "fce91948ba3a59a5bd34c8bcb03202ee479a95dbc3e4d6c327a0c4d1a9170d33",
              "path": "artifacts/worker-061/f1_rev12_gate/pinned/hist/KEY_MANIFEST.rev27.json"},
    "rev28": {"sha256": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
              "path": "artifacts/formulation/KEY_MANIFEST.json"},
}

STALE_SHA = {
    "SCT-C01": "a6ad2638dc993c32f7cc46a1a84441581ab785ba02c84a5197663e6284c86f2a",
    "SCT-C02": "7b910cf34e64baa7d2d02e229f7bfb5224ffb3fa70d264e1cc1f5ec3173e41eb",
    "SCT-C03": "687fd697130497633e63b696ac90d0939c2699fd6d5f3b1bca06b55f5948dee6",
}
PINNED_CANON_SHA = {
    "SCT-K01": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    "SCT-K02": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "SCT-K03": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
}
PINNED_CANON_SNAP = {
    "SCT-K01": "artifacts/worker-061/f1_independent_verdict/pinned/af_scc_c0_vacuum.yaml",
    "SCT-K02": "artifacts/worker-061/f1_independent_verdict/pinned/af_scc_c2_vacuum.yaml",
    "SCT-K03": "artifacts/worker-061/f1_independent_verdict/pinned/af_wcc_vacuum.yaml",
}
CONTROL_FILE = {
    "SCT-C01": "control_comment_only_composite.yaml",
    "SCT-C02": "control_conforming_base.yaml",
    "SCT-C03": "control_quoted_forbidden_phrase.yaml",
}
CANON_FILE = {
    "SCT-K01": "schemas/af_scc_c0_vacuum.yaml",
    "SCT-K02": "schemas/af_scc_c2_vacuum.yaml",
    "SCT-K03": "schemas/af_wcc_vacuum.yaml",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_shadow(root: Path, manifest_src: Path, rebased: bool, suite_name: str) -> dict:
    """One shadow repo + one suite copy; returns provenance."""
    if root.exists():
        shutil.rmtree(root)
    suite = root / "artifacts" / "worker-004" / suite_name
    tools = root / "artifacts" / "formulation" / "tools"
    semdir = root / "artifacts" / "worker-06"
    for d in (tools, semdir, suite):
        d.mkdir(parents=True)
    shutil.copy2(STAGE_TOOL["structural"], tools / "check_class_schema.py")
    shutil.copy2(STAGE_TOOL["semantic"], semdir / "spec_conformance_audit.py")
    shutil.copy2(manifest_src, root / "artifacts" / "formulation" / "KEY_MANIFEST.json")
    shutil.copy2(RULE_SPEC, root / "artifacts" / "formulation" / "rule_spec.json")
    shutil.copytree(SUITE / "fixtures", suite / "fixtures")
    for name in CONTROL_FILE.values():
        if rebased:
            shutil.copy2(REBASED / name, suite / "fixtures" / "controls" / name)

    src_text = RUNNER.read_text()
    old_line = "REPO = HERE.parent.parent\n"
    new_line = "REPO = HERE.parents[2]  # patched by worker-004 shadow copy\n"
    if src_text.count(old_line) != 1:
        raise SystemExit("runner REPO line not found exactly once (fails closed)")
    (suite / "run_contract_tests.py").write_text(src_text.replace(old_line, new_line, 1))

    man = json.loads(MANIFEST.read_text())
    patch_ops = []
    for e in man["controls"]:
        tid = e["test_id"]
        new = sha(suite / "fixtures" / "controls" / CONTROL_FILE[tid])
        patch_ops.append({"test_id": tid, "field": "sha256", "old": e["sha256"], "new": new})
        if rebased:
            e["rebased_from_sha256"] = e["sha256"]
            e["sha256"] = new
            e["note"] = e["note"] + " [rebased 2026-09-12 by worker-004: R28-violating duplicate row deleted]"
        elif new != STALE_SHA[tid]:
            raise SystemExit(f"stale copy hash mismatch {tid}")

    snap_dir = suite / "fixtures" / "canonical_snapshot"
    snap_dir.mkdir(parents=True, exist_ok=True)
    for e in man["conforming_canonical_controls"]:
        tid = e["test_id"]
        src = REPO / PINNED_CANON_SNAP[tid]
        if sha(src) != PINNED_CANON_SHA[tid]:
            raise SystemExit(f"pinned canonical snapshot drift {tid} (fails closed)")
        snap = snap_dir / Path(CANON_FILE[tid]).name
        shutil.copy2(src, snap)
        new_sha = sha(snap)
        patch_ops.append({"test_id": tid, "field": "fixture", "old": e["fixture"],
                          "new": f"fixtures/canonical_snapshot/{snap.name}"})
        patch_ops.append({"test_id": tid, "field": "sha256", "old": e["sha256"], "new": new_sha})
        e["canonical_path"] = CANON_FILE[tid]
        e["snapshot_source_path"] = PINNED_CANON_SNAP[tid]
        e["snapshot_source_sha256"] = new_sha
        e["snapshot_at"] = now()
        e["fixture"] = f"fixtures/canonical_snapshot/{snap.name}"
        e["sha256"] = new_sha

    man["copy_provenance"] = {
        "built_by": "worker-004",
        "built_at": now(),
        "kind": ("shadow-repo suite copy " + ("with rebased controls" if rebased else "with original frozen controls")),
        "canonical_manifest_sha256": sha(MANIFEST),
        "canonical_runner_sha256": sha(RUNNER),
        "key_manifest": {"sha256": sha(manifest_src), "source": str(manifest_src.relative_to(REPO))},
        "rule_spec": {"sha256": sha(RULE_SPEC), "source": str(RULE_SPEC.relative_to(REPO))},
        "stage_pins": STAGE_PINS,
        "pinned_canonical_basis": PINNED_CANON_SHA,
        "runner_patch": "REPO = HERE.parent.parent -> HERE.parents[2] (one line, shadow path resolution)",
        "fixtures": "byte copies from the canonical suite (runner integrity gate verifies every sha256)",
    }
    (suite / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return {"shadow_root": str(root.relative_to(REPO)), "suite": str(suite.relative_to(REPO)),
            "key_manifest_sha256": sha(manifest_src), "patch_ops": patch_ops}


def run_suite(suite: Path, tag: str) -> dict:
    proc = subprocess.run([sys.executable, str(suite / "run_contract_tests.py")],
                          capture_output=True, text=True, timeout=900)
    (HERE / "logs" / f"{tag}.stdout.log").write_text(proc.stdout)
    (HERE / "logs" / f"{tag}.stderr.log").write_text(proc.stderr)
    obs_path = suite / "observed_verdicts.json"
    obs = json.loads(obs_path.read_text()) if obs_path.exists() else {}
    return {"exit": proc.returncode, "stdout_tail": proc.stdout.strip().splitlines()[-6:],
            "summary": obs.get("summary", {}), "validity": obs.get("validity", {}),
            "observed_verdicts_sha256": sha(obs_path) if obs_path.exists() else None}


def unknown_keys(doc, allowed: set) -> set:
    unk = set()

    def walk(n):
        if isinstance(n, dict):
            for k, v in n.items():
                if str(k) not in allowed:
                    unk.add(str(k))
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(doc)
    return unk


def main() -> int:
    import yaml

    rep = json.loads((HERE / "rebase_report.json").read_text())
    for tid, info in rep["rebased_controls"].items():
        if sha(REBASED / CONTROL_FILE[tid]) != info["rebased_sha256"]:
            raise SystemExit(f"rebased control drift for {tid} (fails closed)")
    if not rep["measurements"]["summary"]["sufficient_to_clear_ADJ_CONTROL_STALENESS"]:
        raise SystemExit("rebase_report does not certify the repair (fails closed)")
    for kind, want in STAGE_PINS.items():
        if sha(STAGE_TOOL[kind]) != want:
            raise SystemExit(f"stage tool {kind} drifted (fails closed)")
    for tid, want in PINNED_CANON_SHA.items():
        if sha(REPO / PINNED_CANON_SNAP[tid]) != want:
            raise SystemExit(f"pinned canonical snapshot drift {tid} (fails closed)")
    km27 = REPO / KM_SNAP["rev27"]["path"]
    km28 = REPO / KM_SNAP["rev28"]["path"]
    if sha(km27) != KM_SNAP["rev27"]["sha256"] or sha(km28) != KM_SNAP["rev28"]["sha256"]:
        raise SystemExit("key-manifest pin drift (fails closed)")

    a27 = set(json.loads(km27.read_text())["allowed_keys"])
    a28 = set(json.loads(km28.read_text())["allowed_keys"])
    out = {"task": "W004-SEMCT-CONTROL-REBASE-02", "created_at": now(),
           "rebased_control_sha256": {t: rep["rebased_controls"][t]["rebased_sha256"] for t in CONTROL_FILE},
           "pinned_canonical_basis": {t: {"snapshot": PINNED_CANON_SNAP[t], "sha256": PINNED_CANON_SHA[t],
                                          "canonical_path": CANON_FILE[t]} for t in CANON_FILE},
           "stage_pins": STAGE_PINS,
           "rule_spec_sha256": sha(RULE_SPEC),
           "key_manifests": {
               "rev27": {"sha256": sha(km27), "source": KM_SNAP["rev27"]["path"],
                         "allowed_keys": len(a27), "has_revised_at_unused": "revised_at_unused" in a27},
               "rev28": {"sha256": sha(km28), "source": KM_SNAP["rev28"]["path"],
                         "allowed_keys": len(a28), "has_revised_at_unused": "revised_at_unused" in a28},
               "rev28_minus_rev27_keys": sorted(a28 - a27),
               "rev27_minus_rev28_keys": sorted(a27 - a28),
           },
           "runs": {}}

    print("building shadow_repo (rev27 manifest) ...")
    sh27p = build_shadow(HERE / "shadow_repo", km27, rebased=True, suite_name="suite_patched")
    sh27s = build_shadow(HERE / "shadow_repo_stale", km27, rebased=False, suite_name="suite_stale")
    print("building shadow_repo_rev28 (current manifest) ...")
    sh28p = build_shadow(HERE / "shadow_repo_rev28", km28, rebased=True, suite_name="suite_patched")
    out["shadows"] = {"rev27_patched": sh27p, "rev27_stale": sh27s, "rev28_patched": sh28p}

    print("run 1/3: rev27 + rebased controls ...")
    out["runs"]["rev27_patched"] = run_suite(REPO / sh27p["suite"], "rev27_patched")
    print("run 2/3: rev27 + original controls (negative control) ...")
    out["runs"]["rev27_stale"] = run_suite(REPO / sh27s["suite"], "rev27_stale")
    print("run 3/3: rev28 + rebased controls (manifest-regression control) ...")
    out["runs"]["rev28_patched"] = run_suite(REPO / sh28p["suite"], "rev28_patched")

    r1 = out["runs"]["rev27_patched"]
    r2 = out["runs"]["rev27_stale"]
    r3 = out["runs"]["rev28_patched"]
    # which fixtures does the rev28 allowlist reject, and on which keys
    rev28_rejects = {}
    for tid, name in list(CONTROL_FILE.items()) + list(CANON_FILE.items()):
        f = REPO / sh28p["suite"] / "fixtures" / ("controls/" + name if tid in CONTROL_FILE
                                                  else "canonical_snapshot/" + Path(name).name)
        unk = sorted(unknown_keys(yaml.safe_load(f.read_text()), a28))
        if unk:
            rev28_rejects[tid] = unk
    out["rev28_unknown_key_rejections"] = rev28_rejects

    ok = (r1["exit"] == 0 and r1["validity"].get("valid_for_calibration") is True
          and r1["summary"].get("structural_caught") == 32
          and r1["summary"].get("semantic_baseline_caught") == 11
          and r1["summary"].get("semantic_hardened_caught") == 32
          and r1["summary"].get("controls_accepted_both_stages") is True
          and r1["summary"].get("conforming_canonical_accepted_both_stages") is True
          and r2["exit"] == 3 and r2["validity"].get("valid_for_calibration") is False
          and r2["summary"].get("controls_accepted_both_stages") is False)
    out["conclusion"] = {
        "rev27_patched_exit": r1["exit"], "rev27_patched_valid_for_calibration": r1["validity"].get("valid_for_calibration"),
        "rev27_stale_exit": r2["exit"], "rev27_stale_valid_for_calibration": r2["validity"].get("valid_for_calibration"),
        "rev28_patched_exit": r3["exit"], "rev28_patched_valid_for_calibration": r3["validity"].get("valid_for_calibration"),
        "single_variable_rev27_pair": "controls only (same mutants, same canonical snapshots, same tools, same manifest)",
        "mutants_unchanged_32_11_32": r1["summary"].get("structural_caught") == 32
                                        and r1["summary"].get("semantic_baseline_caught") == 11
                                        and r1["summary"].get("semantic_hardened_caught") == 32,
        "escapes_adopted_stages": r1["summary"].get("escaped_adopted_stages"),
        "hardened_only_catches": r1["summary"].get("hardened_only_catches"),
        "control_rebase_clears_control_staleness_component": bool(
            r1["summary"].get("controls_accepted_both_stages") is True
            and r2["summary"].get("controls_accepted_both_stages") is False),
        "rev28_manifest_regression_confirmed": bool(r3["exit"] == 3 and rev28_rejects),
        "all_checks_pass": bool(ok),
    }
    out["falsifier"] = rep["falsifier"] + [
        "rev27_patched exiting non-zero or valid_for_calibration not true",
        "rev27_stale exiting 0, i.e. the controls were already acceptable and the rebase is unnecessary",
        "any mutant-count change from 32/11/32, which would mean the copy or tools differ",
        "a rev27 shadow accepting a fixture its manifest allowlist would reject, or vice versa",
        "any byte change in the pinned fixtures, tools, manifests or shadows, which voids the runs",
        "regenerating KEY_MANIFEST with `revised_at_unused` reinstated, which would falsify the regression claim",
    ]
    (HERE / "suite_run_report.json").write_text(json.dumps(out, indent=1) + "\n")

    proposal = {
        "proposal_id": "W004-SEMCT-CONTROL-REBASE-01",
        "author": "worker-004",
        "created_at": now(),
        "owner_of_decision": "astra-lead-formulation",
        "adjudication_item": "ADJ-CONTROL-STALENESS",
        "part_1_control_rebase": {
            "what_it_does": "replace the three frozen controls with the rebased bytes (R28-violating duplicate row deleted)",
            "control_file_replacements": [
                {"path": f"schemas/semantic_contract_tests/fixtures/controls/{CONTROL_FILE[t]}",
                 "old_sha256": STALE_SHA[t],
                 "new_sha256": rep["rebased_controls"][t]["rebased_sha256"],
                 "new_bytes_source": f"artifacts/worker-004/semct_control_rebase/rebased_controls/{CONTROL_FILE[t]}",
                 "diff": rep["rebased_controls"][t]["diff"]} for t in sorted(CONTROL_FILE)
            ],
            "verified_end_to_end": out["conclusion"]["control_rebase_clears_control_staleness_component"],
        },
        "part_2_key_manifest_regression": {
            "finding": ("KEY_MANIFEST rev28 (014e2d301978, written 00:34) was regenerated from the new "
                        "canonical revision and dropped `revised_at_unused` (plus 7 other keys, added 7). "
                        "Under rev28 the binding structural gate R22 rejects the rebased controls, the "
                        "original frozen controls, and the pinned canonical revision that rev27 accepted. "
                        "No frozen corpus is currently usable as calibration evidence."),
            "rev27_sha256": sha(km27), "rev28_sha256": sha(km28),
            "rev28_dropped_keys": sorted(a27 - a28), "rev28_added_keys": sorted(a28 - a27),
            "rejections": rev28_rejects,
            "needed_to_unblock": ("lead decision: freeze KEY_MANIFEST with the schema revision it is used "
                                  "to judge (or make R22 path-sensitive / revision-aware); then re-pin and "
                                  "re-run the suite"),
        },
        "manifest_field_updates": (sh27p["patch_ops"] + sh27s["patch_ops"]),
        "conforming_canonical_repin": {
            "note": ("mechanical (worker-064); re-pin to the canonical revision the lead freezes. Values "
                     "below are the last revision measured accepted by all three stages."),
            "pinned_accepted_values": PINNED_CANON_SHA,
        },
        "mutants": "not touched; all 32 fixture sha256 values unchanged",
        "evidence": {
            "rebase_report": "artifacts/worker-004/semct_control_rebase/rebase_report.json",
            "suite_run_report": "artifacts/worker-004/semct_control_rebase/suite_run_report.json",
            "rev27_patched_observed": f"{sh27p['suite']}/observed_verdicts.json",
            "rev27_stale_observed": f"{sh27s['suite']}/observed_verdicts.json",
            "rev28_patched_observed": f"{sh28p['suite']}/observed_verdicts.json",
        },
        "not_claimed": ["no gate verdict", "no node completion", "no canonical file written",
                        "no theorem or mathematical statement promoted"],
        "falsifier": out["falsifier"],
    }
    (HERE / "manifest_patch_proposal.json").write_text(json.dumps(proposal, indent=1) + "\n")
    print(json.dumps(out["conclusion"], indent=1))
    print("rev28 rejections:", json.dumps(rev28_rejects, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
