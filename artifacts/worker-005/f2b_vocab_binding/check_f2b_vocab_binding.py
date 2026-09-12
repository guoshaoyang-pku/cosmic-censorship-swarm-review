#!/usr/bin/env python3
"""W005-F2B-VOCAB-BIND-01 -- independent vocabulary-binding audit of one class.

class_id : AF-SCC-C0-VAC-GEN
node_id  : F2b
gate     : G-FORM
scope    : structural / evidence-binding only. Read-only on canonical artifacts.
           Decides no mathematics, sets no node status and no gate verdict.

Question: does the class-bound vocabulary that schemas/af_scc_c0_vacuum.yaml declares
(conclusion.conclusion_type, genericity.kind) have a machine-checkable binding to the
canonical F0 taxonomy (research_map/formulation_taxonomy.yaml), either by literal
membership in F0's field_vocabulary allowed-lists or by a path+sha256 reference to
artifacts/formulation/VOCAB_ALIASES.json? And does that vocabulary stay inside the
single C0 class (no C2/WCC merge or confusion)?

Usage:
  python3 check_f2b_vocab_binding.py --report [--measured-at TS]
  python3 check_f2b_vocab_binding.py --selftest
Exit code 0 iff the checker ran and wrote its outputs; the verdict is data, not an
exit status (a failing audit still exits 0 so the evidence lands on disk).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
PATHS = {
    "f2b": ROOT / "schemas/af_scc_c0_vacuum.yaml",
    "f0": ROOT / "research_map/formulation_taxonomy.yaml",
    "alias": ROOT / "artifacts/formulation/VOCAB_ALIASES.json",
    "frozen": ROOT / "artifacts/formulation/FROZEN.json",
    "ce": ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json",
}

# Declared pins as of the rev12 freeze (FROZEN.json revision 28, 2026-09-12T00:35:08+08:00)
EXPECTED = {
    "f2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "f0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "alias": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "ce": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}
CLASS_ID = "AF-SCC-C0-VAC-GEN"
CANON_C0 = "scc_c0_future_inextendibility"
ALIAS_C0 = "strong_cosmic_censorship_C0"
MERGED_TOKEN = "strong_cosmic_censorship"  # rejected_ambiguous_tokens in VOCAB_ALIASES


class DuplicateKeyError(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys instead of silently last-winning."""


def _no_duplicates(loader: StrictLoader, node, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DuplicateKeyError(f"duplicate mapping key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml_strict(path: Path):
    with path.open("rb") as fh:
        return yaml.load(fh.read().decode("utf-8"), Loader=StrictLoader)


def find_alias_refs(node, hits=None):
    """Collect string leaves that name VOCAB_ALIASES.json (any depth)."""
    if hits is None:
        hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str) and "VOCAB_ALIASES" in v:
                hits.append({"key": str(k), "value": v})
            find_alias_refs(v, hits)
    elif isinstance(node, list):
        for v in node:
            find_alias_refs(v, hits)
    return hits


def collect_sha256s(node, out=None):
    """All string leaves that look like a sha256 hex digest, with their key path."""
    if out is None:
        out = []
    if isinstance(node, dict):
        for k, v in node.items():
            collect_sha256s(v, out)
            if isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v.lower()):
                out.append(v.lower())
    elif isinstance(node, list):
        for v in node:
            collect_sha256s(v, out)
    return out


def canonicalize(kind: str, token, alias: dict):
    """Map a token to its VOCAB_ALIASES canonical key. Returns (canonical_or_token, status)."""
    rejected = alias.get("rejected_ambiguous_tokens", {}) or {}
    if token in rejected:
        return token, "rejected_ambiguous"
    table = alias.get(kind, {}) or {}
    for canon, accepted in table.items():
        if token == canon or token in (accepted or []):
            return canon, "registered"
    return token, "unregistered"


