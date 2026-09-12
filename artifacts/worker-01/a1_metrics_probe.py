#!/usr/bin/env python3
"""A1 breadth probe: duplication, class-binding leakage, and comms hard-failure metrics.

Scope (worker-01 proposal, NOT a completion claim):
  node A1 (independent review queue), metrics owned by the audit group:
  duplication, hard failures, class binding. This tool is an *instrument*: it produces a
  deterministic snapshot that lead-audit may accept, revise or reject. It does not modify
  research_map.json, research_map/events.jsonl, or any lead-owned path.

Findings it reports
  1. malformed upward events: outbox JSON objects that fail research_map/schemas.validate_event
     (these are silently dropped by research_map/comms.py ingest; a comms hard-failure rate)
  2. artifact-path collisions: >1 actor claiming the same output path
  3. duplicate proposals: >1 actor proposing the same (node_id, artifact path)
  4. class-binding leakage: text merging C0/C2, or a class_id outside the four frozen classes
     (applied to the map and to outbox events)
  5. ingest rejects: counts by reason, from comms/rejected.jsonl

Usage
  python3 artifacts/worker-01/a1_metrics_probe.py                 # human summary
  python3 artifacts/worker-01/a1_metrics_probe.py --json out.json # write machine report
  python3 artifacts/worker-01/a1_metrics_probe.py --self-test     # fixture-based control
Exit code 0 always; use --fail-on-hard for CI (nonzero if hard findings).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "research_map"
if str(SCHEMA_DIR) not in sys.path:
    sys.path.insert(0, str(SCHEMA_DIR))

try:
    from schemas import validate_event, SchemaError, EVENT_TYPES, STATUSES
except Exception as exc:  # pragma: no cover - surfaced as a hard finding instead
    validate_event = None
    SchemaError = Exception
    EVENT_TYPES, STATUSES = set(), set()
    _IMPORT_ERROR = str(exc)
else:
    _IMPORT_ERROR = None

FROZEN_CLASSES = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
# "C0 or C2", "C0/C2", "C0 and C2" are forbidden merges (ASTRA_HANDOFF.md hard decision 1).
MERGED_REGULARITY_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)


def _normalize_regularity(text: str) -> str:
    return re.sub(r"[\^_{}\s]", "", text)


def merged_regularity_match(text: str) -> bool:
    return bool(MERGED_REGULARITY_RE.search(text)) or bool(MERGED_REGULARITY_RE.search(_normalize_regularity(text)))
# A full class id has at least three hyphen segments after the AF- prefix; family-only
# tokens such as "AF-SCC" and node labels such as "AF-SCC C2/C0 split" are not class ids.
CLASS_TOKEN_RE = re.compile(r"\bAF-(?:WCC|SCC)(?:-[A-Z0-9]+){2,}\b")
BINDING_KEYS = ("class_id", "class_ids", "conclusion_type", "expected_classification", "expected_class")


def parse_docs(text: str):
    """Best-effort JSON-object extraction, mirroring research_map/comms.py ingest."""
    text = text.strip()
    if not text:
        return
    try:
        doc = json.loads(text)
    except ValueError:
        pass
    else:
        if isinstance(doc, dict):
            yield doc
            return
        if isinstance(doc, list):
            yield from (d for d in doc if isinstance(d, dict))
            return
    for block in re.findall(r"```(?:json)?\s*(.*?)```", text, re.S):
        try:
            doc = json.loads(block.strip())
        except ValueError:
            continue
        if isinstance(doc, dict):
            yield doc
        elif isinstance(doc, list):
            yield from (d for d in doc if isinstance(d, dict))
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if line.startswith("{") and line.endswith("}"):
            try:
                doc = json.loads(line)
            except ValueError:
                continue
            if isinstance(doc, dict):
                yield doc


def collect_outbox(root: Path):
    docs = []
    outbox = root / "comms" / "outbox"
    if not outbox.exists():
        return docs
    for path in sorted(p for p in outbox.rglob("*") if p.is_file() and not p.name.startswith("._")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for doc in parse_docs(text):
            docs.append((path.relative_to(root).as_posix(), doc))
    return docs


def collect_rejects(root: Path):
    path = root / "comms" / "rejected.jsonl"
    if not path.exists():
        return []
    return list(parse_docs(path.read_text(errors="replace")))


def analyse(docs, map_obj, rejects, schema_ok=True):
    """Pure detector. docs: [(source, event_dict)]; rejects: [reject_dict]."""
    hard, soft = [], []

    # 1. malformed upward events (would be / were dropped by ingest)
    malformed = []
    for source, doc in docs:
        if validate_event is None:
            malformed.append({"source": source, "event_id": doc.get("event_id"),
                              "reason": f"schemas import failed: {_IMPORT_ERROR}"})
            continue
        try:
            validate_event(dict(doc))
        except SchemaError as exc:
            malformed.append({"source": source, "event_id": doc.get("event_id"),
                              "event_type": doc.get("event_type"), "reason": str(exc)})
    if malformed:
        hard.append(f"{len(malformed)} malformed upward event(s) would be dropped by ingest")

    # 2/3. artifact-path claims, collisions, duplicate proposals
    claims = defaultdict(list)
    for source, doc in docs:
        actor = doc.get("actor") or Path(source).stem
        node = doc.get("node_id")
        paths = []
        if doc.get("event_type") == "artifact" and isinstance(doc.get("path"), str):
            paths.append(doc["path"])
        for key in ("artifact_path", "artifact"):
            if isinstance(doc.get(key), str):
                paths.append(doc[key])
        for path in paths:
            claims[path].append({"actor": actor, "node_id": node, "source": source,
                                 "event_type": doc.get("event_type")})
    collisions, duplicates = [], []
    for path, entries in sorted(claims.items()):
        actors = sorted({e["actor"] for e in entries})
        if len(actors) > 1:
            collisions.append({"path": path, "actors": actors, "claims": entries})
        by_node = defaultdict(set)
        for e in entries:
            by_node[e["node_id"]].add(e["actor"])
        for node, node_actors in by_node.items():
            if len(node_actors) > 1:
                duplicates.append({"node_id": node, "path": path, "actors": sorted(node_actors)})
    if collisions:
        hard.append(f"{len(collisions)} artifact path(s) claimed by more than one actor")
    if duplicates:
        soft.append(f"{len(duplicates)} duplicate proposal(s) by (node_id, artifact)")

    # 4. class-binding leakage: HARD only where a structured class-binding field merges or
    #    names an unknown class. Prose that *discusses* a C0/C2 split is a soft mention: the
    #    taxonomy's own prohibition text is legitimate and must not be flagged as a binding.
    leakage, soft_mentions = [], []

    def scan_binding(label, obj):
        for key in BINDING_KEYS:
            values = obj.get(key)
            if values is None:
                continue
            vals = values if isinstance(values, list) else [values]
            for value in vals:
                if not isinstance(value, str):
                    continue
                if merged_regularity_match(value):
                    leakage.append({"where": label, "kind": "merged_regularity", "field": key, "value": value})
                for cid in {c for c in CLASS_TOKEN_RE.findall(value) if c not in FROZEN_CLASSES}:
                    leakage.append({"where": label, "kind": "unknown_class_id", "field": key, "class_id": cid})
        text = json.dumps(obj, sort_keys=True)
        if merged_regularity_match(text):
            soft_mentions.append({"where": label, "kind": "merged_regularity_mention"})

    for group in map_obj.get("groups", []):
        for node in group.get("nodes", []):
            scan_binding(f"map:{node.get('id')}", node)
    for source, doc in docs:
        scan_binding(f"event:{doc.get('event_id') or source}", doc)
    if leakage:
        hard.append(f"{len(leakage)} class-binding leakage finding(s) (structured fields only)")
    if soft_mentions:
        soft.append(f"{len(soft_mentions)} prose mention(s) of a merged-regularity pattern (needs human read, not a binding)")

    # 5. rejected ingests
    reject_counts = defaultdict(int)
    for r in rejects:
        reject_counts[str(r.get("reason", "unknown"))[:160]] += 1

    summary = {
        "outbox_events": len(docs),
        "outbox_files": len({s for s, _ in docs}),
        "malformed_events": len(malformed),
        "artifact_paths_claimed": len(claims),
        "artifact_path_collisions": len(collisions),
        "duplicate_proposals": len(duplicates),
        "class_leakage_findings": len(leakage),
        "merged_regularity_mentions_soft": len(soft_mentions),
        "ingest_rejects_total": len(rejects),
        "frozen_classes": sorted(FROZEN_CLASSES),
        "schemas_import_ok": validate_event is not None,
    }
    return {
        "summary": summary,
        "hard_findings": hard,
        "soft_findings": soft,
        "malformed_events": malformed,
        "artifact_path_collisions": collisions,
        "duplicate_proposals": duplicates,
        "class_leakage": leakage,
        "soft_mentions": soft_mentions,
        "ingest_reject_reasons": dict(reject_counts),
    }


def self_test():
    """Planted-defect control: every detector must fire on a fixture that contains it."""
    fixture_docs = [
        ("fixture/a.jsonl", {"event_id": "f1", "event_type": "status", "created_at": "t",
                             "actor": "actor-a", "node_id": "A1", "status": "active", "hours": 0.1,
                             "summary": "x", "evidence_refs": ["e"], "next_falsifier": "f"}),
        ("fixture/a.jsonl", {"event_id": "f2", "event_type": "artifact", "created_at": "t",
                             "actor": "actor-a", "node_id": "A1", "artifact_type": "t",
                             "path": "schemas/shared.yaml", "sha256": "0" * 64,
                             "validation_status": "unverified"}),
        ("fixture/b.jsonl", {"event_id": "f3", "event_type": "artifact", "created_at": "t",
                             "actor": "actor-b", "node_id": "A1", "artifact_type": "t",
                             "path": "schemas/shared.yaml", "sha256": "1" * 64,
                             "validation_status": "unverified"}),
        ("fixture/b.jsonl", {"event_id": "f4", "event_type": "status", "created_at": "t",
                             "actor": "actor-b", "node_id": "F2",
                             "summary": "merged class C0/C2 regularity", "next_falsifier": "f"}),
        ("fixture/b.jsonl", {"event_id": "f5", "event_type": "claim", "created_at": "t",
                             "actor": "actor-b", "class_id": "AF-WCC-C0-C2-VAC-GEN",
                             "statement": "planted unknown class id", "conclusion_type": "open_problem",
                             "assumptions": [], "falsifier": "f", "evidence_refs": ["e"]}),
    ]
    map_obj = {"groups": [{"id": "formulation", "nodes": [
        {"id": "F1", "class_id": "AF-WCC-VAC-GEN", "label": "ok"},
        {"id": "F2", "class_id": "AF-SCC-C0-C2-MERGED", "label": "C0 or C2"},
    ]}]}
    rejects = [{"reason": "status: missing hours, summary"}]
    res = analyse(fixture_docs, map_obj, rejects)
    checks = {
        "malformed_events>=1": res["summary"]["malformed_events"] >= 1,
        "artifact_path_collisions==1": res["summary"]["artifact_path_collisions"] == 1,
        "duplicate_proposals==1": res["summary"]["duplicate_proposals"] == 1,
        "class_leakage>=2": res["summary"]["class_leakage_findings"] >= 2,
        "rejects==1": res["summary"]["ingest_rejects_total"] == 1,
        "hard_findings>=3": len(res["hard_findings"]) >= 3,
    }
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    return all(checks.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", default=None, help="write machine-readable report here")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--fail-on-hard", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        ok = self_test()
        print("self-test:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    root = Path(args.root).resolve()
    map_path = root / "research_map" / "research_map.json"
    map_obj = json.loads(map_path.read_text()) if map_path.exists() else {}
    docs = collect_outbox(root)
    rejects = collect_rejects(root)
    res = analyse(docs, map_obj, rejects)
    res["root"] = str(root)
    res["map_path"] = str(map_path.relative_to(root)) if map_path.exists() else None

    print(json.dumps(res["summary"], indent=2))
    for f in res["hard_findings"]:
        print(f"  HARD  {f}")
    for f in res["soft_findings"]:
        print(f"  soft  {f}")
    if res["malformed_events"]:
        print("  malformed examples:")
        for m in res["malformed_events"][:5]:
            print(f"    - {m['source']} {m.get('event_id')}: {m['reason']}")
    if res["artifact_path_collisions"]:
        print("  collisions:")
        for c in res["artifact_path_collisions"]:
            print(f"    - {c['path']}: {', '.join(c['actors'])}")
    if res["class_leakage"]:
        print("  class leakage:")
        for c in res["class_leakage"][:8]:
            print(f"    - {c['where']} [{c['kind']}] {c.get('class_id')}")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
        print(f"wrote {out}")
    if args.fail_on_hard and res["hard_findings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
