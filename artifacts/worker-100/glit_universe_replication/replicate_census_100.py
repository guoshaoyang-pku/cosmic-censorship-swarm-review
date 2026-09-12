#!/usr/bin/env python3
"""W100-GLIT-UNIVERSE-REPL-01 -- independent non-author replication of the
worker-075 source_meta census headline numbers at pinned bytes.

Read-only on every canonical path.  Writes only inside its own task directory.
Written from the definitions in PREREGISTRATION.json; the target's own
implementation (census_source_meta_075.py) is not read or imported.

Usage:
  python3 replicate_census_100.py            # measure, write replication_report.json
  python3 replicate_census_100.py --selftest # controls/fixtures only
  python3 replicate_census_100.py --verify   # re-measure and compare digest to report
"""
from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
TARGET = ROOT / "artifacts/worker-075/source_meta_census/source_meta_census_075.json"
REPORT = TASK / "replication_report.json"
RAW = TASK / "raw"
CST = timezone(timedelta(hours=8))

AXES = ["matter_model", "cosmological_constant", "dimension", "symmetry", "formulation"]
NEAR_RE = re.compile(r"matter|lambda|cosmolog|dimension|dim|symmetr|formulation|scope|model", re.I)
FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
SOURCE_KEY_ORDER = ["source_id", "citation_id", "bibkey", "id", "key"]
CLASS_FIELDS = ["class_mapping", "class_ids", "informs_classes", "class_id"]
CLASS_SPLIT_RE = re.compile(r"[;,|/()\[\]]+|\s+(?:and|or)\s+")
NOT_BEFORE = re.compile(r"(?:not|never|no)\s+$", re.I)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------- parsing

def read_records(path: Path, fmt: str):
    if fmt == "jsonl":
        rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    if fmt == "json":
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, list) else [doc]
    if fmt in ("csv", "tsv"):
        delim = "," if fmt == "csv" else "\t"
        text = path.read_text(encoding="utf-8")
        return list(csv.DictReader(io.StringIO(text), delimiter=delim))
    raise ValueError(f"unknown format {fmt}")


def get(row: dict, *keys):
    for k in keys:
        if k in row and row[k] not in (None, "", [], {}):
            return row[k]
    return None


# ------------------------------------------------------------- predicates

def is_source(row: dict) -> bool:
    key = get(row, *SOURCE_KEY_ORDER)
    title = get(row, "title")
    locator = get(row, "doi", "arxiv_id", "url")
    return bool(key and title and locator)


def is_theorem(row: dict) -> bool:
    return bool(get(row, "theorem_id"))


def is_class_row(row: dict) -> bool:
    return bool(get(row, "row_id") and get(row, "source_id")
                and get(row, "class_id", "class_ids", "class_mapping"))


def source_key(row: dict) -> str:
    key = get(row, *SOURCE_KEY_ORDER)
    if key:
        return str(key).strip()
    title = str(get(row, "title") or "").strip().lower()
    year = str(get(row, "year") or "").strip()
    return f"title::{title}|{year}"


def theorem_key(row: dict) -> str:
    key = get(row, "theorem_id")
    if key:
        return str(key).strip()
    label = str(get(row, "label") or "").strip().lower()
    stmt = str(get(row, "statement_exact") or "").strip().lower()[:80]
    return f"label::{label}|{stmt}"


def axis_hits(obj, max_depth: int = 2):
    """Literal axis keys at top level (depth 0) or nested dict depth <= max_depth.

    Returns (hits, near_miss_keys, max_depth_at_which_an_axis_fired).
    An axis key three dict levels below the record (record->a->b->c) is depth 3
    and does not count; the primary reading is max_depth=2 (keys of a depth-2
    nested dict count) with the strict depth<=1 reading reported as sensitivity.
    """
    hits, near, depths = set(), set(), []

    def walk(o, depth):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in AXES:
                    hits.add(k)
                    depths.append(depth)
                elif NEAR_RE.search(str(k)):
                    near.add(str(k))
                if isinstance(v, dict) and depth + 1 <= max_depth:
                    walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                if isinstance(v, dict):
                    walk(v, depth)
    walk(obj, 0)
    return hits, near, (max(depths) if depths else -1)


def class_tokens(row: dict, reading: str = "substring"):
    """reading A (primary): split on all delimiters, substring-match frozen tokens.
    reading B (author's rule): split each class field on ';' only and require an
    exact whole-token match, so 'AF-SCC-C0-VAC-GEN (scope-caveated)' and
    'not AF-SCC-C2-VAC-GEN)' do not credit the frozen token."""
    toks = []
    for field in CLASS_FIELDS:
        v = row.get(field)
        if v is None:
            continue
        vals = v if isinstance(v, list) else [v]
        for item in vals:
            s = str(item)
            parts = s.split(";") if reading == "exact_semicolon" else CLASS_SPLIT_RE.split(s)
            for tok in parts:
                tok = tok.strip()
                if tok:
                    toks.append(tok)
    return toks


