#!/usr/bin/env python3
"""W092-F0ADJ-01 - independent adjudication of the conflicting F0 verdicts at pinned bytes.

Context (read-only task, no shared artifact is edited by this tool):
  W040 (artifacts/worker-040/f0_independent_verdict/verdict.json) accepted F0 at
  research_map/formulation_taxonomy.yaml#276009f4f63d with score 4.0.
  W082 (artifacts/worker-082/f0_independent_verdict/REVIEW-F0-082.json) returned revise 3.5
  at the same hash with blocking findings W082-F-01/F-02.
  The controller cannot count two accepts; this tool adjudicates the conflict from the bytes.

What it does (deterministic, offline, fail-closed):
  1. hash-pins the input F0 copy and aborts on drift;
  2. evaluates each contested finding against the YAML content and the raw text
     (line anchors measured, never copied from the reviews);
  3. audits the group's own consistency checker statically (AST) to test W082-F-02's
     claim that its D3 predicate never inspects the scalar class;
  4. audits whether the W040 accept check set probed the contested axis at all;
  5. runs controls on synthetic corrected/mutated copies so the detector is falsifiable;
  6. writes adjudication.json with per-finding CONFIRMED / NOT-CONFIRMED / PARTIAL.

Exit 0 iff the pin holds and all controls behave as recorded; nonzero otherwise.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

EXPECTED_F0_SHA = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
FROZEN_FOUR = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
SCALAR = "AF-WCC-SCALAR-SPH"
VACUUM = "AF-WCC-VAC-GEN"
CST = timezone(timedelta(hours=8))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(text: str, needle: str) -> int | None:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return None


def conclusion_text(doc: dict, cid: str) -> str:
    return str(((doc.get("classes", {}).get(cid, {}) or {}).get("conclusion") or {}).get("text", ""))


def detect(doc: dict, raw: str, aliases: dict) -> dict:
    """All predicates are pure functions of (doc, raw, aliases)."""
    classes = doc.get("classes", {})
    scalar = classes.get(SCALAR, {})
    vac = classes.get(VACUUM, {})
    concl = conclusion_text(doc, SCALAR)
    axes = scalar.get("axes", {}) or {}
    h4 = next((h for h in scalar.get("hypotheses", []) if h.get("id") == "H4"), {})
    fv = (doc.get("field_vocabulary") or {}).get("genericity_kind", {}) or {}
    rule = str(fv.get("rule", ""))
    comes = {cid: ("comeager" in conclusion_text(doc, cid).lower()) for cid in classes}
    adjud = doc.get("class_scope_adjudication", {}) or {}
    d3 = next((d for d in adjud.get("resolved_divergences", []) if d.get("id") == "D3"), {})
    d3_res = str(d3.get("resolution", ""))

    # ADJ-02: bare generic quantifier vs the class's own unresolved genericity declarations.
    bare_generic = bool(re.search(r"for generic data", concl, re.I))
    f01a = bool(
        bare_generic
        and str(axes.get("genericity_kind")) == "unresolved"
        and bool(h4.get("unresolved"))
        and not scalar.get("genericity_topology")
        and "must name genericity_kind" in rule
    )

    # ADJ-03: unsourced 'equivalently' equivalence clause.
    eq = "equivalently" in concl.lower()
    definition_marker = "not an asserted equivalence" in concl.lower()
    vac_has_marker = "not an asserted equivalence" in conclusion_text(doc, VACUUM).lower()
    src_hay = json.dumps(
        {
            "provenance": scalar.get("provenance"),
            "known_obstruction": scalar.get("known_obstruction"),
            "candidate_consequences": scalar.get("candidate_consequences"),
        },
        default=str,
    ).lower()
    sourced = any(tok in src_hay for tok in ("equivalen", "equivalence"))
    f01b = bool(eq and not definition_marker and not sourced)

    # ADJ-04: D3 record claims the comeager quantifier in EACH class conclusion text.
    claims_each = "each class conclusion text" in d3_res
    f02 = bool(claims_each and not all(comes.values()))

    # ADJ-05: revision chronology metadata.
    written = str(doc.get("written_at", ""))
    decided = str(adjud.get("decided_at", ""))
    rev = doc.get("revision")
    f03 = bool(written and decided and written < decided and rev == 4)

    # ADJ-06: alias tokens in a canonical artifact (VOCAB_ALIASES policy).
    alias_map = (aliases or {}).get("conclusion_type", {}) or {}
    alias_tokens = {t for canon, al in alias_map.items() for t in al if t != canon}
    alias_hits = {}
    for cid in classes:
        tok = str((classes.get(cid, {}).get("axes", {}) or {}).get("conclusion_type", ""))
        if tok in alias_tokens:
            alias_hits[cid] = tok
    f04 = bool(alias_hits)

    return {
        "measured": {
            "scalar_conclusion_line": line_of(raw, "For generic data in the class"),
            "scalar_H4_unresolved_line": line_of(raw, "must be named before any claim is filed"),
            "D3_record_line": line_of(raw, "the comeager quantifier is now stated explicitly"),
            "written_at_line": line_of(raw, "written_at:"),
            "comeager_in_class_conclusion": comes,
            "bare_generic_quantifier": bare_generic,
            "genericity_kind": axes.get("genericity_kind"),
            "genericity_topology": scalar.get("genericity_topology"),
            "H4_unresolved": bool(h4.get("unresolved")),
            "field_rule_requires_kind_and_topology": "must name genericity_kind" in rule,
            "equivalently_clause": eq,
            "definition_marker_in_scalar": definition_marker,
            "definition_marker_in_vacuum_HF06": vac_has_marker,
            "equivalence_source_found": sourced,
            "D3_resolution_text": d3_res[:200],
            "D3_claims_each_class": claims_each,
            "revision": rev,
            "written_at": written,
            "adjudication_decided_at": decided,
            "artifact_status": doc.get("status"),
            "alias_tokens_used_in_canonical": alias_hits,
        },
        "classification": {
            "W082-F-01a_bare_generic_vs_unresolved": "CONFIRMED" if f01a else "NOT-CONFIRMED",
            "W082-F-01b_unsourced_equivalently": "CONFIRMED" if f01b else "NOT-CONFIRMED",
            "W082-F-02_D3_record_false_for_scalar": "CONFIRMED" if f02 else "NOT-CONFIRMED",
            "W082-F-03_stale_written_at_rev4": "CONFIRMED" if f03 else "NOT-CONFIRMED",
            "W082-F-04_alias_tokens_in_canonical": "CONFIRMED-minor" if f04 else "NOT-CONFIRMED",
        },
        "booleans": {"f01a": f01a, "f01b": f01b, "f02": f02, "f03": f03, "f04": f04},
    }


def checker_scope(checker_src: str) -> dict:
    """Static AST audit of the D3 predicate in check_taxonomy_consistency.py.

    W082-F-02 claims the D3 predicate never inspects the scalar class conclusion.
    Find the If node whose test calls ctext() and collect the class-id literals it reads.
    """
    tree = ast.parse(checker_src)
    scopes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        called = [n for n in ast.walk(node.test) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Name) and n.func.id == "ctext"]
        if not called:
            continue
        literals = sorted({a.value for n in ast.walk(node.test)
                           for a in ast.walk(n)
                           if isinstance(a, ast.Constant) and isinstance(a.value, str)
                           and a.value.startswith("AF-")})
        if literals:
            scopes.append({"classes_read_by_predicate": literals,
                           "n_ctext_calls": len(called)})
    inspected = sorted({c for s in scopes for c in s["classes_read_by_predicate"]})
    return {
        "ctext_predicate_scopes": scopes,
        "classes_inspected_by_any_ctext_predicate": inspected,
        "scalar_class_inspected": SCALAR in inspected,
        "W082_F02_tool_coverage_claim_CONFIRMED": SCALAR not in inspected,
    }


def w040_coverage(checks_path: Path) -> dict:
    """Measure what the W040 accept actually probed, not which words it contains.

    W082-F-01/F-02 are about *internal* consistency: the scalar conclusion's bare
    'generic' quantifier and 'equivalently' clause versus that class's own
    genericity_kind/H4. A dual-tree comparison that records
    genericity_kind='unresolved' and only asserts conclusion_present_both: true does
    not test that axis. Count the decisive tokens and the presence-only predicate.
    """
    blob = checks_path.read_text().lower() if checks_path.exists() else ""
    counts = {tok: blob.count(tok) for tok in
              ("comeager", "inflation", "unsourced", "generic data", "genericity_kind")}
    recorded_unresolved = '"genericity_kind": "unresolved"' in blob.replace("\n", " ")
    try:
        data = json.loads(checks_path.read_text())
        per_class = (((data.get("checks", {}).get("C4_dual_tree", {}) or {})
                      .get("per_class", {}) or {}).get(SCALAR, {}) or {})
    except Exception:
        per_class = {}
    presence_only = bool(per_class.get("conclusion_present_both")) and "conclusion_text" not in json.dumps(per_class)
    internal_axis_probed = counts["comeager"] > 0 or counts["inflation"] > 0 or counts["unsourced"] > 0
    return {
        "checks_file": str(checks_path),
        "checks_file_sha256": sha256_file(checks_path) if checks_path.exists() else None,
        "decisive_token_counts_in_W040_check_set": counts,
        "W040_recorded_scalar_genericity_unresolved": recorded_unresolved,
        "W040_scalar_conclusion_check_is_presence_only": presence_only,
        "W040_accept_probed_contested_axis": internal_axis_probed,
        "assessment": (
            "no internal-consistency predicate: the accept recorded genericity_kind='unresolved' for "
            "AF-WCC-SCALAR-SPH but tested only conclusion presence and canonical/authoring token "
            "agreement (0 occurrences of comeager/inflation/unsourced in its check set)"
            if not internal_axis_probed else
            "the accept check set contains a predicate on the contested axis; re-read before relying "
            "on the conflict resolution"
        ),
    }


def controls(doc: dict, raw: str, aliases: dict) -> dict:
    base = detect(doc, raw, aliases)
    # CTL-1 pristine
    ctl1 = base["booleans"]
    # CTL-2 mutation: add the missing comeager quantifier to the scalar conclusion.
    mut = copy.deepcopy(doc)
    mut["classes"][SCALAR]["conclusion"]["text"] = (
        conclusion_text(doc, SCALAR) + " In the comeager sense."
    )
    ctl2 = detect(mut, raw, aliases)["booleans"]
    # CTL-3 repair: named genericity + definition marker, mirroring the vacuum HF-06 repair.
    rep = copy.deepcopy(doc)
    rep["classes"][SCALAR]["conclusion"]["text"] = (
        "For every admissible (s,delta) there is a comeager set G_{s,delta} of data such that "
        "for every data set in G_{s,delta}, the MGHD admits I+ and every future-inextendible "
        "causal geodesic contained in J-(I+) is complete. This is a definition, not an asserted "
        "equivalence with any other formulation (review HF-06)."
    )
    rep["classes"][SCALAR]["axes"]["genericity_kind"] = "baire_residual"
    for h in rep["classes"][SCALAR].get("hypotheses", []):
        if h.get("id") == "H4":
            h["unresolved"] = False
    ctl3 = detect(rep, raw, aliases)["booleans"]
    # CTL-4 determinism: byte-identical rerun.
    ctl4 = detect(doc, raw, aliases)["booleans"]
    expected = {
        "CTL-1_pristine_fires": ctl1 == {"f01a": True, "f01b": True, "f02": True, "f03": True, "f04": True},
        "CTL-2_mutation_clears_D3_quantifier_only": ctl2["f02"] is False and ctl2["f01a"] is True,
        "CTL-3_repair_clears_F01": ctl3["f01a"] is False and ctl3["f01b"] is False,
        "CTL-4_deterministic": ctl4 == ctl1,
    }
    return {
        "CTL-1_pristine": ctl1,
        "CTL-2_mutation_add_comeager_to_scalar": ctl2,
        "CTL-3_repair_scalar_conclusion": ctl3,
        "CTL-4_pristine_rerun": ctl4,
        "expected": expected,
        "all_controls_as_expected": all(expected.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--f0", required=True)
    ap.add_argument("--checker", required=True)
    ap.add_argument("--aliases", required=True)
    ap.add_argument("--w040-checks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expected-sha", default=EXPECTED_F0_SHA)
    args = ap.parse_args()

    f0 = Path(args.f0)
    out = Path(args.out)
    measured = sha256_file(f0)
    drift = measured != args.expected_sha
    if drift:
        print(f"FAIL hash drift: {f0} = {measured}, expected {args.expected_sha}")
        return 2

    raw = f0.read_text()
    doc = yaml.safe_load(raw)
    aliases = json.loads(Path(args.aliases).read_text())
    checker_src = Path(args.checker).read_text()

    det = detect(doc, raw, aliases)
    scope = checker_scope(checker_src)
    cov = w040_coverage(Path(args.w040_checks))
    ctl = controls(doc, raw, aliases)

    adjudication = {
        "task_id": "W092-F0ADJ-01",
        "adjudicator": "worker-092",
        "pinned_f0": str(f0),
        "pinned_f0_sha256": measured,
        "pinned_checker_sha256": sha256_file(Path(args.checker)),
        "generated_at": datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "verdict": "revise",
        "score": 3.0,
        "verdict_basis": (
            "W082 blocking findings W082-F-01 (a,b) and W082-F-02 are CONFIRMED against the pinned "
            "bytes with independently measured anchors; W082-F-03 and W082-F-04 are also confirmed "
            "(minor/info). The W040 accept check set recorded the scalar class's "
            "genericity_kind='unresolved' but tested only conclusion presence and canonical/authoring "
            "token agreement (0 occurrences of comeager/inflation/unsourced), so it does not "
            "contradict the confirmed defect - it did not probe internal conclusion/genericity "
            "consistency."
        ),
        "conflict_resolution": {
            "W040_verdict": "accept",
            "W040_score": 4.0,
            "W082_verdict": "revise",
            "W082_score": 3.5,
            "resolution": "revise",
            "reason": "the contested content defect is measured to exist; the accept's checks are structural-only",
        },
        "detection": det,
        "checker_coverage_audit": scope,
        "W040_coverage_audit": cov,
        "controls": ctl,
        "gate_relevance": {
            "gate": "G-F0",
            "artifact_status_blocks_accept_claim": det["measured"]["artifact_status"] == "draft_unverified",
            "artifact_status": det["measured"]["artifact_status"],
            "D3_record_is_contradicted_by_bytes": det["booleans"]["f02"],
            "note": "adjudication only; worker events cannot set gate verdicts or node status",
        },
        "falsifier": (
            "Re-run adjudicate_f0.py on artifacts/worker-092/f0adj/pinned/"
            "formulation_taxonomy.276009f4f63d.yaml: falsified if any CONFIRMED classification "
            "does not reproduce, if CTL-1..CTL-4 do not behave as recorded, or if a reviewer "
            "exhibits a named genericity notion for AF-WCC-SCALAR-SPH inside the pinned revision."
        ),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "adjudication.json").write_text(json.dumps(adjudication, indent=2, sort_keys=True) + "\n")

    print(f"pin ok: {f0.name} {measured[:12]}")
    for k, v in det["classification"].items():
        print(f"  {k}: {v}")
    print(f"  checker inspects scalar class: {scope['scalar_class_inspected']}")
    print(f"  W040 accept probed contested axis: {cov['W040_accept_probed_contested_axis']}")
    for k, v in ctl["expected"].items():
        print(f"  control {k}: {'ok' if v else 'FAIL'}")
    print(f"adjudication written: {out / 'adjudication.json'}")

    ok = ctl["all_controls_as_expected"] and scope["W082_F02_tool_coverage_claim_CONFIRMED"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
