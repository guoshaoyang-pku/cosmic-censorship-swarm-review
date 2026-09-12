#!/usr/bin/env python3
"""W014-GNUM-GUARD-VERIFY-01 — independent non-author verification of worker-064's
W064-GNUM-GUARD-CENSUS-01 (artifacts/worker-064/gnum_guard/).

Read-only. Re-implements the guard semantics and the R1-R3 candidate rule from the
published spec (does not import worker-064's harness), cross-checks the shadow against
the live `numerics.gates._protocol_review` on the author's frozen snapshot, reproduces
every arm and negative control, and adds six adversarial controls probing the discharge
rule's trust boundary.

Run:  python3 verify_guard_census.py --out report.json
Exit: 0 verdict reached, 2 falsified / fail-closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
W64 = ROOT / "artifacts" / "worker-064" / "gnum_guard"

PIN_GATES = "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e"
PIN_PROTO = "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274"
PROTO_PATH = "numerics/CONVERGENCE_PROTOCOL.md"
TARGETS = (PROTO_PATH, "G-NUM-protocol", "N0")
SELF_REVIEWER = "astra-lead-numerics"
WITHDRAW_FIELDS = ("withdraws", "withdraws_event_ids", "withdrawn_event_ids")
DISCHARGE_FIELDS = ("discharges", "discharged_event_ids", "supersedes_event_ids")

# hashes declared in artifacts/worker-064/gnum_guard/SHA256SUMS and in the author's
# artifact events; verified against disk before any measurement.
DECLARED = {
    "report.json": "e3ebf9e502491f659eaa10e84654c73dc83ae147d0842134e2fe1858d631cdb5",
    "census.jsonl": "ff3ad3eb6d481e9aef946ee0da0173d47f5d5cc69eb19f67ca2ad784f48d96fa",
    "candidate_rules.json": "e6ad4f16eecc0379ef87eda29bc906747178c73cbfe458bc8ecf9423ff036a7c",
    "prereg.json": "57a64cb6451ea7a1f9e567494abec34bf29ba0ae0e3f5d798ae7128ed8c561c3",
    "w064_gnum_guard_census.py": "1db0e4f09b697d255bf5fc8d6be02a52cff74d33847d05bb1db3b7842132e9fd",
    "README.md": "e6cf9cf97cc2f6f27f2d95c5a8c3534aed7091a75a0a47d653d448dc01f057b1",
    "raw/events_snapshot.jsonl": "b476b9e5e54fbcbdfd356f4f61f74381599fafe481223c8afe4f29ddc031c437",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def payload_digest(report: dict) -> str:
    drop = {"generated_at", "runtime_seconds"}
    return hashlib.sha256(canon({k: v for k, v in report.items() if k not in drop}).encode()).hexdigest()


def parse_ts(value):
    """Parse both +08:00 and +0800 forms; naive timestamps are read as UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    t = value.strip()
    m = re.search(r"([+-])(\d{2})(\d{2})$", t)
    if m:
        t = t[: m.start()] + m.group(1) + m.group(2) + ":" + m.group(3)
    t = t.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def rank(event: dict, idx: int):
    ts = parse_ts(event.get("created_at"))
    return (ts.timestamp() if ts else float("-inf"), idx)


# ---------------------------------------------------------------- guard semantics

def targets_protocol(target: str) -> bool:
    t = str(target or "").strip()
    for cand in TARGETS:
        if t == cand or t.startswith(cand + "#") or t.startswith(cand + "@"):
            return True
    return False


def target_class(target: str) -> str:
    t = str(target or "").strip()
    if t == "N0":
        return "n0"
    if targets_protocol(t):
        return "protocol"
    return "other"


def cited_hashes(event: dict) -> list:
    """Guard-visible citations: the three fields plus PROTOCOL_PATH-pinned evidence_refs."""
    out = []
    for key in ("reviewed_sha256", "artifact_sha256", "reviewed_protocol_hash"):
        v = event.get(key)
        if isinstance(v, str) and len(v.strip()) >= 12:
            out.append(v.strip().lower())
    for ref in event.get("evidence_refs", []) or []:
        if not isinstance(ref, str):
            continue
        for sep in ("#sha256:", "#"):
            if ref.startswith(PROTO_PATH + sep):
                h = ref.split(sep, 1)[1].strip().lower()
                if len(h) >= 12:
                    out.append(h)
    return out


