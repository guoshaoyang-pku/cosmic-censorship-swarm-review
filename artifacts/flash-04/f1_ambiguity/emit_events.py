#!/usr/bin/env python3
"""Regenerate the evidence bundle and emit worker-04 delta events (frozen rev4).

Steps:
1. rebuild the artifact from `binding_rev4.py` (deterministic);
2. run suite validation, runner self-test, the frozen-schema audit, the
   adjudication-queue cross-check, and the r3 -> rev4 delta report;
3. build `status`, `artifact` (x2) and `blocker` events, validate them against
   `research_map/schemas.py`, and append to `comms/outbox/deepseek-flash-04.jsonl`
   (idempotent by `event_id`, with `supersedes` links);
4. write `BUNDLE.sha256`.

No node completion is claimed; the status stays `active`.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TESTS = ROOT / "schemas" / "f1_falsifier_tests.jsonl"
SNAPSHOT = HERE / "schema_snapshots" / "af_wcc_vacuum.f512af5f.yaml"
REPORT = HERE / "ambiguity_report.json"
CROSSCHECK = HERE / "adjudication_crosscheck.json"
DELTA = HERE / "frozen_rev4_delta_report.json"
OUTBOX = ROOT / "comms" / "outbox" / "deepseek-flash-04.jsonl"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
ADJUDICATION = ROOT / "artifacts" / "formulation" / "reviews" / "ADJUDICATION_flash04_ambiguity.md"
VOCAB = ROOT / "artifacts" / "formulation" / "VOCAB_ALIASES.json"
SCHEMA_SHA_PREFIX = "f512af5f"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], out_file: Path | None = None) -> int:
    proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    if out_file is not None:
        out_file.write_text(proc.stdout + (("\n[stderr]\n" + proc.stderr) if proc.stderr else ""))
    return proc.returncode


def ref(path: Path) -> str:
    return f"{path.relative_to(ROOT)}#{sha256_file(path)[:8]}"


def main() -> int:
    rc_build = run([sys.executable, "build_tests.py"], HERE / "build_stdout.txt")
    rc_validate = run([sys.executable, "run_f1_ambiguity.py", "--validate-only"],
                      HERE / "suite_validation.txt")
    rc_selftest = run([sys.executable, "run_f1_ambiguity.py", "--self-test"],
                      HERE / "runner_selftest.txt")
    rc_audit = run([sys.executable, "run_f1_ambiguity.py",
                    "--schema", str(SNAPSHOT.relative_to(HERE)), "--expect-sha", SCHEMA_SHA_PREFIX,
                    "--out", str(REPORT)])
    rc_cross = run([sys.executable, "audit_adjudication_queue.py"],
                   HERE / "crosscheck_stdout.txt")
    rc_delta = run([sys.executable, "delta_report.py"], HERE / "delta_stdout.txt")
    if (rc_build, rc_validate, rc_selftest, rc_cross, rc_delta) != (0, 0, 0, 0, 0) or rc_audit not in (0, 1):
        print(f"bundle regeneration failed: build={rc_build} validate={rc_validate} "
              f"self_test={rc_selftest} audit={rc_audit} cross={rc_cross} delta={rc_delta}",
              file=sys.stderr)
        return 2

    report = json.loads(REPORT.read_text())
    cross = json.loads(CROSSCHECK.read_text())["summary"]
    delta = json.loads(DELTA.read_text())
    tests_sha = sha256_file(TESTS)
    report_sha = sha256_file(REPORT)
    snapshot_sha = sha256_file(SNAPSHOT)
    cross_sha = sha256_file(CROSSCHECK)
    delta_sha = sha256_file(DELTA)
    findings = HERE / "FINDINGS.md"
    readme = HERE / "README.md"
    runner = HERE / "run_f1_ambiguity.py"
    build = HERE / "build_tests.py"
    adjudication = ADJUDICATION
    vocab = VOCAB
    rule_spec = ROOT / "artifacts" / "formulation" / "rule_spec.json"

    versions = HERE / "versions"
    versions.mkdir(exist_ok=True)
    versioned = versions / f"f1_falsifier_tests.{tests_sha[:8]}.jsonl"
    if not versioned.exists() or versioned.read_bytes() != TESTS.read_bytes():
        versioned.write_bytes(TESTS.read_bytes())
    versioned_sha = sha256_file(versioned)

    now = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    stamp = time.strftime("%Y%m%dT%H%M%S")
    short = tests_sha[:8]

    existing = []
    if OUTBOX.exists():
        existing = [json.loads(line) for line in OUTBOX.read_text().splitlines() if line.strip()]

    def supersedes_for(ev_type: str, path: str | None = None) -> list[str]:
        out = []
        for e in existing:
            if e.get("event_type") != ev_type or e.get("node_id") != "F1":
                continue
            if path is not None and e.get("path") != path:
                continue
            out.append(e["event_id"])
        return out

    counts = delta["counts"]
    still_open = delta["still_open"]
    status_event = {
        "event_id": f"flash-04-status-F1-frozen-{stamp}-{short}",
        "supersedes": supersedes_for("status"),
        "event_type": "status",
        "created_at": now,
        "actor": "deepseek-flash-04",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "group_id": "formulation",
        "status": "active",
        "hours": 2.5,
        "summary": (
            "Delta re-run against frozen F1 revision 4 sha256 f512af5f (FROZEN.json 23:35:45; "
            "the 23:33:37 message cited 17873b9d, which the manifest superseded before this run). "
            "Deltas vs the r3 worker draft 7a3e1f93: closed AMB-09, AMB-10; finding-closed AMB-07 "
            "(set-level membership ruling) and AMB-08 (slice narrowed to R^3); reclassified as "
            "accepted obligations AMB-01/02/03/15; field renames AMB-04/06; 7 unchanged. "
            f"Still open: {', '.join(still_open)}. Cross-check vs the schema's "
            f"adjudication_queue.open_rows: {cross['in_queue']} queued, {cross['exact_leaf_match']} "
            f"exact + {cross['alternate_leaf_match']} alternate leaf match, {cross['leaf_mismatch']} "
            "mismatch; AMB-03 is an accepted obligation but absent from open_rows. Adjudication doc "
            "and VOCAB_ALIASES are cited as evidence. No completion claimed; tests artifact "
            f"rebuilt at {tests_sha[:8]}."
        ),
        "evidence_refs": [
            ref(TESTS), ref(REPORT), ref(DELTA), ref(CROSSCHECK), ref(findings),
            ref(adjudication), ref(vocab), ref(FROZEN),
            f"artifacts/flash-04/f1_ambiguity/schema_snapshots/"
            f"af_wcc_vacuum.f512af5f.yaml#{snapshot_sha[:8]}",
            ref(rule_spec),
        ],
        "next_falsifier": (
            "A new freeze hash without a delta re-run; an obligation closed without L1/L0 evidence; "
            "or a G-FORM verdict citing a revision label instead of a sha256."
        ),
    }

    artifact_tests = {
        "event_id": f"flash-04-art-F1-tests-frozen-{stamp}-{short}",
        "supersedes": supersedes_for("artifact", "schemas/f1_falsifier_tests.jsonl"),
        "event_type": "artifact",
        "created_at": now,
        "actor": "deepseek-flash-04",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "group_id": "formulation",
        "artifact_type": "falsifier_test_suite",
        "path": str(TESTS.relative_to(ROOT)),
        "sha256": tests_sha,
        "bytes": TESTS.stat().st_size,
        "validation_status": "unverified",
        "summary": (
            f"{report['tests_count']} ambiguity tests rebound to the frozen rev4 sha256 "
            f"{SCHEMA_SHA_PREFIX}; 13/17 determinate, 4 open obligations "
            f"({', '.join(still_open)}); delta report and adjudication cross-check attached."
        ),
        "supporting_artifacts": [
            {"path": str(REPORT.relative_to(ROOT)), "sha256": report_sha},
            {"path": str(DELTA.relative_to(ROOT)), "sha256": delta_sha},
            {"path": str(CROSSCHECK.relative_to(ROOT)), "sha256": cross_sha},
            {"path": ("artifacts/flash-04/f1_ambiguity/schema_snapshots/"
                      "af_wcc_vacuum.f512af5f.yaml"), "sha256": snapshot_sha},
            {"path": f"artifacts/flash-04/f1_ambiguity/versions/{versioned.name}",
             "sha256": versioned_sha},
            {"path": str(runner.relative_to(ROOT)), "sha256": sha256_file(runner)},
            {"path": str(build.relative_to(ROOT)), "sha256": sha256_file(build)},
            {"path": str(findings.relative_to(ROOT)), "sha256": sha256_file(findings)},
            {"path": str(adjudication.relative_to(ROOT)), "sha256": sha256_file(adjudication)},
        ],
        "evidence_refs": [ref(TESTS), ref(DELTA), ref(ADJUDICATION), ref(FROZEN)],
        "next_falsifier": "Re-run after any freeze-hash change; a row that cannot be rebound is rejected.",
    }

    artifact_report = {
        "event_id": f"flash-04-art-F1-report-frozen-{stamp}-{short}",
        "supersedes": supersedes_for("artifact", "artifacts/flash-04/f1_ambiguity/ambiguity_report.json"),
        "event_type": "artifact",
        "created_at": now,
        "actor": "deepseek-flash-04",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "group_id": "formulation",
        "artifact_type": "ambiguity_audit_report",
        "path": str(REPORT.relative_to(ROOT)),
        "sha256": report_sha,
        "bytes": REPORT.stat().st_size,
        "validation_status": "unverified",
        "summary": (
            "Frozen-rev4 binding: per-test structural binding, contract-leaf audit, "
            "schema unresolved_items, delta vs r3, and adjudication-queue cross-check."
        ),
        "evidence_refs": [ref(REPORT), ref(TESTS), ref(DELTA), ref(CROSSCHECK)],
        "next_falsifier": "Any reviewer re-run producing a different binding for the same frozen sha256.",
    }

    blocker = {
        "event_id": f"flash-04-blocker-F1-frozen-{stamp}-{short}",
        "supersedes": supersedes_for("blocker"),
        "event_type": "blocker",
        "created_at": now,
        "actor": "deepseek-flash-04",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "group_id": "formulation",
        "description": (
            "Frozen rev4 f512af5f resolves the r3 ambiguity findings except the four accepted "
            f"obligations ({', '.join(still_open)}). Two items remain: (1) AMB-03 (finite-dimensional "
            "Kerr-type meagerness) is accepted in ADJUDICATION_flash04_ambiguity.md but is absent "
            "from adjudication_queue.open_rows, so A1's queue is incomplete; (2) FROZEN.json lists "
            "its own sha256 as 94880c36, which can never match its content (actual 8d0725ef) because "
            "the manifest embeds its own hash. The r3 token-duality and hash-citation blockers are "
            "resolved by VOCAB_ALIASES.json and FROZEN.json respectively."
        ),
        "needed_to_unblock": (
            "(a) A1/L1 adjudicate or discharge the four obligations with evidence (genericity "
            "meagerness, non-vacuity witness, equivalence to future asymptotic predictability); "
            "(b) add AMB-03 to open_rows or fold it explicitly under the meagerness obligation; "
            "(c) make FROZEN.json self-consistent (exclude its own entry or record the self-hash as "
            "not-applicable); (d) G-FORM verdict cites f512af5f or a successor hash."
        ),
        "evidence_refs": [ref(DELTA), ref(CROSSCHECK), ref(ADJUDICATION), ref(FROZEN), ref(TESTS)],
        "next_falsifier": (
            "If a later freeze closes all four obligations with cited evidence and open_rows covers "
            "every accepted obligation, this blocker is falsified."
        ),
    }

    sys.path.insert(0, str(ROOT / "research_map"))
    from schemas import validate_event  # noqa: E402

    for ev in (status_event, artifact_tests, artifact_report, blocker):
        validate_event(ev)
        if ev["event_type"] == "artifact":
            assert sha256_file(ROOT / ev["path"]) == ev["sha256"], f"hash mismatch {ev['path']}"

    seen = {e.get("event_id") for e in existing}
    new_events = [e for e in (status_event, artifact_tests, artifact_report, blocker)
                  if e["event_id"] not in seen]
    if new_events:
        OUTBOX.parent.mkdir(parents=True, exist_ok=True)
        with OUTBOX.open("a") as fh:
            for ev in new_events:
                fh.write(json.dumps(ev, sort_keys=True, ensure_ascii=True) + "\n")

    bundle_files = [TESTS, REPORT, CROSSCHECK, DELTA, HERE / "r3_7a3e1f93_report.json",
                    HERE / "FINDINGS.md", HERE / "README.md", HERE / "CHECKPOINTS.md",
                    runner, build, HERE / "emit_events.py", HERE / "watch_drift.sh",
                    HERE / "audit_adjudication_queue.py", HERE / "delta_report.py",
                    HERE / "binding_rev4.py",
                    HERE / "suite_validation.txt", HERE / "runner_selftest.txt",
                    HERE / "crosscheck_stdout.txt", HERE / "delta_stdout.txt",
                    HERE / "build_stdout.txt", versioned, SNAPSHOT,
                    HERE / "schema_snapshots" / "af_wcc_vacuum.7a3e1f93.yaml",
                    HERE / "schema_snapshots" / "af_wcc_vacuum.f55722a7.yaml",
                    adjudication, vocab, FROZEN]
    manifest = [f"{sha256_file(p)}  {p.relative_to(ROOT)}"
                for p in bundle_files if p.exists()]
    (HERE / "BUNDLE.sha256").write_text("\n".join(manifest) + "\n")

    print(f"validate={rc_validate} self_test={rc_selftest} audit_rc={rc_audit} "
          f"cross={rc_cross} delta={rc_delta}")
    print(f"tests_sha256={tests_sha}")
    print(f"report_sha256={report_sha}")
    print(f"delta={json.dumps(counts)} still_open={still_open}")
    print(f"outbox appended={len(new_events)} total={len(existing)+len(new_events)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
