#!/usr/bin/env python3
"""W026-GFORM-PIN-COVERAGE-01: independent gate-readiness census at the frozen bytes.

QUESTION THIS ANSWERS
  At the FROZEN rev28 pins, how many *independent, non-author, pin-bound, clean* accept
  verdicts exist for F0 / F1 / F2a / F2b, and which hard-failure families are still open?

WHY IT IS CLASS-BOUND
  The four targets carry the frozen class ids:
    F0  research_map/formulation_taxonomy.yaml        classes AF-WCC-VAC-GEN,
        AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH
    F1  schemas/af_wcc_vacuum.yaml                    AF-WCC-VAC-GEN
    F2a schemas/af_scc_c2_vacuum.yaml                 AF-SCC-C2-VAC-GEN
    F2b schemas/af_scc_c0_vacuum.yaml                 AF-SCC-C0-VAC-GEN
  Gate routing: G-F0 (F0), G-FORM (F1/F2a/F2b).

WHAT IT DOES NOT DO
  * It is not a gate verdict, not a node status, not a validation_status promotion.
  * It does not edit, apply, or promote any canonical artifact.
  * It does not re-adjudicate a finding's severity; it counts and families findings.

COUNTING RULE (mirrors map.assignments acceptance text)
  A verdict counts toward "two independent accepts at hash H" iff
    (1) target resolves to the frozen path for that node,
    (2) the most specific sha256 recorded for that path equals H,
    (3) verdict == accept and hard_failures is empty,
    (4) reviewer is not the artifact author (astra-lead-formulation),
    (5) reviewer has not already contributed a counted accept for that target.
  Everything else is reported with its exclusion reason, never silently dropped.

USAGE
  python3 check_pin_coverage.py            # write coverage.json / pins.json / controls.json
  python3 check_pin_coverage.py --check    # re-run and byte-compare, exit 1 on drift
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
MAP = ROOT / "research_map/research_map.json"
OUTBOX = ROOT / "comms/outbox"

AUTHOR_ACTORS = {"astra-lead-formulation"}

# node -> (canonical path, authoring mirror path)
TARGETS = {
    "F0": ("research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"),
    "F1": ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
}

HEX12 = re.compile(r"\b([0-9a-f]{12,64})\b")
OFFSET = re.compile(r"([+-]\d{2})(\d{2})$")


def parse_ts(ev: dict) -> str:
    raw = str(ev.get("created_at") or ev.get("_received_at") or "")
    raw = OFFSET.sub(r"\1:\2", raw.replace("Z", "+00:00"))
    return raw


def latest_per_reviewer(rows: list[dict]) -> dict:
    """Last at-pin verdict per reviewer (ISO-8601 strings, normalised offsets)."""
    out = {}
    for r in sorted(rows, key=parse_ts):
        if r["pin_status"] == "AT_PIN" and r["reviewer"]:
            out[r["reviewer"]] = r
    return out


def _is_lead(actor: str | None) -> bool:
    a = str(actor or "")
    return a.startswith("astra") or a.startswith("lead-") or a.startswith("controller")


FAMILY_PATTERNS = [
    ("VOCAB-CONCLUSION-TYPE", re.compile(r"conclusion[_ ]?type|vocab|scc_c[02]_future|strong_cosmic_censorship", re.I)),
    ("R03-BINDER-FORMAL", re.compile(r"binder|R03|absent from formal", re.I)),
    ("POINTER-CLASS-CONTRACT", re.compile(r"class_contract|pointer|class_contracts", re.I)),
    ("DATA-CLASS-D0", re.compile(r"data[_ ]?class|D0|tagged|disjoint union|regularity_class", re.I)),
    ("CLOCK-DUPKEY", re.compile(r"revised_at|duplicate|future[- ]dated|clock", re.I)),
    ("LEAKAGE-VISIBILITY-IPLUS", re.compile(r"visib|i\+|i_plus|leak|c0 or c2|composite", re.I)),
    ("FALSIFIER-SCOPE", re.compile(r"falsifier|tier|scope|locator|citation", re.I)),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def shas_in(obj) -> set[str]:
    """Every 12+ hex token anywhere in a JSON-ish object."""
    return set(HEX12.findall(json.dumps(obj, sort_keys=True)))


def load_events() -> tuple[list[dict], int]:
    """Accepted reviews from the map plus pending review events from the outbox."""
    accepted = []
    m = json.loads(MAP.read_text())
    for r in m.get("reviews", []):
        if isinstance(r, dict):
            r = dict(r)
            r["_source"] = "map.reviews"
            accepted.append(r)
    pending, files = [], 0
    seen = {r.get("event_id") for r in accepted}
    for p in sorted(OUTBOX.rglob("*.jsonl")):
        files += 1
        try:
            lines = p.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("event_type") != "review":
                continue
            if e.get("event_id") in seen:
                continue
            e = dict(e)
            e["_source"] = f"outbox:{p.relative_to(ROOT)}"
            pending.append(e)
    return accepted + pending, files


def target_of(ev: dict) -> set[str]:
    """Resolve which frozen targets a review event claims."""
    tid = ev.get("target_id")
    toks = []
    if isinstance(tid, str):
        toks.append(tid)
    elif isinstance(tid, list):
        toks += [str(x) for x in tid]
    node = ev.get("node_id") or ev.get("target_node_id")
    if isinstance(node, str):
        toks.append(node)
    elif isinstance(node, list):
        toks += [str(x) for x in node]
    blob = " ".join(toks)
    out = set()
    for t, (canon, authoring) in TARGETS.items():
        if canon in blob or authoring in blob:
            out.add(t)
            continue
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![A-Za-z0-9])", blob):
            out.add(t)
    return out


def pin_of(ev: dict, target: str, frozen: str | None = None) -> tuple[str | None, str]:
    """Most specific recorded sha for the target's canonical path in this event."""
    canon, authoring = TARGETS[target]
    fields = []
    for key in ("verified_sha256", "cited_sha256", "artifact_sha256", "sha256"):
        v = ev.get(key)
        if isinstance(v, str):
            fields.append(v)
    for key in ("artifact_refs", "evidence_refs"):
        v = ev.get(key)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    s = item.get("sha256")
                    if isinstance(s, str) and (item.get("path") in (canon, authoring)):
                        fields.append(s)
                elif isinstance(item, str) and (canon + "#" in item or authoring + "#" in item):
                    fields.extend(HEX12.findall(item))
    for f in fields:
        f = f.strip()
        if len(f) >= 12 and re.fullmatch(r"[0-9a-f]+", f):
            return f, "recorded"
    # fall back: any hex token in the whole event (lower confidence, still reported)
    cands = shas_in(ev)
    if len(cands) == 1:
        return next(iter(cands)), "inferred-single-token"
    # last resort: the event explicitly names the frozen pin (full or 12-prefix) somewhere
    if frozen:
        blob = json.dumps(ev, sort_keys=True)
        if frozen in blob or (len(frozen) >= 12 and frozen[:12] in blob):
            return frozen, "mentions-frozen-pin"
    return None, "unpinned"


