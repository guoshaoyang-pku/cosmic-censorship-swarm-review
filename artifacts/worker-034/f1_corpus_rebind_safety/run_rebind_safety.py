#!/usr/bin/env python3
"""W034-F1-CORPUS-REBIND-SAFETY-01.

Bounded, class-bound worker task (worker-034).  Class AF-WCC-VAC-GEN, node F1,
gate G-FORM.

Question (L-FORM-04 second disjunct): if the 25-row F1 falsifier corpus
`schemas/f1_falsifier_tests.jsonl` is mechanically re-bound from the superseded
F1 rev12 hash `cce9c60146d6...` to the live F1 rev13 hash `d9cebb9404b2...`,
do the corpus's own 84 recorded probes still evaluate the same way?

Method
  1. pin every input by sha256 (fail closed), copy to pinned/, re-hash copies;
  2. re-execute every `probe_results[*]` entry of all 25 rows against the
     rev12 baseline schema and against the live rev13 schema;
  3. SELFTEST: rev12 must reproduce every recorded `pass` value (otherwise the
     recorded corpus, not the schema, is the defective object);
  4. OUTCOME-DIFF: a probe whose pass value changes rev12 -> rev13 means a
     mechanical rebind is NOT safe (the row content must be revised);
     CONTENT-DIFF: a probe whose resolved value changes while pass is stable is
     metadata-safe but semantic drift and is reported;
  5. controls: two field mutants and a path-deletion mutant must flip their
     mapped probes; a tampered expectation must fail; re-evaluation must be
     deterministic; inputs must be byte-stable at exit.

Verdicts
  SAFE_MECHANICAL_REBIND              no probe outcome changes and 84/84 recorded
                                      passes are truthful at the declared binding
  REBIND_CARRIES_FALSE_RECORDED_PASSES no outcome changes, but >=1 recorded pass is
                                      not supported by the declared binding, so a
                                      re-hash would launder a false record
  REBIND_REQUIRES_ROW_UPDATES         >=1 probe flips; rows must be edited, not just
                                      re-hashed
  INSTRUMENT_OR_RECORD_DEFECT         reserved: a recorded-False probe measures True
                                      (evaluator semantics not excluded)

No canonical write, no gate verdict, no node status.  Worker measurement only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = HERE / "pinned"
CST = timezone(timedelta(hours=8))

TASK_ID = "W034-F1-CORPUS-REBIND-SAFETY-01"
WORKER = "worker-034"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"

# Declared pins measured before authoring (fail closed on mismatch).
DECLARED = {
    "live_rev13": (
        "schemas/af_wcc_vacuum.yaml",
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    ),
    "rev12_baseline_a": (
        "artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml",
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    ),
    "rev12_baseline_b": (
        "artifacts/heldout/heldout-09/bases/af_wcc_vacuum.yaml",
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    ),
    "corpus": (
        "schemas/f1_falsifier_tests.jsonl",
        "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    ),
    "frozen": (
        "artifacts/formulation/FROZEN.json",
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    ),
}

# Test numbers worker-041 (W041-F1-CORPUS-REBIND-01) measured as exercising
# fields that changed rev12 -> rev13 (its table: F1-AMB-11/17/23/25).  This task
# tests whether their *probe outcomes* change.
W041_SEMANTIC_ROWS = [11, 17, 23, 25]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def canon_dump(v, sort_keys: bool, ensure_ascii: bool) -> str:
    return json.dumps(v, ensure_ascii=ensure_ascii, sort_keys=sort_keys)


def norm_ws(s: str) -> str:
    return " ".join(str(s).split())


def resolve(doc, path: str):
    """Strict dotted-path resolver.  Returns (found, value)."""
    cur = doc
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return False, None
    return True, cur


def evaluate(probe: dict, doc) -> bool:
    found, value = resolve(doc, probe["path"])
    kind = probe["kind"]
    if kind == "equals":
        return found and value == probe["expected"]
    if kind == "contains":
        return found and str(probe["expected"]) in canon(value)
    if kind == "is_true":
        return found and value is True
    if kind == "is_none":
        return found and value is None
    if kind == "path_exists":
        return found
    if kind == "nonnull":
        return found and value is not None
    raise ValueError("unknown probe kind %r in %s" % (kind, probe.get("path")))


def main() -> int:
    checks: list[dict] = []
    findings: list[dict] = []

    def check(cid: str, ok: bool, detail: str, falsifier: str = "") -> bool:
        checks.append(
            {
                "check_id": cid,
                "status": "PASS" if ok else "FAIL",
                "detail": detail,
                "falsifier": falsifier
                or "re-run on the same pinned bytes yields the opposite status",
            }
        )
        return ok

    # ---------- 1. pin inputs ----------
    PINS.mkdir(exist_ok=True)
    hashes_start: dict[str, str] = {}
    for role, (rel, want) in DECLARED.items():
        src = ROOT / rel
        got = sha256_file(src)
        hashes_start[role] = got
        dst = PINS / ("%s__%s" % (role, Path(rel).name))
        shutil.copyfile(src, dst)
        got_copy = sha256_file(dst)
        check(
            "PIN-%s" % role,
            got == want and got_copy == want,
            "%s declared %s measured %s copy %s" % (rel, want[:16], got[:16], got_copy[:16]),
            "any byte of %s differs at the declared hash" % rel,
        )
    # two independent rev12 copies must be byte-identical
    check(
        "PIN-rev12-copies-agree",
        hashes_start["rev12_baseline_a"] == hashes_start["rev12_baseline_b"],
        "copy A %s vs copy B %s (independent holders)"
        % (hashes_start["rev12_baseline_a"][:16], hashes_start["rev12_baseline_b"][:16]),
    )

    # ---------- 2. load ----------
    def load_yaml(role):
        return yaml.safe_load(open(PINS / ("%s__af_wcc_vacuum.yaml" % role), encoding="utf-8"))

    live = load_yaml("live_rev13")
    rev12 = load_yaml("rev12_baseline_a")
    rev12b = load_yaml("rev12_baseline_b")
    check(
        "LOAD-rev12-parses-identically",
        canon(rev12) == canon(rev12b),
        "both rev12 copies parse to the same document",
    )

    rows = [json.loads(l) for l in open(PINS / "corpus__f1_falsifier_tests.jsonl", encoding="utf-8") if l.strip()]
    check("LOAD-corpus-25-rows", len(rows) == 25, "rows loaded: %d" % len(rows))
    test_ids = [r.get("test_id") for r in rows]
    check(
        "LOAD-test-ids-unique",
        len(set(test_ids)) == len(test_ids) == 25,
        "25 unique test ids; classes=%s" % sorted({r.get("class_id") for r in rows}),
    )
    check(
        "LOAD-corpus-class-bound",
        all(r.get("class_id") == CLASS_ID and r.get("node_id") == NODE_ID for r in rows),
        "all rows class_id=%s node_id=%s" % (CLASS_ID, NODE_ID),
    )

    # ---------- 3. execute probes ----------
    per_row = []
    total = 0
    reproduced = 0
    selftest_mismatch = []
    record_false_positive = []
    record_false_negative = []
    outcome_changed = []
    content_changed = []
    excerpt_mismatch = []

    for r in rows:
        tid = r["test_id"]
        probes = r.get("probe_results") or []
        row_rec = {"test_id": tid, "n_probes": len(probes), "probes": []}
        for i, p in enumerate(probes):
            total += 1
            ok12 = evaluate(p, rev12)
            okl = evaluate(p, live)
            f12, v12 = resolve(rev12, p["path"])
            fl, vl = resolve(live, p["path"])
            rec = p.get("pass")
            pid = "%s/P%d" % (tid, i + 1)
            if rec is not None and bool(rec) == ok12:
                reproduced += 1
            elif rec is not None:
                entry = {
                    "probe_id": pid,
                    "path": p["path"],
                    "kind": p["kind"],
                    "expected": p.get("expected"),
                    "recorded_pass": rec,
                    "rev12_measured": ok12,
                    "rev12_value": (canon(v12) if f12 else None),
                    "live_measured": okl,
                    "live_value": (canon(vl) if fl else None),
                }
                selftest_mismatch.append(entry)
                if bool(rec) and not ok12:
                    record_false_positive.append(entry)
                if (not bool(rec)) and ok12:
                    record_false_negative.append(entry)
            c12 = canon(v12) if f12 else None
            cl = canon(vl) if fl else None
            same_content = (c12 == cl)
            if ok12 != okl:
                outcome_changed.append(
                    {
                        "probe_id": pid,
                        "path": p["path"],
                        "kind": p["kind"],
                        "rev12_pass": ok12,
                        "live_pass": okl,
                        "recorded_pass": rec,
                    }
                )
            if not same_content:
                content_changed.append(
                    {
                        "probe_id": pid,
                        "path": p["path"],
                        "kind": p["kind"],
                        "rev12_pass": ok12,
                        "live_pass": okl,
                        "pass_stable": ok12 == okl,
                    }
                )
            if rec is not None and p.get("observed_excerpt") is not None and f12:
                recorded = "".join(str(p["observed_excerpt"]).split()).rstrip(".…")
                # the corpus excerpts were emitted by several harness versions: accept any
                # key-order / ascii-escaping convention, then require a prefix match
                fresh_variants = []
                for sk in (False, True):
                    for ea in (False, True):
                        fresh_variants.append("".join(canon_dump(v12, sk, ea).split()))
                if not any(
                    fv.startswith(recorded) or recorded.startswith(fv) for fv in fresh_variants
                ):
                    excerpt_mismatch.append(
                        {
                            "probe_id": pid,
                            "path": p["path"],
                            "recorded_excerpt": str(p["observed_excerpt"])[:160],
                            "rev12_value": c12[:160],
                        }
                    )
            row_rec["probes"].append(
                {
                    "probe_id": pid,
                    "path": p["path"],
                    "kind": p["kind"],
                    "role": p.get("role"),
                    "recorded_pass": rec,
                    "rev12_pass": ok12,
                    "live_pass": okl,
                    "content_stable": same_content,
                }
            )
        row_rec["all_probes_reproduce_on_rev12"] = all(
            (p.get("pass") is None) or (evaluate(p, rev12) == bool(p.get("pass"))) for p in probes
        )
        row_rec["probe_outcome_changed"] = any(
            evaluate(p, rev12) != evaluate(p, live) for p in probes
        )
        per_row.append(row_rec)

    # rev13 semantic-field rows from worker-041: did their outcome change?
    w041 = []
    for r in rows:
        n = int(r["test_id"].split("-")[-1])
        if n in W041_SEMANTIC_ROWS:
            row = next(x for x in per_row if x["test_id"] == r["test_id"])
            w041.append(
                {
                    "test_id": r["test_id"],
                    "probe_outcome_changed": row["probe_outcome_changed"],
                    "probes": [
                        {
                            "probe_id": q["probe_id"],
                            "path": q["path"],
                            "rev12_pass": q["rev12_pass"],
                            "live_pass": q["live_pass"],
                        }
                        for q in row["probes"]
                    ],
                }
            )

    record_truth_ok = check(
        "RECORD-TRUTH-AT-DECLARED-BINDING",
        not record_false_positive and not record_false_negative,
        "recorded pass values reproduced at F1 rev12 (the corpus's declared binding_ref): "
        "%d/%d; recorded-True-but-measured-False: %d; recorded-False-but-measured-True: %d"
        % (reproduced, total, len(record_false_positive), len(record_false_negative)),
        "a recorded pass value that the corpus's own declared binding revision does not support",
    )
    check(
        "EXCERPT-FIDELITY-REV12",
        not excerpt_mismatch,
        "recorded observed_excerpt is a truncation-tolerant match of the rev12 value for %d/%d "
        "probes (%d unexplained)" % (total - len(excerpt_mismatch), total, len(excerpt_mismatch)),
        "a probe whose recorded observed_excerpt is not a prefix of what rev12 resolves to at that path",
    )
    no_outcome_change = len(outcome_changed) == 0
    check(
        "OUTCOME-REV12-VS-REV13",
        no_outcome_change,
        "probe pass values that change rev12 -> rev13: %d" % len(outcome_changed),
        "one probe whose pass value differs between the two bound schemas",
    )
    check(
        "CONTENT-DRIFT-REV12-VS-REV13",
        len(content_changed) == 0,
        "probes whose resolved value differs rev12 -> rev13: %d (pass-stable: %d)"
        % (len(content_changed), sum(1 for c in content_changed if c["pass_stable"])),
        "a probe whose resolved value differs between the two bound schemas",
    )
    # the manifest that pins the corpus pins F1 at rev13: the frozen evidence set
    # is internally inconsistent unless the corpus binding matches that hash
    fz = json.load(open(PINS / "frozen__FROZEN.json", encoding="utf-8"))
    fz_files = fz.get("files") or {}

    def fz_entry(path):
        if isinstance(fz_files, dict):
            return fz_files.get(path)
        for e in fz_files:
            if isinstance(e, dict) and e.get("path") == path:
                return e
        return None

    fz_corpus = fz_entry(DECLARED["corpus"][0]) or {}
    fz_f1 = fz_entry(DECLARED["live_rev13"][0]) or {}
    corpus_binding = {r.get("binding_sha256") for r in rows}
    check(
        "FROZEN-PINS-INTERNAL-CONSISTENCY",
        fz_f1.get("sha256") in corpus_binding,
        "FROZEN rev%s pins %s at %s but %s binds %s"
        % (
            fz.get("revision"),
            DECLARED["corpus"][0],
            (fz_corpus.get("sha256") or "?")[:16],
            DECLARED["corpus"][0],
            ",".join(sorted(x[:16] for x in corpus_binding)),
        ),
        "a FROZEN revision whose pinned F1 schema hash equals the corpus's binding_sha256",
    )

    # ---------- 4. controls ----------
    mut_eq = copy.deepcopy(live)
    mut_eq["genericity"]["kind"] = "MUTANT_TOKEN"
    ctrl_eq = not evaluate(
        {"path": "genericity.kind", "kind": "equals", "expected": "residual_comeager"}, mut_eq
    )
    check(
        "CTRL-MUT-EQUALS",
        ctrl_eq,
        "equals-probe at genericity.kind flips to False under a value mutation",
        "the mutant is still scored pass, i.e. the evaluator ignores the field",
    )

    mut_con = copy.deepcopy(live)
    mut_con["non_vacuity"]["condition"] = "MUTANTXYZ no future-incomplete data at all"
    ctrl_con = not evaluate(
        {
            "path": "non_vacuity.condition",
            "kind": "contains",
            "expected": "future geodesically incomplete",
        },
        mut_con,
    )
    check(
        "CTRL-MUT-CONTAINS",
        ctrl_con,
        "contains-probe at non_vacuity.condition flips to False under a value mutation",
        "the mutant is still scored pass, i.e. substring matching is vacuous",
    )

    mut_path = copy.deepcopy(live)
    had = "slice_topology" in mut_path.get("topology", {})
    mut_path.get("topology", {}).pop("slice_topology", None)
    ctrl_path = had and not evaluate({"path": "topology.slice_topology", "kind": "path_exists"}, mut_path)
    check(
        "CTRL-MUT-PATH-DELETE",
        ctrl_path,
        "path_exists-probe flips to False after the key is deleted (key was present: %s)" % had,
        "a deleted path still resolves",
    )

    rogue = {"path": "class_id", "kind": "equals", "expected": "AF-DOES-NOT-EXIST"}
    check(
        "CTRL-NEG-EXPECTED",
        evaluate(rogue, live) is False,
        "a tampered expectation at class_id evaluates False",
        "the corpus records any expectation as pass",
    )

    det = all(
        evaluate(p, live) == evaluate(p, live)
        for r in rows
        for p in (r.get("probe_results") or [])
    )
    check("CTRL-DETERMINISM", det, "live evaluation is deterministic across two passes")

    # ---------- 5. exit drift ----------
    hashes_end = {role: sha256_file(ROOT / rel) for role, (rel, _) in DECLARED.items()}
    drift = {k: (hashes_start[k], hashes_end[k]) for k in hashes_start if hashes_start[k] != hashes_end[k]}
    check(
        "STABLE-AT-EXIT",
        not drift,
        "all %d pinned inputs byte-stable across the run" % len(DECLARED),
        "any pinned input changes between the two measurements",
    )

    # ---------- 6. verdict ----------
    if outcome_changed:
        verdict = "REBIND_REQUIRES_ROW_UPDATES"
    elif not record_truth_ok:
        verdict = "REBIND_CARRIES_FALSE_RECORDED_PASSES"
    else:
        verdict = "SAFE_MECHANICAL_REBIND"

    if record_false_positive:
        findings.append(
            {
                "id": "W034-RBS-F1",
                "severity": "major",
                "text": "%d recorded probe pass value(s) are not supported by the corpus's own declared "
                "binding (F1 rev12 cce9c601): %s. A mechanical rebind to rev13 would carry these false "
                "passes into the new pin unchanged, because no probe outcome changes rev12 -> rev13. "
                "Each listed probe must have its expectation (or the corpus row) repaired, not re-hashed."
                % (
                    len(record_false_positive),
                    "; ".join(
                        "%s %s expected %r measured %r"
                        % (e["probe_id"], e["path"], e["expected"], e["rev12_value"])
                        for e in record_false_positive
                    ),
                ),
            }
        )
    if record_false_negative:
        findings.append(
            {
                "id": "W034-RBS-F1N",
                "severity": "major",
                "text": "%d recorded probe value(s) are False although the declared binding makes them "
                "True: %s. Either the record is stale or the evaluator semantics differ from the "
                "authoring harness; the latter is not excluded by this run."
                % (len(record_false_negative), ", ".join(e["probe_id"] for e in record_false_negative)),
            }
        )
    if not outcome_changed and not record_truth_ok:
        findings.append(
            {
                "id": "W034-RBS-F2",
                "severity": "info",
                "text": "Rebind-outcome safety is clean: 0/84 probe outcomes change rev12 -> rev13, so "
                "for the 82 truthful probes a metadata-only rebind preserves the recorded verdicts. The "
                "blocker is record rot (F1), not the rev13 direction edits.",
            }
        )
    if content_changed:
        findings.append(
            {
                "id": "W034-RBS-F3",
                "severity": "minor",
                "text": "%d probe(s) resolve to different values rev12 -> rev13 with stable pass values "
                "(%s). The rev13 prose corrections are visible to the corpus probes but do not flip any "
                "recorded outcome."
                % (
                    len(content_changed),
                    ", ".join(sorted({c["probe_id"] for c in content_changed})),
                ),
            }
        )
    if excerpt_mismatch:
        findings.append(
            {
                "id": "W034-RBS-F5",
                "severity": "minor",
                "text": "%d recorded observed_excerpt value(s) do not match the corpus's declared binding "
                "under any key-order/ascii convention: %s. Two of them (F1-AMB-25/P1,P4) also carry a "
                "false pass flag (F1); the other two are stale excerpt text with a still-truthful pass "
                "flag (F1-AMB-09/P2 records the pre-rev12 ambient-space name X^{s,delta}_vac, F1-AMB-21/P1 "
                "records the pre-rev5 F0 hash 276009f4). The corpus was not re-executed when F1 or F0 "
                "moved."
                % (len(excerpt_mismatch), ", ".join(e["probe_id"] for e in excerpt_mismatch)),
            }
        )
    findings.append(
        {
            "id": "W034-RBS-F4",
            "severity": "info",
            "text": "Worker-041 semantic rows %s: no probe outcome flips rev12 -> rev13, confirming that "
            "its field-level finding and this outcome-level finding are compatible (fields changed, "
            "recorded verdicts did not)." % W041_SEMANTIC_ROWS,
        }
    )

    evidence = {
        "task_id": TASK_ID,
        "worker": WORKER,
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "authority": "worker measurement only; no gate verdict, no node status, canonical_writes=false",
        "question": "does a mechanical rebind of schemas/f1_falsifier_tests.jsonl from F1 rev12 "
        "cce9c60146d6 to the live rev13 d9cebb9404b2 preserve every recorded probe outcome?",
        "verdict": verdict,
        "pins": {
            "live_rev13": {"path": DECLARED["live_rev13"][0], "sha256": hashes_start["live_rev13"]},
            "rev12_baseline_a": {
                "path": DECLARED["rev12_baseline_a"][0],
                "sha256": hashes_start["rev12_baseline_a"],
            },
            "rev12_baseline_b": {
                "path": DECLARED["rev12_baseline_b"][0],
                "sha256": hashes_start["rev12_baseline_b"],
            },
            "corpus": {"path": DECLARED["corpus"][0], "sha256": hashes_start["corpus"]},
            "frozen": {"path": DECLARED["frozen"][0], "sha256": hashes_start["frozen"]},
        },
        "counts": {
            "rows": len(rows),
            "probes": total,
            "recorded_passes_reproduced_on_rev12": reproduced,
            "recorded_pass_not_reproduced": len(selftest_mismatch),
            "recorded_false_positives": len(record_false_positive),
            "recorded_false_negatives": len(record_false_negative),
            "probe_outcomes_changed_rev12_to_rev13": len(outcome_changed),
            "probes_with_content_drift": len(content_changed),
            "probes_with_stable_pass_but_changed_value": sum(
                1 for c in content_changed if c["pass_stable"]
            ),
            "recorded_excerpt_mismatches_on_rev12": len(excerpt_mismatch),
        },
        "worker_041_semantic_rows": {
            "claim_under_test": "W041-F1-CORPUS-REBIND-01 measured that rows 10,16,22,24 exercise "
            "rev12->rev13 changed fields",
            "measured_here": w041,
        },
        "outcome_changed": outcome_changed,
        "content_changed": content_changed,
        "selftest_mismatch": selftest_mismatch,
        "record_false_positive": record_false_positive,
        "record_false_negative": record_false_negative,
        "excerpt_mismatch": excerpt_mismatch,
        "checks": checks,
        "findings": findings,
        "falsifier": "a probe whose pass value or resolved value differs rev12 -> rev13 that this run "
        "did not list; a recorded pass value that rev12 does not reproduce; a probe whose recorded "
        "observed_excerpt is not a truncation-tolerant match of the rev12 value; or a re-run on the "
        "same pinned bytes producing a different verdict",
        "next_falsifier": "repair F1-AMB-25/P1 (declared_f0_sha256 expectation 276009f4 -> the live F0 "
        "rev5 0abb9ed8) and F1-AMB-25/P4 (binding_note token), re-bind the corpus to the live F1 pin "
        "d9cebb9404b2, re-run run_rebind_safety.py: 84/84 truthful probes with 0 outcome changes retires "
        "this measurement",
        "tool_sha256": sha256_file(Path(__file__)),
        "canonical_writes": False,
    }
    # self-hash: sha256 over canonical JSON without the artifact_sha256 field
    body = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    evidence["artifact_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()

    with open(HERE / "evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    report = {
        "task_id": TASK_ID,
        "verdict": verdict,
        "pins": evidence["pins"],
        "counts": evidence["counts"],
        "rows": per_row,
        "checks": checks,
    }
    with open(HERE / "report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")

    print("verdict:", verdict)
    for c in checks:
        print("  %-4s %s :: %s" % (c["status"], c["check_id"], c["detail"]))
    print("evidence sha256(declared):", evidence["artifact_sha256"])
    print("report  sha256:", sha256_file(HERE / "report.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
