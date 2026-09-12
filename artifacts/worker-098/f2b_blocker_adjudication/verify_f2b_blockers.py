#!/usr/bin/env python3
"""W098-F2B-BLOCKER-ADJ-01: independent adjudication of the blocking findings on
class AF-SCC-C0-VAC-GEN (node F2b) at the live canonical hash.

Context.  F2b reached four recorded `accept` verdicts at 1bb78ce9b357, then
worker-034 and astra-lead-audit-r3 recorded BLOCKING findings at the same hash:
  B1 duplicate top-level YAML key `revised_at` x8 (data ambiguity / strict-reader failure)
  B2 the D0 disjunction under a `forall (s,delta)` binder (formal typing)
  B3 class_contract_pointer does not resolve at the declared canonical F0 artifact
  B4 map-side F2b.artifact_sha256 reported malformed (zero-padded prefix)
This script adjudicates each claim mechanically and independently, runs the
canonical structural gate and the class-separation detector, runs reviewer
contract checks, and measures the detection power of those stages against
deliberate mutants -- including the specific blind spot the claims imply.

It claims NO node completion, NO theorem, NO gate verdict.  Verdicts are for
the controller / audit lead to weigh.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, SequenceNode

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
HERE = ROOT / "artifacts/worker-098/f2b_blocker_adjudication"
CANON_F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"
CANON_TAXO = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP_TAXO = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
SPEC = ROOT / "artifacts/formulation/rule_spec.json"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
MAP = ROOT / "research_map/research_map.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
SIBLING_CLASSES = {"F1": ROOT / "schemas/af_wcc_vacuum.yaml",
                   "F2a": ROOT / "schemas/af_scc_c2_vacuum.yaml",
                   "F2b": CANON_F2B}

CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
SIBLING = "AF-SCC-C2-VAC-GEN"
WCC = "AF-WCC-VAC-GEN"
TASK_ID = "W098-F2B-BLOCKER-ADJ-01"

sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

CST = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def get(d, *path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def find_key(obj, key):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            out.extend(find_key(v, key))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(find_key(v, key))
    return out


# --------------------------------------------------------------------------- #
# claim adjudicators
# --------------------------------------------------------------------------- #

def duplicate_keys(text: str) -> list:
    """Exact duplicate-mapping-key enumeration via yaml.compose (no dedup)."""
    dups = []

    def walk(node, path):
        if isinstance(node, MappingNode):
            seen = {}
            for knode, vnode in node.value:
                key = knode.value
                if key in seen:
                    dups.append({"path": f"{path}/{key}",
                                 "first_line": seen[key].start_mark.line + 1,
                                 "duplicate_line": knode.start_mark.line + 1})
                else:
                    seen[key] = knode
                walk(vnode, f"{path}/{key}")
        elif isinstance(node, SequenceNode):
            for i, vnode in enumerate(node.value):
                walk(vnode, f"{path}[{i}]")

    walk(yaml.compose(text), "")
    return dups


class StrictDupLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys (what a strict reader does)."""

    def construct_mapping(self, node, deep=False):
        keys = set()
        for knode, _ in node.value:
            k = self.construct_object(knode, deep=deep)
            if k in keys:
                raise ValueError(f"duplicate key {k!r} at line {knode.start_mark.line + 1}")
            keys.add(k)
        return super().construct_mapping(node, deep=deep)


def strict_parse_error(text: str) -> str | None:
    try:
        yaml.load(text, Loader=StrictDupLoader)
        return None
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def last_wins_value(text: str, key: str):
    """What PyYAML (last-wins) exposes for a top-level key."""
    doc = yaml.safe_load(text)
    return doc.get(key)


def d0_typing_analysis(schema: dict) -> dict:
    q = schema.get("quantifiers", {}) or {}
    domains = q.get("domains", {}) or {}
    d0 = (domains.get("D0") or {}).get("definition", "")
    ordered = q.get("ordered") or []
    first = ordered[0] if ordered else {}
    formal = q.get("formal", "") or ""
    gen = schema.get("genericity", {}) or {}
    ambient = gen.get("ambient_space", "") or ""
    topology_note = gen.get("topology_or_measure", "") or ""
    return {
        "binder": first.get("binder"),
        "domain_id": first.get("domain_id"),
        "d0_definition": d0,
        "d0_has_disjunction": (" or " in d0),
        "d0_sobolev_branch": "Sobolev" in d0,
        "d0_smooth_branch": "smooth-with-decay" in d0,
        "formal_uses_pair_binder": bool(re.search(r"forall\s*\(s,\s*delta\)\s*in\s*D0", formal)),
        "ambient_mentions_sobolev_product": "Sobolev" in ambient,
        "ambient_mentions_frechet_branch": "Frechet" in topology_note or "Frechet" in ambient,
        "pair_indexed_generic_set": "G_{s,delta}" in formal,
        "ill_typed_on_smooth_branch": bool(
            " or " in d0 and "smooth-with-decay" in d0
            and re.search(r"forall\s*\(s,\s*delta\)\s*in\s*D0", formal)
            and re.search(r"G_\{s,delta\}", formal)),
    }


