#!/usr/bin/env python3
"""W027-F2A-HB1-INDEP-01 finaliser: pin snapshots, README, SHA256SUMS, events, checkpoint.

Run after verify_hb1_indep.py has produced report.json.  Writes only under
artifacts/worker-027/f2a_hb1_indep/, runtime/state/, and appends to
comms/outbox/worker-027.jsonl.  Never writes a canonical artifact.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
WORK = ROOT / "artifacts/worker-027/f2a_hb1_indep"
TASK = "W027-F2A-HB1-INDEP-01"
CN = timezone(timedelta(hours=8))

PINS = {
    "research_map/formulation_taxonomy.yaml": "pinned/formulation_taxonomy.canonical.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml": "pinned/formulation_taxonomy.supplement.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "pinned/taxonomy_consistency.live.json",
    "artifacts/worker-05/verify/taxonomy_consistency_hashbound.json": "pinned/taxonomy_consistency_hashbound.candidate.json",
    "artifacts/worker-05/verify/gen_hashbound_consistency_evidence.py": "pinned/gen_hashbound_consistency_evidence.py",
    "artifacts/worker-05/verify/check_class_binding_drift.py": "pinned/check_class_binding_drift.py",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "pinned/check_taxonomy_consistency.py",
    "artifacts/formulation/VOCAB_ALIASES.json": "pinned/VOCAB_ALIASES.json",
    "artifacts/formulation/FROZEN.json": "pinned/FROZEN.rev29.json",
    "schemas/af_wcc_vacuum.yaml": "pinned/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml": "pinned/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "pinned/af_scc_c0_vacuum.yaml",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CN).strftime("%Y-%m-%dT%H:%M:%S%z")


def main() -> int:
    report = json.loads((WORK / "report.json").read_text(encoding="utf-8"))
    assert report["task_id"] == TASK
    (WORK / "pinned").mkdir(exist_ok=True)

    # ---- 1. pin immutable snapshots -------------------------------------------
    manifest = []
    for src_rel, dst_rel in PINS.items():
        src = ROOT / src_rel
        dst = WORK / dst_rel
        shutil.copy2(src, dst)
        manifest.append({"source_path": src_rel, "sha256": sha(dst), "pinned_as": dst_rel})
    (WORK / "pinned/manifest.json").write_text(
        json.dumps({"task_id": TASK, "pinned_at": now(), "files": manifest},
                   indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # ---- 2. README -------------------------------------------------------------
    checks = {c["id"]: c["ok"] for c in report["primary_checks"]}
    ctrls = {c["id"]: c["ok"] for c in report["controls"]}
    probes = report["instrument_probes"]
    readme = f"""# W027-F2A-HB1-INDEP-01 — independent verification of the F2a HF-B1 hashbound closure

Worker: worker-027 · Class: `AF-SCC-C2-VAC-GEN` (node F2a) · Gate: G-FORM · read-only.
Claim author under test: `deepseek-flash-05` (`artifacts/worker-05/verify/hb1_closure_report.json#c7eeab551128`).

## Verdict

`{report['verdict']}` (exit {report['exit_code']}), at the pins recorded in `report.json`
(`pins_t0` = `pins_t1`, 12/12 unchanged; measurement digest
`{report['repeat']['digests'][0]}` identical over {report['repeat']['runs']} in-process runs and one
separate process).

* **W027-HB1-F1 (main claim) — VERIFIED.** The live evidence record
  `artifacts/formulation/evidence/taxonomy_consistency.json#{report['pins_t0']['artifacts/formulation/evidence/taxonomy_consistency.json'][:12]}`
  embeds no sha256 of either compared taxonomy file (private hex64 scan: none; classifier: UNBOUND),
  so HF-B1 reproduces. The candidate
  `artifacts/worker-05/verify/taxonomy_consistency_hashbound.json#{report['pins_t0']['artifacts/worker-05/verify/taxonomy_consistency_hashbound.json'][:12]}`
  embeds exactly the independently measured hashes of both compared files; the pinned generator
  reproduces it byte-for-byte over two runs; dropped in at the canonical evidence path in an
  isolated sandbox it makes every hard check of `check_class_binding_drift.py` pass for all three
  schemas, and the canonical `check_taxonomy_consistency.py` exits 0. No canonical byte was written.
* **W027-HB1-F2 (major, instrument) — CONFIRMED.** The proposed durable checker's B7 is a substring
  test (`declared in blob or declared[:16] in blob`). A record whose canonical binding hash shares
  only the first 16 hex chars (one suffix nibble flipped) passes **all** hard checks (exit 0), so B7
  does not verify that the record's declared revision equals the measured revision.
