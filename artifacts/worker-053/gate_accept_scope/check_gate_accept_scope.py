#!/usr/bin/env python3
"""W053-GATE-ACCEPT-SCOPE-01: does the proposed union-stream repair of the
controller's review-coverage scan honour declared gate-accept scope?

Read-only, deterministic, stdlib-only, single-read pinning, drift guard.

Object under test
-----------------
`research_map/astra_lifecycle.py::review_coverage` is the advisory instrument
behind the G-F0/G-FORM/G-AUDIT distinct-accept counts. Two independent workers
measured that it (a) counts a review that the same reviewer later amended to
`revise` (CV-01) and (b) cannot see path#hash target ids (CV-02 / W042-GSG).
W001-COVERAGE-SCAN-01 proposed a repair: union the accepted event stream,
resolve path#hash targets, apply latest-verdict supersession. This checker
audits the *scope* dimension of that proposal, which no prior task covered:

    several review records declare `counts_as_gate_accept: false` (worker-089),
    i.e. their author explicitly declines to have them counted as gate accepts.
    Neither the shipped scan nor the proposed union consults that key.

Three censuses at one pinned snapshot:
    C1 shipped        : reviews/*.json, shipped target/pin semantics, full flag
    C2 naive union    : files + accepted stream, path#hash resolution, full flag
    C3 scoped union   : C2 plus `counts_as_gate_accept is not False`
    C4 scoped union + latest-verdict-wins per (reviewer, target)

Exit code 0 = measurements completed (not a gate verdict; a FAIL check is data).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]  # artifacts/worker-053/gate_accept_scope/x.py
OUT = Path(__file__).resolve().parent

TARGET_PATHS = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "L0": "ledger/theorems.jsonl",
}
ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
PATH_TO_TARGET = {v: k for k, v in TARGET_PATHS.items()}
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
HEX12 = re.compile(r"^[0-9a-f]{12,64}$")
HEX_IN = re.compile(r"([0-9a-fA-F]{12,64})")

failures: list[str] = []


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def check(cid: str, ok: bool, detail: str) -> dict:
    if not ok:
        failures.append(cid)
    return {"id": cid, "status": "pass" if ok else "FAIL", "detail": detail}


# --------------------------------------------------------------------------- #
# 1. single-read pinning
# --------------------------------------------------------------------------- #
class Pin:
    def __init__(self, rel: str):
        self.rel = rel
        self.bytes = (ROOT / rel).read_bytes()
        self.sha256 = sha(self.bytes)
        self.text = self.bytes.decode("utf-8", "replace")

    @property
    def short(self) -> str:
        return self.sha256[:12]


def read_or_none(rel: str):
    p = ROOT / rel
    return p.read_bytes() if p.is_file() else None


pinned = {
    "events": Pin("research_map/events.jsonl"),
    "lifecycle": Pin("research_map/astra_lifecycle.py"),
    "lifecycle05": Pin("research_map/astra_lifecycle_05_events.py"),
    "map": Pin("research_map/research_map.json"),
    "frozen": Pin("artifacts/formulation/FROZEN.json"),
}
for _t, _p in TARGET_PATHS.items():
    pinned["target_" + _t] = Pin(_p)

LIVE = {t: pinned["target_" + t].sha256 for t in TARGET_PATHS}
review_files = {}
for p in sorted((ROOT / "reviews").glob("*.json")):
    b = p.read_bytes()
    review_files[p.name] = {"sha256": sha(b), "bytes": b}

corpus_digest = sha(b"".join(
    name.encode() + b"\0" + review_files[name]["sha256"].encode() + b"\n"
    for name in sorted(review_files)))


# --------------------------------------------------------------------------- #
# 2. record model (shipped and repair semantics)
# --------------------------------------------------------------------------- #
def load_events(text: str):
    rows, bad = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(d, dict):
            rows.append(d)
    return rows, bad


def raw_targets(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    return out


def resolve_shipped(raw: str) -> str:
    return ALIASES.get(raw, ALIASES.get(raw.upper(), raw))


def resolve_repair(raw: str) -> str:
    t = raw.strip()
    sh = resolve_shipped(t)
    if sh != t and sh in TARGET_PATHS:
        return sh
    base = re.sub(r"#(?:sha256:)?[0-9a-fA-F]{6,64}$", "", t)
    return PATH_TO_TARGET.get(base, sh)


def pins_shipped(d: dict) -> list:
    out = []
    for key in PIN_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            out.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    out.append(v[k2].lower())
    return out


def pins_repair(d: dict) -> list:
    out = list(pins_shipped(d))
    for raw in raw_targets(d):
        m = HEX_IN.search(raw)
        if m:
            out.append(m.group(1).lower())
    return out


def binds(d: dict, target: str, pin_fn) -> bool:
    h = LIVE[target]
    for p in pin_fn(d):
        if len(p) < 12:
            continue
        if p.startswith(h[:12]) or h.startswith(p[:12]):
            return True
    return False


def is_full(d: dict) -> bool:
    return d.get("counts_as_full_schema_verdict") is not False


def gate_ok(d: dict) -> bool:
    return d.get("counts_as_gate_accept") is not False


def rows_from(d, src: str, actor: str, created, pin_fn, resolve_fn, verdict=None):
    v = str(verdict if verdict is not None else d.get("verdict", "")).lower()
    out = []
    for raw in raw_targets(d):
        t = resolve_fn(raw)
        if t in LIVE and binds(d, t, pin_fn):
            out.append({
                "src": src, "actor": actor, "target": t, "verdict": v,
                "full": is_full(d), "gate": gate_ok(d),
                "created": str(created) if created is not None else "",
            })
    return out


event_rows, bad_event_lines = load_events(pinned["events"].text)
file_records = []
for name in sorted(review_files):
    try:
        d = json.loads(review_files[name]["bytes"])
    except ValueError:
        continue
    if isinstance(d, dict):
        file_records.append((name, d))


def build(pin_fn, resolve_fn):
    rows = []
    for name, d in file_records:
        rows += rows_from(d, "reviews/" + name,
                          str(d.get("reviewer") or d.get("actor") or "?"),
                          d.get("created_at"), pin_fn, resolve_fn)
    for e in event_rows:
        if e.get("event_type") != "review":
            continue
        rows += rows_from(e, "events.jsonl#" + str(e.get("event_id")),
                          str(e.get("actor") or "?"), e.get("created_at"),
                          pin_fn, resolve_fn)
    return rows


shipped = build(pins_shipped, resolve_shipped)
repair = build(pins_repair, resolve_repair)


def census(rows, target_filter=None):
    out = {}
    for t in TARGET_PATHS:
        if target_filter and t != target_filter:
            continue
        out[t] = sorted({r["actor"] for r in rows
                         if r["target"] == t and r["verdict"] == "accept" and r["full"]})
    return out


def latest_wins(rows):
    best, keep = {}, []
    for r in rows:
        k = (r["actor"], r["target"])
        best[k] = max(best.get(k, ""), r["created"])
    for r in rows:
        if r["created"] == best[(r["actor"], r["target"])]:
            keep.append(r)
    return keep


C1 = census([r for r in shipped if r["src"].startswith("reviews/")])
C2 = census([r for r in repair if r["full"]])
C3 = census([r for r in repair if r["full"] and r["gate"]])
C4 = census([r for r in latest_wins(repair) if r["full"] and r["gate"]])

leaked = [r for r in repair if r["full"] and not r["gate"] and r["verdict"] == "accept"]
gate_false_accepts = [r for r in repair
                      if r["verdict"] == "accept" and not r["gate"]]

# controller-quoted counts at the pinned map revision (informational)
ctrl_quote, map_updated = {}, None
try:
    m = json.loads(pinned["map"].bytes)
    map_updated = m.get("updated_at")
    cga = m.get("controller_gate_audit", {})
    for gate in ("G-F0", "G-FORM", "G-AUDIT"):
        reason = str(cga.get(gate, {}).get("reason", ""))
        for t in TARGET_PATHS:
            for pat in (rf"{t} \[(\d+) distinct accept",
                        rf"{t} (\d+)[,\]]"):
                mm = re.search(pat, reason)
                if mm:
                    ctrl_quote[t] = int(mm.group(1))
                    break
except ValueError:
    pass


# --------------------------------------------------------------------------- #
# 3. checks
# --------------------------------------------------------------------------- #
checks = [
    check("V1-live-hashes", all(len(v) == 64 for v in LIVE.values()),
          {t: v[:12] for t, v in LIVE.items()}),
    check("V2-shipped-reproduces-controller",
          all(ctrl_quote.get(t, len(C1[t])) == len(C1[t]) for t in TARGET_PATHS),
          {"recomputed": {t: len(C1[t]) for t in TARGET_PATHS},
           "controller_quote": ctrl_quote, "map_updated_at": map_updated}),
    check("V3-worker089-declares-gate-false",
          any(r["actor"] == "worker-089" and not r["gate"] and r["target"] == "F2a"
              for r in repair)
          and any(r["actor"] == "worker-089" and not r["gate"] and r["target"] == "F2b"
                  for r in repair),
          "worker-089 live accepts on F2a/F2b present in accepted stream with "
          "counts_as_gate_accept=false"),
    check("V4-naive-union-leaks",
          "worker-089" in C2["F2a"] and "worker-089" in C2["F2b"],
          {"C2_F2a": C2["F2a"], "C2_F2b": C2["F2b"]}),
    check("V5-scope-aware-excludes",
          "worker-089" not in C3["F2a"] and "worker-089" not in C3["F2b"],
          {"C3_F2a": C3["F2a"], "C3_F2b": C3["F2b"]}),
    check("V6-leak-bounded",
          {r["actor"] for r in leaked} == {"worker-089"} and len(leaked) == 2,
          {"leaked": leaked}),
    check("V7-scanner-lacks-gate-key",
          "counts_as_gate_accept" not in pinned["lifecycle"].text
          and "counts_as_gate_accept" not in pinned["lifecycle05"].text,
          "key occurrences: lifecycle=%d lifecycle05=%d"
          % (pinned["lifecycle"].text.count("counts_as_gate_accept"),
             pinned["lifecycle05"].text.count("counts_as_gate_accept"))),
    check("V8-criterion-consequence",
          len(C2["F2b"]) >= 2 and len(C3["F2b"]) < 2,
          {"C2_F2b_meets_2": len(C2["F2b"]) >= 2, "C3_F2b_meets_2": len(C3["F2b"]) >= 2,
           "C2": C2, "C3": C3}),
    check("V9-drift-none", True, "re-measured in section 4"),
]

# --------------------------------------------------------------------------- #
# 4. drift guard
# --------------------------------------------------------------------------- #
drift = []
for key, p in pinned.items():
    cur = read_or_none(p.rel)
    if cur is None or sha(cur) != p.sha256:
        drift.append(key)
review_drift = []
for name, rec in review_files.items():
    cur = read_or_none("reviews/" + name)
    if cur is None or sha(cur) != rec["sha256"]:
        review_drift.append(name)
extra = sorted(set(p.name for p in (ROOT / "reviews").glob("*.json")) - set(review_files))
drift_detected = bool(drift or review_drift or extra)
checks[-1] = check("V9-drift-none", not drift_detected,
                   {"pinned": drift, "review_files": review_drift, "added": extra})

# --------------------------------------------------------------------------- #
# 5. controls (in-memory, through the same predicates)
# --------------------------------------------------------------------------- #
def synth(target="F2b", h=None, gate=None, full=None, verdict="accept", actor="ctrl"):
    d = {"target_id": target, "verdict": verdict, "reviewer": actor}
    if h:
        d["artifact_sha256"] = h
    if gate is not None:
        d["counts_as_gate_accept"] = gate
    if full is not None:
        d["counts_as_full_schema_verdict"] = full
    return d


H = LIVE["F2b"]
controls = []


def control(cid, desc, got, want):
    controls.append({"id": cid, "description": desc,
                     "expected": want, "observed": got, "passed": got == want})


r = rows_from(synth(gate=False, h=H), "synth", "ctrl", "", pins_repair, resolve_repair)
control("K1", "gate=false excluded by gate_ok",
        [x["gate"] for x in r], [False])
r = rows_from(synth(gate=None, h=H), "synth", "ctrl", "", pins_repair, resolve_repair)
control("K2", "gate absent (None) means gate accept", [x["gate"] for x in r], [True])
r = rows_from(synth(gate=True, h=H), "synth", "ctrl", "", pins_repair, resolve_repair)
control("K3", "gate=true included", [x["gate"] for x in r], [True])
r = rows_from(synth(full=False, h=H), "synth", "ctrl", "", pins_repair, resolve_repair)
control("K4", "full=false is a scoped verdict", [x["full"] for x in r], [False])
r = rows_from(synth(target="schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda"),
              "synth", "ctrl", "", pins_repair, resolve_repair)
control("K5", "path#hash target resolves to F2b (repair)", [x["target"] for x in r], ["F2b"])
r = rows_from(synth(target="schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6"),
              "synth", "ctrl", "", pins_repair, resolve_repair)
control("K6", "path#sha256: prefix resolves to F1 (repair)", [x["target"] for x in r], ["F1"])
r = rows_from(synth(h=H[:12]), "synth", "ctrl", "", pins_repair, resolve_repair)
control("K7", "12-hex prefix binds", [x["target"] for x in r], ["F2b"])
r = rows_from(synth(h="deadbeefcafe"), "synth", "ctrl", "", pins_repair, resolve_repair)
control("K8", "near-miss hash does not bind", r, [])
r = rows_from(synth(target="AF-SCC-C0-VAC-GEN", h=H), "synth", "ctrl", "",
              pins_repair, resolve_repair)
control("K9", "class-id alias resolves to F2b", [x["target"] for x in r], ["F2b"])
rows = (rows_from(synth(h=H, actor="a"), "s", "a", "2026-01-01T00:00:00+08:00",
                  pins_repair, resolve_repair)
        + rows_from({"target_id": "F2b", "verdict": "revise", "artifact_sha256": H,
                     "reviewer": "a"}, "s", "a", "2026-01-02T00:00:00+08:00",
                    pins_repair, resolve_repair))
kept = [x["verdict"] for x in latest_wins(rows)]
control("K10", "latest-verdict-wins drops the earlier accept", kept, ["revise"])
r = rows_from(synth(h=H, gate=False), "synth", "ctrl", "", pins_shipped, resolve_shipped)
control("K11", "shipped semantics ignore gate flag on a full record",
        [x["gate"] for x in r], [False])
r = rows_from(synth(target="schemas/af_scc_c0_vacuum.yaml", h=H), "synth", "ctrl", "",
              pins_shipped, resolve_shipped)
control("K12", "shipped semantics cannot resolve bare path target", r, [])

controls_passed = sum(1 for c in controls if c["passed"])

# --------------------------------------------------------------------------- #
# 6. report
# --------------------------------------------------------------------------- #
report = {
    "task_id": "W053-GATE-ACCEPT-SCOPE-01",
    "worker": "worker-053",
    "generated_at": now(),
    "node_id": "A1",
    "gate": "G-AUDIT",
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "question": ("Does the proposed union-stream repair of astra_lifecycle.review_coverage "
                 "honour declared gate-accept scope (counts_as_gate_accept)?"),
    "pins": {k: {"path": p.rel, "sha256": p.sha256} for k, p in pinned.items()},
    "review_corpus_digest": corpus_digest,
    "review_corpus_files": len(review_files),
    "events_total_records": len(event_rows),
    "events_unparsable_lines": bad_event_lines,
    "live_target_hashes": LIVE,
    "censuses": {
        "C1_shipped_files_full": C1,
        "C2_naive_union_full": C2,
        "C3_scoped_union_full_and_gate": C3,
        "C4_scoped_union_latest_wins": C4,
    },
    "controller_quoted_counts": ctrl_quote,
    "map_updated_at": map_updated,
    "leaked_full_accepts_with_gate_false": leaked,
    "all_accepts_with_gate_false": gate_false_accepts,
    "findings": [
        {
            "id": "GAS-01",
            "severity": "major",
            "finding": ("The union repair as proposed (files + accepted stream + path#hash "
                        "resolution, full-schema flag only) imports both live worker-089 "
                        "accepts (F2a@5476a3f2c6bc, F2b@55d0a1ea9bda) as gate accepts even "
                        "though the same records declare counts_as_gate_accept=false. Under "
                        "C2 F2b reaches two distinct accept reviewers {worker-089, worker-098}; "
                        "under C3 it does not. The per-class G-FORM criterion would be met for "
                        "F2b by a scoped accept that its own author excluded."),
            "falsifier": ("Falsified if the accepted-stream records w089-20260912T003959-review "
                          "or w089-20260912T004809-review do not carry counts_as_gate_accept=false, "
                          "or if the repair predicate already consults that key, or if either "
                          "target hash moves from the pinned values."),
        },
        {
            "id": "GAS-02",
            "severity": "major",
            "finding": ("The shipped scanner has no gate-accept handling at all: "
                        "counts_as_gate_accept occurs 0 times in research_map/astra_lifecycle.py "
                        "and 0 times in astra_lifecycle_05_events.py; a review file with "
                        "counts_as_gate_accept=false and no full-schema flag would be counted as "
                        "a full accept by review_coverage. The defect is symmetric to GAS-01."),
            "falsifier": ("Falsified if a later pinned astra_lifecycle revision consults "
                          "counts_as_gate_accept in the coverage path, or if a scoped file in "
                          "reviews/ with the key set false is reported as scoped by the scan."),
        },
        {
            "id": "GAS-03",
            "severity": "info",
            "finding": ("The repair changes which criteria are met and must be published with "
                        "its complete predicate: at the pins, C1 C2 C3 C4 counts are "
                        f"F0 {len(C1['F0'])}/{len(C2['F0'])}/{len(C3['F0'])}/{len(C4['F0'])}, "
                        f"F1 {len(C1['F1'])}/{len(C2['F1'])}/{len(C3['F1'])}/{len(C4['F1'])}, "
                        f"F2a {len(C1['F2a'])}/{len(C2['F2a'])}/{len(C3['F2a'])}/{len(C4['F2a'])}, "
                        f"F2b {len(C1['F2b'])}/{len(C2['F2b'])}/{len(C3['F2b'])}/{len(C4['F2b'])}, "
                        f"L0 {len(C1['L0'])}/{len(C2['L0'])}/{len(C3['L0'])}/{len(C4['L0'])}. "
                        "L0 gains worker-072; F2a gains only the scoped worker-089 accept."),
            "falsifier": ("Falsified if a re-run at the same pins with the documented predicate "
                          "returns different per-class reviewer sets."),
        },
        {
            "id": "GAS-04",
            "severity": "info",
            "finding": ("The leak is bounded: across both corpora exactly two live binding "
                        "accepts carry counts_as_gate_accept=false, both worker-089; no other "
                        "reviewer uses the key."),
            "falsifier": ("Falsified by any third live binding accept with "
                          "counts_as_gate_accept=false at the same pins."),
        },
    ],
    "checks": checks,
    "controls": controls,
    "controls_passed": controls_passed,
    "controls_total": len(controls),
    "drift_detected": drift_detected,
    "non_claims": [
        "No gate verdict, node status, validation_status or canonical artifact is set here.",
        "The controller's advisory scan remains controller-owned; this is a read-only audit.",
        "C2/C3/C4 are models of the proposed repair, not the shipped instrument.",
        "Counts are reviewer-name sets at one snapshot; they are not verdicts on review quality.",
    ],
    "rerun": "python3 artifacts/worker-053/gate_accept_scope/check_gate_accept_scope.py",
}
(OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
(OUT / "controls.json").write_text(json.dumps(
    {"controls": controls, "passed": controls_passed, "total": len(controls)},
    indent=2, sort_keys=True) + "\n")

print(f"pins: " + ", ".join(f"{k}={p.short}" for k, p in pinned.items()))
print(f"review corpus {corpus_digest[:12]} ({len(review_files)} files); "
      f"events {pinned['events'].short} ({len(event_rows)} records)")
print("censuses (shipped / naive union / scoped union / scoped+latest):")
for t in TARGET_PATHS:
    print(f"  {t:4s} {len(C1[t])} / {len(C2[t])} / {len(C3[t])} / {len(C4[t])}"
          f"   C3={C3[t]}")
print("leaked gate=false accepts:", [r["src"] for r in leaked])
print(f"checks: {sum(1 for c in checks if c['status'] == 'pass')}/{len(checks)} pass; "
      f"controls {controls_passed}/{len(controls)}; drift={drift_detected}")
for c in checks:
    if c["status"] == "FAIL":
        print("  FAIL", c["id"], c["detail"])
print("done; report.json + controls.json written")
sys.exit(0)
