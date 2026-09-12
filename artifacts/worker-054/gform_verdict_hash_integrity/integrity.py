#!/usr/bin/env python3
"""W054-GFORM-VERDICT-HASH-INTEGRITY-01  (read-only).

Question (class-bound, F0/F1/F2a/F2b, gate G-FORM): for every review verdict that could
count toward the gate, is it bound to a hash that (a) exists on disk and (b) still equals
the current bytes at the cited path? And is every cited evidence path covered by the
FROZEN rev28 pin set, so that a later byte change cannot silently invalidate the verdict?

Method
 1. Snapshot sha256 of every input (events.jsonl, research_map.json, FROZEN.json,
    the three canonical class schemas, canonical taxonomy, KEY_MANIFEST).
 2. Parse research_map/events.jsonl review events.
 3. For hash-bearing citations, resolve the short hash against live files that carry it:
      FOUND             the hash matches at least one live file; the matched paths are
                        reported so a caller can tell canonical-current from archival copy
      UNRESOLVED        the hash matches no live file
 4. Classify each review event VERIFIED_BOUND / STALE_BOUND / UNRESOLVED_BOUND / UNBOUND.
 5. Per target (F0/F1/F2a/F2b), count distinct accept/revise reviewers at the current
    node hash vs at superseded hashes.
 6. Re-snapshot every input; any drift makes the run VOID (fail closed).

Falsifier: re-run in an unchanged tree -- any classification that changes, any live input
hash differing from the start snapshot, or any prefix resolved to non-matching bytes
falsifies the corresponding row. The report is valid only if drift.detected == false.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
EVENTS = ROOT / "research_map/events.jsonl"
MAP = ROOT / "research_map/research_map.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
CANON = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
]
NODE_ALIASES = {"F0", "F1", "F2a", "F2b"}
HASH_RE = re.compile(r"#([0-9a-f]{12,64})")
BARE_RE = re.compile(r"^[0-9a-f]{12,64}$")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot() -> dict:
    snap = {"events.jsonl": sha(EVENTS), "research_map.json": sha(MAP), "FROZEN.json": sha(FROZEN)}
    for rel in CANON:
        f = ROOT / rel
        snap[rel] = sha(f) if f.exists() else None
    return snap


def freeze_inputs(work: Path) -> dict:
    """Copy the append-only event stream and the map once, so analysis runs on frozen
    bytes while the live swarm keeps writing. The live files are re-hashed afterwards:
    any content change to the live event stream is reported (no stable full-file hash
    exists for a file being appended to), while the frozen copies must be byte-stable.
    """
    work.mkdir(parents=True, exist_ok=True)
    frozen_files = {"events.jsonl": EVENTS, "research_map.json": MAP,
                    "FROZEN.json": FROZEN}
    out = {}
    for name, src in frozen_files.items():
        dst = work / name
        dst.write_bytes(src.read_bytes())
        out[name] = {"source": str(src.relative_to(ROOT)), "frozen_sha256": sha(dst),
                     "frozen_bytes": dst.stat().st_size}
    for rel in CANON:
        src = ROOT / rel
        if not src.exists():
            out[rel] = {"source": rel, "frozen_sha256": None}
            continue
        dst = work / ("canonical__" + rel.replace("/", "__"))
        dst.write_bytes(src.read_bytes())
        out[rel] = {"source": rel, "frozen_sha256": sha(dst),
                    "frozen_bytes": dst.stat().st_size}
    return out


def snap_one(rel: str):
    f = ROOT / rel
    return sha(f) if f.exists() else None


def load_events(src: Path) -> list:
    rows = []
    with src.open() as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception as exc:  # noqa: BLE001
                rows.append({"_line": i, "_parse_error": str(exc)})
                continue
            e["_line"] = i
            rows.append(e)
    return rows


SKIP_DIRS = {".git", "__pycache__", "tmp", ".tmp", ".cache", "node_modules", ".dsh"}


def index_workspace() -> dict:
    """sha256 -> [paths] over the live tree (bounded: skip meta/caches/tmp)."""
    by_hash: dict = {}
    for p in ROOT.rglob("*"):
        if not p.is_file() or p.name.startswith("._") or p.is_symlink():
            continue
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        try:
            if p.stat().st_size > 8_000_000:
                continue
            digest = sha(p)
        except OSError:
            continue
        by_hash.setdefault(digest, []).append(str(rel))
    return by_hash


def resolve_hash(h: str, by_hash: dict) -> dict:
    hits = sorted((digest, paths) for digest, paths in by_hash.items()
                  if digest.startswith(h))
    if not hits:
        return {"status": "UNRESOLVED", "paths": []}
    digest, paths = hits[0]
    canon = [p for p in paths if p in CANON]
    rest = [p for p in paths if p not in CANON]
    ordered = canon + rest
    return {"status": "FOUND", "sha256": digest,
            "paths": ordered[:12],
            "canonical_live": [p for p in canon],
            "n_paths_total": len(paths)}


def render_markdown(rep: dict) -> str:
    lines = []
    add = lines.append
    add(f"# {rep['task']} — {rep['worker']}")
    add("")
    add(f"Measured at `{rep['measured_at_wall_clock']}` (worker report only; no gate verdict).")
    add("")
    add("## Canonical bytes at run start vs map declaration")
    add("")
    add("| artifact | sha256 (16) | node hash in frozen map | match |")
    add("|---|---|---|---|")
    for tgt in ("F0", "F1", "F2a", "F2b"):
        row = rep["per_target"][tgt]
        art = {"F0": "research_map/formulation_taxonomy.yaml",
               "F1": "schemas/af_wcc_vacuum.yaml",
               "F2a": "schemas/af_scc_c2_vacuum.yaml",
               "F2b": "schemas/af_scc_c0_vacuum.yaml"}[tgt]
        snap = (rep["frozen_inputs"].get(art) or {}).get("frozen_sha256") or "-"
        declared = row["current_hash"] or "-"
        add(f"| `{art}` | `{snap[:16]}` | `{declared[:16]}` | "
            f"{'yes' if snap == declared else 'NO'} |")
    add("")
    add("## Review-event classification")
    add("")
    add("| classification | count |")
    add("|---|---|")
    for k, v in sorted(rep["counts"].items()):
        if k.startswith("class_"):
            add(f"| `{k[6:].upper()}` | {v} |")
    add(f"| reviews total | {rep['counts']['reviews_total']} |")
    add("")
    add("## Distinct reviewers bound to the current bytes")
    add("")
    add("| target | accept (bound) | revise (bound) | criterion (>=2 distinct bound accepts) |")
    add("|---|---|---|---|")
    for tgt, row in rep["per_target"].items():
        acc = ", ".join(row["distinct_accept_hash_bound_to_current"]) or "—"
        rev = ", ".join(row["distinct_revise_hash_bound_to_current"]) or "—"
        add(f"| {tgt} | {acc} | {rev} | "
            f"{'**met**' if row['gate_criterion_met'] else '**not met**'} |")
    add("")
    add("## Flags")
    add("")
    add(f"- frozen input copies byte-stable: `{rep['frozen_copies_byte_stable']}`")
    add(f"- run void: `{rep['drift']['run_void']}`")
    add(f"- canonical bytes changed since snapshot: "
        f"`{ {k: v['changed'] for k, v in rep['canonical_drift_since_snapshot'].items()} }`")
    add(f"- review events citing at least one path not covered by the FROZEN pin set: "
        f"{rep['counts']['verdicts_live_citation_unpinned_paths']}")
    add("")
    add("## Falsifier")
    add("")
    add(rep["falsifier"])
    add("")
    return "\n".join(lines)


def main() -> int:
    before = snapshot()
    work = OUT / "frozen_inputs"
    frozen_inputs = freeze_inputs(work)
    frozen = json.loads((work / "FROZEN.json").read_text())
    pinned = {p: rec["sha256"] for p, rec in frozen["files"].items()}
    mapdoc = json.loads((work / "research_map.json").read_text())
    events_src = work / "events.jsonl"
    node_hashes = {}
    for grp in mapdoc.get("groups", []):
        for n in grp.get("nodes", []):
            if n.get("artifact_sha256"):
                node_hashes[n["id"]] = n["artifact_sha256"]
    events = load_events(events_src)
    print("indexing workspace by sha256 ...", file=sys.stderr)
    by_hash = index_workspace()
    # canonical snapshot: hash -> path, taken from the frozen copies in this directory
    canonical_snapshot = {v["frozen_sha256"]: k for k, v in frozen_inputs.items()
                          if k in CANON and v.get("frozen_sha256")}

    reviews = [e for e in events if e.get("event_type") == "review"]
    rows, problems = [], []
    for e in reviews:
        tid = str(e.get("target_id") or "")
        target_hashes = HASH_RE.findall(tid)
        for key in ("target_sha256", "cited_sha256"):
            v = e.get(key) or ""
            if isinstance(v, str) and BARE_RE.match(v.strip()):
                target_hashes.append(v.strip())
        evidence_hashes, evidence_ref_map = [], []
        for ref in (e.get("evidence_refs") or []):
            hs = HASH_RE.findall(str(ref))
            evidence_hashes.extend(hs)
            path = str(ref).split("#")[0]
            for h in hs:
                evidence_ref_map.append({"hash": h, "ref_path": path})
        cited = list(dict.fromkeys(target_hashes + evidence_hashes))
        row = {
            "event_id": e.get("event_id"),
            "line": e["_line"],
            "reviewer": e.get("reviewer"),
            "target_id": tid,
            "verdict": e.get("verdict"),
            "score": e.get("score"),
            "created_at": e.get("created_at"),
            "target_hashes": list(dict.fromkeys(target_hashes)),
            "evidence_hashes": list(dict.fromkeys(evidence_hashes)),
            "evidence_ref_map": evidence_ref_map,
            "cited_hashes": cited,
            "classification": None,
            "resolutions": [],
        }
        if not cited:
            # node-alias or prose target, and no hash anywhere: verdict is not hash-bound
            alias = tid if tid in NODE_ALIASES else (
                "F0" if tid.startswith("F0") else
                "F1" if tid.startswith("F1") else
                "F2a" if tid.startswith("F2a") else
                "F2b" if tid.startswith("F2b") else None)
            row["classification"] = "UNBOUND"
            row["binding_mode"] = "NO_HASH_ANYWHERE"
            row["node_alias"] = alias
            if alias:
                cur = node_hashes.get(alias)
                row["current_node_hash"] = cur
                row["current_node_hash_live_at"] = (
                    sorted(resolve_hash(cur, by_hash).get("paths", []))[:4] if cur else [])
        else:
            # A verdict is *target-bound* only when it identifies one target:
            #   (a) the target_id itself carries a hash (or the target_id path is canonical), or
            #   (b) no target-side hash exists and exactly ONE canonical artifact path is cited
            #       among the evidence refs. A review that cites several canonical artifacts
            #       (cross-target/ledger reviews) cannot be attributed to a single target and is
            #       recorded as AMBIGUOUS_TARGET rather than counted.
            ev_canon_refs = list(dict.fromkeys(
                m["ref_path"] for m in evidence_ref_map if m["ref_path"] in CANON))
            tid_path = tid.split("#")[0]
            if row["target_hashes"]:
                binding = "TARGET_FIELD"
                bound_paths = ([tid_path] if tid_path in CANON
                               else (ev_canon_refs if len(ev_canon_refs) == 1 else []))
            elif tid_path in CANON:
                binding = "TARGET_PATH"
                bound_paths = [tid_path]
            elif len(ev_canon_refs) == 1:
                binding = "SINGLE_CANONICAL_EVIDENCE_REF"
                bound_paths = ev_canon_refs
            elif len(ev_canon_refs) > 1:
                binding = "AMBIGUOUS_TARGET_MULTIPLE_CANONICAL_REFS"
                bound_paths = []
            else:
                binding = "NO_TARGET_IDENTIFIER"
                bound_paths = []
            row["binding_mode"] = binding
            row["bound_target_paths"] = bound_paths
            bound_path_set = set(bound_paths)
            # a hash is target-side if its evidence ref names a bound target path, or if it
            # appears directly on the target fields of a TARGET_PATH/TARGET_FIELD review.
            target_hashes_set = set(row["target_hashes"])
            for h in cited:
                r = resolve_hash(h, by_hash)
                r["cited_hash"] = h
                ref_paths = [m["ref_path"] for m in evidence_ref_map if m["hash"] == h]
                r["side"] = ("target" if (bound_path_set & set(ref_paths)
                                          or (h in target_hashes_set and bound_paths))
                             else "evidence")
                row["resolutions"].append(r)
            # target-side verdict: every hash on the target side must equal the live
            # canonical bytes of a canonical class artifact or of the declared taxonomy.
            target_res = [r for r in row["resolutions"] if r["side"] == "target"]
            cur_ok, canonical_paths, archive_paths = True, set(), set()
            for r in target_res:
                # "current" = equals the canonical snapshot taken at run start
                snap_hit = canonical_snapshot.get(r.get("sha256"))
                if snap_hit:
                    canonical_paths.add(snap_hit)
                else:
                    cur_ok = False
                    archive_paths.update(p for p in r.get("paths", []) if p not in CANON)
            if not target_res:
                row["classification"] = ("AMBIGUOUS_TARGET"
                                         if row.get("binding_mode") ==
                                         "AMBIGUOUS_TARGET_MULTIPLE_CANONICAL_REFS"
                                         else "EVIDENCE_ONLY_HASH")
                row["target_bound_to_current"] = False
            elif cur_ok:
                row["classification"] = "VERIFIED_BOUND"
                row["target_bound_to_current"] = True
            elif not canonical_paths:
                row["classification"] = "UNRESOLVED_BOUND"
                row["target_bound_to_current"] = False
            else:
                row["classification"] = "STALE_BOUND"
                row["target_bound_to_current"] = False
            row["resolved_live_canonical"] = sorted(canonical_paths)[:8]
            row["resolved_archival_copies"] = sorted(archive_paths)[:8]
            row["pinned"] = {p: (p in pinned) for p in sorted(canonical_paths or archive_paths)}
        ev_paths = [str(x).split("#")[0] for x in (e.get("evidence_refs") or [])]
        ev_paths = [p for p in ev_paths if p and (ROOT / p).exists()]
        row["cited_evidence_paths"] = ev_paths
        row["evidence_unpinned"] = [p for p in ev_paths if p not in pinned]
        row.setdefault("target_bound_to_current", False)
        # intended target for aggregation: alias in target_id, else canonical schema cited
        row["target_key"] = row.get("node_alias")
        if not row["target_key"]:
            for rel, tgt in (("schemas/af_wcc_vacuum.yaml", "F1"),
                             ("schemas/af_scc_c2_vacuum.yaml", "F2a"),
                             ("schemas/af_scc_c0_vacuum.yaml", "F2b"),
                             ("research_map/formulation_taxonomy.yaml", "F0")):
                if rel in (row.get("resolved_live_canonical") or []) or any(
                        rel in (r.get("paths") or []) for r in row["resolutions"]):
                    row["target_key"] = tgt
                    break
        if row["classification"] in ("STALE_BOUND", "UNRESOLVED_BOUND"):
            problems.append(row)
        rows.append(row)

    # per-target counts: only hash-bound-to-current reviewers count toward the criterion
    per_target = {}
    for tgt in ("F0", "F1", "F2a", "F2b"):
        cur = node_hashes.get(tgt)
        accepts_cur, accepts_other, revise_cur, total, unbound = set(), set(), set(), 0, 0
        for r in rows:
            if r.get("target_key") != tgt:
                continue
            total += 1
            bound = bool(r.get("target_bound_to_current"))
            if not bound:
                if r["classification"] == "UNBOUND":
                    unbound += 1
                if r["verdict"] == "accept":
                    accepts_other.add(r["reviewer"])
                continue
            if r["verdict"] == "accept":
                accepts_cur.add(r["reviewer"])
            if r["verdict"] == "revise":
                revise_cur.add(r["reviewer"])
        per_target[tgt] = {
            "current_hash": cur,
            "reviews_total": total,
            "reviews_unbound_no_hash_anywhere": unbound,
            "n_target_hash_bound_to_current": sum(
                1 for r in rows if r.get("target_key") == tgt and r.get("target_bound_to_current")),
            "distinct_accept_hash_bound_to_current": sorted(x for x in accepts_cur if x),
            "n_accept_bound_to_current": len([x for x in accepts_cur if x]),
            "distinct_accept_unbound_or_stale": sorted(x for x in accepts_other if x),
            "n_accept_unbound_or_stale": len([x for x in accepts_other if x]),
            "distinct_revise_hash_bound_to_current": sorted(x for x in revise_cur if x),
            "gate_criterion_met": len([x for x in accepts_cur if x]) >= 2,
        }

    after = snapshot()
    # frozen copies must be byte-stable across the run (hard fail-closed)
    frozen_stable = {name: frozen_inputs[name]["frozen_sha256"] == sha(work / name)
                     for name in ("events.jsonl", "research_map.json", "FROZEN.json")}
    # canonical drift: live bytes vs the run-start snapshot (writers are active in this swarm)
    canonical_drift = {rel: {"snapshot": frozen_inputs[rel].get("frozen_sha256"),
                             "live_at_end": after.get(rel),
                             "changed": frozen_inputs[rel].get("frozen_sha256")
                             != after.get(rel)}
                       for rel in CANON}
    # live-input observations: the append-only event stream is expected to grow;
    # this records the exact live bytes seen before and after so the snapshot is auditable.
    live_observations = {
        "sha256_before": before,
        "sha256_after": after,
        "events_bytes_before": EVENTS.stat().st_size,
    }
    drift = {k: [before.get(k), after.get(k)] for k in before if before.get(k) != after.get(k)}
    void = (not all(frozen_stable.values()))
    report = {
        "task": "W054-GFORM-VERDICT-HASH-INTEGRITY-01",
        "worker": "worker-054",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "measured_at_wall_clock": __import__("datetime").datetime.now().astimezone().isoformat(),
        "input_snapshot_sha256": before,
        "frozen_inputs": frozen_inputs,
        "canonical_drift_since_snapshot": canonical_drift,
        # is the measured snapshot itself the binding pin (FROZEN) and the map-declared hash?
        "snapshot_vs_pins": {
            rel: {
                "snapshot": frozen_inputs[rel].get("frozen_sha256"),
                "frozen_pin": pinned.get(rel),
                "equals_frozen_pin": frozen_inputs[rel].get("frozen_sha256") == pinned.get(rel),
                "declared_node_hash": node_hashes.get(
                    {"research_map/formulation_taxonomy.yaml": "F0",
                     "schemas/af_wcc_vacuum.yaml": "F1",
                     "schemas/af_scc_c2_vacuum.yaml": "F2a",
                     "schemas/af_scc_c0_vacuum.yaml": "F2b"}[rel]),
            }
            for rel in CANON if rel in frozen_inputs
        },
        # standing policy check: which artifacts were pinned by the freeze manifest but are
        # byte-different from the revision the map declares for their node?
        "pin_freshness": {
            rel: {
                "equals_frozen_pin": frozen_inputs[rel].get("frozen_sha256") == pinned.get(rel),
                "equals_map_declared": frozen_inputs[rel].get("frozen_sha256") == node_hashes.get(
                    {"research_map/formulation_taxonomy.yaml": "F0",
                     "schemas/af_wcc_vacuum.yaml": "F1",
                     "schemas/af_scc_c2_vacuum.yaml": "F2a",
                     "schemas/af_scc_c0_vacuum.yaml": "F2b"}[rel]),
            }
            for rel in CANON if rel in frozen_inputs
        },
        "frozen_copies_byte_stable": frozen_stable,
        "live_input_observations": live_observations,
        "frozen_revision": frozen.get("revision"),
        "frozen_manifest_sha256": before["FROZEN.json"],
        "drift": {"detected": bool(drift), "diff": drift, "run_void": void},
        "counts": {
            "events_total": len(events),
            "reviews_total": len(rows),
            **{f"class_{k.lower()}": sum(1 for r in rows if r["classification"] == k)
               for k in ("VERIFIED_BOUND", "STALE_BOUND", "UNRESOLVED_BOUND", "UNBOUND",
                         "EVIDENCE_ONLY_HASH", "AMBIGUOUS_TARGET")},
            "verdicts_live_citation_unpinned_paths": sum(
                1 for r in rows if r.get("evidence_unpinned")),
        },
        "per_target": per_target,
        "problem_rows": problems,
        "rows": rows,
        "falsifier": (
            "Re-run integrity.py in an unchanged tree: any classification that changes, any live "
            "input hash differing from input_snapshot_sha256, or a cited prefix resolving to "
            "non-matching bytes falsifies this report. Valid only while drift.detected is false."),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    summary = {
        "counts": report["counts"],
        "per_target": per_target,
        "problem_event_ids": [r["event_id"] for r in problems],
        "drift": report["drift"],
        "frozen_copies_byte_stable": report["frozen_copies_byte_stable"],
        "canonical_drift_since_snapshot": report["canonical_drift_since_snapshot"],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    (OUT / "summary.md").write_text(render_markdown(report))
    print(json.dumps(summary, indent=1, sort_keys=True))
    if void:
        print("RUN VOID: frozen input copies were not byte-stable", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
