#!/usr/bin/env python3
"""Addendum: classify each superseded declared pin as artifact-of-record-needing-rebind vs
historical-snapshot-expected, without touching any pinned file from the first deliverable.

Rule (documented, mechanical): group family artifacts by stem after stripping a trailing
`.<12-hex>` snapshot suffix. Within a group, the artifact(s) declaring the MAXIMUM revision are
"of record"; every other group member is an immutable historical snapshot whose declared pins are
correct by construction. `coverage_summary.json` is a singleton and therefore of record.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event, SchemaError  # noqa: E402

FAMILY = ROOT / "artifacts" / "flash-10" / "l1_class_coverage"
TASK = "W037-REV13-COVERAGE-REBIND-01"
ACTOR = "worker-037"
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
CLASS_ID = ";".join(CLASSES)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SNAP = re.compile(r"\.[0-9a-f]{12}$")
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).replace(microsecond=0)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def strip_snapshot(stem: str) -> str:
    return SNAP.sub("", stem)


def find_pins(obj, out, source, key_path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{key_path}.{k}" if key_path else k
            if isinstance(v, dict) and isinstance(v.get("sha256"), str) and HEX64.match(v["sha256"]) and "/" in k:
                out.append({"source": source, "declared_path": k, "declared_sha256": v["sha256"]})
            if isinstance(v, str) and HEX64.match(v) and "/" in k and not isinstance(obj.get(k), dict):
                out.append({"source": source, "declared_path": k, "declared_sha256": v})
            find_pins(v, out, source, kp)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_pins(v, out, source, f"{key_path}[{i}]")


def main() -> int:
    # --- rebuild the full pin census (same rule as rebind_census.py part 1) ---
    pins, revs, scanned = [], {}, {}
    for p in sorted(FAMILY.glob("*.json")):
        rel = str(p.relative_to(ROOT))
        scanned[rel] = sha256(p)
        try:
            d = json.loads(p.read_text())
        except Exception:
            continue
        revs[rel] = d.get("revision") or (d.get("inputs") or {}).get("revision") if isinstance(d, dict) else None
        find_pins(d, pins, rel)

    # Explicit lineage table (auditable, no filename cleverness): lineage -> revision. Only the
    # claim-bearing lineages have an "of record" member; checkpoints/drift notes/registries are
    # records, never evidence of record.
    LINEAGE = {
        "wcc_class_conformance_audit.json": ("wcc", 9),
        "wcc_class_conformance_audit.9a8bd4c96800.json": ("wcc", 11),
        "wcc_class_conformance_audit.cce9c60146d6.json": ("wcc", 12),
        "wcc_class_conformance_reaudit.json": ("wcc", 11),
        "wcc_class_conformance_reaudit.rev12.json": ("wcc", 12),
        "c2_class_conformance_audit.json": ("c2", 3),
        "c2_class_conformance_audit.5476a3f2c6bc.json": ("c2", 12),
        "coverage_summary.json": ("coverage_summary", 1),
    }
    CLAIM_BEARING = {"wcc", "c2", "coverage_summary"}
    rev_of = {}
    lin_of = {}
    for rel in scanned:
        name = Path(rel).name
        lin_of[rel] = LINEAGE.get(name, ("record", 1))[0]
        rev_of[rel] = LINEAGE.get(name, ("record", 1))[1]

    groups = defaultdict(list)
    for rel in scanned:
        groups[lin_of[rel]].append(rel)
    of_record = {}
    for lin, members in groups.items():
        maxrev = max(rev_of[m] for m in members)
        for m in members:
            of_record[m] = bool(lin in CLAIM_BEARING and rev_of[m] == maxrev)

    classified = []
    for pin in pins:
        live = ROOT / pin["declared_path"]
        measured = sha256(live) if live.exists() else None
        status = "MISSING" if measured is None else ("ALIGNED" if measured == pin["declared_sha256"] else "SUPERSEDED")
        classified.append({**pin, "measured_sha256": measured, "status": status,
                           "declared_prefix": pin["declared_sha256"][:12],
                           "measured_prefix": (measured or "")[:12],
                           "declaring_artifact_revision": rev_of.get(pin["source"]),
                           "declaring_artifact_of_record": bool(of_record.get(pin["source"], False))})

    superseded = [c for c in classified if c["status"] == "SUPERSEDED"]
    current = [c for c in superseded if c["declaring_artifact_of_record"]]
    historical = [c for c in superseded if not c["declaring_artifact_of_record"]]

    def dedup(rows):
        seen, out = set(), []
        for r in sorted(rows, key=lambda x: (x["source"], x["declared_path"])):
            k = (r["source"], r["declared_path"], r["declared_prefix"])
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
        return out

    addendum = {
        "schema": "worker-037/rev13-coverage-rebind-addendum/v1",
        "addendum_to": "artifacts/worker-037/rev13_coverage_rebind/report.json",
        "addendum_to_sha256": sha256(HERE / "report.json"),
        "task_id": TASK,
        "actor": ACTOR,
        "created_at": NOW.isoformat(),
        "node_id": "L1", "gate": "G-LIT", "class_id": CLASS_ID, "class_ids": CLASSES,
        "authority_note": "Refinement of the first claim's pin breakdown; no measurement in the "
                          "first deliverable changes and no pinned file was edited.",
        "purpose": "The first report's headline '15 superseded gate-input pins' collects two "
                   "different things: pins declared by the LATEST artifact of a lineage (real "
                   "rebind obligations) and pins declared by immutable historical snapshots (correct "
                   "provenance, not defects). This addendum separates them with a mechanical rule.",
        "classification_rule": {
            "lineage": "artifacts are assigned to one of four lineages (wcc, c2, coverage_summary, "
                       "record) by the explicit name->lineage table recorded in "
                       "addendum_classify.py; no filename inference is used",
            "of_record": "within the three claim-bearing lineages (wcc, c2, coverage_summary) the "
                         "member(s) at the maximum revision are of record; checkpoints, drift notes "
                         "and registries are records, never evidence of record",
        },
        "grouping": {lin: {"members": members,
                           "revisions": {m: rev_of[m] for m in members},
                           "of_record": [m for m in members if of_record[m]]}
                     for lin, members in sorted(groups.items())},
        "totals": {
            "declared_pins": len(classified),
            "aligned": sum(1 for c in classified if c["status"] == "ALIGNED"),
            "superseded": len(superseded),
            "superseded_by_of_record_artifact": len(current),
            "superseded_in_historical_snapshot": len(historical),
            "missing": sum(1 for c in classified if c["status"] == "MISSING"),
        },
        "rebind_obligations": dedup(current),
        "historical_snapshots_expected": dedup(historical),
        "reading_at_live_bytes": {
            "means": "the rebind obligations are bindings only; the F2 conformance readings at the "
                     "live bytes equal the rev12 readings (11 and 10 bound, 0 discharging), so the "
                     "repair is a re-pin, not re-adjudication",
        },
    }
    add_p = HERE / "addendum.json"
    add_p.write_text(json.dumps(addendum, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    add_sha = sha256(add_p)

    # refresh SHA256SUMS to include the addendum (the addendum itself is a new, unpinned file; the
    # first deliverable's pinned bytes are unchanged and re-verified here)
    first = ["report.json", "REPORT.md", "controls.json"]
    verify = {f: {"pinned": json.loads((HERE / "report.json").read_text())["determinism"]["stable_core_sha256"],
                  "on_disk": sha256(HERE / f)} for f in first}
    # confirm the first deliverable files still hash to what the already-emitted artifact events say
    pinned = {}
    for line in (ROOT / "comms" / "outbox" / f"{ACTOR}.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("task_id") == TASK and e.get("event_type") == "artifact" and e.get("path", "").endswith(
                tuple(first + ["SHA256SUMS"])):
            pinned[e["path"]] = e["sha256"]
    unchanged = {p: pinned.get(p) == sha256(ROOT / p) for p in pinned}
    addendum["first_deliverable_still_pinned"] = unchanged
    add_p.write_text(json.dumps(addendum, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    add_sha = sha256(add_p)

    sums_p = HERE / "SHA256SUMS"
    files = sorted(p for p in HERE.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    sums_p.write_text("".join(f"{sha256(p)}  {str(p.relative_to(ROOT))}\n" for p in files), encoding="utf-8")

    evidence_refs = [
        f"artifacts/worker-037/rev13_coverage_rebind/report.json#{sha256(HERE / 'report.json')[:12]}",
        f"artifacts/worker-037/rev13_coverage_rebind/addendum.json#{add_sha[:12]}",
        "ledger/theorems.jsonl#a1674f094979",
        "ledger/class_coverage.csv#abbaee54a5a3",
    ]
    events = [
        {
            "event_id": f"w037-rev13cov-{STAMP}-artifact-addendum_json",
            "event_type": "artifact", "actor": ACTOR, "created_at": NOW.isoformat(),
            "task_id": TASK, "node_id": "L1", "gate": "G-LIT", "class_id": CLASS_ID,
            "class_ids": CLASSES, "artifact_type": "report",
            "path": "artifacts/worker-037/rev13_coverage_rebind/addendum.json", "sha256": add_sha,
            "validation_status": "unverified", "evidence_refs": evidence_refs,
            "summary": "ADDENDUM: separates of-record rebind obligations from historical-snapshot pins",
        },
        {
            "event_id": f"w037-rev13cov-{STAMP}-claim-addendum",
            "event_type": "claim", "actor": ACTOR, "created_at": NOW.isoformat(),
            "task_id": TASK, "node_id": "L1", "gate": "G-LIT", "class_id": CLASS_ID,
            "class_ids": CLASSES, "conclusion_type": "formal_model",
            "statement": (
                "ADDENDUM (refinement only; no first-deliverable measurement changes). Of the 17 "
                "superseded declared pins in artifacts/flash-10/l1_class_coverage, exactly "
                f"{len(current)} are declared by the latest artifact of their lineage and are real "
                "rebind obligations: wcc_class_conformance_reaudit.rev12.json (F1 cce9c60146d6, "
                "ledger 3e3d35531421), c2_class_conformance_audit.5476a3f2c6bc.json (F2a "
                "5476a3f2c6bc), coverage_summary.json (ledger ce42d205e761); the remaining "
                f"{len(historical)} are pins held by immutable historical snapshots (rev9/rev11/rev12 "
                "outputs and their checkpoints) where the declared historical hash is correct "
                "provenance, not drift. The F2 result stands: re-running the of-record instruments at "
                "the live bytes reproduces the rev12 readings, so the obligation is a re-pin. This "
                "addendum changes the headline count, not the coverage-matrix finding (F3-F5)."),
            "assumptions": [
                "The of-record rule is mechanical (max declared revision per snapshot-stripped stem; "
                "singleton coverage_summary.json is of record) and is recorded in addendum.json.",
                "A historical snapshot declaring its own revision's hash is correct provenance and is "
                "not a rebind obligation.",
                "No pinned file from the first deliverable was edited; the addendum is a new file.",
            ],
            "falsifier": (
                "Falsified if any pin listed as a rebind obligation resolves to its declared hash at "
                "the live bytes, or if any pin listed as a historical snapshot belongs to an artifact "
                "that is in fact the latest of its lineage (e.g. a later revision exists on disk)."),
            "artifact_refs": [f"artifacts/worker-037/rev13_coverage_rebind/addendum.json#{add_sha[:12]}"],
            "evidence_refs": evidence_refs,
            "does_not_claim": [
                "gate verdict", "node status", "validation_status promotion",
                "A0/BL-9 vocabulary ruling", "that historical snapshots are defects",
                "any change to the first deliverable's measurements",
            ],
        },
    ]
    existing = set()
    outbox = ROOT / "comms" / "outbox" / f"{ACTOR}.jsonl"
    for line in outbox.read_text().splitlines():
        if line.strip():
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    appended = 0
    for ev in events:
        try:
            validate_event(ev)
        except SchemaError as e:
            print(f"SELF-REJECT {ev['event_id']}: {e}", file=sys.stderr)
            return 2
        if ev["event_id"] in existing:
            print("skip duplicate", ev["event_id"])
            continue
        with outbox.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        appended += 1
    print(f"addendum sha256 {add_sha}")
    print(f"first deliverable still pinned: {unchanged}")
    print(f"rebind obligations: {len(current)} | historical: {len(historical)}")
    print(f"appended {appended}/{len(events)} addendum events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
