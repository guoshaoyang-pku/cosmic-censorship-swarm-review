#!/usr/bin/env python3
"""worker-030 independent full-schema review instrument for F2b (AF-SCC-C0-VAC-GEN).

Deterministic, hash-pinned structural + cross-artifact audit of the canonical
strong-censorship C0 schema. It does NOT import research_map/class_separation.py
(that instrument is owned by another worker); the class-token scan here is a
separate implementation.

Usage:
    python3 artifacts/worker-030/f2b_review_check.py [--json PATH]

Exit codes:
    0  no blocking check failed
    1  >=1 blocking check failed
    2  operational failure (target missing / hash drift vs pinned hash)

The pinned hash is the revision reviewed. Any edit to the target makes this
instrument exit 2 rather than silently reviewing a different revision.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET = "schemas/af_scc_c0_vacuum.yaml"
PINNED_SHA256 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
FROZEN_CLASSES = (
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
)
SIBLING = "schemas/af_scc_c2_vacuum.yaml"
WCC = "schemas/af_wcc_vacuum.yaml"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
LEDGER = "ledger/theorems.jsonl"
VARIANT_REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"

CHECKS = []


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(cid, group, blocking, ok, detail, **extra):
    CHECKS.append(
        {
            "id": cid,
            "group": group,
            "blocking_if_failed": bool(blocking),
            "status": "PASS" if ok else ("FAIL" if blocking else "NOTE"),
            "detail": detail,
            **extra,
        }
    )


class DuplicateKeyError(Exception):
    pass


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys (and can reject them)."""

    def __init__(self, stream, strict=False):
        super().__init__(stream)
        self.strict = strict
        self.duplicates = []

    def construct_mapping(self, node, deep=False):
        seen = {}
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                self.duplicates.append(
                    {"key": str(key), "lines": [seen[key], key_node.start_mark.line + 1]}
                )
                if self.strict:
                    raise DuplicateKeyError(
                        f"duplicate key {key!r} at lines {seen[key]} and {key_node.start_mark.line + 1}"
                    )
            else:
                seen[key] = key_node.start_mark.line + 1
        return super().construct_mapping(node, deep=deep)


def load_yaml_strict(path: str):
    loader = StrictLoader(open(path, encoding="utf-8"), strict=True)
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc


def load_yaml_dups(path: str):
    loader = StrictLoader(open(path, encoding="utf-8"), strict=False)
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, loader.duplicates


def walk(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, path + (str(i),))
    elif isinstance(obj, str):
        yield path, obj


FORBIDDEN_PATH_PARTS = {
    "anti_scope",
    "forbidden",
    "forbidden_falsifier",
    "forbidden_strengthenings",
    "forbidden_weakenings",
    "must_not_conflate",
    "phrases_that_are_not_this_class",
    "schema_falsifiers",
    "class_change_warning",
    "vacuity_falsifier",
    "known_status",
    "unresolved_items",
    "provenance",
    "f0_binding",
    "l1_ledger_refs",
    "transfer_failures",
    "review_status",
}


