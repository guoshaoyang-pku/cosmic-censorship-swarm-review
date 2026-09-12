#!/usr/bin/env python3
"""W079-L0-HF02-STAGED-REPAIR-VERIFY-01 — independent, read-only verification of
worker-025's staged L0 HF-02 disjunction repair candidate.

Pre-registration: artifacts/worker-079/l0_hf02_verify/PREREGISTRATION.md
Task: verify, at pinned bytes, that the staged candidate
  artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl
clears the literal HF-02 'disjunction of class_ids' firing on the live ledger
  ledger/theorems.jsonl
while changing only class-binding fields, introducing no class-vocabulary
violation, and leaving every other field byte-equal.

Read-only on all canonical paths. Writes report.json (+ .sha256) in its own
directory only. Fail-closed: exit 2 (no report) on pin drift, exit 3 (no report)
if any pre-registered control is not detected, exit 1 (report) if any
expectation fails, exit 0 on CANDIDATE_VERIFIED.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

TASK_ID = "W079-L0-HF02-STAGED-REPAIR-VERIFY-01"
WORKER = "worker-079"

PINS = {
    "ledger/theorems.jsonl":
        "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl":
        "b3ab6a1a635720a97e51fd332bcf1d9f9e6fdc45ad64d886106f1cd298d61cea",
    "evaluation_rubric.yaml":
        "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "schemas/taxonomy_cases.jsonl":
        "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
}

FROZEN = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
DECLARED_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528"]
SCC_ROWS = ["D-004", "D-005", "T-303", "T-305", "T-402", "T-526"]
WCC_ROWS = ["T-515", "T-528"]
PATCHABLE = ("class_ids", "informs_classes", "ledger_tags")
REPORT = HERE / "report.json"
REPORT_SHA = HERE / "report.json.sha256"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path):
    text = path.read_text(encoding="utf-8")
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{i} is not a JSON object")
        rows.append(obj)
    return rows


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def disjunction_rows(rows):
    """Literal HF-02 'disjunction of class_ids': >=2 distinct frozen tokens."""
    out = []
    for r in rows:
        toks = [t for t in (r.get("class_ids") or []) if t in FROZEN]
        if len(set(toks)) >= 2:
            out.append(r.get("theorem_id"))
    return out


def row_diff_fields(a: dict, b: dict):
    fields = sorted(set(a) | set(b))
    return [k for k in fields if canon(a.get(k)) != canon(b.get(k))]


# ---------------------------------------------------------------- expectations
def e1_rows(live, staged):
    ids_l = [r.get("theorem_id") for r in live]
    ids_s = [r.get("theorem_id") for r in staged]
    ok = (len(live) == 62 and len(staged) == 62 and ids_l == ids_s
          and len(set(ids_l)) == len(ids_l))
    return {"ok": ok, "live_rows": len(live), "staged_rows": len(staged),
            "order_identical": ids_l == ids_s,
            "unique_ids": len(set(ids_l)) == len(ids_l)}


def e2_live_disjunction(live, staged):
    got = disjunction_rows(live)
    ok = got == DECLARED_ROWS
    return {"ok": ok, "measured": got, "declared": DECLARED_ROWS}


def e3_staged_disjunction(live, staged):
    got = disjunction_rows(staged)
    return {"ok": got == [], "measured": got}


def e4_diff_scope(live, staged):
    offenders = {}
    for a, b in zip(live, staged):
        d = row_diff_fields(a, b)
        extra = [k for k in d if k not in PATCHABLE]
        if extra:
            offenders[a.get("theorem_id")] = extra
    return {"ok": not offenders, "non_patchable_offenders": offenders,
            "patchable_fields": list(PATCHABLE)}


def e5_changed_row_set(live, staged):
    changed = [a.get("theorem_id") for a, b in zip(live, staged)
               if row_diff_fields(a, b)]
    ok = changed == DECLARED_ROWS
    return {"ok": ok, "measured": changed, "declared": DECLARED_ROWS}


def e6_tokens(live, staged):
    foreign, overlap, badtype = [], [], []
    for r in staged:
        rid = r.get("theorem_id")
        cid, inf = r.get("class_ids"), r.get("informs_classes") or []
        if not isinstance(cid, list) or not isinstance(inf, list):
            badtype.append(rid)
            continue
        for t in list(cid) + list(inf):
            if t not in FROZEN:
                foreign.append([rid, t])
        if set(cid) & set(inf):
            overlap.append([rid, sorted(set(cid) & set(inf))])
    return {"ok": not (foreign or overlap or badtype),
            "foreign_tokens": foreign, "class_ids_informs_overlap": overlap,
            "non_list_fields": badtype, "frozen_ids": FROZEN}


def e7_mapping(live, staged):
    problems, table = [], {}
    live_by = {r["theorem_id"]: r for r in live}
    for b in staged:
        rid = b["theorem_id"]
        if rid not in DECLARED_ROWS:
            continue
        a = live_by[rid]
        lf = [t for t in (a.get("class_ids") or []) if t in FROZEN]
        cid = list(b.get("class_ids") or [])
        inf = list(b.get("informs_classes") or [])
        if len(set(lf)) != 2:
            problems.append([rid, "live_not_two_frozen", lf])
        if not set(cid) <= set(lf):
            problems.append([rid, "staged_class_ids_not_subset", cid, lf])
        if not set(inf) <= set(lf):
            problems.append([rid, "staged_informs_not_subset", inf, lf])
        table[rid] = {"live_class_ids": a.get("class_ids"),
                      "staged_class_ids": cid,
                      "staged_informs_classes": inf,
                      "dropped_without_replacement": sorted(set(lf) - set(cid) - set(inf))}
    return {"ok": not problems, "problems": problems, "mapping": table}


def e8_unchanged_deep_equal(live, staged):
    offenders = {}
    for a, b in zip(live, staged):
        rid = a.get("theorem_id")
        if rid in DECLARED_ROWS:
            continue
        if canon(a) != canon(b):
            offenders[rid] = row_diff_fields(a, b)
    return {"ok": not offenders, "unchanged_row_offenders": offenders}


def e9_tags_append_only(live, staged):
    problems = {}
    live_by = {r["theorem_id"]: r for r in live}
    for b in staged:
        rid = b["theorem_id"]
        if rid not in DECLARED_ROWS:
            continue
        lt = list(live_by[rid].get("ledger_tags") or [])
        st = list(b.get("ledger_tags") or [])
        if st[:len(lt)] != lt:
            problems[rid] = {"live": lt, "staged": st}
    return {"ok": not problems, "tag_prefix_offenders": problems}


def e10_no_informationless_row(live, staged):
    problems = {}
    for b in staged:
        rid = b["theorem_id"]
        if rid not in DECLARED_ROWS:
            continue
        cid = list(b.get("class_ids") or [])
        inf = list(b.get("informs_classes") or [])
        if not (set(cid) | set(inf)):
            problems[rid] = "empty_class_ids_and_informs"
        if rid in WCC_ROWS and cid != ["AF-WCC-VAC-GEN"]:
            problems[rid] = f"wcc_row_class_ids={cid}"
        if rid in SCC_ROWS and len(cid) > 1:
            problems[rid] = f"scc_row_class_ids_len={len(cid)}"
    return {"ok": not problems, "problems": problems,
            "wcc_rows": WCC_ROWS, "scc_rows": SCC_ROWS}


EXPECTATIONS = [
    ("E1_rows_parse_and_order", e1_rows),
    ("E2_live_disjunction_set", e2_live_disjunction),
    ("E3_staged_disjunction_empty", e3_staged_disjunction),
    ("E4_diff_scope_patchable_only", e4_diff_scope),
    ("E5_changed_row_set_exact", e5_changed_row_set),
    ("E6_class_vocabulary_and_disjointness", e6_tokens),
    ("E7_subset_mapping", e7_mapping),
    ("E8_unchanged_rows_deep_equal", e8_unchanged_deep_equal),
    ("E9_tags_append_only", e9_tags_append_only),
    ("E10_no_informationless_row", e10_no_informationless_row),
]


# ------------------------------------------------------------------- controls
def run_controls(live, staged):
    out = {}

    m = copy.deepcopy(staged)
    target = next(r for r in m if r["theorem_id"] not in DECLARED_ROWS)
    target["class_ids"] = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
    out["C1_reintroduced_disjunction"] = {"detected": not e3_staged_disjunction(live, m)["ok"]}

    m = copy.deepcopy(staged)
    target = next(r for r in m if r["theorem_id"] not in DECLARED_ROWS)
    target["statement_exact"] = str(target.get("statement_exact", "")) + " [tamper]"
    out["C2_content_tamper"] = {"detected": not e4_diff_scope(live, m)["ok"]}

    m = copy.deepcopy(staged)[:-1]
    out["C3_row_loss"] = {"detected": not e1_rows(live, m)["ok"]}

    m = copy.deepcopy(staged)
    target = next(r for r in m if r["theorem_id"] in DECLARED_ROWS)
    target["class_ids"] = ["AF-BOGUS-CLASS"]
    out["C4_foreign_token"] = {"detected": not e6_tokens(live, m)["ok"]}

    m = copy.deepcopy(staged)
    target = next(r for r in m if r["theorem_id"] not in DECLARED_ROWS)
    target["ledger_tags"] = list(target.get("ledger_tags") or []) + ["NINTH-ROW-EDIT"]
    out["C5_ninth_row_edit"] = {"detected": not e5_changed_row_set(live, m)["ok"]}

    out["C6_live_baseline_swap"] = {"detected": not e2_live_disjunction(staged, staged)["ok"]}

    for name, res in out.items():
        res["ok"] = bool(res["detected"])
    return out


def main() -> int:
    pins = {}
    drift = []
    for rel, declared in PINS.items():
        measured = sha256_file(ROOT / rel)
        pins[rel] = {"declared": declared, "measured": measured,
                     "match": measured == declared}
        if measured != declared:
            drift.append(rel)
    if drift:
        print(f"PIN DRIFT on {drift}; refusing to write a report (exit 2).")
        return 2

    live = load_jsonl(ROOT / "ledger/theorems.jsonl")
    staged = load_jsonl(ROOT / "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl")

    results = {}
    for name, fn in EXPECTATIONS:
        results[name] = fn(live, staged)

    controls = run_controls(live, staged)
    missed = [k for k, v in controls.items() if not v["detected"]]
    if missed:
        print(f"CONTROL MISS {missed}; refusing to write a report (exit 3).")
        return 3

    failed = [k for k, v in results.items() if not v["ok"]]
    verdict = "CANDIDATE_VERIFIED" if not failed else "CANDIDATE_REJECTED"

    body = {
        "task_id": TASK_ID,
        "worker": WORKER,
        "role": "independent non-author verification (worker-025 authored the candidate)",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "authority": ("worker-level review verdict and evidence only; no canonical write, "
                      "no node status, no validation_status=passed, no gate verdict, "
                      "no HF-02 scope ruling"),
        "object_under_test": {
            "live_anchor": "ledger/theorems.jsonl",
            "staged_candidate": "artifacts/worker-025/l0_hf02_staged/staged/theorems.hf02-staged.jsonl",
            "patchable_fields": list(PATCHABLE),
        },
        "pins": pins,
        "expectations": results,
        "expectations_failed": failed,
        "controls": controls,
        "baseline": {
            "live_rows": len(live),
            "staged_rows": len(staged),
            "live_disjunction_rows": disjunction_rows(live),
            "staged_disjunction_rows": disjunction_rows(staged),
        },
        "mapping_table": results["E7_subset_mapping"]["mapping"],
        "verdict": verdict,
        "falsifier": ("At pinned live a1674f094979 and staged b3ab6a1a6357: a ninth row with a "
                      "two-frozen-token class_ids, any staged non-patchable field differing from "
                      "live, any foreign class token or per-row class_ids/informs_classes overlap, "
                      "a non-empty staged disjunction set, or pin drift falsifies this verification."),
        "not_claimed": [
            "No HF-02 scope ruling: whether 'disjunction of class_ids' applies to ledger rows is the audit lead's decision.",
            "No semantic certification of which sibling class each row informs; the mapping table is reported for the audit lead.",
            "No mathematical review of any row; not a per-row independent review of the 62 theorems.",
            "Not a gate verdict; worker events cannot move G-LIT.",
        ],
    }
    digest = hashlib.sha256(canon(body).encode("utf-8")).hexdigest()
    body["determinism_sha256"] = digest
    REPORT.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_SHA.write_text(sha256_file(REPORT) + "  report.json\n", encoding="utf-8")

    print(f"{verdict}: expectations failed={failed or 'none'}; "
          f"controls detected={sum(1 for v in controls.values() if v['detected'])}/{len(controls)}; "
          f"determinism_sha256={digest}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
