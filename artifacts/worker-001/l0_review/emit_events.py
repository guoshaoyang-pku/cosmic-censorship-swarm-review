#!/usr/bin/env python3
"""Emit worker-001's L0 review: review copy, outbox events, checkpoint.

Every event is validated with research_map.schemas.validate_event before it is
written, so nothing is emitted that the controller's ingest would reject.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts" / "worker-001" / "l0_review"
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

NOW = "2026-09-12T00:31:00+08:00"
TAG = "20260912T0031+0800"
ACTOR = "worker-001"
CLASS = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"


def sha(p):
    h = hashlib.sha256()
    with open(ROOT / p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def ref(p):
    return "%s#%s" % (p, sha(p)[:12])


review = json.loads((OUT / "review.json").read_text())
ledger_sha = review["artifact_sha256"]

# 1. review copy (byte-identical to the artifact under artifacts/)
copy = ROOT / "reviews" / "L0-review-worker-001.json"
shutil.copyfile(OUT / "review.json", copy)
assert sha("reviews/L0-review-worker-001.json") == sha(
    "artifacts/worker-001/l0_review/review.json")

# 2. README for the artifact directory
(OUT / "README.md").write_text("""# worker-001 / W001-L0-REVIEW-CE42D205

One bounded class-bound task for gate **G-LIT**, node **L0**, classes
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.

**Verdict: revise, score 3.5, 1 hard failure (HF-L0-01).** The reviewed ledger
meets the locator half of its stop rule (92/92 source_ids resolve, every
registry row carries a doi/arxiv/url, 0 accepted+unverified contradictions) but
fails the class-column half: 28/62 rows have `class_ids: []` (24 accepted), and
21 of those have no `informs_classes` fallback.

Reproduce (read-only on all reviewed paths; exit 3 = hash drift, no verdict):

```bash
python3 artifacts/worker-001/l0_review/run_l0_review.py \\
  --expect-ledger ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72
```

Contents:
- `run_l0_review.py` — pinned checks C1–C13 + 6 negative controls
- `review.json` — the verdict (copy at `reviews/L0-review-worker-001.json`)
- `EVIDENCE.json` — measured hashes, check results, control results
- `raw/arxiv_*.xml` — 4 arXiv Atom payloads fetched at review time (T-302,
  T-505, T-526, T-401), hashed in `EVIDENCE.json`

