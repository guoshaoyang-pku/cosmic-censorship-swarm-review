#!/usr/bin/env python3
"""Independent non-author review instrument for F2b / AF-SCC-C0-VAC-GEN.

Owner: worker-072 (bounded execution worker). Written for task W072-F2B-REVIEW-REV29-01.

SCOPE.  This instrument is deliberately NOT a wrapper of the canonical formulation gate
(artifacts/formulation/tools/check_class_schema.py).  It re-derives the review questions
from the raw YAML so that the verdict does not inherit the canonical gate's blind spots:

  * binding   : target sha256, mirror identity, FROZEN rev29 pin chain, f0 hash chain,
                pointer resolution, refresh rule;
  * class     : C0/C2 regularity separation, composite-regularity ban, implication-ledger
                direction, axis roles (I+/visibility), anti-scope, foreign-regularity
                hypotheses inside extension_predicate;
  * conclusion: epistemic status, no theorem promotion, falsifier shape and decidability
                honesty, provenance honesty;
  * flag      : candidate-variant class-id-shaped tokens (the rev27 soft flag near line 316);
  * vacuity   : genericity and non-vacuity gating.

The canonical gate is run as an ADDITIONAL advisory check (x1) over a subprocess so the
report records both verdicts and any disagreement.

USAGE
  python3 check_f2b.py --json [--schema PATH] [--expected-sha HEX] [--frozen PATH]
  exit 0 = all required checks pass, 1 = at least one FAIL, 2 = usage/unreadable input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA = ROOT / "schemas/af_scc_c0_vacuum.yaml"
DEFAULT_MIRROR = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
DEFAULT_FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SIBLING_C2 = ROOT / "schemas/af_scc_c2_vacuum.yaml"
CANON_TAX = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP_TAX = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"

CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
EXPECTED_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
EXPECTED_FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
EXPECTED_CONCLUSION = "scc_c0_future_inextendibility"
EXPECTED_C2_CONCLUSION = "scc_c2_future_inextendibility"
FROZEN_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CLASS_TOKEN = re.compile(r"\bAF-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
# composite regularity: "C0 or C2", "continuous and twice-differentiable", "C0/C2", ...
COMPOSITE = re.compile(
    r"\b(C0|C2|C\^?0|C\^?2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b\s*,?\s*"
    r"(or|and|/)\s*(?:\w+\s+){0,2}\b(C0|C2|C\^?0|C\^?2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b",
    re.I)
FOREIGN_REG = re.compile(r"\bC\^?2\b|\bC\^?\{?1,1\}?\b|\bH2_loc\b|\bLipschitz\b|\btwice[- ]differentiable\b", re.I)
NEG = re.compile(r"\b(no|not|never|cannot|unavailable|undefined|forbidden|must not|may not|different|"
                 r"weaker|stronger|subset|distinct|excludes?|without)\b", re.I)
EXEMPT_KEY = re.compile(
    r"^(forbidden|must_not|anti_scope|not_|excluded|variants|phrases_that_are_not|why_|reason$|"
    r"sibling_|derived_|visible_singularity_is_wcc$|no_|never_|c0_uniqueness_caveat$|"
    r"composite_regularity_ban$|terminology_disambiguation$|schema_falsifiers$|vacuity_falsifier$|"
    r"class_change_warning$|subsumption_note$|observability_note$|equivalence_claim$|"
    r"non_goals$|forbidden_strengthenings$|forbidden_weakenings$|forbidden_transfers$|"
    r"forbidden_falsifier$|promotion_rule$|promotion_rule$)", re.I)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text())


def strings_at(doc, *path):
    cur = doc
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return []
        cur = cur[p]
    out = []
    if isinstance(cur, str):
        out.append(cur)
    elif isinstance(cur, list):
        for x in cur:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                out.extend(str(v) for v in x.values() if isinstance(v, str))
    elif isinstance(cur, dict):
        out.extend(str(v) for v in cur.values() if isinstance(v, str))
    return out


def walk_strings(node, path="$", key=None):
    """Yield (path, key, string) for every string not under an exempt key."""
    if key is not None and EXEMPT_KEY.match(str(key)):
        return
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}", k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}[{i}]", key)
    elif isinstance(node, str):
        yield path, key, node


class Review:
    def __init__(self, schema: Path, mirror: Path, frozen: Path, expected_sha: str, expected_frozen: str,
                 controls: bool = False):
        self.schema, self.mirror, self.frozen = schema, mirror, frozen
        self.expected_sha, self.expected_frozen = expected_sha, expected_frozen
        self.controls = controls  # control mode: binding/advisory failures are expected, noted not failed
        self.results = []
        self.doc = None
        self.sha_before = sha256_file(schema) if schema.exists() else None
        self.frozen_doc = json.loads(frozen.read_text()) if frozen.exists() else {}
        self.c2 = load_yaml(SIBLING_C2) if SIBLING_C2.exists() else {}

    def add(self, cid, status, detail):
        self.results.append({"id": cid, "status": status, "detail": detail})

    def need(self, cid, ok, detail):
        if self.controls and re.match(r"^(b\d|x1|z1)", cid):
            self.add(cid, "NOTE", f"[control mode] {detail}")
            return
        self.add(cid, "PASS" if ok else "FAIL", detail)

    def run(self):
        try:
            self.doc = load_yaml(self.schema)
        except Exception as e:  # noqa: BLE001
            self.add("parse", "FAIL", f"cannot parse {self.schema}: {e}")
            return self.results
        d = self.doc
        fb = d.get("f0_binding") or {}
        files = self.frozen_doc.get("files") or {}

        # ---------------- binding ----------------
        self.need("b1_target_pin", self.sha_before == self.expected_sha,
                  f"measured {self.sha_before} expected {self.expected_sha}")
        mirror_sha = sha256_file(self.mirror) if self.mirror.exists() else None
        self.need("b2_mirror_identity", mirror_sha == self.sha_before,
                  f"canonical {self.sha_before} authoring {mirror_sha}")
        frozen_sha = sha256_file(self.frozen) if self.frozen.exists() else None
        self.need("b3_frozen_self", frozen_sha == self.expected_frozen,
                  f"measured {frozen_sha} expected {self.expected_frozen} rev={self.frozen_doc.get('revision')}")
        rel = str(self.schema.relative_to(ROOT)) if self.schema.is_absolute() else str(self.schema)
        pin = (files.get(rel) or {}).get("sha256")
        self.need("b4_frozen_pin", pin == self.sha_before, f"FROZEN[{rel}].sha256={pin} measured={self.sha_before}")
        rel_m = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
        pin_m = (files.get(rel_m) or {}).get("sha256")
        self.need("b5_frozen_pin_authoring", pin_m == mirror_sha, f"FROZEN[{rel_m}].sha256={pin_m} measured={mirror_sha}")
        supp = "artifacts/formulation/formulation_taxonomy.yaml"
        supp_live = sha256_file(ROOT / supp) if (ROOT / supp).exists() else None
        supp_pin = (files.get(supp) or {}).get("sha256")
        self.need("b6_supplement_pin", supp_pin == supp_live, f"FROZEN pin={supp_pin} live={supp_live}")
        f0_ref = str(fb.get("declared_f0_artifact", ""))
        f0_live = sha256_file(ROOT / f0_ref) if (ROOT / f0_ref).exists() else None
        self.need("b7_declared_f0_resolves", fb.get("declared_f0_sha256") == f0_live,
                  f"declared={fb.get('declared_f0_sha256')} live={f0_live}")
        ce_ref = str(fb.get("consistency_evidence", ""))
        ce_live = sha256_file(ROOT / ce_ref) if (ROOT / ce_ref).exists() else None
        self.need("b8_consistency_evidence_resolves", fb.get("consistency_evidence_sha256") == ce_live,
                  f"declared={fb.get('consistency_evidence_sha256')} live={ce_live}")
        cons_doc = json.loads((ROOT / ce_ref).read_text()) if (ROOT / ce_ref).exists() else {}
        self.need("b9_consistency_reported", cons_doc.get("consistent") is True,
                  f"{ce_ref} consistent={cons_doc.get('consistent')} errors={cons_doc.get('errors')}")
        tax = load_yaml(CANON_TAX) if CANON_TAX.exists() else {}
        sup = load_yaml(SUPP_TAX) if SUPP_TAX.exists() else {}
        p1 = str(d.get("class_contract_pointer", ""))
        p2 = str(d.get("class_contract_supplement_pointer", ""))
        self.need("b10_pointers_resolve",
                  CLASS_ID in (tax.get("classes") or {}) and CLASS_ID in (sup.get("class_contracts") or {})
                  and CLASS_ID in p1 and CLASS_ID in p2,
                  f"canonical classes={CLASS_ID in (tax.get('classes') or {})} supplement={CLASS_ID in (sup.get('class_contracts') or {})}")
        self.need("b11_refresh_rule_satisfied", fb.get("declared_f0_sha256") == f0_live and fb.get("checked_at"),
                  f"declared==live:{fb.get('declared_f0_sha256') == f0_live} checked_at={fb.get('checked_at')}")

        # ---------------- class separation ----------------
        self.need("c1_identity", d.get("class_id") == CLASS_ID and d.get("node_id") == NODE_ID,
                  f"class_id={d.get('class_id')} node_id={d.get('node_id')} revision={d.get('revision')}")
        c0_type = ((d.get("conclusion") or {}).get("conclusion_type"))
        c2_type = ((self.c2.get("conclusion") or {}).get("conclusion_type"))
        self.need("c2_conclusion_type_distinct",
                  c0_type == EXPECTED_CONCLUSION and c2_type == EXPECTED_C2_CONCLUSION and c0_type != c2_type,
                  f"C0={c0_type!r} C2={c2_type!r}")
        ep = d.get("extension_predicate") or {}
        want = {"frozen_direction": "future", "frozen_regularity": "C0", "frozen_equation_concept": "none"}
        self.need("c3_extension_axes", all(ep.get(k) == v for k, v in want.items()),
                  f"{ {k: ep.get(k) for k in want} }")
        reg = d.get("regularity") or {}
        self.need("c4_regularity_axes",
                  reg.get("extension_regularity") == "C0" and reg.get("extension_solution_concept") == "none",
                  f"extension_regularity={reg.get('extension_regularity')!r} extension_solution_concept={reg.get('extension_solution_concept')!r}")
        hits = [(p, s[:90]) for p, _k, s in walk_strings(d) if COMPOSITE.search(s)]
        self.need("c5_composite_ban", not hits, f"{len(hits)} non-exempt composite-regularity strings" + (f": {hits[:3]}" if hits else ""))
        il = d.get("implication_ledger") or {}
        owe = il.get("one_way_entailments") or []
        ft = il.get("forbidden_transfers") or []
        c0_to_c2 = any("C0" in str(e.get("from", "")) and "C2" in str(e.get("to", "")) for e in owe)
        c2_to_c0_forbidden = any(
            "C2" in str(e.get("from", "")) and (CLASS_ID in str(e.get("to", "")) or "this class" in str(e.get("to", "")).lower())
            for e in ft)
        converse_owed = any("C2" in str(e.get("from", "")) and "C0" in str(e.get("to", "")) for e in owe)
        self.need("c6_implication_direction", c0_to_c2 and c2_to_c0_forbidden and not converse_owed,
                  f"c0->c2={c0_to_c2} c2->c0 forbidden={c2_to_c0_forbidden} converse owed={converse_owed}")
        ip, vis = d.get("i_plus") or {}, d.get("visibility") or {}
        self.need("c7_axis_roles",
                  ip.get("role") == "assumption" and ip.get("in_conclusion") is False
                  and vis.get("role") == "not_in_conclusion" and bool(vis.get("reason"))
                  and bool(vis.get("forbidden_falsifier")),
                  f"i_plus.role={ip.get('role')} in_conclusion={ip.get('in_conclusion')} visibility.role={vis.get('role')}")
        anti = d.get("anti_scope") or {}
        anti_blob = json.dumps(anti)
        self.need("c8_anti_scope", "AF-SCC-C2-VAC-GEN" in anti_blob and "AF-WCC-VAC-GEN" in anti_blob,
                  f"lists C2={'AF-SCC-C2-VAC-GEN' in anti_blob} WCC={'AF-WCC-VAC-GEN' in anti_blob}")
        freg = []
        for p, _k, s in walk_strings(ep):
            if FOREIGN_REG.search(s) and not NEG.search(s):
                freg.append((p, s[:90]))
        self.need("c9_no_foreign_regularity_in_extension",
                  not freg, f"{len(freg)} foreign-regularity assertions in extension_predicate" + (f": {freg[:2]}" if freg else ""))
        wcc_leak = []
        for p in (("conclusion",), ("i_plus",), ("visibility",)):
            for s in strings_at(d, *p):
                if re.search(r"\bcomplete(ness)?\b", s, re.I) and not NEG.search(s):
                    wcc_leak.append((".".join(p), s[:90]))
        self.need("c10_conclusion_no_wcc_completeness", not wcc_leak,
                  f"{len(wcc_leak)} unnegated completeness assertions in conclusion/I+/visibility" + (f": {wcc_leak[:2]}" if wcc_leak else ""))

        # ---------------- conclusion / assumptions ----------------
        conc = d.get("conclusion") or {}
        self.need("d1_status_open", conc.get("epistemic_status") == "open_problem" and bool(d.get("promotion_rule")),
                  f"epistemic_status={conc.get('epistemic_status')} promotion_rule={'promotion_rule' in d}")
        stmts = strings_at(d, "conclusion", "statement_natural_language") + strings_at(d, "conclusion", "statement_formal")
        promote = [s[:90] for s in stmts if re.search(r"\b(we prove|we establish|is proved|is established|theorem)\b", s, re.I) and not NEG.search(s)]
        self.need("d2_no_theorem_promotion", not promote, f"{len(promote)} promoting statements" + (f": {promote}" if promote else ""))
        f1 = (d.get("falsifier") or {}).get("tier_1") or {}
        f2 = (d.get("falsifier") or {}).get("tier_2") or {}
        self.need("d3_falsifier_shape",
                  f1.get("refutes") == CLASS_ID and "extension" in str(f1.get("witness_type", "")).lower()
                  and bool(f1.get("machine_checkable_steps")) and bool(f1.get("non_machine_checkable_step"))
                  and f2.get("labelling_required") == "refutes_strengthening_only",
                  f"tier1.refutes={f1.get('refutes')} machine_steps={len(f1.get('machine_checkable_steps') or [])} "
                  f"non_machine={bool(f1.get('non_machine_checkable_step'))} tier2_label={f2.get('labelling_required')!r}")
        pr = d.get("provenance") or {}
        self.need("d4_provenance_honesty",
                  pr.get("citation_status") == "unverified" and bool(pr.get("unresolved_citations"))
                  and bool(d.get("unresolved_items")) and (pr.get("no_progress_claim") is not None),
                  f"citation_status={pr.get('citation_status')!r} unresolved_citations={len(pr.get('unresolved_citations') or [])} "
                  f"unresolved_items={len(d.get('unresolved_items') or [])} no_progress_claim={'no_progress_claim' in pr}")
        self.need("d5_forbidden_lists",
                  bool(conc.get("forbidden_strengthenings")) and bool(conc.get("forbidden_weakenings")),
                  f"strengthenings={len(conc.get('forbidden_strengthenings') or [])} weakenings={len(conc.get('forbidden_weakenings') or [])}")

        # ---------------- soft flag / candidate class tokens ----------------
        raw_lines = self.schema.read_text().splitlines()
        tok_rows = []
        for i, line in enumerate(raw_lines, 1):
            for m in CLASS_TOKEN.finditer(line):
                if m.group(0) not in FROZEN_CLASSES:
                    tok_rows.append({"line": i, "token": m.group(0), "text": line.strip()[:110]})
        self.need("e1_no_foreign_class_ids", not tok_rows,
                  f"{len(tok_rows)} class-id-shaped tokens outside the frozen four" + (f": {tok_rows[:4]}" if tok_rows else ""))
        window = [{"line": i, "text": raw_lines[i - 1].strip()[:120]} for i in range(300, min(len(raw_lines), 330) + 1)]
        window_tokens = [{"line": w["line"], "token": CLASS_TOKEN.search(w["text"]).group(0), "text": w["text"]}
                         for w in window if CLASS_TOKEN.search(w["text"])]
        self.need("e2_flag_window_disposed",
                  all(t["token"] in FROZEN_CLASSES for t in window_tokens) if window_tokens else True,
                  f"lines 300-330: {len(window_tokens)} class-id-shaped tokens, all frozen={all(t['token'] in FROZEN_CLASSES for t in window_tokens)}; "
                  f"line 316={raw_lines[315].strip()[:90]!r}")
        variant_blob = json.dumps(d.get("class_identity_variants") or {})
        variant_ok = ("parent_class" in variant_blob or "variant_id" in variant_blob) and "is_this_class" in variant_blob
        self.need("e3_variant_registry_context", variant_ok,
                  f"class_identity_variants carries parent_class/variant_id/is_this_class={variant_ok}")

        # ---------------- vacuity / genericity ----------------
        nv = d.get("non_vacuity") or {}
        cond = str(nv.get("condition", ""))
        self.need("f1_non_vacuity",
                  bool(re.search(r"incomplete|not a regular|singular|failure of extendibility|Cauchy horizon", cond, re.I))
                  and bool(nv.get("vacuity_falsifier")) and bool(nv.get("witness_type")),
                  f"condition gates on non-regular/incomplete=True vacuity_falsifier={bool(nv.get('vacuity_falsifier'))} witness={bool(nv.get('witness_type'))}")
        gen = d.get("genericity") or {}
        self.need("f2_genericity",
                  gen.get("kind") == "residual_comeager" and gen.get("is_part_of_class") is True
                  and bool(re.search(r"comeager|intersection", str(gen.get("generic_set", "")), re.I))
                  and bool(gen.get("transfer_failures")) and bool(gen.get("class_change_warning")),
                  f"kind={gen.get('kind')} is_part_of_class={gen.get('is_part_of_class')} transfer_rows={len(gen.get('transfer_failures') or [])}")

        # ---------------- advisory: canonical gate subprocess ----------------
        if GATE.exists():
            r = subprocess.run([sys.executable, str(GATE), "--json", str(self.schema)],
                               capture_output=True, text=True)
            try:
                rep = json.loads(r.stdout)
                status = "NOTE" if self.controls else ("PASS" if rep.get("verdict") == "pass" else "FAIL")
                self.add("x1_canonical_gate", status,
                         f"verdict={rep.get('verdict')} failed_rules={rep.get('failed_rules')}")
            except ValueError:
                self.add("x1_canonical_gate", "NOTE" if self.controls else "FAIL",
                         f"unparseable gate output: {r.stdout[-200:]!r} stderr={r.stderr[-200:]!r}")

        # ---------------- stability ----------------
        sha_after = sha256_file(self.schema)
        self.add("z1_hash_stable", "PASS" if sha_after == self.sha_before else "FAIL",
                 f"before={self.sha_before} after={sha_after}")
        return self.results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--mirror", default=str(DEFAULT_MIRROR))
    ap.add_argument("--frozen", default=str(DEFAULT_FROZEN))
    ap.add_argument("--expected-sha", default=EXPECTED_SHA)
    ap.add_argument("--expected-frozen", default=EXPECTED_FROZEN_SHA)
    ap.add_argument("--controls", action="store_true", help="control-mutant mode: binding checks noted, not failed")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    schema = Path(a.schema)
    if not schema.exists():
        print(f"schema not found: {schema}", file=sys.stderr)
        return 2
    rv = Review(schema, Path(a.mirror), Path(a.frozen), a.expected_sha, a.expected_frozen, controls=a.controls)
    res = rv.run()
    fails = [r for r in res if r["status"] == "FAIL"]
    out = {"schema": str(schema), "class_id": (rv.doc or {}).get("class_id"),
           "sha256_before": rv.sha_before, "checks": res,
           "n_pass": sum(1 for r in res if r["status"] == "PASS"),
           "n_fail": len(fails), "verdict": "PASS" if not fails else "FAIL"}
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"{out['verdict']} {schema} sha={str(out['sha256_before'])[:12]} "
              f"pass={out['n_pass']} fail={out['n_fail']}")
        for r in fails:
            print(f"  FAIL {r['id']}: {r['detail']}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
