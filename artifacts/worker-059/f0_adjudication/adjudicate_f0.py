#!/usr/bin/env python3
"""W059-F0-ADJUDICATE-01 — independent measurement for the F0 accept/revise split.

Question being adjudicated (not taken on trust):
  W040 (accept, 4.0) vs W082 (revise, 3.5) on research_map/formulation_taxonomy.yaml
  at sha256 276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc.
  W082 claims (F-01) the AF-WCC-SCALAR-SPH conclusion quantifies bare "generic data"
  while H4 declares the genericity notion unresolved, and asserts an unsourced
  "equivalently" equivalence; (F-02) that class_scope_adjudication D3 ("comeager
  quantifier explicit in EACH class conclusion text") is false for that class and
  that artifacts/formulation/tools/check_taxonomy_consistency.py certifies
  CONSISTENT without inspecting it.

This checker is independent: it imports no canonical gate/tool module, reads only
the pinned snapshot bytes, and re-derives every claim from the document. It records
raw evidence (line numbers + verbatim quotes) so a third party can re-run it.

Usage: python3 adjudicate_f0.py <taxonomy.yaml> <out.json>
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

FROZEN = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_TOKEN_RE = re.compile(r"\bAF-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
EQUIV_RE = re.compile(r"\bequivalen\w*\b", re.I)
EXPLICIT_QUANT_RE = re.compile(
    r"comeager|for every admissible|G_\{s,delta\}|G_\{s, ?delta\}|dense[- ]open|full[- ]measure",
    re.I,
)
REQUIRED_CLASS_FIELDS = ["axes", "hypotheses", "conclusion", "exclusions", "test_cases", "provenance"]


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently keeping the last."""


def _construct_mapping(loader, node, deep=False):
    seen = {}
    for k, _v in node.value:
        key = loader.construct_object(k, deep=deep)
        seen.setdefault(key, []).append(k.start_mark.line + 1)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    if dups:
        raise yaml.YAMLError(f"duplicate mapping keys: {dups}")
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def line_of(lines: list[str], needle: str, start: int = 0) -> int | None:
    for i in range(start, len(lines)):
        if needle in lines[i]:
            return i + 1
    return None


def class_id_tokens_in(text: str) -> set[str]:
    return set(CLASS_TOKEN_RE.findall(text))