def build_view(measured_at: str) -> dict:
    """Read the artifacts once and project only the fields the checks consume."""
    f2b_raw = PATHS["f2b"].read_bytes()
    f0_raw = PATHS["f0"].read_bytes()
    f2b = yaml.load(f2b_raw.decode("utf-8"), Loader=StrictLoader)
    f0 = yaml.load(f0_raw.decode("utf-8"), Loader=StrictLoader)
    alias = json.loads(PATHS["alias"].read_text())
    frozen = json.loads(PATHS["frozen"].read_text())
    frozen_files = frozen.get("files", {}) or {}

    fv = f0.get("field_vocabulary", {}) or {}
    axes = ((f0.get("classes", {}) or {}).get(CLASS_ID, {}) or {}).get("axes", {}) or {}
    transfers = f0.get("transfer_rules", {}) or {}
    allowed = transfers.get("allowed", []) or []
    forbidden = transfers.get("forbidden", []) or []
    implication = f2b.get("implication_ledger", {}) or {}
    f0_binding = f2b.get("f0_binding", {}) or {}

    # pin stability: re-measure after the projections were built
    f2b_after = sha256_file(PATHS["f2b"])
    f0_after = sha256_file(PATHS["f0"])

    return {
        "measured_at": measured_at,
        "f2b": {
            "sha256": hashlib.sha256(f2b_raw).hexdigest(),
            "sha256_after": f2b_after,
            "class_id": f2b.get("class_id"),
            "components": f2b.get("class_components", {}) or {},
            "conclusion_type": (f2b.get("conclusion", {}) or {}).get("conclusion_type"),
            "conclusion_family": (f2b.get("conclusion", {}) or {}).get("family"),
            "genericity_kind": (f2b.get("genericity", {}) or {}).get("kind"),
            "i_plus_role": (f2b.get("i_plus", {}) or {}).get("role"),
            "i_plus_in_conclusion": (f2b.get("i_plus", {}) or {}).get("in_conclusion"),
            "sibling_disjoint_from": f2b.get("sibling_disjoint_from"),
            "alias_refs": find_alias_refs(f2b),
            "sha256s": collect_sha256s(f2b),
            "f0_binding": f0_binding,
            "entailments": implication.get("one_way_entailments", []) or [],
            "subsumption_note": implication.get("subsumption_note", ""),
        },
        "f0": {
            "sha256": hashlib.sha256(f0_raw).hexdigest(),
            "sha256_after": f0_after,
            "allowed_conclusion": (fv.get("conclusion_type", {}) or {}).get("allowed", []) or [],
            "allowed_genericity": (fv.get("genericity_kind", {}) or {}).get("allowed", []) or [],
            "axes": axes,
            "t1_c0_to_c2": any(
                r.get("from") == CLASS_ID and r.get("to") == "AF-SCC-C2-VAC-GEN" for r in allowed
            ),
            "x1_c2_to_c0_forbidden": any(
                (r.get("from") == "AF-SCC-C2-VAC-GEN" and r.get("to") == CLASS_ID)
                or (
                    "AF-SCC-C2-VAC-GEN" in str(r.get("pattern", ""))
                    and CLASS_ID in str(r.get("pattern", ""))
                    and "->" in str(r.get("pattern", ""))
                    and str(r.get("pattern", "")).index("AF-SCC-C2-VAC-GEN")
                    < str(r.get("pattern", "")).index(CLASS_ID)
                )
                for r in forbidden
            ),
        },
        "alias": {
            "sha256": sha256_file(PATHS["alias"]),
            "conclusion_type": alias.get("conclusion_type", {}) or {},
            "genericity_kind": alias.get("genericity_kind", {}) or {},
            "rejected": alias.get("rejected_ambiguous_tokens", {}) or {},
        },
        "frozen": {
            "revision": frozen.get("revision"),
            "f2b_pin": (frozen_files.get("schemas/af_scc_c0_vacuum.yaml", {}) or {}).get("sha256"),
            "ce_pin": (frozen_files.get("artifacts/formulation/evidence/taxonomy_consistency.json", {}) or {}).get("sha256"),
        },
        "ce": {"sha256": sha256_file(PATHS["ce"])},
    }


