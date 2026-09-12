#!/usr/bin/env python3
"""L1 spot-check independence census (worker-028, gate G-LIT, node L1).

Question
--------
G-LIT requires ">=3 independent re-fetch spot checks". The controller counts *files*
(the 00:24 gate audit lists 19 paths). Files are not checks: the list can contain
superseded/buggy revisions, per-worker duplicates and auxiliary manifests, and a glob
can miss valid checks whose file name differs. This census asks instead:

  (a) how many distinct actors have a non-superseded check bound to the measured
      ledger hash (process independence, which is what the gate wording means);
  (b) which sampled rows each check covers, how much the samples overlap
      (overlap is redundancy, not dependence) and how much of the 97-row ledger the
      union actually covers;
  (c) which files a naive file-glob count would miscount.

What this does (read-only)
--------------------------
1. Enumerates candidate JSON under artifacts/*/l1_spotcheck/** and reviews/L1-spotcheck-*.
2. Per file: actor, declared ledger pin (ordered explicit keys, else weak
   `text_contains` fallback), superseded / draft flags, results-derived row set
   (explicit lists, `SRC-NNN` citation ids, referenced frozen manifests; prose is
   never parsed).
3. Binds pins to the measured ledger sha256, re-measures the ledger at the end.
4. Deduplicates actors, excludes superseded revisions, computes actor-level and
   file-level overlap, union coverage and redundancy.
5. Reports both the naive per-file count and the actor/coverage counts, with every
   mis-count named.

Controls (`--self-test`, always run and recorded):
  * positive: two actors sharing a row -> overlap MUST be reported;
  * negative: disjoint rows -> overlap MUST be empty;
  * superseded: superseded file MUST NOT add an actor;
  * unbound: wrong-pin file MUST NOT count as bound.
A census tool that cannot detect planted overlap is not evidence of independence.

Falsifiers
----------
* ledger hash changes -> every pin binding and count here is void;
* a check on disk this census did not enumerate;
* two checks called disjoint here are shown to share a ledger row;
* a declared pin is shown not to match the ledger bytes actually fetched.

Writes only its JSON artifact under artifacts/worker-028/. Global state
(research_map.json, artifact_hashes.json, ledger) is read-only input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[3]
LEDGER_REL = "ledger/citation_audit.csv"
OUT_REL = "artifacts/worker-028/l1_independence_census/independence_census.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HASH_SUFFIX = re.compile(r"#([0-9a-f]{12,64})\b")
SRC_ROW = re.compile(r"SRC-(\d{1,3})\b", re.I)
ROW_KEYS = ("sampled_rows", "sample_rows", "rows_sampled", "row_numbers", "rows", "sample_ids")
NUMERIC_LIST = re.compile(r"^\s*\d{1,3}(\s*[,; ]\s*\d{1,3})*\s*$")
SUPERSEDED_PATH = re.compile(r"/(superseded|pass1_strict)/|\.rev[12][-.]|instrument-bug|partial-fetch|\.rev[12]\.json$", re.I)
AUX_NAME = re.compile(r"manifest|preregist|sample_freeze|erratum|comparison", re.I)
PIN_STRONG_KEYS = ("reviewed_sha256", "artifact_sha256", "declared_sha256", "ledger_sha256", "frozen_pin", "sha256")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def norm_actor(obj: dict) -> str:
    for k in ("actor", "reviewer", "worker"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip() and v.strip() != "unknown":
            return v.strip().split("(")[0].strip()
    return "UNKNOWN"


def _pin_from_mapping(d: dict, prefix: str = "") -> tuple[str | None, str]:
    """Ordered explicit pin lookup inside a mapping."""
    for k in ("sha256_before_fetch", "sha256_before", "sha256_pinned", "frozen_pin", "pinned",
              "sha256_at_start", "sha256_declared_frozen", "sha256_before_fetch_measured",
              "sha256", "sha256_after_fetch", "sha256_after"):
        v = d.get(k)
        if isinstance(v, str) and HEX64.match(v):
            return v, f"{prefix}{k}"
    return None, ""


def get_pin(obj: dict, measured: str) -> tuple[str | None, str, str]:
    """Return (pin, where_found, strength). Explicit keys first, weak text fallback last."""
    t = obj.get("target")
    if isinstance(t, dict):
        p, w = _pin_from_mapping(t, "target.")
        if p:
            return p, w, "strong"
    elif isinstance(t, str) and HEX64.match(t):
        return t, "target", "strong"
    for key in PIN_STRONG_KEYS:
        v = obj.get(key)
        if isinstance(v, str) and HEX64.match(v):
            return v, key, "strong"
    inputs = obj.get("inputs")
    if isinstance(inputs, dict):
        for k, v in inputs.items():
            if isinstance(v, dict) and "citation_audit" in str(k):
                p, w = _pin_from_mapping(v, f"inputs[{k}].")
                if p:
                    return p, w, "strong"
    led = obj.get("ledger")
    if isinstance(led, dict) and led.get("citation_audit.csv") and HEX64.match(str(led["citation_audit.csv"])):
        return led["citation_audit.csv"], "ledger.citation_audit.csv", "strong"
    tid = obj.get("target_id")
    if isinstance(tid, str):
        m = HASH_SUFFIX.search(tid)
        if m and len(m.group(1)) >= 12:
            return m.group(1), "target_id#suffix", "strong"
    for ref in (obj.get("evidence_refs") or []):
        if isinstance(ref, str) and LEDGER_REL in ref:
            m = HASH_SUFFIX.search(ref)
            if m and len(m.group(1)) >= 12:
                return m.group(1), "evidence_refs[ledger]", "strong"
    # weak fallback: the measured ledger hash appears somewhere in the document
    if measured and measured in json.dumps(obj):
        return measured, "text_contains(measured)", "weak"
    return None, "none", "none"


def rows_from_value(v) -> set[int]:
    out: set[int] = set()
    if v is None:
        return out
    if isinstance(v, int):
        return {v}
    if isinstance(v, str):
        if NUMERIC_LIST.match(v):
            return {int(x) for x in re.split(r"[,; ]+", v.strip()) if x}
        return {int(m) for m in SRC_ROW.findall(v)}
    if isinstance(v, (list, tuple)):
        for x in v:
            if isinstance(x, int):
                out.add(x)
            elif isinstance(x, str):
                if NUMERIC_LIST.match(x):
                    out |= {int(y) for y in re.split(r"[,; ]+", x.strip()) if y}
                else:
                    out |= {int(m) for m in SRC_ROW.findall(x)}
            elif isinstance(x, dict):
                for k in ("row", "row_number", "idx", "index"):
                    if isinstance(x.get(k), int):
                        out.add(x[k])
                        break
                    if isinstance(x.get(k), str) and x[k].strip().isdigit():
                        out.add(int(x[k]))
                        break
                else:
                    for k in ("citation_id", "source_id", "id"):
                        if isinstance(x.get(k), str):
                            mm = SRC_ROW.search(x[k])
                            if mm:
                                out.add(int(mm.group(1)))
                                break
    return {r for r in out if r > 0}


def rows_from(obj: dict, root: Path) -> tuple[set[int], list[str]]:
    rows: set[int] = set()
    sources: list[str] = []
    sr = obj.get("sampling_rule")
    if isinstance(sr, dict):
        for k in ROW_KEYS:
            rr = rows_from_value(sr.get(k))
            if rr:
                rows |= rr
                sources.append(f"sampling_rule.{k}")
    for key in ("results", "checks", "rows_checked", "sampled_rows", "sample_rows", "sample_ids"):
        v = obj.get(key)
        if isinstance(v, list):
            rr = rows_from_value(v)
            if rr:
                rows |= rr
                sources.append(key)
    cand = []
    if isinstance(sr, dict):
        cand += [sr.get("sample_manifest"), sr.get("manifest")]
    for k in ("sample_manifest", "manifest", "manifest_path"):
        cand.append(obj.get(k))
    inputs = obj.get("inputs")
    if isinstance(inputs, dict):
        for k, v in inputs.items():
            if isinstance(v, dict) and "citation_audit" in str(k):
                cand.append(v.get("sample_manifest"))
    for c in cand:
        if not isinstance(c, str) or not c:
            continue
        p = (root / c).resolve()
        if root not in p.parents or not p.is_file():
            continue
        try:
            man = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(man, dict):
            for k in ROW_KEYS + ("rows_checked", "rows_frozen", "sample", "entries"):
                rr = rows_from_value(man.get(k))
                if rr:
                    rows |= rr
                    sources.append(f"{c}#{k}")
    return rows, sources


def classify(path: Path, obj: dict) -> tuple[str, bool, bool, str]:
    """Return (kind, superseded, draft, why)."""
    name = path.name.lower()
    kind = "check"
    if obj.get("artifact_type") == "l1_spotcheck":
        kind = "check"
    elif "spotcheck" in name:
        kind = "check"
    elif obj.get("node_id") == "L1" and obj.get("gate") == "G-LIT" and isinstance(obj.get("results"), list):
        kind = "check"
    elif AUX_NAME.search(name) or isinstance(obj.get("targets"), list) and not isinstance(obj.get("results"), list):
        kind = "auxiliary"
    else:
        kind = "other"
    sup, why = False, ""
    rel = str(path)
    if SUPERSEDED_PATH.search(rel):
        sup, why = True, "path_name"
    elif isinstance(obj.get("superseded_by"), str) and obj["superseded_by"]:
        sup, why = True, "field:superseded_by"
    elif isinstance(obj.get("status"), str) and "superseded" in obj["status"].lower():
        sup, why = True, "field:status"
    draft = bool(isinstance(obj.get("status"), str) and "draft" in obj["status"].lower())
    return kind, sup, draft, why


def collect(root: Path, measured: str) -> list[dict]:
    records = []
    paths = sorted(root.glob("artifacts/*/l1_spotcheck/**/*.json"))
    paths += sorted(root.glob("reviews/L1-spotcheck-*.json"))
    for p in paths:
        try:
            obj = json.loads(p.read_text())
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        rel = str(p.relative_to(root))
        kind, sup, draft, why = classify(p, obj)
        if kind == "other":
            continue
        rows, row_sources = rows_from(obj, root)
        pin, pin_where, strength = get_pin(obj, measured)
        results = obj.get("results") if isinstance(obj.get("results"), list) else []
        outcomes: dict[str, int] = {}
        for r in results:
            if isinstance(r, dict):
                v = str(r.get("verdict") or r.get("comparison") or r.get("overall") or "?")
                key = v.split(":")[0].strip().upper()[:12] or "?"
                outcomes[key] = outcomes.get(key, 0) + 1
        records.append({
            "path": rel, "sha256": sha256_file(p), "kind": kind, "actor": norm_actor(obj),
            "created_at": obj.get("created_at"), "verdict": obj.get("verdict") or obj.get("status"),
            "check_number": obj.get("check_number"), "superseded": sup, "superseded_why": why,
            "draft": draft, "pin": pin, "pin_where": pin_where, "pin_strength": strength,
            "bound": bool(pin and measured and (measured.startswith(pin) or pin.startswith(measured))),
            "rows": sorted(rows), "row_sources": row_sources, "rows_machine_readable": bool(rows),
            "n_results": len(results), "outcomes": outcomes,
        })
    return records


def analyze(records: list[dict], requirement: int = 3) -> dict:
    checks = [r for r in records if r["kind"] == "check"]
    bound = [r for r in checks if r["bound"] and not r["superseded"]]
    superseded = [r for r in checks if r["superseded"]]
    unbound = [r for r in checks if not r["bound"]]
    auxiliary = [r for r in records if r["kind"] == "auxiliary"]

    actors: dict[str, list[dict]] = {}
    for r in bound:
        actors.setdefault(r["actor"], []).append(r)

    readable = [r for r in bound if r["rows_machine_readable"]]
    overlap_pairs = []
    for i in range(len(readable)):
        for j in range(i + 1, len(readable)):
            a, b = readable[i], readable[j]
            shared = sorted(set(a["rows"]) & set(b["rows"]))
            if shared:
                union = set(a["rows"]) | set(b["rows"])
                overlap_pairs.append({
                    "a": a["path"], "a_actor": a["actor"], "b": b["path"], "b_actor": b["actor"],
                    "shared_rows": shared, "shared_count": len(shared),
                    "jaccard": round(len(shared) / max(1, len(union)), 3),
                    "intra_actor": a["actor"] == b["actor"],
                })

    # actor-level union rows and cross-actor overlap
    actor_rows = {a: sorted(set().union(*[set(r["rows"]) for r in rs])) for a, rs in actors.items()}
    cross_actor_overlaps = []
    names = sorted(actor_rows)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            shared = sorted(set(actor_rows[names[i]]) & set(actor_rows[names[j]]))
            if shared:
                cross_actor_overlaps.append({"a": names[i], "b": names[j], "shared_rows": shared})
    overlapped_actors = {n for p in cross_actor_overlaps for n in (p["a"], p["b"])}
    zero_overlap_actors = [a for a in names if a not in overlapped_actors and actor_rows[a]]

    instances = [r for r in readable for _ in r["rows"]]
    union_rows = sorted(set().union(*[set(r["rows"]) for r in readable])) if readable else []
    redundant = len(instances) - len(union_rows)
    uncovered_rows = [r for r in range(1, 98) if r not in set(union_rows)]

    return {
        "candidate_files": len(records),
        "check_files": len(checks),
        "auxiliary_files": len(auxiliary),
        "bound_checks": len(bound),
        "superseded_checks": len(superseded),
        "unbound_checks": len(unbound),
        "distinct_actors_bound": len(actors),
        "actors_with_readable_rows": sum(1 for a in actors if actor_rows.get(a)),
        "checks_with_readable_rows": len(readable),
        "union_rows_covered": len(union_rows),
        "uncovered_rows": uncovered_rows,
        "ledger_rows": 97,
        "coverage_fraction": round(len(union_rows) / 97, 3),
        "row_instances": len(instances),
        "redundant_row_instances": redundant,
        "zero_overlap_actors": zero_overlap_actors,
        "actor_level_overlaps": cross_actor_overlaps,
        "file_level_overlap_pairs": overlap_pairs,
        "requirement": requirement,
        "meets_requirement_distinct_actors": len(actors) >= requirement,
        "meets_requirement_bound_files": len(bound) >= requirement,
        "meets_requirement_zero_overlap_actors": len(zero_overlap_actors) >= requirement,
        "bound": [{k: r[k] for k in ("path", "sha256", "actor", "created_at", "verdict", "pin", "pin_where",
                                     "pin_strength", "rows", "row_sources", "rows_machine_readable", "outcomes")} for r in bound],
        "superseded": [{k: r[k] for k in ("path", "sha256", "actor", "verdict", "superseded_why", "pin", "rows")} for r in superseded],
        "unbound": [{k: r[k] for k in ("path", "sha256", "actor", "verdict", "pin", "pin_where", "rows")} for r in unbound],
        "auxiliary": [{k: r[k] for k in ("path", "sha256", "actor", "pin", "rows")} for r in auxiliary],
    }


def self_test() -> dict:
    def rec(path, actor, rows, pin, superseded=False, measured="a" * 64):
        return {"path": path, "sha256": "0" * 64, "kind": "check", "actor": actor, "created_at": None,
                "verdict": "accept", "check_number": None, "superseded": superseded,
                "superseded_why": "fixture" if superseded else "", "draft": False, "pin": pin,
                "pin_where": "fixture", "pin_strength": "strong",
                "bound": bool(pin and (measured.startswith(pin) or pin.startswith(measured))),
                "rows": sorted(rows), "row_sources": ["fixture"], "rows_machine_readable": bool(rows),
                "n_results": len(rows), "outcomes": {}}

    pin = "a" * 64
    cases = {
        "positive_shared_row": analyze([rec("f1", "A", {1, 2}, pin), rec("f2", "B", {2, 3}, pin)]),
        "negative_disjoint": analyze([rec("f1", "A", {1, 2}, pin), rec("f2", "B", {3, 4}, pin)]),
        "superseded_excluded": analyze([rec("f1", "A", {1, 2}, pin), rec("f2", "A", {1, 2}, pin, superseded=True)]),
        "unbound_excluded": analyze([rec("f1", "A", {1, 2}, pin), rec("f2", "B", {3, 4}, "b" * 64)]),
    }
    checks = {
        "positive_shared_row": len(cases["positive_shared_row"]["file_level_overlap_pairs"]) >= 1,
        "negative_disjoint": len(cases["negative_disjoint"]["file_level_overlap_pairs"]) == 0,
        "superseded_excluded": cases["superseded_excluded"]["distinct_actors_bound"] == 1
                               and cases["superseded_excluded"]["superseded_checks"] == 1,
        "unbound_excluded": cases["unbound_excluded"]["bound_checks"] == 1
                            and cases["unbound_excluded"]["unbound_checks"] == 1,
    }
    return {"verdict": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
            "observed": {k: {"overlap_pairs": len(v["file_level_overlap_pairs"]), "actors": v["distinct_actors_bound"],
                             "superseded": v["superseded_checks"], "bound": v["bound_checks"], "unbound": v["unbound_checks"]}
                         for k, v in cases.items()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if args.self_test:
        st = self_test()
        print(json.dumps(st, indent=2))
        return 0 if st["verdict"] == "PASS" else 1

    t0 = time.time()
    ledger = root / LEDGER_REL
    pin_start = sha256_file(ledger)
    with open(ledger, newline="") as fh:
        data_rows = sum(1 for _ in csv.DictReader(fh))
    controls = self_test()
    records = collect(root, pin_start)
    analysis = analyze(records)
    pin_end = sha256_file(ledger)

    findings = []
    findings.append(
        f"naive per-check-file count = {analysis['bound_checks']} bound checks; "
        f"distinct actors = {analysis['distinct_actors_bound']}; requirement {analysis['requirement']} "
        f"=> process-independence criterion " + ("MET" if analysis["meets_requirement_distinct_actors"] else "NOT MET") + "."
    )
    if analysis["superseded_checks"]:
        findings.append(
            "superseded/buggy revisions on disk that a file-glob count would include: "
            + ", ".join(r["path"] for r in analysis["superseded"]) + "."
        )
    if analysis["auxiliary_files"]:
        findings.append(
            "auxiliary (non-check) files on disk: "
            + ", ".join(r["path"] for r in analysis["auxiliary"]) + "."
        )
    no_rows = [r["path"] for r in analysis["bound"] if not r["rows_machine_readable"]]
    if no_rows:
        findings.append(
            "bound checks with no machine-readable row list (sample independence unverifiable from the "
            f"artifact alone): {no_rows}."
        )
    weak = [r["path"] for r in analysis["bound"] if r["pin_strength"] == "weak"]
    if weak:
        findings.append(f"bound only by weak text containment of the measured ledger hash (no explicit pin field): {weak}.")
    if analysis["actor_level_overlaps"]:
        worst = max(analysis["actor_level_overlaps"], key=lambda p: len(p["shared_rows"]))
        findings.append(
            f"cross-actor row overlap in {len(analysis['actor_level_overlaps'])} actor pair(s); largest: "
            f"{worst['a']} vs {worst['b']} share {len(worst['shared_rows'])} row(s) {worst['shared_rows'][:12]}"
            + (" ..." if len(worst["shared_rows"]) > 12 else "")
            + ". Overlap is redundancy of coverage, not dependence of verification."
        )
    findings.append(
        f"union coverage: {analysis['union_rows_covered']}/{analysis['ledger_rows']} ledger data rows "
        f"({analysis['coverage_fraction']:.1%}) sampled by checks with readable row lists; "
        f"{analysis['redundant_row_instances']} of {analysis['row_instances']} row instances are re-samples of an already sampled row; "
        f"uncovered rows: {analysis['uncovered_rows']}."
    )
    zero = analysis["zero_overlap_actors"]
    findings.append(
        f"actors whose readable sample is disjoint from every other actor: {zero if zero else 'none'} "
        f"(strict zero-overlap reading = {len(zero)}, requirement {analysis['requirement']})."
    )

    report = {
        "artifact_type": "l1_spotcheck_independence_census",
        "census_id": "W028-L1-INDEP-CENSUS-02",
        "actor": "worker-028",
        "reviewer": "worker-028",
        "created_at": now(),
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "question": ("How many L1 re-fetch spot checks bound to the measured ledger hash are independent by "
                     "process (distinct actor, non-superseded, own pin), and what is the sampled-row "
                     "coverage/overlap structure behind the controller's per-file count?"),
        "ledger": {"path": LEDGER_REL, "sha256_at_start": pin_start, "sha256_at_end": pin_end,
                   "stable_during_run": pin_start == pin_end, "data_rows": data_rows},
        "method": ("enumerate artifacts/*/l1_spotcheck/**/*.json and reviews/L1-spotcheck-*.json; classify "
                   "check vs auxiliary; explicit pin fields only with a weak measured-hash text fallback; "
                   "row sets from explicit lists, SRC-NNN result ids and referenced frozen manifests; prose "
                   "sampling rules are never parsed."),
        "controls": controls,
        "counts": {k: analysis[k] for k in (
            "candidate_files", "check_files", "auxiliary_files", "bound_checks", "superseded_checks",
            "unbound_checks", "distinct_actors_bound", "actors_with_readable_rows", "checks_with_readable_rows",
            "union_rows_covered", "uncovered_rows", "ledger_rows", "coverage_fraction", "row_instances",
            "redundant_row_instances", "requirement", "meets_requirement_distinct_actors",
            "meets_requirement_bound_files", "meets_requirement_zero_overlap_actors")},
        "distinct_actors": sorted({r["actor"] for r in analysis["bound"]}),
        "zero_overlap_actors": zero,
        "actor_level_overlaps": analysis["actor_level_overlaps"],
        "file_level_overlap_pairs": analysis["file_level_overlap_pairs"],
        "bound_checks": analysis["bound"],
        "superseded_checks": analysis["superseded"],
        "unbound_checks": analysis["unbound"],
        "auxiliary_files": analysis["auxiliary"],
        "evidence_refs": [f"{LEDGER_REL}#{pin_start[:12]}", "research_map/research_map.json#controller_gate_audit.G-LIT"],
        "findings": findings,
        "falsifiers": [
            f"ledger/citation_audit.csv no longer hashes to {pin_start[:12]} (all bindings and counts void);",
            "a spot-check artifact on disk that this census did not enumerate;",
            "a check judged disjoint here is shown to share a ledger row with another check;",
            "a declared pin is shown not to match the ledger bytes actually fetched.",
        ],
        "not_claimed": [
            "No gate verdict. This is a measurement of independence and coverage structure, not an acceptance of G-LIT.",
            "No re-fetch: no citation is verified against a primary source here; the checks' own fetch evidence is taken as declared.",
            "Row extraction is limited to machine-readable fields; checks whose sampling rule is prose-only are counted for process independence but excluded from coverage/overlap.",
            "Sample-row overlap is reported as redundancy of coverage, not as dependence between verification processes.",
        ],
        "runtime_seconds": round(time.time() - t0, 3),
    }
    out = root / OUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("census_id", "created_at", "counts", "distinct_actors",
                                             "zero_overlap_actors", "findings", "controls")}, indent=2, sort_keys=False))
    print("artifact:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
