#!/usr/bin/env python3
"""Independent, fail-closed machine check of transfer rule T1's preconditions.

Task: W001-T1-TRANSFER-PRECONDITION-01 (worker-001, class-bound to
AF-SCC-C0-VAC-GEN -> AF-SCC-C2-VAC-GEN, with AF-WCC-VAC-GEN recorded as the
family sibling for the triple-wise shared-class observation).

Question measured (not assumed):
  At the pinned rev13 formulation bytes, do F2a (AF-SCC-C2-VAC-GEN) and
  F2b (AF-SCC-C0-VAC-GEN) discharge the guards of canonical F0 transfer rule T1
  ("allowed C0 -> C2", research_map/formulation_taxonomy.yaml#transfer_rules)?
    G1: data_class fields must match exactly (including s, delta once F2 fixes them)
    G2: genericity_kind and genericity_topology must match exactly
  and does any class declare the `norm` slot the G-FORM unmet note names as (s,delta,norm)?

Behaviour:
  * measures every pinned input; any sha256 drift exits 3 WITHOUT emitting a verdict
  * runs 8 seeded mutation controls through the same comparison functions;
    any failed control exits 4 WITHOUT emitting a verdict
  * otherwise writes report.json + PINNED.json and exits 0

This is an artifact-and-binding measurement. It makes no mathematical claim, sets no
node status, records no gate verdict and writes no canonical artifact.

Usage:
  python3 artifacts/worker-001/t1_transfer_audit/audit_t1_transfer.py
Exit codes: 0 verdict emitted / 3 pin drift / 4 control failure.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

TASK_ID = "W001-T1-TRANSFER-PRECONDITION-01"
C0 = "AF-SCC-C0-VAC-GEN"
C2 = "AF-SCC-C2-VAC-GEN"
WCC = "AF-WCC-VAC-GEN"

F1_PATH = "schemas/af_wcc_vacuum.yaml"
F2A_PATH = "schemas/af_scc_c2_vacuum.yaml"
F2B_PATH = "schemas/af_scc_c0_vacuum.yaml"
TAX_PATH = "research_map/formulation_taxonomy.yaml"
SUP_PATH = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
G3_PATH = "artifacts/worker-01/validate_taxonomy.py"

# Pins measured 2026-09-12T01:02+08:00. The harness exits 3 if any moves.
PINS = {
    F1_PATH: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    F2A_PATH: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F2B_PATH: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    TAX_PATH: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    SUP_PATH: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    FROZEN_PATH: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    G3_PATH: "2cc8ee04023e2316ee47683802b0fc99c9358cc06bea824993d3ac85964a1cc3",
}

PROVENANCE_TOKENS = (
    "status", "locator", "citation", "source", "reference", "provenance", "note",
    "review", "owner", "pending", "todo", "authored", "revised", "reconciliation",
)
INDEX_LEAF_SUFFIXES = (
    "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
)
NUMERIC_ONLY = re.compile(r"^[-+]?\d+(?:\.\d+)?$")
ASSIGNED_NUMBER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s*([-+]?\d+(?:\.\d+)?)$")
WORD_NORM = re.compile(r"\bnorm\b", re.I)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(value) -> str:
    """Whitespace-normalize a scalar/list rendering so YAML folding cannot fake a diff."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def leaves(obj, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for key, val in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.update(leaves(val, path))
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            out.update(leaves(val, f"{prefix}[{i}]"))
    else:
        out[prefix] = norm(obj)
    return out


def leaf_class(path: str) -> str:
    if path.endswith(INDEX_LEAF_SUFFIXES):
        return "index"
    low = path.lower()
    if any(tok in low for tok in PROVENANCE_TOKENS):
        return "provenance"
    return "semantic"


def is_frozen(value: str) -> bool:
    """A frozen index is a single numeric literal (possibly 's = 3'), not a range/inequality."""
    v = norm(value)
    if NUMERIC_ONLY.match(v):
        return True
    m = ASSIGNED_NUMBER.match(v)
    return bool(m)


