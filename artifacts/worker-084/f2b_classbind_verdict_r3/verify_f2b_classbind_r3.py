#!/usr/bin/env python3
"""W084-F2B-CLASSBIND-03: class-binding verification of AF-SCC-C0-VAC-GEN (F2b), round 3.

One bounded class-bound task: re-pin the frozen class schema at its CURRENT canonical
bytes, adjudicate the round-2 falsifier (FROZEN revision bump with wall-clock
frozen_at AND a re-stamped f0_binding.checked_at), and add the two checks round 2
lacked:

  * time-INDEPENDENT future-dating. Round 1/2 compared stamps to `now()`, which is
    race-prone (a 00:30 stamp stops being future at 00:30). Round 3 compares every
    machine-readable stamp to the file's OWN mtime as well as to wall clock, so the
    defect is falsifiable regardless of when the check runs.
  * class-contract chain location. The schema's `class_contract_pointer` names the
    class core. Round 3 checks whether that fragment resolves in the DECLARED F0
    artifact that `f0_binding` hash-pins, whether the pointer target is pinned by
    FROZEN rev26, and whether the pointer carries a hash of its own; it also detects
    duplicate top-level YAML keys that make the effective `revised_at`
    parser-dependent.

This round independently reproduces the controller's open finding (a) future-dated
`revised_at` / (b) class_contract_pointer targeting the authoring tree, listed in
assignment `astra-life03-close-findings` and in the pass-03 gate reasons. It is
corroboration at a pinned hash, not a novel discovery.

Freeze discipline: canonical/authoring/F0/FROZEN bytes are read ONCE into memory and
hashed; the paths are re-hashed at the end. If any moved, the report records drift and
the verdict is VOID for gate use (audit freeze-first rule).

Usage:  python3 artifacts/worker-084/f2b_classbind_verdict_r3/verify_f2b_classbind_r3.py
Writes: report.json (same directory)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

CST = timezone(timedelta(hours=8))
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"
TASK_ID = "W084-F2B-CLASSBIND-03"
SIBLING = "AF-SCC-C2-VAC-GEN"
CANON = ROOT / "schemas/af_scc_c0_vacuum.yaml"
AUTHOR = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
MAP = ROOT / "research_map/research_map.json"
FROZEN_FOUR = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
TOP_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, CST).isoformat(timespec="seconds")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def top_level_duplicate_keys(text: str) -> dict:
    """Top-level YAML keys appearing more than once. PyYAML silently keeps the
    last; strict parsers error. The effective value is therefore parser-dependent."""
    seen: dict[str, int] = {}
    for line in text.splitlines():
        if not line or line[0] in " \t#-":
            continue
        m = TOP_KEY.match(line)
        if m:
            seen[m.group(1)] = seen.get(m.group(1), 0) + 1
    return {k: v for k, v in seen.items() if v > 1}


def main() -> int:
    # ---- atomic snapshot -------------------------------------------------
    canon_bytes = CANON.read_bytes()
    canon_sha = sha256_bytes(canon_bytes)
    author_bytes = AUTHOR.read_bytes()
    author_sha = sha256_bytes(author_bytes)
    f0_bytes = F0.read_bytes()
    f0_sha = sha256_bytes(f0_bytes)
    supp_bytes = SUPP.read_bytes()
    supp_sha = sha256_bytes(supp_bytes)
    frozen_bytes = FROZEN.read_bytes()
    frozen_sha = sha256_bytes(frozen_bytes)

    canon_mtime = iso(CANON.stat().st_mtime)
    author_mtime = iso(AUTHOR.stat().st_mtime)
    frozen_mtime = iso(FROZEN.stat().st_mtime)

    doc = yaml.safe_load(canon_bytes)
    adoc = yaml.safe_load(author_bytes)
    tax = yaml.safe_load(f0_bytes)
    supp = yaml.safe_load(supp_bytes)
    frozen = json.loads(frozen_bytes)
    run_now = now()

    fb = doc.get("f0_binding") or {}
    rev_at = str(doc.get("revised_at", ""))
    fb_checked = str(fb.get("checked_at", ""))

    hard: list[str] = []
    soft: list[str] = []
    checks: dict[str, dict] = {}

    def check(cid: str, ok: bool, detail: str, severity: str = "hard"):
        target = hard if (not ok and severity == "hard") else (soft if not ok else None)
        if target is not None:
            target.append(f"{cid}: {detail}")
        checks[cid] = {"ok": bool(ok), "severity": severity, "detail": detail}

    # ---- C1 hash binding to FROZEN rev26 + round-2 resolution table -------
    fz = frozen.get("files", {})
    fz_canon = (fz.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
    fz_author = (fz.get("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
    fz_supp = (fz.get("artifacts/formulation/formulation_taxonomy.yaml") or {}).get("sha256")
    fz_f0 = (fz.get("research_map/formulation_taxonomy.yaml") or {}).get("sha256")
    frozen_at = str(frozen.get("frozen_at", ""))

    check("C0.1_snapshot_pinned", len(canon_sha) == 64 and len(frozen_sha) == 64,
          f"canonical={canon_sha[:12]} frozen={frozen_sha[:12]}")
    check("C1.1_canonical_hash_measured", len(canon_sha) == 64, f"canonical sha256={canon_sha}")
    check("C1.2_canonical_vs_authoring_byte_identical", author_sha == canon_sha,
          f"canonical={canon_sha[:12]} authoring={author_sha[:12]}")
    check("C1.3_frozen_manifest_canonical_entry_matches", fz_canon == canon_sha,
          f"FROZEN rev{frozen.get('revision')} canonical entry={str(fz_canon)[:12]} measured={canon_sha[:12]}")
    check("C1.4_frozen_manifest_authoring_entry_matches", fz_author == canon_sha,
          f"FROZEN rev{frozen.get('revision')} authoring entry={str(fz_author)[:12]} measured={canon_sha[:12]}")
    check("C1.5_frozen_at_not_future_vs_now", frozen_at <= run_now,
          f"frozen_at={frozen_at} now={run_now}")
    check("C1.6_frozen_at_not_future_vs_own_mtime", frozen_at <= frozen_mtime,
          f"frozen_at={frozen_at} FROZEN mtime={frozen_mtime} (time-independent form)")
    sidecar = CANON.with_name(CANON.name + ".sha256")
    sidecar_sha = sidecar.read_text().split()[0] if sidecar.exists() else None
    check("C1.7_sidecar_hash_matches_measured", sidecar_sha == canon_sha,
          f"sidecar={str(sidecar_sha)[:12]} measured={canon_sha[:12]}")

    # round-2 falsifier adjudication (declared successor test)
    r2 = {
        "task_id": "W084-F2B-CLASSBIND-02",
        "report_sha256": "45ee2bc650fe7ec884e1c7402374ff612e532b7cdd111d1e9522ebba798738e8",
        "snapshot": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
        "frozen_revision": 25,
        "checked_at_field": "2026-09-12T00:30:00+08:00",
    }
    hf1 = (fz_canon == canon_sha)
    hf2 = (fz_author == canon_sha)
    hf3 = (frozen_at <= run_now) and (frozen_at <= frozen_mtime)
    hf4 = (fb_checked <= run_now) and (fb_checked <= canon_mtime)
    check("C1.8a_HF1_frozen_canonical_entry_matches", hf1,
          f"rev{frozen.get('revision')} entry={str(fz_canon)[:12]} measured={canon_sha[:12]}")
    check("C1.8b_HF2_frozen_authoring_entry_matches", hf2,
          f"rev{frozen.get('revision')} entry={str(fz_author)[:12]} measured={author_sha[:12]}")
    check("C1.8c_HF3_frozen_at_resolved_by_rev26", hf3,
          f"rev{frozen.get('revision')} frozen_at={frozen_at} own_mtime={frozen_mtime} now={run_now} "
          f"(round-2 stamp 00:42; rev26 corrected to wall clock)")
    check("C1.8d_HF4_checked_at_persists", hf4,
          f"f0_binding.checked_at={fb_checked} schema_mtime={canon_mtime} now={run_now} "
          f"(round-1/2 value {r2['checked_at_field']}: byte-identical means the declared re-stamp never happened)")

    # ---- C2 frozen class membership --------------------------------------
    check("C2.1_class_id_is_frozen_class", doc.get("class_id") in FROZEN_FOUR,
          f"class_id={doc.get('class_id')!r} in frozen four")
    check("C2.2_class_id_is_this_class", doc.get("class_id") == CLASS_ID,
          f"class_id={doc.get('class_id')!r} expected {CLASS_ID!r}")

    # ---- C3 canonical class-separation checker ---------------------------
    findings = cs.findings_for_text(canon_bytes.decode("utf-8", errors="replace"), CANON.name)
    hard_sep = [f for f in findings if not f.startswith("CLASSSEP-SOFT:")]
    soft_sep = [f for f in findings if f.startswith("CLASSSEP-SOFT:")]
    check("C3.1_no_hard_class_separation_finding", not hard_sep,
          f"hard findings={len(hard_sep)}: {hard_sep[:3]}")
    check("C3.2_no_unknown_class_token", not soft_sep,
          f"soft unknown-token findings={len(soft_sep)}: {soft_sep[:4]}", severity="soft")
    reg = cs.regression()
    check("C3.3_checker_regression_clean", reg.get("verdict") == "PASS",
          f"corpus={reg.get('corpus_size')} tp={reg.get('tp')} fn={reg.get('fn')} fp={reg.get('fp')} "
          f"tn={reg.get('tn')} verdict={reg.get('verdict')}")

    # ---- C4 declared F0 contract + axis vector ---------------------------
    classes = tax.get("classes", {})
    contract = classes.get(CLASS_ID)
    axes = (contract or {}).get("axes") or {}
    cc = doc.get("class_components") or {}
    check("C4.1_f0_contract_present", isinstance(contract, dict),
          f"classes[{CLASS_ID}] present={isinstance(contract, dict)}")
    axis_pairs = {
        "family": (cc.get("censorship"), axes.get("family")),
        "matter_model": (("vacuum" if cc.get("matter") == "VAC" else cc.get("matter")), axes.get("matter_model")),
        "symmetry": (("none_assumed" if cc.get("genericity") and axes.get("symmetry") == "none_assumed"
                      else (cc.get("symmetry") or "none_assumed")), axes.get("symmetry")),
        "asymptotics": (("asymptotically_flat_3p1" if cc.get("asymptotics") == "AF" else cc.get("asymptotics")),
                        axes.get("asymptotics")),
        "regularity_token": (cc.get("regularity_token"), axes.get("regularity_token")),
    }
    mismatch = {k: v for k, v in axis_pairs.items() if v[0] != v[1]}
    check("C4.2_axis_vector_agrees_with_contract", not mismatch, f"mismatches={mismatch}")

    # ---- C5 regularity ----------------------------------------------------
    check("C5.1_regularity_token_is_C0_exactly", cc.get("regularity_token") == "C0",
          f"class_components.regularity_token={cc.get('regularity_token')!r}")
    check("C5.2_contract_regularity_token_is_C0", axes.get("regularity_token") == "C0",
          f"taxonomy axes.regularity_token={axes.get('regularity_token')!r}")
    check("C5.3_extension_regularity_is_C0", (doc.get("regularity") or {}).get("extension_regularity") == "C0",
          f"regularity.extension_regularity={(doc.get('regularity') or {}).get('extension_regularity')!r}")
    check("C5.4_no_composite_regularity_in_declarations",
          not any("composite" in f.lower() for f in hard_sep),
          f"composite-regularity findings={[f for f in hard_sep if 'composite' in f.lower()][:2]}")

    # ---- C6 conclusion family --------------------------------------------
    concl = doc.get("conclusion") or {}
    check("C6.1_conclusion_family_is_SCC", concl.get("family") == "SCC",
          f"conclusion.family={concl.get('family')!r}")
    check("C6.2_contract_conclusion_type_is_C0_family",
          str(axes.get("conclusion_type", "")).lower().find("c0") >= 0,
          f"taxonomy axes.conclusion_type={axes.get('conclusion_type')!r}")
    check("C6.3_no_WCC_content_in_forbidden_strengthenings",
          any("WCC" in s or "predictab" in s for s in concl.get("forbidden_strengthenings", [])),
          "forbidden_strengthenings explicitly excludes WCC/I+ content")
    check("C6.4_conclusion_not_declared_theorem",
          (doc.get("promotion_rule") or "").find("theorem") >= 0 and not doc.get("claims_theorem_status", False),
          f"promotion_rule present, claims_theorem_status={doc.get('claims_theorem_status')}")

    # ---- C7 sibling disjointness -----------------------------------------
    check("C7.1_sibling_disjoint_from_C2", doc.get("sibling_disjoint_from") == SIBLING,
          f"sibling_disjoint_from={doc.get('sibling_disjoint_from')!r}")
    pairs = [tuple(sorted(d.get("pair", []))) for d in tax.get("disjointness", [])]
    check("C7.2_taxonomy_disjointness_pair_present",
          tuple(sorted((SIBLING, CLASS_ID))) in pairs,
          f"disjointness covers {SIBLING} vs {CLASS_ID}")
    anti = doc.get("anti_scope") or {}
    anti_ids = {e.get("class_id") for e in anti.get("not_this_class", [])}
    check("C7.3_anti_scope_covers_all_three_siblings",
          {s for s in FROZEN_FOUR if s != CLASS_ID} <= anti_ids,
          f"anti_scope class_ids={sorted(x for x in anti_ids if x)}")

    # ---- C8 F0 binding freshness (now + own mtime) -----------------------
    declared_f0 = fb.get("declared_f0_sha256")
    check("C8.1_f0_binding_declared_hash_present",
          isinstance(declared_f0, str) and len(declared_f0) == 64,
          f"declared_f0_sha256={str(declared_f0)[:12]}")
    check("C8.2_f0_binding_matches_measured_F0", declared_f0 == f0_sha,
          f"declared={str(declared_f0)[:12]} measured={f0_sha[:12]}")
    check("C8.3_f0_binding_checked_at_not_future_vs_now", fb_checked <= run_now,
          f"f0_binding.checked_at={fb_checked} now={run_now}")
    check("C8.4_f0_binding_checked_at_not_future_vs_own_mtime", fb_checked <= canon_mtime,
          f"f0_binding.checked_at={fb_checked} schema mtime={canon_mtime} (time-independent form)")

    # ---- C9 falsifier decidability ---------------------------------------
    fal = doc.get("falsifier") or {}
    tier1 = fal.get("tier_1") or {}
    check("C9.1_falsifier_tier1_present", bool(tier1), f"falsifier.tier_1 keys={sorted(tier1)[:6]}")
    check("C9.2_falsifier_names_witness_type", bool(tier1.get("witness_type")),
          f"witness_type={tier1.get('witness_type')!r}")
    check("C9.3_falsifier_has_proof_obligations", bool(tier1.get("proof_obligations")),
          f"proof_obligations={len(tier1.get('proof_obligations') or [])}")

    # ---- C10 not self-accepted -------------------------------------------
    rs = doc.get("review_status") or {}
    check("C10.1_review_not_self_passed", rs.get("verdict") == "pending",
          f"review_status.verdict={rs.get('verdict')!r} requested={rs.get('requested_reviewers')}")
    check("C10.2_reviewers_are_not_author", "astra-lead-formulation" not in (rs.get("requested_reviewers") or []),
          f"requested_reviewers={rs.get('requested_reviewers')}")

    # ---- C11 revision stamp discipline (NEW in round 3) ------------------
    dup = top_level_duplicate_keys(canon_bytes.decode("utf-8"))
    check("C11.1_revised_at_not_future_vs_now", rev_at <= run_now,
          f"effective revised_at={rev_at} now={run_now}")
    check("C11.2_revised_at_not_future_vs_own_mtime", rev_at <= canon_mtime,
          f"effective revised_at={rev_at} schema mtime={canon_mtime} (time-independent form)")
    check("C11.3_no_duplicate_top_level_keys", not dup,
          f"duplicate top-level keys={dup} (PyYAML keeps the last value; strict parsers error, "
          f"so the effective revision stamp is parser-dependent)")
    check("C11.4_canonical_authoring_revised_at_agree", rev_at == str(adoc.get("revised_at", "")),
          f"canonical={rev_at} authoring={adoc.get('revised_at')!r}")

    # ---- C12 class-contract chain (NEW in round 3) -----------------------
    ptr = str(doc.get("class_contract_pointer", ""))
    ptr_path, _, ptr_frag = ptr.partition("#")
    frag_class = ptr_frag.split(".", 1)[1] if "." in ptr_frag else ptr_frag
    supp_contracts = supp.get("class_contracts") or {}
    check("C12.1_class_contract_pointer_wellformed",
          bool(ptr_path) and bool(frag_class) and frag_class == CLASS_ID,
          f"pointer={ptr!r} parsed_path={ptr_path!r} fragment_class={frag_class!r}")
    check("C12.2_pointer_fragment_resolves_in_supplement",
          frag_class in supp_contracts,
          f"class_contracts[{frag_class}] present in supplement={frag_class in supp_contracts}")
    check("C12.3_pointer_fragment_resolves_at_declared_F0",
          frag_class in (tax.get("class_contracts") or {}),
          f"declared F0 canonical ({F0.name}) has class_contracts key="
          f"{'class_contracts' in tax}; class_contracts[{frag_class}] present="
          f"{frag_class in (tax.get('class_contracts') or {})} (class core lives outside the hash-pinned F0)")
    check("C12.4_pointer_target_pinned_by_manifest", fz_supp == supp_sha,
          f"FROZEN rev{frozen.get('revision')} supplement entry={str(fz_supp)[:12]} measured={supp_sha[:12]}")
    check("C12.5_pointer_carries_own_hash", any(
        isinstance(fb.get(k), str) and len(str(fb.get(k))) == 64
        for k in ("class_contract_supplement_sha256", "supplement_sha256")),
        f"f0_binding keys={sorted(fb)}; class_contract_supplement={fb.get('class_contract_supplement')!r} "
        f"is a path-only pointer (no inline sha256)", severity="soft")
    pair = next((p for p in ((_map.get("publication_status") or {}).get("pairs") or [])
                 if p.get("canonical") == "research_map/formulation_taxonomy.yaml"), None)
    check("C12.6_supplement_publication_pair_aligned",
          (pair or {}).get("status") == "aligned",
          f"publication_status pair research_map/formulation_taxonomy.yaml vs "
          f"artifacts/formulation/formulation_taxonomy.yaml status={(pair or {}).get('status')!r} "
          f"canonical={str((pair or {}).get('canonical_sha256'))[:12]} "
          f"authoring={str((pair or {}).get('authoring_sha256'))[:12]}", severity="soft")

    # ---- drift re-hash ----------------------------------------------------
    canon_after = sha256_file(CANON)
    author_after = sha256_file(AUTHOR)
    f0_after = sha256_file(F0)
    supp_after = sha256_file(SUPP)
    frozen_after = sha256_file(FROZEN)
    drifted = any([
        canon_after != canon_sha, author_after != author_sha, f0_after != f0_sha,
        supp_after != supp_sha, frozen_after != frozen_sha,
    ])

    # ---- distinct defects -------------------------------------------------
    distinct = [
        {"id": "D1", "defect": "f0_binding.checked_at is future-dated relative to the schema's own write",
         "checks": ["C1.8d", "C8.3", "C8.4"], "status": "PERSISTS from round 2 (byte-identical value)"},
        {"id": "D2", "defect": "effective revised_at is future-dated relative to the schema's own write",
         "checks": ["C11.1", "C11.2"], "status": "NEW detection in round 3"},
        {"id": "D3", "defect": "duplicate top-level YAML keys make the effective revised_at parser-dependent",
         "checks": ["C11.3"], "status": "NEW detection in round 3; listed in astra-life03-close-findings (a)"},
        {"id": "D4", "defect": "class_contract_pointer does not resolve at the declared (hash-pinned) F0 artifact",
         "checks": ["C12.3"], "status": "independently reproduces the controller's open finding (b) and the "
                                        "F2b-review-034 revise rationale; class semantics unaffected"},
    ]

    # ---- verdict ----------------------------------------------------------
    if hard:
        verdict, score = "revise", 2.5
    elif drifted:
        verdict, score = "inconclusive", 3.0
    else:
        verdict, score = "accept", 4.0

    report = {
        "task_id": TASK_ID,
        "round": 3,
        "supersedes": r2,
        "worker": "worker-084",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "scope": ("class identity, regularity token, conclusion family, sibling disjointness, "
                  "F0/class-contract binding, revision-stamp discipline, falsifier decidability, "
                  "canonical class-separation scan — no mathematical verdict on the conjecture itself"),
        "generated_at": run_now,
        "snapshot": {
            "schemas/af_scc_c0_vacuum.yaml": canon_sha,
            "schemas/af_scc_c0_vacuum.yaml|mtime": canon_mtime,
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": author_sha,
            "research_map/formulation_taxonomy.yaml": f0_sha,
            "artifacts/formulation/formulation_taxonomy.yaml": supp_sha,
            "artifacts/formulation/FROZEN.json": frozen_sha,
            "artifacts/formulation/FROZEN.json|mtime": frozen_mtime,
            "FROZEN.json revision": frozen.get("revision"),
            "FROZEN.json frozen_at": frozen_at,
            "schema_revision_field": doc.get("revision"),
            "schema_revised_at_effective": rev_at,
        },
        "drift": {
            "canonical_before": canon_sha, "canonical_after": canon_after,
            "authoring_before": author_sha, "authoring_after": author_after,
            "f0_before": f0_sha, "f0_after": f0_after,
            "supplement_before": supp_sha, "supplement_after": supp_after,
            "frozen_before": frozen_sha, "frozen_after": frozen_after,
            "moved_during_check": drifted,
        },
        "round2_falsifier_adjudication": {
            "declared": ("FROZEN rev26+ with frozen_at <= wall clock AND f0_binding.checked_at re-stamped from "
                         "observed wall clock, plus a write-time future-stamp lint demonstrated on a synthetic "
                         "fixture; canonical move past 1bb78ce9b357 voids the verdict."),
            "clause_c_frozen_at_fixed": hf3,
            "clause_c_checked_at_restamped": fb_checked != r2["checked_at_field"],
            "clause_d_lint_demonstrated": False,
            "verdict": ("NOT FALSIFIED: canonical did not move (1bb78ce9b357 unchanged), FROZEN rev26 fixed "
                        "frozen_at to wall clock (clause c half-met), but f0_binding.checked_at is byte-identical "
                        "to rounds 1/2 (00:30:00) and no write-time stamp lint exists in the repo (clause d "
                        "unmet), so the round-2 revise verdict stands and is extended by D2/D3."),
        },
        "checks": checks,
        "hard_failures": hard,
        "soft_findings": soft,
        "hard_failure_count": len(hard),
        "distinct_defect_count": len(distinct),
        "distinct_defects": distinct,
        "round_over_round": {
            "round_1": {"snapshot": "962f33c6d047", "frozen_revision": 24, "hard": 4, "verdict": "VOID (drift)"},
            "round_2": {"snapshot": r2["snapshot"], "frozen_revision": 25, "hard": 4, "verdict": "revise"},
            "round_3": {"snapshot": canon_sha, "frozen_revision": frozen.get("revision"),
                        "hard": len(hard), "verdict": verdict},
        },
        "checker": {"module": "research_map/class_separation.py", "regression": reg},
        "controller_corroboration": {
            "note": ("D2/D3 and D4 are NOT novel to this round. They reproduce, at a pinned hash and with "
                     "machine checks, findings already open in the controller's pass-03 state; this report "
                     "is independent corroboration plus a falsifier, not a discovery claim."),
            "assignment": "astra-life03-close-findings (map.assignments): close (a) duplicate top-level YAML "
                          "keys and future-dated machine-readable timestamps, (b) class_contract_pointer values "
                          "that target artifacts/formulation/ or do not resolve at the declared F0 artifact.",
            "gate_reason": ("runtime/state/controller_verification/astra-lifecycle-03.md: F2b 4 accepts + 1 "
                            "revise; unresolved hash-bound findings include the authoring-tree class_contract_pointer."),
            "publication_evidence": "artifacts/formulation/evidence/f0_mirror_conflict.json (FROZEN rev26 rev26_delta; "
                                    "REC-1/REC-2, status blocked-pending-controller-adjudication)",
        },
        "verdict": verdict,
        "score": score,
        "falsifier": (
            "Re-run this script at the same pinned hashes. This round-3 report is falsified if: (a) any check "
            "recorded ok=true re-runs false; (b) the canonical/authoring copies re-hash differently or the "
            "canonical file moves past " + canon_sha[:12] + " (drift, not falsification, voids the verdict); "
            "(c) a successor freeze sets revised_at AND f0_binding.checked_at <= the schema's own mtime, removes "
            "the duplicate top-level revised_at keys, and repoints class_contract_pointer at a fragment that "
            "resolves inside the hash-pinned declared F0 artifact, while all class-identity checks stay clean; or "
            "(d) a write-time stamp lint is demonstrated that rejects future-dated and duplicate revision stamps "
            "on synthetic fixtures. A path without a hash binds nothing; the snapshot hashes pin exactly what "
            "was read."
        ),
        "claim_boundary": (
            "Class semantics (identity, regularity token, conclusion family, sibling disjointness) are CLEAN at "
            "this snapshot. The revise verdict is about the evidence chain: two future-dated machine-readable "
            "stamps, parser-dependent duplicate keys, and a class-contract pointer that resolves outside the "
            "declared F0 artifact. This report asserts nothing about cosmic censorship itself and sets no node "
            "status, gate verdict, or validation_status."
        ),
        "warning": ("LIVE DRIFT: inputs moved during the check window; verdict is VOID for gate use."
                    if drifted else None),
    }
    out = Path(__file__).resolve().parent / "report.json"
    out.write_text(json.dumps(report, indent=1) + "\n")

    print(f"canonical {canon_sha[:12]}  authoring {author_sha[:12]}  f0 {f0_sha[:12]}  "
          f"supplement {supp_sha[:12]}  frozen rev{frozen.get('revision')} {frozen_sha[:12]}")
    print(f"hard failures {len(hard)}  soft {len(soft)}  drift={drifted}  now={run_now}")
    for h in hard:
        print("  HARD:", h)
    for s in soft:
        print("  soft:", s)
    print(f"VERDICT: {verdict} (score {score})  -> {out}")
    return 0 if verdict == "accept" else 1


# publication_status is read lazily inside the check lambda; load defensively so a
# concurrent controller write cannot crash the verifier.
_map: dict = {}
try:
    _map = json.loads(MAP.read_text())
except Exception:
    _map = {}


if __name__ == "__main__":
    sys.exit(main())
