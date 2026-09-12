#!/usr/bin/env python3
"""W070-GFORM-CLAIM-REDUNDANCY-01 instrument (read-only; stdlib only).

Question: at a pinned snapshot of the accepted event stream, how much of the
G-FORM claim traffic is *distinct evidential basis* and how much is restatement?

Method (pre-registered in frame.json, written before the analysis run):
  * snapshot research_map/events.jsonl byte-for-byte, hash source before/after copy;
  * universe U = claim events whose class binding (class_id + class_ids) intersects
    the three G-FORM classes {AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN};
  * per claim, extract sha256 tokens (>=12 hex, normalised to first 12 lower-case)
    from declared reference keys; the *evidence signature* is the sorted set of
    distinct tokens;
  * cluster U by exact signature equality. Claims in one cluster cite the same
    set of hashes, i.e. share their entire declared evidential basis;
  * report distinct-signature count (effective independent bases), redundancy
    factor, cluster-size histogram, exact-statement duplicates, per-class split,
    and the largest clusters with actors/tasks.

Authority: worker evidence only. No gate verdict, no node status, no canonical
write, no ingest. The instrument cannot set validation_status=passed.

Usage:
  python3 census_070_redundancy.py --preregister
  python3 census_070_redundancy.py --run
Exit codes: 0 ok; 2 snapshot/void condition; 3 control or identity failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SRC = ROOT / "research_map" / "events.jsonl"
FRAME = OUT / "frame.json"
FRAME_SEAL = OUT / "frame.sha256.txt"
REPORT = OUT / "report.json"
RUNLOG = OUT / "run.log"
CST = timezone(timedelta(hours=8))

TASK_ID = "W070-GFORM-CLAIM-REDUNDANCY-01"
REVISION = "rev3"
REVISION_NOTE = (
    "rev1 aborted with AttributeError inside control C5 and rev2 with TypeError inside "
    "control C7, both before any measurement or report was produced. rev3 fixes the two "
    "control-only bugs. Declared rules, universe, extraction, metrics and controls are "
    "unchanged across revisions; frames were re-sealed at later snapshots because the "
    "live event stream kept growing (4a91d47afa94 -> 9973feb4c5fe -> this frame)."
)
GATE = "G-FORM"
GROUPS = "F1,F2a,F2b"
GFORM_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
REV29_FROZEN_HASH = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"

# Declared reference-bearing keys. Hash tokens are only extracted from these.
REF_KEYS = {
    "artifact_refs", "evidence_refs", "artifact_ref", "artifact_sha256",
    "reviewed_sha256", "ledger_sha256", "source_sha256", "sha256", "hash",
    "pins", "reviewed_pins", "frozen_manifest", "manifest_sha256",
    "frozen_rev29_pin", "entry_hashes", "exit_hashes", "reviewed_frozen_sha256",
    "reviewed_mirror_sha256", "supersedes_sha256", "base_sha256", "frozen_sha256",
}
HEX_TOKEN = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{12,64}(?![0-9a-fA-F])")
HEX_ONLY = re.compile(r"^[0-9a-fA-F]{12,64}$")

FALSIFIER = (
    "Re-run `census_070_redundancy.py --run` against the same snapshot sha256 "
    "recorded in frame.json. Falsified if any reported count, signature, cluster "
    "membership or control outcome differs between runs; falsified if any claim in "
    "the universe is shown to cite a hash token outside its reported signature, or "
    "if two claims reported in one cluster are shown to have non-identical declared "
    "reference sets. A snapshot sha256 that does not equal frame.snapshot_sha256, or "
    "an events.jsonl source hash that changes across the preregistration copy, voids "
    "the run rather than falsifying it; the finding is snapshot-bound and asserts "
    "nothing about cosmic censorship, no gate verdict and no node status."
)
NON_CLAIMS = [
    "Not a mathematics or physics claim; the object under test is the accepted event stream.",
    "Not a verdict on any artifact, reviewer or gate; worker evidence only.",
    "The count of distinct evidence signatures is a structural measure of shared declared hashes, not proof that two claims with different signatures are independent in method.",
    "Snapshot-bound: traffic continues; the snapshot sha256 is the artifact identity.",
    "No canonical path was written; no ingest was run; no node status or validation_status changed.",
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    print(line)
    with RUNLOG.open("a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------- extraction

def collect_strings(value, out: list) -> None:
    """Recursively collect strings under a declared reference key."""
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and HEX_ONLY.match(k):
                out.append(k)
            collect_strings(v, out)
    elif isinstance(value, list):
        for v in value:
            collect_strings(v, out)


def extract_hashes(event: dict) -> set:
    strings: list = []
    for k in REF_KEYS:
        if k in event:
            collect_strings(event[k], strings)
    toks = set()
    for s in strings:
        for m in HEX_TOKEN.findall(s):
            toks.add(m.lower()[:12])
    return toks


def class_binding(event: dict) -> set:
    b = set()
    cid = event.get("class_id")
    if isinstance(cid, str):
        b.add(cid)
    cids = event.get("class_ids")
    if isinstance(cids, list):
        for c in cids:
            if isinstance(c, str):
                b.add(c)
    return b


def in_universe(event: dict) -> bool:
    return bool(class_binding(event) & set(GFORM_CLASSES))


def norm_statement(event: dict) -> str:
    return re.sub(r"\s+", " ", str(event.get("statement", "")).strip().lower())


def parse_stream(path: Path) -> dict:
    claims, parse_errors, non_objects, dup_ids = [], 0, 0, 0
    seen = set()
    lines = 0
    with path.open() as f:
        for line in f:
            lines += 1
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                parse_errors += 1
                continue
            if not isinstance(d, dict):
                non_objects += 1
                continue
            if d.get("event_type") != "claim":
                continue
            eid = d.get("event_id")
            if isinstance(eid, str):
                if eid in seen:
                    dup_ids += 1
                    continue
                seen.add(eid)
            claims.append(d)
    return {
        "lines": lines, "parse_errors": parse_errors, "non_objects": non_objects,
        "duplicate_event_ids": dup_ids, "claims": claims,
    }


# ---------------------------------------------------------------- clustering

def build_records(claims: list) -> list:
    recs = []
    for d in claims:
        sig = tuple(sorted(extract_hashes(d)))
        recs.append({
            "event_id": d.get("event_id"),
            "actor": d.get("actor"),
            "task": d.get("task_id") or d.get("assignment_ref") or "",
            "classes": sorted(class_binding(d)),
            "gate": d.get("gate"),
            "sig": sig,
            "stmt": norm_statement(d),
            "raw": d.get("statement", ""),
            "event": d,
        })
    return recs


def cluster(recs: list) -> dict:
    groups: dict = {}
    for r in recs:
        groups.setdefault(r["sig"], []).append(r)
    return groups


def summarise(recs: list) -> dict:
    n = len(recs)
    groups = cluster(recs)
    sizes = sorted((len(v) for v in groups.values()), reverse=True)
    hist: dict = {}
    for s in sizes:
        hist[str(s)] = hist.get(str(s), 0) + 1
    stmts: dict = {}
    for r in recs:
        if r["stmt"]:
            stmts.setdefault(r["stmt"], []).append(r)
    dup_groups = {k: v for k, v in stmts.items() if len(v) > 1}
    per_class: dict = {}
    for c in GFORM_CLASSES:
        sub = [r for r in recs if c in r["classes"]]
        sg = cluster(sub)
        per_class[c] = {
            "claims": len(sub),
            "actors": len({r["actor"] for r in sub}),
            "signatures": len(sg),
            "largest_cluster": max((len(v) for v in sg.values()), default=0),
        }
    top = []
    for sig, members in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:15]:
        top.append({
            "size": len(members),
            "signature_size": len(sig),
            "signature_prefixes": list(sig[:6]),
            "actors": sorted({str(m["actor"]) for m in members}),
            "tasks": sorted({str(m["task"]) for m in members if m["task"]}),
            "classes": sorted({c for m in members for c in m["classes"]}),
            "sample_statement": next((m["raw"][:220] for m in members if m["raw"]), ""),
        })
    return {
        "claims": n,
        "actors": len({r["actor"] for r in recs}),
        "tasks": len({r["task"] for r in recs if r["task"]}),
        "signatures": len(groups),
        "redundancy_factor": round(n / len(groups), 4) if groups else None,
        "largest_cluster": sizes[0] if sizes else 0,
        "cluster_size_histogram": hist,
        "exact_statement_duplicate_groups": len(dup_groups),
        "exact_statement_duplicate_claims": sum(len(v) for v in dup_groups.values()),
        "max_exact_statement_group": max((len(v) for v in dup_groups.values()), default=0),
        "per_class": per_class,
        "top_clusters": top,
    }


def subset(recs: list, pred) -> list:
    return [r for r in recs if pred(r)]


# ---------------------------------------------------------------- controls

def run_controls(recs: list) -> list:
    ctrls = []

    def mk(eid, refs, classes, stmt="s"):
        return {"event_type": "claim", "event_id": eid, "actor": "fixture",
                "class_id": classes[0], "class_ids": list(classes),
                "statement": stmt, "artifact_refs": list(refs), "evidence_refs": []}

    a = mk("c1a", ["x.json#aaaaaaaaaaaa"], ["AF-WCC-VAC-GEN"])
    b = mk("c1b", ["y.json#aaaaaaaaaaaa"], ["AF-WCC-VAC-GEN"])
    c = mk("c1c", ["z.json#bbbbbbbbbbbb"], ["AF-WCC-VAC-GEN"])
    g = cluster(build_records([a, b, c]))
    ctrls.append({"id": "C1-shared-hash-clusters",
                  "pass": len(g) == 2 and max(len(v) for v in g.values()) == 2,
                  "detail": f"clusters={len(g)} sizes={sorted(len(v) for v in g.values())}"})

    up = mk("c2a", ["x#ABCDEF123456"], ["AF-WCC-VAC-GEN"])
    lo = mk("c2b", ["x#sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"],
            ["AF-WCC-VAC-GEN"])
    g2 = cluster(build_records([up, lo]))
    ctrls.append({"id": "C2-case-and-length-normalisation",
                  "pass": len(g2) == 1 and list(g2)[0] == ("abcdef123456",),
                  "detail": f"signature={list(g2)[0] if g2 else None}"})

    e1 = mk("c3a", [], ["AF-WCC-VAC-GEN"])
    e2 = mk("c3b", [], ["AF-SCC-C0-VAC-GEN"])
    g3 = cluster(build_records([e1, e2]))
    ctrls.append({"id": "C3-empty-refs-share-empty-signature",
                  "pass": len(g3) == 1 and list(g3)[0] == (),
                  "detail": f"clusters={len(g3)}"})

    m1 = mk("c4a", ["p.json#1234567890ab:14-16"], ["AF-WCC-VAC-GEN"])
    m2 = mk("c4b", ["p.json:14-16#1234567890ab"], ["AF-WCC-VAC-GEN"])
    g4 = cluster(build_records([m1, m2]))
    ctrls.append({"id": "C4-path-line-hash-forms",
                  "pass": len(g4) == 1 and list(g4)[0] == ("1234567890ab",),
                  "detail": f"signature={list(g4)[0] if g4 else None}"})

    s_only = mk("c5a", ["q#cccccccccccc"], ["AF-WCC-SCALAR-SPH"])
    mixed = mk("c5b", ["q#cccccccccccc"], ["AF-WCC-SCALAR-SPH"])
    mixed["class_id"] = "AF-WCC-VAC-GEN"
    uni = [r for r in build_records([s_only, mixed]) if in_universe(r["event"])]
    ctrls.append({"id": "C5-universe-union-rule",
                  "pass": len(uni) == 1 and uni[0]["event_id"] == "c5b",
                  "detail": f"in_universe={[r['event_id'] for r in uni]}"})

    summ1 = summarise(recs)
    summ2 = summarise(recs)
    ctrls.append({"id": "C6-identity-and-idempotence",
                  "pass": summ1 == summ2 and sum(
                      int(k) * v for k, v in summ1["cluster_size_histogram"].items()) == summ1["claims"],
                  "detail": f"claims={summ1['claims']} signatures={summ1['signatures']}"})

    recomputed = all(
        tuple(sorted(extract_hashes(r["event"]))) == r["sig"] for r in recs)
    ctrls.append({"id": "C7-signature-recompute",
                  "pass": recomputed,
                  "detail": "every record signature equals a fresh extraction from its event"})
    return ctrls


# ---------------------------------------------------------------- modes

def preregister() -> int:
    if not SRC.is_file():
        log(f"VOID: source missing {SRC}")
        return 2
    before = sha256_file(SRC)
    size_before = SRC.stat().st_size
    snap_dir = OUT / "snapshot"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap = snap_dir / f"events.{before[:12]}.jsonl"
    if not snap.exists() or sha256_file(snap) != before:
        shutil.copyfile(SRC, snap)
    snap_hash = sha256_file(snap)
    after = sha256_file(SRC)
    if before != after or snap_hash != before:
        log(f"VOID: source changed across copy {before[:12]} -> {after[:12]}")
        return 2
    parsed = parse_stream(snap)
    frame = {
        "schema": "worker-070/preregistration/v1",
        "task_id": TASK_ID,
        "actor": "worker-070",
        "created_at": now(),
        "instrument_revision": REVISION,
        "revision_note": REVISION_NOTE,
        "object_under_test": "accepted event stream snapshot (research_map/events.jsonl)",
        "snapshot": {
            "source_path": "research_map/events.jsonl",
            "source_sha256_before_copy": before,
            "source_sha256_after_copy": after,
            "snapshot_path": str(snap.relative_to(ROOT)),
            "snapshot_sha256": snap_hash,
            "bytes": snap.stat().st_size,
            "lines": parsed["lines"],
            "claim_events": len(parsed["claims"]),
        },
        "universe": {
            "rule": "event_type == 'claim' AND (class_id or class_ids) intersects the three G-FORM classes",
            "classes": GFORM_CLASSES,
            "dedup": "first occurrence per event_id in file order",
            "excluded": ["claim events bound only to AF-WCC-SCALAR-SPH"],
        },
        "extraction_rules": {
            "ref_keys": sorted(REF_KEYS),
            "hash_regex": HEX_TOKEN.pattern,
            "normalisation": "lower-case, first 12 hex chars, distinct",
            "signature": "sorted tuple of distinct normalised hash tokens; empty tuple if none",
        },
        "metrics": [
            "claims, actors, tasks, signatures, redundancy_factor = claims/signatures",
            "cluster-size histogram over exact signatures",
            "exact-statement duplicate groups (whitespace/case-normalised)",
            "per-class split for each of the three classes",
            "top-15 largest clusters with actors/tasks",
            "secondary subsets: gate == G-FORM; and claims citing FROZEN rev29 " + REV29_FROZEN_HASH[:12],
        ],
        "controls": [
            "C1 shared hash -> one cluster", "C2 case/length normalisation",
            "C3 empty refs share empty signature", "C4 path#line#hash forms",
            "C5 universe union rule", "C6 identity + idempotence", "C7 signature recompute",
        ],
        "falsifier": FALSIFIER,
        "void_conditions": [
            "source sha256 changes across the preregistration copy",
            "snapshot sha256 != frame.snapshot.snapshot_sha256 at run time",
        ],
        "authority_note": "worker evidence; no gate verdict, no node status, no canonical write, no ingest",
        "non_claims": NON_CLAIMS,
    }
    FRAME.write_text(json.dumps(frame, indent=1, sort_keys=True) + "\n")
    runner_hash = sha256_file(Path(__file__).resolve())
    seal = {
        "frame_sha256": sha256_file(FRAME),
        "runner_sha256": runner_hash,
        "runner_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "sealed_at": now(),
        "task_id": TASK_ID,
    }
    FRAME_SEAL.write_text(json.dumps(seal, indent=1, sort_keys=True) + "\n")
    log(f"PREREGISTERED snapshot={snap_hash[:12]} lines={parsed['lines']} claims={len(parsed['claims'])}")
    return 0


def run() -> int:
    if not FRAME.is_file() or not FRAME_SEAL.is_file():
        log("VOID: frame or seal missing; run --preregister first")
        return 2
    frame = json.loads(FRAME.read_text())
    seal = json.loads(FRAME_SEAL.read_text())
    if sha256_file(FRAME) != seal["frame_sha256"]:
        log("VOID: frame bytes changed after sealing")
        return 2
    snap = ROOT / frame["snapshot"]["snapshot_path"]
    if not snap.is_file() or sha256_file(snap) != frame["snapshot"]["snapshot_sha256"]:
        log("VOID: snapshot hash mismatch")
        return 2
    parsed = parse_stream(snap)
    recs = build_records([c for c in parsed["claims"] if in_universe(c)])
    summ = summarise(recs)
    controls = run_controls(recs)
    controls_ok = all(c["pass"] for c in controls)

    rev29 = "815e08079aef"
    secondary = {
        "gate_G_FORM": summarise(subset(recs, lambda r: r["gate"] == GATE)),
        "cites_FROZEN_rev29": summarise(subset(recs, lambda r: rev29 in r["sig"])),
    }
    report = {
        "schema": "worker-070/claim-redundancy-report/v1",
        "task_id": TASK_ID,
        "actor": "worker-070",
        "generated_at": now(),
        "instrument_revision": REVISION,
        "revision_note": REVISION_NOTE,
        "gate": GATE,
        "node_id": GROUPS,
        "class_ids": GFORM_CLASSES,
        "snapshot_sha256": frame["snapshot"]["snapshot_sha256"],
        "snapshot_path": frame["snapshot"]["snapshot_path"],
        "snapshot_lines": parsed["lines"],
        "claim_events_total": len(parsed["claims"]),
        "claim_events_in_universe": len(recs),
        "parse_errors": parsed["parse_errors"],
        "non_object_lines": parsed["non_objects"],
        "duplicate_event_ids_skipped": parsed["duplicate_event_ids"],
        "universe": summ,
        "secondary_subsets": secondary,
        "controls": controls,
        "controls_all_pass": controls_ok,
        "falsifier": FALSIFIER,
        "non_claims": NON_CLAIMS,
        "authority_note": "worker evidence; not a gate verdict and not a node transition",
    }
    REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    log(f"RUN snapshot={frame['snapshot']['snapshot_sha256'][:12]} "
        f"claims={summ['claims']} signatures={summ['signatures']} "
        f"redundancy={summ['redundancy_factor']} controls_ok={controls_ok}")
    for c in controls:
        log(f"  {c['id']}: {'PASS' if c['pass'] else 'FAIL'} ({c['detail']})")
    if not controls_ok:
        return 3
    if sum(int(k) * v for k, v in summ["cluster_size_histogram"].items()) != summ["claims"]:
        log("IDENTITY FAILURE: histogram does not sum to claims")
        return 3
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preregister", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.preregister:
        RUNLOG.write_text("")
        return preregister()
    if a.run:
        return run()
    ap.error("choose --preregister or --run")
    return 2


if __name__ == "__main__":
    sys.exit(main())
