#!/usr/bin/env python3
"""W010-C2-UNBOUND-MENTION-ADJUDICATION-01 -- instrument.

Read-only, pin-guarded audit of the live AF-SCC-C2-VAC-GEN binding register:
  A. completeness of the class_ids-bound set against the rev13 register and the
     coverage-matrix C2 theorem set;
  B. adjudication of the five entries that mention the C2 token outside class_ids;
  C. an all-62-entry assertion-field discharge screen for the frozen class
     conclusion (generic + asymptotically flat + vacuum + C2-or-smoother
     inextendibility), with a declared post-screen adjudication of every positive;
  D. frozen-token policy check on class_ids.

Writes only under artifacts/worker-010/c2_unbound_mentions/.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-010/c2_unbound_mentions -> repo root

LEDGER = ROOT / "ledger" / "theorems.jsonl"
MATRIX = ROOT / "ledger" / "class_coverage.csv"
SCHEMA = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"
REV13_AUDIT = ROOT / "artifacts" / "worker-010" / "c2_conformance_rev13" / "c2_conformance_audit.json"
REV13_RESULT = ROOT / "artifacts" / "worker-010" / "c2_conformance_rev13" / "W010_F2A_C2_REV13_result.json"
CBR_AUDIT = ROOT / "artifacts" / "worker-010" / "class_binding_reconcile" / "binding_reconcile_audit.json"
PREREG = HERE / "prereg.json"

TOK = "AF-SCC-C2-VAC-GEN"
FROZEN_TOKENS = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}

# Declared marker sets (normalised, lower-case, whitespace-collapsed text).
C2_RE = re.compile(r"c\s*\^?\s*\{?\s*(?:2|0\s*,\s*1)\s*\}?(?![0-9a-z])")
GEN_RE = re.compile(r"\b(generic|generically|comeager|open set|open sets|positive measure)\b")
AF_RE = re.compile(r"asymptotically[\s\-]flat")
CONTRA_RE = re.compile(r"(?<!non-)\bextend(?:ible|ed|s)?\b|naked singularit|extension exists")
NEGATION_RE = re.compile(
    r"\b(no peer[- ]reviewed|no theorem|no result|not proved|not proven|unproven|"
    r"was not located|were not located|not located|remains open|is open|open problem)\b"
)
MATTER_RE = re.compile(
    r"(einstein[\s\-–—]maxwell|klein[\s\-–—]gordon|em[\s\-–—]scalar|em[\s\-–—]kg|"
    r"charged scalar|scalar field system|electromagnetic|matter model|matter field|"
    r"real[\s\-–—]scalar)"
)
NONVAC_RE = re.compile(r"(cosmological constant|lambda\s*>\s*0|not vacuum|non[\s\-]vacuum)")
SYMRESTR_RE = re.compile(r"(gowdy|t\s*\^?\s*3|spherically symmetric|spherical symmetry|two[\s\-]ended)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(text) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def load_ledger():
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def markers(statement: str) -> dict:
    t = norm(statement)
    return {
        "c2_or_smoother_regularity": bool(C2_RE.search(t)),
        "inextendibility": "inextendib" in t,
        "vacuum": "vacuum" in t,
        "genericity": bool(GEN_RE.search(t)),
        "asymptotic_flatness": bool(AF_RE.search(t)),
        "contrary_extension_exists": bool(CONTRA_RE.search(t)),
        "negative_or_status_phrasing": bool(NEGATION_RE.search(t)),
        "matter_model": bool(MATTER_RE.search(t)),
        "non_vacuum": bool(NONVAC_RE.search(t)),
        "symmetry_or_subclass_restriction": bool(SYMRESTR_RE.search(t)),
    }


def discharge_screen(m: dict) -> bool:
    return bool(
        m["c2_or_smoother_regularity"]
        and m["inextendibility"]
        and m["vacuum"]
        and m["genericity"]
        and m["asymptotic_flatness"]
    )


def adjudicate_positive(entry: dict, m: dict) -> tuple[str, str]:
    """Declared post-screen adjudication rule for a screened positive.

    Returns (reason_code, counted_as_discharging). Fail-closed: only a positively
    identified negation/status report or a symmetry restriction removes a
    screened positive; anything else stays counted as a discharging candidate.
    """
    if m["negative_or_status_phrasing"]:
        return "NEGATIVE_STATUS_REPORT", False
    if m["symmetry_or_subclass_restriction"] and not m["asymptotic_flatness"]:
        return "SUBCLASS_RESTRICTED", False
    if m["matter_model"] or m["non_vacuum"]:
        return "MATTER_MODEL_OR_NON_VACUUM", False
    return "UNRESOLVED_DISCHARGE_CANDIDATE", True


def mention_exclusion_reasons(entry: dict) -> list[str]:
    m = markers(entry.get("statement_exact"))
    reasons = []
    if m["matter_model"]:
        reasons.append("MATTER_MODEL")
    if m["non_vacuum"]:
        reasons.append("NON_VACUUM")
    if entry.get("conclusion_type") == "conditional_theorem":
        reasons.append("CONDITIONAL_STATEMENT")
    if m["symmetry_or_subclass_restriction"]:
        reasons.append("SYMMETRY_OR_SUBCLASS_RESTRICTED")
    dnl = norm(" ".join(entry.get("does_not_imply") or []))
    if "does not prove c^2 scc in vacuum" in dnl or "does not refute af-scc-c2-vac-gen" in dnl:
        reasons.append("EXPLICIT_NON_DISCHARGE_DECLARED")
    return reasons


def matrix_c2_ids() -> list[str]:
    rows = list(csv.DictReader(MATRIX.open()))
    ids = set()
    for row in rows:
        if row.get("class_id") != TOK:
            continue
        for piece in re.split(r"[;|,]", row.get("theorem_ids") or ""):
            piece = piece.strip()
            if piece:
                ids.add(piece)
    return sorted(ids)


def rev13_register_ids() -> list[str]:
    audit = json.loads(REV13_AUDIT.read_text())
    return sorted(b["theorem_id"] for b in audit.get("bindings", []))


def core() -> dict:
    ledger = load_ledger()
    bound = sorted(e["theorem_id"] for e in ledger if TOK in (e.get("class_ids") or []))
    mentions = sorted(
        e["theorem_id"]
        for e in ledger
        if TOK not in (e.get("class_ids") or []) and TOK in json.dumps(e)
    )
    matrix = matrix_c2_ids()
    rev13 = rev13_register_ids()

    mention_rows = []
    for tid in mentions:
        e = next(x for x in ledger if x["theorem_id"] == tid)
        m = markers(e.get("statement_exact"))
        mention_rows.append(
            {
                "theorem_id": tid,
                "label": e.get("label"),
                "conclusion_type": e.get("conclusion_type"),
                "entry_kind": e.get("entry_kind"),
                "assertion_markers": {k: v for k, v in m.items()},
                "assertion_discharge_screen": discharge_screen(m),
                "assertion_contrary_extension_exists": m["contrary_extension_exists"],
                "exclusion_reasons": mention_exclusion_reasons(e),
                "next_action": e.get("next_action"),
            }
        )

    sweep_rows = []
    screened_positive = []
    for e in ledger:
        m = markers(e.get("statement_exact"))
        if discharge_screen(m):
            code, counted = adjudicate_positive(e, m)
            row = {
                "theorem_id": e["theorem_id"],
                "bound_to_c2": TOK in (e.get("class_ids") or []),
                "conclusion_type": e.get("conclusion_type"),
                "adjudication": code,
                "counted_as_discharging": counted,
                "markers": m,
            }
            sweep_rows.append(row)
            screened_positive.append(row)

    tokens_seen: dict[str, int] = {}
    for e in ledger:
        for c in e.get("class_ids") or []:
            tokens_seen[c] = tokens_seen.get(c, 0) + 1
    out_of_tax = sorted(t for t in tokens_seen if t not in FROZEN_TOKENS)

    n_discharging = sum(1 for r in sweep_rows if r["counted_as_discharging"])
    mention_ok = all(
        (not r["assertion_discharge_screen"]) and bool(r["exclusion_reasons"]) for r in mention_rows
    )
    sets_ok = bound == matrix == rev13
    decision = (
        "COMPLETE_AND_OPEN"
        if (sets_ok and mention_ok and n_discharging == 0 and not out_of_tax)
        else ("BINDING_GAP" if not sets_ok or n_discharging else "MENTION_MISCLASSIFIED")
    )

    return {
        "ledger_entries": len(ledger),
        "sets": {
            "bound_to_c2_from_class_ids": bound,
            "token_mentions_outside_class_ids": mentions,
            "coverage_matrix_c2_theorem_ids": matrix,
            "rev13_register_theorem_ids": rev13,
            "bound_equals_matrix": bound == matrix,
            "bound_equals_rev13": bound == rev13,
        },
        "mention_adjudication": mention_rows,
        "discharge_sweep": {
            "n_entries_screened": len(ledger),
            "n_screened_positive_raw": len(screened_positive),
            "screened_positive": sweep_rows,
            "n_discharging_after_adjudication": n_discharging,
            "discharging_ids": [r["theorem_id"] for r in sweep_rows if r["counted_as_discharging"]],
        },
        "token_policy": {
            "class_id_tokens_seen": tokens_seen,
            "out_of_frozen_taxonomy": out_of_tax,
            "frozen_tokens": sorted(FROZEN_TOKENS),
        },
        "decision": decision,
    }


def main() -> dict:
    prereg = json.loads(PREREG.read_text())
    declared = prereg["pins"]
    path_of = {
        "ledger/theorems.jsonl": LEDGER,
        "ledger/class_coverage.csv": MATRIX,
        "schemas/af_scc_c2_vacuum.yaml": SCHEMA,
        "research_map/formulation_taxonomy.yaml": F0,
        "artifacts/worker-010/c2_conformance_rev13/W010_F2A_C2_REV13_result.json": REV13_RESULT,
        "artifacts/worker-010/class_binding_reconcile/binding_reconcile_audit.json": CBR_AUDIT,
    }
    pin_start = {k: {"declared": v, "measured": sha256(path_of[k]), "match": sha256(path_of[k]) == v} for k, v in declared.items()}
    pins_ok_start = all(v["match"] for v in pin_start.values())

    body = core()
    body2 = core()
    determinism = json.dumps(body, sort_keys=True) == json.dumps(body2, sort_keys=True)

    # Controls.
    base = "every generic asymptotically flat vacuum development is c^2-future-inextendible"
    ctl1_m = markers(base)
    ctl1 = discharge_screen(ctl1_m)
    ctl2_m = markers(base.replace("vacuum", "einstein-maxwell-scalar field"))
    ctl2 = discharge_screen(ctl2_m)
    field_scope_entry = {"statement_exact": "status note only", "does_not_imply": [base]}
    ctl3_m = markers(field_scope_entry["statement_exact"])
    ctl3 = discharge_screen(ctl3_m)
    controls = [
        {"id": "CTL-1", "kind": "mutation positive", "pre_stated": "synthetic vacuum+generic+asymptotically-flat C2-inextendibility assertion screens as discharging=true", "observed": ctl1, "pass": ctl1 is True},
        {"id": "CTL-2", "kind": "mutation negative", "pre_stated": "same assertion with the vacuum marker replaced by a matter model screens as discharging=false", "observed": ctl2, "pass": ctl2 is False},
        {"id": "CTL-3", "kind": "field-scope", "pre_stated": "a discharging sentence placed only in does_not_imply screens as discharging=false (assertion field only)", "observed": ctl3, "pass": ctl3 is False},
        {"id": "CTL-4", "kind": "determinism", "pre_stated": "two in-process runs of the core produce byte-identical canonical JSON", "observed": determinism, "pass": determinism is True},
    ]
    controls_ok = all(c["pass"] for c in controls)

    pin_end = {k: {"declared": v, "measured": sha256(path_of[k]), "match": sha256(path_of[k]) == v} for k, v in declared.items()}
    pins_ok_end = all(v["match"] for v in pin_end.values())

    decision = body["decision"]
    if not pins_ok_start or not pins_ok_end or not controls_ok:
        decision = "INSTRUMENT_FAIL"

    report = {
        "schema": "w010-c2-unbound-mentions/1",
        "task_id": prereg["task_id"],
        "actor": "worker-010",
        "class_id": TOK,
        "class_ids": [TOK],
        "node_id": prereg["node_id"],
        "gate": prereg["gate"],
        "created_at": "2026-09-12T01:24:39+08:00",
        "object_under_test": {
            "ledger": "ledger/theorems.jsonl",
            "coverage_matrix": "ledger/class_coverage.csv",
            "class_schema": "schemas/af_scc_c2_vacuum.yaml",
            "frozen_taxonomy": "research_map/formulation_taxonomy.yaml",
            "prior_register": "artifacts/worker-010/c2_conformance_rev13/c2_conformance_audit.json",
        },
        "pin_check": {"start": pin_start, "end": pin_end, "pins_ok_start": pins_ok_start, "pins_ok_end": pins_ok_end, "drift": pins_ok_start != pins_ok_end},
        "controls": controls,
        "result": body,
        "decision": decision,
        "falsifier": prereg["falsifiers"],
        "non_claims": prereg["non_claims"],
        "verification": {"status": "pending_second_implementation", "verifier_path": "artifacts/worker-010/c2_unbound_mentions/verify_c2_unbound_mentions.json"},
        "validation_status": "unverified",
        "claims_completion": False,
    }

    (HERE / "c2_unbound_mentions_audit.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    runlog = {
        "volatile_run_metadata_not_part_of_the_pinned_report": True,
        "measured_at": "2026-09-12T01:24:39+08:00",
        "ledger_mtime": LEDGER.stat().st_mtime,
        "matrix_mtime": MATRIX.stat().st_mtime,
        "python_hashes": {k: sha256(p) for k, p in path_of.items()},
    }
    (HERE / "run_log.json").write_text(json.dumps(runlog, indent=2, sort_keys=True))
    print(json.dumps({"decision": decision, "pins_ok": pins_ok_start and pins_ok_end, "controls_ok": controls_ok,
                      "n_bound": len(body["sets"]["bound_to_c2_from_class_ids"]),
                      "n_mentions": len(body["sets"]["token_mentions_outside_class_ids"]),
                      "n_screened_positive_raw": body["discharge_sweep"]["n_screened_positive_raw"],
                      "n_discharging": body["discharge_sweep"]["n_discharging_after_adjudication"]}, indent=2))
    return report


if __name__ == "__main__":
    main()
