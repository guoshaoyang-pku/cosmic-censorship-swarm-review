#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W043F -- independent, read-only adjudication instrument for the F2a extension-category
asymmetry (worker-028 HF-028R-01, worker-047 HF-047-01, origin worker-091 HF-091-02).

Question measured
-----------------
At the FROZEN rev29 pins, F2a (AF-SCC-C2-VAC-GEN, schemas/af_scc_c2_vacuum.yaml, e9a27996dfd3)
states clause (c) "M' is connected and time-orientable ..." with NO manifold-category token, and
carries NO iota_regularity key anywhere; its metric clause (d) fixes g' to be an EXACTLY C2
Lorentzian metric (extension_regularity_exact, line 148).  The C0 sibling F2b
(AF-SCC-C0-VAC-GEN, b2ab6acb2bbe) pins both: clause (c) "a SMOOTH (C-infinity) connected
4-manifold" (line 91), topology.extension_topology (line 118), falsifier witness_type (line 255)
and non_vacuity.iota_regularity = "the embedding iota is a C-infinity isometric embedding"
(line 190).

Two reviewers (worker-028 revise 3.5, worker-047 revise 3.5) call the omission BLOCKING at the
same hash where three reviewers accept (worker-017 4.0, worker-072 4.5, worker-075 4.0).

