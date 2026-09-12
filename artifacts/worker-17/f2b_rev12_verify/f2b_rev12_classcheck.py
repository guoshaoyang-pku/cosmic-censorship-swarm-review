#!/usr/bin/env python3
"""FORM-QNF follow-up / worker-017: F2b (AF-SCC-C0-VAC-GEN) rev12 class-identity check.

Bounded, class-bound verification of the frozen F2b artifact
`artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (FROZEN rev27/28 pin
sha256 55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6)
against the frozen F0 declared taxonomy, the F0 class-contract supplement,
rule_spec, and VARIANT_REGISTRY.

What this decides
-----------------
Whether F2b rev12 is a class-bound, non-inflated, non-disjunctive specification
of exactly one frozen class, whose declared pointers, hashes and registration
claims resolve at the pinned revisions -- and whether the recorded known
findings (stale consistency-evidence pin, unregistered Sobolev/data-class
branch, rule_spec version label) are still live at this hash.

What this does NOT decide
-------------------------
Physical truth, the truth of the conjecture, mathematical sufficiency of the
schema, or any gate verdict. `PASS` is a statement about form, pinning and
class separation only.  Worker evidence is advisory; only the controller and
group leads move gates (comms/PROTOCOL.md).

Negative controls: each check has a mutant that must trip it (see MUTANTS).
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

SCHEMA = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
SCHEMA_MIRROR = "schemas/af_scc_c0_vacuum.yaml"
F0_DECLARED = "research_map/formulation_taxonomy.yaml"
F0_SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
FROZEN = "artifacts/formulation/FROZEN.json"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"

CLASS_ID = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2b"
PIN_F2B_REV12 = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
PIN_F0_DECLARED = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_F0_SUPPLEMENT = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def dget(doc, dotted: str, default=None):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def check(cid: str, ok: bool, detail: str, expected_finding: bool = False):
    return {"id": cid, "ok": bool(ok), "expected_finding": expected_finding, "detail": detail}


# ---------------------------------------------------------------- checks ----

def run_checks(schema: dict, ctx: dict) -> list[dict]:
    out: list[dict] = []
    class_id = schema.get("class_id")
    node_id = schema.get("node_id")

    # ID-01: exactly one frozen class, correct node.
    frozen_four = ctx["rule_spec"].get("frozen_classes", [])
    out.append(check(
        "ID-01_class_and_node",
        class_id == CLASS_ID and class_id in frozen_four and node_id == NODE_ID,
        f"class_id={class_id!r} node_id={node_id!r} frozen_four={frozen_four}",
    ))

    # ID-02: class axes match the declared F0 contract.
    f0 = dget(ctx["f0_declared"], f"classes.{CLASS_ID}") or {}
    axes = f0.get("axes", {})
    comp = schema.get("class_components", {})
    expect_components = {
        "asymptotics": "AF",
        "censorship": axes.get("family"),
        "matter": "VAC",
        "genericity": "GEN",
        "regularity_token": axes.get("regularity_token"),
    }
    out.append(check(
        "ID-02_components_match_f0",
        comp == expect_components,
        f"components={comp} expected={expect_components}",
    ))

    # ID-03: conclusion type is exactly the rule_spec vocabulary value for the class.
    vocab_type = dget(ctx["rule_spec"], f"vocabularies.class_conclusion_type.{CLASS_ID}")
    conclusion_type = dget(schema, "conclusion.conclusion_type")
    out.append(check(
        "ID-03_conclusion_type",
        conclusion_type == vocab_type,
        f"conclusion_type={conclusion_type!r} rule_spec_vocabulary={vocab_type!r}",
    ))

    # ID-04/05: both pointers resolve in the two F0 artefacts.
    p1 = schema.get("class_contract_pointer")
    ok1 = False
    detail1 = f"pointer={p1!r}"
    if isinstance(p1, str) and "#" in p1:
        path, frag = p1.split("#", 1)
        ok1 = path == F0_DECLARED and dget(ctx["f0_declared"], frag) is not None
        detail1 += f" resolves={ok1} (path matches declared F0: {path == F0_DECLARED})"
    out.append(check("ID-04_class_contract_pointer", ok1, detail1))

    p2 = schema.get("class_contract_supplement_pointer")
    ok2 = False
    detail2 = f"pointer={p2!r}"
    if isinstance(p2, str) and "#" in p2:
        path, frag = p2.split("#", 1)
        ok2 = path == F0_SUPPLEMENT and dget(ctx["f0_supplement"], frag) is not None
        detail2 += f" resolves={ok2} (path matches supplement: {path == F0_SUPPLEMENT})"
    out.append(check("ID-05_supplement_pointer", ok2, detail2))

    # ID-06/07/08: f0_binding hashes resolve.
    f0b = schema.get("f0_binding", {})
    out.append(check(
        "ID-06_declared_f0_hash",
        f0b.get("declared_f0_sha256") == ctx["hashes"][F0_DECLARED],
        f"declared={f0b.get('declared_f0_sha256')} measured={ctx['hashes'][F0_DECLARED]}",
    ))
    ce_path = f0b.get("consistency_evidence")
    ce_exists = isinstance(ce_path, str) and (ROOT / ce_path).is_file()
    out.append(check("ID-07_consistency_evidence_exists", ce_exists,
                     f"consistency_evidence={ce_path!r} exists={ce_exists}"))
    ce_measured = ctx["hashes"].get(CONSISTENCY)
    out.append(check(
        "ID-08_consistency_evidence_hash",
        f0b.get("consistency_evidence_sha256") == ce_measured,
        f"declared={f0b.get('consistency_evidence_sha256')} measured={ce_measured}",
        expected_finding=True,
    ))

    # ID-09: sibling separation is a frozen class and the containment is one-way.
    sib = schema.get("sibling_disjoint_from")
    ledger = str(dget(schema, "implication_ledger.extension_class_containment", ""))
    containment_ok = bool(re.search(r"contains\s+E_?C2|E_C2\s+subset", ledger))
    out.append(check(
        "ID-09_sibling_separation",
        sib == SIBLING and sib in frozen_four and containment_ok
        and "never the reverse" in str(dget(schema, "implication_ledger.subsumption_note", "")),
        f"sibling={sib!r} containment_text_ok={containment_ok}",
    ))

    # ID-10: D0 is a two-branch tagged union, not a 'suitable regularity' range.
    d0 = str(dget(schema, "quantifiers.domains.D0.definition", ""))
    formal = str(dget(schema, "quantifiers.formal", ""))
    smooth_branch = "r = smooth" in d0
    sobolev_branch = "r = (sobolev,s,delta)" in d0
    suitable_forbidden = "does not range over 'suitable' regularity" in d0
    out.append(check(
        "ID-10_d0_tagged_union",
        smooth_branch and sobolev_branch and "s > 5/2" in d0 and "(1/2,1)" in d0
        and suitable_forbidden and "forall r in D0" in formal,
        f"smooth_branch={smooth_branch} sobolev_branch={sobolev_branch} s>5/2={'s > 5/2' in d0} "
        f"delta={'/2,1)' in d0} suitable_explicitly_forbidden={suitable_forbidden} "
        f"formal_single_binder={'forall r in D0' in formal}",
    ))

    # ID-11: the Sobolev/data-class branch is registered as a variant (EXPECTED FINDING: absent).
    variants = ctx["registry"].get("variants", [])
    sob = [v for v in variants if v.get("parent_class") == CLASS_ID
           and re.search(r"sobolev|data[_ -]?class|regularity[_ -]?axis", json.dumps(v).lower())]
    out.append(check(
        "ID-11_sobolev_branch_registered",
        len(sob) > 0,
        f"VARIANT_REGISTRY v{ctx['registry'].get('version')} variants={len(variants)}; "
        f"matching Sobolev/data-class variant(s) for {CLASS_ID}: {len(sob)}",
        expected_finding=True,
    ))

    # ID-12: supplement data_class_freeze version claim resolves to the frozen rule_spec.
    freeze = str(dget(ctx["f0_supplement"], f"class_contracts.{CLASS_ID}.data_class_freeze", ""))
    m = re.search(r"rule_spec v([0-9.]+)", freeze)
    claimed = m.group(1) if m else None
    actual = str(ctx["rule_spec"].get("spec_version"))
    out.append(check(
        "ID-12_rule_spec_version_claim",
        claimed == actual,
        f"supplement claims rule_spec v{claimed}; frozen rule_spec spec_version={actual}; "
        f"registered-claim present={'registered Sobolev variant' in freeze}",
        expected_finding=True,
    ))

    # ID-13: no WCC content in the conclusion / I+ / visibility slots (SCC class).
    vis_role = dget(schema, "visibility.role")
    iplus_role = dget(schema, "i_plus.role")
    iplus_conc = dget(schema, "i_plus.in_conclusion")
    conc_text = " ".join(str(x) for x in [
        dget(schema, "conclusion.statement_natural_language", ""),
        dget(schema, "conclusion.statement_formal", ""),
    ]).lower()
    wcc_tokens = [t for t in ("visible", "visibility") if t in conc_text]
    out.append(check(
        "ID-13_no_wcc_in_conclusion",
        vis_role == "not_in_conclusion" and iplus_role == "assumption" and iplus_conc is False
        and not wcc_tokens,
        f"visibility.role={vis_role!r} i_plus.role={iplus_role!r} i_plus.in_conclusion={iplus_conc!r} "
        f"wcc_tokens_in_conclusion={wcc_tokens}",
    ))

    # ID-14: tier-1 falsifier is witness-shaped and refutes this class only.
    t1 = dget(schema, "falsifier.tier_1", {}) or {}
    wt = str(t1.get("witness_type", "")).lower()
    out.append(check(
        "ID-14_falsifier_shape",
        t1.get("refutes") == CLASS_ID and "extension" in wt
        and "visible" not in wt and "non-meager" in str(t1.get("genericity_requirement", ""))
        and bool(t1.get("machine_checkable_steps")),
        f"refutes={t1.get('refutes')!r} extension_in_witness={'extension' in wt} "
        f"visible_in_witness={'visible' in wt} non_meager_req="
        f"{'non-meager' in str(t1.get('genericity_requirement',''))}",
    ))

    # ID-15: composite/disjunctive class token absent from the *specification* slots.
    # anti_scope.phrases_that_are_not_this_class is a prohibition list and is
    # exempt by design (it must be allowed to name the forbidden composite).
    spec_slots = [
        dget(schema, "scope_statement", ""),
        formal,
        dget(schema, "conclusion.statement_natural_language", ""),
        dget(schema, "conclusion.statement_formal", ""),
        str(dget(schema, "regularity", "")),
        str(dget(schema, "quantifiers.domains.D0.definition", "")),
    ]
    spec_text = " ".join(str(x) for x in spec_slots)
    # Hard decision 1 forbids the composite token "C0 or C2".  The reversed
    # "C2 or C0" occurs once in a negation ("No containment with C2 or C0 is
    # asserted here") and is a prohibition, not a use, so only the canonical
    # order is scanned here.
    hits = re.findall(r"C\^?0\s+or\s+C\^?2", spec_text)
    prohibited = "any 'C0 or C2' composite regularity" in str(
        dget(schema, "anti_scope.phrases_that_are_not_this_class", ""))
    out.append(check("ID-15_no_composite_disjunction", not hits and prohibited,
                     f"spec_slot_disjunction_hits={hits} count={len(hits)} "
                     f"anti_scope_prohibits_composite={prohibited}"))

    # ID-16: freeze pin is the FROZEN rev12/27+ hash and did not move during the run.
    out.append(check(
        "ID-16_freeze_pin",
        ctx["hashes"][SCHEMA] == PIN_F2B_REV12 == ctx["hashes_after"][SCHEMA]
        and ctx["hashes"][SCHEMA_MIRROR] == PIN_F2B_REV12,
        f"schema={ctx['hashes'][SCHEMA][:12]} mirror={ctx['hashes'][SCHEMA_MIRROR][:12]} "
        f"expected={PIN_F2B_REV12[:12]} stable={ctx['hashes'][SCHEMA] == ctx['hashes_after'][SCHEMA]}",
    ))

    # ID-17: review_status is not a self-certified acceptance (HF-14 guard).
    rs = json.dumps(schema.get("review_status", {})).lower()
    self_cert = any(t in rs for t in ('"accepted"', '"passed"', "validation_status"))
    out.append(check("ID-17_no_self_certified_status", not self_cert,
                     f"review_status={schema.get('review_status')!r}"))

    return out


# --------------------------------------------------------------- mutants ----

def mutate(text: str, name: str) -> str:
    if name == "M1_umbrella_class_id":
        return text.replace(f"class_id: {CLASS_ID}", "class_id: AF-SCC-VAC-GEN", 1)
    if name == "M2_inflated_conclusion":
        return text.replace("conclusion_type: scc_c0_future_inextendibility",
                            "conclusion_type: scc_c2_future_inextendibility", 1)
    if name == "M3_visibility_in_conclusion":
        return text.replace("visibility:\n  role: not_in_conclusion",
                            "visibility:\n  role: conclusion", 1)
    if name == "M4_visible_falsifier":
        return text.replace(
            'witness_type: "an open (or at least non-meager) set of one-ended AF vacuum data',
            'witness_type: "a visible incomplete causal geodesic', 1)
    if name == "M5_stale_f0_hash":
        return re.sub(r"declared_f0_sha256: \"0abb9ed8a961[0-9a-f]*\"",
                      'declared_f0_sha256: "' + "0" * 64 + '"', text, count=1)
    if name == "M6_composite_disjunction":
        return text.replace("scope_statement: >",
                            "scope_statement: >\n  (C0 or C2 composite) ", 1)
    if name == "M7_drop_sobolev_branch":
        return text.replace(
            "r = smooth (the smooth-with-decay default) or r = (sobolev,s,delta) with s > 5/2 and delta in (1/2,1)",
            "r = smooth (the smooth-with-decay default)", 1)
    if name == "M8_self_certified_accept":
        return text.replace("review_status:\n  independent_reviewers: []\n  verdict: pending",
                            "review_status:\n  independent_reviewers: []\n  verdict: accepted\n"
                            "  validation_status: passed", 1)
    raise KeyError(name)


MUTANTS = {
    "M1_umbrella_class_id": "ID-01_class_and_node",
    "M2_inflated_conclusion": "ID-03_conclusion_type",
    "M3_visibility_in_conclusion": "ID-13_no_wcc_in_conclusion",
    "M4_visible_falsifier": "ID-14_falsifier_shape",
    "M5_stale_f0_hash": "ID-06_declared_f0_hash",
    "M6_composite_disjunction": "ID-15_no_composite_disjunction",
    "M7_drop_sobolev_branch": "ID-10_d0_tagged_union",
    "M8_self_certified_accept": "ID-17_no_self_certified_status",
}


def main() -> int:
    schema_path = ROOT / SCHEMA
    ctx = {
        "rule_spec": json.loads((ROOT / RULE_SPEC).read_text()),
        "registry": json.loads((ROOT / REGISTRY).read_text()),
        "f0_declared": read_yaml(ROOT / F0_DECLARED),
        "f0_supplement": read_yaml(ROOT / F0_SUPPLEMENT),
        "hashes": {},
    }
    for rel in (SCHEMA, SCHEMA_MIRROR, F0_DECLARED, F0_SUPPLEMENT, CONSISTENCY,
                RULE_SPEC, REGISTRY, FROZEN):
        ctx["hashes"][rel] = sha256_file(ROOT / rel)

    schema_text = schema_path.read_text()
    ctx["schema_text"] = schema_text
    ctx["hashes_after"] = dict(ctx["hashes"])  # re-measured after the checks below
    schema = yaml.safe_load(schema_text)
    checks = run_checks(schema, ctx)
    ctx["hashes_after"] = {SCHEMA: sha256_file(schema_path),
                           SCHEMA_MIRROR: sha256_file(ROOT / SCHEMA_MIRROR)}
    freeze_drift = ctx["hashes"][SCHEMA] != ctx["hashes_after"][SCHEMA]
    if freeze_drift:
        for c in checks:
            if c["id"] == "ID-16_freeze_pin":
                c["ok"] = False
                c["detail"] += f" | FREEZE DRIFT during run: {ctx['hashes_after'][SCHEMA][:12]}"
    for c in checks:
        if c["id"] == "ID-16_freeze_pin":
            c["freeze_drift"] = freeze_drift

    controls = []
    ctrl_dir = ROOT / "artifacts/worker-17/f2b_rev12_verify/controls"
    ctrl_dir.mkdir(parents=True, exist_ok=True)
    for name, expected_check in MUTANTS.items():
        mtext = mutate(schema_text, name)
        mpath = ctrl_dir / f"{name}.yaml"
        mpath.write_text(mtext)
        mctx = dict(ctx)
        mctx["schema_text"] = mtext
        mres = run_checks(yaml.safe_load(mtext), mctx)
        failed = [c["id"] for c in mres if not c["ok"]]
        controls.append({
            "mutant": name,
            "expected_check": expected_check,
            "observed_failed_checks": failed,
            "detected": expected_check in failed,
            "mutant_sha256": sha256_text(mtext),
        })

    expected_findings = [c for c in checks if c["expected_finding"] and not c["ok"]]
    unexpected = [c for c in checks if not c["ok"] and not c["expected_finding"]]
    return_code = 0 if not unexpected and all(c["detected"] for c in controls) else 1

    report = {
        "report_id": "w17-f2b-rev12-classcheck-" + datetime.now(CST).strftime("%Y%m%dT%H%M%S%z"),
        "actor": "deepseek-flash-17",
        "worker": "worker-017",
        "role": "bounded execution worker (independent A1/G-FORM review of F2b)",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": "G-FORM",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "tool": {"path": str(Path(__file__).resolve().relative_to(ROOT)),
                 "sha256": sha256_file(Path(__file__).resolve())},
        "inputs_measured": ctx["hashes"],
        "pins_expected": {"F2b_rev12": PIN_F2B_REV12, "F0_declared": PIN_F0_DECLARED,
                          "F0_supplement": PIN_F0_SUPPLEMENT},
        "checks": checks,
        "checks_failed_expected_findings": [c["id"] for c in expected_findings],
        "checks_failed_unexpected": [c["id"] for c in unexpected],
        "negative_controls": controls,
        "controls_all_detected": all(c["detected"] for c in controls),
        "result": "PASS_WITH_RECORDED_FINDINGS" if return_code == 0 else "FAIL",
        "not_claimed": [
            "no gate verdict", "no node completion", "no validation_status=passed",
            "no truth claim about the conjecture", "no edit to any canonical artifact",
            "advisory machine evidence only",
        ],
        "falsifier": ("An F2b rev12 schema in which the frozen class/conclusion/pointer/pin checks "
                      "hold AND the Sobolev/data-class branch resolves in VARIANT_REGISTRY AND the "
                      "supplement's rule_spec version claim equals the frozen spec_version would "
                      "falsify the two blocking findings; a mutant that does not trip its check "
                      "falsifies this instrument."),
        "exit_code": return_code,
    }
    out_path = ROOT / "artifacts/worker-17/f2b_rev12_verify/f2b_rev12_classcheck_report.json"
    out_path.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in
                      ("report_id", "result", "checks_failed_expected_findings",
                       "checks_failed_unexpected", "controls_all_detected", "exit_code")},
                     indent=1))
    return return_code


if __name__ == "__main__":
    sys.exit(main())