* **W027-HB1-F3 (minor, instrument) — CONFIRMED.** B7 binds only the canonical F0 hash; the
  supplement input `artifacts/formulation/formulation_taxonomy.yaml` is bound by no hard check, so a
  stale supplement hash passes.

F2/F3 are blind spots of the tool, not defects of the candidate; they gate *adopting the tool* as
the durable binding check. See the `blocker` event in `comms/outbox/worker-027.jsonl`.

## Method (independence)

Primary verdicts use this worker's own instruments: a recursive hex64 scanner, an
UNBOUND/BOUND/STALE classifier driven by independently recomputed live hashes, and a private
class-set consistency check. The author's checker is used only as a labelled cross-instrument
(P7/P8/IP1–IP3), and the canonical project checker as a second independent instrument (P9).
Sandbox roots are built under `scratch/` and never touch canonical paths.

## Pre-registered checks

| id | check | ok |
|---|---|---|
""" + "\n".join(f"| {k} | {v} |" for k, v in checks.items()) + """

| id | control | ok |
|---|---|---|
""" + "\n".join(f"| {k} | {v} |" for k, v in ctrls.items()) + """

Instrument probes (recorded, not gating): """ + "; ".join(
        f"{p['id']}={p['private_classifier']}/author_exit{p['author_drift_exit']}" for p in probes) + f"""

## Reproduction

```bash
cd {ROOT}
python3 artifacts/worker-027/f2a_hb1_indep/verify_hb1_indep.py \\
  --out artifacts/worker-027/f2a_hb1_indep/report.json \\
  --work artifacts/worker-027/f2a_hb1_indep/scratch --repeat 2
```

Exit 0 = verified, 1 = claim not verified, 2 = void (input drift). `scratch/` holds the drift-checker
reports for the live record, the candidate drop-in and the three instrument probes, plus the
generator's two runs and the tamper fixtures.

## Falsifier

{report['falsifier']}

## Non-claims

