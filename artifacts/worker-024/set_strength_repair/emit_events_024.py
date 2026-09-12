#!/usr/bin/env python3
"""W024-SET-STRENGTH-REPAIR-01 emit step: checkpoint + outbox events.

Deterministic and idempotent:
  * regenerates exit_hashes.json as the final artifact rollup;
  * builds artifact/claim/status events with measured hashes and measured wall-clock stamps;
  * validates every event through research_map.schemas.validate_event before writing;
  * appends only event_ids not already present in comms/outbox/worker-024.jsonl;
  * writes runtime/state/w024_set_strength_repair_checkpoint.json.

No canonical research artifact is written. Re-running is a no-op for the outbox.
"""
import hashlib, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from research_map.schemas import validate_event  # noqa: E402

OUT = ROOT / "artifacts/worker-024/set_strength_repair"
OUTBOX = ROOT / "comms/outbox/worker-024.jsonl"
CKPT = ROOT / "runtime/state/w024_set_strength_repair_checkpoint.json"

CANON = [
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
    "artifacts/formulation/tools/check_variant_registry.py",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    now = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    ts = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    # 1) final rollup (exit_hashes.json itself excluded: no self-reference)
    files = sorted(p for p in OUT.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts and p.name != "exit_hashes.json")
    rollup = {str(p.relative_to(ROOT)): {"sha256": sha(p), "bytes": p.stat().st_size} for p in files}
    canon_pins = {c: sha(ROOT / c) for c in CANON}
    (OUT / "exit_hashes.json").write_text(json.dumps({
        "kind": "w024_set_strength_repair_exit_pins",
        "created_at": now,
        "canonical_pins": canon_pins,
        "artifact_rollup": rollup,
        "artifact_count": len(rollup),
        "rollup_concat_sha256": hashlib.sha256(
            "".join(f"{k}:{v['sha256']}\n" for k, v in sorted(rollup.items())).encode()).hexdigest(),
        "note": "Canonical pins are byte-identical to entry_hashes.json; no canonical path was written.",
    }, indent=2, sort_keys=True) + "\n")

    H = lambda rel: sha(ROOT / rel)[:12]  # noqa: E731
    R = lambda name: f"artifacts/worker-024/set_strength_repair/{name}"  # noqa: E731
    ev = lambda kind: {"event_id": f"w024-ssr-{ts}-{kind}", "created_at": now, "actor": "worker-024"}  # noqa: E731

    events = []
    artifacts = [
        ("report", R("report.json"), "set_strength_repair_candidate_audit",
         "Full measurement: defect sites, level model, candidate pins, 21/21 checks, F0:199 adjudication note, residual blockers, falsifier."),
        ("readme", R("README.md"), "audit_readme",
         "Method, defect table, candidate hashes, verification summary, reproduction, falsifier, residual scope."),
        ("candidate-registry", R("CANDIDATE_VARIANT_REGISTRY.json"), "unfrozen_candidate_variant_registry",
         "Unfrozen candidate: line 57 strength label only, level-qualified (class-level STRONGER, predicate-level WEAKER). NOT APPLIED."),
        ("candidate-delta", R("CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json"), "unfrozen_candidate_set_delta",
         "Unfrozen candidate: line 11 strength label only, byte-identical to the registry candidate label. NOT APPLIED."),
        ("candidate-checker", R("CANDIDATE_check_variant_registry.py"), "unfrozen_candidate_assertion_aware_checker",
         "Unfrozen candidate: SET clause strips bracket provenance notes and requires the class-level + level-qualifier + predicate-level assertions. NOT APPLIED."),
        ("patch", R("repair.patch"), "proposed_three_site_repair_patch",
         "Proposal only (not applied): applies cleanly to the three FROZEN rev29 members and reproduces all three candidates byte-for-byte."),
        ("verifier", R("verify_set_strength_repair_024.py"), "reproducible_audit_driver",
         "Independent verifier: fail-closed pin check, line-diff minimality, finite level model, five sandboxed checker runs, sibling checkers, patch round-trip."),
        ("verify-results", R("verify_results.json"), "verification_results",
         "Machine-readable per-check results: 21/21 PASS, verdict ALL_PASS, entry==exit pins."),
        ("hashpins", R("exit_hashes.json"), "entry_exit_hash_pins",
         f"Exit rollup: {len(rollup)} artifact files, 6 canonical pins identical to entry."),
    ]
    for kind, path, atype, summary in artifacts:
        e = ev(f"artifact-{kind}")
        e.update({"event_type": "artifact", "node_id": "F0", "gate": "G-FORM",
                  "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN"], "variant_id": "SET",
                  "task_id": "W024-SET-STRENGTH-REPAIR-01", "artifact_type": atype,
                  "path": path, "sha256": sha(ROOT / path), "validation_status": "unverified",
                  "summary": summary})
        events.append(e)

    refs = [
        f"{R('report.json')}#{H(R('report.json'))}",
        f"{R('README.md')}#{H(R('README.md'))}",
        f"{R('verify_results.json')}#{H(R('verify_results.json'))}",
        f"{R('verify_set_strength_repair_024.py')}#{H(R('verify_set_strength_repair_024.py'))}",
        f"{R('CANDIDATE_VARIANT_REGISTRY.json')}#{H(R('CANDIDATE_VARIANT_REGISTRY.json'))}",
        f"{R('CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json')}#{H(R('CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json'))}",
        f"{R('CANDIDATE_check_variant_registry.py')}#{H(R('CANDIDATE_check_variant_registry.py'))}",
        f"{R('repair.patch')}#{H(R('repair.patch'))}",
        f"{R('exit_hashes.json')}#{H(R('exit_hashes.json'))}",
        f"artifacts/formulation/VARIANT_REGISTRY.json#{H('artifacts/formulation/VARIANT_REGISTRY.json')}",
        f"artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#{H('artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json')}",
        f"artifacts/formulation/tools/check_variant_registry.py#{H('artifacts/formulation/tools/check_variant_registry.py')}",
        f"research_map/formulation_taxonomy.yaml#{H('research_map/formulation_taxonomy.yaml')}",
        f"artifacts/formulation/formulation_taxonomy.yaml#{H('artifacts/formulation/formulation_taxonomy.yaml')}",
        f"schemas/af_wcc_vacuum.yaml#{H('schemas/af_wcc_vacuum.yaml')}",
        f"artifacts/formulation/FROZEN.json#{H('artifacts/formulation/FROZEN.json')}",
        "artifacts/worker-094/f0_setdir_audit/run/report.json#849febe9a59c",
        "artifacts/formulation/evidence/lead_formulation_lifecycle_07_independent_verify.json#965cbc01e954",
    ]
    claim = ev("claim-set-strength-level")
    claim.update({
        "event_type": "claim", "node_id": "F0", "gate": "G-FORM", "variant_id": "SET",
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN"],
        "task_id": "W024-SET-STRENGTH-REPAIR-01", "conclusion_type": "formal_model",
        "statement": (
            "Artifact-and-checker measurement plus unfrozen repair candidate at pins VARIANT_REGISTRY "
            "6bac9adea19e, SET-delta 64b8d6394a04, checker c471da4b7be9, F0-canonical 0abb9ed8a961, "
            "F0-supplement d7419b4e8963, F1 d9cebb9404b2, FROZEN rev29 815e08079aef. (i) The live SET "
            "strength label at VARIANT_REGISTRY.json:57 and the SET-delta strength at :11 applies the "
            "predicate-level direction ('strictly weaker') to the class-level subject (variant vs parent "
            "class AF-WCC-VAC-GEN) while the justification in the same sentence is the class-level argument "
            "for stronger. (ii) The finite level model derives P entails S and not-S entails not-P, hence "
            "the SET variant is strictly STRONGER as a class statement while S is strictly WEAKER as a "
            "predicate; the repair direction agrees with F0:94 (class-level) and F1:235 (predicate-level). "
            "(iii) check_variant_registry.py:89-91 returns VALID on live bytes only because its bare "
            "'STRONGER' substring matches the bracket note [rev13 direction corrected from 'strictly "
            "STRONGER']; note-stripped it returns INVALID. (iv) An unfrozen three-site candidate "
            "(registry 5c05a8cc7ea2, delta 7a1f6212ad70, checker 8b15f43e843d, combined patch "
            "9fb0c6674849) carries one byte-identical level-qualified label in both artifacts and an "
            "assertion-aware SET clause; candidate checker INVALID on live and VALID on candidate, original "
            "checker still VALID on candidate, check_variant_deltas.py VALID and "
            "check_taxonomy_consistency.py CONSISTENT on the candidate tree, 21/21 verifier assertions "
            "PASS. No canonical byte was written; applying and re-pinning FROZEN is the gate owner's action."
        ),
        "assumptions": [
            "Level convention: the registry/delta strength field compares the variant to its parent CLASS; F0:94 and F0:200 are class-level and F1:235 is predicate-level (astra-lead-formulation lifecycle-07 measurement_6); the repair is anchored to those frozen bytes, which this run re-hashed.",
            "The semantic separation itself (P does not entail S; omega-chain witness W076-GFORM-STRICTNESS-RECONCILE-06 T4) is taken as already adjudicated; this task repairs the label level and the checker assertion, and re-derives the level ordering only.",
            "All three repair targets are FROZEN rev29 members, so adoption requires a FROZEN revision bump and re-pins of evidence/variant_registry_check.json and evidence/variant_delta_check.json; the candidates here are unfrozen and no canonical path was written.",
            "The F0:199 reading dispute is left open (worker-094 predicate-level vs lifecycle-07 class-level); the candidate is correct under either reading because it carries both levels explicitly, and no F0 byte was touched.",
        ],
        "evidence_refs": refs,
        "artifact_refs": [R("report.json"), R("CANDIDATE_VARIANT_REGISTRY.json"),
                          R("CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json"),
                          R("CANDIDATE_check_variant_registry.py"), R("repair.patch"),
                          R("verify_set_strength_repair_024.py"), R("verify_results.json"),
                          R("exit_hashes.json")],
        "falsifier": (
            "Re-run artifacts/worker-024/set_strength_repair/verify_set_strength_repair_024.py at the "
            "pre-registered pins. FALSIFIED if any of: (a) a canonical pin differs (exit 2); (b) a "
            "candidate differs from live outside the three declared sites; (c) the finite level model "
            "fails to derive variant-stronger, or the live label is shown to be governed by a declared "
            "predicate-level convention making 'weaker than AF-WCC-VAC-GEN' correct as written; (d) the "
            "five checker-contrast runs do not reproduce; (e) check_variant_deltas.py or "
            "check_taxonomy_consistency.py regress on the candidate tree; (f) repair.patch does not apply "
            "cleanly or does not reproduce the candidates."
        ),
    })
    events.append(claim)

    status = ev("status-set-strength-repair")
    status.update({
        "event_type": "status", "node_id": "F0", "gate": "G-FORM", "variant_id": "SET",
        "class_id": "AF-WCC-VAC-GEN", "class_ids": ["AF-WCC-VAC-GEN"],
        "task_id": "W024-SET-STRENGTH-REPAIR-01", "status": "active", "hours": 0.3,
        "authority_note": "worker event: no gate verdict, no validation_status=passed, no node status=done, no canonical write",
        "summary": (
            "W024-SET-STRENGTH-REPAIR-01 complete at worker level: one class-bound task taken (AF-WCC-VAC-GEN "
            "variant SET). Unfrozen 3-site candidate repair of the level-mixed strength label filed by "
            "worker-094 and confirmed by astra-lead-formulation lifecycle-07 measurement_6, plus an "
            "assertion-aware owner checker. 21/21 verifier assertions PASS, exit 0: line-diff minimality, "
            "finite level model, five sandboxed checker-contrast runs (original VALID on live; note-stripped "
            "original INVALID on live; candidate INVALID on live; candidate VALID on candidate; original "
            "VALID on candidate), sibling checkers VALID/CONSISTENT, patch round-trip byte-exact, 6/6 "
            "canonical pins unchanged at exit including G-F0 0abb9ed8a961. Adoption (apply + FROZEN bump + "
            "re-pin) belongs to the formulation gate owner."
        ),
        "evidence_refs": refs[:9],
        "next_falsifier": (
            "Owner applies repair.patch or an equivalent level-qualified label plus assertion-aware checker "
            "at the next authorized revision; then a re-run must keep candidate checker VALID on the new "
            "bytes while the note-stripped check still fails closed on the old label, and check_variant_deltas.py "
            "plus check_taxonomy_consistency.py must stay green after the FROZEN re-pin. If any pinned byte "
            "moves before adoption, re-measure and re-pin; this claim binds only to the hashes above."
        ),
    })
    events.append(status)

    for e in events:
        validate_event(e)

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            if line.strip():
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    fresh = [e for e in events if e["event_id"] not in existing]
    if fresh:
        with OUTBOX.open("a") as fh:
            for e in fresh:
                fh.write(json.dumps(e, sort_keys=True) + "\n")

    CKPT.write_text(json.dumps({
        "kind": "w024_set_strength_repair_checkpoint",
        "actor": "worker-024", "task_id": "W024-SET-STRENGTH-REPAIR-01",
        "created_at": now, "class_ids": ["AF-WCC-VAC-GEN"], "node_id": "F0", "gate": "G-FORM",
        "status": "complete_at_worker_level",
        "result": "unfrozen 3-site candidate; 21/21 verifier assertions PASS; 0 canonical writes",
        "pins": canon_pins,
        "candidate_sha256": {
            R("CANDIDATE_VARIANT_REGISTRY.json"): sha(OUT / "CANDIDATE_VARIANT_REGISTRY.json"),
            R("CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json"): sha(OUT / "CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json"),
            R("CANDIDATE_check_variant_registry.py"): sha(OUT / "CANDIDATE_check_variant_registry.py"),
            R("repair.patch"): sha(OUT / "repair.patch"),
        },
        "report_sha256": sha(OUT / "report.json"),
        "verify_results_sha256": sha(OUT / "verify_results.json"),
        "exit_hashes_sha256": sha(OUT / "exit_hashes.json"),
        "events": [e["event_id"] for e in events],
        "events_appended_now": [e["event_id"] for e in fresh],
        "authority_note": "worker checkpoint: no gate verdict, no validation_status=passed, no node done, no canonical write",
    }, indent=2, sort_keys=True) + "\n")

    print(f"events total={len(events)} appended_now={len(fresh)} (idempotent)")
    for e in events:
        print("  ", e["event_type"], e["event_id"])
    print("checkpoint:", CKPT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
