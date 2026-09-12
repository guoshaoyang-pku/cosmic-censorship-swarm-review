#!/usr/bin/env python3
"""W058-CONTAIN-DERIVE-04 checkpoint: re-measure the bound bytes and artifact hashes, then
write runtime/state/w058_checkpoint_4.json and append runtime/state/w058_checkpoints.jsonl.
Fails closed if any hash moved after the events were emitted."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
STATE = os.path.join(ROOT, "runtime", "state")

BOUND = [
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
]
ARTIFACTS = [
    "artifacts/worker-058/contain_derive/derive_containment.py",
    "artifacts/worker-058/contain_derive/containment_derivation.json",
    "artifacts/worker-058/contain_derive/run_sensitivity_selftest.py",
    "artifacts/worker-058/contain_derive/sensitivity_selftest.json",
    "artifacts/worker-058/contain_derive/README.md",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    cert = json.load(open(os.path.join(ROOT, ARTIFACTS[1]), encoding="utf-8"))
    selftest = json.load(open(os.path.join(ROOT, ARTIFACTS[3]), encoding="utf-8"))
    measured = {rel: sha256(os.path.join(ROOT, rel)) for rel in BOUND + ARTIFACTS}

    bound_mismatch = [rel for rel in BOUND
                      if measured[rel] != cert["inputs"]["files"][rel]["sha256"]]
    # the self-test JSON records the checker build it ran against
    checker_mismatch = (selftest["checker_sha256"] != measured[ARTIFACTS[0]])

    # confirm the emitted events carry these exact hashes
    outbox = os.path.join(ROOT, "comms", "outbox", "worker-058.jsonl")
    emitted = {}
    for line in open(outbox, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_id", "").startswith("w058-cd-") and e.get("event_type") == "artifact":
            emitted[e["path"]] = e["sha256"]
    event_mismatch = [rel for rel in ARTIFACTS
                      if emitted.get(rel) and emitted[rel] != measured[rel]]

    checkpoint = {
        "worker": "worker-058",
        "task_id": "W058-CONTAIN-DERIVE-04",
        "checkpoint_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "node_id": "F2b",
        "class_ids": cert["class_ids"],
        "gate": "G-FORM",
        "verdict": cert["verdict"],
        "counts": cert["counts"],
        "bound_inputs": {rel: measured[rel] for rel in BOUND},
        "frozen_revision": cert["inputs"]["frozen_revision"],
        "frozen_match": cert["inputs"]["frozen_match"],
        "chain_links": {l["link_id"]: l["status"] for l in cert["chain"]["links"]},
        "hard_findings": [(f["code"], f["file"], f["line"]) for f in cert["hard_findings"]],
        "advisories": [(f["code"], f["file"], f["line"]) for f in cert["advisories"]],
        "sensitivity_selftest": {
            "cases": selftest["cases_total"],
            "cases_met": selftest["cases_met"],
            "all_expectations_met": selftest["all_expectations_met"],
            "artifact": ARTIFACTS[3],
        },
        "artifact_hashes": {rel: measured[rel] for rel in ARTIFACTS},
        "bound_hash_mismatches_vs_certificate": bound_mismatch,
        "checker_hash_mismatch_vs_selftest": checker_mismatch,
        "artifact_hash_mismatches_vs_emitted_events": event_mismatch,
        "next_falsifier": cert["next_falsifier"],
        "authority_note": cert["authority_note"],
    }

    if bound_mismatch or checker_mismatch or event_mismatch:
        print("CHECKPOINT FAILED: hash movement detected", file=sys.stderr)
        print(json.dumps({"bound": bound_mismatch, "checker": checker_mismatch,
                          "events": event_mismatch}, indent=1), file=sys.stderr)
        return 1

    out = os.path.join(STATE, "w058_checkpoint_4.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(checkpoint, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(STATE, "w058_checkpoints.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "worker": checkpoint["worker"], "task_id": checkpoint["task_id"],
            "checkpoint_at": checkpoint["checkpoint_at"], "verdict": checkpoint["verdict"],
            "counts": checkpoint["counts"],
            "sensitivity_selftest": checkpoint["sensitivity_selftest"],
            "artifact_hash_mismatches_vs_emitted_events": event_mismatch,
        }, ensure_ascii=False) + "\n")
    print("checkpoint written: %s" % os.path.relpath(out, ROOT))
    print("bound hashes stable: %s" % (not bound_mismatch))
    print("verdict=%s hard=%d advisory=%d links=%s selftest=%d/%d"
          % (checkpoint["verdict"], checkpoint["counts"]["hard"],
             checkpoint["counts"]["advisory"], checkpoint["chain_links"],
             selftest["cases_met"], selftest["cases_total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
