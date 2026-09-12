#!/usr/bin/env python3
"""Worker-053 independent instrument for the F2b (AF-SCC-C0-VAC-GEN) review at the
FROZEN rev29 pins (astra-life05-verify-gform-r3 axes).

Checks, from scratch (no reuse of worker-075's instrument):
  C1  FROZEN rev29 pin for the canonical F2b schema resolves to the measured bytes
  C2  every one of the 50 pins in the FROZEN manifest resolves to measured bytes
  C3  authoring mirror artifacts/formulation/schemas/af_scc_c0_vacuum.yaml is byte-identical
  C4  f0_binding: declared F0 hash, consistency-evidence hash, and both pointers resolve
  C5  a staged re-run of the canonical consistency checker reproduces the evidence bytes
  C6  class identity cross-checked against the declared F0 taxonomy + alias canon
  C7  assertive class-leakage scan (own scan) + canonical detector (recorded)
  C8  no conclusion inflation / promotion / refutation laundering
  C9  quantifier order, comeager binder, topology and future-C0 extension binding
  C10 internal consistency of the implication ledger (containment vs transfer reasons)
  C11 target/manifest bytes stable across the review window (T0 -> T1)
  C12 every r3-required review axis is present and non-empty

Exit 0 always; the report is the deliverable.  Read-only outside the worker artifact tree.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../ai4math-swarm
STAGE = HERE / "stage"
WARDEN = HERE / "_mutation_warden"

SCHEMA_REL = "schemas/af_scc_c0_vacuum.yaml"
MIRROR_REL = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
MANIFEST_REL = "artifacts/formulation/FROZEN.json"
F0_REL = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT_REL = "artifacts/formulation/formulation_taxonomy.yaml"
EVIDENCE_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
ALIASES_REL = "artifacts/formulation/VOCAB_ALIASES.json"
CONSISTENCY_TOOL_REL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
CLASS_SCHEMA_TOOL_REL = "artifacts/formulation/tools/check_class_schema.py"
CLASS_SEP_REL = "research_map/class_separation.py"
CASES_REL = "schemas/taxonomy_cases.jsonl"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(rel: str) -> dict:
    p = ROOT / rel
    if not p.exists():
        return {"path": rel, "exists": False}
    return {"path": rel, "exists": True, "sha256": sha256_file(p), "bytes": p.stat().st_size}


def mpin(manifest, rel):
    return (manifest.get("files") or {}).get(rel)


def get(d, dotted, default=None):
    cur = d
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def canon(aliases: dict, kind: str, token):
    table = aliases.get(kind, {})
    tok = str(token)
    for c, alts in table.items():
        if tok == c or tok in [str(a) for a in alts]:
            return c
    return tok


def load_ctx() -> dict:
    return {
        "schema_rel": SCHEMA_REL,
        "mirror_rel": MIRROR_REL,
        "manifest_rel": MANIFEST_REL,
        "schema": yaml.safe_load((ROOT / SCHEMA_REL).read_text()),
        "manifest": json.loads((ROOT / MANIFEST_REL).read_text()),
        "f0": yaml.safe_load((ROOT / F0_REL).read_text()),
        "supplement": yaml.safe_load((ROOT / SUPPLEMENT_REL).read_text()),
        "aliases": json.loads((ROOT / ALIASES_REL).read_text()),
        "measured": {r: measure(r) for r in (
            SCHEMA_REL, MIRROR_REL, MANIFEST_REL, F0_REL, SUPPLEMENT_REL,
            EVIDENCE_REL, CONSISTENCY_TOOL_REL, CLASS_SCHEMA_TOOL_REL,
            CLASS_SEP_REL, CASES_REL)},
    }


# ---------------------------------------------------------------- checks

def c1_frozen_pin(ctx):
    pin = mpin(ctx["manifest"], SCHEMA_REL)
    m = ctx["measured"][SCHEMA_REL]
    ok = bool(pin) and m.get("exists") and pin.get("sha256") == m.get("sha256") and \
        pin.get("bytes") == m.get("bytes")
    return {
        "status": "PASS" if ok else "FAIL",
        "frozen_revision": ctx["manifest"].get("revision"),
        "manifest_frozen_at": ctx["manifest"].get("frozen_at"),
        "declared_pin": pin,
        "measured": m,
    }


def c2_all_manifest_pins(ctx):
    bad = []
    n = 0
    for rel, pin in (ctx["manifest"].get("files") or {}).items():
        n += 1
        m = measure(rel)
        if not m.get("exists") or m.get("sha256") != pin.get("sha256") or m.get("bytes") != pin.get("bytes"):
            bad.append({"path": rel, "declared": pin, "measured": m})
    return {"status": "PASS" if not bad else "FAIL", "n_pins": n, "bad": bad}


def c3_mirror(ctx):
    a = measure(ctx["schema_rel"])
    b = measure(ctx["mirror_rel"])
    mirror_pin = mpin(ctx["manifest"], MIRROR_REL)
    ok = a.get("sha256") == b.get("sha256") and b.get("sha256") == (mirror_pin or {}).get("sha256")
    return {"status": "PASS" if ok else "FAIL", "canonical": a, "mirror": b,
            "manifest_pin": mirror_pin}


def c4_f0_binding(ctx):
    fb = ctx["schema"].get("f0_binding") or {}
    f0 = ctx["measured"][F0_REL]
    ev = ctx["measured"][EVIDENCE_REL]
    sup = ctx["measured"][SUPPLEMENT_REL]
    sup_pin = mpin(ctx["manifest"], SUPPLEMENT_REL)
    errs = []
    if fb.get("declared_f0_sha256") != f0.get("sha256"):
        errs.append("declared_f0_sha256 != measured F0")
    if fb.get("consistency_evidence_sha256") != ev.get("sha256"):
        errs.append("consistency_evidence_sha256 != measured evidence")
    cid = ctx["schema"].get("class_id")
    ptr = str(ctx["schema"].get("class_contract_pointer") or fb.get("class_contract_pointer") or "")
    if ptr != f"research_map/formulation_taxonomy.yaml#classes.{cid}":
        errs.append(f"class_contract_pointer does not resolve to classes.{cid} (got {ptr!r})")
    sptr = str(fb.get("class_contract_supplement_pointer")
               or ctx["schema"].get("class_contract_supplement_pointer") or "")
    if sptr != f"artifacts/formulation/formulation_taxonomy.yaml#class_contracts.{cid}":
        errs.append(f"class_contract_supplement_pointer does not resolve to class_contracts.{cid}")
    if (ctx["supplement"].get("class_contracts") or {}).get(cid) is None:
        errs.append("supplement has no class_contracts entry for the class")
    if sup_pin and sup_pin.get("sha256") != sup.get("sha256"):
        errs.append("supplement manifest pin != measured supplement")
    return {"status": "PASS" if not errs else "FAIL", "errors": errs,
            "declared": {k: fb.get(k) for k in (
                "declared_f0_artifact", "declared_f0_sha256", "consistency_evidence",
                "consistency_evidence_sha256", "checked_at")},
            "measured_f0": f0, "measured_evidence": ev, "measured_supplement": sup}


def c5_consistency_replay(ctx):
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "artifacts/formulation/tools").mkdir(parents=True)
    (STAGE / "artifacts/formulation/evidence").mkdir(parents=True)
    (STAGE / "research_map").mkdir(parents=True)
    shutil.copy2(ROOT / CONSISTENCY_TOOL_REL, STAGE / CONSISTENCY_TOOL_REL)
    shutil.copy2(ROOT / F0_REL, STAGE / F0_REL)
    shutil.copy2(ROOT / SUPPLEMENT_REL, STAGE / SUPPLEMENT_REL)
    shutil.copy2(ROOT / ALIASES_REL, STAGE / ALIASES_REL)
    proc = subprocess.run([sys.executable, str(STAGE / CONSISTENCY_TOOL_REL)],
                          capture_output=True, text=True, cwd=str(STAGE), timeout=120)
    out_rel = "artifacts/formulation/evidence/taxonomy_consistency.json"
    staged = STAGE / out_rel
    replay = sha256_file(staged) if staged.exists() else None
    canonical = ctx["measured"][EVIDENCE_REL].get("sha256")
    match = replay == canonical
    return {"status": "PASS" if match else "FAIL", "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[:300], "stderr": proc.stderr.strip()[:300],
            "canonical_evidence_sha256": canonical, "replay_sha256": replay,
            "bytes_identical": match}


def c6_class_identity(ctx):
    s = ctx["schema"]
    aliases = ctx["aliases"]
    cls = (ctx["f0"].get("classes") or {}).get(s.get("class_id"))
    errs, detail = [], {}
    comp = s.get("class_components") or {}
    detail["components"] = comp
    if s.get("node_id") != "F2b":
        errs.append("node_id != F2b")
    if not cls:
        errs.append("class missing from declared F0 taxonomy")
    else:
        allowed = (comp.get("asymptotics"), comp.get("censorship"), comp.get("matter"),
                   comp.get("genericity"), comp.get("regularity_token"))
        exp = ("AF", "SCC", "VAC", "GEN", "C0")
        if allowed != exp:
            errs.append(f"class components {allowed} != {exp}")
        ax = cls.get("axes") or {}
        if ax.get("family") != comp.get("censorship"):
            errs.append("family != taxonomy axes.family")
        if ax.get("regularity_token") != comp.get("regularity_token"):
            errs.append("regularity_token != taxonomy axes.regularity_token")
        if canon(aliases, "conclusion_type", s["conclusion"].get("conclusion_type")) != \
           canon(aliases, "conclusion_type", ax.get("conclusion_type")):
            errs.append("conclusion_type not alias-equal to taxonomy")
        if canon(aliases, "genericity_kind", s["genericity"].get("kind")) != \
           canon(aliases, "genericity_kind", ax.get("genericity_kind")):
            errs.append("genericity kind not alias-equal to taxonomy")
        detail["taxonomy_axes"] = ax
    if s.get("sibling_disjoint_from") != "AF-SCC-C2-VAC-GEN":
        errs.append("sibling_disjoint_from != AF-SCC-C2-VAC-GEN")
    forbidden = ((ctx["f0"].get("transfer_rules") or {}).get("forbidden") or [])
    if not any((r.get("from") == "AF-SCC-C2-VAC-GEN" and r.get("to") == "AF-SCC-C0-VAC-GEN")
               or ("AF-SCC-C2-VAC-GEN -> AF-SCC-C0-VAC-GEN" in str(r.get("pattern", "")))
               for r in forbidden):
        errs.append("taxonomy does not forbid the C2 -> C0 converse")
    if s.get("family") and s.get("family") != comp.get("censorship"):
        errs.append("top-level family disagrees with class_components.censorship")
    return {"status": "PASS" if not errs else "FAIL", "errors": errs, "detail": detail}


ASSERTIVE_PATHS = [
    "scope_statement", "quantifiers.formal", "quantifiers.negation",
    "quantifiers.negation_normal_form", "quantifiers.order_note",
    "conclusion.statement_natural_language", "conclusion.statement_formal",
    "conclusion.equivalent_rephrasings",
    "conclusion.conclusion_type", "extension_predicate.definition",
    "genericity.ambient_space", "genericity.topology_or_measure", "genericity.generic_set",
    "data_class.regularity_class.default", "data_class.equations", "known_status.status",
    "known_status.refutation_candidate", "known_status.consequence",
    "c0_specifics.conclusion_relation_to_sibling",
]
MENTION_PATHS = [
    "anti_scope.not_this_class", "implication_ledger.forbidden_transfers",
    "l1_ledger_refs", "class_identity_variants", "known_status.why_this_class_is_not_recorded_as_refuted",
]
COMPOSITE = re.compile(r"\bC0\s*(?:or|/|,|and|&)\s*C2\b|\bC2\s*(?:or|/|,|and|&)\s*C0\b", re.I)
MERGE = re.compile(r"(one class|same class|merged|merge|share one schema|unified class|are one)", re.I)
FOREIGN_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def _collect(obj, path):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _collect(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _collect(v, f"{path}[{i}]")
    else:
        yield path, obj


def c7_leakage(ctx):
    s = ctx["schema"]
    assertive, mentions = [], []
    for p in ASSERTIVE_PATHS:
        for path, val in _collect(get(s, p, ""), p):
            text = str(val)
            if COMPOSITE.search(text) or MERGE.search(text):
                assertive.append({"path": path, "match": COMPOSITE.search(text).group(0)
                                  if COMPOSITE.search(text) else MERGE.search(text).group(0),
                                  "text": text[:240]})
            for fid in FOREIGN_IDS:
                if fid == s.get("class_id"):
                    continue
                if fid in text and not re.search(r"not\b|exclud|forbidden|sibling|anti_scope|weaker|stronger",
                                                 text, re.I):
                    assertive.append({"path": path, "match": fid, "text": text[:240]})
    for p in MENTION_PATHS:
        for path, val in _collect(get(s, p, ""), p):
            text = str(val)
            if COMPOSITE.search(text) or any(f in text for f in FOREIGN_IDS):
                mentions.append({"path": path, "text": text[:240]})
    # canonical detector as a secondary instrument (untrusted, recorded verbatim)
    det = {"available": False}
    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import class_separation  # type: ignore
        found = class_separation.findings(s, SCHEMA_REL)
        det = {"available": True, "module_sha256": ctx["measured"][CLASS_SEP_REL].get("sha256"),
               "findings": list(found) if found else []}
    except Exception as exc:  # pragma: no cover
        det = {"available": False, "error": repr(exc)}
    ok = not assertive and not det.get("findings")
    return {"status": "PASS" if ok else "FAIL", "assertive": assertive, "mentions": mentions,
            "canonical_detector": det}


FORBIDDEN_STATUS = re.compile(r"theorem|proved|proven|refuted|established|settled", re.I)


def c8_conclusion(ctx):
    s = ctx["schema"]
    aliases = ctx["aliases"]
    con = s.get("conclusion") or {}
    errs = []
    ctype = canon(aliases, "conclusion_type", con.get("conclusion_type"))
    if ctype != "scc_c0_future_inextendibility":
        errs.append(f"conclusion_type {ctype} is not the C0 SCC class conclusion")
    if con.get("epistemic_status") != "open_problem":
        errs.append("conclusion.epistemic_status != open_problem")
    if con.get("family") != "SCC":
        errs.append("conclusion.family != SCC")
    if s.get("epistemic_status") != "open_problem":
        errs.append("schema epistemic_status != open_problem")
    cp = str(con.get("claim_promotion", ""))
    if not cp:
        errs.append("no claim_promotion rule")
    if "artifact_refs" not in cp or "open_problem" not in cp:
        errs.append("claim_promotion does not require artifact_refs under open_problem")
    for path, val in _collect(con, "conclusion"):
        if path.endswith("claim_promotion"):
            continue
        if FORBIDDEN_STATUS.search(str(val)) and "not " not in str(val).lower()[:40]:
            errs.append(f"assertive proof/refutation language at {path}")
    ks = s.get("known_status") or {}
    if ks.get("status") != "open_problem_with_scoped_conditional_refutation":
        errs.append("known_status.status does not quarantine the conditional refutation")
    if "CH" not in str(ks.get("consequence", "")) and "variant" not in str(ks.get("consequence", "")):
        errs.append("known_status.consequence does not quarantine to variant CH")
    vr = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    variants = vr.get("variants") or vr.get("classes") or vr
    ch = None
    if isinstance(variants, dict):
        ch = variants.get("AF-SCC-C0-CH-VAC-GEN") or variants.get("CH")
    elif isinstance(variants, list):
        ch = next((v for v in variants if str(v.get("variant_id")) == "CH"
                   or str(v.get("variant_id")) == "AF-SCC-C0-CH-VAC-GEN"), None)
    if not ch:
        errs.append("VARIANT_REGISTRY has no CH variant for the quarantined conditional refutation")
    if (s.get("i_plus") or {}).get("in_conclusion") is not False:
        errs.append("i_plus is claimed in the conclusion")
    if (s.get("visibility") or {}).get("role") != "not_in_conclusion":
        errs.append("visibility role is not 'not_in_conclusion'")
    if not (con.get("forbidden_strengthenings") and con.get("forbidden_weakenings")):
        errs.append("forbidden_strengthenings/weakenings missing")
    return {"status": "PASS" if not errs else "FAIL", "errors": errs,
            "conclusion_type": ctype, "epistemic_status": con.get("epistemic_status"),
            "ch_variant_present": bool(ch)}


def c9_quantifier_topology(ctx):
    s = ctx["schema"]
    q = s.get("quantifiers") or {}
    t = s.get("topology") or {}
    errs = []
    kinds = [o.get("kind") for o in (q.get("ordered") or [])]
    if kinds != ["forall", "exists", "forall", "not_exists"]:
        errs.append(f"quantifier order {kinds} != [forall, exists, forall, not_exists]")
    if q.get("quantifier_class") != "forall-exists(comeager)-forall-not-exists(extension)":
        errs.append("quantifier_class string inconsistent with the ordered form")
    if q.get("order_matters") is not True:
        errs.append("order_matters not true")
    d1 = str(get(q, "domains.D1.definition", ""))
    if "comeager" not in d1:
        errs.append("D1 is not the comeager set")
    ext = s.get("extension_predicate") or {}
    if ext.get("frozen_regularity") != "C0":
        errs.append("extension_predicate.frozen_regularity != C0")
    if ext.get("frozen_direction") != "future":
        errs.append("extension_predicate.frozen_direction != future")
    if "future" not in str(s.get("conclusion", {}).get("statement_formal", "")):
        pass  # direction is bound by extension_predicate and quantifier class
    if t.get("spacetime_dimension") != 4:
        errs.append("topology.spacetime_dimension != 4")
    if "R^3" not in str(t.get("slice_topology", "")) or "one" not in str(t.get("end_structure", "")):
        errs.append("slice topology / one-ended AF structure not bound")
    if "R x S^2" not in str(t.get("I_plus_topology", "")):
        errs.append("I_plus_topology != R x S^2")
    if not t.get("development_topology") or not t.get("extension_topology"):
        errs.append("development/extension topology missing")
    return {"status": "PASS" if not errs else "FAIL", "errors": errs, "kinds": kinds,
            "quantifier_class": q.get("quantifier_class")}


CHAIN_RE = re.compile(r"E_\{?([A-Za-z0-9^,]+)\}?")
SIZE_WORD = re.compile(r"\b(larger|bigger|wider|smaller|narrower|subset|contain(s|ed)?)\b", re.I)


def _chain_ranks(containment: str):
    toks = CHAIN_RE.findall(containment or "")
    return {t: i for i, t in enumerate(toks)}, toks


def _norm_tok(tok):
    tok = str(tok).replace(" ", "")
    if tok in ("C0", "C2"):
        return tok
    if tok.lower().startswith("h2"):
        return "H2loc"
    if "1,1" in tok or "1,1" in tok.replace(" ", ""):
        return "C11"
    return tok


def c10_containment(ctx):
    s = ctx["schema"]
    il = s.get("implication_ledger") or {}
    containment = str(il.get("extension_class_containment", ""))
    ranks, toks = _chain_ranks(containment)
    here = _norm_tok((s.get("class_components") or {}).get("regularity_token", "C0"))
    errs, notes = [], []
    if len(ranks) < 3:
        errs.append({"field": "implication_ledger.extension_class_containment",
                     "detail": "containment chain not parseable", "text": containment[:240]})
    # one-way entailments must run from the larger extension set to the smaller
    for i, row in enumerate(il.get("one_way_entailments") or []):
        frm = _norm_tok(re.search(r"(?:E_)?\{?(C0|C2|H2[^ ,;]*|C\^?\{?1,1\}?)", str(row.get("from", ""))).group(1)) \
            if re.search(r"(?:E_)?\{?(C0|C2|H2[^ ,;]*|C\^?\{?1,1\}?)", str(row.get("from", ""))) else None
        to = _norm_tok(re.search(r"(?:E_)?\{?(C0|C2|H2[^ ,;]*|C\^?\{?1,1\}?)", str(row.get("to", ""))).group(1)) \
            if re.search(r"(?:E_)?\{?(C0|C2|H2[^ ,;]*|C\^?\{?1,1\}?)", str(row.get("to", ""))) else None
        if frm in ranks and to in ranks and ranks[frm] > ranks[to]:
            errs.append({"field": f"implication_ledger.one_way_entailments[{i}]",
                         "detail": f"entailment {frm} -> {to} contradicts containment order",
                         "text": str(row)[:240]})
    # forbidden-transfer reasons must not assert the opposite size relation
    for i, row in enumerate(il.get("forbidden_transfers") or []):
        reason = str(row.get("reason", ""))
        frm_tok = None
        m = re.search(r"\b(C0|C2|H2_?loc|C\^?\{?1,1\}?)\b", str(row.get("from", "")))
        if m:
            frm_tok = _norm_tok(m.group(1))
        for sm in SIZE_WORD.finditer(reason):
            word = sm.group(1).lower()
            ctx_txt = reason[max(0, sm.start() - 40): sm.end() + 20]
            # token that the size word is predicated of
            tm = re.search(r"\b(C0|C2|H2_?loc|C\^?\{?1,1\}?)\b", ctx_txt)
            if not tm or frm_tok is None:
                continue
            tok = _norm_tok(tm.group(1))
            if tok not in ranks or here not in ranks or tok == here:
                continue
            # chain order is DECREASING set size: rank 0 = largest extension class
            claims_larger = word in ("larger", "bigger", "wider", "contain", "contains", "contained")
            relation_ok = (ranks[tok] < ranks[here]) if claims_larger else (ranks[tok] > ranks[here])
            if not relation_ok:
                errs.append({
                    "field": f"implication_ledger.forbidden_transfers[{i}].reason",
                    "detail": (f"reason asserts '{tok} is a strictly {word} extension class' "
                               f"but containment has E_{here} (rank {ranks[here]}) "
                               f"{'contains' if ranks[here] < ranks[tok] else 'is contained in'} "
                               f"E_{tok} (rank {ranks[tok]})"),
                    "text": reason[:240],
                })
            break
    return {"status": "PASS" if not errs else "FAIL", "errors": errs,
            "containment": containment[:300], "ranks": ranks, "notes": notes}


REQUIRED_AXES = [
    "class_id", "class_components", "scope_statement", "quantifiers", "topology",
    "data_class", "regularity", "genericity", "extension_predicate", "i_plus",
    "visibility", "conclusion", "falsifier", "anti_scope", "f0_binding",
    "promotion_rule", "epistemic_status", "sibling_disjoint_from",
]


def c12_required_axes(ctx):
    s = ctx["schema"]
    missing = [k for k in REQUIRED_AXES if s.get(k) in (None, "", [], {})]
    return {"status": "PASS" if not missing else "FAIL", "missing": missing,
            "n_required": len(REQUIRED_AXES)}


def run_checks(ctx):
    out = {}
    out["C1_frozen_pin_f2b"] = c1_frozen_pin(ctx)
    out["C2_all_manifest_pins"] = c2_all_manifest_pins(ctx)
    out["C3_mirror_byte_identical"] = c3_mirror(ctx)
    out["C4_f0_binding"] = c4_f0_binding(ctx)
    out["C5_consistency_replay"] = c5_consistency_replay(ctx)
    out["C6_class_identity"] = c6_class_identity(ctx)
    out["C7_leakage"] = c7_leakage(ctx)
    out["C8_conclusion"] = c8_conclusion(ctx)
    out["C9_quantifier_topology"] = c9_quantifier_topology(ctx)
    out["C10_containment"] = c10_containment(ctx)
    out["C12_required_axes"] = c12_required_axes(ctx)
    return out


# ---------------------------------------------------------------- controls

def _clone(ctx):
    c = dict(ctx)
    c["schema"] = copy.deepcopy(ctx["schema"])
    c["manifest"] = copy.deepcopy(ctx["manifest"])
    return c


def mk_controls(base_ctx):
    results = {}

    def record(name, expect, got, detail):
        results[name] = {"expect": expect, "got": got, "detected": got == expect, "detail": detail}

    c = _clone(base_ctx); c["schema"]["f0_binding"]["declared_f0_sha256"] = "0" * 64
    r = c4_f0_binding(c); record("M1_stale_f0_pin", "FAIL", r["status"], r["errors"][:2])

    if WARDEN.exists():
        shutil.rmtree(WARDEN)
    WARDEN.mkdir(parents=True)
    flipped = WARDEN / "af_scc_c0_vacuum.yaml"
    flipped.write_bytes((ROOT / MIRROR_REL).read_bytes() + b"\n# mutation\n")
    c = _clone(base_ctx); c["mirror_rel"] = str(flipped)
    r = c3_mirror(c); record("M2_mirror_byte_flip", "FAIL", r["status"],
                             {"mirror": r["mirror"].get("sha256"), "canonical": r["canonical"].get("sha256")})

    c = _clone(base_ctx); c["schema"]["class_id"] = "AF-SCC-C2-VAC-GEN"
    r = c6_class_identity(c); record("M3_foreign_class_id", "FAIL", r["status"], r["errors"][:2])

    c = _clone(base_ctx)
    c["schema"]["conclusion"]["equivalent_rephrasings"].append(
        {"phrasing": "The C0 or C2 statement is one class in the vacuum case.", "status": "asserted"})
    r = c7_leakage(c); record("M4_assertive_composite", "FAIL", r["status"], r["assertive"][:1])

    c = _clone(base_ctx)
    c["schema"]["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
        "C2 extensions form a strictly smaller class, so C2-inextendibility is strictly weaker")
    r = c10_containment(c); record("M5_corrected_reason", "PASS", r["status"], r["errors"][:1])

    c = _clone(base_ctx)
    c["schema"]["quantifiers"]["ordered"] = list(reversed(c["schema"]["quantifiers"]["ordered"]))
    r = c9_quantifier_topology(c); record("M6_quantifier_reorder", "FAIL", r["status"], r["errors"][:1])

    c = _clone(base_ctx); c["schema"].pop("f0_binding", None)
    r = c12_required_axes(c); record("M7_missing_axis", "FAIL", r["status"], r["missing"])

    c = _clone(base_ctx)
    c["manifest"]["files"][SCHEMA_REL]["sha256"] = "f" * 64
    r = c1_frozen_pin(c); record("M8_tampered_manifest_pin", "FAIL", r["status"],
                                 {"declared": r["declared_pin"], "measured": r["measured"].get("sha256")})

    c = _clone(base_ctx)
    c["schema"]["implication_ledger"]["extension_class_containment"] = (
        "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0; this class requires the HIGHEST regularity")
    r = c10_containment(c); record("M9_inverted_chain", "FAIL", r["status"], r["errors"][:1])

    detected = sum(1 for v in results.values() if v["detected"])
    return {"results": results, "detected": f"{detected}/{len(results)}",
            "all_detected": detected == len(results)}


# ---------------------------------------------------------------- main

def main():
    t0 = time.time()
    ctx = load_ctx()
    target0 = ctx["measured"][SCHEMA_REL].get("sha256")
    manifest0 = ctx["measured"][MANIFEST_REL].get("sha256")
    checks = run_checks(ctx)
    controls = mk_controls(ctx)
    time.sleep(2.0)
    end = {r: measure(r) for r in (SCHEMA_REL, MANIFEST_REL)}
    stable = (end[SCHEMA_REL].get("sha256") == target0 and
              end[MANIFEST_REL].get("sha256") == manifest0)
    checks["C11_window_stability"] = {
        "status": "PASS" if stable else "FAIL",
        "start": {"target": target0, "manifest": manifest0},
        "end": {"target": end[SCHEMA_REL].get("sha256"), "manifest": end[MANIFEST_REL].get("sha256")},
    }
    # secondary instruments, recorded verbatim
    tool = subprocess.run([sys.executable, str(ROOT / CLASS_SCHEMA_TOOL_REL), SCHEMA_REL],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=180)
    secondary = {
        "check_class_schema": {"returncode": tool.returncode,
                               "stdout_tail": tool.stdout.strip()[-300:],
                               "stderr_tail": tool.stderr.strip()[-300:]},
        "check_taxonomy_cases": None,
    }
    try:
        tc = subprocess.run([sys.executable, "artifacts/flash-02/check_taxonomy_cases.py"],
                            capture_output=True, text=True, cwd=str(ROOT), timeout=180)
        secondary["check_taxonomy_cases"] = {"returncode": tc.returncode,
                                             "stdout_tail": tc.stdout.strip()[-300:]}
    except Exception as exc:
        secondary["check_taxonomy_cases"] = {"error": repr(exc)}
    # taxonomy_cases meta must bind the declared F0 rev5 and the live cases bytes
    cases_pin = mpin(ctx["manifest"], CASES_REL)
    cases_live = ctx["measured"][CASES_REL]
    try:
        meta = json.loads((ROOT / CASES_REL).read_text().splitlines()[0])
    except Exception:
        meta = {}
    checks["C13_cases_binding"] = {
        "status": "PASS" if (cases_pin and cases_pin.get("sha256") == cases_live.get("sha256")
                             and get(meta, "taxonomy_ref.sha256") == ctx["measured"][F0_REL].get("sha256"))
                  else "FAIL",
        "manifest_pin": cases_pin, "measured": cases_live,
        "meta_taxonomy_ref": get(meta, "taxonomy_ref"),
        "rebound_at": meta.get("rebound_at"),
    }
    hard = []
    for name, res in checks.items():
        if res.get("status") == "FAIL":
            if name == "C10_containment":
                for e in res["errors"]:
                    hard.append({"id": "W053-F2B-REV29-01", "severity": "major",
                                 "field": e["field"], "detail": e["detail"],
                                 "falsifier": "a containment-respecting model in which E_C2 is strictly "
                                              "larger than E_C0, or corrected bytes in a new revision"})
            else:
                hard.append({"id": f"W053-F2B-REV29-{name}", "severity": "major", "field": name,
                             "detail": json.dumps(res)[:400],
                             "falsifier": "re-measure at the pinned bytes with a corrected instrument"})
    verdict = "accept" if not hard else "revise"
    report = {
        "instrument": "artifacts/worker-053/f2b_rev29_review/check_f2b_rev29.py",
        "reviewer": "worker-053",
        "non_blind_note": ("worker-075's F2b rev29 verdict was read before this review was finalized; "
                           "this is a confirmatory re-measurement with an independent from-scratch "
                           "instrument, NOT one of the two blind verdicts requested by "
                           "astra-life05-verify-gform-r3"),
        "counts_as_full_schema_verdict": False,
        "class_id": ctx["schema"].get("class_id"),
        "node_id": ctx["schema"].get("node_id"),
        "gate": "G-FORM",
        "frozen_revision": ctx["manifest"].get("revision"),
        "frozen_frozen_at": ctx["manifest"].get("frozen_at"),
        "manifest_sha256": manifest0,
        "reviewed_sha256": target0,
        "target_bytes": ctx["measured"][SCHEMA_REL].get("bytes"),
        "checks": checks,
        "controls": controls,
        "secondary_instruments": secondary,
        "hard_failures": hard,
        "verdict": verdict,
        "score": 3.5 if verdict == "revise" else 4.0,
        "elapsed_s": round(time.time() - t0, 2),
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    out = Path(sys.argv[sys.argv.index("--report") + 1]) if "--report" in sys.argv else HERE / "report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "reviewed_sha256": target0,
                      "hard_failures": [h["field"] for h in hard],
                      "controls": controls["detected"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
