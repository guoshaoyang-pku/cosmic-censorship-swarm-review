#!/usr/bin/env python3
"""Build the worker-088 F2b rev13 repair CANDIDATE (never writes canonical paths).

Candidate bundle (all under artifacts/worker-088/f2b_rev13_blockers/candidate/):
  af_scc_c0_vacuum.rev13repair.yaml
  artifacts/formulation/evidence/taxonomy_consistency.json   (self-verifying copy)

Edits applied, each asserted to occur exactly once in the pinned live bytes:
  R1  forbidden_transfers[0].reason inverted premise  -> smaller-set wording
  R2  regularity.must_not_conflate containment denial -> nested-sets wording
  R3  new vocabulary_binding block (registry path+sha256 + per-field equivalence)
  R4  f0_binding.consistency_evidence_sha256 re-stamped to the self-verifying
      evidence copy, and the binding_note records the repair

The candidate is a proposal for the formulation lead; the canonical paths are
read-only to this worker.
"""
import hashlib
import json
import os
import sys

import yaml

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
BASE = f"{ROOT}/artifacts/worker-088/f2b_rev13_blockers"
CAND = f"{BASE}/candidate"
LIVE = f"{ROOT}/schemas/af_scc_c0_vacuum.yaml"
LIVE_EVIDENCE = f"{ROOT}/artifacts/formulation/evidence/taxonomy_consistency.json"
ALIASES = f"{ROOT}/artifacts/formulation/VOCAB_ALIASES.json"
TAXONOMY = f"{ROOT}/research_map/formulation_taxonomy.yaml"
EXPECT_LIVE = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"

