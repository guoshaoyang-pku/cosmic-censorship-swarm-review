#!/usr/bin/env python3
"""W057-GNUM-PROTOCOL-REVIEW-CENSUS-01 — independent census of the pinned
``numerics/gates.py::_protocol_review`` rule at the protocol of record.

Class-bound: class_id AF-WCC-SCALAR-SPH, node N0, gate G-NUM.  Read-only: this
instrument writes only ``report.json`` and ``census.json`` next to itself and
never touches a canonical artifact.  It is advisory evidence for REC-15 /
B-N0-R2-2 (the standing protocol contest); it sets no gate verdict and does not
release ``numerics_lock`` / N1.

Three channels:
  A. independent stdlib re-implementation of the documented rule (no author code
     imported), run on a frozen in-memory snapshot of the review stream;
  B. the pinned module itself (``numerics.gates._protocol_review``) executed in a
     subprocess, on the same snapshot and on a synthetic fixture matrix;
  C. the pinned CLI (``python3 numerics/gates.py --pretty``) end to end, with the
     stream source bytes hashed immediately before and after.

Exit 0 iff every pre-registered expectation and every fail-closed control holds.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT_REPORT = HERE / "report.json"
OUT_CENSUS = HERE / "census.json"

# ---------------------------------------------------------------- pins -------
# Blob pins that must NOT move: if either differs, the premise of the census
# (which bytes define the rule / which revision is contested) is void.
PINS = {
    "numerics/gates.py": "fcd1d70991b6eade4aa993dc49b6103e338f68320aabb955d97da5a8f55d996e",
    "numerics/CONVERGENCE_PROTOCOL.md": "1e6cdf04d7a2431373092b657095bab4edeea9fb32f1d3c8981c50b2156a7274",
}
# The review stream is live; this is the pin taken when the task was scoped.
# A move is recorded (stream_moved) and re-bound, not treated as fatal.
DECLARED_EVENTS_PIN = "b0ce9a8eda06a7bc8b29ec032340ea595e760e4dbdfc3b9efecd46f24cf4d8dc"

# Constants transcribed from the pinned gates.py (also asserted as literal
# source fragments below, so a silent constant change cannot pass).
PROTOCOL_REVIEW_TARGETS = (
    "numerics/CONVERGENCE_PROTOCOL.md",
    "G-NUM-protocol",
    "N0",
)
PROTOCOL_REVIEW_SELF = "astra-lead-numerics"
PROTOCOL_PATH = "numerics/CONVERGENCE_PROTOCOL.md"
VERDICTS = ("accept", "revise", "reject")

PIN_CHECK_TOLERANCE = 0  # exact match required

# ------------------------------------------------------------- utilities -----


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical_digest(obj) -> str:
    return sha256_bytes(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def stream_sources(root: Path) -> list[Path]:
    """Exactly the source set/order of the pinned ``load_event_stream``:
    accepted stream first, then sorted outbox, then sorted inbox."""
    sources = [root / "research_map" / "events.jsonl"]
    for folder in (root / "comms" / "outbox", root / "comms" / "inbox"):
        if folder.is_dir():
            sources.extend(sorted(folder.rglob("*.jsonl")))
    return [p for p in sources if p.is_file()]


def snapshot_stream(root: Path) -> tuple[list[dict], dict]:
    """Read every source once; return (events, provenance)."""
    events: list[dict] = []
    files: dict[str, str] = {}
    for p in stream_sources(root):
        raw = p.read_bytes()
        rel = str(p.relative_to(root))
        files[rel] = sha256_bytes(raw)
        for line in raw.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(doc, dict):
                doc["__source"] = rel
                events.append(doc)
    return events, {"source_hashes": files, "n_sources": len(files), "n_events": len(events)}


# ------------------------------------------------- channel A: independent ----


def targets_protocol(target: str) -> bool:
    t = target.strip()
    for cand in PROTOCOL_REVIEW_TARGETS:
        if t == cand or t.startswith(cand + "#") or t.startswith(cand + "@"):
            return True
    return False


def cited_hashes(e: dict) -> list[str]:
    """Re-implementation of the pinned ``_review_cited_hashes`` including its
    no-break loop over ('#sha256:', '#') which can append both readings."""
    out: list[str] = []
    for k in ("reviewed_sha256", "artifact_sha256", "reviewed_protocol_hash"):
        v = e.get(k)
        if isinstance(v, str) and len(v.strip()) >= 12:
            out.append(v.strip().lower())
    for ref in e.get("evidence_refs", []) or []:
        if not isinstance(ref, str):
            continue
        for sep in ("#sha256:", "#"):
            if ref.startswith(PROTOCOL_PATH + sep):
                h = ref.split(sep, 1)[1].strip().lower()
                if len(h) >= 12:
                    out.append(h)
    return out


def class_a_census(events: list[dict], protocol_sha: str) -> dict:
    accepts: list[str] = []
    dissents: list[dict] = []
    advisory: list[dict] = []
    seen: set[str] = set()
    target = protocol_sha.lower()
    for e in events:
        if e.get("event_type") != "review":
            continue
        verdict = e.get("verdict")
        if verdict not in VERDICTS:
            continue
        if not targets_protocol(str(e.get("target_id", ""))):
            continue
        if e.get("reviewer") == PROTOCOL_REVIEW_SELF:
            continue
        eid = str(e.get("event_id") or id(e))
        if eid in seen:
            continue
        seen.add(eid)
        cited = cited_hashes(e)
        binds = bool(target) and any(
            target.startswith(c) or c.startswith(target) for c in cited
        )
        base = {
            "event_id": eid,
            "reviewer": e.get("reviewer"),
            "verdict": verdict,
            "score": e.get("score"),
            "created_at": e.get("created_at"),
            "target_id": e.get("target_id"),
            "cited": cited,
            "first_source": e.get("__source"),
        }
        if not binds:
            advisory.append(base)
            continue
        if verdict == "accept":
            accepts.append(eid)
        else:
            dissents.append(base)
    return {
        "reviewed": bool(accepts),
        "accepting_reviews": accepts,
        "dissenting_reviews": dissents,
        "contest": bool(dissents),
        "advisory_reviews_at_other_hashes": advisory,
        "protocol_sha256_measured": protocol_sha,
        "reviewed_protocol_sha256": protocol_sha if accepts else None,
    }


def binding_records(events: list[dict], protocol_sha: str) -> list[dict]:
    """Binding review events in stream order (dedup by event_id), full records."""
    out: list[dict] = []
    seen: set[str] = set()
    target = protocol_sha.lower()
    for e in events:
        if e.get("event_type") != "review" or e.get("verdict") not in VERDICTS:
            continue
        if not targets_protocol(str(e.get("target_id", ""))):
            continue
        if e.get("reviewer") == PROTOCOL_REVIEW_SELF:
            continue
        eid = str(e.get("event_id") or id(e))
        if eid in seen:
            continue
        seen.add(eid)
        if any(target.startswith(c) or c.startswith(target) for c in cited_hashes(e)):
            out.append(e)
    return out


# ------------------------------------------------- channel B: pinned code ---

DRIVER = r"""
import json, sys
from pathlib import Path
root = Path(sys.argv[1]); mode = sys.argv[2]
sys.path.insert(0, str(root))
from numerics.gates import _protocol_review, load_event_stream
payload = json.load(sys.stdin)
if mode == "stream":
    events = load_event_stream(root)
