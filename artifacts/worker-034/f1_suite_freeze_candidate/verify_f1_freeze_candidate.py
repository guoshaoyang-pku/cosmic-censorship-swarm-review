#!/usr/bin/env python3
"""W034-F1-FREEZE-CANDIDATE-DERIVATION-01 -- independent verification pass.

Re-reads the *on-disk* candidate bytes (not the in-memory objects the derivation
script adjudicated), re-runs the imported C1-C8 battery, and checks two owner
variants that must remain freeze-ready:

  V1  rebind_note omitted on every row (minimal-byte publication variant);
  V2  binding_frozen_revision=30 (the row is part of the FROZEN rev30 issue).

Writes verification.json next to the candidate.  Read-only on canonical paths.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-034/f1_suite_freeze_candidate"
CAND = OUT / "candidate" / "f1_falsifier_tests.rev13.frozen29.derived.jsonl"
ADJ_PATH = (
    ROOT
    / "artifacts/worker-034/f1_repair_candidate_adjudication"
    / "adjudicate_f1_repair_candidates.py"
)
CST = timezone(timedelta(hours=8))


def load_adj():
    spec = importlib.util.spec_from_file_location("w034_adj_verify", ADJ_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    adj = load_adj()
    raw = CAND.read_bytes()
    rows = [json.loads(l) for l in raw.decode("utf-8").splitlines() if l.strip()]
    orig_rows = adj.load_jsonl(ROOT / adj.DECLARED["corpus_orig"][0])
    live_doc = adj.yaml.safe_load((ROOT / adj.DECLARED["f1_live_rev13"][0]).read_text())
    rev12_doc = adj.yaml.safe_load((ROOT / adj.DECLARED["f1_rev12"][0]).read_text())
    authoring_doc = adj.yaml.safe_load((ROOT / adj.DECLARED["f1_authoring_rev11"][0]).read_text())

    res = adj.check_candidate("cand_w034_derived_on_disk", rows, orig_rows, live_doc,
                              rev12_doc, authoring_doc)
    on_disk = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "rows": len(rows),
        "freeze_ready": res["freeze_ready"],
        "failed_checks": [c["check_id"] for c in res["checks"] if c["status"] == "FAIL"],
        "checks": res["checks"],
    }

    variants = []
    import copy

    v1 = copy.deepcopy(rows)
    for r in v1:
        r.pop("rebind_note", None)
    r1 = adj.check_candidate("V1_no_rebind_note", v1, orig_rows, live_doc, rev12_doc,
                             authoring_doc)
    variants.append({"variant": "V1_no_rebind_note", "freeze_ready": r1["freeze_ready"],
                     "failed_checks": [c["check_id"] for c in r1["checks"]
                                       if c["status"] == "FAIL"]})
    v2 = copy.deepcopy(rows)
    for r in v2:
        r["binding_frozen_revision"] = 30
    r2 = adj.check_candidate("V2_frozen_rev30", v2, orig_rows, live_doc, rev12_doc,
                             authoring_doc)
    variants.append({"variant": "V2_binding_frozen_revision_30",
                     "freeze_ready": r2["freeze_ready"],
                     "failed_checks": [c["check_id"] for c in r2["checks"]
                                       if c["status"] == "FAIL"]})

    applied_sha = adj.sha256_file(ROOT / "schemas/f1_falsifier_tests.jsonl")
    out = {
        "task_id": "W034-F1-FREEZE-CANDIDATE-DERIVATION-01",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "authority": "worker evidence only; no canonical write performed",
        "candidate": str(CAND.relative_to(ROOT)),
        "on_disk": on_disk,
        "owner_variants": variants,
        "applied_corpus_sha256_at_verify": applied_sha,
        "applied_corpus_is_still_rev29": applied_sha
        == adj.DECLARED["corpus_orig"][1],
        "falsifier": "the on-disk candidate failing any C1-C8 check, or a variant "
                     "regressing, or the applied corpus already having moved off the "
                     "pinned rev29 bytes",
    }
    (OUT / "verification.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(
        "on_disk freeze_ready=%s sha=%s variants=%s applied_still_rev29=%s"
        % (
            on_disk["freeze_ready"],
            on_disk["sha256"][:16],
            [(v["variant"], v["freeze_ready"]) for v in variants],
            out["applied_corpus_is_still_rev29"],
        )
    )
    ok = on_disk["freeze_ready"] and all(v["freeze_ready"] for v in variants)
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