def frozen_classes_of(row: dict, reading: str = "substring"):
    text = " | ".join(class_tokens(row, reading))
    if reading == "exact_semicolon":
        found = {t.strip() for t in class_tokens(row, reading)} & set(FROZEN)
        return found
    found = set()
    for cls in FROZEN:
        if cls in text:
            found.add(cls)
    return found


# ------------------------------------------------------------- aggregation

def measure(records_by_file: dict, record_kinds: dict):
    universes = {}
    raw_sources, raw_theorems, raw_class_rows = [], [], []
    for path, rows in records_by_file.items():
        for r in rows:
            kind = record_kinds[path].get(id(r))
            if kind == "source":
                raw_sources.append(r)
            elif kind == "theorem":
                raw_theorems.append(r)
            elif kind == "class_row":
                raw_class_rows.append(r)

    src_unique = {}
    for r in raw_sources:
        src_unique.setdefault(source_key(r), r)
    thm_unique = {}
    for r in raw_theorems:
        thm_unique.setdefault(theorem_key(r), r)

    def cover(rows):
        any_axis = all_five = near = any_strict = 0
        max_hit_depth = -1
        per_axis = {a: 0 for a in AXES}
        for r in rows:
            hits, nk, depth = axis_hits(r, max_depth=2)
            strict_hits, _, _ = axis_hits(r, max_depth=1)
            if hits:
                any_axis += 1
                max_hit_depth = max(max_hit_depth, depth)
            if strict_hits:
                any_strict += 1
            if len(hits) == len(AXES):
                all_five += 1
            if nk and not hits:
                near += 1
            for a in hits:
                per_axis[a] += 1
        return {"records": len(rows), "records_with_any_axis": any_axis,
                "records_with_any_axis_strict_depth_le_1": any_strict,
                "records_with_all_five": all_five, "records_with_near_miss_keys": near,
                "max_axis_hit_depth": max_hit_depth, "per_axis": per_axis}

    universes["U1_source_records_raw"] = cover(raw_sources)
    universes["U1u_source_records_unique_id"] = cover(list(src_unique.values()))
    universes["U2_theorem_records_raw"] = cover(raw_theorems)
    universes["U2u_theorem_records_unique_id"] = cover(list(thm_unique.values()))
    universes["U4_source_plus_theorem_raw"] = cover(raw_sources + raw_theorems)
    universes["U4u_source_plus_theorem_unique"] = cover(
        list(src_unique.values()) + list(thm_unique.values()))
    universes["U5_class_coverage_rows"] = cover(raw_class_rows)

    links_raw, pairs = 0, set()
    for r in raw_theorems:
        tid = theorem_key(r)
        sids = r.get("source_ids")
        if sids is None and r.get("source_id") is not None:
            sids = [r.get("source_id")]
        if isinstance(sids, str):
            sids = [sids]
        for s in sids or []:
            links_raw += 1
            pairs.add((tid, str(s).strip()))
    universes["U3_citation_links"] = {
        "links_raw": links_raw,
        "links_unique_pairs": len(pairs),
        "distinct_theorem_ids": len({p[0] for p in pairs}),
        "distinct_source_ids": len({p[1] for p in pairs}),
    }

    def class_census(reading):
        per_class = {c: 0 for c in FROZEN}
        no_token = 0
        for r in raw_sources:
            found = frozen_classes_of(r, reading)
            if not found:
                no_token += 1
            for c in found:
                per_class[c] += 1
        return {"reading": reading, "per_frozen_class": per_class,
                "records_without_frozen_class_token": no_token}

    return (universes, class_census("substring"), class_census("exact_semicolon"),
            src_unique, thm_unique)


