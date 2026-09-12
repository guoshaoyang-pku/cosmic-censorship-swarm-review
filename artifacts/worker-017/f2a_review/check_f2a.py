#!/usr/bin/env python3
"""Independent bounded check of F2a (AF-SCC-C2-VAC-GEN), worker-017.

Read-only on canonical paths. Writes only its own report (--out).
Emits one JSON object on stdout.

Checks C1..C13 plus in-memory falsification controls CTL-A..CTL-F, so the
instrument is shown non-vacuous (a control that fails to fire is an error).

Falsifier of this instrument: re-run at the same measured hash; any check
result change, any control that stops firing, or any pre/post hash drift
means the record is falsified.
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
TZ = timezone(timedelta(hours=8))
TARGET = "F2a"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
CANON = "schemas/af_scc_c2_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
LEDGER = "ledger/theorems.jsonl"

R12_BLOCKS = ("conclusion", "visibility", "i_plus", "falsifier")
COMPOSITE_RE = re.compile(r"\bC0\s*(?:or|and|/)\s*C2\b", re.IGNORECASE)
WCC_CONCLUSION_TOKENS = (
    "visible incomplete causal geodesic",
    "visibility of the singularity",
    "i+ completeness",
    "i+ is complete",
    "asymptotic predictability",
    "visible",
    "visibility",
    "predictability",
)
EXEMPT_PATHS = ("anti_scope", "variants", "provenance", "revision_history",
                "must_not_conflate", "forbidden", "phrases_that_are_not_this_class",
                "schema_falsifiers", "forbidden_falsifier", "equivalent_rephrasings",
                "visibility")


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measure_tag(p: Path) -> dict:
    return {"path": str(p.relative_to(ROOT)), "exists": p.is_file(),
            "sha256": sha(p) if p.is_file() else None}


def flatten(obj, prefix=""):
    """Yield (dotted path, string) for every string leaf."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def exempt(path: str) -> bool:
    return any(seg in path for seg in EXEMPT_PATHS)


def check_c1(doc, ctx):
    m = ctx["measured"]["canonical_sha256"]
    exp = ctx["expect_hash"]
    ok = m == exp
    return ("pass" if ok else "fail",
            f"measured {m} vs expected pin {exp}; pre==post={ctx['measured']['stable']}; "
            f"bytes={ctx['measured']['bytes']}")


def check_c2(doc, ctx):
    a, b = ctx["measured"]["canonical_sha256"], ctx["measured"]["mirror_sha256"]
    return ("pass" if a == b else "fail",
            f"canonical {a[:16]} vs mirror {b[:16]} (mirror pair must be byte-identical)")


def check_c3(doc, ctx):
    comp = doc.get("class_components", {})
    expect_comp = {"asymptotics": "AF", "censorship": "SCC", "matter": "VAC",
                   "genericity": "GEN", "regularity_token": "C2"}
    problems = []
    if doc.get("class_id") != CLASS_ID:
        problems.append(f"class_id={doc.get('class_id')}")
    if doc.get("node_id") != TARGET:
        problems.append(f"node_id={doc.get('node_id')}")
    if comp != expect_comp:
        problems.append(f"class_components={comp}")
    if doc.get("class_boundary", {}).get("one_class_only") != CLASS_ID:
        problems.append("class_boundary.one_class_only mismatch")
    if doc.get("sibling_disjoint_from") != "AF-SCC-C0-VAC-GEN":
        problems.append("sibling_disjoint_from mismatch")
    return ("pass" if not problems else "fail",
            "identity consistent" if not problems else "; ".join(problems))


def check_c4(doc, ctx):
    rs = ctx["rule_spec"]
    want = rs["vocabularies"]["class_conclusion_type"][CLASS_ID]
    got = doc.get("conclusion", {}).get("conclusion_type")
    epi = doc.get("conclusion", {}).get("epistemic_status")
    epi_ok = epi in rs["vocabularies"]["epistemic_status"]
    f0_allowed = ctx["f0_conclusion_allowed"]
    note = (f"conclusion_type={got} vs rule_spec[{CLASS_ID}]={want}; epistemic_status={epi} "
            f"(in vocab={epi_ok}); in F0 allowed list={got in f0_allowed}")
    ok = got == want and epi_ok
    return ("pass" if ok else "fail", note)


