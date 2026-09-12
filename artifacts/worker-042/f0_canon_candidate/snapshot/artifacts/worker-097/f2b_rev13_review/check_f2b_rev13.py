#!/usr/bin/env python3
"""W097-F2B-REV13-INDEP-REVIEW-01 instrument.

Independent, read-only, fail-closed class-contract conformance check for
schemas/af_scc_c0_vacuum.yaml (class AF-SCC-C0-VAC-GEN, node F2b) at revision 13.

Writes only under artifacts/worker-097/f2b_rev13_review/. Imports no other agent's checker.
Pre-registration: PREREGISTRATION.md (written before this file was executed).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

ART = os.path.dirname(os.path.abspath(__file__))
PINS = os.path.join(ART, "pins")
CST = timezone(timedelta(hours=8))

EXPECT = {
    "schema_path": "schemas/af_scc_c0_vacuum.yaml",
    "mirror_path": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "sibling_path": "schemas/af_scc_c2_vacuum.yaml",
    "f0_path": "research_map/formulation_taxonomy.yaml",
    "supplement_path": "artifacts/formulation/formulation_taxonomy.yaml",
    "frozen_path": "artifacts/formulation/FROZEN.json",
    "alias_path": "artifacts/formulation/VOCAB_ALIASES.json",
    "evidence_path": "artifacts/formulation/evidence/taxonomy_consistency.json",
    "variant_registry_path": "artifacts/formulation/VARIANT_REGISTRY.json",
    "class_id": "AF-SCC-C0-VAC-GEN",
    "node_id": "F2b",
    "gate": "G-FORM",
}

REQUIRED_TOP = [
    "schema_version", "artifact_kind", "class_id", "node_id", "owner", "authored_by",
    "revision", "revision_history", "class_components", "class_contract_pointer",
    "class_contract_supplement_pointer", "sibling_disjoint_from", "quantifiers", "topology",
    "data_class", "regularity", "genericity", "non_vacuity", "i_plus", "visibility",
    "conclusion", "implication_ledger", "falsifier", "anti_scope", "class_identity_variants",
    "f0_binding", "provenance", "unresolved_items", "review_status",
]

MATTER_COMPONENT_MAP = {"VAC": "vacuum"}
ASYMPTOTICS_COMPONENT_MAP = {"AF": "asymptotically_flat_3p1"}

INVERTED_C2_PATTERNS = [
    (r"C2\s+is\s+a\s+strictly\s+larger", "calls C2 a strictly larger extension class"),
    (r"C2[^.]{0,60}strictly\s+larger\s+extension\s+class", "calls C2 a strictly larger extension class"),
    (r"C2-inextendibility\s+is\s+strictly\s+stronger", "calls C2-inextendibility strictly stronger"),
    (r"C2[^.]{0,40}\bstronger\s+than\s+(this\s+class|C0|the\s+C0)", "calls C2-inextendibility stronger than C0"),
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_duplicate_keys(raw: str):
    node = yaml.compose(raw)
    dups = []

    def walk(n, path):
        if isinstance(n, yaml.MappingNode):
            seen = {}
            for k, v in n.value:
                key = getattr(k, "value", None)
                if key in seen:
                    dups.append({"path": path, "key": key,
                                 "lines": [seen[key], k.start_mark.line + 1]})
                else:
                    seen[key] = k.start_mark.line + 1
                walk(v, f"{path}.{key}")
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, f"{path}[{i}]")

    walk(node, "$")
    return dups


def resolve_pointer(doc, pointer: str, repo: str):
    """pointer = '<path>#a.b.c' -> (exists, resolved_object, reason)."""
    if "#" not in pointer:
        return False, None, "no fragment"
    path, frag = pointer.split("#", 1)
    full = os.path.join(repo, path)
    if not os.path.exists(full):
        return False, None, f"file absent: {path}"
    try:
        with open(full) as fh:
            obj = yaml.safe_load(fh)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"parse error: {exc!r}"
    cur = obj
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None, f"fragment {part!r} unresolved"
    return True, cur, "resolved"


def alias_allowed(field: str, token, vocab: dict, aliases: dict):
    """Return (ok, f0_token_or_None, how). Alias-aware against F0 field_vocabulary.

    The alias registry maps schema-side canonical tokens to F0 vocabulary tokens
    (e.g. scc_c0_future_inextendibility -> strong_cosmic_censorship_C0). A schema token is
    conformant iff it, or one of its registered aliases, is in the F0 allowed list.
    """
    allowed = list(vocab.get(field, {}).get("allowed", []))
    table = aliases.get(field, {})
    if token in allowed:
        return True, token, "direct"
    for canonical, alist in table.items():
        if token == canonical or token in alist:
            for cand in [canonical] + list(alist):
                if cand in allowed:
                    return True, cand, "alias-registry"
            return False, None, "alias-registry-no-allowed-target"
    return False, None, "unknown"


# --------------------------------------------------------------------------- checks

def h1_structure(d, raw, ctx):
    out = {"title": "structural integrity", "findings": []}
    missing = [k for k in REQUIRED_TOP if k not in d]
    dups = find_duplicate_keys(raw)
    rev = d.get("revision")
    hist = d.get("revision_history") or []
    problems = []
    if missing:
        problems.append(f"missing top-level keys: {missing}")
    if dups:
        problems.append(f"duplicate YAML keys: {dups}")
    if not isinstance(hist, list) or not hist:
        problems.append("revision_history empty or not a list")
        hist = []
    try:
        rev_i = int(rev)
        if len(hist) > rev_i:
            problems.append(f"revision_history longer ({len(hist)}) than revision ({rev_i})")
        elif len(hist) < rev_i:
            out["collapse_gap"] = rev_i - len(hist)
    except Exception:  # noqa: BLE001
        problems.append(f"revision not an int: {rev!r}")
    idx = [h.get("index") for h in hist if isinstance(h, dict)]
    if idx != list(range(1, len(hist) + 1)):
        problems.append(f"revision_history indices not 1..n: {idx}")
    for h in hist:
        if not isinstance(h, dict) or "at" not in h or "unused" not in h or "notes" not in h:
            problems.append(f"history entry malformed: {h!r}")
            break
    try:
        last_at = str(hist[-1].get("at"))
        revised_at = str(d.get("revised_at"))
        if revised_at < last_at:
            problems.append(f"revised_at {revised_at} earlier than last history entry {last_at}")
    except Exception:  # noqa: BLE001
        pass
    out["findings"] = problems
    out["duplicate_keys"] = dups
    out["verdict"] = "fail" if problems else "pass"
    return out


def h2_identity(d, raw, ctx):
    cid = d.get("class_id")
    comp = d.get("class_components") or {}
    want = {"asymptotics": "AF", "censorship": "SCC", "matter": "VAC",
            "genericity": "GEN", "regularity_token": "C0"}
    problems = []
    if cid != EXPECT["class_id"]:
        problems.append(f"class_id {cid!r} != {EXPECT['class_id']!r}")
    for k, v in want.items():
        if comp.get(k) != v:
            problems.append(f"class_components.{k}={comp.get(k)!r} != {v!r}")
    if d.get("node_id") != EXPECT["node_id"]:
        problems.append(f"node_id {d.get('node_id')!r} != {EXPECT['node_id']!r}")
    return {"title": "class identity", "findings": problems,
            "verdict": "fail" if problems else "pass"}


def h3_containment_direction(d, raw, ctx):
    il = d.get("implication_ledger") or {}
    c0 = d.get("c0_specifics") or {}
    nv = d.get("non_vacuity") or {}
    reg = d.get("regularity") or {}
    con = d.get("conclusion") or {}
    var = ((d.get("class_identity_variants") or {}).get("horizon_localized_variant") or {})
    anti = (d.get("anti_scope") or {}).get("not_this_class") or [{}]

    statements = [
        ("implication_ledger.extension_class_containment", il.get("extension_class_containment", "")),
        ("conclusion.forbidden_weakenings", " | ".join(con.get("forbidden_weakenings") or [])),
        ("non_vacuity.vacuity_falsifier", nv.get("vacuity_falsifier", "")),
        ("regularity.must_not_conflate", " | ".join(reg.get("must_not_conflate") or [])),
        ("c0_specifics.conclusion_relation_to_sibling", c0.get("conclusion_relation_to_sibling", "")),
        ("class_identity_variants.horizon_localized_variant.relation", var.get("relation", "")),
        ("anti_scope.not_this_class[0].why", anti[0].get("why", "") if anti else ""),
    ]
    for i, row in enumerate(il.get("one_way_entailments") or []):
        statements.append((f"implication_ledger.one_way_entailments[{i}].reason", row.get("reason", "")))
    for i, row in enumerate(il.get("forbidden_transfers") or []):
        statements.append((f"implication_ledger.forbidden_transfers[{i}].reason", row.get("reason", "")))

    inverted = []
    for path, text in statements:
        for pat, label in INVERTED_C2_PATTERNS:
            if re.search(pat, text, flags=re.IGNORECASE):
                inverted.append({"path": path, "pattern": pat, "label": label,
                                 "text": text.strip()})

    missing_positive = []
    joined = dict(statements)
    required = [
        ("implication_ledger.extension_class_containment", "E_C0 contains"),
        ("implication_ledger.extension_class_containment", "E_C2"),
        ("conclusion.forbidden_weakenings", "substituting C2 or C1 for C0"),
        ("non_vacuity.vacuity_falsifier", "a C2 result is weaker"),
        ("regularity.must_not_conflate", "the implication runs C0 => C2"),
        ("c0_specifics.conclusion_relation_to_sibling",
         "excluding all continuous extensions excludes all C2 extensions"),
        ("class_identity_variants.horizon_localized_variant.relation", "strictly WEAKER"),
    ]
    for path, needle in required:
        if needle not in joined.get(path, ""):
            missing_positive.append({"path": path, "missing": needle})

    problems = []
    inverted_paths = sorted({x["path"] for x in inverted})
    if inverted_paths:
        problems.append(f"{len(inverted_paths)} inverted C0/C2 direction statement path(s): {inverted_paths}")
    if missing_positive:
        problems.append(f"{len(missing_positive)} required direction statement(s) absent")
    return {
        "title": "internal containment-direction consistency (C2 subset C0; C0 strongest)",
        "statements_censused": len(statements),
        "inverted": inverted,
        "inverted_paths": inverted_paths,
        "missing_positive": missing_positive,
        "findings": problems,
        "verdict": "fail" if problems else "pass",
    }


def h3b_containment_denial(d, raw, ctx):
    """A live 'no containment with C2/C0' clause while the artifact asserts containment.

    Added in erratum round 2 after an independent peer review found the line-152 clause; the
    finding was re-derived here from the primary bytes. Clauses carrying an explicit repair
    marker (was wrong / corrected / repaired) are treated as historical notes, not denials.
    """
    clauses = (d.get("regularity") or {}).get("must_not_conflate") or []
    denial = re.compile(r"no\s+containment\s+with\s+(C2|C0|C2 or C0)", re.IGNORECASE)
    repair_marker = re.compile(r"was wrong|corrected|repaired|superseded", re.IGNORECASE)
    cont = (d.get("implication_ledger") or {}).get("extension_class_containment", "")
    asserts = ("E_C0 contains" in cont) and ("E_C2" in cont)
    hits = []
    for i, clause in enumerate(clauses):
        if denial.search(clause) and not repair_marker.search(clause):
            hits.append({"path": f"regularity.must_not_conflate[{i}]", "text": clause.strip()})
    problems = []
    if hits and asserts:
        problems.append(f"{len(hits)} live containment-denial clause(s) contradict "
                        "implication_ledger.extension_class_containment")
    return {"title": "live containment-denial clauses vs asserted containment",
            "artifact_asserts_containment": asserts,
            "denials": hits, "findings": problems,
            "verdict": "fail" if problems else "pass"}


def h4_f0_binding(d, raw, ctx):
    live = ctx["live"]
    repo = ctx["repo"]
    fb = d.get("f0_binding") or {}
    problems = []
    if fb.get("declared_f0_artifact") != EXPECT["f0_path"]:
        problems.append(f"declared_f0_artifact {fb.get('declared_f0_artifact')!r} != {EXPECT['f0_path']!r}")
    if fb.get("declared_f0_sha256") != live.get(EXPECT["f0_path"]):
        problems.append("declared_f0_sha256 != live taxonomy sha256")
    ev = fb.get("consistency_evidence")
    ev_sha = fb.get("consistency_evidence_sha256")
    if ev != EXPECT["evidence_path"]:
        problems.append(f"consistency_evidence {ev!r} != {EXPECT['evidence_path']!r}")
    if not ev or not os.path.exists(os.path.join(repo, ev)):
        problems.append("consistency evidence file absent")
    elif sha256_file(os.path.join(repo, ev)) != ev_sha:
        problems.append("consistency evidence sha256 mismatch with declared value")
    else:
        evd = json.load(open(os.path.join(repo, ev)))
        if evd.get("consistent") is not True:
            problems.append("consistency evidence does not declare consistent=true")
        if EXPECT["class_id"] not in (evd.get("classes_compared") or []):
            problems.append("consistency evidence classes_compared omits this class")
    frozen_path = os.path.join(repo, EXPECT["frozen_path"])
    if not os.path.exists(frozen_path):
        problems.append("FROZEN.json absent")
    else:
        frozen = json.load(open(frozen_path))
        files = frozen.get("files") or {}
        pin_paths = [EXPECT["schema_path"], EXPECT["mirror_path"], EXPECT["f0_path"],
                     EXPECT["supplement_path"], EXPECT["alias_path"], EXPECT["evidence_path"],
                     EXPECT["variant_registry_path"]]
        for p in pin_paths:
            entry = files.get(p)
            if entry is None:
                problems.append(f"FROZEN rev{frozen.get('revision')} does not pin {p}")
            elif entry.get("sha256") != live.get(p):
                problems.append(f"FROZEN pin stale for {p}: {entry.get('sha256','')[:12]} != {live.get(p,'')[:12]}")
    return {
        "title": "declared-F0 binding and FROZEN rev29 pin closure",
        "declared_f0_sha256": fb.get("declared_f0_sha256"),
        "declared_consistency_sha256": ev_sha,
        "findings": problems,
        "verdict": "fail" if problems else "pass",
    }


def h5_pointers(d, raw, ctx):
    repo = ctx["repo"]
    problems = []
    ok1, obj1, why1 = resolve_pointer(d, d.get("class_contract_pointer", ""), repo)
    ok2, obj2, why2 = resolve_pointer(d, d.get("class_contract_supplement_pointer", ""), repo)
    if not ok1:
        problems.append(f"class_contract_pointer unresolved: {why1}")
    if not ok2:
        problems.append(f"class_contract_supplement_pointer unresolved: {why2}")
    if ok1 and isinstance(obj1, dict):
        if obj1.get("axes", {}).get("regularity_token") != "C0":
            problems.append("resolved F0 contract axes.regularity_token != C0")
    if ok2 and isinstance(obj2, dict):
        marker = obj2.get("node_id") or obj2.get("label") or (obj2.get("components") or {}).get("regularity_token")
        if marker is None:
            problems.append("resolved supplement contract carries no node_id/label/components marker")
        elif obj2.get("node_id") is not None and obj2.get("node_id") != EXPECT["node_id"]:
            problems.append(f"supplement contract node_id {obj2.get('node_id')!r} != {EXPECT['node_id']!r}")
    return {"title": "contract pointer resolution", "pointer": d.get("class_contract_pointer"),
            "supplement_pointer": d.get("class_contract_supplement_pointer"),
            "findings": problems, "verdict": "fail" if problems else "pass"}


def h6_quantifiers(d, raw, ctx):
    q = d.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    domains = q.get("domains") or {}
    formal = q.get("formal", "")
    problems = []
    kinds = [row.get("kind") for row in ordered]
    doms = [row.get("domain_id") for row in ordered]
    if kinds != ["forall", "exists", "forall", "not_exists"]:
        problems.append(f"ordered kinds {kinds} != ['forall','exists','forall','not_exists']")
    if doms != ["D0", "D1", "D2", "D3"]:
        problems.append(f"ordered domain_ids {doms} != D0..D3")
    if set(domains) != {"D0", "D1", "D2", "D3"}:
        problems.append(f"domains keys {sorted(domains)} != D0..D3")
    for needle in ["forall r in D0", "exists G_r", "forall (Sigma,h,K)", "not exists"]:
        if needle not in formal:
            problems.append(f"formal text lacks {needle!r}")
    neg = q.get("negation", "")
    if "there exists r in D0" not in neg:
        problems.append("negation is not the exists-r dual")
    if not (q.get("negation_normal_form") and "non-meager" in q["negation_normal_form"]):
        problems.append("negation_normal_form lacks non-meager")
    if q.get("order_matters") is not True:
        problems.append("order_matters is not true")
    for row in ordered:
        did = row.get("domain_id")
        if did in domains and "definition" not in domains[did]:
            problems.append(f"domain {did} has no definition")
    return {"title": "quantifier well-typedness and dual negation", "findings": problems,
            "verdict": "fail" if problems else "pass"}


def h7_vocabulary(d, raw, ctx):
    repo = ctx["repo"]
    tax = yaml.safe_load(open(os.path.join(repo, EXPECT["f0_path"])))
    aliases = json.load(open(os.path.join(repo, EXPECT["alias_path"])))
    vocab = tax.get("field_vocabulary") or {}
    contract = tax["classes"][EXPECT["class_id"]]
    axes = contract.get("axes") or {}
    problems = []

    ct = (d.get("conclusion") or {}).get("conclusion_type")
    ok, f0_ct, how = alias_allowed("conclusion_type", ct, vocab, aliases)
    if not ok:
        problems.append(f"conclusion_type {ct!r} not allowed by F0 field_vocabulary (nor alias)")
    elif f0_ct != axes.get("conclusion_type"):
        problems.append(f"conclusion_type maps to F0 token {f0_ct!r} != F0 axes.conclusion_type {axes.get('conclusion_type')!r}")

    gk = (d.get("genericity") or {}).get("kind")
    ok, f0_gk, how_g = alias_allowed("genericity_kind", gk, vocab, aliases)
    if not ok:
        problems.append(f"genericity.kind {gk!r} not allowed by F0 field_vocabulary (nor alias)")
    elif f0_gk != axes.get("genericity_kind") and {f0_gk, axes.get("genericity_kind")} - {
            "baire_residual", "provisional_baire_residual"}:
        problems.append(f"genericity.kind maps to F0 token {f0_gk!r} != F0 axes.genericity_kind {axes.get('genericity_kind')!r}")

    comp = d.get("class_components") or {}
    if (d.get("conclusion") or {}).get("family") != axes.get("family"):
        problems.append("conclusion.family != F0 axes.family")
    if comp.get("regularity_token") != axes.get("regularity_token"):
        problems.append("class_components.regularity_token != F0 axes.regularity_token")
    if MATTER_COMPONENT_MAP.get(comp.get("matter")) != axes.get("matter_model"):
        problems.append("class_components.matter != F0 axes.matter_model")
    if ASYMPTOTICS_COMPONENT_MAP.get(comp.get("asymptotics")) != axes.get("asymptotics"):
        problems.append(f"class_components.asymptotics {comp.get('asymptotics')!r} != F0 axes.asymptotics")
    if (d.get("data_class") or {}).get("symmetry") != axes.get("symmetry"):
        problems.append("data_class.symmetry != F0 axes.symmetry")
    return {"title": "F0 vocabulary + axes conformance (alias-aware)", "conclusion_type": ct,
            "genericity_kind": gk, "findings": problems,
            "verdict": "fail" if problems else "pass"}


def h8_mirror(d, raw, ctx):
    live = ctx["live"]
    same = live.get(EXPECT["schema_path"]) == live.get(EXPECT["mirror_path"])
    return {"title": "canonical/mirror byte identity",
            "canonical": live.get(EXPECT["schema_path"]),
            "mirror": live.get(EXPECT["mirror_path"]),
            "findings": [] if same else ["canonical and mirror bytes differ"],
            "verdict": "pass" if same else "fail"}


def h9_sibling(d, raw, ctx):
    repo = ctx["repo"]
    problems = []
    if d.get("sibling_disjoint_from") != "AF-SCC-C2-VAC-GEN":
        problems.append(f"sibling_disjoint_from {d.get('sibling_disjoint_from')!r} != AF-SCC-C2-VAC-GEN")
    sib = yaml.safe_load(open(os.path.join(repo, EXPECT["sibling_path"])))
    if sib.get("sibling_disjoint_from") != EXPECT["class_id"]:
        problems.append("F2a does not declare this class as sibling (not mutual)")
    tax = yaml.safe_load(open(os.path.join(repo, EXPECT["f0_path"])))
    pairs = [set(x.get("pair") or []) for x in (tax.get("disjointness") or [])]
    if {"AF-SCC-C2-VAC-GEN", EXPECT["class_id"]} not in pairs:
        problems.append("taxonomy disjointness lacks the C2/C0 pair")
    anti = [x.get("class_id") for x in ((d.get("anti_scope") or {}).get("not_this_class") or [])]
    if "AF-SCC-C2-VAC-GEN" not in anti:
        problems.append("anti_scope.not_this_class omits AF-SCC-C2-VAC-GEN")
    return {"title": "sibling disjointness mutuality", "findings": problems,
            "verdict": "fail" if problems else "pass"}


def h10_review_status(d, raw, ctx):
    rs = d.get("review_status") or {}
    problems = []
    if rs.get("gate") != EXPECT["gate"]:
        problems.append(f"review_status.gate {rs.get('gate')!r} != {EXPECT['gate']!r}")
    if not isinstance(rs.get("requested_reviewers"), list) or not rs.get("requested_reviewers"):
        problems.append("requested_reviewers empty")
    if not isinstance(rs.get("independent_reviewers"), list):
        problems.append("independent_reviewers not a list")
    return {"title": "review_status well-formed", "findings": problems,
            "verdict": "fail" if problems else "pass"}


def advisories(d, raw, ctx):
    repo = ctx["repo"]
    out = []
    alias_tokens = ["scc_c0_future_inextendibility", "residual_comeager"]
    hits = [t for t in alias_tokens if re.search(re.escape(t), raw)]
    if hits:
        out.append({
            "id": "A1", "severity": "minor",
            "title": "accepted alias tokens used in a canonical artifact",
            "detail": (f"tokens {hits} are registered aliases in VOCAB_ALIASES.json; the registry policy "
                       "says 'accepted aliases are equivalent for consistency checks only and must never "
                       "appear in a new canonical artifact'."),
            "evidence": [EXPECT["alias_path"]],
        })
    ev_path = os.path.join(repo, EXPECT["evidence_path"])
    if os.path.exists(ev_path):
        ev = json.load(open(ev_path))
        keys = set(ev)
        if not ({"input_hashes", "sha256", "checked_at", "files"} & keys):
            out.append({
                "id": "A2", "severity": "minor",
                "title": "consistency evidence is a hash-free boolean",
                "detail": ("taxonomy_consistency.json records consistent=true over four classes but no input "
                           "hashes or checked_at; the only byte binding is the sha256 declared in f0_binding "
                           "and pinned by FROZEN."),
                "evidence": [EXPECT["evidence_path"]],
            })
    tax = yaml.safe_load(open(os.path.join(repo, EXPECT["f0_path"])))
    text = ((tax.get("classes", {}).get(EXPECT["class_id"], {}).get("conclusion") or {}).get("text") or "")
    d0 = ((d.get("quantifiers") or {}).get("domains") or {}).get("D0", {}).get("definition", "")
    if "For every admissible (s,delta)" in text and "smooth" in d0:
        out.append({
            "id": "A3", "severity": "minor",
            "title": "F0 contract text quantifies over (s,delta); schema D0 adds the smooth branch",
            "detail": ("F0 classes.AF-SCC-C0-VAC-GEN.conclusion.text says 'For every admissible (s,delta)'; the "
                       "schema's D0 is a tagged disjoint union r = smooth or (sobolev,s,delta). Scope phrasing "
                       "mismatch, same pattern in F1/F2a; owner to confirm the smooth branch is intended."),
            "evidence": [EXPECT["f0_path"], EXPECT["schema_path"]],
        })
    ko = (d.get("conclusion") or {}).get("known_obstruction", "")
    if re.search(r"^\s*citation_status:", ko, flags=re.MULTILINE):
        out.append({
            "id": "A4", "severity": "info",
            "title": "embedded YAML fragment inside conclusion.known_obstruction string",
            "detail": "the string contains a line 'citation_status: ...' rather than a structured field.",
            "evidence": [EXPECT["schema_path"]],
        })
    try:
        rev = int(d.get("revision"))
        hist = d.get("revision_history") or []
        gap = rev - len(hist)
        if gap > 0:
            sib = yaml.safe_load(open(os.path.join(repo, EXPECT["sibling_path"])))
            sib_gap = int(sib.get("revision")) - len(sib.get("revision_history") or [])
            out.append({
                "id": "A5", "severity": "minor",
                "title": f"revision_history collapses {gap} revision(s) into history entries",
                "detail": (f"revision={rev} but len(revision_history)={len(hist)}; the same gap ({sib_gap}) is "
                           "present in the F2a sibling and was introduced by the documented rev12 "
                           "'duplicate revised_at keys collapsed into revision_history' repair. Confirm the "
                           "collapse is intended and that no revision delta is unrecorded."),
                "evidence": [EXPECT["schema_path"], EXPECT["sibling_path"]],
            })
    except Exception:  # noqa: BLE001
        pass
    return out


HARD = [("H1", h1_structure), ("H2", h2_identity), ("H3", h3_containment_direction),
        ("H3b", h3b_containment_denial),
        ("H4", h4_f0_binding), ("H5", h5_pointers), ("H6", h6_quantifiers),
        ("H7", h7_vocabulary), ("H8", h8_mirror), ("H9", h9_sibling), ("H10", h10_review_status)]


def run_suite(parsed, raw, ctx):
    checks = {}
    for cid, fn in HARD:
        try:
            res = fn(parsed, raw, ctx)
        except Exception as exc:  # fail closed
            res = {"title": fn.__name__, "verdict": "error", "findings": [f"internal error: {exc!r}"]}
        checks[cid] = res
    try:
        adv = advisories(parsed, raw, ctx)
    except Exception as exc:  # noqa: BLE001
        adv = [{"id": "A0", "severity": "info", "title": "advisory sweep error",
                "detail": repr(exc), "evidence": []}]
    hard = [cid for cid, r in checks.items() if r["verdict"] in ("fail", "error")]
    errors = [cid for cid, r in checks.items() if r["verdict"] == "error"]
    if errors:
        verdict, score = "inconclusive", 2.0
    elif hard:
        verdict = "revise"
        score = {1: 3.5, 2: 3.0}.get(len(hard), 2.5)
    else:
        verdict, score = "accept", 4.5
    return {"checks": checks, "advisories": adv, "hard_failures": hard, "errors": errors,
            "verdict": verdict, "score": score}


def digest_of(result):
    return hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()


# --------------------------------------------------------------------------- controls

def controls(parsed, raw, ctx):
    out = {}
    K = {}

    # K1 repair-responsiveness of H3
    m = copy.deepcopy(parsed)
    for row in m["implication_ledger"]["forbidden_transfers"]:
        if "strictly larger extension class" in row.get("reason", ""):
            row["reason"] = row["reason"].replace("strictly larger extension class",
                                                  "strictly smaller extension class")
    r = run_suite(m, raw, ctx)
    K["K1_H3_repaired"] = {"expect": "H3 pass", "got": r["checks"]["H3"]["verdict"],
                           "pass": r["checks"]["H3"]["verdict"] == "pass"}
    r0 = run_suite(parsed, raw, ctx)
    K["K1b_H3_baseline"] = {"expect": "H3 fail", "got": r0["checks"]["H3"]["verdict"],
                            "pass": r0["checks"]["H3"]["verdict"] == "fail"}

    # K2 declared F0 hash zeroed
    m = copy.deepcopy(parsed)
    m["f0_binding"]["declared_f0_sha256"] = "0" * 64
    r = run_suite(m, raw, ctx)
    K["K2_H4_zeroed_hash"] = {"expect": "H4 fail", "got": r["checks"]["H4"]["verdict"],
                              "pass": r["checks"]["H4"]["verdict"] == "fail"}

    # K3 unknown vocabulary token
    m = copy.deepcopy(parsed)
    m["conclusion"]["conclusion_type"] = "bogus_token"
    r = run_suite(m, raw, ctx)
    K["K3_H7_unknown_token"] = {"expect": "H7 fail", "got": r["checks"]["H7"]["verdict"],
                                "pass": r["checks"]["H7"]["verdict"] == "fail"}

    # K4 deleted required key
    m = copy.deepcopy(parsed)
    del m["visibility"]
    r = run_suite(m, raw, ctx)
    K["K4_H1_missing_key"] = {"expect": "H1 fail", "got": r["checks"]["H1"]["verdict"],
                              "pass": r["checks"]["H1"]["verdict"] == "fail"}

    # K5 duplicate-key detector
    raw_dup = raw + "\nrevision: 999\n"
    r = run_suite(yaml.safe_load(raw_dup), raw_dup, ctx)
    K["K5_H1_duplicate_key"] = {"expect": "H1 fail", "got": r["checks"]["H1"]["verdict"],
                                "pass": r["checks"]["H1"]["verdict"] == "fail"}

    # K6 mirror divergence (in-memory)
    ctx2 = copy.deepcopy(ctx)
    ctx2["live"][EXPECT["mirror_path"]] = "f" * 64
    r = run_suite(parsed, raw, ctx2)
    K["K6_H8_diverged_mirror"] = {"expect": "H8 fail", "got": r["checks"]["H8"]["verdict"],
                                  "pass": r["checks"]["H8"]["verdict"] == "fail"}

    # K7 determinism
    d1 = digest_of(run_suite(parsed, raw, ctx))
    d2 = digest_of(run_suite(parsed, raw, ctx))
    K["K7_determinism"] = {"expect": "identical digests", "digest": d1,
                           "pass": d1 == d2}

    # K8 fail-closed on empty document
    r = run_suite({}, "{}", ctx)
    K["K8_empty_doc"] = {"expect": "not accept and no raise", "verdict": r["verdict"],
                         "pass": r["verdict"] in ("revise", "inconclusive")}

    # K9 live containment-denial detection (added in erratum round 2)
    m = copy.deepcopy(parsed)
    m["regularity"]["must_not_conflate"][0] = (
        m["regularity"]["must_not_conflate"][0]
        + " [R2 major: the earlier 'no containment with C2' was wrong]")
    r = run_suite(m, raw, ctx)
    K["K9_H3b_repair_marker"] = {"expect": "H3b pass", "got": r["checks"]["H3b"]["verdict"],
                                 "pass": r["checks"]["H3b"]["verdict"] == "pass"}
    r0 = run_suite(parsed, raw, ctx)
    K["K9b_H3b_baseline"] = {"expect": "H3b fail", "got": r0["checks"]["H3b"]["verdict"],
                             "pass": r0["checks"]["H3b"]["verdict"] == "fail"}

    out["controls"] = K
    out["pass"] = all(v["pass"] for v in K.values())
    return out


def main():
    repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
    schema_full = os.path.join(repo, EXPECT["schema_path"])
    raw = open(schema_full).read()
    parsed = yaml.safe_load(raw)

    pin_paths = [EXPECT["schema_path"], EXPECT["mirror_path"], EXPECT["sibling_path"],
                 EXPECT["f0_path"], EXPECT["supplement_path"], EXPECT["frozen_path"],
                 EXPECT["alias_path"], EXPECT["evidence_path"], EXPECT["variant_registry_path"]]
    live = {}
    pins = {}
    drift = []
    for p in pin_paths:
        full = os.path.join(repo, p)
        if not os.path.exists(full):
            drift.append(p)
            continue
        live[p] = sha256_file(full)
    # verify the pinned snapshot copies match live bytes
    snapshot_map = {
        "af_scc_c0_vacuum.canonical.yaml": EXPECT["schema_path"],
        "af_scc_c0_vacuum.mirror.yaml": EXPECT["mirror_path"],
        "af_scc_c2_vacuum.canonical.yaml": EXPECT["sibling_path"],
        "formulation_taxonomy.canonical.yaml": EXPECT["f0_path"],
        "formulation_taxonomy.supplement.yaml": EXPECT["supplement_path"],
        "FROZEN.json": EXPECT["frozen_path"],
        "VOCAB_ALIASES.json": EXPECT["alias_path"],
        "taxonomy_consistency.json": EXPECT["evidence_path"],
        "VARIANT_REGISTRY.json": EXPECT["variant_registry_path"],
    }
    for snap, src in snapshot_map.items():
        sp = os.path.join(PINS, snap)
        pins[src] = {"live_sha256": live.get(src),
                     "pinned_sha256": sha256_file(sp) if os.path.exists(sp) else None,
                     "bytes": os.path.getsize(os.path.join(repo, src)) if src in live else None}
        pins[src]["matches"] = pins[src]["live_sha256"] == pins[src]["pinned_sha256"]
        if not pins[src]["matches"]:
            drift.append(src)

    ctx = {"repo": repo, "live": live}
    result = run_suite(parsed, raw, ctx)
    ctl = controls(parsed, raw, ctx)

    report = {
        "task_id": "W097-F2B-REV13-INDEP-REVIEW-01",
        "instrument": "check_f2b_rev13.py",
        "class_id": EXPECT["class_id"],
        "node_id": EXPECT["node_id"],
        "gate": EXPECT["gate"],
        "schema_revision": parsed.get("revision"),
        "pins": pins,
        "pin_drift": drift,
        "checks": result["checks"],
        "advisories": result["advisories"],
        "hard_failures": result["hard_failures"],
        "controls": ctl["controls"],
        "controls_pass": ctl["pass"],
        "verdict": "inconclusive" if drift else result["verdict"],
        "score": 2.0 if drift else result["score"],
        "result_digest": digest_of(result),
        "limits": [
            "mechanical class-contract conformance only; no mathematical or physical correctness is decided",
            "no citation-scope or primary-source verification (L1 owns that)",
            "reviewer is not an author of the schema, the taxonomy, the supplement, VARIANT_REGISTRY, FROZEN.json or the rev13 repair",
            "instrument written from scratch; imports no other checker; read-only outside this artifact directory",
            "worker verdict: does not set node status, validation_status=passed, or any gate verdict",
        ],
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
    }
    with open(os.path.join(ART, "report.json"), "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"verdict": report["verdict"], "score": report["score"],
                      "hard_failures": report["hard_failures"],
                      "controls_pass": report["controls_pass"],
                      "pin_drift": drift,
                      "result_digest": report["result_digest"]}, indent=1))
    return 0 if not drift else 3


if __name__ == "__main__":
    sys.exit(main())
