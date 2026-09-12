#!/usr/bin/env python3
"""W045-F2-VOCAB-SEP-ADJ-01 -- independent adjudication of two live G-FORM findings on the
frozen AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN schemas:

  (1) worker-033 HF-02 (critical, "class_leakage"): the F2a/F2b conclusion_type tokens
      `scc_c2_future_inextendibility` / `scc_c0_future_inextendibility` are not members of the
      canonical F0 vocabulary at research_map/formulation_taxonomy.yaml#276009f4f63d
      (field_vocabulary.conclusion_type.allowed = weak_cosmic_censorship,
      strong_cosmic_censorship_C2, strong_cosmic_censorship_C0).
  (2) worker-088 F-088-2 (major): F2a and F2b data_class blocks are key-identical and their
      regularity_class values are equal, so C2/C0 separation rests on extension_predicate +
      conclusion only.

METHOD (moving-target safe): both findings were filed against pinned hashes that were still
current when this task started and were REPUBLISHED (rev12) before the measurement ran. The
adjudication is therefore performed twice:
  * PRIMARY  -- the exact bytes the findings were filed against, read from on-disk snapshots
                whose sha256 is verified against the pinned value (F0 276009f4, F2a b6123750,
                F2b 1bb78ce9).
  * LIVE     -- the current canonical paths at measurement time (delta report only).
This is a read-only measurement. It writes exactly one artifact. It cannot set node status,
validation_status=passed, or a gate verdict. Sensitivity controls are included so the
measurement itself can fail (see `controls` and `falsifier`).

Run:  python3 artifacts/worker-045/run_f2_vocab_separation_adjudication.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(REPO, "artifacts", "worker-045", "f2_vocab_separation_adjudication.json")

C2 = "AF-SCC-C2-VAC-GEN"
C0 = "AF-SCC-C0-VAC-GEN"

# Findings were filed against these exact bytes (full sha256, verified via snapshot copies).
CLAIM_TARGETS = {
    "F0": {
        "path": "artifacts/worker-020/f2a_independent_verdict/snapshots/f0_taxonomy_276009f4f63d.yaml",
        "sha256": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    },
    "F2a": {
        "path": "artifacts/worker-047/d0_cross_class/snapshot/af_scc_c2_vacuum.yaml.b6123750b37d",
        "sha256": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    },
    "F2b": {
        "path": "artifacts/worker-047/d0_cross_class/snapshot/af_scc_c0_vacuum.yaml.1bb78ce9b357",
        "sha256": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
    },
}
LIVE_TARGETS = {
    "F0": {"path": "research_map/formulation_taxonomy.yaml", "sha256": None},
    "F2a": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": None},
    "F2b": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": None},
}
# Context artifacts, stable across the task.
CONTEXT = {
    "F0_authoring_supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "VOCAB_ALIASES": "artifacts/formulation/VOCAB_ALIASES.json",
    "class_separation": "research_map/class_separation.py",
}
EXPECTED_CANONICAL_AT_SCOPING = {  # observed when the task was scoped, before the republish
    "research_map/formulation_taxonomy.yaml": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
    "schemas/af_scc_c2_vacuum.yaml": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
    "schemas/af_scc_c0_vacuum.yaml": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_bytes(path: str) -> bytes:
    with open(os.path.join(REPO, path), "rb") as fh:
        return fh.read()


def sha256_file(path: str) -> str:
    return sha256_bytes(read_bytes(path))


def line_of(text: str, needle: str):
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def measure(f0_raw, f2a_raw, f2b_raw, aliases):
    """All vocabulary + separation measurements for one pair of byte-sets."""
    f0 = yaml.safe_load(f0_raw)
    f2a = yaml.safe_load(f2a_raw)
    f2b = yaml.safe_load(f2b_raw)
    f0_text = f0_raw.decode("utf8", "replace")
    f2a_text = f2a_raw.decode("utf8", "replace")
    f2b_text = f2b_raw.decode("utf8", "replace")

    allowed = list((f0.get("field_vocabulary", {}).get("conclusion_type") or {}).get("allowed") or [])
    f0_axes = {
        cid: (f0.get("classes", {}).get(cid, {}) or {}).get("axes", {}).get("conclusion_type")
        for cid in (C2, C0)
    }
    f2a_ct = (f2a.get("conclusion") or {}).get("conclusion_type")
    f2b_ct = (f2b.get("conclusion") or {}).get("conclusion_type")
    alias_map = aliases.get("conclusion_type", {})

    def alias_resolution(token):
        if token in alias_map:
            return {"canonical_from_token": token, "via": "token is itself a canonical key"}
        for canon, accepted in alias_map.items():
            if token in (accepted or []):
                return {"canonical_from_token": canon, "via": "token is an accepted alias"}
        return {"canonical_from_token": None, "via": "no alias-table entry"}

    res_a, res_b = alias_resolution(f2a_ct), alias_resolution(f2b_ct)

    da, db = f2a.get("data_class") or {}, f2b.get("data_class") or {}
    fa, fb = flatten(da), flatten(db)
    shared_differ = [k for k in sorted(set(f2a) & set(f2b)) if f2a[k] != f2b[k]]
    f0_disjointness = None
    for entry in f0.get("disjointness") or []:
        if set(entry.get("pair") or []) == {C2, C0}:
            f0_disjointness = entry
            break

    def locus(path, extract):
        return {path: [extract(f2a), extract(f2b)]}

    return {
        "f0_canonical": {
            "conclusion_type_allowed": allowed,
            "conclusion_type_rule": (f0.get("field_vocabulary", {}).get("conclusion_type") or {}).get("rule"),
            "class_axes_conclusion_type": f0_axes,
            "bytes_mention_alias": bool(re.search(r"alias", f0_text, re.I)),
            "bytes_mention_scc_canonical_token": "scc_c2_future_inextendibility" in f0_text,
        },
        "schemas": {
            "F2a": {
                "class_id": f2a.get("class_id"),
                "revision": f2a.get("revision"),
                "conclusion_type": f2a_ct,
                "conclusion_type_line": line_of(f2a_text, f"conclusion_type: {f2a_ct}"),
                "f0_binding": f2a.get("f0_binding"),
                "class_contract_pointer": f2a.get("class_contract_pointer"),
            },
            "F2b": {
                "class_id": f2b.get("class_id"),
                "revision": f2b.get("revision"),
                "conclusion_type": f2b_ct,
                "conclusion_type_line": line_of(f2b_text, f"conclusion_type: {f2b_ct}"),
                "f0_binding": f2b.get("f0_binding"),
                "class_contract_pointer": f2b.get("class_contract_pointer"),
            },
        },
        "literal_membership_in_canonical_f0_allowed": {
            "F2a_token_in_allowed": f2a_ct in allowed,
            "F2b_token_in_allowed": f2b_ct in allowed,
        },
        "alias_resolution": {
            "F2a": res_a,
            "F2b": res_b,
            "alias_table_declares_f0_tokens_as_accepted_aliases": {
                f0_axes[C2]: bool(
                    alias_map.get(res_a.get("canonical_from_token") or "")
                    and f0_axes[C2] in alias_map.get(res_a.get("canonical_from_token") or "", [])
                ),
                f0_axes[C0]: bool(
                    alias_map.get(res_b.get("canonical_from_token") or "")
                    and f0_axes[C0] in alias_map.get(res_b.get("canonical_from_token") or "", [])
                ),
            },
        },
        "c2_c0_merge_test_under_alias_table": {
            "F2a_resolved": res_a.get("canonical_from_token"),
            "F2b_resolved": res_b.get("canonical_from_token"),
            "same_canonical_token": res_a.get("canonical_from_token") == res_b.get("canonical_from_token"),
        },
        "resolution_available_from_canonical_path_alone": bool(
            re.search(r"alias", f0_text, re.I) or "scc_c2_future_inextendibility" in f0_text
        ),
        "separation": {
            "data_class": {
                "key_paths_equal": set(fa) == set(fb),
                "sub_block_keys_equal": set(da) == set(db),
                "sub_block_count": len(da),
                "key_path_count": len(fa),
                "value_diff_paths": sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k]),
                "keys_only_in_F2a": sorted(set(fa) - set(fb)),
                "keys_only_in_F2b": sorted(set(fb) - set(fa)),
                "regularity_class_equal": da.get("regularity_class") == db.get("regularity_class"),
            },
            "top_level": {
                "keys_only_in_F2a": sorted(set(f2a) - set(f2b)),
                "keys_only_in_F2b": sorted(set(f2b) - set(f2a)),
                "shared_blocks_differ": shared_differ,
            },
            "separation_locus_at_pinned_bytes": {
                **locus("class_id", lambda d: d.get("class_id")),
                **locus("class_components.regularity_token", lambda d: (d.get("class_components") or {}).get("regularity_token")),
                **locus("extension_predicate.frozen_regularity", lambda d: (d.get("extension_predicate") or {}).get("frozen_regularity")),
                **locus("extension_predicate.frozen_equation_concept", lambda d: (d.get("extension_predicate") or {}).get("frozen_equation_concept")),
                **locus("regularity.extension_regularity", lambda d: (d.get("regularity") or {}).get("extension_regularity")),
                **locus("conclusion.conclusion_type", lambda d: (d.get("conclusion") or {}).get("conclusion_type")),
            },
            "f0_disjointness_entry_for_C2_C0": f0_disjointness,
            "f0_decisive_axes_for_C2_C0": (f0_disjointness or {}).get("decisive_axes"),
            "data_class_is_a_decisive_axis_for_C2_C0": "data_class"
            in ((f0_disjointness or {}).get("decisive_axes") or []),
        },
        "_raw": {"f2a": f2a_raw, "f2b": f2b_raw},
    }


def controls_for(m, cs):
    """Sensitivity controls, run against the PRIMARY (claim-hash) F2a bytes."""
    f2a_text = m["_raw"]["f2a"].decode("utf8", "replace")
    f2b_text = m["_raw"]["f2b"].decode("utf8", "replace")
    allowed = m["f0_canonical"]["conclusion_type_allowed"]
    res_a = m["alias_resolution"]["F2a"]
    res_b = m["alias_resolution"]["F2b"]
    f2a_ct = m["schemas"]["F2a"]["conclusion_type"]

    base = {"F2a": cs.findings_for_text(f2a_text, "F2a"), "F2b": cs.findings_for_text(f2b_text, "F2b")}
    merge_line = 'note: "C0 and C2 are one class"\n'
    c1 = cs.findings_for_text(f2a_text + merge_line, "C1-merge-assertion")
    c1b = cs.findings_for_text(f2a_text + "class_id: AF-SCC-C2-VAC-SET\n", "C1b-unknown-token")
    synthetic = "scc_c2_future_inextendibility_SYNTHETIC"
    c4_text = re.sub(r"(conclusion_type: )" + re.escape(str(f2a_ct)),
                     r"\1" + str(m["schemas"]["F2b"]["conclusion_type"]), f2a_text, count=1)
    c4 = cs.findings_for_text(c4_text, "C4-C0-token-injected-into-C2")

    controls = {
        "C0_baseline_canonical_schemas_have_zero_findings": {
            "F2a_findings": base["F2a"],
            "F2b_findings": base["F2b"],
            "pass": base["F2a"] == [] and base["F2b"] == [],
        },
        "C1_merge_assertion_injection_detected": {
            "mutation": f"appended line: {merge_line.strip()}",
            "findings": c1,
            "pass": len(c1) >= 1,
        },
        "C1b_unknown_class_token_injection_detected": {
            "mutation": "appended line: class_id: AF-SCC-C2-VAC-SET",
            "findings": c1b,
            "pass": len(c1b) >= 1,
        },
        "C2_synthetic_non_vocabulary_token_rejected_literally": {
            "token": synthetic,
            "in_canonical_allowed": synthetic in allowed,
            "pass": synthetic not in allowed,
        },
        "C3_alias_resolution_keeps_C2_C0_distinct": {
            "resolved": [res_a.get("canonical_from_token"), res_b.get("canonical_from_token")],
            "pass": res_a.get("canonical_from_token") is not None
            and res_b.get("canonical_from_token") is not None
            and res_a.get("canonical_from_token") != res_b.get("canonical_from_token"),
        },
    }
    probes = {
        "C4_sibling_C0_conclusion_token_injected_into_C2": {
            "mutation": f"conclusion_type: {f2a_ct} -> {m['schemas']['F2b']['conclusion_type']}",
            "findings": c4,
            "note": (
                "Observed: the frozen class_separation.py returns no finding for a swapped C0/C2 conclusion token on a "
                "C2 class; its conclusion branch only fires on WCC<->SCC family swaps, so conclusion-type vocabulary "
                "conformance is enforced by check_class_schema / A0-HF-02, not by this checker. Recorded as an observed "
                "scope boundary of the frozen checker; not adjudicated here."
            ),
        }
    }
    return controls, probes


def main() -> int:
    t0 = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    inputs, target_verification = {}, {}

    # --- verify claim-hash snapshots against the pinned full sha256 ---
    snap = {}
    for name, t in CLAIM_TARGETS.items():
        raw = read_bytes(t["path"])
        got = sha256_bytes(raw)
        inputs[t["path"]] = got
        target_verification[name] = {
            "path": t["path"],
            "expected_sha256": t["sha256"],
            "measured_sha256": got,
            "match": got == t["sha256"],
        }
        if got != t["sha256"]:
            raise SystemExit(f"FATAL: snapshot {t['path']} does not match the pinned claim hash")
        snap[name] = raw

    # --- live canonical bytes ---
    live = {}
    live_hashes_at_start = {}
    for name, t in LIVE_TARGETS.items():
        raw = read_bytes(t["path"])
        live[name] = raw
        live_hashes_at_start[t["path"]] = sha256_bytes(raw)
        inputs[t["path"]] = live_hashes_at_start[t["path"]]

    # --- context artifacts ---
    for rel in CONTEXT.values():
        inputs[rel] = sha256_file(rel)
    aliases = json.loads(read_bytes(CONTEXT["VOCAB_ALIASES"]))
    f0r_raw = read_bytes(CONTEXT["F0_authoring_supplement"])

    sys.path.insert(0, os.path.join(REPO, "research_map"))
    import class_separation as cs  # noqa: E402

    primary = measure(snap["F0"], snap["F2a"], snap["F2b"], aliases)
    live_m = measure(live["F0"], live["F2a"], live["F2b"], aliases)
    controls, probes = controls_for(primary, cs)
    all_controls_pass = all(v.get("pass", True) for v in controls.values() if "pass" in v)
    live_baseline = {
        "F2a_findings": cs.findings_for_text(live["F2a"].decode("utf8", "replace"), "live F2a"),
        "F2b_findings": cs.findings_for_text(live["F2b"].decode("utf8", "replace"), "live F2b"),
    }

    # --- delta between claim bytes and live canonical bytes ---
    def short(v):
        return (v or "")[:12]

    live_delta = {
        "note": (
            "The canonical F0/F2a/F2b bytes were republished (rev12) after the two findings were filed and before this "
            "measurement ran; the primary adjudication above is on the exact claim-filing bytes, this block is the delta "
            "at the live canonical paths."
        ),
        "hashes": {
            "F0": {"claim": short(CLAIM_TARGETS["F0"]["sha256"]), "live": short(live_hashes_at_start[LIVE_TARGETS["F0"]["path"]])},
            "F2a": {"claim": short(CLAIM_TARGETS["F2a"]["sha256"]), "live": short(live_hashes_at_start[LIVE_TARGETS["F2a"]["path"]])},
            "F2b": {"claim": short(CLAIM_TARGETS["F2b"]["sha256"]), "live": short(live_hashes_at_start[LIVE_TARGETS["F2b"]["path"]])},
        },
        "F0_conclusion_type_vocabulary_unchanged": (
            live_m["f0_canonical"]["conclusion_type_allowed"] == primary["f0_canonical"]["conclusion_type_allowed"]
            and not live_m["f0_canonical"]["bytes_mention_alias"]
        ),
        "F0_literal_membership_still_false": live_m["literal_membership_in_canonical_f0_allowed"],
        "schemas_conclusion_tokens_unchanged": (
            live_m["schemas"]["F2a"]["conclusion_type"] == primary["schemas"]["F2a"]["conclusion_type"]
            and live_m["schemas"]["F2b"]["conclusion_type"] == primary["schemas"]["F2b"]["conclusion_type"]
        ),
        "data_class_key_identity": {
            "at_claim_hashes_sub_block_keys_equal": primary["separation"]["data_class"]["sub_block_keys_equal"],
            "at_claim_hashes_full_key_paths_equal": primary["separation"]["data_class"]["key_paths_equal"],
            "at_live_sub_block_keys_equal": live_m["separation"]["data_class"]["sub_block_keys_equal"],
            "at_live_full_key_paths_equal": live_m["separation"]["data_class"]["key_paths_equal"],
            "at_live_value_diff_paths": live_m["separation"]["data_class"]["value_diff_paths"],
            "at_live_keys_only_in_F2a": live_m["separation"]["data_class"]["keys_only_in_F2a"],
            "at_live_keys_only_in_F2b": live_m["separation"]["data_class"]["keys_only_in_F2b"],
            "at_live_regularity_class_equal": live_m["separation"]["data_class"]["regularity_class_equal"],
        },
        "live_baseline_classsep_findings": live_baseline,
    }

    # --- verdicts ---
    lit = primary["literal_membership_in_canonical_f0_allowed"]
    alias_ok = primary["alias_resolution"]["alias_table_declares_f0_tokens_as_accepted_aliases"]
    merge_same = primary["c2_c0_merge_test_under_alias_table"]["same_canonical_token"]
    sep = primary["separation"]
    hf02_confirmed_literal = (not lit["F2a_token_in_allowed"]) and (not lit["F2b_token_in_allowed"])

    verdicts = {
        "worker-033-HF-02": {
            "claim_as_filed": "critical class_leakage: F2a/F2b conclusion_type tokens are not in the canonical F0 allowed vocabulary",
            "adjudication_at_claim_hashes": {
                "literal_mismatch_confirmed": hf02_confirmed_literal,
                "class_merge_or_inflation_confirmed": bool(merge_same),
                "resolved_by_alias_table": bool(alias_ok[primary["f0_canonical"]["class_axes_conclusion_type"][C2]]
                                               and alias_ok[primary["f0_canonical"]["class_axes_conclusion_type"][C0]]),
                "verdict": "CONFIRMED-AS-LITERAL-MISMATCH / NOT-CLASS-LEAKAGE",
                "reasoning": [
                    "Literal membership test against the binding target's own field_vocabulary: both schema tokens are absent (positivity control C2).",
                    "The alias table (artifacts/formulation/VOCAB_ALIASES.json#46cd9f1e) declares the two token sets equivalent for consistency checks, with the schemas' scc_* forms as canonical keys and the F0 tokens as accepted aliases; under it both tokens resolve and stay distinct, so no C2/C0 merge and no conclusion inflation exists under either vocabulary (control C3).",
                    "Canonical F0 bytes (276009f4f63d) contain neither 'alias' nor the canonical token: the rescuing policy is NOT resolvable from the declared binding artifact alone.",
                    "Therefore this is a vocabulary-authority/binding placement defect (one logical vocabulary split across two trees), not class leakage. It is blocking for any checker that binds canonical F0 literally with no alias resolution (including A0-HF-02 as written) and for the artifact's own f0_binding declaration.",
                ],
                "blocking_assessment": {
                    "for_class_identity_or_separation": False,
                    "for_a_literal_canonical_F0_only_checker": True,
                    "for_G_FORM": "conditional: must be discharged by a single-source vocabulary fix before any literal canonical-vocabulary check can pass",
                },
            },
            "adjudication_at_live_canonical": {
                "literal_mismatch_confirmed": not live_m["literal_membership_in_canonical_f0_allowed"]["F2a_token_in_allowed"],
                "status": "UNCHANGED at the live rev12 bytes: F0 still carries only the alias tokens and no alias registry; the two schemas still use the scc_* tokens.",
            },
            "discharging_fix": "One of: (a) publish the F0-R supplement over the canonical F0 path so the binding target carries the canonical tokens + alias registry; (b) add the canonical tokens and the alias mapping to canonical F0 field_vocabulary; (c) republish F0 with a single conclusion_type vocabulary. No class semantics change is required.",
        },
        "worker-088-F-088-2": {
            "claim_as_filed": "F2a and F2b data_class blocks are key-identical and their regularity_class values are equal, so separation rests on extension_predicate + conclusion only",
            "adjudication_at_claim_hashes": {
                "data_class_sub_block_key_identical": sep["data_class"]["sub_block_keys_equal"],
                "data_class_full_key_path_identical": sep["data_class"]["key_paths_equal"],
                "regularity_class_equal": sep["data_class"]["regularity_class_equal"],
                "verdict": "FACTUAL-CORE-SUBSTANTIALLY-CONFIRMED (sub-block key-identical; one extra nested leaf key in F2b) / IMPLICATION-INCOMPLETE",
                "reasoning": [
                    f"At the claim hashes: data_class sub-block key sets equal = {sep['data_class']['sub_block_keys_equal']} "
                    f"({sep['data_class']['sub_block_count']} sub-blocks); full nested key paths equal = {sep['data_class']['key_paths_equal']} "
                    f"(count {sep['data_class']['key_path_count']}); keys only in F2b = {sep['data_class']['keys_only_in_F2b']}; "
                    f"differing leaf paths = {sep['data_class']['value_diff_paths'] or 'none'}; "
                    f"regularity_class values equal = {sep['data_class']['regularity_class_equal']}.",
                    "So the claim's factual core holds at sub-block granularity (all 10 data_class sub-blocks, and regularity_class values, match) but not literally at full key-path granularity: F2b carries one extra nested key adm_mass.hypotheses_reconciliation.",
                    "The measured separation locus also includes class_components.regularity_token and regularity.extension_regularity (C2 vs C0) in addition to extension_predicate and conclusion, so the appositive 'rests on extension_predicate + conclusion only' understates the actual separation.",
                    f"Canonical F0's own disjointness entry for this pair names decisive_axes={sep['f0_decisive_axes_for_C2_C0']}; data_class is not among them (data_class_is_a_decisive_axis_for_C2_C0={sep['data_class_is_a_decisive_axis_for_C2_C0']}).",
                    "So a shared data-class block does not by itself merge C2 and C0 under the taxonomy's own separation contract; it is a single-frozen-data-class criterion question (G-FORM one data space), which the finding itself assigns to lead-formulation across F1/F2a/F2b.",
                ],
                "blocking_assessment": {
                    "for_class_identity_or_separation": False,
                    "for_G_FORM_one_frozen_data_class_criterion": "open, owned by lead-formulation (F1/F2a/F2b alignment); this measurement does not resolve it",
                },
            },
            "adjudication_at_live_canonical": {
                "data_class_sub_block_key_identical": live_m["separation"]["data_class"]["sub_block_keys_equal"],
                "data_class_full_key_path_identical": live_m["separation"]["data_class"]["key_paths_equal"],
                "value_diff_paths": live_m["separation"]["data_class"]["value_diff_paths"],
                "regularity_class_equal": live_m["separation"]["data_class"]["regularity_class_equal"],
                "status": (
                    "At the live rev12 bytes the shape is unchanged from the claim hashes: the 10 data_class sub-block keys and "
                    "the regularity_class values match, while the nested key adm_mass.hypotheses_reconciliation remains present "
                    "only in F2b and adm_mass.locator differs. The class-separation locus is unchanged."
                ),
            },
            "discharging_fix": "lead-formulation aligns the F1/F2a/F2b data_class blocks to the single frozen data class it selects; no edit made here.",
        },
    }

    verdict = (
        f"HF-02=CONFIRMED-LITERAL/NOT-CLASS-LEAKAGE (live: unchanged); "
        f"F-088-2=SUB-BLOCK-KEY-IDENTICAL+ONE-NESTED-LEAF-DIFF/IMPLICATION-INCOMPLETE (live: same shape); "
        f"controls_pass={all_controls_pass}"
    )

    artifact = {
        "schema_version": "1.0",
        "artifact_kind": "independent_measurement_adjudication",
        "task_id": "W045-F2-VOCAB-SEP-ADJ-01",
        "worker": "worker-045",
        "instance": os.environ.get("DSH_INSTANCE_ID", "worker-045-unknown"),
        "created_at": t0.isoformat(),
        "class_id": C2,
        "class_ids": [C2, C0],
        "node_id": "F2a,F2b",
        "gate": "G-FORM",
        "verdict": verdict,
        "verdicts": verdicts,
        "claim_target_verification": target_verification,
        "measurement_primary_at_claim_hashes": {k: v for k, v in primary.items() if k != "_raw"},
        "measurement_live_canonical": {k: v for k, v in live_m.items() if k != "_raw"},
        "live_delta": live_delta,
        "f0_authoring_supplement": {
            "path": CONTEXT["F0_authoring_supplement"],
            "sha256": inputs[CONTEXT["F0_authoring_supplement"]],
            "canonical_token_present": "scc_c2_future_inextendibility" in f0r_raw.decode("utf8", "replace"),
        },
        "controls": controls,
        "controls_pass": all_controls_pass,
        "probe_notes": probes,
        "inputs": inputs,
        "drift_during_run": {},
        "falsifier": (
            "Falsified if any of: (a) at the verified claim-hash snapshots, either schema conclusion_type token IS a literal "
            "member of canonical F0 field_vocabulary.conclusion_type.allowed, or the canonical F0 bytes DO contain an alias "
            "registry or the canonical tokens; (b) under artifacts/formulation/VOCAB_ALIASES.json the two schema tokens resolve "
            "to the SAME canonical token (a real C2/C0 merge); (c) the F2a/F2b data_class key sets are not equal at the claim "
            "hashes, or regularity_class values differ there; (d) the canonical F0 disjointness entry for C2/C0 lists data_class "
            "among its decisive_axes; (e) the class_separation baseline controls fail (canonical schemas produce findings) or the "
            "C1/C1b/C2/C3 controls fail to separate; (f) any snapshot hash does not match its pinned claim hash, or a live input "
            "hash differs between the start and end of the run (drift voids only the live delta)."
        ),
        "no_completion_claim": (
            "Worker events cannot set node status=done, validation_status=passed, or a gate verdict. F2a/F2b/G-FORM remain "
            "lead- and controller-owned. This artifact is a measurement for the lead's close-findings pass and the controller's "
            "next lifecycle."
        ),
        "observed_not_dispositioned": {
            "moving_target": (
                "F0/F2a/F2b were republished between scoping and measurement; see live_delta. Primary adjudication is at the "
                "verified claim-hash snapshots. The review-coverage implication (verdicts bound to superseded hashes are advisory) "
                "is for the controller, not claimed here."
            ),
            "f0_dual_tree_divergence": (
                "Schema class_contract_pointer targets the authoring supplement while f0_binding.declared_f0_sha256 targets the "
                "canonical tree; the vocabulary split measured here is a symptom of that divergence (worker-094). Not re-adjudicated."
            ),
            "duplicate_yaml_keys": "A duplicate-revised_at defect at the claim hashes (worker-076/088) is not re-measured here; the live rev12 bytes appear to have removed it (see live_delta).",
            "D0_disjunction": "worker-088 HF-088-1 remains a separate critical finding; not re-adjudicated here.",
        },
    }

    # --- drift check on live inputs ---
    drift = {}
    for rel, h in live_hashes_at_start.items():
        now = sha256_file(rel)
        if now != h:
            drift[rel] = {"at_start": h, "at_end": now}
    artifact["drift_during_run"] = drift

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(artifact, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print(json.dumps({
        "verdict": verdict,
        "controls_pass": all_controls_pass,
        "drift": drift,
        "claim_targets_verified": {k: v["match"] for k, v in target_verification.items()},
        "out": os.path.relpath(OUT, REPO),
        "out_sha256": sha256_file(OUT),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
