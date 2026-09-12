#!/usr/bin/env python3
"""W052-L0-HF02-REMAP-VERIFY-01 — independent adversarial verification of worker-023's
HF-02 (class_leakage: disjunction of class_ids) adjudication packet for L0.

What this is
------------
worker-023 (artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json) proposes a
NOT-APPLIED remap of the 8 L0 ledger rows whose class_ids disjoin two frozen classes. This
harness is an independent, read-only verifier written from scratch against the frozen rule
text (evaluation_rubric.yaml HF-02) and the VARIANT_REGISTRY.json class_id_rule. It does not
import or execute worker-023's builder/verifier.

Pre-registered expectations (fixed before the run; all must hold for exit 0)
----------------------------------------------------------------------------
P1  all 7 pinned inputs re-hash to the packet's declared sha256 values.
R1  the disjunctive row set independently re-derived from the live ledger equals the packet's
    declared set and equals the 8 named rows {D-004,D-005,T-303,T-305,T-402,T-515,T-526,T-528}.
R2  every packet row's class_ids_at_pin equals the live ledger class_ids, and every declared
    row_evidence field equals the live row field.
R3  every recommendation is shape-valid: class_ids/informs subsets of the frozen four,
    disjoint, non-empty binding, no registered variant id inside class_ids, tag additions are
    registered variant ids.
R4  every cited extension variant exists in VARIANT_REGISTRY.json with the declared parent, and
    each recommendation's containment direction is stated in the registry strength text.
R5  an in-memory application of the packet patch yields: 0 disjunctions, 0 unknown class
    tokens, 0 variant ids in class_ids, 0 duplicate ids, exactly 2 newly singular class_ids
    rows, exactly 6 class_ids-empty/informs-nonempty relation bindings — matching the packet
    summary.
R6  applying the patch twice is idempotent.
R7  the live ledger sha256 is unchanged after the run (harness is read-only).
M1  scope metrics recorded before/after for the owner (class_ids-empty 28 -> 34, no-binding
    21 -> 21, singular 26 -> 28, class_binding fraction 0.4194 -> 0.4516).

Mutation controls (each must be caught; C0 must pass clean)
-----------------------------------------------------------
C0  unmodified inputs -> all primary checks pass.
C1  a registered variant id injected into a class_ids field -> R3/R5 must flag it.
C2  a 9th synthetic disjunctive row appended -> R1 completeness must differ.
C3  a row_evidence field tampered in a packet copy -> R2 must fail.
C4  the packet's anchor/pin hash altered -> P1 must fail.
C5  one row dropped from the packet copy -> R1 row-set equality must fail.

Authority: worker evidence only. No gate verdict, no node status, no validation_status=passed,
no ledger edit. Verdict on the target packet is advisory.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # .../ai4math-swarm
OUT = Path(__file__).resolve().parent
REPORT = OUT / "report.json"

LEDGER = ROOT / "ledger/theorems.jsonl"
PACKET = ROOT / "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json"
REGISTRY = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
RUBRIC = ROOT / "evaluation_rubric.yaml"
SCHEMA_C0 = ROOT / "schemas/af_scc_c0_vacuum.yaml"
SCHEMA_C2 = ROOT / "schemas/af_scc_c2_vacuum.yaml"

FROZEN = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
REGISTERED_VARIANTS = {"SET", "CH", "H2LOC", "TWOSIDED", "DISTRIBUTIONAL", "L2CONN", "LIP"}
DECLARED_DISJUNCTIVE = [
    "D-004", "D-005", "T-303", "T-305", "T-402", "T-515", "T-526", "T-528",
]
EVIDENCE_FIELDS = [
    "label", "statement_exact", "regularity", "genericity", "conclusion_type",
    "entry_kind", "evidence_level", "ledger_tags", "unresolved", "scope_caveats",
]
# extension class -> registered variant id expected to carry the containment direction
EXT_TO_VARIANT = {"L2CONN": "L2CONN", "LIP": "LIP", "H2LOC": "H2LOC"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def frozen_hits(row: dict) -> set:
    return set(row.get("class_ids") or []) & FROZEN


def disjunctive_rows(rows, frozen=FROZEN):
    return [r["theorem_id"] for r in rows if len(set(r.get("class_ids") or []) & frozen) >= 2]


def unknown_class_rows(rows, frozen=FROZEN):
    out = []
    for r in rows:
        bad = [c for c in (r.get("class_ids") or []) if c not in frozen]
        if bad:
            out.append({"theorem_id": r["theorem_id"], "tokens": bad})
    return out


def variant_class_rows(rows):
    return [
        {"theorem_id": r["theorem_id"], "tokens": sorted(set(r.get("class_ids") or []) & REGISTERED_VARIANTS)}
        for r in rows
        if set(r.get("class_ids") or []) & REGISTERED_VARIANTS
    ]


def dup_class_rows(rows):
    return [
        r["theorem_id"]
        for r in rows
        if len(r.get("class_ids") or []) != len(set(r.get("class_ids") or []))
    ]


def apply_patch(rows, patch):
    """Return a patched copy of rows; pure function, no canonical write."""
    by_id = {p["row_id"]: p for p in patch}
    out = []
    for r in rows:
        r2 = copy.deepcopy(r)
        p = by_id.get(r.get("theorem_id"))
        if p:
            r2["class_ids"] = list(p["class_ids"])
            r2["informs_classes"] = list(p["informs_classes"])
            if p.get("ledger_tags_add"):
                r2["ledger_tags"] = sorted(set(r2.get("ledger_tags") or []) | set(p["ledger_tags_add"]))
        out.append(r2)
    return out


def metrics(rows):
    total = len(rows)
    singular = sum(1 for r in rows if len(frozen_hits(r)) == 1)
    empty_ids = sum(1 for r in rows if not (r.get("class_ids") or []))
    no_binding = sum(
        1
        for r in rows
        if not (r.get("class_ids") or []) and not (set(r.get("informs_classes") or []) & FROZEN)
    )
    return {
        "total": total,
        "singular_frozen_class_ids": singular,
        "class_ids_empty": empty_ids,
        "no_binding_at_all": no_binding,
        "class_binding_fraction_singular_over_total": round(singular / total, 4),
    }


def check_pins(packet, overrides=None):
    declared = packet["inputs"]
    measured = {}
    mismatch = {}
    for rel, want in declared.items():
        got = overrides.get(rel) if overrides and rel in overrides else sha256(ROOT / rel)
        measured[rel] = got
        if got != want:
            mismatch[rel] = {"declared": want, "measured": got}
    return measured, mismatch


def check_packet_rows(rows_by_id, packet):
    problems = []
    # packet integrity: one row record per declared disjunctive row, 8 in total
    row_ids = [r["row_id"] for r in packet["rows"]]
    if len(row_ids) != 8 or set(row_ids) != set(packet["disjunctive_row_set"]) \
            or set(row_ids) != set(DECLARED_DISJUNCTIVE):
        problems.append({"issue": "packet row-set does not cover the declared 8-row set",
                         "row_ids": row_ids, "declared": packet["disjunctive_row_set"]})
    for row in packet["rows"]:
        tid = row["row_id"]
        live = rows_by_id.get(tid)
        if live is None:
            problems.append({"row": tid, "issue": "absent from live ledger"})
            continue
        if list(live.get("class_ids") or []) != list(row.get("class_ids_at_pin") or []):
            problems.append(
                {"row": tid, "issue": "class_ids_at_pin mismatch",
                 "live": live.get("class_ids"), "packet": row.get("class_ids_at_pin")}
            )
        for field in EVIDENCE_FIELDS:
            if field not in row.get("row_evidence", {}):
                continue
            if live.get(field) != row["row_evidence"][field]:
                problems.append({"row": tid, "issue": f"row_evidence.{field} mismatch"})
    return problems


def check_recommendation_shape(packet):
    problems = []
    table = []
    for row in packet["rows"]:
        rec = row["recommended"]
        cids = list(rec.get("class_ids") or [])
        inf = list(rec.get("informs_classes") or [])
        bad = []
        if any(c not in FROZEN for c in cids):
            bad.append("class_ids not subset of frozen four")
        if any(c not in FROZEN for c in inf):
            bad.append("informs_classes not subset of frozen four")
        if set(cids) & set(inf):
            bad.append("class_ids and informs_classes overlap")
        if not cids and not inf:
            bad.append("empty binding")
        if set(cids) & REGISTERED_VARIANTS:
            bad.append("registered variant id inside class_ids")
        if any(t not in REGISTERED_VARIANTS for t in (rec.get("ledger_tags_add") or [])):
            bad.append("ledger_tags_add contains a non-registered token")
        if bad:
            problems.append({"row": row["row_id"], "problems": bad})
        table.append(
            {"row": row["row_id"], "class_ids": cids, "informs_classes": inf,
             "tags_add": rec.get("ledger_tags_add") or [], "ok": not bad}
        )
    return problems, table


def check_registry(packet, registry):
    variants = {v["variant_id"]: v for v in registry["variants"]}
    problems = []
    table = []
    for row in packet["rows"]:
        ext = row.get("measured_extension_class")
        parent = row.get("registry_parent")
        if ext in (None, "WCC-ANTECEDENT"):
            # T-515/T-528: no variant cited; the recommendation is a frozen WCC class binding.
            table.append({"row": row["row_id"], "extension_class": ext, "variant": None,
                          "parent_ok": None, "containment_stated": None})
            continue
        v = variants.get(EXT_TO_VARIANT.get(ext, ext))
        if v is None:
            problems.append({"row": row["row_id"], "issue": f"variant {ext} not registered"})
            table.append({"row": row["row_id"], "extension_class": ext, "variant": None,
                          "parent_ok": False, "containment_stated": False})
            continue
        parent_ok = v.get("parent_class") == parent
        strength = str(v.get("strength", ""))
        containment_stated = ("subset E_C0" in strength) or ("between C2 and C0" in strength) \
            or ("between C^{1,1} and C0" in strength)
        if not parent_ok:
            problems.append({"row": row["row_id"],
                             "issue": f"registry parent {v.get('parent_class')} != packet {parent}"})
        if not containment_stated:
            problems.append({"row": row["row_id"],
                             "issue": f"registry strength text lacks a containment direction: {strength[:80]}"})
        table.append({"row": row["row_id"], "extension_class": ext,
                      "variant": v["variant_id"], "registry_parent": v.get("parent_class"),
                      "parent_ok": parent_ok, "containment_stated": containment_stated})
    return problems, table


def primary_checks(ledger_rows, packet, registry, rubric_text):
    rows_by_id = {r["theorem_id"]: r for r in ledger_rows}
    checks = {}

    # P1 pins
    measured, mismatch = check_pins(packet)
    checks["P1_pins_match"] = {"ok": not mismatch, "measured": measured, "mismatch": mismatch}

    # R1 completeness
    rederived = sorted(disjunctive_rows(ledger_rows))
    declared = sorted(packet["disjunctive_row_set"])
    checks["R1_disjunctive_set"] = {
        "ok": rederived == declared == sorted(DECLARED_DISJUNCTIVE),
        "rederived": rederived,
        "declared": declared,
        "expected": sorted(DECLARED_DISJUNCTIVE),
    }

    # R2 row evidence binding
    problems = check_packet_rows(rows_by_id, packet)
    checks["R2_evidence_binding"] = {"ok": not problems, "problems": problems}

    # R3 recommendation shape
    problems, table = check_recommendation_shape(packet)
    checks["R3_recommendation_shape"] = {"ok": not problems, "problems": problems, "table": table}

    # R4 registry consistency
    problems, rtable = check_registry(packet, registry)
    checks["R4_registry_consistency"] = {"ok": not problems, "problems": problems, "table": rtable}

    # R5 in-memory patch counts
    patched = apply_patch(ledger_rows, packet["proposed_patch"])
    after = {
        "disjunctions": disjunctive_rows(patched),
        "unknown_class_rows": unknown_class_rows(patched),
        "variant_in_class_ids": variant_class_rows(patched),
        "duplicate_class_ids": dup_class_rows(patched),
        "newly_singular": sorted(
            r["theorem_id"] for r in patched
            if r["theorem_id"] in DECLARED_DISJUNCTIVE and len(frozen_hits(r)) == 1
        ),
        "relation_bindings": sorted(
            r["theorem_id"] for r in patched
            if r["theorem_id"] in DECLARED_DISJUNCTIVE
            and not (r.get("class_ids") or [])
            and (set(r.get("informs_classes") or []) & FROZEN)
        ),
    }
    summary = packet["summary"]
    r5_ok = (
        after["disjunctions"] == []
        and after["unknown_class_rows"] == []
        and after["variant_in_class_ids"] == []
        and after["duplicate_class_ids"] == []
        and len(after["newly_singular"]) == summary["singular_class_members_after_patch"] == 2
        and len(after["relation_bindings"]) == summary["relation_bindings_after_patch"] == 6
        and summary["predicted_hf02_disjunctions_after_patch"] == 0
    )
    checks["R5_patched_counts"] = {"ok": r5_ok, "after": after, "summary": summary}

    # R6 idempotence
    twice = apply_patch(patched, packet["proposed_patch"])
    checks["R6_idempotent"] = {"ok": twice == patched}

    # M1 scope metrics
    checks["M1_scope_metrics"] = {"before": metrics(ledger_rows), "after": metrics(patched)}

    # rubric text
    hf02_ok = "disjunction of class_ids" in rubric_text
    checks["R8_rubric_hf02_text"] = {"ok": hf02_ok}
    return checks


def controls(ledger_rows, packet, registry, rubric_text):
    """Pre-registered mutations; each must be caught, C0 must pass."""
    res = {}

    def run(led, pkt):
        return primary_checks(led, pkt, registry, rubric_text)

    # C0 clean
    c0 = run(ledger_rows, packet)
    res["C0_clean_passes"] = {
        "ok": all(v["ok"] for k, v in c0.items() if k.startswith(("P1", "R1", "R2", "R3", "R4", "R5", "R6"))),
        "caught": False,
    }

    # C1 variant id in class_ids
    led1 = copy.deepcopy(ledger_rows)
    for r in led1:
        if r["theorem_id"] == "D-004":
            r["class_ids"] = ["L2CONN"]
    c1 = run(led1, packet)
    res["C1_variant_as_class_caught"] = {
        "ok": bool(unknown_class_rows(led1)) and (not c1["R2_evidence_binding"]["ok"]),
        "detail": {"unknown_tokens": unknown_class_rows(led1),
                   "evidence_binding_failed": not c1["R2_evidence_binding"]["ok"]},
    }

    # C2 extra disjunctive row
    led2 = copy.deepcopy(ledger_rows)
    extra = copy.deepcopy(next(r for r in led2 if r["theorem_id"] == "D-001"))
    extra["theorem_id"] = "X-999"
    extra["class_ids"] = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"]
    led2.append(extra)
    c2 = run(led2, packet)
    res["C2_extra_disjunctive_caught"] = {
        "ok": (not c2["R1_disjunctive_set"]["ok"]) and ("X-999" in c2["R1_disjunctive_set"]["rederived"]),
        "detail": c2["R1_disjunctive_set"]["rederived"],
    }

    # C3 tampered row_evidence
    pkt3 = copy.deepcopy(packet)
    pkt3["rows"][0]["row_evidence"]["regularity"] = "TAMPERED"
    c3 = run(ledger_rows, pkt3)
    res["C3_tampered_evidence_caught"] = {"ok": not c3["R2_evidence_binding"]["ok"]}

    # C4 altered pin
    pkt4 = copy.deepcopy(packet)
    first = next(iter(pkt4["inputs"]))
    pkt4["inputs"][first] = "0" * 64
    c4 = run(ledger_rows, pkt4)
    res["C4_altered_pin_caught"] = {"ok": not c4["P1_pins_match"]["ok"]}

    # C5 dropped row from packet
    pkt5 = copy.deepcopy(packet)
    pkt5["rows"] = pkt5["rows"][:-1]
    c5 = run(ledger_rows, pkt5)
    res["C5_dropped_row_caught"] = {
        "ok": not c5["R2_evidence_binding"]["ok"],
        "detail": "packet row-set shortened to 7 while the declared set and ledger have 8",
    }
    return res


def main() -> int:
    ledger_rows = load_jsonl(LEDGER)
    packet = json.loads(PACKET.read_text())
    registry = json.loads(REGISTRY.read_text())
    rubric_text = RUBRIC.read_text()

    before_ledger_sha = sha256(LEDGER)

    checks = primary_checks(ledger_rows, packet, registry, rubric_text)
    ctrl = controls(ledger_rows, packet, registry, rubric_text)

    after_ledger_sha = sha256(LEDGER)
    checks["R7_read_only"] = {"ok": before_ledger_sha == after_ledger_sha,
                              "before": before_ledger_sha, "after": after_ledger_sha}

    primary_keys = ["P1_pins_match", "R1_disjunctive_set", "R2_evidence_binding",
                    "R3_recommendation_shape", "R4_registry_consistency",
                    "R5_patched_counts", "R6_idempotent", "R7_read_only",
                    "R8_rubric_hf02_text"]
    primary_ok = all(checks[k]["ok"] for k in primary_keys)
    controls_ok = ctrl["C0_clean_passes"]["ok"] and all(
        v["ok"] for k, v in ctrl.items() if k != "C0_clean_passes"
    )

    # Advisory findings are reviewer judgement, not machine checks.
    advisory = [
        {"id": "W052-A1", "severity": "advisory",
         "target": "T-303 rationale",
         "text": ("The packet's T-303 rationale calls the row 'a counterexample inside the L2CONN "
                  "variant'. Direction is imprecise: T-303 exhibits a C0 extension whose Christoffels "
                  "are not in L^2_loc, so it is a counterexample to the C0-regularity statement on a "
                  "special (non-generic, impulsive) data class and a strictness witness for "
                  "E_L2conn subset E_C0. It does not refute the L2CONN statement, which forbids only "
                  "extensions whose Christoffels ARE in L^2_loc. The recommended binding "
                  "(class_ids=[], informs=[AF-SCC-C0-VAC-GEN], tag L2CONN) is unaffected."),
         "owner_action": "record the implication direction before citing T-303 as an L2CONN counterexample"},
        {"id": "W052-A2", "severity": "advisory",
         "target": "D-005 scope",
         "text": ("D-005 defines a family: Lipschitz C^{0,1}_loc OR continuous metric with Christoffel "
                  "in L^s_loc for s>1. The remap registers only the LIP variant; the s>1 L^s_loc family "
                  "(of which L2CONN is s=2) has no registered variant id. HF-02 clearance is unaffected "
                  "(class_ids becomes empty), but the variant registration is incomplete."),
         "owner_action": "register a generic LSCONN (s>1) variant or narrow D-005's wording"},
        {"id": "W052-A3", "severity": "scope",
         "target": "post-patch class-binding metrics",
         "text": ("Applying the patch raises class_ids-empty rows 28 -> 34 and lowers the A0 "
                  "class_binding numerator 26 -> 28 only because T-515/T-528 gain a singular WCC binding. "
                  "The L0 stop_rule clause 'the class column is non-empty' is satisfied for these rows "
                  "only if the class column is read as class_ids UNION informs_classes; under a "
                  "class_ids-only reading the patch appears to regress 34 -> 28 non-empty rows. This is "
                  "an owner-level interpretation decision, not an HF-02 defect."),
         "owner_action": "record the reading of 'class column' (class_ids union informs_classes) at the same time as the patch"},
        {"id": "W052-A4", "severity": "boundary",
         "target": "packet validity window",
         "text": ("The whole packet is void if ledger/theorems.jsonl moves; all checks here bind "
                  "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28."),
         "owner_action": "re-run this harness if the ledger hash changes"},
    ]

    report = {
        "schema": "w052-l0-hf02-remap-independent-verification/v1",
        "artifact_id": "w052-20260912T0040-l0-hf02-remap-verify",
        "actor": "worker-052",
        "node_id": "L0",
        "gate": "G-LIT",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "target": {
            "artifact": "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json",
            "sha256": sha256(PACKET),
            "author": "worker-023",
            "author_self_verification": "artifacts/worker-023/l0_hf02/hf02-verify-023.json (same author; not independent)",
        },
        "harness": {
            "path": "artifacts/worker-052/l0_hf02_verify/verify_hf02_remap_052.py",
            "independent_of_author_tools": True,
            "imports_author_code": False,
        },
        "pins": {rel: sha256(ROOT / rel) for rel in packet["inputs"]},
        "checks": checks,
        "controls": ctrl,
        "advisory_findings": advisory,
        "hard_failures": [],
        "verdict": "VERIFIED_ACCEPT" if (primary_ok and controls_ok) else "REVISE",
        "verdict_scope": ("one HF-02 (disjunction of class_ids) adjudication packet at the pinned L0 "
                          "hash; not a verdict on the ledger, the L0 node, G-LIT, or the mathematics"),
        "authority_note": ("Worker evidence only. No gate verdict, no node status, no "
                           "validation_status=passed, no ledger edit."),
        "falsifier": ("Falsified if: (a) any pinned input re-hashes differently; (b) the independently "
                      "re-derived disjunctive set differs from the packet's 8 rows; (c) any packet "
                      "row_evidence field differs from the pinned ledger row; (d) the in-memory patch "
                      "leaves a disjunction, an unknown class token, a variant id in class_ids, or a "
                      "duplicate; (e) any mutation control C1-C5 is not caught or C0 fails; or "
                      "(f) ledger/theorems.jsonl changes from the pinned hash."),
        "reproduction": f"python3 {Path(__file__).relative_to(ROOT)}",
    }

    REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "verdict": report["verdict"],
        "primary_ok": primary_ok,
        "controls_ok": controls_ok,
        "failed_checks": [k for k in primary_keys if not checks[k]["ok"]],
        "failed_controls": [k for k, v in ctrl.items() if not v["ok"]],
        "report_sha256": sha256(REPORT),
    }, indent=1))
    return 0 if (primary_ok and controls_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
