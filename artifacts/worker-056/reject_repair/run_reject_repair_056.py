#!/usr/bin/env python3
"""W056-REJECT-REPAIR-01 — reject-stream loss repair instrument (bounded, read-only).

Task
----
One bounded, class-bound task: turn the *measured* defect in `comms/rejected.jsonl`
into the missing repair half — a semantics-preserving repair map, a round-trip-validated
recovery bundle, and a reusable pre-flight gate — without writing to any canonical path.

Division of labour (checked before starting, to avoid duplication, CF-12)
------------------------------------------------------------------------
`artifacts/worker-097/reject_audit/` (worker-097, 00:45–00:48) already MEASURED the
reject stream read-only and pre-registered "no ingest, no canonical writes". This
instrument does not repeat that measurement as its contribution; it takes the
measurement as an input premise, re-measures it at its own pins for the repair window,
and adds what was explicitly out of worker-097's scope:

  * `repair_map.json`        — explicit invalid -> allowed `conclusion_type` mapping
  * `recovery_bundle.jsonl`  — repaired events, each round-trip validated
  * `preflight_event.py`     — reusable pre-emission gate (shared with ingest functions)
  * `PATCH_PROPOSAL.md`      — proposed (NOT applied) ingest fix for terminal rejection
  * `reemission_manifest.json` — verbatim-valid but terminally suppressed events

Also cites `comms/outbox/worker-027.jsonl` blocker `w027-ccalign-...-blocker-ingest-rejects`.

Invariants
----------
I1  No repair may target a strong conclusion type (theorem / conditional_theorem /
    stability_result / counterexample / formal_model). Only numerical_evidence or
    open_problem are permitted targets, so a repair can never inflate a conclusion.
I2  No canonical path is written: this script writes only under its own artifact dir.
I3  Pinned inputs are hashed before and after; a move is recorded as DRIFT, not hidden.
I4  Every recovery candidate must pass the *real* `normalize_event`+`validate_event`.

Usage
-----
    python3 run_reject_repair_056.py            # write artifacts
    python3 run_reject_repair_056.py --check    # verify existing artifacts, no writes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-056/reject_repair -> swarm root
sys.path.insert(0, str(ROOT / "research_map"))

from comms import normalize_event, _json_objects  # noqa: E402
from schemas import validate_event, SchemaError  # noqa: E402
from preflight_event import preflight, STRONG_CONCLUSION_TYPES, REPAIRABLE_TARGETS  # noqa: E402

RAW = HERE / "raw"
SNAPSHOT = RAW / "rejected.snapshot.jsonl"
EVENTS_SNAPSHOT = RAW / "events.snapshot.jsonl"

PINNED_INPUTS = [
    "comms/rejected.jsonl",
    "research_map/comms.py",
    "research_map/schemas.py",
    "research_map/events.jsonl",
    "runtime/state/ingested_ids.json",
    "comms/outbox/worker-027.jsonl",
]

# Semantics-preserving mapping. Every target is one of the two weakest evidential
# types (I1). Rationale is per token, not per event, so it is auditable in one table.
REPAIR_MAP: dict[str, tuple[str, str]] = {
    # measurements / replications / calibrations -> numerical_evidence
    "empirical": ("numerical_evidence", "denotes a measured, non-analytic result"),
    "empirical_measurement": ("numerical_evidence", "denotes an empirical measurement"),
    "empirical_observation": ("numerical_evidence", "denotes an empirical observation"),
    "observation": ("numerical_evidence", "denotes a recorded observation/measurement"),
    "measurement": ("numerical_evidence", "denotes a measurement"),
    "artifact_measurement": ("numerical_evidence", "denotes a measurement of an artifact"),
    "audit_measurement": ("numerical_evidence", "denotes a measurement made by an audit"),
    "machine_measurement": ("numerical_evidence", "denotes a machine-produced measurement"),
    "measurement_evidence": ("numerical_evidence", "denotes measurement evidence"),
    "verification_measurement": ("numerical_evidence", "denotes a measurement in verification"),
    "verification_result": ("numerical_evidence", "denotes the result of a verification run"),
    "calibration_result": ("numerical_evidence", "denotes a calibration outcome"),
    "independent_replication": ("numerical_evidence", "denotes a replication measurement"),
    "mechanical_evidence": ("numerical_evidence", "denotes mechanically produced evidence"),
    "root_cause_measurement": ("numerical_evidence", "denotes a measurement of a root cause"),
    # findings / process / proposals -> open_problem (deflationary, never a result claim)
    "methodological_finding": ("open_problem", "a finding about method, not a result"),
    "process_finding": ("open_problem", "a finding about process, not a result"),
    "instrument_finding": ("open_problem", "a finding about an instrument, not a result"),
    "diagnosis": ("open_problem", "a diagnosis, not a result claim"),
    "adjudication_input": ("open_problem", "an input to adjudication, not a result"),
    "independent_review_verdict": ("open_problem", "a review verdict is not a result claim"),
    "proposal": ("open_problem", "a proposal, not an established result"),
}

# Rule tier for tokens not in the explicit table: the live stream invents new tokens
# faster than a static list tracks (instrument_measurement, empirical_observation, ...
# all appeared during this run). Rules are pattern-based and auditable, and remain
# constrained by I1 — they can only ever emit numerical_evidence or open_problem.
MEASUREMENT_PATTERNS = ("measurement", "observation", "replication", "calibration",
                        "empirical", "evidence", "result")
FINDING_PATTERNS = ("finding", "proposal", "diagnosis", "verdict", "input", "adjudication")


def resolve_token(token) -> tuple[str, str, str] | None:
    """(target, rationale, tier) or None when the token cannot be mapped safely."""
    if token in REPAIR_MAP:
        target, why = REPAIR_MAP[token]
        return target, why, "explicit"
    if not isinstance(token, str) or not token.strip():
        return None
    low = token.lower()
    if any(p in low for p in MEASUREMENT_PATTERNS):
        return ("numerical_evidence",
                f"rule:measurement-family token {token!r} maps to a measured result",
                "rule:measurement")
    if any(p in low for p in FINDING_PATTERNS):
        return ("open_problem",
                f"rule:finding-family token {token!r} asserts no established result",
                "rule:finding")
    return None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins() -> dict:
    out = {}
    for rel in PINNED_INPUTS:
        p = ROOT / rel
        out[rel] = sha256_file(p) if p.is_file() else None
    return out


def load_rejects(snapshot: Path) -> list[dict]:
    rows = []
    for line in snapshot.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            rows.append({"_unparseable": line[:200]})
    return rows


SOURCES_DIR = RAW / "sources"


def snapshot_sources(sources: set[str]) -> dict[str, dict]:
    """Pin the outbox bytes that recovery reads.

    Recovery resolves a rejected event_id in the outbox file recorded as its `source`.
    Those files are live and append-only, so reading them directly makes the census
    irreproducible: a source rewritten between two runs moves an event between
    UNRECOVERABLE and NET_LOST_* (observed once during this task). Every source is
    therefore byte-copied under raw/sources/ and all classification reads the copy.
    """
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    pins: dict[str, dict] = {}
    for rel in sorted(s for s in sources if s):
        src = ROOT / rel
        dst = SOURCES_DIR / rel.replace("/", "__")
        if src.is_file():
            dst.write_bytes(src.read_bytes())
            pins[rel] = {"snapshot": str(dst.relative_to(HERE)), "sha256": sha256_file(dst)}
        else:
            pins[rel] = {"snapshot": None, "sha256": None}
    return pins


def index_sources(source_pins: dict[str, dict]) -> dict[str, list[tuple[int, dict]]]:
    """event_id -> [(line_no, doc)] read from the PINNED source snapshots."""
    idx: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for rel, pin in source_pins.items():
        if not pin.get("snapshot"):
            continue
        p = HERE / pin["snapshot"]
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            s = line.strip()
            if not s:
                continue
            try:
                d = json.loads(s)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get("event_id"):
                idx[d["event_id"]].append((n, d))
    return idx


def raw_prefix_match(rec: dict, doc: dict) -> bool:
    """worker-097's SOURCE_MUTATED check: compare stored raw prefix to current bytes."""
    stored = rec.get("raw") or ""
    if not stored:
        return False
    now = json.dumps(doc, sort_keys=True)
    return now[:300].replace(" ", "") == stored[:300].replace(" ", "")


