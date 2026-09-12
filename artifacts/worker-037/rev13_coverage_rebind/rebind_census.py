#!/usr/bin/env python3
"""W037-REV13-COVERAGE-REBIND-01 -- class-coverage / class-conformance evidence rebinding census.

Task (worker-037, bounded, class-bound to the L1 node scope AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;
AF-SCC-C0-VAC-GEN): after the rev13 schema landing (F1 d9cebb94, F2a e9a27996, F2b b2ab6acb,
FROZEN rev29, L0 ledger a1674f09), measure whether the L1 class-coverage family still binds to
live bytes, and whether its published readings still reproduce at the live inputs.

Read-only with respect to every canonical path and every other agent's artifact:
  * the three flash-10 instruments are IMPORTED (not copied, not modified) and their output
    constants are redirected into this artifact directory before main() is called;
  * one control uses a copy of the builder inside this directory with a documented one-line
    key patch applied to the copy only;
  * no file outside artifacts/worker-037/rev13_coverage_rebind/ is written.

Outputs: report.json, controls.json, REPORT.md, SHA256SUMS (written by emit_report.py).
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FAMILY = ROOT / "artifacts" / "flash-10" / "l1_class_coverage"
RERUN = HERE / "rerun"
RERUN.mkdir(parents=True, exist_ok=True)

# live pins this census binds to (declared here, measured below)
LIVE_PATHS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "ledger/class_coverage.csv": "abbaee54a5a3c82b70a6b4e646edd29ff6d6daa3e2d82844296dfba8afc3a724",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
}
INSTRUMENTS = {
    "wcc_driver": FAMILY / "wcc_class_conformance_audit.py",
    "c2_driver": FAMILY / "c2_class_conformance_audit.py",
    "coverage_builder": FAMILY / "build_ledger_class_coverage.py",
    "c2_reaudit_rev12": FAMILY / "c2_reaudit_rev12.py",
}
BASELINES = {
    "wcc_rev12": FAMILY / "wcc_class_conformance_audit.cce9c60146d6.json",
    "c2_rev12": FAMILY / "c2_class_conformance_audit.5476a3f2c6bc.json",
}
DECLARED_SUMMARY = FAMILY / "coverage_summary.json"
LIVE_MATRIX = ROOT / "ledger" / "class_coverage.csv"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256(p: Path) -> str | None:
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def import_driver(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------------------------
# Part 1 -- declared-pin census across the family
# --------------------------------------------------------------------------------------------
def is_path_like(key: str) -> bool:
    return ("/" in key) and not key.startswith("artifacts/flash-10/l1_class_coverage/" + "x")


def walk_pins(obj, out: list, source: str, key_path: str = ""):
    """Collect (declared_path, declared_sha256) from any nested {'<path>': {'sha256': h}} or
    {'<path>': h} structure, plus flat '<path>-sha256' keys."""
    if isinstance(obj, dict):
        # form A: {"<path>": {"sha256": "..."}}
        for k, v in obj.items():
            kp = f"{key_path}.{k}" if key_path else k
            if isinstance(v, dict) and isinstance(v.get("sha256"), str) and HEX64.match(v["sha256"]):
                if is_path_like(k):
                    out.append({"source": source, "key_path": kp, "declared_path": k,
                                "declared_sha256": v["sha256"], "form": "dict.sha256"})
            if isinstance(v, str) and HEX64.match(v) and is_path_like(k):
                if not (isinstance(obj.get(k), dict)):
                    out.append({"source": source, "key_path": kp, "declared_path": k,
                                "declared_sha256": v, "form": "flat_path_to_hash"})
            walk_pins(v, out, source, kp)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_pins(v, out, source, f"{key_path}[{i}]")


def classify_pin(pin: dict) -> dict:
    live = ROOT / pin["declared_path"]
    measured = sha256(live)
    if measured is None:
        status = "MISSING"
    elif measured == pin["declared_sha256"]:
        status = "ALIGNED"
    else:
        status = "SUPERSEDED"
    pin = dict(pin)
    pin["measured_sha256"] = measured
    pin["status"] = status
    if measured and status == "SUPERSEDED":
        pin["measured_prefix"] = measured[:12]
        pin["declared_prefix"] = pin["declared_sha256"][:12]
    return pin


def part1_pin_census() -> dict:
    pins = []
    scanned = []
    for p in sorted(FAMILY.glob("*.json")):
        scanned.append({"path": str(p.relative_to(ROOT)), "sha256": sha256(p)})
        try:
            walk_pins(load_json(p), pins, str(p.relative_to(ROOT)))
        except Exception as e:  # a malformed family member is itself a finding
            pins.append({"source": str(p.relative_to(ROOT)), "error": repr(e)})
    classified = [classify_pin(p) for p in pins if "declared_path" in p]
    by_status: dict[str, int] = {}
    for p in classified:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
    # only pins to the five class/gate-bearing inputs count as gate-relevant
    gate_inputs = set(LIVE_PATHS)
    gate_pins = [p for p in classified if p["declared_path"] in gate_inputs]
    return {
        "family_files_scanned": scanned,
        "n_declared_pins": len(classified),
        "by_status": by_status,
        "gate_input_pins": sorted(gate_pins, key=lambda p: (p["declared_path"], p["source"])),
        "gate_input_pins_superseded": [p for p in gate_pins if p["status"] == "SUPERSEDED"],
        "gate_input_pins_aligned": [p for p in gate_pins if p["status"] == "ALIGNED"],
        "errors": [p for p in pins if "error" in p],
    }


# --------------------------------------------------------------------------------------------
# Part 2 -- conformance re-read at live bytes vs the rev12 baselines
# --------------------------------------------------------------------------------------------
def part2_conformance_reread() -> dict:
    out = {"instruments": {}, "runs": {}, "field_diff": {}}
    for name, path in INSTRUMENTS.items():
        out["instruments"][name] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}

    # WCC
    mod = import_driver(INSTRUMENTS["wcc_driver"], "wcc_drv_census")
    mod.OUT = RERUN / "wcc_rerun.json"
    rc = mod.main()
    out["runs"]["wcc"] = {"exit_code": rc, "out": str(mod.OUT.relative_to(ROOT)),
                          "out_sha256": sha256(mod.OUT)}
    # C2
    mod2 = import_driver(INSTRUMENTS["c2_driver"], "c2_drv_census")
    mod2.OUT = RERUN / "c2_rerun.json"
    rc2 = mod2.main()
    out["runs"]["c2"] = {"exit_code": rc2, "out": str(mod2.OUT.relative_to(ROOT)),
                         "out_sha256": sha256(mod2.OUT)}

    for label, new_p, base_p in (("wcc", RERUN / "wcc_rerun.json", BASELINES["wcc_rev12"]),
                                 ("c2", RERUN / "c2_rerun.json", BASELINES["c2_rev12"])):
        new, base = load_json(new_p), load_json(base_p)
        blk_new, blk_base = new.get("class_definition", {}), base.get("class_definition", {})
        keys = sorted(set(blk_new) | set(blk_base))
        differing = [k for k in keys
                     if json.dumps(blk_new.get(k), sort_keys=True) != json.dumps(blk_base.get(k), sort_keys=True)]
        # fields that are pin/bookkeeping by construction (a-priori non-substantive)
        bookkeeping = {"sha256", "revision", "authoring_tree_observation", "map_pinned_f2a_revision_observation",
                       "map_gate_measured_f2a_prefix", "map_updated_at", "note"}
        substantive = [k for k in differing if k not in bookkeeping]
        s_new, s_base = new.get("summary", {}), base.get("summary", {})
        counts_keys = ["n_bound_entries", "n_discharging", "class_conclusion_state"]
        counts_same = all(json.dumps(s_new.get(k), sort_keys=True) == json.dumps(s_base.get(k), sort_keys=True)
                          for k in counts_keys)
        out["field_diff"][label] = {
            "new": str(new_p.relative_to(ROOT)),
            "baseline": str(base_p.relative_to(ROOT)),
            "n_fields": len(keys),
            "differing_fields": differing,
            "substantive_differing_fields": substantive,
            "bookkeeping_differing_fields": [k for k in differing if k in bookkeeping],
            "reading_counts_same": counts_same,
            "new_counts": {k: s_new.get(k) for k in counts_keys},
            "baseline_counts": {k: s_base.get(k) for k in counts_keys},
            "new_inputs": new.get("inputs"),
            "baseline_inputs": base.get("inputs"),
        }
    return out


# --------------------------------------------------------------------------------------------
# Part 3 -- coverage matrix/summary rebuild at live inputs (unmodified builder, redirected OUT)
# --------------------------------------------------------------------------------------------
def run_builder(builder_path: Path, out_csv: Path, out_summary: Path, module_name: str) -> dict:
    mod = import_driver(builder_path, module_name)
    mod.OUT_CSV = out_csv
    mod.SUMMARY = out_summary
    rc = mod.main()
    return {"exit_code": rc, "out_csv": str(out_csv.relative_to(ROOT)),
            "out_csv_sha256": sha256(out_csv), "out_summary": str(out_summary.relative_to(ROOT)),
            "out_summary_sha256": sha256(out_summary)}


def matrix_column_diff(live: Path, rebuilt: Path) -> dict:
    a = list(csv.DictReader(live.open(newline="")))
    b = list(csv.DictReader(rebuilt.open(newline="")))
    if len(a) != len(b):
        return {"row_count_mismatch": [len(a), len(b)]}
    changed_cols: dict[str, int] = {}
    changed_rows = []
    for ra, rb in zip(a, b):
        if ra["row_id"] != rb["row_id"] or ra["source_id"] != rb["source_id"] or ra["class_id"] != rb["class_id"]:
            return {"key_alignment_failure": [ra["row_id"], rb["row_id"]]}
        diffs = [c for c in ra if ra[c] != rb[c]]
        for c in diffs:
            changed_cols[c] = changed_cols.get(c, 0) + 1
        if diffs:
            changed_rows.append({"row_id": ra["row_id"], "class_id": ra["class_id"],
                                 "coverage_live": ra["coverage"], "coverage_rebuilt": rb["coverage"],
                                 "changed_columns": diffs})
    return {"n_rows": len(a), "n_changed_rows": len(changed_rows),
            "changed_columns": changed_cols, "sample_changed_rows": changed_rows[:12]}


def per_class_counts(summary: dict) -> dict:
    return {c: {k: v.get(k) for k in ("covered", "partial", "none", "unassessed")}
            for c, v in summary["classes"].items()}


def part3_coverage_rebuild() -> dict:
    live_summary = load_json(DECLARED_SUMMARY)
    run = run_builder(INSTRUMENTS["coverage_builder"], RERUN / "class_coverage.rebuilt.csv",
                      RERUN / "coverage_summary.rebuilt.json", "builder_live")
    rebuilt_summary = load_json(RERUN / "coverage_summary.rebuilt.json")
    live_sha, rebuilt_sha = sha256(LIVE_MATRIX), run["out_csv_sha256"]
    declared_counts = per_class_counts(live_summary)
    rebuilt_counts = per_class_counts(rebuilt_summary)
    return {
        "builder": {"path": str(INSTRUMENTS["coverage_builder"].relative_to(ROOT)),
                    "sha256": sha256(INSTRUMENTS["coverage_builder"])},
        "run": run,
        "live_matrix": {"path": str(LIVE_MATRIX.relative_to(ROOT)), "sha256": live_sha},
        "matrix_rebuild_matches_live": live_sha == rebuilt_sha,
        "declared_summary_inputs": live_summary.get("inputs"),
        "rebuilt_summary_inputs": rebuilt_summary.get("inputs"),
        "declared_counts": declared_counts,
        "rebuilt_counts": rebuilt_counts,
        "counts_differ": declared_counts != rebuilt_counts,
        "column_diff": matrix_column_diff(LIVE_MATRIX, RERUN / "class_coverage.rebuilt.csv"),
    }


# --------------------------------------------------------------------------------------------
# Part 4 -- controls: isolate the cause to the ledger vocabulary, prove instrument sensitivity
# --------------------------------------------------------------------------------------------
def part4_controls() -> dict:
    controls = {}

    # C1: augmented ledger copy -- add the builder's key (status: accepted) to every row that
    # the live vocabulary marks verified+author-asserted. If covered counts become non-zero, the
    # frozen-key reading of 0 is caused by the missing `status` key, not by other inputs.
    src_rows = [json.loads(l) for l in (ROOT / "ledger" / "theorems.jsonl").read_text().splitlines() if l.strip()]
    augmented = []
    n_aug = 0
    for r in src_rows:
        r2 = dict(r)
        if r2.get("status") is None:
            r2["status"] = "accepted" if (r2.get("content_status") == "verified"
                                          and r2.get("author_asserts_supports") is True) else "withdrawn"
            n_aug += 1
        augmented.append(r2)
    aug_path = RERUN / "theorems.augmented_status.jsonl"
    aug_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in augmented) + "\n", encoding="utf-8")
    mod = import_driver(INSTRUMENTS["coverage_builder"], "builder_c1")
    mod.THEOREMS = aug_path
    mod.OUT_CSV = RERUN / "class_coverage.c1_augmented.csv"
    mod.SUMMARY = RERUN / "coverage_summary.c1_augmented.json"
    rc = mod.main()
    c1 = load_json(RERUN / "coverage_summary.c1_augmented.json")
    controls["C1_augmented_status_key"] = {
        "purpose": "positive control: adding only the builder's expected key to a COPY of the live "
                   "ledger must make covered cells reappear if the missing key is the cause",
        "rows_augmented": n_aug,
        "exit_code": rc,
        "counts": per_class_counts(c1),
        "covered_total": sum(v.get("covered", 0) for v in per_class_counts(c1).values()),
    }

    # C2: identity/no-op control -- rebuild the unmodified live inputs into a second file; must
    # reproduce the Part-3 rebuild byte-for-byte (determinism).
    run2 = run_builder(INSTRUMENTS["coverage_builder"], RERUN / "class_coverage.rebuilt.ctrl2.csv",
                       RERUN / "coverage_summary.rebuilt.ctrl2.json", "builder_c2")
    r1 = sha256(RERUN / "class_coverage.rebuilt.csv")
    controls["C2_determinism"] = {
        "purpose": "determinism control: a second unmodified rebuild must equal the first",
        "first_sha256": r1, "second_sha256": run2["out_csv_sha256"], "identical": r1 == run2["out_csv_sha256"],
    }

    # C3: counterfactual control -- the SAME unmodified builder module with its coverage key
    # function replaced in memory by the nearest live-vocabulary key. THIS IS A COUNTERFACTUAL,
    # NOT A CLAIM: it measures what `content_status == verified and author_asserts_supports` would
    # yield, pending the A0/BL-9 vocabulary ruling. The patch is recorded verbatim below and the
    # instrument file itself is hashed into the report.
    def strength_counterfactual(t: dict) -> tuple:
        accepted = (t.get("content_status") == "verified" and t.get("author_asserts_supports") is True)
        covered = (accepted and t.get("entry_kind") in mod.COVERED_KINDS
                   and t.get("conclusion_type") in mod.COVERED_CONCLUSIONS)
        return (0 if covered else 1,
                mod.CT_RANK.get(t.get("conclusion_type"), 9),
                mod.EK_RANK.get(t.get("entry_kind"), 12),
                0 if accepted else 1,
                t.get("theorem_id", ""))

    mod3 = import_driver(INSTRUMENTS["coverage_builder"], "builder_c3")
    mod3.strength = strength_counterfactual
    mod3.OUT_CSV = RERUN / "class_coverage.c3_counterfactual.csv"
    mod3.SUMMARY = RERUN / "coverage_summary.c3_counterfactual.json"
    rc3 = mod3.main()
    c3 = load_json(RERUN / "coverage_summary.c3_counterfactual.json")
    controls["C3_counterfactual_content_status_verified"] = {
        "purpose": "counterfactual only: nearest-live-token re-key of the coverage predicate; "
                   "requires A0/BL-9 vocabulary adjudication before it can be cited as coverage",
        "patch": {
            "target": "build_ledger_class_coverage.strength (module global, in-memory)",
            "from": 'accepted = (t.get("status") == "accepted")',
            "to": 'accepted = (t.get("content_status") == "verified" and '
                  't.get("author_asserts_supports") is True)',
        },
        "exit_code": rc3,
        "counts": per_class_counts(c3),
        "covered_total": sum(v.get("covered", 0) for v in per_class_counts(c3).values()),
    }

    # C4: mutation control -- the counterfactual keyed builder on a ledger copy with
    # content_status removed must lose every cell the counterfactual just gained, proving the
    # counterfactual instrument is sensitive to that field and not to file identity.
    mut_rows = []
    for r in src_rows:
        r2 = dict(r)
        r2.pop("content_status", None)
        mut_rows.append(r2)
    mut_path = RERUN / "theorems.c4_mutated.jsonl"
    mut_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in mut_rows) + "\n", encoding="utf-8")
    mod4 = import_driver(INSTRUMENTS["coverage_builder"], "builder_c4")
    mod4.strength = strength_counterfactual
    mod4.THEOREMS = mut_path
    mod4.OUT_CSV = RERUN / "class_coverage.c4_mutated.csv"
    mod4.SUMMARY = RERUN / "coverage_summary.c4_mutated.json"
    rc4 = mod4.main()
    c4 = load_json(RERUN / "coverage_summary.c4_mutated.json")
    controls["C4_mutation_drops_covered"] = {
        "purpose": "mutation control: counterfactual builder + content_status removed from a COPY "
                   "of the live ledger must yield zero covered cells",
        "exit_code": rc4,
        "counts": per_class_counts(c4),
        "covered_total": sum(v.get("covered", 0) for v in per_class_counts(c4).values()),
    }
    return controls


# --------------------------------------------------------------------------------------------
# Part 5 -- exposure: who cites the stale family artifacts / published counts
# --------------------------------------------------------------------------------------------
def part5_exposure() -> dict:
    pats = ["class_coverage.csv", "coverage_summary.json", "l1_class_coverage"]
    hits = {"research_map.json": [], "reviews": [], "events": []}
    mapped = load_json(ROOT / "research_map" / "research_map.json")
    txt = json.dumps(mapped)
    for pat in pats:
        hits["research_map.json"].append({"pattern": pat, "count": txt.count(pat)})
    for p in sorted((ROOT / "reviews").glob("*.json")):
        t = p.read_text(encoding="utf-8", errors="replace")
        for pat in pats:
            if pat in t:
                hits["reviews"].append({"path": str(p.relative_to(ROOT)), "pattern": pat})
    ev = ROOT / "research_map" / "events.jsonl"
    if ev.exists():
        t = ev.read_text(encoding="utf-8", errors="replace")
        for pat in pats:
            hits["events"].append({"pattern": pat, "count": t.count(pat)})
    # L1 node declaration
    l1 = None
    for g in mapped.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == "L1":
                l1 = {k: n.get(k) for k in ("artifact", "artifact_sha256", "artifact_sha256_measured",
                                            "declared_hash_matches_measured", "validation_status", "status")}
    # gate text mentioning coverage
    gates = {g["gate_id"]: {"verdict": g.get("verdict"),
                            "unmet": [u for u in (g.get("unmet") or []) if "cover" in u.lower()]}
             for g in mapped.get("gates", [])}
    return {"map_mentions": hits["research_map.json"], "review_mentions": hits["reviews"],
            "event_mentions": hits["events"], "L1_node": l1, "gate_coverage_unmet": gates}


def main() -> int:
    t0 = {p: sha256(ROOT / p) for p in LIVE_PATHS}
    report = {
        "schema": "worker-037/rev13-coverage-rebind/v1",
        "task_id": "W037-REV13-COVERAGE-REBIND-01",
        "actor": "worker-037",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "authority_note": "Worker-level measurement evidence only. No gate verdict, no node status, "
                          "no validation_status promotion, no canonical-path write.",
        "declared_live_pins": LIVE_PATHS,
        "measured_at_start": t0,
        "part1_pin_census": part1_pin_census(),
    }
    report["part2_conformance_reread"] = part2_conformance_reread()
    report["part3_coverage_rebuild"] = part3_coverage_rebuild()
    controls = part4_controls()
    (HERE / "controls.json").write_text(json.dumps(controls, indent=2) + "\n", encoding="utf-8")
    report["part4_controls"] = {k: {kk: vv for kk, vv in v.items() if kk != "counts"}
                                for k, v in controls.items()}
    report["part5_exposure"] = part5_exposure()
    t1 = {p: sha256(ROOT / p) for p in LIVE_PATHS}
    report["measured_at_end"] = t1
    report["inputs_stable"] = t0 == t1
    # Determinism disclosure: the measurement core is a pure function of the pinned inputs; the
    # live-map observation fields (part2's map_* observation values inside the rerun JSONs, part5's
    # mention counts, and the rerun outputs' own created_at stamps) move with the map and the
    # 15-minute cycle. Hash the core so two runs can be compared without those fields.
    core = {
        "declared_live_pins": LIVE_PATHS,
        "part1_pin_census": report["part1_pin_census"],
        "part2_field_diff": report["part2_conformance_reread"]["field_diff"],
        "part2_instruments": report["part2_conformance_reread"]["instruments"],
        "part3_coverage_rebuild": report["part3_coverage_rebuild"],
        "part4_controls": report["part4_controls"],
    }
    report["determinism"] = {
        "stable_core_sha256": hashlib.sha256(
            json.dumps(core, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        "stable_core_covers": ["part1", "part2 field_diff + instrument hashes", "part3", "part4"],
        "volatile_fields": [
            "part2 runs[*].out_sha256 and the rerun JSONs' created_at (regenerated each run)",
            "part2 class_definition map_* observation values (live map read)",
            "part5 exposure counts (live map/events text)",
        ],
        "note": "artifacts are pinned by sha256 as snapshots; the stable core is what a re-run must "
                "reproduce to confirm the measurement, the volatile fields are live-map observations",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("== summary ==")
    print("part1 by_status:", report["part1_pin_census"]["by_status"])
    print("part1 superseded gate pins:", len(report["part1_pin_census"]["gate_input_pins_superseded"]))
    for lab, d in report["part2_conformance_reread"]["field_diff"].items():
        print(f"part2 {lab}: counts_same={d['reading_counts_same']} substantive_diff={d['substantive_differing_fields']}")
    p3 = report["part3_coverage_rebuild"]
    print("part3 matrix_rebuild_matches_live:", p3["matrix_rebuild_matches_live"])
    print("part3 declared:", json.dumps(p3["declared_counts"]))
    print("part3 rebuilt :", json.dumps(p3["rebuilt_counts"]))
    for k, v in controls.items():
        print(f"  {k}: covered_total={v.get('covered_total')} identical={v.get('identical')}")
    print("inputs_stable:", report["inputs_stable"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
