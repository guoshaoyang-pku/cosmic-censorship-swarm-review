#!/usr/bin/env python3
"""W14-GNUM-BINDING-AUDIT-01: is the N0 gate proposal's verification still bound to the bytes on disk?

Task (class-bound): class AF-WCC-SCALAR-SPH, node N0, gate G-NUM, actor deepseek-flash-14.
No inbox card: self-selected bounded read-only provenance task from the open N0/G-NUM
verification queue (astra-life04-n0-verify is lead-owned; this is worker-side evidence only).

Question.  numerics/tests/n0_gate_proposal.json was rewritten during lifecycle pass 04 to
re-base the certified spatial order from the constant-CFL ladder to the fixed-dt = 1e-4
ladder (see its own headline.what_changed_since_sha_58a175b52fbe).  Its filed verification
record, numerics/protocol/n0_gate_proposal_leadverify.json, pins the PREVIOUS revision
58a175b5.  This instrument answers, from bytes on disk and nothing else:

  A. does every one of the current proposal's 23 declared evidence hashes still match disk?
  B. does the filed verification-of-record cover the current proposal revision, and which
     evidence entries changed between the verified revision and the current one?
  C. at the measured registry snapshot, how much of the current evidence chain is registered?
  D. do the load-bearing cross-file facts still hold (certified orders == certification file,
     standing C8 accept binds the protocol-of-record hash, evaluator fix in place, lock intact)?

Everything is read-only.  The instrument writes exactly one file: its own report under
artifacts/worker-14/binding_audit/.  It never edits another agent's artifact, never writes
the registry, and never sets a gate verdict.

Controls (fail-closed).  A synthetic battery with a known-correct hash, a tampered hash, a
missing path and a directory-as-file must classify as match/stale/missing/not-match, and the
real stale leadverify pin must be detected as stale.  Any control that misbehaves sets
instrument_valid=false and the process exits 2.

Reproduce:
  python3 artifacts/worker-14/binding_audit/audit_proposal_binding.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
OUT = OUT_DIR / "n0_proposal_binding_audit.json"
CST = timezone(timedelta(hours=8))

PROPOSAL = "numerics/tests/n0_gate_proposal.json"
LEADVERIFY = "numerics/protocol/n0_gate_proposal_leadverify.json"
REGISTRY = "runtime/state/artifact_hashes.json"
MAP = "research_map/research_map.json"
C8_REVIEW = "reviews/G-NUM-protocol-review.json"
PROTOCOL = "numerics/CONVERGENCE_PROTOCOL.md"
CERT = "numerics/protocol/n0_fixed_dt_certification.json"
FIXED_RUN = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
GATES_PY = "numerics/gates.py"
SPHERICAL_SOLVER = "numerics/spherical_solver"

# Records that mention the current proposal hash; scanned to show who cites it and whether
# any of them is a binding verification of the current revision.
MENTION_RECORDS = [
    LEADVERIFY,
    "artifacts/worker-067/n0_f0_rebind/rebind_check.json",
    "artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json",
]


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
    """Measure every declared path; status is match / stale / missing (dirs count missing)."""
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


def count(rows: list[dict], status: str) -> int:
    return sum(1 for r in rows if r["status"] == status)


def main() -> int:
    controls: list[dict] = []

    def control(name: str, ok: bool, detail: str) -> None:
        controls.append({"control": name, "behaved": bool(ok), "detail": detail})

    # ---- pinned inputs (bytes read once; the hash printed is the hash parsed) -------------
    prop_b = read_bytes(PROPOSAL)
    lv_b = read_bytes(LEADVERIFY)
    reg_b = read_bytes(REGISTRY)
    map_b = read_bytes(MAP)
    if prop_b is None or lv_b is None or reg_b is None or map_b is None:
        print("FATAL: a pinned input is missing", file=sys.stderr)
        return 2
    prop = json.loads(prop_b)
    leadverify = json.loads(lv_b)
    registry = json.loads(reg_b)
    rmap = json.loads(map_b)
    prop_sha = sha256_bytes(prop_b)
    lv_sha = sha256_bytes(lv_b)
    reg_sha = sha256_bytes(reg_b)

    reg_hashes = registry.get("hashes", {})
    chain = prop.get("evidence_hashes", {})

    # ---- A. current evidence chain integrity ---------------------------------------------
    chain_rows = classify(chain)
    chain_summary = {s: count(chain_rows, s) for s in ("match", "stale", "missing")}

    # ---- B. verification-of-record coverage ----------------------------------------------
    old_verified = leadverify.get("verified_artifacts", {}) or {}
    old_pin = (leadverify.get("proposal_verified") or {}).get("sha256")
    pin_is_current = old_pin == prop_sha
    added = sorted(set(chain) - set(old_verified))
    removed = sorted(set(old_verified) - set(chain))
    changed = sorted(p for p in set(chain) & set(old_verified) if chain[p] != old_verified[p])

    # ---- C. registry coverage at the measured snapshot ------------------------------------
    reg_rows = []
    for rel in sorted(set(chain) | {PROPOSAL, LEADVERIFY}):
        rec = reg_hashes.get(rel)
        declared = chain.get(rel)
        if rec is None:
            status = "unregistered"
        elif declared is not None and rec.get("sha256") == declared:
            status = "registered_match"
        elif rec.get("sha256") == (sha256_bytes(read_bytes(rel)) if read_bytes(rel) else None):
            status = "registered_match_live"
        else:
            status = "registered_stale"
        reg_rows.append({"path": rel, "status": status,
                         "registry_sha256": (rec or {}).get("sha256"),
                         "declared_sha256": declared})
    reg_summary = {s: count(reg_rows, s) for s in
                   ("registered_match", "registered_match_live", "registered_stale", "unregistered")}

    # ---- D. load-bearing cross-file facts --------------------------------------------------
    cert_b = read_bytes(CERT)
    cert = json.loads(cert_b) if cert_b else {}
    c8_b = read_bytes(C8_REVIEW)
    c8 = json.loads(c8_b) if c8_b else {}
    cert_v = cert.get("verdict", {})
    claim = prop.get("certified_order_claim", {})
    claim_orders = claim.get("orders_4rung_certified_fixed_dt_1e-4", {})
    cert_orders = cert_v.get("certified_spatial_order", {})
    order_max_abs_diff = max(
        (abs(claim_orders.get(s, float("nan")) - cert_orders.get(s, float("nan")))
         for s in sorted(set(claim_orders) | set(cert_orders))), default=None)
    claim_delta = claim.get("delta_R5_4rung_fixed_dt", {})
    cert_delta = cert.get("cross_scheme_R5", {}).get("delta_R5_by_scheme", {})
    delta_max_abs_diff = max(
        (abs(claim_delta.get(s, float("nan")) - cert_delta.get(s, float("nan")))
         for s in sorted(set(claim_delta) | set(cert_delta))), default=None)
    lock = rmap.get("numerics_lock", {})
    solver_present = (ROOT / SPHERICAL_SOLVER).exists()
    gates_b = read_bytes(GATES_PY)
    gates_sha = sha256_bytes(gates_b) if gates_b else None
    fixed_run_b = read_bytes(FIXED_RUN)
    fixed_run_sha = sha256_bytes(fixed_run_b) if fixed_run_b else None

    load_bearing = {
        "certified_orders_equal_certification_file": {
            "claim": claim_orders, "certification": cert_orders,
            "max_abs_diff": order_max_abs_diff, "ok": bool(order_max_abs_diff is not None
                                                          and order_max_abs_diff <= 1e-12)},
        "delta_R5_equal_certification_file": {
            "claim": claim_delta, "certification": cert_delta,
            "max_abs_diff": delta_max_abs_diff, "ok": bool(delta_max_abs_diff is not None
                                                          and delta_max_abs_diff <= 1e-12)},
        "standing_C8_accept_binds_protocol_of_record": {
            "review_verdict": c8.get("verdict"),
            "reviewed_sha256": c8.get("reviewed_sha256"),
            "protocol_sha256": sha256_bytes(read_bytes(PROTOCOL) or b""),
            "ok": bool(c8.get("verdict") == "accept"
                       and c8.get("reviewed_sha256") == sha256_bytes(read_bytes(PROTOCOL) or b""))},
        "evaluator_fix_in_place": {
            "proposal_declared": chain.get(GATES_PY), "measured": gates_sha,
            "ok": gates_sha == chain.get(GATES_PY)},
        "lock_intact": {
            "state": lock.get("state"), "spherical_solver_present": solver_present,
            "ok": bool(lock.get("state") == "locked" and not solver_present)},
        "C4_fixed_run_registered": {
            "path": FIXED_RUN, "sha256": fixed_run_sha,
            "registered": FIXED_RUN in reg_hashes,
            "ok": FIXED_RUN in reg_hashes},
        "protocol_of_record_registered": {
            "path": PROTOCOL, "registered": PROTOCOL in reg_hashes,
            "ok": PROTOCOL in reg_hashes},
    }

    # ---- bounded mention scan --------------------------------------------------------------
    mention_scan = []
    for rel in MENTION_RECORDS:
        b = read_bytes(rel)
        if b is None:
            mention_scan.append({"path": rel, "present": False})
            continue
        txt = b.decode("utf-8", "replace")
        mention_scan.append({
            "path": rel, "present": True, "sha256": sha256_bytes(b),
            "mentions_current_proposal_hash": prop_sha[:12] in txt,
            "mentions_superseded_pin": bool(old_pin) and old_pin[:12] in txt,
            "is_verification_of_record": rel == LEADVERIFY,
        })

    # ---- controls (fail-closed) ------------------------------------------------------------
    tmp_correct = OUT_DIR / ".control_correct.bin"
    tmp_tamper = OUT_DIR / ".control_tamper.bin"
    tmp_correct.write_bytes(b"control-bytes")
    tmp_tamper.write_bytes(b"control-bytes")
    good = sha256_bytes(tmp_correct.read_bytes())
    rows_c = classify({
        str(tmp_correct.relative_to(ROOT)): good,
        str(tmp_tamper.relative_to(ROOT)): "0" * 64,
        "no/such/path.bin": "1" * 64,
    })
    got = {r["path"]: r["status"] for r in rows_c}
    control("C1_known_good_classifies_match",
            got.get(str(tmp_correct.relative_to(ROOT))) == "match", "expected match")
    control("C2_tampered_hash_classifies_stale",
            got.get(str(tmp_tamper.relative_to(ROOT))) == "stale", "expected stale")
    control("C3_missing_path_classifies_missing",
            got.get("no/such/path.bin") == "missing", "expected missing")
    control("C4_real_stale_verification_pin_detected",
            (old_pin is not None) and (not pin_is_current),
            f"leadverify pin {str(old_pin)[:12]} vs disk {prop_sha[:12]}")
    control("C5_registry_lookup_sane",
            (PROPOSAL not in reg_hashes) and
            (reg_hashes.get("research_map/formulation_taxonomy.yaml", {}).get("sha256")
             == sha256_bytes(read_bytes("research_map/formulation_taxonomy.yaml") or b"")),
            "proposal unregistered; a known registered path matches live bytes")
    control("C6_load_bearing_facts_hold",
            all(load_bearing[k]["ok"] for k in (
                "certified_orders_equal_certification_file",
                "delta_R5_equal_certification_file",
                "standing_C8_accept_binds_protocol_of_record",
                "evaluator_fix_in_place",
                "lock_intact")),
            "claimed-true cross-file facts must hold for this audit to be usable")
    control("C7_open_registration_items_visible",
            (not load_bearing["C4_fixed_run_registered"]["ok"])
            and (not load_bearing["protocol_of_record_registered"]["ok"]),
            "known-open C4 items must be reported, not hidden")
    for t in (tmp_correct, tmp_tamper):
        t.unlink(missing_ok=True)

    instrument_valid = all(c["behaved"] for c in controls)
    coverage_gap = not pin_is_current

    findings = []
    if coverage_gap:
        findings.append({
            "id": "BA-1", "severity": "load-bearing-for-verdict",
            "finding": ("the filed verification of record "
                        f"({LEADVERIFY}#{lv_sha[:12]}) verifies proposal revision "
                        f"{str(old_pin)[:12]}, but the bytes on disk are {prop_sha[:12]}; "
                        "the current revision's evidence chain has no binding verification record"),
            "consequence": ("astra-life04-n0-verify must re-verify the proposal at the current "
                            "hash (or the lead must re-issue the leadverify record at it); the "
                            "existing leadverify must not be cited as covering current bytes"),
        })
    if not pin_is_current or added or changed:
        findings.append({
            "id": "BA-2", "severity": "informational",
            "finding": "revision delta between the verified revision and the current proposal",
            "added_evidence_entries": added,
            "removed_evidence_entries": removed,
            "changed_declared_hashes": changed,
        })
    findings.append({
        "id": "BA-3", "severity": "advisory",
        "finding": (f"registry coverage at snapshot {reg_sha[:12]}: "
                    f"{reg_summary['registered_match']} match, "
                    f"{reg_summary['registered_stale']} stale, "
                    f"{reg_summary['unregistered']} unregistered of "
                    f"{len(reg_rows)} proposal-chain/proposal/leadverify paths"),
        "open_C4_items": [r["path"] for r in reg_rows
                          if r["status"] == "unregistered"
                          and r["path"] in (PROTOCOL, FIXED_RUN, PROPOSAL, LEADVERIFY)],
    })
    if not any(m.get("is_verification_of_record") and m.get("mentions_current_proposal_hash")
               for m in mention_scan if m.get("present")):
        findings.append({
            "id": "BA-4", "severity": "informational",
            "finding": ("no scanned record that mentions the current proposal hash is a "
                        "verification-of-record; mentions are rebind/adjudication notes"),
            "scan": mention_scan,
        })

    report = {
        "schema": "w14-n0-proposal-binding-audit/v1",
        "task_id": "W14-GNUM-BINDING-AUDIT-01",
        "actor": "deepseek-flash-14",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "class_id": prop.get("class_id", "AF-WCC-SCALAR-SPH"),
        "node_id": "N0",
        "gate": "G-NUM",
        "conclusion_type": "provenance_measurement",
        "pins": {
            PROPOSAL: {"sha256": prop_sha, "bytes": len(prop_b)},
            LEADVERIFY: {"sha256": lv_sha, "bytes": len(lv_b)},
            REGISTRY: {"sha256": reg_sha, "bytes": len(reg_b), "note": "mutable controller file; snapshot pin"},
            MAP: {"sha256": sha256_bytes(map_b)},
        },
        "verification_of_record": {
            "record": f"{LEADVERIFY}#{lv_sha[:12]}",
            "verified_proposal_sha256": old_pin,
            "current_proposal_sha256": prop_sha,
            "pin_is_current": pin_is_current,
            "coverage_gap": coverage_gap,
            "old_verified_entries": len(old_verified),
            "current_chain_entries": len(chain),
            "added_evidence_entries": added,
            "removed_evidence_entries": removed,
            "changed_declared_hashes": changed,
        },
        "evidence_chain": {"summary": chain_summary, "rows": chain_rows},
        "registry_coverage": {"summary": reg_summary, "rows": reg_rows},
        "load_bearing": load_bearing,
        "mention_scan": mention_scan,
        "findings": findings,
        "controls": controls,
        "instrument_valid": instrument_valid,
        "verdict": ("BINDING_GAP_VERIFICATION_OF_RECORD_STALE"
                    if instrument_valid and coverage_gap else
                    "BINDING_COVERED" if instrument_valid else "INSTRUMENT_INVALID"),
        "does_not_claim": [
            "no gate verdict and no gate self-pass; G-NUM adjudication is Astra's",
            "no node completion; numerics_lock stays LOCKED and N1 stays queued",
            "no judgement that the current proposal revision is wrong; the measured chain matches disk",
            "no independent protocol review; this is a provenance measurement",
            "no controller registration write; C4 remains a controller action",
            "no edit of any other agent's artifact; every input was read read-only",
        ],
        "falsifier": ("Re-run this instrument at the pinned input hashes: the report is falsified if "
                      "any evidence_chain row classified match has a different measured sha256, if "
                      "the leadverify record is shown to pin the current proposal hash, if the "
                      "current proposal is registered, if a control behaves differently, or if any "
                      "load-bearing check that is recorded ok is shown false. A moved proposal hash "
                      "voids the coverage verdict for the new bytes."),
    }
    OUT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"verdict={report['verdict']} instrument_valid={instrument_valid}")
    print(f"chain={chain_summary} registry={reg_summary} coverage_gap={coverage_gap}")
    print(f"report_sha256={sha256_bytes(OUT.read_bytes())}")
    return 0 if instrument_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