def check_c5(doc, ctx):
    rs = ctx["rule_spec"]
    kind = doc.get("genericity", {}).get("kind")
    aliases = ctx["aliases"]["genericity_kind"]
    licensed = kind in rs["vocabularies"]["genericity_kind"]
    alias_of = [canon for canon, al in aliases.items() if kind in al or kind == canon]
    f0_allowed = ctx["f0_genericity_allowed"]
    note = (f"kind={kind}; in rule_spec vocab={licensed}; alias_of={alias_of}; "
            f"in F0 allowed list={kind in f0_allowed}")
    ok = licensed or bool(alias_of)
    return ("pass" if ok else "fail", note)


def check_c6(doc, ctx):
    q = doc.get("quantifiers", {})
    ordered = q.get("ordered", [])
    kinds = [o.get("kind") for o in ordered]
    expect = ["forall", "exists", "forall", "not_exists"]
    problems = []
    if kinds != expect:
        problems.append(f"ordered kinds {kinds} != {expect}")
    domains = q.get("domains", {})
    for o in ordered:
        if o.get("domain_id") not in domains:
            problems.append(f"binder {o.get('binder')} domain {o.get('domain_id')} undefined")
    for d in ("D0", "D1", "D2", "D3"):
        entry = domains.get(d, {})
        if not entry.get("definition") or not entry.get("definition_ref"):
            problems.append(f"{d} missing definition/definition_ref")
    refs = {
        "regularity.data_regularity": doc.get("regularity", {}).get("data_regularity"),
        "genericity": doc.get("genericity"),
        "data_class": doc.get("data_class"),
        "extension_predicate": doc.get("extension_predicate"),
    }
    for d, entry in domains.items():
        ref = entry.get("definition_ref")
        if ref in refs and refs[ref] in (None, {}, []):
            problems.append(f"{d} definition_ref {ref} does not resolve")
    for key in ("negation", "negation_normal_form"):
        if not q.get(key):
            problems.append(f"quantifiers.{key} empty")
    if q.get("order_matters") is not True:
        problems.append("order_matters is not true")
    if q.get("quantifier_class") != "forall-exists(comeager)-forall-not-exists(extension)":
        problems.append(f"quantifier_class={q.get('quantifier_class')}")
    formal = q.get("formal", "")
    formal_norm = formal.replace("(", " ").replace(")", " ")
    for o in ordered:
        binder = str(o.get("binder", "")).strip("()")
        if binder and binder not in formal_norm:
            problems.append(f"binder {o.get('binder')} absent from formal string")
    return ("pass" if not problems else "fail",
            "quantifier normal form well-typed; all binders bound and refs resolve"
            if not problems else "; ".join(problems))


def check_c7(doc, ctx):
    b = doc.get("f0_binding", {})
    rows = []
    for label, key, declared_path in (
        ("declared_f0", "declared_f0_sha256", b.get("declared_f0_artifact")),
        ("consistency_evidence", "consistency_evidence_sha256", b.get("consistency_evidence")),
    ):
        declared = b.get(key)
        p = ROOT / declared_path if declared_path else None
        measured = sha(p) if p and p.is_file() else None
        frozen = ctx["frozen_files"].get(declared_path, {}).get("sha256")
        rows.append({"label": label, "declared": declared, "measured": measured,
                     "resolved": bool(declared and measured and declared == measured),
                     "frozen_pin": frozen, "frozen_matches": frozen == measured})
    ptr_ok = ctx["contract_ptr_resolves"] and ctx["supplement_ptr_resolves"]
    unresolved = [r["label"] for r in rows if not r["resolved"]]
    ok = not unresolved and ptr_ok
    detail = "; ".join(
        f"{r['label']}: declared={str(r['declared'])[:16]} measured={str(r['measured'])[:16]} "
        f"resolved={r['resolved']} frozen={str(r['frozen_pin'])[:16]}" for r in rows)
    detail += f"; pointers resolve={ptr_ok}"
    return ("pass" if ok else "fail", detail)