def classify(doc: dict, source: str) -> tuple[bool, str]:
    d = json.loads(json.dumps(doc))
    d.setdefault("created_at", "x")
    d.setdefault("actor", "x")
    d["_received_at"] = "x"
    try:
        d = normalize_event(d, source)
        validate_event(d)
        return True, "ok"
    except SchemaError as e:
        return False, str(e)
    except Exception as e:  # pragma: no cover - defensive
        return False, f"normalizer: {type(e).__name__}: {e}"


def repair_event(doc: dict) -> tuple[dict | None, str | None]:
    """Apply the explicit table, else the rule tier, to an out-of-vocabulary claim type."""
    token = doc.get("conclusion_type")
    if doc.get("event_type") != "claim":
        return None, f"not a claim event (event_type={doc.get('event_type')!r})"
    resolved = resolve_token(token)
    if resolved is None:
        return None, f"no declared mapping for conclusion_type={token!r}"
    target, why, tier = resolved
    if target in STRONG_CONCLUSION_TYPES or target not in REPAIRABLE_TARGETS:
        return None, f"mapping target {target!r} violates I1"
    out = json.loads(json.dumps(doc))
    out["conclusion_type"] = target
    out["conclusion_type_repaired_from"] = token
    out["_repair"] = {
        "instrument": "W056-REJECT-REPAIR-01",
        "mapping_tier": tier,
        "mapping_rationale": why,
        "invariant": "I1: repair targets restricted to numerical_evidence|open_problem",
        "requires_author_or_controller_emission": True,
    }
    out["event_id"] = f"{doc.get('event_id')}-recovered-056"
    return out, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--repin", action="store_true",
                    help="re-copy rejected.jsonl/events.jsonl/sources (moves the pins)")
    args = ap.parse_args()

    pins_before = measure_pins()
    RAW.mkdir(parents=True, exist_ok=True)

    # Pins move only on an explicit --repin (or first run). A plain re-run regenerates
    # derived artifacts from the existing pins, so published numbers stay reproducible.
    if args.repin or not SNAPSHOT.is_file():
        SNAPSHOT.write_bytes((ROOT / "comms/rejected.jsonl").read_bytes())
    if args.repin or not EVENTS_SNAPSHOT.is_file():
        EVENTS_SNAPSHOT.write_bytes((ROOT / "research_map/events.jsonl").read_bytes())

    if not EVENTS_SNAPSHOT.is_file():
        print(json.dumps({"check": "FAIL", "reason": "pinned events snapshot missing"}, indent=1))
        return 1

    snap_sha = sha256_file(SNAPSHOT)
    recs = load_rejects(SNAPSHOT)
    sources = {r.get("source") for r in recs if r.get("source")}

    if args.check:
        # Reuse the pins recorded in report.json so --check reproduces, not re-pins.
        source_pins = json.loads((HERE / "report.json").read_text())["source_pins"]
        missing = [p for p in source_pins.values() if p.get("snapshot")
                   and not (HERE / p["snapshot"]).is_file()]
        if missing:
            print(json.dumps({"check": "FAIL", "reason": "pinned source snapshot missing",
                              "missing": missing[:5]}, indent=1))
            return 1
    elif args.repin or not (RAW / "sources").is_dir():
        source_pins = snapshot_sources(sources)
    else:
        source_pins = json.loads((HERE / "report.json").read_text())["source_pins"]

    idx = index_sources(source_pins)

    seen = set(json.loads((ROOT / "runtime/state/ingested_ids.json").read_text()))
    accepted_ids = set()
    for line in EVENTS_SNAPSHOT.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            accepted_ids.add(json.loads(line).get("event_id"))
        except ValueError:
            pass

    # One row per distinct rejected event_id. The reject log contains repeat rows for
    # the same id (the same event rejected from more than one cycle/source), so census
    # counts are reported over DISTINCT events while reject_rows keeps the raw volume.
    rows = []
    rowcount: dict = {}
    for rec in recs:
        eid = rec.get("event_id")
        rowcount[eid] = rowcount.get(eid, 0) + 1
    for rec in recs:
        eid = rec.get("event_id")
        if any(r["event_id"] == eid for r in rows):
            continue
        src = rec.get("source")
        hits = idx.get(eid) or []
        entry = {
            "event_id": eid,
            "source": src,
            "reject_reason": rec.get("reason"),
            "rejected_at": rec.get("rejected_at"),
            "reject_row_count": rowcount.get(eid, 1),
            "recovered": bool(hits),
            "source_line": hits[0][0] if hits else None,
        }
        if not hits:
            entry.update(classification="UNRECOVERABLE",
                         detail="original event not found in its recorded source file")
            rows.append(entry)
            continue
        doc = dict(hits[0][1])
        entry["raw_prefix_match"] = raw_prefix_match(rec, doc)
        entry["event_type"] = doc.get("event_type")
        entry["class_id"] = doc.get("class_id") or (doc.get("class_ids") or [None])[0]
        entry["node_id"] = doc.get("node_id")
        entry["conclusion_type"] = doc.get("conclusion_type")
        entry["in_seen"] = eid in seen
        entry["in_events"] = eid in accepted_ids
        ok, reason = classify(doc, str(src))
        entry["current_verdict"] = "ACCEPT" if ok else "REJECT"
        entry["current_reason"] = reason
        if eid in accepted_ids:
            entry["classification"] = "EVENTUALLY_ACCEPTED"
        elif ok:
            entry["classification"] = "NET_LOST_NOW_VALID"
        else:
            entry["classification"] = "NET_LOST_STILL_INVALID"
        rows.append(entry)

    # ---- repair candidates -------------------------------------------------
    bundle, unrepairable = [], []
    for e in rows:
        if e["classification"] != "NET_LOST_STILL_INVALID":
            continue
        hits = idx.get(e["event_id"]) or []
        if not hits:
            continue
        doc = dict(hits[0][1])
        fixed, why = repair_event(doc)
        if fixed is None:
            unrepairable.append({"event_id": e["event_id"], "reason": why})
            continue
        ok, reason = classify(fixed, str(e["source"]))
        if not ok:  # I4: never ship a candidate the real validator rejects
            unrepairable.append({"event_id": e["event_id"],
                                 "reason": f"repaired candidate still rejected: {reason}"})
            continue
        # The ingester would have set actor from the outbox path stem; mirror that so the
        # bundle names the true author rather than recording an anonymous repair.
        fixed["_original_actor"] = doc.get("actor") or Path(str(e["source"])).stem
        fixed["_original_event_id"] = e["event_id"]
        fixed["_source"] = f"{e['source']}:{e['source_line']}"
        bundle.append(fixed)

    # ---- verbatim-valid but terminally suppressed --------------------------
    reemit = []
    for e in rows:
        if e["classification"] != "NET_LOST_NOW_VALID":
            continue
        hits = idx.get(e["event_id"]) or []
        if not hits:
            continue
        doc = dict(hits[0][1])
        reemit.append({
            "original_event_id": e["event_id"],
            "original_actor": doc.get("actor"),
            "event_type": doc.get("event_type"),
            "class_id": e.get("class_id"),
            "source": f"{e['source']}:{e['source_line']}",
            "current_verdict": "ACCEPT",
            "note": ("valid at current validator but terminally suppressed by seen.add on "
                     "reject; requires re-emission under a NEW event_id by the original "
                     "actor or the controller — not emitted by this worker (attribution)"),
        })

    # ---- controls ----------------------------------------------------------
    controls: dict[str, object] = {}

    # C1: no false positives on the accepted stream (deterministic stride sample).
    ev_lines = [l for l in EVENTS_SNAPSHOT.read_text(errors="replace").splitlines() if l.strip()]
    stride = max(1, len(ev_lines) // 60)
    sample, flagged = [], []
    for i in range(0, len(ev_lines), stride):
        try:
            d = json.loads(ev_lines[i])
        except ValueError:
            continue
        sample.append(d.get("event_id"))
        ok, reason = preflight(d, "control-accepted")
        if not ok:
            flagged.append({"event_id": d.get("event_id"), "reason": reason})
    controls["C1_no_false_positive_on_accepted"] = {
        "sampled": len(sample), "flagged": len(flagged), "flagged_detail": flagged,
        "expectation": "flagged == 0", "pass": len(flagged) == 0,
        "method": f"every {stride}th line of the pinned events snapshot",
    }

    # C2: preflight flags 100% of recovered still-invalid originals.
    still = [e for e in rows if e["classification"] == "NET_LOST_STILL_INVALID"]
    caught = 0
    for e in still:
        hits = idx.get(e["event_id"]) or []
        if not hits:
            continue
        ok, _ = preflight(dict(hits[0][1]), "control-still-invalid")
        caught += 0 if ok else 1
    controls["C2_preflight_catches_rejects"] = {
        "still_invalid": len(still), "caught": caught,
        "expectation": "caught == still_invalid", "pass": caught == len(still),
    }

    # C3: determinism — re-read the PINNED bytes from disk and re-derive every
    # classification independently of the first pass. (An earlier version compared a
    # dict to itself, which is a tautology; this version can actually fail.)
    idx2 = index_sources(source_pins)
    rec_by_id = {r.get("event_id"): r for r in load_rejects(SNAPSHOT)}
    mismatches = []
    for e in rows:
        r2 = rec_by_id.get(e["event_id"]) or {}
        hits2 = idx2.get(e["event_id"]) or []
        if not hits2:
            c2 = "UNRECOVERABLE"
        else:
            ok2, _ = classify(dict(hits2[0][1]), str(r2.get("source")))
            c2 = ("EVENTUALLY_ACCEPTED" if e["event_id"] in accepted_ids
                  else "NET_LOST_NOW_VALID" if ok2 else "NET_LOST_STILL_INVALID")
        if c2 != e["classification"]:
            mismatches.append({"event_id": e["event_id"],
                               "first": e["classification"], "second": c2})
    controls["C3_deterministic"] = {
        "recomputed": len(rows), "mismatches": mismatches,
        "expectation": "mismatches == []", "pass": not mismatches,
    }

    # C7: pin discipline (I3) — report how far the live outbox has moved from the pins.
    live_div = []
    for rel, pin in source_pins.items():
        p = ROOT / rel
        if (sha256_file(p) if p.is_file() else None) != pin.get("sha256"):
            live_div.append(rel)
    controls["C7_live_source_divergence"] = {
        "sources_pinned": len(source_pins), "diverged": len(live_div), "ids": live_div[:20],
        "expectation": "non-zero is expected and harmless: classification reads the pin, not the live file",
        "pass": True,
    }

    # C4: repair-target invariant (I1).
    bad_targets = [c["event_id"] for c in bundle
                   if c.get("conclusion_type") in STRONG_CONCLUSION_TYPES]
    controls["C4_no_conclusion_inflation"] = {
        "repaired": len(bundle), "strong_targets": bad_targets,
        "expectation": "strong_targets == []", "pass": not bad_targets,
    }

    # C5: every shipped candidate passes the real validator (I4, restated as a control).
    rt_fail = []
    for c in bundle:
        ok, reason = preflight(c, "control-roundtrip")
        if not ok:
            rt_fail.append({"event_id": c["event_id"], "reason": reason})
    controls["C5_roundtrip_all_candidates"] = {
        "candidates": len(bundle), "failures": rt_fail,
        "expectation": "failures == []", "pass": not rt_fail,
    }

    # C6: source-mutation flag — how many recovered originals no longer match stored raw.
    src_mut = [e["event_id"] for e in rows if e.get("recovered") and not e.get("raw_prefix_match")]
    controls["C6_source_mutation"] = {
        "recovered": sum(1 for e in rows if e.get("recovered")),
        "prefix_mismatch": len(src_mut), "ids": src_mut[:20],
        "note": "mismatch makes that row's replay advisory (raw stored is truncated to 600 chars)",
    }

    # ---- census ------------------------------------------------------------
    # `rows` is deduped by event_id: classification counts DISTINCT events.
    cls = Counter(e["classification"] for e in rows)
    def sk(counter: Counter) -> dict:
        """Counters keyed for JSON: every key coerced to str (None is not sortable)."""
        return {str(k): v for k, v in sorted(counter.items(), key=lambda kv: str(kv[0]))}

    by_reason = Counter(str(e["reject_reason"]) for e in rows)
    by_reason_rows = Counter(str(r.get("reason")) for r in recs)
    loss_reason = Counter(str(e["current_reason"]) for e in rows
                          if e["classification"] == "NET_LOST_STILL_INVALID")
    loss_class = Counter(str(e.get("class_id") or "(none)") for e in rows
                         if e["classification"] in {"NET_LOST_STILL_INVALID", "NET_LOST_NOW_VALID"})
    loss_node = Counter(str(e.get("node_id") or "(none)") for e in rows
                        if e["classification"] in {"NET_LOST_STILL_INVALID", "NET_LOST_NOW_VALID"})
    loss_token = Counter(str(e.get("conclusion_type")) for e in rows
                         if e["classification"] == "NET_LOST_STILL_INVALID")

    pins_after = measure_pins()
    drift = {k: [pins_before[k], pins_after[k]] for k in pins_before
             if pins_before[k] != pins_after[k]}

    report = {
        "instrument": "W056-REJECT-REPAIR-01",
        "actor": "worker-056",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "class_id_bound": loss_class.most_common(1)[0][0] if loss_class else None,
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
        ).isoformat(timespec="seconds"),
        "snapshot": {"path": "artifacts/worker-056/reject_repair/raw/rejected.snapshot.jsonl",
                     "sha256": snap_sha, "rows": len(recs),
                     "distinct_event_ids": len({r.get("event_id") for r in recs})},
        "source_pins": source_pins,
        "events_snapshot": {"path": "artifacts/worker-056/reject_repair/raw/events.snapshot.jsonl",
                            "sha256": sha256_file(EVENTS_SNAPSHOT)},
        "census": {
            "reject_rows": len(recs),
            "distinct_event_ids": len(rows),
            "classification_distinct": sk(cls),
            "reject_reason_histogram_distinct": sk(by_reason),
            "reject_reason_histogram_rows": sk(by_reason_rows),
            "net_lost_still_invalid_by_reason": sk(loss_reason),
            "net_lost_by_class": sk(loss_class),
            "net_lost_by_node": sk(loss_node),
            "net_lost_invalid_conclusion_type_tokens": sk(loss_token),
        },
        "repair": {
            "candidates": len(bundle),
            "unrepairable": len(unrepairable),
            "unrepairable_detail": unrepairable[:20],
            "mapping_tokens_used": sorted({c.get("conclusion_type_repaired_from") for c in bundle}),
            "bundle": "artifacts/worker-056/reject_repair/recovery_bundle.jsonl",
        },
        "reemission": {"count": len(reemit),
                       "manifest": "artifacts/worker-056/reject_repair/reemission_manifest.json"},
        "controls": controls,
        "pins_before": pins_before,
        "pins_after": pins_after,
        "drift": drift,
    }

    if args.check:
        # verification mode: re-derive the headline numbers and compare to report.json
        prev = json.loads((HERE / "report.json").read_text())
        ok = (prev["snapshot"]["sha256"] == snap_sha
              and prev["census"]["classification_distinct"] == sk(cls))
        print(json.dumps({"check": "PASS" if ok else "FAIL",
                          "snapshot_sha256": snap_sha,
                          "classification": sk(cls)}, indent=1))
        return 0 if ok else 1

    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (HERE / "repair_map.json").write_text(json.dumps(
        {k: {"target": v[0], "rationale": v[1]} for k, v in sorted(REPAIR_MAP.items())},
        indent=1, sort_keys=True) + "\n")
    (HERE / "reemission_manifest.json").write_text(json.dumps(reemit, indent=1, sort_keys=True) + "\n")
    with (HERE / "recovery_bundle.jsonl").open("w") as f:
        for c in bundle:
            f.write(json.dumps(c, sort_keys=True) + "\n")

    # SHA256SUMS over the shipped artifacts, excluding itself.
    lines = []
    for p in sorted(HERE.iterdir()):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha256_file(p)}  {p.name}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(json.dumps({k: report[k] for k in ("snapshot", "census", "repair", "reemission", "drift")},
                     indent=1))
    print("controls:", json.dumps({k: v.get("pass", v.get("prefix_mismatch")) for k, v in controls.items()}))
    return 3 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