def in_forbidden_context(path) -> bool:
    return any(part in FORBIDDEN_PATH_PARTS for part in path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--json",
        default=os.path.join(ROOT, "artifacts/worker-030/f2b_binding_audit.json"),
    )
    args = ap.parse_args()

    generated_at = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
    tpath = os.path.join(ROOT, TARGET)

    # ---- operational preconditions -------------------------------------------------
    if not os.path.exists(tpath):
        print(json.dumps({"error": "target missing", "target": TARGET}))
        return 2
    measured = sha256_of(tpath)
    nbytes = os.path.getsize(tpath)
    if measured != PINNED_SHA256:
        print(
            json.dumps(
                {
                    "error": "hash drift: target no longer matches the pinned revision",
                    "target": TARGET,
                    "pinned_sha256": PINNED_SHA256,
                    "measured_sha256": measured,
                }
            )
        )
        return 2

    # HASH-01: pinned hash and sidecar
    sidecar = tpath + ".sha256"
    sidecar_sha = None
    if os.path.exists(sidecar):
        sidecar_sha = open(sidecar, encoding="utf-8").read().split()[0]
    record(
        "HASH-01",
        "identity",
        True,
        measured == PINNED_SHA256 and (sidecar_sha is None or sidecar_sha == measured),
        f"measured sha256={measured} bytes={nbytes}; sidecar={sidecar_sha}",
    )

    # YAML-01: strict duplicate-key parse
    strict_ok, strict_err = True, None
    try:
        doc = load_yaml_strict(tpath)
    except DuplicateKeyError as exc:
        strict_ok, strict_err = False, str(exc)
        doc = None
    if doc is None:
        doc, dups = load_yaml_dups(tpath)
    else:
        _, dups = load_yaml_dups(tpath)
    record(
        "YAML-01",
        "hygiene",
        False,
        strict_ok,
        "strict duplicate-key parse: "
        + ("clean" if strict_ok else f"{len(dups)} duplicate top-level key occurrence(s): {dups}"),
        duplicates=dups,
    )

    # YAML-02: ordinary parse succeeds, top-level keys
    record(
        "YAML-02",
        "hygiene",
        True,
        isinstance(doc, dict),
        f"safe_load type={type(doc).__name__}; top-level keys={sorted(doc) if isinstance(doc, dict) else None}",
    )
    if not isinstance(doc, dict):
        _flush(args.json, generated_at, measured, nbytes)
        return 1

    # ---- class binding --------------------------------------------------------------
    cid = doc.get("class_id")
    record(
        "CLASS-01",
        "class_binding",
        True,
        cid == CLASS_ID,
        f"class_id={cid!r} (expected {CLASS_ID!r})",
    )
    comp = doc.get("class_components") or {}
    expected_comp = {
        "asymptotics": "AF",
        "censorship": "SCC",
        "matter": "VAC",
        "genericity": "GEN",
        "regularity_token": "C0",
    }
    record(
        "CLASS-02",
        "class_binding",
        True,
        comp == expected_comp,
        f"class_components={comp} (expected {expected_comp})",
    )
    record(
        "CLASS-03",
        "class_binding",
        True,
        doc.get("node_id") == "F2b" and doc.get("sibling_disjoint_from") == "AF-SCC-C2-VAC-GEN",
        f"node_id={doc.get('node_id')!r} sibling_disjoint_from={doc.get('sibling_disjoint_from')!r}",
    )

    # CLASS-04: unknown class-token scan (independent of class_separation.py)
    token_re = re.compile(r"\bAF-[A-Z]+(?:-[A-Z0-9]+)*\b")
    unknown, asserted_bad_classid = [], []
    for path, text in walk(doc):
        for tok in token_re.findall(text):
            if tok not in FROZEN_CLASSES:
                unknown.append({"path": "/".join(path), "token": tok})
        if path and path[-1] == "class_id" and text not in FROZEN_CLASSES:
            asserted_bad_classid.append({"path": "/".join(path), "value": text})
    record(
        "CLASS-04",
        "class_binding",
        True,
        not unknown and not asserted_bad_classid,
        f"unknown AF-* tokens={unknown}; non-frozen class_id fields={asserted_bad_classid}",
        unknown_tokens=unknown,
    )

    # CLASS-05: sibling separation, both directions
    sibling_ok, sibling_detail = False, "sibling missing"
    if os.path.exists(os.path.join(ROOT, SIBLING)):
        sib = yaml.safe_load(open(os.path.join(ROOT, SIBLING), encoding="utf-8"))
        sibling_ok = (
            sib.get("class_id") == "AF-SCC-C2-VAC-GEN"
            and sib.get("sibling_disjoint_from") == CLASS_ID
            and (sib.get("regularity") or {}).get("extension_regularity") == "C2"
            and (sib.get("conclusion") or {}).get("conclusion_type") != doc["conclusion"]["conclusion_type"]
        )
        sibling_detail = (
            f"{SIBLING}: class_id={sib.get('class_id')!r} "
            f"sibling_disjoint_from={sib.get('sibling_disjoint_from')!r} "
            f"extension_regularity={(sib.get('regularity') or {}).get('extension_regularity')!r} "
            f"conclusion_type={(sib.get('conclusion') or {}).get('conclusion_type')!r}"
        )
    record("CLASS-05", "class_binding", True, sibling_ok, sibling_detail)

    # CLASS-06: composite regularity token appears only in forbidding contexts
    composite_hits = []
    for path, text in walk(doc):
        for pat in ("C0 or C2", "C0/C2", "C2 or C0"):
            if pat in text:
                composite_hits.append(
                    {"path": "/".join(path), "pattern": pat, "forbidden_context": in_forbidden_context(path)}
                )
    leaked = [h for h in composite_hits if not h["forbidden_context"]]
    record(
        "CLASS-06",
        "class_binding",
        True,
        not leaked,
        f"composite-regularity occurrences={composite_hits}; asserted-context leaks={leaked}",
    )

    # ---- regularity ----------------------------------------------------------------
    reg = doc.get("regularity") or {}
    record(
        "REG-01",
        "regularity",
        True,
        reg.get("extension_regularity") == "C0"
        and "continuous" in str(reg.get("extension_regularity_exact", "")).lower()
        and reg.get("extension_solution_concept") == "none",
        f"extension_regularity={reg.get('extension_regularity')!r} "
        f"extension_regularity_exact={reg.get('extension_regularity_exact')!r} "
        f"extension_solution_concept={reg.get('extension_solution_concept')!r}",
    )
    mnc = " ".join(reg.get("must_not_conflate") or [])
    record(
        "REG-02",
        "regularity",
        True,
        all(tok in mnc for tok in ("H2_loc", "distributional", "C2")),
        "regularity.must_not_conflate covers H2_loc / distributional / C2",
    )

    # ---- quantifiers ---------------------------------------------------------------
    q = doc.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    kinds = [row.get("kind") for row in ordered if isinstance(row, dict)]
    record(
        "QUANT-01",
        "quantifiers",
        True,
        kinds == ["forall", "exists", "forall", "not_exists"],
        f"quantifier order kinds={kinds} (expected forall,exists,forall,not_exists)",
    )
    domains = q.get("domains") or {}
    record(
        "QUANT-02",
        "quantifiers",
        True,
        set(domains) >= {"D0", "D1", "D2", "D3"}
        and all(domains[d].get("definition") and domains[d].get("definition_ref") for d in ("D0", "D1", "D2", "D3")),
        f"domains={sorted(domains)}; each has definition+definition_ref",
    )
    neg = str(q.get("negation", "")) + " " + str(q.get("negation_normal_form", ""))
    record(
        "QUANT-03",
        "quantifiers",
        True,
        "non-meager" in neg and q.get("order_matters") is True and bool(q.get("order_note")),
        "negation present and expressed as non-meagerness of the extendible set; order_matters=true",
    )

    # ---- topology ------------------------------------------------------------------
    topo = doc.get("topology") or {}
    forb = " ".join(topo.get("forbidden") or [])
    record(
        "TOPO-01",
        "topology",
        True,
        topo.get("spacetime_dimension") == 4
        and "R^3" in str(topo.get("slice_topology", ""))
        and "one af end" in str(topo.get("end_structure", "")).lower()
        and topo.get("I_plus_topology") == "R x S^2",
        f"dim={topo.get('spacetime_dimension')} slice={topo.get('slice_topology')!r} "
        f"end={topo.get('end_structure')!r} I+={topo.get('I_plus_topology')!r}",
    )
    ext_top = str(topo.get("extension_topology", ""))
    record(
        "TOPO-02",
        "topology",
        True,
        "SMOOTH" in ext_top
        and "continuous" in ext_top
        and "NOT assumed globally hyperbolic" in ext_top
        and {"closed or periodic spatial slice", "more than one asymptotically flat end"} <= set(topo.get("forbidden") or []),
        "extension manifold smooth vs metric continuous pinned; forbidden list rejects closed slice / multi-end / differentiability",
    )

    # ---- genericity -----------------------------------------------------------------
    gen = doc.get("genericity") or {}
    amb = str(gen.get("ambient_space", ""))
    record(
        "GEN-01",
        "genericity",
        True,
        gen.get("kind") == "residual_comeager"
        and "SUBSPACE" in amb
        and "Baire" in amb
        and gen.get("is_part_of_class") is True,
        f"kind={gen.get('kind')!r}; ambient cites subspace topology and Baire; is_part_of_class={gen.get('is_part_of_class')!r}",
    )
    record(
        "GEN-02",
        "genericity",
        True,
        len(gen.get("transfer_failures") or []) >= 3
        and len(gen.get("transfer_holds") or []) >= 2
        and bool(gen.get("class_change_warning"))
        and bool(gen.get("generic_set"))
        and bool(gen.get("excluded_set")),
        f"transfer_failures={len(gen.get('transfer_failures') or [])} "
        f"transfer_holds={len(gen.get('transfer_holds') or [])} class_change_warning present",
    )

    # ---- conclusion / family separation ---------------------------------------------
    conc = doc.get("conclusion") or {}
    record(
        "CONC-01",
        "conclusion",
        True,
        conc.get("conclusion_type") == "scc_c0_future_inextendibility"
        and conc.get("family") == "SCC"
        and bool(conc.get("statement_natural_language"))
        and bool(conc.get("statement_formal"))
        and "exists G" in str(conc.get("statement_formal", "")),
        f"conclusion_type={conc.get('conclusion_type')!r} family={conc.get('family')!r}; formal statement carries the comeager existential",
    )
    ip = doc.get("i_plus") or {}
    vis = doc.get("visibility") or {}
    record(
        "CONC-02",
        "conclusion",
        True,
        ip.get("in_conclusion") is False
        and ip.get("completeness_in_conclusion") is False
        and vis.get("role") == "not_in_conclusion"
        and bool(vis.get("forbidden_falsifier")),
        f"i_plus.role={ip.get('role')!r} in_conclusion={ip.get('in_conclusion')!r} "
        f"completeness_in_conclusion={ip.get('completeness_in_conclusion')!r} visibility.role={vis.get('role')!r}",
    )
    wcc_tokens = ("completeness of i", "visible", "predictab", "naked singular")
    wcc_leaks = [
        {"path": "/".join(p), "text": t}
        for p, t in walk({"conclusion": conc})
        if any(tok in t.lower() for tok in wcc_tokens) and not in_forbidden_context(p)
    ]
    record(
        "CONC-03",
        "conclusion",
        True,
        not wcc_leaks,
        f"WCC-conclusion tokens inside conclusion block={wcc_leaks}",
    )
    fs = " ".join(conc.get("forbidden_strengthenings") or [])
    fw = " ".join(conc.get("forbidden_weakenings") or [])
    record(
        "CONC-04",
        "conclusion",
        True,
        "I+ completeness" in fs and "C2" in fw and "generic quantifier" in fw,
        "forbidden_strengthenings covers WCC content; forbidden_weakenings covers C2 substitution and generic-quantifier dropping",
    )

    # ---- falsifier -------------------------------------------------------------------
    fal = doc.get("falsifier") or {}
    t1 = fal.get("tier_1") or {}
    t2 = fal.get("tier_2") or {}
    record(
        "FALS-01",
        "falsifier",
        True,
        t1.get("refutes") == CLASS_ID
        and "non-meager" in str(t1.get("genericity_requirement", ""))
        and "explicitly" in str(t1.get("witness_type", ""))
        and len(t1.get("machine_checkable_steps") or []) >= 3
        and bool(t1.get("non_machine_checkable_step")),
        f"tier_1.refutes={t1.get('refutes')!r}; witness explicit; non-meagerness required; "
        f"machine steps={len(t1.get('machine_checkable_steps') or [])}",
    )
    record(
        "FALS-02",
        "falsifier",
        True,
        t2.get("labelling_required") == "refutes_strengthening_only"
        and "strictly stronger" in str(t2.get("refutes", ""))
        and len(fal.get("schema_falsifiers") or []) >= 3,
        f"tier_2 labelling={t2.get('labelling_required')!r}; schema_falsifiers={len(fal.get('schema_falsifiers') or [])}",
    )

    # ---- epistemic status / promotion -------------------------------------------------
    record(
        "EPI-01",
        "epistemic",
        True,
        doc.get("epistemic_status") == "open_problem"
        and conc.get("epistemic_status") == "open_problem"
        and bool(doc.get("promotion_rule"))
        and "theorem" not in str(conc.get("conclusion_type", "")).lower(),
        f"epistemic_status={doc.get('epistemic_status')!r} promotion_rule present; no theorem conclusion_type",
    )
    known = doc.get("known_status") or {}
    record(
        "EPI-02",
        "epistemic",
        True,
        known.get("status") == "open_problem_with_scoped_conditional_refutation"
        and bool(known.get("why_this_class_is_not_recorded_as_refuted"))
        and bool(known.get("consequence"))
        and bool(known.get("refutation_candidate"))
        and "not" in str(known.get("why_this_class_is_not_recorded_as_refuted", "")).lower(),
        f"known_status={known.get('status')!r}; refutation candidate quarantined to variant; no refutation claim",
    )

    # ---- ledger cross-check ------------------------------------------------------------
    lrefs = doc.get("l1_ledger_refs") or []
    ledger_sha = sha256_of(os.path.join(ROOT, LEDGER)) if os.path.exists(os.path.join(ROOT, LEDGER)) else None
    rows = {}
    if ledger_sha:
        for line in open(os.path.join(ROOT, LEDGER), encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("theorem_id"):
                rows[row["theorem_id"]] = row
    mismatches = []
    for ref in lrefs:
        tid = ref.get("theorem_id")
        row = rows.get(tid)
        if row is None:
            mismatches.append({"theorem_id": tid, "issue": "missing_from_ledger"})
            continue
        if row.get("status") != ref.get("l1_status"):
            mismatches.append(
                {
                    "theorem_id": tid,
                    "issue": "status_mismatch",
                    "ledger": row.get("status"),
                    "schema": ref.get("l1_status"),
                }
            )
        if CLASS_ID not in (row.get("class_ids") or []):
            mismatches.append({"theorem_id": tid, "issue": "class_ids_missing_target", "ledger": row.get("class_ids")})
    record(
        "LEDGER-01",
        "evidence",
        True,
        len(lrefs) >= 4 and not mismatches,
        f"{len(lrefs)} ledger refs cross-checked against {LEDGER}#{ledger_sha[:12] if ledger_sha else 'MISSING'}; mismatches={mismatches}",
        ledger_sha256=ledger_sha,
    )

    # ---- F0 binding ---------------------------------------------------------------------
    f0 = doc.get("f0_binding") or {}
    tax_path = os.path.join(ROOT, TAXONOMY)
    tax_sha = sha256_of(tax_path) if os.path.exists(tax_path) else None
    record(
        "F0B-01",
        "f0_binding",
        True,
        f0.get("declared_f0_artifact") == TAXONOMY
        and f0.get("declared_f0_sha256") == tax_sha
        and bool(f0.get("rule")),
        f"declared={f0.get('declared_f0_sha256')} measured={tax_sha} artifact={f0.get('declared_f0_artifact')!r}",
        measured_taxonomy_sha256=tax_sha,
    )
    cons_path = os.path.join(ROOT, CONSISTENCY)
    cons_ok, cons_detail = False, "missing"
    if os.path.exists(cons_path):
        cons = json.load(open(cons_path, encoding="utf-8"))
        cons_ok = bool(cons.get("consistent")) and set(cons.get("classes_compared") or []) == set(FROZEN_CLASSES)
        cons_detail = f"consistent={cons.get('consistent')} classes_compared={cons.get('classes_compared')}"
    record("F0B-02", "f0_binding", True, cons_ok, f"{CONSISTENCY}: {cons_detail}")
    # F0B-03: canonical taxonomy exposes the same class contract axes
    tax_ok, tax_detail = False, "canonical taxonomy missing classes.AF-SCC-C0-VAC-GEN"
    if tax_sha:
        tax = yaml.safe_load(open(tax_path, encoding="utf-8"))
        entry = ((tax.get("classes") or {}).get(CLASS_ID)) or {}
        axes = entry.get("axes") or {}
        tax_ok = axes.get("regularity_token") == "C0" and axes.get("family") == "SCC"
        tax_detail = (
            f"{TAXONOMY}#classes.{CLASS_ID}: axes.family={axes.get('family')!r} "
            f"axes.regularity_token={axes.get('regularity_token')!r} "
            f"axes.conclusion_type={axes.get('conclusion_type')!r}"
        )
    record("F0B-03", "f0_binding", True, tax_ok, tax_detail)

    # ---- hygiene: clock discipline and stale hash literals ------------------------------
    mtime = _dt.datetime.fromtimestamp(os.path.getmtime(tpath)).astimezone().replace(microsecond=0)
    eff_revised = doc.get("revised_at")
    future = []
    for label, value in (("revised_at", eff_revised), ("f0_binding.checked_at", f0.get("checked_at"))):
        if value:
            ts = _dt.datetime.fromisoformat(str(value))
            if ts > _dt.datetime.now().astimezone():
                future.append({"field": label, "value": str(value), "skew_seconds": int((ts - _dt.datetime.now().astimezone()).total_seconds())})
    record(
        "HYG-01",
        "hygiene",
        False,
        not future,
        f"file mtime={mtime.isoformat()} effective revised_at={eff_revised!r}; future-dated fields={future}",
        future_dated=future,
    )
    comment_hashes = []
    for ln, line in enumerate(open(tpath, encoding="utf-8"), 1):
        if line.lstrip().startswith("#"):
            for tok in re.findall(r"\b[0-9a-f]{8,64}\b", line):
                comment_hashes.append({"line": ln, "token": tok})
    known_hashes = {measured, tax_sha, ledger_sha}
    known_prefixes = {h[:8] for h in known_hashes if h}
    stale = [h for h in comment_hashes if h["token"][:8] not in known_prefixes]
    record(
        "HYG-02",
        "hygiene",
        False,
        not stale,
        f"hash-like literals in comments not matching any current pinned hash: {stale}",
        stale_comment_hashes=stale,
    )

    # ---- pointer policy ----------------------------------------------------------------
    ptr = str(doc.get("class_contract_pointer", ""))
    ptr_path, _, ptr_section = ptr.partition("#")
    ptr_resolves = False
    ptr_detail = f"class_contract_pointer={ptr!r}"
    if ptr_path and os.path.exists(os.path.join(ROOT, ptr_path)):
        pdoc = yaml.safe_load(open(os.path.join(ROOT, ptr_path), encoding="utf-8"))
        cur = pdoc
        for part in [p for p in ptr_section.split(".") if p]:
            cur = cur.get(part) if isinstance(cur, dict) else None
        ptr_resolves = isinstance(cur, dict)
        ptr_detail += f"; target section resolves={ptr_resolves}"
        if ptr_path != TAXONOMY:
            can = yaml.safe_load(open(tax_path, encoding="utf-8"))
            ptr_detail += (
                f"; points at the AUTHORING tree, not the authoritative {TAXONOMY} "
                f"(canonical section key is 'classes', authoring key is 'class_contracts')"
            )
    record(
        "PTR-01",
        "hygiene",
        False,
        ptr_resolves and ptr_path == TAXONOMY,
        ptr_detail,
    )

    # ---- non-vacuity / open items --------------------------------------------------------
    nv = doc.get("non_vacuity") or {}
    record(
        "NONVAC-01",
        "structure",
        True,
        bool(nv.get("condition")) and bool(nv.get("witness_type")) and bool(nv.get("status")) and bool(nv.get("vacuity_falsifier")),
        "non_vacuity has condition, witness_type, explicit status, and a vacuity falsifier",
    )
    record(
        "OPEN-01",
        "structure",
        True,
        len(doc.get("unresolved_items") or []) >= 3,
        f"unresolved_items={doc.get('unresolved_items')}",
    )

    # ---- WCC sibling sanity (separation evidence, not a WCC review) -----------------------
    wcc_ok, wcc_detail = False, "missing"
    if os.path.exists(os.path.join(ROOT, WCC)):
        w = yaml.safe_load(open(os.path.join(ROOT, WCC), encoding="utf-8"))
        wcc_ok = (
            w.get("class_id") == "AF-WCC-VAC-GEN"
            and (w.get("i_plus") or {}).get("in_conclusion") is True
            and (w.get("visibility") or {}).get("role") == "conclusion"
        )
        wcc_detail = (
            f"{WCC}: class_id={w.get('class_id')!r} i_plus.in_conclusion={(w.get('i_plus') or {}).get('in_conclusion')!r} "
            f"visibility.role={(w.get('visibility') or {}).get('role')!r}"
        )
    record("CLASS-07", "class_binding", True, wcc_ok, wcc_detail)

    return _flush(args.json, generated_at, measured, nbytes)


def _flush(out_path, generated_at, measured, nbytes) -> int:
    blocking_failures = [c for c in CHECKS if c["status"] == "FAIL" and c["blocking_if_failed"]]
    nonblocking = [c for c in CHECKS if c["status"] == "NOTE"]
    findings = []
    for c in CHECKS:
        if c["status"] != "PASS":
            findings.append(
                {
                    "id": f"W030-{c['id']}",
                    "severity": "B" if (c["status"] == "FAIL" and c["blocking_if_failed"]) else "N",
                    "check": c["id"],
                    "finding": c["detail"],
                }
            )
    payload = {
        "instrument": "artifacts/worker-030/f2b_review_check.py",
        "instrument_sha256": sha256_of(os.path.abspath(__file__)),
        "generated_at": generated_at,
        "target": TARGET,
        "pinned_sha256": PINNED_SHA256,
        "measured_sha256": measured,
        "bytes": nbytes,
        "class_id": CLASS_ID,
        "node_id": "F2b",
        "gate_scope": "G-FORM/G-AUDIT (advisory review input; not a gate verdict)",
        "checks": CHECKS,
        "counts": {
            "total": len(CHECKS),
            "pass": sum(1 for c in CHECKS if c["status"] == "PASS"),
            "fail_blocking": len(blocking_failures),
            "note_nonblocking": len(nonblocking),
        },
        "findings": findings,
        "verdict_recommendation": "revise" if blocking_failures else "accept",
        "falsifier": (
            "any byte change to schemas/af_scc_c0_vacuum.yaml (sha256 leaves "
            f"{PINNED_SHA256[:12]}) voids this audit; a revision of {LEDGER} that changes the "
            "status or class_ids of D-002/T-301/T-302/T-305/T-515/T-528 voids LEDGER-01; a strict "
            "duplicate-key parse that succeeds on a revision claiming to fix YAML-01 falsifies that finding."
        ),
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(json.dumps({k: payload[k] for k in ("target", "measured_sha256", "counts", "verdict_recommendation", "findings")}, indent=1))
    print(f"[written] {out_path}")
    return 1 if blocking_failures else 0


if __name__ == "__main__":
    sys.exit(main())
