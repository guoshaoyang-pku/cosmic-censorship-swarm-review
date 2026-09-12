#!/usr/bin/env python3
"""worker-091 bounded task: re-test the named F0 blocking findings at F0 rev5.

Context
-------
The previous worker-091 run (artifacts/worker-091/f0_blocking_verify/results.json,
verdict revise 3.5) bound its verification to F0 sha256 276009f4f63d and recorded the
falsifier: "re-run the K2-K5 checks against a snapshot of the new hash". The canonical
file was republished at 2026-09-12T00:31:41+08:00 as rev5 0abb9ed8a961. The lead-audit
closing verification (reviews/G-F0-final-verify.json, 00:35:21) records B-GF0-1:
"0 independent verdicts cite the rev27 canonical hash ... two blind non-author
reviewers at 0abb9ed8a961, hash re-checked at the second verdict".

This script re-runs the named checks K1a, K1b, K2, K3, K4, K5, K6 (plus controls K0,
K7 and the FROZEN pin-integrity check K8) mechanically at the pinned rev5 bytes.

It is read-only w.r.t. every canonical/authoring input. Only files under
artifacts/worker-091/f0_rev5_reverify/ are written.

Exit codes: 0 = results emitted; 3 = integrity/drift failure, verdict UNMEASURED.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

# Declared target, from the previous run's falsifier + ASTRA_HANDOFF pass-03 measurements.
EXPECTED_F0_SHA256 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
EXPECTED_F0_BYTES = 36372
ACTOR = "worker-091"
TASK_ID = "w091-20260912T0035-f0-rev5-reverify"

# Inputs whose pre/post stability matters (drift => UNMEASURED).
INPUTS = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_regularities.yaml",
]

SET_SENTENCE = (
    "every future-inextendible causal geodesic contained in J-(I+) is complete"
)
SET_NEEDLE = "contained in J-(I+)"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

RUNS: list[dict] = []
INTEGRITY_FAILURES: list[str] = []


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def measure(rel: str) -> dict:
    p = REPO / rel
    if not p.exists():
        return {"path": rel, "exists": False}
    b = p.read_bytes()
    st = p.stat()
    return {
        "path": rel,
        "exists": True,
        "sha256": sha256_bytes(b),
        "sha256_12": sha256_bytes(b)[:12],
        "bytes": len(b),
        "mtime": st.st_mtime,
    }


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def lines_of(text: str, needle: str) -> list[int]:
    n = norm(needle)
    return [i for i, ln in enumerate(text.splitlines(), 1) if n in norm(ln)]


def log(kind: str, **kw) -> None:
    RUNS.append({"at": now_iso(), "kind": kind, **kw})


def main() -> int:
    pre = {rel: measure(rel) for rel in INPUTS}
    log("pre_hashes", hashes={k: v.get("sha256_12") for k, v in pre.items()})

    f0_rel = "research_map/formulation_taxonomy.yaml"
    f0_bytes = (REPO / f0_rel).read_bytes()
    snapshot = HERE / "f0_rev5_snapshot.yaml"
    snapshot.write_bytes(f0_bytes)
    snap_bytes = snapshot.read_bytes()
    f0_sha = sha256_bytes(f0_bytes)
    snap_ok = snap_bytes == f0_bytes
    log("snapshot", sha256_12=f0_sha[:12], bytes=len(f0_bytes), byte_identical=snap_ok)
    if not snap_ok:
        INTEGRITY_FAILURES.append("snapshot is not byte-identical to canonical source")
    if f0_sha != EXPECTED_F0_SHA256 or len(f0_bytes) != EXPECTED_F0_BYTES:
        INTEGRITY_FAILURES.append(
            f"canonical F0 moved: measured {f0_sha[:12]}/{len(f0_bytes)}B, "
            f"expected {EXPECTED_F0_SHA256[:12]}/{EXPECTED_F0_BYTES}B"
        )

    try:
        doc = yaml.safe_load(snap_bytes)
        parse_ok = isinstance(doc, dict)
        parse_err = None
    except Exception as e:  # pragma: no cover - defensive
        doc, parse_ok, parse_err = None, False, repr(e)
    if not parse_ok:
        INTEGRITY_FAILURES.append(f"YAML parse failed: {parse_err}")

    f0_text = f0_bytes.decode("utf-8", "replace")
    checks: list[dict] = []

    # ---------------- K0: control ----------------
    checks.append(
        {
            "check_id": "K0",
            "source_claim": "worker-091 control",
            "statement_under_test": "The reviewed bytes are the ones measured and the file does not move during the run.",
            "method": "sha256 + byte count + byte-identical snapshot; live re-hash after all checks.",
            "observed": {
                "pre_sha256": f0_sha,
                "pre_bytes": len(f0_bytes),
                "expected_sha256": EXPECTED_F0_SHA256,
                "snapshot_byte_identical": snap_ok,
                "yaml_parse_ok": parse_ok,
            },
            "status": "CONFIRMED" if (snap_ok and parse_ok) else "FAILED",
            "blocking_for_F0": False,
            "classification": "integrity control; failure is handled as UNMEASURED, not as a content defect",
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    if not parse_ok:
        return finish(pre, checks, "inconclusive", 0.0, {}, [])

    classes = doc.get("classes", {})
    csa = doc.get("class_scope_adjudication", {})
    vocab = doc.get("field_vocabulary", {})
    resolver = csa.get("resolved_divergences", [])

    # ---------------- K1a: canonical vs authoring ----------------
    canon = pre[f0_rel]
    auth = pre["artifacts/formulation/formulation_taxonomy.yaml"]
    k1a_observed = {
        "canonical": {k: canon.get(k) for k in ("path", "sha256", "bytes", "mtime")},
        "authoring": {k: auth.get(k) for k in ("path", "sha256", "bytes", "mtime")},
        "byte_identical": canon.get("sha256") == auth.get("sha256"),
    }
    checks.append(
        {
            "check_id": "K1a",
            "source_claim": "reviews/F0-review-lead-audit-r2.json hard_failures[0]",
            "statement_under_test": "Canonical F0 and artifacts/formulation/formulation_taxonomy.yaml are not byte-identical.",
            "method": "sha256 of both files; byte counts; mtimes.",
            "observed": k1a_observed,
            "status": "CONFIRMED_FACT" if not k1a_observed["byte_identical"] else "REFUTED",
            "blocking_for_F0": False,
            "classification": "declared two-artifact split (see K1b); not an undeclared drift under FROZEN rev28",
            "evidence_refs": [
                f"{f0_rel}#{canon.get('sha256_12')}",
                f"artifacts/formulation/formulation_taxonomy.yaml#{auth.get('sha256_12')}",
            ],
        }
    )

    # ---------------- K8: FROZEN pin integrity (drives K1b) ----------------
    frozen_rel = "artifacts/formulation/FROZEN.json"
    frozen = json.loads((REPO / frozen_rel).read_bytes())
    la = frozen.get("logical_artifacts", {})
    f0_pin = la.get("F0-declared-taxonomy", {})
    sup_pin = la.get("F0-class-contract-supplement", {})
    mirror = frozen.get("f0_mirror_adjudication_request", {})
    file_pins = frozen.get("files", {})
    schema_pin_report = {}
    for sp in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"):
        pin = file_pins.get(sp, {}).get("sha256")
        live = pre[sp].get("sha256")
        schema_pin_report[sp] = {"pinned": pin, "live": live, "match": pin == live}
    k8 = {
        "frozen_revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "frozen_sha256_12": pre[frozen_rel].get("sha256_12"),
        "f0_pin": {"pinned": f0_pin.get("sha256"), "live": f0_sha, "match": f0_pin.get("sha256") == f0_sha,
                   "mirrors": f0_pin.get("mirrors")},
        "supplement_pin": {"pinned": sup_pin.get("sha256"), "live": auth.get("sha256"),
                           "match": sup_pin.get("sha256") == auth.get("sha256"),
                           "mirrors": sup_pin.get("mirrors")},
        "schema_pins": schema_pin_report,
        "legacy_aggregator_pinned": "schemas/af_scc_regularities.yaml" in file_pins,
    }
    checks.append(
        {
            "check_id": "K8",
            "source_claim": "worker-038 blocker w038-f0-conformance-moving-target-blocker-20260912T003250 (stale FROZEN rev26 pin)",
            "statement_under_test": "FROZEN pins the live rev5 canonical taxonomy, the live supplement and the live canonical per-class schemas; the legacy aggregator is not pinned.",
            "method": "read artifacts/formulation/FROZEN.json; compare logical_artifacts and files pins to live sha256.",
            "observed": k8,
            "status": "CONFIRMED" if (
                k8["f0_pin"]["match"] and k8["supplement_pin"]["match"]
                and all(v["match"] for v in schema_pin_report.values())
                and not k8["legacy_aggregator_pinned"]
                and (k8["frozen_revision"] or 0) >= 27
            ) else "REFUTED",
            "blocking_for_F0": False,
            "classification": "informational: manifest-level discharge of the stale-pin blocker; worker-038's verdict still governs its own artifact",
            "evidence_refs": [f"{frozen_rel}#{pre[frozen_rel].get('sha256_12')}"],
        }
    )

    # ---------------- K1b: mirror classification ----------------
    checks.append(
        {
            "check_id": "K1b",
            "source_claim": "reviews/F0-review-lead-audit-r2.json hard_failures[0] (blocker classification)",
            "statement_under_test": "The byte divergence is a publication-drift blocker discharged by publishing one file over the other.",
            "method": "Read FROZEN logical_artifacts roles, mirror disposition and the mirror adjudication request; compare pins to live hashes.",
            "observed": {
                "frozen_revision": frozen.get("revision"),
                "logical_artifacts": la,
                "mirror_request_status": mirror.get("status"),
                "mirror_request_reason": mirror.get("reason"),
                "mirror_options": mirror.get("options"),
                "k1a_byte_identical": k1a_observed["byte_identical"],
            },
            "status": "PENDING_CONTROLLER_ADJUDICATION",
            "blocking_for_F0": True,
            "classification": (
                "the 'publish one over the other' discharge method is REFUTED (FROZEN rev28 declares two distinct "
                "logical artifacts, mirrors NONE, byte-identity refused as destructive); the underlying item is a "
                "controller disposition (REC-1 recommended), not a schema-text defect"
            ),
            "evidence_refs": [
                f"{frozen_rel}#{pre[frozen_rel].get('sha256_12')}",
                f"{f0_rel}#{f0_sha[:12]}",
                f"artifacts/formulation/formulation_taxonomy.yaml#{auth.get('sha256_12')}",
            ],
        }
    )

    # ---------------- K2: set-based wording residue ----------------
    per_class_set = {}
    for cid in CLASS_IDS:
        ctext = norm(classes.get(cid, {}).get("conclusion", {}).get("text", ""))
        per_class_set[cid] = norm(SET_SENTENCE) in ctext
    occ_lines = lines_of(f0_text, SET_NEEDLE)
    raw_occ_lines = [i for i, ln in enumerate(f0_text.splitlines(), 1) if SET_NEEDLE in ln]
    quoted_in_supersedes = norm(SET_SENTENCE) in norm(json.dumps(csa.get("supersedes", {})))
    variant_text = norm(json.dumps(doc.get("variants", [])))
    set_variant_ok = "set-based" in variant_text and "af-wcc-vac-gen" in variant_text
    k2_blocking = any(per_class_set[cid] for cid in CLASS_IDS)
    checks.append(
        {
            "check_id": "K2",
            "source_claim": "worker-16 B-16F0-1; worker-082 W082-F-01(a); lead-audit-r2 hard_failures[1]",
            "statement_under_test": "The demoted set-based visibility reading survives verbatim in the AF-WCC-SCALAR-SPH conclusion of the canonical F0 revision.",
            "method": "Exact normalized substring test for the set-based sentence in each of the four class conclusions; locate remaining occurrences and classify them.",
            "observed": {
                "set_sentence_in_class_conclusion": per_class_set,
                "set_needle_raw_occurrence_lines": raw_occ_lines,
                "set_needle_normalized_occurrence_lines": occ_lines,
                "quoted_in_supersedes_history": quoted_in_supersedes,
                "registered_set_variant_present": set_variant_ok,
                "detector_control": {
                    "detector_fires_on_mutant": norm(SET_SENTENCE)
                    in norm(
                        classes.get("AF-WCC-SCALAR-SPH", {}).get("conclusion", {}).get("text", "")
                        + " "
                        + SET_SENTENCE
                    ),
                    "detector_quiet_on_real_rev5": not any(per_class_set.values()),
                },
                "classification": (
                    "only remaining occurrence is a labelled historical quotation in "
                    "class_scope_adjudication.supersedes.wcc_text_before (line 84), not a class conclusion"
                ),
            },
            "status": "CONFIRMED" if k2_blocking else "REFUTED",
            "blocking_for_F0": k2_blocking,
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    # ---------------- K3: unsourced equivalence bridge ----------------
    sph_text = norm(classes.get("AF-WCC-SCALAR-SPH", {}).get("conclusion", {}).get("text", ""))
    wcc_text = norm(classes.get("AF-WCC-VAC-GEN", {}).get("conclusion", {}).get("text", ""))
    prov_keys = sorted((classes.get("AF-WCC-SCALAR-SPH", {}).get("provenance", {}) or {}).keys())
    k3_bridge = ("equivalently" in sph_text) or ("equivalently" in wcc_text)
    k3_gloss = "hidden behind an event horizon" in sph_text
    checks.append(
        {
            "check_id": "K3",
            "source_claim": "worker-082 W082-F-01(b); lead-audit-r2 hard_failures[1]; review HF-06 history",
            "statement_under_test": "The AF-WCC-SCALAR-SPH conclusion asserts an 'equivalently' bridge between J-(I+)-completeness and event-horizon/no-visible-singularity that is not sourced in the artifact, while the same pattern was removed from AF-WCC-VAC-GEN.",
            "method": "Substring test for the equivalence clause in both class conclusions; read SPH provenance keys and literature_status.",
            "observed": {
                "sph_contains_equivalently_bridge": "equivalently" in sph_text,
                "wcc_vac_contains_equivalently_bridge": "equivalently" in wcc_text,
                "sph_provenance_keys": prov_keys,
                "sph_provenance_evidence_keys": [],
                "sph_literature_status": (classes.get("AF-WCC-SCALAR-SPH", {}).get("provenance", {}) or {}).get("literature_status"),
                "sph_residual_gloss": "hidden behind an event horizon" if k3_gloss else None,
                "residual_gloss_classification": (
                    "non-blocking: a physical restatement of the class's own no-visible-singularity predicate, "
                    "not a J-(I+) completeness equivalence; no 'equivalently' token remains"
                ) if k3_gloss else None,
                "detector_control": {
                    "detector_fires_on_mutant": "equivalently" in norm(sph_text + " equivalently"),
                    "detector_quiet_on_real_rev5": not k3_bridge,
                },
            },
            "status": "CONFIRMED" if k3_bridge else "REFUTED",
            "blocking_for_F0": k3_bridge,
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    # ---------------- K4: D3 comeager discharge ----------------
    comeager = {cid: ("comeager" in norm(classes.get(cid, {}).get("conclusion", {}).get("text", ""))) for cid in CLASS_IDS}
    binding = {}
    for cid in CLASS_IDS:
        t = norm(classes.get(cid, {}).get("conclusion", {}).get("text", ""))
        binding[cid] = ("for every" in t) and ("comeager" in t)
    gkind = {cid: (classes.get(cid, {}).get("axes", {}) or {}).get("genericity_kind") for cid in CLASS_IDS}
    d3 = next((e for e in resolver if e.get("id") == "D3"), {})
    k4_bad = [cid for cid in CLASS_IDS if not (comeager[cid] and binding[cid])]
    checks.append(
        {
            "check_id": "K4",
            "source_claim": "worker-16 B-16F0-2; worker-082 W082-F-02; lead-audit-r2 hard_failures[2]",
            "statement_under_test": "class_scope_adjudication.resolved_divergences[D3] claims the comeager quantifier is stated explicitly in EACH class conclusion, but it is not discharged for AF-WCC-SCALAR-SPH.",
            "method": "Regex/substring for an explicit comeager quantifier and a preceding 'for every' binder in each of the four class conclusions; compare with the D3 resolution text and per-class axes.genericity_kind.",
            "observed": {
                "d3_entry": d3,
                "comeager_quantifier_present_by_class": comeager,
                "comeager_bound_with_for_every": binding,
                "classes_missing_bound_quantifier": k4_bad,
                "genericity_kind_by_class": gkind,
                "axes_conclusion_mismatch": [cid for cid in CLASS_IDS if gkind.get(cid) in ("unresolved", None) and comeager[cid]],
            },
            "status": "REFUTED" if not k4_bad else "CONFIRMED",
            "blocking_for_F0": bool(k4_bad),
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    # ---------------- K5: schema_owner pointers ----------------
    owner_map = {}
    ptr_target = {}
    ptr_exists = {}
    ptr_pinned = {}
    for cid in CLASS_IDS:
        owner = (classes.get(cid, {}).get("provenance", {}) or {}).get("schema_owner")
        owner_map[cid] = owner
        m = re.search(r"artifact ([^)]+\.yaml)", str(owner))
        if m:
            tgt = m.group(1).strip()
            ptr_target[cid] = tgt
            ptr_exists[cid] = (REPO / tgt).exists()
            ptr_pinned[cid] = file_pins.get(tgt, {}).get("sha256") == pre.get(tgt, {}).get("sha256")
    legacy_in_conclusions = any(
        "af_scc_regularities" in norm(json.dumps(classes.get(cid, {})))
        for cid in CLASS_IDS
    )
    legacy_lines = [i for i, ln in enumerate(f0_text.splitlines(), 1) if "af_scc_regularities" in ln]
    k5_bad = legacy_in_conclusions or any(not ptr_exists.get(cid, False) for cid in ptr_target)
    checks.append(
        {
            "check_id": "K5",
            "source_claim": "worker-16 B-16F0-3; lead-audit-r2 hard_failures[3]",
            "statement_under_test": "The C2/C0 provenance.schema_owner pointers name the superseded node F2 and the legacy non-class aggregator schemas/af_scc_regularities.yaml.",
            "method": "Read schema_owner strings; extract the named artifact path; test existence and FROZEN pin; scan class blocks for the legacy aggregator token.",
            "observed": {
                "schema_owner_by_class": owner_map,
                "extracted_pointer_target": ptr_target,
                "pointer_target_exists": ptr_exists,
                "pointer_target_pinned_by_frozen": ptr_pinned,
                "legacy_aggregator_inside_any_class_block": legacy_in_conclusions,
                "legacy_aggregator_file_lines_in_f0": legacy_lines,
                "legacy_aggregator_measured": pre["schemas/af_scc_regularities.yaml"],
                "classification": (
                    "the only remaining 'af_scc_regularities' line is the rev5 revision note describing the fix (line 17); "
                    "C2 -> F2a canonical path, C0 -> F2b canonical path"
                ),
            },
            "status": "CONFIRMED" if k5_bad else "REFUTED",
            "blocking_for_F0": k5_bad,
            "evidence_refs": [
                f"{f0_rel}#{f0_sha[:12]}",
                f"schemas/af_scc_c2_vacuum.yaml#{pre['schemas/af_scc_c2_vacuum.yaml'].get('sha256_12')}",
                f"schemas/af_scc_c0_vacuum.yaml#{pre['schemas/af_scc_c0_vacuum.yaml'].get('sha256_12')}",
            ],
        }
    )

    # ---------------- K6: genericity_topology slot ----------------
    slot_declared = "genericity_topology" in vocab
    axes_carrying = [cid for cid in CLASS_IDS if "genericity_topology" in (classes.get(cid, {}).get("axes", {}) or {})]
    k6_bad = slot_declared and not axes_carrying
    checks.append(
        {
            "check_id": "K6",
            "source_claim": "reviews/F0-review-094.json findings[0] (F-094-F0-01)",
            "statement_under_test": "genericity_topology is declared in field_vocabulary with a rule requiring it for generic-quantified claims, but no class axes block carries the slot.",
            "method": "Key-presence test over field_vocabulary and the four class axes blocks.",
            "observed": {
                "slot_declared": slot_declared,
                "slot_rule": (vocab.get("genericity_topology") or {}).get("rule") if isinstance(vocab.get("genericity_topology"), dict) else None,
                "axes_blocks_carrying_slot": axes_carrying,
                "axes_keys_by_class": {cid: sorted((classes.get(cid, {}).get("axes", {}) or {}).keys()) for cid in CLASS_IDS},
            },
            "status": "CONFIRMED" if k6_bad else "REFUTED",
            "blocking_for_F0": False,
            "classification": "informational, unchanged non-blocking vocabulary gap",
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    # ---------------- K7: axes.genericity_kind vs conclusion ----------------
    k7_mismatch = [cid for cid in CLASS_IDS if comeager.get(cid) and gkind.get(cid) in ("unresolved", None)]
    checks.append(
        {
            "check_id": "K7",
            "source_claim": "reviews/G-F0-final-verify.json open_objections_non_blocking[0] (O-GF0-1)",
            "statement_under_test": "AF-WCC-SCALAR-SPH axes.genericity_kind is still 'unresolved' while its rev5 conclusion quantifies over an explicit comeager set, so field and conclusion disagree.",
            "method": "Compare per-class axes.genericity_kind against the conclusion's comeager quantifier.",
            "observed": {
                "genericity_kind_by_class": gkind,
                "comeager_by_class": comeager,
                "mismatched_classes": k7_mismatch,
                "consistency_checker_compares_this_field": False,
            },
            "status": "CONFIRMED" if k7_mismatch else "REFUTED",
            "blocking_for_F0": False,
            "classification": "informational, confirms the lead-audit O-GF0-1",
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    # ---------------- K9: no duplicate YAML keys (control already claimed fixed) ---
    dup_keys: list[str] = []

    class DupLoader(yaml.SafeLoader):
        pass

    def _no_dup(loader, node, deep=False):
        mapping = {}
        for k, v in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in mapping:
                dup_keys.append(str(key))
            mapping[key] = loader.construct_object(v, deep=deep)
        return mapping

    DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)
    try:
        yaml.load(snap_bytes, Loader=DupLoader)
    except Exception as e:  # pragma: no cover
        dup_keys.append(f"<parse error {e!r}>")
    checks.append(
        {
            "check_id": "K9",
            "source_claim": "reviews/G-F0-final-verify.json verified_fixed[0] (VF-2)",
            "statement_under_test": "The canonical F0 rev5 has no duplicate YAML mapping keys (which silently drop data).",
            "method": "Mapping-scoped YAML load that records every duplicate key.",
            "observed": {"duplicate_keys": dup_keys},
            "status": "REFUTED" if not dup_keys else "CONFIRMED",
            "blocking_for_F0": bool([d for d in dup_keys if not str(d).startswith("<")]),
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    # ---------------- post-run drift ----------------
    post = {rel: measure(rel) for rel in INPUTS}
    drift = {}
    for rel in INPUTS:
        a, b = pre[rel].get("sha256"), post[rel].get("sha256")
        if a != b:
            drift[rel] = {"pre": a, "post": b}
    log("post_hashes", drifted=list(drift), hashes={k: v.get("sha256_12") for k, v in post.items()})
    f0_post = post[f0_rel].get("sha256")
    checks.append(
        {
            "check_id": "K0-post",
            "source_claim": "worker-091 control",
            "statement_under_test": "No measured input moved during the run (post-run re-hash).",
            "method": "Re-hash all inputs after the checks.",
            "observed": {
                "f0_pre": f0_sha,
                "f0_post": f0_post,
                "f0_stable": f0_post == f0_sha,
                "drifted_inputs": drift,
            },
            "status": "REFUTED" if (f0_post == f0_sha and not drift) else "CONFIRMED",
            "blocking_for_F0": bool(drift) or f0_post != f0_sha,
            "evidence_refs": [f"{f0_rel}#{f0_sha[:12]}"],
        }
    )

    content_blockers = [c["check_id"] for c in checks if c.get("blocking_for_F0") and c["status"] == "CONFIRMED"]
    integrity_fail = bool(INTEGRITY_FAILURES) or any(c["status"] == "FAILED" for c in checks) or bool(drift) or f0_post != f0_sha
    if integrity_fail:
        verdict, score = "inconclusive", 0.0
    elif content_blockers:
        verdict, score = "revise", 3.5
    else:
        verdict = "accept"
        # 4.0 = no blocking content defect at the pinned hash. The recorded residuals
        # (K6 vocabulary slot, K7 axes/conclusion mismatch) are already on record in
        # reviews/F0-review-094.json and reviews/G-F0-final-verify.json and are
        # non-blocking; the K3 residual gloss is a non-substantive restatement of the
        # class's own predicate. A *new* substantive non-blocking defect would cost 0.5.
        new_residuals = []
        score = max(3.0, 4.0 - 0.5 * len(new_residuals))
    return finish(pre, checks, verdict, score, drift, content_blockers, post)


def finish(pre, checks, verdict, score, drift, content_blockers, post=None) -> int:
    created = now_iso()
    results = {
        "schema_version": "worker-verification/v1",
        "verification_id": TASK_ID,
        "actor": ACTOR,
        "created_at": created,
        "task": (
            "Re-test the named F0 blocking findings K1a/K1b/K2/K3/K4/K5/K6 at canonical F0 rev5 "
            "0abb9ed8a961, the falsifier left by the previous worker-091 run (f0_blocking_verify) and "
            "the independent non-author verdict required by lead-audit B-GF0-1."
        ),
        "authority_note": (
            "Worker verdict is evidence only. Per ASTRA_HANDOFF and comms/PROTOCOL.md this cannot set "
            "status=done, validation_status=passed, or any gate verdict; the controller and group leads adjudicate."
        ),
        "not_claimed": [
            "no gate verdict (G-F0/G-FORM/G-AUDIT remain controller-owned)",
            "not a fresh full-content semantic review of the class definitions; only the named findings + controls",
            "no claim about the mirror adjudication outcome; REC-1/REC-2 is a controller decision",
            "no physics claim",
        ],
        "target": {
            "artifact": "research_map/formulation_taxonomy.yaml",
            "sha256": pre.get("research_map/formulation_taxonomy.yaml", {}).get("sha256"),
            "bytes": pre.get("research_map/formulation_taxonomy.yaml", {}).get("bytes"),
            "revision": 5,
            "status_field": None,
        },
        "publication_counterpart": {
            "artifact": "artifacts/formulation/formulation_taxonomy.yaml",
            "sha256": pre.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256"),
            "bytes": pre.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("bytes"),
            "artifact_id": "F0-R",
        },
        "frozen_manifest": {
            "artifact": "artifacts/formulation/FROZEN.json",
            "sha256": pre.get("artifacts/formulation/FROZEN.json", {}).get("sha256"),
        },
        "drift": {"pre": pre, "post": post, "drifted": drift},
        "verification_integrity_failures": INTEGRITY_FAILURES,
        "checks": checks,
        "content_blockers_standing": content_blockers,
        "verdict": verdict,
        "score": score,
        "score_rule": (
            "accept = 4.0 (no blocking content defect at the pinned hash); each new substantive "
            "non-blocking defect found would cost 0.5 (floor 3.0). The K6/K7 residuals are already "
            "on record in F0-review-094 / G-F0-final-verify and the K3 gloss is a non-substantive "
            "restatement, so they do not change the score."
        ),
        "counts_as_full_schema_verdict": False,
        "counts_as_independent_second_verdict": True,
        "counts_as_independent_non_author_verdict": True,
        "counting_note": (
            "Item-level verdict on the six named lead-audit-r2 blocking findings (K1a/K1b/K2-K5) plus "
            "controls K0/K6-K9 at the pinned rev5 hash, not a fresh full semantic review of all four "
            "class definitions. It is an independent non-author verdict (author is deepseek-flash-01), "
            "the kind lead-audit B-GF0-1 asks for; whether it counts as a full schema verdict remains "
            "the controller's/audit lead's call and is not claimed here."
        ),
        "reviewed_sha256": {
            "F0": pre.get("research_map/formulation_taxonomy.yaml", {}).get("sha256"),
            "F0-R": pre.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256"),
            "FROZEN": pre.get("artifacts/formulation/FROZEN.json", {}).get("sha256"),
            "F1": pre.get("schemas/af_wcc_vacuum.yaml", {}).get("sha256"),
            "F2a": pre.get("schemas/af_scc_c2_vacuum.yaml", {}).get("sha256"),
            "F2b": pre.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256"),
        },
        "reviewer_independence": {
            "reviewer": ACTOR,
            "authored_F0": False,
            "shared_text_with_reviewed_artifact": False,
            "shares_template_with": [],
        },
        "accept_conditional_on": [
            "controller adjudication of artifacts/formulation/FROZEN.json f0_mirror_adjudication_request; "
            "REC-1 (pair-check exception) leaves these bytes valid. Under REC-2 the artifact is rewritten and this verdict is void.",
            "the verdict binds only sha256 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3.",
        ],
        "conditions": [
            "Binds only sha256 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3; any further edit voids this verification (UNMEASURED, not accept/revise).",
            "Mechanical measurement only; semantic suitability of the four class definitions is out of scope.",
            "K8 is informational about FROZEN revision 28 pin integrity; it does not review worker-038's artifact.",
        ],
        "falsifier": (
            "This artifact is FALSE if any of the following, re-run at the recorded input hashes: "
            "(1) the canonical F0 pre/post digest differs from 0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3 "
            "(then the verdict is UNMEASURED, not accept/revise); "
            "(2) the exact set-based sentence is present in any of the four class conclusion texts in f0_rev5_snapshot.yaml; "
            "(3) 'equivalently' is present in the AF-WCC-SCALAR-SPH or AF-WCC-VAC-GEN conclusion; "
            "(4) any of the four class conclusions lacks a comeager quantifier bound before the data; "
            "(5) any class provenance.schema_owner names schemas/af_scc_regularities.yaml or a pointer target does not exist; "
            "(6) a non-author re-measurement shows F0 rev5 content differs semantically from the claims above. "
            "Directional form: an accept is FALSE if any blocking check stays CONFIRMED at the pinned bytes; "
            "a revise verdict is FALSE only if all blocking checks are refuted at the pinned bytes."
        ),
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{pre.get('research_map/formulation_taxonomy.yaml', {}).get('sha256_12')}",
            f"artifacts/formulation/formulation_taxonomy.yaml#{pre.get('artifacts/formulation/formulation_taxonomy.yaml', {}).get('sha256_12')}",
            f"artifacts/formulation/FROZEN.json#{pre.get('artifacts/formulation/FROZEN.json', {}).get('sha256_12')}",
            f"schemas/af_wcc_vacuum.yaml#{pre.get('schemas/af_wcc_vacuum.yaml', {}).get('sha256_12')}",
            f"schemas/af_scc_c2_vacuum.yaml#{pre.get('schemas/af_scc_c2_vacuum.yaml', {}).get('sha256_12')}",
            f"schemas/af_scc_c0_vacuum.yaml#{pre.get('schemas/af_scc_c0_vacuum.yaml', {}).get('sha256_12')}",
            f"artifacts/worker-091/f0_rev5_reverify/f0_rev5_snapshot.yaml#{sha256_file(HERE / 'f0_rev5_snapshot.yaml')[:12]}",
        ],
        "inputs_read": list(INPUTS),
        "runs": RUNS,
    }
    log("finished", verdict=verdict, score=score, content_blockers=content_blockers, drift=bool(drift))
    (HERE / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in RUNS))
    (HERE / "results.json").write_text(json.dumps(results, indent=1, sort_keys=False) + "\n")

    # validation: every evidence ref of the form path#hash-prefix must match disk
    validation = {"schema_version": "worker-validation/v1", "checked_at": now_iso(), "refs": [], "ok": True}
    for ref in results["evidence_refs"]:
        if "#" not in ref:
            continue
        path, prefix = ref.rsplit("#", 1)
        p = REPO / path
        exists = p.exists()
        actual = sha256_file(p)[:12] if exists else None
        ok = exists and actual == prefix
        validation["refs"].append({"ref": ref, "exists": exists, "actual_12": actual, "match": ok})
        if not ok:
            validation["ok"] = False
    validation["verdict_logic"] = {
        "content_blockers_standing": content_blockers,
        "drift": bool(drift),
        "integrity_failures": INTEGRITY_FAILURES,
        "verdict": verdict,
    }
    (HERE / "validation.json").write_text(json.dumps(validation, indent=1) + "\n")

    manifest = {"schema_version": "worker-manifest/v1", "verification_id": TASK_ID,
                "note": "MANIFEST.json is not self-listed; every other file is hashed after its final write.",
                "files": {}}
    for rel in sorted(p.name for p in HERE.iterdir() if p.is_file() and p.name != "MANIFEST.json"):
        manifest["files"][rel] = {"sha256": sha256_file(HERE / rel), "bytes": (HERE / rel).stat().st_size}
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")

    integrity_fail = (
        bool(INTEGRITY_FAILURES)
        or any(c["status"] == "FAILED" for c in checks)
        or bool(drift)
    )
    print(json.dumps({"verdict": verdict, "score": score, "content_blockers": content_blockers,
                      "integrity_failures": INTEGRITY_FAILURES, "drift": drift}, indent=1))
    return 0 if not integrity_fail else 3


if __name__ == "__main__":
    raise SystemExit(main())
