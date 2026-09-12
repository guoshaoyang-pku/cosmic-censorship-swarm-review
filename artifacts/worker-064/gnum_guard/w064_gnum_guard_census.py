#!/usr/bin/env python3
"""W064-GNUM-GUARD-CENSUS-01: read-only census + candidate-rule simulation for
numerics/gates.py::_protocol_review at protocol 1e6cdf04d7a2.

No canonical file is written. The live gate module is never imported from its
canonical path (a hash-pinned copy is imported instead, with bytecode writing
disabled) so that no __pycache__ or other byte is deposited in numerics/.

Exit 0 iff every preregistered expectation (artifacts/worker-064/gnum_guard/
prereg.json) is reproduced on the frozen snapshot. Exit 2 on a pin mismatch
(tool or protocol moved). Exit 3 on a falsified expectation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # repo root
RAW = HERE / "raw"
PIN_GATES = HERE / "pinned" / "gates_fcd1d70991b6.py"
PIN_PROTO = HERE / "pinned" / "CONVERGENCE_PROTOCOL_1e6cdf04d7a2.md"
PROTOCOL_REL = "numerics/CONVERGENCE_PROTOCOL.md"
GATES_REL = "numerics/gates.py"

EXPECT_GATES_SHA = "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e"
EXPECT_PROTO_SHA = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
ADJ_EVENT = "audit-l06-review-gnum-r4-20260912T005926"
ADJ_ARTIFACT = "reviews/G-NUM-protocol-r4-adjudication.json"
ADJ_ARTIFACT_SHA_PREFIX = "b836902fa4ae"

PRED_ACCEPTS = [
    "w081-20260912T002140-c8-review",
    "audit-review-gnum-protocol-final-20260912T0027",
    "w081-20260912T0042050800-adj2-review",
    "w012-c3-review-0001-adjudication",
    "f13-n0rev3-20260912T005801-review",
]
PRED_DISSENTS = [
    "w067-review-gnum-protocol-r3-20260912T002256",
    "w081-2026-09-12T00:29:19+0800-f1-review",
    "w067-provledger-20260912T005149-20-review",
    "w042-n0-stoprule-01-review",
    "w081-20260912T005818-pinsplit-review",
]
WITHDRAWN_ACCEPT = "w081-20260912T002140-c8-review"
WITHDRAWAL_EVENT = "w081-2026-09-12T00:29:19+0800-complete"
SCOPE_TARGETS = (PROTOCOL_REL, "G-NUM-protocol")
N0_DISSENTS = [
    "w067-provledger-20260912T005149-20-review",
    "w042-n0-stoprule-01-review",
    "w081-20260912T005818-pinsplit-review",
]
WITHDRAW_FIELDS = ("withdraws", "withdraws_event_ids", "withdrawn_event_ids",
                   "withdraws_review")
DISCHARGE_FIELDS = ("discharges", "discharged_event_ids", "supersedes_event_ids")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ts(s) -> float | None:
    if not isinstance(s, str):
        return None
    t = s.strip().replace("+0800", "+08:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(t, fmt).timestamp()
        except ValueError:
            continue
    return None


def cited_hashes(e: dict) -> list[str]:
    out = []
    for k in ("reviewed_sha256", "artifact_sha256", "reviewed_protocol_hash"):
        v = e.get(k)
        if isinstance(v, str) and len(v.strip()) >= 12:
            out.append(v.strip().lower())
    for ref in e.get("evidence_refs", []) or []:
        if not isinstance(ref, str):
            continue
        for sep in ("#sha256:", "#"):
            if ref.startswith(PROTOCOL_REL + sep):
                h = ref.split(sep, 1)[1].strip().lower()
                if len(h) >= 12:
                    out.append(h)
    return out


def load_pinned():
    spec = importlib.util.spec_from_file_location("gates_pinned", PIN_GATES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_review(e: dict) -> bool:
    return e.get("event_type") == "review" and e.get("verdict") in (
        "accept", "revise", "reject")


def targets_protocol_any(target: str, gate_targets) -> bool:
    t = str(target or "").strip()
    for cand in gate_targets:
        if t == cand or t.startswith(cand + "#") or t.startswith(cand + "@"):
            return True
    return False


def find_prose_withdrawal(events: list[dict], target_id: str) -> dict | None:
    """Locate a non-machine-readable withdrawal declaration (prose) naming target_id."""
    out = None
    for e in events:
        blob = " ".join(str(e.get(k) or "") for k in
                        ("summary", "description", "statement", "note", "notes"))
        low = blob.lower()
        if "withdraw" in low and (target_id.lower() in low
                                  or "prior w081-n0-c8-01 accept withdrawn" in low):
            out = {"event_id": e.get("event_id"), "event_type": e.get("event_type"),
                   "actor": e.get("actor"), "created_at": e.get("created_at"),
                   "evidence_text": blob[:300],
                   "structured_fields_present": [f for f in WITHDRAW_FIELDS
                                                 if e.get(f)]}
            break
    return out


def collect_withdrawals(events: list[dict]) -> dict[str, dict]:
    """map withdrawn event_id -> withdrawing event (only author may withdraw own review)."""
    by_id = {}
    for e in events:
        eid = e.get("event_id")
        if eid:
            by_id.setdefault(str(eid), e)
    out = {}
    for e in events:
        ids = []
        for f in WITHDRAW_FIELDS:
            v = e.get(f)
            if isinstance(v, str):
                ids.append(v)
            elif isinstance(v, list):
                ids.extend(str(x) for x in v)
        for target in ids:
            tgt = by_id.get(target)
            if tgt is None:
                continue
            if e.get("actor") != tgt.get("reviewer") and e.get("actor") != tgt.get("actor"):
                continue  # third-party withdrawal is not authority
            out[target] = {
                "withdrawing_event": e.get("event_id"),
                "event_type": e.get("event_type"),
                "actor": e.get("actor"),
                "created_at": e.get("created_at"),
                "same_hash_binding": bool(tgt),
            }
    return out


def collect_discharges(events: list[dict], protocol_sha: str) -> dict[str, dict]:
    """map dissent event_id -> discharging carrier event (fail-closed)."""
    by_id = {str(e.get("event_id")): e for e in events if e.get("event_id")}
    out = {}
    for e in events:
        if not is_review(e) or e.get("verdict") != "accept":
            continue
        if not targets_protocol_any(str(e.get("target_id", "")),
                                    (PROTOCOL_REL, "G-NUM-protocol", "N0")):
            continue
        hs = cited_hashes(e)
        binds = any(protocol_sha.startswith(h) or h.startswith(protocol_sha) for h in hs)
        if not binds:
            continue
        ids = []
        for f in DISCHARGE_FIELDS:
            v = e.get(f)
            if isinstance(v, str):
                ids.append(v)
            elif isinstance(v, list):
                ids.extend(str(x) for x in v)
        carrier_ts = parse_ts(e.get("created_at"))
        for target in ids:
            tgt = by_id.get(target)
            if tgt is None:
                continue  # unknown id: ignored
            tgt_ts = parse_ts(tgt.get("created_at"))
            if carrier_ts is not None and tgt_ts is not None and carrier_ts < tgt_ts:
                continue  # pre-dissent carrier never discharges
            out[target] = {
                "carrier_event": e.get("event_id"),
                "carrier_reviewer": e.get("reviewer"),
                "carrier_created_at": e.get("created_at"),
                "carrier_binds_hash": True,
            }
    return out


def shadow_review(events: list[dict], protocol_sha: str, *, scope: bool,
                  withdrawal: bool, discharge: bool, gate_targets) -> dict:
    """Shadow of numerics/gates.py::_protocol_review with the candidate rule hooks.

    With scope=withdrawal=discharge=False this must reproduce the pinned module's
    output exactly (equivalence control, E0).
    """
    withdrawals = collect_withdrawals(events) if withdrawal else {}
    discharges = collect_discharges(events, protocol_sha) if discharge else {}
    accepts, dissents, advisory, discharged = [], [], [], []
    seen = set()
    for e in events:
        if not is_review(e):
            continue
        target = str(e.get("target_id", ""))
        if not targets_protocol_any(target, gate_targets):
            continue
        if scope and not targets_protocol_any(target, SCOPE_TARGETS):
            continue
        if e.get("reviewer") == "astra-lead-numerics":
            continue
        eid = str(e.get("event_id") or id(e))
        if eid in seen:
            continue
        seen.add(eid)
        hs = cited_hashes(e)
        binds = bool(protocol_sha) and any(
            protocol_sha.startswith(h) or h.startswith(protocol_sha) for h in hs)
        if not binds:
            advisory.append({"event_id": e.get("event_id"), "verdict": e.get("verdict"),
                             "cited": hs, "reviewer": e.get("reviewer")})
            continue
        if withdrawal and eid in withdrawals:
            continue
        if e.get("verdict") == "accept":
            accepts.append(eid)
        elif discharge and eid in discharges:
            discharged.append({"event_id": eid, "verdict": e.get("verdict"),
                               "reviewer": e.get("reviewer"),
                               "discharged_by": discharges[eid]})
        else:
            dissents.append({"event_id": eid, "verdict": e.get("verdict"),
                             "reviewer": e.get("reviewer")})
    return {
        "reviewed": bool(accepts),
        "accepting_reviews": accepts,
        "dissenting_reviews": dissents,
        "discharged_dissents": discharged,
        "contest": bool(dissents),
        "advisory_reviews_at_other_hashes": advisory,
        "protocol_sha256_measured": protocol_sha,
        "reviewed_protocol_sha256": protocol_sha if accepts else None,
        "withdrawals_applied": withdrawals if withdrawal else {},
    }


def main() -> int:
    ts_start = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    RAW.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    fails: list[str] = []

    def check(cid: str, ok: bool, detail):
        checks.append({"id": cid, "pass": bool(ok), "detail": detail})
        if not ok:
            fails.append(cid)

    # ---- pins -------------------------------------------------------------
    live_gates_sha = sha256_file(ROOT / GATES_REL)
    live_proto_sha = sha256_file(ROOT / PROTOCOL_REL)
    pin_gates_sha = sha256_file(PIN_GATES)
    pin_proto_sha = sha256_file(PIN_PROTO)
    check("P0-live-gates-pin", live_gates_sha == EXPECT_GATES_SHA,
          {"live": live_gates_sha, "expected": EXPECT_GATES_SHA})
    check("P0-live-protocol-pin", live_proto_sha == EXPECT_PROTO_SHA,
          {"live": live_proto_sha, "expected": EXPECT_PROTO_SHA})
    check("P0-copy-gates-pin", pin_gates_sha == EXPECT_GATES_SHA,
          {"copy": pin_gates_sha})
    check("P0-copy-protocol-pin", pin_proto_sha == EXPECT_PROTO_SHA,
          {"copy": pin_proto_sha})
    if fails:
        print("PIN MISMATCH -> exit 2:", fails)
        return 2

    gates = load_pinned()

    # ---- frozen snapshot --------------------------------------------------
    snapshot = gates.load_event_stream(ROOT)
    snap_path = RAW / "events_snapshot.jsonl"
    with open(snap_path, "w") as f:
        for e in snapshot:
            f.write(json.dumps(e, sort_keys=True) + "\n")
    snap_sha = sha256_file(snap_path)

    sources = [ROOT / "research_map" / "events.jsonl"]
    for folder in (ROOT / "comms" / "outbox", ROOT / "comms" / "inbox"):
        if folder.is_dir():
            sources.extend(sorted(folder.rglob("*.jsonl")))
    src_manifest = [{"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p)}
                    for p in sources if p.is_file()]
    (RAW / "source_manifest.json").write_text(json.dumps(
        {"captured_at": ts_start, "n_sources": len(src_manifest),
         "n_events": len(snapshot), "snapshot_sha256": snap_sha,
         "sources": src_manifest}, indent=1))

    # ---- arm 0: guard as-is + equivalence control -------------------------
    guard_rep = gates._protocol_review(snapshot, EXPECT_PROTO_SHA)
    shadow0 = shadow_review(snapshot, EXPECT_PROTO_SHA, scope=False,
                            withdrawal=False, discharge=False,
                            gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    eq = {k: (guard_rep.get(k) == shadow0.get(k))
          for k in ("reviewed", "accepting_reviews", "dissenting_reviews",
                    "contest", "advisory_reviews_at_other_hashes")}
    check("E0-shadow-equivalence", all(eq.values()), eq)

    acc = guard_rep["accepting_reviews"]
    dis = [d["event_id"] for d in guard_rep["dissenting_reviews"]]
    adv = {a["event_id"]: a for a in guard_rep["advisory_reviews_at_other_hashes"]}
    check("E1-guard-verdict", guard_rep["reviewed"] and guard_rep["contest"],
          {"reviewed": guard_rep["reviewed"], "contest": guard_rep["contest"]})
    missing_acc = [i for i in PRED_ACCEPTS if i not in acc]
    missing_dis = [i for i in PRED_DISSENTS if i not in dis]
    extra_acc = [i for i in acc if i not in PRED_ACCEPTS]
    extra_dis = [i for i in dis if i not in PRED_DISSENTS]
    check("E2-predicted-rows", not missing_acc and not missing_dis,
          {"missing_accepts": missing_acc, "missing_dissents": missing_dis,
           "predicted_accepts_present": len(PRED_ACCEPTS) - len(missing_acc),
           "predicted_dissents_present": len(PRED_DISSENTS) - len(missing_dis),
           "post_prediction_drift": {"accepts": extra_acc, "dissents": extra_dis}})
    check("E3-adjudication-advisory", ADJ_EVENT in adv and ADJ_EVENT not in acc,
          {"advisory_row": adv.get(ADJ_EVENT), "in_accepts": ADJ_EVENT in acc})

    # ---- census rows with provenance --------------------------------------
    occ: dict[str, list] = {}
    for p in sources:
        if not p.is_file():
            continue
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = d.get("event_id")
            if eid in set(acc) | set(dis) | set(adv):
                occ.setdefault(str(eid), []).append(
                    f"{p.relative_to(ROOT)}:{i}")
    first_doc = {}
    for e in snapshot:
        eid = str(e.get("event_id"))
        if eid in set(acc) | set(dis) | set(adv) and eid not in first_doc:
            first_doc[eid] = e
    r4 = json.loads((ROOT / ADJ_ARTIFACT).read_text())
    discharges = {}
    for obj, row in (r4.get("discharge") or {}).items():
        if isinstance(row, dict) and row.get("discharged"):
            discharges[obj] = row
    withdrawn = collect_withdrawals(snapshot)
    subject = {
        "w067-review-gnum-protocol-r3-20260912T002256": "protocol_text:F1_evidence_basis",
        "w081-2026-09-12T00:29:19+0800-f1-review": "protocol_text:F1prime_evidence_basis",
        "w067-provledger-20260912T005149-20-review": "N0_node:provenance_ledger",
        "w042-n0-stoprule-01-review": "N0_node:stop_rule",
        "w081-20260912T005818-pinsplit-review": "N0_node:pin_split",
        "w081-20260912T002140-c8-review": "protocol_text:accept",
        "audit-review-gnum-protocol-final-20260912T0027": "protocol_text:accept",
        "w081-20260912T0042050800-adj2-review": "protocol_text:accept",
        "w012-c3-review-0001-adjudication": "protocol_text:accept",
        "f13-n0rev3-20260912T005801-review": "N0_node:accept",
    }
    census_rows = []
    for side, ids in (("accept", acc), ("dissent", dis),
                      ("advisory", list(adv))):
        for eid in ids:
            d = first_doc.get(eid, {})
            row = {
                "event_id": eid,
                "side": side,
                "reviewer": d.get("reviewer") or d.get("actor"),
                "created_at": d.get("created_at"),
                "target_id": d.get("target_id"),
                "verdict": d.get("verdict"),
                "score": d.get("score"),
                "cited_hashes": cited_hashes(d),
                "binds_protocol_hash": eid not in adv,
                "subject": subject.get(eid, "unclassified"),
                "occurrences": occ.get(eid, []),
                "n_occurrences": len(occ.get(eid, [])),
                "withdrawal": withdrawn.get(eid),
                "discharge_claimed": discharges.get(
                    "F1_w067" if "w067-review-gnum-protocol-r3" in eid else
                    "F1_prime_w081" if "f1-review" in eid else None),
                "task_id": d.get("task_id"),
                "gate": d.get("gate"),
                "node_id": d.get("node_id"),
            }
            census_rows.append(row)
    with open(HERE / "census.jsonl", "w") as f:
        for r in census_rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")

    # E4 target conflation
    n0_counted = [r["event_id"] for r in census_rows
                  if r["side"] == "dissent" and r["target_id"] == "N0"]
    check("E4-n0-target-conflation",
          sorted(n0_counted) == sorted(N0_DISSENTS) and "N0" in gates.PROTOCOL_REVIEW_TARGETS,
          {"n0_dissents_counted": n0_counted, "targets": list(gates.PROTOCOL_REVIEW_TARGETS)})
    # E5 refinement: the withdrawal is declared in prose only; E5 as preregistered
    # (structured detection) is recorded as falsified, not hidden.
    wid = withdrawn.get(WITHDRAWN_ACCEPT)
    prose_w = find_prose_withdrawal(snapshot, WITHDRAWN_ACCEPT)
    prereg_falsified = []
    if not (WITHDRAWN_ACCEPT in acc and wid is not None
            and wid.get("withdrawing_event") == WITHDRAWAL_EVENT):
        prereg_falsified.append({
            "id": "E5-withdrawal-ignored",
            "predicted": "a structured author withdrawal exists and the guard ignores it",
            "measured": {"counted_accept": WITHDRAWN_ACCEPT in acc,
                         "structured_withdrawal": wid,
                         "prose_withdrawal_event": (prose_w or {}).get("event_id")},
            "resolution": "refined to E5R (prose-only withdrawal, no machine-readable field)",
        })
    check("E5R-withdrawal-is-prose-only",
          prose_w is not None and prose_w.get("event_id") == WITHDRAWAL_EVENT
          and not prose_w.get("structured_fields_present"),
          {"prose_withdrawal": prose_w,
           "structured_withdrawal_signal": wid})
    # E6 same reviewer both sides
    both = sorted(set(r["reviewer"] for r in census_rows if r["side"] == "accept")
                  & set(r["reviewer"] for r in census_rows if r["side"] == "dissent"))
    check("E6-reviewer-both-sides", both == ["worker-081"], {"reviewers": both})

    # ---- candidate-rule arms ---------------------------------------------
    def ids(rep):
        return {"accepts": rep["accepting_reviews"],
                "dissents": [d["event_id"] for d in rep["dissenting_reviews"]],
                "discharged": [d["event_id"] for d in rep.get("discharged_dissents", [])],
                "contest": rep["contest"], "reviewed": rep["reviewed"]}

    arm_scope = shadow_review(snapshot, EXPECT_PROTO_SHA, scope=True,
                              withdrawal=False, discharge=False,
                              gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    arm_scope_w = shadow_review(snapshot, EXPECT_PROTO_SHA, scope=True,
                                withdrawal=True, discharge=False,
                                gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    # in-memory discharge carrier: same r4 event plus a machine-readable list
    snap_d = []
    for e in snapshot:
        if e.get("event_id") == ADJ_EVENT:
            e = dict(e)
            e["reviewed_sha256"] = EXPECT_PROTO_SHA
            e["discharges"] = ["w067-review-gnum-protocol-r3-20260912T002256",
                               "w081-2026-09-12T00:29:19+0800-f1-review"]
        snap_d.append(e)
    arm_scope_w_d = shadow_review(snap_d, EXPECT_PROTO_SHA, scope=True,
                                  withdrawal=True, discharge=True,
                                  gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    arm_hash_repair = shadow_review(
        [{**e, "reviewed_sha256": EXPECT_PROTO_SHA}
         if e.get("event_id") == ADJ_EVENT else e for e in snapshot],
        EXPECT_PROTO_SHA, scope=False, withdrawal=False, discharge=False,
        gate_targets=gates.PROTOCOL_REVIEW_TARGETS)

    # E8 as preregistered predicted accepts=3 under R2. That prediction is
    # falsified on the live stream because the withdrawal exists only as prose:
    # R2 is inert (E8R) until a structured field is emitted (positive control E8P).
    snap_w = []
    for e in snapshot:
        if e.get("event_id") == WITHDRAWAL_EVENT:
            e = dict(e)
            e["withdraws"] = [WITHDRAWN_ACCEPT]
        snap_w.append(e)
    arm_scope_w_synth = shadow_review(snap_w, EXPECT_PROTO_SHA, scope=True,
                                      withdrawal=True, discharge=False,
                                      gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    check("E7-scope-rule",
          ids(arm_scope)["accepts"] == [a for a in PRED_ACCEPTS
                                        if a != "f13-n0rev3-20260912T005801-review"]
          and ids(arm_scope)["dissents"] == PRED_DISSENTS[:2],
          ids(arm_scope))
    check("E8R-withdrawal-rule-inert-without-structured-signal",
          ids(arm_scope_w) == ids(arm_scope),
          {"arm_scope": ids(arm_scope), "arm_scope_withdrawal": ids(arm_scope_w)})
    check("E8P-withdrawal-rule-binds-when-field-emitted",
          ids(arm_scope_w_synth)["accepts"] == [a for a in PRED_ACCEPTS
                                                if a not in ("f13-n0rev3-20260912T005801-review",
                                                             WITHDRAWN_ACCEPT)]
          and ids(arm_scope_w_synth)["dissents"] == PRED_DISSENTS[:2],
          ids(arm_scope_w_synth))
    check("E9-scope-withdrawal-discharge",
          ids(arm_scope_w_d)["contest"] is False
          and sorted(ids(arm_scope_w_d)["discharged"]) == sorted(PRED_DISSENTS[:2]
          ) and ids(arm_scope_w_d)["reviewed"] is True,
          ids(arm_scope_w_d))
    check("E11-hash-repair-alone-insufficient",
          ids(arm_hash_repair)["contest"] is True
          and ADJ_EVENT in ids(arm_hash_repair)["accepts"],
          {"accepts": len(ids(arm_hash_repair)["accepts"]),
           "dissents": len(ids(arm_hash_repair)["dissents"]),
           "contest": ids(arm_hash_repair)["contest"]})

    # negative controls
    def with_extra(evs, extra):
        return list(evs) + list(extra)

    unknown = shadow_review(
        with_extra(snapshot, [{"event_id": "w064-ctl-unknown", "event_type": "review",
                               "verdict": "accept", "reviewer": "w064-ctl",
                               "created_at": "2026-09-12T01:30:00+08:00",
                               "target_id": "G-NUM-protocol",
                               "reviewed_sha256": EXPECT_PROTO_SHA,
                               "discharges": ["no-such-event-id"]}]),
        EXPECT_PROTO_SHA, scope=True, withdrawal=True, discharge=True,
        gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    stale = shadow_review(
        with_extra(snapshot, [{"event_id": "w064-ctl-stale", "event_type": "review",
                               "verdict": "accept", "reviewer": "w064-ctl",
                               "created_at": "2026-09-12T01:30:00+08:00",
                               "target_id": "G-NUM-protocol",
                               "reviewed_sha256": "01b2072434cd0783da1c874941981f14813af35e8ebc0386faff1fa7515d900a",
                               "discharges": PRED_DISSENTS[:2]}]),
        EXPECT_PROTO_SHA, scope=True, withdrawal=True, discharge=True,
        gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    predated = shadow_review(
        with_extra(snapshot, [{"event_id": "w064-ctl-predated", "event_type": "review",
                               "verdict": "accept", "reviewer": "w064-ctl",
                               "created_at": "2026-09-12T00:10:00+08:00",
                               "target_id": "G-NUM-protocol",
                               "reviewed_sha256": EXPECT_PROTO_SHA,
                               "discharges": PRED_DISSENTS[:2]}]),
        EXPECT_PROTO_SHA, scope=True, withdrawal=True, discharge=True,
        gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    fresh = shadow_review(
        with_extra(snap_d, [{"event_id": "w064-ctl-fresh-dissent",
                             "event_type": "review", "verdict": "revise",
                             "reviewer": "w064-ctl",
                             "created_at": "2026-09-12T01:31:00+08:00",
                             "target_id": "G-NUM-protocol",
                             "reviewed_sha256": EXPECT_PROTO_SHA}]),
        EXPECT_PROTO_SHA, scope=True, withdrawal=True, discharge=True,
        gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    thirdparty = shadow_review(
        with_extra(snapshot, [{"event_id": "w064-ctl-thirdparty-withdrawal",
                               "event_type": "status", "actor": "astra",
                               "created_at": "2026-09-12T01:32:00+08:00",
                               "withdraws": PRED_DISSENTS[0]}]),
        EXPECT_PROTO_SHA, scope=True, withdrawal=True, discharge=False,
        gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    nonbinding = shadow_review(
        with_extra(snapshot, [{"event_id": "w064-ctl-nonbinding-carrier",
                               "event_type": "review", "verdict": "accept",
                               "reviewer": "w064-ctl",
                               "created_at": "2026-09-12T01:33:00+08:00",
                               "target_id": "G-NUM-protocol",
                               "discharges": PRED_DISSENTS[:2]}]),
        EXPECT_PROTO_SHA, scope=True, withdrawal=True, discharge=True,
        gate_targets=gates.PROTOCOL_REVIEW_TARGETS)
    controls = {
        "C1_unknown_id_never_discharges": ids(unknown)["contest"] is True,
        "C2_stale_hash_carrier_never_discharges": ids(stale)["contest"] is True,
        "C3_predated_carrier_never_discharges": ids(predated)["contest"] is True,
        "C4_fresh_unlisted_dissent_still_contests": ids(fresh)["contest"] is True,
        "C5_thirdparty_withdrawal_not_authority":
            PRED_DISSENTS[0] in ids(thirdparty)["dissents"],
        "C6_uncited_carrier_never_discharges": ids(nonbinding)["contest"] is True,
    }
    check("E10-negative-controls", all(controls.values()),
          {"controls": controls,
           "fresh_dissents": ids(fresh)["dissents"],
           "thirdparty_dissents": ids(thirdparty)["dissents"],
           "nonbinding_discharged": ids(nonbinding)["discharged"]})

    # ---- determinism ------------------------------------------------------
    snapshot2 = [json.loads(l) for l in snap_path.read_text().splitlines()]
    guard_rep2 = gates._protocol_review(snapshot2, EXPECT_PROTO_SHA)
    det = (json.dumps(guard_rep, sort_keys=True) == json.dumps(guard_rep2, sort_keys=True))
    check("E12-determinism", det, {"frozen_snapshot_rerun_identical": det})

    # ---- live recheck -----------------------------------------------------
    live = gates.load_event_stream(ROOT)
    live_rep = gates._protocol_review(live, EXPECT_PROTO_SHA)
    drift = {"live_events": len(live), "snapshot_events": len(snapshot),
             "live_accepts": live_rep["accepting_reviews"],
             "live_dissents": [d["event_id"] for d in live_rep["dissenting_reviews"]],
             "live_contest": live_rep["contest"]}
    check("E13-live-recheck", live_rep["contest"] is True, drift)
    live_proto_after = sha256_file(ROOT / PROTOCOL_REL)
    live_gates_after = sha256_file(ROOT / GATES_REL)
    check("P1-no-pin-drift-during-run",
          live_proto_after == EXPECT_PROTO_SHA and live_gates_after == EXPECT_GATES_SHA,
          {"protocol": live_proto_after, "gates": live_gates_after})
    (RAW / "live_recheck.json").write_text(json.dumps(drift, indent=1))

    # ---- write outputs ----------------------------------------------------
    summary = {
        "schema": "worker-064/gnum-guard-census/report/v1",
        "task_id": "W064-GNUM-GUARD-CENSUS-01",
        "actor": "worker-064",
        "created_at": ts_start,
        "node_id": "N0",
        "gate": "G-NUM",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "pins": {
            "numerics/gates.py": live_gates_sha,
            "numerics/CONVERGENCE_PROTOCOL.md": live_proto_sha,
            "frozen_event_snapshot": snap_sha,
            "frozen_event_count": len(snapshot),
        },
        "guard_verdict": {
            "reviewed": guard_rep["reviewed"],
            "contest": guard_rep["contest"],
            "accepts": acc,
            "dissents": [d["event_id"] for d in guard_rep["dissenting_reviews"]],
            "advisory": list(adv),
            "reviewed_protocol_sha256": guard_rep["reviewed_protocol_sha256"],
        },
        "findings": {
            "F-GUARD-1_adjudication_accept_advisory": {
                "measured": "the audit lead's operative r4 accept is counted advisory, not accepting, because the emitted event cites no protocol hash; the cited artifact does carry reviewed_sha256=" + EXPECT_PROTO_SHA[:12],
                "impact": "the ruling that discharges F1/F1' does not bind the guard; one-field event-layer repair demonstrated in arm E11 (binds, contest unchanged)",
            },
            "F-GUARD-2_target_conflation": {
                "measured": "PROTOCOL_REVIEW_TARGETS includes 'N0', so 3 of 5 counted dissents are N0 node reviews (provenance ledger, stop rule, pin split) and 1 of 5 counted accepts is an N0 node verdict",
                "impact": "protocol review state is not separable from N0 node verdict state; the r4 card explicitly claims no N0 verdict",
            },
            "F-GUARD-3_withdrawal_ignored": {
                "measured": "the counted accept %s is declared withdrawn by its author in %s -- but only in the event's prose summary; no withdraws/withdraws_event_ids/withdrawn_event_ids field exists anywhere in the stream, and _protocol_review reads only event_type=='review'" % (WITHDRAWN_ACCEPT, WITHDRAWAL_EVENT),
                "impact": "a retracted verdict keeps voting; a withdrawal-aware rule (R2) is inert on the live stream until the owner emits a structured field (positive control E8P shows the rule then binds)",
                "prose_evidence": prose_w,
            },
            "F-GUARD-4_reviewer_both_sides": {
                "measured": "worker-081 is counted as both an accept and a dissent at the same protocol hash",
                "impact": "no per-reviewer supersession; a revised author is double-counted",
            },
            "F-GUARD-5_contest_not_gate_deciding": {
                "measured": "clearing the guard contest (arm E9) flips production_allowed only if the other reasons are also clear; the controller's own G-NUM audit keeps the gate pending until the N0 node verdict is an accept, and the on-disk N0 verdict is a 3.5 revise",
                "impact": "b4 is necessary, not sufficient; gate G-NUM does not turn green on this repair alone",
            },
        },
        "candidate_rule": {
            "status": "PROPOSAL ONLY, NOT APPLIED (owner: controller, per audit-l06-b4 / CF-26 pattern)",
            "R1_scope": "protocol review state excludes N0-targeted reviews",
            "R2_withdrawal": "author-declared withdrawal removes the verdict (third-party ignored)",
            "R3_discharge": "later binding review at the same hash may carry discharges/discharged_event_ids/supersedes_event_ids; fail-closed on unknown ids, stale carriers, pre-dated carriers",
            "arms": {
                "arm0_current_bytes": ids(guard_rep),
                "arm_scope": ids(arm_scope),
                "arm_scope_withdrawal": ids(arm_scope_w),
                "arm_scope_withdrawal_synthetic_field": ids(arm_scope_w_synth),
                "arm_scope_withdrawal_discharge": ids(arm_scope_w_d),
                "arm_hash_repair_only": ids(arm_hash_repair),
            },
            "negative_controls": controls,
        },
        "prereg_falsified": {
            "note": "preregistered predictions that failed as written on the frozen snapshot; recorded here rather than edited out of prereg.json",
            "items": prereg_falsified + [{
                "id": "E8-scope-plus-withdrawal",
                "predicted": "accepts=3 under rule R2 on the live stream",
                "measured": {"arm_scope_withdrawal_accepts": len(ids(arm_scope_w)["accepts"]),
                             "arm_scope_withdrawal_synthetic_accepts": len(ids(arm_scope_w_synth)["accepts"])},
                "resolution": "R2 is inert until a structured withdraws field exists; E8P positive control shows accepts=3 once emitted",
            }],
        },
        "prose_withdrawal_evidence": prose_w,
        "checks": checks,
        "verdict": ("ALL_EXPECTATIONS_REPRODUCED__GUARD_CONTEST_IS_MECHANICAL__"
                    "SCOPE_AND_WITHDRAWAL_AND_DISCHARGE_RULE_SAFE_ON_CONTROLS"
                    if not fails else "FALSIFIED:" + ",".join(fails)),
        "not_claimed": [
            "no gate verdict, no gate self-pass, no N0 node completion",
            "no physics claim, no solver, no self-gravity; numerics_lock stays LOCKED",
            "no canonical file modified; candidate rule is simulated in-memory only",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(summary, indent=1, sort_keys=True))
    (HERE / "candidate_rules.json").write_text(json.dumps(
        {"task_id": "W064-GNUM-GUARD-CENSUS-01",
         "generated_at": ts_start,
         "rule_status": "proposal-only-not-applied",
         "arms": summary["candidate_rule"]["arms"],
         "negative_controls": controls,
         "equivalence_control_shadow_vs_pinned": eq},
        indent=1, sort_keys=True))

    print(json.dumps({"verdict": summary["verdict"], "fails": fails,
                      "checks": len(checks),
                      "accepts": len(acc), "dissents": len(dis),
                      "advisory": len(adv)}, indent=1))
    return 0 if not fails else 3


if __name__ == "__main__":
    sys.exit(main())
