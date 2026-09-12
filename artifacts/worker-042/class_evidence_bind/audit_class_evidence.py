#!/usr/bin/env python3
"""W042-CLASS-EVID-BIND-01: do class-bound claims cite hash-resolvable evidence?

Bounded, stdlib-only, read-only audit of one snapshot of research_map/events.jsonl.

Question
--------
For the four frozen classes (ASTRA_HANDOFF.md hard decision 1), do the `claim`
events bound to those classes carry evidence_refs that still resolve to the bytes
they cite (protocol rule 4: `path#sha256-prefix`), and do the `artifact` events
bound to those classes declare a sha256 equal to the file on disk (rule 2)?

Method
------
1. Read research_map/events.jsonl once into bytes; record its sha256 and parse it.
   A truncated final line (concurrent append) is dropped and flagged.
2. For every claim event, collect frozen class ids from class_id + class_ids.
3. Classify each evidence_ref:
     hash_match    path#<hex>  -> file exists and sha256 starts with <hex>
     hash_stale    path#<hex>  -> file exists, prefix does not match
     hash_missing  path#<hex>  -> file absent
     line_ref      path#Lx[-Ly] or path:N -> file exists (no hash to check)
     unpinned      path exists but no hash prefix       (rule-4 deviation)
     dir_ref       path is a directory                  (unhashable by prefix)
     unresolvable  cannot be mapped to a repo path
4. For every artifact event, compare declared sha256 against the file on disk
   (file -> sha256; directory -> manifest digest, same construction as
   research_map/audit_evidence.py:artifact_digest).
5. Re-hash every referenced file at the end; files whose bytes changed during the
   scan are listed as snapshot instability.
6. Emit report.json + README.md and print a summary.

Determinism: one snapshot in, one report out. Re-running on unchanged inputs
reproduces the same classifications and counts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # .../ai4math-swarm
EVENTS = ROOT / "research_map" / "events.jsonl"
OUT_DIR = ROOT / "artifacts" / "worker-042" / "class_evidence_bind"
REPORT = OUT_DIR / "report.json"
README = OUT_DIR / "README.md"
CST = timezone(timedelta(hours=8))

# ASTRA_HANDOFF.md hard decision 1 (frozen four).
FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
CANONICAL = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
    "AF-WCC-SCALAR-SPH": "research_map/formulation_taxonomy.yaml",
}

HEX = re.compile(r"^([^#\s]+)#([0-9a-fA-F]{7,64})(?=$|\s|[(),;.])")
LINE = re.compile(r"^([^#\s]+)#L\d+(?:-L?\d+)?(?=$|\s|[(),;.])")
COLON = re.compile(r"^([A-Za-z0-9_./-]+):(\d+)(?=$|\s|[(),;.])")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(path: Path) -> dict:
    """File -> sha256; directory -> manifest digest (same as audit_evidence.py)."""
    if path.is_file():
        return {"kind": "file", "sha256": sha256_file(path), "bytes": path.stat().st_size}
    if path.is_dir():
        h = hashlib.sha256()
        files = sorted(p for p in path.rglob("*") if p.is_file() and not p.name.startswith("._"))
        for p in files:
            h.update(f"{p.relative_to(path)}\0{sha256_file(p)}\n".encode())
        return {"kind": "directory", "sha256": h.hexdigest(), "files": len(files),
                "bytes": sum(p.stat().st_size for p in files)}
    return {"kind": "absent", "sha256": None}


def load_snapshot(events_path: Path) -> tuple[dict, list, dict]:
    raw = events_path.read_bytes()
    snap = {"path": str(events_path.relative_to(ROOT)) if events_path.is_relative_to(ROOT)
            else str(events_path),
            "sha256": sha256_bytes(raw),
            "bytes": len(raw), "read_at": now()}
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    events, bad, truncated = [], 0, False
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            if i == len(lines) - 1:
                truncated = True
            else:
                bad += 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
    snap["lines"] = len(lines)
    snap["events_parsed"] = len(events)
    snap["malformed_lines"] = bad
    snap["truncated_tail_dropped"] = truncated
    return snap, events, {}


def classes_of(ev: dict) -> set:
    out = set()
    for key in ("class_id", "class_ids"):
        v = ev.get(key)
        if isinstance(v, str):
            out.update(x.strip() for x in re.split(r"[;,]", v) if x.strip())
        elif isinstance(v, list):
            out.update(str(x).strip() for x in v if str(x).strip())
    return out & set(FROZEN)


def resolve(path_str: str) -> Path:
    return (ROOT / path_str).resolve()


def rel_ok(path_str: str) -> bool:
    try:
        resolve(path_str).relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def classify_ref(ref: str, cache: dict) -> dict:
    """Classify one evidence_ref string. cache: relpath -> digest dict."""
    ref = ref.strip()
    m = HEX.match(ref)
    if m:
        path_str, prefix = m.group(1), m.group(2).lower()
        if not rel_ok(path_str):
            return {"ref": ref, "class": "unresolvable", "path": path_str, "detail": "outside repo"}
        p = resolve(path_str)
        if not p.exists():
            return {"ref": ref, "class": "hash_missing", "path": path_str, "declared_prefix": prefix}
        d = cache.get(path_str) or cache.setdefault(path_str, digest(p))
        if d["kind"] != "file":
            return {"ref": ref, "class": "dir_ref", "path": path_str, "declared_prefix": prefix}
        cur = d["sha256"]
        cls = "hash_match" if cur.startswith(prefix) else "hash_stale"
        return {"ref": ref, "class": cls, "path": path_str, "declared_prefix": prefix,
                "current_sha256": cur}
    m = LINE.match(ref)
    if m:
        path_str = m.group(1)
        if not rel_ok(path_str):
            return {"ref": ref, "class": "unresolvable", "path": path_str, "detail": "outside repo"}
        p = resolve(path_str)
        cls = "line_ref" if p.exists() else "hash_missing"
        return {"ref": ref, "class": cls, "path": path_str}
    m = COLON.match(ref)
    if m:
        path_str = m.group(1)
        if not rel_ok(path_str):
            return {"ref": ref, "class": "unresolvable", "path": path_str, "detail": "outside repo"}
        p = resolve(path_str)
        cls = "line_ref" if p.exists() else "hash_missing"
        return {"ref": ref, "class": cls, "path": path_str}
    # bare repo path?
    cand = ref.rstrip(").,;")
    if "/" in cand and rel_ok(cand):
        p = resolve(cand)
        if p.exists():
            d = cache.get(cand) or cache.setdefault(cand, digest(p))
            return {"ref": ref, "class": "dir_ref" if d["kind"] == "directory" else "unpinned",
                    "path": cand, "current_sha256": d.get("sha256")}
    return {"ref": ref, "class": "unresolvable", "path": None,
            "detail": "not a repo-relative path with a hash or line anchor"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(EVENTS.relative_to(ROOT)),
                    help="event stream to audit (repo-relative or absolute)")
    ap.add_argument("--snapshot-copy", default=None,
                    help="directory: copy the stream there as events_<sha12>.jsonl and audit the copy")
    args = ap.parse_args()

    src = Path(args.events)
    if not src.is_absolute():
        src = ROOT / src
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.snapshot_copy:
        dst_dir = Path(args.snapshot_copy)
        if not dst_dir.is_absolute():
            dst_dir = ROOT / dst_dir
        dst_dir.mkdir(parents=True, exist_ok=True)
        raw = src.read_bytes()
        dst = dst_dir / f"events_{sha256_bytes(raw)[:12]}.jsonl"
        dst.write_bytes(raw)
        src = dst
    scan_start = now()
    snap, events, _ = load_snapshot(src)
    cache: dict = {}

    claims, artifacts = [], []
    class_counts = {c: {"claims": 0, "claim_refs": 0, "refs": {"hash_match": 0, "hash_stale": 0,
                                                               "hash_missing": 0, "line_ref": 0,
                                                               "unpinned": 0, "dir_ref": 0,
                                                               "unresolvable": 0},
                        "artifacts": 0, "artifact_match": 0, "artifact_stale": 0,
                        "artifact_missing": 0, "artifact_placeholder": 0} for c in FROZEN}
    totals = {"claim_events": 0, "claim_events_frozen_bound": 0, "claim_events_other": 0,
              "refs_total": 0, "refs": {}, "artifact_events": 0,
              "artifact_events_frozen_bound": 0, "artifact_events_other": 0,
              "artifact_verdicts": {}}
    stale_actors: dict = {}
    stale_paths: dict = {}
    examples = {"hash_stale": [], "hash_missing": [], "unpinned": [], "unresolvable": []}

    for ev in events:
        et = ev.get("event_type")
        actor = ev.get("actor", "?")
        eid = ev.get("event_id", "?")
        cls = classes_of(ev)
        if et == "claim":
            totals["claim_events"] += 1
            if not cls:
                totals["claim_events_other"] += 1
                continue
            totals["claim_events_frozen_bound"] += 1
            refs = ev.get("evidence_refs") or []
            if not isinstance(refs, list):
                refs = [str(refs)]
            row = {"event_id": eid, "actor": actor, "created_at": ev.get("created_at"),
                   "classes": sorted(cls), "node_id": ev.get("node_id"),
                   "gate": ev.get("gate"), "conclusion_type": ev.get("conclusion_type"),
                   "refs": []}
            for c in cls:
                class_counts[c]["claims"] += 1
            for ref in refs:
                if not isinstance(ref, str):
                    ref = str(ref)
                r = classify_ref(ref, cache)
                totals["refs_total"] += 1
                totals["refs"][r["class"]] = totals["refs"].get(r["class"], 0) + 1
                for c in cls:
                    class_counts[c]["claim_refs"] += 1
                    class_counts[c]["refs"][r["class"]] += 1
                if r["class"] in ("hash_stale", "hash_missing"):
                    stale_actors[actor] = stale_actors.get(actor, 0) + 1
                    key = r.get("path") or ref
                    stale_paths[key] = stale_paths.get(key, 0) + 1
                if r["class"] in examples and len(examples[r["class"]]) < 12:
                    examples[r["class"]].append({"event_id": eid, "actor": actor, **r})
                row["refs"].append(r)
            if row["refs"]:
                claims.append(row)
        elif et == "artifact":
            totals["artifact_events"] += 1
            if not cls:
                totals["artifact_events_other"] += 1
                continue
            totals["artifact_events_frozen_bound"] += 1
            path_str = ev.get("path") or ""
            declared = str(ev.get("sha256") or "")
            p = resolve(path_str) if path_str and rel_ok(path_str) else None
            if not path_str or p is None or not p.exists():
                verdict = "missing"
                cur = None
            elif not re.fullmatch(r"[0-9a-fA-F]{64}", declared):
                verdict = "placeholder"
                cur = None
            else:
                d = cache.get(path_str) or cache.setdefault(path_str, digest(p))
                cur = d["sha256"]
                verdict = "match" if cur.lower() == declared.lower() else "stale"
            totals["artifact_verdicts"][verdict] = totals["artifact_verdicts"].get(verdict, 0) + 1
            for c in cls:
                class_counts[c]["artifacts"] += 1
                class_counts[c]["artifact_" + verdict] = class_counts[c].get("artifact_" + verdict, 0) + 1
            artifacts.append({"event_id": eid, "actor": actor, "created_at": ev.get("created_at"),
                              "classes": sorted(cls), "path": path_str,
                              "declared_sha256": declared, "current_sha256": cur,
                              "verdict": verdict})

    # stability re-hash
    changed = []
    for path_str, d in sorted(cache.items()):
        if d["kind"] != "file":
            continue
        fresh = sha256_file(resolve(path_str))
        if fresh != d["sha256"]:
            changed.append({"path": path_str, "scan_sha256": d["sha256"], "recheck_sha256": fresh})

    scan_end = now()

    def falsifier(what: str) -> str:
        return ("Re-run this checker on the same events.jsonl sha256. This finding is FALSIFIED if "
                + what + "; a change to the inputs after the snapshot is not a falsifier.")

    findings = []
    stale = totals["refs"].get("hash_stale", 0)
    missing = totals["refs"].get("hash_missing", 0)
    unpinned = totals["refs"].get("unpinned", 0)
    unres = totals["refs"].get("unresolvable", 0)
    if stale:
        findings.append({
            "id": "W042-EB-01", "severity": "major",
            "statement": f"{stale} hash-pinned evidence_ref(s) in class-bound claims cite a sha256 "
                         f"prefix that no longer matches the file on disk at snapshot "
                         f"{snap['sha256'][:12]}.",
            "examples": examples["hash_stale"],
            "falsifier": falsifier("any ref classified hash_stale re-hashes to a prefix match"),
        })
    if missing:
        findings.append({
            "id": "W042-EB-02", "severity": "major",
            "statement": f"{missing} evidence_ref(s) point at files that do not exist at the snapshot.",
            "examples": examples["hash_missing"],
            "falsifier": falsifier("any ref classified hash_missing resolves to an existing file"),
        })
    if unpinned:
        findings.append({
            "id": "W042-EB-03", "severity": "minor",
            "statement": f"{unpinned} evidence_ref(s) name an existing file with no hash or line anchor "
                         f"(protocol rule 4 asks for `path#sha256-prefix`).",
            "examples": examples["unpinned"],
            "falsifier": falsifier("any ref classified unpinned turns out to carry a hash prefix"),
        })
    if unres:
        findings.append({
            "id": "W042-EB-04", "severity": "minor",
            "statement": f"{unres} evidence_ref(s) cannot be mapped to a repo-relative path or line anchor "
                         f"(prose-only citations are not machine-checkable).",
            "examples": examples["unresolvable"],
            "falsifier": falsifier("any ref classified unresolvable resolves to a repo path on re-parse"),
        })
    av = totals["artifact_verdicts"]
    if av.get("stale") or av.get("missing") or av.get("placeholder"):
        findings.append({
            "id": "W042-EB-05", "severity": "major",
            "statement": f"class-bound artifact events at this snapshot: {av.get('match', 0)} match, "
                         f"{av.get('stale', 0)} stale, {av.get('missing', 0)} missing, "
                         f"{av.get('placeholder', 0)} with a non-hash sha256 placeholder.",
            "examples": [a for a in artifacts if a["verdict"] != "match"][:12],
            "falsifier": falsifier("any artifact classified stale/missing/placeholder re-checks as a match"),
        })
    if changed:
        findings.append({
            "id": "W042-EB-06", "severity": "info",
            "statement": f"{len(changed)} referenced file(s) changed bytes between first hash and re-hash "
                         f"during the scan; hash verdicts are snapshot-bound.",
            "examples": changed[:12],
            "falsifier": falsifier("any changed-during-scan file re-hashes to its scan value"),
        })

    per_class = {}
    for c in FROZEN:
        cc = class_counts[c]
        refs = cc["refs"]
        bound = refs["hash_match"] + refs["hash_stale"] + refs["hash_missing"]
        per_class[c] = {
            "canonical_artifact": CANONICAL[c],
            "claims": cc["claims"], "claim_refs": cc["claim_refs"],
            "refs": refs,
            "hash_bound_refs": bound,
            "hash_bound_match_rate": round(refs["hash_match"] / bound, 4) if bound else None,
            "artifact_events": cc["artifacts"],
            "artifact_match": cc["artifact_match"], "artifact_stale": cc["artifact_stale"],
            "artifact_missing": cc["artifact_missing"],
            "artifact_placeholder": cc["artifact_placeholder"],
        }

    report = {
        "task_id": "W042-CLASS-EVID-BIND-01",
        "actor": "worker-042",
        "created_at": scan_end,
        "question": "At one event-stream snapshot, do class-bound claims cite hash-resolvable "
                    "evidence, and do class-bound artifact events declare the bytes on disk?",
        "conclusion_type": "formal_model",
        "classification_rule": {
            "hash_match": "path#<hex>=7..64 and file sha256 startswith <hex>",
            "hash_stale": "path#<hex> but file sha256 differs",
            "hash_missing": "path#<hex> or line anchor but file absent",
            "line_ref": "path#Lx[-Ly] or path:N and file exists (no hash to check)",
            "unpinned": "existing file cited with no hash/line anchor",
            "dir_ref": "cited path is a directory (prefix-hash not applicable)",
            "unresolvable": "ref is prose or outside the repo",
        },
        "frozen_classes": FROZEN,
        "snapshot": snap,
        "totals": totals,
        "per_class": per_class,
        "stale_ref_actors": dict(sorted(stale_actors.items(), key=lambda kv: (-kv[1], kv[0]))),
        "stale_ref_paths": dict(sorted(stale_paths.items(), key=lambda kv: (-kv[1], kv[0]))),
        "claims": sorted(claims, key=lambda r: r["event_id"]),
        "artifact_events": sorted(artifacts, key=lambda r: r["event_id"]),
        "stable_during_scan": not changed,
        "changed_during_scan": changed,
        "findings": findings,
        "tool": {"path": "artifacts/worker-042/class_evidence_bind/audit_class_evidence.py",
                 "sha256": sha256_file(Path(__file__).resolve())},
        "inputs": {"events_path": snap["path"], "events_sha256": snap["sha256"]},
        "rerun_command": ("python3 artifacts/worker-042/class_evidence_bind/audit_class_evidence.py "
                          f"--events {snap['path']}"),
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True))

    lines = [
        "# W042-CLASS-EVID-BIND-01 — class-bound evidence binding audit",
        "",
        f"- actor: worker-042; snapshot events.jsonl `{snap['sha256'][:12]}` "
        f"({snap['events_parsed']} events, {snap['lines']} lines); scan {scan_start} → {scan_end}",
        "- method: classify every evidence_ref of every claim bound to a frozen class; re-hash the "
        "files on disk; compare artifact-event sha256 declarations; re-hash at end for stability.",
        f"- re-run: `{report['rerun_command']}`",
        "",
        "## Headline (snapshot-bound)",
        "",
        f"- frozen-class claim events: {totals['claim_events_frozen_bound']} of {totals['claim_events']} "
        f"claim events; evidence_refs on them: {totals['refs_total']}",
        "- ref verdicts: " + ", ".join(f"{k}={v}" for k, v in sorted(totals["refs"].items())),
        f"- class-bound artifact events: {totals['artifact_events_frozen_bound']} of "
        f"{totals['artifact_events']}; verdicts: "
        + ", ".join(f"{k}={v}" for k, v in sorted(totals["artifact_verdicts"].items())),
        "",
        "## Per frozen class",
        "",
        "| class | claims | refs | hash-bound | match rate | artifacts match/stale/missing |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for c in FROZEN:
        r = per_class[c]
        lines.append(f"| {c} | {r['claims']} | {r['claim_refs']} | {r['hash_bound_refs']} | "
                     f"{r['hash_bound_match_rate']} | {r['artifact_match']}/{r['artifact_stale']}/"
                     f"{r['artifact_missing']} |")
    lines += ["", "## Findings (each carries its own falsifier)", ""]
    for f in findings:
        lines.append(f"- **{f['id']}** ({f['severity']}): {f['statement']}")
        lines.append(f"  - falsifier: {f['falsifier']}")
    lines += [
        "",
        "## Interpretation limits (why a stale verdict is not an accusation of error)",
        "",
        "- A `hash_stale` verdict means the cited bytes changed after the event was written; the "
        "declaration may have been true at write time. It is exactly the binding-drift the controller "
        "records in CF-11/CF-13 and the G-FORM unmet item 'no accept at the current hash'.",
        "- `unresolvable` refs are prose citations (`file.md line 39`, `map F2 line 28`); they cannot be "
        "machine-checked and are reported, not judged.",
        "- Frozen schemas are expected to be revised; the actionable quantity is how many class-bound "
        "claims/artifacts still resolve to the current canonical bytes at the snapshot.",
        "",
        "## Top drift targets (stale refs per file)",
        "",
    ]
    for path_str, n in list(report["stale_ref_paths"].items())[:10]:
        lines.append(f"- `{path_str}`: {n}")
    lines += [
        "",
        "## Scope / non-claims",
        "",
        "- This is a snapshot audit of a live workspace; verdicts bind to the recorded hashes only.",
        "- No node is marked done, no gate verdict is claimed, no canonical artifact was edited.",
        "- Classification is mechanical: `path#<hex-prefix>` is the only machine-checkable binding.",
        "",
    ]
    README.write_text("\n".join(lines))
    print(json.dumps({
        "task_id": report["task_id"], "snapshot": snap["sha256"][:12],
        "claim_events_frozen_bound": totals["claim_events_frozen_bound"],
        "refs_total": totals["refs_total"], "refs": totals["refs"],
        "artifact_verdicts": totals["artifact_verdicts"],
        "findings": [f["id"] for f in findings],
        "report_sha256": sha256_file(REPORT),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
