#!/usr/bin/env python3
"""L0 freeze reconciliation check (CF-19 / astra-life04-l0-freeze-reconcile).

Purpose
-------
`ledger/theorems.jsonl` moved from the announced rev-3 hand-patch
(`3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6`) to
`a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` at 00:35:19
with no artifact event. This tool produces the owner-side evidence the controller
asked for, machine-checkable and read-only with respect to the canonical ledger:

  C1  live ledger measured (path, sha256, bytes, mtime, rows)
  C2  the nine build inputs (`artifacts/literature/theorems/batch-*.jsonl`) still
      hash to the `after` values recorded in `rev3-axis-split.json`
  C3  a rebuild of the canonical ledger FROM THE SOURCE OF TRUTH, using the repo's
      own `build_literature.py` redirected into a scratch directory, is
      byte-identical to the live ledger (and reproduces L1 `citation_audit.csv`)
  C4  content preservation: no content key differs from either archive
      (`theorems.pre-rev3-*` = ce42d205, `theorems.rev3-handpatch-*` = 3e3d3553)
  C5  claim-lowering vs the self-certified baseline: acceptance vocabulary
      (status/validation_status/supports_claim) removed, review axis recorded as
      absent on every row
  C6  HF-14 predicate census under the A0 rubric text and the strict detector
      (must be 0)
  C7  controls: the HF-14 detector and the content comparator both fire on a
      planted mutation (non-vacuous check)

It writes only `artifacts/literature/reviews/L0-freeze-reconciliation-evidence.json`
plus a scratch rebuild under `tmp/`. It never writes `ledger/`.

Usage:
    python3 artifacts/literature/tools/l0_freeze_reconcile_check.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
LIT = ROOT / "artifacts" / "literature"
LEDGER = ROOT / "ledger"
BUILDER = LIT / "tools" / "build_literature.py"
AXIS_SPLIT = LIT / "reviews" / "rev3-axis-split.json"
EVIDENCE = LIT / "reviews" / "L0-freeze-reconciliation-evidence.json"

EXPECTED_LIVE = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
EXPECTED_PRE = "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72"
EXPECTED_REV3 = "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6"
EXPECTED_L1 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"

# Union of the rev3_axis_split guard keys and worker-073's claim-bearing key list.
CONTENT_KEYS = sorted({
    "statement_exact", "assumptions", "class_ids", "regularity", "topology", "genericity",
    "falsifiers", "unresolved", "source_ids", "conclusion_type", "label", "theorem_id",
    "entry_kind", "scope_caveats", "does_not_imply", "ledger_tags", "next_action",
    "informs_classes",
})
ACCEPTANCE_MARKERS = ("status", "validation_status", "supports_claim")
VERDICT_FIELDS = ("reviewer_verdict", "review_verdict", "independent_verdict", "reviewer",
                  "reviewer_decision", "verdict")
FROZEN_CLASSES = ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                  "AF-WCC-SCALAR-SPH")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def rows(path: Path):
    out = {}
    order = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        tid = o.get("theorem_id", f"__row{i}")
        out[tid] = o
        order.append(tid)
    return out, order


def hf14_predicates(row: dict) -> dict:
    """Literal A0 HF-14 predicates (evaluation_rubric.yaml:244-252).

    Fires when any of status==accepted / validation_status==passed /
    supports_claim is true occurs with no independent reviewer verdict field and
    no artifact hash. In the live ledger all three are absent, so the conjunction
    is evaluated for completeness.
    """
    fires = []
    if row.get("status") == "accepted":
        fires.append("status=accepted")
    if row.get("validation_status") == "passed":
        fires.append("validation_status=passed")
    if row.get("supports_claim") is True:
        fires.append("supports_claim=true")
    if not fires:
        return {"fires": False, "markers": []}
    has_verdict = any(row.get(k) not in (None, "", "not_independently_reviewed")
                      for k in VERDICT_FIELDS)
    has_hash = any(row.get(k) for k in ("artifact_sha256", "artifact_hash", "artifact_refs"))
    return {"fires": not (has_verdict and has_hash), "markers": fires,
            "has_verdict": has_verdict, "has_hash": has_hash}


def rebuild_from_source(scratch: Path) -> dict:
    """Run the repo builder with outputs redirected to scratch. Reads real inputs."""
    spec = importlib.util.spec_from_file_location("build_literature_reconcile", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # module has __name__ != "__main__": no side effects
    real_sources, real_theorems = LIT / "sources", LIT / "theorems"
    mod.LEDGER = scratch / "ledger"
    mod.LIT = scratch / "lit"
    mod.SOURCES = real_sources
    mod.THEOREMS = real_theorems
    (scratch / "ledger").mkdir(parents=True, exist_ok=True)
    (scratch / "lit" / "classes").mkdir(parents=True, exist_ok=True)
    rc = mod.main()
    out = {"exit_code": rc}
    for name, key in (("theorems.jsonl", "ledger"), ("citation_audit.csv", "l1")):
        p = scratch / "ledger" / name
        out[key + "_sha256"] = sha256_file(p) if p.exists() else None
        out[key + "_bytes"] = p.stat().st_size if p.exists() else None
    # determinism: rebuild once more into a second scratch dir
    spec2 = importlib.util.spec_from_file_location("build_literature_reconcile2", BUILDER)
    mod2 = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(mod2)
    mod2.LEDGER = scratch.parent / (scratch.name + "-b") / "ledger"
    mod2.LIT = scratch.parent / (scratch.name + "-b") / "lit"
    mod2.SOURCES, mod2.THEOREMS = real_sources, real_theorems
    mod2.LEDGER.mkdir(parents=True, exist_ok=True)
    (mod2.LIT / "classes").mkdir(parents=True, exist_ok=True)
    rc2 = mod2.main()
    p2 = mod2.LEDGER / "theorems.jsonl"
    out["second_exit_code"] = rc2
    out["second_sha256"] = sha256_file(p2) if p2.exists() else None
    out["deterministic"] = out["second_sha256"] == out["ledger_sha256"]
    return out


def main() -> int:
    result: dict = {"schema": "astra/literature/l0-freeze-reconcile-evidence/v1",
                    "created_at": now(), "actor": "astra-lead-literature",
                    "assignment": "astra-life04-l0-freeze-reconcile", "checks": {}}
    ledger_path = LEDGER / "theorems.jsonl"
    l1_path = LEDGER / "citation_audit.csv"
    live_bytes = ledger_path.read_bytes()
    live, live_order = rows(ledger_path)
    pre, pre_order = rows(LIT / "archive" / "theorems.pre-rev3-20260912T003026.jsonl")
    rev3, rev3_order = rows(LIT / "archive" / "theorems.rev3-handpatch-20260912T003026.jsonl")

    # C1 -- measurement
    st = ledger_path.stat()
    result["checks"]["C1_measured"] = {
        "path": "ledger/theorems.jsonl",
        "sha256": sha256_bytes(live_bytes),
        "bytes": st.st_size,
        "mtime_iso": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
        "rows": len(live),
        "unique_ids": len(set(live)) == len(live),
        "expected": EXPECTED_LIVE,
        "matches_expected": sha256_bytes(live_bytes) == EXPECTED_LIVE,
        "l1": {"path": "ledger/citation_audit.csv", "sha256": sha256_file(l1_path),
               "bytes": l1_path.stat().st_size, "expected": EXPECTED_L1,
               "matches_expected": sha256_file(l1_path) == EXPECTED_L1},
    }

    # C2 -- build inputs at the recorded post-split hashes
    split = json.loads(AXIS_SPLIT.read_text())
    batch_files = sorted((LIT / "theorems").glob("batch-*.jsonl"))
    batches = {}
    for p in batch_files:
        measured = sha256_file(p)
        file_rows = len(rows(p)[1])
        recorded = (split.get("files", {}).get(p.name) or {}).get("after")
        # An empty batch file was never part of the recorded split and contributes
        # no rows; treat it as a no-op rather than a mismatch.
        match = (measured == recorded) if recorded is not None else (file_rows == 0)
        batches[p.name] = {"measured": measured, "recorded_after": recorded,
                           "rows": file_rows, "match": match}
    result["checks"]["C2_source_of_truth"] = {
        "files": batches,
        "all_match": bool(batches) and all(v["match"] for v in batches.values()),
        "nonempty_files": sum(1 for v in batches.values() if v["rows"]),
        "rows": sum(v["rows"] for v in batches.values()),
    }

    # C3 -- rebuild from source of truth (scratch output only)
    scratch = ROOT / "tmp" / f"l0-reconcile-{datetime.now(CST).strftime('%H%M%S')}"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    rebuild = rebuild_from_source(scratch)
    rebuild["is_byte_identical_to_live"] = rebuild.get("ledger_sha256") == EXPECTED_LIVE
    rebuild["reproduces_l1"] = rebuild.get("l1_sha256") == EXPECTED_L1
    result["checks"]["C3_rebuild_from_source"] = rebuild
    shutil.rmtree(scratch, ignore_errors=True)
    shutil.rmtree(scratch.parent / (scratch.name + "-b"), ignore_errors=True)

    # C4 -- content preservation vs both archives
    def content_diffs(a: dict, b: dict) -> list:
        out = []
        for tid in sorted(set(a) | set(b)):
            ra, rb = a.get(tid, {}), b.get(tid, {})
            for k in CONTENT_KEYS:
                if ra.get(k) != rb.get(k):
                    out.append({"theorem_id": tid, "key": k,
                                "archive": json.dumps(rb.get(k), ensure_ascii=False)[:200],
                                "live": json.dumps(ra.get(k), ensure_ascii=False)[:200]})
        return out

    pre_diffs, rev3_diffs = content_diffs(live, pre), content_diffs(live, rev3)
    result["checks"]["C4_content_preservation"] = {
        "content_keys": CONTENT_KEYS,
        "vs_pre_rev3_sha256": EXPECTED_PRE,
        "vs_pre_rev3_diffs": pre_diffs,
        "vs_rev3_handpatch_sha256": EXPECTED_REV3,
        "vs_rev3_handpatch_diffs": rev3_diffs,
        "zero_diffs": not pre_diffs and not rev3_diffs,
        "row_sets_equal": (set(live) == set(pre) == set(rev3)),
        "row_order_equal": live_order == pre_order == rev3_order,
    }

    # C5 -- claim lowering vs the self-certified baseline
    def census(d: dict) -> dict:
        return {
            "status=accepted": sum(1 for r in d.values() if r.get("status") == "accepted"),
            "status=included_unreviewed": sum(1 for r in d.values() if r.get("status") == "included_unreviewed"),
            "validation_status=passed": sum(1 for r in d.values() if r.get("validation_status") == "passed"),
            "supports_claim=true": sum(1 for r in d.values() if r.get("supports_claim") is True),
            "has_status_key": sum(1 for r in d.values() if "status" in r),
            "has_supports_claim_key": sum(1 for r in d.values() if "supports_claim" in r),
            "review_status": sum(1 for r in d.values() if r.get("review_status")),
            "acceptance_authority": sum(1 for r in d.values() if r.get("acceptance_authority")),
            "content_status": dict(Counter(r.get("content_status", "<none>") for r in d.values())),
            "author_asserts_supports_true": sum(1 for r in d.values() if r.get("author_asserts_supports") is True),
        }

    result["checks"]["C5_claim_axis"] = {
        "pre_rev3_self_certified": census(pre),
        "rev3_handpatch": census(rev3),
        "live": census(live),
        "acceptance_vocabulary_removed": (
            census(live)["has_status_key"] == 0
            and census(live)["has_supports_claim_key"] == 0
            and census(live)["validation_status=passed"] == 0),
        "review_axis_recorded_absent": census(live)["review_status"] == len(live),
        "tier_census_preserved": (census(live)["author_asserts_supports_true"]
                                 == census(pre)["supports_claim=true"]),
        "note": ("vs pre-rev3: strictly claim-lowering (acceptance markers 50/60 -> 0, review axis "
                 "recorded absent). vs rev3-handpatch: axis rename, not a further literal lowering; "
                 "the hand-patch's included_unreviewed content tier is carried as content_status and "
                 "its review axis stays explicitly absent. No acceptance-vocabulary token survives."),
    }

    # C6 -- HF-14 predicate census
    def hf14(d: dict) -> dict:
        firing = [tid for tid, r in d.items() if hf14_predicates(r)["fires"]]
        markers = Counter()
        for r in d.values():
            for m in hf14_predicates(r)["markers"]:
                markers[m] += 1
        return {"rows": len(d), "firing_rows": len(firing), "firing_ids": sorted(firing),
                "marker_counts": dict(markers)}

    result["checks"]["C6_hf14"] = {
        "pre_rev3_self_certified": hf14(pre),
        "rev3_handpatch": hf14(rev3),
        "live": hf14(live),
        "rubric_ref": "evaluation_rubric.yaml:244-252 (HF-14 self_certified_acceptance, critical)",
    }

    # C7 -- non-vacuity controls
    planted = dict(next(iter(live.values())))
    planted.update({"status": "accepted", "supports_claim": True})
    planted_result = hf14_predicates(planted)
    mutated = json.loads(json.dumps(next(iter(live.values()))))
    mutated["statement_exact"] = mutated.get("statement_exact", "") + " MUTATION"
    control_diffs = content_diffs({mutated.get("theorem_id", "X"): mutated},
                                  {mutated.get("theorem_id", "X"): next(iter(live.values()))})
    result["checks"]["C7_controls"] = {
        "hf14_positive_control_fires": planted_result["fires"] is True,
        "hf14_positive_control_markers": planted_result["markers"],
        "content_comparator_positive_control_detects": len(control_diffs) == 1,
    }

    # C8 -- report-only: open findings visible at this hash (revise verdicts)
    disj = {tid: r.get("class_ids") for tid, r in live.items()
            if len([c for c in r.get("class_ids", []) if c in FROZEN_CLASSES]) >= 2}
    singular = sum(1 for r in live.values()
                   if len([c for c in r.get("class_ids", []) if c in FROZEN_CLASSES]) == 1)
    unbound = sum(1 for r in live.values()
                  if not [c for c in r.get("class_ids", []) if c in FROZEN_CLASSES])
    result["checks"]["C8_open_findings_report_only"] = {
        "hf02_disjunction_rows": sorted(disj),
        "hf02_disjunction_count": len(disj),
        "class_binding_singular": singular,
        "class_binding_unbound": unbound,
        "class_binding_metric": round(singular / len(live), 4) if live else None,
        "note": "Reported, not adjudicated here; these are the open findings of the two revise verdicts at this hash.",
    }

    result["all_pass"] = all([
        result["checks"]["C1_measured"]["matches_expected"],
        result["checks"]["C1_measured"]["l1"]["matches_expected"],
        result["checks"]["C2_source_of_truth"]["all_match"],
        rebuild.get("is_byte_identical_to_live", False),
        rebuild.get("reproduces_l1", False),
        rebuild.get("deterministic", False),
        result["checks"]["C4_content_preservation"]["zero_diffs"],
        result["checks"]["C4_content_preservation"]["row_sets_equal"],
        result["checks"]["C5_claim_axis"]["acceptance_vocabulary_removed"],
        result["checks"]["C5_claim_axis"]["review_axis_recorded_absent"],
        result["checks"]["C5_claim_axis"]["tier_census_preserved"],
        result["checks"]["C6_hf14"]["live"]["firing_rows"] == 0,
        result["checks"]["C7_controls"]["hf14_positive_control_fires"],
        result["checks"]["C7_controls"]["content_comparator_positive_control_detects"],
    ])

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"evidence": str(EVIDENCE.relative_to(ROOT)),
                      "sha256": sha256_file(EVIDENCE),
                      "all_pass": result["all_pass"],
                      "live": result["checks"]["C1_measured"]["sha256"],
                      "rebuild": rebuild.get("ledger_sha256"),
                      "content_diffs": len(pre_diffs) + len(rev3_diffs),
                      "hf14_live_firing": result["checks"]["C6_hf14"]["live"]["firing_rows"]},
                     indent=2))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