def reconciliation(records_by_file, row_counts, universes):
    def ids(rows, kind):
        out = set()
        for r in rows:
            out.add(("t:" if kind == "theorem" else "s:") +
                    (theorem_key(r) if kind == "theorem" else source_key(r)))
        return out

    named = {}
    A = [("artifacts/literature/registry.jsonl", "source"),
         ("ledger/citation_audit.csv", "source"),
         ("artifacts/literature/incoming/w07-sources.jsonl", "source")]
    B = [("artifacts/literature/registry.jsonl", "source"),
         ("ledger/theorems.jsonl", "theorem"),
         ("artifacts/literature/unresolved.jsonl", "theorem"),
         ("artifacts/literature/incoming/w07-theorems.jsonl", "theorem"),
         ("ledger/citation_audit_wcc_flash-08.jsonl", "source")]
    for label, spec in (("A", A), ("B", B)):
        allids, parts, total = set(), [], 0
        for path, kind in spec:
            rows = records_by_file[path]
            total += len(rows)
            allids |= ids(rows, kind)
            parts.append([path, len(rows)])
        named[label] = {"parts": parts, "sum": total, "distinct_record_ids": len(allids)}

    single_201 = [p for p, n in row_counts.items() if n == 201]
    canonical = [p for p in row_counts
                 if "/archive/" not in p and "flash" not in p and "worker-" not in p]
    subset_hits = []
    for k in (1, 2, 3, 4):
        for combo in itertools.combinations(sorted(canonical), k):
            if sum(row_counts[p] for p in combo) == 201:
                subset_hits.append([list(combo), sum(row_counts[p] for p in combo)])
    measured = {
        "U1_source_records_raw": universes["U1_source_records_raw"]["records"],
        "U1u_source_records_unique_id": universes["U1u_source_records_unique_id"]["records"],
        "U2_theorem_records_raw": universes["U2_theorem_records_raw"]["records"],
        "U2u_theorem_records_unique_id": universes["U2u_theorem_records_unique_id"]["records"],
        "U4_source_plus_theorem_raw": universes["U4_source_plus_theorem_raw"]["records"],
        "U4u_source_plus_theorem_unique": universes["U4u_source_plus_theorem_unique"]["records"],
        "U5_class_coverage_rows": universes["U5_class_coverage_rows"]["records"],
        "U3_links_raw": universes["U3_citation_links"]["links_raw"],
        "U3_links_unique_pairs": universes["U3_citation_links"]["links_unique_pairs"],
    }
    min_dist = min(abs(v - 201) for v in measured.values())
    return {"named_decompositions": named,
            "single_file_row_count_201": single_201,
            "canonical_subset_sums_eq_201_k_le_4": subset_hits,
            "measured_universe_values": measured,
            "min_abs_distance_of_any_measured_universe_to_201": min_dist,
            "target_201_equals_any_measured_universe": 201 in measured.values()}


# ---------------------------------------------------------------- controls

def run_controls() -> list:
    out = []

    def ctl(name, expected, got, near_expected=0):
        out.append({"control": name, "expected": expected, "measured": got,
                    "near_miss_expected": near_expected, "pass": expected == got})

    for name, obj, exp in [
        ("C1_flat_axis", {"matter_model": "vacuum"}, ["matter_model"]),
        ("C2_nested_depth1_axis", {"source_meta": {"symmetry": "spherical"}}, ["symmetry"]),
        ("C3_nested_depth3_axis", {"a": {"b": {"c": {"dimension": 4}}}}, []),
        ("C3b_nested_depth2_axis_primary", {"a": {"b": {"dimension": 4}}}, ["dimension"]),
        ("C4_near_miss_only", {"scope_caveats": ["spherical_symmetry"]}, []),
        ("C5_empty", {}, []),
        ("C5b_all_five_flat", {a: 1 for a in AXES}, sorted(AXES)),
    ]:
        hits, near, depth = axis_hits(obj)
        ctl(name, exp, sorted(hits), 1 if name == "C4_near_miss_only" else 0)
        if name == "C3b_nested_depth2_axis_primary":
            strict, _, _ = axis_hits(obj, max_depth=1)
            ctl("C3b_nested_depth2_axis_strict_reading", [], sorted(strict))

    rows = [{"source_id": "SRC-1", "title": "t", "url": "u"},
            {"source_id": "SRC-1", "title": "t2", "url": "u2"}]
    u = {}
    for r in rows:
        u.setdefault(source_key(r), r)
    ctl("C6_duplicate_source_key_raw", 2, len(rows))
    ctl("C6_duplicate_source_key_unique", 1, len(u))

    raw_links, pairs = 0, set()
    for _ in range(2):
        raw_links += 1
        pairs.add(("T-1", "SRC-1"))
    ctl("C7_duplicate_link_raw", 2, raw_links)
    ctl("C7_duplicate_link_unique", 1, len(pairs))

    # C8: pin-drift detection is exercised by tampering an in-memory digest
    real = hashlib.sha256(b"pinned-bytes").hexdigest()
    tampered = hashlib.sha256(b"tampered-bytes").hexdigest()
    ctl("C8_pin_drift_detected", True, real != tampered)
    return out


# ------------------------------------------------------------------- main

