#!/usr/bin/env python3
"""Emit the v2 review artifact (corrected check-count wording) and superseding events.

v1 review_F2b_55d0a1ea.json (sha b3ccf5e4) remains on disk, byte-identical to the bytes
its events reference.  v2 supersedes it only in one findings sentence: the check tally is
34 total / 31 pass / 3 fail (2 blocking + 1 advisory), not "32 pass".  Verdict, score,
hard failures and all other findings are unchanged.
"""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
D = ROOT / "artifacts/worker-059/f2b_rev12_verdict"
OUTBOX = ROOT / "comms/outbox/worker-059.jsonl"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


v1_path = D / "review_F2b_55d0a1ea.json"
v1 = json.loads(v1_path.read_text())
v1_sha_now = sha(v1_path)
v2 = json.loads(json.dumps(v1))
v2["findings"][0] = v2["findings"][0].replace(
    "34 independent checks, 32 pass;",
    "34 independent checks (31 pass, 3 fail: 2 blocking + 1 advisory);")
v2["supersedes_path"] = "artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea.json"
v2["supersedes_sha256"] = v1_sha_now
v2["supersedes_event_id"] = "w059-f2b-rev12-20260912T004317+0800-review"
v2["note"] = (v2["note"] + " v2 correction: check tally restated as 31 pass / 3 fail "
              "(2 blocking + 1 advisory); one wording fix only, verdict and hard failures "
              "unchanged.")
v2_path = D / "review_F2b_55d0a1ea_v2.json"
v2_path.write_text(json.dumps(v2, indent=1, ensure_ascii=False) + "\n")
v2_sha = sha(v2_path)

now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
eid = "w059-f2b-rev12-" + now.replace(":", "").replace("-", "")

artifact_ev = {
    "event_id": eid + "-artifact-review-v2",
    "event_type": "artifact",
    "created_at": now,
    "actor": "worker-059",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "artifact_type": "independent_review",
    "path": "artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea_v2.json",
    "sha256": v2_sha,
    "reviewed_sha256": v2["reviewed_sha256"],
    "validation_status": "unverified",
    "supersedes_path": v2["supersedes_path"],
    "supersedes_sha256": v1_sha_now,
    "evidence_refs": v2["evidence_refs"],
    "falsifier": v2["next_falsifier"],
}
review_ev = {
    "event_id": eid + "-review-v2",
    "event_type": "review",
    "created_at": now,
    "actor": "worker-059",
    "reviewer": "worker-059",
    "target_id": "F2b",
    "target_path": "schemas/af_scc_c0_vacuum.yaml",
    "node_id": "F2b",
    "group_id": "formulation",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "gate": "G-FORM",
    "reviewed_revision": 12,
    "reviewed_sha256": v2["reviewed_sha256"],
    "artifact": "artifacts/worker-059/f2b_rev12_verdict/review_F2b_55d0a1ea_v2.json",
    "sha256": v2_sha,
    "verdict": "revise",
    "score": 4.0,
    "counts_as_independent_verdict": True,
    "counts_as_full_schema_verdict": True,
    "counts_as_independent_second_verdict": False,
    "supersedes_event_id": "w059-f2b-rev12-20260912T004317+0800-review",
    "supersedes_path": v2["supersedes_path"],
    "supersedes_sha256": v1_sha_now,
    "hard_failures": v2["hard_failures"],
    "findings": v2["findings"],
    "evidence_refs": v2["evidence_refs"],
    "next_falsifier": v2["next_falsifier"],
    "validation_status": "unverified",
    "note": "v2 of the same verdict; supersedes the v1 review event only to correct the check "
            "tally wording (31 pass/3 fail, not 32 pass). Verdict revise 4.0 and both hard "
            "failures unchanged.",
}
for ev in (artifact_ev, review_ev):
    validate_event(ev)
before = OUTBOX.read_text().count("\n")
with open(OUTBOX, "a", encoding="utf-8") as fh:
    for ev in (artifact_ev, review_ev):
        fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
after = OUTBOX.read_text().count("\n")
print(json.dumps({
    "v1_sha256_verified": v1_sha_now,
    "v2_path": str(v2_path.relative_to(ROOT)),
    "v2_sha256": v2_sha,
    "lines_before": before, "lines_after": after,
    "append_only_ok": after == before + 2,
}, indent=1))
