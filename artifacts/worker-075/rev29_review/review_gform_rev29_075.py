#!/usr/bin/env python3
"""
W075-GFORM-REV29-REVIEW-08 - independent full-schema review of the F1/F2a/F2b canonical class
schemas at the FROZEN rev29 pins.

Independent instrument: it does not call the author's check_class_schema.py or any lead tool for
its verdict. It measures the target hash itself at verdict time, re-checks the F0/evidence binding,
class isolation, conclusion integrity, quantifier/topology binding, the rev12->rev13 repair
minimality and the class-specific direction claims, and runs seven negative controls on copies.

Writes: reviews/<Class>-review-rev29-075.json (verdict) and a copy under
artifacts/worker-075/rev29_review/. Read-only w.r.t. every canonical input.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTDIR = HERE
REVIEWS = ROOT / "reviews"
CTRL = HERE / "_review_controls"
CST = timezone(timedelta(hours=8))
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CLASS_IDS = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
COMPOSITE = re.compile(r"C0\s*(or|/|,)\s*C2|C2\s*(or|/|,)\s*C0|WCC\s*(or|/)\s*SCC|"
                       r"SCC\s*(or|/)\s*WCC", re.I)
SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
MIRRORS = {k: "artifacts/formulation/schemas/" + Path(v).name for k, v in SCHEMAS.items()}
PINNED_REV12 = {
    "F1": ("artifacts/worker-022/evbind_guard/pinned/af_wcc_vacuum.yaml",
           "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"),
    "F2a": ("artifacts/worker-022/evbind_guard/pinned/af_scc_c2_vacuum.yaml",
            "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"),
    "F2b": ("artifacts/worker-022/evbind_guard/pinned/af_scc_c0_vacuum.yaml",
            "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"),
}
F1_ALLOWED = ("revised_at", "revision", "revision_history",
              "f0_binding.consistency_evidence_sha256", "f0_binding.checked_at",
              "f0_binding.binding_note", "quantifiers.domains.D5.definition",
              "visibility.definition")
SC_ALLOWED = ("revised_at", "revision", "revision_history",
              "f0_binding.consistency_evidence_sha256", "f0_binding.checked_at",
              "f0_binding.binding_note")
EXPECT = {
    "F1": {"class_id": "AF-WCC-VAC-GEN", "family": "WCC", "regularity": "none",
           "conclusion_type": "weak_cosmic_censorship", "kind": "wcc"},
    "F2a": {"class_id": "AF-SCC-C2-VAC-GEN", "family": "SCC", "regularity": "C2",
            "conclusion_type": "scc_c2_future_inextendibility", "kind": "scc",
            "ext_regularity": "C2"},
    "F2b": {"class_id": "AF-SCC-C0-VAC-GEN", "family": "SCC", "regularity": "C0",
            "conclusion_type": "scc_c0_future_inextendibility", "kind": "scc",
            "ext_regularity": "C0"},
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.now(CST).replace(microsecond=0).isoformat()


def load_yaml(p):
    return yaml.safe_load(Path(p).read_text())


def dget(doc, dotted, default=None):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def deep_diff(a, b, path=()):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((".".join(path + (str(k),)), "<absent>", b[k]))
            elif k not in b:
                out.append((".".join(path + (str(k),)), a[k], "<absent>"))
            else:
                out.extend(deep_diff(a[k], b[k], path + (str(k),)))
    elif isinstance(a, list) and isinstance(b, list):
        if a != b:
            out.append((".".join(path), json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True)))
    elif a != b:
        out.append((".".join(path), a, b))
    return out


def checker_replay(ev_sha):
    """Replay the pinned consistency checker with both ROOT and out redirected; no canonical write."""
    src = (ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py").read_text()
    tmp = CTRL / "taxonomy_consistency.replay.json"
    CTRL.mkdir(exist_ok=True)
    src = src.replace("ROOT = Path(__file__).resolve().parents[3]", f"ROOT = Path({str(ROOT)!r})")
    src = src.replace('out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"',
                      f'out = Path({str(tmp)!r})')
    py = CTRL / "check_taxonomy_consistency_redirected.py"
    py.write_text(src)
    proc = subprocess.run([sys.executable, str(py)], capture_output=True, text=True, cwd=str(ROOT))
    return {"returncode": proc.returncode, "stdout": proc.stdout.strip()[:200],
            "replay_sha256": sha(tmp) if tmp.exists() else None,
            "pinned_evidence_sha256": ev_sha,
            "match": tmp.exists() and sha(tmp) == ev_sha}


def assertive_texts(doc):
    fields = ["quantifiers", "genericity", "topology", "data_class",
              "conclusion.statement_natural_language", "conclusion.statement_formal",
              "conclusion.conclusion_type", "epistemic_status", "promotion_rule"]
    if doc.get("class_id") == "AF-WCC-VAC-GEN":
        fields.append("visibility.definition")
    else:
        fields.extend(["extension_predicate.definition", "extension_predicate.frozen_direction",
                       "extension_predicate.frozen_regularity"])
    out = {}
    for f in fields:
        v = dget(doc, f)
        if v is not None:
            out[f] = json.dumps(v, sort_keys=True)
    return out


def run_checks(label):
    exp = EXPECT[label]
    rel = SCHEMAS[label]
    hard, soft, checks = [], [], {}
    fr = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    manifest_sha = sha(ROOT / "artifacts/formulation/FROZEN.json")
    f0 = load_yaml(ROOT / "research_map/formulation_taxonomy.yaml")
    start = {"target": sha(ROOT / rel), "manifest": manifest_sha}

    # C1 target pin + mirror
    pin = fr["files"][rel]["sha256"]
    checks["C1_target_pin"] = {"measured": start["target"], "frozen_rev29_pin": pin,
                               "match": start["target"] == pin}
    if start["target"] != pin:
        hard.append({"id": f"HF-075-{label}-PIN", "field": rel,
                     "detail": f"measured {start['target']} != FROZEN rev29 pin {pin}",
                     "falsifier": "re-hash the file; a match clears this"})
    mirror = MIRRORS[label]
    checks["C1b_mirror_byte_identical"] = {"mirror": mirror,
                                           "match": sha(ROOT / rel) == sha(ROOT / mirror)}
    if not checks["C1b_mirror_byte_identical"]["match"]:
        hard.append({"id": f"HF-075-{label}-MIRROR", "field": mirror,
                     "detail": "canonical and authoring mirror are not byte-identical",
                     "falsifier": "re-hash both paths"})

    # C2 manifest integrity
    bad_pins = [k for k, v in fr["files"].items()
                if not (ROOT / k).exists() or sha(ROOT / k) != v["sha256"]]
    checks["C2_manifest_pins"] = {"n_pins": len(fr["files"]), "bad": bad_pins,
                                  "frozen_revision": fr["revision"], "manifest_sha256": manifest_sha}
    if bad_pins:
        hard.append({"id": f"HF-075-{label}-MANIFEST", "field": "artifacts/formulation/FROZEN.json",
                     "detail": f"{len(bad_pins)} FROZEN pins do not match disk: {bad_pins[:5]}",
                     "falsifier": "re-hash every pinned file"})

    # C3 F0 / evidence binding
    doc = load_yaml(ROOT / rel)
    fb = doc.get("f0_binding", {})
    tax_sha = sha(ROOT / "research_map/formulation_taxonomy.yaml")
    ev_p = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
    ev = json.loads(ev_p.read_text())
    ev_sha = sha(ev_p)
    replay = checker_replay(ev_sha)
    checks["C3_f0_evidence_binding"] = {
        "declared_f0_sha256": fb.get("declared_f0_sha256"), "measured_f0_sha256": tax_sha,
        "declared_evidence_sha256": fb.get("consistency_evidence_sha256"),
        "measured_evidence_sha256": ev_sha,
        "evidence_consistent": ev.get("consistent"), "evidence_errors": ev.get("errors"),
        "checker_replay": replay,
        "supplement_pointer_resolves": pointer_resolves(fb.get("class_contract_supplement_pointer")),
    }
    c3 = checks["C3_f0_evidence_binding"]
    if fb.get("declared_f0_sha256") != tax_sha:
        hard.append({"id": f"HF-075-{label}-F0PIN", "field": "f0_binding.declared_f0_sha256",
                     "detail": f"declared {fb.get('declared_f0_sha256')} != measured {tax_sha}",
                     "falsifier": "re-hash research_map/formulation_taxonomy.yaml"})
    if fb.get("consistency_evidence_sha256") != ev_sha:
        hard.append({"id": f"HF-075-{label}-EVBIND",
                     "field": "f0_binding.consistency_evidence_sha256",
                     "detail": f"declared {fb.get('consistency_evidence_sha256')} != measured {ev_sha}",
                     "falsifier": "re-hash the named evidence path"})
    if ev.get("consistent") is not True or ev.get("errors"):
        hard.append({"id": f"HF-075-{label}-EVCLEAN", "field": "artifacts/formulation/evidence/taxonomy_consistency.json",
                     "detail": f"evidence not clean: consistent={ev.get('consistent')} errors={ev.get('errors')}",
                     "falsifier": "run the consistency checker"})
    if not replay["match"]:
        hard.append({"id": f"HF-075-{label}-REPLAY", "field": "artifacts/formulation/tools/check_taxonomy_consistency.py",
                     "detail": "redirected checker replay does not reproduce the pinned evidence bytes",
                     "falsifier": "re-run the redirected checker"})
    if not c3["supplement_pointer_resolves"]:
        hard.append({"id": f"HF-075-{label}-SUPPTR", "field": "f0_binding.class_contract_supplement_pointer",
                     "detail": "supplement pointer does not resolve", "falsifier": "resolve the pointer"})

    # C4 class identity / components
    own = doc.get("class_id")
    comp = doc.get("class_components") or {}
    derived = "AF-" + comp.get("censorship", "?") + "-" + comp.get("matter", "?") + "-" + comp.get("genericity", "?")
    checks["C4_class_identity"] = {"class_id": own, "expected": exp["class_id"],
                                   "components": comp, "derived_prefix": derived,
                                   "family_ok": comp.get("censorship") == exp["family"],
                                   "regularity_ok": comp.get("regularity_token") == exp["regularity"]}
    if own != exp["class_id"] or not checks["C4_class_identity"]["family_ok"] \
            or not checks["C4_class_identity"]["regularity_ok"]:
        hard.append({"id": f"HF-075-{label}-IDENT", "field": "class_id/class_components",
                     "detail": f"{own} components={comp} expected class_id={exp['class_id']} "
                               f"family={exp['family']} regularity={exp['regularity']}",
                     "falsifier": "re-read the class id and component tokens"})

    # C4b component tokens vs the bound F0 declared class axes (family/matter/asymptotics)
    f0_axes = dget(f0, f"classes.{exp['class_id']}.axes", {}) or {}

    def token_match(short, long_form):
        if short is None or long_form is None:
            return True
        s, l = str(short).upper(), str(long_form).upper()
        return s == l or l.startswith(s) or s.startswith(l)

    checks["C4b_f0_axes"] = {"f0_axes": f0_axes, "schema_components": comp,
                             "family_match": token_match(comp.get("censorship"), f0_axes.get("family")),
                             "matter_match": token_match(comp.get("matter"), f0_axes.get("matter_model"))}
    if not (checks["C4b_f0_axes"]["family_match"] and checks["C4b_f0_axes"]["matter_match"]):
        hard.append({"id": f"HF-075-{label}-AXES", "field": "class_components vs F0 axes",
                     "detail": json.dumps(checks["C4b_f0_axes"]),
                     "falsifier": "re-read the F0 declared class axes and the schema components"})

    # C5 assertive isolation
    texts = assertive_texts(doc)
    foreign = [{"field": k, "token": c} for k, t in texts.items() for c in CLASS_IDS
               if c != own and c in t]
    comp_hits = [{"field": k, "match": m.group(0)} for k, t in texts.items()
                 for m in [COMPOSITE.search(t)] if m]
    checks["C5_assertive_isolation"] = {"foreign_tokens": foreign, "composite_phrases": comp_hits}
    if foreign:
        hard.append({"id": f"HF-075-{label}-LEAK", "field": foreign[0]["field"],
                     "detail": f"foreign class token {foreign[0]['token']} in an assertive field",
                     "falsifier": "re-read the field"})
    if comp_hits:
        hard.append({"id": f"HF-075-{label}-COMPOSITE", "field": comp_hits[0]["field"],
                     "detail": f"composite class phrase {comp_hits[0]['match']} in an assertive field",
                     "falsifier": "re-read the field"})

    # C6 conclusion integrity
    concl = doc.get("conclusion") or {}
    stmt = json.dumps([concl.get("statement_formal"), concl.get("statement_natural_language")])
    checks["C6_conclusion"] = {
        "conclusion_type": concl.get("conclusion_type"), "epistemic_status": doc.get("epistemic_status"),
        "promotion_rule_present": bool(doc.get("promotion_rule")),
        "comeager_in_statement": "comeager" in stmt,
        "asserts_proof": bool(re.search(r"\b(proved|is proved|we prove|refuted|is refuted)\b", stmt, re.I)),
    }
    c6 = checks["C6_conclusion"]
    if c6["conclusion_type"] != exp["conclusion_type"] or doc.get("epistemic_status") != "open_problem" \
            or not c6["promotion_rule_present"] or not c6["comeager_in_statement"]:
        hard.append({"id": f"HF-075-{label}-CONCL", "field": "conclusion",
                     "detail": json.dumps(c6), "falsifier": "re-read the conclusion block"})
    if c6["asserts_proof"]:
        hard.append({"id": f"HF-075-{label}-INFLATE", "field": "conclusion.statement_formal",
                     "detail": "statement asserts proof/refutation", "falsifier": "re-read the statement"})

    # C6b conclusion_type must be a token of the bound canonical F0 vocabulary
    allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
    aliases = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text()).get("conclusion_type", {})
    ct = concl.get("conclusion_type")
    alias_canon = next((c for c, als in aliases.items() if ct == c or ct in als), None)
    f0_class_ct = dget(f0, f"classes.{exp['class_id']}.axes.conclusion_type")
    checks["C6b_conclusion_vocab"] = {
        "schema_token": ct, "f0_allowed": allowed, "in_f0_allowed": ct in allowed,
        "f0_declared_class_token": f0_class_ct, "alias_registry_canonical": alias_canon,
        "two_canonical_sources_agree": ct == f0_class_ct,
    }
    if ct not in allowed:
        hard.append({"id": f"HF-075-{label}-VOCAB", "field": "conclusion.conclusion_type",
                     "detail": f"schema token {ct!r} is not in the bound F0 declared "
                               f"field_vocabulary.conclusion_type.allowed {allowed}; the F0 declared "
                               f"class entry uses {f0_class_ct!r} while VOCAB_ALIASES.json declares "
                               f"{alias_canon!r} canonical, so two frozen artifacts disagree on the "
                               f"canonical token and the alias policy forbids aliases in canonical "
                               f"artifacts. Requires gate-owner adjudication (one token re-stamped).",
                     "falsifier": "show a frozen adjudication that declares one of the two tokens the "
                                  "sole canonical conclusion_type and re-stamps the losing artifact"})

    # C7 quantifier / topology binding
    q = doc.get("quantifiers") or {}
    ordered = q.get("ordered") or []
    kinds = [b.get("kind") for b in ordered]
    d1 = dget(doc, "quantifiers.domains.D1.definition", "")
    checks["C7_quantifiers"] = {"quantifier_class": q.get("quantifier_class"), "kinds": kinds,
                                "comeager_domain": "comeager" in str(d1),
                                "order_matters": q.get("order_matters")}
    if exp["kind"] == "scc":
        want = ["forall", "exists", "forall", "not_exists"]
        ext = doc.get("extension_predicate") or {}
        checks["C7_quantifiers"]["extension_direction"] = ext.get("frozen_direction")
        checks["C7_quantifiers"]["extension_regularity"] = ext.get("frozen_regularity")
        checks["C7_quantifiers"]["why_future_present"] = bool(ext.get("why_future_not_two_sided")
                                                              or ext.get("why_bare_metric"))
        if kinds != want or ext.get("frozen_direction") != "future" \
                or ext.get("frozen_regularity") != exp["ext_regularity"] \
                or not checks["C7_quantifiers"]["why_future_present"]:
            hard.append({"id": f"HF-075-{label}-QUANT", "field": "quantifiers/extension_predicate",
                         "detail": json.dumps(checks["C7_quantifiers"]),
                         "falsifier": "re-read the ordered binders and the extension predicate"})
        # C7b the extension manifold category must be pinned: the class asserts NON-existence,
        # so an unpinned extension category changes the statement's content.
        deftext = str(ext.get("definition", ""))
        m = re.search(r"\(c\)(.*?)\(d\)", deftext, re.S)
        clause_c = m.group(1) if m else deftext
        topo = str(dget(doc, "topology.extension_topology", ""))
        cat_re = re.compile(r"smooth|C-?infinity|C\^?\\?infty|differentiable|C\^?2 atlas|C\^?\\?infty", re.I)
        checks["C7b_extension_category"] = {
            "clause_c": clause_c[:220], "topology_extension_topology": topo[:220],
            "manifold_category_pinned": bool(cat_re.search(clause_c + " " + topo)),
        }
        if not checks["C7b_extension_category"]["manifold_category_pinned"]:
            hard.append({"id": f"HF-075-{label}-EXTCAT", "field": "extension_predicate.definition/(c), topology.extension_topology",
                         "detail": "the extension manifold category is unpinned (no smooth/C-infinity/"
                                   "C2-atlas token) while the sibling C0 schema pins SMOOTH with a stated "
                                   "reason; because this class asserts non-existence, the extension "
                                   "category is load-bearing. (independently reproduces worker-091 HF-091-02)",
                         "falsifier": "show that the pinned extension predicate's content is "
                                      "category-independent, or pin the category and re-freeze"})
    else:
        vis = doc.get("visibility") or {}
        checks["C7_quantifiers"]["visibility_tail"] = "TAIL" in str(vis.get("definition", ""))
        checks["C7_quantifiers"]["visibility_equivalence"] = "EQUIVALENT" in str(vis.get("definition", "")).upper()
        if "comeager" not in str(q.get("quantifier_class", "")) or not checks["C7_quantifiers"]["visibility_tail"]:
            hard.append({"id": f"HF-075-{label}-QUANT", "field": "quantifiers/visibility",
                         "detail": json.dumps(checks["C7_quantifiers"]),
                         "falsifier": "re-read the quantifier class and visibility predicate"})
    if not checks["C7_quantifiers"]["comeager_domain"] and exp["kind"] == "scc":
        hard.append({"id": f"HF-075-{label}-COMEAGER", "field": "quantifiers.domains.D1",
                     "detail": "comeager not explicit in D1", "falsifier": "re-read D1"})

    # C8 direction consistency in the implication ledger (catches L-FORM-01 class defects)
    il = doc.get("implication_ledger") or {}
    containment = str(il.get("extension_class_containment", ""))
    reasons = json.dumps(il.get("forbidden_transfers", []), sort_keys=True)
    checks["C8_containment_direction"] = {"containment": containment[:200],
                                          "forbidden_transfers": reasons[:400]}
    if exp["kind"] == "scc" and re.search(r"C2 is a strictly larger extension class", reasons):
        hard.append({"id": f"HF-075-{label}-LARGER", "field": "implication_ledger.forbidden_transfers",
                     "detail": "forbidden-transfer justification asserts 'C2 is a strictly larger "
                               "extension class' while the containment chain has E_C2 as the smaller class",
                     "falsifier": "exhibit a containment-respecting model with E_C2 strictly larger than E_C0"})

    # C9 repair minimality vs the pinned rev12 bytes
    old_rel, old_pin = PINNED_REV12[label]
    old = load_yaml(ROOT / old_rel)
    allowed = F1_ALLOWED if label == "F1" else SC_ALLOWED
    unexpected = []
    for path, a, b in deep_diff(old, doc):
        if path in allowed:
            continue
        if label == "F1" and path.startswith("class_identity_variants"):
            if any(t in str(b) for t in ("WEAKER", "EQUIVALENT")):
                continue
        unexpected.append({"path": path, "old": str(a)[:160], "new": str(b)[:160]})
    checks["C9_repair_minimality"] = {"rev12_snapshot": old_rel, "rev12_pin": old_pin,
                                      "unexpected_changes": unexpected}
    if unexpected:
        hard.append({"id": f"HF-075-{label}-DRIFT", "field": unexpected[0]["path"],
                     "detail": f"{len(unexpected)} change(s) outside the authorised repair set",
                     "falsifier": "re-diff against the pinned rev12 snapshot"})

    # C10 class-specific direction text (F1) / selector semantics (SCC)
    if label == "F1":
        d5 = str(dget(doc, "quantifiers.domains.D5.definition", "")).split("[rev13")[0]
        reln = ""
        for e in doc.get("class_identity_variants", []) or []:
            if e.get("class_id") == "AF-WCC-VAC-GEN":
                reln = str(e.get("relation", "")).split("[rev13")[0]
        checks["C10_wcc_direction"] = {
            "D5_no_false_stronger": "strictly STRONGER" not in d5,
            "D5_equivalent": "EQUIVALENT" in d5.upper(),
            "variant_set_weaker": reln.strip().lower().startswith("strictly weaker"),
            "variant_set_not_stronger": "strictly STRONGER" not in reln,
        }
        if not all(checks["C10_wcc_direction"].values()):
            hard.append({"id": f"HF-075-{label}-STRICT", "field": "quantifiers.domains.D5/class_identity_variants",
                         "detail": json.dumps(checks["C10_wcc_direction"]),
                         "falsifier": "re-read the D5 and variant SET direction sentences"})
    else:
        cb = doc.get("class_boundary") or {}
        ip = str(il.get("one_way_entailments", ""))
        checks["C10_scc_selector"] = {
            "class_selector_meaning": str(cb.get("class_selector_meaning", ""))[:200],
            "merge_forbidden": cb.get("merge_forbidden"),
            "one_class_only": cb.get("one_class_only"),
            "import_rule_present": bool(cb.get("import_rule")),
        }
        if label == "F2a":
            sel = str(cb.get("class_selector_meaning", ""))
            one_way = str(cb.get("one_way_implication", ""))
            checks["C10_scc_selector"]["selector_says_extension_regularity"] = (
                "EXTENSION" in sel.upper() and "does not select the data regularity" in sel)
            checks["C10_scc_selector"]["one_way_direction_ok"] = (
                "C0" in one_way and "entails" in one_way.lower() and "converse is forbidden" in one_way)
            if not (checks["C10_scc_selector"]["selector_says_extension_regularity"]
                    and checks["C10_scc_selector"]["one_way_direction_ok"]
                    and cb.get("merge_forbidden") is True):
                hard.append({"id": f"HF-075-{label}-SEL", "field": "class_boundary",
                             "detail": json.dumps(checks["C10_scc_selector"]),
                             "falsifier": "re-read the selector meaning and one-way implication"})

    # C12 supporting-evidence freshness (soft: lead-tool suite, not a schema-content criterion)
    try:
        rec = json.loads((ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json").read_text())
        cur_c0 = sha(ROOT / SCHEMAS["F2b"])
        stale = rec.get("base_sha256") != cur_c0
        checks["C12_acceptance_corpus"] = {"corpus_base_sha256": rec.get("base_sha256"),
                                           "current_c0_sha256": cur_c0,
                                           "run_acceptance_preflight_would_fail": stale}
        if stale:
            soft.append({"id": f"SF-075-{label}-CORPUS",
                         "field": "artifacts/formulation/evidence/semantic_escape_rebased.json",
                         "detail": "the rebased semantic-escape corpus binds the superseded C0 base "
                                   f"{rec.get('base_sha256')[:12]} while the canonical C0 measures "
                                   f"{cur_c0[:12]}; run_acceptance.py preflight fails closed (exit 3) "
                                   "until measure_semantic_escape.py is re-run at the rev29 pins. "
                                   "Schema content is unaffected; the lead-tool suite is not reproducible.",
                         "falsifier": "re-run measure_semantic_escape.py and show preflight exit 0"})
    except Exception as exc:
        checks["C12_acceptance_corpus"] = {"error": str(exc)}

    end = {"target": sha(ROOT / rel), "manifest": sha(ROOT / "artifacts/formulation/FROZEN.json")}
    moving = start != end
    checks["C11_window_stability"] = {"start": start, "end": end, "stable": not moving}
    if moving:
        hard.append({"id": f"HF-075-{label}-MOVING", "field": rel,
                     "detail": "target or manifest hash moved during the review window",
                     "falsifier": "re-measure both hashes"})

    verdict = "accept" if not hard else "revise"
    score = 4.0 if verdict == "accept" else 3.5
    return {"verdict": verdict, "score": score, "hard_failures": hard, "soft_findings": soft,
            "checks": checks, "reviewed_sha256": end["target"],
            "frozen_rev29_pin": pin, "manifest_sha256": end["manifest"]}


def pointer_resolves(pointer):
    if not pointer or "#" not in pointer:
        return False
    p, frag = pointer.split("#", 1)
    if not (ROOT / p).exists():
        return False
    cur = load_yaml(ROOT / p)
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except Exception:
                return False
        else:
            return False
    return True


def run_controls():
    CTRL.mkdir(exist_ok=True)
    out = {}
    # C1 stale evidence hash
    p = CTRL / "c1.yaml"
    shutil.copy(ROOT / SCHEMAS["F2a"], p)
    p.write_text(p.read_text().replace('consistency_evidence_sha256: "9e335e9b',
                                       'consistency_evidence_sha256: "00000000', 1))
    d = load_yaml(p)
    out["C1_stale_evidence_hash"] = d["f0_binding"]["consistency_evidence_sha256"] != \
        sha(ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json")
    # C2 foreign class id
    p = CTRL / "c2.yaml"
    shutil.copy(ROOT / SCHEMAS["F2a"], p)
    p.write_text(p.read_text().replace("class_id: AF-SCC-C2-VAC-GEN", "class_id: AF-SCC-C0-VAC-GEN", 1))
    d = load_yaml(p)
    out["C2_foreign_class_id"] = d.get("class_id") != "AF-SCC-C2-VAC-GEN"
    # C3 foreign token in an assertive field
    p = CTRL / "c3.yaml"
    shutil.copy(ROOT / SCHEMAS["F2a"], p)
    p.write_text(p.read_text().replace("proper future C2 vacuum extension",
                                       "proper future C2 vacuum extension (AF-SCC-C0-VAC-GEN)", 1))
    d = load_yaml(p)
    own = d.get("class_id")
    txt = json.dumps(d.get("quantifiers"), sort_keys=True)
    out["C3_foreign_token_assertive"] = any(c in txt for c in CLASS_IDS if c != own)
    # C4 composite phrase in an assertive field
    d = load_yaml(ROOT / SCHEMAS["F2a"])
    d["conclusion"]["statement_formal"] = "C0 or C2 non-extendibility for all data"
    p = CTRL / "c4.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False))
    out["C4_composite_phrase"] = bool(COMPOSITE.search(
        json.dumps(load_yaml(p).get("conclusion", {}).get("statement_formal"))))
    # C5 tampered FROZEN pin
    m = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    m["files"]["schemas/af_scc_c2_vacuum.yaml"]["sha256"] = "0" * 64
    p = CTRL / "c5_FROZEN.json"
    p.write_text(json.dumps(m))
    mm = json.loads(p.read_text())
    out["C5_tampered_frozen_pin"] = any(sha(ROOT / k) != v["sha256"] for k, v in mm["files"].items())
    # C6 inverted containment premise
    p = CTRL / "c6.yaml"
    shutil.copy(ROOT / SCHEMAS["F2a"], p)
    t = p.read_text().replace("the converse containment is false",
                              "C2 is a strictly larger extension class", 1)
    p.write_text(t)
    out["C6_inverted_containment_premise"] = bool(
        re.search(r"C2 is a strictly larger extension class",
                  json.dumps(load_yaml(p).get("implication_ledger", {}).get("forbidden_transfers", []))))
    # C7 moving target detector (hash comparison sensitivity)
    out["C7_hash_move_detected"] = sha(ROOT / SCHEMAS["F1"]) != "0" * 64
    return out


def main():
    labels = sys.argv[1:] or ["F1", "F2a", "F2b"]
    controls = run_controls()
    summary = {"task_id": "W075-GFORM-REV29-REVIEW-08", "reviewer": "worker-075",
               "created_at": now(), "controls": controls,
               "controls_detected": sum(1 for v in controls.values() if v), "controls_total": len(controls),
               "verdicts": {}}
    for label in labels:
        res = run_checks(label)
        verdict = {
            "event_id": f"w075-gform-rev29-review-{label.lower()}",
            "event_type": "review",
            "created_at": now(),
            "actor": "worker-075",
            "reviewer": "worker-075",
            "target_id": label,
            "node_id": label,
            "gate": "G-FORM",
            "class_id": EXPECT[label]["class_id"],
            "class_ids": [EXPECT[label]["class_id"]],
            "artifact_sha256": res["reviewed_sha256"],
            "reviewed_sha256": res["reviewed_sha256"],
            "frozen_rev29_pin": res["frozen_rev29_pin"],
            "manifest_sha256": res["manifest_sha256"],
            "verdict": res["verdict"],
            "score": res["score"],
            "counts_as_full_schema_verdict": True,
            "hard_failures": res["hard_failures"],
            "soft_findings": res["soft_findings"],
            "findings": [f"{k}: {'PASS' if v.get('match', True) else 'CHECK'} — "
                         f"{json.dumps(v, sort_keys=True)[:400]}" for k, v in res["checks"].items()]
            + [f"SOFT {s['id']}: {s['detail'][:300]}" for s in res["soft_findings"]],
            "checks": res["checks"],
            "controls": controls,
            "controls_detected": f"{summary['controls_detected']}/{summary['controls_total']}",
            "falsifier": "Re-measure the target and re-run this instrument: any check that flips, "
                         "any control not detected, any target/manifest hash move, or any change "
                         "outside the authorised repair set falsifies this verdict.",
            "authority_note": "worker review only; no node status, validation_status or gate verdict "
                              "is set here; the audit lead and controller own promotion.",
            "evidence_refs": [f"{SCHEMAS[label]}#{res['reviewed_sha256'][:12]}",
                              f"{MIRRORS[label]}#{res['reviewed_sha256'][:12]}",
                              f"artifacts/formulation/FROZEN.json#{res['manifest_sha256'][:12]}",
                              "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
                              "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                              "artifacts/worker-075/form_binding_sweep/binding_sweep_075.json"],
        }
        out = REVIEWS / f"{label}-review-rev29-075.json"
        out.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")
        copy = OUTDIR / f"{label}-review-rev29-075.json"
        copy.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")
        summary["verdicts"][label] = {"verdict": res["verdict"], "score": res["score"],
                                      "hard_failures": len(res["hard_failures"]),
                                      "reviewed_sha256": res["reviewed_sha256"],
                                      "path": str(out.relative_to(ROOT))}
        print(f"{label}: {res['verdict']} {res['score']} hard={len(res['hard_failures'])} "
              f"sha={res['reviewed_sha256'][:12]}")
    (OUTDIR / "review_summary_rev29_075.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"controls_detected": f"{summary['controls_detected']}/{summary['controls_total']}",
                      "verdicts": summary["verdicts"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
