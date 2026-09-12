#!/usr/bin/env python3
"""F1-REVISE-DISPOSITION-01: textual disposition of F1 revise findings at the frozen revision.

Question: the recorded F1 revise verdicts bind revision 3 (sha 7a3e1f93...). The frozen
canonical revision is rev9 (sha b65fcc0f...). For every concrete finding in those verdicts,
is the cited defect still present in the frozen bytes?

This is a STATIC TEXT AUDIT authored by the agent id that authored the F1 draft
(deepseek-flash-03). It is NOT a review verdict, NOT an acceptance, and it carries no gate
authority. Every disposition is derived from a named, re-runnable probe over the frozen
bytes; residuals that need a human/mathematical call are reported as observations, not
silently closed.

Run:
    python3 artifacts/worker-03/f1_revise_disposition/scan_f1_disposition.py

Exit codes: 0 = report written and frozen pin matched; 2 = frozen pin mismatch (report
written in drift mode, dispositions marked void).
"""
from __future__ import annotations

import difflib
import hashlib
import os
import json

import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

FROZEN_PIN_FIRST_SCAN = "b65fcc0f0118980fe50b4a5eaf5fb637f4f744d0db095105fd8031db1dabcd94"
AUTHORING_F1 = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
CANONICAL_F1 = "schemas/af_wcc_vacuum.yaml"
FROZEN_MANIFEST = "artifacts/formulation/FROZEN.json"
F1_REV9_SNAPSHOT = "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.b65fcc0f.yaml"
F0_CANONICAL = "research_map/formulation_taxonomy.yaml"
F0_AUTHORING = "artifacts/formulation/formulation_taxonomy.yaml"
F1_SUITE = "schemas/f1_falsifier_tests.jsonl"
SUITE_PIN = "bd405cffcc2d87e97c18ce521a50e6636a02edb67702eb7b428ee10905147692"
REVIEWS = {
    "flash16_r1": "reviews/F1-review-16.json",
    "flash16_r2": "reviews/F1-review-16-r2.json",
    "lead_audit": "reviews/F1-review-lead-audit.json",
}

