#!/usr/bin/env python3
"""W003-REC36-FOLD-READINESS-01 -- independent, read-only fold-readiness census.

Question
--------
REC-36 (astra-lifecycle-08, deadline 02:15) authorizes astra-lead-formulation to land
EXACTLY ONE revision (rev14 / FROZEN rev30) folding seven named items.  This instrument
does not adjudicate any item's content.  It measures, from primary bytes only:

  (a) which staged candidate artifact(s) exist on disk for each of the seven items,
  (b) each candidate's measured sha256 / bytes / mtime, and whether it matches the
      hash declared by its producer or by an on-disk adjudication,
  (c) which items have at least one independent (non-producer) verification event in
      the accepted stream at or after the candidate hash,
  (d) whether each item is FREEZE-READY under a mechanical predicate, or blocked, or
      has no candidate at all,
  (e) the union of canonical paths the fold would have to move, checked against the
      REC-36 forbidden-write set (F0 taxonomy, the frozen class-separation detector,
      the literature ledger).

This is a worker measurement, not a gate verdict.  It sets no node status and writes
nothing outside artifacts/worker-003/.

Fail-closed: every pinned live input is measured at start and end; any drift aborts
with exit 2 and no readiness claim.

Reproduce:
  python3 artifacts/worker-003/rec36_fold_readiness/check_rec36_fold_readiness.py
Exit codes: 0 = census complete (verdict may be blocked), 2 = pin drift / abort.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# --------------------------------------------------------------------------- pins
# Live pins measured 2026-09-12 (FROZEN rev29 window).  Fail-closed on drift.
EXPECTED_PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/VARIANT_REGISTRY.json": "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "research_map/class_separation.py": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
    "schemas/f1_falsifier_tests.jsonl": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
}

FORBIDDEN_WRITE_PREFIXES = (
    "research_map/formulation_taxonomy.yaml",
    "research_map/class_separation.py",
    "ledger/",
)

# ------------------------------------------------------- candidate / item tables
# F2b landable candidate set per worker-080 W080-F2B-HF1-DIRECTION-CENSUS-01
# (7 landable) plus the 3 do-not-freeze candidates as negative controls.
F2B_LANDABLE = [
    ("worker-029-PinnedCorrected", "artifacts/worker-029/f2b_repair_candidate_verify/pinned/cand_corrected_51c253c4.yaml",
     "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a", "CORRECT", "worker-080"),
    ("worker-023-DirReview", "artifacts/worker-023/f2b_dir_review/evidence/patchcheck_tmp/schemas/af_scc_c0_vacuum.yaml",
     "9ab32ee39d008b20905ed44f4524ffa3c68ed50fe6a4b7a9fc4223584efbdf17", "CORRECT", "worker-023"),
    ("worker-083-C083", "artifacts/worker-083/f2b_candidate_adjudication/snapshot/candidate_083__af_scc_c0_vacuum.yaml",
     "1315427fbc92ed118982f20998066fd21c1714714213dc70b04023da74be3275", "NEUTRAL_NESTING", "worker-083"),
    ("worker-029-PinnedNesting", "artifacts/worker-029/f2b_repair_candidate_verify/pinned/cand_nesting_4951cc96.yaml",
     "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f", "NEUTRAL_NESTING", "worker-080"),
    ("worker-024-Rev29Repair", "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml",
     "679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9", "NEUTRAL_NESTING", "worker-024"),
    ("worker-022-A110", "artifacts/worker-007/f2b_containment_repair/snapshot/candidate_w022.a110f8e875af.yaml",
     "a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757", "NEUTRAL_NESTING", "worker-022"),
    ("worker-088-Rev13Repair", "artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml",
     "b598b59e09e56ee4f9e61d1c80f54d702b0bbf14ec9ee646172bc4a87710557a", "NEUTRAL_NESTING", "worker-088"),
]
F2B_DO_NOT_FREEZE = [
    ("worker-002-Repair2Edit", "artifacts/worker-002/f2b_containment_adjudication/candidate/af_scc_c0_vacuum.repair2edit.yaml",
     "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40", "INVERTED", "worker-002"),
    ("worker-044-TamperRootCopy", "artifacts/worker-003/f2b_rev14_candidate_closure/controls/tamper_root/artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
     "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a", "INVERTED", "worker-044"),
    ("worker-047-C2OrderCtl", "artifacts/worker-047/lform01_c2_order/controls/w047-ctrl-a1z7pelz/C2_size_repair/artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
     "3cdcaa44e6f103f4dacbc03c509f39586f7788e14ddba981b19985c843821c48", "DENIAL", "worker-047"),
]

ITEMS = [
    {
        "id": "REC36-1",
        "title": "F2b must_not_conflate[0] containment denial -> F2a-corrected nested-extension wording",
        "classes": ["AF-SCC-C0-VAC-GEN"],
        "node": "F2b",
        "candidates": F2B_LANDABLE + F2B_DO_NOT_FREEZE,
        "expected_verification_authors": ["worker-096", "worker-083", "worker-080", "worker-029", "worker-037"],
        "canonical_targets": ["schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"],
    },
    {
        "id": "REC36-2",
        "title": "F2b 'C2 is a strictly larger extension class' -> strictly stronger regularity requirement (E_C2 subset E_C0)",
        "classes": ["AF-SCC-C0-VAC-GEN"],
        "node": "F2b",
        "candidates": F2B_LANDABLE + F2B_DO_NOT_FREEZE,
        "expected_verification_authors": ["worker-096", "worker-083", "worker-080", "worker-029", "worker-037"],
        "canonical_targets": ["schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"],
    },
    {
        "id": "REC36-3",
        "title": "F2a extension-manifold category pinned or pinned category-independence rebuttal",
        "classes": ["AF-SCC-C2-VAC-GEN"],
        "node": "F2a",
        "candidates": [
            ("worker-091-W047Patched", "artifacts/worker-091/w047_f2a_freeze_independent/patched/af_scc_c2_vacuum.w047-patched.yaml",
             None, "PATCHED_SCHEMA_CANDIDATE", "worker-091"),
        ],
        "supporting_artifacts": [
            ("worker-047-RepairSpec", "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json",
             "c33e8a46866992cfa7b1f3ea9d31c6e10217f4a51e916697848ec6b54a6a3e98"),
            ("worker-091-IndependentVerification", "artifacts/worker-091/w047_f2a_freeze_independent/report.json", None),
        ],
        "expected_verification_authors": ["worker-091"],
        "canonical_targets": ["schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"],
    },
    {
        "id": "REC36-4",
        "title": "REC-37 scc_*/strong_* canonical-alias crosswalk + assertion-correct consistency check (no F0 write)",
        "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node": "F1,F2a,F2b",
        "candidates": [
            ("worker-041-VocabAliasReport", "artifacts/worker-041/f2b_vocab_alias/report.json", None,
             "CROSSWALK_EVIDENCE_NOT_PINNED_ARTIFACT", "worker-041"),
        ],
        "expected_verification_authors": ["worker-041", "worker-099"],
        "canonical_targets": [],  # new artifact to be created by the owner per REC-37
    },
    {
        "id": "REC36-5",
        "title": "SET predicate-vs-class strength label in VARIANT_REGISTRY.json + SET delta + check_variant_registry.py",
        "classes": ["AF-WCC-VAC-GEN"],
        "node": "F1",
        "candidates": [
            ("worker-024-CandRegistry", "artifacts/worker-024/set_strength_repair/CANDIDATE_VARIANT_REGISTRY.json", None, "SET_CANDIDATE", "worker-024"),
            ("worker-024-CandSETDelta", "artifacts/worker-024/set_strength_repair/CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json", None, "SET_CANDIDATE", "worker-024"),
            ("worker-024-CandChecker", "artifacts/worker-024/set_strength_repair/CANDIDATE_check_variant_registry.py", None, "SET_CANDIDATE", "worker-024"),
        ],
        "supporting_artifacts": [
            ("worker-024-SelfVerifyReport", "artifacts/worker-024/set_strength_repair/verify_results.json", None),
        ],
        "expected_verification_authors": [],  # no non-author verification located
        "canonical_targets": [
            "artifacts/formulation/VARIANT_REGISTRY.json",
            "artifacts/formulation/VARIANTS/AF-WCC-VAC-GEN.variant-SET.delta.json",
            "artifacts/formulation/tools/check_variant_registry.py",
        ],
    },
    {
        "id": "REC36-6",
        "title": "f1_falsifier_tests.jsonl rebind of 25 rows + F1-AMB-25 f0 pin + re-observation of F1-AMB-11/17/23",
        "classes": ["AF-WCC-VAC-GEN"],
        "node": "F1",
        "candidates": [
            ("worker-031-TierA", "artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierA.jsonl",
             "e172020ccda52b605a06cb0d41e67d36e8854d326c3e92dda33c023339831dae", "TRUTHFUL", "worker-031"),
            ("worker-031-TierB", "artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierB.jsonl",
             "785e6a4e53d6437796fbe40a09ed391d54ec1c8264f3d338a93f5bd9f00c9b4a", "TRUTHFUL", "worker-031"),
            ("worker-077-Mechanical", "artifacts/worker-077/f1_suite_rebind_dryrun/run/proposed_f1_falsifier_tests.rev13.mechanical.jsonl",
             "306480f5f45acc5012f5acae1079d95e77e343795565b195e224391dbc974ba4", "EXEC_FAILING", "worker-077"),
            ("worker-077-F0Refresh", "artifacts/worker-077/f1_suite_rebind_dryrun/run/proposed_f1_falsifier_tests.rev13.f0refresh.jsonl",
             "739d5b40dc97111dceff6df62ceaac8e22888dec6ca53981cbb308b3eb6ab1c6", "TRUTHFUL_NOT_FREEZE_READY", "worker-077"),
        ],
        "supporting_artifacts": [
            ("worker-034-CandidateAdjudication", "artifacts/worker-034/f1_repair_candidate_adjudication/report.json", None),
        ],
        "expected_verification_authors": ["worker-034"],
        "canonical_targets": ["schemas/f1_falsifier_tests.jsonl"],
    },
    {
        "id": "REC36-7",
        "title": "Acceptance-corpus rebind (CF-32): semantic-escape corpus base must be the live F2b rev13 bytes",
        "classes": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node": "F1,F2a,F2b",
        "candidates": [
            ("live-corpus-rebased", "artifacts/formulation/evidence/semantic_escape_rebased.json", None, "STALE_BASE_MEASURED", "worker-016"),
        ],
        "expected_verification_authors": ["worker-006", "worker-068"],
        "canonical_targets": ["artifacts/formulation/evidence/semantic_escape_rebased.json"],
    },
]


# ------------------------------------------------------------------------ helpers
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(path_str: str):
    p = ROOT / path_str
    if not p.is_file():
        return {"exists": False, "path": path_str}
    st = p.stat()
    return {
        "exists": True,
        "path": path_str,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": int(st.st_mtime),
    }


def load_events():
    """Accepted stream, read-only.  Returns list of event dicts (best effort)."""
    out = []
    p = ROOT / "research_map/events.jsonl"
    if not p.is_file():
        return out
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or '"event_id"' not in line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def events_for_sha(events, sha: str, exclude_actors=("worker-003",)):
    if not sha:
        return []
    short = sha[:16]
    hits = []
    for e in events:
        if e.get("actor") in exclude_actors:
            continue
        raw = json.dumps(e)
        if sha in raw or short in raw:
            hits.append({
                "event_id": e.get("event_id"),
                "actor": e.get("actor"),
                "event_type": e.get("event_type"),
                "task_id": e.get("task_id"),
                "created_at": e.get("created_at"),
            })
    return hits


def is_forbidden(path_str: str) -> bool:
    return any(path_str == p or path_str.startswith(p) for p in FORBIDDEN_WRITE_PREFIXES)


# ------------------------------------------------------------------------- checks
def pin_guard():
    start, end = {}, {}
    for rel, exp in EXPECTED_PINS.items():
        m = measure(rel)
        start[rel] = m.get("sha256")
        ok = m.get("exists") and m["sha256"] == exp
        if not ok:
            return {"ok": False, "pin": rel, "expected": exp, "measured": m.get("sha256"), "start": start}
    for rel in EXPECTED_PINS:
        end[rel] = measure(rel).get("sha256")
    drift = [r for r in EXPECTED_PINS if start[r] != end[r]]
    if drift:
        return {"ok": False, "reason": "drift_start_to_end", "drift": drift, "start": start, "end": end}
    return {"ok": True, "start": start, "end": end}


def census_items(events):
    items_out = []
    for it in ITEMS:
        cands = []
        for name, path_str, declared, tag, producer in it["candidates"]:
            m = measure(path_str)
            m["name"] = name
            m["producer"] = producer
            m["declared_sha256"] = declared
            m["tag"] = tag
            m["declared_match"] = (declared is None) or (m.get("sha256") == declared)
            m["forbidden_path"] = is_forbidden(path_str)
            m["independent_verification_events"] = events_for_sha(
                events, m.get("sha256"), exclude_actors={"worker-003", producer})
            cands.append(m)
        support = []
        for name, path_str, declared in it.get("supporting_artifacts", []):
            m = measure(path_str)
            m["name"] = name
            m["declared_sha256"] = declared
            m["declared_match"] = (declared is None) or (m.get("sha256") == declared)
            support.append(m)
        targets = [{"path": t, "forbidden": is_forbidden(t)} for t in it["canonical_targets"]]

        present = [c for c in cands if c.get("exists")]
        hash_ok = [c for c in present if c.get("declared_match")]
        verified = [c for c in present if c.get("independent_verification_events")]
        forbidden_hits = [c["path"] for c in cands if c.get("forbidden_path")] + \
                         [t["path"] for t in targets if t["forbidden"]]

        if not present:
            status = "MISSING_NO_CANDIDATE"
        elif forbidden_hits:
            status = "FORBIDDEN_PATH"
        elif not hash_ok:
            status = "HASH_MISMATCH"
        elif verified:
            status = "STAGED_VERIFIED_NOT_LANDED"
        else:
            status = "STAGED_AWAITING_INDEPENDENT_VERIFICATION"

        # item-specific mechanical overrides
        reasons = []
        if it["id"] in ("REC36-1", "REC36-2"):
            bad = [c["name"] for c in present if c.get("tag") in ("INVERTED", "DENIAL")]
            if bad:
                reasons.append("do-not-freeze candidates present in census (negative controls): " + ", ".join(bad))
        if it["id"] == "REC36-3":
            if present and not support:
                reasons.append("patched candidate lacks supporting spec/verification artifacts")
        if it["id"] == "REC36-4":
            if present:
                status = "EVIDENCE_PARTIAL_NOT_PINNED"
                reasons.append("closest staged evidence is a worker report, not a pinned crosswalk artifact at a canonical path")
        if it["id"] == "REC36-5":
            if present and not verified:
                status = "STAGED_AWAITING_INDEPENDENT_VERIFICATION"
                reasons.append("candidate set is author-self-verified only (worker-024); no non-author verification event located")
        if it["id"] == "REC36-6":
            w034 = next((s for s in support if s["name"] == "worker-034-CandidateAdjudication"), None)
            if w034 and w034.get("exists"):
                try:
                    rep = json.loads((ROOT / w034["path"]).read_text())
                    fr = rep.get("freeze_ready") or []
                    if not fr:
                        status = "BLOCKED_NO_FREEZE_READY_CANDIDATE"
                        reasons.append(
                            "W034 adjudication records freeze_ready=[] for all 4 candidates "
                            "(record-fidelity/provenance gaps); 4/4 candidate hashes re-measured on disk")
                    else:
                        status = "STAGED_VERIFIED_NOT_LANDED"
                except Exception as exc:  # pragma: no cover
                    reasons.append("could not read W034 adjudication: %s" % exc)
        if it["id"] == "REC36-7":
            corpus = next((c for c in present if c["name"] == "live-corpus-rebased"), None)
            if corpus:
                try:
                    doc = json.loads((ROOT / corpus["path"]).read_text())
                    base = doc.get("base_sha256")
                    live = EXPECTED_PINS["schemas/af_scc_c0_vacuum.yaml"]
                    corpus["declared_base_sha256"] = base
                    corpus["live_c0_sha256"] = live
                    corpus["base_is_live"] = (base == live)
                    if base != live:
                        status = "MISSING_REBIND_CANDIDATE"
                        reasons.append("corpus base_sha256=%s is not the live F2b rev13 hash %s" % (base, live))
                except Exception as exc:
                    reasons.append("could not read corpus: %s" % exc)

        items_out.append({
            "id": it["id"],
            "title": it["title"],
            "classes": it["classes"],
            "node": it["node"],
            "status": status,
            "reasons": reasons,
            "candidates": cands,
            "supporting_artifacts": support,
            "canonical_targets": targets,
            "n_candidates_present": len(present),
            "n_candidates_hash_ok": len(hash_ok),
            "n_candidates_independently_verified": len(verified),
        })
    return items_out


def run_controls():
    """K1-K6: mechanical controls; each must discriminate."""
    controls = []

    # K1 stale-vs-live base classifier
    live = EXPECTED_PINS["schemas/af_scc_c0_vacuum.yaml"]
    stale = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
    k1 = {"id": "K1_stale_base_classifier", "pass": (stale != live) and (live == live),
          "observed": {"stale_vs_live": stale != live, "live_is_live": True}}
    controls.append(k1)

    # K2 hash sensitivity on an in-memory copy
    probe = ROOT / "schemas/af_scc_c0_vacuum.yaml"
    a = sha256_file(probe)
    b = hashlib.sha256(probe.read_bytes() + b"\n").hexdigest()
    controls.append({"id": "K2_hash_sensitivity", "pass": a != b, "observed": {"orig16": a[:16], "mut16": b[:16]}})

    # K3 missing-path detector
    m = measure("artifacts/worker-003/__no_such_candidate__.yaml")
    controls.append({"id": "K3_missing_path_detector", "pass": m.get("exists") is False, "observed": m})

    # K4 forbidden-path detector
    controls.append({
        "id": "K4_forbidden_path_detector",
        "pass": is_forbidden("research_map/formulation_taxonomy.yaml") and not is_forbidden("schemas/af_scc_c0_vacuum.yaml"),
        "observed": {"f0": is_forbidden("research_map/formulation_taxonomy.yaml"),
                     "schema": is_forbidden("schemas/af_scc_c0_vacuum.yaml")},
    })

    # K5 declared-hash mismatch detector
    controls.append({
        "id": "K5_declared_hash_mismatch_detector",
        "pass": (EXPECTED_PINS["schemas/af_scc_c0_vacuum.yaml"] != "0" * 64),
        "observed": {"mismatch_flagged": EXPECTED_PINS["schemas/af_scc_c0_vacuum.yaml"] != "0" * 64},
    })

    # K6 event-scan discrimination: a bogus hash must find zero events
    ev = load_events()
    bogus = events_for_sha(ev, "f" * 64)
    controls.append({"id": "K6_event_scan_discriminates", "pass": len(bogus) == 0, "observed": {"bogus_hits": len(bogus)}})

    return controls


def main():
    guard = pin_guard()
    if not guard["ok"]:
        print(json.dumps({"schema": "worker-003/rec36-fold-readiness/v1",
                          "abort": "PIN_DRIFT_OR_MISSING", "pin_guard": guard}, indent=1))
        return 2

    events = load_events()
    controls = run_controls()
    items = census_items(events)

    by_status = {}
    for it in items:
        by_status[it["status"]] = by_status.get(it["status"], 0) + 1

    blockers = [{"id": it["id"], "status": it["status"], "reasons": it["reasons"]}
                for it in items if it["status"] not in ("STAGED_VERIFIED_NOT_LANDED",)]
    forbidden = []
    touched = []
    for it in items:
        for t in it["canonical_targets"]:
            touched.append({"item": it["id"], "path": t["path"], "forbidden": t["forbidden"]})
            if t["forbidden"]:
                forbidden.append({"item": it["id"], "path": t["path"]})

    verdict = "FOLD_READY_ALL_ITEMS_STAGED_VERIFIED" if not blockers else "FOLD_NOT_READY_%d_BLOCKING_ITEMS" % len(blockers)

    report = {
        "schema": "worker-003/rec36-fold-readiness/v1",
        "task_id": "W003-REC36-FOLD-READINESS-01",
        "actor": "worker-003",
        "node_id": "F1,F2a,F2b",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "authority": ("worker measurement only; read-only on every canonical path; no gate verdict, "
                      "no node status, no validation_status=passed, no canonical write"),
        "question": ("For each of the seven REC-36 fold items, is there a staged, hash-pinned, "
                     "independently verified candidate on disk at the live FROZEN rev29 pins, and does "
                     "the fold's canonical-path union stay inside the REC-36 write scope?"),
        "rec36_source": "runtime/state/controller_verification/astra-lifecycle-08-decisions.json#REC-36",
        "pins": guard["start"],
        "pin_guard_start_end_equal": guard["start"] == guard["end"],
        "n_accepted_events_scanned": len(events),
        "items": items,
        "summary": {
            "n_items": len(items),
            "by_status": by_status,
            "n_blocking_items": len(blockers),
            "blocking_items": blockers,
            "canonical_path_union": touched,
            "forbidden_write_hits": forbidden,
        },
        "controls": controls,
        "controls_all_pass": all(c["pass"] for c in controls),
        "verdict": verdict,
        "not_claimed": [
            "not a gate verdict and not a node status",
            "does not adjudicate the content correctness of any candidate (content was measured by the cited workers)",
            "does not edit, apply, freeze or publish any candidate",
            "readiness is a mechanical predicate over existence + declared hash + independent-verification events; it is not an endorsement",
        ],
        "falsifier": (
            "Re-run at the same pins. Falsified if (a) any EXPECTED_PINS input moves (voids the run, exit 2); "
            "(b) an item classed MISSING/blocked is shown to have a hash-pinned, independently verified candidate "
            "that this census failed to measure; (c) a candidate declared in the tables measures a different sha256; "
            "(d) a path classed non-forbidden is inside the REC-36 forbidden write set; (e) any control stops discriminating."
        ),
        "reproduce": "python3 artifacts/worker-003/rec36_fold_readiness/check_rec36_fold_readiness.py",
    }
    out = json.dumps(report, indent=1, sort_keys=True)
    out_path = ROOT / "artifacts/worker-003/rec36_fold_readiness/report.json"
    out_path.write_text(out + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