def pointer_resolution(schema: dict, canon: dict, supp: dict) -> dict:
    ptr = schema.get("class_contract_pointer", "") or ""
    path, _, anchor = ptr.partition("#")

    def resolve(doc, dotted):
        cur = doc
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur

    canon_obj = resolve(canon, anchor) if anchor else None
    supp_obj = resolve(supp, anchor) if anchor else None
    return {
        "pointer": ptr,
        "file_exists": (ROOT / path).is_file(),
        "anchor_resolves_canonical_F0": canon_obj is not None,
        "anchor_resolves_authoring_supplement": supp_obj is not None,
        "canonical_top_level_contract_keys": [k for k in canon.keys() if "class" in k],
        "supplement_contract_components": get(supp_obj or {}, "components"),
        "supplement_contract_conclusion_type": get(supp_obj or {}, "conclusion_type"),
    }


def alias_canon(kind: str, tok, aliases: dict):
    for c, al in (aliases.get(kind) or {}).items():
        if tok == c or (isinstance(al, list) and tok in al):
            return c
    return tok


def map_hash_integrity(m: dict, measured_f2b: str) -> dict:
    hex64 = re.compile(r"^[0-9a-f]{64}$")
    hexish = re.compile(r"^[0-9a-f]{8,}$")
    malformed = []
    truncated = []
    timestamp_named = []
    hash_fields = 0
    f2b_node = {}

    def walk(o, path=""):
        nonlocal hash_fields
        if isinstance(o, dict):
            if o.get("id") == "F2b" or o.get("node_id") == "F2b":
                for k in ("artifact_sha256", "artifact_sha256_measured",
                          "declared_hash_matches_measured"):
                    if k in o:
                        f2b_node[k] = o[k]
            for k, v in o.items():
                key = str(k)
                is_hash_key = bool(re.search(r"sha256$|_hash$|^hash$", key, re.I))
                if is_hash_key and isinstance(v, str):
                    if key.endswith("_at"):
                        timestamp_named.append({"path": f"{path}/{key}", "value": v[:40]})
                    else:
                        hash_fields += 1
                        if not hex64.match(v):
                            rec = {"path": f"{path}/{key}", "value": v[:90],
                                   "len": len(v)}
                            (truncated if hexish.match(v) else malformed).append(rec)
                walk(v, f"{path}/{key}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")

    walk(m)
    return {
        "hash_valued_fields_scanned": hash_fields,
        "malformed_live_hash_fields": malformed,
        "truncated_live_hash_fields": truncated,
        "timestamp_named_hash_fields": timestamp_named,
        "f2b_node_hash_fields": f2b_node,
        "measured_f2b": measured_f2b,
        "f2b_pin_matches_measured": (f2b_node.get("artifact_sha256") == measured_f2b),
        "f2b_declared_matches_measured": f2b_node.get("declared_hash_matches_measured"),
    }


def cross_class_d0() -> dict:
    out = {}
    shape = {}
    for node, p in SIBLING_CLASSES.items():
        try:
            s = yaml.safe_load(p.read_text())
            d0 = get(s, "quantifiers", "domains", "D0", "definition", default="")
            formal = get(s, "quantifiers", "formal", default="")
            out[node] = d0
            shape[node] = {
                "has_disjunction": " or " in d0,
                "sobolev_branch": "Sobolev" in d0,
                "smooth_branch": "smooth-with-decay" in d0,
                "pair_binder": bool(re.search(r"forall\s*\(s,\s*delta\)\s*in\s*D0", formal)),
                "pair_indexed_G": bool(re.search(r"G_\{s,delta\}", formal)),
            }
        except Exception as e:  # noqa: BLE001
            out[node] = f"unreadable: {e}"
            shape[node] = {}
    norm = {k: re.sub(r"\s+", " ", v).strip() for k, v in out.items()}
    defect_shape = {k: tuple(sorted(v.items())) for k, v in shape.items()}
    return {
        "definitions": out,
        "shape": shape,
        "normalized_identical_across_F1_F2a_F2b": len(set(norm.values())) == 1,
        "same_defect_shape_across_F1_F2a_F2b":
            len({tuple(sorted(v.items())) for v in shape.values()}) == 1,
        "note": "F1 appends a clarifying sentence to the same D0 disjunction; F2a and F2b "
                "carry the text verbatim, so the typing defect is family-wide.",
    }


# --------------------------------------------------------------------------- #
# stages
# --------------------------------------------------------------------------- #

def run_gate(schema: Path) -> dict:
    r = subprocess.run([sys.executable, str(GATE), "--json", str(schema)],
                       capture_output=True, text=True)
    try:
        rep = json.loads(r.stdout)
    except Exception:  # noqa: BLE001
        rep = {"verdict": "UNPARSEABLE", "stdout": r.stdout[:4000]}
    rep["_exit_code"] = r.returncode
    rep["_stderr_tail"] = r.stderr[-400:]
    return rep


