#!/usr/bin/env python3
"""W090-F2B-REV13-FULL-01 -- independent full-schema verification of F2b
(AF-SCC-C0-VAC-GEN) at the frozen rev13 pin b2ab6acb2bbe.

Read-only with respect to every canonical path: all content checks read the
freeze-first snapshot copies written by pin_snapshot.py.  Deterministic;
stdlib + PyYAML.  Exit 0 iff there is no blocking check failure and every
pre-registered mutant is caught.

Outputs results.json and controls.json next to this file.
"""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SNAP = os.path.join(HERE, "snapshot")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).astimezone(timezone.utc)
_MUTANT = None

PIN = {
    "F2b_canonical": ("schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F2b_mirror": ("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "F2a_canonical": ("schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F1_canonical": ("schemas/af_wcc_vacuum.yaml", "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "F0_taxonomy": ("research_map/formulation_taxonomy.yaml", "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"),
    "supplement": ("artifacts/formulation/formulation_taxonomy.yaml", "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"),
    "consistency_evidence": ("artifacts/formulation/evidence/taxonomy_consistency.json", "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"),
    "frozen": ("artifacts/formulation/FROZEN.json", "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
    "vocab_aliases": ("artifacts/formulation/VOCAB_ALIASES.json", "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba"),
}

CLASSSEP_PINNED = "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py"
CHECK_CLASS_SCHEMA = "artifacts/formulation/tools/check_class_schema.py"
STRUCTURAL_TOOL_SHA = "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff"

REQUIRED_SECTIONS = [
    "schema_version", "artifact_kind", "class_id", "node_id", "owner", "authored_by",
    "authored_at", "revised_at", "revision", "class_components", "class_contract_pointer",
    "class_contract_supplement_pointer", "sibling_disjoint_from", "epistemic_status",
    "promotion_rule", "scope_statement", "quantifiers", "extension_predicate", "topology",
    "data_class", "regularity", "genericity", "non_vacuity", "i_plus", "visibility",
    "conclusion", "implication_ledger", "falsifier", "anti_scope", "class_identity_variants",
    "known_status", "f0_binding",
]
SECTIONS_FOR_SEMANTICS = ["quantifiers", "extension_predicate", "conclusion", "genericity",
                          "implication_ledger", "falsifier", "visibility", "i_plus", "anti_scope"]

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
MERGED_RE = re.compile(r"C\s*[\^\{]*\s*(0|2)\s*[\}\^]*\s*(or|/|,|and)\s*[\^\{]*\s*(0|2)\s*[\}\^]*", re.I)

import yaml  # noqa: E402


class DupLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    keys = []
    for k, _ in node.value:
        try:
            keys.append(loader.construct_object(k, deep=deep))
        except Exception:
            keys.append(repr(k))
    dups = sorted({str(k) for k in keys if keys.count(k) > 1})
    mapping = yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
    if dups:
        loader.dup_keys.extend(dups)
    return mapping


DupLoader.construct_mapping = _construct_mapping
DupLoader.dup_keys = []


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _snap_path(rel):
    prefix = PIN[rel][1]
    names = [n for n in os.listdir(SNAP) if n.startswith(prefix or "___none___")]
    if not names:
        suffix = PIN[rel][0].replace("/", "__")
        names = [n for n in os.listdir(SNAP) if n.endswith(suffix)]
    if not names:
        raise FileNotFoundError(rel)
    return os.path.join(SNAP, names[0])


def load_pinned(rel):
    raw = open(_snap_path(rel), "rb").read()
    return raw, raw.decode()


def parse_yaml(text):
    DupLoader.dup_keys = []
    obj = yaml.load(text, Loader=DupLoader)
    return obj, list(DupLoader.dup_keys)


def norm_core(s):
    """Whitespace/parenthetical/stopword normalization for data_class prose.

    Declared in results.json so every core-vector equality is auditable.
    Provenance fields (citation_status, locator, hypotheses_reconciliation,
    sobolev status) are excluded from the core vector by construction.
    """
    s = str(s).lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = s.replace("every predicate in this schema is", "all predicates are")
    s = s.replace("no gauge is fixed", "no gauge fixed")
    s = re.sub(r"\b(is|are|this|the|in|schema)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ;.")
    return s


def core_vector(dc):
    sv = (dc.get("regularity_class") or {}).get("sobolev_variant") or {}
    ad = dc.get("asymptotic_decay") or {}
    am = dc.get("adm_mass") or {}
    con = dc.get("constraints") or {}
    return {
        "matter": norm_core(dc.get("matter")),
        "cosmological_constant": norm_core(dc.get("cosmological_constant")),
        "equations": norm_core(dc.get("equations")),
        "constraints.hamiltonian": norm_core(con.get("hamiltonian")),
        "constraints.momentum": norm_core(con.get("momentum")),
        "regularity.default": norm_core((dc.get("regularity_class") or {}).get("default")),
        "regularity.sobolev.s": norm_core(sv.get("s")),
        "regularity.sobolev.delta": norm_core(sv.get("delta")),
        "regularity.sobolev.spaces": norm_core(sv.get("spaces")),
        "decay.metric": norm_core(ad.get("metric")),
        "decay.second_fundamental_form": norm_core(ad.get("second_fundamental_form")),
        "decay.parity_conditions": norm_core(str(ad.get("parity_conditions")).split(";")[0]),
        "symmetry": norm_core(dc.get("symmetry")),
        "adm_mass.exists": am.get("exists"),
        "adm_mass.sign": norm_core(am.get("sign")),
        "gauge": norm_core(dc.get("gauge")),
    }


def run_checks():
    checks = []

    def add(cid, blocking, ok, detail):
        checks.append({"id": cid, "blocking": blocking,
                       "status": "pass" if ok else "fail", "detail": detail})

    if _MUTANT is not None:
        f2b_text, f2b = _MUTANT
        f2b_raw = f2b_text.encode()
        _, dup_keys = parse_yaml(f2b_text)
    else:
        f2b_raw, f2b_text = load_pinned("F2b_canonical")
        f2b, dup_keys = parse_yaml(f2b_text)

    f0 = yaml.safe_load(load_pinned("F0_taxonomy")[1])
    f2a = yaml.safe_load(load_pinned("F2a_canonical")[1])
    f1 = yaml.safe_load(load_pinned("F1_canonical")[1])
    sup = yaml.safe_load(load_pinned("supplement")[1])
    ev_text = load_pinned("consistency_evidence")[1]
    ev = json.loads(ev_text)
    frozen = json.loads(load_pinned("frozen")[1])
    vocab = json.loads(load_pinned("vocab_aliases")[1])

    # --- pins / mirror ---------------------------------------------------
    live_f2b = sha256(os.path.join(ROOT, PIN["F2b_canonical"][0]))
    live_mirror = sha256(os.path.join(ROOT, PIN["F2b_mirror"][0]))
    add("P01-pin-canonical", True, live_f2b == PIN["F2b_canonical"][1],
        f"live F2b {live_f2b[:12]} vs pin {PIN['F2b_canonical'][1][:12]}")
    add("P02-mirror-byte-identical", True, live_mirror == live_f2b,
        f"mirror {live_mirror[:12]} vs canonical {live_f2b[:12]}")

    # --- structural hygiene ----------------------------------------------
    add("S01-yaml-parses", True, isinstance(f2b, dict), f"type={type(f2b).__name__}")
    add("S02-no-duplicate-keys", True, not dup_keys, f"duplicates={dup_keys}")
    add("S03-revision-13", True, f2b.get("revision") == 13, f"revision={f2b.get('revision')}")
    stamps = {"revised_at": f2b.get("revised_at"),
              "checked_at": (f2b.get("f0_binding") or {}).get("checked_at")}
    worst, worst_skew = None, -10 ** 9
    for k, v in stamps.items():
        try:
            skew = (datetime.fromisoformat(str(v)).astimezone(timezone.utc) - NOW).total_seconds()
        except Exception:
            skew = 10 ** 9
        if skew > worst_skew:
            worst, worst_skew = k, skew
    add("S04-clock-not-future", True, worst_skew < 300,
        f"max future skew {worst_skew:.0f}s on {worst} (limit 300s)")
    missing = [s for s in REQUIRED_SECTIONS if s not in f2b]
    add("S05-required-sections", True, not missing, f"missing={missing}")
    empty_sem = [s for s in SECTIONS_FOR_SEMANTICS if not f2b.get(s)]
    add("S06-semantic-sections-nonempty", True, not empty_sem, f"empty={empty_sem}")

    # --- F0 binding -------------------------------------------------------
    f0_live = sha256(os.path.join(ROOT, PIN["F0_taxonomy"][0]))
    bind = f2b.get("f0_binding") or {}
    add("B01-declared-F0-resolves", True,
        bind.get("declared_f0_sha256") == f0_live == PIN["F0_taxonomy"][1],
        f"declared={str(bind.get('declared_f0_sha256'))[:12]} live={f0_live[:12]}")
    classes = f0.get("classes") or {}
    add("B02-class-contract-resolves", True,
        f2b.get("class_id") in (f0.get("class_ids") or []) and f2b.get("class_id") in classes,
        f"class_ids={f0.get('class_ids')}")
    ptr = str(f2b.get("class_contract_pointer") or "")
    add("B03-pointer-target-correct", True,
        ptr.endswith("#classes." + str(f2b.get("class_id"))), f"pointer={ptr}")
    ev_live = sha256(os.path.join(ROOT, PIN["consistency_evidence"][0]))
    add("B04-consistency-evidence-resolves", True,
        bind.get("consistency_evidence_sha256") == ev_live == PIN["consistency_evidence"][1],
        f"declared={str(bind.get('consistency_evidence_sha256'))[:12]} live={ev_live[:12]}")
    add("B05-evidence-consistent", True,
        ev.get("consistent") is True and f2b.get("class_id") in (ev.get("classes_compared") or []),
        f"consistent={ev.get('consistent')} compared={len(ev.get('classes_compared') or [])}")
    witnesses = HEX64.findall(ev_text)
    add("B06-embedding-witnesses", False, len(witnesses) > 0,
        f"hex64 byte-identity witnesses in evidence = {len(witnesses)} (residual W090-FCONSEV-01)")
    sup_cc = (sup.get("class_contracts") or {}).get(f2b.get("class_id"))
    add("B07-supplement-pointer-resolves", True, isinstance(sup_cc, dict),
        f"supplement class_contracts.{f2b.get('class_id')} present={isinstance(sup_cc, dict)}")
    add("B08-supplement-components-match", True,
        isinstance(sup_cc, dict) and sup_cc.get("components") == f2b.get("class_components"),
        f"supplement={json.dumps(sup_cc.get('components')) if isinstance(sup_cc, dict) else None} schema={json.dumps(f2b.get('class_components'))}")
    frozen_files = frozen.get("files") or {}
    sup_entry = frozen_files.get(PIN["supplement"][0]) or {}
    add("B09-supplement-transitively-pinned", False,
        sup_entry.get("sha256") == PIN["supplement"][1],
        f"FROZEN rev{frozen.get('revision')} entry={str(sup_entry.get('sha256'))[:12]}; no schema-side supplement hash field (W090-FCONSEV-02 residual)")
    f2b_entry = frozen_files.get(PIN["F2b_canonical"][0]) or {}
    add("B10-schema-manifest-pin", True, f2b_entry.get("sha256") == PIN["F2b_canonical"][1],
        f"FROZEN entry={str(f2b_entry.get('sha256'))[:12]}")

    # --- vocabulary -------------------------------------------------------
    ct = (f2b.get("conclusion") or {}).get("conclusion_type")
    gk = (f2b.get("genericity") or {}).get("kind")
    ct_canon = ct in (vocab.get("conclusion_type") or {})
    gk_canon = gk in (vocab.get("genericity_kind") or {})
    add("V01-tokens-in-registry", True, ct_canon and gk_canon,
        f"conclusion_type={ct} registry={ct_canon}; genericity_kind={gk} registry={gk_canon}")
    f0_ct_allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
    f0_gk_allowed = ((f0.get("field_vocabulary") or {}).get("genericity_kind") or {}).get("allowed") or []
    inversions = []
    if ct not in f0_ct_allowed:
        inversions.append(f"conclusion_type={ct} not in F0 allowed {f0_ct_allowed}")
    if gk not in f0_gk_allowed:
        inversions.append(f"genericity_kind={gk} not in F0 allowed {f0_gk_allowed}")
    add("V02-F0-allowed-list-inversion", False, not inversions,
        "; ".join(inversions) + " (W090-VOCAB-01 authority conflict; registry declares these equivalent)")
    add("V03-registry-pointer-declared", False, "VOCAB_ALIASES.json" in f2b_text,
        "F2b declares no VOCAB_ALIASES.json pointer (W090-VOCAB-04 residual)"
        if "VOCAB_ALIASES.json" not in f2b_text else "pointer present")

    # --- merged-regularity scan ------------------------------------------
    hits = []
    for m in MERGED_RE.finditer(f2b_text):
        hits.append(f2b_text[max(0, m.start() - 90):m.end() + 60].replace("\n", " "))
    assertions = [h for h in hits
                  if not re.search(r"not_this_class|forbidden|must not|never|not use|phrases_that_are_not", h, re.I)]
    add("V04-no-merged-regularity-assertion", True, not assertions,
        f"merged-pattern hits={len(hits)} assertion-context={len(assertions)}")

    # --- conclusion / family separation -----------------------------------
    concl = f2b.get("conclusion") or {}
    iplus = f2b.get("i_plus") or {}
    vis = f2b.get("visibility") or {}
    add("C01-no-conclusion-inflation", True,
        concl.get("conclusion_type") == "scc_c0_future_inextendibility"
        and concl.get("epistemic_status") == "open_problem"
        and bool(concl.get("promotion_rule") or f2b.get("promotion_rule")),
        f"type={concl.get('conclusion_type')} status={concl.get('epistemic_status')}")
    operative = {k: concl.get(k) for k in ("conclusion_type", "family", "epistemic_status",
                                           "statement_natural_language", "statement_formal",
                                           "equivalent_rephrasings", "known_obstruction",
                                           "claim_promotion")}
    operative_blob = json.dumps(operative).lower()
    wcc_tokens = [t for t in ("i+", "asymptotic predictability", "visible") if t in operative_blob]
    prohibitions = " ".join(str(x) for x in (concl.get("forbidden_strengthenings") or [])).lower()
    add("C02-I-plus-out-of-conclusion", True,
        iplus.get("in_conclusion") is False and iplus.get("completeness_in_conclusion") is False
        and not wcc_tokens and "i+" in prohibitions,
        f"operative WCC tokens={wcc_tokens}; prohibition present={'i+' in prohibitions}")
    add("C03-visibility-out-of-conclusion", True,
        vis.get("role") == "not_in_conclusion" and bool(vis.get("forbidden_falsifier")),
        f"role={vis.get('role')}")
    led = f2b.get("implication_ledger") or {}
    one_way = led.get("one_way_entailments") or []
    c0_to_c2 = any("C0" in str(r.get("from")) and "C2" in str(r.get("to")) for r in one_way)
    rev_rows = [r for r in one_way if "C2" in str(r.get("from")) and "C0" in str(r.get("to"))]
    forb = led.get("forbidden_transfers") or []
    rev_forbidden = any("C2" in str(r.get("from")) for r in forb)
    add("C04-one-way-C0-to-C2", True, c0_to_c2 and not rev_rows and rev_forbidden,
        f"c0_to_c2={c0_to_c2} reverse_rows={len(rev_rows)} forbidden_reverse={rev_forbidden}")
    reg = f2b.get("regularity") or {}
    ext = f2b.get("extension_predicate") or {}
    add("C05-extension-class-frozen", True,
        reg.get("extension_regularity") == "C0" and reg.get("extension_solution_concept") == "none"
        and ext.get("frozen_regularity") == "C0" and ext.get("frozen_equation_concept") == "none"
        and ext.get("frozen_direction") == "future",
        f"ext_reg={reg.get('extension_regularity')} eq={reg.get('extension_solution_concept')} dir={ext.get('frozen_direction')}")
    anti_ids = [e.get("class_id") for e in ((f2b.get("anti_scope") or {}).get("not_this_class") or []) if e.get("class_id")]
    add("C06-anti-scope-free-of-foreign-classes", True,
        all(cid in (f0.get("class_ids") or []) for cid in anti_ids),
        f"anti_scope class ids={sorted(set(anti_ids))}")
    pairs = {tuple(sorted(p)) for p in (d.get("pair") for d in (f0.get("disjointness") or [])) if p}
    sib = f2b.get("sibling_disjoint_from")
    sib_a = f2a.get("sibling_disjoint_from")
    add("C07-sibling-disjointness-recursive", True,
        tuple(sorted((f2b.get("class_id"), sib))) in pairs and sib_a == f2b.get("class_id")
        and f2a.get("class_id") == sib,
        f"F0 pair present={tuple(sorted((f2b.get('class_id'), sib))) in pairs}; "
        f"F2b->{sib}, F2a->{sib_a}")
    axes = ((f0.get("classes") or {}).get(f2b.get("class_id")) or {}).get("axes") or {}
    comp = f2b.get("class_components") or {}
    alias_ct = (vocab.get("conclusion_type") or {}).get(ct, [])
    alias_gk = (vocab.get("genericity_kind") or {}).get(gk, [])
    axis_checks = {
        "family": comp.get("censorship") == axes.get("family"),
        "matter": comp.get("matter") == "VAC" and axes.get("matter_model") == "vacuum",
        "symmetry": (f2b.get("data_class") or {}).get("symmetry") == axes.get("symmetry"),
        "asymptotics": comp.get("asymptotics") == "AF" and axes.get("asymptotics") == "asymptotically_flat_3p1",
        "genericity": comp.get("genericity") == "GEN" and axes.get("genericity_kind") in (alias_gk + [gk]),
        "regularity_token": comp.get("regularity_token") == axes.get("regularity_token") == "C0",
        "conclusion_type": axes.get("conclusion_type") in (alias_ct + [ct]),
    }
    bad_axes = sorted(k for k, v in axis_checks.items() if not v)
    add("C08-class-components-agree-F0-axes", True, not bad_axes,
        f"F0 axes vs schema disagreement={bad_axes} (alias-resolved against VOCAB_ALIASES)")

    # --- genericity -------------------------------------------------------
    gen = f2b.get("genericity") or {}
    add("G01-genericity-wellformed", True,
        gen.get("kind") == "residual_comeager" and gen.get("is_part_of_class") is True
        and bool(gen.get("class_change_warning")) and bool(gen.get("transfer_failures"))
        and bool(gen.get("transfer_holds")),
        f"kind={gen.get('kind')} is_part={gen.get('is_part_of_class')} warnings={bool(gen.get('class_change_warning'))}")
    variants = gen.get("variants") or []
    bad_variants = [v for v in variants if v.get("kind") != "residual_comeager" and v.get("is_this_class") is not False]
    add("G02-no-nondefault-genericity-as-class", True, not bad_variants,
        f"non-default variants mistakenly flagged is_this_class: {len(bad_variants)}")

    # --- data-class transfer guard (T1) -----------------------------------
    dc_b, dc_a, dc_1 = f2b.get("data_class") or {}, f2a.get("data_class") or {}, f1.get("data_class") or {}
    vec_b, vec_a, vec_1 = core_vector(dc_b), core_vector(dc_a), core_vector(dc_1)
    diffs_ba = sorted(k for k in vec_b if vec_b[k] != vec_a[k])
    diffs_b1 = sorted(k for k in vec_b if vec_b[k] != vec_1[k])
    add("T01-data-class-core-equal-C0-C2", True, not diffs_ba,
        f"F2b vs F2a normalized 16-key core diffs={diffs_ba}")
    gk_a = (f2a.get("genericity") or {}).get("kind")
    gen_a = f2a.get("genericity") or {}
    gen_keys = ("kind", "ambient_space", "topology_or_measure", "generic_set", "is_part_of_class")
    gen_diffs = [k for k in gen_keys if gen.get(k) != gen_a.get(k)]
    add("T02-genericity-identical-siblings", True, not gen_diffs,
        f"F2b vs F2a genericity field diffs={gen_diffs}")
    add("T03-data-class-core-versus-F1", False, not diffs_b1,
        f"F2b vs F1 normalized core diffs={diffs_b1}; raw F1-only clauses are prose/annotation "
        f"(adm_mass.rigidity, parity guidance, sobolev status/locator)")

    # --- falsifier decidability -------------------------------------------
    fal = f2b.get("falsifier") or {}
    t1 = fal.get("tier_1") or {}
    add("F01-falsifier-decidable", True,
        bool(t1.get("witness_type")) and bool(t1.get("genericity_requirement"))
        and bool(t1.get("machine_checkable_steps")) and bool(t1.get("non_machine_checkable_step"))
        and bool(fal.get("schema_falsifiers")),
        f"tier1_steps={len(t1.get('machine_checkable_steps') or [])} schema_falsifiers={len(fal.get('schema_falsifiers') or [])}")
    nv = f2b.get("non_vacuity") or {}
    add("F02-non-vacuity-declared", True, bool(nv.get("condition")) and bool(nv.get("vacuity_falsifier")),
        f"status={str(nv.get('status'))[:60]}")
    ks = f2b.get("known_status") or {}
    add("F03-no-proof-claim", True,
        "open" in str(ks.get("status", "")) and bool(ks.get("why_this_class_is_not_recorded_as_refuted")),
        f"status={ks.get('status')}")

    # --- review bookkeeping ----------------------------------------------
    rev_events = []
    ev_path = os.path.join(ROOT, "research_map", "events.jsonl")
    if os.path.isfile(ev_path):
        for line in open(ev_path):
            if not line.strip() or '"F2b"' not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("event_type") != "review":
                continue
            if "b2ab6acb" in json.dumps(d) and str(d.get("target_id")) in ("F2b", "F2a,F1,F2b", "F1,F2a,F2b"):
                rev_events.append({"actor": d.get("actor"), "verdict": d.get("verdict"),
                                   "reviewed_sha256": str(d.get("reviewed_sha256"))[:12],
                                   "event_id": d.get("event_id")})
    rs = f2b.get("review_status") or {}
    add("R01-review-status-fresh", False, bool(rs.get("independent_reviewers")),
        f"independent_reviewers={rs.get('independent_reviewers')} verdict={rs.get('verdict')} while "
        f"{len(rev_events)} F2b rev13 review event(s) exist at this pin (residual W090-R12-02 analog)")

    # --- external tools (read-only) ---------------------------------------
    tool = os.path.join(ROOT, CHECK_CLASS_SCHEMA)
    tool_sha = sha256(tool) if os.path.isfile(tool) else None
    x1 = subprocess.run([sys.executable, tool, "--json", _snap_path("F2b_canonical")],
                        capture_output=True, text=True)
    try:
        x1j = json.loads(x1.stdout)
    except Exception:
        x1j = {}
    add("X01-structural-checker", True,
        tool_sha == STRUCTURAL_TOOL_SHA and x1j.get("verdict") == "pass" and x1.returncode == 0,
        f"tool={str(tool_sha)[:12]} verdict={x1j.get('verdict')} rc={x1.returncode}")
    sep_results = {}
    for tag, path in (("pinned_c266dbec", os.path.join(ROOT, CLASSSEP_PINNED)),
                      ("live_a8c04fc3", os.path.join(ROOT, "research_map", "class_separation.py"))):
        try:
            spec = importlib.util.spec_from_file_location("cs_" + tag, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            f = mod.findings_for_text(f2b_text, PIN["F2b_canonical"][0])
            sep_results[tag] = {"sha256": sha256(path)[:12], "n_findings": len(f),
                                "findings": [str(x)[:200] for x in f][:6]}
        except Exception as e:  # noqa: BLE001
            sep_results[tag] = {"error": repr(e)[:200]}
    add("X02-class-separation-pinned", True,
        sep_results["pinned_c266dbec"].get("n_findings") == 0,
        json.dumps(sep_results["pinned_c266dbec"])[:300])
    add("X03-class-separation-live-drift", False,
        sep_results["live_a8c04fc3"].get("n_findings") == 0,
        "live detector (drift, not adopted, CF-26): " + json.dumps(sep_results["live_a8c04fc3"])[:260])

    # --- fixture stage behavior (advisory; suite calibration invalid) -----
    fixture_dir = os.path.join(ROOT, "schemas", "semantic_contract_tests", "fixtures")
    fixture_verdicts = {}
    for name in ("sem14_c2_result_cited_as_c0.yaml", "sem06_visibility_falsifier_rephrased.yaml",
                 "sem16_converse_implication.yaml", "struct01_composite_regularity.yaml",
                 "sem07_i_plus_used_in_conclusion.yaml"):
        fp = os.path.join(fixture_dir, name)
        if not os.path.isfile(fp):
            fixture_verdicts[name] = "missing"
            continue
        r = subprocess.run([sys.executable, tool, "--json", fp], capture_output=True, text=True)
        try:
            fixture_verdicts[name] = json.loads(r.stdout).get("verdict")
        except Exception:
            fixture_verdicts[name] = "unparsed"
    add("X04-fixture-stage", False, True,
        "advisory only: suite observed_verdicts validity.valid_for_calibration=false (ADJ-CONTROL-STALENESS); "
        "verdicts=" + json.dumps(fixture_verdicts))

    # --- live re-measure at end ------------------------------------------
    live_after = sha256(os.path.join(ROOT, PIN["F2b_canonical"][0]))
    add("P03-pin-stable-across-run", True, live_after == live_f2b,
        f"before={live_f2b[:12]} after={live_after[:12]}")

    ctx = {"rev_events_at_pin": rev_events, "classsep": sep_results,
           "fixture_verdicts": fixture_verdicts, "tool_sha256": tool_sha,
           "witnesses": len(witnesses), "dup_keys": dup_keys,
           "core_vector_normalized_F2b": vec_b, "core_diffs_F2b_F2a": diffs_ba,
           "core_diffs_F2b_F1": diffs_b1,
           "normalization_note": "norm_core(): lowercase, strip parentheticals, collapse whitespace, "
                                 "drop articles/prepositions, singularize 'every predicate in this schema is'; "
                                 "parity_conditions truncated at first ';'; provenance fields by construction excluded"}
    return checks, ctx


def _mutate_obj(obj, mut):
    o = json.loads(json.dumps(obj))
    mut(o)
    return yaml.safe_dump(o, sort_keys=False, default_flow_style=False, allow_unicode=True)


MUTANTS = [
    ("M1-merged-conclusion-type", "V01-tokens-in-registry",
     lambda o: o["conclusion"].__setitem__("conclusion_type", "strong_cosmic_censorship")),
    ("M2-visibility-in-conclusion", "C03-visibility-out-of-conclusion",
     lambda o: o["visibility"].__setitem__("role", "conclusion")),
    ("M3-reverse-implication", "C04-one-way-C0-to-C2",
     lambda o: o["implication_ledger"]["one_way_entailments"].append(
         {"from": "no proper future C2 extension", "to": "no proper future C0 extension", "relation": "entails"})),
    ("M4-extension-regularity-C2", "C05-extension-class-frozen",
     lambda o: o["regularity"].__setitem__("extension_regularity", "C2")),
    ("M5-genericity-full-measure", "G01-genericity-wellformed",
     lambda o: o["genericity"].__setitem__("kind", "full_measure")),
    ("M6-f0-hash-wrong", "B01-declared-F0-resolves",
     lambda o: o["f0_binding"].__setitem__("declared_f0_sha256", "0" * 64)),
    ("M7-duplicate-key", "S02-no-duplicate-keys",
     lambda t: t + "\nrevision: 13\n"),
    ("M8-future-checked-at", "S04-clock-not-future",
     lambda o: o["f0_binding"].__setitem__("checked_at", "2099-01-01T00:00:00+08:00")),
]


def main():
    global _MUTANT
    _MUTANT = None
    checks, ctx = run_checks()
    blocking_fail = [c for c in checks if c["blocking"] and c["status"] != "pass"]
    carriers = [c for c in checks if not c["blocking"] and c["status"] != "pass"]

    _, f2b_text0 = load_pinned("F2b_canonical")
    f2b_obj = yaml.safe_load(f2b_text0)

    controls = []
    for name, target, mut in MUTANTS:
        try:
            if name == "M7-duplicate-key":
                text = mut(f2b_text0)
            else:
                text = _mutate_obj(f2b_obj, mut)
            obj = yaml.safe_load(text)
            _MUTANT = (text, obj)
            mchecks, _ = run_checks()
            statuses = {c["id"]: c["status"] for c in mchecks}
            controls.append({"mutant": name, "expected_check": target,
                             "caught": statuses.get(target) == "fail",
                             "mutant_status": statuses.get(target)})
        except Exception as e:  # noqa: BLE001
            controls.append({"mutant": name, "expected_check": target, "caught": False,
                             "error": repr(e)[:200]})
        finally:
            _MUTANT = None
    controls_pass = sum(1 for c in controls if c["caught"])
    ok = (not blocking_fail) and controls_pass == len(controls)
    verdict = "accept" if ok else "revise"

    results = {
        "schema": "w090-f2b-full-verification/v1",
        "task_id": "W090-F2B-REV13-FULL-01",
        "actor": "worker-090",
        "created_at": datetime.now(CST).isoformat(),
        "target": {"node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
                   "path": PIN["F2b_canonical"][0], "sha256": PIN["F2b_canonical"][1]},
        "pins": {k: {"path": v[0], "sha256": v[1]} for k, v in PIN.items()},
        "counts": {"checks": len(checks),
                   "pass": sum(1 for c in checks if c["status"] == "pass"),
                   "blocking_fail": len(blocking_fail), "carriers": len(carriers)},
        "checks": checks,
        "carriers": [c["id"] for c in carriers],
        "blocking_failures": [c["id"] for c in blocking_fail],
        "controls": controls, "controls_caught": controls_pass,
        "verdict_recommendation": verdict,
        "context": ctx,
        "blind": False,
        "blind_disclosure": ("Not a carded blind review. Verdict-level rows in the map review index and "
                             "worker-061's scoped CH-axis accept event were read while auditing accept coverage; "
                             "no full-schema F2b review file body was read before this verdict. "
                             "Advisory worker verdict; cannot set a gate verdict or node status."),
        "clock_at_run": NOW.isoformat(),
    }
    with open(os.path.join(HERE, "results.json"), "w") as fh:
        json.dump(results, fh, indent=1, sort_keys=True)
    with open(os.path.join(HERE, "controls.json"), "w") as fh:
        json.dump({"schema": "w090-controls/v1", "task_id": "W090-F2B-REV13-FULL-01",
                   "controls": controls, "caught": controls_pass, "total": len(controls),
                   "pre_registered": True}, fh, indent=1, sort_keys=True)
    print(json.dumps({"counts": results["counts"], "verdict": verdict,
                      "blocking_failures": results["blocking_failures"],
                      "carriers": results["carriers"],
                      "controls": f"{controls_pass}/{len(controls)}"}, indent=1))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