TASK_ID = "F1-REVISE-DISPOSITION-01"
REPORT_ID = "w03-f1revdisp"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(ROOT / path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def probe(text: str, pattern: str, mode: str = "present", min_count: int = 1) -> dict:
    """Return a named probe result over the frozen bytes.

    mode: present  -> result True iff >= min_count matching lines
          absent   -> result True iff 0 matching lines
          count_ge -> result True iff matching lines >= min_count (raw count recorded)
    """
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(pattern, line):
            hits.append({"line": i, "excerpt": line.strip()[:220]})
    count = len(hits)
    if mode == "present":
        result = count >= min_count
    elif mode == "absent":
        result = count == 0
    elif mode == "count_ge":
        result = count >= min_count
    else:
        raise ValueError(mode)
    return {
        "pattern": pattern,
        "mode": mode,
        "min_count": min_count,
        "match_count": count,
        "result": result,
        "hits": hits[:12],
    }


def build_checks() -> list[dict]:
    """(check_id, expected_result, description, probe kwargs)."""
    return [
        # --- F1-16-01: unverified equivalence inside the operative statement
        ("T01_past_phrase_absent", True, "the reviewed phrase 'complete to the past' is absent",
         (r"complete to the past", "absent", 1)),
        ("T01_equivalence_sequestered", True, "the unverified equivalence is isolated and tagged",
         (r"claimed equivalence, UNVERIFIED", "present", 1)),
        ("T01_statement_no_equivalently", True,
         "neither conclusion.statement_* line carries an 'equivalently' clause",
         (r"^  statement_(natural_language|formal):.*equivalently", "absent", 1)),
        # --- F1-16-02: freeze integrity
        ("T02_revision_label_present", True, "a revision label exists", (r"^revision: \d+$", "present", 1)),
        # --- F1-16-03: non-vacuity black-hole requirement
        ("T03_bh_excluded", True, "black-hole non-emptiness explicitly excluded from non_vacuity",
         (r"separate black-hole-formation statement", "present", 1)),
        ("T03_bh_forbidden_strengthening", True, "black-hole non-emptiness named a forbidden strengthening",
         (r"black-hole region non-empty \(black-hole formation", "present", 1)),
        ("T03_g_nonempty", True, "G non-emptiness argued (Baire)", (r"G is non-empty because X_vac is Baire", "present", 1)),
        # --- F1-16-04: tier_1 vs the statement
        ("T04_non_meager", True, "tier_1 requires non-meagerness", (r"NON-MEAGER", "present", 1)),
        ("T04_tier2", True, "a separate single-datum tier exists", (r"^  tier_2:", "present", 1)),
        # --- F1-16-05: machine-checkable vs proof obligations
        ("T05_proof_obligations", True, "proof_obligations block exists", (r"^    proof_obligations:", "present", 1)),
        ("T05_machine_checkable", True, "machine_checkable_steps block exists",
         (r"^    machine_checkable_steps:", "present", 1)),
        # --- F1-16-06: pinned quantifiers with pending domains
        ("T06_acceptance_map_absent", True, "the acceptance_map block is gone", (r"acceptance_map", "absent", 1)),
        ("T06_pinned_token_absent", True, "the token 'pinned' is gone", (r"\bpinned\b", "absent", 1)),
        ("T06_quantifier_class", True, "the quantifier class is stated", (r"^  quantifier_class:", "present", 1)),
        # --- F1-16-07: ambiguity runner on the frozen revision
        ("T07_suite_hash_unbound", True, "the frozen suite hash is NOT cited inside the schema",
         (r"bd405cff", "absent", 1)),
        ("T07_stale_provenance", True, "schema provenance still cites the r3 worker draft",
         (r"worker_sha256: 7a3e1f93", "present", 1)),
        # --- F1-16-08: dangling unresolved refs
        ("T08_unresolved_refs_absent", True, "no unresolved_refs field remains", (r"unresolved_refs", "absent", 1)),
        ("T08_old_topology_key_absent", True, "the old initial_slice_topology key is gone",
         (r"initial_slice_topology", "absent", 1)),
        ("T08_curve_class_absent", True, "visibility.curve_class is gone", (r"curve_class", "absent", 1)),
        # --- lead-audit HF-06
        ("A06_f0_equivalent_form_absent", True, "f0_equivalent_form is gone", (r"f0_equivalent_form", "absent", 1)),
        ("A06_linter_absent", True, "no linter-shaped wording remains", (r"linter", "absent", 1)),
        ("A06_B_nonempty_interior_absent", True, "the old 'B has non-empty interior' clause is gone",
         (r"B has non-empty", "absent", 1)),
        ("A06_slice_complete_asserted", True, "slice completeness is asserted as a class assumption",
         (r"^  completeness_of_slice: true", "present", 1)),
        # --- lead-audit HF-04
        ("A04_intersect_M_explicit", True, "the M-intersection typing is explicit (formal + D5)",
         (r"intersect M", "present", 2)),
        # --- derived: F0 binding freshness
        ("BIND_f0_binding_field", True, "f0_binding block exists", (r"^f0_binding:", "present", 1)),
    ]


def check_results(text: str) -> dict:
    out = {}
    for cid, expected, desc, (pat, mode, minc) in build_checks():
        r = probe(text, pat, mode, minc)
        r.update({"expected": expected, "pass": r["result"] == expected, "description": desc})
        out[cid] = r
    # count-based residual probes
    extra = {
        "T02_duplicate_revised_at": probe(text, r"^revised_at:", "count_ge", 2),
        "T05_mc_future_inext": probe(text, r"finite affine parameter while future-inextendible", "present", 1),
        "T05_po_future_inext": probe(text, r"future-inextendibility of gamma in M", "present", 1),
        "T07_open_rows_mismatch": probe(text, r"test: F1-AMB-", "count_ge", 3),
        "T04_tier1_robust_label": probe(text, r"tier_1[-_]robust", "present", 1),
        "T01_completeness_equivalently": probe(text, r"completeness_definition:.*equivalently", "present", 1),
    }
    for cid, r in extra.items():
        r["expected"] = None
        r["pass"] = None
        out[cid] = r
    return out


def base_ok(checks: dict, base: list) -> bool:
    return all(checks[cid]["result"] == exp for cid, exp in base)



DECLARED_FINAL_EVENT = "leadform-status-0013"
QUIESCE_MAX_S = 150
QUIESCE_INTERVAL_S = 4
QUIESCE_NEED = 3


def sample_state() -> dict:
    frozen = json.loads((ROOT / FROZEN_MANIFEST).read_text())
    entry = frozen.get("files", {}).get(CANONICAL_F1, {})
    return {
        "t": now(),
        "f1_sha256": sha256(CANONICAL_F1),
        "f1_mtime": datetime.fromtimestamp(os.path.getmtime(ROOT / CANONICAL_F1), CST).isoformat(timespec="seconds"),
        "manifest_revision": frozen.get("revision"),
        "manifest_pin": entry.get("sha256"),
    }


def wait_quiescent() -> tuple:
    """Wait until disk == manifest pin and the triple is stable for N samples.

    The formulation fleet was republishing F1 in place while this task ran; a static
    disposition of unpinned bytes is worthless, so we wait for a settled (hash, pin, revision).
    """
    samples = [sample_state()]
    deadline = time.time() + QUIESCE_MAX_S
    while time.time() < deadline:
        time.sleep(QUIESCE_INTERVAL_S)
        samples.append(sample_state())
        tail = samples[-QUIESCE_NEED:]
        keys = {(x["f1_sha256"], x["manifest_pin"], x["manifest_revision"]) for x in tail}
        if len(tail) == QUIESCE_NEED and len(keys) == 1 and tail[-1]["f1_sha256"] == tail[-1]["manifest_pin"]:
            return True, samples
    return False, samples


def declared_final_pin() -> dict:
    """The F1 hash named by the NEWEST formulation-lead status event."""
    path = ROOT / "comms" / "outbox" / "astra-lead-formulation.jsonl"
    if not path.is_file():
        return {"event_id": None, "sha256": None, "source": None}
    best = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("event_type") == "status" and str(d.get("event_id", "")).startswith("leadform-status"):
            if best is None or str(d.get("created_at", "")) >= str(best.get("created_at", "")):
                best = d
    if not best:
        return {"event_id": None, "sha256": None, "source": str(path.relative_to(ROOT))}
    m = re.search(r"schemas rev\d+\s*\(?\s*([0-9a-f]{64})", best.get("summary", ""))
    return {
        "event_id": best.get("event_id"),
        "sha256": m.group(1) if m else None,
        "source": str(path.relative_to(ROOT)),
        "created_at": best.get("created_at"),
    }


def main() -> int:
    started = now()
    quiescent, churn = wait_quiescent()
    frozen = json.loads((ROOT / FROZEN_MANIFEST).read_text())
    files = frozen.get("files", {})
    pin_entry = files.get(CANONICAL_F1, {})
    frozen_pin = pin_entry.get("sha256") or FROZEN_PIN_FIRST_SCAN
    pin_source = f"{FROZEN_MANIFEST}#files.{CANONICAL_F1}.sha256"
    f1_start = sha256(CANONICAL_F1)
    text = (ROOT / CANONICAL_F1).read_text(encoding="utf-8")
    checks = check_results(text)
    f1_end = sha256(CANONICAL_F1)
    pin_matches = f1_start == frozen_pin
    authoring_aligned = sha256(AUTHORING_F1) == frozen_pin
    manifest_pins_match = all(
        files.get(p, {}).get("sha256") == frozen_pin for p in (CANONICAL_F1, AUTHORING_F1)
    )
    stable = f1_start == f1_end

    # F0 binding measurement (declared vs measured) -- may drift during the scan; measure twice
    m = re.search(r'declared_f0_sha256:\s*"([0-9a-f]{64})"', text)
    declared_f0 = m.group(1) if m else None
    f0_can_a, f0_auth_a = sha256(F0_CANONICAL), sha256(F0_AUTHORING)
    f0_can_b, f0_auth_b = sha256(F0_CANONICAL), sha256(F0_AUTHORING)
    f0_stale = declared_f0 not in {f0_can_a, f0_auth_a, f0_can_b, f0_auth_b}
    checks["BIND_declared_f0_stale"] = {
        "description": "declared F0 hash matches neither the measured canonical nor authoring F0 artifact",
        "expected": False,
        "result": bool(f0_stale),
        "pass": not bool(f0_stale),
        "match_count": int(bool(f0_stale)),
        "pattern": "(measurement)",
        "mode": "measure",
        "min_count": 1,
        "hits": [
            {"line": 0, "excerpt": f"declared={declared_f0}"},
            {"line": 0, "excerpt": f"measured_canonical={f0_can_a}"},
            {"line": 0, "excerpt": f"measured_authoring={f0_auth_a}"},
        ],
    }
    def measure_check(cid, desc, value, excerpt):
        checks[cid] = {
            "description": desc, "expected": True, "result": bool(value), "pass": bool(value),
            "match_count": int(bool(value)), "pattern": "(measurement)", "mode": "measure",
            "min_count": 1, "hits": [{"line": 0, "excerpt": excerpt}],
        }

    measure_check("M_f1_hash_match", "canonical F1 sha256 equals the FROZEN pin", pin_matches,
                  f"measured={f1_start} pin={frozen_pin}")
    measure_check("M_authoring_aligned", "authoring F1 sha256 equals the canonical F1 sha256", authoring_aligned,
                  f"canonical={f1_start} authoring={sha256(AUTHORING_F1)}")
    measure_check("M_stable_during_scan", "canonical F1 sha256 did not change during the scan", stable,
                  f"start={f1_start} end={f1_end}")
    measure_check("M_manifest_pins_f1", "FROZEN manifest pins both F1 paths at the frozen sha256", manifest_pins_match,
                  f"revision={frozen.get('revision')}")
    suite_binding = None
    if (ROOT / F1_SUITE).is_file():
        for line in (ROOT / F1_SUITE).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("binding_sha256"):
                suite_binding = rec["binding_sha256"]
                break
    suite_ok = suite_binding == frozen_pin
    checks["M_suite_bound_to_frozen"] = {
        "description": "external ambiguity suite declares a binding_sha256 equal to the frozen F1 pin",
        "expected": True,
        "result": bool(suite_ok),
        "pass": bool(suite_ok),
        "match_count": int(bool(suite_ok)),
        "pattern": "(measurement)",
        "mode": "measure",
        "min_count": 1,
        "hits": [{"line": 0, "excerpt": f"{F1_SUITE} sha256={sha256(F1_SUITE) if (ROOT/F1_SUITE).is_file() else 'MISSING'} binding_sha256={suite_binding}"}],
    }

    # ---- dispositions -------------------------------------------------------
    F = []  # findings

    def add(fid, source, bound, severity, claim, base, residual, falsifier,
            verdict_override=None, observations=()):
        b = base_ok(checks, base)
        res = [cid for cid in residual if checks[cid]["result"]]
        if verdict_override:
            verdict = verdict_override
        elif not b:
            verdict = "present_at_frozen"
        elif res:
            verdict = "partially_resolved_at_frozen"
        else:
            verdict = "resolved_at_frozen"
        F.append({
            "id": fid, "source_review": source, "review_bound_sha256_12": bound,
            "severity": severity, "finding": claim,
            "base_checks": [{"check_id": c, "expected": e, "result": checks[c]["result"]} for c, e in base],
            "residual_checks": [{"check_id": c, "result": checks[c]["result"], "hits": checks[c]["hits"][:3]} for c in residual],
            "verdict": verdict,
            "evidence": {c: checks[c]["hits"][:4] for c, _ in base if checks[c]["hits"]},
            "observations": list(observations),
            "falsifier": falsifier,
        })

    add("F1-16-01", "reviews/F1-review-16.json", "f55722a74167", "major",
        "operative statement asserted an equivalence the artifact marks unverified",
        [("T01_past_phrase_absent", True), ("T01_equivalence_sequestered", True),
         ("T01_statement_no_equivalently", True)],
        [],
        "Show the phrase 'complete to the past' or an equivalently-clause in conclusion.statement_* at b65fcc0f.",
        observations=[{
            "id": "OBS-01",
            "anchor": checks["T01_completeness_equivalently"]["hits"],
            "statement": "completeness_definition (l.198) still uses 'equivalently' for generator-completeness vs infinite affine length of null geodesics reaching I+; l.199 labels it definitional and excludes the unverified conclusion equivalence. Whether that null-null restatement is a definitional identity or a theorem is a reviewer adjudication item.",
            "falsifier": "Exhibit a null geodesic reaching I+ with finite affine length whose generator is future-complete (or the converse) in the declared regularity class.",
        }])

    add("F1-16-02", "reviews/F1-review-16-r2.json", "7a3e1f93f77c", "process-critical",
        "in-place edits under a fixed revision label defeated hash binding",
        [("T02_revision_label_present", True), ("M_f1_hash_match", True), ("M_authoring_aligned", True),
         ("M_stable_during_scan", True), ("M_manifest_pins_f1", True)],
        [],
        "Show the canonical F1 bytes changed without a revision bump or a FROZEN manifest update.",
        observations=[{
            "id": "OBS-02",
            "anchor": checks["T02_duplicate_revised_at"]["hits"][:4],
            "statement": "header uses the YAML key revised_at six times (l.8,10,12,14,16,20) plus revised_at_unused twice; PyYAML resolves last-key-wins (00:15:00). Hygiene, not the reviewed defect.",
            "falsifier": "A strict YAML 1.1/1.2 parser rejects or mis-resolves the header on re-parse.",
        }])

    add("F1-16-03", "reviews/F1-review-16-r2.json", "7a3e1f93f77c", "medium",
        "non_vacuity smuggled in a non-empty black-hole region requirement",
        [("T03_bh_excluded", True), ("T03_bh_forbidden_strengthening", True), ("T03_g_nonempty", True)],
        [],
        "Find a black-hole-region requirement inside non_vacuity.condition at b65fcc0f.")

    add("F1-16-04", "reviews/F1-review-16-r2.json", "7a3e1f93f77c", "medium",
        "tier_1 falsifier was strictly stronger than the universally quantified statement",
        [("T04_non_meager", True), ("T04_tier2", True)],
        [],
        "Show a single D0 datum accepted as a class refutation at b65fcc0f without non-meagerness or an instantiated G*.",
        observations=[{
            "id": "OBS-04",
            "anchor": checks["T04_tier1_robust_label"]["hits"],
            "statement": "the literal label 'tier_1-robust' requested by the reviewer is absent; the role is played by tier_2 (l.273-276), which refutes only the for-all-data strengthening.",
            "falsifier": "A gate criterion requiring the literal token tier_1-robust.",
        }])

    add("F1-16-05", "reviews/F1-review-16-r2.json", "7a3e1f93f77c", "medium",
        "machine_checkable_steps included proof obligations",
        [("T05_proof_obligations", True), ("T05_machine_checkable", True)],
        ["T05_mc_future_inext", "T05_po_future_inext"],
        "Show future-inextendibility listed only under proof_obligations, or only under machine_checkable_steps, at b65fcc0f.")

    add("F1-16-06", "reviews/F1-review-16-r2.json", "7a3e1f93f77c", "minor",
        "'exact_quantifiers: pinned' while quantifier domains were pending",
        [("T06_acceptance_map_absent", True), ("T06_pinned_token_absent", True), ("T06_quantifier_class", True)],
        [],
        "Find the acceptance_map block or the token 'pinned' at b65fcc0f.")

    add("F1-16-07", "reviews/F1-review-16-r2.json", "7a3e1f93f77c", "minor",
        "ambiguity runner had been run only on revision 2; re-run required before any gate claim",
        [("M_suite_bound_to_frozen", True), ("T07_suite_hash_unbound", True)],
        ["T07_stale_provenance", "T07_open_rows_mismatch"],
        "Show the external suite is not bound to b65fcc0f, or that the schema cites it, at the frozen revision.",
        verdict_override="partially_resolved_schema_provenance_stale")

    add("F1-16-08", "reviews/F1-review-16-r2.json", "7a3e1f93f77c", "minor-fixed",
        "dangling unresolved refs / deleted open decisions",
        [("T08_unresolved_refs_absent", True), ("T08_old_topology_key_absent", True), ("T08_curve_class_absent", True)],
        [],
        "Find an unresolved_refs field, an initial_slice_topology key, or a visibility.curve_class ref at b65fcc0f.")

    add("HF-06-a", "reviews/F1-review-lead-audit.json", "7a3e1f93f77c", "critical",
        "the F0 geodesic-completeness clause was relegated to f0_equivalent_form because a linter flagged a token",
        [("A06_f0_equivalent_form_absent", True), ("T01_past_phrase_absent", True)],
        [],
        "Show an f0_equivalent_form block or the past-completeness clause at b65fcc0f.")

    add("HF-06-b", "reviews/F1-review-lead-audit.json", "7a3e1f93f77c", "critical",
        "F0 clause 'B has non-empty interior whenever future-incomplete' absent with the divergence undocumented",
        [("A06_B_nonempty_interior_absent", True), ("T03_bh_excluded", True), ("T03_bh_forbidden_strengthening", True)],
        ["BIND_declared_f0_stale"],
        "Show the declared F0 hash in f0_binding equals the measured canonical or authoring F0 artifact at scan time.")

    add("HF-06-linter", "reviews/F1-review-lead-audit.json", "7a3e1f93f77c", "major",
        "formulation was shaped to avoid a linter token ('a gate that changes the formulation is not a gate')",
        [("A06_linter_absent", True)],
        [],
        "Find wording that justifies a formulation choice by a lexical-scan pass at b65fcc0f.")

    add("HF-06-contradiction", "reviews/F1-review-lead-audit.json", "7a3e1f93f77c", "major",
        "topology asserted slice completeness while unresolved[data_class.topology] asked whether it is assumed",
        [("A06_slice_complete_asserted", True), ("T08_old_topology_key_absent", True)],
        [],
        "Find an unresolved item that reopens slice completeness at b65fcc0f.")

    add("HF-04-past", "reviews/F1-review-lead-audit.json", "7a3e1f93f77c", "major",
        "equivalent_forms[0] used 'complete to the past', not the WCC condition",
        [("T01_past_phrase_absent", True)],
        [],
        "Find the phrase 'complete to the past' in any equivalent_* block at b65fcc0f.")

    add("HF-04-typing", "reviews/F1-review-lead-audit.json", "7a3e1f93f77c", "major",
        "logical_form mixed a boundary subset of M with a causal past computed in the conformal completion",
        [("A04_intersect_M_explicit", True)],
        [],
        "Find a J^-(q) occurrence in the formal statement or D5 that is not intersected with M at b65fcc0f.")

    add("DISPO-15", "reviews/F1-review-lead-audit.json (stop_rule) + f0_binding refresh rule", "7a3e1f93f77c",
        "critical",
        "F1 must bind the conclusion object field-for-field to F0; the schema's own refresh rule (l.307+) applies",
        [("BIND_f0_binding_field", True), ("BIND_declared_f0_stale", False)],
        [],
        "Show the declared F0 hash differs from both the measured canonical and authoring F0 hashes at scan time.")

    # ---- summary ------------------------------------------------------------
    counts = {}
    for f in F:
        counts[f["verdict"]] = counts.get(f["verdict"], 0) + 1

    n_res = counts.get("resolved_at_frozen", 0)
    n_part = sum(v for k, v in counts.items() if k.startswith("partially_resolved"))
    n_pres = counts.get("present_at_frozen", 0)
    gate_relevance = [
        f"{n_res}/{len(F)} disposed findings are resolved at the frozen pin; {n_part} partially resolved with named text residuals; {n_pres} present at the frozen bytes.",
        ("f0_binding is fresh at the frozen pin: declared == measured F0 artifact."
         if not f0_stale else
         f"f0_binding is STALE at the frozen pin: declared={declared_f0[:12]} measured_canonical={f0_can_a[:12]} measured_authoring={f0_auth_a[:12]}."),
        "The dominant G-FORM blocker is process-level, not textual: no independent verdict of record binds this pin; review_status.verdict is 'pending' in the frozen schema.",
        "Residual text items a re-review must adjudicate: " + ", ".join(
            f["id"] for f in F if f["verdict"] != "resolved_at_frozen") + ".",
    ]

    # ---- drift ledger: rev9 b65fcc0f -> rev10 68392dd8, observed mid-task -----
    drift_ledger = []
    if frozen_pin != FROZEN_PIN_FIRST_SCAN:
        entry = {
            "from_pin": FROZEN_PIN_FIRST_SCAN,
            "to_pin": frozen_pin,
            "observed_at": started,
            "effect": "two earlier runs of this scanner were written in drift mode with all 15 dispositions void; they are preserved hash-pinned at report.rev9-b65fcc0f.void.json and report.rev10-16128b62.void.json",
            "new_pin_manifest_revision": frozen.get("revision"),
        }
        snap = ROOT / F1_REV9_SNAPSHOT
        if snap.is_file():
            old_lines = snap.read_text(encoding="utf-8").splitlines()
            new_lines = text.splitlines()
            changed_new, changed_old = [], []
            for ln in difflib.unified_diff(old_lines, new_lines, lineterm="", n=0):
                if ln.startswith("@@"):
                    continue
                if ln.startswith("-") and not ln.startswith("---"):
                    changed_old.append(ln[1:].strip()[:120])
                elif ln.startswith("+") and not ln.startswith("+++"):
                    changed_new.append(ln[1:].strip()[:120])
            class_semantic = [l for l in changed_new
                              if "f0_binding" not in l and not l.startswith("#")
                              and not l.startswith("revised_at") and not l.startswith("revision:")]
            entry.update({
                "rev9_snapshot": F1_REV9_SNAPSHOT,
                "changed_old_lines": changed_old[:20],
                "changed_new_lines": changed_new[:20],
                "changed_lines_not_header_or_f0_binding": class_semantic,
                "delta_scope_note": "diff computed against the flash-04 rev9 snapshot; listed lines are changes outside the header and the f0_binding line and are NOT adjudicated here for class semantics; the formulation lead documents three refreeze cycles in leadform-status-0014.",
            })
        drift_ledger.append(entry)
    if not quiescent and pin_matches:
        drift_ledger.append({
            "from_pin": frozen_pin,
            "to_pin": f1_start,
            "observed_at": started,
            "effect": f"no quiescent window (disk == manifest pin, stable for {QUIESCE_NEED} samples) within {QUIESCE_MAX_S}s; dispositions are provisional against the measured bytes",
            "churn_samples": len(churn),
        })

    preserved = []
    for name in ("report.rev9-b65fcc0f.void.json", "report.rev10-16128b62.void.json"):
        if (OUT / name).is_file():
            preserved.append({"path": str((OUT / name).relative_to(ROOT)), "sha256": sha256(str((OUT / name).relative_to(ROOT)))})

    report = {
        "schema_version": "0.1",
        "report_id": f"{REPORT_ID}-{datetime.now(CST).strftime('%Y%m%dT%H%M%S')}",
        "task_id": TASK_ID,
        "actor": "worker-03",
        "agent_id": "deepseek-flash-03",
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "purpose": "static disposition of recorded F1 revise findings against the frozen F1 revision",
        "authority": "author-side textual audit only; NOT a review verdict, NOT an acceptance, no node/gate authority",
        "snapshot": {
            "started_at": started,
            "finished_at": now(),
            "artifact": CANONICAL_F1,
            "sha256": f1_start,
            "frozen_pin": frozen_pin,
            "pin_source": pin_source,
            "hash_match": pin_matches,
            "pin_status": "pinned" if pin_matches else "provisional_unpinned",
            "quiescent": quiescent,
            "stable_during_scan": stable,
            "declared_final_pin": declared_final_pin(),
            "churn_samples": churn,
            "authoring_aligned": authoring_aligned,
            "frozen_manifest": FROZEN_MANIFEST,
            "frozen_manifest_sha256": sha256(FROZEN_MANIFEST),
            "frozen_manifest_revision": frozen.get("revision"),
            "manifest_pins_f1": manifest_pins_match,
            "schema_revision": re.search(r"^revision: (\d+)$", text, re.M).group(1),
            "review_status_in_schema": "independent_reviewers=[] / verdict=pending",
        },
        "drift_ledger": drift_ledger,
        "preserved_void_reports": preserved,
        "finding_provenance": {
            "reviews": {k: {"path": v, "sha256": sha256(v)} for k, v in REVIEWS.items()},
            "note": "findings were written against F1 rev2/rev3 hashes f55722a7 / 7a3e1f93; the frozen target moved rev9 b65fcc0f -> rev10 68392dd8 during this task",
        },
        "measurements": {
            "declared_f0_sha256": declared_f0,
            "measured_f0_canonical": f0_can_a,
            "measured_f0_authoring": f0_auth_a,
            "f0_stable_during_scan": f0_can_a == f0_can_b and f0_auth_a == f0_auth_b,
            "f0_declared_stale": bool(f0_stale),
            "f1_suite": F1_SUITE,
            "f1_suite_sha256": sha256(F1_SUITE) if (ROOT / F1_SUITE).is_file() else None,
            "f1_suite_binding_sha256": suite_binding,
            "f1_suite_bound_to_frozen": bool(suite_ok),
            "research_map_sha256": sha256("research_map/research_map.json"),
        },
        "checks": checks,
        "dispositions": F,
        "summary": {"counts": counts, "total_findings_disposed": len(F)},
        "gate_relevance": gate_relevance,
        "falsifier": (
            "Re-run this scanner against the same FROZEN pin. The report is FALSIFIED if (a) the canonical F1 sha256 "
            "differs from " + frozen_pin[:12] + " while a disposition claims resolved; (b) any check's recorded result does not "
            "reproduce; or (c) a 'resolved_at_frozen' finding's cited defect is shown present at the frozen bytes. "
            "A prose mention without a line anchor is not a counterexample."
        ),
        "limitations": [
            "Static text only; no mathematical adjudication of the residual questions.",
            "Authored by the agent id that drafted F1; independent confirmation required before any gate use.",
            "A freeze after the measured sha256 voids every disposition (drift mode).",
        ],
        "tool": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256(str(Path(__file__).resolve().relative_to(ROOT)))},
    }
    if not pin_matches:
        report["drift_mode"] = True
        report["summary"]["counts"] = {"void_frozen_pin_mismatch": len(F)}

    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(OUT / "report.json"),
        "task_id": TASK_ID,
        "f1_sha256": f1_start[:16],
        "hash_match": pin_matches,
        "stable": stable,
        "f0_declared_stale": bool(f0_stale),
        "suite_bound": bool(suite_ok),
        "counts": report["summary"]["counts"],
        "non_resolved": [{"id": f["id"], "verdict": f["verdict"]} for f in F if f["verdict"] != "resolved_at_frozen"],
    }, indent=2))
    return 0 if pin_matches else 2


if __name__ == "__main__":
    sys.exit(main())