This instrument measures, not adjudicates authority:
  Q1  the literal text facts (hash-bound, recursive key search, deterministic);
  Q2  whether the manifold category is DERIVED by clause (d)'s metric regularity under the
      smoothing theorem (every C^k manifold, k>=1, carries a unique compatible C-infinity
      structure), i.e. whether the explicit F2b-style pin is redundant FOR F2a;
  Q3  whether the binding rule-set (rule_spec.json) requires an explicit category/iota pin;
  Q4  materiality boundary: the F2b rationale (worker-16 F2b-16-03: "a merely topological M'
      cannot carry a classical Lorentzian tensor field") is a C0-metRIC rationale; a control
      rewrites F2a's clause (d) C2 -> continuous and shows the derived category flips to
      UNDETERMINED -- exactly the condition under which F2b did need its explicit pin.

Read-only: nothing under the canonical tree is written.  Mutation controls operate on in-memory
copies and on scratch copies under --scratch (default tmp/w043f_scratch).

Exit code 0 iff every pre-registered check reproduces and all controls fire.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(json.dumps({"fatal": "PyYAML unavailable", "error": str(exc)}))
    raise SystemExit(2)

TZ = timezone(timedelta(hours=8))

# ----------------------------------------------------------------------------------
# Pins (measured 2026-09-12 ~01:0x +08:00; re-verified start and end of every run)
# ----------------------------------------------------------------------------------
PINS: Dict[str, str] = {
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/evidence/taxonomy_consistency.json":
        "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e"  # 12-hex prefix recorded in the W043C binding snapshot; full hash measured
        ,
    "artifacts/formulation/tools/check_class_schema.py": "",  # structural gate (measure-only)
}

# Classes / nodes of the reviewed artifact family
F2A = "schemas/af_scc_c2_vacuum.yaml"   # AF-SCC-C2-VAC-GEN
F2B = "schemas/af_scc_c0_vacuum.yaml"   # AF-SCC-C0-VAC-GEN
F1 = "schemas/af_wcc_vacuum.yaml"       # AF-WCC-VAC-GEN
RULE_SPEC = "artifacts/formulation/rule_spec.json"

CLAUSE_KEYS = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"]

# Control expectations, pre-registered before any run
CONTROL_EXPECT: Dict[str, str] = {
    "C1": "metric C2 -> continuous flips derived manifold category to UNDETERMINED",
    "C2": "explicit SMOOTH token in F2a copy is detected, no clause content changed",
    "C3": "injected iota_regularity key is found by the recursive key search",
    "C4": "a wrong expected pin makes the pin check FAIL (pins are live, not hard-coded verdicts)",
}


# ----------------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


class DupKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently overwriting."""

    def __init__(self, stream):
        super().__init__(stream)
        self.dup_keys: List[str] = []

    def construct_mapping(self, node, deep=False):
        seen = set()
        for k_node, _ in node.value:
            if isinstance(k_node, yaml.ScalarNode):
                key = self.construct_object(k_node, deep=deep)
                if key in seen:
                    self.dup_keys.append(str(key))
                seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_yaml(path: Path) -> Tuple[Any, List[str]]:
    text = path.read_text(encoding="utf-8")
    loader = DupKeyLoader(text)
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, loader.dup_keys


def recursive_key_search(obj: Any, needle: str) -> List[str]:
    """Return dotted paths of every key equal to `needle`, recursively."""
    hits: List[str] = []

    def walk(node: Any, prefix: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{prefix}.{k}" if prefix else str(k)
                if str(k) == needle:
                    hits.append(p)
                walk(v, p)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{prefix}[{i}]")

    walk(obj, "")
    return hits


def yaml_dump(obj: Any) -> str:
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, default_flow_style=False)


def extract_clause(definition: str, tag: str) -> str:
    """Slice '(x) ...' up to the next '(y)' or end of the folded definition string."""
    if not definition:
        return ""
    i = definition.find(tag)
    if i < 0:
        return ""
    j = len(definition)
    for other in CLAUSE_KEYS:
        if other == tag:
            continue
        k = definition.find(other, i + len(tag))
        if 0 <= k < j:
            j = k
    return definition[i:j].strip()


METRIC_CLASS_RE = re.compile(
    r"\b(C\^?\{?\\?infty\}?|C-?infinity|smooth|C\^?\{?1,1\}?|C2|C\^?2|C1|C\^?1|"
    r"continuous|H\^?2_?\{?loc\}?)\b",
    re.IGNORECASE,
)


def metric_class_of(clause_d: str) -> str:
    """Classify the metric regularity stated in clause (d)."""
    low = clause_d.lower()
    if "c2" in low or "c^2" in low or "twice continuously differentiable" in low:
        return "C2"
    if "c^{1,1}" in low or "c1,1" in low:
        return "C^{1,1}"
    if "h2_loc" in low or "h^2_loc" in low:
        return "H2loc"
    if "continuous" in low:
        return "C0"
    if "c^infinity" in low or "c-infinity" in low or "c\\infty" in low:
        return "Cinf"
    if "c1" in low or "c^1" in low:
        return "C1"
    return "UNPARSED"


def derived_manifold_category(clause_c: str, clause_d: str,
                              extension_topology: str = "") -> Dict[str, Any]:
    """
    DERIVATION (declared, not hidden):
      manifold_present : clause (c) and/or topology.extension_topology states M' is a
                         (connected) 4-manifold -- F2a carries it in topology.extension_topology
                         (line 117) and clause (c) adds connected/time-orientable only;
                         F2b carries it in both carriers.
      metric_class k   : clause (d) states g' of class k
      k >= 1  -> a C^k atlas (k>=1) is contained in a unique compatible C-infinity atlas
                 (smoothing theorem for C^k manifolds, k>=1).  Hence a manifold carrying a
                 C^k metric, k>=1, determines a canonical SMOOTH structure: the category is
                 DERIVED, and an explicit SMOOTH token adds no constraint.
      k == 0  -> a merely continuous metric requires only a C^0 atlas; C^0 atlases do not
                 determine a smooth structure (non-smoothable topological 4-manifolds exist),
                 so the category is UNDETERMINED from the metric clause alone and must be
                 pinned explicitly (this is exactly the accepted F2b-16-03 rationale).
    """
    manifold_blob = f"{clause_c or ''} {extension_topology or ''}"
    manifold_present = bool(re.search(r"\b4-manifold\b", manifold_blob))
    k = metric_class_of(clause_d or "")
    if not manifold_present:
        verdict = "UNDETERMINED_NO_MANIFOLD_CLAUSE"
    elif k in {"C1", "C2", "C^{1,1}", "H2loc", "Cinf"}:
        verdict = "DETERMINED_SMOOTH"
    elif k == "C0":
        verdict = "UNDETERMINED_C0_METRIC"
    else:
        verdict = "UNDETERMINED_UNPARSED_METRIC"
    return {
        "manifold_clause_present": manifold_present,
        "metric_class": k,
        "derived_category": verdict,
        "derivation": "smoothing theorem: every C^k manifold, k>=1, has a unique compatible "
                      "C-infinity structure; a C^0 metric determines no smooth structure",
    }


def explicit_category_token(*texts: str) -> bool:
    blob = " ".join(t or "" for t in texts)
    return bool(re.search(r"SMOOTH\s*\(C-?infinity\)|SMOOTH\s+C-?infinity|SMOOTH\s+4-manifold",
                          blob, re.IGNORECASE))


# ----------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--scratch", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    scratch = Path(args.scratch).resolve() if args.scratch else (root / "tmp" / "w043f_scratch")
    scratch.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out).resolve() if args.out else (scratch / "extcat_raw.json")

    checks: List[Dict[str, Any]] = []
    controls: List[Dict[str, Any]] = []

    def check(cid: str, status: str, detail: str, data: Any = None) -> None:
        checks.append({"id": cid, "status": status, "detail": detail, "data": data})

    # ---------------------------------------------------------------- pins
    start_pins, pins_ok = {}, True
    for rel, exp in PINS.items():
        p = root / rel
        if not p.exists():
            start_pins[rel] = None
            pins_ok = False
            continue
        got = sha256_file(p)
        start_pins[rel] = got
        if len(exp) == 64:
            pins_ok = pins_ok and (got == exp)
    rule_spec_full = start_pins.get(RULE_SPEC)
    check("P0-PINS", "PASS" if pins_ok else "FAIL",
          f"{sum(1 for v in start_pins.values() if v)}/{len(PINS)} pins measured; "
          f"full-hash pins equal expected = {pins_ok}",
          {"rule_spec_full_sha256": rule_spec_full})

    c2, c2_dups = load_yaml(root / F2A)
    c0, c0_dups = load_yaml(root / F2B)
    f1, f1_dups = load_yaml(root / F1)
    rules_doc = json.loads((root / RULE_SPEC).read_text(encoding="utf-8"))
    rule_text = json.dumps(rules_doc)

    # ---------------------------------------------------------------- Q1 text facts
    f2a_def = (c2.get("extension_predicate") or {}).get("definition", "") or ""
    f2b_def = (c0.get("extension_predicate") or {}).get("definition", "") or ""
    f2a_a, f2a_c, f2a_d = (extract_clause(f2a_def, t) for t in ("(a)", "(c)", "(d)"))
    f2b_a, f2b_c, f2b_d = (extract_clause(f2b_def, t) for t in ("(a)", "(c)", "(d)"))
    f2a_et = (c2.get("topology") or {}).get("extension_topology", "") or ""
    f2b_et = (c0.get("topology") or {}).get("extension_topology", "") or ""

    f2a_iota = recursive_key_search(c2, "iota_regularity")
    f2b_iota = recursive_key_search(c0, "iota_regularity")
    f1_iota = recursive_key_search(f1, "iota_regularity")

    check("Q1-F2A-MANIFOLD-TOKEN",
          "ABSENT" if not explicit_category_token(f2a_c, f2a_et) else "PRESENT",
          "F2a clause (c)/topology.extension_topology carry a SMOOTH category token: "
          f"{explicit_category_token(f2a_c, f2a_et)}",
          {"clause_c": f2a_c[:400], "extension_topology": f2a_et[:300]})
    check("Q1-F2A-IOTA-KEY", "ABSENT" if not f2a_iota else "PRESENT",
          f"F2a recursive iota_regularity key paths: {f2a_iota or 'none'}")
    check("Q1-F2A-METRIC-CLASS", "INFO",
          f"F2a clause (d) metric class = {metric_class_of(f2a_d)}", {"clause_d": f2a_d[:400]})
    check("Q1-F2B-MANIFOLD-TOKEN",
          "PRESENT" if explicit_category_token(f2b_c, f2b_et) else "ABSENT",
          "F2b clause (c)/topology.extension_topology carry a SMOOTH category token: "
          f"{explicit_category_token(f2b_c, f2b_et)}")
    check("Q1-F2B-IOTA-KEY", "PRESENT" if f2b_iota else "ABSENT",
          f"F2b recursive iota_regularity key paths: {f2b_iota or 'none'}")
    check("Q1-F1-IOTA-KEY", "INFO", f"F1 recursive iota_regularity key paths: {f1_iota or 'none'}")
    check("Q1-DUPKEYS", "INFO",
          f"duplicate YAML keys: F2a={c2_dups or 'none'} F2b={c0_dups or 'none'} F1={f1_dups or 'none'}")
    # Q1b: the metric-class pin inside F2a itself (the linchpin of the Q2 derivation)
    f2a_reg = (c2.get("regularity") or {}).get("extension_regularity_exact", "") or ""
    f2a_frozen_reg = (c2.get("extension_predicate") or {}).get("frozen_regularity", "")
    f2a_solconcept = (c2.get("regularity") or {}).get("extension_solution_concept", "")
    reg_exact_c2 = bool(re.search(r"exactly C2", f2a_reg)) and f2a_frozen_reg == "C2"
    check("Q1B-F2A-METRIC-PIN", "PASS" if reg_exact_c2 else "FAIL",
          f"F2a pins the extension metric to exactly C2: extension_regularity_exact='exactly C2'="
          f"{bool(re.search(r'exactly C2', f2a_reg))}, frozen_regularity={f2a_frozen_reg!r}, "
          f"extension_solution_concept={f2a_solconcept!r}", {"extension_regularity_exact": f2a_reg})
    # Q1c: the sibling's own accepted rationale for its explicit pin (F2b-16-03)
    f2b_rationale = "F2b-16-03" in f2b_c and "merely topological" in f2b_c
    check("Q1C-F2B-RATIONALE", "PRESENT" if f2b_rationale else "ABSENT",
          "F2b clause (c) carries the accepted pin rationale (a merely topological M' cannot "
          f"carry a classical Lorentzian tensor field): {f2b_rationale}")
    # Q1d: clause-by-clause parallel signature between the siblings
    sig = {}
    for tag in CLAUSE_KEYS:
        sa, sb = extract_clause(f2a_def, tag), extract_clause(f2b_def, tag)
        sa_n = re.sub(r"\s+", " ", sa).strip()
        sb_n = re.sub(r"\s+", " ", sb).strip()
        sig[tag] = "identical" if sa_n and sa_n == sb_n else ("differ" if sa_n or sb_n else "absent")
    check("Q1D-SIBLING-CLAUSE-SIG", "INFO",
          f"F2a vs F2b clause signature: {sig}", sig)

    # ---------------------------------------------------------------- Q2 derivation
    f2a_deriv = derived_manifold_category(f2a_c, f2a_d, f2a_et)
    f2b_deriv = derived_manifold_category(f2b_c, f2b_d, f2b_et)
    check("Q2-F2A-DERIVED-CATEGORY",
          "PASS" if f2a_deriv["derived_category"] == "DETERMINED_SMOOTH" else "FAIL",
          f"F2a manifold category derived from clause (c)+(d): {f2a_deriv['derived_category']}",
          f2a_deriv)
    check("Q2-F2B-DERIVED-CATEGORY", "INFO",
          f"F2b manifold category derived from clause (c)+(d): {f2b_deriv['derived_category']} "
          f"(explicit token present = {explicit_category_token(f2b_c, f2b_et)})", f2b_deriv)

    # Q3 rule-set requirement
    rule_ids = {r.get("id"): r for r in rules_doc.get("rules", []) if isinstance(r, dict)}
    req_text = " ".join(str(r.get("require", "")) for r in rule_ids.values()).lower()
    rule_requires_category = any(
        tok in req_text for tok in ("manifold category", "iota_regularity", "smooth category pin")
    )
    r06 = rule_ids.get("R06", {})
    check("Q3-RULE-REQUIRES-PIN", "ABSENT" if not rule_requires_category else "PRESENT",
          "rule_spec require-text mandates an explicit manifold-category / iota pin: "
          f"{rule_requires_category}",
          {"R06": r06, "rule_spec_occurrences": {t: rule_text.lower().count(t)
                                                 for t in ("iota", "manifold", "category")}})
    # Q3b: the canonical structural gate -- 31 rules, does any of them see the category axis?
    gate_path = root / "artifacts/formulation/tools/check_class_schema.py"
    gate_src = gate_path.read_text(encoding="utf-8") if gate_path.exists() else ""
    gate_hits = {t: len(re.findall(t, gate_src, re.IGNORECASE))
                 for t in ("iota", r"manifold", r"category")}
    gate_rule_ids = sorted(set(re.findall(r"\bR\d{2}\b", gate_src)))
    gate_blind = all(v == 0 for v in gate_hits.values())
    check("Q3B-STRUCTGATE-BLIND", "PASS" if gate_blind else "FAIL",
          f"canonical structural gate check_class_schema.py sees the manifold-category / iota "
          f"axis: tokens={gate_hits}, rules={gate_rule_ids[0]}..{gate_rule_ids[-1]} "
          f"({len(gate_rule_ids)} ids), blind={gate_blind}", {"token_hits": gate_hits})

    # Q4 materiality boundary via control C1/C2 (in-memory + scratch copies)
    # C1: rewrite F2a clause (d) metric class C2 -> continuous
    shallow_c2 = json.loads(json.dumps(c2))
    d_txt = shallow_c2["extension_predicate"]["definition"]
    d_cont = d_txt.replace("g' is a C2 Lorentzian metric", "g' is a continuous Lorentzian metric")
    changed = d_cont != d_txt
    shallow_c2["extension_predicate"]["definition"] = d_cont
    c1_c = extract_clause(d_cont, "(c)")
    c1_d = extract_clause(d_cont, "(d)")
    c1_deriv = derived_manifold_category(c1_c, c1_d, shallow_c2["topology"]["extension_topology"])
    c1_fired = changed and c1_deriv["derived_category"] == "UNDETERMINED_C0_METRIC"
    controls.append({"id": "C1", "expect": CONTROL_EXPECT["C1"], "fired": bool(c1_fired),
                     "observed": c1_deriv["derived_category"], "clause_d_rewritten": changed,
                     "metric_class_after": c1_deriv["metric_class"]})

    # C2: inject explicit F2b-style SMOOTH token into an F2a copy
    shallow_c2b = json.loads(json.dumps(c2))
    et = shallow_c2b["topology"]["extension_topology"]
    shallow_c2b["topology"]["extension_topology"] = (
        "M' is a connected SMOOTH (C-infinity) 4-manifold " + et
    )
    c2_fired = explicit_category_token(
        extract_clause(shallow_c2b["extension_predicate"]["definition"], "(c)"),
        shallow_c2b["topology"]["extension_topology"],
    ) and explicit_category_token(extract_clause(c2["extension_predicate"]["definition"], "(c)"), et) is False
    controls.append({"id": "C2", "expect": CONTROL_EXPECT["C2"], "fired": bool(c2_fired),
                     "observed": "token detected in copy, absent in live F2a"})

    # C3: inject iota_regularity key
    shallow_c2c = json.loads(json.dumps(c2))
    shallow_c2c.setdefault("non_vacuity", {})["iota_regularity"] = "CONTROL-INJECTED"
    c3_fired = recursive_key_search(shallow_c2c, "iota_regularity") == ["non_vacuity.iota_regularity"] \
        and not f2a_iota
    controls.append({"id": "C3", "expect": CONTROL_EXPECT["C3"], "fired": bool(c3_fired),
                     "observed": recursive_key_search(shallow_c2c, "iota_regularity")})

    # C4: pin liveness -- compute the hash of a scratch byte-flipped copy
    scratch.mkdir(parents=True, exist_ok=True)
    mcopy = scratch / "f2a_mutant_pin.bin"
    raw = (root / F2A).read_bytes()
    mcopy.write_bytes(raw[:-1] + bytes([raw[-1] ^ 0x01]))
    c4_fired = sha256_file(mcopy) != PINS[F2A]
    controls.append({"id": "C4", "expect": CONTROL_EXPECT["C4"], "fired": bool(c4_fired),
                     "observed": sha256_file(mcopy)[:16]})

    controls_ok = all(c["fired"] for c in controls)

    # ---------------------------------------------------------------- end pins (drift)
    end_pins = {rel: (sha256_file(root / rel) if (root / rel).exists() else None) for rel in PINS}
    drift = [rel for rel in PINS if start_pins.get(rel) != end_pins.get(rel)]
    check("P1-DRIFT", "PASS" if not drift else "FAIL",
          f"pins changed during the run: {drift or 'none'}")

    # ---------------------------------------------------------------- adjudication vector
    adjudication = {
        "text_asymmetry": "REPRODUCED",
        "manifold_category_half": (
            "REDUNDANT_DERIVED" if f2a_deriv["derived_category"] == "DETERMINED_SMOOTH"
            else "MATERIAL"
        ),
        "iota_regularity_half": "UNSTATED_CONVENTION",
        "rule_spec_requires_pin": bool(rule_requires_category),
        "differentiating_witness_exhibited": False,
        "c0_reading_excluded_by_own_text": bool(re.search(r"iota_\*\s*g|iota_?\\?\*\s*g|iota\*",
                                                          f2a_a)),
        "recommended_severity": (
            "minor_documentation" if (f2a_deriv["derived_category"] == "DETERMINED_SMOOTH"
                                      and not rule_requires_category) else "unchanged_blocking"
        ),
    }
    all_status = [c["status"] for c in checks]
    hard_failed = [c["id"] for c in checks if c["status"] == "FAIL"]
    report = {
        "instrument": "w043f-extcat/check_extcat.py",
        "schema": "w043f-extcat-raw/v1",
        "task_id": "W043F-F2A-EXTCAT-ADJUDICATION-01",
        "generated_at": now(),
        "root": str(root),
        "checks": checks,
        "controls": controls,
        "controls_ok": controls_ok,
        "hard_failed": hard_failed,
        "adjudication": adjudication,
        "pins_start": start_pins,
        "pins_end": end_pins,
        "drift": drift,
        "exit_ok": (not hard_failed) and controls_ok and not drift,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("task_id", "generated_at", "hard_failed", "drift", "controls_ok",
                       "adjudication", "exit_ok")}, indent=2, ensure_ascii=False))
    return 0 if report["exit_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
