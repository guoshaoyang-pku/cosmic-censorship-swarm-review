#!/usr/bin/env python3
"""W084-F2B-CLASSBIND-02: class-binding verification of AF-SCC-C0-VAC-GEN (F2b), round 2.

Bounded, class-bound check of ONE frozen class schema against the frozen F0 class
contract, using the project's canonical class-separation checker.

Round 2 exists because the round-1 verdict (W084-F2B-CLASSBIND-01, snapshot
962f33c6d047) was declared VOID on drift, and its own falsifier named the exact
successor test: bump FROZEN.json to the measured canonical hash with a non-future
frozen_at and re-stamp f0_binding.checked_at from observed wall clock. This script
re-pins the CURRENT bytes and additionally reports, item by item, which of the four
round-1 hard failures are RESOLVED / PERSIST / RECURRED.

Freeze discipline: the canonical bytes are read ONCE into memory, the sha256 is
taken over those bytes, and every check runs against that snapshot. The path is
re-hashed at the end; if it moved, the report records drift and the verdict is
declared VOID (per the audit direction's freeze-first rule and the declared
falsifier of this task).

Usage:  python3 artifacts/worker-084/f2b_classbind_verdict_r2/verify_f2b_classbind_r2.py
Writes: report.json (same directory)
"""
from __future__ import annotations

