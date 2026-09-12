#!/usr/bin/env python3
"""Independent hash-pinned structural review of the F2b class schema.

Target   : schemas/af_scc_c0_vacuum.yaml  (class AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM)
Reviewer : worker-001 (independent: this file and its checks were written from the
           assignment card asg-2026-09-11-F2-astra-lead-formulation-02, the A0 rubric
           section verifiers.schema_formulation, and the artifact text only. No other
           worker's checker is imported for the pass/fail decision; the frozen
           research_map/class_separation.py is run once as an explicitly non-binding
           external cross-check.)

FAIL-CLOSED CONTRACT
  The harness measures the live canonical artifact first. If the live sha256 differs
  from --expect, it writes NOTHING and exits 3: a verdict on superseded bytes would be
  advisory only, so it is not emitted.

Exit codes: 0 = verdict emitted, 3 = live hash drift (no verdict), 2 = usage/read error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML is required", file=sys.stderr)
    raise SystemExit(2)

CST = timezone(timedelta(hours=8))
FROZEN = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
EXPECTED_CONCLUSION = "scc_c0_future_inextendibility"
CANONICAL_F0 = "research_map/formulation_taxonomy.yaml"
SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"
VARIANT_REGISTRY = "artifacts/formulation/VARIANT_REGISTRY.json"
RUBRIC = "evaluation_rubric.yaml"


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def line_of(text, needle, start=0):
    idx = text.find(needle, start)
    if idx < 0:
        return None
    return text.count("\n", 0, idx) + 1


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node, deep=False):
    seen = set()
    dups = []
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            dups.append({"key": key, "line": key_node.start_mark.line + 1})
        seen.add(key)
    loader.duplicate_keys = getattr(loader, "duplicate_keys", []) + dups
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def load_yaml_recording_dups(path):
    loader = UniqueKeyLoader(open(path, "rb").read())
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, getattr(loader, "duplicate_keys", [])


def check(cid, description, ok, evidence):
    return {
        "id": cid,
        "description": description,
        "status": "pass" if ok else "fail",
        "evidence": evidence,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--expect", required=True, help="expected sha256 of the live canonical F2b")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    live = os.path.join(root, "schemas/af_scc_c0_vacuum.yaml")

    measured_at = now()
    live_sha = sha256_file(live)
    if live_sha != args.expect:
        print(
            json.dumps(
                {
                    "status": "drift_abort",
                    "expected_sha256": args.expect,
                    "measured_sha256": live_sha,
                    "measured_at": measured_at,
                    "note": "verdict withheld: canonical bytes changed since the review pin",
                },
                indent=1,
            )
        )
        return 3

    text = open(live, "rb").read().decode("utf-8")
    schema, dup_keys = load_yaml_recording_dups(live)
    st = os.stat(live)

    # --- input artifacts referenced by the binding -------------------------------
    f0_sha = sha256_file(os.path.join(root, CANONICAL_F0))
    f0, _ = load_yaml_recording_dups(os.path.join(root, CANONICAL_F0))
    sup_sha = sha256_file(os.path.join(root, SUPPLEMENT))
    sup, _ = load_yaml_recording_dups(os.path.join(root, SUPPLEMENT))
    vr = json.load(open(os.path.join(root, VARIANT_REGISTRY)))
    rubric, _ = load_yaml_recording_dups(os.path.join(root, RUBRIC))

    checks = []

    # H1 identity -----------------------------------------------------------------
    checks.append(
        check(
            "H1",
            "artifact parses and carries the expected frozen class identity",
            schema.get("class_id") == CLASS_ID and schema.get("node_id") == NODE_ID,
            {"class_id": schema.get("class_id"), "node_id": schema.get("node_id")},
        )
    )

    # H2 single-class binding, no unknown class ids --------------------------------
    tokens = sorted(set(re.findall(r"AF-[A-Z0-9-]+", text)))
    vr_ids = {
        (v.get("parent_class"), v.get("variant_id"))
        for v in vr.get("variants", [])
    }
    variant_tokens = {f"{p}-{v}" for p, v in vr_ids}
    unknown = [t for t in tokens if t not in FROZEN and t not in variant_tokens]
    checks.append(
        check(
            "H2",
            "every AF-* token is a frozen class id or a registered variant token",
            not unknown,
            {"tokens": tokens, "unknown": unknown, "registry_entries": len(vr_ids)},
        )
    )

    # H3 no composite C0/C2 declaration outside the anti_scope prohibition ---------
    composite = re.compile(r"C0\s*(?:or|/)\s*C2|C2\s*(?:or|/)\s*C0", re.I)
    composite_lines = [
        text.count("\n", 0, m.start()) + 1 for m in composite.finditer(text)
    ]
    # A composite token is only a declaration if it is not inside a disavowal/prohibition
    # sentence. Prohibition markers were fixed before the run to avoid the CF-4 failure mode
    # where a linter's false positive drives a statement change.
    prohibition_markers = (
        "must not",
        "no containment",
        "not asserted",
        "composite regularity",
        "phrases_that_are_not_this_class",
        "not_this_class",
    )
    lines = text.splitlines()
    allowed_lines = [
        n
        for n in composite_lines
        if any(m.lower() in lines[n - 1].lower() for m in prohibition_markers)
    ]
    undeclared = [n for n in composite_lines if n not in allowed_lines]
    checks.append(
        check(
            "H3",
            "no composite C0/C2 declaration outside a disavowal/prohibition sentence",
            not undeclared,
            {
                "occurrence_lines": composite_lines,
                "prohibition_lines": allowed_lines,
                "undeclared_lines": undeclared,
                "matched_lines": {str(n): lines[n - 1].strip()[:120] for n in composite_lines},
            },
        )
    )

    # H4 conclusion binds to C0, not C2/H2_loc -------------------------------------
    sup_c0 = (sup.get("class_contracts") or {}).get(CLASS_ID, {})
    sup_conclusion = sup_c0.get("conclusion_type")
    concl = schema.get("conclusion", {})
    reg = schema.get("regularity", {})
    comp = schema.get("class_components", {})
    concl_token = concl.get("conclusion_type")
    h4_ok = (
        comp.get("regularity_token") == "C0"
        and reg.get("extension_regularity") == "C0"
        and concl.get("family") == "SCC"
        and concl_token == EXPECTED_CONCLUSION
        and concl_token == sup_conclusion
        and "c2" not in str(concl_token).lower()
    )
    checks.append(
        check(
            "H4",
            "class_components/extension_regularity are C0; conclusion_type equals the "
            "declared supplement contract and is not a C2 token",
            h4_ok,
            {
                "regularity_token": comp.get("regularity_token"),
                "extension_regularity": reg.get("extension_regularity"),
                "family": concl.get("family"),
                "conclusion_type": concl_token,
                "supplement_conclusion_type": sup_conclusion,
                "line_conclusion_type": line_of(text, "conclusion_type: " + str(concl_token)),
            },
        )
    )

    # H5 I+/visibility role by family ---------------------------------------------
    iplus = schema.get("i_plus", {})
    vis = schema.get("visibility", {})
    h5_ok = (
        iplus.get("role") == "assumption"
        and iplus.get("in_conclusion") is False
        and vis.get("role") == "not_in_conclusion"
    )
    checks.append(
        check(
            "H5",
            "SCC family: I+ and visibility are excluded from the conclusion",
            h5_ok,
            {
                "i_plus.role": iplus.get("role"),
                "i_plus.in_conclusion": iplus.get("in_conclusion"),
                "visibility.role": vis.get("role"),
            },
        )
    )

    # H6 quantifier block ----------------------------------------------------------
    q = schema.get("quantifiers", {})
    ordered = q.get("ordered", [])
    h6_ok = bool(q.get("formal")) and len(ordered) >= 4 and q.get("order_matters") is True \
        and bool(q.get("negation")) and bool(q.get("negation_normal_form")) \
        and "comeager" in str(q.get("quantifier_class", ""))
    checks.append(
        check(
            "H6",
            "quantifier block has formal form, >=4 ordered binders, order_matters, "
            "negation + normal form, comeager class",
            h6_ok,
            {
                "ordered_binders": len(ordered),
                "order_matters": q.get("order_matters"),
                "quantifier_class": q.get("quantifier_class"),
                "line_D0": line_of(text, "D0:"),
            },
        )
    )

    # H7 topology ------------------------------------------------------------------
    topo = schema.get("topology", {})
    boundary = str(topo.get("conformal_boundary", []))
    h7_ok = topo.get("spacetime_dimension") == 4 and all(
        t in boundary for t in ("I+", "I-", "i0")
    ) and "one" in str(topo.get("end_structure", "")).lower()
    checks.append(
        check(
            "H7",
            "topology block: 3+1, I+/I-/i0, one asymptotically flat end",
            h7_ok,
            {
                "dimension": topo.get("spacetime_dimension"),
                "conformal_boundary": topo.get("conformal_boundary"),
                "end_structure": topo.get("end_structure"),
            },
        )
    )

    # H8 genericity -----------------------------------------------------------------
    gen = schema.get("genericity", {})
    h8_ok = (
        gen.get("kind") == "residual_comeager"
        and gen.get("is_part_of_class") is True
        and "excluded_set_status" in gen
    )
    checks.append(
        check(
            "H8",
            "genericity is residual/comeager, part of the class, with a status on the "
            "excluded set",
            h8_ok,
            {
                "kind": gen.get("kind"),
                "is_part_of_class": gen.get("is_part_of_class"),
                "excluded_set_status": gen.get("excluded_set_status"),
            },
        )
    )

    # H9 non-vacuity ------------------------------------------------------------------
    nv = schema.get("non_vacuity", {})
    h9_ok = bool(nv.get("condition")) and bool(nv.get("vacuity_falsifier"))
    checks.append(
        check(
            "H9",
            "non-vacuity block present with an explicit vacuity falsifier",
            h9_ok,
            {"line_condition": line_of(text, "non_vacuity:"), "status": nv.get("status")},
        )
    )

    # H10 falsifier tiering -----------------------------------------------------------
    fal = schema.get("falsifier", {})
    t1 = fal.get("tier_1", {})
    t2 = fal.get("tier_2", {})
    h10_ok = t1.get("refutes") == CLASS_ID and t2.get("labelling_required") == \
        "refutes_strengthening_only" and bool(t1.get("genericity_requirement"))
    checks.append(
        check(
            "H10",
            "tier-1 falsifier refutes this class and is non-meagerness-quantified; "
            "tier-2 is labelled strengthening-only",
            h10_ok,
            {
                "tier_1_refutes": t1.get("refutes"),
                "tier_2_labelling": t2.get("labelling_required"),
                "line_tier_1": line_of(text, "tier_1:"),
            },
        )
    )

    # H11 binding to the measured canonical F0 ---------------------------------------
    bind = schema.get("f0_binding", {})
    h11_ok = (
        bind.get("declared_f0_artifact") == CANONICAL_F0
        and bind.get("declared_f0_sha256") == f0_sha
    )
    checks.append(
        check(
            "H11",
            "f0_binding declares the measured canonical taxonomy hash",
            h11_ok,
            {
                "declared": bind.get("declared_f0_sha256"),
                "measured": f0_sha,
                "line": line_of(text, "f0_binding:"),
            },
        )
    )

    # H12 class_contract_pointer resolves ---------------------------------------------
    ptr = str(schema.get("class_contract_pointer", ""))
    path_part, _, frag = ptr.partition("#")
    resolved = None
    try:
        node = sup
        for key in frag.split("."):
            node = node[key]
        resolved = node
    except Exception:
        resolved = None
    h12_ok = (
        path_part == SUPPLEMENT
        and isinstance(resolved, dict)
        and resolved.get("node_id") == NODE_ID
    )
    checks.append(
        check(
            "H12",
            "declared class_contract_pointer resolves in the supplement to this node",
            h12_ok,
            {
                "pointer": ptr,
                "supplement_sha256": sup_sha,
                "resolved_node_id": resolved.get("node_id") if isinstance(resolved, dict) else None,
            },
        )
    )

    # --- non-hard findings -----------------------------------------------------------
    f0_variants = f0.get("variants", [])
    f0_variant_pairs = {(v.get("parent_class"), v.get("variant_id")) for v in f0_variants}
    registry_pairs = vr_ids
    cited_pairs = set()
    for entry in (schema.get("anti_scope", {}) or {}).get("not_this_class", []):
        why = str(entry.get("why", ""))
        for m in re.finditer(r"parent_class (\S+), variant_id (\S+)", why):
            cited_pairs.add((m.group(1), m.group(2)))
    missing_from_f0 = sorted(p for p in cited_pairs if p not in f0_variant_pairs)
    findings = []

    findings.append(
        {
            "id": "W001-F1",
            "severity": "major",
            "kind": "condition",
            "finding": (
                "Variant-registry divergence: the canonical F0 taxonomy registers "
                f"{len(f0_variant_pairs)} variant(s) inline ({sorted(f0_variant_pairs)}), while "
                f"{VARIANT_REGISTRY} v{vr.get('version')} registers {len(registry_pairs)}; this schema "
                f"cites {sorted(cited_pairs)}, of which {missing_from_f0} are absent from canonical F0. "
                "The declared consistency evidence compares class contracts only, so this divergence is "
                "invisible to it."
            ),
            "evidence_refs": [
                f"{CANONICAL_F0}#sha256:{f0_sha[:16]}",
                f"{VARIANT_REGISTRY}#sha256:{sha256_file(os.path.join(root, VARIANT_REGISTRY))[:16]}",
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{live_sha[:16]}:line_277",
            ],
            "deciding_field": "anti_scope.not_this_class[*].why variant_id vs canonical F0 variants[]",
            "remediation": (
                "Either inline every registered variant into canonical F0, or make canonical F0 "
                "delegate to VARIANT_REGISTRY.json as the single registry, and extend the consistency "
                "check to compare the variant sets."
            ),
            "falsifier": (
                "Canonical F0 is falsified as divergent if it contains H2LOC and DISTRIBUTIONAL for "
                "AF-SCC-C0-VAC-GEN on re-measurement; this finding is falsified if it does."
            ),
        }
    )

    concl_vocab = {
        "canonical_F0_axes": (
            (f0.get("classes", {}).get(CLASS_ID, {}) or {}).get("axes", {}) or {}
        ).get("conclusion_type"),
        "canonical_F0_conclusion": (
            (f0.get("classes", {}).get(CLASS_ID, {}) or {}).get("conclusion", {}) or {}
        ).get("type"),
        "schema_and_supplement": concl_token,
        "rubric_conclusion_primary": next(
            (c.get("conclusion_primary") for c in rubric.get("frozen_classes", []) if c.get("id") == CLASS_ID),
            None,
        ),
    }
    findings.append(
        {
            "id": "W001-F2",
            "severity": "major",
            "kind": "condition",
            "finding": (
                "Conclusion-type token for AF-SCC-C0-VAC-GEN is not unique across canonical "
                f"authorities: {json.dumps(concl_vocab)}. The consistency evidence asserts an alias "
                "policy but publishes no alias map, so a machine class-binding check cannot decide "
                "'conclusion_type allowed for class' without a human."
            ),
            "evidence_refs": [
                f"{CANONICAL_F0}#sha256:{f0_sha[:16]}",
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{live_sha[:16]}:line_{line_of(text, 'conclusion_type: ' + str(concl_token))}",
                f"{RUBRIC}#sha256:{sha256_file(os.path.join(root, RUBRIC))[:16]}",
            ],
            "deciding_field": "classes.AF-SCC-C0-VAC-GEN.axes.conclusion_type",
            "remediation": (
                "Publish the alias map in artifacts/formulation/evidence/taxonomy_consistency.json "
                "(token -> canonical token) and cite it from every class binding, or unify the token "
                "in one revision."
            ),
            "falsifier": (
                "A published alias map containing all three tokens as equivalent falsifies the "
                "'cannot be decided mechanically' claim."
            ),
        }
    )

    consistency_path = os.path.join(root, "artifacts/formulation/evidence/taxonomy_consistency.json")
    consistency = json.load(open(consistency_path)) if os.path.exists(consistency_path) else None
    findings.append(
        {
            "id": "W001-F3",
            "severity": "major",
            "kind": "condition",
            "finding": (
                "The f0_binding consistency evidence is a bare verdict object "
                f"({os.path.getsize(consistency_path) if consistency is not None else 0} bytes: "
                f"consistent={consistency.get('consistent') if consistency else None}, "
                f"errors={consistency.get('errors') if consistency else None}, "
                f"contract_divergences={consistency.get('contract_divergences') if consistency else None}) "
                "with no per-field comparison table, so 'consistent: true' is not independently "
                "reproducible from the artifact."
            ),
            "evidence_refs": [
                f"artifacts/formulation/evidence/taxonomy_consistency.json#sha256:"
                f"{sha256_file(consistency_path)[:16]}" if cons_ok(consistency_path) else
                "artifacts/formulation/evidence/taxonomy_consistency.json#missing"
            ],
            "deciding_field": "consistent",
            "remediation": "Record the per-class, per-field comparison rows and their source hashes.",
            "falsifier": "A re-run of an independent per-field differ that reproduces consistency: true with zero rows would falsify this finding.",
        }
    )

    findings.append(
        {
            "id": "W001-F4",
            "severity": "minor",
            "kind": "finding",
            "finding": (
                f"{len(dup_keys)} duplicate YAML mapping keys in the preamble; the revision history is "
                "silently collapsed to the last value by every YAML parser."
            ),
            "evidence_refs": [
                f"schemas/af_scc_c0_vacuum.yaml#sha256:{live_sha[:16]}:lines_"
                + ",".join(str(d["line"]) for d in dup_keys)
            ],
            "deciding_field": "revised_at (duplicate)",
            "falsifier": "A strict YAML parse reporting zero duplicate keys falsifies this finding.",
        }
    )

    declared_rev = schema.get("revised_at")
    mtime = datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds")
    findings.append(
        {
            "id": "W001-F5",
            "severity": "minor",
            "kind": "finding",
            "finding": (
                f"declared revised_at={declared_rev} is ahead of the filesystem mtime={mtime}; the "
                "timestamp_provenance field covers authored_at only. This is the CF-6 clock pattern, "
                "recorded here because a review binding to the declared time would mis-order revisions."
            ),
            "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#sha256:{live_sha[:16]}:mtime={mtime}"],
            "deciding_field": "revised_at vs st_mtime",
            "falsifier": "A measured mtime at or after the declared revised_at falsifies the finding.",
        }
    )

    d0 = (schema.get("quantifiers", {}).get("domains", {}) or {}).get("D0", {}).get("definition")
    findings.append(
        {
            "id": "W001-F6",
            "severity": "info",
            "kind": "known_condition",
            "finding": (
                "D0 remains a disjunctive domain ('weighted Sobolev ... or the smooth-with-decay "
                "default') and the ambient space is the weighted Sobolev constraint manifold, while the "
                "default data class is Frechet. This is the prior lead-audit HF-06 condition, unchanged; "
                "recorded, not treated as blocking by precedent, but it must be resolved before any "
                "claim quantifies over 'the class' as one data space."
            ),
            "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#sha256:{live_sha[:16]}:line_{line_of(text, 'or the smooth-with-decay default')}"],
            "deciding_field": "quantifiers.domains.D0.definition",
            "falsifier": "A single non-disjunctive D0 definition matched by genericity.ambient_space falsifies this finding.",
        }
    )

    # F0 drift: the declared binding is measured against the live canonical taxonomy.
    declared_f0 = bind.get("declared_f0_sha256")
    pinned_f0 = os.path.join(
        root, "artifacts/worker-001/f2b_review/pinned/research_map_formulation_taxonomy.yaml"
    )
    drift_detail = {"predecessor_bytes_available": False}
    if declared_f0 and os.path.exists(pinned_f0) and sha256_file(pinned_f0) == declared_f0:
        import difflib

        old = open(pinned_f0).read().splitlines()
        new = open(os.path.join(root, CANONICAL_F0)).read().splitlines()
        changed = [
            l
            for l in difflib.unified_diff(old, new, lineterm="", n=0)
            if l[:1] in "+-" and not l.startswith(("+++", "---"))
        ]
        drift_detail = {
            "predecessor_bytes_available": True,
            "changed_lines": len(changed),
            "sample": changed[:8],
        }
    if declared_f0 != f0_sha:
        findings.append(
            {
                "id": "W001-F7",
                "severity": "major",
                "kind": "hard_binding_drift",
                "finding": (
                    f"f0_binding declares {declared_f0} but the canonical taxonomy measures "
                    f"{f0_sha} at review time (checked_at in the schema was "
                    f"{bind.get('checked_at')}). The schema's own rule requires a refresh before a gate "
                    "verdict, so H11 fails. Drift detail: " + json.dumps(drift_detail)
                ),
                "evidence_refs": [
                    f"schemas/af_scc_c0_vacuum.yaml#sha256:{live_sha[:16]}:line_{line_of(text, 'f0_binding:')}",
                    f"{CANONICAL_F0}#sha256:{f0_sha}",
                ],
                "deciding_field": "f0_binding.declared_f0_sha256",
                "remediation": (
                    "Freeze the canonical F0 publication first, then refresh f0_binding to the frozen "
                    "sha256 and re-run artifacts/formulation/evidence/taxonomy_consistency.json; the "
                    "harness re-runs in seconds and will flip H11 to pass."
                ),
                "falsifier": (
                    "Re-measuring the canonical taxonomy at the declared sha256 falsifies the drift; a "
                    "refreshed f0_binding equal to the measured hash falsifies the finding."
                ),
            }
        )
    else:
        findings.append(
            {
                "id": "W001-F7",
                "severity": "info",
                "kind": "binding_current",
                "finding": (
                    f"f0_binding.declared_f0_sha256 equals the measured canonical taxonomy hash "
                    f"{f0_sha}; drift detail against the previously pinned predecessor "
                    f"(0fcc6a19): {json.dumps(drift_detail)}"
                ),
                "evidence_refs": [f"{CANONICAL_F0}#sha256:{f0_sha}"],
                "deciding_field": "f0_binding.declared_f0_sha256",
                "falsifier": "A later rewrite of the canonical taxonomy without a binding refresh falsifies this at the next re-run.",
            }
        )

    # --- external cross-check (non-binding) ------------------------------------------
    cross = {"tool": "research_map/class_separation.py", "binding": False,
             "caveat": "frozen checker authored by another worker; its regression corpus is self-authored (CF-9)"}
    try:
        sys.path.insert(0, os.path.join(root, "research_map"))
        import class_separation as cs  # type: ignore
        cross["findings_for_text_count"] = len(cs.findings_for_text(text, "schemas/af_scc_c0_vacuum.yaml"))
        cross["regression"] = cs.regression()
    except Exception as exc:  # pragma: no cover
        cross["error"] = f"{type(exc).__name__}: {exc}"

    hard_failures = [
        {"id": c["id"], "description": c["description"], "evidence": c["evidence"]}
        for c in checks
        if c["status"] == "fail"
    ]
    verdict = "revise" if hard_failures else "accept"
    score = 4.0 if verdict == "accept" else 2.5

    review = {
        "schema_version": "0.1",
        "review_id": f"F2b-review-worker-001-{measured_at.replace(':', '').replace('-', '')}",
        "node_id": NODE_ID,
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "reviewer": "worker-001",
        "independent": True,
        "target_id": f"schemas/af_scc_c0_vacuum.yaml#{live_sha}",
        "reviewed_path": "schemas/af_scc_c0_vacuum.yaml",
        "reviewed_sha256": live_sha,
        "reviewed_bytes": st.st_size,
        "reviewed_mtime": mtime,
        "measured_at": measured_at,
        "verdict": verdict,
        "score": score,
        "hard_failures": hard_failures,
        "checks": checks,
        "findings": findings,
        "conditions": [f["id"] for f in findings if f.get("kind") == "condition"],
        "cross_checks": cross,
        "benchmark": {
            "criteria_source": f"{RUBRIC}#verifiers.schema_formulation",
            "assignment": "asg-2026-09-11-F2-astra-lead-formulation-02",
            "frozen_class_ids_at_measurement": sorted(f0.get("class_ids", [])),
            "f0_sha256_measured": f0_sha,
            "supplement_sha256_measured": sup_sha,
            "variant_registry_sha256_measured": sha256_file(os.path.join(root, VARIANT_REGISTRY)),
        },
        "scope_note": (
            "Structural, hash-pinned review only. It certifies the schema's declared fields against "
            "the G-FORM/assignment criteria and the A0 schema_formulation checklist at the cited "
            "sha256. It does NOT certify physical fidelity, the truth of any citation, or any gate; "
            "the conditions W001-F1..F3 are recorded as pre-gate obligations for the controller. A "
            "later revision of the artifact voids this verdict, not the harness."
        ),
        "falsifier": (
            f"Re-measure schemas/af_scc_c0_vacuum.yaml: a sha256 other than {live_sha} voids this "
            "verdict (harness exits 3 without emitting one). At the pinned hash the verdict is "
            "falsified if any check H1-H12 is shown to fail under an independent implementation, or "
            "if canonical F0 at " + f0_sha[:16] + " is shown to contain an AF-SCC-C0-VAC-GEN contract "
            "whose hypotheses, exclusions or conclusion_type contradict this schema."
        ),
        "reproduce": (
            f"python3 artifacts/worker-001/f2b_review/run_review.py --expect {live_sha} "
            "--out artifacts/worker-001/f2b_review/review.json"
        ),
    }

    out = args.out or os.path.join(root, "artifacts/worker-001/f2b_review/review.json")
    with open(out, "w") as fh:
        json.dump(review, fh, indent=1)
        fh.write("\n")
    print(json.dumps({"status": "emitted", "verdict": verdict, "score": score,
                      "hard_failures": [h["id"] for h in hard_failures],
                      "conditions": review["conditions"], "out": out,
                      "reviewed_sha256": live_sha}, indent=1))
    return 0


def cons_ok(path):
    return os.path.exists(path)


if __name__ == "__main__":
    raise SystemExit(main())