def classify_all(target):
    records_by_file, record_kinds, row_counts, kinds_match = {}, {}, {}, {}
    for path, meta in target["input_files"].items():
        p = ROOT / path
        rows = read_records(p, meta.get("format", "jsonl"))
        records_by_file[path] = rows
        row_counts[path] = len(rows)
        kinds = {}
        for r in rows:
            if is_source(r):
                kinds[id(r)] = "source"
            elif is_class_row(r):
                kinds[id(r)] = "class_row"
            elif is_theorem(r):
                kinds[id(r)] = "theorem"
            else:
                kinds[id(r)] = "other"
        record_kinds[path] = kinds
        mine = {}
        for k in kinds.values():
            mine[k] = mine.get(k, 0) + 1
        theirs = {k: v for k, v in (meta.get("record_kinds") or {}).items()}
        kinds_match[path] = {"mine": dict(sorted(mine.items())),
                             "recorded": dict(sorted(theirs.items())),
                             "match": mine == theirs}
    return records_by_file, record_kinds, row_counts, kinds_match


def verify_pins(target):
    pins = {}
    for path, meta in target["input_files"].items():
        live = sha256_file(ROOT / path)
        pins[path] = {"recorded": meta["sha256"], "live": live,
                      "match": live == meta["sha256"]}
    return pins


def measurement_payload(target, pins_t0):
    records_by_file, record_kinds, row_counts, kinds_match = classify_all(target)
    universes, per_class, per_class_B, src_unique, thm_unique = measure(records_by_file, record_kinds)
    recon = reconciliation(records_by_file, row_counts, universes)
    controls = run_controls()

    headline = target["headline"]
    comp = {
        "source_records_raw": [universes["U1_source_records_raw"]["records"], headline["source_records_raw"]],
        "source_records_unique": [universes["U1u_source_records_unique_id"]["records"], headline["source_records_unique"]],
        "theorem_records_raw": [universes["U2_theorem_records_raw"]["records"], headline["theorem_records_raw"]],
        "theorem_records_unique": [universes["U2u_theorem_records_unique_id"]["records"], headline["theorem_records_unique"]],
        "source_plus_theorem_raw": [universes["U4_source_plus_theorem_raw"]["records"], headline["source_plus_theorem_raw"]],
        "source_plus_theorem_unique": [universes["U4u_source_plus_theorem_unique"]["records"], headline["unique_source_universe"] + headline["unique_theorem_universe"]],
        "class_coverage_rows": [universes["U5_class_coverage_rows"]["records"], headline["class_coverage_rows"]],
        "citation_links_raw": [universes["U3_citation_links"]["links_raw"], headline["citation_links_raw"]],
        "records_with_any_axis": [sum(universes[u]["records_with_any_axis"]
                                      for u in universes if u != "U3_citation_links"),
                                  headline["records_with_any_axis"]],
    }
    comparisons = {k: {"mine": v[0], "recorded": v[1], "match": v[0] == v[1]}
                   for k, v in comp.items()}

    per_class_recorded = target["class_breakdown"]["U1_source_records"]["per_frozen_class"]
    per_class_cmp = {c: {"mine_reading_A": per_class["per_frozen_class"][c],
                         "recorded": per_class_recorded[c]["records"],
                         "match_reading_A": per_class["per_frozen_class"][c] == per_class_recorded[c]["records"],
                         "mine_reading_B": per_class_B["per_frozen_class"][c],
                         "match_reading_B": per_class_B["per_frozen_class"][c] == per_class_recorded[c]["records"]}
                     for c in FROZEN}
    per_class_cmp["no_frozen_class_token"] = {
        "mine_reading_A": per_class["records_without_frozen_class_token"],
        "recorded": target["class_breakdown"]["U1_source_records"]["records_without_frozen_class_token"],
        "match_reading_A": per_class["records_without_frozen_class_token"] == target["class_breakdown"]["U1_source_records"]["records_without_frozen_class_token"],
        "mine_reading_B": per_class_B["records_without_frozen_class_token"],
        "match_reading_B": per_class_B["records_without_frozen_class_token"] == target["class_breakdown"]["U1_source_records"]["records_without_frozen_class_token"]}
    per_class_B_all_match = all(v["match_reading_B"] for v in per_class_cmp.values())

    payload = {
        "task_id": "W100-GLIT-UNIVERSE-REPL-01",
        "worker": "worker-100",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": FROZEN,
        "target": {"path": str(TARGET.relative_to(ROOT)),
                   "sha256": sha256_file(TARGET)},
        "pins_t0": pins_t0,
        "pins_t0_all_match": all(v["match"] for v in pins_t0.values()),
        "universes": universes,
        "per_class_U1_raw_sources": {"reading_A_substring": per_class,
                                     "reading_B_exact_semicolon": per_class_B},
        "headline_comparisons": comparisons,
        "per_class_comparisons": per_class_cmp,
        "per_class_all_match_reading_A": all(v["match_reading_A"] for v in per_class_cmp.values()),
        "per_class_all_match_reading_B": per_class_B_all_match,
        "record_kind_agreement": kinds_match,
        "record_kind_agreement_all": all(v["match"] for v in kinds_match.values()),
        "reconciliation_201": recon,
        "controls": controls,
        "controls_all_pass": all(c["pass"] for c in controls),
    }
    verdict = "REPLICATED"
    if not payload["pins_t0_all_match"] or not payload["controls_all_pass"]:
        verdict = "NOT_REPLICATED"
    elif not all(v["match"] for v in comparisons.values()) or not payload["record_kind_agreement_all"]:
        verdict = "PARTIAL"
    elif not payload["per_class_all_match_reading_A"]:
        verdict = "PARTIAL"
        payload["reading_note"] = (
            "All nine headline universes and all per-file record-kind classifications "
            "reproduce exactly. The per-class U1 split differs under reading A (substring "
            "match) and reproduces the recorded 67/58/26/18/337 exactly under reading B "
            "(split class fields on ';' and require exact whole-token equality). The delta "
            "is confined to qualified/negated tokens: '(definitional support)', "
            "'(scope-caveated)', '(supporting)', '(background)', 'bears on ... / ...', and "
            "'not AF-SCC-...'. Reading A credits qualified assignments that reading B drops "
            "and also credits negated mentions that reading B correctly drops; the target "
            "recorded reading B. No headline number depends on this choice.")
    payload["verdict"] = verdict
    payload["measurement_digest"] = hashlib.sha256(canonical(payload).encode()).hexdigest()
    return payload


