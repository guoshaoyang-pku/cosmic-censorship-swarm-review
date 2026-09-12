#!/usr/bin/env python3
"""W034-F1-FREEZE-CANDIDATE-DERIVATION-01

Derive the union F1 falsifier-corpus freeze candidate from the two independently
produced repair lineages, at the FROZEN rev29 pins, and adjudicate the derived
bytes with the *same* battery that produced W034-F1-REPAIR-CANDIDATE-ADJUDICATION-01.

Object under test
-----------------
schemas/f1_falsifier_tests.jsonl (node F1, class AF-WCC-VAC-GEN, gate G-FORM),
measured 56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e at read time.
The live F1 schema is rev13 d9cebb9404b2e79e; the live F0 taxonomy is rev5
0abb9ed8a96135c9; FROZEN rev29 is 815e08079aefbc16.

Inputs (all pinned and re-measured; abort on any mismatch)
----------------------------------------------------------
  schemas/f1_falsifier_tests.jsonl                         56bcb4b3234bc86c
  schemas/af_wcc_vacuum.yaml (F1 rev13)                    d9cebb9404b2e79e
  research_map/formulation_taxonomy.yaml (F0 rev5)         0abb9ed8a96135c9
  artifacts/formulation/FROZEN.json (rev29)                815e08079aefbc16
  artifacts/worker-031/f1_suite_repin_dryrun/patched/f1_falsifier_tests.tierB.jsonl
                                                           785e6a4e53d64377
  artifacts/worker-077/f1_suite_rebind_dryrun/run/proposed_f1_falsifier_tests.rev13.mechanical.jsonl
                                                           306480f5f45acc50
  artifacts/worker-077/f1_suite_rebind_dryrun/run/proposed_f1_falsifier_tests.rev13.f0refresh.jsonl
                                                           739d5b40dc97111d
  snapshots rev12/rev11 of F1 (via the adjudicator's declared pins)

Derived write set (only these, nothing else)
--------------------------------------------
  D1 record fidelity: for every probe whose recorded observed_excerpt does not
     resolve to the live rev13 value, take the faithful excerpt from the W077
     mechanical lineage when it matches rev13, else recompute it from rev13.
     Residual set at derivation time: F1-AMB-09 genericity.ambient_space,
     F1-AMB-21 f0_binding.declared_f0_sha256.
  D2 row provenance: binding_frozen_revision_schema=13 and binding_frozen_revision=29
     on every row; rebound_at set to the derivation stamp REBIND_AT; rebind_note added.
  Base bytes: cand_w031_tierB (row rebinding to F1 rev13 + F1-AMB-25 P1/P4 anchor
  repair already adjudicated truthful).  Historical fields are never rewritten.

Adjudication
------------
  (a) full C1-C8 battery + 8 mutant controls imported verbatim from
      artifacts/worker-034/f1_repair_candidate_adjudication/adjudicate_f1_repair_candidates.py;
  (b) W029-equivalent materiality checks B1/B2/X1 plus the 84-probe recomputation
      (the W029 instrument itself is hard-bound to the canonical path and cannot be
      pointed at a candidate);
  (c) negative controls: original corpus, tierB, w077_f0refresh, plus reverted-excerpt,
      reverted-provenance, rewritten-history and dropped-row mutants of the derived bytes;
  (d) byte determinism: derive twice, compare digests;
  (e) pin stability: every declared pin re-measured at the end.

Authority: worker evidence only.  No gate verdict, no node status, no validation_status,
no canonical write.  The candidate is a proposal; the F1 owner re-stamps rebound_at at
publication.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-034/f1_suite_freeze_candidate"
CAND = OUT / "candidate"
ADJ_PATH = (
    ROOT
    / "artifacts/worker-034/f1_repair_candidate_adjudication"
    / "adjudicate_f1_repair_candidates.py"
)
CST = timezone(timedelta(hours=8))

TASK_ID = "W034-F1-FREEZE-CANDIDATE-DERIVATION-01"
NODE_ID = "F1"
CLASS_ID = "AF-WCC-VAC-GEN"
GATE = "G-FORM"
# Fixed derivation stamp: makes the candidate bytes deterministic.  Chosen at/before the
# derivation instant (no future-dating); the owner may re-stamp at publication, and the
# battery only requires a fresh ISO-parseable value.
REBIND_AT = "2026-09-12T01:20:30+08:00"
REBIND_NOTE = (
    "W034-F1-FREEZE-CANDIDATE-DERIVATION-01: rebound to F1 rev13 d9cebb9404b2 under "
    "FROZEN rev29 815e08079aef; base cand_w031_tierB 785e6a4e53d6 + W077 faithful "
    "observed_excerpt refresh; proposal only, owner re-stamps at publication."
)

FIXED_EXCERPT_SOURCES = {
    # probes whose excerpt the base lineage did not refresh; W077 mechanical has
    # faithful rev13 excerpts for both.
    ("F1-AMB-09", "genericity.ambient_space"),
    ("F1-AMB-21", "f0_binding.declared_f0_sha256"),
}

ALLOWED_SCOPES = {
    "row_binding_or_provenance",
    "observation",
    "cross_artifact_binding",
    "citation",
    "probe_expectation",
    "historical_delta",
}


def load_adjudicator():
    spec = importlib.util.spec_from_file_location("w034_adj", ADJ_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_jsonl(p: Path):
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def dump_jsonl(rows) -> bytes:
    """Canonical corpus serialization: insertion-order JSON, one row per line."""
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")


def derive(adj, orig_rows, tierb_rows, mech_rows):
    """Build the derived rows + a per-pointer derivation ledger.  Pure function."""
    import copy

    derived = copy.deepcopy(tierb_rows)
    mech = {r["test_id"]: r for r in mech_rows}
    ledger = []

    # D1: excerpt fidelity, minimal change set.
    for row in derived:
        mr = mech[row["test_id"]]
        for probe in row["probe_results"]:
            found, value = adj.resolve(adj_live, probe["path"])
            rec = probe.get("observed_excerpt")
            if rec is None or not found or adj.excerpt_matches(rec, value):
                continue
            mp = next((p for p in mr["probe_results"] if p["path"] == probe["path"]), None)
            if mp is not None and adj.excerpt_matches(mp.get("observed_excerpt"), value):
                new = mp["observed_excerpt"]
                source = "w077_mechanical"
            else:
                new = json.dumps(value, ensure_ascii=False)
                source = "recomputed_from_rev13"
            ledger.append(
                {
                    "write": "D1_excerpt_fidelity",
                    "test_id": row["test_id"],
                    "pointer": "probe_results/%s/observed_excerpt" % probe["path"],
                    "before": rec,
                    "after": new,
                    "source": source,
                }
            )
            probe["observed_excerpt"] = new

    # D2: complete rev13 / FROZEN rev29 provenance on every row.
    for row in derived:
        for field, after in (
            ("binding_frozen_revision_schema", 13),
            ("binding_frozen_revision", 29),
            ("rebound_at", REBIND_AT),
            ("rebind_note", REBIND_NOTE),
        ):
            before = row.get(field)
            row[field] = after
            if before != after:
                ledger.append(
                    {
                        "write": "D2_row_provenance",
                        "test_id": row["test_id"],
                        "pointer": field,
                        "before": before,
                        "after": after,
                        "source": "derivation",
                    }
                )

    # rows keep the base lineage's insertion order (the corpus serializer preserves it)
    return derived, ledger


def materiality_checks(adj, rows, orig_rows, live_doc):
    """W029-equivalent B1/B2/X1 + 84-probe recomputation, on candidate bytes."""
    checks = []

    def chk(cid, ok, measured, falsifier):
        checks.append(
            {
                "check_id": cid,
                "status": "PASS" if ok else "FAIL",
                "measured": measured,
                "falsifier": falsifier,
            }
        )
        return ok

    live_f1 = adj.sha256_file(ROOT / "schemas/af_wcc_vacuum.yaml")
    bfrs = sorted({r.get("binding_frozen_revision_schema") for r in rows})
    bindings = sorted({r.get("binding_sha256") for r in rows})
    reb = sorted({r.get("rebound_at") for r in rows})
    orig_reb = sorted({r.get("rebound_at") for r in orig_rows})
    bound_live = sum(1 for r in rows if r.get("binding_sha256") == adj.F1_LIVE_SHA)
    chk(
        "B1-ALL-25-ROWS-REBOUND-TO-LIVE-REV13",
        bfrs == [13] and bindings == [adj.F1_LIVE_SHA] and bound_live == 25
        and reb and not (set(reb) & set(orig_reb)),
        {
            "binding_frozen_revision_schema": bfrs,
            "distinct_bindings": [b[:12] for b in bindings],
            "rows": len(rows),
            "rows_bound_to_live_rev13": bound_live,
            "rebound_at": reb,
            "original_rebound_at": orig_reb,
        },
        "any row still bound to cce9c601 (rev12), any binding_frozen_revision_schema != 13, "
        "or a rebound_at unchanged from the rev29 corpus",
    )
    chk(
        "B2-SUITE-BINDING-EQUALS-CANONICAL-F1-SHA",
        live_f1 == adj.F1_LIVE_SHA and all(r.get("binding_sha256") == live_f1 for r in rows),
        {"canonical_f1": live_f1, "distinct_suite_binding": [b[:12] for b in bindings]},
        "the canonical F1 sha256 differs from the suite binding (the vendor hard check C1a)",
    )

    stale = []
    for r in rows:
        for ca in r.get("cross_artifact") or []:
            if not isinstance(ca, dict):
                continue
            p = ROOT / str(ca.get("path", ""))
            ok = (
                p.is_file()
                and adj.sha256_file(p) == ca.get("sha256")
                and ca.get("sha256") == adj.F0_LIVE_SHA
            )
            if not ok:
                stale.append(
                    {
                        "test_id": r["test_id"],
                        "declared_path": ca.get("path"),
                        "stored": ca.get("sha256"),
                        "live": adj.sha256_file(p) if p.is_file() else None,
                    }
                )
    chk(
        "X1-CROSS-ARTIFACT-DECLARATIONS-RESOLVE-TO-LIVE-F0",
        not stale,
        {"checked": sum(len(r.get("cross_artifact") or []) for r in rows), "stale": stale},
        "a cross_artifact declaration whose path does not resolve to the live F0 rev5 hash",
    )

    invalidated, false_rows, probes, passed = [], [], 0, 0
    for r in rows:
        for p in r["probe_results"]:
            probes += 1
            if adj.evaluate(p, live_doc):
                passed += 1
            else:
                invalidated.append({"test_id": r["test_id"], "path": p["path"],
                                    "expected": p.get("expected")})
                if r["test_id"] not in false_rows:
                    false_rows.append(r["test_id"])
    chk(
        "M2-84-PROBES-RECOMPUTE-TRUE-AT-REV13",
        probes == 84 and passed == 84 and not false_rows,
        {"probes_total": probes, "recomputed_pass_rev13": passed,
         "false_rows": false_rows, "invalidated": invalidated},
        "any probe whose recorded expectation rev13 does not support (pre-existing false rows)",
    )

    schema_f0 = (live_doc.get("f0_binding") or {}).get("declared_f0_sha256")
    chk(
        "C9-SCHEMA-F0-BINDING-EQUALS-LIVE-F0",
        schema_f0 == adj.F0_LIVE_SHA,
        {"f1_f0_binding_declared": schema_f0, "live_f0": adj.F0_LIVE_SHA},
        "the F1 schema's own f0_binding declaration is stale (a cross-artifact pin split)",
    )
    return checks


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    CAND.mkdir(parents=True, exist_ok=True)
    adj = load_adjudicator()
    global adj_live
    adj_live = None

    # ---- pin verification (abort on any mismatch) ---------------------------
    pin_checks = []
    pins_now = {}
    for role, (rel, want) in adj.DECLARED.items():
        src = ROOT / rel
        if not src.is_file():
            pin_checks.append({"pin": role, "path": rel, "declared": want,
                               "measured": None, "match": False})
            continue
        got = adj.sha256_file(src)
        pins_now[role] = got
        pin_checks.append({"pin": role, "path": rel, "declared": want,
                           "measured": got, "match": got == want})
    pins_ok = all(p["match"] for p in pin_checks)
    if not pins_ok:
        report = {
            "task_id": TASK_ID, "verdict": "ABORT_PIN_MISMATCH",
            "pin_checks": pin_checks,
            "falsifier": "a declared pin whose measured sha256 differs at read time",
        }
        (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("PIN MISMATCH - aborting", file=sys.stderr)
        for p in pin_checks:
            if not p["match"]:
                print("  ", p, file=sys.stderr)
        return 2

    orig_rows = adj.load_jsonl(ROOT / adj.DECLARED["corpus_orig"][0])
    tierb_rows = adj.load_jsonl(ROOT / adj.DECLARED["cand_w031_tierB"][0])
    mech_rows = adj.load_jsonl(ROOT / adj.DECLARED["cand_w077_mechanical"][0])
    f0ref_rows = adj.load_jsonl(ROOT / adj.DECLARED["cand_w077_f0refresh"][0])
    tierA_rows = adj.load_jsonl(ROOT / adj.DECLARED["cand_w031_tierA"][0])
    live_doc = adj.yaml.safe_load((ROOT / adj.DECLARED["f1_live_rev13"][0]).read_text())
    rev12_doc = adj.yaml.safe_load((ROOT / adj.DECLARED["f1_rev12"][0]).read_text())
    authoring_doc = adj.yaml.safe_load((ROOT / adj.DECLARED["f1_authoring_rev11"][0]).read_text())
    adj_live = live_doc

    # ---- derivation (twice, for byte determinism) ---------------------------
    derived_rows, ledger = derive(adj, orig_rows, tierb_rows, mech_rows)
    derived_rows_b, ledger_b = derive(adj, orig_rows, tierb_rows, mech_rows)
    cand_bytes = dump_jsonl(derived_rows)
    cand_bytes_b = dump_jsonl(derived_rows_b)
    deterministic = cand_bytes == cand_bytes_b and ledger == ledger_b
    cand_sha = hashlib.sha256(cand_bytes).hexdigest()
    cand_path = CAND / "f1_falsifier_tests.rev13.frozen29.derived.jsonl"
    cand_path.write_bytes(cand_bytes)

    # ---- primary battery on the derived bytes -------------------------------
    res = adj.check_candidate("cand_w034_derived", derived_rows, orig_rows, live_doc,
                              rev12_doc, authoring_doc)
    res["sha256"] = cand_sha
    res["bytes"] = len(cand_bytes)
    res["controls"] = adj.run_mutants("cand_w034_derived", derived_rows, orig_rows,
                                      live_doc, rev12_doc, authoring_doc)
    res["controls_all_caught"] = all(c["caught"] for c in res["controls"])
    res["changed_pointers"] = []
    for ro, rc in zip(orig_rows, derived_rows):
        for ptr, before, after in adj.leaf_diff(ro, rc, "/" + ro["test_id"]):
            res["changed_pointers"].append(
                {"pointer": ptr, "before": before, "after": after,
                 "scope": adj.scope_class(ptr)}
            )
    res["semantic_forbidden_changes"] = [
        d for d in res["changed_pointers"] if d["scope"] == "SEMANTIC_FORBIDDEN"
    ]
    res["out_of_write_set_changes"] = [
        d for d in res["changed_pointers"] if d["scope"] not in ALLOWED_SCOPES
    ]
    res["changed_pointers_by_scope"] = {}
    for d in res["changed_pointers"]:
        res["changed_pointers_by_scope"].setdefault(d["scope"], 0)
        res["changed_pointers_by_scope"][d["scope"]] += 1

    mat = materiality_checks(adj, derived_rows, orig_rows, live_doc)

    # ---- lineage re-adjudication (independent replication of the prior task) -
    lineage = {}
    for name, rows in (
        ("cand_w031_tierA", tierA_rows),
        ("cand_w031_tierB", tierb_rows),
        ("cand_w077_mechanical", mech_rows),
        ("cand_w077_f0refresh", f0ref_rows),
    ):
        r = adj.check_candidate(name, rows, orig_rows, live_doc, rev12_doc, authoring_doc)
        lineage[name] = {
            "sha256": pins_now[name],
            "freeze_ready": r["freeze_ready"],
            "failed_checks": [c["check_id"] for c in r["checks"] if c["status"] == "FAIL"],
        }

    # ---- negative controls on the derived bytes -----------------------------
    import copy

    def failed_checks(rows):
        r = adj.check_candidate("neg", rows, orig_rows, live_doc, rev12_doc, authoring_doc)
        return [c["check_id"] for c in r["checks"] if c["status"] == "FAIL"]

    negatives = []
    for name, rows, expect in (
        ("N1_original_corpus", orig_rows, "C2-ROW-BINDING-REV13"),
        ("N2_base_tierB", tierb_rows, "C6-EXCERPT-FIDELITY-REV13"),
        ("N3_w077_f0refresh", f0ref_rows, "C8-HISTORY-PRESERVED"),
    ):
        f = failed_checks(rows)
        negatives.append({"control": name, "expected_failure_present": expect in f,
                          "observed_failures": f, "caught": expect in f})
    m = copy.deepcopy(derived_rows)
    row09 = next(r for r in m if r["test_id"] == "F1-AMB-09")
    p = next(pp for pp in row09["probe_results"]
             if pp["path"] == "genericity.ambient_space")
    p["observed_excerpt"] = json.dumps("stale rev12 text", ensure_ascii=False)
    f = failed_checks(m)
    negatives.append({"control": "N4_excerpt_reverted", "expected_failure_present":
                      "C6-EXCERPT-FIDELITY-REV13" in f, "observed_failures": f,
                      "caught": "C6-EXCERPT-FIDELITY-REV13" in f})
    m = copy.deepcopy(derived_rows)
    m[0]["binding_frozen_revision_schema"] = 12
    f = failed_checks(m)
    negatives.append({"control": "N5_provenance_reverted", "expected_failure_present":
                      "C7-PROVENANCE-COMPLETE" in f, "observed_failures": f,
                      "caught": "C7-PROVENANCE-COMPLETE" in f})
    m = copy.deepcopy(derived_rows)
    m[0]["binding_at_authoring"] = "schemas/af_wcc_vacuum.yaml#sha256:d9cebb9404b2e79e"
    f = failed_checks(m)
    negatives.append({"control": "N6_history_rewritten", "expected_failure_present":
                      "C8-HISTORY-PRESERVED" in f, "observed_failures": f,
                      "caught": "C8-HISTORY-PRESERVED" in f})
    m = copy.deepcopy(derived_rows)
    del m[3]
    f = failed_checks(m)
    negatives.append({"control": "N7_row_dropped", "expected_failure_present":
                      "C1-LOAD-25-ROWS-ORDER" in f, "observed_failures": f,
                      "caught": "C1-LOAD-25-ROWS-ORDER" in f})
    negatives_all_caught = all(n["caught"] for n in negatives)

    # ---- pin stability + verdict -------------------------------------------
    pin_recheck = {}
    for role, (rel, want) in adj.DECLARED.items():
        src = ROOT / rel
        pin_recheck[role] = {
            "measured_at_end": adj.sha256_file(src) if src.is_file() else None,
            "match": src.is_file() and adj.sha256_file(src) == want,
        }
    pins_stable = all(v["match"] for v in pin_recheck.values())

    required_pass = all(c["status"] == "PASS" for c in res["checks"]
                        if c["check_id"].startswith(("C1", "C2", "C3", "C4", "C5")))
    materiality_pass = all(c["status"] == "PASS" for c in mat)
    controls_pass = res["controls_all_caught"] and negatives_all_caught
    freeze_ready = (
        res["freeze_ready"] and materiality_pass and controls_pass and deterministic
        and pins_stable and not res["semantic_forbidden_changes"]
    )
    verdict = "FREEZE_READY_CANDIDATE_DERIVED" if freeze_ready else "NOT_FREEZE_READY"

    measured_at = datetime.now(CST).isoformat(timespec="seconds")
    report = {
        "task_id": TASK_ID,
        "actor": "worker-034",
        "created_at": measured_at,
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "verdict": verdict,
        "candidate": str(cand_path.relative_to(ROOT)),
        "candidate_sha256": cand_sha,
        "candidate_bytes": len(cand_bytes),
        "pins": {
            "corpus_orig": adj.DECLARED["corpus_orig"][1],
            "f1_live_rev13": adj.DECLARED["f1_live_rev13"][1],
            "f0_live_rev5": adj.DECLARED["f0_live_rev5"][1],
            "frozen_rev29": adj.DECLARED["frozen_rev29"][1],
            "base_tierB": pins_now["cand_w031_tierB"],
            "excerpt_source_w077_mechanical": pins_now["cand_w077_mechanical"],
        },
        "pins_all_match_at_read": pins_ok,
        "pins_stable_to_end": pins_stable,
        "deterministic_derivation": deterministic,
        "freeze_ready": freeze_ready,
        "required_pass": required_pass,
        "record_fidelity_pass": res["record_fidelity_pass"],
        "provenance_pass": res["provenance_pass"],
        "materiality_pass": materiality_pass,
        "controls_pass": controls_pass,
        "checks": res["checks"],
        "materiality_checks": mat,
        "lineage_replication": lineage,
        "mutant_controls": res["controls"],
        "negative_controls": negatives,
        "changed_pointers_by_scope": res["changed_pointers_by_scope"],
        "changed_pointer_count": len(res["changed_pointers"]),
        "semantic_forbidden_changes": res["semantic_forbidden_changes"],
        "out_of_write_set_changes": res["out_of_write_set_changes"],
        "derivation_ledger_count": len(ledger),
        "authority": "worker evidence only; no gate verdict, node status or "
                     "validation_status is claimed; the candidate is a proposal and is "
                     "not written to any canonical path",
        "falsifier": "any check in checks[]/materiality_checks[] whose status flips on "
                     "a re-run over the pinned bytes; any changed pointer outside the "
                     "declared D1/D2 write set; any pin whose sha256 differs at use time; "
                     "or a derived candidate not byte-identical across two derivations",
        "next_falsifier": "when the owner applies a corpus to schemas/f1_falsifier_tests.jsonl, "
                          "re-run this battery on the applied bytes and on FROZEN rev30's "
                          "per-file pin: the applied sha256 must equal either this derived "
                          "candidate (freeze-ready) or be re-adjudicated as a new candidate",
    }
    evidence = {
        "task_id": TASK_ID,
        "created_at": measured_at,
        "object_under_test": "schemas/f1_falsifier_tests.jsonl",
        "object_sha256_at_read": pins_now["corpus_orig"],
        "derived_candidate_sha256": cand_sha,
        "derived_candidate_relpath": str(cand_path.relative_to(ROOT)),
        "derivation_write_set": {
            "D1_excerpt_fidelity": sorted(FIXED_EXCERPT_SOURCES),
            "D2_row_provenance": {
                "binding_frozen_revision_schema": 13,
                "binding_frozen_revision": 29,
                "rebound_at": REBIND_AT,
                "rebind_note": REBIND_NOTE,
            },
        },
        "derivation_ledger": ledger,
        "changed_pointers": res["changed_pointers"],
        "pin_checks": pin_checks,
        "pin_recheck_at_end": pin_recheck,
        "check_detail": res,
        "materiality_checks": mat,
        "lineage_replication": lineage,
        "authority": "worker evidence only; read-only on canonical paths",
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    (OUT / "derivation_ledger.json").write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    )

    print(
        "verdict=%s sha256=%s bytes=%d checks=%d/%d mat=%d/%d controls_all=%s "
        "deterministic=%s pins_stable=%s"
        % (
            verdict,
            cand_sha,
            len(cand_bytes),
            sum(1 for c in res["checks"] if c["status"] == "PASS"),
            len(res["checks"]),
            sum(1 for c in mat if c["status"] == "PASS"),
            len(mat),
            controls_pass,
            deterministic,
            pins_stable,
        )
    )
    failed = [c["check_id"] for c in res["checks"] if c["status"] == "FAIL"] + [
        c["check_id"] for c in mat if c["status"] == "FAIL"
    ]
    if failed:
        print("failed:", failed)
    return 0 if freeze_ready else 3


if __name__ == "__main__":
    sys.exit(main())