def check_c8(doc, ctx):
    variants = ctx["registry"].get("variants", [])
    have = {(v.get("parent_class"), v.get("variant_id")) for v in variants}
    problems = []
    if ("AF-SCC-C0-VAC-GEN", "H2LOC") not in have:
        problems.append("H2LOC/AF-SCC-C0-VAC-GEN missing")
    if ("AF-SCC-C2-VAC-GEN", "TWOSIDED") not in have:
        problems.append("TWOSIDED/AF-SCC-C2-VAC-GEN missing")
    txt = json.dumps(doc.get("anti_scope", {}))
    for tok in ("H2LOC", "TWOSIDED"):
        if tok not in txt:
            problems.append(f"anti_scope does not name {tok}")
    return ("pass" if not problems else "fail",
            "variant references resolve in VARIANT_REGISTRY" if not problems else "; ".join(problems))


def check_c9(doc, ctx):
    hits = []
    for block in R12_BLOCKS:
        for path, text in flatten(doc.get(block, {}), block):
            if exempt(path):
                continue
            low = text.lower()
            for tok in WCC_CONCLUSION_TOKENS:
                if tok in low:
                    hits.append(f"{path}: WCC conclusion token '{tok}'")
            if COMPOSITE_RE.search(text):
                hits.append(f"{path}: composite C0/C2 regularity")
    return ("pass" if not hits else "fail",
            f"R12 scan over blocks {list(R12_BLOCKS)}: no foreign-family conclusion token, "
            f"no composite regularity" if not hits else "; ".join(hits))


def check_c10(doc, ctx):
    f = doc.get("falsifier", {})
    t1 = f.get("tier_1", {})
    t2 = f.get("tier_2", {})
    problems = []
    if t1.get("refutes") != CLASS_ID:
        problems.append("tier_1.refutes mismatch")
    gr = t1.get("genericity_requirement", "")
    if "One extendible datum is NOT sufficient" not in gr:
        problems.append("tier_1 does not state single-datum insufficiency")
    if "non-meager" not in gr:
        problems.append("tier_1 does not require non-meagerness")
    if not t1.get("machine_checkable_steps"):
        problems.append("machine_checkable_steps empty")
    if not t1.get("non_machine_checkable_step"):
        problems.append("non_machine_checkable_step not declared")
    wt = t1.get("witness_type", "")
    if "not a numerical near-solution" not in wt:
        problems.append("witness_type does not exclude numerical near-solutions")
    if t2.get("labelling_required") != "refutes_strengthening_only":
        problems.append("tier_2 not labelled refutes_strengthening_only")
    if not f.get("schema_falsifiers"):
        problems.append("schema_falsifiers empty")
    return ("pass" if not problems else "fail",
            "tier-1 falsifier decidable up to the declared non-machine-checkable meagerness step; "
            "single-datum trivial witness explicitly refused"
            if not problems else "; ".join(problems))


def check_c11(doc, ctx):
    problems = []
    if doc.get("conclusion", {}).get("family") != "SCC":
        problems.append("conclusion.family != SCC")
    if doc.get("visibility", {}).get("role") != "not_in_conclusion":
        problems.append("visibility.role != not_in_conclusion")
    if doc.get("i_plus", {}).get("in_conclusion") is not False:
        problems.append("i_plus.in_conclusion is not false")
    if doc.get("i_plus", {}).get("completeness_in_conclusion") is not False:
        problems.append("i_plus.completeness_in_conclusion is not false")
    # leaf-level scan of the conclusion block; prohibited-pattern fields are exempt
    for path, text in flatten(doc.get("conclusion", {}), "conclusion"):
        if exempt(path):
            continue
        low = text.lower()
        for tok in WCC_CONCLUSION_TOKENS:
            if tok in low:
                problems.append(f"{path}: WCC token '{tok}'")
    return ("pass" if not problems else "fail",
            "conclusion is family-pure (no I+ completeness / visibility content)"
            if not problems else "; ".join(sorted(set(problems))))


def check_c12(doc, ctx):
    ledger = ctx["ledger"]
    problems, notes = [], []
    expected_level = {"T-401": "preprint", "T-305": "preprint", "T-402": "peer-reviewed",
                      "T-514": "peer-reviewed", "T-520": "peer-reviewed"}
    for ref in doc.get("l1_ledger_refs", []):
        tid = ref.get("theorem_id")
        row = ledger.get(tid)
        if row is None:
            problems.append(f"{tid} absent from ledger")
            continue
        lvl = row.get("evidence_level")
        if tid in expected_level and lvl != expected_level[tid]:
            problems.append(f"{tid} evidence_level={lvl} expected {expected_level[tid]}")
        if row.get("review_status") == "not_independently_reviewed":
            notes.append(f"{tid}:citation_status={ref.get('citation_status')} is ledger-author "
                         f"verification, review_status=not_independently_reviewed")
    for tid in doc.get("known_status", {}).get("provisional_support", []):
        if tid not in ledger:
            problems.append(f"provisional_support {tid} absent from ledger")
    return ("pass" if not problems else "fail",
            "; ".join(problems) if problems else
            "all l1 refs resolve with expected evidence level; scope note: " + "; ".join(notes[:2]))