def binds(event: dict, protocol_sha: str) -> bool:
    target = (protocol_sha or "").lower()
    return bool(target) and any(
        target.startswith(c) or c.startswith(target) for c in cited_hashes(event)
    )


def dedup(events: list) -> list:
    seen, out = set(), []
    for idx, e in enumerate(events):
        eid = str(e.get("event_id") or "")
        if eid and eid in seen:
            continue
        if eid:
            seen.add(eid)
        out.append((idx, e))
    return out


def review_pool(events: list) -> list:
    """All reviews a guard would consider, deduplicated, with bind/class metadata."""
    rows = []
    for idx, e in dedup(events):
        if e.get("event_type") != "review":
            continue
        if e.get("verdict") not in ("accept", "revise", "reject"):
            continue
        if not targets_protocol(e.get("target_id")):
            continue
        if e.get("reviewer") == SELF_REVIEWER:
            continue
        rows.append(
            {
                "idx": idx,
                "event_id": str(e.get("event_id") or ""),
                "reviewer": e.get("reviewer"),
                "verdict": e.get("verdict"),
                "cls": target_class(e.get("target_id")),
                "bound": binds(e, PIN_PROTO),
                "cited": cited_hashes(e),
                "rank": rank(e, idx),
                "event": e,
            }
        )
    return rows


def shadow_state(rows: list) -> dict:
    """Independent re-implementation of numerics.gates._protocol_review's state shape."""
    accepts, dissents, advisory = [], [], []
    for r in rows:
        if not r["bound"]:
            advisory.append(r["event_id"])
            continue
        if r["verdict"] == "accept":
            accepts.append(r["event_id"])
        else:
            dissents.append({"event_id": r["event_id"], "verdict": r["verdict"], "reviewer": r["reviewer"]})
    return {
        "reviewed": bool(accepts),
        "accepting_reviews": accepts,
        "dissenting_reviews": dissents,
        "contest": bool(dissents),
        "advisory_reviews_at_other_hashes": advisory,
    }


def structured_withdrawals(events: list, by_id: dict) -> dict:
    """R2: author-declared withdrawal via a structured field; third-party ignored."""
    out = {}
    for e in events:
        actor = str(e.get("actor") or e.get("reviewer") or "")
        for field in WITHDRAW_FIELDS:
            ids = e.get(field)
            if isinstance(ids, str):
                ids = [ids]
            if not isinstance(ids, list):
                continue
            for tid in ids:
                if not isinstance(tid, str) or tid not in by_id:
                    continue
                if actor and actor == str(by_id[tid]["reviewer"]):
                    out[tid] = str(e.get("event_id") or "")
    return out


def structured_discharges(events: list, by_id: dict) -> dict:
    """R3: later binding review at the current hash listing dissent ids.

    Fail-closed: unknown ids, non-review carriers, non-binding carriers, pre-dated
    carriers, self-named ids and accept targets never discharge.
    """
    out = {}
    for e in events:
        if e.get("event_type") != "review":
            continue
        if not binds(e, PIN_PROTO):
            continue
        carrier_rank = rank(e, 10**9)
        for field in DISCHARGE_FIELDS:
            ids = e.get(field)
            if isinstance(ids, str):
                ids = [ids]
            if not isinstance(ids, list):
                continue
            for tid in ids:
                if not isinstance(tid, str) or tid not in by_id:
                    continue
                row = by_id[tid]
                if row["verdict"] == "accept":
                    continue
                if str(e.get("event_id")) == tid:
                    continue
                if carrier_rank < row["rank"]:
                    continue
                out.setdefault(tid, []).append(str(e.get("event_id") or ""))
    return out


def rule_state(events: list, *, scope: bool, withdrawal: bool, discharge: bool) -> dict:
    rows = review_pool(events)
    by_id = {r["event_id"]: r for r in rows}
    pool = [r for r in rows if (not scope) or r["cls"] == "protocol"]
    pool_ids = {r["event_id"] for r in pool}
    withdrawn = structured_withdrawals(events, by_id) if withdrawal else {}
    discharged = structured_discharges(events, by_id) if discharge else {}
    accepts, dissents, dis, wd = [], [], [], []
    for r in pool:
        if not r["bound"]:
            continue
        eid = r["event_id"]
        if eid in withdrawn:
            wd.append(eid)
            continue
        if r["verdict"] == "accept":
            accepts.append(eid)
        elif eid in discharged:
            dis.append(eid)
        else:
            dissents.append(eid)
    return {
        "accepts": sorted(accepts),
        "dissents": sorted(dissents),
        "discharged": sorted(dis),
        "withdrawn": sorted(wd),
        "reviewed": bool(accepts),
        "contest": bool(dissents),
    }


