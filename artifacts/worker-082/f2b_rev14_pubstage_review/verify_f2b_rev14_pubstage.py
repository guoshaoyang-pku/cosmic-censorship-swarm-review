#!/usr/bin/env python3
"""W082-F2B-REV14-PUBSTAGE-REVIEW-01 independent checker.

Read-only on every canonical path.  Writes only under the directory holding this file.
No network.  Stdlib + PyYAML.

What it decides (worker evidence only; no gate verdict, no node status):

  P1  pin discipline: target sha256 measured before and after the read; a drift aborts.
  S1  YAML parses and contains no duplicate mapping keys (custom loader).
  S2  class identity + canonical, sibling-distinguishable conclusion_type.
  S3  composite-regularity scan, re-implemented from the canonical stage-A rule R13:
        S3a outside revision_history  -> must be zero for an accept
        S3b inside  revision_history  -> reported; stage-A R13 does not exempt it
  S4  D1 repair: regularity.must_not_conflate[0] states the nested extension sets in the
      direction declared by F0 and no longer denies containment.
  S5  D2 repair: implication_ledger.forbidden_transfers[0].reason no longer says
      "strictly larger extension class" and gives the direction-correct subset reason.
  S6  containment model extracted from F0 (pinned) vs every containment claim in the schema.
  S7  declared-hash bind chain resolves to live bytes (F0, consistency evidence, pointers).
  S8  canonical stage-A instrument check_class_schema.py re-run on a frozen snapshot.
  S9  no conclusion inflation (theorem/counterexample promotion).
  S10 assumption completeness (quantifiers + typed domains + clauses (a)-(f) + axes).
  S11 variant / anti-scope class-id-shaped tokens are disposed as annotations, not classes.
  S12 falsifier is decidable and machine-checkable steps are present.
  S13 revision metadata present and coherent (revision bumped, history entry appended).
  S14 revised_at is not future-dated relative to the measurement instant (CF-14 class).
  S15 publication state: FROZEN.json per-file pin for this schema vs the measured bytes
      (a state observation, reported separately from artifact-content checks).
  D1  diff scope vs the rev13 predecessor: only the authorized leaf paths changed.

Negative controls K1..K9 must flip the named check; a control that does not fire makes
this review's own instrument invalid (format-dominated), exactly as in the held-out cards.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TARGET_REL = "schemas/af_scc_c0_vacuum.yaml"
SIBLING_REL = "schemas/af_scc_c2_vacuum.yaml"
PREDECESSOR_REL = "artifacts/worker-082/a1_xtarget_census/snapshots/af_scc_c0_vacuum.b2ab6acb2bbe.yaml"
F0_REL = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT_REL = "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
VOCAB_REL = "artifacts/formulation/VOCAB_ALIASES.json"
STAGE_A_REL = "artifacts/formulation/tools/check_class_schema.py"

F0_PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
REV13_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"

# ---- canonical stage-A lexical rules, re-implemented (check_class_schema.py:47-96) ----
EXEMPT_KEY = re.compile(
    r"^(forbidden|must_not|anti_scope|not_|excluded|variants|phrases_that_are_not|why_|reason$|"
    r"sibling_|derived_|visible_singularity_is_wcc$|no_|never_|c0_uniqueness_caveat$|"
    r"composite_regularity_ban$|terminology_disambiguation$|schema_falsifiers$|vacuity_falsifier$|"
    r"class_change_warning$|subsumption_note$|observability_note$|equivalence_claim$|"
    r"non_goals$|forbidden_strengthenings$|forbidden_weakenings$|forbidden_transfers$)", re.I)
COMPOSITE = re.compile(r"(C0|C2|C\^?0|C\^?2)\s*(or|and|/)\s*(C0|C2|C\^?0|C\^?2)", re.I)
COMPOSITE_PROSE = re.compile(
    r"\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b\s*,?\s*(or|and|/|alternatively)\s*"
    r"(?:\w+\s+){0,2}\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b", re.I)

CONTAINMENT_CHAIN = re.compile(
    r"E_C2\s+subset of\s+E_\{?C\^1,1\}?\s+subset of\s+E_H2loc\s+subset of\s+E_C0", re.I)
NESTED_ORDER_BAD = re.compile(r"E_C0\s+subset of\s+.*E_C2", re.I)

REQUIRED_TOP = [
    "schema_version", "artifact_kind", "class_id", "node_id", "owner", "authored_by",
    "authored_at", "revised_at", "revision_history", "revision", "class_components",
    "class_contract_pointer", "scope_statement", "quantifiers", "extension_predicate",
    "topology", "data_class", "regularity", "genericity", "non_vacuity", "i_plus",
    "visibility", "conclusion", "implication_ledger", "falsifier", "anti_scope",
    "class_identity_variants", "known_status", "f0_binding", "provenance",
    "unresolved_items", "review_status",
]


class DupLoader(yaml.SafeLoader):
    duplicates: list = []


def _construct_mapping(loader, node, deep=False):
    keys = []
    for k, _ in node.value:
        try:
            kk = loader.construct_object(k, deep=deep)
        except Exception:
            kk = None
        if kk in keys:
            loader.duplicates.append(str(kk))
        keys.append(kk)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def parse_yaml(raw: str):
    DupLoader.duplicates = []
    doc = yaml.load(raw, Loader=DupLoader)
    return doc, list(DupLoader.duplicates)


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def flat_get(flat, rel):
    return flat.get(rel)


def strings_in(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += strings_in(v, f"{prefix}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += strings_in(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        out.append((prefix, obj))
    return out


def scan_composite(node, path="$", hits=None):
    """Exact re-implementation of check_class_schema.py::scan_composite."""
    if hits is None:
        hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            if EXEMPT_KEY.match(str(k)):
                continue
            scan_composite(v, f"{path}.{k}", hits)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            scan_composite(v, f"{path}[{i}]", hits)
    elif isinstance(node, str) and (COMPOSITE.search(node) or COMPOSITE_PROSE.search(node)):
        hits.append(path)
    return hits


def load_f0_model():
    """Extract the authoritative containment direction from the pinned F0 taxonomy."""
    f0_path = ROOT / F0_REL
    raw = f0_path.read_text()
    f0_hash = sha256_bytes(raw.encode())
    doc = yaml.safe_load(raw)
    flat = flatten(doc)
    meaning_c2 = next((v for k, v in flat.items()
                       if isinstance(v, str) and "does NOT forbid C^{1,1} or H^2_loc" in v), None)
    meaning_c0 = next((v for k, v in flat.items()
                       if isinstance(v, str) and "strictly stronger than the C2 conclusion" in v), None)
    return {
        "path": F0_REL, "sha256": f0_hash, "pin_match": f0_hash == F0_PIN,
        "meaning_c2_path": next((k for k, v in flat.items()
                                 if isinstance(v, str) and "does NOT forbid C^{1,1} or H^2_loc" in v), None),
        "meaning_c2_says_larger_classes": bool(meaning_c2 and "strictly larger classes" in meaning_c2),
        "meaning_c0_path": next((k for k, v in flat.items()
                                 if isinstance(v, str) and "strictly stronger than the C2 conclusion" in v), None),
        "meaning_c0_says_strictly_stronger": bool(meaning_c0 and "strictly stronger than the C2 conclusion" in meaning_c0),
        "c2_excerpt": (meaning_c2 or "")[:320],
        "c0_excerpt": (meaning_c0 or "")[:280],
    }


def resolve_pointer(doc, pointer: str) -> bool:
    """pointer 'path#a.b.c' -> the dotted key path resolves in doc."""
    cur = doc
    for part in pointer.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    return True


def run_checks(schema_path: Path, expect_sha=None, snapshot_path=None) -> dict:
    """Core check battery. Returns {checks: {id: {ok, detail}}, ...}."""
    t0 = time.time()
    raw_bytes = schema_path.read_bytes()
    measured = sha256_bytes(raw_bytes)
    raw = raw_bytes.decode()
    doc, dups = parse_yaml(raw)
    flat = flatten(doc)
    checks = {}

    def rec(cid, ok, detail, severity="content", falsifier=""):
        checks[cid] = {"ok": bool(ok), "detail": detail,
                       "severity": severity, "falsifier": falsifier}

    # P1 pin
    rec("P1_pin_declared", expect_sha is None or measured == expect_sha,
        f"measured={measured} expected={expect_sha}",
        falsifier="a byte move of the target voids the whole review")

    # S1 parse + duplicate keys
    rec("S1_parse_no_duplicate_keys", doc is not None and not dups,
        f"parsed={doc is not None} duplicate_keys={dups}",
        falsifier="re-run parse_yaml on the same bytes; a duplicate mapping key is a hard failure")

    # S2 class identity + conclusion token
    conc = (doc or {}).get("conclusion", {})
    tok = conc.get("conclusion_type")
    vocab = json.loads((ROOT / VOCAB_REL).read_text())["conclusion_type"]
    canon = set(vocab.keys())
    aliases = {a for v in vocab.values() for a in v}
    sib_tok = yaml.safe_load((ROOT / SIBLING_REL).read_text())["conclusion"]["conclusion_type"]
    rec("S2_class_identity_and_token",
        (doc or {}).get("class_id") == "AF-SCC-C0-VAC-GEN"
        and (doc or {}).get("node_id") == "F2b"
        and tok == "scc_c0_future_inextendibility"
        and tok in canon and tok not in aliases
        and tok != sib_tok and sib_tok == "scc_c2_future_inextendibility",
        f"class_id={(doc or {}).get('class_id')} node_id={(doc or {}).get('node_id')} "
        f"token={tok} canonical={tok in canon} alias={tok in aliases} sibling_token={sib_tok}",
        falsifier="a schema whose conclusion token is not the canonical C0 token, equals the C2 sibling's, or is an alias")

    # S3 composite scan (canonical R13 re-implementation)
    hits = scan_composite(doc)
    hist_hits = [h for h in hits if h.startswith("$.revision_history")]
    other_hits = [h for h in hits if not h.startswith("$.revision_history")]
    rec("S3a_no_composite_outside_revision_history", not other_hits,
        f"hits_outside_revision_history={other_hits}",
        falsifier="a composite regularity token in a non-exempt class-semantic field")
    rec("S3b_no_composite_in_revision_history", not hist_hits,
        f"hits_in_revision_history={hist_hits} "
        f"(canonical stage-A R13 does not exempt revision_history; each hit is a stage-A failure)",
        falsifier="re-run check_class_schema.py on the same bytes; a pass means this finding is void")

    # S4 D1 repair
    mnc = ((doc or {}).get("regularity") or {}).get("must_not_conflate") or []
    mnc0 = mnc[0] if mnc else ""
    rec("S4_d1_containment_repair",
        bool(mnc0) and bool(CONTAINMENT_CHAIN.search(mnc0))
        and "no containment" not in mnc0.lower()
        and "ENTAILS H2_loc-inextendibility and C2-inextendibility" in mnc0
        and "never the reverse" in mnc0,
        f"must_not_conflate[0]={mnc0[:400]}",
        falsifier="re-introduce the containment denial or invert the chain and re-run")

    # S5 D2 repair
    fts = ((doc or {}).get("implication_ledger") or {}).get("forbidden_transfers") or []
    ft0 = (fts[0] or {}).get("reason", "") if fts else ""
    rec("S5_d2_forbidden_transfer_reason",
        bool(ft0) and "strictly larger extension class" not in ft0
        and "strictly stronger regularity requirement" in ft0
        and ("E_C2 subset of E_C0" in ft0 or "E_C2 ⊆ E_C0" in ft0),
        f"forbidden_transfers[0].reason={ft0}",
        falsifier="re-introduce 'strictly larger extension class' and re-run")

    # S6 F0 vs schema containment consistency
    f0 = load_f0_model()
    one_way = ((doc or {}).get("implication_ledger") or {}).get("one_way_entailments") or []
    ow_reasons = " || ".join(str((r or {}).get("reason", "")) for r in one_way)
    chain_decl = ((doc or {}).get("implication_ledger") or {}).get(
        "extension_class_containment", "")
    sub_note = ((doc or {}).get("implication_ledger") or {}).get("subsumption_note", "")
    bad_dir = bool(NESTED_ORDER_BAD.search(mnc0)) or bool(NESTED_ORDER_BAD.search(chain_decl))
    rec("S6_f0_direction_consistency",
        f0["pin_match"] and f0["meaning_c2_says_larger_classes"]
        and f0["meaning_c0_says_strictly_stronger"]
        and not bad_dir
        and "E_H2loc subset of E_C0" in ow_reasons
        and "E_C2 subset of E_H2loc" in ow_reasons
        and "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2" in chain_decl
        and "C0 => H2loc => C2" in sub_note,
        f"f0_pin_match={f0['pin_match']} f0_c2_larger={f0['meaning_c2_says_larger_classes']} "
        f"f0_c0_stronger={f0['meaning_c0_says_strictly_stronger']} inverted_chain={bad_dir} "
        f"chain_decl_present={'E_C0 contains E_H2loc' in chain_decl}",
        falsifier="a nested-order inversion or a subset reason contradicting F0's meaning_C2/meaning_C0")

    # S7 bind chain
    fb = (doc or {}).get("f0_binding") or {}
    live_f0 = sha256_file(ROOT / F0_REL)
    live_cons = sha256_file(ROOT / CONSISTENCY_REL)
    supp = yaml.safe_load((ROOT / SUPPLEMENT_REL).read_text())
    c0_pointer = (doc or {}).get("class_contract_pointer", "")
    supp_pointer = (doc or {}).get("class_contract_supplement_pointer", "")
    ptr_ok = bool(c0_pointer) and resolve_pointer(yaml.safe_load((ROOT / F0_REL).read_text()),
                                                  c0_pointer.split("#", 1)[1])
    supp_ok = bool(supp_pointer) and resolve_pointer(supp, supp_pointer.split("#", 1)[1])
    rec("S7_bind_chain_resolves",
        fb.get("declared_f0_sha256") == live_f0 == F0_PIN
        and fb.get("consistency_evidence_sha256") == live_cons
        and ptr_ok and supp_ok,
        f"declared_f0={str(fb.get('declared_f0_sha256'))[:12]} live_f0={live_f0[:12]} "
        f"declared_consistency={str(fb.get('consistency_evidence_sha256'))[:12]} live_consistency={live_cons[:12]} "
        f"class_pointer_resolves={ptr_ok} supplement_pointer_resolves={supp_ok}",
        falsifier="any declared sha256 that does not equal its named live file, or a dangling pointer")

    # S9 no conclusion inflation
    known = (doc or {}).get("known_status") or {}
    rec("S9_no_conclusion_inflation",
        tok not in ("theorem", "counterexample")
        and conc.get("epistemic_status") == "open_problem"
        and bool(conc.get("claim_promotion"))
        and "open_problem" in str(known.get("status", ""))
        and "theorem" not in str((doc or {}).get("claims_theorem_status", "")).lower(),
        f"token={tok} epistemic_status={conc.get('epistemic_status')} "
        f"known_status={known.get('status')} claim_promotion_present={bool(conc.get('claim_promotion'))}",
        falsifier="a conclusion_type of theorem/counterexample or a missing promotion rule")

    # S10 assumption completeness
    q = (doc or {}).get("quantifiers") or {}
    doms = q.get("domains") or {}
    ordered = q.get("ordered") or []
    ext_def = str(((doc or {}).get("extension_predicate") or {}).get("definition", ""))
    clauses = all(f"({c})" in ext_def for c in "abcdef")
    axis_roles = (
        ((doc or {}).get("i_plus") or {}).get("role") == "assumption"
        and ((doc or {}).get("visibility") or {}).get("role") == "not_in_conclusion"
        and bool((doc or {}).get("data_class")) and bool((doc or {}).get("genericity"))
        and bool((doc or {}).get("topology")) and bool((doc or {}).get("regularity"))
    )
    d0_typed = "tagged disjoint union" in str((doms.get("D0") or {}).get("definition", ""))
    rec("S10_assumption_completeness",
        len(ordered) == 4
        and [o.get("kind") for o in ordered] == ["forall", "exists", "forall", "not_exists"]
        and all(k in doms for k in ("D0", "D1", "D2", "D3"))
        and all(isinstance(doms[k], dict) and doms[k].get("definition") and doms[k].get("definition_ref")
                for k in ("D0", "D1", "D2", "D3"))
        and d0_typed and clauses and axis_roles,
        f"ordered={[o.get('kind') for o in ordered]} domains={sorted(doms)} d0_typed={d0_typed} "
        f"extension_clauses_a_f={clauses} axis_roles_ok={axis_roles}",
        falsifier="a missing typed quantifier domain, an untyped D0 binder, a missing extension clause or axis")

    # S11 variant / anti-scope token disposal
    anti = ((doc or {}).get("anti_scope") or {}).get("not_this_class") or []
    variants = (doc or {}).get("class_identity_variants") or {}
    anti_ok = all(
        (e.get("class_id") != "AF-SCC-C0-VAC-GEN") or e.get("kind") in
        ("regularity_axis_variant", "equation_concept_variant")
        for e in anti if isinstance(e, dict))
    var_ok = all(
        (v.get("is_this_class") is False)
        for k, v in variants.items() if isinstance(v, dict) and k != "frozen_broad_statement")
    no_live_variant_class = not any(
        isinstance(v, dict) and "conclusion_type" in v for v in variants.values())
    rec("S11_variant_tokens_disposed",
        anti_ok and var_ok and no_live_variant_class
        and "C0 or C2" in " ".join(
            ((doc or {}).get("anti_scope") or {}).get("phrases_that_are_not_this_class") or []),
        f"anti_scope_entries={len(anti)} anti_disposed={anti_ok} variants_disposed={var_ok} "
        f"no_variant_conclusion_type={no_live_variant_class}",
        falsifier="a variant entry presented as a live separate class or an undisposed class-id-shaped token")

    # S12 decidable falsifier
    f = (doc or {}).get("falsifier") or {}
    t1 = f.get("tier_1") or {}
    t2 = f.get("tier_2") or {}
    rec("S12_decidable_falsifier",
        bool(t1.get("refutes")) and bool(t1.get("witness_type"))
        and isinstance(t1.get("machine_checkable_steps"), list) and len(t1["machine_checkable_steps"]) >= 3
        and bool(t1.get("non_machine_checkable_step"))
        and bool(t2.get("labelling_required")) and bool(f.get("schema_falsifiers")),
        f"tier_1_refutes={t1.get('refutes')} witness_type_len={len(str(t1.get('witness_type','')))} "
        f"machine_steps={len(t1.get('machine_checkable_steps') or [])} "
        f"non_machine_step={bool(t1.get('non_machine_checkable_step'))} tier_2_labelling={t2.get('labelling_required')}",
        falsifier="an empty witness type, missing machine-checkable steps, or an undecidable falsifier")

    # S13 revision metadata
    rh = (doc or {}).get("revision_history") or []
    last = rh[-1] if rh else {}
    rec("S13_revision_metadata",
        (doc or {}).get("revision") == 14
        and len(rh) >= 12 and last.get("index") == 12 and last.get("unused") is False
        and isinstance(last.get("notes"), list) and len(last["notes"]) >= 1
        and bool((doc or {}).get("revised_at")),
        f"revision={(doc or {}).get('revision')} n_history={len(rh)} "
        f"last_index={last.get('index')} last_unused={last.get('unused')} revised_at={(doc or {}).get('revised_at')}",
        falsifier="a rev14 publication that does not bump revision/history or drops revised_at")

    # S14 clock discipline
    now = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    revised_at = str((doc or {}).get("revised_at", ""))
    rec("S14_revised_at_not_future", revised_at <= now,
        f"revised_at={revised_at} measured_at={now}",
        severity="clock", falsifier="a revised_at later than the wall-clock at review time")

    # S15 publication state (FROZEN per-file pin)
    frozen = json.loads((ROOT / FROZEN_REL).read_text())
    fpin = (frozen.get("files") or {}).get(TARGET_REL, {}).get("sha256")
    rec("S15_frozen_pin_matches_live", fpin == measured,
        f"frozen_revision={frozen.get('revision')} frozen_pin={str(fpin)[:12]} live={measured[:12]}",
        severity="state", falsifier="a FROZEN re-issue whose per-file pin equals the live bytes clears this state finding")

    return {
        "schema_path": str(schema_path), "schema_sha256": measured,
        "bytes": len(raw_bytes), "measurement_started": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime(t0)),
        "checks": checks, "composite_hits_all": hits,
        "f0_model": f0,
        "snapshot": str(snapshot_path) if snapshot_path else None,
        "duplicate_keys": dups,
    }


def diff_scope(predecessor: Path, target: Path):
    pred = flatten(yaml.safe_load(predecessor.read_text()))
    targ = flatten(yaml.safe_load(target.read_text()))
    changed = []
    for k in sorted(set(pred) | set(targ)):
        if pred.get(k) != targ.get(k):
            changed.append({"path": k, "old": pred.get(k), "new": targ.get(k)})
    return changed


AUTHORIZED_EXACT = {
    "$.revision", "$.revised_at",
    "$.regularity.must_not_conflate[0]",
    "$.implication_ledger.forbidden_transfers[0].reason",
}
AUTHORIZED_PREFIX = ("$.revision_history[11]",)


def is_authorized(path: str) -> bool:
    return path in AUTHORIZED_EXACT or path.startswith(AUTHORIZED_PREFIX)


def mutate_and_check(base_doc, base_raw, name, mutator, expect_check, expect_ok, tmpdir: Path):
    doc = copy.deepcopy(base_doc)
    raw = base_raw
    mutator(doc, raw)
    p = tmpdir / f"{name}.yaml"
    # re-emit only for doc mutations; raw mutations are supplied directly
    if getattr(mutator, "raw_bytes", None) is not None:
        p.write_bytes(mutator.raw_bytes)
    else:
        p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=10**6))
    res = run_checks(p)
    observed = res["checks"].get(expect_check, {}).get("ok")
    return {"control": name, "expect_check": expect_check, "expect_ok": expect_ok,
            "observed": observed,
            "fired": observed == expect_ok,
            "detail": res["checks"].get(expect_check, {}).get("detail")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default=str(ROOT / TARGET_REL))
    ap.add_argument("--expect-sha", default=None)
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--controls", action="store_true")
    args = ap.parse_args()

    schema = Path(args.schema).resolve()
    before = sha256_file(schema)
    if args.expect_sha and before != args.expect_sha:
        print(json.dumps({"abort": "moving-target", "measured": before,
                          "expected": args.expect_sha}, indent=1))
        return 2
    snap_dir = HERE / "snapshot"
    snap_dir.mkdir(exist_ok=True)
    snap = snap_dir / f"{schema.name}.{before[:12]}.yaml"
    snap.write_bytes(schema.read_bytes())
    result = run_checks(schema, expect_sha=args.expect_sha, snapshot_path=snap)

    # canonical stage-A re-run on the frozen snapshot (read-only on canonical paths)
    stage_a = subprocess.run(
        [sys.executable, str(ROOT / STAGE_A_REL), "--json", str(snap)],
        capture_output=True, text=True)
    try:
        stage_a_json = json.loads(stage_a.stdout)
    except Exception:
        stage_a_json = {"parse_error": stage_a.stdout[:400]}
    result["stage_a"] = {
        "tool": STAGE_A_REL, "tool_sha256": sha256_file(ROOT / STAGE_A_REL),
        "exit_code": stage_a.returncode, "report": stage_a_json,
        "stderr": stage_a.stderr[:300],
    }

    # diff scope vs the rev13 predecessor
    pred = ROOT / PREDECESSOR_REL
    result["predecessor"] = {"path": PREDECESSOR_REL, "sha256": sha256_file(pred),
                             "pin_match": sha256_file(pred) == REV13_PIN}
    changed = diff_scope(pred, snap)
    unauthorized = [c for c in changed if not is_authorized(c["path"])]
    result["diff"] = {"changed_leaf_paths": changed,
                      "n_changed": len(changed),
                      "unauthorized": unauthorized,
                      "scope_ok": not unauthorized}
    result["checks"]["D1_diff_scope_authorized"] = {
        "ok": not unauthorized,
        "detail": f"n_changed={len(changed)} unauthorized={[c['path'] for c in unauthorized]}",
        "severity": "content",
        "falsifier": "a changed leaf path outside the REC-36 items 1-2 + revision metadata"}

    # drift guard after all reads
    after = sha256_file(schema)
    result["pin_after"] = after
    result["pin_stable"] = after == before

    # negative controls
    if args.controls:
        ctrl = HERE / "controls"
        ctrl.mkdir(exist_ok=True)
        base_doc, base_raw = parse_yaml(snap.read_text())
        controls = []

        def k1(doc, raw):
            doc["regularity"]["must_not_conflate"][0] = (
                "H2_loc is a distinct regularity-axis value. No containment with C2 or C0 is "
                "asserted here; the informal phrase 'strictly between' is not used.")

        def k2(doc, raw):
            doc["implication_ledger"]["forbidden_transfers"][0]["reason"] = (
                "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker")

        def k3(doc, raw):
            doc["regularity"]["must_not_conflate"][0] = (
                "The extension sets are nonetheless nested: E_C0 subset of E_H2loc subset of "
                "E_{C^1,1} subset of E_C2, so this class's conclusion ENTAILS H2_loc-inextendibility "
                "and C2-inextendibility, never the reverse.")

        def k4(doc, raw):
            k4.raw_bytes = raw.replace(
                "revision: 14", "revision: 14\nrevision: 13", 1).encode()

        k4.raw_bytes = None

        def k5(doc, raw):
            doc["conclusion"]["conclusion_type"] = "scc_c2_future_inextendibility"

        def k6(doc, raw):
            doc["f0_binding"]["declared_f0_sha256"] = "0" * 64

        def k7(doc, raw):
            doc["falsifier"]["tier_1"]["machine_checkable_steps"] = []

        def k8(doc, raw):
            k8.raw_bytes = raw.replace(" the H2_loc and C2 conclusions", " both sibling conclusions", 1).encode()

        k8.raw_bytes = None

        def k9(doc, raw):
            del doc["implication_ledger"]["one_way_entailments"][:]

        for fn, expect, expect_ok in (
                (k1, "S4_d1_containment_repair", False),
                (k2, "S5_d2_forbidden_transfer_reason", False),
                (k3, "S4_d1_containment_repair", False),
                (k4, "S1_parse_no_duplicate_keys", False),
                (k5, "S2_class_identity_and_token", False),
                (k6, "S7_bind_chain_resolves", False),
                (k7, "S12_decidable_falsifier", False),
                (k8, "S3b_no_composite_in_revision_history", True),
                (k9, "S6_f0_direction_consistency", False)):
            controls.append(mutate_and_check(base_doc, base_raw, fn.__name__, fn,
                                             expect, expect_ok, ctrl))
        result["controls"] = controls
        result["controls_all_fired"] = all(c["fired"] for c in controls)

    Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=True))
    hard = [k for k, v in result["checks"].items()
            if not v["ok"] and v.get("severity") == "content"]
    print(json.dumps({
        "target": result["schema_path"], "sha256": result["schema_sha256"],
        "pin_stable": result["pin_stable"], "stage_a_exit": result["stage_a"]["exit_code"],
        "hard_failures": hard,
        "state_findings": [k for k, v in result["checks"].items()
                           if not v["ok"] and v.get("severity") == "state"],
        "clock_findings": [k for k, v in result["checks"].items()
                           if not v["ok"] and v.get("severity") == "clock"],
        "diff_unauthorized": [c["path"] for c in result["diff"]["unauthorized"]],
        "controls_all_fired": result.get("controls_all_fired"),
        "report": args.out,
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