def checks(v: dict) -> list:
    f2b, f0, alias, frozen, ce = v["f2b"], v["f0"], v["alias"], v["frozen"], v["ce"]
    out = []

    def add(cid, title, ok, detail, evidence):
        out.append(
            {
                "id": cid,
                "title": title,
                "status": "pass" if ok else "fail",
                "detail": detail,
                "evidence_refs": evidence,
            }
        )

    pin_fail = [k for k in ("f2b", "f0", "alias", "ce") if v[k]["sha256"] != EXPECTED[k]]
    drift = [k for k in ("f2b", "f0") if v[k]["sha256"] != v[k]["sha256_after"]]
    frozen_ok = frozen["f2b_pin"] == f2b["sha256"]
    add(
        "P1",
        "pins_and_freeze_match",
        not pin_fail and not drift and frozen_ok,
        {
            "measured": {k: v[k]["sha256"] for k in ("f2b", "f0", "alias", "ce")},
            "declared": EXPECTED,
            "mismatched": pin_fail,
            "drift_within_run": drift,
            "frozen_rev": frozen["revision"],
            "frozen_pin_matches_measured_f2b": frozen_ok,
        },
        [f"schemas/af_scc_c0_vacuum.yaml#{f2b['sha256'][:12]}",
         f"research_map/formulation_taxonomy.yaml#{f0['sha256'][:12]}",
         f"artifacts/formulation/FROZEN.json#rev{frozen['revision']}"],
    )

    comp = f2b["components"] or {}
    identity_ok = (
        f2b["class_id"] == CLASS_ID
        and comp.get("censorship") == "SCC"
        and comp.get("regularity_token") == "C0"
    )
    add(
        "P2",
        "class_identity_is_C0_SCC",
        identity_ok,
        {"class_id": f2b["class_id"], "class_components": comp},
        [f"schemas/af_scc_c0_vacuum.yaml#{f2b['sha256'][:12]}"],
    )

    canon_tok, canon_status = canonicalize("conclusion_type", f2b["conclusion_type"], alias)
    p3_ok = canon_status != "rejected_ambiguous" and canon_tok == CANON_C0
    add(
        "P3",
        "conclusion_token_resolves_to_exactly_one_C0_class",
        p3_ok,
        {
            "declared": f2b["conclusion_type"],
            "canonical": canon_tok,
            "alias_status": canon_status,
            "required_canonical": CANON_C0,
        },
        [f"schemas/af_scc_c0_vacuum.yaml#{f2b['sha256'][:12]}",
         f"artifacts/formulation/VOCAB_ALIASES.json#{alias['sha256'][:12]}"],
    )

    p4_ok = f2b["conclusion_type"] in f0["allowed_conclusion"]
    add(
        "P4",
        "conclusion_token_literal_member_of_bound_F0_allowed_list",
        p4_ok,
        {
            "declared": f2b["conclusion_type"],
            "f0_allowed": f0["allowed_conclusion"],
            "f0_C0_axis_value": f0["axes"].get("conclusion_type"),
        },
        [f"research_map/formulation_taxonomy.yaml#{f0['sha256'][:12]}"],
    )

    p5_ok = f2b["genericity_kind"] in f0["allowed_genericity"]
    add(
        "P5",
        "genericity_token_literal_member_of_bound_F0_allowed_list",
        p5_ok,
        {
            "declared": f2b["genericity_kind"],
            "f0_allowed": f0["allowed_genericity"],
            "f0_C0_axis_value": f0["axes"].get("genericity_kind"),
        },
        [f"research_map/formulation_taxonomy.yaml#{f0['sha256'][:12]}"],
    )

    refs = f2b["alias_refs"]
    shas = f2b["sha256s"] + [r.get("sha256") for r in refs if isinstance(r, dict)]
    p6_ok = len(refs) > 0 and alias["sha256"] in shas
    add(
        "P6",
        "alias_companion_bound_by_path_and_sha256",
        p6_ok,
        {
            "alias_refs_found": refs,
            "measured_alias_sha256": alias["sha256"],
            "alias_sha_present_anywhere_in_f2b": alias["sha256"] in shas,
        },
        [f"schemas/af_scc_c0_vacuum.yaml#{f2b['sha256'][:12]}",
         f"artifacts/formulation/VOCAB_ALIASES.json#{alias['sha256'][:12]}"],
    )

    forbidden_tokens = {
        MERGED_TOKEN,
        "strong_cosmic_censorship_C2",
        "scc_c2_future_inextendibility",
        "weak_cosmic_censorship",
    }
    p7_ok = (
        f2b["conclusion_family"] == "SCC"
        and f2b["i_plus_in_conclusion"] is False
        and f2b["conclusion_type"] not in forbidden_tokens
    )
    add(
        "P7",
        "family_separation_no_WCC_or_C2_token_in_class_conclusion",
        p7_ok,
        {
            "conclusion_family": f2b["conclusion_family"],
            "i_plus_role": f2b["i_plus_role"],
            "i_plus_in_conclusion": f2b["i_plus_in_conclusion"],
            "conclusion_token": f2b["conclusion_type"],
            "forbidden_tokens": sorted(forbidden_tokens),
        },
        [f"schemas/af_scc_c0_vacuum.yaml#{f2b['sha256'][:12]}",
         f"research_map/formulation_taxonomy.yaml#{f0['sha256'][:12]}"],
    )

    bad_rows = [
        r
        for r in f2b["entailments"]
        if r.get("relation") == "entails" and "C2" in str(r.get("from", "")) and "this class" in str(r.get("to", ""))
    ]
    c0_c2_row = any(
        r.get("relation") == "entails"
        and "C0" in str(r.get("from", ""))
        and "C2" in str(r.get("to", ""))
        for r in f2b["entailments"]
    )
    note_ok = "never the reverse" in str(f2b["subsumption_note"]) and "C0" in str(f2b["subsumption_note"])
    p8_ok = f0["t1_c0_to_c2"] and f0["x1_c2_to_c0_forbidden"] and c0_c2_row and not bad_rows and note_ok
    add(
        "P8",
        "C0_implies_C2_one_way_and_converse_forbidden",
        p8_ok,
        {
            "f0_T1_C0_to_C2": f0["t1_c0_to_c2"],
            "f0_X1_C2_to_C0_forbidden": f0["x1_c2_to_c0_forbidden"],
            "f2b_has_C0_to_C2_entailment_row": c0_c2_row,
            "f2b_bad_converse_entailment_rows": bad_rows,
            "subsumption_note_direction_ok": note_ok,
        },
        [f"schemas/af_scc_c0_vacuum.yaml#{f2b['sha256'][:12]}",
         f"research_map/formulation_taxonomy.yaml#{f0['sha256'][:12]}"],
    )

    b = f2b["f0_binding"]
    decl_f0_ok = b.get("declared_f0_sha256") == f0["sha256"]
    ce_pin_ok = b.get("consistency_evidence_sha256") == ce["sha256"] == frozen["ce_pin"]
    add(
        "P9",
        "f0_binding_evidence_pins_current",
        decl_f0_ok and ce_pin_ok,
        {
            "declared_f0_sha256": b.get("declared_f0_sha256"),
            "measured_f0_sha256": f0["sha256"],
            "declared_f0_ok": decl_f0_ok,
            "declared_consistency_evidence_sha256": b.get("consistency_evidence_sha256"),
            "measured_consistency_evidence_sha256": ce["sha256"],
            "frozen_consistency_evidence_pin": frozen["ce_pin"],
            "consistency_evidence_pin_ok": ce_pin_ok,
        },
        [f"schemas/af_scc_c0_vacuum.yaml#{f2b['sha256'][:12]}",
         f"artifacts/formulation/evidence/taxonomy_consistency.json#{ce['sha256'][:12]}",
         f"artifacts/formulation/FROZEN.json#rev{frozen['revision']}"],
    )
    return out