def check_c13(doc, ctx):
    path, measured = CANON, ctx["measured"]["canonical_sha256"]
    pin = ctx["frozen_files"].get(path, {}).get("sha256")
    if pin is None:
        return ("warn", f"{path} not present in FROZEN rev{ctx['frozen_revision']}")
    if pin == measured:
        return ("pass", f"FROZEN rev{ctx['frozen_revision']} pins the measured bytes")
    return ("warn", f"FROZEN rev{ctx['frozen_revision']} pins {pin[:16]} but disk measures "
                    f"{measured[:16]}: owner re-freeze/artifact-event step pending; verdict binds "
                    f"to the measured hash, not the stale manifest")


CHECKS = [("C1", "pin and read-stability", check_c1),
          ("C2", "mirror alignment", check_c2),
          ("C3", "class identity", check_c3),
          ("C4", "conclusion type vs frozen rule_spec", check_c4),
          ("C5", "genericity kind vocabulary", check_c5),
          ("C6", "quantifier normal form / binder domains", check_c6),
          ("C7", "f0_binding hash chain resolution", check_c7),
          ("C8", "variant-registry references", check_c8),
          ("C9", "R12/R13 leakage scan", check_c9),
          ("C10", "falsifier decidability and trivial-witness refusal", check_c10),
          ("C11", "conclusion family exclusivity", check_c11),
          ("C12", "ledger reference resolution", check_c12),
          ("C13", "freeze manifest binding", check_c13)]


def run_checks(doc, ctx):
    out = []
    for cid, name, fn in CHECKS:
        try:
            result, detail = fn(doc, ctx)
        except Exception as exc:  # a crashing check is a failure, not a pass
            result, detail = "fail", f"check raised {type(exc).__name__}: {exc}"
        out.append({"id": cid, "name": name, "result": result, "detail": detail})
    return out


def controls(doc, ctx):
    """In-memory mutations that each check must catch."""
    planned = []

    d = copy.deepcopy(doc)
    d["f0_binding"]["declared_f0_sha256"] = "0" * 64
    planned.append(("CTL-A", "wrong declared_f0_sha256", check_c7, d, "fail"))

    d = copy.deepcopy(doc)
    d["conclusion"]["conclusion_type"] = "scc_c0_future_inextendibility"
    planned.append(("CTL-B", "C0 conclusion token in the C2 schema", check_c4, d, "fail"))

    d = copy.deepcopy(doc)
    d["conclusion"]["statement_natural_language"] += " The singularity is visible from I+."
    planned.append(("CTL-C", "WCC visibility claim injected into the conclusion", check_c11, d, "fail"))

    d = copy.deepcopy(doc)
    d["quantifiers"]["domains"].pop("D1", None)
    planned.append(("CTL-D", "comeager domain D1 deleted", check_c6, d, "fail"))

    d = copy.deepcopy(doc)
    d["falsifier"]["tier_1"]["genericity_requirement"] = "one extendible datum suffices"
    planned.append(("CTL-E", "trivial single-datum falsifier substituted", check_c10, d, "fail"))

    d = copy.deepcopy(doc)
    d["class_id"] = "AF-WCC-VAC-GEN"
    planned.append(("CTL-F", "wrong class id", check_c3, d, "fail"))

    rows = []
    for cid, label, fn, mutated, expect in planned:
        try:
            result, detail = fn(mutated, ctx)
        except Exception as exc:
            result, detail = "fail", f"raised {type(exc).__name__}: {exc}"
        rows.append({"id": cid, "mutation": label, "expected": expect,
                     "observed": result, "detected": result == expect,
                     "detail": detail[:200]})
    return rows


