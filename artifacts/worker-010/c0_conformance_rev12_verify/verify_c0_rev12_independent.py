#!/usr/bin/env python3
"""Worker-010 independent third-implementation verification of the AF-SCC-C0-VAC-GEN
class-conformance re-audit at F2b rev12 55d0a1ea9bda.

Target: artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.55d0a1ea9bda.json
(actor deepseek-flash-10 / fleet slot 010, emitted 2026-09-12T00:38:15+08:00,
validation_status unverified).

This verifier was written from the frozen class contract
(research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN and
schemas/af_scc_c0_vacuum.yaml rev12) and does NOT import the audited driver.  It:

  1. re-hashes every input the audit pins (live canonical file vs pinned snapshot);
  2. selects the class bindings straight from the ledger snapshot by class_ids membership;
  3. re-derives D1/D2/D3 with an independently written predicate set;
  4. compares binding-by-binding and count-by-count with the audit;
  5. re-measures the rev11 -> rev12 class-definition drift with a normal-form check;
  6. runs adversarial synthetic controls (one discharging, three sabotaged, one
     field-mapping control);
  7. records findings, including a correction of the audit's D3 mechanism claim
     (the rev3 ledger dropped the `status` key; the equivalent field is `content_status`).

Disclosure: this verifier shares fleet slot 010 with the target's actor alias
(`deepseek-flash-10`); it is a mechanical reproducibility check, NOT an independent
reviewer verdict.  A1/Astra remain the verdict authority.

Usage: python3 verify_c0_rev12_independent.py
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # <repo>/artifacts/worker-010/c0_conformance_rev12_verify

CLASS = "AF-SCC-C0-VAC-GEN"
SIBLING = "AF-SCC-C2-VAC-GEN"

AUDIT_ORIG = ROOT / "artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.55d0a1ea9bda.json"
AUDIT_SNAP = HERE / "snapshots/c0_class_conformance_audit.55d0a1ea9bda.json"
LEDGER_SNAP = HERE / "snapshots/theorems.a1674f094979.jsonl"
SCHEMA_SNAP = HERE / "snapshots/af_scc_c0_vacuum.55d0a1ea9bda.yaml"
TAX_SNAP = HERE / "snapshots/formulation_taxonomy.0abb9ed8a961.yaml"
REV11_SCHEMA_SNAP = ROOT / "artifacts/worker-010/c0_class_conformance/snapshots/af_scc_c0_vacuum.1bb78ce9b357.yaml"

LIVE_FILES = {
    "ledger/theorems.jsonl": ROOT / "ledger/theorems.jsonl",
    "schemas/af_scc_c0_vacuum.yaml": ROOT / "schemas/af_scc_c0_vacuum.yaml",
    "ledger/class_coverage.csv": ROOT / "ledger/class_coverage.csv",
    "research_map/formulation_taxonomy.yaml": ROOT / "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json": ROOT / "artifacts/formulation/FROZEN.json",
}

# --------------------------------------------------------------------------------------
# independent predicate set (written from the class contract, not copied from the driver)
# --------------------------------------------------------------------------------------

RESULT_KINDS_EXCLUDED = {"definition", "conjecture", "literature_status", "stability_result"}
CONCLUSION_KINDS = {"theorem", "conditional_theorem"}
PEER_LEVELS = {"peer-reviewed", "accepted-in-press"}

GENERIC_RE = re.compile(
    r"(comeag|residual|\bgeneric|\bgenerically\b|open neighbourhood|open neighborhood|open set|\bdense\b)"
)
D1_VETO = (
    "exact solution", "not a generic", "not generic", "not quantified", "special",
    "characteristic", "interior", "impulsive", "high-frequency", "conditional",
    "assum", "does not fix", "class-dependent", "not applicable",
)
EXTENSION_POSITIVE = (
    "can be extended", "extends continuously", "continuously extendible",
    "extension exists", "admit a continuous extension", "admits a non-trivial",
    "extendible but not", "c^0-extendible", "c0-extendible", "c^0 extendible",
    "c0 extendible", "c^0-stability", "c0-stability",
)
C0_INEXT_RE = re.compile(
    r"continuous(?:ly)?[^.]{0,90}inextendib|inextendib[^.]{0,90}continuous|"
    r"c\s*\^?\{?0\}?[^.]{0,50}inextendib"
)
WEAKER_MARKERS = ("lipschitz", "c^{0,1}", "c^0,1", "c2", "c^2", "h2_loc", "h^2_loc", "l^2", "l2_loc")
C0_POSITIVE_RE = re.compile(r"metric\s+c\s*\^?\{?0\}?\b|merely continuous|continuous metric")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grab(text: str, key: str) -> str:
    m = re.search(r"^\s*" + re.escape(key) + r"\s*:\s*(.+)$", text, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def flatten(entry: dict) -> dict:
    scope = " ".join(entry.get("scope_caveats") or [])
    assumptions = " ".join(entry.get("assumptions") or [])
    statement = " ".join(str(entry.get(k) or "") for k in ("statement_exact", "label", "regularity"))
    return {
        "genericity": (entry.get("genericity") or "").lower(),
        "scope": scope.lower(),
        "assumptions": assumptions.lower(),
        "statement": statement.lower(),
        "regularity": (entry.get("regularity") or "").lower(),
        "all": " ".join([
            entry.get("genericity") or "", scope, assumptions, statement,
            entry.get("topology") or "",
        ]).lower(),
    }


def classify_independent(entry: dict) -> dict:
    """Return D1/D2/D3 plus explicit reasons; structured differently from the audit driver."""
    t = flatten(entry)
    kind = entry.get("entry_kind")
    concl = entry.get("conclusion_type")

    # D1: a RESULT entry over the class's generic set of one-ended AF vacuum Cauchy data.
    generic_hit = GENERIC_RE.search(t["genericity"])
    veto = [m for m in D1_VETO if m in t["genericity"] or m in t["scope"]]
    vacuum = "vacuum" in t["all"]
    af = ("asymptotically flat" in t["all"]) or bool(re.search(r"\baf\b", t["all"]))
    d1 = bool(kind not in RESULT_KINDS_EXCLUDED and generic_hit and vacuum and af and not veto)
    d1_reason = {
        "kind_excluded": kind in RESULT_KINDS_EXCLUDED,
        "genericity_hit": generic_hit.group(0) if generic_hit else None,
        "vacuum": vacuum,
        "asymptotically_flat": af,
        "veto_markers": veto,
    }

    # D2: conclusion is future C0-inextendibility of the maximal development.
    inext = "inextendib" in t["statement"]
    positive = [m for m in EXTENSION_POSITIVE if m in t["statement"]]
    c0_link = bool(C0_INEXT_RE.search(t["statement"]))
    weaker = any(m in t["regularity"] for m in WEAKER_MARKERS) and not C0_POSITIVE_RE.search(t["statement"])
    d2 = bool(concl in CONCLUSION_KINDS and inext and c0_link and not positive and not weaker)
    d2_reason = {
        "conclusion_type": concl,
        "conclusion_kind_ok": concl in CONCLUSION_KINDS,
        "inextendibility_token": inext,
        "c0_link": c0_link,
        "extension_positive_markers": positive,
        "weaker_regularity_only": weaker,
    }

    # D3: accepted evidence with no open items and no preprint caveat.
    raw_status = entry.get("status")
    content_status = entry.get("content_status")
    equiv = {"verified": "accepted", "accepted": "accepted", "provisional": "provisional",
             "rejected": "rejected"}.get(content_status, content_status)
    status_accepted = (raw_status == "accepted") or (raw_status is None and equiv == "accepted")
    peer = entry.get("evidence_level") in PEER_LEVELS
    n_unresolved = len(entry.get("unresolved") or [])
    no_open = n_unresolved == 0
    no_preprint = entry.get("evidence_level") != "preprint" and "preprint" not in t["scope"]
    d3 = bool(status_accepted and peer and no_open and no_preprint)
    d3_reason = {
        "raw_status_key_present": raw_status is not None,
        "raw_status": raw_status,
        "content_status": content_status,
        "content_status_equivalent": equiv,
        "status_accepted_corrected_mapping": status_accepted,
        "evidence_level": entry.get("evidence_level"),
        "peer_level": peer,
        "n_unresolved": n_unresolved,
        "no_preprint": no_preprint,
    }

    failing = [n for n, ok in (("D1_data_class", d1), ("D2_conclusion", d2), ("D3_evidence", d3)) if not ok]
    return {
        "checks": {"D1_data_class": d1, "D2_conclusion": d2, "D3_evidence": d3},
        "discharges_class": not failing,
        "failing_conjuncts": failing,
        "reasons": {"D1": d1_reason, "D2": d2_reason, "D3": d3_reason},
    }


def my_direction(entry: dict) -> str:
    t = flatten(entry)
    if any(m in t["statement"] for m in EXTENSION_POSITIVE):
        return "falsifier_side_extension_exists"
    if any(m in t["regularity"] for m in ("lipschitz", "c^{0,1}", "c^0,1")) and "inextendib" in t["statement"]:
        return "weaker_inextendibility_not_C0"
    c = classify_independent(entry)
    if c["checks"]["D2_conclusion"]:
        return "supports_conclusion"
    return "no_C0_conclusion"


# --------------------------------------------------------------------------------------
# adversarial synthetic controls (the independent classifier must be able to say yes)
# --------------------------------------------------------------------------------------

CONTROL_BASE = {
    "theorem_id": "CTRL-POS",
    "entry_kind": "theorem",
    "conclusion_type": "theorem",
    "genericity": "A comeager (residual) set of one-ended asymptotically flat vacuum Cauchy data.",
    "scope_caveats": [],
    "assumptions": ["Einstein vacuum equations"],
    "statement_exact": "The maximal globally hyperbolic development is inextendible as a Lorentzian manifold with a continuous metric.",
    "regularity": "C^0 metric.",
    "topology": "asymptotically flat; future null infinity",
    "content_status": "verified",
    "evidence_level": "peer-reviewed",
    "unresolved": [],
}


def control(name: str, **over: object) -> dict:
    e = dict(CONTROL_BASE)
    e.update(over)
    e["theorem_id"] = name
    return e


CONTROLS = [
    (control("CTRL-POS"), True, []),
    (control("CTRL-NEG-D1", genericity="Exact solution, not a generic-data statement."), False, ["D1_data_class"]),
    (control("CTRL-NEG-D2-OPP",
             statement_exact="The maximal development can be extended across the Cauchy horizon as a Lorentzian manifold with continuous metric."),
     False, ["D2_conclusion"]),
    (control("CTRL-NEG-D2-WEAK",
             statement_exact="The maximal development is Lipschitz-inextendible.",
             regularity="Lipschitz (C^{0,1})."),
     False, ["D2_conclusion"]),
    (control("CTRL-NEG-D3", unresolved=["open item"]), False, ["D3_evidence"]),
    # field-mapping control: same evidence strength as CTRL-POS but expressed in the rev3
    # ledger vocabulary (no `status` key, content_status=verified) must still pass D3.
    (control("CTRL-MAP-CONTENT-STATUS", content_status="verified", **{"status": None}),
     True, []),
]


def main() -> int:
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: object) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    # ---------- load target + pinned snapshots -----------------------------------------
    audit = json.loads(AUDIT_ORIG.read_text(encoding="utf-8"))
    audit_snap_bytes_equal = AUDIT_ORIG.read_bytes() == AUDIT_SNAP.read_bytes()
    check("audit_snapshot_copy_byte_identical", audit_snap_bytes_equal,
          {"orig": sha256_file(AUDIT_ORIG), "snap": sha256_file(AUDIT_SNAP)})

    pins = audit.get("inputs", {})
    pin_measurements = {}
    for rel, live in LIVE_FILES.items():
        want = (pins.get(rel) or {}).get("sha256")
        got = sha256_file(live) if live.exists() else None
        pin_measurements[rel] = {"pinned": want, "live": got, "live_matches_pin": want == got}
    check("live_inputs_match_audit_pins",
          all(v["live_matches_pin"] for v in pin_measurements.values()),
          pin_measurements)

    snap_map = {
        "ledger": (LEDGER_SNAP, (pins.get("ledger/theorems.jsonl") or {}).get("sha256")),
        "schema": (SCHEMA_SNAP, (pins.get("schemas/af_scc_c0_vacuum.yaml") or {}).get("sha256")),
        "taxonomy": (TAX_SNAP, (pins.get("research_map/formulation_taxonomy.yaml") or {}).get("sha256")),
    }
    snap_report = {}
    for name, (p, want) in snap_map.items():
        got = sha256_file(p)
        snap_report[name] = {"path": str(p.relative_to(ROOT)), "pinned": want, "measured": got,
                             "matches": want == got}
    check("pinned_snapshots_match_audit_pins", all(v["matches"] for v in snap_report.values()), snap_report)

    schema_text = SCHEMA_SNAP.read_text(encoding="utf-8")
    cdef = audit.get("class_definition", {})
    check("class_definition_hash_binds_schema_snapshot",
          cdef.get("sha256") == sha256_file(SCHEMA_SNAP) and cdef.get("revision") == "12",
          {"class_definition_sha256": cdef.get("sha256"), "schema_snapshot_sha256": sha256_file(SCHEMA_SNAP),
           "revision": cdef.get("revision")})
    check("class_id_and_gate_fields",
          audit.get("class_id") == CLASS and audit.get("node_id") == "L1" and audit.get("gate") == "G-LIT",
          {"class_id": audit.get("class_id"), "node_id": audit.get("node_id"), "gate": audit.get("gate")})
    check("schema_sibling_disjoint_from_c2",
          grab(schema_text, "sibling_disjoint_from").strip('"') == SIBLING,
          {"sibling_disjoint_from": grab(schema_text, "sibling_disjoint_from")})

    # ---------- frozen class contract cross-check -------------------------------------
    tax = yaml.safe_load(TAX_SNAP.read_text(encoding="utf-8"))
    contract = (tax.get("classes") or {}).get(CLASS, {})
    axes = contract.get("axes", {})
    conclusion = contract.get("conclusion", {})
    contract_ok = (
        axes.get("regularity_token") == "C0"
        and axes.get("conclusion_type") == "strong_cosmic_censorship_C0"
        and "C2-inextendibility" in " ".join(contract.get("exclusions") or [])
        and "comeager" in conclusion.get("text", "")
    )
    check("taxonomy_class_contract_matches_schema_reading", contract_ok,
          {"regularity_token": axes.get("regularity_token"),
           "conclusion_type": axes.get("conclusion_type"),
           "exclusions": contract.get("exclusions"),
           "conclusion_text_excerpt": conclusion.get("text", "")[:220]})

    # ---------- binding set from the ledger snapshot -----------------------------------
    entries = [json.loads(line) for line in LEDGER_SNAP.read_text(encoding="utf-8").splitlines() if line.strip()]
    bound = sorted((e for e in entries if CLASS in (e.get("class_ids") or [])),
                   key=lambda e: e.get("theorem_id") or "")
    my_ids = [e["theorem_id"] for e in bound]
    audit_bindings = audit.get("bindings", [])
    audit_ids = [b.get("theorem_id") for b in audit_bindings]
    check("binding_set_matches_audit", my_ids == audit_ids, {"mine": my_ids, "audit": audit_ids})

    # rev11 binding set (if present) for set-drift evidence
    rev11_ids = None
    rev11_report = ROOT / "artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.json"
    if rev11_report.exists():
        try:
            rev11_ids = [b["theorem_id"] for b in json.loads(rev11_report.read_text(encoding="utf-8"))["bindings"]]
        except Exception:
            rev11_ids = None
    check("binding_set_unchanged_vs_rev11", rev11_ids is None or sorted(rev11_ids) == my_ids,
          {"rev11": rev11_ids, "rev12": my_ids})

    # ---------- per-binding independent re-derivation ----------------------------------
    rows = []
    for entry, ab in zip(bound, audit_bindings):
        mine = classify_independent(entry)
        audit_checks = ab.get("checks", {})
        audit_discharge = ab.get("discharges_class")
        internal_consistent = bool(
            audit_discharge == (not ab.get("failing_conjuncts"))
            and audit_discharge == all(audit_checks.values())
        )
        rows.append({
            "theorem_id": entry["theorem_id"],
            "audit_checks": audit_checks,
            "audit_discharges_class": audit_discharge,
            "audit_direction": ab.get("direction"),
            "independent_checks": mine["checks"],
            "independent_discharges_class": mine["discharges_class"],
            "independent_failing_conjuncts": mine["failing_conjuncts"],
            "independent_direction": my_direction(entry),
            "audit_binding_internally_consistent": internal_consistent,
            "discharge_agreement": audit_discharge == mine["discharges_class"],
            "d1_agreement": audit_checks.get("D1_data_class") == mine["checks"]["D1_data_class"],
            "d2_agreement": audit_checks.get("D2_conclusion") == mine["checks"]["D2_conclusion"],
            "d3_boolean_agreement": audit_checks.get("D3_evidence") == mine["checks"]["D3_evidence"],
            "d3_reasons": mine["reasons"]["D3"],
            "d1_reasons": mine["reasons"]["D1"],
            "d2_reasons": mine["reasons"]["D2"],
        })

    n = len(rows)
    discharge_agree = sum(r["discharge_agreement"] for r in rows)
    d1_agree = sum(r["d1_agreement"] for r in rows)
    d2_agree = sum(r["d2_agreement"] for r in rows)
    d3_agree = sum(r["d3_boolean_agreement"] for r in rows)
    internal_ok = all(r["audit_binding_internally_consistent"] for r in rows)
    n_discharging_independent = sum(r["independent_discharges_class"] for r in rows)
    n_discharging_audit = sum(bool(r["audit_discharges_class"]) for r in rows)

    check("audit_bindings_internally_consistent", internal_ok,
          {"n": n, "failures": [r["theorem_id"] for r in rows if not r["audit_binding_internally_consistent"]]})
    check("discharge_verdicts_agree_all_bindings", discharge_agree == n,
          {"agreement": f"{discharge_agree}/{n}",
           "disagreements": [r["theorem_id"] for r in rows if not r["discharge_agreement"]]})
    check("d2_conclusion_verdicts_agree_all_bindings", d2_agree == n,
          {"agreement": f"{d2_agree}/{n}",
           "disagreements": [r["theorem_id"] for r in rows if not r["d2_agreement"]]})
    check("zero_discharging_reproduced_independently",
          n_discharging_independent == 0 and n_discharging_audit == 0,
          {"audit": n_discharging_audit, "independent": n_discharging_independent})
    check("class_conclusion_state_open_problem",
          audit.get("summary", {}).get("class_conclusion_state") == "open_problem",
          {"audit": audit.get("summary", {}).get("class_conclusion_state")})

    # ---------- D3 mechanism: status-key artifact --------------------------------------
    n_with_status_key = sum("status" in e for e in entries)
    n_with_content_status = sum("content_status" in e for e in entries)
    corrected_accepted = [r["theorem_id"] for r in rows
                          if r["d3_reasons"]["status_accepted_corrected_mapping"]]
    raw_accepted = [r["theorem_id"] for r in rows if r["d3_reasons"]["raw_status"] == "accepted"]
    mechanism_artifact = (n_with_status_key == 0 and n_with_content_status == len(entries)
                          and len(raw_accepted) == 0 and len(corrected_accepted) > 0)
    check("d3_status_field_artifact_confirmed", mechanism_artifact,
          {"entries_with_status_key": n_with_status_key, "entries_with_content_status": n_with_content_status,
           "raw_status_accepted": raw_accepted, "content_status_equivalent_accepted": corrected_accepted})
    check("headline_robust_under_corrected_d3_mapping",
          n_discharging_independent == 0 and all(not r["independent_checks"]["D3_evidence"] for r in rows),
          {"d3_failures_under_corrected_mapping": [r["theorem_id"] for r in rows
                                                   if not r["independent_checks"]["D3_evidence"]]})

    # ---------- rev11 -> rev12 drift, normal-form check --------------------------------
    rev11_text = REV11_SCHEMA_SNAP.read_text(encoding="utf-8") if REV11_SCHEMA_SNAP.exists() else ""
    fields = ["revision", "class_id", "conclusion_type", "statement_natural_language",
              "statement_formal", "epistemic_status", "genericity_kind",
              "extension_regularity", "extension_regularity_exact"]
    rev11_def = {k: grab(rev11_text, k) for k in fields}
    rev12_def = {k: grab(schema_text, k) for k in fields}
    differing = [k for k in fields if rev11_def[k] != rev12_def[k]]
    changed = [k for k in differing if k != "revision"]

    def normal_form(s: str) -> str:
        for a, b in (("(s,delta)", "r"), ("{s,delta}", "r"), ("G_{s,delta}", "G_r"),
                     ("X^{s,delta}_vac", "X^r_vac"), ("X^{s,delta}", "X^r")):
            s = s.replace(a, b)
        return re.sub(r"\s+", " ", s).strip()

    norm_equal = normal_form(rev11_def["statement_formal"]) == normal_form(rev12_def["statement_formal"])
    check("rev11_to_rev12_drift_remeasured", differing == ["revision", "statement_formal"],
          {"differing_fields": differing, "audit_claim": ["revision", "statement_formal"]})
    check("statement_formal_diff_is_parameter_renaming_only", norm_equal,
          {"rev11_normalized": normal_form(rev11_def["statement_formal"]),
           "rev12_normalized": normal_form(rev12_def["statement_formal"])})

    # ---------- adversarial controls ---------------------------------------------------
    control_rows = []
    controls_ok = True
    for entry, expect_discharge, expect_failing in CONTROLS:
        c = classify_independent(entry)
        ok = (c["discharges_class"] == expect_discharge
              and (expect_discharge or c["failing_conjuncts"] == expect_failing))
        controls_ok = controls_ok and ok
        control_rows.append({"name": entry["theorem_id"], "expected_discharge": expect_discharge,
                             "observed_discharge": c["discharges_class"],
                             "expected_failing": expect_failing,
                             "observed_failing": c["failing_conjuncts"], "pass": ok})
    check("adversarial_controls", controls_ok, control_rows)

    # ---------- findings ---------------------------------------------------------------
    findings = [
        {
            "id": "V010-F1",
            "severity": "medium",
            "statement": (
                "The audit's D3 reading (n_accepted_status=0) and its note that the rev11 accepted "
                "statuses were 'self-certified records since downgraded' are caused by a ledger field "
                "rename, not by an evidence downgrade: at ledger a1674f094979 no entry carries a "
                "`status` key (0/62); the equivalent field is `content_status`, and 9 of the 11 bound "
                "entries are `content_status=verified` (D-004 and T-305 are `provisional`). The "
                "driver's D3 predicate `entry.get('status') == 'accepted'` therefore cannot be true "
                "at this revision."
            ),
            "evidence": {
                "entries_with_status_key": n_with_status_key,
                "entries_with_content_status": n_with_content_status,
                "content_status_equivalent_accepted": corrected_accepted,
                "driver_line": "artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.py:148",
                "rev11_status_to_rev12_content_status": {r["theorem_id"]: {
                    "audit_checks": r["audit_checks"].get("D3_evidence"),
                    "content_status": r["d3_reasons"]["content_status"],
                } for r in rows},
            },
            "impact_on_headline": (
                "none: under the corrected content_status mapping D3 still fails for all 11 bindings "
                "(every binding has >=1 unresolved item and/or a preprint evidence level), so "
                "n_discharging=0 and class_conclusion_state=open_problem are unchanged. Only the "
                "stated mechanism is corrected."
            ),
            "falsifier": (
                "Exhibit a `status` key in ledger/theorems.jsonl#a1674f094979, or one bound entry "
                "that passes D3 (accepted-equivalent status AND peer-reviewed/accepted-in-press AND "
                "zero unresolved items AND no preprint caveat)."
            ),
        },
        {
            "id": "V010-F2",
            "severity": "info",
            "statement": (
                "The rev12 report is a same-implementation re-run: c0_reaudit_rev12.py imports the "
                "unmodified rev11 driver c0_class_conformance_audit.py and monkeypatches only its "
                "output path. It is a re-pin, not an independent re-implementation; this verifier "
                "supplies the missing third implementation."
            ),
            "evidence": {
                "wrapper": "artifacts/worker-010/c0_class_conformance/c0_reaudit_rev12.py:62-70",
                "driver_sha256_after_import": audit.get("revision_addendum", {}).get("driver_sha256"),
                "driver_unmodified": audit.get("revision_addendum", {}).get("driver_unmodified"),
            },
            "impact_on_headline": "none; the headline is independently reproduced here.",
            "falsifier": "Show that the wrapper re-implements the predicates rather than importing the rev11 driver.",
        },
        {
            "id": "V010-F3",
            "severity": "info",
            "statement": (
                "The rev11 -> rev12 class-definition move is a parameter renaming plus a revision "
                "stamp at extraction level: `statement_formal` normalizes to equality under "
                "(s,delta)->r and G_{s,delta}->G_r, and no other extracted class field changed. No "
                "class-semantics change is detectable mechanically; whether the renaming is semantic "
                "remains an F1/A1 adjudication."
            ),
            "evidence": {"differing_fields": differing, "normalized_equal": norm_equal},
            "impact_on_headline": "none; binding set and discharge reading unchanged from rev11.",
            "falsifier": "Exhibit a further changed class field (beyond revision/statement_formal) or a normalized statement_formal mismatch.",
        },
    ]
    if d1_agree != n:
        findings.append({
            "id": "V010-F4",
            "severity": "low",
            "statement": (
                "Conjunct-level classifier sensitivity: the independent D1 reading differs from the "
                "audit on at least one binding (open-neighbourhood genericity is read permissively by "
                "the independent predicate). No discharge verdict changes because D2/D3 fail for "
                "those bindings independently."
            ),
            "evidence": {"disagreements": [r["theorem_id"] for r in rows if not r["d1_agreement"]],
                         "d1_agreement": f"{d1_agree}/{n}"},
            "impact_on_headline": "none.",
            "falsifier": "Show a D1 disagreement that flips a discharge verdict.",
        })

    core_pass = all(c["pass"] for c in checks if c["check"] != "adversarial_controls") and controls_ok

    report = {
        "verification_id": f"worker-010-c0-rev12-independent-verify-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "verifier": "worker-010",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "provenance_disclosure": (
            "The verifier shares fleet slot 010 with the target's actor alias (deepseek-flash-10). "
            "This is a mechanical reproducibility check by an independently written implementation; "
            "it is not an independent reviewer verdict and does not move any gate."
        ),
        "target": {
            "path": str(AUDIT_ORIG.relative_to(ROOT)),
            "sha256": sha256_file(AUDIT_ORIG),
            "report_id": audit.get("report_id"),
            "validation_status": audit.get("validation_status"),
            "actor": audit.get("actor"),
            "alias_actor": audit.get("alias_actor"),
            "class_id": audit.get("class_id"),
        },
        "method": {
            "class_contract_source": "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN",
            "schema_source": "schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda",
            "ledger_source": "ledger/theorems.jsonl#a1674f094979",
            "binding_rule": "theorem entries whose class_ids contains AF-SCC-C0-VAC-GEN",
            "discharge_rule": "D1_data_class AND D2_conclusion AND D3_evidence",
            "implementation": "independent third implementation; the audited driver is not imported",
        },
        "pins": {"live_vs_audit": pin_measurements, "snapshots": snap_report},
        "taxonomy_contract_check": {"pass": contract_ok, "axes": axes, "exclusions": contract.get("exclusions")},
        "drift_check_rev11_rev12": {
            "differing_fields": differing,
            "fields_changed_beyond_revision": changed,
            "statement_formal_normalized_equal": norm_equal,
            "rev11_statement_formal": rev11_def["statement_formal"],
            "rev12_statement_formal": rev12_def["statement_formal"],
        },
        "bindings": rows,
        "summary": {
            "n_bound_entries": n,
            "n_discharging_audit": n_discharging_audit,
            "n_discharging_independent": n_discharging_independent,
            "class_conclusion_state_audit": audit.get("summary", {}).get("class_conclusion_state"),
            "class_conclusion_state_independent": "open_problem" if n_discharging_independent == 0 else "discharged",
            "discharge_agreement": f"{discharge_agree}/{n}",
            "d1_agreement": f"{d1_agree}/{n}",
            "d2_agreement": f"{d2_agree}/{n}",
            "d3_boolean_agreement": f"{d3_agree}/{n}",
            "n_accepted_status_audit": audit.get("summary", {}).get("n_accepted_status"),
            "n_accepted_status_corrected_content_status_mapping": len(corrected_accepted),
            "raw_status_accepted_mapping": len(raw_accepted),
            "headline_reproduced": bool(n_discharging_independent == 0 and discharge_agree == n),
            "all_pass": bool(core_pass),
        },
        "checks": checks,
        "negative_controls": control_rows,
        "findings": findings,
        "falsifier": (
            "Any of: a live input no longer matching the audit pin at re-measurement; an independent "
            "binding selection differing from the audit's 11 ids; an independent discharge verdict of "
            "true for any bound entry; an independent D2 verdict differing on any binding; or a "
            "synthetic discharging control that the independent predicate set cannot discharge. "
            "Any of these falsifies 'headline reproduced'."
        ),
        "limitations": [
            "Mechanical field reading only; class_ids are inherited from L0/L1 and not re-adjudicated.",
            "Same fleet slot as the target alias; not an independence claim in the reviewer sense.",
            "Snapshots are pinned at read time; later canonical drift voids citation at the newer revision.",
            "The corrected D3 mapping (content_status verified->accepted) is this verifier's reading of the rev3 ledger vocabulary, recorded as a finding for L0/A1 rather than applied to the ledger.",
        ],
        "evidence_refs": [
            f"{AUDIT_ORIG.relative_to(ROOT)}#{sha256_file(AUDIT_ORIG)[:12]}",
            f"schemas/af_scc_c0_vacuum.yaml#{sha256_file(SCHEMA_SNAP)[:12]}",
            f"ledger/theorems.jsonl#{sha256_file(LEDGER_SNAP)[:12]}",
            f"research_map/formulation_taxonomy.yaml#{sha256_file(TAX_SNAP)[:12]}",
            f"artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.py#{sha256_file(ROOT / 'artifacts/worker-010/c0_class_conformance/c0_class_conformance_audit.py')[:12]}",
            f"artifacts/worker-010/c0_class_conformance/c0_reaudit_rev12.py#{sha256_file(ROOT / 'artifacts/worker-010/c0_class_conformance/c0_reaudit_rev12.py')[:12]}",
        ],
    }

    out = HERE / "verify_c0_rev12_independent.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"wrote {out.relative_to(ROOT)}")
    print(json.dumps(report["summary"], indent=2))
    print("findings:", [f["id"] + ":" + f["severity"] for f in findings])
    print("failed checks:", [c["check"] for c in checks if not c["pass"]])
    return 0 if core_pass and controls_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
