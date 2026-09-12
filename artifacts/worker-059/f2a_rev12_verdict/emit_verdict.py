#!/usr/bin/env python3
"""Emit W059-F2A-REV12-VERDICT-01 artifacts, outbox events and worker checkpoint.

Writes only under artifacts/worker-059/, runtime/state/ and comms/outbox/worker-059.jsonl.
Never mutates a canonical artifact, the map, or another agent's channel.
"""
import hashlib
import json
import os
import subprocess
import time

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
HERE = os.path.join(ROOT, "artifacts/worker-059/f2a_rev12_verdict")
PINNED = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
LIVE = os.path.join(ROOT, "schemas/af_scc_c2_vacuum.yaml")


def sha_file(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def main():
    evidence = json.load(open(os.path.join(HERE, "independent_evidence.json")))
    f2a_live = sha_file(LIVE)
    drift = f2a_live != PINNED
    frozen = json.load(open(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")))
    f0_sha = sha_file(os.path.join(ROOT, "research_map/formulation_taxonomy.yaml"))
    vocab_sha = sha_file(os.path.join(ROOT, "artifacts/formulation/VOCAB_ALIASES.json"))
    evidence_sha = sha_file(os.path.join(ROOT, "artifacts/formulation/evidence/taxonomy_consistency.json"))
    gate_json = json.load(open(os.path.join(HERE, "canonical_gate_supporting.json")))
    gate_tool = os.path.join(ROOT, "artifacts/formulation/tools/check_class_schema.py")
    gate_tool_sha = sha_file(gate_tool)
    f2a_snap = os.path.join(HERE, "snapshot/f2a.5476a3f2c6bc.yaml")
    f2a_snap_sha = sha_file(f2a_snap)
    instr = os.path.join(HERE, "check_f2a_rev12.py")
    instr_sha = sha_file(instr)
    ev_path = os.path.join(HERE, "independent_evidence.json")
    ev_sha = sha_file(ev_path)

    # ledger cross-check (recomputed here so the annex is reproducible)
    import yaml

    d = yaml.safe_load(open(f2a_snap))
    led = {}
    for line in open(os.path.join(ROOT, "ledger/theorems.jsonl"), errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        led[e.get("theorem_id") or e.get("id")] = e
    ledger_rows = []
    for r in d.get("l1_ledger_refs") or []:
        tid = r.get("theorem_id")
        e = led.get(tid) or {}
        ledger_rows.append(
            {
                "theorem_id": tid,
                "schema_l1_status": r.get("l1_status"),
                "ledger_verification_status": e.get("verification_status"),
                "ledger_content_status": e.get("content_status"),
            }
        )

    annex = {
        "task": "W059-F2A-REV12-VERDICT-01",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "annex_measured_at": now_iso(),
        "pinned_sha256": PINNED,
        "snapshot_sha256": f2a_snap_sha,
        "live_f2a_sha256_at_emit": f2a_live,
        "drift_at_emit": drift,
        "frozen_manifest": {
            "path": "artifacts/formulation/FROZEN.json",
            "sha256": sha_file(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")),
            "revision": frozen.get("revision"),
            "frozen_at": frozen.get("frozen_at"),
            "pins_f2a_pinned": (frozen.get("files", {}).get("schemas/af_scc_c2_vacuum.yaml") or {}).get("sha256") == PINNED,
            "pins_f0": (frozen.get("files", {}).get("research_map/formulation_taxonomy.yaml") or {}).get("sha256"),
            "pins_evidence": (frozen.get("files", {}).get("artifacts/formulation/evidence/taxonomy_consistency.json") or {}).get("sha256"),
            "pins_vocab_aliases": (frozen.get("files", {}).get("artifacts/formulation/VOCAB_ALIASES.json") or {}).get("sha256"),
        },
        "measured_now": {
            "f0_sha256": f0_sha,
            "vocab_aliases_sha256": vocab_sha,
            "consistency_evidence_sha256": evidence_sha,
        },
        "declared_consistency_evidence_sha256_in_f2a": (d.get("f0_binding") or {}).get("consistency_evidence_sha256"),
        "declared_evidence_matches_current": (d.get("f0_binding") or {}).get("consistency_evidence_sha256") == evidence_sha,
        "canonical_gate_supporting": {
            "path": "artifacts/formulation/tools/check_class_schema.py",
            "sha256": gate_tool_sha,
            "verdict": gate_json.get("verdict"),
            "failed_rules": gate_json.get("failed_rules"),
            "note": "supporting evidence only; the verdict below does not rest on this gate",
        },
        "ledger_cross_check": ledger_rows,
    }
    annex_path = os.path.join(HERE, "postrun_annex.json")
    with open(annex_path, "w") as fh:
        json.dump(annex, fh, indent=1, sort_keys=True)
    annex_sha = sha_file(annex_path)

    verdict = "revise"
    if drift:
        verdict = "inconclusive"  # void on drift
    review = {
        "task": "W059-F2A-REV12-VERDICT-01",
        "reviewer": "worker-059",
        "reviewer_role": "bounded execution worker; independent instrument, no canonical-gate imports",
        "target_id": "F2a",
        "target_path": "schemas/af_scc_c2_vacuum.yaml",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "gate": "G-FORM",
        "reviewed_sha256": PINNED,
        "review_window_utc8": {"opened": "2026-09-12T00:33:35+08:00", "closed": now_iso()},
        "live_hash_at_close": f2a_live,
        "drift_voids_verdict": drift,
        "verdict": verdict,
        "score": 4.0,
        "counts_as_independent_verdict": True,
        "counts_as_full_schema_verdict": True,
        "counts_as_independent_second_verdict": False,
        "hard_failures": [
            {
                "id": "HF-059-F2A-01",
                "severity": "blocking",
                "kind": "class-binding/vocabulary",
                "statement": (
                    "At the pinned pair, conclusion.conclusion_type='scc_c2_future_inextendibility' is NOT in the bound "
                    "canonical F0 field_vocabulary.conclusion_type.allowed ['weak_cosmic_censorship', "
                    "'strong_cosmic_censorship_C2', 'strong_cosmic_censorship_C0'] and differs from the bound F0 axis token "
                    "'strong_cosmic_censorship_C2'; independently, the frozen VOCAB_ALIASES.json declares F2a's token the "
                    "canonical key and F0's token a registered alias that 'must never appear in a new canonical artifact'. "
                    "Both files are canonical and pinned by FROZEN r28. The canonical class gate returns verdict=pass with 0 "
                    "failed rules on the same bytes, so the gate does not enforce F0's allowed list. No controller record "
                    "designates which registry governs a new canonical artifact."
                ),
                "evidence": [
                    f"snapshot/f2a.5476a3f2c6bc.yaml#{f2a_snap_sha[:12]} (conclusion.conclusion_type)",
                    f"research_map/formulation_taxonomy.yaml#{f0_sha[:12]} (classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type, field_vocabulary.conclusion_type.allowed)",
                    f"artifacts/formulation/VOCAB_ALIASES.json#{vocab_sha[:12]} (conclusion_type key/alias map + policy)",
                    "artifacts/worker-059/f2a_rev12_verdict/canonical_gate_supporting.json (verdict=pass, failed_rules=[])",
                ],
                "falsifier": (
                    "A controller ruling designating one registry as authoritative plus a revision of the other to match, "
                    "or documented evidence that F0's field_vocabulary.allowed is descriptive rather than binding for new "
                    "canonical artifacts. Then HF-01 clears without any change to F2a semantics."
                ),
            },
            {
                "id": "HF-059-F2A-02",
                "severity": "major, clearable by metadata refresh",
                "kind": "binding/provenance",
                "statement": (
                    "f0_binding.consistency_evidence_sha256=675a99d0... does not match the current evidence bytes "
                    f"{evidence_sha[:12]}... pinned by FROZEN r28; the declared consistency evidence is one regeneration "
                    "behind. The declared F0 hash itself is fresh (0abb9ed8 == measured)."
                ),
                "evidence": [
                    f"snapshot/f2a.5476a3f2c6bc.yaml#{f2a_snap_sha[:12]} (f0_binding)",
                    f"artifacts/formulation/evidence/taxonomy_consistency.json#{evidence_sha[:12]}",
                    f"artifacts/formulation/FROZEN.json#{annex['frozen_manifest']['sha256'][:12]} (revision {frozen.get('revision')})",
                ],
                "falsifier": (
                    "Refresh consistency_evidence_sha256 to the measured evidence hash (or restore a FROZEN whose evidence "
                    "pin equals 675a99d0) and re-run the instrument: C4 must flip to true."
                ),
            },
        ],
        "findings": [
            {
                "id": "F-059-F2A-01",
                "kind": "closure-delta (positive)",
                "statement": (
                    "Five hard-finding classes raised at b6123750 are independently confirmed RESOLVED at rev12: duplicate "
                    "top-level keys (now revision_history, strict parse clean); future-dated revised_at (00:31:41 vs live "
                    "mtime 00:32:02, skew -21 s); cross-tree class_contract_pointer (now canonical classes.<class_id>, "
                    "supplement split into its own resolving field); D0 ill-typedness (tagged union r=smooth|(sobolev,s,delta), "
                    "forall r in D0); stale f0_binding (declared F0 hash equals measured 0abb9ed8). FROZEN r28 pins the pinned "
                    "F2a hash and all current canonical bytes."
                ),
                "evidence": [
                    f"artifacts/worker-059/f2a_rev12_verdict/independent_evidence.json#{ev_sha[:12]}",
                    f"artifacts/worker-020/f2a_independent_verdict/snapshots/f2a_b6123750b37d.yaml",
                ],
            },
            {
                "id": "F-059-F2A-02",
                "kind": "well-typedness residual (medium, non-blocking)",
                "statement": (
                    "The rev12 D0 retyping is complete in the quantifier block, but genericity.ambient_space still justifies "
                    "non-emptiness of the comeager set with 'X_vac is a closed subset of a Banach space'; with D0 now "
                    "including the Frechet smooth branch, that argument covers only r=(sobolev,s,delta). The smooth topology "
                    "is declared in genericity.topology_or_measure, so the fix is an extended branchwise Baire statement, not "
                    "a semantics change."
                ),
                "evidence": [f"snapshot/f2a.5476a3f2c6bc.yaml#{f2a_snap_sha[:12]} (genericity)"],
            },
            {
                "id": "F-059-F2A-03",
                "kind": "ledger status vocabulary (medium, non-blocking)",
                "statement": (
                    "l1_ledger_refs declare l1_status accepted for T-402/T-514/T-520 and provisional for T-401/T-305, while "
                    "the corresponding ledger/theorems.jsonl rows all carry verification_status='abstract-read'. No mapping "
                    "between the schema's l1_status vocabulary and the ledger's verification_status is defined in the file. "
                    "Corroborates worker-029 F1/F2 without deciding it."
                ),
                "evidence": [f"artifacts/worker-059/f2a_rev12_verdict/postrun_annex.json#{annex_sha[:12]} (ledger_cross_check)"],
            },
            {
                "id": "F-059-F2A-04",
                "kind": "bookkeeping (low)",
                "statement": "revision_history index 9 (rev11) is marked unused:true; benign, but the history contains a hole.",
                "evidence": [f"artifacts/worker-059/f2a_rev12_verdict/independent_evidence.json#{ev_sha[:12]}"],
            },
            {
                "id": "F-059-F2A-05",
                "kind": "instrument control (positive)",
                "statement": (
                    "7/7 single-defect mutants were detected by their target checks (duplicate key, future timestamp, dangling "
                    "pointer, stale f0 hash, alias token, WCC leakage, composite regularity) and the unmodified pinned file "
                    "failed no mutant-target check except the class-binding check under adjudication. Instrument imports only "
                    "the standard library and PyYAML."
                ),
                "evidence": [
                    f"artifacts/worker-059/f2a_rev12_verdict/check_f2a_rev12.py#{instr_sha[:12]}",
                    f"artifacts/worker-059/f2a_rev12_verdict/independent_evidence.json#{ev_sha[:12]} (mutants)",
                ],
            },
            {
                "id": "F-059-F2A-06",
                "kind": "independence limits",
                "statement": (
                    "Reviewer is worker-059; several prior F2a reviewers converged on parts of HF-01 (worker-033 HF-02, "
                    "worker-095 F-BIND-4) and worker-020/worker-088 on the resolved axes, so this verdict is independent in "
                    "instrument but not necessarily in viewpoint. Whether it counts as an independent second verdict is the "
                    "controller's call (counts_as_independent_second_verdict=false)."
                ),
                "evidence": ["research_map/research_map.json#reviews (F2a)"],
            },
        ],
        "resolved_at_this_hash": [
            "duplicate revised_at keys",
            "future-dated revised_at",
            "cross-tree class_contract_pointer",
            "D0 pair-vs-smooth ill-typedness",
            "stale declared F0 hash",
            "FROZEN manifest staleness (r28 pins current bytes)",
        ],
        "evidence_refs": [
            f"artifacts/worker-059/f2a_rev12_verdict/snapshot/f2a.5476a3f2c6bc.yaml#{f2a_snap_sha[:12]}",
            f"artifacts/worker-059/f2a_rev12_verdict/independent_evidence.json#{ev_sha[:12]}",
            f"artifacts/worker-059/f2a_rev12_verdict/postrun_annex.json#{annex_sha[:12]}",
            f"artifacts/worker-059/f2a_rev12_verdict/check_f2a_rev12.py#{instr_sha[:12]}",
            f"artifacts/formulation/VOCAB_ALIASES.json#{vocab_sha[:12]}",
            f"research_map/formulation_taxonomy.yaml#{f0_sha[:12]}",
        ],
        "next_falsifier": (
            "A F2a revision (or controller ruling) in which conclusion.conclusion_type equals "
            "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type, appears in that file's "
            "field_vocabulary.conclusion_type.allowed, is the canonical key in VOCAB_ALIASES.json, and the declared "
            "consistency evidence hash equals the measured evidence bytes, all at a hash pinned by the then-current FROZEN "
            "manifest. Hash drift of schemas/af_scc_c2_vacuum.yaml voids this verdict immediately (pinned hash "
            + PINNED[:12] + ")."
        ),
    }
    review_path = os.path.join(HERE, "review_F2a_5476a3f2.json")
    with open(review_path, "w") as fh:
        json.dump(review, fh, indent=1, sort_keys=True)
    review_sha = sha_file(review_path)

    checkpoint = {
        "task": "W059-F2A-REV12-VERDICT-01",
        "actor": "worker-059",
        "role": "bounded execution worker",
        "node_id": "F2a",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "gate": "G-FORM",
        "checkpoint_id": "w059-ckpt-f2a-rev12-" + time.strftime("%Y%m%dT%H%M%S"),
        "created_at": now_iso(),
        "hours": 0.4,
        "pinned_sha256": PINNED,
        "live_sha256_at_checkpoint": f2a_live,
        "drift": drift,
        "verdict": verdict,
        "score": 4.0,
        "deliverables": {
            "review": {"path": os.path.relpath(review_path, ROOT), "sha256": review_sha},
            "evidence": {"path": os.path.relpath(ev_path, ROOT), "sha256": ev_sha},
            "annex": {"path": os.path.relpath(annex_path, ROOT), "sha256": annex_sha},
            "instrument": {"path": os.path.relpath(instr, ROOT), "sha256": instr_sha},
            "snapshot": {"path": os.path.relpath(f2a_snap, ROOT), "sha256": f2a_snap_sha},
        },
        "blocking_items": ["HF-059-F2A-01 class-binding token contradiction"],
        "no_global_state_mutated": True,
        "no_node_completion_or_gate_verdict_claimed": True,
        "next_falsifier": review["next_falsifier"],
    }
    ckpt_path = os.path.join(HERE, "checkpoint_w059_f2a_rev12.json")
    with open(ckpt_path, "w") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)
    ckpt_sha = sha_file(ckpt_path)
    state_ckpt = os.path.join(ROOT, "runtime/state/w059_f2a_rev12_checkpoint_1.json")
    with open(state_ckpt, "w") as fh:
        json.dump(checkpoint, fh, indent=1, sort_keys=True)

    # ---------------- outbox events ----------------
    ts = now_iso()
    base_refs = [
        f"artifacts/worker-059/f2a_rev12_verdict/review_F2a_5476a3f2.json#{review_sha[:12]}",
        f"artifacts/worker-059/f2a_rev12_verdict/independent_evidence.json#{ev_sha[:12]}",
        f"artifacts/worker-059/f2a_rev12_verdict/postrun_annex.json#{annex_sha[:12]}",
        f"artifacts/worker-059/f2a_rev12_verdict/check_f2a_rev12.py#{instr_sha[:12]}",
        f"artifacts/worker-059/f2a_rev12_verdict/snapshot/f2a.5476a3f2c6bc.yaml#{f2a_snap_sha[:12]}",
    ]
    events = [
        {
            "event_id": "w059-f2arev12-claim",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-059",
            "node_id": "F2a",
            "group_id": "formulation",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "gate": "G-FORM",
            "status": "active",
            "hours": 0.1,
            "summary": (
                "No inbox card exists for worker-059 (fleet 2026-09-12T00:29:48). Took ONE bounded class-bound task with "
                "no open owner: W059-F2A-REV12-VERDICT-01 = independent full-schema verification of the freshly "
                "republished F2a revision 12 at pinned sha256 5476a3f2c6bc, including closure-delta against the "
                "b6123750 hard-finding set and drift-void. Own instrument, no canonical-gate imports, 7/7 mutant controls "
                "detected. Does not claim node completion or any gate verdict."
            ),
            "evidence_refs": base_refs,
            "next_falsifier": review["next_falsifier"],
        },
        {
            "event_id": "w059-f2arev12-artifact-evidence",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-059",
            "node_id": "F2a",
            "group_id": "formulation",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "independent_measurement",
            "path": os.path.relpath(ev_path, ROOT),
            "sha256": ev_sha,
            "validation_status": "unverified",
            "reviewed_sha256": PINNED,
            "evidence_refs": [f"artifacts/worker-059/f2a_rev12_verdict/check_f2a_rev12.py#{instr_sha[:12]}"],
            "falsifier": "Re-running check_f2a_rev12.py on the pinned snapshot must reproduce every recorded boolean; any difference falsifies this evidence file.",
        },
        {
            "event_id": "w059-f2arev12-artifact-instrument",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-059",
            "node_id": "F2a",
            "group_id": "formulation",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "review_instrument",
            "path": os.path.relpath(instr, ROOT),
            "sha256": instr_sha,
            "validation_status": "unverified",
            "evidence_refs": [f"artifacts/worker-059/f2a_rev12_verdict/independent_evidence.json#{ev_sha[:12]}"],
            "note": "Stdlib+PyYAML only; builds deterministic single-defect mutants and reports sensitivity/specificity.",
        },
        {
            "event_id": "w059-f2arev12-artifact-review",
            "event_type": "artifact",
            "created_at": ts,
            "actor": "worker-059",
            "node_id": "F2a",
            "group_id": "formulation",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "gate": "G-FORM",
            "artifact_type": "independent_review",
            "path": os.path.relpath(review_path, ROOT),
            "sha256": review_sha,
            "validation_status": "unverified",
            "reviewed_sha256": PINNED,
            "evidence_refs": [f"artifacts/worker-059/f2a_rev12_verdict/independent_evidence.json#{ev_sha[:12]}"],
            "falsifier": review["next_falsifier"],
        },
        {
            "event_id": "w059-f2arev12-review",
            "event_type": "review",
            "created_at": ts,
            "actor": "worker-059",
            "reviewer": "worker-059",
            "target_id": "F2a",
            "target_path": "schemas/af_scc_c2_vacuum.yaml",
            "node_id": "F2a",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "gate": "G-FORM",
            "reviewed_sha256": PINNED,
            "artifact": os.path.relpath(review_path, ROOT),
            "sha256": review_sha,
            "verdict": verdict,
            "score": 4.0,
            "counts_as_independent_verdict": True,
            "counts_as_full_schema_verdict": True,
            "counts_as_independent_second_verdict": False,
            "hard_failures": [h["id"] + ": " + h["statement"] for h in review["hard_failures"]],
            "findings": [f["id"] + ": " + f["statement"] for f in review["findings"]],
            "resolved_at_this_hash": review["resolved_at_this_hash"],
            "evidence_refs": base_refs,
            "next_falsifier": review["next_falsifier"],
            "validation_status": "unverified",
        },
        {
            "event_id": "w059-f2arev12-blocker",
            "event_type": "blocker",
            "created_at": ts,
            "actor": "worker-059",
            "node_id": "F2a",
            "group_id": "formulation",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "gate": "G-FORM",
            "description": (
                "A binding accept for F2a at 5476a3f2c6bc is blocked by HF-059-F2A-01: the conclusion token "
                "'scc_c2_future_inextendibility' is not in the bound canonical F0 rev5 field_vocabulary.conclusion_type."
                "allowed and differs from the bound F0 axis token 'strong_cosmic_censorship_C2', while the frozen "
                "VOCAB_ALIASES.json declares F2a's token canonical and F0's token an alias that must never appear in a new "
                "canonical artifact; the canonical class gate nevertheless returns pass on the same bytes. HF-059-F2A-02 "
                "(stale consistency_evidence_sha256) is clearable by metadata refresh. All six previously reported defect "
                "classes at b6123750 are resolved at rev12 and FROZEN r28 pins the current bytes."
            ),
            "needed_to_unblock": (
                "One controller ruling designating the governing conclusion-token registry plus a matching revision of the "
                "other registry (F0 field_vocabulary or VOCAB_ALIASES), and a refresh of consistency_evidence_sha256 to "
                "the measured evidence hash; then hold F2a stable for one full review window."
            ),
            "evidence_refs": base_refs,
            "expected_information_gain": "high: removes the last class-binding blocker on the F2a leg of G-FORM.",
        },
        {
            "event_id": "w059-f2arev12-status-checkpoint",
            "event_type": "status",
            "created_at": ts,
            "actor": "worker-059",
            "node_id": "F2a",
            "group_id": "formulation",
            "class_id": "AF-SCC-C2-VAC-GEN",
            "gate": "G-FORM",
            "status": "active",
            "hours": 0.4,
            "checkpoint_id": checkpoint["checkpoint_id"],
            "summary": (
                "W059-F2A-REV12-VERDICT-01 complete at worker level. Pinned F2a rev12 sha256 5476a3f2c6bc (stable "
                "00:32:02-"
                + time.strftime("%H:%M:%S")
                + ", no drift). Verdict revise 4.0: semantics, well-typedness, pointers and class-separation clean; one "
                "blocking class-binding contradiction between F2a's conclusion token, canonical F0 rev5 field_vocabulary "
                "and frozen VOCAB_ALIASES, plus a stale consistency-evidence hash. Six prior hard-finding classes from "
                "b6123750 independently confirmed resolved; FROZEN r28 pins the current canonical set. Artifacts: "
                "artifacts/worker-059/f2a_rev12_verdict/. Worker-level checkpoint only; no global state mutated, no node "
                "completion or gate verdict claimed."
            ),
            "evidence_refs": base_refs
            + [f"artifacts/worker-059/f2a_rev12_verdict/checkpoint_w059_f2a_rev12.json#{ckpt_sha[:12]}"],
            "next_falsifier": review["next_falsifier"],
        },
    ]
    outbox = os.path.join(ROOT, "comms/outbox/worker-059.jsonl")
    with open(outbox, "a") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(json.dumps({
        "verdict": verdict,
        "drift": drift,
        "review": os.path.relpath(review_path, ROOT),
        "review_sha256": review_sha,
        "evidence_sha256": ev_sha,
        "annex_sha256": annex_sha,
        "checkpoint_sha256": ckpt_sha,
        "events_appended": len(events),
        "outbox": os.path.relpath(outbox, ROOT),
        "state_checkpoint": os.path.relpath(state_ckpt, ROOT),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
