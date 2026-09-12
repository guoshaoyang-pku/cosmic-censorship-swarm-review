#!/usr/bin/env python3
"""W069-F2B-REV12-INDEPENDENT-VERDICT-01: independent G-FORM checker for F2b.

Class: AF-SCC-C0-VAC-GEN   Node: F2b   Target: schemas/af_scc_c0_vacuum.yaml
Pinned target sha256: 55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6

Written by worker-069 from evaluation_rubric.yaml#G-FORM, the frozen F0 class contract,
the schema's own declared contract, and the standing review findings at this hash. It is
NOT an author self-test: worker-069 authored none of the reviewed artifacts. All checks are
deterministic and read-only on canonical paths; mutations are applied only to in-memory or
temp copies of the snapshot.

Usage:
  python3 check_f2b_rev12_independent.py [--subject PATH] [--out PATH] [--controls]
Exit: 0 all checks pass (no hard failures); 1 at least one hard failure; 2 input/pin error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot"
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))

TASK_ID = "W069-F2B-REV12-INDEPENDENT-VERDICT-01"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"

PATHS = {
    "subject": "schemas/af_scc_c0_vacuum.yaml",
    "f0": "research_map/formulation_taxonomy.yaml",
    "supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "frozen": "artifacts/formulation/FROZEN.json",
    "aliases": "artifacts/formulation/VOCAB_ALIASES.json",
    "rubric": "evaluation_rubric.yaml",
    "stage1": "artifacts/formulation/tools/check_class_schema.py",
    "stage2": "artifacts/worker-06/spec_conformance_audit.py",
    "run_acceptance": "artifacts/formulation/tools/run_acceptance.py",
    "verify_frozen": "artifacts/formulation/tools/verify_frozen.py",
    "classsep_regression": "runtime/bin/classsep_regression.py",
    "classsep_module": "research_map/class_separation.py",
    "artifact_hashes": "runtime/state/artifact_hashes.json",
}

EXPECTED = {
    "subject": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "f0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "supplement": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "evidence": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "frozen": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "aliases": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "rubric": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "stage1": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "stage2": "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "classsep_module": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
}

F0_AXES = {
    "asymptotics": {"AF", "asymptotically_flat_3p1", "asymptotically_flat"},
    "censorship": {"SCC", "strong_cosmic_censorship"},
    "matter": {"VAC", "vacuum"},
    "genericity": {"GEN", "provisional_baire_residual", "residual_comeager", "baire_residual"},
    "regularity_token": {"C0"},
}

PIN_REFS = {
    "subject": "schemas/af_scc_c0_vacuum.yaml",
    "f0": "research_map/formulation_taxonomy.yaml",
    "supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "frozen": "artifacts/formulation/FROZEN.json",
    "aliases": "artifacts/formulation/VOCAB_ALIASES.json",
    "rubric": "evaluation_rubric.yaml",
}


class DupKeyError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    pass


def _strict_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise DupKeyError(f"duplicate mapping key {key!r} at line {key_node.start_mark.line + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping
)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_yaml(text: str):
    return yaml.load(text, Loader=StrictLoader)


def get(d, dotted, default=None):
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def text_of(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def run(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    return {"cmd": cmd, "exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr[-4000:]}


# --------------------------------------------------------------------------- checks
def build_checks(doc, ctx):
    checks = []

    def add(cid, title, fn):
        try:
            ok, detail = fn(doc, ctx)
        except Exception as e:  # fail closed on checker error
            ok, detail = False, f"CHECKER ERROR: {type(e).__name__}: {e}"
        checks.append({"id": cid, "title": title, "ok": bool(ok), "detail": detail})

    # ---- structure / provenance
    add("S01", "target bytes match the frozen rev12 pin 55d0a1ea",
        lambda d, c: (c["pins"]["subject"] == EXPECTED["subject"],
                      f"measured {c['pins']['subject'][:16]} expected {EXPECTED['subject'][:16]}"))
    add("S02", "strict parse: no duplicate mapping key anywhere; document parses",
        lambda d, c: (True, "strict SafeLoader duplicate-key rejection passed"))
    add("S03", "required top-level blocks present",
        lambda d, c: _check_required(d, c))
    add("S04", "class_id/node_id/owner/artifact_kind/schema_version/revision exact",
        lambda d, c: _check_identity(d, c))
    add("S05", "revised_at single, equals last revision_history.at, not future-dated",
        lambda d, c: _check_timestamps(d, c))
    add("S06", "revision_history indices unique and terminal index == revision",
        lambda d, c: _check_revhistory(d))

    # ---- class identity + F0 binding
    add("I01", "class_components axes agree with canonical F0 class axes",
        lambda d, c: _check_axes(d, c))
    add("I02", "class_contract_pointer resolves in canonical F0 at classes.<class_id>",
        lambda d, c: _check_pointer(d, c))
    add("I03", "supplement pointer is a separate field and resolves in the supplement tree",
        lambda d, c: _check_supplement(d, c))
    add("I04", "declared_f0_sha256 equals the measured canonical F0 hash",
        lambda d, c: _check_f0_declared(d, c))
    add("I05", "conclusion_type is the canonical C0 token; alias-maps to F0 conclusion_type",
        lambda d, c: _check_conclusion_token(d, c))
    add("I06", "no WCC/C2 content asserted inside the conclusion block",
        lambda d, c: _check_conclusion_scope(d))
    add("I07", "single class identity; sibling declared; no composite C0/C2 class token",
        lambda d, c: _check_single_class(d))
    add("I08", "declared consistency_evidence_sha256 resolves at the canonical evidence path",
        lambda d, c: _check_evidence_pin(d, c))
    add("I09", "consistency evidence binds the compared trees by hash (input pins present)",
        lambda d, c: _check_evidence_binds_inputs(d, c))
    add("I10", "checked_at not after subject mtime; F0 refresh rule recorded",
        lambda d, c: _check_checked_at(d, c))

    # ---- quantifiers
    add("Q01", "quantifier prefix exact: forall r in D0 ... not exists extension",
        lambda d, c: _check_quantifier_prefix(d))
    add("Q02", "ordered quantifier kinds [forall,exists,forall,not_exists] resolve over D0-D3",
        lambda d, c: _check_ordered(d))
    add("Q03", "each domain has a definition and a resolving definition_ref",
        lambda d, c: _check_domains(d))
    add("Q04", "D0 is a tagged disjoint union over r; no pair-typed binder residue",
        lambda d, c: _check_d0(d))
    add("Q05", "negation and negation_normal_form present and state non-meagerness",
        lambda d, c: _check_negation(d))
    add("Q06", "order_matters + comeager independent of data + negated existential recorded",
        lambda d, c: _check_order(d))
    add("Q07", "conclusion.statement_formal has the same quantifier shape as quantifiers.formal",
        lambda d, c: _check_statement_shape(d))

    # ---- content axes
    add("C01", "data_class: vacuum, Lambda=0, both constraints, named regularity/decay",
        lambda d, c: _check_data_class(d))
    add("C02", "topology: 4d, one AF end, I+/I-/i0, no forbidden slice topology",
        lambda d, c: _check_topology(d))
    add("C03", "extension regularity exactly C0 and no smuggled differentiability",
        lambda d, c: _check_regularity(d))
    add("C04", "genericity kind in rubric vocabulary; part of class; excluded set recorded",
        lambda d, c: _check_genericity(d, c))
    add("C05", "genericity transfer rules present in both directions; no silent strengthening",
        lambda d, c: _check_transfers(d))
    add("C06", "extension_predicate clauses (a)-(f) with interior future clause; no equation",
        lambda d, c: _check_extension_predicate(d))
    add("C07", "non-vacuity marked unverified but recorded; C0=>C2 direction correct",
        lambda d, c: _check_nonvacuity(d))
    add("C08", "I+ and visibility excluded from the conclusion",
        lambda d, c: _check_iplus_visibility(d))
    add("C09", "falsifier finite/checkable; tier-1 non-meagerness; tier-2 labelled strengthening-only",
        lambda d, c: _check_falsifier(d))
    add("C10", "implication ledger containment C0>=H2loc>=C2; forbidden C2->C0 transfer",
        lambda d, c: _check_implications(d))
    add("C11", "four declared unresolved items retained; conditional refutation quarantined",
        lambda d, c: _check_unresolved(d))
    add("C12", "anti-scope excludes the three sibling classes and lists non-class phrases",
        lambda d, c: _check_antiscope(d))
    add("C13", "review_status: no self-certified reviewers; two requested; G-FORM gate named",
        lambda d, c: _check_review_status(d))
    add("C14", "known obstruction (Kerr) recorded; genericity necessity stated",
        lambda d, c: _check_obstruction(d))

    # ---- repo gates reproduced on the snapshot
    add("F01", "canonical structural gate verdict=pass, failed_rules=[] on the snapshot",
        lambda d, c: _check_stage(c, "stage1"))
    add("F02", "semantic stage (stage 2) verdict on the snapshot recorded as pass",
        lambda d, c: _check_stage(c, "stage2"))
    add("F03", "FROZEN rev28 verify_frozen: exit 0, 0 problems",
        lambda d, c: _check_frozen(c))
    add("F04", "repository class-separation regression PASS",
        lambda d, c: _check_classsep_regression(c))
    add("F05", "class_separation.findings on the snapshot report 0 findings",
        lambda d, c: _check_classsep_module(d, c))
    add("F06", "FROZEN rev28 pins subject/F0/supplement/evidence exactly",
        lambda d, c: _check_frozen_pins(c))
    add("F07", "two-stage acceptance pipeline status recorded (PASS required for clean accept)",
        lambda d, c: _check_acceptance(c))
    return checks


def _check_required(d, c):
    needed = ["schema_version", "artifact_kind", "class_id", "node_id", "revision",
              "class_components", "class_contract_pointer", "quantifiers", "data_class",
              "regularity", "genericity", "conclusion", "falsifier", "f0_binding",
              "extension_predicate", "topology", "visibility", "i_plus", "anti_scope"]
    missing = [k for k in needed if k not in d]
    return not missing, f"missing={missing}" if missing else f"{len(needed)} required blocks present"


def _check_identity(d, c):
    want = {"class_id": CLASS_ID, "node_id": NODE_ID, "artifact_kind": "class_schema",
            "owner": "lead-formulation"}
    bad = {k: (d.get(k), v) for k, v in want.items() if d.get(k) != v}
    if d.get("revision") != 12:
        bad["revision"] = (d.get("revision"), 12)
    if not str(d.get("schema_version", "")).startswith("1."):
        bad["schema_version"] = (d.get("schema_version"), "1.x")
    return not bad, f"mismatches={bad}" if bad else "class_id/node_id/kind/owner/revision exact at rev12"


def _check_timestamps(d, c):
    stamps = []
    ra = d.get("revised_at")
    hist = d.get("revision_history") or []
    if not isinstance(ra, str):
        return False, "revised_at missing or not a string"
    stamps.append(("revised_at", ra))
    if hist and isinstance(hist[-1], dict):
        last = hist[-1].get("at")
        if last != ra:
            return False, f"revised_at {ra} != last revision_history.at {last}"
    for i, row in enumerate(hist):
        if isinstance(row, dict) and isinstance(row.get("at"), str):
            stamps.append((f"history[{i}]", row["at"]))
    now = datetime.now(CST)
    future = []
    for name, s in stamps:
        try:
            t = datetime.fromisoformat(s)
        except Exception:
            return False, f"unparseable timestamp {name}={s}"
        if t.tzinfo is None:
            t = t.replace(tzinfo=CST)
        if t > now:
            future.append((name, s))
    return not future, f"future={future} (run clock {now.isoformat()})" if future else f"{len(stamps)} timestamps not future-dated; revised_at == terminal history entry"


def _check_revhistory(d):
    hist = d.get("revision_history") or []
    rows = [r for r in hist if isinstance(r, dict)]
    idx = [r.get("index") for r in rows]
    if not idx:
        return False, "revision_history empty"
    if len(idx) != len(set(idx)):
        return False, f"duplicate revision_history indices: {idx}"
    if idx != sorted(idx):
        return False, f"revision_history indices not increasing: {idx}"
    if rows[-1].get("at") != d.get("revised_at"):
        return False, f"terminal history entry at {rows[-1].get('at')!r} != revised_at {d.get('revised_at')!r}"
    return True, f"{len(idx)} unique increasing history entries; terminal entry == revised_at"


def _norm_kind(kind):
    return {"residual_comeager": "comeager", "provisional_baire_residual": "comeager",
            "baire_residual": "comeager", "comeager": "comeager",
            "GEN": "comeager"}.get(str(kind), str(kind))


def _check_axes(d, c):
    comp = d.get("class_components") or {}
    axes = get(c["f0"], f"classes.{CLASS_ID}.axes", {}) or {}
    if not axes:
        return False, f"canonical F0 has no axes for {CLASS_ID}"
    problems = []
    pairs = [("asymptotics", comp.get("asymptotics"), axes.get("asymptotics")),
             ("censorship", comp.get("censorship"), axes.get("family")),
             ("matter", comp.get("matter"), axes.get("matter_model")),
             ("genericity", comp.get("genericity"), axes.get("genericity_kind")),
             ("regularity_token", comp.get("regularity_token"), axes.get("regularity_token"))]
    for name, got, ref in pairs:
        allowed = F0_AXES.get(name, set())
        if got not in allowed:
            problems.append(f"{name}: schema {got!r} not in allowed {sorted(allowed)}")
        if ref is not None and str(ref) not in allowed:
            problems.append(f"{name}: F0 {ref!r} not in allowed {sorted(allowed)}")
    if _norm_kind(comp.get("genericity")) != _norm_kind(axes.get("genericity_kind")):
        problems.append(f"genericity kind mismatch schema {comp.get('genericity')!r} "
                        f"vs F0 {axes.get('genericity_kind')!r}")
    return not problems, f"problems={problems}" if problems else "all five axes agree with canonical F0 (alias-set normalized)"


def _check_pointer(d, c):
    ptr = str(d.get("class_contract_pointer", ""))
    if "#" not in ptr:
        return False, f"pointer has no anchor: {ptr!r}"
    path, anchor = ptr.split("#", 1)
    if path != PATHS["f0"]:
        return False, f"pointer path {path!r} is not the canonical declared F0 {PATHS['f0']!r}"
    parts = anchor.split(".")
    target = get(c["f0"], anchor)
    if target is None:
        # try dotted navigation
        cur = c["f0"]
        for part in parts:
            cur = cur.get(part) if isinstance(cur, dict) else None
            if cur is None:
                break
        target = cur
    if not isinstance(target, dict):
        return False, f"anchor {anchor!r} does not resolve to a mapping in canonical F0"
    if target.get("axes", {}).get("regularity_token") != "C0":
        return False, f"anchor resolves but regularity_token={target.get('axes', {}).get('regularity_token')!r}"
    return True, f"{ptr} resolves; class axes present in canonical F0"


def _check_supplement(d, c):
    ptr = d.get("class_contract_supplement_pointer")
    if not isinstance(ptr, str) or "#" not in ptr:
        return False, f"supplement pointer missing/ill-formed: {ptr!r}"
    sup_field = d.get("class_contract_supplement") or get(d, "f0_binding.class_contract_supplement")
    if not sup_field:
        return False, "no separate class_contract_supplement field (top level or f0_binding)"
    if str(sup_field) != PATHS["supplement"]:
        return False, f"supplement field {sup_field!r} != {PATHS['supplement']!r}"
    path, anchor = ptr.split("#", 1)
    if path != PATHS["supplement"]:
        return False, f"supplement path {path!r} != {PATHS['supplement']!r}"
    cur = c["supplement"]
    for part in anchor.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return False, f"anchor {anchor!r} does not resolve in supplement"
    if d.get("class_contract_pointer") == ptr:
        return False, "supplement pointer equals the canonical pointer (conflation)"
    return True, f"{ptr} resolves in the supplement; distinct from the canonical pointer"


def _check_f0_declared(d, c):
    declared = get(d, "f0_binding.declared_f0_sha256")
    measured = c["pins"]["f0"]
    if declared != measured:
        return False, f"declared {str(declared)[:16]} != measured canonical F0 {measured[:16]}"
    if get(d, "f0_binding.declared_f0_artifact") != PATHS["f0"]:
        return False, f"declared_f0_artifact {get(d,'f0_binding.declared_f0_artifact')!r} != {PATHS['f0']!r}"
    return True, f"declared == measured == {measured[:16]}"


def _check_conclusion_token(d, c):
    tok = get(d, "conclusion.conclusion_type")
    aliases = c["aliases"].get("conclusion_type", {})
    canon = None
    for k, vals in aliases.items():
        if tok == k or tok in vals:
            canon = k
            break
    f0_tok = get(c["f0"], f"classes.{CLASS_ID}.axes.conclusion_type")
    if canon is None:
        return False, f"conclusion_type {tok!r} not in VOCAB_ALIASES"
    canon_f0 = None
    for k, vals in aliases.items():
        if f0_tok == k or f0_tok in vals:
            canon_f0 = k
            break
    if canon_f0 is None:
        return False, f"F0 conclusion_type {f0_tok!r} not in VOCAB_ALIASES"
    if canon != canon_f0:
        return False, f"schema alias-canon {canon!r} != F0 alias-canon {canon_f0!r}"
    if canon != "scc_c0_future_inextendibility":
        return False, f"canonical conclusion token {canon!r} is not the C0 token"
    return True, f"{tok!r} -> {canon!r} == F0 {f0_tok!r}"


def _check_conclusion_scope(d):
    con = d.get("conclusion") or {}
    scan = " ".join(text_of(con.get(k)) for k in
                    ("statement_natural_language", "statement_formal", "equivalent_rephrasings"))
    hits = [t for t in ("C2", "C1", "H2_loc", "I+", "visible", "visibility", "predictab") if t.lower() in scan.lower()]
    if hits:
        return False, f"WCC/C2 tokens in asserted conclusion text: {hits}"
    return True, "conclusion text carries no WCC/C2 content (they appear only in forbidden lists)"


def _check_single_class(d):
    cid = d.get("class_id")
    comp = d.get("class_components") or {}
    problems = []
    if cid != CLASS_ID:
        problems.append(f"class_id {cid!r}")
    if comp.get("regularity_token") != "C0":
        problems.append(f"regularity_token {comp.get('regularity_token')!r}")
    if comp.get("censorship") != "SCC":
        problems.append(f"censorship {comp.get('censorship')!r}")
    if d.get("sibling_disjoint_from") != "AF-SCC-C2-VAC-GEN":
        problems.append(f"sibling_disjoint_from {d.get('sibling_disjoint_from')!r}")
    if not (ROOT / PATHS["subject"]).exists():
        problems.append("F2b canonical path missing")
    f2a = ROOT / "schemas/af_scc_c2_vacuum.yaml"
    if f2a.exists():
        try:
            d2 = parse_yaml(f2a.read_text())
            if d2.get("class_id") != "AF-SCC-C2-VAC-GEN":
                problems.append("sibling F2a class_id mismatch")
        except Exception as e:
            problems.append(f"sibling F2a unreadable: {e}")
    for key in ("class_id", "class_components", "class_contract_pointer"):
        val = text_of(d.get(key))
        if re.search(r"C0\s*[/,&+]?\s*C2|C2\s*[/,&+]?\s*C0|C0\s+or\s+C2|C0\s+and\s+C2", val):
            problems.append(f"composite class token in {key}: {val[:60]!r}")
    return not problems, f"problems={problems}" if problems else "single class AF-SCC-C0-VAC-GEN; sibling C2 separate; no composite token in identity fields"


def _check_evidence_pin(d, c):
    declared = get(d, "f0_binding.consistency_evidence_sha256")
    measured = c["pins"]["evidence"]
    path = get(d, "f0_binding.consistency_evidence")
    if path != PATHS["evidence"]:
        return False, f"consistency_evidence path {path!r} != {PATHS['evidence']!r}"
    if declared != measured:
        return False, (f"declared consistency_evidence_sha256 {str(declared)[:16]} does not resolve: "
                       f"canonical {path} measures {measured[:16]} (FROZEN rev28 pin)")
    return True, f"declared == measured == {measured[:16]}"


def _check_evidence_binds_inputs(d, c):
    ev = c["evidence_obj"]
    keys = set(ev.keys())
    pin_keys = [k for k in keys if "sha256" in k.lower()]
    if not pin_keys:
        return False, ("canonical consistency evidence contains no sha256 of either compared tree "
                       f"(keys={sorted(keys)}); the consistency claim is not bound to the inputs it checks")
    return True, f"evidence binds inputs via {pin_keys}"


def _check_checked_at(d, c):
    checked = get(d, "f0_binding.checked_at")
    rule = get(d, "f0_binding.rule")
    try:
        t = datetime.fromisoformat(checked)
        if t.tzinfo is None:
            t = t.replace(tzinfo=CST)
    except Exception:
        return False, f"checked_at unparseable: {checked!r}"
    mtime = datetime.fromtimestamp(Path(c["subject_path"]).stat().st_mtime, CST)
    if t > mtime:
        return False, f"checked_at {checked} postdates subject mtime {mtime.isoformat()}"
    if not isinstance(rule, str) or "refreshed" not in rule:
        return False, "f0_binding.rule does not require refresh on F0 hash change"
    return True, f"checked_at {checked} <= subject mtime {mtime.isoformat()}; refresh rule present"


def _check_quantifier_prefix(d):
    f = text_of(get(d, "quantifiers.formal"))
    if not re.search(r"forall\s+r\s+in\s+D0", f):
        return False, "formal quantifier does not bind r over D0"
    for pat in (r"exists\s+G_r", r"forall\s+\(Sigma,h,K\)", r"not\s+exists"):
        if not re.search(pat, f):
            return False, f"formal quantifier missing {pat!r}"
    rough = [w for w in ("roughly", "essentially", "suitable", "or C2") if w in f.lower()]
    if rough:
        return False, f"inexact quantifier vocabulary in formal statement: {rough}"
    return True, "forall r in D0 / exists G_r / forall data / not exists extension; no vague vocabulary"


def _check_ordered(d):
    ordered = get(d, "quantifiers.ordered")
    if not isinstance(ordered, list) or len(ordered) < 4:
        return False, f"ordered quantifier block malformed: {ordered!r}"
    kinds = [r.get("kind") for r in ordered]
    if kinds != ["forall", "exists", "forall", "not_exists"]:
        return False, f"ordered kinds {kinds}"
    domains = get(d, "quantifiers.domains", {}) or {}
    for row in ordered:
        if row.get("domain_id") not in domains:
            return False, f"quantifier domain {row.get('domain_id')!r} absent from domains"
        if not row.get("binder"):
            return False, f"quantifier row without binder: {row!r}"
    return True, f"kinds {kinds} resolve over {sorted(domains)}"


def _check_domains(d):
    domains = get(d, "quantifiers.domains", {}) or {}
    problems = []
    for name, row in domains.items():
        if not isinstance(row, dict) or not row.get("definition"):
            problems.append(f"{name}: no definition")
            continue
        ref = row.get("definition_ref")
        if not isinstance(ref, str) or get(d, ref) is None:
            problems.append(f"{name}: definition_ref {ref!r} does not resolve")
    return not problems, f"problems={problems}" if problems else f"{len(domains)} domains with resolving definition_refs"


def _check_d0(d):
    defn = text_of(get(d, "quantifiers.domains.D0.definition"))
    if "disjoint union" not in defn.lower():
        return False, "D0 definition does not declare a tagged disjoint union"
    if "sobolev" not in defn.lower() or "smooth" not in defn.lower():
        return False, "D0 branches not both named"
    formal = text_of(get(d, "quantifiers.formal"))
    stmt = text_of(get(d, "conclusion.statement_formal"))
    residue = []
    for field, text in (("quantifiers.formal", formal), ("conclusion.statement_formal", stmt)):
        for pat in (r"\(s,\s*delta\)\s+in\s+D0", r"forall\s+\(s", r"G_\{?s", r"X\^\{?s",
                    r"for every admissible \(s"):
            if re.search(pat, text):
                residue.append(f"{field}:{pat}")
    if residue:
        return False, f"pair-typed binder residue: {residue}"
    return True, "D0 tagged union over r (smooth | (sobolev,s,delta)); operative statements bind r only"

def _check_negation(d):
    neg = text_of(get(d, "quantifiers.negation"))
    nnf = text_of(get(d, "quantifiers.negation_normal_form"))
    if not neg or not nnf:
        return False, "negation and/or negation_normal_form missing"
    if "non-meager" not in (neg + nnf).lower() and "nonmeager" not in (neg + nnf).lower():
        return False, "negation does not state non-meagerness of the extendible set"
    return True, "negation + NNF present; extendible set non-meager"


def _check_order(d):
    if get(d, "quantifiers.order_matters") is not True:
        return False, "order_matters is not true"
    note = text_of(get(d, "quantifiers.order_note")).lower()
    if "independently of the data" not in note:
        return False, "order_note does not state the comeager set is fixed independently of the data"
    if "negated existential" not in note:
        return False, "order_note does not state the extension quantifier is a negated existential"
    return True, "order_matters true; order_note records independence and negated existential"


def _check_statement_shape(d):
    stmt = text_of(get(d, "conclusion.statement_formal"))
    for pat in (r"forall\s+r\s+in\s+D0", r"G_r\s+comeager", r"not\s+exists", r"proper_future_extension_in_class"):
        if not re.search(pat, stmt):
            return False, f"statement_formal missing {pat!r}"
    return True, "statement_formal mirrors the forall/exists(comeager)/forall/not-exists shape"


def _check_data_class(d):
    dc = d.get("data_class") or {}
    problems = []
    if dc.get("matter") != "none":
        problems.append(f"matter={dc.get('matter')!r}")
    if dc.get("cosmological_constant") != 0:
        problems.append(f"Lambda={dc.get('cosmological_constant')!r}")
    if "vacuum" not in text_of(dc.get("equations")).lower():
        problems.append("equations not vacuum")
    cons = dc.get("constraints") or {}
    if "hamiltonian" not in cons or "momentum" not in cons:
        problems.append("constraints missing hamiltonian/momentum")
    reg = dc.get("regularity_class") or {}
    if "smooth" not in text_of(reg.get("default")).lower():
        problems.append("default regularity not smooth-with-decay")
    sv = reg.get("sobolev_variant") or {}
    if "5/2" not in text_of(sv.get("s")) or "1/2" not in text_of(sv.get("delta")):
        problems.append("Sobolev variant s/delta not the declared ranges")
    return not problems, f"problems={problems}" if problems else "vacuum, Lambda=0, both constraints, smooth-with-decay + Sobolev variant named"


def _check_topology(d):
    t = d.get("topology") or {}
    problems = []
    if t.get("spacetime_dimension") != 4:
        problems.append(f"dimension={t.get('spacetime_dimension')!r}")
    if "one" not in text_of(t.get("end_structure")).lower():
        problems.append("end structure not one-ended")
    cb = " ".join(text_of(x) for x in (t.get("conformal_boundary") or []))
    for tok in ("I+", "I-", "i0"):
        if tok not in cb:
            problems.append(f"conformal boundary missing {tok}")
    if not t.get("forbidden"):
        problems.append("topology.forbidden empty")
    return not problems, f"problems={problems}" if problems else "4d, one AF end, I+/I-/i0 declared, forbidden slice topologies listed"


def _check_regularity(d):
    r = d.get("regularity") or {}
    problems = []
    if r.get("extension_regularity") != "C0":
        problems.append(f"extension_regularity={r.get('extension_regularity')!r}")
    if "continuous" not in text_of(r.get("extension_regularity_exact")).lower():
        problems.append("extension_regularity_exact does not say continuous")
    if r.get("extension_solution_concept") not in (None, "none"):
        problems.append(f"extension_solution_concept={r.get('extension_solution_concept')!r}")
    mnc = " ".join(text_of(x) for x in (r.get("must_not_conflate") or []))
    if "H2_loc" not in mnc or "C2" not in mnc:
        problems.append("must_not_conflate does not separate H2_loc/C2 from C0")
    return not problems, f"problems={problems}" if problems else "C0 extension regularity exact; H2_loc/C2 separations recorded"


def _check_genericity(d, c=None):
    g = d.get("genericity") or {}
    allowed = {"comeager", "residual_comeager", "full_measure", "open_dense", "codim_ge_1",
               "non_generic_excluded", "provisional_baire_residual", "baire_residual"}
    problems = []
    if g.get("kind") not in allowed:
        problems.append(f"kind={g.get('kind')!r} not in rubric vocabulary")
    f0_kind = get(c["f0"], f"classes.{CLASS_ID}.axes.genericity_kind") if c else None
    if f0_kind is not None and _norm_kind(g.get("kind")) != _norm_kind(f0_kind):
        problems.append(f"genericity kind {g.get('kind')!r} is not the class-contract comeager family {f0_kind!r}")
    if g.get("is_part_of_class") is not True:
        problems.append("is_part_of_class is not true")
    if not g.get("excluded_set_status"):
        problems.append("excluded_set_status not recorded")
    return not problems, f"problems={problems}" if problems else f"kind={g.get('kind')!r} matches F0; part of class; excluded-set status recorded"


def _check_transfers(d):
    g = d.get("genericity") or {}
    tf = g.get("transfer_failures") or []
    th = g.get("transfer_holds") or []
    if len(tf) < 4 or len(th) < 2:
        return False, f"transfer rows incomplete: failures={len(tf)} holds={len(th)}"
    warn = text_of(g.get("class_change_warning")).lower()
    if "no strengthening" not in warn and "strictly stronger" not in warn:
        return False, "class_change_warning does not forbid silent strengthening"
    return True, f"{len(tf)} no-transfer rows + {len(th)} transfer rows; strengthening forbidden"


def _check_extension_predicate(d):
    ep = d.get("extension_predicate") or {}
    defn = text_of(ep.get("definition"))
    problems = []
    for clause in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)"):
        if clause not in defn:
            problems.append(f"clause {clause} absent")
    seg = defn.split("(f)", 1)[1].split("CONVENTION CAVEAT", 1)[0] if "(f)" in defn else ""
    if "non-empty" not in seg or "interior" not in seg.lower():
        problems.append("clause (f) does not require interior future points")
    if "no equation" not in defn.lower():
        problems.append("clause (e) no-equation requirement absent")
    if ep.get("frozen_direction") != "future":
        problems.append(f"frozen_direction={ep.get('frozen_direction')!r}")
    if ep.get("frozen_regularity") != "C0":
        problems.append(f"frozen_regularity={ep.get('frozen_regularity')!r}")
    if ep.get("frozen_equation_concept") not in (None, "none"):
        problems.append(f"frozen_equation_concept={ep.get('frozen_equation_concept')!r}")
    return not problems, f"problems={problems}" if problems else "clauses (a)-(f) present, future+C0 frozen, no equation required"


def _check_nonvacuity(d):
    nv = d.get("non_vacuity") or {}
    problems = []
    for k in ("condition", "witness_type", "status", "vacuity_falsifier"):
        if not nv.get(k):
            problems.append(f"{k} missing")
    note = text_of(nv.get("c0_specific_note")).lower()
    if "c2" not in note or "weaker" not in note:
        problems.append("c0_specific_note does not keep the C0 => C2 direction")
    return not problems, f"problems={problems}" if problems else "non-vacuity recorded (status unverified is explicit, not dropped); direction C0=>C2"


def _check_iplus_visibility(d):
    problems = []
    if get(d, "i_plus.in_conclusion") is not False:
        problems.append("i_plus.in_conclusion is not false")
    if get(d, "i_plus.completeness_in_conclusion") is not False:
        problems.append("i_plus.completeness_in_conclusion is not false")
    if get(d, "visibility.role") != "not_in_conclusion":
        problems.append(f"visibility.role={get(d,'visibility.role')!r}")
    ip_forb = " ".join(text_of(x) for x in (get(d, "i_plus.forbidden", []) or []))
    if not ip_forb:
        problems.append("i_plus.forbidden empty")
    vis_forb = text_of(get(d, "visibility.forbidden_falsifier"))
    if "wcc" not in vis_forb.lower():
        problems.append("visibility.forbidden_falsifier does not name the WCC falsifier")
    return not problems, f"problems={problems}" if problems else "I+ and visibility are assumptions only, both forbidden as conclusion/falsifier"


def _check_falsifier(d):
    f = d.get("falsifier") or {}
    t1 = f.get("tier_1") or {}
    t2 = f.get("tier_2") or {}
    problems = []
    if t1.get("refutes") != CLASS_ID:
        problems.append(f"tier_1.refutes={t1.get('refutes')!r}")
    if not re.search(r"non-meager\b", text_of(t1.get("genericity_requirement")).lower()):
        problems.append("tier_1 genericity requirement does not require non-meagerness")
    if len(t1.get("machine_checkable_steps") or []) < 4:
        problems.append("tier_1 machine-checkable steps < 4")
    if not t1.get("non_machine_checkable_step"):
        problems.append("tier_1 non-machine-checkable step not recorded")
    if t2.get("labelling_required") != "refutes_strengthening_only":
        problems.append(f"tier_2 labelling={t2.get('labelling_required')!r}")
    if len(f.get("schema_falsifiers") or []) < 3:
        problems.append("schema_falsifiers < 3")
    return not problems, f"problems={problems}" if problems else "tier-1 non-meagerness + machine steps; tier-2 labelled strengthening-only; 4 schema falsifiers"


def _check_implications(d):
    il = d.get("implication_ledger") or {}
    containment = text_of(il.get("extension_class_containment"))
    problems = []
    if not all(t in containment for t in ("E_C0", "E_H2loc", "E_C2")):
        problems.append("containment chain incomplete")
    if containment.find("E_C0") > containment.find("E_C2"):
        problems.append("containment chain direction appears reversed")
    ft = " ".join(text_of(x) for x in (il.get("forbidden_transfers") or []))
    if "AF-WCC-VAC-GEN" not in ft:
        problems.append("WCC->C0 forbidden transfer absent")
    if "strictly larger" not in ft:
        problems.append("C2-is-larger forbidden-transfer reason absent")
    if "no wcc" not in text_of(il.get("cross_family")).lower():
        problems.append("cross_family transfer not forbidden")
    return not problems, f"problems={problems}" if problems else "C0 superset chain correct; C2->C0 and WCC->C0 transfers forbidden"


def _check_unresolved(d):
    ui = d.get("unresolved_items") or []
    problems = []
    if len(ui) < 4:
        problems.append(f"only {len(ui)} unresolved items")
    joined = " ".join(text_of(x) for x in ui).lower()
    for tok in ("diffeomorphism", "meagerness", "non-vacuity", "continuous"):
        if tok not in joined:
            problems.append(f"declared unresolved gap {tok!r} not retained")
    why = text_of(get(d, "known_status.why_this_class_is_not_recorded_as_refuted")).lower()
    cons = text_of(get(d, "known_status.consequence")).lower()
    if "interior" not in why:
        problems.append("why-not-refuted does not record the interior-data restriction")
    if "variant" not in cons:
        problems.append("conditional refutation not quarantined to a registered variant")
    return not problems, f"problems={problems}" if problems else "4 unresolved gaps retained; conditional refutation quarantined to variant CH"


def _check_antiscope(d):
    a = d.get("anti_scope") or {}
    ntc = a.get("not_this_class") or []
    ids = set()
    for row in ntc:
        if isinstance(row, dict):
            ids.add(row.get("class_id"))
    problems = []
    for want in ("AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"):
        if want not in ids:
            problems.append(f"anti-scope missing {want}")
    if not a.get("phrases_that_are_not_this_class"):
        problems.append("phrases_that_are_not_this_class empty")
    return not problems, f"problems={problems}" if problems else "three sibling classes + non-class phrases excluded"


def _check_review_status(d):
    rs = d.get("review_status") or {}
    problems = []
    if rs.get("independent_reviewers") not in ([], None):
        problems.append("schema self-certifies independent reviewers")
    if len(rs.get("requested_reviewers") or []) < 2:
        problems.append("fewer than two requested reviewers")
    if rs.get("verdict") != "pending":
        problems.append(f"self-declared verdict {rs.get('verdict')!r}")
    if rs.get("gate") != "G-FORM":
        problems.append(f"gate {rs.get('gate')!r}")
    return not problems, f"problems={problems}" if problems else "no self-certification; 2 requested reviewers; verdict pending; G-FORM"


def _check_obstruction(d):
    ko = text_of(get(d, "conclusion.known_obstruction")).lower()
    problems = []
    if "kerr" not in ko:
        problems.append("Kerr obstruction not recorded")
    if "generic" not in ko and "meager" not in ko:
        problems.append("genericity necessity not stated")
    return not problems, f"problems={problems}" if problems else "Kerr extendible family + genericity necessity recorded"


def _check_stage(c, which):
    r = c["tools"].get(which) or {}
    verdict = r.get("verdict")
    if verdict != "pass":
        return False, f"{which} verdict={verdict!r} failed_rules={r.get('failed_rules')} exit={r.get('exit')}"
    return True, f"{which} verdict=pass failed_rules={r.get('failed_rules')}"


def _check_frozen(c):
    r = c["tools"].get("verify_frozen") or {}
    if r.get("exit") != 0:
        return False, f"verify_frozen exit={r.get('exit')}: {r.get('stdout','')[-300:]}"
    m = re.search(r"(\d+) problems", r.get("stdout", ""))
    n = int(m.group(1)) if m else -1
    if n != 0:
        return False, f"verify_frozen reports {n} problems"
    return True, r.get("stdout", "").strip().splitlines()[0] if r.get("stdout") else "exit 0"


def _check_classsep_regression(c):
    r = c["tools"].get("classsep_regression") or {}
    out = (r.get("stdout") or "") + (r.get("stderr") or "")
    if r.get("exit") != 0 or "PASS" not in out:
        return False, f"classsep_regression exit={r.get('exit')} out={out[-300:]!r}"
    return True, "classsep_regression PASS"


def _check_classsep_module(d, c):
    r = c["tools"].get("classsep_module") or {}
    n = r.get("findings_count")
    if n is None:
        return False, f"module findings unavailable: {r.get('error')}"
    if n != 0:
        return False, f"{n} class-separation findings: {r.get('findings')[:3]}"
    return True, "0 class-separation findings on the subject snapshot"


def _check_frozen_pins(c):
    frozen = c["frozen"]
    files = frozen.get("files") or {}
    problems = []
    for key in ("subject", "f0", "supplement", "evidence"):
        path = PATHS[key]
        rec = files.get(path)
        if not rec:
            problems.append(f"{path} not listed in FROZEN rev{frozen.get('revision')}")
        elif rec.get("sha256") != c["pins"].get(key):
            problems.append(f"{path} manifest {str(rec.get('sha256'))[:12]} != measured {str(c['pins'].get(key))[:12]}")
    logical = frozen.get("logical_artifacts") or {}
    for name, rec in logical.items():
        p = rec.get("path")
        if p in PATHS.values() and rec.get("sha256") != c["pins"].get({v: k for k, v in PATHS.items()}[p]):
            problems.append(f"logical artifact {name} pin mismatch")
    return not problems, f"problems={problems}" if problems else f"FROZEN rev{frozen.get('revision')} pins subject/F0/supplement/evidence exactly"


def _check_acceptance(c):
    r = c["tools"].get("run_acceptance") or {}
    out = (r.get("stdout") or "") + (r.get("stderr") or "")
    ok = r.get("exit") == 0 and "PASS" in out.upper() and "PREFLIGHT FAIL" not in out.upper()
    if not ok:
        return False, f"two-stage acceptance not PASS (exit={r.get('exit')}): {out.strip().splitlines()[-1][:220] if out.strip() else 'no output'}"
    return True, "run_acceptance exit 0 with PASS"


# --------------------------------------------------------------------------- controls
MUTATIONS = [
    ("M01_duplicate_top_key", lambda t: t.replace("class_id: AF-SCC-C0-VAC-GEN\n",
                                                   "class_id: AF-SCC-C0-VAC-GEN\nclass_id: AF-SCC-C0-VAC-GEN\n", 1),
     "S02", False),
    ("M02_wrong_class_id", lambda t: t.replace("class_id: AF-SCC-C0-VAC-GEN", "class_id: AF-SCC-C2-VAC-GEN", 1),
     "S04", False),
    ("M03_c2_conclusion_token", lambda t: t.replace("conclusion_type: scc_c0_future_inextendibility",
                                                     "conclusion_type: scc_c2_future_inextendibility", 1),
     "I05", False),
    ("M04_pair_typed_d0", lambda t: t.replace("forall r in D0:", "forall (s,delta) in D0:", 1),
     "Q01", False),
    ("M05_remove_interior_clause", lambda t: t.replace("int(M' minus iota(M))", "M'", 1).replace(
        "The interior requirement blocks", "This requirement blocks", 1),
     "C06", False),
    ("M06_full_measure_genericity", lambda t: t.replace("kind: residual_comeager", "kind: full_measure", 1),
     "C04", False),
    ("M07_weaken_tier1_genericity", lambda t: t.replace(
        "is non-meager (equivalently", "is nonempty (equivalently", 1),
     "C09", False),
    ("M08_pointer_to_supplement", lambda t: t.replace(
        "class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
        "class_contract_pointer: artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-SCC-C0-VAC-GEN", 1),
     "I02", False),
    ("M09_stale_f0_declared", lambda t: t.replace(
        "declared_f0_sha256: \"0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3\"",
        "declared_f0_sha256: \"276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc\"", 1),
     "I04", False),
    ("M10_correct_evidence_pin_positive_control", lambda t: t.replace(
        "consistency_evidence_sha256: \"675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48\"",
        "consistency_evidence_sha256: \"9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b\"", 1),
     "I08", True),
    ("M11_future_revised_at", lambda t: t.replace('revised_at: "2026-09-12T00:31:41+08:00"',
                                                  'revised_at: "2099-01-01T00:00:00+08:00"', 1),
     "S05", False),
    ("M12_duplicate_history_index", lambda t: t.replace("{index: 10, at:", "{index: 9, at:", 1),
     "S06", False),
    ("M13_reversed_containment", lambda t: t.replace(
        "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0", 1),
     "C10", False),
    ("M14_iplus_in_conclusion", lambda t: t.replace("in_conclusion: false", "in_conclusion: true", 1),
     "C08", False),
    ("M15_drop_c2_antiscope", lambda t: t.replace(
        '- {class_id: AF-SCC-C2-VAC-GEN, why: "different (weaker) statement; C0 containment runs C0 => C2 only"}',
        '- {class_id: AF-WCC-SCALAR-SPH, why: "different matter and symmetry"}', 1),
     "C12", False),
    ("M16_wcc_statement", lambda t: t.replace(
        'statement_formal: "forall r in D0 exists G_r comeager forall D in G_r: not exists proper_future_extension_in_class(MGHD(D))"',
        'statement_formal: "generic AF vacuum data have a complete future null infinity I+"', 1),
     "Q07", False),
    ("M17_residue_pair_index", lambda t: t.replace(
        "forall r in D0: exists G_r", "forall r in D0: exists G_r and X^{s,delta}_vac", 1),
     "Q04", False),
]


def run_controls(subject_text, ctx, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, mutate, check_id, expect_ok in MUTATIONS:
        t2 = mutate(subject_text)
        changed = t2 != subject_text
        rec = {"control": name, "expected_check": check_id, "expected_ok": expect_ok,
               "mutation_applied": changed}
        if not changed:
            rec.update({"control_ok": False, "detail": "mutation did not change the bytes"})
            results.append(rec)
            continue
        tmp = outdir / f"{name}.yaml"
        tmp.write_text(t2)
        try:
            doc2 = parse_yaml(t2)
            checks2 = {c["id"]: c for c in build_checks(doc2, ctx)}
            got = checks2[check_id]["ok"]
            rec.update({"control_ok": (got == expect_ok), "observed_ok": got,
                        "detail": checks2[check_id]["detail"][:220]})
        except DupKeyError as e:
            rec.update({"control_ok": (check_id == "S02" and expect_ok is False),
                        "observed_ok": "DupKeyError", "detail": str(e)[:180]})
        except Exception as e:
            rec.update({"control_ok": False, "observed_ok": None, "detail": f"{type(e).__name__}: {e}"[:180]})
        results.append(rec)
    return results


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default=str(SNAP / "subject__af_scc_c0_vacuum.yaml"))
    ap.add_argument("--out", default=str(RAW / "checker_result.json"))
    ap.add_argument("--controls", action="store_true", default=True)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    subject_path = Path(args.subject)
    subject_text = subject_path.read_text()
    subject_sha = hashlib.sha256(subject_text.encode()).hexdigest()

    pins = {k: sha256_file(ROOT / v) for k, v in PATHS.items() if k not in
            ("stage1", "stage2", "run_acceptance", "verify_frozen", "classsep_regression",
             "classsep_module", "artifact_hashes")}
    for k in ("stage1", "stage2", "classsep_module"):
        pins[k] = sha256_file(ROOT / PATHS[k])
    if subject_sha != EXPECTED["subject"]:
        print(json.dumps({"error": "subject pin mismatch", "measured": subject_sha,
                          "expected": EXPECTED["subject"]}, indent=1))
        return 2

    f0 = parse_yaml((SNAP / "f0__formulation_taxonomy.yaml").read_text())
    supplement = parse_yaml((SNAP / "supplement__formulation_taxonomy.yaml").read_text())
    aliases = json.loads((SNAP / "VOCAB_ALIASES.json").read_text())
    frozen = json.loads((SNAP / "FROZEN.json").read_text())
    evidence_obj = json.loads((SNAP / "evidence__taxonomy_consistency.json").read_text())

    ctx = {"pins": pins, "f0": f0, "supplement": supplement, "aliases": aliases,
           "frozen": frozen, "evidence_obj": evidence_obj, "subject_path": subject_path,
           "tools": {}}

    # canonical tool reproduction (read-only; subject argument is the snapshot copy)
    r1 = run([sys.executable, str(ROOT / PATHS["stage1"]), "--json", str(subject_path)])
    try:
        d1 = json.loads(r1["stdout"])
        ctx["tools"]["stage1"] = {"exit": r1["exit"], "verdict": d1.get("verdict"),
                                  "failed_rules": d1.get("failed_rules")}
    except Exception as e:
        ctx["tools"]["stage1"] = {"exit": r1["exit"], "verdict": f"unparseable: {e}",
                                  "failed_rules": None, "stderr": r1["stderr"][-500:]}
    (RAW / "stage1_stdout.json").write_text(r1["stdout"] or "")
    (RAW / "stage1_stderr.txt").write_text(r1["stderr"] or "")

    r2 = run([sys.executable, str(ROOT / PATHS["stage2"]), str(subject_path)])
    try:
        d2 = json.loads(r2["stdout"])
        ctx["tools"]["stage2"] = {"exit": r2["exit"],
                                  "verdict": "pass" if str(d2.get("verdict", "")).lower() in
                                             ("accept", "pass", "ok") else d2.get("verdict"),
                                  "failed_rules": d2.get("failed_rules")}
    except Exception as e:
        ctx["tools"]["stage2"] = {"exit": r2["exit"], "verdict": f"unparseable: {e}",
                                  "failed_rules": None, "stderr": r2["stderr"][-500:]}
    (RAW / "stage2_stdout.txt").write_text(r2["stdout"] or "")
    (RAW / "stage2_stderr.txt").write_text(r2["stderr"] or "")

    r3 = run([sys.executable, str(ROOT / PATHS["verify_frozen"])])
    ctx["tools"]["verify_frozen"] = {"exit": r3["exit"], "stdout": r3["stdout"], "stderr": r3["stderr"]}
    (RAW / "verify_frozen.txt").write_text(r3["stdout"] + r3["stderr"])

    r4 = run([sys.executable, str(ROOT / PATHS["classsep_regression"])])
    ctx["tools"]["classsep_regression"] = {"exit": r4["exit"], "stdout": r4["stdout"], "stderr": r4["stderr"]}
    (RAW / "classsep_regression.txt").write_text(r4["stdout"] + r4["stderr"])

    r5 = run([sys.executable, str(ROOT / PATHS["run_acceptance"]), "--json"])
    ctx["tools"]["run_acceptance"] = {"exit": r5["exit"], "stdout": r5["stdout"], "stderr": r5["stderr"]}
    (RAW / "run_acceptance.txt").write_text(r5["stdout"] + r5["stderr"])

    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import class_separation as cs
        fnd = cs.findings_for_text(subject_text, PATHS["subject"])
        ctx["tools"]["classsep_module"] = {"findings_count": len(fnd), "findings": fnd}
    except Exception as e:
        ctx["tools"]["classsep_module"] = {"findings_count": None, "error": f"{type(e).__name__}: {e}"}
    (RAW / "classsep_module.json").write_text(json.dumps(ctx["tools"]["classsep_module"], indent=1)[:20000])

    doc = parse_yaml(subject_text)
    checks = build_checks(doc, ctx)
    controls = run_controls(subject_text, ctx, RAW / "controls_dir") if args.controls else []

    drift = {}
    for k, v in PATHS.items():
        if k in ("verify_frozen", "run_acceptance", "classsep_regression", "artifact_hashes"):
            continue
        p = ROOT / v
        if p.exists():
            drift[k] = {"pre": pins.get(k), "post": sha256_file(p)}

    failing = [c for c in checks if not c["ok"]]
    hard = []
    for c in failing:
        hard.append({
            "id": f"HF-069F2B-{c['id']}",
            "check": c["id"],
            "label": c["title"],
            "severity": "blocking-for-clean-accept",
            "detail": c["detail"],
            "falsifier": _falsifier_for(c["id"]),
        })

    ctrl_fail = [c for c in controls if not c["control_ok"]]
    verdict = "accept" if not hard and not ctrl_fail else "revise"
    result = {
        "task_id": TASK_ID,
        "worker": "worker-069",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": "G-FORM",
        "verdict": verdict,
        "score": 4.0 if verdict == "accept" else 3.5,
        "run_at": datetime.now(CST).isoformat(),
        "checker_sha256": sha256_file(Path(__file__)),
        "subject": {"path": PATHS["subject"], "sha256": pins["subject"]},
        "pins": pins,
        "drift": {k: {"drifted": v["pre"] != v["post"], "pre": v["pre"], "post": v["post"]}
                  for k, v in drift.items()},
        "tools": ctx["tools"],
        "checks": checks,
        "check_count": len(checks),
        "checks_passed": len(checks) - len(failing),
        "controls": controls,
        "controls_passed": len(controls) - len(ctrl_fail),
        "hard_failures": hard,
        "adjudication": {
            "worker-098_accept_B1_B2_B3_closed": {
                "B1_duplicate_revised_at": _adjudicate(checks, "S02"),
                "B2_typed_D0_binder": _adjudicate(checks, "Q04"),
                "B3_canonical_pointer_resolves": _adjudicate(checks, "I02"),
            },
            "worker-022_HF-022-R1_consistency_evidence_pin": _adjudicate(checks, "I08"),
            "worker-077_D0_deferral_recorded_not_dropped": _adjudicate(checks, "C11"),
        },
        "independence": ("worker-069 authored none of schemas/af_scc_c0_vacuum.yaml, the F0 taxonomy, "
                         "the supplement, the evidence file or the canonical gate tools. Criteria "
                         "transcribed from evaluation_rubric.yaml#G-FORM, the frozen F0 class contract "
                         "and the schema's own declared contract; author self-tests were not used as "
                         "evidence; 17 mutation controls bound non-vacuity. Not a gate verdict."),
    }
    Path(args.out).write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(json.dumps({k: result[k] for k in
                      ("task_id", "verdict", "score", "check_count", "checks_passed",
                       "controls_passed", "hard_failures")}, indent=1, ensure_ascii=False))
    return 0 if verdict == "accept" else 1


def _adjudicate(checks, cid):
    for c in checks:
        if c["id"] == cid:
            return {"check": cid, "ok": c["ok"], "detail": c["detail"]}
    return {"check": cid, "ok": None, "detail": "check not found"}


def _falsifier_for(cid):
    return {
        "I08": ("regenerate artifacts/formulation/evidence/taxonomy_consistency.json with the measured "
                "sha256 of both compared trees, re-pin it in FROZEN, update the three schemas' "
                "consistency_evidence_sha256 to the new measured value, and re-run; if declared == "
                "measured the finding is void"),
        "I09": ("an evidence generation whose bytes carry the sha256 of the canonical F0 taxonomy and of "
                "the supplement (as the declared 675a99d0 generation did) closes this finding"),
        "F02": ("stage 2 must return pass on the pinned subject bytes; any ACCEPT/exit-0 semantic run "
                "on this snapshot voids the finding"),
        "F07": ("run_acceptance.py on the frozen rev12 bytes must report PASS; a rebuilt rebased fixture "
                "corpus that makes the pipeline pass voids the finding"),
    }.get(cid, "re-measure the named check on byte-identical pinned inputs; a passing value voids it")


if __name__ == "__main__":
    sys.exit(main())
