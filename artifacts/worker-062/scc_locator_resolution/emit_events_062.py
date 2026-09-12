#!/usr/bin/env python3
"""Emit worker-062 events, README, sha256 sidecars and the worker checkpoint.

Task: W062-SCC-LOCATOR-RESOLVABILITY-01 (node L1 / gate G-LIT / primary class
AF-SCC-C0-VAC-GEN).  Idempotent: if EMITTED.json exists and binds the current
resolution.json sha256, nothing is written and the script exits 0.

Emits to comms/outbox/worker-062.jsonl (append):
  artifact x3 (resolution.json, classify_scc_locators.py, README.md)
  claim    x1 (conclusion_type formal_model)
  review   x1 (worker-level verdict on the frozen L1 exact_locator column)
  status   x1 (node L1, active)
Writes checkpoint: runtime/state/w062_checkpoint_<token>.json,
appends runtime/state/w062_checkpoints.jsonl, refreshes runtime/state/w062_checkpoint.json.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ART_DIR = "artifacts/worker-062/scc_locator_resolution"
OUTBOX = "comms/outbox/worker-062.jsonl"
CHECKPOINT_DIR = "runtime/state"
TZ = timezone(timedelta(hours=8))
PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
EVIDENCE = f"ledger/citation_audit.csv#{PIN[:12]}"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now():
    return datetime.now(TZ)


def now_iso() -> str:
    return now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def load_schema_validator():
    spec = importlib.util.spec_from_file_location("ai4math_schemas", os.path.join(ROOT, "research_map/schemas.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ai4math_schemas"] = mod
    spec.loader.exec_module(mod)
    return mod.validate_event


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_sha256_sidecar(path):
    digest = sha256_file(path)
    base = os.path.basename(path)
    write_text(path + ".sha256", f"{digest}  {base}\n")
    return digest


def build_readme(report) -> str:
    c = report["counts"]
    scope = report["scope"]
    ctrl = report["controls"]
    g = report["cross_checks"]["global_all97_vs_lead_adjudication"]
    rel = g["annotation_stripped_sensitivity"]
    worst = ", ".join(f"`{x[:80]}` x{c['weak_worst_sharing']}" for x in c["weak_worst_locators"])
    lines = [
        "# W062 — SCC-side `exact_locator` resolvability map",
        "",
        f"- **Task:** {report['artifact_id']} (worker-062, bounded class-bound task; no inbox card existed for this slot)",
        f"- **Node / gate / class:** L1 / G-LIT / `AF-SCC-C0-VAC-GEN` (SCC-side scope)",
        f"- **Pin:** `ledger/citation_audit.csv` sha256 `{report['pins']['ledger/citation_audit.csv']['sha256_measured']}`",
        f"- **Created:** {report['created_at']}",
        "",
        "## Result",
        "",
        f"| SCC-side rows | direct record locator | weak (`exact_locator` is not a record locator) |",
        "|---|---:|---:|",
        f"| {scope['scc_rows']} | {c['direct_record_locator']} | {c['weak']} |",
        "",
        f"- Weak categories: `search_or_query_endpoint` {c['by_category']['search_or_query_endpoint']}, "
        f"`elided_or_truncated` {c['by_category']['elided_or_truncated']}; "
        f"weak rows by verification method: {c['weak_by_verification_method']}.",
        f"- Weak rows share {c['weak_distinct_locator_strings']} distinct locator strings; worst sharing "
        f"{c['weak_worst_sharing']} rows ({worst}).",
        f"- Repair proposals: {c['repair_proposed']}/{c['weak']} weak rows have a replacement available from a value "
        f"already in the row (`evidence_url` / `doi` / `arxiv_id` / `url`); {c['repair_unavailable']} unavailable. "
        "No value was invented and no ledger cell was edited.",
        "",
        "## Controls (all must pass; run exits 4 otherwise)",
        "",
        f"- C1 positive (7 synthetic record locators): {'PASS' if ctrl['C1_positive_record_locators']['pass'] else 'FAIL'}",
        f"- C2 negative mutants (7 search/truncated/empty): {'PASS' if ctrl['C2_negative_mutants_not_direct']['pass'] else 'FAIL'}",
        f"- C3 scope/disjointness (34 rows, disjoint from worker-050's WCC scope): {'PASS' if ctrl['C3_scope_and_disjointness']['pass'] else 'FAIL'}",
        f"- C4 hash-guard teeth (byte-mutated ledger -> exit 3): {'PASS' if ctrl['C4_hash_guard_teeth']['pass'] else 'FAIL'}",
        f"- C5 cross-instrument agreement with worker-050 on the 12 exact-match WCC rows: "
        f"{ctrl['C5_cross_instrument_worker050_wcc12']['agree']}/12 "
        f"{'PASS' if ctrl['C5_cross_instrument_worker050_wcc12']['pass'] else 'FAIL'}",
        "",
        "## Cross-checks against published aggregates",
        "",
        f"- Strict classifier over all 97 rows: {g['measured']['weak']} weak / {g['measured']['direct']} direct, "
        f"{g['measured']['distinct_weak_locators']} distinct weak locators, worst sharing {g['measured']['worst_sharing']}.",
        f"- astra-lead-literature's adjudication claims {g['lead_adjudication_claim']['weak_expected']} weak / "
        f"{g['lead_adjudication_claim']['direct_expected']} direct, "
        f"{g['lead_adjudication_claim']['distinct_weak_locators_expected']} distinct, worst "
        f"{g['lead_adjudication_claim']['worst_sharing_expected']}.",
        f"- After stripping one trailing parenthetical annotation from each cell (the only relaxed rule): "
        f"{rel['measured']['weak']} weak / {rel['measured']['direct']} direct / "
        f"{rel['measured']['distinct_weak_locators']} distinct / worst {rel['measured']['worst_sharing']} "
        f"-> matches the lead aggregate: {rel['matches_lead_aggregate']}.",
        f"- Adjudication of the single strict/relaxed difference: {rel['adjudication']}",
        "",
        "## Limits and falsifiers",
        "",
        f"- {report['scope_limit']}",
        f"- {report['fetch_policy']}",
    ]
    for f_ in report["falsifiers"]:
        lines.append(f"- {f_}")
    lines += [
        "",
        "Authority: worker evidence only — not a ledger edit, not a gate verdict, not a node completion, "
        "not a `validation_status`.",
        "",
    ]
    return "\n".join(lines)


def find_instance_id() -> str:
    base = os.path.join(ROOT, "runtime/instances")
    cands = []
    if os.path.isdir(base):
        for name in os.listdir(base):
            if name.startswith("worker-062-"):
                meta = os.path.join(base, name, "meta.json")
                if os.path.isfile(meta):
                    cands.append((os.path.getmtime(meta), read_json(meta).get("id", name)))
    return max(cands)[1] if cands else "worker-062-unknown"


def main() -> int:
    validate_event = load_schema_validator()
    res_path = os.path.join(ROOT, ART_DIR, "resolution.json")
    runner_path = os.path.join(ROOT, ART_DIR, "classify_scc_locators.py")
    report = read_json(res_path)
    emitted_marker = os.path.join(ROOT, ART_DIR, "EMITTED.json")
    res_hash = sha256_file(res_path)
    if os.path.isfile(emitted_marker):
        prev = read_json(emitted_marker)
        if prev.get("resolution_sha256") == res_hash:
            print(json.dumps({"status": "already_emitted", "resolution_sha256": res_hash,
                              "events": prev.get("events_emitted")}, indent=2))
            return 0

    ts = now_iso()
    token = now().strftime("%Y%m%dT%H%M%S")
    readme_path = os.path.join(ROOT, ART_DIR, "README.md")
    write_text(readme_path, build_readme(report))

    res_hash = write_sha256_sidecar(res_path)
    runner_hash = write_sha256_sidecar(runner_path)
    readme_hash = write_sha256_sidecar(readme_path)
    ref = lambda p, h: f"{p}#{h[:12]}"
    res_rel = f"{ART_DIR}/resolution.json"
    runner_rel = f"{ART_DIR}/classify_scc_locators.py"
    readme_rel = f"{ART_DIR}/README.md"
    w050_ref = "artifacts/worker-050/wcc_locator_resolution/resolution.json#8ce6895f0524"
    c = report["counts"]
    ctrl = report["controls"]
    g = report["cross_checks"]["global_all97_vs_lead_adjudication"]
    rel = g["annotation_stripped_sensitivity"]
    ev_base = f"w062-{token}"

    evidence_refs = [EVIDENCE, ref(res_rel, res_hash), ref(runner_rel, runner_hash), w050_ref]
    false_short = ("Any SCC-side row whose exact_locator does address one record (or vice versa), any drift of "
                   "ledger/citation_audit.csv away from the pinned sha256, or a re-fetch that fails to return the "
                   "cited work voids the corresponding row or the whole table.")
    artifact_common = {"actor": "worker-062", "node_id": "L1", "gate": "G-LIT",
                       "class_id": "AF-SCC-C0-VAC-GEN",
                       "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
                       "validation_status": "unverified"}

    events = [
        dict(artifact_common, event_id=f"{ev_base}-artifact-resolution", event_type="artifact",
             created_at=ts, artifact_type="class_bound_locator_resolvability_map",
             path=res_rel, sha256=res_hash,
             summary=(f"W062-SCC-LOCATOR-RESOLVABILITY-01 at pinned ledger sha {PIN[:12]}: 34 SCC-side rows "
                      f"classified, {c['direct_record_locator']} direct record locators, {c['weak']} weak, "
                      f"{c['repair_proposed']} replacement locators proposed from row fields, 0 ledger edits."),
             artifact_refs=[ref(res_rel, res_hash)], evidence_refs=evidence_refs, falsifier=false_short),
        dict(artifact_common, event_id=f"{ev_base}-artifact-runner", event_type="artifact",
             created_at=ts, artifact_type="reproducible_runner",
             path=runner_rel, sha256=runner_hash,
             summary=("Deterministic classifier + repair proposer; pins the ledger sha256 and exits 3 on mismatch, "
                      "exits 4 if any of the five harness controls fails."),
             artifact_refs=[ref(runner_rel, runner_hash)], evidence_refs=evidence_refs,
             falsifier="Re-run produces different category/proposal fields at the same pinned ledger hash, or the hash guard does not exit 3 on a mutated copy."),
        dict(artifact_common, event_id=f"{ev_base}-artifact-readme", event_type="artifact",
             created_at=ts, artifact_type="documentation",
             path=readme_rel, sha256=readme_hash,
             summary="Human-readable summary of the SCC-side locator map, controls and cross-checks.",
             artifact_refs=[ref(readme_rel, readme_hash)], evidence_refs=evidence_refs,
             falsifier="README numbers disagree with resolution.json at the same sha256."),
        {"event_id": f"{ev_base}-claim", "event_type": "claim", "created_at": ts, "actor": "worker-062",
         "node_id": "L1", "gate": "G-LIT", "class_id": "AF-SCC-C0-VAC-GEN",
         "conclusion_type": "formal_model",
         "statement": (f"At ledger/citation_audit.csv sha256 {PIN}, {c['direct_record_locator']} of {report['scope']['scc_rows']} "
                       f"SCC-side rows (class_mapping contains AF-SCC-C0-VAC-GEN or AF-SCC-C2-VAC-GEN) carry a direct "
                       f"record locator in exact_locator and {c['weak']} do not ({c['by_category']['search_or_query_endpoint']} "
                       f"query endpoints, {c['by_category']['elided_or_truncated']} truncated); all {c['weak']} weak rows have a "
                       f"replacement available from a value already in the row. An independent classifier reproduces "
                       f"worker-050's WCC 12/12 per-row split and, after stripping one trailing cell annotation, the lead's "
                       f"global 67 weak / 30 direct / 43 distinct / worst-7 aggregate."),
         "assumptions": ["only the exact_locator field is under test; citation quality is not assessed",
                         "no live fetch was performed, so the claim is syntactic (locator shape), not resolvability",
                         "the ledger hash was stable during the run",
                         "ledger/citation_audit.csv was read-only; no cell was edited"],
         "falsifier": false_short,
         "evidence_refs": evidence_refs,
         "artifact_refs": [ref(res_rel, res_hash), ref(runner_rel, runner_hash)],
         "class_ids": artifact_common["class_ids"],
         "reviewed_sha256": PIN},
        {"event_id": f"{ev_base}-review", "event_type": "review", "created_at": ts, "actor": "worker-062",
         "reviewer": "worker-062", "reviewer_role": "bounded execution worker (not the ledger author)",
         "target_id": "L1", "node_id": "L1", "gate": "G-LIT", "class_id": "AF-SCC-C0-VAC-GEN",
         "reviewed_path": "ledger/citation_audit.csv", "reviewed_sha256": PIN,
         "verdict": "revise", "score": 3,
         "hard_failures": [{
             "id": "HF-062-01", "severity": "major", "class_id": "AF-SCC-C0-VAC-GEN",
             "name": "scc_side_exact_locator_is_not_a_record_locator",
             "finding": (f"{c['weak']} of {report['scope']['scc_rows']} SCC-side rows carry a search-query or truncated URL in "
                         f"exact_locator, so the column fails a per-row-uniqueness reading of the G-LIT criterion "
                         f"'ledger rows have resolvable locators' on the SCC side."),
             "evidence": [EVIDENCE, ref(res_rel, res_hash), w050_ref],
             "mitigation_available": (f"{c['repair_proposed']}/{c['weak']} weak rows have a direct locator already present in "
                                      f"evidence_url/doi/arxiv_id; the rewrite is metadata-only but moves the L1 hash and voids "
                                      f"the frozen-hash spot checks, so it needs a controller freeze decision."),
             "falsifier": "A row listed weak whose exact_locator does resolve to exactly one record, or a re-fetch of a proposal returning a different work."}],
         "findings": [
             {"id": "P-062-01", "severity": "positive",
              "finding": (f"{c['direct_record_locator']}/34 SCC rows already carry a direct record locator; all {c['repair_proposed']} "
                          f"proposals use values already in the row, so no ledger content is invented."),
              "evidence": [ref(res_rel, res_hash)]},
             {"id": "P-062-02", "severity": "positive",
              "finding": ("The same instrument agrees 12/12 with worker-050's independently authored WCC locator map on the "
                          "12 exact-match WCC rows (control C5)."),
              "evidence": [w050_ref, ref(res_rel, res_hash)]},
             {"id": "A-062-01", "severity": "advisory",
              "finding": (f"Strict global classification gives {g['measured']['weak']} weak / {g['measured']['direct']} direct vs the "
                          f"lead's {g['lead_adjudication_claim']['weak_expected']}/{g['lead_adjudication_claim']['direct_expected']}; the single "
                          f"difference is SRC-090 (direct PDF plus page annotation, not an SCC row). Stripping one trailing "
                          f"parenthetical annotation reproduces {rel['measured']['weak']}/{rel['measured']['direct']}/"
                          f"{rel['measured']['distinct_weak_locators']}/worst-{rel['measured']['worst_sharing']} exactly."),
              "evidence": [EVIDENCE, ref(res_rel, res_hash)]},
             {"id": "A-062-02", "severity": "advisory",
              "finding": (f"Within the SCC scope, {c['weak']} weak rows share only {c['weak_distinct_locator_strings']} distinct strings; "
                          f"the worst string is reused by {c['weak_worst_sharing']} rows, confirming that the column is provenance, not identity."),
              "evidence": [ref(res_rel, res_hash)]},
             {"id": "A-062-03", "severity": "advisory",
              "finding": ("evidence_url is a record locator for all 34 SCC rows, so a metadata-only rewrite is available; it moves "
                          "the L1 hash and voids the frozen-hash spot checks, matching the lead's freeze-first decision (BL-4)."),
              "evidence": [ref(res_rel, res_hash), EVIDENCE]}],
         "evidence_refs": evidence_refs,
         "falsifier": false_short},
        {"event_id": f"{ev_base}-status", "event_type": "status", "created_at": ts, "actor": "worker-062",
         "node_id": "L1", "gate": "G-LIT", "class_id": "AF-SCC-C0-VAC-GEN", "status": "active", "hours": 0.5,
         "summary": (f"No assignment card exists in comms/inbox for worker-062 (relaunched slot). Took one bounded class-bound "
                     f"task, W062-SCC-LOCATOR-RESOLVABILITY-01: SCC-side exact_locator resolvability map at frozen L1 sha "
                     f"{PIN[:12]}. Result: {c['direct_record_locator']}/34 direct, {c['weak']}/34 weak, {c['repair_proposed']} replacements "
                     f"proposed, all 5 harness controls pass (incl. 12/12 agreement with worker-050), global aggregate reproduced "
                     f"after annotation stripping; worker verdict revise 3 with one major locator-hygiene hard failure. No ledger edit, "
                     f"no gate verdict, no node completion claimed."),
         "artifact": res_rel, "reviewed_sha256": PIN,
         "artifact_refs": [ref(res_rel, res_hash), ref(runner_rel, runner_hash), ref(readme_rel, readme_hash)],
         "evidence_refs": evidence_refs,
         "next_falsifier": report["next_falsifier"]},
    ]

    for ev in events:
        validate_event(ev)

    outbox_path = os.path.join(ROOT, OUTBOX)
    existing = set()
    if os.path.isfile(outbox_path):
        with open(outbox_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except json.JSONDecodeError:
                    pass
    appended = []
    with open(outbox_path, "a", encoding="utf-8") as f:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, sort_keys=True) + "\n")
            appended.append(ev["event_id"])

    instance_id = find_instance_id()
    map_path = os.path.join(ROOT, "research_map/research_map.json")
    checkpoint = {
        "checkpoint_id": f"w062-ckpt-{token}",
        "instance": instance_id,
        "actor": "worker-062",
        "role": "bounded execution worker",
        "created_at": ts,
        "task": "W062-SCC-LOCATOR-RESOLVABILITY-01 -- SCC-side exact_locator resolvability map",
        "node_id": "L1", "gate": "G-LIT",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": artifact_common["class_ids"],
        "inputs": {"ledger/citation_audit.csv": PIN,
                   "ledger/citation_audit.csv_measured": report["pins"]["ledger/citation_audit.csv"]["sha256_measured"],
                   "research_map/research_map.json_at_checkpoint": sha256_file(map_path) if os.path.isfile(map_path) else None},
        "artifacts": [{"path": res_rel, "sha256": res_hash},
                      {"path": runner_rel, "sha256": runner_hash},
                      {"path": readme_rel, "sha256": readme_hash}],
        "result": {"scc_rows": report["scope"]["scc_rows"],
                   "direct_record_locator": c["direct_record_locator"], "weak": c["weak"],
                   "repair_proposed": c["repair_proposed"], "repair_unavailable": c["repair_unavailable"],
                   "controls_pass": ctrl["all_harness_controls_pass"],
                   "worker050_wcc12_agree": ctrl["C5_cross_instrument_worker050_wcc12"]["agree"],
                   "global_strict": g["measured"],
                   "global_annotation_stripped_matches_lead": rel["matches_lead_aggregate"],
                   "verdict": "revise 3 (HF-062-01)"},
        "events_emitted": appended,
        "evidence_refs": evidence_refs + [f"runtime/state/w062_checkpoint_{token}.json"],
        "status": "task_complete_pending_ingest",
        "authority_note": "Worker evidence only; cannot set a gate verdict, status=done, or validation_status=passed.",
        "next_falsifier": report["next_falsifier"],
    }
    ckpt_path = os.path.join(ROOT, CHECKPOINT_DIR, f"w062_checkpoint_{token}.json")
    write_text(ckpt_path, json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
    with open(os.path.join(ROOT, CHECKPOINT_DIR, "w062_checkpoints.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(checkpoint, sort_keys=True) + "\n")
    write_text(os.path.join(ROOT, CHECKPOINT_DIR, "w062_checkpoint.json"),
               json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")

    marker = {"artifact_id": report["artifact_id"], "emitted_at": ts, "resolution_sha256": res_hash,
              "runner_sha256": runner_hash, "readme_sha256": readme_hash,
              "events_emitted": [ev["event_id"] for ev in events], "appended_this_run": appended,
              "checkpoint": f"runtime/state/w062_checkpoint_{token}.json"}
    write_text(emitted_marker, json.dumps(marker, indent=2, sort_keys=True) + "\n")

    print(json.dumps({"status": "emitted", "appended": appended, "checkpoint": marker["checkpoint"],
                      "resolution_sha256": res_hash, "runner_sha256": runner_hash,
                      "readme_sha256": readme_hash}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