CHECK_IDS = [f"P{i}" for i in range(1, 10)]


def status_map(results: list) -> dict:
    return {r["id"]: r["status"] for r in results}


def run_selftest(live_view: dict) -> dict:
    baseline = status_map(checks(live_view))
    expected_baseline = {
        "P1": "pass", "P2": "pass", "P3": "pass", "P4": "fail", "P5": "fail",
        "P6": "fail", "P7": "pass", "P8": "pass", "P9": "fail",
    }

    def mutate(fn):
        v = copy.deepcopy(live_view)
        fn(v)
        return v

    mutants = [
        ("m1_conclusion_uses_F0_alias_form",
         lambda v: v["f2b"].update(conclusion_type=ALIAS_C0),
         {"P4": "pass", "P7": "pass"}),
        ("m2_conclusion_crosses_to_C2_token",
         lambda v: v["f2b"].update(conclusion_type="scc_c2_future_inextendibility"),
         {"P3": "fail", "P7": "fail"}),
        ("m3_conclusion_uses_merged_ambiguous_token",
         lambda v: v["f2b"].update(conclusion_type=MERGED_TOKEN),
         {"P3": "fail", "P4": "fail", "P7": "fail"}),
        ("m4_alias_companion_bound",
         lambda v: (v["f2b"].update(alias_refs=[{"key": "vocabulary_aliases_ref",
                                                "value": "artifacts/formulation/VOCAB_ALIASES.json",
                                                "sha256": v["alias"]["sha256"]}]),
                    v["f2b"]["sha256s"].append(v["alias"]["sha256"])),
         {"P6": "pass"}),
        ("m5_genericity_uses_F0_alias_form",
         lambda v: v["f2b"].update(genericity_kind="baire_residual"),
         {"P5": "pass"}),
        ("m6_consistency_evidence_pin_refreshed",
         lambda v: v["f2b"]["f0_binding"].update(consistency_evidence_sha256=v["ce"]["sha256"]),
         {"P9": "pass"}),
        ("m7_converse_entailment_injected",
         lambda v: v["f2b"]["entailments"].append(
             {"from": "no proper future C2 extension", "to": "this class", "relation": "entails"}),
         {"P8": "fail"}),
        ("m8_measured_hash_drifted",
         lambda v: v["f2b"].update(sha256="0" * 64),
         {"P1": "fail"}),
        ("m9_regularity_token_swapped_to_C2",
         lambda v: v["f2b"]["components"].update(regularity_token="C2"),
         {"P2": "fail"}),
    ]

    rows = []
    for name, fn, expected_flips in mutants:
        observed = status_map(checks(mutate(fn)))
        flips = {cid: observed[cid] for cid in expected_flips}
        ok = all(observed[cid] == st for cid, st in expected_flips.items())
        rows.append({"mutant": name, "expected_flips": expected_flips, "observed": flips, "pass": ok})

    # degenerate reference controls
    all_pass = {cid: "pass" for cid in CHECK_IDS}
    all_fail = {cid: "fail" for cid in CHECK_IDS}
    accept_control_ok = all_pass != baseline and all_pass != status_map(checks(live_view))
    discriminate = sorted({cid for _, _, exp in mutants for cid in exp})

    return {
        "schema": "f2b-vocab-binding-selftest/v1",
        "baseline": baseline,
        "baseline_expected": expected_baseline,
        "baseline_matches_expected": baseline == expected_baseline,
        "mutants": rows,
        "mutants_all_pass": all(r["pass"] for r in rows),
        "degenerate_controls": {
            "always_accept_equals_baseline": all_pass == baseline,
            "always_reject_equals_baseline": all_fail == baseline,
            "note": "a checker with no discriminating power would equal the baseline in one of these; the live baseline is neither all-pass nor all-fail",
        },
        "discriminating_checks": discriminate,
        "all_checks_discriminated": discriminate == CHECK_IDS,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="write report.json and selftest.json")
    ap.add_argument("--selftest", action="store_true", help="run controls and print them")
    ap.add_argument("--measured-at", default=None)
    args = ap.parse_args(argv)

    measured_at = args.measured_at or __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
    view = build_view(measured_at)
    results = checks(view)
    smap = status_map(results)
    hard_failures = [f"HF-W005-F2V-{r['id']}" for r in results if r["status"] == "fail"]

    report = {
        "schema": "f2b-vocab-binding-report/v1",
        "task_id": "W005-F2B-VOCAB-BIND-01",
        "class_id": CLASS_ID,
        "node_id": "F2b",
        "gate": "G-FORM",
        "actor": "worker-005",
        "measured_at": measured_at,
        "instrument": "artifacts/worker-005/f2b_vocab_binding/check_f2b_vocab_binding.py",
        "pins": {
            "schemas/af_scc_c0_vacuum.yaml": view["f2b"]["sha256"],
            "research_map/formulation_taxonomy.yaml": view["f0"]["sha256"],
            "artifacts/formulation/VOCAB_ALIASES.json": view["alias"]["sha256"],
            "artifacts/formulation/evidence/taxonomy_consistency.json": view["ce"]["sha256"],
            "artifacts/formulation/FROZEN.json": {"revision": view["frozen"]["revision"],
                                                  "f2b_pin": view["frozen"]["f2b_pin"],
                                                  "ce_pin": view["frozen"]["ce_pin"]},
        },
        "checks": results,
        "status_map": smap,
        "verdict": None,
        "hard_failures": hard_failures,
        "findings": [],
        "falsifier": None,
        "authority": "worker event; cannot set status=done, validation_status=passed, or a gate verdict",
        "scope_limits": "structural/evidence binding only; no mathematics is decided; read-only on canonical artifacts",
    }

    p_fail = [r for r in results if r["status"] == "fail"]
    if not p_fail:
        report["verdict"] = "vocab_binding_pass"
    elif any(r["id"] in {"P3", "P7", "P8"} and r["status"] == "fail" for r in p_fail):
        report["verdict"] = "class_separation_fail"
    else:
        report["verdict"] = "literal_vocab_binding_fail__no_class_leakage"

    report["findings"] = [
        {
            "id": f"F-W005-F2V-{r['id']}",
            "check": r["id"],
            "severity": "major" if r["id"] in {"P3", "P4", "P6", "P7", "P8"} else "minor",
            "statement": r["title"],
            "detail": r["detail"],
        }
        for r in p_fail
    ]
    report["falsifier"] = (
        "Re-run after any write: if P4 and P5 flip to pass because the F0 allowed-lists gained the "
        "VOCAB_ALIASES canonical tokens (or F2b switched to the F0 alias forms), and P6 flips because "
        "F2b binds artifacts/formulation/VOCAB_ALIASES.json at its measured sha256, and P9 flips because "
        "f0_binding.consistency_evidence_sha256 equals the frozen pin, then this report is superseded. "
        "If instead P3 or P7 turns fail, the no-leakage half is falsified and the finding is class-level."
    )

    if args.selftest or args.report:
        st = run_selftest(view)
        report["controls"] = {
            "baseline_matches_expected": st["baseline_matches_expected"],
            "mutants_all_pass": st["mutants_all_pass"],
            "all_checks_discriminated": st["all_checks_discriminated"],
        }
        if args.report:
            outdir = Path(__file__).resolve().parent
            (outdir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            (outdir / "selftest.json").write_text(json.dumps(st, indent=2, sort_keys=True) + "\n")
        if args.selftest:
            print(json.dumps(st, indent=2, sort_keys=True))

    if not args.report and not args.selftest:
        print(json.dumps({"verdict": report["verdict"], "status_map": smap,
                          "hard_failures": hard_failures}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
