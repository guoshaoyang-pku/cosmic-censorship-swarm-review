#!/usr/bin/env python3
"""Recover the exact pre-repair (rev12) schema bytes from independently written snapshots and
recompute the baseline class-semantics fingerprints for W039-REV13-BINDCHAIN-01.

Why: the baseline was first captured from the live tree while the repair was in flight, so the
raw bytes were not archived and the strict-core digest could not be compared against the
repaired bytes. Six other agents had snapshotted the same rev12 files under hash-verified names
before the repair; this tool re-verifies each candidate against the rev12 sha256 published in
`report_pre_repair.json` and refuses to use any candidate that does not match.

Inputs (all read-only):
  artifacts/worker-039/rev13_binding_chain/report_pre_repair.json   -- the rev12 pins
  candidate snapshot paths listed below

Output:
  artifacts/worker-039/rev13_binding_chain/fingerprints_pre_repair.json  (rewritten)
  artifacts/worker-039/rev13_binding_chain/rev12_recovery.json           (provenance record)

Exit 0 iff all three snapshots match their rev12 pin exactly.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from schema_fingerprint import fingerprint  # noqa: E402

import yaml  # noqa: E402

# candidate snapshots written by other agents before the repair; the first hash-matching
# candidate for each path wins, and every rejected candidate is recorded.
CANDIDATES = {
    "schemas/af_wcc_vacuum.yaml": [
        "artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml",
        "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml",
        "artifacts/worker-007/citebind_census/snapshot/af_wcc_vacuum.cce9c60146d6.yaml",
        "artifacts/worker-080/semct_rebase/stage/schemas/af_wcc_vacuum.yaml",
        "artifacts/worker-032/f1amb25/pinned/af_wcc_vacuum.yaml",
    ],
    "schemas/af_scc_c2_vacuum.yaml": [
        "artifacts/worker-060/rev29_binding_acceptance/snapshots/f2a__af_scc_c2_vacuum.5476a3f2c6bc.yaml",
        "artifacts/worker-007/rev29_preflight/snapshot/af_scc_c2_vacuum.5476a3f2c6bc.yaml",
        "artifacts/worker-007/citebind_census/snapshot/af_scc_c2_vacuum.5476a3f2c6bc.yaml",
        "artifacts/worker-080/semct_rebase/stage/schemas/af_scc_c2_vacuum.yaml",
        "artifacts/worker-061/f2a_rev12_bind/pinned/af_scc_c2_vacuum.yaml",
        "artifacts/worker-061/f2a_independent_verdict/pinned/af_scc_c2_vacuum.yaml",
    ],
    "schemas/af_scc_c0_vacuum.yaml": [
        "artifacts/worker-060/rev29_binding_acceptance/snapshots/f2b__af_scc_c0_vacuum.55d0a1ea9bda.yaml",
        "artifacts/worker-007/rev29_preflight/snapshot/af_scc_c0_vacuum.55d0a1ea9bda.yaml",
    ],
}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    pre = json.loads((HERE / "report_pre_repair.json").read_text())
    pins = pre["schema_pins"]
    fps, provenance, ok = [], {}, True
    for logical, cands in CANDIDATES.items():
        want = pins[logical]
        chosen = None
        tried = []
        for c in cands:
            p = ROOT / c
            if not p.exists():
                tried.append({"path": c, "sha256": None, "accepted": False, "why": "missing"})
                continue
            b = p.read_bytes()
            h = sha(b)
            accepted = h == want
            tried.append({"path": c, "sha256": h, "accepted": accepted,
                          "why": "match" if accepted else "hash mismatch"})
            if accepted and chosen is None:
                chosen = (c, b)
        if chosen is None:
            ok = False
            provenance[logical] = {"declared_rev12_pin": want, "chosen": None, "candidates": tried}
            continue
        c, b = chosen
        doc = yaml.safe_load(b.decode("utf-8"))
        f = fingerprint(doc, b, logical)
        fps.append(f)
        provenance[logical] = {
            "declared_rev12_pin": want,
            "chosen": c,
            "chosen_sha256": sha(b),
            "chosen_revision": doc.get("revision"),
            "strict_core_sha256": f["strict_core_sha256"],
            "prose_sha256": f["prose_sha256"],
            "metadata_sha256": f["metadata_sha256"],
            "candidates": tried,
        }
    if ok:
        (HERE / "fingerprints_pre_repair.json").write_text(
            json.dumps(fps, indent=2, sort_keys=True) + "\n")
    record = {
        "task_id": "W039-REV13-BINDCHAIN-01",
        "tool": "recover_rev12_baseline.py",
        "recovered": ok,
        "note": ("rev12 bytes recovered from independently written, hash-verified snapshots; "
                 "the earlier baseline captured live during the repair is superseded by this one"),
        "schemas": provenance,
    }
    (HERE / "rev12_recovery.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"recovered": ok,
                      "strict_core": {k: v.get("strict_core_sha256", "")[:12] for k, v in provenance.items()}},
                     indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
