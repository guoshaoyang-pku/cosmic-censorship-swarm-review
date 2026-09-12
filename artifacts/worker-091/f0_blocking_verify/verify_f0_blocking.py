#!/usr/bin/env python3
"""worker-091: independent, hash-bound verification of the F0 blocking findings.

Task (self-selected; no downward assignment exists for worker-091): adjudicate, by
independent mechanical measurement, the conflict between two on-file F0 verdicts that bind
the SAME canonical hash 276009f4f63d:

  * reviews/F0-review-094.json              verdict accept   (worker-094, 00:27, same hash)
  * reviews/F0-review-lead-audit-r2.json    verdict revise   (lead-audit, 00:25, same hash)
  * reviews/F0-review-16.json               verdict revise   (worker-16, same hash)
  * reviews/F0-independent-worker-082.json  verdict revise   (worker-082, same hash)

It does NOT re-review prose. It tests each *named blocking item* against the frozen bytes,
and it tests the publication ("mirror") blocker against the frozen manifest that defines
what the authoring file actually is.

Read-only with respect to canonical paths: the script copies snapshots into its own
artifact directory and never writes outside artifacts/worker-091/f0_blocking_verify/.

Output: results.json in this directory. Exit 0 when the verification itself completed
(any verdict), 2 when the target drifted mid-run (verdict must then be read as
UNMEASURED), 3 on a verification-integrity failure.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # <root>/artifacts/worker-091/f0_blocking_verify -> <root>

F0 = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
LEGACY_AGG = "schemas/af_scc_regularities.yaml"
MAP = "research_map/research_map.json"
CHECKER = "artifacts/formulation/tools/check_taxonomy_consistency.py"

BASELINE_F0_SHA = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
F0_BYTES = 35145

CONFLICT_REVIEWS = [
    "reviews/F0-review-094.json",
    "reviews/F0-review-lead-audit-r2.json",
    "reviews/F0-review-16.json",
    "reviews/F0-independent-worker-082.json",
    "reviews/F0-review-21.json",
    "reviews/F0-review-22.json",
]

SET_READING = "every future-inextendible causal geodesic contained in J-(I+) is complete"
SET_READING_SPH_ONLY = SET_READING + "; equivalently"
EQUIV_CLAUSE = "equivalently, the singularities that form are hidden behind an event horizon and no singularity is visible from I+"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(text: str, needle: str) -> int | None:
    """1-based line number of the first line containing needle, or None."""
    if not needle:
        return None
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return None


def lines_of(text: str, needle: str) -> list[int]:
    return [i for i, ln in enumerate(text.splitlines(), 1) if needle in ln]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def main() -> int:
    import yaml

    HERE.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    integrity: list[str] = []

    # ---------- Step 0: measure live inputs, freeze snapshots ----------
    f0_bytes = (ROOT / F0).read_bytes()
    supp_bytes = (ROOT / SUPP).read_bytes()
    f0_sha, supp_sha = sha256_bytes(f0_bytes), sha256_bytes(supp_bytes)
    f0_mtime = (ROOT / F0).stat().st_mtime
    supp_mtime = (ROOT / SUPP).stat().st_mtime

    (HERE / "f0_snapshot.yaml").write_bytes(f0_bytes)
    (HERE / "supplement_snapshot.yaml").write_bytes(supp_bytes)

    f0_text = f0_bytes.decode("utf-8")
    A = yaml.safe_load(f0_bytes)
    B = yaml.safe_load(supp_bytes)
    frozen = json.loads((ROOT / FROZEN).read_text())
    rmap = json.loads((ROOT / MAP).read_text())
    checker_text = (ROOT / CHECKER).read_text()

    if f0_sha != BASELINE_F0_SHA or len(f0_bytes) != F0_BYTES:
        integrity.append(
            f"BASELINE MISMATCH: measured F0 {f0_sha[:12]} / {len(f0_bytes)} B, "
            f"expected {BASELINE_F0_SHA[:12]} / {F0_BYTES} B")
    if (HERE / "f0_snapshot.yaml").read_bytes() != f0_bytes:
        integrity.append("snapshot copy is not byte-identical to the measured source")

    classes = A["classes"]
    cls_ids = list(A["class_ids"])
    sph = classes["AF-WCC-SCALAR-SPH"]
    wcc = classes["AF-WCC-VAC-GEN"]
    c2 = classes["AF-SCC-C2-VAC-GEN"]
    c0 = classes["AF-SCC-C0-VAC-GEN"]
    sph_concl = norm(sph["conclusion"]["text"])
    wcc_concl = norm(wcc["conclusion"]["text"])

    def chk(cid, source, statement, method, observed, status, refs, blocking):
        checks.append({
            "check_id": cid,
            "source_claim": source,
            "statement_under_test": statement,
            "method": method,
            "observed": observed,
            "status": status,  # CONFIRMED | REFUTED | CONTESTED | INFORMATIONAL
            "blocking_for_F0": blocking,
            "evidence_refs": refs,
        })

    # ---------- K0 integrity / drift guard ----------
    chk("K0", "worker-091 control",
        "The reviewed bytes are the ones measured and the file does not move during the run.",
        "sha256 + byte count + byte-identical snapshot; live re-hash after all checks.",
        {"pre_sha256": f0_sha, "pre_bytes": len(f0_bytes), "expected_sha256": BASELINE_F0_SHA,
         "snapshot_byte_identical": (HERE / "f0_snapshot.yaml").read_bytes() == f0_bytes},
        "CONFIRMED" if not integrity else "REFUTED", [f"{F0}#{f0_sha[:12]}"], True)

    # ---------- K1 mirror / publication divergence ----------
    chk("K1a", "reviews/F0-review-lead-audit-r2.json hard_failures[0]",
        "Canonical F0 and artifacts/formulation/formulation_taxonomy.yaml are not byte-identical.",
        "sha256 of both files; byte counts; mtimes.",
        {"canonical": {"path": F0, "sha256": f0_sha, "bytes": len(f0_bytes), "mtime": f0_mtime},
         "authoring": {"path": SUPP, "sha256": supp_sha, "bytes": len(supp_bytes), "mtime": supp_mtime},
         "byte_identical": f0_sha == supp_sha},
        "CONFIRMED" if f0_sha != supp_sha else "REFUTED",
        [f"{F0}#{f0_sha[:12]}", f"{SUPP}#{supp_sha[:12]}"], True)

    logical = (frozen.get("logical_artifacts") or {})
    mirror_req = frozen.get("f0_mirror_adjudication_request") or {}
    supp_role = norm(B.get("artifact_role", ""))
    chk("K1b", "reviews/F0-review-lead-audit-r2.json hard_failures[0] (blocker classification)",
        "The byte divergence is a publication-drift blocker that is discharged by publishing one "
        "file over the other.",
        "Read the frozen manifest's logical-artifact roles and the supplement's own artifact_role; "
        "read FROZEN.f0_mirror_adjudication_request.",
        {"frozen_revision": frozen.get("revision"),
         "frozen_logical_artifacts": {k: {"path": v.get("path"), "role": v.get("role"), "mirrors": v.get("mirrors")}
                                      for k, v in logical.items()},
         "supplement_artifact_id": B.get("artifact_id"),
         "supplement_artifact_role": supp_role[:220],
         "frozen_mirror_request": {"status": mirror_req.get("status"), "reason": mirror_req.get("reason"),
                                   "options": mirror_req.get("options"),
                                   "evidence": mirror_req.get("evidence")}},
        "CONTESTED",
        [f"{FROZEN}#{sha256_file(ROOT / FROZEN)[:12]}", f"{SUPP}#{supp_sha[:12]}"], True)

    # ---------- K2 demoted set-based reading survives in AF-WCC-SCALAR-SPH ----------
    set_in_sph = SET_READING in sph_concl
    set_in_wcc = SET_READING in wcc_concl
    single_q_marker = "single-q TAIL predicate" in wcc_concl
    set_variant = [v for v in A.get("variants", []) if v.get("variant_id") == "SET"]
    set_variant_def = norm(set_variant[0]["definition"]) if set_variant else ""
    d1 = [d for d in A["class_scope_adjudication"]["resolved_divergences"] if d.get("id") == "D1"]
    chk("K2", "worker-16 B-16F0-1; worker-082 W082-F-01(a); lead-audit-r2 hard_failures[1]",
        "The demoted set-based visibility reading survives verbatim in the AF-WCC-SCALAR-SPH "
        "conclusion of the canonical F0 revision.",
        f"Exact normalized substring test for {SET_READING!r} in each class conclusion; "
        "read the registered SET variant and the D1 resolution.",
        {"sph_conclusion_contains_set_reading": set_in_sph,
         "wcc_vac_conclusion_contains_set_reading": set_in_wcc,
         "wcc_vac_conclusion_uses_single_q_predicate": single_q_marker,
         "set_variant_registered_parent": set_variant[0].get("parent_class") if set_variant else None,
         "set_variant_status": set_variant[0].get("status") if set_variant else None,
         "set_variant_definition_head": set_variant_def[:200],
         "d1_resolution": d1[0]["resolution"] if d1 else None,
         "sph_conclusion_line": line_of(f0_text, "For generic data in the class"),
         "set_reading_raw_occurrence_lines_in_f0": lines_of(f0_text, "contained in J-(I+)"),
         "set_reading_occurrence_context": [
             {"line": n, "text": f0_text.splitlines()[n - 1].strip()[:160]}
             for n in lines_of(f0_text, "contained in J-(I+)")],
         "supplement_sph_conclusion_predicate": norm(
             (B.get("class_contracts", {}).get("AF-WCC-SCALAR-SPH", {}) or {}).get("conclusion_predicate", ""))},
        "CONFIRMED" if (set_in_sph and not set_in_wcc) else "REFUTED",
        [f"{F0}#{f0_sha[:12]}", f"{F0}:{line_of(f0_text, 'For generic data in the class')}",
         "artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-SCALAR-SPH"], True)

    # ---------- K3 unsourced 'equivalently' equivalence in AF-WCC-SCALAR-SPH ----------
    equiv_in_sph = EQUIV_CLAUSE in sph_concl
    hf06_in_wcc = "not an asserted equivalence" in wcc_concl
    sph_prov = sph.get("provenance") or {}
    equiv_sources = [k for k in ("evidence", "sources", "citation", "support") if k in sph_prov]
    chk("K3", "worker-082 W082-F-01(b); lead-audit-r2 hard_failures[1]; review HF-06 history",
        "The AF-WCC-SCALAR-SPH conclusion asserts an 'equivalently' bridge between "
        "J-(I+)-completeness and event-horizon/no-visible-singularity that is not sourced in the "
        "artifact, while the same pattern was removed from AF-WCC-VAC-GEN.",
        "Substring test for the equivalence clause; read the class provenance for any evidentiary "
        "key; read the WCC-VAC counter-wording.",
        {"sph_contains_equivalence_clause": equiv_in_sph,
         "sph_conclusion_line": line_of(f0_text, "equivalently"),
         "sph_provenance_keys": sorted(sph_prov.keys()),
         "sph_provenance_evidence_keys": equiv_sources,
         "sph_literature_status": sph_prov.get("literature_status"),
         "wcc_vac_states_definition_not_equivalence": hf06_in_wcc,
         "wcc_vac_equivalence_disclaimer_line": line_of(f0_text, "not an asserted equivalence")},
        "CONFIRMED" if (equiv_in_sph and not equiv_sources) else "REFUTED",
        [f"{F0}:{line_of(f0_text, 'equivalently')}", f"{F0}#{f0_sha[:12]}"], True)

    # ---------- K4 D3 comeager quantifier not discharged for AF-WCC-SCALAR-SPH ----------
    d3 = [d for d in A["class_scope_adjudication"]["resolved_divergences"] if d.get("id") == "D3"]
    comeager_by_class = {cid: bool(re.search(r"comeager|G_\{s,delta\}|G_\{s, ?delta\}", norm(c["conclusion"]["text"])))
                         for cid, c in classes.items()}
    gk = {cid: (c["axes"].get("genericity_kind"), c.get("genericity_value_status"))
          for cid, c in classes.items()}
    # what the lead's own consistency checker actually inspects for D1 and D3
    d1_guard = line_of(checker_text, 'wcc = ctext("AF-WCC-VAC-GEN")')
    d3_guard_lines = lines_of(checker_text, "for every data set in the class")
    d3_guard_src = (checker_text.splitlines()[d3_guard_lines[0] - 1].strip()
                    if d3_guard_lines else None)
    d1_scope_note = ("checker D1 guard evaluates only ctext('AF-WCC-VAC-GEN'); the other three class "
                     "conclusions are outside its scope" if d1_guard else "checker D1 guard not located")
    d3_scope_note = ("checker D3 guard binds 'for every data set in the class' on AF-SCC-C0-VAC-GEN and "
                     "searches the comeager token only over the concatenated AF-SCC-C2/C0 texts; "
                     "AF-WCC-SCALAR-SPH is outside its scope"
                     if d3_guard_lines else "checker D3 guard not located")
    chk("K4", "worker-16 B-16F0-2; worker-082 W082-F-02; lead-audit-r2 hard_failures[2]",
        "class_scope_adjudication.resolved_divergences[D3] claims the comeager quantifier is stated "
        "explicitly in EACH class conclusion, but it is not discharged for AF-WCC-SCALAR-SPH.",
        "Regex for a bound comeager/measure quantifier per class conclusion; compare with the D3 "
        "resolution text and the SPH axes.genericity_kind; read the D1 and D3 guards in the lead "
        "consistency checker to scope its CONSISTENT verdict.",
        {"d3_resolution": d3[0]["resolution"] if d3 else None,
         "d3_entry_keys": sorted(d3[0].keys()) if d3 else None,
         "comeager_quantifier_present_by_class": comeager_by_class,
         "genericity_kind_and_status_by_class": {k: list(v) for k, v in gk.items()},
         "sph_conclusion_head": sph_concl[:160],
         "checker_d1_guard_line": d1_guard,
         "checker_d3_guard_line": d3_guard_lines[0] if d3_guard_lines else None,
         "checker_d3_guard_source": d3_guard_src,
         "checker_d1_scope_note": d1_scope_note,
         "checker_d3_scope_note": d3_scope_note,
         "taxonomy_consistency_verdict": json.loads(
             (ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json").read_text())},
        "CONFIRMED" if (d3 and not comeager_by_class["AF-WCC-SCALAR-SPH"]) else "REFUTED",
        ["artifacts/formulation/evidence/taxonomy_consistency.json",
         f"{F0}#{f0_sha[:12]}", f"{CHECKER}#{sha256_file(ROOT / CHECKER)[:12]}"], True)

    # ---------- K5 provenance pointers target legacy aggregator + superseded node F2 ----------
    owners = {cid: norm(classes[cid]["provenance"].get("schema_owner", "")) for cid in cls_ids}
    agg_sha = sha256_file(ROOT / LEGACY_AGG)
    legacy = [x for x in rmap.get("legacy_artifacts", []) if x.get("path") == LEGACY_AGG]
    chk("K5", "worker-16 B-16F0-3; lead-audit-r2 hard_failures[3]",
        "The C2/C0 provenance.schema_owner pointers name the superseded node F2 and the legacy "
        "non-class aggregator schemas/af_scc_regularities.yaml.",
        "Read schema_owner strings; cross-check the map's legacy_artifacts record for the aggregator; "
        "measure the aggregator; check the canonical per-class schemas named by the frozen manifest.",
        {"schema_owner_by_class": owners,
         "legacy_artifacts_record": legacy[0] if legacy else None,
         "aggregator_measured_sha256": agg_sha,
         "aggregator_exists": (ROOT / LEGACY_AGG).is_file(),
         "canonical_class_schemas_in_frozen": sorted(
             k for k in (frozen.get("files") or {}) if k.startswith("schemas/af_scc")),
         "map_nodes_F2a_F2b_mentions": {"F2a": json.dumps(rmap).count("F2a"),
                                        "F2b": json.dumps(rmap).count("F2b")},
         "pointer_line_c2": line_of(f0_text, "schemas/af_scc_regularities.yaml, section C2"),
         "pointer_line_c0": line_of(f0_text, "schemas/af_scc_regularities.yaml, section C0")},
        "CONFIRMED" if all("schemas/af_scc_regularities.yaml" in owners[c]
                           for c in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN")) else "REFUTED",
        [f"{F0}:{line_of(f0_text, 'schemas/af_scc_regularities.yaml, section C2')}",
         f"{MAP}#{sha256_file(ROOT / MAP)[:12]}", f"{LEGACY_AGG}#{agg_sha[:12]}"], True)

    # ---------- K6 worker-094's non-blocking finding, independently reproduced ----------
    fv = A["field_vocabulary"]
    slot_declared = "genericity_topology" in fv
    axes_with_slot = [cid for cid, c in classes.items() if "genericity_topology" in (c.get("axes") or {})]
    chk("K6", "reviews/F0-review-094.json findings[0] (F-094-F0-01)",
        "genericity_topology is declared in field_vocabulary with a rule requiring it for "
        "generic-quantified claims, but no class axes block carries the slot.",
        "Key-presence test over field_vocabulary and the four class axes blocks.",
        {"slot_declared": slot_declared,
         "slot_rule": norm(fv.get("genericity_topology", {}).get("rule", "")) if slot_declared else None,
         "axes_blocks_carrying_slot": axes_with_slot,
         "axes_keys": {cid: sorted((c.get("axes") or {}).keys()) for cid, c in classes.items()}},
        "CONFIRMED" if (slot_declared and not axes_with_slot) else "REFUTED",
        [f"{F0}#{f0_sha[:12]}"], False)

    # ---------- K7 verdict census at the pinned hash ----------
    census = []
    for rel in CONFLICT_REVIEWS:
        p = ROOT / rel
        if not p.is_file():
            census.append({"review": rel, "present": False})
            continue
        try:
            d = json.loads(p.read_text())
        except Exception as exc:  # noqa: BLE001
            census.append({"review": rel, "present": True, "parse_error": str(exc)})
            continue
        bound = (d.get("reviewed_sha256") or d.get("artifact_sha256") or d.get("target_sha256")
                 or d.get("reviewed_hash") or (d.get("hash_drift_record") or {}).get("reviewed_sha256"))
        census.append({"review": rel, "present": True, "reviewer": d.get("reviewer") or d.get("actor"),
                       "verdict": d.get("verdict"), "score": d.get("score"),
                       "bound_sha256_prefix": (bound or "")[:12] if isinstance(bound, str) else None,
                       "binds_pinned_hash": (bound or "") == f0_sha if isinstance(bound, str) else None})
    n_accept = sum(1 for c in census if c.get("verdict") == "accept" and c.get("binds_pinned_hash"))
    n_revise = sum(1 for c in census if c.get("verdict") == "revise" and c.get("binds_pinned_hash"))
    chk("K7", "worker-091 adjudication input",
        "On-file verdicts bound to the pinned hash disagree (accept vs revise), so the conflict "
        "must be resolved by item-level measurement rather than by verdict counting.",
        "Census of F0 review files with their bound sha256 and verdict.",
        {"census": census, "accepts_at_pinned_hash": n_accept, "revises_at_pinned_hash": n_revise,
         "hard_failures_reproduced": [c["check_id"] for c in checks if c["blocking_for_F0"] and c["status"] == "CONFIRMED"],
         "hard_failures_contested": [c["check_id"] for c in checks if c["blocking_for_F0"] and c["status"] == "CONTESTED"]},
        "CONFIRMED", ["reviews/"], False)

    # ---------- Step last: drift re-measure ----------
    f0_sha_post = sha256_file(ROOT / F0)
    supp_sha_post = sha256_file(ROOT / SUPP)
    drifted = (f0_sha_post != f0_sha) or (supp_sha_post != supp_sha)

    blocking_confirmed = [c["check_id"] for c in checks if c["blocking_for_F0"] and c["status"] == "CONFIRMED"]
    blocking_contested = [c["check_id"] for c in checks if c["blocking_for_F0"] and c["status"] == "CONTESTED"]
    informational = [c["check_id"] for c in checks if c["status"] == "INFORMATIONAL"]

    if integrity:
        verdict, score = "inconclusive", 0.0
    elif drifted:
        verdict, score = "inconclusive", 0.0  # moving target: no verdict binds
    elif blocking_confirmed:
        verdict, score = "revise", 3.5
    else:
        verdict, score = "accept", 4.0

    results = {
        "schema_version": "worker-verification/v1",
        "verification_id": "w091-20260912-f0-blocking-verify",
        "actor": "worker-091",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "task": ("Independently test the F0 blocking findings that decide between the conflicting "
                 "accept (worker-094) and revise (worker-16, worker-082, lead-audit) verdicts bound "
                 "to the same canonical F0 hash."),
        "authority_note": ("Worker verdict is evidence only. Per ASTRA_HANDOFF and comms/PROTOCOL.md "
                           "this cannot set status=done, validation_status=passed, or any gate "
                           "verdict; the controller/leads adjudicate."),
        "not_claimed": [
            "no gate verdict (G-F0/G-FORM/G-AUDIT remain controller-owned)",
            "no physics claim and no review of the four class semantics beyond the named items",
            "the K1b classification is explicitly left to controller adjudication",
            "no claim that the on-file reviewers were wrong as reviewers; only their named items are measured",
        ],
        "target": {
            "artifact": F0,
            "sha256": f0_sha,
            "bytes": len(f0_bytes),
            "mtime": f0_mtime,
            "expected_baseline_sha256": BASELINE_F0_SHA,
            "revision": A.get("revision"),
            "status_field": A.get("status"),
        },
        "publication_counterpart": {"artifact": SUPP, "sha256": supp_sha, "bytes": len(supp_bytes),
                                    "mtime": supp_mtime, "artifact_id": B.get("artifact_id"),
                                    "revision": B.get("revision")},
        "drift": {"pre_sha256": f0_sha, "post_sha256": f0_sha_post,
                  "supplement_pre": supp_sha, "supplement_post": supp_sha_post,
                  "drifted_during_run": drifted},
        "verification_integrity_failures": integrity,
        "checks": checks,
        "blocking_confirmed": blocking_confirmed,
        "blocking_contested": blocking_contested,
        "informational_checks": informational,
        "verdict": verdict,
        "score": score,
        "counts_as_full_schema_verdict": True,
        "counts_as_independent_second_verdict": False,
        "conditions": [
            f"Binds only sha256 {f0_sha}; any further edit of the canonical file voids this verification.",
            "K1b is CONTESTED, not confirmed: forcing byte-identity between the declared F0 taxonomy "
            "and the F0-R class-contract supplement is destructive under FROZEN rev26; controller "
            "adjudication (REC-1/REC-2) is required before the mirror item can be called discharged.",
            "Mechanical measurement only; suitability of the class semantics is out of scope.",
        ],
        "falsifier": (
            "This artifact is FALSE if any of the following, re-run at the recorded input hashes: "
            "(1) the canonical F0 pre/post digest differs from " + f0_sha[:12] + " (then the verdict is "
            "UNMEASURED, not accept/revise); (2) the exact set-based sentence "
            "\"" + SET_READING + "\" is absent from the AF-WCC-SCALAR-SPH conclusion in "
            "f0_snapshot.yaml, or present in the AF-WCC-VAC-GEN conclusion; (3) the AF-WCC-SCALAR-SPH "
            "conclusion contains a bound comeager/measure quantifier or the D3 resolution names only "
            "classes other than it; (4) both C2 and C0 provenance.schema_owner strings name a "
            "canonical per-class schema instead of schemas/af_scc_regularities.yaml; (5) FROZEN's "
            "logical_artifacts names one artifact for both physical paths, which would refute the "
            "CONTESTED classification of K1b. Directional form: a clean accept at this hash is FALSE "
            "if any blocking check stays CONFIRMED; a revise verdict is FALSE only if all blocking "
            "checks are refuted at the pinned bytes."),
        "evidence_refs": [
            f"{F0}#{f0_sha[:12]}",
            f"{SUPP}#{supp_sha[:12]}",
            f"{FROZEN}#{sha256_file(ROOT / FROZEN)[:12]}",
            f"{MAP}#{sha256_file(ROOT / MAP)[:12]}",
            "artifacts/worker-091/f0_blocking_verify/f0_snapshot.yaml#" + f0_sha[:12],
            "artifacts/worker-091/f0_blocking_verify/results.json",
        ],
        "inputs_read": [F0, SUPP, FROZEN, MAP, LEGACY_AGG, CHECKER,
                        "artifacts/formulation/evidence/taxonomy_consistency.json"] + CONFLICT_REVIEWS,
    }

    out = HERE / "results.json"
    out.write_text(json.dumps(results, indent=1, sort_keys=False) + "\n")

    print(f"F0 {f0_sha[:12]} ({len(f0_bytes)} B) revision {A.get('revision')} status={A.get('status')}")
    for c in checks:
        refs = ", ".join(c["evidence_refs"][:3])
        print(f"  {c['check_id']:4s} {c['status']:13s} blocking={str(c['blocking_for_F0']):5s} :: {refs}")
    print(f"OVERALL: {verdict} (score {score})  drift={drifted}  integrity_failures={len(integrity)}")
    print(f"wrote {out}")
    if integrity:
        return 3
    if drifted:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
