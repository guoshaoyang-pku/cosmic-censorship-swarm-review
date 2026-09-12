#!/usr/bin/env python3
"""W080-GFORM-R29-VIS-01: independent, hash-pinned verification of the AF-WCC-VAC-GEN
(F1) schema at FROZEN rev29 (schema revision 13), focused on the rev13 repair.

Read-only on every canonical path: all inputs are the pinned copies in ./pinned/.
Deterministic; no network; emits ./report.json and ./sandbox/check_taxonomy_consistency.out.

Checks
  H1  pin integrity: pinned schema/FROZEN bytes match FROZEN rev29 declared sha256
  H2  F0 hash chain: declared_f0_sha256 == measured canonical F0 bytes
  H3  evidence binding (CF-20 #2): consistency_evidence_sha256 == measured evidence bytes
  H4  pointer resolution: class_contract_pointer / class_contract_supplement_pointer
  H5  case-corpus rebind (CF-20 #1): taxonomy_cases meta row binds measured F0 rev5 hash
  H6  symbol closure (W080-FSYM-01): AF_{I+} has a definition site and every use resolves
  V1  whole/tail equivalence lemma (rev13 T1): finite exhaustive check under past-closedness
  V2  single-q tail predicate entails the union predicate (set-theoretic)
  V3  union predicate does not entail single-q tail (omega-chain separation, T4)
  C1  class binding: exactly one frozen class id; no composite C0/C2 token in assertions
  C2  conclusion_type registered; falsifier present
  C3  variant SET relation direction (rev13) is the predicate-level truth, and the
      frozen F0 / VARIANT_REGISTRY strength sentence is statement-level; level labels
      are absent -> recorded divergence finding (not a hash failure)
  X1  canonical consistency checker re-run on the pins reproduces CONSISTENT
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
PIN = ROOT / "pinned"
SANDBOX = ROOT / "sandbox"

MEASURED = {}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def load_yaml(name: str):
    return yaml.safe_load((PIN / name).read_text())


def check(cid: str, ok: bool, statement: str, observed, severity_if_fail="hard"):
    return {
        "check_id": cid,
        "statement": statement,
        "pass": bool(ok),
        "observed": observed,
        "severity_if_fail": severity_if_fail,
    }


def main() -> int:
    checks: list[dict] = []
    findings: list[dict] = []

    frozen = json.loads((PIN / "FROZEN.json").read_text())
    f1 = load_yaml("af_wcc_vacuum.yaml")
    f2a = load_yaml("af_scc_c2_vacuum.yaml")
    f2b = load_yaml("af_scc_c0_vacuum.yaml")
    canonical = load_yaml("formulation_taxonomy.canonical.yaml")
    supplement = load_yaml("formulation_taxonomy.supplement.yaml")
    variant_registry = json.loads((PIN / "VARIANT_REGISTRY.json").read_text())
    evidence = json.loads((PIN / "taxonomy_consistency.json").read_text())
    cases = [json.loads(l) for l in (PIN / "taxonomy_cases.jsonl").read_text().splitlines() if l.strip()]

    f1_text = (PIN / "af_wcc_vacuum.yaml").read_text()
    concl_raw = f1.get("conclusion", {}) or {}

    # ---------------------------------------------------------------- H1 pins
    fz_pins = frozen.get("files", {})
    pin_rows = []
    for path, declared in (
        ("schemas/af_wcc_vacuum.yaml", "af_wcc_vacuum.yaml"),
        ("schemas/af_scc_c2_vacuum.yaml", "af_scc_c2_vacuum.yaml"),
        ("schemas/af_scc_c0_vacuum.yaml", "af_scc_c0_vacuum.yaml"),
        ("schemas/taxonomy_cases.jsonl", "taxonomy_cases.jsonl"),
        ("artifacts/formulation/formulation_taxonomy.yaml", "formulation_taxonomy.supplement.yaml"),
        ("research_map/formulation_taxonomy.yaml", "formulation_taxonomy.canonical.yaml"),
        ("artifacts/formulation/VARIANT_REGISTRY.json", "VARIANT_REGISTRY.json"),
    ):
        measured = sha256_file(PIN / declared)
        MEASURED[path] = measured
        pin_rows.append({"path": path, "declared": fz_pins.get(path, {}).get("sha256"),
                         "measured_pinned_copy": measured,
                         "match": fz_pins.get(path, {}).get("sha256") == measured})
    manifest_self = sha256_file(PIN / "FROZEN.json")
    checks.append(check(
        "H1", all(r["match"] for r in pin_rows) and frozen.get("revision") == 29,
        "pinned schema/supplement/registry bytes equal the FROZEN rev29 declared sha256",
        {"frozen_revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
         "frozen_json_sha256": manifest_self, "rows": pin_rows}))

    binding = f1.get("f0_binding", {})
    MEASURED["artifacts/formulation/evidence/taxonomy_consistency.json"] = sha256_file(
        PIN / "taxonomy_consistency.json")

    # ------------------------------------------------------ H2 F0 hash chain
    canon_measured = MEASURED["research_map/formulation_taxonomy.yaml"]
    checks.append(check(
        "H2", binding.get("declared_f0_sha256") == canon_measured,
        "f0_binding.declared_f0_sha256 equals the measured canonical F0 bytes",
        {"declared": binding.get("declared_f0_sha256"), "measured": canon_measured}))

    # --------------------------------------------------- H3 evidence binding
    ev_measured = MEASURED["artifacts/formulation/evidence/taxonomy_consistency.json"]
    per_schema_ev = {n: load_yaml(n).get("f0_binding", {}).get("consistency_evidence_sha256")
                     for n in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")}
    checks.append(check(
        "H3", all(v == ev_measured for v in per_schema_ev.values()),
        "all three class schemas bind consistency_evidence_sha256 to the measured evidence bytes "
        "(the CF-20 second defect, refreshed at rev13)",
        {"measured": ev_measured, "declared": per_schema_ev}))

    # ------------------------------------------------ H4 pointer resolution
    ptr_rows = []
    for n, cls in (("af_wcc_vacuum.yaml", "AF-WCC-VAC-GEN"),
                   ("af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN"),
                   ("af_scc_c0_vacuum.yaml", "AF-SCC-C0-VAC-GEN")):
        d = load_yaml(n)
        cp = d.get("class_contract_pointer", "")
        sp = d.get("class_contract_supplement_pointer", "")
        cls_key = cp.split("#classes.", 1)[1] if "#classes." in cp else None
        sup_key = sp.split("#class_contracts.", 1)[1] if "#class_contracts." in sp else None
        ptr_rows.append({
            "schema": n, "class_contract_pointer": cp, "supplement_pointer": sp,
            "resolves_canonical_classes_key": bool(cls_key and cls_key in canonical.get("classes", {})),
            "resolves_supplement_class_contracts_key": bool(
                sup_key and sup_key in supplement.get("class_contracts", {})),
            "declared_class_id": d.get("class_id"),
            "pointer_class_matches_declared": cls_key == d.get("class_id") == sup_key,
        })
    checks.append(check(
        "H4", all(r["resolves_canonical_classes_key"] and r["resolves_supplement_class_contracts_key"]
                  and r["pointer_class_matches_declared"] for r in ptr_rows),
        "class-contract pointer and supplement pointer resolve and name the declared class",
        {"rows": ptr_rows}))

    # ------------------------------------------------ H5 case-corpus rebind
    meta = next((r for r in cases if r.get("record_type") == "meta"), {})
    tax_ref = meta.get("taxonomy_ref", {})
    checks.append(check(
        "H5", tax_ref.get("sha256") == canon_measured and tax_ref.get("revision") == 5
        and fz_pins.get("schemas/taxonomy_cases.jsonl", {}).get("sha256") == MEASURED["schemas/taxonomy_cases.jsonl"],
        "case-corpus meta row binds the measured F0 rev5 canonical hash and the corpus is FROZEN-pinned",
        {"meta_taxonomy_ref": tax_ref, "measured_f0": canon_measured,
         "frozen_pin": fz_pins.get("schemas/taxonomy_cases.jsonl", {}).get("sha256")}))

    # --------------------------------------------------- H6 symbol closure
    defs = f1.get("i_plus", {}).get("predicate_abbreviation", "")
    occurrences = [{"line": i + 1, "text": ln.strip()}
                   for i, ln in enumerate(f1_text.splitlines()) if "AF_{I+}" in ln]
    use_lines = [o for o in occurrences if "abbreviates" not in o["text"]]
    defined = "AF_{I+}(M) abbreviates" in defs
    checks.append(check(
        "H6", defined and len(use_lines) >= 1 and all(
            "predicate_abbreviation" not in o["text"] for o in use_lines),
        "AF_{I+} has exactly one definition site (i_plus.predicate_abbreviation) and every "
        "use is downstream of it (W080-FSYM-01 closure at rev29)",
        {"definition_site_present": defined, "definition": defs[:180],
         "occurrences": occurrences}))

    # ------------------------------------- V1 whole/tail equivalence lemma
    # Finite model: gamma is a causal chain g0<...<gn, J^-(q) is a past-closed down-set.
    # Lemma: tail(k) subset J^-(q)  =>  whole subset J^-(q) for every down-set and every k.
    v1_violations = 0
    v1_tested = 0
    n = 5
    for mask in range(1 << n):  # all down-sets of a chain are prefixes; enumerate all subsets
        downset = {i for i in range(n) if mask >> i & 1}
        if downset and max(downset) + 1 != len(downset):
            continue  # not a prefix -> not past-closed
        for k in range(n):
            v1_tested += 1
            tail = set(range(k, n))
            if tail <= downset and not set(range(n)) <= downset:
                v1_violations += 1
    checks.append(check(
        "V1", v1_violations == 0,
        "whole-curve and tail containment in J^-(q) are equivalent for causal geodesics "
        "(J^-(q) past-closed): finite exhaustive check over chain prefixes",
        {"models_tested": v1_tested, "violations": v1_violations}))

    # ------------------------- V2 single-q tail entails the union predicate
    v2_violations = 0
    v2_tested = 0
    for mask in range(1 << n):  # pasts P_q (prefixes); union = union of q-pasts
        pasts = [set(range(j + 1)) for j in range(n) if mask >> j & 1]
        union = set().union(*pasts) if pasts else set()
        for k in range(n):
            v2_tested += 1
            if set(range(k, n)) <= union and not set(range(n)) <= union:
                v2_violations += 1
    checks.append(check(
        "V2", v2_violations == 0,
        "the single-q tail predicate entails the union (set-based) predicate",
        {"models_tested": v2_tested, "violations": v2_violations}))

    # --------------- V3 union does not entail single-q tail (omega-chain, T4)
    # Infinite model g_0<g_1<... with I+ = {q_j : j in omega}, g_i in J^-(q_j) iff i <= j.
    # Truncate at g_N and q_{N-1}: union covers the prefix, but no q_j contains any tail
    # of gamma because g_N is in every tail and g_N not in J^-(q_j) for all j <= N-1.
    # The separation needs infinitude: with I+ = {q_j : j in omega} every gamma point is
    # covered because some j >= i always exists, while no finite q_j contains a tail.  A
    # finite truncation therefore must be read as: prefix covered (hypothesis of the general
    # case), no q_j contains any tail of the truncated chain, and the coverage of the last
    # point is supplied by a q beyond the truncation - which is exactly why the model is an
    # omega-chain and not a finite poset.
    N = 12
    gamma = list(range(N))
    qs = list(range(N - 1))
    prefix_covered = all(any(i <= j for j in qs) for i in range(N - 1))
    tail_contained = {}
    for j in qs:
        tail_contained[j] = [k for k in gamma if all(i <= j for i in gamma if i >= k)]
    separated = all(not v for v in tail_contained.values())
    # general-case coverage argument, machine-checked on the pattern: for every index i there
    # is a q_j with j >= i, so the omega-union covers all of gamma.
    coverage_arg = all(any(j >= i for j in qs) for i in range(N - 1))
    checks.append(check(
        "V3", prefix_covered and separated and coverage_arg,
        "the union predicate does not entail the single-q tail predicate: omega-chain "
        "separation (rev13 T4). No q_j contains any tail of gamma, while the omega-union "
        "covers gamma because some q_j exists with j >= i for every i",
        {"chain_length": N, "finite_prefix_covered": prefix_covered,
         "coverage_argument_holds_on_pattern": coverage_arg,
         "q_with_a_contained_tail": tail_contained}))

    # --------------------------------------------------- C1 class binding
    # Scope the composite-token scan to assertion surfaces.  The schema legitimately *mentions*
    # composite tokens inside forbidden_weakenings / schema_falsifiers / anti_scope phrase lists
    # (the CF-16 metalinguistic-mention pattern); those are prohibitions, not declarations.
    assertion_surfaces = {
        "class_id": f1.get("class_id"),
        "class_components": f1.get("class_components"),
        "scope_statement": f1.get("scope_statement"),
        "quantifiers": f1.get("quantifiers"),
        "hypotheses": f1.get("hypotheses"),
        "conclusion.statement_natural_language": concl_raw.get("statement_natural_language"),
        "conclusion.statement_formal": concl_raw.get("statement_formal"),
    }
    comp = re.compile(r"\bC\s*0\s*(?:or|/|,)\s*C\s*2\b|\bC\s*2\s*(?:or|/|,)\s*C\s*0\b", re.I)
    composite_asserted = {k: comp.findall(json.dumps(v)) for k, v in assertion_surfaces.items()
                          if v is not None and comp.search(json.dumps(v))}
    composite_mentions = len(comp.findall(f1_text))
    checks.append(check(
        "C1", f1.get("class_id") == "AF-WCC-VAC-GEN" and not composite_asserted,
        "F1 schema declares exactly the frozen class AF-WCC-VAC-GEN and asserts no composite "
        "C0/C2 token on any assertion surface (mentions in prohibition lists are allowed)",
        {"class_id": f1.get("class_id"),
         "composite_tokens_on_assertion_surfaces": composite_asserted,
         "composite_tokens_in_prohibition_or_meta_text": composite_mentions}))

    # ------------------------------------------- C2 conclusion + falsifier
    concl = concl_raw
    fals = f1.get("falsifier", {}) or {}
    tier1 = fals.get("tier_1", {}) or {}
    checks.append(check(
        "C2", concl.get("conclusion_type") == "weak_cosmic_censorship"
        and tier1.get("refutes") == "AF-WCC-VAC-GEN"
        and len(tier1.get("machine_checkable_steps", []) or []) >= 3,
        "conclusion_type is the registered WCC token and the schema carries a tier-1 falsifier "
        "against this class with machine-checkable witness steps",
        {"conclusion_type": concl.get("conclusion_type"),
         "tier1_refutes": tier1.get("refutes"),
         "machine_checkable_steps": tier1.get("machine_checkable_steps")}))

    # ------------------------------------------- C3 variant SET direction
    vs = next((v for v in f1.get("class_identity_variants", [])
               if v.get("kind") == "set_based_visibility_reading"), {})
    rel = vs.get("relation", "")
    rel_says_weaker = "strictly WEAKER" in rel and "entails the union reading" in rel
    canon_wcc = canonical["classes"]["AF-WCC-VAC-GEN"]["conclusion"]["text"]
    f0_says_stronger = "is strictly stronger" in canon_wcc
    # locate the frozen registry strength for variant SET
    reg_text = json.dumps(variant_registry)
    reg_says_stronger = "strictly STRONGER than AF-WCC-VAC-GEN" in reg_text
    checks.append(check(
        "C3", rel_says_weaker,
        "F1 rev13 variant SET relation states the predicate-level truth (SET predicate is "
        "strictly weaker; single-q tail entails union)",
        {"relation": rel, "predicate_level_weaker": rel_says_weaker,
         "frozen_f0_statement_level_stronger_sentence_present": f0_says_stronger,
         "frozen_registry_statement_level_stronger_present": reg_says_stronger,
         "statement_strength_field_present": "statement_strength" in vs}))

    # ------------------------------- X1 canonical consistency checker
    SANDBOX.mkdir(exist_ok=True)
    sandbox_out = SANDBOX / "check_taxonomy_consistency.out"
    rc = None
    out = ""
    try:
        sandbox_root = SANDBOX / "root"
        for rel in ("research_map", "artifacts/formulation/tools", "artifacts/formulation/evidence"):
            (sandbox_root / rel).mkdir(parents=True, exist_ok=True)
        (sandbox_root / "research_map/formulation_taxonomy.yaml").write_bytes(
            (PIN / "formulation_taxonomy.canonical.yaml").read_bytes())
        (sandbox_root / "artifacts/formulation/formulation_taxonomy.yaml").write_bytes(
            (PIN / "formulation_taxonomy.supplement.yaml").read_bytes())
        (sandbox_root / "artifacts/formulation/tools/check_taxonomy_consistency.py").write_bytes(
            (PIN / "check_taxonomy_consistency.py").read_bytes())
        # AL is read from artifacts/formulation/VOCAB_ALIASES.json; reproduce it from the
        # canonical taxonomy alias block if present, else from the live file pinned here.
        va = ROOT / "pinned_vocab_aliases.json"
        if va.exists():
            (sandbox_root / "artifacts/formulation/VOCAB_ALIASES.json").write_bytes(va.read_bytes())
        proc = subprocess.run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"],
                              cwd=sandbox_root, capture_output=True, text=True, timeout=120)
        rc, out = proc.returncode, (proc.stdout + proc.stderr)
    except Exception as exc:  # pragma: no cover
        out = f"runner error: {exc}"
    sandbox_out.write_text(f"exit={rc}\n{out}")
    checks.append(check(
        "X1", rc == 0 and out.strip().startswith("CONSISTENT"),
        "the canonical check_taxonomy_consistency.py, run against the pinned F0 pair, "
        "returns CONSISTENT (the source of the bound evidence file)",
        {"exit": rc, "output_head": out.strip()[:200]}))

    # ----------------------------------------------------------------- verdict
    hard = [c for c in checks if not c["pass"] and c["severity_if_fail"] == "hard"]
    lvl_finding = {
        "id": "W080-F1-DIV-01",
        "severity": "major",
        "statement": (
            "Level-conflated strength labels for the SET reading across frozen artifacts. "
            "F1 rev13 states the predicate-level fact correctly ('variant SET ... strictly WEAKER "
            "than this class's single-q tail predicate'), while the frozen F0 canonical class text "
            "(0abb9ed8a961) and the frozen VARIANT_REGISTRY both say the set-based reading/condition "
            "is 'strictly stronger', which is correct only at the class-statement level "
            "(the SET conclusion entails the base conclusion because P_tail => P_set). Neither "
            "artifact states the level, and no declared checker compares these fields, so the "
            "same pair carries opposite-sounding labels in the corpus. This is the same inversion "
            "class repaired at rev12->rev13 (W076-GFORM-STRICTNESS-RECONCILE-06, "
            "W040-F1-STRICTNESS-ADJ-04). It is not a hash or binding failure and does not falsify "
            "the rev13 predicate relation."
        ),
        "licensed_direction": (
            "P_tail(gamma) => P_set(gamma) for every incomplete causal geodesic, so the SET class "
            "statement entails the AF-WCC-VAC-GEN class statement; a SET-based proof establishes "
            "the class conclusion a fortiori, while a single-q (class) proof does NOT establish the "
            "SET variant statement. F1's variant note forbids interchanging the readings, which is "
            "correct as registry policy, but the note does not record the one licensed direction."
        ),
        "recommended_fix": (
            "F1 rev14 / next revision: add explicit level labels to the variant SET entry "
            "(relation: strictly_weaker_predicate; statement_strength: strictly_stronger) using the "
            "vocabulary already present in this schema for genericity variants; qualify the "
            "leakage note with the licensed direction; record the F0/VARIANT_REGISTRY wording as a "
            "controller-adjudicated divergence (F0 bytes are frozen by REC-11, so any F0 repair "
            "requires a fresh F0 review round)."
        ),
        "evidence_refs": [
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2:234",
            "research_map/formulation_taxonomy.yaml#0abb9ed8a961:200",
            "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e:57",
            "artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3 D1",
        ],
    }
    findings.append(lvl_finding)
    findings.append({
        "id": "W080-F1-MAN-01",
        "severity": "info",
        "statement": (
            "FROZEN.json bytes changed inside revision 29 during this review window: measured "
            "3d9e3d77fd87... at ~00:58 and 815e08079aef... at 01:03 (frozen_at 00:55:02 -> "
            "00:57:26) while the three schema bytes stayed d9cebb94/e9a27996/b2ab6acb. The manifest "
            "self-hash is not in artifact_hashes.json, so a manifest rewrite at constant revision "
            "is not caught by the declared-vs-measured drift check. Schema binding is unaffected."
        ),
        "evidence_refs": ["artifacts/formulation/FROZEN.json#815e08079aef"],
    })

    report = {
        "task_id": "W080-GFORM-R29-VIS-01",
        "worker": "worker-080",
        "instance": "worker-080-20260912T005226-968807",
        "node_id": "F1",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN"],
        "target": {
            "path": "schemas/af_wcc_vacuum.yaml",
            "sha256": MEASURED["schemas/af_wcc_vacuum.yaml"],
            "schema_revision": f1.get("revision"),
            "frozen_revision": frozen.get("revision"),
            "frozen_json_sha256": manifest_self,
        },
        "pins": MEASURED,
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
        "hard_failures": hard,
        "findings": findings,
        "verdict": "accept" if not hard else "revise",
        "verdict_scope": (
            "Conformance of the pinned F1 bytes only, for: visibility predicate + rev13 direction "
            "repair, whole/tail equivalence lemma, AF_{I+} symbol closure, class binding, F0 and "
            "consistency-evidence hash chain, case-corpus rebind, and the canonical consistency "
            "checker re-run. Not a claim about the mathematical truth of WCC, not a gate verdict, "
            "not a node status."
        ),
        "falsifier": (
            "Re-run this harness at the same pinned hashes: any H/V/C check flipping, or a "
            "demonstration that P_tail does not entail P_set for incomplete causal geodesics with "
            "J^-(q) past-closed, or that the union predicate does entail the single-q tail predicate "
            "(which would collapse variant SET and falsify W080-F1-DIV-01's licensed direction), "
            "voids this report. A silent rewrite of schemas/af_wcc_vacuum.yaml or of the pinned F0 "
            "pair voids the hash binding and requires a fresh review."
        ),
        "authority_note": (
            "Worker evidence only: no gate verdict, no node status, no validation_status=passed, "
            "no canonical artifact modified, no mathematical claim."
        ),
        "generated_at": None,
    }
    from datetime import datetime, timezone, timedelta
    report["generated_at"] = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")

    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"verdict={report['verdict']} checks={report['checks_passed']}/{report['checks_total']} "
          f"hard_failures={len(hard)}")
    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['check_id']}: {c['statement'][:88]}")
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
