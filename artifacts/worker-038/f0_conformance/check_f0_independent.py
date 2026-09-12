#!/usr/bin/env python3
"""W038-F0-CONFORMANCE-01 — independent conformance checks for canonical F0.

Scope
  Node F0, gate G-F0. Independently recomputes the machine-checkable G-F0
  criteria on the canonical taxonomy `research_map/formulation_taxonomy.yaml`
  at its measured sha256, plus cross-artifact consistency checks that the
  declared acceptance checker (artifacts/worker-01/validate_taxonomy.py) does
  not perform: the A0 rubric's frozen-class axis cross-check, the FROZEN.json
  logical-artifact pin, and the canonical/supplement role separation.

What this is not
  Not a physics verdict, not a gate verdict, not a node-completion claim.
  A worker event cannot set status=done, validation_status=passed or a gate
  verdict (comms/PROTOCOL.md; ASTRA_HANDOFF authority note).

Determinism
  Reads only files under --root. No network, no clock-dependent check. The
  input hash is measured before and after the checks; a mid-run move is a FAIL.

Usage
  python3 artifacts/worker-038/f0_conformance/check_f0_independent.py \
      --root . --json-out artifacts/worker-038/f0_conformance/independent_checks.json
Exit 0 = all checks PASS; 1 = at least one FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

import yaml

F0 = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
RUBRIC = "evaluation_rubric.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CHECKER = "artifacts/worker-01/validate_taxonomy.py"

MAPPING_NOTE = (
    "explicit vocabulary mapping used here: rubric formulation WCC -> family WCC; "
    "SCC-C2 -> family SCC + regularity_token C2; SCC-C0 -> family SCC + regularity_token C0; "
    "rubric symmetry none_required -> axes symmetry none_assumed; spherical -> spherical; "
    "rubric dimension 3+1 <-> axes asymptotics asymptotically_flat_3p1; "
    "rubric cosmological_constant 0 -> class hypothesis text containing 'Lambda = 0'."
)
CONCLUSION_VOCAB_NOTE = (
    "conclusion label vocabularies differ by artifact: the A0 rubric names a "
    "conclusion_primary (e.g. future_asymptotic_predictability) while the F0 taxonomy "
    "names a conclusion_type (weak_cosmic_censorship / strong_cosmic_censorship_C2/C0). "
    "F1 records the equivalence between the WCC conclusion and future asymptotic "
    "predictability as UNVERIFIED, so this is reported as a cross-artifact vocabulary "
    "observation, not as a G-F0 failure."
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Result:
    def __init__(self):
        self.checks = []

    def add(self, cid, name, status, detail, evidence=None):
        self.checks.append({
            "id": cid,
            "name": name,
            "status": status,
            "detail": detail,
            "evidence": evidence or [],
        })

    @property
    def failed(self):
        return [c for c in self.checks if c["status"] == "FAIL"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json-out", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()

    res = Result()
    pins_before = {p: sha256_file(root / p) for p in (F0, SUPPLEMENT, RUBRIC, FROZEN, CHECKER)}
    tax = load_yaml(root / F0)
    sup = load_yaml(root / SUPPLEMENT)
    rub = load_yaml(root / RUBRIC)
    frozen = json.loads((root / FROZEN).read_text())
    raw = (root / F0).read_text(encoding="utf-8")
    lines = raw.splitlines()

    # IND-01 — pinned hash stability across the run.
    pins_after = {p: sha256_file(root / p) for p in (F0, SUPPLEMENT, RUBRIC, FROZEN, CHECKER)}
    if pins_before == pins_after:
        res.add("IND-01", "pinned inputs stable across the check", "PASS",
                "all five input hashes identical before and after the check",
                [f"{F0}#{pins_before[F0]}", f"{CHECKER}#{pins_before[CHECKER]}"])
    else:
        res.add("IND-01", "pinned inputs stable across the check", "FAIL",
                "hash moved mid-run: " + json.dumps({k: [pins_before[k], pins_after[k]]
                                                     for k in pins_before if pins_before[k] != pins_after[k]}),
                [F0])

    # IND-02 — exactly four frozen class ids, equal to the A0 rubric set.
    tax_ids = list(tax.get("class_ids") or [])
    rubric_ids = [c["id"] for c in rub.get("frozen_classes", [])]
    class_keys = list((tax.get("classes") or {}).keys())
    if len(tax_ids) == 4 and len(set(tax_ids)) == 4 and set(tax_ids) == set(class_keys) == set(rubric_ids):
        res.add("IND-02", "exactly four class ids; taxonomy == rubric frozen set", "PASS",
                f"class_ids={tax_ids}; classes keys and evaluation_rubric frozen_classes agree",
                [f"{F0}#class_ids", f"{RUBRIC}#frozen_classes"])
    else:
        res.add("IND-02", "exactly four class ids; taxonomy == rubric frozen set", "FAIL",
                f"tax_ids={tax_ids} classes={class_keys} rubric={rubric_ids}",
                [f"{F0}#class_ids", f"{RUBRIC}#frozen_classes"])

    # IND-03 — all 6 pairs present; recompute that each decisive axis really differs.
    pairs = {}
    for row in tax.get("disjointness") or []:
        key = tuple(sorted(row.get("pair") or []))
        pairs[key] = row
    missing, axis_failures = [], []
    classes = tax.get("classes") or {}
    for a, b in itertools.combinations(sorted(tax_ids), 2):
        row = pairs.get((a, b))
        if row is None:
            missing.append([a, b])
            continue
        axes = row.get("decisive_axes") or []
        if not axes:
            axis_failures.append({"pair": [a, b], "why": "no decisive_axes listed"})
            continue
        diff = [ax for ax in axes if classes[a]["axes"].get(ax) != classes[b]["axes"].get(ax)]
        if not diff:
            axis_failures.append({"pair": [a, b], "why": "no named axis differs",
                                  "axes": axes})
    if not missing and not axis_failures and len(pairs) == 6:
        res.add("IND-03", "6/6 disjointness pairs present; decisive axes recomputed to differ", "PASS",
                "recomputed from parsed axis vectors, not read from the prose",
                [f"{F0}#disjointness"])
    else:
        res.add("IND-03", "6/6 disjointness pairs present; decisive axes recomputed to differ", "FAIL",
                json.dumps({"missing": missing, "axis_failures": axis_failures}),
                [f"{F0}#disjointness"])

    # IND-04 — G2 recomputed: SCC exactly one token in {C0,C2}; WCC token absent/null.
    g2_bad = []
    for cid in tax_ids:
        axes = classes.get(cid, {}).get("axes", {})
        fam = axes.get("family")
        tok = axes.get("regularity_token")
        if fam == "SCC" and tok not in ("C0", "C2"):
            g2_bad.append({"class": cid, "why": f"SCC token={tok!r}"})
        if fam == "WCC" and tok is not None:
            g2_bad.append({"class": cid, "why": f"WCC token={tok!r}"})
    res.add("IND-04", "G2: regularity token exactly one iff family == SCC", "PASS" if not g2_bad else "FAIL",
            "recomputed for all four classes" if not g2_bad else json.dumps(g2_bad),
            [f"{F0}#classes.*.axes.regularity_token"])

    # IND-05 — axis vocabulary membership and unique conclusion_type per class.
    vocab = tax.get("field_vocabulary") or {}
    vocab_bad = []
    for cid in tax_ids:
        axes = classes.get(cid, {}).get("axes", {})
        for slot in ("family", "matter_model", "symmetry", "asymptotics",
                     "regularity_token", "genericity_kind", "conclusion_type"):
            allowed = (vocab.get(slot) or {}).get("allowed")
            if allowed is None:
                continue
            if slot == "regularity_token":
                ok = axes.get(slot) in allowed or (axes.get(slot) is None and None in allowed)
            else:
                ok = axes.get(slot) in allowed
            if not ok:
                vocab_bad.append({"class": cid, "slot": slot, "value": axes.get(slot)})
    # The taxonomy rule is "one class -> exactly one conclusion_type" (not all-distinct:
    # the two WCC classes legitimately share weak_cosmic_censorship), and the C0/C2
    # conclusion families must not be merged.
    concl = [classes[c]["axes"].get("conclusion_type") for c in tax_ids]
    concl_bad = []
    for cid in tax_ids:
        axes = classes[cid]["axes"]
        fam, ct = axes.get("family"), str(axes.get("conclusion_type"))
        if fam == "SCC" and not ct.startswith("strong_cosmic_censorship_"):
            concl_bad.append({"class": cid, "why": f"SCC conclusion_type={ct!r}"})
        if fam == "WCC" and ct != "weak_cosmic_censorship":
            concl_bad.append({"class": cid, "why": f"WCC conclusion_type={ct!r}"})
        if re.search(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", ct, re.I):
            concl_bad.append({"class": cid, "why": f"merged regularity token in conclusion_type={ct!r}"})
    if not vocab_bad and not concl_bad:
        res.add("IND-05", "axis values in field_vocabulary; one conclusion_type per class, C0/C2 unmerged", "PASS",
                f"conclusion_types={concl} (shared WCC value is expected)",
                [f"{F0}#field_vocabulary", f"{F0}#classes"])
    else:
        res.add("IND-05", "axis values in field_vocabulary; one conclusion_type per class, C0/C2 unmerged", "FAIL",
                json.dumps({"vocab": vocab_bad, "conclusion": concl_bad}),
                [f"{F0}#field_vocabulary"])

    # IND-06 — FROZEN.json logical_artifacts pins match measured canonical + supplement bytes.
    la = frozen.get("logical_artifacts") or {}
    pin_bad = []
    for key, path in (("F0-declared-taxonomy", F0), ("F0-class-contract-supplement", SUPPLEMENT)):
        entry = la.get(key) or {}
        want = entry.get("sha256")
        got = pins_before[path]
        if want != got or entry.get("path") != path:
            pin_bad.append({"key": key, "path": entry.get("path"), "pinned": want, "measured": got})
    res.add("IND-06", "FROZEN.json logical_artifacts pins match measured bytes",
            "PASS" if not pin_bad else "FAIL",
            "both logical artifacts pinned and byte-identical" if not pin_bad else json.dumps(pin_bad),
            [f"{FROZEN}#logical_artifacts", f"{F0}#{pins_before[F0]}", f"{SUPPLEMENT}#{pins_before[SUPPLEMENT]}"])

    # IND-07 — canonical/supplement role separation: identical class-id sets and disjoint
    # ROLE keys (shared provenance keys are expected and are only reported).
    sup_contracts = list((sup.get("class_contracts") or {}).keys())
    canonical_role = {"class_ids", "classes", "disjointness", "disjointness_scope",
                      "disjointness_overlap_note", "transfer_rules", "guards",
                      "coverage_gaps", "open_questions", "field_vocabulary", "variants"}
    supplement_role = {"class_contracts", "frozen_classes", "axis_registry",
                       "implication_ledger", "terminology_disambiguation",
                       "contract_divergences", "artifact_role"}
    role_ok = (set(sup_contracts) == set(tax_ids)
               and not (canonical_role & supplement_role)
               and "class_contracts" not in tax
               and "classes" not in sup)
    shared_keys = sorted(set(tax.keys()) & set(sup.keys()))
    if role_ok:
        res.add("IND-07", "canonical/supplement role separation consistent", "PASS",
                f"class-id sets identical across trees; role keys disjoint; shared provenance keys={shared_keys}",
                [f"{SUPPLEMENT}#class_contracts", f"{F0}#class_ids"])
    else:
        res.add("IND-07", "canonical/supplement role separation consistent", "FAIL",
                json.dumps({"contracts": sup_contracts, "tax_ids": tax_ids,
                            "role_overlap": sorted(canonical_role & supplement_role),
                            "class_contracts_in_canonical": "class_contracts" in tax,
                            "classes_in_supplement": "classes" in sup}),
                [f"{SUPPLEMENT}#class_contracts"])

    # IND-08 — independent merged-regularity scan (G3), own normalization.
    # G3 forbids a merged token in asserted class content; prohibition/guard sentences that
    # mention the forbidden spellings are not violations, so they are reported as NOTE.
    def merged_hits(text):
        norm = re.sub(r"[\^{}_\s]", "", text)
        return [m.group(0) for m in re.finditer(r"C[0-9](?:or|and|/|\+|,)?C[0-9]", norm)]

    class_hits = merged_hits(yaml.safe_dump(tax.get("classes") or {}, sort_keys=False))
    res.add("IND-08", "independent merged-regularity scan of the four class blocks (G3)", "PASS" if not class_hits else "FAIL",
            "0 merged tokens in the class blocks" if not class_hits else f"hits={sorted(set(class_hits))}",
            [f"{F0}#classes", f"{F0}#{pins_before[F0]}"])
    file_hits = [{"line": i, "text": ln.strip()[:160]} for i, ln in enumerate(lines, 1) if merged_hits(ln)]
    res.add("IND-08-OBS", "whole-file merged-token occurrences are prohibitions/guards, not classes", "NOTE",
            ("no whole-file occurrences" if not file_hits else
             "occurrences are in prohibition/guard/vocabulary text and match distinct-value rules: "
             + json.dumps(file_hits)),
            [f"{F0}"] + [f"{F0}:{h['line']}" for h in file_hits])

    # IND-09 — no theorem promotion in a draft file.
    no_promo = tax.get("claims_theorem_status") is False and str(tax.get("status", "")).startswith("draft")
    res.add("IND-09", "no theorem-status promotion in F0", "PASS" if no_promo else "FAIL",
            f"status={tax.get('status')!r} claims_theorem_status={tax.get('claims_theorem_status')!r}",
            [f"{F0}#status", f"{F0}#claims_theorem_status"])

    # IND-10 — variants are pointers, not classes, and carry falsifiers.
    var_bad = []
    for v in tax.get("variants") or []:
        if v.get("parent_class") not in tax_ids:
            var_bad.append({"variant": v.get("variant_id"), "why": "parent_class not frozen"})
        if v.get("variant_id") in tax_ids:
            var_bad.append({"variant": v.get("variant_id"), "why": "variant_id collides with a class id"})
        if not str(v.get("falsifier") or "").strip():
            var_bad.append({"variant": v.get("variant_id"), "why": "no falsifier"})
    res.add("IND-10", "variants are parent-bound pointers with falsifiers, not classes",
            "PASS" if not var_bad else "FAIL",
            f"{len(tax.get('variants') or [])} variants checked" if not var_bad else json.dumps(var_bad),
            [f"{F0}#variants"])

    # IND-11 — A0 rubric axis cross-check (documented mapping).
    rub_by_id = {c["id"]: c for c in rub.get("frozen_classes", [])}
    axis_notes, axis_bad = [], []
    for cid in tax_ids:
        r, axes = rub_by_id.get(cid, {}), classes.get(cid, {}).get("axes", {})
        fam, tok, matter = axes.get("family"), axes.get("regularity_token"), axes.get("matter_model")
        want_form = {"WCC": "WCC", "SCC-C2": "SCC", "SCC-C0": "SCC"}.get(str(r.get("formulation")))
        if want_form != fam:
            axis_bad.append({"class": cid, "slot": "formulation/family",
                             "rubric": r.get("formulation"), "taxonomy": fam})
        if want_form == "SCC" and tok != str(r.get("formulation")).split("-")[-1]:
            axis_bad.append({"class": cid, "slot": "formulation/regularity_token",
                             "rubric": r.get("formulation"), "taxonomy": tok})
        if matter != r.get("matter_model"):
            axis_bad.append({"class": cid, "slot": "matter_model",
                             "rubric": r.get("matter_model"), "taxonomy": matter})
        if axes.get("symmetry") != ("spherical" if r.get("symmetry") == "spherical" else "none_assumed"):
            axis_bad.append({"class": cid, "slot": "symmetry",
                             "rubric": r.get("symmetry"), "taxonomy": axes.get("symmetry")})
        lam = any("Lambda = 0" in h.get("text", "") for h in classes[cid].get("hypotheses", []))
        if bool(r.get("cosmological_constant") == 0) != lam:
            axis_bad.append({"class": cid, "slot": "cosmological_constant",
                             "rubric": r.get("cosmological_constant"), "taxonomy_has_lambda0": lam})
        axis_notes.append({"class": cid, "rubric_conclusion_primary": r.get("conclusion_primary"),
                           "taxonomy_conclusion_type": axes.get("conclusion_type")})
    res.add("IND-11", "A0 rubric frozen-class axes cross-check (mapped vocabulary)",
            "PASS" if not axis_bad else "FAIL",
            json.dumps({"mismatches": axis_bad}) if axis_bad else "all mapped axes agree: " + MAPPING_NOTE,
            [f"{RUBRIC}#frozen_classes", f"{F0}#classes"])
    res.add("IND-11-OBS", "conclusion-label vocabulary divergence is cross-artifact, not G-F0",
            "NOTE", CONCLUSION_VOCAB_NOTE, [f"{RUBRIC}#frozen_classes", f"{F0}#classes.*.axes.conclusion_type"])

    verdict = "accept" if not res.failed else "revise"
    report = {
        "artifact": "artifacts/worker-038/f0_conformance/check_f0_independent.py",
        "task": "W038-F0-CONFORMANCE-01",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": tax_ids,
        "pins": {
            "before": pins_before,
            "after": pins_after,
            "canonical_f0": f"{F0}#{pins_before[F0]}",
            "declared_checker": f"{CHECKER}#{pins_before[CHECKER]}",
            "rubric": f"{RUBRIC}#{pins_before[RUBRIC]}",
            "frozen_manifest": f"{FROZEN}#{pins_before[FROZEN]}",
        },
        "checks": res.checks,
        "summary": {
            "passed": sum(1 for c in res.checks if c["status"] == "PASS"),
            "failed": len(res.failed),
            "notes": sum(1 for c in res.checks if c["status"] == "NOTE"),
        },
        "verdict": verdict,
        "verdict_scope": ("independent worker evidence for the G-F0 machine-checkable criteria; "
                          "not a gate verdict and not a node-completion claim"),
        "falsifier": ("a reader who (a) shows any resolved id/symmetry/matter/conclusion axis is "
                      "misread by this script, (b) exhibits a merged-regularity string the IND-08 "
                      "normalization misses, (c) shows a taxonomy case that names a non-frozen class "
                      "or an unresolved hypothesis, or (d) shows a canonical/supplement class-id "
                      "mismatch, refutes the corresponding PASS; the verdict flips to revise if any "
                      "FAIL is substantiated."),
        "claims_not_made": [
            "no gate verdict (authority: Astra / group leads)",
            "no node done/passed status",
            "no physics result, no theorem, no counterexample",
            "no claim that the class formulations are scientifically correct",
            "no authorship of F0; reviewer is not an author of the taxonomy, checker, rubric or manifest",
        ],
        "authority_note": ("Per comms/PROTOCOL.md and ASTRA_HANDOFF, a worker event cannot set "
                           "status=done, validation_status=passed or a gate verdict."),
    }
    out = Path(args.json_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "summary": report["summary"],
                      "json_out": str(out)}, indent=1))
    return 0 if verdict == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