R1_OLD = 'reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"'
R1_NEW = 'reason: "E_C2 is a strictly smaller extension set than E_C0, so C2-inextendibility is strictly weaker"'
R2_OLD = (
    "No containment with C2 or C0 is asserted here; the informal phrase 'strictly "
    "between' is not used and must not be cited (worker-16 F2b-16-02 accepted)."
)
R2_NEW = (
    "H2_loc is a distinct regularity-axis value from C2 and C0, but their "
    "extension sets are nested (E_C2 subset E_{C^1,1} subset E_H2loc subset "
    "E_C0; see extension_class_containment); the informal phrase 'strictly "
    "between' is not used and must not be cited (worker-16 F2b-16-02 accepted)."
)
MARKER = "\nprovenance:\n"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(f"{CAND}/artifacts/formulation/evidence", exist_ok=True)
    live_sha = sha256_file(LIVE)
    if live_sha != EXPECT_LIVE:
        print(f"REFUSING: live F2b moved to {live_sha}; candidate binds {EXPECT_LIVE}", file=sys.stderr)
        return 2

    with open(LIVE, "r", encoding="utf-8") as fh:
        text = fh.read()

    # --- R4 evidence copy first (the schema must stamp its hash) ---
    with open(LIVE_EVIDENCE, "r", encoding="utf-8") as fh:
        evidence = json.load(fh)
    evidence["map_taxonomy_sha256"] = sha256_file(TAXONOMY)
    evidence["lead_contract_sha256"] = sha256_file(
        f"{ROOT}/artifacts/formulation/formulation_taxonomy.yaml"
    )
    evidence["alias_registry_sha256"] = sha256_file(ALIASES)
    evidence["generator"] = (
        "artifacts/formulation/tools/check_taxonomy_consistency.py (owner must be "
        "updated to emit the three sha256 inputs; this candidate shows the required "
        "document shape)"
    )
    evidence["repair_note"] = (
        "worker-088 rev13repair candidate: compared-input sha256s recorded so the "
        "consistent=true claim is reproducible from this document alone"
    )
    ev_path = f"{CAND}/artifacts/formulation/evidence/taxonomy_consistency.json"
    with open(ev_path, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
        fh.write("\n")
    ev_sha = sha256_file(ev_path)

    # --- R1 / R2 exact replacements ---
    for name, old, new in (("R1", R1_OLD, R1_NEW), ("R2", R2_OLD, R2_NEW)):
        count = text.count(old)
        if count != 1:
            print(f"REFUSING: {name} anchor count={count} (expected 1)", file=sys.stderr)
            return 2
        text = text.replace(old, new)

    # --- R3 vocabulary binding block ---
    if text.count(MARKER) != 1:
        print("REFUSING: provenance marker not unique", file=sys.stderr)
        return 2
    aliases_sha = sha256_file(ALIASES)
    block = f"""
extensions:
  vocabulary_binding:
    alias_registry: artifacts/formulation/VOCAB_ALIASES.json
    alias_registry_sha256: "{aliases_sha}"
    policy: "canonical token first; the F0 field_vocabulary allowed-values are the registry's accepted aliases"
    conclusion_type: {{token: scc_c0_future_inextendibility, f0_allowed_equivalent_alias: strong_cosmic_censorship_C0, f0_literal_member: false, resolution: equivalent_via_bound_alias_registry}}
    genericity_kind: {{token: residual_comeager, f0_allowed_equivalent_alias: baire_residual, f0_literal_member: false, resolution: equivalent_via_bound_alias_registry}}
    owner_adjudication_required: "whether the bound registry or the frozen F0 allowed-list is operative for class-schema vocabulary; no class-semantics change is proposed either way"
"""
    text = text.replace(MARKER, block + MARKER)

    # --- R4 re-stamp + note ---
    live_ev_sha = sha256_file(LIVE_EVIDENCE)
    if text.count(live_ev_sha) != 1:
        print("REFUSING: live evidence hash not unique in schema", file=sys.stderr)
        return 2
    text = text.replace(
        f'consistency_evidence_sha256: "{live_ev_sha}"',
        f'consistency_evidence_sha256: "{ev_sha}"',
    )
    note_anchor = "the declared F0 bytes 0abb9ed8a961 are untouched.\"}"
    if text.count(note_anchor) != 1:
        print("REFUSING: binding_note anchor not unique", file=sys.stderr)
        return 2
    text = text.replace(
        note_anchor,
        'the declared F0 bytes 0abb9ed8a961 are untouched. rev13repair candidate '
        "(worker-088): the consistency-evidence document now records the sha256 of "
        "each compared input and this binding re-stamps to it in the same "
        'revision."}',
    )

    cand_path = f"{CAND}/af_scc_c0_vacuum.rev13repair.yaml"
    with open(cand_path, "w", encoding="utf-8") as fh:
        fh.write(text)

    # --- integrity of the candidate itself ---
    with open(cand_path, "r", encoding="utf-8") as fh:
        parsed = yaml.safe_load(fh.read())
    ok = (
        parsed["implication_ledger"]["forbidden_transfers"][0]["reason"].startswith("E_C2")
        and "vocabulary_binding" in (parsed.get("extensions") or {})
        and parsed["f0_binding"]["consistency_evidence_sha256"] == ev_sha
    )
    manifest = {
        "task": "W088-F2B-REV13-REPAIR-CANDIDATE",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "base_schema": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": live_sha},
        "candidate_schema": {
            "path": "artifacts/worker-088/f2b_rev13_blockers/candidate/af_scc_c0_vacuum.rev13repair.yaml",
            "sha256": sha256_file(cand_path),
            "bytes": os.path.getsize(cand_path),
        },
        "candidate_evidence": {
            "path": "artifacts/worker-088/f2b_rev13_blockers/candidate/artifacts/formulation/evidence/taxonomy_consistency.json",
            "sha256": ev_sha,
        },
        "edits": ["R1 inverted premise", "R2 containment denial", "R3 vocabulary_binding", "R4 self-verifying evidence + re-stamp"],
        "parses_and_edits_present": ok,
        "authority_note": "candidate only; canonical schemas/af_scc_c0_vacuum.yaml untouched; owner lands or rejects",
    }
    with open(f"{BASE}/candidate/MANIFEST.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(manifest))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
