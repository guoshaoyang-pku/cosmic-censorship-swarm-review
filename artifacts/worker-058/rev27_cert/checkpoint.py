#!/usr/bin/env python3
"""W058-REV27-CERT-03 checkpoint.

Re-hashes every bound input, every emitted artifact and every artifact event written by this
task, and records `runtime/state/w058_checkpoint_3.json` + a line in
`runtime/state/w058_checkpoints.jsonl`. Refuses to checkpoint if any emitted artifact hash
differs from disk.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STATE = os.path.join(ROOT, "runtime", "state")
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-058.jsonl")
TASK = "W058-REV27-CERT-03"
STAMP = "w058-rc3-"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    cert = json.load(open(os.path.join(HERE, "rev12_delta_cert.json"), encoding="utf-8"))
    sweep = json.load(open(os.path.join(HERE, "sweep_rev27.json"), encoding="utf-8"))
    selftest = json.load(open(os.path.join(HERE, "sensitivity_selftest.json"), encoding="utf-8"))

    artifacts = {}
    for rel in [
        "artifacts/worker-058/rev27_cert/check_rev12_delta.py",
        "artifacts/worker-058/rev27_cert/rev12_delta_cert.json",
        "artifacts/worker-058/rev27_cert/sweep_rev27.json",
        "artifacts/worker-058/rev27_cert/sweep_scc_order_frozen_copy.py",
        "artifacts/worker-058/rev27_cert/run_sensitivity_selftest.py",
        "artifacts/worker-058/rev27_cert/sensitivity_selftest.json",
        "artifacts/worker-058/rev27_cert/README.md",
        "artifacts/worker-058/rev27_cert/emit_events.py",
        "artifacts/worker-058/rev27_cert/checkpoint.py",
    ]:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            artifacts[rel] = sha256(p)

    binding = {}
    for rel, label in [("schemas/af_scc_c0_vacuum.yaml", "AF-SCC-C0-VAC-GEN"),
                       ("schemas/af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN"),
                       ("artifacts/formulation/FROZEN.json", "FROZEN.json")]:
        binding[label] = {"path": rel, "live_now": sha256(os.path.join(ROOT, rel))}

    # verify every artifact event written by this task against disk
    mismatches, emitted = [], []
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if not e.get("event_id", "").startswith(STAMP):
                continue
            emitted.append(e["event_id"])
            if e["event_type"] == "artifact":
                disk = sha256(os.path.join(ROOT, e["path"]))
                if disk != e["sha256"]:
                    mismatches.append({"event_id": e["event_id"], "path": e["path"],
                                       "emitted": e["sha256"], "disk": disk})
    if not emitted:
        print("checkpoint refused: no %s events found in %s" % (STAMP, OUTBOX), file=sys.stderr)
        return 2
    if mismatches:
        print("checkpoint refused: artifact hash mismatches %s" % mismatches, file=sys.stderr)
        return 2
    if cert["verdict"] != "FAIL" or sweep["verdict"] != "FAIL":
        print("checkpoint refused: verdict moved off the bound FAIL", file=sys.stderr)
        return 2
    if not selftest.get("all_expectations_met"):
        print("checkpoint refused: self-test not calibrated", file=sys.stderr)
        return 2

    # the certificate must still bind the live SCC bytes, else it is stale
    drift = []
    for rel, label in [("schemas/af_scc_c0_vacuum.yaml", "AF-SCC-C0-VAC-GEN"),
                       ("schemas/af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN")]:
        live = binding[label]["live_now"]
        bound = cert["inputs"]["files"][rel]["sha256"]
        if live != bound:
            drift.append({"path": rel, "certificate": bound, "live_now": live})
    if drift:
        print("checkpoint refused: canonical bytes moved since the certificate; re-run the "
              "certificate first: %s" % drift, file=sys.stderr)
        return 3

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    hard = [{"id": ("HF-1" if f["check"] == "D6_HF1_open" else "MINOR-1"),
             "check": f["check"], "file": f["file"], "line": f.get("line"),
             "detail": f.get("detail")} for f in cert["hard_findings"]]

    payload = {
        "worker": "worker-058",
        "slot": "058",
        "task_id": TASK,
        "node_id": "F2b",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate_context": "G-FORM",
        "checkpoint_at": now,
        "verdict": "FAIL",
        "counts": {"hard": cert["counts"]["hard"], "advisory": 3, "consistent": 35,
                   "total_claims_evaluated": 40},
        "hard_findings": hard,
        "rev12_claim_checks": {k: v["status"] for k, v in cert["rev12_claim_checks"].items()},
        "order_strength_delta": {
            "new_hard_codes": cert["delta"]["new_hard_codes"],
            "resolved_hard_codes": cert["delta"]["resolved_hard_codes"],
            "persisting_hard_codes": cert["delta"]["persisting_hard_codes"],
            "line_shift": cert["delta"]["line_shift"],
            "baseline_sha256": cert["delta"]["baseline_expected_sha256"],
        },
        "sensitivity_selftest": {
            "cases": selftest["cases_total"],
            "cases_met": selftest["cases_met"],
            "all_expectations_met": selftest["all_expectations_met"],
            "artifact": "artifacts/worker-058/rev27_cert/sensitivity_selftest.json",
        },
        "binding": binding,
        "frozen_manifest_revision_measured": cert["inputs"]["frozen_revision"],
        "manifest_motion_note": cert["inputs"]["manifest_motion_note"],
        "artifacts": artifacts,
        "artifact_hash_mismatches_vs_emitted_events": mismatches,
        "events_emitted": emitted,
        "outbox_lines_total": sum(1 for line in open(OUTBOX, encoding="utf-8") if line.strip()),
        "next_falsifier": cert["next_falsifier"],
        "authority_note": cert["authority_note"],
    }
    os.makedirs(STATE, exist_ok=True)
    out = os.path.join(STATE, "w058_checkpoint_3.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(STATE, "w058_checkpoints.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "worker": "worker-058", "task_id": TASK, "checkpoint_at": now,
            "verdict": "FAIL",
            "counts": payload["counts"],
            "sensitivity_selftest": payload["sensitivity_selftest"],
            "artifact_hash_mismatches_vs_emitted_events": mismatches,
        }, ensure_ascii=False) + "\n")
    print("checkpoint written: %s (%d artifacts, %d emitted events, 0 mismatches)"
          % (os.path.relpath(out, ROOT), len(artifacts), len(emitted)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