Not claimed: no gate verdict, no node status, no ledger edit, no claim that any
citation is unsupported (4/4 spot checks SUPPORTED).
""")

# 3. events
events = [
    {"event_id": "w001-l0-artifact-harness-%s" % TAG, "event_type": "artifact",
     "created_at": NOW, "actor": ACTOR, "node_id": "L0", "class_id": CLASS,
     "gate": "G-LIT", "artifact_type": "review_harness",
     "path": "artifacts/worker-001/l0_review/run_l0_review.py",
     "sha256": sha("artifacts/worker-001/l0_review/run_l0_review.py"),
     "validation_status": "unverified",
     "evidence_refs": [ref("artifacts/worker-001/l0_review/EVIDENCE.json")]},
    {"event_id": "w001-l0-artifact-review-%s" % TAG, "event_type": "artifact",
     "created_at": NOW, "actor": ACTOR, "node_id": "L0", "class_id": CLASS,
     "gate": "G-LIT", "artifact_type": "independent_review",
     "path": "artifacts/worker-001/l0_review/review.json",
     "sha256": sha("artifacts/worker-001/l0_review/review.json"),
     "validation_status": "unverified",
     "evidence_refs": ["ledger/theorems.jsonl#%s" % ledger_sha[:12]]},
    {"event_id": "w001-l0-artifact-review-copy-%s" % TAG, "event_type": "artifact",
     "created_at": NOW, "actor": ACTOR, "node_id": "L0", "class_id": CLASS,
     "gate": "G-LIT", "artifact_type": "independent_review_copy",
     "path": "reviews/L0-review-worker-001.json",
     "sha256": sha("reviews/L0-review-worker-001.json"),
     "validation_status": "unverified",
     "evidence_refs": [ref("artifacts/worker-001/l0_review/review.json")]},
    {"event_id": "w001-l0-artifact-evidence-%s" % TAG, "event_type": "artifact",
     "created_at": NOW, "actor": ACTOR, "node_id": "L0", "class_id": CLASS,
     "gate": "G-LIT", "artifact_type": "review_evidence_bundle",
     "path": "artifacts/worker-001/l0_review/EVIDENCE.json",
     "sha256": sha("artifacts/worker-001/l0_review/EVIDENCE.json"),
     "validation_status": "unverified",
     "evidence_refs": ["artifacts/worker-001/l0_review/raw/arxiv_2001.11156.xml",
                       "artifacts/worker-001/l0_review/raw/arxiv_1507.00601.xml",
                       "artifacts/worker-001/l0_review/raw/arxiv_1710.01722.xml",
                       "artifacts/worker-001/l0_review/raw/arxiv_2604.04877.xml"]},
    {"event_id": "w001-l0-review-%s" % TAG, "event_type": "review",
     "created_at": NOW, "actor": ACTOR, "node_id": "L0", "class_id": CLASS,
     "gate": "G-LIT",
     "target_id": "ledger/theorems.jsonl#%s" % ledger_sha,
     "reviewer": ACTOR, "verdict": review["verdict"], "score": review["score"],
     "hard_failures": review["hard_failures"], "findings": review["findings"],
     "positives": review["positives"], "conditions": [f["id"] for f in review["findings"]
                                                      if f["severity"] in ("major", "minor")],
     "artifact_refs": [ref("artifacts/worker-001/l0_review/review.json"),
                       ref("artifacts/worker-001/l0_review/run_l0_review.py"),
                       ref("artifacts/worker-001/l0_review/EVIDENCE.json")],
     "evidence_refs": ["ledger/theorems.jsonl#%s" % ledger_sha[:12],
                       "artifacts/literature/registry.jsonl#%s" % sha("artifacts/literature/registry.jsonl")[:12],
                       "ledger/citation_audit.csv#%s" % sha("ledger/citation_audit.csv")[:12],
                       "research_map/formulation_taxonomy.yaml#%s" % sha("research_map/formulation_taxonomy.yaml")[:12]],
     "controls_all_passed": review["cross_checks"]["controls_all_passed"],
     "next_falsifier": review["next_falsifier"],
     "authority_note": review["authority_note"]},
    {"event_id": "w001-l0-status-%s" % TAG, "event_type": "status",
     "created_at": NOW, "actor": ACTOR, "node_id": "L0", "class_id": CLASS,
     "gate": "G-LIT", "status": "active", "hours": 0.6,
     "summary": ("worker-001 bounded task complete: independent hash-pinned L0 review at "
                 "ledger sha256 %s -> verdict revise (score 3.5, HF-L0-01: L0 stop-rule "
                 "class-column clause unmet, 28/62 rows empty class_ids, 21 with no "
                 "informs_classes fallback). Worker lifecycle ends; node L0 status is NOT "
                 "moved by this event." % ledger_sha[:12]),
     "evidence_refs": [ref("artifacts/worker-001/l0_review/review.json"),
                       ref("reviews/L0-review-worker-001.json"),
                       ref("artifacts/worker-001/l0_review/EVIDENCE.json")],
     "next_falsifier": review["next_falsifier"]},
]
for e in events:
    validate_event(e)

outbox = ROOT / "comms" / "outbox" / "worker-001.jsonl"
existing = {json.loads(l)["event_id"] for l in open(outbox) if l.strip()}
new = [e for e in events if e["event_id"] not in existing]
with open(outbox, "a") as f:
    for e in new:
        f.write(json.dumps(e, sort_keys=True) + "\n")

# 4. checkpoint
ckpt = {
    "checkpoint_id": "w001-l0-ckpt-%s" % TAG,
    "at": NOW, "actor": ACTOR, "role": "worker", "slot": "001",
    "lifecycle": "one bounded class-bound task, then exit",
    "node_id": "L0", "gate": "G-LIT", "class_id": CLASS,
    "task": "independent hash-pinned L0 review of ledger/theorems.jsonl at %s" % ledger_sha,
    "verdict": review["verdict"], "score": review["score"],
    "hard_failures": [h["id"] for h in review["hard_failures"]],
    "findings": [f["id"] for f in review["findings"]],
    "controls_all_passed": review["cross_checks"]["controls_all_passed"],
    "artifacts": [{"path": p, "sha256": sha(p)} for p in (
        "artifacts/worker-001/l0_review/run_l0_review.py",
        "artifacts/worker-001/l0_review/review.json",
        "artifacts/worker-001/l0_review/EVIDENCE.json",
        "artifacts/worker-001/l0_review/README.md",
        "reviews/L0-review-worker-001.json",
        "ledger/theorems.jsonl",
        "artifacts/literature/registry.jsonl",
        "ledger/citation_audit.csv",
        "research_map/formulation_taxonomy.yaml",
        "artifacts/literature/L0_L1_ACCEPTANCE.md")],
    "events_emitted": [e["event_id"] for e in new],
    "next_falsifier": review["next_falsifier"],
    "authority_note": review["authority_note"],
}
(ROOT / "runtime" / "state" / "worker-001_checkpoint_l0.json").write_text(
    json.dumps(ckpt, indent=1) + "\n")
with open(ROOT / "runtime" / "state" / "worker-001_checkpoints.jsonl", "a") as f:
    f.write(json.dumps({k: ckpt[k] for k in (
        "checkpoint_id", "at", "actor", "node_id", "gate", "class_id", "task",
        "verdict", "score", "hard_failures", "findings",
        "controls_all_passed", "events_emitted")}, sort_keys=True) + "\n")

print(json.dumps({"emitted_events": len(new), "outbox_lines": len(existing) + len(new),
                  "checkpoint": "runtime/state/worker-001_checkpoint_l0.json",
                  "review_copy": "reviews/L0-review-worker-001.json",
                  "verdict": review["verdict"]}, indent=1))