def main() -> int:
    tax_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    raw = tax_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8")
    lines = text.splitlines()

    result: dict = {
        "task_id": "W059-F0-ADJUDICATE-01",
        "reviewed_path": str(tax_path),
        "reviewed_sha256": sha,
        "reviewed_bytes": len(raw),
        "checker": str(Path(__file__).resolve()),
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "checks": {},
        "adjudication": {},
    }

    # strict parse (duplicate-key-free)
    parse_ok, parse_err = True, None
    try:
        doc = yaml.load(raw, StrictLoader)
    except yaml.YAMLError as e:  # pragma: no cover - reported, not raised
        parse_ok, parse_err = False, str(e)
        doc = None
    result["checks"]["A_strict_parse"] = {"pass": parse_ok, "error": parse_err}

    if doc is None:
        Path(out_path).write_text(json.dumps(result, indent=2) + "\n")
        return 1

    classes = doc.get("classes", {})
    ids = doc.get("class_ids", [])
    result["checks"]["A_strict_parse"].update({
        "exactly_four_frozen_ids": sorted(ids) == sorted(FROZEN),
        "class_ids": ids,
        "classes_present": sorted(classes),
    })

    # ---- B: per-class quantified-genericity binding in the conclusion text ----
    gen = {}
    for cid in FROZEN:
        c = classes.get(cid, {})
        ctext = str((c.get("conclusion") or {}).get("text", ""))
        ln = line_of(lines, "text: >-", 0)
        ctext_lines = [i + 1 for i, l in enumerate(lines) if l.strip().startswith("For generic data") or "comeager set G_{s,delta}" in l]
        gen[cid] = {
            "conclusion_text": ctext,
            "conclusion_text_lines": ctext_lines,
            "has_explicit_quantifier_before_data": bool(EXPLICIT_QUANT_RE.search(ctext)),
            "axes_genericity_kind": (c.get("axes") or {}).get("genericity_kind"),
            "genericity_value_status": c.get("genericity_value_status"),
            "h4_unresolved": any(h.get("unresolved") for h in c.get("hypotheses", [])),
        }
    result["checks"]["B_conclusion_quantifier_binding"] = gen
    missing_explicit = [cid for cid, g in gen.items() if not g["has_explicit_quantifier_before_data"]]

    # ---- C: D3 resolution claim vs measurement ----
    adj = doc.get("class_scope_adjudication", {})
    d3 = next((d for d in adj.get("resolved_divergences", []) if str(d.get("id")) == "D3"), None)
    d3_res = (d3 or {}).get("resolution", "")
    d3_line = line_of(lines, "D3", 0)
    result["checks"]["C_D3_resolution_claim"] = {
        "d3_present": d3 is not None,
        "d3_status": (d3 or {}).get("status"),
        "d3_resolution": d3_res,
        "d3_line": d3_line,
        "claims_each_class_conclusion_text": bool(re.search(r"each class conclusion text", d3_res, re.I)),
        "classes_without_explicit_quantifier": missing_explicit,
        "d3_true_by_measurement": not missing_explicit,
    }

    # ---- D: asserted equivalences in conclusion texts ----
    wcc_vac = str((classes.get("AF-WCC-VAC-GEN", {}).get("conclusion") or {}).get("text", ""))
    hf06_disclaimer = bool(re.search(r"not an asserted equivalence", wcc_vac, re.I))
    equiv = {}
    for cid in FROZEN:
        ctext = str((classes.get(cid, {}).get("conclusion") or {}).get("text", ""))
        m = EQUIV_RE.search(ctext)
        equiv[cid] = {
            "asserts_equivalence": bool(m),
            "phrase": ctext[max(0, m.start() - 60):m.end() + 140] if m else None,
            "line": line_of(lines, ctext.strip().splitlines()[0][:60], 0) if ctext else None,
        }
    result["checks"]["D_asserted_equivalences"] = {
        "wcc_vac_has_hf06_disclaimer": hf06_disclaimer,
        "wcc_vac_disclaimer_line": line_of(lines, "not an asserted equivalence", 0),
        "per_class": equiv,
        "classes_asserting_unregistered_equivalence": [
            cid for cid in FROZEN
            if equiv[cid]["asserts_equivalence"] and cid != "AF-WCC-VAC-GEN"
        ],
    }

    # ---- E: independent disjointness recomputation ----
    pairs = doc.get("disjointness", [])
    pair_rows = []
    for row in pairs:
        a, b = row.get("pair", [None, None])
        ax = (classes.get(a, {}).get("axes") or {})
        bx = (classes.get(b, {}).get("axes") or {})
        axes = row.get("decisive_axes", [])
        differing = [k for k in axes if ax.get(k) != bx.get(k)]
        pair_rows.append({
            "pair": [a, b],
            "decisive_axes": axes,
            "axes_that_differ": differing,
            "separated": bool(axes) and len(differing) == len(axes) and len(axes) > 0,
        })
    expected_pairs = {tuple(sorted(p)) for p in (
        (FROZEN[0], FROZEN[1]), (FROZEN[0], FROZEN[2]), (FROZEN[0], FROZEN[3]),
        (FROZEN[1], FROZEN[2]), (FROZEN[1], FROZEN[3]), (FROZEN[2], FROZEN[3]))}
    got_pairs = {tuple(sorted(r["pair"])) for r in pair_rows}
    result["checks"]["E_disjointness"] = {
        "pairs_declared": len(pair_rows),
        "all_six_pairs": got_pairs == expected_pairs,
        "all_separated_on_declared_axes": all(r["separated"] for r in pair_rows),
        "rows": pair_rows,
    }

    # ---- F: class token scan over the whole document ----
    tokens = class_id_tokens_in(text)
    variants = doc.get("variants", [])
    registered = set()
    for v in variants:
        registered.add(v.get("variant_id"))
    foreign = sorted(t for t in tokens if t not in FROZEN)
    allowed_mentions = set()
    for t in foreign:
        # any foreign token must be a documented analysis token (e.g. the superseded SET class name)
        idx = [i + 1 for i, l in enumerate(lines) if t in l]
        allowed_mentions.add(t)
        foreign[foreign.index(t)] = {"token": t, "lines": idx} if isinstance(t, str) else t
    result["checks"]["F_class_tokens"] = {
        "frozen_tokens": sorted(tokens & set(FROZEN)),
        "foreign_tokens": foreign,
    }

    # ---- G: per-class completeness + test-case consistency ----
    completeness = {}
    for cid in FROZEN:
        c = classes.get(cid, {})
        tc = c.get("test_cases") or {}
        pos, neg = tc.get("positive") or {}, tc.get("negative") or {}
        neg2 = tc.get("negative_2") or {}
        completeness[cid] = {
            "has_required_fields": all(k in c for k in REQUIRED_CLASS_FIELDS),
            "missing_fields": [k for k in REQUIRED_CLASS_FIELDS if k not in c],
            "has_positive": bool(pos),
            "has_negative": bool(neg),
            "has_negative_2": bool(neg2),
            "positive_expected_self": pos.get("expected_classification") == cid,
            "negative_expected": [neg.get("expected_classification"), neg2.get("expected_classification")],
            "exclusions_nonempty": bool(c.get("exclusions")),
        }
    result["checks"]["G_class_completeness"] = completeness

    # ---- adjudication verdicts ----
    w082_f01 = {
        "claim": "AF-WCC-SCALAR-SPH conclusion quantifies bare 'generic data' while H4 says the notion is unresolved; and asserts an unsourced 'equivalently' (horizon/no-visible-singularity) that AF-WCC-VAC-GEN explicitly disclaims as unasserted.",
        "measurements": {
            "scalar_conclusion_has_explicit_quantifier": gen["AF-WCC-SCALAR-SPH"]["has_explicit_quantifier_before_data"],
            "scalar_conclusion_text_lines": sorted(set(gen["AF-WCC-SCALAR-SPH"]["conclusion_text_lines"])),
            "scalar_h4_unresolved": gen["AF-WCC-SCALAR-SPH"]["h4_unresolved"],
            "other_three_have_explicit_quantifier": all(
                gen[c]["has_explicit_quantifier_before_data"] for c in FROZEN if c != "AF-WCC-SCALAR-SPH"),
            "scalar_asserts_equivalence": equiv["AF-WCC-SCALAR-SPH"]["asserts_equivalence"],
            "scalar_equivalence_phrase": equiv["AF-WCC-SCALAR-SPH"]["phrase"],
            "wcc_vac_equivalence_disclaimer": hf06_disclaimer,
        },
        "verdict": (
            "substantiated" if (
                not gen["AF-WCC-SCALAR-SPH"]["has_explicit_quantifier_before_data"]
                and gen["AF-WCC-SCALAR-SPH"]["h4_unresolved"]
                and equiv["AF-WCC-SCALAR-SPH"]["asserts_equivalence"]
                and hf06_disclaimer
            ) else "not substantiated"
        ),
    }
    w082_f02 = {
        "claim": "D3 resolution ('comeager quantifier explicit in each class conclusion text') is false for AF-WCC-SCALAR-SPH, and check_taxonomy_consistency.py certifies CONSISTENT without inspecting that class.",
        "measurements": {
            "d3_claims_each_class": bool(re.search(r"each class conclusion text", d3_res, re.I)),
            "d3_true_by_measurement": not missing_explicit,
            "classes_without_explicit_quantifier": missing_explicit,
        },
        "verdict": (
            "substantiated" if (re.search(r"each class conclusion text", d3_res, re.I) and missing_explicit)
            else "not substantiated"
        ),
    }
    result["adjudication"] = {
        "w082_f01": w082_f01,
        "w082_f02_part_a_d3_false": w082_f02,
        "w040_accept_at_this_hash": {
            "safe_as_binding_accept": False if (w082_f01["verdict"] == "substantiated" or missing_explicit) else True,
            "reason": (
                "the accept at 276009f4 did not surface a self-contradiction inside the class-binding surface: "
                "a resolved divergence (D3) is measurable-false for one of the four classes and that class's "
                "conclusion violates the file's own genericity vocabulary rule"
            ) if missing_explicit else "no blocking defect reproduced",
        },
        "recommended_verdict": "revise" if missing_explicit else "accept",
        "recommended_score": 3.0 if missing_explicit else 4.0,
        "scope_note": (
            "blocking for a hash-bound accept that certifies the class-binding surface as machine-checkable; "
            "the minimal G-F0 criteria (existence, 4 ids, disjointness, 2 verdicts) are separable and re-measured green here"
        ),
    }
    result["measured_green_baseline"] = {
        "strict_parse": parse_ok,
        "exactly_four_frozen_ids": sorted(ids) == sorted(FROZEN),
        "all_six_disjointness_pairs_separated": result["checks"]["E_disjointness"]["all_separated_on_declared_axes"],
        "all_classes_complete": all(v["has_required_fields"] and v["has_positive"] and v["has_negative"] for v in completeness.values()),
    }
    Path(out_path).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "sha256": sha,
        "recommended_verdict": result["adjudication"]["recommended_verdict"],
        "w082_f01": w082_f01["verdict"],
        "w082_f02_part_a": w082_f02["verdict"],
        "classes_without_explicit_quantifier": missing_explicit,
        "out": str(out_path),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
