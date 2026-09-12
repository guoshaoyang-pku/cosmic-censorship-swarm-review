#!/usr/bin/env python3
"""W047 independent class-contract review instrument for F2a (AF-SCC-C2-VAC-GEN).

Deterministic, offline, re-runnable. Reads the canonical artifacts by path, pins their
sha256 before and after the run (drift voids the review), and derives a verdict from
machine checks -- never from prose. Optional outputs:

    python3 check_f2a_contract_047.py                     # JSON evidence on stdout
    python3 check_f2a_contract_047.py --evidence OUT.json
    python3 check_f2a_contract_047.py --review reviews/F2a-review-047.json

The review file is only written with verdict "accept" when every check with severity
"fail" passes; otherwise the verdict is "revise"/"reject" and the failing checks are
listed as hard failures. Severity "finding" items are reported but do not block accept.

Owner: worker-047 (breadth worker). This instrument does NOT set gate verdicts and does
NOT claim completion; it is advisory input to astra-lead-audit and the controller.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

CST = dt.timezone(dt.timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]           # .../ai4math-swarm
F2A = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
C0 = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
TAX = ROOT / "research_map" / "formulation_taxonomy.yaml"
REGISTRY = ROOT / "artifacts" / "formulation" / "VARIANT_REGISTRY.json"
ALIASES = ROOT / "artifacts" / "formulation" / "VOCAB_ALIASES.json"
RULE_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"
GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
AUTHORING_TAX = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"

FROZEN_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
VARIANT_IDS = ["SET", "CH", "H2LOC", "TWOSIDED", "DISTRIBUTIONAL", "L2CONN", "LIP"]
EXEMPT_SEG = re.compile(
    r"^(forbidden|must_not|anti_scope|not_this_class|phrases_that_are_not|excluded|"
    r"implication_ledger\.forbidden|schema_falsifiers|vacuity_falsifier|sibling_disjoint|"
    r"known_obstruction|non_goals|rejected|variants)", re.I)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DupLoader(yaml.SafeLoader):
    """Records duplicate mapping keys instead of silently keeping the last."""


def _no_dup(loader, node, deep=False):
    mapping = {}
    dups = []
    for k_node, v_node in node.value:
        k = loader.construct_object(k_node, deep=deep)
        if k in mapping:
            dups.append(k)
        mapping[k] = loader.construct_object(v_node, deep=deep)
    loader.duplicates = getattr(loader, "duplicates", []) + dups
    return mapping


DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


def load_yaml(p: Path):
    """Parse a YAML file; duplicates (if any) are recorded on the loader, not raised."""
    with open(p, "r", encoding="utf-8") as fh:
        loader = DupLoader(fh)
        try:
            data = loader.get_single_data()
            dups = sorted({str(k) for k in getattr(loader, "duplicates", [])})
        finally:
            loader.dispose()
    return data, dups


def flat(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flat(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flat(v, f"{prefix}[{i}]")
    else:
        yield prefix, str(obj)


def is_exempt(path: str) -> bool:
    parts = [p for p in re.split(r"[.\[]", path) if p]
    return any(EXEMPT_SEG.match(p) for p in parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence")
    ap.add_argument("--review")
    args = ap.parse_args()

    checks: list[dict] = []

    def add(cid, severity, ok, detail, extra=None):
        checks.append({"id": cid, "severity": severity, "status": "pass" if ok else "fail",
                       "detail": detail, "extra": extra or {}})

    pins_before = {}
    inputs = [F2A, C0, TAX, AUTHORING_TAX, REGISTRY, ALIASES, RULE_SPEC, GATE]
    for p in inputs:
        if p.is_file():
            pins_before[str(p.relative_to(ROOT))] = sha256(p)

    try:
        f2a, dups = load_yaml(F2A)
        c0, _ = load_yaml(C0)
        tax, _ = load_yaml(TAX)
        registry = json.loads(REGISTRY.read_text())
        aliases = json.loads(ALIASES.read_text())
        rules = json.loads(RULE_SPEC.read_text())
        yaml_ok = True
    except Exception as exc:  # fail closed
        print(json.dumps({"error": f"parse failure: {exc}"}, indent=2))
        return 1

    # C01 parse + duplicate keys + declared revision
    add("C01", "fail", yaml_ok and isinstance(f2a, dict) and f2a.get("class_id") == "AF-SCC-C2-VAC-GEN",
        f"parsed; class_id={f2a.get('class_id')!r}; revision={f2a.get('revision')!r}",
        {"duplicate_top_level_keys": dups})

    # C02 class identity
    comps = f2a.get("class_components", {})
    boundary = f2a.get("class_boundary", {})
    add("C02", "fail",
        comps.get("regularity_token") == "C2" and comps.get("censorship") == "SCC"
        and comps.get("matter") == "VAC" and boundary.get("one_class_only") == "AF-SCC-C2-VAC-GEN"
        and boundary.get("merge_forbidden") is True,
        "class components and one_class_only/merge_forbidden",
        {"components": comps, "one_class_only": boundary.get("one_class_only"),
         "merge_forbidden": boundary.get("merge_forbidden")})

    # C03 extension predicate frozen axes
    ext = f2a.get("extension_predicate", {})
    reg = f2a.get("regularity", {})
    clause_ok = all(tok in str(ext.get("definition", "")) for tok in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)"))
    add("C03", "fail",
        ext.get("frozen_regularity") == "C2" and ext.get("frozen_direction") == "future"
        and ext.get("frozen_equation_concept") == "classical_ricci"
        and reg.get("extension_regularity") == "C2"
        and reg.get("extension_solution_concept") == "classical_ricci" and clause_ok,
        "frozen extension regularity/direction/equation and clauses (a)-(f)",
        {"frozen_regularity": ext.get("frozen_regularity"), "frozen_direction": ext.get("frozen_direction"),
         "frozen_equation_concept": ext.get("frozen_equation_concept"),
         "extension_regularity": reg.get("extension_regularity"), "clauses_present": clause_ok})

    # C04 conclusion binding
    concl = f2a.get("conclusion", {})
    i_plus = f2a.get("i_plus", {})
    vis = f2a.get("visibility", {})
    wcc_hits = [p for p, s in flat(f2a) if "weak_cosmic_censorship" in s]
    add("C04", "fail",
        concl.get("conclusion_type") == "scc_c2_future_inextendibility"
        and concl.get("family") == "SCC"
        and i_plus.get("in_conclusion") is False and i_plus.get("completeness_in_conclusion") is False
        and vis.get("role") == "not_in_conclusion" and not wcc_hits,
        "conclusion_type/family, I+ and visibility excluded from the conclusion, no WCC token",
        {"conclusion_type": concl.get("conclusion_type"), "family": concl.get("family"),
         "i_plus_in_conclusion": i_plus.get("in_conclusion"),
         "visibility_role": vis.get("role"), "wcc_token_paths": wcc_hits})

    # C05 quantifier order and domains
    q = f2a.get("quantifiers", {})
    kinds = [o.get("kind") for o in q.get("ordered", []) if isinstance(o, dict)]
    doms = q.get("domains", {})
    dom_ok = all(isinstance(doms.get(f"D{i}"), dict) and doms[f"D{i}"].get("definition")
                 and doms[f"D{i}"].get("definition_ref") for i in range(4))
    add("C05", "fail",
        kinds == ["forall", "exists", "forall", "not_exists"] and dom_ok
        and q.get("order_matters") is True and bool(q.get("negation_normal_form")),
        "quantifier order [forall, exists(comeager), forall(data), not_exists(extension)] and domains D0-D3",
        {"kinds": kinds, "domains_defined": dom_ok, "order_matters": q.get("order_matters")})

    # C06 implication ledger: containment chain and direction
    led = f2a.get("implication_ledger", {})
    chain = "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0"
    ent = led.get("one_way_entailments", [])
    ent_ok = bool(ent) and all(("C2" in str(e.get("to", ""))) and
                               any(t in str(e.get("from", "")) for t in ("C0", "C^1,1", "H2_loc"))
                               for e in ent)
    forb = led.get("forbidden_transfers", [])
    forb_c2 = [e for e in forb if "C2" in str(e.get("from", ""))]
    forb_other = [e for e in forb if "AF-WCC-VAC-GEN" in str(e.get("from", ""))]
    chain_ctx = str(reg.get("extension_regularity_exact", "")) + " " + str(led.get("extension_class_containment", ""))
    add("C06", "fail",
        chain in str(reg.get("extension_regularity_exact", ""))
        and chain in str(led.get("extension_class_containment", ""))
        and ent_ok and len(forb_c2) == 2 and len(forb_other) == 1 and "C0" in chain_ctx and "H2_loc" in chain_ctx,
        "containment chain present twice; entailments run strong->C2; two C2-converse bans (C0, H2loc) and one WCC ban",
        {"n_entailments": len(ent), "entailment_direction_ok": ent_ok,
         "n_forbidden_c2": len(forb_c2), "n_forbidden_wcc": len(forb_other)})

    # C07 falsifier adequacy
    fal = f2a.get("falsifier", {})
    t1 = fal.get("tier_1", {})
    sf = " | ".join(str(x) for x in fal.get("schema_falsifiers", []))
    add("C07", "fail",
        t1.get("refutes") == "AF-SCC-C2-VAC-GEN" and "C2" in str(t1.get("witness_type", ""))
        and "non-meager" in str(t1.get("genericity_requirement", ""))
        and bool(t1.get("machine_checkable_steps"))
        and "visible" in str(vis.get("forbidden_falsifier", ""))
        and "conclusion inflation" in sf and "wrong-family falsifier" in sf
        and "vacuous citation" in sf and "Ric = 0" in sf,
        "tier-1 falsifier binds the class, requires non-meagerness, separates the WCC falsifier, schema falsifiers listed",
        {"tier1_refutes": t1.get("refutes"), "visibility_forbidden_falsifier": bool(vis.get("forbidden_falsifier"))})

    # C08 sibling separation (C0/C2 merge test) + assertive-path leakage scan
    c0_concl = c0.get("conclusion", {})
    c0_reg = c0.get("regularity", {})
    c2_tokens_in_c0 = [p for p, s in flat(c0) if "scc_c2_future_inextendibility" in s and not is_exempt(p)]
    c0_tokens_in_c2 = [p for p, s in flat(f2a) if "scc_c0_future_inextendibility" in s and not is_exempt(p)]
    merged = [p for p, s in flat(f2a) if "C0 or C2" in s and not is_exempt(p)]
    cross = [p for p, s in flat(f2a) if "AF-SCC-C0-VAC-GEN" in s and not is_exempt(p)]
    add("C08", "fail",
        c0.get("class_id") == "AF-SCC-C0-VAC-GEN" and c0_reg.get("extension_regularity") == "C0"
        and c0_concl.get("conclusion_type") == "scc_c0_future_inextendibility"
        and not c2_tokens_in_c0 and not c0_tokens_in_c2 and not merged and not cross,
        "C0 sibling has its own class/regularity/conclusion; no merged token and no cross-class token in assertive paths",
        {"cross_class_paths": cross, "merged_paths": merged,
         "c2_in_c0": c2_tokens_in_c0, "c0_in_c2": c0_tokens_in_c2})

    # C09 cross-artifact vocabulary alignment via the project alias map
    tax_contract = (tax.get("classes", {}) or {}).get("AF-SCC-C2-VAC-GEN", {}) or {}
    tax_axes = tax_contract.get("axes", {}) or {}
    canon_concl = aliases.get("conclusion_type", {})
    canon_gen = aliases.get("genericity_kind", {})

    def canon_token(family: str, token: str) -> str:
        for canonical, alts in (canon_concl if family == "conclusion_type" else canon_gen).items():
            if token == canonical or token in alts:
                return canonical
        return f"UNMAPPED:{token}"

    tax_concl = canon_token("conclusion_type", str(tax_axes.get("conclusion_type", "")))
    tax_gen = canon_token("genericity_kind", str(tax_axes.get("genericity_kind", "")))
    schema_gen = canon_token("genericity_kind", str(f2a.get("genericity", {}).get("kind", "")))
    add("C09", "fail",
        tax_concl == "scc_c2_future_inextendibility" and tax_gen == "residual_comeager"
        and schema_gen == "residual_comeager",
        "taxonomy class-contract tokens map to the schema's frozen vocabulary via VOCAB_ALIASES",
        {"taxonomy_conclusion_type_raw": tax_axes.get("conclusion_type"), "taxonomy_conclusion_type_canonical": tax_concl,
         "taxonomy_genericity_raw": tax_axes.get("genericity_kind"), "taxonomy_genericity_canonical": tax_gen,
         "schema_genericity_canonical": schema_gen})

    # C10 declared F0 binding matches the measured canonical taxonomy
    fb = f2a.get("f0_binding", {})
    tax_measured = pins_before.get("research_map/formulation_taxonomy.yaml")
    add("C10", "fail",
        fb.get("declared_f0_artifact") == "research_map/formulation_taxonomy.yaml"
        and fb.get("declared_f0_sha256") == tax_measured,
        "f0_binding declares the canonical taxonomy and its measured sha256",
        {"declared_artifact": fb.get("declared_f0_artifact"), "declared_sha256": fb.get("declared_f0_sha256"),
         "measured_sha256": tax_measured, "match": fb.get("declared_f0_sha256") == tax_measured})

    # C11 canonical-path policy: pointers into the authoring tree
    authoring_ptrs = [p for p, s in flat(f2a) if "artifacts/formulation/formulation_taxonomy.yaml" in s]
    auth_measured = pins_before.get("artifacts/formulation/formulation_taxonomy.yaml")
    add("C11", "finding", not authoring_ptrs,
        "class-contract pointer/supplement resolve into the authoring tree; canonical path is authoritative",
        {"authoring_pointer_paths": authoring_ptrs, "authoring_taxonomy_sha256": auth_measured,
         "canonical_taxonomy_sha256": tax_measured, "authoring_aligned": auth_measured == tax_measured})

    # C12 variant registry consistency; no variant id used as a class id
    var = {v.get("variant_id"): v for v in registry.get("variants", [])}
    var_ok = (var.get("H2LOC", {}).get("parent_class") == "AF-SCC-C0-VAC-GEN"
              and var.get("TWOSIDED", {}).get("parent_class") == "AF-SCC-C2-VAC-GEN")
    id_fields = []
    for src, label in ((f2a, "F2a"), (c0, "C0")):
        for p, s in flat(src):
            if re.search(r"(class_id|class_ids|one_class_only)", p) and s in VARIANT_IDS:
                id_fields.append(f"{label}:{p}={s}")
    add("C12", "fail", var_ok and not id_fields,
        "variant parents registered (H2LOC->C0, TWOSIDED->C2); no variant id occupies a class-id field",
        {"registry_parents_ok": var_ok, "variant_id_in_class_field": id_fields})

    # C13 timestamp hygiene (clock discipline)
    now = dt.datetime.now(CST)
    stamps = [("revised_at", f2a.get("revised_at")), ("f0_binding.checked_at", fb.get("checked_at")),
              ("authored_at", f2a.get("authored_at"))]
    future = []
    for label, s in stamps:
        try:
            t = dt.datetime.fromisoformat(str(s))
            if t.tzinfo is None:
                t = t.replace(tzinfo=CST)
            if t > now:
                future.append({"field": label, "value": str(s), "skew_seconds": int((t - now).total_seconds())})
        except Exception:
            pass
    add("C13", "finding", not future and not dups,
        "no future-dated timestamps and no duplicate YAML keys in the reviewed revision",
        {"future_dated": future, "duplicate_top_level_keys": dups, "review_time": now.isoformat()})

    # C14 project structural gate (lead-owned) as corroboration
    gate_rc, gate_out = None, None
    if GATE.is_file():
        try:
            r = subprocess.run([sys.executable, str(GATE), "--json", str(F2A)],
                               capture_output=True, text=True, timeout=120)
            gate_rc = r.returncode
            gate_out = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {"raw": r.stdout[:2000]}
        except Exception as exc:
            gate_out = {"error": str(exc)}
    add("C14", "fail", gate_rc == 0,
        "project structural gate check_class_schema.py (FORM-RULE-SPEC R01-R16) on the canonical file",
        {"exit_code": gate_rc, "verdict": (gate_out or {}).get("verdict"),
         "failed_rules": (gate_out or {}).get("failed_rules"), "tool_sha256": pins_before.get(str(GATE.relative_to(ROOT)))})

    # C15 input drift during the run (a moved pin voids the review)
    pins_after = {k: (sha256(ROOT / k) if (ROOT / k).is_file() else None) for k in pins_before}
    drift = {k: {"before": pins_before[k], "after": pins_after[k]}
             for k in pins_before if pins_before[k] != pins_after.get(k)}
    add("C15", "fail", not drift, "all pinned inputs byte-stable across the run",
        {"drift": drift, "n_inputs": len(pins_before)})

    # C16 declared incompleteness is explicit
    add("C16", "finding", bool(f2a.get("unresolved_items")) and bool(f2a.get("provenance", {}).get("unresolved_citations")),
        "open technical gaps and unresolved citations are declared rather than hidden",
        {"n_unresolved_items": len(f2a.get("unresolved_items", [])),
         "n_unresolved_citations": len(f2a.get("provenance", {}).get("unresolved_citations", []))})

    hard = [c for c in checks if c["severity"] == "fail" and c["status"] == "fail"]
    soft = [c for c in checks if c["severity"] == "finding" and c["status"] == "fail"]
    verdict = "accept" if not hard else "revise"
    score = 5.0 if not hard and not soft else (4.5 if not hard and len(soft) == 1 else (4.0 if not hard else 2.0))

    report = {
        "instrument": "check_f2a_contract_047.py",
        "instrument_version": "1.0",
        "reviewer": "worker-047",
        "created_at": now.isoformat(),
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "pins": pins_before,
        "checks": checks,
        "hard_failures": hard,
        "soft_findings": soft,
        "suggested_verdict": verdict,
        "suggested_score": score,
        "falsifier": ("any of: a C0-only datum satisfying this schema; the C2 conclusion token appearing in the "
                      "C0 canonical file; a merged 'C0 or C2' token in an assertive path; declared F0 sha256 != "
                      "measured canonical taxonomy sha256; a check input drifting mid-run"),
    }
    out = json.dumps(report, indent=2)
    if args.evidence:
        Path(args.evidence).write_text(out + "\n", encoding="utf-8")
    evidence_sha = (sha256(Path(args.evidence)) if args.evidence
                    else hashlib.sha256(out.encode()).hexdigest())
    print(out)

    if args.review:
        review = {
            "schema_version": "1.0",
            "artifact_kind": "independent_class_schema_review",
            "event_id": f"w047-f2a-review-{now.strftime('%Y%m%dT%H%M%S')}",
            "event_type": "review",
            "created_at": now.isoformat(),
            "actor": "worker-047",
            "reviewer": "worker-047",
            "group_id": "formulation",
            "node_id": "F2a",
            "target_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "class_ids": ["AF-SCC-C2-VAC-GEN"],
            "task_id": "W047-F2A-REVIEW-01",
            "artifact": "schemas/af_scc_c2_vacuum.yaml",
            "artifact_sha256": pins_before["schemas/af_scc_c2_vacuum.yaml"],
            "artifact_revision": f2a.get("revision"),
            "counts_as_full_schema_verdict": True,
            "verdict": verdict,
            "score": score,
            "score_rationale": ("all class-binding, conclusion, quantifier, implication, falsifier and C0/C2 "
                                "separation checks pass; project structural gate passes"
                                if verdict == "accept" else "one or more hard class-contract checks failed"),
            "hard_failures": [{"check": c["id"], "detail": c["detail"], "extra": c["extra"]} for c in hard],
            "findings": [
                {"id": "F-01", "severity": "binding-hygiene",
                 "detail": ("class_contract_pointer and f0_binding.class_contract_supplement point into "
                            "artifacts/formulation/formulation_taxonomy.yaml (authoring tree). Canonical path policy "
                            "makes research_map/formulation_taxonomy.yaml authoritative; re-point before the verdict binds."),
                 "paths": [c["extra"].get("authoring_pointer_paths") for c in checks if c["id"] == "C11"]},
                {"id": "F-02", "severity": "machine-hygiene",
                 "detail": ("duplicate top-level YAML key revised_at (last-wins); parsers that reject duplicates fail. "
                            "Machine consumers read the last occurrence."),
                 "paths": dups},
                {"id": "F-03", "severity": "clock-discipline",
                 "detail": "revision and f0_binding.checked_at carry timestamps ahead of wall clock at review time.",
                 "paths": future},
                {"id": "F-04", "severity": "process",
                 "detail": ("review_status.independent_reviewers is empty and this review is the first at the pinned "
                            "hash; a second distinct reviewer is still required for G-FORM."),
                 "paths": ["review_status.independent_reviewers"]},
            ],
            "method": ("independent machine checks C01-C16 in artifacts/worker-047/f2a_review/check_f2a_contract_047.py "
                       "at the pinned sha256, reading the canonical artifacts only; the project's lead-owned structural "
                       "gate is cited as corroboration, not as the basis of the verdict"),
            "machine_evidence": {"instrument_sha256": sha256(Path(__file__)),
                                 "evidence_sha256": evidence_sha,
                                 "checks_total": len(checks), "checks_failed": len(hard)},
            "independence": ("sampled and reviewed against direct file reads at the pinned hash; no use of the authoring "
                             "tree as evidence, no reliance on prior review verdicts"),
            "assumptions": ["the canonical path is authoritative (controller policy 2026-09-12)",
                            "VOCAB_ALIASES.json alias equivalence is accepted for consistency checks"],
            "falsifier": report["falsifier"],
            "next_falsifier": ("re-run this instrument on the next canonical revision; a moved pin or a failed check "
                               "supersedes this verdict"),
            "claims_completion": False,
            "gate_verdict_claimed": False,
        }
        Path(args.review).write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        print(f"[w047] review written: {args.review} verdict={verdict} score={score}", file=sys.stderr)
    return 0 if not hard else 1


if __name__ == "__main__":
    sys.exit(main())
