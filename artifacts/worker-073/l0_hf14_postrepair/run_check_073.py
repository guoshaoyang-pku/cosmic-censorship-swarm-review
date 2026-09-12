#!/usr/bin/env python3
"""W073-L0-HF14-POSTREPAIR-01: independent post-repair check of the L0 rev-3 HF-14 closure.

Bounded class-bound worker task (worker-073, instance 2026-09-12T002948-968807).
Node L0, gate G-LIT. Classes covered: the four frozen ids, per-class census in the report.
No network, no writes outside artifacts/worker-073/l0_hf14_postrepair/.

Question
--------
The literature lead's rev-3 repair renamed acceptance vocabulary in ledger/theorems.jsonl
(ce42d205e761 -> 3e3d35531421) and asserts HF-14 closed. Two things had not been delivered:

  (1) an independent read of the rev-3 delta (are the claim-bearing fields byte-preserved?),
  (2) a check, by an own implementation of the rubric's HF-14 detector text, of whether the
      predicates really return 0 -- including the pre-repair revision as a positive control.

Moving-target handling (added after observing the target move during this task)
-------------------------------------------------------------------------------
At the first run of this script (2026-09-12T00:33+08:00) the live ledger was 3e3d3553 (the
pin check passed and the analysis completed). Before the second run the live file had moved
to a1674f09 (mtime 00:35:19), so the second run failed closed. The verdict is therefore bound
to the *archived* rev-3 bytes (artifacts/literature/archive/theorems.rev3-handpatch-
20260912T003026.jsonl, hash-verified == 3e3d3553), which is the revision the lead's repair
record declares as after_sha256. The live ledger is probed at start and end and reported as an
observation only; nothing is certified about a revision that moves during the run.

Method (pre-declared; detector written from evaluation_rubric.yaml:243-252 only, no import of
artifacts/audit/audit_lib.py or the lead's repair tool)
--------------------------------------------------------------------------------------------
HF-14 text: "a ledger or claim record sets status=accepted / validation_status=passed /
supports_claim=true with no independent reviewer verdict field and no artifact hash; an
author's own selftest is not a reviewer verdict".

  acceptance markers (literal): status == "accepted" | validation_status == "passed" |
                                supports_claim is True
  reviewer verdict field       : any of VERDICT_FIELDS non-empty and not a placeholder
  artifact hash field          : any 64-hex token in HASH_FIELDS (incl. artifact_refs[].sha256)

Three readings are reported because the detector text is ambiguous on "independent":
  R1 literal-weak : markers and no verdict FIELD and no hash FIELD (what the text says)
  R2 strict       : markers and no *identity-bearing* verdict and no *resolvable* hash
  R3 any-absence  : markers and (no verdict field OR no hash field)  [harshest reading]

Fail closed: every *certified* input hash is hardcoded; any mismatch raises before a verdict is
written. The certified revision is re-measured after the analysis; drift voids the verdict.

Output: report.json, raw/live_probe.json (+ stdout log). Worker evidence only: no node status,
no gate verdict, no canonical file edited.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
ARCHIVE_REV3 = ROOT / "artifacts" / "literature" / "archive" / "theorems.rev3-handpatch-20260912T003026.jsonl"
OLD_LEDGER = ROOT / "artifacts" / "literature" / "archive" / "theorems.pre-rev3-20260912T003026.jsonl"
LIVE_LEDGER = ROOT / "ledger" / "theorems.jsonl"
L1_LEDGER = ROOT / "ledger" / "citation_audit.csv"
RUBRIC = ROOT / "evaluation_rubric.yaml"
REPAIR_RECORD = ROOT / "artifacts" / "literature" / "reviews" / "L0-rev3-hf14-repair.json"
OUTDIR = ROOT / "artifacts" / "worker-073" / "l0_hf14_postrepair"
RAW = OUTDIR / "raw"
REPORT = OUTDIR / "report.json"

# Hardcoded pins (fail closed) for the CERTIFIED inputs only.
REV3_SHA = "3e3d35531421388a17ca7bad7f6c7093dd1cc21a3a808ca8ff65ce6c2b79c6a6"
OLD_SHA = "ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72"
PINS = {
    str(ARCHIVE_REV3.relative_to(ROOT)): REV3_SHA,
    str(OLD_LEDGER.relative_to(ROOT)): OLD_SHA,
    str(L1_LEDGER.relative_to(ROOT)): "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    str(RUBRIC.relative_to(ROOT)): "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
}

ACCEPT_STATUS = {"accepted"}
PASS_VALIDATION_STATUS = {"passed"}
VERDICT_FIELDS = ("reviewer_verdict", "review_verdict", "independent_verdict",
                  "reviewer", "reviewer_decision", "verdict")
HASH_FIELDS = ("artifact_sha256", "artifact_hash", "artifact_hashes", "artifact_refs",
               "validation_artifact_sha256", "evidence_sha256")
PLACEHOLDER = {"", "none", "null", "n/a", "na", "not_independently_reviewed", "unreviewed",
               "author", "self", "self-assessment", "pending"}
AUTHOR_TOKEN = "astra-lead-literature"
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")

CLAIM_BEARING_FIELDS = (
    "theorem_id", "label", "statement_exact", "assumptions", "conclusion_type", "class_ids",
    "source_ids", "falsifiers", "genericity", "regularity", "topology", "scope_caveats",
    "does_not_imply", "unresolved", "entry_kind", "evidence_level",
    "informs_classes", "ledger_tags",
)
# Fields the repair is allowed to move: acceptance/status vocabulary only.
# supports_claim_basis is mutable by construction: it is the textual basis for the
# supports_claim marker the repair withdraws (null -> explicit non-adjudication caveat).
MUTABLE_FIELDS = ("status", "review_status", "supports_claim", "supports_claim_basis",
                  "status_note", "acceptance_authority", "verification_status", "next_action",
                  "review_refs")

CST = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in open(p) if line.strip()]


def norm(v) -> str:
    return str(v).strip().lower() if v is not None else ""


def compact(v, limit: int = 200):
    """JSON-safe, bounded rendering of an old/new field value for the delta census."""
    if isinstance(v, str):
        return v if len(v) <= limit else v[:limit] + f"...<+{len(v) - limit}>"
    s = json.dumps(v, sort_keys=True, ensure_ascii=False)
    return s if len(s) <= limit else s[:limit] + f"...<+{len(s) - limit}>"


# --- HF-14 detector (own implementation) -------------------------------------------------

def acceptance_markers(row: dict) -> list[str]:
    out = []
    if norm(row.get("status")) in ACCEPT_STATUS:
        out.append("status=accepted")
    if norm(row.get("validation_status")) in PASS_VALIDATION_STATUS:
        out.append("validation_status=passed")
    if row.get("supports_claim") is True:
        out.append("supports_claim=true")
    return out


def verdict_field_present(row: dict) -> tuple[bool, list[str]]:
    hits = []
    for f in VERDICT_FIELDS:
        v = row.get(f)
        if v is None or v == "" or v == {} or v == []:
            continue
        if isinstance(v, str) and norm(v) in PLACEHOLDER:
            continue
        hits.append(f)
    return bool(hits), hits


def verdict_strong_present(row: dict) -> tuple[bool, list[str]]:
    """Identity-bearing independent verdict: a reviewer identity that is not the ledger author,
    with a verdict value, and (for dicts) an evidence/hash anchor."""
    hits = []
    for f in VERDICT_FIELDS:
        v = row.get(f)
        if v is None or v == "" or v == {} or v == []:
            continue
        if isinstance(v, str):
            if norm(v) in PLACEHOLDER or AUTHOR_TOKEN in norm(v):
                continue
            hits.append(f)
        elif isinstance(v, dict):
            blob = json.dumps(v, sort_keys=True).lower()
            if AUTHOR_TOKEN in blob:
                continue
            ident = any(v.get(k) for k in ("reviewer", "reviewer_id", "agent", "agent_id", "actor", "id"))
            anchor = bool(HEX64.search(blob)) or bool(v.get("evidence_refs") or v.get("artifact_refs"))
            if ident and (v.get("verdict") or v.get("decision")) and anchor:
                hits.append(f)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    blob = json.dumps(item, sort_keys=True).lower()
                    if AUTHOR_TOKEN in blob:
                        continue
                    if any(item.get(k) for k in ("reviewer", "reviewer_id", "agent", "actor")) and \
                       (item.get("verdict") or item.get("decision")) and HEX64.search(blob):
                        hits.append(f)
                        break
    return bool(hits), hits


def hash_field_present(row: dict, strong: bool) -> tuple[bool, list[str]]:
    hits = []
    for f in HASH_FIELDS:
        v = row.get(f)
        if v is None or v == "" or v == {} or v == []:
            continue
        blob = json.dumps(v, sort_keys=True).lower()
        if HEX64.search(blob):
            if strong:
                # require a hash attached to a path/ref object, not a bare digest string
                if f == "artifact_refs":
                    ok = any(isinstance(it, dict) and it.get("path") and HEX64.search(json.dumps(it).lower())
                             for it in (v if isinstance(v, list) else []))
                else:
                    ok = isinstance(v, (dict, list))
                if not ok:
                    continue
            hits.append(f)
    return bool(hits), hits


def hf14_readings(row: dict) -> dict:
    markers = acceptance_markers(row)
    vw, vwf = verdict_field_present(row)
    vs, vsf = verdict_strong_present(row)
    hw, hwf = hash_field_present(row, strong=False)
    hs, hsf = hash_field_present(row, strong=True)
    return {
        "markers": markers,
        "verdict_field_weak": vw, "verdict_field_weak_hits": vwf,
        "verdict_strong": vs, "verdict_strong_hits": vsf,
        "hash_field_weak": hw, "hash_field_weak_hits": hwf,
        "hash_strong": hs, "hash_strong_hits": hsf,
        "R1_literal_weak_fires": bool(markers) and not vw and not hw,
        "R2_strict_fires": bool(markers) and not vs and not hs,
        "R3_any_absence_fires": bool(markers) and (not vw or not hw),
    }


def run_detector(rows: list[dict]) -> dict:
    per_row = []
    for r in rows:
        d = hf14_readings(r)
        d["theorem_id"] = r.get("theorem_id")
        per_row.append(d)
    return {
        "rows": len(per_row),
        "marker_counts": {
            "status=accepted": sum("status=accepted" in d["markers"] for d in per_row),
            "validation_status=passed": sum("validation_status=passed" in d["markers"] for d in per_row),
            "supports_claim=true": sum("supports_claim=true" in d["markers"] for d in per_row),
            "any_marker": sum(bool(d["markers"]) for d in per_row),
        },
        "R1_literal_weak_fires": sum(d["R1_literal_weak_fires"] for d in per_row),
        "R2_strict_fires": sum(d["R2_strict_fires"] for d in per_row),
        "R3_any_absence_fires": sum(d["R3_any_absence_fires"] for d in per_row),
        "R1_firing_ids": [d["theorem_id"] for d in per_row if d["R1_literal_weak_fires"]],
        "R2_firing_ids": [d["theorem_id"] for d in per_row if d["R2_strict_fires"]],
        "R3_firing_ids": [d["theorem_id"] for d in per_row if d["R3_any_absence_fires"]],
        "per_row": per_row,
    }


# --- controls -----------------------------------------------------------------------------

def synthetic(overrides: dict) -> dict:
    row = {"theorem_id": "SYNTH", "status": "accepted", "supports_claim": True,
           "source_ids": ["SRC-001"], "statement_exact": "synthetic"}
    row.update(overrides)
    return row


def run_controls() -> dict:
    c = {}
    c["C1_positive_fires"] = hf14_readings(synthetic({}))["R1_literal_weak_fires"]
    h = "ab" * 32
    c["C2_negative_verdict_and_hash_clears"] = not hf14_readings(synthetic({
        "reviewer_verdict": {"reviewer": "worker-999", "verdict": "accept", "artifact_sha256": h},
        "artifact_sha256": h,
    }))["R1_literal_weak_fires"]
    c["C3_author_named_verdict_still_fires_strict"] = hf14_readings(synthetic({
        "reviewer_verdict": {"reviewer": AUTHOR_TOKEN, "verdict": "accept", "artifact_sha256": h},
        "artifact_sha256": h,
    }))["R2_strict_fires"]
    c["C4_supports_claim_only_fires"] = hf14_readings(synthetic({
        "status": "provisional", "supports_claim": True,
    }))["R1_literal_weak_fires"]
    c["C5_placeholder_verdict_without_hash_still_fires"] = hf14_readings(synthetic({
        "reviewer_verdict": "not_independently_reviewed",
    }))["R1_literal_weak_fires"]
    c["C6_placeholder_verdict_with_hash_clears_weak"] = not hf14_readings(synthetic({
        "reviewer_verdict": "not_independently_reviewed",
        "artifact_sha256": h,
    }))["R1_literal_weak_fires"]
    c["C7_hash_without_path_does_not_clear_strict"] = hf14_readings(synthetic({
        "reviewer_verdict": {"reviewer": "worker-999", "verdict": "accept"},
        "artifact_sha256": h,
    }))["R2_strict_fires"]
    return c


# --- main ---------------------------------------------------------------------------------

def probe(path: Path) -> dict:
    st = path.stat()
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "size": st.st_size,
        "mtime_iso": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
        "probed_at": now_iso(),
    }


def fail(msg: str) -> None:
    print(f"FAIL-CLOSED: {msg}", file=sys.stderr)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({"status": "FAIL_CLOSED", "reason": msg,
                                  "at": now_iso()}, indent=1) + "\n")
    raise SystemExit(2)


def main() -> int:
    started = now_iso()
    measured = {}
    for rel, want in PINS.items():
        got = sha256_file(ROOT / rel)
        measured[rel] = got
        if got != want:
            fail(f"{rel} measured {got[:16]} != pinned {want[:16]}")

    live_start = probe(LIVE_LEDGER)

    old_rows = load_jsonl(OLD_LEDGER)
    rev3_rows = load_jsonl(ARCHIVE_REV3)
    if len(old_rows) != 62 or len(rev3_rows) != 62:
        fail(f"row counts old={len(old_rows)} rev3={len(rev3_rows)} != 62")

    with open(L1_LEDGER) as f:
        l1_ids = {r["citation_id"] for r in csv.DictReader(f)}

    pre = run_detector(old_rows)
    post = run_detector(rev3_rows)
    controls = run_controls()

    # delta census pre -> rev3
    old_by = {r["theorem_id"]: r for r in old_rows}
    new_by = {r["theorem_id"]: r for r in rev3_rows}
    if set(old_by) != set(new_by):
        fail("theorem_id sets differ between revisions")
    field_change_counts: dict[str, int] = {}
    claim_bearing_changes: list[dict] = []
    per_row_delta = []
    for tid in sorted(old_by):
        o, n = old_by[tid], new_by[tid]
        changed = []
        for k in sorted(set(o) | set(n)):
            if o.get(k) != n.get(k):
                changed.append(k)
                field_change_counts[k] = field_change_counts.get(k, 0) + 1
                if k in CLAIM_BEARING_FIELDS:
                    claim_bearing_changes.append({"theorem_id": tid, "field": k,
                                                  "old": compact(o.get(k)), "new": compact(n.get(k))})
        if changed:
            per_row_delta.append({"theorem_id": tid, "changed_fields": changed,
                                  "old_status": o.get("status"), "new_status": n.get("status"),
                                  "old_supports_claim": o.get("supports_claim"),
                                  "new_supports_claim": n.get("supports_claim")})

    unexpected_field_changes = sorted(k for k in field_change_counts
                                      if k not in MUTABLE_FIELDS and k not in CLAIM_BEARING_FIELDS)

    # referential + class integrity retained
    ref_breaks = []
    class_moves = []
    for tid in sorted(new_by):
        o, n = old_by[tid], new_by[tid]
        if o.get("class_ids") != n.get("class_ids"):
            class_moves.append(tid)
        for s in n.get("source_ids") or []:
            if s not in l1_ids:
                ref_breaks.append({"theorem_id": tid, "source_id": s})

    # per-class census of exposure (pre) and post markers
    per_class = {}
    for rows, tag in ((old_rows, "pre"), (rev3_rows, "post")):
        for r in rows:
            key = ";".join(r.get("class_ids") or []) or "(unbound)"
            d = per_class.setdefault(key, {"rows": 0, "pre_fires_R1": 0, "post_fires_R1": 0,
                                           "post_markers": 0})
            if tag == "pre":
                d["pre_fires_R1"] += int(hf14_readings(r)["R1_literal_weak_fires"])
            else:
                d["rows"] += 1
                d["post_fires_R1"] += int(hf14_readings(r)["R1_literal_weak_fires"])
                d["post_markers"] += int(bool(acceptance_markers(r)))

    # residual / counterfactual reporting (decision-relevant, explicitly NOT the literal reading)
    near_miss_validation_passed = [r["theorem_id"] for r in rev3_rows
                                   if norm(r.get("validation_status")) in PASS_VALIDATION_STATUS]
    near_miss_verification_passed = [r["theorem_id"] for r in rev3_rows
                                     if norm(r.get("verification_status")) in PASS_VALIDATION_STATUS]
    acceptance_like_statuses = {}
    for r in rev3_rows:
        acceptance_like_statuses[norm(r.get("status"))] = acceptance_like_statuses.get(norm(r.get("status")), 0) + 1
    counterfactual_status_reading = sum(1 for r in rev3_rows
                                        if norm(r.get("status")) in ("included_unreviewed", "provisional")
                                        and not verdict_field_present(r)[0] and not hash_field_present(r, False)[0])

    # determinism control: re-run both detectors, compare canonical JSON
    deterministic = (json.dumps(run_detector(old_rows), sort_keys=True) == json.dumps(pre, sort_keys=True)
                     and json.dumps(run_detector(rev3_rows), sort_keys=True) == json.dumps(post, sort_keys=True))
    controls["C8_deterministic_rerun"] = deterministic

    # certified pins re-measured at end; drift voids the verdict
    end_hashes = {rel: sha256_file(ROOT / rel) for rel in PINS}
    pins_stable = end_hashes == measured

    # live ledger probed at end; observation only, never certified
    live_end = probe(LIVE_LEDGER)
    live = {"start": live_start, "end": live_end,
            "stable_during_run": live_start["sha256"] == live_end["sha256"]}
    if live["stable_during_run"]:
        try:
            live_rows = load_jsonl(LIVE_LEDGER)
            live["rows"] = len(live_rows)
            live["detector_state"] = {k: v for k, v in run_detector(live_rows).items() if k != "per_row"}
            live["equals_certified_rev3"] = live_end["sha256"] == REV3_SHA
            live["label"] = "observed_not_certified"
        except Exception as exc:  # noqa: BLE001
            live["parse_error"] = str(exc)
            live["label"] = "observed_not_certified_unparseable"
    else:
        live["label"] = "MOVING_TARGET_DURING_RUN__not_analyzed"

    repair_record = json.loads(REPAIR_RECORD.read_text())
    repair_reconcile = {
        "record_hf14_rows_closed": repair_record.get("hf14_rows_closed"),
        "measured_pre_status_accepted": pre["marker_counts"]["status=accepted"],
        "record_supports_claim_withdrawn": repair_record.get("supports_claim_withdrawn"),
        "measured_pre_supports_claim_true": pre["marker_counts"]["supports_claim=true"],
        "measured_pre_any_marker_union": pre["marker_counts"]["any_marker"],
        "note": "the union count is the HF-14 exposure count pre-repair (disjunctive detector); "
                "record's hf14_rows_closed=50 counts only the status=accepted arm",
    }

    core_ok = (all(controls.values()) and not claim_bearing_changes
               and not unexpected_field_changes and not ref_breaks and not class_moves)
    if not pins_stable:
        status = "VOIDED_MOVING_TARGET"
    elif post["R1_literal_weak_fires"] > 0:
        status = "STILL_EXPOSED"
    elif core_ok:
        status = "CONFIRMED_CLOSED"
    else:
        status = "INCONCLUSIVE"

    report = {
        "schema_version": "0.1",
        "artifact_type": "l0_hf14_postrepair_check",
        "node_id": "L0",
        "gate": "G-LIT",
        "actor": "worker-073",
        "reviewer": "worker-073",
        "task_id": "W073-L0-HF14-POSTREPAIR-01",
        "created_at": now_iso(),
        "started_at": started,
        "class_coverage": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                           "AF-WCC-SCALAR-SPH"],
        "class_binding_note": "all 62 L0 rows were censused per class_ids; 28 rows are unbound "
                              "(pre-existing BL-6), 8 rows carry two frozen classes (pre-existing BL-6)",
        "status": status,
        "certified_revision": {
            "path": str(ARCHIVE_REV3.relative_to(ROOT)),
            "sha256": REV3_SHA,
            "why_archive": "the live ledger moved from 3e3d3553 to a1674f09 at 00:35:19+08:00 "
                           "between this task's first and second runs; the archive copy is "
                           "hash-identical to the rev-3 revision the lead's repair record "
                           "declares as after_sha256, so the verdict is bound to it",
            "baseline_sha256": OLD_SHA,
        },
        "moving_target_observation": {
            "live_at_first_run_00_33": {"sha256": REV3_SHA, "probe_evidence":
                                        "run_stdout.txt (first run passed the pin check and completed)"},
            "live_at_00_35_2x": live_start,
            "session_second_run": "FAIL_CLOSED at 00:35:2x: measured a1674f09 != pin 3e3d3553",
            "note": "reported as clock-stamped observation; no verdict is bound to the live file",
        },
        "independence": {
            "detector_source": "evaluation_rubric.yaml:243-252 (read as text)",
            "own_implementation": True,
            "imported_audit_lib": False,
            "read_leads_repair_tool": False,
            "prior_work_reconciled": ["artifacts/literature/reviews/L0-rev3-hf14-repair.json",
                                      "reviews/L0-review-lead-audit-r2.json"],
        },
        "pins": {rel: {"sha256": h, "matches_hardcoded_pin": True} for rel, h in measured.items()},
        "pins_stable_during_run": pins_stable,
        "end_hashes": end_hashes,
        "live_ledger_probe": live,
        "method": {
            "readings": {
                "R1_literal_weak": "any acceptance marker AND no non-placeholder verdict field AND no hash field",
                "R2_strict": "any acceptance marker AND no identity-bearing independent verdict AND no path-anchored sha256",
                "R3_any_absence": "any acceptance marker AND (no verdict field OR no hash field)",
            },
            "acceptance_markers": ["status==accepted", "validation_status==passed", "supports_claim is True"],
            "verdict_fields": list(VERDICT_FIELDS),
            "hash_fields": list(HASH_FIELDS),
            "claim_bearing_fields": list(CLAIM_BEARING_FIELDS),
            "mutable_fields": list(MUTABLE_FIELDS),
        },
        "pre_repair": {k: v for k, v in pre.items() if k != "per_row"},
        "post_repair_rev3": {k: v for k, v in post.items() if k != "per_row"},
        "per_class_census": per_class,
        "delta_census": {
            "rows_changed": len(per_row_delta),
            "field_change_counts": field_change_counts,
            "claim_bearing_changes": claim_bearing_changes,
            "unexpected_field_changes": unexpected_field_changes,
            "per_row_delta": per_row_delta,
        },
        "integrity": {
            "l1_source_ids_resolved": not ref_breaks,
            "ref_breaks": ref_breaks,
            "class_ids_moved": class_moves,
        },
        "controls": controls,
        "residual_risk": {
            "literal_markers_remaining": post["marker_counts"]["any_marker"],
            "validation_status_passed_rows": near_miss_validation_passed,
            "verification_status_passed_rows": near_miss_verification_passed,
            "status_distribution_rev3": acceptance_like_statuses,
            "counterfactual_if_included_unreviewed_or_provisional_counts_as_acceptance":
                counterfactual_status_reading,
            "counterfactual_note": "not the detector's literal text; reported so a lead can rule on "
                                   "whether renamed acceptance vocabulary still counts as self-certification",
            "pre_existing_class_binding_defects_not_introduced_by_rev3":
                "28 unbound rows, 8 rows with two frozen classes (BL-6, open)",
        },
        "repair_record_reconciliation": repair_reconcile,
        "verdict_scope": {
            "covers": ["HF-14 predicate state at certified rev-3 3e3d3553",
                       "rev-3 delta content preservation",
                       "L0->L1 source referential integrity", "class_ids preservation"],
            "does_not_cover": ["full L0 review", "class-binding adjudication (BL-6)",
                               "L1 locator resolvability (BL-4)", "the post-00:35 live revision",
                               "gate verdict"],
            "counts_toward_gate_accept": False,
        },
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    RAW.joinpath("live_probe.json").write_text(json.dumps({"start": live_start, "end": live_end,
                                                           "stable": live["stable_during_run"]},
                                                          indent=1) + "\n")
    REPORT.write_text(json.dumps(report, indent=1, sort_keys=False, ensure_ascii=False) + "\n")

    print(f"status={status} certified_rev3={REV3_SHA[:12]}")
    print(f"pre  R1={pre['R1_literal_weak_fires']} R2={pre['R2_strict_fires']} R3={pre['R3_any_absence_fires']} markers={pre['marker_counts']}")
    print(f"rev3 R1={post['R1_literal_weak_fires']} R2={post['R2_strict_fires']} R3={post['R3_any_absence_fires']} markers={post['marker_counts']}")
    print(f"controls={controls}")
    print(f"delta rows_changed={len(per_row_delta)} claim_bearing_changes={len(claim_bearing_changes)} unexpected={unexpected_field_changes}")
    print(f"live stable={live['stable_during_run']} label={live.get('label')} sha={live_end['sha256'][:12]}")
    print(f"report={REPORT.relative_to(ROOT)}")
    return 0 if status == "CONFIRMED_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
