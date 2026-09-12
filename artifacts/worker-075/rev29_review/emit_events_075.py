#!/usr/bin/env python3
"""
W075 checkpoint + outbox emitter (run once, at the end of the bounded task).

Writes:
  runtime/state/w075_checkpoint_5.json          checkpoint (hashes of every artifact)
  comms/outbox/worker-075.jsonl                 appended events (status, artifacts, claim,
                                                three reviews, blocker)

Idempotent by event_id: re-running skips an event whose id is already present in the outbox.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTBOX = ROOT / "comms/outbox/worker-075.jsonl"
CKPT = ROOT / "runtime/state/w075_checkpoint_5.json"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
TAG = datetime.now(CST).strftime("%Y%m%dT%H%M")

ARTIFACTS = [
    "artifacts/worker-075/form_binding_sweep/sweep_form_bindings_075.py",
    "artifacts/worker-075/form_binding_sweep/binding_sweep_075.json",
    "artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.py",
    "artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json",
    "artifacts/worker-075/form_binding_sweep/README.md",
    "artifacts/worker-075/rev29_review/review_gform_rev29_075.py",
    "artifacts/worker-075/rev29_review/review_summary_rev29_075.json",
    "artifacts/worker-075/rev29_review/F1-review-rev29-075.json",
    "artifacts/worker-075/rev29_review/F2a-review-rev29-075.json",
    "artifacts/worker-075/rev29_review/F2b-review-rev29-075.json",
    "artifacts/worker-075/rev29_review/README.md",
    "reviews/F1-review-rev29-075.json",
    "reviews/F2a-review-rev29-075.json",
    "reviews/F2b-review-rev29-075.json",
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def meas(rel):
    p = ROOT / rel
    return {"sha256": sha(p), "bytes": p.stat().st_size}


def main():
    arts = {r: meas(r) for r in ARTIFACTS}
    sweep = json.loads((ROOT / "artifacts/worker-075/form_binding_sweep/binding_sweep_075.json").read_text())
    reviews = {l: json.loads((ROOT / f"reviews/{l}-review-rev29-075.json").read_text())
               for l in ("F1", "F2a", "F2b")}
    vsha = {l: reviews[l]["reviewed_sha256"] for l in reviews}

    checkpoint = {
        "checkpoint": 5,
        "at": NOW,
        "assignment": "no assignment card for slot worker-075; two bounded class-bound tasks "
                      "W075-FORM-BINDING-SWEEP-07 (F0/F1/F2a/F2b, G-FORM) and "
                      "W075-GFORM-REV29-REVIEW-08 (F1/F2a/F2b, G-FORM) taken from the "
                      "astra-life05-evidence-binding-repair re-freeze and the "
                      "astra-life05-verify-gform-r3 review requirement",
        "node_id": "F0,F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "hours_spent_estimate": 0.7,
        "inputs": {
            "artifacts/formulation/FROZEN.json": {
                "sha256": sweep["S2_frozen_pins"]["manifest_sha256"],
                "revision": sweep["S2_frozen_pins"]["frozen_revision"],
                "frozen_at": sweep["S2_frozen_pins"]["frozen_at"],
            },
            **{k: {"sha256": v["sha256"]} for k, v in sweep["S1_inputs"].items()},
        },
        "frozen_rev29": {
            "manifest_sha256": sweep["S2_frozen_pins"]["manifest_sha256"],
            "pins": sweep["S2_frozen_pins"]["n_pins"],
            "pin_mismatches": len(sweep["S2_frozen_pins"]["mismatches"]),
            "declared_hash_mismatches": sweep["S3_declared_hashes"]["n_mismatch"],
            "post_freeze_rewrites_same_bytes": sweep["S2_frozen_pins"]["post_freeze_rewrites_same_bytes"],
            "checker_replay_status": sweep["S4_consistency_chain"]["checker_replay"].get("status"),
        },
        "verifier": {
            "status": json.loads((ROOT / "artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json").read_text())["status"],
            "controls": json.loads((ROOT / "artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json").read_text())["controls"],
        },
        "reviews": {l: {"verdict": reviews[l]["verdict"], "score": reviews[l]["score"],
                        "reviewed_sha256": vsha[l],
                        "hard_failures": [h["id"] for h in reviews[l]["hard_failures"]],
                        "path": f"reviews/{l}-review-rev29-075.json"} for l in reviews},
        "artifacts": arts,
        "status": {"delivered": True, "events_emitted": []},
        "next_falsifier": "Re-run the sweep and verifier at the same bytes, then re-run "
                          "review_gform_rev29_075.py: any FROZEN pin mismatch, declared-hash "
                          "mismatch, checker-replay mismatch, undetected control, hash move during "
                          "a review window, or a check that flips falsifies this checkpoint. The "
                          "F2a/F2b hard findings are cleared only by a new pin carrying a "
                          "gate-owner adjudication of the conclusion_type token, a pinned extension "
                          "manifold category (F2a), and a corrected containment premise (F2b).",
    }

    events = []

    def add(ev):
        ev = {"event_id": ev["event_id"], **{k: v for k, v in ev.items() if k != "event_id"}}
        events.append(ev)

    common = {"created_at": NOW, "actor": "worker-075", "gate": "G-FORM",
              "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]}

    add({**common, "event_id": f"w075-{TAG}-status",
         "event_type": "status", "node_id": "F0,F1,F2a,F2b", "status": "active", "hours": 0.7,
         "summary": "Two bounded class-bound tasks complete at worker level. (1) W075-FORM-BINDING-SWEEP-07: "
                    "independent declared-hash/freeze sweep at FROZEN rev29 manifest sha "
                    f"{sweep['S2_frozen_pins']['manifest_sha256'][:12]} - {sweep['S2_frozen_pins']['n_pins']}/"
                    f"{sweep['S2_frozen_pins']['n_pins']} pins match disk, 0 declared-hash mismatches, "
                    "0 consistency-chain findings, checker replay byte-identical to the pinned evidence "
                    "9e335e9ba1bf, 0/3 mirror divergences, 0/36 unbound taxonomy-case rows, 0 unauthorised "
                    "semantic diffs vs the pinned rev12 snapshots, F1 strictness model T1/T2/T4 verified; "
                    "independent verifier PASS with 6/6 controls. (2) W075-GFORM-REV29-REVIEW-08: blind "
                    "full-schema verdicts at the rev29 pins - F1 accept 4.0 (d9cebb9404b2), F2a revise 3.5 "
                    "(e9a27996dfd3: HF-075-F2a-VOCAB conclusion_type not in the bound F0 allowed vocabulary, "
                    "and HF-075-F2a-EXTCAT extension manifold category unpinned), F2b revise 3.5 "
                    "(b2ab6acb2bbe: HF-075-F2b-VOCAB and HF-075-F2b-LARGER inverted containment premise); "
                    "7/7 controls detected. Both tasks read-only on canonical paths; no gate verdict or "
                    "node completion claimed.",
         "evidence_refs": [f"artifacts/worker-075/form_binding_sweep/binding_sweep_075.json#{arts['artifacts/worker-075/form_binding_sweep/binding_sweep_075.json']['sha256'][:12]}",
                           f"artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json#{arts['artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json']['sha256'][:12]}",
                           f"artifacts/formulation/FROZEN.json#{sweep['S2_frozen_pins']['manifest_sha256'][:12]}",
                           f"reviews/F1-review-rev29-075.json#{vsha['F1'][:12]}",
                           f"reviews/F2a-review-rev29-075.json#{vsha['F2a'][:12]}",
                           f"reviews/F2b-review-rev29-075.json#{vsha['F2b'][:12]}"],
         "next_falsifier": "Re-run the two instruments at the same bytes: any FROZEN pin mismatch, "
                           "declared-hash mismatch, checker-replay mismatch, undetected control, hash "
                           "move in a review window, or a check that flips falsifies this status."})

    for rel, m in arts.items():
        add({**common, "event_id": f"w075-{TAG}-artifact-" + rel.replace("/", "-"),
             "event_type": "artifact", "node_id": "F0,F1,F2a,F2b",
             "artifact_type": ("review_verdict" if rel.startswith("reviews/")
                               else "repro_script" if rel.endswith(".py")
                               else "checkpoint" if rel.endswith("checkpoint_5.json")
                               else "evidence_report" if rel.endswith(".json") else "summary"),
             "path": rel, "sha256": m["sha256"], "validation_status": "unverified",
             "evidence_refs": [f"{rel}#{m['sha256'][:12]}"]})

    add({**common, "event_id": f"w075-{TAG}-claim-binding-sweep",
         "event_type": "claim", "node_id": "F0,F1,F2a,F2b", "class_id": "AF-SCC-C2-VAC-GEN",
         "conclusion_type": "verification_result", "claims_theorem_status": False,
         "statement": "Artifact-and-checker result (not a mathematics claim): at FROZEN rev29 "
                      f"(manifest sha256 {sweep['S2_frozen_pins']['manifest_sha256']}) the formulation "
                      "freeze is internally consistent - all "
                      f"{sweep['S2_frozen_pins']['n_pins']} manifest pins match live bytes, every declared "
                      "sha256 in the three canonical schemas and the F0 pair resolves to the path it names, "
                      "the consistency evidence is byte-reproducible by a redirected run of the pinned "
                      "checker, the three canonical/authoring schema pairs are byte-identical, "
                      "schemas/taxonomy_cases.jsonl is bound to F0 rev5 0abb9ed8a961, and the rev12->rev13 "
                      "byte changes are confined to the authorised evidence-binding + F1 strictness repair "
                      "set. Independent blind review at the same pins yields F1 accept (d9cebb9404b2), "
                      "F2a revise (e9a27996dfd3) and F2b revise (b2ab6acb2bbe); the F2a/F2b blockers are the "
                      "conclusion_type token conflict with the bound F0 field_vocabulary, the unpinned "
                      "extension manifold category in F2a, and the inverted containment premise in F2b.",
         "assumptions": ["FROZEN rev29 manifest sha 815e08079aef is the binding manifest; a later "
                         "re-issue voids the sweep numbers until re-run",
                         "the redirected checker replay is the pinned checker's logic with only ROOT and "
                         "the output path changed",
                         "review verdicts bind the measured target hashes and are void if the target or "
                         "manifest moves",
                         "worker cannot set done/passed/gate verdicts; leads adjudicate"],
         "falsifier": "Re-run sweep_form_bindings_075.py + verify_binding_sweep_075.py and "
                      "review_gform_rev29_075.py at the same bytes: falsified by any FROZEN pin mismatch, "
                      "any declared hash that does not equal its named path, a checker replay that differs "
                      "from the pinned evidence bytes, any undetected control, any target/manifest hash move, "
                      "or any unauthorised semantic change vs the rev12 snapshots.",
         "evidence_refs": [f"artifacts/worker-075/form_binding_sweep/binding_sweep_075.json#{arts['artifacts/worker-075/form_binding_sweep/binding_sweep_075.json']['sha256'][:12]}",
                           f"artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json#{arts['artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json']['sha256'][:12]}",
                           f"artifacts/formulation/FROZEN.json#{sweep['S2_frozen_pins']['manifest_sha256'][:12]}"],
         "artifact_refs": ["artifacts/worker-075/form_binding_sweep/binding_sweep_075.json",
                           "artifacts/worker-075/form_binding_sweep/verify_binding_sweep_075.json"]})

    for label in ("F1", "F2a", "F2b"):
        r = reviews[label]
        path = f"reviews/{label}-review-rev29-075.json"
        add({**common, "event_id": f"w075-{TAG}-review-{label.lower()}",
             "event_type": "review", "node_id": label, "target_id": label,
             "reviewer": "worker-075", "verdict": r["verdict"], "score": r["score"],
             "artifact_sha256": r["reviewed_sha256"], "reviewed_sha256": r["reviewed_sha256"],
             "counts_as_full_schema_verdict": True,
             "hard_failures": r["hard_failures"],
             "findings": [f"{h['id']}: {h['detail'][:400]}" for h in r["hard_failures"]]
             + [f"SOFT {s['id']}: {s['detail'][:300]}" for s in r.get("soft_findings", [])]
             + [f"{k}: {'PASS' if v.get('match', True) else 'CHECK'}" for k, v in r["checks"].items()],
             "falsifier": r["falsifier"],
             "evidence_refs": [f"{path}#{r['reviewed_sha256'][:12]}",
                               f"artifacts/formulation/FROZEN.json#{r['manifest_sha256'][:12]}"]})

    add({**common, "event_id": f"w075-{TAG}-blocker-acceptance-corpus",
         "event_type": "blocker", "node_id": "F1,F2a,F2b", "gate": "G-FORM",
         "description": "The rebased two-stage acceptance corpus is stale at the FROZEN rev29 pins: "
                        "artifacts/formulation/evidence/semantic_escape_rebased.json binds base_sha256 "
                        "1bb78ce9b3572cda (rev11 C0) while the canonical C0 schema measures "
                        "b2ab6acb2bbe7f86, so artifacts/formulation/tools/run_acceptance.py fails its own "
                        "preflight closed (exit 3) before either stage runs. Schema content is not "
                        "implicated (the schema-level checks pass), but the formulation lead's acceptance "
                        "suite is not reproducible at rev29.",
         "needed_to_unblock": "Re-run artifacts/formulation/tools/measure_semantic_escape.py at the rev29 "
                              "pins (or state that run_acceptance.py is not part of the G-FORM evidence bar) "
                              "and record the new base_sha256; no schema write required.",
         "evidence_refs": ["artifacts/formulation/evidence/semantic_escape_rebased.json",
                           "artifacts/formulation/tools/run_acceptance.py:54-63",
                           "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
                           f"reviews/F2a-review-rev29-075.json#{vsha['F2a'][:12]}"]})

    checkpoint["status"]["events_emitted"] = [e["event_id"] for e in events]
    CKPT.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    appended = 0
    with OUTBOX.open("a") as f:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, sort_keys=True) + "\n")
            appended += 1
    print(f"checkpoint -> {CKPT}")
    print(f"events appended: {appended} (of {len(events)}); outbox -> {OUTBOX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
