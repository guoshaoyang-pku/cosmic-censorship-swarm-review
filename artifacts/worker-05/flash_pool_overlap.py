#!/usr/bin/env python3
"""W05-T1: Flash-pool intent-overlap and assignment-gap snapshot (A1/A2 support).

Measures, from a *frozen snapshot* of the live worker logs, how the 20 DeepSeek Flash
executors are self-selecting targets when comms/inbox has no lead assignment.  This is a
coordination measurement, not a mathematical review: it never reads a draft's content and
never marks any research-map node complete.

Usage:
    python3 artifacts/worker-05/flash_pool_overlap.py --selftest
    python3 artifacts/worker-05/flash_pool_overlap.py --scan
    python3 artifacts/worker-05/flash_pool_overlap.py --scan --root <repo> --out <prefix>

Design notes
------------
* stdlib only; no network; deterministic given the log snapshot.
* Every finding carries evidence refs `runtime/logs/<file>.log:<line>`.
* `--scan` runs the `--selftest` control first and records the result ("run the null first").
* The evidence is *live*: log SHA256 hashes are recorded so a later re-run can detect drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter, OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
MAP_NODE_ORDER = ["F0", "F1", "F2", "L0", "L1", "N0", "N1", "A0", "A1", "A2"]
NODE_RE = re.compile(r"(?<![A-Za-z0-9])([FLNA][0-9])(?![0-9])")
CLASS_RE = re.compile(r"(?<![A-Za-z0-9])(AF-[A-Z0-9]+(?:-[A-Z0-9]+){2,})(?![A-Za-z0-9-])")
PATH_RE = re.compile(r"(?:artifacts|reviews|schemas|ledger|numerics|evaluation)/[A-Za-z0-9_./+-]+")
QUEUE_LINE_RE = re.compile(r"^-\s*([A-Za-z][0-9](?:/[A-Za-z][0-9])*)\s*:")
QUEUE_HEADING_RE = re.compile(r"^##\s+Immediate queue\s*$", re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_path(raw: str) -> str:
    """Normalize a mentioned artifact path; return '' if it is not a usable target."""
    p = raw.strip()
    p = p.rstrip(".,;:)]}'\"`")
    if "..." in p:
        p = p.split("...", 1)[0].rstrip("/")
    p = re.sub(r"/+", "/", p)
    p = p.rstrip("/")
    if not p or "/" not in p:
        return ""
    return p


def extract_intents(text: str) -> dict:
    """Extract node / class / path mentions with first-mention line numbers."""
    node_mentions: Counter = Counter()
    node_first: dict[str, int] = {}
    class_mentions: Counter = Counter()
    class_first: dict[str, int] = {}
    path_mentions: Counter = Counter()
    path_first: dict[str, int] = {}
    rejected_nodes: Counter = Counter()
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in NODE_RE.finditer(line):
            token = m.group(1)
            if token in MAP_NODE_ORDER:
                node_mentions[token] += 1
                node_first.setdefault(token, lineno)
            else:
                rejected_nodes[token] += 1
        for m in CLASS_RE.finditer(line):
            token = m.group(1)
            class_mentions[token] += 1
            class_first.setdefault(token, lineno)
        for m in PATH_RE.finditer(line):
            token = normalize_path(m.group(0))
            if token:
                path_mentions[token] += 1
                path_first.setdefault(token, lineno)
    return {
        "node_mentions": dict(sorted(node_mentions.items())),
        "node_first_line": node_first,
        "class_mentions": dict(sorted(class_mentions.items())),
        "class_first_line": class_first,
        "path_mentions": dict(sorted(path_mentions.items())),
        "path_first_line": path_first,
        "rejected_node_tokens": dict(rejected_nodes),
    }


def parse_queue(handoff_text: str) -> list[str]:
    """Read node IDs from the '## Immediate queue' section of ASTRA_HANDOFF.md."""
    m = QUEUE_HEADING_RE.search(handoff_text)
    if not m:
        return []
    tail = handoff_text[m.end():]
    nxt = NEXT_HEADING_RE.search(tail)
    section = tail[: nxt.start()] if nxt else tail
    nodes: list[str] = []
    for line in section.splitlines():
        q = QUEUE_LINE_RE.match(line.strip())
        if q:
            for part in q.group(1).split("/"):
                if part not in nodes:
                    nodes.append(part)
    return nodes


def primary_node(node_mentions: dict) -> tuple[str | None, bool]:
    if not node_mentions:
        return None, False
    ranked = sorted(
        node_mentions.items(),
        key=lambda kv: (-kv[1], MAP_NODE_ORDER.index(kv[0]) if kv[0] in MAP_NODE_ORDER else 99),
    )
    top_count = ranked[0][1]
    tied = [n for n, c in ranked if c == top_count]
    return ranked[0][0], len(tied) > 1


def build_record(log_path: Path, root: Path) -> dict:
    text = log_path.read_text(errors="replace")
    intents = extract_intents(text)
    primary, ambiguous = primary_node(intents["node_mentions"])
    return {
        "worker_id": log_path.stem,
        "log": str(log_path.relative_to(root)),
        "sha256": sha256_file(log_path),
        "bytes": log_path.stat().st_size,
        "lines": len(text.splitlines()),
        "empty": len(text.strip()) == 0,
        "primary_node": primary,
        "primary_ambiguous": ambiguous,
        **intents,
    }


def evidence_refs(root: Path, records: list[dict], node: str) -> list[str]:
    refs = []
    for r in records:
        if node in r["node_first_line"]:
            refs.append(f"{r['log']}:{r['node_first_line'][node]}")
    return refs


def check_control() -> tuple[bool, str]:
    """Planted-overlap control: two synthetic logs overlap on F1, one does not, one is adversarial."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "syn-a.log").write_text(
            "dsh: reasoning:\nI will target F1 and write schemas/af_wcc_vacuum.yaml for AF-WCC-VAC-GEN.\n"
        )
        (t / "syn-b.log").write_text(
            "Node binding: F1.\nArtifact: `schemas/af_wcc_vacuum.yaml` (class AF-WCC-VAC-GEN).\n"
        )
        (t / "syn-c.log").write_text(
            "Node binding: N0.\nPlan: numerics/tests/flat_wave.py for AF-WCC-SCALAR-SPH.\n"
            "Scratch dir artifacts/w06/... for notes.\n"
        )
        (t / "syn-d.log").write_text("Adversarial tokens F10 and AAF1 and XN0 must not match.\n")
        recs = [build_record(p, t) for p in sorted(t.glob("syn-*.log"))]
        by = {r["worker_id"]: r for r in recs}
        problems = []
        if set(by["syn-a"]["node_mentions"]) != {"F1"}:
            problems.append(f"syn-a nodes={by['syn-a']['node_mentions']}")
        if set(by["syn-b"]["node_mentions"]) != {"F1"}:
            problems.append(f"syn-b nodes={by['syn-b']['node_mentions']}")
        if set(by["syn-c"]["node_mentions"]) != {"N0"}:
            problems.append(f"syn-c nodes={by['syn-c']['node_mentions']}")
        if by["syn-d"]["node_mentions"]:
            problems.append(f"syn-d false positive nodes={by['syn-d']['node_mentions']}")
        if "schemas/af_wcc_vacuum.yaml" not in by["syn-a"]["path_mentions"]:
            problems.append("syn-a path not captured")
        if "schemas/af_wcc_vacuum.yaml" not in by["syn-b"]["path_mentions"]:
            problems.append("syn-b path not captured")
        if "numerics/tests/flat_wave.py" not in by["syn-c"]["path_mentions"]:
            problems.append("syn-c path not captured")
        if "artifacts/w06" not in by["syn-c"]["path_mentions"]:
            problems.append(f"syn-c ellipsis path={list(by['syn-c']['path_mentions'])}")
        if "AF-WCC-VAC-GEN" not in by["syn-a"]["class_mentions"]:
            problems.append("syn-a class not captured")
        if "AF-WCC-SCALAR-SPH" not in by["syn-c"]["class_mentions"]:
            problems.append("syn-c class not captured")
        # aggregate duplication check
        path_workers: dict[str, set] = {}
        for r in recs:
            for p in r["path_mentions"]:
                path_workers.setdefault(p, set()).add(r["worker_id"])
        if len(path_workers.get("schemas/af_wcc_vacuum.yaml", set())) != 2:
            problems.append("planted overlap not detected")
        if len(path_workers.get("numerics/tests/flat_wave.py", set())) != 1:
            problems.append("zero-overlap control failed")
        if problems:
            return False, "; ".join(problems)
        return True, "planted overlap detected; zero-overlap control clean; F10/AAFN0 rejected"


