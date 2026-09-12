#!/usr/bin/env python3
"""Audit runner: enforce A0 rubric over the live swarm workspace.

Usage:
  python3 artifacts/audit/audit_run.py                # full run, writes reports + outbox events
  python3 artifacts/audit/audit_run.py --quiet        # checkpoint mode, no outbox events
  python3 artifacts/audit/audit_run.py --kind gate    # only gate/status events

Exit code is 0 unless a critical violation is found and --fail-on-critical is passed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "research_map"))

import audit_lib as A  # noqa: E402

STARTED_AT = ROOT / "runtime" / "state" / "started_at"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def elapsed() -> float:
    try:
        t0 = datetime.fromisoformat(STARTED_AT.read_text().strip())
        return round((datetime.now(t0.tzinfo) - t0).total_seconds(), 1)
    except Exception:
        return -1.0


def iter_json_objects(path: Path):
    """Yield JSON objects from .json / .jsonl / .md (fenced json blocks)."""
    if not path.is_file():
        return
    text = path.read_text(errors="replace")
    if path.suffix == ".jsonl":
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    yield json.loads(line)
                except ValueError:
                    pass
    elif path.suffix == ".json":
        try:
            obj = json.loads(text)
        except ValueError:
            return
        if isinstance(obj, list):
            yield from (o for o in obj if isinstance(o, dict))
        elif isinstance(obj, dict):
            yield obj
    elif path.suffix in (".md", ".txt"):
        for block in _fenced(text):
            try:
                obj = json.loads(block)
            except ValueError:
                continue
            if isinstance(obj, dict):
                yield obj
            elif isinstance(obj, list):
                yield from (o for o in obj if isinstance(o, dict))


def _fenced(text: str):
    import re
    return re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)


def scan_corpus(dirs: list[Path]) -> dict:
    claims, artifacts, citations, results, records = [], [], [], [], []
    files = []
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file() or p.suffix not in (".json", ".jsonl"):
                continue
            if "audit/reports" in str(p) or "audit/checkpoints" in str(p):
                continue
            files.append(str(p.resolve().relative_to(ROOT.resolve())))
            for obj in iter_json_objects(p):
                rel = str(p.resolve().relative_to(ROOT.resolve()))
                is_schema_doc = any(k in obj for k in
                                    ("class_components", "quantifiers", "axes", "documents",
                                     "quantifier_order", "inextendibility", "artifact_kind"))
                is_fixture = any(t in rel for t in ("/fixtures/", "/corpus/", "/selftest/", "repaired_inputs")) \
                    or rel.endswith(("EXPECTATIONS.json", "manifest.json"))
                if not is_fixture and ("claim_id" in obj or
                                       (not is_schema_doc and "class_id" in obj
                                        and "statement" in obj)):
                    obj.setdefault("_source", rel)
                    claims.append(obj)
                status = obj.get("resolution_status") or obj.get("status")
                if status and ("cite_key" in obj or "source_id" in obj) and not is_fixture:
                    if "resolution_status" not in obj:
                        obj["resolution_status"] = normalize_citation_status(str(status))
                    obj.setdefault("_source", rel)
                    citations.append(obj)
                if "node_id" in obj and "path" in obj and "sha256" in obj:
                    obj.setdefault("_source", rel)
                    artifacts.append(obj)
                if "seeds" in obj and "statistic" in obj:
                    obj.setdefault("_source", rel)
                    results.append(obj)
                if "theorem_id" in obj or ("class_ids" in obj and "statement_exact" in obj):
                    obj.setdefault("_source", rel)
                    records.append(obj)
    return {"files": files, "claims": claims, "artifacts": artifacts,
            "citations": citations, "results": results, "records": records}


def normalize_citation_status(status: str) -> str:
    """Map ledger spellings onto the rubric vocabulary; unknown -> unresolved (fail closed)."""
    s = status.strip().lower().replace("-", "_").replace(" ", "_")
    table = {
        "verified_primary": "verified_primary",
        "verified_api": "verified_secondary",
        "verified_secondary": "verified_secondary",
        "partial": "partial",
        "unresolved": "unresolved",
        "contradicted": "contradicted",
    }
    return table.get(s, "unresolved")


def gate_verdicts(mapv, claimv, dup, cit) -> dict:
    """Derive gate verdicts from measured violations; pending until evidence exists."""
    critical = [v for v in mapv + claimv if v.severity == "critical"]
    return {
        "G-FORM": "pending" if not any(c.get("class_id") for c in []) else
                  ("fail" if any(v.hf in ("HF-02", "HF-06") for v in claimv) else "pass"),
        "G-LIT": ("pending" if cit["n"] == 0 else
                  ("pass" if cit["score"] == 1.0 and not cit["contradicted"] else "fail")),
        "G-AUDIT": ("pending" if not mapv and not claimv else
                    ("fail" if critical else "pass")),
        "G-NUM": "pending",
    }


def emit_events(report: dict, outdir: Path, kind: str = "all") -> str | None:
    """Write validated upward events; dedupe by content so 15-min ticks do not spam."""
    outdir.mkdir(parents=True, exist_ok=True)
    events = []
    base = {"actor": "lead-audit", "created_at": now_iso()}
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    summary = report["summary"]

    events.append({**base, "event_id": f"audit-status-{stamp}",
                   "event_type": "status", "node_id": "A1",
                   "status": "active",
                   "hours": round(elapsed() / 3600.0, 3),
                   "summary": (f"audit tick: critical={summary['critical']} "
                               f"total={summary['total']} citations={report['citation_support']['n']} "
                               f"gate={report['gates']['G-AUDIT']}"),
                   "evidence_refs": [report["report_path"]],
                   "next_falsifier": "re-run after each new lead artifact; any critical HF blocks G-AUDIT"})

    if kind in ("all", "findings") and summary["critical"] > 0:
        events.append({**base, "event_id": f"audit-review-map-{stamp}",
                       "event_type": "review", "target_id": "A1/map-integrity",
                       "reviewer": "lead-audit", "verdict": "reject", "score": 1.0,
                       "hard_failures": sorted({v["hf"] for v in report["violations"]
                                                if v["severity"] == "critical"}),
                       "findings": [f"{v['where']}: {v['detail']}" for v in report["violations"]
                                    if v["severity"] == "critical"][:12],
                       "evidence_refs": [report["report_path"]]})
    if kind == "all":
        events.append({**base, "event_id": f"audit-artifact-rubric-{stamp}",
                       "event_type": "artifact", "node_id": "A0",
                       "artifact_type": "evaluation_rubric",
                       "path": "artifacts/audit/evaluation_rubric.yaml",
                       "sha256": report["rubric_sha256"],
                       "validation_status": ("passed" if summary["critical"] == 0 else "unverified"),
                       "evidence_refs": [report["report_path"]]})

    path = outdir / f"audit-{stamp}.jsonl"
    try:
        from schemas import validate_event, SchemaError  # type: ignore
    except Exception:
        validate_event, SchemaError = (lambda e: e), Exception  # type: ignore
    accepted, rejected = [], []
    for ev in events:
        try:
            validate_event(ev)
            accepted.append(ev)
        except Exception as e:  # SchemaError or anything else during concurrent schema edits
            ev["_schema_error"] = str(e)
            rejected.append(ev)
    if accepted:
        with open(path, "a") as f:
            for ev in accepted:
                f.write(json.dumps(ev, sort_keys=True) + "\n")
    if rejected:
        rej = ROOT / "comms" / "outbox" / "audit-REJECTED.jsonl"
        with open(rej, "a") as f:
            for ev in rejected:
                f.write(json.dumps(ev, sort_keys=True) + "\n")
    return (str(path.relative_to(ROOT)) if accepted else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=str(ROOT / "research_map" / "research_map.json"))
    ap.add_argument("--scan", nargs="*", default=["artifacts", "comms/outbox", "ledger"])
    ap.add_argument("--out", default=str(HERE / "reports"))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--fail-on-critical", action="store_true")
    ap.add_argument("--kind", default="all", choices=["all", "findings", "gate"])
    a = ap.parse_args()

    t0 = time.time()
    rubric = A.load_rubric()
    classes = A.frozen_classes(rubric)

    mapv = A.check_map_integrity(a.map)
    inv = A.artifact_inventory(a.map)
    corpus = scan_corpus([ROOT / s for s in a.scan])

    claimv = []
    for c in corpus["claims"]:
        claimv += A.check_class_binding(c, classes)
    registry = {}
    for c in corpus["citations"]:
        key = c.get("cite_key") or c.get("id") or c.get("title")
        if key:
            registry[key] = c
    for c in corpus["claims"]:
        claimv += A.check_citations(c, registry)
    for r in corpus["results"]:
        claimv += A.check_seed_hygiene(r)
    claimv += A.check_ledger_scope(corpus["citations"])
    self_cert = A.check_self_certification(corpus["records"])
    if self_cert:
        by_file: dict[str, int] = {}
        for v in self_cert:
            by_file[v.evidence.get("source", "ledger")] = by_file.get(v.evidence.get("source", "ledger"), 0) + 1
        for src, n in sorted(by_file.items()):
            claimv.append(A.Violation("HF-14", "critical", f"ledger:{src}",
                                      f"{n} records self-certified as accepted/supports_claim with no "
                                      "independent reviewer verdict", {"file": src}))
    frozen_ids = set(classes)
    invented: dict[str, int] = {}
    for rec in corpus["records"]:
        for cid in rec.get("class_ids", []) or []:
            if cid not in frozen_ids and cid not in ("DEFINITIONS", "GLOBAL"):
                invented[cid] = invented.get(cid, 0) + 1
    for cid, n in sorted(invented.items()):
        claimv.append(A.Violation("HF-02", "critical", f"ledger:class-token",
                                  f"invented class token {cid!r} used by {n} ledger entries: not in the "
                                  "frozen taxonomy; open a class via direction_update or re-label as an evidence family",
                                  {"token": cid}))

    # HF-13: cross-project contamination in text artifacts (excluding the base project's own
    # directories and this audit's tooling, where the token lists live by necessity)
    contam_files = 0
    for d in ("artifacts", "research_map", "schemas"):
        base = ROOT / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix not in (".md", ".yaml", ".yml", ".json", ".jsonl", ".py", ".txt"):
                continue
            rel = str(p.relative_to(ROOT))
            if rel.startswith("artifacts/audit/") or p.stat().st_size > 2_000_000:
                continue
            contam_files += 1
            claimv += A.check_contamination(p.read_text(errors="replace"), rel, rel)

    cit = A.citation_support(corpus["citations"])
    texts = {}
    for c in corpus["claims"]:
        cid = c.get("claim_id") or c.get("event_id") or c.get("_source", "?")
        texts[f"{cid}@{c.get('_source','')}"] = str(c.get("statement", ""))
    dup = A.duplication_report(texts) if texts else {
        "n": 0, "duplicate_pairs": [], "duplicate_cluster_rate": 0.0,
        "mean_novelty": None, "novelty": {}}

    # aggregate per-file systemic findings so checkpoint summaries stay readable
    def _merge(vs, hfs):
        keep, groups = [], {}
        for v in vs:
            if v.hf in hfs:
                groups.setdefault(v.hf, []).append(v)
            else:
                keep.append(v)
        import re as _re
        for hf, g in groups.items():
            total = 0
            for v in g:
                m = _re.search(r"(\d+)\s+(of the ledger's citations|records)", v.detail)
                total += int(m.group(1)) if m else 1
            files = [v.where.split(":", 1)[1] if ":" in v.where else v.where for v in g]
            keep.append(A.Violation(hf, g[0].severity, f"{hf}:systemic",
                                    f"{total} affected records across {len(g)} ledger files "
                                    f"({', '.join(files[:5])}{'...' if len(files) > 5 else ''})",
                                    {"files": files}))
        return keep
    claimv = _merge(claimv, {"HF-14", "HF-03"})
    violations = mapv + claimv
    summary = A.summarize(violations)
    gates = gate_verdicts(mapv, claimv, dup, cit)

    report = {
        "audit": "A1-live",
        "generated_at": now_iso(),
        "elapsed_since_swarm_start_s": elapsed(),
        "map": str(Path(a.map).relative_to(ROOT)),
        "map_sha256": A.sha256_file(a.map),
        "rubric_sha256": A.sha256_file(A.RUBRIC),
        "corpus": {k: (len(v) if isinstance(v, list) else v) for k, v in corpus.items()},
        "corpus_files": corpus["files"],
        "inventory": inv,
        "violations": [v.as_dict() for v in violations],
        "summary": summary,
        "citation_support": cit,
        "duplication": dup,
        "gates": gates,
        "runtime_s": round(time.time() - t0, 3),
    }
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    report["report_path"] = str((out / f"audit-{stamp}.json").relative_to(ROOT))
    sha = A.write_json(out / f"audit-{stamp}.json", report)
    report["report_sha256"] = sha
    A.write_json(out / "LATEST.json", report)

    # markdown summary
    lines = [
        f"# Audit tick {stamp}",
        "",
        f"- elapsed since swarm start: {report['elapsed_since_swarm_start_s']}s",
        f"- map sha256: `{report['map_sha256']}`",
        f"- rubric sha256: `{report['rubric_sha256']}`",
        f"- corpus: {report['corpus']}",
        f"- violations: {summary['total']} (critical {summary['critical']}) {summary['by_hf']}",
        f"- citations: n={cit['n']} score={cit['score']} unresolved={len(cit['unresolved'])}",
        f"- duplication: n={dup['n']} cluster_rate={dup['duplicate_cluster_rate']} "
        f"mean_novelty={dup['mean_novelty']}",
        f"- gates: {gates}",
        "",
        "## Violations",
    ]
    for v in report["violations"][:60]:
        lines.append(f"- **{v['hf']}** ({v['severity']}) `{v['where']}`: {v['detail']}")
    (out / "LATEST.md").write_text("\n".join(lines) + "\n")

    if not a.quiet:
        ev = emit_events(report, ROOT / "comms" / "outbox", kind=a.kind)
        if ev:
            print(f"events -> {ev}")
    print(f"audit: violations={summary['total']} critical={summary['critical']} "
          f"citations={cit['n']} gates={gates} -> {report['report_path']}")
    if a.fail_on_critical and summary["critical"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