""" + "\n".join(f"- {x}" for x in report["non_claims"]) + "\n"
    (WORK / "README.md").write_text(readme, encoding="utf-8")

    # ---- 3. SHA256SUMS ----------------------------------------------------------
    files = sorted(p for p in WORK.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    sums = "".join(f"{sha(p)}  {p.relative_to(WORK).as_posix()}\n" for p in files)
    (WORK / "SHA256SUMS").write_text(sums, encoding="utf-8")

    # ---- 4. outbox events -------------------------------------------------------
    h = {p.relative_to(WORK).as_posix(): sha(p) for p in files}
    report_h = h["report.json"]
    script_h = h["verify_hb1_indep.py"]
    readme_h = h["README.md"]
    manifest_h = h["pinned/manifest.json"]
    sums_h = sha(WORK / "SHA256SUMS")
    ev = []
    ts = now().replace(":", "").replace("+", "+")

    def ref(rel: str, short: bool = True) -> str:
        d = h.get(rel) or (sums_h if rel == "SHA256SUMS" else None)
        return f"{WORK.relative_to(ROOT).as_posix()}/{rel}#{d[:12] if short else d}"

    ev.append({
        "event_id": f"w027-hb1-{ts}-status", "event_type": "status", "created_at": now(),
        "actor": "worker-027", "agent_slot": "worker-027",
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "node_id": "F2a", "gate": "G-FORM", "task_id": TASK, "status": "active", "hours": 0.8,
        "summary": ("W027-F2A-HB1-INDEP-01 complete at worker level: independent, read-only verification of "
                    "the deepseek-flash-05 HF-B1 hashbound closure at the live pins. Main claim VERIFIED "
                    "(W027-HB1-F1): live evidence 9e335e9b is unbound; candidate 4c4803c5 embeds exactly the "
                    "measured hashes of both compared taxonomy files, reproduces byte-for-byte from the pinned "
                    "generator, passes every hard check of check_class_binding_drift.py in an isolated sandbox "
                    "for all three schemas, and the canonical check_taxonomy_consistency.py exits 0 there. "
                    "Two instrument blind spots CONFIRMED (W027-HB1-F2: B7 accepts a 16-hex-prefix substring, "
                    "so a one-nibble tamper passes all hard checks; W027-HB1-F3: B7 does not bind the supplement "
                    "input). No canonical file written; candidate NOT published. This is a task-completion "
                    "claim, not a node transition; workers cannot set status=done."),
        "evidence_refs": [ref("report.json"), ref("verify_hb1_indep.py"), ref("README.md"),
                          ref("pinned/manifest.json")],
        "next_falsifier": report["falsifier"],
    })
    for rel, atype in (("report.json", "verification_report"),
                       ("verify_hb1_indep.py", "verification_harness"),
                       ("README.md", "readme"),
                       ("pinned/manifest.json", "pinned_snapshot_manifest"),
                       ("SHA256SUMS", "hash_manifest")):
        d = sums_h if rel == "SHA256SUMS" else h[rel]
        ev.append({
            "event_id": f"w027-hb1-{ts}-artifact-{rel.replace('/', '-').replace('.', '-')}",
            "event_type": "artifact", "created_at": now(), "actor": "worker-027",
            "agent_slot": "worker-027", "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a",
            "gate": "G-FORM", "task_id": TASK, "artifact_type": atype,
            "path": f"{WORK.relative_to(ROOT).as_posix()}/{rel}", "sha256": d,
            "validation_status": "unverified",
        })
    ev.append({
        "event_id": f"w027-hb1-{ts}-claim", "event_type": "claim", "created_at": now(),
        "actor": "worker-027", "agent_slot": "worker-027",
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "node_id": "F2a", "gate": "G-FORM", "task_id": TASK,
        "conclusion_type": "verification_result",
        "statement": ("At the pinned live bytes (canonical F0 0abb9ed8a961, supplement d7419b4e8963, live "
                      "evidence 9e335e9b, candidate 4c4803c5, FROZEN rev29 815e08079aef), the HF-B1 closure "
                      "proposal is valid and unpublished: the live evidence embeds no revision hash, the "
                      "candidate embeds exactly the independently measured hashes of both compared files and "
                      "is reproducible byte-for-byte from the pinned generator, and with the candidate at the "
                      "canonical evidence path in an isolated sandbox every hard check of "
                      "check_class_binding_drift.py passes for all three schemas while the canonical "
                      "check_taxonomy_consistency.py exits 0. Separately, the same checker's B7 accepts a "
                      "record whose declared hash shares only the first 16 hex chars with the measured hash, "
                      "and does not bind the supplement input; the candidate is not affected, but the tool "
                      "must be hardened before it is adopted as the durable binding check."),
        "assumptions": [
            "The class schema under F2a is schemas/af_scc_c2_vacuum.yaml (live e9a27996) and its f0_binding rule is the one being discharged",
            "The two compared files are the canonical research_map/formulation_taxonomy.yaml and the supplement artifacts/formulation/formulation_taxonomy.yaml",
            "Sandbox drop-in is an admissible proxy for publication because the checker resolves the evidence path from the schema's f0_binding",
        ],
        "falsifier": report["falsifier"],
        "evidence_refs": [ref("report.json"), ref("verify_hb1_indep.py"),
                          ref("pinned/taxonomy_consistency_hashbound.candidate.json"),
                          ref("pinned/taxonomy_consistency.live.json")],
        "artifact_refs": [ref("report.json", short=False), ref("verify_hb1_indep.py", short=False)],
    })
    ev.append({
        "event_id": f"w027-hb1-{ts}-review", "event_type": "review", "created_at": now(),
        "actor": "worker-027", "agent_slot": "worker-027",
        "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a", "gate": "G-FORM", "task_id": TASK,
        "target_id": "artifacts/worker-05/verify/taxonomy_consistency_hashbound.json#4c4803c540a1",
        "reviewer": "worker-027", "verdict": "accept", "score": 4.0, "hard_failures": [],
        "findings": [
            {"id": "W027-HB1-F2", "severity": "major", "status": "CONFIRMED",
             "finding": ("check_class_binding_drift.py B7 is a substring test (declared in blob or "
                         "declared[:16] in blob): a record with one suffix nibble flipped passes all hard "
                         "checks (exit 0). B7 should compare the record's declared revision to the schema's "
                         "declared/measured revision for full-string equality."),
             "evidence": ref("scratch/drift_ip1.json")},
            {"id": "W027-HB1-F3", "severity": "minor", "status": "CONFIRMED",
             "finding": ("B7 binds only the canonical F0 hash; the supplement input hash is not bound by any "
                         "hard check, so a stale supplement binding passes."),
             "evidence": ref("scratch/drift_ip3.json")},
            {"id": "W027-HB1-F4", "severity": "info", "status": "OBSERVED",
             "finding": ("The author's closure harness self-reports 14/14; an independent re-execution at the "
                         "live pins reproduces the before/base behaviour (P7/P8) and adds the two blind-spot "
                         "probes above."),
             "evidence": ref("scratch/drift_live.json")},
        ],
    })
    ev.append({
        "event_id": f"w027-hb1-{ts}-blocker", "event_type": "blocker", "created_at": now(),
        "actor": "worker-027", "agent_slot": "worker-027",
        "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a", "gate": "G-FORM", "task_id": TASK,
        "description": ("The F2a/F2b/F1 HF-B1 closure rests on check_class_binding_drift.py returning 'all hard "
                        "checks pass'. Its B7 currently accepts any record containing the declared hash or its "
                        "first 16 hex chars as a substring and does not bind the supplement input, so a "
                        "prefix-preserving tamper or a stale supplement passes (W027-HB1-F2/F3). The candidate "
                        "4c4803c5 itself is sound and fully bound (W027-HB1-F1); this blocker is about adopting "
                        "the tool, not about the candidate."),
        "needed_to_unblock": ("Tool owner: (1) make B7 compare the record's declared revision to the schema's "
                              "declared/measured canonical revision by full-string equality; (2) bind the "
                              "supplement input hash by a hard check or an explicit informational check with a "
                              "fail-closed rule; (3) add a prefix-preserving tamper fixture to --selftest; "
                              "(4) re-run the checker and re-verify at unchanged hashes. Until then any verdict "
                              "that cites 'all hard checks pass' exercises only a substring test."),
        "evidence_refs": [ref("report.json"), ref("scratch/drift_ip1.json"),
                          ref("scratch/drift_ip3.json"),
                          "artifacts/worker-05/verify/check_class_binding_drift.py#bde270d3886a"],
    })
    outbox = ROOT / "comms/outbox/worker-027.jsonl"
    with outbox.open("a", encoding="utf-8") as fh:
        for e in ev:
            fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    # ---- 5. checkpoint ----------------------------------------------------------
    outbox_h = sha(outbox)
    arts = {f"{WORK.relative_to(ROOT).as_posix()}/{p.relative_to(WORK).as_posix()}": sha(p)
            for p in files}
    arts["comms/outbox/worker-027.jsonl"] = outbox_h
    ck = {
        "schema_version": "0.1", "worker": "worker-027", "task_id": TASK,
        "created_at": now(), "status": "complete_bounded",
        "verdict": report["verdict"], "exit_code": report["exit_code"],
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": ["AF-SCC-C2-VAC-GEN"],
        "node_id": "F2a", "gate": "G-FORM", "hours": 0.8,
        "artifacts": arts,
        "findings": [
            {"id": "W027-HB1-F1", "severity": "info", "status": "VERIFIED",
             "statement": "HF-B1 hashbound closure proposal valid and unpublished at the live pins"},
            {"id": "W027-HB1-F2", "severity": "major", "status": "CONFIRMED",
             "statement": "drift checker B7 accepts a 16-hex-prefix substring; prefix-preserving tamper passes"},
            {"id": "W027-HB1-F3", "severity": "minor", "status": "CONFIRMED",
             "statement": "drift checker B7 does not bind the supplement input hash"},
        ],
        "controls": {"passed": sum(1 for c in report["controls"] if c["ok"]),
                     "total": len(report["controls"])},
        "instrument_probes": [{"id": p["id"], "private": p["private_classifier"],
                               "author_exit": p["author_drift_exit"],
                               "author_caught": p["author_caught_tamper"]} for p in probes],
        "measurements": {
            "primary_checks_passed": sum(1 for c in report["primary_checks"] if c["ok"]),
            "primary_checks_total": len(report["primary_checks"]),
            "measurement_digest": report["repeat"]["digests"][0],
            "repeat_runs": report["repeat"]["runs"],
            "pin_count": len(report["pins_t0"]),
            "pin_drift": report["pin_drift"],
            "pins": {k: v for k, v in report["pins_t0"].items()},
        },
        "falsifier": report["falsifier"],
        "completion_scope": ("worker lifecycle only; cannot set node done, validation_status=passed, or any gate "
                             "verdict"),
        "non_claims": report["non_claims"],
    }
    ck_path = ROOT / "runtime/state/w027_f2a_hb1_indep_checkpoint.json"
    ck_path.write_text(json.dumps(ck, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "task": TASK, "verdict": report["verdict"], "events_appended": len(ev),
        "report_sha256": report_h, "script_sha256": script_h, "readme_sha256": readme_h,
        "sha256sums_sha256": sums_h, "outbox_sha256": outbox_h,
        "checkpoint": str(ck_path.relative_to(ROOT)), "checkpoint_sha256": sha(ck_path),
        "artifact_files": len(arts),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