def scan(root: Path, out_prefix: Path) -> dict:
    selftest_ok, selftest_detail = check_control()
    map_path = root / "research_map" / "research_map.json"
    handoff_path = root / "research_map" / "ASTRA_HANDOFF.md"
    research_map = json.loads(map_path.read_text())
    handoff_text = handoff_path.read_text()

    node_owner: dict[str, tuple[str, dict]] = {}
    for group in research_map.get("groups", []):
        for node in group.get("nodes", []):
            node_owner[node["id"]] = (group["id"], node)

    log_paths = sorted((root / "runtime" / "logs").glob("deepseek-flash-*.log"))
    records = [build_record(p, root) for p in log_paths]

    node_workers: dict[str, list[str]] = {n: [] for n in node_owner}
    path_workers: dict[str, list[str]] = {}
    class_workers: dict[str, list[str]] = {}
    for r in records:
        for n in r["node_mentions"]:
            node_workers.setdefault(n, []).append(r["worker_id"])
        for p in r["path_mentions"]:
            path_workers.setdefault(p, []).append(r["worker_id"])
        for c in r["class_mentions"]:
            class_workers.setdefault(c, []).append(r["worker_id"])

    queue_nodes = parse_queue(handoff_text)
    zero_coverage_queue = [n for n in queue_nodes if not node_workers.get(n)]
    unclaimed_map_nodes = [n for n in node_owner if not node_workers.get(n)]

    inbox_files = sorted(p.name for p in (root / "comms" / "inbox").glob("*") if p.is_file())
    outbox_files = sorted(p.name for p in (root / "comms" / "outbox").glob("*") if p.is_file())
    outbox_events = []
    for p in (root / "comms" / "outbox").glob("*.json"):
        try:
            payload = json.loads(p.read_text())
            if isinstance(payload, dict) and "event_type" in payload:
                outbox_events.append({"file": p.name, "event_type": payload["event_type"], "actor": payload.get("actor")})
        except (ValueError, OSError):
            outbox_events.append({"file": p.name, "event_type": "UNPARSEABLE", "actor": None})

    declared_artifacts = {
        n: (gid, node.get("artifact"), (root / node["artifact"]).exists())
        for n, (gid, node) in node_owner.items()
        if node.get("artifact")
    }
    nodes_with_class_field = [
        n for n, (_, node) in node_owner.items() if "class_id" in node or "class_ids" in node
    ]

    def finding(fid, severity, statement, refs, falsifier):
        return {
            "id": fid,
            "severity": severity,
            "statement": statement,
            "evidence_refs": refs,
            "next_falsifier": falsifier,
        }

    findings = []
    findings.append(
        finding(
            "no-assignment-channel",
            "hard_failure" if not inbox_files else "observation",
            f"comms/inbox holds {len(inbox_files)} file(s) at scan time; the task protocol requires a "
            "class-bound lead assignment before execution agents act.",
            [f"comms/inbox/ ({len(inbox_files)} files)", "research_map/ASTRA_HANDOFF.md:47"],
            "A lead posts an `assignment` event naming node_id, assignee and gate; re-scan must then show 0 unassigned workers.",
        )
    )
    findings.append(
        finding(
            "no-contract-events",
            "hard_failure" if not outbox_events else "observation",
            f"comms/outbox holds {len(outbox_events)} contract event(s) from {len(records)} Flash workers at scan time; "
            "no worker output is auditable through the sanctioned channel yet.",
            [f"comms/outbox/ ({len(outbox_events)} events)", "research_map/schemas.py:13"],
            "Any outbox event appears; then count per-worker emission rate instead of presence.",
        )
    )
    if node_workers:
        top_node, top_workers = max(node_workers.items(), key=lambda kv: len(kv[1]))
        findings.append(
            finding(
                "node-concentration",
                "hard_failure" if len(top_workers) >= 5 else "warning" if len(top_workers) >= 3 else "observation",
                f"highest self-selected node concentration: {top_node} mentioned by {len(top_workers)} workers "
                f"({', '.join(top_workers)}); the map assigns each node to one group, not to a fleet.",
                evidence_refs(root, records, top_node),
                "Re-scan after assignments; concentration should fall to the node owner(s) if the protocol works.",
            )
        )
    findings.append(
        finding(
            "queue-coverage-gap",
            "warning" if zero_coverage_queue else "observation",
            f"immediate-queue nodes with zero Flash mention: {zero_coverage_queue or 'none'} "
            f"(queue parsed as {queue_nodes}).",
            ["research_map/ASTRA_HANDOFF.md:36-43"],
            "All queue nodes get at least one mention/assignee in a later snapshot.",
        )
    )
    findings.append(
        finding(
            "class-binding-unmachine-checkable",
            "warning",
            "research_map.json carries no structured class_id field on any of its "
            f"{len(node_owner)} nodes ({len(nodes_with_class_field)} with class_id/class_ids); class IDs "
            "exist only inside human-readable node labels, so the validator cannot detect cross-class leakage.",
            ["research_map/research_map.json:26-28", "research_map/validate_map.py:12-40", "research_map/ARCHITECTURE.md:63"],
            "Add class_id to every node and a leakage rule to validate_map.py; then a map with a leaked class must fail validation.",
        )
    )
    missing_artifacts = {n: v[1] for n, v in declared_artifacts.items() if v[1] and not v[2]}
    findings.append(
        finding(
            "declared-artifacts-absent",
            "hard_failure",
            f"{len(missing_artifacts)}/{len(declared_artifacts)} declared node artifacts are absent from disk "
            f"(including done/passed nodes): {missing_artifacts}. validate_map.py returns VALID because it never "
            "touches the filesystem.",
            ["research_map/research_map.json:26-56", "research_map/validate_map.py:23-26"],
            "Commit the declared artifacts (or downgrade the nodes); a re-scan must then find 0 absent declared artifacts.",
        )
    )

    result = {
        "task_id": "W05-T1",
        "worker": "deepseek-flash-05",
        "role": "execution worker (DeepSeek Flash breadth) — artifact-backed support to A1/A2, no node claimed complete",
        "generated_at": now_iso(),
        "scan": {
            "root": str(root),
            "log_glob": "runtime/logs/deepseek-flash-*.log",
            "logs_scanned": len(records),
            "empty_logs": [r["log"] for r in records if r["empty"]],
            "research_map_sha256": sha256_file(map_path),
            "astra_handoff_sha256": sha256_file(handoff_path),
            "queue_nodes": queue_nodes,
            "node_owner": {n: node_owner[n][0] for n in node_owner},
        },
        "selftest": {"ran": True, "passed": selftest_ok, "detail": selftest_detail},
        "channel_state": {
            "inbox_files": inbox_files,
            "outbox_files": outbox_files,
            "outbox_events": outbox_events,
        },
        "workers": records,
        "aggregates": OrderedDict(
            [
                (
                    "nodes",
                    {
                        n: {"count": len(v), "workers": v, "map_owner_group": node_owner.get(n, ("?",))[0]}
                        for n, v in sorted(node_workers.items(), key=lambda kv: (-len(kv[1]), kv[0]))
                    },
                ),
                (
                    "duplicated_paths",
                    {
                        p: {"count": len(v), "workers": v}
                        for p, v in sorted(path_workers.items(), key=lambda kv: (-len(kv[1]), kv[0]))
                        if len(v) > 1
                    },
                ),
                ("class_ids", {c: {"count": len(v), "workers": v} for c, v in sorted(class_workers.items())}),
                ("zero_coverage_queue_nodes", zero_coverage_queue),
                ("unclaimed_map_nodes", unclaimed_map_nodes),
                ("declared_artifacts", {n: {"group": v[0], "path": v[1], "exists": v[2]} for n, v in declared_artifacts.items()}),
                ("nodes_with_structured_class_id", nodes_with_class_field),
            ]
        ),
        "findings": findings,
        "limitations": [
            "Logs capture reasoning-in-progress, not final actions; mentions are intents, not assignments or deliverables.",
            "Snapshot is frozen at generated_at with per-log SHA256; a later re-run with different hashes invalidates direct comparison.",
            "Only deepseek-flash-*.log is scanned; group-lead (astra-*) logs are excluded by design.",
            "Primary-node attribution is a mention-count heuristic and is flagged when ties occur.",
            "Presence of a file at a mentioned path is NOT verified here; declared-artifact existence is checked only against the map.",
        ],
        "next_falsifier": (
            "Post explicit lead assignments in comms/outbox and re-scan: if node concentration collapses to assigned owners "
            "and zero_coverage_queue_nodes becomes empty while outbox_events > 0, the duplication/assignment-gap finding is "
            "refuted for that window."
        ),
    }
    return result


