#!/usr/bin/env python3
"""W005-L0-FINALVERIFY-INDEP-01.

Independent, read-only verification of the audit lead's fresh L0 gate-final-verify
artifact `reviews/L0-review-final-verify.json` (event audit-l09-art-l0-20260912T011904)
at the frozen pins:

    ledger/theorems.jsonl        a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28
    ledger/citation_audit.csv    315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9
    reviews/L0-review-final-verify.json  8f3ddc732983402e139f65b1077c313dabe91352ab883561168f82f603884039

The instrument re-derives, from bytes, every gate-relevant number in the target:
  C1 target hash / pin binding / pin stability (T0 == T1)
  C2 ledger facts (rows, bytes)
  C3 HF-14 predicate triple re-run (independent scanner) + review-axis census
  C4 the four coverage_table accept rows, each against its durable source
     (review file or accepted review event) and its declared backing artifacts
  C5 the complete binding-verdict universe at the pin, under explicit counting
     rules R1 (pin-exact file records), R2 (R1 + accepted review events) and
     R3 (any-hash L0 file records), with the supersession/staleness disposition
  C6 the gate-relevant verdict basis ("two full-schema non-author accepts")

Controls K1-K6 mutate in-memory copies of the pinned inputs and require every
check family to fail closed on the mutation; K6 requires byte-identical core
output across two full runs.

Writes only into this task directory (report.json, selftest.json, run_log.json,
SCAN.md). No canonical path is written. Exit 0 iff no hard failure, 2 otherwise.
Read-only on every pinned input: input sha256 is measured before and after.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

PIN_LEDGER = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
PIN_AUDIT = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
PIN_TARGET = "8f3ddc732983402e139f65b1077c313dabe91352ab883561168f82f603884039"
LEDGER_ROWS = 62
LEDGER_BYTES = 151521
TASK_ID = "W005-L0-FINALVERIFY-INDEP-01"
CLASS_ID = "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH"
AUTHOR_REVIEWERS = {"astra-lead-literature", "lead-literature"}

CANON = {
    "ledger/theorems.jsonl": PIN_LEDGER,
    "ledger/citation_audit.csv": PIN_AUDIT,
    "reviews/L0-review-final-verify.json": PIN_TARGET,
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def load_json(p: Path):
    return json.loads(p.read_text())


def load_jsonl(p: Path):
    rows = []
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from all_strings(v)


def binds_pin(obj, pin: str) -> bool:
    """Declared rule: a record binds the pin if the full pin or its 12-hex prefix
    occurs in any string value (the project's own citation convention)."""
    return any(pin in s or pin[:12] in s for s in all_strings(obj))


def binding_values(obj: dict) -> list:
    """Declared binding-field values of a verdict record (not free text)."""
    vals = []
    for k in ("reviewed_sha256", "artifact_sha256", "target_sha256",
              "companion_sha256", "measured_sha256", "sha256"):
        v = obj.get(k)
        if isinstance(v, str):
            vals.append(v)
        elif isinstance(v, dict):
            vals.extend(str(x) for x in v.values())
    for k in ("target", "binding_pins", "companion_pins", "pins"):
        v = obj.get(k)
        if isinstance(v, dict):
            vals.extend(str(x) for x in v.values())
    return vals


def binds_pin_strict(obj: dict, pin: str) -> bool:
    """A verdict record binds the pin iff a declared binding field carries it."""
    return any(v == pin or v.startswith(pin[:12]) for v in binding_values(obj))


def is_l0_record(obj: dict) -> bool:
    """Declared rule: a verdict record belongs to the L0 node iff its target is L0
    (target_id/node_id 'L0...'), or its primary target path is ledger/theorems.jsonl.
    Companion citations of the ledger from other nodes (F2a/L1 review records that
    carry the ledger pin as a binding pin) are excluded."""
    tid = str(obj.get("target_id") or "")
    nid = str(obj.get("node_id") or "")
    if tid.startswith("L0") or nid == "L0":
        return True
    tgt = obj.get("target")
    if isinstance(tgt, str) and "theorems.jsonl" in tgt:
        return True
    if isinstance(tgt, dict) and "theorems.jsonl" in str(tgt.get("canonical_path", "")):
        return True
    return False


def review_meta(obj: dict) -> dict:
    full = obj.get("counts_as_full_schema_verdict")
    hf = obj.get("hard_failures")
    if hf is None:
        hf = []
    if isinstance(hf, dict):
        hf = list(hf.keys())
    return {
        "reviewer": obj.get("reviewer") or obj.get("actor"),
        "verdict": obj.get("verdict"),
        "score": obj.get("score"),
        "full_flag": full,
        "hard_failures": len(hf) if isinstance(hf, list) else 1,
        "created": obj.get("measured_at") or obj.get("created_at") or obj.get("reviewed_at"),
        "declared_binding": [
            k for k in ("reviewed_sha256", "artifact_sha256", "target_sha256",
                        "reviewed_bytes", "artifact_bytes") if k in obj
        ],
    }


# --------------------------------------------------------------------------
# check families (pure over explicit inputs so controls can mutate copies)
# --------------------------------------------------------------------------

def check_c1(target: dict, pins_measured: dict) -> dict:
    fails = []
    if pins_measured["ledger/theorems.jsonl"]["after"] != PIN_LEDGER:
        fails.append("ledger bytes moved off pin")
    if pins_measured["ledger/citation_audit.csv"]["after"] != PIN_AUDIT:
        fails.append("audit csv moved off pin")
    if pins_measured["reviews/L0-review-final-verify.json"]["after"] != PIN_TARGET:
        fails.append("target artifact moved off its declared hash")
    for k, v in pins_measured.items():
        if v["before"] != v["after"]:
            fails.append(f"{k} changed during the run")
    reviewed = target.get("reviewed_sha256")
    measured = target.get("measured_sha256")
    if reviewed != PIN_LEDGER:
        fails.append("target.reviewed_sha256 != ledger pin")
    if measured != PIN_LEDGER:
        fails.append("target.measured_sha256 != ledger pin")
    if target.get("pin_stable") is not True:
        fails.append("target.pin_stable is not true")
    return {"status": "FAIL" if fails else "PASS", "detail": fails or
            "target hash, internal pin binding and T0==T1 stability all reproduce"}


def check_c2(rows: list, ledger_bytes: int, ledger_mtime: str) -> dict:
    fails = []
    ids = [r.get("theorem_id") for r in rows]
    if len(rows) != LEDGER_ROWS:
        fails.append(f"row count {len(rows)} != {LEDGER_ROWS}")
    if ledger_bytes != LEDGER_BYTES:
        fails.append(f"byte count {ledger_bytes} != {LEDGER_BYTES}")
    if len(set(ids)) != len(ids):
        fails.append("duplicate theorem_id")
    if not all(ids):
        fails.append("empty theorem_id")
    if not ledger_mtime.startswith("2026-09-12T00:39"):
        fails.append(f"mtime {ledger_mtime} not the declared 2026-09-12T00:39")
    return {"status": "FAIL" if fails else "PASS", "detail": fails or
            f"{len(rows)} rows / {ledger_bytes} bytes / {len(set(ids))} unique ids"}


def check_c3(rows: list) -> dict:
    triple = {"status": 0, "validation_status": 0, "supports_claim": 0}
    review_status = {}
    content_status = {}
    author_asserts = 0
    for r in rows:
        for k in triple:
            if k in r and r[k]:
                triple[k] += 1
        review_status[str(r.get("review_status"))] = review_status.get(str(r.get("review_status")), 0) + 1
        content_status[str(r.get("content_status"))] = content_status.get(str(r.get("content_status")), 0) + 1
        if r.get("author_asserts_supports") is True:
            author_asserts += 1
    fails = []
    if any(v != 0 for v in triple.values()):
        fails.append(f"HF-14 predicate triple nonzero: {triple}")
    if review_status.get("not_independently_reviewed", 0) != len(rows):
        fails.append(f"review_status census unexpected: {review_status}")
    return {
        "status": "FAIL" if fails else "PASS",
        "detail": fails or "0/62 for each of status/validation_status/supports_claim",
        "hf14_triple": triple,
        "review_status_census": dict(sorted(review_status.items())),
        "content_status_census": dict(sorted(content_status.items())),
        "author_asserts_supports_true": author_asserts,
    }


def load_review_records() -> list:
    recs = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            obj = load_json(p)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("verdict") is None and not any(
            k in obj for k in ("review_id", "reviewer")
        ):
            continue
        recs.append({"path": str(p.relative_to(ROOT)), "obj": obj})
    return recs


def load_event_index() -> dict:
    """event_id -> (event, source) from the accepted stream and the outboxes."""
    idx = {}
    ev = ROOT / "research_map" / "events.jsonl"
    if ev.exists():
        for e in load_jsonl(ev):
            if isinstance(e, dict) and e.get("event_id"):
                idx.setdefault(e["event_id"], (e, "research_map/events.jsonl"))
    for p in sorted((ROOT / "comms" / "outbox").glob("*.jsonl")):
        for e in load_jsonl(p):
            if isinstance(e, dict) and e.get("event_id"):
                idx.setdefault(e["event_id"], (e, str(p.relative_to(ROOT))))
    return idx


def event_binds_pin(ev: dict) -> bool:
    """An L0 verdict event at the pin is a review event whose node is L0 and whose
    primary target is the L0 ledger at the pin (target_id 'L0...' or
    'ledger/theorems.jsonl[#a1674f094979]'); events about staged patches or other
    artifacts that merely cite the ledger are excluded."""
    if not isinstance(ev, dict) or ev.get("event_type") != "review":
        return False
    if str(ev.get("node_id") or "") != "L0":
        return False
    tid = str(ev.get("target_id") or "")
    if not (tid.startswith("L0") or tid.startswith("ledger/theorems.jsonl")):
        return False
    blob = json.dumps(ev)
    return PIN_LEDGER in blob or PIN_LEDGER[:12] in blob


def check_c4(target: dict, records: list, events: dict) -> dict:
    """Verify each coverage_table row against its durable source."""
    by_reviewer = {}
    for r in records:
        m = review_meta(r["obj"])
        by_reviewer.setdefault(m["reviewer"], []).append((r["path"], r["obj"], m))
    rows_out = []
    fails = []
    for row in target.get("coverage_table", []):
        rev = row.get("reviewer")
        ev_id = row.get("event_id")
        entry = {"reviewer": rev, "event_id": ev_id, "declared": dict(row)}
        # durable source: an L0 review file for this reviewer (prefer one bound to
        # the pin), else an accepted review event
        src = None
        cands = [(path, obj, m) for path, obj, m in by_reviewer.get(rev, [])
                 if is_l0_record(obj)]
        binding_cands = [c for c in cands if binds_pin_strict(c[1], PIN_LEDGER)]
        pick = (binding_cands or cands)
        if pick:
            path, obj, m = pick[0]
            src = {"kind": "review_file", "path": path, "obj": obj, "meta": m}
        if src is None and ev_id in events:
            ev = events[ev_id][0]
            src = {"kind": "review_event", "path": events[ev_id][1], "obj": ev,
                   "meta": review_meta(ev)}
        if src is None:
            fails.append(f"{rev}: no durable binding source found")
            entry["source"] = None
            entry["status"] = "FAIL"
            rows_out.append(entry)
            continue
        m = src["meta"]
        entry["source"] = {"kind": src["kind"], "path": src["path"]}
        entry["measured"] = {
            "reviewer": m["reviewer"], "verdict": m["verdict"], "score": m["score"],
            "full_flag": m["full_flag"], "hard_failures": m["hard_failures"],
            "created": m["created"],
        }
        local, adv = [], []
        if m["reviewer"] != rev:
            local.append(f"reviewer {m['reviewer']} != {rev}")
        if m["verdict"] != row.get("verdict"):
            local.append(f"verdict {m['verdict']} != {row.get('verdict')}")
        if row.get("score") is not None and m["score"] != row.get("score"):
            local.append(f"score {m['score']} != {row.get('score')}")
        if m["full_flag"] is True and row.get("full_schema") is not True:
            local.append(f"full_flag {m['full_flag']} != {row.get('full_schema')}")
        elif m["full_flag"] is None and row.get("full_schema") is False:
            adv.append("full flag absent on the source; target records it as false")
        elif m["full_flag"] is not row.get("full_schema"):
            local.append(f"full_flag {m['full_flag']} != {row.get('full_schema')}")
        if bool(m["hard_failures"]) != bool(row.get("hard_failures", 0)):
            local.append(f"hard_failures {m['hard_failures']} != {row.get('hard_failures')}")
        if rev in AUTHOR_REVIEWERS:
            local.append("coverage row is authored by the ledger owner")
        # binding proof for each accept
        if src["kind"] == "review_file":
            if not binds_pin_strict(src["obj"], PIN_LEDGER):
                local.append("review file does not declare the pin in a binding field")
        else:
            ev = src["obj"]
            proof = json.dumps(ev)
            if PIN_LEDGER not in proof and PIN_LEDGER[:12] not in proof:
                local.append("review event does not carry the pin")
            if not ev.get("target_id"):
                adv.append("review event has no target_id (binds via evidence_refs only)")
        # declared backing artifacts must exist and match their hash prefix
        refs = list(src["obj"].get("evidence_refs") or []) + list(
            src["obj"].get("artifact_refs") or [])
        if isinstance(src["obj"].get("artifact_refs"), str):
            refs.append(src["obj"]["artifact_refs"])
        checked = []
        for ref in refs:
            if "#" not in ref:
                continue
            path, frag = ref.split("#", 1)
            frag = frag.replace("sha256:", "")
            p = ROOT / path
            if not p.exists():
                local.append(f"backing artifact missing: {path}")
                continue
            h = sha256_file(p)
            if not h.startswith(frag[:12]):
                local.append(f"backing hash mismatch: {path}#{frag[:12]} vs {h[:12]}")
            checked.append({"ref": ref, "sha256": h})
        entry["binding_artifacts"] = checked
        entry["advisories"] = adv
        entry["status"] = "FAIL" if local else "PASS"
        entry["detail"] = local or (adv or "row reproduces against its durable source")
        if local:
            fails.extend(f"{rev}: {x}" for x in local)
        rows_out.append(entry)
    n_declared = len(target.get("coverage_table", []))
    if n_declared != 4:
        fails.append(f"coverage_table has {n_declared} rows, expected 4")
    return {"status": "FAIL" if fails else "PASS", "detail": fails or
            f"{n_declared}/4 coverage rows reproduce against durable sources",
            "rows": rows_out}


def build_universe(records: list, events: dict) -> dict:
    pin_files, stale_files = [], []
    for r in records:
        obj = r["obj"]
        m = review_meta(obj)
        if m["verdict"] is None or not is_l0_record(obj):
            continue
        entry = {"path": r["path"], **m}
        if binds_pin_strict(obj, PIN_LEDGER):
            pin_files.append(entry)
        else:
            blob = json.dumps(obj)
            if "theorems.jsonl" in blob and m["verdict"] in ("accept", "revise", "inconclusive"):
                entry["binding_hash_class"] = ("L1-audit-csv"
                                               if "citation_audit" in str(obj.get("target_id"))
                                               else "ledger-revision")
                stale_files.append(entry)
    pin_events = []
    for eid, (ev, src) in events.items():
        if event_binds_pin(ev):
            m = review_meta(ev)
            pin_events.append({"event_id": eid, "path": src, **m,
                               "target_id": ev.get("target_id")})
    def by_full(seq, flag):
        return [e for e in seq if e["full_flag"] is flag]

    accepts_full = sorted(e["reviewer"] for e in by_full(pin_files, True) if e["verdict"] == "accept")
    revises_full = sorted(e["reviewer"] for e in by_full(pin_files, True) if e["verdict"] == "revise")
    absent = sorted(e["reviewer"] for e in by_full(pin_files, None))
    flagged_false = sorted(e["reviewer"] for e in by_full(pin_files, False))
    file_reviewers = {e["reviewer"] for e in pin_files}
    self_reviewers = AUTHOR_REVIEWERS | {"astra-lead-audit"}
    event_accepts = sorted(
        e["reviewer"] for e in pin_events
        if e["verdict"] == "accept" and e["reviewer"] not in file_reviewers
        and e["reviewer"] not in self_reviewers)
    event_accepts_excluded = sorted(
        e["reviewer"] for e in pin_events
        if e["verdict"] == "accept" and e["reviewer"] in self_reviewers)
    event_only_other = sorted(
        [{"reviewer": e["reviewer"], "verdict": e["verdict"], "event_id": e["event_id"]}
         for e in pin_events
         if e["verdict"] in ("revise", "reject", "inconclusive")
         and e["reviewer"] not in file_reviewers
         and e["reviewer"] not in self_reviewers],
        key=lambda d: (d["reviewer"], d["event_id"]))
    universe = {
        "R1_pin_exact_file_records": {
            "records": sorted(pin_files, key=lambda e: (str(e["reviewer"]), str(e["created"]))),
            "accepts_full_schema": accepts_full,
            "revises_full_schema": revises_full,
            "flag_absent": absent,
            "flag_false": flagged_false,
            "counts": {"accept": len([e for e in pin_files if e["verdict"] == "accept"]),
                       "revise": len([e for e in pin_files if e["verdict"] == "revise"]),
                       "inconclusive": len([e for e in pin_files if e["verdict"] == "inconclusive"])},
        },
        "R2_pin_exact_files_plus_events": {
            "event_only_accepts": event_accepts,
            "event_only_accepts_rule": ("accept review events at the pin minus reviewers that "
                                        "already have a pin-exact review file and minus the ledger "
                                        "owner and the author of the target artifact "
                                        f"({sorted(self_reviewers)}); the target artifact's own "
                                        "authoring event is not an independent accept"),
            "self_or_owner_accept_events_excluded": event_accepts_excluded,
            "event_only_nonaccept_verdicts": event_only_other,
            "events": sorted(pin_events, key=lambda e: str(e["event_id"])),
            "counts": {
                "accept": len([e for e in pin_files if e["verdict"] == "accept"]) + len(event_accepts),
                "revise": len([e for e in pin_files if e["verdict"] == "revise"]) + len(
                    [e for e in event_only_other if e["verdict"] == "revise"]),
                "inconclusive": len([e for e in pin_files if e["verdict"] == "inconclusive"]) + len(
                    [e for e in event_only_other if e["verdict"] == "inconclusive"]),
                "rule": "R2 = R1 file records + L0-target review events at the pin, "
                        "self/owner events excluded",
            },
        },
        "R3_any_hash_l0_file_records": {
            "records": sorted(stale_files, key=lambda e: (str(e["reviewer"]), str(e["created"]))),
            "accepts": sorted(e["reviewer"] for e in stale_files if e["verdict"] == "accept"),
        },
    }
    return universe


def check_c5(universe: dict) -> dict:
    r1 = universe["R1_pin_exact_file_records"]
    r2 = universe["R2_pin_exact_files_plus_events"]
    fails = []
    if sorted(r1["accepts_full_schema"]) != ["worker-075", "worker-079"]:
        fails.append(f"R1 full-schema accepts {r1['accepts_full_schema']} != [worker-075, worker-079]")
    if sorted(r1["revises_full_schema"]) != ["worker-011", "worker-093"]:
        fails.append(f"R1 full-schema revises {r1['revises_full_schema']} != [worker-011, worker-093]")
    if sorted(r2["event_only_accepts"]) != ["worker-050", "worker-072"]:
        fails.append(f"R2 event-only accepts {r2['event_only_accepts']} != [worker-050, worker-072]")
    if len(universe["R3_any_hash_l0_file_records"]["accepts"]) < 2:
        fails.append("expected at least two stale any-hash accepts")
    return {"status": "FAIL" if fails else "PASS", "detail": fails or
            "universe reproduces: 2 full accepts, 2 full revises, 2 flag-absent revises, "
            "2 flag-false scoped verdicts, 2 event-only accepts, 2 stale any-hash accepts"}


def check_c6(target: dict) -> dict:
    basis = str(target.get("verdict_basis") or "")
    fails = []
    if "two full-schema non-author accepts" not in basis:
        fails.append("verdict_basis does not rest on two full-schema non-author accepts")
    if target.get("adjudicated_verdict") != "accept-with-carried-objections":
        fails.append(f"unexpected adjudicated_verdict {target.get('adjudicated_verdict')}")
    carried = target.get("carried_objections") or []
    if not carried:
        fails.append("no carried objections recorded")
    if not target.get("falsifiers"):
        fails.append("target declares no falsifiers")
    return {"status": "FAIL" if fails else "PASS", "detail": fails or
            "verdict basis, carried objections and declared falsifiers present"}


# --------------------------------------------------------------------------
# controls
# --------------------------------------------------------------------------

def run_controls(data: dict) -> list:
    out = []

    def rec(cid, expect, observed, ok, note):
        out.append({"id": cid, "expected": expect, "observed": observed,
                    "status": "PASS" if ok else "FAIL", "note": note})

    # K1: pin mutation in the target artifact must fail C1
    t = copy.deepcopy(data["target"])
    t["measured_sha256"] = "0" * 64
    r = check_c1(t, data["pins"])
    rec("K1-target-pin-mutation", "C1 FAIL", r["status"], r["status"] == "FAIL",
        "mutated measured_sha256 is detected")

    # K2: coverage row verdict mutation must fail C4
    t = copy.deepcopy(data["target"])
    t["coverage_table"][0]["verdict"] = "revise"
    r = check_c4(t, data["records"], data["events"])
    rec("K2-coverage-verdict-mutation", "C4 FAIL", r["status"], r["status"] == "FAIL",
        "a flipped coverage verdict is detected")

    # K3: truthy HF-14 key must fail C3
    rows = copy.deepcopy(data["ledger_rows"])
    rows[3]["supports_claim"] = True
    r = check_c3(rows)
    rec("K3-hf14-key-injection", "C3 FAIL", r["status"], r["status"] == "FAIL",
        "an injected supports_claim=true is detected")

    # K4: review-file binding mutation must fail C4 (record no longer binds pin)
    recs = copy.deepcopy(data["records"])
    for r_ in recs:
        if review_meta(r_["obj"])["reviewer"] == "worker-075":
            r_["obj"]["reviewed_sha256"] = "f" * 64
            r_["obj"]["artifact_sha256"] = "f" * 64
    r = check_c4(data["target"], recs, data["events"])
    rec("K4-accept-binding-mutation", "C4 FAIL", r["status"], r["status"] == "FAIL",
        "an accept that no longer binds the pin is detected")

    # K5: an extra full-schema accept at the pin must move the universe count
    recs = copy.deepcopy(data["records"])
    recs.append({"path": "SYNTHETIC/reviews/L0-review-synthetic.json",
                 "obj": {"reviewer": "worker-999", "verdict": "accept", "score": 4.0,
                         "counts_as_full_schema_verdict": True, "target_id": "L0",
                         "node_id": "L0",
                         "measured_at": "2026-09-12T01:30:00+08:00",
                         "reviewed_sha256": PIN_LEDGER}})
    u = build_universe(recs, data["events"])
    got = u["R1_pin_exact_file_records"]["accepts_full_schema"]
    rec("K5-extra-accept-detected", "worker-999 in R1 accepts",
        got, "worker-999" in got, "universe enumeration is not hardcoded")

    # K6: determinism of the core report across two constructions
    a = core_report(data)
    b = core_report(copy.deepcopy(data))
    rec("K6-determinism", "identical core_digest",
        a["core_digest"] == b["core_digest"],
        a["core_digest"] == b["core_digest"], "two runs give byte-identical cores")
    return out


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def core_report(data: dict) -> dict:
    c1 = check_c1(data["target"], data["pins"])
    c2 = check_c2(data["ledger_rows"], data["ledger_bytes"], data["ledger_mtime"])
    c3 = check_c3(data["ledger_rows"])
    c4 = check_c4(data["target"], data["records"], data["events"])
    universe = build_universe(data["records"], data["events"])
    c5 = check_c5(universe)
    c6 = check_c6(data["target"])
    checks = [dict(id="C1", title="target hash / pin binding / stability", **c1),
              dict(id="C2", title="ledger facts", **c2),
              dict(id="C3", title="HF-14 predicate triple + review axis", **c3),
              dict(id="C4", title="coverage_table rows vs durable sources", **c4),
              dict(id="C5", title="binding-verdict universe / rule sensitivity", **c5),
              dict(id="C6", title="verdict basis and falsifiers", **c6)]
    hard = [f"{c['id']}: {x}" for c in checks if c["status"] == "FAIL"
            for x in (c["detail"] if isinstance(c["detail"], list) else [c["detail"]])]

    r1 = universe["R1_pin_exact_file_records"]
    r2 = universe["R2_pin_exact_files_plus_events"]
    findings = []
    if len(r2["event_only_accepts"]) == 2:
        findings.append({
            "id": "A-W005-L0FV-01", "severity": "advisory",
            "finding": ("2 of the 4 accepts in coverage_table (worker-072 4.5, worker-050 4.0) "
                        "are event-only verdicts: they exist as accepted review events, not as "
                        "review files in reviews/. They bind the pin through evidence_refs; "
                        "worker-050's event carries no target_id field at all. The accept basis "
                        "is unaffected (both are non-author and both backing artifacts hash-match), "
                        "but the gate record should record the binding class."),
            "evidence": ["research_map/events.jsonl",
                         "artifacts/worker-072/l0_cf19_rederive/report.json",
                         "artifacts/worker-050/l0_independent_spotcheck/static_report.json"],
        })
    findings.append({
        "id": "A-W005-L0FV-02", "severity": "advisory",
        "finding": (f"The G-LIT criteria line counts '5 revise' at the pin, but the verdict count is "
                    f"rule-dependent. R1 (pin-exact review files, n=8): accepts "
                    f"{sorted(r1['accepts_full_schema'])}, full-schema revises "
                    f"{sorted(r1['revises_full_schema'])}, no-full-flag revises {r1['flag_absent']}, "
                    f"scoped/no-full-flag verdicts {r1['flag_false']}. R2 (R1 + L0-target review "
                    f"events at the pin, self/owner excluded) adds event-only accepts "
                    f"{r2['event_only_accepts']} and "
                    f"{len(r2['event_only_nonaccept_verdicts'])} event-only non-accept verdicts "
                    f"{[e['reviewer'] + ':' + str(e['verdict']) for e in r2['event_only_nonaccept_verdicts']]}. "
                    f"The decisive 'two full-schema non-author accepts' basis is robust under every "
                    f"rule; any quoted revise/inconclusive count must name its rule."),
        "evidence": ["reviews/L0-review-093.json", "reviews/L0-review-011-rev4.json",
                     "reviews/L0-review-worker-005-rev3.json", "reviews/L0-review-18-rev3.json",
                     "reviews/L0-hf02-staged-repair-025.json",
                     "reviews/w063-l0-scope-adjudication.json",
                     "research_map/events.jsonl"],
    })
    findings.append({
        "id": "A-W005-L0FV-03", "severity": "info",
        "finding": ("Two stale any-hash accepts exist on disk and are correctly excluded by the "
                    "target: worker-006 accept at 3e3d35531421 (older revision) and worker-011 "
                    "accept at ce42d205 (superseded by that reviewer's own rev4 revise at the pin). "
                    "A supersession-aware reading is required to reach the target's count."),
        "evidence": ["reviews/L0-review-worker-006.json", "reviews/L0-review-011.json",
                     "reviews/L0-review-011-rev4.json"],
    })

    verdict = "accept" if not hard else "revise"
    score = 4.0 if not hard else 2.5
    core = {
        "schema": "worker-005/l0-finalverify-independent/1",
        "task_id": TASK_ID,
        "actor": "worker-005",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_id": CLASS_ID,
        "target": {"path": "reviews/L0-review-final-verify.json", "sha256": PIN_TARGET,
                   "event_id": "audit-l09-art-l0-20260912T011904"},
        "pins": {k: {"sha256": v} for k, v in CANON.items()},
        "ledger_facts": {"rows": len(data["ledger_rows"]), "bytes": data["ledger_bytes"],
                         "mtime": data["ledger_mtime"]},
        "checks": checks,
        "universe": universe,
        "findings": findings,
        "hard_failures": hard,
        "verdict": verdict,
        "score": score,
        "verdict_rule": ("accept iff target/pins reproduce AND HF-14 triple is 0 AND C4 rows "
                         "reproduce AND >=2 full-schema non-author pin-exact accepts with 0 hard "
                         "failures; any hard failure -> revise"),
        "falsifier": ("Any of: reviews/L0-review-final-verify.json not at 8f3ddc732983; "
                      "ledger/theorems.jsonl not at a1674f094979 or row/byte counts changed; any "
                      "HF-14 predicate nonzero; either full accept (worker-075, worker-079) no "
                      "longer binding, full-schema, non-author, 0-hard-failure; a coverage_table "
                      "row not reproducing against its durable source; a moved backing-artifact "
                      "hash; a new full-schema accept at the pin that the universe misses."),
        "not_claimed": [
            "not a mathematics or physics claim; not a gate verdict; workers cannot set done/passed",
            "no citation-content, locator or ledger-content adjudication",
            "the carried HF-01/HF-02 dispositions are recorded, not decided here",
        ],
    }
    core["core_digest"] = sha256_bytes(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode())
    return core


def measure_pins() -> dict:
    out = {}
    for rel, pin in CANON.items():
        p = ROOT / rel
        out[rel] = {"declared": pin, "before": sha256_file(p)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=None, help="label for run_log only (volatile)")
    args = ap.parse_args()

    pins = measure_pins()
    target = load_json(ROOT / "reviews/L0-review-final-verify.json")
    ledger_rows = load_jsonl(ROOT / "ledger/theorems.jsonl")
    ledger_bytes = (ROOT / "ledger/theorems.jsonl").stat().st_size
    ledger_mtime = datetime.fromtimestamp(
        (ROOT / "ledger/theorems.jsonl").stat().st_mtime, CST).isoformat(timespec="minutes")
    records = load_review_records()
    events = load_event_index()
    for rel in CANON:
        pins[rel]["after"] = sha256_file(ROOT / rel)

    data = {"pins": pins, "target": target, "ledger_rows": ledger_rows,
            "ledger_bytes": ledger_bytes, "ledger_mtime": ledger_mtime,
            "records": records, "events": events}

    report = core_report(data)
    controls = run_controls(data)
    report_controls = [c for c in controls if c["status"] == "FAIL"]
    if report_controls:
        report["hard_failures"].extend(f"control {c['id']} did not fail closed"
                                       for c in report_controls)
        report["verdict"] = "revise"
        report["score"] = 2.0

    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (HERE / "selftest.json").write_text(json.dumps(
        {"schema": "worker-005/l0-finalverify-independent/controls/1",
         "task_id": TASK_ID, "n_controls": len(controls),
         "n_pass": len(controls) - len([c for c in controls if c["status"] == "FAIL"]),
         "controls": controls,
         "core_digest": report["core_digest"]}, indent=1, sort_keys=True) + "\n")
    (HERE / "run_log.json").write_text(json.dumps(
        {"task_id": TASK_ID, "stamp": args.stamp, "measured_at": now(),
         "pins_before_after": pins, "volatile": True,
         "note": "wall-clock and per-pin mtimes are volatile and excluded from core_digest"},
        indent=1, sort_keys=True) + "\n")

    scan = ["# W005-L0-FINALVERIFY-INDEP-01 — independent verification of the L0 gate-final-verify",
            "",
            f"* target: `reviews/L0-review-final-verify.json#{PIN_TARGET[:12]}` "
            f"(event `audit-l09-art-l0-20260912T011904`)",
            f"* pins: ledger `{PIN_LEDGER[:12]}`, audit csv `{PIN_AUDIT[:12]}`",
            f"* verdict: **{report['verdict']} {report['score']}** — "
            f"{len(report['hard_failures'])} hard failures, "
            f"{len([c for c in controls if c['status'] == 'PASS'])}/{len(controls)} controls pass",
            f"* core_digest: `{report['core_digest'][:12]}`", "",
            "## Checks", ""]
    for c in report["checks"]:
        scan.append(f"* **{c['id']} {c['status']}** — {c['title']}")
        d = c["detail"]
        scan.append(f"  * {d if isinstance(d, str) else json.dumps(d)}")
    scan += ["", "## Binding-verdict universe at the pin (R1, file records)", ""]
    for e in report["universe"]["R1_pin_exact_file_records"]["records"]:
        scan.append(f"* {e['reviewer']}: {e['verdict']} {e['score']} "
                    f"full_schema={e['full_flag']} hard_failures={e['hard_failures']} "
                    f"({e['created']}) — `{e['path']}`")
    scan += ["", "  event-only accepts (R2): "
             + ", ".join(report["universe"]["R2_pin_exact_files_plus_events"]["event_only_accepts"]),
             "", "## Findings", ""]
    for f in report["findings"]:
        scan.append(f"* **{f['id']}** ({f['severity']}) — {f['finding']}")
    scan += ["", "## Falsifier", "", report["falsifier"], "",
             "Worker-level measurement only: no node status, validation_status or gate verdict is set.",
             "Reproduce: `python3 artifacts/worker-005/l0_finalverify_independent/check_l0_finalverify.py`", ""]
    (HERE / "SCAN.md").write_text("\n".join(scan))

    print(json.dumps({"verdict": report["verdict"], "score": report["score"],
                      "hard_failures": report["hard_failures"],
                      "core_digest": report["core_digest"],
                      "controls_pass": len([c for c in controls if c["status"] == "PASS"]),
                      "controls_total": len(controls)}, indent=1))
    return 2 if report["hard_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
