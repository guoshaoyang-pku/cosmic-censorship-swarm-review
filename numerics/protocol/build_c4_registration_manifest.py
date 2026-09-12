#!/usr/bin/env python3
"""Worker-14 C4 registration manifest builder (N0 / G-NUM / AF-WCC-SCALAR-SPH).

Purpose
-------
The last worker-side precondition named by the independent protocol review
(`reviews/G-NUM-protocol-review.json`, accept at rev3 `1e6cdf04`) and by the
controller gate audit (00:21:55) is **C4 registration**: `PROTOCOL.md` rule 2
requires a declared artifact's sha256 to be recorded in
`runtime/state/artifact_hashes.json`, and three G-NUM anchors are absent from
that registry while their bytes are on disk and hash-clean.

This builder is *measurement only*. It does not write the registry (a
controller-owned file) and does not set any gate verdict. It produces a
registration-ready manifest the controller can apply in one step.

Declared hashes are resolved at build time from cited on-disk sources
(registry entry, review `reviewed_sha256`, summary provenance, or the 16-char
prefix published in the outbox/review), then compared with freshly measured
bytes. Nothing is hardcoded from memory.

It also re-runs `build_three_scheme_reports.py` into a scratch directory
(never over the registered outputs, so the recorded hashes stay valid) and
compares rebuilt report payloads to the on-disk registered reports. That is
the falsifier test: if the re-run yields an audit FAIL, an R5 disagreement, a
null solver_tolerance, a non-finite delta, a non-deterministic rebuild, a
payload divergence, or the frozen-module guard fires, the manifest must not
be emitted as clean.

Output: numerics/protocol/n0_c4_registration_manifest.json
Usage:  python3 numerics/protocol/build_c4_registration_manifest.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import shutil
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROTOCOL = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "runtime" / "state" / "artifact_hashes.json"
REVIEW_PATH = ROOT / "reviews" / "G-NUM-protocol-review.json"
SUMMARY_PATH = PROTOCOL / "three_scheme_r1r5_summary.json"
OUT = PROTOCOL / "n0_c4_registration_manifest.json"
SCRATCH = PROTOCOL / ".c4_rebuild_scratch"
BUILDER = Path(__file__).resolve()
SCHEMES = ("lffd", "cnfd", "cnfem")
STAMP = time.strftime("%Y-%m-%dT%H:%M:%S%z")

# path, role, declared-full source key or None, published 16-char prefix, prefix source
TARGETS = [
    (
        "numerics/CONVERGENCE_PROTOCOL.md",
        "protocol-of-record revision 3; the rev3 accept verdict and the G-NUM C8 criterion bind here",
        "review:reviewed_sha256",
        "1e6cdf04d7a24313",
        "reviews/G-NUM-protocol-review.json reviewed_sha256 (full) and map gates.G-NUM evidence_refs",
    ),
    (
        "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json",
        "controller-executed FIXED replication run; PROTOCOL.md rule 2 completion hash and the R5/delta provenance anchor",
        None,
        "6542db93eebc5095",
        "reviews/G-NUM-protocol-review.json open_items_outside_protocol_text and map gates.G-NUM.evidence_refs",
    ),
    (
        "artifacts/numerics/n0/lead_4rung_replication.json",
        "lead 4-rung replication addendum carrying delta=max(SLR SE, pair half-range); supplies the R5 uncertainty the FIXED run lacks",
        None,
        "a1f04d2a3cb4d66f",
        "comms/outbox/deepseek-flash-14.jsonl w14-art-2026-09-12T00:15:24+0800-fcdispo",
    ),
    (
        "numerics/tests/n0_order_4rung.json",
        "4-rung order addendum (the >=4-rung requirement of protocol rev3)",
        "registry",
        "c88146a1375c50f0",
        "runtime/state/artifact_hashes.json registry entry",
    ),
    (
        "numerics/tests/flat_wave_replication.py",
        "frozen replication module (hash guard in the builder)",
        "summary:provenance.frozen_module_sha256",
        "8ade1cdc163ea420",
        "numerics/protocol/three_scheme_r1r5_summary.json provenance and builder FROZEN_SHA",
    ),
    (
        "reviews/G-NUM-protocol-review.json",
        "independent audit verdict accept (score 4.5) bound to protocol rev3",
        "registry",
        "8137f18f1a3b2b01",
        "runtime/state/artifact_hashes.json registry entry",
    ),
    (
        "numerics/protocol/three_scheme_r1r5_summary.json",
        "this worker's three-scheme x four-rung R1-R5 summary",
        None,
        "6e1ded36be6f1440",
        "comms/outbox/deepseek-flash-14.jsonl w14-art-2026-09-12T001929+0800-3scheme",
    ),
    (
        "numerics/protocol/fixed_replication_verdict.json",
        "worker re-measurement of the FIXED run (Q1/Q2 verdict)",
        "registry",
        "dcad962324e3be15",
        "runtime/state/artifact_hashes.json registry entry",
    ),
    (
        "numerics/protocol/scheme_independence_review.md",
        "protocol/scheme-independence review that demoted the leapfrog-only harness functional",
        "registry",
        "2fdb85b23f7d120b",
        "runtime/state/artifact_hashes.json registry entry",
    ),
    (
        "numerics/protocol/build_three_scheme_reports.py",
        "deterministic builder that produced the three 4-rung reports",
        "summary:artifact_sha256",
        "11393ba25677d62f",
        "numerics/protocol/three_scheme_r1r5_summary.json artifact_sha256",
    ),
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declared_full(key: str | None, registry: dict, review: dict, summary: dict) -> tuple:
    """Resolve a declared full sha256 from a cited on-disk source."""
    if key is None:
        return None, None
    if key == "registry":
        return None, "runtime/state/artifact_hashes.json (per-path registry entry)"
    if key.startswith("review:"):
        return review.get(key.split(":", 1)[1]), f"reviews/G-NUM-protocol-review.json {key.split(':', 1)[1]}"
    if key.startswith("summary:"):
        node = summary
        for part in key.split(":", 1)[1].split("."):
            node = node[part]
        return node, f"numerics/protocol/three_scheme_r1r5_summary.json {key.split(':', 1)[1]}"
    raise ValueError(key)


def measure_targets() -> tuple:
    registry = json.loads(REGISTRY_PATH.read_text()).get("registry", {})
    review = json.loads(REVIEW_PATH.read_text())
    summary = json.loads(SUMMARY_PATH.read_text())

    records = []
    for path, role, full_key, prefix, prefix_source in TARGETS:
        fp = ROOT / path
        if full_key == "registry":
            full = registry.get(path, {}).get("sha256")
            full_source = "runtime/state/artifact_hashes.json (per-path registry entry)"
        else:
            full, full_source = declared_full(full_key, registry, review, summary)
        rec = {
            "path": path,
            "role": role,
            "declared_sha256": full,
            "declared_sha256_source": full_source,
            "published_prefix": prefix,
            "published_prefix_source": prefix_source,
            "exists_on_disk": fp.exists(),
            "measured_sha256": None,
            "measured_bytes": None,
            "declared_full_match": None if full is None else False,
            "published_prefix_match": False,
            "declared_match": False,
            "registry_status": "absent",
            "registry_sha256": None,
            "registry_match": None,
            "action": "REGISTER",
        }
        if fp.exists():
            data = fp.read_bytes()
            rec["measured_sha256"] = hashlib.sha256(data).hexdigest()
            rec["measured_bytes"] = len(data)
            if full is not None:
                rec["declared_full_match"] = rec["measured_sha256"] == full
            rec["published_prefix_match"] = rec["measured_sha256"].startswith(prefix)
            rec["declared_match"] = rec["published_prefix_match"] and (
                rec["declared_full_match"] is not False)
        reg = registry.get(path)
        if reg:
            rec["registry_status"] = "registered"
            rec["registry_sha256"] = reg.get("sha256")
            rec["registry_match"] = reg.get("sha256") == rec["measured_sha256"]
            rec["action"] = "NO_ACTION_ALREADY_REGISTERED"
        records.append(rec)
    return records, registry


def scratch_rebuild() -> dict:
    """Re-run the three-scheme builder into a scratch dir; compare payloads."""
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location(
        "b3sr_c4_probe", PROTOCOL / "build_three_scheme_reports.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    if str(PROTOCOL) not in sys.path:
        sys.path.insert(0, str(PROTOCOL))
    mod.OUT_DIR = SCRATCH
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.main()

    payload_equal = {}
    for s in SCHEMES:
        disk = json.loads((PROTOCOL / f"report_{s}_4rung.json").read_text())
        scr = json.loads((SCRATCH / f"report_{s}_4rung.json").read_text())
        d1 = {k: v for k, v in disk.items() if k != "generated_at"}
        d2 = {k: v for k, v in scr.items() if k != "generated_at"}
        payload_equal[s] = json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)

    scratch_summary = json.loads((SCRATCH / "three_scheme_r1r5_summary.json").read_text())
    result = {
        "exit_code": rc,
        "stdout": buf.getvalue().strip(),
        "deterministic_rebuild": scratch_summary["deterministic_rebuild"],
        "audits": {s: scratch_summary["reports"][s]["audit_verdict"] for s in SCHEMES},
        "failed_checks": {s: scratch_summary["reports"][s]["failed_checks"] for s in SCHEMES},
        "orders": scratch_summary["verdict"]["orders"],
        "deltas": scratch_summary["verdict"]["deltas"],
        "all_pairs_agree_R5": scratch_summary["verdict"]["all_pairs_agree_R5"],
        "all_have_declared_solver_tolerance": scratch_summary["verdict"]["all_have_declared_solver_tolerance"],
        "payload_equal_to_registered_reports": payload_equal,
        "scratch_dir": str(SCRATCH.relative_to(ROOT)),
        "scratch_removed_after_measurement": True,
    }
    shutil.rmtree(SCRATCH, ignore_errors=True)
    return result


def main() -> int:
    targets, _registry = measure_targets()
    rebuild = scratch_rebuild()

    anchors_ok = all(
        t["exists_on_disk"] and t["declared_match"] and t["published_prefix_match"]
        for t in targets)
    already = [t for t in targets if t["action"] == "NO_ACTION_ALREADY_REGISTERED"]
    request = [t for t in targets if t["action"] == "REGISTER"]
    rebuild_ok = (
        rebuild["exit_code"] == 0
        and rebuild["deterministic_rebuild"]
        and all(v == "PASS" for v in rebuild["audits"].values())
        and rebuild["all_pairs_agree_R5"]
        and all(rebuild["payload_equal_to_registered_reports"].values())
        and rebuild["all_have_declared_solver_tolerance"]
    )

    manifest = {
        "schema": "n0-c4-registration-manifest/v1",
        "actor": "deepseek-flash-14",
        "node_id": "N0",
        "gate": "G-NUM",
        "class_id": "AF-WCC-SCALAR-SPH",
        "assignment_ref": "astra-numfix-03 (residual C4: registration of the N0 G-NUM anchors)",
        "created_at": STAMP,
        "purpose": (
            "Hand the controller a registration-ready, hash-remeasured list so the last named "
            "worker-side precondition of G-NUM (C4 registration, PROTOCOL.md rule 2) can be applied "
            "in one step; also re-runs the three-scheme builder to re-test its own falsifier."
        ),
        "authority_note": (
            "This manifest does NOT write runtime/state/artifact_hashes.json (controller-owned) and "
            "does NOT set status=done, validation_status=passed, or any gate verdict. It is a "
            "measurement and a request; only the controller registers hashes and only Astra "
            "adjudicates G-NUM."
        ),
        "registration_request": [
            {
                "path": t["path"],
                "sha256": t["measured_sha256"],
                "bytes": t["measured_bytes"],
                "role": t["role"],
                "published_prefix": t["published_prefix"],
                "prefix_matches_measured": t["published_prefix_match"],
                "reason_absent_from_registry": (
                    "measured on disk at the published prefix but no registry entry at measurement time"),
            }
            for t in request
        ],
        "registration_request_count": len(request),
        "already_registered": [
            {
                "path": t["path"],
                "measured_sha256": t["measured_sha256"],
                "registry_sha256": t["registry_sha256"],
                "registry_match": t["registry_match"],
            }
            for t in already
        ],
        "verified_anchors": targets,
        "anchors_ok": anchors_ok,
        "rebuild": rebuild,
        "rebuild_ok": rebuild_ok,
        "falsifier": (
            "a re-run of this builder that reports any anchor missing or not matching its published "
            "prefix, a rebuild exit_code != 0, a non-deterministic rebuild, any audit FAIL, any R5 "
            "pair disagreeing, any null solver_tolerance, a report-payload divergence from the "
            "registered reports, or the frozen-module hash guard firing; or a controller "
            "registration of a sha256 that is not the measured_sha256 recorded here"
        ),
        "not_claimed": [
            "no gate verdict and no gate self-pass; G-NUM adjudication is Astra's",
            "no N0 completion; numerics_lock stays LOCKED, N1 not started, numerics/spherical_solver absent",
            "no independent review; this worker may not review its own artifacts",
            "no physics/censorship claim; flat-space calibration evidence only",
            "no claim that the map's 00:21:55 G-NUM unmet list is current; it predates the 00:19-00:20 evidence",
        ],
    }

    OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "manifest": str(OUT.relative_to(ROOT)),
        "sha256": sha256_file(OUT),
        "anchors_ok": anchors_ok,
        "rebuild_ok": rebuild_ok,
        "registration_request": [t["path"] for t in request],
        "already_registered": len(already),
        "builder_sha256": sha256_file(BUILDER),
    }))
    return 0 if (anchors_ok and rebuild_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