else:
    events = payload["events"]
print(json.dumps(_protocol_review(events, payload["protocol_sha"]), sort_keys=True))
"""


def run_pinned(payload: dict, mode: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", DRIVER, str(REPO), mode],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=900,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pinned driver failed rc={proc.returncode}: {proc.stderr[:800]}")
    return json.loads(proc.stdout)


def run_cli() -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, "numerics/gates.py", "--pretty"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=900,
    )
    return json.loads(proc.stdout), proc.returncode


# ----------------------------------------------------------- comparison ------


def norm_result(d: dict) -> dict:
    """Comparable projection of a protocol_review block."""
    return {
        "reviewed": d.get("reviewed"),
        "contest": d.get("contest"),
        "accepts": sorted(d.get("accepting_reviews") or []),
        "dissents": sorted(
            (x.get("event_id"), x.get("verdict"), x.get("reviewer"))
            for x in (d.get("dissenting_reviews") or [])
        ),
        "advisory": sorted(
            (x.get("event_id"), x.get("verdict"))
            for x in (d.get("advisory_reviews_at_other_hashes") or [])
        ),
        "protocol_sha256_measured": d.get("protocol_sha256_measured"),
    }


# ------------------------------------------------------------- fixtures -----

H = PINS["numerics/CONVERGENCE_PROTOCOL.md"]


def ev(eid, verdict, reviewer, target="numerics/CONVERGENCE_PROTOCOL.md", cite=None,
       event_type="review"):
    e = {
        "event_id": eid,
        "event_type": event_type,
        "created_at": "2026-09-12T00:00:00+08:00",
        "actor": reviewer,
        "target_id": target,
        "reviewer": reviewer,
        "verdict": verdict,
    }
    if cite is not None:
        e["reviewed_sha256"] = cite
    return e


def fixtures() -> list[dict]:
    return [
        {
            "id": "F1-single-accept",
            "events": [ev("a1", "accept", "r1", cite=H)],
            "expect": {"reviewed": True, "contest": False, "n_accepts": 1, "n_dissents": 0,
                       "n_advisory": 0},
        },
        {
            "id": "F2-accept-then-revise-same-reviewer",
            "events": [ev("a1", "accept", "r1", cite=H), ev("a2", "revise", "r1", cite=H)],
            "expect": {"reviewed": True, "contest": True, "n_accepts": 1, "n_dissents": 1,
                       "n_advisory": 0},
        },
        {
            "id": "F3-revise-then-accept-same-reviewer",
            "events": [ev("a1", "revise", "r1", cite=H), ev("a2", "accept", "r1", cite=H)],
            "expect": {"reviewed": True, "contest": True, "n_accepts": 1, "n_dissents": 1,
                       "n_advisory": 0},
        },
        {
            "id": "F4-self-review-excluded",
            "events": [
                ev("a1", "accept", PROTOCOL_REVIEW_SELF, cite=H),
                ev("a2", "revise", PROTOCOL_REVIEW_SELF, cite=H),
            ],
            "expect": {"reviewed": False, "contest": False, "n_accepts": 0, "n_dissents": 0,
                       "n_advisory": 0},
        },
        {
            "id": "F5-stale-hash-advisory-only",
            "events": [ev("a1", "revise", "r1", cite="0" * 64)],
            "expect": {"reviewed": False, "contest": False, "n_accepts": 0, "n_dissents": 0,
                       "n_advisory": 1},
        },
        {
            "id": "F6-uncited-review-advisory-only",
            "events": [ev("a1", "revise", "r1", cite=None)],
            "expect": {"reviewed": False, "contest": False, "n_accepts": 0, "n_dissents": 0,
                       "n_advisory": 1},
        },
        {
            "id": "F7-duplicate-event-id-deduped",
            "events": [ev("dup", "accept", "r1", cite=H), ev("dup", "accept", "r1", cite=H)],
            "expect": {"reviewed": True, "contest": False, "n_accepts": 1, "n_dissents": 0,
                       "n_advisory": 0},
        },
        {
            "id": "F8-N0-target-with-cited-pin-binds",
            "events": [ev("a1", "accept", "r1", target="N0#" + H, cite=H)],
            "expect": {"reviewed": True, "contest": False, "n_accepts": 1, "n_dissents": 0,
                       "n_advisory": 0},
        },
        {
            "id": "F8b-target-pin-alone-does-not-bind",
            "events": [ev("a1", "accept", "r1", target="N0#" + H, cite=None)],
            "expect": {"reviewed": False, "contest": False, "n_accepts": 0, "n_dissents": 0,
                       "n_advisory": 1},
        },
        {
            "id": "F9-other-target-ignored",
            "events": [ev("a1", "accept", "r1", target="numerics/CONVERGENCE_PROTOCOL_X.md",
                          cite=H)],
            "expect": {"reviewed": False, "contest": False, "n_accepts": 0, "n_dissents": 0,
                       "n_advisory": 0},
        },
        {
            "id": "F10-12char-prefix-binds-and-mismatch-advisory",
            "events": [ev("a1", "accept", "r1", cite=H[:12]),
                       ev("a2", "revise", "r2", cite="f" * 12)],
            "expect": {"reviewed": True, "contest": False, "n_accepts": 1, "n_dissents": 0,
                       "n_advisory": 1},
        },
        {
            "id": "F11-revise-then-reject-both-stand",
            "events": [ev("a1", "revise", "r1", cite=H), ev("a2", "reject", "r1", cite=H)],
            "expect": {"reviewed": False, "contest": True, "n_accepts": 0, "n_dissents": 2,
                       "n_advisory": 0},
        },
        {
            "id": "F12-independent-accept-plus-dissent-contested",
            "events": [ev("a1", "accept", "r1", cite=H), ev("a2", "revise", "r2", cite=H)],
            "expect": {"reviewed": True, "contest": True, "n_accepts": 1, "n_dissents": 1,
                       "n_advisory": 0},
        },
        {
            "id": "F13-withdrawal-event-type-not-counted",
            "events": [ev("a1", "revise", "r1", cite=H),
                       {"event_id": "w1", "event_type": "withdrawal",
                        "created_at": "2026-09-12T00:00:01+08:00", "actor": "r1",
                        "target_id": "numerics/CONVERGENCE_PROTOCOL.md", "reviewer": "r1",
                        "verdict": "accept", "reviewed_sha256": H}],
            "expect": {"reviewed": False, "contest": True, "n_accepts": 0, "n_dissents": 1,
                       "n_advisory": 0},
        },
    ]


def fixture_expectation_diff(res: dict, expect: dict) -> list[str]:
    got = {
        "reviewed": res.get("reviewed"),
        "contest": res.get("contest"),
        "n_accepts": len(res.get("accepting_reviews") or []),
        "n_dissents": len(res.get("dissenting_reviews") or []),
        "n_advisory": len(res.get("advisory_reviews_at_other_hashes") or []),
    }
    return [f"{k}: expected {v!r} got {got.get(k)!r}" for k, v in expect.items() if got.get(k) != v]


# ------------------------------------------------ counterfactual rules -------


def counterfactual(events: list[dict], protocol_sha: str, rule: str) -> dict:
    """Apply a candidate supersession rule to the same binding event set.

    V1 latest-per-reviewer: keep only each reviewer's latest binding review.
    V2e latest-per-(reviewer,target_id exact); V2n latest-per-(reviewer,target
    normalized to the protocol family).  Ordering: created_at then source order.
    """
    binding = []
    seen = set()
    for i, e in enumerate(events):
        if e.get("event_type") != "review" or e.get("verdict") not in VERDICTS:
            continue
        if not targets_protocol(str(e.get("target_id", ""))):
            continue
        if e.get("reviewer") == PROTOCOL_REVIEW_SELF:
            continue
        eid = str(e.get("event_id") or id(e))
        if eid in seen:
            continue
        seen.add(eid)
        cited = cited_hashes(e)
        binds = bool(protocol_sha) and any(
            protocol_sha.startswith(c) or c.startswith(protocol_sha) for c in cited
        )
        if binds:
            binding.append((i, e))

    def key_of(e):
        if rule == "V1":
            return (e.get("reviewer"),)
        if rule == "V2e":
            return (e.get("reviewer"), str(e.get("target_id", "")).strip())
        return (e.get("reviewer"), "protocol-family")

    latest: dict = {}
    for i, e in binding:
        k = key_of(e)
        prev = latest.get(k)
        ts = str(e.get("created_at", ""))
        if prev is None or ts >= str(prev[1].get("created_at", "")):
            latest[k] = (i, e)
    kept = {e.get("event_id") for _, e in latest.values()}
    accepts, dissents = [], []
    for _, e in binding:
        if e.get("event_id") not in kept:
            continue
        (accepts if e.get("verdict") == "accept" else dissents).append(e.get("event_id"))
    return {
        "rule": rule,
        "n_binding": len(binding),
        "kept_accepts": accepts,
        "kept_dissents": dissents,
        "reviewed_under_rule": bool(accepts),
        "contest_under_rule": bool(dissents),
        "dropped": sorted(e.get("event_id") for _, e in binding
                          if e.get("event_id") not in kept),
    }


# ---------------------------------------------------------------- main -------


def main() -> int:
    started = time.time()
    checks: list[dict] = []
    controls: list[dict] = []

    def check(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})
        return bool(ok)

    def control(cid, ok, detail):
        controls.append({"id": cid, "ok": bool(ok), "detail": detail})
        return bool(ok)

    # --- E1: pins -----------------------------------------------------------
    measured = {rel: sha256_file(REPO / rel) for rel in PINS}
    pins_ok = all(measured[r] == PINS[r] for r in PINS)
    check("E1-pins", pins_ok, {"declared": PINS, "measured": measured})
    if not pins_ok:
        OUT_REPORT.write_text(json.dumps(
            {"task_id": "W057-GNUM-PROTOCOL-REVIEW-CENSUS-01", "verdict": "PIN_MOVED",
             "checks": checks, "controls": controls}, indent=2, sort_keys=True))
        print("FAIL E1 pins moved")
        return 1
    protocol_sha = measured["numerics/CONVERGENCE_PROTOCOL.md"]
    gates_sha = measured["numerics/gates.py"]

    # literal source fragments: constants and the contest expression
    gates_src = (REPO / "numerics/gates.py").read_text()
    fragments = {
        "targets": 'PROTOCOL_REVIEW_TARGETS = (\n    "numerics/CONVERGENCE_PROTOCOL.md",\n'
                   '    "G-NUM-protocol",\n    "N0",\n)',
        "self": 'PROTOCOL_REVIEW_SELF = "astra-lead-numerics"',
        "seen": "        if eid in seen:\n            continue\n        seen.add(eid)",
        "contest": '"contest": bool(dissents),',
        "reviewed": '"reviewed": bool(accepts),',
    }
    frag_ok = {k: (v in gates_src) for k, v in fragments.items()}
    check("E1b-source-fragments", all(frag_ok.values()), frag_ok)

    # --- snapshot -----------------------------------------------------------
    events, prov = snapshot_stream(REPO)
    stream_pin = prov["source_hashes"].get("research_map/events.jsonl")
    check(
        "E1c-stream-pin",
        True,
        {"declared": DECLARED_EVENTS_PIN, "measured": stream_pin,
         "moved_since_scoping": stream_pin != DECLARED_EVENTS_PIN,
         "n_events": prov["n_events"]},
    )

    # --- channel A ----------------------------------------------------------
    a = class_a_census(events, protocol_sha)
    check("E2-classA-reproduced", a["reviewed"] and a["contest"],
          {"reviewed": a["reviewed"], "contest": a["contest"],
           "n_accepts": len(a["accepting_reviews"]),
           "n_dissents": len(a["dissenting_reviews"])})

    # --- channel B on the same snapshot ------------------------------------
    b_events = run_pinned({"events": events, "protocol_sha": protocol_sha}, mode="events")
    ab_same = norm_result(a) == norm_result(b_events)
    check("E5-A-equals-B", ab_same,
          {"A": norm_result(a), "B": norm_result(b_events)})

    # --- channel B on its own re-read of the live stream --------------------
    b_stream = run_pinned({"protocol_sha": protocol_sha}, mode="stream")
    check("E5b-B-stream-matches-A-snapshot", norm_result(b_stream) == norm_result(a),
          {"n_accepts": len(b_stream.get("accepting_reviews") or []),
           "n_dissents": len(b_stream.get("dissenting_reviews") or []),
           "contest": b_stream.get("contest")})

    # --- channel C: CLI, with stream bytes hashed around it -----------------
    pre = {str(p.relative_to(REPO)): sha256_file(p) for p in stream_sources(REPO)}
    cli, rc = run_cli()
    post = {str(p.relative_to(REPO)): sha256_file(p) for p in stream_sources(REPO)}
    cli_pr = cli.get("protocol_review", {})
    ac_same = norm_result(a) == norm_result(cli_pr)
    check("E6-A-equals-CLI", ac_same,
          {"cli_exit": rc, "stream_bytes_stable_around_cli": pre == post,
           "cli": norm_result(cli_pr)})

    # --- E3/E4: census substance -------------------------------------------
    dissent_ids = sorted(x["event_id"] for x in a["dissenting_reviews"])
    accept_ids = sorted(a["accepting_reviews"])
    check("E3-census-lists",
          len(accept_ids) >= 1 and len(dissent_ids) >= 1,
          {"accepts": accept_ids, "dissents": dissent_ids})
    w081 = [x for x in a["dissenting_reviews"] if x["reviewer"] == "worker-081"]
    check("E4-worker-081-holds-accept-and-revise-at-one-hash",
          len(w081) == 1 and "w081-20260912T0042050800-adj2-review" in accept_ids,
          {"binding_revise": [x["event_id"] for x in w081],
           "binding_accepts_by_worker_081": sorted(
               x for x in a["accepting_reviews"] if x.startswith("w081"))})

    # --- E7: fixture matrix -------------------------------------------------
    fixture_rows = []
    fx_ok = True
    for fx in fixtures():
        exp = fx["expect"]
        a_fx = class_a_census(fx["events"], protocol_sha)
        b_fx = run_pinned({"events": fx["events"], "protocol_sha": protocol_sha},
                          mode="events")
        a_diff = fixture_expectation_diff(a_fx, exp)
        b_diff = fixture_expectation_diff(b_fx, exp)
        agree = norm_result(a_fx) == norm_result(b_fx)
        ok = not a_diff and not b_diff and agree
        fx_ok = fx_ok and ok
        fixture_rows.append({
            "id": fx["id"], "ok": ok, "expect": exp,
            "channel_A_diff": a_diff, "channel_B_diff": b_diff,
            "A_equals_B": agree,
            "B": {"reviewed": b_fx.get("reviewed"), "contest": b_fx.get("contest"),
                  "accepts": sorted(b_fx.get("accepting_reviews") or []),
                  "dissents": sorted(x.get("event_id") for x in
                                     (b_fx.get("dissenting_reviews") or [])),
                  "advisory": sorted(x.get("event_id") for x in
                                     (b_fx.get("advisory_reviews_at_other_hashes") or []))},
        })
    check("E7-fixture-matrix", fx_ok, fixture_rows)

    # --- E8: counterfactual supersession rules -----------------------------
    # Structural, stream-robust assertions (the stream is live).
    cf = {r: counterfactual(events, protocol_sha, r) for r in ("V1", "V2e", "V2n")}
    brecs = binding_records(events, protocol_sha)
    lates: dict = {}
    for e in brecs:
        k = e.get("reviewer")
        if k not in lates or str(e.get("created_at", "")) >= str(
                lates[k].get("created_at", "")):
            lates[k] = e
    expected_v1_drop = {e["event_id"] for e in brecs
                        if lates[e.get("reviewer")]["event_id"] != e["event_id"]}
    expected_v1_keep = {e["event_id"] for e in brecs} - expected_v1_drop
    late_accept_over_dissent = any(
        any(x.get("verdict") == "accept" and
            str(x.get("created_at", "")) >= str(d.get("created_at", ""))
            for x in brecs if x.get("reviewer") == d.get("reviewer"))
        for d in brecs if d.get("verdict") != "accept")
    check("E8-counterfactuals",
          set(cf["V1"]["dropped"]) == expected_v1_drop and
          set(cf["V1"]["kept_accepts"]) | set(cf["V1"]["kept_dissents"]) == expected_v1_keep and
          set(cf["V2e"]["dropped"]) <= set(cf["V1"]["dropped"]) and
          cf["V1"]["contest_under_rule"] is True and late_accept_over_dissent,
          {"counterfactuals": cf, "expected_v1_drop": sorted(expected_v1_drop),
           "late_accept_over_dissent_property": late_accept_over_dissent})

    # --- E9: no reviewer-keyed supersession state in the pinned function ----
    fn = gates_src.split("def _protocol_review", 1)[1].split("\ndef ", 1)[0]
    has_seen_by_event = "if eid in seen:" in fn and "seen.add(eid)" in fn
    has_reviewer_state = bool(re.search(r"reviewer[^\n]*\b(dict|set|latest|supersed)", fn, re.I))
    check("E9-no-supersession-state",
          has_seen_by_event and not has_reviewer_state and '"contest": bool(dissents)' in fn,
          {"seen_is_event_id_keyed": has_seen_by_event,
           "reviewer_keyed_state_regex_hit": has_reviewer_state,
           "contest_is_bool_dissents": '"contest": bool(dissents)' in fn})

    # --- E10: advisory (stale/uncited) census -------------------------------
    check("E10-advisory-listed", True,
          [{"event_id": x["event_id"], "verdict": x["verdict"],
            "cited": x["cited"]} for x in a["advisory_reviews_at_other_hashes"]])

    # --- controls (fail-closed) --------------------------------------------
    import tempfile

    with tempfile.TemporaryDirectory(prefix="w057census_") as td:
        td = Path(td)
        # C1/C2: the pin checker must reject a one-byte edit
        for rel in ("numerics/gates.py", "numerics/CONVERGENCE_PROTOCOL.md"):
            raw = (REPO / rel).read_bytes()
            t = td / Path(rel).name
            t.write_bytes(raw[:-1] + (b"X" if raw[-1:] != b"X" else b"Y"))
            control("C-" + rel, sha256_file(t) != PINS[rel],
                    "one-byte edit changes the pin")
        # C3: flipping every binding dissent to accept must clear the contest
        dissent_ids = {x["event_id"] for x in a["dissenting_reviews"]}
        accept_ids_now = set(a["accepting_reviews"])
        flip = [dict(e) for e in events]
        for e in flip:
            if e.get("event_id") in dissent_ids:
                e["verdict"] = "accept"
        c3 = run_pinned({"events": flip, "protocol_sha": protocol_sha}, mode="events")
        control("C3-flip-all-dissents",
                c3.get("contest") is False and c3.get("reviewed") is True,
                {"contest_after_flip": c3.get("contest"),
                 "reviewed_after_flip": c3.get("reviewed"),
                 "n_flipped": len(dissent_ids)})
        # C3b: flipping every binding accept to revise must clear reviewed and contest
        flip2 = [dict(e) for e in events]
        for e in flip2:
            if e.get("event_id") in accept_ids_now:
                e["verdict"] = "revise"
        c3b = run_pinned({"events": flip2, "protocol_sha": protocol_sha}, mode="events")
        control("C3b-flip-all-accepts",
                c3b.get("reviewed") is False and c3b.get("contest") is True,
                {"reviewed_after_flip": c3b.get("reviewed"),
                 "contest_after_flip": c3b.get("contest"),
                 "n_flipped": len(accept_ids_now)})
        # C4: non-target is ignored
        c4 = run_pinned({"events": [ev("x", "accept", "r", target="NUMERICS",
                                       cite=protocol_sha)], "protocol_sha": protocol_sha},
                        mode="events")
        control("C4-non-target", c4.get("reviewed") is False, c4.get("reviewed"))
        # C5: self-review cannot turn reviewed green
        c5 = run_pinned({"events": [ev("x", "accept", PROTOCOL_REVIEW_SELF, cite=protocol_sha)],
                         "protocol_sha": protocol_sha}, mode="events")
        control("C5-self-review", c5.get("reviewed") is False, c5.get("reviewed"))
        # C6: uncited review is advisory only
        c6 = run_pinned({"events": [ev("x", "revise", "r")], "protocol_sha": protocol_sha},
                        mode="events")
        control("C6-uncited", (c6.get("contest") is False and
                               len(c6.get("advisory_reviews_at_other_hashes") or []) == 1),
                {"contest": c6.get("contest"),
                 "n_advisory": len(c6.get("advisory_reviews_at_other_hashes") or [])})
        # C7: 12-char prefix binds, mismatch does not
        c7 = run_pinned({"events": [ev("p", "accept", "r", cite=protocol_sha[:12]),
                                    ev("q", "accept", "r2", cite="e" * 12)],
                         "protocol_sha": protocol_sha}, mode="events")
        control("C7-prefix", (c7.get("reviewed") is True and
                              len(c7.get("advisory_reviews_at_other_hashes") or []) == 1),
                {"reviewed": c7.get("reviewed"),
                 "n_advisory": len(c7.get("advisory_reviews_at_other_hashes") or [])})

    # --- re-hash pins at exit ----------------------------------------------
    measured_end = {rel: sha256_file(REPO / rel) for rel in PINS}
    check("E1d-pins-stable-start-to-end", measured_end == measured, measured_end)

    ok = all(c["ok"] for c in checks) and all(c["ok"] for c in controls)
    census_block = {
        "protocol_sha256": protocol_sha,
        "reviewed": a["reviewed"],
        "contest": a["contest"],
        "binding_accepts": sorted(a["accepting_reviews"]),
        "binding_dissents": [
            {k: x[k] for k in ("event_id", "reviewer", "verdict", "score", "created_at",
                               "target_id", "cited", "first_source")}
            for x in sorted(a["dissenting_reviews"], key=lambda z: z["event_id"])],
        "advisory": [
            {k: x[k] for k in ("event_id", "reviewer", "verdict", "cited")}
            for x in sorted(a["advisory_reviews_at_other_hashes"], key=lambda z: z["event_id"])],
        "cli_block": norm_result(cli_pr),
        "channel_agreement": {
            "A_equals_B_events": ab_same,
            "A_equals_B_stream": norm_result(b_stream) == norm_result(a),
            "A_equals_CLI": ac_same,
            "stream_bytes_stable_around_cli": pre == post,
        },
        "counterfactual_supersession": cf,
        "worker_081_dual_status": {
            "binding_revise": [x["event_id"] for x in w081],
            "binding_accepts": sorted(x for x in a["accepting_reviews"]
                                      if x.startswith("w081")),
            "contest_due_to_same_reviewer": bool(w081) and
            "w081-20260912T0042050800-adj2-review" in a["accepting_reviews"],
        },
    }
    report = {
        "schema": "worker-verification-report/v1",
        "task_id": "W057-GNUM-PROTOCOL-REVIEW-CENSUS-01",
        "worker": "worker-057",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "node_id": "N0",
        "gate": "G-NUM",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "runtime_seconds": round(time.time() - started, 2),
        "verdict": "CENSUS_CONFIRMED" if ok else "CENSUS_FAILED",
        "pins": {"gates.py": gates_sha, "protocol": protocol_sha,
                 "events_jsonl": stream_pin, "declared_events_pin": DECLARED_EVENTS_PIN,
                 "stream_moved_since_scoping": stream_pin != DECLARED_EVENTS_PIN},
        "stream_provenance": {"n_sources": prov["n_sources"], "n_events": prov["n_events"],
                              "source_hashes": prov["source_hashes"]},
        "census": census_block,
        "census_digest": canonical_digest(census_block),
        "expectations": checks,
        "controls": controls,
        "falsifier": (
            "Re-run this instrument at the same pins (numerics/gates.py "
            + gates_sha[:12] + ", numerics/CONVERGENCE_PROTOCOL.md " + protocol_sha[:12] +
            "): the census block is falsified if any channel disagrees, if any expectation "
            "or control fails, if the binding accept/dissent sets differ from the listed "
            "event_ids, or if a fresh run of the pinned gates.py at these bytes reports a "
            "different protocol_review block. A moved gates.py or protocol hash voids the "
            "census for the new bytes; the review stream is live, so any appended review "
            "event re-binds the census for the new stream bytes."
        ),
        "non_claims": [
            "worker evidence only; no gate verdict, no node status, no validation_status",
            "does not adjudicate whether worker-067/worker-081 findings are correct",
            "does not propose or apply any change to numerics/gates.py",
            "does not release numerics_lock or authorize N1",
        ],
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True))
    census_doc = {
        "schema": "protocol-review-census/v1",
        "task_id": report["task_id"],
        "created_at": report["created_at"],
        "pins": report["pins"],
        "census": census_block,
        "fixtures": fixture_rows,
        "source_order": [str(p.relative_to(REPO)) for p in stream_sources(REPO)],
    }
    OUT_CENSUS.write_text(json.dumps(census_doc, indent=2, sort_keys=True))
    print(json.dumps({
        "verdict": report["verdict"],
        "checks": f"{sum(c['ok'] for c in checks)}/{len(checks)}",
        "controls": f"{sum(c['ok'] for c in controls)}/{len(controls)}",
        "report_sha256": sha256_file(OUT_REPORT),
        "census_sha256": sha256_file(OUT_CENSUS),
        "census_digest": report["census_digest"],
    }, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