def write_markdown(result: dict, out_md: Path) -> None:
    agg = result["aggregates"]
    lines = []
    lines.append("# W05-T1 — Flash-pool intent-overlap and assignment-gap snapshot")
    lines.append("")
    lines.append(f"- **Worker:** {result['worker']} ({result['role']})")
    lines.append(f"- **Snapshot:** {result['generated_at']}")
    lines.append(f"- **Logs scanned:** {result['scan']['logs_scanned']} (empty: {result['scan']['empty_logs'] or 'none'})")
    lines.append(f"- **Self-test control:** {'PASS' if result['selftest']['passed'] else 'FAIL'} — {result['selftest']['detail']}")
    lines.append(f"- **research_map.json sha256:** `{result['scan']['research_map_sha256']}`")
    lines.append(f"- **ASTRA_HANDOFF.md sha256:** `{result['scan']['astra_handoff_sha256']}`")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    lines.append("| id | severity | statement | evidence |")
    lines.append("|---|---|---|---|")
    for f in result["findings"]:
        ev = "<br>".join(f["evidence_refs"][:6]) + ("<br>…" if len(f["evidence_refs"]) > 6 else "")
        lines.append(f"| `{f['id']}` | {f['severity']} | {f['statement']} | {ev} |")
    lines.append("")
    lines.append("## Node concentration (worker mentions, primary metric)")
    lines.append("")
    lines.append("| node | group | workers | worker list |")
    lines.append("|---|---|---:|---|")
    for n, d in agg["nodes"].items():
        lines.append(f"| {n} | {d['map_owner_group']} | {d['count']} | {', '.join(d['workers'])} |")
    lines.append("")
    lines.append("## Duplicated artifact paths (secondary)")
    lines.append("")
    if agg["duplicated_paths"]:
        lines.append("| path | workers |")
        lines.append("|---|---:|")
        for p, d in agg["duplicated_paths"].items():
            lines.append(f"| `{p}` | {d['count']} — {', '.join(d['workers'])} |")
    else:
        lines.append("_none_")
    lines.append("")
    lines.append("## Channel state")
    lines.append("")
    lines.append(f"- comms/inbox files: {result['channel_state']['inbox_files'] or 'EMPTY'}")
    lines.append(f"- comms/outbox files: {result['channel_state']['outbox_files'] or 'EMPTY'}")
    lines.append(f"- contract events parsed: {result['channel_state']['outbox_events'] or 'NONE'}")
    lines.append(f"- zero-coverage queue nodes: {agg['zero_coverage_queue_nodes'] or 'none'}")
    lines.append(f"- unclaimed map nodes: {agg['unclaimed_map_nodes'] or 'none'}")
    lines.append(f"- nodes with structured class_id: {agg['nodes_with_structured_class_id'] or 'NONE'}")
    lines.append("")
    lines.append("## Declared artifacts vs disk")
    lines.append("")
    lines.append("| node | group | declared path | exists |")
    lines.append("|---|---|---|---|")
    for n, d in agg["declared_artifacts"].items():
        lines.append(f"| {n} | {d['group']} | `{d['path']}` | {'yes' if d['exists'] else '**NO**'} |")
    lines.append("")
    lines.append("## Per-worker snapshot")
    lines.append("")
    lines.append("| worker | lines | sha256 (first 12) | primary node | nodes mentioned | classes | intended paths |")
    lines.append("|---|---:|---|---|---|---|---|")
    for r in result["workers"]:
        nodes = ", ".join(f"{k}×{v}" for k, v in r["node_mentions"].items()) or "—"
        classes = ", ".join(r["class_mentions"].keys()) or "—"
        paths = ", ".join(f"`{p}`" for p in list(r["path_mentions"])[:4]) or "—"
        if len(r["path_mentions"]) > 4:
            paths += f" (+{len(r['path_mentions']) - 4})"
        prim = r["primary_node"] or "—"
        if r["primary_ambiguous"]:
            prim += " (tie)"
        lines.append(
            f"| {r['worker_id']} | {r['lines']} | `{r['sha256'][:12]}` | {prim} | {nodes} | {classes} | {paths} |"
        )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for lim in result["limitations"]:
        lines.append(f"- {lim}")
    lines.append("")
    lines.append("## Next falsifier")
    lines.append("")
    lines.append(result["next_falsifier"])
    lines.append("")
    out_md.write_text("\n".join(lines))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true", help="run the planted-overlap control only")
    ap.add_argument("--scan", action="store_true", help="scan the frozen log snapshot and write JSON+MD")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]), help="repo root")
    ap.add_argument("--out", default=None, help="output prefix (default artifacts/worker-05/flash_pool_overlap)")
    args = ap.parse_args(argv)

    if args.selftest:
        ok, detail = check_control()
        print(("PASS" if ok else "FAIL") + ": " + detail)
        return 0 if ok else 1
    if not args.scan:
        ap.print_help()
        return 2

    root = Path(args.root).resolve()
    out_prefix = Path(args.out) if args.out else root / "artifacts" / "worker-05" / "flash_pool_overlap"
    if not out_prefix.is_absolute():
        out_prefix = root / out_prefix
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    result = scan(root, out_prefix)
    out_json = out_prefix.with_suffix(".json")
    out_md = out_prefix.with_suffix(".md")
    out_json.write_text(json.dumps(result, indent=2) + "\n")
    write_markdown(result, out_md)
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    print(f"selftest={'PASS' if result['selftest']['passed'] else 'FAIL'}")
    for f in result["findings"]:
        print(f"[{f['severity']}] {f['id']}: {f['statement'][:150]}")
    return 0 if result["selftest"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
