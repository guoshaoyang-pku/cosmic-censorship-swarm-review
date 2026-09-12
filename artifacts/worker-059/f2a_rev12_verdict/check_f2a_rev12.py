#!/usr/bin/env python3
"""W059-F2A-REV12-VERDICT-01 independent instrument (worker-059).

Class: AF-SCC-C2-VAC-GEN (node F2a).
Purpose: independent full-schema verification of the freshly republished F2a
revision 12 at the pinned hash, plus a closure-delta against the hard-finding
set raised at b6123750, plus controlled mutants proving each detector fires and
does not fire on the unmodified pinned file.

Independence: this file imports ONLY the standard library and PyYAML. It does
not import, exec or copy any canonical gate (check_class_schema.py,
run_contract_tests.py, check_taxonomy_consistency.py, classsep_regression.py).
Token/pointer/vocabulary checks are re-implemented from first principles on the
pinned bytes.
"""
import hashlib
import json
import os
import subprocess
import sys
import time

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot", "f2a.5476a3f2c6bc.yaml")
PINNED = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"

INPUTS = {
    "f2a_live": "schemas/af_scc_c2_vacuum.yaml",
    "f0_canonical": "research_map/formulation_taxonomy.yaml",
    "supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "vocab_aliases": "artifacts/formulation/VOCAB_ALIASES.json",
    "frozen_manifest": "artifacts/formulation/FROZEN.json",
    "consistency_evidence": "artifacts/formulation/evidence/taxonomy_consistency.json",
}

