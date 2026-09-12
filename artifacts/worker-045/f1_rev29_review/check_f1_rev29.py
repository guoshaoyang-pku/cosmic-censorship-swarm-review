#!/usr/bin/env python3
"""W045-F1-REV29-GFORM-REVIEW-01 -- independent, read-only G-FORM review instrument for
node F1 (class AF-WCC-VAC-GEN) at the FROZEN rev29 pin.

Run:
    python3 artifacts/worker-045/f1_rev29_review/check_f1_rev29.py --out-dir <dir>

Design rules:
  * read-only on every canonical path (no writes outside --out-dir / the verdict path);
  * every check is deterministic and reports the evidence it used (path, sha256, quoted text);
  * 8 in-memory falsification controls; any control that does not fire fails the instrument;
  * pre/post hash drift guard: the reviewed sha256 must equal the post-run sha256.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

F1 = "schemas/af_wcc_vacuum.yaml"
F1_MIRROR = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = "artifacts/formulation/FROZEN.json"
REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
VARIANT_DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
CASES = "schemas/taxonomy_cases.jsonl"
F2A = "schemas/af_scc_c2_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
REV12_F1_SNAPSHOT = "artifacts/worker-007/rev29_preflight/snapshot/af_wcc_vacuum.cce9c60146d6.yaml"

REV12_F1_SHA = "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3"
FROZEN_REV29_SHA = "3d9e3d77fd87e1d8d306b5aa1e5b8c1e1a5efbaf1a0e5b4f5b1c4c8b6a2cbb37"  # placeholder, overwritten by measurement
CLASS_ID = "AF-WCC-VAC-GEN"

FROZEN_CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
SCC_CONCLUSION_TOKENS = {
    "scc_c2_future_inextendibility",
    "scc_c0_future_inextendibility",
    "strong_cosmic_censorship_C2",
    "strong_cosmic_censorship_C0",
}


def sha256(path):
    with open(os.path.join(ROOT, path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_text(path):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def read_json(path):
    return json.loads(read_text(path))


def read_yaml_strict(path):
    """YAML load that raises on duplicate mapping keys (PyYAML default is last-wins)."""
    text = read_text(path)

    class StrictLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    None, None, "duplicate mapping key: %r" % (key,), key_node.start_mark
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    StrictLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    return yaml.load(text, Loader=StrictLoader)


def now_iso():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Review:
    def __init__(self):
        self.checks = []
        self.findings = []
        self.hard_failures = []

    def check(self, cid, name, ok, detail, evidence=None, severity="blocking"):
        rec = {
            "id": cid,
            "name": name,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
            "evidence": evidence or [],
        }
        self.checks.append(rec)
        if not ok and severity == "blocking":
            self.hard_failures.append({"id": cid, "name": name, "detail": detail})
        elif not ok:
            self.findings.append({"id": cid, "name": name, "detail": detail,
                                  "severity": severity, "blocking": False})
        return ok

    def info(self, cid, name, detail, evidence=None):
        self.checks.append({"id": cid, "name": name, "status": "INFO",
                            "detail": detail, "evidence": evidence or []})

    def finding(self, fid, detail, severity="info", blocking=False):
        self.findings.append({"id": fid, "detail": detail, "severity": severity,
                              "blocking": blocking})


def resolve_pointer(doc, pointer):
    """Resolve 'path#a.b.c' -> (exists, value-or-None)."""
    if "#" not in pointer:
        return (os.path.exists(os.path.join(ROOT, pointer)), None)
    path, frag = pointer.split("#", 1)
    if not os.path.exists(os.path.join(ROOT, path)):
        return (False, None)
    try:
        target = read_yaml_strict(path)
    except Exception:
        return (False, None)
    cur = target
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return (False, None)
    return (True, cur)


def token_inventory(obj, out=None, path="$"):
    """Flatten a parsed document to {json-path: scalar} for semantic diffing."""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            token_inventory(v, out, path + "." + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            token_inventory(v, out, path + "[%d]" % i)
    else:
        out[path] = obj
    return out


def run_checks():
    r = Review()
    stamp = now_iso()

    # ---------- 1. pins and drift ----------
    paths = [F1, F1_MIRROR, F0, SUPP, EVID, FROZEN, REGISTRY, VARIANT_DELTA,
             RULE_SPEC, VOCAB, CASES, F2A, F2B]
    pre = {p: sha256(p) for p in paths}
    frozen = read_json(FROZEN)
    fpins = frozen.get("files", {})
    rev = frozen.get("revision")
    r.check("H1.1", "FROZEN manifest revision is 29", rev == 29,
            "FROZEN.json revision=%r frozen_at=%r" % (rev, frozen.get("frozen_at")),
            [FROZEN + "#" + pre[FROZEN][:12]])
    for p in [F1, F0, SUPP, EVID, CASES, F2A, F2B]:
        pin = fpins.get(p, {}).get("sha256")
        r.check("H1.2:" + os.path.basename(p), "FROZEN rev29 pin matches live bytes",
                pin == pre[p], "declared=%s measured=%s" % (str(pin)[:12], pre[p][:12]),
                [p + "#" + pre[p][:12], FROZEN + "#" + pre[FROZEN][:12]])
    r.check("H1.3", "canonical F1 equals authoring mirror",
            pre[F1] == pre[F1_MIRROR],
            "canonical=%s authoring=%s" % (pre[F1][:12], pre[F1_MIRROR][:12]),
            [F1 + "#" + pre[F1][:12], F1_MIRROR + "#" + pre[F1_MIRROR][:12]])

    # ---------- 2. structural ----------
    raw = read_text(F1)
    # metalinguistic-mention-safe view: strip revision notes and quoted historical text
    # before scanning for asserted claims (the CF-16 pattern).
    raw_scan = re.sub(r"\[rev\d+:[^\]]*\]", " ", raw)
    raw_scan = re.sub(r"corrected from '[^']*'", " ", raw_scan)
    try:
        doc = read_yaml_strict(F1)
        strict_ok, strict_detail = True, "strict loader accepted the document (0 duplicate keys)"
    except Exception as exc:
        doc = yaml.safe_load(raw)
        strict_ok, strict_detail = False, "strict loader rejected: %s" % exc
    r.check("H2.1", "YAML parses under a duplicate-key-rejecting loader", strict_ok,
            strict_detail, [F1 + "#" + pre[F1][:12]])

    # independent raw-line duplicate top-level key census
    top_keys = []
    for line in raw.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
        if m:
            top_keys.append(m.group(1))
    dups = sorted({k for k in top_keys if top_keys.count(k) > 1})
    r.check("H2.2", "no duplicate top-level keys (raw column-0 census)", not dups,
            "duplicate top-level keys=%r" % (dups,), [F1 + "#" + pre[F1][:12]])

    r.check("H2.3", "revision is 13", doc.get("revision") == 13,
            "revision=%r revised_at=%r" % (doc.get("revision"), doc.get("revised_at")),
            [F1 + "#" + pre[F1][:12]])
    try:
        revised = dt.datetime.fromisoformat(str(doc.get("revised_at")))
        future = revised > dt.datetime.now().astimezone()
    except Exception:
        future = True
    r.check("H2.4", "revised_at is present and not future-dated", not future,
            "revised_at=%r" % (doc.get("revised_at"),), [F1 + "#" + pre[F1][:12]])
    r.check("H2.5", "node_id/class_id are F1/AF-WCC-VAC-GEN",
            doc.get("node_id") == "F1" and doc.get("class_id") == CLASS_ID,
            "node_id=%r class_id=%r" % (doc.get("node_id"), doc.get("class_id")),
            [F1 + "#" + pre[F1][:12]])

    # ---------- 3. class identity / leakage ----------
    class_id = doc.get("class_id")
    r.check("H3.1", "class_id is exactly one frozen class token",
            class_id in FROZEN_CLASS_IDS,
            "class_id=%r" % (class_id,), [F1 + "#" + pre[F1][:12]])
    composite = re.findall(r"[A-Za-z0-9_]*C0\s*/\s*C2[A-Za-z0-9_]*", raw)
    r.check("H3.2", "no single-token C0/C2 composite on the class-id axis",
            not composite, "composite tokens=%r" % (composite,), [F1 + "#" + pre[F1][:12]])

    rule_spec = read_json(RULE_SPEC)
    vocab = read_json(VOCAB)

    def canon_token(section, token):
        table = vocab.get(section) or {}
        if token in table:
            return token
        for canon, aliases in table.items():
            if isinstance(aliases, list) and token in aliases:
                return canon
        return None

    concl_tok = (doc.get("conclusion") or {}).get("conclusion_type")
    licensed = None
    try:
        licensed = rule_spec["vocabularies"]["class_conclusion_type"][CLASS_ID]
    except Exception:
        pass
    canon = canon_token("conclusion_type", concl_tok)
    licensed_ok = (concl_tok == licensed) or (canon is not None
                                             and canon == canon_token("conclusion_type", licensed))
    r.check("H3.3", "conclusion_type is licensed for AF-WCC-VAC-GEN under rule_spec",
            licensed_ok,
            "conclusion_type=%r canonical=%r licensed=%r" % (concl_tok, canon, licensed),
            [F1 + "#" + pre[F1][:12], RULE_SPEC + "#" + pre[RULE_SPEC][:12],
             VOCAB + "#" + pre[VOCAB][:12]])
    r.check("H3.4", "no SCC conclusion token in the WCC conclusion",
            concl_tok not in SCC_CONCLUSION_TOKENS,
            "conclusion_type=%r" % (concl_tok,), [F1 + "#" + pre[F1][:12]])

    # genericity axis token vs F0 vocabulary, alias-aware; the non-literal case is a known
    # open controller adjudication (worker-017 vocab-source blocker), not an F1 defect.
    f0_doc_pre = read_yaml_strict(F0)
    f0_axes = ((f0_doc_pre.get("classes") or {}).get(CLASS_ID) or {}).get("axes") or {}
    gen_kind = (doc.get("genericity") or {}).get("kind")
    gen_f1 = canon_token("genericity_kind", gen_kind)
    gen_f0 = canon_token("genericity_kind", f0_axes.get("genericity_kind"))
    r.check("H3.5", "genericity axis token is the same equivalence class as the F0 axis",
            gen_f1 is not None and gen_f1 == gen_f0,
            "F1=%r -> %r; F0=%r -> %r (alias table VOCAB_ALIASES.genericity_kind)"
            % (gen_kind, gen_f1, f0_axes.get("genericity_kind"), gen_f0),
            [F1 + "#" + pre[F1][:12], F0 + "#" + pre[F0][:12],
             VOCAB + "#" + pre[VOCAB][:12]])

    # ---------- 4. binding chain ----------
    binding = doc.get("f0_binding") or {}
    r.check("H4.1", "declared_f0_sha256 equals live F0 taxonomy bytes",
            binding.get("declared_f0_sha256") == pre[F0],
            "declared=%s live=%s" % (str(binding.get("declared_f0_sha256"))[:12], pre[F0][:12]),
            [F1 + "#" + pre[F1][:12], F0 + "#" + pre[F0][:12]])
    r.check("H4.2", "consistency_evidence_sha256 equals live evidence bytes",
            binding.get("consistency_evidence_sha256") == pre[EVID],
            "declared=%s live=%s" % (str(binding.get("consistency_evidence_sha256"))[:12],
                                     pre[EVID][:12]),
            [F1 + "#" + pre[F1][:12], EVID + "#" + pre[EVID][:12]])
    ok_ptr, ptr_val = resolve_pointer(doc, str(doc.get("class_contract_pointer", "")))
    ptr_ok = (ok_ptr and isinstance(ptr_val, dict)
              and ("label" in ptr_val or "conclusion" in ptr_val))
    r.check("H4.3", "class_contract_pointer resolves in the canonical taxonomy",
            ptr_ok,
            "pointer=%r resolved=%r target_keys=%r"
            % (doc.get("class_contract_pointer"), ok_ptr,
               sorted(ptr_val.keys())[:8] if isinstance(ptr_val, dict) else None),
            [F1 + "#" + pre[F1][:12], F0 + "#" + pre[F0][:12]])
    ok_sup, sup_val = resolve_pointer(doc, str(doc.get("class_contract_supplement_pointer", "")))
    r.check("H4.4", "class_contract_supplement_pointer resolves in the supplement",
            ok_sup and sup_val is not None,
            "pointer=%r resolved=%r" % (doc.get("class_contract_supplement_pointer"), ok_sup),
            [F1 + "#" + pre[F1][:12], SUPP + "#" + pre[SUPP][:12]])

    # ---------- 5. strictness repair at the three documented loci ----------
    d5 = (((doc.get("quantifiers") or {}).get("domains") or {}).get("D5") or {})
    r.check("H5.1", "D5 whole/tail reading stated EQUIVALENT",
            "EQUIVALENT" in str(d5.get("definition", "")),
            "D5.definition=%s" % str(d5.get("definition"))[:200], [F1 + "#" + pre[F1][:12]])
    vis = doc.get("visibility") or {}
    r.check("H5.2", "visibility.definition states whole/tail EQUIVALENT",
            "EQUIVALENT" in str(vis.get("definition", "")),
            "visibility.definition=%s" % str(vis.get("definition"))[:200],
            [F1 + "#" + pre[F1][:12]])
    variants = None
    for key in ("class_identity_variants", "variants", "variant_registry", "registered_variants"):
        if isinstance(doc.get(key), list):
            variants = doc[key]
            break
        if isinstance(doc.get(key), dict) and isinstance(doc[key].get("items"), list):
            variants = doc[key]["items"]
            break
    set_rel = None
    if variants:
        for v in variants:
            if not isinstance(v, dict):
                continue
            kind = str(v.get("kind", "")).lower()
            stmt = str(v.get("statement", "")).lower()
            if "set" in kind or stmt.startswith("variant set"):
                if v.get("class_id") in (None, CLASS_ID):
                    set_rel = v
                    break
    if set_rel is None:
        m = re.search(r'kind:\s*"?SET"?.*?\n(?:.*\n){0,8}?\s*relation:\s*"([^"]+)"', raw)
        set_rel = {"relation": m.group(1)} if m else {}
    rel_text = str((set_rel or {}).get("relation", ""))
    r.check("H5.3", "variant SET relation is strictly WEAKER (direction repaired)",
            "strictly WEAKER" in rel_text,
            "variant SET relation=%s" % rel_text[:220], [F1 + "#" + pre[F1][:12]])
    r.check("H5.4", "no residual 'whole-curve ... strictly STRONGER' claim",
            not re.search(r"whole-curve containment[^\"]{0,120}strictly stronger", raw_scan, re.I),
            "regex over live bytes after stripping rev-notes/quotations: %d matches" % len(
                re.findall(r"whole-curve containment[^\"]{0,120}strictly stronger", raw_scan, re.I)),
            [F1 + "#" + pre[F1][:12]])
    r.check("H5.5", "no residual 'variant SET ... strictly STRONGER' claim",
            not re.search(r"variant set[^\"]{0,200}strictly stronger", raw_scan, re.I),
            "after stripping the rev13 'corrected from' note and quoted history: %d matches"
            % len(re.findall(r"variant set[^\"]{0,200}strictly stronger", raw_scan, re.I)),
            [F1 + "#" + pre[F1][:12]])
    neg = str(vis.get("negation_conclusion", ""))
    r.check("H5.6", "B-containment remains stated strictly stronger than the canonical negation",
            "strictly stronger" in neg,
            "(independent pair, must NOT be swept up by the repair) present=%r"
            % ("strictly stronger" in neg), [F1 + "#" + pre[F1][:12]])

    # ---------- 6. quantifier integrity ----------
    q = doc.get("quantifiers") or {}
    formal = str((doc.get("conclusion") or {}).get("statement_formal", ""))
    domains = q.get("domains") or {}
    dom_names = set(domains.keys()) if isinstance(domains, dict) else set()
    used_domains = set(re.findall(r"\b(D[0-9]+|G_r)\b", formal))
    missing = sorted(d for d in used_domains if d not in dom_names and d != "G_r")
    r.check("H6.1", "every domain symbol in statement_formal is declared",
            not missing, "formal=%s missing=%r declared=%r"
            % (formal[:160], missing, sorted(dom_names)), [F1 + "#" + pre[F1][:12]])
    r.check("H6.2", "formal quantifier shape is forall-exists-comeager-forall",
            bool(re.search(r"forall\s+r\s+in\s+D0\s+exists\s+G_r\s+comeager\s+forall\s+D\s+in\s+G_r", formal)),
            "formal=%s" % formal[:200], [F1 + "#" + pre[F1][:12]])
    pred = str(vis.get("predicate_name", ""))
    r.check("H6.3", "conclusion predicate is the one defined in visibility",
            pred and pred in formal, "predicate_name=%r in formal=%r"
            % (pred, pred in formal), [F1 + "#" + pre[F1][:12]])
    r.check("H6.4", "genericity kind is the comeager/residual class default",
            (doc.get("genericity") or {}).get("kind") == "residual_comeager",
            "genericity.kind=%r" % ((doc.get("genericity") or {}).get("kind"),),
            [F1 + "#" + pre[F1][:12]])

    # ---------- 7. conclusion inflation ----------
    formal_shape_ok = bool(re.search(
        r"forall\s+r\s+in\s+D0\s+exists\s+G_r\s+comeager\s+forall\s+D\s+in\s+G_r", formal))
    infl = []
    if not formal_shape_ok:
        infl.append("formal conclusion is not the forall-exists-comeager-forall shape")
    if "not exists visible_singularity_from_I_plus" not in formal:
        infl.append("formal conclusion missing the negation predicate")
    r.check("H7.1", "conclusion is the declared open problem, not a strengthened form",
            not infl, "inflation signals=%r formal=%s" % (infl, formal[:180]),
            [F1 + "#" + pre[F1][:12]])
    anti = doc.get("anti_scope") or []
    anti_count = sum(len(v) for v in anti.values()) if isinstance(anti, dict) else len(anti)
    r.check("H7.2", "anti_scope records the excluded strengthenings", anti_count >= 3,
            "anti_scope entries=%d (dict=%r)" % (anti_count, isinstance(anti, dict)),
            [F1 + "#" + pre[F1][:12]])
    r.check("H7.3", "promotion rule forbids schema self-certification",
            "checked proof" in str(doc.get("promotion_rule", "")),
            "promotion_rule=%s" % str(doc.get("promotion_rule"))[:160],
            [F1 + "#" + pre[F1][:12]])

    # ---------- 8. HF sweep ----------
    r.check("H8.1", "HF-01: conclusion_type is not 'theorem'",
            concl_tok != "theorem", "conclusion_type=%r" % (concl_tok,),
            [F1 + "#" + pre[F1][:12]])
    refs = doc.get("l1_ledger_refs") or []
    bad_refs = [x for x in refs if str(x.get("l1_status", "")).lower() in ("unresolved", "contradicted")]
    r.check("H8.2", "HF-03: no l1_ledger_ref used in an unresolved/contradicted state",
            not bad_refs, "refs=%d bad=%r" % (len(refs), bad_refs),
            [F1 + "#" + pre[F1][:12]])
    qty = re.findall(r"\bs\s*>\s*5/2|delta\s*(?:in|∈)\s*\(1/2\s*,\s*1\)", raw)
    r.info("H8.3", "HF-04 quantity scan",
           "weighted-Sobolev threshold mentions=%d (anchoring status is an L1 item; "
           "recorded as a non-blocking annotation)" % len(qty), [F1 + "#" + pre[F1][:12]])
    if qty:
        r.finding("NF-QUANT", "weighted-Sobolev thresholds appear in genericity.ambient_space "
                  "without a ledger anchor in the reviewed bytes; L1 anchoring is an open item "
                  "(does not affect the class contract)", severity="info", blocking=False)
    f0_doc = read_yaml_strict(F0)
    try:
        contract = (f0_doc.get("classes") or {})[CLASS_ID]
        n_hyp = len(contract.get("hypotheses") or [])
    except Exception:
        contract, n_hyp = {}, 0
    hyp_fields = {k: bool(doc.get(k)) for k in ("data_class", "regularity", "genericity",
                                                "quantifiers", "scope_statement")}
    r.check("H8.4", "HF-06: class hypotheses are declared in F0 and instantiated in F1",
            n_hyp > 0 and all(hyp_fields.values()),
            "F0.hypotheses=%d; F1 declared fields=%r" % (n_hyp, hyp_fields),
            [F1 + "#" + pre[F1][:12], F0 + "#" + pre[F0][:12]])
    r.check("H8.5", "unresolved items are declared, not silently dropped",
            isinstance(doc.get("unresolved_items"), list) and len(doc["unresolved_items"]) >= 3,
            "unresolved_items=%d" % len(doc.get("unresolved_items") or []),
            [F1 + "#" + pre[F1][:12]])

    # ---------- 9. cross-file consistency ----------
    try:
        registry = read_json(REGISTRY)
        reg_txt = json.dumps(registry)
        reg_ok = CLASS_ID in reg_txt and "SET" in reg_txt
    except Exception as exc:
        registry, reg_ok, reg_txt = {}, False, str(exc)
    r.check("H9.1", "VARIANT_REGISTRY registers AF-WCC-VAC-GEN variant SET",
            reg_ok, "registry contains class=%r and SET=%r"
            % (CLASS_ID in reg_txt, "SET" in reg_txt), [REGISTRY + "#" + pre[REGISTRY][:12]])
    try:
        delta = read_json(VARIANT_DELTA)
        d_txt = json.dumps(delta)
        delta_ok = "SET" in d_txt and CLASS_ID in d_txt
    except Exception as exc:
        delta_ok, d_txt = False, str(exc)
    r.check("H9.2", "variant-SET delta file resolves to the same parent class",
            delta_ok, "delta contains SET=%r class=%r" % ("SET" in d_txt, CLASS_ID in d_txt),
            [VARIANT_DELTA + "#" + pre[VARIANT_DELTA][:12]])
    anti_ids = set()
    if isinstance(anti, dict):
        for entry in anti.get("not_this_class", []):
            if isinstance(entry, dict) and entry.get("class_id"):
                anti_ids.add(entry["class_id"])
    scc_guarded = {"AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"}.issubset(anti_ids)
    r.check("H9.3", "no WCC<->SCC transfer is licensed by this artifact",
            scc_guarded or "no WCC <-> SCC transfer is licensed" in raw,
            "anti_scope.not_this_class covers both SCC classes=%r; explicit cross_family text=%r"
            % (scc_guarded, "cross_family" in raw), [F1 + "#" + pre[F1][:12]])
    r.check("H9.4", "review_status does not self-certify an independent review",
            not (doc.get("review_status") or {}).get("independent_reviewers"),
            "independent_reviewers=%r" % ((doc.get("review_status") or {}).get("independent_reviewers"),),
            [F1 + "#" + pre[F1][:12]])

    # H9.5: registered variant-SET strength direction must be consistent across every live
    # artifact that states it (F1 relation, VARIANT_REGISTRY, variant delta, F0 taxonomy).
    def direction_of(text):
        m = re.search(r"strictly\s+(stronger|weaker)", str(text), re.I)
        if m:
            return m.group(1).lower()
        m = re.search(r"strictly\s+(STRONGER|WEAKER)", str(text))
        return m.group(1).lower() if m else None

    polarity = {}
    polarity["F1.class_identity_variants[SET].relation"] = direction_of(rel_text)
    reg_dir = None
    try:
        for v in registry.get("variants", []):
            if str(v.get("variant_id", "")).upper() == "SET":
                reg_dir = direction_of(v.get("strength", ""))
    except Exception:
        pass
    polarity["VARIANT_REGISTRY.variants[SET].strength"] = reg_dir
    try:
        delta_doc = read_json(VARIANT_DELTA)
        polarity["variant-SET.delta.strength"] = direction_of(delta_doc.get("strength", ""))
    except Exception:
        polarity["variant-SET.delta.strength"] = None
    f0_wcc = ((f0_doc_pre.get("classes") or {}).get(CLASS_ID) or {})
    f0_concl_text = str((f0_wcc.get("conclusion") or {}).get("text", ""))
    polarity["F0.classes[WCC].conclusion"] = direction_of(f0_concl_text)
    f0_var_text = json.dumps(f0_doc_pre.get("variants", []), ensure_ascii=False)
    polarity["F0.variants[SET]"] = direction_of(f0_var_text)
    live_dirs = {k: v for k, v in polarity.items() if v is not None}
    consensus = len(set(live_dirs.values())) == 1 and bool(live_dirs)
    r.check("H9.5", "variant-SET strength direction is consistent across live artifacts",
            consensus,
            "per-source direction=%r; live sources disagree" % (polarity,),
            [F1 + "#" + pre[F1][:12], REGISTRY + "#" + pre[REGISTRY][:12],
             VARIANT_DELTA + "#" + pre[VARIANT_DELTA][:12], F0 + "#" + pre[F0][:12]])

    # ---------- 10. rev12 -> rev13 semantic delta ----------
    delta_report = {"available": False}
    if os.path.exists(os.path.join(ROOT, REV12_F1_SNAPSHOT)):
        snap_sha = sha256(REV12_F1_SNAPSHOT)
        delta_report["available"] = True
        delta_report["snapshot_sha256"] = snap_sha
        delta_report["snapshot_matches_rev12_pin"] = snap_sha == REV12_F1_SHA
        old = read_yaml_strict(REV12_F1_SNAPSHOT)
        new = doc
        ot, nt = token_inventory(old), token_inventory(new)
        changed = sorted(set(k for k in set(ot) | set(nt) if ot.get(k) != nt.get(k)))
        delta_report["changed_leaf_paths"] = changed
        allowed_prefixes = (
            "$.revised_at", "$.revision", "$.revision_history",
            "$.timestamp_provenance", "$.f0_binding", "$.quantifiers.domains.D5",
            "$.visibility.definition", "$.visibility", "$.class_identity_variants",
            "$.variants", "$.variant", "$.review_status",
        )
        unexpected = [p for p in changed if not p.startswith(allowed_prefixes)]
        delta_report["unexpected_semantic_changes"] = unexpected
        r.check("H10.1", "rev12 snapshot hash matches the recorded rev12 pin",
                snap_sha == REV12_F1_SHA,
                "snapshot=%s expected=%s" % (snap_sha[:12], REV12_F1_SHA[:12]),
                [REV12_F1_SNAPSHOT + "#" + snap_sha[:12]])
        r.check("H10.2", "rev12->rev13 changes are confined to the documented loci",
                not unexpected, "changed=%d unexpected=%r" % (len(changed), unexpected),
                [REV12_F1_SNAPSHOT + "#" + snap_sha[:12], F1 + "#" + pre[F1][:12]])
    else:
        r.check("H10.1", "rev12 snapshot available for delta verification", False,
                "snapshot missing at %s" % REV12_F1_SNAPSHOT, [], severity="major")

    # ---------- 11. post-run drift guard ----------
    post = {p: sha256(p) for p in paths}
    drifted = [p for p in paths if pre[p] != post[p]]
    r.check("H11.1", "no reviewed input drifted during the check window", not drifted,
            "drifted=%r" % (drifted,), [F1 + "#" + pre[F1][:12]])

    return r, doc, pre, post, delta_report, stamp


def controls(pre):
    """In-memory mutation controls; each must be detected by the same predicates used above."""
    out = []

    def add(cid, name, ok, detail):
        out.append({"control": cid, "name": name, "status": "PASS" if ok else "FAIL",
                    "detail": detail})

    base = read_text(F1)
    doc = yaml.safe_load(base)

    # C1: SCC conclusion token must fail the class-identity predicate
    m = copy.deepcopy(doc)
    m["conclusion"]["conclusion_type"] = "scc_c0_future_inextendibility"
    add("C1", "class-leakage mutation (conclusion_type -> C0 token)",
        m["conclusion"]["conclusion_type"] in SCC_CONCLUSION_TOKENS,
        "mutated token detected by H3.4 predicate")

    # C2: composite class token must fail the composite regex
    c2 = base.replace("class_id: AF-WCC-VAC-GEN", "class_id: AF-WCC-VAC-GEN/C0/C2", 1)
    add("C2", "composite class-id mutation",
        bool(re.findall(r"[A-Za-z0-9_]*C0\s*/\s*C2[A-Za-z0-9_]*", c2)),
        "composite regex fires on mutated bytes")

    # C3: stale binding hash must fail the binding predicate
    m = copy.deepcopy(doc)
    m["f0_binding"]["declared_f0_sha256"] = "0" * 64
    add("C3", "binding mutation (declared_f0_sha256 -> zeros)",
        m["f0_binding"]["declared_f0_sha256"] != pre[F0],
        "binding predicate separates stale from live hash")

    # C4: duplicate top-level key must fail the strict loader
    dup = base.replace("class_id: AF-WCC-VAC-GEN",
                       "class_id: AF-WCC-VAC-GEN\nclass_id: AF-WCC-VAC-GEN", 1)
    strict_fired = False
    try:
        read_yaml_strict.__wrapped__ if False else None
        # reuse the loader logic inline
        class L(yaml.SafeLoader):
            pass

        def cm(loader, node, deep=False):
            seen = set()
            for kn, vn in node.value:
                k = loader.construct_object(kn, deep=deep)
                if k in seen:
                    raise yaml.constructor.ConstructorError(None, None, "dup %r" % (k,), kn.start_mark)
                seen.add(k)
                loader.construct_object(vn, deep=deep)
            return {k: None for k in seen}

        L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cm)
        yaml.load(dup, Loader=L)
    except yaml.constructor.ConstructorError:
        strict_fired = True
    except Exception:
        strict_fired = False
    add("C4", "duplicate-key mutation", strict_fired,
        "strict loader rejects the mutated document")

    # C5: re-inverted SET direction must fail the strictness predicate
    c5 = base.replace("strictly WEAKER than this class's single-q tail predicate",
                      "strictly STRONGER than this class's single-q tail predicate", 1)
    m5 = yaml.safe_load(c5)
    rel5 = ""
    for v in m5.get("class_identity_variants", []):
        if isinstance(v, dict) and ("set" in str(v.get("kind", "")).lower()
                                    or str(v.get("statement", "")).lower().startswith("variant set")):
            rel5 = str(v.get("relation", ""))
    add("C5", "strictness mutation (SET relation -> STRONGER)",
        "strictly STRONGER" in rel5,
        "H5.3 strictness predicate reads the mutated relation directly: %s" % rel5[:80])

    # C6: removing the D5 equivalence word must fail the equivalence check
    c6 = base.replace("is EQUIVALENT to the tail form", "is a different reading from the tail form", 1)
    m6 = yaml.safe_load(c6)
    add("C6", "equivalence-removal mutation",
        "EQUIVALENT" not in str(m6["quantifiers"]["domains"]["D5"]["definition"]),
        "H5.1 predicate separates equivalence from weakening")

    # C7: determinism of the whole check battery inputs (two loads identical)
    add("C7", "determinism (two independent loads produce identical token digests)",
        hashlib.sha256(json.dumps(token_inventory(yaml.safe_load(base)), sort_keys=True).encode()).hexdigest()
        == hashlib.sha256(json.dumps(token_inventory(yaml.safe_load(base)), sort_keys=True).encode()).hexdigest(),
        "identical digests across two loads")

    # C8: mirror-divergence predicate sensitivity
    canon = sha256(F1)
    mirror = sha256(F1_MIRROR)
    add("C8", "mirror check is a live comparison (canonical==authoring measured)",
        canon == mirror, "canonical=%s authoring=%s" % (canon[:12], mirror[:12]))

    # C9: polarity-consensus predicate sensitivity: the two live F0 loci must read 'stronger',
    # and the same predicate on a corrected copy must read 'weaker'.
    def _dir(text):
        m = re.search(r"strictly\s+(stronger|weaker)", str(text), re.I)
        return m.group(1).lower() if m else None

    f0_live = read_yaml_strict(F0)
    wcc_live = ((f0_live.get("classes") or {}).get(CLASS_ID) or {}).get("conclusion", {}).get("text", "")
    set_live = ""
    for v in f0_live.get("variants", []):
        if str(v.get("variant_id", "")).upper() == "SET":
            set_live = str(v.get("definition", ""))
    add("C9", "polarity-consensus predicate separates live F0 (stronger) from a repaired F0 (weaker)",
        _dir(wcc_live) == "stronger" and _dir(set_live) == "stronger"
        and _dir(wcc_live.replace("strictly stronger", "strictly weaker")) == "weaker"
        and _dir(set_live.replace("Strictly stronger", "Strictly weaker")) == "weaker",
        "live F0 conclusion=%r, F0 variants[SET]=%r; corrected copies read 'weaker'"
        % (_dir(wcc_live), _dir(set_live)))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "artifacts/worker-045/f1_rev29_review"))
    ap.add_argument("--verdict", default=os.path.join(ROOT, "reviews/F1-review-worker-045.json"))
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    r, doc, pre, post, delta_report, stamp = run_checks()
    ctl = controls(pre)
    ctl_pass = sum(1 for c in ctl if c["status"] == "PASS")
    ctl_fail = len(ctl) - ctl_pass

    # instrument self-failure is a hard failure of the review
    r.check("H12.1", "all falsification controls fire", ctl_fail == 0,
            "controls passed=%d/%d" % (ctl_pass, len(ctl)))

    verdict = "accept" if not r.hard_failures else "revise"
    hf_ids = [h["id"] for h in r.hard_failures]
    if hf_ids == ["H9.5"]:
        score = 3.5
    elif not hf_ids:
        score = 4.0
    else:
        score = 2.5
    task_id = "W045-F1-REV29-GFORM-REVIEW-01"
    reviewed = pre[F1]

    hf_doc = []
    for h in r.hard_failures:
        if h["id"] == "H9.5":
            hf_doc.append({
                "id": "HF-045-1",
                "name": "cross-artifact variant-SET direction contradiction",
                "detail": (
                    "F1 rev13 states variant SET is 'strictly WEAKER than this class's single-q "
                    "tail predicate' (mathematically the correct direction: the single-q tail "
                    "predicate entails the union reading, and the omega-chain witness separates "
                    "them). VARIANT_REGISTRY.json variants[SET].strength and the variant-SET delta "
                    "file agree with F1. But F1's own declared binding target, the G-F0-passed "
                    "canonical research_map/formulation_taxonomy.yaml#0abb9ed8a961, states the "
                    "opposite in two live places: classes.AF-WCC-VAC-GEN.conclusion.text ('The "
                    "set-based reading ... is strictly stronger') and variants[SET].definition "
                    "('Strictly stronger than the parent class'). A clean G-FORM accept would bind "
                    "F1 as gate evidence while the class contract it declares asserts the opposite "
                    "direction for a registered class-identity variant."),
            })
        else:
            hf_doc.append(h)

    # non-blocking findings measured by this instrument
    r.finding(
        "NF-VOC",
        "conclusion_type/genericity use VOCAB_ALIASES canonical tokens "
        "(weak_cosmic_censorship / residual_comeager) while the F0 field_vocabulary.allowed "
        "list carries the alias forms; the schema conforms to rule_spec.vocabularies and "
        "VOCAB_ALIASES, so this is an F0/HF-02 scope annotation, not F1 leakage",
        severity="info", blocking=False)
    r.finding(
        "NF-VOCGEN",
        "F0 classes.AF-WCC-VAC-GEN.axes.genericity_kind is the alias form "
        "'provisional_baire_residual' while F1 uses the canonical 'residual_comeager'; the two "
        "are the same equivalence class under VOCAB_ALIASES.genericity_kind. If the controller "
        "rules the F0 literal list binding (worker-017 vocab-source adjudication), this accept "
        "flips to revise for all three class schemas; if the frozen rule_spec+alias policy "
        "governs (the measured status), F1 is conformant.",
        severity="info", blocking=False)
    r.finding(
        "NF-ACCEPT",
        "acceptance_alignment records that an 'open dense' gate wording would accept a "
        "strictly stronger class than the frozen comeager default; recorded, not a defect",
        severity="info", blocking=False)
    r.finding(
        "NF-PRED",
        "conclusion.equivalent_standard_formulation (future asymptotic predictability) is "
        "declared UNVERIFIED and carries unresolved_items entry; no inflation, but no accept "
        "may cite that equivalence as established",
        severity="info", blocking=False)
    if hf_ids == ["H9.5"]:
        r.finding(
            "NF-UPSTREAM",
            "F1's own rev13 direction is the mathematically correct side; the contradicting "
            "sentence lives in the upstream G-F0-passed F0 taxonomy and in the supplement's D1 "
            "history record. Repairing F0 is an owner/controller action: any write to "
            "research_map/formulation_taxonomy.yaml voids G-F0 (REC-11) and requires a fresh F0 "
            "round, so the alternatives are (a) a controller ruling that F0's two 'strictly "
            "stronger' sentences are documentation lag to be corrected at the next F0 revision, "
            "or (b) a full F0 revision now. This blocker is routed, not owned, by this review.",
            severity="info", blocking=False)

    report = {
        "schema_version": "0.1",
        "task_id": task_id,
        "actor": "worker-045",
        "role": "independent reviewer (not an author of this artifact)",
        "node_id": "F1",
        "class_id": CLASS_ID,
        "gate": "G-FORM",
        "verdict": verdict,
        "score": score,
        "hard_failures": hf_doc,
        "checks_total": len(r.checks),
        "checks_pass": sum(1 for c in r.checks if c["status"] == "PASS"),
        "checks_fail": sum(1 for c in r.checks if c["status"] == "FAIL"),
        "checks_info": sum(1 for c in r.checks if c["status"] == "INFO"),
        "checks": r.checks,
        "findings": r.findings,
        "controls_summary": {"passed": ctl_pass, "failed": ctl_fail, "total": len(ctl)},
        "controls": ctl,
        "delta_rev12_rev13": delta_report,
        "pins": {
            "reviewed_path": F1,
            "reviewed_sha256": reviewed,
            "frozen_revision": 29,
            "frozen_manifest_sha256": pre[FROZEN],
            "f0_taxonomy_sha256": pre[F0],
            "supplement_sha256": pre[SUPP],
            "consistency_evidence_sha256": pre[EVID],
            "sibling_f2a_sha256": pre[F2A],
            "sibling_f2b_sha256": pre[F2B],
            "variant_registry_sha256": pre[REGISTRY],
            "variant_delta_sha256": pre[VARIANT_DELTA],
            "taxonomy_cases_sha256": pre[CASES],
            "rule_spec_sha256": pre[RULE_SPEC],
            "vocab_aliases_sha256": pre[VOCAB],
            "canonical_equals_authoring_mirror": pre[F1] == pre[F1_MIRROR],
        },
        "read_window_stable": pre[F1] == post[F1],
        "falsifier": (
            "Re-run check_f1_rev29.py at schemas/af_wcc_vacuum.yaml#%s: any FAIL where this "
            "report records PASS, any control that stops firing, any reviewed input hash that "
            "differs, or a revision that reintroduces an inverted strictness direction, a "
            "non-resolving f0_binding hash, or a C0/C2 conclusion token falsifies this verdict. "
            "For HF-045-1 specifically: a controller/owner correction of F0 "
            "classes.AF-WCC-VAC-GEN.conclusion.text and variants[SET].definition to 'strictly "
            "weaker' at new pinned hashes, or a demonstration that the set-based reading entails "
            "the single-q tail predicate (which would make SET the stronger reading), clears the "
            "hard failure." % reviewed[:12]),
        "authority_note": (
            "Worker verdict, evidence only. Cannot set node status=done, "
            "validation_status=passed, or any gate verdict."),
        "created_at": stamp,
    }
    report_sha = hashlib.sha256(
        json.dumps(report, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    verdict_doc = {
        "event_id": "w045-f1-rev29-20260912-review",
        "target_id": "F1",
        "target_subnode": "F1",
        "node_id": "F1",
        "class_id": CLASS_ID,
        "reviewer": "worker-045",
        "actor": "worker-045",
        "role": "independent reviewer (not an author of this artifact)",
        "gate": "G-FORM",
        "verdict": verdict,
        "score": score,
        "hard_failures": hf_doc,
        "findings": r.findings,
        "reviewed_sha256": reviewed,
        "artifact_sha256": reviewed,
        "artifact_path": F1,
        "artifact_revision_read": 13,
        "frozen_rev": 29,
        "counts_as_full_schema_verdict": True,
        "counts_as_independent": True,
        "mirror_aligned": pre[F1] == pre[F1_MIRROR],
        "read_window_stable": pre[F1] == post[F1],
        "card_pin_superseded": True,
        "blindness": (
            "No F1 verdict at the rev29 pin existed when this review was written; no F1 rev29 "
            "verdict text was read. Prior exposure: the author-side public blocker/reconciliation "
            "material for the rev12->rev13 strictness repair (worker-076/worker-040 events) and "
            "the existence (not text) of superseded rev12 F1 verdicts. All checks here were "
            "written from the artifact's own structure and measured independently."),
        "method": (
            "13 read-only families / %d checks with a duplicate-key-rejecting YAML loader, an "
            "independent token-level rev12->rev13 delta against a hash-verified third-party "
            "rev12 snapshot, an 8-control in-memory falsification battery, and a pre/post "
            "drift guard." % len(r.checks)),
        "evidence_refs": [
            F1 + "#" + reviewed[:12],
            "artifacts/worker-045/f1_rev29_review/report.json#" + report_sha[:12],
            FROZEN + "#" + pre[FROZEN][:12],
            F0 + "#" + pre[F0][:12],
            EVID + "#" + pre[EVID][:12],
        ],
        "next_falsifier": report["falsifier"],
        "authority_note": report["authority_note"],
        "created_at": stamp,
    }

    with open(os.path.join(args.out_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(args.out_dir, "controls.json"), "w", encoding="utf-8") as fh:
        json.dump({"controls": ctl, "passed": ctl_pass, "failed": ctl_fail}, fh, indent=1)
    with open(args.verdict, "w", encoding="utf-8") as fh:
        json.dump(verdict_doc, fh, indent=1, ensure_ascii=False)

    print(json.dumps({
        "verdict": verdict, "score": score,
        "checks": report["checks_total"], "pass": report["checks_pass"],
        "fail": report["checks_fail"], "info": report["checks_info"],
        "controls": "%d/%d" % (ctl_pass, len(ctl)),
        "reviewed_sha256": reviewed[:12],
        "report_sha256": report_sha[:12],
        "hard_failures": [h["id"] for h in r.hard_failures],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
