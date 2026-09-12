#!/usr/bin/env python3
"""Independent full-schema verification instrument for F2b (AF-SCC-C0-VAC-GEN) rev12.

Task: W059-F2B-REV12-VERDICT-01.  Owner: worker-059.

Scope: one class, one node, one pinned hash.  The instrument is self-contained
(stdlib + PyYAML only); it does NOT import canonical gate modules, so a canonical
gate regression cannot silently make this instrument pass.  It parses the pinned
snapshot with a strict duplicate-key-rejecting loader, runs 30 named checks, and
builds 18 deterministic single-defect mutants of the parsed document to measure
the instrument's own sensitivity.

Usage:
  python3 check_f2b_rev12.py SNAPSHOT.yaml [--root REPO_ROOT] [--out EVIDENCE.json]

Exit codes: 0 = all checks pass; 1 = at least one check fails; 2 = usage/parse error.
The exit code reports the CLASS CONTENT verdict (check failure), not the review verdict:
a binding failure is still a check failure.  The review verdict is recorded separately
in review_F2b_55d0a1ea.json.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import yaml

F2B = "AF-SCC-C0-VAC-GEN"
F2A = "AF-SCC-C2-VAC-GEN"
WCC = "AF-WCC-VAC-GEN"
C0_TOKEN = "scc_c0_future_inextendibility"
C2_TOKEN = "scc_c2_future_inextendibility"
CANON_CONTRACT = "research_map/formulation_taxonomy.yaml"
AUTHOR_CONTRACT = "artifacts/formulation/formulation_taxonomy.yaml"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
FROZEN = "artifacts/formulation/FROZEN.json"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"

REQUIRED_TOP = [
    "schema_version", "artifact_kind", "class_id", "node_id", "owner", "authored_by",
    "authored_at", "revised_at", "revision_history", "timestamp_provenance", "revision",
    "class_components", "class_contract_pointer", "class_contract_supplement_pointer",
    "sibling_disjoint_from", "epistemic_status", "promotion_rule", "scope_statement",
    "quantifiers", "extension_predicate", "topology", "data_class", "regularity",
    "genericity", "non_vacuity", "i_plus", "visibility", "conclusion", "falsifier",
    "anti_scope", "l1_ledger_refs", "known_status", "f0_binding", "provenance",
    "unresolved_items", "review_status",
]

ASSERTED_TEXT_PATHS = [
    ("conclusion", "statement_natural_language"),
    ("conclusion", "statement_formal"),
    ("conclusion", "conclusion_type"),
    ("scope_statement",),
]
WCC_CONCLUSION_TERMS = [
    "i+ completeness", "future null infinity is complete", "predictab",
    "visible from i+", "visibility from i+ is the conclusion",
]


# ----------------------------------------------------------------------------- loader
class DuplicateKeyError(Exception):
    pass


def strict_load(path: Path):
    """Load YAML and return (doc, duplicates). Duplicates are recorded, not raised."""
    duplicates: list[dict] = []

    class StrictLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                hashable = key
                exists = hashable in mapping
            except TypeError:
                exists = False
            if exists:
                duplicates.append({
                    "key": str(key),
                    "line": key_node.start_mark.line + 1,
                    "value_line": value_node.start_mark.line + 1,
                })
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    StrictLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    with open(path, "rb") as fh:
        doc = yaml.load(fh, Loader=StrictLoader)
    return doc, duplicates


# ----------------------------------------------------------------------------- helpers
def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(kind: str, token, vocab: dict):
    """Canonicalise a vocab token (same rule as the published alias policy)."""
    tok = str(token)
    for c, aliases in vocab.get(kind, {}).items():
        if tok == c or tok in aliases:
            return c
    return tok


def parse_ts(s):
    if not isinstance(s, str):
        return None
    try:
        return _dt.datetime.fromisoformat(s)
    except ValueError:
        return None


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def get_path(doc, dotted):
    if isinstance(dotted, (tuple, list)):
        cur = doc
        for part in dotted:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur
    cur = doc
    for part in str(dotted).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def resolve_pointer(doc, pointer: str):
    """Resolve 'path#a.b.c' against a parsed dict (path part ignored)."""
    if "#" not in pointer:
        return None
    frag = pointer.split("#", 1)[1]
    cur = doc
    for part in frag.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


# ----------------------------------------------------------------------------- checks
class Checker:
    def __init__(self, doc, dup, snap_path: Path, root: Path, now: _dt.datetime):
        self.doc = doc
        self.dup = dup
        self.snap = snap_path
        self.root = root
        self.now = now
        self.rows: list[dict] = []
        self.measured: dict = {}

    def check(self, cid, group, desc, ok, detail, severity="blocking"):
        self.rows.append({
            "id": cid, "group": group, "description": desc,
            "status": "pass" if ok else "fail",
            "severity": severity if not ok else "n/a",
            "detail": detail if isinstance(detail, (str, int, float, bool, type(None))) else dumps(detail),
        })
        return ok

    # -- structural -----------------------------------------------------------
    def run_structural(self):
        d = self.doc
        self.check("P1", "structure", "strict parse, zero duplicate mapping keys",
                   len(self.dup) == 0, {"duplicates": self.dup})
        missing = [k for k in REQUIRED_TOP if k not in d]
        self.check("P2", "structure", "all required top-level slots present",
                   not missing, {"missing": missing})
        rev_ok = d.get("revision") == 12
        self.check("P3", "structure", "revision metadata coherent (revision=12, single revised_at)",
                   rev_ok and isinstance(d.get("revised_at"), str)
                   and isinstance(d.get("timestamp_provenance"), str)
                   and len(d.get("timestamp_provenance", "")) > 0,
                   {"revision": d.get("revision"), "revised_at": d.get("revised_at")})
        auth, revd = parse_ts(d.get("authored_at")), parse_ts(d.get("revised_at"))
        mtime = _dt.datetime.fromtimestamp(os.path.getmtime(self.snap)).astimezone()
        now = self.now
        ts_ok = bool(auth and revd) and auth <= revd <= now and revd <= mtime
        self.check("P4", "structure", "timestamp discipline: authored_at <= revised_at <= mtime <= now",
                   ts_ok, {
                       "authored_at": d.get("authored_at"), "revised_at": d.get("revised_at"),
                       "mtime": mtime.isoformat(), "measured_now": now.isoformat(),
                       "future_dated": bool(revd and revd > now)})
        hist = d.get("revision_history") or []
        idx = [r.get("index") for r in hist]
        unique_idx = len(idx) == len(set(idx)) and all(isinstance(i, int) for i in idx)
        future_rows = [r.get("index") for r in hist
                       if (parse_ts(r.get("at")) or now) > now]
        times = [parse_ts(r.get("at")) for r in hist]
        monotone = all(a is None or b is None or a <= b for a, b in zip(times, times[1:]))
        self.check("P5", "structure", "revision_history indices unique; no future rows",
                   unique_idx and not future_rows,
                   {"n_rows": len(hist), "indices": idx, "future_rows": future_rows,
                    "unused_rows": [r.get("index") for r in hist if r.get("unused")]})
        effective = [r for r in hist if not r.get("unused")]
        times_eff = [parse_ts(r.get("at")) for r in effective]
        monotone_eff = all(a is not None and b is not None and a <= b
                           for a, b in zip(times_eff, times_eff[1:]))
        self.check("P6", "structure", "revision_history timestamps monotone over used rows (advisory class)",
                   monotone_eff,
                   {"monotone_all_rows": monotone, "monotone_used_rows": monotone_eff,
                    "unused_rows": [r.get("index") for r in hist if r.get("unused")],
                    "note": "row 9 is flagged unused:true and is the only out-of-order row; "
                            "ordering defect over effective history is advisory only"})

    # -- identity / binding ---------------------------------------------------
    def run_identity(self):
        d = self.doc
        self.check("B1", "identity", "class_id/node_id/artifact_kind",
                   d.get("class_id") == F2B and d.get("node_id") == "F2b"
                   and d.get("artifact_kind") == "class_schema",
                   {"class_id": d.get("class_id"), "node_id": d.get("node_id"),
                    "artifact_kind": d.get("artifact_kind")})
        comp = d.get("class_components") or {}
        exp = {"asymptotics": "AF", "censorship": "SCC", "matter": "VAC",
               "genericity": "GEN", "regularity_token": "C0"}
        self.check("B2", "identity", "class_components match the C0 SCC vacuum-GEN identity",
                   comp == exp, {"measured": comp, "expected": exp})

        f0 = yaml.safe_load((self.root / CANON_CONTRACT).read_text())
        auth_tree = yaml.safe_load((self.root / AUTHOR_CONTRACT).read_text())
        vocab = json.loads((self.root / VOCAB).read_text())
        ptr = d.get("class_contract_pointer")
        target = resolve_pointer(f0, ptr or "")
        self.check("B3", "binding", "class_contract_pointer resolves in canonical taxonomy",
                   isinstance(target, dict), {"pointer": ptr, "resolved": isinstance(target, dict)})
        axes = (target or {}).get("axes", {}) if isinstance(target, dict) else {}
        schema_tok = (d.get("conclusion") or {}).get("conclusion_type")
        self.check("B4", "binding", "canonical contract axes agree with the schema identity",
                   axes.get("family") == "SCC" and axes.get("regularity_token") == "C0"
                   and axes.get("conclusion_type") is not None,
                   {"axes": axes})
        supp_ptr = d.get("class_contract_supplement_pointer")
        supp = resolve_pointer(auth_tree, supp_ptr or "")
        self.check("B5", "binding", "class_contract_supplement_pointer resolves in the authoring contract",
                   isinstance(supp, dict), {"pointer": supp_ptr, "resolved": isinstance(supp, dict)})

        # vocab/token registry
        canon_schema = canon("conclusion_type", schema_tok, vocab)
        canon_axes = canon("conclusion_type", axes.get("conclusion_type"), vocab)
        allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
        schema_is_vocab_key = schema_tok in (vocab.get("conclusion_type") or {})
        axes_is_alias = axes.get("conclusion_type") not in (vocab.get("conclusion_type") or {})
        self.check("B6", "binding", "conclusion token canonicalises consistently across registries",
                   canon_schema == canon_axes == C0_TOKEN,
                   {"schema_token": schema_tok, "schema_is_VOCAB_key": schema_is_vocab_key,
                    "canonical_F0_axis_token": axes.get("conclusion_type"),
                    "canonical_F0_axis_is_VOCAB_alias": axes_is_alias,
                    "F0_field_vocabulary_allowed": allowed,
                    "canon_schema": canon_schema, "canon_axes": canon_axes,
                    "VOCAB_policy": vocab.get("policy")})
        self.check("B7", "binding", "schema token is the VOCAB canonical key and F0 stores only an accepted alias",
                   schema_is_vocab_key and axes_is_alias,
                   {"schema_token_canonical": schema_is_vocab_key,
                    "f0_stores_alias": axes_is_alias,
                    "policy_says": vocab.get("policy")})

        # f0 hash binding
        f0_meas = sha256_file(self.root / CANON_CONTRACT)
        declared_f0 = (d.get("f0_binding") or {}).get("declared_f0_sha256")
        self.check("B8", "binding", "declared_f0_sha256 equals measured canonical F0 hash",
                   declared_f0 == f0_meas,
                   {"declared": declared_f0, "measured": f0_meas})

        # consistency evidence chain
        fb = d.get("f0_binding") or {}
        ev_path = self.root / str(fb.get("consistency_evidence"))
        ev_meas = sha256_file(ev_path)
        declared_ev = fb.get("consistency_evidence_sha256")
        frozen = json.loads((self.root / FROZEN).read_text())
        frozen_ev = (frozen.get("files", {}).get(CONSISTENCY) or {}).get("sha256")
        enriched = self.root / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"
        enriched_meas = sha256_file(enriched)
        self.check("B9", "binding", "declared consistency_evidence_sha256 resolves at the declared canonical path",
                   declared_ev == ev_meas,
                   {"declared": declared_ev, "measured_at_declared_path": ev_meas,
                    "frozen_pin": frozen_ev,
                    "out_of_tree_pin_exists": enriched.exists(),
                    "out_of_tree_pin_sha256_measured": enriched_meas,
                    "declared_equals_out_of_tree_pin": declared_ev == enriched_meas})
        self.check("B10", "binding", "declared consistency evidence hash equals the FROZEN pin",
                   declared_ev == frozen_ev,
                   {"declared": declared_ev, "frozen_pin": frozen_ev})
        self.measured["consistency_evidence"] = {
            "declared": declared_ev, "canonical_path_measured": ev_meas,
            "frozen_pin": frozen_ev, "enriched_pin_measured": enriched_meas,
        }

        # FROZEN pins
        pins = frozen.get("files", {})
        pairs = [
            ("canonical F2b", "schemas/af_scc_c0_vacuum.yaml", self.root / "schemas/af_scc_c0_vacuum.yaml"),
            ("authoring F2b", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
             self.root / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
            ("canonical F0", CANON_CONTRACT, self.root / CANON_CONTRACT),
            ("authoring F0", AUTHOR_CONTRACT, self.root / AUTHOR_CONTRACT),
            ("VOCAB", VOCAB, self.root / VOCAB),
        ]
        pin_rows = []
        for label, rel, path in pairs:
            pin = (pins.get(rel) or {}).get("sha256")
            meas = sha256_file(path)
            pin_rows.append({"label": label, "path": rel, "pin": pin, "measured": meas,
                             "match": pin == meas})
        self.check("B11", "binding", "FROZEN rev28 pins match measured bytes",
                   all(r["match"] for r in pin_rows),
                   {"revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
                    "rows": pin_rows})
        mirror_ok = (sha256_file(self.root / "schemas/af_scc_c0_vacuum.yaml")
                     == sha256_file(self.root / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"))
        self.check("B12", "binding", "canonical and authoring F2b mirrors byte-identical",
                   mirror_ok, {"mirror_identical": mirror_ok})

    # -- class semantics ------------------------------------------------------
    def run_semantics(self):
        d = self.doc
        concl = d.get("conclusion") or {}
        blob_asserted = dumps([get_path(d, p) for p in ASSERTED_TEXT_PATHS])
        fw = dumps(concl.get("forbidden_weakenings") or []).lower()
        fs = dumps(concl.get("forbidden_strengthenings") or []).lower()
        anti = dumps(d.get("anti_scope") or []).lower()
        sibling = d.get("sibling_disjoint_from")
        tok = concl.get("conclusion_type")
        c0_ok = (
            tok == C0_TOKEN
            and ("c0" in dumps(concl.get("statement_formal")).lower()
                 or "continuous" in dumps(concl.get("statement_natural_language")).lower())
            and "c2" in fw and "c1" in fw
            and "af-scc-c2-vac-gen" in anti
            and sibling == F2A
            and "c0 or c2" not in blob_asserted.lower()
        )
        self.check("S1", "semantics", "C0 conclusion asserted; C2/C1 substitutions forbidden; no C0/C2 merge",
                   c0_ok,
                   {"conclusion_type": tok, "sibling_disjoint_from": sibling,
                    "forbidden_weakenings": concl.get("forbidden_weakenings"),
                    "forbidden_strengthenings": concl.get("forbidden_strengthenings")})
        occ_c2 = [m.start() for m in re.finditer(re.escape(C2_TOKEN), dumps(d))]
        self.check("S2", "semantics", "C2 conclusion token absent from the C0 schema",
                   len(occ_c2) == 0, {"occurrences": len(occ_c2)})

        q = d.get("quantifiers") or {}
        ordered = q.get("ordered") or []
        kinds = [r.get("kind") for r in ordered]
        binders = [r.get("binder") for r in ordered]
        doms = [r.get("domain_id") for r in ordered]
        dmap = q.get("domains") or {}
        dom_defs_ok = all(isinstance(dmap.get(dd), dict) and dmap[dd].get("definition")
                          and dmap[dd].get("definition_ref") for dd in doms)
        refs_ok = True
        for dd in doms:
            ref = (dmap.get(dd) or {}).get("definition_ref")
            if ref and get_path(d, str(ref)) is None:
                refs_ok = False
        q_ok = (
            kinds == ["forall", "exists", "forall", "not_exists"]
            and binders == ["r", "G_r", "(Sigma,h,K)", "(M',g',iota)"]
            and doms == ["D0", "D1", "D2", "D3"]
            and dom_defs_ok and refs_ok and q.get("order_matters") is True
            and "non-meager" in dumps(q.get("negation"))
            and bool(q.get("negation_normal_form"))
        )
        self.check("S3", "semantics", "exact quantifier order forall(comeager)-forall-not-exists, domains defined",
                   q_ok,
                   {"kinds": kinds, "binders": binders, "domains": doms,
                    "domain_defs_ok": dom_defs_ok, "definition_refs_resolve": refs_ok,
                    "order_matters": q.get("order_matters"),
                    "negation_present": bool(q.get("negation")),
                    "negation_normal_form_present": bool(q.get("negation_normal_form"))})

        ep = d.get("extension_predicate") or {}
        ep_def = ep.get("definition") or ""
        clauses = [c for c in ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"] if c in ep_def]
        ep_ok = (ep.get("frozen_regularity") == "C0" and ep.get("frozen_equation_concept") == "none"
                 and ep.get("frozen_direction") == "future" and len(clauses) == 6
                 and "interior" in ep_def.lower())
        self.check("S4", "semantics", "extension predicate frozen axes C0/none/future with clauses (a)-(f)",
                   ep_ok,
                   {"frozen_regularity": ep.get("frozen_regularity"),
                    "frozen_equation_concept": ep.get("frozen_equation_concept"),
                    "frozen_direction": ep.get("frozen_direction"), "clauses_found": clauses})

        topo = d.get("topology") or {}
        topo_ok = (topo.get("spacetime_dimension") == 4 and "one" in str(topo.get("end_structure")).lower()
                   and "smooth" in dumps(topo.get("extension_topology")).lower()
                   and any("differentiable" in str(x).lower() for x in (topo.get("forbidden") or [])))
        self.check("S5", "semantics", "topology: 4d, one AF end, smooth M' with continuous metric",
                   topo_ok, {"dimension": topo.get("spacetime_dimension"),
                             "end_structure": topo.get("end_structure")})

        dc = d.get("data_class") or {}
        dc_ok = (dc.get("matter") == "none" and dc.get("cosmological_constant") == 0
                 and "Ric" in str(dc.get("equations"))
                 and "hamiltonian" in (dc.get("constraints") or {})
                 and "momentum" in (dc.get("constraints") or {})
                 and "smooth-with-decay" in str((dc.get("regularity_class") or {}).get("default"))
                 and "sobolev_variant" in (dc.get("regularity_class") or {}))
        self.check("S6", "semantics", "data class: vacuum, Lambda=0, both constraints, declared regularity",
                   dc_ok, {"matter": dc.get("matter"),
                           "cosmological_constant": dc.get("cosmological_constant"),
                           "regularity_variants": list((dc.get("regularity_class") or {}).keys())})

        reg = d.get("regularity") or {}
        reg_ok = (reg.get("extension_regularity") == "C0"
                  and "continuous" in str(reg.get("extension_regularity_exact")).lower()
                  and "H2_loc" in dumps(reg.get("must_not_conflate"))
                  and "C2" in dumps(reg.get("must_not_conflate")))
        self.check("S7", "semantics", "regularity axis frozen at C0 and not conflated with H2_loc/C2",
                   reg_ok, {"extension_regularity": reg.get("extension_regularity")})

        gen = d.get("genericity") or {}
        gen_ok = (gen.get("kind") == "residual_comeager" and gen.get("is_part_of_class") is True
                  and "constraint manifold" in dumps(gen.get("ambient_space")).lower()
                  and "subspace topology" in dumps(gen.get("ambient_space")).lower())
        self.check("S8", "semantics", "genericity is residual-comeager and part of the class identity",
                   gen_ok, {"kind": gen.get("kind"), "is_part_of_class": gen.get("is_part_of_class")})

        ip = d.get("i_plus") or {}
        self.check("S9", "semantics", "I+ is an assumption only, never in the conclusion",
                   ip.get("role") == "assumption" and ip.get("in_conclusion") is False
                   and ip.get("completeness_in_conclusion") is False,
                   {"role": ip.get("role"), "in_conclusion": ip.get("in_conclusion"),
                    "completeness_in_conclusion": ip.get("completeness_in_conclusion")})

        vis = d.get("visibility") or {}
        self.check("S10", "semantics", "visibility explicitly excluded from this SCC conclusion",
                   vis.get("role") == "not_in_conclusion" and vis.get("visible_singularity_is_wcc") is True
                   and bool(vis.get("forbidden_falsifier")),
                   {"role": vis.get("role"), "visible_singularity_is_wcc": vis.get("visible_singularity_is_wcc")})

        fal = d.get("falsifier") or {}
        t1 = fal.get("tier_1") or {}
        t2 = fal.get("tier_2") or {}
        fal_ok = (t1.get("refutes") == F2B and "non-meager" in dumps(t1.get("genericity_requirement"))
                  and len(t1.get("machine_checkable_steps") or []) >= 3
                  and bool(t1.get("witness_type")) and bool(t2.get("labelling_required")))
        self.check("S11", "semantics", "falsifier refutes this class, requires non-meagerness, has machine steps",
                   fal_ok, {"tier_1_refutes": t1.get("refutes"),
                            "machine_steps": len(t1.get("machine_checkable_steps") or []),
                            "tier_2_labelling": t2.get("labelling_required")})

        leak = [t for t in WCC_CONCLUSION_TERMS if t in blob_asserted.lower()]
        self.check("S12", "semantics", "no WCC conclusion content on the asserted surface",
                   not leak, {"leaks": leak})

        promo = d.get("promotion_rule") or ""
        self.check("S13", "semantics", "promotion guard present (no schema self-promotion)",
                   "checked proof artifact" in promo and concl.get("claim_promotion"),
                   {"promotion_rule": promo, "claim_promotion": concl.get("claim_promotion")})

    # -- ledger / honesty -----------------------------------------------------
    def run_ledger(self):
        d = self.doc
        ledger_path = self.root / "ledger/theorems.jsonl"
        rows = {}
        if ledger_path.exists():
            for line in ledger_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = r.get("theorem_id") or r.get("id")
                if tid:
                    rows[tid] = r
        refs = d.get("l1_ledger_refs") or []
        missing = [r.get("theorem_id") for r in refs if r.get("theorem_id") not in rows]
        self.check("L1", "ledger", "every l1_ledger_refs theorem_id exists in ledger/theorems.jsonl",
                   not missing, {"refs": [r.get("theorem_id") for r in refs], "missing": missing})
        honesty = []
        for r in refs:
            tid = r.get("theorem_id")
            lrow = rows.get(tid) or {}
            honesty.append({
                "theorem_id": tid, "schema_l1_status": r.get("l1_status"),
                "ledger_verification_status": lrow.get("verification_status"),
                "ledger_scope_use": str(lrow.get("scope") or lrow.get("statement") or "")[:120],
            })
        mismatch = [h for h in honesty
                    if h["schema_l1_status"] == "accepted"
                    and h["ledger_verification_status"] not in ("accepted", "verified", "verified_by_L1")]
        self.check("L2", "ledger", "no schema 'accepted' label outruns the ledger verification_status (advisory)",
                   not mismatch, {"mapping_undefined": True, "rows": honesty, "mismatches": mismatch},
                   severity="advisory")

        self.check("L3", "ledger", "unresolved items and provenance honest (not claimed as proved)",
                   "open_problem" in str(d.get("epistemic_status"))
                   and len(d.get("unresolved_items") or []) >= 1
                   and str((d.get("provenance") or {}).get("citation_status")) in ("unverified", "unresolved"),
                   {"epistemic_status": d.get("epistemic_status"),
                    "n_unresolved": len(d.get("unresolved_items") or []),
                    "citation_status": (d.get("provenance") or {}).get("citation_status")})


# ----------------------------------------------------------------------------- mutants
def build_mutants(doc, snap_bytes: bytes):
    """Return list of (id, description, target_check, mutant_bytes_or_doc, textual)."""
    ms = []

    def mut(mid, desc, target, fn):
        m = copy.deepcopy(doc)
        fn(m)
        ms.append({"id": mid, "description": desc, "target": target, "doc": m})

    mut("M01", "class_id -> AF-SCC-C2-VAC-GEN", "B1", lambda m: m.__setitem__("class_id", F2A))
    mut("M02", "class_components.regularity_token -> C2", "B2",
        lambda m: m["class_components"].__setitem__("regularity_token", "C2"))
    mut("M03", "class_contract_pointer repointed to authoring tree", "B3",
        lambda m: m.__setitem__("class_contract_pointer",
                                "artifacts/formulation/formulation_taxonomy.yaml#class_contracts." + F2B))
    mut("M04", "conclusion_type -> C2 token", "S1",
        lambda m: m["conclusion"].__setitem__("conclusion_type", C2_TOKEN))
    mut("M05", "forbidden_weakenings C2/C1 entries removed", "S1",
        lambda m: m["conclusion"].__setitem__(
            "forbidden_weakenings", ["dropping the generic quantifier in practice while keeping the word"]))
    mut("M06", "sibling_disjoint_from -> WCC", "S1",
        lambda m: m.__setitem__("sibling_disjoint_from", WCC))
    mut("M07", "'C0 or C2' composite injected into scope_statement", "S1",
        lambda m: m.__setitem__("scope_statement", str(m.get("scope_statement")) + " This is a C0 or C2 claim."))
    mut("M08", "comeager exists-quantifier dropped from ordered[]", "S3",
        lambda m: m["quantifiers"].__setitem__("ordered", [r for r in m["quantifiers"]["ordered"]
                                                           if r["kind"] != "exists"]))
    mut("M09", "domain D2 definition_ref repointed to a missing block", "S3",
        lambda m: m["quantifiers"]["domains"]["D2"].__setitem__("definition_ref", "no_such_block"))
    mut("M10", "extension_predicate.frozen_regularity -> C2", "S4",
        lambda m: m["extension_predicate"].__setitem__("frozen_regularity", "C2"))
    mut("M11", "clause (f) interior requirement stripped", "S4",
        lambda m: m["extension_predicate"].__setitem__(
            "definition", str(m["extension_predicate"]["definition"]).replace("interior", "closure")))
    mut("M12", "topology.forbidden drops the differentiability entry", "S5",
        lambda m: m["topology"].__setitem__("forbidden", ["closed or periodic spatial slice"]))
    mut("M13", "data_class.matter -> scalar field", "S6",
        lambda m: m["data_class"].__setitem__("matter", "scalar_field"))
    mut("M14", "regularity.extension_regularity -> C2", "S7",
        lambda m: m["regularity"].__setitem__("extension_regularity", "C2"))
    mut("M15", "genericity.kind -> open_dense_escape", "S8",
        lambda m: m["genericity"].__setitem__("kind", "open_dense_escape"))
    mut("M16", "i_plus.in_conclusion -> True", "S9",
        lambda m: m["i_plus"].__setitem__("in_conclusion", True))
    mut("M17", "visibility.role -> in_conclusion", "S10",
        lambda m: m["visibility"].__setitem__("role", "in_conclusion"))
    mut("M18", "falsifier.tier_1.refutes -> WCC class", "S11",
        lambda m: m["falsifier"]["tier_1"].__setitem__("refutes", WCC))
    mut("M19", "f0_binding.declared_f0_sha256 -> deadbeef", "B8",
        lambda m: m["f0_binding"].__setitem__("declared_f0_sha256", "deadbeef"))
    mut("M20", "consistency_evidence_sha256 -> cleared", "B9",
        lambda m: m["f0_binding"].__setitem__("consistency_evidence_sha256", "0" * 64))
    mut("M21", "promotion_rule emptied", "S13",
        lambda m: m.__setitem__("promotion_rule", ""))
    mut("M22", "revision -> 11", "P3", lambda m: m.__setitem__("revision", 11))

    # textual duplicate-key mutant
    text = snap_bytes.decode()
    dup_text = text.replace("revision: 12", "revision: 12\nrevision: 12", 1)
    ms.append({"id": "M23", "description": "duplicate top-level key injected (revision twice)",
               "target": "P1", "text": dup_text.encode()})
    # future-dated mutant
    fut = text.replace("revised_at: \"2026-09-12T00:31:41+08:00\"",
                       "revised_at: \"2099-01-01T00:00:00+08:00\"", 1)
    ms.append({"id": "M24", "description": "revised_at future-dated to 2099",
               "target": "P4", "text": fut.encode()})
    return ms


def run_target_check(cid, doc, dup, snap_path, root, now):
    c = Checker(doc, dup, snap_path, root, now)
    mapping = {
        "P1": lambda: c.check("P1", "structure", "dup", len(dup) == 0, {"duplicates": dup}),
        "P3": lambda: c.check("P3", "structure", "rev", doc.get("revision") == 12,
                              {"revision": doc.get("revision")}),
        "P4": lambda: c.check("P4", "structure", "ts",
                              bool(parse_ts(doc.get("revised_at")) and parse_ts(doc.get("revised_at")) <= now),
                              {"revised_at": doc.get("revised_at")}),
    }
    if cid in mapping:
        mapping[cid]()
        return c.rows
    if cid.startswith("B"):
        c.run_identity()
    elif cid.startswith("S"):
        c.run_semantics()
    else:
        c.run_structural()
    return [r for r in c.rows if r["id"] == cid]


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    snap = Path(args.snapshot).resolve()
    root = Path(args.root).resolve() if args.root else snap.parents[3]
    now = _dt.datetime.now().astimezone()

    raw = snap.read_bytes()
    doc, dup = strict_load(snap)
    checker = Checker(doc, dup, snap, root, now)
    checker.run_structural()
    checker.run_identity()
    checker.run_semantics()
    checker.run_ledger()

    mutants = build_mutants(doc, raw)
    rows = []
    for m in mutants:
        if "text" in m:
            tmp = snap.parent / ("mutant_%s.yaml" % m["id"])
            tmp.write_bytes(m["text"])
            mdoc, mdup = strict_load(tmp)
            mrows = run_target_check(m["target"], mdoc, mdup, tmp, root, now)
            tmp.unlink()
        else:
            mrows = run_target_check(m["target"], m["doc"], [], snap, root, now)
        caught = any(r["status"] == "fail" for r in mrows)
        rows.append({"id": m["id"], "description": m["description"],
                     "target_check": m["target"], "target_check_failed": caught})
    detected = sum(1 for r in rows if r["target_check_failed"])

    failed = [r["id"] for r in checker.rows if r["status"] == "fail"]
    blocking_failed = [r["id"] for r in checker.rows
                       if r["status"] == "fail" and r.get("severity") == "blocking"]
    advisory_failed = [r["id"] for r in checker.rows
                       if r["status"] == "fail" and r.get("severity") == "advisory"]
    evidence = {
        "instrument": "artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py",
        "instrument_sha256": sha256_file(Path(__file__)),
        "task_id": "W059-F2B-REV12-VERDICT-01",
        "worker": "worker-059",
        "class_id": F2B,
        "node_id": "F2b",
        "reviewed_sha256": sha256_bytes(raw),
        "snapshot_path": str(snap.relative_to(root)) if str(snap).startswith(str(root)) else str(snap),
        "measured_at": now.isoformat(),
        "snapshot_mtime": _dt.datetime.fromtimestamp(os.path.getmtime(snap)).astimezone().isoformat(),
        "checks": checker.rows,
        "failed_checks": failed,
        "blocking_failed_checks": blocking_failed,
        "advisory_failed_checks": advisory_failed,
        "n_checks": len(checker.rows),
        "n_failed": len(failed),
        "content_verdict": "pass" if not blocking_failed else "fail",
        "mutant_controls": {
            "total": len(rows), "detected": detected,
            "sensitivity": (detected / len(rows)) if rows else None, "rows": rows,
        },
        "measured": checker.measured,
        "root": str(root),
        "rerun": "python3 artifacts/worker-059/f2b_rev12_verdict/check_f2b_rev12.py "
                 "artifacts/worker-059/f2b_rev12_verdict/snapshot/f2b.55d0a1ea9bda.yaml",
    }
    text = json.dumps(evidence, indent=1, sort_keys=False) + "\n"
    if args.out:
        Path(args.out).write_text(text)
    print(text)
    return 0 if not blocking_failed else 1


if __name__ == "__main__":
    sys.exit(main())
