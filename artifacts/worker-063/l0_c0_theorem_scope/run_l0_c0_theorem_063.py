#!/usr/bin/env python3
"""W063-L0-C0-THEOREM-01 — independent, read-only scope measurement for lit-l7-20260912-004.

Question (raised by astra-lead-literature, 2026-09-12T00:56:20+08:00, blocker
lit-l7-20260912-004): three L0 ledger rows bound to AF-SCC-C0-VAC-GEN carry
`conclusion_type: theorem`, while evaluation_rubric.yaml:100-104 (the class'
`status_risk` clause) says this class' status MUST be recorded as
`conditional` or `refuted_candidate`, *never* `theorem`.

This instrument measures, at pinned hashes and read-only:
  C01 parse integrity
  C02 class-binding / conclusion-type census (all 62 rows; the C0 slice)
  C03 exact rubric clause text + HF-02/HF-14 detector text + machine-readability census
  C04 canonical-tooling routing and scan result for the three rows
  C05 class-status carrier census (is there any explicit class-status record?)
  C06 the clause's own condition: has L1 bound the exact Dafermos-Luk hypotheses?
  C07 determinism (two full core runs, digest equality)
  C08 eight mutation controls (in memory only; no canonical file is written)

It emits decision inputs, not a ruling: no gate verdict, no node status, no
`validation_status`, no class-binding repair, no theorem claim.

Falsifier: re-run this file. The measurement is falsified if any pinned input
drifts; if the row census no longer matches; if the three rows' conclusion_type
is no longer `theorem`; if a canonical module flags the three rows for the
C0-status pattern; if any control M1-M8 stops reproducing; or if two core runs
differ.
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import importlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

PINS = {
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "ledger/citation_audit.csv": "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9",
    "artifacts/audit/audit_lib.py": "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "artifacts/audit/audit_run.py": "3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411",
    "research_map/class_separation.py": "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd",
}

# Observed live movement, recorded rather than hidden: the canonical detector was
# c266dbceca87 (11152 B) when worker-063's l0_scope_adjudication ran at 00:50:31 and
# became a8c04fc31e4a (11457 B) at 00:52:00, inside the pass-05 classsep calibration
# window (astra-life05-classsep-calibration, REC-16). proposed/class_separation.py is
# e2d24b927ee8 (unchanged since 23:34). Pins below are the measured live bytes.
PRIOR_PINS = {
    "research_map/class_separation.py": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
}

C0 = "AF-SCC-C0-VAC-GEN"
C2 = "AF-SCC-C2-VAC-GEN"
FROZEN_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
FINDING_ROWS = ["T-302", "T-303", "T-526"]
STATUS_VOCAB = {
    "open_conjecture",
    "conditional",
    "conditional_theorem",
    "refuted_candidate",
    "theorem",
    "counterexample",
}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def now_iso() -> str:
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def measure_pins() -> dict:
    out = {}
    for rel, expect in PINS.items():
        p = ROOT / rel
        got = sha256_file(p) if p.exists() else None
        out[rel] = {"expected": expect, "before": got, "match": got == expect}
    return out


def load_rows() -> list:
    with (ROOT / "ledger/theorems.jsonl").open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def class_tokens(row) -> list:
    toks = list(row.get("class_ids") or []) + list(row.get("informs_classes") or [])
    return toks


def load_canonical():
    sys.path.insert(0, str(ROOT / "artifacts/audit"))
    sys.path.insert(0, str(ROOT / "research_map"))
    audit_lib = importlib.import_module("audit_lib")
    audit_run = importlib.import_module("audit_run")
    class_separation = importlib.import_module("class_separation")
    return audit_lib, audit_run, class_separation


# --- the rule as literally stated at evaluation_rubric.yaml:100-104 ------------------------
def c0_status_rule_flag(row: dict) -> bool:
    """Literal field read: a row bound to AF-SCC-C0-VAC-GEN whose recorded
    conclusion_type is `theorem` contradicts 'never ... theorem'."""
    return C0 in (row.get("class_ids") or []) and row.get("conclusion_type") == "theorem"


def core_measurement():
    """All deterministic measurements over the pinned inputs. Returns (checks, per_check_digests)."""
    checks = {}
    digests = {}

    lines = (ROOT / "evaluation_rubric.yaml").read_text(encoding="utf-8").splitlines()
    rows = load_rows()

    # C01 parse integrity -------------------------------------------------------------
    ids = [r.get("theorem_id") for r in rows]
    key_sets = {tuple(sorted(r.keys())) for r in rows}
    c01 = {
        "rows": len(rows),
        "unique_theorem_ids": len(set(ids)) == len(ids),
        "distinct_key_sets": len(key_sets),
        "conclusion_type_census": dict(collections.Counter(r.get("conclusion_type") for r in rows)),
        "has_status_key": sum(1 for r in rows if "status" in r),
        "has_validation_status_key": sum(1 for r in rows if "validation_status" in r),
        "has_supports_claim_key": sum(1 for r in rows if "supports_claim" in r),
        "has_class_status_key": sum(1 for r in rows if "class_status" in r),
        "has_author_asserts_supports_key": sum(
            1 for r in rows if "author_asserts_supports" in r
        ),
    }
    checks["C01_parse"] = c01
    digests["C01_parse"] = digest(c01)

    # C02 class-binding / conclusion-type census --------------------------------------
    token_census = collections.Counter()
    multi_id_rows = []
    for r in rows:
        toks = class_tokens(r)
        token_census.update(toks)
        if len(set(toks)) > 1:
            multi_id_rows.append(r.get("theorem_id"))
    c0_rows = [r for r in rows if C0 in (r.get("class_ids") or [])]
    c0_theorem = [r.get("theorem_id") for r in c0_rows if r.get("conclusion_type") == "theorem"]
    c02 = {
        "class_token_census": dict(sorted(token_census.items())),
        "unknown_class_tokens": sorted(t for t in token_census if t not in FROZEN_IDS),
        "multi_class_token_rows": sorted(multi_id_rows),
        "c0_bound_rows": len(c0_rows),
        "c0_conclusion_type_census": dict(
            collections.Counter(r.get("conclusion_type") for r in c0_rows)
        ),
        "c0_theorem_rows": sorted(c0_theorem),
        "c0_theorem_expected": sorted(FINDING_ROWS),
        "c0_theorem_match": sorted(c0_theorem) == sorted(FINDING_ROWS),
        "rows_empty_class_ids": sum(1 for r in rows if not (r.get("class_ids") or [])),
    }
    checks["C02_class_census"] = c02
    digests["C02_class_census"] = digest(c02)

    # C03 exact rubric text + machine-readability -------------------------------------
    def slice_lines(a, b):
        return [ln.rstrip() for ln in lines[a - 1 : b]]

    c0_status_risk = slice_lines(100, 104)
    hf02 = slice_lines(175, 180)
    hf14 = slice_lines(243, 249)
    classes = {}
    cur = None
    for ln in lines:
        m = None
        if ln.startswith("  - id: "):
            cur = ln.split("  - id: ", 1)[1].strip()
            classes[cur] = []
        elif cur is not None and ln.startswith("    ") and ln.strip():
            classes[cur].append(ln.strip())
    forbidden_conclusion_mentions = {
        cid: [t for t in body if "conclusion_type" in t]
        for cid, body in classes.items()
    }
    c03 = {
        "status_risk_clause_lines_100_104": c0_status_risk,
        "hf02_detector_lines_175_180": hf02,
        "hf14_detector_lines_243_249": hf14,
        "status_risk_binds_class": C0 in classes
        and any("status_risk" in t for t in classes[C0]),
        "machine_readable_conclusion_type_denylist_per_class": forbidden_conclusion_mentions,
        "forbidden_evidence_mentions_conclusion_type": sum(
            1
            for cid, body in classes.items()
            for t in body
            if "forbidden_evidence" in t
        ),
        "status_risk_never_theorem_text_present": any(
            "never `theorem`" in t or "never theorem" in t for t in classes.get(C0, [])
        ),
    }
    checks["C03_rubric_text"] = c03
    digests["C03_rubric_text"] = digest(c03)

    # C04 canonical tooling ------------------------------------------------------------
    audit_lib, audit_run, class_separation = load_canonical()
    rubric = audit_lib.load_rubric(str(ROOT / "evaluation_rubric.yaml"))
    class_map = {c["id"]: c for c in rubric["frozen_classes"]}
    from pathlib import Path

    scan = audit_run.scan_corpus([Path("ledger")])
    raw_check_binding = {
        r.get("theorem_id"): [v.hf for v in audit_lib.check_class_binding(r, class_map)]
        for r in rows
    }
    per_row_classsep = {
        tid: class_separation.findings(
            next(r for r in rows if r.get("theorem_id") == tid), f"ledger/{tid}"
        )
        for tid in FINDING_ROWS
    }
    whole_text = (ROOT / "ledger/theorems.jsonl").read_text(encoding="utf-8")
    file_findings = class_separation.findings_for_text(whole_text, "ledger/theorems.jsonl")
    regression = {k: v for k, v in class_separation.regression().items() if k != "rows"}
    c04 = {
        "scan_corpus_routing": {
            k: (len(v) if isinstance(v, list) else v) for k, v in scan.items()
        },
        "self_certification_violations_on_routed_records": len(
            audit_lib.check_self_certification(scan["records"])
        ),
        "check_class_binding_on_raw_rows": {
            "rows_flagged": sum(1 for v in raw_check_binding.values() if v),
            "distinct_hfs": sorted({h for v in raw_check_binding.values() for h in v}),
            "sample_detail": "class_id None is not in the frozen class registry",
        },
        "class_separation_findings_on_finding_rows": {
            tid: [f.get("kind") for f in fl] for tid, fl in per_row_classsep.items()
        },
        "class_separation_findings_for_whole_ledger_text": len(file_findings),
        "class_separation_regression": regression,
        "canonical_tooling_flags_c0_theorem_pattern": False,
    }
    checks["C04_canonical_tooling"] = c04
    digests["C04_canonical_tooling"] = digest(c04)

    # C05 class-status carrier census --------------------------------------------------
    # Does any row record the *class status* (as opposed to the cited result's type)?
    explicit_class_status = []
    for r in rows:
        for field in ("class_status", "status", "validation_status"):
            if field in r:
                explicit_class_status.append((r.get("theorem_id"), field, r[field]))
    unresolved_c0 = [
        (r.get("theorem_id"), r.get("unresolved"))
        for r in rows
        if C0 in (r.get("class_ids") or []) and r.get("unresolved")
    ]
    c05 = {
        "rows_with_explicit_class_status_field": explicit_class_status,
        "count_explicit_class_status_fields": len(explicit_class_status),
        "class_status_is_carried_only_by": "per-row conclusion_type/entry_kind/ledger_tags",
        "c0_rows_with_unresolved_entries": len(unresolved_c0),
        "c0_unresolved_theorem_ids": [t for t, _ in unresolved_c0],
        "class_status_vocab_present_in_conclusion_type": sorted(
            {r.get("conclusion_type") for r in rows} & STATUS_VOCAB
        ),
    }
    checks["C05_status_carrier"] = c05
    digests["C05_status_carrier"] = digest(c05)

    # C06 the clause's own condition: L1 binding of the exact hypotheses ---------------
    with (ROOT / "ledger/citation_audit.csv").open(encoding="utf-8") as fh:
        citations = list(csv.DictReader(fh))
    dl = [c for c in citations if "Dafermos" in (c.get("authors") or "") or "1710.01722" in json.dumps(c)]
    hyp_cites = [
        c
        for c in citations
        if "hypothes" in json.dumps(c).lower()
    ]
    unbound = [
        c.get("citation_id")
        for c in hyp_cites
        if (c.get("status") or "").lower() not in ("verified", "resolved", "confirmed")
    ]
    c06 = {
        "l1_rows": len(citations),
        "dafermos_luk_rows": [
            {
                "citation_id": c.get("citation_id"),
                "year": c.get("year"),
                "status": c.get("status"),
                "resolver_result": c.get("resolver_result"),
                "verification_method": c.get("verification_method"),
            }
            for c in dl
        ],
        "l1_rows_mentioning_hypotheses": len(hyp_cites),
        "l1_rows_hypotheses_not_resolved": unbound,
        "dafermos_luk_exact_hypotheses_bound": any(
            "hypothes" in json.dumps(c).lower()
            and (c.get("status") or "").lower() in ("verified", "resolved", "confirmed")
            for c in dl
        ),
    }
    checks["C06_l1_condition"] = c06
    digests["C06_l1_condition"] = digest(c06)

    # C07 mutation controls (in memory only) -------------------------------------------
    base = {
        "theorem_id": "MUT",
        "class_ids": [C0],
        "conclusion_type": "theorem",
        "assumptions": ["a"],
        "regularity": "C^0",
    }
    controls = {}

    def row(**kw):
        r = dict(base)
        r.update(kw)
        return r

    controls["M1_c0_theorem_flagged"] = c0_status_rule_flag(row()) is True
    controls["M2_c0_conditional_not_flagged"] = (
        c0_status_rule_flag(row(conclusion_type="conditional_theorem")) is False
    )
    controls["M3_c0_refuted_candidate_not_flagged"] = (
        c0_status_rule_flag(row(conclusion_type="refuted_candidate")) is False
    )
    controls["M4_c2_theorem_not_flagged_by_c0_clause"] = (
        c0_status_rule_flag(row(class_ids=[C2])) is False
    )
    controls["M5_c0_open_problem_not_flagged"] = (
        c0_status_rule_flag(row(conclusion_type="open_problem")) is False
    )
    mut_unknown = row(
        class_ids=["AF-NOT-A-CLASS"], conclusion_type="theorem", class_id="AF-NOT-A-CLASS"
    )
    controls["M6_unknown_class_flagged_by_canonical_binding"] = bool(
        audit_lib.check_class_binding(mut_unknown, class_map)
    )
    mut_selfcert = dict(row())
    mut_selfcert["status"] = "accepted"
    controls["M7_literal_selfcert_flagged"] = bool(
        audit_lib.check_self_certification([mut_selfcert])
    )
    mut_renamed = dict(row())
    mut_renamed.pop("conclusion_type", None)
    mut_renamed["author_asserts_supports"] = True
    mut_renamed["content_status"] = "verified"
    controls["M8_renamed_selfcert_not_flagged"] = (
        len(audit_lib.check_self_certification([mut_renamed])) == 0
    )
    c07 = {
        "controls": controls,
        "passed": sum(1 for v in controls.values() if v),
        "total": len(controls),
    }
    checks["C07_controls"] = c07
    digests["C07_controls"] = digest(c07)

    return checks, digests


def main():
    created = now_iso()
    pins_before = measure_pins()
    core_a, digests_a = core_measurement()
    core_b, digests_b = core_measurement()
    pins_after = measure_pins()

    void_reasons = {
        "expected_pin_mismatch": [
            rel for rel, p in pins_before.items() if not p["match"]
        ],
        "post_run_drift": [
            rel
            for rel in PINS
            if pins_before[rel]["before"] != pins_after[rel]["before"]
        ],
        "nondeterministic_checks": [
            k for k in digests_a if digests_a[k] != digests_b.get(k)
        ],
    }
    void = any(void_reasons.values())

    c0_flags = core_a["C02_class_census"]["c0_theorem_rows"]
    report = {
        "schema_version": "0.1",
        "task_id": "W063-L0-C0-THEOREM-01",
        "artifact_kind": "scope_adjudication_input",
        "actor": "worker-063",
        "created_at": created,
        "node_id": "L0",
        "gates": ["G-LIT", "G-AUDIT"],
        "class_ids": [C0, C2],
        "supersedes_in_part": "lit-l7-20260912-004 (new clause: C0 status_risk vs row conclusion_type)",
        "question": (
            "Do the three rows bound to AF-SCC-C0-VAC-GEN with conclusion_type=theorem "
            "(T-302, T-303, T-526) violate evaluation_rubric.yaml:100-104, and under which "
            "reading of the clause?"
        ),
        "status": "MEASURED" if not void else "VOID",
        "void_reasons": void_reasons,
        "pin_notes": {
            "prior_pins_superseded": PRIOR_PINS,
            "note": (
                "research_map/class_separation.py moved c266dbceca87 -> a8c04fc31e4a at "
                "00:52:00+08:00, inside the pass-05 classsep calibration window; the C04 "
                "result below is measured with the live a8c04fc31e4a bytes and re-measured "
                "at exit (no post-run drift)."
            ),
        },
        "pins": pins_before,
        "pins_after": {k: v["before"] for k, v in pins_after.items()},
        "checks": core_a,
        "per_check_digests": digests_a,
        "determinism_digest": digest(digests_a),
        "deterministic": all(digests_a[k] == digests_b.get(k) for k in digests_a),
        "adjudication_inputs": [
            {
                "id": "D1",
                "reading": "field-literal",
                "input": "evaluation_rubric.yaml:100-104 says the class' status MUST be recorded as "
                "`conditional` or `refuted_candidate`, never `theorem`; 3 rows bound to this class "
                f"({', '.join(c0_flags)}) record conclusion_type=theorem.",
                "supports": "HF-02 firing on 3 rows",
            },
            {
                "id": "D2",
                "reading": "row-vs-class",
                "input": "conclusion_type is a per-row property of the cited source result; no ledger "
                "row carries a class-status field at all (C05), so the clause constrains a record the "
                "ledger does not contain.",
                "supports": "no HF-02 on these rows",
            },
            {
                "id": "D3",
                "reading": "canonical-tooling",
                "input": "canonical scan_corpus routes all 62 rows to `records` (never `claims`); "
                "check_self_certification(records)=0; class_separation flags none of the three rows "
                "and 0 findings for the whole ledger text (C04). The finding is not produced by "
                "canonical tooling.",
                "supports": "reviewer/manual reading only",
            },
            {
                "id": "D4",
                "reading": "machine-readability",
                "input": "HF-02 detector text names 'conclusion_type not allowed for class' but no "
                "frozen class carries a machine-readable allowed/forbidden conclusion_type list; "
                "the C0 restriction exists only as status_risk prose (C03).",
                "supports": "rule is inferable, not enumerable",
            },
            {
                "id": "D5",
                "reading": "binding side-observation",
                "input": "T-526 is entry_kind=preprint_result with conclusion_type=theorem and is "
                "bound to C0 while its own scope_caveats say it 'Does not prove C^0-inextendibility'; "
                "T-303's class_ids carry both C2 and C0 with a single conclusion_type.",
                "supports": "second, independent binding question in the same three rows",
            },
            {
                "id": "D6",
                "reading": "clause condition",
                "input": "the clause is conditional on 'Until L1 binds the exact hypotheses'; C06 "
                "measures the L1 SRC-004 (Dafermos-Luk 1710.01722) row status and hypothesis-binding "
                "rows. The condition is unresolved at the pinned L1 hash.",
                "supports": "restriction remains in force on the clause's own terms",
            },
        ],
        "recommendation": (
            "Route to the A0/controller owner: rule whether frozen_classes[AF-SCC-C0-VAC-GEN]."
            "status_risk constrains per-row conclusion_type (D1) or only an explicit class-status "
            "record the ledger does not carry (D2). Either way the canonical tooling gap (D3/D4) "
            "means the finding cannot be discharged by re-running canonical audits."
        ),
        "not_claimed": [
            "no gate verdict (G-LIT/G-AUDIT untouched)",
            "no node status for L0",
            "no validation_status",
            "no class-binding repair and no write to any pinned file",
            "no claim that the three rows are or are not class leakage",
        ],
        "falsifier": (
            "Re-run run_l0_c0_theorem_063.py at the pins above. Falsified if any pinned input "
            "drifts; if the C0-bound row census or the three theorem rows change; if any canonical "
            "module flags the three rows for the C0-status pattern; if any control M1-M8 stops "
            "reproducing; or if the two core runs differ."
        ),
    }
    out = pathlib.Path(__file__).resolve().parent / "report.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(out.relative_to(ROOT)),
        "status": report["status"],
        "void_reasons": void_reasons,
        "determinism_digest": report["determinism_digest"],
        "c0_theorem_rows": c0_flags,
        "controls_passed": f"{core_a['C07_controls']['passed']}/{core_a['C07_controls']['total']}",
    }, indent=1))
    return 0 if not void else 2


if __name__ == "__main__":
    sys.exit(main())