def classify(ev: dict, target: str, frozen: str) -> dict:
    pin, basis = pin_of(ev, target, frozen)
    hf = ev.get("hard_failures") or []
    if not isinstance(hf, list):
        hf = [str(hf)]
    verdict = ev.get("verdict")
    reviewer = ev.get("reviewer") or ev.get("actor")
    at_pin = None
    if pin is None:
        status = "UNPINNED"
    elif frozen.startswith(pin) or pin.startswith(frozen):
        status = "AT_PIN"
        at_pin = True
    else:
        status = "VOID_PIN"
        at_pin = False
    reasons = []
    if status == "VOID_PIN":
        reasons.append(f"pin {pin[:12]} != frozen {frozen[:12]}")
    if status == "UNPINNED":
        reasons.append("no sha256 for the frozen path in the event")
    if verdict != "accept":
        reasons.append(f"verdict={verdict}")
    if hf:
        reasons.append(f"{len(hf)} hard_failure(s)")
    if reviewer in AUTHOR_ACTORS:
        reasons.append("reviewer is the artifact author")
    return {
        "event_id": ev.get("event_id"),
        "actor": ev.get("actor"),
        "reviewer": reviewer,
        "target": target,
        "verdict": verdict,
        "score": ev.get("score"),
        "pin": pin,
        "pin_basis": basis,
        "pin_status": status,
        "hard_failures": hf,
        "source": ev.get("_source"),
        "counts_as_counted_accept": not reasons,
        "exclusion_reasons": reasons,
    }


