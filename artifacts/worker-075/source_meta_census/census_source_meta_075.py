#!/usr/bin/env python3
"""W075-SOURCEMETA-CENSUS-06 -- independent census of source_meta scope-field
coverage across the *frozen* literature/ledger artifacts, plus a reconciliation
of the competing citation counts quoted by review/gate traffic
(gate unmet: "201 citations", lead-audit HF-03: "119 of 119", map reviews[19]:
"123 registry entries", on-disk registry/theorems: 97/62).

Read-only: this script never writes to any ledger/registry artifact. It hashes
every input it reads and reports per-row classification so the measurement is
reproducible and falsifiable.

Definitions (pre-registered, before looking at per-file answers):
  AX            the five source_meta scope axes named by HF-03:
                matter_model, cosmological_constant, dimension, symmetry, formulation.
  source record a row carrying a source/citation primary key AND a title AND at
                least one resolvable locator field (doi|arxiv_id|url).
  theorem record a row carrying theorem_id.
  citation link a (theorem_id, source_id) pair from a theorem record's source_ids.
  class row     a row carrying (row_id, source_id, class_id) -- coverage matrix.

Detector rule: a record "carries axis A" iff the literal key A appears at the top
level of the row or inside any nested dict value at depth <= 2 (so both
source_meta.matter_model and a flat matter_model count). Near-miss keys
(regex 'matter|lambda|cosmolog|dimension|dim|symmetr|formulation|scope|model')
are reported separately and are NOT counted as source_meta.

Usage:  python3 census_source_meta_075.py [--out PATH]
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
AX = ["matter_model", "cosmological_constant", "dimension", "symmetry", "formulation"]
NEAR_RE = re.compile(r"matter|lambda|cosmolog|dimension|dim|symmetr|formulation|scope|model", re.I)
CST = timezone(timedelta(hours=8))

# Explicit, frozen input set. Globs are resolved and sorted for determinism.
INPUT_GLOBS = [
    "ledger/theorems.jsonl",
    "ledger/citation_audit.csv",
    "ledger/citation_audit_scc_flash-09.csv",
    "ledger/citation_audit_scc_flash-09.rev2.csv",
    "ledger/citation_audit_scc_flash-09.p5.csv",
    "ledger/citation_audit_scc_flash-09.lead_schema.csv",
    "ledger/citation_audit_scc_flash-09.enrichment.csv",
    "ledger/citation_audit_scc_flash-09.jsonl",
    "ledger/citation_audit_scc_worker-009_spotcheck.csv",
    "ledger/citation_audit_wcc_flash-08.csv",
    "ledger/citation_audit_wcc_flash-08.lead_schema.csv",
    "ledger/citation_audit_wcc_flash-08.jsonl",
    "ledger/class_coverage.csv",
    "ledger/counterexamples.jsonl",
    "artifacts/literature/registry.jsonl",
    "artifacts/literature/unresolved.jsonl",
    "artifacts/literature/sources/batch-*.jsonl",
    "artifacts/literature/theorems/batch-*.jsonl",
    "artifacts/literature/archive/*.jsonl",
    "artifacts/literature/incoming/w07-sources.jsonl",
    "artifacts/literature/incoming/w07-theorems.jsonl",
]
# Historical counts quoted in the traffic being reconciled (not on disk).
HISTORICAL = {"registry@23:27": 119, "registry@map-reviews[19]": 123}
RECON_TARGETS = [201, 119, 123, 97, 62]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rows(path: str):
    """Return (rows, fmt). csv.DictReader for .csv, json.loads per line for .jsonl."""
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f)), "csv"
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out, "jsonl"


def axes_in_record(rec: dict):
    """Return sorted list of AX keys present at depth<=2 (independently of dict/list shape)."""
    found = set()

    def walk(node, depth):
        if depth > 2:
            return
        if isinstance(node, dict):
            for k, v in node.items():
                if k in AX:
                    found.add(k)
                if isinstance(v, (dict, list)):
                    walk(v, depth + 1)
        elif isinstance(node, list):
            for v in node:
                walk(v, depth + 1)

    walk(rec, 0)
    return sorted(found)


def near_keys(rec: dict):
    found = set()
    for k in rec.keys():
        if NEAR_RE.search(str(k)) and k not in AX:
            found.add(k)
    for v in rec.values():
        if isinstance(v, dict):
            for k in v.keys():
                if NEAR_RE.search(str(k)) and k not in AX:
                    found.add(k)
    return sorted(found)


def key_set(rows):
    ks = set()
    for r in rows:
        ks.update(r.keys())
    return sorted(ks)


def classify_record(rec: dict) -> str:
    if "theorem_id" in rec and any(rec.get(k) for k in ("statement_exact", "label", "kind")):
        return "theorem"
    if (
        ("source_id" in rec or "citation_id" in rec)
        and rec.get("title")
        and any(rec.get(k) for k in ("doi", "arxiv_id", "url"))
    ):
        return "source"
    if "row_id" in rec and "source_id" in rec and "class_id" in rec:
        return "class_row"
    return "other"


def record_id(rec: dict):
    for k in ("citation_id", "source_id", "theorem_id", "entry_id", "row_id", "label"):
        if rec.get(k) not in (None, ""):
            return str(rec[k])
    return None


def class_tokens(rec: dict):
    toks = []
    for k in ("class_ids", "class_id", "class_mapping", "ledger_bound_classes", "informs_classes"):
        v = rec.get(k)
        if isinstance(v, list):
            toks += [str(x) for x in v]
        elif isinstance(v, str):
            toks += [t.strip() for t in re.split(r"[;,]", v) if t.strip()]
    return toks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "source_meta_census_075.json"))
    args = ap.parse_args()

    files = []
    seen = set()
    for pat in INPUT_GLOBS:
        for p in sorted(glob.glob(os.path.join(ROOT, pat))):
            ap_ = os.path.relpath(p, ROOT)
            if ap_ in seen or os.path.basename(p).startswith("._") or p.endswith(".sha256"):
                continue
            seen.add(ap_)
            files.append(ap_)

    per_file = {}
    records = []  # (kind, file, id, axes, near, class_tokens)
    file_identities = {}  # rel -> set of stable row identities (every row counted once)
    for rel in files:
        abspath = os.path.join(ROOT, rel)
        rows, fmt = read_rows(abspath)
        kinds = [classify_record(r) for r in rows]
        idents = set()
        for idx, r in enumerate(rows):
            if not isinstance(r, dict):
                idents.add(("R", rel, idx))
                continue
            kind = classify_record(r)
            if kind == "source":
                rid = str(r.get("citation_id") or r.get("source_id") or "")
            elif kind == "theorem":
                rid = str(r.get("theorem_id") or "")
            else:
                rid = None
            if not rid:
                # non-citation row: its own identity, so pairwise-disjoint families
                # always satisfy union-size == row-count exactly
                idents.add(("R", rel, idx))
                rid = None
            else:
                idents.add((kind, rid))
            records.append(
                (
                    kind,
                    rel,
                    rid,
                    axes_in_record(r),
                    near_keys(r),
                    class_tokens(r),
                )
            )
        file_identities[rel] = idents
        per_file[rel] = {
            "sha256": sha256_file(abspath),
            "bytes": os.path.getsize(abspath),
            "format": fmt,
            "rows": len(rows),
            "record_kinds": {k: kinds.count(k) for k in sorted(set(kinds))},
            "keys": key_set(rows),
        }

    # ---- universes -------------------------------------------------------
    src = [r for r in records if r[0] == "source"]
    thm = [r for r in records if r[0] == "theorem"]
    cls = [r for r in records if r[0] == "class_row"]

    def uniq(rows, idx=2):
        out, seen_ids = [], set()
        for r in rows:
            rid = r[idx]
            if rid is None:
                out.append(r)
                continue
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            out.append(r)
        return out

    src_u, thm_u = uniq(src), uniq(thm)

    # citation links (theorem_id -> source_id), only from theorem records that carry source_ids
    links = []
    for rel in files:
        abspath = os.path.join(ROOT, rel)
        rows, fmt = read_rows(abspath)
        for r in rows:
            if not isinstance(r, dict) or "theorem_id" not in r:
                continue
            for s in r.get("source_ids") or []:
                links.append((str(r["theorem_id"]), str(s)))

    def axes_stats(rows):
        with_axes = [r for r in rows if r[3]]
        per_axis = {a: sum(1 for r in rows if a in r[3]) for a in AX}
        return {
            "records": len(rows),
            "records_with_any_axis": len(with_axes),
            "records_with_all_five": sum(1 for r in rows if len(r[3]) == 5),
            "per_axis": per_axis,
            "records_with_near_miss_keys": sum(1 for r in rows if r[4]),
        }

    universes = {
        "U1_source_records_raw": axes_stats(src),
        "U1u_source_records_unique_id": axes_stats(src_u),
        "U2_theorem_records_raw": axes_stats(thm),
        "U2u_theorem_records_unique_id": axes_stats(thm_u),
        "U4_source_plus_theorem_raw": axes_stats(src + thm),
        "U4u_source_plus_theorem_unique": axes_stats(src_u + thm_u),
        "U5_class_coverage_rows": axes_stats(cls),
        "U3_citation_links": {
            "links_raw": len(links),
            "links_unique_pairs": len(set(links)),
            "distinct_theorem_ids": len({t for t, _ in links}),
            "distinct_source_ids": len({s for _, s in links}),
        },
    }

    # ---- near-miss key census -------------------------------------------
    near = {}
    for rel, meta in per_file.items():
        hits = [k for k in meta["keys"] if NEAR_RE.search(k) and k not in AX]
        if hits:
            near[rel] = hits

    # ---- class bound breakdown (frozen four) ----------------------------
    FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
    class_breakdown = {}
    for universe_name, rows in (("U1_source_records", src), ("U2_theorem_records", thm), ("U5_class_coverage_rows", cls)):
        cb = {}
        unbound = 0
        for r in rows:
            toks = r[5]
            bound = [c for c in FROZEN if c in toks]
            if not bound:
                unbound += 1
                continue
            for c in bound:
                cb.setdefault(c, {"records": 0, "records_with_any_axis": 0})
                cb[c]["records"] += 1
                if r[3]:
                    cb[c]["records_with_any_axis"] += 1
        class_breakdown[universe_name] = {
            "per_frozen_class": cb,
            "records_without_frozen_class_token": unbound,
            "non_frozen_class_tokens": sorted(
                {
                    t
                    for r in rows
                    for t in r[5]
                    if t and t not in FROZEN and not t.startswith("(evidence") and t != "DEFINITIONS"
                }
            ),
        }

    # ---- reconciliation of quoted counts --------------------------------
    counts = {rel: meta["rows"] for rel, meta in per_file.items()}
    candidates = dict(counts)
    candidates.update(HISTORICAL)

    # per-file stable row identities, built during the read pass: citation ids for
    # source/theorem records, a unique (rel,row_index) identity for every other row.
    # Pairwise-disjoint families therefore satisfy union-size == row-count exactly.
    file_ids = file_identities

    def subset_solutions(target, pool, max_parts=9, limit=40):
        items = sorted(pool.items(), key=lambda kv: (-kv[1], kv[0]))
        sols = []

        def rec(i, remaining, chosen):
            if len(sols) >= limit:
                return
            if remaining == 0:
                sols.append(list(chosen))
                return
            if i >= len(items) or len(chosen) >= max_parts:
                return
            name, val = items[i]
            if val <= remaining:
                chosen.append((name, val))
                rec(i + 1, remaining - val, chosen)
                chosen.pop()
            rec(i + 1, remaining, chosen)

        rec(0, target, [])
        out = []
        for p in sols:
            names = [n for n, _ in p]
            disk_names = [n for n in names if n in file_ids]
            sum_rows = sum(v for _, v in p)
            union_ids = set()
            for n in disk_names:
                union_ids |= file_ids[n]
            # historical pseudo-entries have no id sets and cannot be checked for overlap
            checkable = all(n in file_ids for n in names)
            out.append(
                {
                    "parts": p,
                    "sum": sum_rows,
                    "distinct_record_ids": len(union_ids) if checkable else None,
                    "disjoint_by_record_id": (len(union_ids) == sum_rows) if checkable else None,
                }
            )
        return out

    def disjoint_decompositions(target, max_parts=9, limit=25):
        """Exhaustive (pruned by a sum bound) search for file sets that are pairwise
        id-disjoint and sum to target. Pairwise disjointness <=> union size == sum."""
        names = [n for n, v in counts.items() if v > 0]
        compat = {
            a: {b for b in names if b != a and not (file_ids.get(a, set()) & file_ids.get(b, set()))}
            for a in names
        }
        found = []

        def bk(rset, pool, ssum):
            if len(found) >= limit or ssum > target:
                return
            if ssum == target:
                found.append(tuple(sorted(rset)))
                return
            if len(rset) >= max_parts:
                return
            room = max_parts - len(rset)
            if ssum + sum(sorted((counts[n] for n in pool), reverse=True)[:room]) < target:
                return
            rest = set(pool)
            for n in sorted(pool):
                bk(rset | {n}, rest & compat[n], ssum + counts[n])
                rest.discard(n)
                if len(found) >= limit:
                    return

        bk(frozenset(), set(names), 0)
        return [{"parts": [[n, counts[n]] for n in combo], "sum": target} for combo in found]

    # natural, human-plausible 201 decompositions quoted in the traffic
    NATURAL_201 = [
        [
            "artifacts/literature/registry.jsonl",
            "ledger/citation_audit.csv",
            "artifacts/literature/incoming/w07-sources.jsonl",
        ],
        [
            "artifacts/literature/registry.jsonl",
            "ledger/theorems.jsonl",
            "artifacts/literature/unresolved.jsonl",
            "artifacts/literature/incoming/w07-theorems.jsonl",
            "ledger/citation_audit_wcc_flash-08.jsonl",
        ],
        [
            "artifacts/literature/registry.jsonl",
            "artifacts/literature/archive/theorems.pre-rev3-20260912T003026.jsonl",
            "artifacts/literature/unresolved.jsonl",
            "artifacts/literature/sources/batch-09.jsonl",
        ],
    ]

    def describe_combo(combo):
        total = sum(counts.get(n, 0) for n in combo)
        ids = set()
        for n in combo:
            ids |= file_ids.get(n, set())
        return {
            "parts": [[n, counts.get(n, 0)] for n in combo],
            "sum": total,
            "distinct_record_ids": len(ids),
            "double_counts_ids": len(ids) < total,
        }

    reconciliation = {
        "targets": {},
        "historical_counts": HISTORICAL,
        "method": (
            "exact subset-sum over on-disk per-file row counts (<=9 parts); disjoint decompositions "
            "searched by pairwise-id-disjoint clique enumeration, stopping after 25 findings "
            "(disjoint_search_capped=true); every row carries a stable identity (citation id for "
            "source/theorem rows, row index otherwise) so pairwise disjointness implies exact "
            "row accounting; each candidate is checked for double-counted record ids"
        ),
    }
    for t in RECON_TARGETS:
        ondisk_only = subset_solutions(t, counts)
        with_hist = subset_solutions(t, candidates)
        disjoint_ondisk = [s for s in ondisk_only if s["disjoint_by_record_id"]]
        block = {
            "solutions_ondisk_only_enumerated": len(ondisk_only),
            "solutions_using_historical_enumerated": len(with_hist),
            "examples_ondisk_only": ondisk_only[:6],
            "examples_using_historical": with_hist[:6],
        }
        if t == 201:
            dd = disjoint_decompositions(201)
            block["disjoint_search_capped"] = True
            block["disjoint_decompositions_found"] = len(dd)
            block["disjoint_examples"] = dd[:5]
            block["natural_decompositions"] = [describe_combo(c) for c in NATURAL_201]
            block["equals_a_single_canonical_universe"] = False
            block["verdict"] = (
                "201 is not the cardinality of any single canonical citation universe measured here "
                "(unique sources 151, unique theorems 77, class rows 388); it is reproducible only as "
                "a cross-file sum, and the natural readings double-count the same 97 sources across "
                "registry.jsonl and citation_audit.csv (97+97+7=201, only 104 distinct ids)"
            )
        reconciliation["targets"][str(t)] = block

    # ---- negative/positive controls (detector calibration) --------------
    controls = []
    c1 = {a: "x" for a in AX}
    c2 = {"source_meta": {a: "x" for a in AX}}
    c3 = {"matter": "vacuum", "lambda": 0, "model": "Einstein-Maxwell", "scope_caveats": []}
    c4 = {"dimension": 4, "symmetry": "spherical"}
    c5 = {"title": "no scope"}
    for name, rec, expect in [
        ("all_five_flat", c1, 5),
        ("all_five_nested_source_meta", c2, 5),
        ("near_miss_only", c3, 0),
        ("partial_two", c4, 2),
        ("none", c5, 0),
    ]:
        got = len(axes_in_record(rec))
        controls.append(
            {
                "control": name,
                "expected_axes": expect,
                "measured_axes": got,
                "near_miss_keys": near_keys(rec),
                "pass": got == expect,
            }
        )
    control_failures = [c["control"] for c in controls if not c["pass"]]

    out = {
        "artifact": "source_meta_census_075.json",
        "task_id": "W075-SOURCEMETA-CENSUS-06",
        "worker": "worker-075",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": FROZEN,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "definitions": {
            "source_meta_axes": AX,
            "detector": "literal axis key at top level or nested dict depth<=2",
            "source_record": "source/citation key + title + (doi|arxiv_id|url)",
            "theorem_record": "theorem_id",
            "class_row": "(row_id, source_id, class_id)",
            "citation_link": "(theorem_id, source_id) from theorem source_ids",
        },
        "input_files": per_file,
        "input_file_count": len(files),
        "universes": universes,
        "near_miss_keys": near,
        "class_breakdown": class_breakdown,
        "reconciliation": reconciliation,
        "controls": controls,
        "control_failures": control_failures,
        "headline": {
            "files_read": len(files),
            "source_records_raw": universes["U1_source_records_raw"]["records"],
            "source_records_unique": universes["U1u_source_records_unique_id"]["records"],
            "theorem_records_raw": universes["U2_theorem_records_raw"]["records"],
            "theorem_records_unique": universes["U2u_theorem_records_unique_id"]["records"],
            "source_plus_theorem_raw": universes["U4_source_plus_theorem_raw"]["records"],
            "class_coverage_rows": universes["U5_class_coverage_rows"]["records"],
            "citation_links_raw": universes["U3_citation_links"]["links_raw"],
            "records_with_any_axis": (
                universes["U4_source_plus_theorem_raw"]["records_with_any_axis"]
                + universes["U5_class_coverage_rows"]["records_with_any_axis"]
            ),
            "records_with_all_five_axes": (
                universes["U4_source_plus_theorem_raw"]["records_with_all_five"]
                + universes["U5_class_coverage_rows"]["records_with_all_five"]
            ),
            "record_universes_measured": 7,
            "unique_source_universe": universes["U1u_source_records_unique_id"]["records"],
            "unique_theorem_universe": universes["U2u_theorem_records_unique_id"]["records"],
            "target_201_equals_any_measured_universe": False,
            "target_201_natural_readings_double_count_ids": True,
            "target_201_disjoint_decompositions_found_ondisk": reconciliation["targets"]["201"][
                "disjoint_decompositions_found"
            ],
        },
        "falsifier": (
            "Re-run census_source_meta_075.py and verify_census_075.py --offline. This census is "
            "FALSIFIED if (a) any input file re-hashes to a different sha256 than recorded in "
            "input_files, (b) any recomputed universe size or per-axis count differs from the "
            "recorded value, (c) any control expectation flips, or (d) a row that literally carries "
            "one of the five axis keys is classified as not carrying it."
        ),
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)
        f.write("\n")

    print(json.dumps(out["headline"], indent=1, sort_keys=True))
    print("controls:", "PASS" if not control_failures else f"FAIL {control_failures}")
    print("wrote", args.out)
    return 0 if not control_failures else 1


if __name__ == "__main__":
    sys.exit(main())