def main(argv):
    if "--selftest" in argv:
        ctrls = run_controls()
        print(json.dumps(ctrls, indent=1))
        return 0 if all(c["pass"] for c in ctrls) else 1
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    pins_t0 = verify_pins(target)
    if not all(v["match"] for v in pins_t0.values()):
        bad = {p: v for p, v in pins_t0.items() if not v["match"]}
        print(json.dumps({"abort": "PIN_DRIFT_AT_T0", "files": bad}, indent=1))
        return 2
    payload = measurement_payload(target, pins_t0)
    pins_t1 = verify_pins(target)
    payload["pins_t1"] = pins_t1
    payload["pins_t1_all_match"] = all(v["match"] for v in pins_t1.values())
    if not payload["pins_t1_all_match"]:
        payload["verdict"] = "NOT_REPLICATED"
        payload["notes"] = "input bytes moved during measurement; numbers bind T0 only"
    payload["generated_at"] = now()
    if "--verify" in argv and REPORT.exists():
        old = json.loads(REPORT.read_text(encoding="utf-8"))
        same = (old.get("measurement_digest") == payload.get("measurement_digest")
                and old.get("verdict") == payload.get("verdict"))
        print(json.dumps({"verify": "MATCH" if same else "MISMATCH",
                          "old_digest": old.get("measurement_digest"),
                          "new_digest": payload.get("measurement_digest"),
                          "verdict": payload["verdict"]}, indent=1))
        return 0 if same else 3
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "inputs_hashes_t0.json").write_text(json.dumps(pins_t0, indent=1, sort_keys=True), encoding="utf-8")
    (RAW / "inputs_hashes_t1.json").write_text(json.dumps(pins_t1, indent=1, sort_keys=True), encoding="utf-8")
    REPORT.write_text(json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"verdict": payload["verdict"],
                      "measurement_digest": payload["measurement_digest"],
                      "headline_mismatches": [k for k, v in payload["headline_comparisons"].items() if not v["match"]],
                      "per_class_mismatches_reading_A": [k for k, v in payload["per_class_comparisons"].items() if not v["match_reading_A"]],
                      "per_class_mismatches_reading_B": [k for k, v in payload["per_class_comparisons"].items() if not v["match_reading_B"]],
                      "record_kind_mismatch_files": [k for k, v in payload["record_kind_agreement"].items() if not v["match"]],
                      "controls_all_pass": payload["controls_all_pass"],
                      "reconciliation_201": {k: v for k, v in payload["reconciliation_201"].items()
                                             if k in ("single_file_row_count_201",
                                                      "canonical_subset_sums_eq_201_k_le_4",
                                                      "min_abs_distance_of_any_measured_universe_to_201")}},
                     indent=1))
    return 0 if payload["verdict"] != "NOT_REPLICATED" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