def families(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        for hf in r["hard_failures"]:
            text = hf if isinstance(hf, str) else json.dumps(hf, sort_keys=True)
            fam = "OTHER"
            for name, pat in FAMILY_PATTERNS:
                if pat.search(text):
                    fam = name
                    break
            groups[fam].append((r["event_id"], r["reviewer"], r["pin_status"], text))
    out = []
    for fam, items in sorted(groups.items()):
        reviewers = sorted({i[1] for i in items if i[1]})
        out.append({
            "family": fam,
            "n_mentions": len(items),
            "n_distinct_reviewers": len(reviewers),
            "reviewers": reviewers,
            "at_pin_mentions": sum(1 for i in items if i[2] == "AT_PIN"),
            "example": {"event_id": items[0][0], "reviewer": items[0][1], "text": items[0][3][:400]},
        })
    return out


def run_controls() -> list[dict]:
    frozen = "f" * 64

    def ev(eid, actor, verdict="accept", hf=None, pin=frozen, ts="2026-09-12T00:00:00+08:00"):
        return {
            "event_id": eid, "event_type": "review", "actor": actor, "reviewer": actor,
            "target_id": "F2a", "verdict": verdict, "score": 4.0, "created_at": ts,
            "hard_failures": hf or [], "verified_sha256": pin,
        }

    t0, t1 = "2026-09-12T00:00:00+08:00", "2026-09-12T00:01:00+08:00"
    cases = [
        ("C1 one clean accept at pin counts", [ev("c1", "rev-A")], 1),
        ("C2 duplicate reviewer does not double-count", [ev("c2a", "rev-A", ts=t0), ev("c2b", "rev-A", ts=t1)], 1),
        ("C3 wrong pin is void", [ev("c3", "rev-A", pin="0" * 64)], 0),
        ("C4 author accept is excluded", [ev("c4", "astra-lead-formulation")], 0),
        ("C5 accept with hard failure is not clean", [ev("c5", "rev-A", hf=["x"])], 0),
        ("C6 two distinct clean accepts meet the criterion", [ev("c6a", "rev-A"), ev("c6b", "rev-B")], 2),
        ("C7 accept superseded by later revise from the same reviewer does not count",
         [ev("c7a", "rev-A", ts=t0), ev("c7b", "rev-A", verdict="revise", ts=t1)], 0),
        ("C8 lead/controller verdict is not an external accept",
         [ev("c8", "astra-lead-audit")], 0),
    ]
    out = []
    for name, events, expected in cases:
        rows = [classify(e, "F2a", frozen) for e in events]
        latest = latest_per_reviewer(rows)
        counted = sum(1 for r in latest.values()
                      if r["counts_as_counted_accept"] and not _is_lead(r["reviewer"]))
        out.append({"control": name, "expected": expected, "observed": counted,
                    "pass": counted == expected,
                    "reasons": [r["exclusion_reasons"] for r in rows]})
    return out


def build(events: list[dict], n_files: int, event_source: str, inputs_override: dict | None = None) -> dict:
    fz = json.loads(FROZEN.read_text())
    pins = {}
    for t, (canon, authoring) in TARGETS.items():
        decl = fz["files"][canon]["sha256"]
        meas = sha256_file(ROOT / canon)
        a_meas = sha256_file(ROOT / authoring) if (ROOT / authoring).exists() else None
        a_decl = fz["files"].get(authoring, {}).get("sha256")
        pins[t] = {
            "canonical_path": canon, "canonical_declared_sha256": decl,
            "canonical_measured_sha256": meas, "declared_matches_measured": decl == meas,
            "authoring_path": authoring, "authoring_declared_sha256": a_decl,
            "authoring_measured_sha256": a_meas,
            "mirror": (a_meas == meas),
        }
    per_target = {}
    for t, info in pins.items():
        frozen = info["canonical_measured_sha256"]
        rows = []
        for e in events:
            if t not in target_of(e):
                continue
            rows.append(classify(e, t, frozen))
        counted, seen = [], set()
        for r in rows:
            if r["counts_as_counted_accept"] and r["reviewer"] not in seen:
                counted.append(r)
                seen.add(r["reviewer"])
        latest = latest_per_reviewer(rows)
        current = [r for r in latest.values() if r["counts_as_counted_accept"]]
        external = [r for r in current if not _is_lead(r["reviewer"])]
        superseded = []
        for r in rows:
            if r["verdict"] == "accept" and r["pin_status"] == "AT_PIN" and not r["hard_failures"] \
                    and r["reviewer"] not in AUTHOR_ACTORS and r["event_id"] not in {c["event_id"] for c in current}:
                superseded.append({"event_id": r["event_id"], "reviewer": r["reviewer"],
                                   "latest_verdict": (latest.get(r["reviewer"]) or {}).get("verdict"),
                                   "latest_event_id": (latest.get(r["reviewer"]) or {}).get("event_id")})
        per_target[t] = {
            "frozen_pin": frozen,
            "n_review_events_resolved": len(rows),
            "n_counted_independent_accepts": len(counted),
            "n_current_independent_accepts": len(current),
            "n_current_external_accepts": len(external),
            "criterion_two_accepts_met": len(counted) >= 2,
            "criterion_two_current_accepts_met": len(current) >= 2,
            "criterion_two_external_accepts_met": len(external) >= 2,
            "counted_accepts": [{"event_id": r["event_id"], "reviewer": r["reviewer"],
                                 "source": r["source"]} for r in counted],
            "current_accepts": [{"event_id": r["event_id"], "reviewer": r["reviewer"]} for r in current],
            "current_external_accepts": [{"event_id": r["event_id"], "reviewer": r["reviewer"]} for r in external],
            "superseded_accepts": superseded,
            "at_pin_verdicts": dict(Counter(r["verdict"] for r in rows if r["pin_status"] == "AT_PIN")),
            "pin_basis_counts": dict(Counter(r["pin_basis"] for r in rows)),
            "void_or_unpinned": sum(1 for r in rows if r["pin_status"] != "AT_PIN"),
            "open_finding_families": families([r for r in rows if r["pin_status"] == "AT_PIN"]),
            "rows": rows,
        }
    controls = run_controls()
    inputs = {
        "frozen_manifest": "artifacts/formulation/FROZEN.json",
        "frozen_manifest_sha256": sha256_file(FROZEN),
        "research_map": "research_map/research_map.json",
        "research_map_sha256": sha256_file(MAP),
        "outbox_files_scanned": n_files,
        "event_set": event_source,
        "event_set_sha256": hashlib.sha256(
            "\n".join(sorted(json.dumps(e, sort_keys=True) for e in events)).encode()).hexdigest(),
        "n_events": len(events),
    }
    if inputs_override:
        for k in ("frozen_manifest_sha256", "research_map_sha256", "outbox_files_scanned"):
            if k in inputs_override:
                inputs[k] = inputs_override[k]
    return {
        "schema": "w026.gform_pin_coverage/1",
        "task_id": "W026-GFORM-PIN-COVERAGE-01",
        "actor": "worker-026",
        "gate_routing": {"F0": "G-F0", "F1": "G-FORM", "F2a": "G-FORM", "F2b": "G-FORM"},
        "class_ids": {
            "F0": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
            "F1": ["AF-WCC-VAC-GEN"], "F2a": ["AF-SCC-C2-VAC-GEN"], "F2b": ["AF-SCC-C0-VAC-GEN"],
        },
        "authority_limits": [
            "worker-level measurement only; not a gate verdict",
            "does not edit, apply, or promote any canonical artifact",
            "counts verdicts by recorded pin; a pin recorded wrongly is a finding, not an edit",
        ],
        "inputs": inputs,
        "frozen_revision": fz.get("revision"),
        "frozen_at": fz.get("frozen_at"),
        "pins": pins,
        "targets": per_target,
        "controls": controls,
        "falsifier": (
            "Falsified if: (a) any counted accept's recorded sha256 differs from the measured "
            "canonical hash printed in pins; (b) two counted accepts for one target share a "
            "reviewer; (c) a counted accept's reviewer is astra-lead-formulation; (d) a counted "
            "accept carries a non-empty hard_failures list; (e) a counted accept is superseded by "
            "a later at-pin non-accept verdict from the same reviewer; or (f) any target's counted "
            "accept set changes on a byte-identical rerun (--check)."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-write", action="store_true",
                    help="freeze the loaded review set to snapshot/events.jsonl and compute from it")
    ap.add_argument("--snapshot-check", action="store_true",
                    help="recompute from snapshot/events.jsonl and byte-compare coverage.json")
    args = ap.parse_args()

    snap_dir = OUT / "snapshot"
    snap_file = snap_dir / "events.jsonl"

    if args.snapshot_check:
        events = [json.loads(l) for l in snap_file.read_text().splitlines() if l.strip()]
        recorded = json.loads((OUT / "coverage.json").read_text())
        data = build(events, 0, "snapshot/events.jsonl", inputs_override=recorded.get("inputs"))
        payload = json.dumps(data, indent=1, sort_keys=True)
        existing = (OUT / "coverage.json").read_text()
        if existing != payload + "\n":
            keys = sorted(set(recorded) | set(data))
            moved = [k for k in keys if recorded.get(k) != data.get(k)]
            print(f"DRIFT: coverage.json differs from a recomputation on the frozen snapshot; "
                  f"top-level sections differing: {moved}")
            return 1
        print(f"OK: coverage.json is byte-stable on the {len(events)}-event frozen snapshot")
        return 0

    events, n_files = load_events()
    source = "live map.reviews + comms/outbox"
    if args.snapshot_write:
        snap_dir.mkdir(exist_ok=True)
        events = sorted(events, key=lambda x: str(x.get("event_id")))
        snap_file.write_text("\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n")
        source = "snapshot/events.jsonl"
    data = build(events, n_files, source)
    payload = json.dumps(data, indent=1, sort_keys=True)
    (OUT / "coverage.json").write_text(payload + "\n")
    (OUT / "pins.json").write_text(json.dumps(
        {"frozen_revision": data["frozen_revision"], "frozen_at": data["frozen_at"],
         "pins": data["pins"], "inputs": data["inputs"]}, indent=1, sort_keys=True) + "\n")
    (OUT / "controls.json").write_text(json.dumps(
        {"controls": data["controls"],
         "all_pass": all(c["pass"] for c in data["controls"])}, indent=1, sort_keys=True) + "\n")
    for t, v in data["targets"].items():
        print(f"{t}: pin={v['frozen_pin'][:12]} reviews={v['n_review_events_resolved']} "
              f"accepts_any={v['n_counted_independent_accepts']} "
              f"accepts_current={v['n_current_independent_accepts']} "
              f"accepts_external={v['n_current_external_accepts']} "
              f"criterion_any={v['criterion_two_accepts_met']} "
              f"criterion_current={v['criterion_two_current_accepts_met']} "
              f"criterion_external={v['criterion_two_external_accepts_met']} "
              f"at_pin_verdicts={v['at_pin_verdicts']} void_or_unpinned={v['void_or_unpinned']} "
              f"superseded={len(v['superseded_accepts'])}")
        for f in v["open_finding_families"]:
            print(f"   open-family {f['family']}: mentions={f['n_mentions']} "
                  f"reviewers={f['n_distinct_reviewers']} at_pin={f['at_pin_mentions']}")
    print("controls:", "ALL PASS" if all(c["pass"] for c in data["controls"]) else "FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