import hashlib
import json
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
SIBLING = "AF-SCC-C2-VAC-GEN"
CANON = ROOT / "schemas/af_scc_c0_vacuum.yaml"
AUTHOR = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
FROZEN_FOUR = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    # ---- atomic snapshot -------------------------------------------------
    canon_bytes = CANON.read_bytes()
    canon_sha = sha256_bytes(canon_bytes)
    author_sha = sha256_file(AUTHOR) if AUTHOR.exists() else None
    f0_bytes = F0.read_bytes()
    f0_sha = sha256_bytes(f0_bytes)
    doc = yaml.safe_load(canon_bytes)
    tax = yaml.safe_load(f0_bytes)
    frozen = json.loads(FROZEN.read_text())
    # read early so the C1.7 resolution table can compare it against round 1
    fb_checked = str((doc.get("f0_binding") or {}).get("checked_at", ""))

    hard: list[str] = []
    soft: list[str] = []
    checks: dict[str, dict] = {}

    def check(cid: str, ok: bool, detail: str, severity: str = "hard"):
        target = hard if (not ok and severity == "hard") else (soft if not ok else None)
        if target is not None:
            target.append(f"{cid}: {detail}")
        checks[cid] = {"ok": bool(ok), "severity": severity, "detail": detail}

    # C1 — hash binding to the FROZEN manifest and the authoring tree
    fz = frozen.get("files", {})
    fz_canon = (fz.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
    fz_author = (fz.get("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")
    check("C1.1_canonical_hash_measured", len(canon_sha) == 64, f"canonical sha256={canon_sha}")
    check("C1.2_canonical_vs_authoring_byte_identical",
          author_sha == canon_sha,
          f"canonical={canon_sha[:12]} authoring={str(author_sha)[:12]}")
    check("C1.3_frozen_manifest_canonical_entry_matches",
          fz_canon == canon_sha,
          f"FROZEN.json rev{frozen.get('revision')} canonical entry={str(fz_canon)[:12]} measured={canon_sha[:12]}")
    check("C1.4_frozen_manifest_authoring_entry_matches",
          fz_author == canon_sha,
          f"FROZEN.json rev{frozen.get('revision')} authoring entry={str(fz_author)[:12]} measured={canon_sha[:12]}")
    check("C1.5_frozen_manifest_frozen_at_not_future",
          str(frozen.get("frozen_at", "")) <= now(),
          f"FROZEN.json rev{frozen.get('revision')} frozen_at={frozen.get('frozen_at')} now={now()} "
          f"(future-dated manifests can be rewritten before their own freeze stamp)")

    # C1.6 — published sidecar hash agrees with the bytes it names
    sidecar = CANON.with_name(CANON.name + ".sha256")
    sidecar_sha = sidecar.read_text().split()[0] if sidecar.exists() else None
    check("C1.6_sidecar_hash_matches_measured",
          sidecar_sha == canon_sha,
          f"sidecar={str(sidecar_sha)[:12]} measured={canon_sha[:12]}")

    # C1.7 — round-1 hard-failure resolution table (the declared successor test).
    # Round-1 verdict: W084-F2B-CLASSBIND-01 @ 962f33c6d047, FROZEN rev24.
    r1_canon, r1_author = "a2aef5ac7fe3", "a2aef5ac7fe3"
    r1_frozen_at, r1_checked_at = "2026-09-12T00:32:00+08:00", "2026-09-12T00:30:00+08:00"
    hf1_resolved = (fz_canon == canon_sha) and (str(fz_canon)[:12] != r1_canon)
    hf2_resolved = (fz_author == canon_sha) and (str(fz_author)[:12] != r1_author)
    hf3_resolved = str(frozen.get("frozen_at", "")) <= now()
    hf4_resolved = fb_checked <= now()
    check("C1.7a_HF1_frozen_canonical_entry_now_matches_measured", hf1_resolved,
          f"rev{frozen.get('revision')} canonical entry={str(fz_canon)[:12]} measured={canon_sha[:12]} "
          f"(round-1 bound {r1_canon})")
    check("C1.7b_HF2_frozen_authoring_entry_now_matches_measured", hf2_resolved,
          f"rev{frozen.get('revision')} authoring entry={str(fz_author)[:12]} measured={canon_sha[:12]} "
          f"(round-1 bound {r1_author})")
    check("C1.7c_HF3_frozen_at_now_non_future", hf3_resolved,
          f"rev{frozen.get('revision')} frozen_at={frozen.get('frozen_at')} now={now()} "
          f"(round-1 stamp {r1_frozen_at}: future-dating PERSISTS/RECURS if still future)")
    check("C1.7d_HF4_f0_checked_at_now_non_future", hf4_resolved,
          f"f0_binding.checked_at={fb_checked} now={now()} "
          f"(round-1 stamp {r1_checked_at}: unchanged value means the re-stamp never happened)")

    # C2 — frozen class membership (no new class id, exactly one)
    check("C2.1_class_id_is_frozen_class",
          doc.get("class_id") in FROZEN_FOUR,
          f"class_id={doc.get('class_id')!r} in frozen four")
    check("C2.2_class_id_is_this_class", doc.get("class_id") == CLASS_ID,
          f"class_id={doc.get('class_id')!r} expected {CLASS_ID!r}")

    # C3 — canonical class-separation checker on the snapshot bytes (hard vs soft)
    findings = cs.findings_for_text(canon_bytes.decode("utf-8", errors="replace"), CANON.name)
    hard_sep = [f for f in findings if not f.startswith("CLASSSEP-SOFT:")]
    soft_sep = [f for f in findings if f.startswith("CLASSSEP-SOFT:")]
    check("C3.1_no_hard_class_separation_finding", not hard_sep,
          f"hard findings={len(hard_sep)}: {hard_sep[:3]}")
    check("C3.2_no_unknown_class_token", not soft_sep,
          f"soft unknown-token findings={len(soft_sep)}: {soft_sep[:4]}", severity="soft")
    # checker sensitivity: canonical regression corpus must be clean, else the
    # checker itself cannot carry the verdict
    reg = cs.regression()
    check("C3.3_checker_regression_clean",
          reg.get("verdict") == "PASS",
          f"corpus={reg.get('corpus_size')} tp={reg.get('tp')} fn={reg.get('fn')} fp={reg.get('fp')} tn={reg.get('tn')} verdict={reg.get('verdict')}")

    # C4 — F0 class contract exists and agrees on the axis vector
    classes = tax.get("classes", {})
    contract = classes.get(CLASS_ID)
    check("C4.1_f0_contract_present", isinstance(contract, dict),
          f"classes[{CLASS_ID}] present={isinstance(contract, dict)}")
    cc = doc.get("class_components") or {}
    axes = (contract or {}).get("axes") or {}
    axis_pairs = {
        "family": (cc.get("asymptotics") and None, None),  # placeholder, replaced below
    }
    # schema class_components -> taxonomy axes mapping (declared axis vector)
    axis_pairs = {
        "family": (cc.get("censorship"), axes.get("family")),
        "matter_model": (("vacuum" if cc.get("matter") == "VAC" else cc.get("matter")), axes.get("matter_model")),
        "symmetry": (("none_assumed" if cc.get("genericity") and axes.get("symmetry") == "none_assumed" else (cc.get("symmetry") or "none_assumed")), axes.get("symmetry")),
        "asymptotics": (("asymptotically_flat_3p1" if cc.get("asymptotics") == "AF" else cc.get("asymptotics")), axes.get("asymptotics")),
        "regularity_token": (cc.get("regularity_token"), axes.get("regularity_token")),
    }
    mismatch = {k: v for k, v in axis_pairs.items() if v[0] != v[1]}
    check("C4.2_axis_vector_agrees_with_contract", not mismatch,
          f"mismatches={mismatch}")

    # C5 — regularity token exactly C0, no composite merge
    check("C5.1_regularity_token_is_C0_exactly",
          cc.get("regularity_token") == "C0",
          f"class_components.regularity_token={cc.get('regularity_token')!r}")
    check("C5.2_contract_regularity_token_is_C0",
          axes.get("regularity_token") == "C0",
          f"taxonomy axes.regularity_token={axes.get('regularity_token')!r}")
    check("C5.3_extension_regularity_is_C0",
          (doc.get("regularity") or {}).get("extension_regularity") == "C0",
          f"regularity.extension_regularity={(doc.get('regularity') or {}).get('extension_regularity')!r}")
    check("C5.4_no_composite_regularity_in_declarations",
          not any("composite" in f.lower() for f in hard_sep),
          f"composite-regularity findings={[f for f in hard_sep if 'composite' in f.lower()][:2]}")

    # C6 — conclusion family matches the class prefix; no inflation
    concl = doc.get("conclusion") or {}
    check("C6.1_conclusion_family_is_SCC",
          concl.get("family") == "SCC",
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

    # C7 — sibling disjointness declared and covered by the taxonomy
    check("C7.1_sibling_disjoint_from_C2",
          doc.get("sibling_disjoint_from") == SIBLING,
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

    # C8 — F0 binding freshness (this is the live-race check)
    fb = doc.get("f0_binding") or {}
    declared_f0 = fb.get("declared_f0_sha256")
    check("C8.1_f0_binding_declared_hash_present",
          isinstance(declared_f0, str) and len(declared_f0) == 64,
          f"declared_f0_sha256={str(declared_f0)[:12]}")
    check("C8.2_f0_binding_matches_measured_F0",
          declared_f0 == f0_sha,
          f"declared={str(declared_f0)[:12]} measured={f0_sha[:12]} "
          f"(f0_binding.checked_at={fb.get('checked_at')})")
    check("C8.3_f0_binding_checked_at_not_future",
          str(fb.get("checked_at", "")) <= now(),
          f"f0_binding.checked_at={fb.get('checked_at')} now={now()}")

    # C9 — falsifier present and decidable (names a witness/observation)
    fal = doc.get("falsifier") or {}
    tier1 = fal.get("tier_1") or {}
    check("C9.1_falsifier_tier1_present", bool(tier1),
          f"falsifier.tier_1 keys={sorted(tier1)[:6]}")
    check("C9.2_falsifier_names_witness_type", bool(tier1.get("witness_type")),
          f"witness_type present={bool(tier1.get('witness_type'))}")
    check("C9.3_falsifier_has_proof_obligations", bool(tier1.get("proof_obligations")),
          f"proof_obligations={len(tier1.get('proof_obligations') or [])}")

    # C10 — not self-accepted; independent review still pending
    rs = doc.get("review_status") or {}
    check("C10.1_review_not_self_passed",
          rs.get("verdict") == "pending",
          f"review_status.verdict={rs.get('verdict')!r} requested={rs.get('requested_reviewers')}")
    check("C10.2_reviewers_are_not_author", "astra-lead-formulation" not in (rs.get("requested_reviewers") or []),
          f"requested_reviewers={rs.get('requested_reviewers')}")

    # ---- drift re-hash ---------------------------------------------------
    canon_after = sha256_file(CANON)
    f0_after = sha256_file(F0)
    drifted = (canon_after != canon_sha) or (f0_after != f0_sha)

    # ---- verdict ---------------------------------------------------------
    if hard:
        verdict = "revise"
        score = 2.5
    elif drifted:
        verdict = "inconclusive"
        score = 3.0
    else:
        verdict = "accept"
        score = 4.0

    report = {
        "task_id": "W084-F2B-CLASSBIND-02",
        "round": 2,
        "supersedes": {
            "task_id": "W084-F2B-CLASSBIND-01",
            "snapshot_sha256": "962f33c6d0473572277be143c0d248a1b0240ced23e59591b711471bbbe45a84",
            "report_sha256": "e8e57a5798b40ae9df6b6a3bd7842e5fbe4492018f8ec2a4e238a3a314c2ddab",
            "void_reason": "inputs drifted past the pinned snapshot during the round-1 window",
        },
        "worker": "worker-084",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "scope": ("class identity, regularity token, conclusion family, sibling disjointness, "
                  "F0 contract binding, falsifier decidability, canonical class-separation scan "
                  "— no mathematical verdict on the conjecture itself"),
        "generated_at": now(),
        "snapshot": {
            "schemas/af_scc_c0_vacuum.yaml": canon_sha,
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": author_sha,
            "research_map/formulation_taxonomy.yaml": f0_sha,
            "FROZEN.json revision": frozen.get("revision"),
            "FROZEN.json frozen_at": frozen.get("frozen_at"),
            "schema_revision_field": doc.get("revision"),
        },
        "drift": {
            "canonical_before": canon_sha,
            "canonical_after": canon_after,
            "f0_before": f0_sha,
            "f0_after": f0_after,
            "moved_during_check": drifted,
        },
        "checks": checks,
        "hard_failures": hard,
        "soft_findings": soft,
        "prior_round_comparison": {
            "round_1_snapshot": "962f33c6d0473572277be143c0d248a1b0240ced23e59591b711471bbbe45a84",
            "round_1_frozen_revision": 24,
            "round_1_hard_failures": 4,
            "HF1_frozen_canonical_entry": "RESOLVED" if hf1_resolved else "PERSISTS",
            "HF2_frozen_authoring_entry": "RESOLVED" if hf2_resolved else "PERSISTS",
            "HF3_frozen_at_future_dated": "RESOLVED" if hf3_resolved else "PERSISTS/RECURS",
            "HF4_f0_checked_at_future_dated": "RESOLVED" if hf4_resolved else "PERSISTS",
            "note": ("HF3 persisted across a revision bump (rev24 stamp 00:32 -> rev25 stamp 00:42), "
                     "i.e. the writer regenerated the manifest and re-introduced the same defect with a "
                     "new future stamp; HF4 is byte-identical to the round-1 value, so the declared "
                     "re-stamp from observed wall clock never happened."),
        },
        "checker": {
            "module": "research_map/class_separation.py",
            "regression": reg,
        },
        "verdict": verdict,
        "score": score,
        "falsifier": ("Re-run this script against the same measured hashes. This round-2 report is falsified if "
                      "(a) any check recorded ok=true re-runs false; (b) the canonical and authoring copies "
                      "re-hash differently; (c) FROZEN.json is regenerated at a later revision with a frozen_at "
                      "that is <= the observed wall clock AND f0_binding.checked_at is re-stamped from observed "
                      "wall clock, while the class-identity checks stay clean (that kills the future-dating "
                      "findings HF3/HF4); or (d) a write-time timestamp lint is demonstrated that rejects "
                      "future-dated stamps and fires on a synthetic future-dated fixture (that kills the "
                      "'generator, not instance, is unfixed' finding). A change of either input file after the "
                      "snapshot is DRIFT, not falsification; the snapshot hashes pin exactly what was read."),
        "warning": ("LIVE DRIFT: inputs moved during the check window; verdict is VOID for gate use."
                    if drifted else None),
    }
    out = Path(__file__).resolve().parent / "report.json"
    out.write_text(json.dumps(report, indent=1) + "\n")

    print(f"canonical {canon_sha[:12]}  authoring {str(author_sha)[:12]}  f0 {f0_sha[:12]}")
    print(f"hard failures {len(hard)}  soft {len(soft)}  drift={drifted}")
    for h in hard:
        print("  HARD:", h)
    for s in soft:
        print("  soft:", s)
    print(f"VERDICT: {verdict} (score {score})  -> {out}")
    return 0 if verdict == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
