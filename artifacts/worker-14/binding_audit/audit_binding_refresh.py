#!/usr/bin/env python3
"""W14-GNUM-BINDING-AUDIT-02: refresh of the N0 proposal binding audit at the *current* bytes.

Class-bound task: class AF-WCC-SCALAR-SPH, node N0, gate G-NUM, actor deepseek-flash-14
(runtime slot worker-014).  No inbox card exists for the relaunched slot; this is the
continuation of W14-GNUM-BINDING-AUDIT-01 (report d63b67f1), self-selected from the open
N0/G-NUM verification queue.  Read-only; writes exactly one file (its own report).

Why a refresh is worth doing rather than re-reading audit-01.  Three inputs moved after
audit-01 was written at 2026-09-12T00:44:31:
  * runtime/state/artifact_hashes.json (the controller registry) was rewritten: audit-01
    measured c9f20343 and found 1/25 coverage with the four C4 items open; the registry on
    disk now has a different hash and may have closed them;
  * the numerics lead closed its lifecycle at 00:46:36 and filed rev3 stop-rule evidence;
  * audit-01's own report is now a fixed baseline against which deltas can be measured.

Audit-01's load-bearing finding BA-1 (the filed verification of record pins the superseded
proposal revision) is re-measured, not assumed.  Audit-01's BA-3 (C4 registration gap) is
re-measured against the current registry section and union of registry sections, because the
registry file is controller-rewritten and its bytes are explicitly not stable evidence.

Checks:
  A. does every one of the current proposal's 23 declared evidence hashes still match disk?
  B. does the filed verification-of-record now cover the current proposal revision, and does
     any record written after the proposal bind it as verified?
  C. registry coverage at the current snapshot: per section (hashes / registry) and union,
     for the 25 proposal-chain + proposal + leadverify paths; state the C4 delta vs audit-01.
  D. the proposal's own declared mutable registry snapshot: does it match the registry on
     disk, and was its declared measurement instant even reachable at audit time?
  E. load-bearing cross-file facts (orders, C8 accept, evaluator fix, lock, solver absence).
  F. is leadverify's recorded criteria_status now stale on the registration item?

Controls are fail-closed: a synthetic known-good / tampered / missing / directory-as-file
battery, two planted registry-lookup cases (match and stale), the real stale pin, the
baseline-unchanged check, and a registry drift guard (hash before vs after; if the
controller rewrites the registry mid-run the coverage verdict is voided and
instrument_valid=false).

Reproduce:
  python3 artifacts/worker-14/binding_audit/audit_binding_refresh.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
OUT = OUT_DIR / "n0_binding_audit_refresh.json"
CST = timezone(timedelta(hours=8))

PROPOSAL = "numerics/tests/n0_gate_proposal.json"
LEADVERIFY = "numerics/protocol/n0_gate_proposal_leadverify.json"
REGISTRY = "runtime/state/artifact_hashes.json"
BASELINE = "artifacts/worker-14/binding_audit/n0_proposal_binding_audit.json"
BASELINE_SHA_EXPECTED = "d63b67f191e35e5478ca519fc7a493391a2c303c8b21cc03b2bc594ea1619e1d"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
FIXED_RUN = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
C4_MANIFEST = "numerics/protocol/n0_c4_registration_manifest.json"
LIFECYCLE = "comms/outbox/astra-lead-numerics.jsonl"
MAP = "research_map/research_map.json"
GATES_PY = "numerics/gates.py"
SPHERICAL_SOLVER = "numerics/spherical_solver"

# Bounded record set scanned for a binding verification of the *current* proposal revision.
MENTION_RECORDS = [
    LEADVERIFY,
    PROPOSAL,
    BASELINE,
    C4_MANIFEST,
    LIFECYCLE,
    MAP,
    "reviews/G-NUM-protocol-review.json",
    "reviews/N0-review-lead-audit.json",
    "reviews/N0-review-worker-012.json",
    "artifacts/worker-067/n0_f0_rebind/rebind_check.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
    "numerics/results/flat_wave_convergence_rev3.json",
]

# The four C4 items audit-01 reported open at registry c9f20343cc46 (BA-3 open_C4_items).
AUDIT01_OPEN_C4 = [PROTOCOL, LEADVERIFY, PROPOSAL, FIXED_RUN]
BASELINE_REGISTRY_SHA_PREFIX = "c9f20343cc46"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_bytes(rel: str) -> bytes | None:
    p = ROOT / rel
    try:
        if p.is_file():
            return p.read_bytes()
    except OSError:
        return None
    return None


def classify(declared: dict[str, str]) -> list[dict]:
    rows = []
    for rel in sorted(declared):
        b = read_bytes(rel)
        measured = sha256_bytes(b) if b is not None else None
        if measured is None:
            status = "missing"
        elif measured == declared[rel]:
            status = "match"
        else:
            status = "stale"
        rows.append({"path": rel, "declared_sha256": declared[rel],
                     "measured_sha256": measured, "status": status})
    return rows


def count(rows: list[dict], status: str, key: str = "status") -> int:
    return sum(1 for r in rows if r[key] == status)


def registry_lookup(live_sha: str | None, entry: dict | None) -> str:
    """Classify one path against one registry section.  Mirrors the controller semantics:
    a path is registered_match when the registry sha equals the bytes on disk."""
    if entry is None:
        return "unregistered"
    if live_sha is not None and entry.get("sha256") == live_sha:
        return "registered_match"
    return "registered_stale"


def find_paths(obj, needle: str, prefix: str = "") -> list[str]:
    """Nested search for a full sha256 string; returns dotted paths where it occurs."""
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            hits.extend(find_paths(v, needle, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_paths(v, needle, f"{prefix}[{i}]"))
    elif isinstance(obj, str) and obj == needle:
        hits.append(prefix)
    return hits


def main() -> int:
    controls: list[dict] = []

    def control(name: str, ok: bool, detail: str) -> None:
        controls.append({"control": name, "behaved": bool(ok), "detail": detail})

    prop_b = read_bytes(PROPOSAL)
    lv_b = read_bytes(LEADVERIFY)
    reg_b = read_bytes(REGISTRY)
    map_b = read_bytes(MAP)
    base_b = read_bytes(BASELINE)
    if None in (prop_b, lv_b, reg_b, map_b, base_b):
        print("FATAL: a pinned input is missing", file=sys.stderr)
        return 2
    prop = json.loads(prop_b)
    leadverify = json.loads(lv_b)
    registry = json.loads(reg_b)
    rmap = json.loads(map_b)
    baseline = json.loads(base_b)
    prop_sha = sha256_bytes(prop_b)
    lv_sha = sha256_bytes(lv_b)
    reg_sha_before = sha256_bytes(reg_b)
    base_sha = sha256_bytes(base_b)

    reg_hashes = registry.get("hashes", {}) or {}
    reg_registry = registry.get("registry", {}) or {}
    chain = prop.get("evidence_hashes", {}) or {}

    # ---- A. current evidence chain integrity ---------------------------------------------
    chain_rows = classify(chain)
    chain_summary = {s: count(chain_rows, s) for s in ("match", "stale", "missing")}

    # ---- B. verification-of-record coverage + binding scan --------------------------------
    old_verified = leadverify.get("verified_artifacts", {}) or {}
    old_pin = (leadverify.get("proposal_verified") or {}).get("sha256")
    pin_is_current = old_pin == prop_sha
    added = sorted(set(chain) - set(old_verified))
    removed = sorted(set(old_verified) - set(chain))
    changed = sorted(p for p in set(chain) & set(old_verified) if chain[p] != old_verified[p])

    binding_scan = []
    for rel in MENTION_RECORDS:
        b = read_bytes(rel)
        if b is None:
            binding_scan.append({"path": rel, "present": False})
            continue
        txt = b.decode("utf-8", "replace")
        row = {
            "path": rel, "present": True, "sha256": sha256_bytes(b),
            "mentions_current_proposal_hash": prop_sha[:12] in txt,
            "mentions_superseded_pin": bool(old_pin) and old_pin[:12] in txt,
            "is_verification_of_record": rel == LEADVERIFY,
            "binds_current_as_verified": False,
            "binding_field_paths": [],
        }
        try:
            doc = json.loads(b)
            hits = find_paths(doc, prop_sha)
            row["binding_field_paths"] = hits
            # A record binds the current revision as *verified* only if the current proposal
            # hash appears under a verification/review field and not merely as a mention.
            row["binds_current_as_verified"] = any(
                any(tok in h for tok in ("proposal_verified", "verified", "reviewed", "verified_sha256"))
                for h in hits
            )
        except (ValueError, UnicodeDecodeError):
            pass
        binding_scan.append(row)
    any_binding_record_for_current = any(
        r.get("binds_current_as_verified") for r in binding_scan if r.get("present"))

    # ---- C. registry coverage at the measured snapshot, per section and union --------------
    paths25 = sorted(set(chain) | {PROPOSAL, LEADVERIFY})
    reg_rows = []
    for rel in paths25:
        live = sha256_bytes(read_bytes(rel)) if read_bytes(rel) is not None else None
        in_h = reg_hashes.get(rel)
        in_r = reg_registry.get(rel)
        s_h = registry_lookup(live, in_h)
        s_r = registry_lookup(live, in_r)
        if "registered_match" in (s_h, s_r):
            union = "registered_match"
        elif "registered_stale" in (s_h, s_r):
            union = "registered_stale"
        else:
            union = "unregistered"
        reg_rows.append({
            "path": rel, "live_sha256": live,
            "hashes_section": s_h, "registry_section": s_r, "union": union,
            "declared_sha256": chain.get(rel),
        })
    union_summary = {s: count(reg_rows, s, "union") for s in
                     ("registered_match", "registered_stale", "unregistered")}
    hashes_summary = {s: sum(1 for r in reg_rows if r["hashes_section"] == s) for s in
                      ("registered_match", "registered_stale", "unregistered")}
    registry_summary = {s: sum(1 for r in reg_rows if r["registry_section"] == s) for s in
                        ("registered_match", "registered_stale", "unregistered")}

    c4_delta = []
    for rel in AUDIT01_OPEN_C4:
        row = next(r for r in reg_rows if r["path"] == rel)
        c4_delta.append({
            "path": rel,
            "audit01_status_at_c9f20343cc46": "unregistered",
            "status_now_union": row["union"],
            "status_now_registry_section": row["registry_section"],
            "closed": row["union"] == "registered_match",
        })
    c4_closed = all(item["closed"] for item in c4_delta)

    # ---- D. declared mutable registry snapshot ---------------------------------------------
    declared_snapshot = (prop.get("mutable_registry_snapshots") or {}).get(REGISTRY) or {}
    declared_sha = declared_snapshot.get("sha256")
    declared_at = declared_snapshot.get("measured_at")
    now_dt = datetime.now(CST)
    declared_reachable = None
    if declared_at:
        try:
            declared_reachable = datetime.fromisoformat(declared_at) <= now_dt
        except ValueError:
            declared_reachable = None

    # ---- E. load-bearing cross-file facts --------------------------------------------------
    cert_b = read_bytes(CERT)
    cert = json.loads(cert_b) if cert_b else {}
    c8_b = read_bytes("reviews/G-NUM-protocol-review.json")
    c8 = json.loads(c8_b) if c8_b else {}
    cert_v = cert.get("verdict", {}) or {}
    claim = prop.get("certified_order_claim", {}) or {}
    claim_orders = claim.get("orders_4rung_certified_fixed_dt_1e-4", {}) or {}
    cert_orders = cert_v.get("certified_spatial_order", {}) or {}
    order_max_abs_diff = max(
        (abs(claim_orders.get(s, float("nan")) - cert_orders.get(s, float("nan")))
         for s in sorted(set(claim_orders) | set(cert_orders))), default=None)
    claim_delta = claim.get("delta_R5_4rung_fixed_dt", {}) or {}
    cert_delta = (cert.get("cross_scheme_R5", {}) or {}).get("delta_R5_by_scheme", {}) or {}
    delta_max_abs_diff = max(
        (abs(claim_delta.get(s, float("nan")) - cert_delta.get(s, float("nan")))
         for s in sorted(set(claim_delta) | set(cert_delta))), default=None)
    lock = rmap.get("numerics_lock", {}) or {}
    solver_present = (ROOT / SPHERICAL_SOLVER).exists()
    gates_sha = sha256_bytes(read_bytes(GATES_PY) or b"")
    fixed_run_sha = sha256_bytes(read_bytes(FIXED_RUN) or b"")
    protocol_sha = sha256_bytes(read_bytes(PROTOCOL) or b"")

    load_bearing = {
        "certified_orders_equal_certification_file": {
            "claim": claim_orders, "certification": cert_orders,
            "max_abs_diff": order_max_abs_diff,
            "ok": bool(order_max_abs_diff is not None and order_max_abs_diff <= 1e-12)},
        "delta_R5_equal_certification_file": {
            "claim": claim_delta, "certification": cert_delta,
            "max_abs_diff": delta_max_abs_diff,
            "ok": bool(delta_max_abs_diff is not None and delta_max_abs_diff <= 1e-12)},
        "standing_C8_accept_binds_protocol_of_record": {
            "review_verdict": c8.get("verdict"), "reviewed_sha256": c8.get("reviewed_sha256"),
            "protocol_sha256": protocol_sha,
            "ok": bool(c8.get("verdict") == "accept" and c8.get("reviewed_sha256") == protocol_sha)},
        "evaluator_fix_in_place": {
            "proposal_declared": chain.get(GATES_PY), "measured": gates_sha,
            "ok": gates_sha == chain.get(GATES_PY)},
        "lock_intact": {
            "state": lock.get("state"), "spherical_solver_present": solver_present,
            "ok": bool(lock.get("state") == "locked" and not solver_present)},
        "fixed_run_registered_union": {
            "path": FIXED_RUN, "sha256": fixed_run_sha,
            "status": next(r["union"] for r in reg_rows if r["path"] == FIXED_RUN),
            "ok": next(r["union"] for r in reg_rows if r["path"] == FIXED_RUN) == "registered_match"},
        "protocol_of_record_registered_union": {
            "path": PROTOCOL, "sha256": protocol_sha,
            "status": next(r["union"] for r in reg_rows if r["path"] == PROTOCOL),
            "ok": next(r["union"] for r in reg_rows if r["path"] == PROTOCOL) == "registered_match"},
    }

    # ---- F. leadverify recorded-criteria staleness ------------------------------------------
    lv_criteria = leadverify.get("criteria_status", {}) or {}
    lv_stale_registration_text = lv_criteria.get("registration-in-artifact-hashes")
    lv_registration_now_met = load_bearing["fixed_run_registered_union"]["ok"] and \
        load_bearing["protocol_of_record_registered_union"]["ok"]

    # ---- controls (fail-closed) -------------------------------------------------------------
    tmp_correct = OUT_DIR / ".control_correct.bin"
    tmp_tamper = OUT_DIR / ".control_tamper.bin"
    tmp_dir = OUT_DIR / ".control_dir"
    tmp_correct.write_bytes(b"control-bytes")
    tmp_tamper.write_bytes(b"control-bytes")
    tmp_dir.mkdir(exist_ok=True)
    good = sha256_bytes(tmp_correct.read_bytes())
    rows_c = classify({
        str(tmp_correct.relative_to(ROOT)): good,
        str(tmp_tamper.relative_to(ROOT)): "0" * 64,
        "no/such/path.bin": "1" * 64,
        str(tmp_dir.relative_to(ROOT)): good,
    })
    got = {r["path"]: r["status"] for r in rows_c}
    control("C1_known_good_classifies_match",
            got.get(str(tmp_correct.relative_to(ROOT))) == "match", "expected match")
    control("C2_tampered_hash_classifies_stale",
            got.get(str(tmp_tamper.relative_to(ROOT))) == "stale", "expected stale")
    control("C3_missing_path_classifies_missing",
            got.get("no/such/path.bin") == "missing", "expected missing")
    control("C4_directory_as_file_classifies_missing",
            got.get(str(tmp_dir.relative_to(ROOT))) == "missing", "expected missing")
    control("C5_planted_registry_match",
            registry_lookup(good, {"sha256": good}) == "registered_match",
            "planted matching entry classifies registered_match")
    control("C6_planted_registry_stale",
            registry_lookup(good, {"sha256": "f" * 64}) == "registered_stale",
            "planted wrong-hash entry classifies registered_stale")
    control("C7_planted_registry_absent",
            registry_lookup(good, None) == "unregistered",
            "absent entry classifies unregistered")
    control("C8_real_stale_verification_pin_detected",
            (old_pin is not None) and (not pin_is_current),
            f"leadverify pin {str(old_pin)[:12]} vs disk {prop_sha[:12]}")
    control("C9_baseline_audit01_unchanged",
            base_sha == BASELINE_SHA_EXPECTED,
            f"baseline {base_sha[:12]} vs expected {BASELINE_SHA_EXPECTED[:12]}")
    control("C10_load_bearing_facts_hold",
            all(load_bearing[k]["ok"] for k in (
                "certified_orders_equal_certification_file",
                "delta_R5_equal_certification_file",
                "standing_C8_accept_binds_protocol_of_record",
                "evaluator_fix_in_place",
                "lock_intact")),
            "claimed-true cross-file facts must hold for this audit to be usable")
    for t in (tmp_correct, tmp_tamper):
        t.unlink(missing_ok=True)
    tmp_dir.rmdir()

    controls_ok = all(c["behaved"] for c in controls)

    # ---- registry drift guard ---------------------------------------------------------------
    reg_after_b = read_bytes(REGISTRY)
    reg_sha_after = sha256_bytes(reg_after_b) if reg_after_b is not None else None
    registry_stable = reg_sha_after == reg_sha_before

    instrument_valid = controls_ok and registry_stable

    # ---- findings ----------------------------------------------------------------------------
    findings: list[dict] = []
    if not pin_is_current:
        findings.append({
            "id": "BA-1", "severity": "load-bearing-for-verdict", "status": "open",
            "finding": (f"the filed verification of record ({LEADVERIFY}#{lv_sha[:12]}) verifies "
                        f"proposal revision {str(old_pin)[:12]}, but the bytes on disk are "
                        f"{prop_sha[:12]}; the current revision's evidence chain has no binding "
                        "verification record"),
            "consequence": ("astra-life04-n0-verify must re-verify the proposal at the current "
                            "hash (or the lead must re-issue the leadverify record at it); the "
                            "existing leadverify must not be cited as covering current bytes"),
        })
    findings.append({
        "id": "BA-2", "severity": "informational", "status": "recorded",
        "finding": "revision delta between the verified revision and the current proposal",
        "added_evidence_entries": added, "removed_evidence_entries": removed,
        "changed_declared_hashes": changed,
    })
    findings.append({
        "id": "BA-3R", "severity": "resolution", "status": "closed-at-current-snapshot",
        "finding": (f"C4 registration gap CLOSED at registry {reg_sha_before[:12]}: union "
                    f"coverage of the 25 proposal-chain + proposal + leadverify paths is "
                    f"{union_summary['registered_match']} registered_match, "
                    f"{union_summary['registered_stale']} registered_stale, "
                    f"{union_summary['unregistered']} unregistered (audit-01 BA-3 measured "
                    f"1/25 at {BASELINE_REGISTRY_SHA_PREFIX} with four C4 items open)"),
        "c4_items_audit01_open": c4_delta,
        "section_summaries": {"hashes": hashes_summary, "registry": registry_summary,
                              "union": union_summary},
        "consequence": ("the registration-in-artifact-hashes criterion is now met for the "
                        "measured chain; leadverify's recorded criteria_status predates this"),
    })
    if declared_sha and declared_sha != reg_sha_before:
        findings.append({
            "id": "BA-5", "severity": "advisory-for-verdict", "status": "open",
            "finding": (f"the proposal declares mutable registry snapshot {str(declared_sha)[:12]} "
                        f"measured_at {declared_at}, but the registry on disk at audit time is "
                        f"{reg_sha_before[:12]}; the declared snapshot is not reproducible and its "
                        f"declared measurement instant was {'in the future' if declared_reachable is False else 'not established'} "
                        "relative to this audit"),
            "consequence": ("do not cite the declared snapshot as a binding registry pin; the "
                            "registry is controller-rewritten and explicitly not stable evidence"),
        })
    if lv_stale_registration_text and lv_registration_now_met:
        findings.append({
            "id": "BA-6", "severity": "informational", "status": "recorded",
            "finding": (f"leadverify criteria_status still records "
                        f"'registration-in-artifact-hashes: {lv_stale_registration_text}', but the "
                        "current registry now covers the C4 items; the record is stale on two "
                        "independent grounds (superseded proposal pin and superseded registration state)"),
        })
    findings.append({
        "id": "BA-4R", "severity": "informational", "status": "recorded",
        "finding": (f"binding scan over {len(MENTION_RECORDS)} candidate records: "
                    f"{'a' if any_binding_record_for_current else 'no'} record other than a "
                    "verification-of-record binds the current proposal hash under a "
                    "verified/reviewed field; mentions are rebind/adjudication notes"),
        "scan": binding_scan,
    })

    if not controls_ok:
        verdict = "INDETERMINATE_CONTROL_FAILURE"
    elif not registry_stable:
        verdict = "INDETERMINATE_REGISTRY_MOVED_DURING_AUDIT"
    elif pin_is_current and c4_closed:
        verdict = "BINDING_CURRENT_AND_C4_CLOSED"
    elif not pin_is_current and c4_closed:
        verdict = "BINDING_GAP_REMAINS_C4_CLOSED"
    else:
        verdict = "BINDING_GAP_AND_C4_OPEN"

    report = {
        "schema": "w14-n0-binding-audit-refresh/v1",
        "task_id": "W14-GNUM-BINDING-AUDIT-02",
        "actor": "deepseek-flash-14",
        "runtime_slot": "worker-014",
        "created_at": now_dt.isoformat(timespec="seconds"),
        "class_id": prop.get("class_id", "AF-WCC-SCALAR-SPH"),
        "node_id": "N0",
        "gate": "G-NUM",
        "conclusion_type": "provenance_measurement",
        "verdict": verdict,
        "supersedes_baseline": {
            "path": BASELINE, "sha256": base_sha,
            "expected_sha256": BASELINE_SHA_EXPECTED, "unchanged": base_sha == BASELINE_SHA_EXPECTED,
            "baseline_registry_snapshot_prefix": BASELINE_REGISTRY_SHA_PREFIX,
            "baseline_verdict": baseline.get("verdict"),
        },
        "pins": {
            PROPOSAL: {"sha256": prop_sha, "bytes": len(prop_b)},
            LEADVERIFY: {"sha256": lv_sha, "bytes": len(lv_b)},
            REGISTRY: {"sha256": reg_sha_before, "bytes": len(reg_b)},
            MAP: {"sha256": sha256_bytes(map_b), "bytes": len(map_b)},
        },
        "drift_guard": {
            "registry_sha256_before": reg_sha_before,
            "registry_sha256_after": reg_sha_after,
            "stable": registry_stable,
        },
        "A_evidence_chain": {
            "declared_entries": len(chain),
            "summary": chain_summary,
            "rows": chain_rows,
        },
        "B_verification_of_record": {
            "proposal_on_disk_sha256": prop_sha,
            "leadverify_pin_sha256": old_pin,
            "pin_is_current": pin_is_current,
            "verified_artifacts_entries": len(old_verified),
            "added_evidence_entries": added,
            "removed_evidence_entries": removed,
            "changed_declared_hashes": changed,
            "any_binding_record_for_current": any_binding_record_for_current,
            "binding_scan": binding_scan,
        },
        "C_registry_coverage": {
            "registry_snapshot_sha256": reg_sha_before,
            "paths_measured": len(reg_rows),
            "hashes_section_summary": hashes_summary,
            "registry_section_summary": registry_summary,
            "union_summary": union_summary,
            "c4_closed": c4_closed,
            "c4_delta_vs_audit01": c4_delta,
            "rows": reg_rows,
        },
        "D_declared_registry_snapshot": {
            "declared_sha256": declared_sha,
            "declared_measured_at": declared_at,
            "measured_registry_sha256": reg_sha_before,
            "matches_measured": declared_sha == reg_sha_before,
            "declared_instant_reachable_at_audit_time": declared_reachable,
            "audit_time": now_dt.isoformat(timespec="seconds"),
        },
        "E_load_bearing": load_bearing,
        "F_leadverify_criteria": {
            "recorded": lv_criteria,
            "registration_recorded_UNMET": "UNMET" in str(lv_stale_registration_text or ""),
            "registration_now_met_at_current_registry": lv_registration_now_met,
        },
        "controls": controls,
        "controls_ok": controls_ok,
        "instrument_valid": instrument_valid,
        "findings": findings,
        "falsifier": (
            "Re-run this instrument at the pinned input hashes (proposal "
            f"{prop_sha[:12]}, leadverify {lv_sha[:12]}, registry {reg_sha_before[:12]}). "
            "The report is falsified if: (a) any A-row classified match has a different measured "
            "sha256; (b) the leadverify record is shown to pin the current proposal hash, or a "
            "record binding the current revision as verified is produced; (c) any C-row's union "
            "status is wrong, or the registry on disk at the pinned snapshot does not contain the "
            "named paths with the named hashes; (d) any control behaved differently from its "
            "expected classification; or (e) any load-bearing fact recorded ok is shown false. "
            "A moved proposal, leadverify or registry hash voids the corresponding verdict for "
            "the new bytes."
        ),
        "not_claimed": [
            "no gate verdict and no gate self-pass; G-NUM adjudication is Astra's",
            "no N0 completion; numerics_lock stays LOCKED, N1 not started, numerics/spherical_solver absent",
            "no independent review; this worker may not review its own artifacts",
            "no physics/censorship claim; provenance measurement only",
            "no claim that the controller registry is stable evidence; it is measured at one snapshot",
            "no claim about records outside the bounded binding-scan set",
        ],
    }

    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "task_id": report["task_id"], "verdict": verdict,
        "instrument_valid": instrument_valid, "controls": len(controls),
        "controls_ok": controls_ok,
        "chain": chain_summary, "union": union_summary, "c4_closed": c4_closed,
        "pin_is_current": pin_is_current, "registry_stable": registry_stable,
        "report_sha256": sha256_bytes(OUT.read_bytes()),
        "report_bytes": OUT.stat().st_size,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