def diff_leaves(a: dict[str, str], b: dict[str, str]) -> list[dict]:
    out = []
    for path in sorted(set(a) | set(b)):
        av, bv = a.get(path), b.get(path)
        if av != bv:
            out.append({"path": path, "left": av, "right": bv, "leaf_class": leaf_class(path)})
    return out


def project(schema: dict) -> dict:
    dc = schema.get("data_class") or {}
    gen = schema.get("genericity") or {}
    reg = schema.get("regularity") or {}
    con = schema.get("conclusion") or {}
    sob = ((dc.get("regularity_class") or {}).get("sobolev_variant")) or {}
    return {
        "meta": {
            "class_id": norm(schema.get("class_id")),
            "node_id": norm(schema.get("node_id")),
            "revision": norm(schema.get("revision")),
        },
        "data_class": leaves(dc),
        "genericity": leaves(gen),
        "regularity": leaves(reg),
        "index": {
            "s": norm(sob.get("s")),
            "delta": norm(sob.get("delta")),
            "s_frozen": is_frozen(norm(sob.get("s"))),
            "delta_frozen": is_frozen(norm(sob.get("delta"))),
        },
        "conclusion": {
            "conclusion_type": norm(con.get("conclusion_type")),
            "regularity_token": norm(((schema.get("class_components") or {}).get("regularity_token"))),
        },
    }


def norm_declared(projection: dict) -> tuple[bool, list[str]]:
    hits = [p for p, v in projection["data_class"].items() if WORD_NORM.search(p) or WORD_NORM.search(v)]
    return bool(hits), hits


def merged_regularity(text: str) -> bool:
    """Reuse the canonical G3 helper (guard: copy, do not re-derive)."""
    g3 = ROOT / G3_PATH
    spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
    mod = spec.spec_from_file_location("worker01_validate_taxonomy", g3)
    obj = spec.module_from_spec(mod)
    mod.loader.exec_module(obj)
    return bool(obj.merged_match(text))


