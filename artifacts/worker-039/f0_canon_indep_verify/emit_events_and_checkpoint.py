#!/usr/bin/env python3
"""Emit W039-F0-CANON-INDEP-VERIFY-01 deliverables, events and worker checkpoint.

Writes (inside this task directory, one runtime/state copy, and the worker outbox):
  entry_hashes.json, CHECKPOINT.json, SHA256SUMS
  runtime/state/w039_f0_canon_indep_verify_checkpoint.json
  comms/outbox/deepseek-flash-39.jsonl   (append, idempotent by event_id)

Validates every event with research_map.schemas.validate_event before appending.
No canonical artifact is written; no gate verdict / node status is set.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))
import schemas  # noqa: E402

HERE = Path(__file__).resolve().parent
OUTBOX = ROOT / "comms/outbox/deepseek-flash-39.jsonl"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).replace(microsecond=0).isoformat()
STAMP = NOW.replace(":", "").replace("-", "")[:15]

TASK = "W039-F0-CANON-INDEP-VERIFY-01"
TARGET_TASK = "W042-F0-CANON-CANDIDATE-08"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]

PINS = {
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}
TARGET_BUNDLE = {
    "W042_report": "artifacts/worker-042/f0_canon_candidate/report.json",
    "W042_candidate_A": "artifacts/worker-042/f0_canon_candidate/CANDIDATE_A_formulation_taxonomy.yaml",
    "W042_candidate_B": "artifacts/worker-042/f0_canon_candidate/CANDIDATE_B_formulation_taxonomy.yaml",
    "W042_events_snapshot": "artifacts/worker-042/f0_canon_candidate/snapshot/research_map/events.jsonl",
    "rule_spec": "artifacts/formulation/rule_spec.json",
    "check_taxonomy_consistency": "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "worker019_results": "artifacts/worker-019/f2a_review/results.json",
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


report_p = HERE / "report.json"
script_p = HERE / "verify_f0_canon_039.py"
readme_p = HERE / "README.md"
run1_p = HERE / "report.run1.json"
report = json.loads(report_p.read_text())

deliverables = {
    "report.json": {"sha256": sha(report_p), "bytes": report_p.stat().st_size},
    "verify_f0_canon_039.py": {"sha256": sha(script_p), "bytes": script_p.stat().st_size},
    "README.md": {"sha256": sha(readme_p), "bytes": readme_p.stat().st_size},
    "report.run1.json": {"sha256": sha(run1_p), "bytes": run1_p.stat().st_size},
}
pins_measured = {rel: {"declared": want, "measured": sha(ROOT / rel),
                       "match": sha(ROOT / rel) == want} for rel, want in PINS.items()}
target_files = {name: {"path": rel, "sha256": sha(ROOT / rel), "bytes": (ROOT / rel).stat().st_size}
                for name, rel in TARGET_BUNDLE.items()}

entry = {
    "schema": "w039-entry-hashes/v1",
    "task_id": TASK,
    "actor": "worker-039",
    "measured_at": NOW,
    "canonical_pins": pins_measured,
    "target_bundle": target_files,
    "deliverables": deliverables,
    "verdict": report["verdict"],
    "drift": [],
    "note": ("canonical pins re-measured read-only at T0 and T1 by verify_f0_canon_039.py "
             "(10/10 declared matches, drift []); no canonical artifact written"),
}
(HERE / "entry_hashes.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n")
entry_sha = sha(HERE / "entry_hashes.json")
deliverables["entry_hashes.json"] = {"sha256": entry_sha,
                                     "bytes": (HERE / "entry_hashes.json").stat().st_size}

kv = report["checks"]["V9_BLAST_RADIUS"]
checkpoint = {
    "schema": "w039-worker-checkpoint/v1",
    "task_id": TASK,
    "actor": "worker-039",
    "created_at": NOW,
    "state": "complete_worker_level",
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": CLASS_IDS,
    "node_id": "F0",
    "gate": "G-F0",
    "secondary_gate": "G-FORM",
    "target": {"task_id": TARGET_TASK,
               "artifact": "artifacts/worker-042/f0_canon_candidate/report.json#21b7598096bb",
               "report_sha256": target_files["W042_report"]["sha256"],
               "candidate_A_sha256": target_files["W042_candidate_A"]["sha256"],
               "candidate_B_sha256": target_files["W042_candidate_B"]["sha256"]},
    "pins": {k: v["measured"] for k, v in pins_measured.items()},
    "verdict": report["verdict"],
    "counts": {"checks": len(report["checks"]),
               "pass": sum(1 for c in report["checks"].values() if c["status"] == "pass"),
               "fail": sum(1 for c in report["checks"].values() if c["status"] != "pass"),
               "controls": 7, "controls_fired": 7},
    "key_measurements": {
        "frozen_alias_use_sites": 6,
        "frozen_full_alias_occurrences": 7,
        "frozen_abbreviations": 1,
        "candidate_A_rebuild_matches_bytes": True,
        "candidate_B_text_residue": 0,
        "blast_radius_pinned_snapshot": kv["pinned_total"],
        "blast_radius_live_at": kv["live_events_sha256"][:12],
        "blast_radius_live": kv["live_total"],
    },
    "findings": [f["id"] for f in report["findings"]],
    "deliverables": deliverables,
    "next_falsifier": report["falsifier"],
    "authority_note": report["authority_note"],
    "non_canonical": True,
}
(HERE / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
checkpoint_sha = sha(HERE / "CHECKPOINT.json")
deliverables["CHECKPOINT.json"] = {"sha256": checkpoint_sha,
                                   "bytes": (HERE / "CHECKPOINT.json").stat().st_size}

runtime_copy = ROOT / "runtime/state/w039_f0_canon_indep_verify_checkpoint.json"
runtime_copy.write_text((HERE / "CHECKPOINT.json").read_text())
assert sha(runtime_copy) == checkpoint_sha

sums_lines = [f"{v['sha256']}  {k}" for k, v in sorted(deliverables.items())]
sums_lines.append(f"{sha(runtime_copy)}  runtime/state/w039_f0_canon_indep_verify_checkpoint.json")
(HERE / "SHA256SUMS").write_text("\n".join(sums_lines) + "\n")

E = f"w039-f0canon-{STAMP}"
BASE = [
    "artifacts/worker-039/f0_canon_indep_verify/report.json#sha256:" + deliverables["report.json"]["sha256"],
    "artifacts/worker-039/f0_canon_indep_verify/verify_f0_canon_039.py#sha256:" + deliverables["verify_f0_canon_039.py"]["sha256"],
    "artifacts/worker-039/f0_canon_indep_verify/README.md#sha256:" + deliverables["README.md"]["sha256"],
    "artifacts/worker-039/f0_canon_indep_verify/entry_hashes.json#sha256:" + entry_sha,
    "artifacts/worker-042/f0_canon_candidate/report.json#sha256:" + target_files["W042_report"]["sha256"],
    "artifacts/worker-042/f0_canon_candidate/CANDIDATE_A_formulation_taxonomy.yaml#sha256:" + target_files["W042_candidate_A"]["sha256"],
    "artifacts/worker-042/f0_canon_candidate/CANDIDATE_B_formulation_taxonomy.yaml#sha256:" + target_files["W042_candidate_B"]["sha256"],
    "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
    "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534",
    "artifacts/formulation/rule_spec.json#40f9bb9e657b",
]
NEXT_FALSIFIER = report["falsifier"]

events = []


def artifact(name, atype, path, sha256, summary):
    events.append({
        "event_id": f"{E}-artifact-{name}",
        "event_type": "artifact",
        "created_at": NOW,
        "actor": "worker-039",
        "group_id": "formulation",
        "node_id": "F0",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": CLASS_IDS,
        "gate": "G-F0",
        "task_id": TASK,
        "artifact_type": atype,
        "path": path,
        "sha256": sha256,
        "validation_status": "unverified",
        "summary": summary,
        "evidence_refs": BASE,
    })


artifact("report", "independent_verification_report",
         "artifacts/worker-039/f0_canon_indep_verify/report.json",
         deliverables["report.json"]["sha256"],
         "Independent non-author verification of W042-F0-CANON-CANDIDATE-08: verdict REPRODUCED, 10/10 checks pass, 7/7 controls fire, no correction to the W042 numbers. Frozen F0 0abb9ed8a961 carries exactly 6 alias use sites at the six declared paths, 7 full alias occurrences (6 quoted + 1 prose) and one '_C0' abbreviation; my own quoted-substitution rebuild reproduces candidate A byte-for-byte (ef180b5cfe0a); candidate B is residue-free with its diff vs A confined to field_vocabulary.conclusion_type.rule; canonical-resolved semantics are identical across frozen/A/B with C0!=C2; consumer rules diverge on frozen (literal FAIL) and converge on A/B; checked checker exit 0 on all three with 0 field_vocabulary references; blast radius exactly 817 on the W042 pinned events snapshot.")
artifact("checker", "verifier_script",
         "artifacts/worker-039/f0_canon_indep_verify/verify_f0_canon_039.py",
         deliverables["verify_f0_canon_039.py"]["sha256"],
         "Deterministic stdlib+PyYAML own instrument, no worker-042 code imported: strict duplicate-key loader, structural use-site census against VOCAB_ALIASES, quoted/unquoted residue census, byte-oracle rebuild of candidate A, flattened parsed-tree diffs, canonical-resolved semantics table, worker-019 B1 and worker-097 alias-aware consumer replay, sandboxed end-to-end replay of the pinned consistency checker, event-snapshot blast radius, and 7 mutation/determinism/pin controls. Exit 3 on pin drift; two runs byte-identical modulo created_at and the two stamped live-stream fields.")
artifact("readme", "README",
         "artifacts/worker-039/f0_canon_indep_verify/README.md",
         deliverables["README.md"]["sha256"],
         "Task record: unclaimed-gap argument, pins, method, V1-V10 result table, disposition of the W042 claim, instrument self-erratum (two first-run defects, fixed before the reported run), falsifier, limits, reproduction.")
artifact("run1", "independent_verification_report_run1",
         "artifacts/worker-039/f0_canon_indep_verify/report.run1.json",
         deliverables["report.run1.json"]["sha256"],
         "Preserved run 1; byte-identical to report.json modulo created_at and the two stamped live-stream fields (live_events_sha256, live_total).")
artifact("entry-hashes", "entry_hashes",
         "artifacts/worker-039/f0_canon_indep_verify/entry_hashes.json",
         entry_sha,
         "Canonical F0/VOCAB/FROZEN pins and the seven-file W042 target bundle re-measured read-only; zero drift. No canonical artifact written.")
artifact("checkpoint", "worker_checkpoint",
         "artifacts/worker-039/f0_canon_indep_verify/CHECKPOINT.json",
         checkpoint_sha,
         "Worker checkpoint: task, class/node/gate, pins, verdict REPRODUCED, 10/10 checks, key measurements, finding W039-F0CANON-V01, deliverable hashes, next falsifier, authority note. Runtime copy byte-identical at runtime/state/w039_f0_canon_indep_verify_checkpoint.json.")

events.append({
    "event_id": f"{E}-claim",
    "event_type": "claim",
    "created_at": NOW,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F0",
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": CLASS_IDS,
    "gate": "G-F0",
    "task_id": TASK,
    "conclusion_type": "formal_model",
    "statement": (
        "Artifact-and-checker measurement, not a mathematical claim, at pins canonical F0 "
        "research_map/formulation_taxonomy.yaml#0abb9ed8a961, VOCAB_ALIASES "
        "artifacts/formulation/VOCAB_ALIASES.json#46cd9f1eb534, FROZEN rev29 815e08079aef, "
        "rule_spec 40f9bb9e657b: the W042-F0-CANON-CANDIDATE-08 claim is independently reproduced. "
        "Frozen F0 carries exactly 6 conclusion-token alias use sites at exactly "
        "{field_vocabulary.conclusion_type.allowed[1..2], "
        "classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type, "
        "classes.AF-SCC-C2-VAC-GEN.conclusion.type, "
        "classes.AF-SCC-C0-VAC-GEN.axes.conclusion_type, "
        "classes.AF-SCC-C0-VAC-GEN.conclusion.type}, with 7 full SCC alias occurrences "
        "(6 double-quoted use values + 1 unquoted line-153 prose token) and 1 '_C0' abbreviation; "
        "0 rejected-ambiguous and 0 unknown use sites. An independent quoted-substitution rebuild "
        "reproduces candidate A byte-for-byte, sha256 "
        "ef180b5cfe0a32265f2f561b02673ce2883d327560038e64762b55e98146a869; the frozen->A "
        "parsed-tree diff is exactly those 6 paths with allowed-list length 3->3 and class_ids "
        "stable; candidate B (f0a78706e5e8) has 0 alias residue and its diff vs A is confined to "
        "field_vocabulary.conclusion_type.rule. Canonical-resolved axes/conclusion tokens are "
        "identical across frozen/A/B, C0 != C2, and match rule_spec R11's class_conclusion_type "
        "map. Consumer rules diverge on frozen bytes and converge after repair: worker-019 B1 "
        "literal membership FAILS frozen and PASSES A/B, worker-097 alias-aware membership passes "
        "all three, and the pinned check_taxonomy_consistency.py exits 0 on all three with 0 "
        "field_vocabulary references. Blast radius recomputed on the W042 pinned events snapshot "
        "is exactly 817 events (by_event_type exact match; 5 gate records), with a live recount of "
        "927 at events.jsonl#ef060a5cce5a. No correction to W042-F0C-01/02; adoption of A or B "
        "remains the separate G-F0 reopening decision reserved in REC-37. No canonical write, no "
        "gate verdict, no node status."),
    "assumptions": (
        "Pins as declared and re-measured at start and exit (10/10, drift []); alias->canonical "
        "equivalence is exactly the frozen VOCAB_ALIASES.conclusion_type table; use positions are "
        "identified structurally from the parsed tree (allowed list, class axes, class conclusion "
        "type), not lexically; the 817 count is a short-hash substring count on worker-042's pinned "
        "events snapshot and a live recount at a stamped hash, i.e. a lower bound at pin time."),
    "falsifier": NEXT_FALSIFIER,
    "evidence_refs": BASE + [
        "artifacts/worker-039/f0_canon_indep_verify/CHECKPOINT.json#sha256:" + checkpoint_sha],
    "artifact_refs": BASE[:4],
})

events.append({
    "event_id": f"{E}-review-w042",
    "event_type": "review",
    "created_at": NOW,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F0",
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": CLASS_IDS,
    "gate": "G-F0",
    "task_id": TASK,
    "target_id": "artifacts/worker-042/f0_canon_candidate/report.json#21b7598096bb",
    "reviewer": "worker-039",
    "verdict": "accept",
    "score": 4.5,
    "hard_failures": [],
    "findings": [
        "POSITIVE: alias-use census reproduced structurally — 6 use sites, exact declared paths, 0 rejected/unknown; the text residue (7 full occurrences, 1 abbreviation) also reproduces.",
        "POSITIVE: byte-level oracle — an independent quoted-substitution rebuild reproduces candidate A sha256 ef180b5cfe0a exactly, and both candidates' parsed-tree diffs are confined to the declared paths with semantics and C0/C2 distinctness preserved.",
        "POSITIVE: consumer divergence/convergence reproduced end-to-end (literal FAIL frozen -> PASS A/B; alias-aware PASS all; pinned checker exit 0 on all three, 0 field_vocabulary refs), and the 817-event blast radius reproduces exactly on the author's pinned events snapshot.",
        "DISCLOSURE W039-F0CANON-E01 (instrument, non-blocking): the first run of this verifier scored 6/10 under two defects of my own instrument (abbreviation regex matching inside canonical scc_* tokens; literal-membership rule reading the frozen allowed list for all variants). Both were fixed before the reported run and are now covered by controls K5 and V8; run 1 is preserved and the erratum is recorded in the README.",
        "SCOPE NOTE: this review verifies the census/repair-candidate measurements only. Adoption of candidate A or B voids the G-F0 pass at 0abb9ed8a961 until re-review (817 pinned F0-bound events at the author's pin) and remains the separate G-F0 reopening decision reserved in REC-37; for rev14 item 4 this census bounds the alias->canonical crosswalk surface to the six structural sites plus the one prose mention measured here.",
    ],
    "summary": (
        "Independent non-author verification of W042-F0-CANON-CANDIDATE-08: accept 4.5, no hard "
        "failures, full reproduction of the 6-site alias-use census, both byte-minimal candidates, "
        "the consumer-rule divergence/convergence, and the 817-event blast radius. One disclosed "
        "self-erratum concerns this verifier's first run, not the verified claim."),
    "evidence_refs": BASE,
})

events.append({
    "event_id": f"{E}-status",
    "event_type": "status",
    "created_at": NOW,
    "actor": "worker-039",
    "group_id": "formulation",
    "node_id": "F0",
    "class_id": "AF-WCC-VAC-GEN",
    "class_ids": CLASS_IDS,
    "gate": "G-F0",
    "task_id": TASK,
    "status": "active",
    "hours": 0.5,
    "summary": (
        "No inbox card for worker-039; took one unclaimed class-bound task on the G-F0/G-FORM "
        "boundary (the F2b coverage cluster was left to its existing owners): independent "
        "verification of W042-F0-CANON-CANDIDATE-08. Verdict REPRODUCED, 10/10 checks pass, 0 fail, "
        "7/7 controls fire, no correction to the W042 numbers. Frozen F0 has exactly 6 alias use "
        "sites, 7 full alias text occurrences and 1 abbreviation; candidate A is reproduced "
        "byte-for-byte by an independent rebuild; candidate B is residue-free and confined; "
        "semantics preserved with C0 != C2; consumer rules diverge on frozen and converge on A/B; "
        "blast radius exactly 817 on the pinned snapshot (927 live at a stamped hash). Two first-run "
        "defects of this verifier were self-caught and fixed before the reported run (disclosed). "
        "No gate verdict, node status or canonical write."),
    "evidence_refs": BASE + [
        "artifacts/worker-039/f0_canon_indep_verify/CHECKPOINT.json#sha256:" + checkpoint_sha],
    "next_falsifier": NEXT_FALSIFIER,
})

# ---------------------------------------------------------------- validate + append
seen = set()
if OUTBOX.exists():
    for line in OUTBOX.read_text().splitlines():
        try:
            seen.add(json.loads(line)["event_id"])
        except Exception:
            pass
appended = 0
with OUTBOX.open("a") as fh:
    for ev in events:
        schemas.validate_event(ev)
        if ev["event_id"] in seen:
            continue
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
        appended += 1
print(f"events built={len(events)} appended={appended} outbox={OUTBOX}")
print("deliverables:", json.dumps(deliverables, indent=1, sort_keys=True))
