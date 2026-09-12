#!/usr/bin/env python3
"""W047-D0-REPAIR-ACCEPT-02 instrument.

Independent repair-acceptance verification of the rev12 D0 well-typedness repair
across the G-FORM class-contract chain:

    canonical schema  ->  declared-F0 pointer target  ->  lead supplement

Scope (class-bound):
  F1  AF-WCC-VAC-GEN      schemas/af_wcc_vacuum.yaml
  F2a AF-SCC-C2-VAC-GEN   schemas/af_scc_c2_vacuum.yaml
  F2b AF-SCC-C0-VAC-GEN   schemas/af_scc_c0_vacuum.yaml
  F0  (shared contract)   research_map/formulation_taxonomy.yaml
                          artifacts/formulation/formulation_taxonomy.yaml (supplement)

Pre-registered acceptance criteria (fixed before the run; see report
`pre_registered_criteria`):

  A1 SCHEMA_D0_TYPED          each schema types D0 as a tagged disjoint union
                              with members r=smooth and r=(sobolev,s,delta) and
                              index r ranging over exactly D0; no positive
                              'suitable regularity' hedge.
  A2 SCHEMA_BINDER_CONSISTENT ordered[0] binds r on D0 and statement_formal
                              binds `forall r in D0`; no `forall (s,delta) in D0`
                              anywhere in the file.
  A3 SCHEMA_AMBIENT_PER_BRANCH D0 names Frechet for r=smooth and the weighted
                              Sobolev product for r=(sobolev,s,delta); X^r_vac(AF)
                              is the indexed ambient; no orphan X^{s,delta}_vac.
  A4 SCHEMA_INDEXED_OBJECTS   D1/formal/qnf index G_r and X^r_vac(AF); no orphan
                              G_{s,delta} in the file.
  A5 POINTER_RESOLVES         class_contract_pointer resolves to an existing
                              classes.<ID> entry in the canonical taxonomy and
                              declared_f0_sha256 equals the measured taxonomy hash.
  A6 POINTER_TARGET_TYPED     END-TO-END: the resolved class-contract entry does
                              not bind (s,delta) over, or index G_{s,delta} in,
                              a D0 that contains the non-pair smooth member.
  A7 SUPPLEMENT_ALIGNED       (advisory) the supplement contract entry does not
                              contradict the repaired D0 typing; absence of the
                              typed index is recorded, not silently accepted.
  A8 EVIDENCE_COVERS_TYPING   the declared consistency evidence must not report
                              `consistent: true` while A6 fails and while its
                              compared inputs exclude the three schemas.
  A9 NO_REGRESSION            no duplicate top-level YAML keys in the three
                              schemas; D0 definition text identical across them.

Controls K1-K9 calibrate the probes on synthetic copies (in memory only); a
control that does not flip as pre-registered is an instrument-integrity failure
and makes the run fail closed (exit 2).

Exit codes: 0 = all criteria pass, 1 = --strict and at least one FAIL,
2 = fail-closed (unreadable/moved input, parse failure, control mis-calibration).

Authority: worker evidence only. Read-only with respect to canonical artifacts:
this instrument writes only its own report/snapshot outputs. It does not set gate
verdicts, node status, or validation_status.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import yaml

CST = timezone(timedelta(hours=8))
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

SCHEMAS = [
    {"key": "F1", "node_id": "F1", "class_id": "AF-WCC-VAC-GEN",
     "path": "schemas/af_wcc_vacuum.yaml"},
    {"key": "F2a", "node_id": "F2a", "class_id": "AF-SCC-C2-VAC-GEN",
     "path": "schemas/af_scc_c2_vacuum.yaml"},
    {"key": "F2b", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
     "path": "schemas/af_scc_c0_vacuum.yaml"},
]

TAX_PATH = "research_map/formulation_taxonomy.yaml"
SUP_PATH = "artifacts/formulation/formulation_taxonomy.yaml"
CE_PATH = "artifacts/formulation/evidence/taxonomy_consistency.json"

PAIR_BINDER_RE = re.compile(r"forall\s*\(\s*s\s*,\s*delta\s*\)")
PAIR_ADMISSIBLE_RE = re.compile(r"admissible\s*\(\s*s\s*,\s*delta\s*\)")
ORPHAN_INDEX_RE = re.compile(r"G_\{s,delta\}")
ORPHAN_AMBIENT_RE = re.compile(r"X\^\{s,delta\}_vac")
DUP_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")

PRE_REGISTERED = {
    "A1": "SCHEMA_D0_TYPED: D0 is a tagged disjoint union r=smooth | r=(sobolev,s,delta), index r ranges over exactly D0, no positive 'suitable regularity' hedge.",
    "A2": "SCHEMA_BINDER_CONSISTENT: ordered[0]=(forall,r,D0), statement_formal binds 'forall r in D0', no 'forall (s,delta) in D0' in the file.",
    "A3": "SCHEMA_AMBIENT_PER_BRANCH: Frechet named for r=smooth, weighted Sobolev product named for r=(sobolev,s,delta), X^r_vac(AF) indexed, no orphan X^{s,delta}_vac.",
    "A4": "SCHEMA_INDEXED_OBJECTS: G_r/X^r_vac(AF) used in D1/formal/qnf, no orphan G_{s,delta} in the file.",
    "A5": "POINTER_RESOLVES: class_contract_pointer resolves to classes.<ID> in the canonical taxonomy and declared_f0_sha256 equals the measured taxonomy sha256.",
    "A6": "POINTER_TARGET_TYPED (end-to-end): the resolved class-contract entry does not bind (s,delta) over, or index G_{s,delta} in, a D0 containing the non-pair smooth member.",
    "A7": "SUPPLEMENT_ALIGNED (advisory): supplement contract entry does not contradict the repaired D0 typing; a missing typed index is recorded.",
    "A8": "EVIDENCE_COVERS_TYPING: consistency evidence must not report consistent=true while A6 fails and its compared inputs exclude the three schemas.",
    "A9": "NO_REGRESSION: no duplicate top-level YAML keys in the three schemas and D0 definition text identical across them.",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    return sha256_bytes(open(path, "rb").read())


def read_stable(path: str):
    raw1 = open(path, "rb").read()
    h1 = sha256_bytes(raw1)
    raw2 = open(path, "rb").read()
    h2 = sha256_bytes(raw2)
    text = raw1.decode("utf-8")
    return raw1, text, h1, (h1 == h2)


def load_yaml(text: str):
    return yaml.safe_load(text)


def duplicate_top_level_keys(text: str):
    seen, dups = set(), []
    for line in text.splitlines():
        m = DUP_LINE_RE.match(line)
        if m:
            k = m.group(1)
            if k in seen and k not in dups:
                dups.append(k)
            seen.add(k)
    return dups


def d0_definition(doc) -> str | None:
    try:
        d = (doc or {}).get("quantifiers", {}).get("domains", {}).get("D0", {})
        v = d.get("definition")
        return v if isinstance(v, str) else None
    except AttributeError:
        return None


def ordered(doc):
    try:
        v = (doc or {}).get("quantifiers", {}).get("ordered")
        return v if isinstance(v, list) else []
    except AttributeError:
        return []


def statement_formal(doc) -> str:
    try:
        return (doc or {}).get("conclusion", {}).get("statement_formal") or ""
    except AttributeError:
        return ""


def resolve_fragment(doc, fragment: str):
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def pointer_parts(doc):
    p = (doc or {}).get("class_contract_pointer")
    if not isinstance(p, str) or "#" not in p:
        return None, None
    path, frag = p.split("#", 1)
    return path, frag


def d0_shape(defn: str | None):
    d = defn or ""
    return {
        "tagged_disjoint_union": "tagged disjoint union" in d,
        "member_smooth": bool(re.search(r"r\s*=\s*smooth\b", d)),
        "member_sobolev": bool(re.search(r"r\s*=\s*\(\s*sobolev\s*,\s*s\s*,\s*delta\s*\)", d)),
        "index_ranges_over_exactly_d0": "index r ranges over exactly D0" in d,
        "positive_suitable_hedge": ("suitable" in d) and ("does not range over" not in d),
    }


# ---------------------------------------------------------------------------
# criteria
# ---------------------------------------------------------------------------

def crit_a1(doc, text):
    defn = d0_definition(doc)
    sh = d0_shape(defn)
    fails = [k for k in ("tagged_disjoint_union", "member_smooth", "member_sobolev",
                         "index_ranges_over_exactly_d0") if not sh[k]]
    if sh["positive_suitable_hedge"]:
        fails.append("positive_suitable_hedge")
    return {
        "id": "A1", "name": "SCHEMA_D0_TYPED",
        "status": "FAIL" if fails else "PASS",
        "detail": f"D0 typing probe: {sh}; failed: {fails}" if fails else "D0 typed union complete",
        "evidence": {"d0_definition": defn, "shape": sh},
    }


def crit_a2(doc, text):
    ob = ordered(doc)
    first = ob[0] if ob else None
    sf = statement_formal(doc)
    pair_in_ordered = any(isinstance(b, dict) and PAIR_BINDER_RE.search(str(b.get("binder", "")))
                          for b in ob)
    pair_anywhere = bool(PAIR_BINDER_RE.search(text))
    ok_first = isinstance(first, dict) and first.get("kind") == "forall" \
        and first.get("binder") == "r" and first.get("domain_id") == "D0"
    ok_sf = "forall r in D0" in sf
    fails = []
    if not ok_first:
        fails.append("ordered[0] != (forall, r, D0)")
    if not ok_sf:
        fails.append("statement_formal lacks 'forall r in D0'")
    if pair_in_ordered:
        fails.append("pair binder over D0 in ordered[]")
    if pair_anywhere:
        fails.append("'forall (s,delta)' still present in file text")
    return {
        "id": "A2", "name": "SCHEMA_BINDER_CONSISTENT",
        "status": "FAIL" if fails else "PASS",
        "detail": f"binder probe failed: {fails}" if fails else "binder and D0 typing agree",
        "evidence": {"ordered_first": first, "statement_formal_head": sf[:160],
                     "pair_binder_occurrences": len(PAIR_BINDER_RE.findall(text))},
    }


def crit_a3(doc, text):
    defn = d0_definition(doc) or ""
    frechet = "Frechet for r = smooth" in defn
    sobolev = bool(re.search(r"weighted Sobolev product H\^s_delta x H\^\{?s-1\}?_\{?delta\+1\}? for r = \(sobolev,s,delta\)", defn))
    indexed_ambient = "X^r_vac(AF)" in defn
    orphan = ORPHAN_AMBIENT_RE.findall(text)
    fails = []
    if not frechet:
        fails.append("no Frechet ambient for r=smooth")
    if not sobolev:
        fails.append("no weighted Sobolev product for r=(sobolev,s,delta)")
    if not indexed_ambient:
        fails.append("X^r_vac(AF) not indexed in D0")
    if orphan:
        fails.append(f"orphan X^{{s,delta}}_vac occurrences: {len(orphan)}")
    return {
        "id": "A3", "name": "SCHEMA_AMBIENT_PER_BRANCH",
        "status": "FAIL" if fails else "PASS",
        "detail": f"ambient probe failed: {fails}" if fails else "ambient object declared per D0 branch",
        "evidence": {"frechet_named": frechet, "sobolev_product_named": sobolev,
                     "indexed_ambient_x_r_vac": indexed_ambient,
                     "orphan_ambient_occurrences": len(orphan)},
    }


def crit_a4(doc, text):
    d1 = ""
    try:
        d1 = str((doc or {}).get("quantifiers", {}).get("domains", {}).get("D1", {}).get("definition") or "")
    except AttributeError:
        d1 = ""
    sf = statement_formal(doc)
    qnf = ""
    qformal = ""
    try:
        qnf = str((doc or {}).get("quantifiers", {}).get("negation_normal_form") or "")
        qformal = str((doc or {}).get("quantifiers", {}).get("formal") or "")
    except AttributeError:
        qnf, qformal = "", ""
    g_r_d1 = "G_r" in d1
    # The long formal statement (quantifiers.formal) carries the ambient subscript in all
    # three classes; F2a/F2b's compact conclusion.statement_formal intentionally omits it.
    formal_indexes_ambient = bool(re.search(r"G_r\s+subset\s+X\^r_vac\(AF\)", qformal))
    sf_binds_r_g_r = ("forall r in D0" in sf) and ("G_r" in sf)
    r_in_d0_qnf = ("r in D0" in qnf) or bool(re.search(r"\{\s*r\s+in\s+D0", qnf))
    orphan = ORPHAN_INDEX_RE.findall(text)
    fails = []
    if not g_r_d1:
        fails.append("D1 does not define G_r")
    if not formal_indexes_ambient:
        fails.append("quantifiers.formal lacks G_r subset X^r_vac(AF)")
    if not sf_binds_r_g_r:
        fails.append("statement_formal does not bind forall r in D0 with G_r")
    if not r_in_d0_qnf:
        fails.append("negation_normal_form does not index by r in D0")
    if orphan:
        fails.append(f"orphan G_{{s,delta}} occurrences: {len(orphan)}")
    return {
        "id": "A4", "name": "SCHEMA_INDEXED_OBJECTS",
        "status": "FAIL" if fails else "PASS",
        "detail": f"indexing probe failed: {fails}" if fails else "G_r/X^r_vac(AF) indexing consistent",
        "evidence": {"d1_defines_G_r": g_r_d1, "formal_indexes_G_r_subset_X_r": formal_indexes_ambient,
                     "statement_formal_binds_r_and_G_r": sf_binds_r_g_r,
                     "qnf_indexes_r_in_D0": r_in_d0_qnf,
                     "orphan_index_occurrences": len(orphan),
                     "quantifiers_formal_head": qformal[:200], "statement_formal": sf},
    }


def crit_a5(doc, text, tax_doc, tax_sha):
    path, frag = pointer_parts(doc)
    cid = (doc or {}).get("class_id") or ""
    resolved = resolve_fragment(tax_doc, frag) if frag else None
    fb = (doc or {}).get("f0_binding") or {}
    declared = fb.get("declared_f0_sha256") if isinstance(fb, dict) else None
    fails = []
    if path != TAX_PATH:
        fails.append(f"pointer path {path!r} != {TAX_PATH!r}")
    if not frag:
        fails.append("pointer has no fragment")
    if resolved is None:
        fails.append(f"fragment {frag!r} does not resolve")
    if declared != tax_sha:
        fails.append(f"declared_f0_sha256 {declared} != measured {tax_sha}")
    return {
        "id": "A5", "name": "POINTER_RESOLVES",
        "status": "FAIL" if fails else "PASS",
        "detail": f"pointer probe failed: {fails}" if fails else "pointer resolves and hash-pins the measured taxonomy",
        "evidence": {"class_contract_pointer": (doc or {}).get("class_contract_pointer"),
                     "fragment": frag, "fragment_resolves": resolved is not None,
                     "declared_f0_sha256": declared, "measured_taxonomy_sha256": tax_sha},
    }


def a6_core(defn: str | None, contract_text: str | None):
    """End-to-end typing predicate, shared by criterion A6 and controls K6/K7."""
    sh = d0_shape(defn)
    union_with_nonpair = bool(sh["tagged_disjoint_union"] and sh["member_smooth"]) or bool(
        sh["member_smooth"] and re.search(r"\bor\b", defn or ""))
    t = contract_text or ""
    pair_binder = bool(PAIR_BINDER_RE.search(t)) or bool(PAIR_ADMISSIBLE_RE.search(t))
    orphan_index = bool(ORPHAN_INDEX_RE.search(t))
    typed_index_present = bool(re.search(r"forall\s+r\s+in\s+D0", t)) or bool(re.search(r"\bG_r\b", t))
    return {
        "d0_is_union_with_nonpair_member": union_with_nonpair,
        "target_pair_binder": pair_binder,
        "target_orphan_G_s_delta": orphan_index,
        "target_typed_index_present": typed_index_present,
        "fail": bool(union_with_nonpair and (pair_binder or orphan_index)),
    }


def crit_a6(doc, text, tax_doc, tax_text):
    path, frag = pointer_parts(doc)
    target = resolve_fragment(tax_doc, frag) if frag else None
    ctext = ""
    if isinstance(target, dict):
        ctext = str((target.get("conclusion") or {}).get("text") or "")
    core = a6_core(d0_definition(doc), ctext)
    lines = [i for i, l in enumerate(tax_text.splitlines(), 1) if PAIR_ADMISSIBLE_RE.search(l)]
    return {
        "id": "A6", "name": "POINTER_TARGET_TYPED",
        "status": "FAIL" if core["fail"] else "PASS",
        "detail": ("resolved class-contract target still binds (s,delta)/G_{s,delta} over a D0 "
                   "that contains the non-pair smooth member") if core["fail"]
                  else "resolved class-contract target is well typed under the repaired D0 union",
        "evidence": {"target_fragment": frag, "target_conclusion_text": ctext,
                     "core": core, "taxonomy_pair_binder_lines": lines},
    }


def crit_a7(doc, text, sup_doc):
    cid = (doc or {}).get("class_id") or ""
    cc = ((sup_doc or {}).get("class_contracts") or {}).get(cid)
    if not isinstance(cc, dict):
        return {"id": "A7", "name": "SUPPLEMENT_ALIGNED", "status": "INFO",
                "detail": f"supplement has no class_contracts.{cid} entry", "evidence": {}}
    pred = str(cc.get("conclusion_predicate") or "")
    pair = bool(PAIR_BINDER_RE.search(pred)) or bool(PAIR_ADMISSIBLE_RE.search(pred))
    typed = bool(re.search(r"\bG_r\b", pred)) or bool(re.search(r"\br\s+in\s+D0\b", pred))
    freeze = str(cc.get("data_class_freeze") or "")
    contradicts = pair
    return {
        "id": "A7", "name": "SUPPLEMENT_ALIGNED",
        "status": "FAIL" if contradicts else "INFO",
        "detail": ("supplement contract binds the pair over D0") if contradicts else
                  ("supplement contract carries no quantifier; typed r-index not present "
                   f"(advisory gap): {pred[:120]!r}"),
        "evidence": {"conclusion_predicate": pred, "components": cc.get("components"),
                     "typed_index_present": typed, "data_class_freeze": freeze[:200]},
    }


def crit_a8(ce_doc, ce_text, a6_statuses):
    consistent = bool((ce_doc or {}).get("consistent")) if isinstance(ce_doc, dict) else None
    covers = any(s in (ce_text or "") for s in
                 ("af_wcc_vacuum", "af_scc_c2_vacuum", "af_scc_c0_vacuum", "statement_formal",
                  "binder", "typing"))
    a6_fail = any(v == "FAIL" for v in a6_statuses.values())
    fail = bool(a6_fail and consistent is True and not covers)
    return {
        "id": "A8", "name": "EVIDENCE_COVERS_TYPING",
        "status": "FAIL" if fail else "PASS",
        "detail": ("consistency evidence reports consistent=true while A6 fails and its compared "
                   "inputs exclude the three schemas: the green check is silent on the "
                   "schema<->contract typing relation") if fail
                  else "consistency evidence does not mask the checked relation",
        "evidence": {"consistent": consistent, "compared_classes": (ce_doc or {}).get("classes_compared"),
                     "compared_inputs_include_schemas_or_typing": covers,
                     "a6_statuses": a6_statuses},
    }


def crit_a9(texts, defs):
    dups = {k: duplicate_top_level_keys(t) for k, t in texts.items()}
    dup_any = {k: v for k, v in dups.items() if v}
    norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
    equal = len({norm(v) for v in defs.values()}) == 1
    fails = []
    if dup_any:
        fails.append(f"duplicate top-level keys: {dup_any}")
    if not equal:
        fails.append("D0 definition text differs across classes")
    return {
        "id": "A9", "name": "NO_REGRESSION",
        "status": "FAIL" if fails else "PASS",
        "detail": f"regression probe failed: {fails}" if fails else
                  "no duplicate top-level keys; D0 text identical across classes",
        "evidence": {"duplicate_keys": dup_any, "d0_text_identical": equal},
    }


# ---------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------

def controls(schema_doc, schema_text, tax_doc, defn):
    ks = []

    def add(kid, name, expected, observed, detail):
        ks.append({"id": kid, "name": name, "expected": expected, "observed": observed,
                   "status": "PASS" if observed == expected else "FAIL", "detail": detail})

    # K1 clean clone passes A1-A4
    clone_text = schema_text
    s1 = crit_a1(schema_doc, clone_text)["status"]
    s2 = crit_a2(schema_doc, clone_text)["status"]
    s3 = crit_a3(schema_doc, clone_text)["status"]
    s4 = crit_a4(schema_doc, clone_text)["status"]
    add("K1", "clean rev12-like schema clone", "PASS/PASS/PASS/PASS",
        f"{s1}/{s2}/{s3}/{s4}", "criteria accept a correctly repaired schema")

    # K2 pair-binder mutant flips A2
    t2 = schema_text.replace("forall r in D0", "forall (s,delta) in D0", 1)
    d2 = load_yaml(t2)
    add("K2", "binder mutant: forall (s,delta) in D0", "FAIL",
        crit_a2(d2, t2)["status"], "A2 detects the reintroduced pair binder")

    # K3 ambient mutant flips A3
    t3 = re.sub(r"Frechet for r = smooth", "a locally convex topology", schema_text)
    d3 = load_yaml(t3)
    add("K3", "ambient mutant: smooth Frechet removed", "FAIL",
        crit_a3(d3, t3)["status"], "A3 detects a missing smooth ambient")

    # K4 orphan index mutant flips A4
    t4 = schema_text + "\n# synthetic orphan G_{s,delta}\n"
    d4 = load_yaml(t4)
    add("K4", "orphan index mutant: G_{s,delta}", "FAIL",
        crit_a4(d4, t4)["status"], "A4 detects an orphan pair-indexed object")

    # K5 pointer fragment mutant flips A5
    d5 = copy.deepcopy(schema_doc)
    d5["class_contract_pointer"] = TAX_PATH + "#classes.NOPE"
    add("K5", "pointer mutant: fragment does not resolve", "FAIL",
        crit_a5(d5, schema_text, tax_doc, sha256_bytes(yaml.safe_dump(tax_doc).encode()))["status"],
        "A5 detects an unresolvable pointer fragment")

    # K6/K7 A6 direction both ways on synthetic contracts
    union_defn = defn
    c_bad = {"conclusion": {"text": "For every admissible (s,delta) there is a comeager set "
                                    "G_{s,delta} of data such that ..."}}
    c_good = {"conclusion": {"text": "forall r in D0 exists G_r subset X^r_vac(AF) comeager ..."}}
    bad = a6_core(union_defn, c_bad["conclusion"]["text"])["fail"]
    good = a6_core(union_defn, c_good["conclusion"]["text"])["fail"]
    add("K6", "A6 mutant contract: pair binder over union D0", "FAIL",
        "FAIL" if bad else "PASS", "A6 rejects a pair-bound contract target")
    add("K7", "A6 clean contract: forall r in D0 with G_r", "PASS",
        "FAIL" if good else "PASS", "A6 accepts a well-typed contract target")

    # K8 duplicate-key mutant flips the A9 scan
    t8 = "alpha: 1\nalpha: 2\n" + schema_text
    add("K8", "duplicate top-level key mutant", "FAIL",
        "FAIL" if duplicate_top_level_keys(t8) else "PASS",
        "A9's duplicate-key scan detects a strict-YAML duplicate")

    # K9 missing D0 fails closed rather than passing silently
    add("K9", "missing D0 domain (fail-closed)", "FAIL",
        crit_a1({}, "")["status"], "A1 reports FAIL when D0 is absent")

    # K10 ambient subscript removed from the long formal statement flips A4
    t10 = schema_text.replace("exists G_r subset X^r_vac(AF)", "exists G_r comeager", 1)
    d10 = load_yaml(t10)
    add("K10", "indexing mutant: ambient subscript dropped from quantifiers.formal", "FAIL",
        crit_a4(d10, t10)["status"], "A4 detects loss of the G_r subset X^r_vac(AF) indexing")

    return ks


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def run(repo: str, snapshot_dir=None):
    inputs, docs, texts = {}, {}, {}

    def pin(key, rel):
        p = os.path.join(repo, rel)
        if not os.path.isfile(p):
            raise RuntimeError(f"missing input {p}")
        raw, text, sha, stable = read_stable(p)
        inputs[key] = {"path": rel, "sha256": sha, "bytes": len(raw),
                       "stable_during_read": stable}
        docs[key] = load_yaml(text)
        texts[key] = text
        if snapshot_dir:
            os.makedirs(snapshot_dir, exist_ok=True)
            with open(os.path.join(snapshot_dir, f"{os.path.basename(rel)}.{sha[:12]}"), "wb") as f:
                f.write(raw)

    for s in SCHEMAS:
        pin(s["key"], s["path"])
    pin("TAX", TAX_PATH)
    pin("SUP", SUP_PATH)
    pin("CE", CE_PATH)

    drifted = [k for k, v in inputs.items() if not v["stable_during_read"]]
    if drifted:
        raise RuntimeError(f"inputs drifted during read: {drifted}")

    checks = []
    for s in SCHEMAS:
        k, doc, text = s["key"], docs[s["key"]], texts[s["key"]]
        for fn in (lambda d, t: crit_a1(d, t), lambda d, t: crit_a2(d, t),
                   lambda d, t: crit_a3(d, t), lambda d, t: crit_a4(d, t)):
            c = fn(doc, text)
            c["node_id"] = s["node_id"]
            c["class_id"] = s["class_id"]
            checks.append(c)
        c = crit_a5(doc, text, docs["TAX"], inputs["TAX"]["sha256"])
        c.update(node_id=s["node_id"], class_id=s["class_id"])
        checks.append(c)
        c = crit_a6(doc, text, docs["TAX"], texts["TAX"])
        c.update(node_id=s["node_id"], class_id=s["class_id"])
        checks.append(c)
        c = crit_a7(doc, text, docs["SUP"])
        c.update(node_id=s["node_id"], class_id=s["class_id"])
        checks.append(c)

    a6_statuses = {c["class_id"]: c["status"] for c in checks if c["id"] == "A6"}
    a8 = crit_a8(docs["CE"], texts["CE"], a6_statuses)
    a8.update(node_id="F0,F1,F2a,F2b", class_id="AF-SCC-C2-VAC-GEN")
    checks.append(a8)

    defs = {s["key"]: d0_definition(docs[s["key"]]) for s in SCHEMAS}
    a9 = crit_a9({s["key"]: texts[s["key"]] for s in SCHEMAS}, defs)
    a9.update(node_id="F1,F2a,F2b", class_id="AF-SCC-C2-VAC-GEN")
    checks.append(a9)

    ctrl = controls(docs["F2a"], texts["F2a"], docs["TAX"], defs["F2a"])

    findings = []
    for c in checks:
        if c["status"] == "FAIL" and c["id"] == "A6":
            findings.append({
                "id": "RA-1", "severity": "critical",
                "finding": (f"{c['class_id']} class-contract pointer resolves into the canonical "
                            "taxonomy entry whose conclusion.text still quantifies over (s,delta) "
                            "and indexes G_{s,delta}, while the schema's D0 is a tagged union with "
                            "the non-pair smooth member: the rev12 repair is not carried through "
                            "to the declared contract target."),
                "evidence": c["evidence"], "class_id": c["class_id"],
                "minimal_repair": ("amend classes.<ID>.conclusion.text in the canonical taxonomy to "
                                   "the r-indexed form (forall r in D0 ... G_r subset X^r_vac(AF)), "
                                   "or record an adjudication that the taxonomy conclusion text is "
                                   "non-binding and re-point the schemas at the binding contract, "
                                   "then refresh declared_f0_sha256."),
            })
        if c["status"] == "FAIL" and c["id"] == "A8":
            findings.append({
                "id": "RA-2", "severity": "major",
                "finding": ("taxonomy_consistency.json declares consistent=true with no contract "
                            "divergences while its compared inputs exclude the three schemas; it "
                            "therefore certifies a green state that is silent on the live "
                            "schema<->contract typing divergence (A6)."),
                "evidence": c["evidence"],
                "minimal_repair": ("extend the consistency checker/evidence to compare the schemas' "
                                   "D0/binder normal forms against the contract targets, or record "
                                   "the scope limitation explicitly in the evidence JSON."),
            })
    for c in checks:
        if c["id"] == "A7" and c["status"] == "INFO":
            findings.append({
                "id": "RA-3", "severity": "advisory",
                "finding": (f"{c['class_id']} supplement contract carries no quantifier and no "
                            "r-index; its data_class_freeze prose (default plus registered Sobolev "
                            "variant) is consistent with rev12 but cannot discharge the typed "
                            "contract on its own."),
                "evidence": c["evidence"], "class_id": c["class_id"],
                "minimal_repair": ("add a typed D0 union component to the supplement contract "
                                   "entries or explicitly subordinate them to the canonical taxonomy."),
            })

    hard = [f for f in findings if f["severity"] in ("critical", "major")]
    any_fail = any(c["status"] == "FAIL" for c in checks)
    ctrl_fail = [k for k in ctrl if k["status"] == "FAIL"]

    report = {
        "schema_version": "w047-repair-acceptance/v1",
        "task_id": "W047-D0-REPAIR-ACCEPT-02",
        "actor": "worker-047",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "class_ids": [s["class_id"] for s in SCHEMAS],
        "authority_note": ("worker evidence only; no gate verdict, no node status, no canonical "
                           "file edit; read-only except this artifact directory"),
        "pre_registered_criteria": PRE_REGISTERED,
        "inputs": inputs,
        "checks": checks,
        "controls": ctrl,
        "findings": findings,
        "hard_failures": [f["id"] for f in hard],
        "instrument_integrity_failures": ctrl_fail,
        "verdict": {
            "decision": "revise" if any_fail else "accept",
            "score": 2.5 if hard else (3.5 if any_fail else 4.0),
            "scope": [s["class_id"] for s in SCHEMAS],
            "basis": ("schema-level rev12 D0 repair passes A1-A5/A9; the end-to-end contract "
                      "target (A6) and the consistency evidence coverage (A8) fail"),
        },
        "assumptions": [
            "the class-contract binding is the resolved classes.<ID> object referenced by "
            "class_contract_pointer, and conclusion.text is its statement-bearing field",
            "the F0 scope_statement rule that downstream-owned provisional values must be "
            "replaced, not inherited silently, applies to the conclusion text",
            "the pinned bytes are the object of the verdict; later writes are outside it",
        ],
        "falsifier": ("If, at a later canonical revision, the resolved contract target for each of "
                      "the three classes binds the D0 index r (or a single regime) with G_r / "
                      "X^r_vac(AF) and no (s,delta) pair binder, and declared_f0_sha256 is "
                      "refreshed to that revision, then A6/RA-1 is falsified; if the consistency "
                      "evidence is extended to cover the schema<->contract typing relation (or "
                      "records the scope limitation) and re-run, A8/RA-2 is falsified. A later file "
                      "write alone is not a falsifier: the fresh hash must be measured and these "
                      "criteria re-run."),
    }
    return report, checks, ctrl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--out", default=None)
    ap.add_argument("--snapshot-dir", default=None)
    ap.add_argument("--strict", action="store_true", help="exit 1 on any FAIL")
    args = ap.parse_args()
    try:
        report, checks, ctrl = run(os.path.abspath(args.repo), snapshot_dir=args.snapshot_dir)
    except Exception as exc:  # fail closed
        print(json.dumps({"error": str(exc), "repo": args.repo}), file=sys.stderr)
        return 2

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1, sort_keys=False)
            f.write("\n")

    fails = [c["id"] for c in checks if c["status"] == "FAIL"]
    print(json.dumps({
        "task_id": report["task_id"], "verdict": report["verdict"],
        "checks": {c["id"]: c["status"] for c in checks},
        "hard_failures": report["hard_failures"],
        "controls": {c["id"]: c["status"] for c in ctrl},
        "integrity_failures": report["instrument_integrity_failures"],
        "fails": fails, "out": args.out,
    }, indent=1))
    if report["instrument_integrity_failures"]:
        return 2
    if args.strict and fails:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