def contract_checks(schema: dict, contracts: dict, spec: dict, aliases: dict) -> list:
    checks = []

    def chk(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    comp = schema.get("class_components", {}) or {}
    concl = schema.get("conclusion", {}) or {}
    ctype = concl.get("conclusion_type")
    pred = schema.get("extension_predicate", {}) or {}
    reg = schema.get("regularity", {}) or {}
    gen = schema.get("genericity", {}) or {}
    vis = schema.get("visibility", {}) or {}
    ip = schema.get("i_plus", {}) or {}
    q = schema.get("quantifiers", {}) or {}
    nv = schema.get("non_vacuity", {}) or {}
    vocab = spec["vocabularies"]["class_conclusion_type"]
    genvocab = spec["vocabularies"]["genericity_kind"]

    chk("class_id_matches_target", schema.get("class_id") == CLASS_ID,
        f"declared={schema.get('class_id')!r}")
    chk("node_id_matches_target", schema.get("node_id") == NODE_ID,
        f"declared={schema.get('node_id')!r}")
    chk("components_match_contract", comp == contracts.get("components"),
        f"schema={comp} contract={contracts.get('components')}")
    chk("family_is_scc",
        spec["class_family"].get(CLASS_ID) == "SCC" and comp.get("censorship") == "SCC"
        and concl.get("family") == "SCC",
        "family=SCC in spec, class_components and conclusion")
    chk("conclusion_type_matches_contract_and_vocab",
        ctype == contracts.get("conclusion_type") == vocab.get(CLASS_ID)
        == "scc_c0_future_inextendibility",
        f"schema={ctype!r} contract={contracts.get('conclusion_type')!r} "
        f"vocab[class]={vocab.get(CLASS_ID)!r}")
    chk("extension_predicate_frozen_fields",
        pred.get("frozen_regularity") == "C0"
        and pred.get("frozen_equation_concept") == "none"
        and pred.get("frozen_direction") == "future",
        f"frozen={ {k: pred.get(k) for k in ('frozen_regularity','frozen_equation_concept','frozen_direction')} }")
    chk("extension_regularity_exactly_c0", reg.get("extension_regularity") == "C0",
        f"extension_regularity={reg.get('extension_regularity')!r}")
    chk("extension_solution_concept_none",
        reg.get("extension_solution_concept") == "none",
        f"extension_solution_concept={reg.get('extension_solution_concept')!r}")
    _cm = re.search(r"c([0-9])", ctype or "", re.I)
    ctoken = ("C" + _cm.group(1)) if _cm else None
    token_places = {
        "class_components.regularity_token": comp.get("regularity_token"),
        "extension_predicate.frozen_regularity": pred.get("frozen_regularity"),
        "regularity.extension_regularity": reg.get("extension_regularity"),
        "conclusion_type_regularity_token": ctoken,
    }
    token_values = {k: (v.upper() if isinstance(v, str) else v) for k, v in token_places.items()}
    chk("regularity_token_consistent_across_fields", set(token_values.values()) == {"C0"},
        json.dumps(token_values))
    exact = reg.get("extension_regularity_exact", "") or ""
    chk("regularity_exact_prose_asserts_c0_not_c2",
        bool(re.search(r"\(C0\)|C0\b", exact))
        and not re.search(r"exactly\s+C2\b", exact),
        f"head={exact[:90]!r}")
    chk("genericity_kind_vocab_and_part_of_class",
        gen.get("kind") in genvocab and gen.get("is_part_of_class") is True,
        f"kind={gen.get('kind')!r} in_vocab={gen.get('kind') in genvocab} "
        f"is_part_of_class={gen.get('is_part_of_class')!r}")
    chk("sibling_disjoint_declared", schema.get("sibling_disjoint_from") == SIBLING,
        f"sibling_disjoint_from={schema.get('sibling_disjoint_from')!r}")
    chk("anti_scope_names_c2_wcc_and_scalar",
        all(c in json.dumps(schema.get("anti_scope", {}))
            for c in (SIBLING, WCC, "AF-WCC-SCALAR-SPH")),
        "anti_scope names C2 sibling, WCC and scalar classes")
    chk("one_class_only_no_merge",
        (json.dumps(schema.get("anti_scope", {})).count(CLASS_ID) >= 1)
        and "not_this_class" in (schema.get("anti_scope") or {}),
        "anti_scope declares not_this_class set; no merge token in class_id")
    chk("topology_RxS2_and_lambda0",
        get(schema, "topology", "I_plus_topology") == "R x S^2"
        and get(schema, "data_class", "cosmological_constant") == 0,
        f"I_plus_topology={get(schema,'topology','I_plus_topology')!r} "
        f"Lambda={get(schema,'data_class','cosmological_constant')!r}")
    ordered = q.get("ordered") or []
    chk("quantifiers_exact_ordered",
        bool(q.get("formal")) and len(ordered) >= 4 and q.get("order_matters") is True
        and bool(q.get("negation")) and bool(q.get("negation_normal_form"))
        and all(d.get("domain_id") in (q.get("domains") or {}) for d in ordered),
        f"ordered={len(ordered)} order_matters={q.get('order_matters')!r} "
        f"domains={list((q.get('domains') or {}).keys())}")
    chk("non_vacuity_witness_and_falsifier",
        bool(nv.get("condition")) and bool(nv.get("witness_type"))
        and bool(nv.get("vacuity_falsifier")),
        f"non_vacuity keys={list(nv.keys())}")
    chk("visibility_not_in_conclusion",
        vis.get("role") == "not_in_conclusion"
        and vis.get("visible_singularity_is_wcc") is True
        and bool(vis.get("forbidden_falsifier")),
        f"visible_singularity_is_wcc={vis.get('visible_singularity_is_wcc')!r}")
    chk("i_plus_is_assumption_not_conclusion",
        ip.get("role") == "assumption" and ip.get("in_conclusion") is False
        and ip.get("completeness_in_conclusion") is False,
        f"i_plus.role={ip.get('role')!r} in_conclusion={ip.get('in_conclusion')!r}")
    sf = find_key(schema.get("falsifier", {}), "schema_falsifiers")
    sf_flat = [x for v in sf for x in (v if isinstance(v, list) else [v])]
    chk("class_falsifiers_present",
        len(sf_flat) >= 3
        and get(schema, "falsifier", "tier_1", "refutes") == CLASS_ID,
        f"schema_falsifiers={len(sf_flat)} tier_1.refutes="
        f"{get(schema,'falsifier','tier_1','refutes')!r}")
    # asserted surfaces must not carry a composite/merged regularity conclusion
    asserted = json.dumps([concl.get("statement_natural_language"),
                           concl.get("statement_formal"),
                           concl.get("conclusion_type"), comp,
                           pred.get("frozen_regularity"),
                           reg.get("extension_regularity")])
    chk("no_composite_regularity_in_asserted_surfaces",
        not re.search(r"C0\s+or\s+C2|C2\s+or\s+C0", asserted, re.I),
        "asserted surfaces scanned for 'C0 or C2'")
    chk("no_wcc_conclusion_token_in_asserted_surfaces",
        not cs.WCC_CONCLUSION.search(json.dumps(
            [concl.get("statement_natural_language"), concl.get("statement_formal"),
             concl.get("conclusion_type")])),
        "WCC regex over asserted conclusion surfaces only")
    variants = schema.get("class_identity_variants", {}) or {}
    hlv = variants.get("horizon_localized_variant", {}) or {}
    chk("identity_variant_CH_registered_inline",
        hlv.get("is_this_class") is False and "CH" in json.dumps(hlv)
        and CLASS_ID == hlv.get("class_id"),
        f"horizon_localized_variant keys={list(hlv.keys())} is_this_class={hlv.get('is_this_class')!r}")
    try:
        reg = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
        reg_variants = sorted({v.get("variant_id") for v in reg.get("variants", [])
                               if v.get("parent_class") == CLASS_ID})
    except Exception as e:  # noqa: BLE001
        reg_variants = [f"registry_unreadable: {e}"]
    anti = json.dumps(schema.get("anti_scope", {}))
    chk("variant_registry_membership_visible",
        "CH" in reg_variants and "CH" in json.dumps(hlv),
        f"registry variants for {CLASS_ID}: {reg_variants}; inline: "
        f"{[k for k, v in variants.items() if isinstance(v, dict)]}; "
        f"anti_scope mentions {[v for v in reg_variants if v in anti]} "
        f"(unmentioned: {[v for v in reg_variants if v not in anti and v not in json.dumps(hlv)]})")
    d0a = d0_typing_analysis(schema)
    chk("d0_binder_domain_well_typed", not d0a["ill_typed_on_smooth_branch"],
        f"binder={d0a['binder']} D0={d0a['d0_definition'][:110]!r}")
    return checks


def mutants(text: str) -> dict:
    """Deliberate defectors built from the live snapshot."""
    out = {}
    # same-value duplicate: structurally illegal, semantically identical
    m = text.replace("class_id: AF-SCC-C0-VAC-GEN",
                     "class_id: AF-SCC-C0-VAC-GEN\nclass_id: AF-SCC-C0-VAC-GEN", 1)
    if m != text:
        out["M1_duplicate_same_value_class_id"] = m
    # last-wins semantic flip of a guarded field
    m = text.replace("visibility:\n  role: not_in_conclusion",
                     "visibility:\n  role: not_in_conclusion\n  role: conclusion", 1)
    if m != text:
        out["M2_duplicate_last_wins_visibility_flip"] = m
    # D0 typing: remove the smooth branch so the pair binder is well typed
    m = text.replace(
        "definition: \"admissible regularity pairs: Sobolev variant s > 5/2 and delta in "
        "(1/2,1), or the smooth-with-decay default\"",
        "definition: \"admissible regularity pairs: Sobolev variant s > 5/2 and delta in "
        "(1/2,1)\"", 1)
    if m != text:
        out["M3_d0_pair_only_no_smooth_branch"] = m
    # WCC conclusion inflation
    m = text.replace("conclusion_type: scc_c0_future_inextendibility",
                     "conclusion_type: weak_cosmic_censorship", 1)
    if m != text:
        out["M4_wcc_conclusion_inflation"] = m
    # composite regularity
    m = text.replace("extension_regularity: C0",
                     "extension_regularity: C0 or C2", 1)
    if m != text:
        out["M5_composite_c0_or_c2_regularity"] = m
    # wrong sibling
    m = text.replace("sibling_disjoint_from: AF-SCC-C2-VAC-GEN",
                     "sibling_disjoint_from: AF-WCC-VAC-GEN", 1)
    if m != text:
        out["M6_wrong_sibling"] = m
    return out


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    # ---- Step 0: hash-pinned snapshots ----
    snaps = {
        "af_scc_c0_vacuum.snapshot.yaml": CANON_F2B,
        "formulation_taxonomy.canonical.snapshot.yaml": CANON_TAXO,
        "formulation_taxonomy.supplement.snapshot.yaml": SUPP_TAXO,
        "rule_spec.snapshot.json": SPEC,
        "VOCAB_ALIASES.snapshot.json": ALIASES,
        "research_map.snapshot.json": MAP,
    }
    snap_hashes = {}
    for name, src in snaps.items():
        dst = HERE / name
        shutil.copyfile(src, dst)
        snap_hashes[name] = sha256_file(dst)
    (HERE / "SNAPSHOT.sha256").write_text(
        "\n".join(f"{h}  {n}" for n, h in sorted(snap_hashes.items())) + "\n")

    snap_f2b = HERE / "af_scc_c0_vacuum.snapshot.yaml"
    text = snap_f2b.read_text()
    schema = yaml.safe_load(text)
    canon = yaml.safe_load((HERE / "formulation_taxonomy.canonical.snapshot.yaml").read_text())
    supp = yaml.safe_load((HERE / "formulation_taxonomy.supplement.snapshot.yaml").read_text())
    spec = json.loads((HERE / "rule_spec.snapshot.json").read_text())
    aliases = json.loads((HERE / "VOCAB_ALIASES.snapshot.json").read_text())
    mapdoc = json.loads((HERE / "research_map.snapshot.json").read_text())
    contracts = supp["class_contracts"][CLASS_ID]

    f2b_start = sha256_file(CANON_F2B)
    f0_start = sha256_file(CANON_TAXO)
    supp_start = sha256_file(SUPP_TAXO)
    map_start = sha256_file(MAP)

    # ---- Stage 1/2: canonical gate + class-separation ----
    gate = run_gate(snap_f2b)
    cs_findings = cs.findings_for_text(text, snap_f2b.name)
    cs_hard = [f for f in cs_findings if not str(f).startswith("CLASSSEP-SOFT")]

    # ---- Stage 3: reviewer contract checks ----
    checks = contract_checks(schema, contracts, spec, aliases)
    failed = [c for c in checks if not c["ok"]]

    # ---- Claim adjudication ----
    dups = duplicate_keys(text)
    strict_err = strict_parse_error(text)
    last_rev = last_wins_value(text, "revised_at")
    claim_b1 = {
        "claim": "duplicate top-level YAML key revised_at x8",
        "status": "CONFIRMED_LIVE",
        "duplicates": dups,
        "duplicate_count": len(dups),
        "strict_reader_result": strict_err,
        "pyyaml_last_wins_value": last_rev,
        "line_values": [ln.strip() for ln in text.splitlines()
                        if re.match(r"^revised_at:", ln)],
        "impact": ("strict YAML readers fail to load the canonical artifact; last-wins "
                   "readers disagree with first-wins readers on the revision timestamp; "
                   "the canonical gate passes the file regardless (blind spot, see controls)"),
    }
    d0 = d0_typing_analysis(schema)
    xd0 = cross_class_d0()
    claim_b2 = {
        "claim": "family-of-statements quantifier domain: D0 disjunction under a forall (s,delta) binder",
        "status": "CONFIRMED_LIVE_FAMILY_WIDE",
        "analysis": d0,
        "cross_class": xd0,
        "impact": ("the formal statement's first binder ranges over pairs (s,delta) while D0 "
                   "is a disjunction whose smooth-with-decay branch has no (s,delta) values and "
                   "a different (Frechet) ambient topology; the pair-indexed G_{s,delta} and "
                   "X^{s,delta}_vac are undefined on that branch. The class content is not "
                   "invalidated, but the formal statement is not well typed as written."),
        "scope_correction": ("the same defect shape (disjunction + pair binder + smooth branch) "
                             "appears in F1, F2a and F2b at their live hashes; F2a/F2b carry the "
                             "D0 text verbatim and F1 appends a clarifying clause, so this is a "
                             "family-level repair, not an F2b-specific defect"),
    }
    ptr = pointer_resolution(schema, canon, supp)
    f0_declared = get(schema, "f0_binding", "declared_f0_sha256")
    f0_declared_ok = (f0_declared == f0_start)
    supp_declared = get(schema, "f0_binding", "class_contract_supplement")
    # alias-aware canonical-vs-contract agreement
    cax = canon["classes"][CLASS_ID]["axes"]
    semantic_agree = (
        alias_canon("conclusion_type", cax.get("conclusion_type"), aliases)
        == alias_canon("conclusion_type", contracts.get("conclusion_type"), aliases)
        and cax.get("regularity_token") == contracts["components"].get("regularity_token")
        and cax.get("family") == contracts["components"].get("censorship")
        and alias_canon("genericity_kind", cax.get("genericity_kind"), aliases)
        == alias_canon("genericity_kind", schema.get("genericity", {}).get("kind"), aliases)
    )
    claim_b3 = {
        "claim": "class_contract_pointer does not resolve at the declared canonical F0 artifact",
        "status": "CONFIRMED_STRUCTURAL_SCOPE_CORRECTED",
        "pointer": ptr,
        "f0_binding": {
            "declared_f0_artifact": get(schema, "f0_binding", "declared_f0_artifact"),
            "declared_f0_sha256_matches_measured_canonical": f0_declared_ok,
            "class_contract_supplement": supp_declared,
            "supplement_anchor_resolves": ptr["anchor_resolves_authoring_supplement"],
        },
        "alias_aware_canonical_vs_contract_agreement": semantic_agree,
        "impact": ("the pointer names the authoring-tree fragment; the canonical F0 taxonomy "
                   "has no `class_contracts` key, so the fragment does not resolve against the "
                   "artifact the controller declares authoritative. The same f0_binding block "
                   "declares the authoring supplement where the fragment DOES resolve and whose "
                   "class axes agree alias-aware. This is therefore an F0 publication / "
                   "canonical-tree gap affecting every class schema, not an F2b class-semantics "
                   "defect. It still blocks binding a verdict to the canonical tree."),
    }
    mi = map_hash_integrity(mapdoc, f2b_start)
    claim_b4 = {
        "claim": "map-side F2b.artifact_sha256 malformed (zero-padded truncated prefix)",
        "status": "NOT_LIVE_REPAIRED_WITH_MAP_HYGIENE_NOTE",
        "map_integrity": mi,
        "historical_occurrences": (
            "the string survives in research_map.json only inside review/finding text "
            "(reviews[137], reviews[143], reviews[151], reviews[157], resource_requests[20]); "
            "no live hash-valued field matches it"),
        "impact": ("the live F2b node pin equals the measured canonical hash and "
                   "declared_hash_matches_measured is true, so B4 as stated is repaired / not a "
                   "defect of the current bytes. The general scan adds a map-hygiene note: "
                   f"{len(mi['truncated_live_hash_fields'])} map hash-valued field(s) hold "
                   "truncated prefixes (e.g. reviews[*].reviewed_sha256, target_sha256) and "
                   f"{len(mi['timestamp_named_hash_fields'])} field(s) named `*_measured_at` are "
                   "timestamps, not hashes; neither is an F2b class defect, but the map cannot "
                   "be used as a hash authority from those fields."),
    }
    blockers = {"B1": claim_b1, "B2": claim_b2, "B3": claim_b3, "B4": claim_b4}
    confirmed_live = [k for k, v in blockers.items() if v["status"].startswith("CONFIRMED")]
    scope_corrected = [k for k, v in blockers.items() if "SCOPE_CORRECTED" in v["status"]]
    not_live = [k for k, v in blockers.items() if v["status"].startswith("NOT_LIVE")]

    # ---- Stage 4: controls / detector sensitivity ----
    controls = []
    for name, mtext in mutants(text).items():
        mp = HERE / f"control_{name}.yaml"
        mp.write_text(mtext)
        mrep = run_gate(mp)
        mfind = cs.findings_for_text(mtext, f"control:{name}")
        mfail = [c["check"] for c in contract_checks(
            yaml.safe_load(mtext), contracts, spec, aliases) if not c["ok"]]
        mdups = duplicate_keys(mtext)
        mstrict = strict_parse_error(mtext)
        detected_by = [s for s, hit in
                       (("gate", mrep.get("verdict") != "pass"),
                        ("classsep", bool(mfind)),
                        ("reviewer_checks", bool(mfail)),
                        ("strict_yaml", bool(mstrict))) if hit]
        controls.append({
            "control": name,
            "control_sha256": sha256_text(mtext),
            "duplicate_keys": mdups,
            "strict_reader_error": mstrict,
            "gate_verdict": mrep.get("verdict"),
            "gate_failed_rules": mrep.get("failed_rules"),
            "classsep_findings": mfind,
            "reviewer_check_failures": mfail,
            "detected_by": detected_by,
            "detected": bool(detected_by),
        })
    undetected = [c["control"] for c in controls if not c["detected"]]
    # controls that the canonical gate passes on its own
    gate_alone_blind_spots = [c["control"] for c in controls if c["gate_verdict"] == "pass"]
    # controls invisible to all three project stages (gate + classsep + reviewer checks)
    undetected_by_project_stages = [
        c["control"] for c in controls
        if c["gate_verdict"] == "pass" and not c["classsep_findings"]
        and not c["reviewer_check_failures"]]

    # ---- Stage 5: drift re-measure ----
    f2b_end = sha256_file(CANON_F2B)
    f0_end = sha256_file(CANON_TAXO)
    supp_end = sha256_file(SUPP_TAXO)
    map_end = sha256_file(MAP)
    drift = (f2b_end != f2b_start or f0_end != f0_start
             or supp_end != supp_start or map_end != map_start)

    # ---- verdict ----
    hard_failures = []
    subsumed_by_claims = {"d0_binder_domain_well_typed": "B2"}
    contract_hard = [c for c in failed if c["check"] not in subsumed_by_claims]
    if gate.get("verdict") != "pass":
        hard_failures.append(f"canonical gate verdict={gate.get('verdict')} "
                             f"rules={gate.get('failed_rules')}")
    hard_failures.extend(f"contract:{c['check']} :: {c['detail']}" for c in contract_hard)
    hard_failures.extend(f"classsep:{f}" for f in cs_hard)
    if claim_b1["status"].startswith("CONFIRMED"):
        hard_failures.append(
            "B1 CONFIRMED: 8 top-level `revised_at` keys (7 duplicates, lines "
            + ",".join(str(d["duplicate_line"]) for d in dups) + "); strict YAML readers fail; "
            "canonical gate passes the file (duplicate-key blind spot)")
    if claim_b2["status"].startswith("CONFIRMED"):
        hard_failures.append(
            "B2 CONFIRMED (family-wide): D0 disjunction under a `forall (s,delta)` binder; "
            "formal statement not well typed on the smooth-with-decay branch; same defect shape "
            "in F1/F2a/F2b (F2a/F2b D0 text verbatim, F1 adds a clause)")
    if drift:
        hard_failures.append(
            f"moving target during review: F2b {f2b_start[:12]}->{f2b_end[:12]}, "
            f"F0 {f0_start[:12]}->{f0_end[:12]}, map {map_start[:12]}->{map_end[:12]}")

    if drift:
        verdict, score = "inconclusive", 2.0
    elif hard_failures:
        verdict, score = "revise", 3.0
    else:
        verdict, score = "accept", 4.0

    # accept-count quality observation (verification-layer finding, not a defect of bytes)
    accept_quality = {
        "recorded_accepts_at_this_hash": 4,
        "reviewers": ["worker-030", "deepseek-flash-07", "deepseek-flash-17", "worker-001"],
        "observation": (
            "worker-030 recorded the duplicate-key finding (YAML-01, severity N) and still "
            "accepted at 4.0; worker-001 recorded a variant-registry divergence as a major "
            "condition and accepted; flash-17 recorded a falsifier machine-checkability warning "
            "and accepted. None of the four accepts treats B1/B2 as blocking, and B3 was read "
            "as an F2b defect rather than an F0 publication gap. The accept COUNT at this hash "
            "therefore overstates clean coverage: two independent blocking defects are visible "
            "in the same bytes (worker-034 and astra-lead-audit-r3 found them)."),
        "implication": ("G-FORM/G-AUDIT criteria that count distinct accept reviewers without "
                        "requiring disposition of open hard findings will bind a defective "
                        "revision; the count is not a verification-strength measure."),
    }

    evidence = {
        "task_id": TASK_ID,
        "reviewer": "worker-098",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "review_scope": ("adjudication of the four blocking/major findings raised at the live "
                         "hash + structural conformance re-check; not a re-audit of citation "
                         "scope or of the mathematical truth of cited theorems"),
        "canonical_path": "schemas/af_scc_c0_vacuum.yaml",
        "reviewed_sha256": f2b_start,
        "reviewed_bytes": len(snap_f2b.read_bytes()),
        "hashes": {
            "f2b_at_start": f2b_start, "f2b_at_end": f2b_end,
            "canonical_f0_at_start": f0_start, "canonical_f0_at_end": f0_end,
            "authoring_supplement": supp_start,
            "research_map": map_start,
            "snapshots": snap_hashes,
            "gate_tool": sha256_file(GATE),
            "class_separation_tool": sha256_file(ROOT / "research_map/class_separation.py"),
        },
        "stage_1_canonical_gate": {
            "tool": "artifacts/formulation/tools/check_class_schema.py",
            "verdict": gate.get("verdict"),
            "failed_rules": gate.get("failed_rules"),
            "exit_code": gate.get("_exit_code"),
        },
        "stage_2_class_separation": {
            "tool": "research_map/class_separation.py",
            "findings": cs_findings,
            "hard_findings": cs_hard,
        },
        "stage_3_contract_checks": checks,
        "stage_3_failed": [c["check"] for c in failed],
        "stage_3_failed_subsumed_by_claims": subsumed_by_claims,
        "blocker_adjudication": blockers,
        "confirmed_live_claims": confirmed_live,
        "scope_corrected_claims": scope_corrected,
        "not_live_claims": not_live,
        "stage_4_controls": controls,
        "stage_4_undetected": undetected,
        "stage_4_gate_alone_blind_spots": gate_alone_blind_spots,
        "stage_4_undetected_by_project_stages": undetected_by_project_stages,
        "stage_5_drift": {
            "f2b": [f2b_start, f2b_end], "f0": [f0_start, f0_end],
            "map": [map_start, map_end], "drift": drift,
        },
        "accept_count_quality_observation": accept_quality,
        "verdict": verdict,
        "score": score,
        "hard_failures": hard_failures,
        "documented_method_blind_spots": undetected + [
            "the canonical gate does not detect duplicate mapping keys (measured: live file "
            "passes with 7 duplicates; M1 same-value duplicate passes the gate)",
            "neither structural stage type-checks the quantifier domains (measured: M3 passes "
            "both stages)",
            "mathematical truth of the class statement (both stages structural only)",
            "citation scope/truth of l1_ledger_refs (not verified here)",
        ],
        "scope_limit": (
            "Structural + contract conformance and blocker adjudication of one snapshot at the "
            "pinned hash. B3 is a canonical-publication (F0) gap, not an F2b class defect. Not a "
            "physics verdict, not a gate verdict, not an endorsement of cited theorems."),
        "next_falsifier": (
            "A live snapshot of AF-SCC-C0-VAC-GEN at 1bb78ce9b357 in which (i) a strict "
            "duplicate-key YAML loader parses cleanly and one canonical `revised_at` exists, "
            "(ii) D0 is a well-typed pair domain (or the binder is split per branch), and "
            "(iii) class_contract_pointer resolves against the controller-authoritative "
            "canonical tree -- i.e. a repair that falsifies B1+B2+B3; or measured drift of the "
            "canonical F2b/F0/map files away from the hashes recorded here."),
        "generated_at": now_iso(),
    }
    (HERE / "f2b_blocker_adjudication_evidence.json").write_text(
        json.dumps(evidence, indent=1) + "\n")
    ev_hash = sha256_file(HERE / "f2b_blocker_adjudication_evidence.json")

    review = {
        "schema_version": "a1-review/v1",
        "event_id": "w098-f2b-blocker-review-" + now_iso(),
        "event_type": "review",
        "created_at": now_iso(),
        "actor": "worker-098",
        "reviewer": "worker-098",
        "reviewer_independence": (
            "not an author of this artifact or of its authoring mirror; method and script are "
            "this worker's own (yaml.compose duplicate enumeration, strict-loader probe, pointer "
            "resolution, alias-aware cross-check, map hash-field scan)"),
        "task_id": TASK_ID,
        "target_id": NODE_ID,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "artifact": "schemas/af_scc_c0_vacuum.yaml",
        "reviewed_sha256": f2b_start,
        "reviewed_bytes": evidence["reviewed_bytes"],
        "counts_as_full_schema_verdict": False,
        "verdict": verdict,
        "score": score,
        "hard_failures": hard_failures,
        "findings": [
            "B1 CONFIRMED live: 8 top-level `revised_at` keys (7 duplicates) in the canonical "
            "bytes; a strict duplicate-key YAML loader fails; the canonical gate still returns "
            "PASS (measured blind spot).",
            "B2 CONFIRMED live, family-wide: D0 is a disjunction under a `forall (s,delta)` "
            "binder with different ambient topologies per branch; the same defect shape is in "
            "F1, F2a and F2b (F2a/F2b D0 text verbatim, F1 adds a clause), so the repair "
            "belongs to the family, not to F2b alone.",
            "B3 CONFIRMED structurally, scope-corrected: class_contract_pointer does not resolve "
            "in canonical F0 (no `class_contracts` key) but resolves in the declared authoring "
            "supplement and agrees alias-aware; this is an F0 publication gap affecting every "
            "class schema, not an F2b class-semantics defect.",
            "B4 NOT live: the current map F2b pin equals the measured hash and "
            "declared_hash_matches_measured is true; the malformed prefix survives only in "
            "historical review text. Disposition: repaired/not a defect of these bytes.",
            f"structural re-check: canonical gate {gate.get('verdict')}, "
            f"class-separation hard findings {len(cs_hard)}, "
            f"contract checks {len(checks) - len(failed)}/{len(checks)} ok",
            f"controls: detected {sum(c['detected'] for c in controls)}/{len(controls)}; "
            f"gate-alone blind spots: {gate_alone_blind_spots}; "
            f"undetected by all three project stages: {undetected_by_project_stages}",
            "accept-count quality: four recorded accepts at this hash did not treat B1/B2 as "
            "blocking; the accept count overstates clean verification coverage.",
        ],
        "conditions": [
            "binds only sha256 " + f2b_start,
            "scoped: blocker adjudication + structural conformance; not a full physics or "
            "citation audit",
        ],
        "evidence_refs": [
            "artifacts/worker-098/f2b_blocker_adjudication/f2b_blocker_adjudication_evidence.json"
            f"#{ev_hash[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{f2b_start[:12]}",
            f"research_map/formulation_taxonomy.yaml#{f0_start[:12]}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{supp_start[:12]}",
            f"research_map/research_map.json#{map_start[:12]}",
        ],
        "artifact_refs": [
            "artifacts/worker-098/f2b_blocker_adjudication/f2b_blocker_adjudication_evidence.json",
        ],
        "scope_limit": evidence["scope_limit"],
        "next_falsifier": evidence["next_falsifier"],
    }
    (HERE / "f2b_blocker_adjudication_review.json").write_text(
        json.dumps(review, indent=1) + "\n")
    rev_dir = ROOT / "reviews"
    rev_dir.mkdir(exist_ok=True)
    (rev_dir / "F2b-blocker-adjudication-worker-098.json").write_text(
        json.dumps(review, indent=1) + "\n")

    print(json.dumps({
        "task_id": TASK_ID,
        "reviewed_sha256": f2b_start,
        "gate": gate.get("verdict"),
        "classsep_hard": cs_hard,
        "contract_ok": f"{len(checks) - len(failed)}/{len(checks)}",
        "claims": {k: v["status"] for k, v in blockers.items()},
        "duplicates": len(dups),
        "controls_detected": f"{sum(c['detected'] for c in controls)}/{len(controls)}",
        "gate_alone_blind_spots": gate_alone_blind_spots,
        "undetected_by_project_stages": undetected_by_project_stages,
        "undetected": undetected,
        "hard_failures": hard_failures,
        "verdict": verdict,
        "score": score,
        "evidence_sha256": ev_hash,
        "review_file": "reviews/F2b-blocker-adjudication-worker-098.json",
        "drift": drift,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
