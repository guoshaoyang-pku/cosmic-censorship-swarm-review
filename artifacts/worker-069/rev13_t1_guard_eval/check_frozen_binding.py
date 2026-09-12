#!/usr/bin/env python3
"""W069-GFORM-T1-GUARD-REV13-01 supporting check: frozen-revision binding for the
T1 guard inputs plus the publication mirror check.

Read-only. Verifies:
  1. each live canonical input re-hashes to the snapshot pin;
  2. the FROZEN rev29 manifest entries for the schema/taxonomy paths equal those pins;
  3. the artifacts/formulation/schemas mirrors are byte-identical to the canonical schemas.
Controls: an in-memory manifest corrupted at one entry must be detected; a mismatch of
exactly one pin must be attributed to exactly that path.

Measurement only: no gate verdict, no node status, no validation_status=passed.
Exit 0 if all checks pass, 2 otherwise.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot")
CST = timezone(timedelta(hours=8))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# path -> (snapshot copy, expected sha256)
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": ("schemas_af_scc_c0_vacuum.yaml",
                                      "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "schemas/af_scc_c2_vacuum.yaml": ("schemas_af_scc_c2_vacuum.yaml",
                                      "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "schemas/af_wcc_vacuum.yaml": ("schemas_af_wcc_vacuum.yaml",
                                   "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "research_map/formulation_taxonomy.yaml": ("research_map_formulation_taxonomy.yaml",
                                               "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "artifacts/formulation/evidence/taxonomy_consistency.json": (
        "artifacts_formulation_evidence_taxonomy_consistency.json",
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"),
}
FROZEN_SNAP = "artifacts_formulation_FROZEN.json"
FROZEN_EXPECTED_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
MIRRORS = {
    "schemas/af_wcc_vacuum.yaml": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}


def manifest_binding_error(manifest, pins):
    """Return list of (path, expected, manifest_value) where manifest disagrees."""
    errs = []
    for path, (_snap, expected) in pins.items():
        got = (manifest.get("files", {}).get(path) or {}).get("sha256")
        if got != expected:
            errs.append((path, expected, got))
    return errs


def main():
    result = {
        "task_id": "W069-GFORM-T1-GUARD-REV13-01-support-frozen-binding",
        "actor": "worker-069",
        "generated_at": datetime.now(CST).isoformat(),
        "authority_note": "Worker measurement only; no gate verdict, node status or validation_status=passed.",
    }

    # snapshot integrity
    snap_ok = {}
    for path, (snap, expected) in PINS.items():
        snap_ok[path] = (sha256_file(os.path.join(SNAP, snap)) == expected)

    # live canonical vs pin
    live = {}
    for path, (_snap, expected) in PINS.items():
        got = sha256_file(os.path.join(ROOT, path))
        live[path] = {"expected": expected, "measured": got, "ok": got == expected}

    with open(os.path.join(SNAP, FROZEN_SNAP)) as f:
        manifest = json.load(f)
    frozen_sha = sha256_file(os.path.join(SNAP, FROZEN_SNAP))
    frozen_binding = manifest_binding_error(manifest, PINS)
    frozen_meta = {
        "revision": manifest.get("revision"),
        "frozen_at": manifest.get("frozen_at"),
        "files": len(manifest.get("files", {})),
        "snapshot_sha256": frozen_sha,
        "snapshot_sha256_matches_pin": frozen_sha == FROZEN_EXPECTED_SHA,
        "binding_errors": [{"path": p, "expected": e, "manifest": g} for p, e, g in frozen_binding],
    }

    mirrors = {}
    for canonical, mirror in MIRRORS.items():
        a = sha256_file(os.path.join(ROOT, canonical))
        b = sha256_file(os.path.join(ROOT, mirror))
        mirrors[mirror] = {"canonical_sha256": a, "mirror_sha256": b, "identical": a == b,
                           "mirror_matches_pin": b == PINS[canonical][1]}

    # controls: corrupt one manifest entry in memory -> exactly that path flagged
    corrupt = json.loads(json.dumps(manifest))
    victim = "schemas/af_scc_c0_vacuum.yaml"
    corrupt["files"][victim]["sha256"] = "0" * 64
    ctl_errs = manifest_binding_error(corrupt, PINS)
    ctl_manifest = {
        "expected": "exactly one error at the corrupted path",
        "observed_paths": [p for p, _e, _g in ctl_errs],
        "ok": [p for p, _e, _g in ctl_errs] == [victim],
    }

    ctl_pin = {
        "expected": "flipping one pin makes exactly that live path fail",
        "ok": None,
    }
    flipped = dict(PINS)
    flipped[victim] = (PINS[victim][0], "0" * 64)
    bad = [p for p, (_s, exp) in flipped.items()
           if sha256_file(os.path.join(ROOT, p)) != exp]
    ctl_pin["observed_paths"] = bad
    ctl_pin["ok"] = bad == [victim]

    all_ok = (all(snap_ok.values())
              and all(v["ok"] for v in live.values())
              and not frozen_binding
              and frozen_meta["snapshot_sha256_matches_pin"]
              and all(v["identical"] for v in mirrors.values())
              and ctl_manifest["ok"] and ctl_pin["ok"])

    result.update({
        "snapshot_integrity": snap_ok,
        "live_canonical_vs_pin": live,
        "frozen_manifest": frozen_meta,
        "mirror_check": mirrors,
        "controls": {"CTL_CORRUPT_MANIFEST_ENTRY": ctl_manifest, "CTL_FLIPPED_PIN": ctl_pin},
        "all_checks_pass": bool(all_ok),
        "verdict": "FROZEN_BINDING_INTACT" if all_ok else "FROZEN_BINDING_BROKEN",
    })

    out = os.path.join(HERE, "raw", "frozen_binding.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
        f.write("\n")

    print(json.dumps({
        "snapshot_integrity_all": all(snap_ok.values()),
        "live_all_match": all(v["ok"] for v in live.values()),
        "frozen_revision": frozen_meta["revision"],
        "frozen_binding_errors": len(frozen_binding),
        "mirrors_identical": all(v["identical"] for v in mirrors.values()),
        "controls_ok": ctl_manifest["ok"] and ctl_pin["ok"],
        "verdict": result["verdict"],
    }, indent=1))
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
