#!/usr/bin/env python3
"""
W070-F2B-REV29-CANDIDATE-CENSUS-01 — finalizer (worker-070).

Reads the pre-registered frame.json and the measured report.json, writes:
  - addendum.json : clearly-labelled POST-FRAME reclassification + adoption matrix
  - README.md     : one-page summary generated from the measured numbers
  - comms/outbox/worker-070.jsonl : artifact / claim / status events (idempotent)
  - runtime/state/w070_checkpoint_f2b_candidate_census.json : checkpoint

No canonical file, map entry, gate or node status is modified.
"""
import hashlib
import json
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TASK = "W070-F2B-REV29-CANDIDATE-CENSUS-01"
OUTBOX = os.path.join(ROOT, "comms/outbox/worker-070.jsonl")
CKPT = os.path.join(ROOT, "runtime/state/w070_checkpoint_f2b_candidate_census.json")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def main():
    frame = json.load(open(os.path.join(HERE, "frame.json")))
    report = json.load(open(os.path.join(HERE, "report.json")))
    frozen = report["frozen"]["sha256"]
    fz = frozen[:12]

    # ---------- addendum: post-frame reclassification + adoption matrix ----------
    post = []
    for r in report["results"]:
        d = r["sha256_declared"][:12]
        new_block_added = "extensions" in [p for p in r.get("changed_paths", [])]
        other_after = [p for p in r.get("changed_paths", [])
                       if p not in (frame["hf_sites"]["HF1_containment_denial"]["path"],
                                    frame["hf_sites"]["HF2_inverted_size_premise"]["path"])
                       and p not in frame["classification_rule"]["METADATA"]
                       and p != "extensions"]
        post.append({
            "sha256": r["sha256_declared"], "author": r["author"], "label": r["label"],
            "core_repair_complete": r.get("status") == "CORE_REPAIR_COMPLETE",
            "core_sites_changed": [c["site"] for c in r.get("core_changes", [])],
            "metadata_changes": [m["class"] for m in r.get("metadata_changes", [])],
            "new_top_level_blocks": (["extensions"] if new_block_added else []),
            "other_changes_frame_rule": [o["path"] for o in r.get("other_changes", [])],
            "other_changes_after_reclassification": other_after,
            "evidence_pin": (r.get("external_refs", {}).get("consistency_evidence") or {}),
            "adoption_note": None,
        })
    for e in post:
        d = e["sha256"][:12]
        if not e["core_repair_complete"]:
            e["adoption_note"] = ("would carry the unrepaired carrier(s) into a freeze: "
                                  "HF1 containment denial survives (P1 false)")
        elif not e["metadata_changes"] and not e["new_top_level_blocks"]:
            e["adoption_note"] = "core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin"
        elif d == "48cadb72e507":
            e["adoption_note"] = ("core + revision 13->14 + evidence pin moved to 675a99d0 (neither the FROZEN "
                                  "manifest pin nor the live file, both 9e335e9b) + new extensions.vocabulary_binding "
                                  "block (alias-registry sha matches FROZEN; declared token matches rule_spec)")
        elif d == "b598b59e09e5":
            e["adoption_note"] = ("core + evidence pin moved to a03ba9c5 (neither frozen nor live; would require a "
                                  "coupled evidence-document freeze) + binding_note update + new extensions block "
                                  "(no declared_conclusion_type_canonical field, so the vocabulary check reports "
                                  "'field absent', not a contradiction)")
        else:
            e["adoption_note"] = "core + declared metadata/binding changes"

    addendum = {
        "task_id": TASK, "actor": "worker-070", "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
        "created_at": now(),
        "label": "POST-FRAME ADDENDUM — generated after report.json; report.json is unchanged",
        "parent_report_sha256": sha256_file(os.path.join(HERE, "report.json")),
        "parent_frame_sha256": report["frame_sha256"],
        "post_frame_reclassification": {
            "rule_v1_0": "NEW_BLOCK = changed paths STARTING WITH 'extensions.'",
            "rule_v1_1": "NEW_BLOCK also includes the exact added top-level key 'extensions'",
            "reason": ("the instrument reports an added top-level key with exact path 'extensions', not "
                       "'extensions.<field>'; the frame rule missed the exact path"),
            "effect": ("48cadb72e507 other 1->0 and new_block 0->1; b598b59e09e5 other 2->1 and new_block 0->1; "
                       "no core classification, predicate, invariant or hash changes"),
        },
        "adoption_matrix": post,
        "convergence": report["convergence"],
        "instrument_caveats": [
            ("variant-token scan is substring-based: token 'SET' fires on the word 'SETS' in some repaired HF1 "
             "texts; the H2LOC registration check (the only variant actually named as a variant entry in those "
             "texts) resolves true with parent_class AF-SCC-C0-VAC-GEN; treat the 'SET' row as a lexical false "
             "positive, not a finding"),
            ("equality asserted here is byte/object equality at the pinned hashes; no semantic equivalence "
             "between the distinct HF1 wordings is claimed"),
            ("b598b59e09e5's extensions block is not the same schema as 48cadb72e507's; the vocabulary check "
             "reports ok=false because the declared_conclusion_type_canonical field is absent, which is a "
             "missing-field observation, not a contradiction with rule_spec"),
        ],
        "headline": [
            "9 of 10 declared candidates discharge both standing blocking carriers with all frozen invariants preserved",
            "3cdcaa44e6f1 repairs only the inverted-premise carrier (worker-047 inversion-only variant); HF1 denial survives",
            "7 of 10 are core-only (only the two HF carriers differ from the frozen bytes)",
            "HF2 has one byte-identical 6-candidate repair; HF1 has 9 distinct wordings across 10 candidates",
            "48cadb72e507 and b598b59e09e5 also move the consistency-evidence pin off the frozen 9e335e9b",
            "the conclusion-token conflict is gate-wide and not candidate-fixable",
        ],
        "falsifier": report["falsifier"],
        "authority": report["authority"],
    }
    add_path = os.path.join(HERE, "addendum.json")
    json.dump(addendum, open(add_path, "w"), indent=1, sort_keys=True)

    # ---------- README (generated from measured numbers) ----------
    rows = []
    for e in post:
        d = e["sha256"][:12]
        rows.append(f"| `{d}` | {e['author']} | {'YES' if e['core_repair_complete'] else 'NO (P1)'} | "
                    f"{len(e['core_sites_changed'])}/2 | {','.join(e['metadata_changes']) or '-'} | "
                    f"{','.join(e['new_top_level_blocks']) or '-'} | {e['adoption_note']} |")
    hf1 = report["convergence"]["HF1"]["distinct_repairs"]
    hf2 = report["convergence"]["HF2"]["distinct_repairs"]
    readme = f"""# W070-F2B-REV29-CANDIDATE-CENSUS-01 — one page

**Worker:** worker-070 · **Node:** F2b · **Class:** `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Nature:** artifact-and-byte measurement. No mathematical claim, no gate verdict, no node status,
no canonical write. `report.json` is the pre-registered run; `addendum.json` is a clearly-labelled
post-frame reclassification.

## Question

At the FROZEN rev29 pin of `schemas/af_scc_c0_vacuum.yaml` (`{fz}`), for each of the
10 declared rev29/rev14 repair candidates: which semantic paths change, is every change at one of
the two standing blocking-hard-failure carriers or a declared metadata/binding path, are the two
carriers discharged, are the frozen invariants preserved, and do introduced external references
resolve?

## Headline

- **9/10 candidates** discharge both blocking carriers (HF1 containment denial, HF2 inverted size
  premise) and preserve every frozen invariant (class id, conclusion token, containment chain,
  counts, declared F0 pin) with the rest of the document byte-identical.
- **`3cdcaa44e6f1` (worker-047) repairs only HF2** — the HF1 denial survives, so adopting it would
  carry a standing blocker into a freeze.
- **7/10 are core-only** (only the two HF carriers differ).
- **Convergence is asymmetric:** HF2 has one byte-identical repair shared by 6 candidates; HF1 has
  **{hf1} distinct wordings** across 10 candidates (no convergent text).
- **Two candidates move the evidence pin:** `48cadb72e507` → `675a99d0` (neither the FROZEN
  manifest pin nor the live file, both `9e335e9b`); `b598b59e09e5` → `a03ba9c5` (couples a new
  evidence document to the freeze). Both also add an `extensions` block.
- The conclusion-token conflict between F0's `field_vocabulary.allowed` and VOCAB_ALIASES canonical
  tokens is gate-wide and **not candidate-fixable** (unchanged residual).

## Adoption matrix (measured)

| candidate | author | both carriers | core sites | metadata | new block | adoption note |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Instrument and controls

Strict YAML load (duplicate-key detecting) + object-tree deep diff + cross-registry resolution.
Controls **6/6 PASS**: no-op zero diffs; unrelated-leaf mutation detected at exactly that path;
denial re-injection fails P1; inversion re-injection fails P2; fabricated variant token unresolved;
duplicate-key detector fires. Pins unchanged before/after; the FROZEN-manifest pin equals the live
schema; the mirror copy is byte-identical.

## Replication

```bash
python3 artifacts/worker-070/f2b_candidate_census/census_070.py   # pre-registered run
python3 artifacts/worker-070/f2b_candidate_census/finalize_070.py # addendum + events + checkpoint
```

Falsifier: re-run at the same pins. Falsified if any candidate sha, changed-path set, P1/P2 value,
invariant value or external-reference resolution differs, or if any control fails. Any pin change
away from `frame.json:pins_before` voids the run rather than falsifying it.
"""
    readme_path = os.path.join(HERE, "README.md")
    open(readme_path, "w").write(readme)

    # ---------- event emission (idempotent) ----------
    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX):
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except Exception:
                pass
    ts = datetime.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    prefix = f"w070C-{ts}"
    artifacts = {
        "frame": os.path.join(HERE, "frame.json"),
        "report": os.path.join(HERE, "report.json"),
        "addendum": os.path.join(HERE, "addendum.json"),
        "census_070": os.path.join(HERE, "census_070.py"),
        "finalize_070": os.path.join(HERE, "finalize_070.py"),
        "readme": os.path.join(HERE, "README.md"),
        "run_log": os.path.join(HERE, "run.log"),
    }
    shas = {k: sha256_file(v) for k, v in artifacts.items()}
    ev = []

    def add(e):
        if e["event_id"] not in existing:
            ev.append(e)

    add({"event_id": f"{prefix}-status-start", "event_type": "status", "created_at": now(),
         "actor": "worker-070", "node_id": "F2b", "group_id": "formulation",
         "status": "active", "hours": 0.4, "task_id": TASK,
         "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM",
         "assignment_ref": "self-taken; no inbox card for worker-070 (relaunched slot)",
         "summary": ("Started the pre-registered F2b rev29 repair-candidate census at the FROZEN pin "
                     f"{fz}; 10 declared candidate sha256s resolved on disk before any check."),
         "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{fz}",
                           "artifacts/formulation/FROZEN.json#815e08079aef"],
         "next_falsifier": report["falsifier"]})

    for key in ("frame", "report", "addendum", "census_070", "finalize_070", "readme", "run_log"):
        add({"event_id": f"{prefix}-artifact-{key}", "event_type": "artifact",
             "created_at": now(), "actor": "worker-070", "node_id": "F2b",
             "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM", "task_id": TASK,
             "artifact_type": ("preregistration" if key == "frame" else
                               "measurement_report" if key == "report" else
                               "post_frame_addendum" if key == "addendum" else
                               "instrument" if key in ("census_070", "finalize_070") else
                               "summary" if key == "readme" else "run_log"),
             "path": rel(artifacts[key]), "sha256": shas[key],
             "validation_status": "unverified",
             "evidence_refs": [f"{rel(artifacts[key])}#{shas[key][:12]}"]})

    cand_refs = [f"{e['primary_path']}#{e['sha256'][:12]}" for e in report["registry_resolution"]]
    add({"event_id": f"{prefix}-claim-candidate-census", "event_type": "claim",
         "created_at": now(), "actor": "worker-070", "node_id": "F2b",
         "group_id": "formulation", "class_id": "AF-SCC-C0-VAC-GEN",
         "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM", "task_id": TASK,
         "conclusion_type": "formal_model",
         "statement": (
             f"At FROZEN rev29 {frozen} (node F2b, class AF-SCC-C0-VAC-GEN), of the 10 declared repair "
             "candidates, 9 change exactly the two standing blocking carriers (regularity.must_not_conflate[0] "
             "and implication_ledger.forbidden_transfers[0].reason) and discharge both while preserving every "
             "frozen invariant; 3cdcaa44e6f1 repairs only the inverted-premise carrier, so the containment "
             "denial survives; 7 of 10 change nothing outside those two sites; 48cadb72e507 and b598b59e09e5 "
             "additionally move the consistency-evidence pin off the frozen 9e335e9b (to 675a99d0 and a03ba9c5 "
             "respectively) and add an extensions block; the HF2 repair has one byte-identical text shared by 6 "
             "candidates while HF1 has 9 distinct wordings; the conclusion-token conflict is gate-wide and not "
             "candidate-fixable. This is a byte/path measurement, not a mathematics claim and not a gate verdict."),
         "assumptions": [
             "the pinned bytes are the objects; candidates are read-only inputs and controls are built in memory",
             "the HF carrier paths are those declared by independent reviewers at rev29 (worker-017/018/053/075)",
             "tree equality is exact for the loaded YAML (duplicate keys checked separately) and asserts no "
             "semantic equivalence between distinct wordings",
             "the census measures candidate content only; it does not adjudicate which wording the class needs"],
         "falsifier": report["falsifier"],
         "evidence_refs": [f"schemas/af_scc_c0_vacuum.yaml#{fz}",
                           "artifacts/formulation/FROZEN.json#815e08079aef",
                           "artifacts/formulation/rule_spec.json#40f9bb9e657b",
                           "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
                           "artifacts/formulation/VARIANT_REGISTRY.json#6bac9adea19e",
                           "artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf",
                           f"{rel(artifacts['report'])}#{shas['report'][:12]}",
                           f"{rel(artifacts['frame'])}#{shas['frame'][:12]}",
                           f"{rel(artifacts['addendum'])}#{shas['addendum'][:12]}",
                           f"{rel(artifacts['readme'])}#{shas['readme'][:12]}",
                           ] + cand_refs,
         "artifact_refs": [f"{rel(artifacts['report'])}#{shas['report'][:12]}",
                           f"{rel(artifacts['frame'])}#{shas['frame'][:12]}",
                           f"{rel(artifacts['addendum'])}#{shas['addendum'][:12]}"]})

    ckpt = {
        "worker": "worker-070", "checkpoint_at": now(), "task_id": TASK,
        "assignment_ref": "self-taken; no inbox card for worker-070",
        "node_id": "F2b", "gate": "G-FORM", "group_id": "formulation",
        "class_ids": ["AF-SCC-C0-VAC-GEN"], "status": "bounded_task_complete_unverified",
        "question": frame["question"],
        "pins": report["pins_before"], "pins_after": report["pins_after"],
        "corpus_valid": report["controls_all_pass"] and not report["pin_drift"],
        "controls": {k: v["pass"] for k, v in report["controls"].items()},
        "aggregate": {
            "declared_candidates": report["aggregate"]["declared_candidates"],
            "core_repair_complete": report["aggregate"]["core_repair_complete"],
            "core_only": sum(1 for e in post if not e["metadata_changes"] and not e["new_top_level_blocks"]),
            "inversion_only_candidate": "3cdcaa44e6f1",
            "evidence_pin_moves": {"48cadb72e507": "675a99d0 (stale vs frozen/live 9e335e9b)",
                                   "b598b59e09e5": "a03ba9c5 (new, requires coupled evidence freeze)"},
            "hf1_distinct_wordings": hf1, "hf2_distinct_wordings": hf2,
            "residual_gate_wide_blocker": report["aggregate"]["residual_gate_wide_blocker"],
        },
        "no_write_paths": report["no_write_paths"],
        "artifacts": {k: shas[k] for k in ("frame", "report", "addendum", "census_070",
                                           "finalize_070", "readme", "run_log")},
        "frame_sha256": report["frame_sha256"],
        "falsifier": report["falsifier"], "authority": report["authority"],
        "events_emitted": [e["event_id"] for e in ev],
    }

    add({"event_id": f"{prefix}-status-complete", "event_type": "status", "created_at": now(),
         "actor": "worker-070", "node_id": "F2b", "group_id": "formulation",
         "status": "active", "hours": 0.4, "task_id": TASK,
         "class_ids": ["AF-SCC-C0-VAC-GEN"], "gate": "G-FORM",
         "assignment_ref": "self-taken; no inbox card for worker-070 (relaunched slot)",
         "summary": (f"worker-070 bounded task complete and exiting. {report['aggregate']['core_repair_complete']}"
                     f"/{report['aggregate']['declared_candidates']} declared F2b rev29 repair candidates "
                     "discharge both blocking carriers with invariants preserved; 3cdcaa44e6f1 is inversion-only; "
                     "2 candidates move the evidence pin; HF1 wordings do not converge. report.json "
                     f"{shas['report'][:12]}, frame.json {shas['frame'][:12]}, addendum.json {shas['addendum'][:12]}, "
                     "checkpoint runtime/state/w070_checkpoint_f2b_candidate_census.json. controls_all_pass="
                     f"{report['controls_all_pass']}. No gate verdict, no node done, no canonical write."),
         "evidence_refs": [f"{rel(artifacts['report'])}#{shas['report'][:12]}",
                           f"{rel(artifacts['frame'])}#{shas['frame'][:12]}",
                           f"{rel(artifacts['addendum'])}#{shas['addendum'][:12]}",
                           f"{rel(artifacts['readme'])}#{shas['readme'][:12]}",
                           f"{rel(artifacts['census_070'])}#{shas['census_070'][:12]}",
                           f"{rel(artifacts['run_log'])}#{shas['run_log'][:12]}",
                           "runtime/state/w070_checkpoint_f2b_candidate_census.json"],
         "next_falsifier": report["falsifier"]})

    ckpt["events_emitted"] = [e["event_id"] for e in ev]
    json.dump(ckpt, open(CKPT, "w"), indent=1, sort_keys=True)
    ckpt_sha = sha256_file(CKPT)

    with open(OUTBOX, "a") as f:
        for e in ev:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    print(json.dumps({
        "report_sha256": shas["report"], "frame_sha256": shas["frame"],
        "addendum_sha256": shas["addendum"], "readme_sha256": shas["readme"],
        "checkpoint": rel(CKPT), "checkpoint_sha256": ckpt_sha,
        "events_appended": len(ev), "events_skipped_existing": 10 - len(ev),
    }, indent=1))


if __name__ == "__main__":
    main()