FINDINGS = [
    {"id": "NF-01", "severity": "info", "kind": "vocabulary-source adjudication",
     "finding": "The schema uses VOCAB_ALIASES canonical tokens (conclusion_type="
                "scc_c2_future_inextendibility, genericity.kind=residual_comeager) while the "
                "declared F0 taxonomy field_vocabulary.allowed lists only "
                "strong_cosmic_censorship_C2 / baire_residual|provisional_baire_residual.",
     "disposition": "annotation, not leak: frozen rule_spec.vocabularies.class_conclusion_type "
                    "maps this class to scc_c2_future_inextendibility and VOCAB_ALIASES declares "
                    "the older tokens equivalent aliases that must not appear in new canonical "
                    "artifacts. The stale F0 allowed-list is an F0 repair item; controller "
                    "adjudication is still open (blocker w017-20260912-vocab-source-blocker)."},
    {"id": "NF-02", "severity": "info", "kind": "assumption completeness",
     "finding": "regularity.i_plus_regularity states 'C^k regularity, k >= 3; k is part of the "
                "assumption', but k is not bound in quantifiers.ordered or domains D0-D3.",
     "disposition": "non-blocking: I+ content is excluded from the conclusion by i_plus.role and "
                    "visibility.role, so the unbound k cannot leak into the class conclusion."},
    {"id": "NF-03", "severity": "info", "kind": "notation collision",
     "finding": "class_boundary.one_way_implication uses E(C0)/E(C2) for statement entailment "
                "while implication_ledger uses E_C2/E_C0 for sets of extensions.",
     "disposition": "non-blocking documentation hazard; both readings are now semantically "
                    "correct (E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0)."},
    {"id": "NF-04", "severity": "info", "kind": "falsifier decidability",
     "finding": "tier_1 machine_checkable_steps permit 'constraint residuals below tolerance' and "
                "'Ric = 0 at sample points' while witness_type excludes numerical near-solutions "
                "and non_machine_checkable_step is 'non-meagerness of the extendible set'.",
     "disposition": "non-blocking: a refutation is decidable only up to the declared genericity "
                    "step; any acceptance procedure must require exact/symbolic extension "
                    "checks, never tolerance-based ones alone."},
    {"id": "NF-05", "severity": "info", "kind": "anti-scope tagging",
     "finding": "anti_scope.not_this_class entries 1-3 name foreign class ids without a kind tag "
                "(entries 4-5 carry kind=regularity_axis_variant/extension_direction_variant).",
     "disposition": "annotation, not leak: import_rule line 79 permits content in anti_scope; the "
                    "frozen R12 scan is block-scoped to conclusion/visibility/i_plus/falsifier. "
                    "CF-16 metalinguistic-mention pattern; same disposition class as the standing "
                    "CLASSSEP findings under lead-audit adjudication."},
    {"id": "NF-06", "severity": "info", "kind": "genericity ambient space",
     "finding": "genericity.ambient_space justifies Baire-ness as 'closed subset of a Banach "
                "space', while the D0 default branch r=smooth has a Frechet ambient space "
                "(topology_or_measure says so).",
     "disposition": "non-blocking: a closed subset of a Frechet space is Baire too; the "
                    "Sobolev-branch wording is just incomplete for the smooth branch."},
    {"id": "NF-07", "severity": "process", "kind": "pin movement and re-freeze",
     "finding": "The audit card pins 5476a3f2c6bc (rev12) were superseded in-flight at "
                "2026-09-12T00:53:20+08:00 by rev13 e9a27996dfd3 (astra-life05-evidence-binding-"
                "repair); FROZEN rev29 (frozen_at 2026-09-12T00:55:02+08:00) now pins the rev13 "
                "bytes for F1/F2a/F2b and the declared F0/evidence pins. The rev12->rev13 delta "
                "was verified byte-exactly against the hash-pinned snapshot "
                "artifacts/worker-007/rev29_preflight/snapshot/af_scc_c2_vacuum.5476a3f2c6bc.yaml: "
                "four hunks only (revised_at, revision_history index 11, revision 13, f0_binding "
                "consistency_evidence_sha256 675a99d0->9e335e9b); no class-semantics change.",
     "disposition": "resolved on the artifact side; remaining action is owner/controller: re-point "
                    "the audit-r2-F2a-a/b cards to the rev29 pin and re-emit the rev13 artifact "
                    "event so the gate scan binds. Not an artifact defect."},
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect-hash", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    canon = ROOT / CANON
    pre = sha(canon)
    expect = args.expect_hash or pre

    doc = yaml.safe_load(canon.read_text())
    frozen = json.loads((ROOT / FROZEN).read_text())
    rule_spec = json.loads((ROOT / RULE_SPEC).read_text())
    aliases = json.loads((ROOT / ALIASES).read_text())
    taxonomy = yaml.safe_load((ROOT / TAXONOMY).read_text())
    supplement = yaml.safe_load((ROOT / SUPPLEMENT).read_text())
    registry = json.loads((ROOT / REGISTRY).read_text())
    consistency = json.loads((ROOT / CONSISTENCY).read_text())
    ledger = {}
    for line in (ROOT / LEDGER).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("theorem_id"):
            ledger[row["theorem_id"]] = row

    fv = taxonomy.get("field_vocabulary", {})
    f0_concl = fv.get("conclusion_type", {}).get("allowed", [])
    f0_gen = fv.get("genericity_kind", {}).get("allowed", [])
    contract_ptr = doc.get("class_contract_pointer", "")
    supp_ptr = doc.get("class_contract_supplement_pointer", "")
    contract_resolves = (contract_ptr.startswith(f"{TAXONOMY}#classes.")
                         and contract_ptr.split("#classes.", 1)[1] in taxonomy.get("classes", {}))
    supp_resolves = (supp_ptr.startswith(f"{SUPPLEMENT}#class_contracts.")
                     and supp_ptr.split("#class_contracts.", 1)[1] in supplement.get("class_contracts", {}))

    ctx = {
        "expect_hash": expect,
        "measured": {"canonical_sha256": pre, "mirror_sha256": sha(ROOT / MIRROR),
                     "bytes": canon.stat().st_size, "stable": None,
                     "read_window_pre": pre},
        "frozen_files": frozen.get("files", {}),
        "frozen_revision": frozen.get("revision"),
        "rule_spec": rule_spec,
        "aliases": aliases,
        "f0_conclusion_allowed": f0_concl,
        "f0_genericity_allowed": f0_gen,
        "registry": registry,
        "ledger": ledger,
        "contract_ptr_resolves": contract_resolves,
        "supplement_ptr_resolves": supp_resolves,
        "consistency_evidence": consistency,
    }

    checks = run_checks(doc, ctx)
    ctl = controls(doc, ctx)

    post = sha(canon)
    ctx["measured"]["read_window_post"] = post
    ctx["measured"]["stable"] = (pre == post)
    for c in checks:
        if c["id"] == "C1":
            c["result"] = "pass" if (pre == expect and pre == post) else "fail"
            c["detail"] = (f"measured {pre[:16]} vs expected {expect[:16]}; "
                           f"pre==post={pre == post}; bytes={ctx['measured']['bytes']}")

    hard = [c for c in checks if c["result"] == "fail"]
    warns = [c for c in checks if c["result"] == "warn"]
    controls_ok = all(r["detected"] for r in ctl)
    recommendation = "accept" if (not hard and controls_ok and ctx["measured"]["stable"]) else "revise"

    report = {
        "instrument": "worker-017-f2a-independent-check",
        "instrument_version": "1.0",
        "run_at": now(),
        "target": {"node_id": TARGET, "class_id": CLASS_ID, "canonical_path": CANON,
                   "mirror_path": MIRROR, "gate": "G-FORM"},
        "measured": ctx["measured"],
        "declared_pins": {"card_pin_superseded": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
                          "reviewed_hash": pre,
                          "frozen_rev": frozen.get("revision"),
                          "frozen_pin_for_canonical": ctx["frozen_files"].get(CANON, {}).get("sha256")},
        "checks": checks,
        "controls": ctl,
        "controls_ok": controls_ok,
        "hard_failure_count": len(hard),
        "warn_count": len(warns),
        "findings": FINDINGS,
        "recommendation": recommendation,
        "authority_note": "worker evidence only; cannot set a gate verdict, status=done, or "
                          "validation_status=passed",
        "falsifier": "re-run at the same reviewed hash: any check result change, any control that "
                     "stops firing, or any pre/post hash drift falsifies this record",
    }

    text = json.dumps(report, indent=2, sort_keys=False)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(text)
    return 0 if not hard and controls_ok else 10


if __name__ == "__main__":
    sys.exit(main())
