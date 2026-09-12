#!/usr/bin/env python3
"""Emit worker-007's W007-REV29-PREFLIGHT-01 events (idempotent) and write the worker checkpoint.

Writes:
  comms/outbox/worker-007.jsonl                          (append; skips event_ids already present)
  runtime/state/w007_rev29_preflight_checkpoint_1.json   (worker checkpoint)
  runtime/state/w007_rev29_preflight_checkpoints.jsonl   (append one line)

Does NOT run comms.py ingest (controller-only) and does not touch research_map.json.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = None
for anc in Path(__file__).resolve().parents:
    if (anc / "research_map" / "research_map.json").exists() and (anc / "schemas").is_dir():
        ROOT = anc
        break
assert ROOT, "swarm root not found"
sys.path.insert(0, str(ROOT / "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
TASK = "W007-REV29-PREFLIGHT-01"
ART = ROOT / "artifacts" / "worker-007" / "rev29_preflight"
OUTBOX = ROOT / "comms" / "outbox" / "worker-007.jsonl"
STATE = ROOT / "runtime" / "state"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def h12(p: Path) -> str:
    return sha256(p)[:12]


FILES = {
    "report": ART / "report.json",
    "checker": ART / "verify_preflight.py",
    "readme": ART / "README.md",
    "sums": ART / "SHA256SUMS.txt",
    "dryrun": ART / "checker_runs" / "rev29_mode_dryrun.json",
    "baseline": ART / "report_preflight_baseline.json",
    "rev29": ART / "report_rev29.json",
    "drift": ART / "drift_observation.json",
    "result": ART / "REV29_RESULT.md",
    "rev29final": ART / "report_rev29_final.json",
}
PINS = {
    "artifacts/formulation/FROZEN.json": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "schemas/taxonomy_cases.jsonl": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json": "45b9b6a8d192091091820a654d8f0c7cd81764f75177f86d7f46f6ae61a447cc",
    "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json": "c28795b0fdfc1c58cc3cd7519e0d0965cbf3c2ceb6171c5ffd346735189a2185",
}

REPORT = json.loads(FILES["report"].read_text())
REV29FINAL = json.loads(FILES["rev29final"].read_text())
COUNT = REPORT["counts"]
HASHES = {k: sha256(v) for k, v in FILES.items()}
LIVE = {p: {"pin": pin, "live": sha256(ROOT / p) if (ROOT / p).exists() else None,
            "match": (sha256(ROOT / p) == pin) if (ROOT / p).exists() else False} for p, pin in PINS.items()}

ARTIFACT_REFS = [
    "artifacts/worker-007/rev29_preflight/report.json",
    "artifacts/worker-007/rev29_preflight/verify_preflight.py",
    "artifacts/worker-007/rev29_preflight/README.md",
    "artifacts/worker-007/rev29_preflight/SHA256SUMS.txt",
    "artifacts/worker-007/rev29_preflight/checker_runs/rev29_mode_dryrun.json",
]
EVIDENCE_REFS = [
    f"artifacts/worker-007/rev29_preflight/report.json#{HASHES['report'][:12]}",
    f"artifacts/worker-007/rev29_preflight/verify_preflight.py#{HASHES['checker'][:12]}",
    f"artifacts/worker-007/rev29_preflight/README.md#{HASHES['readme'][:12]}",
    f"artifacts/worker-007/rev29_preflight/SHA256SUMS.txt#{HASHES['sums'][:12]}",
    "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
    "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
    "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
    "schemas/taxonomy_cases.jsonl#ccf7041bd0ff",
    "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
    "artifacts/formulation/FROZEN.json#2f358f6722d9",
    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#45b9b6a8d192",
    "artifacts/worker-076/gform_vis_strength/probe_result.json",
    "comms/inbox/astra-lead-formulation.jsonl#astra-life05-evidence-binding-repair",
]

CLAIM = (
    "At the pre-repair pins (FROZEN rev28 2f358f6722d9; F1 cce9c60146d6, F2a 5476a3f2c6bc, "
    "F2b 55d0a1ea9bda; taxonomy_cases ccf7041bd0ff; taxonomy_consistency 9e335e9ba1bf), the four "
    "items named in Astra's pass-05 card astra-life05-evidence-binding-repair measure as: I1 "
    "SATISFIED - 36/36 taxonomy_cases rows carry binding_status bound_taxonomy_sha_0abb9ed8a961, "
    "meta.taxonomy_ref pins F0 rev5, canonical check_taxonomy_cases.py exits 0 at ccf7041bd0ff "
    "(with a residual meta-level observation: top-level meta rebound_at 00:09:00 != "
    "taxonomy_ref.rebound_at 00:32:31 and no meta binding_status); I2 OPEN - 3/3 schemas declare "
    "f0_binding.consistency_evidence_sha256=675a99d0d25b while the live evidence file measures "
    "9e335e9ba1bf, and the schemas' own refresh rule is not self-enforcing; I3 OPEN - the pre-repair "
    "token 'strictly STRONGER than this class's single-q tail predicate' is present at F1 line 234 "
    "and the SET delta strength is still 'strictly stronger than AF-WCC-VAC-GEN' while worker-076's "
    "machine check puts the canonical single-q predicate strictly stronger; I4 OPEN - FROZEN is "
    "revision 28 with 44/44 pins resolving and verify_frozen.py exit 0, the four moved paths are not "
    "re-pinned at rev29, and schemas/taxonomy_cases.jsonl has no FROZEN manifest entry. The task also "
    "ships a reusable acceptance predicate (verify_preflight.py --mode rev29) that reports "
    "ALL_ITEMS_PASS only when all four hold at FROZEN revision >= 29. This is a statement about "
    "artifact bytes and hash resolution, not about cosmic censorship."
)

EVENTS = [
    {
        "event_id": "w007-rev29pre-artifact-report-01",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "pre_repair_binding_preflight_report",
        "path": "artifacts/worker-007/rev29_preflight/report.json",
        "sha256": HASHES["report"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": ("Pre-repair census of the four astra-life05-evidence-binding-repair items: "
                    "I1 satisfied; I2/I3/I4 open. 8/8 mutation controls pass."),
        "evidence_refs": EVIDENCE_REFS[:5],
        "falsifier": REPORT["falsifier"],
    },
    {
        "event_id": "w007-rev29pre-artifact-checker-02",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_acceptance_checker",
        "path": "artifacts/worker-007/rev29_preflight/verify_preflight.py",
        "sha256": HASHES["checker"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Reusable checker: --mode preflight (measure+controls) / --mode rev29 (post-repair acceptance predicate).",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/verify_preflight.py#{HASHES['checker'][:12]}"],
        "falsifier": "a rev29 run of the checker that reports ALL_ITEMS_PASS while any pinned file's live bytes differ from FROZEN rev29 pins",
    },
    {
        "event_id": "w007-rev29pre-artifact-readme-03",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "preflight_readme",
        "path": "artifacts/worker-007/rev29_preflight/README.md",
        "sha256": HASHES["readme"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Human-readable pre-repair baseline, re-run instructions, falsifier, non-claims.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/README.md#{HASHES['readme'][:12]}"],
        "falsifier": REPORT["falsifier"],
    },
    {
        "event_id": "w007-rev29pre-artifact-dryrun-04",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_mode_dryrun_report",
        "path": "artifacts/worker-007/rev29_preflight/checker_runs/rev29_mode_dryrun.json",
        "sha256": HASHES["dryrun"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Proof that --mode rev29 runs at the pre-repair bytes and correctly reports REV29_NOT_APPLICABLE__FROZEN_REVISION_28.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/checker_runs/rev29_mode_dryrun.json#{HASHES['dryrun'][:12]}"],
        "falsifier": "a rerun of --mode rev29 at the same bytes that does not report NOT_APPLICABLE while FROZEN revision < 29",
    },
    {
        "event_id": "w007-rev29pre-artifact-sums-05",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "sha256sums",
        "path": "artifacts/worker-007/rev29_preflight/SHA256SUMS.txt",
        "sha256": HASHES["sums"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Hashes of the report, checker, README, canonical checker runs and all snapshots.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/SHA256SUMS.txt#{HASHES['sums'][:12]}"],
        "falsifier": "any listed file whose measured sha256 differs from this file",
    },
    {
        "event_id": "w007-rev29pre-claim-06",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": CLAIM,
        "assumptions": [
            "the reviewed bytes are the snapshot copies under artifacts/worker-007/rev29_preflight/snapshot/, each re-hashed against its live path at run time and again at checkpoint time",
            "item predicates are mechanical over bytes and the three canonical checkers' exit codes; no semantic reading of the schemas is performed",
            "the four items are exactly those named in astra-life05-evidence-binding-repair; nothing else about F1/F2a/F2b is adjudicated",
            "I3's direction is worker-076's machine-checked result (artifacts/worker-076/gform_vis_strength), not re-derived here",
        ],
        "falsifier": REPORT["falsifier"],
        "evidence_refs": EVIDENCE_REFS,
        "artifact_refs": ARTIFACT_REFS,
    },
    {
        "event_id": "w007-rev29pre-review-07",
        "event_type": "review",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "target_id": ("F1@cce9c60146d6, F2a@5476a3f2c6bc, F2b@55d0a1ea9bda "
                      "(pre-repair FROZEN rev28 2f358f6722d9 pins; void once rev29 lands)"),
        "reviewer": "worker-007",
        "verdict": "revise",
        "score": 3.5,
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "hard_failures": [
            {
                "id": "W007-RP-HF-01",
                "severity": "blocking",
                "class": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
                "type": "stale_consistency_evidence_pin",
                "finding": ("F1:304, F2a:291 and F2b:308 declare f0_binding.consistency_evidence_sha256="
                            "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48 while "
                            "artifacts/formulation/evidence/taxonomy_consistency.json measures "
                            "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b. The "
                            "declared pointer does not resolve; the schemas' own binding rule requires a "
                            "refresh and a consistency re-run before any gate verdict. This is Astra's "
                            "repair item (2)."),
                "evidence": [
                    "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
                    "schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc",
                    "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
                    "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                    "artifacts/worker-007/rev29_preflight/report.json#%s" % HASHES["report"][:12],
                ],
                "repair": "refresh consistency_evidence_sha256 to the live evidence hash (or re-run the consistency check and re-pin) in all three schemas and publish FROZEN rev29",
                "falsifier": "a rev29 FROZEN manifest whose three schema pins each declare consistency_evidence_sha256 equal to the live taxonomy_consistency.json hash at the same bytes",
            },
            {
                "id": "W007-RP-HF-02",
                "severity": "major",
                "class": "AF-WCC-VAC-GEN",
                "type": "inverted_variant_strictness_text",
                "finding": ("F1 line 234 asserts variant SET is 'strictly STRONGER than this class's "
                            "single-q tail predicate' and the SET delta strength reads 'strictly stronger "
                            "than AF-WCC-VAC-GEN'; worker-076 gform_vis_strength machine-checks the "
                            "opposite direction (canonical single-q is strictly stronger; equivalence "
                            "fails on an omega-chain). Astra's repair item (3) names this direction-only "
                            "correction. This reviewer records the tokens at the pinned bytes and does "
                            "not re-derive the order."),
                "evidence": [
                    "schemas/af_wcc_vacuum.yaml#cce9c60146d6",
                    "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#45b9b6a8d192",
                    "artifacts/worker-076/gform_vis_strength/probe_result.json",
                    "artifacts/worker-007/rev29_preflight/report.json#%s" % HASHES["report"][:12],
                ],
                "repair": "correct the assertion direction in F1's class_identity_variants relation and in the SET delta strength, per worker-076's cited lines 234/236; CH strength is recorded and not flagged",
                "falsifier": "a rev29 run of verify_preflight.py where the pre-repair SET token is still present in schemas/af_wcc_vacuum.yaml or the SET delta strength is unchanged",
            },
        ],
        "findings": [
            "Repair item (1) measures already satisfied at ccf7041bd0ff: 36/36 case rows bound to live F0 rev5 0abb9ed8a961, meta.taxonomy_ref pins rev5, canonical check_taxonomy_cases.py exit 0 with 11/11 controls. Residual (non-blocking): meta top-level rebound_at 00:09:00 != taxonomy_ref.rebound_at 00:32:31 and the meta row has no binding_status.",
            "Repair item (4) is not yet met: FROZEN is revision 28 (2f358f6722d9) with 44/44 pins resolving and verify_frozen.py exit 0, but no rev29 exists and schemas/taxonomy_cases.jsonl has no manifest entry at all, so it cannot be re-pinned by the current manifest (worker-094 F-094C-3).",
            "All three canonical checkers exit 0 at the measured bytes; the stale consistency pin is not detected by check_taxonomy_consistency.py, which does not self-verify the schemas' declared pins.",
            "8/8 mutation controls pass (stale row pin, consistency-pin switch, F0-pin zeroing, SET token flip, FROZEN pin mutation, manifest entry removal, meta pin mutation, CH record-only negative control).",
            "This verdict binds only the three measured schema hashes and FROZEN rev28; it is void once FROZEN rev29 lands. Worker verdict only: it sets no gate verdict and no node status.",
        ],
        "evidence_refs": EVIDENCE_REFS,
    },
    {
        "event_id": "w007-rev29pre-artifact-checker-v2-09",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_acceptance_checker_v2",
        "path": "artifacts/worker-007/rev29_preflight/verify_preflight.py",
        "sha256": HASHES["checker"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": ("Checker v2 (supersedes the hash in w007-rev29pre-artifact-checker-02): fixes a "
                    "case-sensitivity bug in the SET-delta-strength predicate that wrongly passed item I3, "
                    "adds control M9 (delta-strength-alone regression), and makes the falsifier "
                    "mode-conditional."),
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/verify_preflight.py#{HASHES['checker'][:12]}"],
        "falsifier": "a rev29 run reporting ALL_ITEMS_PASS while the SET delta strength still reads the pre-repair wording or any pinned path differs from live bytes",
    },
    {
        "event_id": "w007-rev29pre-artifact-sums-v2-10",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "sha256sums_v2",
        "path": "artifacts/worker-007/rev29_preflight/SHA256SUMS.txt",
        "sha256": HASHES["sums"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Updated SHA256SUMS covering the baseline and rev29 reports, drift observation, result note and checker v2; supersedes the hash in w007-rev29pre-artifact-sums-05.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/SHA256SUMS.txt#{HASHES['sums'][:12]}"],
        "falsifier": "any listed file whose measured sha256 differs from this file",
    },
    {
        "event_id": "w007-rev29pre-artifact-baseline-11",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "pre_repair_report_preserved",
        "path": "artifacts/worker-007/rev29_preflight/report_preflight_baseline.json",
        "sha256": HASHES["baseline"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "The pre-repair baseline report preserved under a stable name (byte-identical to the originally emitted report.json at FROZEN rev28).",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/report_preflight_baseline.json#{HASHES['baseline'][:12]}"],
        "falsifier": REPORT["falsifier"],
    },
    {
        "event_id": "w007-rev29pre-artifact-rev29-12",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_acceptance_report",
        "path": "artifacts/worker-007/rev29_preflight/report_rev29.json",
        "sha256": HASHES["rev29"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Rev29 run at FROZEN 3d9e3d77fd87: I1 pass, I2 pass, I3 open (SET delta strength still pre-repair), I4 open (variant_delta_check.json drifted after the freeze); verdict OPEN_ITEMS=I3,I4. 9/9 controls pass.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/report_rev29.json#{HASHES['rev29'][:12]}",
                          "artifacts/formulation/FROZEN.json#3d9e3d77fd87",
                          "artifacts/formulation/evidence/variant_delta_check.json"],
        "falsifier": ("a re-run at FROZEN 3d9e3d77fd87 whose item flags differ; or a corrected SET delta "
                      "strength at 45b9b6a8d192; or variant_delta_check.json measuring the rev29 pin fc6ee058dd96"),
    },
    {
        "event_id": "w007-rev29pre-artifact-drift-13",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "unpinned_window_observation",
        "path": "artifacts/worker-007/rev29_preflight/drift_observation.json",
        "sha256": HASHES["drift"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": ("Observed the unpinned window open at 00:54:08 (verify_frozen exit 1, 7 drifts: 3 canonical "
                    "schemas, 3 mirrors, gate_test_report.json) and closed by FROZEN rev29 at 00:54:32/00:55:02; "
                    "at rev29 the item flags were I1/I2/I4 pass, I3 open."),
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/drift_observation.json#{HASHES['drift'][:12]}",
                          "artifacts/formulation/FROZEN.json#3d9e3d77fd87"],
        "falsifier": "a verify_frozen.py exit 0 at FROZEN revision 28 during the window, or a drift count other than 7 at the 00:54:08 bytes",
    },
    {
        "event_id": "w007-rev29pre-artifact-result-14",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_result_note",
        "path": "artifacts/worker-007/rev29_preflight/REV29_RESULT.md",
        "sha256": HASHES["result"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Timeline and implication: FROZEN rev29 is not yet a stable binding base; the SET variant record and one post-freeze pinned evidence file remain open, so a rev30 is required before binding reviews.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/REV29_RESULT.md#{HASHES['result'][:12]}"],
        "falsifier": "a hashes-stable rev29 window (or rev30) in which all four acceptance predicates hold and the SET variant record is corrected",
    },
    {
        "event_id": "w007-rev29pre-claim-rev29-15",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": (
            "At FROZEN rev29 (3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833, "
            "frozen_at 2026-09-12T00:55:02+08:00, 48 files), the four astra-life05-evidence-binding-repair "
            "items measure: I1 PASS (36/36 taxonomy_cases rows bound to live F0 rev5, canonical checker "
            "exit 0); I2 PASS (all three schemas declare consistency_evidence_sha256=9e335e9ba1bf = live); "
            "I3 OPEN - F1's inverted token 'strictly STRONGER than this class's single-q tail predicate' is "
            "absent at the new F1 bytes, but artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET."
            "delta.json#45b9b6a8d192 still reads strength='strictly stronger than AF-WCC-VAC-GEN'; I4 OPEN - "
            "47/48 FROZEN pins resolve, with artifacts/formulation/evidence/variant_delta_check.json "
            "measuring 0b23f0b29232fba4d6638de7d3d94f1e97851f5ba3cec8b29a43181a5a40fd7c against its rev29 "
            "pin fc6ee058dd961275b37f8386b1675112d96291e22f972204efc1f8b6df9607b1, and F1 moved again "
            "during the measurement (anchor lines 215->216, 236->237). Verdict: "
            "REV29_ACCEPTANCE_PREDICATE__OPEN_ITEMS=I3,I4. Separately, the unpinned window was observed "
            "open at 00:54:08 (verify_frozen exit 1, 7 drift paths) and closed by rev29. Conclusion: "
            "FROZEN rev29 is not yet a stable binding base for the open G-FORM round; the SET variant "
            "record and the post-freeze drift need a rev30 before binding reviews. This is a statement "
            "about artifact bytes and hash resolution, not about cosmic censorship."),
        "assumptions": [
            "the measurement is an as-of snapshot; concurrent writers moved bytes between two measurements in this slot, which is the recorded phenomenon",
            "item predicates are mechanical over bytes and the canonical checkers' exit codes; I3's direction is worker-076's machine-checked result, not re-derived",
            "the four items are exactly those named in astra-life05-evidence-binding-repair",
            "the SET-delta-strength predicate is case-insensitive and is covered by regression control M9",
        ],
        "falsifier": ("A re-run at FROZEN 3d9e3d77fd87 returning a different per-item flag; or the SET delta "
                      "at 45b9b6a8d192 carrying a corrected strength; or variant_delta_check.json measuring "
                      "its rev29 pin; or a verify_frozen.py exit 0 at FROZEN revision 28 during 00:53:4x-00:54:32."),
        "evidence_refs": [
            f"artifacts/worker-007/rev29_preflight/report_rev29.json#{HASHES['rev29'][:12]}",
            f"artifacts/worker-007/rev29_preflight/drift_observation.json#{HASHES['drift'][:12]}",
            f"artifacts/worker-007/rev29_preflight/REV29_RESULT.md#{HASHES['result'][:12]}",
            "artifacts/formulation/FROZEN.json#3d9e3d77fd87",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
            "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#45b9b6a8d192",
            "artifacts/formulation/evidence/variant_delta_check.json",
        ],
        "artifact_refs": [
            "artifacts/worker-007/rev29_preflight/report_rev29.json",
            "artifacts/worker-007/rev29_preflight/drift_observation.json",
            "artifacts/worker-007/rev29_preflight/REV29_RESULT.md",
        ],
    },
    {
        "event_id": "w007-rev29pre-status-08",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "status": "active",
        "hours": 0.6,
        "summary": ("W007-REV29-PREFLIGHT-01 complete (self-claimed class-bound task; no inbox card for "
                    "worker-007). Independent pre-repair census of the four astra-life05-evidence-binding-repair "
                    "items at FROZEN rev28: I1 satisfied (36/36 rows + checker exit 0), I2 open (3/3 stale "
                    "consistency pins), I3 open (inverted SET token at F1:234 + SET delta), I4 open (rev28, "
                    "44/44 pins resolve, taxonomy_cases unpinned). 8/8 controls pass; a rev29 acceptance "
                    "checker is shipped. Worker cannot set done/passed or a gate verdict."),
        "next_falsifier": ("Run verify_preflight.py --mode rev29 after FROZEN rev29 is published; any item "
                           "still open at the rev29 pins falsifies the repair, and any pinned path that moves "
                           "between the rev29 measurement and a binding review falsifies the pin."),
        "evidence_refs": EVIDENCE_REFS,
    },
    {
        "event_id": "w007-rev29pre-status-move-16",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "status": "active",
        "hours": 0.8,
        "summary": ("Addendum to W007-REV29-PREFLIGHT-01: FROZEN rev29 landed during the task (00:54:32/"
                    "00:55:02). Rev29 acceptance run: I1 pass, I2 pass, I3 open (SET delta strength still "
                    "pre-repair at 45b9b6a8d192), I4 open (variant_delta_check.json drifted from its rev29 "
                    "pin; F1 moved again during measurement) -> REV29_ACCEPTANCE_PREDICATE__OPEN_ITEMS=I3,I4. "
                    "The unpinned window 00:53:4x-00:54:32 was observed open (verify_frozen exit 1, 7 drifts) "
                    "and closed by rev29. FROZEN rev29 is not yet a stable binding base; a rev30 after the "
                    "SET variant-record repair is required before binding G-FORM reviews. 9/9 controls pass. "
                    "Worker cannot set done/passed or a gate verdict."),
        "next_falsifier": ("Run verify_preflight.py --mode rev29 after the SET variant record is corrected and "
                           "FROZEN rev30 is published: ALL_ITEMS_PASS at a hashes-stable window falsifies this "
                           "moving-target warning; a pinned path changing without a new revision falsifies the pin."),
        "evidence_refs": [
            f"artifacts/worker-007/rev29_preflight/report_rev29.json#{HASHES['rev29'][:12]}",
            f"artifacts/worker-007/rev29_preflight/drift_observation.json#{HASHES['drift'][:12]}",
            f"artifacts/worker-007/rev29_preflight/REV29_RESULT.md#{HASHES['result'][:12]}",
            "artifacts/formulation/FROZEN.json#3d9e3d77fd87",
        ],
    },
    {
        "event_id": "w007-rev29pre-artifact-checker-v3-17",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_acceptance_checker_v3",
        "path": "artifacts/worker-007/rev29_preflight/verify_preflight.py",
        "sha256": HASHES["checker"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Checker v3 (supersedes v2): state-independent mutation controls M2/M3 and M9 (inject the pre-repair delta strength into a copy); 9/9 controls pass at the final rev29 bytes.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/verify_preflight.py#{HASHES['checker'][:12]}"],
        "falsifier": "a rev29 run reporting ALL_ITEMS_PASS while any injected mutation is not detected by its control",
    },
    {
        "event_id": "w007-rev29pre-artifact-sums-v3-18",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "sha256sums_v3",
        "path": "artifacts/worker-007/rev29_preflight/SHA256SUMS.txt",
        "sha256": HASHES["sums"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "SHA256SUMS covering the final rev29 report and checker v3; supersedes the hash in w007-rev29pre-artifact-sums-v2-10.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/SHA256SUMS.txt#{HASHES['sums'][:12]}"],
        "falsifier": "any listed file whose measured sha256 differs from this file",
    },
    {
        "event_id": "w007-rev29pre-artifact-result-v2-19",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_result_note_v2",
        "path": "artifacts/worker-007/rev29_preflight/REV29_RESULT.md",
        "sha256": HASHES["result"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Result note with a FINAL UPDATE: the follow-up repair closed I3 (both deltas rebased 00:57:02) and FROZEN rev29 was republished at 00:57:26; final run ALL_ITEMS_PASS. Supersedes the hash in w007-rev29pre-artifact-result-14.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/REV29_RESULT.md#{HASHES['result'][:12]}"],
        "falsifier": "a final rev29 measurement whose item flags differ from the FINAL UPDATE block",
    },
    {
        "event_id": "w007-rev29pre-artifact-rev29-final-20",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "artifact_type": "rev29_final_acceptance_report",
        "path": "artifacts/worker-007/rev29_preflight/report_rev29_final.json",
        "sha256": HASHES["rev29final"],
        "validation_status": "unverified",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "task_id": TASK,
        "summary": "Final rev29 run at FROZEN 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0 (frozen_at 00:57:26, 50 files): REV29_ACCEPTANCE_PREDICATE__ALL_ITEMS_PASS, 50/50 pins resolve, 9/9 controls.",
        "evidence_refs": [f"artifacts/worker-007/rev29_preflight/report_rev29_final.json#{HASHES['rev29final'][:12]}",
                          "artifacts/formulation/FROZEN.json#815e08079aef"],
        "falsifier": "a re-run at FROZEN 815e08079aef returning a different per-item flag, or any pinned path changing without a new FROZEN revision",
    },
    {
        "event_id": "w007-rev29pre-claim-final-21",
        "event_type": "claim",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "conclusion_type": "formal_model",
        "statement": (
            "FINAL: at FROZEN rev29 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0 "
            "(frozen_at 2026-09-12T00:57:26+08:00, 50 files), all four astra-life05-evidence-binding-repair "
            "items hold: I1 (36/36 taxonomy_cases rows bound to live F0 rev5 0abb9ed8a961, taxonomy_cases "
            "ccf7041bd0ff now carries a FROZEN pin, canonical checker exit 0); I2 (all three schemas declare "
            "consistency_evidence_sha256=9e335e9ba1bf = live); I3 (F1's inverted token absent; SET delta "
            "64b8d6394a04 rebased 00:57:02 with strength 'strictly weaker than AF-WCC-VAC-GEN ...', CH delta "
            "7c165a9063c6 recorded); I4 (FROZEN revision 29, 50/50 pins resolve, verify_frozen exit 0). "
            "Verdict: REV29_ACCEPTANCE_PREDICATE__ALL_ITEMS_PASS with 9/9 mutation controls. The intermediate "
            "run report_rev29.json (at the earlier 3d9e3d77 rev29 bytes) recorded I3/I4 open and is retained "
            "as evidence of the moving window: the schemas moved at 00:53:4x (unpinned window open 00:54:08, "
            "verify_frozen exit 1, 7 drifts), rev29 was published at 00:54:32/00:55:02, the variant deltas "
            "were corrected at 00:57:02, and rev29 was republished at 00:57:26. This is a statement about "
            "artifact bytes and hash resolution, not about cosmic censorship."),
        "assumptions": [
            "the final measurement is an as-of snapshot at FROZEN rev29 815e08079aef; the run and checkpoint re-measured all pins",
            "item predicates are mechanical over bytes and the canonical checkers' exit codes; I3's direction is worker-076's machine-checked result, not re-derived",
            "the four items are exactly those named in astra-life05-evidence-binding-repair",
        ],
        "falsifier": ("A re-run at FROZEN rev29 815e08079aef returning a different per-item flag; or any of the "
                      "50 pinned paths changing bytes without a new FROZEN revision; or the SET delta at "
                      "64b8d6394a04 readvertising the pre-repair strength."),
        "evidence_refs": [
            f"artifacts/worker-007/rev29_preflight/report_rev29_final.json#{HASHES['rev29final'][:12]}",
            f"artifacts/worker-007/rev29_preflight/REV29_RESULT.md#{HASHES['result'][:12]}",
            f"artifacts/worker-007/rev29_preflight/report_rev29.json#{HASHES['rev29'][:12]}",
            f"artifacts/worker-007/rev29_preflight/drift_observation.json#{HASHES['drift'][:12]}",
            "artifacts/formulation/FROZEN.json#815e08079aef",
            "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json#64b8d6394a04",
            "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json#7c165a9063c6",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
            "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
        ],
        "artifact_refs": [
            "artifacts/worker-007/rev29_preflight/report_rev29_final.json",
            "artifacts/worker-007/rev29_preflight/REV29_RESULT.md",
            "artifacts/worker-007/rev29_preflight/report_rev29.json",
        ],
    },
    {
        "event_id": "w007-rev29pre-status-final-22",
        "event_type": "status",
        "created_at": NOW,
        "actor": "worker-007",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "task_id": TASK,
        "status": "active",
        "hours": 0.9,
        "summary": ("W007-REV29-PREFLIGHT-01 final: at FROZEN rev29 815e08079aef (00:57:26, 50 files) all "
                    "four evidence-binding repair items pass - REV29_ACCEPTANCE_PREDICATE__ALL_ITEMS_PASS, "
                    "50/50 pins resolve, 9/9 mutation controls. The slot also captured the moving window: "
                    "pre-repair baseline at rev28 (I2/I3/I4 open), unpinned window 00:53:4x-00:54:32 "
                    "(verify_frozen exit 1, 7 drifts), intermediate rev29 run with I3/I4 open, then the "
                    "variant-record repair at 00:57:02 and rev29 republish at 00:57:26. The audit lead's "
                    "G-FORM r3 round can bind the final rev29 pins provided bytes stay stable; this worker "
                    "sets no gate verdict and no node status."),
        "next_falsifier": ("Re-run verify_preflight.py --mode rev29 against FROZEN rev29 815e08079aef: any "
                           "flag differing from report_rev29_final.json, or any pinned path moving without a "
                           "new revision, re-opens the binding question."),
        "evidence_refs": [
            f"artifacts/worker-007/rev29_preflight/report_rev29_final.json#{HASHES['rev29final'][:12]}",
            f"artifacts/worker-007/rev29_preflight/REV29_RESULT.md#{HASHES['result'][:12]}",
            "artifacts/formulation/FROZEN.json#815e08079aef",
        ],
    },
]

# ---------------------------------------------------------------- emit (idempotent)
OUTBOX.parent.mkdir(parents=True, exist_ok=True)
existing = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass

emitted, skipped = [], []
for e in EVENTS:
    validate_event(e)
    if e["event_id"] in existing:
        skipped.append(e["event_id"])
        continue
    with OUTBOX.open("a") as f:
        f.write(json.dumps(e, sort_keys=False) + "\n")
    emitted.append(e["event_id"])

# ---------------------------------------------------------------- checkpoint
inputs_pinned = {}
_run_inputs = {r["path"]: r for r in REPORT["inputs_pinned"]}
for p, pin in PINS.items():
    live = ROOT / p
    measured = sha256(live) if live.exists() else None
    snap = next((s.name for s in (ART / "snapshot").glob(f"{Path(p).stem}.*{Path(p).suffix}")), None)
    inputs_pinned[p] = {"expected_pin": pin,
                        "sha256_at_run": _run_inputs.get(p, {}).get("live_sha256"),
                        "sha256_at_checkpoint": measured,
                        "live_equals_pin_at_run": _run_inputs.get(p, {}).get("live_equals_pin"),
                        "live_equals_pin_at_checkpoint": measured == pin, "snapshot": snap}

ckpt = {
    "checkpoint_id": "w007-rev29pre-ckpt-" + datetime.now(CST).strftime("%Y%m%dT%H%M%S"),
    "created_at": NOW,
    "worker": "worker-007",
    "instance": "worker-007-20260912T004802-968807",
    "task_id": TASK,
    "description": ("Independent pre-repair census of the four items in astra-life05-evidence-binding-repair "
                    "(F1/F2a/F2b, G-FORM) plus a reusable rev29 acceptance predicate."),
    "mode": "preflight",
    "node_id": "F1,F2a,F2b",
    "gates": ["G-FORM"],
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "verdict": REPORT["verdict"]["primary"],
    "counts": COUNT,
    "controls": REPORT["controls_summary"],
    "final_rev29": {
        "report": "artifacts/worker-007/rev29_preflight/report_rev29_final.json",
        "sha256": HASHES["rev29final"],
        "frozen_pin": "artifacts/formulation/FROZEN.json#815e08079aef",
        "verdict": REV29FINAL["verdict"]["primary"],
        "counts": REV29FINAL["counts"],
        "controls": REV29FINAL["controls_summary"],
    },
    "inputs_pinned": inputs_pinned,
    "artifacts": [{"path": str(FILES[k].relative_to(ROOT)), "sha256": HASHES[k]} for k in FILES],
    "canonical_checker_exits": {
        "check_taxonomy_cases": REPORT["items"]["I1"]["canonical_checker"]["exit_code"],
        "check_taxonomy_consistency": REPORT["items"]["I2"]["canonical_checker"]["exit_code"],
        "verify_frozen": REPORT["items"]["I4"]["canonical_checker"]["exit_code"],
    },
    "events_emitted": [e["event_id"] for e in EVENTS],
    "events_already_present": skipped,
    "boundaries": ["no research_map.json mutation", "no comms.py ingest", "no gate verdict",
                   "no canonical artifact edit", "no node status change"],
    "falsifier": REPORT["falsifier"],
    "next_falsifier": REPORT["next_falsifier"],
}
STATE.mkdir(parents=True, exist_ok=True)
(STATE / "w007_rev29_preflight_checkpoint_1.json").write_text(json.dumps(ckpt, indent=2, sort_keys=True) + "\n")
with (STATE / "w007_rev29_preflight_checkpoints.jsonl").open("a") as f:
    f.write(json.dumps({k: ckpt[k] for k in ("checkpoint_id", "created_at", "task_id", "verdict",
                                             "counts", "controls", "events_emitted")}) + "\n")

print(json.dumps({"emitted": emitted, "skipped": skipped, "checkpoint": ckpt["checkpoint_id"],
                  "verdict": ckpt["verdict"], "live_pins_all_match": all(v["live_equals_pin_at_checkpoint"] for v in inputs_pinned.values())},
                 indent=2))