RESULT = {"task": "W059-F2A-REV12-VERDICT-01", "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read_bytes(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return fh.read()


class DupLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys at every nesting level."""


def _dup_constructor(loader, node):
    dups = loader._dup_keys  # set by caller
    seen = set()
    pairs = []
    for k_node, v_node in node.value:
        k = loader.construct_object(k_node, deep=True)
        if k in seen:
            dups.append(str(k))
        seen.add(k)
        pairs.append((k, loader.construct_object(v_node, deep=True)))
    return dict(pairs)


DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_constructor)


def strict_load(text):
    """Return (doc, duplicate_key_list). Duplicates are reported, not hidden."""
    loader = DupLoader(text)
    loader._dup_keys = []
    try:
        doc = loader.get_single_data()
    finally:
        loader.dispose()
    return doc, sorted(loader._dup_keys)


def fragment_resolves(doc, fragment):
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False
    return True


def check_a_parse(text, expect_class, expect_node):
    doc, dups = strict_load(text)
    c = {}
    c["A1_strict_duplicate_key_free"] = len(dups) == 0
    c["A1_duplicate_keys"] = dups
    c["A2_is_mapping"] = isinstance(doc, dict)
    c["A3_class_id_exact"] = bool(doc) and doc.get("class_id") == expect_class
    c["A4_node_id_exact"] = bool(doc) and doc.get("node_id") == expect_node
    return doc, c


def check_b_provenance(doc, mtime, now):
    c = {}
    rev = doc.get("revised_at")
    ts = None
    if isinstance(rev, str):
        try:
            ts = time.mktime(time.strptime(rev[:19], "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            ts = None
    c["B1_revised_at_parses"] = ts is not None
    c["B1_revised_at"] = rev
    c["B1_skew_vs_mtime_s"] = round(ts - mtime, 1) if ts is not None else None
    c["B1_not_future_vs_now_s"] = round(now - ts, 1) if ts is not None else None
    c["B1_timestamp_consistent"] = (
        ts is not None and abs(ts - mtime) <= 600 and ts <= now + 120
    )
    hist = doc.get("revision_history")
    ok_hist = isinstance(hist, list) and len(hist) > 0
    idxs, ats, unused = [], [], []
    if ok_hist:
        for row in hist:
            if not isinstance(row, dict):
                ok_hist = False
                break
            idxs.append(row.get("index"))
            ats.append(row.get("at"))
            if row.get("unused"):
                unused.append(row.get("index"))
    c["B2_revision_history_present"] = ok_hist
    c["B2_indices_unique"] = ok_hist and len(set(idxs)) == len(idxs)
    c["B2_history_len"] = len(idxs) if ok_hist else 0
    c["B2_unused_entries"] = unused
    c["B3_live_revision_field"] = doc.get("revision")
    return c


def check_c_binding(doc, f0, supplement, measured_f0_sha, measured_supp_sha, measured_evidence_sha):
    c = {}
    ptr = doc.get("class_contract_pointer") or ""
    spr = doc.get("class_contract_supplement_pointer") or ""
    c["C1_pointer"] = ptr
    c["C1_pointer_resolves_canonical_f0"] = (
        "#" in ptr and ptr.split("#", 1)[0] == "research_map/formulation_taxonomy.yaml"
        and fragment_resolves(f0, ptr.split("#", 1)[1])
    )
    c["C2_supplement_pointer"] = spr
    c["C2_supplement_pointer_resolves"] = (
        bool(spr) and "#" in spr and fragment_resolves(supplement, spr.split("#", 1)[1])
    )
    fb = doc.get("f0_binding") or {}
    declared = fb.get("declared_f0_sha256")
    c["C3_declared_f0_sha256"] = declared
    c["C3_declared_f0_matches_measured"] = declared == measured_f0_sha
    ce = fb.get("consistency_evidence_sha256")
    c["C4_consistency_evidence_sha256"] = ce
    c["C4_evidence_matches_measured"] = ce == measured_evidence_sha
    return c


def check_d_vocabulary(doc, f0, vocab):
    """Class-binding on the conclusion surface.

    D1/D2 test F2a against the canonical F0 field vocabulary; D3 tests the
    registered alias equivalence; D4 tests F2a against the frozen alias policy
    ('canonical token first, aliases must never appear in a new canonical
    artifact'). The F2a-side and F0-side results are reported separately because
    the two frozen registries can contradict each other.
    """
    c = {}
    concl = doc.get("conclusion") or {}
    tok = concl.get("conclusion_type")
    c["D1_f2a_conclusion_type"] = tok
    f0_axes = (((f0.get("classes") or {}).get("AF-SCC-C2-VAC-GEN") or {}).get("axes") or {})
    f0_tok = f0_axes.get("conclusion_type")
    c["D1_f0_axis_conclusion_type"] = f0_tok
    c["D1_exact_match_f2a_vs_f0"] = tok == f0_tok
    allowed = ((f0.get("field_vocabulary") or {}).get("conclusion_type") or {}).get("allowed") or []
    c["D2_f0_allowed"] = allowed
    c["D2_token_in_f0_allowed"] = tok in allowed
    canon = None
    alias_of = None
    for key, aliases in (vocab.get("conclusion_type") or {}).items():
        if tok == key:
            canon, alias_of = key, aliases
        elif tok in (aliases or []):
            canon, alias_of = key, aliases
    c["D3_vocab_canonical_key_for_token"] = canon
    c["D3_token_is_vocab_canonical_key"] = canon == tok
    c["D3_token_is_registered_alias"] = bool(canon) and canon != tok
    c["D3_registered_alias_class"] = alias_of
    # policy side: which of the two artifacts uses the non-canonical token?
    c["D4_f0_axis_token_is_vocab_canonical"] = f0_tok in (vocab.get("conclusion_type") or {})
    c["D4_policy"] = vocab.get("policy")
    c["D5_f2a_token_policy_conformant"] = c["D3_token_is_vocab_canonical_key"] is True
    c["D4_contradiction_present"] = (
        c["D2_token_in_f0_allowed"] is False
        and c["D3_token_is_registered_alias"] is False
        and c["D4_f0_axis_token_is_vocab_canonical"] is False
    )
    return c


def check_e_welltyped(doc):
    c = {}
    formal = str((doc.get("quantifiers") or {}).get("formal") or "")
    domains = (doc.get("quantifiers") or {}).get("domains") or {}
    ordered = (doc.get("quantifiers") or {}).get("ordered") or []
    d0 = str((domains.get("D0") or {}).get("definition") or "")
    c["E1_formal_binder_r"] = "forall r in D0" in formal
    c["E1_d0_tagged_union"] = ("tagged disjoint union" in d0) and ("r = smooth" in d0)
    c["E1_d0_smooth_branch"] = "smooth" in d0 and "sobolev" in d0.lower()
    c["E2_no_stale_pair_binder_in_formal"] = "(s,delta) in D0" not in formal
    unresolved = [b.get("domain_id") for b in ordered if b.get("domain_id") not in domains]
    c["E3_ordered_binders"] = [(b.get("kind"), b.get("binder"), b.get("domain_id")) for b in ordered]
    c["E3_all_binder_domains_resolve"] = len(ordered) > 0 and not unresolved
    gen = doc.get("genericity") or {}
    amb = str(gen.get("ambient_space") or "")
    top = str(gen.get("topology_or_measure") or "")
    c["E4_ambient_space_covers_smooth"] = ("Frechet" in amb or "Fréchet" in amb) or (
        "Frechet" in top or "Fréchet" in top
    )
    c["E4_baire_argument_banach_only"] = ("Banach" in amb) and not (
        "Frechet" in amb or "Fréchet" in amb
    )
    c["E4_smooth_topology_declared_in_topology_field"] = (
        "Frechet" in top or "Fréchet" in top
    )
    return c


def check_f_class_integrity(doc):
    c = {}
    reg = doc.get("regularity") or {}
    ext = reg.get("extension_regularity")
    c["F1_extension_regularity"] = ext
    c["F1_exactly_C2"] = ext == "C2"
    concl = doc.get("conclusion") or {}
    tout = " ".join(
        str(concl.get(k) or "") for k in ("statement_natural_language", "statement_formal")
    )
    c["F2_no_wcc_token_in_conclusion"] = "WCC" not in tout and "AF-WCC" not in tout
    c["F2_visibility_not_in_conclusion"] = (doc.get("visibility") or {}).get("role") == "not_in_conclusion"
    c["F2_i_plus_not_in_conclusion"] = (doc.get("i_plus") or {}).get("in_conclusion") is False
    c["F2_extension_regularity_not_in_conclusion_text"] = "C0" not in tout and "C^{1,1}" not in tout
    # anti-scope guard present
    c["F3_anti_scope_present"] = bool(doc.get("anti_scope"))
    sib = doc.get("sibling_disjoint_from")
    c["F3_sibling_disjoint_from"] = sib
    return c


def check_g_publication(pinned_sha, frozen):
    c = {}
    files = (frozen or {}).get("files") or {}
    e = files.get("schemas/af_scc_c2_vacuum.yaml") or {}
    c["G1_frozen_revision"] = (frozen or {}).get("revision")
    c["G1_frozen_pins_f2a"] = e.get("sha256")
    c["G1_frozen_pins_pinned_rev12"] = e.get("sha256") == pinned_sha
    f0e = files.get("research_map/formulation_taxonomy.yaml") or {}
    c["G1_frozen_pins_f0"] = f0e.get("sha256")
    return c


def check_h_review_status(doc):
    rs = doc.get("review_status") or {}
    return {
        "H1_review_status_verdict": rs.get("verdict"),
        "H1_review_status_reviewers": rs.get("independent_reviewers"),
        "H1_is_pending_empty": rs.get("verdict") == "pending" and not rs.get("independent_reviewers"),
    }


CHECKS_WITH_MUTANT = [
    "A1_strict_duplicate_key_free",
    "B1_timestamp_consistent",
    "C1_pointer_resolves_canonical_f0",
    "C3_declared_f0_matches_measured",
    "D1_exact_match_f2a_vs_f0",
    "D5_f2a_token_policy_conformant",
    "F1_exactly_C2",
    "F2_no_wcc_token_in_conclusion",
]


def run_all(text, inputs, t_now):
    f2a, dup = strict_load(text)
    res = {}
    _, a = check_a_parse(text, "AF-SCC-C2-VAC-GEN", "F2a")
    res.update(a)
    res.update(check_b_provenance(f2a, inputs["f2a_mtime"], t_now))
    res.update(
        check_c_binding(
            f2a,
            inputs["f0_doc"],
            inputs["supp_doc"],
            inputs["f0_sha"],
            inputs["supp_sha"],
            inputs["evidence_sha"],
        )
    )
    res.update(check_d_vocabulary(f2a, inputs["f0_doc"], inputs["vocab_doc"]))
    res.update(check_e_welltyped(f2a))
    res.update(check_f_class_integrity(f2a))
    res.update(check_g_publication(PINNED, inputs["frozen_doc"]))
    res.update(check_h_review_status(f2a))
    return f2a, res, dup


def mutate(text, kind):
    """Deterministic single-defect mutants, built from the pinned rev12 bytes."""
    if kind == "dup_key":
        # re-introduce a second top-level revised_at immediately before the real one
        return text.replace(
            'revised_at: "2026-09-12T00:31:41+08:00"',
            'revised_at: "2000-01-01T00:00:00+08:00"\nrevised_at: "2026-09-12T00:31:41+08:00"',
            1,
        )
    if kind == "future_ts":
        return text.replace(
            'revised_at: "2026-09-12T00:31:41+08:00"',
            'revised_at: "2099-01-01T00:00:00+08:00"',
            1,
        )
    if kind == "bad_pointer":
        return text.replace(
            "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN",
            "research_map/formulation_taxonomy.yaml#classes.NO-SUCH-CLASS",
            1,
        )
    if kind == "stale_f0":
        return text.replace(
            "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
            hashlib.sha256(b"stale").hexdigest(),
            1,
        )
    if kind == "alias_token":
        return text.replace(
            "conclusion_type: scc_c2_future_inextendibility",
            "conclusion_type: strong_cosmic_censorship_C2",
            1,
        )
    if kind == "wcc_leak":
        return text.replace(
            "Generic asymptotically flat vacuum initial data have a maximal development",
            "Generic asymptotically flat vacuum initial data visible from I+ (AF-WCC-VAC-GEN content) have a maximal development",
            1,
        )
    if kind == "composite_regularity":
        return text.replace("extension_regularity: C2", 'extension_regularity: "C0/C2"', 1)
    raise ValueError(kind)


def main():
    t0 = time.time()
    now = t0
    live = read_bytes(INPUTS["f2a_live"])
    inputs = {
        "f2a_live_sha": sha(live),
        "f2a_live_mtime": os.stat(os.path.join(ROOT, INPUTS["f2a_live"])).st_mtime,
        "pinned_sha": PINNED,
        "live_matches_pinned_at_start": sha(live) == PINNED,
    }
    for key in ("f0_canonical", "supplement", "vocab_aliases", "frozen_manifest", "consistency_evidence"):
        b = read_bytes(INPUTS[key])
        inputs[key + "_sha"] = sha(b)
    inputs["f0_doc"] = yaml.safe_load(read_bytes(INPUTS["f0_canonical"]))
    inputs["supp_doc"] = yaml.safe_load(read_bytes(INPUTS["supplement"]))
    inputs["vocab_doc"] = json.loads(read_bytes(INPUTS["vocab_aliases"]))
    inputs["frozen_doc"] = json.loads(read_bytes(INPUTS["frozen_manifest"]))
    inputs["f0_sha"] = inputs["f0_canonical_sha"]
    inputs["supp_sha"] = inputs["supplement_sha"]
    inputs["evidence_sha"] = inputs["consistency_evidence_sha"]
    # publication instant of rev12: the live file's mtime if the live bytes still
    # equal the pinned bytes, else the snapshot copy's mtime with the skew noted.
    inputs["f2a_mtime"] = (
        inputs["f2a_live_mtime"]
        if inputs["live_matches_pinned_at_start"]
        else os.stat(SNAP).st_mtime
    )
    inputs["f2a_mtime_source"] = (
        "live_file" if inputs["live_matches_pinned_at_start"] else "snapshot_copy"
    )

    snap_text = open(SNAP, "r", encoding="utf-8").read()
    doc, res, dups = run_all(snap_text, inputs, now)

    # ---- mutants: each must flip its target check to fail; baseline must pass ----
    mut_report = {}
    baseline_fail = [k for k in CHECKS_WITH_MUTANT if not res.get(k)]
    for kind, target in [
        ("dup_key", "A1_strict_duplicate_key_free"),
        ("future_ts", "B1_timestamp_consistent"),
        ("bad_pointer", "C1_pointer_resolves_canonical_f0"),
        ("stale_f0", "C3_declared_f0_matches_measured"),
        ("alias_token", "D5_f2a_token_policy_conformant"),
        ("wcc_leak", "F2_no_wcc_token_in_conclusion"),
        ("composite_regularity", "F1_exactly_C2"),
    ]:
        mtext = mutate(snap_text, kind)
        mpath = os.path.join(HERE, "mutants", f"mutant_{kind}.yaml")
        with open(mpath, "w", encoding="utf-8") as fh:
            fh.write(mtext)
        mdoc, mres, _ = run_all(mtext, inputs, now)
        mut_report[kind] = {
            "target_check": target,
            "target_failed_on_mutant": mres.get(target) is False,
            "mutant_sha256": sha(mtext.encode()),
            "mutant_path": os.path.relpath(mpath, ROOT),
            "other_checks_changed": sorted(
                k for k in res if k in mres and res.get(k) != mres.get(k)
            ),
        }
    # specificity: the unmodified pinned rev12 file must pass every mutant target
    baseline_ok = not baseline_fail

    # ---- drift re-measure at end ----
    live_end = read_bytes(INPUTS["f2a_live"])
    drift = sha(live_end) != PINNED
    res["Z1_live_sha_end"] = sha(live_end)
    res["Z1_drift_at_end"] = drift
    res["Z1_drift_voids_verdict"] = drift
    res["Z2_measurement_window_s"] = round(time.time() - t0, 2)

    evidence = {
        "task": "W059-F2A-REV12-VERDICT-01",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
        "pinned_artifact": "schemas/af_scc_c2_vacuum.yaml@" + PINNED,
        "pinned_snapshot": os.path.relpath(SNAP, ROOT),
        "inputs": {k: v for k, v in inputs.items() if not k.endswith("_doc")},
        "checks": res,
        "baseline_all_mutant_targets_pass": baseline_ok,
        "baseline_failed_targets": baseline_fail,
        "mutants": mut_report,
        "mutant_summary": {
            "mutants": len(mut_report),
            "targets_detected": sum(1 for m in mut_report.values() if m["target_failed_on_mutant"]),
            "specificity_ok": baseline_ok,
        },
        "instrument": {
            "path": os.path.relpath(os.path.abspath(__file__), ROOT),
            "sha256": sha(open(os.path.abspath(__file__), "rb").read()),
            "imports_only": ["hashlib", "json", "os", "subprocess", "sys", "time", "yaml"],
            "canonical_gate_imports": [],
        },
    }
    out = os.path.join(HERE, "independent_evidence.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
    print(json.dumps({
        "pinned": PINNED[:12],
        "live_at_start_matches": inputs["live_matches_pinned_at_start"],
        "drift_at_end": drift,
        "baseline_failed_targets": baseline_fail,
        "targets_detected": evidence["mutant_summary"]["targets_detected"],
        "key_fails": {k: v for k, v in res.items() if v is False},
        "evidence_sha256": sha(open(out, "rb").read()),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