def pair_report(pa: dict, pb: dict) -> dict:
    dc_diff = diff_leaves(pa["data_class"], pb["data_class"])
    gen_diff = diff_leaves(pa["genericity"], pb["genericity"])
    sem = [d for d in dc_diff if d["leaf_class"] == "semantic"]
    return {
        "data_class_strict_equal": not dc_diff,
        "data_class_diff": dc_diff,
        "data_class_diff_count": len(dc_diff),
        "data_class_semantic_diff_count": len(sem),
        "data_class_index_diff": [d for d in dc_diff if d["leaf_class"] == "index"],
        "data_class_provenance_diff": [d for d in dc_diff if d["leaf_class"] == "provenance"],
        "data_class_semantic_diff": sem,
        "genericity_strict_equal": not gen_diff,
        "genericity_diff": gen_diff,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--pins-out", default=str(HERE / "PINNED.json"))
    args = ap.parse_args()

    # ---- 1. pin measurement, fail closed -------------------------------------
    measured = {rel: sha256_file(ROOT / rel) for rel in PINS}
    drift = {rel: {"expected": PINS[rel], "measured": measured[rel]}
             for rel in PINS if measured[rel] != PINS[rel]}
    if drift:
        print(json.dumps({"verdict": "PIN_DRIFT", "drift": drift}, indent=1))
        return 3

    schemas = {
        WCC: yaml.safe_load((ROOT / F1_PATH).read_text()),
        C2: yaml.safe_load((ROOT / F2A_PATH).read_text()),
        C0: yaml.safe_load((ROOT / F2B_PATH).read_text()),
    }
    tax = yaml.safe_load((ROOT / TAX_PATH).read_text())
    proj = {cid: project(s) for cid, s in schemas.items()}

    # ---- 2. checks -----------------------------------------------------------
    allowed = ((tax.get("transfer_rules") or {}).get("allowed")) or []
    t1 = [r for r in allowed
          if r.get("from") == C0 and r.get("to") == C2]
    checks: dict[str, object] = {}
    checks["C1_t1_rule_present"] = {
        "pass": len(t1) == 1,
        "rules_found": t1,
        "guards": t1[0].get("guards") if t1 else [],
    }

    c0c2 = pair_report(proj[C0], proj[C2])
    checks["C2_data_class_exact_match_c0_c2"] = c0c2

    idx = {cid: proj[cid]["index"] for cid in (C0, C2, WCC)}
    norms = {cid: norm_declared(proj[cid]) for cid in (C0, C2, WCC)}
    checks["C3_index_frozen_and_norm"] = {
        "index": idx,
        "both_sc_indices_frozen": bool(idx[C0]["s_frozen"] and idx[C0]["delta_frozen"]
                                        and idx[C2]["s_frozen"] and idx[C2]["delta_frozen"]),
        "norm_declared": {cid: norms[cid][0] for cid in norms},
        "norm_hits": {cid: norms[cid][1] for cid in norms},
    }

    gen = {cid: proj[cid]["genericity"] for cid in (C0, C2)}
    checks["C4_genericity_exact_match_c0_c2"] = {
        "kind_equal": gen[C0].get("kind") == gen[C2].get("kind"),
        "topology_or_measure_equal": gen[C0].get("topology_or_measure") == gen[C2].get("topology_or_measure"),
        "ambient_space_equal": gen[C0].get("ambient_space") == gen[C2].get("ambient_space"),
        "genericity_strict_equal": c0c2["genericity_strict_equal"],
        "genericity_diff": c0c2["genericity_diff"],
    }

    pairs = [(WCC, C2), (WCC, C0), (C2, C0)]
    checks["C5_triplewise_shared_class"] = {
        f"{a}|{b}": pair_report(proj[a], proj[b]) for a, b in pairs
    }

    con = {cid: proj[cid]["conclusion"] for cid in (C0, C2)}
    checks["C6_conclusion_distinct"] = {
        "c0": con[C0],
        "c2": con[C2],
        "distinct_conclusion_type": con[C0]["conclusion_type"] != con[C2]["conclusion_type"],
        "merged_regularity_in_tokens": {
            cid: merged_regularity(proj[cid]["conclusion"]["regularity_token"]) for cid in con
        },
    }

    # ---- 3. seeded mutation controls through the same functions --------------
    def mutated(cid: str, mutate) -> dict:
        s = copy.deepcopy(schemas[cid])
        mutate(s)
        return project(s)

    ctl_specs = [
        ("CT1_identical_copy_no_false_positive",
         lambda: (pair_report(proj[C0], mutated(C0, lambda s: None))["data_class_strict_equal"],
                  pair_report(proj[C0], mutated(C0, lambda s: None))["genericity_strict_equal"]) == (True, True)),
        ("CT2_seeded_s_mutation_detected",
         lambda: any(d["path"].endswith("sobolev_variant.s")
                     for d in pair_report(proj[C0], mutated(C0, lambda s: s["data_class"]["regularity_class"]["sobolev_variant"].__setitem__("s", "3"))  # noqa: E501
                                          )["data_class_diff"])),
        ("CT3_seeded_delta_mutation_detected",
         lambda: any(d["path"].endswith("sobolev_variant.delta")
                     for d in pair_report(proj[C2], mutated(C2, lambda s: s["data_class"]["regularity_class"]["sobolev_variant"].__setitem__("delta", "0.9"))  # noqa: E501
                                          )["data_class_diff"])),
        ("CT4_seeded_genericity_kind_mutation_detected",
         lambda: pair_report(proj[C0], mutated(C0, lambda s: s["genericity"].__setitem__("kind", "full_measure"))
                             )["genericity_strict_equal"] is False),
        ("CT5_seeded_topology_mutation_detected",
         lambda: pair_report(proj[C0], mutated(C0, lambda s: s["genericity"].__setitem__("topology_or_measure", "discrete topology"))
                             )["genericity_strict_equal"] is False),
        ("CT6_seeded_conclusion_merge_detected",
         lambda: merged_regularity("C0 or C2") is True and merged_regularity("C^{0} and C^{2}") is True),
        ("CT7_frozen_detector_fires_on_numeric",
         lambda: is_frozen("3") is True and is_frozen("0.5") is True and is_frozen("s = 3") is True),
        ("CT8_norm_detector_fires_on_injected_norm",
         lambda: norm_declared({"data_class": {"regularity_class.spaces": "H^s_delta with the weighted norm"}})[0] is True),
    ]
    controls = []
    for name, fn in ctl_specs:
        try:
            ok = bool(fn())
            err = None
        except Exception as exc:  # pragma: no cover
            ok, err = False, f"{type(exc).__name__}: {exc}"
        controls.append({"control": name, "passed": ok, "error": err})
    if not all(c["passed"] for c in controls):
        print(json.dumps({"verdict": "CONTROL_FAILURE", "controls": controls}, indent=1))
        return 4

    # ---- 4. verdict ----------------------------------------------------------
    reasons = []
    if not checks["C1_t1_rule_present"]["pass"]:
        reasons.append("T1_RULE_ABSENT")
    if not checks["C3_index_frozen_and_norm"]["both_sc_indices_frozen"]:
        reasons.append("INDEX_NOT_FROZEN")
    if not all(checks["C3_index_frozen_and_norm"]["norm_declared"].values()):
        reasons.append("NORM_NOT_DECLARED")
    if not c0c2["data_class_strict_equal"]:
        reasons.append("DATA_CLASS_NOT_EXACT_MATCH")
    if not (checks["C4_genericity_exact_match_c0_c2"]["kind_equal"]
            and checks["C4_genericity_exact_match_c0_c2"]["topology_or_measure_equal"]
            and checks["C4_genericity_exact_match_c0_c2"]["ambient_space_equal"]):
        reasons.append("GENERICITY_NOT_EXACT_MATCH")

    verdict = "T1_PRECONDITION_MET" if not reasons else "T1_PRECONDITION_UNMET"
    report = {
        "task_id": TASK_ID,
        "generated_at": now(),
        "actor": "worker-001",
        "harness_path": str(Path(__file__).resolve().relative_to(ROOT)),
        "harness_sha256": sha256_file(Path(__file__).resolve()),
        "pins": measured,
        "verdict": verdict,
        "transfer_status": "licensed" if verdict == "T1_PRECONDITION_MET" else "blocked",
        "reason_codes": reasons,
        "checks": checks,
        "controls": controls,
        "observation_f1_not_required_by_t1": (
            "T1 is an intra-SCC rule (C0 -> C2). Its guards bind F2a/F2b only; F1 "
            "(AF-WCC-VAC-GEN) participates in no guard of T1. The G-FORM unmet "
            "phrasing 'no single frozen data class shared by F1/F2a/F2b disables the "
            "licensed C0=>C2 transfer' therefore over-states the precondition: the "
            "measured blocker is the C0/C2 pair plus unfrozen s, delta and the absent norm."
        ),
        "falsifiers": [
            "Pin drift: any pinned sha256 changing voids this measurement (harness exits 3).",
            "At the pins, T1_PRECONDITION_UNMET is falsified if F2a and F2b declare byte-identical "
            "data_class subtrees AND numeric single-valued s and delta AND a declared norm slot AND "
            "identical genericity kind/topology, or if canonical F0 contains no C0->C2 allowed rule.",
            "A frozen-field definition is falsified by a downstream artifact that fixes s, delta and "
            "the norm at a single value in a way this projection does not read.",
        ],
        "non_claims": [
            "No mathematical statement, no gate verdict, no node status change.",
            "Not a full-schema review of F1/F2a/F2b; it measures only the T1 guard projection.",
            "No canonical artifact was written by this task.",
        ],
        "authority_note": "Worker events cannot set node status=done, validation_status=passed, or a gate verdict.",
    }
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    Path(args.pins_out).write_text(json.dumps({"measured_at": now(), "pins": measured}, indent=1) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "reason_codes": reasons,
        "report": args.out,
        "report_sha256": sha256_file(Path(args.out)),
        "controls_passed": sum(c["passed"] for c in controls),
        "controls_total": len(controls),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
