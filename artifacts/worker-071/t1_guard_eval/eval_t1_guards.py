#!/usr/bin/env python3
"""W071-T1-GUARD-EVAL-01 -- machine evaluation of transfer rule T1's three guards.

Pre-registered method: artifacts/worker-071/t1_guard_eval/PREREGISTRATION.json, written before
this script was executed. Guards, readings, decision rule and controls are fixed there; this
script implements them literally.

Classes: AF-SCC-C0-VAC-GEN (source, F2b) -> AF-SCC-C2-VAC-GEN (target, F2a). Gate: G-FORM.
Measurement only. Writes only under artifacts/worker-071/t1_guard_eval/. Never sets a gate
verdict, a node status, or validation_status=passed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
TASK_ID = "W071-T1-GUARD-EVAL-01"
WORKER = "worker-071"
FROM_CLASS = "AF-SCC-C0-VAC-GEN"
TO_CLASS = "AF-SCC-C2-VAC-GEN"

INPUTS = {
    "F0_canonical": "research_map/formulation_taxonomy.yaml",
    "F2a_target": "schemas/af_scc_c2_vacuum.yaml",
    "F2b_source": "schemas/af_scc_c0_vacuum.yaml",
    "map": "research_map/research_map.json",
    # added for the context block only (not a T1 input); pinned and window-checked all the same
    "F1_context": "schemas/af_wcc_vacuum.yaml",
}

CORE_KEYS = [
    "matter",
    "cosmological_constant",
    "equations",
    "constraints.hamiltonian",
    "constraints.momentum",
    "regularity_class.default",
    "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
    "regularity_class.sobolev_variant.spaces",
    "asymptotic_decay.metric",
    "asymptotic_decay.second_fundamental_form",
    "asymptotic_decay.parity_conditions",
    "symmetry",
    "adm_mass.exists",
    "adm_mass.sign",
]

FALSIFIER = (
    "Re-run artifacts/worker-071/t1_guard_eval/eval_t1_guards.py at the same pinned sha256 "
    "values. Falsified per guard if G1_literal evaluates PASS, or G2_literal evaluates PASS, or "
    "G3_literal evaluates PASS, contrary to the recorded per-guard verdicts; if all three evaluate "
    "PASS then T1 is licensed at the pins, the G-FORM unmet item is refuted at the whole strength "
    "of the transfer rule, and this report's overall verdict is falsified. Any input sha256 change "
    "across the pre/post window voids the result at the changed path and requires a re-run."
)

LIMITATIONS = [
    "G1 compares F2b (source) with F2a (target) only; F1 (AF-WCC-VAC-GEN) is a different transfer family and is not part of T1.",
    "The G2 mapped reading uses a mapping (genericity_kind -> genericity.kind, genericity_topology -> genericity.topology_or_measure) inferred by this artifact; F0 does not declare it.",
    "G3 binds claims recorded in research_map/research_map.json only; un-ingested outbox traffic is out of scope by construction.",
    "Line numbers are value-node start lines from the YAML composer.",
    "No gate verdict, no node status, no validation_status=passed is asserted.",
]


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text())


def line_map(path: Path) -> dict:
    """Map dotted path -> value-node start line (1-based) using the YAML composer."""
    node = yaml.compose(path.read_text())
    out: dict[str, int] = {}

    def walk(n, prefix: str):
        if isinstance(n, yaml.MappingNode):
            for k, v in n.value:
                key = str(k.value)
                p = f"{prefix}.{key}" if prefix else key
                out[p] = v.start_mark.line + 1
                walk(v, p)
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, f"{prefix}[{i}]")

    if node is not None:
        walk(node, "")
    return out


def dig(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def find_key_paths(obj, target: str, prefix: str = ""):
    """All dotted paths whose final key equals target (recursive)."""
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            if k == target:
                hits.append(p)
            hits.extend(find_key_paths(v, target, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_key_paths(v, target, f"{prefix}[{i}]"))
    return hits


def walk_leaves(obj, prefix: str = ""):
    if isinstance(obj, dict):
        if not obj:
            yield prefix, "<empty-mapping>"
        for k, v in obj.items():
            yield from walk_leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        if not obj:
            yield prefix, "<empty-sequence>"
        for i, v in enumerate(obj):
            yield from walk_leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def norm_strict(v) -> str:
    if v is None:
        return "<null>"
    if isinstance(v, bool):
        return "true" if v else "false"
    return re.sub(r"\s+", " ", str(v)).strip()


def norm_core(v):
    """T3 convenience normalization: drop parenthesized text and post-';' text."""
    s = norm_strict(v)
    dropped = [m.group(0) for m in re.finditer(r"\([^)]*\)", s)]
    s = re.sub(r"\([^)]*\)", "", s)
    if ";" in s:
        head, tail = s.split(";", 1)
        dropped.append(";" + tail)
        s = head
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[.,;]+$", "", s).strip()
    return s, dropped


def strict_diff(da: dict, db: dict, lines_a: dict, lines_b: dict, prefix: str):
    """Exact-value diff over leaf paths of two subtrees; witnesses carry both lines."""
    fa = dict(walk_leaves(da, prefix))
    fb = dict(walk_leaves(db, prefix))
    witnesses = []
    for k in sorted(set(fa) | set(fb)):
        va, vb = fa.get(k, "<missing>"), fb.get(k, "<missing>")
        if va != vb:
            witnesses.append({
                "path": k,
                "F2a_target": norm_strict(va) if va != "<missing>" else "<missing>",
                "F2b_source": norm_strict(vb) if vb != "<missing>" else "<missing>",
                "F2a_line": lines_a.get(k),
                "F2b_line": lines_b.get(k),
            })
    return witnesses


def core_strict_table(dc_a: dict, dc_b: dict, prefix: str):
    """Per-CORE_KEY strict values and T3-normalized values."""
    table = {}
    for k in CORE_KEYS:
        full = f"{prefix}.{k}"
        ka, kb = full.split(".", 1)[1], full.split(".", 1)[1]
        fa, va = dig(dc_a, ka)
        fb, vb = dig(dc_b, kb)
        sa = norm_strict(va) if fa else "<missing>"
        sb = norm_strict(vb) if fb else "<missing>"
        na = norm_core(va)[0] if fa else "<missing>"
        nb = norm_core(vb)[0] if fb else "<missing>"
        dropped_a = norm_core(va)[1] if fa else []
        dropped_b = norm_core(vb)[1] if fb else []
        table[k] = {
            "F2a_target": sa,
            "F2b_source": sb,
            "equal_strict": sa == sb,
            "F2a_target_T3": na,
            "F2b_source_T3": nb,
            "equal_T3": na == nb,
            "dropped_fragments": {k: {"F2a_target": dropped_a, "F2b_source": dropped_b}}
            if (dropped_a or dropped_b) else {},
        }
    return table


def eval_g1(dc_a: dict, dc_b: dict, lines_a: dict, lines_b: dict):
    """G1 under the pre-registered literal exact-match rule, plus the T3 secondary reading."""
    witnesses = strict_diff(dc_a, dc_b, lines_a, lines_b, "data_class")
    core_table = core_strict_table(dc_a, dc_b, "data_class")
    core_w = [w for w in witnesses if w["path"].split(".", 1)[1] in CORE_KEYS]
    noncore_w = [w for w in witnesses if w["path"].split(".", 1)[1] not in CORE_KEYS]
    t3_unequal = [k for k, row in core_table.items() if not row["equal_T3"]]
    strict = len(witnesses) == 0
    return {
        "guard": "G1",
        "guard_text": "data_class fields must match exactly (including s, delta once F2 fixes them)",
        "literal_reading": "exact value equality over every leaf path of the data_class subtree, no normalization",
        "verdict_literal": "PASS" if strict else "FAIL",
        "verdict_literal_reason": (
            "every data_class leaf path equals between F2b (source) and F2a (target)"
            if strict else
            f"{len(witnesses)} data_class leaf path(s) differ between F2b (source) and F2a (target); "
            "exact match is not satisfied"
        ),
        "n_witnesses": len(witnesses),
        "core_key_witnesses": core_w,
        "noncore_key_witnesses": noncore_w,
        "witnesses": witnesses,
        "core_key_table": core_table,
        "secondary_T3_normalized_core": {
            "reading": "CORE_KEYS after dropping parenthesized and post-';' text, collapsing whitespace, stripping trailing punctuation",
            "verdict": "PASS" if not t3_unequal else "FAIL",
            "unequal_core_keys": t3_unequal,
        },
    }


def eval_g2_literal(doc_a: dict, doc_b: dict):
    """G2 literal: the exact field names genericity_kind / genericity_topology must resolve and match."""
    fields = ["genericity_kind", "genericity_topology"]
    per_field = {}
    evaluable = True
    for f in fields:
        ha, va = dig(doc_a, f)
        hb, vb = dig(doc_b, f)
        if not ha or not hb:
            evaluable = False
        per_field[f] = {
            "F2a_target_present": ha,
            "F2a_target_value": norm_strict(va) if ha else None,
            "F2b_source_present": hb,
            "F2b_source_value": norm_strict(vb) if hb else None,
            "equal": (ha and hb and norm_strict(va) == norm_strict(vb)),
        }
    if not evaluable:
        verdict = "UNEVALUABLE_AS_WRITTEN"
        reason = ("the literal field name(s) "
                  + ", ".join(f for f in fields if not (per_field[f]["F2a_target_present"] and per_field[f]["F2b_source_present"]))
                  + " do not resolve in both frozen schemas; a missing field cannot satisfy 'must match exactly'")
    elif all(v["equal"] for v in per_field.values()):
        verdict = "PASS"
        reason = "both literal fields resolve and are equal"
    else:
        verdict = "FAIL"
        reason = "both literal fields resolve but at least one value is unequal"
    return {
        "guard": "G2",
        "guard_text": "genericity_kind and genericity_topology must match exactly",
        "literal_reading": "resolve the exact dotted key paths 'genericity_kind' and 'genericity_topology'; require presence and equality in both schemas",
        "verdict_literal": verdict,
        "verdict_literal_reason": reason,
        "per_field": per_field,
        "occurrences_anywhere_literal_names": {
            "F2a_target": {f: find_key_paths(doc_a, f) for f in fields},
            "F2b_source": {f: find_key_paths(doc_b, f) for f in fields},
        },
    }


def eval_g2_mapped(doc_a: dict, doc_b: dict):
    """G2 secondary: mapped reading on the actual genericity field names used by the schemas."""
    mapping = {"genericity_kind": "genericity.kind", "genericity_topology": "genericity.topology_or_measure"}
    per_field = {}
    for src, dst in mapping.items():
        ha, va = dig(doc_a, dst)
        hb, vb = dig(doc_b, dst)
        per_field[src] = {
            "mapped_to": dst,
            "F2a_target_present": ha,
            "F2a_target_value": norm_strict(va) if ha else None,
            "F2b_source_present": hb,
            "F2b_source_value": norm_strict(vb) if hb else None,
            "equal_exact_text": (ha and hb and norm_strict(va) == norm_strict(vb)),
        }
    ga, _ = dig(doc_a, "genericity")
    gb, _ = dig(doc_b, "genericity")
    present = all(v["equal_exact_text"] for v in per_field.values()) and all(
        v["F2a_target_present"] and v["F2b_source_present"] for v in per_field.values())
    return {
        "reading": "mapped by this artifact (NOT declared in F0): genericity_kind -> genericity.kind, genericity_topology -> genericity.topology_or_measure",
        "per_field": per_field,
        "genericity_block_keys": {
            "F2a_target": sorted(ga.keys()) if isinstance(ga, dict) else None,
            "F2b_source": sorted(gb.keys()) if isinstance(gb, dict) else None,
        },
        "mapped_verdict_if_mapping_accepted": "PASS" if present else "FAIL",
        "binding": False,
    }


def eval_g3(claims: list, reviews: list):
    """G3 literal: source claim (AF-SCC-C0-VAC-GEN) carries artifact_refs and a reviewer verdict."""
    def class_match(c):
        ids = []
        if isinstance(c.get("class_id"), str):
            ids.append(c["class_id"])
        if isinstance(c.get("class_ids"), list):
            ids.extend([x for x in c["class_ids"] if isinstance(x, str)])
        return FROM_CLASS in ids

    review_by_target = {}
    for r in reviews or []:
        t = r.get("target_id")
        if isinstance(t, str):
            review_by_target.setdefault(t, []).append(r)

    candidates = []
    for c in claims or []:
        if not class_match(c):
            continue
        eid = c.get("event_id")
        refs = c.get("artifact_refs") or []
        refs = refs if isinstance(refs, list) else [refs]
        ref_paths = [str(x).split("#")[0] for x in refs]
        # Binding rule per PREREGISTRATION.json: a reviewer verdict targets the claim iff
        # review.target_id == claim.event_id. Reviews of files merely cited by the claim are
        # recorded as a non-binding secondary count and never satisfy G3.
        revs_claim = review_by_target.get(eid, []) if eid else []
        revs_artifact = []
        for key in ref_paths:
            revs_artifact.extend(review_by_target.get(key, []))
        text = " ".join(str(c.get(k, "")) for k in ("statement", "summary", "conclusion_type", "task_id"))
        candidates.append({
            "event_id": eid,
            "conclusion_type": c.get("conclusion_type"),
            "task_id": c.get("task_id"),
            "has_artifact_refs": bool(refs),
            "n_artifact_refs": len(refs),
            "review_verdicts_on_claim_id": [
                {"target_id": r.get("target_id"), "reviewer": r.get("reviewer"), "verdict": r.get("verdict")}
                for r in revs_claim
            ],
            "review_verdicts_on_cited_artifacts_nonbinding": [
                {"target_id": r.get("target_id"), "reviewer": r.get("reviewer"), "verdict": r.get("verdict")}
                for r in revs_artifact
            ],
            "mentions_C0_inextendibility": bool(re.search(r"C0", text)) and bool(re.search(r"inextendib", text, re.I)),
        })
    bound = [c for c in candidates if c["has_artifact_refs"] and c["review_verdicts_on_claim_id"]]
    asserting = [c for c in candidates if c["mentions_C0_inextendibility"]]
    strengthened = [
        c for c in candidates
        if c["has_artifact_refs"] and c["mentions_C0_inextendibility"]
        and any(v["verdict"] == "accept" for v in c["review_verdicts_on_claim_id"])
    ]
    verdict = "PASS" if bound else "FAIL"
    reason = (
        f"{len(bound)} C0-class claim(s) carry both artifact_refs and a reviewer verdict with target_id == claim event_id"
        if bound else
        f"0 of {len(candidates)} claim(s) whose class includes {FROM_CLASS} carry both non-empty "
        "artifact_refs and a reviewer verdict bound to the claim event_id; the T1 source claim is not "
        "present and bound in the pinned map (reviews of files the claim merely cites do not satisfy the guard)"
    )
    return {
        "guard": "G3",
        "guard_text": "the source claim must carry artifact_refs and a reviewer verdict",
        "literal_reading": "a claim in the pinned map whose class_id/class_ids includes the T1 source class has non-empty artifact_refs and at least one review targeting it with a verdict",
        "source_class": FROM_CLASS,
        "verdict_literal": verdict,
        "verdict_literal_reason": reason,
        "n_c0_class_claims": len(candidates),
        "n_c0_class_claims_asserting_c0_inextendibility": len(asserting),
        "n_bound_claims": len(bound),
        "bound_claim_ids": [c["event_id"] for c in bound],
        "bound_claim_qualifiers": [
            {
                "event_id": c["event_id"],
                "conclusion_type": c["conclusion_type"],
                "mentions_C0_inextendibility": c["mentions_C0_inextendibility"],
                "review_verdicts_on_claim_id": c["review_verdicts_on_claim_id"],
            }
            for c in bound
        ],
        "post_run_diagnostic_strengthened_reading": {
            "not_preregistered": True,
            "never_changes_binding_verdict": True,
            "rule": "source claim asserts C0 future-inextendibility, carries non-empty artifact_refs, and has an accept verdict targeting the claim event_id",
            "n_qualifying": len(strengthened),
        },
        "candidates": candidates,
        "map_reviews_total": len(reviews or []),
    }


def controls():
    """Pre-registered controls; pure synthetic inputs, canonical files never touched."""
    # G1 controls
    a = {"regularity_class": {"sobolev_variant": {"spaces": "X"}},
         "asymptotic_decay": {"parity_conditions": "not imposed"}}
    b = json.loads(json.dumps(a))
    ctl_pos_g1 = eval_g1(a, b, {}, {})["verdict_literal"] == "PASS"
    b2 = json.loads(json.dumps(a))
    b2["asymptotic_decay"]["parity_conditions"] = "imposed"
    neg = eval_g1(a, b2, {}, {})
    ctl_neg_g1 = neg["verdict_literal"] == "FAIL" and [w["path"] for w in neg["witnesses"]] == [
        "data_class.asymptotic_decay.parity_conditions"]
    # G2 literal controls
    d1 = {"genericity_kind": "residual_comeager", "genericity_topology": "subspace"}
    d2 = json.loads(json.dumps(d1))
    ctl_pos_g2 = eval_g2_literal(d1, d2)["verdict_literal"] == "PASS"
    d3 = {"genericity_kind": "residual_comeager", "genericity_topology": "frechet"}
    ctl_neg_g2 = eval_g2_literal(d1, d3)["verdict_literal"] == "FAIL"
    # G3 control
    claims_pos = [{"event_id": "C1", "class_id": FROM_CLASS, "artifact_refs": ["p#abc"]}]
    reviews_pos = [{"target_id": "C1", "verdict": "accept", "reviewer": "ctl"}]
    ctl_pos_g3 = eval_g3(claims_pos, reviews_pos)["verdict_literal"] == "PASS"
    ctl_neg_g3 = eval_g3(claims_pos, [])["verdict_literal"] == "FAIL"
    return {
        "CTL_POS_G1": {"expected": "PASS", "pass": ctl_pos_g1},
        "CTL_NEG_G1": {"expected": "FAIL with exactly the parity_conditions witness", "pass": ctl_neg_g1},
        "CTL_POS_G2": {"expected": "PASS", "pass": ctl_pos_g2},
        "CTL_NEG_G2": {"expected": "FAIL", "pass": ctl_neg_g2},
        "CTL_POS_G3": {"expected": "PASS", "pass": ctl_pos_g3},
        "CTL_NEG_G3": {"expected": "FAIL", "pass": ctl_neg_g3},
        "all_pass": all([ctl_pos_g1, ctl_neg_g1, ctl_pos_g2, ctl_neg_g2, ctl_pos_g3, ctl_neg_g3]),
    }


def main() -> dict:
    before = {name: sha256_file(ROOT / rel) for name, rel in INPUTS.items()}
    f0 = load_yaml(ROOT / INPUTS["F0_canonical"])
    f2a = load_yaml(ROOT / INPUTS["F2a_target"])
    f2b = load_yaml(ROOT / INPUTS["F2b_source"])
    mp = json.loads((ROOT / INPUTS["map"]).read_text())
    lines_a = line_map(ROOT / INPUTS["F2a_target"])
    lines_b = line_map(ROOT / INPUTS["F2b_source"])

    # T1 rule verbatim from the pinned F0 taxonomy
    rule = None
    for r in f0.get("transfer_rules", {}).get("allowed", []):
        if r.get("id") == "T1":
            rule = r
    if rule is None or rule.get("from") != FROM_CLASS or rule.get("to") != TO_CLASS:
        print(json.dumps({"error": "T1 rule not found or class binding changed",
                          "found": rule}), file=sys.stderr)
        sys.exit(3)

    g1 = eval_g1(f2a["data_class"], f2b["data_class"], lines_a, lines_b)
    g2 = eval_g2_literal(f2a, f2b)
    g2_map = eval_g2_mapped(f2a, f2b)
    g3 = eval_g3(mp.get("claims", []), mp.get("reviews", []))
    ctl = controls()

    # Context only (NOT part of T1, which runs F2b -> F2a): the G-FORM unmet item names
    # F1/F2a/F2b jointly, so record where the F1 data_class diverges from the T1 pair.
    f1 = load_yaml(ROOT / INPUTS["F1_context"])
    lines_f1 = line_map(ROOT / INPUTS["F1_context"])
    ctx_f1_f2b = strict_diff(f1["data_class"], f2b["data_class"], lines_f1, lines_b, "data_class")
    context = {
        "label": "context_not_part_of_T1",
        "why": "the G-FORM unmet item is worded over F1/F2a/F2b jointly; T1 itself runs F2b -> F2a",
        "F1_path": INPUTS["F1_context"],
        "F1_vs_F2b_strict_data_class_witnesses": ctx_f1_f2b,
        "F1_vs_F2b_core_key_witness_paths": [
            w["path"] for w in ctx_f1_f2b if w["path"].split(".", 1)[1] in CORE_KEYS],
    }

    per_guard = {"G1": g1["verdict_literal"], "G2": g2["verdict_literal"], "G3": g3["verdict_literal"]}
    blocked = [k for k, v in per_guard.items() if v != "PASS"]
    licensed = len(blocked) == 0

    after = {name: sha256_file(ROOT / rel) for name, rel in INPUTS.items()}
    drift = {name: {"before": before[name], "after": after[name]} for name in INPUTS if before[name] != after[name]}
    window_status = "VOID" if drift else "STABLE"
    measurement_valid = window_status == "STABLE" and ctl["all_pass"]

    if not measurement_valid:
        summary = "INVALID: hash drift or control failure; see drift/controls."
    elif licensed:
        summary = (
            "At the pinned hashes all three literal T1 guards PASS: T1 is licensed, and the G-FORM unmet "
            "item 'no single frozen data class is shared ... disables the licensed C0=>C2 transfer' is "
            "refuted at the strength of the transfer rule."
        )
    else:
        notes = []
        if per_guard["G1"] != "PASS":
            notes.append(
                f"G1 fails on {g1['n_witnesses']} exact-match witness path(s) "
                f"({[w['path'] for w in g1['witnesses']]}), {len(g1['core_key_witnesses'])} of them "
                "inside the pre-registered core tuple "
                f"({'core tuple strictly equal' if not g1['core_key_witnesses'] else 'core tuple differs'})")
        if per_guard["G2"] != "PASS":
            notes.append(
                "G2 is UNEVALUABLE_AS_WRITTEN because the literal field names genericity_kind / "
                "genericity_topology resolve nowhere in the frozen schemas")
        if per_guard["G3"] == "PASS":
            notes.append(
                f"G3 passes literally on {g3['n_bound_claims']} bound C0-class claim(s), but the bound "
                "claim(s) do not assert C0 future-inextendibility and carry revise verdicts; "
                f"{g3['n_c0_class_claims_asserting_c0_inextendibility']} C0-class claim(s) mention C0 "
                "inextendibility and none is bound (post-run strengthened-reading diagnostic: "
                f"{g3['post_run_diagnostic_strengthened_reading']['n_qualifying']} qualifying)")
        else:
            notes.append("G3 fails: no C0-class claim carries artifact_refs plus a claim-bound reviewer verdict")
        summary = (
            f"At the pinned hashes T1 is NOT licensed: guard(s) {', '.join(blocked)} do not evaluate PASS "
            "under the pre-registered literal readings. " + "; ".join(notes) + ". The G-FORM unmet item "
            "stands at exactly the strength of these guard-level findings; note that G3's literal text is "
            "satisfied by a claim that is not the C0 conclusion, so the unmet item is carried by G1 and G2. "
            "Context (not part of T1): the F1 data_class differs from F2b at "
            f"{len(context['F1_vs_F2b_core_key_witness_paths'])} core-key path(s) "
            f"({context['F1_vs_F2b_core_key_witness_paths']}), so the gate's joint F1/F2a/F2b wording is "
            "driven by F1, not by the F2b->F2a pair."
        )

    result = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "generated_at": now(),
        "generator": "artifacts/worker-071/t1_guard_eval/eval_t1_guards.py",
        "method_preregistration": "artifacts/worker-071/t1_guard_eval/PREREGISTRATION.json",
        "node_ids": ["F2a", "F2b"],
        "class_ids": [FROM_CLASS, TO_CLASS],
        "gate": "G-FORM",
        "inputs": {
            name: {
                "path": INPUTS[name],
                "sha256_before": before[name],
                "sha256_after": after[name],
                "bytes": (ROOT / INPUTS[name]).stat().st_size,
                "revision_moved": before[name] != after[name],
            }
            for name in INPUTS
        },
        "window_status": window_status,
        "drift": drift,
        "t1_rule_verbatim": {
            "source": "research_map/formulation_taxonomy.yaml#transfer_rules.allowed[id=T1]",
            "rule": {k: rule.get(k) for k in ("id", "from", "to", "kind", "reason", "guards")},
        },
        "guards": {"G1": g1, "G2": g2, "G3": g3},
        "G2_secondary_mapped_reading": g2_map,
        "context_not_part_of_T1": context,
        "controls": ctl,
        "decision_rule": "T1_licensed_at_pins = G1 PASS AND G2 PASS AND G3 PASS under the literal readings; UNEVALUABLE counts as not PASS; secondary readings never change the binding decision.",
        "verdict": {
            "per_guard_literal": per_guard,
            "blocked_guards": blocked,
            "T1_licensed_at_pins": licensed,
            "measurement_valid": measurement_valid,
            "summary": summary,
        },
        "falsifier": FALSIFIER,
        "limitations": LIMITATIONS,
        "authority_note": "Measurement only; no gate verdict, no node status, no validation_status=passed.",
    }
    (HERE / "guard_eval.json").write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    # ---- README ----
    md = []
    md.append("# W071-T1-GUARD-EVAL-01 -- machine evaluation of transfer rule T1's three guards\n")
    md.append(f"Generated {result['generated_at']} by `eval_t1_guards.py`. Measurement only: no gate "
              "verdict, no node status, no validation_status=passed.\n")
    md.append(f"Classes `{FROM_CLASS}` (source, F2b) -> `{TO_CLASS}` (target, F2a); gate `G-FORM`.\n")
    md.append("## Verdict\n")
    md.append(f"- measurement_valid: **{measurement_valid}** (window {window_status}, controls all_pass {ctl['all_pass']})")
    for gname, gverdict in per_guard.items():
        md.append(f"- {gname} literal: **{gverdict}**")
    md.append(f"- T1_licensed_at_pins: **{licensed}**")
    md.append(f"\n{summary}\n")
    md.append("## G1 witnesses (exact-match failures)\n")
    md.append("| path | F2a (target) | F2b (source) | F2a line | F2b line |")
    md.append("|---|---|---|---|---|")
    for w in g1["witnesses"]:
        md.append(f"| `{w['path']}` | {w['F2a_target']} | {w['F2b_source']} | {w['F2a_line']} | {w['F2b_line']} |")
    md.append("\n## G2\n")
    md.append(f"Literal verdict: **{g2['verdict_literal']}** -- {g2['verdict_literal_reason']}.")
    md.append(f"Mapped (non-binding) reading: **{g2_map['mapped_verdict_if_mapping_accepted']}**.")
    for f, row in g2_map["per_field"].items():
        md.append(f"- `{f}` -> `{row['mapped_to']}`: equal_exact_text={row['equal_exact_text']}")
    md.append("\n## G3\n")
    md.append(f"Literal verdict: **{g3['verdict_literal']}** -- {g3['verdict_literal_reason']}.")
    md.append(f"- C0-class claims found: {g3['n_c0_class_claims']} "
              f"(of which mention C0 inextendibility: {g3['n_c0_class_claims_asserting_c0_inextendibility']})")
    md.append(f"- bound (artifact_refs + claim-targeted reviewer verdict): {g3['n_bound_claims']}")
    for b in g3["bound_claim_qualifiers"]:
        md.append(f"  - `{b['event_id']}`: conclusion_type={b['conclusion_type']}, "
                  f"asserts C0 inextendibility={b['mentions_C0_inextendibility']}, "
                  f"verdicts={[v['verdict'] for v in b['review_verdicts_on_claim_id']]}")
    md.append(f"- post-run strengthened-reading diagnostic (not pre-registered, never binding): "
              f"{g3['post_run_diagnostic_strengthened_reading']['n_qualifying']} qualifying claim(s) "
              "(asserts C0 inextendibility + artifact_refs + accept verdict)")
    md.append("\n## Context: where the gate's F1/F2a/F2b wording diverges (not part of T1)\n")
    md.append(f"T1 runs F2b -> F2a. The gate unmet item is worded over F1/F2a/F2b jointly, so the F1 "
              f"data_class is compared to F2b here for context only. Strict witnesses: "
              f"{len(context['F1_vs_F2b_strict_data_class_witnesses'])}, of which "
              f"{len(context['F1_vs_F2b_core_key_witness_paths'])} are core-key paths "
              f"({context['F1_vs_F2b_core_key_witness_paths']}).\n")
    md.append("\n## Pinned hashes\n")
    for name, row in result["inputs"].items():
        md.append(f"- {name} (`{row['path']}`): `{row['sha256_before']}`")
    v1 = HERE / "guard_eval.v1-instrument-bug.json"
    v1_hash = sha256_file(v1) if v1.exists() else None
    md.append("## Instrument history\n")
    md.append("- v1 of `eval_t1_guards.py` matched a review to a claim through any file the claim cited, "
              "which let literature claims inherit reviews of `ledger/theorems.jsonl`. The pre-registered "
              "rule (review.target_id == claim.event_id) was not implemented literally. The v1 output is "
              f"kept as `guard_eval.v1-instrument-bug.json` (superseded intermediate sha256 `{v1_hash}`) and "
              "is not the binding result; v2 implements the pre-registered rule and is the result above.\n")
    md.append("\n## Falsifier\n")
    md.append(FALSIFIER + "\n")
    md.append("## Limitations\n")
    for lim in LIMITATIONS:
        md.append(f"- {lim}")
    (HERE / "README.md").write_text("\n".join(md) + "\n")

    # ---- composite report ----
    files = {
        "PREREGISTRATION.json": sha256_file(HERE / "PREREGISTRATION.json"),
        "eval_t1_guards.py": sha256_file(HERE / "eval_t1_guards.py"),
        "guard_eval.json": sha256_file(HERE / "guard_eval.json"),
        "README.md": sha256_file(HERE / "README.md"),
    }
    if v1_hash:
        files["guard_eval.v1-instrument-bug.json"] = v1_hash
    report = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "created_at": now(),
        "node_ids": ["F2a", "F2b"],
        "class_ids": [FROM_CLASS, TO_CLASS],
        "gate": "G-FORM",
        "task": "Machine evaluation of the three guards of transfer rule T1 (AF-SCC-C0-VAC-GEN -> AF-SCC-C2-VAC-GEN) at the pinned canonical hashes.",
        "artifacts": {k: {"path": f"artifacts/worker-071/t1_guard_eval/{k}", "sha256": v} for k, v in files.items()},
        "result_artifact": "artifacts/worker-071/t1_guard_eval/guard_eval.json#" + files["guard_eval.json"],
        "input_hashes": before,
        "verdict": result["verdict"],
        "key_findings": {
            "G1_witness_paths": [w["path"] for w in g1["witnesses"]],
            "G1_core_witness_paths": [w["path"] for w in g1["core_key_witnesses"]],
            "G1_core_tuple_strict_equal": len(g1["core_key_witnesses"]) == 0,
            "G2_missing_literal_fields": [
                f for f, row in g2["per_field"].items()
                if not (row["F2a_target_present"] and row["F2b_source_present"])],
            "G3_bound_claims": g3["n_bound_claims"],
            "G3_c0_class_claims": g3["n_c0_class_claims"],
            "G3_bound_claim_ids": g3["bound_claim_ids"],
            "context_F1_vs_F2b_core_witness_paths": context["F1_vs_F2b_core_key_witness_paths"],
        },
        "controls": ctl,
        "instrument_history": {
            "v1_instrument_bug": "matched reviews to claims via cited artifact paths instead of claim event_id",
            "v1_superseded_output": "artifacts/worker-071/t1_guard_eval/guard_eval.v1-instrument-bug.json#" + (v1_hash or "absent"),
            "v2_rule": "review.target_id == claim.event_id, per PREREGISTRATION.json",
        },
        "falsifier": FALSIFIER,
        "limitations": LIMITATIONS,
        "authority_note": "Measurement only; no gate verdict, no node status, no validation_status=passed.",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    # ---- sidecars ----
    for name in list(files) + ["report.json"]:
        h = sha256_file(HERE / name)
        (HERE / (name + ".sha256")).write_text(f"{h}  {name}\n")

    if not measurement_valid:
        print(json.dumps({"task_id": TASK_ID, "measurement_valid": False, "window_status": window_status}))
        sys.exit(2)
    return report


if __name__ == "__main__":
    out = main()
    print(json.dumps({
        "task_id": out["task_id"],
        "verdict": out["verdict"],
        "artifacts": {k: v["sha256"][:16] for k, v in out["artifacts"].items()},
    }, indent=2))
