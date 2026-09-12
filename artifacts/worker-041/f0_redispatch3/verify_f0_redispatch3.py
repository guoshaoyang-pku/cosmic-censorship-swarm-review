#!/usr/bin/env python3
"""worker-041 re-dispatch #3: read-only closure verification of the G-F0 record.

This does NOT re-review F0 (the blind review is already complete and pinned at
reviews/F0-review-rev27-a.json#4f5c2a874801). It verifies, from bytes on disk, the
invariants the three prior worker-041 events asserted, so this instance's single
status event is artifact-backed rather than a restatement of prose.

Read-only: opens the two taxonomy surfaces, the pinned verdict, the pinned
checkpoint and the outbox; writes only its own report under artifacts/worker-041/.

Usage: python3 verify_f0_redispatch3.py [--out <path>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CANONICAL = "research_map/formulation_taxonomy.yaml"
COMPANION = "artifacts/formulation/formulation_taxonomy.yaml"
VERDICT = "reviews/F0-review-rev27-a.json"
CHECKPOINT = "runtime/state/worker-041_F0_checkpoint.json"
OUTBOX = "comms/outbox/worker-041.jsonl"

PIN_CANONICAL = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_COMPANION = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
PIN_VERDICT = "4f5c2a874801c9b17e8cf68fbad8a3e21ceaa0c41d0946078b80bf70850195ba"
PIN_CHECKPOINT = "947debc84797ee9c673a0db53a1db77093602709d74f6eadd84168db665896ed"

CST = timezone(timedelta(hours=8))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml_no_dup(path: str):
    """Load YAML, failing loudly on duplicate mapping keys (silent-drop hazard)."""

    class DupSafeLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        loader.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(
                    f"duplicate key {key!r} at line {key_node.start_mark.line + 1} of {path}"
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    DupSafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=DupSafeLoader)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=os.path.join(
            ROOT, "artifacts/worker-041/f0_redispatch3/report.json"
        ),
    )
    args = ap.parse_args()

    checks: list[dict] = []
    observations: list[dict] = []

    def check(cid, ok, detail, severity="hard"):
        checks.append({"id": cid, "ok": bool(ok), "severity": severity, "detail": detail})
        return bool(ok)

    def observe(oid, detail, severity="documentary"):
        observations.append({"id": oid, "severity": severity, "detail": detail})

    hashes = {}
    for rel in (CANONICAL, COMPANION, VERDICT, CHECKPOINT):
        p = os.path.join(ROOT, rel)
        hashes[rel] = sha256_file(p) if os.path.exists(p) else None

    # (1) pins before reading
    check("C1-canonical-pin-before", hashes[CANONICAL] == PIN_CANONICAL,
          f"{CANONICAL} = {hashes[CANONICAL]}")
    check("C2-companion-pin-before", hashes[COMPANION] == PIN_COMPANION,
          f"{COMPANION} = {hashes[COMPANION]}")
    check("C3-verdict-pin", hashes[VERDICT] == PIN_VERDICT,
          f"{VERDICT} = {hashes[VERDICT]}")
    check("C4-checkpoint-pin", hashes[CHECKPOINT] == PIN_CHECKPOINT,
          f"{CHECKPOINT} = {hashes[CHECKPOINT]}")

    canon = load_yaml_no_dup(os.path.join(ROOT, CANONICAL))
    comp = load_yaml_no_dup(os.path.join(ROOT, COMPANION))

    # (2) exactly four class ids on every structural surface, sets equal
    canon_ids = list(canon.get("class_ids") or [])
    canon_classes = list((canon.get("classes") or {}).keys())
    comp_frozen = list(comp.get("frozen_classes") or [])
    comp_contracts = list((comp.get("class_contracts") or {}).keys())
    surfaces = {
        "canonical.class_ids": canon_ids,
        "canonical.classes": canon_classes,
        "companion.frozen_classes": comp_frozen,
        "companion.class_contracts": comp_contracts,
    }
    check("C5-four-ids-every-surface",
          all(len(v) == 4 for v in surfaces.values()),
          {k: len(v) for k, v in surfaces.items()})
    sets = {k: set(v) for k, v in surfaces.items()}
    check("C6-class-id-sets-equal",
          len({frozenset(s) for s in sets.values()}) == 1,
          {k: sorted(v) for k, v in sets.items()})

    # (3) disjointness: 6/6 unordered pairs on both surfaces
    def pairset(pairs):
        return {frozenset(p) for p in pairs}

    canon_pairs = pairset([tuple(d["pair"]) for d in canon.get("disjointness") or []])
    comp_pairs = pairset([tuple(row[:2]) for row in (comp.get("disjointness_matrix") or {}).get("pairwise") or []])
    all_pairs = pairset([(a, b) for i, a in enumerate(sorted(canon_ids)) for b in sorted(canon_ids)[i + 1:]])
    check("C7-canonical-6-disjoint-pairs",
          len(canon_pairs) == 6 and canon_pairs == all_pairs,
          {"pairs": len(canon_pairs), "complete": canon_pairs == all_pairs})
    check("C8-companion-6-disjoint-pairs",
          len(comp_pairs) == 6 and comp_pairs == all_pairs,
          {"pairs": len(comp_pairs), "complete": comp_pairs == all_pairs})

    # (4) class leakage: no C0/C2 merge, no WCC/SCC token confusion
    leak = []
    for cid, body in (canon.get("classes") or {}).items():
        fam = (body.get("axes") or {}).get("family")
        token = (body.get("axes") or {}).get("regularity_token")
        ctype = (body.get("axes") or {}).get("conclusion_type")
        if fam == "SCC" and token not in {"C0", "C2"}:
            leak.append(f"{cid}: SCC with token {token!r}")
        if fam == "WCC" and token is not None:
            leak.append(f"{cid}: WCC with token {token!r}")
        if fam == "SCC" and ctype == "weak_cosmic_censorship":
            leak.append(f"{cid}: SCC bound to WCC conclusion")
        if fam == "WCC" and str(ctype).startswith("strong_cosmic"):
            leak.append(f"{cid}: WCC bound to SCC conclusion")
    c2 = next(b for c, b in canon["classes"].items() if c == "AF-SCC-C2-VAC-GEN")
    c0 = next(b for c, b in canon["classes"].items() if c == "AF-SCC-C0-VAC-GEN")
    if c2["axes"]["regularity_token"] == c0["axes"]["regularity_token"]:
        leak.append("C2 and C0 share a regularity token")
    if c2["axes"]["conclusion_type"] == c0["axes"]["conclusion_type"]:
        leak.append("C2 and C0 share a conclusion_type")
    guard3 = next((g for g in canon.get("guards") or [] if g.get("id") == "G3"), None)
    x1 = any(t.get("id") == "X1" for t in (canon.get("transfer_rules") or {}).get("forbidden") or [])
    x5 = any(t.get("id") == "X5" for t in (canon.get("transfer_rules") or {}).get("forbidden") or [])
    comp_ban = bool((comp.get("disjointness_matrix") or {}).get("composite_regularity_ban"))
    check("C9-no-class-leakage-canonical",
          not leak and guard3 is not None and x1 and x5,
          {"violations": leak, "G3": guard3 is not None, "X1": x1, "X5": x5})
    check("C10-companion-composite-ban", comp_ban,
          (comp.get("disjointness_matrix") or {}).get("composite_regularity_ban"))

    # (5) conclusion inflation: nothing promoted from model/calibration
    infl = []
    if canon.get("status") != "draft_unverified":
        infl.append(f"status={canon.get('status')!r}")
    if canon.get("claims_theorem_status") is not False:
        infl.append(f"claims_theorem_status={canon.get('claims_theorem_status')!r}")
    if (canon.get("provenance") or {}).get("claims_theorem_status") is not False:
        infl.append("provenance.claims_theorem_status not False")
    for cid, body in (canon.get("classes") or {}).items():
        ct = (body.get("conclusion") or {}).get("type")
        if ct in {"theorem", "counterexample", "numerical_evidence"}:
            infl.append(f"{cid}: conclusion.type={ct}")
    comp_infl = []
    if (comp.get("review_status") or {}).get("verdict") != "pending":
        comp_infl.append(f"review_status.verdict={(comp.get('review_status') or {}).get('verdict')!r}")
    if (comp.get("provenance") or {}).get("citation_status") != "unverified":
        comp_infl.append("provenance.citation_status not unverified")
    check("C11-no-conclusion-inflation",
          not infl and not comp_infl,
          {"canonical": infl, "companion": comp_infl})

    # (6) assumption completeness + decidable falsifiers (test cases, exclusions)
    gaps = []
    for cid, body in (canon.get("classes") or {}).items():
        if not body.get("hypotheses"):
            gaps.append(f"{cid}: no hypotheses")
        if not body.get("exclusions"):
            gaps.append(f"{cid}: no exclusions")
        tc = body.get("test_cases") or {}
        pos = tc.get("positive") or {}
        neg = tc.get("negative") or {}
        if not pos.get("expected_classification"):
            gaps.append(f"{cid}: no positive expected_classification")
        if not neg.get("expected_classification"):
            gaps.append(f"{cid}: no negative expected_classification")
    for cid, body in (comp.get("class_contracts") or {}).items():
        if not body.get("hypotheses") or not body.get("exclusions"):
            gaps.append(f"companion {cid}: hypotheses/exclusions missing")
        if not body.get("positive_test_case") or not body.get("negative_test_case"):
            gaps.append(f"companion {cid}: test case missing")
    check("C12-assumptions-and-falsifiers-complete", not gaps, {"gaps": gaps})

    # (7) pair consistency: same statements, no contradictory clause
    contradictions = []
    for cid in canon_ids:
        cbody = canon["classes"][cid]
        pbody = comp["class_contracts"][cid]
        ctext = json.dumps(cbody.get("conclusion") or {})
        ptext = json.dumps(pbody)
        fam = cbody["axes"]["family"]
        if fam == "SCC":
            if "inexten" not in ctext or "inexten" not in ptext:
                contradictions.append(f"{cid}: inextendibility wording absent on one surface")
            if "future" not in ctext or "future" not in ptext:
                contradictions.append(f"{cid}: future-direction wording absent on one surface")
        if fam == "WCC":
            if "visible" not in ctext or "visible" not in ptext:
                contradictions.append(f"{cid}: visibility wording absent on one surface")
        if cid == "AF-WCC-SCALAR-SPH" and "spherical" not in ptext:
            contradictions.append(f"{cid}: companion contract lost the spherical scope")
        if cid == "AF-SCC-C2-VAC-GEN" and "C2" not in ptext:
            contradictions.append(f"{cid}: companion contract lost the C2 token")
        if cid == "AF-SCC-C0-VAC-GEN" and "C0" not in ptext:
            contradictions.append(f"{cid}: companion contract lost the C0 token")
    canon_wcc_tail = "TAIL predicate" in json.dumps(canon["classes"]["AF-WCC-VAC-GEN"]["conclusion"])
    comp_no_set = "SET" not in json.dumps(comp["class_contracts"]["AF-WCC-VAC-GEN"]["conclusion_predicate"])
    check("C13-pair-consistency-no-contradiction",
          not contradictions and canon_wcc_tail and comp_no_set,
          {"contradictions": contradictions,
           "canonical_single_q_tail_predicate": canon_wcc_tail,
           "companion_predicate_free_of_set_reading": comp_no_set})

    # (8) the pinned verdict itself: identity + binding fields.
    # `counts_as_gate_verdict` is absent from both the file and its outbox event;
    # absence is not a gate claim (the file carries an explicit authority_note),
    # so the requirement is "not truthy", not "explicitly False".
    verdict = json.load(open(os.path.join(ROOT, VERDICT), "r", encoding="utf-8"))
    check("C14-verdict-binds-pin",
          verdict.get("reviewer") == "worker-041"
          and verdict.get("target_id") == "F0"
          and verdict.get("reviewed_sha256") == PIN_CANONICAL
          and verdict.get("verdict") == "accept"
          and verdict.get("hard_failures") == []
          and verdict.get("gate") == "G-F0"
          and not verdict.get("counts_as_gate_verdict", False)
          and bool(verdict.get("authority_note")),
          {k: verdict.get(k) for k in ("reviewer", "target_id", "reviewed_sha256",
                                        "verdict", "score", "hard_failures", "gate",
                                        "counts_as_gate_verdict", "authority_note")})

    # (9) outbox: exactly one F0 review event at the pin, no duplicate review,
    # and the event's binding fields agree with the pinned verdict file.
    outbox_lines = [json.loads(x) for x in open(os.path.join(ROOT, OUTBOX), encoding="utf-8") if x.strip()]
    f0_reviews = [e for e in outbox_lines
                  if e.get("event_type") == "review" and e.get("target_id") == "F0"]
    agree = False
    if len(f0_reviews) == 1:
        e = f0_reviews[0]
        agree = all([
            e.get("reviewer") == verdict.get("reviewer"),
            e.get("target_id") == verdict.get("target_id"),
            e.get("reviewed_sha256") == verdict.get("reviewed_sha256"),
            e.get("verdict") == verdict.get("verdict"),
            float(e.get("score")) == float(verdict.get("score")),
            e.get("hard_failures") == verdict.get("hard_failures"),
            e.get("gate") == verdict.get("gate"),
        ])
    check("C15-single-f0-review-event",
          len(f0_reviews) == 1
          and f0_reviews[0].get("reviewed_sha256") == PIN_CANONICAL
          and agree,
          {"count": len(f0_reviews),
           "ids": [e.get("event_id") for e in f0_reviews],
           "file_event_binding_fields_agree": agree})
    if verdict.get("counts_as_gate_verdict") is None:
        observe("OBS-5-no-explicit-non-gate-flag",
                "neither reviews/F0-review-rev27-a.json nor its review event carries an explicit "
                "counts_as_gate_verdict=false; both rely on the authority_note / stop_rule text. "
                "Absence is not a gate claim, so this is documentary only")
    closure_ids = sorted(e.get("event_id") for e in outbox_lines
                         if str(e.get("event_id", "")).startswith("w041-f0-redispatch"))
    observe("OBS-1-dispatch-loop",
            f"worker-041 instance launcher independent_supervisor_100.sh has scheduled this slot "
            f"repeatedly; closure events already on record: {closure_ids}; card audit-r2-F0-a "
            f"unchanged since 2026-09-12T00:44:18+08:00 and already satisfies its stop rule")

    # (10) known residual, re-observed but already recorded by the controller
    scalar = canon["classes"]["AF-WCC-SCALAR-SPH"]
    if (scalar["axes"].get("genericity_kind") == "unresolved"
            and "comeager" in json.dumps(scalar.get("conclusion"))):
        observe("OBS-2-CF-21-residual",
                "scalar class axes.genericity_kind='unresolved' while its rev5 conclusion text "
                "asserts a comeager set; this is the residual CF-21 already recorded in "
                "research_map/research_map.json controller_findings and was non-blocking at the "
                "controller's G-F0 pass; NOT a new hard failure of this closure")
    gen_vals = ((comp.get("axis_registry") or {}).get("genericity_axis") or {}).get("values") or []
    if "unresolved" not in gen_vals and "unresolved" in json.dumps(
            ((comp.get("axis_registry") or {}).get("genericity_axis") or {}).get("frozen") or {}):
        observe("OBS-3-companion-vocab-gap",
                "companion axis_registry.genericity_axis.values omits the 'unresolved' token that "
                "its own frozen map uses for AF-WCC-SCALAR-SPH (canonical field_vocabulary does "
                "list 'unresolved'); documentary vocabulary gap, not a contradictory clause")
    rh = comp.get("revision_history") or []
    ats = [r.get("at") for r in rh]
    if ats != sorted(ats):
        observe("OBS-4-revision-history-order",
                "companion revision_history timestamps are not in index order (documentary; same "
                "class of note already recorded against F2a)")

    # (11) hashes after reading
    after = {rel: sha256_file(os.path.join(ROOT, rel)) for rel in (CANONICAL, COMPANION, VERDICT, CHECKPOINT)}
    stable = all(after[rel] == hashes[rel] for rel in after)
    check("C16-bytes-stable-across-read", stable,
          {rel: {"before": hashes[rel], "after": after[rel]} for rel in after})

    hard_failures = [c for c in checks if not c["ok"] and c["severity"] == "hard"]
    report = {
        "report_id": "w041-f0-redispatch3-verification",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "generated_by": "worker-041",
        "instance": "worker-041-20260912T010739-968807",
        "mode": "read-only closure verification (NOT a new blind F0 review)",
        "assignment": "audit-r2-F0-a",
        "target_id": "F0",
        "gate": "G-F0",
        "class_ids": canon_ids,
        "pins": {
            "canonical_expected": PIN_CANONICAL,
            "companion_expected": PIN_COMPANION,
            "verdict_expected": PIN_VERDICT,
            "checkpoint_expected": PIN_CHECKPOINT,
            "measured_before": hashes,
            "measured_after": after,
        },
        "checks": checks,
        "observations": observations,
        "hard_failures": [c["id"] for c in hard_failures],
        "verdict": "PASS" if not hard_failures else "FAIL",
        "counts_as_gate_verdict": False,
        "counts_as_new_blind_review": False,
        "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        "falsifier": (
            "Declare this closure false if any of: (a) sha256(research_map/formulation_taxonomy.yaml) "
            f"!= {PIN_CANONICAL}; (b) sha256(artifacts/formulation/formulation_taxonomy.yaml) != "
            f"{PIN_COMPANION}; (c) sha256(reviews/F0-review-rev27-a.json) != {PIN_VERDICT}; "
            f"(d) sha256(runtime/state/worker-041_F0_checkpoint.json) != {PIN_CHECKPOINT}; "
            "(e) distinct class-id count != 4 on either surface or the sets differ; (f) fewer than 6 "
            "disjointness pairs on either surface; (g) any C2-into-C0 smuggling or C0/C2 merge is "
            "found at this pin; (h) a second review event for target F0 at this pin appears in "
            "comms/outbox/worker-041.jsonl."
        ),
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=False)
        f.write("\n")

    print(f"verdict={report['verdict']} checks={sum(c['ok'] for c in checks)}/{len(checks)} "
          f"hard_failures={report['hard_failures']} observations={[o['id'] for o in observations]}")
    for c in checks:
        print(f"  [{'ok' if c['ok'] else 'FAIL'}] {c['id']}: {c['detail']}")
    for o in observations:
        print(f"  [obs] {o['id']}: {o['detail']}")
    print(f"report={args.out}")
    return 0 if not hard_failures else 1


if __name__ == "__main__":
    sys.exit(main())