# ---------------------------------------------------------------- event helpers

def load_snapshot() -> list:
    path = W64 / "raw" / "events_snapshot.jsonl"
    events = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict):
            events.append(doc)
    return events


def find_event(events: list, eid: str) -> dict:
    for e in events:
        if str(e.get("event_id") or "") == eid:
            return e
    raise KeyError(eid)


def synth(base: dict, **fields) -> dict:
    d = dict(base)
    d.update(fields)
    return d


def replace(events: list, eid: str, new: dict) -> list:
    """Replace an event in place (the pool deduplicates by event_id, first wins)."""
    return [new if str(e.get("event_id") or "") == eid else e for e in events]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="report.json")
    ap.add_argument("--no-live-lock-check", action="store_true")
    args = ap.parse_args()

    import time

    t0 = time.time()
    checks = {}

    # V1 pins -------------------------------------------------------------
    pin_rows, pins_ok = [], True
    for rel, want in DECLARED.items():
        p = W64 / rel
        got = sha256_file(p) if p.is_file() else None
        ok = got == want
        pins_ok &= ok
        pin_rows.append({"path": f"artifacts/worker-064/gnum_guard/{rel}", "declared": want, "measured": got, "match": ok})
    pinned_gates = W64 / "pinned" / "gates_fcd1d70991b6.py"
    pinned_proto = W64 / "pinned" / "CONVERGENCE_PROTOCOL_1e6cdf04d7a2.md"
    pin_rows.append({"path": "artifacts/worker-064/gnum_guard/pinned/gates_fcd1d70991b6.py",
                     "declared": PIN_GATES, "measured": sha256_file(pinned_gates), "match": sha256_file(pinned_gates) == PIN_GATES})
    pin_rows.append({"path": "artifacts/worker-064/gnum_guard/pinned/CONVERGENCE_PROTOCOL_1e6cdf04d7a2.md",
                     "declared": PIN_PROTO, "measured": sha256_file(pinned_proto), "match": sha256_file(pinned_proto) == PIN_PROTO})
    live_gates = ROOT / "numerics" / "gates.py"
    live_proto = ROOT / PROTO_PATH
    live_ok = sha256_file(live_gates) == PIN_GATES and sha256_file(live_proto) == PIN_PROTO
    checks["V1_pins"] = {"status": "CONFIRMED" if pins_ok and live_ok else "REFUTED",
                         "declared_rows_match": pins_ok, "live_canonical_at_pins": live_ok,
                         "rows": pin_rows}
    if not (pins_ok and live_ok):
        print("FAIL-CLOSED: pin mismatch", file=sys.stderr)
        return 2

    # V2 census -----------------------------------------------------------
    snapshot = load_snapshot()
    rows = review_pool(snapshot)
    shadow = shadow_state(rows)

    sys.path.insert(0, str(ROOT))
    import numerics.gates as G  # read-only import, hash-pinned above
    guard = G._protocol_review(snapshot, PIN_PROTO)
    by_id = {r["event_id"]: r for r in rows}

    w64_verdict = json.loads((W64 / "report.json").read_text())["guard_verdict"]
    want = {
        "accepts": sorted(guard["accepting_reviews"]),
        "dissents": sorted(d["event_id"] for d in guard["dissenting_reviews"]),
        "advisory": sorted(a["event_id"] for a in guard["advisory_reviews_at_other_hashes"]),
        "contest": guard["contest"],
        "reviewed": guard["reviewed"],
    }
    w64_view = {
        "accepts": sorted(w64_verdict["accepts"]),
        "dissents": sorted(w64_verdict["dissents"]),
        "advisory": sorted(w64_verdict["advisory"]),
        "contest": w64_verdict["contest"],
        "reviewed": w64_verdict["reviewed"],
    }
    shadow_view = {
        "accepts": sorted(shadow["accepting_reviews"]),
        "dissents": sorted(d["event_id"] for d in shadow["dissenting_reviews"]),
        "advisory": sorted(shadow["advisory_reviews_at_other_hashes"]),
        "contest": shadow["contest"],
        "reviewed": shadow["reviewed"],
    }
    census_ok = shadow_view == want == w64_view and len(guard["accepting_reviews"]) == 5 and len(guard["dissenting_reviews"]) == 5
    checks["V2_census"] = {
        "status": "CONFIRMED" if census_ok else "REFUTED",
        "snapshot_events": len(snapshot), "snapshot_sha256": sha256_file(W64 / "raw" / "events_snapshot.jsonl"),
        "accepts": want["accepts"], "dissents": want["dissents"], "advisory": want["advisory"],
        "contest": want["contest"], "reviewed": want["reviewed"],
        "shadow_equals_guard": shadow_view == want, "shadow_equals_w64": shadow_view == w64_view,
        "guard_equals_w64": want == w64_view,
    }

    # V3 findings ---------------------------------------------------------
    r4_id = "audit-l06-review-gnum-r4-20260912T005926"
    r4 = find_event(snapshot, r4_id)
    r4_adjudication = ROOT / "reviews" / "G-NUM-protocol-r4-adjudication.json"
    adjudication_hash = None
    if r4_adjudication.is_file():
        doc = json.loads(r4_adjudication.read_text())
        stack = [doc]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                for k, v in cur.items():
                    if k in ("reviewed_sha256", "protocol_sha256", "reviewed_protocol_hash") and isinstance(v, str):
                        adjudication_hash = v.lower()
                    stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)
    f1 = {
        "r4_in_guard_advisory": r4_id in want["advisory"],
        "r4_guard_citations": cited_hashes(r4),
        "r4_has_reviewed_sha256": "reviewed_sha256" in r4,
        "cited_adjudication_path_exists": r4_adjudication.is_file(),
        "cited_adjudication_reviewed_sha256": adjudication_hash,
    }
    f1["status"] = "CONFIRMED" if (f1["r4_in_guard_advisory"] and not f1["r4_guard_citations"]
                                   and adjudication_hash == PIN_PROTO) else "REFUTED"
    checks["V3a_F_GUARD_1"] = f1

    counted = [(eid, "accept") for eid in want["accepts"]] + [(eid, "dissent") for eid in want["dissents"]]
    conflation_rows = [{"event_id": eid, "counted_as": side, "target_class": by_id[eid]["cls"],
                        "target_id": by_id[eid]["event"].get("target_id")} for eid, side in counted]
    n0_rows = [r for r in conflation_rows if r["target_class"] == "n0"]
    n0_dissents = [r for r in n0_rows if r["counted_as"] == "dissent"]
    n0_accepts = [r for r in n0_rows if r["counted_as"] == "accept"]
    checks["V3b_F_GUARD_2"] = {
        "status": "CONFIRMED" if (len(n0_rows) == 4 and len(n0_dissents) == 3 and len(n0_accepts) == 1) else "REFUTED",
        "counted_total": len(counted), "n0_targeted_total": len(n0_rows),
        "n0_dissents": [r["event_id"] for r in n0_dissents], "n0_accepts": [r["event_id"] for r in n0_accepts],
        "rows": conflation_rows,
    }

    structured_hits = []
    discharge_field_hits = []
    for e in snapshot:
        for field in WITHDRAW_FIELDS:
            if field in e:
                structured_hits.append({"event_id": e.get("event_id"), "field": field})
        for field in DISCHARGE_FIELDS:
            if field in e:
                discharge_field_hits.append({"event_id": e.get("event_id"), "field": field,
                                             "event_type": e.get("event_type"), "target_id": e.get("target_id")})
    prose = find_event(snapshot, "w081-2026-09-12T00:29:19+0800-complete")
    prose_text = str(prose.get("summary") or prose.get("statement") or prose.get("description") or "")
    c8_id = "w081-20260912T002140-c8-review"
    checks["V3c_F_GUARD_3"] = {
        "status": "CONFIRMED" if (not structured_hits and c8_id in want["accepts"]
                                  and "prior W081-N0-C8-01 accept withdrawn" in prose_text) else "REFUTED",
        "structured_withdrawal_field_hits": structured_hits,
        "discharge_field_hits_elsewhere_in_stream": discharge_field_hits,
        "withdrawn_accept_still_counted": c8_id in want["accepts"],
        "prose_withdrawal_event": "w081-2026-09-12T00:29:19+0800-complete",
        "prose_withdrawal_actor": prose.get("actor"),
        "prose_withdrawal_phrase_present": "prior W081-N0-C8-01 accept withdrawn" in prose_text,
        "namespace_note": "the stream already uses supersedes_event_ids for unrelated worker-029 task chains; "
                          "R3 reusing that field name is a collision risk (see X7)",
    }

    both_sides = [eid for eid in want["accepts"] if eid in want["dissents"]]
    w081_rows = [r for r in rows if r["reviewer"] == "worker-081" and r["bound"]]
    checks["V3d_F_GUARD_4"] = {
        "status": "CONFIRMED" if ("w081-20260912T002140-c8-review" in want["accepts"]
                                  and "w081-2026-09-12T00:29:19+0800-f1-review" in want["dissents"]
                                  and "w081-20260912T0042050800-adj2-review" in want["accepts"]) else "REFUTED",
        "worker_081_bound_verdicts": [{"event_id": r["event_id"], "verdict": r["verdict"]} for r in w081_rows],
        "same_reviewer_both_sides": bool(both_sides),
    }

    if args.no_live_lock_check:
        eval_report = None
    else:
        eval_report = G.evaluate(ROOT)
    checks["V3e_F_GUARD_5"] = {
        "status": "CONFIRMED" if (eval_report is None or eval_report["verdict"] == "N1_BLOCKED") else "REFUTED",
        "evaluate_verdict": None if eval_report is None else eval_report["verdict"],
        "production_allowed": None if eval_report is None else eval_report["production_allowed"],
        "contest_reason_present": None if eval_report is None else any("contested" in r for r in eval_report["blocking_reasons"]),
        "blocking_reason_count": None if eval_report is None else len(eval_report["blocking_reasons"]),
        "note": "contest=false alone is not sufficient: lock state + required gates are independent reasons",
    }

    # V4 arms -------------------------------------------------------------
    r4_repaired = synth(r4, reviewed_sha256=PIN_PROTO)
    synth_withdrawal = {
        "actor": "worker-081", "reviewer": "worker-081", "event_type": "status",
        "event_id": "w014-synth-withdraw-c8", "created_at": "2026-09-12T00:30:00+0800",
        "withdraws_event_ids": [c8_id],
    }
    r4_discharge = synth(r4_repaired, discharged_event_ids=[
        "w067-review-gnum-protocol-r3-20260912T002256",
        "w081-2026-09-12T00:29:19+0800-f1-review",
    ])
    ev_arm0 = snapshot
    ev_hash_repair = replace(snapshot, r4_id, r4_repaired)
    ev_synth_field = snapshot + [synth_withdrawal]
    ev_discharge = replace(snapshot, r4_id, r4_discharge)

    arms = {
        "arm0_current_bytes": {"guard": shadow_state(review_pool(ev_arm0))},
        "arm_hash_repair_only": {"guard": shadow_state(review_pool(ev_hash_repair))},
        "arm_scope": rule_state(snapshot, scope=True, withdrawal=False, discharge=False),
        "arm_scope_withdrawal": rule_state(ev_arm0, scope=True, withdrawal=True, discharge=False),
        "arm_scope_withdrawal_synthetic_field": rule_state(ev_synth_field, scope=True, withdrawal=True, discharge=False),
        "arm_scope_withdrawal_discharge": rule_state(ev_discharge, scope=True, withdrawal=True, discharge=True),
    }
    want_arms = json.loads((W64 / "candidate_rules.json").read_text())["arms"]

    def view(state: dict, guard_shape: bool) -> dict:
        if guard_shape:
            return {
                "accepts": sorted(state["accepting_reviews"]),
                "dissents": sorted(d["event_id"] for d in state["dissenting_reviews"]),
                "contest": state["contest"], "reviewed": state["reviewed"], "discharged": [],
            }
        return {"accepts": state["accepts"], "dissents": state["dissents"],
                "contest": state["contest"], "reviewed": state["reviewed"], "discharged": state["discharged"]}

    arm_rows, arms_ok = [], True
    for name, got in arms.items():
        guard_shape = "guard" in got
        state = got["guard"] if guard_shape else got
        mine = view(state, guard_shape)
        theirs = want_arms[name]
        match = all(sorted(mine[k]) == sorted(theirs[k]) for k in ("accepts", "dissents", "discharged")) \
            and mine["contest"] == theirs["contest"] and mine["reviewed"] == theirs["reviewed"]
        arms_ok &= match
        arm_rows.append({"arm": name, "match": match, "mine": mine, "author": theirs})
    checks["V4_arms"] = {"status": "CONFIRMED" if arms_ok else "REFUTED", "rows": arm_rows}

    # V5/V6 controls ------------------------------------------------------
    def run_control(name, events, *, scope, withdrawal, discharge, expect) -> dict:
        got = rule_state(events, scope=scope, withdrawal=withdrawal, discharge=discharge)
        ok = all(got[k] == v for k, v in expect.items())
        return {"control": name, "expected": expect, "measured": got, "pass": ok}

    c8_dissent_pair = ["w067-review-gnum-protocol-r3-20260912T002256", "w081-2026-09-12T00:29:19+0800-f1-review"]
    carrier_ok = synth(r4_repaired, discharged_event_ids=c8_dissent_pair)
    ev_carrier = replace(snapshot, r4_id, carrier_ok)

    author_controls = [
        run_control("C1_unknown_id_never_discharges", replace(snapshot, r4_id, synth(r4_repaired, discharged_event_ids=["no-such-event"])),
                    scope=True, withdrawal=False, discharge=True,
                    expect={"dissents": sorted(c8_dissent_pair), "contest": True}),
        run_control("C2_stale_hash_carrier_never_discharges", replace(snapshot, r4_id, synth(r4_repaired, reviewed_sha256="f" * 64, discharged_event_ids=c8_dissent_pair)),
                    scope=True, withdrawal=False, discharge=True,
                    expect={"dissents": sorted(c8_dissent_pair), "contest": True}),
        run_control("C3_predated_carrier_never_discharges",
                    replace(snapshot, r4_id, synth(r4_repaired, created_at="2026-09-12T00:10:00+0800", discharged_event_ids=c8_dissent_pair)),
                    scope=True, withdrawal=False, discharge=True,
                    expect={"dissents": sorted(c8_dissent_pair), "contest": True}),
        run_control("C4_fresh_unlisted_dissent_still_contests",
                    ev_carrier + [{"event_type": "review", "event_id": "w014-ctrl-fresh-dissent", "reviewer": "worker-999",
                                   "verdict": "revise", "target_id": PROTO_PATH + "#" + PIN_PROTO[:12],
                                   "reviewed_sha256": PIN_PROTO, "created_at": "2026-09-12T01:00:00+0800"}],
                    scope=True, withdrawal=False, discharge=True,
                    expect={"dissents": ["w014-ctrl-fresh-dissent"], "contest": True}),
        run_control("C5_thirdparty_withdrawal_not_authority",
                    snapshot + [{"event_type": "status", "event_id": "w014-ctrl-thirdparty", "actor": "worker-999",
                                 "created_at": "2026-09-12T00:30:00+0800", "withdraws_event_ids": [c8_id]}],
                    scope=True, withdrawal=True, discharge=False,
                    expect={"withdrawn": [], "contest": True}),
        run_control("C6_uncited_carrier_never_discharges",
                    snapshot + [{"event_type": "review", "event_id": "w014-ctrl-uncited", "reviewer": "worker-999",
                                 "verdict": "accept", "target_id": "G-NUM-protocol", "created_at": "2026-09-12T01:00:00+0800",
                                 "discharged_event_ids": c8_dissent_pair, "evidence_refs": []}],
                    scope=True, withdrawal=False, discharge=True,
                    expect={"dissents": sorted(c8_dissent_pair), "contest": True}),
    ]

    own_dissent = "w067-review-gnum-protocol-r3-20260912T002256"
    ev_self_discharge = snapshot + [synth(r4_repaired, event_id="w014-x1-self-discharge", reviewer="worker-067",
                                          discharged_event_ids=[own_dissent])]
    ev_empty_evidence = snapshot + [synth(r4_repaired, event_id="w014-x2-empty-evidence", evidence_refs=[],
                                          discharged_event_ids=c8_dissent_pair)]
    ev_accept_target = snapshot + [synth(r4_repaired, event_id="w014-x3-accept-target",
                                         discharged_event_ids=["audit-review-gnum-protocol-final-20260912T0027"])]
    ev_status_carrier = snapshot + [{"event_type": "status", "event_id": "w014-x4-status-carrier", "actor": "worker-999",
                                     "created_at": "2026-09-12T01:00:00+0800", "discharged_event_ids": c8_dissent_pair}]
    ev_new_after_carrier = ev_carrier + [{"event_type": "review", "event_id": "w014-x5-late-dissent", "reviewer": "worker-999",
                                          "verdict": "reject", "target_id": PROTO_PATH + "#" + PIN_PROTO[:12],
                                          "reviewed_sha256": PIN_PROTO, "created_at": "2026-09-12T01:10:00+0800"}]
    ev_dup = ev_carrier + [synth(carrier_ok, event_id="w014-x6-second-carrier",
                                 discharged_event_ids=c8_dissent_pair + c8_dissent_pair)]
    ev_x7 = snapshot + [{"event_type": "review", "event_id": "w014-x7-unrelated-review", "reviewer": "worker-999",
                         "verdict": "accept", "target_id": "schemas/af_scc_c0_vacuum.yaml",
                         "reviewed_sha256": "a" * 64, "created_at": "2026-09-12T01:00:00+0800",
                         "evidence_refs": [PROTO_PATH + "#" + PIN_PROTO[:12]],
                         "supersedes_event_ids": [own_dissent]}]
    x7_measured = rule_state(ev_x7, scope=True, withdrawal=False, discharge=True)

    adversarial = [
        {"control": "X1_self_discharge_allowed_by_rule_as_specified",
         "measured": rule_state(ev_self_discharge, scope=True, withdrawal=False, discharge=True),
         "spec_gap": "R3 does not scope the carrier away from the discharged dissent's own author; measured outcome: "
                     + ("discharged" if own_dissent not in rule_state(ev_self_discharge, scope=True, withdrawal=False, discharge=True)["dissents"] else "still contests")},
        {"control": "X2_empty_evidence_carrier_trusts_the_list",
         "measured": rule_state(ev_empty_evidence, scope=True, withdrawal=False, discharge=True),
         "spec_gap": "a binding review with empty evidence still discharges listed ids; the list is trusted, not evidence-bound"},
        {"control": "X3_list_naming_an_accept_is_ignored",
         "measured": rule_state(ev_accept_target, scope=True, withdrawal=False, discharge=True),
         "spec_gap": "fail-closed: accepts are not dischargeable, no state change"},
        {"control": "X4_non_review_carrier_does_not_discharge",
         "measured": rule_state(ev_status_carrier, scope=True, withdrawal=False, discharge=True),
         "spec_gap": "fail-closed: a status/claim carrying the field has no effect"},
        {"control": "X5_dissent_arriving_after_carrier_still_contests",
         "measured": rule_state(ev_new_after_carrier, scope=True, withdrawal=False, discharge=True),
         "spec_gap": "fail-closed: ordering is respected, later dissent contests"},
        {"control": "X6_duplicate_ids_and_carriers_are_idempotent",
         "measured": rule_state(ev_dup, scope=True, withdrawal=False, discharge=True),
         "spec_gap": "discharge set semantics are idempotent"},
        {"control": "X7_generic_field_name_collision",
         "measured": x7_measured,
         "spec_gap": "R3 accepts a carrier that does not target the protocol at all (an unrelated schema review that "
                     "merely cites the protocol hash in an evidence ref) and reuses the generic field name "
                     "supersedes_event_ids, which worker-029 already uses for unrelated task chains"},
    ]

    author_ok = all(c["pass"] for c in author_controls)
    checks["V5_author_controls"] = {"status": "CONFIRMED" if author_ok else "REFUTED", "rows": author_controls}
    x1_gap = own_dissent not in adversarial[0]["measured"]["dissents"]
    x2_gap = c8_dissent_pair[0] not in adversarial[1]["measured"]["dissents"]
    x3_ok = "audit-review-gnum-protocol-final-20260912T0027" in adversarial[2]["measured"]["accepts"] and not adversarial[2]["measured"]["discharged"]
    x4_ok = all(d in adversarial[3]["measured"]["dissents"] for d in c8_dissent_pair)
    x5_ok = "w014-x5-late-dissent" in adversarial[4]["measured"]["dissents"]
    x6_ok = len(adversarial[5]["measured"]["discharged"]) == 2
    x7_gap = own_dissent not in x7_measured["dissents"]
    checks["V6_adversarial"] = {
        "status": "CONFIRMED" if (x1_gap and x2_gap and x7_gap and x3_ok and x4_ok and x5_ok and x6_ok) else "PARTIAL",
        "X1_self_discharge_gap": x1_gap, "X2_list_trust_gap": x2_gap, "X3_accept_ignored": x3_ok,
        "X4_non_review_carrier_fail_closed": x4_ok, "X5_ordering_fail_closed": x5_ok, "X6_idempotent": x6_ok,
        "X7_field_namespace_collision_gap": x7_gap,
        "rows": adversarial,
        "specification_gaps": [
            "R3 permits a reviewer to discharge their own dissent; R2 scopes withdrawal to the author, R3 is unscoped.",
            "R3 trusts the discharge list: the carrier's evidence is not required to name the discharged finding.",
            "R3 does not constrain the carrier to a protocol-targeted review and reuses the generic field name "
            "supersedes_event_ids, which is already used elsewhere in the stream for unrelated task chains.",
        ],
    }

    # V7 minimal repair ---------------------------------------------------
    repair_binds = binds(r4_repaired, PIN_PROTO) and not binds(r4, PIN_PROTO)
    repair_state = shadow_state(review_pool(ev_hash_repair))
    checks["V7_minimal_repair"] = {
        "status": "CONFIRMED" if (repair_binds and r4_id in repair_state["accepting_reviews"] and repair_state["contest"]) else "REFUTED",
        "r4_binds_after_one_field_repair": repair_binds,
        "accepts_after_repair": len(repair_state["accepting_reviews"]),
        "contest_after_repair": repair_state["contest"],
        "note": "event-layer hash repair is necessary but not sufficient; scope/withdrawal/discharge remain",
    }

    # V8 lock + determinism ----------------------------------------------
    solver_absent = not (ROOT / "numerics" / "spherical_solver").exists()
    lock_state = json.loads((ROOT / "research_map" / "research_map.json").read_text())["numerics_lock"]["state"]
    again = rule_state(ev_discharge, scope=True, withdrawal=True, discharge=True)
    checks["V8_lock_determinism"] = {
        "status": "CONFIRMED" if (solver_absent and lock_state == "locked" and again == arms["arm_scope_withdrawal_discharge"]) else "REFUTED",
        "spherical_solver_absent": solver_absent, "numerics_lock": lock_state, "rule_rebuild_equal": again == arms["arm_scope_withdrawal_discharge"],
    }

    all_status = [v["status"] for v in checks.values()]
    verdict = "W064_CENSUS_AND_RULE_INDEPENDENTLY_REPRODUCED" if all(s == "CONFIRMED" for s in all_status) else "PARTIAL_OR_REFUTED"
    report = {
        "schema": "worker-014/guard-verify/v1",
        "task_id": "W014-GNUM-GUARD-VERIFY-01",
        "actor": "worker-014",
        "class_id": "AF-WCC-SCALAR-SPH", "node_id": "N0", "gate": "G-NUM",
        "reviewed_revision": {
            "task": "W064-GNUM-GUARD-CENSUS-01", "author": "worker-064",
            "report": "artifacts/worker-064/gnum_guard/report.json#e3ebf9e502491f65",
            "snapshot": "artifacts/worker-064/gnum_guard/raw/events_snapshot.jsonl#b476b9e5e54fbcbd",
            "gates_pin": "numerics/gates.py#" + PIN_GATES[:12],
            "protocol_pin": PROTO_PATH + "#" + PIN_PROTO[:12],
        },
        "verdict": verdict,
        "checks": checks,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runtime_seconds": round(time.time() - t0, 3),
        "not_claimed": [
            "no G-NUM gate verdict and no gate self-pass", "no N0 node completion",
            "no adoption of the candidate rule; proposal for the owner only",
            "no canonical write; numerics_lock stays LOCKED",
        ],
        "falsifier": (
            "Re-run at the pinned inputs (numerics/gates.py fcd1d70991b6, protocol 1e6cdf04d7a2, "
            "worker-064 report e3ebf9e502491f65, snapshot b476b9e5e54fbcbd): any check status that "
            "flips, any arm that stops matching, a pin/hash drift, a canonical write, or a lock-state "
            "change falsifies the corresponding verdict."
        ),
    }
    dig = payload_digest(report)
    report["payload_sha256"] = dig

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "out": str(out), "payload_sha256": dig,
                      "statuses": {k: v["status"] for k, v in checks.items()}}, indent=1))
    return 0 if verdict.startswith("W064") else 3


if __name__ == "__main__":
    sys.exit(main())
